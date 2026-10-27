import requests
import json

BASE = "http://127.0.0.1:8000"

def test_endpoint(name, method, url, payload, expected_status):
    fn = requests.get if method == "GET" else requests.post
    resp = fn(f"{BASE}{url}", json=payload)
    status_match = resp.status_code == expected_status
    status_str = "PASS" if status_match else "FAIL"
    print(f"[{name}] Status: {resp.status_code} (Expected {expected_status}) -> {status_str}")
    if resp.status_code == 200:
        data = resp.json()
        if "model_estimated_risk" in data:
            print(f"   -> Risk: {data['model_estimated_risk']}, Prob: {data['high_risk_probability']:.3f}, Stage: {data['clinical_blood_pressure_assessment']['stage']}")
        elif "predicted_class_name" in data:
            print(f"   -> ECG Class: {data['predicted_class_name']}, Conf: {data['confidence_percentage']:.1f}%")
        elif "prediction" in data:
            print(f"   -> Fall: {data['prediction']}, Prob: {data['fall_probability']:.3f}")
        elif "triage_summary" in data:
            print(f"   -> Triage Severity: {data['triage_summary']['overall_severity']}, Alerts: {data['triage_summary']['active_alerts']}")
    else:
        err = resp.json().get("detail", "")
        # truncate for output
        err_str = str(err)[:90] + ("..." if len(str(err)) > 90 else "")
        print(f"   -> Handled Validation: {err_str}")
    return status_match

print("=" * 70)
print("CAREEDGE LIVE API VERIFICATION MATRIX")
print("=" * 70)

results = []

# 1. Health check
results.append(test_endpoint("Health Check", "GET", "/health", None, 200))

# 2. Model Status
results.append(test_endpoint("Model Status", "GET", "/models/status", None, 200))

# 3. Vitals Valid Low Risk
results.append(test_endpoint("Vitals Valid Low Risk", "POST", "/predict/hypertension-risk", {
    "heart_rate": 72.0, "respiratory_rate": 16.0, "body_temperature": 36.6,
    "oxygen_saturation": 98.0, "systolic_bp": 118.0, "diastolic_bp": 76.0,
    "age": 40.0, "gender": "Female", "weight_kg": 60.0, "height_m": 1.68
}, 200))

# 4. Vitals Valid High Risk & Stage 2 HTN
results.append(test_endpoint("Vitals Valid High Risk / Stage 2 HTN", "POST", "/predict/hypertension-risk", {
    "heart_rate": 98.0, "respiratory_rate": 20.0, "body_temperature": 37.1,
    "oxygen_saturation": 96.0, "systolic_bp": 148.0, "diastolic_bp": 94.0,
    "age": 55.0, "gender": "Male", "weight_kg": 95.0, "height_m": 1.70
}, 200))

# 5. Vitals Invalid (HR < 30)
results.append(test_endpoint("Vitals Invalid HR (15 bpm)", "POST", "/predict/hypertension-risk", {
    "heart_rate": 15.0, "systolic_bp": 120.0, "diastolic_bp": 80.0
}, 422))

# 6. Vitals Invalid Gender
results.append(test_endpoint("Vitals Invalid Gender ('Unknown')", "POST", "/predict/hypertension-risk", {
    "heart_rate": 75.0, "gender": "Unknown"
}, 422))

# 7. ECG Valid Normal
ecg_normal = [0.0] * 187
ecg_normal[40] = 1.0
results.append(test_endpoint("ECG Valid Signal (187 points)", "POST", "/predict/ecg-heartbeat", {
    "signal": ecg_normal
}, 200))

# 8. ECG Invalid Length (50 points instead of 187)
results.append(test_endpoint("ECG Invalid Length (50 points)", "POST", "/predict/ecg-heartbeat", {
    "signal": [0.1] * 50
}, 422))

# 9. Fall Valid ADL
results.append(test_endpoint("Fall Valid ADL Movement", "POST", "/predict/fall", {
    "accel_mag_max": 11.5, "accel_mag_min": 8.2, "accel_mag_mean": 9.8,
    "accel_y_mean": 9.8, "accel_y_std": 1.1, "gyro_mag_max": 0.8, "accel_jerk_max": 3.5
}, 200))

# 10. Fall Valid Fall Event
results.append(test_endpoint("Fall Valid Fall Event", "POST", "/predict/fall", {
    "accel_mag_max": 36.2, "accel_mag_min": 1.0, "accel_mag_mean": 18.6,
    "accel_y_mean": 18.2, "accel_y_std": 8.4, "gyro_mag_max": 6.5, "accel_jerk_max": 28.0
}, 200))

# 11. Fall Invalid (Missing required accel_mag_max)
results.append(test_endpoint("Fall Invalid Missing Field", "POST", "/predict/fall", {
    "accel_y_mean": 9.8
}, 422))

# 12. Unified Valid Multi-Modal Alert
results.append(test_endpoint("Unified Valid Multi-Modal Alert", "POST", "/predict/unified", {
    "vitals": {"heart_rate": 105.0, "systolic_bp": 190.0, "diastolic_bp": 125.0, "weight_kg": 90.0, "height_m": 1.65},
    "ecg": {"signal": ecg_normal},
    "movement": {"accel_mag_max": 38.0, "accel_y_mean": 19.0, "gyro_mag_max": 7.0}
}, 200))

print("=" * 70)
print(f"RESULTS: {sum(results)} / {len(results)} tests passed.")
print("=" * 70)
