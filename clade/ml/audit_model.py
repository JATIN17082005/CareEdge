import sys
from pathlib import Path

import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import GroupShuffleSplit


# Make features.py importable
sys.path.append(str(Path(__file__).resolve().parent))

from features import create_windows


DATA_PATH = "data/careedge_training_data.csv"


def prepare_data():

    print("Loading raw dataset...")

    raw_data = pd.read_csv(DATA_PATH)

    print("Raw dataset:", raw_data.shape)

    print("\nCreating windows...")

    data = create_windows(raw_data)

    print("Windowed dataset:", data.shape)

    return data


def split_by_patient(data):

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.20,
        random_state=42,
    )

    train_idx, test_idx = next(
        splitter.split(
            data,
            groups=data["patient_id"],
        )
    )

    train_data = data.iloc[train_idx]
    test_data = data.iloc[test_idx]

    print("\nTraining patients:")
    print(sorted(train_data["patient_id"].unique()))

    print("\nTest patients:")
    print(sorted(test_data["patient_id"].unique()))

    return train_data, test_data


def train_and_evaluate(
    train_data,
    test_data,
    include_fall_detector=True,
):

    DROP_COLUMNS = [
        "patient_id",
        "event",
        "window_id",
    ]

    X_train = train_data.drop(
        columns=DROP_COLUMNS
    ).copy()

    X_test = test_data.drop(
        columns=DROP_COLUMNS
    ).copy()

    y_train = train_data["event"]
    y_test = test_data["event"]

    # Convert boolean to integer
    X_train["fall_detected"] = (
        X_train["fall_detected"].astype(int)
    )

    X_test["fall_detected"] = (
        X_test["fall_detected"].astype(int)
    )

    # Audit: optionally remove direct fall detector
    if not include_fall_detector:

        X_train = X_train.drop(
            columns=["fall_detected"]
        )

        X_test = X_test.drop(
            columns=["fall_detected"]
        )

    model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    return model, accuracy, y_test, predictions


def main():

    print("=" * 65)
    print("CAREEDGE CLADE MODEL AUDIT")
    print("=" * 65)

    data = prepare_data()

    train_data, test_data = split_by_patient(data)

    # ---------------------------------------------------------
    # MODEL A
    # ---------------------------------------------------------

    print("\n")
    print("=" * 65)
    print("MODEL A — SENSOR + FALL DETECTOR")
    print("=" * 65)

    model_a, accuracy_a, y_test_a, predictions_a = (
        train_and_evaluate(
            train_data,
            test_data,
            include_fall_detector=True,
        )
    )

    print(
        "\nTest accuracy:",
        f"{accuracy_a:.4f}",
    )

    print("\nClassification report:")

    print(
        classification_report(
            y_test_a,
            predictions_a,
            zero_division=0,
        )
    )

    # ---------------------------------------------------------
    # MODEL B
    # ---------------------------------------------------------

    print("\n")
    print("=" * 65)
    print("MODEL B — SENSOR ONLY")
    print("=" * 65)

    model_b, accuracy_b, y_test_b, predictions_b = (
        train_and_evaluate(
            train_data,
            test_data,
            include_fall_detector=False,
        )
    )

    print(
        "\nTest accuracy:",
        f"{accuracy_b:.4f}",
    )

    print("\nClassification report:")

    print(
        classification_report(
            y_test_b,
            predictions_b,
            zero_division=0,
        )
    )

    # ---------------------------------------------------------
    # COMPARISON
    # ---------------------------------------------------------

    print("\n")
    print("=" * 65)
    print("MODEL COMPARISON")
    print("=" * 65)

    print(
        f"\nWith fall detector : "
        f"{accuracy_a:.4f}"
    )

    print(
        f"Sensor only        : "
        f"{accuracy_b:.4f}"
    )

    print(
        "\nAccuracy difference:",
        f"{(accuracy_a - accuracy_b):.4f}",
    )
        # ---------------------------------------------------------
    # FEATURE IMPORTANCE
    # ---------------------------------------------------------

    print("\n")
    print("=" * 65)
    print("TOP CLADE FEATURES")
    print("=" * 65)

    feature_names = train_data.drop(
        columns=[
            "patient_id",
            "event",
            "window_id",
            "fall_detected",
        ]
    ).columns

    importance = pd.Series(
        model_b.feature_importances_,
        index=feature_names,
    ).sort_values(
        ascending=False
    )

    print("\nTop 15 sensor features:")

    print(
        importance.head(15).to_string()
    )

    print("\nAudit complete.")


if __name__ == "__main__":
    main()