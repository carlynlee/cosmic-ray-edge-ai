// In-browser federated-learning client. Each phone: registers, fetches a seed
// shard of labelled hits, then loops { pull global model -> train locally with
// CosmicModel -> submit weights }. Raw images never leave the phone — only the
// tiny weight vector. Live camera detections can be folded into the local set
// via opts.getLiveHits.
//
// UMD: window.CosmicFL in the browser; module.exports in Node (for testing the
// real client loop headlessly against the server).
(function (root) {
  "use strict";
  var Model = (typeof module !== "undefined" && module.exports)
    ? require("./model.js") : root.CosmicModel;
  var doFetch = (typeof fetch !== "undefined") ? fetch : null;

  async function post(base, path, body) {
    var r = await doFetch(base + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    if (!r.ok) throw new Error(path + " -> " + r.status);
    return r.json();
  }

  async function register(base, id) { return post(base, "/register", { client_id: id }); }

  async function fetchSeed(base, id, n) {
    var d = await post(base, "/seed", { client_id: id, n: n });
    return d.hits || [];
  }

  // One FL round: pull global -> local train -> submit. Returns {round, loss, acc}.
  async function trainRound(base, id, X, y) {
    var g = await post(base, "/get_global_model", { client_id: id });
    var res = Model.trainLocal(g.parameters, X, y, g.local_epochs, g.lr);
    await post(base, "/submit_params", {
      client_id: id, parameters: res.weights, sample_count: y.length,
      loss: res.loss, round: g.round,
    });
    return { round: g.round, loss: res.loss, acc: Model.accuracy(res.weights, X, y) };
  }

  function hitsToXY(hits) {
    var X = [], y = [];
    for (var i = 0; i < hits.length; i++) {
      X.push(Model.extractFeatures(hits[i]));
      y.push(hits[i].label != null ? hits[i].label : Model.weakLabel(hits[i]));
    }
    return { X: X, y: y };
  }

  // Run the FL loop. opts: {base, clientId, rounds, intervalMs, seedN,
  // onStatus, getLiveHits, shouldStop}. Returns after `rounds` (or forever if
  // rounds is falsy and shouldStop drives it).
  async function startFL(opts) {
    var id = opts.clientId;
    await register(opts.base, id);
    var hits = await fetchSeed(opts.base, id, opts.seedN || 120);
    var r = 0;
    while (!(opts.shouldStop && opts.shouldStop()) &&
           (!opts.rounds || r < opts.rounds)) {
      var live = opts.getLiveHits ? opts.getLiveHits() : null;
      var all = live && live.length ? hits.concat(live) : hits;
      var xy = hitsToXY(all);
      var info;
      try {
        info = await trainRound(opts.base, id, xy.X, xy.y);
      } catch (e) {
        if (opts.onStatus) opts.onStatus({ error: String(e) });
        await sleep(opts.intervalMs || 1500);
        continue;
      }
      r++;
      if (opts.onStatus) opts.onStatus({ round: info.round, localAcc: info.acc,
                                         localLoss: info.loss, samples: all.length });
      if (opts.rounds && r >= opts.rounds) break;
      await sleep(opts.intervalMs || 1500);
    }
    return r;
  }

  function sleep(ms) { return new Promise(function (res) { setTimeout(res, ms); }); }

  var FL = { register: register, fetchSeed: fetchSeed, trainRound: trainRound,
             hitsToXY: hitsToXY, startFL: startFL };
  if (typeof module !== "undefined" && module.exports) module.exports = FL;
  else root.CosmicFL = FL;
})(typeof self !== "undefined" ? self : this);
