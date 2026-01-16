#!/bin/bash

# Complete Data Tsunami startup script
# Starts both receive and transmit at maximum bandwidth

set -euo pipefail

echo "🌊 Starting DATA TSUNAMI - Maximum Bandwidth Configuration"
echo ""

# Stop any existing streams
./deploy/stream-from-elasticsearch.sh stop 2>/dev/null || true
pkill -f transmit-coordinator.sh 2>/dev/null || true
sleep 2

# Start receive streams (from Elasticsearch)
echo "📥 Starting RECEIVE streams (from Elasticsearch)..."
./deploy/max-bandwidth-tsunami.sh

# Wait a moment for receive streams to generate data
sleep 5

# Start transmit coordinator (from host, copies to Caltech)
echo ""
echo "📤 Starting TRANSMIT coordinator (to Caltech pods)..."
nohup ./deploy/transmit-coordinator.sh > /tmp/tsunami_transmit.log 2>&1 &
echo $! > /tmp/tsunami_transmit.pid

echo ""
echo "✅ DATA TSUNAMI ACTIVATED!"
echo ""
echo "Status:"
echo "  - Receive streams: Running in RC3 pods"
echo "  - Transmit coordinator: PID $(cat /tmp/tsunami_transmit.pid)"
echo ""
echo "To check status: ./deploy/stream-from-elasticsearch.sh status"
echo "To stop: ./deploy/stop-tsunami.sh"

