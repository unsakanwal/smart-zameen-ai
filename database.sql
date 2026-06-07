-- ============================================================
--  SmartZameen AI — Neon Postgres schema (run ONCE)
-- ============================================================
--  You do NOT strictly need to run this: the backend creates these tables
--  automatically on first startup (create_database() in backend/database/db.py).
--  But running it once in the Neon SQL console gives you the schema up-front
--  and is safe to run again (every statement is idempotent).
--
--  How to run:
--    Neon dashboard → your project → "SQL Editor" → paste this whole file → Run.
-- ============================================================

-- Users (auth + profile)
CREATE TABLE IF NOT EXISTS users (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT UNIQUE NOT NULL,
    password   TEXT NOT NULL,
    region     TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reference crop catalogue (growing conditions)
CREATE TABLE IF NOT EXISTS crops (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    urdu_name   TEXT,
    season      TEXT,
    min_rain    REAL, max_rain REAL,
    min_temp    REAL, max_temp REAL,
    min_ph      REAL, max_ph   REAL,
    region      TEXT,
    description TEXT
);

-- Every crop prediction made through the app
CREATE TABLE IF NOT EXISTS predictions (
    id             SERIAL PRIMARY KEY,
    nitrogen       REAL, phosphorus REAL,
    potassium      REAL, ph         REAL,
    temperature    REAL, rainfall   REAL,
    region         TEXT, season     TEXT,
    predicted_crop TEXT,
    confidence     REAL,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Optional manual soil entries
CREATE TABLE IF NOT EXISTS soil_data (
    id          SERIAL PRIMARY KEY,
    region      TEXT,
    nitrogen    REAL, phosphorus REAL,
    potassium   REAL, ph_value   REAL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- IoT soil-sensor readings (virtual sensor / simulator / future hardware)
CREATE TABLE IF NOT EXISTS sensor_readings (
    id             SERIAL PRIMARY KEY,
    node_id        TEXT, source TEXT,
    nitrogen       REAL, phosphorus REAL, potassium REAL, ph REAL,
    temperature    REAL, rainfall   REAL, moisture  REAL,
    region         TEXT, season     TEXT,
    predicted_crop TEXT,
    received_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed the reference crop catalogue (skips rows that already exist)
INSERT INTO crops (name, urdu_name, season, min_rain, max_rain, min_temp, max_temp, min_ph, max_ph, region, description) VALUES
    ('Wheat',     'گندم',  'rabi',   40,  100, 10, 25, 6.0, 7.5, 'Punjab',       'Sardi ki fasal'),
    ('Rice',      'چاول',  'kharif', 150, 300, 20, 35, 5.5, 7.0, 'Punjab,Sindh', 'Pani wali zameen'),
    ('Maize',     'مکئی',  'kharif', 60,  110, 18, 32, 5.8, 7.5, 'KPK,Punjab',   'KPK ki fasal'),
    ('Cotton',    'کپاس',  'kharif', 50,  100, 20, 38, 6.0, 8.0, 'Punjab,Sindh', 'Naqdi fasal'),
    ('Sugarcane', 'گنا',   'kharif', 100, 200, 20, 35, 6.0, 7.5, 'Punjab',       'Cheeni ke liye'),
    ('Mustard',   'سرسوں', 'rabi',   25,  60,  8,  25, 6.0, 7.5, 'Punjab,Sindh', 'Tail wali fasal'),
    ('Chickpea',  'چنے',   'rabi',   20,  40,  10, 25, 6.0, 8.0, 'Balochistan',  'Khuski zameen'),
    ('Mango',     'آم',    'kharif', 75,  200, 24, 40, 5.5, 7.5, 'Punjab,Sindh', 'Phal')
ON CONFLICT (name) DO NOTHING;
