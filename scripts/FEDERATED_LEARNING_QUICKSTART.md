# Federated Learning Quick Start Guide

## Installation

### Install Flower Framework
```bash
pip install flwr
```

### Verify Installation
```bash
python3 -c "import flwr; print('Flower version:', flwr.__version__)"
```

## Running Federated Learning

### Option 1: Run Complete Experiment (Recommended)

This starts the server and all clients automatically:

```bash
cd scripts
python3 run_federated_experiment.py
```

### Option 2: Manual Setup (For Testing)

**Terminal 1 - Start Server:**
```bash
cd scripts
python3 federated_learning_server.py
```

**Terminal 2 - Start Client 1 (Coincidence Events):**
```bash
cd scripts
python3 federated_learning_client.py --node node1 --server localhost:8080 --cid 0
```

**Terminal 3 - Start Client 2 (Non-Coincidence Events):**
```bash
cd scripts
python3 federated_learning_client.py --node node2 --server localhost:8080 --cid 1
```

**Terminal 4 - Start Client 3 (CREDO Data - Optional):**
```bash
cd scripts
python3 federated_learning_client.py --node node3 --server localhost:8080 --cid 2
```

## Expected Output

The experiment will run 5 federated learning rounds:
- Each client trains locally on its data
- Server aggregates model parameters
- Global model is distributed back to clients
- Process repeats for multiple rounds

## Troubleshooting

### "ModuleNotFoundError: No module named 'flwr'"
```bash
pip install flwr
```

### "Connection refused" errors
- Make sure server is started before clients
- Check that server is listening on correct port (8080)

### "Data file not found" errors
- Ensure data partitions exist in `scripts/data/data_partitions/`
- Run `analyze_and_partition_data.py` first if needed

## Next Steps

After federated learning completes:
1. Compare global model vs baseline model performance
2. Analyze model convergence across rounds
3. Prepare results for SC25 demonstration




