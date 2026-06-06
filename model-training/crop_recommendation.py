import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import os
import warnings
warnings.filterwarnings('ignore')

print("=" * 55)
print("🌾  Smart Agriculture — Crop Recommendation Model")
print("=" * 55)

# ===== STEP 1: CSV FILE LOAD KARO =====
def load_dataset():
    csv_path = os.path.join(os.path.dirname(__file__), 'dataset', 'crops_pakistan.csv')
    
    if os.path.exists(csv_path):
        print(f"✅ CSV file mil gayi: {csv_path}")
        df = pd.read_csv(csv_path)
        print(f"📊 Total rows: {len(df)}")
        print(f"📋 Columns: {list(df.columns)}")
        return df
    else:
        print("⚠️  CSV nahi mili — Synthetic data bana raha hun...")
        return create_synthetic_data()


# ===== STEP 2: SYNTHETIC DATA BANAO =====
def create_synthetic_data():
    np.random.seed(42)
    data = []

    crops_config = [
        # (crop_name, urdu, season, region, N_min, N_max, P_min, P_max,
        #  K_min, K_max, ph_min, ph_max, temp_min, temp_max, rain_min, rain_max, samples)
        ('wheat',      'گندم',    'rabi',   'Punjab',       60,120, 30,60,  30,60,  6.0,7.5, 10,22, 40,100,  400),
        ('wheat',      'گندم',    'rabi',   'KPK',          55,110, 28,58,  28,58,  6.0,7.5, 8, 20, 35,90,   150),
        ('rice',       'چاول',    'kharif', 'Punjab',       70,130, 40,80,  30,60,  5.5,7.0, 22,35, 150,300, 350),
        ('rice',       'چاول',    'kharif', 'Sindh',        65,125, 38,75,  28,58,  5.5,7.0, 24,37, 160,320, 200),
        ('maize',      'مکئی',    'kharif', 'KPK',          70,130, 35,65,  35,65,  5.8,7.5, 18,32, 60,110,  300),
        ('maize',      'مکئی',    'kharif', 'Punjab',       65,125, 32,62,  32,62,  6.0,7.5, 20,33, 55,105,  150),
        ('cotton',     'کپاس',    'kharif', 'Punjab',       50,110, 30,55,  25,55,  6.0,8.0, 20,38, 50,100,  300),
        ('cotton',     'کپاس',    'kharif', 'Sindh',        48,105, 28,52,  23,52,  6.5,8.0, 24,40, 45,95,   200),
        ('mustard',    'سرسوں',   'rabi',   'Punjab',       40,90,  25,50,  25,50,  6.0,7.5, 8, 25, 25,60,   250),
        ('mustard',    'سرسوں',   'rabi',   'Sindh',        38,85,  22,48,  22,48,  6.0,7.5, 10,27, 20,55,   150),
        ('chickpea',   'چنے',     'rabi',   'Balochistan',  30,70,  25,55,  25,55,  6.0,8.0, 10,25, 20,40,   250),
        ('chickpea',   'چنے',     'rabi',   'KPK',          28,68,  23,52,  23,52,  6.0,8.0, 8, 23, 18,38,   100),
        ('sugarcane',  'گنا',     'kharif', 'Punjab',       80,140, 35,70,  35,70,  6.0,7.5, 20,35, 100,200, 200),
        ('sugarcane',  'گنا',     'kharif', 'Sindh',        75,135, 33,68,  33,68,  6.0,7.5, 22,37, 110,210, 150),
        ('mango',      'آم',      'kharif', 'Punjab',       30,80,  20,50,  20,50,  5.5,7.5, 24,40, 75,200,  150),
        ('mango',      'آم',      'kharif', 'Sindh',        28,78,  18,48,  18,48,  5.5,7.5, 26,42, 80,210,  100),
        ('tomato',     'ٹماٹر',   'rabi',   'Punjab',       50,100, 30,60,  30,60,  6.0,7.0, 15,25, 40,80,   150),
        ('onion',      'پیاز',    'rabi',   'Sindh',        40,90,  25,55,  25,55,  6.0,7.5, 12,28, 30,70,   150),
        ('potato',     'آلو',     'rabi',   'KPK',          80,150, 40,80,  40,80,  5.0,6.5, 8, 20, 50,100,  150),
        ('kino',       'کینو',    'rabi',   'Balochistan',  20,60,  15,45,  15,45,  6.0,7.5, 5, 20, 20,60,   150),
    ]

    for cfg in crops_config:
        (crop, urdu, season, region,
         n_min, n_max, p_min, p_max,
         k_min, k_max, ph_min, ph_max,
         t_min, t_max, r_min, r_max, n_samples) = cfg

        for _ in range(n_samples):
            row = {
                'nitrogen':    round(np.random.uniform(n_min,  n_max),  1),
                'phosphorus':  round(np.random.uniform(p_min,  p_max),  1),
                'potassium':   round(np.random.uniform(k_min,  k_max),  1),
                'ph':          round(np.random.uniform(ph_min, ph_max), 2),
                'temperature': round(np.random.uniform(t_min,  t_max),  1),
                'rainfall':    round(np.random.uniform(r_min,  r_max),  1),
                'season':      season,
                'region':      region,
                'crop':        crop,
                'urdu_name':   urdu,
            }
            data.append(row)

    df = pd.DataFrame(data)
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    # CSV save karo
    os.makedirs(os.path.join(os.path.dirname(__file__), 'dataset'), exist_ok=True)
    save_path = os.path.join(os.path.dirname(__file__), 'dataset', 'crops_pakistan.csv')
    df.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"✅ CSV ban gayi aur save hui: {save_path}")
    print(f"📊 Total rows: {len(df)}")

    return df


# ===== STEP 3: DATA EXPLORE KARO =====
def explore_data(df):
    print("\n📊 Dataset Overview:")
    print(f"   Shape        : {df.shape}")
    print(f"   Crops        : {df['crop'].nunique()} qismein")
    print(f"   Faslein      : {list(df['crop'].unique())}")
    print(f"\n   Har fasal ke samples:")
    for crop, count in df['crop'].value_counts().items():
        bar = '█' * (count // 30)
        print(f"   {crop:12s}: {count:4d}  {bar}")

    print(f"\n   Statistics:")
    print(df[['nitrogen','phosphorus','potassium','ph','temperature','rainfall']].describe().round(2))


# ===== STEP 4: DATA PREPARE KARO =====
def prepare_data(df):
    # Features
    feature_cols = ['nitrogen','phosphorus','potassium','ph','temperature','rainfall']
    X = df[feature_cols].copy()
    y = df['crop'].copy()

    # Label Encoding
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    print(f"\n🏷️  Crop Labels:")
    for i, crop in enumerate(le.classes_):
        urdu = df[df['crop'] == crop]['urdu_name'].iloc[0]
        print(f"   {i}: {crop:12s} ({urdu})")

    return X, y_encoded, le, feature_cols


# ===== STEP 5: MODEL TRAIN KARO =====
def train_model(X, y):
    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y       # har class equal proportion mein
    )

    print(f"\n🔀 Data Split:")
    print(f"   Training samples : {len(X_train)}")
    print(f"   Testing samples  : {len(X_test)}")

    # ---- Random Forest Model ----
    print("\n🤖 Random Forest train ho raha hai...")
    rf_model = RandomForestClassifier(
        n_estimators   = 200,
        max_depth      = 15,
        min_samples_split = 5,
        min_samples_leaf  = 2,
        random_state   = 42,
        n_jobs         = -1
    )
    rf_model.fit(X_train, y_train)

    # Cross Validation
    cv_scores = cross_val_score(rf_model, X_train, y_train, cv=5)
    print(f"   CV Accuracy  : {cv_scores.mean()*100:.2f}% ± {cv_scores.std()*100:.2f}%")

    # Test Accuracy
    y_pred    = rf_model.predict(X_test)
    test_acc  = accuracy_score(y_test, y_pred)
    print(f"   Test Accuracy: {test_acc*100:.2f}%")

    return rf_model, X_test, y_test


# ===== STEP 6: MODEL EVALUATE KARO =====
def evaluate_model(model, X_test, y_test, le):
    y_pred = model.predict(X_test)
    acc    = accuracy_score(y_test, y_pred)

    print(f"\n📈 Model Performance:")
    print(f"   Final Accuracy: {acc*100:.2f}%")

    # Har fasal ke liye precision/recall
    report = classification_report(
        y_test, y_pred,
        target_names=le.classes_,
        output_dict=True
    )

    print(f"\n   Per-crop accuracy:")
    for crop in le.classes_:
        if crop in report:
            prec = report[crop]['precision'] * 100
            rec  = report[crop]['recall']    * 100
            f1   = report[crop]['f1-score']  * 100
            print(f"   {crop:12s}: Precision={prec:.0f}%  Recall={rec:.0f}%  F1={f1:.0f}%")

    # Feature Importance
    feature_names = ['nitrogen','phosphorus','potassium','ph','temperature','rainfall']
    importances   = model.feature_importances_
    print(f"\n   Feature Importance:")
    for feat, imp in sorted(zip(feature_names, importances), key=lambda x: -x[1]):
        bar = '█' * int(imp * 50)
        print(f"   {feat:15s}: {imp:.3f}  {bar}")

    return acc


# ===== STEP 7: MODEL SAVE KARO =====
def save_model(model, le, feature_cols, accuracy):
    # backend/ml_models/ folder mein save karo
    save_dir = os.path.join(
        os.path.dirname(__file__), '..', 'backend', 'ml_models'
    )
    os.makedirs(save_dir, exist_ok=True)

    local_dir = os.path.join(os.path.dirname(__file__), '..', 'backend', 'ml_models')
    os.makedirs(local_dir, exist_ok=True)

    model_path   = os.path.join(local_dir, 'crop_model.pkl')
    encoder_path = os.path.join(local_dir, 'label_encoder.pkl')

    joblib.dump(model, model_path)
    joblib.dump(le,    encoder_path)

    # Model info bhi save karo
    model_info = {
        'accuracy':      round(accuracy * 100, 2),
        'feature_cols':  feature_cols,
        'crops':         list(le.classes_),
        'n_estimators':  model.n_estimators,
    }
    info_path = os.path.join(local_dir, 'model_info.pkl')
    joblib.dump(model_info, info_path)

    print(f"\n💾 Files save ho gayi:")
    print(f"   {model_path}")
    print(f"   {encoder_path}")
    print(f"   {info_path}")


# ===== STEP 8: PREDICTION TEST KARO =====
def test_predictions(model, le):
    print(f"\n🧪 Sample Predictions Test:")
    print("-" * 50)

    test_cases = [
        # (N,   P,  K,  pH,  Temp, Rain,  Expected)
        (80,  40, 40, 6.5, 18,   70,    'wheat'),
        (90,  50, 45, 6.2, 28,   200,   'rice'),
        (100, 50, 50, 6.8, 25,   80,    'maize'),
        (60,  35, 35, 7.0, 30,   60,    'cotton'),
        (45,  30, 30, 6.5, 15,   35,    'mustard'),
        (40,  35, 35, 7.2, 15,   25,    'chickpea'),
        (100, 50, 50, 6.8, 28,   150,   'sugarcane'),
        (50,  30, 30, 6.5, 32,   120,   'mango'),
    ]

    correct = 0
    for n, p, k, ph, temp, rain, expected in test_cases:
        features  = np.array([[n, p, k, ph, temp, rain]])
        pred_idx  = model.predict(features)[0]
        probs     = model.predict_proba(features)[0]
        conf      = round(float(max(probs)) * 100, 1)
        pred_name = le.inverse_transform([pred_idx])[0]

        status = '✅' if pred_name == expected else '⚠️ '
        if pred_name == expected:
            correct += 1
        print(f"   {status} Input:[N={n},P={p},K={k},pH={ph},T={temp},R={rain}]")
        print(f"      Predicted: {pred_name:12s} ({conf}%) | Expected: {expected}")

    print(f"\n   Test Score: {correct}/{len(test_cases)} correct")


# ===== MAIN FUNCTION =====
def main():
    # 1. Data load karo
    df = load_dataset()

    # 2. Explore karo
    explore_data(df)

    # 3. Prepare karo
    X, y, le, feature_cols = prepare_data(df)

    # 4. Train karo
    model, X_test, y_test = train_model(X, y)

    # 5. Evaluate karo
    accuracy = evaluate_model(model, X_test, y_test, le)

    # 6. Save karo
    save_model(model, le, feature_cols, accuracy)

    # 7. Test karo
    test_predictions(model, le)

    print("\n" + "=" * 55)
    print(f"🎉 Model tayar! Accuracy: {accuracy*100:.2f}%")
    print("📁 backend/ml_models/ mein save ho gaya")
    print("▶️  Ab chalao: cd backend && python app.py")
    print("=" * 55)


if __name__ == '__main__':
    main()