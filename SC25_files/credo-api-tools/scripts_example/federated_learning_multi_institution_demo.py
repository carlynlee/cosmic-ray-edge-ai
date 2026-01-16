#!/usr/bin/env python3
"""
Multi-Institution Federated Learning Demo for SC25
Simulates distributed cosmic ray detection network across institutions
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

# Institution Configuration
INSTITUTIONS = {
    "Caltech": {
        "clusters": [0, 1, 2, 3],
        "name": "California Institute of Technology",
        "location": "Pasadena, CA",
        "detectors": 4
    },
    "MIT": {
        "clusters": [4, 5, 6],
        "name": "Massachusetts Institute of Technology", 
        "location": "Cambridge, MA",
        "detectors": 3
    },
    "University_of_Delaware": {
        "clusters": [7, 8, 9],
        "name": "University of Delaware",
        "location": "Newark, DE", 
        "detectors": 3
    }
}

class InstitutionModel:
    """Model representing a single institution in the federated learning network"""
    
    def __init__(self, institution_name, cluster_ids):
        self.institution_name = institution_name
        self.cluster_ids = cluster_ids
        self.model = None
        self.x_train, self.y_train = None, None
        self.x_test, self.y_test = None, None
        self.training_history = []
        
        # Load institution-specific data
        self._load_institution_data()
        self._build_model()
    
    def _load_institution_data(self):
        """Load images for this specific institution's clusters"""
        print(f"Loading data for {self.institution_name}...")
        
        # Load cluster assignments
        cluster_file = "/data/exports/cluster_results.txt"
        if not os.path.exists(cluster_file):
            print("Cluster results not found!")
            return
        
        df = pd.read_csv(cluster_file)
        
        # Filter images for this institution's clusters
        institution_images = df[df['Cluster'].isin(self.cluster_ids)]['Image_Path'].tolist()
        
        print(f"Found {len(institution_images)} images for {self.institution_name}")
        
        if len(institution_images) == 0:
            print(f"No images found for {self.institution_name}")
            return
        
        # Load and preprocess images
        images = []
        labels = []
        
        for img_path in institution_images:
            try:
                # Load and preprocess image
                img = load_img(img_path, target_size=IMG_SIZE)
                img_array = img_to_array(img)
                img_preprocessed = preprocess_input(img_array)
                
                images.append(img_preprocessed)
                
                # Get cluster ID for this image
                cluster_id = df[df['Image_Path'] == img_path]['Cluster'].iloc[0]
                labels.append(cluster_id)
                    
            except Exception as e:
                print(f"Error loading {img_path}: {e}")
                continue
        
        if len(images) == 0:
            print(f"No valid images loaded for {self.institution_name}")
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
        
        print(f"{self.institution_name}: {len(self.x_train)} train, {len(self.x_test)} test samples")
    
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
        print(f"Model built for {self.institution_name}")
    
    def train_local(self):
        """Train the model on local institution data"""
        if self.x_train is None or len(self.x_train) == 0:
            print(f"No training data for {self.institution_name}")
            return None
        
        print(f"\nTraining {self.institution_name} model...")
        
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
            'institution': self.institution_name,
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

def run_multi_institution_demo():
    """Run multi-institution federated learning demo"""
    print("=" * 60)
    print("MULTI-INSTITUTION FEDERATED LEARNING DEMO")
    print("Distributed Cosmic Ray Detection Network")
    print("=" * 60)
    
    # Create models for each institution
    institution_models = []
    
    for institution_name, config in INSTITUTIONS.items():
        print(f"\nSetting up {config['name']} ({institution_name})")
        print(f"  Location: {config['location']}")
        print(f"  Cosmic Ray Detectors: {config['detectors']}")
        print(f"  Data Clusters: {config['clusters']}")
        
        model = InstitutionModel(institution_name, config['clusters'])
        if model.x_train is not None and len(model.x_train) > 0:
            institution_models.append(model)
    
    print(f"\nCreated {len(institution_models)} institution models")
    
    if len(institution_models) == 0:
        print("No valid models created!")
        return
    
    # Federated learning rounds
    global_weights = None
    round_results = []
    
    for round_num in range(NUM_ROUNDS):
        print(f"\n{'='*50}")
        print(f"FEDERATED LEARNING ROUND {round_num + 1}/{NUM_ROUNDS}")
        print(f"{'='*50}")
        
        # Train each institution model locally
        round_weights = []
        round_metrics = []
        
        for model in institution_models:
            print(f"\n--- {model.institution_name} ---")
            
            # Set global weights if available
            if global_weights is not None:
                model.set_weights(global_weights)
                print(f"  Applied global model weights")
            
            # Train locally
            history = model.train_local()
            
            if history is not None:
                # Get weights
                weights = model.get_weights()
                round_weights.append(weights)
                
                # Get metrics
                loss, accuracy = model.evaluate_local()
                round_metrics.append({
                    'institution': model.institution_name,
                    'accuracy': accuracy,
                    'loss': loss,
                    'train_samples': len(model.x_train),
                    'clusters': model.cluster_ids
                })
                
                print(f"  Local Accuracy: {accuracy:.4f}, Loss: {loss:.4f}")
        
        # Federated averaging
        if round_weights:
            global_weights = federated_average(round_weights)
            print(f"\nFEDERATED AVERAGING COMPLETED")
            print(f"   Combined knowledge from {len(round_weights)} institutions")
            print(f"   No raw data shared - only model parameters exchanged")
        
        # Store round results
        round_results.append({
            'round': round_num + 1,
            'metrics': round_metrics,
            'num_institutions': len(round_weights)
        })
    
    # Final evaluation
    print(f"\n{'='*50}")
    print("FINAL EVALUATION")
    print(f"{'='*50}")
    final_metrics = []
    
    for model in institution_models:
        if global_weights is not None:
            model.set_weights(global_weights)
        
        loss, accuracy = model.evaluate_local()
        final_metrics.append({
            'institution': model.institution_name,
            'accuracy': accuracy,
            'loss': loss,
            'train_samples': len(model.x_train),
            'clusters': model.cluster_ids
        })
        
        print(f"{model.institution_name}: Final Accuracy={accuracy:.4f}, Loss={loss:.4f}")
    
    # Save results
    results = {
        'round_results': round_results,
        'final_metrics': final_metrics,
        'total_rounds': NUM_ROUNDS,
        'total_institutions': len(institution_models),
        'institutions': INSTITUTIONS
    }
    
    results_file = "/data/exports/multi_institution_fl_results.json"
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {results_file}")
    
    # Create visualization
    create_multi_institution_visualization(round_results, final_metrics)
    
    print("\n" + "="*60)
    print("MULTI-INSTITUTION FEDERATED LEARNING DEMO COMPLETE!")
    print("="*60)

def create_multi_institution_visualization(round_results, final_metrics):
    """Create visualization of multi-institution federated learning results"""
    plt.figure(figsize=(15, 10))
    
    # Plot 1: Accuracy progression across rounds
    plt.subplot(2, 2, 1)
    colors = ['blue', 'red', 'green']
    for i, round_data in enumerate(round_results):
        round_num = round_data['round']
        for j, metric in enumerate(round_data['metrics']):
            plt.plot(round_num, metric['accuracy'], 'o', 
                    color=colors[j], alpha=0.6, markersize=8)
    
    plt.xlabel('Round')
    plt.ylabel('Accuracy')
    plt.title('Institution Accuracy Progression')
    plt.grid(True, alpha=0.3)
    
    # Plot 2: Final accuracy by institution
    plt.subplot(2, 2, 2)
    institutions = [m['institution'] for m in final_metrics]
    accuracies = [m['accuracy'] for m in final_metrics]
    
    bars = plt.bar(range(len(institutions)), accuracies, 
                   color=['blue', 'red', 'green'])
    plt.xlabel('Institution')
    plt.ylabel('Final Accuracy')
    plt.title('Final Accuracy by Institution')
    plt.xticks(range(len(institutions)), institutions, rotation=45)
    
    # Add value labels on bars
    for bar, acc in zip(bars, accuracies):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{acc:.3f}', ha='center', va='bottom')
    
    # Plot 3: Loss progression
    plt.subplot(2, 2, 3)
    for i, round_data in enumerate(round_results):
        round_num = round_data['round']
        for j, metric in enumerate(round_data['metrics']):
            plt.plot(round_num, metric['loss'], 'o', 
                    color=colors[j], alpha=0.6, markersize=8)
    
    plt.xlabel('Round')
    plt.ylabel('Loss')
    plt.title('Institution Loss Progression')
    plt.grid(True, alpha=0.3)
    
    # Plot 4: Training samples vs accuracy
    plt.subplot(2, 2, 4)
    samples = [m['train_samples'] for m in final_metrics]
    accuracies = [m['accuracy'] for m in final_metrics]
    
    plt.scatter(samples, accuracies, c=['blue', 'red', 'green'], 
               s=100, alpha=0.7)
    for i, institution in enumerate(institutions):
        plt.annotate(institution, (samples[i], accuracies[i]), 
                    xytext=(5, 5), textcoords='offset points')
    
    plt.xlabel('Training Samples')
    plt.ylabel('Final Accuracy')
    plt.title('Training Samples vs Final Accuracy')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save visualization
    viz_file = "/data/exports/multi_institution_fl_visualization.png"
    plt.savefig(viz_file, dpi=300, bbox_inches='tight')
    print(f"Visualization saved to {viz_file}")

if __name__ == "__main__":
    run_multi_institution_demo() 