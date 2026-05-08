# ML Design

---

## 1. Baseline Model (Built for SC25)

**Task:** Binary classification — predict coincidence flag (0/1) from detector measurements.

**Architecture:** MLP — Input(5) → Linear(64) → ReLU → Dropout(0.3) → Linear(32) → ReLU → Dropout(0.3) → Linear(1) → Sigmoid

**Features:** `adc_value`, `sipm_mv`, `temperature_c`, `pressure_pa`, `deadtime_s`  
**Normalization:** StandardScaler (fitted on training set)  
**Class weights:** `{0: 1.0, 1: 7.0}` (inverse frequency for 1:7 imbalance)  
**Optimizer:** Adam lr=0.001, BCE loss, early stopping patience=10

**Results:** ROC-AUC 0.82 | Accuracy 69.78% at threshold 0.5 | Optimal threshold 0.72 → predicted rate 13.35% (matches observed 12.29%)

**Saved:** `scripts/models/binary_baseline_model.pth`, `binary_baseline_scaler.pkl`

---

## 2. Why Coincidence Prediction Has Limited Scientific Value

The hardware already measures coincidence directly — the `coincident` field is a hardware output, not a derived quantity. Predicting it with ML is redundant scientifically.

**Why we did it anyway for SC25:** demonstrates the ML pipeline, enables federated learning with a concrete labeled task, and validates that ADC correlates with coincidence (ADC 394 vs 249 average).

**Better ML targets for future work:**

| Use case | Why it's better | Approach |
|---|---|---|
| Energy estimation | ADC is a proxy, not a direct energy measure — ML can combine all features for a better estimate | Regression: predict energy (MeV) from ADC, SiPM, env |
| Anomaly detection | Finds rare high-energy events, detector malfunction, data quality issues | Autoencoder or isolation forest on ADC/SiPM combinations |
| Multi-class energy bins | More granular than binary: Low (<200), Medium (200–500), High (>500 or coincidence) | 3-class MLP |

**Framing for SC25:** "The hardware measures coincidence directly, but ML validates the underlying physics relationship and demonstrates the pipeline for future energy estimation applications."

---

## 3. Transformer Roadmap (Zichun's Recommendations)

Based on correspondence with Zichun (RINO paper author, arxiv 2509.07486):

### CREDO images → DINO-v2/v3
CREDO images are already in standard image format (20×20px PNG, base64-encoded in Elasticsearch). Use Meta's pre-trained DINO-v2/v3 vision transformers directly — no need to adapt the RINO particle physics framework.

- **Model:** `facebook/dinov2-base` (768-dim output)
- **Input processing:** base64 decode → RGB → resize to 224×224 → normalize
- **Strategy:** use pre-trained weights, fine-tune only if needed

### CosmicWatch events → BERT/GPT
Events are irregularly sampled time-series, not momentum-space vectors. Treat each event as a token.

- **Each event:** 10-dim feature vector (ADC, SiPM, temp, pressure, accel x/y/z, gyro x/y/z)
- **Sequence length:** 128 events per sequence (sliding window, stride 64)
- **Pre-training:** masked event modeling (15% of events masked, predict from context — analogous to BERT MLM)
- **Output:** `{'sequence': [batch, 128, 10], 'mask': [batch, 128], 'timestamps': [batch, 128]}`

**Key difference from RINO:** RINO uses Lorentz-invariant transformations for momentum-space data. Our data is in the time domain — we borrow the transformer architecture but use time-shift augmentations and event masking instead.

### Multi-modal fusion (longer term)
Combine DINO image embeddings + BERT event embeddings into a unified 512-dim space. Cross-modal agreement scoring (cosine similarity) gives high-confidence detections by requiring both modalities to agree.

```
DINO(image) → 768-dim
BERT(events) → 768-dim
Fusion layer → 512-dim → classifier
```

---

## 4. Implementation Status

| Component | Module | Status | Notes |
|---|---|---|---|
| DINO image encoder | `credo/` | ✅ implemented | Lazy import to avoid protobuf conflict with Flower |
| BERT event encoder | `cosmicwatch/` | ✅ implemented | 627 sequences from 40K events, RINO-compatible format |
| Multi-modal fusion | `multimodal/` | ✅ architecture ready | Concat/add/attention fusion methods, not yet trained |
| BERT pre-training | — | ⬜ not started | Masked event modeling pipeline needed |
| DINO fine-tuning | — | ⬜ not started | May not be needed with pre-trained weights |
| Paired dataset | — | ⬜ not started | Need to match CREDO images + CosmicWatch events by timestamp |

**Dependency note:** Flower requires `protobuf<5.0.0`, TensorFlow requires `≥5.28.0`. Solution: lazy imports in `credo/models/dino.py`; data loading works independently of the model.

---

## 5. Next Steps

1. Pre-train BERT model on 28,144 CosmicWatch training events (masked event modeling)
2. Extract DINO features from 369,804 CREDO images — analyze feature space
3. Create paired dataset: match CREDO detections to CosmicWatch events by timestamp
4. Fine-tune both models for binary classification; compare single-modal vs multi-modal
5. Implement energy estimation regression (higher scientific value than coincidence prediction)
