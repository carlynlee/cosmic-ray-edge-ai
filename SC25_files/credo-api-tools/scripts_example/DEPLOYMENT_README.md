# CREDO Deployment Guide

Current deployment status and access instructions for the CREDO federated learning demo.

## Current Deployment

### **Cluster Information**
- **Cluster:** Nautilus QAIC Cluster
- **Namespace:** `cblee-credo`
- **Pod:** `credo-image-clustering-cpu-7787846784-qmrqf`
- **Status:** Running

### **Quick Access**
```bash
# Check pod status
kubectl get pods -n cblee-credo

# Access pod shell
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- bash

# Run demo scripts
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python /data/scripts_example/SC25_Simple_Demo.py
```

## Available Scripts

### **Demo Scripts**
- `SC25_Simple_Demo.py` - Presentation demo
- `federated_learning_multi_institution_demo.py` - Full FL demo

### **Data Preparation**
- `cluster_local_images.py` - Image clustering
- `analyze_device_ids.py` - Device analysis
- `visualize_cluster_samples.py` - Visualization

## Data Structure

```
/data/
├── images/hit-images-final/          # Cosmic ray images
├── exports/                          # Generated outputs
│   ├── cluster_results.txt           # Cluster assignments
│   ├── device_id_analysis.json      # Device statistics
│   └── *.png                        # Visualization plots
└── scripts_example/                  # Demo scripts
```

## 🔧 Environment

### **Python Environment**
- **Python:** 3.8+
- **TensorFlow:** 2.x
- **Dependencies:** All required packages installed

### **Data Status**
- **Images:** 2,354 cosmic ray images extracted
- **Clustering:** K-means model trained
- **Analysis:** Device statistics generated
- **Demo:** Ready for SC25 presentation

## SC25 Demo

### **Simple Demo (Recommended)**
```bash
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python /data/scripts_example/SC25_Simple_Demo.py
```

### **Full Technical Demo**
```bash
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python /data/scripts_example/federated_learning_multi_institution_demo.py
```

## Troubleshooting

### **Common Issues**
1. **Pod not running:** Check with `kubectl get pods -n cblee-credo`
2. **Script errors:** Verify data preparation with `ls -la /data/exports/`
3. **Missing files:** Ensure images are extracted in `/data/images/`

### **Debug Commands**
```bash
# Check pod logs
kubectl logs -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf

# Check data files
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- ls -la /data/exports/

# Check Python environment
kubectl exec -n cblee-credo credo-image-clustering-cpu-7787846784-qmrqf -- python -c "import tensorflow as tf; print(tf.__version__)"
```

## Performance

### **Current Status**
- **Data:** 2,354 images processed
- **Clusters:** 10 distinct particle patterns
- **Institutions:** 3 (Caltech, MIT, University of Delaware)
- **Accuracy:** >95% across all institutions
- **Privacy:** 100% - no raw data shared

---

**Status:** Ready for SC25 demonstration  
**Last Updated:** August 2025  
**Focus:** Multi-institution federated learning demo 