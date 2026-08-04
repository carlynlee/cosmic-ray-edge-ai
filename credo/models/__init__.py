"""Models for CREDO image processing."""

# Lazy import - DINOImageEncoder is imported only when needed
# This avoids dependency conflicts with tensorflow/protobuf when
# only data loading functionality is used

__all__ = ['DINOImageEncoder']

def __getattr__(name):
    """Lazy import for DINOImageEncoder."""
    if name == 'DINOImageEncoder':
        from .dino import DINOImageEncoder
        return DINOImageEncoder
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

