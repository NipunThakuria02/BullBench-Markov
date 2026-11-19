# Local and hosted deployment

Updated 5 November 2026. Deployment configuration is prepared; no public service has been created by these changes. Scientific validation remains exploratory.

## 1. Files and distributions

The source repository now includes START_HERE.md, requirements-local.lock, START_WINDOWS.bat, start_local.sh, scripts/run_local.py and scripts/check_distribution.py. The GitHub archive excludes private/generated paths by design. The complete private distribution includes those helpers **plus** web/dist/, data/exploratory_snapshots/, all six model bundles/pointers and evidence. See START_HERE.md and the package's PACKAGE_CONTENTS.json.

Use `python scripts/check_distribution.py --local` before following instructions that require the full local distribution. Model scalers are arrays inside hmm.npz. The accepted exploratory track uses `data/exploratory_snapshots`, not the old official-track placeholder `data/snapshots`.

## 2. Local private launch

Use START_WINDOWS.bat or `bash start_local.sh` after installing Python 3.12. The launchers create a .venv, install pinned requirements, install the local package and run readiness checks on first setup. The prebuilt private package needs no Node.js for normal use. The server serves the frontend and API on the same localhost port; no CORS/API-origin configuration is needed for that case.

Manual check/start: `.venv/bin/python scripts/run_local.py --check` and `.venv/bin/python scripts/run_local.py`. Windows uses `.venv\\Scripts\\python.exe`. Port override: `--port 8001`.

## 3. Architecture for public hosting

Vercel static frontend → HTTPS FastAPI service → private persistent snapshot/model storage.

Public Vercel output contains application code and branding assets only. Private local legacy results/history, raw data, cookies and model binaries must not enter the public static output. Python training/import/promotion remain offline. `/v1/assets/{asset}/history` continues to deny raw-history serving pending rights review.

## 4. Render backend

`Dockerfile.backend` is the Python 3.12 backend image definition. `.dockerignore` excludes private data, models, environments and frontend artifacts from the image context. `render.yaml` is an optional Blueprint with a disk-capable paid plan and a 1 GB persistent disk; review current plans/costs in Render before creating it. No infrastructure is created by the file itself.

Repository root is the deployment root. The Docker image installs `requirements-local.lock` and the Python package, then runs:

```bash
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

The image supplies a default port of 8000; the host's PORT takes precedence. Attach the persistent disk at `/var/data` and set:

```text
BULLBENCH_SNAPSHOTS=/var/data/exploratory_snapshots
BULLBENCH_REGISTRY=/var/data/model_registry
BULLBENCH_CORS_ORIGINS=https://YOUR-ACTUAL-FRONTEND.vercel.app
```

Transfer the contents of the separate **private backend-data archive** to `/var/data`, using the provider's authenticated shell/file-transfer mechanism. It contains `exploratory_snapshots/`, `model_registry/` and supporting evidence. Do not put it in public Git or a public download bucket. A source checkout/image without these files starts process health but cannot serve saved models.

For an existing backend: preserve old immutable artifacts before updating files and switching pointers; do not edit released bundle contents. Check the data/model checksums and restart the service after deployment.

Without Docker, use Python 3.12, build `pip install -r requirements-local.lock && pip install --no-deps -e .`, and start uvicorn as above. The same private storage/environment configuration is needed.

## 5. Vercel frontend (repository root)

Deploy the backend first to obtain its real HTTPS origin. Then run locally:

```bash
python scripts/configure_api_host.py https://YOUR-ACTUAL-BACKEND.onrender.com
```

Commit the resulting exact-origin CSP in vercel.json and push. In Vercel, set:

```text
VITE_API_BASE_URL=https://YOUR-ACTUAL-BACKEND.onrender.com
```

Import the GitHub project with repository root as Root Directory and use the checked-in settings:

- Install: `npm --prefix web ci`
- Build: `node scripts/build_vercel.mjs`
- Output: `web/dist-vercel`
- Framework override: Other, if Vercel tries to apply a conflicting root preset.

The build fails with a specific message if the actual backend origin is missing or mismatched with CSP. It uses an isolated branding-only public directory, so even a local private package's web/public/results.json and web/public/history/ cannot leak into the Vercel build. The local prebuilt web/dist is not overwritten.

After Vercel assigns the actual frontend URL, set that exact URL in backend BULLBENCH_CORS_ORIGINS and restart/redeploy the backend. Redeploy the frontend after any VITE_API_BASE_URL change because it is a build-time value. Preview/frontend custom domains need their own explicit CORS allowance. Do not use wildcard origins to avoid configuration work.

The site uses hash routes. There is no catch-all rewrite turning API failures into HTML. No second web/vercel.json is used.

## 6. Readiness and practical limits

- `/health`: process is running.
- `/ready?asset=TCS` (or each other asset): saved model/data/schema load and verify. It is not a claim that forecast calendar prerequisites or research gates have passed.
- `/v1/experiments`: six saved development runs when all private files are present.
- `/v1/experiments/{id}`: checked saved probability/price results; NIFTY classification metrics stay null where undefined.
- `/v1/data/evidence`: imported evidence and outstanding reconciliation.

Verify an actual results request and state/transition load after hosting. Saved-result display is possible while new-session forecasting remains blocked by unresolved calendar requirements. Do not label historical data current or report invented timestamps. One-worker in-process rate limiting is a prototype control, not a distributed production rate limiter. Hosting does not establish source redistribution rights, predictive usefulness or G0–G4 completion.

Render reference: https://render.com/docs/deploy-fastapi

## 7. Produce and audit the distributions

With a clean committed source tree, the six private datasets/models present and a local frontend build:

```bash
python scripts/package_release.py --output releases
```

This creates three clearly named archives with checksums. It refuses missing local assets or uncommitted tracked source changes. Optional `--legacy-public PATH` and `--legacy-cache PATH` include the owner's original local legacy static artifacts/cache without adding them to Git. The backend-data archive has no extra directory prefix: extract directly into the backend's persistent mount. No vendor cookies, credentials or node_modules are included.

Source-only download checks are intentionally different from full private-local checks; never infer that model training is needed merely because a source archive omitted the existing private artifacts.

## 8. Two-terminal Windows development (updated evaluation + original dashboard)

Use the updated source from main and the updated `data.zip` / `model_registry.zip` on the `local-data-models` branch. Extract both archives directly into the project root. The data archive now includes `data/legacy_site` (original historical results/history plus checksums); it is required for original dashboard values. Registry includes preserved 2023 development runs, 2026 locked historical test results and separate latest state-exploration models.

Terminal 1, from project root:

```powershell
.\.venv\Scripts\python.exe scripts\run_backend.py
```

Terminal 2, from the same project root:

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm --prefix web run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open http://127.0.0.1:5173/ . This backend launcher explicitly enables private local legacy endpoints and binds to loopback. Running plain hosted uvicorn does not enable them. Check `/api/results` for the original comparison, `/api/history?symbol=TCS.NS` for its history, and `/v1/experiments` for saved MarkovLab runs. The public raw-OHLC endpoint remains disabled.

For direct uvicorn development, explicitly set `BULLBENCH_LOCAL_LEGACY=1` and `BULLBENCH_LEGACY_SITE` to the absolute `data/legacy_site` directory, alongside existing snapshots/registry env settings. Do not enable this mode in the hosted backend; the local dashboard fix does not authorize default public history serving. Vercel still excludes raw/static legacy files.
