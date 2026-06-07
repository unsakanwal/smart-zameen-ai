import joblib
import numpy as np

# Load model and label encoder
model = joblib.load("soil.pkl")
label_encoder = joblib.load("label_encoder.pkl")

def predict(inputs):
    """
    Inputs: List of 7 features [N, P, K, temperature, humidity, ph, rainfall]
    """
    input_array = np.array(inputs).reshape(1, -1)
    prediction = model.predict(input_array)
    crop = label_encoder.inverse_transform(prediction)
    return crop[0]
