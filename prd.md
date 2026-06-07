# SmartZameen AI — Product Requirements Document (PRD)

**Status:** Production-bound (frontend on Vercel · backend on Render · database on Neon)
**Last updated:** 2026-06-07
**Owner:** Faizan (omizzy786@gmail.com)

> This is the **single source of truth** for the project: product spec **and** the
> local-run / testing / deployment runbook. (It replaces the old separate
> `project-prd.md`, `PROJECT-GUIDE.md`, and `SETUP.md`.) For a quick public overview
> see `README.md`.

---

## 1. Summary

**SmartZameen AI** is a precision-agriculture web platform for Pakistani farmers. It turns
everyday field data — soil nutrients, a soil photo, the local weather, or a spoken/typed
question — into clear, actionable crop decisions, in **five regional languages** (Urdu,
Punjabi, Sindhi, Pashto, English), on any device.

The product combines:
- two **locally-trained / curated ML models** for crop recommendation,
- a **vision soil-classifier** that reads a soil photo,
- an **OpenAI-powered assistant** (chat + voice) that ties everything together in the
  farmer's own language,
- a **virtual IoT soil-sensor** layer (no hardware required), and
- **WhatsApp / SMS** access via Twilio.

---

## 2. Goals & non-goals

### Goals
1. Give an accurate, explainable **crop recommendation** from soil + climate inputs.
2. Let a farmer get advice **without literacy or typing** — via voice and WhatsApp.
3. Work on **low-end Android phones** and poor connections.
4. Use **real data only** — no mock/sample numbers shown to users.
5. Be **cheap to run** (free tiers: Vercel + Render + Neon).

### Non-goals (for this version)
- Native mobile apps (the web app is mobile-first instead).
- Real hardware sensor integration (the IoT layer is simulated, but the ingest API is
  hardware-ready).
- Marketplace / payments / e-commerce.
- User-to-user social features.

---

## 3. Personas

| Persona | Need | How the product serves it |
|---|---|---|
| **Smallholder farmer** (low literacy, Urdu/regional) | "What should I plant?" | Voice chat + WhatsApp bot + simple farmer-friendly form |
| **Progressive farmer / agronomist** | Data-driven decisions | Full soil form, IoT simulator, dashboard analytics, history |
| **Extension worker / NGO** | Advise many farmers | Multi-language UI, soil-photo analysis, shareable web app |

---

## 4. System architecture

```
                    ┌──────────────────────────┐
   Browser  ─────►  │  Vercel (static frontend)│   HTML/CSS/JS
   (Android/        │  index, dashboard, chat… │
    desktop)        └────────────┬─────────────┘
                                 │  HTTPS (CORS) — base URL from js/config.js
                                 ▼
                    ┌──────────────────────────┐
                    │  Render (Flask backend)  │   gunicorn app:app
                    │  /api/*  + auth routes   │
                    └───┬───────────┬──────────┘
                        │           │
            ┌───────────▼──┐   ┌────▼───────────────┐
            │ Neon Postgres│   │ External services  │
            │ users, preds,│   │ OpenAI (chat+voice)│
            │ sensors      │   │ OpenWeather, Twilio│
            └──────────────┘   └────────────────────┘
                        ▲
            ┌───────────┴───────────┐
            │ ML models (on disk)   │
            │ models/local-trained- │
            │ modal + crop-recc-…   │
            └───────────────────────┘
```

- **Frontend and backend are separate origins.** The single source of truth for the
  backend URL is **`frontend/js/config.js`** (`BACKEND_URL`). It auto-detects local dev
  (file://, localhost, served-by-Flask) and otherwise points at the Render backend.
- **One backend service** serves all `/api/*` routes and the auth routes. It can also
  serve the frontend statically when run locally (so local dev is single-origin).
- **Database is dual-mode:** if `DATABASE_URL` is set → **Neon Postgres**; if not → a
  local **SQLite** file (`backend/database/smartzameen.db`). Same code, no app changes.

### Tech stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla HTML + CSS + JS, shared design system in `frontend/css/theme.css` |
| Backend | Python + Flask (blueprints per feature), gunicorn in production |
| Database | Neon Postgres (prod) / SQLite (local) via `psycopg` |
| ML | scikit-learn (crop models + soil-image classifier), NumPy/SciPy, joblib |
| AI assistant | OpenAI — `gpt-4o-mini` (chat + vision), `whisper-1` (voice → text) |
| Weather | OpenWeatherMap |
| Messaging | Twilio (WhatsApp + SMS) |
| Hosting | Vercel (frontend), Render (backend), Neon (DB) |

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
├── model-training/                  # train_model.py, train_soil_cnn.py, dataset/
├── render.yaml                      # Render blueprint (backend)
├── prd.md                           # this document
└── README.md
```

---

## 5. Features (functional requirements)

### 5.1 Crop recommendation (core)
- **Inputs:** N, P, K, pH, temperature, rainfall, region, season; optional humidity.
- **Logic:** if humidity is provided → higher-accuracy **Kaggle crop-recommendation model**
  (`models/crop-reccomendation-modal/soil.pkl`, 22 crops). Otherwise → the **locally-trained
  model** (`models/local-trained-modal/crop_model.pkl`, region/season aware). If neither
  loads → transparent rule-based fallback.
- **Which model ran is reported and shown.** The API returns `model` (a human label) and
  `model_key` (`kaggle` / `random-forest` / `rule-based`), and the result card displays it
  as a badge. This makes the choice **explainable** — and explains why the *same* soil
  values can map to a different crop when humidity is/ isn't supplied (different model),
  rather than looking random. Each individual model is deterministic: identical inputs
  through the same model always give the same result.
- **Output:** best crop + confidence + top-3 alternatives, with Urdu names, season, best
  sowing time, water need, expected yield.
- **Persistence:** every prediction is saved to the `predictions` table (Neon).
- **API:** `POST /api/predict-crop`.

### 5.2 Soil image analysis (vision)
- Farmer uploads / captures a **soil photo**.
- A local CNN-feature + classifier (`models/local-trained-modal/soil_classifier.pkl`)
  detects the **soil type** and estimates **N/P/K and pH** from a soil-properties map.
- It **auto-fills only the soil-derived fields** (N/P/K/pH). Temperature & rainfall are
  environmental and are **not fabricated** — the farmer enters them.
- **API:** `POST /api/analyze-soil-image`.

### 5.3 AI assistant — chat + voice (OpenAI)
- A single chat (the **Crop Advisor** page, `ai-agent.html`) handles **text, image,
  attached files, and voice**, replying in the user's language.
- **Voice is part of the chat:** the mic records audio → `POST /api/transcribe`
  (**OpenAI Whisper**, accurate for Urdu/regional) → text → normal chat flow. Browser
  speech recognition is a fallback when recording isn't available; replies can be read
  aloud via the browser's speech synthesis.
- **API:** `POST /api/chat` (text/vision/file), `POST /api/transcribe` (speech-to-text).
- **Model:** OpenAI only. (Anthropic/Claude has been fully removed.)

### 5.4 Weather
- Real **OpenWeatherMap** data for 8 Pakistani cities: current conditions + 5-step forecast.
- **Real data only** — there is no mock fallback. If `WEATHER_API_KEY` is missing or the
  provider errors, the API returns `success:false` and the UI shows a neutral/empty state
  (never fake numbers).
- **API:** `GET /api/weather`, `GET /api/weather/forecast`, `GET /api/cities`.

### 5.5 IoT soil node (virtual + simulator)
- **Virtual sensor** (`backend/virtual_sensor.py`) and an **HTML simulator** (Crop Advisor
  → IoT Node page) both POST readings to `POST /api/sensor-ingest`, which runs the crop
  model and stores the reading in `sensor_readings` (Neon).
- The dashboard's **Connected Soil Node** tile polls `GET /api/sensor-latest` and shows the
  live reading + AI-suggested crop. Node IDs starting with `ESP` are tagged "hardware",
  so a real device can use the same ingest endpoint later.

### 5.6 Dashboard (real data)
- Real stats from Neon: total predictions, this-month count, average confidence, top crop.
- Real recent-predictions table, real weather card + forecast, live soil-node tile.
- No demo/placeholder values are shown — empty states read "—" / "no data yet".
- **API:** `GET /api/dashboard-summary`.

### 5.7 History
- Full activity log: every crop prediction and every IoT sensor reading, from Neon.
- **API:** `GET /api/history`.

### 5.8 WhatsApp / SMS bot (Twilio)
- Conversational crop advice over WhatsApp and SMS using the same crop model.
- **API (webhooks):** `POST /whatsapp`, `POST /sms`.

### 5.9 Auth & profile
- Email/password signup + login (SHA-256 hashed), stored in Neon `users`.
- Login & signup forms include a **show/hide password** toggle.
- Profile page (name, region, password). Region personalizes recommendations.
- **API:** `POST /signup`, `POST /login`, `GET /api/profile`, `POST /api/update-profile`.

### 5.10 Internationalization
- 5 languages with full RTL for Urdu/Punjabi/Sindhi/Pashto.
- A **globe language switcher** lives in the top-right header on every page and is always
  visible (it never collapses into the mobile hamburger). Choice persists across pages
  (`localStorage 'sz_lang'`, applied centrally in `js/lang.js`).

---

## 6. Non-functional requirements

| Area | Requirement |
|---|---|
| **Responsiveness** | Mobile-first; must look correct on small Android screens. Global CSS prevents horizontal overflow; grids/tables collapse; nav uses an off-canvas drawer. |
| **Performance** | First prediction < 2s on warm backend. (Render free tier sleeps after 15 min → first request is slower; acceptable for this stage.) |
| **Reliability** | Missing API keys degrade gracefully (clear errors), never crash the app. |
| **Data integrity** | Neon Postgres persists users/predictions/sensors across restarts & redeploys. |
| **Security** | Secrets only in environment variables / `.env` (gitignored). Passwords hashed. CORS enabled for the Vercel origin. |
| **Cost** | Runs entirely on free tiers (Vercel + Render + Neon + OpenAI pay-as-you-go). |

---

## 7. Data model (Neon Postgres / SQLite)

| Table | Key columns |
|---|---|
| `users` | id, name, email (unique), password (hash), region, created_at |
| `crops` | id, name (unique), urdu_name, season, min/max rain·temp·ph, region, description |
| `predictions` | id, nitrogen…rainfall, region, season, predicted_crop, confidence, created_at |
| `sensor_readings` | id, node_id, source, N/P/K, ph, temperature, rainfall, moisture, region, season, predicted_crop, received_at |
| `soil_data` | id, region, N/P/K, ph_value, recorded_at |

DDL is created idempotently on startup by `create_database()`, which runs at import time
(so it also runs under gunicorn) and is dialect-aware (Postgres vs SQLite).

---

## 8. External integrations & required env vars

| Service | Env var(s) | Used by |
|---|---|---|
| Neon Postgres | `DATABASE_URL` | all persistence |
| OpenAI | `OPENAI_API_KEY` (· `OPENAI_MODEL`, `OPENAI_WHISPER_MODEL`) | chat + voice |
| OpenWeatherMap | `WEATHER_API_KEY` | weather |
| Twilio | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE` | WhatsApp/SMS |

All are set in **Render** (backend) for production and in **`backend/.env`** for local dev.
`.env` is gitignored and must never be committed. The core app (crop prediction, IoT
simulator, dashboard, auth) runs **without any keys**; chat/voice need `OPENAI_API_KEY` and
the Weather page needs `WEATHER_API_KEY`.

---

## 9. API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/signup` | Create an account |
| POST | `/login` | Log in (returns a token) |
| GET  | `/api/profile` · POST `/api/update-profile` | Profile read / update |
| POST | `/api/predict-crop` | Crop recommendation from soil + climate (returns `model`/`model_key`) |
| GET  | `/api/crops` · `/api/crops/<name>` | Crop list / one crop's detail |
| POST | `/api/analyze-soil-image` | Soil-type + N/P/K/pH from a photo |
| POST | `/api/chat` | AI assistant (text / vision / file) |
| POST | `/api/transcribe` | Speech → text (OpenAI Whisper) |
| GET  | `/api/weather` · `/api/weather/forecast` · `/api/cities` | Weather (real only) |
| POST | `/api/sensor-ingest` | IoT reading ingest + live prediction |
| GET  | `/api/sensor-latest` · `/api/sensor-history` | Latest reading / recent readings |
| GET  | `/api/dashboard-summary` · `/api/history` | Dashboard stats / full activity log |
| POST | `/whatsapp` · `/sms` | Twilio webhooks |

---

## 10. Local setup & run

### 10.1 Prerequisites
- **Python 3.10+** (3.12 recommended; matches the Render runtime). Check: `python --version`.
- That's it for local dev — SQLite ships with Python, so no database server is needed.

### 10.2 Install dependencies (one time)
```powershell
cd backend
python -m venv venv
venv\Scripts\activate            # Windows  (source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
```
This installs Flask, scikit-learn, NumPy/SciPy, Pillow, joblib, **psycopg** (Postgres),
gunicorn, requests and Twilio.

### 10.3 Configure `backend/.env`
Copy `backend/.env.example` to `backend/.env` and fill in your values:
```
# Leave DATABASE_URL UNSET to use a local SQLite file (no setup).
# Set it to your Neon string to use Postgres locally too.
# DATABASE_URL=postgresql://USER:PASSWORD@ep-xxxx.neon.tech/neondb?sslmode=require

OPENAI_API_KEY=sk-...            # required for chat + voice
WEATHER_API_KEY=...             # required for the Weather page
TWILIO_ACCOUNT_SID=...           # optional: WhatsApp/SMS bot
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE=+14155238886
```
> `.env`: no spaces around `=`.

### 10.4 Run the backend (serves the API **and** the frontend locally)
```powershell
cd backend
python app.py            # http://localhost:80  (auto-falls back to :5000 if 80 is busy)
```
On first run you'll see the DB mode (`SQLite` or `Neon/Postgres`), `[OK] ML Model load ho gaya!`,
and the server URL. Open the printed URL — the frontend talks to the same-origin backend
automatically (`frontend/js/config.js` handles this).

| Page | URL |
|---|---|
| Landing | http://localhost:80/ |
| Login / Signup | /login.html · /signup.html |
| Dashboard | /dashboard.html |
| Crop Advisor (chat + voice + image) | /ai-agent.html |
| Crop prediction + IoT node | /crop-advisor.html |

> **Port 80 note (Windows):** `PermissionError` / `OSError 10013` means port 80 is taken —
> run the terminal as Administrator or close Skype/IIS; otherwise the app auto-falls back
> to port 5000.

### 10.5 Run the virtual IoT sensor (no hardware)
In a **second terminal** (keep the backend running):
```powershell
cd backend
venv\Scripts\activate
python virtual_sensor.py                 # stream a reading every 3s
python virtual_sensor.py --once          # one reading
python virtual_sensor.py --node ESP8266-A0   # show up as "hardware"
```
Open `/dashboard.html` → the **Connected Soil Node** tile goes *Live*. Every reading is
stored in `sensor_readings`. The HTML simulator on `/crop-advisor.html` does the same with
sliders.

---

## 11. Feature test checklist

Replace `BASE` with your local URL (`http://localhost:80` or `:5000`) or your Render URL.

### 11.1 Crop prediction (core ML)
```powershell
Invoke-RestMethod -Uri "$BASE/api/predict-crop" -Method Post -ContentType "application/json" `
  -Body '{"nitrogen":80,"phosphorus":40,"potassium":30,"ph":6.8,"temperature":24,"rainfall":150,"region":"Punjab","season":"rabi","humidity":60}'
```
**Expect:** a crop + confidence + `top3` + a `model`/`model_key` field naming which model
ran. The prediction is saved to the DB. (Drop `humidity` to see it fall back to the local
model — the `model` label changes accordingly.)

### 11.2 IoT simulator + virtual sensor
- HTML: `BASE/crop-advisor.html` → adjust sliders → **Transmit** → AI card fills in, with the
  model badge shown on the result.
- CLI: `python virtual_sensor.py --once`. `BASE/dashboard.html` shows it **Live**.

### 11.3 Dashboard (real data)
`BASE/dashboard.html` → stats, recent predictions, weather card and forecast load from the
API. Empty states show "—" (no fake numbers).

### 11.4 Weather (real only)
`Invoke-RestMethod "$BASE/api/weather?city=lahore"` → real temp/humidity/wind. Without
`WEATHER_API_KEY` it returns `success:false` (UI shows a neutral state).

### 11.5 Soil image analysis
`BASE/ai-agent.html` → send a soil **photo** in the chat → soil type + estimated N/P/K/pH.

### 11.6 AI chat + voice (OpenAI)
`BASE/ai-agent.html` → type a question (any of the 5 languages), send a crop/soil **photo**,
or tap the **mic** (audio → Whisper → text → reply). Needs `OPENAI_API_KEY`.

### 11.7 Auth
`BASE/signup.html` → create account (try the show-password toggle) → `BASE/login.html` →
log in → dashboard.

### 11.8 Languages
On any page, open the globe switcher (top-right) → pick Urdu/Punjabi/Sindhi/Pashto/English →
the page flips RTL/LTR and the choice persists across pages.

### 11.9 WhatsApp / SMS
Needs Twilio + a public URL (your Render URL, or ngrok locally). See §13.4.

---

## 12. Deployment — Vercel + Render + Neon

The frontend (Vercel) and backend (Render) are **separate origins**; the database is **Neon**.

### 12.1 Database — Neon Postgres (free)
1. Create a project at **neon.tech** → copy the **connection string**
   (`postgresql://…?sslmode=require`).
2. Paste it into Render as `DATABASE_URL` (step 12.2). Tables are created automatically on
   first backend start.

### 12.2 Backend — Render (free)
1. Push the repo to GitHub. Ensure `backend/models/**` is committed (the `.pkl` files are
   needed at runtime — well under GitHub limits).
2. Render → **New → Blueprint** → pick the repo (it reads **`render.yaml`** automatically:
   root `backend`, build `pip install -r requirements.txt`, start `gunicorn app:app`).
3. In the Render dashboard set the env vars (all `sync:false` in the blueprint):
   `DATABASE_URL`, `OPENAI_API_KEY`, `WEATHER_API_KEY`, `TWILIO_ACCOUNT_SID`,
   `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE`.
4. Deploy. Note your backend URL: `https://<your-app>.onrender.com`.

> **Free-tier notes:** the service sleeps after ~15 min idle (first request is slow), and
> 512 MB RAM is tight with the models — upgrade to **Starter** if it OOMs. Neon keeps data
> persistent regardless.

### 12.3 Frontend — Vercel (free)
1. Edit **`frontend/js/config.js`** → set `BACKEND_URL` to your Render URL → commit & push.
2. Vercel → **New Project** → import the repo → set **Root Directory = `frontend`** →
   framework preset **Other** (static) → Deploy.
3. Visit your Vercel URL. It calls the Render backend (CORS is already enabled).

### 12.4 Twilio WhatsApp / SMS webhooks
After the backend is public:
1. Twilio Console → WhatsApp Sandbox / Messaging.
2. Set the inbound webhook to `https://<your-app>.onrender.com/whatsapp` (and `/sms`).
3. For local testing use `ngrok http 80` and point the webhook at the ngrok HTTPS URL.

### 12.5 How the frontend resolves the backend URL
`frontend/js/config.js` is the single source of truth. It uses `http://localhost:5000` when
opened as a `file://`, same-origin when served by Flask locally, and otherwise `BACKEND_URL`
(your Render URL — i.e. on Vercel). Every page loads `config.js` first, and every API call is
routed through it.

---

## 13. Retraining the models

```powershell
cd model-training
python train_model.py        # → backend/models/local-trained-modal/crop_model.pkl + encoders
python train_soil_cnn.py     # (optional) → soil_classifier.pkl
```
Restart the backend to load new artifacts. Keep the scikit-learn version close to the one in
`requirements.txt` so the pickles load cleanly.

---

## 14. Troubleshooting

| Symptom | Cause / Fix |
|---------|-------------|
| `ModuleNotFoundError: flask` / `psycopg` | Activate the venv and `pip install -r requirements.txt` in `backend/`. |
| Vercel site loads but API calls fail | `BACKEND_URL` in `frontend/js/config.js` not set to the Render URL (or Render is asleep — retry after ~30s). |
| `[OK] Database ready! (SQLite)` in prod | `DATABASE_URL` not set on Render → set the Neon string and redeploy. |
| Chat/voice error "OpenAI API key not set" | Add `OPENAI_API_KEY` on Render (and `backend/.env` locally). |
| Weather shows "—" | `WEATHER_API_KEY` missing — real data only, no mock. |
| Model-load warning at startup | Harmless sklearn version notice; the model still predicts. Retrain to silence. |
| `ModuleNotFoundError: 'your_application'` on Render | Default start command is running. Set **Start Command** to `gunicorn app:app --bind 0.0.0.0:$PORT` and **Root Directory** to `backend` (or redeploy via the Blueprint). |
| WhatsApp messages never arrive | Twilio webhook must point at the public Render URL, not localhost. |
| Virtual sensor `[OFFLINE]` | Start the backend first, then run the sensor. |
| Want a clean local DB | Stop the backend, delete `backend/database/smartzameen.db` (SQLite only). |

---

## 15. Pre-deploy checklist

- [ ] `pip install -r requirements.txt` succeeds in a fresh venv
- [ ] `python app.py` boots, prints `[OK] ML Model load ho gaya!` and the DB mode
- [ ] Crop prediction, dashboard, weather, chat all work locally (§11)
- [ ] `backend/models/**` committed to git
- [ ] Neon `DATABASE_URL` + all API keys set in Render env (not committed)
- [ ] `frontend/js/config.js` → `BACKEND_URL` = Render URL
- [ ] Frontend deployed on Vercel (Root Directory = `frontend`)
- [ ] Twilio webhooks point at the public Render URL (if using WhatsApp/SMS)
- [ ] Any credentials shared during development have been rotated

---

## 16. What changed in the production refactor (June 2026)

- **Database:** SQLite → **Neon Postgres** (dual-mode; SQLite kept for local dev).
- **AI provider:** consolidated to **OpenAI only**; **Anthropic/Claude removed everywhere**.
- **Voice:** moved into the main chat and switched to **OpenAI Whisper** speech-to-text;
  the standalone Anthropic voice assistant and `js/voice.js` were removed.
- **Mock/dummy data removed:** weather no longer returns fake numbers; the soil-image route
  no longer fabricates temperature/rainfall; dashboard placeholders show "—" until real
  data loads; leftover demo strings (sample user/yield/area) were stripped from `js/lang.js`.
- **Explainable model choice:** the crop API now returns which model ran (`model`/`model_key`)
  and the result card shows it as a badge.
- **Auth UX:** login & signup got a show/hide password toggle.
- **Vercel/Render split:** introduced `frontend/js/config.js` and routed every frontend
  fetch through the configured backend base.
- **Model folder** reorganized to `backend/models/{local-trained-modal, crop-reccomendation-modal}`.
- **Language switcher** moved to an always-visible globe in the header; full mobile/Android
  responsive pass; saved-language application centralized in `js/lang.js`.
- **Docs consolidated:** `project-prd.md` + `PROJECT-GUIDE.md` + `SETUP.md` merged into this
  single `prd.md`.

---

## 17. Open items / future work

- Move TTS replies to **OpenAI TTS** (currently browser speech synthesis).
- Make OpenAI **orchestrate the ML models as tools** (one agent that calls crop/soil models).
- Add a **Render Disk or connection pooling** if traffic grows.
- Rotate any credentials that were shared during development.
- Optional: persistent auth tokens / sessions instead of localStorage flags.

---

*SmartZameen AI — Pakistani Kisan ko Technology ki Taqat 🌾*
