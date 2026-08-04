"""
DINO Image Encoder for CREDO Images

Based on Zichun's recommendations, uses DINO-v2/v3 for processing
CREDO cosmic ray images.
"""

import torch
import torch.nn as nn
from transformers import AutoImageProcessor, AutoModel
from typing import Optional, Union, Tuple


class DINOImageEncoder(nn.Module):
    """
    DINO-based image encoder for CREDO images.
    
    Uses pre-trained DINO-v2 or DINO-v3 models from META.
    Can be used for:
    - Feature extraction
    - Fine-tuning for cosmic ray detection
    - Multi-modal fusion (with CosmicWatch event embeddings)
    """
    
    def __init__(
        self,
        model_name: str = 'facebook/dinov2-base',
        freeze_backbone: bool = False,
        output_dim: Optional[int] = None,
    ):
        """
        Initialize DINO encoder.
        
        Args:
            model_name: HuggingFace model name
                - 'facebook/dinov2-base' (default)
                - 'facebook/dinov2-large'
                - 'facebook/dinov2-giant'
                - Or DINO-v3 models when available
            freeze_backbone: Whether to freeze pre-trained weights
            output_dim: Optional output dimension (for fine-tuning head)
        """
        super().__init__()
        
        # Load DINO model and processor
        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        
        # Freeze backbone if requested
        if freeze_backbone:
            for param in self.model.parameters():
                param.requires_grad = False
        
        # Get model dimension
        self.hidden_dim = self.model.config.hidden_size
        
        # Optional projection head for fine-tuning
        self.output_dim = output_dim
        if output_dim is not None:
            self.projection = nn.Linear(self.hidden_dim, output_dim)
        else:
            self.projection = None
    
    def forward(
        self,
        images: torch.Tensor,
        return_pooled: bool = True,
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """
        Forward pass.
        
        Args:
            images: Image tensor [batch, 3, H, W] (already preprocessed)
            return_pooled: Whether to return pooled features (CLS token)
            
        Returns:
            If return_pooled=True: Pooled features [batch, hidden_dim]
            If return_pooled=False: Full sequence [batch, seq_len, hidden_dim]
            If projection exists: Projected features [batch, output_dim]
        """
        # Forward through DINO model
        # Note: images should already be preprocessed (normalized, resized)
        outputs = self.model(pixel_values=images)
        
        # Extract features
        if return_pooled:
            # Use CLS token (first token) as pooled representation
            features = outputs.last_hidden_state[:, 0, :]  # [batch, hidden_dim]
        else:
            features = outputs.last_hidden_state  # [batch, seq_len, hidden_dim]
        
        # Apply projection if exists
        if self.projection is not None:
            features = self.projection(features)
        
        return features
    
    def extract_features(
        self,
        images: torch.Tensor,
        normalize: bool = True,
    ) -> torch.Tensor:
        """
        Extract features from images (convenience method).
        
        Args:
            images: Image tensor [batch, 3, H, W]
            normalize: Whether to L2 normalize features
            
        Returns:
            Features [batch, hidden_dim] or [batch, output_dim]
        """
        with torch.no_grad():
            features = self.forward(images, return_pooled=True)
        
        if normalize:
            features = nn.functional.normalize(features, p=2, dim=1)
        
        return features
    
    def fine_tune_for_classification(
        self,
        num_classes: int,
        freeze_backbone: bool = True,
    ) -> nn.Module:
        """
        Add classification head for fine-tuning.
        
        Args:
            num_classes: Number of classes (e.g., 2 for binary: cosmic ray / not)
            freeze_backbone: Whether to freeze backbone during fine-tuning
            
        Returns:
            Complete model with classification head
        """
        # Freeze backbone if requested
        if freeze_backbone:
            for param in self.model.parameters():
                param.requires_grad = False
        
        # Add classification head
        classifier = nn.Sequential(
            nn.Linear(self.hidden_dim, self.hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(self.hidden_dim // 2, num_classes),
        )
        
        return nn.ModuleDict({
            'backbone': self.model,
            'classifier': classifier,
        })
    
    @classmethod
    def from_pretrained(
        cls,
        model_name: str = 'facebook/dinov2-base',
        **kwargs
    ) -> 'DINOImageEncoder':
        """
        Create encoder from pre-trained model.
        
        Args:
            model_name: Model name
            **kwargs: Additional arguments for __init__
        """
        return cls(model_name=model_name, **kwargs)


def create_dino_classifier(
    model_name: str = 'facebook/dinov2-base',
    num_classes: int = 2,
    freeze_backbone: bool = True,
) -> nn.Module:
    """
    Create DINO model with classification head.
    
    Convenience function for creating a complete classification model.
    
    Args:
        model_name: DINO model name
        num_classes: Number of classes
        freeze_backbone: Whether to freeze backbone
        
    Returns:
        Model with backbone + classifier
    """
    encoder = DINOImageEncoder(model_name=model_name, freeze_backbone=freeze_backbone)
    return encoder.fine_tune_for_classification(num_classes, freeze_backbone)


