# SmartZameen AI — Product Requirements Document (PRD)

**Status:** Production-bound (frontend on Vercel · backend on Render · database on Neon)
**Last updated:** 2026-06-07
**Owner:** Faizan (omizzy786@gmail.com)

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

---

## 5. Features (functional requirements)

### 5.1 Crop recommendation (core)
- **Inputs:** N, P, K, pH, temperature, rainfall, region, season; optional humidity.
- **Logic:** if humidity is provided → higher-accuracy **Kaggle crop-recommendation model**
  (`models/crop-reccomendation-modal/soil.pkl`, 22 crops). Otherwise → the **locally-trained
  model** (`models/local-trained-modal/crop_model.pkl`, region/season aware). If neither
  loads → transparent rule-based fallback.
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
- A single chat (the **Crop Advisor** page) handles **text, image, attached files, and
  voice**, replying in the user's language.
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
  → IoT tab) both POST readings to `POST /api/sensor-ingest`, which runs the crop model and
  stores the reading in `sensor_readings` (Neon).
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
- Profile page (name, region, password). Region personalizes recommendations.
- **API:** `POST /signup`, `POST /login`, `GET /api/profile`, `POST /api/update-profile`.

### 5.10 Internationalization
- 5 languages with full RTL for Urdu/Punjabi/Sindhi/Pashto.
- A **globe language switcher** lives in the top-right header on every page and is always
  visible (it never collapses into the mobile hamburger). Choice persists across pages.

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

## 7. Data model (Neon Postgres)

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
`.env` is gitignored and must never be committed.

---

## 9. Deployment

- **Frontend → Vercel:** deploy the `frontend/` directory as a static site. Set
  `BACKEND_URL` in `frontend/js/config.js` to the Render backend URL before/after deploy.
- **Backend → Render:** `render.yaml` blueprint (root `backend`, `gunicorn app:app`).
  Set all env vars (incl. `DATABASE_URL`) in the Render dashboard.
- **Database → Neon:** create a free Postgres project, copy the connection string into
  `DATABASE_URL`.
- **Python:** pinned to 3.12 on Render (`PYTHON_VERSION`) for stable ML wheels.

See `PROJECT-GUIDE.md` for the step-by-step deploy + test runbook.

---

## 10. What changed in the production refactor (June 2026)

- **Database:** SQLite → **Neon Postgres** (dual-mode; SQLite kept for local dev).
- **AI provider:** consolidated to **OpenAI only**; **Anthropic/Claude removed everywhere**.
- **Voice:** moved into the main chat and switched to **OpenAI Whisper** speech-to-text;
  the standalone Anthropic voice assistant and `js/voice.js` were removed.
- **Mock/dummy data removed:** weather no longer returns fake numbers; the soil-image route
  no longer fabricates temperature/rainfall; dashboard placeholders show "—" until real
  data loads.
- **Vercel/Render split:** introduced `frontend/js/config.js` and routed every frontend
  fetch through the configured backend base (no more relative-URL assumptions).
- **Model folder** reorganized to `backend/models/{local-trained-modal, crop-reccomendation-modal}`;
  the backend resolves paths against the new layout (with a legacy fallback).
- **Language switcher** moved to an always-visible globe in the header; full mobile/Android
  responsive pass.

---

## 11. Open items / future work

- Move TTS replies to **OpenAI TTS** (currently browser speech synthesis).
- Make OpenAI **orchestrate the ML models as tools** (one agent that calls crop/soil models).
- Add a **Render Disk or connection pooling** if traffic grows.
- Rotate any credentials that were shared during development.
- Optional: persistent auth tokens / sessions instead of localStorage flags.
