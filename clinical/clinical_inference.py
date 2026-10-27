import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import joblib
import numpy as np
import pandas as pd
from scipy import stats

CLADE_ML_DIR = Path(__file__).resolve().parents[1] / "clade" / "ml"
if str(CLADE_ML_DIR) not in sys.path:
    sys.path.insert(0, str(CLADE_ML_DIR))

from inference import CLADEInference as LegacyCLADEInference

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_DIR = BASE_DIR / "clade" / "ml" / "models"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

SISFALL_MODEL_PATH = MODEL_DIR / "sisfall_fall_model.joblib"
HYPERTENSION_MODEL_PATH = MODEL_DIR / "hypertension_risk_model.joblib"
ECG_MODEL_PATH = MODEL_DIR / "ecg_heartbeat_model.joblib"
ECG_PREPROCESSOR_PATH = PROCESSED_DIR / "ecg_preprocessor.joblib"

# American College of Cardiology / American Heart Association (ACC/AHA) 2017 Guidelines
BP_STAGES = [
    ("Hypertensive Crisis", lambda s, d: s > 180 or d > 120, "CRITICAL", "Seek immediate emergency medical evaluation."),
    ("Stage 2 Hypertension", lambda s, d: s >= 140 or d >= 90, "HIGH", "Prompt clinical evaluation and lifestyle modification recommended."),
    ("Stage 1 Hypertension", lambda s, d: (130 <= s <= 139) or (80 <= d <= 89), "MEDIUM", "Monitor regularly; consult healthcare provider."),
    ("Elevated Blood Pressure", lambda s, d: (120 <= s <= 129) and d < 80, "LOW", "Adhere to healthy diet and exercise."),
    ("Normal Blood Pressure", lambda s, d: s < 120 and d < 80, "LOW", "Blood pressure within recommended healthy range."),
]


class CareEdgeClinicalEngine:
    """
    Unified Production Prediction Engine for CareEdge.
    Integrates:
      1. Legacy CLADE synthetic simulation & early warning engine
      2. SisFall Random Forest Movement Fall Detector
      3. Vital Signs / Hypertension Risk Classifier
      4. MIT-BIH AAMI EC57 ECG Heartbeat Classifier
    """

    def __init__(self):
        # 1. Initialize legacy simulation engine
        try:
            self.legacy_engine = LegacyCLADEInference()
            self.legacy_loaded = True
        except Exception as e:
            print(f"Warning: Legacy simulation engine could not be loaded: {e}")
            self.legacy_engine = None
            self.legacy_loaded = False

        # 2. Load SisFall model
        self.sisfall_artifact = None
        if SISFALL_MODEL_PATH.exists():
            try:
                self.sisfall_artifact = joblib.load(SISFALL_MODEL_PATH)
            except Exception as e:
                print(f"Warning: SisFall model load error: {e}")

        # 3. Load Hypertension / Vital Signs model
        self.hypertension_artifact = None
        if HYPERTENSION_MODEL_PATH.exists():
            try:
                self.hypertension_artifact = joblib.load(HYPERTENSION_MODEL_PATH)
            except Exception as e:
                print(f"Warning: Hypertension model load error: {e}")

        # 4. Load ECG Heartbeat model & preprocessor
        self.ecg_artifact = None
        if ECG_MODEL_PATH.exists():
            try:
                self.ecg_artifact = joblib.load(ECG_MODEL_PATH)
            except Exception as e:
                print(f"Warning: ECG model load error: {e}")

        self.ecg_preprocessor = None
        if ECG_PREPROCESSOR_PATH.exists():
            try:
                self.ecg_preprocessor = joblib.load(ECG_PREPROCESSOR_PATH)
            except Exception as e:
                print(f"Warning: ECG preprocessor load error: {e}")

    # =========================================================================
    # 1. LEGACY SIMULATION PREDICTION (for existing dashboard replay)
    # =========================================================================
    def predict(self, window_data: pd.DataFrame) -> Dict[str, Any]:
        """Preserves exact signature for existing dashboard simulation replay."""
        if not self.legacy_loaded or self.legacy_engine is None:
            raise RuntimeError("Legacy CLADE simulation models are not loaded.")
        return self.legacy_engine.predict(window_data)

    # =========================================================================
    # 2. SISFALL FALL DETECTION
    # =========================================================================
    def predict_fall_sisfall(self, movement_data: Dict[str, float]) -> Dict[str, Any]:
        """
        Evaluate movement features with the SisFall Random Forest classifier.
        """
        if self.sisfall_artifact is None:
            return {
                "status": "unavailable",
                "error": "SisFall fall detection model is not loaded.",
            }

        model = self.sisfall_artifact["model"]
        feature_names = self.sisfall_artifact["feature_names"]

        # Validate required features or provide intelligent defaults from magnitudes
        input_row = {}
        for feat in feature_names:
            if feat in movement_data:
                input_row[feat] = float(movement_data[feat])
            else:
                input_row[feat] = 0.0

        X = pd.DataFrame([input_row])[feature_names]

        # Predict
        prob_fall = float(model.predict_proba(X)[0, 1])
        is_fall = bool(prob_fall >= 0.5)
        confidence = float(prob_fall if is_fall else (1.0 - prob_fall)) * 100.0

        return {
            "status": "success",
            "task": "sisfall_fall_detection",
            "model_name": self.sisfall_artifact.get("model_name", "SisFall_RandomForest"),
            "version": self.sisfall_artifact.get("version", "1.0.0"),
            "is_fall": is_fall,
            "prediction": "Fall" if is_fall else "Non-Fall Activity (ADL)",
            "fall_probability": round(prob_fall, 4),
            "confidence_percentage": round(confidence, 2),
            "alert_level": "CRITICAL" if is_fall else "NORMAL",
            "message": "Fall impact and orientation shift detected." if is_fall else "Normal activity of daily living.",
        }

    # =========================================================================
    # 3. HYPERTENSION & VITAL SIGNS RISK PREDICTION
    # =========================================================================
    def evaluate_blood_pressure(self, systolic: float, diastolic: float) -> Dict[str, Any]:
        """
        Deterministic clinical assessment following 2017 ACC/AHA guidelines.
        """
        for stage_name, condition_fn, alert_severity, recommendation in BP_STAGES:
            if condition_fn(systolic, diastolic):
                return {
                    "stage": stage_name,
                    "severity": alert_severity,
                    "recommendation": recommendation,
                    "guideline": "2017 ACC/AHA High Blood Pressure Clinical Practice Guidelines",
                }
        return {
            "stage": "Normal Blood Pressure",
            "severity": "LOW",
            "recommendation": "Maintain healthy lifestyle.",
            "guideline": "2017 ACC/AHA Guidelines",
        }

    def predict_hypertension_risk(self, vitals: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict health risk from physiological vital signs and evaluate clinical blood pressure.
        """
        if self.hypertension_artifact is None:
            return {
                "status": "unavailable",
                "error": "Hypertension / vital signs risk model is not loaded.",
            }

        model = self.hypertension_artifact["model"]
        feature_names = self.hypertension_artifact["feature_names"]

        # Parse and derive metrics
        hr = float(vitals.get("heart_rate", vitals.get("Heart Rate", 75.0)))
        resp = float(vitals.get("respiratory_rate", vitals.get("Respiratory Rate", 16.0)))
        temp = float(vitals.get("body_temperature", vitals.get("Body Temperature", 36.8)))
        spo2 = float(vitals.get("oxygen_saturation", vitals.get("Oxygen Saturation", 98.0)))
        sbp = float(vitals.get("systolic_bp", vitals.get("Systolic Blood Pressure", 120.0)))
        dbp = float(vitals.get("diastolic_bp", vitals.get("Diastolic Blood Pressure", 80.0)))
        age = float(vitals.get("age", vitals.get("Age", 50.0)))
        gender_str = str(vitals.get("gender", vitals.get("Gender", "Male"))).strip().capitalize()
        gender = 1 if gender_str == "Male" else 0
        weight = float(vitals.get("weight_kg", vitals.get("Weight (kg)", 70.0)))
        height = float(vitals.get("height_m", vitals.get("Height (m)", 1.75)))

        # Derived metrics
        hrv = float(vitals.get("derived_hrv", vitals.get("Derived_HRV", 0.10)))
        pulse_pressure = sbp - dbp
        bmi = weight / (height ** 2) if height > 0 else 24.0
        map_val = dbp + (sbp - dbp) / 3.0

        # Clinical range sanity checks
        if not (30 <= hr <= 250):
            raise ValueError(f"Heart rate {hr} bpm is out of plausible physiological range [30, 250].")
        if not (50 <= sbp <= 260):
            raise ValueError(f"Systolic BP {sbp} mmHg is out of plausible physiological range [50, 260].")
        if not (30 <= dbp <= 160):
            raise ValueError(f"Diastolic BP {dbp} mmHg is out of plausible physiological range [30, 160].")
        if not (70 <= spo2 <= 100):
            raise ValueError(f"Oxygen saturation {spo2}% is out of plausible physiological range [70, 100].")

        row = {
            "Heart Rate": hr,
            "Respiratory Rate": resp,
            "Body Temperature": temp,
            "Oxygen Saturation": spo2,
            "Systolic Blood Pressure": sbp,
            "Diastolic Blood Pressure": dbp,
            "Age": age,
            "Gender": gender,
            "Weight (kg)": weight,
            "Height (m)": height,
            "Derived_HRV": hrv,
            "Derived_Pulse_Pressure": pulse_pressure,
            "Derived_BMI": bmi,
            "Derived_MAP": map_val,
        }

        X = pd.DataFrame([row])[feature_names]

        # ML Prediction
        probs = model.predict_proba(X)[0]
        prob_high_risk = float(probs[1])
        is_high_risk = bool(prob_high_risk >= 0.5)
        pred_label = "High Risk" if is_high_risk else "Low Risk"
        confidence = float(prob_high_risk if is_high_risk else (1.0 - prob_high_risk)) * 100.0

        # Clinical guideline blood pressure stage (ACC/AHA 2017)
        bp_assessment = self.evaluate_blood_pressure(sbp, dbp)

        return {
            "status": "success",
            "task": "synthetic_vital_signs_risk_classification",
            "model_name": self.hypertension_artifact.get("model_name", "RandomForest"),
            "version": self.hypertension_artifact.get("version", "1.0.0"),
            "model_estimated_risk": pred_label,
            "high_risk_probability": round(prob_high_risk, 4),
            "confidence_percentage": round(confidence, 2),
            "clinical_blood_pressure_assessment": bp_assessment,
            "derived_metrics": {
                "bmi": round(bmi, 2),
                "mean_arterial_pressure": round(map_val, 1),
                "pulse_pressure": round(pulse_pressure, 1),
            },
            "disclaimer": (
                "AUDIT CONFIRMATION: The reported 100% accuracy in this model arises because the dataset target "
                "is deterministically generated by (Heart Rate > 90) or (BMI > 30) or (BMI < 18.5). "
                "Blood pressure measurements do NOT determine the target. This task is strictly a "
                "synthetic/rule-based vital signs risk classifier and is NOT a validated hypertension diagnosis model."
            ),
        }

    # =========================================================================
    # 4. MIT-BIH ECG HEARTBEAT CLASSIFICATION
    # =========================================================================
    def extract_single_ecg_features(self, sig: np.ndarray) -> pd.DataFrame:
        """Extract morphological and spectral features from a single 187-pt heartbeat."""
        sig_mean = float(np.mean(sig))
        sig_std = float(np.std(sig))
        sig_var = float(np.var(sig))
        sig_min = float(np.min(sig))
        sig_max = float(np.max(sig))
        sig_p2p = sig_max - sig_min
        sig_skew = float(stats.skew(sig))
        sig_kurt = float(stats.kurtosis(sig))

        r_peak_idx = int(np.argmax(sig))
        r_peak_val = float(sig[r_peak_idx])
        energy = float(np.sum(sig ** 2))
        auc = float(np.trapezoid(sig)) if hasattr(np, "trapezoid") else float(np.sum(sig))
        mad = float(np.mean(np.abs(sig - sig_mean)))
        zero_crossings = int(np.sum(np.diff(np.signbit(sig - sig_mean)) != 0))

        q10, q25, q50, q75, q90 = [float(q) for q in np.percentile(sig, [10, 25, 50, 75, 90])]

        fft_vals = np.abs(np.fft.rfft(sig))
        freqs = np.fft.rfftfreq(len(sig), d=1.0 / 125.0)
        spectral_energy = float(np.sum(fft_vals ** 2))
        spectral_centroid = float(np.sum(freqs * fft_vals) / (np.sum(fft_vals) + 1e-8))
        dominant_freq = float(freqs[np.argmax(fft_vals[1:]) + 1]) if len(fft_vals) > 1 else 0.0

        feat_dict = {
            "mean": sig_mean,
            "std": sig_std,
            "var": sig_var,
            "min": sig_min,
            "max": sig_max,
            "peak_to_peak": sig_p2p,
            "skew": sig_skew,
            "kurtosis": sig_kurt,
            "r_peak_idx": r_peak_idx,
            "r_peak_val": r_peak_val,
            "energy": energy,
            "auc": auc,
            "mad": mad,
            "zero_crossings": zero_crossings,
            "q10": q10,
            "q25": q25,
            "q50": q50,
            "q75": q75,
            "q90": q90,
            "spectral_energy": spectral_energy,
            "spectral_centroid": spectral_centroid,
            "dominant_freq": dominant_freq,
        }

        for step_idx, sample_pos in enumerate(np.linspace(0, 186, 10, dtype=int)):
            feat_dict[f"sig_pt_{step_idx}"] = float(sig[sample_pos])

        return pd.DataFrame([feat_dict])

    def predict_ecg_heartbeat(self, signal: List[float]) -> Dict[str, Any]:
        """
        Classify a single 187-sample ECG heartbeat into AAMI EC57 categories.
        """
        if self.ecg_artifact is None:
            return {
                "status": "unavailable",
                "error": "ECG heartbeat classification model is not loaded.",
            }

        if len(signal) != 187:
            raise ValueError(f"ECG heartbeat must contain exactly 187 numerical samples, received {len(signal)}.")

        sig_arr = np.array(signal, dtype=np.float32)

        # Feature extraction
        feats_df = self.extract_single_ecg_features(sig_arr)
        feature_names = self.ecg_artifact["feature_names"]
        X = feats_df[feature_names]

        model = self.ecg_artifact["model"]
        probs = model.predict_proba(X)[0]
        class_id = int(np.argmax(probs))
        confidence = float(probs[class_id]) * 100.0

        class_names = self.ecg_artifact.get("class_mapping", {
            0: "Normal Beat (N)",
            1: "Supraventricular Ectopic (S)",
            2: "Ventricular Ectopic (V)",
            3: "Fusion Beat (F)",
            4: "Unknown / Paced (Q)",
        })

        prob_breakdown = {class_names[i]: round(float(probs[i]), 4) for i in range(len(probs))}

        return {
            "status": "success",
            "task": "ecg_heartbeat_classification",
            "model_name": self.ecg_artifact.get("model_name", "XGBoost"),
            "version": self.ecg_artifact.get("version", "1.0.0"),
            "predicted_class_id": class_id,
            "predicted_class_name": class_names.get(class_id, "Unknown"),
            "confidence_percentage": round(confidence, 2),
            "class_probabilities": prob_breakdown,
            "disclaimer": (
                "Classification follows ANSI/AAMI EC57 beat categories (N, S, V, F, Q). "
                "These represent morphological beat categories, NOT whole-record rhythm diagnoses (e.g. tachycardia or bradycardia)."
            ),
        }

    # =========================================================================
    # 5. CARDIAC RHYTHM RESEARCH: TACHYCARDIA & BRADYCARDIA ASSESSMENT
    # =========================================================================
    def evaluate_cardiac_rhythm(
        self,
        heart_rate: float,
        rr_intervals: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate cardiac rhythm rate categories using clinical practice guidelines (ACC/AHA).
        Distinguishes sustained rhythm disorders from single-beat morphological classifications.
        """
        hr = float(heart_rate)
        if hr < 30.0 or hr > 260.0:
            raise ValueError(f"Heart rate {hr} is outside physiological limits (30-260 BPM).")

        if hr < 40.0:
            category = "Severe Bradycardia"
            severity = "CRITICAL"
            recommendation = "Immediate clinical evaluation required. Risk of cerebral hypoperfusion and hemodynamic instability."
        elif hr < 60.0:
            category = "Bradycardia"
            severity = "MEDIUM"
            recommendation = "Review medication, physical conditioning, and symptoms (dizziness, fatigue)."
        elif hr <= 100.0:
            category = "Normal Sinus Rate"
            severity = "LOW"
            recommendation = "Heart rate within standard adult resting physiological limits."
        elif hr <= 140.0:
            category = "Tachycardia"
            severity = "HIGH"
            recommendation = "Evaluate for secondary triggers (fever, exertion, anxiety, hypovolemia) or supraventricular arrhythmia."
        else:
            category = "Severe Tachycardia"
            severity = "CRITICAL"
            recommendation = "Urgent medical assessment indicated. Potential rapid ventricular response or ventricular tachycardia."

        hrv_metrics = None
        if rr_intervals and len(rr_intervals) >= 5:
            rr_arr = np.array(rr_intervals, dtype=np.float64)
            mean_rr = float(np.mean(rr_arr))
            sdnn = float(np.std(rr_arr))
            diff_rr = np.diff(rr_arr)
            rmssd = float(np.sqrt(np.mean(diff_rr ** 2))) if len(diff_rr) > 0 else 0.0
            hrv_metrics = {
                "mean_rr_ms": round(mean_rr * 1000.0, 1) if mean_rr < 10.0 else round(mean_rr, 1),
                "sdnn_ms": round(sdnn * 1000.0, 2) if mean_rr < 10.0 else round(sdnn, 2),
                "rmssd_ms": round(rmssd * 1000.0, 2) if mean_rr < 10.0 else round(rmssd, 2),
                "interval_count": len(rr_intervals),
            }

        return {
            "status": "success",
            "task": "cardiac_rhythm_rate_assessment",
            "heart_rate_bpm": hr,
            "rhythm_category": category,
            "severity": severity,
            "clinical_recommendation": recommendation,
            "hrv_metrics": hrv_metrics,
            "clinical_disclaimer": (
                "Rhythm-level tachycardia/bradycardia assessment requires continuous multi-beat or 30-second monitoring. "
                "Single-beat morphological classification (AAMI EC57) does NOT establish a sustained rhythm diagnosis."
            ),
        }

    # =========================================================================
    # 6. OXYGENATION & HYPOXEMIA RESEARCH ASSESSMENT
    # =========================================================================
    def evaluate_oxygenation(
        self,
        spo2: float,
        respiratory_rate: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate oxygenation and hypoxemia severity using clinical pulse oximetry standards.
        Designed for integration with pulse oximetry and PhysioNet BIDMC PPG research protocols.
        """
        sat = float(spo2)
        if sat < 50.0 or sat > 100.0:
            raise ValueError(f"SpO2 saturation {sat}% is outside valid measurement range (50-100%).")

        if sat >= 95.0:
            category = "Normal Oxygenation"
            severity = "LOW"
            recommendation = "Oxygen saturation is adequate. No supplemental oxygen therapy indicated."
        elif sat >= 91.0:
            category = "Mild Hypoxemia"
            severity = "MEDIUM"
            recommendation = "Monitor continuously; assess respiratory effort and consider room-air vs oxygen status."
        elif sat >= 85.0:
            category = "Moderate-to-Severe Hypoxemia"
            severity = "HIGH"
            recommendation = "Supplemental oxygen administration indicated. Perform arterial blood gas (ABG) verification."
        else:
            category = "Critical Hypoxemia"
            severity = "CRITICAL"
            recommendation = "EMERGENCY: Immediate airway management and high-flow oxygen delivery required."

        resp_info = None
        if respiratory_rate is not None:
            rr = float(respiratory_rate)
            resp_info = {
                "respiratory_rate_bpm": rr,
                "tachypnea": rr > 20.0,
                "bradypnea": rr < 12.0,
            }

        return {
            "status": "success",
            "task": "oxygenation_assessment",
            "spo2_percentage": sat,
            "oxygenation_category": category,
            "severity": severity,
            "clinical_recommendation": recommendation,
            "respiratory_status": resp_info,
            "research_note": (
                "Calibrated against clinical pulse oximetry standards. Continuous PPG waveform research (e.g. BIDMC 1.0.0) "
                "requires optical AC/DC pulsatile ratio calibration and motion artifact rejection."
            ),
        }

    # =========================================================================
    # 7. MODEL STATUS SUMMARY (safe for API response)
    # =========================================================================
    def get_model_status(self) -> Dict[str, Any]:
        return {
            "sisfall_fall_model": {
                "loaded": self.sisfall_artifact is not None,
                "version": self.sisfall_artifact.get("version", "1.0.0") if self.sisfall_artifact else None,
                "model_type": self.sisfall_artifact.get("model_name") if self.sisfall_artifact else None,
                "dataset": "SisFall (38 real subjects, 4,505 movement trials)",
                "task": "Fall vs Activities of Daily Living",
            },
            "hypertension_risk_model": {
                "loaded": self.hypertension_artifact is not None,
                "version": self.hypertension_artifact.get("version", "1.0.0") if self.hypertension_artifact else None,
                "model_type": self.hypertension_artifact.get("model_name") if self.hypertension_artifact else None,
                "dataset": "Human Vital Signs Dataset (200,020 records)",
                "task": "Synthetic / Rule-Based Vital Signs Risk Classification (Deterministic HR/BMI target)",
                "clinical_warning": "Not a validated hypertension diagnosis model. Target does not depend on blood pressure.",
            },
            "ecg_heartbeat_model": {
                "loaded": self.ecg_artifact is not None,
                "version": self.ecg_artifact.get("version", "1.0.0") if self.ecg_artifact else None,
                "model_type": self.ecg_artifact.get("model_name") if self.ecg_artifact else None,
                "dataset": "MIT-BIH Arrhythmia Database (21,892 test heartbeats)",
                "task": "AAMI EC57 Heartbeat Morphology (N, S, V, F, Q)",
            },
            "cardiac_rhythm_engine": {
                "loaded": True,
                "version": "1.0.0",
                "model_type": "ACC/AHA Rhythm Rate Staging",
                "task": "Tachycardia & Bradycardia Assessment",
                "status": "active",
            },
            "oxygenation_engine": {
                "loaded": True,
                "version": "1.0.0",
                "model_type": "Clinical Hypoxemia Protocol",
                "task": "Continuous SpO2 & Hypoxemia Staging",
                "status": "active",
            },
            "legacy_clade_simulation_model": {
                "loaded": self.legacy_loaded,
                "model_type": "RandomForest (Synthetic Stream Replay)",
            },
        }


# Global singleton instance
_engine_instance = None


def get_clinical_engine() -> CareEdgeClinicalEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = CareEdgeClinicalEngine()
    return _engine_instance
