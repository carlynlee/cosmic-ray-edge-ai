#!/bin/bash

# CREDO Federated Learning - Start Script
# Starts the FL server and clients for three-site federated learning

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
    kubectl exec -n "$NAMESPACE" "$fl_server_pod" -- python3 /workspace/fl-server/fl_server_caltech.py &
    
    log_success "FL server started on $fl_server_pod"
    log_info "Waiting 5 seconds for server to initialize..."
    sleep 5
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
    kubectl exec -n "$NAMESPACE" "$caltech_pod" -- python3 /workspace/fl-client/fl_client_caltech.py &
    
    log_success "Caltech FL client started on $caltech_pod"
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
    kubectl exec -n "$NAMESPACE" "$mit_pod" -- python3 /workspace/fl-client/fl_client_mit.py &
    
    log_success "MIT FL client started on $mit_pod"
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
    kubectl exec -n "$NAMESPACE" "$udel_pod" -- python3 /workspace/fl-client/fl_client_udel.py &
    
    log_success "UDel FL client started on $udel_pod"
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
        kubectl logs -n "$NAMESPACE" "$fl_server_pod" --tail=5 2>/dev/null || echo "  No logs yet"
    fi
    
    if [ ! -z "$caltech_pod" ]; then
        echo "Caltech Client (clusters 0-3): $caltech_pod"
        kubectl logs -n "$NAMESPACE" "$caltech_pod" --tail=5 2>/dev/null || echo "  No logs yet"
    fi
    
    if [ ! -z "$mit_pod" ]; then
        echo "MIT Client (clusters 4-6): $mit_pod"
        kubectl logs -n "$NAMESPACE" "$mit_pod" --tail=5 2>/dev/null || echo "  No logs yet"
    fi
    
    if [ ! -z "$udel_pod" ]; then
        echo "UDel Client (clusters 7-9): $udel_pod"
        kubectl logs -n "$NAMESPACE" "$udel_pod" --tail=5 2>/dev/null || echo "  No logs yet"
    fi
}

# Main function
main() {
    log_info "Starting CREDO Three-Site Federated Learning..."
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
    
    # Start components
    start_fl_server
    start_caltech_client
    start_mit_client
    start_udel_client
    
    echo ""
    log_success "All federated learning components started!"
    echo ""
    log_info "Federated learning is now running across three sites:"
    echo "  - Caltech: FL Server (coordinator) + FL Client (clusters 0-3)"
    echo "  - MIT: FL Client (clusters 4-6)"
    echo "  - UDel: FL Client (clusters 7-9)"
    echo ""
    log_info "Monitor progress with:"
    echo "  kubectl logs -n $NAMESPACE $fl_server_pod -f"
    echo "  kubectl logs -n $NAMESPACE $mit_pod -f"
    echo "  kubectl logs -n $NAMESPACE $udel_pod -f"
    echo ""
    
    # Show initial status
    check_status
}

# Run main function
main

