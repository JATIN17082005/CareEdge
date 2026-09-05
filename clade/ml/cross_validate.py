import sys
from pathlib import Path

import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import LeaveOneGroupOut


# Make features.py importable
sys.path.append(str(Path(__file__).resolve().parent))

from features import create_windows


DATA_PATH = "data/careedge_training_data.csv"


def prepare_dataset():
    """Load raw sensor data and create ML windows."""

    print("Loading dataset...")

    raw_data = pd.read_csv(DATA_PATH)

    print("Raw dataset:", raw_data.shape)

    print("\nCreating windows...")

    data = create_windows(raw_data)

    print("Windowed dataset:", data.shape)

    return data


def prepare_features(data):
    """Separate ML features from labels and identifiers."""

    drop_columns = [
        "patient_id",
        "event",
        "window_id",
        "fall_detected",
    ]

    X = data.drop(
        columns=drop_columns
    ).copy()

    y = data["event"]

    # Keep the patient identifier separately for grouping.
    groups = data["patient_id"]

    return X, y, groups


def main():

    print("=" * 70)
    print("CAREEDGE CLADE — PATIENT-LEVEL CROSS VALIDATION")
    print("=" * 70)

    # ---------------------------------------------------------
    # Load data
    # ---------------------------------------------------------

    data = prepare_dataset()

    X, y, groups = prepare_features(data)

    # ---------------------------------------------------------
    # Leave-One-Patient-Out CV
    # ---------------------------------------------------------

    logo = LeaveOneGroupOut()

    results = []

    print("\nPatients:", sorted(groups.unique()))
    print("\nStarting patient-level evaluation...\n")

    for fold, (train_idx, test_idx) in enumerate(
        logo.split(X, y, groups),
        start=1,
    ):

        train_patients = sorted(
            groups.iloc[train_idx].unique()
        )

        test_patients = sorted(
            groups.iloc[test_idx].unique()
        )

        X_train = X.iloc[train_idx]
        X_test = X.iloc[test_idx]

        y_train = y.iloc[train_idx]
        y_test = y.iloc[test_idx]

        # -----------------------------------------------------
        # Train
        # -----------------------------------------------------

        model = RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            class_weight="balanced",
            n_jobs=-1,
        )

        model.fit(
            X_train,
            y_train,
        )

        # -----------------------------------------------------
        # Predict
        # -----------------------------------------------------

        predictions = model.predict(X_test)

        accuracy = accuracy_score(
            y_test,
            predictions,
        )

        precision, recall, f1, _ = (
            precision_recall_fscore_support(
                y_test,
                predictions,
                average="macro",
                zero_division=0,
            )
        )

        results.append(
            {
                "patient": test_patients[0],
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            }
        )

        print(
            f"Fold {fold:02d} | "
            f"Test patient: {test_patients[0]} | "
            f"Accuracy: {accuracy:.4f} | "
            f"Macro F1: {f1:.4f}"
        )

    # ---------------------------------------------------------
    # Results
    # ---------------------------------------------------------

    results_df = pd.DataFrame(results)

    print("\n")
    print("=" * 70)
    print("CROSS-VALIDATION RESULTS")
    print("=" * 70)

    print("\nPer-patient results:\n")

    print(
        results_df.to_string(
            index=False,
            formatters={
                "accuracy": "{:.4f}".format,
                "precision": "{:.4f}".format,
                "recall": "{:.4f}".format,
                "f1": "{:.4f}".format,
            },
        )
    )

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    print("\n")
    print("=" * 70)
    print("OVERALL PERFORMANCE")
    print("=" * 70)

    print(
        "\nMean accuracy:",
        f"{results_df['accuracy'].mean():.4f}",
    )

    print(
        "Accuracy std:",
        f"{results_df['accuracy'].std():.4f}",
    )

    print(
        "Mean macro precision:",
        f"{results_df['precision'].mean():.4f}",
    )

    print(
        "Mean macro recall:",
        f"{results_df['recall'].mean():.4f}",
    )

    print(
        "Mean macro F1:",
        f"{results_df['f1'].mean():.4f}",
    )

    print("\nCross-validation complete.")


if __name__ == "__main__":
    main()