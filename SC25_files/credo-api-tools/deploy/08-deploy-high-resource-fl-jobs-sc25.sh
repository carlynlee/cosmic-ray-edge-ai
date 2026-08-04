#!/bin/bash

# CREDO High-Resource Federated Learning Jobs with SC25 Node Affinity
# Creates Kubernetes Jobs (not Deployments) with increased resources for SC25 nodes

set -euo pipefail

# Configuration
NAMESPACE="cblee-credo"
CREDO_TOKEN="e26fcf245c7b96a4c8daf5b72ddc17d34891ea0e68b10bd396e547ec74917656"

# SC25 Node Configuration - can specify specific nodes or use any SC25 node
# Available SC25 nodes: r640-01.sc25.nrp-nautilus.io, rc3-sc-13.sc25.nrp-nautilus.io, 
#                       rc3-sc-14.sc25.nrp-nautilus.io, rc3-sc-15.sc25.nrp-nautilus.io
SC25_NODES="${SC25_NODES:-r640-01.sc25.nrp-nautilus.io}"

# Resource Configuration - Higher resources for SC25 nodes
CPU_REQUEST="${CPU_REQUEST:-8}"
CPU_LIMIT="${CPU_LIMIT:-16}"
MEMORY_REQUEST="${MEMORY_REQUEST:-32Gi}"
MEMORY_LIMIT="${MEMORY_LIMIT:-64Gi}"

# Job Configuration
JOB_RESTART_POLICY="${JOB_RESTART_POLICY:-Never}"
JOB_BACKOFF_LIMIT="${JOB_BACKOFF_LIMIT:-3}"
JOB_ACTIVE_DEADLINE_SECONDS="${JOB_ACTIVE_DEADLINE_SECONDS:-7200}"  # 2 hours

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

# Function to generate SC25 node affinity and toleration YAML
generate_sc25_affinity_toleration() {
    # Convert comma-separated nodes to array
    IFS=',' read -ra NODE_ARRAY <<< "$SC25_NODES"
    
    local node_values=""
    for node in "${NODE_ARRAY[@]}"; do
        node_values="${node_values}                - ${node}"$'\n'
    done
    
    cat << AFFINITY_EOF
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/hostname
                operator: In
                values:
${node_values}
      tolerations:
      - key: "nautilus.io/reservation"
        operator: "Equal"
        value: "scinet"
        effect: "NoSchedule"
AFFINITY_EOF
}

# Function to check if namespace exists
check_namespace() {
    if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
        log_error "Namespace $NAMESPACE does not exist!"
        log_info "Please run ./deploy/01-deploy-credo-system.sh first to create the namespace and services"
        exit 1
    fi
    log_success "Namespace $NAMESPACE exists"
}

# Function to check if required services exist
check_services() {
    local services=("caltech-fl-server-service" "credo-elasticsearch-service")
    local missing=()
    
    for service in "${services[@]}"; do
        if ! kubectl get service -n "$NAMESPACE" "$service" >/dev/null 2>&1; then
            missing+=("$service")
        fi
    done
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_warning "Some required services are missing: ${missing[*]}"
        log_info "Jobs will be created but may fail if services are not available"
    else
        log_success "Required services are available"
    fi
}

# Function to create FL Server Job
create_fl_server_job() {
    log_info "Creating Caltech FL Server Job with SC25 affinity..."
    log_info "Resources: CPU ${CPU_REQUEST}-${CPU_LIMIT}, Memory ${MEMORY_REQUEST}-${MEMORY_LIMIT}"
    
    cat << EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: caltech-fl-server-job-sc25
  namespace: $NAMESPACE
  labels:
    app: caltech-fl-server
    component: federated-learning
    job-type: high-resource-sc25
spec:
  backoffLimit: $JOB_BACKOFF_LIMIT
  activeDeadlineSeconds: $JOB_ACTIVE_DEADLINE_SECONDS
  template:
    metadata:
      labels:
        app: caltech-fl-server
        component: federated-learning
        job-type: high-resource-sc25
    spec:
      restartPolicy: $JOB_RESTART_POLICY
$(generate_sc25_affinity_toleration)
      containers:
      - name: fl-server
        image: gitlab-registry.nrp-nautilus.io/cloud-ai-100/qaic-docker-images:vllm-latest
        ports:
        - containerPort: 5000
          name: fl-server
        - containerPort: 8888
          name: jupyter
        - containerPort: 8080
          name: web
        resources:
          requests:
            cpu: "$CPU_REQUEST"
            memory: "$MEMORY_REQUEST"
          limits:
            cpu: "$CPU_LIMIT"
            memory: "$MEMORY_LIMIT"
        env:
        - name: PYTHONUNBUFFERED
          value: "1"
        - name: TF_CPP_MIN_LOG_LEVEL
          value: "2"
        - name: PYTHONPATH
          value: "/workspace"
        - name: CREDO_TOKEN
          value: "$CREDO_TOKEN"
        - name: ELASTICSEARCH_URL
          value: "https://credo-elasticsearch-service:9200"
        command:
        - /bin/bash
        - -c
        - |
          set -e
          echo "=========================================="
          echo "Caltech FL Server Job (High-Resource SC25)"
          echo "=========================================="
          echo "Node: \$(hostname)"
          echo "CPU: \$(nproc) cores"
          echo "Memory: \$(free -h | grep Mem | awk '{print \$2}')"
          echo "Resources: CPU ${CPU_REQUEST}-${CPU_LIMIT}, Memory ${MEMORY_REQUEST}-${MEMORY_LIMIT}"
          echo ""
          echo "Installing dependencies..."
          pip install -q tensorflow scikit-learn flwr flask pyyaml requests elasticsearch scikit-image
          echo ""
          echo "Setting up federated learning environment..."
          mkdir -p /workspace/fl-server
          echo ""
          echo "Waiting for FL server script to be available..."
          # Wait up to 2 minutes for script to be copied
          for i in {1..60}; do
            if [ -f /workspace/fl-server/fl_server_caltech.py ]; then
              echo "FL server script found!"
              break
            fi
            if [ \$i -eq 60 ]; then
              echo "ERROR: FL server script not found after 2 minutes"
              echo "The script should be copied to /workspace/fl-server/fl_server_caltech.py"
              exit 1
            fi
            sleep 2
          done
          echo ""
          echo "Starting FL Server..."
          echo "Server will run on port 5000"
          echo ""
          cd /workspace/fl-server
          python3 /workspace/fl-server/fl_server_caltech.py
EOF
    
    log_success "Caltech FL Server Job created"
}

# Function to create Caltech FL Client Job
create_caltech_fl_client_job() {
    log_info "Creating Caltech FL Client Job with SC25 affinity..."
    log_info "Resources: CPU ${CPU_REQUEST}-${CPU_LIMIT}, Memory ${MEMORY_REQUEST}-${MEMORY_LIMIT}"
    
    cat << EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: caltech-fl-client-job-sc25
  namespace: $NAMESPACE
  labels:
    app: caltech-fl-client
    component: federated-learning-client
    site: caltech
    job-type: high-resource-sc25
spec:
  backoffLimit: $JOB_BACKOFF_LIMIT
  activeDeadlineSeconds: $JOB_ACTIVE_DEADLINE_SECONDS
  template:
    metadata:
      labels:
        app: caltech-fl-client
        component: federated-learning-client
        site: caltech
        job-type: high-resource-sc25
    spec:
      restartPolicy: $JOB_RESTART_POLICY
$(generate_sc25_affinity_toleration)
      containers:
      - name: fl-client
        image: gitlab-registry.nrp-nautilus.io/cloud-ai-100/qaic-docker-images:vllm-latest
        ports:
        - containerPort: 5000
          name: api
        - containerPort: 8888
          name: jupyter
        - containerPort: 8080
          name: web
        resources:
          requests:
            cpu: "$CPU_REQUEST"
            memory: "$MEMORY_REQUEST"
          limits:
            cpu: "$CPU_LIMIT"
            memory: "$MEMORY_LIMIT"
        env:
        - name: PYTHONUNBUFFERED
          value: "1"
        - name: TF_CPP_MIN_LOG_LEVEL
          value: "2"
        - name: PYTHONPATH
          value: "/workspace"
        - name: CREDO_TOKEN
          value: "$CREDO_TOKEN"
        - name: ELASTICSEARCH_URL
          value: "https://credo-elasticsearch-service:9200"
        - name: FL_SERVER_URL
          value: "caltech-fl-server-service:5000"
        - name: INSTITUTION_NAME
          value: "Caltech"
        - name: INSTITUTION_SITE
          value: "caltech"
        command:
        - /bin/bash
        - -c
        - |
          set -e
          echo "=========================================="
          echo "Caltech FL Client Job (High-Resource SC25)"
          echo "=========================================="
          echo "Node: \$(hostname)"
          echo "CPU: \$(nproc) cores"
          echo "Memory: \$(free -h | grep Mem | awk '{print \$2}')"
          echo "Resources: CPU ${CPU_REQUEST}-${CPU_LIMIT}, Memory ${MEMORY_REQUEST}-${MEMORY_LIMIT}"
          echo ""
          echo "Waiting for FL Server to be ready..."
          for i in {1..60}; do
            if nc -z caltech-fl-server-service 5000 2>/dev/null; then
              echo "FL Server is ready!"
              break
            fi
            echo "Waiting for FL Server... (\$i/60)"
            sleep 2
          done
          echo ""
          echo "Installing dependencies..."
          pip install -q tensorflow scikit-learn flwr flask pyyaml requests elasticsearch scikit-image pandas
          echo ""
          echo "Setting up federated learning client environment..."
          mkdir -p /workspace/fl-client
          echo ""
          echo "Waiting for FL client script to be available..."
          # Wait up to 2 minutes for script to be copied
          for i in {1..60}; do
            if [ -f /workspace/fl-client/fl_client_caltech.py ]; then
              echo "FL client script found!"
              break
            fi
            if [ \$i -eq 60 ]; then
              echo "ERROR: FL client script not found after 2 minutes"
              echo "The script should be copied to /workspace/fl-client/fl_client_caltech.py"
              exit 1
            fi
            sleep 2
          done
          echo ""
          echo "Starting Caltech FL Client (clusters 0-3)..."
          cd /workspace/fl-client
          python3 /workspace/fl-client/fl_client_caltech.py
EOF
    
    log_success "Caltech FL Client Job created"
}

# Function to create MIT FL Client Job
create_mit_fl_client_job() {
    log_info "Creating MIT FL Client Job with SC25 affinity..."
    log_info "Resources: CPU ${CPU_REQUEST}-${CPU_LIMIT}, Memory ${MEMORY_REQUEST}-${MEMORY_LIMIT}"
    
    cat << EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: mit-fl-client-job-sc25
  namespace: $NAMESPACE
  labels:
    app: mit-fl-client
    component: federated-learning-client
    site: mit
    job-type: high-resource-sc25
spec:
  backoffLimit: $JOB_BACKOFF_LIMIT
  activeDeadlineSeconds: $JOB_ACTIVE_DEADLINE_SECONDS
  template:
    metadata:
      labels:
        app: mit-fl-client
        component: federated-learning-client
        site: mit
        job-type: high-resource-sc25
    spec:
      restartPolicy: $JOB_RESTART_POLICY
$(generate_sc25_affinity_toleration)
      containers:
      - name: fl-client
        image: gitlab-registry.nrp-nautilus.io/cloud-ai-100/qaic-docker-images:vllm-latest
        ports:
        - containerPort: 5000
          name: api
        - containerPort: 8888
          name: jupyter
        - containerPort: 8080
          name: web
        resources:
          requests:
            cpu: "$CPU_REQUEST"
            memory: "$MEMORY_REQUEST"
          limits:
            cpu: "$CPU_LIMIT"
            memory: "$MEMORY_LIMIT"
        env:
        - name: PYTHONUNBUFFERED
          value: "1"
        - name: TF_CPP_MIN_LOG_LEVEL
          value: "2"
        - name: PYTHONPATH
          value: "/workspace"
        - name: CREDO_TOKEN
          value: "$CREDO_TOKEN"
        - name: ELASTICSEARCH_URL
          value: "https://credo-elasticsearch-service:9200"
        - name: FL_SERVER_URL
          value: "caltech-fl-server-service:5000"
        - name: INSTITUTION_NAME
          value: "MIT"
        - name: INSTITUTION_SITE
          value: "mit"
        command:
        - /bin/bash
        - -c
        - |
          set -e
          echo "=========================================="
          echo "MIT FL Client Job (High-Resource SC25)"
          echo "=========================================="
          echo "Node: \$(hostname)"
          echo "CPU: \$(nproc) cores"
          echo "Memory: \$(free -h | grep Mem | awk '{print \$2}')"
          echo "Resources: CPU ${CPU_REQUEST}-${CPU_LIMIT}, Memory ${MEMORY_REQUEST}-${MEMORY_LIMIT}"
          echo ""
          echo "Waiting for FL Server to be ready..."
          for i in {1..60}; do
            if nc -z caltech-fl-server-service 5000 2>/dev/null; then
              echo "FL Server is ready!"
              break
            fi
            echo "Waiting for FL Server... (\$i/60)"
            sleep 2
          done
          echo ""
          echo "Installing dependencies..."
          pip install -q tensorflow scikit-learn flwr flask pyyaml requests elasticsearch scikit-image pandas
          echo ""
          echo "Setting up federated learning client environment..."
          mkdir -p /workspace/fl-client
          echo ""
          echo "Waiting for FL client script to be available..."
          # Wait up to 2 minutes for script to be copied
          for i in {1..60}; do
            if [ -f /workspace/fl-client/fl_client_mit.py ]; then
              echo "FL client script found!"
              break
            fi
            if [ \$i -eq 60 ]; then
              echo "ERROR: FL client script not found after 2 minutes"
              echo "The script should be copied to /workspace/fl-client/fl_client_mit.py"
              exit 1
            fi
            sleep 2
          done
          echo ""
          echo "Starting MIT FL Client (clusters 4-6)..."
          cd /workspace/fl-client
          python3 /workspace/fl-client/fl_client_mit.py
EOF
    
    log_success "MIT FL Client Job created"
}

# Function to create UDel FL Client Job
create_udel_fl_client_job() {
    log_info "Creating UDel FL Client Job with SC25 affinity..."
    log_info "Resources: CPU ${CPU_REQUEST}-${CPU_LIMIT}, Memory ${MEMORY_REQUEST}-${MEMORY_LIMIT}"
    
    cat << EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: udel-fl-client-job-sc25
  namespace: $NAMESPACE
  labels:
    app: udel-fl-client
    component: federated-learning-client
    site: udel
    job-type: high-resource-sc25
spec:
  backoffLimit: $JOB_BACKOFF_LIMIT
  activeDeadlineSeconds: $JOB_ACTIVE_DEADLINE_SECONDS
  template:
    metadata:
      labels:
        app: udel-fl-client
        component: federated-learning-client
        site: udel
        job-type: high-resource-sc25
    spec:
      restartPolicy: $JOB_RESTART_POLICY
$(generate_sc25_affinity_toleration)
      containers:
      - name: fl-client
        image: gitlab-registry.nrp-nautilus.io/cloud-ai-100/qaic-docker-images:vllm-latest
        ports:
        - containerPort: 5000
          name: api
        - containerPort: 8888
          name: jupyter
        - containerPort: 8080
          name: web
        resources:
          requests:
            cpu: "$CPU_REQUEST"
            memory: "$MEMORY_REQUEST"
          limits:
            cpu: "$CPU_LIMIT"
            memory: "$MEMORY_LIMIT"
        env:
        - name: PYTHONUNBUFFERED
          value: "1"
        - name: TF_CPP_MIN_LOG_LEVEL
          value: "2"
        - name: PYTHONPATH
          value: "/workspace"
        - name: CREDO_TOKEN
          value: "$CREDO_TOKEN"
        - name: ELASTICSEARCH_URL
          value: "https://credo-elasticsearch-service:9200"
        - name: FL_SERVER_URL
          value: "caltech-fl-server-service:5000"
        - name: INSTITUTION_NAME
          value: "University of Delaware"
        - name: INSTITUTION_SITE
          value: "udel"
        command:
        - /bin/bash
        - -c
        - |
          set -e
          echo "=========================================="
          echo "UDel FL Client Job (High-Resource SC25)"
          echo "=========================================="
          echo "Node: \$(hostname)"
          echo "CPU: \$(nproc) cores"
          echo "Memory: \$(free -h | grep Mem | awk '{print \$2}')"
          echo "Resources: CPU ${CPU_REQUEST}-${CPU_LIMIT}, Memory ${MEMORY_REQUEST}-${MEMORY_LIMIT}"
          echo ""
          echo "Waiting for FL Server to be ready..."
          for i in {1..60}; do
            if nc -z caltech-fl-server-service 5000 2>/dev/null; then
              echo "FL Server is ready!"
              break
            fi
            echo "Waiting for FL Server... (\$i/60)"
            sleep 2
          done
          echo ""
          echo "Installing dependencies..."
          pip install -q tensorflow scikit-learn flwr flask pyyaml requests elasticsearch scikit-image pandas
          echo ""
          echo "Setting up federated learning client environment..."
          mkdir -p /workspace/fl-client
          echo ""
          echo "Waiting for FL client script to be available..."
          # Wait up to 2 minutes for script to be copied
          for i in {1..60}; do
            if [ -f /workspace/fl-client/fl_client_udel.py ]; then
              echo "FL client script found!"
              break
            fi
            if [ \$i -eq 60 ]; then
              echo "ERROR: FL client script not found after 2 minutes"
              echo "The script should be copied to /workspace/fl-client/fl_client_udel.py"
              exit 1
            fi
            sleep 2
          done
          echo ""
          echo "Starting UDel FL Client (clusters 7-9)..."
          cd /workspace/fl-client
          python3 /workspace/fl-client/fl_client_udel.py
EOF
    
    log_success "UDel FL Client Job created"
}

# Function to show job status
show_job_status() {
    log_info "Federated Learning Job Status:"
    echo ""
    kubectl get jobs -n "$NAMESPACE" -l job-type=high-resource-sc25 -o wide
    echo ""
    log_info "Job Pods:"
    kubectl get pods -n "$NAMESPACE" -l job-type=high-resource-sc25 -o wide
    echo ""
}

# Function to show job logs
show_job_logs() {
    local job_name=$1
    local pod_name=$(kubectl get pods -n "$NAMESPACE" -l job-name="$job_name" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    if [ -z "$pod_name" ]; then
        log_warning "No pod found for job: $job_name"
        return 1
    fi
    
    log_info "Showing logs for $job_name (pod: $pod_name):"
    kubectl logs -n "$NAMESPACE" "$pod_name" --tail=50 -f
}

# Function to copy FL scripts to job pods
copy_fl_scripts_to_jobs() {
    log_info "Copying federated learning scripts to job pods..."
    
    # Wait for pods to be running
    log_info "Waiting for pods to be ready..."
    local max_wait=60
    local waited=0
    while [ $waited -lt $max_wait ]; do
        local running_pods=$(kubectl get pods -n "$NAMESPACE" -l job-type=high-resource-sc25 --field-selector=status.phase=Running -o jsonpath='{.items[*].metadata.name}' 2>/dev/null | wc -w)
        if [ "$running_pods" -gt 0 ]; then
            break
        fi
        sleep 2
        waited=$((waited + 2))
    done
    
    # Get pod names
    local server_pod=$(kubectl get pods -n "$NAMESPACE" -l job-name=caltech-fl-server-job-sc25 --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    local caltech_pod=$(kubectl get pods -n "$NAMESPACE" -l job-name=caltech-fl-client-job-sc25 --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    local mit_pod=$(kubectl get pods -n "$NAMESPACE" -l job-name=mit-fl-client-job-sc25 --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    local udel_pod=$(kubectl get pods -n "$NAMESPACE" -l job-name=udel-fl-client-job-sc25 --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    
    # Copy FL server script
    if [ ! -z "$server_pod" ] && [ -f "./scripts_example/fl_server_caltech.py" ]; then
        log_info "Copying FL server script to $server_pod..."
        kubectl cp ./scripts_example/fl_server_caltech.py "$NAMESPACE/$server_pod:/workspace/fl-server/" 2>/dev/null && \
            log_success "FL server script copied" || log_warning "Could not copy FL server script"
    fi
    
    # Copy FL client scripts
    if [ ! -z "$caltech_pod" ] && [ -f "./scripts_example/fl_client_caltech.py" ]; then
        log_info "Copying Caltech FL client script to $caltech_pod..."
        kubectl cp ./scripts_example/fl_client_caltech.py "$NAMESPACE/$caltech_pod:/workspace/fl-client/" 2>/dev/null && \
            log_success "Caltech FL client script copied" || log_warning "Could not copy Caltech FL client script"
    fi
    
    if [ ! -z "$mit_pod" ] && [ -f "./scripts_example/fl_client_mit.py" ]; then
        log_info "Copying MIT FL client script to $mit_pod..."
        kubectl cp ./scripts_example/fl_client_mit.py "$NAMESPACE/$mit_pod:/workspace/fl-client/" 2>/dev/null && \
            log_success "MIT FL client script copied" || log_warning "Could not copy MIT FL client script"
    fi
    
    if [ ! -z "$udel_pod" ] && [ -f "./scripts_example/fl_client_udel.py" ]; then
        log_info "Copying UDel FL client script to $udel_pod..."
        kubectl cp ./scripts_example/fl_client_udel.py "$NAMESPACE/$udel_pod:/workspace/fl-client/" 2>/dev/null && \
            log_success "UDel FL client script copied" || log_warning "Could not copy UDel FL client script"
    fi
    
    log_success "Script copying complete"
}

# Function to delete all high-resource SC25 jobs
delete_jobs() {
    log_info "Deleting all high-resource SC25 federated learning jobs..."
    kubectl delete jobs -n "$NAMESPACE" -l job-type=high-resource-sc25 --ignore-not-found=true
    log_success "Jobs deleted"
}

# Main function
main() {
    echo "=========================================="
    echo "CREDO High-Resource FL Jobs (SC25)"
    echo "=========================================="
    echo ""
    log_info "Configuration:"
    echo "  Namespace: $NAMESPACE"
    echo "  SC25 Nodes: $SC25_NODES"
    echo "  CPU: ${CPU_REQUEST}-${CPU_LIMIT} cores"
    echo "  Memory: ${MEMORY_REQUEST}-${MEMORY_LIMIT}"
    echo "  Job Restart Policy: $JOB_RESTART_POLICY"
    echo "  Job Backoff Limit: $JOB_BACKOFF_LIMIT"
    echo "  Job Timeout: ${JOB_ACTIVE_DEADLINE_SECONDS}s"
    echo ""
    
    # Check prerequisites
    check_namespace
    check_services
    
    # Create jobs
    echo ""
    log_info "Creating high-resource federated learning jobs with SC25 node affinity..."
    echo ""
    
    create_fl_server_job
    sleep 2
    
    create_caltech_fl_client_job
    sleep 2
    
    create_mit_fl_client_job
    sleep 2
    
    create_udel_fl_client_job
    
    echo ""
    log_success "All high-resource federated learning jobs created!"
    echo ""
    
    # Copy scripts to running pods
    copy_fl_scripts_to_jobs
    
    echo ""
    # Show status
    show_job_status
    
    echo ""
    log_info "Useful commands:"
    echo "  # Check job status:"
    echo "  kubectl get jobs -n $NAMESPACE -l job-type=high-resource-sc25"
    echo ""
    echo "  # Check pod status:"
    echo "  kubectl get pods -n $NAMESPACE -l job-type=high-resource-sc25"
    echo ""
    echo "  # View logs for a specific job:"
    echo "  kubectl logs -n $NAMESPACE -l job-name=caltech-fl-server-job-sc25 -f"
    echo "  kubectl logs -n $NAMESPACE -l job-name=caltech-fl-client-job-sc25 -f"
    echo "  kubectl logs -n $NAMESPACE -l job-name=mit-fl-client-job-sc25 -f"
    echo "  kubectl logs -n $NAMESPACE -l job-name=udel-fl-client-job-sc25 -f"
    echo ""
    echo "  # Delete all jobs:"
    echo "  kubectl delete jobs -n $NAMESPACE -l job-type=high-resource-sc25"
    echo ""
    echo "  # Or use this script with --delete flag:"
    echo "  $0 --delete"
    echo ""
}

# Handle command line arguments
case "${1:-}" in
    --delete|--remove)
        delete_jobs
        ;;
    --status)
        show_job_status
        ;;
    --logs)
        if [ -z "${2:-}" ]; then
            log_error "Please specify job name (e.g., caltech-fl-server-job-sc25)"
            exit 1
        fi
        show_job_logs "$2"
        ;;
    --help|-h)
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  (no args)     Create high-resource FL jobs with SC25 affinity"
        echo "  --delete      Delete all high-resource SC25 FL jobs"
        echo "  --status      Show job status"
        echo "  --logs JOB    Show logs for a specific job"
        echo "  --help        Show this help message"
        echo ""
        echo "Environment Variables:"
        echo "  SC25_NODES              Comma-separated list of SC25 nodes (default: r640-01.sc25.nrp-nautilus.io)"
        echo "  CPU_REQUEST             CPU request (default: 8)"
        echo "  CPU_LIMIT               CPU limit (default: 16)"
        echo "  MEMORY_REQUEST          Memory request (default: 32Gi)"
        echo "  MEMORY_LIMIT            Memory limit (default: 64Gi)"
        echo "  JOB_RESTART_POLICY      Job restart policy (default: Never)"
        echo "  JOB_BACKOFF_LIMIT       Job backoff limit (default: 3)"
        echo "  JOB_ACTIVE_DEADLINE_SECONDS  Job timeout in seconds (default: 7200)"
        echo ""
        echo "Examples:"
        echo "  # Create jobs with default settings"
        echo "  $0"
        echo ""
        echo "  # Create jobs on multiple SC25 nodes"
        echo "  SC25_NODES='r640-01.sc25.nrp-nautilus.io,rc3-sc-13.sc25.nrp-nautilus.io' $0"
        echo ""
        echo "  # Create jobs with custom resources"
        echo "  CPU_REQUEST=16 CPU_LIMIT=32 MEMORY_REQUEST=64Gi MEMORY_LIMIT=128Gi $0"
        echo ""
        exit 0
        ;;
    "")
        main
        ;;
    *)
        log_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac

