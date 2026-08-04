# Scripts Directory

This directory contains scripts for data analysis, model training, and federated learning.

## Data Export and Analysis

### `export_cosmicwatch_data.py`
Exports CosmicWatch data from Elasticsearch to JSON format.

**Usage:**
```bash
export ES_HOST="https://localhost:9200"
export ES_USER="elastic"
export ES_PASS="your-password"
export ES_INDEX="credo-detections"
python3 export_cosmicwatch_data.py
```

**Output:** `data/cosmicwatch_data_export.json`

### `analyze_and_partition_data.py`
Analyzes CosmicWatch data and partitions it for federated learning.

**Usage:**
```bash
python3 analyze_and_partition_data.py
```

**Requirements:** `cosmicwatch_data_export.json` must exist in `data/` directory

**Output:**
- `data/data_partitions/node1_coincidence_events.json` - Coincidence events
- `data/data_partitions/node1_coincidence_events.csv` - Training-ready CSV
- `data/data_partitions/node2_non_coincidence_events.json` - Non-coincidence events
- `data/data_partitions/node2_non_coincidence_events.csv` - Training-ready CSV

## Data Files

Large data files are stored in `data/` directory and are gitignored:
- `cosmicwatch_data_export.json` - Full data export (~40,000 documents)
- `data_partitions/` - Partitioned data for training

## Model Training (Day 3-4)

Scripts for model training will be added here:
- `train_baseline_model.py` - Train baseline models
- `evaluate_model.py` - Evaluate model performance
- `predict_events.py` - Real-time inference

## Federated Learning (Day 5-6)

Scripts for federated learning will be added here:
- `federated_learning_server.py` - FL server
- `federated_learning_client.py` - FL clients
- `run_federated_experiment.py` - Main experiment script

