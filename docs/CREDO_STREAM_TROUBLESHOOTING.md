# CREDO Streamer Troubleshooting

## Issue: Connection Timeout to S3

**Error:**
```
ConnectTimeoutError: Connection to s3.cloud.cyfronet.pl timed out
```

### Root Cause

The Kubernetes pod can reach the CREDO API (gets export URL), but cannot connect to the S3 bucket (`s3.cloud.cyfronet.pl`) where the export file is stored.

### Possible Causes

1. **Network Policy** - Kubernetes NetworkPolicy may be blocking outbound connections
2. **Firewall Rules** - Cluster firewall blocking access to `s3.cloud.cyfronet.pl`
3. **DNS Resolution** - Pod cannot resolve `s3.cloud.cyfronet.pl`
4. **Egress Restrictions** - Cluster egress rules blocking S3 access

### Diagnostic Steps

#### 1. Test DNS Resolution

```bash
kubectl run -it --rm debug --image=busybox --restart=Never -n cblee-credo -- nslookup s3.cloud.cyfronet.pl
```

#### 2. Test Network Connectivity

```bash
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n cblee-credo -- curl -v -I https://s3.cloud.cyfronet.pl
```

#### 3. Check Network Policies

```bash
kubectl get networkpolicies -n cblee-credo
kubectl describe networkpolicy <policy-name> -n cblee-credo
```

#### 4. Test from Existing Pod

```bash
# Get into the credo-stream pod
kubectl exec -it deployment/credo-stream -n cblee-credo -- bash

# Inside pod, test connectivity
curl -v -I https://s3.cloud.cyfronet.pl
nslookup s3.cloud.cyfronet.pl
```

### Solutions

#### Option 1: Allow Egress to S3 (Recommended)

If you have access to NetworkPolicy configuration, allow egress to `s3.cloud.cyfronet.pl`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-credo-s3-egress
  namespace: cblee-credo
spec:
  podSelector:
    matchLabels:
      app: credo-stream
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 80
  - to: []  # Allow all egress (if no restrictions)
```

#### Option 2: Use Proxy (If Available)

If your cluster has an HTTP/HTTPS proxy, configure it in the deployment:

```yaml
env:
- name: HTTP_PROXY
  value: "http://proxy.example.com:8080"
- name: HTTPS_PROXY
  value: "http://proxy.example.com:8080"
- name: NO_PROXY
  value: "localhost,127.0.0.1,credo-elasticsearch-es-http"
```

#### Option 3: Run Locally Instead

If network policies cannot be changed, run the streamer locally:

```bash
cd /Users/carlyn_oligo/git/credo-api-tools/scripts

export CREDO_USERNAME="carlynan"
export CREDO_PASSWORD="Password321!"
export ES_HOST="https://localhost:9200"
export ES_USER="elastic"
export ES_PASS="RC0hJ6vR68c29mqq5O5Hu19u"
export ES_INDEX="credo-detections"

# Start port-forward first
kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200 &

# Run streamer
python3 stream_credo_to_elasticsearch.py
```

#### Option 4: Contact NRP Admins

If you don't have permission to modify network policies, contact NRP Nautilus administrators to:
- Allow egress to `s3.cloud.cyfronet.pl:443`
- Or configure a proxy for outbound connections

### Current Status

The streamer will:
- ✅ Continue running (won't crash)
- ✅ Retry on each poll cycle (every 5 minutes)
- ✅ Log clear error messages
- ⚠️ Not import data until network issue is resolved

### Check Logs

```bash
kubectl logs -f deployment/credo-stream -n cblee-credo
```

You should see retry attempts with clear error messages.




