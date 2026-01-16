#!/usr/bin/env python3
"""
High-bandwidth Elasticsearch streamer for RC3 pods
Runs persistently as a daemon process
"""
import json
import os
import sys
import time
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth

# Configuration
ES_HOST = os.environ.get('ES_HOST', 'credo-elasticsearch-service')
ES_PORT = int(os.environ.get('ES_PORT', 9200))
ES_INDEX = os.environ.get('ES_INDEX', 'credo-detections')
ES_USER = os.environ.get('ES_USER', 'elastic')
ES_PASSWORD = os.environ.get('ES_PASSWORD', '')
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', 2000))
STREAM_INTERVAL = float(os.environ.get('STREAM_INTERVAL', 1))
STREAM_ID = os.environ.get('STREAM_ID', '1')
OUTPUT_DIR = os.environ.get('OUTPUT_DIR', f'/workspace/credo-data-rc3/detections/stream{STREAM_ID}')

# Setup
os.makedirs(OUTPUT_DIR, exist_ok=True)
auth = HTTPBasicAuth(ES_USER, ES_PASSWORD) if ES_PASSWORD else None
es_url = f'https://{ES_HOST}:{ES_PORT}'
last_timestamp_file = os.path.join(OUTPUT_DIR, '.last_timestamp')

# Load last timestamp
last_timestamp = None
if os.path.exists(last_timestamp_file):
    try:
        with open(last_timestamp_file, 'r') as f:
            last_timestamp = int(f.read().strip())
    except:
        pass

batch_num = 0
total_docs = 0

print(f'Stream {STREAM_ID}: Starting (Batch: {BATCH_SIZE}, Interval: {STREAM_INTERVAL}s, Output: {OUTPUT_DIR})', flush=True)

while True:
    try:
        # Build query
        query = {'size': BATCH_SIZE, 'sort': [{'timestamp': {'order': 'asc'}}]}
        if last_timestamp:
            query['query'] = {'range': {'timestamp': {'gt': last_timestamp}}}
        else:
            query['query'] = {'match_all': {}}
        
        # Query Elasticsearch
        response = requests.get(
            f'{es_url}/{ES_INDEX}/_search',
            json=query,
            auth=auth,
            verify=False,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f'Stream {STREAM_ID}: Error {response.status_code}', flush=True)
            time.sleep(STREAM_INTERVAL)
            continue
        
        data = response.json()
        hits = data.get('hits', {}).get('hits', [])
        
        if not hits:
            time.sleep(STREAM_INTERVAL)
            continue
        
        # Extract documents
        detections = [hit['_source'] for hit in hits]
        max_timestamp = last_timestamp or 0
        
        for det in detections:
            ts = det.get('timestamp')
            if ts:
                if isinstance(ts, str):
                    try:
                        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        ts = int(dt.timestamp() * 1000)
                    except:
                        pass
                if isinstance(ts, (int, float)) and ts > max_timestamp:
                    max_timestamp = int(ts)
        
        # Save batch
        batch_num += 1
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'stream{STREAM_ID}_batch_{batch_num}_{timestamp_str}.json'
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        with open(filepath, 'w') as f:
            json.dump({'detections': detections}, f)
        
        total_docs += len(detections)
        last_timestamp = max_timestamp
        
        # Save timestamp
        with open(last_timestamp_file, 'w') as f:
            f.write(str(last_timestamp))
        
        # Progress update every 10 batches
        if batch_num % 10 == 0:
            print(f'Stream {STREAM_ID}: Batch {batch_num}, Total docs: {total_docs}', flush=True)
        
        time.sleep(STREAM_INTERVAL)
        
    except KeyboardInterrupt:
        print(f'\nStream {STREAM_ID}: Stopped by user', flush=True)
        break
    except Exception as e:
        print(f'Stream {STREAM_ID}: Error: {e}', flush=True)
        time.sleep(STREAM_INTERVAL)

