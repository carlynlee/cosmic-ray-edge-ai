#!/usr/bin/env python3
"""
Federated Learning Client for Cosmic Ray Event Classification

This client trains models locally on partitioned data and participates in federated learning.
Supports multiple client nodes:
- Node 1: Coincidence events
- Node 2: Non-coincidence events  
- Node 3: CREDO.science data (optional)
"""

import flwr as fl
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
import pandas as pd
import numpy as np
import pickle
import os
import sys
from typing import Dict, List, Tuple, Optional

# Import model architecture
from train_binary_baseline import BinaryCoincidenceClassifier, CosmicWatchDataset
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Configuration
DATA_DIR = 'data/data_partitions'
MODEL_DIR = 'models'
BATCH_SIZE = 32
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Core features (same as baseline model)
FEATURES = [
    'adc_value',
    'sipm_mv',
    'temperature_c',
    'pressure_pa',
    'accel_z_g',
]

class FLClient(fl.client.NumPyClient):
    """Federated Learning Client"""
    
    def __init__(self, node_name: str, csv_file: str, cid: int):
        self.node_name = node_name
        self.csv_file = csv_file
        self.cid = cid
        self.model = None
        self.scaler = None
        self.train_loader = None
        self.val_loader = None
        self.test_loader = None
        
        # Load and prepare data
        self._load_data()
        
        # Initialize model
        self._init_model()
        
    def _load_data(self):
        """Load and prepare data for this client"""
        print(f"\n[{self.node_name}] Loading data from {self.csv_file}...")
        
        if not os.path.exists(self.csv_file):
            print(f"Error: {self.csv_file} not found")
            sys.exit(1)
        
        # Load CSV
        df = pd.read_csv(self.csv_file)
        
        # Extract features (handle missing columns)
        available_features = [f for f in FEATURES if f in df.columns]
        X = df[available_features].values
        
        # Binary label: coincident (1) or not (0)
        y = df['coincident'].astype(int).values
        
        print(f"  Loaded {len(df):,} samples")
        print(f"  Features: {len(available_features)}")
        print(f"  Coincidence events: {y.sum():,} ({100*y.mean():.2f}%)")
        
        # Split data: 70% train, 15% val, 15% test
        from sklearn.model_selection import train_test_split
        
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
        )
        
        # Normalize features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Create datasets
        train_dataset = CosmicWatchDataset(X_train_scaled, y_train)
        val_dataset = CosmicWatchDataset(X_val_scaled, y_val)
        test_dataset = CosmicWatchDataset(X_test_scaled, y_test)
        
        # Create weighted sampler for class imbalance
        class_counts = np.bincount(y_train.astype(int))
        class_weights = 1.0 / class_counts
        sample_weights = class_weights[y_train.astype(int)]
        weighted_sampler = WeightedRandomSampler(sample_weights, len(sample_weights))
        
        self.train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, sampler=weighted_sampler)
        self.val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
        self.test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)
        
        print(f"  Train: {len(X_train):,}, Val: {len(X_val):,}, Test: {len(X_test):,}")
        
    def _init_model(self):
        """Initialize model"""
        self.model = BinaryCoincidenceClassifier(
            input_size=len(FEATURES),
            hidden_sizes=[64, 32]
        ).to(DEVICE)
        
    def get_parameters(self, config: Dict) -> List[np.ndarray]:
        """Return model parameters as numpy arrays"""
        return [val.cpu().numpy() for _, val in self.model.state_dict().items()]
    
    def set_parameters(self, parameters: List[np.ndarray]):
        """Set model parameters from numpy arrays"""
        params_dict = zip(self.model.state_dict().keys(), parameters)
        state_dict = {k: torch.tensor(v) for k, v in params_dict}
        self.model.load_state_dict(state_dict, strict=False)
    
    def fit(self, parameters: List[np.ndarray], config: Dict) -> Tuple[List[np.ndarray], int, Dict]:
        """Train model on local data"""
        # Set parameters from server
        self.set_parameters(parameters)
        
        # Get training config
        epochs = config.get("epochs", 5)
        learning_rate = config.get("learning_rate", 0.001)
        round_num = config.get("round", 0)
        
        # Train model
        criterion = nn.BCELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        
        self.model.train()
        train_loss = 0.0
        
        for epoch in range(epochs):
            for features, labels in self.train_loader:
                features, labels = features.to(DEVICE), labels.to(DEVICE)
                
                optimizer.zero_grad()
                outputs = self.model(features)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item()
        
        train_loss /= len(self.train_loader) * epochs
        
        # Evaluate on validation set
        val_acc = self._evaluate(self.val_loader)
        
        print(f"[{self.node_name}] Round {round_num}: Train Loss: {train_loss:.4f}, Val Acc: {val_acc:.4f}")
        
        # Return updated parameters
        return self.get_parameters({}), len(self.train_loader.dataset), {
            "accuracy": float(val_acc),
            "loss": float(train_loss)
        }
    
    def evaluate(self, parameters: List[np.ndarray], config: Dict) -> Tuple[float, int, Dict]:
        """Evaluate model on local test set"""
        # Set parameters from server
        self.set_parameters(parameters)
        
        # Evaluate on test set
        test_acc = self._evaluate(self.test_loader)
        
        # Calculate additional metrics
        self.model.eval()
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            for features, labels in self.test_loader:
                features = features.to(DEVICE)
                outputs = self.model(features)
                preds = (outputs > 0.5).float().cpu().numpy().astype(int)
                all_preds.extend(preds)
                all_labels.extend(labels.numpy())
        
        precision = precision_score(all_labels, all_preds, zero_division=0)
        recall = recall_score(all_labels, all_preds, zero_division=0)
        f1 = f1_score(all_labels, all_preds, zero_division=0)
        
        round_num = config.get("round", 0)
        print(f"[{self.node_name}] Round {round_num} Test: Acc: {test_acc:.4f}, Prec: {precision:.4f}, Rec: {recall:.4f}, F1: {f1:.4f}")
        
        return float(test_acc), len(self.test_loader.dataset), {
            "accuracy": float(test_acc),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1)
        }
    
    def _evaluate(self, loader: DataLoader) -> float:
        """Evaluate model on a data loader"""
        self.model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for features, labels in loader:
                features = features.to(DEVICE)
                outputs = self.model(features)
                predicted = (outputs > 0.5).float().cpu()
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        
        return correct / total if total > 0 else 0.0

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Federated Learning Client')
    parser.add_argument('--node', type=str, required=True, choices=['node1', 'node2', 'node3'],
                       help='Node identifier (node1=coincidence, node2=non-coincidence, node3=CREDO)')
    parser.add_argument('--server', type=str, default='localhost:8080',
                       help='Server address (default: localhost:8080)')
    parser.add_argument('--cid', type=int, default=0,
                       help='Client ID (default: 0)')
    
    args = parser.parse_args()
    
    # Map node to CSV file
    node_map = {
        'node1': os.path.join(DATA_DIR, 'node1_coincidence_events.csv'),
        'node2': os.path.join(DATA_DIR, 'node2_non_coincidence_events.csv'),
        'node3': os.path.join(DATA_DIR, 'node3_credo_data.csv'),  # May not exist
    }
    
    csv_file = node_map[args.node]
    node_name = args.node.upper()
    
    print("=" * 70)
    print(f"Federated Learning Client - {node_name}")
    print("=" * 70)
    print(f"Server: {args.server}")
    print(f"Client ID: {args.cid}")
    print()
    
    # Create client
    client = FLClient(node_name, csv_file, args.cid)
    
    # Start client
    print(f"Connecting to server at {args.server}...")
    fl.client.start_numpy_client(
        server_address=args.server,
        client=client
    )
    
    print(f"\n✓ Client {node_name} disconnected")

if __name__ == "__main__":
    main()

