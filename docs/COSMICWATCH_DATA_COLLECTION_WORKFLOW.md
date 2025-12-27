# CosmicWatch Data Collection Workflow

This guide explains how to collect data from your CosmicWatch detector and post it persistently to Elasticsearch on NRP.

## Quick Start (Recommended)

### Step 1: Start Persistent Port-Forward

```bash
cd /Users/carlyn_oligo/git/credo-api-tools/scripts
./start_port_forward.sh
```

This script:
- Runs port-forward in the background using `nohup`
- Survives terminal closure (but will stop when laptop shuts down)
- Logs output to `~/.credo-port-forward.log`
- Saves PID to `~/.credo-port-forward.pid`

**To stop port-forward:**
```bash
./stop_port_forward.sh
```

### Step 2: Start Data Collection

```bash
cd /Users/carlyn_oligo/git/credo-api-tools/scripts
./start_cosmicwatch_collection.sh
```

This script:
- Checks if port-forward is running
- Sets up environment variables
- Tests Elasticsearch connection
- Starts the data collection script

When prompted:
- **Select port:** Enter the number for your CosmicWatch detector port
- **Enter detector ID:** Enter ID or press Enter for default (`cosmicwatch-001`)
- **Save to file too?** y/n (default: y)

## Manual Workflow (Alternative)

If you prefer to run commands manually:

### Terminal 1 - Port Forward (Background)

```bash
cd /Users/carlyn_oligo/git/credo-api-tools/scripts

# Option A: Using nohup (survives terminal closure)
nohup kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200 > ~/.credo-port-forward.log 2>&1 &

# Option B: Using screen (survives terminal closure and SSH disconnection)
screen -S port-forward
kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200
# Press Ctrl+A then D to detach
# To reattach: screen -r port-forward

# Option C: Using tmux (similar to screen)
tmux new-session -d -s port-forward 'kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200'
# To attach: tmux attach -t port-forward
```

### Terminal 2 - Data Collection

```bash
cd /Users/carlyn_oligo/git/credo-api-tools/CosmicWatch-Desktop-Muon-Detector-v3X/Data

export ES_HOST="https://localhost:9200"
export ES_USER="elastic"
export ES_PASS="RC0hJ6vR68c29mqq5O5Hu19u"
export ES_INDEX="credo-detections"
export ES_ENABLED="true"

python3 import_data_to_elasticsearch.py
```

### Terminal 3 - Inference Pipeline (Optional)

```bash
cd /Users/carlyn_oligo/git/credo-api-tools/scripts

export ES_HOST="https://localhost:9200"
export ES_USER="elastic"
export ES_PASS="RC0hJ6vR68c29mqq5O5Hu19u"
export ES_INDEX="credo-detections"

python3 real_time_inference.py
```

### Terminal 4 - Dashboard (Optional)

```bash
cd /Users/carlyn_oligo/git/credo-api-tools/scripts

export ES_HOST="https://localhost:9200"
export ES_USER="elastic"
export ES_PASS="RC0hJ6vR68c29mqq5O5Hu19u"
export ES_INDEX="credo-detections"

python3 visualization_dashboard.py
```

## Important Notes

### Port-Forward Persistence

**The port-forward will stop when:**
- You manually kill it
- Your laptop shuts down or goes to sleep
- The Kubernetes service becomes unavailable
- Network connection is lost

**To keep it running after laptop shutdown:**
- Use a remote server or VM that stays on
- Use `screen` or `tmux` on a persistent SSH session
- Consider deploying a Kubernetes service that connects directly (no port-forward needed)

### Verifying Data Collection

**Check if data is being posted:**
```bash
# Count documents from CosmicWatch
curl -k -u "elastic:RC0hJ6vR68c29mqq5O5Hu19u" \
  "https://localhost:9200/credo-detections/_count" \
  -H "Content-Type: application/json" \
  -d '{"query": {"term": {"source": "cosmicwatch-v3x"}}}'
```

**Check recent documents:**
```bash
curl -k -u "elastic:RC0hJ6vR68c29mqq5O5Hu19u" \
  "https://localhost:9200/credo-detections/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {"term": {"source": "cosmicwatch-v3x"}},
    "sort": [{"timestamp": {"order": "desc"}}],
    "size": 5
  }'
```

**View in Kibana:**
- URL: https://credo-kibana.nrp-nautilus.io
- Username: `elastic`
- Password: `RC0hJ6vR68c29mqq5O5Hu19u`
- Create index pattern: `credo-detections`
- Filter by: `source: cosmicwatch-v3x`

## Troubleshooting

### Port-Forward Not Working

1. **Check if port-forward is running:**
   ```bash
   ps aux | grep port-forward
   # Or check PID file
   cat ~/.credo-port-forward.pid
   ```

2. **Check port-forward logs:**
   ```bash
   tail -f ~/.credo-port-forward.log
   ```

3. **Restart port-forward:**
   ```bash
   ./stop_port_forward.sh
   ./start_port_forward.sh
   ```

### Elasticsearch Connection Failed

1. **Verify port-forward is active:**
   ```bash
   curl -k -u "elastic:RC0hJ6vR68c29mqq5O5Hu19u" "https://localhost:9200"
   ```

2. **Check Kubernetes service:**
   ```bash
   kubectl get svc -n cblee-credo | grep elasticsearch
   kubectl get pods -n cblee-credo | grep elasticsearch
   ```

3. **Verify namespace:**
   ```bash
   kubectl get namespace cblee-credo
   ```

### Data Not Appearing in Elasticsearch

1. **Check script output** - Look for error messages
2. **Verify ES_ENABLED is set to "true"**
3. **Check Elasticsearch index exists:**
   ```bash
   curl -k -u "elastic:RC0hJ6vR68c29mqq5O5Hu19u" \
     "https://localhost:9200/_cat/indices/credo-detections?v"
   ```
4. **Check for recent documents:**
   ```bash
   curl -k -u "elastic:RC0hJ6vR68c29mqq5O5Hu19u" \
     "https://localhost:9200/credo-detections/_search?size=1&sort=timestamp:desc"
   ```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ES_HOST` | `https://localhost:9200` | Elasticsearch host URL |
| `ES_USER` | `elastic` | Elasticsearch username |
| `ES_PASS` | (required) | Elasticsearch password |
| `ES_INDEX` | `credo-detections` | Elasticsearch index name |
| `ES_ENABLED` | `false` | Set to `true` to enable Elasticsearch upload |
| `CREDO_NAMESPACE` | `cblee-credo` | Kubernetes namespace |

## Next Steps

After data collection is running:
1. **Monitor data in Kibana** - Create visualizations and dashboards
2. **Run inference pipeline** - Add ML predictions to new events
3. **View dashboard** - See real-time statistics and visualizations

