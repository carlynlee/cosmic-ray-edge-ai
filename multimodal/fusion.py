"""
Multi-Modal Fusion

Combines CREDO image embeddings (from DINO) with CosmicWatch event embeddings
(from BERT) into a unified representation space.

Based on Zichun's recommendation: "This could be powerful for tasks like
identifying high-confidence events by requiring agreement across both the
visual features and the sequential sensor data."
"""

import torch
import torch.nn as nn
from typing import Optional, Dict, Tuple


class MultiModalFusion(nn.Module):
    """
    Multi-modal fusion layer combining image and event embeddings.
    
    Architecture:
    1. Image encoder (DINO) -> image_features
    2. Event encoder (BERT) -> event_features
    3. Fusion layer -> unified_features
    4. Optional: Classification/regression head
    """
    
    def __init__(
        self,
        image_encoder: nn.Module,
        event_encoder: nn.Module,
        image_dim: int,
        event_dim: int,
        fusion_dim: int = 512,
        fusion_method: str = 'concat',  # 'concat', 'add', 'attention'
        dropout: float = 0.1,
    ):
        """
        Initialize multi-modal fusion.
        
        Args:
            image_encoder: DINO image encoder
            event_encoder: BERT event encoder
            image_dim: Dimension of image embeddings
            event_dim: Dimension of event embeddings
            fusion_dim: Dimension of fused representation
            fusion_method: How to fuse ('concat', 'add', 'attention')
            dropout: Dropout rate
        """
        super().__init__()
        
        self.image_encoder = image_encoder
        self.event_encoder = event_encoder
        self.image_dim = image_dim
        self.event_dim = event_dim
        self.fusion_dim = fusion_dim
        self.fusion_method = fusion_method
        
        # Fusion layer
        if fusion_method == 'concat':
            input_dim = image_dim + event_dim
            self.fusion = nn.Sequential(
                nn.Linear(input_dim, fusion_dim),
                nn.LayerNorm(fusion_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            )
        elif fusion_method == 'add':
            # Project both to same dimension
            assert image_dim == event_dim, "For 'add' fusion, image_dim must equal event_dim"
            self.image_proj = nn.Linear(image_dim, fusion_dim)
            self.event_proj = nn.Linear(event_dim, fusion_dim)
            self.fusion = nn.Sequential(
                nn.LayerNorm(fusion_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            )
        elif fusion_method == 'attention':
            # Cross-attention fusion
            self.image_proj = nn.Linear(image_dim, fusion_dim)
            self.event_proj = nn.Linear(event_dim, fusion_dim)
            self.attention = nn.MultiheadAttention(fusion_dim, num_heads=8, batch_first=True)
            self.fusion = nn.Sequential(
                nn.LayerNorm(fusion_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
            )
        else:
            raise ValueError(f"Unknown fusion method: {fusion_method}")
    
    def forward(
        self,
        images: torch.Tensor,
        events: torch.Tensor,
        event_mask: Optional[torch.Tensor] = None,
        return_individual: bool = False,
    ) -> Union[torch.Tensor, Tuple[torch.Tensor, Dict[str, torch.Tensor]]]:
        """
        Forward pass.
        
        Args:
            images: Image tensor [batch, 3, H, W]
            events: Event sequence [batch, seq_len, event_features]
            event_mask: Event mask [batch, seq_len] (optional)
            return_individual: Whether to return individual embeddings
            
        Returns:
            If return_individual=False: Fused features [batch, fusion_dim]
            If return_individual=True: (fused_features, {'image': ..., 'event': ...})
        """
        # Encode images
        image_features = self.image_encoder(images, return_pooled=True)  # [batch, image_dim]
        
        # Encode events
        if event_mask is not None:
            event_features = self.event_encoder(
                inputs_embeds=events,
                attention_mask=event_mask,
            )
        else:
            event_features = self.event_encoder(inputs_embeds=events)
        
        # Get pooled event features (CLS token or mean pooling)
        if hasattr(event_features, 'pooler_output') and event_features.pooler_output is not None:
            event_pooled = event_features.pooler_output  # [batch, event_dim]
        else:
            # Mean pooling over sequence
            if event_mask is not None:
                mask_expanded = event_mask.unsqueeze(-1).float()
                event_pooled = (event_features.last_hidden_state * mask_expanded).sum(1) / mask_expanded.sum(1)
            else:
                event_pooled = event_features.last_hidden_state.mean(1)
        
        # Fuse features
        if self.fusion_method == 'concat':
            fused = torch.cat([image_features, event_pooled], dim=1)
            fused = self.fusion(fused)
        elif self.fusion_method == 'add':
            image_proj = self.image_proj(image_features)
            event_proj = self.event_proj(event_pooled)
            fused = image_proj + event_proj
            fused = self.fusion(fused)
        elif self.fusion_method == 'attention':
            # Use events as query, image as key/value
            image_proj = self.image_proj(image_features).unsqueeze(1)  # [batch, 1, fusion_dim]
            event_proj = self.event_proj(event_pooled).unsqueeze(1)  # [batch, 1, fusion_dim]
            
            # Cross-attention: event attends to image
            fused, _ = self.attention(event_proj, image_proj, image_proj)
            fused = fused.squeeze(1)  # [batch, fusion_dim]
            fused = self.fusion(fused)
        
        if return_individual:
            return fused, {
                'image': image_features,
                'event': event_pooled,
            }
        return fused


def create_multimodal_model(
    image_encoder: nn.Module,
    event_encoder: nn.Module,
    image_dim: int,
    event_dim: int,
    fusion_dim: int = 512,
    num_classes: Optional[int] = None,
    fusion_method: str = 'concat',
) -> nn.Module:
    """
    Create complete multi-modal model with optional classification head.
    
    Args:
        image_encoder: DINO image encoder
        event_encoder: BERT event encoder
        image_dim: Image embedding dimension
        event_dim: Event embedding dimension
        fusion_dim: Fusion dimension
        num_classes: Optional number of classes for classification
        fusion_method: Fusion method
        
    Returns:
        Complete model (fusion + optional classifier)
    """
    fusion = MultiModalFusion(
        image_encoder=image_encoder,
        event_encoder=event_encoder,
        image_dim=image_dim,
        event_dim=event_dim,
        fusion_dim=fusion_dim,
        fusion_method=fusion_method,
    )
    
    if num_classes is not None:
        classifier = nn.Sequential(
            nn.Linear(fusion_dim, fusion_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(fusion_dim // 2, num_classes),
        )
        
        return nn.ModuleDict({
            'fusion': fusion,
            'classifier': classifier,
        })
    
    return fusion


