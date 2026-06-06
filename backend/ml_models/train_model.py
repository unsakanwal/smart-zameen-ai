import pandas as pd
import numpy as np
import os
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score

print("=" * 50)
print("Smart Agriculture - Improved Training")
print("=" * 50)


# ===== LOAD DATA =====
def load_dataset():
    path = os.path.join(
        os.path.dirname(__file__),
        '..', '..', 'model-training', 'dataset', 'crops_pakistan.csv'
    )

    if not os.path.exists(path):
        print("[ERROR] Dataset nahi mila!")
        exit()

    df = pd.read_csv(path)

    print(f"[OK] Dataset loaded: {len(df)} rows")

    # Clean columns
    df = df[['nitrogen','phosphorus','potassium','ph',
             'temperature','rainfall','season','region','crop']]

    return df

def expand_data(df, times=10):
    import numpy as np
    new_rows = []

    for _, row in df.iterrows():
        for _ in range(times):
            new_rows.append({
                'nitrogen': row['nitrogen'] + np.random.uniform(-5, 5),
                'phosphorus': row['phosphorus'] + np.random.uniform(-5, 5),
                'potassium': row['potassium'] + np.random.uniform(-5, 5),
                'ph': row['ph'] + np.random.uniform(-0.3, 0.3),
                'temperature': row['temperature'] + np.random.uniform(-2, 2),
                'rainfall': row['rainfall'] + np.random.uniform(-10, 10),
                'season': row['season'],
                'region': row['region'],
                'crop': row['crop']
            })

    return pd.DataFrame(new_rows)

# ===== PREPROCESS =====
def preprocess(df):
    print("\n[INFO] Preprocessing...")

    # Encode categorical
    le_season = LabelEncoder()
    le_region = LabelEncoder()
    le_crop   = LabelEncoder()

    df['season'] = le_season.fit_transform(df['season'])
    df['region'] = le_region.fit_transform(df['region'])
    df['crop']   = le_crop.fit_transform(df['crop'])

    X = df[['nitrogen','phosphorus','potassium',
            'ph','temperature','rainfall','season','region']]
    y = df['crop']

    return X, y, le_crop, le_season, le_region


# ===== TRAIN =====
def train_model(X, y):
    print("\n[INFO] Training model...")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=500,
        max_depth=None,
        min_samples_split=2,
        min_samples_leaf=1,
        max_features='sqrt',
        random_state=42,
        n_jobs=-1
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print(f"[OK] Test Accuracy: {acc * 100:.2f}%")

    # Cross Validation
    cv_scores = cross_val_score(model, X, y, cv=5)
    print(f"[OK] CV Accuracy: {cv_scores.mean() * 100:.2f}%")

    return model


# ===== SAVE =====
def save_all(model, le_crop, le_season, le_region):
    # Save the .pkl artifacts next to this script (backend/ml_models/).
    out = os.path.dirname(os.path.abspath(__file__))

    joblib.dump(model,     os.path.join(out, "crop_model.pkl"))
    joblib.dump(le_crop,   os.path.join(out, "le_crop.pkl"))
    joblib.dump(le_season, os.path.join(out, "le_season.pkl"))
    joblib.dump(le_region, os.path.join(out, "le_region.pkl"))

    print("[OK] Sab save ho gaya")


# ===== MAIN =====
if __name__ == "__main__":
    df_real = load_dataset()
    df_expand = expand_data(df_real, times=15)
    df = pd.concat([df_real, df_expand], ignore_index=True)
    print("Total rows after expansion:", len(df))
    X, y, le_crop, le_season, le_region = preprocess(df)
    model = train_model(X, y)
    save_all(model, le_crop, le_season, le_region)

    print("\n[INFO] DONE! Run: python app.py")