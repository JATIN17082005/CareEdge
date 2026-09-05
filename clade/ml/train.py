import sys
from pathlib import Path

import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import GroupShuffleSplit

sys.path.append(str(Path(__file__).resolve().parent))

DATA_PATH = "data/careedge_training_data.csv"
MODEL_PATH = "clade/ml/models/clade_model.pkl"


def load_data():
    """Load raw CareEdge sensor data."""
    return pd.read_csv(DATA_PATH)


def create_features(df):
    """
    Import the windowing pipeline and create ML features.
    """
    from features import create_windows

    return create_windows(df)


def split_by_patient(data):
    """
    Split windows by patient so that the same patient
    never appears in both training and test sets.
    """

    # First split: 80% train, 20% temporary
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.20,
        random_state=42,
    )

    train_idx, temp_idx = next(
        splitter.split(
            data,
            groups=data["patient_id"],
        )
    )

    train_data = data.iloc[train_idx]
    temp_data = data.iloc[temp_idx]

    # Second split: temporary → validation/test
    splitter_2 = GroupShuffleSplit(
        n_splits=1,
        test_size=0.50,
        random_state=42,
    )

    val_idx, test_idx = next(
        splitter_2.split(
            temp_data,
            groups=temp_data["patient_id"],
        )
    )

    val_data = temp_data.iloc[val_idx]
    test_data = temp_data.iloc[test_idx]

    return train_data, val_data, test_data


def main():

    print("=" * 60)
    print("CAREEDGE CLADE ML TRAINING")
    print("=" * 60)

    # ---------------------------------------------------------
    # Load and window data
    # ---------------------------------------------------------

    print("\nLoading dataset...")

    raw_data = load_data()

    print("Raw dataset:", raw_data.shape)

    print("\nCreating temporal windows...")

    data = create_features(raw_data)

    print("Windowed dataset:", data.shape)

    # ---------------------------------------------------------
    # Split
    # ---------------------------------------------------------

    train_data, val_data, test_data = split_by_patient(data)

    print("\nPatient-level split:")
    print("Training patients:", sorted(train_data["patient_id"].unique()))
    print("Validation patients:", sorted(val_data["patient_id"].unique()))
    print("Test patients:", sorted(test_data["patient_id"].unique()))

    print("\nSplit sizes:")
    print("Training:", train_data.shape)
    print("Validation:", val_data.shape)
    print("Test:", test_data.shape)

    # ---------------------------------------------------------
    # Prepare X / y
    # ---------------------------------------------------------

    DROP_COLUMNS = [
        "patient_id",
        "event",
        "window_id",
    ]

    X_train = train_data.drop(columns=DROP_COLUMNS)
    y_train = train_data["event"]

    X_val = val_data.drop(columns=DROP_COLUMNS)
    y_val = val_data["event"]

    X_test = test_data.drop(columns=DROP_COLUMNS)
    y_test = test_data["event"]

    # Convert boolean fall feature to integer.
    for X in [X_train, X_val, X_test]:
        X["fall_detected"] = X["fall_detected"].astype(int)

    # ---------------------------------------------------------
    # Train model
    # ---------------------------------------------------------

    print("\nTraining Random Forest...")

    model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1,
    )

    model.fit(X_train, y_train)

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    print("\nValidation performance:")

    val_predictions = model.predict(X_val)

    print(
        "Validation accuracy:",
        f"{accuracy_score(y_val, val_predictions):.4f}",
    )

    # ---------------------------------------------------------
    # Test
    # ---------------------------------------------------------

    print("\nFinal test performance:")

    test_predictions = model.predict(X_test)

    print(
        "Test accuracy:",
        f"{accuracy_score(y_test, test_predictions):.4f}",
    )

    print("\nClassification report:")

    print(
        classification_report(
            y_test,
            test_predictions,
            zero_division=0,
        )
    )

    print("Confusion matrix:")

    print(
        confusion_matrix(
            y_test,
            test_predictions,
        )
    )

    # ---------------------------------------------------------
    # Feature importance
    # ---------------------------------------------------------

    feature_importance = pd.Series(
        model.feature_importances_,
        index=X_train.columns,
    ).sort_values(ascending=False)

    print("\nTop 10 important features:")

    print(feature_importance.head(10))

    # ---------------------------------------------------------
    # Save model
    # ---------------------------------------------------------

    joblib.dump(model, MODEL_PATH)

    print("\nModel saved to:")
    print(MODEL_PATH)

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()