"""
CosmicWatch Data Loader for RINO Integration

This module provides data loaders that format CosmicWatch events as sequences
compatible with transformer-based self-supervised learning frameworks.
"""

from .dataset import CosmicWatchSequenceDataset
from .loader import load_cosmicwatch_sequences

__all__ = ["CosmicWatchSequenceDataset", "load_cosmicwatch_sequences"]
