#!/bin/bash

# CREDO Federated Learning - Check Results Script
# Monitors training and displays results when complete

set -euo pipefail

# Configuration
NAMESPACE="cblee-credo"
MAX_WAIT_TIME=1800  # 30 minutes max wait time
CHECK_INTERVAL=30   # Check every 30 seconds

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Function to get pod names
get_pod_name() {
    local app_label=$1
    kubectl get pods -n "$NAMESPACE" -l app="$app_label" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null
}

# Function to check if training is complete
check_training_complete() {
    local fl_server_pod=$(get_pod_name "caltech-fl-server")
    
    if [ -z "$fl_server_pod" ]; then
        return 1
    fi
    
    # Check if results files exist
    kubectl exec -n "$NAMESPACE" "$fl_server_pod" -- test -f /workspace/fl-server/fl_training_results.json 2>/dev/null
}

# Function to get server process PID
get_server_pid() {
    local fl_server_pod=$(get_pod_name "caltech-fl-server")
    
    if [ -z "$fl_server_pod" ]; then
        echo ""
        return
    fi
    
    kubectl exec -n "$NAMESPACE" "$fl_server_pod" -- sh -c "ps aux | grep 'fl_server_caltech.py' | grep -v grep | awk '{print \$2}'" 2>/dev/null || echo ""
}

# Function to display results
display_results() {
    local fl_server_pod=$(get_pod_name "caltech-fl-server")
    
    if [ -z "$fl_server_pod" ]; then
        log_error "FL Server pod not found!"
        return 1
    fi
    
    log_success "Training Complete! Displaying results..."
    echo ""
    echo "============================================================"
    echo "FEDERATED LEARNING TRAINING RESULTS"
    echo "============================================================"
    echo ""
    
    # Display training results
    if kubectl exec -n "$NAMESPACE" "$fl_server_pod" -- test -f /workspace/fl-server/fl_training_results.json 2>/dev/null; then
        log_info "Training History:"
        kubectl exec -n "$NAMESPACE" "$fl_server_pod" -- python3 -c "
import json
with open('/workspace/fl-server/fl_training_results.json', 'r') as f:
    data = json.load(f)
    print(f\"Total Rounds: {data.get('total_rounds', 'N/A')}\")
    print(f\"Timestamp: {data.get('timestamp', 'N/A')}\")
    print(\"\\nTraining History:\")
    for entry in data.get('training_history', []):
        print(f\"  Round {entry.get('round', 'N/A')}: Loss={entry.get('loss', 'N/A'):.4f}, Clients={entry.get('num_clients', 'N/A')}\")
" 2>/dev/null || echo "  Could not parse training results"
        echo ""
    fi
    
    # Display per-site test accuracy
    if kubectl exec -n "$NAMESPACE" "$fl_server_pod" -- test -f /workspace/fl-server/fl_test_accuracy_per_site.json 2>/dev/null; then
        log_info "Per-Site Test Accuracy:"
        kubectl exec -n "$NAMESPACE" "$fl_server_pod" -- python3 -c "
import json
with open('/workspace/fl-server/fl_test_accuracy_per_site.json', 'r') as f:
    data = json.load(f)
    print(f\"Final Round: {data.get('final_round', 'N/A')}\")
    print(\"\\nPer-Site Results:\")
    for site, site_data in data.get('per_site_test_accuracy', {}).items():
        print(f\"\\n  {site_data.get('institution', site)} ({site}):\")
        print(f\"    Overall Accuracy: {site_data.get('overall_accuracy', 0.0):.4f}\")
        print(f\"    Overall Loss: {site_data.get('overall_loss', 0.0):.4f}\")
        print(f\"    Total Test Samples: {site_data.get('total_test_samples', 0)}\")
        print(\"    Per-Class Accuracy:\")
        per_class = site_data.get('per_class_accuracy', {})
        for class_id in range(10):
            class_key = f'class_{class_id}'
            class_acc = per_class.get(class_key, 0.0)
            class_samples = site_data.get('test_samples_per_class', {}).get(class_key, 0)
            print(f\"      Class {class_id}: {class_acc:.4f} ({class_samples} samples)\")
" 2>/dev/null || echo "  Could not parse test accuracy results"
        echo ""
    fi
    
    echo "============================================================"
    
    # Copy results files locally
    log_info "Copying results files to local directory..."
    mkdir -p results
    kubectl cp "$NAMESPACE/$fl_server_pod:/workspace/fl-server/fl_training_results.json" ./results/fl_training_results.json 2>/dev/null || log_warning "Could not copy training results"
    kubectl cp "$NAMESPACE/$fl_server_pod:/workspace/fl-server/fl_test_accuracy_per_site.json" ./results/fl_test_accuracy_per_site.json 2>/dev/null || log_warning "Could not copy test accuracy results"
    
    log_success "Results saved to ./results/"
}

# Main function
main() {
    log_info "Monitoring federated learning training..."
    log_info "This will wait up to $((MAX_WAIT_TIME / 60)) minutes for training to complete"
    echo ""
    
    local fl_server_pod=$(get_pod_name "caltech-fl-server")
    
    if [ -z "$fl_server_pod" ]; then
        log_error "FL Server pod not found!"
        exit 1
    fi
    
    local start_time=$(date +%s)
    local elapsed=0
    local server_pid=$(get_server_pid)
    
    if [ -z "$server_pid" ]; then
        log_warning "No FL server process found. Training may not have started."
        exit 1
    fi
    
    log_info "Server process PID: $server_pid"
    log_info "Checking every $CHECK_INTERVAL seconds..."
    echo ""
    
    while [ $elapsed -lt $MAX_WAIT_TIME ]; do
        # Check if server process is still running
        if ! kubectl exec -n "$NAMESPACE" "$fl_server_pod" -- test -d "/proc/$server_pid" 2>/dev/null; then
            log_info "Server process completed. Checking for results..."
            sleep 5
            if check_training_complete; then
                display_results
                exit 0
            else
                log_warning "Server process ended but no results files found."
                log_info "Checking server output..."
                kubectl logs -n "$NAMESPACE" "$fl_server_pod" --tail=50 | tail -30
                exit 1
            fi
        fi
        
        # Check if results files exist (training might have completed but process still running)
        if check_training_complete; then
            log_success "Results files found! Training appears complete."
            sleep 5  # Give it a moment to finish writing
            display_results
            exit 0
        fi
        
        elapsed=$(($(date +%s) - start_time))
        remaining=$((MAX_WAIT_TIME - elapsed))
        
        if [ $((elapsed % 60)) -eq 0 ]; then
            log_info "Still training... (${elapsed}s elapsed, ${remaining}s remaining)"
        fi
        
        sleep $CHECK_INTERVAL
    done
    
    log_warning "Maximum wait time reached. Checking current status..."
    
    if check_training_complete; then
        display_results
    else
        log_error "Training did not complete within the time limit."
        log_info "Server process status:"
        kubectl exec -n "$NAMESPACE" "$fl_server_pod" -- sh -c "ps aux | grep 'fl_server' | grep -v grep || echo 'No server process found'"
        log_info "Recent server logs:"
        kubectl logs -n "$NAMESPACE" "$fl_server_pod" --tail=50 | tail -30
        exit 1
    fi
}

# Run main function
main

