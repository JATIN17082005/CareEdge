from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupShuffleSplit


DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "careedge_early_warning_data.csv"
)

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "early_warning_model.pkl"
)


SENSOR_COLUMNS = [
    "heart_rate",
    "spo2",
    "temperature",
    "systolic_bp",
    "diastolic_bp",
    "accel_x",
    "accel_y",
    "accel_z",
    "gyro_x",
    "gyro_y",
    "gyro_z",
]


def create_windows(df, window_size=50):
    """
    Create temporal windows while preserving the early-warning label.

    Each patient's fall sequence is reconstructed using timestamp.
    """

    windows = []

    df = df.sort_values(
        ["patient_id", "timestamp"]
    ).reset_index(drop=True)

    for patient_id, patient_group in df.groupby(
        "patient_id"
    ):

        patient_group = patient_group.sort_values(
            "timestamp"
        ).reset_index(drop=True)

        # Create windows over the complete patient timeline.
        # This allows windows to contain transitions between
        # normal, pre-fall, fall-transition and fall states.
        for start in range(
            0,
            len(patient_group) - window_size + 1
        ):

            window = patient_group.iloc[
                start:start + window_size
            ]

            features = {
                "patient_id": patient_id,
                "window_start": start,
            }

            # -----------------------------------------------------
            # Raw sensor statistics
            # -----------------------------------------------------
            for column in SENSOR_COLUMNS:

                values = window[column].astype(float)

                features[f"{column}_mean"] = values.mean()
                features[f"{column}_std"] = values.std()
                features[f"{column}_min"] = values.min()
                features[f"{column}_max"] = values.max()

            # -----------------------------------------------------
            # Motion magnitude features
            # -----------------------------------------------------
            accel_mag = (
                window["accel_x"] ** 2
                + window["accel_y"] ** 2
                + window["accel_z"] ** 2
            ) ** 0.5

            gyro_mag = (
                window["gyro_x"] ** 2
                + window["gyro_y"] ** 2
                + window["gyro_z"] ** 2
            ) ** 0.5

            dynamic_accel = abs(
                accel_mag - 9.81
            )

            for name, values in [
                ("accel_mag", accel_mag),
                ("gyro_mag", gyro_mag),
                ("dynamic_accel", dynamic_accel),
            ]:

                features[f"{name}_mean"] = values.mean()
                features[f"{name}_std"] = values.std()
                features[f"{name}_min"] = values.min()
                features[f"{name}_max"] = values.max()

            # -----------------------------------------------------
            # Temporal features
            # -----------------------------------------------------
            features["accel_mag_first_last_change"] = (
                accel_mag.iloc[-1]
                - accel_mag.iloc[0]
            )

            features["gyro_mag_first_last_change"] = (
                gyro_mag.iloc[-1]
                - gyro_mag.iloc[0]
            )

            accel_diff = abs(
                accel_mag.diff()
            ).dropna()

            gyro_diff = abs(
                gyro_mag.diff()
            ).dropna()

            features["accel_mag_max_abs_diff"] = (
                accel_diff.max()
                if not accel_diff.empty
                else 0.0
            )

            features["gyro_mag_max_abs_diff"] = (
                gyro_diff.max()
                if not gyro_diff.empty
                else 0.0
            )

            # -----------------------------------------------------
            # Activity ratios
            # -----------------------------------------------------
            for activity in [
                "sitting",
                "standing",
                "walking",
            ]:

                features[
                    f"activity_{activity}_ratio"
                ] = (
                    window["activity"] == activity
                ).mean()

            # -----------------------------------------------------
            # EARLY-WARNING LABEL
            #
            # Use the label of the LAST sample in the window.
            #
            # This means:
            # "Given everything observed up to now,
            #  what state is the patient currently in?"
            # -----------------------------------------------------
            features["early_warning_event"] = (
                window["early_warning_event"].iloc[-1]
            )

            windows.append(features)

    return pd.DataFrame(windows)


def main():

    print("=" * 70)
    print("CAREEDGE — EARLY WARNING MODEL TRAINING")
    print("=" * 70)

    print()
    print("Loading early-warning dataset...")

    df = pd.read_csv(DATA_PATH)

    print("Dataset:", df.shape)

    print()
    print("Creating temporal windows...")

    windowed = create_windows(df)

    print("Windowed dataset:", windowed.shape)

    print()
    print("Window labels:")
    print(
        windowed["early_warning_event"]
        .value_counts()
    )

    # ---------------------------------------------------------
    # Features and target
    # ---------------------------------------------------------
    X = windowed.drop(
        columns=[
            "patient_id",
            "window_start",
            "early_warning_event",
        ]
    )

    y = windowed["early_warning_event"]

    groups = windowed["patient_id"]

    # ---------------------------------------------------------
    # Patient-level split
    # ---------------------------------------------------------
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.20,
        random_state=42,
    )

    train_idx, test_idx = next(
        splitter.split(
            X,
            y,
            groups=groups,
        )
    )

    X_train = X.iloc[train_idx]
    X_test = X.iloc[test_idx]

    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]

    print()
    print("Training windows:", X_train.shape)
    print("Test windows:", X_test.shape)

    print()
    print("Training patients:")
    print(
        sorted(
            groups.iloc[train_idx].unique()
        )
    )

    print()
    print("Test patients:")
    print(
        sorted(
            groups.iloc[test_idx].unique()
        )
    )

    # ---------------------------------------------------------
    # Train model
    # ---------------------------------------------------------
    print()
    print("Training Early-Warning Random Forest...")

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

    # ---------------------------------------------------------
    # Evaluate
    # ---------------------------------------------------------
    predictions = model.predict(X_test)

    print()
    print("=" * 70)
    print("EARLY WARNING MODEL PERFORMANCE")
    print("=" * 70)

    print()
    print(
        classification_report(
            y_test,
            predictions,
            digits=4,
        )
    )

    print("Confusion matrix:")

    labels = model.classes_

    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=labels,
    )

    print(
        pd.DataFrame(
            matrix,
            index=labels,
            columns=labels,
        )
    )

    # ---------------------------------------------------------
    # Save
    # ---------------------------------------------------------
    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        MODEL_PATH,
    )

    print()
    print("Model saved to:")
    print(MODEL_PATH)

    print()
    print("=" * 70)
    print("EARLY WARNING TRAINING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()