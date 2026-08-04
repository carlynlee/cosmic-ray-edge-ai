#!/usr/bin/env python3
"""
Visualization Dashboard for CosmicWatch Data

Simple dashboard showing real-time metrics, model predictions, and scientific plots.
"""

import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta
from urllib3.exceptions import InsecureRequestWarning
import warnings
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from collections import deque

# Configuration
# Default to HTTP for localhost port-forwarding
ES_HOST = os.getenv('ES_HOST', 'http://localhost:9200')
ES_USER = os.getenv('ES_USER', 'elastic')
ES_PASS = os.getenv('ES_PASS', '')
ES_INDEX = os.getenv('ES_INDEX', 'credo-detections')
OUTPUT_DIR = 'data/dashboard'
UPDATE_INTERVAL = 60  # Update every 60 seconds

class Dashboard:
    """Real-time dashboard for cosmic ray detection"""
    
    def __init__(self):
        self.output_dir = OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Data buffers for time series
        self.timestamps = deque(maxlen=100)
        self.event_counts = deque(maxlen=100)
        self.coincidence_counts = deque(maxlen=100)
        self.prediction_counts = deque(maxlen=100)
        self.accuracy_scores = deque(maxlen=100)
        
    def query_elasticsearch(self, query):
        """Query Elasticsearch"""
        url = f"{ES_HOST}/{ES_INDEX}/_search"
        auth = (ES_USER, ES_PASS)
        
        # Use HTTP for localhost, HTTPS for remote
        use_https = not ('localhost' in ES_HOST or '127.0.0.1' in ES_HOST)
        
        try:
            response = requests.post(
                url,
                json=query,
                auth=auth,
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.SSLError as e:
            # If SSL error on localhost, try HTTP instead
            if not use_https and ES_HOST.startswith('https://'):
                http_url = ES_HOST.replace('https://', 'http://')
                url = f"{http_url}/{ES_INDEX}/_search"
                try:
                    response = requests.post(
                        url,
                        json=query,
                        auth=auth,
                        timeout=10
                    )
                    response.raise_for_status()
                    return response.json()
                except Exception as e2:
                    print(f"Error querying Elasticsearch (HTTP fallback): {e2}")
                    return None
            else:
                print(f"SSL Error querying Elasticsearch: {e}")
                return None
        except requests.exceptions.HTTPError as e:
            # Print more details about HTTP errors
            error_msg = str(e)
            if e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"{error_msg}\n  Details: {error_detail.get('error', {}).get('reason', 'Unknown error')}"
                except:
                    error_msg = f"{error_msg}\n  Response: {e.response.text[:200]}"
            print(f"Error querying Elasticsearch: {error_msg}")
            return None
        except Exception as e:
            print(f"Error querying Elasticsearch: {e}")
            return None
    
    def get_recent_stats(self, hours=24):
        """Get statistics for recent data"""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        # Format timestamp as ISO string with Z suffix for UTC
        start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"source": "cosmicwatch-v3x"}},
                        {"range": {
                            "timestamp": {
                                "gte": start_time_str
                            }
                        }}
                    ]
                }
            },
            "size": 0,
            "aggs": {
                "coincidence_events": {
                    "filter": {"term": {"coincident": True}}
                },
                "predicted_coincidence": {
                    "filter": {"term": {"ml_prediction": 1}}
                },
                "hourly": {
                    "date_histogram": {
                        "field": "timestamp",
                        "calendar_interval": "1h"
                    },
                    "aggs": {
                        "coincidence_rate": {
                            "avg": {"field": "coincident"}
                        },
                        "prediction_rate": {
                            "avg": {"field": "ml_prediction"}
                        }
                    }
                }
            }
        }
        
        response = self.query_elasticsearch(query)
        if not response:
            # If query with time range fails, try without time range (data might have future timestamps)
            print("  Warning: Time range query failed, trying without time filter...")
            query_no_time = {
                "query": {
                    "term": {"source": "cosmicwatch-v3x"}
                },
                "size": 0,
                "aggs": {
                    "coincidence_events": {
                        "filter": {"term": {"coincident": True}}
                    },
                    "predicted_coincidence": {
                        "filter": {"term": {"ml_prediction": 1}}
                    },
                    "hourly": {
                        "date_histogram": {
                            "field": "timestamp",
                            "calendar_interval": "1h",
                            "min_doc_count": 1
                        },
                        "aggs": {
                            "coincidence_rate": {
                                "avg": {"field": "coincident"}
                            },
                            "prediction_rate": {
                                "avg": {"field": "ml_prediction"}
                            }
                        }
                    }
                }
            }
            response = self.query_elasticsearch(query_no_time)
            if not response:
                return None
        
        # Get total from hits.total (not from aggregation on _id)
        total = response.get('hits', {}).get('total', {})
        if isinstance(total, dict):
            total_events = total.get('value', 0)
        else:
            total_events = total
        
        aggs = response.get('aggregations', {})
        
        stats = {
            'total_events': total_events,
            'coincidence_events': aggs.get('coincidence_events', {}).get('doc_count', 0),
            'predicted_coincidence': aggs.get('predicted_coincidence', {}).get('doc_count', 0),
            'hourly_data': []
        }
        
        # Process hourly data
        for bucket in aggs.get('hourly', {}).get('buckets', []):
            coincidence_rate = bucket.get('coincidence_rate', {}).get('value')
            prediction_rate = bucket.get('prediction_rate', {}).get('value')
            stats['hourly_data'].append({
                'time': bucket['key_as_string'],
                'count': bucket['doc_count'],
                'coincidence_rate': coincidence_rate if coincidence_rate is not None else 0,
                'prediction_rate': prediction_rate if prediction_rate is not None else 0
            })
        
        return stats
    
    def calculate_accuracy(self):
        """Calculate model accuracy from recent predictions"""
        start_time = datetime.utcnow() - timedelta(hours=1)
        # Format timestamp as ISO string with Z suffix for UTC
        start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"source": "cosmicwatch-v3x"}},
                        {"exists": {"field": "ml_prediction"}},
                        {"range": {
                            "timestamp": {
                                "gte": start_time_str
                            }
                        }}
                    ]
                }
            },
            "size": 1000
        }
        
        response = self.query_elasticsearch(query)
        if not response or not response.get('hits', {}).get('hits'):
            return None
        
        hits = response['hits']['hits']
        correct = 0
        total = 0
        
        for hit in hits:
            source = hit.get('_source', {})
            actual = source.get('coincident', 0)
            predicted = source.get('ml_prediction', 0)
            
            if actual == predicted:
                correct += 1
            total += 1
        
        return correct / total if total > 0 else None
    
    def create_summary_plot(self, stats):
        """Create summary visualization"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('CosmicWatch Real-Time Dashboard', fontsize=16, fontweight='bold')
        
        # 1. Event counts over time
        ax1 = axes[0, 0]
        if stats['hourly_data']:
            times = [datetime.fromisoformat(d['time'].replace('Z', '+00:00')) for d in stats['hourly_data']]
            counts = [d.get('count', 0) for d in stats['hourly_data']]
            ax1.plot(times, counts, marker='o', linewidth=2, markersize=6)
            ax1.set_title('Detection Rate (Events/Hour)')
            ax1.set_xlabel('Time')
            ax1.set_ylabel('Events')
            ax1.grid(True, alpha=0.3)
            ax1.tick_params(axis='x', rotation=45)
        
        # 2. Coincidence vs Prediction Rate
        ax2 = axes[0, 1]
        if stats['hourly_data']:
            times = [datetime.fromisoformat(d['time'].replace('Z', '+00:00')) for d in stats['hourly_data']]
            coincidence_rates = [(d['coincidence_rate'] or 0) * 100 for d in stats['hourly_data']]
            prediction_rates = [(d['prediction_rate'] or 0) * 100 for d in stats['hourly_data']]
            ax2.plot(times, coincidence_rates, label='Actual Coincidence', marker='o', linewidth=2)
            ax2.plot(times, prediction_rates, label='Predicted Coincidence', marker='s', linewidth=2)
            ax2.set_title('Coincidence Rate Comparison')
            ax2.set_xlabel('Time')
            ax2.set_ylabel('Rate (%)')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            ax2.tick_params(axis='x', rotation=45)
        
        # 3. Statistics summary
        ax3 = axes[1, 0]
        ax3.axis('off')
        stats_text = f"""
        Real-Time Statistics (Last 24 Hours)
        
        Total Events: {stats['total_events']:,}
        Coincidence Events: {stats['coincidence_events']:,}
        Predicted Coincidence: {stats['predicted_coincidence']:,}
        
        Coincidence Rate: {100*stats['coincidence_events']/max(stats['total_events'],1):.2f}%
        Prediction Rate: {100*stats['predicted_coincidence']/max(stats['total_events'],1):.2f}%
        
        Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        ax3.text(0.1, 0.5, stats_text, fontsize=12, family='monospace',
                verticalalignment='center', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        # 4. Accuracy over time (if available)
        ax4 = axes[1, 1]
        accuracy = self.calculate_accuracy()
        if accuracy is not None:
            ax4.bar(['Model Accuracy'], [accuracy * 100], color='green', alpha=0.7)
            ax4.set_title('Model Accuracy (Last Hour)')
            ax4.set_ylabel('Accuracy (%)')
            ax4.set_ylim(0, 100)
            ax4.text(0, accuracy * 100 + 2, f'{accuracy*100:.1f}%', 
                    ha='center', fontweight='bold')
        else:
            ax4.text(0.5, 0.5, 'No predictions available\nfor accuracy calculation', 
                    ha='center', va='center', transform=ax4.transAxes)
            ax4.set_title('Model Accuracy')
        
        plt.tight_layout()
        
        # Save
        output_file = os.path.join(self.output_dir, 'dashboard_summary.png')
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✓ Dashboard saved: {output_file}")
        return output_file
    
    def update(self):
        """Update dashboard"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Updating dashboard...")
        
        # Get statistics
        stats = self.get_recent_stats(hours=24)
        if not stats:
            print("  No data available")
            return
        
        # Create visualization
        output_file = self.create_summary_plot(stats)
        
        # Print summary
        print(f"  Total events: {stats['total_events']:,}")
        print(f"  Coincidence events: {stats['coincidence_events']:,} ({100*stats['coincidence_events']/max(stats['total_events'],1):.2f}%)")
        print(f"  Predicted coincidence: {stats['predicted_coincidence']:,}")
        
        accuracy = self.calculate_accuracy()
        if accuracy:
            print(f"  Model accuracy: {accuracy*100:.1f}%")
    
    def run(self, continuous=True):
        """Run dashboard"""
        print("=" * 70)
        print("CosmicWatch Visualization Dashboard")
        print("=" * 70)
        print(f"Elasticsearch: {ES_HOST}")
        print(f"Index: {ES_INDEX}")
        print(f"Output directory: {self.output_dir}")
        print(f"Update interval: {UPDATE_INTERVAL} seconds")
        print("=" * 70)
        print()
        
        if continuous:
            print("Running in continuous mode (Ctrl+C to stop)...")
            print()
        
        try:
            while True:
                self.update()
                
                if not continuous:
                    break
                
                time.sleep(UPDATE_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n" + "=" * 70)
            print("Dashboard stopped")
            print("=" * 70)

def main():
    """Main function"""
    import argparse
    
    global UPDATE_INTERVAL
    
    parser = argparse.ArgumentParser(description='Visualization dashboard')
    parser.add_argument('--once', action='store_true', help='Update once instead of continuously')
    parser.add_argument('--interval', type=int, default=UPDATE_INTERVAL,
                       help=f'Update interval in seconds (default: {UPDATE_INTERVAL})')
    
    args = parser.parse_args()
    
    UPDATE_INTERVAL = args.interval
    
    dashboard = Dashboard()
    dashboard.run(continuous=not args.once)

if __name__ == "__main__":
    main()

