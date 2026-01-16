#!/bin/bash

# Maximum Bandwidth Data Tsunami Configuration
# For SC25 final push - maximize all available bandwidth

set -euo pipefail

NAMESPACE="cblee-credo"
RC3_NODES=("rc3-sc-13" "rc3-sc-14" "rc3-sc-15")

# MAXIMUM bandwidth settings - DATA TSUNAMI CONFIGURATION
BATCH_SIZE=10000         # Maximum batch size
STREAM_INTERVAL=0.1      # Poll every 0.1 seconds (10 polls/second)
NUM_RECEIVE_STREAMS=20   # 20 receive streams per pod (60 total)

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

# Get Elasticsearch password
ES_PASSWORD=$(kubectl get secret credo-elasticsearch-es-elastic-user -n "$NAMESPACE" -o jsonpath='{.data.elastic}' | base64 -d)

# Find Caltech target pods
CALTECH_PODS=()
for pod in $(kubectl get pods -n "$NAMESPACE" -l app=credo-caltech-server -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
    CALTECH_PODS+=("$pod")
done
for pod in $(kubectl get pods -n "$NAMESPACE" -l app=caltech-fl-server -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
    CALTECH_PODS+=("$pod")
done
for pod in $(kubectl get pods -n "$NAMESPACE" -l app=caltech-fl-client -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
    CALTECH_PODS+=("$pod")
done

if [[ ${#CALTECH_PODS[@]} -eq 0 ]]; then
    log_warning "No Caltech pods found, will only do receive streaming"
    TARGET_POD=""
else
    TARGET_POD="${CALTECH_PODS[0]}"
    log_info "Found Caltech target pod: $TARGET_POD"
fi

log_info "=== MAXIMUM BANDWIDTH DATA TSUNAMI CONFIGURATION ==="
log_info "Receive streams: ${NUM_RECEIVE_STREAMS} per pod (from Elasticsearch)"
log_info "Transmit streams: ${NUM_TRANSMIT_STREAMS} per pod (to Caltech)"
log_info "Batch size: ${BATCH_SIZE} documents"
log_info "Polling interval: ${STREAM_INTERVAL} seconds"
log_info "Total streams per pod: $((NUM_RECEIVE_STREAMS + NUM_TRANSMIT_STREAMS))"
log_info "Total streams across 3 pods: $(((NUM_RECEIVE_STREAMS + NUM_TRANSMIT_STREAMS) * 3))"
echo ""

# Copy transmit script
cp ./deploy/transmit-flood.py /tmp/transmit_streamer.py 2>/dev/null || true

log_info "Setting up maximum bandwidth streaming on all RC3 pods..."

for node_name in "${RC3_NODES[@]}"; do
    node_num=$(echo "$node_name" | sed -E 's/.*rc3-sc-([0-9]+)\..*/\1/')
    pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-data-collector,node=rc3-sc-${node_num} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -z "$pod" ]]; then
        log_warning "Pod for $node_name not found, skipping..."
        continue
    fi
    
    log_info "Configuring $pod (RC3-SC-${node_num})..."
    
    # Copy scripts to pod
    kubectl cp ./deploy/high-bandwidth-streamer.py "$NAMESPACE/$pod:/tmp/" 2>/dev/null || true
    kubectl cp ./deploy/transmit-flood.py "$NAMESPACE/$pod:/tmp/transmit_streamer.py" 2>/dev/null || true
    
    # Start maximum receive streams
    kubectl exec -n "$NAMESPACE" "$pod" -- bash << SCRIPT_EOF
set -e

# Kill existing streams
pkill -f high-bandwidth-streamer || true
pkill -f transmit_streamer || true
sleep 1

ES_PASSWORD='${ES_PASSWORD}'

# Start RECEIVE streams (from Elasticsearch)
for i in \$(seq 1 ${NUM_RECEIVE_STREAMS}); do
    OUTPUT_DIR="/workspace/credo-data-rc3/detections/receive\${i}"
    mkdir -p "\$OUTPUT_DIR"
    
    nohup env ES_HOST=credo-elasticsearch-service ES_INDEX=credo-detections \
         ES_USER=elastic ES_PASSWORD="\$ES_PASSWORD" \
         BATCH_SIZE=${BATCH_SIZE} STREAM_INTERVAL=${STREAM_INTERVAL} \
         STREAM_ID="rx\${i}" OUTPUT_DIR="\$OUTPUT_DIR" \
         python3 /tmp/high-bandwidth-streamer.py > /tmp/receive_\${i}.log 2>&1 &
    
    echo \$! > /tmp/receive_\${i}.pid
done

echo "Started ${NUM_RECEIVE_STREAMS} receive streams"
echo "Note: Transmit streams will be started separately via transmit-coordinator.sh"
SCRIPT_EOF

    log_success "Maximum bandwidth configured on $pod"
done

log_success "=== DATA TSUNAMI ACTIVATED ==="
echo ""
echo "Configuration:"
echo "  - Receive streams: ${NUM_RECEIVE_STREAMS} per pod × 3 pods = $((NUM_RECEIVE_STREAMS * 3)) total"
if [[ -n "$TARGET_POD" ]]; then
    echo "  - Transmit streams: ${NUM_TRANSMIT_STREAMS} per pod × 3 pods = $((NUM_TRANSMIT_STREAMS * 3)) total"
fi
echo "  - Batch size: ${BATCH_SIZE} documents"
echo "  - Polling: Every ${STREAM_INTERVAL} seconds"
echo ""
echo "Total streams: $(((NUM_RECEIVE_STREAMS + (TARGET_POD ? NUM_TRANSMIT_STREAMS : 0)) * 3))"
echo ""
log_info "All streams running as persistent daemons!"
log_info "Check status: ./deploy/stream-from-elasticsearch.sh status"
log_info "Stop: ./deploy/stream-from-elasticsearch.sh stop"

