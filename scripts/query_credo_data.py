#!/usr/bin/env python3
"""
Query CREDO-science data from Elasticsearch

This script queries Elasticsearch for data imported from api.credo.science
and displays it in a readable format.

Usage:
    python3 query_credo_data.py [--count] [--recent N] [--time-range HOURS]
"""

import argparse
import requests
import json
import subprocess
import sys
from datetime import datetime, timedelta
from urllib3.exceptions import InsecureRequestWarning
import warnings
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

def get_es_password():
    """Get Elasticsearch password from Kubernetes secret"""
    try:
        result = subprocess.run(
            ['kubectl', 'get', 'secret', 'credo-elasticsearch-es-elastic-user',
             '-n', 'cblee-credo', '-o', 'jsonpath={.data.elastic}'],
            capture_output=True, text=True, check=True
        )
        es_pass = subprocess.run(
            ['base64', '-d'],
            input=result.stdout,
            capture_output=True, text=True
        ).stdout.strip()
        return es_pass
    except subprocess.CalledProcessError:
        print("Error: Could not get Elasticsearch password from Kubernetes")
        print("Make sure you're connected to the cluster and the secret exists")
        sys.exit(1)

def query_elasticsearch(query, es_host="https://localhost:9200", es_user="elastic", es_pass=None):
    """Query Elasticsearch"""
    if es_pass is None:
        es_pass = get_es_password()
    
    url = f"{es_host}/credo-detections/_search"
    
    response = requests.get(
        url,
        json=query,
        auth=(es_user, es_pass),
        verify=False,
        timeout=30
    )
    
    if not response.ok:
        print(f"Error: HTTP {response.status_code}")
        print(response.text)
        sys.exit(1)
    
    return response.json()

def count_credo_data(es_host, es_user, es_pass):
    """Count CREDO-science documents"""
    query = {
        "size": 0,
        "query": {
            "term": {
                "source.keyword": "credo-science"
            }
        }
    }
    
    result = query_elasticsearch(query, es_host, es_user, es_pass)
    return result.get("hits", {}).get("total", {}).get("value", 0)

def get_recent_documents(n=10, es_host="https://localhost:9200", es_user="elastic", es_pass=None):
    """Get recent CREDO-science documents"""
    query = {
        "size": n,
        "query": {
            "term": {
                "source.keyword": "credo-science"
            }
        },
        "sort": [
            {
                "timestamp": {
                    "order": "desc"
                }
            }
        ]
    }
    
    result = query_elasticsearch(query, es_host, es_user, es_pass)
    return result.get("hits", {}).get("hits", [])

def get_time_range_stats(hours=24, es_host="https://localhost:9200", es_user="elastic", es_pass=None):
    """Get statistics for a time range"""
    since = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
    until = datetime.utcnow().isoformat() + "Z"
    
    query = {
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    {
                        "term": {
                            "source.keyword": "credo-science"
                        }
                    },
                    {
                        "range": {
                            "timestamp": {
                                "gte": since,
                                "lte": until
                            }
                        }
                    }
                ]
            }
        },
        "aggs": {
            "events_over_time": {
                "date_histogram": {
                    "field": "timestamp",
                    "calendar_interval": "1h"
                }
            }
        }
    }
    
    result = query_elasticsearch(query, es_host, es_user, es_pass)
    return result.get("aggregations", {}).get("events_over_time", {}).get("buckets", [])

def main():
    parser = argparse.ArgumentParser(
        description='Query CREDO-science data from Elasticsearch'
    )
    parser.add_argument(
        '--count',
        action='store_true',
        help='Show count of CREDO-science documents'
    )
    parser.add_argument(
        '--recent',
        type=int,
        metavar='N',
        help='Show N most recent documents (default: 10)'
    )
    parser.add_argument(
        '--time-range',
        type=int,
        metavar='HOURS',
        help='Show statistics for last N hours'
    )
    parser.add_argument(
        '--es-host',
        default='https://localhost:9200',
        help='Elasticsearch host (default: https://localhost:9200)'
    )
    parser.add_argument(
        '--es-user',
        default='elastic',
        help='Elasticsearch username (default: elastic)'
    )
    
    args = parser.parse_args()
    
    # Check if port forwarding is needed
    if args.es_host == 'https://localhost:9200':
        print("Note: Make sure Elasticsearch is port-forwarded:")
        print("  kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200")
        print()
    
    es_pass = get_es_password()
    
    # Count
    if args.count or (not args.recent and not args.time_range):
        count = count_credo_data(args.es_host, args.es_user, es_pass)
        print(f"CREDO-science documents: {count:,}")
        if count == 0:
            print("\n⚠ No CREDO-science data found yet.")
            print("  The data streamer may still be waiting for exports to complete.")
            print("  Check status: kubectl logs deployment/credo-stream -n cblee-credo")
    
    # Recent documents
    if args.recent:
        n = args.recent
        print(f"\n=== {n} Most Recent CREDO-science Documents ===")
        hits = get_recent_documents(n, args.es_host, args.es_user, es_pass)
        
        if not hits:
            print("No documents found.")
        else:
            for i, hit in enumerate(hits, 1):
                source = hit.get("_source", {})
                print(f"\n[{i}] Document ID: {hit.get('_id')}")
                print(f"    Timestamp: {source.get('timestamp', 'N/A')}")
                print(f"    Source: {source.get('source', 'N/A')}")
                if 'location' in source:
                    loc = source['location']
                    print(f"    Location: {loc.get('lat')}, {loc.get('lon')}")
                print(f"    Data preview: {json.dumps(source, indent=2)[:200]}...")
    
    # Time range statistics
    if args.time_range:
        hours = args.time_range
        print(f"\n=== Statistics for Last {hours} Hours ===")
        buckets = get_time_range_stats(hours, args.es_host, args.es_user, es_pass)
        
        if not buckets:
            print("No data in this time range.")
        else:
            total = sum(b['doc_count'] for b in buckets)
            print(f"Total events: {total:,}")
            print("\nEvents per hour:")
            for bucket in buckets:
                time_str = bucket.get('key_as_string', 'N/A')
                count = bucket.get('doc_count', 0)
                print(f"  {time_str}: {count:,} events")

if __name__ == "__main__":
    main()




