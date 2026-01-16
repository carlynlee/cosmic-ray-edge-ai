# RC3-SC Data Collection Guide

This guide explains how to collect more unique data using the RC3-SC nodes (rc3-sc-13, rc3-sc-14, rc3-sc-15).

## Overview

The script `deploy/05-deploy-rc3-data-collectors.sh` deploys **additional data collection pods** on the RC3-SC nodes. Each pod:
- Runs independently on its own node
- Has its own data export state (tracks `last_exported_detection`)
- Collects **new, unique data** that hasn't been collected yet
- Stores data in `/workspace/credo-data-rc3/` inside each pod

## Quick Start

### 1. Deploy Data Collectors on RC3-SC Nodes

```bash
cd /Users/carlyn_oligo/Downloads/credo-api-tools
./deploy/05-deploy-rc3-data-collectors.sh deploy
```

This will:
- Create 3 data collector pods (one on each RC3-SC node)
- Set up the data exporter in each pod
- Wait for pods to be ready

### 2. Start Data Collection

```bash
./deploy/05-deploy-rc3-data-collectors.sh start
```

This starts data collection in the background on all 3 collectors. Each collector will:
- Fetch data from CREDO.science API
- Track what it has already collected (using `last_exported_detection`)
- Collect **new data** that hasn't been exported yet
- Store JSON files in `/workspace/credo-data-rc3/detections/` inside each pod

### 3. Check Status

```bash
./deploy/05-deploy-rc3-data-collectors.sh status
```

This shows:
- Pod status and which node each is on
- Whether data collection is running
- How many data files have been collected
- Latest log entries

### 4. Copy Collected Data to Local Machine

```bash
# Copy to default location: ./credo-data-rc3-collected
./deploy/05-deploy-rc3-data-collectors.sh copy

# Or specify a custom directory
./deploy/05-deploy-rc3-data-collectors.sh copy ./my-rc3-data
```

This copies all collected data from all 3 pods to your local machine.

## How It Works

### Data Collection Process

1. **Each pod maintains its own state:**
   - File: `/workspace/credo-data-rc3/last_exported_detection`
   - Tracks the timestamp of the last detection it exported
   - Ensures no duplicate data collection

2. **Incremental data fetching:**
   - The data exporter uses `last_exported_detection` to request only NEW data
   - Each pod can collect different time ranges
   - All pods together collect more data in parallel

3. **Data storage:**
   - Inside pods: `/workspace/credo-data-rc3/detections/*.json`
   - Each pod has its own directory
   - Data persists until pod is deleted

### Why This Collects More Unique Data

- **Parallel collection:** 3 pods collecting simultaneously = 3x faster
- **Independent state:** Each pod tracks its own progress
- **No conflicts:** Each pod requests different time ranges
- **More coverage:** Can collect data from different time periods in parallel

## Data Structure

After copying data locally, you'll have:

```
credo-data-rc3-collected/
├── rc3-sc-13/
│   └── detections/
│       ├── export_<timestamp1>_<timestamp2>.json
│       └── ...
├── rc3-sc-14/
│   └── detections/
│       ├── export_<timestamp1>_<timestamp2>.json
│       └── ...
└── rc3-sc-15/
    └── detections/
        ├── export_<timestamp1>_<timestamp2>.json
        └── ...
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `./deploy/05-deploy-rc3-data-collectors.sh deploy` | Deploy collectors on all RC3-SC nodes |
| `./deploy/05-deploy-rc3-data-collectors.sh start` | Start data collection on all collectors |
| `./deploy/05-deploy-rc3-data-collectors.sh status` | Show status of all collectors |
| `./deploy/05-deploy-rc3-data-collectors.sh copy [dir]` | Copy collected data to local directory |
| `./deploy/05-deploy-rc3-data-collectors.sh help` | Show help message |

## Manual Data Collection

If you want to manually trigger data collection on a specific pod:

```bash
# Get pod name
POD=$(kubectl get pods -n cblee-credo -l app=credo-data-collector,node=rc3-sc-13 -o jsonpath='{.items[0].metadata.name}')

# Start data collection
kubectl exec -n cblee-credo $POD -- bash -c "
    export CREDO_TOKEN='e26fcf245c7b96a4c8daf5b72ddc17d34891ea0e68b10bd396e547ec74917656'
    cd /workspace/data-exporter
    python3 credo-data-exporter.py --token \$CREDO_TOKEN --dir /workspace/credo-data-rc3 --max-chunk-size 1000 --data-type detection
"
```

## Viewing Collected Data

### Inside Pods

```bash
# List files in a specific collector
POD=$(kubectl get pods -n cblee-credo -l app=credo-data-collector,node=rc3-sc-13 -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n cblee-credo $POD -- ls -lh /workspace/credo-data-rc3/detections/

# View a specific file
kubectl exec -n cblee-credo $POD -- cat /workspace/credo-data-rc3/detections/export_*.json | head -100
```

### After Copying Locally

```bash
# List all collected files
find ./credo-data-rc3-collected -name "*.json" | wc -l

# View a file
cat ./credo-data-rc3-collected/rc3-sc-13/detections/export_*.json | python3 -m json.tool | head -50
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n cblee-credo -l app=credo-data-collector

# Check pod logs
kubectl logs -n cblee-credo <pod-name>
```

### Data Collection Not Working

```bash
# Check if collection process is running
POD=$(kubectl get pods -n cblee-credo -l app=credo-data-collector,node=rc3-sc-13 -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n cblee-credo $POD -- cat /tmp/data-collection.log

# Check process status
kubectl exec -n cblee-credo $POD -- ps aux | grep credo-data-exporter
```

### Node Affinity Issues

If pods can't be scheduled on RC3-SC nodes:

```bash
# Check node labels
kubectl get nodes --show-labels | grep rc3-sc

# Check pod events
kubectl describe pod -n cblee-credo <pod-name>
```

## Combining with Existing Data

The data collected from RC3-SC nodes is separate from your existing data collection. You can:

1. **Keep them separate:** Use RC3-SC data for different experiments
2. **Combine them:** Copy all data to one location and process together
3. **Compare:** Analyze differences between data collected on different nodes

## Next Steps

After collecting data:

1. **Process the data:**
   ```bash
   python3 data-processor/credo-data-processor.py --dir ./credo-data-rc3-collected/rc3-sc-13 --data-type detection
   ```

2. **Index to Elasticsearch:**
   - Use the existing Elasticsearch pod
   - Or create a new index for RC3-SC data

3. **Use in federated learning:**
   - The collected data can be used in your FL training
   - Each RC3-SC collector can act as a separate data source

## Summary

- **3 pods** collecting data in parallel on RC3-SC nodes
- Each pod collects **unique, new data** (no duplicates)
- Data stored **inside pods** at `/workspace/credo-data-rc3/`
- Copy to local machine when ready to analyze
- **3x faster** data collection compared to single pod

