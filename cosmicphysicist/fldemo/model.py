#!/usr/bin/env python3
"""
Shared model CONTRACT for the SC26 federated-learning demo.

This is the single source of truth that the browser client (model.js) and the
FL server (fl_server.py) must agree on byte-for-byte. Keep model.js in lockstep
with this file — the feature extraction, the MLP forward pass, and the weight
JSON layout are all part of the wire contract.

Task: classify a phone-camera candidate hit as a real cosmic-ray track (1) vs a
sensor artifact / noise (0). The model is deliberately tiny (3->6->1, ~31
params) so it trains with hand-rolled SGD in JavaScript on the phone and its
weights are a few hundred bytes to ship over the wire.

Federated learning: every phone trains THIS model locally on its own seeded
hits and submits only the weights. The server FedAvg-averages them. CosmicWatch
independently validates the aggregate rate (it is the referee, not a client).
"""

import numpy as np

# --- feature contract --------------------------------------------------------
# Features are derived from fields present on phone-camera docs (see ES schema):
# brightness, cluster_size, hit_x, hit_y, frame_width, frame_height.
FEATURE_NAMES = ["log_brightness", "log_cluster", "elongation"]
IN_DIM = len(FEATURE_NAMES)
HIDDEN = 8
OUT_DIM = 1
# Leaky-ReLU slope. Leaky (not plain ReLU) so a tiny net can't get stuck with
# dead units on an unlucky init — critical for reliable convergence on stage.
LEAK = 0.01

# Fixed normalization scales (part of the contract — must match model.js).
_BRIGHT_SCALE = 5.55   # log1p(255)
_CLUSTER_SCALE = 8.6   # ~log1p(5000)
_ELONG_CAP = 10.0      # bounding-box aspect ratio, clamped


def extract_features(hit):
    """Map a hit dict -> normalized feature list [log_brightness, log_cluster,
    elongation]. All three come straight from the cluster extraction, so any
    pixel patch (a real detection OR a background sample) has them well-defined.
    A single hot pixel is cluster 1 / elong 1; a cosmic track is a compact
    multi-pixel, often elongated, cluster; a light leak is a huge cluster."""
    brightness = float(hit.get("brightness", 0) or 0)
    cluster = float(hit.get("cluster_size", 0) or 0)
    elong = float(hit.get("elongation", 1.0) or 1.0)
    return [
        np.log1p(brightness) / _BRIGHT_SCALE,
        np.log1p(cluster) / _CLUSTER_SCALE,
        min(elong, _ELONG_CAP) / _ELONG_CAP,
    ]


def weak_label(hit):
    """Heuristic weak label used to seed local training. NOT ground truth —
    it encodes the obvious artifact rules (single hot pixels, whole-frame light
    leaks) so the federated model can learn and smooth the boundary;
    CosmicWatch validates the result in aggregate.

    Returns 1 (likely real cosmic cluster) or 0 (likely noise/artifact)."""
    brightness = float(hit.get("brightness", 0) or 0)
    cluster = float(hit.get("cluster_size", 0) or 0)
    if cluster <= 1 or cluster >= 50:
        return 0
    if 2 <= cluster <= 25 and brightness >= 20:
        return 1
    return 0


# --- weights (JSON-serializable dict; the wire format) -----------------------
def init_weights(seed=0):
    """Small random init. Layout is the contract shared with model.js."""
    rng = np.random.default_rng(seed)
    scale_in = np.sqrt(2.0 / IN_DIM)   # He init for (leaky) ReLU
    scale_h = np.sqrt(2.0 / HIDDEN)
    return {
        "arch": {"in": IN_DIM, "hidden": HIDDEN, "out": OUT_DIM},
        "W1": (rng.standard_normal((HIDDEN, IN_DIM)) * scale_in).tolist(),
        "b1": [0.0] * HIDDEN,
        "W2": (rng.standard_normal((OUT_DIM, HIDDEN)) * scale_h).tolist(),
        "b2": [0.0] * OUT_DIM,
    }


def _unpack(weights):
    return (np.array(weights["W1"]), np.array(weights["b1"]),
            np.array(weights["W2"]), np.array(weights["b2"]))


def forward(weights, X):
    """Forward pass. X: (N, IN_DIM) array. Returns (N,) probabilities.
    h = relu(W1 x + b1); y = sigmoid(W2 h + b2). Mirror exactly in model.js."""
    W1, b1, W2, b2 = _unpack(weights)
    X = np.atleast_2d(np.asarray(X, dtype=np.float64))
    z1 = X @ W1.T + b1
    h = np.where(z1 > 0, z1, LEAK * z1)          # leaky ReLU, (N, HIDDEN)
    logits = h @ W2.T + b2                        # (N, OUT_DIM)
    return _sigmoid(logits[:, 0])


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def train_local(weights, X, y, epochs=5, lr=0.1):
    """One client's local training: plain full-batch SGD on BCE loss. Returns
    (new_weights, final_loss). This is the reference; model.js implements the
    same update so submitted weights are comparable across clients."""
    W1, b1, W2, b2 = _unpack(weights)
    X = np.atleast_2d(np.asarray(X, dtype=np.float64))
    y = np.asarray(y, dtype=np.float64)
    n = max(1, X.shape[0])
    loss = None
    for _ in range(epochs):
        z1 = X @ W1.T + b1
        h = np.where(z1 > 0, z1, LEAK * z1)             # leaky ReLU
        p = _sigmoid((h @ W2.T + b2)[:, 0])
        loss = _bce(y, p)
        # gradients
        dz2 = (p - y)[:, None] / n                      # (N,1)
        dW2 = dz2.T @ h                                 # (1,HIDDEN)
        db2 = dz2.sum(axis=0)                            # (1,)
        dh = dz2 @ W2                                    # (N,HIDDEN)
        dz1 = dh * np.where(z1 > 0, 1.0, LEAK)          # leaky ReLU grad
        dW1 = dz1.T @ X                                  # (HIDDEN,IN)
        db1 = dz1.sum(axis=0)
        W2 = W2 - lr * dW2
        b2 = b2 - lr * db2
        W1 = W1 - lr * dW1
        b1 = b1 - lr * db1
    return ({"arch": weights["arch"], "W1": W1.tolist(), "b1": b1.tolist(),
             "W2": W2.tolist(), "b2": b2.tolist()}, float(loss))


def _bce(y, p):
    eps = 1e-7
    p = np.clip(p, eps, 1 - eps)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def accuracy(weights, X, y):
    p = forward(weights, X)
    return float(np.mean((p >= 0.5).astype(float) == np.asarray(y)))


def fedavg(weight_list, sample_counts):
    """Weighted average of client weights (FedAvg). weight_list: list of weight
    dicts; sample_counts: matching client sample sizes."""
    counts = np.asarray(sample_counts, dtype=np.float64)
    total = counts.sum()
    if total <= 0:
        return weight_list[0]
    w = counts / total
    out = {"arch": weight_list[0]["arch"]}
    for key in ("W1", "b1", "W2", "b2"):
        acc = None
        for wi, cw in zip(w, weight_list):
            arr = np.array(cw[key]) * wi
            acc = arr if acc is None else acc + arr
        out[key] = acc.tolist()
    return out
