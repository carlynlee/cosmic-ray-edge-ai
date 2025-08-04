# CREDO Scripts - Quick Reference

This directory contains the main demonstration and analysis scripts for the CREDO Cosmic Ray Detection Network.

## 🚀 Quick Start Scripts

### **SC25_Simple_Demo.py** - **RECOMMENDED for Presentations**
```bash
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python SC25_Simple_Demo.py
```
- **Purpose:** Simple demo for meetings and presentations
- **Features:** Overview, institution setup, simulated FL rounds, network requirements
- **Output:** Clear presentation of the project capabilities

### **federated_learning_multi_institution_demo.py** - **FULL TECHNICAL DEMO**
```bash
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python federated_learning_multi_institution_demo.py
```
- **Purpose:** Complete federated learning demonstration
- **Features:** Real model training, institution-specific data, privacy preservation
- **Output:** Actual federated learning results and visualizations

## 📊 Data Analysis Scripts

### **analyze_device_ids.py**
```bash
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python analyze_device_ids.py
```
- **Purpose:** Analyze device ID distribution from image filenames
- **Output:** Device statistics, mappings, and federated learning configuration

### **cluster_local_images.py**
```bash
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python cluster_local_images.py
```
- **Purpose:** Cluster cosmic ray images using ResNet50 + K-means
- **Output:** Cluster assignments, visualizations, and K-means model

## 🎨 Visualization Scripts

### **visualize_cluster_samples.py**
```bash
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python visualize_cluster_samples.py
```
- **Purpose:** Visualize sample images from each cluster
- **Output:** Grid of sample images per cluster

### **visualize_cluster_mean_images.py**
```bash
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python visualize_cluster_mean_images.py
```
- **Purpose:** Compute and display mean images for each cluster
- **Output:** Average cosmic ray patterns per cluster

### **plot_device_cluster_statistics.py**
```bash
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python plot_device_cluster_statistics.py
```
- **Purpose:** Plot device distribution across clusters
- **Output:** Statistical visualizations of device-cluster relationships

## 🔧 Alternative Demo Scripts

### **federated_learning_demo.py**
```bash
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python federated_learning_demo.py
```
- **Purpose:** Basic federated learning demonstration
- **Features:** Simple cluster-based federated learning
- **Output:** Basic FL results and visualizations

## 📁 Data Files

- **hit-images-final.zip** - Cosmic ray image dataset (2,354 images)
- **kmeans_model.pkl** - Trained K-means clustering model
- **results/** - Generated outputs and visualizations

## 🎯 Use Cases

### **For SC25 Conference:**
1. **Simple Demo:** `SC25_Simple_Demo.py` - Perfect for booth presentations
2. **Technical Demo:** `federated_learning_multi_institution_demo.py` - For technical discussions

### **For Data Analysis:**
1. **Device Analysis:** `analyze_device_ids.py` - Understand data distribution
2. **Image Clustering:** `cluster_local_images.py` - Group similar images
3. **Visualization:** Various visualization scripts for insights

### **For Research:**
1. **Deep Analysis:** All scripts for comprehensive research
2. **Custom Analysis:** Modify scripts for specific research needs

## 📊 Expected Outputs

All scripts generate outputs in `/data/exports/`:
- **cluster_results.txt** - Cluster assignments
- **cluster_visualization.png** - PCA visualization
- **device_id_analysis.json** - Device statistics
- **federated_learning_results.json** - FL training results
- **multi_institution_fl_results.json** - Multi-institution results

## 🔍 Troubleshooting

### **Common Issues:**
1. **Data not prepared:** Run `cluster_local_images.py` first
2. **Images not found:** Ensure `hit-images-final.zip` is extracted
3. **Dependencies missing:** All required packages are in the container

### **Debug Commands:**
```bash
# Check if data is ready
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- ls -la /data/exports/

# Check if images are available
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- ls -la /data/images/
```

---

**Last Updated:** August 3, 2025  
**Status:** ✅ All scripts tested and working  
**SC25 Ready:** ✅ Demos prepared for conference
