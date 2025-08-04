# SC25 NRE Network Requirements: CREDO Cosmic Ray Detection Experiment

**Project**: Distributed Cosmic Ray Detection Network with Federated Learning  
**Principal Investigator**: Carlyn Lee (Caltech)  
**Institution**: California Institute of Technology  
**Proposed Collaborators**: University of Delaware, MIT (Cosmic Watch Muon Detectors)  
**NRE Title**: "Real-Time Cosmic Ray Detection and Analysis Using Distributed Sensor Networks"  
**Submission Date**: August 1, 2025  
**Repository**: https://github.com/carlynlee/credo-api-tools/tree/sc25-nre-submission  

## Summary

This NRE proposes to demonstrate a distributed cosmic ray detection network using federated learning to process real-time data from multiple sensor nodes. The experiment would explore how distributed computing could enable collaborative scientific discovery through federated learning techniques.

## Proposed Collaboration

### Institutional Roles
- **Caltech**: Project coordination, SCinet deployment, and federated learning framework
- **MIT**: Cosmic Watch muon detector expertise, cosmic ray analysis, and machine learning contributions
- **University of Delaware**: Cosmic Watch detector deployment, distributed computing expertise, and data validation

## Use Case Description

### Scientific Objective
Our experiment demonstrates real-time cosmic ray detection and analysis using a distributed network of sensors. The system processes cosmic ray detection events from multiple geographically distributed nodes, applies machine learning for pattern recognition, and uses federated learning to collaboratively train models across institutions.

### SCinet Cluster Integration
The SCinet Compute Cluster will serve as our central processing hub, enabling:
- **Real-time data aggregation** from distributed cosmic ray detectors
- **Federated learning coordination** across multiple sensor nodes
- **High-performance model training** using GPU acceleration
- **Distributed storage and analysis** of potential cosmic ray event data

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
- **Booth Location**: Caltech Booth in General Exhibit Area (St. Louis Convention Center)
- **Z Locations**: 8+ distributed sensor nodes (Caltech, MIT, University of Delaware, partner institutions)
- **Edge Processing**: Local preprocessing at each sensor node
- **Central Coordination**: Federated learning server on SCinet cluster
- **Live Demo**: Real-time processing at Caltech booth

## Network Requirements

### Physical Connections

#### Primary Circuit (SCinet Managed)
- **A Location**: SCinet Compute Cluster, St. Louis Convention Center
- **Z Location**: Caltech Network Operations Center
- **Connection Type**: 100Gbps Ethernet
- **Protocol**: Layer 3 (IPv6)
- **Bandwidth**: 100 Gbps dedicated
- **Purpose**: Primary data pipeline and federated learning coordination

#### Secondary Circuits (Self-Managed)
- **Sensor Node 1**: Caltech Cosmic Ray Lab
  - Connection: 10Gbps Ethernet
  - Protocol: Layer 3 (IPv6)
  - Bandwidth: 10 Gbps
  - Purpose: Real-time cosmic ray data transmission

- **Sensor Node 2**: MIT Cosmic Watch Lab
  - Connection: 10Gbps Ethernet
  - Protocol: Layer 3 (IPv6)
  - Bandwidth: 10 Gbps
  - Purpose: Muon detector and cosmic ray analysis

- **Sensor Node 3**: University of Delaware
  - Connection: 10Gbps Ethernet
  - Protocol: Layer 3 (IPv6)
  - Bandwidth: 10 Gbps
  - Purpose: Distributed computing and cosmic ray detection

- **Caltech Booth**: General Exhibit Area (St. Louis Convention Center)
  - Connection: 10Gbps Ethernet to SCinet cluster
  - Protocol: Layer 3 (IPv6)
  - Bandwidth: 10 Gbps
  - Purpose: Live demonstration and real-time processing

- **Sensor Node 4-8**: Partner Institutions
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
- **Federated Learning**: TCP/8888 (Flower framework)
- **Data Streaming**: WebSocket/TLS (Port 443)
- **Model Transfer**: HTTP/2/TLS (Port 443)
- **Monitoring**: HTTP (Port 9090)
- **Control**: gRPC (Port 50051)

### Network Configuration

#### Primary Circuit Details
Bandwidth: 100 Gbps
Interface: 100Gbps Ethernet
Protocol: IPv6 with QoS
VLAN: 1001 (Federated Learning)

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
- **Proposed Network Topology Diagram**: https://github.com/carlynlee/credo-api-tools/blob/sc25-nre-submission/CREDO_Network_Topology.md
- **Proposed Space Deployment Experiment**: https://github.com/carlynlee/credo-api-tools/blob/sc25-nre-submission/Space_Global_Model_Experiment.md

### Contact Information
- **Project Lead**: Carlyn Lee (cblee@caltech.edu)
- **Network Engineer**: [To be assigned by SCinet]

### Special Requirements
- **Powert and Cooling**: Adequate for GPUs
- **Physical Access**: 24/7 access to compute cluster
- **Network Access**: Dedicated 100Gbps circuit with guaranteed bandwidth

### Caltech Booth Requirements
- **Booth Space**: in general exhibit area
- **Network**: 10Gbps connection to SCinet cluster
- **Compute**: 2x CPU nodes for live demonstration
- **Storage**: 1TB NVMe for local data processing

### Success Criteria
- Process 10,000+ cosmic ray events per hour
- Train federated models across 8+ distributed nodes
- Achieve sub-100ms latency for real-time processing
- Demonstrate 95%+ accuracy in cosmic ray classification
- Showcase distributed computing for scientific discovery

## Document Links

All SC25 NRE submission documents are available in the GitHub repository:

- **Main Requirements Document**: https://github.com/carlynlee/credo-api-tools/blob/sc25-nre-submission/SC25_NRE_Network_Requirements_CREDO.md
- **Network Topology**: https://github.com/carlynlee/credo-api-tools/blob/sc25-nre-submission/CREDO_Network_Topology.md
- **Space Deployment Experiment**: https://github.com/carlynlee/credo-api-tools/blob/sc25-nre-submission/Space_Global_Model_Experiment.md
- **Repository Home**: https://github.com/carlynlee/credo-api-tools/tree/sc25-nre-submission

---

**Document Version**: 1.0  
**Last Updated**: August 1, 2025  
**Status**: Ready for SCinet Review 