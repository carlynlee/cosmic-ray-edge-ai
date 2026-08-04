"""
CREDO Image Processing Module

Based on Zichun's recommendations, uses DINO-v2/v3 vision transformers
for processing CREDO cosmic ray images.
"""

from .dataloader.dataset import CREDOImageDataset
from .dataloader.loader import load_credo_images

# Lazy import for DINO to avoid dependency conflicts
# DINOImageEncoder will only be imported when accessed
def __getattr__(name):
    """Lazy import for DINOImageEncoder to avoid dependency conflicts."""
    if name == 'DINOImageEncoder':
        from .models.dino import DINOImageEncoder
        return DINOImageEncoder
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    'CREDOImageDataset',
    'load_credo_images',
    'DINOImageEncoder',
]

