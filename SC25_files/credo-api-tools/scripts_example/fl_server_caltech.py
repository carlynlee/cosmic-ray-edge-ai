#!/usr/bin/env python3
"""
Federated Learning Server for CREDO
Runs on Caltech FL Server pod and coordinates training across MIT and UDel clients
"""

import flwr as fl
import tensorflow as tf
from tensorflow.keras.applications.resnet50 import ResNet50
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.optimizers import Adam
import numpy as np
import os
import json
from datetime import datetime

# Configuration
IMG_SIZE = (224, 224)
NUM_CLASSES = 10
LEARNING_RATE = 0.001
NUM_ROUNDS = 5
MIN_CLIENTS = 3  # Need Caltech, MIT, and UDel clients

def build_global_model():
    """Build the global model architecture"""
    # Base ResNet50 model
    base_model = ResNet50(weights='imagenet', include_top=False, input_shape=(*IMG_SIZE, 3))
    
    # Freeze base model layers
    base_model.trainable = False
    
    # Add classification head
    model = tf.keras.Sequential([
        base_model,
        GlobalAveragePooling2D(),
        Dense(512, activation='relu'),
        Dropout(0.5),
        Dense(NUM_CLASSES, activation='softmax')
    ])
    
    # Compile model
    model.compile(
        optimizer=Adam(learning_rate=LEARNING_RATE),
        loss='categorical_crossentropy',
        metrics=['accuracy']
    )
    
    return model

def get_model_parameters(model):
    """Get model parameters as a flat list of NumPy ndarrays"""
    params = []
    for layer in model.layers:
        if layer.trainable_weights:
            weights = layer.get_weights()
            params.extend(weights)  # Flatten the list
    return params

def set_model_parameters(model, parameters):
    """Set model parameters from a flat list of NumPy ndarrays"""
    param_idx = 0
    for layer in model.layers:
        if layer.trainable_weights:
            num_weights = len(layer.trainable_weights)
            layer_weights = parameters[param_idx:param_idx + num_weights]
            layer.set_weights(layer_weights)
            param_idx += num_weights

# Create global model
global_model = build_global_model()

# Store training history
training_history = []

# Store per-site test set accuracy results
per_site_test_results = {}

class CREDOFederatedStrategy(fl.server.strategy.FedAvg):
    """Custom federated learning strategy for CREDO"""
    
    def aggregate_fit(self, rnd, results, failures):
        """Aggregate model updates from clients"""
        if not results:
            return None, {}
        
        print(f"\n[Round {rnd}] Aggregating updates from {len(results)} clients")
        
        # Aggregate weights using federated averaging
        aggregated_weights = super().aggregate_fit(rnd, results, failures)
        
        if aggregated_weights is not None:
            # Convert Parameters to list of numpy arrays
            aggregated_ndarrays = fl.common.parameters_to_ndarrays(aggregated_weights[0])
            # Update global model
            set_model_parameters(global_model, aggregated_ndarrays)
            print(f"[Round {rnd}] Global model updated")
        
        return aggregated_weights
    
    def aggregate_evaluate(self, rnd, results, failures):
        """Aggregate evaluation results from clients"""
        if not results:
            return None, {}
        
        print(f"\n[Round {rnd}] Aggregating evaluation from {len(results)} clients")
        
        # Aggregate metrics
        aggregated_metrics = super().aggregate_evaluate(rnd, results, failures)
        
        if aggregated_metrics is not None:
            loss, metrics = aggregated_metrics
            print(f"[Round {rnd}] Aggregated Loss: {loss:.4f}, Metrics: {metrics}")
            
            # Extract per-site test set accuracy for all 10 classes
            for result in results:
                client_metrics = result[1].metrics if result[1].metrics else {}
                institution = client_metrics.get('institution', 'Unknown')
                site = client_metrics.get('site', 'unknown')
                
                if institution and 'per_class_accuracy' in client_metrics:
                    per_site_test_results[site] = {
                        'institution': institution,
                        'site': site,
                        'round': rnd,
                        'overall_accuracy': client_metrics.get('overall_accuracy', 0.0),
                        'overall_loss': client_metrics.get('overall_loss', 0.0),
                        'per_class_accuracy': client_metrics.get('per_class_accuracy', {}),
                        'test_samples_per_class': client_metrics.get('test_samples_per_class', {}),
                        'total_test_samples': client_metrics.get('total_test_samples', 0)
                    }
                    
                    print(f"\n[{institution}] Test Set Accuracy (Round {rnd}):")
                    print(f"  Overall Accuracy: {client_metrics.get('overall_accuracy', 0.0):.4f}")
                    print(f"  Per-Class Accuracy:")
                    for class_id in range(NUM_CLASSES):
                        class_acc = client_metrics.get('per_class_accuracy', {}).get(f'class_{class_id}', 0.0)
                        class_samples = client_metrics.get('test_samples_per_class', {}).get(f'class_{class_id}', 0)
                        print(f"    Class {class_id}: {class_acc:.4f} ({class_samples} samples)")
            
            # Store in history
            training_history.append({
                'round': rnd,
                'loss': float(loss),
                'metrics': metrics,
                'num_clients': len(results)
            })
        
        return aggregated_metrics

def main():
    """Start the federated learning server"""
    print("=" * 60)
    print("CREDO FEDERATED LEARNING SERVER")
    print("Caltech FL Server - Coordinating Multi-Site Training")
    print("=" * 60)
    
    # Get initial parameters
    initial_parameters = fl.common.ndarrays_to_parameters(
        get_model_parameters(global_model)
    )
    
    # Create strategy
    strategy = CREDOFederatedStrategy(
        min_fit_clients=MIN_CLIENTS,
        min_evaluate_clients=MIN_CLIENTS,
        min_available_clients=MIN_CLIENTS,
        initial_parameters=initial_parameters,
        fraction_fit=1.0,  # Use all available clients
        fraction_evaluate=1.0,
    )
    
    # Start server
    print(f"\nStarting FL server on port 5000...")
    print(f"Waiting for {MIN_CLIENTS} clients (Caltech, MIT, and UDel)...")
    print("=" * 60)
    
    fl.server.start_server(
        server_address="0.0.0.0:5000",
        config=fl.server.ServerConfig(num_rounds=NUM_ROUNDS),
        strategy=strategy
    )
    
    # Save results after training
    print("\n" + "=" * 60)
    print("FEDERATED LEARNING COMPLETE")
    print("=" * 60)
    
    results_file = "/workspace/fl-server/fl_training_results.json"
    test_accuracy_file = "/workspace/fl-server/fl_test_accuracy_per_site.json"
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    
    results = {
        'total_rounds': NUM_ROUNDS,
        'training_history': training_history,
        'final_model_parameters': get_model_parameters(global_model),
        'timestamp': datetime.now().isoformat()
    }
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"Training results saved to {results_file}")
    
    # Save per-site test set accuracy for all 10 types
    if per_site_test_results:
        # Get the final round results (most recent)
        final_round = max([r['round'] for r in per_site_test_results.values()])
        final_results = {site: data for site, data in per_site_test_results.items() 
                        if data['round'] == final_round}
        
        test_accuracy_summary = {
            'timestamp': datetime.now().isoformat(),
            'total_rounds': NUM_ROUNDS,
            'final_round': final_round,
            'per_site_test_accuracy': final_results,
            'summary': {}
        }
        
        # Create summary table
        print("\n" + "=" * 60)
        print("PER-SITE TEST SET ACCURACY (All 10 Types)")
        print("=" * 60)
        for site, data in final_results.items():
            print(f"\n{data['institution']} ({site}):")
            print(f"  Overall Accuracy: {data['overall_accuracy']:.4f}")
            print(f"  Per-Class Accuracy:")
            for class_id in range(NUM_CLASSES):
                class_acc = data['per_class_accuracy'].get(f'class_{class_id}', 0.0)
                class_samples = data['test_samples_per_class'].get(f'class_{class_id}', 0)
                print(f"    Class {class_id}: {class_acc:.4f} ({class_samples} samples)")
            
            # Add to summary
            test_accuracy_summary['summary'][site] = {
                'institution': data['institution'],
                'overall_accuracy': data['overall_accuracy'],
                'per_class_accuracy': data['per_class_accuracy']
            }
        
        with open(test_accuracy_file, 'w') as f:
            json.dump(test_accuracy_summary, f, indent=2, default=str)
        
        print(f"\nPer-site test accuracy saved to {test_accuracy_file}")
    else:
        print("\nWarning: No per-site test accuracy results collected")
    
    print("=" * 60)

if __name__ == "__main__":
    main()

