#!/bin/bash

# Script to redeploy FL pods to non-SC25 nodes
# This will delete existing FL deployments and recreate them without SC25 node affinity

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

# Function to get current node for a pod
get_current_node() {
    local app_label=$1
    kubectl get pods -n "$NAMESPACE" -l app="$app_label" -o jsonpath='{.items[0].spec.nodeName}' 2>/dev/null || echo "N/A"
}

# Main function
main() {
    log_info "Redeploying FL pods to non-SC25 nodes..."
    echo ""
    
    # Show current node assignments
    log_info "Current node assignments:"
    echo "  FL Server: $(get_current_node caltech-fl-server)"
    echo "  Caltech Client: $(get_current_node caltech-fl-client)"
    echo "  MIT Client: $(get_current_node mit-fl-client)"
    echo "  UDel Client: $(get_current_node udel-fl-client)"
    echo ""
    
    # Confirm
    read -p "This will delete and recreate FL deployments. Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cancelled."
        exit 0
    fi
    
    # Delete existing FL deployments (but keep data pods)
    log_info "Deleting existing FL deployments..."
    kubectl delete deployment -n "$NAMESPACE" caltech-fl-server caltech-fl-client mit-fl-client udel-fl-client 2>/dev/null || true
    
    log_info "Waiting for pods to terminate..."
    sleep 10
    
    # Unset SC25_NODE_NAME to allow scheduling on any node
    unset SC25_NODE_NAME
    export SC25_NODE_NAME=""
    
    log_info "Redeploying FL components without SC25 node affinity..."
    log_info "Pods will be scheduled on any available non-SC25 node"
    echo ""
    
    # Run the deployment script without SC25 node
    cd "$(dirname "$0")"
    SC25_NODE_NAME="" ./01-deploy-credo-system.sh
    
    echo ""
    log_success "Deployment complete!"
    echo ""
    
    # Wait a bit for pods to start
    log_info "Waiting for pods to start..."
    sleep 15
    
    # Show new node assignments
    log_info "New node assignments:"
    echo "  FL Server: $(get_current_node caltech-fl-server)"
    echo "  Caltech Client: $(get_current_node caltech-fl-client)"
    echo "  MIT Client: $(get_current_node mit-fl-client)"
    echo "  UDel Client: $(get_current_node udel-fl-client)"
    echo ""
    
    # Check if any are still on SC25 nodes
    local all_nodes=$(kubectl get pods -n "$NAMESPACE" -l 'app in (caltech-fl-server,caltech-fl-client,mit-fl-client,udel-fl-client)' -o jsonpath='{.items[*].spec.nodeName}')
    if echo "$all_nodes" | grep -q "sc25"; then
        log_warning "Some pods are still on SC25 nodes. They may need to be manually deleted and rescheduled."
    else
        log_success "All FL pods are now on non-SC25 nodes!"
    fi
}

# Run main function
main

