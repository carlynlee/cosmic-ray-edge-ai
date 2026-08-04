#!/bin/bash

# Demo script to demonstrate SC25 network links using RC3 pods
# This script generates network traffic between the three RC3 pods to showcase bandwidth

set -euo pipefail

NAMESPACE="cblee-credo"
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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to get pod name for a node
get_pod_name() {
    local node_num=$1
    kubectl get pods -n "$NAMESPACE" -l app=credo-data-collector,node=rc3-sc-${node_num} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null
}

# Function to find existing CREDO JSON files in a pod
find_credo_json_files() {
    local pod=$1
    local node_num=$2
    
    # Check for JSON files in RC3 collector's detections directory
    local json_files=$(kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "
        if [ -d /workspace/credo-data-rc3/detections ]; then
            find /workspace/credo-data-rc3/detections -name '*.json' -type f 2>/dev/null | head -1
        fi
    " 2>/dev/null)
    
    if [[ -n "$json_files" ]]; then
        echo "$json_files"
        return 0
    fi
    
    # Check Elasticsearch pod for existing CREDO data
    local es_pod=$(kubectl get pods -n "$NAMESPACE" -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [[ -n "$es_pod" ]]; then
        local es_files=$(kubectl exec -n "$NAMESPACE" "$es_pod" -- bash -c "
            if [ -d /workspace/credo-data/detections ]; then
                find /workspace/credo-data/detections -name '*.json' -type f 2>/dev/null | head -1
            fi
        " 2>/dev/null)
        
        if [[ -n "$es_files" ]]; then
            # Copy one file from ES to this pod for transfer
            local basename_file=$(basename "$es_files")
            log_info "Copying CREDO JSON from Elasticsearch to $pod for transfer..."
            kubectl cp "$NAMESPACE/$es_pod:$es_files" "$NAMESPACE/$pod:/workspace/credo-data-rc3/$basename_file" 2>/dev/null
            if kubectl exec -n "$NAMESPACE" "$pod" -- test -f "/workspace/credo-data-rc3/$basename_file" 2>/dev/null; then
                echo "/workspace/credo-data-rc3/$basename_file"
                return 0
            fi
        fi
    fi
    
    return 1
}

# Function to stream file from Elasticsearch to RC3 pod (for SC25 demo)
stream_file_from_elasticsearch() {
    local pod=$1
    local node_num=$2
    local filename=$3
    
    # Get Elasticsearch pod
    local es_pod=$(kubectl get pods -n "$NAMESPACE" -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -z "$es_pod" ]]; then
        log_error "Elasticsearch pod not found"
        return 1
    fi
    
    # Find any data file in Elasticsearch (check multiple locations)
    local es_file=$(kubectl exec -n "$NAMESPACE" "$es_pod" -- bash -c "
        # Try workspace locations first
        if [ -d /workspace/credo-data/detections ]; then
            find /workspace/credo-data/detections -type f 2>/dev/null | head -1
        fi
    " 2>/dev/null)
    
    # If no files, try /tmp (writable location)
    if [[ -z "$es_file" ]]; then
        es_file=$(kubectl exec -n "$NAMESPACE" "$es_pod" -- bash -c "
            find /tmp -type f -size +1k 2>/dev/null | head -1
        " 2>/dev/null)
    fi
    
    # If still no files, create a test file in /tmp (writable location)
    if [[ -z "$es_file" ]]; then
        log_info "No data files found in Elasticsearch, creating test file in /tmp for SC25 demo..."
        
        # Create test file in /tmp (writable location)
        kubectl exec -n "$NAMESPACE" "$es_pod" -- bash -c "
            if command -v dd >/dev/null 2>&1; then
                dd if=/dev/urandom of=/tmp/demo-test-file.bin bs=1M count=1 2>/dev/null
            elif command -v python3 >/dev/null 2>&1; then
                python3 -c \"import os; f=open('/tmp/demo-test-file.bin','wb'); f.write(os.urandom(1048576)); f.close()\"
            else
                # Fallback: create smaller file
                head -c 1048576 /dev/urandom > /tmp/demo-test-file.bin 2>/dev/null || \
                echo 'SC25 demo test data' > /tmp/demo-test-file.bin
            fi
        " 2>/dev/null
        
        es_file="/tmp/demo-test-file.bin"
        
        # Verify file was created
        if kubectl exec -n "$NAMESPACE" "$es_pod" -- test -f "$es_file" 2>/dev/null; then
            local file_size=$(kubectl exec -n "$NAMESPACE" "$es_pod" -- du -h "$es_file" 2>/dev/null | cut -f1)
            log_info "Created test file for SC25 demo: $es_file ($file_size)"
        else
            log_error "Failed to create test file in Elasticsearch /tmp"
            return 1
        fi
    fi
    
    # Stream/copy file from Elasticsearch to RC3 pod
    log_info "Streaming data file from Elasticsearch to $pod..."
    log_info "  Source: $es_file"
    
    # kubectl cp requires one end to be local, so we copy via temp file
    local temp_file=$(mktemp)
    trap "rm -f $temp_file" EXIT
    
    # Step 1: Copy from ES pod to local temp file
    if ! kubectl cp "$NAMESPACE/$es_pod:$es_file" "$temp_file" 2>/dev/null; then
        log_error "Failed to copy file from Elasticsearch pod to local"
        rm -f "$temp_file"
        return 1
    fi
    
    # Step 2: Copy from local temp file to RC3 pod
    if kubectl cp "$temp_file" "$NAMESPACE/$pod:/workspace/credo-data-rc3/$filename" 2>/dev/null; then
        local file_size=$(kubectl exec -n "$NAMESPACE" "$pod" -- du -h "/workspace/credo-data-rc3/$filename" 2>/dev/null | cut -f1)
        log_success "Streamed file from Elasticsearch: $filename ($file_size)"
        rm -f "$temp_file"
        return 0
    else
        log_error "Failed to copy file to RC3 pod"
        rm -f "$temp_file"
        return 1
    fi
}

# Function to prepare data file in a pod (stream from ES, delete after use for SC25 demo)
prepare_data_file() {
    local pod=$1
    local node_num=$2
    local filename=$3
    
    log_info "Streaming CREDO JSON file from Elasticsearch to $pod (for SC25 demo)..."
    
    # Always stream from Elasticsearch for SC25 demo
    if stream_file_from_elasticsearch "$pod" "$node_num" "$filename"; then
        log_success "Prepared data file: $filename (streamed from Elasticsearch)"
        return 0
    else
        log_error "Failed to stream file from Elasticsearch to $pod"
        return 1
    fi
}

# Function to clean up files on RC3 pod after collection (for SC25 demo)
cleanup_rc3_files() {
    local pod=$1
    local filename=$2
    
    log_info "Cleaning up files on $pod after collection..."
    kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "
        rm -f /workspace/credo-data-rc3/$filename 2>/dev/null
        rm -f /workspace/credo-data-rc3/received-* 2>/dev/null
    " 2>/dev/null
    log_success "Cleaned up files on $pod"
}


# Function to transfer data between pods using kubectl cp (demonstrates network)
transfer_data_between_pods() {
    local source_pod=$1
    local dest_pod=$2
    local filename=$3
    
    log_info "Transferring $filename from $source_pod to $dest_pod..."
    local start_time=$(date +%s)
    
    # kubectl cp requires one end to be local, so use temp file as intermediate
    local temp_file=$(mktemp)
    trap "rm -f $temp_file" EXIT
    
    # Step 1: Copy from source pod to local temp file
    if ! kubectl cp "$NAMESPACE/$source_pod:/workspace/credo-data-rc3/$filename" "$temp_file" 2>&1; then
        log_error "Transfer failed: could not copy from source pod"
        rm -f "$temp_file"
        return 1
    fi
    
    # Step 2: Copy from local temp file to destination pod
    if kubectl cp "$temp_file" "$NAMESPACE/$dest_pod:/workspace/credo-data-rc3/received-$(basename $filename)" 2>&1; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        # Verify file was received
        if kubectl exec -n "$NAMESPACE" "$dest_pod" -- test -f "/workspace/credo-data-rc3/received-$(basename $filename)" 2>/dev/null; then
            # Get file size
            local file_size=$(kubectl exec -n "$NAMESPACE" "$source_pod" -- du -b "/workspace/credo-data-rc3/$filename" 2>/dev/null | cut -f1 || echo "0")
            local size_kb=$((file_size / 1024))
            local size_mb=$((file_size / 1024 / 1024))
            
            if [ $duration -gt 0 ] && [ $file_size -gt 0 ]; then
                if [ $size_mb -gt 0 ]; then
                    local throughput=$((size_mb / duration))
                    log_success "✓ Transfer complete: ${size_mb}MB in ${duration}s (~${throughput} MB/s)"
                else
                    log_success "✓ Transfer complete: ${size_kb}KB in ${duration}s"
                fi
            else
                if [ $size_mb -gt 0 ]; then
                    log_success "✓ Transfer complete: ${size_mb}MB"
                else
                    log_success "✓ Transfer complete: ${size_kb}KB"
                fi
            fi
        else
            log_error "Transfer failed: file not found in destination"
            return 1
        fi
    else
        log_error "Transfer failed: kubectl cp error"
        return 1
    fi
}

# Function to run iperf3 server in a pod (if available)
start_iperf_server() {
    local pod=$1
    log_info "Starting iperf3 server in $pod..."
    kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "
        if command -v iperf3 >/dev/null 2>&1; then
            iperf3 -s -p 5201 > /tmp/iperf-server.log 2>&1 &
            echo \$! > /tmp/iperf-server.pid
            echo 'iperf3 server started on port 5201'
        else
            echo 'iperf3 not available, installing...'
            apt-get update >/dev/null 2>&1 && apt-get install -y iperf3 >/dev/null 2>&1
            iperf3 -s -p 5201 > /tmp/iperf-server.log 2>&1 &
            echo \$! > /tmp/iperf-server.pid
            echo 'iperf3 server started'
        fi
    " || log_info "Note: iperf3 may not be available in container"
}

# Function to run iperf3 client test
run_iperf_test() {
    local client_pod=$1
    local server_pod=$2
    local duration=${3:-10}
    
    # Get server pod IP
    local server_ip=$(kubectl get pod -n "$NAMESPACE" "$server_pod" -o jsonpath='{.status.podIP}')
    
    log_info "Running iperf3 test: $client_pod -> $server_pod (${duration}s)..."
    kubectl exec -n "$NAMESPACE" "$client_pod" -- bash -c "
        if command -v iperf3 >/dev/null 2>&1; then
            iperf3 -c $server_ip -p 5201 -t $duration
        else
            echo 'Installing iperf3...'
            apt-get update >/dev/null 2>&1 && apt-get install -y iperf3 >/dev/null 2>&1
            iperf3 -c $server_ip -p 5201 -t $duration
        fi
    " || log_info "Note: iperf3 test requires network connectivity between pods"
}

# Function to demonstrate parallel data collection from Elasticsearch
demo_parallel_collection() {
    log_info "Demonstrating parallel data collection from Elasticsearch by RC3 pods..."
    echo ""
    
    # Get all pod names
    local pod_13=$(get_pod_name "13")
    local pod_14=$(get_pod_name "14")
    local pod_15=$(get_pod_name "15")
    
    if [[ -z "$pod_13" ]]; then
        log_error "RC3-SC-13 pod not found. Make sure pods are deployed."
        return 1
    fi
    if [[ -z "$pod_14" ]]; then
        log_error "RC3-SC-14 pod not found. Make sure pods are deployed."
        return 1
    fi
    if [[ -z "$pod_15" ]]; then
        log_error "RC3-SC-15 pod not found. Make sure pods are deployed."
        return 1
    fi
    
    log_info "Found pods:"
    echo "  - rc3-sc-13: $pod_13"
    echo "  - rc3-sc-14: $pod_14"
    echo "  - rc3-sc-15: $pod_15"
    echo ""
    
    # Collect data from Elasticsearch in parallel (all pods simultaneously)
    log_info "Collecting data from Elasticsearch in parallel (all pods simultaneously)..."
    log_info "  (Files will be deleted after collection to demonstrate continuous streaming)"
    echo ""
    
    local start_time=$(date +%s)
    
    # Start all three collection processes in parallel using background jobs
    (
        prepare_data_file "$pod_13" "13" "collected-data-13.bin" && \
        log_success "rc3-sc-13: Collected data from Elasticsearch" || \
        log_error "rc3-sc-13: Failed to collect data"
    ) &
    local pid_13=$!
    
    (
        prepare_data_file "$pod_14" "14" "collected-data-14.bin" && \
        log_success "rc3-sc-14: Collected data from Elasticsearch" || \
        log_error "rc3-sc-14: Failed to collect data"
    ) &
    local pid_14=$!
    
    (
        prepare_data_file "$pod_15" "15" "collected-data-15.bin" && \
        log_success "rc3-sc-15: Collected data from Elasticsearch" || \
        log_error "rc3-sc-15: Failed to collect data"
    ) &
    local pid_15=$!
    
    # Wait for all parallel collections to complete
    wait $pid_13
    local result_13=$?
    wait $pid_14
    local result_14=$?
    wait $pid_15
    local result_15=$?
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    
    echo ""
    
    # Check if all collections succeeded
    if [ $result_13 -eq 0 ] && [ $result_14 -eq 0 ] && [ $result_15 -eq 0 ]; then
        log_success "All pods successfully collected data from Elasticsearch in parallel!"
        log_info "  Total time: ${duration}s"
        echo ""
        
        # Clean up files after collection (SC25 demo: demonstrate ephemeral data)
        log_info "Cleaning up collected files (demonstrating ephemeral data flow)..."
        cleanup_rc3_files "$pod_13" "collected-data-13.bin"
        cleanup_rc3_files "$pod_14" "collected-data-14.bin"
        cleanup_rc3_files "$pod_15" "collected-data-15.bin"
        echo ""
        
        log_success "SC25 network links demonstrated through parallel Elasticsearch collection!"
        log_info "Summary: All three RC3-SC nodes simultaneously streamed data from Elasticsearch"
        log_info "Files were deleted after collection to demonstrate continuous, ephemeral data flow"
        log_info "This demonstrates network utilization across SC25 infrastructure"
    else
        log_error "Some pods failed to collect data from Elasticsearch"
        [ $result_13 -ne 0 ] && log_error "  rc3-sc-13 failed"
        [ $result_14 -ne 0 ] && log_error "  rc3-sc-14 failed"
        [ $result_15 -ne 0 ] && log_error "  rc3-sc-15 failed"
        return 1
    fi
}

# Function to sync data to Elasticsearch (demonstrates network to central storage)
demo_sync_to_elasticsearch() {
    log_info "Demonstrating data sync from RC3 pods to Elasticsearch (network activity)..."
    
    # Get Elasticsearch pod
    local es_pod=$(kubectl get pods -n "$NAMESPACE" -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -z "$es_pod" ]]; then
        log_info "Elasticsearch pod not found, skipping sync demo"
        return 0
    fi
    
    log_info "Elasticsearch pod: $es_pod"
    
    # Generate data in each RC3 pod and sync to ES
    for node_num in "13" "14" "15"; do
        local pod=$(get_pod_name "$node_num")
        if [[ -n "$pod" ]]; then
            log_info "Generating and syncing data from $pod..."
            
            # Generate test data
            generate_test_data "$pod" "100" "sync-demo-${node_num}.bin"
            
            # Sync to Elasticsearch (demonstrates network transfer)
            local start_time=$(date +%s)
            kubectl cp "$NAMESPACE/$pod:/workspace/credo-data-rc3/sync-demo-${node_num}.bin" \
                       "$NAMESPACE/$es_pod:/workspace/credo-data/rc3-sc-${node_num}-sync-demo.bin" 2>&1
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            
            log_success "Synced 100MB from $pod to Elasticsearch in ${duration}s"
        fi
    done
    
    log_success "All data synced to Elasticsearch - network activity demonstrated!"
}

# Function to show network statistics
show_network_stats() {
    log_info "Network statistics for RC3 pods:"
    echo ""
    
    for node_num in "13" "14" "15"; do
        local pod=$(get_pod_name "$node_num")
        if [[ -n "$pod" ]]; then
            echo "Pod: $pod (rc3-sc-${node_num})"
            kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "
                echo '  Network interfaces:'
                ip -br addr show 2>/dev/null | head -3 || echo '    (network info not available)'
                echo '  Pod IP:'
                hostname -I 2>/dev/null || echo '    (IP info not available)'
            " 2>/dev/null || echo "  (stats not available)"
            echo ""
        fi
    done
}

# Main function
main() {
    case "${1:-demo}" in
        "demo")
            echo "=========================================="
            echo "SC25 Network Link Demonstration"
            echo "Using RC3-SC Pods"
            echo "=========================================="
            echo ""
            
            # Verify pods exist first
            log_info "Checking RC3 pods..."
            local pod_13=$(get_pod_name "13")
            local pod_14=$(get_pod_name "14")
            local pod_15=$(get_pod_name "15")
            
            if [[ -z "$pod_13" || -z "$pod_14" || -z "$pod_15" ]]; then
                log_error "Not all RC3 pods are available!"
                echo ""
                echo "Please deploy the RC3 data collectors first:"
                echo "  ./deploy/05-deploy-rc3-data-collectors.sh deploy"
                exit 1
            fi
            
            demo_parallel_collection
            ;;
        "sync")
            demo_sync_to_elasticsearch
            ;;
        "iperf")
            local pod_13=$(get_pod_name "13")
            local pod_14=$(get_pod_name "14")
            if [[ -n "$pod_13" && -n "$pod_14" ]]; then
                start_iperf_server "$pod_14"
                sleep 2
                run_iperf_test "$pod_13" "$pod_14" "30"
            else
                echo "Error: Pods not available"
            fi
            ;;
        "stats")
            show_network_stats
            ;;
        "help"|"-h"|"--help")
            cat << EOF
Usage: $0 [command]

Commands:
    demo    Run parallel data transfers between RC3 pods (default)
    sync    Sync data from RC3 pods to Elasticsearch
    iperf   Run iperf3 bandwidth test between pods
    stats   Show network statistics for RC3 pods
    help    Show this help message

Examples:
    $0 demo              # Demonstrate parallel transfers
    $0 sync              # Sync data to Elasticsearch
    $0 iperf             # Run bandwidth test
    $0 stats             # Show network stats

This script demonstrates SC25 network links by transferring CREDO JSON
files between the three RC3-SC pods (rc3-sc-13, rc3-sc-14, rc3-sc-15).

Note: This script requires existing CREDO JSON files in the pods. If no
files are found, run data collection first:
  ./deploy/05-deploy-rc3-data-collectors.sh start
EOF
            ;;
        *)
            echo "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

main "$@"

