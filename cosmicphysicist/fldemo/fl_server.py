#!/usr/bin/env python3
"""
Federated-learning server for the SC26 phone demo.

Coordinates FL rounds across many browser (phone) clients that each train the
shared tiny MLP (see model.py) locally and submit only weights. The server
FedAvg-averages submissions into a global model, evaluates it on a held-out
validation set after every round, and exposes /status so the dashboard can plot
the global-accuracy curve live.

Framework-light on purpose: plain Flask + numpy (no torch), manual CORS so
browsers can call it, in-memory state. Runnable locally; deployable to NRP.

Endpoints (JSON):
  POST /register          {client_id}                  -> {round, lr, parameters}
  POST /get_global_model  {client_id}                  -> {round, lr, parameters}
  POST /submit_params     {client_id, parameters, sample_count, round}
                                                        -> {accepted, round}
  GET  /status                                          -> dashboard state
  GET  /health                                          -> {ok:true}
"""

import argparse
import json
import os
import threading
import time

import numpy as np
from flask import Flask, jsonify, request, send_file

try:
    from . import model as M, synth          # run as package: python -m fldemo.fl_server
except ImportError:                           # run flat in a pod: python /app/fl_server.py
    import model as M
    import synth

app = Flask(__name__)

# --- config ------------------------------------------------------------------
MIN_CLIENTS = int(os.environ.get("FL_MIN_CLIENTS", "2"))   # close round at N submits
ROUND_TIMEOUT_S = float(os.environ.get("FL_ROUND_TIMEOUT_S", "8"))
# Few local steps + lr decay keeps client updates small so FedAvg stays coherent
# (large local steps let each client's hidden units permute and averaging then
# degrades the global model — a jagged/declining curve on stage).
LR0 = float(os.environ.get("FL_LR", "0.5"))
LR_DECAY = float(os.environ.get("FL_LR_DECAY", "0.95"))
LR_MIN = float(os.environ.get("FL_LR_MIN", "0.05"))
LOCAL_EPOCHS = int(os.environ.get("FL_LOCAL_EPOCHS", "1"))  # advertised to clients
VAL_PATH = os.environ.get("FL_VAL_PATH")                    # JSON list of hit dicts
SEED_PATH = os.environ.get("FL_SEED_PATH")                  # training pool for /seed
SEED_N = int(os.environ.get("FL_SEED_N", "120"))            # hits served per client
REFEREE_PATH = os.environ.get("FL_REFEREE_PATH",
    os.path.join(os.path.dirname(__file__), "data", "referee_summary.json"))
# Estimated wire size of ONE raw detection (60x60 crop + metadata) if it had
# been uploaded instead of trained on locally. Empirical distribution over all
# 1,569 real ES phone-camera docs: median 1691B, mean 1673B (see
# data/raw_doc_sizes.json). Used only for the labelled "kept on device"
# estimate — actual FL traffic is measured.
RAW_HIT_BYTES = int(os.environ.get("FL_RAW_HIT_BYTES", "1673"))
# Optional admin token: when set, /reset requires "Authorization: Bearer <it>".
# Leave unset for local runs; ALWAYS set for any public deployment.
ADMIN_TOKEN = os.environ.get("FL_ADMIN_TOKEN", "")
# BYOD clients are untrusted: cap the FedAvg weight any one client can claim.
MAX_SAMPLE_COUNT = int(os.environ.get("FL_MAX_SAMPLE_COUNT", "1000"))
MAX_WEIGHT_ABS = 1e3   # sanity bound on submitted parameters
CLIENT_STALE_S = 30.0
_HERE = os.path.dirname(__file__)


def _valid_weights(p):
    """Strict shape/value check on client-submitted weights. A single NaN or
    wrong-shaped submission would otherwise poison FedAvg and wreck the global
    model mid-demo. Returns True only for a well-formed, finite, bounded set."""
    try:
        W1 = np.asarray(p["W1"], dtype=np.float64)
        b1 = np.asarray(p["b1"], dtype=np.float64)
        W2 = np.asarray(p["W2"], dtype=np.float64)
        b2 = np.asarray(p["b2"], dtype=np.float64)
    except (KeyError, TypeError, ValueError):
        return False
    if (W1.shape != (M.HIDDEN, M.IN_DIM) or b1.shape != (M.HIDDEN,)
            or W2.shape != (M.OUT_DIM, M.HIDDEN) or b2.shape != (M.OUT_DIM,)):
        return False
    for a in (W1, b1, W2, b2):
        if not np.isfinite(a).all() or np.abs(a).max() > MAX_WEIGHT_ABS:
            return False
    return True


def _referee():
    if os.path.exists(REFEREE_PATH):
        try:
            with open(REFEREE_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"headline": "CosmicWatch referee offline", "flux_hz": None,
            "beta_pct_per_hpa": None, "verdict": None}


class FLState:
    def __init__(self):
        self.lock = threading.Lock()
        self.round = 0
        self.global_w = M.init_weights(0)
        self.buffer = {}                 # client_id -> {"w":.., "n":.., "loss":..}
        self.round_start = time.time()
        self.clients = {}                # client_id -> {"last_seen","submits","samples"}
        self.acc_curve = []              # [{"round","accuracy","n_clients"}]
        # Measured WAN bytes by endpoint: {path: {"in": n, "out": n, "calls": n}}
        self.wan = {}
        self.seed_pool = self._load_seed()
        self.Xval, self.yval = self._load_val()
        self.acc_curve.append({"round": 0,
                               "accuracy": M.accuracy(self.global_w, self.Xval, self.yval),
                               "n_clients": 0})

    def _load_val(self):
        hits = None
        if VAL_PATH and os.path.exists(VAL_PATH):
            with open(VAL_PATH) as f:
                hits = json.load(f)
            app.logger.info(f"[fl] loaded {len(hits)} validation hits from {VAL_PATH}")
        if not hits:
            hits = synth.make_hits(400, seed=999)
            app.logger.info("[fl] using synthetic validation set (set FL_VAL_PATH for real data)")
        X = np.array([M.extract_features(h) for h in hits], dtype=np.float64)
        y = np.array([h.get("label", M.weak_label(h)) for h in hits], dtype=np.float64)
        return X, y

    def _load_seed(self):
        if SEED_PATH and os.path.exists(SEED_PATH):
            with open(SEED_PATH) as f:
                pool = json.load(f)
            app.logger.info(f"[fl] loaded {len(pool)} seed hits from {SEED_PATH}")
            return pool
        pool = synth.make_hits(1200, seed=7)
        for h in pool:
            h["label"] = M.weak_label(h)
        app.logger.info("[fl] using synthetic seed pool (set FL_SEED_PATH for real data)")
        return pool

    def lr(self):
        return max(LR_MIN, LR0 * (LR_DECAY ** self.round))

    def touch(self, cid):
        c = self.clients.setdefault(cid, {"first_seen": time.time(), "submits": 0,
                                          "samples": 0, "last_seen": 0})
        c["last_seen"] = time.time()

    def reset_locked(self):
        """Re-initialise the global model (demo attract-loop: replay the climb).
        Keeps the client registry so tiles persist. Caller holds lock."""
        self.round = 0
        self.global_w = M.init_weights(0)
        self.buffer = {}
        self.round_start = time.time()
        self.acc_curve = [{"round": 0,
                           "accuracy": M.accuracy(self.global_w, self.Xval, self.yval),
                           "n_clients": 0}]
        app.logger.info("[fl] global model reset")

    def close_round_locked(self):
        """Aggregate buffered updates into the global model. Caller holds lock."""
        if not self.buffer:
            return
        ws = [b["w"] for b in self.buffer.values()]
        ns = [b["n"] for b in self.buffer.values()]
        self.global_w = M.fedavg(ws, ns)
        self.round += 1
        acc = M.accuracy(self.global_w, self.Xval, self.yval)
        self.acc_curve.append({"round": self.round, "accuracy": acc,
                               "n_clients": len(self.buffer)})
        app.logger.info(f"[fl] round {self.round} closed: {len(self.buffer)} clients, "
                        f"acc={acc:.3f}, lr={self.lr():.3f}")
        self.buffer = {}
        self.round_start = time.time()


state = FLState()


def _reaper():
    """Close a round on timeout so a few clients still make progress."""
    while True:
        time.sleep(1.0)
        with state.lock:
            if state.buffer and (time.time() - state.round_start) > ROUND_TIMEOUT_S:
                state.close_round_locked()


@app.after_request
def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    # WAN byte accounting (headline demo metric): measure actual request /
    # response payload sizes per endpoint. Dashboard polling is excluded so the
    # numbers reflect the experiment's traffic, not the display's.
    path = request.path
    if request.method != "OPTIONS" and path not in ("/status", "/referee", "/", "/health"):
        n_in = request.content_length or 0
        n_out = resp.calculate_content_length() or 0
        with state.lock:
            e = state.wan.setdefault(path, {"in": 0, "out": 0, "calls": 0})
            e["in"] += n_in
            e["out"] += n_out
            e["calls"] += 1
    return resp


@app.route("/register", methods=["POST", "OPTIONS"])
def register():
    if request.method == "OPTIONS":
        return ("", 204)
    cid = (request.json or {}).get("client_id", "anon")
    with state.lock:
        state.touch(cid)
        return jsonify(round=state.round, lr=state.lr(),
                       local_epochs=LOCAL_EPOCHS, parameters=state.global_w)


@app.route("/get_global_model", methods=["POST", "OPTIONS"])
def get_global_model():
    if request.method == "OPTIONS":
        return ("", 204)
    cid = (request.json or {}).get("client_id", "anon")
    with state.lock:
        state.touch(cid)
        return jsonify(round=state.round, lr=state.lr(),
                       local_epochs=LOCAL_EPOCHS, parameters=state.global_w)


@app.route("/submit_params", methods=["POST", "OPTIONS"])
def submit_params():
    if request.method == "OPTIONS":
        return ("", 204)
    d = request.json or {}
    cid = d.get("client_id", "anon")
    params = d.get("parameters")
    n = int(d.get("sample_count", 0) or 0)
    if not params or n <= 0:
        return jsonify(accepted=False, error="missing parameters or sample_count"), 400
    if not _valid_weights(params):
        return jsonify(accepted=False, error="malformed parameters"), 400
    n = min(n, MAX_SAMPLE_COUNT)
    with state.lock:
        state.touch(cid)
        c = state.clients[cid]
        c["submits"] += 1
        c["samples"] = n
        state.buffer[cid] = {"w": params, "n": n, "loss": d.get("loss")}
        if len(state.buffer) >= MIN_CLIENTS:
            state.close_round_locked()
        return jsonify(accepted=True, round=state.round)


@app.route("/seed", methods=["POST", "OPTIONS"])
def seed():
    """Give a joining client a stable shard of labelled hits to train on
    locally (real cosmic hits are too rare to capture live at a booth)."""
    if request.method == "OPTIONS":
        return ("", 204)
    d = request.json or {}
    cid = d.get("client_id", "anon")
    n = min(int(d.get("n", SEED_N) or SEED_N), len(state.seed_pool))
    rng = np.random.default_rng(abs(hash(cid)) % (2 ** 32))
    idx = rng.choice(len(state.seed_pool), size=n, replace=False)
    hits = [state.seed_pool[int(i)] for i in idx]
    return jsonify(hits=hits, count=len(hits))


@app.route("/status")
def status():
    now = time.time()
    with state.lock:
        clients = [
            {"client_id": cid, "submits": c["submits"], "samples": c["samples"],
             "active": (now - c["last_seen"]) < CLIENT_STALE_S,
             "sim": cid.startswith("sim-"),
             "age_s": round(now - c["last_seen"], 1)}
            for cid, c in sorted(state.clients.items())
        ]
        latest = state.acc_curve[-1]
        # WAN summary: FL coordination traffic is measured; the "kept on
        # device" figure is a labelled estimate (samples held x median raw
        # detection size) of what centralized raw-data upload would have moved.
        fl_paths = ("/get_global_model", "/submit_params", "/register")
        fl_bytes = sum(e["in"] + e["out"] for p, e in state.wan.items()
                       if p in fl_paths)
        seed_bytes = sum(e["in"] + e["out"] for p, e in state.wan.items()
                         if p == "/seed")
        on_device = sum(c["samples"] for c in state.clients.values()) * RAW_HIT_BYTES
        wan = {
            "fl_update_bytes": fl_bytes,
            "seed_bytes": seed_bytes,
            "kept_on_device_bytes_est": on_device,
            "raw_hit_bytes_assumed": RAW_HIT_BYTES,
            "by_endpoint": state.wan,
        }
        return jsonify(
            wan=wan,
            round=state.round,
            current_accuracy=latest["accuracy"],
            lr=state.lr(),
            n_clients=len(clients),
            n_active=sum(1 for c in clients if c["active"]),
            n_active_real=sum(1 for c in clients if c["active"] and not c["sim"]),
            n_active_sim=sum(1 for c in clients if c["active"] and c["sim"]),
            pending_in_round=len(state.buffer),
            min_clients_per_round=MIN_CLIENTS,
            val_size=int(state.Xval.shape[0]),
            accuracy_curve=state.acc_curve,
            clients=clients,
        )


@app.route("/reset", methods=["POST", "OPTIONS"])
def reset():
    # Demo attract-loop. With FL_ADMIN_TOKEN set (any public deployment),
    # requires a matching bearer token.
    if request.method == "OPTIONS":
        return ("", 204)
    if ADMIN_TOKEN:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {ADMIN_TOKEN}":
            return jsonify(ok=False, error="unauthorized"), 401
    with state.lock:
        state.reset_locked()
    return jsonify(ok=True)


@app.route("/referee")
def referee():
    return jsonify(_referee())


@app.route("/")
def dashboard():
    return send_file(os.path.join(_HERE, "dashboard.html"))


@app.route("/health")
def health():
    return jsonify(ok=True, round=state.round)


def main():
    ap = argparse.ArgumentParser(description="FL server for the SC26 phone demo")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8088)
    args = ap.parse_args()
    threading.Thread(target=_reaper, daemon=True, name="fl-reaper").start()
    app.logger.info(f"[fl] server up on {args.host}:{args.port}, "
                    f"min_clients={MIN_CLIENTS}, timeout={ROUND_TIMEOUT_S}s")
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
