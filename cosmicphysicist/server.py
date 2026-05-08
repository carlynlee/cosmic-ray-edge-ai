#!/usr/bin/env python3
"""
CosmicPhysicist server — aggregates CosmicWatch + iPhone detections,
correlates them, queries the LLM, and streams results to the web UI.
"""

import json
import os
import queue
import sqlite3
import threading
import time

import requests
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

DB_PATH = "/home/pi/cosmic_server/cosmic.db"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "CosmicPhysicist"
CORRELATION_WINDOW_S = 5.0

sse_clients = []
sse_lock = threading.Lock()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cosmicwatch_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_num INTEGER,
            timestamp_s REAL,
            wall_time REAL,
            adc_value INTEGER,
            sipm_mv REAL,
            coincidence_flag INTEGER,
            temperature_c REAL,
            pressure_pa REAL,
            deadtime_s REAL,
            accel_x REAL, accel_y REAL, accel_z REAL,
            gyro_x REAL, gyro_y REAL, gyro_z REAL,
            detector TEXT,
            llm_interpretation TEXT,
            correlated_iphone_id INTEGER
        );
        CREATE TABLE IF NOT EXISTS iphone_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wall_time REAL,
            brightness REAL,
            cluster_size INTEGER,
            llm_interpretation TEXT,
            correlated_cw_id INTEGER
        );
    """)
    conn.commit()
    conn.close()


def broadcast(event_type, data):
    msg = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    with sse_lock:
        for q in list(sse_clients):
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass


def ask_llm(prompt):
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=180,
        )
        return resp.json().get("response", "").strip()
    except Exception as e:
        return f"[LLM unavailable: {e}]"


def find_correlation(wall_time, source):
    conn = get_db()
    if source == "cosmicwatch":
        row = conn.execute(
            "SELECT * FROM iphone_events WHERE ABS(wall_time - ?) <= ?"
            " ORDER BY ABS(wall_time - ?) LIMIT 1",
            (wall_time, CORRELATION_WINDOW_S, wall_time),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM cosmicwatch_events WHERE ABS(wall_time - ?) <= ?"
            " ORDER BY ABS(wall_time - ?) LIMIT 1",
            (wall_time, CORRELATION_WINDOW_S, wall_time),
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def interpret_cosmicwatch(event, correlated=None):
    coinc = "YES — both detectors fired" if event.get("coincidence_flag") else "no"
    prompt = (
        f"Live CosmicWatch event:\n"
        f"  Event #{event.get('event_num')}  ADC={event.get('adc_value')}"
        f"  SiPM={event.get('sipm_mv')}mV  Coincidence={coinc}\n"
        f"  T={event.get('temperature_c')}°C  P={event.get('pressure_pa'):.0f}Pa"
        f"  Deadtime={event.get('deadtime_s'):.4f}s\n"
    )
    if correlated:
        dt = abs(event.get("wall_time", 0) - correlated.get("wall_time", 0))
        prompt += (
            f"\n*** CORRELATED iPhone camera detection {dt:.2f}s apart! ***\n"
            f"  iPhone cluster: {correlated.get('cluster_size')} pixels"
            f"  brightness: {correlated.get('brightness', 0):.1f}\n\n"
            f"This may be an extended air shower hitting both detectors simultaneously."
            f" Interpret the combined event in 3 sentences."
        )
    else:
        prompt += "\nGive a concise 2-sentence physics interpretation."
    return ask_llm(prompt)


def interpret_iphone(event, correlated=None):
    prompt = (
        f"iPhone camera particle detection:\n"
        f"  Cluster: {event.get('cluster_size')} pixels"
        f"  Brightness: {event.get('brightness', 0):.1f}\n"
    )
    if correlated:
        dt = abs(event.get("wall_time", 0) - correlated.get("wall_time", 0))
        prompt += (
            f"\n*** CORRELATED CosmicWatch event {dt:.2f}s apart! ***\n"
            f"  ADC={correlated.get('adc_value')}"
            f"  Coincidence={'YES' if correlated.get('coincidence_flag') else 'no'}\n\n"
            f"This may be an extended air shower. Interpret in 3 sentences."
        )
    else:
        prompt += "\nIs this likely a cosmic ray hit or noise? Answer in 1 sentence."
    return ask_llm(prompt)


@app.route("/api/cosmicwatch", methods=["POST"])
def receive_cosmicwatch():
    event = request.json
    event["wall_time"] = time.time()

    conn = get_db()
    cur = conn.execute(
        """INSERT INTO cosmicwatch_events
           (event_num, timestamp_s, wall_time, adc_value, sipm_mv, coincidence_flag,
            temperature_c, pressure_pa, deadtime_s,
            accel_x, accel_y, accel_z, gyro_x, gyro_y, gyro_z, detector)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            event.get("event"), event.get("timestamp_s"), event["wall_time"],
            event.get("adc_value"), event.get("sipm_mv"), event.get("coincidence_flag"),
            event.get("temperature_c"), event.get("pressure_pa"), event.get("deadtime_s"),
            event.get("accel_x_g"), event.get("accel_y_g"), event.get("accel_z_g"),
            event.get("gyro_x_degs"), event.get("gyro_y_degs"), event.get("gyro_z_degs"),
            event.get("detector"),
        ),
    )
    event_id = cur.lastrowid
    conn.commit()
    conn.close()

    broadcast("cosmicwatch", {**event, "id": event_id})

    def process():
        correlated = find_correlation(event["wall_time"], "cosmicwatch")
        interpretation = interpret_cosmicwatch(event, correlated)
        conn2 = get_db()
        conn2.execute(
            "UPDATE cosmicwatch_events SET llm_interpretation=?, correlated_iphone_id=? WHERE id=?",
            (interpretation, correlated["id"] if correlated else None, event_id),
        )
        conn2.commit()
        conn2.close()
        broadcast("interpretation", {
            "source": "cosmicwatch", "id": event_id,
            "interpretation": interpretation,
            "correlated": correlated is not None,
            "event": event,
        })

    threading.Thread(target=process, daemon=True).start()
    return jsonify({"id": event_id})


@app.route("/api/iphone", methods=["POST"])
def receive_iphone():
    data = request.json
    wall_time = time.time()

    conn = get_db()
    cur = conn.execute(
        "INSERT INTO iphone_events (wall_time, brightness, cluster_size) VALUES (?,?,?)",
        (wall_time, data.get("brightness", 0), data.get("cluster_size", 0)),
    )
    event_id = cur.lastrowid
    conn.commit()
    conn.close()

    event = {"id": event_id, "wall_time": wall_time, **data}
    broadcast("iphone", event)

    def process():
        correlated = find_correlation(wall_time, "iphone")
        interpretation = interpret_iphone(event, correlated)
        conn2 = get_db()
        conn2.execute(
            "UPDATE iphone_events SET llm_interpretation=?, correlated_cw_id=? WHERE id=?",
            (interpretation, correlated["id"] if correlated else None, event_id),
        )
        conn2.commit()
        conn2.close()
        broadcast("interpretation", {
            "source": "iphone", "id": event_id,
            "interpretation": interpretation,
            "correlated": correlated is not None,
            "event": event,
        })

    threading.Thread(target=process, daemon=True).start()
    return jsonify({"id": event_id})


@app.route("/api/events")
def get_events():
    limit = request.args.get("limit", 50, type=int)
    conn = get_db()
    cw = [dict(r) for r in conn.execute(
        "SELECT * FROM cosmicwatch_events ORDER BY id DESC LIMIT ?", (limit,)
    )]
    iph = [dict(r) for r in conn.execute(
        "SELECT * FROM iphone_events ORDER BY id DESC LIMIT ?", (limit,)
    )]
    conn.close()
    return jsonify({"cosmicwatch": cw, "iphone": iph})


@app.route("/stream")
def stream():
    q = queue.Queue(maxsize=50)
    with sse_lock:
        sse_clients.append(q)

    def generate():
        try:
            yield "data: connected\n\n"
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield msg
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            with sse_lock:
                if q in sse_clients:
                    sse_clients.remove(q)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/")
@app.route("/<path:path>")
def serve_static(path="index.html"):
    return send_from_directory(app.static_folder, path)


if __name__ == "__main__":
    init_db()
    print("CosmicPhysicist server on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, threaded=True)
