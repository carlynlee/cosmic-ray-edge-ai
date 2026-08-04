#!/usr/bin/env python3
"""
Federated Learning Client for Caltech
Connects to Caltech FL Server and participates in federated learning
Note: The FL server runs on the same pod but this client handles Caltech's data
"""

import os
import sys
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array, load_img
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import to_categorical
import pandas as pd
import flwr as fl
from typing import Dict, Tuple, List
import glob
from sklearn.metrics import classification_report

# Configuration
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 3
LEARNING_RATE = 0.001
NUM_CLASSES = 10

# Caltech-specific configuration
INSTITUTION_NAME = os.getenv("INSTITUTION_NAME", "Caltech")
INSTITUTION_SITE = os.getenv("INSTITUTION_SITE", "caltech")
CALTECH_CLUSTERS = [0, 1, 2, 3]  # Caltech's assigned clusters

class CaltechFLClient(fl.client.NumPyClient):
    """Federated Learning Client for Caltech"""
    
    def __init__(self):
        self.institution_name = INSTITUTION_NAME
        self.cluster_ids = CALTECH_CLUSTERS
        self.model = None
        self.x_train, self.y_train = None, None
        self.x_test, self.y_test = None, None
        
        print(f"Initializing {self.institution_name} FL Client...")
        print(f"  Site: {INSTITUTION_SITE}")
        print(f"  Clusters: {self.cluster_ids}")
        
        # Load Caltech-specific data
        self._load_institution_data()
        self._build_model()
    
    def _load_institution_data(self):
        """Load images for Caltech's clusters (training) and all clusters (testing)"""
        print(f"\nLoading data for {self.institution_name}...")
        
        # Load cluster assignments
        cluster_file = "/data/exports/cluster_results.txt"
        if not os.path.exists(cluster_file):
            print(f"Warning: Cluster results not found at {cluster_file}")
            print("Using fallback data loading...")
            return
        
        df = pd.read_csv(cluster_file)
        
        # Step 1: Load ALL clusters for global test set
        print("Loading ALL clusters for global test set...")
        all_images = df['Image_Path'].tolist()
        
        # Load and preprocess ALL images for test set
        all_images_processed = []
        all_labels = []
        
        for img_path in all_images:
            try:
                if not os.path.exists(img_path):
                    continue
                    
                # Load and preprocess image
                img = load_img(img_path, target_size=IMG_SIZE)
                img_array = img_to_array(img)
                img_preprocessed = preprocess_input(img_array)
                
                all_images_processed.append(img_preprocessed)
                
                # Get cluster ID for this image
                cluster_id = df[df['Image_Path'] == img_path]['Cluster'].iloc[0]
                all_labels.append(cluster_id)
                    
            except Exception as e:
                print(f"Error loading {img_path}: {e}")
                continue
        
        if len(all_images_processed) == 0:
            print(f"No valid images loaded")
            return
        
        # Convert to numpy arrays
        X_all = np.array(all_images_processed)
        y_all = np.array(all_labels)
        
        # Split ALL data into train/test (80/20) - this is the global split
        from sklearn.model_selection import train_test_split
        X_train_all, X_test_all, y_train_all, y_test_all = train_test_split(
            X_all, y_all, test_size=0.2, random_state=42, stratify=y_all
        )
        
        # Step 2: Filter training data to only Caltech's clusters
        print(f"Filtering training data for {self.institution_name} clusters: {self.cluster_ids}")
        train_mask = np.isin(y_train_all, self.cluster_ids)
        X_train_filtered = X_train_all[train_mask]
        y_train_filtered = y_train_all[train_mask]
        
        # Convert labels to categorical
        y_train_categorical = to_categorical(y_train_filtered, num_classes=NUM_CLASSES)
        y_test_categorical = to_categorical(y_test_all, num_classes=NUM_CLASSES)
        
        # Store training and test data
        self.x_train = X_train_filtered
        self.y_train = y_train_categorical
        self.x_test = X_test_all  # Global test set with ALL clusters
        self.y_test = y_test_categorical
        
        print(f"{self.institution_name}: {len(self.x_train)} train samples (clusters {self.cluster_ids})")
        print(f"{self.institution_name}: {len(self.x_test)} test samples (ALL clusters 0-9)")
        
        # Print class distribution in test set
        unique_test_classes = np.unique(y_test_all)
        print(f"Test set contains classes: {sorted(unique_test_classes.tolist())}")
    
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
    
    def get_parameters(self, config: Dict) -> List[np.ndarray]:
        """Return current model parameters as a flat list"""
        params = []
        for layer in self.model.layers:
            if layer.trainable_weights:
                weights = layer.get_weights()
                params.extend(weights)  # Flatten the list
        return params
    
    def set_parameters(self, parameters: List[np.ndarray]) -> None:
        """Update model parameters from server"""
        param_idx = 0
        for layer in self.model.layers:
            if layer.trainable_weights:
                num_weights = len(layer.trainable_weights)
                layer_weights = parameters[param_idx:param_idx + num_weights]
                layer.set_weights(layer_weights)
                param_idx += num_weights
    
    def fit(self, parameters: List[np.ndarray], config: Dict) -> Tuple[List[np.ndarray], int, Dict]:
        """Train the model on local Caltech data"""
        print(f"\n[{self.institution_name}] Starting local training...")
        
        # Set parameters from server
        self.set_parameters(parameters)
        
        if self.x_train is None or len(self.x_train) == 0:
            print(f"[{self.institution_name}] No training data available")
            return self.get_parameters({}), 0, {}
        
        # Train the model (NO validation_data - test set is kept separate)
        history = self.model.fit(
            self.x_train, self.y_train,
            batch_size=BATCH_SIZE,
            epochs=EPOCHS,
            verbose=1
        )
        
        # Get updated parameters
        updated_parameters = self.get_parameters({})
        num_samples = len(self.x_train)
        
        metrics = {
            'institution': self.institution_name,
            'train_accuracy': float(history.history['accuracy'][-1]),
            'train_loss': float(history.history['loss'][-1])
        }
        
        print(f"[{self.institution_name}] Training complete: Accuracy={metrics['train_accuracy']:.4f}")
        
        return updated_parameters, num_samples, metrics
    
    def evaluate(self, parameters: List[np.ndarray], config: Dict) -> Tuple[float, int, Dict]:
        """Evaluate the model on global test set (ALL 10 classes)"""
        print(f"\n[{self.institution_name}] Evaluating model on global test set (ALL classes 0-9)...")
        
        # Set parameters from server
        self.set_parameters(parameters)
        
        if self.x_test is None or len(self.x_test) == 0:
            return 0.0, 0, {}
        
        # Evaluate on global test set with all classes
        loss, accuracy = self.model.evaluate(self.x_test, self.y_test, verbose=0)
        num_samples = len(self.x_test)
        
        # Calculate per-class accuracy for all 10 types
        predictions = self.model.predict(self.x_test, verbose=0)
        predicted_classes = np.argmax(predictions, axis=1)
        true_classes = np.argmax(self.y_test, axis=1)
        
        # Calculate per-class accuracy (not F1-score)
        per_class_accuracy = {}
        for class_id in range(NUM_CLASSES):
            # Find samples belonging to this class
            class_mask = (true_classes == class_id)
            if np.sum(class_mask) > 0:
                # Calculate accuracy for this class
                class_correct = np.sum((predicted_classes[class_mask] == class_id))
                class_total = np.sum(class_mask)
                per_class_accuracy[f'class_{class_id}'] = float(class_correct / class_total)
            else:
                per_class_accuracy[f'class_{class_id}'] = 0.0
        
        # Also get classification report for additional metrics
        class_report = classification_report(true_classes, predicted_classes, 
                                             labels=range(NUM_CLASSES), 
                                             output_dict=True, zero_division=0)
        
        metrics = {
            'institution': self.institution_name,
            'site': INSTITUTION_SITE,
            'overall_accuracy': float(accuracy),
            'overall_loss': float(loss),
            'per_class_accuracy': per_class_accuracy,
            'test_samples_per_class': {f'class_{i}': int(np.sum(true_classes == i)) 
                                      for i in range(NUM_CLASSES)},
            'total_test_samples': int(num_samples)
        }
        
        print(f"[{self.institution_name}] Global Evaluation: Accuracy={accuracy:.4f}, Loss={loss:.4f}")
        print(f"[{self.institution_name}] Test samples: {num_samples} (all classes 0-9)")
        print(f"[{self.institution_name}] Per-Class Test Accuracy:")
        for class_id in range(NUM_CLASSES):
            class_acc = per_class_accuracy.get(f'class_{class_id}', 0.0)
            class_samples = metrics.get('test_samples_per_class', {}).get(f'class_{class_id}', 0)
            print(f"  Class {class_id}: {class_acc:.4f} ({class_samples} samples)")
        
        return float(loss), num_samples, metrics

def main():
    """Start the Caltech FL client"""
    print("=" * 60)
    print(f"{INSTITUTION_NAME} FEDERATED LEARNING CLIENT")
    print("Connecting to Caltech FL Server")
    print("=" * 60)
    
    # Get server address from environment
    server_address = os.getenv("FL_SERVER_URL", "caltech-fl-server-service:5000")
    server_host, server_port = server_address.split(":")
    
    print(f"\nConnecting to FL server at {server_host}:{server_port}...")
    
    # Create client
    client = CaltechFLClient()
    
    # Start client
    try:
        fl.client.start_numpy_client(
            server_address=f"{server_host}:{server_port}",
            client=client
        )
        print(f"\n[{INSTITUTION_NAME}] Federated learning complete!")
    except Exception as e:
        print(f"\n[{INSTITUTION_NAME}] Error connecting to server: {e}")
        print("Make sure the FL server is running on the Caltech pod")
        sys.exit(1)

if __name__ == "__main__":
    main()

