#!/bin/bash

# CREDO Three-Pod System - Status and Monitoring Script
# Check system status and health

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

# Function to show pod status
show_pod_status() {
    log_info "Pod Status:"
    echo ""
    kubectl get pods -n "$NAMESPACE" -o wide
    echo ""
}

# Function to show service status
show_service_status() {
    log_info "Service Status:"
    echo ""
    kubectl get services -n "$NAMESPACE"
    echo ""
}

# Function to show Elasticsearch status
show_elasticsearch_status() {
    log_info "Elasticsearch Status:"
    echo ""
    
    # Get Elasticsearch pod
    local es_pod=$(kubectl get pods -n "$NAMESPACE" -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -n "$es_pod" ]]; then
        # Get Elasticsearch password
        local es_password=$(kubectl get secret credo-elasticsearch-es-elastic-user -n "$NAMESPACE" -o jsonpath='{.data.elastic}' | base64 -d)
        
        # Show cluster health
        log_info "Cluster Health:"
        kubectl exec -n "$NAMESPACE" "$es_pod" -- curl -k -u "elastic:$es_password" -X GET "https://localhost:9200/_cluster/health?pretty" 2>/dev/null || echo "Elasticsearch not accessible"
        echo ""
        
        # Show document count
        log_info "Document Count:"
        kubectl exec -n "$NAMESPACE" "$es_pod" -- curl -k -u "elastic:$es_password" -X GET "https://localhost:9200/credo-detections/_count" 2>/dev/null || echo "No data indexed yet"
        echo ""
        
        # Show indices
        log_info "Indices:"
        kubectl exec -n "$NAMESPACE" "$es_pod" -- curl -k -u "elastic:$es_password" -X GET "https://localhost:9200/_cat/indices?v" 2>/dev/null || echo "No indices found"
        echo ""
    else
        log_warning "Elasticsearch pod not found"
    fi
}

# Function to show resource usage
show_resource_usage() {
    log_info "Resource Usage:"
    echo ""
    kubectl top pods -n "$NAMESPACE" 2>/dev/null || echo "Metrics not available"
    echo ""
}

# Function to show logs
show_logs() {
    log_info "Recent Logs:"
    echo ""
    
    # CREDO Caltech Server logs
    local credo_pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-caltech-server -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [[ -n "$credo_pod" ]]; then
        log_info "CREDO Caltech Server logs (last 10 lines):"
        kubectl logs -n "$NAMESPACE" "$credo_pod" --tail=10
        echo ""
    fi
    
    # Caltech FL Server logs
    local fl_pod=$(kubectl get pods -n "$NAMESPACE" -l app=caltech-fl-server -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [[ -n "$fl_pod" ]]; then
        log_info "Caltech FL Server logs (last 10 lines):"
        kubectl logs -n "$NAMESPACE" "$fl_pod" --tail=10
        echo ""
    fi
    
    # Caltech FL Client logs
    local caltech_client_pod=$(kubectl get pods -n "$NAMESPACE" -l app=caltech-fl-client -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [[ -n "$caltech_client_pod" ]]; then
        log_info "Caltech FL Client logs (last 10 lines):"
        kubectl logs -n "$NAMESPACE" "$caltech_client_pod" --tail=10
        echo ""
    fi
    
    # MIT FL Client logs
    local mit_pod=$(kubectl get pods -n "$NAMESPACE" -l app=mit-fl-client -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [[ -n "$mit_pod" ]]; then
        log_info "MIT FL Client logs (last 10 lines):"
        kubectl logs -n "$NAMESPACE" "$mit_pod" --tail=10
        echo ""
    fi
    
    # UDel FL Client logs
    local udel_pod=$(kubectl get pods -n "$NAMESPACE" -l app=udel-fl-client -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [[ -n "$udel_pod" ]]; then
        log_info "UDel FL Client logs (last 10 lines):"
        kubectl logs -n "$NAMESPACE" "$udel_pod" --tail=10
        echo ""
    fi
    
    # Elasticsearch logs
    local es_pod=$(kubectl get pods -n "$NAMESPACE" -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [[ -n "$es_pod" ]]; then
        log_info "Elasticsearch logs (last 10 lines):"
        kubectl logs -n "$NAMESPACE" "$es_pod" --tail=10
        echo ""
    fi
}

# Function to show port forwarding commands
show_port_forwarding() {
    log_info "Port Forwarding Commands:"
    echo ""
    echo "CREDO Caltech Server (Jupyter):"
    echo "kubectl port-forward -n $NAMESPACE svc/credo-caltech-server-service 8888:8888"
    echo ""
    echo "Caltech FL Server (API):"
    echo "kubectl port-forward -n $NAMESPACE svc/caltech-fl-server-service 5000:5000"
    echo ""
    echo "Caltech FL Client (Jupyter):"
    echo "kubectl port-forward -n $NAMESPACE svc/caltech-fl-client-service 8888:8888"
    echo ""
    echo "MIT FL Client (Jupyter):"
    echo "kubectl port-forward -n $NAMESPACE svc/mit-fl-client-service 8888:8888"
    echo ""
    echo "UDel FL Client (Jupyter):"
    echo "kubectl port-forward -n $NAMESPACE svc/udel-fl-client-service 8888:8888"
    echo ""
    echo "Elasticsearch:"
    echo "kubectl port-forward -n $NAMESPACE svc/credo-elasticsearch-service 9200:9200"
    echo ""
}

# Function to show Elasticsearch queries
show_elasticsearch_queries() {
    log_info "Elasticsearch Query Examples:"
    echo ""
    echo "Get document count:"
    echo "curl -k -u \"elastic:<password>\" -X GET \"https://localhost:9200/credo-detections/_count\""
    echo ""
    echo "Search for specific data:"
    echo "curl -k -u \"elastic:<password>\" -X GET \"https://localhost:9200/credo-detections/_search?q=particle_type:cosmic_ray\""
    echo ""
    echo "Get sample documents:"
    echo "curl -k -u \"elastic:<password>\" -X GET \"https://localhost:9200/credo-detections/_search?size=5&pretty\""
    echo ""
}

# Main function
main() {
    case "${1:-all}" in
        "pods")
            show_pod_status
            ;;
        "services")
            show_service_status
            ;;
        "elasticsearch")
            show_elasticsearch_status
            ;;
        "resources")
            show_resource_usage
            ;;
        "logs")
            show_logs
            ;;
        "ports")
            show_port_forwarding
            ;;
        "queries")
            show_elasticsearch_queries
            ;;
        "all"|"status")
            show_pod_status
            show_service_status
            show_elasticsearch_status
            show_resource_usage
            ;;
        "help"|"-h"|"--help")
            cat << EOF
Usage: $0 [command]

Commands:
    pods         Show pod status
    services     Show service status
    elasticsearch Show Elasticsearch status and data
    resources    Show resource usage
    logs         Show recent logs
    ports        Show port forwarding commands
    queries      Show Elasticsearch query examples
    all          Show all status information (default)
    help         Show this help message

Examples:
    $0 pods          # Show only pod status
    $0 elasticsearch # Show only Elasticsearch status
    $0 all           # Show all status information
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
