#!/bin/bash

# Transmit coordinator - runs on host to flood transmit bandwidth
# Continuously copies data from RC3 pods to Caltech pods

set -euo pipefail

NAMESPACE="cblee-credo"
RC3_NODES=("rc3-sc-13" "rc3-sc-14" "rc3-sc-15")
TRANSMIT_INTERVAL=0.1  # Maximum frequency
NUM_TRANSMIT_STREAMS=10  # 10 parallel transmit streams per RC3 pod

# Find Caltech target pod
TARGET_POD=$(kubectl get pods -n "$NAMESPACE" -l app=credo-caltech-server -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [[ -z "$TARGET_POD" ]]; then
    TARGET_POD=$(kubectl get pods -n "$NAMESPACE" -l app=caltech-fl-server -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
fi

if [[ -z "$TARGET_POD" ]]; then
    echo "No Caltech target pod found"
    exit 1
fi

echo "Target pod: $TARGET_POD"
echo "Starting transmit flood coordinator..."

# Setup target directory
kubectl exec -n "$NAMESPACE" "$TARGET_POD" -- mkdir -p /tmp/tsunami_data 2>/dev/null || true

# Function to transmit from one RC3 pod (single stream)
transmit_from_pod() {
    local pod=$1
    local stream_id=$2
    
    local count=0
    while true; do
        # Find files to send (get more files for higher bandwidth)
        files=$(kubectl exec -n "$NAMESPACE" "$pod" -- find /workspace/credo-data-rc3/detections -name "*.json" -type f 2>/dev/null | head -50)
        
        for file in $files; do
            if [[ -n "$file" ]]; then
                filename=$(basename "$file")
                target_path="/tmp/tsunami_data/stream${stream_id}_${filename}_$(date +%s%N).json"
                
                # Copy file (non-blocking, continue on errors)
                kubectl cp "$NAMESPACE/$pod:$file" "$NAMESPACE/$TARGET_POD:$target_path" 2>/dev/null &
                
                count=$((count + 1))
                if [[ $((count % 100)) -eq 0 ]]; then
                    echo "Stream ${stream_id}: Transmitted ${count} files" >&2
                fi
            fi
        done
        
        sleep "$TRANSMIT_INTERVAL"
    done
}

# Start multiple transmit processes for each RC3 pod (maximum bandwidth)
for i in "${!RC3_NODES[@]}"; do
    node_name="${RC3_NODES[$i]}"
    node_num=$(echo "$node_name" | sed -E 's/.*rc3-sc-([0-9]+)\..*/\1/')
    pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-data-collector,node=rc3-sc-${node_num} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -n "$pod" ]]; then
        echo "Starting ${NUM_TRANSMIT_STREAMS} transmit streams from $pod..."
        for stream in $(seq 1 ${NUM_TRANSMIT_STREAMS}); do
            transmit_from_pod "$pod" "${node_num}_${stream}" &
            echo $! > /tmp/transmit_${node_num}_${stream}.pid
        done
    fi
done

total_streams=$(ls /tmp/transmit_*.pid 2>/dev/null | wc -l | tr -d ' ')
echo "All transmit coordinators started: ${total_streams} streams"
echo "PIDs: $(cat /tmp/transmit_*.pid 2>/dev/null | tr '\n' ' ')"
echo ""
echo "To stop: ./deploy/stop-tsunami.sh or pkill -f transmit-coordinator.sh"

# Keep script running
wait

