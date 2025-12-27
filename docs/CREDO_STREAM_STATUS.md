# CREDO Data Stream Integration Status

## Current Status: ⚠️ DEPLOYED BUT RATE LIMITED

### Data Import Status

**Checked:** No CREDO data has been successfully imported yet.

**Current Elasticsearch Sources:**
- `cosmicwatch-v3x`: 268,222 documents ✅
- `legacy`: 69,000 documents ✅
- `credo-science`: **0 documents** ❌

### Deployment Status

**Kubernetes Deployment:**
- ✅ Deployment exists: `credo-stream` in namespace `cblee-credo`
- ✅ Pod is running: `1/1 Ready, Running` (15+ hours uptime)
- ⚠️ **Issue:** Hitting API rate limits (429 Too Many Requests)

### Current Issue

**Problem:** CREDO API is returning `429 Too Many Requests`
- The streamer is polling every 5 minutes
- CREDO API has rate limits that are being exceeded
- No data can be imported while rate limited

**Error in logs:**
```
HTTPError: 429 Client Error: Too Many Requests for url: https://api.credo.science/api/v2/data_export
```

## Improvements Made

### 1. Rate Limit Handling ✅

**Updated:** `scripts/stream_credo_to_elasticsearch.py`

**Changes:**
- ✅ Added `RateLimitError` custom exception
- ✅ Detects 429 errors and handles gracefully
- ✅ Reads `Retry-After` header from API response
- ✅ Implements exponential backoff (default: 30 minutes when rate limited)
- ✅ Tracks consecutive rate limits and warns after 3 occurrences
- ✅ Increased default poll interval from 5 minutes to **15 minutes** (reduces API calls)

**New Features:**
- Automatic backoff when rate limited
- Respects `Retry-After` header from API
- Clear error messages with recommendations
- Prevents continuous retry loops

### 2. Configuration Updates

**Default Poll Interval:** Changed from 300s (5 min) → 900s (15 min)
- Reduces API calls by 3x
- Less likely to hit rate limits
- Still frequent enough for real-time updates

**Rate Limit Backoff:** 1800s (30 minutes)
- When rate limited, waits 30 minutes before retry
- Can be overridden with `RATE_LIMIT_BACKOFF` environment variable

## Next Steps

### Option 1: Update Running Deployment (Recommended)

Update the deployment to use the new script and poll interval:

```bash
# Update the deployment with new poll interval
kubectl set env deployment/credo-stream POLL_INTERVAL=900 -n cblee-credo

# Restart to pick up script changes
kubectl rollout restart deployment/credo-stream -n cblee-credo

# Monitor logs
kubectl logs -f deployment/credo-stream -n cblee-credo
```

### Option 2: Wait for Rate Limit to Reset

The CREDO API rate limit will reset after some time. The updated script will:
- Automatically wait when rate limited
- Use the `Retry-After` header if provided
- Resume polling once the limit resets

### Option 3: Run Locally (Bypass Kubernetes)

If Kubernetes deployment continues to have issues:

```bash
cd /Users/carlyn_oligo/git/credo-api-tools/scripts

# Set up port-forward
kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200 &

# Set environment variables
export ES_HOST="https://localhost:9200"
export ES_USER="elastic"
export ES_PASS="RC0hJ6vR68c29mqq5O5Hu19u"
export ES_INDEX="credo-detections"
export CREDO_USERNAME="your-username"
export CREDO_PASSWORD="your-password"
export POLL_INTERVAL=900  # 15 minutes

# Run with updated script
python3 stream_credo_to_elasticsearch.py
```

## Verification

After updating, check if data is being imported:

```bash
# Port-forward Elasticsearch
kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200

# Check CREDO data count
curl -k -u "elastic:RC0hJ6vR68c29mqq5O5Hu19u" \
  "https://localhost:9200/credo-detections/_count" \
  -H "Content-Type: application/json" \
  -d '{"query": {"term": {"source": "credo-science"}}}'
```

## Summary

**Status:** Script updated with rate limit handling ✅  
**Deployment:** Needs restart to pick up changes ⚠️  
**Data Import:** 0 documents (blocked by rate limits) ❌  
**Next Action:** Restart deployment with updated script and new poll interval




