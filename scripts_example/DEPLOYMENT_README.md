# CREDO Image Clustering - QAIC Deployment Guide

This guide explains how to deploy the CREDO image clustering project on the Nautilus cluster using Qualcomm Cloud AI 100 Ultra cards.

## Prerequisites

1. **Access to Nautilus Cluster**: Ensure you have access to the Nautilus cluster
2. **Namespace**: Your namespace `cblee-credo` should exist
3. **kubectl**: Configured to connect to the Nautilus cluster
4. **Docker Registry Access**: Access to the GitLab registry for building custom images

## Project Overview

This deployment includes:
- **Image Clustering**: Using ResNet50 and K-means clustering
- **Federated Learning**: For distributed model training
- **Elasticsearch Integration**: For image storage and retrieval
- **Flask Web Application**: For image search interface
- **Jupyter Notebooks**: For interactive development

## Files Structure

```
scripts_example/
├── credo-image-clustering-deployment.yaml  # Main deployment manifest
├── credo-pvcs.yaml                        # Persistent volume claims
├── requirements.txt                        # Python dependencies
├── Dockerfile                             # Custom container image
├── setup_images.py                        # Image extraction script
├── deploy.sh                              # Automated deployment script
├── cluster_images_from_elasticsearch.py   # Main clustering script
├── hit-images-final.zip                   # Image dataset
└── DEPLOYMENT_README.md                   # This file
```

## Deployment Steps

### 1. Build Custom Docker Image

First, you need to build and push a custom Docker image with your code:

```bash
# Navigate to the scripts_example directory
cd scripts_example

# Build the Docker image
docker build -t gitlab-registry.nrp-nautilus.io/cblee-credo/credo-image-clustering:latest .

# Push to the registry
docker push gitlab-registry.nrp-nautilus.io/cblee-credo/credo-image-clustering:latest
```

### 2. Deploy to Cluster

Use the automated deployment script:

```bash
# Make the script executable (if not already done)
chmod +x deploy.sh

# Run the deployment
./deploy.sh
```

Or deploy manually:

```bash
# Apply PVCs
kubectl apply -f credo-pvcs.yaml

# Apply deployment
kubectl apply -f credo-image-clustering-deployment.yaml

# Check status
kubectl get pods -n cblee-credo
```

### 3. Access the Application

#### Jupyter Notebook
```bash
kubectl port-forward -n cblee-credo deployment/credo-image-clustering 8888:8888
```
Then open `http://localhost:8888` in your browser.

#### Flask Application (if running)
```bash
kubectl port-forward -n cblee-credo deployment/credo-image-clustering 5000:5000
```
Then open `http://localhost:5000` in your browser.

## Configuration Details

### QAIC Configuration
- **Node Selector**: `nrp-ai-100-02.sdsc.optiputer.net`
- **Toleration**: `nautilus.io/qaic`
- **Resources**: 1 QAIC card, 4-8 CPU cores, 16-32GB RAM

### Storage Volumes
- **Code Volume**: 20Gi for code and models
- **Data Volume**: 100Gi for processed data and exports
- **Images Volume**: 50Gi for extracted images

### Environment Variables
- `PYTHONPATH=/workspace`
- `PYTHONUNBUFFERED=1`
- `TF_CPP_MIN_LOG_LEVEL=2`

## Working with the Deployment

### View Logs
```bash
kubectl logs -f -n cblee-credo deployment/credo-image-clustering
```

### Execute Commands in Pod
```bash
# Get pod name
POD_NAME=$(kubectl get pods -n cblee-credo -l app=credo-image-clustering -o jsonpath='{.items[0].metadata.name}')

# Execute bash in pod
kubectl exec -it -n cblee-credo $POD_NAME -- /bin/bash
```

### Copy Files
```bash
# Copy files to pod
kubectl cp local_file.txt cblee-credo/$POD_NAME:/workspace/

# Copy files from pod
kubectl cp cblee-credo/$POD_NAME:/workspace/file.txt ./
```

### Extract Images
Once the pod is running, you can extract the images from `hit-images-final.zip`:

```bash
# Execute the setup script
kubectl exec -n cblee-credo $POD_NAME -- python setup_images.py
```

## Troubleshooting

### Common Issues

1. **PVC Not Bound**
   ```bash
   kubectl get pvc -n cblee-credo
   kubectl describe pvc credo-pvc-cblee -n cblee-credo
   ```

2. **Pod Not Starting**
   ```bash
   kubectl describe pod -n cblee-credo -l app=credo-image-clustering
   kubectl logs -n cblee-credo deployment/credo-image-clustering
   ```

3. **QAIC Resource Issues**
   ```bash
   kubectl get nodes -l kubernetes.io/hostname=nrp-ai-100-02.sdsc.optiputer.net
   kubectl describe node nrp-ai-100-02.sdsc.optiputer.net
   ```

### Resource Monitoring
```bash
# Check resource usage
kubectl top pods -n cblee-credo

# Check node resources
kubectl top nodes
```

## Scaling and Management

### Scale Deployment
```bash
kubectl scale deployment credo-image-clustering -n cblee-credo --replicas=2
```

### Update Image
```bash
kubectl set image deployment/credo-image-clustering credo-container=gitlab-registry.nrp-nautilus.io/cblee-credo/credo-image-clustering:new-version -n cblee-credo
```

### Delete Deployment
```bash
kubectl delete deployment credo-image-clustering -n cblee-credo
kubectl delete pvc credo-pvc-cblee credo-data-pvc-cblee credo-images-pvc-cblee -n cblee-credo
```

## Additional Information

- **QAIC Documentation**: https://nrp.ai/documentation/userdocs/ai/qaic/
- **Nautilus Cluster**: https://nautilus.optiputer.net/
- **GitLab Registry**: https://gitlab-registry.nrp-nautilus.io/

## Support

For issues with:
- **QAIC Resources**: Contact Nautilus support
- **Kubernetes**: Check cluster documentation
- **Application**: Review logs and deployment status 