#!/bin/bash
# Quick start script for CREDO data streamer

set -e

echo "======================================================================"
echo "CREDO.science Data Streamer - Quick Start"
echo "======================================================================"
echo ""

# Check if port-forward is needed
if ! curl -k -s -u "elastic:${ES_PASS:-RC0hJ6vR68c29mqq5O5Hu19u}" "https://localhost:9200" > /dev/null 2>&1; then
    echo "⚠️  Elasticsearch not accessible on localhost:9200"
    echo ""
    echo "You need to start port-forwarding first:"
    echo "  kubectl port-forward -n cblee-credo svc/credo-elasticsearch-es-http 9200:9200 &"
    echo ""
    read -p "Press Enter after starting port-forward, or Ctrl+C to cancel..."
    echo ""
fi

# Set default values if not already set
export ES_HOST="${ES_HOST:-https://localhost:9200}"
export ES_USER="${ES_USER:-elastic}"
export ES_PASS="${ES_PASS:-RC0hJ6vR68c29mqq5O5Hu19u}"
export ES_INDEX="${ES_INDEX:-credo-detections}"

# Check for CREDO credentials
if [ -z "$CREDO_TOKEN" ] && [ -z "$CREDO_USERNAME" ]; then
    echo "⚠️  CREDO credentials not found"
    echo ""
    echo "You can either:"
    echo "  1. Set CREDO_TOKEN environment variable"
    echo "  2. Set CREDO_USERNAME and CREDO_PASSWORD"
    echo ""
    echo "To get a token, run:"
    echo "  python3 get_credo_token.py --username your-username --password your-password"
    echo ""
    read -p "Enter CREDO_TOKEN (or press Enter to use username/password): " token
    if [ -n "$token" ]; then
        export CREDO_TOKEN="$token"
    else
        read -p "Enter CREDO_USERNAME: " username
        read -sp "Enter CREDO_PASSWORD: " password
        echo ""
        export CREDO_USERNAME="$username"
        export CREDO_PASSWORD="$password"
    fi
fi

echo ""
echo "Configuration:"
echo "  CREDO Endpoint: https://api.credo.science/api/v2"
echo "  Elasticsearch: $ES_HOST"
echo "  Index: $ES_INDEX"
if [ -n "$CREDO_TOKEN" ]; then
    echo "  Authentication: Token (${CREDO_TOKEN:0:20}...)"
else
    echo "  Authentication: Username/Password"
fi
echo ""
echo "Starting streamer..."
echo "Press Ctrl+C to stop"
echo "======================================================================"
echo ""

# Run the streamer
cd "$(dirname "$0")"
python3 stream_credo_to_elasticsearch.py




