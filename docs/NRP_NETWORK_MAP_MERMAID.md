# NRP Network Map - Mermaid Diagrams

This document contains Mermaid diagrams visualizing the NRP network architecture for the CREDO API Tools project.

## Network Topology Diagram

```mermaid
graph TB
    subgraph Internet["Internet / External Services"]
        CREDO_API["CREDO.science API<br/>api.credo.science/api/v2"]
        PublicUsers["Public Users<br/>(Web Browsers)"]
    end

    subgraph NRP[" NRP Nautilus Kubernetes Cluster<br/>Namespace: cblee-credo"]
        subgraph Ingress["Ingress Layer"]
            HAProxy["HAProxy Ingress Controller<br/>credo-kibana.nrp-nautilus.io"]
        end
        
        subgraph Services["Kubernetes Services"]
            KibanaSvc["Kibana Service<br/>credo-kibana-kb-http:5601"]
            ESSvc["Elasticsearch Service<br/>credo-elasticsearch-es-http:9200"]
        end
        
        subgraph Deployments["Deployments"]
            CREDOStream["CREDO Stream Deployment<br/>credo-stream<br/>"]
        end
        subgraph Storage["Storage & Config"]
            ESStorage["Elasticsearch<br/>Index: credo-detections"]
            Secrets["Kubernetes Secrets<br/>• credo-elasticsearch-es-elastic-user<br/>• credo-credentials<br/>• credo-token"]
            ConfigMaps["ConfigMaps<br/>• credo-stream-script"]
        end
        ESStorage --> FLClient1["Federated Learning Exploration 1<br/>CREDO smart phone K-means clustering"]
        

  
    end

    subgraph Local["Local Dev Machine"]
        PortForward["Port-Forward Process<br/>kubectl port-forward<br/>localhost:9200 → ES:9200"]
        
        subgraph DataCollection["Data Collection"]
            CWScript["import_data_to_elasticsearch.py<br/>CosmicWatch Data Collection"]
            CWDetector["CosmicWatch Detector<br/>Desktop Muon Detector v3X<br/>USB/Serial Connection"]
        end
        
        subgraph ML["Data Viz"]
            Inference["real_time_inference.py<br/>Real-Time ML Inference"]
            Dashboard["visualization_dashboard.py<br/>Visualization Dashboard"]
        end
            %% Federated Learning connections
    
        PortForward-->FLClient2["FL Exploration 2<br/>Cosmic Watch: MLP Neural Network"]

    end


    %% External to NRP connections
    CREDO_API -->|HTTPS:443<br/>Poll every 15 min| CREDOStream
    PublicUsers -->|HTTPS:443| HAProxy
    HAProxy -->|HTTP:5601| KibanaSvc
    
    %% Internal NRP connections
    KibanaSvc -->|HTTP:9200| ESSvc
    CREDOStream -->|HTTPS:9200<br/>Internal K8s Network| ESSvc
    ESSvc --> ESStorage
    
    %% CREDO Stream configuration
    Secrets --> CREDOStream
    ConfigMaps --> CREDOStream
    
    %% Local to NRP connections
    PortForward -.->|kubectl tunnel<br/>HTTPS:9200| ESSvc
    
    %% Local data collection flow
    CWDetector -->|USB/Serial| CWScript
    CWScript -->|HTTPS:9200<br/>via port-forward| PortForward
    
    %% Local ML connections
    Inference -->|HTTPS:9200<br/>via port-forward| PortForward
    Dashboard -->|HTTPS:9200<br/>via port-forward| PortForward
    



    %% Styling
    classDef internet fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef nrp fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef local fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef service fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef deployment fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    
    class CREDO_API,PublicUsers internet
    class HAProxy,KibanaSvc,ESSvc,ESStorage,Secrets,ConfigMaps nrp
    class PortForward,CWScript,CWDetector,Inference,Dashboard,FLServer,FLClient1,FLClient2,FLClient3 local
    class ESSvc,KibanaSvc service
    class CREDOStream deployment
```

## Data Flow Diagram

```mermaid
flowchart TD
    subgraph Source1["Source 1: CosmicWatch Detector"]
        CW["CosmicWatch Hardware<br/>USB/Serial"]
        CWData["Raw Detection Data<br/>Event, ADC, SiPM, Temp, etc."]
    end
    
    subgraph Source2["Source 2: CREDO.science API"]
        CREDOAPI["CREDO.science API<br/>api.credo.science/api/v2"]
        CREDOData["Legacy Detection Data"]
    end
    
    subgraph Processing["Data Processing"]
        CWScript["import_data_to_elasticsearch.py<br/>Format & Transform"]
        CREDOStream["CREDO Stream Deployment<br/>Poll & Transform"]
    end
    
    subgraph Storage["Data Storage (NRP)"]
        ES["Elasticsearch<br/>credo-detections index<br/>Namespace: cblee-credo"]
    end
    
    subgraph ML["Machine Learning Pipeline"]
        Inference["real_time_inference.py<br/>Query new events"]
        Model["ML Model<br/>Binary Classifier<br/>Coincidence Detection"]
        Update["Update Documents<br/>ml_prediction<br/>ml_probability"]
    end
    
    subgraph Visualization["Visualization & Analysis"]
        Kibana["Kibana Dashboard<br/>Public: credo-kibana.nrp-nautilus.io"]
        Dashboard["Python Dashboard<br/>visualization_dashboard.py"]
    end
    
    subgraph FL["Federated Learning"]
        Partition["Data Partitioning<br/>Node 1, 2, 3"]
        FLTrain["FL Training<br/>Distributed Model Training"]
        AggModel["Aggregated Model"]
    end
    
    %% Source to Processing
    CW -->|USB/Serial| CWScript
    CWData --> CWScript
    CREDOAPI -->|HTTPS Poll| CREDOStream
    CREDOData --> CREDOStream
    
    %% Processing to Storage
    CWScript -->|Port-Forward<br/>HTTPS:9200| ES
    CREDOStream -->|Internal K8s<br/>HTTPS:9200| ES
    
    %% Storage to ML
    ES -->|Query| Inference
    Inference --> Model
    Model --> Update
    Update -->|Update| ES
    
    %% Storage to Visualization
    ES -->|Query| Kibana
    ES -->|Port-Forward<br/>Query| Dashboard
    
    %% Storage to FL
    ES -->|Export| Partition
    Partition --> FLTrain
    FLTrain --> AggModel
    AggModel -->|Update| Model
    
    %% Styling
    classDef source fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef process fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef storage fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef ml fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef viz fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef fl fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    
    class CW,CWData,CREDOAPI,CREDOData source
    class CWScript,CREDOStream process
    class ES storage
    class Inference,Model,Update ml
    class Kibana,Dashboard viz
    class Partition,FLTrain,AggModel fl
```

## Component Relationship Diagram

```mermaid
graph LR
    subgraph NRPCluster["NRP Kubernetes Cluster"]
        subgraph Namespace["Namespace: cblee-credo"]
            ES[("Elasticsearch<br/>Data Storage")]
            KB[("Kibana<br/>Visualization")]
            CS[("CREDO Stream<br/>Data Import")]
        end
        
        ING[("Ingress<br/>HAProxy")]
    end
    
    subgraph External["External"]
        API[("CREDO.science<br/>API")]
        USERS[("Public<br/>Users")]
    end
    
    subgraph LocalDev["Local Development"]
        PF[("Port-Forward<br/>Tunnel")]
        CW[("CosmicWatch<br/>Detector")]
        ML[("ML Pipeline<br/>Inference")]
        VIZ[("Dashboard<br/>Visualization")]
        FL[("Federated<br/>Learning")]
    end
    
    %% External to NRP
    API -->|HTTPS| CS
    USERS -->|HTTPS| ING
    ING -->|HTTP| KB
    
    %% NRP Internal
    CS -->|HTTPS| ES
    KB -->|HTTP| ES
    
    %% Local to NRP
    PF -.->|kubectl tunnel| ES
    CW -->|USB/Serial| PF
    ML -->|Query/Update| PF
    VIZ -->|Query| PF
    FL -->|Train| ML
    
    %% Styling
    classDef nrp fill:#fff3e0,stroke:#e65100,stroke-width:3px
    classDef external fill:#e1f5ff,stroke:#01579b,stroke-width:3px
    classDef local fill:#f3e5f5,stroke:#4a148c,stroke-width:3px
    
    class ES,KB,CS,ING nrp
    class API,USERS external
    class PF,CW,ML,VIZ,FL local
```

## Deployment Architecture Diagram

```mermaid
graph TB
    subgraph K8s["Kubernetes Cluster (NRP Nautilus)"]
        subgraph NS["Namespace: cblee-credo"]
            subgraph Pods["Pods"]
                ESPod["Elasticsearch Pods<br/>StatefulSet"]
                KBPod["Kibana Pod<br/>Deployment"]
                CSPod["CREDO Stream Pod<br/>Deployment"]
            end
            
            subgraph Svc["Services"]
                ESSvc["credo-elasticsearch-es-http<br/>ClusterIP:9200"]
                KBSvc["credo-kibana-kb-http<br/>ClusterIP:5601"]
            end
            
            subgraph Config["Configuration"]
                ESSecret["Secret:<br/>credo-elasticsearch-es-elastic-user"]
                CREDOSecret["Secret:<br/>credo-credentials<br/>credo-token"]
                ScriptCM["ConfigMap:<br/>credo-stream-script"]
            end
        end
        
        subgraph IngressNS["Ingress Namespace"]
            Ingress["Ingress:<br/>credo-kibana-ingress<br/>Host: credo-kibana.nrp-nautilus.io"]
        end
    end
    
    subgraph Internet["Internet"]
        Users["Users"]
        CREDOAPI["CREDO.science API"]
    end
    
    subgraph Local["Local Machine"]
        KubeCtl["kubectl<br/>port-forward"]
        Apps["Applications<br/>• Data Collection<br/>• ML Inference<br/>• Dashboard"]
    end
    
    %% Pod to Service
    ESPod --> ESSvc
    KBPod --> KBSvc
    CSPod --> ESSvc
    
    %% Service to Ingress
    KBSvc --> Ingress
    
    %% Config to Pods
    ESSecret --> ESPod
    CREDOSecret --> CSPod
    ScriptCM --> CSPod
    
    %% External connections
    Users -->|HTTPS:443| Ingress
    CREDOAPI -->|HTTPS:443| CSPod
    
    %% Local connections
    KubeCtl -.->|Tunnel| ESSvc
    Apps -->|localhost:9200| KubeCtl
    
    %% Styling
    classDef pod fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    classDef svc fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef config fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef ingress fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef external fill:#ffebee,stroke:#c62828,stroke-width:2px
    classDef local fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    
    class ESPod,KBPod,CSPod pod
    class ESSvc,KBSvc svc
    class ESSecret,CREDOSecret,ScriptCM config
    class Ingress ingress
    class Users,CREDOAPI external
    class KubeCtl,Apps local
```

## Federated Learning Architecture

```mermaid
graph TB
    subgraph Data["Data Sources"]
        ES[("Elasticsearch<br/>credo-detections")]
    end
    
    subgraph Partition["Data Partitioning"]
        Node1["Node 1<br/>Coincidence Events<br/>High Energy"]
        Node2["Node 2<br/>Non-Coincidence Events<br/>Background"]
        Node3["Node 3<br/>CREDO Legacy Data<br/>Optional"]
    end
    
    subgraph FLSystem["Federated Learning System"]
        FLServer["FL Server<br/>fl_server.py:8080<br/>• Parameter Aggregation<br/>• Federated Averaging"]
        
        FLClient1["FL Client 1<br/>Node 1 Data<br/>• Local Training<br/>• Parameter Submission"]
        FLClient2["FL Client 2<br/>Node 2 Data<br/>• Local Training<br/>• Parameter Submission"]
        FLClient3["FL Client 3<br/>Node 3 Data<br/>• Local Training<br/>• Parameter Submission"]
    end
    
    subgraph Model["Model Management"]
        GlobalModel["Global Model<br/>Aggregated Parameters"]
        LocalModels["Local Models<br/>Per-Node Trained"]
    end
    
    subgraph Deployment["Model Deployment"]
        Inference["Real-Time Inference<br/>real_time_inference.py"]
        Production["Production Model<br/>Binary Classifier"]
    end
    
    %% Data flow
    ES -->|Export| Node1
    ES -->|Export| Node2
    ES -->|Export| Node3
    
    %% Partition to FL
    Node1 --> FLClient1
    Node2 --> FLClient2
    Node3 --> FLClient3
    
    %% FL Training cycle
    FLClient1 -->|Submit Parameters| FLServer
    FLClient2 -->|Submit Parameters| FLServer
    FLClient3 -->|Submit Parameters| FLServer
    
    FLServer -->|Aggregate| GlobalModel
    GlobalModel -->|Distribute| FLClient1
    GlobalModel -->|Distribute| FLClient2
    GlobalModel -->|Distribute| FLClient3
    
    FLClient1 --> LocalModels
    FLClient2 --> LocalModels
    FLClient3 --> LocalModels
    
    %% Model to deployment
    GlobalModel --> Production
    Production --> Inference
    
    %% Styling
    classDef data fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef partition fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef fl fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef model fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef deploy fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    
    class ES data
    class Node1,Node2,Node3 partition
    class FLServer,FLClient1,FLClient2,FLClient3 fl
    class GlobalModel,LocalModels model
    class Inference,Production deploy
```

## Sequence Diagram: Data Collection Flow

```mermaid
sequenceDiagram
    participant CW as CosmicWatch Detector
    participant Script as import_data_to_elasticsearch.py
    participant PF as Port-Forward
    participant ES as Elasticsearch (NRP)
    participant KB as Kibana
    participant User as User/Public

    CW->>Script: USB/Serial Data<br/>(Event, ADC, SiPM, etc.)
    Script->>Script: Format & Transform Data
    Script->>PF: POST /credo-detections/_doc<br/>HTTPS:9200
    PF->>ES: Forward Request<br/>Internal K8s Network
    ES->>ES: Index Document
    ES-->>PF: Success Response
    PF-->>Script: Success
    Script->>Script: Log Upload Count
    
    Note over ES,KB: Real-time Indexing
    ES->>KB: Index Update Available
    KB->>User: Display in Dashboard<br/>credo-kibana.nrp-nautilus.io
```

## Sequence Diagram: ML Inference Flow

```mermaid
sequenceDiagram
    participant ES as Elasticsearch (NRP)
    participant PF as Port-Forward
    participant Inference as real_time_inference.py
    participant Model as ML Model
    participant KB as Kibana

    loop Every 30 seconds
        Inference->>PF: Query New Events<br/>GET /credo-detections/_search
        PF->>ES: Forward Query
        ES-->>PF: Return Documents
        PF-->>Inference: Documents
        
        Inference->>Inference: Extract Features<br/>(ADC, SiPM, Temp, etc.)
        Inference->>Model: Run Inference
        Model-->>Inference: Prediction + Probability
        
        Inference->>PF: Update Document<br/>POST /credo-detections/_update/{id}
        PF->>ES: Forward Update
        ES->>ES: Add ml_prediction<br/>ml_probability fields
        ES-->>PF: Success
        PF-->>Inference: Success
        
        Note over ES,KB: Updated documents available
        ES->>KB: Index Update
        KB->>KB: Refresh Dashboard
    end
```

## Sequence Diagram: CREDO Stream Flow

```mermaid
sequenceDiagram
    participant API as CREDO.science API
    participant Stream as CREDO Stream Pod
    participant ES as Elasticsearch (NRP)
    participant KB as Kibana

    loop Every 15 minutes
        Stream->>API: Poll for New Data<br/>GET /api/v2/detections
        API-->>Stream: Return Detections
        
        alt Rate Limited
            API-->>Stream: 429 Too Many Requests
            Stream->>Stream: Backoff 30 minutes
        else Success
            Stream->>Stream: Transform Data
            Stream->>ES: POST /credo-detections/_doc<br/>HTTPS:9200 (Internal)
            ES->>ES: Index Document
            ES-->>Stream: Success
            
            Note over ES,KB: Real-time Indexing
            ES->>KB: Index Update Available
            KB->>KB: Refresh Dashboard
        end
    end
```

## Network Ports and Protocols

```mermaid
graph LR
    subgraph External["External Access"]
        E1["HTTPS:443<br/>Public → Ingress"]
        E2["HTTPS:443<br/>Stream → CREDO API"]
    end
    
    subgraph NRP["NRP Internal"]
        N1["HTTP:5601<br/>Ingress → Kibana"]
        N2["HTTPS:9200<br/>Kibana → Elasticsearch"]
        N3["HTTPS:9200<br/>Stream → Elasticsearch"]
    end
    
    subgraph Local["Local Access"]
        L1["HTTPS:9200<br/>Port-Forward → ES"]
        L2["USB/Serial<br/>Detector → Script"]
        L3["HTTP:8080<br/>FL Clients → FL Server"]
    end
    
    External --> NRP
    NRP --> Local
    
    classDef external fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef nrp fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef local fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    
    class E1,E2 external
    class N1,N2,N3 nrp
    class L1,L2,L3 local
```

## Legend

- **Blue nodes**: External/Internet services
- **Orange nodes**: NRP Kubernetes cluster components
- **Purple nodes**: Local development machine components
- **Green nodes**: Services and storage
- **Yellow nodes**: Deployments and pods
- **Pink nodes**: Visualization and ML components

## Usage

These Mermaid diagrams can be viewed in:
- GitHub (renders automatically in markdown)
- VS Code (with Mermaid extension)
- Online Mermaid editor: https://mermaid.live/
- Documentation tools that support Mermaid

To render locally, you can use:
```bash
# Install Mermaid CLI
npm install -g @mermaid-js/mermaid-cli

# Render to PNG
mmdc -i docs/NRP_NETWORK_MAP_MERMAID.md -o docs/nrp_network_map.png

# Or use online editor
# Copy diagram code to https://mermaid.live/
```

