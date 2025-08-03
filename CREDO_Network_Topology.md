# CREDO Network Topology Diagram

## Overall Architecture

```mermaid
graph TB
    subgraph "SCinet Core Network"
        CORE[400 Gbps Backbone<br/>ConnectX-7 400Gbps]
    end
    
    subgraph "SCinet Compute Cluster"
        subgraph "St. Louis Convention Center"
            GPU1[GPU Node 1<br/>H100 SXM<br/>4x H100<br/>1.5TB RAM<br/>400Gbps NIC]
            GPU2[GPU Node 2<br/>H100 SXM<br/>4x H100<br/>1.5TB RAM<br/>400Gbps NIC]
            CPU1[CPU Node 1<br/>32-core<br/>256GB RAM<br/>1TB NVMe<br/>100Gbps NIC]
            CPU2[CPU Node 2<br/>32-core<br/>256GB RAM<br/>1TB NVMe<br/>100Gbps NIC]
            CPU3[CPU Node 3<br/>32-core<br/>256GB RAM<br/>1TB NVMe<br/>100Gbps NIC]
            CPU4[CPU Node 4<br/>32-core<br/>256GB RAM<br/>1TB NVMe<br/>100Gbps NIC]
            STORAGE[Storage Node<br/>150TB NVMe<br/>100Gbps NIC]
            CONTROL[Control Node<br/>Management<br/>100Gbps NIC]
            FL[Federated Learning Server<br/>Flower Framework<br/>Model Aggregation]
        end
    end
    
    subgraph "Caltech NOC"
        subgraph "Network Operations Center"
            ROUTER1[Router 1<br/>100Gbps<br/>Primary]
            ROUTER2[Router 2<br/>100Gbps<br/>Secondary]
            LB[Load Balancer<br/>100Gbps<br/>Traffic Mgmt]
            FW[Firewall<br/>100Gbps<br/>Security]
            BUFFER[Data Buffer<br/>1GB RAM]
            PREPROC[Preprocessor<br/>Real-time]
            QC[Quality Control]
            AGG[Aggregator<br/>Batch]
        end
    end
    
    subgraph "Distributed Sensor Network"
        CALTECH[Caltech Cosmic Ray Lab<br/>10Gbps<br/>Muon Detector<br/>Real-time Processing]
        MITUDEL[MIT/UDel Space Science Lab<br/>10Gbps<br/>Space Weather<br/>Correlation Analysis]
        PARTNER1[Partner Institution 3<br/>10Gbps<br/>Cosmic Ray Detection<br/>Local ML]
        PARTNER2[Partner Institution 4<br/>10Gbps<br/>Cosmic Ray Detection<br/>Local ML]
        PARTNER3[Partner Institution 5<br/>1Gbps<br/>Cosmic Ray Detection<br/>Local ML]
        PARTNER4[Partner Institution 6<br/>1Gbps<br/>Cosmic Ray Detection<br/>Local ML]
        PARTNER5[Partner Institution 7<br/>1Gbps<br/>Cosmic Ray Detection<br/>Local ML]
        PARTNER6[Partner Institution 8<br/>1Gbps<br/>Cosmic Ray Detection<br/>Local ML]
    end
    
    CORE --> GPU1
    CORE --> GPU2
    CORE --> CPU1
    CORE --> CPU2
    CORE --> CPU3
    CORE --> CPU4
    CORE --> STORAGE
    CORE --> CONTROL
    CORE --> FL
    
    GPU1 --> FL
    GPU2 --> FL
    CPU1 --> FL
    CPU2 --> FL
    CPU3 --> FL
    CPU4 --> FL
    
    ROUTER1 -.->|100 Gbps Primary Circuit| GPU1
    ROUTER1 -.->|100 Gbps Primary Circuit| GPU2
    ROUTER1 -.->|100 Gbps Primary Circuit| CPU1
    ROUTER1 -.->|100 Gbps Primary Circuit| CPU2
    ROUTER1 -.->|100 Gbps Primary Circuit| CPU3
    ROUTER1 -.->|100 Gbps Primary Circuit| CPU4
    ROUTER1 -.->|100 Gbps Primary Circuit| STORAGE
    ROUTER1 -.->|100 Gbps Primary Circuit| CONTROL
    ROUTER1 -.->|100 Gbps Primary Circuit| FL
    
    CALTECH --> ROUTER1
    MITUDEL --> ROUTER1
    PARTNER1 --> ROUTER1
    PARTNER2 --> ROUTER1
    PARTNER3 --> ROUTER1
    PARTNER4 --> ROUTER1
    PARTNER5 --> ROUTER1
    PARTNER6 --> ROUTER1
    
    BUFFER --> PREPROC
    PREPROC --> QC
    QC --> AGG
    AGG --> ROUTER1
    
    style CORE fill:#e1f5fe
    style GPU1 fill:#f3e5f5
    style GPU2 fill:#f3e5f5
    style FL fill:#fff3e0
    style ROUTER1 fill:#e8f5e8
    style CALTECH fill:#fff8e1
    style MITUDEL fill:#fff8e1
```

## Bandwidth Allocation

### Primary Circuit (SCinet Managed)
- **Total Bandwidth**: 100 Gbps
- **Real-time Data**: 20 Gbps (20%)
- **Federated Learning**: 60 Gbps (60%)
- **Control Traffic**: 10 Gbps (10%)
- **Monitoring**: 10 Gbps (10%)

### Secondary Circuits (Self-Managed)
- **Caltech Lab**: 10 Gbps
- **MIT/University of Delaware Lab**: 10 Gbps
- **Partner Institutions**: 40 Gbps total (5-10 Gbps each)

### Peak Usage Scenarios
- **Normal Operation**: 50 Gbps sustained
- **Federated Learning Round**: 160 Gbps burst
- **Data Synchronization**: 80 Gbps burst
- **Emergency Mode**: 200 Gbps peak

## Network Protocols

### Layer 2/3 Configuration
```
Primary Circuit:
- Protocol: IPv6
- VLAN: 1001 (Federated Learning)
- QoS: Priority queuing
- Encryption: TLS 1.3

Secondary Circuits:
- Protocol: IPv6
- VLAN: 1002 (Sensor Data)
- QoS: Best effort
- Encryption: TLS 1.3
```

### Application Protocols
```
Federated Learning: TCP/8888 (Flower)
Data Streaming: WebSocket/TLS (Port 443)
Model Transfer: HTTP/2/TLS (Port 443)
Monitoring: HTTP (Port 9090)
Control: gRPC (Port 50051)
```

## Performance Metrics

### Latency Targets
- **Real-time Events**: < 10ms
- **Model Updates**: < 100ms
- **Data Sync**: < 1s
- **Control Commands**: < 50ms

### Throughput Targets
- **Peak Data Rate**: 160 Gbps
- **Sustained Rate**: 50 Gbps
- **Storage I/O**: 100 Gbps
- **Inter-node**: 400 Gbps

### Reliability Targets
- **Uptime**: 99.9%
- **Packet Loss**: < 0.01%
- **Failover Time**: < 30s
- **Data Integrity**: 100%

## Deployment Architecture

### Compute Cluster Layout

```mermaid
graph TB
    subgraph "SCinet Compute Cluster"
        subgraph "Kubernetes Cluster"
            subgraph "Namespace: credo-fl"
                FL_SERVER[Federated Learning Server<br/>Flower Framework]
                FL_COORD[FL Coordinator<br/>Model Aggregation]
            end
            
            subgraph "Namespace: credo-data"
                DATA_PIPE[Data Pipeline<br/>Real-time Processing]
                DATA_STORE[Data Storage<br/>50TB Raw Data]
                DATA_EXPORT[Data Export<br/>25TB Processed]
            end
            
            subgraph "Namespace: credo-ml"
                ML_TRAIN[Model Training<br/>GPU Acceleration]
                ML_INFER[Model Inference<br/>Real-time]
                ML_EVAL[Model Evaluation<br/>Performance Metrics]
            end
            
            subgraph "Namespace: credo-monitor"
                MONITOR[Monitoring Stack<br/>Prometheus + Grafana]
                ALERTS[Alerting System<br/>Real-time Alerts]
                TELEMETRY[Telemetry Collection<br/>Performance Data]
            end
        end
        
        subgraph "Persistent Storage (150TB NVMe)"
            RAW[Raw Data<br/>50TB<br/>Cosmic Ray Events]
            PROCESSED[Processed Data<br/>25TB<br/>Feature Vectors]
            MODELS[Models<br/>5TB<br/>FL Models & Checkpoints]
            EXPORTS[Exports<br/>25TB<br/>Results & Visualizations]
        end
    end
    
    FL_SERVER --> FL_COORD
    FL_COORD --> ML_TRAIN
    ML_TRAIN --> ML_INFER
    ML_INFER --> ML_EVAL
    
    DATA_PIPE --> DATA_STORE
    DATA_STORE --> RAW
    DATA_EXPORT --> PROCESSED
    
    ML_TRAIN --> MODELS
    ML_EVAL --> EXPORTS
    
    MONITOR --> ALERTS
    ALERTS --> TELEMETRY
    TELEMETRY --> MONITOR
    
    style FL_SERVER fill:#fff3e0
    style ML_TRAIN fill:#f3e5f5
    style DATA_STORE fill:#e8f5e8
    style MONITOR fill:#e1f5fe
    style RAW fill:#ffebee
    style PROCESSED fill:#e8f5e8
    style MODELS fill:#f3e5f5
    style EXPORTS fill:#fff8e1
```

---

**Document Version**: 1.0  
**Last Updated**: August 1, 2025  
**Status**: Ready for SCinet Review 