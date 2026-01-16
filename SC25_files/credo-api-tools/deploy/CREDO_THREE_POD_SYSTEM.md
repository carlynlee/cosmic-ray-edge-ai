# CREDO Three-Pod System - Deployment Scripts

This directory contains the deployment scripts for the CREDO three-pod federated learning system, designed for the SC25 Network Research Exhibit (NRE).

## 🏗️ Architecture

The system implements a three-pod architecture:

1. **CREDO Caltech Server** → Fetches real cosmic ray data from CREDO.science
2. **Elasticsearch** → Stores and indexes the cosmic ray detection data  
3. **Caltech FL Server** → Runs federated learning algorithms on the indexed data

## 🚀 Deployment Scripts

### `00-cleanup-existing.sh`
**Purpose**: Clean up existing CREDO resources before deployment

**Usage:**
```bash
./deploy/00-cleanup-existing.sh
```

**What it does:**
- Shows current resources in the namespace
- Asks for confirmation before cleanup
- Deletes existing deployments, services, and Elasticsearch
- Waits for pods to terminate
- Prepares the environment for fresh deployment

**When to use:**
- Before deploying the system for the first time
- When you want to start with a clean slate
- After making significant changes to the deployment

### `01-deploy-credo-system.sh`
**Purpose**: Main deployment script that creates the complete three-pod system

**Usage:**
```bash
./deploy/01-deploy-credo-system.sh
```

**What it does:**
- Creates the `cblee-credo` namespace
- Deploys CREDO Caltech Server pod with GPU support
- Deploys Elasticsearch pod with persistent storage
- Deploys Caltech FL Server pod for federated learning
- Waits for all pods to be ready
- Sets up CREDO data exporter
- Fetches real data from CREDO.science
- Indexes data into Elasticsearch
- Verifies system health and shows final status

**Features:**
- Automatic resource allocation
- Real data fetching from CREDO.science
- Data indexing and verification
- Comprehensive error handling
- Status reporting

### `02-status.sh`
**Purpose**: Comprehensive status and monitoring script

**Usage:**
```bash
./deploy/02-status.sh [command]
```

**Commands:**
- `pods` - Show pod status and health
- `services` - Show service status
- `elasticsearch` - Show Elasticsearch status and data
- `resources` - Show resource usage
- `logs` - Show recent logs from all pods
- `ports` - Show port forwarding commands
- `queries` - Show Elasticsearch query examples
- `all` - Show all status information (default)

**Examples:**
```bash
./deploy/02-status.sh pods          # Show only pod status
./deploy/02-status.sh elasticsearch # Show only Elasticsearch status
./deploy/02-status.sh all           # Show all status information
```

**What it shows:**
- Pod status and health
- Service endpoints
- Elasticsearch cluster health
- Document count and indices
- Resource usage metrics
- Recent logs from all components
- Port forwarding commands
- Sample Elasticsearch queries

### `03-data-management.sh`
**Purpose**: Data management and manipulation script

**Usage:**
```bash
./deploy/03-data-management.sh [command]
```

**Commands:**
- `fetch` - Fetch more CREDO data from CREDO.science
- `index` - Index additional data into Elasticsearch
- `stats` - Show data statistics and samples
- `clear` - Clear all data from Elasticsearch

**Examples:**
```bash
./deploy/03-data-management.sh fetch    # Fetch more data
./deploy/03-data-management.sh index    # Index additional data
./deploy/03-data-management.sh stats    # Show data statistics
./deploy/03-data-management.sh clear    # Clear all data
```

**What it does:**
- Fetches additional cosmic ray data from CREDO.science
- Indexes new data into Elasticsearch
- Shows data statistics and samples
- Provides data cleanup functionality
- Handles data export timeouts gracefully

## 📋 Step-by-Step Deployment

### 1. Clean Up Existing Resources
```bash
./deploy/00-cleanup-existing.sh
```

### 2. Deploy the System
```bash
./deploy/01-deploy-credo-system.sh
```

### 3. Verify Deployment
```bash
./deploy/02-status.sh all
```

### 4. Access the System
```bash
# Get port forwarding commands
./deploy/02-status.sh ports

# Then run the commands shown
kubectl port-forward -n cblee-credo svc/credo-caltech-server-service 8888:8888
kubectl port-forward -n cblee-credo svc/caltech-fl-server-service 5000:5000
kubectl port-forward -n cblee-credo svc/credo-elasticsearch-service 9200:9200
```

## 🔧 Configuration

### Environment Variables
The scripts use the following configuration:
- **Namespace**: `cblee-credo`
- **CREDO Token**: Pre-configured in scripts
- **Image**: `gitlab-registry.nrp-nautilus.io/cloud-ai-100/qaic-docker-images:vllm-latest`

### Resource Allocation
- **CREDO Server**: 4 CPU, 16Gi memory, 1 GPU (requests); 8 CPU, 32Gi memory, 1 GPU (limits)
- **Elasticsearch**: 100m CPU, 2Gi memory (limits)
- **FL Server**: 4 CPU, 16Gi memory (requests); 8 CPU, 32Gi memory (limits)

## 📊 Data Management

### Fetching More Data
```bash
./deploy/03-data-management.sh fetch
```

### Indexing Additional Data
```bash
./deploy/03-data-management.sh index
```

### Viewing Data Statistics
```bash
./deploy/03-data-management.sh stats
```

### Clearing All Data
```bash
./deploy/03-data-management.sh clear
```

## 🔍 Monitoring

### Check System Health
```bash
./deploy/02-status.sh all
```

### View Specific Components
```bash
./deploy/02-status.sh pods
./deploy/02-status.sh elasticsearch
./deploy/02-status.sh resources
```

### View Logs
```bash
./deploy/02-status.sh logs
```

## 🛠️ Troubleshooting

### Common Issues

1. **Pods not starting**
   - Check resource availability: `kubectl describe nodes`
   - Verify GPU availability for CREDO server
   - Check resource requests/limits

2. **Elasticsearch not ready**
   - Wait longer (can take 10+ minutes)
   - Check logs: `./deploy/02-status.sh logs`
   - Verify persistent volume claims

3. **Data not indexing**
   - Check CREDO token validity
   - Verify network connectivity
   - Check data exporter logs

4. **Authentication errors**
   - Get correct password from secrets
   - Use HTTPS with self-signed certificates
   - Check Elasticsearch security settings

### Useful Commands

```bash
# Describe pods for detailed information
kubectl describe pod <pod-name> -n cblee-credo

# Execute commands in pods
kubectl exec -n cblee-credo -it <pod-name> -- bash

# Copy files to/from pods
kubectl cp <local-file> cblee-credo/<pod-name>:<remote-path>
kubectl cp cblee-credo/<pod-name>:<remote-path> <local-file>
```

## 📚 Additional Resources

- [Main README](../README.md) - Project overview
- [Deployment Guide](../DEPLOYMENT_GUIDE.md) - Detailed deployment instructions
- [CREDO.science](https://credo.science) - Cosmic Ray Extremely Distributed Observatory
- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)

## 🎯 SC25 NRE Demo

This system is designed for the Supercomputing 2025 Network Research Exhibit, demonstrating:

- Real-time cosmic ray data collection from CREDO.science
- Distributed data storage and indexing with Elasticsearch
- Federated learning coordination across network nodes
- Network performance and scalability testing

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the logs using `./deploy/02-status.sh logs`
3. Open an issue in the repository
4. Contact the development team

---

**Ready for SC25 NRE Demo! 🚀**