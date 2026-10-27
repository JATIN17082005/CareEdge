import json
import re
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SISFALL_DIR = PROJECT_ROOT / "data" / "raw" / "sisfall" / "SisFall_dataset"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifests"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

# Conversion factors from SisFall documentation:
# ADXL345: 13-bit, +-16g -> Accel [g] = (32 / 8192) * AD. In m/s^2: * 9.80665
# ITG3200: 16-bit, +-2000 deg/s -> Gyro [deg/s] = (4000 / 65536) * RD. In rad/s: * (pi / 180)
# MMA8451Q: 14-bit, +-8g -> Accel [g] = (16 / 16384) * AD. In m/s^2: * 9.80665
ADXL_SCALE = (32.0 / 8192.0) * 9.80665
ITG_SCALE = (4000.0 / 65536.0) * (np.pi / 180.0)
MMA_SCALE = (16.0 / 16384.0) * 9.80665

# Subject splits: group by subject to guarantee ZERO patient leakage
TEST_SUBJECTS = ["SA04", "SA08", "SA15", "SA21", "SE03", "SE09", "SE14"]
VAL_SUBJECTS = ["SA02", "SA11", "SA18", "SE02", "SE07"]


def parse_sisfall_file(file_path: Path):
    """
    Parse a single SisFall trial file into a feature vector.
    Each file has 9 columns:
      0, 1, 2: ADXL345 accel (x, y, z)
      3, 4, 5: ITG3200 gyro (x, y, z)
      6, 7, 8: MMA8451Q accel (x, y, z)
    """
    rows = []
    with open(file_path, "r", encoding="latin1") as f:
        for line in f:
            line = line.strip().rstrip(";")
            if not line:
                continue
            parts = line.split(",")
            if len(parts) >= 9:
                try:
                    rows.append([float(p) for p in parts[:9]])
                except ValueError:
                    continue

    if len(rows) < 10:
        return None

    arr = np.array(rows, dtype=np.float32)

    # Convert to physical units
    ax = arr[:, 0] * ADXL_SCALE
    ay = arr[:, 1] * ADXL_SCALE
    az = arr[:, 2] * ADXL_SCALE

    gx = arr[:, 3] * ITG_SCALE
    gy = arr[:, 4] * ITG_SCALE
    gz = arr[:, 5] * ITG_SCALE

    # Compute signal magnitudes
    accel_mag = np.sqrt(ax**2 + ay**2 + az**2)
    gyro_mag = np.sqrt(gx**2 + gy**2 + gz**2)
    dynamic_accel = np.abs(accel_mag - 9.81)

    # Sample-to-sample jerk
    accel_diff = np.abs(np.diff(accel_mag))
    gyro_diff = np.abs(np.diff(gyro_mag))

    # Feature dictionary
    features = {
        "accel_mag_mean": float(np.mean(accel_mag)),
        "accel_mag_std": float(np.std(accel_mag)),
        "accel_mag_min": float(np.min(accel_mag)),
        "accel_mag_max": float(np.max(accel_mag)),
        "gyro_mag_mean": float(np.mean(gyro_mag)),
        "gyro_mag_std": float(np.std(gyro_mag)),
        "gyro_mag_min": float(np.min(gyro_mag)),
        "gyro_mag_max": float(np.max(gyro_mag)),
        "dynamic_accel_mean": float(np.mean(dynamic_accel)),
        "dynamic_accel_max": float(np.max(dynamic_accel)),
        "accel_jerk_max": float(np.max(accel_diff)) if len(accel_diff) > 0 else 0.0,
        "gyro_jerk_max": float(np.max(gyro_diff)) if len(gyro_diff) > 0 else 0.0,
        "accel_x_mean": float(np.mean(ax)),
        "accel_x_std": float(np.std(ax)),
        "accel_y_mean": float(np.mean(ay)),
        "accel_y_std": float(np.std(ay)),
        "accel_z_mean": float(np.mean(az)),
        "accel_z_std": float(np.std(az)),
        "gyro_x_mean": float(np.mean(gx)),
        "gyro_x_std": float(np.std(gx)),
        "gyro_y_mean": float(np.mean(gy)),
        "gyro_y_std": float(np.std(gy)),
        "gyro_z_mean": float(np.mean(gz)),
        "gyro_z_std": float(np.std(gz)),
    }
    return features


def preprocess_sisfall():
    print("=" * 70)
    print("PREPROCESSING SISFALL FALL & ADL DATASET")
    print("=" * 70)

    if not SISFALL_DIR.exists():
        raise FileNotFoundError(f"SisFall dataset not found at: {SISFALL_DIR}")

    records = []
    subject_dirs = [d for d in SISFALL_DIR.iterdir() if d.is_dir() and (d.name.startswith("SA") or d.name.startswith("SE"))]
    print(f"Found {len(subject_dirs)} subject directories.")

    for subj_dir in subject_dirs:
        subject_id = subj_dir.name
        is_elderly = subject_id.startswith("SE")

        # Partition assignment by subject
        if subject_id in TEST_SUBJECTS:
            split_type = "test"
        elif subject_id in VAL_SUBJECTS:
            split_type = "val"
        else:
            split_type = "train"

        trial_files = list(subj_dir.glob("*.txt"))
        for tfile in trial_files:
            fname = tfile.stem  # e.g. D01_SA01_R01 or F01_SA01_R01
            parts = fname.split("_")
            code = parts[0]
            is_fall = 1 if code.startswith("F") else 0

            feat = parse_sisfall_file(tfile)
            if feat is None:
                continue

            feat["subject_id"] = subject_id
            feat["activity_code"] = code
            feat["is_elderly"] = int(is_elderly)
            feat["split"] = split_type
            feat["target"] = is_fall
            records.append(feat)

    df = pd.DataFrame(records)
    print(f"\nProcessed {len(df):,} valid movement trials across 38 subjects.")
    print("Class distribution:")
    print(df["target"].value_counts().rename({0: "ADL (Non-Fall)", 1: "Fall"}))

    train_df = df[df["split"] == "train"].drop(columns=["split", "subject_id", "activity_code"])
    val_df = df[df["split"] == "val"].drop(columns=["split", "subject_id", "activity_code"])
    test_df = df[df["split"] == "test"].drop(columns=["split", "subject_id", "activity_code"])

    print(f"\nSubject-stratified partition sizes:")
    print(f"  Train: {len(train_df):,} trials (Falls: {train_df['target'].sum():,})")
    print(f"  Val:   {len(val_df):,} trials (Falls: {val_df['target'].sum():,})")
    print(f"  Test:  {len(test_df):,} trials (Falls: {test_df['target'].sum():,})")

    feature_cols = [c for c in train_df.columns if c != "target"]
    scaler = StandardScaler()
    scaler.fit(train_df[feature_cols])

    preprocessor = {
        "feature_names": feature_cols,
        "scaler": scaler,
        "class_mapping": {0: "Non-Fall Activity (ADL)", 1: "Fall"},
        "test_subjects": TEST_SUBJECTS,
        "val_subjects": VAL_SUBJECTS,
    }
    joblib.dump(preprocessor, PROCESSED_DIR / "sisfall_preprocessor.joblib")

    train_df.to_parquet(PROCESSED_DIR / "sisfall_train.parquet", index=False)
    val_df.to_parquet(PROCESSED_DIR / "sisfall_val.parquet", index=False)
    test_df.to_parquet(PROCESSED_DIR / "sisfall_test.parquet", index=False)

    metadata = {
        "dataset_name": "SisFall: Fall and Movement Dataset",
        "total_trials": len(df),
        "train_samples": len(train_df),
        "val_samples": len(val_df),
        "test_samples": len(test_df),
        "fall_count": int(df["target"].sum()),
        "adl_count": int(len(df) - df["target"].sum()),
        "feature_names": feature_cols,
        "test_subjects": TEST_SUBJECTS,
        "val_subjects": VAL_SUBJECTS,
    }
    with open(MANIFEST_DIR / "sisfall_dataset_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print(" SisFall preprocessing complete. Artifacts saved to data/processed/")
    return metadata


if __name__ == "__main__":
    preprocess_sisfall()
