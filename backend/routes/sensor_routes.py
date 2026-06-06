"""
sensor_routes.py  —  IoT ingestion endpoint for SmartZameen AI

Location:  backend/routes/sensor_routes.py

Accepts soil-sensor readings from EITHER source through the SAME endpoint and
SAME JSON shape:
    1. The UI simulator panel (sensor-simulator.html)
    2. A physical ESP8266 POSTing over Wi-Fi (added later)

That shared path is the architectural point: the system is hardware-agnostic
and IoT-ready.

Wired up in app.py:
    from routes.sensor_routes import sensor_bp
    app.register_blueprint(sensor_bp)
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
import threading
import numpy as np

# Reuse the crop model that crop_routes already loads at import time. We import
# the MODULE (not the names) so we always read the globals it populates inside
# load_ml_model() — even though that runs after this import.
import routes.crop_routes as crop_routes

sensor_bp = Blueprint("sensor", __name__)

# ---------------------------------------------------------------------------
# In-memory store of the most recent reading + a short history ring buffer.
# Fine for an MVP demo; swap for a DB table for production.
# ---------------------------------------------------------------------------
_lock = threading.Lock()
_latest = None
_history = []          # newest-last
_MAX_HISTORY = 50

# Required numeric fields a valid reading must contain.
_REQUIRED = ["nitrogen", "phosphorus", "potassium", "ph",
             "temperature", "rainfall"]


def _try_predict(reading):
    """
    Run the incoming reading through the EXISTING crop model so a sensor packet
    instantly yields a crop suggestion (the demo highlight).

    This mirrors the prediction logic in crop_routes.predict_crop() exactly,
    using the same already-loaded model/encoders — it does NOT re-train or
    change anything. If the model isn't loaded, it falls back to the same
    rule_based_predict() crop_routes uses.

    Returns a dict {crop, confidence, top3, source} so the simulator can show
    the full model output, or None on any failure (ingestion still succeeds
    either way). `source` is "model" or "rule-based" so the UI is honest about
    where the answer came from.
    """
    try:
        region = str(reading.get("region", "Punjab")).strip().title()
        season = str(reading.get("season", "Rabi")).strip().lower()

        model     = crop_routes.model
        encoder   = crop_routes.encoder
        le_season = crop_routes.le_season
        le_region = crop_routes.le_region

        if model is not None and encoder is not None:
            season_enc = le_season.transform([season])[0] if season in le_season.classes_ else 0
            region_enc = le_region.transform([region])[0] if region in le_region.classes_ else 0
            features = np.array([[reading["nitrogen"], reading["phosphorus"],
                                  reading["potassium"], reading["ph"],
                                  reading["temperature"], reading["rainfall"],
                                  season_enc, region_enc]])
            probs   = model.predict_proba(features)[0]
            top_idx = np.argsort(probs)[::-1][:3]
            top3 = [
                {
                    "crop":       encoder.inverse_transform([int(i)])[0],
                    "confidence": round(float(probs[int(i)]) * 100, 1),
                    "urdu":       crop_routes.CROP_INFO.get(
                                      encoder.inverse_transform([int(i)])[0], {}
                                  ).get("urdu", ""),
                }
                for i in top_idx
            ]
            return {
                "crop":       top3[0]["crop"],
                "confidence": top3[0]["confidence"],
                "urdu":       top3[0]["urdu"],
                "top3":       top3,
                "source":     "model",
            }

        # Model not loaded — same fallback crop_routes uses.
        crop_name, conf, _top3 = crop_routes.rule_based_predict(
            reading["temperature"], reading["rainfall"], season, region)
        return {
            "crop":       crop_name,
            "confidence": conf,
            "urdu":       crop_routes.CROP_INFO.get(crop_name, {}).get("urdu", ""),
            "top3":       [{"crop": crop_name, "confidence": conf,
                            "urdu": crop_routes.CROP_INFO.get(crop_name, {}).get("urdu", "")}],
            "source":     "rule-based",
        }
    except Exception:
        return None


@sensor_bp.route("/api/sensor-ingest", methods=["POST"])
def sensor_ingest():
    """Accept one sensor reading from simulator OR ESP8266 hardware."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "error": "No JSON body received"}), 400

    # Validate required numeric fields.
    missing = [f for f in _REQUIRED if f not in data]
    if missing:
        return jsonify({"ok": False,
                        "error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        reading = {
            "node_id":     str(data.get("node_id", "UNKNOWN")),
            "source":      str(data.get("source", "simulator")),
            "nitrogen":    float(data["nitrogen"]),
            "phosphorus":  float(data["phosphorus"]),
            "potassium":   float(data["potassium"]),
            "ph":          float(data["ph"]),
            "temperature": float(data["temperature"]),
            "rainfall":    float(data["rainfall"]),
            "moisture":    float(data.get("moisture", -1)),
            "region":      str(data.get("region", "Punjab")),
            "season":      str(data.get("season", "Rabi")),
            "received_at": datetime.now(timezone.utc).isoformat(),
        }
    except (TypeError, ValueError) as e:
        return jsonify({"ok": False,
                        "error": f"Bad numeric value: {e}"}), 400

    # Instant crop suggestion from the reading (full model output).
    predicted = _try_predict(reading)
    if predicted:
        reading["predicted_crop"] = predicted["crop"]        # back-compat (virtual_sensor.py)
        reading["prediction"]     = predicted                 # full {crop,confidence,top3,source}

    # Store in memory (fast path the dashboard polls).
    global _latest
    with _lock:
        _latest = reading
        _history.append(reading)
        if len(_history) > _MAX_HISTORY:
            _history.pop(0)

    # Also persist to SQLite as a permanent audit trail (best-effort).
    try:
        from database.db import save_sensor_reading
        save_sensor_reading(reading)
    except Exception:
        pass

    resp = {"ok": True, "stored": True, "node_id": reading["node_id"]}
    if predicted:
        resp["predicted_crop"] = predicted["crop"]            # back-compat
        resp["prediction"]     = predicted                     # full result for the UI
    return jsonify(resp), 200


@sensor_bp.route("/api/sensor-latest", methods=["GET"])
def sensor_latest():
    """Dashboard polls this to show the most recent live reading."""
    with _lock:
        if _latest is None:
            return jsonify({"ok": True, "reading": None}), 200
        return jsonify({"ok": True, "reading": _latest}), 200


@sensor_bp.route("/api/sensor-history", methods=["GET"])
def sensor_history():
    """Return recent readings (newest last) for a live chart / table."""
    with _lock:
        return jsonify({"ok": True, "count": len(_history),
                        "readings": list(_history)}), 200
