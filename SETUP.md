# SmartZameen AI — Setup & Run Guide

AI crop-recommendation platform for Pakistani farmers.

- **Frontend:** plain HTML/CSS/JS (deployed on **Vercel**).
- **Backend:** Flask + scikit-learn (deployed on **Render**).
- **Database:** **Neon Postgres** in production; **SQLite** locally (zero setup).
- **AI:** **OpenAI** powers chat + voice (Whisper). Weather via OpenWeather, bots via Twilio.

> Run locally with one backend that **also serves the frontend** (single origin), so you
> don't need Vercel for development.

---

## 1. Prerequisites

- **Python 3.10+** (3.12 recommended; matches the Render runtime). Check: `python --version`
- That's it for local dev — SQLite ships with Python, so you don't need a database server.

---

## 2. Install dependencies (one time)

```powershell
cd c:\Users\Faizan\Desktop\smart-zameen-ai\backend
python -m venv venv
venv\Scripts\activate            # Windows  (source venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
```

This installs Flask, scikit-learn, NumPy/SciPy, Pillow, joblib, **psycopg** (Postgres),
gunicorn, requests and Twilio.

---

## 3. Configure `backend/.env`

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

> The core app (crop prediction, IoT simulator, dashboard, auth) runs without any keys.
> Chat/voice need `OPENAI_API_KEY`; the Weather page needs `WEATHER_API_KEY`.

---

## 4. Run the backend (serves the API + the frontend)

```powershell
cd c:\Users\Faizan\Desktop\smart-zameen-ai\backend
python app.py
```

On first run you'll see:

```
SmartZameen Backend
[OK] Database ready! (SQLite)        <- or "(Neon/Postgres)" if DATABASE_URL is set
[OK] ML Model load ho gaya!
[OK] OpenAI API key ready!
Server: http://localhost:80          <- falls back to :5000 if port 80 is busy
```

Open the printed URL:

| Page | URL |
|---|---|
| Landing | http://localhost:80/ |
| Login / Signup | http://localhost:80/login.html · /signup.html |
| Dashboard | http://localhost:80/dashboard.html |
| Crop Advisor (chat + voice + image) | http://localhost:80/ai-agent.html |
| Crop prediction + IoT simulator | http://localhost:80/crop-advisor.html |

> **Port 80 note (Windows):** `PermissionError` / `OSError 10013` means port 80 is taken —
> run the terminal as Administrator or close Skype/IIS; otherwise the app auto-falls back to
> port 5000. Open whatever URL it prints.

When opened via `http://localhost`, the frontend talks to the same-origin backend
automatically (`frontend/js/config.js` handles this).

---

## 5. Run the virtual IoT sensor (no hardware)

In a **second terminal** (keep the backend running):

```powershell
cd c:\Users\Faizan\Desktop\smart-zameen-ai\backend
venv\Scripts\activate
python virtual_sensor.py                 # stream a reading every 3s
python virtual_sensor.py --once          # one reading
python virtual_sensor.py --node ESP8266-A0   # show up as "hardware"
```

Open **http://localhost:80/dashboard.html** → the **Connected Soil Node** tile goes *Live*.
Every reading is stored in the database (`sensor_readings`). The HTML simulator on
`/crop-advisor.html` (IoT tab) does the same thing with sliders.

---

## 6. Use Neon Postgres locally (optional)

To test against the real production database from your machine, set `DATABASE_URL` in
`backend/.env` to your Neon connection string and restart. You'll see
`[OK] Database ready! (Neon/Postgres)`. Tables are created automatically on first run.

---

## 7. Deploy

See **`PROJECT-GUIDE.md` §Deployment** for the full Vercel + Render + Neon runbook.
Short version:

1. **Neon** → create a free Postgres, copy the connection string.
2. **Render** → New → Blueprint → pick the repo (uses `render.yaml`). Set env vars
   (`DATABASE_URL`, `OPENAI_API_KEY`, `WEATHER_API_KEY`, Twilio…). Note the Render URL.
3. **`frontend/js/config.js`** → set `BACKEND_URL` to that Render URL, commit.
4. **Vercel** → deploy the `frontend/` directory as a static site.

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'flask'` / `psycopg` | Activate the venv and `pip install -r requirements.txt` in `backend/`. |
| `[OK] Database ready! (SQLite)` but you wanted Neon | `DATABASE_URL` isn't set — add it to `backend/.env` and restart. |
| Chat/voice says "OpenAI API key not set" | Add `OPENAI_API_KEY` to `backend/.env`. |
| Weather shows "—" / unavailable | Add `WEATHER_API_KEY` (real data only — there is no mock). |
| Frontend on Vercel can't reach the API | Set `BACKEND_URL` in `frontend/js/config.js` to your Render URL and redeploy. |
| Model load warning at startup | Harmless sklearn version notice; the model still predicts. |
| Virtual sensor `[OFFLINE]` | Start the backend first, then run the sensor. |
| Want a clean local DB | Stop the backend, delete `backend/database/smartzameen.db` (SQLite only). |
