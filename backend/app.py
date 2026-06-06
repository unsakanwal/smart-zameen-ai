from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from database.db import create_database, get_connection
from routes.crop_routes import crop_bp
from routes.weather_routes import weather_bp
from routes.whatsapp_routes import whatsapp_bp
from routes.sms_routes import sms_bp
from routes.image_routes import image_bp
from routes.voice_routes import voice_bp
from routes.sensor_routes import sensor_bp
from routes.chat_routes import chat_bp
import os
import hashlib

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

# ===== BLUEPRINTS =====
app.register_blueprint(crop_bp)
app.register_blueprint(weather_bp)
app.register_blueprint(whatsapp_bp)
app.register_blueprint(sms_bp)
app.register_blueprint(image_bp)
app.register_blueprint(voice_bp)
app.register_blueprint(sensor_bp)
app.register_blueprint(chat_bp)


# ===== HELPERS =====
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# ===== AUTH ROUTES =====
@app.route('/signup', methods=['POST'])
def signup():
    data     = request.get_json()
    name     = data.get('name', '').strip()
    email    = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({'error': 'Email aur password zaroori hai!'}), 400

    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Database error!'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (name, email, hash_password(password))
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Account ban gaya!'}), 200
    except Exception as e:
        if 'Duplicate' in str(e) or 'UNIQUE' in str(e):
            return jsonify({'error': 'یہ email پہلے سے رجسٹر ہے!'}), 400
        return jsonify({'error': str(e)}), 500


@app.route('/login', methods=['POST'])
def login():
    data     = request.get_json()
    email    = data.get('email', '').strip()
    password = data.get('password', '').strip()

    if not email or not password:
        return jsonify({'error': 'Email aur password daalo!'}), 400

    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Database error!'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email = %s AND password = %s",
            (email, hash_password(password))
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user:
            token = hashlib.sha256(f"{email}smartzameen".encode()).hexdigest()
            return jsonify({
                'success': True,
                'token':   token,
                'user':    {'name': user['name'], 'email': user['email']}
            }), 200
        else:
            return jsonify({'error': 'Email ya password galat hai!'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== PROFILE ROUTES =====
@app.route('/api/profile', methods=['GET'])
def get_profile():
    email = request.args.get('email', '').strip()
    if not email:
        return jsonify({'error': 'Email zaroori hai!'}), 400
    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Database error!'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name, email, region FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        cursor.close(); conn.close()
        if not row:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        return jsonify({'success': True, 'name': row['name'], 'email': row['email'],
                        'region': row['region'] or ''})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/update-profile', methods=['POST'])
def update_profile():
    data     = request.get_json() or {}
    email    = data.get('email', '').strip()
    name     = data.get('name', '').strip()
    region   = data.get('region', '').strip()
    password = data.get('password')

    if not email or not name:
        return jsonify({'error': 'Email aur name zaroori hai!'}), 400
    if password is not None and len(str(password)) < 6:
        return jsonify({'error': 'Password kam az kam 6 characters ka ho!'}), 400

    conn = get_connection()
    if not conn:
        return jsonify({'error': 'Database error!'}), 500
    try:
        cursor = conn.cursor()
        if password:
            cursor.execute("UPDATE users SET name = %s, region = %s, password = %s WHERE email = %s",
                           (name, region, hash_password(password), email))
        else:
            cursor.execute("UPDATE users SET name = %s, region = %s WHERE email = %s",
                           (name, region, email))
        conn.commit()
        cursor.close(); conn.close()
        return jsonify({'success': True, 'message': 'Profile updated!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== FRONTEND SERVE =====
@app.route('/')
def home():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if path.startswith('api/'):
        return jsonify({'error': 'Not found'}), 404
    if os.path.exists(os.path.join(FRONTEND_DIR, path)):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')


# ===== ERROR HANDLERS =====
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Route nahi mili!'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error!'}), 500


# ===== START =====
if __name__ == '__main__':
    print("=" * 45)
    print("SmartZameen Backend")
    print("=" * 45)

    print("Database setup...")
    try:
        create_database()
        print("[OK] Database ready!")
    except Exception as e:
        print(f"[WARNING] Database error: {e}")

    # Anthropic API key check
    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("[WARNING] ANTHROPIC_API_KEY set nahi - soil image analysis fallback will be used if needed")
        print("    Terminal mein chalao: set ANTHROPIC_API_KEY=your_key_here")
    else:
        print("[OK] Anthropic API key ready!")

    # Port 80 often needs admin rights on Windows (or is taken by IIS/Skype).
    # Try 80 first; if it can't bind, fall back to 5000 so the app ALWAYS runs.
    def _run(port):
        print(f"Server: http://localhost:{port}")
        print("=" * 45)
        app.run(debug=True, use_reloader=False, host='0.0.0.0', port=port)

    try:
        _run(80)
    except (PermissionError, OSError) as e:
        print(f"[WARNING] Port 80 unavailable ({e}). Falling back to port 5000...")
        _run(5000)