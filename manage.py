import sys
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "scripts" / "run_pipeline.py"

if __name__ == "__main__":
    cmd = [sys.executable, str(SCRIPT)] + sys.argv[1:]
    sys.exit(subprocess.run(cmd).returncode)
