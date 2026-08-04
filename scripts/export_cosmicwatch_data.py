#!/usr/bin/env python3
"""
Export CosmicWatch Data from Elasticsearch

This script exports CosmicWatch data from Elasticsearch for analysis and partitioning.
"""

import os
import json
import sys
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan

# Configuration
ES_HOST = os.getenv('ES_HOST', 'https://localhost:9200')
ES_USER = os.getenv('ES_USER', 'elastic')
ES_PASS = os.getenv('ES_PASS')
ES_INDEX = os.getenv('ES_INDEX', 'credo-detections')

if not ES_PASS:
    print("Error: ES_PASS environment variable is required")
    print("Set it with: export ES_PASS='your-password'")
    sys.exit(1)

# Connect to Elasticsearch
try:
    es = Elasticsearch(
        [ES_HOST],
        basic_auth=(ES_USER, ES_PASS),
        verify_certs=False,
        ssl_show_warn=False,
        request_timeout=60
    )
    # Test connection
    es.info()
    print(f'✓ Connected to Elasticsearch at {ES_HOST}')
except Exception as e:
    print(f'✗ Failed to connect to Elasticsearch: {e}')
    sys.exit(1)

# Query CosmicWatch data
print(f'\nExporting CosmicWatch data from index: {ES_INDEX}...')

query = {
    "query": {
        "term": {"source": "cosmicwatch-v3x"}
    },
    "sort": [{"timestamp": {"order": "asc"}}]
}

# Get total count
count_result = es.count(index=ES_INDEX, body={"query": query["query"]})
total_docs = count_result['count']
print(f'Total CosmicWatch documents: {total_docs:,}')

# Export data
os.makedirs('data', exist_ok=True)
output_file = 'data/cosmicwatch_data_export.json'
print(f'Exporting to: {output_file}...')

documents = []
try:
    # Use scan for large result sets
    query_body = {"query": {"term": {"source": "cosmicwatch-v3x"}}}
    for doc in scan(es, query=query_body, index=ES_INDEX, scroll='5m'):
        documents.append(doc['_source'])
        
        if len(documents) % 1000 == 0:
            print(f'  Exported {len(documents):,} documents...', end='\r')
    
    print(f'\n✓ Exported {len(documents):,} documents')
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(documents, f, indent=2)
    
    print(f'✓ Saved to {output_file}')
    
except Exception as e:
    print(f'✗ Error exporting data: {e}')
    sys.exit(1)

# Basic statistics
if documents:
    print(f'\n=== Basic Statistics ===')
    print(f'Total documents: {len(documents):,}')
    
    # Coincidence statistics
    coincident_count = sum(1 for d in documents if d.get('coincident') == True)
    non_coincident_count = len(documents) - coincident_count
    print(f'Coincidence events: {coincident_count:,} ({coincident_count/len(documents)*100:.1f}%)')
    print(f'Non-coincidence events: {non_coincident_count:,} ({non_coincident_count/len(documents)*100:.1f}%)')
    
    # ADC statistics
    adc_values = [d.get('adc_value') for d in documents if d.get('adc_value') is not None]
    if adc_values:
        print(f'ADC values: min={min(adc_values)}, max={max(adc_values)}, avg={sum(adc_values)/len(adc_values):.1f}')
    
    # SiPM statistics
    sipm_values = [d.get('sipm_mv') for d in documents if d.get('sipm_mv') is not None]
    if sipm_values:
        print(f'SiPM voltage: min={min(sipm_values):.1f}, max={max(sipm_values):.1f}, avg={sum(sipm_values)/len(sipm_values):.1f}')
    
    # Time range
    timestamps = [d.get('timestamp') for d in documents if d.get('timestamp') is not None]
    if timestamps:
        min_time = min(timestamps)
        max_time = max(timestamps)
        print(f'Time range: {min_time} to {max_time}')

print(f'\n✓ Export complete!')

