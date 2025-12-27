# Federated Learning Roadmap for SC25 Demonstration

## Current Data Status

**Elasticsearch Data:**
- **Total documents:** 107,804
- **CREDO.science (legacy):** 69,000 documents
- **CosmicWatch v3X:** 39,677 documents (coincidence detection system)
  - Device: `cosmicwatch-001` (single coincidence detection system)
  - **Coincidence events:** 4,874 (12.3%) - both detectors detect same particle
  - **Non-coincidence events:** 34,803 (87.7%) - single detector
  - **Coincidence ADC average:** 394.7 (higher energy particles)
  - **Non-coincidence ADC average:** 249.4
  - Data fields: ADC values, SiPM voltages, temperature, pressure, accelerometer, gyroscope
  - Time range: ~6 days of data
  - ADC range: 67-4053, average: 267.5
  - SiPM voltage range: 3.4-1000 mV, average: 13.9 mV

## Challenge: Federated Learning with Coincidence Detection System

**Important Finding:** The two detectors are stacked and connected via ethernet cable, operating as a **single coincidence detection system**, not as two independent detectors. The data shows:
- Only one `device_id`: `cosmicwatch-001`
- Coincidence events: 12.3% (4,874 events) - when both detectors detect the same particle (Flag=1)
- Coincidence events have higher average ADC (394.7 vs 249.4) - indicating muons with sufficient energy to trigger both detectors simultaneously
- **Physics basis:** The CosmicWatch detector uses "coincidence mode with a second detector for background suppression" (from README.md)

**Implication:** We cannot treat them as two separate federated learning nodes. Instead, we need to use the coincidence detection capability and leverage CREDO.science data as additional nodes.

## Strategy 1: Coincidence-Based Data Partitioning (Recommended for SC25)

### Concept
Partition data by coincidence patterns and use CREDO.science data as additional federated learning nodes.

### Implementation Approach

1. **Data Partitioning:**
   - Node 1: Coincidence events (both detectors detect same particle) - 4,874 events
   - Node 2: Non-coincidence events (single detector) - 34,803 events
   - Node 3: CREDO.science historical data - 69,000 documents

2. **Federated Learning Architecture:**
   ```
   Node 1 (Coincidence Events) ──┐
                                 ├──> Federated Learning Server ──> Global Model
   Node 2 (Non-Coincidence) ────┤
                                 │
   Node 3 (CREDO.science data) ──┘
   ```

3. **Training Workflow:**
   - Node 1 trains on high-energy coincidence events (both detectors)
   - Node 2 trains on single-detector events
   - Node 3 trains on historical CREDO data
   - Models exchange parameters (not raw data)
   - Global model aggregates knowledge from all nodes

### Benefits
- Demonstrates federated learning concept with meaningful data partitions
- Coincidence events represent different physics (higher energy particles)
- Shows how different event types can contribute to federated learning
- Leverages existing CREDO.science data as third node
- Validates architecture for future multi-institution deployment

## Strategy 2: Time-Based and Geographic Partitioning (Alternative)

### Concept
Partition CREDO.science data by time period or geographic region to create multiple federated learning nodes.

### Implementation Approach

1. **Data Sources as Nodes:**
   - Node 1: CosmicWatch coincidence events (real-time, high-energy)
   - Node 2: CosmicWatch non-coincidence events (real-time, single-detector)
   - Node 3: CREDO.science data - Time period 1 (e.g., 2017)
   - Node 4: CREDO.science data - Time period 2 (e.g., 2018)
   - Node 5: CREDO.science data - Geographic region 1 (if location data available)
   - Node 6: CREDO.science data - Geographic region 2 (if location data available)

2. **Partitioning Strategy:**
   - Partition CREDO data by time period (different years)
   - Or partition by geographic region (if location data available)
   - Each partition acts as a separate node
   - Simulates distributed deployment across time/space

### Benefits
- More realistic demonstration with multiple data sources
- Shows how historical data can participate in federated learning
- Demonstrates scalability
- Time-based partitioning shows how models can learn from different time periods

## Strategy 3: Focus on Edge AI Processing with Coincidence Detection (Alternative)

### Concept
Focus on edge AI processing at the coincidence detection system, demonstrating space-ready architecture.

### Implementation Approach

1. **Edge Processing:**
   - Coincidence detection system runs local AI model for event classification
   - Model processes data locally (edge computing)
   - Classifies events as coincidence vs non-coincidence
   - Predicts energy levels based on ADC values and coincidence patterns

2. **Federated Learning Elements:**
   - Model can share parameters with CREDO.science data nodes
   - Demonstrates space-ready architecture (autonomous edge processing)
   - Shows bandwidth efficiency (only model updates shared, not raw data)

### Benefits
- Aligns with space mission requirements
- Demonstrates edge AI capabilities
- Shows power efficiency (0.5W detectors)
- Coincidence detection is scientifically meaningful (higher energy particles)

## Recommended Implementation Plan

### Phase 1: Data Preparation (Week 1-2)

1. **Ensure coincidence detection system is streaming:**
   ```bash
   # Verify coincidence detection system is posting to Elasticsearch
   # Check coincidence flag to distinguish event types
   ```

2. **Data Analysis:**
   - Analyze data distributions for coincidence vs non-coincidence events
   - Compare ADC values: coincidence events (avg 394.7) vs non-coincidence (avg 249.4)
   - Identify features for model training (ADC, SiPM, coincidence flag, etc.)
   - Prepare training datasets

3. **Data Partitioning:**
   - Partition data by `coincident` flag (coincidence vs non-coincidence events)
   - Partition CREDO data by time period or geographic region
   - Create separate training sets for each node

### Phase 2: Model Development (Week 2-3)

1. **Task Definition:**
   - **Classification task:** 
     - Option A: Classify events by energy level (low/medium/high based on ADC + coincidence)
     - Option B: Predict coincidence from ADC and other features
     - Option C: Classify event types (coincidence vs non-coincidence)
   - **Features:** ADC values, SiPM voltages, coincidence flags, environmental data
   - **Labels:** 
     - Coincidence flag (binary: coincidence vs non-coincidence)
     - Energy level (derived from ADC: low < 200, medium 200-500, high > 500)
     - Or: Combined label (coincidence + energy level)

2. **Model Architecture:**
   - Simple neural network (e.g., 2-3 layer MLP)
   - Input: [ADC, SiPM, temperature, pressure, accel_x, accel_y, accel_z]
   - Output: Event classification (e.g., low/medium/high energy)

3. **Local Training:**
   - Train model on each node's data
   - Evaluate local performance

### Phase 3: Federated Learning Implementation (Week 3-4)

1. **Federated Learning Framework:**
   - Use PySyft, Flower, or TensorFlow Federated
   - Implement Federated Averaging (FedAvg) algorithm

2. **Federated Learning Server:**
   - Deploy on NRP Nautilus (patternlab.calit2.optiputer.net)
   - Coordinates model aggregation
   - Manages training rounds

3. **Client Nodes:**
   - Node 1: Coincidence events (high-energy, both detectors)
   - Node 2: Non-coincidence events (single-detector)
   - Node 3: CREDO.science data (historical, partitioned by time/region)

### Phase 4: Demonstration Setup (Week 4-5)

1. **Real-time Pipeline:**
   - Stream data from detectors → Elasticsearch
   - Extract features → Model input
   - Run inference → Classify events
   - Update model via federated learning

2. **Visualization:**
   - Kibana dashboard showing:
     - Real-time detections
     - Model predictions
     - Federated learning metrics (accuracy, loss)
     - Model update rounds

3. **Demo Script:**
   - Automated federated learning rounds
   - Show model improvement over time
   - Compare local vs. global model performance

## Technical Implementation Details

### Federated Learning Algorithm: FedAvg

```python
# Pseudocode for Federated Averaging
def federated_averaging(global_model, local_models, client_weights):
    """
    Aggregate local model parameters
    """
    global_params = {}
    total_weight = sum(client_weights)
    
    for param_name in global_model.parameters():
        weighted_sum = sum(
            local_model[param_name] * weight
            for local_model, weight in zip(local_models, client_weights)
        )
        global_params[param_name] = weighted_sum / total_weight
    
    return global_params
```

### Data Pipeline

```
CosmicWatch Coincidence Detection System (2 stacked detectors)
    ↓ (serial/USB, ethernet connection)
import_data_to_elasticsearch.py
    ↓
Elasticsearch (indexed by coincidence flag)
    ↓
Feature Extraction
    ↓
Local Model Training
    ├─ Node 1: Coincidence events (high-energy)
    ├─ Node 2: Non-coincidence events (single-detector)
    └─ Node 3: CREDO.science data
    ↓
Federated Learning Server
    ↓
Global Model
    ↓
Model Updates → All Nodes
```

### Model Features

**Input Features:**
- `adc_value` (0-4095)
- `sipm_mv` (voltage)
- `coincident` (boolean)
- `temperature_c`
- `pressure_pa`
- `accel_x_g`, `accel_y_g`, `accel_z_g`
- `gyro_x_degs`, `gyro_y_degs`, `gyro_z_degs`

**Output:**
- Event classification (e.g., energy level categories)
- Or: Anomaly detection
- Or: Coincidence prediction

## Demonstration Scenarios

### Scenario 1: Real-time Federated Learning with Coincidence Detection
- Show live data streaming from coincidence detection system
- Demonstrate local model training on coincidence vs non-coincidence events
- Show how coincidence events (higher energy) improve model
- Show federated averaging creating global model with CREDO data
- Display improved accuracy from collaboration

### Scenario 2: Historical Data Integration
- Use CREDO.science data as third node
- Show how historical data improves model
- Demonstrate data sovereignty (data stays at source)

### Scenario 3: Edge AI Processing
- Show local inference at each detector
- Demonstrate bandwidth efficiency (only model updates shared)
- Show space-ready architecture

## Next Steps

1. **Immediate:**
   - [x] Coincidence detection system is streaming to Elasticsearch
   - [ ] Verify data quality and completeness
   - [ ] Analyze data distributions (coincidence vs non-coincidence)
   - [ ] Partition data by coincidence flag

2. **Short-term (1-2 weeks):**
   - [ ] Choose federated learning framework (Flower recommended)
   - [ ] Define classification task
   - [ ] Develop baseline model
   - [ ] Implement data partitioning

3. **Medium-term (2-4 weeks):**
   - [ ] Implement federated learning server
   - [ ] Set up client nodes
   - [ ] Run federated learning experiments
   - [ ] Evaluate model performance

4. **Long-term (4-6 weeks):**
   - [ ] Integrate with real-time data pipeline
   - [ ] Create visualization dashboard
   - [ ] Prepare demonstration script
   - [ ] Document results

## Tools and Frameworks

### Federated Learning Frameworks
- **Flower (Flwr):** Recommended - Python-based, easy to use
- **PySyft:** More advanced, supports secure aggregation
- **TensorFlow Federated:** Google's framework
- **FedML:** Comprehensive ML framework

### Machine Learning
- **TensorFlow/Keras:** Model development
- **PyTorch:** Alternative framework
- **Scikit-learn:** For simpler models

### Data Processing
- **Elasticsearch:** Data storage and querying
- **Pandas:** Data manipulation
- **NumPy:** Numerical operations

## Key Metrics to Track

1. **Data Metrics:**
   - Events per detector
   - Data distribution (ADC, SiPM, etc.)
   - Data quality (missing values, outliers)

2. **Model Metrics:**
   - Local model accuracy (per node)
   - Global model accuracy
   - Convergence rate
   - Communication rounds

3. **System Metrics:**
   - Latency (data → model → prediction)
   - Bandwidth usage (model updates only)
   - Power consumption (edge processing)

## Success Criteria

1. **Technical:**
   - Federated learning successfully aggregates models from 2+ nodes
   - Global model performs better than individual local models
   - Real-time data pipeline works end-to-end

2. **Demonstration:**
   - Clear visualization of federated learning process
   - Show data sovereignty (data stays at source)
   - Demonstrate space-ready architecture

3. **Research:**
   - Validates federated learning for cosmic ray detection
   - Shows feasibility for space deployment
   - Demonstrates edge AI processing

## Resources

- **Flower Documentation:** https://flower.dev/
- **Federated Learning Papers:** FedAvg, FedProx
- **CREDO Data:** Already in Elasticsearch
- **NRP Nautilus:** Infrastructure for federated learning server

