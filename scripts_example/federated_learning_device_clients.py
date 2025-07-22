#!/usr/bin/env python3
"""
Federated Learning for CREDO Image Classification
Each device ID becomes a client that trains on its own images
"""

import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.resnet50 import ResNet50, preprocess_input
from tensorflow.keras.preprocessing.image import img_to_array, load_img
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import to_categorical
import flwr as fl
from collections import OrderedDict
import glob
import json
import pickle
from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

# Configuration
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 5
LEARNING_RATE = 0.001
NUM_CLASSES = 10  # Number of clusters from previous analysis

class CREDOImageClient(fl.client.NumPyClient):
    """Federated Learning Client for CREDO Image Classification"""
    
    def __init__(self, device_id, images_dir="/data/images"):
        self.device_id = device_id
        self.images_dir = images_dir
        self.model = None
        self.x_train, self.y_train = None, None
        self.x_test, self.y_test = None, None
        
        # Load device-specific data
        self._load_device_data()
        self._build_model()
    
    def _load_device_data(self):
        """Load images specific to this device ID"""
        print(f"Loading data for device {self.device_id}")
        
        # Find all images for this device
        device_pattern = f"*{self.device_id}*"
        device_images = []
        
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
            device_images.extend(glob.glob(os.path.join(self.images_dir, '**', device_pattern + ext), recursive=True))
            device_images.extend(glob.glob(os.path.join(self.images_dir, '**', device_pattern + ext.upper()), recursive=True))
        
        print(f"Found {len(device_images)} images for device {self.device_id}")
        
        if len(device_images) == 0:
            print(f"No images found for device {self.device_id}")
            return
        
        # Load cluster assignments
        cluster_file = "/data/exports/cluster_results.txt"
        if os.path.exists(cluster_file):
            df = pd.read_csv(cluster_file)
            # Create mapping from image path to cluster
            path_to_cluster = dict(zip(df['Image_Path'], df['Cluster']))
        else:
            print("Cluster results not found, using random labels")
            path_to_cluster = {}
        
        # Load and preprocess images
        images = []
        labels = []
        
        for img_path in device_images:
            try:
                # Load and preprocess image
                img = load_img(img_path, target_size=IMG_SIZE)
                img_array = img_to_array(img)
                img_preprocessed = preprocess_input(img_array)
                
                images.append(img_preprocessed)
                
                # Get cluster label
                if img_path in path_to_cluster:
                    labels.append(path_to_cluster[img_path])
                else:
                    labels.append(np.random.randint(0, NUM_CLASSES))
                    
            except Exception as e:
                print(f"Error loading {img_path}: {e}")
                continue
        
        if len(images) == 0:
            print(f"No valid images loaded for device {self.device_id}")
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
        
        print(f"Device {self.device_id}: {len(self.x_train)} train, {len(self.x_test)} test samples")
    
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
        print(f"Model built for device {self.device_id}")
    
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
            print(f"No training data for device {self.device_id}")
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
        history_file = f"/data/exports/device_{self.device_id}_training_history.json"
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

def get_device_ids():
    """Extract unique device IDs from image filenames"""
    images_dir = "/data/images"
    device_ids = set()
    
    for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
        for img_path in glob.glob(os.path.join(images_dir, '**', ext), recursive=True):
            # Extract device ID from filename
            filename = os.path.basename(img_path)
            # Assuming device ID is in filename, adjust pattern as needed
            if '_' in filename:
                device_id = filename.split('_')[0]
                device_ids.add(device_id)
    
    return list(device_ids)

def start_federated_learning():
    """Start federated learning with device-based clients"""
    print("Starting Federated Learning for CREDO Image Classification")
    
    # Get device IDs
    device_ids = get_device_ids()
    print(f"Found {len(device_ids)} device IDs: {device_ids[:10]}...")  # Show first 10
    
    if len(device_ids) == 0:
        print("No device IDs found!")
        return
    
    # Create clients for each device
    clients = []
    for device_id in device_ids:
        client = CREDOImageClient(device_id)
        if client.x_train is not None and len(client.x_train) > 0:
            clients.append(client)
    
    print(f"Created {len(clients)} valid clients")
    
    if len(clients) == 0:
        print("No valid clients created!")
        return
    
    # Start federated learning
    # For now, we'll simulate federated learning with one client
    # In a real scenario, you'd run this on multiple machines
    
    print("Starting federated learning simulation...")
    
    # Use the first client as an example
    client = clients[0]
    
    # Start Flower client
    fl.client.start_numpy_client(
        server_address="localhost:8080",
        client=client
    )

if __name__ == "__main__":
    start_federated_learning() 