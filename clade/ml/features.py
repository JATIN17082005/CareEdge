import pandas as pd
import numpy as np


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

ACTIVITIES = ["sitting", "standing", "walking"]


def create_windows(df, window_size=50):
    windows = []

    # Reconstruct the temporal order of each patient/event sequence
    df = df.sort_values(
        ["patient_id", "event", "timestamp"]
    ).reset_index(drop=True)

    for (patient_id, event), group in df.groupby(
        ["patient_id", "event"]
    ):
        group = group.reset_index(drop=True)

        num_windows = len(group) // window_size

        for window_idx in range(num_windows):
            start = window_idx * window_size
            end = start + window_size

            window = group.iloc[start:end]

            if len(window) < window_size:
                continue

            features = {
                "patient_id": patient_id,
                "event": event,
                "window_id": window_idx,
            }

            # ---------------------------------------------------------
            # Basic statistical features for each raw sensor
            # ---------------------------------------------------------
            for column in SENSOR_COLUMNS:
                values = window[column].astype(float)

                features[f"{column}_mean"] = values.mean()
                features[f"{column}_std"] = values.std()
                features[f"{column}_min"] = values.min()
                features[f"{column}_max"] = values.max()

            # ---------------------------------------------------------
            # Temporal / motion-derived features
            # ---------------------------------------------------------

            accel_x = window["accel_x"].astype(float)
            accel_y = window["accel_y"].astype(float)
            accel_z = window["accel_z"].astype(float)

            gyro_x = window["gyro_x"].astype(float)
            gyro_y = window["gyro_y"].astype(float)
            gyro_z = window["gyro_z"].astype(float)

            # Acceleration magnitude
            accel_mag = np.sqrt(
                accel_x**2 +
                accel_y**2 +
                accel_z**2
            )

            # Angular velocity magnitude
            gyro_mag = np.sqrt(
                gyro_x**2 +
                gyro_y**2 +
                gyro_z**2
            )

            # Dynamic acceleration relative to gravity
            dynamic_accel = np.abs(accel_mag - 9.81)

            # Statistical features of derived motion signals
            for name, values in [
                ("accel_mag", accel_mag),
                ("gyro_mag", gyro_mag),
                ("dynamic_accel", dynamic_accel),
            ]:
                features[f"{name}_mean"] = values.mean()
                features[f"{name}_std"] = values.std()
                features[f"{name}_min"] = values.min()
                features[f"{name}_max"] = values.max()

            # ---------------------------------------------------------
            # Temporal change features
            # ---------------------------------------------------------

            features["accel_mag_first_last_change"] = (
                accel_mag.iloc[-1] - accel_mag.iloc[0]
            )

            features["gyro_mag_first_last_change"] = (
                gyro_mag.iloc[-1] - gyro_mag.iloc[0]
            )

            # Largest sample-to-sample acceleration change
            accel_diff = np.abs(np.diff(accel_mag))

            if len(accel_diff) > 0:
                features["accel_mag_max_abs_diff"] = accel_diff.max()
            else:
                features["accel_mag_max_abs_diff"] = 0.0

            # Largest sample-to-sample gyro change
            gyro_diff = np.abs(np.diff(gyro_mag))

            if len(gyro_diff) > 0:
                features["gyro_mag_max_abs_diff"] = gyro_diff.max()
            else:
                features["gyro_mag_max_abs_diff"] = 0.0

            # ---------------------------------------------------------
            # Activity distribution
            # ---------------------------------------------------------

            for activity in ACTIVITIES:
                features[f"activity_{activity}_ratio"] = (
                    window["activity"] == activity
                ).mean()

            # Whether any simulated fall flag occurred
            features["fall_detected"] = (
                window["fall_detected"]
                .astype(bool)
                .any()
            )

            windows.append(features)

    return pd.DataFrame(windows)


if __name__ == "__main__":
    data_path = "data/careedge_training_data.csv"

    df = pd.read_csv(data_path)

    print("Raw dataset:", df.shape)

    windowed = create_windows(df)

    print("Windowed dataset:", windowed.shape)

    print()
    print("Events:")
    print(windowed["event"].value_counts())

    print()
    print("Feature count:", len(windowed.columns))

    print()
    print("Feature columns:")
    for column in windowed.columns:
        print(column)

    print()
    print(windowed.head())