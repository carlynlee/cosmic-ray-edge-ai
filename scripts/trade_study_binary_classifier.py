#!/usr/bin/env python3
"""
Trade Study for Binary Classifier - Compare Different Parameters

This script trains multiple models with different hyperparameters and
generates ROC curves on a single graph for comparison.
"""

import os
import sys
import json
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_curve, roc_auc_score, accuracy_score, precision_score, recall_score, f1_score
from scipy.interpolate import interp1d, UnivariateSpline
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pickle
from datetime import datetime

# Import model class
from train_binary_baseline import BinaryCoincidenceClassifier, CosmicWatchDataset, load_and_combine_data, create_weighted_sampler

# Configuration
DATA_DIR = 'data/data_partitions'
MODEL_DIR = 'models'
TRADE_STUDY_DIR = 'models/trade_study'
BATCH_SIZE = 32
EPOCHS = 100
EARLY_STOPPING_PATIENCE = 10

# Core features
FEATURES = [
    'adc_value',
    'sipm_mv',
    'temperature_c',
    'pressure_pa',
    'accel_z_g',
]

# Trade study configurations
TRADE_STUDY_CONFIGS = [
    # Baseline
    {
        'name': 'Baseline',
        'hidden_sizes': [64, 32],
        'dropout': 0.3,
        'learning_rate': 0.001,
        'batch_size': 32,
    },
    # Different architectures
    {
        'name': 'Small (32, 16)',
        'hidden_sizes': [32, 16],
        'dropout': 0.3,
        'learning_rate': 0.001,
        'batch_size': 32,
    },
    {
        'name': 'Large (128, 64)',
        'hidden_sizes': [128, 64],
        'dropout': 0.3,
        'learning_rate': 0.001,
        'batch_size': 32,
    },
    {
        'name': 'Deep (64, 64, 32)',
        'hidden_sizes': [64, 64, 32],
        'dropout': 0.3,
        'learning_rate': 0.001,
        'batch_size': 32,
    },
    # Different dropout rates
    {
        'name': 'No Dropout',
        'hidden_sizes': [64, 32],
        'dropout': 0.0,
        'learning_rate': 0.001,
        'batch_size': 32,
    },
    {
        'name': 'High Dropout (0.5)',
        'hidden_sizes': [64, 32],
        'dropout': 0.5,
        'learning_rate': 0.001,
        'batch_size': 32,
    },
    # Different learning rates
    {
        'name': 'LR 0.0001',
        'hidden_sizes': [64, 32],
        'dropout': 0.3,
        'learning_rate': 0.0001,
        'batch_size': 32,
    },
    {
        'name': 'LR 0.01',
        'hidden_sizes': [64, 32],
        'dropout': 0.3,
        'learning_rate': 0.01,
        'batch_size': 32,
    },
    # Different batch sizes
    {
        'name': 'Batch 16',
        'hidden_sizes': [64, 32],
        'dropout': 0.3,
        'learning_rate': 0.001,
        'batch_size': 16,
    },
    {
        'name': 'Batch 64',
        'hidden_sizes': [64, 32],
        'dropout': 0.3,
        'learning_rate': 0.001,
        'batch_size': 64,
    },
]

class BinaryCoincidenceClassifierCustom(nn.Module):
    """MLP with configurable dropout"""
    def __init__(self, input_size=5, hidden_sizes=[64, 32], dropout=0.3):
        super(BinaryCoincidenceClassifierCustom, self).__init__()
        
        layers = []
        prev_size = input_size
        
        for hidden_size in hidden_sizes:
            layers.append(nn.Linear(prev_size, hidden_size))
            layers.append(nn.ReLU())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            prev_size = hidden_size
        
        layers.append(nn.Linear(prev_size, 1))
        layers.append(nn.Sigmoid())
        self.model = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.model(x).squeeze()

def train_model(config, X_train, y_train, X_val, y_val, X_test, y_test, scaler, device):
    """Train a single model configuration"""
    print(f"\n{'='*70}")
    print(f"Training: {config['name']}")
    print(f"{'='*70}")
    print(f"  Architecture: {config['hidden_sizes']}")
    print(f"  Dropout: {config['dropout']}")
    print(f"  Learning Rate: {config['learning_rate']}")
    print(f"  Batch Size: {config['batch_size']}")
    
    # Create datasets
    train_dataset = CosmicWatchDataset(X_train, y_train)
    val_dataset = CosmicWatchDataset(X_val, y_val)
    test_dataset = CosmicWatchDataset(X_test, y_test)
    
    # Create weighted sampler
    weighted_sampler = create_weighted_sampler(y_train)
    
    train_loader = DataLoader(train_dataset, batch_size=config['batch_size'], sampler=weighted_sampler)
    val_loader = DataLoader(val_dataset, batch_size=config['batch_size'], shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=config['batch_size'], shuffle=False)
    
    # Create model
    model = BinaryCoincidenceClassifierCustom(
        input_size=X_train.shape[1],
        hidden_sizes=config['hidden_sizes'],
        dropout=config['dropout']
    ).to(device)
    
    # Training
    criterion = nn.BCELoss()
    optimizer = optim.Adam(model.parameters(), lr=config['learning_rate'])
    
    best_val_loss = float('inf')
    best_val_acc = 0.0
    patience_counter = 0
    best_model_state = None
    
    for epoch in range(EPOCHS):
        # Training
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
        
        # Validation
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
                predicted = (outputs > 0.5).float()
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()
        
        val_loss /= len(val_loader)
        val_acc = val_correct / val_total
        
        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_val_acc = val_acc
            patience_counter = 0
            best_model_state = model.state_dict().copy()
        else:
            patience_counter += 1
        
        if (epoch + 1) % 20 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1}/{EPOCHS}: Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}")
        
        if patience_counter >= EARLY_STOPPING_PATIENCE:
            print(f"  Early stopping at epoch {epoch+1}")
            break
    
    # Load best model
    if best_model_state:
        model.load_state_dict(best_model_state)
    
    # Evaluate on test set
    model.eval()
    all_probs = []
    all_labels = []
    all_preds = []
    
    with torch.no_grad():
        for features, labels in test_loader:
            features = features.to(device)
            outputs = model(features)
            probs = outputs.cpu().numpy()
            preds = (probs > 0.5).astype(int)
            
            all_probs.extend(probs)
            all_preds.extend(preds)
            all_labels.extend(labels.numpy())
    
    all_probs = np.array(all_probs)
    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    
    # Calculate metrics
    accuracy = accuracy_score(all_labels, all_preds)
    precision = precision_score(all_labels, all_preds, zero_division=0)
    recall = recall_score(all_labels, all_preds, zero_division=0)
    f1 = f1_score(all_labels, all_preds, zero_division=0)
    roc_auc = roc_auc_score(all_labels, all_probs)
    
    print(f"  Test Results:")
    print(f"    Accuracy:  {accuracy:.4f}")
    print(f"    Precision: {precision:.4f}")
    print(f"    Recall:    {recall:.4f}")
    print(f"    F1-Score:  {f1:.4f}")
    print(f"    ROC-AUC:   {roc_auc:.4f}")
    
    return {
        'config': config,
        'model': model,
        'probs': all_probs,
        'labels': all_labels,
        'metrics': {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'roc_auc': roc_auc,
            'best_val_acc': best_val_acc,
        }
    }

def plot_all_roc_curves(results, output_dir, smooth=True, interpolation_points=5000):
    """Plot all ROC curves on a single graph
    
    Args:
        results: List of result dictionaries
        output_dir: Output directory
        smooth: Whether to smooth curves using interpolation (default: True)
        interpolation_points: Number of points for interpolation (default: 1000)
    """
    plt.figure(figsize=(10, 8))
    
    # Color palette
    colors = plt.cm.tab10(np.linspace(0, 1, len(results)))
    
    # Plot random classifier
    plt.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.5, label='Random (AUC = 0.500)')
    
    # Plot each model's ROC curve
    for i, result in enumerate(results):
        labels = result['labels']
        probs = result['probs']
        config_name = result['config']['name']
        roc_auc = result['metrics']['roc_auc']
        
        fpr, tpr, _ = roc_curve(labels, probs)
        
        # Smooth curve using interpolation if requested
        if smooth and len(fpr) > 1:
            # Ensure we have endpoints at (0,0) and (1,1) for proper ROC curve
            fpr_full = np.concatenate([[0], fpr, [1]])
            tpr_full = np.concatenate([[0], tpr, [1]])
            
            # Remove duplicates while preserving order (needed for interpolation)
            # Keep unique FPR values, taking last TPR for duplicates
            unique_indices = []
            seen_fpr = set()
            for idx in range(len(fpr_full) - 1, -1, -1):
                if fpr_full[idx] not in seen_fpr:
                    unique_indices.append(idx)
                    seen_fpr.add(fpr_full[idx])
            unique_indices = sorted(unique_indices)
            
            fpr_unique = fpr_full[unique_indices]
            tpr_unique = tpr_full[unique_indices]
            
            # Create dense interpolation points
            fpr_interp = np.linspace(0, 1, interpolation_points)
            
            # Use UnivariateSpline for smooth curves with smoothing factor
            # This creates much smoother curves than interpolation
            if len(fpr_unique) >= 4:
                # Use smoothing spline - s parameter controls smoothness (lower = smoother)
                # Set s to balance smoothness vs accuracy
                spline = UnivariateSpline(fpr_unique, tpr_unique, s=0, k=min(3, len(fpr_unique)-1))
                tpr_interp = spline(fpr_interp)
            else:
                # Fall back to cubic interpolation if not enough points
                interp_func = interp1d(fpr_unique, tpr_unique, kind='cubic', 
                                      bounds_error=False, fill_value=(0, 1))
                tpr_interp = interp_func(fpr_interp)
            
            # Ensure monotonicity (ROC curves must be non-decreasing)
            tpr_interp = np.maximum.accumulate(np.clip(tpr_interp, 0, 1))
            
            # Ensure endpoints
            tpr_interp[0] = 0
            tpr_interp[-1] = 1
            
            # Clip to valid range
            tpr_interp = np.clip(tpr_interp, 0, 1)
            
            plt.plot(fpr_interp, tpr_interp, linewidth=2.5, color=colors[i], 
                    label=f"{config_name} (AUC = {roc_auc:.3f})", antialiased=True, alpha=0.9)
        else:
            # Plot raw curve
            plt.plot(fpr, tpr, linewidth=2, color=colors[i], 
                    label=f"{config_name} (AUC = {roc_auc:.3f})")
    
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate', fontsize=12)
    plt.ylabel('True Positive Rate', fontsize=12)
    plt.title('ROC Curves - Binary Classifier Trade Study', fontsize=14, fontweight='bold')
    plt.legend(loc='lower right', fontsize=10, ncol=1)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_file = os.path.join(output_dir, 'trade_study_roc_curves.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n✓ Saved ROC curves: {output_file}")
    return output_file

def save_results_table(results, output_dir):
    """Save results as a comparison table"""
    data = []
    for result in results:
        config = result['config']
        metrics = result['metrics']
        data.append({
            'Name': config['name'],
            'Architecture': str(config['hidden_sizes']),
            'Dropout': config['dropout'],
            'Learning Rate': config['learning_rate'],
            'Batch Size': config['batch_size'],
            'Accuracy': metrics['accuracy'],
            'Precision': metrics['precision'],
            'Recall': metrics['recall'],
            'F1-Score': metrics['f1'],
            'ROC-AUC': metrics['roc_auc'],
            'Val Accuracy': metrics['best_val_acc'],
        })
    
    df = pd.DataFrame(data)
    
    # Save CSV with formatted values for readability
    df_formatted = df.copy()
    for col in ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'ROC-AUC', 'Val Accuracy']:
        df_formatted[col] = df_formatted[col].apply(lambda x: f"{x:.4f}")
    
    csv_file = os.path.join(output_dir, 'trade_study_results.csv')
    df_formatted.to_csv(csv_file, index=False)
    print(f"✓ Saved results table: {csv_file}")
    
    # Also save as JSON
    json_file = os.path.join(output_dir, 'trade_study_results.json')
    with open(json_file, 'w') as f:
        json.dump([{
            'config': r['config'],
            'metrics': r['metrics']
        } for r in results], f, indent=2)
    print(f"✓ Saved results JSON: {json_file}")
    
    return df  # Return unformatted DataFrame for sorting

def main():
    print("=" * 70)
    print("Binary Classifier Trade Study")
    print("=" * 70)
    
    # Create directories
    os.makedirs(TRADE_STUDY_DIR, exist_ok=True)
    
    # Device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\nUsing device: {device}")
    print(f"Number of configurations: {len(TRADE_STUDY_CONFIGS)}")
    
    # Load and prepare data
    print("\nLoading data...")
    X, y, features_used = load_and_combine_data()
    
    # Split data (same split for all models)
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )
    
    # Normalize features
    print("\nNormalizing features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    
    # Train all configurations
    results = []
    for config in TRADE_STUDY_CONFIGS:
        result = train_model(
            config, X_train_scaled, y_train, X_val_scaled, y_val, 
            X_test_scaled, y_test, scaler, device
        )
        results.append(result)
    
    # Plot all ROC curves
    print(f"\n{'='*70}")
    print("Generating ROC Curves Comparison")
    print(f"{'='*70}")
    plot_all_roc_curves(results, TRADE_STUDY_DIR)
    
    # Save results table
    print(f"\n{'='*70}")
    print("Saving Results")
    print(f"{'='*70}")
    df = save_results_table(results, TRADE_STUDY_DIR)
    
    # Print summary
    print(f"\n{'='*70}")
    print("Trade Study Summary")
    print(f"{'='*70}")
    print("\nTop 5 Models by ROC-AUC:")
    top5 = df.nlargest(5, 'ROC-AUC')[['Name', 'ROC-AUC', 'Accuracy', 'F1-Score']].copy()
    # Format for display
    top5['ROC-AUC'] = top5['ROC-AUC'].apply(lambda x: f"{x:.4f}")
    top5['Accuracy'] = top5['Accuracy'].apply(lambda x: f"{x:.4f}")
    top5['F1-Score'] = top5['F1-Score'].apply(lambda x: f"{x:.4f}")
    print(top5.to_string(index=False))
    
    print(f"\n{'='*70}")
    print("Trade Study Complete!")
    print(f"{'='*70}")
    print(f"\nResults saved to: {TRADE_STUDY_DIR}/")
    print(f"  - trade_study_roc_curves.png (all ROC curves)")
    print(f"  - trade_study_results.csv (comparison table)")
    print(f"  - trade_study_results.json (detailed results)")

if __name__ == "__main__":
    main()
