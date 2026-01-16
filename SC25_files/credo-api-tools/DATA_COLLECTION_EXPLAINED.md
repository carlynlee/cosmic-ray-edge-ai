# CREDO Data Collection Flow Explained

## Quick Answer

**All data is now stored centrally in the Elasticsearch pod at `/workspace/credo-data/`.**

The `credo-data-temp/` directory you see is a **temporary staging area** used during data transfer. It should be cleaned up automatically, but may remain if a previous run was interrupted.

## Detailed Data Flow

### Step 1: Data Collection
When `populate_elasticsearch()` runs (part of the main deployment), it:

1. **Runs the data exporter in CREDO server pod, then copies to Elasticsearch pod:**
   ```bash
   # Fetch data in CREDO pod
   kubectl exec -n "$NAMESPACE" "$credo_pod" -- python3 credo-data-exporter.py --token $TOKEN --dir /tmp/credo-data-temp
   
   # Copy directly to Elasticsearch pod
   kubectl cp "$NAMESPACE/$credo_pod:/tmp/credo-data-temp/" "$NAMESPACE/$es_pod:/workspace/credo-data/"
   ```

2. **Data is saved in the Elasticsearch pod at:**
   - `/workspace/credo-data/detections/*.json` (inside the Elasticsearch pod)
   - This is where all JSON files are centrally stored

### Step 2: RC3 Data Collectors
RC3 data collectors collect data locally and can be synced to Elasticsearch:

1. **RC3 collectors write to their local pod:**
   - Path: `/workspace/credo-data-rc3/detections/*.json` (in each RC3 collector pod)

2. **Sync to Elasticsearch pod:**
   ```bash
   ./deploy/05-deploy-rc3-data-collectors.sh sync
   ```
   This copies all collected data from RC3 collectors to the Elasticsearch pod at `/workspace/credo-data/`

## Where Data Actually Lives

### Centralized Storage Location:

**Elasticsearch Pod (Primary Storage):**
   - Path: `/workspace/credo-data/detections/*.json`
   - Path: `/workspace/credo-data/pings/*.json`
   - **All data from all sources is stored here**
   - Data is also indexed into Elasticsearch for search/query
   - Index name: `credo-detections`
   - **Persistent until pod is deleted** (uses emptyDir volume)

### Temporary/Staging Locations:

1. **RC3 Collector Pods (Temporary):**
   - Path: `/workspace/credo-data-rc3/detections/*.json` (in each RC3 collector pod)
   - Data is collected here first, then synced to Elasticsearch pod
   - Use `./deploy/05-deploy-rc3-data-collectors.sh sync` to sync to Elasticsearch

2. **Local Directory (Temporary Only):**
   - `./credo-data-temp/` - **Should be empty or deleted after transfer**
   - This is NOT where data is stored long-term
   - It's just a temporary staging area (if used)

### Local Directory (Temporary Only):

- `./credo-data-temp/` - **Should be empty or deleted after transfer**
- This is NOT where data is stored long-term
- It's just a temporary staging area

## Important Note About `generate_sc25_affinity_toleration`

The function you're calling:
```bash
generate_sc25_affinity_toleration
```

**This function does NOT collect data.** It only generates YAML configuration for Kubernetes node affinity/toleration. It's used to ensure pods are scheduled on specific SC25 nodes.

To actually collect data, you need to run the full deployment script which calls `populate_elasticsearch()`.

## How to Access Data

### Option 1: Access Data Inside Pods

**View data in Elasticsearch pod (centralized storage):**
```bash
# Get Elasticsearch pod name
ES_POD=$(kubectl get pods -n cblee-credo -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}')

# List files
kubectl exec -n cblee-credo $ES_POD -- ls -lh /workspace/credo-data/detections/

# View a file
kubectl exec -n cblee-credo $ES_POD -- cat /workspace/credo-data/detections/export_*.json | head -50
```

**Query Elasticsearch:**
```bash
# Port forward Elasticsearch
kubectl port-forward -n cblee-credo svc/credo-elasticsearch-service 9200:9200

# Query (in another terminal)
curl -k -u elastic:<password> https://localhost:9200/credo-detections/_search?pretty
```

### Option 2: Copy Data to Local Machine (If Needed)

If you want to work with data locally:

```bash
# Get Elasticsearch pod name
ES_POD=$(kubectl get pods -n cblee-credo -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}')

# Copy FROM Elasticsearch pod TO local
kubectl cp cblee-credo/$ES_POD:/workspace/credo-data ./local-credo-data/

# Now you can explore locally
cd local-credo-data/detections
ls -lh
```

### Option 3: Use Data Processor

The `data-processor/credo-data-processor.py` script can process data from any directory:

```bash
# Process data from local directory
python3 data-processor/credo-data-processor.py --dir ./credo-data-temp --data-type detection

# Or process data from inside pod (requires copying first)
```

## Summary

| Location | Purpose | Persistent? |
|----------|---------|-------------|
| `/workspace/credo-data/` (inside Elasticsearch pod) | **Centralized storage - ALL data here** | ✅ Yes (until pod deleted, uses emptyDir) |
| `/workspace/credo-data-rc3/` (inside RC3 collector pods) | Temporary staging before sync | ⚠️ Temporary (sync to ES pod) |
| `./credo-data-temp/` (local) | Temporary staging | ❌ Should be deleted |

**Bottom line:** All data is now centralized in the Elasticsearch pod at `/workspace/credo-data/`. RC3 collectors write locally first, then sync to Elasticsearch using the `sync` command.

