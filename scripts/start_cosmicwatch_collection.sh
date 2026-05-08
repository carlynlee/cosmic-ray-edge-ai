#!/bin/bash
# Start CosmicWatch data collection with Elasticsearch upload
# This script sets up environment and starts the data collection

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DATA_DIR="$PROJECT_ROOT/CosmicWatch-Desktop-Muon-Detector-v3X/Data"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "======================================================================"
echo "CosmicWatch Data Collection - Elasticsearch Upload"
echo "======================================================================"
echo ""

# Check if port-forward is running
if ! curl -k -s -u "elastic:${ES_PASS:-<YOUR_ES_PASSWORD>}" "https://localhost:9200" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Elasticsearch not accessible on localhost:9200${NC}"
    echo ""
    echo "You need to start port-forwarding first:"
    echo "  cd $SCRIPT_DIR"
    echo "  ./start_port_forward.sh"
    echo ""
    read -p "Press Enter after starting port-forward, or Ctrl+C to cancel..."
    echo ""
fi

# Set environment variables
export ES_HOST="${ES_HOST:-https://localhost:9200}"
export ES_USER="${ES_USER:-elastic}"
export ES_PASS="${ES_PASS:-<YOUR_ES_PASSWORD>}"
export ES_INDEX="${ES_INDEX:-credo-detections}"
export ES_ENABLED="${ES_ENABLED:-true}"

echo -e "${BLUE}Configuration:${NC}"
echo "  ES_HOST: $ES_HOST"
echo "  ES_USER: $ES_USER"
echo "  ES_INDEX: $ES_INDEX"
echo "  ES_ENABLED: $ES_ENABLED"
echo ""

# Test Elasticsearch connection
echo "Testing Elasticsearch connection..."
if curl -k -s -u "$ES_USER:$ES_PASS" "$ES_HOST" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connected to Elasticsearch${NC}"
else
    echo -e "${RED}✗ Failed to connect to Elasticsearch${NC}"
    echo "   Make sure port-forward is running: ./start_port_forward.sh"
    exit 1
fi

# Check if data directory exists
if [ ! -d "$DATA_DIR" ]; then
    echo -e "${RED}✗ Data directory not found: $DATA_DIR${NC}"
    exit 1
fi

# Check if script exists
if [ ! -f "$DATA_DIR/import_data_to_elasticsearch.py" ]; then
    echo -e "${RED}✗ Script not found: $DATA_DIR/import_data_to_elasticsearch.py${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Starting data collection...${NC}"
echo "  Script: $DATA_DIR/import_data_to_elasticsearch.py"
echo ""
echo "When prompted:"
echo "  - Select port: [enter the number for your CosmicWatch detector port]"
echo "  - Enter detector ID: [enter ID or press Enter for default: cosmicwatch-001]"
echo "  - Save to file too? [y/n - default: y]"
echo ""
echo "Press Ctrl+C to stop data collection"
echo ""

# Change to data directory and run script
cd "$DATA_DIR"
python3 import_data_to_elasticsearch.py

