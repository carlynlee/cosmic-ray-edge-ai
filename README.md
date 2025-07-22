# CREDO API Tools

A comprehensive toolkit for processing CREDO (Crowdsourced Radar for Everyone with Doppler Observations) image data using machine learning, clustering, and federated learning techniques.

## 🚀 Recent Deployment Success

**✅ Successfully deployed to Nautilus QAIC Cluster (July 19, 2025)**

- **Images Processed**: 2,354 images from `hit-images-final.zip`
- **Clustering**: 10 clusters using ResNet50 + K-means
- **Federated Learning**: Cluster-based federated learning with 10 device models
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

## 📊 Current Status

### Active Deployments
- **CPU Deployment**: `credo-image-clustering-cpu` (Running)
- **QAIC Deployment**: `credo-image-clustering` (Pending - waiting for QAIC resources)

### Available Resources
- **Jupyter Notebook**: http://localhost:8888
- **Results**: `./results/cluster_results.txt` and `./results/cluster_visualization.png`
- **Federated Learning Results**: `./results/federated_learning_results.json`
- **Model**: `/data/models/kmeans_model.pkl` (in pod)

## 🎯 Repository Overview

This repository provides a complete pipeline for:

1. **Image Clustering**: Group similar CREDO radar images using ResNet50 feature extraction and K-means clustering
2. **Federated Learning**: Train device-specific models that learn from their own image clusters
3. **Data Processing**: Extract and process images from CREDO datasets
4. **Visualization**: Generate insights and visualizations of clustering and learning results

## 🏗️ Architecture

### Components

- **Image Clustering Pipeline**: ResNet50 + K-means for unsupervised image grouping
- **Federated Learning System**: Flower-based federated learning with cluster-based clients
- **Data Export Tools**: Elasticsearch integration for data storage and retrieval
- **Web Interface**: Flask-based image search and visualization
- **Kubernetes Deployment**: Containerized deployment on Nautilus cluster

### Data Flow

```
hit-images-final.zip → Image Extraction → Feature Extraction → Clustering → Federated Learning
                                    ↓
                              Device Analysis → Cluster Assignment → Model Training
```

## 🚀 Quick Start Guide

### Prerequisites

1. **Kubernetes Access**: Access to Nautilus cluster with namespace `cblee-credo`
2. **Docker**: For building and pushing images
3. **kubectl**: Configured for Nautilus cluster
4. **Data**: `hit-images-final.zip` file with CREDO images

### Step 1: Deploy to Kubernetes

```bash
# Navigate to scripts directory
cd scripts_example

# Quick deployment (recommended)
./quick-start.sh

# Or simple deployment (if image already exists)
./simple-deploy.sh
```

### Step 2: Access the Deployment

```bash
# Check pod status
kubectl get pods -n cblee-credo

# Port forward for Jupyter access
kubectl port-forward -n cblee-credo deployment/credo-image-clustering-cpu 8888:8888

# Access Jupyter at http://localhost:8888
```

### Step 3: Run Image Clustering

```bash
# Execute clustering in the pod
kubectl exec -n cblee-credo credo-image-clustering-cpu-<POD_ID> -- python cluster_local_images.py
```

### Step 4: Run Federated Learning

```bash
# Execute federated learning demo
kubectl exec -n cblee-credo credo-image-clustering-cpu-<POD_ID> -- python federated_learning_demo.py
```

## 📁 File Structure

```
credo-api-tools/
├── data-exporter/           # Data export tools
├── data-processor/          # Data processing pipeline
├── scripts_example/         # Main deployment and ML scripts
│   ├── cluster_local_images.py           # Image clustering
│   ├── federated_learning_demo.py        # Federated learning
│   ├── analyze_device_ids.py             # Device analysis
│   ├── setup_images.py                   # Image extraction
│   ├── quick-start.sh                    # Complete deployment
│   ├── simple-deploy.sh                  # Simple deployment
│   ├── credo-image-clustering-cpu.yaml   # CPU deployment
│   ├── credo-image-clustering.yaml       # QAIC deployment
│   └── credo-pvcs.yaml                  # Storage configuration
├── results/                 # Generated results
└── miscellaneous/           # Additional tools
```

## 🔧 Configuration

### Kubernetes Deployments

- **CPU Deployment**: `credo-image-clustering-cpu.yaml` - General purpose CPU nodes
- **QAIC Deployment**: `credo-image-clustering.yaml` - Qualcomm AI 100 accelerators
- **Storage**: 20Gi code, 100Gi data, 50Gi images

### Federated Learning Settings

- **Clusters**: 10 image clusters (100-391 images each)
- **Training Rounds**: 5 federated learning rounds
- **Model**: ResNet50 + classification head
- **Batch Size**: 32, Epochs: 3 per round

## 📊 Results and Outputs

### Clustering Results
- **Cluster Distribution**: 10 clusters with 100-391 images each
- **Visualization**: PCA scatter plot of clusters
- **Model**: K-means model saved as `kmeans_model.pkl`

### Federated Learning Results
- **Training History**: Per-cluster training metrics
- **Global Model**: Federated averaged model weights
- **Evaluation**: Cross-cluster performance metrics
- **Visualization**: Training progression and final accuracy

### Output Files
```
/data/exports/
├── cluster_results.txt                    # Cluster assignments
├── cluster_visualization.png             # PCA visualization
├── federated_learning_results.json       # FL training results
├── federated_learning_visualization.png  # FL training plots
├── device_id_analysis.json               # Device distribution
└── device_image_mapping.csv              # Device-image mapping
```

## 🎯 Use Cases

### 1. Image Clustering
- **Purpose**: Group similar CREDO radar images
- **Method**: ResNet50 feature extraction + K-means
- **Output**: 10 clusters with visualizations

### 2. Federated Learning
- **Purpose**: Train models on device-specific data
- **Method**: Flower-based federated learning
- **Output**: Collaborative model without data sharing

### 3. Device Analysis
- **Purpose**: Understand device distribution
- **Method**: Extract device IDs from filenames
- **Output**: Device statistics and mappings

## 🔍 Troubleshooting

### Common Issues

1. **Pod Pending**: QAIC resources unavailable
   ```bash
   # Use CPU deployment instead
   kubectl apply -f credo-image-clustering-cpu.yaml
   ```

2. **Port Forward Issues**: Connection lost
   ```bash
   # Restart port forward
   kubectl port-forward -n cblee-credo deployment/credo-image-clustering-cpu 8888:8888
   ```

3. **Missing Dependencies**: Module not found
   ```bash
   # Install in pod
   kubectl exec -n cblee-credo <POD_NAME> -- pip install <PACKAGE>
   ```

### Debugging Commands

```bash
# Check pod logs
kubectl logs -n cblee-credo <POD_NAME>

# Check pod status
kubectl describe pod -n cblee-credo <POD_NAME>

# Access pod shell
kubectl exec -it -n cblee-credo <POD_NAME> -- /bin/bash
```

## 📈 Performance Metrics

### Current Results
- **Images Processed**: 2,354
- **Clusters Created**: 10
- **Federated Learning Rounds**: 5
- **Training Time**: ~15 minutes (CPU)
- **Memory Usage**: ~16Gi
- **Storage Used**: ~170Gi total

### Expected QAIC Performance
- **Training Speed**: 3-5x faster than CPU
- **Memory**: 32Gi available
- **GPU**: Qualcomm AI 100 acceleration

## 🔮 Next Steps

1. **QAIC Migration**: Switch to QAIC when resources available
2. **Web Interface**: Deploy Flask app for image search
3. **Real-time Processing**: Stream processing for new images
4. **Advanced FL**: Multi-round federated learning with more devices
5. **Model Optimization**: Quantization and optimization for edge deployment

## 📚 Documentation

- **Deployment Guide**: [`scripts_example/DEPLOYMENT_README.md`](scripts_example/DEPLOYMENT_README.md)
- **Session Log**: [`scripts_example/CREDO_QAIC_DEPLOYMENT_SESSION.md`](scripts_example/CREDO_QAIC_DEPLOYMENT_SESSION.md)
- **API Documentation**: See individual script docstrings

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with the deployment scripts
5. Submit a pull request

## 📄 License

See [LICENSE](LICENSE) file for details.

## 🔗 Related Links

- [Nautilus Cluster Documentation](https://nrp.ai/documentation/userdocs/ai/qaic/)
- [Flower Federated Learning](https://flower.dev/)
- [CREDO Project](https://credo.science/)

---

**Last Updated**: July 22, 2025  
**Status**: ✅ Active deployment with federated learning capabilities  
**Contact**: For issues, create an issue in this repository
