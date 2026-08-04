# RINO Integration Guide

This guide explains how to integrate CREDO and CosmicWatch data processing with self-supervised learning frameworks, based on Zichun's (RINO author) recommendations.

## Overview

Based on Zichun's recommendations:
- **CREDO Images**: Use **DINO-v2/v3 vision transformers** directly (see `credo/` module)
- **CosmicWatch Events**: Use **BERT/GPT-style transformer models** for event sequences (see `cosmicwatch/` module)
- **Multi-Modal**: Combine both in unified embedding space (see `multimodal/` module)

**Note**: We do NOT adapt RINO's particle physics framework directly, but follow similar principles for data processing.

## Architecture Comparison

### RINO (Particle Physics)
- **Data**: Particle sequences in momentum space
- **Model**: ParticleTransformer
- **Augmentations**: Lorentz transformations, rotations, kT clustering
- **Format**: `(sequence, mask, jets)` where sequence is particles

### CosmicWatch (Event Sequences)
- **Data**: Event sequences in time domain
- **Model**: BERT/GPT (HuggingFace Transformers)
- **Augmentations**: Time shifts, event masking, noise injection
- **Format**: `(sequence, mask, timestamps)` where sequence is events

## Integration Workflow

### Step 1: Export CosmicWatch Data

```bash
cd scripts
export ES_HOST="https://localhost:9200"
export ES_USER="elastic"
export ES_PASS="your-password"
export ES_INDEX="credo-detections"

python3 export_cosmicwatch_data.py
```

This creates `data/cosmicwatch_data_export.json`.

### Step 2: Load Sequences

```python
from cosmicwatch import load_cosmicwatch_sequences
from torch.utils.data import DataLoader

# Load sequences (similar to RINO's dataloader)
dataset = load_cosmicwatch_sequences(
    data_path="scripts/data/cosmicwatch_data_export.json",
    max_seq_length=128,
    window_size=128,
    stride=64,
    normalize=True,
)

# Create DataLoader (same as RINO)
dataloader = DataLoader(
    dataset,
    batch_size=32,
    shuffle=True,
    num_workers=4,
)
```

### Step 3: Pre-training with BERT

```python
from transformers import AutoModel, AutoConfig, AutoTokenizer
import torch
import torch.nn as nn

# Create event embedding (replaces BERT's token embeddings)
class EventEmbedding(nn.Module):
    def __init__(self, feature_dim=10, hidden_dim=768):
        super().__init__()
        self.linear = nn.Linear(feature_dim, hidden_dim)
    
    def forward(self, events):
        # events: [batch, seq_len, feature_dim]
        return self.linear(events)

# Load BERT model
config = AutoConfig.from_pretrained("bert-base-uncased")
model = AutoModel.from_pretrained("bert-base-uncased")

# Replace token embeddings with event embeddings
model.embeddings.word_embeddings = EventEmbedding(
    feature_dim=10,  # Number of event features
    hidden_dim=config.hidden_size
)

# Training loop (similar to RINO's DINO training)
for batch in dataloader:
    sequences = batch['sequence']  # [batch, seq_len, features]
    masks = batch['mask']  # [batch, seq_len]
    
    # Apply masking (15% of events, like BERT's masked language modeling)
    masked_sequences, labels = apply_masking(sequences, masks, mask_prob=0.15)
    
    # Forward pass
    outputs = model(inputs_embeds=masked_sequences, attention_mask=masks)
    
    # Compute loss
    loss = compute_masked_loss(outputs.last_hidden_state, labels)
    
    # Backward pass
    loss.backward()
    optimizer.step()
```

## Data Format Compatibility

### RINO Format
```python
{
    'sequence': torch.Tensor,  # [batch, seq_len, features]
    'mask': torch.BoolTensor,  # [batch, seq_len]
    'jets': torch.Tensor,      # [batch, jet_features]
}
```

### CosmicWatch Format
```python
{
    'sequence': torch.Tensor,    # [batch, seq_len, features]
    'mask': torch.BoolTensor,    # [batch, seq_len]
    'timestamps': torch.Tensor,  # [batch, seq_len]
}
```

**Note**: Both use the same `sequence` and `mask` format, making it easy to adapt RINO-style training loops.

## Augmentation Strategies

### RINO Augmentations (Particle Physics)
- Lorentz transformations
- Rotations
- kT clustering
- Particle masking
- Feature smearing

### CosmicWatch Augmentations (Time Series)
- **Time shifts**: Shift events in time
- **Event masking**: Randomly mask events (like BERT)
- **Noise injection**: Add sensor noise
- **Time warping**: Stretch/compress time
- **Event dropout**: Randomly drop events

### Example Augmentation

```python
def apply_time_augmentation(sequences, masks):
    """Apply time-based augmentations."""
    augmented = []
    
    for seq, mask in zip(sequences, masks):
        # Random time shift
        shift = torch.randint(-10, 10, (1,)).item()
        seq_shifted = torch.roll(seq, shift, dims=0)
        
        # Random masking (15%)
        mask_prob = 0.15
        random_mask = torch.rand(seq.shape[0]) < mask_prob
        seq_shifted[random_mask] = 0.0  # Mask events
        
        augmented.append(seq_shifted)
    
    return torch.stack(augmented)
```

## Training Pipeline

### Pre-training (Self-Supervised)

Similar to RINO's DINO pre-training, but using BERT's masked event modeling:

```python
# Student and teacher models (like RINO)
student_model = create_bert_model()
teacher_model = create_bert_model()

# Copy student to teacher
teacher_model.load_state_dict(student_model.state_dict())

# Training loop
for epoch in range(num_epochs):
    for batch in dataloader:
        sequences = batch['sequence']
        masks = batch['mask']
        
        # Create multiple views (like RINO)
        view1 = apply_augmentation(sequences, masks)
        view2 = apply_augmentation(sequences, masks)
        
        # Student forward
        student_out1 = student_model(inputs_embeds=view1, attention_mask=masks)
        student_out2 = student_model(inputs_embeds=view2, attention_mask=masks)
        
        # Teacher forward (no gradients)
        with torch.no_grad():
            teacher_out = teacher_model(inputs_embeds=sequences, attention_mask=masks)
        
        # Contrastive loss (like DINO)
        loss = contrastive_loss(student_out1, student_out2, teacher_out)
        
        # Update
        loss.backward()
        optimizer.step()
        
        # EMA update teacher (like RINO)
        update_teacher_ema(student_model, teacher_model, momentum=0.996)
```

### Fine-tuning (Supervised)

```python
# Load pre-trained model
model = AutoModel.from_pretrained("path/to/pretrained")

# Add classification head
classifier = nn.Linear(model.config.hidden_size, num_classes)

# Fine-tuning loop
for batch in train_dataloader:
    sequences = batch['sequence']
    masks = batch['mask']
    labels = batch['labels']
    
    # Forward pass
    outputs = model(inputs_embeds=sequences, attention_mask=masks)
    pooled = outputs.pooler_output  # Or use CLS token
    
    # Classification
    logits = classifier(pooled)
    loss = nn.CrossEntropyLoss()(logits, labels)
    
    # Backward pass
    loss.backward()
    optimizer.step()
```

## Multi-Modal Integration

For combining CosmicWatch events with CREDO images (as suggested by RINO team):

```python
# Image encoder (DINO-v2)
from transformers import AutoImageProcessor, AutoModel
image_processor = AutoImageProcessor.from_pretrained("facebook/dinov2-base")
image_model = AutoModel.from_pretrained("facebook/dinov2-base")

# Event encoder (BERT)
event_model = AutoModel.from_pretrained("path/to/pretrained-bert")

# Fusion layer
fusion = nn.Linear(image_dim + event_dim, unified_dim)

# Forward pass
image_features = image_model(images).pooler_output
event_features = event_model(inputs_embeds=events, attention_mask=masks).pooler_output

# Fuse
unified_features = fusion(torch.cat([image_features, event_features], dim=1))
```

## Configuration Files

Create RINO-style config files for CosmicWatch:

```yaml
# configs/cosmicwatch/bert-pretrain.yaml
model:
  type: "bert-base-uncased"
  feature_dim: 10
  hidden_dim: 768

data:
  path: "scripts/data/cosmicwatch_data_export.json"
  max_seq_length: 128
  window_size: 128
  stride: 64
  normalize: true

training:
  batch_size: 32
  num_epochs: 100
  learning_rate: 1e-4
  mask_prob: 0.15
```

## CREDO Images with DINO

For CREDO images, use the `credo/` module:

```python
from credo import DINOImageEncoder, load_credo_images

# Load images
dataset = load_credo_images(
    source='scripts/data/credo_images_export.json',
    image_size=224,
)

# Extract features or fine-tune
encoder = DINOImageEncoder.from_pretrained('facebook/dinov2-base')
features = encoder.extract_features(images)
```

See `credo/README.md` for details.

## Multi-Modal Fusion

Combine CREDO images with CosmicWatch events:

```python
from multimodal import create_multimodal_model

model = create_multimodal_model(
    image_encoder=image_encoder,  # DINO
    event_encoder=event_encoder,   # BERT
    image_dim=768,
    event_dim=768,
    fusion_dim=512,
    num_classes=2,
)
```

See `multimodal/README.md` for details.

## Next Steps

1. ✅ **CREDO Images**: DINO-v2/v3 implementation (see `credo/` module)
2. ✅ **CosmicWatch Events**: BERT-style implementation (see `cosmicwatch/` module)
3. ✅ **Multi-modal Fusion**: Fusion module (see `multimodal/` module)
4. **Pre-training**: Implement masked event modeling for CosmicWatch
5. **Fine-tuning**: Fine-tune both models for downstream tasks
6. **Evaluation**: Compare with baseline models

## References

- **Zichun's Recommendations**: See `docs/ZICHUN_RECOMMENDATIONS.md`
- **RINO Repository**: `/Users/carlyn_oligo/git/credo-api-tools/RINO`
- **RINO Paper**: `RINO/2509.07486v3 (1).pdf`
- **DINO-v2**: https://dinov2.metademolab.com/
- **DINO-v3**: https://ai.meta.com/dinov3/
- **HuggingFace Transformers**: https://huggingface.co/docs/transformers/
- **BERT Paper**: "BERT: Pre-training of Deep Bidirectional Transformers"
