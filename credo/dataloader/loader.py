"""
CREDO Image Data Loader

Utilities for loading CREDO images from various sources.
"""

from typing import List, Dict, Optional
from .dataset import CREDOImageDataset


def load_credo_images(
    source: str,
    image_key: str = 'frame_content',
    image_size: int = 224,
    transform: Optional[callable] = None,
    **kwargs
) -> CREDOImageDataset:
    """
    Load CREDO images from various sources.
    
    Args:
        source: Source of images - can be:
            - JSON file path
            - Elasticsearch index name (requires es_client in kwargs)
        image_key: Key in data containing image
        image_size: Target image size
        transform: Optional transform
        **kwargs: Additional arguments
    
    Returns:
        CREDOImageDataset
    """
    if source.endswith('.json'):
        # Load from JSON file
        return CREDOImageDataset.from_json(
            source,
            image_key=image_key,
            image_size=image_size,
            transform=transform,
        )
    else:
        # Assume Elasticsearch index
        es_client = kwargs.get('es_client')
        if es_client is None:
            raise ValueError("For Elasticsearch source, 'es_client' must be provided in kwargs")
        
        query = kwargs.get('query')
        size = kwargs.get('size', 1000)
        
        return CREDOImageDataset.from_elasticsearch(
            es_client,
            index=source,
            query=query,
            size=size,
            image_key=image_key,
            image_size=image_size,
            transform=transform,
        )


