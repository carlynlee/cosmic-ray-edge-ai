# SC26 FL demo — deployment

Two things get deployed: the **FL server** (coordinator + dashboard, new host
`credo-fl.nrp-nautilus.io`) and the **upgraded PWA** (served by the existing
phone-receiver at `credo-phone.nrp-nautilus.io`). All k8s lives in namespace
`cblee-credo`, mirroring the phone-receiver pattern (stock python image, deps
pip-installed at startup, code/data from ConfigMaps).

## 0. Prereqs
- `kubectl` context pointing at Nautilus, access to `cblee-credo`.
- Data files present (regenerate if stale):
  ```
  python -m fldemo.backfill      # -> data/real_train.json, real_val.json
  python -m fldemo.referee       # -> data/referee_summary.json
  ```

## 1. FL server -> credo-fl.nrp-nautilus.io
```
./deploy/08-deploy-fl-server.sh
```
Builds `fl-server-code` + `fl-server-data` ConfigMaps from the real files,
applies `deploy/fl-server-deployment.yaml` (Deployment/Service/Ingress), and
restarts. Verify:
```
curl -s https://credo-fl.nrp-nautilus.io/health      # {"ok":true,...}
open  https://credo-fl.nrp-nautilus.io/              # live dashboard
```
- **DNS/ingress:** the `credo-fl` host must resolve to the Nautilus haproxy the
  same way `credo-phone` does. If it 404s at the ingress, the host/cert isn't
  wired yet — mirror whatever set up `credo-phone`.
- Single replica on purpose: the FL global model is in-memory. Don't scale it.

## 2. Upgraded PWA -> credo-phone.nrp-nautilus.io
The phone-receiver serves the PWA. Its served static set must now include the
new/updated files:
- `static/phone.html`  (real cluster/elongation detector + FL client wiring)
- `static/sw.js`       (**v2** — cache bump; without it phones keep the old code)
- `static/model.js`    (new)
- `static/fl_client.js`(new)

`phone.html` already points `FL_SERVER_URL` at `https://credo-fl.nrp-nautilus.io`.
Update the phone-receiver ConfigMap/static bundle with these four files and roll
it out. (If the receiver serves from a ConfigMap, add `model.js`/`fl_client.js`
as extra keys; if from an image, rebuild.)

## 3. Post-deploy checks
- Dashboard shows rounds/curve/clients + the CosmicWatch referee panel.
- On a real phone: open the PWA, START, confirm the `FL round N · local X%` line
  advances and a new tile appears on the dashboard. (Camera APIs — getUserMedia,
  ImageCapture, wake lock — can only be validated on-device.)
- CORS: the FL server sends `Access-Control-Allow-Origin: *`, so cross-origin
  calls from `credo-phone` -> `credo-fl` work. Confirm no console CORS errors.

## Booth / attract mode
`node fldemo/sim_phones.js https://credo-fl.nrp-nautilus.io 5` runs simulated
phones so the dashboard is alive before/without a crowd. It also POSTs `/reset`
every ~75s to replay the climb.

## Caveats
- `/reset` requires `Authorization: Bearer $FL_ADMIN_TOKEN` when the env var is
  set — **change the placeholder token in `deploy/fl-server-deployment.yaml`
  before deploying**. `sim_phones.js` reads the same var from its environment.
- Client submissions are validated (shape / finite / bounded, sample_count
  capped) so a malformed or hostile BYOD submit can't poison FedAvg.
- Simulated clients (`sim-*` ids) are flagged in `/status` and badged "SIM" on
  the dashboard; the Active Phones KPI counts real phones separately.
- `data/real_train.json` is the only surviving copy of some phone hits' features
  (re-extracted from ES image crops) — keep it in git.
