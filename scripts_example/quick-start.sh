#!/bin/bash

# CREDO Image Clustering - Quick Start Deployment
# This script handles the complete deployment process

set -e

echo "🚀 CREDO Image Clustering - Quick Start Deployment"
echo "=================================================="

# Configuration
REGISTRY="gitlab-registry.nrp-nautilus.io"
NAMESPACE="cblee-credo"
IMAGE_NAME="credo-image-clustering"
FULL_IMAGE_NAME="$REGISTRY/$NAMESPACE/$IMAGE_NAME:latest"

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed or not in PATH"
    exit 1
fi

# Check namespace exists (namespace-specific check)
echo "📋 Checking namespace $NAMESPACE..."
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    echo "❌ Namespace $NAMESPACE does not exist"
    echo "Please create the namespace first: kubectl create namespace $NAMESPACE"
    exit 1
fi

# Check permissions in namespace
echo "📋 Checking permissions in namespace $NAMESPACE..."
if ! kubectl auth can-i create deployments --namespace $NAMESPACE &> /dev/null; then
    echo "❌ No permission to create deployments in namespace $NAMESPACE"
    exit 1
fi

if ! kubectl auth can-i create pvc --namespace $NAMESPACE &> /dev/null; then
    echo "❌ No permission to create PVCs in namespace $NAMESPACE"
    exit 1
fi

echo "✅ Permissions verified for namespace $NAMESPACE"

# Build and push Docker image
echo "🐳 Building Docker image..."
docker build -t $FULL_IMAGE_NAME .

echo "📤 Pushing Docker image to registry..."
docker push $FULL_IMAGE_NAME

# Deploy to cluster
echo "🚀 Deploying to cluster..."

# Apply PVCs
echo "💾 Creating Persistent Volume Claims..."
kubectl apply -f credo-pvcs.yaml

# Wait for PVCs to be bound
echo "⏳ Waiting for PVCs to be bound..."
kubectl wait --for=condition=bound pvc/credo-pvc-cblee -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=bound pvc/credo-data-pvc-cblee -n $NAMESPACE --timeout=300s
kubectl wait --for=condition=bound pvc/credo-images-pvc-cblee -n $NAMESPACE --timeout=300s

# Apply the deployment
echo "🚀 Deploying CREDO Image Clustering..."
kubectl apply -f credo-image-clustering-deployment.yaml

# Wait for deployment to be ready
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available deployment/credo-image-clustering -n $NAMESPACE --timeout=600s

# Get pod name
POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=credo-image-clustering -o jsonpath='{.items[0].metadata.name}')

echo "✅ Deployment successful!"
echo ""
echo "📊 Deployment Status:"
kubectl get pods -n $NAMESPACE -l app=credo-image-clustering

echo ""
echo "🔗 To access Jupyter Notebook:"
echo "kubectl port-forward -n $NAMESPACE deployment/credo-image-clustering 8888:8888"
echo ""
echo "🔗 To access Flask app (if running):"
echo "kubectl port-forward -n $NAMESPACE deployment/credo-image-clustering 5000:5000"
echo ""
echo "📝 To view logs:"
echo "kubectl logs -f -n $NAMESPACE deployment/credo-image-clustering"
echo ""
echo "🔧 To execute commands in the pod:"
echo "kubectl exec -it -n $NAMESPACE $POD_NAME -- /bin/bash"
echo ""
echo "📁 To extract images from hit-images-final.zip:"
echo "kubectl exec -n $NAMESPACE $POD_NAME -- python setup_images.py"
echo ""
echo "🎉 Quick start complete! Your CREDO image clustering environment is ready." 