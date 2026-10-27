import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
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
    brier_score_loss,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "clade" / "ml" / "models"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifests"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
MANIFEST_DIR.mkdir(parents=True, exist_ok=True)


def train_hypertension_models():
    print("=" * 70)
    print("TRAINING HYPERTENSION & VITAL SIGNS RISK MODELS")
    print("=" * 70)

    train_path = PROCESSED_DIR / "vitals_train.parquet"
    val_path = PROCESSED_DIR / "vitals_val.parquet"
    test_path = PROCESSED_DIR / "vitals_test.parquet"

    if not train_path.exists():
        raise FileNotFoundError(f"Processed train data missing: {train_path}. Run preprocess_vitals.py first.")

    train_df = pd.read_parquet(train_path)
    val_df = pd.read_parquet(val_path)
    test_df = pd.read_parquet(test_path)

    X_train = train_df.drop(columns=["target"])
    y_train = train_df["target"]
    X_val = val_df.drop(columns=["target"])
    y_val = val_df["target"]
    X_test = test_df.drop(columns=["target"])
    y_test = test_df["target"]

    feature_names = list(X_train.columns)
    print(f"Features ({len(feature_names)}): {feature_names}")
    print(f"Train samples: {len(X_train):,}, Val: {len(X_val):,}, Test: {len(X_test):,}")

    models = {
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
        "RandomForest": RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1),
        "XGBoost": XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42, eval_metric="logloss", n_jobs=-1),
    }

    val_results = {}
    fitted_models = {}

    print("\n" + "-" * 70)
    print("MODEL VALIDATION COMPARISON")
    print("-" * 70)

    for name, model in models.items():
        print(f"\nTraining {name}...")
        model.fit(X_train, y_train)
        fitted_models[name] = model

        val_preds = model.predict(X_val)
        val_probs = model.predict_proba(X_val)[:, 1] if hasattr(model, "predict_proba") else val_preds

        acc = accuracy_score(y_val, val_preds)
        prec = precision_score(y_val, val_preds, zero_division=0)
        rec = recall_score(y_val, val_preds, zero_division=0)
        f1 = f1_score(y_val, val_preds, zero_division=0)
        auc = roc_auc_score(y_val, val_probs)

        val_results[name] = {
            "accuracy": float(acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1_score": float(f1),
            "roc_auc": float(auc),
        }
        print(f" {name} Val Accuracy: {acc:.4f} | Precision: {prec:.4f} | Recall: {rec:.4f} | F1: {f1:.4f} | ROC-AUC: {auc:.4f}")

    # Model selection based on validation F1 score
    best_model_name = max(val_results, key=lambda k: val_results[k]["f1_score"])
    best_model = fitted_models[best_model_name]
    print(f"\n Selected Best Model: {best_model_name} (Validation F1: {val_results[best_model_name]['f1_score']:.4f})")

    # Evaluate Best Model on UNTOUCHED Test Set
    print("\n" + "=" * 70)
    print(f"FINAL HELD-OUT TEST EVALUATION — {best_model_name}")
    print("=" * 70)

    test_preds = best_model.predict(X_test)
    test_probs = best_model.predict_proba(X_test)[:, 1]

    test_acc = accuracy_score(y_test, test_preds)
    test_prec = precision_score(y_test, test_preds, zero_division=0)
    test_rec = recall_score(y_test, test_preds, zero_division=0)
    test_f1 = f1_score(y_test, test_preds, zero_division=0)
    test_auc = roc_auc_score(y_test, test_probs)
    brier = brier_score_loss(y_test, test_probs)
    cm = confusion_matrix(y_test, test_preds).tolist()
    report = classification_report(y_test, test_preds, target_names=["Low Risk", "High Risk"], output_dict=True)

    print(f"Test Accuracy:  {test_acc:.4f}")
    print(f"Test Precision: {test_prec:.4f}")
    print(f"Test Recall:    {test_rec:.4f}")
    print(f"Test F1-Score:  {test_f1:.4f}")
    print(f"Test ROC-AUC:   {test_auc:.4f}")
    print(f"Brier Score:    {brier:.4f}")
    print("\nConfusion Matrix:")
    print(f"  TN: {cm[0][0]:,} | FP: {cm[0][1]:,}")
    print(f"  FN: {cm[1][0]:,} | TP: {cm[1][1]:,}")

    # Feature Importance (if applicable)
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
        "class_mapping": {0: "Low Risk", 1: "High Risk"},
        "version": "1.0.0",
        "task": "synthetic_vital_signs_risk_classification",
        "task_description": "Synthetic/Rule-Based Vital Signs Risk Classification (Deterministic Heart Rate & BMI benchmark)",
        "clinical_guidelines": {
            "hypertension_stage_1": "SBP 130-139 or DBP 80-89",
            "hypertension_stage_2": "SBP >= 140 or DBP >= 90",
            "hypertensive_crisis": "SBP > 180 or DBP > 120",
        },
    }
    model_save_path = MODEL_DIR / "hypertension_risk_model.joblib"
    joblib.dump(artifact_payload, model_save_path)
    print(f"\n Saved model artifact to: {model_save_path}")

    # Save comprehensive evaluation report
    eval_report = {
        "best_model": best_model_name,
        "validation_comparison": val_results,
        "test_metrics": {
            "accuracy": float(test_acc),
            "precision": float(test_prec),
            "recall": float(test_rec),
            "f1_score": float(test_f1),
            "roc_auc": float(test_auc),
            "brier_score": float(brier),
            "confusion_matrix": cm,
            "classification_report": report,
        },
        "feature_importances": importance_dict,
        "clinical_note": (
            "Target Risk Category in this dataset is deterministically derived from Heart Rate and BMI. "
            "Blood pressure readings do not define Risk Category in this data. Model outputs reflect "
            "statistical risk classification, not clinical diagnosis of chronic hypertension."
        ),
    }
    with open(MANIFEST_DIR / "hypertension_evaluation_report.json", "w") as f:
        json.dump(eval_report, f, indent=2)

    print(" Evaluation report saved to data/manifests/hypertension_evaluation_report.json")
    return eval_report


if __name__ == "__main__":
    train_hypertension_models()
