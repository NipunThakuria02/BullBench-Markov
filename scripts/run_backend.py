"""Start the backend API server for local development.

Sets up paths and enables the local legacy-results endpoints, then
starts uvicorn on http://127.0.0.1:8000.

Run this from the project root:
    .venv/Scripts/python.exe scripts/run_backend.py   (Windows)
    .venv/bin/python scripts/run_backend.py           (macOS / Linux)

Then start the frontend in a second terminal:
    npm --prefix web run dev

Open http://localhost:5173 in your browser.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

os.environ["BULLBENCH_LOCAL_LEGACY"] = "1"
os.environ["BULLBENCH_LEGACY_SITE"] = str(ROOT / "data/legacy_site")
os.environ["BULLBENCH_SNAPSHOTS"] = str(ROOT / "data/exploratory_snapshots")
os.environ["BULLBENCH_REGISTRY"] = str(ROOT / "model_registry")

if __name__ == "__main__":
    import uvicorn

    print("Backend running at http://127.0.0.1:8000")
    print("Open the frontend at http://localhost:5173")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
