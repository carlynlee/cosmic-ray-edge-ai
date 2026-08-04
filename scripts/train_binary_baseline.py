#!/usr/bin/env python3
"""
Train Binary Baseline Model for Coincidence Prediction

This script trains a binary classifier to predict coincidence events (high-energy muons).
Baseline model for Day 3-4, ready for federated learning.
"""

import os
import sys
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, roc_curve, confusion_matrix, classification_report
import pickle
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Configuration
DATA_DIR = 'data/data_partitions'
MODEL_DIR = 'models'
BATCH_SIZE = 32
EPOCHS = 100
LEARNING_RATE = 0.001
EARLY_STOPPING_PATIENCE = 10

# Core features (can add more if needed)
FEATURES = [
    'adc_value',      # Primary energy proxy
    'sipm_mv',       # Energy-related
    'temperature_c', # Environmental
    'pressure_pa',   # Environmental
    # Motion features (optional - can be removed if not helpful)
    'accel_z_g',     # Vertical acceleration
]

class CosmicWatchDataset(Dataset):
    """Dataset for CosmicWatch binary classification"""
    def __init__(self, features, labels):
        self.features = torch.FloatTensor(features)
        self.labels = torch.FloatTensor(labels)
    
    def __len__(self):
        return len(self.features)
    
    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]

class BinaryCoincidenceClassifier(nn.Module):
    """MLP for binary classification (coincidence prediction)"""
    def __init__(self, input_size=5, hidden_sizes=[64, 32]):
        super(BinaryCoincidenceClassifier, self).__init__()
        
        layers = []
        prev_size = input_size
        
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(prev_size, hidden_size))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.3))
            prev_size = hidden_size
        
        # Binary output
        layers.append(nn.Linear(prev_size, 1))
        layers.append(nn.Sigmoid())
        self.model = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.model(x).squeeze()

def load_and_combine_data():
    """Load and combine data from both partitions"""
    print("Loading data from partitions...")
    
    node1_file = os.path.join(DATA_DIR, 'node1_coincidence_events.csv')
    node2_file = os.path.join(DATA_DIR, 'node2_non_coincidence_events.csv')
    
    if not os.path.exists(node1_file) or not os.path.exists(node2_file):
        print(f"Error: Data files not found in {DATA_DIR}")
        print("Please run analyze_and_partition_data.py first")
        sys.exit(1)
    
    # Load both partitions
    df1 = pd.read_csv(node1_file)
    df2 = pd.read_csv(node2_file)
    
    # Combine
    df = pd.concat([df1, df2], ignore_index=True)
    
    print(f"  Node 1 (coincidence): {len(df1):,} samples")
    print(f"  Node 2 (non-coincidence): {len(df2):,} samples")
    print(f"  Total: {len(df):,} samples")
    
    # Extract features (handle missing columns)
    available_features = [f for f in FEATURES if f in df.columns]
    missing_features = [f for f in FEATURES if f not in df.columns]
    
    if missing_features:
        print(f"  Warning: Missing features {missing_features}, using available: {available_features}")
    
    X = df[available_features].values
    
    # Binary label: coincident (1) or not (0)
    y = df['coincident'].astype(int).values
    
    print(f"  Features: {len(available_features)}")
    print(f"  Coincidence events: {y.sum():,} ({100*y.mean():.2f}%)")
    print(f"  Non-coincidence events: {(1-y).sum():,} ({100*(1-y.mean()):.2f}%)")
    
    return X, y, available_features

def create_weighted_sampler(labels):
    """Create weighted sampler for class imbalance"""
    class_counts = np.bincount(labels.astype(int))
    class_weights = 1.0 / class_counts
    sample_weights = class_weights[labels.astype(int)]
    return WeightedRandomSampler(sample_weights, len(sample_weights))

def train_model(model, train_loader, val_loader, epochs, device):
    """Train the model with early stopping"""
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    best_val_loss = float('inf')
    best_val_acc = 0.0
    patience_counter = 0
    train_losses = []
    val_losses = []
    val_accuracies = []
    
    print(f"\nTraining on {device}...")
    print(f"Epochs: {epochs}, Batch size: {BATCH_SIZE}, Learning rate: {LEARNING_RATE}")
    print(f"Early stopping patience: {EARLY_STOPPING_PATIENCE}")
    
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
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for features, labels in val_loader:
                features, labels = features.to(device), labels.to(device)
                outputs = model(features)
                loss = criterion(outputs, labels)
                val_loss += loss.item()
                
                # Binary predictions (threshold 0.5)
                predicted = (outputs > 0.5).float()
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
        
        val_loss /= len(val_loader)
        val_acc = val_correct / val_total
        val_losses.append(val_loss)
        val_accuracies.append(val_acc)
        
        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_val_acc = val_acc
            patience_counter = 0
            # Save best model
            best_model_state = model.state_dict().copy()
        else:
            patience_counter += 1
        
        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"Epoch {epoch+1}/{epochs}: Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}")
        
        if patience_counter >= EARLY_STOPPING_PATIENCE:
            print(f"\nEarly stopping at epoch {epoch+1}")
            model.load_state_dict(best_model_state)
            break
    
    print(f"\n✓ Training complete! Best validation accuracy: {best_val_acc:.4f}")
    return train_losses, val_losses, val_accuracies, best_val_acc

def evaluate_model(model, test_loader, device):
    """Evaluate model on test set"""
    model.eval()
    all_preds = []
    all_probs = []
    all_labels = []
    
    with torch.no_grad():
        for features, labels in test_loader:
            features = features.to(device)
            outputs = model(features)
            probs = outputs.cpu().numpy()
            preds = (probs > 0.5).astype(int)
            
            all_preds.extend(preds)
            all_probs.extend(probs)
            all_labels.extend(labels.numpy())
    
    all_labels = np.array(all_labels)
    all_preds = np.array(all_preds)
    all_probs = np.array(all_probs)
    
    # Calculate metrics
    accuracy = accuracy_score(all_labels, all_preds)
    precision = precision_score(all_labels, all_preds, zero_division=0)
    recall = recall_score(all_labels, all_preds, zero_division=0)
    f1 = f1_score(all_labels, all_preds, zero_division=0)
    roc_auc = roc_auc_score(all_labels, all_probs)
    
    cm = confusion_matrix(all_labels, all_preds)
    report = classification_report(all_labels, all_preds, target_names=['Non-coincidence', 'Coincidence'])
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'roc_auc': roc_auc,
        'confusion_matrix': cm,
        'classification_report': report,
        'predictions': all_preds,
        'probabilities': all_probs,
        'labels': all_labels
    }

def plot_training_curves(train_losses, val_losses, val_accuracies, output_dir):
    """Plot training curves"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    
    epochs = range(1, len(train_losses) + 1)
    
    ax1.plot(epochs, train_losses, 'b-', label='Train Loss')
    ax1.plot(epochs, val_losses, 'r-', label='Val Loss')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Loss')
    ax1.set_title('Training and Validation Loss')
    ax1.legend()
    ax1.grid(True)
    
    ax2.plot(epochs, val_accuracies, 'g-', label='Val Accuracy')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Accuracy')
    ax2.set_title('Validation Accuracy')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'training_curves.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✓ Saved training curves: {output_file}")

def plot_roc_curve(labels, probs, roc_auc, output_dir):
    """Plot ROC curve"""
    # Flatten probabilities if needed
    if probs.ndim > 1:
        probs = probs.flatten()
    fpr, tpr, _ = roc_curve(labels, probs)
    
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, 'b-', linewidth=2, label=f'ROC Curve (AUC = {roc_auc:.3f})')
    plt.plot([0, 1], [0, 1], 'r--', linewidth=1, label='Random Classifier (AUC = 0.500)')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate', fontsize=12)
    plt.ylabel('True Positive Rate', fontsize=12)
    plt.title('ROC Curve - Binary Coincidence Classification', fontsize=14, fontweight='bold')
    plt.legend(loc='lower right', fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'roc_curve.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✓ Saved ROC curve: {output_file}")

def main():
    print("=" * 70)
    print("Binary Baseline Model Training - Coincidence Prediction")
    print("=" * 70)
    
    # Create directories
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nUsing device: {device}")
    
    # Load and combine data
    X, y, features_used = load_and_combine_data()
    
    # Split data: 80% train, 10% validation, 10% test
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )
    
    print(f"\nData split:")
    print(f"  Train: {len(X_train):,} samples ({100*len(X_train)/len(X):.1f}%)")
    print(f"  Validation: {len(X_val):,} samples ({100*len(X_val)/len(X):.1f}%)")
    print(f"  Test: {len(X_test):,} samples ({100*len(X_test)/len(X):.1f}%)")
    
    # Normalize features
    print(f"\nNormalizing features using StandardScaler...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    
    # Create datasets
    train_dataset = CosmicWatchDataset(X_train_scaled, y_train)
    val_dataset = CosmicWatchDataset(X_val_scaled, y_val)
    test_dataset = CosmicWatchDataset(X_test_scaled, y_test)
    
    # Create weighted sampler for class imbalance
    weighted_sampler = create_weighted_sampler(y_train)
    
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, sampler=weighted_sampler)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)
    
    # Create model
    model = BinaryCoincidenceClassifier(input_size=len(features_used), hidden_sizes=[64, 32])
    model = model.to(device)
    
    print(f"\nModel architecture:")
    print(model)
    print(f"  Input features: {len(features_used)}")
    print(f"  Features used: {features_used}")
    
    # Train model
    train_losses, val_losses, val_accuracies, best_val_acc = train_model(
        model, train_loader, val_loader, EPOCHS, device
    )
    
    # Evaluate on test set
    print(f"\n{'='*70}")
    print("Evaluating on Test Set")
    print(f"{'='*70}")
    results = evaluate_model(model, test_loader, device)
    
    print(f"\nTest Set Results:")
    print(f"  Accuracy:  {results['accuracy']:.4f}")
    print(f"  Precision: {results['precision']:.4f}")
    print(f"  Recall:    {results['recall']:.4f}")
    print(f"  F1-Score:  {results['f1']:.4f}")
    print(f"  ROC-AUC:   {results['roc_auc']:.4f}")
    print(f"\nConfusion Matrix:")
    print(results['confusion_matrix'])
    print(f"\nClassification Report:")
    print(results['classification_report'])
    
    # Physics validation
    predicted_coincidence_rate = results['predictions'].mean() * 100
    actual_coincidence_rate = results['labels'].mean() * 100
    print(f"\n{'='*70}")
    print("Physics Validation")
    print(f"{'='*70}")
    print(f"  Actual coincidence rate:   {actual_coincidence_rate:.2f}%")
    print(f"  Predicted coincidence rate:  {predicted_coincidence_rate:.2f}%")
    print(f"  Expected range: 5-15%")
    if 5 <= predicted_coincidence_rate <= 15:
        print(f"  ✓ Predicted rate within expected range!")
    else:
        print(f"  ⚠ Predicted rate outside expected range")
    
    # Save model and scaler
    model_path = os.path.join(MODEL_DIR, 'binary_baseline_model.pth')
    scaler_path = os.path.join(MODEL_DIR, 'binary_baseline_scaler.pkl')
    
    torch.save(model.state_dict(), model_path)
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    
    print(f"\n✓ Model saved to: {model_path}")
    print(f"✓ Scaler saved to: {scaler_path}")
    
    # Save results
    results_summary = {
        'model_type': 'binary_classification',
        'task': 'coincidence_prediction',
        'features_used': features_used,
        'test_accuracy': float(results['accuracy']),
        'test_precision': float(results['precision']),
        'test_recall': float(results['recall']),
        'test_f1': float(results['f1']),
        'test_roc_auc': float(results['roc_auc']),
        'best_val_accuracy': float(best_val_acc),
        'train_samples': len(X_train),
        'val_samples': len(X_val),
        'test_samples': len(X_test),
        'confusion_matrix': results['confusion_matrix'].tolist(),
        'predicted_coincidence_rate': float(predicted_coincidence_rate),
        'actual_coincidence_rate': float(actual_coincidence_rate),
        'model_architecture': {
            'input_size': len(features_used),
            'hidden_sizes': [64, 32],
            'output_size': 1
        }
    }
    
    summary_path = os.path.join(MODEL_DIR, 'binary_baseline_results.json')
    with open(summary_path, 'w') as f:
        json.dump(results_summary, f, indent=2)
    
    # Plot training curves
    plot_training_curves(train_losses, val_losses, val_accuracies, MODEL_DIR)
    
    # Plot ROC curve
    plot_roc_curve(results['labels'], results['probabilities'], results['roc_auc'], MODEL_DIR)
    
    print(f"\n✓ Results saved to: {summary_path}")
    print(f"\n{'='*70}")
    print("Training Complete!")
    print(f"{'='*70}")
    print(f"\nNext steps:")
    print(f"  1. Review model performance (target: >90% accuracy)")
    print(f"  2. Check physics validation (coincidence rate ~12-15%)")
    print(f"  3. Proceed to Day 5-6: Federated Learning Implementation")
    print(f"  4. Use this model as baseline for FL aggregation")

if __name__ == "__main__":
    main()

