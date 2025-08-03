# CREDO Deployment Architecture

## System Overview

This document describes the detailed deployment architecture for the CREDO cosmic ray detection experiment at SC25 NRE, including the Kubernetes deployment, federated learning setup, and data processing pipeline.

## Kubernetes Deployment Architecture

```mermaid
graph TB
    subgraph "SCinet Compute Cluster"
        subgraph "Namespace: credo-fl"
            FL_SERVER[Federated Learning Server<br/>Flower Framework<br/>Port: 8080]
            FL_COORD[FL Coordinator<br/>Model Aggregation<br/>Port: 8081]
            FL_MONITOR[FL Monitor<br/>Training Progress<br/>Port: 8082]
        end
        
        subgraph "Namespace: credo-data"
            DATA_INGEST[Data Ingest<br/>Real-time Collection<br/>Port: 9090]
            DATA_PROCESS[Data Processor<br/>Event Processing<br/>Port: 9091]
            DATA_STORE[Data Storage<br/>50TB Raw Data<br/>Port: 9092]
            DATA_EXPORT[Data Export<br/>25TB Processed<br/>Port: 9093]
        end
        
        subgraph "Namespace: credo-ml"
            ML_TRAIN[Model Training<br/>GPU Acceleration<br/>Port: 5000]
            ML_INFER[Model Inference<br/>Real-time Prediction<br/>Port: 5001]
            ML_EVAL[Model Evaluation<br/>Performance Metrics<br/>Port: 5002]
            ML_SERVE[Model Serving<br/>REST API<br/>Port: 5003]
        end
        
        subgraph "Namespace: credo-monitor"
            PROMETHEUS[Prometheus<br/>Metrics Collection<br/>Port: 9090]
            GRAFANA[Grafana<br/>Visualization<br/>Port: 3000]
            ALERTMANAGER[Alert Manager<br/>Alerting<br/>Port: 9093]
            TELEMETRY[Telemetry<br/>Performance Data<br/>Port: 8080]
        end
    end
    
    subgraph "Persistent Storage"
        PVC_RAW[Raw Data PVC<br/>50TB NVMe]
        PVC_PROCESSED[Processed Data PVC<br/>25TB NVMe]
        PVC_MODELS[Models PVC<br/>5TB NVMe]
        PVC_EXPORTS[Exports PVC<br/>25TB NVMe]
    end
    
    subgraph "Network Services"
        INGRESS[Ingress Controller<br/>Load Balancer<br/>Port: 80/443]
        SERVICE_MESH[Service Mesh<br/>Istio<br/>Traffic Management]
        SECRETS[Secrets Manager<br/>TLS Certificates<br/>X.509 Auth]
    end
    
    FL_SERVER --> FL_COORD
    FL_COORD --> ML_TRAIN
    ML_TRAIN --> ML_INFER
    ML_INFER --> ML_EVAL
    ML_EVAL --> ML_SERVE
    
    DATA_INGEST --> DATA_PROCESS
    DATA_PROCESS --> DATA_STORE
    DATA_STORE --> DATA_EXPORT
    
    DATA_STORE --> PVC_RAW
    DATA_EXPORT --> PVC_PROCESSED
    ML_TRAIN --> PVC_MODELS
    ML_EVAL --> PVC_EXPORTS
    
    PROMETHEUS --> GRAFANA
    GRAFANA --> ALERTMANAGER
    ALERTMANAGER --> TELEMETRY
    
    INGRESS --> FL_SERVER
    INGRESS --> ML_SERVE
    INGRESS --> GRAFANA
    
    SERVICE_MESH --> FL_SERVER
    SERVICE_MESH --> ML_SERVE
    SERVICE_MESH --> DATA_INGEST
    
    SECRETS --> FL_SERVER
    SECRETS --> ML_SERVE
    SECRETS --> DATA_INGEST
    
    style FL_SERVER fill:#fff3e0
    style ML_TRAIN fill:#f3e5f5
    style DATA_INGEST fill:#e8f5e8
    style PROMETHEUS fill:#e1f5fe
    style PVC_RAW fill:#ffebee
    style PVC_PROCESSED fill:#e8f5e8
    style PVC_MODELS fill:#f3e5f5
    style PVC_EXPORTS fill:#fff8e1
```

## Container Architecture

```mermaid
graph TB
    subgraph "Container Images"
        subgraph "Federated Learning"
            FL_IMAGE[flwr/flower:latest<br/>Federated Learning Server]
            FL_CLIENT_IMAGE[credo-fl-client:latest<br/>FL Client Container]
        end
        
        subgraph "Machine Learning"
            ML_IMAGE[tensorflow/tensorflow:2.10-gpu<br/>TensorFlow GPU]
            PYTORCH_IMAGE[pytorch/pytorch:1.12-cuda11.3<br/>PyTorch GPU]
            INFERENCE_IMAGE[credo-inference:latest<br/>Custom Inference]
        end
        
        subgraph "Data Processing"
            DATA_IMAGE[credo-data-processor:latest<br/>Custom Data Processor]
            STREAM_IMAGE[apache/kafka:2.13<br/>Stream Processing]
            STORAGE_IMAGE[elasticsearch:8.6.0<br/>Data Storage]
        end
        
        subgraph "Monitoring"
            PROM_IMAGE[prom/prometheus:latest<br/>Metrics Collection]
            GRAFANA_IMAGE[grafana/grafana:latest<br/>Visualization]
            ALERT_IMAGE[prom/alertmanager:latest<br/>Alerting]
        end
    end
    
    subgraph "Deployment Strategy"
        ROLLING[Rolling Update<br/>Zero Downtime]
        BLUE_GREEN[Blue-Green Deployment<br/>A/B Testing]
        CANARY[Canary Deployment<br/>Gradual Rollout]
    end
    
    subgraph "Resource Allocation"
        GPU_NODES[GPU Nodes<br/>2x H100 SXM<br/>8x GPUs Total]
        CPU_NODES[CPU Nodes<br/>4x 32-core<br/>128 Cores Total]
        STORAGE_NODES[Storage Nodes<br/>150TB NVMe<br/>High I/O]
    end
    
    FL_IMAGE --> FL_CLIENT_IMAGE
    ML_IMAGE --> PYTORCH_IMAGE
    PYTORCH_IMAGE --> INFERENCE_IMAGE
    DATA_IMAGE --> STREAM_IMAGE
    STREAM_IMAGE --> STORAGE_IMAGE
    PROM_IMAGE --> GRAFANA_IMAGE
    GRAFANA_IMAGE --> ALERT_IMAGE
    
    ROLLING --> GPU_NODES
    BLUE_GREEN --> CPU_NODES
    CANARY --> STORAGE_NODES
    
    style FL_IMAGE fill:#fff3e0
    style ML_IMAGE fill:#f3e5f5
    style DATA_IMAGE fill:#e8f5e8
    style PROM_IMAGE fill:#e1f5fe
```

## Service Architecture

```mermaid
graph TB
    subgraph "External Services"
        SENSOR_NETWORK[Distributed Sensor Network<br/>8+ Locations]
        NOC[Caltech NOC<br/>Network Operations Center]
        SCINET[SCinet Primary Circuit<br/>100 Gbps]
    end
    
    subgraph "Kubernetes Services"
        subgraph "Load Balancer Services"
            FL_SERVICE[credo-fl-service<br/>Type: LoadBalancer<br/>Port: 8080]
            ML_SERVICE[credo-ml-service<br/>Type: LoadBalancer<br/>Port: 5000]
            DATA_SERVICE[credo-data-service<br/>Type: LoadBalancer<br/>Port: 9090]
            MONITOR_SERVICE[credo-monitor-service<br/>Type: LoadBalancer<br/>Port: 3000]
        end
        
        subgraph "Cluster IP Services"
            FL_INTERNAL[credo-fl-internal<br/>Type: ClusterIP<br/>Port: 8081]
            ML_INTERNAL[credo-ml-internal<br/>Type: ClusterIP<br/>Port: 5001]
            DATA_INTERNAL[credo-data-internal<br/>Type: ClusterIP<br/>Port: 9091]
            MONITOR_INTERNAL[credo-monitor-internal<br/>Type: ClusterIP<br/>Port: 9090]
        end
        
        subgraph "Node Port Services"
            FL_NODEPORT[credo-fl-nodeport<br/>Type: NodePort<br/>Port: 30080]
            ML_NODEPORT[credo-ml-nodeport<br/>Type: NodePort<br/>Port: 30081]
            DATA_NODEPORT[credo-data-nodeport<br/>Type: NodePort<br/>Port: 30082]
            MONITOR_NODEPORT[credo-monitor-nodeport<br/>Type: NodePort<br/>Port: 30083]
        end
    end
    
    subgraph "Network Policies"
        FL_POLICY[FL Network Policy<br/>Allow FL Traffic]
        ML_POLICY[ML Network Policy<br/>Allow ML Traffic]
        DATA_POLICY[Data Network Policy<br/>Allow Data Traffic]
        MONITOR_POLICY[Monitor Network Policy<br/>Allow Monitor Traffic]
    end
    
    SENSOR_NETWORK --> NOC
    NOC --> SCINET
    SCINET --> FL_SERVICE
    SCINET --> ML_SERVICE
    SCINET --> DATA_SERVICE
    SCINET --> MONITOR_SERVICE
    
    FL_SERVICE --> FL_INTERNAL
    ML_SERVICE --> ML_INTERNAL
    DATA_SERVICE --> DATA_INTERNAL
    MONITOR_SERVICE --> MONITOR_INTERNAL
    
    FL_INTERNAL --> FL_NODEPORT
    ML_INTERNAL --> ML_NODEPORT
    DATA_INTERNAL --> DATA_NODEPORT
    MONITOR_INTERNAL --> MONITOR_NODEPORT
    
    FL_POLICY --> FL_SERVICE
    ML_POLICY --> ML_SERVICE
    DATA_POLICY --> DATA_SERVICE
    MONITOR_POLICY --> MONITOR_SERVICE
    
    style FL_SERVICE fill:#fff3e0
    style ML_SERVICE fill:#f3e5f5
    style DATA_SERVICE fill:#e8f5e8
    style MONITOR_SERVICE fill:#e1f5fe
```

## Storage Architecture

```mermaid
graph TB
    subgraph "Persistent Volume Claims"
        subgraph "Raw Data Storage"
            PVC_RAW[credo-raw-pvc<br/>50TB NVMe<br/>AccessMode: ReadWriteOnce]
            PV_RAW[credo-raw-pv<br/>50TB NVMe<br/>StorageClass: fast-ssd]
        end
        
        subgraph "Processed Data Storage"
            PVC_PROCESSED[credo-processed-pvc<br/>25TB NVMe<br/>AccessMode: ReadWriteOnce]
            PV_PROCESSED[credo-processed-pv<br/>25TB NVMe<br/>StorageClass: fast-ssd]
        end
        
        subgraph "Model Storage"
            PVC_MODELS[credo-models-pvc<br/>5TB NVMe<br/>AccessMode: ReadWriteMany]
            PV_MODELS[credo-models-pv<br/>5TB NVMe<br/>StorageClass: fast-ssd]
        end
        
        subgraph "Export Storage"
            PVC_EXPORTS[credo-exports-pvc<br/>25TB NVMe<br/>AccessMode: ReadWriteMany]
            PV_EXPORTS[credo-exports-pv<br/>25TB NVMe<br/>StorageClass: fast-ssd]
        end
    end
    
    subgraph "Storage Classes"
        FAST_SSD[fast-ssd<br/>NVMe Storage<br/>High Performance]
        STANDARD_SSD[standard-ssd<br/>SSD Storage<br/>Standard Performance]
        HDD[standard-hdd<br/>HDD Storage<br/>Archive Performance]
    end
    
    subgraph "Data Flow"
        RAW_DATA[Raw Cosmic Ray Events<br/>10K events/hour]
        PROCESSED_DATA[Processed Feature Vectors<br/>2048 dimensions]
        MODEL_DATA[Federated Learning Models<br/>Compressed weights]
        EXPORT_DATA[Results & Visualizations<br/>Reports & Metrics]
    end
    
    PVC_RAW --> PV_RAW
    PVC_PROCESSED --> PV_PROCESSED
    PVC_MODELS --> PV_MODELS
    PVC_EXPORTS --> PV_EXPORTS
    
    PV_RAW --> FAST_SSD
    PV_PROCESSED --> FAST_SSD
    PV_MODELS --> FAST_SSD
    PV_EXPORTS --> FAST_SSD
    
    RAW_DATA --> PVC_RAW
    PROCESSED_DATA --> PVC_PROCESSED
    MODEL_DATA --> PVC_MODELS
    EXPORT_DATA --> PVC_EXPORTS
    
    style PVC_RAW fill:#ffebee
    style PVC_PROCESSED fill:#e8f5e8
    style PVC_MODELS fill:#f3e5f5
    style PVC_EXPORTS fill:#fff8e1
    style FAST_SSD fill:#e1f5fe
```

## Security Architecture

```mermaid
graph TB
    subgraph "Authentication & Authorization"
        subgraph "Identity Management"
            SERVICE_ACCOUNTS[Kubernetes Service Accounts<br/>Namespace-specific]
            RBAC[Role-Based Access Control<br/>Fine-grained permissions]
            SECRETS[Kubernetes Secrets<br/>TLS certificates]
        end
        
        subgraph "Network Security"
            NETWORK_POLICIES[Network Policies<br/>Pod-to-pod communication]
            INGRESS_RULES[Ingress Rules<br/>External access control]
            EGRESS_RULES[Egress Rules<br/>Outbound traffic control]
        end
        
        subgraph "Data Security"
            ENCRYPTION[Data Encryption<br/>TLS 1.3 in transit<br/>AES-256 at rest]
            INTEGRITY[Data Integrity<br/>SHA-256 checksums]
            AUDIT[Audit Logging<br/>All access attempts]
        end
    end
    
    subgraph "Security Components"
        subgraph "TLS/SSL"
            TLS_CERTS[TLS Certificates<br/>X.509 certificates]
            CERT_MANAGER[Cert Manager<br/>Automatic certificate renewal]
        end
        
        subgraph "Secrets Management"
            SECRETS_STORE[Secrets Store<br/>Encrypted secrets]
            VAULT[Hashicorp Vault<br/>Centralized secrets]
        end
        
        subgraph "Monitoring"
            SECURITY_MONITOR[Security Monitoring<br/>Intrusion detection]
            COMPLIANCE[Compliance Checking<br/>Policy enforcement]
        end
    end
    
    SERVICE_ACCOUNTS --> RBAC
    RBAC --> SECRETS
    SECRETS --> NETWORK_POLICIES
    NETWORK_POLICIES --> INGRESS_RULES
    INGRESS_RULES --> EGRESS_RULES
    EGRESS_RULES --> ENCRYPTION
    ENCRYPTION --> INTEGRITY
    INTEGRITY --> AUDIT
    
    TLS_CERTS --> CERT_MANAGER
    CERT_MANAGER --> SECRETS_STORE
    SECRETS_STORE --> VAULT
    VAULT --> SECURITY_MONITOR
    SECURITY_MONITOR --> COMPLIANCE
    
    style SERVICE_ACCOUNTS fill:#e8f5e8
    style ENCRYPTION fill:#fff3e0
    style SECURITY_MONITOR fill:#e1f5fe
```

## Monitoring & Observability

```mermaid
graph TB
    subgraph "Metrics Collection"
        subgraph "Application Metrics"
            APP_METRICS[Application Metrics<br/>Custom CREDO metrics]
            BUSINESS_METRICS[Business Metrics<br/>Cosmic ray detection rate]
            PERFORMANCE_METRICS[Performance Metrics<br/>Latency & throughput]
        end
        
        subgraph "Infrastructure Metrics"
            INFRA_METRICS[Infrastructure Metrics<br/>CPU, Memory, Disk]
            NETWORK_METRICS[Network Metrics<br/>Bandwidth, Latency]
            STORAGE_METRICS[Storage Metrics<br/>I/O, Capacity]
        end
    end
    
    subgraph "Logging"
        subgraph "Application Logs"
            APP_LOGS[Application Logs<br/>Structured JSON]
            ERROR_LOGS[Error Logs<br/>Exception tracking]
            AUDIT_LOGS[Audit Logs<br/>Security events]
        end
        
        subgraph "System Logs"
            SYSTEM_LOGS[System Logs<br/>Kubernetes events]
            CONTAINER_LOGS[Container Logs<br/>Docker logs]
            NETWORK_LOGS[Network Logs<br/>Traffic analysis]
        end
    end
    
    subgraph "Tracing"
        subgraph "Distributed Tracing"
            TRACE_COLLECTOR[Trace Collector<br/>Jaeger/Zipkin]
            TRACE_ANALYZER[Trace Analyzer<br/>Performance analysis]
            TRACE_VISUALIZER[Trace Visualizer<br/>Request flows]
        end
    end
    
    subgraph "Alerting"
        subgraph "Alert Rules"
            CRITICAL_ALERTS[Critical Alerts<br/>System down]
            WARNING_ALERTS[Warning Alerts<br/>Performance degradation]
            INFO_ALERTS[Info Alerts<br/>Status updates]
        end
        
        subgraph "Notification Channels"
            EMAIL[Email Notifications<br/>SMTP]
            SLACK[Slack Notifications<br/>Webhook]
            PAGERDUTY[PagerDuty<br/>Escalation]
        end
    end
    
    APP_METRICS --> BUSINESS_METRICS
    BUSINESS_METRICS --> PERFORMANCE_METRICS
    INFRA_METRICS --> NETWORK_METRICS
    NETWORK_METRICS --> STORAGE_METRICS
    
    APP_LOGS --> ERROR_LOGS
    ERROR_LOGS --> AUDIT_LOGS
    SYSTEM_LOGS --> CONTAINER_LOGS
    CONTAINER_LOGS --> NETWORK_LOGS
    
    TRACE_COLLECTOR --> TRACE_ANALYZER
    TRACE_ANALYZER --> TRACE_VISUALIZER
    
    CRITICAL_ALERTS --> WARNING_ALERTS
    WARNING_ALERTS --> INFO_ALERTS
    INFO_ALERTS --> EMAIL
    EMAIL --> SLACK
    SLACK --> PAGERDUTY
    
    style APP_METRICS fill:#e8f5e8
    style APP_LOGS fill:#fff3e0
    style TRACE_COLLECTOR fill:#e1f5fe
    style CRITICAL_ALERTS fill:#ffebee
```

## Deployment Configuration

### Kubernetes Manifests

```yaml
# Federated Learning Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: credo-fl-server
  namespace: credo-fl
spec:
  replicas: 1
  selector:
    matchLabels:
      app: credo-fl-server
  template:
    metadata:
      labels:
        app: credo-fl-server
    spec:
      containers:
      - name: fl-server
        image: flwr/flower:latest
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "4"
            memory: "8Gi"
        env:
        - name: FL_SERVER_PORT
          value: "8080"
        - name: FL_SERVER_ADDRESS
          value: "0.0.0.0"
        volumeMounts:
        - name: fl-models
          mountPath: /models
      volumes:
      - name: fl-models
        persistentVolumeClaim:
          claimName: credo-models-pvc
---
# Machine Learning Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: credo-ml-training
  namespace: credo-ml
spec:
  replicas: 2
  selector:
    matchLabels:
      app: credo-ml-training
  template:
    metadata:
      labels:
        app: credo-ml-training
    spec:
      containers:
      - name: ml-training
        image: tensorflow/tensorflow:2.10-gpu
        ports:
        - containerPort: 5000
        resources:
          requests:
            nvidia.com/gpu: 1
            cpu: "4"
            memory: "8Gi"
          limits:
            nvidia.com/gpu: 1
            cpu: "8"
            memory: "16Gi"
        volumeMounts:
        - name: ml-data
          mountPath: /data
        - name: ml-models
          mountPath: /models
      volumes:
      - name: ml-data
        persistentVolumeClaim:
          claimName: credo-processed-pvc
      - name: ml-models
        persistentVolumeClaim:
          claimName: credo-models-pvc
```

### Service Configuration

```yaml
# Federated Learning Service
apiVersion: v1
kind: Service
metadata:
  name: credo-fl-service
  namespace: credo-fl
spec:
  selector:
    app: credo-fl-server
  ports:
  - name: http
    port: 8080
    targetPort: 8080
  type: LoadBalancer
---
# Machine Learning Service
apiVersion: v1
kind: Service
metadata:
  name: credo-ml-service
  namespace: credo-ml
spec:
  selector:
    app: credo-ml-training
  ports:
  - name: http
    port: 5000
    targetPort: 5000
  type: LoadBalancer
```

### Storage Configuration

```yaml
# Raw Data PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: credo-raw-pvc
  namespace: credo-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Ti
  storageClassName: fast-ssd
---
# Processed Data PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: credo-processed-pvc
  namespace: credo-data
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 25Ti
  storageClassName: fast-ssd
---
# Models PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: credo-models-pvc
  namespace: credo-ml
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 5Ti
  storageClassName: fast-ssd
---
# Exports PVC
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: credo-exports-pvc
  namespace: credo-ml
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 25Ti
  storageClassName: fast-ssd
```

---

**Document Version**: 1.0  
**Last Updated**: August 1, 2025  
**Status**: Ready for SCinet Review 