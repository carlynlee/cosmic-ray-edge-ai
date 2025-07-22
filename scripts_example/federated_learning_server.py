#!/usr/bin/env python3
"""
Federated Learning Server for CREDO Image Classification
Coordinates training across multiple device clients
"""

import flwr as fl
import tensorflow as tf
from tensorflow.keras.applications.resnet50 import ResNet50
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.utils import to_categorical
import numpy as np
import json
import os
from collections import OrderedDict

# Configuration
IMG_SIZE = (224, 224)
NUM_CLASSES = 10
LEARNING_RATE = 0.001

class CREDOImageServer(fl.server.strategy.FedAvg):
    """Federated Learning Server for CREDO Image Classification"""
    
    def __init__(self):
        # Build the global model
        self.global_model = self._build_global_model()
        
        # Initialize FedAvg strategy
        super().__init__(
            min_fit_clients=2,  # Minimum number of clients to train
            min_evaluate_clients=2,  # Minimum number of clients to evaluate
            min_available_clients=2,  # Minimum number of available clients
            evaluate_fn=self.evaluate_fn,
            on_fit_config_fn=self.get_fit_config,
            on_evaluate_config_fn=self.get_evaluate_config,
            initial_parameters=fl.common.ndarrays_to_parameters(
                [val.numpy() for val in self.global_model.trainable_weights]
            )
        )
    
    def _build_global_model(self):
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
    
    def get_fit_config(self, server_round):
        """Return training configuration for clients"""
        return {
            "epochs": 5,
            "batch_size": 32,
            "learning_rate": LEARNING_RATE,
        }
    
    def get_evaluate_config(self, server_round):
        """Return evaluation configuration for clients"""
        return {
            "batch_size": 32,
        }
    
    def evaluate_fn(self, server_round, parameters, config):
        """Evaluate the global model"""
        # Set parameters to global model
        for param, val in zip(self.global_model.trainable_weights, parameters):
            param.assign(val)
        
        # For now, return dummy evaluation
        # In a real scenario, you'd evaluate on a test set
        loss = 0.0
        accuracy = 0.0
        
        return loss, {"accuracy": accuracy}

def start_federated_server():
    """Start the federated learning server"""
    print("Starting Federated Learning Server for CREDO Image Classification")
    
    # Define server configuration
    server_config = fl.server.ServerConfig(
        num_rounds=10,  # Number of federated learning rounds
    )
    
    # Start server
    fl.server.start_server(
        server_address="0.0.0.0:8080",
        config=server_config,
        strategy=CREDOImageServer()
    )

if __name__ == "__main__":
    start_federated_server() 