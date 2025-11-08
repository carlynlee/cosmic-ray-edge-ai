#!/bin/bash

# CREDO Data Indexing Helper Functions
# This script provides reusable functions for indexing CREDO data using the Python infrastructure

set -e

# Configuration - Use environment variables with defaults
NAMESPACE="${CREDO_NAMESPACE:-cblee-credo}"
ES_POD="${CREDO_ES_POD:-credo-elasticsearch-es-default-0}"
ES_URL="${CREDO_ES_URL:-https://localhost:9200}"
ES_USER="${CREDO_ES_USER:-elastic}"

# Get Elasticsearch password from Kubernetes secret
get_elasticsearch_password() {
    kubectl get secret credo-elasticsearch-es-elastic-user -n "$NAMESPACE" -o jsonpath='{.data.elastic}' | base64 -d
}

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

# Function to prepare data processor environment for remote Elasticsearch
prepare_data_processor_for_remote() {
    log_info "Preparing data processor environment for remote Elasticsearch..."
    
    # Check if data-processor directory exists
    if [[ ! -d "data-processor" ]]; then
        log_error "data-processor directory not found. Please run this script from the project root."
        return 1
    fi
    
    # Check if export_to_elasticsearch.py exists
    if [[ ! -f "data-processor/plugins/export_to_elasticsearch.py" ]]; then
        log_error "export_to_elasticsearch.py not found in data-processor/plugins/"
        return 1
    fi
    
    # Backup the original export_to_elasticsearch.py
    cp data-processor/plugins/export_to_elasticsearch.py data-processor/plugins/export_to_elasticsearch.py.backup
    
    # Modify the ES_HOSTS to point to remote cluster
    sed -i.tmp 's/ES_HOSTS = \["127.0.0.1"\]/ES_HOSTS = ["https:\/\/localhost:9200"]/' data-processor/plugins/export_to_elasticsearch.py
    
    # Add authentication to the Elasticsearch client
    local es_password=$(get_elasticsearch_password)
    sed -i.tmp2 "s/es = Elasticsearch(ES_HOSTS, sniff_on_start=False)/es = Elasticsearch(ES_HOSTS, basic_auth=(\"$ES_USER\", \"$es_password\"), verify_certs=False, ssl_show_warn=False, sniff_on_start=False)/" data-processor/plugins/export_to_elasticsearch.py
    
    # Clean up temporary files
    rm -f data-processor/plugins/export_to_elasticsearch.py.tmp data-processor/plugins/export_to_elasticsearch.py.tmp2
    
    log_success "Data processor environment ready (configured for remote cluster)"
}

# Function to restore original export_to_elasticsearch.py
restore_export_script() {
    log_info "Restoring original export_to_elasticsearch.py..."
    if [[ -f "data-processor/plugins/export_to_elasticsearch.py.backup" ]]; then
        mv data-processor/plugins/export_to_elasticsearch.py.backup data-processor/plugins/export_to_elasticsearch.py
        log_success "Original script restored"
    fi
}

# Function to index data using Python infrastructure
index_data_with_python() {
    local data_dir="$1"
    local data_type="${2:-detection}"
    
    log_info "Indexing data using Python infrastructure..."
    
    # Check if Python3 is available
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 is not available. Please install Python3 to use this function."
        return 1
    fi
    
    # Check if elasticsearch Python package is available
    if ! python3 -c "import elasticsearch" 2>/dev/null; then
        log_warning "Elasticsearch Python package is not available. Installing..."
        pip3 install elasticsearch
    fi
    
    # Use the existing data processor to process data
    log_info "Processing $data_type data using credo-data-processor.py..."
    python3 data-processor/credo-data-processor.py --dir "$data_dir" --data-type "$data_type"
    
    log_success "Python indexing completed"
}

# Function to copy data from pod to local and index it
copy_and_index_data() {
    local source_pod="$1"
    local source_path="$2"
    local local_temp_dir="$3"
    local data_type="${4:-detection}"
    
    log_info "Copying data from pod '$source_pod:$source_path' to local machine..."
    
    # Create local temporary directory
    mkdir -p "$local_temp_dir"
    
    # Copy data from pod to local
    kubectl cp "$NAMESPACE/$source_pod:$source_path" "$local_temp_dir" || {
        log_warning "No data found or error copying data from pod. Continuing anyway."
        return 0
    }
    
    local file_count=$(find "$local_temp_dir" -name "*.json" 2>/dev/null | wc -l)
    log_success "Copied $file_count JSON files to local machine"
    
    # Prepare data processor environment
    prepare_data_processor_for_remote
    
    # Index the data using Python infrastructure
    index_data_with_python "$local_temp_dir" "$data_type"
    
    # Restore original script
    restore_export_script
    
    # Clean up local temporary directory
    log_info "Cleaning up local temporary data directory: $local_temp_dir"
    rm -rf "$local_temp_dir"
    
    log_success "Data indexing process completed"
}

# Function to verify indexed data
verify_indexed_data() {
    log_info "Verifying indexed data..."
    
    # Get document count
    local es_password=$(get_elasticsearch_password)
    local count=$(kubectl exec -n "$NAMESPACE" "$ES_POD" -- curl -k -u "$ES_USER:$es_password" -X GET "$ES_URL/credo-detections/_count" 2>/dev/null | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
    
    if [[ -n "$count" ]]; then
        log_success "Successfully indexed $count CREDO detection documents"
        
        # Get sample of unique values
        log_info "Checking data quality..."
        kubectl exec -n "$NAMESPACE" "$ES_POD" -- curl -k -u "$ES_USER:$es_password" -X GET "$ES_URL/credo-detections/_search?size=0" -H "Content-Type: application/json" -d '{
            "aggs": {
                "unique_device_ids": {
                    "cardinality": {
                        "field": "device_id.keyword"
                    }
                },
                "unique_timestamps": {
                    "cardinality": {
                        "field": "timestamp.keyword"
                    }
                },
                "unique_detection_ids": {
                    "cardinality": {
                        "field": "detection_id.keyword"
                    }
                }
            }
        }' 2>/dev/null | grep -o '"value":[0-9]*' | grep -o '[0-9]*' | head -3 | while read -r unique_count; do
            echo "  - Unique values: $unique_count"
        done
        
    else
        log_warning "Could not retrieve document count"
    fi
}

# Export functions for use by other scripts
export -f get_elasticsearch_password
export -f prepare_data_processor_for_remote
export -f restore_export_script
export -f index_data_with_python
export -f copy_and_index_data
export -f verify_indexed_data
export -f log_info log_success log_warning log_error
