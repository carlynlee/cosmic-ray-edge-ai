#!/bin/bash

# Deploy CREDO Data Stream CronJob
# This script creates a CronJob that periodically fetches data from CREDO.science
# and streams it to Elasticsearch

set -euo pipefail

# Configuration
NAMESPACE="${CREDO_NAMESPACE:-cblee-credo}"
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

# Check if CREDO_TOKEN is provided
if [[ -z "$CREDO_TOKEN" ]]; then
    log_error "CREDO_TOKEN environment variable is required"
    echo "Usage: CREDO_TOKEN='your_token' $0"
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" &>/dev/null; then
    log_error "Namespace '$NAMESPACE' does not exist"
    exit 1
fi

log_info "Deploying CREDO Data Stream CronJob..."
log_info "Namespace: $NAMESPACE"

# Create secret for CREDO token if it doesn't exist
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

# Apply CronJob
log_info "Applying CronJob manifest..."
kubectl apply -f deploy/credo-data-stream-cronjob.yaml

log_success "CronJob deployed successfully!"

# Show status
log_info "CronJob status:"
kubectl get cronjob credo-data-stream -n "$NAMESPACE"

echo ""
log_info "The CronJob will:"
echo "  • Run every 10 minutes"
echo "  • Fetch latest data from CREDO.science API"
echo "  • Stream data directly to Elasticsearch"
echo "  • Track incremental updates (only fetches new data)"

echo ""
log_info "To check job status:"
echo "  kubectl get jobs -n $NAMESPACE -l app=credo-data-stream"
echo ""
log_info "To view job logs:"
echo "  kubectl logs -n $NAMESPACE -l app=credo-data-stream --tail=100"
echo ""
log_info "To manually trigger a job:"
echo "  kubectl create job --from=cronjob/credo-data-stream manual-trigger -n $NAMESPACE"

