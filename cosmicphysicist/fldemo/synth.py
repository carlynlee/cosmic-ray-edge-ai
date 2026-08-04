#!/usr/bin/env python3
"""
Synthetic phone-hit generator — a stand-in for real ES data used by the FL
server's fallback validation set and by tests. Produces hits in the same shape
as phone-camera docs (brightness, cluster_size, hit_x/y, frame_width/height).

Real cosmic tracks: compact, mid brightness, away from frame edges.
Noise: single hot pixels (cluster 1), whole-frame light leaks (huge cluster),
and edge artifacts (hot columns / vignetting).
"""

import numpy as np

FRAME_W, FRAME_H = 480, 640


def make_hits(n, seed=0):
    """Return a list of ~n hit dicts, roughly balanced real/noise."""
    rng = np.random.default_rng(seed)
    hits = []
    for _ in range(n // 2):
        hits.append(dict(
            brightness=float(rng.uniform(40, 150)),
            cluster_size=int(rng.integers(2, 40)),
            frame_width=FRAME_W, frame_height=FRAME_H,
            hit_x=float(rng.uniform(0.25, 0.75) * FRAME_W),
            hit_y=float(rng.uniform(0.25, 0.75) * FRAME_H),
        ))
    for _ in range(n - n // 2):
        kind = int(rng.integers(0, 3))
        if kind == 0:      # hot pixel
            cs, bx, hx, hy = 1, rng.uniform(30, 255), rng.uniform(0, FRAME_W), rng.uniform(0, FRAME_H)
        elif kind == 1:    # light leak / whole frame
            cs, bx, hx, hy = int(rng.integers(300, 2000)), rng.uniform(100, 255), FRAME_W / 2, FRAME_H / 2
        else:              # edge artifact
            cs, bx = int(rng.integers(2, 40)), rng.uniform(40, 150)
            hx, hy = float(rng.choice([5, FRAME_W - 5])), float(rng.uniform(0, FRAME_H))
        hits.append(dict(brightness=float(bx), cluster_size=cs,
                         frame_width=FRAME_W, frame_height=FRAME_H,
                         hit_x=float(hx), hit_y=float(hy)))
    perm = rng.permutation(len(hits))
    return [hits[i] for i in perm]
