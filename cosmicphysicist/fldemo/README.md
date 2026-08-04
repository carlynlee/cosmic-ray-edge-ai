# Federated Edge AI for Cosmic-Ray Detection — Reproducibility Package

Minimal code and data to reproduce the measurements in:

> *Measured WAN Traffic Reduction from Federated Edge AI in a Distributed
> Cosmic-Ray Sensor Network.* C. Lee, H. Newman, Y. Wu, S. Axani.
> Submitted to INDIS 2026 (SC26 workshop). Demonstrated live as SC26 NRE115.

## What is here

| Path | Role in the paper |
|---|---|
| `model.py` | Shared model contract: features, weak labels, 3→8→1 MLP (41 params), training, FedAvg (§III) |
| `../static/model.js` | Dependency-free JavaScript port of `model.py`, runs in the browser |
| `test_parity.py` | Conformance test holding `model.py` ↔ `model.js` to machine precision (§III) |
| `fl_server.py` | FedAvg coordinator: rounds, straggler tolerance, submission validation, WAN byte counters (§III, §VI) |
| `../static/phone.html`, `../static/fl_client.js` | Browser PWA detector and federated-learning client |
| `experiment_modes.py` | Mode A vs Mode B WAN measurement campaign — regenerates Table I (§V–VI) |
| `paper_figs.py` | Regenerates the paper figures from `data/modeAB_results.json` |
| `sim_phones.js`, `dashboard.html`, `run_demo.sh` | Local demo: simulated clients + live dashboard |
| `data/real_train.json`, `data/real_val.json` | 3,131 labeled samples (2,349 train / 782 val) derived from archived phone-camera crops (§IV). Features + weak labels only; no imagery, no device identifiers |
| `data/raw_doc_sizes.json` | Empirical wire-size distribution of the 1,569 archived detection documents (Mode A cost model) |
| `data/modeAB_results.json` | Measured results behind Table I and Figs. 2–3 |
| `data/referee_summary.json` | CosmicWatch referee summary consumed by the dashboard (§VI) |

The corpus-recovery tooling (`backfill.py`, `seed.py` in the development repo)
requires the project's internal Elasticsearch archive and is therefore not
included; the derivation is described in §IV of the paper and its output is
the `data/real_*.json` files shipped here.

## Requirements

- Python 3.9+ with `pip install -r requirements.txt` (numpy, flask, requests, matplotlib)
- Node.js on `PATH` (for the parity test and simulated clients)

## Reproduce

All commands run from the `cosmicphysicist/` directory.

```bash
# 1. Verify the model wire contract (paper §III: machine-precision parity)
python -m fldemo.test_parity

# 2. Re-run the WAN measurement campaign (paper Table I; ~minutes on a laptop)
python -m fldemo.experiment_modes            # writes data/modeAB_results.json

# 3. Regenerate the paper figures from the measured results
python -m fldemo.paper_figs                  # writes fldemo/figs/*.pdf

# 4. Run the live demo locally (coordinator + 5 simulated phones + dashboard)
./fldemo/run_demo.sh                         # then open http://localhost:8088
```

To join the federation from a real phone, serve `static/` over HTTPS (camera
access requires a secure context), open `phone.html`, and point
`FL_SERVER_URL` at your coordinator. `DEPLOY.md` describes the
Kubernetes/NRP deployment used for the SC26 demonstration.

Byte accounting notes (paper §V): both modes exclude HTTP headers; federated
totals exclude the demonstration seed bootstrap; a fixed random seed gives
both modes identical client shards.
