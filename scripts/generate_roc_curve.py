#!/usr/bin/env python3
"""
Generate ROC Curve from Saved Model

This script loads the saved binary baseline model and generates a ROC curve plot.
"""

import os
import sys
import pickle
import json
import torch
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_curve, roc_auc_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Import model class
from train_binary_baseline import BinaryCoincidenceClassifier, CosmicWatchDataset
from torch.utils.data import DataLoader

MODEL_DIR = 'models'
DATA_DIR = 'data/data_partitions'

def load_model_and_data():
    """Load trained model and test data"""
    print("Loading model and data...")
    
    # Load results to get features
    with open(os.path.join(MODEL_DIR, 'binary_baseline_results.json'), 'r') as f:
        results = json.load(f)
    
    features_used = results['features_used']
    roc_auc_expected = results['test_roc_auc']
    
    # Load scaler
    with open(os.path.join(MODEL_DIR, 'binary_baseline_scaler.pkl'), 'rb') as f:
        scaler = pickle.load(f)
    
    # Load test data
    df1 = pd.read_csv(os.path.join(DATA_DIR, 'node1_coincidence_events.csv'))
    df2 = pd.read_csv(os.path.join(DATA_DIR, 'node2_non_coincidence_events.csv'))
    df = pd.concat([df1, df2], ignore_index=True)
    
    X = df[features_used].values
    y = df['coincident'].astype(int).values
    
    # Use same split as training
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    _, X_test, _, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )
    
    X_test_scaled = scaler.transform(X_test)
    
    # Load model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = BinaryCoincidenceClassifier(
        input_size=len(features_used), 
        hidden_sizes=[64, 32]
    )
    model.load_state_dict(torch.load(os.path.join(MODEL_DIR, 'binary_baseline_model.pth')))
    model = model.to(device)
    model.eval()
    
    # Get predictions
    test_dataset = CosmicWatchDataset(X_test_scaled, y_test)
    test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
    
    all_probs = []
    all_labels = []
    
    with torch.no_grad():
        for features, labels in test_loader:
            features = features.to(device)
            outputs = model(features)
            all_probs.extend(outputs.cpu().numpy())
            all_labels.extend(labels.numpy())
    
    all_probs = np.array(all_probs)
    all_labels = np.array(all_labels)
    
    # Calculate ROC-AUC
    roc_auc = roc_auc_score(all_labels, all_probs)
    
    print(f"✓ Model loaded successfully")
    print(f"✓ Test samples: {len(all_labels)}")
    print(f"✓ ROC-AUC: {roc_auc:.4f} (expected: {roc_auc_expected:.4f})")
    
    return all_probs, all_labels, roc_auc

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
    return output_file

if __name__ == "__main__":
    print("=" * 70)
    print("Generate ROC Curve from Saved Model")
    print("=" * 70)
    
    # Check if model exists
    if not os.path.exists(os.path.join(MODEL_DIR, 'binary_baseline_model.pth')):
        print(f"Error: Model not found at {MODEL_DIR}/binary_baseline_model.pth")
        print("Please train the model first using train_binary_baseline.py")
        sys.exit(1)
    
    # Load model and data
    probs, labels, roc_auc = load_model_and_data()
    
    # Generate ROC curve
    output_file = plot_roc_curve(labels, probs, roc_auc, MODEL_DIR)
    
    print(f"\n{'='*70}")
    print("ROC Curve Generated Successfully!")
    print(f"{'='*70}")
    print(f"\nOutput file: {output_file}")
    print(f"ROC-AUC: {roc_auc:.4f}")

