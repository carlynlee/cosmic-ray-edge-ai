#!/usr/bin/env python3
"""
Compare Different Classifier Architectures for Binary Classification

This script compares multiple classifier architectures including:
- Neural Networks (MLP)
- Tree-based models (Random Forest, XGBoost, LightGBM)
- Logistic Regression
- Support Vector Machines

All results are plotted on a single ROC curve for comparison.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_curve, roc_auc_score, accuracy_score, precision_score, recall_score, f1_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pickle

# Try to import XGBoost and LightGBM (optional)
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("Note: XGBoost not available. Install with: pip install xgboost")

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("Note: LightGBM not available. Install with: pip install lightgbm")

# Import PyTorch model
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler

# Import from train_binary_baseline with error handling
try:
    from train_binary_baseline import BinaryCoincidenceClassifier, CosmicWatchDataset, load_and_combine_data, create_weighted_sampler
except Exception as e:
    print(f"Warning: Could not import from train_binary_baseline: {e}")
    # Define minimal versions if import fails
    def load_and_combine_data():
        raise NotImplementedError("Need to import from train_binary_baseline")
    def create_weighted_sampler(*args, **kwargs):
        raise NotImplementedError("Need to import from train_binary_baseline")

# Configuration
DATA_DIR = 'data/data_partitions'
MODEL_DIR = 'models'
ARCHITECTURE_COMPARISON_DIR = 'models/architecture_comparison'
EPOCHS = 100
EARLY_STOPPING_PATIENCE = 10
BATCH_SIZE = 32
LEARNING_RATE = 0.001

def train_mlp(X_train, y_train, X_val, y_val, X_test, y_test, device):
    """Train MLP neural network"""
    print("\nTraining MLP Neural Network...")
    sys.stdout.flush()
    
    print("  Creating train dataset...")
    sys.stdout.flush()
    print(f"    X_train type: {type(X_train)}, shape: {X_train.shape}, dtype: {X_train.dtype}")
    sys.stdout.flush()
    print(f"    y_train type: {type(y_train)}, shape: {y_train.shape}, dtype: {y_train.dtype}")
    sys.stdout.flush()
    # Ensure data is numpy array and float32
    X_train_np = np.array(X_train, dtype=np.float32)
    y_train_np = np.array(y_train, dtype=np.float32)
    train_dataset = CosmicWatchDataset(X_train_np, y_train_np)
    print("  Train dataset created")
    sys.stdout.flush()
    print("  Creating val dataset...")
    sys.stdout.flush()
    val_dataset = CosmicWatchDataset(X_val, y_val)
    print("  Val dataset created")
    sys.stdout.flush()
    print("  Creating test dataset...")
    sys.stdout.flush()
    test_dataset = CosmicWatchDataset(X_test, y_test)
    print("  Test dataset created")
    sys.stdout.flush()
    
    print("  Creating weighted sampler...")
    sys.stdout.flush()
    weighted_sampler = create_weighted_sampler(y_train)
    print("  Weighted sampler created")
    sys.stdout.flush()
    print("  Creating data loaders...")
    sys.stdout.flush()
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, sampler=weighted_sampler)
    print("  Train loader created")
    sys.stdout.flush()
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    print("  Val loader created")
    sys.stdout.flush()
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)
    print("  Test loader created")
    sys.stdout.flush()
    
    model = BinaryCoincidenceClassifier(input_size=X_train.shape[1], hidden_sizes=[64, 32])
    model = model.to(device)
    
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    best_val_loss = float('inf')
    patience_counter = 0
    best_model_state = None
    
    for epoch in range(EPOCHS):
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
        
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for features, labels in val_loader:
                features, labels = features.to(device), labels.to(device)
                outputs = model(features)
                loss = criterion(outputs, labels)
                val_loss += loss.item()
        
        val_loss /= len(val_loader)
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            best_model_state = model.state_dict().copy()
        else:
            patience_counter += 1
        
        if patience_counter >= EARLY_STOPPING_PATIENCE:
            break
    
    if best_model_state:
        model.load_state_dict(best_model_state)
    
    model.eval()
    all_probs = []
    all_labels = []
    with torch.no_grad():
        for features, labels in test_loader:
            features = features.to(device)
            outputs = model(features)
            all_probs.extend(outputs.cpu().numpy())
            all_labels.extend(labels.numpy())
    
    return np.array(all_probs), np.array(all_labels), model

def train_logistic_regression(X_train, y_train, X_test, y_test):
    """Train Logistic Regression"""
    print("\nTraining Logistic Regression...")
    model = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
    model.fit(X_train, y_train)
    probs = model.predict_proba(X_test)[:, 1]
    return probs, y_test, model

def train_random_forest(X_train, y_train, X_test, y_test):
    """Train Random Forest"""
    print("\nTraining Random Forest...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    probs = model.predict_proba(X_test)[:, 1]
    return probs, y_test, model

def train_gradient_boosting(X_train, y_train, X_test, y_test):
    """Train Gradient Boosting"""
    print("\nTraining Gradient Boosting...")
    model = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    )
    model.fit(X_train, y_train)
    probs = model.predict_proba(X_test)[:, 1]
    return probs, y_test, model

def train_xgboost(X_train, y_train, X_test, y_test):
    """Train XGBoost"""
    print("\nTraining XGBoost...")
    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        eval_metric='logloss',
        use_label_encoder=False
    )
    model.fit(X_train, y_train)
    probs = model.predict_proba(X_test)[:, 1]
    return probs, y_test, model

def train_lightgbm(X_train, y_train, X_test, y_test):
    """Train LightGBM"""
    print("\nTraining LightGBM...")
    model = lgb.LGBMClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
        verbose=-1
    )
    model.fit(X_train, y_train)
    probs = model.predict_proba(X_test)[:, 1]
    return probs, y_test, model

def train_svm(X_train, y_train, X_test, y_test):
    """Train Support Vector Machine"""
    print("\nTraining Support Vector Machine...")
    # Use smaller sample for SVM (can be slow)
    if len(X_train) > 10000:
        sample_idx = np.random.choice(len(X_train), 10000, replace=False)
        X_train_sample = X_train[sample_idx]
        y_train_sample = y_train[sample_idx]
    else:
        X_train_sample = X_train
        y_train_sample = y_train
    
    model = SVC(
        kernel='rbf',
        probability=True,
        class_weight='balanced',
        random_state=42,
        gamma='scale'
    )
    model.fit(X_train_sample, y_train_sample)
    probs = model.predict_proba(X_test)[:, 1]
    return probs, y_test, model

def calculate_metrics(y_true, y_pred, probs):
    """Calculate classification metrics"""
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_true, probs)
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'roc_auc': roc_auc
    }

def plot_all_roc_curves(results, output_dir):
    """Plot all ROC curves on a single graph"""
    try:
        plt.figure(figsize=(10, 8))
        
        colors = plt.cm.tab10(np.linspace(0, 1, len(results)))
        
        # Plot random classifier
        plt.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.5, label='Random (AUC = 0.500)')
        
        # Plot each model's ROC curve
        for i, result in enumerate(results):
            labels = result['labels']
            probs = result['probs']
            name = result['name']
            roc_auc = result['metrics']['roc_auc']
            
            fpr, tpr, _ = roc_curve(labels, probs)
            
            plt.plot(fpr, tpr, linewidth=2, color=colors[i], 
                    label=f"{name} (AUC = {roc_auc:.3f})")
        
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate', fontsize=12)
        plt.ylabel('True Positive Rate', fontsize=12)
        plt.title('ROC Curves - Classifier Architecture Comparison', fontsize=14, fontweight='bold')
        plt.legend(loc='lower right', fontsize=10, ncol=1)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        output_file = os.path.join(output_dir, 'architecture_comparison_roc_curves.png')
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n✓ Saved ROC curves: {output_file}")
        return output_file
    except Exception as e:
        print(f"✗ Error plotting ROC curves: {e}")
        import traceback
        traceback.print_exc()
        return None

def save_results_table(results, output_dir):
    """Save results as a comparison table"""
    data = []
    for result in results:
        metrics = result['metrics']
        data.append({
            'Architecture': result['name'],
            'Accuracy': metrics['accuracy'],
            'Precision': metrics['precision'],
            'Recall': metrics['recall'],
            'F1-Score': metrics['f1'],
            'ROC-AUC': metrics['roc_auc'],
        })
    
    df = pd.DataFrame(data)
    
    # Save CSV with formatted values
    df_formatted = df.copy()
    for col in ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'ROC-AUC']:
        df_formatted[col] = df_formatted[col].apply(lambda x: f"{x:.4f}")
    
    csv_file = os.path.join(output_dir, 'architecture_comparison_results.csv')
    df_formatted.to_csv(csv_file, index=False)
    print(f"✓ Saved results table: {csv_file}")
    
    # Save JSON
    json_file = os.path.join(output_dir, 'architecture_comparison_results.json')
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"✓ Saved results JSON: {json_file}")
    
    return df

def main():
    try:
        print("=" * 70)
        print("Classifier Architecture Comparison")
        print("=" * 70)
        sys.stdout.flush()
        
        # Create directories
        os.makedirs(ARCHITECTURE_COMPARISON_DIR, exist_ok=True)
        print("Directories created")
        sys.stdout.flush()
        
        # Device
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"\nUsing device: {device}")
        sys.stdout.flush()
        
        # Load and prepare data
        print("\nLoading data...")
        sys.stdout.flush()
        X, y, features_used = load_and_combine_data()
        print(f"  Data loaded: {len(X)} samples, {X.shape[1]} features")
        sys.stdout.flush()
        
        # Split data (same split for all models)
        print("Splitting data...")
        sys.stdout.flush()
        X_train, X_temp, y_train, y_temp = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        print("  First split done")
        sys.stdout.flush()
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
        )
        print("  Second split done")
        sys.stdout.flush()
        
        # Normalize features
        print("\nNormalizing features...")
        sys.stdout.flush()
        scaler = StandardScaler()
        print("  Scaler created")
        sys.stdout.flush()
        X_train_scaled = scaler.fit_transform(X_train)
        print("  Train scaled")
        sys.stdout.flush()
        X_val_scaled = scaler.transform(X_val)
        print("  Val scaled")
        sys.stdout.flush()
        X_test_scaled = scaler.transform(X_test)
        print("  Test scaled")
        sys.stdout.flush()
        
        # Train all architectures
        results = []
        
        # 1. MLP Neural Network
        print("\nTraining MLP...")
        sys.stdout.flush()
        try:
            probs, labels, model = train_mlp(X_train_scaled, y_train, X_val_scaled, y_val, X_test_scaled, y_test, device)
            preds = (probs > 0.5).astype(int)
            metrics = calculate_metrics(labels, preds, probs)
            results.append({
                'name': 'MLP Neural Network',
                'probs': probs,
                'labels': labels,
                'metrics': metrics,
                'model': model
            })
            print(f"  ✓ MLP - ROC-AUC: {metrics['roc_auc']:.4f}")
        except Exception as e:
            print(f"  ✗ MLP failed: {e}")
        
        # 2. Logistic Regression
        try:
            probs, labels, model = train_logistic_regression(X_train_scaled, y_train, X_test_scaled, y_test)
            preds = (probs > 0.5).astype(int)
            metrics = calculate_metrics(labels, preds, probs)
            results.append({
                'name': 'Logistic Regression',
                'probs': probs,
                'labels': labels,
                'metrics': metrics,
                'model': model
            })
            print(f"  ✓ Logistic Regression - ROC-AUC: {metrics['roc_auc']:.4f}")
        except Exception as e:
            print(f"  ✗ Logistic Regression failed: {e}")
        
        # 3. Random Forest
        try:
            probs, labels, model = train_random_forest(X_train_scaled, y_train, X_test_scaled, y_test)
            preds = (probs > 0.5).astype(int)
            metrics = calculate_metrics(labels, preds, probs)
            results.append({
                'name': 'Random Forest',
                'probs': probs,
                'labels': labels,
                'metrics': metrics,
                'model': model
            })
            print(f"  ✓ Random Forest - ROC-AUC: {metrics['roc_auc']:.4f}")
        except Exception as e:
            print(f"  ✗ Random Forest failed: {e}")
        
        # 4. Gradient Boosting
        try:
            probs, labels, model = train_gradient_boosting(X_train_scaled, y_train, X_test_scaled, y_test)
            preds = (probs > 0.5).astype(int)
            metrics = calculate_metrics(labels, preds, probs)
            results.append({
                'name': 'Gradient Boosting',
                'probs': probs,
                'labels': labels,
                'metrics': metrics,
                'model': model
            })
            print(f"  ✓ Gradient Boosting - ROC-AUC: {metrics['roc_auc']:.4f}")
        except Exception as e:
            print(f"  ✗ Gradient Boosting failed: {e}")
        
        # 5. XGBoost (if available)
        if XGBOOST_AVAILABLE:
            try:
                probs, labels, model = train_xgboost(X_train_scaled, y_train, X_test_scaled, y_test)
                preds = (probs > 0.5).astype(int)
                metrics = calculate_metrics(labels, preds, probs)
                results.append({
                    'name': 'XGBoost',
                    'probs': probs,
                    'labels': labels,
                    'metrics': metrics,
                    'model': model
                })
                print(f"  ✓ XGBoost - ROC-AUC: {metrics['roc_auc']:.4f}")
            except Exception as e:
                print(f"  ✗ XGBoost failed: {e}")
        
        # 6. LightGBM (if available)
        if LIGHTGBM_AVAILABLE:
            try:
                probs, labels, model = train_lightgbm(X_train_scaled, y_train, X_test_scaled, y_test)
                preds = (probs > 0.5).astype(int)
                metrics = calculate_metrics(labels, preds, probs)
                results.append({
                    'name': 'LightGBM',
                    'probs': probs,
                    'labels': labels,
                    'metrics': metrics,
                    'model': model
                })
                print(f"  ✓ LightGBM - ROC-AUC: {metrics['roc_auc']:.4f}")
            except Exception as e:
                print(f"  ✗ LightGBM failed: {e}")
        
        # 7. SVM (skip for now - can be slow and cause issues)
        # try:
        #     probs, labels, model = train_svm(X_train_scaled, y_train, X_test_scaled, y_test)
        #     preds = (probs > 0.5).astype(int)
        #     metrics = calculate_metrics(labels, preds, probs)
        #     results.append({
        #         'name': 'Support Vector Machine',
        #         'probs': probs,
        #         'labels': labels,
        #         'metrics': metrics,
        #         'model': model
        #     })
        #     print(f"  ✓ SVM - ROC-AUC: {metrics['roc_auc']:.4f}")
        # except Exception as e:
        #     print(f"  ✗ SVM failed: {e}")
        
        if not results:
            print("\n✗ No models trained successfully!")
            return
        
        # Plot all ROC curves
        print(f"\n{'='*70}")
        print("Generating ROC Curves Comparison")
        print(f"{'='*70}")
        plot_all_roc_curves(results, ARCHITECTURE_COMPARISON_DIR)
        
        # Save results table
        print(f"\n{'='*70}")
        print("Saving Results")
        print(f"{'='*70}")
        df = save_results_table(results, ARCHITECTURE_COMPARISON_DIR)
        
        # Print summary
        print(f"\n{'='*70}")
        print("Architecture Comparison Summary")
        print(f"{'='*70}")
        print("\nAll Models (sorted by ROC-AUC):")
        df_sorted = df.sort_values('ROC-AUC', ascending=False)
        df_display = df_sorted.copy()
        for col in ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'ROC-AUC']:
            df_display[col] = df_display[col].apply(lambda x: f"{x:.4f}")
        print(df_display[['Architecture', 'ROC-AUC', 'Accuracy', 'F1-Score']].to_string(index=False))
        
        print(f"\n{'='*70}")
        print("Architecture Comparison Complete!")
        print(f"{'='*70}")
        print(f"\nResults saved to: {ARCHITECTURE_COMPARISON_DIR}/")
        print(f"  - architecture_comparison_roc_curves.png (all ROC curves)")
        print(f"  - architecture_comparison_results.csv (comparison table)")
        print(f"  - architecture_comparison_results.json (detailed results)")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
