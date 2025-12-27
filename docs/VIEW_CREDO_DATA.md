# Viewing CREDO.science Data in Elasticsearch

This guide shows you how to view and query data from `api.credo.science` that has been imported into your Elasticsearch instance.

## Current Status

**Note:** As of the last check, no CREDO-science data has been imported yet (0 documents). The data streamer is deployed but exports are taking longer than expected. Once data starts flowing, use the methods below to view it.

## Method 1: Kibana Dashboard (Recommended)

### Access Kibana

1. **Navigate to:** https://credo-kibana.nrp-nautilus.io
2. **Login:**
   - Username: `elastic`
   - Password: Get from Kubernetes secret:
     ```bash
     kubectl get secret credo-elasticsearch-es-elastic-user -n cblee-credo -o jsonpath='{.data.elastic}' | base64 -d
     ```

### View CREDO-science Data in Kibana

#### Step 1: Create/Verify Index Pattern

1. Go to **Stack Management** → **Index Patterns**
2. If `credo-detections*` doesn't exist, create it:
   - Click **Create index pattern**
   - Pattern: `credo-detections*`
   - Select **timestamp** as the time field
   - Click **Create index pattern**

#### Step 2: Create Visualization for CREDO-science Data

1. Go to **Visualize Library** → **Create visualization**
2. Choose **Line** chart
3. Select index pattern: `credo-detections*`
4. Configure:
   - **X-axis:** Date Histogram on `timestamp` (1 hour interval)
   - **Y-axis:** Count
   - **Filter:** `source.keyword: credo-science` (to show only CREDO API data)
5. Save as: "CREDO API Events Over Time"

#### Step 3: Create Dashboard

1. Go to **Dashboard** → **Create dashboard**
2. Add the visualization you created
3. Add filters:
   - `source.keyword: credo-science`
4. Save as: "CREDO API Data Dashboard"

### Quick Search in Kibana

1. Go to **Discover**
2. Select index pattern: `credo-detections*`
3. Add filter: `source.keyword: credo-science`
4. View and explore the data

## Method 2: Direct Elasticsearch Queries

### Setup Port Forward

```bash
# Forward Elasticsearch port
kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200

# Get password
ES_PASS=$(kubectl get secret credo-elasticsearch-es-elastic-user -n cblee-credo -o jsonpath='{.data.elastic}' | base64 -d)
```

### Query Examples

#### 1. Count CREDO-science Documents

```bash
curl -k -u "elastic:$ES_PASS" \
  "https://localhost:9200/credo-detections/_count" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "term": {
        "source.keyword": "credo-science"
      }
    }
  }'
```

#### 2. Get Recent CREDO-science Documents

```bash
curl -k -u "elastic:$ES_PASS" \
  "https://localhost:9200/credo-detections/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "size": 10,
    "query": {
      "term": {
        "source.keyword": "credo-science"
      }
    },
    "sort": [
      {
        "timestamp": {
          "order": "desc"
        }
      }
    ]
  }'
```

#### 3. Count by Time Range

```bash
curl -k -u "elastic:$ES_PASS" \
  "https://localhost:9200/credo-detections/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "size": 0,
    "query": {
      "bool": {
        "must": [
          {
            "term": {
              "source.keyword": "credo-science"
            }
          },
          {
            "range": {
              "timestamp": {
                "gte": "2025-11-13T00:00:00Z",
                "lte": "2025-11-13T23:59:59Z"
              }
            }
          }
        ]
      }
    },
    "aggs": {
      "events_over_time": {
        "date_histogram": {
          "field": "timestamp",
          "calendar_interval": "1h"
        }
      }
    }
  }'
```

#### 4. Get Document Structure

```bash
curl -k -u "elastic:$ES_PASS" \
  "https://localhost:9200/credo-detections/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "size": 1,
    "query": {
      "term": {
        "source.keyword": "credo-science"
      }
    }
  }' | python3 -m json.tool
```

## Method 3: Python Script

Create a simple Python script to query and display data:

```python
#!/usr/bin/env python3
import requests
import json
import subprocess
from datetime import datetime

# Get Elasticsearch password
result = subprocess.run(
    ['kubectl', 'get', 'secret', 'credo-elasticsearch-es-elastic-user',
     '-n', 'cblee-credo', '-o', 'jsonpath={.data.elastic}'],
    capture_output=True, text=True
)
es_pass = subprocess.run(
    ['base64', '-d'],
    input=result.stdout,
    capture_output=True, text=True
).stdout.strip()

# Query Elasticsearch
url = "https://localhost:9200/credo-detections/_search"
query = {
    "size": 10,
    "query": {
        "term": {
            "source.keyword": "credo-science"
        }
    },
    "sort": [{"timestamp": {"order": "desc"}}]
}

response = requests.get(
    url,
    json=query,
    auth=("elastic", es_pass),
    verify=False
)

if response.ok:
    data = response.json()
    hits = data.get("hits", {}).get("hits", [])
    print(f"Found {len(hits)} CREDO-science documents")
    for hit in hits:
        source = hit.get("_source", {})
        print(f"\nTimestamp: {source.get('timestamp')}")
        print(f"Source: {source.get('source')}")
        print(f"Data: {json.dumps(source, indent=2)[:200]}...")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

## Method 4: Check Import Status

### Check Streamer Status

```bash
# View streamer logs
kubectl logs -f deployment/credo-stream -n cblee-credo

# Check state file
kubectl exec deployment/credo-stream -n cblee-credo -- \
  cat /workspace/credo_stream_state.json
```

### Monitor Data Import

```bash
# Watch document count increase
watch -n 5 'curl -s -k -u "elastic:$(kubectl get secret credo-elasticsearch-es-elastic-user -n cblee-credo -o jsonpath='{.data.elastic}' | base64 -d)" "https://localhost:9200/credo-detections/_count" -H "Content-Type: application/json" -d "{\"query\": {\"term\": {\"source.keyword\": \"credo-science\"}}}" | python3 -c "import sys, json; print(json.load(sys.stdin)[\"count\"])"'
```

## Expected Data Structure

CREDO-science documents should have this structure:

```json
{
  "source": "credo-science",
  "timestamp": "2025-11-13T12:00:00Z",
  "time_received": 1763011200000,
  "location": {
    "lat": 50.0614,
    "lon": 19.9366
  },
  "device_id": "...",
  "detection_data": {
    // CREDO detection fields
  }
}
```

## Troubleshooting

### No Data Appearing

1. **Check streamer status:**
   ```bash
   kubectl get pods -l app=credo-stream -n cblee-credo
   kubectl logs deployment/credo-stream -n cblee-credo
   ```

2. **Check if exports are completing:**
   - Look for "✓ Export ready" in logs
   - Look for "✓ Imported X detections" messages

3. **Verify Elasticsearch connection:**
   ```bash
   kubectl exec deployment/credo-stream -n cblee-credo -- \
     python3 -c "import requests; r = requests.get('https://credo-elasticsearch-es-http:9200', verify=False, auth=('elastic', '...')); print(r.status_code)"
   ```

### Data Not Filtering Correctly

- Ensure you're using `source.keyword` (keyword field) not `source` (text field)
- In Kibana, use the exact value: `credo-science`

## Next Steps

Once data starts flowing:
1. Set up Kibana dashboards for visualization
2. Create alerts for data flow issues
3. Compare CREDO-science data with CosmicWatch data
4. Use for federated learning experiments




