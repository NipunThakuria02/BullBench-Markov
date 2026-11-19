# Start here: source download vs complete private local package

## First check which download you have

- **GitHub source ZIP / clone:** contains code, launch helpers and deployment configuration. It intentionally does **not** contain private data/models or generated `web/dist/`.
- **BullBench-Markov-Deployment-Local.zip:** complete private local distribution. Contains code, launchers, prebuilt `web/dist/`, six imported datasets under `data/exploratory_snapshots/`, six model bundles/pointers, saved results, and preserved evidence. It also includes the original private legacy results/history for local viewing.
- **BullBench-Markov-Deployment-Source.zip:** deployment/source package without private inputs or model binaries. Build the frontend and supply private backend artifacts separately.

The previous screenshot describes a **source ZIP**, not the complete private distribution. `data/snapshots/` is not the directory for the owner's approved Yahoo-equity/manual-NIFTY exploratory track. The correct path is `data/exploratory_snapshots/`. Do not rename it to imply official-only validation. Scaler mean/scale arrays are stored in each `hmm.npz`; there is no required separate `scaler.npz`.

Run this dependency-free check from the extracted project root:

```bash
python scripts/check_distribution.py
python scripts/check_distribution.py --local
```

The first checks source helpers. The second additionally checks the local frontend, all six datasets, model artifacts, pointers and scaler arrays. The detailed archive listing is in `PACKAGE_CONTENTS.json` in the private ZIP.

## Windows local launch

1. Install 64-bit Python 3.12 from https://www.python.org/downloads/ including the `py` launcher.
2. Extract the entire **private local ZIP** to a normal writable folder; do not run inside the ZIP.
3. Double-click `START_WINDOWS.bat`. First setup installs pinned dependencies into `.venv`; internet is required then.
4. Open http://127.0.0.1:8000/ . MARKOVLAB appears beside HOME. Every instrument has saved development results.
5. Keep the terminal open; Ctrl+C stops the server.

No Node.js is needed for running the prebuilt private package. Cookies, tokens, virtual environments and node_modules are excluded. Ordinary startup does not fetch data, train models or run final-test evaluation.

## macOS / Linux local launch

Install Python 3.12, extract the private ZIP, open a terminal in its root and run:

```bash
bash start_local.sh
```

Linux may need its Python venv package. If macOS reports a missing XGBoost OpenMP runtime, install the official libomp runtime through your package manager. Fresh Windows/macOS dependency installation has not been tested in this Linux task.

## Manual local setup

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-local.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\run_local.py --check
.\.venv\Scripts\python.exe scripts\run_local.py
```

macOS/Linux: use `python3.12 -m venv .venv` and `.venv/bin/python` for the remaining commands. To change ports, append `--port 8001` to the launch command.

## Running a GitHub source checkout

The launch helper now exists in GitHub, but a GitHub source download is still not the private distribution. Copy `data/` and `model_registry/` from your private package, install Python dependencies as above, then build the frontend with Node.js 22+:

```bash
npm --prefix web ci
npm --prefix web run build
python scripts/check_distribution.py --local
```

Use the .venv Python to run `scripts/run_local.py`. Without private artifacts, the API reports unavailable; it must not fabricate model results. Optional original static legacy results/history are only in the private local ZIP, not the public source build.

## Vercel / hosted backend

Read `docs/DEPLOYMENT.md`. Vercel hosts the **frontend only**. Deploy the Python backend separately using `Dockerfile.backend` / optional `render.yaml`, provide the private backend data, obtain its actual HTTPS origin, and configure the frontend API origin/CSP/CORS.

Vercel builds into `web/dist-vercel/` using `scripts/build_vercel.mjs`. That build excludes local legacy results/history even if invoked from a private ZIP, and leaves local `web/dist/` untouched. Do not override the guarded build with the private/local build command for a public deployment.

## Scope and privacy

The six models are exploratory development bundles (training cutoff 2023-03-31; validation targets 2023-04-05–2023-09-29). NIFTY has zero validation events; class-dependent metrics remain not estimable. Calendar amendments, official adjustment checks and source rights remain pending; new-session forecasts may remain correctly blocked. No G0–G4 release or final-test performance is claimed.

Keep the private ZIP, datasets and model payload private. The local launcher binds only to 127.0.0.1. Do not upload that ZIP to a public GitHub repository or a public static-data host. `BUNDLE_MANIFEST.json` records packaged file checksums. No session-specific workspace path is required.

## November 5 update: two terminals and newer evaluations

Use the updated `data.zip` (now includes `data/legacy_site`) and `model_registry.zip` from the `local-data-models` GitHub branch with the updated main-branch source. For Windows backend run `.\.venv\Scripts\python.exe scripts\run_backend.py`; in another project-root terminal run `$env:VITE_API_BASE_URL="http://127.0.0.1:8000"` then `npm --prefix web run dev -- --host 127.0.0.1 --port 5173 --strictPort`.

The lab prefers the locked historical run when present. Its model was fit through December 2024, selected on 2025 validation and evaluated on 19 January–16 October 2026. Earlier 2023 development results stay selectable. Separate latest HMMs are fit through 16 October 2026 for state exploration; they do not inherit historical test scores. No new-session forecasts, official validation or prospective evaluation is claimed. See HISTORICAL_RESULTS.md and LATEST_MODELS.json.
