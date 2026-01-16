#!/bin/bash

# CREDO Three-Pod System - Cleanup Script
# Use this before deploying the new three-pod system

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

# Function to cleanup existing resources
cleanup_existing() {
    log_info "Cleaning up existing CREDO resources..."
    
    # Delete existing deployments
    log_info "Deleting existing deployments..."
    kubectl delete deployment credo-caltech-server -n "$NAMESPACE" --ignore-not-found=true
    kubectl delete deployment caltech-fl-server -n "$NAMESPACE" --ignore-not-found=true
    kubectl delete deployment caltech-fl-client -n "$NAMESPACE" --ignore-not-found=true
    kubectl delete deployment mit-fl-client -n "$NAMESPACE" --ignore-not-found=true
    kubectl delete deployment udel-fl-client -n "$NAMESPACE" --ignore-not-found=true
    kubectl delete deployment credo-demo -n "$NAMESPACE" --ignore-not-found=true
    
    # Delete existing services
    log_info "Deleting existing services..."
    kubectl delete service credo-caltech-server-service -n "$NAMESPACE" --ignore-not-found=true
    kubectl delete service caltech-fl-server-service -n "$NAMESPACE" --ignore-not-found=true
    kubectl delete service caltech-fl-client-service -n "$NAMESPACE" --ignore-not-found=true
    kubectl delete service mit-fl-client-service -n "$NAMESPACE" --ignore-not-found=true
    kubectl delete service udel-fl-client-service -n "$NAMESPACE" --ignore-not-found=true
    kubectl delete service credo-demo-service -n "$NAMESPACE" --ignore-not-found=true
    
    # Delete existing Elasticsearch
    log_info "Deleting existing Elasticsearch..."
    kubectl delete elasticsearch quickstart -n "$NAMESPACE" --ignore-not-found=true
    kubectl delete elasticsearch credo-elasticsearch -n "$NAMESPACE" --ignore-not-found=true
    
    # Delete existing services
    kubectl delete service quickstart-es-default -n "$NAMESPACE" --ignore-not-found=true
    kubectl delete service quickstart-kb-http -n "$NAMESPACE" --ignore-not-found=true
    kubectl delete service credo-elasticsearch-service -n "$NAMESPACE" --ignore-not-found=true
    
    # Delete existing secrets
    log_info "Deleting existing secrets..."
    kubectl delete secret credo-token -n "$NAMESPACE" --ignore-not-found=true
    
    # Wait for pods to terminate
    log_info "Waiting for pods to terminate..."
    kubectl wait --for=delete pod -l app=credo-caltech-server -n "$NAMESPACE" --timeout=60s || true
    kubectl wait --for=delete pod -l app=caltech-fl-server -n "$NAMESPACE" --timeout=60s || true
    kubectl wait --for=delete pod -l app=caltech-fl-client -n "$NAMESPACE" --timeout=60s || true
    kubectl wait --for=delete pod -l app=mit-fl-client -n "$NAMESPACE" --timeout=60s || true
    kubectl wait --for=delete pod -l app=udel-fl-client -n "$NAMESPACE" --timeout=60s || true
    kubectl wait --for=delete pod -l app=credo-demo -n "$NAMESPACE" --timeout=60s || true
    
    log_success "Cleanup completed"
}

# Function to show current resources
show_current_resources() {
    log_info "Current resources in namespace $NAMESPACE:"
    echo ""
    kubectl get pods -n "$NAMESPACE" 2>/dev/null || echo "No pods found"
    echo ""
    kubectl get services -n "$NAMESPACE" 2>/dev/null || echo "No services found"
    echo ""
    kubectl get elasticsearch -n "$NAMESPACE" 2>/dev/null || echo "No Elasticsearch found"
    echo ""
}

# Main function
main() {
    log_info "Starting cleanup of existing CREDO resources..."
    log_info "Namespace: $NAMESPACE"
    
    # Show current resources
    show_current_resources
    
    # Ask for confirmation
    echo ""
    read -p "Do you want to proceed with cleanup? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cleanup_existing
        log_success "Cleanup completed successfully!"
        log_info "You can now run ./deploy/01-deploy-credo-system.sh to deploy the new three-pod system"
    else
        log_info "Cleanup cancelled"
    fi
}

# Run main function
main
