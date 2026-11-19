# AGENTS.md — BullBench MarkovLab

Instructions for AI coding/analysis agents. Read this file first, fully, before touching anything.
Last updated: 4 Nov 2026.

## 1. What this project is
BullBench is an existing Python + React pipeline that compares five next-day return forecasters (Naive, Ridge, ARIMA, Random Forest, XGBoost) on six NSE series (HDFCBANK, ICICIBANK, TCS, RELIANCE, TATASTEEL, NIFTY 50).
We are extending it into **BullBench MarkovLab**, a Unit 4 (Hidden Markov Models) project:
- Primary task: probability that the next session has a large absolute return, HMM vs baselines.
- Secondary task: the original next-close forecast, with and without causal HMM-filtered features.
- A FastAPI backend serves saved model bundles to the existing React site.

## 2. What exists vs what is only specified
EXISTS (in the zip): `src/nse_forecast/` (config, data, features, models, evaluate, diagnostics, audit, provenance, import_csv, history, report, web, cli), `web/` React site, 56 passing pytest tests, exploratory `web/public/results.json`.
SPECIFIED ONLY (do not claim it exists): HMM code (`unit4/`), official-NSE adapters (`ingest/`), `experiments/`, model registry, FastAPI `backend/`, new frontend pages, `config/*.yaml`, most scripts.
NO MODEL RESULTS EXIST for the HMM task. Never invent metrics, dates, endpoints, citations or timestamps.

## 3. Reading order
Specs (constraints first, then intent, then design):
1. `RULES.md`
2. `PRD.md`
3. `docs/EXPERIMENT_PROTOCOL.md`
4. `docs/DECISIONS.md`
5. `ARCHITECTURE_EXTENDED.md`
6. `WORKFLOW.md`
7. `docs/LIMITATIONS.md`
8. `docs/DEPLOYMENT.md` and `docs/SECURITY.md` (only for API/hosting work)
9. `docs/MODEL_CARD.md` (empty template; note its shape only)

Code (ground truth for the present):
1. `README.md` (stale: says STOCK-main; cache paths wrong; treat as a hint)
2. `pyproject.toml`, `requirements.lock`
3. `src/nse_forecast/config.py`, `data.py`, `provenance.py`
4. `features.py`, `models.py`, `evaluate.py`
5. `audit.py`, `diagnostics.py` (contains the paired block bootstrap to reuse)
6. `cli.py`, `web.py`
7. `docs/RESEARCH_REVISION.md`, `docs/DATA_AVAILABILITY.md`
8. `tests/`
9. `web/src/data.ts`, then skim `web/src/main.tsx` (about 1,550 lines), then `vercel.json`
10. `web/public/results.json`: read metadata keys only, not the rows.
Skip: `docs/cache/*.csv`, `docs/cache/.yfinance/`, logos, fonts, lockfiles of node_modules.

## 4. Precedence when files conflict
1. `RULES.md`
2. `docs/EXPERIMENT_PROTOCOL.md` (once frozen)
3. `docs/DECISIONS.md`: Accepted entries only. Proposed and Open entries are NOT settled; ask before relying on them.
4. `PRD.md`
5. `ARCHITECTURE_EXTENDED.md`
6. `WORKFLOW.md`
7. Current code and README
Gate names: use G0–G4 only. Ignore the M0–M5 and "milestone 0–7" labels.

## 5. Hard rules (summary of RULES.md; the file wins on any difference)
- Real observations only. No synthetic price rows, labels, imputation across missing sessions, or forward-fill over suspended sessions. Tiny hand-checkable fixtures are allowed in unit tests only.
- No leakage: fit scalers, thresholds, HMMs, calibrators on training data only. No shuffled splits. No current-day close used to "predict" the same day.
- Real-time inference uses **filtering only**. Viterbi and smoothed probabilities are retrospective displays and never feed a historical forecast. Do not use library `predict_proba` in the inference path without proving it is causal.
- Hidden state IDs are never class labels and have no stable meaning across fits.
- Never mix adjusted and unadjusted prices. Corporate actions follow the documented policy (D-003).
- Do not call Yahoo data official NSE data. Do not automate NSE website downloads (their terms prohibit it without permission).
- Do not retrain on API requests. No training or promotion endpoint.
- Do not hard-code performance numbers in the frontend. No generated placeholder predictions in production views.
- Keep a non-investment-advice notice. No buy/sell UI.
- Do not commit secrets, cookies, or raw licensed data.

## 6. Known traps in the current code
- `START`/`END` (2021-10-01 to 2026-10-16) are hard-coded in `config.py` and also enforced in `data.validate`, `provenance.valid_provenance`, `web.py` (date and model/asset whitelists) and tests. Changing the range means touching all of them.
- `data.py` is coupled to Yahoo (`yfinance`, `auto_adjust=True`).
- `features.py` uses simple `pct_change` returns; the new task uses log returns defined in the protocol.
- `docs/cache` holds only 8 series, so the full original evaluation cannot be re-run from the zip.
- `web/public/results.json` is labeled "exploratory, review_required" with 69 audit findings.
- `web/src/data.ts` contains `exampleRows()` generated data. Never let it reach prediction views.
- `vercel.json`: CSP `connect-src 'self'` and the `/api/(.*)` rewrite to `/index.html` break calls to a separate API. Two `vercel.json` files exist.
- `docs/cache/.yfinance/cookies.db` should not be in a public repo.
- XGBoost showed cross-platform differences (up to about 0.002) in the legacy run; reproduction tolerances are not yet defined.

## 7. Working agreement
1. Complete one gate at a time: G0 data, G1 Unit 4 algorithms, G2 research, G3 app, G4 submission. Run its tests and commit artifacts and decisions before the next gate.
2. Smallest reliable change. Do not rename the package or combine refactors with new ML features (D-001).
3. Run `python -m pytest -q` before and after changes. Existing 56 tests must keep passing unless a change is recorded in `docs/DECISIONS.md`.
4. Any change to a target, threshold, dataset, algorithm or definition gets a `docs/DECISIONS.md` entry and, after the protocol freeze, a deviation-log row in `docs/EXPERIMENT_PROTOCOL.md`.
5. Every reported metric must be reproducible from saved predictions plus the experiment config.
6. When something is unknown, say so and mark it `TBD`/`unverified`. Do not fill gaps with plausible values.
7. Ask before: accepting a Proposed/Open decision, freezing the protocol, touching the final-test window, changing data sources, or deleting files.

## 8. Before writing code, answer these in plain text
1. What exists versus what is only specified?
2. What is the primary target, and why is θ fixed rather than per fold?
3. Which HMM outputs are allowed in real-time inference, and which are not?
4. Which files must change to remove the hard-coded `END`?
5. Which decisions in `DECISIONS.md` are still Open or Proposed?
6. List any contradictions you found between files.
If you cannot answer these correctly, re-read Section 3.

## 9. Suggested first tasks (in order)
1. Fix `vercel.json` (single file, CSP and rewrite) and repo hygiene (`.gitignore`, remove cookies/db files, add LICENSE).
2. G0: manual official-data import for one stock plus NIFTY 50; verify previous-close adjustment on known ex-dates; write `docs/DATA_SOURCES.md` and `docs/CORPORATE_ACTIONS.md`.
3. G1: implement `unit4/` (forward, backward, Viterbi, Baum-Welch) with the hand-calculated fixture; use hmmlearn only as a test oracle.
4. Freeze `docs/EXPERIMENT_PROTOCOL.md`, then G2 experiments including the EWMA and GARCH baselines.
5. Only then FastAPI and the frontend pages.

## 10. Style
Plain, simple, debuggable code with tests. Typed schemas at API boundaries. Versioned artifacts. Explicit as-of dates and freshness in every output.
