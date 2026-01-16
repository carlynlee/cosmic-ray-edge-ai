"""
Preprocessing functions for converting events to sequences.
"""

from typing import List, Dict, Optional
import numpy as np


def create_event_tokens(
    events: List[Dict],
    feature_keys: Optional[List[str]] = None,
) -> List[np.ndarray]:
    """
    Convert events to token vectors.
    
    Each event becomes a token with features as the token embedding.
    This is similar to how BERT tokenizes text, but for event data.
    
    Args:
        events: List of event dictionaries
        feature_keys: Features to include in token
    
    Returns:
        List of feature vectors (one per event)
    """
    if feature_keys is None:
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
    
    tokens = []
    
    for event in events:
        token = []
        for key in feature_keys:
            value = event.get(key)
            if value is None:
                token.append(0.0)
            else:
                try:
                    token.append(float(value))
                except (ValueError, TypeError):
                    token.append(0.0)
        
        tokens.append(np.array(token, dtype=np.float32))
    
    return tokens


def preprocess_events_to_sequences(
    events: List[Dict],
    window_size: int = 128,
    stride: Optional[int] = None,
    min_events_per_sequence: int = 1,
) -> List[List[Dict]]:
    """
    Convert events into sequences using sliding window.
    
    Args:
        events: List of event dictionaries (should be sorted by timestamp)
        window_size: Number of events per sequence
        stride: Step size for sliding window (None = non-overlapping)
        min_events_per_sequence: Minimum events required for a valid sequence
    
    Returns:
        List of sequences, where each sequence is a list of events
    """
    if stride is None:
        stride = window_size
    
    sequences = []
    
    for i in range(0, len(events) - window_size + 1, stride):
        sequence = events[i:i + window_size]
        
        if len(sequence) >= min_events_per_sequence:
            sequences.append(sequence)
    
    return sequences


def add_positional_encoding(
    sequences: List[List[Dict]],
    use_timestamps: bool = True,
) -> List[List[Dict]]:
    """
    Add positional encoding to sequences.
    
    For time-based sequences, we can use relative timestamps as positional encoding.
    For BERT/GPT models, this can be added to the token embeddings.
    
    Args:
        sequences: List of event sequences
        use_timestamps: Whether to use timestamps for positional encoding
    
    Returns:
        Sequences with positional information added
    """
    encoded_sequences = []
    
    for sequence in sequences:
        encoded_sequence = []
        base_time = None
        
        for event in sequence:
            encoded_event = event.copy()
            
            if use_timestamps:
                ts = event.get('timestamp_ms') or event.get('timestamp') or event.get('time')
                
                if ts is not None:
                    try:
                        ts_float = float(ts)
                        if base_time is None:
                            base_time = ts_float
                        
                        # Add relative time as positional feature
                        encoded_event['relative_time'] = ts_float - base_time
                    except (ValueError, TypeError):
                        encoded_event['relative_time'] = 0.0
                else:
                    encoded_event['relative_time'] = 0.0
            
            encoded_sequence.append(encoded_event)
        
        encoded_sequences.append(encoded_sequence)
    
    return encoded_sequences
