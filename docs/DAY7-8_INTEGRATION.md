# Day 7-8: Integration & Visualization

## Overview

Integration of all components into a working demonstration pipeline with real-time inference and visualization capabilities.

## Implementation Status

### ✅ Completed

1. **Real-Time Inference Pipeline** (`real_time_inference.py`)
   - Streams data from Elasticsearch
   - Extracts features from new documents
   - Runs model inference using trained baseline model
   - Updates Elasticsearch documents with predictions
   - Continuous monitoring mode

2. **Visualization Dashboard** (`visualization_dashboard.py`)
   - Real-time statistics dashboard
   - Event counts over time
   - Coincidence rate vs prediction rate comparison
   - Model accuracy tracking
   - Generates PNG visualizations

3. **Demonstration Script** (`demo_script.py`)
   - Orchestrates all components
   - Monitors data collection status
   - Starts/stops inference and dashboard
   - Status reporting

## Components

### Real-Time Inference Pipeline

**Purpose:** Add ML predictions to incoming data in real-time

**Features:**
- Queries Elasticsearch for new documents (configurable time window)
- Extracts features (ADC, SiPM, temperature, pressure, accel_z)
- Runs inference using trained baseline model
- Updates documents with `ml_prediction` and `ml_probability` fields
- Continuous polling mode or one-time execution

**Usage:**
```bash
cd scripts
python3 real_time_inference.py

# Run once
python3 real_time_inference.py --once

# Custom settings
python3 real_time_inference.py --window 10 --interval 60
```

**Configuration:**
- `ES_HOST`: Elasticsearch host (default: https://localhost:9200)
- `ES_USER`: Elasticsearch username (default: elastic)
- `ES_PASS`: Elasticsearch password
- `ES_INDEX`: Index name (default: credo-detections)
- `QUERY_WINDOW_MINUTES`: Time window for querying (default: 5 minutes)
- `POLL_INTERVAL_SECONDS`: Polling interval (default: 30 seconds)

### Visualization Dashboard

**Purpose:** Create visualizations of real-time data and model performance

**Features:**
- Real-time statistics (last 24 hours)
- Event counts over time (hourly)
- Coincidence rate vs prediction rate comparison
- Model accuracy calculation
- Generates dashboard PNG file

**Usage:**
```bash
cd scripts
python3 visualization_dashboard.py

# Update once
python3 visualization_dashboard.py --once

# Custom interval
python3 visualization_dashboard.py --interval 120
```

**Output:**
- `data/dashboard/dashboard_summary.png` - Main dashboard visualization

**Metrics Displayed:**
- Total events (last 24 hours)
- Coincidence events count and rate
- Predicted coincidence count and rate
- Model accuracy (last hour)
- Hourly trends

### Demonstration Script

**Purpose:** Orchestrate and monitor the complete demonstration

**Features:**
- Checks Elasticsearch connectivity
- Monitors data collection status
- Starts/stops inference pipeline
- Starts/stops visualization dashboard
- Status reporting

**Usage:**
```bash
cd scripts
python3 demo_script.py
```

**Options:**
1. Start real-time inference pipeline
2. Start visualization dashboard
3. Start both
4. Status check only

## Data Flow

```
CosmicWatch Detectors
    ↓
Elasticsearch (credo-detections index)
    ↓
Real-Time Inference Pipeline
    ↓
Elasticsearch (with ml_prediction field)
    ↓
Visualization Dashboard
    ↓
Dashboard PNG files
```

## Integration with Kibana

The inference pipeline adds two fields to Elasticsearch documents:
- `ml_prediction`: Binary prediction (0 or 1)
- `ml_probability`: Prediction probability (0.0 to 1.0)
- `ml_timestamp`: When prediction was made

These fields can be visualized in Kibana:
1. Navigate to Kibana Dashboard
2. Create visualizations using `ml_prediction` field
3. Compare `coincident` (actual) vs `ml_prediction` (predicted)
4. Filter by `ml_timestamp` for recent predictions

## Model Requirements

The inference pipeline requires:
- Trained model: `scripts/models/binary_baseline_model.pth`
- Scaler: `scripts/models/binary_baseline_scaler.pkl`

These are created by `train_binary_baseline.py` (Day 3-4).

## Testing

### Test Inference Pipeline
```bash
cd scripts
python3 real_time_inference.py --once
```

### Test Dashboard
```bash
cd scripts
python3 visualization_dashboard.py --once
```

### Test Full Demo
```bash
cd scripts
python3 demo_script.py
# Choose option 3 (Both)
```

## Expected Output

### Inference Pipeline
```
======================================================================
Real-Time Inference Pipeline
======================================================================
Elasticsearch: https://localhost:9200
Index: credo-detections
Model: models/binary_baseline_model.pth
Query window: 5 minutes
Poll interval: 30 seconds
======================================================================

Loading model and scaler...
✓ Model loaded: models/binary_baseline_model.pth
✓ Scaler loaded: models/binary_baseline_scaler.pkl
✓ Device: cpu

Running in continuous mode (Ctrl+C to stop)...

[14:30:15] Processed 5 new documents (total: 5)
  ✓ Coincidence predicted (prob=0.723) for doc abc12345...
```

### Dashboard
```
======================================================================
CosmicWatch Visualization Dashboard
======================================================================
Elasticsearch: https://localhost:9200
Index: credo-detections
Output directory: data/dashboard
Update interval: 60 seconds
======================================================================

Running in continuous mode (Ctrl+C to stop)...

[14:30:00] Updating dashboard...
  Total events: 40,207
  Coincidence events: 4,947 (12.30%)
  Predicted coincidence: 4,850
  Model accuracy: 94.2%
✓ Dashboard saved: data/dashboard/dashboard_summary.png
```

## Troubleshooting

### Inference Pipeline Issues

**No model found:**
- Ensure `train_binary_baseline.py` has been run
- Check that model files exist in `scripts/models/`

**Elasticsearch connection error:**
- Verify port-forwarding is active: `kubectl port-forward ...`
- Check ES_HOST, ES_USER, ES_PASS environment variables

**No new documents:**
- Check data collection is running
- Verify documents have `source: cosmicwatch-v3x`
- Adjust `QUERY_WINDOW_MINUTES` if needed

### Dashboard Issues

**No data available:**
- Check Elasticsearch connectivity
- Verify data exists in the index
- Check time range (default: last 24 hours)

**Accuracy calculation fails:**
- Ensure inference pipeline has run
- Check that documents have both `coincident` and `ml_prediction` fields

## Next Steps

1. **Test Components:**
   - Run inference pipeline on recent data
   - Generate dashboard visualizations
   - Verify predictions in Kibana

2. **Prepare for SC25:**
   - Test full demonstration script
   - Create backup plans
   - Document talking points

3. **Enhancements (if time permits):**
   - Add more visualization types
   - Create Kibana dashboard templates
   - Add alerting for anomalies

## Files Created

- `scripts/real_time_inference.py` - Real-time inference pipeline
- `scripts/visualization_dashboard.py` - Visualization dashboard
- `scripts/demo_script.py` - Demonstration orchestrator
- `docs/DAY7-8_INTEGRATION.md` - This document

## Status

**Implementation:** ✅ Complete  
**Testing:** ⏳ Ready for testing  
**Ready for:** Day 7-8 execution and SC25 demonstration




