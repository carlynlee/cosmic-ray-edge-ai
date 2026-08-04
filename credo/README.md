# CREDO Image Processing Module

This module provides tools for processing CREDO cosmic ray images using DINO-v2/v3 vision transformers, based on Zichun's recommendations.

## Overview

Based on the RINO team's feedback, CREDO images should be processed using **DINO/DINO-v2/DINO-v3 vision transformers** directly, since they are already in image format. No need to adapt RINO's particle physics framework.

### Key Features

- **Pre-trained Models**: Uses META's DINO-v2/v3 models
- **Feature Extraction**: Extract image embeddings for downstream tasks
- **Fine-tuning**: Fine-tune for cosmic ray detection
- **Multi-modal Ready**: Designed to work with multi-modal fusion

## Installation

```bash
pip install torch transformers torchvision Pillow
```

## Quick Start

### 1. Load CREDO Images

```python
from credo import load_credo_images
from torch.utils.data import DataLoader

# Load from JSON file
dataset = load_credo_images(
    source='scripts/data/credo_images_export.json',
    image_key='frame_content',
    image_size=224,  # DINO standard size
)

# Create DataLoader
dataloader = DataLoader(dataset, batch_size=8, shuffle=True)

# Get a batch
batch = next(iter(dataloader))
images = batch['image']  # [batch, 3, 224, 224]
metadata = batch['metadata']
```

### 2. Extract Features with Pre-trained DINO

```python
from credo import DINOImageEncoder

# Load pre-trained DINO-v2
encoder = DINOImageEncoder.from_pretrained(
    model_name='facebook/dinov2-base',
    freeze_backbone=True,  # Use pre-trained weights only
)
encoder.eval()

# Extract features
with torch.no_grad():
    features = encoder.extract_features(images)  # [batch, 768]
```

### 3. Fine-tune for Classification

```python
# Create model with classification head
encoder = DINOImageEncoder.from_pretrained(
    model_name='facebook/dinov2-base',
    freeze_backbone=False,  # Allow fine-tuning
)

model = encoder.fine_tune_for_classification(
    num_classes=2,  # Binary: cosmic ray / not
    freeze_backbone=False,
)

# Training loop
criterion = torch.nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

for epoch in range(num_epochs):
    for batch in dataloader:
        images = batch['image']
        labels = batch['labels']
        
        # Forward pass
        image_features = encoder(images, return_pooled=True)
        logits = model['classifier'](image_features)
        loss = criterion(logits, labels)
        
        # Backward pass
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()
```

### 4. Load from Elasticsearch

```python
from elasticsearch import Elasticsearch
from credo import load_credo_images

# Connect to Elasticsearch
es = Elasticsearch(
    ['https://localhost:9200'],
    basic_auth=('elastic', 'your-password'),
    verify_certs=False,
)

# Load images
dataset = load_credo_images(
    source='credo-detections',
    es_client=es,
    query={'term': {'source': 'credo-science'}},
    size=100,
    image_key='frame_content',
)
```

## Module Structure

```
credo/
├── __init__.py              # Module exports
├── dataloader/              # Data loading
│   ├── dataset.py           # CREDOImageDataset
│   └── loader.py            # Load from JSON or Elasticsearch
├── models/                  # Models
│   └── dino.py              # DINOImageEncoder
└── examples/                # Example scripts
    └── example_dino_usage.py
```

## Data Format

### Input Format

Images can be provided as:
- **Base64-encoded strings** (from Elasticsearch)
- **File paths**
- **PIL Image objects**
- **NumPy arrays**

### Output Format

```python
{
    'image': torch.Tensor,      # [batch, 3, 224, 224] - normalized
    'metadata': Dict,            # Original data (device_id, timestamp, etc.)
}
```

## Available Models

- `facebook/dinov2-base` (default) - 768-dim embeddings
- `facebook/dinov2-large` - 1024-dim embeddings
- `facebook/dinov2-giant` - 1536-dim embeddings
- DINO-v3 models (when available)

## Integration with Multi-Modal

This module is designed to work with the `multimodal` module for combining CREDO images with CosmicWatch events:

```python
from credo import DINOImageEncoder
from multimodal import create_multimodal_model

# Image encoder
image_encoder = DINOImageEncoder.from_pretrained('facebook/dinov2-base')

# Use in multi-modal model (see multimodal module)
```

## Examples

See `examples/example_dino_usage.py` for complete examples:
1. Loading images from JSON
2. Extracting features with pre-trained DINO
3. Fine-tuning for classification
4. Loading from Elasticsearch

## References

- **Zichun's Recommendations**: See `docs/ZICHUN_RECOMMENDATIONS.md`
- **DINO-v2**: https://dinov2.metademolab.com/
- **DINO-v3**: https://ai.meta.com/dinov3/
- **HuggingFace Transformers**: https://huggingface.co/docs/transformers/


