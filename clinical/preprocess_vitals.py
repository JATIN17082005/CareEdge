import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "vitals" / "human_vital_signs_dataset_2024.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifests"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

# Feature schema and clinical bounds
FEATURE_COLUMNS = [
    "Heart Rate",
    "Respiratory Rate",
    "Body Temperature",
    "Oxygen Saturation",
    "Systolic Blood Pressure",
    "Diastolic Blood Pressure",
    "Age",
    "Gender",
    "Weight (kg)",
    "Height (m)",
    "Derived_HRV",
    "Derived_Pulse_Pressure",
    "Derived_BMI",
    "Derived_MAP",
]

NUMERIC_COLUMNS = [
    "Heart Rate",
    "Respiratory Rate",
    "Body Temperature",
    "Oxygen Saturation",
    "Systolic Blood Pressure",
    "Diastolic Blood Pressure",
    "Age",
    "Weight (kg)",
    "Height (m)",
    "Derived_HRV",
    "Derived_Pulse_Pressure",
    "Derived_BMI",
    "Derived_MAP",
]

CLINICAL_RANGES = {
    "Heart Rate": (30.0, 250.0),
    "Respiratory Rate": (6.0, 60.0),
    "Body Temperature": (30.0, 45.0),
    "Oxygen Saturation": (70.0, 100.0),
    "Systolic Blood Pressure": (60.0, 260.0),
    "Diastolic Blood Pressure": (30.0, 160.0),
    "Age": (1.0, 120.0),
    "Weight (kg)": (20.0, 300.0),
    "Height (m)": (0.5, 2.5),
    "Derived_HRV": (0.001, 1.0),
    "Derived_Pulse_Pressure": (5.0, 150.0),
    "Derived_BMI": (10.0, 70.0),
    "Derived_MAP": (40.0, 200.0),
}


def preprocess_vitals():
    print("=" * 70)
    print("PREPROCESSING VITAL SIGNS & HYPERTENSION RISK DATASET")
    print("=" * 70)

    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(f"Raw vitals file not found at: {RAW_DATA_PATH}")

    print(f"Loading raw dataset from {RAW_DATA_PATH}...")
    df = pd.read_csv(RAW_DATA_PATH)
    print(f"Loaded {len(df):,} records with {len(df.columns)} columns.")

    # Drop identifiers and unneeded columns
    drop_cols = ["Patient ID", "Timestamp"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])

    # Validate feature presence
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Missing expected column: {col}")

    # Binary target encoding: High Risk -> 1, Low Risk -> 0
    if "Risk Category" not in df.columns:
        raise ValueError("Target column 'Risk Category' not found.")

    y = (df["Risk Category"] == "High Risk").astype(int)
    X = df[FEATURE_COLUMNS].copy()

    # Encode Gender: Male -> 1, Female -> 0
    X["Gender"] = (X["Gender"].astype(str).str.strip().str.capitalize() == "Male").astype(int)

    # Check for NaN / invalid values
    nan_count = X.isnull().sum().sum()
    if nan_count > 0:
        print(f"Imputing {nan_count} missing values using feature medians...")
        X = X.fillna(X.median())

    # Range validation
    for col, (low, high) in CLINICAL_RANGES.items():
        out_of_bounds = ((X[col] < low) | (X[col] > high)).sum()
        if out_of_bounds > 0:
            print(f"Clipping {out_of_bounds} out-of-range values in {col} to [{low}, {high}].")
            X[col] = X[col].clip(low, high)

    # Stratified Splits: 70% Train, 15% Validation, 15% Test
    print("Performing stratified 70/15/15 train/val/test split...")
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
    )

    print(f"Train set: {len(X_train):,} samples (High Risk: {y_train.sum():,})")
    print(f"Val set:   {len(X_val):,} samples (High Risk: {y_val.sum():,})")
    print(f"Test set:  {len(X_test):,} samples (High Risk: {y_test.sum():,})")

    # Fit scaler ONLY on training data
    scaler = StandardScaler()
    scaler.fit(X_train[NUMERIC_COLUMNS])

    # Save preprocessing artifact
    preprocessor = {
        "feature_columns": FEATURE_COLUMNS,
        "numeric_columns": NUMERIC_COLUMNS,
        "scaler": scaler,
        "clinical_ranges": CLINICAL_RANGES,
        "class_mapping": {0: "Low Risk", 1: "High Risk"},
    }
    joblib.dump(preprocessor, PROCESSED_DIR / "vitals_preprocessor.joblib")

    # Save processed datasets
    train_df = X_train.copy()
    train_df["target"] = y_train
    val_df = X_val.copy()
    val_df["target"] = y_val
    test_df = X_test.copy()
    test_df["target"] = y_test

    train_df.to_parquet(PROCESSED_DIR / "vitals_train.parquet", index=False)
    val_df.to_parquet(PROCESSED_DIR / "vitals_val.parquet", index=False)
    test_df.to_parquet(PROCESSED_DIR / "vitals_test.parquet", index=False)

    metadata = {
        "dataset_name": "human_vital_signs_dataset_2024",
        "total_samples": len(df),
        "train_samples": len(train_df),
        "val_samples": len(val_df),
        "test_samples": len(test_df),
        "target_distribution": {
            "High Risk": int(y.sum()),
            "Low Risk": int(len(y) - y.sum()),
        },
        "feature_columns": FEATURE_COLUMNS,
        "numeric_columns": NUMERIC_COLUMNS,
        "rule_dependency": "Risk Category = 1 if (Heart Rate > 90) or (BMI > 30) or (BMI < 18.5) else 0",
    }
    with open(MANIFEST_DIR / "vitals_dataset_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(" Preprocessing complete. Artifacts saved to data/processed/")
    return metadata


if __name__ == "__main__":
    preprocess_vitals()
