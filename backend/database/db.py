"""
db.py  —  Data layer for SmartZameen AI (Neon Postgres OR SQLite)

Dual-mode, picked automatically at startup:

  • DATABASE_URL is set  ->  Neon / Postgres   (production, e.g. on Render)
  • DATABASE_URL is empty ->  SQLite file       (local dev — zero setup)

So locally you just run `python app.py` (SQLite, nothing to install), and in
production you set DATABASE_URL to your Neon connection string and the SAME code
talks to Postgres instead. Neon persists data across restarts/redeploys, which
a file-based SQLite on Render's ephemeral disk does not.

Public API is unchanged so the rest of the app needs no edits:
    get_connection()      -> a DB connection (dict-style rows) or None
    create_database()     -> creates tables + seeds sample crops (idempotent)
    save_prediction()     -> store one crop prediction
    get_all_crops()       -> list[dict] of seeded crops
    save_sensor_reading() -> persist one IoT soil-sensor reading

Both backends use MySQL/Postgres-style "%s" placeholders. Postgres uses them
natively; for SQLite a tiny cursor shim rewrites "%s" -> "?".
"""

import os

# .env is optional (used for DATABASE_URL + API keys). Never let a missing
# python-dotenv break the database layer.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Neon / Postgres when DATABASE_URL is provided; otherwise local SQLite file.
DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
USE_PG = bool(DATABASE_URL)

if USE_PG:
    import psycopg
    from psycopg.rows import dict_row
else:
    import sqlite3
    # Single-file database, created on demand right next to this module.
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smartzameen.db')

    class _Cursor(sqlite3.Cursor):
        """Cursor that accepts Postgres-style %s placeholders (rewritten to ?)."""
        def execute(self, sql, params=()):
            return super().execute(sql.replace('%s', '?'), params)

        def executemany(self, sql, seq):
            return super().executemany(sql.replace('%s', '?'), seq)

    class _Connection(sqlite3.Connection):
        def cursor(self, factory=_Cursor):
            return super().cursor(factory)


def get_connection():
    """Return a DB connection with dict-style rows, or None on failure."""
    try:
        if USE_PG:
            # row_factory=dict_row makes rows behave like dicts: row['name'].
            return psycopg.connect(DATABASE_URL, row_factory=dict_row)
        conn = sqlite3.connect(DB_PATH, timeout=5, factory=_Connection)
        conn.row_factory = sqlite3.Row        # rows behave like dicts: row['name']
        return conn
    except Exception as e:
        print(f"Database Error: {e}")
        return None


# ── Tiny dialect helpers (the only SQL that differs between the two backends) ──
def _pk():
    """Auto-incrementing primary-key clause for the active backend."""
    return "SERIAL PRIMARY KEY" if USE_PG else "INTEGER PRIMARY KEY AUTOINCREMENT"


def create_database():
    """Create all tables (idempotent) and seed sample crops."""
    conn = get_connection()
    if not conn:
        print("[WARNING] Database khol nahi saka")
        return
    try:
        cursor = conn.cursor()
        pk = _pk()

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS users (
                id         {pk},
                name       TEXT NOT NULL,
                email      TEXT UNIQUE NOT NULL,
                password   TEXT NOT NULL,
                region     TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS crops (
                id          {pk},
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

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS predictions (
                id             {pk},
                nitrogen       REAL, phosphorus REAL,
                potassium      REAL, ph         REAL,
                temperature    REAL, rainfall   REAL,
                region         TEXT, season     TEXT,
                predicted_crop TEXT,
                confidence     REAL,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS soil_data (
                id          {pk},
                region      TEXT,
                nitrogen    REAL, phosphorus REAL,
                potassium   REAL, ph_value   REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Persistent log of IoT soil-sensor readings (virtual sensor / simulator).
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id             {pk},
                node_id        TEXT, source TEXT,
                nitrogen       REAL, phosphorus REAL, potassium REAL, ph REAL,
                temperature    REAL, rainfall   REAL, moisture  REAL,
                region         TEXT, season     TEXT,
                predicted_crop TEXT,
                received_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration: older databases may not have the users.region column.
        try:
            if USE_PG:
                cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS region TEXT")
            else:
                cols = [r['name'] for r in cursor.execute("PRAGMA table_info(users)").fetchall()]
                if 'region' not in cols:
                    cursor.execute("ALTER TABLE users ADD COLUMN region TEXT")
                    print("[migration] added users.region")
        except Exception as _e:
            print(f"[migration] users.region skipped: {_e}")

        conn.commit()
        insert_sample_crops(cursor)
        conn.commit()
        cursor.close()
        conn.close()
        print(f"[OK] Database ready! ({'Neon/Postgres' if USE_PG else 'SQLite'})")

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
    # "do nothing on duplicate name" — Postgres ON CONFLICT vs SQLite OR IGNORE.
    conflict = "ON CONFLICT (name) DO NOTHING" if USE_PG else ""
    or_ignore = "" if USE_PG else "OR IGNORE"
    cursor.executemany(f"""
        INSERT {or_ignore} INTO crops
        (name, urdu_name, season, min_rain, max_rain,
         min_temp, max_temp, min_ph, max_ph, region, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        {conflict}
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
        # Convert rows -> plain dict so Flask's jsonify can serialize them.
        crops = [dict(r) for r in cursor.fetchall()]
        cursor.close()
        conn.close()
        return crops
    except Exception as e:
        print(f"Get crops error: {e}")
        return []


def get_prediction_stats():
    """Real dashboard stats computed from the predictions table.

    Returns zeros / None when there are no predictions yet (clean empty state).
    """
    empty = {'total': 0, 'this_month': 0, 'avg_confidence': 0, 'top_crop': None}
    conn = get_connection()
    if not conn:
        return empty
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM predictions")
        total = cur.fetchone()['c']

        # "predictions made this calendar month" — Postgres to_char vs SQLite strftime.
        if USE_PG:
            cur.execute("""
                SELECT COUNT(*) AS c FROM predictions
                WHERE to_char(created_at, 'YYYY-MM') = to_char(now(), 'YYYY-MM')
            """)
        else:
            cur.execute("""
                SELECT COUNT(*) AS c FROM predictions
                WHERE strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
            """)
        this_month = cur.fetchone()['c']

        cur.execute("SELECT AVG(confidence) AS a FROM predictions")
        avg = cur.fetchone()['a']

        cur.execute("""
            SELECT predicted_crop, COUNT(*) AS c
            FROM predictions
            WHERE predicted_crop IS NOT NULL
            GROUP BY predicted_crop ORDER BY c DESC LIMIT 1
        """)
        row = cur.fetchone()
        top_crop = row['predicted_crop'] if row else None

        cur.close(); conn.close()
        return {
            'total': total,
            'this_month': this_month,
            'avg_confidence': round(avg, 1) if avg is not None else 0,
            'top_crop': top_crop,
        }
    except Exception as e:
        print(f"Get prediction stats error: {e}")
        return empty


def get_recent_predictions(limit=5):
    """Most recent predictions for the dashboard table (newest first)."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT created_at, region, season, predicted_crop, confidence,
                   nitrogen, phosphorus, potassium, ph, temperature, rainfall
            FROM predictions ORDER BY id DESC LIMIT %s
        """, (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows
    except Exception as e:
        print(f"Get recent predictions error: {e}")
        return []


def get_sensor_readings(limit=50):
    """Recent IoT sensor readings for the History page (newest first)."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT received_at, node_id, source, nitrogen, phosphorus, potassium,
                   ph, temperature, rainfall, moisture, region, season, predicted_crop
            FROM sensor_readings ORDER BY id DESC LIMIT %s
        """, (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        cur.close(); conn.close()
        return rows
    except Exception as e:
        print(f"Get sensor readings error: {e}")
        return []
