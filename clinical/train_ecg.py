import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
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

CLASS_NAMES = [
    "Normal Beat (N)",
    "Supraventricular Ectopic (S)",
    "Ventricular Ectopic (V)",
    "Fusion Beat (F)",
    "Unknown / Paced (Q)",
]

CLASS_SHORT_NAMES = ["Normal", "Supraventricular", "Ventricular", "Fusion", "Unknown"]


def train_ecg_models():
    print("=" * 70)
    print("TRAINING MIT-BIH ECG HEARTBEAT CLASSIFICATION MODELS")
    print("=" * 70)

    train_path = PROCESSED_DIR / "ecg_train.parquet"
    val_path = PROCESSED_DIR / "ecg_val.parquet"
    test_path = PROCESSED_DIR / "ecg_test.parquet"

    if not train_path.exists():
        raise FileNotFoundError(f"Processed train data missing: {train_path}. Run preprocess_ecg.py first.")

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
    print(f"Features ({len(feature_names)}): {feature_names[:6]}... (total {len(feature_names)})")
    print(f"Train samples: {len(X_train):,}, Val: {len(X_val):,}, Test: {len(X_test):,}")

    models = {
        "RandomForest": RandomForestClassifier(
            n_estimators=100, max_depth=15, class_weight="balanced", random_state=42, n_jobs=-1
        ),
        "XGBoost": XGBClassifier(
            n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, eval_metric="mlogloss", n_jobs=-1
        ),
    }

    val_results = {}
    fitted_models = {}

    print("\n" + "-" * 70)
    print("MODEL VALIDATION COMPARISON (MACRO METRICS FOR CLASS IMBALANCE)")
    print("-" * 70)

    for name, model in models.items():
        print(f"\nTraining {name} on {len(X_train):,} heartbeat segments...")
        model.fit(X_train, y_train)
        fitted_models[name] = model

        val_preds = model.predict(X_val)
        val_probs = model.predict_proba(X_val)

        acc = accuracy_score(y_val, val_preds)
        macro_prec = precision_score(y_val, val_preds, average="macro", zero_division=0)
        macro_rec = recall_score(y_val, val_preds, average="macro", zero_division=0)
        macro_f1 = f1_score(y_val, val_preds, average="macro", zero_division=0)
        weighted_f1 = f1_score(y_val, val_preds, average="weighted", zero_division=0)
        try:
            auc = roc_auc_score(y_val, val_probs, multi_class="ovr", average="macro")
        except Exception:
            auc = 0.0

        val_results[name] = {
            "accuracy": float(acc),
            "macro_precision": float(macro_prec),
            "macro_recall": float(macro_rec),
            "macro_f1": float(macro_f1),
            "weighted_f1": float(weighted_f1),
            "macro_roc_auc": float(auc),
        }
        print(f" {name} Val Accuracy: {acc:.4f} | Macro F1: {macro_f1:.4f} | Weighted F1: {weighted_f1:.4f} | Macro AUC: {auc:.4f}")

    # Select best model based on macro F1 (handles extreme class imbalance)
    best_model_name = max(val_results, key=lambda k: val_results[k]["macro_f1"])
    best_model = fitted_models[best_model_name]
    print(f"\n Selected Best Model: {best_model_name} (Validation Macro F1: {val_results[best_model_name]['macro_f1']:.4f})")

    # Evaluate Best Model on UNTOUCHED Test Set
    print("\n" + "=" * 70)
    print(f"FINAL HELD-OUT TEST EVALUATION — {best_model_name}")
    print("=" * 70)

    test_preds = best_model.predict(X_test)
    test_probs = best_model.predict_proba(X_test)

    test_acc = accuracy_score(y_test, test_preds)
    test_macro_prec = precision_score(y_test, test_preds, average="macro", zero_division=0)
    test_macro_rec = recall_score(y_test, test_preds, average="macro", zero_division=0)
    test_macro_f1 = f1_score(y_test, test_preds, average="macro", zero_division=0)
    test_weighted_f1 = f1_score(y_test, test_preds, average="weighted", zero_division=0)
    try:
        test_auc = roc_auc_score(y_test, test_probs, multi_class="ovr", average="macro")
    except Exception:
        test_auc = 0.0

    cm = confusion_matrix(y_test, test_preds).tolist()
    report = classification_report(
        y_test, test_preds, target_names=CLASS_SHORT_NAMES, output_dict=True, zero_division=0
    )

    print(f"Test Accuracy:    {test_acc:.4f}")
    print(f"Macro Precision:  {test_macro_prec:.4f}")
    print(f"Macro Recall:     {test_macro_rec:.4f}")
    print(f"Macro F1-Score:   {test_macro_f1:.4f}")
    print(f"Weighted F1:      {test_weighted_f1:.4f}")
    print(f"Macro ROC-AUC:    {test_auc:.4f}")

    print("\nClass-wise Performance:")
    for cls_name in CLASS_SHORT_NAMES:
        c_stats = report[cls_name]
        print(f"  {cls_name:16s} | Prec: {c_stats['precision']:.4f} | Rec: {c_stats['recall']:.4f} | F1: {c_stats['f1-score']:.4f} | Support: {c_stats['support']}")

    print("\nConfusion Matrix (Rows: True, Cols: Pred):")
    print(f"  Classes: {CLASS_SHORT_NAMES}")
    for i, row in enumerate(cm):
        print(f"  {CLASS_SHORT_NAMES[i]:16s}: {row}")

    # Top Feature Importances
    importance_dict = {}
    if hasattr(best_model, "feature_importances_"):
        importances = best_model.feature_importances_
        sorted_idx = np.argsort(importances)[::-1]
        print("\nTop 5 Feature Importances:")
        for idx in sorted_idx[:5]:
            importance_dict[feature_names[idx]] = float(importances[idx])
            print(f"  {feature_names[idx]}: {importances[idx]:.4f}")

    # Save fitted model package
    artifact_payload = {
        "model_name": best_model_name,
        "model": best_model,
        "feature_names": feature_names,
        "class_mapping": {i: name for i, name in enumerate(CLASS_NAMES)},
        "class_short_names": {i: name for i, name in enumerate(CLASS_SHORT_NAMES)},
        "version": "1.0.0",
        "task": "ecg_heartbeat_classification",
        "supported_classes": CLASS_NAMES,
    }
    model_save_path = MODEL_DIR / "ecg_heartbeat_model.joblib"
    joblib.dump(artifact_payload, model_save_path)
    print(f"\n Saved model artifact to: {model_save_path}")

    eval_report = {
        "best_model": best_model_name,
        "validation_comparison": val_results,
        "test_metrics": {
            "accuracy": float(test_acc),
            "macro_precision": float(test_macro_prec),
            "macro_recall": float(test_macro_rec),
            "macro_f1": float(test_macro_f1),
            "weighted_f1": float(test_weighted_f1),
            "macro_roc_auc": float(test_auc),
            "confusion_matrix": cm,
            "classification_report": report,
        },
        "feature_importances": importance_dict,
        "supported_classes": CLASS_NAMES,
        "clinical_note": (
            "Supported AAMI EC57 classes: Normal, Supraventricular, Ventricular, Fusion, Unknown. "
            "These represent morphological beat categories, NOT rhythm diagnoses like tachycardia or bradycardia."
        ),
    }
    with open(MANIFEST_DIR / "ecg_evaluation_report.json", "w") as f:
        json.dump(eval_report, f, indent=2)

    print(" Evaluation report saved to data/manifests/ecg_evaluation_report.json")
    return eval_report


if __name__ == "__main__":
    train_ecg_models()
