import sys
import time
from pathlib import Path
import requests

TARGET_PATH = Path(r"C:\CareEdge\CareEdge-1\data\raw\mitbih\mitbih_train.csv")
TARGET_PATH.parent.mkdir(parents=True, exist_ok=True)
URL = "https://huggingface.co/datasets/Zermatzor/heartbeat_data/resolve/main/mitbih_train.csv"

print(f"Downloading original mitbih_train.csv to {TARGET_PATH}...")
t0 = time.time()

# Resume support if partially downloaded
initial_bytes = TARGET_PATH.stat().st_size if TARGET_PATH.exists() else 0
headers = {"User-Agent": "Mozilla/5.0"}
if initial_bytes > 0:
    headers["Range"] = f"bytes={initial_bytes}-"
    print(f"Resuming download from byte {initial_bytes:,}...")

mode = "ab" if initial_bytes > 0 else "wb"
with requests.get(URL, headers=headers, stream=True, timeout=30) as r:
    r.raise_for_status()
    total_len = int(r.headers.get("content-length", 0)) + initial_bytes
    downloaded = initial_bytes
    with open(TARGET_PATH, mode) as f:
        for chunk in r.iter_content(chunk_size=1048576 * 2):  # 2MB chunks
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if time.time() - t0 > 10:
                    pct = (downloaded / total_len * 100) if total_len else 0
                    print(f"Downloaded {downloaded / 1048576:.1f} MB / {total_len / 1048576:.1f} MB ({pct:.1f}%)")
                    t0 = time.time()

print(f" Successfully downloaded mitbih_train.csv ({TARGET_PATH.stat().st_size:,} bytes)")
