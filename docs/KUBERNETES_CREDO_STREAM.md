# Deploy CREDO Real-Time Streamer to Kubernetes

## Overview

This guide shows how to deploy the CREDO.science real-time streamer to your Kubernetes cluster. The streamer will continuously poll the CREDO API and stream new detections directly to Elasticsearch.

## Prerequisites

- Kubernetes cluster access (NRP Nautilus)
- CREDO.science credentials (username/password or API token)
- Elasticsearch running in the cluster (already deployed)

## Quick Deploy

### Option 1: Using Username/Password

```bash
cd /Users/carlyn_oligo/git/credo-api-tools

export CREDO_USERNAME="carlynan"
export CREDO_PASSWORD="Password321!"

./deploy/07-deploy-credo-stream.sh
```

### Option 2: Using API Token

```bash
cd /Users/carlyn_oligo/git/credo-api-tools

export CREDO_TOKEN="your-api-token-here"

./deploy/07-deploy-credo-stream.sh
```

## What It Does

1. **Creates Kubernetes Secrets:**
   - `credo-credentials` (if using username/password)
   - `credo-token` (if using token)

2. **Deploys the Streamer:**
   - Runs as a Kubernetes Deployment
   - Polls CREDO API every 5 minutes
   - Streams new detections directly to Elasticsearch
   - Maintains state in pod storage

3. **Connects to Elasticsearch:**
   - Uses internal Kubernetes service: `credo-elasticsearch-es-http:9200`
   - Authenticates using existing Elasticsearch secret
   - Writes to `credo-detections` index

## Verify Deployment

### Check Pod Status

```bash
kubectl get pods -l app=credo-stream -n cblee-credo
```

### View Logs

```bash
kubectl logs -f deployment/credo-stream -n cblee-credo
```

You should see output like:
```
=== CREDO Real-Time Streamer Starting ===
CREDO.science Real-Time Streamer (Kubernetes)
======================================================================
CREDO Endpoint: https://api.credo.science/api/v2
Elasticsearch: https://credo-elasticsearch-es-http:9200
Index: credo-detections
Poll Interval: 300 seconds (5.0 minutes)
======================================================================

[2024-11-12 15:30:00] Polling CREDO API...
  Last timestamp: 0 (N/A)
  Export URL: https://s3.cloud.cyfronet.pl/credo/export_...
  ✓ Fetched 150 detections
  ✓ Imported 150 detections to Elasticsearch
  ✓ Updated last timestamp: 1731426000000
```

### Check Data in Elasticsearch

```bash
# Port-forward Elasticsearch
kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200

# In another terminal, check CREDO data count
curl -k -u "elastic:RC0hJ6vR68c29mqq5O5Hu19u" \
  "https://localhost:9200/credo-detections/_count" \
  -H "Content-Type: application/json" \
  -d '{"query": {"term": {"source": "credo-science"}}}'
```

## Configuration

### Adjust Poll Interval

Edit the deployment:
```bash
kubectl edit deployment credo-stream -n cblee-credo
```

Change the `POLL_INTERVAL` environment variable (default: 300 seconds = 5 minutes)

### Update Credentials

**Update username/password:**
```bash
kubectl create secret generic credo-credentials \
  --from-literal=username="new-username" \
  --from-literal=password="new-password" \
  -n cblee-credo \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart the deployment to pick up new credentials
kubectl rollout restart deployment/credo-stream -n cblee-credo
```

**Update token:**
```bash
kubectl create secret generic credo-token \
  --from-literal=token="new-token" \
  -n cblee-credo \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart the deployment
kubectl rollout restart deployment/credo-stream -n cblee-credo
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod events
kubectl describe pod -l app=credo-stream -n cblee-credo

# Check logs
kubectl logs -l app=credo-stream -n cblee-credo
```

### Authentication Errors

- Verify credentials are correct
- Check secret exists: `kubectl get secret credo-credentials -n cblee-credo`
- Check secret exists: `kubectl get secret credo-token -n cblee-credo`

### Elasticsearch Connection Errors

- Verify Elasticsearch is running: `kubectl get pods -n cblee-credo | grep elasticsearch`
- Check service exists: `kubectl get svc credo-elasticsearch-es-http -n cblee-credo`
- Verify Elasticsearch secret: `kubectl get secret credo-elasticsearch-es-elastic-user -n cblee-credo`

### No Data Being Imported

- Check logs for errors
- Verify CREDO API is accessible from the cluster
- Check if there's actually new data (last timestamp might be recent)

## Undeploy

To remove the streamer:

```bash
kubectl delete deployment credo-stream -n cblee-credo

# Optional: Remove secrets
kubectl delete secret credo-credentials -n cblee-credo
kubectl delete secret credo-token -n cblee-credo
```

## State Persistence

Currently, the state file (last timestamp) is stored in `emptyDir`, which means it's lost when the pod restarts. For production, you might want to use a PersistentVolumeClaim:

1. Create a PVC
2. Update the deployment to use the PVC instead of `emptyDir`

This ensures the streamer continues from the last timestamp even after pod restarts.




