"""
virtual_sensor.py  —  A VIRTUAL IoT soil-sensor node for SmartZameen AI

This Python script REPLACES physical IoT hardware (ESP8266 + sensors). It
behaves exactly like a real field node would: every few seconds it reads its
"sensors" (simulated with realistic random drift) and POSTs a JSON packet to
the SAME backend endpoint a real device would use — /api/sensor-ingest.

Why this matters: the backend cannot tell the difference between this script
and a $20 hardware node. The transport and payload are identical. So the entire
IoT pipeline (ingest -> store -> auto crop prediction -> live dashboard) is
fully demonstrable with zero money and zero hardware setup.

Run it (backend must already be running):
    python virtual_sensor.py

Options:
    python virtual_sensor.py --interval 3      # seconds between readings
    python virtual_sensor.py --node ESP8266-A0 # pretend to be hardware
    python virtual_sensor.py --once            # send a single reading and exit
    python virtual_sensor.py --url http://localhost:80/api/sensor-ingest

Dependencies: just `requests` (already in requirements.txt).
"""

import argparse
import random
import sys
import time

import requests

DEFAULT_URL = "http://localhost:80/api/sensor-ingest"

# Each sensor: realistic baseline + plausible min/max range for Pakistani soil.
SENSORS = {
    "nitrogen":    {"value": 75.0, "min": 0,   "max": 140, "decimals": 0},
    "phosphorus":  {"value": 45.0, "min": 0,   "max": 145, "decimals": 0},
    "potassium":   {"value": 50.0, "min": 0,   "max": 205, "decimals": 0},
    "ph":          {"value": 6.8,  "min": 3.5, "max": 9.5, "decimals": 1},
    "temperature": {"value": 27.0, "min": 5,   "max": 48,  "decimals": 1},
    "rainfall":    {"value": 95.0, "min": 0,   "max": 300, "decimals": 0},
    "moisture":    {"value": 42.0, "min": 0,   "max": 100, "decimals": 0},
}

REGIONS = ["Punjab", "Sindh", "KPK", "Balochistan"]
SEASONS = ["Rabi", "Kharif"]


def drift(sensor):
    """Move a sensor value by a small natural amount, clamped to its range."""
    span = sensor["max"] - sensor["min"]
    sensor["value"] += (random.random() - 0.5) * span * 0.06   # +/-3% wander
    sensor["value"] = max(sensor["min"], min(sensor["max"], sensor["value"]))
    return round(sensor["value"], sensor["decimals"])


def build_payload(node_id, region, season):
    source = "hardware" if node_id.upper().startswith("ESP") else "simulator"
    payload = {key: drift(s) for key, s in SENSORS.items()}
    payload.update({
        "node_id": node_id,
        "source":  source,
        "region":  region,
        "season":  season,
    })
    return payload


def transmit(url, payload):
    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.ok:
            data = res.json()
            crop = data.get("predicted_crop")
            extra = f"  ->  suggests {crop}" if crop else ""
            print(f"[200 OK] N{payload['nitrogen']} P{payload['phosphorus']} "
                  f"K{payload['potassium']} pH{payload['ph']} "
                  f"temp{payload['temperature']}C{extra}")
            return True
        print(f"[HTTP {res.status_code}] backend rejected the reading: {res.text[:120]}")
    except requests.exceptions.ConnectionError:
        print(f"[OFFLINE] Cannot reach backend at {url} — is it running? (python app.py)")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
    return False


def main():
    p = argparse.ArgumentParser(description="Virtual IoT soil sensor for SmartZameen AI")
    p.add_argument("--url", default=DEFAULT_URL, help="Ingest endpoint URL")
    p.add_argument("--interval", type=float, default=3.0, help="Seconds between readings")
    p.add_argument("--node", default="SIM-NODE-01", help="Node ID (start with ESP to fake hardware)")
    p.add_argument("--region", default="Punjab", choices=REGIONS)
    p.add_argument("--season", default="Rabi", choices=SEASONS)
    p.add_argument("--once", action="store_true", help="Send one reading and exit")
    args = p.parse_args()

    print("=" * 52)
    print(" SmartZameen — Virtual IoT Soil Node")
    print(f" node={args.node}  region={args.region}  season={args.season}")
    print(f" target={args.url}")
    print(f" {'single reading' if args.once else f'streaming every {args.interval}s — Ctrl+C to stop'}")
    print("=" * 52)

    if args.once:
        transmit(args.url, build_payload(args.node, args.region, args.season))
        return

    try:
        while True:
            transmit(args.url, build_payload(args.node, args.region, args.season))
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[STOPPED] Virtual sensor node powered off.")
        sys.exit(0)


if __name__ == "__main__":
    main()
