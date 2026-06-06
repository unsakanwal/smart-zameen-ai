# SmartZameen AI — Setup & Run Guide

AI crop-recommendation system with a **fully virtual IoT soil-sensor layer**
(no hardware, no cost). Backend is **Flask + SQLite**; frontend is plain
**HTML/CSS/JS** served by the same backend.

- **Database:** SQLite — a single file, created automatically. Nothing to install or configure.
- **IoT:** simulated entirely in software (a Python virtual sensor + an HTML simulator). No ESP8266 needed.
- **Python:** works on **Python 3.14+**. **No virtual environment required.**

---

## 1. Prerequisites

- **Python 3.14+** installed and on your PATH. Check:
  ```powershell
  python --version
  ```
- That's it. SQLite ships with Python — no database server to install.

---

## 2. Install dependencies (one time)

From the project root:

```powershell
cd c:\Users\Faizan\Desktop\smart-zameen-ai\backend
pip install -r requirements.txt
```

If you get a permissions warning, install into your user account instead:

```powershell
pip install --user -r requirements.txt
```

> This installs Flask, scikit-learn, NumPy, Pillow, SciPy, Twilio, Anthropic, etc.
> The versions are chosen to have Python 3.14 wheels, so pip just downloads them — no compiling.

---

## 3. Run the backend

```powershell
cd c:\Users\Faizan\Desktop\smart-zameen-ai\backend
python app.py
```

On first run you'll see:

```
SmartZameen Backend
Database setup...
[OK] Sample crops data ready!
[OK] Database aur tables tayar hain!
[OK] ML Model load ho gaya!          <- or a rule-based fallback notice (both fine)
Server: http://localhost:80
```

The SQLite file `backend/database/smartzameen.db` is created automatically here.

> **Port 80 note (Windows):** if you see `PermissionError` / `OSError 10013`
> ("only one usage of each socket address"), port 80 is taken or reserved.
> Easiest fix: **close Skype/IIS** or **run the terminal as Administrator**, then
> `python app.py` again. (The frontend is wired for port 80, so keeping 80 is the
> smoothest path.)

---

## 4. Open the app (frontend)

The backend serves the frontend, so just open these in your browser:

| Page | URL |
|---|---|
| Landing | http://localhost:80/ |
| Login / Signup | http://localhost:80/login.html |
| Dashboard | http://localhost:80/dashboard.html |
| Crop Prediction | http://localhost:80/predict.html |
| **IoT Soil Simulator** | http://localhost:80/sensor-simulator.html |

> Do **not** open the HTML files directly from disk (`file://`). Always go through
> `http://localhost:80/...` so the frontend can reach the backend API.

---

## 5. Run the virtual IoT sensor (the "no-hardware" IoT)

This is the part that replaces a physical ESP8266 + soil sensor. It's a Python
script that pretends to be a field device and streams live readings to the
backend. **Open a second terminal** (keep the backend running in the first):

```powershell
cd c:\Users\Faizan\Desktop\smart-zameen-ai\backend
python virtual_sensor.py
```

You'll see readings flow every 3 seconds, each one auto-getting a crop suggestion:

```
[200 OK] N75 P45 K50 pH6.8 temp27.0C  ->  suggests wheat
```

Useful options:

```powershell
python virtual_sensor.py --interval 2          # faster stream
python virtual_sensor.py --once                # send a single reading
python virtual_sensor.py --node ESP8266-A0     # show up as "hardware" on the dashboard
python virtual_sensor.py --region Sindh --season Kharif
```

Now open **http://localhost:80/dashboard.html** — the **Connected Soil Node** tile
goes *Live* and updates every 3 seconds with N/P/K/pH/temperature/moisture and the
AI-suggested crop.

> Prefer clicking over the command line? The **HTML simulator**
> (`/sensor-simulator.html`) does the same thing with sliders and a
> "Start Auto-Stream" button. The virtual sensor and the HTML simulator are
> interchangeable — both POST to the same endpoint.

---

## 6. Full demo in 4 steps

1. **Terminal 1:** `python app.py`  → backend on http://localhost:80
2. **Browser:** open http://localhost:80/dashboard.html
3. **Terminal 2:** `python virtual_sensor.py`
4. Watch the **Connected Soil Node** tile on the dashboard light up and update live, with a crop suggestion from the soil readings.

Every reading is also saved permanently in SQLite (`sensor_readings` table).

---

## 7. Optional — external API keys

The app **runs fine without any keys** (it uses sensible fallbacks). To enable the
extra features, fill these into `backend/.env`:

| Feature | Key(s) in `.env` |
|---|---|
| Soil-image AI analysis | `ANTHROPIC_API_KEY` (or set it as an environment variable) |
| WhatsApp / SMS bot | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE` |
| Live weather | `WEATHER_API_KEY` |

The old `DB_HOST` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` entries are **no longer
used** (we moved to SQLite) — you can ignore or delete them.

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `PermissionError` / `OSError 10013` on start | Port 80 is busy/reserved — run terminal as Administrator, or close Skype/IIS. |
| `ModuleNotFoundError: No module named 'flask'` (etc.) | Run `pip install -r requirements.txt` in the `backend` folder. |
| `[WARNING] Model load fail ... rule-based prediction use hogi` | Harmless. The old model pickle didn't match the new scikit-learn; the app falls back to rule-based crop logic. To get the exact model back, retrain: `python model-training/crop_recommendation.py`. |
| Virtual sensor says `[OFFLINE] Cannot reach backend` | Start the backend first (`python app.py`), then run the sensor. |
| Dashboard tile stays "Waiting for node…" | Make sure the virtual sensor (or HTML simulator) is transmitting, and that you opened the dashboard via `http://localhost:80/...`, not `file://`. |
| Want a clean database | Stop the backend and delete `backend/database/smartzameen.db`. It's recreated on next start. |

---

## What changed in this refactor

- **MySQL → SQLite** (`backend/database/db.py`): single-file DB, zero setup, zero cost. Public API unchanged; a compatibility shim keeps existing `%s`-style SQL working.
- **Python 3.14 ready**: dependency versions bumped to ones with 3.14 wheels; model loading made resilient so a version mismatch falls back to rule-based prediction instead of crashing.
- **Virtual IoT** (`backend/virtual_sensor.py`): a software soil-sensor node — the IoT layer with no hardware and no money spent.
- **IoT persistence**: every sensor reading is now logged to the SQLite `sensor_readings` table.
- **No venv needed**: install straight into your Python 3.14.
