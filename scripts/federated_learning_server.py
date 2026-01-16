#!/usr/bin/env python3
"""
Federated Learning Server for Cosmic Ray Event Classification

This server coordinates federated learning across multiple client nodes:
- Node 1: Coincidence events (high-energy muons)
- Node 2: Non-coincidence events (single detector hits)
- Node 3: CREDO.science historical data (optional)

Uses Flower framework for federated learning coordination.
"""

import flwr as fl
import torch
import numpy as np
from typing import Dict, List, Tuple, Optional
import json
import os
from datetime import datetime

# Import model architecture
from train_binary_baseline import BinaryCoincidenceClassifier

class FederatedLearningServer:
    """Federated Learning Server for coordinating model training"""
    
    def __init__(self, num_rounds=5, min_clients=2, min_available_clients=2):
        self.num_rounds = num_rounds
        self.min_clients = min_clients
        self.min_available_clients = min_available_clients
        self.round_history = []
        
    def weighted_average(self, metrics: List[Tuple[int, Dict]]) -> Dict:
        """Calculate weighted average of metrics"""
        # Extract accuracies and sample counts
        accuracies = [m[1]["accuracy"] for m in metrics]
        samples = [m[0] for m in metrics]
        
        # Calculate weighted average
        total_samples = sum(samples)
        weighted_acc = sum(acc * num for acc, num in zip(accuracies, samples)) / total_samples
        
        return {"accuracy": weighted_acc}
    
    def fit_config(self, rnd: int) -> Dict:
        """Return training configuration for each round"""
        return {
            "round": rnd,
            "epochs": 5,  # Fewer epochs per round for faster FL
            "batch_size": 32,
            "learning_rate": 0.001,
        }
    
    def evaluate_config(self, rnd: int) -> Dict:
        """Return evaluation configuration"""
        return {"round": rnd}

def main():
    print("=" * 70)
    print("Federated Learning Server - Cosmic Ray Event Classification")
    print("=" * 70)
    print()
    print("Server Configuration:")
    print(f"  Framework: Flower (Flwr)")
    print(f"  Minimum clients: 2")
    print(f"  Expected clients: 3 (Node 1: Coincidence, Node 2: Non-coincidence, Node 3: CREDO)")
    print()
    print("Starting server...")
    print("Waiting for clients to connect...")
    print()
    
    # Create server strategy
    strategy = fl.server.strategy.FedAvg(
        fraction_fit=1.0,  # Use all available clients
        fraction_evaluate=1.0,  # Evaluate on all clients
        min_fit_clients=2,  # Minimum 2 clients required
        min_available_clients=2,
        evaluate_metrics_aggregation_fn=lambda metrics: {
            "accuracy": sum(m[1]["accuracy"] * m[0] for m in metrics) / sum(m[0] for m in metrics)
        },
        on_fit_config_fn=lambda rnd: {
            "round": rnd,
            "epochs": 5,
            "batch_size": 32,
            "learning_rate": 0.001,
        },
    )
    
    # Start server
    fl.server.start_server(
        server_address="0.0.0.0:8080",
        config=fl.server.ServerConfig(num_rounds=5),
        strategy=strategy,
    )
    
    print("\n✓ Federated learning server stopped")

if __name__ == "__main__":
    main()




