#!/usr/bin/env python3
"""
Run Complete Federated Learning Experiment

This script orchestrates a complete federated learning experiment:
1. Starts the FL server
2. Starts multiple FL clients (in separate processes)
3. Runs federated learning rounds
4. Collects and saves results
5. Generates evaluation report
"""

import subprocess
import time
import os
import sys
import signal
import json
import requests
from datetime import datetime
from pathlib import Path

# Configuration
SERVER_ADDRESS = "http://localhost:8080"
SERVER_PORT = 8080
NUM_ROUNDS = 5
EPOCHS_PER_ROUND = 5
CLIENTS = ['node1', 'node2']  # node3 (CREDO) optional
RESULTS_DIR = 'data/fl_results'
MODEL_DIR = 'models'

def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []
    
    try:
        import torch
    except ImportError:
        missing.append('torch')
    
    try:
        import pandas
    except ImportError:
        missing.append('pandas')
    
    try:
        import numpy
    except ImportError:
        missing.append('numpy')
    
    try:
        import sklearn
    except ImportError:
        missing.append('scikit-learn')
    
    try:
        import requests
    except ImportError:
        missing.append('requests')
    
    if missing:
        print("✗ Missing dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        print("\nInstall with: pip install -r requirements.txt")
        return False
    
    print("✓ All dependencies installed")
    return True

def check_data_files():
    """Check if data files exist"""
    data_dir = Path(__file__).parent / 'data' / 'data_partitions'
    
    missing = []
    for node in CLIENTS:
        if node == 'node1':
            csv_file = data_dir / 'node1_coincidence_events.csv'
        elif node == 'node2':
            csv_file = data_dir / 'node2_non_coincidence_events.csv'
        elif node == 'node3':
            csv_file = data_dir / 'node3_credo_data.csv'
        else:
            continue
        
        if not csv_file.exists():
            if node == 'node3':
                print(f"⚠ Node 3 (CREDO) data not found, skipping...")
                if 'node3' in CLIENTS:
                    CLIENTS.remove('node3')
            else:
                missing.append(str(csv_file))
    
    if missing:
        print("✗ Missing data files:")
        for f in missing:
            print(f"  - {f}")
        print("\nRun analyze_and_partition_data.py first to create data partitions")
        return False
    
    print("✓ All required data files found")
    return True

def start_server():
    """Start federated learning server"""
    print("\n" + "=" * 70)
    print("Starting Federated Learning Server")
    print("=" * 70)
    
    server_script = Path(__file__).parent / 'fl_server.py'
    
    server_process = subprocess.Popen(
        [sys.executable, str(server_script),
         '--port', str(SERVER_PORT),
         '--rounds', str(NUM_ROUNDS),
         '--min-clients', str(len(CLIENTS))],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent
    )
    
    # Wait for server to start
    print("Waiting for server to start...")
    for i in range(10):
        time.sleep(1)
        try:
            response = requests.get(f"{SERVER_ADDRESS}/status", timeout=2)
            if response.status_code == 200:
                print("✓ Server started successfully")
                return server_process
        except:
            continue
    
    # Check if process is still running
    if server_process.poll() is None:
        print("⚠ Server process running but not responding yet")
        return server_process
    else:
        stdout, stderr = server_process.communicate()
        print("✗ Server failed to start")
        print(stderr.decode())
        return None

def start_client(node_name, client_id):
    """Start a federated learning client"""
    print(f"\nStarting client: {node_name} (ID: {client_id})")
    
    client_script = Path(__file__).parent / 'fl_client.py'
    
    client_process = subprocess.Popen(
        [sys.executable, str(client_script),
         '--node', node_name,
         '--server', SERVER_ADDRESS,
         '--client-id', client_id,
         '--rounds', str(NUM_ROUNDS),
         '--epochs', str(EPOCHS_PER_ROUND)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent
    )
    
    return client_process

def wait_for_experiment(server_process, client_processes, timeout=600):
    """Wait for experiment to complete"""
    print("\n" + "=" * 70)
    print("Federated Learning Experiment Running")
    print("=" * 70)
    print(f"Rounds: {NUM_ROUNDS}")
    print(f"Clients: {len(CLIENTS)}")
    print(f"Press Ctrl+C to stop early")
    print()
    
    start_time = time.time()
    
    try:
        # Monitor server status
        while True:
            elapsed = time.time() - start_time
            
            # Check if server is still running
            if server_process.poll() is not None:
                print("\n⚠ Server process ended")
                break
            
            # Check if all clients are done
            all_done = all(cp.poll() is not None for cp in client_processes)
            if all_done:
                print("\n✓ All clients completed")
                break
            
            # Check timeout
            if elapsed > timeout:
                print(f"\n⚠ Timeout after {timeout} seconds")
                break
            
            # Show status
            try:
                response = requests.get(f"{SERVER_ADDRESS}/status", timeout=2)
                if response.status_code == 200:
                    status = response.json()
                    print(f"\r[Status] Round: {status.get('current_round', 0)}/{NUM_ROUNDS}, "
                          f"Clients: {status.get('registered_clients', 0)}, "
                          f"Pending: {status.get('pending_parameters', 0)}", end='', flush=True)
            except:
                pass
            
            time.sleep(5)
        
        print("\n")
        
    except KeyboardInterrupt:
        print("\n\nStopping experiment...")
        return False
    
    return True

def collect_results():
    """Collect results from server"""
    print("\n" + "=" * 70)
    print("Collecting Results")
    print("=" * 70)
    
    try:
        response = requests.get(f"{SERVER_ADDRESS}/results", timeout=10)
        if response.status_code == 200:
            results = response.json()
            return results
        else:
            print("✗ Failed to get results from server")
            return None
    except Exception as e:
        print(f"✗ Error collecting results: {e}")
        return None

def save_results(results, experiment_id):
    """Save experiment results"""
    results_dir = Path(__file__).parent / RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Save results JSON
    results_file = results_dir / f"fl_experiment_{experiment_id}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✓ Results saved to {results_file}")
    
    # Generate summary report
    summary_file = results_dir / f"fl_experiment_{experiment_id}_summary.txt"
    with open(summary_file, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write("Federated Learning Experiment Summary\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Experiment ID: {experiment_id}\n")
        f.write(f"Date: {datetime.now().isoformat()}\n")
        f.write(f"Rounds: {NUM_ROUNDS}\n")
        f.write(f"Clients: {len(CLIENTS)}\n\n")
        
        if 'client_metrics' in results:
            f.write("Round-by-Round Metrics:\n")
            f.write("-" * 70 + "\n")
            for round_num, round_metrics in sorted(results['client_metrics'].items()):
                f.write(f"\nRound {round_num}:\n")
                for client_id, metrics in round_metrics.items():
                    f.write(f"  {client_id}:\n")
                    for metric_name, value in metrics.items():
                        f.write(f"    {metric_name}: {value:.4f}\n")
    
    print(f"✓ Summary saved to {summary_file}")

def main():
    print("=" * 70)
    print("Federated Learning Experiment - Cosmic Ray Event Classification")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Rounds: {NUM_ROUNDS}")
    print(f"Epochs per round: {EPOCHS_PER_ROUND}")
    print(f"Clients: {', '.join(CLIENTS)}")
    print()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check data files
    if not check_data_files():
        sys.exit(1)
    
    # Create results directory
    results_dir = Path(__file__).parent / RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate experiment ID
    experiment_id = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Start server
    server_process = start_server()
    if not server_process:
        sys.exit(1)
    
    # Start clients
    client_processes = []
    client_ids = {}
    
    try:
        for i, node in enumerate(CLIENTS):
            client_id = f"{node}_{experiment_id}"
            client_ids[node] = client_id
            client_process = start_client(node, client_id)
            client_processes.append(client_process)
            time.sleep(3)  # Stagger client starts
        
        print(f"\n✓ Started {len(client_processes)} clients")
        
        # Wait for experiment
        success = wait_for_experiment(server_process, client_processes)
        
        # Collect results
        if success:
            results = collect_results()
            if results:
                results['experiment_id'] = experiment_id
                results['config'] = {
                    'rounds': NUM_ROUNDS,
                    'epochs_per_round': EPOCHS_PER_ROUND,
                    'clients': CLIENTS
                }
                save_results(results, experiment_id)
        
        print("\n✓ Experiment complete")
        
    except KeyboardInterrupt:
        print("\n\nStopping federated learning experiment...")
        
        # Terminate clients
        for client_process in client_processes:
            if client_process.poll() is None:
                client_process.terminate()
                client_process.wait()
        
        # Terminate server
        if server_process.poll() is None:
            server_process.terminate()
            server_process.wait()
        
        print("✓ All processes stopped")
    
    finally:
        # Cleanup
        print("\n" + "=" * 70)
        print("Experiment Summary")
        print("=" * 70)
        print(f"Experiment ID: {experiment_id}")
        print(f"Server: {SERVER_ADDRESS}")
        print(f"Clients: {len(CLIENTS)}")
        print(f"Rounds: {NUM_ROUNDS}")
        print(f"\nResults saved to: {RESULTS_DIR}/")
        print("\nTo view results:")
        print(f"  cat {RESULTS_DIR}/fl_experiment_{experiment_id}_summary.txt")

if __name__ == "__main__":
    main()




