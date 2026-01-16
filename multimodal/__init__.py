"""
Multi-Modal Fusion Module

Combines CREDO image embeddings (DINO) with CosmicWatch event embeddings (BERT)
into a unified representation space, as recommended by Zichun.
"""

from .fusion import MultiModalFusion, create_multimodal_model

__all__ = ['MultiModalFusion', 'create_multimodal_model']


