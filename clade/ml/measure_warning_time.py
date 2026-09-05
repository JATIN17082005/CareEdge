from pathlib import Path

import joblib
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

EARLY_WARNING_THRESHOLD = 0.50


def main():

    print("=" * 70)
    print("CAREEDGE — EARLY FALL WARNING TEST")
    print("=" * 70)

    # ---------------------------------------------------------
    # Load model
    # ---------------------------------------------------------
    print()
    print("Loading early-warning model...")

    model = joblib.load(MODEL_PATH)

    print("Model loaded successfully.")

    # ---------------------------------------------------------
    # Load dataset
    # ---------------------------------------------------------
    print()
    print("Loading early-warning dataset...")

    df = pd.read_csv(DATA_PATH)

    print("Dataset:", df.shape)

    # ---------------------------------------------------------
    # Select one complete fall sequence
    # ---------------------------------------------------------
    sequence = (
        df[
            (df["patient_id"] == "P001") &
            (df["event"] == "fall")
        ]
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    print()
    print("Fall sequence samples:", len(sequence))

    if len(sequence) < WINDOW_SIZE:
        raise ValueError(
            "Fall sequence contains fewer than 50 samples."
        )

    # ---------------------------------------------------------
    # Find the simulated impact point.
    #
    # FallMotionSimulator defines impact at:
    #
    # progress >= 0.45
    #
    # 250 samples at 50 Hz.
    # ---------------------------------------------------------
    impact_index = int(
        0.45 * (len(sequence) - 1)
    )

    impact_time = (
        impact_index / SAMPLE_RATE
    )

    print()
    print("Estimated impact sample:", impact_index)
    print(
        "Estimated impact time:",
        f"{impact_time:.2f} seconds"
    )

    # ---------------------------------------------------------
    # Rolling-window inference
    # ---------------------------------------------------------
    predictions = []

    for end_index in range(
        WINDOW_SIZE,
        len(sequence) + 1
    ):

        window = sequence.iloc[
            end_index - WINDOW_SIZE:end_index
        ].copy()

        # -----------------------------------------------------
        # Build the same features used during training.
        # -----------------------------------------------------

        features = {}

        sensor_columns = [
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

        for column in sensor_columns:

            values = window[column].astype(float)

            features[f"{column}_mean"] = values.mean()
            features[f"{column}_std"] = values.std()
            features[f"{column}_min"] = values.min()
            features[f"{column}_max"] = values.max()

        # -----------------------------------------------------
        # Motion magnitude
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
        )

        features["gyro_mag_max_abs_diff"] = (
            gyro_diff.max()
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
        # Fall flag
        # -----------------------------------------------------

        features["fall_detected"] = (
            window["fall_detected"]
            .astype(bool)
            .any()
        )

        X = pd.DataFrame([features])

        # Ensure exact feature order
        X = X.reindex(
            columns=model.feature_names_in_
        )

        if "fall_detected" in X.columns:
            X["fall_detected"] = (
                X["fall_detected"]
                .astype(int)
            )

        # -----------------------------------------------------
        # Predict
        # -----------------------------------------------------

        probabilities = model.predict_proba(X)[0]

        probability_dict = dict(
            zip(
                model.classes_,
                probabilities
            )
        )

        pre_fall_probability = probability_dict.get(
            "pre_fall",
            0.0
        )

        predicted_state = model.classes_[
            probabilities.argmax()
        ]

        current_time = (
            (end_index - 1)
            / SAMPLE_RATE
        )

        predictions.append({
            "sample": end_index - 1,
            "time": current_time,
            "predicted_state": predicted_state,
            "pre_fall_probability": pre_fall_probability,
        })

    # ---------------------------------------------------------
    # Find FIRST warning
    # ---------------------------------------------------------

    first_warning = None

    for result in predictions:

        if (
            result["pre_fall_probability"]
            >= EARLY_WARNING_THRESHOLD
        ):

            first_warning = result
            break

    print()
    print("=" * 70)
    print("EARLY WARNING RESULT")
    print("=" * 70)

    if first_warning is None:

        print()
        print(
            "No pre-fall warning crossed the "
            f"{EARLY_WARNING_THRESHOLD:.0%} threshold."
        )

    else:

        warning_time = first_warning["time"]

        lead_time = (
            impact_time - warning_time
        )

        print()
        print(
            "First warning sample:",
            first_warning["sample"]
        )

        print(
            "First warning time:",
            f"{warning_time:.2f} seconds"
        )

        print(
            "Pre-fall probability:",
            f'{first_warning["pre_fall_probability"]:.2%}'
        )

        print(
            "Predicted state:",
            first_warning["predicted_state"]
        )

        print(
            "Estimated impact time:",
            f"{impact_time:.2f} seconds"
        )

        print()
        print(
            "WARNING LEAD TIME:",
            f"{lead_time:.2f} seconds"
        )

        if lead_time > 0:

            print()
            print(
                "SUCCESS: CLADE warned before "
                "the simulated impact."
            )

        else:

            print()
            print(
                "WARNING: detection occurred "
                "at or after impact."
            )

    # ---------------------------------------------------------
    # Show predictions around warning/impact
    # ---------------------------------------------------------

    print()
    print("-" * 70)
    print("ROLLING PREDICTIONS")
    print("-" * 70)

    for result in predictions:

        # Only display the region close to impact
        if (
            result["time"] >= 1.0
            and result["time"] <= 3.0
        ):

            print(
                f'{result["time"]:5.2f}s | '
                f'{result["predicted_state"]:16s} | '
                f'pre_fall={result["pre_fall_probability"]:.2%}'
            )

    print()
    print("=" * 70)
    print("EARLY WARNING TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()