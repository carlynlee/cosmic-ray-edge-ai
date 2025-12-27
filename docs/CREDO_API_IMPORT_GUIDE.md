# CREDO.science API Import Guide

## Overview

Now that `api.credo.science` is back up and working, you can import CREDO.science data to use as **Node 3** in your federated learning demonstration.

## Quick Start

### Step 1: Export Data from CREDO.science API

```bash
cd /Users/carlyn_oligo/git/credo-api-tools/data-exporter

# Export detections (you'll need your CREDO.science credentials)
python3 credo-data-exporter.py \
  --username YOUR_USERNAME \
  --password YOUR_PASSWORD \
  --endpoint https://api.credo.science/api/v2 \
  --data-type detection \
  --dir ../credo-data-export \
  --max-chunk-size 10000
```

**Note:** You can also use a token instead:
```bash
python3 credo-data-exporter.py \
  --token YOUR_TOKEN \
  --endpoint https://api.credo.science/api/v2 \
  --data-type detection \
  --dir ../credo-data-export
```

### Step 2: Process and Import to Elasticsearch

**Option A: Using the data processor (requires plugin update)**

The existing plugin needs to be updated for your Elasticsearch setup. For now, use Option B.

**Option B: Direct import script (recommended)**

I can create a simple script that:
1. Reads the exported JSON files
2. Transforms CREDO data to match your Elasticsearch schema
3. Imports directly to Elasticsearch with proper authentication

## What This Enables

With CREDO.science data imported, you'll have:

1. **Node 3 for Federated Learning:**
   - Node 1: CosmicWatch coincidence events (high-energy)
   - Node 2: CosmicWatch non-coincidence events (single-detector)
   - Node 3: CREDO.science historical data (diverse sources)

2. **More Training Data:**
   - Currently: ~40K CosmicWatch events
   - With CREDO: +69K historical events
   - Total: ~109K events for training

3. **Better Federated Learning Demo:**
   - Shows how different data sources can collaborate
   - Demonstrates real-world federated learning scenario
   - More impressive for SC25

## Data Format

CREDO.science detections include:
- `device_id` - Device identifier
- `timestamp` - Detection time
- `location` - Geographic coordinates (lat/lon)
- `user_id` - User identifier
- `team_id` - Team identifier
- `x`, `y` - Pixel coordinates
- `width`, `height` - Image dimensions
- `frame_content` - Image data (binary)

## Next Steps

1. **Export CREDO data** (Step 1 above)
2. **Create import script** that:
   - Reads exported JSON files
   - Maps CREDO fields to Elasticsearch schema
   - Adds `source: "credo-science"` field
   - Imports with proper authentication
3. **Verify import** in Kibana
4. **Update federated learning** to include Node 3

## Questions?

- Do you have CREDO.science credentials (username/password or token)?
- How much data do you want to import? (Recent data only, or historical?)
- Should I create the direct import script now?




