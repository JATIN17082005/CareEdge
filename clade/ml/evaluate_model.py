import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

sys.path.append(str(Path(__file__).resolve().parent))

from features import create_windows


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
    print("CAREEDGE CLADE — COMPLETE MODEL EVALUATION")
    print("=" * 70)

    # ---------------------------------------------------------
    # Load model
    # ---------------------------------------------------------
    print()
    print("Loading model...")

    model = joblib.load(MODEL_PATH)

    # ---------------------------------------------------------
    # Load data
    # ---------------------------------------------------------
    print("Loading dataset...")

    df = pd.read_csv(DATA_PATH)

    print("Raw dataset:", df.shape)

    # ---------------------------------------------------------
    # Create feature windows
    # ---------------------------------------------------------
    print()
    print("Creating temporal windows...")

    windowed = create_windows(df)

    print("Windowed dataset:", windowed.shape)

    # ---------------------------------------------------------
    # Prepare features
    # ---------------------------------------------------------
    X = windowed.drop(
        columns=["patient_id", "event", "window_id"]
    )

    y = windowed["event"]

    if "fall_detected" in X.columns:
        X["fall_detected"] = X["fall_detected"].astype(int)

    # ---------------------------------------------------------
    # Predict
    # ---------------------------------------------------------
    print()
    print("Running predictions...")

    predictions = model.predict(X)

    accuracy = accuracy_score(y, predictions)

    # ---------------------------------------------------------
    # Overall accuracy
    # ---------------------------------------------------------
    print()
    print("-" * 70)
    print("OVERALL PERFORMANCE")
    print("-" * 70)

    print()
    print(f"Accuracy across all 300 windows: {accuracy:.4f}")

    # ---------------------------------------------------------
    # Classification report
    # ---------------------------------------------------------
    print()
    print("Classification report:")

    print(
        classification_report(
            y,
            predictions,
            digits=4
        )
    )

    # ---------------------------------------------------------
    # Confusion matrix
    # ---------------------------------------------------------
    print("Confusion matrix:")

    labels = model.classes_

    matrix = confusion_matrix(
        y,
        predictions,
        labels=labels
    )

    matrix_df = pd.DataFrame(
        matrix,
        index=labels,
        columns=labels
    )

    print()
    print(matrix_df)

    # ---------------------------------------------------------
    # Per-event results
    # ---------------------------------------------------------
    print()
    print("-" * 70)
    print("PER-EVENT CORRECT PREDICTIONS")
    print("-" * 70)

    results = pd.DataFrame({
        "actual": y,
        "predicted": predictions
    })

    for event in labels:
        event_rows = results[results["actual"] == event]

        correct = (
            event_rows["actual"] ==
            event_rows["predicted"]
        ).sum()

        total = len(event_rows)

        event_accuracy = correct / total

        print(
            f"{event:15s}: "
            f"{correct}/{total} correct "
            f"({event_accuracy:.2%})"
        )

    print()
    print("=" * 70)
    print("EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()