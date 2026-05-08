# CosmicPhysicist

Edge LLM system for real-time cosmic ray muon detection and physics interpretation. Runs fully offline on a Raspberry Pi 5 connected to a CosmicWatch Desktop Muon Detector v3X, with an iPhone PWA for monitoring and a second-detector camera hit detector.

## Architecture

```
CosmicWatch (USB /dev/ttyACM1)
        |
   cosmic_bridge.py          reads serial, POSTs events to server
        |
   server.py                 Flask API + SQLite + SSE broadcast
        |-- Ollama (CosmicPhysicist model, Qwen 2.5 3B)
        |-- correlation engine (±5s window, CW ↔ iPhone)
        |
   http://<PI_IP_ADDRESS>:5000  iPhone Safari web UI + camera detector
```

## Hardware

- Raspberry Pi 5 (8GB), Debian 13, at `<PI_IP_ADDRESS>`
- CosmicWatch Desktop Muon Detector v3X on `/dev/ttyACM1`
- iPhone (Safari PWA — live feed + camera particle detector)

## Services (all auto-start on boot)

| Service | Description |
|---|---|
| `ollama` | LLM inference (Qwen 2.5 3B) |
| `cosmic-server` | Flask web server on port 5000 |
| `cosmic-bridge` | CosmicWatch serial reader |

```bash
# Check status
sudo systemctl status cosmic-server cosmic-bridge ollama

# View logs
sudo journalctl -u cosmic-server -f
sudo journalctl -u cosmic-bridge -f
```

## Files on Pi

```
/home/pi/cosmic_server/
├── server.py           Flask API, SSE, SQLite, LLM, correlator
├── cosmic.db           SQLite database (events persist here)
└── static/
    ├── index.html      iPhone PWA
    ├── sw.js           Service worker
    └── manifest.json   PWA manifest
/home/pi/cosmic_bridge.py     Serial bridge
/home/pi/CosmicPhysicist.Modelfile  Ollama model definition
/home/pi/cosmic_env/          Python venv (flask, pyserial, requests)
```

## Deploying changes

Edit files locally in this directory, then sync to Pi:

```bash
scp cosmicphysicist/server.py pi@<PI_IP_ADDRESS>:/home/pi/cosmic_server/server.py
scp cosmicphysicist/static/index.html pi@<PI_IP_ADDRESS>:/home/pi/cosmic_server/static/index.html
scp cosmicphysicist/cosmic_bridge.py pi@<PI_IP_ADDRESS>:/home/pi/cosmic_bridge.py
sudo systemctl restart cosmic-server cosmic-bridge
```

To update the LLM system prompt:
```bash
scp cosmicphysicist/CosmicPhysicist.Modelfile pi@<PI_IP_ADDRESS>:/home/pi/CosmicPhysicist.Modelfile
ssh pi@<PI_IP_ADDRESS> "ollama create CosmicPhysicist -f /home/pi/CosmicPhysicist.Modelfile"
```

## iPhone camera detector

The PWA at `http://<PI_IP_ADDRESS>:5000` includes a camera-based particle detector. Safari on iOS requires HTTPS for camera access — if the Start button fails, add SSL:

```bash
ssh pi@<PI_IP_ADDRESS>
openssl req -x509 -newkey rsa:2048 -keyout /home/pi/cosmic_server/key.pem \
  -out /home/pi/cosmic_server/cert.pem -days 365 -nodes \
  -subj "/CN=<PI_IP_ADDRESS>" -addext "subjectAltName=IP:<PI_IP_ADDRESS>"
```

Then update the last line of `server.py`:
```python
app.run(host="0.0.0.0", port=5000, threaded=True,
        ssl_context=("cert.pem", "key.pem"))
```

Visit `https://<PI_IP_ADDRESS>:5000`, accept the certificate warning, and camera access will work.

## What the LLM knows

`CosmicPhysicist.Modelfile` gives the model a system prompt covering:
- CosmicWatch data schema and observed baseline statistics (ADC ranges, coincidence rate 12.3%, pressure baseline)
- Cosmic ray muon physics, SiPM operation, coincidence detection
- How to interpret individual events and correlated detections

## Next steps

- [ ] Add SSL for iPhone camera detector
- [ ] Load CREDO historical dataset (69K detections in `../credo-data-export/`) into LLM context as RAG
- [ ] Add rate monitoring — alert when detection rate deviates significantly from baseline
