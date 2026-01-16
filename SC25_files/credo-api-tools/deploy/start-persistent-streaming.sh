#!/bin/bash

# Start persistent high-bandwidth data streaming on RC3 pods
# This runs as daemon processes that survive session disconnects

set -euo pipefail

NAMESPACE="cblee-credo"
RC3_NODES=("rc3-sc-13" "rc3-sc-14" "rc3-sc-15")

# High bandwidth settings
BATCH_SIZE=2000
STREAM_INTERVAL=1
NUM_STREAMS=5

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get Elasticsearch password
ES_PASSWORD=$(kubectl get secret credo-elasticsearch-es-elastic-user -n "$NAMESPACE" -o jsonpath='{.data.elastic}' 2>/dev/null | base64 -d)

if [[ -z "$ES_PASSWORD" ]]; then
    log_error "Could not retrieve Elasticsearch password"
    exit 1
fi

log_info "Starting persistent high-bandwidth streaming on all RC3 pods..."
log_info "Configuration: Batch=${BATCH_SIZE}, Interval=${STREAM_INTERVAL}s, Streams=${NUM_STREAMS}/pod"

for node_name in "${RC3_NODES[@]}"; do
    node_num=$(echo "$node_name" | sed -E 's/.*rc3-sc-([0-9]+)\..*/\1/')
    pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-data-collector,node=rc3-sc-${node_num} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -z "$pod" ]]; then
        log_error "Pod for $node_name not found"
        continue
    fi
    
    log_info "Setting up persistent streaming on $pod..."
    
    # Create startup script in pod that runs independently
    kubectl exec -n "$NAMESPACE" "$pod" -- bash << SCRIPT_EOF
set -e

# Kill existing streams
pkill -f stream_from_es || true
sleep 2

# Create persistent streaming script
cat > /tmp/start_streams.sh << 'INNER_EOF'
#!/bin/bash
ES_HOST="credo-elasticsearch-service"
ES_PORT=9200
ES_INDEX="credo-detections"
ES_USER="elastic"
ES_PASSWORD="${ES_PASSWORD}"
BATCH_SIZE=${BATCH_SIZE}
STREAM_INTERVAL=${STREAM_INTERVAL}
NUM_STREAMS=${NUM_STREAMS}

# Create Python streaming script
cat > /tmp/stream_from_es.py << 'PYEOF'
import json
import os
import time
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
import sys

ES_HOST = os.environ.get('ES_HOST', 'credo-elasticsearch-service')
ES_PORT = int(os.environ.get('ES_PORT', 9200))
ES_INDEX = os.environ.get('ES_INDEX', 'credo-detections')
ES_USER = os.environ.get('ES_USER', 'elastic')
ES_PASSWORD = os.environ.get('ES_PASSWORD', '')
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', 2000))
STREAM_INTERVAL = float(os.environ.get('STREAM_INTERVAL', 1))
OUTPUT_DIR = os.environ.get('OUTPUT_DIR', '/workspace/credo-data-rc3/detections')
STREAM_ID = os.environ.get('STREAM_ID', '1')

os.makedirs(OUTPUT_DIR, exist_ok=True)

auth = HTTPBasicAuth(ES_USER, ES_PASSWORD) if ES_PASSWORD else None
es_url = f'https://{ES_HOST}:{ES_PORT}'

last_timestamp_file = os.path.join(OUTPUT_DIR, f'.last_timestamp_{STREAM_ID}')
last_timestamp = None

if os.path.exists(last_timestamp_file):
    try:
        with open(last_timestamp_file, 'r') as f:
            last_timestamp = int(f.read().strip())
    except:
        pass

batch_num = 0
total_docs = 0

print(f'Stream {STREAM_ID}: Starting (Batch size: {BATCH_SIZE}, Interval: {STREAM_INTERVAL}s)')

while True:
    try:
        query = {'size': BATCH_SIZE, 'sort': [{'timestamp': {'order': 'asc'}}]}
        if last_timestamp:
            query['query'] = {'range': {'timestamp': {'gt': last_timestamp}}}
        else:
            query['query'] = {'match_all': {}}
        
        response = requests.get(
            f'{es_url}/{ES_INDEX}/_search',
            json=query,
            auth=auth,
            verify=False,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f'Stream {STREAM_ID}: Error {response.status_code}')
            time.sleep(STREAM_INTERVAL)
            continue
        
        data = response.json()
        hits = data.get('hits', {}).get('hits', [])
        
        if not hits:
            time.sleep(STREAM_INTERVAL)
            continue
        
        detections = [hit['_source'] for hit in hits]
        max_timestamp = last_timestamp or 0
        
        for det in detections:
            ts = det.get('timestamp')
            if ts:
                if isinstance(ts, str):
                    try:
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        ts = int(dt.timestamp() * 1000)
                    except:
                        pass
                if isinstance(ts, (int, float)) and ts > max_timestamp:
                    max_timestamp = int(ts)
        
        batch_num += 1
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'stream{STREAM_ID}_batch_{batch_num}_{timestamp_str}.json'
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump({'detections': detections}, f)
        
        total_docs += len(detections)
        last_timestamp = max_timestamp
        
        with open(last_timestamp_file, 'w') as f:
            f.write(str(last_timestamp))
        
        if batch_num % 10 == 0:
            print(f'Stream {STREAM_ID}: Batch {batch_num}, Total docs: {total_docs}')
        
        time.sleep(STREAM_INTERVAL)
        
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f'Stream {STREAM_ID}: Error: {e}')
        time.sleep(STREAM_INTERVAL)
PYEOF

# Start multiple streams
for i in \$(seq 1 \$NUM_STREAMS); do
    OUTPUT_DIR="/workspace/credo-data-rc3/detections/stream\${i}"
    mkdir -p "\$OUTPUT_DIR"
    
    # Start stream with nohup and redirect to log
    nohup env ES_HOST="\$ES_HOST" ES_PORT="\$ES_PORT" ES_INDEX="\$ES_INDEX" \
         ES_USER="\$ES_USER" ES_PASSWORD="\$ES_PASSWORD" \
         BATCH_SIZE="\$BATCH_SIZE" STREAM_INTERVAL="\$STREAM_INTERVAL" \
         OUTPUT_DIR="\$OUTPUT_DIR" STREAM_ID="\${i}" \
         python3 /tmp/stream_from_es.py > /tmp/stream_\${i}.log 2>&1 &
    
    echo \$! > /tmp/stream_\${i}.pid
    echo "Stream \${i} started (PID: \$(cat /tmp/stream_\${i}.pid))"
done

echo "All \${NUM_STREAMS} streams started"
INNER_EOF

chmod +x /tmp/start_streams.sh

# Run startup script in background (survives disconnect)
nohup /tmp/start_streams.sh > /tmp/stream_startup.log 2>&1 &

echo "Startup script launched (will start all streams)"
SCRIPT_EOF

    log_success "Persistent streaming setup on $pod"
done

log_success "All persistent streaming processes started!"
echo ""
log_info "These processes run as daemons in the pods and will continue:"
log_info "  - Even if you close this terminal"
log_info "  - Even if you turn off your laptop"
log_info "  - Until the pods are restarted or you manually stop them"
echo ""
log_info "To check status: ./deploy/stream-from-elasticsearch.sh status"
log_info "To stop: ./deploy/stream-from-elasticsearch.sh stop"

