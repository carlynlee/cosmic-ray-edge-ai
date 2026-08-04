#!/usr/bin/env python3
"""
Real-Time Inference Pipeline for CosmicWatch Data

Streams data from Elasticsearch, runs model inference, and stores predictions.
"""

import os
import sys
import time
import json
import pickle
import requests
from datetime import datetime, timedelta
from urllib3.exceptions import InsecureRequestWarning
import warnings
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

# Import model architecture
from train_binary_baseline import BinaryCoincidenceClassifier, FEATURES

# Configuration
# Default to HTTPS for localhost (Elasticsearch requires HTTPS even through port-forward)
ES_HOST = os.getenv('ES_HOST', 'https://localhost:9200')
ES_USER = os.getenv('ES_USER', 'elastic')
ES_PASS = os.getenv('ES_PASS', '')
ES_INDEX = os.getenv('ES_INDEX', 'credo-detections')
MODEL_DIR = 'models'
MODEL_FILE = os.path.join(MODEL_DIR, 'binary_baseline_model.pth')
SCALER_FILE = os.path.join(MODEL_DIR, 'binary_baseline_scaler.pkl')
PREDICTION_THRESHOLD = 0.5  # Can be tuned based on evaluation

# Time window for querying new data (last N minutes)
QUERY_WINDOW_MINUTES = 5
POLL_INTERVAL_SECONDS = 30

class RealTimeInference:
    """Real-time inference pipeline"""
    
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.scaler = None
        self.last_timestamp = None
        self.processed_count = 0
        self.prediction_count = 0
        
        # Load model and scaler
        self.load_model()
        
    def load_model(self):
        """Load trained model and scaler"""
        print("Loading model and scaler...")
        
        if not os.path.exists(MODEL_FILE):
            print(f"Error: Model file not found: {MODEL_FILE}")
            print("Please train the model first using train_binary_baseline.py")
            sys.exit(1)
        
        if not os.path.exists(SCALER_FILE):
            print(f"Error: Scaler file not found: {SCALER_FILE}")
            sys.exit(1)
        
        # Load scaler
        with open(SCALER_FILE, 'rb') as f:
            self.scaler = pickle.load(f)
        
        # Load model
        model = BinaryCoincidenceClassifier(input_size=len(FEATURES), hidden_sizes=[64, 32])
        model.load_state_dict(torch.load(MODEL_FILE, map_location=self.device))
        model.eval()
        model.to(self.device)
        self.model = model
        
        print(f"✓ Model loaded: {MODEL_FILE}")
        print(f"✓ Scaler loaded: {SCALER_FILE}")
        print(f"✓ Device: {self.device}")
        
    def query_elasticsearch(self, start_time=None):
        """Query Elasticsearch for new documents"""
        if start_time is None:
            # Simple test query
            query = {
                "query": {"match_all": {}},
                "size": 0
            }
        else:
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"source": "cosmicwatch-v3x"}},
                            {"range": {
                                "timestamp": {
                                    "gte": start_time.isoformat(),
                                    "lte": datetime.utcnow().isoformat()
                                }
                            }}
                        ]
                    }
                },
                "sort": [{"timestamp": {"order": "asc"}}],
                "size": 1000
            }
        
        url = f"{ES_HOST}/{ES_INDEX}/_search"
        auth = (ES_USER, ES_PASS)
        
        # Elasticsearch requires HTTPS even through port-forward, use verify=False for self-signed certs
        try:
            response = requests.post(
                url,
                json=query,
                auth=auth,
                verify=False,  # Disable SSL verification for port-forwarded connections
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error: {e}")
            print(f"  Check if port-forwarding is active: kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200")
            return None
        except requests.exceptions.SSLError as e:
            print(f"SSL Error querying Elasticsearch: {e}")
            print(f"  Try: kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error querying Elasticsearch: {e}")
            if e.response is not None:
                print(f"  Status code: {e.response.status_code}")
                print(f"  Response: {e.response.text[:200]}")
            return None
        except Exception as e:
            error_type = type(e).__name__
            print(f"Error querying Elasticsearch ({error_type}): {e}")
            return None
    
    def extract_features(self, doc):
        """Extract features from Elasticsearch document"""
        source = doc.get('_source', {})
        
        features = {}
        for feature in FEATURES:
            # Handle different field names
            if feature == 'adc_value':
                features[feature] = source.get('adc_value') or source.get('adc') or 0
            elif feature == 'sipm_mv':
                features[feature] = source.get('sipm_mv') or source.get('sipm') or 0
            elif feature == 'temperature_c':
                features[feature] = source.get('temperature_c') or source.get('temperature') or 0
            elif feature == 'pressure_pa':
                features[feature] = source.get('pressure_pa') or source.get('pressure') or 0
            elif feature == 'accel_z_g':
                accel = source.get('accel', {})
                if isinstance(accel, dict):
                    features[feature] = accel.get('z', 0)
                else:
                    features[feature] = 0
            else:
                features[feature] = source.get(feature, 0)
        
        return features
    
    def predict(self, features_dict):
        """Run model inference on features"""
        # Convert to array
        feature_array = np.array([[features_dict[f] for f in FEATURES]])
        
        # Scale
        feature_scaled = self.scaler.transform(feature_array)
        
        # Convert to tensor
        feature_tensor = torch.FloatTensor(feature_scaled).to(self.device)
        
        # Predict
        with torch.no_grad():
            output = self.model(feature_tensor)
            probability = output.item()
            prediction = 1 if probability >= PREDICTION_THRESHOLD else 0
        
        return prediction, probability
    
    def update_elasticsearch(self, doc_id, prediction, probability):
        """Update Elasticsearch document with prediction"""
        update_body = {
            "doc": {
                "ml_prediction": prediction,
                "ml_probability": float(probability),
                "ml_timestamp": datetime.utcnow().isoformat()
            }
        }
        
        url = f"{ES_HOST}/{ES_INDEX}/_update/{doc_id}"
        auth = (ES_USER, ES_PASS)
        
        # Elasticsearch requires HTTPS even through port-forward, use verify=False for self-signed certs
        # Retry logic for timeout issues
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url,
                    json=update_body,
                    auth=auth,
                    verify=False,  # Disable SSL verification for port-forwarded connections
                    timeout=15  # Increased timeout from 5 to 15 seconds
                )
                response.raise_for_status()
                return True
            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)  # Brief pause before retry
                    continue
                # Don't print timeout errors for every document (too verbose)
                return False
            except requests.exceptions.SSLError as e:
                print(f"SSL Error updating document {doc_id}: {e}")
                return False
            except Exception as e:
                # Only print non-timeout errors
                if "timeout" not in str(e).lower():
                    print(f"Error updating document {doc_id}: {e}")
                return False
        return False
    
    def process_documents(self, response_data):
        """Process documents from Elasticsearch response"""
        if not response_data or 'hits' not in response_data:
            return 0
        
        hits = response_data['hits'].get('hits', [])
        processed = 0
        skipped = 0
        errors = 0
        
        for hit in hits:
            doc_id = hit['_id']
            source = hit.get('_source', {})
            
            # Skip if already processed
            if 'ml_prediction' in source:
                skipped += 1
                continue
            
            # Extract features
            features = self.extract_features(hit)
            
            # Check if all features are available
            if any(features[f] == 0 and f in ['adc_value', 'sipm_mv'] for f in FEATURES):
                skipped += 1
                continue
            
            # Predict
            prediction, probability = self.predict(features)
            
            # Update Elasticsearch
            if self.update_elasticsearch(doc_id, prediction, probability):
                processed += 1
                self.prediction_count += 1
                
                if prediction == 1:
                    print(f"  ✓ Coincidence predicted (prob={probability:.3f}) for doc {doc_id[:8]}...")
            else:
                errors += 1
        
        # Print summary if there were many documents
        if len(hits) > 10:
            if processed > 0:
                print(f"  Processed: {processed}, Skipped: {skipped}, Errors: {errors}")
        
        return processed
    
    def run(self, continuous=True):
        """Run inference pipeline"""
        print("=" * 70)
        print("Real-Time Inference Pipeline")
        print("=" * 70)
        print(f"Elasticsearch: {ES_HOST}")
        print(f"Index: {ES_INDEX}")
        print(f"Model: {MODEL_FILE}")
        print(f"Query window: {QUERY_WINDOW_MINUTES} minutes")
        print(f"Poll interval: {POLL_INTERVAL_SECONDS} seconds")
        print("=" * 70)
        print()
        
        # Test connection first
        if not self.test_connection():
            if not continuous:
                return
            print("\n⚠️  Will retry connection every 30 seconds...")
            print()
        
        if continuous:
            print("Running in continuous mode (Ctrl+C to stop)...")
            print()
        
        try:
            while True:
                # Determine start time
                if self.last_timestamp:
                    start_time = self.last_timestamp
                else:
                    start_time = datetime.utcnow() - timedelta(minutes=QUERY_WINDOW_MINUTES)
                
                # Query Elasticsearch
                response = self.query_elasticsearch(start_time)
                
                if response:
                    # Process documents
                    processed = self.process_documents(response)
                    
                    if processed > 0:
                        self.processed_count += processed
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Processed {processed} new documents (total: {self.processed_count})")
                    
                    # Update last timestamp
                    if response.get('hits', {}).get('hits'):
                        last_hit = response['hits']['hits'][-1]
                        self.last_timestamp = datetime.fromisoformat(
                            last_hit['_source']['timestamp'].replace('Z', '+00:00')
                        )
                elif continuous:
                    # Only print error occasionally to avoid spam
                    if self.processed_count == 0 or (self.processed_count % 10 == 0):
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for Elasticsearch connection...")
                
                if not continuous:
                    break
                
                # Wait before next poll
                time.sleep(POLL_INTERVAL_SECONDS)
                
        except KeyboardInterrupt:
            print("\n" + "=" * 70)
            print("Inference pipeline stopped")
            print(f"Total documents processed: {self.processed_count}")
            print(f"Total predictions made: {self.prediction_count}")
            print("=" * 70)
    
    def test_connection(self):
        """Test Elasticsearch connection"""
        print("Testing Elasticsearch connection...")
        test_response = self.query_elasticsearch(None)
        if test_response is None:
            print("\n⚠️  Warning: Could not connect to Elasticsearch")
            print("  Troubleshooting steps:")
            print("  1. Port-forward to HTTP service: kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200")
            print("  2. Verify ES_HOST: https://localhost:9200 (HTTPS required)")
            print("  3. Check Elasticsearch pod: kubectl get pods -n cblee-credo | grep elasticsearch")
            return False
        else:
            total = test_response.get('hits', {}).get('total', {})
            if isinstance(total, dict):
                count = total.get('value', 0)
            else:
                count = total
            print(f"✓ Connected! Total documents in index: {count:,}")
            return True

def main():
    """Main function"""
    import argparse
    
    global QUERY_WINDOW_MINUTES, POLL_INTERVAL_SECONDS
    
    parser = argparse.ArgumentParser(description='Real-time inference pipeline')
    parser.add_argument('--once', action='store_true', help='Run once instead of continuously')
    parser.add_argument('--window', type=int, default=QUERY_WINDOW_MINUTES, 
                       help=f'Query window in minutes (default: {QUERY_WINDOW_MINUTES})')
    parser.add_argument('--interval', type=int, default=POLL_INTERVAL_SECONDS,
                       help=f'Poll interval in seconds (default: {POLL_INTERVAL_SECONDS})')
    
    args = parser.parse_args()
    
    # Update global config
    QUERY_WINDOW_MINUTES = args.window
    POLL_INTERVAL_SECONDS = args.interval
    
    # Create and run pipeline
    pipeline = RealTimeInference()
    pipeline.run(continuous=not args.once)

if __name__ == "__main__":
    main()

