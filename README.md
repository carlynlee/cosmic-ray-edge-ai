# CREDO API Tools

Tools for collecting, processing, and visualizing cosmic ray detection data from CREDO.science and CosmicWatch Desktop Muon Detector v3X.

## Project Overview

**Purpose:** Collect and visualize real-time cosmic ray detection data from multiple sources including CREDO.science API and CosmicWatch Desktop Muon Detector v3X devices.

**Key Features:**
- Real-time data streaming from CosmicWatch detectors
- CREDO.science API data import
- Elasticsearch data storage and indexing
- Kibana visualization dashboard
- Public access to Kibana dashboard for real-time monitoring

## Quick Start

### Prerequisites
- Python 3.8+
- Kubernetes cluster access (NRP Nautilus)
- `kubectl` configured for NRP cluster
- Elasticsearch and Kibana deployed in Kubernetes

### Local Development

#### Clone the Repository
```bash
git clone https://github.com/carlynlee/credo-api-tools.git
cd credo-api-tools

# Initialize submodules (CosmicWatch detector scripts)
git submodule update --init --recursive
```

#### Install Dependencies
```bash
# For data export/import
pip install requests elasticsearch pyserial

# Or install from requirements if available
pip install -r requirements.txt
```

### CosmicWatch Data Collection

#### Stream Data to Elasticsearch
```bash
# Set up port-forward to Elasticsearch
kubectl port-forward -n cblee-credo svc/credo-elasticsearch-service 9200:9200 &

# Set environment variables
export ES_HOST="https://localhost:9200"
export ES_USER="elastic"
export ES_PASS="your-elasticsearch-password"
export ES_INDEX="credo-detections"
export ES_ENABLED="true"

# Run the CosmicWatch data import script
cd CosmicWatch-Desktop-Muon-Detector-v3X/Data
python3 import_data_to_elasticsearch.py
```

See [CosmicWatch-Desktop-Muon-Detector-v3X/Data/README.txt](CosmicWatch-Desktop-Muon-Detector-v3X/Data/README.txt) for detailed instructions.

### CREDO.science Data Import

#### Export Data from CREDO.science API
```bash
cd data-exporter
python3 credo-data-exporter.py \
  --username your-username \
  --password your-password \
  --endpoint https://api.credo.science/api/v2 \
  --dir ../credo-data-export
```

#### Process and Index to Elasticsearch
```bash
cd data-processor
python3 credo-data-processor.py \
  --dir ../credo-data-export \
  --plugin-dir plugins
```

### Kubernetes Deployment

#### Deploy CREDO Data Streaming
```bash
# Deploy the data streaming cronjob
./deploy/06-deploy-credo-data-stream.sh

# Check deployment status
kubectl get cronjob -n cblee-credo
kubectl get pods -n cblee-credo
```

#### Access Elasticsearch
```bash
# Port-forward Elasticsearch
kubectl port-forward -n cblee-credo svc/credo-elasticsearch-service 9200:9200

# Query Elasticsearch
curl -k -u "elastic:password" https://localhost:9200/credo-detections/_count
```

#### Access Kibana Dashboard

**Public Access (Recommended):**
- URL: https://credo-kibana.nrp-nautilus.io
- Username: `elastic`
- Password: (check Kubernetes secret: `credo-elasticsearch-es-elastic-user`)

**Local Access (via port-forward):**
```bash
# Port-forward Kibana
kubectl port-forward -n cblee-credo svc/credo-kibana-kb-http 5601:5601

# Open in browser
open http://localhost:5601
```

#### Deploy Public Kibana Access
```bash
# Apply Ingress configuration
kubectl apply -f kibana-public-ingress.yaml

# Apply certificate configuration (if using cert-manager)
kubectl apply -f kibana-certificate.yaml
```

## Project Structure

```
credo-api-tools/
├── README.md                                    # This file
├── kibana-public-ingress.yaml                   # Kibana public access configuration
├── kibana-certificate.yaml                      # TLS certificate configuration
├── deploy/                                      # Deployment scripts
│   ├── 06-deploy-credo-data-stream.sh          # Deploy data streaming cronjob
│   ├── credo-data-indexing-helpers.sh          # Helper scripts for data indexing
│   ├── credo-data-stream-cronjob.yaml          # Kubernetes cronjob for data streaming
│   └── setup-kibana-geo-visualization.py       # Kibana geo-visualization setup
├── CosmicWatch-Desktop-Muon-Detector-v3X/       # CosmicWatch detector submodule
│   └── Data/
│       ├── import_data_to_elasticsearch.py     # Real-time data import script
│       └── README.txt                          # CosmicWatch data import documentation
├── data-exporter/                               # CREDO.science API export tools
│   └── credo-data-exporter.py                   # Export data from CREDO.science API
└── data-processor/                              # Data processing and indexing
    ├── credo-data-processor.py                  # Process exported data
    └── plugins/
        └── export_to_elasticsearch.py           # Elasticsearch export plugin
```

## Core Capabilities

### **Real-Time Data Collection**
- **CosmicWatch Desktop Muon Detector v3X:** Stream real-time detection events from hardware detectors
- **CREDO.science API:** Import historical and real-time data from the CREDO.science platform
- **Multiple Data Sources:** Combine data from different sources in a unified Elasticsearch index

### **Data Storage and Indexing**
- **Elasticsearch:** Centralized data storage with full-text search capabilities
- **Index Pattern:** `credo-detections` for all cosmic ray detection data
- **Source Tagging:** Data tagged by source (`cosmicwatch-v3x`, `legacy`, etc.)
- **Time-series Data:** Optimized for time-based queries and visualizations

### **Data Visualization**
- **Kibana Dashboard:** Interactive visualization and analysis
- **Public Access:** Accessible at https://credo-kibana.nrp-nautilus.io
- **Real-Time Updates:** Auto-refresh for live data monitoring
- **Geo-Visualization:** Geographic mapping of detection events
- **Custom Dashboards:** Create custom visualizations for analysis

### **CosmicWatch Data Fields**
- Event number, device ID, detector name
- ADC values, SiPM voltage
- Coincidence detection flags
- Temperature, pressure
- Accelerometer and gyroscope data
- Timestamps for time-series analysis

## Data Access

### **Kibana Dashboard**
Access the public Kibana dashboard at: https://credo-kibana.nrp-nautilus.io

**Login Credentials:**
- Username: `elastic`
- Password: (retrieve from Kubernetes secret)

**Viewing CosmicWatch Data:**
1. Navigate to Discover
2. Select index pattern: `credo-detections*`
3. Add filter: `source: cosmicwatch-v3x`
4. Enable auto-refresh for real-time updates

**Viewing CREDO.science Data:**
1. Navigate to Discover
2. Select index pattern: `credo-detections*`
3. Expand time range to 2017-2018
4. Add filter: `source: legacy`

### **Elasticsearch API**
Query Elasticsearch directly via API:

```bash
# Count CosmicWatch documents
curl -k -u "elastic:password" \
  https://localhost:9200/credo-detections/_count \
  -H "Content-Type: application/json" \
  -d '{"query": {"term": {"source": "cosmicwatch-v3x"}}}'

# Get latest detections
curl -k -u "elastic:password" \
  https://localhost:9200/credo-detections/_search \
  -H "Content-Type: application/json" \
  -d '{
    "query": {"term": {"source": "cosmicwatch-v3x"}},
    "sort": [{"timestamp": {"order": "desc"}}],
    "size": 10
  }'
```

## Technical Architecture

### **Infrastructure**
- **Kubernetes Cluster:** NRP Nautilus
- **Namespace:** `cblee-credo`
- **Elasticsearch:** Centralized data storage and indexing
- **Kibana:** Visualization and dashboard platform
- **Ingress:** HAProxy Ingress Controller for public access
- **TLS:** cert-manager for automatic certificate management

### **Data Flow**
1. **CosmicWatch Detectors** → Serial connection → `import_data_to_elasticsearch.py` → Elasticsearch
2. **CREDO.science API** → `credo-data-exporter.py` → JSON files → `credo-data-processor.py` → Elasticsearch
3. **Elasticsearch** → Kibana → Public dashboard (https://credo-kibana.nrp-nautilus.io)

### **Deployment Components**
- **Elasticsearch Service:** `credo-elasticsearch-service` (port 9200)
- **Kibana Service:** `credo-kibana-kb-http` (port 5601)
- **Data Streaming CronJob:** Scheduled data import from CREDO.science API
- **Public Ingress:** Exposes Kibana at `credo-kibana.nrp-nautilus.io`

## Documentation

- **[CosmicWatch Data Import](CosmicWatch-Desktop-Muon-Detector-v3X/Data/README.txt)** - Detailed guide for importing CosmicWatch detector data
- **[Deployment Scripts](deploy/)** - Kubernetes deployment configurations and helper scripts
- **[Kibana Configuration](kibana-public-ingress.yaml)** - Public access configuration for Kibana
- **[Certificate Management](kibana-certificate.yaml)** - TLS certificate configuration

## 🎪 SC25 Conference

This project is being demonstrated at the Supercomputing Conference 2025 (SC25) Network Research Exhibit, showcasing real-time cosmic ray detection data collection and visualization.

### **Demo Components**
- Real-time CosmicWatch Desktop Muon Detector v3X data streaming
- CREDO.science API data integration
- Public Kibana dashboard for real-time monitoring
- Elasticsearch data storage and indexing
- Multi-source data aggregation and visualization

## Contributing

This project is part of the CREDO (Cosmic-Ray Extremely Distributed Observatory) initiative. For questions about:
- **CosmicWatch Detectors:** See [CosmicWatch-Desktop-Muon-Detector-v3X](https://github.com/carlynlee/CosmicWatch-Desktop-Muon-Detector-v3X)
- **CREDO.science:** Visit [credo.science](https://credo.science)
- **Deployment:** See deployment scripts in the `deploy/` directory

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Project Status:** Active - SC25 demonstration  
**Last Updated:** December 2024  
**Focus:** Real-time cosmic ray detection data collection and visualization
