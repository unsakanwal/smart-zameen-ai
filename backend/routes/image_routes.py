import os
import base64
import json
import io
import joblib
import numpy as np
from PIL import Image
from scipy.ndimage import convolve
from flask import Blueprint, request, jsonify

image_bp = Blueprint('image', __name__)

# ===================================================
# CNN FEATURE EXTRACTOR
# ===================================================
IMG_SIZE = 64
KERNELS = {
    'horizontal_edge': np.array([[-1, -2, -1],
                                 [ 0,  0,  0],
                                 [ 1,  2,  1]]),
    
    'vertical_edge':   np.array([[-1,  0,  1],
                                 [-2,  0,  2],
                                 [-1,  0,  1]]),
    
    'laplacian_grain': np.array([[ 0,  1,  0],
                                 [ 1, -4,  1],
                                 [ 0,  1,  0]])
}

def extract_cnn_features(image_bytes):
    """
    Applies the exact same CNN-feature pipeline as train_soil_cnn.py:
    1. Color channel extraction
    2. 2D convolution with edge and high-frequency kernels
    3. 4x4 Max Pooling
    4. Flattening
    """
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB').resize((IMG_SIZE, IMG_SIZE))
    img_arr = np.array(img, dtype=float) / 255.0
    
    feature_maps = []
    
    # 1. Color channel maps
    for c in range(3):
        feature_maps.append(img_arr[:, :, c])
        
    # Greyscale for edge/texture kernels
    grey = 0.2989 * img_arr[:,:,0] + 0.5870 * img_arr[:,:,1] + 0.1140 * img_arr[:,:,2]
    
    # 2. Convolve with custom 3x3 kernels
    for kernel_name, kernel in KERNELS.items():
        convolved = convolve(grey, kernel, mode='reflect')
        feature_maps.append(convolved)
        
    # 3. Max Pooling (4x4 downsampling 64x64 -> 16x16)
    pooled_features = []
    pool_size = 4
    out_size = IMG_SIZE // pool_size  # 16
    
    for fmap in feature_maps:
        reshaped = fmap.reshape(out_size, pool_size, out_size, pool_size)
        pooled = reshaped.max(axis=(1, 3))
        pooled_features.append(pooled.flatten())
        
    return np.concatenate(pooled_features)

# ===================================================
# CLASSIFIER MODEL LOADER
# ===================================================
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ml_models')
MODEL_PATH = os.path.join(MODEL_DIR, 'soil_classifier.pkl')
CLASSES_PATH = os.path.join(MODEL_DIR, 'soil_classes.json')

clf = None
classes = None

def load_classifier():
    global clf, classes
    if os.path.exists(MODEL_PATH) and os.path.exists(CLASSES_PATH):
        try:
            clf = joblib.load(MODEL_PATH)
            with open(CLASSES_PATH, 'r') as f:
                classes = json.load(f)
            print("[OK] Custom Soil Classifier loaded successfully in backend!")
            return True
        except Exception as e:
            print(f"[WARNING] Failed to load custom classifier: {e}")
    return False

# ====================
# SOIL PROPERTIES MAP 
# ====================
SOIL_PROPERTIES = {
    'clay': {
        'soil_type': 'Clayey Soil',
        'texture': 'Fine',
        'soil_health': 'Good',
        'organic_matter': 'Medium',
        'nitrogen': 45,
        'phosphorus': 22,
        'potassium': 30,
        'ph': 6.8,
        'soil_color': 'Reddish Brown',
        'moisture': 'High',
        'recommended_crop': 'Rice',
        'recommended_crop_urdu': 'چاول',
        'description_ur': 'آپ کی مٹی چکنی مٹی (Clayey) قسم کی ہے۔ اس کی پانی جذب کرنے کی صلاحیت زیادہ ہے، جو چاول کی کاشت کے لیے نہایت موزوں ہے۔ نائٹروجن اور فاسفورس کی کچھ کمی ہے۔',
        'improvements': [
            'نائٹروجن کے لیے گوبر کی کھاد کا استعمال کریں۔',
            'فاسفورس کی کمی پوری کرنے کے لیے ڈی اے پی (DAP) ڈالیں۔'
        ]
    },
    'loam': {
        'soil_type': 'Loamy Soil',
        'texture': 'Fine-Medium',
        'soil_health': 'Good',
        'organic_matter': 'High',
        'nitrogen': 75,
        'phosphorus': 45,
        'potassium': 50,
        'ph': 7.2,
        'soil_color': 'Dark Brown',
        'moisture': 'Moderate',
        'recommended_crop': 'Wheat',
        'recommended_crop_urdu': 'گندم',
        'description_ur': 'آپ کی مٹی زرخیز لومڑی (Loamy) قسم کی ہے۔ اس میں غذائیت کی مقدار بہترین ہے، جو گندم، کپاس اور گنے کے لیے انتہائی سازگار ہے۔',
        'improvements': [
            'نامیاتی مادہ برقرار رکھنے کے لیے سبز کھاد کا استعمال کریں۔',
            'فصلوں کی گردش (Crop Rotation) پر عمل کریں۔'
        ]
    },
    'sand': {
        'soil_type': 'Sandy Soil',
        'texture': 'Coarse',
        'soil_health': 'Poor',
        'organic_matter': 'Low',
        'nitrogen': 20,
        'phosphorus': 15,
        'potassium': 15,
        'ph': 8.0,
        'soil_color': 'Light Tan',
        'moisture': 'Low',
        'recommended_crop': 'Chickpea',
        'recommended_crop_urdu': 'چنے',
        'description_ur': 'آپ کی مٹی ریتلی (Sandy) قسم کی ہے۔ اس میں پانی اور کھاد روکنے کی صلاحیت کم ہے، جو چنے یا دالوں کی کاشت کے لیے موزوں ہے۔',
        'improvements': [
            'مٹی میں نمی روکنے کے لیے آرگینک کمپوسٹ ڈالیں۔',
            'نائٹروجن کی کمی پوری کرنے کے لیے یوریا کھاد ڈالیں۔'
        ]
    },
    'silt': {
        'soil_type': 'Silty Soil',
        'texture': 'Medium',
        'soil_health': 'Good',
        'organic_matter': 'Medium',
        'nitrogen': 60,
        'phosphorus': 35,
        'potassium': 40,
        'ph': 6.5,
        'soil_color': 'Greyish Brown',
        'moisture': 'Moderate',
        'recommended_crop': 'Maize',
        'recommended_crop_urdu': 'مکئی',
        'description_ur': 'آپ کی مٹی سلٹی (Silty) قسم کی ہے۔ اس کی نمی اور باریک ساخت مکئی اور جوار کی پیداوار کے لیے بہت موزوں ہے۔',
        'improvements': [
            'مٹی کی ساخت بہتر بنانے کے لیے جپسم کا استعمال کریں۔',
            'فاسفورس اور پوٹاشیم کی ہلکی مقدار شامل کریں۔'
        ]
    }
}

# Load classifier model on blueprint register
load_classifier()

# ==========================
# SOIL IMAGE ANALYSIS ROUTE
# ==========================
@image_bp.route('/api/analyze-soil-image', methods=['POST'])
def analyze_soil_image():
    global clf, classes
    
    # Try loading dynamically if not loaded
    if clf is None or classes is None:
        load_classifier()
        
    if clf is None or classes is None:
        return jsonify({
            'success': False,
            'error': 'CNN features classifier model is not trained yet. Run: "python model-training/train_soil_cnn.py" first!'
        }), 500

    try:
        image_bytes = None

        # Check if JSON payload (from camera.js base64)
        if request.is_json:
            req_data = request.get_json(silent=True)
            if req_data and 'image' in req_data:
                image_data = req_data['image']
                if ',' in image_data:
                    # Strip base64 data URL header
                    _, image_data = image_data.split(',', 1)
                image_bytes = base64.b64decode(image_data)

        # Fallback to multipart file upload
        if not image_bytes:
            if 'image' not in request.files:
                return jsonify({'error': 'Image file missing!'}), 400
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': 'No file selected!'}), 400
            image_bytes = file.read()

        # 1. Extract CNN features locally
        features = extract_cnn_features(image_bytes)
        
        # 2. Local model inference
        pred_idx = clf.predict([features])[0]
        
        # Get confidence value from class probability
        probs = clf.predict_proba([features])[0]
        confidence_val = int(max(probs) * 100)
        
        predicted_class = classes[pred_idx]
        
        # 3. Retrieve predefined soil characteristics
        properties = SOIL_PROPERTIES.get(predicted_class, SOIL_PROPERTIES['loam'])

        auto_fill = {
            'nitrogen':    properties['nitrogen'],
            'phosphorus':  properties['phosphorus'],
            'potassium':   properties['potassium'],
            'ph':          properties['ph'],
            'temperature': 24,  # default placeholder
            'rainfall':    150, # default placeholder
        }

        soil_analysis = {
            'soil_type':             properties['soil_type'],
            'texture':               properties['texture'],
            'soil_health':           properties['soil_health'],
            'moisture_level':        properties['moisture'],
            'organic_matter':        properties['organic_matter'],
            'recommended_crop':      properties['recommended_crop'],
            'recommended_crop_urdu': properties['recommended_crop_urdu'],
            'confidence':            confidence_val,
            'estimated_nitrogen':    properties['nitrogen'],
            'estimated_phosphorus':  properties['phosphorus'],
            'estimated_potassium':   properties['potassium'],
            'estimated_ph':          properties['ph'],
            'advice':                properties['description_ur'],
            'improvements':          properties['improvements']
        }

        return jsonify({
            'success':       True,
            'auto_fill':     auto_fill,
            'soil_analysis': soil_analysis
        })

    except Exception as e:
        return jsonify({'error': f'Classifier error: {str(e)}'}), 500


# ========================
# BACKWARD COMPATIBILITY
# =======================
@image_bp.route('/analyze-soil', methods=['POST'])
def analyze_soil_old():
    return analyze_soil_image()