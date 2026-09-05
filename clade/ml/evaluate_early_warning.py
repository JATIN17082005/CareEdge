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
SAMPLE_RATE = 50

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

    # Raw sensor statistics
    for column in SENSOR_COLUMNS:
        values = window[column].astype(float)

        features[f"{column}_mean"] = values.mean()
        features[f"{column}_std"] = values.std()
        features[f"{column}_min"] = values.min()
        features[f"{column}_max"] = values.max()

    # Motion magnitudes
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

    dynamic_accel = np.abs(
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

    # Temporal features
    features["accel_mag_first_last_change"] = (
        accel_mag.iloc[-1] - accel_mag.iloc[0]
    )

    features["gyro_mag_first_last_change"] = (
        gyro_mag.iloc[-1] - gyro_mag.iloc[0]
    )

    accel_diff = np.abs(
        np.diff(accel_mag)
    )

    gyro_diff = np.abs(
        np.diff(gyro_mag)
    )

    features["accel_mag_max_abs_diff"] = (
        accel_diff.max()
        if len(accel_diff)
        else 0.0
    )

    features["gyro_mag_max_abs_diff"] = (
        gyro_diff.max()
        if len(gyro_diff)
        else 0.0
    )

    # Activity ratios
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

    return pd.DataFrame([features])


def main():

    print("=" * 70)
    print("CAREEDGE — 10-PATIENT EARLY WARNING EVALUATION")
    print("=" * 70)

    print()
    print("Loading model...")

    model = joblib.load(MODEL_PATH)

    print("Model loaded successfully.")

    print()
    print("Loading dataset...")

    df = pd.read_csv(DATA_PATH)

    print("Dataset:", df.shape)

    patients = sorted(
        df[df["event"] == "fall"]["patient_id"].unique()
    )

    results = []

    for patient_id in patients:

        sequence = (
            df[
                (df["patient_id"] == patient_id)
                & (df["event"] == "fall")
            ]
            .sort_values("timestamp")
            .reset_index(drop=True)
        )

        impact_index = int(
            0.45 * (len(sequence) - 1)
        )

        impact_time = (
            impact_index / SAMPLE_RATE
        )

        first_warning = None

        # Rolling 50-sample inference
        for end_index in range(
            WINDOW_SIZE,
            len(sequence) + 1
        ):

            window = sequence.iloc[
                end_index - WINDOW_SIZE:end_index
            ].copy()

            X = extract_features(window)

            X = X.reindex(
                columns=model.feature_names_in_
            )

            probabilities = model.predict_proba(X)[0]

            probability_dict = dict(
                zip(
                    model.classes_,
                    probabilities
                )
            )

            pre_fall_probability = (
                probability_dict.get(
                    "pre_fall",
                    0.0
                )
            )

            current_time = (
                (end_index - 1)
                / SAMPLE_RATE
            )

            if (
                pre_fall_probability
                >= WARNING_THRESHOLD
            ):
                first_warning = {
                    "time": current_time,
                    "probability": pre_fall_probability,
                }
                break

        if first_warning is None:

            results.append({
                "patient": patient_id,
                "warning_time": None,
                "impact_time": impact_time,
                "lead_time": None,
                "warning": "NO",
            })

        else:

            lead_time = (
                impact_time
                - first_warning["time"]
            )

            results.append({
                "patient": patient_id,
                "warning_time": first_warning["time"],
                "impact_time": impact_time,
                "lead_time": lead_time,
                "warning": (
                    "YES"
                    if lead_time > 0
                    else "NO"
                ),
            })

    results_df = pd.DataFrame(results)

    print()
    print("=" * 70)
    print("PATIENT RESULTS")
    print("=" * 70)

    print()

    for _, row in results_df.iterrows():

        if pd.isna(row["lead_time"]):

            print(
                f'{row["patient"]}: '
                f'NO WARNING'
            )

        else:

            print(
                f'{row["patient"]}: '
                f'warning={row["warning_time"]:.2f}s | '
                f'impact={row["impact_time"]:.2f}s | '
                f'lead={row["lead_time"]:.2f}s'
            )

    # ---------------------------------------------------------
    # Summary
    # ---------------------------------------------------------

    valid_lead_times = (
        results_df["lead_time"]
        .dropna()
    )

    successful_warnings = (
        results_df["warning"] == "YES"
    ).sum()

    print()
    print("=" * 70)
    print("EARLY WARNING SUMMARY")
    print("=" * 70)

    print()

    print(
        f"Patients tested: "
        f"{len(results_df)}"
    )

    print(
        f"Successful early warnings: "
        f"{successful_warnings}/{len(results_df)}"
    )

    if len(valid_lead_times) > 0:

        print(
            f"Average lead time: "
            f"{valid_lead_times.mean():.2f} seconds"
        )

        print(
            f"Minimum lead time: "
            f"{valid_lead_times.min():.2f} seconds"
        )

        print(
            f"Maximum lead time: "
            f"{valid_lead_times.max():.2f} seconds"
        )

    print()
    print("=" * 70)
    print("10-PATIENT EVALUATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()