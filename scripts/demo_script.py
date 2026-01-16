#!/usr/bin/env python3
"""
SC25 Demonstration Script

Orchestrates the complete demonstration pipeline:
- Data collection monitoring
- Real-time inference
- Visualization dashboard
- Status reporting
"""

import os
import sys
import time
import subprocess
import signal
import requests
from datetime import datetime
from urllib3.exceptions import InsecureRequestWarning
import warnings
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

# Configuration
# Default to HTTP for localhost port-forwarding
ES_HOST = os.getenv('ES_HOST', 'http://localhost:9200')
ES_USER = os.getenv('ES_USER', 'elastic')
ES_PASS = os.getenv('ES_PASS', '')
ES_INDEX = os.getenv('ES_INDEX', 'credo-detections')

class DemoOrchestrator:
    """Orchestrates the demonstration"""
    
    def __init__(self):
        self.processes = []
        self.running = True
        
    def check_elasticsearch(self):
        """Check if Elasticsearch is accessible"""
        url = f"{ES_HOST}/_cluster/health"
        auth = (ES_USER, ES_PASS)
        
        # Use HTTP for localhost, HTTPS for remote
        use_https = not ('localhost' in ES_HOST or '127.0.0.1' in ES_HOST)
        
        try:
            response = requests.get(url, auth=auth, verify=False, timeout=5)
            response.raise_for_status()
            health = response.json()
            return health.get('status') == 'green' or health.get('status') == 'yellow'
        except requests.exceptions.SSLError as e:
            # If SSL error on localhost, try HTTP instead
            if not use_https and ES_HOST.startswith('https://'):
                http_url = ES_HOST.replace('https://', 'http://')
                url = f"{http_url}/_cluster/health"
                try:
                    response = requests.get(url, auth=auth, timeout=5)
                    response.raise_for_status()
                    health = response.json()
                    return health.get('status') == 'green' or health.get('status') == 'yellow'
                except Exception as e2:
                    print(f"✗ Elasticsearch not accessible (HTTP fallback): {e2}")
                    return False
            else:
                print(f"✗ Elasticsearch SSL error: {e}")
                return False
        except Exception as e:
            print(f"✗ Elasticsearch not accessible: {e}")
            return False
    
    def check_data_collection(self):
        """Check if data is being collected"""
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"source": "cosmicwatch-v3x"}},
                        {"range": {
                            "timestamp": {
                                "gte": (datetime.utcnow().isoformat()[:-7] + "Z")
                            }
                        }}
                    ]
                }
            },
            "size": 1
        }
        
        url = f"{ES_HOST}/{ES_INDEX}/_search"
        auth = (ES_USER, ES_PASS)
        
        # Use HTTP for localhost, HTTPS for remote
        use_https = not ('localhost' in ES_HOST or '127.0.0.1' in ES_HOST)
        
        try:
            response = requests.post(url, json=query, auth=auth, verify=False, timeout=5)
            response.raise_for_status()
            hits = response.json().get('hits', {}).get('hits', [])
            return len(hits) > 0
        except requests.exceptions.SSLError as e:
            # If SSL error on localhost, try HTTP instead
            if not use_https and ES_HOST.startswith('https://'):
                http_url = ES_HOST.replace('https://', 'http://')
                url = f"{http_url}/{ES_INDEX}/_search"
                try:
                    response = requests.post(url, json=query, auth=auth, timeout=5)
                    response.raise_for_status()
                    hits = response.json().get('hits', {}).get('hits', [])
                    return len(hits) > 0
                except Exception as e2:
                    print(f"✗ Error checking data (HTTP fallback): {e2}")
                    return False
            else:
                print(f"✗ SSL Error checking data: {e}")
                return False
        except Exception as e:
            print(f"✗ Error checking data: {e}")
            return False
    
    def get_recent_count(self, minutes=5):
        """Get count of recent events"""
        start_time = datetime.utcnow().isoformat()[:-7] + "Z"
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"source": "cosmicwatch-v3x"}},
                        {"range": {
                            "timestamp": {
                                "gte": start_time
                            }
                        }}
                    ]
                }
            },
            "size": 0
        }
        
        url = f"{ES_HOST}/{ES_INDEX}/_search"
        auth = (ES_USER, ES_PASS)
        
        # Use HTTP for localhost, HTTPS for remote
        use_https = not ('localhost' in ES_HOST or '127.0.0.1' in ES_HOST)
        
        try:
            response = requests.post(url, json=query, auth=auth, verify=False, timeout=5)
            response.raise_for_status()
            return response.json().get('hits', {}).get('total', {}).get('value', 0)
        except requests.exceptions.SSLError:
            # If SSL error on localhost, try HTTP instead
            if not use_https and ES_HOST.startswith('https://'):
                http_url = ES_HOST.replace('https://', 'http://')
                url = f"{http_url}/{ES_INDEX}/_search"
                try:
                    response = requests.post(url, json=query, auth=auth, timeout=5)
                    response.raise_for_status()
                    return response.json().get('hits', {}).get('total', {}).get('value', 0)
                except:
                    return 0
            else:
                return 0
        except:
            return 0
    
    def print_status(self):
        """Print current status"""
        print("\n" + "=" * 70)
        print("SC25 Demonstration Status")
        print("=" * 70)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Check Elasticsearch
        es_ok = self.check_elasticsearch()
        print(f"Elasticsearch: {'✓ Connected' if es_ok else '✗ Not accessible'}")
        
        # Check data collection
        data_ok = self.check_data_collection()
        recent_count = self.get_recent_count(minutes=5)
        print(f"Data Collection: {'✓ Active' if data_ok else '✗ No recent data'}")
        print(f"  Recent events (last 5 min): {recent_count}")
        print()
        
        # Component status
        print("Components:")
        print(f"  - Real-time Inference: {'Running' if any('inference' in str(p) for p in self.processes) else 'Not running'}")
        print(f"  - Visualization Dashboard: {'Running' if any('dashboard' in str(p) for p in self.processes) else 'Not running'}")
        print()
        
        print("=" * 70)
        print()
    
    def start_inference(self):
        """Start real-time inference pipeline"""
        print("Starting real-time inference pipeline...")
        try:
            process = subprocess.Popen(
                [sys.executable, 'real_time_inference.py'],
                cwd=os.path.dirname(__file__),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes.append(('inference', process))
            print("✓ Inference pipeline started")
            return True
        except Exception as e:
            print(f"✗ Error starting inference: {e}")
            return False
    
    def start_dashboard(self):
        """Start visualization dashboard"""
        print("Starting visualization dashboard...")
        try:
            process = subprocess.Popen(
                [sys.executable, 'visualization_dashboard.py'],
                cwd=os.path.dirname(__file__),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.processes.append(('dashboard', process))
            print("✓ Dashboard started")
            return True
        except Exception as e:
            print(f"✗ Error starting dashboard: {e}")
            return False
    
    def stop_all(self):
        """Stop all processes"""
        print("\nStopping all processes...")
        for name, process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✓ Stopped {name}")
            except:
                process.kill()
                print(f"✓ Killed {name}")
        self.processes = []
    
    def run(self):
        """Run demonstration"""
        print("=" * 70)
        print("SC25 Demonstration Script")
        print("=" * 70)
        print()
        
        # Initial status
        self.print_status()
        
        # Check prerequisites
        if not self.check_elasticsearch():
            print("Error: Elasticsearch is not accessible")
            print("Please ensure Elasticsearch is running and port-forwarded")
            return
        
        # Ask user what to start
        print("What would you like to start?")
        print("  1. Real-time inference pipeline")
        print("  2. Visualization dashboard")
        print("  3. Both")
        print("  4. Status check only")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            self.start_inference()
        elif choice == '2':
            self.start_dashboard()
        elif choice == '3':
            self.start_inference()
            time.sleep(2)
            self.start_dashboard()
        elif choice == '4':
            pass
        else:
            print("Invalid choice")
            return
        
        # Monitor loop
        if self.processes:
            print("\nMonitoring (Ctrl+C to stop)...")
            print()
            
            try:
                while True:
                    time.sleep(30)
                    self.print_status()
                    
                    # Check if processes are still running
                    for name, process in list(self.processes):
                        if process.poll() is not None:
                            print(f"⚠ {name} process exited")
                            self.processes.remove((name, process))
                    
            except KeyboardInterrupt:
                print("\nStopping...")
                self.stop_all()
        else:
            # Just status check
            print("\nStatus check complete")

def signal_handler(sig, frame):
    """Handle Ctrl+C"""
    print("\n\nInterrupted by user")
    sys.exit(0)

def main():
    """Main function"""
    signal.signal(signal.SIGINT, signal_handler)
    
    orchestrator = DemoOrchestrator()
    orchestrator.run()

if __name__ == "__main__":
    main()

