"""
Data loader utilities for CosmicWatch sequences.
"""

import json
import os
from typing import List, Dict, Optional
from pathlib import Path
from .dataset import CosmicWatchSequenceDataset


def load_cosmicwatch_sequences(
    data_path: str,
    max_seq_length: int = 128,
    window_size: Optional[int] = None,
    stride: Optional[int] = None,
    feature_keys: Optional[List[str]] = None,
    normalize: bool = True,
    stats_path: Optional[str] = None,
) -> CosmicWatchSequenceDataset:
    """
    Load CosmicWatch data and create sequence dataset.
    
    Args:
        data_path: Path to JSON file with CosmicWatch events
        max_seq_length: Maximum sequence length
        window_size: Size of sliding window for sequences (None = use all events)
        stride: Stride for sliding window (None = non-overlapping)
        feature_keys: Features to include
        normalize: Whether to normalize features
        stats_path: Path to pre-computed statistics file
    
    Returns:
        CosmicWatchSequenceDataset instance
    """
    # Load data
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    with open(data_path, 'r') as f:
        events = json.load(f)
    
    if not isinstance(events, list):
        raise ValueError("Data file must contain a list of events")
    
    # Sort events by timestamp
    events = sorted(events, key=lambda x: x.get('timestamp_ms', x.get('timestamp', 0)))
    
    # Create sequences
    if window_size is None:
        # Single sequence with all events
        sequences = [events]
    else:
        # Sliding window sequences
        sequences = []
        stride = stride or window_size
        
        for i in range(0, len(events) - window_size + 1, stride):
            sequences.append(events[i:i + window_size])
    
    # Load statistics if provided
    stats = None
    if stats_path and os.path.exists(stats_path):
        stats = CosmicWatchSequenceDataset.load_stats(stats_path)
    
    # Create dataset
    dataset = CosmicWatchSequenceDataset(
        sequences=sequences,
        max_seq_length=max_seq_length,
        feature_keys=feature_keys,
        normalize=normalize,
        stats=stats,
    )
    
    return dataset


def load_from_elasticsearch(
    es_host: str,
    es_user: str,
    es_pass: str,
    es_index: str = "credo-detections",
    max_events: Optional[int] = None,
    output_path: Optional[str] = None,
) -> List[Dict]:
    """
    Load CosmicWatch events from Elasticsearch.
    
    Args:
        es_host: Elasticsearch host URL
        es_user: Elasticsearch username
        es_pass: Elasticsearch password
        es_index: Elasticsearch index name
        max_events: Maximum number of events to load (None = all)
        output_path: Optional path to save exported data
    
    Returns:
        List of event dictionaries
    """
    try:
        from elasticsearch import Elasticsearch
        from elasticsearch.helpers import scan
    except ImportError:
        raise ImportError("elasticsearch package required. Install with: pip install elasticsearch")
    
    # Connect to Elasticsearch
    es = Elasticsearch(
        [es_host],
        basic_auth=(es_user, es_pass),
        verify_certs=False,
        ssl_show_warn=False,
        request_timeout=60
    )
    
    # Query CosmicWatch data
    query = {
        "query": {
            "term": {"source": "cosmicwatch-v3x"}
        },
        "sort": [{"timestamp": {"order": "asc"}}]
    }
    
    if max_events:
        query["size"] = max_events
    
    # Fetch documents
    events = []
    query_body = {"query": {"term": {"source": "cosmicwatch-v3x"}}}
    
    for doc in scan(es, query=query_body, index=es_index, scroll='5m'):
        events.append(doc['_source'])
        
        if max_events and len(events) >= max_events:
            break
    
    # Save to file if requested
    if output_path:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(events, f, indent=2)
        print(f"Saved {len(events)} events to {output_path}")
    
    return events
