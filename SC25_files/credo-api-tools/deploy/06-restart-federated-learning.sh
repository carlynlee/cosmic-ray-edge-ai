#!/bin/bash

# CREDO Federated Learning - Restart Script
# Kills existing FL processes and restarts everything cleanly

set -euo pipefail

# Configuration
NAMESPACE="cblee-credo"

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

# Function to kill FL server
kill_fl_server() {
    log_info "Killing FL server process..."
    
    local fl_server_pod=$(get_pod_name "caltech-fl-server")
    
    if [ -z "$fl_server_pod" ]; then
        log_warning "Caltech FL Server pod not found!"
        return 0
    fi
    
    log_info "Found FL server pod: $fl_server_pod"
    
    # Find and kill python3 processes running fl_server_caltech.py
    local pids=$(kubectl exec -n "$NAMESPACE" "$fl_server_pod" -- sh -c "ps aux | grep 'fl_server_caltech.py' | grep -v grep | awk '{print \$2}'" 2>/dev/null || echo "")
    
    if [ ! -z "$pids" ]; then
        for pid in $pids; do
            log_info "Killing FL server process PID: $pid"
            kubectl exec -n "$NAMESPACE" "$fl_server_pod" -- kill -9 "$pid" 2>/dev/null || true
        done
        log_success "FL server processes killed"
    else
        log_info "No FL server processes found to kill"
    fi
    
    # Clean up zombie processes
    log_info "Cleaning up zombie processes..."
    kubectl exec -n "$NAMESPACE" "$fl_server_pod" -- sh -c "ps aux | grep '[p]ython3' | awk '{print \$2}' | xargs -r kill -9 2>/dev/null || true" || true
    sleep 2
}

# Function to kill FL clients
kill_fl_clients() {
    log_info "Killing FL client processes..."
    
    local caltech_pod=$(get_pod_name "caltech-fl-client")
    local mit_pod=$(get_pod_name "mit-fl-client")
    local udel_pod=$(get_pod_name "udel-fl-client")
    
    for pod in "$caltech_pod" "$mit_pod" "$udel_pod"; do
        if [ ! -z "$pod" ]; then
            log_info "Cleaning up processes in pod: $pod"
            # Kill any python3 processes (including zombies)
            kubectl exec -n "$NAMESPACE" "$pod" -- sh -c "ps aux | grep '[p]ython3' | awk '{print \$2}' | xargs -r kill -9 2>/dev/null || true" || true
        fi
    done
    
    sleep 2
    log_success "FL client processes cleaned up"
}

# Function to start FL server
start_fl_server() {
    log_info "Starting FL server on Caltech pod..."
    
    local fl_server_pod=$(get_pod_name "caltech-fl-server")
    
    if [ -z "$fl_server_pod" ]; then
        log_error "Caltech FL Server pod not found!"
        return 1
    fi
    
    log_info "Found FL server pod: $fl_server_pod"
    
    # Start FL server in background
    kubectl exec -n "$NAMESPACE" "$fl_server_pod" -- python3 /workspace/fl-server/fl_server_caltech.py > /dev/null 2>&1 &
    
    log_success "FL server started on $fl_server_pod"
    log_info "Waiting 10 seconds for server to initialize..."
    sleep 10
}

# Function to start Caltech FL client
start_caltech_client() {
    log_info "Starting Caltech FL client..."
    
    local caltech_pod=$(get_pod_name "caltech-fl-client")
    
    if [ -z "$caltech_pod" ]; then
        log_error "Caltech FL Client pod not found!"
        return 1
    fi
    
    log_info "Found Caltech client pod: $caltech_pod"
    
    # Start Caltech FL client in background
    kubectl exec -n "$NAMESPACE" "$caltech_pod" -- python3 /workspace/fl-client/fl_client_caltech.py > /dev/null 2>&1 &
    
    log_success "Caltech FL client started on $caltech_pod"
    sleep 2
}

# Function to start MIT FL client
start_mit_client() {
    log_info "Starting MIT FL client..."
    
    local mit_pod=$(get_pod_name "mit-fl-client")
    
    if [ -z "$mit_pod" ]; then
        log_error "MIT FL Client pod not found!"
        return 1
    fi
    
    log_info "Found MIT client pod: $mit_pod"
    
    # Start MIT FL client in background
    kubectl exec -n "$NAMESPACE" "$mit_pod" -- python3 /workspace/fl-client/fl_client_mit.py > /dev/null 2>&1 &
    
    log_success "MIT FL client started on $mit_pod"
    sleep 2
}

# Function to start UDel FL client
start_udel_client() {
    log_info "Starting UDel FL client..."
    
    local udel_pod=$(get_pod_name "udel-fl-client")
    
    if [ -z "$udel_pod" ]; then
        log_error "UDel FL Client pod not found!"
        return 1
    fi
    
    log_info "Found UDel client pod: $udel_pod"
    
    # Start UDel FL client in background
    kubectl exec -n "$NAMESPACE" "$udel_pod" -- python3 /workspace/fl-client/fl_client_udel.py > /dev/null 2>&1 &
    
    log_success "UDel FL client started on $udel_pod"
    sleep 2
}

# Function to check status
check_status() {
    log_info "Checking federated learning status..."
    echo ""
    
    local fl_server_pod=$(get_pod_name "caltech-fl-server")
    local caltech_pod=$(get_pod_name "caltech-fl-client")
    local mit_pod=$(get_pod_name "mit-fl-client")
    local udel_pod=$(get_pod_name "udel-fl-client")
    
    if [ ! -z "$fl_server_pod" ]; then
        echo "FL Server (Caltech): $fl_server_pod"
        local server_pids=$(kubectl exec -n "$NAMESPACE" "$fl_server_pod" -- sh -c "ps aux | grep 'fl_server_caltech.py' | grep -v grep | wc -l" 2>/dev/null || echo "0")
        if [ "$server_pids" -gt 0 ]; then
            echo "  ✓ Server process running"
        else
            echo "  ✗ No server process found"
        fi
    fi
    
    if [ ! -z "$caltech_pod" ]; then
        echo "Caltech Client: $caltech_pod"
        local client_pids=$(kubectl exec -n "$NAMESPACE" "$caltech_pod" -- sh -c "ps aux | grep 'fl_client_caltech.py' | grep -v grep | wc -l" 2>/dev/null || echo "0")
        if [ "$client_pids" -gt 0 ]; then
            echo "  ✓ Client process running"
        else
            echo "  ✗ No client process found"
        fi
    fi
    
    if [ ! -z "$mit_pod" ]; then
        echo "MIT Client: $mit_pod"
        local client_pids=$(kubectl exec -n "$NAMESPACE" "$mit_pod" -- sh -c "ps aux | grep 'fl_client_mit.py' | grep -v grep | wc -l" 2>/dev/null || echo "0")
        if [ "$client_pids" -gt 0 ]; then
            echo "  ✓ Client process running"
        else
            echo "  ✗ No client process found"
        fi
    fi
    
    if [ ! -z "$udel_pod" ]; then
        echo "UDel Client: $udel_pod"
        local client_pids=$(kubectl exec -n "$NAMESPACE" "$udel_pod" -- sh -c "ps aux | grep 'fl_client_udel.py' | grep -v grep | wc -l" 2>/dev/null || echo "0")
        if [ "$client_pids" -gt 0 ]; then
            echo "  ✓ Client process running"
        else
            echo "  ✗ No client process found"
        fi
    fi
}

# Main function
main() {
    log_info "Restarting CREDO Three-Site Federated Learning..."
    log_info "Namespace: $NAMESPACE"
    echo ""
    
    # Check if pods exist
    local fl_server_pod=$(get_pod_name "caltech-fl-server")
    local caltech_pod=$(get_pod_name "caltech-fl-client")
    local mit_pod=$(get_pod_name "mit-fl-client")
    local udel_pod=$(get_pod_name "udel-fl-client")
    
    if [ -z "$fl_server_pod" ] || [ -z "$caltech_pod" ] || [ -z "$mit_pod" ] || [ -z "$udel_pod" ]; then
        log_error "Not all pods are available!"
        log_info "Please run ./deploy/01-deploy-credo-system.sh first"
        exit 1
    fi
    
    # Step 1: Kill existing processes
    log_info "Step 1: Cleaning up existing processes..."
    kill_fl_server
    kill_fl_clients
    
    echo ""
    log_info "Step 2: Starting fresh FL components..."
    
    # Step 2: Start components
    start_fl_server
    start_caltech_client
    start_mit_client
    start_udel_client
    
    echo ""
    log_success "All federated learning components restarted!"
    echo ""
    log_info "Federated learning is now running across three sites:"
    echo "  - Caltech: FL Server (coordinator) + FL Client (clusters 0-3)"
    echo "  - MIT: FL Client (clusters 4-6)"
    echo "  - UDel: FL Client (clusters 7-9)"
    echo ""
    log_info "Monitor progress with:"
    echo "  kubectl logs -n $NAMESPACE $fl_server_pod -f"
    echo "  kubectl logs -n $NAMESPACE $caltech_pod -f"
    echo "  kubectl logs -n $NAMESPACE $mit_pod -f"
    echo "  kubectl logs -n $NAMESPACE $udel_pod -f"
    echo ""
    
    # Show status
    check_status
}

# Run main function
main

