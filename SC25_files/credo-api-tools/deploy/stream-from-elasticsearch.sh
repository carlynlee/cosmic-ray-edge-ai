#!/bin/bash

# Stream data from Elasticsearch instance at sphinx.sdstate.edu to RC3 pods
# This exercises the SC25 network links by continuously streaming data

set -euo pipefail

NAMESPACE="cblee-credo"
ES_HOST="${ES_HOST:-credo-elasticsearch-service}"
ES_PORT="${ES_PORT:-9200}"
ES_INDEX="${ES_INDEX:-credo-detections}"
ES_USER="${ES_USER:-elastic}"
ES_PASSWORD="${ES_PASSWORD:-}"
BATCH_SIZE="${BATCH_SIZE:-1000}"  # Increased for high bandwidth
STREAM_INTERVAL="${STREAM_INTERVAL:-1}"  # Poll every second for max bandwidth
NUM_STREAMS="${NUM_STREAMS:-3}"  # Multiple concurrent streams per pod

RC3_NODES=("rc3-sc-13" "rc3-sc-14" "rc3-sc-15")

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

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to get pod name for a node
get_pod_name() {
    local node_name=$1  # e.g., "rc3-sc-13" or just "13"
    local node_num
    
    # Extract node number if full name provided
    if [[ "$node_name" =~ rc3-sc-([0-9]+) ]]; then
        node_num="${BASH_REMATCH[1]}"
    else
        node_num="$node_name"
    fi
    
    # Try with the label selector
    local pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-data-collector,node=rc3-sc-${node_num} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -z "$pod" ]]; then
        # Fallback: find by node name
        pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-data-collector -o jsonpath="{.items[?(@.spec.nodeName=='rc3-sc-${node_num}.sc25.nrp-nautilus.io')].metadata.name}" 2>/dev/null)
    fi
    
    echo "$pod"
}

# Function to create streaming script in a pod
setup_streaming_script() {
    local pod=$1
    local node_num=$2
    
    log_info "Setting up streaming script in $pod..."
    
    # Create the streaming Python script
    kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "cat > /tmp/stream_from_es.py << PYEOF
import json
import os
import time
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth

ES_HOST = '${ES_HOST}'
ES_PORT = ${ES_PORT}
ES_INDEX = '${ES_INDEX}'
ES_USER = '${ES_USER}'
ES_PASSWORD = '${ES_PASSWORD}'
BATCH_SIZE = ${BATCH_SIZE}
STREAM_INTERVAL = ${STREAM_INTERVAL}
OUTPUT_DIR = '/workspace/credo-data-rc3/detections'

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Setup authentication
auth = None
if ES_USER and ES_USER != '' and ES_PASSWORD and ES_PASSWORD != '':
    auth = HTTPBasicAuth(ES_USER, ES_PASSWORD)
    print(f'Using authentication: user={ES_USER}')
else:
    print('No authentication configured')

# Use HTTPS for Kubernetes service (Elasticsearch uses TLS)
if ES_HOST.endswith('.svc.cluster.local') or ES_HOST.endswith('-service') or ES_PORT == 443:
    es_url = f'https://{ES_HOST}:{ES_PORT}'
else:
    es_url = f'http://{ES_HOST}:{ES_PORT}'

print(f'Connecting to Elasticsearch at {es_url}')
print(f'Index: {ES_INDEX}')
print(f'Output directory: {OUTPUT_DIR}')
print(f'Streaming every {STREAM_INTERVAL} seconds...')
print()

# Track last processed timestamp
last_timestamp_file = os.path.join(OUTPUT_DIR, '.last_timestamp')
last_timestamp = None

if os.path.exists(last_timestamp_file):
    try:
        with open(last_timestamp_file, 'r') as f:
            last_timestamp = int(f.read().strip())
            print(f'Resuming from timestamp: {last_timestamp}')
    except:
        pass

batch_num = 0
total_docs = 0

while True:
    try:
        # Build query
        query = {
            'size': BATCH_SIZE,
            'sort': [{'timestamp': {'order': 'asc'}}]
        }
        
        if last_timestamp:
            query['query'] = {
                'range': {
                    'timestamp': {
                        'gt': last_timestamp
                    }
                }
            }
        else:
            query['query'] = {'match_all': {}}
        
        # Query Elasticsearch
        search_url = f'{es_url}/{ES_INDEX}/_search'
        response = requests.get(
            search_url,
            json=query,
            auth=auth,
            verify=False,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f'Error querying Elasticsearch: {response.status_code}')
            print(response.text[:200])
            time.sleep(STREAM_INTERVAL)
            continue
        
        data = response.json()
        hits = data.get('hits', {}).get('hits', [])
        
        if not hits:
            print(f'No new documents found. Waiting {STREAM_INTERVAL} seconds...')
            time.sleep(STREAM_INTERVAL)
            continue
        
        # Extract documents
        detections = [hit['_source'] for hit in hits]
        max_timestamp = last_timestamp or 0
        
        for det in detections:
            ts = det.get('timestamp')
            if ts:
                if isinstance(ts, str):
                    # Try to parse ISO format
                    try:
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        ts = int(dt.timestamp() * 1000)
                    except:
                        pass
                if isinstance(ts, (int, float)) and ts > max_timestamp:
                    max_timestamp = int(ts)
        
        # Save batch to file
        batch_num += 1
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'stream_batch_{batch_num}_{timestamp_str}.json'
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        output_data = {'detections': detections}
        with open(filepath, 'w') as f:
            json.dump(output_data, f)
        
        total_docs += len(detections)
        last_timestamp = max_timestamp
        
        # Save last timestamp
        with open(last_timestamp_file, 'w') as f:
            f.write(str(last_timestamp))
        
        print(f'Batch {batch_num}: Saved {len(detections)} documents to {filename} (Total: {total_docs} docs)')
        
        time.sleep(STREAM_INTERVAL)
        
    except KeyboardInterrupt:
        print('\\nStreaming stopped by user')
        break
    except Exception as e:
        print(f'Error: {e}')
        time.sleep(STREAM_INTERVAL)
PYEOF
" || log_error "Failed to create streaming script in $pod"
    
    # Verify the script was created with correct settings
    log_info "Verifying authentication settings in $pod..."
    kubectl exec -n "$NAMESPACE" "$pod" -- python3 << PYVERIFY
import sys
sys.path.insert(0, '/tmp')
try:
    # Read the script and check for our variables
    with open('/tmp/stream_from_es.py', 'r') as f:
        content = f.read()
        if 'ES_USER' in content and 'ES_PASSWORD' in content:
            # Extract the values
            for line in content.split('\n'):
                if line.strip().startswith('ES_USER ='):
                    print(f"  {line.strip()}")
                if line.strip().startswith('ES_PASSWORD ='):
                    pwd_val = line.strip().split('=')[1].strip().strip("'\"")
                    if pwd_val:
                        print(f"  ES_PASSWORD = '***' (configured)")
                    else:
                        print(f"  ES_PASSWORD = '' (not set)")
except Exception as e:
    print(f"  Could not verify: {e}")
PYVERIFY
    
    # Install required Python packages
    log_info "Installing Python dependencies in $pod..."
    kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "
        pip3 install requests --quiet 2>/dev/null || \
        python3 -m pip install requests --quiet 2>/dev/null || \
        echo 'Could not install requests (may already be installed)'
    " || log_warning "Could not install requests in $pod"
    
    log_success "Streaming script setup complete in $pod"
}

# Function to start streaming on all RC3 pods
start_streaming() {
    log_info "Starting high-bandwidth data streaming from ${ES_HOST} to RC3 pods..."
    log_info "Configuration: Batch size=${BATCH_SIZE}, Interval=${STREAM_INTERVAL}s, Streams per pod=${NUM_STREAMS}"
    
    for node_name in "${RC3_NODES[@]}"; do
        local node_num=$(echo "$node_name" | sed -E 's/.*rc3-sc-([0-9]+)\..*/\1/')
        local pod=$(get_pod_name "$node_num")
        
        if [[ -z "$pod" ]]; then
            log_warning "Pod for node $node_name not found, skipping..."
            continue
        fi
        
        log_info "Setting up streaming on $pod (node: $node_name)..."
        setup_streaming_script "$pod" "$node_num"
        
        # Start multiple concurrent streams for maximum bandwidth
        log_info "Starting ${NUM_STREAMS} concurrent streaming processes on $pod..."
        kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "
            # Kill any existing streams
            pkill -f stream_from_es.py 2>/dev/null || true
            sleep 1
            
            # Start multiple concurrent streams
            for i in \$(seq 1 ${NUM_STREAMS}); do
                OUTPUT_DIR=\"/workspace/credo-data-rc3/detections/stream\${i}\"
                mkdir -p \$OUTPUT_DIR
                
                # Modify script for this stream instance
                sed \"s|OUTPUT_DIR = '/workspace/credo-data-rc3/detections'|OUTPUT_DIR = '\$OUTPUT_DIR'|g\" /tmp/stream_from_es.py > /tmp/stream_from_es_\${i}.py
                sed -i \"s|stream_batch_|stream\${i}_batch_|g\" /tmp/stream_from_es_\${i}.py
                
                # Start stream in background with nohup (survives session disconnect)
                nohup python3 /tmp/stream_from_es_\${i}.py > /tmp/stream_elasticsearch_\${i}.log 2>&1 &
                echo \$! > /tmp/stream_elasticsearch_\${i}.pid
                echo \"Stream \${i} started (PID: \$(cat /tmp/stream_elasticsearch_\${i}.pid))\"
            done
            
            # Save all PIDs to main file
            cat /tmp/stream_elasticsearch_*.pid > /tmp/stream_elasticsearch.pid 2>/dev/null || true
            echo 'All streams started'
        " || log_warning "Failed to start streaming on $pod"
        
        log_success "Streaming started on $pod (${NUM_STREAMS} concurrent streams)"
    done
    
    log_success "All streaming processes started!"
    echo ""
    log_info "These processes run as daemons in the pods and will continue even if you disconnect."
    log_info "To check status, run: $0 status"
    log_info "To stop streaming, run: $0 stop"
}

# Function to stop streaming
stop_streaming() {
    log_info "Stopping data streaming on all RC3 pods..."
    
    for node_name in "${RC3_NODES[@]}"; do
        local node_num=$(echo "$node_name" | sed -E 's/.*rc3-sc-([0-9]+)\..*/\1/')
        local pod=$(get_pod_name "$node_num")
        
        if [[ -z "$pod" ]]; then
            continue
        fi
        
        log_info "Stopping all streaming processes on $pod..."
        kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "
            # Kill all stream processes
            pkill -f stream_from_es.py 2>/dev/null || true
            # Remove PID files
            rm -f /tmp/stream_elasticsearch*.pid 2>/dev/null || true
            echo 'All streaming processes stopped'
        " || log_warning "Could not stop streaming on $pod"
    done
    
    log_success "All streaming processes stopped"
}

# Function to show streaming status
show_status() {
    log_info "Streaming Status from ${ES_HOST}:"
    echo ""
    kubectl get pods -n "$NAMESPACE" -l app=credo-data-collector -o wide
    echo ""
    
    for node_name in "${RC3_NODES[@]}"; do
        local node_num=$(echo "$node_name" | sed -E 's/.*rc3-sc-([0-9]+)\..*/\1/')
        local pod=$(get_pod_name "$node_num")
        
        if [[ -z "$pod" ]]; then
            continue
        fi
        
        echo ""
        log_info "RC3-SC-${node_num} ($pod):"
        
        # Check how many streams are running
        local stream_count=$(kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "pgrep -f stream_from_es.py | wc -l" 2>/dev/null || echo "0")
        if [[ "$stream_count" -gt 0 ]]; then
            echo "  Status: Running ($stream_count concurrent streams)"
            local pids=$(kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "pgrep -f stream_from_es.py | tr '\n' ','" 2>/dev/null || echo "")
            echo "  PIDs: ${pids%,}"
        else
            echo "  Status: Not running"
        fi
        
        # Show latest logs from all streams
        echo "  Latest logs:"
        for i in $(seq 1 ${NUM_STREAMS}); do
            local log_file="/tmp/stream_elasticsearch_${i}.log"
            if kubectl exec -n "$NAMESPACE" "$pod" -- test -f "$log_file" 2>/dev/null; then
                echo "    Stream ${i}:"
                kubectl exec -n "$NAMESPACE" "$pod" -- tail -2 "$log_file" 2>/dev/null | sed 's/^/      /' || echo "      No recent activity"
            fi
        done
        
        # Show total files and size
        local total_files=$(kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "find /workspace/credo-data-rc3/detections -name 'stream*_batch_*.json' 2>/dev/null | wc -l" 2>/dev/null || echo "0")
        local total_size=$(kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "du -sh /workspace/credo-data-rc3/detections/stream* 2>/dev/null | awk '{sum+=\$1} END {print sum}'" 2>/dev/null || kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "du -ch /workspace/credo-data-rc3/detections/stream* 2>/dev/null | tail -1 | cut -f1" 2>/dev/null || echo "0")
        echo "  Total files: $total_files"
        echo "  Total size: $total_size"
    done
}

# Function to auto-retrieve Elasticsearch password
get_es_password() {
    if [[ -z "$ES_PASSWORD" ]]; then
        log_info "Retrieving Elasticsearch password from Kubernetes secret..."
        ES_PASSWORD=$(kubectl get secret credo-elasticsearch-es-elastic-user -n "$NAMESPACE" -o jsonpath='{.data.elastic}' 2>/dev/null | base64 -d)
        if [[ -n "$ES_PASSWORD" ]]; then
            log_success "Password retrieved from secret"
            export ES_PASSWORD
        else
            log_warning "Could not retrieve password from secret. You may need to set ES_PASSWORD manually."
        fi
    fi
}

# Main function
main() {
    case "${1:-help}" in
        "start")
            get_es_password
            start_streaming
            ;;
        "stop")
            stop_streaming
            ;;
        "status")
            show_status
            ;;
        "help"|"-h"|"--help")
            cat << EOF
Stream data from Elasticsearch at sphinx.sdstate.edu to RC3 pods

Usage: $0 [command] [options]

Commands:
    start     Start streaming data from Elasticsearch to all RC3 pods
    stop      Stop streaming on all RC3 pods
    status    Show streaming status
    help      Show this help message

Environment Variables:
    ES_HOST         Elasticsearch host (default: sphinx.sdstate.edu)
    ES_PORT         Elasticsearch port (default: 9200)
    ES_INDEX        Elasticsearch index (default: credo-detections)
    ES_USER         Elasticsearch username (default: elastic)
    ES_PASSWORD     Elasticsearch password (required - auto-retrieved from secret)
    BATCH_SIZE      Number of documents per batch (default: 1000 for high bandwidth)
    STREAM_INTERVAL Seconds between batches (default: 1 for max bandwidth)
    NUM_STREAMS     Number of concurrent streams per pod (default: 3)

Examples:
    $0 start                                    # Start streaming with defaults
    ES_HOST=sphinx.sdstate.edu $0 start        # Explicit host
    ES_USER=elastic ES_PASSWORD=pass $0 start  # With authentication
    BATCH_SIZE=500 STREAM_INTERVAL=10 $0 start # Custom batch settings
    $0 status                                   # Check status
    $0 stop                                     # Stop streaming

This script exercises the SC25 network links by continuously streaming
data from the remote Elasticsearch instance to the RC3 pods.
EOF
            ;;
        *)
            log_error "Unknown command: $1"
            log_info "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

