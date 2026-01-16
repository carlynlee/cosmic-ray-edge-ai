"""
Conversion utilities for RINO integration.
"""

import json
import numpy as np
from typing import List, Dict, Optional
import torch


def events_to_rino_format(
    events: List[Dict],
    max_seq_length: int = 128,
) -> Dict[str, torch.Tensor]:
    """
    Convert CosmicWatch events to RINO-style format.
    
    Note: RINO is designed for particle physics, but we can adapt the format
    for event sequences. This creates a format similar to RINO's particle sequences.
    
    Args:
        events: List of event dictionaries
        max_seq_length: Maximum sequence length
    
    Returns:
        Dictionary with:
        - 'sequence': Event features [seq_len, num_features]
        - 'mask': Valid event mask [seq_len]
    """
    # Extract features (similar to RINO's particle features)
    feature_keys = [
        'adc_value',
        'sipm_mv',
        'temperature_c',
        'pressure_pa',
        'accel_x_g',
        'accel_y_g',
        'accel_z_g',
        'gyro_x_degs',
        'gyro_y_degs',
        'gyro_z_degs',
    ]
    
    features_list = []
    
    for event in events[:max_seq_length]:
        features = []
        for key in feature_keys:
            value = event.get(key, 0.0)
            try:
                features.append(float(value) if value is not None else 0.0)
            except (ValueError, TypeError):
                features.append(0.0)
        features_list.append(features)
    
    # Pad to max_seq_length
    while len(features_list) < max_seq_length:
        features_list.append([0.0] * len(feature_keys))
    
    # Convert to tensors
    sequence = torch.FloatTensor(features_list)  # [seq_len, num_features]
    
    # Create mask
    mask = torch.ones(len(events[:max_seq_length]), dtype=torch.bool)
    if len(events) < max_seq_length:
        padding = torch.zeros(max_seq_length - len(events), dtype=torch.bool)
        mask = torch.cat([mask, padding])
    
    return {
        'sequence': sequence,
        'mask': mask,
    }


def export_for_training(
    events: List[Dict],
    output_path: str,
    format: str = "json",
    split: Optional[Dict[str, float]] = None,
):
    """
    Export events in format suitable for training.
    
    Args:
        events: List of event dictionaries
        output_path: Output file path
        format: Output format ("json", "h5", "csv")
        split: Optional train/val/test split ratios (e.g., {"train": 0.7, "val": 0.15, "test": 0.15})
    """
    if split:
        # Shuffle and split
        np.random.seed(42)
        indices = np.random.permutation(len(events))
        
        train_end = int(len(events) * split.get("train", 0.7))
        val_end = train_end + int(len(events) * split.get("val", 0.15))
        
        train_events = [events[i] for i in indices[:train_end]]
        val_events = [events[i] for i in indices[train_end:val_end]]
        test_events = [events[i] for i in indices[val_end:]]
        
        splits = {
            "train": train_events,
            "val": val_events,
            "test": test_events,
        }
    else:
        splits = {"all": events}
    
    # Export based on format
    if format == "json":
        for split_name, split_events in splits.items():
            split_path = output_path.replace(".json", f"_{split_name}.json")
            with open(split_path, 'w') as f:
                json.dump(split_events, f, indent=2)
            print(f"Exported {len(split_events)} events to {split_path}")
    
    elif format == "csv":
        import pandas as pd
        
        for split_name, split_events in splits.items():
            df = pd.DataFrame(split_events)
            split_path = output_path.replace(".csv", f"_{split_name}.csv")
            df.to_csv(split_path, index=False)
            print(f"Exported {len(split_events)} events to {split_path}")
    
    else:
        raise ValueError(f"Unsupported format: {format}")
