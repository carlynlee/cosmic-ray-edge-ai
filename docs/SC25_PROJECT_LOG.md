# SC25 Project Log
## November 8–16, 2024

Goal: demonstrate distributed cosmic ray detection with edge ML and federated learning at SC25 (Supercomputing Conference 2025).

---

## Dataset

**Total events in Elasticsearch (`credo-detections` index):** 107,804
- CosmicWatch v3X (`cosmicwatch-001`): 39,677 events, 6 days continuous
- CREDO.science historical: 69,000 detections

**CosmicWatch statistics:**
- Coincidence events (both detectors fired): 4,947 (12.3%) — ADC mean 394.5
- Non-coincidence events: 35,260 (87.7%) — ADC mean 249.4
- ADC range: 67–4,053 | Pressure range: 98,417–101,907 Pa | Temp range: 23.7–28.7°C
- Detection rate: 443–5,169 events/hour (variations reflect collection gaps + cosmic ray flux)

**Key physics finding:** 12.3% coincidence rate is within the theoretical 5–15% range for stacked detector geometry, validating the setup.

---

## Day 1–2: Data Collection & Analysis ✅

- 40,207 events exported from Elasticsearch
- Data partitioned for federated learning:
  - Node 1: 4,947 coincidence events → `node1_coincidence_events.csv`
  - Node 2: 35,260 non-coincidence events → `node2_non_coincidence_events.csv`
- Scientific analysis completed: energy spectra, coincidence rate, environmental correlations, temporal patterns
- Plots saved to `scripts/data/analysis/`

---

## Day 3–4: Baseline Model ✅

**Architecture:** MLP binary classifier (input → 64 → 32 → sigmoid), predicting coincidence flag.

**Results at threshold 0.5:**
- Accuracy: 69.78% | ROC-AUC: 0.82 | Recall: 0.88 | Precision: 0.27
- Predicted coincidence rate: 39.62% (too high — class imbalance issue)

**Optimal threshold (0.72):**
- Predicted coincidence rate: 13.35% (matches observed 12.29%)
- Precision: 0.31 | Recall: 0.34 | F1: 0.32

**Verdict:** ROC-AUC of 0.82 shows the model learns the ADC↔coincidence relationship, but precision is low due to severe class imbalance (1:7 ratio). Model was used as-is for FL demonstration rather than further tuning.

Saved: `scripts/models/binary_baseline_model.pth`, `binary_baseline_scaler.pkl`

---

## Day 5–6: Federated Learning ✅

**FL architecture:** 3 nodes (coincidence events, non-coincidence events, CREDO data), FedAvg aggregation.

**Implementation decision:** Flower framework blocked by protobuf version conflict (Flower requires <5.0.0, TensorFlow requires ≥5.28.0). Built a standalone HTTP/JSON FL implementation instead.

**Standalone FL stack:**
- `scripts/fl_server.py` — HTTP server, coordinates rounds, FedAvg aggregation
- `scripts/fl_client.py` — local training, parameter exchange
- `scripts/run_fl_experiment.py` — orchestrator (starts server + clients, collects results)

**Core FL logic verified:** data loading, local training, parameter aggregation, global model distribution, multi-round training all working.

**Known issue:** Each node has only one class (all coincidence or all non-coincidence), so local models are trivially accurate but global model convergence is limited. For production: use balanced sampling per node.

---

## Day 7–8: Integration & Testing ✅ (partial)

**Built:**
- `scripts/real_time_inference.py` — polls Elasticsearch for new events, runs model, writes `ml_prediction` + `ml_probability` fields back
- `scripts/visualization_dashboard.py` — generates `data/dashboard/dashboard_summary.png` with hourly rates, coincidence rate vs predicted rate, model accuracy
- `scripts/demo_script.py` — orchestrates the full demo pipeline

**Test results (Nov 11, 2024):**
- Model loading: ✅
- Dashboard initialization: ✅
- Elasticsearch-dependent components: ✅ when port-forward active, ✅ graceful error when not

**Elasticsearch access:** requires `kubectl port-forward -n cblee-credo svc/credo-elasticsearch-service 9200:9200`

---

## Architecture Decisions

### Why not use coincidence flag as the prediction target?
The hardware already measures coincidence directly. ML predicting it is redundant scientifically, but useful for: (1) validating the pipeline, (2) demonstrating that ML can learn physics relationships (ADC correlates with coincidence), (3) enabling federated learning with a concrete labeled task. Better future targets: energy estimation (regression), anomaly detection, multi-class energy bins.

### Transformer roadmap (Zichun's recommendations, post-SC25)
Based on correspondence with Zichun (RINO paper author, arxiv 2509.07486):
- **CREDO images** → DINO-v2/v3 vision transformers (Meta pre-trained, standard image format)
- **CosmicWatch sequences** → BERT/GPT-style, treat each event as a token, masked event modeling for pre-training
- **Multi-modal fusion** → unified embedding space for cross-modal validation (longer-term)

Foundational modules implemented in `credo/`, `cosmicwatch/`, `multimodal/` — not yet trained end-to-end.

---

## SC25 Demo Stack

```
CosmicWatch (2 stacked detectors, USB)
        ↓
import_data_to_elasticsearch.py
        ↓
Elasticsearch on NRP Nautilus (credo-detections index)
        ↓  (port-forward localhost:9200)
real_time_inference.py  →  adds ml_prediction to documents
        ↓
Kibana dashboard (credo-kibana.nrp-nautilus.io)  +  visualization_dashboard.py
        ↓
fl_server.py + fl_client.py  (federated learning rounds, 3 nodes)
```

**Backup plan if FL not ready:** demo data pipeline + Kibana + explain FL concept with architecture diagram.  
**Backup plan if model not ready:** demo data collection + analysis plots.  
**Backup plan if detector fails:** use historical data in Kibana.

---

## Key Talking Points

- Coincidence events (12.3%) represent muons with enough energy to pass through both stacked detectors simultaneously — ADC 394 vs 249 for single-detector hits
- Federated learning partitions data by coincidence type (high/low energy) + CREDO historical data; nodes share model weights, not raw data — demonstrates data sovereignty
- 0.5W detector, edge AI processing → space-ready architecture
- CREDO.science network (69K historical detections) acts as third FL node, simulating distributed multi-institution deployment

---

## Infrastructure

- **Kubernetes namespace:** `cblee-credo` on NRP Nautilus (patternlab.calit2.optiputer.net)
- **Kibana public:** https://credo-kibana.nrp-nautilus.io
- **Elasticsearch:** port-forward `svc/credo-elasticsearch-service 9200:9200`
- **ES credentials:** in environment variables `ES_USER=elastic`, `ES_PASS` (see local env)
