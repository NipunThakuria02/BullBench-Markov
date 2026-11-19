# BullBench MarkovLab

A Unit 4 HMM extension of the original Python/React BullBench. Research software; not investment advice.

Implemented: strict manual export adapters and immutable snapshots; separate authorized Yahoo/manual-index exploratory track; NumPy Gaussian HMM with log-space forward/backward, filtering, smoothing, Viterbi and Baum–Welch; development and locked exploratory historical benchmarks, separate newest-data state models and paired price-feature ablations; checksum-verified saved-artifact FastAPI; React research workspace with honest unavailable states.

The original source ZIP remains the provenance reference. Legacy modules remain under `src/nse_forecast`; their fixed-date Yahoo benchmark is separate from the new extension. See [orientation](docs/ORIENTATION.md), [data guide](docs/DATA_SOURCES.md), [progress and limitations](docs/IMPLEMENTATION_STATUS.md). Read AGENTS.md and RULES.md before changes.

## Which download do you have?

Read [START_HERE.md](START_HERE.md) first. The GitHub source archive includes launch/deployment helpers but deliberately excludes private datasets/models and generated frontend builds. The separate complete local ZIP includes those assets. The owner-requested `local-data-models` branch also contains `data.zip` and `model_registry.zip`; extract both in the project root to restore the datasets, models and original local dashboard history. Its data path is `data/exploratory_snapshots/`. Check with `python scripts/check_distribution.py --local`.

## Develop

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-local.lock
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -m pytest -q
npm --prefix web ci
npm --prefix web run build
```

From the repository root, start the backend and frontend in separate terminals:

```bash
.venv/bin/python scripts/run_backend.py
npm --prefix web run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Vite proxies `/api`, `/v1` and `/health` to the backend. The local backend launcher explicitly enables checksummed original results/history under `data/legacy_site`; hosted uvicorn defaults to disabling those endpoints. `/health` is process health; `/ready?asset=TCS` returns 503 unless a valid local bundle and input dataset load. No services train on requests. Data/model paths default to `data/exploratory_snapshots` and `model_registry`; set `BULLBENCH_SNAPSHOTS=data/exploratory_snapshots` for exploratory data. CORS uses `BULLBENCH_CORS_ORIGINS` (comma-separated exact origins).

## MarkovLab in the original frontend

Click **MARKOVLAB** beside **HOME**. From an asset page, its instrument carries into the lab; from the homepage the lab defaults to TCS. All six instruments have preserved development runs and separately labelled locked historical tests. Separate current state-exploration models were trained through 16 October 2026. The lab reuses the original design and offers Results, Hidden states, Transitions, Risk forecasts and Data quality. Results show each run’s exact evaluation dates and exploratory limitations. Missing runs and forecast prerequisites remain unavailable. The original model comparison remains accessible for the same instrument.

The preserved development runs span 2023-04-05–2023-09-29, trained through 2023-03-31. The default locked historical runs were fit through 2024-12-31 and tested on target sessions 2026-01-19–2026-10-16 after 2025 validation. See [historical results](docs/HISTORICAL_RESULTS.md) and [model card](docs/MODEL_CARD_HISTORICAL.md). Only the older development runs have the following one-class NIFTY caveat: These are historical development results, not prospective or final-test evidence. NIFTY 50 has zero validation events, so class-dependent metrics are explicitly not estimable. See docs/ALL_INSTRUMENT_RESULTS.md. Use **EXPORT VALIDATION PREDICTIONS** for the checked derived event probabilities and outcomes; raw-price files are not exposed.

## Data and experiments

Follow [DATA_SOURCES.md](docs/DATA_SOURCES.md). No API key is required. Yahoo network access must be permitted by the environment. NSE Indices files are imported manually.

Development-only example using existing private exploratory snapshots:

```bash
.venv/bin/python -m nse_forecast.experiments.lab --config config/exploratory-tcs.json --output model_registry/tcs-development
```

Runs refuse to overwrite an existing directory. The example ends validation before the original inspected price-test window. Edit explicit dates only as a recorded research choice. No final-test evaluator or protocol-freeze automation exists.

A development candidate can be enabled locally, explicitly labelled exploratory:

```bash
.venv/bin/python -m nse_forecast.experiments.activate --bundle tcs-development --exploratory
```

This only enables local loading; it does not approve G0–G4 or certify a release. Serving forecasts additionally requires an explicit session calendar in the run configuration. Never fabricate future sessions. Raw OHLC history is not public. Official raw-close serving requires an action-consistent reconstruction contract and remains unavailable.

## Checks

```bash
.venv/bin/python -m pytest -q
CHROMIUM_PATH=/usr/bin/chromium npm --prefix web test -- markov.spec.ts
```

`npm --prefix web test` runs both the new workspace and preserved legacy dashboard using separate builds/ports. `VITE_LEGACY_DASHBOARD=1` enables only the explicit legacy build; default prediction screens never use its examples. Browser installation depends on your machine; use a trusted installed Chromium or Playwright's verified installation.

## Hosting

See [the full deployment guide](docs/DEPLOYMENT.md). `Dockerfile.backend`/`render.yaml` prepare backend hosting; Vercel uses the guarded `scripts/build_vercel.mjs` and outputs `web/dist-vercel/`, excluding private static snapshots. No deployment has been made. Use `VITE_API_BASE_URL` for a separately hosted API, `scripts/configure_api_host.py https://YOUR_API_ORIGIN` to prepare exact-origin CSP, and exact CORS origins on the backend. The root Vercel config is the single config; the site uses hash navigation, so API routes are never rewritten to HTML. Do not enable public data display without rights review.

## Attribution

Derived from NipunThakuria02/BullBench, supplied by the owner as BullBench-main.zip. The supplied snapshot contained no license; no third-party licensing rights are invented here. Confirm redistribution permission before public release. See [provenance](docs/CODE_PROVENANCE.md).

All-instrument development runner: `python scripts/run_all_development.py --workers 2`. This reuses compatible checked artifacts and runs missing instruments only; it never executes final-test evaluation.
