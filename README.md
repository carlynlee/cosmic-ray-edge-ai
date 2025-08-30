# CREDO Federated Learning Network

A distributed cosmic ray detection network using federated learning to enable collaborative machine learning across multiple institutions without sharing raw data.

## Project Overview

**Purpose:** Propose a federated learning demonstration for cosmic ray image classification across Caltech, MIT, and University of Delaware.

**Key Innovation:** Institutions would collaborate to build a comprehensive global model while maintaining data sovereignty.

## Quick Start

### Prerequisites
- Python 3.8+
- TensorFlow 2.x
- Kubernetes cluster access (for deployment)

### Local Development
```bash
# Clone the repository
git clone https://github.com/carlynlee/credo-api-tools.git
cd credo-api-tools

# Install dependencies
pip install -r scripts_example/requirements.txt

# Run the simple demo
python scripts_example/SC25_Simple_Demo.py
```

### Kubernetes Deployment
```bash
# Access the deployed pod
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- bash

# Run the multi-institution demo
python /data/scripts_example/federated_learning_multi_institution_demo.py
```

## Project Structure

```
credo-api-tools/
├── README.md                                    # This file
├── Space_Global_Model_Experiment.md             # Space deployment experiment
├── SC25_NRE_Network_Requirements_CREDO.md      # Network requirements
├── CREDO_Network_Topology.md                   # Network architecture
├── scripts_example/                            # Demo scripts and data
│   ├── README.md                              # Script documentation
│   ├── SC25_Simple_Demo.py                    # Easy demo script
│   ├── federated_learning_multi_institution_demo.py
│   ├── cluster_local_images.py                # Data preparation
│   ├── analyze_device_ids.py                  # Device analysis
│   └── visualize_cluster_samples.py           # Visualization
├── data-exporter/                             # Data export tools
└── data-processor/                            # Data processing tools
```

## Core Capabilities

### **Multi-Institution Federated Learning**
- **Caltech:** 4 detectors, clusters 0-3 (high-energy particles)
- **MIT:** 3 detectors, clusters 4-6 (medium-energy particles)
- **University of Delaware:** 3 detectors, clusters 7-9 (low-energy particles)
- **Total:** 2,354 cosmic ray images across 10 detectors

### **Collaborative Learning**
- Model parameters exchanged via federated averaging
- Each institution maintains data sovereignty
- Global model combines knowledge from all institutions
- Collaborative scientific discovery across institutions

### **Real-Time Classification**
- ResNet50 for feature extraction
- K-means clustering for particle pattern grouping
- 10 distinct cosmic ray pattern clusters
- Real-time classification of new particles

## Space Deployment Experiment

The project includes a comprehensive space deployment experiment showing how the global model can be deployed to satellites for autonomous cosmic ray classification in space.

See [`Space_Global_Model_Experiment.md`](Space_Global_Model_Experiment.md) for detailed diagrams and specifications.

## Demo Results

### **Federated Learning Performance**
- **Round 1:** All institutions achieve >96% accuracy
- **Round 5:** Final evaluation shows collaborative improvement
- **Privacy:** Zero raw data shared between institutions
- **Scalability:** Successfully handles 3 institutions, 10 detectors

### **Classification Coverage**
- **Global Model:** Can classify all particle types (0-9)
- **Institution Specialization:** Each institution excels at local particle types
- **Combined Knowledge:** Global model has comprehensive expertise

## Technical Architecture

### **Network Requirements**
- **Bandwidth:** 10 Gbps for real-time data transmission
- **Latency:** <50ms for federated learning coordination
- **Protocols:** IPv6, Layer 2/3 switching
- **Security:** Encrypted model parameter exchange

### **Compute Requirements**
- **GPU Nodes:** H100 SXM for model training
- **CPU Nodes:** For data preprocessing and clustering
- **Storage:** NVMe for high-speed data access
- **Memory:** 32GB+ for large model training

## 📚 Documentation

- **[Network Requirements](SC25_NRE_Network_Requirements_CREDO.md)** - Detailed network specifications
- **[Network Topology](CREDO_Network_Topology.md)** - Network architecture diagrams
- **[Space Experiment](Space_Global_Model_Experiment.md)** - Space deployment experiment
- **[Scripts Documentation](scripts_example/README.md)** - Demo scripts guide

## 🎪 SC25 Conference

This project is proposed for demonstration at the Supercomputing Conference 2025 (SC25) Network Research Exhibit, showcasing distributed AI for scientific collaboration.

### **Proposed Demo Components**
- Multi-institution federated learning
- Real cosmic ray data processing
- Collaborative model sharing
- Space deployment experiment

## 🤝 Contributing

This project demonstrates federated learning for scientific collaboration. For questions about the implementation or deployment, please refer to the documentation in the `scripts_example/` directory.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Project Status:** Proposed for SC25 demonstration  
**Last Updated:** August 2025  
**Focus:** Multi-institution federated learning for cosmic ray detection
