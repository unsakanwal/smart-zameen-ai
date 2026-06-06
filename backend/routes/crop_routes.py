from flask import Blueprint, request, jsonify
import numpy as np
import joblib
import os
from database.db import (save_prediction, get_all_crops,
                         get_prediction_stats, get_recent_predictions,
                         get_sensor_readings)

crop_bp = Blueprint('crop', __name__)

# ===== MODEL PATHS =====
MODEL_PATH     = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'crop_model.pkl')
ENCODER_PATH   = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'le_crop.pkl')
LE_SEASON_PATH = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'le_season.pkl')
LE_REGION_PATH = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'le_region.pkl')

# Higher-accuracy Kaggle Crop Recommendation model (22 crops).
# Inputs: [N, P, K, temperature, humidity, pH, rainfall]. Used when humidity is provided.
NEW_MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'crop-reccomendation-modal', 'soil.pkl')
NEW_LE_PATH    = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'crop-reccomendation-modal', 'label_encoder.pkl')

model     = None
encoder   = None
le_season = None
le_region = None
new_model = None
new_le    = None

def load_ml_model():
    global model, encoder, le_season, le_region, new_model, new_le
    try:
        model     = joblib.load(MODEL_PATH)
        encoder   = joblib.load(ENCODER_PATH)
        le_season = joblib.load(LE_SEASON_PATH)
        le_region = joblib.load(LE_REGION_PATH)
        print("[OK] ML Model load ho gaya!")
    except FileNotFoundError as e:
        print(f"[WARNING] Model nahi mila: {e}")
    except Exception as e:
        print(f"[WARNING] Model load fail ({type(e).__name__}: {e}) — "
              f"rule-based prediction use hogi.")
        model = None
    # higher-accuracy model (optional)
    try:
        new_model = joblib.load(NEW_MODEL_PATH)
        new_le    = joblib.load(NEW_LE_PATH)
        print(f"[OK] Crop Recommendation model loaded ({len(new_le.classes_)} crops; uses humidity).")
    except Exception as e:
        print(f"[INFO] High-accuracy crop model not loaded ({type(e).__name__}) — using base model.")
        new_model = None; new_le = None

CROP_INFO = {
    'wheat':     {'urdu': 'گندم',   'season': 'Rabi',   'time': 'Nov–Mar', 'water': '4–5 dafa',    'yield': '25–30 mann'},
    'rice':      {'urdu': 'چاول',   'season': 'Kharif', 'time': 'Jun–Oct', 'water': 'Zyada',       'yield': '30–40 mann'},
    'maize':     {'urdu': 'مکئی',   'season': 'Kharif', 'time': 'Apr–Aug', 'water': '3–4 dafa',    'yield': '40–50 mann'},
    'cotton':    {'urdu': 'کپاس',   'season': 'Kharif', 'time': 'Apr–Oct', 'water': '5–6 dafa',    'yield': '25–35 mann'},
    'mustard':   {'urdu': 'سرسوں',  'season': 'Rabi',   'time': 'Oct–Feb', 'water': '3–4 dafa',    'yield': '18–22 mann'},
    'chickpea':  {'urdu': 'چنے',    'season': 'Rabi',   'time': 'Oct–Feb', 'water': '2–3 dafa',    'yield': '12–16 mann'},
    'sugarcane': {'urdu': 'گنا',    'season': 'Kharif', 'time': 'Mar–Nov', 'water': 'Bahut zyada', 'yield': 'Per acre alag'},
    'mango':     {'urdu': 'آم',     'season': 'Kharif', 'time': 'May–Jul', 'water': 'Munasib',     'yield': 'Season mein'},
    'tomato':    {'urdu': 'ٹماٹر',  'season': 'Rabi',   'time': 'Oct–Feb', 'water': '3–4 dafa',    'yield': '150–200 mann'},
    'onion':     {'urdu': 'پیاز',   'season': 'Rabi',   'time': 'Oct–Mar', 'water': '3–4 dafa',    'yield': '100–150 mann'},
    'potato':    {'urdu': 'آلو',    'season': 'Rabi',   'time': 'Oct–Jan', 'water': '4–5 dafa',    'yield': '200–300 mann'},
    'kino':      {'urdu': 'کینو',   'season': 'Rabi',   'time': 'Nov–Feb', 'water': '2–3 dafa',    'yield': 'Per tree alag'},
}

# Urdu names for the high-accuracy (Kaggle) model's 22 crops — used for display.
CROP_URDU = {
    'apple': 'سیب', 'banana': 'کیلا', 'blackgram': 'ماش', 'chickpea': 'چنے', 'coconut': 'ناریل',
    'coffee': 'کافی', 'cotton': 'کپاس', 'grapes': 'انگور', 'jute': 'پٹ سن', 'kidneybeans': 'لوبیا',
    'lentil': 'مسور', 'maize': 'مکئی', 'mango': 'آم', 'mothbeans': 'مونگ', 'mungbean': 'مونگ',
    'muskmelon': 'خربوزہ', 'orange': 'مالٹا', 'papaya': 'پپیتا', 'pigeonpeas': 'ارہر',
    'pomegranate': 'انار', 'rice': 'چاول', 'watermelon': 'تربوز',
}

def crop_urdu(name):
    return CROP_INFO.get(name, {}).get('urdu') or CROP_URDU.get(name, '')

def predict_new(n, p, k, temperature, humidity, ph, rainfall):
    """Predict with the high-accuracy Kaggle model. Returns (crop, confidence, top3)."""
    feats = np.array([[n, p, k, temperature, humidity, ph, rainfall]])
    probs = new_model.predict_proba(feats)[0]
    order = np.argsort(probs)[::-1][:3]
    top3 = [{
        'crop':       new_le.inverse_transform([int(i)])[0],
        'confidence': round(float(probs[int(i)]) * 100, 1),
        'urdu':       crop_urdu(new_le.inverse_transform([int(i)])[0]),
    } for i in order]
    return top3[0]['crop'], top3[0]['confidence'], top3

@crop_bp.route('/api/predict-crop', methods=['POST'])
def predict_crop():
    try:
        data = request.get_json()
        required = ['nitrogen','phosphorus','potassium','ph','temperature','rainfall']
        for field in required:
            if field not in data:
                return jsonify({'error': f'{field} field zaroori hai!'}), 400

        nitrogen    = float(data['nitrogen'])
        phosphorus  = float(data['phosphorus'])
        potassium   = float(data['potassium'])
        ph          = float(data['ph'])
        temperature = float(data['temperature'])
        rainfall    = float(data['rainfall'])
        region      = data.get('region', 'Punjab').strip().title()
        season      = data.get('season', 'rabi').strip().lower()
        humidity    = data.get('humidity', None)

        # Prefer the high-accuracy Kaggle model when humidity is available.
        if new_model is not None and humidity not in (None, ''):
            crop_name, confidence, top3 = predict_new(
                nitrogen, phosphorus, potassium, temperature, float(humidity), ph, rainfall)
        elif model is not None and encoder is not None:
            season_enc = le_season.transform([season])[0] if season in le_season.classes_ else 0
            region_enc = le_region.transform([region])[0] if region in le_region.classes_ else 0
            features   = np.array([[nitrogen, phosphorus, potassium, ph,
                                    temperature, rainfall, season_enc, region_enc]])
            prediction    = model.predict(features)[0]
            probabilities = model.predict_proba(features)[0]
            confidence    = round(float(max(probabilities)) * 100, 1)
            crop_name     = encoder.inverse_transform([prediction])[0]

            top3_idx = np.argsort(probabilities)[::-1][:3]
            top3 = [
                {
                    'crop':       encoder.inverse_transform([i])[0],
                    'confidence': round(float(probabilities[i]) * 100, 1),
                    'urdu':       CROP_INFO.get(encoder.inverse_transform([i])[0], {}).get('urdu', '')
                }
                for i in top3_idx
            ]
        else:
            crop_name, confidence, top3 = rule_based_predict(
                temperature, rainfall, season, region)

        info = CROP_INFO.get(crop_name, {})
        save_prediction(data, crop_name, confidence)

        return jsonify({
            'success':   True,
            'crop':      crop_name,
            'urdu':      crop_urdu(crop_name),
            'confidence':confidence,
            'season':    info.get('season', ''),
            'best_time': info.get('time', ''),
            'water':     info.get('water', ''),
            'yield':     info.get('yield', ''),
            'top3':      top3
        })

    except ValueError as e:
        return jsonify({'error': f'Ghalat value: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@crop_bp.route('/api/dashboard-summary', methods=['GET'])
def dashboard_summary():
    """Real dashboard data (stats + recent predictions) from the DB."""
    stats = get_prediction_stats()
    if stats.get('top_crop'):
        stats['top_crop_urdu'] = CROP_INFO.get(stats['top_crop'], {}).get('urdu', '')
    recent = get_recent_predictions(5)
    for r in recent:
        r['urdu'] = CROP_INFO.get(r.get('predicted_crop'), {}).get('urdu', '')
    return jsonify({'success': True, 'stats': stats, 'recent': recent})


@crop_bp.route('/api/history', methods=['GET'])
def history():
    """Full activity history: crop predictions + IoT sensor readings."""
    preds = get_recent_predictions(50)
    for r in preds:
        r['urdu'] = CROP_INFO.get(r.get('predicted_crop'), {}).get('urdu', '')
    sensors = get_sensor_readings(50)
    for r in sensors:
        r['urdu'] = CROP_INFO.get(r.get('predicted_crop'), {}).get('urdu', '')
    return jsonify({'success': True, 'predictions': preds, 'sensors': sensors})


@crop_bp.route('/api/crops', methods=['GET'])
def get_crops():
    crops = get_all_crops()
    if crops:
        return jsonify({'success': True, 'crops': crops})
    return jsonify({'success': True, 'crops': list(CROP_INFO.items())})


@crop_bp.route('/api/crops/<crop_name>', methods=['GET'])
def get_crop_detail(crop_name):
    info = CROP_INFO.get(crop_name.lower())
    if info:
        return jsonify({'success': True, 'crop': crop_name, 'info': info})
    return jsonify({'error': 'Fasal nahi mili!'}), 404


def rule_based_predict(temperature, rainfall, season, region):
    if season == 'rabi':
        if 'balochistan' in region.lower():
            return 'chickpea', 75.0, []
        elif 'sindh' in region.lower():
            return 'mustard', 78.0, []
        else:
            return 'wheat', 82.0, []
    else:
        if rainfall > 150:
            return 'rice', 80.0, []
        elif temperature > 30:
            return 'cotton', 76.0, []
        else:
            return 'maize', 74.0, []


load_ml_model()