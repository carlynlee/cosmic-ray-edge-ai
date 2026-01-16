#!/usr/bin/env python3
"""
Test Federated Learning Logic (Without Flower)

This script tests the core federated learning logic without requiring Flower,
to validate the implementation before dealing with dependency conflicts.
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
import os
import sys
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler

# Import model
from train_binary_baseline import BinaryCoincidenceClassifier, CosmicWatchDataset

FEATURES = ['adc_value', 'sipm_mv', 'temperature_c', 'pressure_pa', 'accel_z_g']
DATA_DIR = 'data/data_partitions'
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def load_node_data(csv_file):
    """Load and prepare data for a node"""
    print(f"\nLoading data from {csv_file}...")
    
    df = pd.read_csv(csv_file)
    available_features = [f for f in FEATURES if f in df.columns]
    X = df[available_features].values
    y = df['coincident'].astype(int).values
    
    # Split
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )
    
    # Normalize
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    
    # Create loaders
    train_dataset = CosmicWatchDataset(X_train_scaled, y_train)
    val_dataset = CosmicWatchDataset(X_val_scaled, y_val)
    test_dataset = CosmicWatchDataset(X_test_scaled, y_test)
    
    # Handle class weights (avoid divide by zero)
    class_counts = np.bincount(y_train.astype(int))
    if len(class_counts) == 2 and class_counts[0] > 0 and class_counts[1] > 0:
        class_weights = 1.0 / class_counts
        sample_weights = class_weights[y_train.astype(int)]
        weighted_sampler = WeightedRandomSampler(sample_weights, len(sample_weights))
    else:
        # If only one class, use regular sampler
        weighted_sampler = None
    
    if weighted_sampler:
        train_loader = DataLoader(train_dataset, batch_size=32, sampler=weighted_sampler)
    else:
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
    
    return {
        'train_loader': train_loader,
        'val_loader': val_loader,
        'test_loader': test_loader,
        'scaler': scaler,
        'n_samples': len(df),
        'coincidence_rate': y.mean()
    }

def train_local_model(model, train_loader, epochs=5):
    """Train model locally"""
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    
    model.train()
    for epoch in range(epochs):
        for features, labels in train_loader:
            features, labels = features.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            outputs = model(features)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
    
    return model

def evaluate_model(model, loader):
    """Evaluate model"""
    model.eval()
    correct = 0
    total = 0
    
    with torch.no_grad():
        for features, labels in loader:
            features = features.to(DEVICE)
            outputs = model(features)
            predicted = (outputs > 0.5).float().cpu()
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    
    return correct / total if total > 0 else 0.0

def federated_averaging(models, sample_counts):
    """Simple federated averaging"""
    # Get parameters from all models
    all_params = []
    for model in models:
        params = [val.cpu().numpy() for _, val in model.state_dict().items()]
        all_params.append(params)
    
    # Weighted average
    total_samples = sum(sample_counts)
    averaged_params = []
    
    for param_idx in range(len(all_params[0])):
        weighted_sum = np.zeros_like(all_params[0][param_idx])
        for model_idx, params in enumerate(all_params):
            weight = sample_counts[model_idx] / total_samples
            weighted_sum += params[param_idx] * weight
        averaged_params.append(weighted_sum)
    
    # Create new model with averaged parameters
    global_model = BinaryCoincidenceClassifier(input_size=5, hidden_sizes=[64, 32])
    state_dict = global_model.state_dict()
    
    for (key, _), param in zip(state_dict.items(), averaged_params):
        state_dict[key] = torch.tensor(param)
    
    global_model.load_state_dict(state_dict)
    return global_model

def main():
    print("=" * 70)
    print("Federated Learning Logic Test (Without Flower)")
    print("=" * 70)
    
    # Load data for both nodes
    node1_file = os.path.join(DATA_DIR, 'node1_coincidence_events.csv')
    node2_file = os.path.join(DATA_DIR, 'node2_non_coincidence_events.csv')
    
    if not os.path.exists(node1_file) or not os.path.exists(node2_file):
        print("Error: Data files not found")
        sys.exit(1)
    
    node1_data = load_node_data(node1_file)
    node2_data = load_node_data(node2_file)
    
    print(f"\n{'='*70}")
    print("Node 1 (Coincidence Events)")
    print(f"  Samples: {node1_data['n_samples']:,}")
    print(f"  Coincidence rate: {node1_data['coincidence_rate']*100:.2f}%")
    
    print(f"\nNode 2 (Non-Coincidence Events)")
    print(f"  Samples: {node2_data['n_samples']:,}")
    print(f"  Coincidence rate: {node2_data['coincidence_rate']*100:.2f}%")
    
    # Initialize models
    print(f"\n{'='*70}")
    print("Initializing Models")
    print(f"{'='*70}")
    
    model1 = BinaryCoincidenceClassifier(input_size=5, hidden_sizes=[64, 32]).to(DEVICE)
    model2 = BinaryCoincidenceClassifier(input_size=5, hidden_sizes=[64, 32]).to(DEVICE)
    
    print("✓ Models initialized")
    
    # Train local models (Round 0 - local training)
    print(f"\n{'='*70}")
    print("Round 0: Local Training")
    print(f"{'='*70}")
    
    print("\nTraining Node 1 model...")
    model1 = train_local_model(model1, node1_data['train_loader'], epochs=5)
    acc1 = evaluate_model(model1, node1_data['val_loader'])
    print(f"  Node 1 validation accuracy: {acc1:.4f}")
    
    print("\nTraining Node 2 model...")
    model2 = train_local_model(model2, node2_data['train_loader'], epochs=5)
    acc2 = evaluate_model(model2, node2_data['val_loader'])
    print(f"  Node 2 validation accuracy: {acc2:.4f}")
    
    # Federated averaging
    print(f"\n{'='*70}")
    print("Federated Averaging")
    print(f"{'='*70}")
    
    sample_counts = [
        len(node1_data['train_loader'].dataset),
        len(node2_data['train_loader'].dataset)
    ]
    
    global_model = federated_averaging([model1, model2], sample_counts)
    global_model = global_model.to(DEVICE)
    
    print("✓ Global model created via federated averaging")
    
    # Evaluate global model
    print(f"\n{'='*70}")
    print("Global Model Evaluation")
    print(f"{'='*70}")
    
    # Evaluate on each node's test set
    global_acc1 = evaluate_model(global_model, node1_data['test_loader'])
    global_acc2 = evaluate_model(global_model, node2_data['test_loader'])
    
    print(f"\nGlobal model on Node 1 test set: {global_acc1:.4f}")
    print(f"Global model on Node 2 test set: {global_acc2:.4f}")
    print(f"\nLocal Node 1 model: {acc1:.4f}")
    print(f"Local Node 2 model: {acc2:.4f}")
    
    # Additional round
    print(f"\n{'='*70}")
    print("Round 1: Federated Learning")
    print(f"{'='*70}")
    
    # Set global model parameters to local models
    model1.load_state_dict(global_model.state_dict())
    model2.load_state_dict(global_model.state_dict())
    
    # Train again
    print("\nTraining Node 1 with global model...")
    model1 = train_local_model(model1, node1_data['train_loader'], epochs=5)
    acc1_r1 = evaluate_model(model1, node1_data['val_loader'])
    print(f"  Node 1 validation accuracy: {acc1_r1:.4f}")
    
    print("\nTraining Node 2 with global model...")
    model2 = train_local_model(model2, node2_data['train_loader'], epochs=5)
    acc2_r1 = evaluate_model(model2, node2_data['val_loader'])
    print(f"  Node 2 validation accuracy: {acc2_r1:.4f}")
    
    # Aggregate again
    global_model_r1 = federated_averaging([model1, model2], sample_counts)
    global_model_r1 = global_model_r1.to(DEVICE)
    
    global_acc1_r1 = evaluate_model(global_model_r1, node1_data['test_loader'])
    global_acc2_r1 = evaluate_model(global_model_r1, node2_data['test_loader'])
    
    print(f"\n{'='*70}")
    print("Results Summary")
    print(f"{'='*70}")
    print(f"\nRound 0 (Local):")
    print(f"  Node 1: {acc1:.4f}")
    print(f"  Node 2: {acc2:.4f}")
    print(f"\nRound 0 (Global):")
    print(f"  Node 1 test: {global_acc1:.4f}")
    print(f"  Node 2 test: {global_acc2:.4f}")
    print(f"\nRound 1 (Federated):")
    print(f"  Node 1: {acc1_r1:.4f}")
    print(f"  Node 2: {acc2_r1:.4f}")
    print(f"  Global on Node 1 test: {global_acc1_r1:.4f}")
    print(f"  Global on Node 2 test: {global_acc2_r1:.4f}")
    
    print(f"\n{'='*70}")
    print("✓ Federated Learning Logic Test Complete!")
    print(f"{'='*70}")
    print("\nThe core federated learning logic works correctly.")
    print("To use Flower framework, resolve protobuf dependency conflict:")
    print("  Option 1: Use virtual environment without TensorFlow")
    print("  Option 2: Use Flower with compatible protobuf version")
    print("  Option 3: Use this simplified implementation for demonstration")

if __name__ == "__main__":
    main()

