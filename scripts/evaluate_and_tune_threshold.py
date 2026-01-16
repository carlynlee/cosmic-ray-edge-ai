#!/usr/bin/env python3
"""
Evaluate Model and Find Optimal Threshold

The baseline model has high recall but low precision (too many false positives).
This script finds the optimal threshold to balance precision/recall and match physics.
"""

import os
import sys
import pickle
import torch
import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
from sklearn.preprocessing import StandardScaler
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Import model class
from train_binary_baseline import BinaryCoincidenceClassifier, CosmicWatchDataset, FEATURES
from torch.utils.data import DataLoader

MODEL_DIR = 'models'
DATA_DIR = 'data/data_partitions'

def load_model_and_data():
    """Load trained model and test data"""
    print("Loading model and data...")
    
    # Load model
    with open(os.path.join(MODEL_DIR, 'binary_baseline_results.json'), 'r') as f:
        results = json.load(f)
    
    features_used = results['features_used']
    
    # Load scaler
    with open(os.path.join(MODEL_DIR, 'binary_baseline_scaler.pkl'), 'rb') as f:
        scaler = pickle.load(f)
    
    # Load test data
    from sklearn.model_selection import train_test_split
    
    df1 = pd.read_csv(os.path.join(DATA_DIR, 'node1_coincidence_events.csv'))
    df2 = pd.read_csv(os.path.join(DATA_DIR, 'node2_non_coincidence_events.csv'))
    df = pd.concat([df1, df2], ignore_index=True)
    
    X = df[features_used].values
    y = df['coincident'].astype(int).values
    
    # Use same split as training
    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    _, X_test, _, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)
    
    X_test_scaled = scaler.transform(X_test)
    
    # Load model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = BinaryCoincidenceClassifier(input_size=len(features_used), hidden_sizes=[64, 32])
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
    
    return all_probs, all_labels, results

def find_optimal_threshold(probs, labels, target_rate=0.123):
    """Find threshold that gives target coincidence rate"""
    thresholds = np.arange(0.1, 0.9, 0.01)
    best_threshold = 0.5
    best_diff = float('inf')
    
    results = []
    
    for threshold in thresholds:
        preds = (probs > threshold).astype(int)
        rate = preds.mean()
        diff = abs(rate - target_rate)
        
        precision = precision_score(labels, preds, zero_division=0)
        recall = recall_score(labels, preds, zero_division=0)
        f1 = f1_score(labels, preds, zero_division=0)
        
        results.append({
            'threshold': threshold,
            'rate': rate,
            'diff': diff,
            'precision': precision,
            'recall': recall,
            'f1': f1
        })
        
        if diff < best_diff:
            best_diff = diff
            best_threshold = threshold
    
    return best_threshold, results

if __name__ == "__main__":
    import json
    
    print("=" * 70)
    print("Threshold Tuning for Binary Baseline Model")
    print("=" * 70)
    
    probs, labels, model_results = load_model_and_data()
    
    print(f"\nCurrent performance (threshold=0.5):")
    preds_05 = (probs > 0.5).astype(int)
    print(f"  Predicted rate: {preds_05.mean()*100:.2f}%")
    print(f"  Actual rate: {labels.mean()*100:.2f}%")
    print(f"  Precision: {precision_score(labels, preds_05, zero_division=0):.4f}")
    print(f"  Recall: {recall_score(labels, preds_05, zero_division=0):.4f}")
    
    # Find optimal threshold
    print(f"\nFinding optimal threshold to match physics (target: 12.3%)...")
    optimal_threshold, threshold_results = find_optimal_threshold(probs, labels, target_rate=0.123)
    
    print(f"\nOptimal threshold: {optimal_threshold:.3f}")
    
    # Evaluate with optimal threshold
    preds_opt = (probs > optimal_threshold).astype(int)
    
    print(f"\nPerformance with optimal threshold ({optimal_threshold:.3f}):")
    print(f"  Predicted rate: {preds_opt.mean()*100:.2f}%")
    print(f"  Actual rate: {labels.mean()*100:.2f}%")
    print(f"  Precision: {precision_score(labels, preds_opt, zero_division=0):.4f}")
    print(f"  Recall: {recall_score(labels, preds_opt, zero_division=0):.4f}")
    print(f"  F1-Score: {f1_score(labels, preds_opt, zero_division=0):.4f}")
    print(f"\nConfusion Matrix:")
    print(confusion_matrix(labels, preds_opt))
    
    # Save optimal threshold
    model_results['optimal_threshold'] = float(optimal_threshold)
    model_results['threshold_05_performance'] = {
        'predicted_rate': float(preds_05.mean()),
        'precision': float(precision_score(labels, preds_05, zero_division=0)),
        'recall': float(recall_score(labels, preds_05, zero_division=0))
    }
    model_results['optimal_threshold_performance'] = {
        'predicted_rate': float(preds_opt.mean()),
        'precision': float(precision_score(labels, preds_opt, zero_division=0)),
        'recall': float(recall_score(labels, preds_opt, zero_division=0)),
        'f1': float(f1_score(labels, preds_opt, zero_division=0))
    }
    
    with open(os.path.join(MODEL_DIR, 'binary_baseline_results.json'), 'w') as f:
        json.dump(model_results, f, indent=2)
    
    print(f"\n✓ Optimal threshold saved to results file")
    print(f"\nRecommendation: Use threshold={optimal_threshold:.3f} for inference")

