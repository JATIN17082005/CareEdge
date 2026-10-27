import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLINICAL_DIR = ROOT / "clinical"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(CLINICAL_DIR))

from api import app

if __name__ == "__main__":
    import uvicorn
    print("=" * 70)
    print("Starting CareEdge Clinical AI Backend Service...")
    print("API Documentation: http://127.0.0.1:8000/docs")
    print("=" * 70)
    uvicorn.run(app, host="127.0.0.1", port=8000)
