from pathlib import Path

import joblib
import numpy as np
import pandas as pd


MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "early_warning_model.pkl"
)

DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "careedge_early_warning_data.csv"
)

WINDOW_SIZE = 50
WARNING_THRESHOLD = 0.50


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


def extract_features(window):
    features = {}

    for column in SENSOR_COLUMNS:
        values = window[column].astype(float)

        features[f"{column}_mean"] = values.mean()
        features[f"{column}_std"] = values.std()
        features[f"{column}_min"] = values.min()
        features[f"{column}_max"] = values.max()

    accel_mag = np.sqrt(
        window["accel_x"] ** 2
        + window["accel_y"] ** 2
        + window["accel_z"] ** 2
    )

    gyro_mag = np.sqrt(
        window["gyro_x"] ** 2
        + window["gyro_y"] ** 2
        + window["gyro_z"] ** 2
    )

    dynamic_accel = np.abs(accel_mag - 9.81)

    for name, values in [
        ("accel_mag", accel_mag),
        ("gyro_mag", gyro_mag),
        ("dynamic_accel", dynamic_accel),
    ]:
        features[f"{name}_mean"] = values.mean()
        features[f"{name}_std"] = values.std()
        features[f"{name}_min"] = values.min()
        features[f"{name}_max"] = values.max()

    features["accel_mag_first_last_change"] = (
        accel_mag.iloc[-1] - accel_mag.iloc[0]
    )

    features["gyro_mag_first_last_change"] = (
        gyro_mag.iloc[-1] - gyro_mag.iloc[0]
    )

    accel_diff = np.abs(np.diff(accel_mag))
    gyro_diff = np.abs(np.diff(gyro_mag))

    features["accel_mag_max_abs_diff"] = (
        accel_diff.max() if len(accel_diff) else 0.0
    )

    features["gyro_mag_max_abs_diff"] = (
        gyro_diff.max() if len(gyro_diff) else 0.0
    )

    for activity in ["sitting", "standing", "walking"]:
        features[f"activity_{activity}_ratio"] = (
            window["activity"] == activity
        ).mean()

    return features


def main():

    print("=" * 70)
    print("CAREEDGE — FALSE WARNING EVALUATION")
    print("=" * 70)

    print("\nLoading model...")
    model = joblib.load(MODEL_PATH)
    print("Model loaded successfully.")

    print("\nLoading dataset...")
    df = pd.read_csv(DATA_PATH)

    print("Dataset:", df.shape)

    non_fall = df[df["event"] != "fall"].copy()

    print("Non-fall samples:", len(non_fall))

    # ---------------------------------------------------------
    # Build ALL windows first
    # ---------------------------------------------------------

    print("\nExtracting non-fall windows...")

    all_features = []
    metadata = []

    for (patient_id, event), group in non_fall.groupby(
        ["patient_id", "event"]
    ):

        group = (
            group
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        for end_index in range(
            WINDOW_SIZE,
            len(group) + 1
        ):

            window = group.iloc[
                end_index - WINDOW_SIZE:end_index
            ]

            features = extract_features(window)

            all_features.append(features)

            metadata.append({
                "patient": patient_id,
                "event": event,
            })

    X = pd.DataFrame(all_features)

    X = X.reindex(
        columns=model.feature_names_in_
    )

    metadata_df = pd.DataFrame(metadata)

    print(
        "Total windows:",
        len(X)
    )

    # ---------------------------------------------------------
    # ONE batched prediction
    # ---------------------------------------------------------

    print("\nRunning batched model prediction...")

    probabilities = model.predict_proba(X)

    classes = list(model.classes_)

    pre_fall_index = classes.index("pre_fall")

    pre_fall_probabilities = (
        probabilities[:, pre_fall_index]
    )

    metadata_df["pre_fall_probability"] = (
        pre_fall_probabilities
    )

    metadata_df["warning"] = (
        pre_fall_probabilities
        >= WARNING_THRESHOLD
    )

    # ---------------------------------------------------------
    # Event-level results
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("EVENT-LEVEL RESULTS")
    print("=" * 70)
    print()

    grouped = metadata_df.groupby(
        ["patient", "event"]
    )

    for (patient, event), group in grouped:

        warnings = int(
            group["warning"].sum()
        )

        max_probability = (
            group["pre_fall_probability"].max()
            * 100
        )

        print(
            f"{patient} | "
            f"{event:<14} | "
            f"windows={len(group):3d} | "
            f"warnings={warnings:3d} | "
            f"max pre-fall probability="
            f"{max_probability:.2f}%"
        )

    # ---------------------------------------------------------
    # Overall summary
    # ---------------------------------------------------------

    total_windows = len(metadata_df)

    false_warning_windows = int(
        metadata_df["warning"].sum()
    )

    false_warning_rate = (
        false_warning_windows
        / total_windows
        * 100
    )

    print()
    print("=" * 70)
    print("FALSE WARNING SUMMARY")
    print("=" * 70)
    print()

    print(
        f"Total non-fall windows: "
        f"{total_windows}"
    )

    print(
        f"False warning windows: "
        f"{false_warning_windows}"
    )

    print(
        f"False warning rate: "
        f"{false_warning_rate:.2f}%"
    )

    print()

    if false_warning_windows == 0:

        print(
            "RESULT: No false pre-fall warnings "
            "were detected on non-fall events."
        )

    else:

        print(
            "RESULT: False pre-fall warnings "
            "were detected."
        )

    print()
    print("=" * 70)
    print("FALSE WARNING EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()