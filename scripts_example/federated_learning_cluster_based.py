#!/usr/bin/env python3
"""
Federated Learning for CREDO Image Classification
Using image clusters as federated clients instead of device IDs
"""

import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array, load_img
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import to_categorical
import flwr as fl
import pandas as pd
import glob
import json
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

# Configuration
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 5
LEARNING_RATE = 0.001
NUM_CLASSES = 10  # Number of clusters

class CREDOClusterClient(fl.client.NumPyClient):
    """Federated Learning Client based on image clusters"""
    
    def __init__(self, cluster_id, images_dir="/data/images"):
        self.cluster_id = cluster_id
        self.images_dir = images_dir
        self.model = None
        self.x_train, self.y_train = None, None
        self.x_test, self.y_test = None, None
        
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
        """Build the federated learning model"""
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
    
    def get_parameters(self, config):
        """Get model parameters for federated learning"""
        return [val.numpy() for val in self.model.trainable_weights]
    
    def set_parameters(self, parameters):
        """Set model parameters from federated learning"""
        for param, val in zip(self.model.trainable_weights, parameters):
            param.assign(val)
    
    def fit(self, parameters, config):
        """Train the model on local data"""
        self.set_parameters(parameters)
        
        if self.x_train is None or len(self.x_train) == 0:
            print(f"No training data for cluster {self.cluster_id}")
            return self.get_parameters(config), len(self.x_train) if self.x_train is not None else 0, {}
        
        # Train the model
        history = self.model.fit(
            self.x_train, self.y_train,
            batch_size=BATCH_SIZE,
            epochs=EPOCHS,
            validation_data=(self.x_test, self.y_test),
            verbose=1
        )
        
        # Save training history
        history_file = f"/data/exports/cluster_{self.cluster_id}_training_history.json"
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        
        with open(history_file, 'w') as f:
            json.dump(history.history, f)
        
        return self.get_parameters(config), len(self.x_train), {
            "accuracy": float(history.history['accuracy'][-1]),
            "loss": float(history.history['loss'][-1]),
            "val_accuracy": float(history.history['val_accuracy'][-1]),
            "val_loss": float(history.history['val_loss'][-1])
        }
    
    def evaluate(self, parameters, config):
        """Evaluate the model on local test data"""
        self.set_parameters(parameters)
        
        if self.x_test is None or len(self.x_test) == 0:
            return 0.0, len(self.x_test) if self.x_test is not None else 0, {}
        
        loss, accuracy = self.model.evaluate(self.x_test, self.y_test, verbose=0)
        
        return loss, len(self.x_test), {"accuracy": accuracy}

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

def start_cluster_based_federated_learning():
    """Start federated learning with cluster-based clients"""
    print("Starting Cluster-Based Federated Learning for CREDO Image Classification")
    
    # Get cluster distribution
    cluster_counts = get_cluster_distribution()
    
    if not cluster_counts:
        print("No cluster data available!")
        return
    
    # Create clients for each cluster with sufficient data (at least 5 images)
    clients = []
    for cluster_id, count in cluster_counts.items():
        if count >= 5:  # Minimum images per cluster
            client = CREDOClusterClient(cluster_id)
            if client.x_train is not None and len(client.x_train) > 0:
                clients.append(client)
    
    print(f"Created {len(clients)} valid cluster clients")
    
    if len(clients) == 0:
        print("No valid clients created!")
        return
    
    # For demonstration, we'll simulate federated learning with one client
    # In a real scenario, you'd run multiple clients on different machines
    
    print("Starting federated learning simulation...")
    
    # Use the first client as an example
    client = clients[0]
    
    # Start Flower client
    fl.client.start_numpy_client(
        server_address="localhost:8080",
        client=client
    )

if __name__ == "__main__":
    start_cluster_based_federated_learning() 