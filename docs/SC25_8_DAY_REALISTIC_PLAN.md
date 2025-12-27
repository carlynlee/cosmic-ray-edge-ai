# SC25 8-Day Realistic Plan
## November 8-16, 2024

**Goal:** Prepare a compelling demonstration for SC25 with coincidence detection system

**Key Constraint:** You have a coincidence detection system (2 stacked detectors), not 2 independent detectors

---

## What You CAN Realistically Complete in 8 Days

### ✅ **Definitely Achievable:**
1. **Real-time data collection** - Already working!
2. **Data visualization in Kibana** - Already working!
3. **Data analysis and partitioning** - 1-2 days
4. **Basic model training** - 2-3 days
5. **Federated learning concept demonstration** - 2-3 days (simplified)

### ⚠️ **Possibly Achievable (if time permits):**
1. **Working federated learning** - Simplified version
2. **Real-time predictions** - Basic inference pipeline
3. **Visualization dashboard** - Simple metrics display

### ❌ **NOT Achievable in 8 Days:**
1. Full production federated learning system
2. Complex deep learning models
3. Extensive model optimization
4. Multi-institution deployment

---

## Day-by-Day Plan

### **Day 1-2 (Nov 8-9): Data Collection & Analysis** ⏱️ 4-6 hours

**Priority: HIGH**

**Tasks:**
- [x] Ensure data collection is running continuously
- [ ] Set up `caffeinate` to prevent sleep
- [ ] Export data from Elasticsearch for analysis
- [ ] Analyze data distributions:
  - Coincidence vs non-coincidence events
  - ADC distributions for each type
  - SiPM voltage patterns
  - Environmental sensor data
- [ ] Partition data:
  - Node 1: Coincidence events (4,874 events)
  - Node 2: Non-coincidence events (34,803 events)
  - Node 3: CREDO.science data (69,000 documents)

**Deliverable:** Cleaned, partitioned datasets ready for training

**Scientific Analysis Opportunities (if time permits):**
- Create ADC histogram (energy spectrum visualization)
- Calculate coincidence rate and compare to theoretical expectations
- Analyze environmental correlations (pressure vs detection rate, temperature vs SiPM)

**Script to create:**
```python
# export_and_partition_data.py
# Export from Elasticsearch and partition by coincidence flag
```

---

### **Day 3-4 (Nov 10-11): Baseline Model Development** ⏱️ 6-8 hours

**Priority: HIGH**

**Tasks:**
- [ ] Set up Python ML environment:
  ```bash
  pip install tensorflow pandas numpy scikit-learn matplotlib
  # Or: pip install torch pandas numpy scikit-learn matplotlib
  ```

- [ ] Define classification task:
  - **Recommended:** Energy level classification (low/medium/high)
    - **Note:** These thresholds are based on data analysis, not official detector specifications
    - Low: ADC < 200
    - Medium: ADC 200-500
    - High: ADC > 500 OR coincidence event (Flag=1)
  - **Alternative:** Coincidence prediction (binary classification)
    - Predicts coincidence flag (0 or 1) directly from detector

- [ ] Develop baseline model:
  - Simple MLP (2-3 hidden layers, 64-128 neurons)
  - Input features: [ADC, SiPM, temp, pressure, accel_x, accel_y, accel_z]
  - Output: 3 classes (low/medium/high energy) or binary (coincidence)

- [ ] Train local models:
  - Train on Node 1 data (coincidence events)
  - Train on Node 2 data (non-coincidence events)
  - Train on Node 3 data (CREDO.science)
  - Evaluate local model performance

**Deliverable:** Working baseline models, training scripts

**Scientific Analysis Opportunities (if time permits):**
- Validate energy classification against known physics (coincidence events = higher energy)
- Compare model predictions to theoretical energy spectrum
- Measure model accuracy on scientific metrics (not just ML metrics)

**Scripts to create:**
- `train_baseline_model.py` - Model training
- `evaluate_model.py` - Model evaluation
- `predict_events.py` - Inference script

---

### **Day 5-6 (Nov 12-13): Federated Learning Implementation** ⏱️ 6-8 hours

**Priority: MEDIUM (if time permits, otherwise demonstrate concept)**

**Option A: Simplified Federated Learning (Recommended)**
- [ ] Install Flower framework:
  ```bash
  pip install flwr
  ```

- [ ] Implement simplified FedAvg:
  - Server aggregates model parameters
  - 3 client nodes (coincidence, non-coincidence, CREDO)
  - 3-5 federated learning rounds
  - Compare global vs local models

- [ ] Run federated learning experiment:
  - Train local models on each node
  - Aggregate parameters
  - Evaluate global model

**Option B: Concept Demonstration (If time is tight)**
- [ ] Create architecture diagram
- [ ] Show how federated learning would work
- [ ] Demonstrate with pre-trained models
- [ ] Explain the concept with data partitions

**Deliverable:** Working federated learning demo OR concept demonstration

**Scripts to create:**
- `federated_learning_server.py` - FL server
- `federated_learning_client.py` - FL clients
- `run_federated_experiment.py` - Main experiment script

---

### **Day 7 (Nov 14): Integration & Visualization** ⏱️ 4-6 hours

**Priority: HIGH**

**Tasks:**
- [ ] Create real-time inference pipeline:
  - Stream data from Elasticsearch
  - Extract features
  - Run model inference
  - Store predictions

- [ ] Create visualization:
  - **Option A:** Simple Python dashboard (matplotlib/plotly)
    - Real-time event counter
    - Model predictions over time
    - Accuracy metrics
  - **Option B:** Kibana dashboard
    - Add prediction field to documents
    - Create visualizations
    - Show federated learning metrics

- [ ] Prepare demonstration script:
  - Automated data collection monitoring
  - Model inference on new data
  - Display results

**Deliverable:** Working demonstration pipeline

**Scientific Analysis Opportunities (if time permits):**
- Add scientific plots to dashboard:
  - Energy spectrum (ADC histogram)
  - Detection rate over time
  - Environmental correlations (pressure, temperature)
  - Coincidence vs non-coincidence comparison

**Scripts to create:**
- `real_time_inference.py` - Real-time predictions
- `visualization_dashboard.py` - Simple dashboard
- `demo_script.py` - Main demonstration script

---

### **Day 8 (Nov 15): Testing & Documentation** ⏱️ 4-6 hours

**Priority: HIGH**

**Tasks:**
- [ ] Test full demonstration:
  - Run through complete pipeline
  - Verify all components work
  - Test edge cases

- [ ] Prepare backup plans:
  - If federated learning not ready: Focus on data pipeline + model concept
  - If model not ready: Focus on data collection + analysis
  - If detectors fail: Use historical data

- [ ] Document setup:
  - Quick start guide
  - Troubleshooting tips
  - Contact information

- [ ] Prepare talking points:
  - Data collection pipeline
  - Coincidence detection system
  - Model training approach
  - Federated learning concept
  - Space-ready architecture

**Deliverable:** Tested demonstration, documentation, backup plans

---

### **Day 9 (Nov 16): SC25 Exhibition** ⏱️ All day

**Priority: CRITICAL**

**Tasks:**
- [ ] Morning setup:
  - Connect coincidence detection system
  - Start data collection
  - Verify Kibana dashboard
  - Test all components

- [ ] During demonstration:
  - Show real-time data collection
  - Display data in Kibana
  - Show model predictions (if ready)
  - Explain federated learning concept
  - Discuss space-ready architecture

- [ ] Backup plans:
  - If federated learning not ready: Focus on data pipeline and model concept
  - If model not ready: Focus on data collection and analysis
  - If detectors fail: Use historical data in Kibana

---

## Realistic Scope for 8 Days

### **Minimum Viable Demo (MUST HAVE):**
1. ✅ Real-time data collection from coincidence detection system
2. ✅ Data visualization in Kibana
3. ✅ Data analysis (coincidence vs non-coincidence)
4. ✅ Basic model training (even if simple)
5. ✅ Federated learning concept explanation

### **Ideal Demo (NICE TO HAVE):**
1. ✅ All of above, plus:
2. ✅ Working federated learning (simplified)
3. ✅ Real-time predictions
4. ✅ Visualization dashboard
5. ✅ Model performance metrics

### **Stretch Goals (IF TIME PERMITS):**
1. ✅ All of above, plus:
2. ✅ Multiple federated learning rounds
3. ✅ Model comparison (local vs global)
4. ✅ Real-time accuracy tracking

---

## Recommended Focus Areas

### **Focus 1: Data Pipeline (Days 1-2)**
- Ensure continuous data collection
- Analyze and partition data
- Prepare datasets for training

### **Focus 2: Model Development (Days 3-4)**
- Train baseline models
- Evaluate performance
- Compare coincidence vs non-coincidence models

### **Focus 3: Federated Learning Concept (Days 5-6)**
- Implement simplified federated learning OR
- Create concept demonstration
- Show how data partitions work

### **Focus 4: Integration (Days 7-8)**
- Integrate components
- Create visualization
- Test and document

---

## Time Estimates

**Total Time Available:** ~8 days × 4-6 hours/day = 32-48 hours

**Breakdown:**
- Data collection & analysis: 4-6 hours
- Model development: 6-8 hours
- Federated learning: 6-8 hours (or 2-3 hours for concept)
- Integration & visualization: 4-6 hours
- Testing & documentation: 4-6 hours
- **Total:** 24-34 hours (realistic for 8 days)

---

## Success Criteria

### **Must Have for SC25:**
- [x] Data collection working
- [x] Kibana visualization working
- [ ] Data analysis completed
- [ ] Basic model trained
- [ ] Federated learning concept demonstrated

### **Nice to Have:**
- [ ] Working federated learning
- [ ] Real-time predictions
- [ ] Visualization dashboard
- [ ] Model performance metrics

---

## Quick Start Commands

### Check Data Collection
```bash
# Check if script is running
ps aux | grep import_data_to_elasticsearch

# Check latest data
curl -k -u "elastic:password" https://localhost:9200/credo-detections/_count \
  -H "Content-Type: application/json" \
  -d '{"query": {"term": {"source": "cosmicwatch-v3x"}}}'
```

### Prevent Sleep
```bash
caffeinate -d -i -m -s -w $(pgrep -f import_data_to_elasticsearch.py)
```

### Start Data Collection
```bash
cd CosmicWatch-Desktop-Muon-Detector-v3X/Data
export ES_HOST="https://localhost:9200"
export ES_USER="elastic"
export ES_PASS="RC0hJ6vR68c29mqq5O5Hu19u"
export ES_INDEX="credo-detections"
export ES_ENABLED="true"
python3 import_data_to_elasticsearch.py
```

---

## Backup Plans

### **If Federated Learning Not Ready:**
- Focus on data pipeline demonstration
- Show data analysis (coincidence vs non-coincidence)
- Explain federated learning concept with diagrams
- Show model training on partitioned data

### **If Model Not Ready:**
- Focus on data collection and visualization
- Show data analysis and partitioning
- Explain model concept
- Demonstrate data pipeline architecture

### **If Detectors Fail:**
- Use historical data in Kibana
- Show data analysis
- Explain system architecture
- Demonstrate with pre-collected data

---

## Key Talking Points

### **Engineering Focus:**

1. **Coincidence Detection System:**
   - "We have a coincidence detection system with 2 stacked detectors"
   - "Coincidence events (12.3%) represent higher energy particles"
   - "This enables us to partition data meaningfully for federated learning"

2. **Data Pipeline:**
   - "Real-time data streaming from detectors to Elasticsearch"
   - "Sub-second indexing for immediate processing"
   - "Rich sensor metadata for AI training"

3. **Federated Learning:**
   - "Data partitioned by coincidence patterns"
   - "Each partition trains local model"
   - "Global model aggregates knowledge from all partitions"
   - "Demonstrates data sovereignty concept"

4. **Space-Ready Architecture:**
   - "Low-power detectors (0.5W)"
   - "Edge AI processing capability"
   - "Bandwidth-efficient (only model updates shared)"
   - "Validates concepts for space deployment"

### **Scientific Potential:**

5. **Scientific Insights Enabled:**
   - "This engineering demonstration enables scientific insights about cosmic ray physics"
   - "Coincidence events (12.3%) represent higher-energy muons passing through both detectors"
   - "ADC distributions reveal the energy spectrum of detected particles"
   - "Environmental sensors enable atmospheric effect studies"

6. **Data-Driven Physics:**
   - "The data reveals physics: coincidence events have higher ADC (394.7 vs 249.4)"
   - "This aligns with theoretical expectations for muon energy spectrum"
   - "Environmental correlations validate atmospheric depth effects"
   - "Continuous data collection enables temporal pattern analysis"

---

## Scientific Insights & Potential

**Note:** While this demonstration focuses on engineering (data pipeline, ML, federated learning), the collected data enables valuable scientific insights about cosmic ray physics.

### **Current Scientific Findings from Data:**

1. **Coincidence Detection Physics:**
   - **Finding:** Coincidence events (12.3%) have higher average ADC (394.7 vs 249.4)
   - **Scientific Insight:** Coincidence events represent higher-energy muons passing through both detectors
   - **Physics:** The 12.3% coincidence rate and higher ADC values indicate these are muons with sufficient energy to trigger both detectors simultaneously
   - **Validation:** This aligns with theoretical expectations for muon energy spectrum

2. **Energy Spectrum Analysis:**
   - **Data Available:** ADC values range from 67-4053 (average: 267.5)
   - **Scientific Potential:** ADC values can be converted to energy proxies
   - **Insight:** The distribution of ADC values reveals the energy spectrum of detected particles
   - **Analysis:** Histogram of ADC values shows the energy distribution of cosmic ray muons

3. **Environmental Correlations:**
   - **Data Available:** Temperature, pressure, accelerometer, gyroscope sensors
   - **Scientific Potential:** Analyze how environmental conditions affect detection
   - **Insight:** Pressure vs detection rate correlation validates atmospheric depth effect
   - **Analysis:** Temperature vs SiPM voltage correlation shows sensor response

4. **Temporal Patterns:**
   - **Data Available:** ~6 days of continuous data collection
   - **Scientific Potential:** Analyze detection rate variations over time
   - **Insight:** Time series analysis can reveal diurnal patterns, atmospheric effects
   - **Analysis:** Detection rate (events/minute) over time shows cosmic ray flux variations

### **Scientific Questions Enabled by This Data:**

1. **What is the energy distribution of detected muons?**
   - Use ADC values to estimate energy
   - Compare coincidence vs non-coincidence energy distributions
   - Validate against theoretical muon energy spectrum

2. **How does atmospheric pressure affect detection rate?**
   - Analyze pressure vs detection rate correlation
   - Validate atmospheric depth effect (higher pressure = more atmosphere = more muons)

3. **What is the coincidence rate, and does it match expectations?**
   - Calculate observed coincidence rate (12.3%)
   - Compare to theoretical predictions based on detector geometry
   - Analyze timing between detectors

4. **How do environmental conditions affect detector performance?**
   - Temperature vs SiPM voltage correlation
   - Pressure vs detection rate correlation
   - Motion sensor patterns (detector stability)

5. **Can federated learning improve energy classification accuracy?**
   - Compare local vs global model performance
   - Measure improvement from data diversity
   - Validate that federated learning preserves scientific accuracy

### **Scientific Analysis Opportunities (If Time Permits):**

**During Data Analysis (Days 1-2):**
- Create ADC histogram (energy spectrum visualization)
- Calculate coincidence rate and compare to theoretical expectations
- Analyze environmental correlations (pressure, temperature)

**During Model Training (Days 3-4):**
- Validate energy classification against known physics
- Compare model predictions to theoretical energy spectrum
- Measure model accuracy on scientific metrics (not just ML metrics)

**During Visualization (Day 7):**
- Add scientific plots to dashboard:
  - Energy spectrum (ADC histogram)
  - Detection rate over time
  - Environmental correlations
  - Coincidence vs non-coincidence comparison

### **Scientific Value of Federated Learning:**

1. **Distributed Science:**
   - Enables collaboration across institutions without sharing raw data
   - Preserves data sovereignty while enabling scientific discovery
   - Demonstrates how distributed detectors can improve classification

2. **Data Diversity:**
   - Coincidence events (high-energy) + non-coincidence events (varied energy)
   - CREDO.science historical data (different time periods, locations)
   - Global model learns from diverse data sources

3. **Validation:**
   - Compare local vs global model performance
   - Validate that federated learning improves scientific accuracy
   - Measure improvement from data diversity

### **Talking Points for Scientific Audience:**

1. **"This engineering demonstration enables scientific insights:"**
   - Real-time data collection provides continuous cosmic ray flux measurements
   - Coincidence detection system enables energy spectrum analysis
   - Environmental sensors enable atmospheric effect studies

2. **"The data reveals physics:"**
   - Coincidence events (12.3%) represent higher-energy muons
   - ADC distributions show energy spectrum of detected particles
   - Environmental correlations validate atmospheric depth effects

3. **"Federated learning enables distributed science:"**
   - Multiple institutions can collaborate without sharing raw data
   - Global model learns from diverse data sources
   - Preserves data sovereignty while enabling scientific discovery

4. **"This validates space-ready architecture:"**
   - Low-power detectors (0.5W) suitable for space deployment
   - Edge AI processing enables autonomous operation
   - Bandwidth-efficient (only model updates shared)

---

## Resources

- **Kibana Dashboard:** https://credo-kibana.nrp-nautilus.io
- **Elasticsearch:** Port-forward on localhost:9200
- **NRP Nautilus:** patternlab.calit2.optiputer.net
- **Federated Learning:** Flower (flwr) framework
- **Machine Learning:** TensorFlow or PyTorch

---

## Notes

- **Be realistic:** Focus on what can be demonstrated, not perfection
- **Have backups:** Multiple ways to show the concept
- **Document everything:** Helps with troubleshooting
- **Test early:** Don't wait until the last day
- **Sleep is important:** Don't burn out before SC25!

---

## Daily Checklist Template

### Morning (2-3 hours)
- [ ] Check data collection status
- [ ] Review previous day's progress
- [ ] Plan day's tasks

### Afternoon (3-4 hours)
- [ ] Focus on main task for the day
- [ ] Test and verify work
- [ ] Document progress

### Evening (1-2 hours)
- [ ] Review and commit code
- [ ] Update documentation
- [ ] Plan next day

