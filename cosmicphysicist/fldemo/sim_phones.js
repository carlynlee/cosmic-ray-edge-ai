// Continuous phone simulator — drives the FL server so the dashboard is live
// without physical phones. Useful as booth "attract mode" and for local viewing.
// Each simulated phone runs the REAL client loop (model.js + fl_client.js).
//
//   node fldemo/sim_phones.js [baseURL] [numPhones]
//
// Periodically POSTs /reset so the accuracy curve replays the climb on a loop.
const path = require("path");
const FL = require(path.join(__dirname, "..", "static", "fl_client.js"));

const BASE = process.argv[2] || "http://localhost:8088";
const N = parseInt(process.argv[3] || "5", 10);
const ADMIN_TOKEN = process.env.FL_ADMIN_TOKEN || "";  // needed for /reset if server sets it
const RESET_EVERY_MS = 75000;

console.log(`sim_phones: ${N} phones -> ${BASE}`);

for (let i = 0; i < N; i++) {
  setTimeout(() => {
    FL.startFL({
      base: BASE, clientId: "sim-phone-" + i, intervalMs: 1800, seedN: 150,
      shouldStop: () => false,   // run forever
      onStatus: s => { if (i === 0 && s.round % 5 === 0)
        console.log(`  round ${s.round} localAcc=${(s.localAcc || 0).toFixed(2)}`); },
    }).catch(e => console.log("phone " + i + " stopped:", String(e)));
  }, i * 400);  // stagger joins so tiles appear over time
}

// Attract loop: replay the climb periodically.
setInterval(async () => {
  try {
    const headers = ADMIN_TOKEN ? { Authorization: "Bearer " + ADMIN_TOKEN } : {};
    const r = await fetch(BASE + "/reset", { method: "POST", headers });
    console.log(r.ok ? "  [reset] replaying climb" : "  [reset] rejected: " + r.status);
  } catch (e) {}
}, RESET_EVERY_MS);
