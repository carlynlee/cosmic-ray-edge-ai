"""
CosmicWatch Sequence Dataset

Converts CosmicWatch event data into sequences suitable for transformer models
(BERT/GPT-style) as recommended by the RINO team.
"""

import torch
from torch.utils.data import Dataset
import numpy as np
from typing import List, Dict, Optional, Tuple
import json


class CosmicWatchSequenceDataset(Dataset):
    """
    Dataset for CosmicWatch event sequences.
    
    Formats events as sequences where each event is a "token" with features:
    - ADC values
    - SiPM voltage
    - Timestamp (relative)
    - Environmental sensors (temperature, pressure)
    - Motion sensors (accelerometer, gyroscope)
    
    Compatible with BERT/GPT-style transformer models for sequential event data.
    """
    
    def __init__(
        self,
        sequences: List[List[Dict]],
        max_seq_length: int = 128,
        feature_keys: Optional[List[str]] = None,
        normalize: bool = True,
        stats: Optional[Dict] = None,
    ):
        """
        Initialize dataset.
        
        Args:
            sequences: List of event sequences, where each sequence is a list of events
            max_seq_length: Maximum sequence length (will pad or truncate)
            feature_keys: List of feature keys to include (default: all available)
            normalize: Whether to normalize features
            stats: Pre-computed statistics for normalization (mean, std)
        """
        self.sequences = sequences
        self.max_seq_length = max_seq_length
        
        # Default feature keys (all available event features)
        if feature_keys is None:
            self.feature_keys = [
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
        else:
            self.feature_keys = feature_keys
        
        self.normalize = normalize
        
        # Compute statistics if not provided
        if stats is None and normalize:
            self.stats = self._compute_stats()
        else:
            self.stats = stats or {}
    
    def _compute_stats(self) -> Dict:
        """Compute mean and std for normalization."""
        all_features = []
        
        for seq in self.sequences:
            for event in seq:
                features = self._extract_features(event)
                if features is not None:
                    all_features.append(features)
        
        if not all_features:
            return {}
        
        all_features = np.array(all_features)
        stats = {}
        
        for i, key in enumerate(self.feature_keys):
            values = all_features[:, i]
            # Filter out NaN and None values
            valid_values = values[~np.isnan(values)]
            if len(valid_values) > 0:
                stats[key] = {
                    'mean': float(np.mean(valid_values)),
                    'std': float(np.std(valid_values)) if np.std(valid_values) > 0 else 1.0,
                }
            else:
                stats[key] = {'mean': 0.0, 'std': 1.0}
        
        return stats
    
    def _extract_features(self, event: Dict) -> Optional[np.ndarray]:
        """Extract feature vector from event."""
        features = []
        
        for key in self.feature_keys:
            value = event.get(key)
            if value is None:
                features.append(0.0)  # Fill missing with 0
            else:
                try:
                    features.append(float(value))
                except (ValueError, TypeError):
                    features.append(0.0)
        
        return np.array(features, dtype=np.float32)
    
    def _normalize_features(self, features: np.ndarray) -> np.ndarray:
        """Normalize features using computed statistics."""
        if not self.normalize or not self.stats:
            return features
        
        normalized = features.copy()
        
        for i, key in enumerate(self.feature_keys):
            if key in self.stats:
                mean = self.stats[key]['mean']
                std = self.stats[key]['std']
                if std > 0:
                    normalized[i] = (features[i] - mean) / std
        
        return normalized
    
    def _compute_relative_timestamps(self, events: List[Dict]) -> List[float]:
        """Compute relative timestamps for events in sequence."""
        timestamps = []
        base_time = None
        
        for event in events:
            # Try different timestamp fields
            ts = event.get('timestamp_ms') or event.get('timestamp') or event.get('time')
            
            if ts is not None:
                try:
                    ts_float = float(ts)
                    if base_time is None:
                        base_time = ts_float
                    timestamps.append(ts_float - base_time)  # Relative to first event
                except (ValueError, TypeError):
                    timestamps.append(0.0)
            else:
                timestamps.append(0.0)
        
        return timestamps
    
    def __len__(self) -> int:
        return len(self.sequences)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        """
        Get a sequence of events.
        
        Returns:
            Dictionary with:
            - 'sequence': Event features [seq_len, num_features]
            - 'mask': Valid event mask [seq_len]
            - 'timestamps': Relative timestamps [seq_len] (optional)
        """
        events = self.sequences[idx]
        
        # Truncate or pad to max_seq_length
        if len(events) > self.max_seq_length:
            events = events[:self.max_seq_length]
        
        # Extract features
        features_list = []
        for event in events:
            features = self._extract_features(event)
            if features is not None:
                features = self._normalize_features(features)
                features_list.append(features)
            else:
                # Zero vector for invalid events
                features_list.append(np.zeros(len(self.feature_keys), dtype=np.float32))
        
        # Pad to max_seq_length
        while len(features_list) < self.max_seq_length:
            features_list.append(np.zeros(len(self.feature_keys), dtype=np.float32))
        
        # Convert to tensor
        sequence = torch.FloatTensor(np.array(features_list))  # [seq_len, num_features]
        
        # Create mask (1 for valid events, 0 for padding)
        mask = torch.ones(len(events), dtype=torch.bool)
        if len(events) < self.max_seq_length:
            padding = torch.zeros(self.max_seq_length - len(events), dtype=torch.bool)
            mask = torch.cat([mask, padding])
        
        # Compute relative timestamps
        timestamps = self._compute_relative_timestamps(events)
        if len(timestamps) < self.max_seq_length:
            timestamps.extend([0.0] * (self.max_seq_length - len(timestamps)))
        timestamps = torch.FloatTensor(timestamps[:self.max_seq_length])
        
        return {
            'sequence': sequence,
            'mask': mask,
            'timestamps': timestamps,
        }
    
    def get_stats(self) -> Dict:
        """Get normalization statistics."""
        return self.stats
    
    def save_stats(self, path: str):
        """Save normalization statistics to file."""
        with open(path, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    @classmethod
    def load_stats(cls, path: str) -> Dict:
        """Load normalization statistics from file."""
        with open(path, 'r') as f:
            return json.load(f)
