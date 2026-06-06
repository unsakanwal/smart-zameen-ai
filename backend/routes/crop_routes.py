from flask import Blueprint, request, jsonify
import numpy as np
import joblib
import os
from database.db import save_prediction, get_all_crops

crop_bp = Blueprint('crop', __name__)

# ===== MODEL PATHS =====
MODEL_PATH     = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'crop_model.pkl')
ENCODER_PATH   = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'le_crop.pkl')
LE_SEASON_PATH = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'le_season.pkl')
LE_REGION_PATH = os.path.join(os.path.dirname(__file__), '..', 'ml_models', 'le_region.pkl')

model     = None
encoder   = None
le_season = None
le_region = None

def load_ml_model():
    global model, encoder, le_season, le_region    # ← FIXED
    try:
        model     = joblib.load(MODEL_PATH)
        encoder   = joblib.load(ENCODER_PATH)
        le_season = joblib.load(LE_SEASON_PATH)
        le_region = joblib.load(LE_REGION_PATH)
        print("[OK] ML Model load ho gaya!")
    except FileNotFoundError as e:
        print(f"[WARNING] Model nahi mila: {e}")
    except Exception as e:
        # e.g. scikit-learn / numpy version mismatch when unpickling an older
        # model on a newer Python. Don't crash — fall back to rule_based_predict.
        print(f"[WARNING] Model load fail ({type(e).__name__}: {e}) — "
              f"rule-based prediction use hogi.")
        model = None

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

        if model is not None and encoder is not None:
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
            'urdu':      info.get('urdu', ''),
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