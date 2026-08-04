#!/usr/bin/env python3
"""
Mode A vs Mode B WAN measurement campaign (INDIS 2026 paper, §5).

Question: for the same real workload, model, and accuracy target, how many
bytes cross the WAN under
  Mode A (centralized): every client uploads its raw detections once; training
      happens centrally. Bytes = sum of real detection wire sizes, drawn from
      the empirical distribution of actual ES phone-camera docs (with images).
  Mode B (federated):  raw data never moves; clients train locally and exchange
      weights with the coordinator. Bytes = the coordinator's own HTTP byte
      accounting (request+response bodies on /register, /get_global_model,
      /submit_params) — the same counters the live dashboard shows.

Method notes (paper honesty):
- One fresh fl_server subprocess per config (FL_MIN_CLIENTS = K so a round
  aggregates all K clients). Clients run in-driver with model.train_local —
  numerically identical to the browser client (model.js parity ≤1e-16).
- Client shards are drawn from the real backfilled dataset (real_train.json);
  K*S may exceed the pool, in which case shards are bootstrap-sampled (noted).
- Stop when server-side validation accuracy (real_val.json) >= TARGET_ACC, or
  MAX_ROUNDS. Mode A trains the same model centrally on the pooled shards to
  confirm it reaches the same target (its WAN bytes don't depend on training).
- Seed-shard traffic is a demo-bootstrap artifact (real phones own their data)
  and is NOT part of Mode B bytes; reported separately by the live demo.

Usage:
    python -m fldemo.experiment_modes [--target-acc 0.95] [--out data/modeAB.json]
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time

import numpy as np
import requests

from . import model as M

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "data")
TARGET_ACC = 0.95
MAX_ROUNDS = 40
CONFIGS = [  # (K clients, S samples per client)
    (5, 150), (10, 150), (25, 150),   # scale clients
    (10, 50), (10, 450),              # scale per-client data volume
]


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _start_server(k, port):
    env = os.environ.copy()
    env.update({
        "FL_MIN_CLIENTS": str(k),
        "FL_VAL_PATH": os.path.join(DATA, "real_val.json"),
        "FL_SEED_PATH": os.path.join(DATA, "real_train.json"),
        "FL_ROUND_TIMEOUT_S": "3600",   # rounds close only on K submissions
    })
    proc = subprocess.Popen(
        [sys.executable, "-m", "fldemo.fl_server", "--port", str(port)],
        cwd=os.path.dirname(HERE), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            requests.get(base + "/health", timeout=2)
            return proc, base
        except Exception:
            time.sleep(0.5)
    proc.kill()
    raise RuntimeError("fl_server did not come up")


def _shards(train_hits, k, s, rng):
    """K shards of S real hits each; bootstrap if K*S exceeds the pool."""
    n = len(train_hits)
    replace = k * s > n
    shards = []
    for _ in range(k):
        idx = rng.choice(n, size=s, replace=replace)
        hits = [train_hits[int(i)] for i in idx]
        X = np.array([M.extract_features(h) for h in hits])
        y = np.array([float(h["label"]) for h in hits])
        shards.append((X, y))
    return shards, replace


def run_mode_b(k, s, train_hits, rng):
    """Federated: real HTTP against a fresh server; bytes from its counters."""
    port = _free_port()
    proc, base = _start_server(k, port)
    try:
        shards, bootstrap = _shards(train_hits, k, s, rng)
        cids = [f"c{k}x{s}-{i}" for i in range(k)]
        for cid in cids:
            requests.post(base + "/register", json={"client_id": cid}, timeout=10)

        rounds = 0
        acc = 0.0
        curve = []
        while rounds < MAX_ROUNDS:
            for cid, (X, y) in zip(cids, shards):
                g = requests.post(base + "/get_global_model",
                                  json={"client_id": cid}, timeout=10).json()
                w, loss = M.train_local(g["parameters"], X, y,
                                        epochs=g["local_epochs"], lr=g["lr"])
                requests.post(base + "/submit_params",
                              json={"client_id": cid, "parameters": w,
                                    "sample_count": len(y), "loss": loss,
                                    "round": g["round"]}, timeout=10)
            st = requests.get(base + "/status", timeout=10).json()
            rounds = st["round"]
            acc = st["current_accuracy"]
            curve.append({"round": rounds, "accuracy": acc,
                          "fl_bytes": st["wan"]["fl_update_bytes"]})
            if acc >= TARGET_ACC:
                break
        st = requests.get(base + "/status", timeout=10).json()
        return {
            "rounds": rounds, "final_acc": acc,
            "fl_bytes": st["wan"]["fl_update_bytes"],
            "by_endpoint": st["wan"]["by_endpoint"],
            "curve": curve, "bootstrap_shards": bootstrap,
            "reached_target": acc >= TARGET_ACC,
        }
    finally:
        proc.kill()


def run_mode_a(k, s, train_hits, doc_sizes, rng):
    """Centralized: bytes = one-time upload of each client's raw detections
    (sizes drawn from the real ES doc-size distribution); central training on
    the pooled data confirms accuracy parity."""
    shards, bootstrap = _shards(train_hits, k, s, rng)
    upload = int(rng.choice(doc_sizes, size=k * s, replace=True).sum())

    Xp = np.vstack([X for X, _ in shards])
    yp = np.concatenate([y for _, y in shards])
    val = json.load(open(os.path.join(DATA, "real_val.json")))
    Xv = np.array([M.extract_features(h) for h in val])
    yv = np.array([float(h["label"]) for h in val])
    w = M.init_weights(0)
    acc, epochs = 0.0, 0
    while epochs < 2000 and acc < TARGET_ACC:
        w, _ = M.train_local(w, Xp, yp, epochs=50, lr=0.5)
        epochs += 50
        acc = M.accuracy(w, Xv, yv)
    return {"upload_bytes": upload, "central_epochs": epochs,
            "final_acc": acc, "reached_target": acc >= TARGET_ACC,
            "bootstrap_shards": bootstrap}


def main():
    ap = argparse.ArgumentParser(description="Mode A vs B WAN measurement")
    ap.add_argument("--target-acc", type=float, default=TARGET_ACC)
    ap.add_argument("--out", default=os.path.join(DATA, "modeAB_results.json"))
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    globals()["TARGET_ACC"] = args.target_acc

    train_hits = json.load(open(os.path.join(DATA, "real_train.json")))
    ds = json.load(open(os.path.join(DATA, "raw_doc_sizes.json")))
    doc_sizes = np.array(ds["sizes_bytes"])
    print(f"pool: {len(train_hits)} real hits | doc-size dist: n={ds['n']}, "
          f"median={np.median(doc_sizes):.0f}B | target acc {args.target_acc}")

    results = []
    for k, s in CONFIGS:
        rng = np.random.default_rng(args.seed)
        b = run_mode_b(k, s, train_hits, rng)
        rng = np.random.default_rng(args.seed)   # same shards for A
        a = run_mode_a(k, s, train_hits, doc_sizes, rng)
        ratio = a["upload_bytes"] / b["fl_bytes"] if b["fl_bytes"] else None
        row = {"K": k, "S": s, "modeA": a, "modeB": b, "reduction_x": ratio}
        results.append(row)
        print(f"K={k:>2} S={s:>3} | A: {a['upload_bytes']/1024:7.1f} KB "
              f"(acc {a['final_acc']:.3f}) | B: {b['fl_bytes']/1024:7.1f} KB "
              f"in {b['rounds']:>2} rounds (acc {b['final_acc']:.3f}) "
              f"| reduction {ratio:5.1f}x")

    out = {"target_acc": args.target_acc, "max_rounds": MAX_ROUNDS,
           "seed": args.seed, "doc_size_dist_n": ds["n"],
           "generated_note": "bytes exclude HTTP headers on both modes; "
                             "Mode B excludes demo seed bootstrap",
           "results": results}
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
