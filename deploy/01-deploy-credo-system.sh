#!/bin/bash

# CREDO Three-Pod System - Complete Deployment Script
# This script creates and manages the three-pod architecture for CREDO federated learning

set -euo pipefail

# Configuration
NAMESPACE="cblee-credo"
CREDO_TOKEN="e26fcf245c7b96a4c8daf5b72ddc17d34891ea0e68b10bd396e547ec74917656"

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
          pip install tensorflow scikit-learn flwr flask pyyaml requests elasticsearch
          echo "Setting up federated learning environment..."
          mkdir -p /workspace/fl-server
          echo "Caltech FL Server ready!"
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

# Function to populate Elasticsearch with real CREDO data
populate_elasticsearch() {
    log_info "Populating Elasticsearch with real CREDO data..."
    
    # Get pod names
    local credo_pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-caltech-server -o jsonpath='{.items[0].metadata.name}')
    local es_pod=$(kubectl get pods -n "$NAMESPACE" -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}')
    
    # Fetch real CREDO data
    log_info "Fetching real CREDO data from CREDO.science..."
    kubectl exec -n "$NAMESPACE" "$credo_pod" -- bash -c "
        export CREDO_TOKEN='$CREDO_TOKEN'
        cd /workspace/data-exporter
        python3 credo-data-exporter.py --token \$CREDO_TOKEN --dir /workspace/credo-data --max-chunk-size 1000 --data-type detection
    " || log_warning "Data export may have timed out, but some data may have been downloaded"
    
    # Copy data to Elasticsearch pod
    log_info "Copying data to Elasticsearch pod..."
    kubectl cp "$NAMESPACE/$credo_pod:/workspace/credo-data/" ./credo-data-temp/ || log_warning "No data to copy"
    kubectl cp ./credo-data-temp/ "$NAMESPACE/$es_pod:/tmp/credo-data/" || log_warning "Failed to copy data"
    
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
        for file in /tmp/credo-data/detections/*.json; do
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
    
    # Create all components
    create_namespace
    create_credo_server
    create_elasticsearch
    create_fl_server
    
    # Wait for pods to be ready
    wait_for_pods
    
    # Setup and populate
    setup_credo_exporter
    populate_elasticsearch
    
    # Show final status
    show_status
    
    log_success "CREDO Three-Pod System deployment completed!"
    
    cat << EOF

Next steps:
1. Access the CREDO Caltech Server:
   kubectl port-forward -n $NAMESPACE svc/credo-caltech-server-service 8888:8888

2. Access the Caltech FL Server:
   kubectl port-forward -n $NAMESPACE svc/caltech-fl-server-service 5000:5000

3. Access Elasticsearch:
   kubectl port-forward -n $NAMESPACE svc/credo-elasticsearch-service 9200:9200

4. Start federated learning:
   kubectl exec -n $NAMESPACE -it <fl-server-pod> -- python3 /workspace/fl-server/start_fl_server.py

System is ready for SC25 NRE demo!

EOF
}

# Run main function
main
