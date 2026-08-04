# CosmicWatch Module for RINO Integration

This module provides tools for processing CosmicWatch Desktop Muon Detector data and preparing it for self-supervised learning with transformer models, following the RINO team's recommendations.

## Overview

Based on the RINO team's feedback, CosmicWatch event data should be processed as **sequential event data** using **BERT/GPT-style transformer models** rather than adapting RINO's particle physics framework directly.

### Key Concepts

- **Events as Tokens**: Each CosmicWatch event becomes a "token" in a sequence
- **Event Features**: ADC values, timestamps, temperature, pressure, accelerometer, gyroscope
- **Sequential Context**: Events are ordered by timestamp, creating temporal sequences
- **Transformer Models**: Use BERT (bidirectional) or GPT (autoregressive) for learning contextual embeddings

## Installation

```bash
# Install dependencies
pip install torch numpy pandas elasticsearch
```

## Quick Start

### 1. Export CosmicWatch Data

```bash
cd scripts
export ES_HOST="https://localhost:9200"
export ES_USER="elastic"
export ES_PASS="your-password"
export ES_INDEX="credo-detections"

python3 export_cosmicwatch_data.py
```

This creates `data/cosmicwatch_data_export.json`.

### 2. Load Sequences

```python
from cosmicwatch import load_cosmicwatch_sequences
from torch.utils.data import DataLoader

# Load sequences with sliding window
dataset = load_cosmicwatch_sequences(
    data_path="scripts/data/cosmicwatch_data_export.json",
    max_seq_length=128,
    window_size=128,  # Events per sequence
    stride=64,  # Overlapping windows
    normalize=True,
)

# Create DataLoader
dataloader = DataLoader(dataset, batch_size=32, shuffle=True)

# Get a batch
batch = next(iter(dataloader))
sequences = batch['sequence']  # [batch, seq_len, features]
masks = batch['mask']  # [batch, seq_len]
```

### 3. Use with BERT/GPT Models

```python
from transformers import AutoModel, AutoConfig
import torch.nn as nn

# Create event embedding layer
class EventEmbedding(nn.Module):
    def __init__(self, feature_dim=10, hidden_dim=768):
        super().__init__()
        self.linear = nn.Linear(feature_dim, hidden_dim)
    
    def forward(self, events):
        return self.linear(events)

# Load BERT model
config = AutoConfig.from_pretrained("bert-base-uncased")
model = AutoModel.from_pretrained("bert-base-uncased")

# Replace token embeddings
model.embeddings.word_embeddings = EventEmbedding(
    feature_dim=10,
    hidden_dim=config.hidden_size
)

# Training loop
for batch in dataloader:
    sequences = batch['sequence']
    # Apply masking and train...
```

## Module Structure

```
cosmicwatch/
├── __init__.py              # Module exports
├── dataloader/              # Data loading
│   ├── dataset.py           # CosmicWatchSequenceDataset
│   └── loader.py            # Load from JSON or Elasticsearch
├── preprocess/              # Preprocessing
│   └── sequences.py         # Event sequence creation
├── utils/                   # Utilities
│   └── conversion.py        # Format conversion
└── examples/                # Example scripts
    └── example_rino_integration.py
```

## Data Format

### Input Format (JSON)

```json
[
  {
    "adc_value": 245,
    "sipm_mv": 1250.5,
    "coincident": true,
    "temperature_c": 22.5,
    "pressure_pa": 101325,
    "accel_x_g": 0.1,
    "accel_y_g": -0.05,
    "accel_z_g": 0.98,
    "gyro_x_degs": 0.0,
    "gyro_y_degs": 0.0,
    "gyro_z_degs": 0.0,
    "timestamp_ms": 1234567890000
  },
  ...
]
```

### Output Format (PyTorch)

```python
{
    'sequence': torch.Tensor,  # [seq_len, num_features]
    'mask': torch.BoolTensor,  # [seq_len] - valid events
    'timestamps': torch.Tensor,  # [seq_len] - relative timestamps
}
```

## Features

### Event Features

Default features included:
- `adc_value`: ADC reading (energy proxy)
- `sipm_mv`: SiPM voltage
- `temperature_c`: Temperature in Celsius
- `pressure_pa`: Pressure in Pascals
- `accel_x_g`, `accel_y_g`, `accel_z_g`: Accelerometer readings
- `gyro_x_degs`, `gyro_y_degs`, `gyro_z_degs`: Gyroscope readings

### Sequence Creation

- **Sliding Window**: Create overlapping sequences from events
- **Normalization**: Automatic feature normalization (mean/std)
- **Padding**: Automatic padding to max sequence length
- **Masking**: Boolean masks for valid events

## Integration with RINO

While RINO is designed for particle physics, the CosmicWatch module follows similar principles:

1. **Sequence Format**: Events formatted as sequences (like RINO's particle sequences)
2. **Masking**: Boolean masks for valid events (like RINO's particle masks)
3. **Normalization**: Feature normalization (like RINO's feature preprocessing)
4. **Transformer Architecture**: Uses transformer models (like RINO's ParticleTransformer)

### Key Differences

| Aspect | RINO | CosmicWatch |
|--------|------|-------------|
| **Data** | Particles in momentum space | Events in time domain |
| **Model** | ParticleTransformer | BERT/GPT |
| **Augmentations** | Lorentz, rotation | Time shifts, masking |
| **Invariance** | Lorentz, rotational | Temporal |

## Examples

See `examples/example_rino_integration.py` for complete examples:

1. Loading sequences from JSON
2. Creating DataLoaders
3. BERT-style pre-training setup
4. Exporting for training

## API Reference

### `load_cosmicwatch_sequences()`

Load CosmicWatch data and create sequence dataset.

**Parameters:**
- `data_path`: Path to JSON file
- `max_seq_length`: Maximum sequence length
- `window_size`: Events per sequence (None = all events)
- `stride`: Sliding window stride
- `normalize`: Whether to normalize features

**Returns:** `CosmicWatchSequenceDataset`

### `CosmicWatchSequenceDataset`

PyTorch Dataset for event sequences.

**Methods:**
- `__getitem__(idx)`: Get sequence at index
- `get_stats()`: Get normalization statistics
- `save_stats(path)`: Save statistics to file
- `load_stats(path)`: Load statistics from file

## Next Steps

1. **Pre-training**: Use BERT/GPT for masked event modeling
2. **Fine-tuning**: Fine-tune for downstream tasks (classification, anomaly detection)
3. **Multi-modal**: Combine with CREDO images (DINO-v2/v3) for unified embeddings

## References

- RINO Team Recommendations: See `CREDO_ADAPTATION_ANALYSIS.md` in RINO repository
- BERT Paper: "BERT: Pre-training of Deep Bidirectional Transformers"
- HuggingFace Transformers: https://huggingface.co/docs/transformers/
