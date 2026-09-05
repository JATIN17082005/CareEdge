import sys
from pathlib import Path

import joblib
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))

from features import create_windows
from risk_engine import calculate_risk


MODEL_PATH = (
    Path(__file__).resolve().parent /
    "models" /
    "clade_model.pkl"
)

DATA_PATH = (
    Path(__file__).resolve().parents[2] /
    "data" /
    "careedge_training_data.csv"
)


def main():
    print("=" * 70)
    print("CAREEDGE CLADE — MODEL INFERENCE")
    print("=" * 70)

    # ---------------------------------------------------------
    # Load trained model
    # ---------------------------------------------------------
    print()
    print("Loading trained model...")

    model = joblib.load(MODEL_PATH)

    print("Model loaded successfully.")

    # ---------------------------------------------------------
    # Load sensor dataset
    # ---------------------------------------------------------
    print()
    print("Loading sensor data...")

    df = pd.read_csv(DATA_PATH)

    print("Raw dataset:", df.shape)

    # ---------------------------------------------------------
    # Create temporal feature windows
    # ---------------------------------------------------------
    print()
    print("Creating temporal windows...")

    windowed = create_windows(df)

    print("Windowed dataset:", windowed.shape)

    # ---------------------------------------------------------
    # Select one window for demonstration
    # ---------------------------------------------------------
    sample = windowed.iloc[[0]].copy()

    actual_event = sample["event"].iloc[0]
    patient_id = sample["patient_id"].iloc[0]
    window_id = sample["window_id"].iloc[0]

    X = sample.drop(
        columns=["patient_id", "event", "window_id"]
    )

    # Convert boolean fall flag to numeric
    if "fall_detected" in X.columns:
        X["fall_detected"] = X["fall_detected"].astype(int)

    # ---------------------------------------------------------
    # Generate model probabilities
    # ---------------------------------------------------------
    probabilities = model.predict_proba(X)[0]

    probability_dict = dict(
        zip(model.classes_, probabilities)
    )

    # ---------------------------------------------------------
    # Convert probabilities into risk information
    # ---------------------------------------------------------
    result = calculate_risk(probability_dict)

    # ---------------------------------------------------------
    # Display result
    # ---------------------------------------------------------
    print()
    print("-" * 70)
    print("INFERENCE RESULT")
    print("-" * 70)

    print()
    print("Patient ID      :", patient_id)
    print("Window ID       :", window_id)
    print("Actual event    :", actual_event)
    print("Predicted event :", result["predicted_event"])
    print("Confidence      :", f'{result["confidence"]}%')
    print("Risk score      :", result["risk_score"])
    print("Risk level      :", result["risk_level"])
    print("Reason          :", result["reason"])

    print()
    print("Event probabilities:")

    for event, probability in result["probabilities"].items():
        print(f"  {event:15s}: {probability}%")

    print()
    print("-" * 70)


if __name__ == "__main__":
    main()