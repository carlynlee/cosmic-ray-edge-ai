#!/bin/bash

# Deploy CREDO Real-Time Streamer to Kubernetes
# This script creates a Deployment that continuously streams CREDO.science data to Elasticsearch

set -euo pipefail

# Configuration
NAMESPACE="${CREDO_NAMESPACE:-cblee-credo}"
CREDO_USERNAME="${CREDO_USERNAME:-}"
CREDO_PASSWORD="${CREDO_PASSWORD:-}"
CREDO_TOKEN="${CREDO_TOKEN:-}"

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

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
    log_error "Namespace '$NAMESPACE' does not exist"
    exit 1
fi

log_info "Deploying CREDO Real-Time Streamer..."
log_info "Namespace: $NAMESPACE"

# Check for credentials
if [[ -z "$CREDO_TOKEN" ]] && [[ -z "$CREDO_USERNAME" ]]; then
    log_error "Either CREDO_TOKEN or CREDO_USERNAME/CREDO_PASSWORD must be provided"
    echo ""
    echo "Usage options:"
    echo "  Option 1 (Token):"
    echo "    CREDO_TOKEN='your_token' $0"
    echo ""
    echo "  Option 2 (Username/Password):"
    echo "    CREDO_USERNAME='username' CREDO_PASSWORD='password' $0"
    exit 1
fi

# Create or update CREDO token secret (if using token)
if [[ -n "$CREDO_TOKEN" ]]; then
    if ! kubectl get secret credo-token -n "$NAMESPACE" &>/dev/null; then
        log_info "Creating CREDO token secret..."
        kubectl create secret generic credo-token \
            --from-literal=token="$CREDO_TOKEN" \
            -n "$NAMESPACE"
        log_success "CREDO token secret created"
    else
        log_info "Updating CREDO token secret..."
        kubectl create secret generic credo-token \
            --from-literal=token="$CREDO_TOKEN" \
            -n "$NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
        log_success "CREDO token secret updated"
    fi
fi

# Create or update CREDO credentials secret (if using username/password)
if [[ -n "$CREDO_USERNAME" ]] && [[ -n "$CREDO_PASSWORD" ]]; then
    if ! kubectl get secret credo-credentials -n "$NAMESPACE" &>/dev/null; then
        log_info "Creating CREDO credentials secret..."
        kubectl create secret generic credo-credentials \
            --from-literal=username="$CREDO_USERNAME" \
            --from-literal=password="$CREDO_PASSWORD" \
            -n "$NAMESPACE"
        log_success "CREDO credentials secret created"
    else
        log_info "Updating CREDO credentials secret..."
        kubectl create secret generic credo-credentials \
            --from-literal=username="$CREDO_USERNAME" \
            --from-literal=password="$CREDO_PASSWORD" \
            -n "$NAMESPACE" \
            --dry-run=client -o yaml | kubectl apply -f -
        log_success "CREDO credentials secret updated"
    fi
fi

# Create or update ConfigMap with the script
# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRIPT_PATH="$PROJECT_ROOT/scripts/stream_credo_to_elasticsearch.py"

if [[ ! -f "$SCRIPT_PATH" ]]; then
    log_error "Script not found: $SCRIPT_PATH"
    log_error "Please ensure scripts/stream_credo_to_elasticsearch.py exists"
    exit 1
fi

log_info "Creating ConfigMap with streaming script..."
log_info "Script path: $SCRIPT_PATH"
kubectl create configmap credo-stream-script \
    --from-file=stream_credo_to_elasticsearch.py="$SCRIPT_PATH" \
    -n "$NAMESPACE" \
    --dry-run=client -o yaml | kubectl apply -f -
log_success "ConfigMap created/updated"

# Apply Deployment
log_info "Applying Deployment manifest..."
kubectl apply -f deploy/credo-stream-deployment.yaml

log_success "Deployment created successfully!"

# Wait for deployment to be ready
log_info "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=60s deployment/credo-stream -n "$NAMESPACE" || true

# Show status
log_info "Deployment status:"
kubectl get deployment credo-stream -n "$NAMESPACE"

echo ""
log_info "Pod status:"
kubectl get pods -l app=credo-stream -n "$NAMESPACE"

echo ""
log_success "CREDO Real-Time Streamer is running!"
echo ""
log_info "The streamer will:"
echo "  • Poll CREDO.science API every 15 minutes (POLL_INTERVAL=900s)"
echo "  • Stream new detections directly to Elasticsearch"
echo "  • Handle rate limits with automatic backoff (30 min when rate limited)"
echo "  • Maintain state in persistent storage"
echo ""
log_info "To view logs:"
echo "  kubectl logs -f deployment/credo-stream -n $NAMESPACE"
echo ""
log_info "To check status:"
echo "  kubectl get pods -l app=credo-stream -n $NAMESPACE"

