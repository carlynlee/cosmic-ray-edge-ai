"""
CosmicWatch Data Processing Module for RINO Integration

This module provides tools for processing CosmicWatch Desktop Muon Detector data
and preparing it for self-supervised learning with RINO-style frameworks.

Key Components:
- dataloader: Data loading and sequence formatting
- preprocess: Event sequence preprocessing
- utils: Utility functions for data conversion
"""

__version__ = "0.1.0"

from .dataloader import CosmicWatchSequenceDataset, load_cosmicwatch_sequences
from .preprocess import preprocess_events_to_sequences, create_event_tokens

__all__ = [
    "CosmicWatchSequenceDataset",
    "load_cosmicwatch_sequences",
    "preprocess_events_to_sequences",
    "create_event_tokens",
]
