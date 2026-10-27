import sys
import os
from pathlib import Path
import json
import requests
import pandas as pd
import numpy as np

# Ensure UTF-8 output
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

API_BASE = "http://127.0.0.1:8000"
DASH_BASE = "http://localhost:8501"

print("=" * 75)
print("CAREEDGE FINAL VERIFICATION & AUDIT SUITE")
print("=" * 75)

all_passed = True
test_log = []

def record(category, test_name, passed, details):
    global all_passed
    if not passed:
        all_passed = False
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} {category} :: {test_name}")
    for d in details:
        print(f"       -> {d}")
    test_log.append({"category": category, "name": test_name, "passed": passed, "details": details})

# =============================================================================
# PART 1: SERVICE HEALTH & MODEL REGISTRY
# =============================================================================
print("\n--- 1. Testing Backend Availability & Model Status ---")

try:
    r_health = requests.get(f"{API_BASE}/health", timeout=3.0)
    health_ok = r_health.status_code == 200 and r_health.json().get("status") == "healthy"
    record("Backend Health", "GET /health", health_ok, [
        f"HTTP Status: {r_health.status_code}",
        f"Response: {r_health.json()}"
    ])
except Exception as e:
    record("Backend Health", "GET /health", False, [f"Connection error: {e}"])

try:
    r_models = requests.get(f"{API_BASE}/models/status", timeout=3.0)
    models_data = r_models.json().get("models", {})
    sisfall_m = models_data.get("sisfall_fall_model", {})
    htn_m = models_data.get("hypertension_risk_model", {})
    ecg_m = models_data.get("ecg_heartbeat_model", {})
    
    models_ok = (r_models.status_code == 200 and 
                 sisfall_m.get("loaded") and 
                 htn_m.get("loaded") and 
                 ecg_m.get("loaded"))
    record("Model Registry", "GET /models/status", models_ok, [
        f"HTTP Status: {r_models.status_code}",
        f"SisFall Fall Model: loaded={sisfall_m.get('loaded')} ({sisfall_m.get('model_type')} v{sisfall_m.get('version')})",
        f"Vitals Risk Model: loaded={htn_m.get('loaded')} ({htn_m.get('model_type')} v{htn_m.get('version')})",
        f"  Warning noted: {htn_m.get('clinical_warning')}",
        f"ECG Heartbeat Model: loaded={ecg_m.get('loaded')} ({ecg_m.get('model_type')} v{ecg_m.get('version')})",
        f"Legacy Replay Model: loaded={models_data.get('legacy_clade_simulation_model', {}).get('loaded')}"
    ])
except Exception as e:
    record("Model Registry", "GET /models/status", False, [f"Error: {e}"])

# =============================================================================
# PART 2: PREDICTION ENDPOINTS WITH VALID & INVALID INPUTS
# =============================================================================
print("\n--- 2. Testing Prediction Endpoints ---")

# 2.1 Vitals Risk Endpoint
# Valid low risk
v_low_req = {
    "heart_rate": 72.0, "respiratory_rate": 16.0, "body_temperature": 36.6,
    "oxygen_saturation": 98.0, "systolic_bp": 118.0, "diastolic_bp": 76.0,
    "age": 35.0, "gender": "Female", "weight_kg": 60.0, "height_m": 1.70
}
r_v_low = requests.post(f"{API_BASE}/predict/hypertension-risk", json=v_low_req)
v_low_data = r_v_low.json() if r_v_low.status_code == 200 else {}
v_low_ok = (r_v_low.status_code == 200 and 
            v_low_data.get("model_estimated_risk") == "Low Risk" and 
            v_low_data.get("clinical_blood_pressure_assessment", {}).get("stage") == "Normal Blood Pressure")
record("Vitals Risk", "POST /predict/hypertension-risk (Valid Low Risk)", v_low_ok, [
    f"HTTP Status: {r_v_low.status_code}",
    f"Risk: {v_low_data.get('model_estimated_risk')} (Prob: {v_low_data.get('high_risk_probability')})",
    f"Clinical BP Stage: {v_low_data.get('clinical_blood_pressure_assessment', {}).get('stage')}"
])

# Valid high risk & Stage 2 HTN
v_high_req = {
    "heart_rate": 96.0, "respiratory_rate": 20.0, "body_temperature": 37.0,
    "oxygen_saturation": 95.0, "systolic_bp": 145.0, "diastolic_bp": 92.0,
    "age": 60.0, "gender": "Male", "weight_kg": 95.0, "height_m": 1.68
}
r_v_high = requests.post(f"{API_BASE}/predict/hypertension-risk", json=v_high_req)
v_high_data = r_v_high.json() if r_v_high.status_code == 200 else {}
v_high_ok = (r_v_high.status_code == 200 and 
             v_high_data.get("model_estimated_risk") == "High Risk" and 
             v_high_data.get("clinical_blood_pressure_assessment", {}).get("stage") == "Stage 2 Hypertension")
record("Vitals Risk", "POST /predict/hypertension-risk (Valid High Risk / Stage 2)", v_high_ok, [
    f"HTTP Status: {r_v_high.status_code}",
    f"Risk: {v_high_data.get('model_estimated_risk')} (Prob: {v_high_data.get('high_risk_probability')})",
    f"Clinical BP Stage: {v_high_data.get('clinical_blood_pressure_assessment', {}).get('stage')}"
])

# Invalid out-of-range HR (15 bpm < 30)
r_v_inv_hr = requests.post(f"{API_BASE}/predict/hypertension-risk", json={"heart_rate": 15.0})
v_inv_hr_ok = r_v_inv_hr.status_code == 422
record("Vitals Risk", "POST /predict/hypertension-risk (Invalid HR < 30)", v_inv_hr_ok, [
    f"HTTP Status: {r_v_inv_hr.status_code} (Expected 422 Unprocessable Entity)",
    f"Validation Error: {r_v_inv_hr.json().get('detail', [{}])[0].get('msg')}"
])

# Invalid gender string
r_v_inv_gen = requests.post(f"{API_BASE}/predict/hypertension-risk", json={"heart_rate": 75.0, "gender": "Alien"})
v_inv_gen_ok = r_v_inv_gen.status_code == 422
record("Vitals Risk", "POST /predict/hypertension-risk (Invalid Gender)", v_inv_gen_ok, [
    f"HTTP Status: {r_v_inv_gen.status_code} (Expected 422)",
    f"Validation Error: {r_v_inv_gen.json().get('detail', [{}])[0].get('msg')}"
])

# 2.2 ECG Heartbeat Endpoint
# Valid 187 sample beat
ecg_sample = [0.0] * 187
ecg_sample[30] = 0.5
ecg_sample[35] = 1.0
ecg_sample[40] = -0.3
r_ecg_valid = requests.post(f"{API_BASE}/predict/ecg-heartbeat", json={"signal": ecg_sample})
ecg_data = r_ecg_valid.json() if r_ecg_valid.status_code == 200 else {}
ecg_valid_ok = (r_ecg_valid.status_code == 200 and 
                "predicted_class_name" in ecg_data and 
                ecg_data.get("predicted_class_id") in [0, 1, 2, 3, 4] and 
                len(ecg_data.get("class_probabilities", {})) == 5)
record("ECG Heartbeat", "POST /predict/ecg-heartbeat (Valid 187 Samples)", ecg_valid_ok, [
    f"HTTP Status: {r_ecg_valid.status_code}",
    f"Predicted Beat Class: {ecg_data.get('predicted_class_name')} (ID: {ecg_data.get('predicted_class_id')})",
    f"Confidence: {ecg_data.get('confidence_percentage')}%",
    f"5-Class Probabilities: {ecg_data.get('class_probabilities')}"
])

# Invalid length (45 samples instead of 187)
r_ecg_inv_len = requests.post(f"{API_BASE}/predict/ecg-heartbeat", json={"signal": [0.1] * 45})
ecg_inv_len_ok = r_ecg_inv_len.status_code == 422
record("ECG Heartbeat", "POST /predict/ecg-heartbeat (Invalid Length: 45 samples)", ecg_inv_len_ok, [
    f"HTTP Status: {r_ecg_inv_len.status_code} (Expected 422)",
    f"Validation Error: {r_ecg_inv_len.json().get('detail', [{}])[0].get('msg')}"
])

# Invalid types (non-numeric)
r_ecg_inv_type = requests.post(f"{API_BASE}/predict/ecg-heartbeat", json={"signal": ["not_a_float"] * 187})
ecg_inv_type_ok = r_ecg_inv_type.status_code == 422
record("ECG Heartbeat", "POST /predict/ecg-heartbeat (Invalid Data Type: strings)", ecg_inv_type_ok, [
    f"HTTP Status: {r_ecg_inv_type.status_code} (Expected 422)",
    f"Validation Error: {r_ecg_inv_type.json().get('detail', [{}])[0].get('msg')}"
])

# 2.3 SisFall Fall Endpoint
# Valid ADL movement
adl_req = {
    "accel_mag_max": 11.4, "accel_mag_min": 8.2, "accel_mag_mean": 9.8,
    "accel_y_mean": 9.8, "accel_y_std": 1.1, "gyro_mag_max": 0.9, "accel_jerk_max": 3.6
}
r_f_adl = requests.post(f"{API_BASE}/predict/fall", json=adl_req)
f_adl_data = r_f_adl.json() if r_f_adl.status_code == 200 else {}
f_adl_ok = (r_f_adl.status_code == 200 and not f_adl_data.get("is_fall"))
record("SisFall Movement", "POST /predict/fall (Valid ADL Movement)", f_adl_ok, [
    f"HTTP Status: {r_f_adl.status_code}",
    f"Prediction: {f_adl_data.get('prediction')}",
    f"Fall Probability: {f_adl_data.get('fall_probability')}",
    f"Alert Level: {f_adl_data.get('alert_level')}"
])

# Valid Fall event
fall_req = {
    "accel_mag_max": 36.8, "accel_mag_min": 1.1, "accel_mag_mean": 18.5,
    "accel_y_mean": 18.0, "accel_y_std": 8.5, "gyro_mag_max": 6.8, "accel_jerk_max": 28.5
}
r_f_fall = requests.post(f"{API_BASE}/predict/fall", json=fall_req)
f_fall_data = r_f_fall.json() if r_f_fall.status_code == 200 else {}
f_fall_ok = (r_f_fall.status_code == 200 and f_fall_data.get("is_fall"))
record("SisFall Movement", "POST /predict/fall (Valid Fall Event)", f_fall_ok, [
    f"HTTP Status: {r_f_fall.status_code}",
    f"Prediction: {f_fall_data.get('prediction')}",
    f"Fall Probability: {f_fall_data.get('fall_probability')}",
    f"Alert Level: {f_fall_data.get('alert_level')}"
])

# Invalid missing required field
r_f_inv = requests.post(f"{API_BASE}/predict/fall", json={"accel_y_mean": 9.8})
f_inv_ok = r_f_inv.status_code == 422
record("SisFall Movement", "POST /predict/fall (Missing Required accel_mag_max)", f_inv_ok, [
    f"HTTP Status: {r_f_inv.status_code} (Expected 422)",
    f"Validation Error: {r_f_inv.json().get('detail', [{}])[0].get('msg')}"
])

# 2.4 Cardiac Rhythm Endpoint
r_rhy_valid = requests.post(f"{API_BASE}/predict/cardiac-rhythm", json={"heart_rate": 130.0, "rr_intervals": [0.46, 0.45, 0.47, 0.46, 0.45]})
rhy_data = r_rhy_valid.json() if r_rhy_valid.status_code == 200 else {}
rhy_ok = r_rhy_valid.status_code == 200 and rhy_data.get("rhythm_category") == "Tachycardia"
record("Cardiac Rhythm", "POST /predict/cardiac-rhythm (Tachycardia 130 BPM)", rhy_ok, [
    f"HTTP Status: {r_rhy_valid.status_code}",
    f"Category: {rhy_data.get('rhythm_category')} (Severity: {rhy_data.get('severity')})",
    f"HRV Mean R-R: {rhy_data.get('hrv_metrics', {}).get('mean_rr_ms')} ms"
])

r_rhy_inv = requests.post(f"{API_BASE}/predict/cardiac-rhythm", json={"heart_rate": 15.0})
record("Cardiac Rhythm", "POST /predict/cardiac-rhythm (Invalid HR 15 BPM)", r_rhy_inv.status_code == 422, [
    f"HTTP Status: {r_rhy_inv.status_code} (Expected 422)",
    f"Validation: {r_rhy_inv.json().get('detail', [{}])[0].get('msg')}"
])

# 2.5 Oxygenation Endpoint
r_ox_valid = requests.post(f"{API_BASE}/predict/oxygenation", json={"spo2": 88.0, "respiratory_rate": 22.0})
ox_data = r_ox_valid.json() if r_ox_valid.status_code == 200 else {}
ox_ok = r_ox_valid.status_code == 200 and ox_data.get("oxygenation_category") == "Moderate-to-Severe Hypoxemia"
record("Oxygenation", "POST /predict/oxygenation (Hypoxemia 88% SpO2)", ox_ok, [
    f"HTTP Status: {r_ox_valid.status_code}",
    f"Category: {ox_data.get('oxygenation_category')} (Severity: {ox_data.get('severity')})",
    f"Recommendation: {ox_data.get('clinical_recommendation')}"
])

r_ox_inv = requests.post(f"{API_BASE}/predict/oxygenation", json={"spo2": 45.0})
record("Oxygenation", "POST /predict/oxygenation (Invalid SpO2 45%)", r_ox_inv.status_code == 422, [
    f"HTTP Status: {r_ox_inv.status_code} (Expected 422)",
    f"Validation: {r_ox_inv.json().get('detail', [{}])[0].get('msg')}"
])

# 2.6 Unified Composite Endpoint
uni_req = {
    "vitals": {"heart_rate": 108.0, "systolic_bp": 195.0, "diastolic_bp": 125.0, "weight_kg": 95.0, "height_m": 1.65},
    "ecg": {"signal": ecg_sample},
    "movement": fall_req,
    "rhythm": {"heart_rate": 145.0},
    "oxygenation": {"spo2": 83.0}
}
r_uni = requests.post(f"{API_BASE}/predict/unified", json=uni_req)
uni_data = r_uni.json() if r_uni.status_code == 200 else {}
uni_ok = (r_uni.status_code == 200 and 
          uni_data.get("triage_summary", {}).get("overall_severity") == "CRITICAL" and 
          len(uni_data.get("triage_summary", {}).get("active_alerts", [])) >= 3)
record("Unified Triage", "POST /predict/unified (Multimodal Critical Event)", uni_ok, [
    f"HTTP Status: {r_uni.status_code}",
    f"Overall Triage Severity: {uni_data.get('triage_summary', {}).get('overall_severity')}",
    f"Active Alerts ({len(uni_data.get('triage_summary', {}).get('active_alerts', []))}): {uni_data.get('triage_summary', {}).get('active_alerts')}",
    f"Vitals Status: {uni_data.get('vitals_assessment', {}).get('model_estimated_risk')}",
    f"ECG Status: {uni_data.get('ecg_assessment', {}).get('predicted_class_name')}",
    f"Fall Status: {uni_data.get('fall_assessment', {}).get('prediction')}",
    f"Rhythm Status: {uni_data.get('rhythm_assessment', {}).get('rhythm_category')}",
    f"Oxygen Status: {uni_data.get('oxygenation_assessment', {}).get('oxygenation_category')}"
])

# =============================================================================
# PART 3: DASHBOARD INTEGRATION & SIMULATION REPLAY
# =============================================================================
print("\n--- 3. Testing Dashboard Integration & Simulation Replay ---")

# Check dashboard HTTP status
try:
    r_dash = requests.get(DASH_BASE, timeout=3.0)
    dash_ok = r_dash.status_code == 200
    record("Dashboard HTTP", "GET http://localhost:8501", dash_ok, [
        f"HTTP Status: {r_dash.status_code}",
        f"Content-Type: {r_dash.headers.get('content-type')}"
    ])
except Exception as e:
    record("Dashboard HTTP", "GET http://localhost:8501", False, [f"Error: {e}"])

# Test dashboard live backend query functions
sys.path.insert(0, str(Path("CareEdge-1/dashboard").resolve()))
from app import (
    query_vitals_prediction,
    query_ecg_prediction,
    query_fall_prediction,
    query_rhythm_prediction,
    query_oxygenation_prediction,
)

# Dynamic query tests
res_v_dash, src_v = query_vitals_prediction(v_low_req)
res_e_dash, src_e = query_ecg_prediction(ecg_sample)
res_f_dash, src_f = query_fall_prediction(adl_req)
res_r_dash, src_r = query_rhythm_prediction(130.0)
res_o_dash, src_o = query_oxygenation_prediction(88.0)

dash_integration_ok = (
    res_v_dash.get("status") == "success"
    and res_e_dash.get("status") == "success"
    and res_f_dash.get("status") == "success"
    and res_r_dash.get("status") == "success"
    and res_o_dash.get("status") == "success"
)
record("Dashboard-Backend Integration", "Dashboard Live Query to Clinical Engines", dash_integration_ok, [
    f"Vitals Provider: {src_v} -> Risk: {res_v_dash.get('model_estimated_risk')}",
    f"ECG Provider: {src_e} -> Class: {res_e_dash.get('predicted_class_name')}",
    f"Fall Provider: {src_f} -> Prediction: {res_f_dash.get('prediction')}",
    f"Rhythm Provider: {src_r} -> Category: {res_r_dash.get('rhythm_category')}",
    f"Oxygen Provider: {src_o} -> Category: {res_o_dash.get('oxygenation_category')}",
])

# Test original 50 Hz patient simulation replay
sys.path.insert(0, str(Path("CareEdge-1/clade/ml").resolve()))
from inference import CLADEInference

training_data_path = Path("CareEdge-1/data/careedge_training_data.csv")
df_train = pd.read_csv(training_data_path)
p1_slice = df_train[df_train["patient_id"] == "P001"].sort_values("timestamp").reset_index(drop=True).iloc[:100].copy()

legacy_engine = CLADEInference()
sim_out = legacy_engine.predict(p1_slice)

sim_replay_ok = ("risk" in sim_out and 
                 "early_warning" in sim_out and 
                 "unified_decision" in sim_out and 
                 sim_out["risk"]["predicted_event"] == "normal" and 
                 sim_out["unified_decision"]["state"] == "NORMAL")
record("Simulation Replay", "CLADE Patient P001 50 Hz Replay", sim_replay_ok, [
    f"Patient ID: P001 (100 windowed samples)",
    f"Risk Output: predicted_event='{sim_out['risk']['predicted_event']}', score={sim_out['risk']['risk_score']}",
    f"Early Warning: state='{sim_out['early_warning']['warning_state']}', pre_fall_prob={sim_out['early_warning']['pre_fall_probability']}%",
    f"Unified Decision: action='{sim_out['unified_decision']['action']}', priority={sim_out['unified_decision']['priority']}"
])

# =============================================================================
# PART 4: AUDITED ML METRICS & EVALUATION MANIFESTS
# =============================================================================
print("\n--- 4. Auditing Saved Evaluation Manifests ---")

manifest_dir = Path("CareEdge-1/data/manifests")

with open(manifest_dir / "sisfall_evaluation_report.json") as f:
    sisfall_rep = json.load(f)
s_acc = sisfall_rep["test_metrics"]["accuracy"]
s_rec = sisfall_rep["test_metrics"]["recall"]
s_fpr = sisfall_rep["test_metrics"]["false_positive_rate"]
s_ok = abs(s_acc - 0.998738) < 0.001 and s_rec == 1.0

record("ML Metrics Audit", "SisFall Manifest (38 Subjects / 7 Held-Out)", s_ok, [
    f"Reported Test Accuracy: {s_acc * 100:.2f}% (Expected: 99.87%)",
    f"Fall Recall: {s_rec * 100:.2f}% (300/300 falls detected)",
    f"False Positive Rate: {s_fpr * 100:.2f}% (1 false alarm / 493 ADLs)",
    f"Subject-Level Split: {sisfall_rep.get('subject_level_split')}"
])

with open(manifest_dir / "ecg_evaluation_report.json") as f:
    ecg_rep = json.load(f)
e_acc = ecg_rep["test_metrics"]["accuracy"]
e_prec = ecg_rep["test_metrics"]["macro_precision"]
e_rec = ecg_rep["test_metrics"]["macro_recall"]
e_f1 = ecg_rep["test_metrics"]["macro_f1"]
e_auc = ecg_rep["test_metrics"]["macro_roc_auc"]
e_classes = ecg_rep.get("supported_classes", [])
e_ok = abs(e_acc - 0.962132) < 0.001 and len(e_classes) == 5

record("ML Metrics Audit", "MIT-BIH ECG Manifest (21,892 Untouched Test Beats)", e_ok, [
    f"Reported Test Accuracy: {e_acc * 100:.2f}% (Expected: 96.21%)",
    f"Macro Precision: {e_prec * 100:.2f}% | Macro Recall: {e_rec * 100:.2f}%",
    f"Macro F1-Score: {e_f1 * 100:.2f}% | Macro ROC-AUC: {e_auc * 100:.2f}%",
    f"Supported Classes ({len(e_classes)}): {e_classes}"
])

with open(manifest_dir / "hypertension_evaluation_report.json") as f:
    htn_rep = json.load(f)
h_acc = htn_rep["test_metrics"]["accuracy"]
h_brier = htn_rep["test_metrics"]["brier_score"]
h_note = htn_rep.get("clinical_note", "")
h_ok = h_acc == 1.0 and "deterministically derived" in h_note

record("ML Metrics Audit", "Synthetic Vital Signs Risk Manifest", h_ok, [
    f"Reported Test Accuracy: {h_acc * 100:.2f}% (Rule-derived benchmark)",
    f"Brier Score: {h_brier:.4f}",
    f"Clinical Audit Note: {h_note}"
])

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "=" * 75)
total_tests = len(test_log)
passed_tests = sum(1 for t in test_log if t["passed"])
print(f"VERIFICATION RESULTS: {passed_tests} / {total_tests} Tests Passed")
if all_passed:
    print("STATUS: ALL VERIFICATION CHECKS PASSED (100% SUCCESS)")
else:
    print("STATUS: ONE OR MORE CHECKS FAILED")
print("=" * 75)
