#!/bin/bash

# CREDO Image Clustering Deployment Script
# This script deploys the CREDO image clustering project to the Nautilus QAIC cluster

set -e

echo "🚀 Starting CREDO Image Clustering Deployment..."

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we're connected to the right cluster
echo "📋 Checking cluster connection..."
kubectl cluster-info

# Check namespace exists
echo "📋 Checking namespace cblee-credo..."
if ! kubectl get namespace cblee-credo &> /dev/null; then
    echo "❌ Namespace cblee-credo does not exist"
    echo "Please create the namespace first: kubectl create namespace cblee-credo"
    exit 1
fi

# Apply PVCs first
echo "💾 Creating Persistent Volume Claims..."
kubectl apply -f credo-pvcs.yaml

# Wait for PVCs to be bound
echo "⏳ Waiting for PVCs to be bound..."
kubectl wait --for=condition=bound pvc/credo-pvc-cblee -n cblee-credo --timeout=300s
kubectl wait --for=condition=bound pvc/credo-data-pvc-cblee -n cblee-credo --timeout=300s
kubectl wait --for=condition=bound pvc/credo-images-pvc-cblee -n cblee-credo --timeout=300s

# Apply the deployment
echo "🚀 Deploying CREDO Image Clustering..."
kubectl apply -f credo-image-clustering-deployment.yaml

# Wait for deployment to be ready
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available deployment/credo-image-clustering -n cblee-credo --timeout=600s

# Get pod name
POD_NAME=$(kubectl get pods -n cblee-credo -l app=credo-image-clustering -o jsonpath='{.items[0].metadata.name}')

echo "✅ Deployment successful!"
echo ""
echo "📊 Deployment Status:"
kubectl get pods -n cblee-credo -l app=credo-image-clustering

echo ""
echo "🔗 To access Jupyter Notebook:"
echo "kubectl port-forward -n cblee-credo deployment/credo-image-clustering 8888:8888"
echo ""
echo "🔗 To access Flask app (if running):"
echo "kubectl port-forward -n cblee-credo deployment/credo-image-clustering 5000:5000"
echo ""
echo "📝 To view logs:"
echo "kubectl logs -f -n cblee-credo deployment/credo-image-clustering"
echo ""
echo "🔧 To execute commands in the pod:"
echo "kubectl exec -it -n cblee-credo $POD_NAME -- /bin/bash"
echo ""
echo "📁 To copy files to/from the pod:"
echo "kubectl cp local_file.txt cblee-credo/$POD_NAME:/workspace/"
echo "kubectl cp cblee-credo/$POD_NAME:/workspace/file.txt ./" 