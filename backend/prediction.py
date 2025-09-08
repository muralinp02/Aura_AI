# backend/prediction.py
import os
import joblib
import pandas as pd

def _candidate_paths():
    """Return likely locations for model.pkl."""
    here = os.path.dirname(__file__)                          # .../backend
    return [
        os.path.join(here, "models", "model.pkl"),            # .../backend/models/model.pkl  ← your case
        os.path.join(here, "..", "models", "model.pkl"),      # .../models/model.pkl
    ]

def load_model():
    """Load a trained model, or return a safe dummy model if not found."""
    for p in _candidate_paths():
        p = os.path.abspath(p)
        if os.path.exists(p):
            print(f"[prediction] Loading model from: {p}")
            return joblib.load(p)

    # Fallback: dummy model so the app doesn't 500 while you develop
    print("⚠️ [prediction] model.pkl not found in any known location — using dummy model.")
    class DummyModel:
        def predict(self, X):
            # Return a low-risk score or labels of your choice
            try:
                n = len(X)
            except Exception:
                n = 1
            return [0] * n  # e.g., all zeros = 'low'
    return DummyModel()

def preprocess_for_mdp(df: pd.DataFrame) -> pd.DataFrame:
    """
    If your uploaded CSV is already preprocessed (numeric, scaled),
    just return it. Add encoding/scaling here if you need to handle raw data.
    """
    return df

def predict(file):
    """Make predictions on uploaded CSV file."""
    model = load_model()
    df = pd.read_csv(file.file)
    df_processed = preprocess_for_mdp(df)
    preds = model.predict(df_processed)
    # Ensure it's JSON-serializable
    return {"predictions": [int(p) if isinstance(p, (int, float)) else p for p in preds]}
