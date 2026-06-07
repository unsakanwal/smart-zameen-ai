# 🌾 SmartZameen AI — Smart Agriculture System

An AI-powered crop-recommendation platform for Pakistani farmers. Enter soil data, upload a
soil photo, or just **talk** to it — and get the best crop suggestion, real weather, and help
over **WhatsApp/SMS**, in **5 regional languages** (Urdu, Punjabi, Sindhi, Pashto, English).

- **Frontend:** plain HTML/CSS/JS — deployed on **Vercel**
- **Backend:** Flask + scikit-learn — deployed on **Render**
- **Database:** **Neon Postgres** (prod) / **SQLite** (local, zero-setup)
- **AI assistant:** **OpenAI** (`gpt-4o-mini` chat/vision + `whisper-1` voice)
- **Weather:** OpenWeatherMap (real data only) · **Bots:** Twilio (WhatsApp + SMS)

> 📖 **Full spec, setup, testing, and deployment runbook live in [`prd.md`](prd.md).**
> This README is the quick start.

---

## ✨ Features

| # | Feature | How it works |
|---|---------|--------------|
| 1 | **AI Crop Recommendation** | Two ML models: a higher-accuracy 22-crop model (when humidity is given) and a region/season-aware local Random Forest; rule-based fallback. The result shows **which model ran**, with top-3 alternatives + confidence. |
| 2 | **Soil Image Analysis** | Upload/snap a soil photo → a local CNN-feature classifier detects soil type and estimates **N/P/K & pH** (it never fabricates temperature/rainfall). |
| 3 | **AI Chat + Voice** | One OpenAI-powered chat handles **text, image, files, and voice** (mic → Whisper → reply) in the user's language. |
| 4 | **Weather** | Real OpenWeatherMap data + 5-step forecast for 8 Pakistani cities. **No mock data** — missing key → neutral empty state. |
| 5 | **Virtual IoT Soil Node** | A virtual sensor + an HTML simulator POST readings to the same ingest API a real ESP32 would use; the dashboard shows the live reading + AI crop. |
| 6 | **Dashboard & History** | Real stats (totals, this-month, avg confidence, top crop), recent predictions, and full activity log — all from the database. |
| 7 | **WhatsApp / SMS bot** | Conversational crop advice over Twilio, same crop model, same 5 languages. |
| 8 | **Auth** | Email/password signup + login (SHA-256 hashed) with a show/hide password toggle. |

---

## 🚀 Quick start (local)

Locally **one backend serves both the API and the frontend**, so you don't need Vercel for dev.

```powershell
cd backend
python -m venv venv
venv\Scripts\activate              # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env             # then fill in keys (all optional for the core app)
python app.py                      # http://localhost:80  (falls back to :5000)
```

Open the printed URL. The core app (crop prediction, IoT simulator, dashboard, auth) runs
**without any API keys**. Chat/voice need `OPENAI_API_KEY`; the Weather page needs
`WEATHER_API_KEY`. With **no** `DATABASE_URL`, it uses a local SQLite file automatically.

### Optional — run the virtual IoT sensor (no hardware)
```powershell
# second terminal, backend still running
cd backend ; venv\Scripts\activate
python virtual_sensor.py           # streams a reading every 3s (--once for one)
```
Then open `/dashboard.html` → the **Connected Soil Node** tile goes *Live*.

---

## 🔑 API keys (`backend/.env`)

| Service | Env var | Needed for |
|---------|---------|-----------|
| Neon Postgres | `DATABASE_URL` | persistence (unset → local SQLite) |
| OpenAI | `OPENAI_API_KEY` | chat + voice |
| OpenWeatherMap | `WEATHER_API_KEY` | the Weather page (real data only) |
| Twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE` | WhatsApp/SMS bot |

> No spaces around `=` in `.env`. `.env` is gitignored — never commit it.

---

## 🌐 Pages

| Page | URL |
|------|-----|
| Landing | http://localhost:80/ |
| Login / Signup | /login.html · /signup.html |
| Dashboard | /dashboard.html |
| Crop Advisor (chat + voice + image) | /ai-agent.html |
| Crop prediction + IoT node | /crop-advisor.html |
| Weather · History · Settings | /weather.html · /history.html · /settings.html |

---

## 📡 Key API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/signup` · `/login` | Auth |
| POST | `/api/predict-crop` | Crop recommendation (returns `model` / `model_key`) |
| POST | `/api/analyze-soil-image` | Soil type + N/P/K/pH from a photo |
| POST | `/api/chat` · `/api/transcribe` | AI chat (text/vision/file) · voice → text |
| GET  | `/api/weather` · `/api/weather/forecast` · `/api/cities` | Weather (real only) |
| POST | `/api/sensor-ingest` · GET `/api/sensor-latest` | IoT ingest + live reading |
| GET  | `/api/dashboard-summary` · `/api/history` | Dashboard stats / activity log |
| POST | `/whatsapp` · `/sms` | Twilio webhooks |

Full list and request/response details: see [`prd.md` §9](prd.md).

---

## 📁 Project structure

```
smart-zameen-ai/
├── backend/
│   ├── app.py                       # Flask app (serves API + frontend locally)
│   ├── requirements.txt · Procfile
│   ├── database/db.py               # dual-mode: Neon Postgres OR SQLite
│   ├── routes/                      # crop, weather, whatsapp, sms, image, voice, sensor, chat
│   ├── virtual_sensor.py            # CLI virtual IoT node
│   └── models/
│       ├── local-trained-modal/     # crop_model.pkl, le_*.pkl, soil_classifier.pkl, soil_classes.json
│       └── crop-reccomendation-modal/  # soil.pkl, label_encoder.pkl (higher-accuracy model)
├── frontend/
│   ├── *.html                       # index, dashboard, crop-advisor, ai-agent, login/signup, …
│   ├── css/theme.css                # shared design system
│   └── js/                          # config.js (backend URL), lang, main, chat, camera, sidebar
├── model-training/                  # train_model.py, train_soil_cnn.py, dataset/
├── render.yaml                      # Render blueprint (backend)
├── prd.md                           # full spec + setup + deploy runbook
└── README.md
```

---

## 🚢 Deploy (Vercel + Render + Neon)

1. **Neon** → create a free Postgres, copy the connection string.
2. **Render** → New → Blueprint → pick the repo (uses `render.yaml`). Set env vars
   (`DATABASE_URL`, `OPENAI_API_KEY`, `WEATHER_API_KEY`, Twilio…). Note the Render URL.
3. **`frontend/js/config.js`** → set `BACKEND_URL` to that Render URL, commit.
4. **Vercel** → import the repo, **Root Directory = `frontend`**, deploy as a static site.

Step-by-step runbook (incl. Twilio webhooks and troubleshooting): [`prd.md` §12–14](prd.md).

---

## 🛠 Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML, CSS, vanilla JavaScript |
| Backend | Python, Flask (gunicorn in prod) |
| Database | Neon Postgres (prod) / SQLite (local) via `psycopg` |
| ML | scikit-learn (crop models + soil-image classifier), NumPy/SciPy |
| AI assistant | OpenAI — `gpt-4o-mini` (chat + vision), `whisper-1` (voice) |
| Weather | OpenWeatherMap | 
| WhatsApp/SMS | Twilio |

---

*SmartZameen AI — Pakistani Kisan ko Technology ki Taqat 🌾*
