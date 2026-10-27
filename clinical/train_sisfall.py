import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "clade" / "ml" / "models"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifests"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)


def train_sisfall_model():
    print("=" * 70)
    print("TRAINING SISFALL FALL DETECTION MODEL")
    print("=" * 70)

    train_path = PROCESSED_DIR / "sisfall_train.parquet"
    val_path = PROCESSED_DIR / "sisfall_val.parquet"
    test_path = PROCESSED_DIR / "sisfall_test.parquet"

    if not train_path.exists():
        raise FileNotFoundError(f"Missing {train_path}. Run preprocess_sisfall.py first.")

    train_df = pd.read_parquet(train_path)
    val_df = pd.read_parquet(val_path)
    test_df = pd.read_parquet(test_path)

    X_train = train_df.drop(columns=["target"])
    y_train = train_df["target"].astype(int)
    X_val = val_df.drop(columns=["target"])
    y_val = val_df["target"].astype(int)
    X_test = test_df.drop(columns=["target"])
    y_test = test_df["target"].astype(int)

    feature_names = list(X_train.columns)
    print(f"Features ({len(feature_names)}): {feature_names[:5]}...")
    print(f"Subject-separated partition sizes:")
    print(f"  Train: {len(X_train):,} trials (Falls: {y_train.sum():,})")
    print(f"  Val:   {len(X_val):,} trials (Falls: {y_val.sum():,})")
    print(f"  Test:  {len(X_test):,} trials (Falls: {y_test.sum():,})")

    # Train Random Forest
    rf = RandomForestClassifier(
        n_estimators=150,
        max_depth=12,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    print("\nFitting Random Forest with class_weight='balanced'...")
    rf.fit(X_train, y_train)

    # Validation evaluation
    val_preds = rf.predict(X_val)
    val_acc = accuracy_score(y_val, val_preds)
    val_f1 = f1_score(y_val, val_preds)
    print(f"Validation Accuracy: {val_acc:.4f} | Validation F1: {val_f1:.4f}")

    # Final evaluation on UNTOUCHED Test Subjects
    print("\n" + "=" * 70)
    print("FINAL HELD-OUT SUBJECT-LEVEL TEST EVALUATION")
    print("=" * 70)

    test_preds = rf.predict(X_test)
    test_probs = rf.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, test_preds)
    prec = precision_score(y_test, test_preds, zero_division=0)
    rec = recall_score(y_test, test_preds, zero_division=0)
    f1 = f1_score(y_test, test_preds, zero_division=0)
    auc = roc_auc_score(y_test, test_probs)

    cm = confusion_matrix(y_test, test_preds).tolist()
    tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]

    # False Positive Rate: FPR = FP / (FP + TN)
    fpr = float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0
    specificity = float(tn / (fp + tn)) if (fp + tn) > 0 else 0.0

    report = classification_report(
        y_test, test_preds, target_names=["ADL (Non-Fall)", "Fall"], output_dict=True, zero_division=0
    )

    print(f"Test Accuracy:      {acc:.4f}")
    print(f"Precision (Fall):   {prec:.4f}")
    print(f"Recall / Sens:      {rec:.4f}")
    print(f"F1-Score:           {f1:.4f}")
    print(f"Specificity:        {specificity:.4f}")
    print(f"False-Positive Rate: {fpr:.4f} ({fpr * 100:.2f}%)")
    print(f"ROC-AUC:            {auc:.4f}")

    print("\nConfusion Matrix:")
    print(f"  True Non-Falls (TN): {tn:,} | False Falls (FP): {fp:,}")
    print(f"  Missed Falls   (FN): {fn:,} | Detected Falls (TP): {tp:,}")

    # Feature Importance
    importances = rf.feature_importances_
    sorted_idx = np.argsort(importances)[::-1]
    print("\nTop 5 Movement Features for Fall Discrimination:")
    importance_dict = {}
    for idx in sorted_idx[:5]:
        importance_dict[feature_names[idx]] = float(importances[idx])
        print(f"  {feature_names[idx]}: {importances[idx]:.4f}")

    # Save model artifact
    artifact_payload = {
        "model_name": "SisFall_RandomForest",
        "model": rf,
        "feature_names": feature_names,
        "class_mapping": {0: "ADL (Non-Fall)", 1: "Fall"},
        "version": "1.0.0",
        "task": "fall_detection",
        "dataset": "SisFall",
        "input_signals": "ADXL345 3-axis accel (m/s^2), ITG3200 3-axis gyro (rad/s)",
    }
    model_save_path = MODEL_DIR / "sisfall_fall_model.joblib"
    joblib.dump(artifact_payload, model_save_path)
    print(f"\n Saved SisFall fall model artifact to: {model_save_path}")

    eval_report = {
        "model_name": "SisFall_RandomForest",
        "subject_level_split": True,
        "test_metrics": {
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1_score": float(f1),
            "specificity": float(specificity),
            "false_positive_rate": float(fpr),
            "roc_auc": float(auc),
            "confusion_matrix": cm,
            "classification_report": report,
        },
        "top_features": importance_dict,
    }
    with open(MANIFEST_DIR / "sisfall_evaluation_report.json", "w") as f:
        json.dump(eval_report, f, indent=2)

    print(" Evaluation report saved to data/manifests/sisfall_evaluation_report.json")
    return eval_report


if __name__ == "__main__":
    train_sisfall_model()
