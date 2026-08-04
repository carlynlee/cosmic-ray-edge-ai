#!/usr/bin/env python3
"""
Run Federated Learning Experiment

This script orchestrates the federated learning experiment:
1. Starts the FL server
2. Starts multiple FL clients (in separate processes)
3. Runs federated learning rounds
4. Evaluates and compares results
"""

import subprocess
import time
import os
import sys
import signal
import json
from datetime import datetime

# Configuration
SERVER_ADDRESS = "localhost:8080"
NUM_ROUNDS = 5
CLIENTS = ['node1', 'node2']  # node3 (CREDO) optional

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import flwr
        print("✓ Flower (flwr) installed")
    except ImportError:
        print("✗ Flower (flwr) not installed")
        print("  Install with: pip install flwr")
        return False
    
    try:
        import torch
        print("✓ PyTorch installed")
    except ImportError:
        print("✗ PyTorch not installed")
        print("  Install with: pip install torch")
        return False
    
    return True

def start_server():
    """Start federated learning server"""
    print("\n" + "=" * 70)
    print("Starting Federated Learning Server")
    print("=" * 70)
    
    server_process = subprocess.Popen(
        [sys.executable, 'federated_learning_server.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(__file__)
    )
    
    # Wait a bit for server to start
    time.sleep(3)
    
    if server_process.poll() is None:
        print("✓ Server started (PID: {})".format(server_process.pid))
        return server_process
    else:
        stdout, stderr = server_process.communicate()
        print("✗ Server failed to start")
        print(stderr.decode())
        return None

def start_client(node_name, cid):
    """Start a federated learning client"""
    print(f"\nStarting client: {node_name} (CID: {cid})")
    
    client_process = subprocess.Popen(
        [sys.executable, 'federated_learning_client.py',
         '--node', node_name,
         '--server', SERVER_ADDRESS,
         '--cid', str(cid)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.path.dirname(__file__)
    )
    
    return client_process

def main():
    print("=" * 70)
    print("Federated Learning Experiment - Cosmic Ray Event Classification")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Rounds: {NUM_ROUNDS}")
    print(f"Clients: {', '.join(CLIENTS)}")
    print()
    
    # Check dependencies
    if not check_dependencies():
        print("\n✗ Missing dependencies. Please install required packages.")
        sys.exit(1)
    
    # Check data files
    data_dir = os.path.join(os.path.dirname(__file__), 'data', 'data_partitions')
    for node in CLIENTS:
        csv_file = os.path.join(data_dir, f'{node}_coincidence_events.csv' if node == 'node1' 
                                else f'{node}_non_coincidence_events.csv' if node == 'node2'
                                else f'{node}_credo_data.csv')
        if not os.path.exists(csv_file):
            print(f"✗ Data file not found: {csv_file}")
            if node == 'node3':
                print("  Note: Node 3 (CREDO) is optional, continuing without it...")
                CLIENTS.remove('node3')
            else:
                sys.exit(1)
    
    print("\n✓ All data files found")
    
    # Start server
    server_process = start_server()
    if not server_process:
        sys.exit(1)
    
    # Start clients
    client_processes = []
    try:
        for i, node in enumerate(CLIENTS):
            client_process = start_client(node, i)
            client_processes.append(client_process)
            time.sleep(2)  # Stagger client starts
        
        print(f"\n✓ Started {len(client_processes)} clients")
        print("\nFederated learning experiment running...")
        print("Press Ctrl+C to stop")
        
        # Wait for processes to complete
        server_process.wait()
        for client_process in client_processes:
            client_process.wait()
        
        print("\n✓ Experiment complete")
        
    except KeyboardInterrupt:
        print("\n\nStopping federated learning experiment...")
        
        # Terminate server
        if server_process:
            server_process.terminate()
            server_process.wait()
        
        # Terminate clients
        for client_process in client_processes:
            client_process.terminate()
            client_process.wait()
        
        print("✓ All processes stopped")
    
    # Collect results
    print("\n" + "=" * 70)
    print("Experiment Summary")
    print("=" * 70)
    print(f"Server: {SERVER_ADDRESS}")
    print(f"Clients: {len(CLIENTS)}")
    print(f"Rounds: {NUM_ROUNDS}")
    print("\nCheck server and client logs for detailed results.")

if __name__ == "__main__":
    main()




