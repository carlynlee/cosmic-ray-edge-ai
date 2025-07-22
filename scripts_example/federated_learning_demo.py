#!/usr/bin/env python3
"""
Simplified Federated Learning Demo for CREDO Image Classification
Simulates federated learning process without requiring a separate server
"""

import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array, load_img
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import to_categorical
import pandas as pd
import json
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import copy

# Configuration
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 3
LEARNING_RATE = 0.001
NUM_CLASSES = 10
NUM_ROUNDS = 5

class CREDOClusterModel:
    """Model for a specific cluster in federated learning"""
    
    def __init__(self, cluster_id):
        self.cluster_id = cluster_id
        self.model = None
        self.x_train, self.y_train = None, None
        self.x_test, self.y_test = None, None
        self.training_history = []
        
        # Load cluster-specific data
        self._load_cluster_data()
        self._build_model()
    
    def _load_cluster_data(self):
        """Load images for this specific cluster"""
        print(f"Loading data for cluster {self.cluster_id}")
        
        # Load cluster assignments
        cluster_file = "/data/exports/cluster_results.txt"
        if not os.path.exists(cluster_file):
            print("Cluster results not found!")
            return
        
        df = pd.read_csv(cluster_file)
        
        # Filter images for this cluster
        cluster_images = df[df['Cluster'] == self.cluster_id]['Image_Path'].tolist()
        
        print(f"Found {len(cluster_images)} images for cluster {self.cluster_id}")
        
        if len(cluster_images) == 0:
            print(f"No images found for cluster {self.cluster_id}")
            return
        
        # Load and preprocess images
        images = []
        labels = []
        
        for img_path in cluster_images:
            try:
                # Load and preprocess image
                img = load_img(img_path, target_size=IMG_SIZE)
                img_array = img_to_array(img)
                img_preprocessed = preprocess_input(img_array)
                
                images.append(img_preprocessed)
                labels.append(self.cluster_id)  # Use cluster ID as label
                    
            except Exception as e:
                print(f"Error loading {img_path}: {e}")
                continue
        
        if len(images) == 0:
            print(f"No valid images loaded for cluster {self.cluster_id}")
            return
        
        # Convert to numpy arrays
        X = np.array(images)
        y = np.array(labels)
        
        # Convert labels to categorical
        y_categorical = to_categorical(y, num_classes=NUM_CLASSES)
        
        # Split into train/test
        self.x_train, self.x_test, self.y_train, self.y_test = train_test_split(
            X, y_categorical, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"Cluster {self.cluster_id}: {len(self.x_train)} train, {len(self.x_test)} test samples")
    
    def _build_model(self):
        """Build the model"""
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
        
        self.model = model
        print(f"Model built for cluster {self.cluster_id}")
    
    def train_local(self):
        """Train the model on local data"""
        if self.x_train is None or len(self.x_train) == 0:
            print(f"No training data for cluster {self.cluster_id}")
            return None
        
        # Train the model
        history = self.model.fit(
            self.x_train, self.y_train,
            batch_size=BATCH_SIZE,
            epochs=EPOCHS,
            validation_data=(self.x_test, self.y_test),
            verbose=1
        )
        
        # Store training history
        self.training_history.append({
            'accuracy': float(history.history['accuracy'][-1]),
            'loss': float(history.history['loss'][-1]),
            'val_accuracy': float(history.history['val_accuracy'][-1]),
            'val_loss': float(history.history['val_loss'][-1])
        })
        
        return history
    
    def evaluate_local(self):
        """Evaluate the model on local test data"""
        if self.x_test is None or len(self.x_test) == 0:
            return 0.0, 0.0
        
        loss, accuracy = self.model.evaluate(self.x_test, self.y_test, verbose=0)
        return loss, accuracy
    
    def get_weights(self):
        """Get model weights"""
        return [layer.get_weights() for layer in self.model.layers if layer.trainable_weights]
    
    def set_weights(self, weights):
        """Set model weights"""
        weight_idx = 0
        for layer in self.model.layers:
            if layer.trainable_weights:
                layer.set_weights(weights[weight_idx])
                weight_idx += 1

def get_cluster_distribution():
    """Get distribution of images across clusters"""
    cluster_file = "/data/exports/cluster_results.txt"
    if not os.path.exists(cluster_file):
        print("Cluster results not found!")
        return {}
    
    df = pd.read_csv(cluster_file)
    cluster_counts = df['Cluster'].value_counts().to_dict()
    
    print("Cluster Distribution:")
    for cluster_id, count in sorted(cluster_counts.items()):
        print(f"  Cluster {cluster_id}: {count} images")
    
    return cluster_counts

def federated_average(weights_list):
    """Simple federated averaging of model weights"""
    if not weights_list:
        return None
    
    # Average the weights
    averaged_weights = []
    for weights_list_tuple in zip(*weights_list):
        averaged_weights.append(
            np.array([np.array(w).mean(axis=0) for w in zip(*weights_list_tuple)])
        )
    
    return averaged_weights

def run_federated_learning_demo():
    """Run federated learning demo"""
    print("Starting Federated Learning Demo for CREDO Image Classification")
    
    # Get cluster distribution
    cluster_counts = get_cluster_distribution()
    
    if not cluster_counts:
        print("No cluster data available!")
        return
    
    # Create models for each cluster with sufficient data (at least 5 images)
    cluster_models = []
    for cluster_id, count in cluster_counts.items():
        if count >= 5:  # Minimum images per cluster
            model = CREDOClusterModel(cluster_id)
            if model.x_train is not None and len(model.x_train) > 0:
                cluster_models.append(model)
    
    print(f"Created {len(cluster_models)} valid cluster models")
    
    if len(cluster_models) == 0:
        print("No valid models created!")
        return
    
    # Federated learning rounds
    global_weights = None
    round_results = []
    
    for round_num in range(NUM_ROUNDS):
        print(f"\n=== Federated Learning Round {round_num + 1}/{NUM_ROUNDS} ===")
        
        # Train each cluster model locally
        round_weights = []
        round_metrics = []
        
        for model in cluster_models:
            print(f"\nTraining cluster {model.cluster_id}...")
            
            # Set global weights if available
            if global_weights is not None:
                model.set_weights(global_weights)
            
            # Train locally
            history = model.train_local()
            
            if history is not None:
                # Get weights
                weights = model.get_weights()
                round_weights.append(weights)
                
                # Get metrics
                loss, accuracy = model.evaluate_local()
                round_metrics.append({
                    'cluster_id': model.cluster_id,
                    'accuracy': accuracy,
                    'loss': loss,
                    'train_samples': len(model.x_train)
                })
                
                print(f"Cluster {model.cluster_id}: Accuracy={accuracy:.4f}, Loss={loss:.4f}")
        
        # Federated averaging
        if round_weights:
            global_weights = federated_average(round_weights)
            print(f"\nFederated averaging completed for {len(round_weights)} models")
        
        # Store round results
        round_results.append({
            'round': round_num + 1,
            'metrics': round_metrics,
            'num_models': len(round_weights)
        })
    
    # Final evaluation
    print("\n=== Final Evaluation ===")
    final_metrics = []
    
    for model in cluster_models:
        if global_weights is not None:
            model.set_weights(global_weights)
        
        loss, accuracy = model.evaluate_local()
        final_metrics.append({
            'cluster_id': model.cluster_id,
            'accuracy': accuracy,
            'loss': loss,
            'train_samples': len(model.x_train)
        })
        
        print(f"Cluster {model.cluster_id}: Final Accuracy={accuracy:.4f}, Loss={loss:.4f}")
    
    # Save results
    results = {
        'round_results': round_results,
        'final_metrics': final_metrics,
        'total_rounds': NUM_ROUNDS,
        'total_models': len(cluster_models)
    }
    
    results_file = "/data/exports/federated_learning_results.json"
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {results_file}")
    
    # Create visualization
    create_federated_learning_visualization(round_results, final_metrics)
    
    print("\nFederated Learning Demo Complete!")

def create_federated_learning_visualization(round_results, final_metrics):
    """Create visualization of federated learning results"""
    plt.figure(figsize=(15, 10))
    
    # Plot 1: Accuracy progression across rounds
    plt.subplot(2, 2, 1)
    for round_data in round_results:
        round_num = round_data['round']
        accuracies = [m['accuracy'] for m in round_data['metrics']]
        plt.plot([round_num] * len(accuracies), accuracies, 'o', alpha=0.6)
    
    plt.xlabel('Round')
    plt.ylabel('Accuracy')
    plt.title('Accuracy Progression Across Rounds')
    plt.grid(True, alpha=0.3)
    
    # Plot 2: Final accuracy by cluster
    plt.subplot(2, 2, 2)
    cluster_ids = [m['cluster_id'] for m in final_metrics]
    accuracies = [m['accuracy'] for m in final_metrics]
    
    plt.bar(range(len(cluster_ids)), accuracies)
    plt.xlabel('Cluster ID')
    plt.ylabel('Final Accuracy')
    plt.title('Final Accuracy by Cluster')
    plt.xticks(range(len(cluster_ids)), cluster_ids)
    
    # Plot 3: Loss progression
    plt.subplot(2, 2, 3)
    for round_data in round_results:
        round_num = round_data['round']
        losses = [m['loss'] for m in round_data['metrics']]
        plt.plot([round_num] * len(losses), losses, 'o', alpha=0.6)
    
    plt.xlabel('Round')
    plt.ylabel('Loss')
    plt.title('Loss Progression Across Rounds')
    plt.grid(True, alpha=0.3)
    
    # Plot 4: Training samples vs accuracy
    plt.subplot(2, 2, 4)
    samples = [m['train_samples'] for m in final_metrics]
    accuracies = [m['accuracy'] for m in final_metrics]
    
    plt.scatter(samples, accuracies, alpha=0.7)
    plt.xlabel('Training Samples')
    plt.ylabel('Final Accuracy')
    plt.title('Training Samples vs Final Accuracy')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save visualization
    viz_file = "/data/exports/federated_learning_visualization.png"
    plt.savefig(viz_file, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to {viz_file}")

if __name__ == "__main__":
    run_federated_learning_demo() 