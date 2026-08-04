# Multi-Modal Fusion Module

This module combines CREDO image embeddings (from DINO) with CosmicWatch event embeddings (from BERT) into a unified representation space, as recommended by Zichun.

## Overview

As Zichun suggested: *"This could be powerful for tasks like identifying high-confidence events by requiring agreement across both the visual features and the sequential sensor data."*

### Architecture

1. **Image Encoder**: DINO-v2/v3 for CREDO images
2. **Event Encoder**: BERT/GPT for CosmicWatch sequences
3. **Fusion Layer**: Combines embeddings into unified space
4. **Optional Classifier**: For downstream tasks

## Installation

```bash
pip install torch transformers
```

## Quick Start

### 1. Create Multi-Modal Model

```python
from credo import DINOImageEncoder
from cosmicwatch import load_cosmicwatch_sequences
from transformers import AutoModel, AutoConfig
from multimodal import create_multimodal_model
import torch.nn as nn

# Image encoder (DINO)
image_encoder = DINOImageEncoder.from_pretrained('facebook/dinov2-base')
image_dim = 768

# Event encoder (BERT)
event_config = AutoConfig.from_pretrained('bert-base-uncased')
event_encoder = AutoModel.from_pretrained('bert-base-uncased')

# Replace token embeddings with event embeddings
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
event_dim = 768

# Create multi-modal model
model = create_multimodal_model(
    image_encoder=image_encoder,
    event_encoder=event_encoder,
    image_dim=image_dim,
    event_dim=event_dim,
    fusion_dim=512,
    num_classes=2,  # Binary classification
    fusion_method='concat',
)
```

### 2. Forward Pass

```python
# Load data
images = torch.randn(8, 3, 224, 224)  # CREDO images
events = torch.randn(8, 128, 10)      # CosmicWatch events
event_mask = torch.ones(8, 128, dtype=torch.bool)

# Forward pass
fused_features = model['fusion'](
    images=images,
    events=events,
    event_mask=event_mask,
)  # [batch, fusion_dim]

# Classification
logits = model['classifier'](fused_features)  # [batch, num_classes]
probs = torch.softmax(logits, dim=1)
```

### 3. High-Confidence Detection

```python
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
agreement = (image_emb_norm * event_emb_norm).sum(dim=1)

# High-confidence: high agreement + high classification probability
logits = model['classifier'](fused)
probs = torch.softmax(logits, dim=1)
confidence = agreement * probs[:, 1]  # Assuming class 1 is "cosmic ray"

# Threshold for high-confidence
high_confidence = confidence > 0.7
```

## Fusion Methods

### 1. Concatenation (`concat`)
- Simple concatenation of image and event embeddings
- Most straightforward approach
- Good for initial experiments

### 2. Addition (`add`)
- Element-wise addition of embeddings
- Requires same dimension for both modalities
- Good when embeddings are in similar space

### 3. Attention (`attention`)
- Cross-attention mechanism
- Events attend to image features
- More sophisticated, learns relationships

## Module Structure

```
multimodal/
├── __init__.py              # Module exports
├── fusion.py                # MultiModalFusion class
└── examples/                # Example scripts
    └── example_multimodal.py
```

## Use Cases

1. **High-Confidence Event Identification**
   - Require agreement across both modalities
   - Reduce false positives

2. **Cross-Modal Validation**
   - Use image features to validate event sequences
   - Use events to validate image detections

3. **Unified Representation**
   - Single embedding space for both modalities
   - Enables downstream tasks on unified features

## Examples

See `examples/example_multimodal.py` for complete examples:
1. Creating multi-modal model
2. Forward pass with paired data
3. High-confidence detection using agreement

## References

- **Zichun's Recommendations**: See `docs/ZICHUN_RECOMMENDATIONS.md`
- **CREDO Module**: See `credo/README.md`
- **CosmicWatch Module**: See `cosmicwatch/README.md`


