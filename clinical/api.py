import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, field_validator
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

# Ensure clinical module is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from clinical_inference import get_clinical_engine, CareEdgeClinicalEngine

app = FastAPI(
    title="CareEdge Clinical AI API",
    description="REST API for Clinical Vital Signs Risk, MIT-BIH ECG Heartbeat Classification, and SisFall Fall Detection.",
    version="1.0.0",
)

# Enable CORS for Streamlit dashboard and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# PYDANTIC SCHEMAS
# =============================================================================

class VitalsPredictionRequest(BaseModel):
    heart_rate: float = Field(..., ge=30.0, le=250.0, description="Heart rate in beats per minute (30-250)")
    respiratory_rate: float = Field(16.0, ge=6.0, le=60.0, description="Respiratory rate in breaths/min (6-60)")
    body_temperature: float = Field(36.8, ge=30.0, le=45.0, description="Body temperature in Celsius (30.0-45.0)")
    oxygen_saturation: float = Field(98.0, ge=70.0, le=100.0, description="SpO2 percentage (70-100)")
    systolic_bp: float = Field(120.0, ge=50.0, le=260.0, description="Systolic Blood Pressure in mmHg (50-260)")
    diastolic_bp: float = Field(80.0, ge=30.0, le=160.0, description="Diastolic Blood Pressure in mmHg (30-160)")
    age: float = Field(50.0, ge=1.0, le=120.0, description="Patient age in years")
    gender: str = Field("Male", description="Patient gender ('Male' or 'Female')")
    weight_kg: float = Field(70.0, ge=20.0, le=300.0, description="Weight in kilograms (20-300)")
    height_m: float = Field(1.75, ge=0.5, le=2.5, description="Height in meters (0.5-2.5)")
    derived_hrv: Optional[float] = Field(0.10, ge=0.001, le=1.0, description="Heart Rate Variability in seconds")

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v: str) -> str:
        v_clean = v.strip().capitalize()
        if v_clean not in ["Male", "Female"]:
            raise ValueError("Gender must be 'Male' or 'Female'.")
        return v_clean


class ECGPredictionRequest(BaseModel):
    signal: List[float] = Field(
        ...,
        description="187 normalized ECG signal sample points (ANSI/AAMI EC57 standardized beat)",
    )

    @field_validator("signal")
    @classmethod
    def validate_signal_length(cls, v: List[float]) -> List[float]:
        if len(v) != 187:
            raise ValueError(f"ECG heartbeat signal must contain exactly 187 float points, received {len(v)}.")
        return v


class FallPredictionRequest(BaseModel):
    accel_mag_max: float = Field(..., description="Peak acceleration magnitude in m/s^2")
    accel_mag_min: Optional[float] = Field(9.8, description="Minimum acceleration magnitude in m/s^2")
    accel_mag_mean: Optional[float] = Field(9.8, description="Mean acceleration magnitude in m/s^2")
    accel_y_mean: Optional[float] = Field(0.0, description="Mean vertical acceleration in m/s^2")
    accel_y_std: Optional[float] = Field(1.0, description="Standard deviation of vertical acceleration")
    gyro_mag_max: Optional[float] = Field(1.0, description="Peak angular velocity magnitude in rad/s")
    accel_jerk_max: Optional[float] = Field(5.0, description="Maximum sample-to-sample jerk in m/s^2")


class CardiacRhythmRequest(BaseModel):
    heart_rate: float = Field(..., ge=30.0, le=260.0, description="Average heart rate in BPM (30-260)")
    rr_intervals: Optional[List[float]] = Field(None, description="Optional sequence of consecutive R-R intervals in seconds")


class OxygenationRequest(BaseModel):
    spo2: float = Field(..., ge=50.0, le=100.0, description="SpO2 percentage (50-100)")
    respiratory_rate: Optional[float] = Field(None, ge=4.0, le=70.0, description="Optional respiratory rate in breaths/min")


class UnifiedPredictionRequest(BaseModel):
    vitals: Optional[VitalsPredictionRequest] = None
    ecg: Optional[ECGPredictionRequest] = None
    movement: Optional[FallPredictionRequest] = None
    rhythm: Optional[CardiacRhythmRequest] = None
    oxygenation: Optional[OxygenationRequest] = None


# =============================================================================
# API ROUTES
# =============================================================================

@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint confirming API availability."""
    return {
        "status": "healthy",
        "service": "CareEdge Clinical AI Prediction Service",
        "version": "1.0.0",
    }


@app.get("/models/status", tags=["System"])
def get_models_status():
    """Return status, versions, and dataset provenance for all loaded models."""
    engine = get_clinical_engine()
    return {
        "status": "success",
        "models": engine.get_model_status(),
    }


@app.post("/predict/hypertension-risk", tags=["Clinical Predictions"])
def predict_hypertension_risk(request: VitalsPredictionRequest):
    """
    Predict vital signs health risk and evaluate clinical blood pressure staging (ACC/AHA 2017).
    """
    engine = get_clinical_engine()
    try:
        result = engine.predict_hypertension_risk(request.model_dump())
        if result.get("status") == "unavailable":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result.get("error", "Model unavailable"),
            )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Prediction error: {str(e)}")


@app.post("/predict/ecg-heartbeat", tags=["Clinical Predictions"])
def predict_ecg_heartbeat(request: ECGPredictionRequest):
    """
    Classify a 187-sample ECG heartbeat into AAMI EC57 classes (N, S, V, F, Q).
    """
    engine = get_clinical_engine()
    try:
        result = engine.predict_ecg_heartbeat(request.signal)
        if result.get("status") == "unavailable":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result.get("error", "Model unavailable"),
            )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"ECG error: {str(e)}")


@app.post("/predict/fall", tags=["Clinical Predictions"])
def predict_fall(request: FallPredictionRequest):
    """
    Detect fall vs normal activity of daily living using the SisFall Random Forest model.
    """
    engine = get_clinical_engine()
    try:
        result = engine.predict_fall_sisfall(request.model_dump())
        if result.get("status") == "unavailable":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result.get("error", "Model unavailable"),
            )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Fall detection error: {str(e)}")


@app.post("/predict/cardiac-rhythm", tags=["Clinical Predictions"])
def predict_cardiac_rhythm(request: CardiacRhythmRequest):
    """
    Evaluate cardiac rhythm rate categories (Tachycardia / Bradycardia) using ACC/AHA clinical guidelines.
    """
    engine = get_clinical_engine()
    try:
        return engine.evaluate_cardiac_rhythm(request.heart_rate, request.rr_intervals)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Rhythm evaluation error: {str(e)}")


@app.post("/predict/oxygenation", tags=["Clinical Predictions"])
def predict_oxygenation(request: OxygenationRequest):
    """
    Evaluate oxygenation status and hypoxemia severity using clinical pulse oximetry standards.
    """
    engine = get_clinical_engine()
    try:
        return engine.evaluate_oxygenation(request.spo2, request.respiratory_rate)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Oxygenation evaluation error: {str(e)}")


@app.post("/predict/unified", tags=["Clinical Predictions"])
def predict_unified(request: UnifiedPredictionRequest):
    """
    Unified evaluation of vitals, ECG, movement, cardiac rhythm, and oxygenation features with integrated clinical triage.
    """
    engine = get_clinical_engine()
    response = {
        "status": "success",
        "vitals_assessment": None,
        "ecg_assessment": None,
        "fall_assessment": None,
        "rhythm_assessment": None,
        "oxygenation_assessment": None,
        "triage_summary": {
            "overall_severity": "NORMAL",
            "active_alerts": [],
        },
    }

    if request.vitals:
        v_res = engine.predict_hypertension_risk(request.vitals.model_dump())
        response["vitals_assessment"] = v_res
        bp_sev = v_res.get("clinical_blood_pressure_assessment", {}).get("severity", "LOW")
        if bp_sev in ["CRITICAL", "HIGH"]:
            response["triage_summary"]["overall_severity"] = bp_sev
            response["triage_summary"]["active_alerts"].append(f"Blood Pressure Alert: {v_res['clinical_blood_pressure_assessment']['stage']}")

    if request.ecg:
        e_res = engine.predict_ecg_heartbeat(request.ecg.signal)
        response["ecg_assessment"] = e_res
        if e_res.get("predicted_class_id") in [1, 2, 3]:
            response["triage_summary"]["active_alerts"].append(f"ECG Arrhythmia Alert: {e_res['predicted_class_name']}")
            if response["triage_summary"]["overall_severity"] != "CRITICAL":
                response["triage_summary"]["overall_severity"] = "HIGH"

    if request.movement:
        f_res = engine.predict_fall_sisfall(request.movement.model_dump())
        response["fall_assessment"] = f_res
        if f_res.get("is_fall"):
            response["triage_summary"]["overall_severity"] = "CRITICAL"
            response["triage_summary"]["active_alerts"].append("FALL DETECTED: Immediate attention required.")

    if request.rhythm:
        r_res = engine.evaluate_cardiac_rhythm(request.rhythm.heart_rate, request.rhythm.rr_intervals)
        response["rhythm_assessment"] = r_res
        r_sev = r_res.get("severity", "LOW")
        if r_sev in ["CRITICAL", "HIGH"]:
            if response["triage_summary"]["overall_severity"] != "CRITICAL" or r_sev == "CRITICAL":
                response["triage_summary"]["overall_severity"] = r_sev
            response["triage_summary"]["active_alerts"].append(f"Cardiac Rhythm Alert: {r_res['rhythm_category']}")

    if request.oxygenation:
        o_res = engine.evaluate_oxygenation(request.oxygenation.spo2, request.oxygenation.respiratory_rate)
        response["oxygenation_assessment"] = o_res
        o_sev = o_res.get("severity", "LOW")
        if o_sev in ["CRITICAL", "HIGH"]:
            if response["triage_summary"]["overall_severity"] != "CRITICAL" or o_sev == "CRITICAL":
                response["triage_summary"]["overall_severity"] = o_sev
            response["triage_summary"]["active_alerts"].append(f"Oxygenation Alert: {o_res['oxygenation_category']}")

    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
