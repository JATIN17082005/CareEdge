import zipfile
import pandas as pd
import numpy as np

archive_path = r"C:\CareEdge\data\archive.zip"
with zipfile.ZipFile(archive_path) as z:
    with z.open("human_vital_signs_dataset_2024.csv") as f:
        df = pd.read_csv(f)

print("=" * 70)
print("HYPERTENSION / VITAL SIGNS DATASET ANALYSIS")
print("=" * 70)
print("Shape:", df.shape)
print("\nData Types:")
print(df.dtypes)

print("\nRisk Category breakdown:")
print(df["Risk Category"].value_counts(dropna=False, normalize=True))

print("\nMean feature values by Risk Category:")
numeric_cols = df.select_dtypes(include=[np.number]).columns.drop("Patient ID")
print(df.groupby("Risk Category")[numeric_cols].mean().T)

print("\nMin/Max feature values by Risk Category:")
for col in ["Systolic Blood Pressure", "Diastolic Blood Pressure", "Derived_MAP", "Derived_Pulse_Pressure", "Heart Rate", "Oxygen Saturation", "Body Temperature", "Age"]:
    print(f"\nFeature: {col}")
    print(df.groupby("Risk Category")[col].agg(["min", "max", "mean", "std"]))

# Check if there is an exact decision rule for Risk Category:
# E.g. Systolic BP >= 130 or Diastolic BP >= 80 or MAP or Age
print("\nChecking decision boundaries:")
print("Systolic BP distribution for Low Risk vs High Risk:")
print("Low Risk SBP range:", df[df["Risk Category"] == "Low Risk"]["Systolic Blood Pressure"].min(), "to", df[df["Risk Category"] == "Low Risk"]["Systolic Blood Pressure"].max())
print("High Risk SBP range:", df[df["Risk Category"] == "High Risk"]["Systolic Blood Pressure"].min(), "to", df[df["Risk Category"] == "High Risk"]["Systolic Blood Pressure"].max())

print("Low Risk DBP range:", df[df["Risk Category"] == "Low Risk"]["Diastolic Blood Pressure"].min(), "to", df[df["Risk Category"] == "Low Risk"]["Diastolic Blood Pressure"].max())
print("High Risk DBP range:", df[df["Risk Category"] == "High Risk"]["Diastolic Blood Pressure"].min(), "to", df[df["Risk Category"] == "High Risk"]["Diastolic Blood Pressure"].max())
