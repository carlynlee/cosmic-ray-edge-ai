#!/usr/bin/env python3
"""
Quick test script to verify Elasticsearch connection
"""
import os
import requests
from urllib3.exceptions import InsecureRequestWarning
import warnings
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

ES_HOST = os.getenv('ES_HOST', 'http://localhost:9200')
# Force HTTP for localhost
if 'localhost' in ES_HOST or '127.0.0.1' in ES_HOST:
    ES_HOST = ES_HOST.replace('https://', 'http://')
ES_USER = os.getenv('ES_USER', 'elastic')
ES_PASS = os.getenv('ES_PASS', '<YOUR_ES_PASSWORD>')

print(f"Testing connection to: {ES_HOST}")
print(f"User: {ES_USER}")
print()

# Test 1: Simple GET request
print("Test 1: Cluster health...")
try:
    url = f"{ES_HOST}/_cluster/health"
    response = requests.get(url, auth=(ES_USER, ES_PASS), timeout=5)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        health = response.json()
        print(f"  Cluster status: {health.get('status')}")
        print("  ✓ Connection successful!")
    else:
        print(f"  Response: {response.text[:200]}")
except requests.exceptions.ConnectionError as e:
    print(f"  ✗ Connection error: {e}")
    print("  → Check if port-forwarding is active")
except Exception as e:
    print(f"  ✗ Error: {e}")

print()

# Test 2: Search request
print("Test 2: Search request...")
try:
    url = f"{ES_HOST}/credo-detections/_search"
    query = {"query": {"match_all": {}}, "size": 0}
    response = requests.post(url, json=query, auth=(ES_USER, ES_PASS), timeout=5)
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        total = data.get('hits', {}).get('total', {})
        if isinstance(total, dict):
            count = total.get('value', 0)
        else:
            count = total
        print(f"  Total documents: {count:,}")
        print("  ✓ Search successful!")
    else:
        print(f"  Response: {response.text[:200]}")
except requests.exceptions.ConnectionError as e:
    print(f"  ✗ Connection error: {e}")
except Exception as e:
    print(f"  ✗ Error: {e}")

print()
print("If both tests fail, try:")
print("  1. Kill existing port-forward: kill <PID>")
print("  2. Port-forward to pod: kubectl port-forward -n cblee-credo credo-elasticsearch-es-default-0 9200:9200")
print("  3. Verify pod is running: kubectl get pods -n cblee-credo | grep elasticsearch")

