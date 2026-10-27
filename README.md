# CareEdge: Multi-Condition Health Monitoring Using Machine Learning

[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.143-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.63-FF4B4B.svg)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/pytest-19%20passed-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/License-Academic%20Research-lightgrey.svg)]()

CareEdge is an advanced clinical AI research prototype for multimodal physiological monitoring, wearable kinematic fall detection, ECG heartbeat morphology classification, cardiac rhythm analysis, and clinical triage.

---

## 1. System Architecture

```text
[Wearable Sensors & Physiological Telemetry]
        │
        ├── SisFall 3-Axis Accelerometer & Gyroscope (200 Hz)
        ├── MIT-BIH Standardized ECG Heartbeat Lead II (125 Hz)
        ├── Continuous Physiological Vitals (HR, BP, SpO2, Temp, BMI)
        └── 50 Hz Windowed Patient Sensor Replay Stream
        │
        ▼
[CareEdge Clinical & CLADE Inference Engines]
        │
        ├── SisFall Random Forest Classifier (99.87% Accuracy, 100% Fall Recall)
        ├── MIT-BIH XGBoost Multiclass Classifier (96.21% Test Accuracy across 5 AAMI classes)
        ├── Synthetic Vital Signs Risk Classifier (Brier Score: 0.0015)
        ├── ACC/AHA 2017 Blood Pressure Clinical Staging Engine
        ├── Cardiac Rhythm Rate Engine (Severe Bradycardia to Severe Tachycardia)
        ├── Oxygenation & Hypoxemia Staging Protocol (<85% to ≥95% SpO2)
        └── CLADE Multistage Early Warning & Unified Triage Engine
        │
        ▼
[FastAPI REST API Service (:8000)] ────► [Streamlit Interactive Dashboard (:8501)]
```

---

## 2. Verified Clinical Models & Performance

| Module | Dataset & Held-Out Partition | Architecture | Key Test Metrics | Clinical Task |
| :--- | :--- | :--- | :---: | :--- |
| **Fall Detection** | SisFall (38 subjects; 7 unseen test subjects: 793 trials) | Random Forest | **99.87% Accuracy**<br/>**100% Fall Recall** (0 missed falls)<br/>0.20% False Positive Rate | Distinguishes falls from ADLs. Scaler fit strictly on training subjects. Zero subject or trial leakage. |
| **ECG Heartbeat** | MIT-BIH (87,554 train; 21,892 untouched test beats) | XGBoost Multiclass | **96.21% Accuracy**<br/>**90.79% Macro Precision**<br/>**81.82% Macro F1** (AUC: 0.9789) | Classifies 5 ANSI/AAMI EC57 beat classes (`N`, `S`, `V`, `F`, `Q`). |
| **Vital Signs Risk** | Human Vitals 2024 (140,014 train, 30,003 val, 30,003 test) | Calibrated Random Forest | **100.00% Accuracy**<br/>Brier Score: 0.0015 | Evaluates risk benchmark. *Note: Target is deterministically derived from HR & BMI; decoupled from BP.* |
| **Blood Pressure** | ACC/AHA 2017 Guidelines | Clinical Rules Engine | Deterministic Staging | Staging across Normal, Elevated, Stage 1 HTN, Stage 2 HTN, and Crisis. |
| **Cardiac Rhythm** | ACC/AHA Rate Staging | Continuous Rhythm Engine | Deterministic Rate Rules | Evaluates sustained heart rate & R-R intervals (Severe Bradycardia to Severe Tachycardia). |
| **Oxygenation** | Clinical Pulse Oximetry Standard | Hypoxemia Protocol | Deterministic Staging | Staging across Normal (≥95%), Mild (91-94%), Mod-Severe (85-90%), Critical (<85%). |

---

## 3. Quickstart & Execution Commands

### Prerequisites
- Python 3.11+ (tested on Python 3.14.5, Windows 11 / Linux)
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### Running the Services

All operations are unified under `manage.py`:

```bash
# 1. Run the complete automated test suite (19 test cases)
python manage.py test

# 2. Launch the FastAPI REST Prediction Backend (Port 8000)
python manage.py serve
# Swagger documentation available at: http://127.0.0.1:8000/docs

# 3. Launch the Streamlit Monitoring Dashboard (Port 8501)
python manage.py dashboard
# Dashboard available at: http://localhost:8501

# 4. Run the full data extraction, preprocessing, training & verification pipeline
python manage.py all
```

---

## 4. REST API Endpoint Reference

| Method | Endpoint | Description | Sample Request Payload |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | System health check | N/A |
| `GET` | `/models/status` | Registry status of all 6 clinical models | N/A |
| `POST` | `/predict/fall` | Evaluates SisFall kinematic movement features | `{"accel_mag_max": 36.5, "accel_y_mean": 18.0, "gyro_mag_max": 6.2}` |
| `POST` | `/predict/ecg-heartbeat` | Classifies 187-sample standardized ECG beat | `{"signal": [0.0, ..., 1.0, ..., 0.0]}` (187 points) |
| `POST` | `/predict/hypertension-risk`| Evaluates vital signs risk and ACC/AHA BP stage | `{"heart_rate": 75, "systolic_bp": 125, "diastolic_bp": 78, "weight_kg": 70, "height_m": 1.75}` |
| `POST` | `/predict/cardiac-rhythm` | Evaluates rhythm-level rate and HRV statistics | `{"heart_rate": 130.0, "rr_intervals": [0.46, 0.45, 0.47]}` |
| `POST` | `/predict/oxygenation` | Evaluates blood oxygenation and hypoxemia severity | `{"spo2": 88.0, "respiratory_rate": 22.0}` |
| `POST` | `/predict/unified` | Composite multi-modal evaluation and triage | `{"vitals": {...}, "ecg": {...}, "movement": {...}, "rhythm": {...}, "oxygenation": {...}}` |

---

## 5. Dashboard Navigation Modes

The Streamlit dashboard (`http://localhost:8501`) provides 3 operational views:
1. **🛰️ Real-Time Patient Stream (Simulation)**:
   - 50 Hz real-time replay simulation on 10 synthetic patients (`P001`–`P010`).
   - Dynamic telemetry graphs for heart rate, SpO2, blood pressure, temperature, and 3-axis accelerometer/gyroscope.
   - 4-phase early warning probability bars (`pre_fall`, `fall_transition`, `fall`, `post_fall`).
2. **🩺 Clinical AI Prediction Modules**:
   - Tab 1: Vital Signs Risk & ACC/AHA Blood Pressure Staging.
   - Tab 2: MIT-BIH ECG Heartbeat Morphology Classification (interactive 5-class beat selector & probability charts).
   - Tab 3: SisFall Wearable Movement & Fall Detection (trial presets & kinematic sliders).
   - Tab 4: Cardiac Rhythm Research (Tachycardia / Bradycardia & simulated R-R intervals).
   - Tab 5: Clinical Oxygenation & Hypoxemia Staging (SpO2 & respiratory status).
3. **📊 Model & Dataset Evaluation Status**:
   - Active Model Registry statuses and dataset provenance.
   - Held-Out Evaluation Metrics Summary Table.
   - Dataset access restrictions (e.g. MIMIC-IV-ED credentialing requirements, PhysioNet BIDMC waveform protocol).

---

## 6. Clinical & Legal Disclaimer

CareEdge is an academic and engineering research prototype developed for multi-condition physiological monitoring and decision support research.
- The models, risk scores, and clinical stagings generated by CareEdge do **not** constitute a definitive medical diagnosis, clinical prognosis, or prescription.
- It is not certified as a Software as a Medical Device (SaMD) by the FDA, CE, or CDSCO.
- In any actual medical emergency or life-threatening event, immediate professional emergency care must be sought.
