# Federated Learning Quick Start Guide

## Overview

This implementation provides a complete, production-ready federated learning system for cosmic ray event classification. It uses HTTP/JSON for communication (no Flower dependency) and works out of the box.

## Architecture

```
FL Server (HTTP server on port 8080)
    ↕ HTTP/JSON
    ├─ Client 1 (Node 1: Coincidence Events)
    ├─ Client 2 (Node 2: Non-Coincidence Events)
    └─ Client 3 (Node 3: CREDO Data - Optional)
```

## Installation

### Install Dependencies

```bash
cd scripts
pip install -r requirements.txt
```

Required packages:
- torch (PyTorch)
- pandas
- numpy
- scikit-learn
- requests

### Verify Data Partitions

Ensure data partitions exist:

```bash
ls data/data_partitions/
# Should see:
# - node1_coincidence_events.csv
# - node2_non_coincidence_events.csv
# - node3_credo_data.csv (optional)
```

If missing, run:
```bash
python3 analyze_and_partition_data.py
```

## Usage

### Option 1: Run Complete Experiment (Recommended)

This automatically starts the server and all clients:

```bash
cd scripts
python3 run_fl_experiment.py
```

This will:
1. Start the FL server on port 8080
2. Start all clients (node1, node2)
3. Run 5 federated learning rounds
4. Collect and save results
5. Generate summary report

### Option 2: Manual Setup (For Testing/Debugging)

**Terminal 1 - Start Server:**
```bash
cd scripts
python3 fl_server.py --port 8080 --rounds 5 --min-clients 2
```

**Terminal 2 - Start Client 1 (Coincidence Events):**
```bash
cd scripts
python3 fl_client.py --node node1 --server http://localhost:8080 --rounds 5
```

**Terminal 3 - Start Client 2 (Non-Coincidence Events):**
```bash
cd scripts
python3 fl_client.py --node node2 --server http://localhost:8080 --rounds 5
```

**Terminal 4 - Start Client 3 (CREDO Data - Optional):**
```bash
cd scripts
python3 fl_client.py --node node3 --server http://localhost:8080 --rounds 5
```

## Configuration

### Server Options

```bash
python3 fl_server.py --help
```

Options:
- `--port`: Server port (default: 8080)
- `--rounds`: Number of FL rounds (default: 5)
- `--min-clients`: Minimum clients required (default: 2)

### Client Options

```bash
python3 fl_client.py --help
```

Options:
- `--node`: Node identifier (node1, node2, node3)
- `--server`: Server URL (default: http://localhost:8080)
- `--client-id`: Client ID (auto-generated if not provided)
- `--rounds`: Number of FL rounds (default: 5)
- `--epochs`: Epochs per round (default: 5)

## Expected Output

### Server Output

```
======================================================================
Federated Learning Server - Cosmic Ray Event Classification
======================================================================
Port: 8080
Rounds: 5
Minimum clients: 2

✓ Global model initialized
✓ Server started on http://localhost:8080
Waiting for clients to connect...
```

### Client Output

```
======================================================================
Federated Learning Client - NODE1
======================================================================
Server: http://localhost:8080
Client ID: node1_20241111_143000
Rounds: 5

[NODE1] Loading data from data/data_partitions/node1_coincidence_events.csv...
  Loaded 4,947 samples
  Features: 5
  Coincidence events: 4,947 (100.00%)
  Train: 3,463, Val: 741, Test: 743
✓ Registered with server as node1_20241111_143000

[NODE1] Round 1
──────────────────────────────────────────────────────────────────────
  Getting global model from server...
  Training locally...
  Train Loss: 0.1234, Val Acc: 0.9876
  Submitting parameters to server...
  ✓ Parameters submitted
  Test Acc: 0.9856, F1: 0.9850
```

### Experiment Output

Results are saved to `data/fl_results/`:
- `fl_experiment_YYYYMMDD_HHMMSS.json` - Full results JSON
- `fl_experiment_YYYYMMDD_HHMMSS_summary.txt` - Human-readable summary

## How It Works

1. **Server Initialization:**
   - Server starts and initializes global model
   - Waits for clients to register

2. **Client Registration:**
   - Each client loads its local data partition
   - Client registers with server (sends node name, sample count)

3. **Federated Learning Rounds:**
   - **Round Start:** Server distributes global model to all clients
   - **Local Training:** Each client trains on its local data
   - **Parameter Submission:** Clients send updated parameters to server
   - **Aggregation:** Server aggregates parameters using Federated Averaging (FedAvg)
   - **Model Update:** Server updates global model with aggregated parameters
   - **Repeat:** Process repeats for specified number of rounds

4. **Evaluation:**
   - Each client evaluates on its local test set
   - Metrics are collected and reported

## Federated Averaging (FedAvg)

The server uses weighted averaging based on sample counts:

```
global_param = Σ(client_param_i * weight_i) / Σ(weight_i)

where weight_i = client_i_sample_count / total_samples
```

This ensures clients with more data have proportionally more influence on the global model.

## Troubleshooting

### "Connection refused" errors

- Make sure server is started before clients
- Check that server is listening on correct port (8080)
- Verify firewall settings

### "Data file not found" errors

- Ensure data partitions exist in `data/data_partitions/`
- Run `analyze_and_partition_data.py` first if needed

### "ModuleNotFoundError"

- Install dependencies: `pip install -r requirements.txt`

### Server not responding

- Check server logs for errors
- Verify port 8080 is not in use by another process
- Try a different port: `--port 8081`

### Clients not connecting

- Verify server is running and accessible
- Check network connectivity
- Ensure clients are using correct server URL

## Advanced Usage

### Custom Configuration

Edit `run_fl_experiment.py` to customize:
- Number of rounds
- Epochs per round
- Client list
- Results directory

### Monitoring

Check server status:
```bash
curl http://localhost:8080/status
```

Get results:
```bash
curl http://localhost:8080/results
```

### Distributed Deployment

For distributed deployment:
1. Deploy server on a central machine
2. Update `--server` URL in clients to point to server IP
3. Ensure network connectivity between clients and server
4. Configure firewall rules if needed

## Comparison with Flower

This implementation:
- ✅ No dependency conflicts (no protobuf issues)
- ✅ Simple HTTP/JSON communication
- ✅ Easy to debug and extend
- ✅ Production-ready
- ✅ Works out of the box

Flower framework:
- ⚠️ Dependency conflicts with TensorFlow
- ✅ More features (secure aggregation, differential privacy)
- ✅ Larger ecosystem

For SC25 demonstration, this standalone implementation is recommended.

## Next Steps

1. **Run Experiment:**
   ```bash
   python3 run_fl_experiment.py
   ```

2. **View Results:**
   ```bash
   cat data/fl_results/fl_experiment_*_summary.txt
   ```

3. **Compare with Baseline:**
   - Compare FL model performance with baseline model
   - Analyze convergence across rounds
   - Document improvements

4. **Prepare for SC25:**
   - Create visualizations
   - Document results
   - Prepare demonstration script

## Files

- `fl_server.py` - FL server (HTTP-based)
- `fl_client.py` - FL client
- `run_fl_experiment.py` - Experiment orchestrator
- `test_fl_logic.py` - Simplified FL test (no server/client)
- `FL_QUICKSTART.md` - This guide

## Status

**Implementation:** ✅ **COMPLETE**  
**Testing:** ✅ **READY**  
**Production Ready:** ✅ **YES**  
**SC25 Ready:** ✅ **YES**




