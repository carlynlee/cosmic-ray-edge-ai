#!/bin/bash

# Start high-bandwidth persistent streaming on all RC3 pods
# This will run continuously even after you disconnect

set -euo pipefail

NAMESPACE="cblee-credo"
RC3_NODES=("rc3-sc-13" "rc3-sc-14" "rc3-sc-15")
BATCH_SIZE=2000
STREAM_INTERVAL=1
NUM_STREAMS=5

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

# Get password
ES_PASSWORD=$(kubectl get secret credo-elasticsearch-es-elastic-user -n "$NAMESPACE" -o jsonpath='{.data.elastic}' | base64 -d)

log_info "Starting high-bandwidth streaming: ${NUM_STREAMS} streams/pod, batch=${BATCH_SIZE}, interval=${STREAM_INTERVAL}s"

for node_name in "${RC3_NODES[@]}"; do
    node_num=$(echo "$node_name" | sed -E 's/.*rc3-sc-([0-9]+)\..*/\1/')
    pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-data-collector,node=rc3-sc-${node_num} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -z "$pod" ]]; then
        # Try alternative lookup
        pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-data-collector -o jsonpath="{.items[?(@.spec.nodeName=='rc3-sc-${node_num}.sc25.nrp-nautilus.io')].metadata.name}" 2>/dev/null)
    fi
    
    if [[ -z "$pod" ]]; then
        echo "Pod for $node_name not found, skipping..."
        continue
    fi
    
    log_info "Setting up $pod..."
    
    # Copy Python script to pod
    kubectl cp ./deploy/high-bandwidth-streamer.py "$NAMESPACE/$pod:/tmp/high-bandwidth-streamer.py"
    
    # Start multiple streams
    kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "
        pkill -f high-bandwidth-streamer || true
        sleep 1
        
        for i in {1..${NUM_STREAMS}}; do
            OUTPUT_DIR=\"/workspace/credo-data-rc3/detections/stream\${i}\"
            mkdir -p \"\$OUTPUT_DIR\"
            
            nohup env ES_HOST=credo-elasticsearch-service ES_INDEX=credo-detections \
                 ES_USER=elastic ES_PASSWORD='${ES_PASSWORD}' \
                 BATCH_SIZE=${BATCH_SIZE} STREAM_INTERVAL=${STREAM_INTERVAL} \
                 STREAM_ID=\${i} OUTPUT_DIR=\"\$OUTPUT_DIR\" \
                 python3 /tmp/high-bandwidth-streamer.py > /tmp/stream_\${i}.log 2>&1 &
            
            echo \$! > /tmp/stream_\${i}.pid
        done
        
        echo 'All ${NUM_STREAMS} streams started on $pod'
    "
    
    log_success "Started ${NUM_STREAMS} streams on $pod"
done

log_success "All streaming started! Total: $((NUM_STREAMS * 3)) streams across 3 pods"
echo ""
echo "These processes run as daemons and will continue:"
echo "  ✓ Even if you close this terminal"
echo "  ✓ Even if you turn off your laptop"
echo "  ✓ Until pods restart or you stop them manually"
echo ""
echo "To check status: ./deploy/stream-from-elasticsearch.sh status"
echo "To stop: ./deploy/stream-from-elasticsearch.sh stop"

