import os
import json
import random
import numpy as np
from PIL import Image, ImageDraw
import joblib

# SciPy for fast 2D convolution
from scipy.ndimage import convolve
# Scikit-learn for neural network/classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# ===== STEP 1: CONFIGURATION =====
DATASET_DIR = os.path.join(os.path.dirname(__file__), 'dataset', 'soil_images')
MODEL_SAVE_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend', 'ml_models')
os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

CLASSES = ['clay', 'loam', 'sand', 'silt']
IMG_SIZE = 64  # Compact size for fast CPU operations
SAMPLES_PER_CLASS = 100

print("=" * 60)
print("SmartZameen AI - Custom Soil CNN Feature Training Engine")
print("=" * 60)

# ===== STEP 2: SYNTHETIC DATA GENERATOR =====
def generate_synthetic_dataset():
    print(f"\nDataset folder: {DATASET_DIR}")
    print("Generating synthetic soil images (colors, textures, and noise)...")
    
    soil_profiles = {
        'clay': {
            'base_color': (145, 75, 30),  # Reddish-brown
            'noise_level': 10,
            'clump_color': (110, 50, 20),
            'clumps_count': 6
        },
        'loam': {
            'base_color': (50, 35, 20),   # Very dark brown / organic rich
            'noise_level': 7,
            'clump_color': (30, 20, 10),
            'clumps_count': 4
        },
        'sand': {
            'base_color': (205, 175, 130), # Light tan / sandy yellow
            'noise_level': 20,             # High noise for graininess
            'clump_color': (180, 150, 110),
            'clumps_count': 2
        },
        'silt': {
            'base_color': (120, 110, 95),  # Medium greyish-brown
            'noise_level': 12,
            'clump_color': (90, 80, 70),
            'clumps_count': 8
        }
    }
    
    random.seed(42)
    np.random.seed(42)

    for class_name, profile in soil_profiles.items():
        class_path = os.path.join(DATASET_DIR, class_name)
        os.makedirs(class_path, exist_ok=True)
        
        # Check if already has SAMPLES_PER_CLASS images
        existing_files = [f for f in os.listdir(class_path) if f.endswith('.jpg')]
        if len(existing_files) >= SAMPLES_PER_CLASS:
            print(f"   [Info] Class '{class_name}' already exists with {len(existing_files)} images. Skipping generation.")
            continue
            
        print(f"   Generating {SAMPLES_PER_CLASS} images for '{class_name}'...")
        for i in range(SAMPLES_PER_CLASS):
            # Create base color canvas
            base = np.full((IMG_SIZE, IMG_SIZE, 3), profile['base_color'], dtype=np.uint8)
            
            # Generate grain/texture noise
            noise = np.random.normal(0, profile['noise_level'], (IMG_SIZE, IMG_SIZE, 3))
            noise_img = np.clip(base + noise, 0, 255).astype(np.uint8)
            
            img = Image.fromarray(noise_img)
            draw = ImageDraw.Draw(img)
            
            # Add some organic clumps/rocks
            for _ in range(profile['clumps_count']):
                cx = random.randint(5, IMG_SIZE - 5)
                cy = random.randint(5, IMG_SIZE - 5)
                radius = random.randint(1, 3)
                
                clr = tuple(
                    int(c + random.uniform(-8, 8)) for c in profile['clump_color']
                )
                
                draw.ellipse(
                    [cx - radius, cy - radius, cx + radius, cy + radius],
                    fill=clr
                )
            
            img_filename = f"{class_name}_{i:03d}.jpg"
            img.save(os.path.join(class_path, img_filename), 'JPEG')
            
    print("Dataset generation completed successfully!")

# ===== STEP 3: CNN FEATURE EXTRACTOR =====
# Custom 2D kernels for feature extraction
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

def extract_cnn_features(image_path):
    """
    Simulates a CNN forward pass:
    1. Loads the image and resizes it to 64x64.
    2. Convolves RGB channels with a bank of 3x3 kernels (Color + Edges + Texture).
    3. Performs 4x4 Max Pooling to downsample.
    4. Flattens into a compact feature vector.
    """
    img = Image.open(image_path).convert('RGB').resize((IMG_SIZE, IMG_SIZE))
    img_arr = np.array(img, dtype=float) / 255.0
    
    feature_maps = []
    
    # 1. Color feature maps (RGB channels directly)
    for c in range(3):
        feature_maps.append(img_arr[:, :, c])
        
    # Convert image to greyscale for edge/texture kernels
    grey = 0.2989 * img_arr[:,:,0] + 0.5870 * img_arr[:,:,1] + 0.1140 * img_arr[:,:,2]
    
    # 2. Convolve with custom 3x3 kernels (equivalent to CNN Convolutional Layer)
    for kernel_name, kernel in KERNELS.items():
        convolved = convolve(grey, kernel, mode='reflect')
        feature_maps.append(convolved)
        
    # 3. Max Pooling (4x4 patches downsampling 64x64 -> 16x16)
    pooled_features = []
    pool_size = 4
    out_size = IMG_SIZE // pool_size  # 16
    
    for fmap in feature_maps:
        # Reshape to 16x4x16x4 to perform 2D pooling
        reshaped = fmap.reshape(out_size, pool_size, out_size, pool_size)
        # Max along axis 1 and 3
        pooled = reshaped.max(axis=(1, 3))
        pooled_features.append(pooled.flatten())
        
    # Flatten all pooled maps into a single 1D vector (equivalent to CNN Flatten Layer)
    # Total features: 6 maps * 16 * 16 = 1536
    return np.concatenate(pooled_features)

# ===== STEP 4: TRAINING =====
def train_model():
    print("\nExtracting CNN-like features from image dataset...")
    X = []
    y = []
    
    for class_idx, class_name in enumerate(CLASSES):
        class_path = os.path.join(DATASET_DIR, class_name)
        images = [f for f in os.listdir(class_path) if f.endswith('.jpg')]
        
        for img_name in images:
            img_path = os.path.join(class_path, img_name)
            features = extract_cnn_features(img_path)
            X.append(features)
            y.append(class_idx)
            
    X = np.array(X)
    y = np.array(y)
    
    print(f"Extracted feature shape: {X.shape}")
    print(f"Classes Index Map: {CLASSES}")
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Training samples  : {len(X_train)}")
    print(f"Validation samples: {len(X_test)}")
    
    # Train random forest classifier on CNN features (low memory footprint)
    print("\nTraining Classifier on CNN features...")
    clf = RandomForestClassifier(
        n_estimators=50,      # Compact size to save disk space
        max_depth=10,
        random_state=42,
        n_jobs=-1
    )
    clf.fit(X_train, y_train)
    
    # Evaluate
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Validation Accuracy: {acc*100:.2f}%")
    
    # Export
    model_path = os.path.join(MODEL_SAVE_DIR, 'soil_classifier.pkl')
    classes_path = os.path.join(MODEL_SAVE_DIR, 'soil_classes.json')
    
    joblib.dump(clf, model_path)
    with open(classes_path, 'w') as f:
        json.dump(CLASSES, f)
        
    print(f"\nModel exported successfully:")
    print(f"   Model Classifier: {model_path} ({os.path.getsize(model_path)/1024:.1f} KB)")
    print(f"   Classes Map     : {classes_path}")
    print("\nCustom CNN soil classifier ready for local deployment!")
    print("=" * 60)

if __name__ == '__main__':
    generate_synthetic_dataset()
    train_model()
