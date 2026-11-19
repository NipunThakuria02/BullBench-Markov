# BullBench MarkovLab

BullBench is a research tool that compares how well different forecasting models predict next-day stock prices for Indian markets. It covers five major NSE stocks (TCS, HDFC Bank, ICICI Bank, Reliance, Tata Steel) and the Nifty 50 index.

MarkovLab is an extension that adds Hidden Markov Model (HMM) analysis. It detects hidden market regimes (calm vs volatile periods) and uses them to estimate the probability of a large price move on the next session.

This is research software only and is not investment advice.

---

## What it does

- Compares five forecasting models: Naive baseline, Ridge regression, ARIMA, Random Forest, and XGBoost
- Shows how close each model's predicted closing price was to the actual closing price
- Uses Hidden Markov Models to identify hidden market states in price history
- Displays all results in an interactive web dashboard
- All data and model outputs are pre-saved; the app only reads and shows them, it never trains live

---

## Project structure

```
backend/                  FastAPI server - serves model results as a REST API
  app/
    main.py               All API endpoints

config/                   Experiment config files, one per asset (JSON)

data/                     Pre-saved data (not in GitHub, add locally)
  exploratory_snapshots/  Input data for HMM models
  legacy_site/            Saved BullBench results (results.json and price history)

model_registry/           Saved trained HMM models (not in GitHub, add locally)

scripts/
  run_backend.py          Starts the backend server for local development

src/
  nse_forecast/           Core Python library used by backend and tests

tests/                    Python test suite

web/                      React + TypeScript frontend
  src/                    UI source code
  public/                 Static assets (fonts, favicons, logos)
  vite.config.ts          Vite configuration
  package.json
```

---

## Running locally

You need Python 3.12 and Node.js 20 or later.

**Step 1: Set up the Python environment**

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\python.exe -m pip install -r requirements-local.lock
.venv\Scripts\python.exe -m pip install --no-deps -e .
```

macOS / Linux:
```bash
.venv/bin/python -m pip install -r requirements-local.lock
.venv/bin/python -m pip install --no-deps -e .
```

**Step 2: Install frontend dependencies**

```bash
npm --prefix web install
```

**Step 3: Add data and models**

Place the `data/` and `model_registry/` folders in the project root. These are not included in the repository because they are large private files.

**Step 4: Start the servers**

Open two terminals from the project root.

Terminal 1 (backend):
```bash
# Windows
.venv\Scripts\python.exe scripts\run_backend.py

# macOS / Linux
.venv/bin/python scripts/run_backend.py
```

Terminal 2 (frontend):
```bash
npm --prefix web run dev
```

Then open http://localhost:5173 in your browser.

The Vite dev server automatically forwards `/api`, `/v1`, and `/health` requests to the backend at port 8000.

---

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `BULLBENCH_SNAPSHOTS` | `data/exploratory_snapshots` | Path to HMM input data |
| `BULLBENCH_REGISTRY` | `model_registry` | Path to saved model bundles |
| `BULLBENCH_LOCAL_LEGACY` | (off) | Set to `1` to enable saved legacy results |
| `BULLBENCH_LEGACY_SITE` | `data/legacy_site` | Path to legacy results data |
| `BULLBENCH_CORS_ORIGINS` | `http://localhost:5173,...` | Allowed frontend origins (comma-separated) |
| `VITE_API_BASE_URL` | (empty, uses proxy) | Backend URL when frontend and backend are on separate hosts |

Copy `.env.example` to `.env` and fill in values as needed.

---

## Running tests

```bash
# Python tests
.venv/bin/python -m pytest -q

# Frontend browser tests (requires Chromium installed)
npm --prefix web test
```

---


