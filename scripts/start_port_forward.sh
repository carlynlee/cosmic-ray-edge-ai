#!/bin/bash
# Persistent port-forward script for Elasticsearch
# This script runs port-forward in the background and logs output

set -e

NAMESPACE="${CREDO_NAMESPACE:-cblee-credo}"
SERVICE="credo-elasticsearch-es-http"
LOCAL_PORT=9200
REMOTE_PORT=9200
LOG_FILE="${HOME}/.credo-port-forward.log"
PID_FILE="${HOME}/.credo-port-forward.pid"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "======================================================================"
echo "CREDO Elasticsearch Port-Forward Manager"
echo "======================================================================"
echo ""

# Check if port-forward is already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Port-forward already running (PID: $OLD_PID)${NC}"
        echo "   To stop it, run: kill $OLD_PID"
        echo "   Or use: ./stop_port_forward.sh"
        echo ""
        read -p "Kill existing port-forward and start new one? (y/N): " answer
        if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
            echo "Keeping existing port-forward running."
            exit 0
        fi
        echo "Stopping existing port-forward..."
        kill "$OLD_PID" 2>/dev/null || true
        rm -f "$PID_FILE"
        sleep 2
    else
        # PID file exists but process is dead, clean up
        rm -f "$PID_FILE"
    fi
fi

# Check if port is already in use
if lsof -Pi :$LOCAL_PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}✗ Port $LOCAL_PORT is already in use${NC}"
    echo "   Please stop the process using port $LOCAL_PORT first"
    echo "   Or check if port-forward is already running: ps aux | grep port-forward"
    exit 1
fi

# Start port-forward in background with nohup
echo "Starting port-forward..."
echo "  Namespace: $NAMESPACE"
echo "  Service: $SERVICE"
echo "  Local port: $LOCAL_PORT"
echo "  Remote port: $REMOTE_PORT"
echo "  Log file: $LOG_FILE"
echo ""

# Use nohup to run in background and survive terminal closure
nohup kubectl port-forward -n "$NAMESPACE" "svc/$SERVICE" "$LOCAL_PORT:$REMOTE_PORT" > "$LOG_FILE" 2>&1 &
PF_PID=$!

# Save PID
echo "$PF_PID" > "$PID_FILE"

# Wait a moment to check if it started successfully
sleep 2

# Check if process is still running
if ! ps -p "$PF_PID" > /dev/null 2>&1; then
    echo -e "${RED}✗ Port-forward failed to start${NC}"
    echo "   Check log file: $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi

# Test connection
echo "Testing connection..."
sleep 1
if curl -k -s -u "elastic:${ES_PASS:-<YOUR_ES_PASSWORD>}" "https://localhost:$LOCAL_PORT" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Port-forward is running successfully${NC}"
    echo "  PID: $PF_PID"
    echo "  Log: $LOG_FILE"
    echo ""
    echo "To stop: kill $PF_PID"
    echo "Or use: ./stop_port_forward.sh"
    echo ""
    echo "The port-forward will continue running even if you close this terminal."
    echo "It will stop when:"
    echo "  - You manually kill it (kill $PF_PID)"
    echo "  - Your laptop shuts down"
    echo "  - The Kubernetes service becomes unavailable"
else
    echo -e "${YELLOW}⚠️  Port-forward started but connection test failed${NC}"
    echo "   This might be normal if Elasticsearch is still starting up"
    echo "   Check log: $LOG_FILE"
    echo "   PID: $PF_PID"
fi

