import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLINICAL_DIR = PROJECT_ROOT / "clinical"
TESTS_DIR = PROJECT_ROOT / "tests"
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "clade" / "ml" / "models"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(CLINICAL_DIR))


def run_inspect():
    print("\n[1/6] Inspecting datasets...")
    from inspect_datasets import nb_path
    cmd = [sys.executable, str(CLINICAL_DIR / "inspect_datasets.py")]
    subprocess.run(cmd, check=True)


def run_extract(force=False):
    print("\n[2/6] Extracting archives safely...")
    cmd = [sys.executable, str(CLINICAL_DIR / "extract_data.py")]
    subprocess.run(cmd, check=True)


def run_preprocess(force=False):
    print("\n[3/6] Preprocessing datasets...")
    pro_dir = DATA_DIR / "processed"
    vitals_parquet = pro_dir / "vitals_train.parquet"
    ecg_parquet = pro_dir / "ecg_train.parquet"
    sisfall_parquet = pro_dir / "sisfall_train.parquet"

    if force or not vitals_parquet.exists():
        print(" -> Preprocessing Vital Signs...")
        subprocess.run([sys.executable, str(CLINICAL_DIR / "preprocess_vitals.py")], check=True)
    else:
        print(" -> Vital Signs already processed (skipping; use --force to recompute)")

    if force or not ecg_parquet.exists():
        print(" -> Preprocessing MIT-BIH ECG Heartbeats...")
        subprocess.run([sys.executable, str(CLINICAL_DIR / "preprocess_ecg.py")], check=True)
    else:
        print(" -> MIT-BIH ECG already processed (skipping)")

    if force or not sisfall_parquet.exists():
        print(" -> Preprocessing SisFall Movement...")
        subprocess.run([sys.executable, str(CLINICAL_DIR / "preprocess_sisfall.py")], check=True)
    else:
        print(" -> SisFall Movement already processed (skipping)")


def run_train(force=False):
    print("\n[4/6] Training clinical models...")
    htn_model = MODELS_DIR / "hypertension_risk_model.joblib"
    ecg_model = MODELS_DIR / "ecg_heartbeat_model.joblib"
    sisfall_model = MODELS_DIR / "sisfall_fall_model.joblib"

    if force or not htn_model.exists():
        print(" -> Training Hypertension & Vital Signs Risk Model...")
        subprocess.run([sys.executable, str(CLINICAL_DIR / "train_hypertension.py")], check=True)
    else:
        print(" -> Hypertension model artifact exists (skipping)")

    if force or not ecg_model.exists():
        print(" -> Training MIT-BIH ECG Heartbeat Model...")
        subprocess.run([sys.executable, str(CLINICAL_DIR / "train_ecg.py")], check=True)
    else:
        print(" -> ECG heartbeat model artifact exists (skipping)")

    if force or not sisfall_model.exists():
        print(" -> Training SisFall Fall Detection Model...")
        subprocess.run([sys.executable, str(CLINICAL_DIR / "train_sisfall.py")], check=True)
    else:
        print(" -> SisFall fall model artifact exists (skipping)")


def run_compare():
    print("\n[5/6] Generating synthetic vs real distribution comparison...")
    subprocess.run([sys.executable, str(CLINICAL_DIR / "compare_synthetic.py")], check=True)


def run_test():
    print("\n[6/6] Executing automated test suite with pytest...")
    test_file = TESTS_DIR / "test_clinical_pipeline.py"
    subprocess.run([sys.executable, "-m", "pytest", str(test_file), "-v"], check=True)


def run_serve():
    print("\nStarting CareEdge Clinical AI REST API on http://127.0.0.1:8000...")
    subprocess.run([sys.executable, "-m", "uvicorn", "api:app", "--app-dir", str(CLINICAL_DIR), "--host", "127.0.0.1", "--port", "8000", "--reload"])


def run_dashboard():
    print("\nStarting CareEdge Streamlit Dashboard on http://localhost:8501...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(DASHBOARD_DIR / "app.py"), "--server.port", "8501"])


def run_all(force=False):
    start = time.time()
    print("=" * 70)
    print("CAREEDGE CLINICAL AI PIPELINE — END-TO-END EXECUTION")
    print("=" * 70)
    run_extract(force=force)
    run_preprocess(force=force)
    run_train(force=force)
    run_compare()
    run_test()
    elapsed = time.time() - start
    print("\n" + "=" * 70)
    print(f"PIPELINE COMPLETED SUCCESSFULLY IN {elapsed:.2f}s")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="CareEdge Clinical Pipeline Orchestrator")
    parser.add_argument(
        "command",
        choices=["all", "inspect", "extract", "preprocess", "train", "compare", "test", "serve", "dashboard"],
        default="all",
        nargs="?",
        help="Command to run (default: all)",
    )
    parser.add_argument("--force", action="store_true", help="Force recomputation of processed data and models")

    args = parser.parse_args()

    if args.command == "all":
        run_all(force=args.force)
    elif args.command == "inspect":
        run_inspect()
    elif args.command == "extract":
        run_extract(force=args.force)
    elif args.command == "preprocess":
        run_preprocess(force=args.force)
    elif args.command == "train":
        run_train(force=args.force)
    elif args.command == "compare":
        run_compare()
    elif args.command == "test":
        run_test()
    elif args.command == "serve":
        run_serve()
    elif args.command == "dashboard":
        run_dashboard()


if __name__ == "__main__":
    main()
