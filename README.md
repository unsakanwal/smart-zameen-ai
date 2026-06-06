# 🌾 SmartZameen AI — Smart Agriculture System

An AI-powered crop recommendation system for Pakistani farmers. Soil data enter karo, image upload karo, ya voice mein baat karo, aur payen best crop suggestion, mausam ki report, aur WhatsApp/SMS par bhi madad!

---

## 📁 Project Structure

```
smart-zameen-ai/
├── backend/
│   ├── app.py                   ← Flask server (main entry point)
│   ├── .env                     ← API keys (Anthropic, Weather, Twilio)
│   ├── requirements.txt         ← Python dependencies
│   ├── database/
│   │   └── db.py                ← SQLite setup & queries (zero-config)
│   ├── routes/
│   │   ├── crop_routes.py       ← Crop prediction API (ML model)
│   │   ├── weather_routes.py    ← Weather API (OpenWeatherMap)
│   │   ├── whatsapp_routes.py   ← WhatsApp chatbot (Twilio)
│   │   ├── sms_routes.py        ← SMS chatbot (Twilio)
│   │   ├── image_routes.py      ← Soil image analysis (Claude Vision)
│   │   ├── voice_routes.py      ← Voice AI chat (Claude Haiku)
│   │   └── sensor_routes.py     ← IoT sensor ingest + live prediction
│   ├── virtual_sensor.py        ← CLI virtual IoT node (no hardware needed)
│   └── ml_models/               ← Trained ML model files (.pkl)
│       ├── crop_model.pkl
│       ├── le_crop.pkl
│       ├── le_season.pkl
│       └── le_region.pkl
├── frontend/
│   ├── index.html               ← Landing page
│   ├── index.html               ← Portfolio / landing page
│   ├── dashboard.html           ← App hub: real stats, weather, live soil node
│   ├── crop-advisor.html        ← Crop AI + IoT sensors (merged, tabbed)
│   ├── login.html / signup.html ← Auth pages
│   ├── assets/
│   │   ├── favicon.svg          ← App favicon
│   │   └── images/              ← All images (hero, soil, farm, dashboard)
│   ├── css/
│   │   └── theme.css            ← Shared design system (tokens + components)
│   └── js/
│       ├── main.js              ← API calls & prediction logic
│       ├── lang.js              ← Multi-language support (5 languages)
│       ├── camera.js            ← Camera / soil image upload
│       └── voice.js             ← Voice chat (Web Speech API + Claude)
├── model-training/
│   ├── train_model.py           ← Crop model training script
│   ├── train_soil_cnn.py        ← Soil image classifier training
│   └── dataset/
│       └── crops_pakistan.csv   ← Pakistan crops training dataset
├── README.md
└── PROJECT-GUIDE.md             ← Full testing + deployment guide
```

---

## ✨ Features — Poori List

### 1️⃣ AI Crop Recommendation (ML Model)
- Random Forest model se best crop predict karta hai
- Input: nitrogen, phosphorus, potassium, pH, temperature, rainfall, region, season
- Output: top-3 crop suggestions with confidence %
- Fallback: agar model load na ho to rule-based logic
- Predictions MySQL database mein save hoti hain

### 2️⃣ Soil Image Analysis (Claude Vision AI)
- Zameen ki photo upload karo — AI soil type detect kar deta hai
- Automatically estimate karta hai: NPK values, pH, moisture, soil color
- Urdu mein description bhi milti hai
- Camera direct bhi use kar sakte hain (camera.js)
- Uses: `claude-opus-4-5` vision model

### 3️⃣ Voice AI Chat (Claude Haiku)
- Microphone se baat karo — AI jawab deta hai
- 5 languages support: Urdu, Punjabi, Sindhi, Pashto, English
- Web Speech API se speech-to-text aur text-to-speech
- Short, farmer-friendly replies
- Uses: `claude-haiku-4-5-20251001` model

### 4️⃣ Weather System (OpenWeatherMap)
- Real-time mausam: temperature, humidity, wind speed, rainfall
- 5-din ka forecast
- 8 Pakistani cities support: Lahore, Karachi, Multan, Peshawar, Quetta, Faisalabad, Islamabad, Hyderabad
- Agar API key nahi to mock data automatically use hota hai

### 5️⃣ WhatsApp Chatbot (Twilio)
- WhatsApp pe number bhejo, fasal ki advice payen
- 5 easy questions: region, season, soil, water source, previous crop
- 5 languages: Urdu, English, Punjabi, Sindhi, Pashto
- Menu options: crop recommendation / weather / crops list
- Session management: har user ka alag session

### 6️⃣ SMS Chatbot (Twilio)
- WhatsApp chatbot jaisa hi — sirf SMS channel alag hai
- Same 5-language support
- Endpoint: `/sms`

### 7️⃣ Multi-Language Support (5 Languages)
- Urdu (default), English, Punjabi, Sindhi, Pashto
- Frontend aur WhatsApp/SMS dono mein kaam karta hai
- Language switch: navbar se ya WhatsApp mein `en` / `ur` / `pa` / `sd` / `ps` likhein

### 8️⃣ User Auth (Login / Signup)
- MySQL mein users table
- SHA-256 password hashing
- Simple token system

---

## ⚙️ Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.8+ | https://python.org |
| MySQL | 8.0+ | https://dev.mysql.com |
| pip | latest | comes with Python |

---

## 🔑 API Keys — Kya Kya Chahiye

| Service | Kahan Use Hota Hai | Kahan Se Lein |
|---------|-------------------|---------------|
| `ANTHROPIC_API_KEY` | Soil image analysis + Voice chat | https://console.anthropic.com |
| `WEATHER_API_KEY` | Real mausam data | https://openweathermap.org/api |
| `TWILIO_ACCOUNT_SID` | WhatsApp + SMS | https://twilio.com |
| `TWILIO_AUTH_TOKEN` | WhatsApp + SMS | https://twilio.com |
| `TWILIO_PHONE` | WhatsApp + SMS sender number | https://twilio.com |

---

## 🚀 Setup & Run — Step by Step

### Step 1 — Project Download Karein

```bash
# Git se clone karein
git clone <your-repo-url>
cd SmartZameen-AI

# Ya zip unzip karein
```

---

### Step 2 — MySQL Database Configure Karein

MySQL service start karein. Phir `backend/database/db.py` mein apna password update karein:

```python
DB_CONFIG = {
    'host':     'localhost',
    'user':     'root',
    'password': 'YourPasswordHere',   # ← yahan apna password likhein
    'database': 'smart_agriculture',
}
```

---

### Step 3 — Virtual Environment Banayein

```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

---

### Step 4 — Dependencies Install Karein

```bash
pip install -r requirements.txt
```

Agar `requirements.txt` kaam na kare:

```bash
pip install flask flask-cors pymysql scikit-learn pandas numpy joblib python-dotenv requests twilio anthropic
```

---

### Step 5 — API Keys Set Karein

`.env` file banayein `backend/` folder mein (ya existing `.env` update karein):

```
ANTHROPIC_API_KEY=your_anthropic_key_here
WEATHER_API_KEY=your_openweather_key_here
TWILIO_ACCOUNT_SID=your_twilio_sid_here
TWILIO_AUTH_TOKEN=your_twilio_token_here
TWILIO_PHONE=+14155238886
```

> ⚠️ `.env` mein `=` ke aage peechhe spaces mat rakhein.

---

### Step 6 — Flask Server Start Karein

```bash
# backend/ folder mein hona chahiye, venv active ho
python app.py
```

Yeh dikhega:

```
=============================================
🌾  SmartZameen Backend
=============================================
📦 Database setup...
✅ Database ready!
✅ Anthropic API key ready!
🚀 Server: http://localhost:80
=============================================
```

---

### Step 7 — App Kholein

Browser mein jayen:

```
http://localhost:80
```

---

## 🌐 Available Pages

| Page | URL |
|------|-----|
| Home (portfolio) | http://localhost:80 |
| Dashboard (app hub) | http://localhost:80/dashboard.html |
| Crop Advisor (Crop AI + IoT) | http://localhost:80/crop-advisor.html |
| Login | http://localhost:80/login.html |
| Sign Up | http://localhost:80/signup.html |

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/signup` | Naya account banayein |
| POST | `/login` | Login karein |
| POST | `/api/predict-crop` | Soil data se crop predict |
| GET | `/api/crops` | Tamam crops ki list |
| GET | `/api/crops/<name>` | Kisi ek crop ki detail |
| GET | `/api/weather?city=multan` | Real-time mausam |
| GET | `/api/weather/forecast?city=lahore` | 5-din forecast |
| GET | `/api/cities` | Supported cities ki list |
| POST | `/api/analyze-soil-image` | Soil image analyze (Claude Vision) |
| POST | `/api/voice-chat` | Voice/text AI chat (Claude Haiku) |
| POST | `/whatsapp` | WhatsApp chatbot webhook (Twilio) |
| POST | `/sms` | SMS chatbot webhook (Twilio) |

---

## 📲 WhatsApp / SMS Setup (Twilio)

1. Twilio account banayein: https://twilio.com
2. WhatsApp Sandbox activate karein
3. Webhook URL set karein: `https://your-domain.com/whatsapp`
4. SMS ke liye: `https://your-domain.com/sms`
5. `.env` mein credentials daalein

Local testing ke liye **ngrok** use karein:

```bash
ngrok http 80
# Phir Twilio mein ngrok URL set karein
```

---

## 🌍 Supported Languages

| Code | Language | Script |
|------|----------|--------|
| `ur` | Urdu (default) | اردو |
| `en` | English | English |
| `pa` | Punjabi | پنجابی |
| `sd` | Sindhi | سنڌي |
| `ps` | Pashto | پښتو |

---

## ❗ Common Issues & Fixes

### "Cannot reach server" on Login/Signup
- `python app.py` terminal mein chal raha ho
- Port 80 firewall mein block na ho (ya port change karein `app.py` mein)

### Database connection error
- MySQL service running hai?
- `db.py` mein password sahi hai?

### ML model not found error
- `backend/ml_models/` folder mein `.pkl` files honi chahiyein — yeh already zip mein hain
- Agar nahin hain to: `python model-training/train_model.py`

### Soil image / Voice chat kaam nahi kar raha
- `ANTHROPIC_API_KEY` set hai? Check karein: `echo %ANTHROPIC_API_KEY%` (Windows) ya `echo $ANTHROPIC_API_KEY` (Linux/Mac)

### WhatsApp messages nahi aa rahe
- Twilio webhook URL sahi set hai?
- `ngrok` ya public server use karein — localhost pe Twilio reach nahi kar sakta

### `.env` parse warning
- Spaces mat rakhein `=` ke aagey peechhe
- Sahi: `API_KEY=abc123`
- Galat: `API_KEY = abc123`

### Port already in use
```bash
# Windows:
netstat -ano | findstr :80
taskkill /PID <PID> /F

# Mac/Linux:
lsof -ti:80 | xargs kill
```

---

## 👩‍💻 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, Flask |
| Database | MySQL (via PyMySQL) |
| ML Model | Scikit-learn (Random Forest) |
| Soil Image AI | Anthropic Claude Vision (claude-opus-4-5) |
| Voice AI | Anthropic Claude Haiku (claude-haiku-4-5-20251001) |
| Weather | OpenWeatherMap API |
| WhatsApp/SMS | Twilio |
| Speech | Web Speech API (browser built-in) |

---

## 📞 Support

Terminal output zaroor check karein — Flask detailed error messages print karta hai. Aksar wahan se problem ka pata chal jata hai.

---

*SmartZameen AI — Pakistani Kisan ko Technology ki Taqat 🌾*