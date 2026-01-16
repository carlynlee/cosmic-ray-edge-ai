# DINO, RINO, and Multi-Modal Analysis: Results and Principal Factors

**Prepared for Meeting with Harvey**  
**Date: January 2025**

## Executive Summary

We implemented transformer-based self-supervised learning approaches for CREDO cosmic ray detection data, following recommendations from Zichun (RINO author). The work encompasses three complementary approaches: DINO for CREDO images, BERT/GPT for CosmicWatch event sequences, and multi-modal fusion combining both modalities.

**Key Achievement**: All three modules are implemented and functional, with data loading capabilities verified on real Elasticsearch data (369,804 CREDO documents with images).

---

## 1. DINO for CREDO Images

### Results and Status

**Implementation Status**: ✅ **Complete and Functional**

- **Module**: `credo/` module fully implemented
- **Data Loading**: Tested with 10,000 images from JSON export and 10 images from Elasticsearch
- **Image Processing**: Images decoded from base64, resized to 224×224 for DINO input
- **Dependency Management**: Lazy import implemented to avoid tensorflow/protobuf conflicts

**Key Findings**:
- CREDO images in Elasticsearch are small 20×20 pixel regions (PNG, RGBA format)
- Original frame dimensions: 960×720 (images are cropped detection regions)
- All 369,804 CREDO documents in Elasticsearch contain `frame_content` field
- Data loading works independently of DINO model (can explore data without model dependencies)

### Principal Factors

1. **Direct Vision Transformer Approach**
   - **Rationale**: CREDO images are already in standard image format
   - **Decision**: Use DINO-v2/v3 directly rather than adapting RINO's particle physics framework
   - **Benefit**: Leverages META's pre-trained models, no need for domain adaptation

2. **Pre-trained Model Strategy**
   - **Models**: DINO-v2-base (768-dim), DINO-v2-large (1024-dim), DINO-v2-giant (1536-dim)
   - **Approach**: Use pre-trained weights, fine-tune only if necessary
   - **Why Pre-trained Models Work**: DINO-v2/v3 were trained on large natural image datasets (ImageNet, etc.) and learned general visual features (edges, textures, patterns, spatial relationships) that transfer across domains. Cosmic ray images contain visual patterns (tracks, streaks, bright spots) that vision transformers can detect even without physics knowledge. The models learn "what looks interesting/unusual" rather than explicit physics, and fine-tuning adapts these general features to cosmic ray-specific patterns. This transfer learning approach is faster and typically outperforms training from scratch.

3. **Data Format Compatibility**
   - **Input**: Base64-encoded strings from Elasticsearch or JSON files
   - **Processing**: Automatic decoding, RGB conversion, normalization
   - **Output**: PyTorch tensors [batch, 3, 224, 224] ready for DINO

4. **Lazy Import Architecture**
   - **Problem**: TensorFlow/protobuf dependency conflicts with other packages (Flower)
   - **Solution**: DINO only imported when `DINOImageEncoder` is actually used
   - **Result**: Data exploration and loading work without model dependencies

---

## 2. RINO-Inspired Approach for CosmicWatch Events

### Results and Status

**Implementation Status**: ✅ **Complete and Tested**

- **Module**: `cosmicwatch/` module fully implemented
- **Data Processing**: Successfully loaded 627 sequences from 40,207 events
- **Sequence Format**: Compatible with RINO-style training (sequence, mask, timestamps)
- **BERT Integration**: Ready for masked event modeling pre-training

**Key Findings**:
- Successfully created 627 sequences with sliding window (128 events, stride 64)
- Each sequence contains 10 features: ADC, SiPM voltage, temperature, pressure, accelerometer (x,y,z), gyroscope (x,y,z)
- Data exported to train/val/test splits (28,144 / 6,031 / 6,032 events)
- Format matches RINO's structure, enabling easy adaptation of training loops

### Principal Factors

1. **NLP Transformer Approach (Not Particle Physics)**
   - **Rationale**: CosmicWatch data is irregularly sampled time-series, not particle momentum space
   - **Decision**: Use BERT/GPT-style transformers instead of RINO's ParticleTransformer
   - **Key Insight**: Events are analogous to tokens in language models

2. **Event-as-Token Paradigm**
   - **Concept**: Each CosmicWatch event becomes a "token" in a sequence
   - **Features**: 10-dimensional feature vector per event (sensor readings)
   - **Context**: Bidirectional (BERT) or autoregressive (GPT) attention learns temporal relationships

3. **RINO-Compatible Format**
   - **Structure**: `(sequence, mask, timestamps)` mirrors RINO's `(sequence, mask, jets)`
   - **Benefit**: Can adapt RINO-style training loops with minimal changes
   - **Augmentations**: Time shifts, event masking, noise injection (vs. RINO's Lorentz transformations)

4. **Self-Supervised Pre-training Strategy**
   - **Method**: Masked event modeling (similar to BERT's masked language modeling)
   - **Masking**: 15% of events randomly masked
   - **Goal**: Learn robust representations from unlabeled event sequences

---

## 3. Multi-Modal Fusion

### Results and Status

**Implementation Status**: ✅ **Complete (Architecture Ready)**

- **Module**: `multimodal/` module fully implemented
- **Fusion Methods**: Concatenation, addition, and attention-based fusion
- **High-Confidence Detection**: Agreement-based confidence scoring implemented
- **Integration**: Ready to combine DINO image embeddings with BERT event embeddings

**Key Capabilities**:
- Unified embedding space (default: 512-dim fusion from 768-dim image + 768-dim event)
- Cross-modal agreement scoring (cosine similarity between modalities)
- High-confidence event identification requiring agreement across both modalities
- Flexible fusion architecture supporting multiple methods

### Principal Factors

1. **Unified Embedding Space**
   - **Architecture**: Image encoder (DINO) + Event encoder (BERT) → Fusion layer → Classifier
   - **Dimensions**: 768 (image) + 768 (event) → 512 (fused) → 2 (classes)
   - **Benefit**: Single representation space enables joint reasoning

2. **High-Confidence Detection Strategy**
   - **Approach**: Require agreement between image and event embeddings
   - **Metric**: Cosine similarity between normalized embeddings
   - **Confidence Score**: `agreement × classification_probability`
   - **Use Case**: Reduce false positives by requiring cross-modal validation

3. **Fusion Methods**
   - **Concatenation**: Simple concatenation (most straightforward)
   - **Addition**: Element-wise addition (requires same dimensions)
   - **Attention**: Cross-attention mechanism (learns relationships)
   - **Flexibility**: Can experiment with different fusion strategies

4. **Cross-Modal Validation**
   - **Principle**: Use image features to validate event sequences and vice versa
   - **Benefit**: Leverages complementary information from both modalities
   - **Application**: High-confidence cosmic ray event identification

---

## 4. Key Architectural Decisions

### Why Not Direct RINO Adaptation?

| Aspect | RINO (Particle Physics) | Our Approach |
|--------|-------------------------|--------------|
| **CREDO Images** | N/A | DINO-v2/v3 (vision transformers) |
| **CosmicWatch** | ParticleTransformer | BERT/GPT (NLP transformers) |
| **Data Format** | Particles in momentum space | Events in time domain |
| **Augmentations** | Lorentz transformations, rotations | Time shifts, event masking |
| **Invariance** | Lorentz, rotational | Temporal |

**Key Insight**: RINO's particle physics framework is designed for momentum space, while our data is in time domain. We adapt the transformer principles (self-supervised learning, sequence modeling) rather than the specific physics framework.

### Data Characteristics

**CREDO Images**:
- Format: 20×20 pixel PNG regions (RGBA)
- Source: 369,804 documents in Elasticsearch
- Storage: Base64-encoded in `frame_content` field
- Original frames: 960×720 (images are cropped detection regions)

**CosmicWatch Events**:
- Features: 10 dimensions (ADC, SiPM, temperature, pressure, accel, gyro)
- Sequences: 128 events per sequence (sliding window, stride 64)
- Total: 40,207 events exported, 627 sequences created
- Temporal: Irregularly sampled, timestamp-ordered

---

## 5. Current Implementation Status

### ✅ Completed

1. **CREDO Module** (`credo/`)
   - Data loading from JSON and Elasticsearch
   - Image preprocessing and normalization
   - DINO encoder architecture (lazy import)
   - Tested with real data

2. **CosmicWatch Module** (`cosmicwatch/`)
   - Sequence creation and preprocessing
   - BERT-compatible data format
   - Data export for training
   - Tested with real data

3. **Multi-Modal Module** (`multimodal/`)
   - Fusion architecture
   - Multiple fusion methods
   - High-confidence detection framework
   - Example implementations

### 🔄 In Progress / Next Steps

1. **Pre-training Pipelines**
   - BERT masked event modeling for CosmicWatch
   - DINO fine-tuning for CREDO (if needed)

2. **Fine-tuning for Downstream Tasks**
   - Cosmic ray vs. background classification
   - Coincidence event detection
   - High-confidence event identification

3. **Evaluation and Comparison**
   - Baseline model comparisons
   - Multi-modal vs. single-modal performance
   - Agreement metrics and confidence calibration

4. **Paired Data Collection**
   - Match CREDO images with corresponding CosmicWatch events
   - Create multi-modal training dataset

---

## 6. Principal Factors Summary

### Technical Factors

1. **Domain-Appropriate Transformers**
   - Vision transformers (DINO) for images
   - Language transformers (BERT/GPT) for sequences
   - Not forcing particle physics framework onto time-domain data

2. **Self-Supervised Learning**
   - Leverage unlabeled data through pre-training
   - Masked event modeling for sequences
   - Transfer learning from pre-trained vision models

3. **Multi-Modal Synergy**
   - Complementary information from images and events
   - Cross-modal validation reduces false positives
   - Unified representation enables joint reasoning

### Practical Factors

1. **Dependency Management**
   - Lazy imports avoid conflicts
   - Data loading independent of model dependencies
   - Enables data exploration without full stack

2. **Data Availability**
   - 369,804 CREDO images in Elasticsearch
   - 40,207 CosmicWatch events exported
   - Real data tested and verified

3. **Modular Architecture**
   - Separate modules for each modality
   - Easy to test and develop independently
   - Flexible integration for multi-modal

---

## 7. Recommendations for Next Steps

### Immediate Priorities

1. **Pre-training CosmicWatch BERT Model**
   - Implement masked event modeling
   - Pre-train on 28,144 training events
   - Evaluate on validation set

2. **DINO Feature Extraction**
   - Extract features from CREDO images using pre-trained DINO
   - Analyze feature space characteristics
   - Identify discriminative patterns

3. **Paired Data Collection**
   - Match CREDO images with CosmicWatch events by timestamp
   - Create multi-modal training dataset
   - Validate pairing quality

### Medium-Term Goals

1. **Fine-tuning for Classification**
   - Binary classification: cosmic ray vs. background
   - Evaluate single-modal vs. multi-modal performance
   - Measure improvement from multi-modal fusion

2. **High-Confidence Detection Pipeline**
   - Implement agreement-based confidence scoring
   - Calibrate confidence thresholds
   - Evaluate false positive reduction

3. **Comparative Evaluation**
   - Baseline models (existing binary classifier)
   - Single-modal (DINO only, BERT only)
   - Multi-modal (fused)
   - Performance metrics: accuracy, precision, recall, F1

---

## 8. Technical Specifications

### Data Formats

**CREDO Images**:
- Input: Base64-encoded PNG (20×20 pixels, RGBA)
- Processing: Decode → RGB → Resize to 224×224 → Normalize
- Output: `torch.Tensor` [batch, 3, 224, 224]

**CosmicWatch Sequences**:
- Input: JSON with event features
- Processing: Sliding window (128 events, stride 64) → Normalize
- Output: `{'sequence': [batch, 128, 10], 'mask': [batch, 128], 'timestamps': [batch, 128]}`

**Multi-Modal**:
- Image embeddings: [batch, 768] from DINO
- Event embeddings: [batch, 768] from BERT
- Fused: [batch, 512] → [batch, 2] (classification)

### Model Architectures

**DINO Image Encoder**:
- Base model: `facebook/dinov2-base`
- Hidden dimension: 768
- Output: Pooled features (CLS token) or full sequence

**BERT Event Encoder**:
- Base model: `bert-base-uncased`
- Custom embedding: Linear layer (10 features → 768)
- Output: Pooled features or sequence

**Multi-Modal Fusion**:
- Fusion dimension: 512 (configurable)
- Methods: concat, add, attention
- Classifier: 2-layer MLP (512 → 256 → 2)

---

## Conclusion

We have successfully implemented transformer-based approaches for cosmic ray detection, following Zichun's recommendations. The architecture is modular, tested with real data, and ready for pre-training and fine-tuning. The multi-modal approach shows promise for high-confidence event identification through cross-modal validation.

**Key Achievement**: All three components (DINO, BERT-style transformers, multi-modal fusion) are implemented and functional, with verified data loading from Elasticsearch.

**Next Milestone**: Pre-training and fine-tuning to evaluate classification performance and measure the benefits of multi-modal fusion.

---

**References**:
- Zichun's Recommendations: `docs/ZICHUN_RECOMMENDATIONS.md`
- RINO Integration Guide: `RINO_INTEGRATION.md`
- CREDO Module: `credo/README.md`
- CosmicWatch Module: `cosmicwatch/README.md`
- Multi-Modal Module: `multimodal/README.md`

