# Baseline Model Design for Day 3-4

## Overview

This document outlines the baseline machine learning model for cosmic ray event classification, based on CosmicWatch detector data and physics principles.

---

## Problem Statement

**Task:** Classify cosmic ray events into energy levels based on detector measurements.

**Approach:** Binary classification - predict whether an event is a **coincidence event** (muon passing through both detectors) or **non-coincidence event** (single detector hit).

**Rationale:** 
- **Coincidence events:** When both detectors detect the same particle (Flag=1). Based on data analysis, these events have higher average ADC values (394.47 vs 249.42), indicating they represent muons with sufficient energy to trigger both detectors simultaneously.
- **Non-coincidence events:** Single detector hits (Flag=0), representing lower-energy muons or background events.
- **Physics basis:** The CosmicWatch detector uses "coincidence mode with a second detector for background suppression" (from README.md). Coincidence events occur when a muon passes through both stacked detectors, which requires higher energy.
- **Data validation:** Observed coincidence rate (12.3%) aligns with typical muon flux expectations for stacked detector geometry.

---

## Data Characteristics

### Dataset Statistics
- **Total events:** 40,207
- **Coincidence events:** 4,947 (12.3%)
- **Non-coincidence events:** 35,260 (87.7%)
- **Class imbalance:** Moderate (1:7 ratio)

### Feature Statistics
- **ADC Value:** 67-4053 (mean: 267.26, std: 208.98)
  - Coincidence: mean=394.47, median=338.00
  - Non-coincidence: mean=249.42, median=181.00
- **SiPM Voltage:** 3.4-1000 mV (mean: 13.84 mV, std: 14.46 mV)
- **Temperature:** 23.7-28.7°C
- **Pressure:** 98,417-101,907 Pa
- **Deadtime:** Variable (detector recovery time)
- **Accelerometer:** X, Y, Z (g)
- **Gyroscope:** X, Y, Z (deg/sec)

### Available Features
1. **Primary Features (Energy-related):**
   - `adc_value` - Direct energy proxy (0-4095)
   - `sipm_mv` - SiPM voltage (correlated with energy)
   - `coincidence_flag` - Ground truth label (0 or 1)

2. **Secondary Features (Environmental):**
   - `temperature_c` - Detector temperature
   - `pressure_pa` - Atmospheric pressure
   - `deadtime_s` - Detector recovery time

3. **Motion Features (Optional):**
   - `accel_x_g`, `accel_y_g`, `accel_z_g` - Accelerometer
   - `gyro_x_degs`, `gyro_y_degs`, `gyro_z_degs` - Gyroscope

---

## Model Architecture

### Model Type: Multi-Layer Perceptron (MLP)

**Rationale:**
- Simple neural network suitable for tabular data
- Can capture non-linear relationships between features
- Fast training and inference
- Good baseline for federated learning
- Aligns with SC25 plan requirements

### Architecture Design

```
Input Layer (N features)
    ↓
Hidden Layer 1 (64 neurons, ReLU activation)
    ↓
Dropout (0.3)
    ↓
Hidden Layer 2 (32 neurons, ReLU activation)
    ↓
Dropout (0.3)
    ↓
Output Layer (1 neuron, Sigmoid activation)
```

**Hyperparameters:**
- **Input features:** 5-7 features (ADC, SiPM, temperature, pressure, deadtime)
- **Hidden layers:** 2 layers (64 → 32 neurons)
- **Activation:** ReLU for hidden layers, Sigmoid for output
- **Dropout:** 0.3 (regularization)
- **Optimizer:** Adam (learning rate: 0.001)
- **Loss function:** Binary cross-entropy
- **Batch size:** 32
- **Epochs:** 50-100 (with early stopping)

---

## Feature Engineering

### Primary Features (Must Include)
1. **`adc_value`** - Normalized to [0, 1] range
   - Formula: `(adc_value - 67) / (4053 - 67)`
   - Most important feature (direct energy proxy)

2. **`sipm_mv`** - Normalized SiPM voltage
   - Formula: `(sipm_mv - 3.4) / (1000 - 3.4)`
   - Correlated with energy deposition

3. **`temperature_c`** - Normalized temperature
   - Formula: `(temperature_c - 23.7) / (28.7 - 23.7)`
   - May affect detector response

4. **`pressure_pa`** - Normalized pressure
   - Formula: `(pressure_pa - 98417) / (101907 - 98417)`
   - Affects muon flux (atmospheric depth)

5. **`deadtime_s`** - Normalized deadtime
   - May indicate detector saturation

### Optional Features (If Available)
6. **`accel_z_g`** - Vertical acceleration (normalized)
   - May indicate detector movement

7. **`gyro_z_degs`** - Vertical rotation (normalized)
   - May indicate detector orientation changes

### Feature Selection Strategy
- **Start with 5 features:** ADC, SiPM, temperature, pressure, deadtime
- **Add motion features** if they improve validation accuracy
- **Remove features** that don't contribute (feature importance analysis)

---

## Training Strategy

### Data Partitioning

**Node 1 (Coincidence Events):**
- Training: 3,958 events (80%)
- Validation: 494 events (10%)
- Test: 495 events (10%)

**Node 2 (Non-Coincidence Events):**
- Training: 28,208 events (80%)
- Validation: 3,526 events (10%)
- Test: 3,526 events (10%)

**Node 3 (CREDO.science Legacy Data):**
- If available: Use similar partitioning
- Otherwise: Use as additional validation set

### Training Approach

1. **Train separate models on each partition:**
   - Model 1: Trained on Node 1 (coincidence events)
   - Model 2: Trained on Node 2 (non-coincidence events)
   - Model 3: Trained on Node 3 (CREDO data, if available)

2. **Handle class imbalance:**
   - Use class weights: `{0: 1.0, 1: 7.0}` (inverse frequency)
   - Or use SMOTE/undersampling (if needed)

3. **Early stopping:**
   - Monitor validation loss
   - Stop if no improvement for 10 epochs
   - Restore best weights

4. **Model evaluation:**
   - Accuracy
   - Precision, Recall, F1-score
   - ROC-AUC
   - Confusion matrix

---

## Expected Performance

### Baseline Expectations

**Simple threshold model (ADC > 300):**
- Accuracy: ~85-90%
- Precision: ~60-70%
- Recall: ~70-80%

**MLP Model (with feature engineering):**
- Accuracy: ~90-95%
- Precision: ~75-85%
- Recall: ~80-90%
- ROC-AUC: ~0.95

**Why these expectations:**
- Clear separation between coincidence and non-coincidence ADC distributions
- Coincidence events have significantly higher ADC values
- Environmental features may add small improvements
- Class imbalance may affect precision/recall balance

---

## Implementation Plan

### Step 1: Data Preparation
- [ ] Load data from CSV partitions
- [ ] Normalize features
- [ ] Split into train/validation/test sets
- [ ] Handle missing values

### Step 2: Model Definition
- [ ] Define MLP architecture (PyTorch or TensorFlow)
- [ ] Set up optimizer and loss function
- [ ] Configure class weights for imbalance

### Step 3: Training
- [ ] Train model on Node 1 data
- [ ] Train model on Node 2 data
- [ ] Train model on Node 3 data (if available)
- [ ] Save model checkpoints

### Step 4: Evaluation
- [ ] Evaluate on test sets
- [ ] Generate confusion matrices
- [ ] Calculate metrics (accuracy, precision, recall, F1, ROC-AUC)
- [ ] Visualize predictions vs ground truth

### Step 5: Feature Analysis
- [ ] Calculate feature importance
- [ ] Visualize feature contributions
- [ ] Identify most important features

---

## Physics Validation

### Scientific Checks

1. **Energy Spectrum:**
   - Model predictions should preserve ADC distribution
   - Coincidence predictions should cluster around ADC > 300

2. **Coincidence Rate:**
   - Predicted coincidence rate should be ~12-15%
   - Should match observed physics

3. **Environmental Correlations:**
   - Model should account for pressure/temperature effects
   - Predictions should be stable across environmental conditions

4. **Temporal Stability:**
   - Model performance should be consistent over time
   - No significant drift in predictions

---

## Code Structure

```
scripts/
├── train_baseline_model.py      # Main training script
├── model_architecture.py         # MLP model definition
├── data_preprocessing.py         # Feature engineering
├── evaluate_model.py             # Model evaluation
├── predict_events.py             # Inference script
└── models/                       # Saved model checkpoints
    ├── node1_model.pth
    ├── node2_model.pth
    └── node3_model.pth (if available)
```

---

## Next Steps (Day 3-4)

1. **Implement data preprocessing:**
   - Feature normalization
   - Train/validation/test splits
   - Class weight calculation

2. **Implement MLP model:**
   - Define architecture
   - Set up training loop
   - Add early stopping

3. **Train models:**
   - Train on each data partition
   - Save model checkpoints
   - Log training metrics

4. **Evaluate models:**
   - Test set evaluation
   - Generate metrics and visualizations
   - Physics validation

5. **Prepare for federated learning:**
   - Ensure models are compatible with FL framework
   - Document model architecture
   - Prepare model weights for aggregation

---

## References

- **CosmicWatch Physics:** Coincidence events represent muons passing through both detectors (higher energy)
- **ADC Values:** Proportional to energy deposited in scintillator
- **SiPM Voltage:** Correlated with photon detection (energy proxy)
- **Expected Coincidence Rate:** 5-15% (matches observed 12.3%)
- **SC25 Plan:** Simple MLP for baseline, federated learning for distributed training

---

## Success Criteria

✅ **Model achieves >90% accuracy on test set**
✅ **Model preserves physics (coincidence rate ~12-15%)**
✅ **Model is ready for federated learning integration**
✅ **Model can make real-time predictions**
✅ **Model performance is documented and reproducible**

