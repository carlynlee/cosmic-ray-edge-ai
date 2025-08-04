# CREDO Cosmic Ray Detection Network

A comprehensive toolkit for distributed cosmic ray detection and privacy-preserving federated learning across multiple institutions. This project demonstrates how institutions can collaborate on machine learning without sharing sensitive data.

## 🌌 What This Project Does

### **Core Capabilities:**

1. **Cosmic Ray Image Processing**
   - Processes 2,354 real cosmic ray detection images
   - Uses ResNet50 for feature extraction and K-means clustering
   - Identifies 10 distinct cosmic ray patterns

2. **Multi-Institution Federated Learning**
   - **Caltech**: 4 detectors, 951 images (clusters 0-3)
   - **MIT**: 3 detectors, 746 images (clusters 4-6)
   - **University of Delaware**: 3 detectors, 657 images (clusters 7-9)
   - **Total**: 2,354 images across 10 cosmic ray detectors

3. **Privacy-Preserving Collaboration**
   - No raw data shared between institutions
   - Only model parameters exchanged
   - Federated averaging combines knowledge globally
   - Each institution maintains data sovereignty

4. **Real-Time Demonstration**
   - Live Python script demos (no Jupyter required)
   - Interactive federated learning rounds
   - Real-time visualization of training progress
   - Performance metrics per institution

## 🚀 Quick Start

### **Option 1: Simple Demo (Recommended for Presentations)**

```bash
# Run the simple demo script
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python SC25_Simple_Demo.py
```

### **Option 2: Full Multi-Institution Demo**

```bash
# Run the complete federated learning demo
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python federated_learning_multi_institution_demo.py
```

### **Option 3: Data Preparation**

```bash
# Analyze device IDs and data distribution
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python analyze_device_ids.py

# Cluster cosmic ray images
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python cluster_local_images.py
```

## 📊 Current Status

### **✅ Completed:**
- ✅ Data preparation and clustering (2,354 images processed)
- ✅ Multi-institution federated learning demo
- ✅ Kubernetes deployment on Nautilus cluster
- ✅ Device ID analysis and mapping
- ✅ Cluster visualization and statistics

### **✅ Demo Results:**
- **Round 1:** All institutions achieve >96% accuracy
- **Round 5:** Final evaluation shows collaborative improvement
- **Privacy:** Zero raw data shared between institutions
- **Scalability:** Successfully handles 3 institutions, 10 detectors

## 🏗️ Architecture

### **Data Pipeline:**
```
Cosmic Ray Detectors → Image Collection → Feature Extraction → Clustering → Federated Learning → Global Model
```

### **Network Requirements:**
- **Bandwidth:** 10 Gbps for real-time data transmission
- **Latency:** <50ms for federated learning coordination
- **Protocols:** IPv6, Layer 2/3 switching
- **Security:** Encrypted model parameter exchange

### **Compute Requirements:**
- **GPU Nodes:** H100 SXM for model training
- **CPU Nodes:** For data preprocessing and clustering
- **Storage:** NVMe for high-speed data access
- **Memory:** 32GB+ for large model training

## 📁 Project Structure

```
credo-api-tools/
├── scripts_example/                    # Main demo scripts
│   ├── SC25_Simple_Demo.py                    # Simple presentation demo
│   ├── federated_learning_multi_institution_demo.py  # Full FL demo
│   ├── federated_learning_demo.py              # Basic FL demo
│   ├── cluster_local_images.py                 # Image clustering
│   ├── analyze_device_ids.py                   # Device analysis
│   ├── visualize_cluster_samples.py            # Cluster visualization
│   ├── plot_device_cluster_statistics.py       # Statistics plotting
│   ├── visualize_cluster_mean_images.py        # Mean image visualization
│   ├── hit-images-final.zip                    # Cosmic ray image dataset
│   ├── kmeans_model.pkl                        # Trained clustering model
│   └── results/                                # Generated outputs
├── data-exporter/                       # Data export tools
├── data-processor/                      # Data processing pipeline
├── SC25_Presentation_Script.md          # GNA-G meeting script
├── SC25_NRE_Network_Requirements_CREDO.md  # SC25 network requirements
├── CREDO_Network_Topology.md            # Network architecture
├── CREDO_Deployment_Architecture.md     # Deployment details
├── CREDO_Data_Flow.md                   # Data flow diagram
└── README.md                            # This file
```

## 🎯 Use Cases

### **1. SC25 Conference Demo**
- **Script:** `SC25_Simple_Demo.py`
- **Purpose:** Present the project to GNA-G DIS-WG
- **Features:** Overview, institution setup, simulated FL rounds, network requirements

### **2. Technical Federated Learning Demo**
- **Script:** `federated_learning_multi_institution_demo.py`
- **Purpose:** Show real federated learning with actual data
- **Features:** Real model training, institution-specific data, privacy preservation

### **3. Data Analysis and Visualization**
- **Scripts:** `analyze_device_ids.py`, `cluster_local_images.py`
- **Purpose:** Understand data distribution and clustering
- **Features:** Device analysis, image clustering, visualizations

### **4. Research and Development**
- **Scripts:** Various visualization and analysis scripts
- **Purpose:** Deep dive into cosmic ray patterns and federated learning
- **Features:** Detailed analysis, custom visualizations, model inspection

## 🔧 Deployment

### **Current Deployment:**
- **Cluster:** Nautilus QAIC Cluster
- **Namespace:** `cblee-credo`
- **Pod:** `credo-image-clustering-cpu-7787846784-qmrqf`
- **Status:** ✅ Running

### **Access:**
```bash
# Check pod status
kubectl get pods -n cblee-credo

# Port forward for Jupyter (if needed)
kubectl port-forward -n cblee-credo deployment/credo-image-clustering-cpu 8888:8888

# Execute scripts directly
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python <script_name>.py
```

## 📈 Results and Outputs

### **Generated Files:**
```
/data/exports/
├── cluster_results.txt                    # Cluster assignments
├── cluster_visualization.png             # PCA visualization
├── device_id_analysis.json               # Device distribution
├── device_image_mapping.csv              # Device-image mapping
├── federated_learning_results.json       # FL training results
├── federated_learning_visualization.png  # FL training plots
├── multi_institution_fl_results.json     # Multi-institution results
└── multi_institution_fl_visualization.png # Multi-institution plots
```

### **Key Metrics:**
- **Total Images:** 2,354 cosmic ray detections
- **Institutions:** 3 (Caltech, MIT, University of Delaware)
- **Detectors:** 10 cosmic ray detectors
- **Clusters:** 10 distinct cosmic ray patterns
- **Privacy:** 100% - no raw data shared
- **Accuracy:** >95% across all institutions

## 🎪 SC25 Conference Preparation

### **Network Requirements:**
- **Bandwidth:** 10 Gbps dedicated connection
- **Latency:** <50ms for federated learning coordination
- **Protocols:** IPv6, Layer 2/3 switching
- **Security:** Encrypted model parameter transmission

### **Compute Requirements:**
- **GPU Nodes:** H100 SXM for model training
- **CPU Nodes:** For data preprocessing
- **Storage:** NVMe for high-speed access
- **Memory:** 32GB+ for large model training

### **Demo Scripts:**
1. **Simple Demo:** `SC25_Simple_Demo.py` - Perfect for presentations
2. **Full Demo:** `federated_learning_multi_institution_demo.py` - Technical demonstration
3. **Documentation:** `SC25_Presentation_Script.md` - Meeting preparation

## 🔍 Troubleshooting

### **Common Issues:**

1. **Pod Not Running:**
   ```bash
   kubectl get pods -n cblee-credo
   kubectl describe pod -n cblee-credo <pod-name>
   ```

2. **Script Execution Errors:**
   ```bash
   # Check if data is prepared
   kubectl exec -n cblee-credo <pod-name> -- ls -la /data/exports/
   ```

3. **Missing Dependencies:**
   ```bash
   # Install in pod
   kubectl exec -n cblee-credo <pod-name> -- pip install <package>
   ```

### **Debugging Commands:**
```bash
# Check pod logs
kubectl logs -n cblee-credo <pod-name>

# Access pod shell
kubectl exec -it -n cblee-credo <pod-name> -- /bin/bash

# Check data files
kubectl exec -n cblee-credo <pod-name> -- ls -la /data/
```

## 📚 Documentation

### **Technical Documentation:**
- **Network Topology:** [`CREDO_Network_Topology.md`](CREDO_Network_Topology.md)
- **Deployment Architecture:** [`CREDO_Deployment_Architecture.md`](CREDO_Deployment_Architecture.md)
- **Data Flow:** [`CREDO_Data_Flow.md`](CREDO_Data_Flow.md)
- **SC25 Requirements:** [`SC25_NRE_Network_Requirements_CREDO.md`](SC25_NRE_Network_Requirements_CREDO.md)

### **Demo Scripts:**
- **Presentation Script:** [`SC25_Presentation_Script.md`](SC25_Presentation_Script.md)
- **Code Flow:** [`Federated_Learning_Code_Flow.md`](Federated_Learning_Code_Flow.md)
- **Demo Explanation:** [`Federated_Learning_Demo_Explanation.md`](Federated_Learning_Demo_Explanation.md)

## 🤝 Collaborators

- **University of Delaware** - Cosmic Watch Muon Detectors
- **MIT** - Cosmic Watch Muon Detectors
- **Caltech** - Project coordination and deployment

## 📄 License

See [LICENSE](LICENSE) file for details.

## 🔗 Related Links

- **Project Repository:** https://github.com/carlynlee/credo-api-tools/tree/sc25-nre-submission
- **CREDO Project:** https://credo.science/
- **Cosmic Watch:** http://cosmicwatch.lns.mit.edu/detector
- **Nautilus Cluster:** https://nrp.ai/documentation/userdocs/ai/qaic/

---

**Last Updated:** August 3, 2025  
**Status:** ✅ Active deployment with multi-institution federated learning  
**SC25 Ready:** ✅ All demos tested and working  
**Contact:** For issues, create an issue in this repository
