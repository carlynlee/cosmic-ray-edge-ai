#!/usr/bin/env python3
"""
Train Baseline Model for Energy Level Classification

This script trains baseline models on partitioned CosmicWatch data for federated learning.
"""

import os
import sys
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import pickle
import json

# Configuration
DATA_DIR = 'data/data_partitions'
MODEL_DIR = 'models'
BATCH_SIZE = 32
EPOCHS = 20
LEARNING_RATE = 0.001

# Features for training
FEATURES = [
    'adc_value', 'sipm_mv', 'temperature_c', 'pressure_pa',
    'accel_x_g', 'accel_y_g', 'accel_z_g',
    'gyro_x_degs', 'gyro_y_degs', 'gyro_z_degs'
]

# Energy level classes
CLASSES = ['low', 'medium', 'high']
NUM_CLASSES = len(CLASSES)

class CosmicWatchDataset(Dataset):
    """Dataset for CosmicWatch data"""
    def __init__(self, features, labels):
        self.features = torch.FloatTensor(features)
        self.labels = torch.LongTensor(labels)
    
    def __len__(self):
        return len(self.features)
    
    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]

class EnergyClassifier(nn.Module):
    """Simple MLP for energy level classification"""
    def __init__(self, input_size=10, hidden_sizes=[128, 64], num_classes=3):
        super(EnergyClassifier, self).__init__()
        
        layers = []
        prev_size = input_size
        
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(prev_size, hidden_size))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.2))
            prev_size = hidden_size
        
        layers.append(nn.Linear(prev_size, num_classes))
        self.model = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.model(x)

def load_data(csv_file):
    """Load and prepare data from CSV"""
    print(f"Loading data from {csv_file}...")
    df = pd.read_csv(csv_file)
    
    # Extract features
    X = df[FEATURES].values
    
    # Extract labels (energy_level)
    label_map = {'low': 0, 'medium': 1, 'high': 2}
    y = df['energy_level'].map(label_map).values
    
    print(f"  Loaded {len(df):,} samples")
    print(f"  Features: {X.shape[1]}")
    print(f"  Classes: {np.bincount(y)}")
    
    return X, y

def train_model(model, train_loader, val_loader, epochs, device):
    """Train the model"""
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    best_val_acc = 0.0
    train_losses = []
    val_accuracies = []
    
    print(f"\nTraining on {device}...")
    print(f"Epochs: {epochs}, Batch size: {BATCH_SIZE}, Learning rate: {LEARNING_RATE}")
    
    for epoch in range(epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        
        for features, labels in train_loader:
            features, labels = features.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(features)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
        
        train_loss /= len(train_loader)
        train_losses.append(train_loss)
        
        # Validation phase
        model.eval()
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for features, labels in val_loader:
                features, labels = features.to(device), labels.to(device)
                outputs = model(features)
                _, predicted = torch.max(outputs.data, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
        
        val_acc = val_correct / val_total
        val_accuracies.append(val_acc)
        
        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
        
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"Epoch {epoch+1}/{epochs}: Train Loss: {train_loss:.4f}, Val Acc: {val_acc:.4f}")
    
    print(f"\n✓ Training complete! Best validation accuracy: {best_val_acc:.4f}")
    return train_losses, val_accuracies, best_val_acc

def evaluate_model(model, test_loader, device):
    """Evaluate model on test set"""
    model.eval()
    all_preds = []
    all_labels = []
    
    with torch.no_grad():
        for features, labels in test_loader:
            features = features.to(device)
            outputs = model(features)
            _, predicted = torch.max(outputs.data, 1)
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.numpy())
    
    accuracy = accuracy_score(all_labels, all_preds)
    report = classification_report(all_labels, all_preds, target_names=CLASSES)
    cm = confusion_matrix(all_labels, all_preds)
    
    return accuracy, report, cm

def main():
    print("=" * 60)
    print("Baseline Model Training for Energy Level Classification")
    print("=" * 60)
    
    # Check for data files
    node1_file = os.path.join(DATA_DIR, 'node1_coincidence_events.csv')
    node2_file = os.path.join(DATA_DIR, 'node2_non_coincidence_events.csv')
    
    if not os.path.exists(node1_file) or not os.path.exists(node2_file):
        print(f"Error: Data files not found in {DATA_DIR}")
        print("Please run analyze_and_partition_data.py first")
        sys.exit(1)
    
    # Create model directory
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nUsing device: {device}")
    
    results = {}
    
    # Train models on each partition
    for node_name, csv_file in [('Node1_Coincidence', node1_file), ('Node2_NonCoincidence', node2_file)]:
        print(f"\n{'='*60}")
        print(f"Training {node_name} Model")
        print(f"{'='*60}")
        
        # Load data
        X, y = load_data(csv_file)
        
        # Split data
        X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
        X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)
        
        print(f"\nData split:")
        print(f"  Train: {len(X_train):,} samples")
        print(f"  Validation: {len(X_val):,} samples")
        print(f"  Test: {len(X_test):,} samples")
        
        # Normalize features
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_val = scaler.transform(X_val)
        X_test = scaler.transform(X_test)
        
        # Create datasets
        train_dataset = CosmicWatchDataset(X_train, y_train)
        val_dataset = CosmicWatchDataset(X_val, y_val)
        test_dataset = CosmicWatchDataset(X_test, y_test)
        
        train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
        test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)
        
        # Create model
        model = EnergyClassifier(input_size=len(FEATURES), hidden_sizes=[128, 64], num_classes=NUM_CLASSES)
        model = model.to(device)
        
        print(f"\nModel architecture:")
        print(model)
        
        # Train model
        train_losses, val_accuracies, best_val_acc = train_model(model, train_loader, val_loader, EPOCHS, device)
        
        # Evaluate on test set
        test_acc, report, cm = evaluate_model(model, test_loader, device)
        
        print(f"\n{'='*60}")
        print(f"{node_name} Model Results")
        print(f"{'='*60}")
        print(f"Test Accuracy: {test_acc:.4f}")
        print(f"\nClassification Report:")
        print(report)
        print(f"\nConfusion Matrix:")
        print(cm)
        
        # Save model
        model_path = os.path.join(MODEL_DIR, f'{node_name.lower()}_model.pth')
        scaler_path = os.path.join(MODEL_DIR, f'{node_name.lower()}_scaler.pkl')
        
        torch.save(model.state_dict(), model_path)
        with open(scaler_path, 'wb') as f:
            pickle.dump(scaler, f)
        
        print(f"\n✓ Model saved to: {model_path}")
        print(f"✓ Scaler saved to: {scaler_path}")
        
        # Save results
        results[node_name] = {
            'test_accuracy': float(test_acc),
            'best_val_accuracy': float(best_val_acc),
            'train_samples': len(X_train),
            'val_samples': len(X_val),
            'test_samples': len(X_test),
            'confusion_matrix': cm.tolist()
        }
    
    # Save summary
    summary_path = os.path.join(MODEL_DIR, 'training_summary.json')
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print("Training Summary")
    print(f"{'='*60}")
    for node_name, result in results.items():
        print(f"{node_name}: Test Accuracy = {result['test_accuracy']:.4f}")
    
    print(f"\n✓ Summary saved to: {summary_path}")
    print(f"\n✓ All models saved to: {MODEL_DIR}/")
    print("\nNext steps:")
    print("  1. Review model performance")
    print("  2. Proceed to Day 5-6: Federated Learning Implementation")
    print("  3. Use models for federated learning aggregation")

if __name__ == "__main__":
    main()

