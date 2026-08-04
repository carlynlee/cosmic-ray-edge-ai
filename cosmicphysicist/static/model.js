// Shared model — JavaScript port of fldemo/model.py. MUST stay numerically
// identical to the Python reference: the FL server averages weights trained
// here (in the browser) with weights from other clients, so divergence between
// this and model.py would corrupt FedAvg. Verified against model.py in Node.
//
// Loads in the browser (window.CosmicModel) and in Node (module.exports).
(function (root) {
  "use strict";

  // --- contract constants (must match model.py) ---
  var LEAK = 0.01;
  var BRIGHT_SCALE = 5.55;
  var CLUSTER_SCALE = 8.6;
  var ELONG_CAP = 10.0;
  var IN_DIM = 3, HIDDEN = 8;

  function log1p(x) { return Math.log(1 + x); }

  function extractFeatures(hit) {
    var brightness = +(hit.brightness || 0);
    var cluster = +(hit.cluster_size || 0);
    var elong = +(hit.elongation || 1.0);
    return [
      log1p(brightness) / BRIGHT_SCALE,
      log1p(cluster) / CLUSTER_SCALE,
      Math.min(elong, ELONG_CAP) / ELONG_CAP,
    ];
  }

  function weakLabel(hit) {
    var cluster = +(hit.cluster_size || 0);
    var brightness = +(hit.brightness || 0);
    if (cluster <= 1 || cluster >= 50) return 0;
    if (cluster >= 2 && cluster <= 25 && brightness >= 20) return 1;
    return 0;
  }

  function sigmoid(z) {
    if (z < -30) z = -30; else if (z > 30) z = 30;
    return 1 / (1 + Math.exp(-z));
  }

  // Forward pass for one feature vector -> probability. (OUT_DIM == 1.)
  function forwardOne(w, x) {
    var H = w.b1.length, h = new Array(H);
    for (var j = 0; j < H; j++) {
      var z = w.b1[j];
      for (var k = 0; k < x.length; k++) z += w.W1[j][k] * x[k];
      h[j] = z > 0 ? z : LEAK * z;
    }
    var logit = w.b2[0];
    for (var m = 0; m < H; m++) logit += w.W2[0][m] * h[m];
    return sigmoid(logit);
  }

  // Probabilities for an array of feature vectors.
  function forward(w, X) { return X.map(function (x) { return forwardOne(w, x); }); }

  function bce(y, p) {
    var eps = 1e-7, s = 0;
    for (var i = 0; i < y.length; i++) {
      var pi = Math.min(1 - eps, Math.max(eps, p[i]));
      s += -(y[i] * Math.log(pi) + (1 - y[i]) * Math.log(1 - pi));
    }
    return s / y.length;
  }

  // Full-batch gradient descent on BCE — mirrors model.py train_local exactly
  // (same mean-gradient, leaky-ReLU grad, update order). Returns {weights,loss}.
  function trainLocal(w0, X, y, epochs, lr) {
    var H = w0.b1.length, IN = w0.W1[0].length, n = Math.max(1, X.length);
    // deep copy weights so we don't mutate the caller's global model
    var W1 = w0.W1.map(function (r) { return r.slice(); });
    var b1 = w0.b1.slice();
    var W2 = [w0.W2[0].slice()];
    var b2 = w0.b2.slice();
    var loss = 0;
    for (var e = 0; e < epochs; e++) {
      var dW1 = [], db1 = new Array(H).fill(0);
      for (var j = 0; j < H; j++) dW1.push(new Array(IN).fill(0));
      var dW2 = new Array(H).fill(0), db2 = 0;
      var p = new Array(n);
      for (var i = 0; i < n; i++) {
        var x = X[i];
        var z1 = new Array(H), hh = new Array(H);
        for (var a = 0; a < H; a++) {
          var z = b1[a];
          for (var c = 0; c < IN; c++) z += W1[a][c] * x[c];
          z1[a] = z; hh[a] = z > 0 ? z : LEAK * z;
        }
        var logit = b2[0];
        for (var b = 0; b < H; b++) logit += W2[0][b] * hh[b];
        var pi = sigmoid(logit); p[i] = pi;
        var dz2 = (pi - y[i]) / n;                 // (p - y)/n
        db2 += dz2;
        for (var d = 0; d < H; d++) {
          dW2[d] += dz2 * hh[d];
          var dz1 = dz2 * W2[0][d] * (z1[d] > 0 ? 1 : LEAK);
          for (var f = 0; f < IN; f++) dW1[d][f] += dz1 * x[f];
          db1[d] += dz1;
        }
      }
      loss = bce(y, p);
      for (var q = 0; q < H; q++) {
        W2[0][q] -= lr * dW2[q];
        b1[q] -= lr * db1[q];
        for (var r2 = 0; r2 < IN; r2++) W1[q][r2] -= lr * dW1[q][r2];
      }
      b2[0] -= lr * db2;
    }
    return { weights: { arch: w0.arch, W1: W1, b1: b1, W2: W2, b2: b2 }, loss: loss };
  }

  function accuracy(w, X, y) {
    var p = forward(w, X), c = 0;
    for (var i = 0; i < y.length; i++) if ((p[i] >= 0.5 ? 1 : 0) === y[i]) c++;
    return c / y.length;
  }

  var Model = {
    LEAK: LEAK, IN_DIM: IN_DIM, HIDDEN: HIDDEN,
    extractFeatures: extractFeatures, weakLabel: weakLabel,
    forward: forward, forwardOne: forwardOne, trainLocal: trainLocal,
    accuracy: accuracy,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = Model;
  else root.CosmicModel = Model;
})(typeof self !== "undefined" ? self : this);
