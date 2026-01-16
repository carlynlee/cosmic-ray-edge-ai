#!/usr/bin/env python3
"""
Example: CosmicWatch Data for RINO-Style Training

This example shows how to use CosmicWatch data with transformer models
for self-supervised learning, following RINO team's recommendations.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cosmicwatch import load_cosmicwatch_sequences, preprocess_events_to_sequences
from torch.utils.data import DataLoader
import torch


def example_1_load_sequences():
    """Example 1: Load CosmicWatch sequences from JSON file."""
    print("=" * 60)
    print("Example 1: Loading CosmicWatch Sequences")
    print("=" * 60)
    
    # Path to exported CosmicWatch data
    data_path = "scripts/data/cosmicwatch_data_export.json"
    
    if not os.path.exists(data_path):
        print(f"Data file not found: {data_path}")
        print("Please run scripts/export_cosmicwatch_data.py first")
        return
    
    # Load sequences with sliding window
    dataset = load_cosmicwatch_sequences(
        data_path=data_path,
        max_seq_length=128,
        window_size=128,  # Events per sequence
        stride=64,  # Overlapping windows
        normalize=True,
    )
    
    print(f"Loaded {len(dataset)} sequences")
    print(f"Feature dimension: {len(dataset.feature_keys)}")
    print(f"Max sequence length: {dataset.max_seq_length}")
    
    # Get a sample
    sample = dataset[0]
    print(f"\nSample sequence shape: {sample['sequence'].shape}")
    print(f"Sample mask shape: {sample['mask'].shape}")
    print(f"Valid events in sample: {sample['mask'].sum().item()}")
    
    return dataset


def example_2_create_dataloader():
    """Example 2: Create PyTorch DataLoader for training."""
    print("\n" + "=" * 60)
    print("Example 2: Creating DataLoader for Training")
    print("=" * 60)
    
    data_path = "scripts/data/cosmicwatch_data_export.json"
    
    if not os.path.exists(data_path):
        print(f"Data file not found: {data_path}")
        return
    
    # Load dataset
    dataset = load_cosmicwatch_sequences(
        data_path=data_path,
        max_seq_length=128,
        window_size=128,
        stride=64,
    )
    
    # Create DataLoader
    dataloader = DataLoader(
        dataset,
        batch_size=32,
        shuffle=True,
        num_workers=4,
        pin_memory=True,
    )
    
    print(f"DataLoader created with {len(dataloader)} batches")
    
    # Get a batch
    batch = next(iter(dataloader))
    print(f"\nBatch sequence shape: {batch['sequence'].shape}")  # [batch, seq_len, features]
    print(f"Batch mask shape: {batch['mask'].shape}")  # [batch, seq_len]
    
    return dataloader


def example_3_bert_style_training():
    """Example 3: Prepare data for BERT-style pre-training."""
    print("\n" + "=" * 60)
    print("Example 3: BERT-Style Pre-training Setup")
    print("=" * 60)
    
    print("""
    For BERT-style pre-training (as recommended by RINO team):
    
    1. Use HuggingFace Transformers library
    2. Each event is a "token" with features as embeddings
    3. Apply masked event modeling (similar to masked language modeling)
    
    Example code:
    
    from transformers import AutoModel, AutoConfig
    import torch.nn as nn
    
    # Create custom token embeddings from event features
    class EventEmbedding(nn.Module):
        def __init__(self, feature_dim, hidden_dim):
            super().__init__()
            self.linear = nn.Linear(feature_dim, hidden_dim)
        
        def forward(self, events):
            return self.linear(events)
    
    # Load BERT model
    config = AutoConfig.from_pretrained("bert-base-uncased")
    model = AutoModel.from_pretrained("bert-base-uncased")
    
    # Replace token embeddings with event embeddings
    model.embeddings.word_embeddings = EventEmbedding(
        feature_dim=10,  # Number of event features
        hidden_dim=config.hidden_size
    )
    
    # Training loop with masked event modeling
    for batch in dataloader:
        sequences = batch['sequence']  # [batch, seq_len, features]
        masks = batch['mask']
        
        # Apply random masking (15% of events)
        masked_sequences, labels = apply_masking(sequences, mask_prob=0.15)
        
        # Forward pass
        outputs = model(inputs_embeds=masked_sequences)
        loss = compute_masked_loss(outputs, labels)
    """)
    
    print("\nSee cosmicwatch/examples/bert_pretraining.py for full example")


def example_4_export_for_rino():
    """Example 4: Export data in RINO-compatible format."""
    print("\n" + "=" * 60)
    print("Example 4: Export for RINO Integration")
    print("=" * 60)
    
    from cosmicwatch.utils import export_for_training
    import json
    
    data_path = "scripts/data/cosmicwatch_data_export.json"
    
    if not os.path.exists(data_path):
        print(f"Data file not found: {data_path}")
        return
    
    with open(data_path, 'r') as f:
        events = json.load(f)
    
    # Export with train/val/test split
    export_for_training(
        events=events,
        output_path="scripts/data/cosmicwatch_training.json",
        format="json",
        split={"train": 0.7, "val": 0.15, "test": 0.15},
    )
    
    print("Data exported for training!")


if __name__ == "__main__":
    print("CosmicWatch RINO Integration Examples")
    print("=" * 60)
    
    # Run examples
    try:
        dataset = example_1_load_sequences()
        dataloader = example_2_create_dataloader()
        example_3_bert_style_training()
        example_4_export_for_rino()
        
        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("\nPlease ensure you have:")
        print("1. Exported CosmicWatch data (run scripts/export_cosmicwatch_data.py)")
        print("2. Data file exists at scripts/data/cosmicwatch_data_export.json")
