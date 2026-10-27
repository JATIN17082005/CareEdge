import os
import shutil
import zipfile
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT.parent / "data"

RAW_VITALS_DIR = PROJECT_ROOT / "data" / "raw" / "vitals"
RAW_MITBIH_DIR = PROJECT_ROOT / "data" / "raw" / "mitbih"
RAW_SISFALL_DIR = PROJECT_ROOT / "data" / "raw" / "sisfall"
MANIFEST_DIR = PROJECT_ROOT / "data" / "manifests"

for d in [RAW_VITALS_DIR, RAW_MITBIH_DIR, RAW_SISFALL_DIR, MANIFEST_DIR]:
    d.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("EXTRACTING AND VALIDATING LOCAL DATASETS")
print("=" * 70)

# 1. Vital signs (archive.zip)
archive_zip = DATA_DIR / "archive.zip"
if archive_zip.exists():
    print(f"Extracting {archive_zip.name} ({archive_zip.stat().st_size:,} bytes)...")
    with zipfile.ZipFile(archive_zip, 'r') as zf:
        corrupt = zf.testzip()
        if corrupt:
            raise RuntimeError(f"Corrupt file in archive.zip: {corrupt}")
        zf.extractall(RAW_VITALS_DIR)
    vitals_csv = RAW_VITALS_DIR / "human_vital_signs_dataset_2024.csv"
    if vitals_csv.exists():
        print(f" Extracted: {vitals_csv} ({vitals_csv.stat().st_size:,} bytes)")
else:
    print(f" Warning: {archive_zip} not found!")

# 2. MIT-BIH test (mitbih_test.csv.zip)
mitbih_zip = DATA_DIR / "mitbih_test.csv.zip"
if mitbih_zip.exists():
    print(f"\nExtracting {mitbih_zip.name} ({mitbih_zip.stat().st_size:,} bytes)...")
    with zipfile.ZipFile(mitbih_zip, 'r') as zf:
        corrupt = zf.testzip()
        if corrupt:
            raise RuntimeError(f"Corrupt file in mitbih_test.csv.zip: {corrupt}")
        zf.extractall(RAW_MITBIH_DIR)
    mitbih_csv = RAW_MITBIH_DIR / "mitbih_test.csv"
    if mitbih_csv.exists():
        print(f" Extracted: {mitbih_csv} ({mitbih_csv.stat().st_size:,} bytes)")
else:
    print(f" Warning: {mitbih_zip} not found!")

# 3. SisFall check
sisfall_dataset = RAW_SISFALL_DIR / "SisFall_dataset"
if sisfall_dataset.exists():
    subjects = [s.name for s in sisfall_dataset.iterdir() if s.is_dir()]
    print(f"\n SisFall verified: {len(subjects)} subjects found at {sisfall_dataset}")
else:
    # check if Downloads/SisFall.zip exists
    dl_zip = Path.home() / "Downloads" / "SisFall.zip"
    if dl_zip.exists():
        print(f"\nExtracting SisFall from {dl_zip}...")
        with zipfile.ZipFile(dl_zip) as z1:
            data = z1.read("SisFall_dataset.zip")
            import io
            with zipfile.ZipFile(io.BytesIO(data)) as z2:
                z2.extractall(RAW_SISFALL_DIR)
        print(" Extracted SisFall successfully.")

print("\n" + "=" * 70)
print("DATA EXTRACTION COMPLETE")
print("=" * 70)
