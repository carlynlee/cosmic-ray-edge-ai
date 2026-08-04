#!/bin/bash

# CREDO Three-Pod System - Complete Deployment Script
# This script creates and manages the three-pod architecture for CREDO federated learning

set -euo pipefail

# Configuration
NAMESPACE="cblee-credo"
CREDO_TOKEN="e26fcf245c7b96a4c8daf5b72ddc17d34891ea0e68b10bd396e547ec74917656"

# SC25 Node Configuration (optional - set to use specific SC25 node)
# Set SC25_NODE_NAME to the hostname of the SC25 node, or leave empty to use any available node
SC25_NODE_NAME="${SC25_NODE_NAME:-}"

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

# Function to generate node affinity and toleration YAML for SC25 node
generate_sc25_affinity_toleration() {
    if [ -n "$SC25_NODE_NAME" ]; then
        cat << AFFINITY_EOF
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/hostname
                operator: In
                values:
                - $SC25_NODE_NAME
      tolerations:
      - key: "nautilus.io/reservation"
        operator: "Equal"
        value: "scinet"
        effect: "NoSchedule"
AFFINITY_EOF
    fi
}

# Function to create namespace
create_namespace() {
    log_info "Creating namespace: $NAMESPACE"
    
    if kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
        log_warning "Namespace $NAMESPACE already exists"
    else
        kubectl create namespace "$NAMESPACE"
        log_success "Namespace $NAMESPACE created"
    fi
}

# Function to create CREDO Caltech Server pod
create_credo_server() {
    log_info "Creating CREDO Caltech Server pod..."
    
    cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: credo-caltech-server
  namespace: $NAMESPACE
  labels:
    app: credo-caltech-server
    component: data-fetcher
spec:
  replicas: 1
  selector:
    matchLabels:
      app: credo-caltech-server
  template:
    metadata:
      labels:
        app: credo-caltech-server
        component: data-fetcher
    spec:
      containers:
      - name: credo-server
        image: gitlab-registry.nrp-nautilus.io/cloud-ai-100/qaic-docker-images:vllm-latest
        ports:
        - containerPort: 8888
        - containerPort: 5000
        - containerPort: 8080
        resources:
          requests:
            cpu: "4"
            memory: "16Gi"
            nvidia.com/gpu: "1"
          limits:
            cpu: "8"
            memory: "32Gi"
            nvidia.com/gpu: "1"
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
        - name: CREDO_SERVER_TYPE
          value: "caltech"
        command:
        - /bin/bash
        - -c
        - |
          echo "Starting CREDO Caltech Server..."
          echo "Installing dependencies..."
          pip install tensorflow scikit-learn elasticsearch opencv-python matplotlib seaborn flwr flask sentence-transformers requests numpy pandas
          echo "Setting up CREDO data exporter..."
          mkdir -p /workspace/data-exporter
          echo "CREDO Caltech Server ready!"
          sleep infinity
---
apiVersion: v1
kind: Service
metadata:
  name: credo-caltech-server-service
  namespace: $NAMESPACE
  labels:
    app: credo-caltech-server
spec:
  selector:
    app: credo-caltech-server
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
    
    log_success "CREDO Caltech Server deployment created"
}

# Function to create Elasticsearch pod
create_elasticsearch() {
    log_info "Creating Elasticsearch pod..."
    
    cat << EOF | kubectl apply -f -
apiVersion: elasticsearch.k8s.elastic.co/v1
kind: Elasticsearch
metadata:
  name: credo-elasticsearch
  namespace: $NAMESPACE
spec:
  version: 8.15.1
  nodeSets:
  - name: default
    count: 1
    config:
      node.roles: ["master", "data", "ingest"]
      node.store.allow_mmap: false
    podTemplate:
      spec:
        containers:
        - name: elasticsearch
          resources:
            requests:
              memory: 2Gi
              cpu: 100m
            limits:
              memory: 2Gi
              cpu: 100m
          env:
          - name: ES_JAVA_OPTS
            value: "-Xms1g -Xmx1g"
  http:
    tls:
      selfSignedCertificate:
        subjectAltNames:
        - ip: 127.0.0.1
        - dns: localhost
---
apiVersion: v1
kind: Service
metadata:
  name: credo-elasticsearch-service
  namespace: $NAMESPACE
  labels:
    app: credo-elasticsearch
spec:
  selector:
    elasticsearch.k8s.elastic.co/cluster-name: credo-elasticsearch
  ports:
  - name: http
    port: 9200
    targetPort: 9200
  - name: transport
    port: 9300
    targetPort: 9300
  type: ClusterIP
EOF
    
    log_success "Elasticsearch deployment created"
}

# Function to create Caltech FL Client pod
create_caltech_fl_client() {
    log_info "Creating Caltech FL Client pod..."
    
    cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: caltech-fl-client
  namespace: $NAMESPACE
  labels:
    app: caltech-fl-client
    component: federated-learning-client
    site: caltech
spec:
  replicas: 1
  selector:
    matchLabels:
      app: caltech-fl-client
  template:
    metadata:
      labels:
        app: caltech-fl-client
        component: federated-learning-client
        site: caltech
    spec:
$(generate_sc25_affinity_toleration)
      containers:
      - name: fl-client
        image: gitlab-registry.nrp-nautilus.io/cloud-ai-100/qaic-docker-images:vllm-latest
        ports:
        - containerPort: 8888
        - containerPort: 5000
        - containerPort: 8080
        resources:
          requests:
            cpu: "4"
            memory: "16Gi"
          limits:
            cpu: "8"
            memory: "32Gi"
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
          echo "Starting Caltech FL Client..."
          echo "Installing dependencies..."
          pip install tensorflow scikit-learn flwr flask pyyaml requests elasticsearch scikit-image pandas
          echo "Setting up federated learning client environment..."
          mkdir -p /workspace/fl-client
          echo "Caltech FL Client ready!"
          echo "To start FL client, run: python3 /workspace/fl-client/fl_client_caltech.py"
          sleep infinity
---
apiVersion: v1
kind: Service
metadata:
  name: caltech-fl-client-service
  namespace: $NAMESPACE
  labels:
    app: caltech-fl-client
    site: caltech
spec:
  selector:
    app: caltech-fl-client
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
    
    log_success "Caltech FL Client deployment created"
}

# Function to create Caltech FL Server pod
create_fl_server() {
    log_info "Creating Caltech FL Server pod..."
    
    cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: caltech-fl-server
  namespace: $NAMESPACE
  labels:
    app: caltech-fl-server
    component: federated-learning
spec:
  replicas: 1
  selector:
    matchLabels:
      app: caltech-fl-server
  template:
    metadata:
      labels:
        app: caltech-fl-server
        component: federated-learning
    spec:
$(generate_sc25_affinity_toleration)
      containers:
      - name: fl-server
        image: gitlab-registry.nrp-nautilus.io/cloud-ai-100/qaic-docker-images:vllm-latest
        ports:
        - containerPort: 8888
        - containerPort: 5000
        - containerPort: 8080
        resources:
          requests:
            cpu: "4"
            memory: "16Gi"
          limits:
            cpu: "8"
            memory: "32Gi"
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
          echo "Starting Caltech FL Server..."
          echo "Installing dependencies..."
          pip install tensorflow scikit-learn flwr flask pyyaml requests elasticsearch scikit-image
          echo "Setting up federated learning environment..."
          mkdir -p /workspace/fl-server
          echo "Caltech FL Server ready!"
          echo "To start FL server, run: python3 /workspace/fl-server/fl_server_caltech.py"
          sleep infinity
---
apiVersion: v1
kind: Service
metadata:
  name: caltech-fl-server-service
  namespace: $NAMESPACE
  labels:
    app: caltech-fl-server
spec:
  selector:
    app: caltech-fl-server
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
    
    log_success "Caltech FL Server deployment created"
}

# Function to create MIT FL Client pod
create_mit_fl_client() {
    log_info "Creating MIT FL Client pod..."
    
    cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mit-fl-client
  namespace: $NAMESPACE
  labels:
    app: mit-fl-client
    component: federated-learning-client
    site: mit
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mit-fl-client
  template:
    metadata:
      labels:
        app: mit-fl-client
        component: federated-learning-client
        site: mit
    spec:
$(generate_sc25_affinity_toleration)
      containers:
      - name: fl-client
        image: gitlab-registry.nrp-nautilus.io/cloud-ai-100/qaic-docker-images:vllm-latest
        ports:
        - containerPort: 8888
        - containerPort: 5000
        - containerPort: 8080
        resources:
          requests:
            cpu: "4"
            memory: "16Gi"
          limits:
            cpu: "8"
            memory: "32Gi"
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
          echo "Starting MIT FL Client..."
          echo "Installing dependencies..."
          pip install tensorflow scikit-learn flwr flask pyyaml requests elasticsearch scikit-image pandas
          echo "Setting up federated learning client environment..."
          mkdir -p /workspace/fl-client
          echo "MIT FL Client ready!"
          echo "To start FL client, run: python3 /workspace/fl-client/fl_client_mit.py"
          sleep infinity
---
apiVersion: v1
kind: Service
metadata:
  name: mit-fl-client-service
  namespace: $NAMESPACE
  labels:
    app: mit-fl-client
    site: mit
spec:
  selector:
    app: mit-fl-client
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
    
    log_success "MIT FL Client deployment created"
}

# Function to create UDel FL Client pod
create_udel_fl_client() {
    log_info "Creating UDel FL Client pod..."
    
    cat << EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: udel-fl-client
  namespace: $NAMESPACE
  labels:
    app: udel-fl-client
    component: federated-learning-client
    site: udel
spec:
  replicas: 1
  selector:
    matchLabels:
      app: udel-fl-client
  template:
    metadata:
      labels:
        app: udel-fl-client
        component: federated-learning-client
        site: udel
    spec:
$(generate_sc25_affinity_toleration)
      containers:
      - name: fl-client
        image: gitlab-registry.nrp-nautilus.io/cloud-ai-100/qaic-docker-images:vllm-latest
        ports:
        - containerPort: 8888
        - containerPort: 5000
        - containerPort: 8080
        resources:
          requests:
            cpu: "4"
            memory: "16Gi"
          limits:
            cpu: "8"
            memory: "32Gi"
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
          echo "Starting UDel FL Client..."
          echo "Installing dependencies..."
          pip install tensorflow scikit-learn flwr flask pyyaml requests elasticsearch scikit-image pandas
          echo "Setting up federated learning client environment..."
          mkdir -p /workspace/fl-client
          echo "UDel FL Client ready!"
          echo "To start FL client, run: python3 /workspace/fl-client/fl_client_udel.py"
          sleep infinity
---
apiVersion: v1
kind: Service
metadata:
  name: udel-fl-client-service
  namespace: $NAMESPACE
  labels:
    app: udel-fl-client
    site: udel
spec:
  selector:
    app: udel-fl-client
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
    
    log_success "UDel FL Client deployment created"
}

# Function to wait for pods to be ready
wait_for_pods() {
    log_info "Waiting for pods to be ready..."
    
    # Wait for CREDO server
    kubectl wait --for=condition=ready pod -l app=credo-caltech-server -n "$NAMESPACE" --timeout=300s
    log_success "CREDO Caltech Server is ready"
    
    # Wait for Elasticsearch
    kubectl wait --for=condition=ready pod -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -n "$NAMESPACE" --timeout=600s
    log_success "Elasticsearch is ready"
    
    # Wait for FL server
    kubectl wait --for=condition=ready pod -l app=caltech-fl-server -n "$NAMESPACE" --timeout=300s
    log_success "Caltech FL Server is ready"
    
    # Wait for Caltech FL client
    kubectl wait --for=condition=ready pod -l app=caltech-fl-client -n "$NAMESPACE" --timeout=300s
    log_success "Caltech FL Client is ready"
    
    # Wait for MIT FL client
    kubectl wait --for=condition=ready pod -l app=mit-fl-client -n "$NAMESPACE" --timeout=300s
    log_success "MIT FL Client is ready"
    
    # Wait for UDel FL client
    kubectl wait --for=condition=ready pod -l app=udel-fl-client -n "$NAMESPACE" --timeout=300s
    log_success "UDel FL Client is ready"
}

# Function to setup CREDO data exporter
setup_credo_exporter() {
    log_info "Setting up CREDO data exporter..."
    
    # Get the CREDO server pod name
    local credo_pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-caltech-server -o jsonpath='{.items[0].metadata.name}')
    
    # Copy the data exporter
    kubectl cp ./data-exporter/credo-data-exporter.py "$NAMESPACE/$credo_pod:/workspace/data-exporter/"
    
    log_success "CREDO data exporter copied to server"
}

# Function to setup federated learning scripts
setup_fl_scripts() {
    log_info "Setting up federated learning scripts..."
    
    # Get pod names
    local fl_server_pod=$(kubectl get pods -n "$NAMESPACE" -l app=caltech-fl-server -o jsonpath='{.items[0].metadata.name}')
    local caltech_client_pod=$(kubectl get pods -n "$NAMESPACE" -l app=caltech-fl-client -o jsonpath='{.items[0].metadata.name}')
    local mit_client_pod=$(kubectl get pods -n "$NAMESPACE" -l app=mit-fl-client -o jsonpath='{.items[0].metadata.name}')
    local udel_client_pod=$(kubectl get pods -n "$NAMESPACE" -l app=udel-fl-client -o jsonpath='{.items[0].metadata.name}')
    
    # Copy FL server script to Caltech FL server
    if [ ! -z "$fl_server_pod" ]; then
        kubectl cp ./scripts_example/fl_server_caltech.py "$NAMESPACE/$fl_server_pod:/workspace/fl-server/" 2>/dev/null || log_warning "Could not copy FL server script"
        log_success "FL server script copied to Caltech pod"
    fi
    
    # Copy FL client scripts to all three sites
    if [ ! -z "$caltech_client_pod" ]; then
        kubectl cp ./scripts_example/fl_client_caltech.py "$NAMESPACE/$caltech_client_pod:/workspace/fl-client/" 2>/dev/null || log_warning "Could not copy Caltech FL client script"
        log_success "Caltech FL client script copied"
    fi
    
    if [ ! -z "$mit_client_pod" ]; then
        kubectl cp ./scripts_example/fl_client_mit.py "$NAMESPACE/$mit_client_pod:/workspace/fl-client/" 2>/dev/null || log_warning "Could not copy MIT FL client script"
        log_success "MIT FL client script copied"
    fi
    
    if [ ! -z "$udel_client_pod" ]; then
        kubectl cp ./scripts_example/fl_client_udel.py "$NAMESPACE/$udel_client_pod:/workspace/fl-client/" 2>/dev/null || log_warning "Could not copy UDel FL client script"
        log_success "UDel FL client script copied"
    fi
    
    log_success "Federated learning scripts setup complete"
}

# Function to populate Elasticsearch with real CREDO data
populate_elasticsearch() {
    log_info "Populating Elasticsearch with real CREDO data..."
    
    # Get pod names
    local credo_pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-caltech-server -o jsonpath='{.items[0].metadata.name}')
    local es_pod=$(kubectl get pods -n "$NAMESPACE" -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}')
    
    # Use CREDO server pod to fetch data, then copy directly to Elasticsearch pod
    log_info "Fetching real CREDO data from CREDO.science..."
    kubectl exec -n "$NAMESPACE" "$credo_pod" -- bash -c "
        export CREDO_TOKEN='$CREDO_TOKEN'
        cd /workspace/data-exporter
        python3 credo-data-exporter.py --token \$CREDO_TOKEN --dir /tmp/credo-data-temp --max-chunk-size 1000 --data-type detection
    " || log_warning "Data export may have timed out, but some data may have been downloaded"
    
    # Copy data directly to Elasticsearch pod (no local temp directory needed)
    log_info "Copying data directly to Elasticsearch pod..."
    kubectl cp "$NAMESPACE/$credo_pod:/tmp/credo-data-temp/" "$NAMESPACE/$es_pod:/workspace/credo-data/" || log_warning "Failed to copy data to Elasticsearch pod"
    
    # Get Elasticsearch password
    local es_password=$(kubectl get secret credo-elasticsearch-es-elastic-user -n "$NAMESPACE" -o jsonpath='{.data.elastic}' | base64 -d)
    
    # Create Elasticsearch index
    log_info "Creating Elasticsearch index..."
    kubectl exec -n "$NAMESPACE" "$es_pod" -- curl -k -u "elastic:$es_password" -X PUT "https://localhost:9200/credo-detections" -H "Content-Type: application/json" -d '{
        "mappings": {
            "properties": {
                "timestamp": {"type": "date"},
                "device_id": {"type": "keyword"},
                "latitude": {"type": "float"},
                "longitude": {"type": "float"},
                "altitude": {"type": "float"},
                "particle_type": {"type": "keyword"},
                "energy": {"type": "float"},
                "source": {"type": "keyword"},
                "time_received": {"type": "long"}
            }
        }
    }'
    
    # Index the data
    log_info "Indexing CREDO data into Elasticsearch..."
    kubectl exec -n "$NAMESPACE" "$es_pod" -- bash -c "
        ES_URL=\"https://localhost:9200\"
        ES_USER=\"elastic\"
        ES_PASSWORD=\"$es_password\"
        
        doc_id=1
        for file in /workspace/credo-data/detections/*.json; do
            if [[ -f \"\$file\" ]]; then
                echo \"Processing \$(basename \"\$file\")...\"
                
                # Extract device IDs and index them
                grep -o \"\\\"device_id\\\": [0-9]*\" \"\$file\" | while read -r line; do
                    if [[ \$line =~ \\\"device_id\\\":\ ([0-9]+) ]]; then
                        device_id=\"\${BASH_REMATCH[1]}\"
                        
                        # Create document
                        doc=\"{
                            \\\"timestamp\\\": \\\"2018-05-11T00:00:00+00:00\\\",
                            \\\"device_id\\\": \\\"\$device_id\\\",
                            \\\"latitude\\\": 0.0,
                            \\\"longitude\\\": 0.0,
                            \\\"altitude\\\": 0.0,
                            \\\"particle_type\\\": \\\"cosmic_ray\\\",
                            \\\"energy\\\": 0,
                            \\\"source\\\": \\\"credo.science\\\",
                            \\\"time_received\\\": 1526043300000,
                            \\\"doc_id\\\": \$doc_id
                        }\"
                        
                        # Index document
                        curl -k -u \"\$ES_USER:\$ES_PASSWORD\" -X POST \"\$ES_URL/credo-detections/_doc\" \
                            -H \"Content-Type: application/json\" \
                            -d \"\$doc\" \
                            --max-time 10 \
                            --connect-timeout 5 \
                            > /dev/null 2>&1
                        
                        doc_id=\$((doc_id + 1))
                    fi
                done
            fi
        done
        
        echo \"Data indexing completed!\"
    "
    
    # Verify the data
    log_info "Verifying indexed data..."
    local count=$(kubectl exec -n "$NAMESPACE" "$es_pod" -- curl -k -u "elastic:$es_password" -X GET "https://localhost:9200/credo-detections/_count" 2>/dev/null | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
    
    if [[ -n "$count" ]]; then
        log_success "Successfully indexed $count CREDO detection documents"
    else
        log_warning "Could not retrieve document count"
    fi
    
    # Clean up temporary files
    rm -rf ./credo-data-temp/ 2>/dev/null || true
}

# Function to show system status
show_status() {
    log_info "System Status:"
    echo ""
    kubectl get pods -n "$NAMESPACE" -o wide
    echo ""
    kubectl get services -n "$NAMESPACE"
    echo ""
    
    # Show Elasticsearch data count
    local es_pod=$(kubectl get pods -n "$NAMESPACE" -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
    if [[ -n "$es_pod" ]]; then
        local es_password=$(kubectl get secret credo-elasticsearch-es-elastic-user -n "$NAMESPACE" -o jsonpath='{.data.elastic}' | base64 -d)
        log_info "Elasticsearch document count:"
        kubectl exec -n "$NAMESPACE" "$es_pod" -- curl -k -u "elastic:$es_password" -X GET "https://localhost:9200/credo-detections/_count" 2>/dev/null || echo "Elasticsearch not ready yet"
    fi
}

# Main function
main() {
    log_info "Starting CREDO Three-Pod System Deployment..."
    log_info "Namespace: $NAMESPACE"
    
    if [ -n "$SC25_NODE_NAME" ]; then
        log_info "SC25 Node Configuration: Pods will be scheduled on node: $SC25_NODE_NAME"
        log_info "Using toleration for: nautilus.io/reservation=scinet"
    else
        log_info "No SC25 node specified - pods will be scheduled on any available node"
        log_info "To use SC25 node, set: export SC25_NODE_NAME=<node-hostname>"
    fi
    
    # Create all components
    create_namespace
    create_credo_server
    create_elasticsearch
    create_fl_server
    create_caltech_fl_client
    create_mit_fl_client
    create_udel_fl_client
    
    # Wait for pods to be ready
    wait_for_pods
    
    # Setup and populate
    setup_credo_exporter
    populate_elasticsearch
    setup_fl_scripts
    
    # Show final status
    show_status
    
    log_success "CREDO Three-Pod System deployment completed!"
    
    cat << EOF

Next steps:
1. Access the CREDO Caltech Server:
   kubectl port-forward -n $NAMESPACE svc/credo-caltech-server-service 8888:8888

2. Access the Caltech FL Server:
   kubectl port-forward -n $NAMESPACE svc/caltech-fl-server-service 5000:5000

3. Access MIT FL Client:
   kubectl port-forward -n $NAMESPACE svc/mit-fl-client-service 8888:8888

4. Access UDel FL Client:
   kubectl port-forward -n $NAMESPACE svc/udel-fl-client-service 8888:8888

5. Access Elasticsearch:
   kubectl port-forward -n $NAMESPACE svc/credo-elasticsearch-service 9200:9200

6. Start federated learning:
   
   a. Start FL server on Caltech pod:
      kubectl exec -n $NAMESPACE -it <caltech-fl-server-pod> -- python3 /workspace/fl-server/fl_server_caltech.py &
   
   b. Start Caltech FL client (clusters 0-3):
      kubectl exec -n $NAMESPACE -it <caltech-fl-client-pod> -- python3 /workspace/fl-client/fl_client_caltech.py &
   
   c. Start MIT FL client (clusters 4-6):
      kubectl exec -n $NAMESPACE -it <mit-fl-client-pod> -- python3 /workspace/fl-client/fl_client_mit.py &
   
   d. Start UDel FL client (clusters 7-9):
      kubectl exec -n $NAMESPACE -it <udel-fl-client-pod> -- python3 /workspace/fl-client/fl_client_udel.py

System is ready for SC25 NRE demo with three-site federated learning!

EOF
}

# Run main function only if script is executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main
fi
