# 🌊 DATA TSUNAMI - Maximum Bandwidth Configuration

## Overview

This configuration maximizes bandwidth usage on RC3 pods for the SC25 Data Tsunami event by:
1. **Receiving** data from Elasticsearch at maximum rate
2. **Transmitting** data to Caltech NRP pods at maximum rate
3. Creating **bidirectional traffic** to fully utilize network links

## Configuration

### Receive Streams (From Elasticsearch)
- **20 streams per pod** × 3 pods = **60 total streams**
- Batch size: **10,000 documents**
- Polling interval: **0.1 seconds** (10 polls/second per stream)
- Total: **~600 requests/second** to Elasticsearch

### Transmit Streams (To Caltech Pods)
- **10 streams per pod** × 3 pods = **30 total streams**
- Transfer interval: **0.1 seconds**
- Continuous file copying from RC3 pods to Caltech pods
- Total: **~300 transfers/second**

### Total Network Activity
- **90 concurrent streams**
- **Bidirectional traffic** (receive + transmit)
- **Maximum bandwidth utilization**

## Usage

### Start Data Tsunami
```bash
./deploy/start-tsunami.sh
```

This will:
1. Stop any existing streams
2. Start 60 receive streams (20 per RC3 pod)
3. Start transmit coordinator (30 streams copying to Caltech)

### Check Status
```bash
./deploy/stream-from-elasticsearch.sh status
```

### Stop Data Tsunami
```bash
./deploy/stop-tsunami.sh
```

## Files

- `deploy/max-bandwidth-tsunami.sh` - Starts receive streams
- `deploy/transmit-coordinator.sh` - Coordinates transmit streams (runs on host)
- `deploy/start-tsunami.sh` - Complete startup script (RECOMMENDED)
- `deploy/stop-tsunami.sh` - Complete shutdown script
- `deploy/high-bandwidth-streamer.py` - Python streaming script
- `deploy/transmit-flood.py` - Transmit script (for reference)

## Persistence

All processes run as **daemons** 

## Event Timing

**Data Tsunami starts: 11:00 Central Time**
- 9:00 AM Pacific
- 12:00 PM Eastern
- 2:00 PM Sao Paulo
- 18:00 CET

