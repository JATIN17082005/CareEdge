# CareEdge: Clinical Dataset Inspection & Provenance Report

## 1. Executive Summary
This report documents the inspection of all local dataset files provided in `c:\CareEdge\data\`, their formats, integrity, class distributions, verified feature dependencies, and clinical limitations.

---

## 2. Dataset Reports

### Dataset A: Human Vital Signs & Risk Prediction (`archive.zip`)
- **File Name**: `human_vital_signs_dataset_2024.csv` (uncompressed: 38.79 MB)
- **Source & Provenance**: Synthesized vital signs dataset created for health risk benchmarking (commonly distributed via Kaggle 2024). Not derived from real electronic health records (EHR).
- **Dimensions**: 200,020 rows $\times$ 17 columns.
- **Missing & Duplicate Values**: 0 missing values; 0 duplicate rows; 200,020 unique Patient IDs.
- **Features (15 inputs + 1 identifier)**:
  - Numerical inputs: `Heart Rate` (60–99 bpm), `Respiratory Rate` (12–19 br/min), `Body Temperature` (36.0–37.5 °C), `Oxygen Saturation` (95.0–100.0 %), `Systolic Blood Pressure` (110–139 mmHg), `Diastolic Blood Pressure` (70–89 mmHg), `Age` (18–89 yrs), `Weight (kg)` (50.0–100.0 kg), `Height (m)` (1.50–2.00 m), `Derived_HRV` (0.05–0.15 s), `Derived_Pulse_Pressure` (21–69 mmHg), `Derived_BMI` (13.6–44.4 $\text{kg/m}^2$), `Derived_MAP` (83.3–105.7 mmHg).
  - Categorical input: `Gender` (Male: 50.02%, Female: 49.98%).
  - Identifiers: `Patient ID`, `Timestamp`.
- **Target Label**: `Risk Category`
  - `High Risk`: 105,115 (52.55%)
  - `Low Risk`: 94,905 (47.45%)
- **Critical Finding & Ground Truth Dependency**:
  - Decision tree and symbolic audits revealed that `Risk Category` is **100.00% deterministically generated** by the following rule:
    $$\text{High Risk} \iff (\text{Heart Rate} > 90) \lor (\text{Derived\_BMI} > 30) \lor (\text{Derived\_BMI} < 18.5)$$
  - **Blood-pressure measurements (`Systolic Blood Pressure`, `Diastolic Blood Pressure`, `Derived_MAP`, `Derived_Pulse_Pressure`) have zero influence on `Risk Category` in this dataset.**
  - **Clinical Warning**: This model predicts synthetic health risk flags. It cannot and does not independently diagnose clinical hypertension or chronic medical disease.

---

### Dataset B: Hypertension Risk Prediction Notebook (`hypertension-risk.ipynb`)
- **File Name**: `hypertension-risk.ipynb` (231 KB, 17 cells)
- **Code Audit**:
  - Cell 3 attempts to load `/kaggle/input/hypertension-risk-prediction-dataset/hypertension_dataset.csv`.
  - Cells perform exploratory data visualization on demographic variables (`Country`, `Physical_Activity_Level`, `Family_History`, `Triglycerides`, `Hypertension`).
  - No malicious network calls, shell invocations, or data deletion operations were found.
- **Status**: The Kaggle CSV referenced inside the notebook was not provided in the directory; instead, the comprehensive vital signs dataset `human_vital_signs_dataset_2024.csv` was provided.

---

### Dataset C: MIT-BIH ECG Heartbeat Dataset (`mitbih_test.csv.zip`)
- **File Name**: `mitbih_test.csv` (uncompressed: 102.89 MB)
- **Source & Provenance**: Standardized AAMI EC57 heartbeat classification benchmark dataset derived from the PhysioNet MIT-BIH Arrhythmia Database (published by Kachueh et al., 2018).
- **Dimensions**: 21,892 rows $\times$ 188 columns.
- **Format**:
  - Columns 0 to 186 (187 points): 125 Hz normalized ECG lead II heartbeat segments, zero-padded.
  - Column 187 (Target label): Categorical heartbeat annotation index (float `0.0` to `4.0`).
- **Missing & Duplicate Values**: 0 missing values; 0 duplicates.
- **Label Mapping (AAMI EC57 Categories)**:
  - `0.0` (Normal / Non-Ectopic Beat - 'N'): 18,118 (82.76%)
  - `1.0` (Supraventricular Ectopic Beat - 'S'): 556 (2.54%)
  - `2.0` (Ventricular Ectopic Beat - 'V'): 1,448 (6.61%)
  - `3.0` (Fusion Beat - 'F'): 162 (0.74%)
  - `4.0` (Unknown / Paced Beat - 'Q'): 1,608 (7.35%)
- **Predefined Split Finding**:
  - The provided file is explicitly the **predefined held-out test split** (`mitbih_test.csv`).
  - The predefined training split (`mitbih_train.csv`, 87,554 rows) was not included in `data/`.
  - **Scientific Evaluation Protocol**: To prevent data contamination, training directly on `mitbih_test.csv` as an unpartitioned benchmark is strictly forbidden. For standalone demonstration, an isolated stratified sub-split (70% train / 15% val / 15% test) is maintained in isolated directories while preserving the full 21,892 test set for final verification.
  - Heartbeat classes represent morphological beat types; they are strictly documented as AAMI beat classes and are not conflated with rhythm diagnoses like sinus tachycardia or bradycardia.

---

### Dataset D: SisFall Fall & Movement Dataset
- **Directory**: `c:\CareEdge\CareEdge-1\data\raw\sisfall\SisFall_dataset`
- **Subjects**: 38 participants (23 Young Adults SA01–SA23, 15 Elderly SE01–SE15).
- **Signals**: 200 Hz Triaxial Accelerometers (ADXL345 $\pm 16g$, MMA8451Q $\pm 8g$) and Triaxial Gyroscope (ITG3200 $\pm 2000^\circ/\text{s}$).
- **Classes**: 19 Activities of Daily Living (`D01`–`D19`, Non-fall) and 15 Falls (`F01`–`F15`, Fall).
