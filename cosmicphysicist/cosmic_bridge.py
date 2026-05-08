#!/usr/bin/env python3
"""
CosmicWatch serial reader — parses events and POSTs them to the local server.
"""

import sys
import time
import serial
import requests
from datetime import datetime

SERIAL_PORT = "/dev/ttyACM1"
BAUD_RATE = 115200
SERVER_URL = "http://localhost:5000/api/cosmicwatch"


def parse_event(line: str) -> dict | None:
    parts = line.strip().split("\t")
    if len(parts) < 10:
        return None
    try:
        accel = parts[8].split(":")
        gyro = parts[9].split(":")
        return {
            "event": int(parts[0]),
            "timestamp_s": float(parts[1]),
            "coincidence_flag": int(parts[2]),
            "adc_value": int(parts[3]),
            "sipm_mv": float(parts[4]),
            "deadtime_s": float(parts[5]),
            "temperature_c": float(parts[6]),
            "pressure_pa": float(parts[7]),
            "accel_x_g": float(accel[0]),
            "accel_y_g": float(accel[1]),
            "accel_z_g": float(accel[2]),
            "gyro_x_degs": float(gyro[0]),
            "gyro_y_degs": float(gyro[1]),
            "gyro_z_degs": float(gyro[2]),
            "detector": parts[10].strip() if len(parts) > 10 else "unknown",
        }
    except (ValueError, IndexError):
        return None


def main():
    print(f"[{datetime.now():%H:%M:%S}] CosmicWatch bridge starting on {SERIAL_PORT}")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=5)
    except serial.SerialException as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    try:
        while True:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace")
            event = parse_event(line)
            if not event:
                continue

            coinc = " *** COINCIDENCE ***" if event["coincidence_flag"] else ""
            print(
                f"[{datetime.now():%H:%M:%S}] #{event['event']}"
                f"  ADC={event['adc_value']}"
                f"  SiPM={event['sipm_mv']}mV"
                f"  P={event['pressure_pa']:.0f}Pa"
                f"{coinc}"
            )
            try:
                requests.post(SERVER_URL, json=event, timeout=5)
            except Exception as e:
                print(f"  [server error: {e}]")
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
