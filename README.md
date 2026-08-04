# CREDO API Tools

Tools for collecting, processing, and visualizing cosmic ray detection data from CREDO.science and CosmicWatch Desktop Muon Detector v3X.

## Project Overview

**Purpose:** Collect, analyze, and classify cosmic ray detection data using AI/ML, with real-time data streaming from CREDO.science API and CosmicWatch Desktop Muon Detector v3X devices. This project demonstrates federated learning for cosmic ray event classification in preparation for SC25 and space-based deployment.

**Key Features:**
- Real-time data streaming from CosmicWatch detectors
- CREDO.science API data import
- Elasticsearch data storage and indexing
- Kibana visualization dashboard with Machine Learning capabilities
- Public access to Kibana dashboard for real-time monitoring
- **Machine Learning:** Baseline models for cosmic ray event classification
- **Data Analysis:** Analysis and data partitioning for federated learning
- **Federated Learning:** Distributed model training across multiple data nodes (complete)
- **RINO Integration:** Transformer-based self-supervised learning based on Zichun's recommendations (NEW)
  - **CREDO Images:** DINO-v2/v3 vision transformers (see `credo/` module)
  - **CosmicWatch Events:** BERT/GPT-style transformers (see `cosmicwatch/` module)
  - **Multi-Modal Fusion:** Unified embedding space (see `multimodal/` module)

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

# For machine learning and analysis
pip install torch pandas numpy scikit-learn matplotlib

# For transformers (BERT/GPT for events, DINO for images)
pip install transformers torchvision Pillow

# Or install from requirements
pip install -r requirements.txt
pip install -r scripts/requirements.txt  # Includes transformers and vision libraries
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
├── RINO_INTEGRATION.md                          # RINO integration guide (NEW)
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
├── cosmicwatch/                                 # CosmicWatch module (BERT/GPT for events)
│   ├── __init__.py                              # Module exports
│   ├── README.md                                # Module documentation
│   ├── dataloader/                              # Data loading
│   │   ├── dataset.py                           # Sequence dataset
│   │   └── loader.py                            # Load from JSON/Elasticsearch
│   ├── preprocess/                              # Preprocessing
│   │   └── sequences.py                         # Event sequence creation
│   ├── utils/                                   # Utilities
│   │   └── conversion.py                        # Format conversion
│   └── examples/                                # Example scripts
│       └── example_rino_integration.py          # Integration examples
├── credo/                                       # CREDO image module (DINO-v2/v3) (NEW)
│   ├── __init__.py                              # Module exports
│   ├── README.md                                # Module documentation
│   ├── dataloader/                              # Data loading
│   │   ├── dataset.py                           # Image dataset
│   │   └── loader.py                            # Load from JSON/Elasticsearch
│   ├── models/                                  # Models
│   │   └── dino.py                              # DINOImageEncoder
│   └── examples/                                # Example scripts
│       └── example_dino_usage.py               # DINO usage examples
├── multimodal/                                  # Multi-modal fusion (NEW)
│   ├── __init__.py                              # Module exports
│   ├── README.md                                # Module documentation
│   ├── fusion.py                                # MultiModalFusion class
│   └── examples/                                # Example scripts
│       └── example_multimodal.py                # Multi-modal examples
├── RINO/                                        # RINO repository (cloned)
│   └── ...                                      # RINO codebase
├── data-exporter/                               # CREDO.science API export tools
│   └── credo-data-exporter.py                   # Export data from CREDO.science API
└── data-processor/                              # Data processing and indexing
    ├── credo-data-processor.py                  # Process exported data
    └── plugins/
        └── export_to_elasticsearch.py           # Elasticsearch export plugin
├── scripts/                                      # Data analysis and ML scripts
    ├── export_cosmicwatch_data.py               # Export data from Elasticsearch
    ├── analyze_and_partition_data.py            # Analyze and partition data for FL
    ├── analysis.py                              # Scientific data analysis
    ├── train_binary_baseline.py                 # Train baseline ML model
    ├── train_baseline_model.py                 # Train multi-class model (legacy)
    ├── evaluate_and_tune_threshold.py          # Model evaluation and tuning
    ├── models/                                  # Trained model checkpoints
    └── data/                                    # Data exports and partitions
└── docs/                                        # Project documentation
    ├── SC25_8_DAY_REALISTIC_PLAN.md            # SC25 demonstration plan
    ├── BASELINE_MODEL_DESIGN.md                # ML model design document
    ├── FEDERATED_LEARNING_ROADMAP.md           # Federated learning strategy
    ├── day1-2_checklist.md                     # Day 1-2 completion summary
    └── DAY3-4_SUMMARY.md                       # Day 3-4 completion summary
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
- **Machine Learning:** Kibana ML features for anomaly detection and classification

### **Data Analysis and Machine Learning**
- **Scientific Analysis:** Energy spectrum, coincidence rate, environmental correlations, temporal patterns
- **Data Partitioning:** Partition data for federated learning (coincidence vs non-coincidence events)
- **Baseline Models:** Binary classification models for coincidence event prediction
- **Model Evaluation:** Performance metrics, threshold tuning, physics validation
- **Federated Learning:** Distributed model training across multiple data nodes (complete)
- **RINO Integration:** Transformer-based self-supervised learning based on Zichun's recommendations (NEW)
  - **CREDO Images:** DINO-v2/v3 vision transformers for cosmic ray images
  - **CosmicWatch Events:** BERT/GPT-style transformers for sequential event data
  - **Multi-Modal Fusion:** Unified embedding space combining images and events
  - See `docs/ZICHUN_RECOMMENDATIONS.md`, `credo/README.md`, `cosmicwatch/README.md`, and `multimodal/README.md` for details

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
4. **Data Analysis:** Elasticsearch → `export_cosmicwatch_data.py` → `analyze_and_partition_data.py` → Training datasets
5. **Model Training:** Training datasets → `train_binary_baseline.py` → Trained models
6. **Federated Learning:** Multiple nodes → FL server → Aggregated model (complete)

### **Deployment Components**
- **Elasticsearch Service:** `credo-elasticsearch-service` (port 9200)
- **Kibana Service:** `credo-kibana-kb-http` (port 5601)
- **Data Streaming CronJob:** Scheduled data import from CREDO.science API
- **Public Ingress:** Exposes Kibana at `credo-kibana.nrp-nautilus.io`

## Documentation

### **Setup and Deployment**
- **[CosmicWatch Data Import](CosmicWatch-Desktop-Muon-Detector-v3X/Data/README.txt)** - Detailed guide for importing CosmicWatch detector data
- **[Deployment Scripts](deploy/)** - Kubernetes deployment configurations and helper scripts
- **[Kibana Configuration](kibana-public-ingress.yaml)** - Public access configuration for Kibana
- **[Certificate Management](kibana-certificate.yaml)** - TLS certificate configuration

### **Machine Learning and Analysis**
- **[SC25 8-Day Plan](docs/SC25_8_DAY_REALISTIC_PLAN.md)** - Complete demonstration plan for SC25
- **[Baseline Model Design](docs/BASELINE_MODEL_DESIGN.md)** - ML model architecture and training strategy
- **[Federated Learning Roadmap](docs/FEDERATED_LEARNING_ROADMAP.md)** - FL implementation strategy
- **[Day 1-2 Checklist](docs/day1-2_checklist.md)** - Data collection and analysis completion
- **[Day 3-4 Summary](docs/DAY3-4_SUMMARY.md)** - Baseline model development summary
- **[Scripts README](scripts/README.md)** - Scripts directory documentation

### **RINO Integration (NEW)**
- **[Zichun's Recommendations](docs/ZICHUN_RECOMMENDATIONS.md)** - Summary of recommendations from RINO author
- **[Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md)** - Complete implementation roadmap
- **[RINO Integration Guide](RINO_INTEGRATION.md)** - Complete guide for integrating with RINO-style frameworks
- **[CREDO Module](credo/README.md)** - DINO-v2/v3 for CREDO images
- **[CosmicWatch Module](cosmicwatch/README.md)** - BERT/GPT for event sequences
- **[Multi-Modal Module](multimodal/README.md)** - Fusion of images and events
- **[Example Scripts](credo/examples/)** - CREDO image processing examples
- **[Example Scripts](cosmicwatch/examples/)** - CosmicWatch event processing examples
- **[Example Scripts](multimodal/examples/)** - Multi-modal fusion examples

## 🎪 SC25 Conference

This project is being demonstrated at the Supercomputing Conference 2025 (SC25) Network Research Exhibit, showcasing real-time cosmic ray detection data collection and visualization.

### **Demo Components**
- Real-time CosmicWatch Desktop Muon Detector v3X data streaming
- CREDO.science API data integration
- Public Kibana dashboard for real-time monitoring
- Elasticsearch data storage and indexing
- Multi-source data aggregation and visualization
- **Machine Learning:** Baseline models for cosmic ray event classification
- **Federated Learning:** Distributed model training demonstration (complete)
- **Scientific Analysis:** Energy spectrum, coincidence detection, environmental correlations

## Contributing

This project is part of the CREDO (Cosmic-Ray Extremely Distributed Observatory) initiative. For questions about:
- **CosmicWatch Detectors:** See [CosmicWatch-Desktop-Muon-Detector-v3X](https://github.com/carlynlee/CosmicWatch-Desktop-Muon-Detector-v3X)
- **CREDO.science:** Visit [credo.science](https://credo.science)
- **Deployment:** See deployment scripts in the `deploy/` directory

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Project Status:** Active - SC25 demonstration (Day 6 of 8 complete)  
**Last Updated:** November 2024  
**Focus:** Real-time cosmic ray detection data collection, AI/ML classification, and federated learning

**Current Progress:**
- ✅ Day 1-2: Data collection, analysis, and partitioning (COMPLETE)
- ✅ Day 3-4: Baseline model development (COMPLETE)
- ✅ Day 5-6: Federated learning implementation (COMPLETE)
- 📋 Day 7-8: Integration and visualization (PLANNED)
