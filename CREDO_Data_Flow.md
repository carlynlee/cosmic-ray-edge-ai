# CREDO Data Flow Diagram

## Overall Data Flow Architecture

```mermaid
graph LR
    subgraph "Sensor Nodes"
        SENSORS[8+ Distributed Sensor Nodes<br/>Cosmic Ray Detectors]
    end
    
    subgraph "Data Pipeline"
        PIPELINE[Real-time Data Processing<br/>Event Collection & Preprocessing]
    end
    
    subgraph "ML Processing"
        ML[GPU/CPU Processing<br/>Feature Extraction & Model Training]
    end
    
    subgraph "Federated Learning"
        FL[Distributed Model Training<br/>Privacy-Preserving Collaboration]
    end
    
    SENSORS --> PIPELINE
    PIPELINE --> ML
    ML --> FL
    
    subgraph "Data Types"
        RAW[Raw Events<br/>10K/hour]
        PREPROC[Preprocessed Data<br/>Cleaned & Validated]
        FEATURES[Feature Vectors<br/>2048-dimensional]
        GLOBAL[Global Model<br/>Aggregated Weights]
    end
    
    SENSORS -.-> RAW
    PIPELINE -.-> PREPROC
    ML -.-> FEATURES
    FL -.-> GLOBAL
    
    style SENSORS fill:#fff8e1
    style PIPELINE fill:#e8f5e8
    style ML fill:#f3e5f5
    style FL fill:#fff3e0
```

## Detailed Data Flow

### Phase 1: Data Collection

```mermaid
graph TB
    subgraph "Sensor Data Collection"
        subgraph "Caltech Lab"
            CALTECH[Caltech Cosmic Ray Lab<br/>Muon Detector<br/>Event Rate: 2K/hour<br/>Data Size: 1MB/event]
            CALTECH_BUFFER[Local Buffer<br/>100 events]
        end
        
        subgraph "MIT/UDel Lab"
            MITUDEL[MIT/UDel Space Science Lab<br/>Space Weather Sensors<br/>Event Rate: 2K/hour<br/>Data Size: 2MB/event]
            MITUDEL_BUFFER[Local Buffer<br/>100 events]
        end
        
        subgraph "Partner Institutions"
            PARTNER1[Partner Institution 3<br/>Cosmic Ray Detectors<br/>Event Rate: 1K/hour<br/>Data Size: 0.5MB/event]
            PARTNER1_BUFFER[Local Buffer<br/>50 events]
            
            PARTNER2[Partner Institution 4<br/>Cosmic Ray Detectors<br/>Event Rate: 1K/hour<br/>Data Size: 0.5MB/event]
            PARTNER2_BUFFER[Local Buffer<br/>50 events]
        end
    end
    
    CALTECH --> CALTECH_BUFFER
    MITUDEL --> MITUDEL_BUFFER
    PARTNER1 --> PARTNER1_BUFFER
    PARTNER2 --> PARTNER2_BUFFER
    
    style CALTECH fill:#fff8e1
    style MITUDEL fill:#fff8e1
    style PARTNER1 fill:#e1f5fe
    style PARTNER2 fill:#e1f5fe
```

### Phase 2: Data Transmission

```mermaid
graph TB
    subgraph "Network Transmission"
        subgraph "Sensor Nodes"
            CALTECH_NET[Caltech → NOC<br/>10 Gbps<br/>Latency: <10ms]
            MITUDEL_NET[MIT/UDel → NOC<br/>10 Gbps<br/>Latency: <10ms]
            PARTNER1_NET[Partner → NOC<br/>1-10 Gbps<br/>Latency: <50ms]
            PARTNER2_NET[Partner → NOC<br/>1-10 Gbps<br/>Latency: <50ms]
        end
        
        subgraph "Caltech NOC"
            subgraph "Network Operations Center"
                BUFFER[Data Buffer<br/>1GB RAM]
                PREPROC[Preprocessor<br/>Real-time Processing]
                QC[Quality Control<br/>Validation & Filtering]
                AGG[Aggregator<br/>Batch Processing]
            end
        end
    end
    
    CALTECH_NET --> BUFFER
    MITUDEL_NET --> BUFFER
    PARTNER1_NET --> BUFFER
    PARTNER2_NET --> BUFFER
    
    BUFFER --> PREPROC
    PREPROC --> QC
    QC --> AGG
    
    style BUFFER fill:#e8f5e8
    style PREPROC fill:#e8f5e8
    style QC fill:#e8f5e8
    style AGG fill:#e8f5e8
```

### Phase 3: SCinet Transmission

```mermaid
graph TB
    subgraph "SCinet Primary Circuit"
        subgraph "Caltech NOC"
            AGGREGATED[Aggregated Data<br/>10K events]
            COMPRESSED[Compressed Data<br/>50% size reduction]
            ENCRYPTED[Encrypted Data<br/>TLS 1.3]
            TRANSMITTED[Transmitted Data<br/>100 Gbps circuit]
        end
        
        subgraph "SCinet Compute Cluster"
            RECEIVED[Received Data<br/>10K events]
            DECOMPRESSED[Decompressed Data<br/>Full size restoration]
            VALIDATED[Validated Data<br/>QC passed]
            STORED[Stored Data<br/>50TB NVMe]
        end
    end
    
    AGGREGATED --> COMPRESSED
    COMPRESSED --> ENCRYPTED
    ENCRYPTED --> TRANSMITTED
    TRANSMITTED --> RECEIVED
    RECEIVED --> DECOMPRESSED
    DECOMPRESSED --> VALIDATED
    VALIDATED --> STORED
    
    style AGGREGATED fill:#e8f5e8
    style ENCRYPTED fill:#fff3e0
    style STORED fill:#f3e5f5
```

### Phase 4: Machine Learning Processing

```mermaid
graph TB
    subgraph "ML Processing Pipeline"
        subgraph "Data Storage"
            RAW_STORAGE[Raw Data Storage<br/>50TB NVMe<br/>Cosmic Ray Events]
        end
        
        subgraph "Feature Extraction"
            FEATURE_EXTR[Feature Extraction<br/>ResNet50<br/>2048-dimensional vectors]
        end
        
        subgraph "Model Training"
            MODEL_TRAIN[Model Training<br/>GPU Nodes<br/>H100 SXM]
        end
        
        subgraph "Results Storage"
            RESULTS_STORAGE[Results Storage<br/>25TB NVMe<br/>Processed Data]
        end
    end
    
    subgraph "Processing Components"
        DATA_LOADER[Data Loader<br/>10K events<br/>Batch processing]
        FEATURE_VECTORS[Feature Vectors<br/>2048 dimensions]
        TRAINING_LOOP[Training Loop<br/>5 rounds]
        MODEL_CHECKPOINTS[Model Checkpoints<br/>5TB storage]
    end
    
    RAW_STORAGE --> DATA_LOADER
    DATA_LOADER --> FEATURE_EXTR
    FEATURE_EXTR --> FEATURE_VECTORS
    FEATURE_VECTORS --> MODEL_TRAIN
    MODEL_TRAIN --> TRAINING_LOOP
    TRAINING_LOOP --> MODEL_CHECKPOINTS
    MODEL_TRAIN --> RESULTS_STORAGE
    
    style RAW_STORAGE fill:#ffebee
    style MODEL_TRAIN fill:#f3e5f5
    style RESULTS_STORAGE fill:#e8f5e8
```

### Phase 5: Federated Learning

```mermaid
graph TB
    subgraph "Federated Learning Flow"
        subgraph "Local Training"
            LOCAL_TRAIN[Local Model Training<br/>Per Node<br/>Device-specific data]
        end
        
        subgraph "Model Aggregation"
            MODEL_AGG[Model Aggregation<br/>Server<br/>Federated Average]
        end
        
        subgraph "Global Update"
            GLOBAL_UPDATE[Global Model Update<br/>Broadcast<br/>Updated weights]
        end
        
        subgraph "Distributed Deployment"
            DIST_DEPLOY[Distributed Deployment<br/>All Nodes<br/>Updated models]
        end
    end
    
    subgraph "FL Components"
        WEIGHT_UPDATES[Weight Updates<br/>Compressed<br/>Model gradients]
        FED_AVG[Federated Average<br/>Algorithm<br/>Weight aggregation]
        UPDATED_WEIGHTS[Updated Weights<br/>Broadcast<br/>Global model]
        PERFORMANCE[Performance Metrics<br/>Monitoring<br/>Accuracy tracking]
    end
    
    LOCAL_TRAIN --> WEIGHT_UPDATES
    WEIGHT_UPDATES --> MODEL_AGG
    MODEL_AGG --> FED_AVG
    FED_AVG --> GLOBAL_UPDATE
    GLOBAL_UPDATE --> UPDATED_WEIGHTS
    UPDATED_WEIGHTS --> DIST_DEPLOY
    DIST_DEPLOY --> PERFORMANCE
    
    style LOCAL_TRAIN fill:#fff8e1
    style MODEL_AGG fill:#fff3e0
    style GLOBAL_UPDATE fill:#e1f5fe
    style DIST_DEPLOY fill:#e8f5e8
```

## Data Volume Analysis

### Real-time Data Flow
```
Hourly Data Volume:
├── Caltech Lab: 2,000 events × 1MB = 2GB/hour
├── MIT/UDel Lab: 2,000 events × 2MB = 4GB/hour
├── Partner Institutions: 6,000 events × 0.5MB = 3GB/hour
└── Total: 10,000 events = 9GB/hour = 216GB/day
```

### Network Bandwidth Requirements
```
Peak Bandwidth Usage:
├── Real-time Events: 20 Gbps (continuous)
├── Federated Learning: 60 Gbps (burst during rounds)
├── Model Updates: 40 Gbps (burst during aggregation)
├── Control Traffic: 10 Gbps (continuous)
└── Total Peak: 160 Gbps
```

### Storage Requirements
```
Data Storage Breakdown:
├── Raw Data: 50TB (cosmic ray events)
├── Processed Data: 25TB (feature vectors)
├── Model Storage: 5TB (federated learning models)
├── Temporary Storage: 20TB (intermediate processing)
└── Total: 100TB NVMe storage
```

## Processing Latency

### End-to-End Latency Targets
```
Real-time Processing:
├── Sensor → Local Buffer: < 1ms
├── Local Buffer → NOC: < 10ms
├── NOC → SCinet: < 50ms
├── SCinet → Processing: < 100ms
├── Processing → Results: < 500ms
└── Total End-to-End: < 661ms
```

### Federated Learning Latency
```
Model Training Cycle:
├── Local Training: 30-60 seconds
├── Weight Upload: < 100ms
├── Global Aggregation: < 50ms
├── Model Broadcast: < 100ms
└── Total Round: 31-61 seconds
```

## Data Security & Integrity

### Encryption & Authentication
```
Security Measures:
├── Data in Transit: TLS 1.3 encryption
├── Data at Rest: AES-256 encryption
├── Authentication: X.509 certificates
├── Authorization: Role-based access control
└── Integrity: SHA-256 checksums
```

### Quality Control
```
Data Validation:
├── Format Validation: JSON schema compliance
├── Content Validation: Cosmic ray event structure
├── Timestamp Validation: Event timing accuracy
├── Source Validation: Sensor authentication
└── Quality Score: > 95% valid events
```

## Performance Monitoring

### Real-time Metrics
```
Monitoring Points:
├── Network Latency: < 10ms (sensor to NOC)
├── Data Throughput: 50 Gbps sustained
├── Processing Speed: 10K events/hour
├── Model Accuracy: > 95% classification
└── System Uptime: 99.9% availability
```

### Alerting Thresholds
```
Alert Conditions:
├── Latency > 100ms: Warning
├── Latency > 500ms: Critical
├── Throughput < 80%: Warning
├── Throughput < 50%: Critical
├── Error Rate > 1%: Warning
└── Error Rate > 5%: Critical
```

---

**Document Version**: 1.0  
**Last Updated**: August 1, 2025  
**Status**: Ready for SCinet Review 