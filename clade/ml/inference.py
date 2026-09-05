from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from risk_engine import calculate_risk
from early_warning_engine import calculate_early_warning
from unified_decision import make_unified_decision


BASE_DIR = Path(__file__).resolve().parent

MAIN_MODEL_PATH = (
    BASE_DIR / "models" / "clade_model.pkl"
)

EARLY_WARNING_MODEL_PATH = (
    BASE_DIR / "models" / "early_warning_model.pkl"
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


class CLADEInference:

    def __init__(
        self,
        main_model_path=MAIN_MODEL_PATH,
        early_warning_model_path=EARLY_WARNING_MODEL_PATH,
    ):
        self.model = joblib.load(
            main_model_path
        )

        self.early_warning_model = joblib.load(
            early_warning_model_path
        )

    # =========================================================
    # MAIN MODEL FEATURES
    # =========================================================

    def create_main_features(self, window):

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

        features["accel_mag_first_last_change"] = (
            accel_mag.iloc[-1]
            - accel_mag.iloc[0]
        )

        features["gyro_mag_first_last_change"] = (
            gyro_mag.iloc[-1]
            - gyro_mag.iloc[0]
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

        # Used by the main model.
        #
        # NOTE:
        # The audit showed that the main model can also
        # perform without this feature. The early-warning
        # model does NOT use this feature.
        features["fall_detected"] = (
            window["fall_detected"]
            .astype(bool)
            .any()
        )

        return pd.DataFrame([features])

    # =========================================================
    # EARLY-WARNING MODEL FEATURES
    # =========================================================

    def create_early_warning_features(
        self,
        window,
    ):

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

        features["accel_mag_first_last_change"] = (
            accel_mag.iloc[-1]
            - accel_mag.iloc[0]
        )

        features["gyro_mag_first_last_change"] = (
            gyro_mag.iloc[-1]
            - gyro_mag.iloc[0]
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

        # IMPORTANT:
        #
        # fall_detected is intentionally NOT included.
        #
        # It is a simulator-generated label and would
        # leak information about the fall into the model.
        #
        # The early-warning model therefore relies only
        # on the sensor-derived features above.

        return pd.DataFrame([features])

    # =========================================================
    # COMPLETE CLADE INFERENCE
    # =========================================================

    def predict(self, sensor_data):

        if not isinstance(
            sensor_data,
            pd.DataFrame,
        ):

            raise TypeError(
                "sensor_data must be a pandas DataFrame."
            )

        if len(sensor_data) < 50:

            raise ValueError(
                "At least 50 sensor samples are required."
            )

        missing_columns = [
            column
            for column in SENSOR_COLUMNS
            if column not in sensor_data.columns
        ]

        if missing_columns:

            raise ValueError(
                "Missing sensor columns: "
                + ", ".join(missing_columns)
            )

        # -----------------------------------------------------
        # Use the most recent 50 samples.
        # -----------------------------------------------------

        window = (
            sensor_data
            .tail(50)
            .copy()
            .reset_index(drop=True)
        )

        # =====================================================
        # 1. MAIN EVENT MODEL
        # =====================================================

        main_features = self.create_main_features(
            window
        )

        main_features = main_features.reindex(
            columns=self.model.feature_names_in_
        )

        main_probabilities = (
            self.model.predict_proba(
                main_features
            )[0]
        )

        main_probability_dict = dict(
            zip(
                self.model.classes_,
                main_probabilities,
            )
        )

        risk = calculate_risk(
            main_probability_dict
        )

        # =====================================================
        # 2. EARLY-WARNING MODEL
        # =====================================================

        early_features = (
            self.create_early_warning_features(
                window
            )
        )

        early_features = early_features.reindex(
            columns=(
                self.early_warning_model
                .feature_names_in_
            )
        )

        early_probabilities = (
            self.early_warning_model
            .predict_proba(
                early_features
            )[0]
        )

        early_probability_dict = dict(
            zip(
                self.early_warning_model.classes_,
                early_probabilities,
            )
        )

        early_warning = calculate_early_warning(
            early_probability_dict
        )

        # =====================================================
        # 3. UNIFIED DECISION
        # =====================================================

        unified_decision = make_unified_decision(
            risk,
            early_warning,
        )

        # =====================================================
        # 4. RETURN DASHBOARD-READY RESULT
        # =====================================================

        return {
            "risk": risk,
            "early_warning": early_warning,
            "unified_decision": unified_decision,
        }


# =============================================================
# DEMO / TEST
# =============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("CAREEDGE — COMBINED CLADE INFERENCE")
    print("=" * 70)

    # ---------------------------------------------------------
    # Dataset path
    # ---------------------------------------------------------

    data_path = (
        BASE_DIR.parents[1]
        / "data"
        / "careedge_training_data.csv"
    )

    print()
    print("Loading sensor data...")

    df = pd.read_csv(data_path)

    # ---------------------------------------------------------
    # Use the first 50 samples of P001's simulated fall
    # ---------------------------------------------------------

    fall_window = (
        df[
            (df["patient_id"] == "P001")
            & (df["event"] == "fall")
        ]
        .sort_values("timestamp")
        .head(50)
        .copy()
    )

    print(
        "Samples used:",
        len(fall_window),
    )

    # ---------------------------------------------------------
    # Create inference engine
    # ---------------------------------------------------------

    engine = CLADEInference()

    result = engine.predict(
        fall_window
    )

    # =========================================================
    # MAIN RISK RESULT
    # =========================================================

    print()
    print("=" * 70)
    print("MAIN RISK RESULT")
    print("=" * 70)

    print(
        "Predicted event:",
        result["risk"]["predicted_event"],
    )

    print(
        "Confidence:",
        f'{result["risk"]["confidence"]:.2f}%',
    )

    print(
        "Risk score:",
        result["risk"]["risk_score"],
    )

    print(
        "Risk level:",
        result["risk"]["risk_level"],
    )

    print(
        "Reason:",
        result["risk"]["reason"],
    )

    # =========================================================
    # EARLY WARNING RESULT
    # =========================================================

    print()
    print("=" * 70)
    print("EARLY WARNING RESULT")
    print("=" * 70)

    print(
        "Warning state:",
        result["early_warning"]["warning_state"],
    )

    print(
        "Warning type:",
        result["early_warning"]["warning_type"],
    )

    print(
        "Predicted state:",
        result["early_warning"]["predicted_state"],
    )

    print(
        "Confidence:",
        f'{result["early_warning"]["confidence"]:.2f}%',
    )

    print(
        "Pre-fall probability:",
        f'{result["early_warning"]["pre_fall_probability"]:.2f}%',
    )

    print(
        "Fall transition probability:",
        f'{result["early_warning"]["fall_transition_probability"]:.2f}%',
    )

    print(
        "Fall probability:",
        f'{result["early_warning"]["fall_probability"]:.2f}%',
    )

    print(
        "Post-fall probability:",
        f'{result["early_warning"]["post_fall_probability"]:.2f}%',
    )

    print(
        "Message:",
        result["early_warning"]["message"],
    )

    # =========================================================
    # UNIFIED CLADE DECISION
    # =========================================================

    print()
    print("=" * 70)
    print("UNIFIED CLADE DECISION")
    print("=" * 70)

    print(
        "State:",
        result["unified_decision"]["state"],
    )

    print(
        "Alert type:",
        result["unified_decision"]["alert_type"],
    )

    print(
        "Priority:",
        result["unified_decision"]["priority"],
    )

    print(
        "Confidence:",
        f'{result["unified_decision"]["confidence"]:.2f}%',
    )

    print(
        "Message:",
        result["unified_decision"]["message"],
    )

    print(
        "Action:",
        result["unified_decision"]["action"],
    )

    # =========================================================
    # COMPLETE
    # =========================================================

    print()
    print("=" * 70)
    print("COMBINED INFERENCE COMPLETE")
    print("=" * 70)