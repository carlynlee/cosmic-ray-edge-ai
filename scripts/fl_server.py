#!/usr/bin/env python3
"""
Federated Learning Server for Cosmic Ray Event Classification

Standalone FL server that coordinates federated learning across multiple clients.
Uses HTTP/JSON for communication (no Flower dependency).

This server:
- Coordinates federated learning rounds
- Aggregates model parameters from clients
- Distributes global model to clients
- Tracks training metrics
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import numpy as np
import torch
from typing import Dict, List
from datetime import datetime

# Import model architecture
from train_binary_baseline import BinaryCoincidenceClassifier

class FLServerHandler(BaseHTTPRequestHandler):
    """HTTP request handler for FL server"""
    
    def log_message(self, format, *args):
        """Override to use custom logging"""
        pass  # Suppress default logging
    
    def do_POST(self):
        """Handle POST requests from clients"""
        parsed_path = urlparse(self.path)
        endpoint = parsed_path.path
        
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode('utf-8'))
        except:
            data = {}
        
        # Route requests
        if endpoint == '/register':
            response = self.server.fl_server.register_client(data)
        elif endpoint == '/submit_params':
            response = self.server.fl_server.submit_parameters(data)
        elif endpoint == '/get_global_model':
            response = self.server.fl_server.get_global_model(data)
        elif endpoint == '/submit_metrics':
            response = self.server.fl_server.submit_metrics(data)
        else:
            response = {'error': 'Unknown endpoint'}
        
        # Send response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        endpoint = parsed_path.path
        
        if endpoint == '/status':
            response = self.server.fl_server.get_status()
        elif endpoint == '/results':
            response = self.server.fl_server.get_results()
        else:
            response = {'error': 'Unknown endpoint'}
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

class FederatedLearningServer:
    """Federated Learning Server"""
    
    def __init__(self, num_rounds=5, min_clients=2, port=8080):
        self.num_rounds = num_rounds
        self.min_clients = min_clients
        self.port = port
        
        # Client registry
        self.clients = {}  # client_id -> {node_name, sample_count, last_seen}
        
        # Model state
        self.current_round = 0
        self.global_model = None
        self.client_parameters = {}  # client_id -> parameters
        self.client_metrics = {}  # round -> {client_id -> metrics}
        
        # Results tracking
        self.round_history = []
        self.start_time = None
        
        # Initialize global model
        self._init_global_model()
    
    def _init_global_model(self):
        """Initialize global model"""
        self.global_model = BinaryCoincidenceClassifier(
            input_size=5,
            hidden_sizes=[64, 32]
        )
        print("✓ Global model initialized")
    
    def register_client(self, data: Dict) -> Dict:
        """Register a new client"""
        client_id = data.get('client_id')
        node_name = data.get('node_name', 'unknown')
        sample_count = data.get('sample_count', 0)
        
        if client_id:
            self.clients[client_id] = {
                'node_name': node_name,
                'sample_count': sample_count,
                'last_seen': time.time(),
                'registered_at': datetime.now().isoformat()
            }
            print(f"✓ Client registered: {client_id} ({node_name}, {sample_count:,} samples)")
            return {'status': 'registered', 'client_id': client_id}
        else:
            return {'error': 'Missing client_id'}
    
    def submit_parameters(self, data: Dict) -> Dict:
        """Receive model parameters from a client"""
        client_id = data.get('client_id')
        round_num = data.get('round', 0)
        parameters = data.get('parameters')  # List of numpy arrays (serialized as lists)
        sample_count = data.get('sample_count', 0)
        
        if not client_id or parameters is None:
            return {'error': 'Missing client_id or parameters'}
        
        # Convert to numpy arrays
        params_np = [np.array(p) for p in parameters]
        self.client_parameters[client_id] = {
            'parameters': params_np,
            'sample_count': sample_count,
            'round': round_num
        }
        
        # Update client last seen
        if client_id in self.clients:
            self.clients[client_id]['last_seen'] = time.time()
        
        print(f"✓ Received parameters from {client_id} (round {round_num}, {sample_count:,} samples)")
        
        # Check if we have enough clients for this round
        if len(self.client_parameters) >= self.min_clients:
            return {'status': 'received', 'ready_for_aggregation': True}
        else:
            return {'status': 'received', 'ready_for_aggregation': False}
    
    def submit_metrics(self, data: Dict) -> Dict:
        """Receive training metrics from a client"""
        client_id = data.get('client_id')
        round_num = data.get('round', 0)
        metrics = data.get('metrics', {})
        
        if round_num not in self.client_metrics:
            self.client_metrics[round_num] = {}
        
        self.client_metrics[round_num][client_id] = metrics
        return {'status': 'received'}
    
    def aggregate_parameters(self) -> List[np.ndarray]:
        """Aggregate client parameters using Federated Averaging (FedAvg)"""
        if not self.client_parameters:
            return None
        
        # Get total sample count
        total_samples = sum(cp['sample_count'] for cp in self.client_parameters.values())
        
        if total_samples == 0:
            return None
        
        # Weighted average of parameters
        aggregated = []
        num_params = len(list(self.client_parameters.values())[0]['parameters'])
        
        for param_idx in range(num_params):
            weighted_sum = None
            for client_id, cp in self.client_parameters.items():
                weight = cp['sample_count'] / total_samples
                param = cp['parameters'][param_idx]
                
                if weighted_sum is None:
                    weighted_sum = param * weight
                else:
                    weighted_sum += param * weight
            
            aggregated.append(weighted_sum)
        
        return aggregated
    
    def get_global_model(self, data: Dict) -> Dict:
        """Get global model parameters for a client"""
        client_id = data.get('client_id', '')
        round_num = data.get('round', 0)
        
        # If we have enough parameters, aggregate them
        if len(self.client_parameters) >= self.min_clients:
            aggregated_params = self.aggregate_parameters()
            
            if aggregated_params is not None:
                # Update global model
                state_dict = self.global_model.state_dict()
                param_idx = 0
                for key in state_dict.keys():
                    if param_idx < len(aggregated_params):
                        state_dict[key] = torch.tensor(aggregated_params[param_idx])
                        param_idx += 1
                self.global_model.load_state_dict(state_dict)
                
                # Clear client parameters for next round
                self.client_parameters = {}
                
                # Convert to list for JSON serialization
                params_list = [p.tolist() for p in aggregated_params]
                
                print(f"✓ Aggregated parameters from {len(self.clients)} clients")
                return {
                    'status': 'success',
                    'parameters': params_list,
                    'round': self.current_round
                }
        
        # Return current global model
        state_dict = self.global_model.state_dict()
        params_list = [v.cpu().numpy().tolist() for v in state_dict.values()]
        
        return {
            'status': 'success',
            'parameters': params_list,
            'round': self.current_round
        }
    
    def get_status(self) -> Dict:
        """Get server status"""
        return {
            'current_round': self.current_round,
            'num_rounds': self.num_rounds,
            'registered_clients': len(self.clients),
            'min_clients': self.min_clients,
            'clients': {cid: {
                'node_name': info['node_name'],
                'sample_count': info['sample_count']
            } for cid, info in self.clients.items()},
            'pending_parameters': len(self.client_parameters)
        }
    
    def get_results(self) -> Dict:
        """Get training results"""
        return {
            'round_history': self.round_history,
            'client_metrics': self.client_metrics,
            'current_round': self.current_round
        }
    
    def start_round(self, round_num: int):
        """Start a new federated learning round"""
        self.current_round = round_num
        self.client_parameters = {}
        print(f"\n{'='*70}")
        print(f"Starting Round {round_num}/{self.num_rounds}")
        print(f"{'='*70}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Federated Learning Server')
    parser.add_argument('--port', type=int, default=8080, help='Server port (default: 8080)')
    parser.add_argument('--rounds', type=int, default=5, help='Number of FL rounds (default: 5)')
    parser.add_argument('--min-clients', type=int, default=2, help='Minimum clients required (default: 2)')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Federated Learning Server - Cosmic Ray Event Classification")
    print("=" * 70)
    print(f"Port: {args.port}")
    print(f"Rounds: {args.rounds}")
    print(f"Minimum clients: {args.min_clients}")
    print()
    
    # Create server
    fl_server = FederatedLearningServer(
        num_rounds=args.rounds,
        min_clients=args.min_clients,
        port=args.port
    )
    
    # Create HTTP server
    server_address = ('', args.port)
    httpd = HTTPServer(server_address, FLServerHandler)
    httpd.fl_server = fl_server
    
    print(f"✓ Server started on http://localhost:{args.port}")
    print("Waiting for clients to connect...")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nStopping server...")
        httpd.shutdown()
        print("✓ Server stopped")

if __name__ == "__main__":
    main()

