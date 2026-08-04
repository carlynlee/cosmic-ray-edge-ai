#!/bin/bash

# Stop all Data Tsunami processes

set -euo pipefail

echo "Stopping Data Tsunami..."

# Stop receive streams
./deploy/stream-from-elasticsearch.sh stop

# Stop transmit coordinator
if [[ -f /tmp/tsunami_transmit.pid ]]; then
    pid=$(cat /tmp/tsunami_transmit.pid)
    kill $pid 2>/dev/null || true
    rm -f /tmp/tsunami_transmit.pid
fi

pkill -f transmit-coordinator.sh 2>/dev/null || true

echo "✅ All Data Tsunami processes stopped"

