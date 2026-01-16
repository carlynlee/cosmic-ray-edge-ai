#!/usr/bin/env python3
"""
Federated Learning Client for Cosmic Ray Event Classification

Standalone FL client that trains models locally and participates in federated learning.
Uses HTTP/JSON for communication (no Flower dependency).

This client:
- Loads local data partition
- Trains model locally
- Sends parameters to server
- Receives global model from server
- Participates in multiple FL rounds
"""

import json
import time
import requests
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
import pandas as pd
import numpy as np
import os
import sys
from typing import Dict, List, Tuple
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# Import model architecture
from train_binary_baseline import BinaryCoincidenceClassifier, CosmicWatchDataset

# Configuration
DATA_DIR = 'data/data_partitions'
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

class FederatedLearningClient:
    """Federated Learning Client"""
    
    def __init__(self, node_name: str, csv_file: str, server_url: str, client_id: str):
        self.node_name = node_name
        self.csv_file = csv_file
        self.server_url = server_url
        self.client_id = client_id
        self.model = None
        self.scaler = None
        self.train_loader = None
        self.val_loader = None
        self.test_loader = None
        self.current_round = 0
        
        # Load and prepare data
        self._load_data()
        
        # Initialize model
        self._init_model()
        
        # Register with server
        self._register()
    
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
        if len(class_counts) == 2 and class_counts[0] > 0 and class_counts[1] > 0:
            class_weights = 1.0 / class_counts
            sample_weights = class_weights[y_train.astype(int)]
            weighted_sampler = WeightedRandomSampler(sample_weights, len(sample_weights))
        else:
            weighted_sampler = None
        
        if weighted_sampler:
            self.train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, sampler=weighted_sampler)
        else:
            self.train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
        self.val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
        self.test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)
        
        print(f"  Train: {len(X_train):,}, Val: {len(X_val):,}, Test: {len(X_test):,}")
    
    def _init_model(self):
        """Initialize model"""
        self.model = BinaryCoincidenceClassifier(
            input_size=len(FEATURES),
            hidden_sizes=[64, 32]
        ).to(DEVICE)
    
    def _register(self):
        """Register with FL server"""
        try:
            response = requests.post(
                f"{self.server_url}/register",
                json={
                    'client_id': self.client_id,
                    'node_name': self.node_name,
                    'sample_count': len(self.train_loader.dataset)
                },
                timeout=5
            )
            if response.status_code == 200:
                print(f"✓ Registered with server as {self.client_id}")
            else:
                print(f"Warning: Registration failed: {response.status_code}")
        except Exception as e:
            print(f"Error registering with server: {e}")
            sys.exit(1)
    
    def get_parameters(self) -> List[np.ndarray]:
        """Get model parameters as numpy arrays"""
        return [val.cpu().numpy() for _, val in self.model.state_dict().items()]
    
    def set_parameters(self, parameters: List[np.ndarray]):
        """Set model parameters from numpy arrays"""
        state_dict = self.model.state_dict()
        param_list = list(state_dict.keys())
        
        for i, key in enumerate(param_list):
            if i < len(parameters):
                state_dict[key] = torch.tensor(parameters[i])
        
        self.model.load_state_dict(state_dict)
    
    def train_local(self, epochs: int = 5, learning_rate: float = 0.001) -> Dict:
        """Train model locally"""
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
        
        return {
            'loss': float(train_loss),
            'accuracy': float(val_acc)
        }
    
    def evaluate(self) -> Dict:
        """Evaluate model on test set"""
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
        
        return {
            'accuracy': float(test_acc),
            'precision': float(precision),
            'recall': float(recall),
            'f1': float(f1)
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
    
    def get_global_model(self, round_num: int) -> bool:
        """Get global model from server"""
        try:
            response = requests.post(
                f"{self.server_url}/get_global_model",
                json={
                    'client_id': self.client_id,
                    'round': round_num
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    parameters = data.get('parameters', [])
                    # Convert lists back to numpy arrays
                    params_np = [np.array(p) for p in parameters]
                    self.set_parameters(params_np)
                    return True
            return False
        except Exception as e:
            print(f"Error getting global model: {e}")
            return False
    
    def submit_parameters(self, round_num: int) -> bool:
        """Submit local parameters to server"""
        try:
            parameters = self.get_parameters()
            # Convert numpy arrays to lists for JSON
            params_list = [p.tolist() for p in parameters]
            
            response = requests.post(
                f"{self.server_url}/submit_params",
                json={
                    'client_id': self.client_id,
                    'round': round_num,
                    'parameters': params_list,
                    'sample_count': len(self.train_loader.dataset)
                },
                timeout=10
            )
            
            return response.status_code == 200
        except Exception as e:
            print(f"Error submitting parameters: {e}")
            return False
    
    def submit_metrics(self, round_num: int, metrics: Dict):
        """Submit training metrics to server"""
        try:
            requests.post(
                f"{self.server_url}/submit_metrics",
                json={
                    'client_id': self.client_id,
                    'round': round_num,
                    'metrics': metrics
                },
                timeout=5
            )
        except Exception as e:
            print(f"Error submitting metrics: {e}")
    
    def run_fl_round(self, round_num: int, epochs: int = 5) -> Dict:
        """Run one federated learning round"""
        print(f"\n[{self.node_name}] Round {round_num}")
        print(f"{'─'*70}")
        
        # Get global model from server
        print("  Getting global model from server...")
        if not self.get_global_model(round_num):
            print("  Warning: Failed to get global model, using local model")
        
        # Train locally
        print("  Training locally...")
        train_metrics = self.train_local(epochs=epochs)
        print(f"  Train Loss: {train_metrics['loss']:.4f}, Val Acc: {train_metrics['accuracy']:.4f}")
        
        # Submit parameters
        print("  Submitting parameters to server...")
        if self.submit_parameters(round_num):
            print("  ✓ Parameters submitted")
        else:
            print("  ✗ Failed to submit parameters")
        
        # Evaluate
        test_metrics = self.evaluate()
        print(f"  Test Acc: {test_metrics['accuracy']:.4f}, F1: {test_metrics['f1']:.4f}")
        
        # Submit metrics
        self.submit_metrics(round_num, {**train_metrics, **test_metrics})
        
        return {**train_metrics, **test_metrics}

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Federated Learning Client')
    parser.add_argument('--node', type=str, required=True, choices=['node1', 'node2', 'node3'],
                       help='Node identifier (node1=coincidence, node2=non-coincidence, node3=CREDO)')
    parser.add_argument('--server', type=str, default='http://localhost:8080',
                       help='Server URL (default: http://localhost:8080)')
    parser.add_argument('--client-id', type=str, default=None,
                       help='Client ID (default: auto-generated from node)')
    parser.add_argument('--rounds', type=int, default=5,
                       help='Number of FL rounds (default: 5)')
    parser.add_argument('--epochs', type=int, default=5,
                       help='Epochs per round (default: 5)')
    
    args = parser.parse_args()
    
    # Map node to CSV file
    node_map = {
        'node1': os.path.join(DATA_DIR, 'node1_coincidence_events.csv'),
        'node2': os.path.join(DATA_DIR, 'node2_non_coincidence_events.csv'),
        'node3': os.path.join(DATA_DIR, 'node3_credo_data.csv'),  # May not exist
    }
    
    csv_file = node_map[args.node]
    node_name = args.node.upper()
    client_id = args.client_id or f"{args.node}_{int(time.time())}"
    
    print("=" * 70)
    print(f"Federated Learning Client - {node_name}")
    print("=" * 70)
    print(f"Server: {args.server}")
    print(f"Client ID: {client_id}")
    print(f"Rounds: {args.rounds}")
    print()
    
    # Create client
    client = FederatedLearningClient(node_name, csv_file, args.server, client_id)
    
    # Run FL rounds
    results = []
    for round_num in range(1, args.rounds + 1):
        try:
            round_metrics = client.run_fl_round(round_num, epochs=args.epochs)
            results.append({
                'round': round_num,
                'metrics': round_metrics
            })
            
            # Wait a bit between rounds
            if round_num < args.rounds:
                time.sleep(2)
        except KeyboardInterrupt:
            print("\n\nStopping client...")
            break
        except Exception as e:
            print(f"\nError in round {round_num}: {e}")
            break
    
    # Final evaluation
    print(f"\n{'='*70}")
    print(f"Final Results - {node_name}")
    print(f"{'='*70}")
    final_metrics = client.evaluate()
    print(f"Final Test Accuracy: {final_metrics['accuracy']:.4f}")
    print(f"Final Test F1: {final_metrics['f1']:.4f}")
    
    print(f"\n✓ Client {node_name} completed")

if __name__ == "__main__":
    main()




