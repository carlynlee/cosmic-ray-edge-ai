#!/usr/bin/env python3
"""
Visualize Classification Threshold

This script creates visualizations showing how the classification threshold works:
1. Probability distribution for both classes
2. Threshold line and decision boundary
3. Predicted rate vs threshold
4. Precision/Recall vs threshold
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
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# Import model class
from train_binary_baseline import BinaryCoincidenceClassifier, CosmicWatchDataset, FEATURES
from torch.utils.data import DataLoader

MODEL_DIR = 'models'
DATA_DIR = 'data/data_partitions'
OUTPUT_DIR = MODEL_DIR

def load_model_and_data():
    """Load trained model and test data"""
    print("Loading model and data...")
    
    # Load results to get features and optimal threshold
    with open(os.path.join(MODEL_DIR, 'binary_baseline_results.json'), 'r') as f:
        results = json.load(f)
    
    features_used = results['features_used']
    optimal_threshold = results.get('optimal_threshold', 0.72)
    actual_rate = results.get('actual_coincidence_rate', 12.29) / 100.0
    
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
            all_probs.extend(outputs.cpu().numpy().flatten())
            all_labels.extend(labels.numpy())
    
    all_probs = np.array(all_probs)
    all_labels = np.array(all_labels)
    
    return all_probs, all_labels, optimal_threshold, actual_rate

def plot_probability_distribution(probs, labels, optimal_threshold, output_dir):
    """Plot probability distribution for both classes with threshold line"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Separate probabilities by class
    probs_class0 = probs[labels == 0]  # Non-coincidence
    probs_class1 = probs[labels == 1]  # Coincidence
    
    # Plot histograms
    bins = np.linspace(0, 1, 50)
    ax.hist(probs_class0, bins=bins, alpha=0.6, label='Non-Coincidence (Class 0)', 
            color='blue', density=True)
    ax.hist(probs_class1, bins=bins, alpha=0.6, label='Coincidence (Class 1)', 
            color='red', density=True)
    
    # Add threshold line
    ax.axvline(x=optimal_threshold, color='green', linestyle='--', linewidth=2, 
               label=f'Optimal Threshold = {optimal_threshold:.2f}')
    
    # Add default threshold line
    ax.axvline(x=0.5, color='orange', linestyle='--', linewidth=1.5, alpha=0.7,
               label='Default Threshold = 0.50')
    
    ax.set_xlabel('Model Probability (Coincidence)', fontsize=12)
    ax.set_ylabel('Density', fontsize=12)
    ax.set_title('Probability Distribution by Class\n(Shows how threshold separates predictions)', 
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 1)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'threshold_probability_distribution.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✓ Saved probability distribution: {output_file}")
    return output_file

def plot_threshold_metrics(probs, labels, optimal_threshold, actual_rate, output_dir):
    """Plot precision, recall, F1, and predicted rate vs threshold"""
    thresholds = np.arange(0.1, 0.95, 0.01)
    precisions = []
    recalls = []
    f1_scores = []
    predicted_rates = []
    
    for threshold in thresholds:
        preds = (probs > threshold).astype(int)
        precisions.append(precision_score(labels, preds, zero_division=0))
        recalls.append(recall_score(labels, preds, zero_division=0))
        f1_scores.append(f1_score(labels, preds, zero_division=0))
        predicted_rates.append(preds.mean())
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot 1: Precision and Recall
    ax1 = axes[0, 0]
    ax1.plot(thresholds, precisions, 'b-', linewidth=2, label='Precision')
    ax1.plot(thresholds, recalls, 'r-', linewidth=2, label='Recall')
    ax1.axvline(x=optimal_threshold, color='green', linestyle='--', linewidth=2, 
                label=f'Optimal Threshold = {optimal_threshold:.2f}')
    ax1.axvline(x=0.5, color='orange', linestyle='--', linewidth=1.5, alpha=0.7,
                label='Default Threshold = 0.50')
    ax1.set_xlabel('Threshold', fontsize=11)
    ax1.set_ylabel('Score', fontsize=11)
    ax1.set_title('Precision and Recall vs Threshold', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0.1, 0.95)
    ax1.set_ylim(0, 1)
    
    # Plot 2: F1 Score
    ax2 = axes[0, 1]
    ax2.plot(thresholds, f1_scores, 'g-', linewidth=2, label='F1 Score')
    ax2.axvline(x=optimal_threshold, color='green', linestyle='--', linewidth=2,
                label=f'Optimal Threshold = {optimal_threshold:.2f}')
    ax2.axvline(x=0.5, color='orange', linestyle='--', linewidth=1.5, alpha=0.7,
                label='Default Threshold = 0.50')
    ax2.set_xlabel('Threshold', fontsize=11)
    ax2.set_ylabel('F1 Score', fontsize=11)
    ax2.set_title('F1 Score vs Threshold', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0.1, 0.95)
    ax2.set_ylim(0, 1)
    
    # Plot 3: Predicted Rate
    ax3 = axes[1, 0]
    ax3.plot(thresholds, np.array(predicted_rates) * 100, 'purple', linewidth=2, 
             label='Predicted Coincidence Rate')
    ax3.axhline(y=actual_rate * 100, color='red', linestyle='-', linewidth=2, alpha=0.7,
                label=f'Observed Rate = {actual_rate*100:.2f}%')
    ax3.axvline(x=optimal_threshold, color='green', linestyle='--', linewidth=2,
                label=f'Optimal Threshold = {optimal_threshold:.2f}')
    ax3.axvline(x=0.5, color='orange', linestyle='--', linewidth=1.5, alpha=0.7,
                label='Default Threshold = 0.50')
    ax3.set_xlabel('Threshold', fontsize=11)
    ax3.set_ylabel('Predicted Rate (%)', fontsize=11)
    ax3.set_title('Predicted Coincidence Rate vs Threshold\n(Goal: Match Observed Rate)', 
                  fontsize=12, fontweight='bold')
    ax3.legend(fontsize=9)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(0.1, 0.95)
    
    # Plot 4: Combined view
    ax4 = axes[1, 1]
    ax4_twin = ax4.twinx()
    
    # Left axis: Precision/Recall
    line1 = ax4.plot(thresholds, precisions, 'b-', linewidth=2, label='Precision', alpha=0.7)
    line2 = ax4.plot(thresholds, recalls, 'r-', linewidth=2, label='Recall', alpha=0.7)
    ax4.set_xlabel('Threshold', fontsize=11)
    ax4.set_ylabel('Precision / Recall', fontsize=11, color='black')
    ax4.tick_params(axis='y', labelcolor='black')
    
    # Right axis: Predicted Rate
    line3 = ax4_twin.plot(thresholds, np.array(predicted_rates) * 100, 'purple', 
                          linewidth=2, label='Predicted Rate (%)', alpha=0.7)
    ax4_twin.set_ylabel('Predicted Rate (%)', fontsize=11, color='purple')
    ax4_twin.tick_params(axis='y', labelcolor='purple')
    
    # Add threshold lines
    ax4.axvline(x=optimal_threshold, color='green', linestyle='--', linewidth=2,
                label=f'Optimal = {optimal_threshold:.2f}')
    ax4.axvline(x=0.5, color='orange', linestyle='--', linewidth=1.5, alpha=0.7,
                label='Default = 0.50')
    
    # Combine legends
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax4.legend(lines, labels, loc='upper left', fontsize=8)
    
    ax4.set_title('Combined View: Metrics vs Threshold', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.set_xlim(0.1, 0.95)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'threshold_metrics.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✓ Saved threshold metrics: {output_file}")
    return output_file

def plot_threshold_comparison(probs, labels, optimal_threshold, output_dir):
    """Show predictions with default vs optimal threshold"""
    preds_default = (probs > 0.5).astype(int)
    preds_optimal = (probs > optimal_threshold).astype(int)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Default threshold
    ax1 = axes[0]
    correct_default = (preds_default == labels)
    ax1.scatter(probs[correct_default], labels[correct_default], 
                c='green', alpha=0.3, s=10, label='Correct')
    ax1.scatter(probs[~correct_default], labels[~correct_default], 
                c='red', alpha=0.3, s=10, label='Incorrect')
    ax1.axvline(x=0.5, color='blue', linestyle='--', linewidth=2, label='Threshold = 0.50')
    ax1.set_xlabel('Model Probability', fontsize=11)
    ax1.set_ylabel('True Label', fontsize=11)
    ax1.set_title(f'Default Threshold (0.50)\nAccuracy: {(correct_default.mean()*100):.1f}%', 
                  fontsize=12, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 1)
    ax1.set_ylim(-0.1, 1.1)
    
    # Optimal threshold
    ax2 = axes[1]
    correct_optimal = (preds_optimal == labels)
    ax2.scatter(probs[correct_optimal], labels[correct_optimal], 
                c='green', alpha=0.3, s=10, label='Correct')
    ax2.scatter(probs[~correct_optimal], labels[~correct_optimal], 
                c='red', alpha=0.3, s=10, label='Incorrect')
    ax2.axvline(x=optimal_threshold, color='blue', linestyle='--', linewidth=2, 
                label=f'Threshold = {optimal_threshold:.2f}')
    ax2.set_xlabel('Model Probability', fontsize=11)
    ax2.set_ylabel('True Label', fontsize=11)
    ax2.set_title(f'Optimal Threshold ({optimal_threshold:.2f})\nAccuracy: {(correct_optimal.mean()*100):.1f}%', 
                  fontsize=12, fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, 1)
    ax2.set_ylim(-0.1, 1.1)
    
    plt.tight_layout()
    output_file = os.path.join(output_dir, 'threshold_comparison.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✓ Saved threshold comparison: {output_file}")
    return output_file

if __name__ == "__main__":
    print("=" * 70)
    print("Threshold Visualization")
    print("=" * 70)
    
    # Check if model exists
    if not os.path.exists(os.path.join(MODEL_DIR, 'binary_baseline_model.pth')):
        print(f"Error: Model not found at {MODEL_DIR}/binary_baseline_model.pth")
        print("Please train the model first using train_binary_baseline.py")
        sys.exit(1)
    
    # Load model and data
    probs, labels, optimal_threshold, actual_rate = load_model_and_data()
    
    print(f"\nData loaded:")
    print(f"  Test samples: {len(labels)}")
    print(f"  Actual coincidence rate: {actual_rate*100:.2f}%")
    print(f"  Optimal threshold: {optimal_threshold:.3f}")
    
    # Create visualizations
    print(f"\nGenerating visualizations...")
    
    plot_probability_distribution(probs, labels, optimal_threshold, OUTPUT_DIR)
    plot_threshold_metrics(probs, labels, optimal_threshold, actual_rate, OUTPUT_DIR)
    plot_threshold_comparison(probs, labels, optimal_threshold, OUTPUT_DIR)
    
    print(f"\n{'='*70}")
    print("Threshold Visualizations Generated Successfully!")
    print(f"{'='*70}")
    print(f"\nOutput files saved to: {OUTPUT_DIR}/")
    print(f"  - threshold_probability_distribution.png")
    print(f"  - threshold_metrics.png")
    print(f"  - threshold_comparison.png")
