"""
Example: Multi-Modal Fusion

Combines CREDO images (DINO) with CosmicWatch events (BERT)
as recommended by Zichun for high-confidence event identification.
"""

import torch
from torch.utils.data import DataLoader
from credo import DINOImageEncoder, load_credo_images
from cosmicwatch import load_cosmicwatch_sequences
from multimodal import create_multimodal_model
from transformers import AutoModel, AutoConfig


def example_1_create_multimodal_model():
    """Create multi-modal fusion model."""
    print("Example 1: Creating multi-modal model")
    
    # Image encoder (DINO)
    image_encoder = DINOImageEncoder.from_pretrained(
        model_name='facebook/dinov2-base',
        freeze_backbone=True,
    )
    image_dim = 768  # DINO-v2-base dimension
    
    # Event encoder (BERT)
    event_config = AutoConfig.from_pretrained('bert-base-uncased')
    event_encoder = AutoModel.from_pretrained('bert-base-uncased')
    
    # Replace token embeddings with event embeddings
    from torch import nn
    class EventEmbedding(nn.Module):
        def __init__(self, feature_dim=10, hidden_dim=768):
            super().__init__()
            self.linear = nn.Linear(feature_dim, hidden_dim)
        
        def forward(self, events):
            return self.linear(events)
    
    event_encoder.embeddings.word_embeddings = EventEmbedding(
        feature_dim=10,  # CosmicWatch features
        hidden_dim=event_config.hidden_size,
    )
    event_dim = event_config.hidden_size  # 768
    
    # Create multi-modal model
    model = create_multimodal_model(
        image_encoder=image_encoder,
        event_encoder=event_encoder,
        image_dim=image_dim,
        event_dim=event_dim,
        fusion_dim=512,
        num_classes=2,  # Binary: high-confidence cosmic ray / not
        fusion_method='concat',
    )
    
    print("Model structure:")
    print(model)
    
    return model


def example_2_forward_pass():
    """Run forward pass with multi-modal data."""
    print("\nExample 2: Forward pass")
    
    # Create model
    model = example_1_create_multimodal_model()
    model.eval()
    
    # Load images
    image_dataset = load_credo_images(
        source='scripts/data/credo_images_export.json',
        image_size=224,
    )
    image_loader = DataLoader(image_dataset, batch_size=4)
    
    # Load events
    event_dataset = load_cosmicwatch_sequences(
        data_path='scripts/data/cosmicwatch_data_export.json',
        max_seq_length=128,
        window_size=128,
        stride=64,
    )
    event_loader = DataLoader(event_dataset, batch_size=4)
    
    # Get batches (assuming they're paired)
    image_batch = next(iter(image_loader))
    event_batch = next(iter(event_loader))
    
    images = image_batch['image']  # [batch, 3, 224, 224]
    events = event_batch['sequence']  # [batch, seq_len, features]
    event_mask = event_batch['mask']  # [batch, seq_len]
    
    # Forward pass
    with torch.no_grad():
        fused_features = model['fusion'](
            images=images,
            events=events,
            event_mask=event_mask,
        )  # [batch, fusion_dim]
        
        # Classification
        logits = model['classifier'](fused_features)  # [batch, num_classes]
        probs = torch.softmax(logits, dim=1)
    
    print(f"Fused features shape: {fused_features.shape}")
    print(f"Logits shape: {logits.shape}")
    print(f"Probabilities: {probs}")
    
    return fused_features, logits


def example_3_high_confidence_detection():
    """
    High-confidence event detection using multi-modal agreement.
    
    As Zichun suggested: "identifying high-confidence events by requiring
    agreement across both the visual features and the sequential sensor data."
    """
    print("\nExample 3: High-confidence detection")
    
    model = example_1_create_multimodal_model()
    model.eval()
    
    # Load paired data (images + events)
    # In practice, you'd have a dataset that pairs CREDO images with
    # corresponding CosmicWatch events
    
    # For demonstration, create dummy paired data
    batch_size = 8
    images = torch.randn(batch_size, 3, 224, 224)
    events = torch.randn(batch_size, 128, 10)  # [batch, seq_len, features]
    event_mask = torch.ones(batch_size, 128, dtype=torch.bool)
    
    with torch.no_grad():
        # Get individual embeddings
        fused, individual = model['fusion'](
            images=images,
            events=events,
            event_mask=event_mask,
            return_individual=True,
        )
        
        image_emb = individual['image']  # [batch, 768]
        event_emb = individual['event']  # [batch, 768]
        
        # Compute agreement (cosine similarity)
        image_emb_norm = torch.nn.functional.normalize(image_emb, p=2, dim=1)
        event_emb_norm = torch.nn.functional.normalize(event_emb, p=2, dim=1)
        agreement = (image_emb_norm * event_emb_norm).sum(dim=1)  # [batch]
        
        # Classification
        logits = model['classifier'](fused)
        probs = torch.softmax(logits, dim=1)
        
        # High-confidence: high agreement + high classification probability
        confidence = agreement * probs[:, 1]  # Assuming class 1 is "cosmic ray"
        
        # Threshold for high-confidence
        threshold = 0.7
        high_confidence = confidence > threshold
    
    print(f"Agreement scores: {agreement}")
    print(f"Confidence scores: {confidence}")
    print(f"High-confidence events: {high_confidence.sum().item()}/{batch_size}")
    
    return high_confidence, confidence


if __name__ == '__main__':
    print("=" * 60)
    print("Multi-Modal Fusion Examples")
    print("Based on Zichun's Recommendations")
    print("=" * 60)
    
    # Run examples
    # example_1_create_multimodal_model()
    # example_2_forward_pass()
    # example_3_high_confidence_detection()
    
    print("\nNote: Uncomment examples to run them")
    print("Make sure you have both CREDO images and CosmicWatch events!")


