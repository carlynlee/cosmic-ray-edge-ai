# CREDO Demo Scripts

This directory contains the core demonstration scripts for the CREDO federated learning network.

## Quick Demo

### **Simple Demo (Recommended for Presentations)**
```bash
python SC25_Simple_Demo.py
```
- High-level overview of the project
- Simulated federated learning rounds
- Network requirements summary
- Perfect for meetings and presentations

### **Full Multi-Institution Demo**
```bash
python federated_learning_multi_institution_demo.py
```
- Real federated learning with actual data
- Institution-specific training and evaluation
- Privacy-preserving model sharing
- Comprehensive results and visualizations

## Data Preparation Scripts

### **Device Analysis**
```bash
python analyze_device_ids.py
```
- Analyzes cosmic ray detector distribution
- Maps device IDs to image files
- Generates device statistics

### **Image Clustering**
```bash
python cluster_local_images.py
```
- Clusters cosmic ray images using ResNet50 + K-means
- Creates 10 distinct particle pattern clusters
- Saves cluster assignments and model

### **Visualization**
```bash
python visualize_cluster_samples.py
```
- Visualizes cluster samples and statistics
- Shows particle pattern distributions
- Creates cluster analysis plots

## Script Descriptions

| Script | Purpose | Output |
|--------|---------|--------|
| `SC25_Simple_Demo.py` | Presentation demo | Overview and simulation |
| `federated_learning_multi_institution_demo.py` | Full FL demo | Training results and plots |
| `cluster_local_images.py` | Data preparation | Cluster assignments |
| `analyze_device_ids.py` | Device analysis | Device statistics |
| `visualize_cluster_samples.py` | Visualization | Cluster plots |

## Demo Results

### **Federated Learning Performance**
- **3 Institutions:** Caltech, MIT, University of Delaware
- **2,354 Images:** Cosmic ray detections
- **10 Clusters:** Distinct particle patterns
- **Privacy:** Zero raw data shared
- **Accuracy:** >95% across all institutions

### **Institution Specialization**
- **Caltech:** Clusters 0-3 (high-energy particles)
- **MIT:** Clusters 4-6 (medium-energy particles)
- **University of Delaware:** Clusters 7-9 (low-energy particles)

## 🔧 Deployment

### **Kubernetes Access**
```bash
# Access the deployed pod
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- bash

# Run scripts in the pod
python /data/scripts_example/SC25_Simple_Demo.py
```

### **Local Development**
```bash
# Install dependencies
pip install -r requirements.txt

# Run scripts locally
python SC25_Simple_Demo.py
```

## Output Files

Scripts generate results in `/data/exports/`:
- `cluster_results.txt` - Image to cluster mappings
- `device_id_analysis.json` - Device statistics
- `multi_institution_fl_results.json` - FL training results
- `*.png` - Visualization plots

## SC25 Conference

These scripts are optimized for the SC25 Network Research Exhibit demonstration, showcasing:
- **Privacy-preserving federated learning**
- **Multi-institution collaboration**
- **Real cosmic ray data processing**
- **Space deployment applications**

---

**Status:** Ready for SC25 demonstration  
**Focus:** Multi-institution federated learning demo
