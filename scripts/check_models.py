import joblib
from pathlib import Path

models_dir = Path("CareEdge-1/clade/ml/models")
models = [
    "sisfall_fall_model.joblib",
    "ecg_heartbeat_model.joblib",
    "hypertension_risk_model.joblib"
]

print("=" * 70)
print("VERIFYING MODEL ARTIFACT LOADING & SCHEMAS")
print("=" * 70)

for m in models:
    p = models_dir / m
    if not p.exists():
        print(f"[MISSING] {m}")
        continue
    artifact = joblib.load(p)
    name = artifact.get("model_name", "unknown")
    ver = artifact.get("version", "1.0.0")
    task = artifact.get("task", "unknown")
    features = artifact.get("feature_names", [])
    classes = artifact.get("class_mapping", artifact.get("supported_classes", []))
    print(f"[LOADED] {m}")
    print(f"  Name: {name} (Version: {ver})")
    print(f"  Task: {task}")
    print(f"  Feature Count: {len(features)}")
    print(f"  Sample Features: {features[:5]}")
    print(f"  Classes: {classes}")
    print()
