# 🌾 SmartZameen AI — Project Guide (Testing & Deployment)

A complete, step-by-step guide to **run, test every feature, and deploy** SmartZameen AI.
Read this end-to-end before deploying.

---

## 1. What's in the box

| Layer | Tech | Notes |
|-------|------|-------|
| Frontend | HTML + CSS + vanilla JS | Served by Flask; shared design system in `frontend/css/theme.css` |
| Backend | Python + Flask | Single entry point `backend/app.py` |
| Database | SQLite | Zero-config; file auto-created at `backend/database/smartzameen.db` |
| ML model | scikit-learn Random Forest | Trained artifacts in `backend/ml_models/*.pkl` |
| AI services | Anthropic Claude | Soil image analysis + voice chat (needs API key) |
| Messaging | Twilio | WhatsApp + SMS (needs Twilio creds + public URL) |
| Weather | OpenWeatherMap | Falls back to mock data without a key |
| IoT | Virtual sensor + simulator | No hardware required |

### Final folder structure

```
smart-zameen-ai/
├── backend/
│   ├── app.py                  # Flask app (entry point)
│   ├── requirements.txt
│   ├── .env                    # API keys (you create this)
│   ├── database/db.py          # SQLite layer
│   ├── routes/                 # crop, weather, whatsapp, sms, image, voice, sensor
│   ├── virtual_sensor.py       # CLI virtual IoT node
│   └── ml_models/              # trained .pkl artifacts  (renamed from models/)
├── frontend/
│   ├── *.html
│   ├── assets/
│   │   ├── favicon.svg
│   │   └── images/             # all images live here
│   ├── css/theme.css           # shared design tokens + components
│   └── js/
├── model-training/             # training scripts + dataset (renamed from ml_training/)
├── README.md
└── PROJECT-GUIDE.md            # this file
```

> ⚠️ **Cleanup note:** there is a leftover nested folder `backend/ml_models/models/`
> (an accidental duplicate of two `.pkl` files from earlier). Nothing references it.
> It is safe to delete: `Remove-Item -Recurse backend/ml_models/models`.

---

## 2. Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.10+ (tested on 3.14) | `python --version` |
| pip | latest | `pip --version` |

No MySQL, no Node.js required.

---

## 3. Local setup

```powershell
# from the project root
cd backend

# create + activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# install dependencies
pip install -r requirements.txt
```

### Create `backend/.env` (optional but recommended)

```
ANTHROPIC_API_KEY=your_anthropic_key_here     # soil image + voice AI
WEATHER_API_KEY=your_openweather_key_here      # real weather (else mock data)
TWILIO_ACCOUNT_SID=your_twilio_sid_here         # WhatsApp + SMS
TWILIO_AUTH_TOKEN=your_twilio_token_here
TWILIO_PHONE=+14155238886
```

> Without keys the **core app still runs** — crop prediction, the IoT simulator,
> weather (mock), and auth all work. Only the AI image/voice and messaging
> features need their respective keys.

---

## 4. Run it

```powershell
cd backend
python app.py
```

You'll see:

```
SmartZameen Backend
[OK] Database ready!
Server: http://localhost:80      (or :5000 if port 80 is busy)
```

> **Port note:** the app tries **port 80** first and automatically **falls back to
> port 5000** if 80 needs admin / is taken. Use whichever URL it prints.

Open the app at the printed URL, e.g. `http://localhost:80` or `http://localhost:5000`.

| Page | Path |
|------|------|
| Home | `/` or `/index.html` |
| Crop AI | `/predict.html` |
| Dashboard | `/dashboard.html` |
| IoT Node simulator | `/sensor-simulator.html` |
| Login / Sign up | `/login.html`, `/signup.html` |

---

## 5. Feature-by-feature test checklist

Replace `BASE` below with your printed base URL (`http://localhost:80` or `:5000`).

### ✅ 5.1 Crop prediction (core ML)
1. Open `BASE/predict.html`.
2. Fill N=80, P=42, K=42, pH=6.5, Temp=18, Rainfall=70, Region=Punjab, Season=Rabi.
3. Click **Get Best Crop Recommendation**.
4. **Expect:** result card shows **Wheat** with ~94% confidence + top-3 list.

CLI check (PowerShell):
```powershell
Invoke-RestMethod -Uri "http://localhost:80/api/predict-crop" -Method Post -ContentType "application/json" -Body '{"nitrogen":80,"phosphorus":42,"potassium":42,"ph":6.5,"temperature":18,"rainfall":70,"region":"Punjab","season":"Rabi"}'
```
Expect `crop: wheat`, `confidence: ~94`.

### ✅ 5.2 IoT Soil Sensor Simulator (the highlight)
1. Open `BASE/sensor-simulator.html`.
2. Click a preset (e.g. **🌾 Rice**) or drag the sliders.
3. Watch the **radar chart**, **soil core**, and **wiring diagram values** update live.
4. Click **Transmit Reading** → wires animate, and the **AI Crop Recommendation**
   card fills in from the real model (Rice ≈ 67%).
5. Try **Auto-Stream (5s)** to simulate a live device.

CLI check:
```powershell
Invoke-RestMethod -Uri "http://localhost:80/api/sensor-ingest" -Method Post -ContentType "application/json" -Body '{"nitrogen":95,"phosphorus":55,"potassium":45,"ph":6.2,"temperature":28,"rainfall":210,"moisture":85,"region":"Sindh","season":"Kharif","node_id":"SIM-NODE-01"}'
```
Expect `predicted_crop: rice` and a `prediction` object with `top3`.

### ✅ 5.3 Virtual sensor (no-hardware IoT, command line)
With the server running, in a second terminal:
```powershell
cd backend
venv\Scripts\activate
python virtual_sensor.py --once                 # send one reading
python virtual_sensor.py --interval 3           # stream every 3s (Ctrl+C to stop)
python virtual_sensor.py --node ESP32-A0        # pretend to be hardware
```
Then open `BASE/dashboard.html` → the **Connected Soil Node** tile shows the live reading.

### ✅ 5.4 Dashboard live tile
1. Open `BASE/dashboard.html`.
2. In another tab, transmit from the simulator (5.2) or run the virtual sensor (5.3).
3. **Expect:** the "Connected Soil Node" card switches to **Live** and shows the values + suggested crop within ~3s.

### ✅ 5.5 Weather
1. Dashboard → change the city dropdown.
2. CLI: `Invoke-RestMethod "http://localhost:80/api/weather?city=lahore"`
3. **Expect:** temp/humidity/wind. (Mock data if `WEATHER_API_KEY` not set — still 200 OK.)

### ✅ 5.6 Soil image analysis *(needs `ANTHROPIC_API_KEY`)*
1. `BASE/predict.html` → **Open Camera** or upload a soil photo.
2. **Expect:** detected soil type + estimated NPK/pH + Urdu description.
3. Without the key it returns a clear "not configured / fallback" message (no crash).

### ✅ 5.7 Voice AI chat *(needs `ANTHROPIC_API_KEY`, Chrome recommended)*
1. `BASE/predict.html?mode=voice` → toggle Voice Mode → tap the mic, speak.
2. **Expect:** speech-to-text + a short spoken reply.

### ✅ 5.8 Auth (login / signup)
1. `BASE/signup.html` → create an account → should succeed and store a token.
2. `BASE/login.html` → log in with the same credentials → redirects to dashboard.
3. CLI:
```powershell
Invoke-RestMethod -Uri "http://localhost:80/signup" -Method Post -ContentType "application/json" -Body '{"name":"Test","email":"t@t.com","password":"secret123"}'
```

### ✅ 5.9 WhatsApp / SMS *(needs Twilio + a public URL — see §6.4)*
- Local testing requires a tunnel (ngrok) because Twilio can't reach `localhost`.

### Quick smoke test (all core endpoints at once)
```powershell
$base = "http://localhost:80"
"GET  /";              (Invoke-WebRequest "$base/").StatusCode
"GET  predict.html";   (Invoke-WebRequest "$base/predict.html").StatusCode
"GET  simulator";      (Invoke-WebRequest "$base/sensor-simulator.html").StatusCode
"GET  favicon";        (Invoke-WebRequest "$base/assets/favicon.svg").StatusCode
"GET  weather";        (Invoke-RestMethod "$base/api/weather?city=multan").temperature
"POST predict-crop";   (Invoke-RestMethod "$base/api/predict-crop" -Method Post -ContentType "application/json" -Body '{"nitrogen":80,"phosphorus":42,"potassium":42,"ph":6.5,"temperature":18,"rainfall":70,"region":"Punjab","season":"Rabi"}').crop
```

---

## 6. Deployment

The app is a single Flask service that serves **both** the API and the static frontend,
so you deploy **one thing**.

### 6.0 Pre-deploy hardening (do this first)
1. **Turn off debug.** In `backend/app.py` the dev server uses `debug=True`. For
   production use a real WSGI server (below) — don't run `python app.py` in prod.
2. **Don't commit secrets.** Keep `.env` out of git; set the same keys as
   environment variables on the host.
3. **Bind the host's port.** Most platforms inject a `$PORT` env var — use it.

A production-friendly entry is simply the existing `app` object in `backend/app.py`
(`app = Flask(...)`), so any WSGI server can serve `app:app`.

### 6.1 Option A — Render.com (easiest free host)
1. Push the repo to GitHub.
2. Add `gunicorn>=22.0` to `backend/requirements.txt` (uncomment the line already there).
3. Create a **Web Service** on Render → connect the repo.
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Add environment variables (ANTHROPIC_API_KEY, WEATHER_API_KEY, Twilio…) in the dashboard.
5. Deploy. Your app is at `https://<your-app>.onrender.com`.

> SQLite works on a single Render instance but resets on redeploy/restart (ephemeral
> disk). For persistent data, attach a Render Disk mounted at `backend/database/`,
> or move to Postgres later.

### 6.2 Option B — Railway
1. New Project → Deploy from GitHub.
2. Set **Root Directory** = `backend`.
3. Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Add env vars. Railway gives you a public domain.

### 6.3 Option C — Windows VPS / your own machine
Use **waitress** (pure-Python, Windows-friendly):
```powershell
cd backend
venv\Scripts\activate
pip install waitress
waitress-serve --listen=0.0.0.0:8000 app:app
```
Put Nginx/Caddy in front for HTTPS if exposing publicly.

### 6.4 Twilio WhatsApp / SMS webhooks
After deploying to a public HTTPS URL:
1. Twilio Console → WhatsApp Sandbox / Messaging.
2. Set the inbound webhook to `https://<your-domain>/whatsapp` (and `/sms`).
3. For **local** testing use ngrok:
   ```powershell
   ngrok http 80           # or 5000 / 8000 — match your running port
   ```
   then point the Twilio webhook at the ngrok HTTPS URL.

### 6.5 Frontend → backend URL
Pages call the API with **relative paths** (e.g. `/api/sensor-ingest`), so once the
frontend is served by the same Flask app, **no URL changes are needed** in production.
(The login page already auto-detects the origin.)

---

## 7. Retraining the model

```powershell
cd model-training
python crop_recommendation.py        # retrains crop model → writes backend/ml_models/*.pkl
python train_soil_cnn.py             # (optional) soil-image classifier
```
The crop script prints accuracy and saves `crop_model.pkl` + encoders into
`backend/ml_models/`. Restart the backend to load the new model.

---

## 8. Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| "Backend offline" in the simulator | Server not running, or wrong port — check the URL the server printed and that the Ingest URL field matches. |
| Port 80 error on start | Run as admin, or just let it fall back to 5000 (automatic), or change the port in `app.py`. |
| Predictions look like guesses, low variety | Confirm `[OK] ML Model load ho gaya!` appears at startup. If you see a model-load warning, the `.pkl` files in `backend/ml_models/` are missing — retrain (§7). |
| Soil image / voice "not configured" | `ANTHROPIC_API_KEY` not set in `backend/.env`. |
| Weather shows generic values | `WEATHER_API_KEY` not set → mock data (expected). |
| WhatsApp messages never arrive | Twilio webhook must point at a **public** URL, not localhost (use ngrok / deployed URL). |
| Images/logo not showing | Confirm they exist under `frontend/assets/images/` and pages reference `assets/images/...`. |
| sklearn "InconsistentVersionWarning" | Harmless version notice; the model still loads and predicts. Retrain to silence it. |

---

## 9. Pre-deploy checklist

- [ ] `pip install -r requirements.txt` succeeds in a fresh venv
- [ ] `python app.py` boots and prints `[OK] ML Model load ho gaya!`
- [ ] Crop prediction returns a sensible crop (§5.1)
- [ ] Simulator transmits and shows a model result (§5.2)
- [ ] Dashboard live tile updates (§5.4)
- [ ] Favicon + images load (no 404s in browser dev tools → Network)
- [ ] Secrets are in env vars, not committed
- [ ] Production server (`gunicorn`/`waitress`) used instead of the dev server
- [ ] Twilio webhooks point at the public URL (if using WhatsApp/SMS)

---

*SmartZameen AI — Pakistani Kisan ko Technology ki Taqat 🌾*
