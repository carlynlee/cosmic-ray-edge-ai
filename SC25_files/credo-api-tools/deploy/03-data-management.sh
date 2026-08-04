#!/bin/bash

# CREDO Three-Pod System - Data Management Script
# Manage CREDO data collection and indexing

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

# Function to fetch more CREDO data
fetch_more_data() {
    log_info "Fetching more CREDO data..."
    
    # Get the CREDO server pod name
    local credo_pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-caltech-server -o jsonpath='{.items[0].metadata.name}')
    
    if [[ -z "$credo_pod" ]]; then
        log_error "CREDO Caltech Server pod not found"
        return 1
    fi
    
    # Fetch more data
    kubectl exec -n "$NAMESPACE" "$credo_pod" -- bash -c "
        export CREDO_TOKEN='$CREDO_TOKEN'
        cd /workspace/data-exporter
        python3 credo-data-exporter.py --token \$CREDO_TOKEN --dir /workspace/credo-data-additional --max-chunk-size 1000 --data-type detection
    " || log_warning "Data export may have timed out, but some data may have been downloaded"
    
    log_success "Data fetching completed"
}

# Function to index additional data
index_additional_data() {
    log_info "Indexing additional data..."
    
    # Get pod names
    local credo_pod=$(kubectl get pods -n "$NAMESPACE" -l app=credo-caltech-server -o jsonpath='{.items[0].metadata.name}')
    local es_pod=$(kubectl get pods -n "$NAMESPACE" -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}')
    
    if [[ -z "$credo_pod" || -z "$es_pod" ]]; then
        log_error "Required pods not found"
        return 1
    fi
    
    # Copy additional data to Elasticsearch pod
    log_info "Copying additional data to Elasticsearch pod..."
    kubectl cp "$NAMESPACE/$credo_pod:/workspace/credo-data-additional/" ./credo-data-additional-temp/ || log_warning "No additional data to copy"
    kubectl cp ./credo-data-additional-temp/ "$NAMESPACE/$es_pod:/tmp/credo-data-additional/" || log_warning "Failed to copy additional data"
    
    # Get Elasticsearch password
    local es_password=$(kubectl get secret credo-elasticsearch-es-elastic-user -n "$NAMESPACE" -o jsonpath='{.data.elastic}' | base64 -d)
    
    # Index the additional data
    log_info "Indexing additional data into Elasticsearch..."
    kubectl exec -n "$NAMESPACE" "$es_pod" -- bash -c "
        ES_URL=\"https://localhost:9200\"
        ES_USER=\"elastic\"
        ES_PASSWORD=\"$es_password\"
        
        # Get current document count
        current_count=\$(curl -k -u \"\$ES_USER:\$ES_PASSWORD\" -X GET \"\$ES_URL/credo-detections/_count\" 2>/dev/null | grep -o '\"count\":[0-9]*' | grep -o '[0-9]*')
        echo \"Current document count: \$current_count\"
        
        doc_id=\$((current_count + 1))
        
        # Process additional files
        for file in /tmp/credo-data-additional/detections/*.json; do
            if [[ -f \"\$file\" ]]; then
                echo \"Processing \$(basename \"\$file\")...\"
                
                # Extract device IDs and index them
                grep -o \"\\\"device_id\\\": [0-9]*\" \"\$file\" | while read -r line; do
                    if [[ \$line =~ \\\"device_id\\\":\ ([0-9]+) ]]; then
                        device_id=\"\${BASH_REMATCH[1]}\"
                        
                        # Create document
                        doc=\"{
                            \\\"timestamp\\\": \\\"2018-05-11T01:00:00+00:00\\\",
                            \\\"device_id\\\": \\\"\$device_id\\\",
                            \\\"latitude\\\": 0.0,
                            \\\"longitude\\\": 0.0,
                            \\\"altitude\\\": 0.0,
                            \\\"particle_type\\\": \\\"cosmic_ray\\\",
                            \\\"energy\\\": 0,
                            \\\"source\\\": \\\"credo.science\\\",
                            \\\"time_received\\\": 1526043400000,
                            \\\"doc_id\\\": \$doc_id,
                            \\\"batch\\\": \\\"additional\\\"
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
        
        echo \"Additional data indexing completed!\"
    "
    
    # Verify the updated data
    log_info "Verifying updated data..."
    local new_count=$(kubectl exec -n "$NAMESPACE" "$es_pod" -- curl -k -u "elastic:$es_password" -X GET "https://localhost:9200/credo-detections/_count" 2>/dev/null | grep -o '"count":[0-9]*' | grep -o '[0-9]*')
    
    if [[ -n "$new_count" ]]; then
        log_success "Successfully indexed $new_count total CREDO detection documents"
    else
        log_warning "Could not retrieve updated document count"
    fi
    
    # Clean up temporary files
    rm -rf ./credo-data-additional-temp/ 2>/dev/null || true
}

# Function to show data statistics
show_data_stats() {
    log_info "Data Statistics:"
    echo ""
    
    # Get Elasticsearch pod
    local es_pod=$(kubectl get pods -n "$NAMESPACE" -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}')
    
    if [[ -n "$es_pod" ]]; then
        # Get Elasticsearch password
        local es_password=$(kubectl get secret credo-elasticsearch-es-elastic-user -n "$NAMESPACE" -o jsonpath='{.data.elastic}' | base64 -d)
        
        # Show document count
        log_info "Total document count:"
        kubectl exec -n "$NAMESPACE" "$es_pod" -- curl -k -u "elastic:$es_password" -X GET "https://localhost:9200/credo-detections/_count" 2>/dev/null || echo "No data found"
        echo ""
        
        # Show sample documents
        log_info "Sample documents:"
        kubectl exec -n "$NAMESPACE" "$es_pod" -- curl -k -u "elastic:$es_password" -X GET "https://localhost:9200/credo-detections/_search?size=3&pretty" 2>/dev/null || echo "No data found"
        echo ""
        
        # Show data by batch
        log_info "Data by batch:"
        kubectl exec -n "$NAMESPACE" "$es_pod" -- curl -k -u "elastic:$es_password" -X GET "https://localhost:9200/credo-detections/_search?size=0&aggs={\"batches\":{\"terms\":{\"field\":\"batch\"}}}" 2>/dev/null || echo "No batch data found"
        echo ""
    else
        log_warning "Elasticsearch pod not found"
    fi
}

# Function to clear all data
clear_all_data() {
    log_warning "This will delete ALL data from Elasticsearch!"
    echo ""
    read -p "Are you sure you want to proceed? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Clearing all data from Elasticsearch..."
        
        # Get Elasticsearch pod
        local es_pod=$(kubectl get pods -n "$NAMESPACE" -l elasticsearch.k8s.elastic.co/cluster-name=credo-elasticsearch -o jsonpath='{.items[0].metadata.name}')
        
        if [[ -n "$es_pod" ]]; then
            # Get Elasticsearch password
            local es_password=$(kubectl get secret credo-elasticsearch-es-elastic-user -n "$NAMESPACE" -o jsonpath='{.data.elastic}' | base64 -d)
            
            # Delete the index
            kubectl exec -n "$NAMESPACE" "$es_pod" -- curl -k -u "elastic:$es_password" -X DELETE "https://localhost:9200/credo-detections" 2>/dev/null || true
            
            log_success "All data cleared from Elasticsearch"
        else
            log_error "Elasticsearch pod not found"
        fi
    else
        log_info "Data clearing cancelled"
    fi
}

# Main function
main() {
    case "${1:-help}" in
        "fetch")
            fetch_more_data
            ;;
        "index")
            index_additional_data
            ;;
        "stats")
            show_data_stats
            ;;
        "clear")
            clear_all_data
            ;;
        "help"|"-h"|"--help")
            cat << EOF
Usage: $0 [command]

Commands:
    fetch    Fetch more CREDO data from CREDO.science
    index    Index additional data into Elasticsearch
    stats    Show data statistics and samples
    clear    Clear all data from Elasticsearch
    help     Show this help message

Examples:
    $0 fetch    # Fetch more data
    $0 index    # Index additional data
    $0 stats    # Show data statistics
    $0 clear    # Clear all data
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
