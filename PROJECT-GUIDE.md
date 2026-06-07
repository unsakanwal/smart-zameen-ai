# 🌾 SmartZameen AI — Project Guide (Testing & Deployment)

A step-by-step guide to **run, test, and deploy** SmartZameen AI to production
(**frontend on Vercel · backend on Render · database on Neon Postgres**).

For a feature/architecture overview see **`project-prd.md`**. For a quick local run see **`SETUP.md`**.

---

## 1. What's in the box

| Layer | Tech | Notes |
|-------|------|-------|
| Frontend | HTML + CSS + vanilla JS | Static site on **Vercel**; shared design system in `frontend/css/theme.css` |
| Backend | Python + Flask (gunicorn) | Single app `backend/app.py` on **Render** |
| Database | **Neon Postgres** (prod) / SQLite (local) | Auto-selected by `DATABASE_URL`; `psycopg` driver |
| ML models | scikit-learn | `backend/models/local-trained-modal/` + `backend/models/crop-reccomendation-modal/` |
| AI assistant | **OpenAI** (`gpt-4o-mini` + `whisper-1`) | Chat (text/vision/file) + voice. **No Anthropic.** |
| Messaging | Twilio | WhatsApp + SMS (needs creds + public URL) |
| Weather | OpenWeatherMap | **Real data only** — no mock fallback |
| IoT | Virtual sensor + HTML simulator | No hardware required |

### Folder structure

```
smart-zameen-ai/
├── backend/
│   ├── app.py                       # Flask app (serves API + frontend locally)
│   ├── requirements.txt
│   ├── Procfile                     # gunicorn app:app
│   ├── .env / .env.example          # secrets (gitignored)
│   ├── database/db.py               # dual-mode: Neon Postgres OR SQLite
│   ├── routes/                      # crop, weather, whatsapp, sms, image, voice, sensor, chat
│   ├── virtual_sensor.py            # CLI virtual IoT node
│   └── models/
│       ├── local-trained-modal/     # crop_model.pkl, le_*.pkl, soil_classifier.pkl, soil_classes.json
│       └── crop-reccomendation-modal/  # soil.pkl, label_encoder.pkl (higher-accuracy Kaggle model)
├── frontend/
│   ├── *.html
│   ├── css/theme.css
│   └── js/                          # config.js (backend URL), lang, main, chat, camera, sidebar
├── render.yaml                      # Render blueprint (backend)
├── project-prd.md · PROJECT-GUIDE.md · SETUP.md · README.md
```

---

## 2. Local setup & run

See **`SETUP.md`** for full detail. Short version:

```powershell
cd backend
python -m venv venv ; venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # then fill in OPENAI_API_KEY, WEATHER_API_KEY, (DATABASE_URL)
python app.py                   # http://localhost:80  (or :5000)
```

Locally the backend serves the frontend too, so open `http://localhost:80/`.

---

## 3. Feature test checklist

Replace `BASE` with your local URL (`http://localhost:80` or `:5000`) or your Render URL.

### 3.1 Crop prediction (core ML)
`POST BASE/api/predict-crop`
```powershell
Invoke-RestMethod -Uri "$BASE/api/predict-crop" -Method Post -ContentType "application/json" `
  -Body '{"nitrogen":80,"phosphorus":40,"potassium":30,"ph":6.8,"temperature":24,"rainfall":150,"region":"Punjab","season":"rabi","humidity":60}'
```
**Expect:** a crop + confidence + `top3`. The prediction is saved to the DB.

### 3.2 IoT simulator + virtual sensor
- HTML: `BASE/crop-advisor.html` → IoT tab → adjust sliders → **Transmit** → AI card fills in.
- CLI: `python virtual_sensor.py --once`
- `POST BASE/api/sensor-ingest` stores the reading; `BASE/dashboard.html` shows it **Live**.

### 3.3 Dashboard (real data)
Open `BASE/dashboard.html` → stats, recent predictions, weather card and forecast all load
from the API. Empty states show "—" (no fake numbers).

### 3.4 Weather (real only)
`Invoke-RestMethod "$BASE/api/weather?city=lahore"` → real temp/humidity/wind.
Without `WEATHER_API_KEY` it returns `success:false` (UI shows a neutral state).

### 3.5 Soil image analysis
`BASE/crop-advisor.html` → camera/upload a soil photo → soil type + estimated N/P/K/pH
(auto-fills only soil fields; you enter temperature/rainfall).

### 3.6 AI chat + voice (OpenAI)
`BASE/ai-agent.html` → type a question (any of the 5 languages), send a crop/soil **photo**,
or tap the **mic** to speak (audio → Whisper → text → reply). Needs `OPENAI_API_KEY`.

### 3.7 Auth
`BASE/signup.html` → create account → `BASE/login.html` → log in → dashboard.

### 3.8 WhatsApp / SMS
Needs Twilio + a public URL (your Render URL, or ngrok locally). See §5.4.

---

## 4. Deployment — Vercel + Render + Neon

The frontend (Vercel) and backend (Render) are **separate origins**; the database is **Neon**.

### 4.1 Database — Neon Postgres (free)
1. Create a project at **neon.tech** → copy the **connection string**
   (`postgresql://…?sslmode=require`).
2. You'll paste it into Render as `DATABASE_URL` (step 4.2). Tables are created automatically
   on first backend start.

### 4.2 Backend — Render (free)
1. Push the repo to GitHub. Ensure `backend/models/**` is committed (the `.pkl` files are
   needed at runtime — they're ~17 MB total, well under GitHub limits).
2. Render → **New → Blueprint** → pick the repo (it reads **`render.yaml`** automatically:
   root `backend`, build `pip install -r requirements.txt`, start `gunicorn app:app`).
3. In the Render dashboard set the env vars (all marked `sync:false` in the blueprint):
   `DATABASE_URL`, `OPENAI_API_KEY`, `WEATHER_API_KEY`, `TWILIO_ACCOUNT_SID`,
   `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE`.
4. Deploy. Note your backend URL: `https://<your-app>.onrender.com`.

> **Free-tier notes:** the service sleeps after ~15 min idle (first request is slow), and
> 512 MB RAM is tight with the 14 MB model — upgrade to **Starter** if it OOMs. Neon keeps
> data persistent regardless.

### 4.3 Frontend — Vercel (free)
1. Edit **`frontend/js/config.js`** → set `BACKEND_URL` to your Render URL → commit & push.
2. Vercel → **New Project** → import the repo → set **Root Directory = `frontend`** →
   framework preset **Other** (static) → Deploy.
3. Visit your Vercel URL. It calls the Render backend (CORS is already enabled).

### 4.4 Twilio WhatsApp / SMS webhooks
After the backend is public:
1. Twilio Console → WhatsApp Sandbox / Messaging.
2. Set the inbound webhook to `https://<your-app>.onrender.com/whatsapp` (and `/sms`).
3. For local testing use `ngrok http 80` and point the webhook at the ngrok HTTPS URL.

### 4.5 Frontend → backend URL (how it resolves)
`frontend/js/config.js` is the single source of truth. It:
- uses `http://localhost:5000` when opened as a `file://`,
- uses same-origin when served by Flask locally,
- otherwise uses `BACKEND_URL` (your Render URL) — i.e. on Vercel.

Every page loads `config.js` first, and every API call is routed through it.

---

## 5. Retraining the models

```powershell
cd model-training
python train_model.py        # → backend/models/local-trained-modal/crop_model.pkl + encoders
python train_soil_cnn.py     # (optional) → soil_classifier.pkl
```
Restart the backend to load new artifacts. Keep the scikit-learn version close to the one in
`requirements.txt` so the pickles load cleanly.

---

## 6. Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| Vercel site loads but API calls fail | `BACKEND_URL` in `frontend/js/config.js` not set to the Render URL (or Render is asleep — retry after ~30s). |
| `[OK] Database ready! (SQLite)` in prod | `DATABASE_URL` not set on Render → set the Neon string and redeploy. |
| Chat/voice error "OpenAI API key not set" | Add `OPENAI_API_KEY` on Render (and `backend/.env` locally). |
| Weather shows "—" | `WEATHER_API_KEY` missing — real data only, no mock. |
| Model-load warning at startup | Harmless sklearn version notice; the model still predicts. Retrain to silence. |
| Render build fails on a pinned wheel | Keep `requirements.txt` on version floors (`>=`); `PYTHON_VERSION` is pinned to 3.12 for stable wheels. |
| WhatsApp messages never arrive | Twilio webhook must point at the public Render URL, not localhost. |

---

## 7. Pre-deploy checklist

- [ ] `pip install -r requirements.txt` succeeds in a fresh venv
- [ ] `python app.py` boots, prints `[OK] ML Model load ho gaya!` and the DB mode
- [ ] Crop prediction, dashboard, weather, chat all work locally (§3)
- [ ] `backend/models/**` committed to git
- [ ] Neon `DATABASE_URL` + all API keys set in Render env (not committed)
- [ ] `frontend/js/config.js` → `BACKEND_URL` = Render URL
- [ ] Frontend deployed on Vercel (Root Directory = `frontend`)
- [ ] Twilio webhooks point at the public Render URL (if using WhatsApp/SMS)
- [ ] Any credentials shared during development have been rotated

---

*SmartZameen AI — Pakistani Kisan ko Technology ki Taqat 🌾*
