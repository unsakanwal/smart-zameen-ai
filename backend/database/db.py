"""
db.py  —  SQLite data layer for SmartZameen AI

Switched from MySQL to SQLite: zero setup, zero server, zero cost. The whole
database is a single file (smartzameen.db) created automatically next to this
module on first run. Nothing to install — sqlite3 ships with Python.

Public API is unchanged so the rest of the app needs no edits:
    get_connection()    -> a DB connection (dict-style rows) or None
    create_database()   -> creates tables + seeds sample crops (idempotent)
    save_prediction()   -> store one crop prediction
    get_all_crops()     -> list[dict] of seeded crops
    save_sensor_reading() -> persist one IoT soil-sensor reading (NEW)

Compatibility shim: existing code uses MySQL-style "%s" placeholders. The
cursor below transparently rewrites "%s" -> "?" so that raw SQL in app.py keeps
working untouched.
"""

import sqlite3
import os

# .env is optional now (only used for API keys elsewhere). Never let a missing
# python-dotenv break the database layer.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Single-file database, created on demand right next to this module.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smartzameen.db')


class _Cursor(sqlite3.Cursor):
    """Cursor that accepts MySQL-style %s placeholders (rewritten to ?)."""
    def execute(self, sql, params=()):
        return super().execute(sql.replace('%s', '?'), params)

    def executemany(self, sql, seq):
        return super().executemany(sql.replace('%s', '?'), seq)


class _Connection(sqlite3.Connection):
    def cursor(self, factory=_Cursor):
        return super().cursor(factory)


def get_connection():
    """Return a SQLite connection with dict-style rows, or None on failure."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5, factory=_Connection)
        conn.row_factory = sqlite3.Row        # rows behave like dicts: row['name']
        return conn
    except Exception as e:
        print(f"Database Error: {e}")
        return None


def create_database():
    """Create all tables (idempotent) and seed sample crops."""
    conn = get_connection()
    if not conn:
        print("[WARNING] SQLite database khol nahi saka")
        return
    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                email      TEXT UNIQUE NOT NULL,
                password   TEXT NOT NULL,
                region     TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crops (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                urdu_name   TEXT,
                season      TEXT,
                min_rain    REAL, max_rain REAL,
                min_temp    REAL, max_temp REAL,
                min_ph      REAL, max_ph   REAL,
                region      TEXT,
                description TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                nitrogen       REAL, phosphorus REAL,
                potassium      REAL, ph         REAL,
                temperature    REAL, rainfall   REAL,
                region         TEXT, season     TEXT,
                predicted_crop TEXT,
                confidence     REAL,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS soil_data (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                region      TEXT,
                nitrogen    REAL, phosphorus REAL,
                potassium   REAL, ph_value   REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # NEW: persistent log of IoT soil-sensor readings (virtual sensor / simulator).
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                node_id        TEXT, source TEXT,
                nitrogen       REAL, phosphorus REAL, potassium REAL, ph REAL,
                temperature    REAL, rainfall   REAL, moisture  REAL,
                region         TEXT, season     TEXT,
                predicted_crop TEXT,
                received_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        insert_sample_crops(cursor)
        conn.commit()
        cursor.close()
        conn.close()
        print("[OK] Database aur tables tayar hain!")

    except Exception as e:
        print(f"[WARNING] Database error: {e}")


def insert_sample_crops(cursor):
    crops = [
        ('Wheat',     'گندم', 'rabi',   40,  100, 10, 25, 6.0, 7.5, 'Punjab',        'Sardi ki fasal'),
        ('Rice',      'چاول', 'kharif', 150, 300, 20, 35, 5.5, 7.0, 'Punjab,Sindh',  'Pani wali zameen'),
        ('Maize',     'مکئی', 'kharif', 60,  110, 18, 32, 5.8, 7.5, 'KPK,Punjab',    'KPK ki fasal'),
        ('Cotton',    'کپاس', 'kharif', 50,  100, 20, 38, 6.0, 8.0, 'Punjab,Sindh',  'Naqdi fasal'),
        ('Sugarcane', 'گنا',  'kharif', 100, 200, 20, 35, 6.0, 7.5, 'Punjab',        'Cheeni ke liye'),
        ('Mustard',   'سرسوں','rabi',   25,  60,  8,  25, 6.0, 7.5, 'Punjab,Sindh',  'Tail wali fasal'),
        ('Chickpea',  'چنے',  'rabi',   20,  40,  10, 25, 6.0, 8.0, 'Balochistan',   'Khuski zameen'),
        ('Mango',     'آم',   'kharif', 75,  200, 24, 40, 5.5, 7.5, 'Punjab,Sindh',  'Phal'),
    ]
    # INSERT OR IGNORE = SQLite equivalent of MySQL's INSERT IGNORE.
    cursor.executemany("""
        INSERT OR IGNORE INTO crops
        (name, urdu_name, season, min_rain, max_rain,
         min_temp, max_temp, min_ph, max_ph, region, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, crops)
    print("[OK] Sample crops data ready!")


def save_prediction(data, predicted_crop, confidence):
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO predictions
            (nitrogen, phosphorus, potassium, ph,
             temperature, rainfall, region, season,
             predicted_crop, confidence)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data.get('nitrogen'),    data.get('phosphorus'),
            data.get('potassium'),   data.get('ph'),
            data.get('temperature'), data.get('rainfall'),
            data.get('region'),      data.get('season'),
            predicted_crop,          confidence
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Save prediction error: {e}")
        return False


def save_sensor_reading(reading):
    """Persist one IoT soil-sensor reading. Best-effort; never raises."""
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sensor_readings
            (node_id, source, nitrogen, phosphorus, potassium, ph,
             temperature, rainfall, moisture, region, season, predicted_crop)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            reading.get('node_id'),     reading.get('source'),
            reading.get('nitrogen'),    reading.get('phosphorus'),
            reading.get('potassium'),   reading.get('ph'),
            reading.get('temperature'), reading.get('rainfall'),
            reading.get('moisture'),    reading.get('region'),
            reading.get('season'),      reading.get('predicted_crop'),
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Save sensor reading error: {e}")
        return False


def get_all_crops():
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM crops")
        # Convert sqlite3.Row -> plain dict so Flask's jsonify can serialize them.
        crops = [dict(r) for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return crops
    except Exception as e:
        print(f"Get crops error: {e}")
        return []
