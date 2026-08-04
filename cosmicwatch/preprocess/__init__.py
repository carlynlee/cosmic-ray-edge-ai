"""
CosmicWatch Preprocessing for RINO Integration

Preprocessing utilities to convert CosmicWatch events into sequences
suitable for transformer-based self-supervised learning.
"""

from .sequences import preprocess_events_to_sequences, create_event_tokens

__all__ = ["preprocess_events_to_sequences", "create_event_tokens"]
