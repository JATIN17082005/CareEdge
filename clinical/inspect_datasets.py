import json
import zipfile
import io
import pandas as pd
import numpy as np

print("=" * 70)
print("INSPECTING HYPERTENSION NOTEBOOK")
print("=" * 70)

nb_path = r"C:\CareEdge\data\hypertension-risk.ipynb"
with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

print(f"Total cells: {len(nb['cells'])}")
for idx, cell in enumerate(nb["cells"]):
    src = "".join(cell.get("source", []))
    if cell.get("cell_type") == "markdown" and any(k in src.lower() for k in ["dataset", "hypertension", "source", "kaggle", "intro"]):
        print(f"\n--- Markdown Cell {idx} ---")
        print(src[:400])
    elif cell.get("cell_type") == "code":
        # Look for read_csv or data loading
        if "read_csv" in src or "pd." in src or "target" in src.lower() or "risk" in src.lower():
            print(f"\n--- Code Cell {idx} ---")
            print(src[:400])

print("\n" + "=" * 70)
print("INSPECTING ARCHIVE.ZIP (HUMAN VITAL SIGNS DATASET)")
print("=" * 70)

archive_path = r"C:\CareEdge\data\archive.zip"
with zipfile.ZipFile(archive_path) as z:
    for name in z.namelist():
        print(f"File inside archive: {name}")
        with z.open(name) as f:
            df = pd.read_csv(f, nrows=10)
            print(f"Columns ({len(df.columns)}):", list(df.columns))
            print("\nSample rows:")
            print(df.head(3))

print("\n" + "=" * 70)
print("PRINTING ALL CELLS OF HYPERTENSION NOTEBOOK")
print("=" * 70)
for idx, cell in enumerate(nb["cells"]):
    print(f"\n--- Cell {idx} ({cell.get('cell_type')}) ---")
    print("".join(cell.get("source", [])))

print("\n" + "=" * 70)
print("ANALYZING HUMAN VITAL SIGNS DATASET (archive.zip)")
print("=" * 70)
with zipfile.ZipFile(archive_path) as z:
    with z.open("human_vital_signs_dataset_2024.csv") as f:
        vitals_df = pd.read_csv(f)
        print("Shape:", vitals_df.shape)
        print("Missing values:\n", vitals_df.isnull().sum())
        print("Duplicate rows:", vitals_df.duplicated().sum())
        print("Patient ID unique:", vitals_df["Patient ID"].nunique())
        print("Risk Category value counts:\n", vitals_df["Risk Category"].value_counts(dropna=False))
        print("Summary stats:\n", vitals_df.describe().T[["mean", "std", "min", "50%", "max"]])

print("\n" + "=" * 70)
print("ANALYZING MIT-BIH TEST DATASET (mitbih_test.csv.zip)")
print("=" * 70)
mitbih_path = r"C:\CareEdge\data\mitbih_test.csv.zip"
with zipfile.ZipFile(mitbih_path) as z:
    with z.open("mitbih_test.csv") as f:
        mit_df = pd.read_csv(f, header=None)
        print("Shape:", mit_df.shape)
        print("Missing values in entire df:", mit_df.isnull().sum().sum())
        print("Duplicate rows:", mit_df.duplicated().sum())
        print("Label column (187) value counts:\n", mit_df.iloc[:, -1].value_counts().sort_index())

