# SC25 NRE Network Requirements: CREDO Cosmic Ray Detection Experiment

**Project**: Distributed Cosmic Ray Detection Network with Federated Learning  
**Principal Investigator**: Carlyn Lee (Caltech)  
**Institution**: California Institute of Technology  
**Collaborators**: University of Delaware, MIT (Cosmic Watch Muon Detectors)  
**NRE Title**: "Real-Time Cosmic Ray Detection and Analysis Using Distributed Sensor Networks"  
**Submission Date**: August 1, 2025  

## Summary

This NRE demonstrates a distributed cosmic ray detection network using federated learning to process real-time data from multiple sensor nodes. The experiment showcases how distributed computing can enable collaborative scientific discovery while preserving data privacy through federated learning techniques.

## Use Case Description

### Scientific Objective
Our experiment demonstrates real-time cosmic ray detection and analysis using a distributed network of sensors. The system processes cosmic ray detection events from multiple geographically distributed nodes, applies machine learning for pattern recognition, and uses federated learning to collaboratively train models without sharing raw data.

### SCinet Cluster Integration
The SCinet Compute Cluster will serve as our central processing hub, enabling:
- **Real-time data aggregation** from distributed cosmic ray detectors
- **Federated learning coordination** across multiple sensor nodes
- **High-performance model training** using GPU acceleration
- **Distributed storage and analysis** of cosmic ray event data

### Success Metrics
- Process 10,000+ cosmic ray detection events per hour
- Train federated models across 8+ distributed nodes
- Achieve sub-100ms latency for real-time event processing
- Demonstrate 95%+ accuracy in cosmic ray classification

## Architecture Overview

### Network Topology
```
[Distributed Sensors] ←→ [SCinet Edge] ←→ [SCinet Core] ←→ [Compute Cluster]
     (8+ locations)         (100Gbps)        (400Gbps)        (GPU Nodes)
```

### Component Distribution
- **A Location**: SCinet Compute Cluster (St. Louis Convention Center)
- **Z Locations**: 8+ distributed sensor nodes (Caltech, MIT, University of Delaware, partner institutions)
- **Edge Processing**: Local preprocessing at each sensor node
- **Central Coordination**: Federated learning server on SCinet cluster

## Network Requirements

### Physical Connections

#### Primary Circuit (SCinet Managed)
- **A Location**: SCinet Compute Cluster, St. Louis Convention Center
- **Z Location**: Caltech Network Operations Center
- **Connection Type**: 100Gbps Ethernet (QSFP28)
- **Protocol**: Layer 3 (IPv6)
- **Bandwidth**: 100 Gbps dedicated
- **Purpose**: Primary data pipeline and federated learning coordination

#### Secondary Circuits (Self-Managed)
- **Sensor Node 1**: Caltech Cosmic Ray Lab
  - Connection: 10Gbps Ethernet
  - Protocol: Layer 3 (IPv6)
  - Bandwidth: 10 Gbps
  - Purpose: Real-time cosmic ray data transmission

- **Sensor Node 2**: MIT/University of Delaware Space Science Lab
  - Connection: 10Gbps Ethernet
  - Protocol: Layer 3 (IPv6)
  - Bandwidth: 10 Gbps
  - Purpose: Space weather correlation data

- **Sensor Node 3-8**: Partner Institutions
  - Connection: 1-10Gbps Ethernet (varies by institution)
  - Protocol: Layer 3 (IPv6)
  - Bandwidth: 1-10 Gbps each
  - Purpose: Distributed cosmic ray detection

### Bandwidth Requirements

#### Total Bandwidth Analysis
- **Primary Circuit**: 100 Gbps (SCinet managed)
- **Secondary Circuits**: 60 Gbps total (self-managed)
- **Peak Bandwidth**: 160 Gbps during federated learning rounds
- **Sustained Bandwidth**: 50 Gbps for continuous data streaming

#### Traffic Patterns
- **Real-time Data**: 10-20 Gbps sustained (cosmic ray events)
- **Model Updates**: 40-80 Gbps burst during federated learning
- **Control Traffic**: 1-2 Gbps (coordination and metadata)
- **Storage Transfers**: 20-40 Gbps (periodic data synchronization)

### Protocol Requirements

#### Layer 2/3 Specifications
- **Primary**: Layer 3 (IPv6) with QoS marking
- **Secondary**: Layer 3 (IPv6) with best-effort delivery
- **VLAN**: Separate VLAN for federated learning traffic
- **QoS**: Priority queuing for real-time cosmic ray data

#### Application Protocols
- **Federated Learning**: Custom protocol over TCP/8888
- **Data Streaming**: WebSocket over TLS/443
- **Model Transfer**: HTTP/2 over TLS/443
- **Monitoring**: Prometheus metrics over HTTP/9090

## Compute Cluster Requirements

### Ecosystem/Methodology
- **Container Orchestration**: Kubernetes (K8s)
- **Job Scheduling**: SLURM for batch processing
- **Federated Learning**: Flower (flwr) framework
- **Machine Learning**: TensorFlow/PyTorch with GPU acceleration

### Node Requirements

#### Dedicated Node Access
- **Primary**: 2x GPU Nodes (H100 SXM) for model training
- **Secondary**: 4x CPU Nodes for data preprocessing
- **Storage**: 1TB NVMe per node for high-speed I/O

#### Compute Specifications
- **GPU Nodes**: 2x H100 SXM (8x GPUs total)
- **CPU Nodes**: 4x 32-core nodes (128 cores total)
- **Memory**: 1.5TB per GPU node, 256GB per CPU node
- **Storage**: 150TB NVMe shared storage

### Bandwidth Requirements
- **Inter-node Communication**: 400 Gbps (ConnectX-7)
- **Storage I/O**: 100 Gbps sustained
- **Federated Learning**: 200 Gbps during model aggregation
- **Data Pipeline**: 50 Gbps for real-time processing

### Storage Requirements
- **Raw Data**: 50TB for cosmic ray event storage
- **Processed Data**: 25TB for feature vectors and metadata
- **Model Storage**: 5TB for federated learning models
- **Temporary Storage**: 20TB for intermediate processing
- **Total**: 100TB NVMe storage

## Technical Implementation

### Network Configuration

#### SCinet Circuit Configuration
```yaml
Circuit: CREDO-Primary-100G
A-Location: SCinet Compute Cluster
Z-Location: Caltech NOC
Bandwidth: 100 Gbps
Interface: QSFP28 (100Gbps Ethernet)
Protocol: IPv6 with QoS
VLAN: 1001 (Federated Learning)
```

#### QoS Configuration
- **Priority 1**: Real-time cosmic ray events (latency < 10ms)
- **Priority 2**: Federated learning model updates (latency < 100ms)
- **Priority 3**: Data synchronization (latency < 1s)
- **Priority 4**: Monitoring and control traffic (best effort)

### Security Requirements
- **Encryption**: TLS 1.3 for all data transmission
- **Authentication**: X.509 certificates for node authentication
- **Authorization**: Role-based access control (RBAC)
- **Network Isolation**: Separate VLAN for federated learning traffic

### Monitoring and Telemetry
- **Network Metrics**: Prometheus + Grafana
- **Application Metrics**: Custom CREDO monitoring stack
- **Performance**: Real-time latency and throughput monitoring
- **Alerts**: Automated alerting for network issues

## Performance Expectations

### Latency Requirements
- **Real-time Events**: < 10ms end-to-end latency
- **Model Updates**: < 100ms for federated learning rounds
- **Data Synchronization**: < 1s for bulk transfers
- **Control Commands**: < 50ms for coordination messages

### Throughput Requirements
- **Peak Data Rate**: 160 Gbps during federated learning
- **Sustained Data Rate**: 50 Gbps for continuous operation
- **Burst Capacity**: 200 Gbps for model aggregation
- **Storage I/O**: 100 Gbps sustained read/write

### Reliability Requirements
- **Uptime**: 99.9% availability during conference
- **Data Loss**: < 0.01% packet loss
- **Recovery**: < 30 seconds failover time
- **Backup**: Real-time data replication

## Deployment Timeline

### Pre-Conference Setup (October 2025)
- **Week 1**: Network circuit provisioning and testing
- **Week 2**: Compute cluster deployment and configuration
- **Week 3**: Sensor node integration and testing
- **Week 4**: Federated learning system validation

### Conference Deployment (November 2025)
- **Day 1**: System deployment and initial testing
- **Day 2**: Live demonstration and performance optimization
- **Day 3**: Extended demonstration with multiple sensor nodes
- **Day 4**: Final demonstration and data collection

### Post-Conference Analysis (December 2025)
- **Data Analysis**: Process collected cosmic ray events
- **Performance Review**: Analyze network and compute performance
- **Documentation**: Publish results and lessons learned

## Additional Information

### Diagrams and Documentation
- **Network Topology Diagram**: See attached `CREDO_Network_Topology.pdf`
- **Deployment Architecture**: See attached `CREDO_Deployment_Architecture.pdf`
- **Data Flow Diagram**: See attached `CREDO_Data_Flow.pdf`

### Contact Information
- **Project Lead**: Carlyn Lee (cblee@caltech.edu)
- **Network Engineer**: [To be assigned by SCinet]

### Special Requirements
- **Power**: 8x C19 outlets for GPU nodes
- **Cooling**: Adequate cooling for 8x H100 GPUs
- **Physical Access**: 24/7 access to compute cluster
- **Network Access**: Dedicated 100Gbps circuit with guaranteed bandwidth

### Success Criteria
- Process 10,000+ cosmic ray events per hour
- Train federated models across 8+ distributed nodes
- Achieve sub-100ms latency for real-time processing
- Demonstrate 95%+ accuracy in cosmic ray classification
- Showcase distributed computing for scientific discovery

---

**Document Version**: 1.0  
**Last Updated**: August 1, 2025  
**Status**: Ready for SCinet Review 