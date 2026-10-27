# CareEdge: Synthetic vs Real Dataset Distribution Comparison

## 1. Overview
This report compares the statistical distributions of the CareEdge simulated/synthetic dataset (`careedge_training_data.csv`) against verified real/benchmark clinical distributions (`human_vital_signs_dataset_2024.csv` and SisFall).

**Clinical Integrity Notice**: Synthetic sensor streams are algorithmically generated for prototype testing and must never be described as medically verified or used as ground-truth evidence of clinical efficacy.

## 2. Physiological Feature Comparisons

| Feature | Unit | Source | Mean ± Std | Range [Min, Max] | 25% | Median | 75% | KS Stat (p-val) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **heart_rate** | bpm | Synthetic | 83.71 ± 19.92 | [61.0, 140.0] | 71.0 | 77.5 | 86.0 | - |
| | | Real | 79.53 ± 11.55 | [60.0, 99.0] | 70.0 | 80.0 | 90.0 | **0.1667** (0.0e+00) |
| **spo2** | % | Synthetic | 96.15 ± 3.62 | [85.0, 99.7] | 96.5 | 97.4 | 98.2 | - |
| | | Real | 97.50 ± 1.44 | [95.0, 100.0] | 96.3 | 97.5 | 98.8 | **0.1667** (0.0e+00) |
| **temperature** | °C | Synthetic | 37.10 ± 0.78 | [36.4, 39.5] | 36.7 | 36.8 | 37.0 | - |
| | | Real | 36.75 ± 0.43 | [36.0, 37.5] | 36.4 | 36.7 | 37.1 | **0.3063** (0.0e+00) |
| **systolic_bp** | mmHg | Synthetic | 132.67 ± 16.49 | [111.0, 180.0] | 121.0 | 129.0 | 137.0 | - |
| | | Real | 124.44 ± 8.66 | [110.0, 139.0] | 117.0 | 124.0 | 132.0 | **0.1924** (0.0e+00) |
| **diastolic_bp** | mmHg | Synthetic | 84.74 ± 9.07 | [72.0, 110.0] | 78.0 | 82.0 | 87.0 | - |
| | | Real | 79.50 ± 5.76 | [70.0, 89.0] | 75.0 | 79.0 | 84.0 | **0.2231** (0.0e+00) |

## 3. Movement & IMU Signals Comparison (CareEdge Synthetic vs SisFall)

| Feature | Unit | Source | Mean ± Std | Range [Min, Max] | KS Stat |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **accel_mag** | m/s² | Synthetic | 9.92 ± 2.90 | [0.50, 34.99] | - |
| | | SisFall Real | 10.02 ± 0.58 | [8.38, 16.29] | **0.4592** |
| **gyro_mag** | rad/s | Synthetic | 0.23 ± 1.04 | [0.00, 11.95] | - |
| | | SisFall Real | 0.37 ± 0.24 | [0.10, 3.48] | **0.9097** |

## 4. Key Distribution Differences
1. **Heart Rate**: Synthetic data features simulated tachycardia episodes (forcing HR > 110-140 bpm for 20% of samples), whereas the real vital signs distribution is centered at 79.5 bpm with max 99 bpm.
2. **Blood Pressure**: Synthetic data forced uniform SBP values for hypertension events (up to 160-180 mmHg), while the real vital signs dataset is constrained between 110 and 139 mmHg.
3. **Movement Signals**: The synthetic Gazebo IMU simulation shows discrete, abrupt kinematic transitions, whereas SisFall signals exhibit natural bio-mechanical continuous damping and sub-second impact spikes.

## 5. Label Distribution Analysis
- **Synthetic Dataset**: Perfectly balanced 6 classes (2,500 samples each: normal, tachycardia, fever, hypoxia, hypertension, fall) — artificial symmetry typical of toy generators.
- **Real Vital Signs Dataset**: Realistic class distribution (52.55% High Risk, 47.45% Low Risk).
- **MIT-BIH ECG Dataset**: Severe real-world class imbalance (82.76% Normal, 2.54% Supraventricular, 6.61% Ventricular, 0.74% Fusion, 7.35% Unknown/Paced).
- **SisFall Dataset**: 60.1% Activities of Daily Living vs 39.9% Fall trials across 38 subjects.

## 6. Unsupported & Unmatched Features
- Features in Real Vitals not in Synthetic stream: `Derived_BMI`, `Derived_HRV`, `Derived_Pulse_Pressure`, `Derived_MAP`, `Height`, `Weight`, `Age`.
- Features in Synthetic stream not in Vitals: `accel_x`, `accel_y`, `accel_z`, `gyro_x`, `gyro_y`, `gyro_z`, `activity`, `fall_detected`.
- Features in MIT-BIH ECG: 187-sample time-series ECG voltage waveforms.