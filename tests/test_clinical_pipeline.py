import sys
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

CLINICAL_DIR = Path(__file__).resolve().parents[1] / "clinical"
if str(CLINICAL_DIR) not in sys.path:
    sys.path.insert(0, str(CLINICAL_DIR))

from api import app
from clinical_inference import CareEdgeClinicalEngine

client = TestClient(app)


# =============================================================================
# 1. SYSTEM & HEALTH TESTS
# =============================================================================

def test_health_check():
    """Verify health endpoint returns 200 and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_models_status():
    """Verify all models report loaded status without leaking internal paths."""
    response = client.get("/models/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    models = data["models"]
    assert "sisfall_fall_model" in models
    assert "hypertension_risk_model" in models
    assert "ecg_heartbeat_model" in models
    assert models["hypertension_risk_model"]["loaded"] is True
    assert models["ecg_heartbeat_model"]["loaded"] is True
    assert models["sisfall_fall_model"]["loaded"] is True
    # Ensure no local file paths leaked
    for m in models.values():
        for val in m.values():
            if isinstance(val, str):
                assert "C:\\" not in val
                assert "/Users/" not in val


# =============================================================================
# 2. HYPERTENSION & VITAL SIGNS TESTS
# =============================================================================

def test_hypertension_risk_valid():
    """Test valid vital signs request."""
    payload = {
        "heart_rate": 75.0,
        "respiratory_rate": 16.0,
        "body_temperature": 36.8,
        "oxygen_saturation": 98.0,
        "systolic_bp": 122.0,
        "diastolic_bp": 78.0,
        "age": 45.0,
        "gender": "Female",
        "weight_kg": 65.0,
        "height_m": 1.68,
    }
    response = client.post("/predict/hypertension-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["model_estimated_risk"] in ["Low Risk", "High Risk"]
    assert 0.0 <= data["high_risk_probability"] <= 1.0
    assert "clinical_blood_pressure_assessment" in data
    assert data["clinical_blood_pressure_assessment"]["stage"] == "Elevated Blood Pressure"
    assert "disclaimer" in data


def test_hypertension_risk_invalid_heart_rate():
    """Test that physiologically impossible heart rate is rejected."""
    payload = {
        "heart_rate": 500.0,  # Invalid: > 250 bpm
        "respiratory_rate": 16.0,
        "body_temperature": 36.8,
        "oxygen_saturation": 98.0,
        "systolic_bp": 120.0,
        "diastolic_bp": 80.0,
        "age": 30.0,
        "gender": "Male",
        "weight_kg": 70.0,
        "height_m": 1.75,
    }
    response = client.post("/predict/hypertension-risk", json=payload)
    assert response.status_code == 422


def test_hypertension_risk_invalid_gender():
    """Test that invalid gender string is rejected."""
    payload = {
        "heart_rate": 70.0,
        "respiratory_rate": 16.0,
        "body_temperature": 36.8,
        "oxygen_saturation": 98.0,
        "systolic_bp": 120.0,
        "diastolic_bp": 80.0,
        "age": 30.0,
        "gender": "Alien",  # Invalid
        "weight_kg": 70.0,
        "height_m": 1.75,
    }
    response = client.post("/predict/hypertension-risk", json=payload)
    assert response.status_code == 422


def test_blood_pressure_stages():
    """Verify ACC/AHA 2017 staging boundary logic."""
    engine = CareEdgeClinicalEngine()
    # Normal
    res = engine.evaluate_blood_pressure(115, 75)
    assert res["stage"] == "Normal Blood Pressure"
    assert res["severity"] == "LOW"

    # Elevated
    res = engine.evaluate_blood_pressure(125, 75)
    assert res["stage"] == "Elevated Blood Pressure"

    # Stage 1
    res = engine.evaluate_blood_pressure(135, 85)
    assert res["stage"] == "Stage 1 Hypertension"

    # Stage 2
    res = engine.evaluate_blood_pressure(145, 95)
    assert res["stage"] == "Stage 2 Hypertension"
    assert res["severity"] == "HIGH"

    # Crisis
    res = engine.evaluate_blood_pressure(190, 130)
    assert res["stage"] == "Hypertensive Crisis"
    assert res["severity"] == "CRITICAL"


# =============================================================================
# 3. ECG HEARTBEAT CLASSIFICATION TESTS
# =============================================================================

def test_ecg_classification_valid():
    """Test valid 187-sample ECG heartbeat."""
    # Synthetic clean beat: R-peak at index 40
    sig = [0.0] * 187
    for i in range(25, 55):
        sig[i] = 1.0 - abs(i - 40) / 15.0

    payload = {"signal": sig}
    response = client.post("/predict/ecg-heartbeat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["predicted_class_id"] in [0, 1, 2, 3, 4]
    assert isinstance(data["predicted_class_name"], str)
    assert "class_probabilities" in data
    assert len(data["class_probabilities"]) == 5
    assert "disclaimer" in data


def test_ecg_classification_invalid_length():
    """Test that wrong signal length (< 187 samples) is rejected."""
    payload = {"signal": [0.5] * 50}  # Only 50 samples
    response = client.post("/predict/ecg-heartbeat", json=payload)
    assert response.status_code == 422


# =============================================================================
# 4. SISFALL FALL DETECTION TESTS
# =============================================================================

def test_fall_detection_valid():
    """Test valid SisFall movement features."""
    payload = {
        "accel_mag_max": 32.5,
        "accel_mag_min": 1.5,
        "accel_mag_mean": 11.2,
        "accel_y_mean": 18.0,
        "accel_y_std": 12.0,
        "gyro_mag_max": 5.2,
        "accel_jerk_max": 20.0,
    }
    response = client.post("/predict/fall", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "is_fall" in data
    assert isinstance(data["is_fall"], bool)
    assert 0.0 <= data["fall_probability"] <= 1.0


# =============================================================================
# 5. UNIFIED CLINICAL PREDICTION TEST
# =============================================================================

def test_unified_prediction():
    """Test combined triage prediction."""
    sig = [0.0] * 187
    payload = {
        "vitals": {
            "heart_rate": 80.0,
            "respiratory_rate": 16.0,
            "body_temperature": 36.8,
            "oxygen_saturation": 98.0,
            "systolic_bp": 145.0,  # Stage 2 HTN
            "diastolic_bp": 92.0,
            "age": 60.0,
            "gender": "Male",
            "weight_kg": 85.0,
            "height_m": 1.75,
        },
        "ecg": {"signal": sig},
        "movement": {
            "accel_mag_max": 12.0,
            "accel_mag_min": 8.5,
            "accel_mag_mean": 9.8,
        },
    }
    response = client.post("/predict/unified", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["vitals_assessment"] is not None
    assert data["ecg_assessment"] is not None
    assert data["fall_assessment"] is not None
    assert data["triage_summary"]["overall_severity"] in ["HIGH", "CRITICAL", "NORMAL"]


# =============================================================================
# 6. CARDIAC RHYTHM TESTS (TACHYCARDIA / BRADYCARDIA)
# =============================================================================

def test_cardiac_rhythm_categories():
    """Verify ACC/AHA rhythm rate staging boundaries."""
    engine = CareEdgeClinicalEngine()

    # Severe Bradycardia
    r_sev_brady = engine.evaluate_cardiac_rhythm(35.0)
    assert r_sev_brady["rhythm_category"] == "Severe Bradycardia"
    assert r_sev_brady["severity"] == "CRITICAL"

    # Bradycardia
    r_brady = engine.evaluate_cardiac_rhythm(50.0)
    assert r_brady["rhythm_category"] == "Bradycardia"
    assert r_brady["severity"] == "MEDIUM"

    # Normal Sinus
    r_norm = engine.evaluate_cardiac_rhythm(75.0)
    assert r_norm["rhythm_category"] == "Normal Sinus Rate"
    assert r_norm["severity"] == "LOW"

    # Tachycardia
    r_tachy = engine.evaluate_cardiac_rhythm(120.0)
    assert r_tachy["rhythm_category"] == "Tachycardia"
    assert r_tachy["severity"] == "HIGH"

    # Severe Tachycardia
    r_sev_tachy = engine.evaluate_cardiac_rhythm(160.0)
    assert r_sev_tachy["rhythm_category"] == "Severe Tachycardia"
    assert r_sev_tachy["severity"] == "CRITICAL"


def test_cardiac_rhythm_endpoint_valid_with_hrv():
    """Test cardiac rhythm API endpoint with simulated R-R intervals."""
    payload = {
        "heart_rate": 72.0,
        "rr_intervals": [0.82, 0.84, 0.81, 0.83, 0.85, 0.82, 0.80, 0.84],
    }
    response = client.post("/predict/cardiac-rhythm", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["rhythm_category"] == "Normal Sinus Rate"
    assert "hrv_metrics" in data
    assert data["hrv_metrics"]["interval_count"] == 8
    assert data["hrv_metrics"]["mean_rr_ms"] > 0


def test_cardiac_rhythm_invalid_hr():
    """Verify rejection of physiologically impossible heart rates."""
    response = client.post("/predict/cardiac-rhythm", json={"heart_rate": 15.0})
    assert response.status_code == 422


# =============================================================================
# 7. OXYGENATION & HYPOXEMIA TESTS
# =============================================================================

def test_oxygenation_categories():
    """Verify pulse oximetry hypoxemia severity boundaries."""
    engine = CareEdgeClinicalEngine()

    # Normal
    o_norm = engine.evaluate_oxygenation(98.0)
    assert o_norm["oxygenation_category"] == "Normal Oxygenation"
    assert o_norm["severity"] == "LOW"

    # Mild Hypoxemia
    o_mild = engine.evaluate_oxygenation(93.0)
    assert o_mild["oxygenation_category"] == "Mild Hypoxemia"
    assert o_mild["severity"] == "MEDIUM"

    # Moderate-to-Severe
    o_mod = engine.evaluate_oxygenation(88.0)
    assert o_mod["oxygenation_category"] == "Moderate-to-Severe Hypoxemia"
    assert o_mod["severity"] == "HIGH"

    # Critical Hypoxemia
    o_crit = engine.evaluate_oxygenation(82.0)
    assert o_crit["oxygenation_category"] == "Critical Hypoxemia"
    assert o_crit["severity"] == "CRITICAL"


def test_oxygenation_endpoint_valid_with_respiration():
    """Test oxygenation endpoint with respiratory rate status."""
    payload = {"spo2": 96.0, "respiratory_rate": 18.0}
    response = client.post("/predict/oxygenation", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["oxygenation_category"] == "Normal Oxygenation"
    assert data["respiratory_status"]["tachypnea"] is False


def test_oxygenation_invalid_spo2():
    """Verify rejection of out-of-bounds SpO2."""
    response = client.post("/predict/oxygenation", json={"spo2": 35.0})
    assert response.status_code == 422


# =============================================================================
# 8. SHAPES, MANIFESTS & REPRODUCIBILITY TESTS
# =============================================================================

def test_ecg_feature_extraction_shape():
    """Verify that single-beat feature extraction yields exact 32 features."""
    engine = CareEdgeClinicalEngine()
    sig = np.zeros(187, dtype=np.float32)
    sig[35] = 1.0
    feats = engine.extract_single_ecg_features(sig)
    assert feats.shape[1] == 32
    assert "mean" in feats.columns
    assert "kurtosis" in feats.columns


def test_manifest_reproducibility():
    """Verify evaluation manifests exist on disk and hold verified metrics."""
    manifest_dir = Path(__file__).resolve().parents[1] / "data" / "manifests"
    import json

    with open(manifest_dir / "ecg_evaluation_report.json") as f:
        ecg_m = json.load(f)
    assert abs(ecg_m["test_metrics"]["accuracy"] - 0.96213) < 0.001

    with open(manifest_dir / "sisfall_evaluation_report.json") as f:
        sis_m = json.load(f)
    assert abs(sis_m["test_metrics"]["accuracy"] - 0.99873) < 0.001

    with open(manifest_dir / "hypertension_evaluation_report.json") as f:
        htn_m = json.load(f)
    assert htn_m["test_metrics"]["accuracy"] == 1.0


def test_unified_multimodal_comprehensive_alert():
    """Test full multimodal request with all 5 subsystems active."""
    payload = {
        "vitals": {
            "heart_rate": 105.0,
            "respiratory_rate": 22.0,
            "body_temperature": 37.5,
            "oxygen_saturation": 96.0,
            "systolic_bp": 185.0,  # Crisis
            "diastolic_bp": 125.0,
            "age": 65.0,
            "gender": "Female",
            "weight_kg": 75.0,
            "height_m": 1.60,
        },
        "movement": {
            "accel_mag_max": 38.5,
            "accel_mag_min": 1.2,
            "accel_mag_mean": 18.0,
            "accel_y_mean": 18.0,
            "accel_y_std": 12.0,
            "gyro_mag_max": 6.5,
            "accel_jerk_max": 25.0,
        },
        "rhythm": {"heart_rate": 145.0},  # Severe Tachycardia
        "oxygenation": {"spo2": 84.0},  # Critical Hypoxemia
    }
    response = client.post("/predict/unified", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["triage_summary"]["overall_severity"] == "CRITICAL"
    alerts = data["triage_summary"]["active_alerts"]
    assert any("Blood Pressure Alert" in a for a in alerts)
    assert any("FALL DETECTED" in a for a in alerts)
    assert any("Cardiac Rhythm Alert" in a for a in alerts)
    assert any("Oxygenation Alert" in a for a in alerts)
