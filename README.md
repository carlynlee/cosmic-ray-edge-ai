# credo-api-tools

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

Collection of tools for exporting and working with data collected by CREDO.

[https://api.credo.science](https://api.credo.science)

## Requirements
need a config file in your ~/.kube directory

## 🚀 Recent Deployment Success

**✅ Successfully deployed to Nautilus QAIC Cluster (July 19, 2025)**

- **Images Processed**: 2,354 images from `hit-images-final.zip`
- **Clustering**: 10 clusters using ResNet50 + K-means
- **Results**: Available at `./results/` directory
- **Jupyter Access**: http://localhost:8888 (when port-forward active)

### Quick Access
```bash
# Start port-forward for Jupyter
kubectl port-forward -n cblee-credo deployment/credo-image-clustering-cpu 8888:8888

# View results
ls -la results/
```

### Session Documentation
📖 Complete deployment session details: [`scripts_example/CREDO_QAIC_DEPLOYMENT_SESSION.md`](scripts_example/CREDO_QAIC_DEPLOYMENT_SESSION.md)

## create a pod on nautilus NRP cluster with Qualcomm Cloud AI 100:

  `kubectl apply -f scripts_example/fl-deployment.yaml | cat`
  `kubectl get pods -n cblee-credo`
  `kubectl port-forward -n cblee-credo deployment/fl-training 8888:8888 | cat`

## Apply Federated Learning to Pre-classified images
[https://github.com/carlynlee/FLSim/blob/main/docs/tutorials/federated_learning_for_image_classification.ipynb](https://github.com/carlynlee/FLSim/blob/main/docs/tutorials/federated_learning_for_image_classification.ipynb)

## 📊 Current Status

### Active Deployments
- **CPU Deployment**: `credo-image-clustering-cpu` (Running)
- **QAIC Deployment**: `credo-image-clustering` (Pending - waiting for QAIC resources)

### Available Resources
- **Jupyter Notebook**: http://localhost:8888
- **Results**: `./results/cluster_results.txt` and `./results/cluster_visualization.png`
- **Model**: `/data/models/kmeans_model.pkl` (in pod)

### Next Steps
1. **Explore Results**: Open Jupyter notebook
2. **QAIC Migration**: Switch to QAIC when resources available
3. **Federated Learning**: Implement FL with existing `flwr` setup
4. **Web Interface**: Deploy Flask app for image search

## 🔧 Deployment Files

### For QAIC Cluster
- `scripts_example/credo-image-clustering-deployment.yaml`
- `scripts_example/credo-image-clustering-flexible.yaml`
- `scripts_example/credo-image-clustering-cpu.yaml`

### Automation Scripts
- `scripts_example/quick-start.sh` - Complete deployment
- `scripts_example/simple-deploy.sh` - Simple deployment
- `scripts_example/deploy.sh` - Basic deployment

### Processing Scripts
- `scripts_example/cluster_local_images.py` - Image clustering
- `scripts_example/setup_images.py` - Image extraction
- `scripts_example/requirements.txt` - Dependencies
