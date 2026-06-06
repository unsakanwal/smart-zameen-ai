from typing import Dict, Any
import numpy as np
import joblib

class EndpointHandler():
    def __init__(self, path: str = ""):
        """
        Initialize the model and encoder when the endpoint starts.
        """
        self.model = joblib.load(f"{path}/soil.pkl")
        self.label_encoder = joblib.load(f"{path}/label_encoder.pkl")

    def __call__(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform prediction using the trained model.
        Expects input data in the format:
            {
                "inputs": [N, P, K, temperature, humidity, ph, rainfall]
            }
        Returns:
            {
                "crop": predicted_crop_name
            }
        """
        inputs = data.get("inputs")
        if inputs is None:
            return {"error": "No input data provided."}

        inputs = np.array(inputs).reshape(1, -1)
        prediction = self.model.predict(inputs)
        crop = self.label_encoder.inverse_transform(prediction)

        return {"crop": crop[0]}
