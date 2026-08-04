#!/bin/bash

# CREDO Data Collection - Deploy Additional Collectors on RC3-SC Nodes
# This script deploys additional data collection pods on rc3-sc nodes to collect more data in parallel

set -euo pipefail

# Configuration
NAMESPACE="cblee-credo"
CREDO_TOKEN="e26fcf245c7b96a4c8daf5b72ddc17d34891ea0e68b10bd396e547ec74917656"

# RC3-SC Nodes to use
RC3_NODES=(
    "rc3-sc-13.sc25.nrp-nautilus.io"
    "rc3-sc-14.sc25.nrp-nautilus.io"
    "rc3-sc-15.sc25.nrp-nautilus.io"
)

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

# Function to generate node affinity and toleration YAML for RC3-SC node
generate_rc3_affinity_toleration() {
    local node_name=$1
    cat << AFFINITY_EOF
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/hostname
                operator: In
                values:
                - $node_name
      tolerations:
      - key: "nautilus.io/reservation"
        operator: "Equal"
        value: "scinet"
        effect: "NoSchedule"
AFFINITY_EOF
}

# Function to create a data collector pod on a specific node
create_data_collector() {
    local node_name=$1
    # Extract the full number (e.g., "13" from "rc3-sc-13.sc25.nrp-nautilus.io")
    local node_num=$(echo "$node_name" | sed -E 's/.*rc3-sc-([0-9]+)\..*/\1/')
    if [[ -z "$node_num" ]]; then
        log_error "Failed to extract node number from: $node_name"
        return 1
    fi
    local pod_name="credo-data-collector-rc3-${node_num}"
    
    log_info "Creating data collector pod: $pod_name on node: $node_name"
    
    cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $pod_name
  namespace: $NAMESPACE
  labels:
    app: credo-data-collector
    component: data-collector
    node: rc3-sc-${node_num}
spec:
  replicas: 1
  selector:
    matchLabels:
      app: credo-data-collector
      node: rc3-sc-${node_num}
  template:
    metadata:
      labels:
        app: credo-data-collector
        component: data-collector
        node: rc3-sc-${node_num}
    spec:
$(generate_rc3_affinity_toleration "$node_name")
      containers:
      - name: data-collector
        image: gitlab-registry.nrp-nautilus.io/cloud-ai-100/qaic-docker-images:vllm-latest
        ports:
        - containerPort: 8888
        - containerPort: 5000
        - containerPort: 8080
        resources:
          requests:
            cpu: "2"
            memory: "8Gi"
          limits:
            cpu: "4"
            memory: "16Gi"
        env:
        - name: PYTHONUNBUFFERED
          value: "1"
        - name: TF_CPP_MIN_LOG_LEVEL
          value: "2"
        - name: PYTHONPATH
          value: "/workspace"
        - name: CREDO_TOKEN
          value: "$CREDO_TOKEN"
        - name: CREDO_ENVIRONMENT
          value: "nrp-nautilus-test"
        - name: COLLECTOR_NODE
          value: "$node_name"
        command:
        - /bin/bash
        - -c
        - |
          echo "Starting CREDO Data Collector on $node_name..."
          echo "Installing dependencies..."
          pip install requests > /dev/null 2>&1
          echo "Setting up CREDO data exporter..."
          mkdir -p /workspace/data-exporter
          mkdir -p /workspace/credo-data-rc3
          echo "Data collector ready on $node_name!"
          echo "Data will be stored in /workspace/credo-data-rc3/"
          echo "To start data collection, run:"
          echo "  python3 /workspace/data-exporter/credo-data-exporter.py --token \$CREDO_TOKEN --dir /workspace/credo-data-rc3 --max-chunk-size 1000 --data-type detection"
          sleep infinity
---
apiVersion: v1
kind: Service
metadata:
  name: ${pod_name}-service
  namespace: $NAMESPACE
  labels:
    app: credo-data-collector
    node: rc3-sc-${node_num}
spec:
  selector:
    app: credo-data-collector
    node: rc3-sc-${node_num}
  ports:
  - name: jupyter
    port: 8888
    targetPort: 8888
  - name: api
    port: 5000
    targetPort: 5000
  - name: web
    port: 8080
    targetPort: 8080
  type: ClusterIP
EOF
    
    log_success "Data collector $pod_name created"
}

# Function to setup data exporter in all collector pods
setup_data_exporters() {
    log_info "Setting up data exporters in all collector pods..."
    
    for node_name in "${RC3_NODES[@]}"; do
        local node_num=$(echo "$node_name" | sed -E 's/.*rc3-sc-([0-9]+)\..*/\1/')
        local pod_name="credo-data-collector-rc3-${node_num}"
        
        # Wait for pod to be ready
        log_info "Waiting for $pod_name to be ready..."
        if kubectl wait --for=condition=ready pod -l app=credo-data-collector,node=rc3-sc-${node_num} -n "$NAMESPACE" --timeout=300s 2>/dev/null; then
            local pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-data-collector,node=rc3-sc-${node_num} -o jsonpath='{.items[0].metadata.name}')
            
            # Copy the data exporter
            kubectl cp ./data-exporter/credo-data-exporter.py "$NAMESPACE/$pod:/workspace/data-exporter/" 2>/dev/null || log_warning "Could not copy data exporter to $pod_name"
            log_success "Data exporter setup in $pod_name"
        else
            log_warning "Pod $pod_name not ready, skipping exporter setup"
        fi
    done
}

# Function to start data collection on all collectors
start_data_collection() {
    log_info "Starting data collection on all RC3-SC collectors..."
    
    for node_name in "${RC3_NODES[@]}"; do
        local node_num=$(echo "$node_name" | sed -E 's/.*rc3-sc-([0-9]+)\..*/\1/')
        local pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-data-collector,node=rc3-sc-${node_num} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        
        if [[ -n "$pod" ]]; then
            log_info "Starting data collection on $pod (node: $node_name)..."
            
            # Start data collection in background
            kubectl exec -n "$NAMESPACE" "$pod" -- bash -c "
                export CREDO_TOKEN='$CREDO_TOKEN'
                cd /workspace/data-exporter
                nohup python3 credo-data-exporter.py --token \$CREDO_TOKEN --dir /workspace/credo-data-rc3 --max-chunk-size 1000 --data-type detection > /tmp/data-collection.log 2>&1 &
                echo \$! > /tmp/data-collection.pid
                echo 'Data collection started in background (PID: \$(cat /tmp/data-collection.pid))'
            " || log_warning "Failed to start data collection on $pod"
            
            log_success "Data collection started on $pod"
        else
            log_warning "Pod for node $node_name not found"
        fi
    done
}

# Function to sync data from all RC3 collectors to Elasticsearch pod
sync_rc3_to_elasticsearch() {
    log_info "Syncing data from RC3 collectors to Elasticsearch pod..."
    
    # Get Elasticsearch pod
    local es_pod=$(kubectl get pods -n "$NAMESPACE" -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -z "$es_pod" ]]; then
        log_error "Elasticsearch pod not found. Please deploy Elasticsearch first."
        return 1
    fi
    
    # Simple: just copy entire directories from each RC3 collector to Elasticsearch pod
    for node_name in "${RC3_NODES[@]}"; do
        local node_num=$(echo "$node_name" | sed -E 's/.*rc3-sc-([0-9]+)\..*/\1/')
        local pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-data-collector,node=rc3-sc-${node_num} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        
        if [[ -n "$pod" ]]; then
            log_info "Copying data from $pod (node: $node_name) to Elasticsearch pod..."
            # Copy detections directory
            kubectl cp "$NAMESPACE/$pod:/workspace/credo-data-rc3/detections/" "$NAMESPACE/$es_pod:/workspace/credo-data/detections/rc3-sc-${node_num}/" 2>/dev/null || log_warning "No detections to copy from $pod"
            # Copy pings directory if it exists
            kubectl cp "$NAMESPACE/$pod:/workspace/credo-data-rc3/pings/" "$NAMESPACE/$es_pod:/workspace/credo-data/pings/rc3-sc-${node_num}/" 2>/dev/null || true
        fi
    done
    
    log_success "Data synced to Elasticsearch pod"
}

# Function to show collector status
show_collector_status() {
    log_info "RC3-SC Data Collector Status:"
    echo ""
    kubectl get pods -n "$NAMESPACE" -l app=credo-data-collector -o wide
    echo ""
    
    log_info "Data collection status per pod:"
    for node_name in "${RC3_NODES[@]}"; do
        local node_num=$(echo "$node_name" | sed -E 's/.*rc3-sc-([0-9]+)\..*/\1/')
        local pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-data-collector,node=rc3-sc-${node_num} -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
        
        if [[ -n "$pod" ]]; then
            echo ""
            log_info "Collector on $node_name ($pod):"
            
            # Check if collection is running
            local pid=$(kubectl exec -n "$NAMESPACE" "$pod" -- cat /tmp/data-collection.pid 2>/dev/null || echo "")
            if [[ -n "$pid" ]]; then
                echo "  Status: Running (PID: $pid)"
            else
                echo "  Status: Not started"
            fi
            
            # Show data files
            echo "  Data files (in collector pod):"
            kubectl exec -n "$NAMESPACE" "$pod" -- ls -lh /workspace/credo-data-rc3/detections/ 2>/dev/null | head -5 || echo "    No data files yet"
            
            # Check Elasticsearch pod for synced data
            local es_pod=$(kubectl get pods -n "$NAMESPACE" -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
            if [[ -n "$es_pod" ]]; then
                echo "  Data files (synced to Elasticsearch pod):"
                kubectl exec -n "$NAMESPACE" "$es_pod" -- ls -lh /workspace/credo-data/detections/rc3-sc-${node_num}-*.json 2>/dev/null | head -5 || echo "    No synced data in Elasticsearch pod yet (run sync_rc3_to_elasticsearch)"
            fi
            
            # Show latest log
            echo "  Latest log:"
            kubectl exec -n "$NAMESPACE" "$pod" -- tail -3 /tmp/data-collection.log 2>/dev/null || echo "    No log available"
        fi
    done
}

# Function to copy collected data to local machine (from Elasticsearch pod)
copy_collected_data() {
    local local_dir="${1:-./credo-data-rc3-collected}"
    
    log_info "Copying collected data from Elasticsearch pod to $local_dir..."
    mkdir -p "$local_dir"
    
    # Get Elasticsearch pod
    local es_pod=$(kubectl get pods -n "$NAMESPACE" -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [[ -n "$es_pod" ]]; then
        log_info "Copying data from Elasticsearch pod ($es_pod)..."
        kubectl cp "$NAMESPACE/$es_pod:/workspace/credo-data/" "$local_dir/" 2>/dev/null || log_warning "No data to copy from Elasticsearch pod"
        log_success "Data copied to $local_dir"
    else
        log_error "Elasticsearch pod not found"
        return 1
    fi
    
    echo ""
    log_info "Data structure:"
    find "$local_dir" -name "*.json" | head -10
    echo ""
    log_info "Total files: $(find "$local_dir" -name "*.json" 2>/dev/null | wc -l)"
}

# Main function
main() {
    case "${1:-deploy}" in
        "deploy")
            log_info "Deploying data collectors on RC3-SC nodes..."
            for node in "${RC3_NODES[@]}"; do
                create_data_collector "$node"
            done
            log_info "Waiting for pods to be ready..."
            sleep 10
            setup_data_exporters
            log_success "All data collectors deployed!"
            show_collector_status
            ;;
        "start")
            start_data_collection
            ;;
        "status")
            show_collector_status
            ;;
        "sync")
            sync_rc3_to_elasticsearch
            ;;
        "copy")
            copy_collected_data "${2:-}"
            ;;
        "help"|"-h"|"--help")
            cat << EOF
Usage: $0 [command] [options]

Commands:
    deploy    Deploy data collector pods on all RC3-SC nodes (default)
    start     Start data collection on all deployed collectors
    sync      Sync collected data from RC3 collectors to Elasticsearch pod
    status    Show status of all data collectors
    copy      Copy collected data from Elasticsearch pod to local directory
              Usage: $0 copy [local-directory]
    help      Show this help message

Examples:
    $0 deploy              # Deploy collectors on all RC3-SC nodes
    $0 start               # Start data collection
    $0 sync                # Sync collected data to Elasticsearch pod
    $0 status              # Check collector status
    $0 copy                # Copy data from Elasticsearch pod to ./credo-data-rc3-collected
    $0 copy ./my-data      # Copy data to ./my-data

Nodes used:
    - rc3-sc-13.sc25.nrp-nautilus.io
    - rc3-sc-14.sc25.nrp-nautilus.io
    - rc3-sc-15.sc25.nrp-nautilus.io
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

