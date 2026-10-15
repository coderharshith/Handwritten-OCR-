import sys
from pathlib import Path
import uvicorn

# Ensure project and backend paths are available
PROJECT_ROOT = Path(__file__).parent.resolve()
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKEND_DIR))

from backend.app.main import app

if __name__ == "__main__":
    print("[INFO] Starting Booklet Evaluation System API & Web UI on http://127.0.0.1:8000...")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=False)
