"""
CREDO Image Dataset

Dataset for loading and processing CREDO cosmic ray images
for DINO-v2/v3 vision transformers.
"""

import torch
from torch.utils.data import Dataset
import numpy as np
from PIL import Image
import io
import base64
from typing import List, Dict, Optional, Union
import json


class CREDOImageDataset(Dataset):
    """
    Dataset for CREDO cosmic ray images.
    
    Loads images from CREDO detection data and prepares them for
    DINO-v2/v3 vision transformer models.
    
    Images can be provided as:
    - Base64-encoded strings (from Elasticsearch)
    - File paths
    - PIL Image objects
    - NumPy arrays
    """
    
    def __init__(
        self,
        images: List[Dict],
        image_size: int = 224,
        transform: Optional[callable] = None,
        image_key: str = 'frame_content',
    ):
        """
        Initialize dataset.
        
        Args:
            images: List of image dictionaries, each containing image data
            image_size: Target image size (default 224 for DINO)
            transform: Optional torchvision transform to apply
            image_key: Key in dictionary containing image data
        """
        self.images = images
        self.image_size = image_size
        self.transform = transform
        self.image_key = image_key
    
    def _decode_image(self, image_data: Union[str, bytes, np.ndarray]) -> Image.Image:
        """
        Decode image from various formats.
        
        Supports:
        - Base64-encoded strings
        - Raw bytes
        - NumPy arrays
        - PIL Images (returned as-is)
        """
        # If already a PIL Image, return it
        if isinstance(image_data, Image.Image):
            return image_data
        
        # If numpy array, convert to PIL
        if isinstance(image_data, np.ndarray):
            return Image.fromarray(image_data)
        
        # If bytes, decode directly
        if isinstance(image_data, bytes):
            return Image.open(io.BytesIO(image_data))
        
        # If string, try base64 decode
        if isinstance(image_data, str):
            try:
                # Try base64 decode
                image_bytes = base64.b64decode(image_data)
                return Image.open(io.BytesIO(image_bytes))
            except Exception:
                # If not base64, try as file path
                try:
                    return Image.open(image_data)
                except Exception as e:
                    raise ValueError(f"Could not decode image data: {e}")
        
        raise ValueError(f"Unsupported image format: {type(image_data)}")
    
    def _process_image(self, image: Image.Image) -> torch.Tensor:
        """
        Process image for DINO model.
        
        Args:
            image: PIL Image
            
        Returns:
            Tensor of shape [3, H, W] (normalized for DINO)
        """
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize to target size
        image = image.resize((self.image_size, self.image_size), Image.Resampling.BILINEAR)
        
        # Convert to tensor
        image_tensor = torch.from_numpy(np.array(image)).permute(2, 0, 1).float() / 255.0
        
        # Apply transform if provided
        if self.transform is not None:
            image_tensor = self.transform(image_tensor)
        else:
            # Default normalization for ImageNet (DINO uses this)
            mean = torch.tensor([0.485, 0.456, 0.406])
            std = torch.tensor([0.229, 0.224, 0.225])
            image_tensor = (image_tensor - mean.view(3, 1, 1)) / std.view(3, 1, 1)
        
        return image_tensor
    
    def __len__(self) -> int:
        return len(self.images)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        """
        Get image and metadata.
        
        Returns:
            Dictionary with:
            - 'image': Image tensor [3, H, W]
            - 'metadata': Dictionary with original data (device_id, timestamp, etc.)
        """
        item = self.images[idx]
        
        # Extract image data
        image_data = item.get(self.image_key)
        if image_data is None:
            raise ValueError(f"Image key '{self.image_key}' not found in item {idx}")
        
        # Decode and process image
        pil_image = self._decode_image(image_data)
        image_tensor = self._process_image(pil_image)
        
        # Extract metadata (everything except image data)
        metadata = {k: v for k, v in item.items() if k != self.image_key}
        
        return {
            'image': image_tensor,
            'metadata': metadata,
        }
    
    @classmethod
    def from_json(cls, json_path: str, **kwargs) -> 'CREDOImageDataset':
        """
        Load dataset from JSON file.
        
        Args:
            json_path: Path to JSON file containing CREDO detection data
            **kwargs: Additional arguments passed to __init__
        """
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(data, dict):
            # If it's a dict, look for common keys like 'detections', 'data', etc.
            if 'detections' in data:
                items = data['detections']
            elif 'data' in data:
                items = data['data']
            else:
                # If no common key, try to use the dict values
                items = list(data.values())
                if items and isinstance(items[0], list):
                    items = items[0]
                else:
                    items = [data]  # Single item
        elif isinstance(data, list):
            items = data
        else:
            raise ValueError(f"Unexpected JSON structure: {type(data)}")
        
        # Filter to only items with image data
        image_key = kwargs.get('image_key', 'frame_content')
        images = [item for item in items if isinstance(item, dict) and item.get(image_key)]
        
        return cls(images, **kwargs)
    
    @classmethod
    def from_elasticsearch(
        cls,
        es_client,
        index: str = 'credo-detections',
        query: Optional[Dict] = None,
        size: int = 1000,
        **kwargs
    ) -> 'CREDOImageDataset':
        """
        Load dataset from Elasticsearch.
        
        Args:
            es_client: Elasticsearch client
            index: Index name
            query: Optional Elasticsearch query
            size: Maximum number of documents to load
            **kwargs: Additional arguments passed to __init__
        """
        if query is None:
            query = {'match_all': {}}
        
        response = es_client.search(
            index=index,
            body={'query': query, 'size': size},
            _source=True,
        )
        
        images = [hit['_source'] for hit in response['hits']['hits']]
        
        # Filter to only items with image data
        image_key = kwargs.get('image_key', 'frame_content')
        images = [item for item in images if item.get(image_key)]
        
        return cls(images, **kwargs)

