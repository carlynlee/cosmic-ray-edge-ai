#!/usr/bin/env python3
"""Conformance test for the model.py <-> model.js wire contract.

The FL server averages weights trained in browsers (model.js) with weights
from the NumPy reference (model.py); silent numerical divergence between the
two would corrupt FedAvg without failing loudly. This test drives both
implementations with identical inputs and asserts machine-precision agreement
on features, weak labels, forward pass, and a 3-epoch training trajectory.

Requires node on PATH (the JS side runs static/model.js under Node).

Usage:
    python -m fldemo.test_parity
"""
import json
import os
import random
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fldemo import model  # noqa: E402

# A few ULPs on doubles. Weights agree to ~1e-18; forward pass and loss are
# the loosest stages at 1-5 ULPs (~1e-16 absolute on O(1) values).
TOL = 1e-15

JS_DRIVER = r"""
const fs = require("fs");
const M = require(process.argv[2]);
const py = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));

const maxdiff = (a, b) => {
  const fa = a.flat(9), fb = b.flat(9);
  let m = 0;
  for (let i = 0; i < fa.length; i++) m = Math.max(m, Math.abs(fa[i] - fb[i]));
  return m;
};

const out = {};
out.features = maxdiff(py.hits.map(M.extractFeatures), py.X);
out.labels_equal = JSON.stringify(py.hits.map(M.weakLabel)) === JSON.stringify(py.y);
out.forward0 = maxdiff(M.forward(py.w0, py.X), py.probs0);

let w = py.w0;
out.epochs = [];
for (let e = 0; e < py.traj.length; e++) {
  const r = M.trainLocal(w, py.X, py.y, 1, 0.1);
  w = r.weights;
  const pw = py.traj[e].weights;
  out.epochs.push({
    weights: Math.max(maxdiff(w.W1, pw.W1), maxdiff(w.b1, pw.b1),
                      maxdiff(w.W2, pw.W2), maxdiff(w.b2, pw.b2)),
    loss: Math.abs(r.loss - py.traj[e].loss),
  });
}
out.forward_final = maxdiff(M.forward(w, py.X), py.probs_after);
console.log(JSON.stringify(out));
"""


def make_reference(n=200, seed=42):
    rng = random.Random(seed)
    hits = [{"brightness": rng.randint(0, 255),
             "cluster_size": rng.randint(0, 60),
             "elongation": round(rng.uniform(1.0, 12.0), 6)} for _ in range(n)]
    X = [model.extract_features(h) for h in hits]
    y = [model.weak_label(h) for h in hits]
    w0 = model.init_weights(seed=0)
    probs0 = model.forward(w0, X).tolist()
    traj, w = [], w0
    for _ in range(3):
        w, loss = model.train_local(w, X, y, epochs=1, lr=0.1)
        traj.append({"weights": w, "loss": loss})
    probs_after = model.forward(traj[-1]["weights"], X).tolist()
    return {"hits": hits, "X": X, "y": y, "w0": w0, "probs0": probs0,
            "traj": traj, "probs_after": probs_after}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    model_js = os.path.join(here, "..", "static", "model.js")
    ref = make_reference()

    with tempfile.TemporaryDirectory() as td:
        ref_path = os.path.join(td, "ref.json")
        drv_path = os.path.join(td, "driver.js")
        with open(ref_path, "w") as f:
            json.dump(ref, f)
        with open(drv_path, "w") as f:
            f.write(JS_DRIVER)
        res = json.loads(subprocess.check_output(
            ["node", drv_path, model_js, ref_path], text=True))

    failures = []

    def check(name, val, ok):
        status = "ok" if ok else "FAIL"
        print(f"  {name:<28} {val!r:<26} [{status}]")
        if not ok:
            failures.append(name)

    print("model.py <-> model.js parity (max abs diff, tolerance %g):" % TOL)
    check("features", res["features"], res["features"] <= TOL)
    check("weak labels", res["labels_equal"], res["labels_equal"] is True)
    check("forward (init weights)", res["forward0"], res["forward0"] <= TOL)
    for i, e in enumerate(res["epochs"], 1):
        check(f"epoch {i} weights", e["weights"], e["weights"] <= TOL)
        check(f"epoch {i} loss", e["loss"], e["loss"] <= TOL)
    check("forward (trained weights)", res["forward_final"],
          res["forward_final"] <= TOL)

    if failures:
        print("PARITY FAILURE:", ", ".join(failures))
        sys.exit(1)
    print("PARITY OK")


if __name__ == "__main__":
    main()
