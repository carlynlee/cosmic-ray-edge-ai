#!/bin/bash
# Stop the persistent port-forward

PID_FILE="${HOME}/.credo-port-forward.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No port-forward PID file found. Port-forward may not be running."
    exit 0
fi

PID=$(cat "$PID_FILE")

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "Port-forward process (PID: $PID) is not running."
    rm -f "$PID_FILE"
    exit 0
fi

echo "Stopping port-forward (PID: $PID)..."
kill "$PID" 2>/dev/null || true
rm -f "$PID_FILE"
sleep 1

if ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  Process still running, forcing kill..."
    kill -9 "$PID" 2>/dev/null || true
    sleep 1
fi

if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "✓ Port-forward stopped"
else
    echo "✗ Failed to stop port-forward"
    exit 1
fi

