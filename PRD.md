# BullBench MarkovLab — Product Requirements Document

**Version:** 1.0 (proposed; no model results claimed)  
**Prepared:** 4 November 2026  
**Project:** Independent Unit 4 university ML application adapted from the original BullBench repository  
**Owner:** Student project team  
**Status:** Specification, not an implemented or validated release

## 1. Executive summary
BullBench MarkovLab is a reproducible Indian equity-market research platform built to investigate whether **Hidden Markov Models (HMMs)** can learn useful patterns in sequential market observations and improve **next-session large-move risk prediction**. It also benchmarks HMM-derived features in the original BullBench next-session closing-price forecasting task. It is **research software, not investment advice, a trading engine, or evidence of profitability**.

The project must be a separate submission for **Unit 4: Hidden Markov Models**. A functioning React/TypeScript website will call a Python FastAPI backend for fresh inference on authentic, newly published NSE observations. The application will expose the HMM's learning and decoding, probability forecasts, transition matrices, model comparisons, and data-quality evidence.

## 2. User problem and measurable value
A raw price chart does not show how an estimated hidden market regime changes over time or whether state-aware models add predictive value. MarkovLab helps students and researchers examine **sequential dependence** while seeing exactly when models outperform or underperform simple baselines.

### Primary research question
> Given information available immediately after trading session *t*, does a Gaussian HMM produce better calibrated predictions of a **large absolute return** during the next trading session than persistence, a simple Markov baseline and standard supervised models?

### Secondary research question
> Does incorporating causal, HMM-filtered state probabilities into standard next-close forecasting reduce out-of-sample prediction error relative to using the same forecaster without these features?

**No assumption that HMM wins.** A negative finding is a valid result.

## 3. Scope and requirements
### In scope (must ship)
1. Six original BullBench instruments: HDFCBANK, ICICIBANK, TCS, RELIANCE, TATASTEEL, and NIFTY 50, subject to sufficient verified history and symbol/series continuity.
2. Authentic NSE/ NSE Indices end-of-day data, latest completed session *at collection time*, with per-instrument freshness and source timestamps.
3. Reproducible cleaning, trading-calendar checks, corporate-action policy, feature-engineering and source manifest.
4. Unit 4: Gaussian HMM with maximum-likelihood/EM fitting, stable forward filtering, backward/forward-backward smoothing, Viterbi decoding, and transition probabilities. Show algorithm outputs and distinguish filtering from smoothing.
5. Independent prediction benchmarks, leakage-safe temporal validation, one final held-out test, and honest per-instrument findings.
6. FastAPI serving **saved validated model artifacts** to a functioning frontend; newest authentic observations may be used for inference after validation.
7. Interactive market/hidden-state explorer, transition matrices, risk forecasts, performance analysis and data-quality/provenance view.
8. Reproducibility instructions, automated tests, and model/data versioning.

### Out of scope
Live intraday trading, trade execution, brokerage integration, forecasts of investment returns, market-manipulation tools, simulated/synthetic training or test samples, fabricated labels, price data redistribution without permission, and using future outcomes to construct historical predictions.

### Optional after core validation
India VIX as context; per-sector state comparisons; HMM with alternate state counts, exogenous features, comparison with linear dynamical systems; scheduled updates; CSV uploads; probability-calibration visualizations.

## 4. Users and workflows
| User | Job to be done | Main interface |
|---|---|---|
| Student/reviewer | Verify Unit 4 concepts and reported scores | Methods Lab / Experiments |
| Research user | Explore historical hidden states and transitions | State Explorer |
| Data auditor | Verify latest update and cleaning | Data Quality |
| General visitor | Obtain an explicitly timestamped research risk estimate | Dashboard |

**Example user story:** Select TCS, view most recent official close, inspect filtered probabilities as of that date, see next-session large-move probability and baseline probabilities, switch to historical Viterbi trace without confusing it with a live forecast, and download experiment metrics.

## 5. Targets and definitions (lock before training)
### Primary target: next-session large-move event
For instrument *i*, session *t*, and **official unadjusted closing price** C, define daily log return `r_t = ln(C_t / C_(t-1))`, only over valid consecutive trading observations. Define `y_(t+1) = 1` when `abs(r_(t+1)) > theta_i`, else 0.

`theta_i` is an **asset-specific threshold fixed from the training fold only** (e.g., training 80th percentile of absolute daily log return), not estimated on validation/test. Report this definition conspicuously as **large absolute price move**, not next-day realized volatility or a genuine latent regime label. If corporate actions distort the definition, resolve adjustment using a documented official corporate-action series or use an approved consistent total-return/adjusted series; don't silently combine adjusted and unadjusted prices. A stable fixed threshold alternative must be preregistered.

### HMM risk calculation
Fit HMM on chronological observation vectors `o_t` formed from data genuinely available at the end of *t*. Use filtering `P(z_t|o_1:t)` (not full-sample smoothing) and transitions to calculate `P(z_(t+1)|o_1:t)`. Compute event probability via the next-return emission distribution, **provided that return is an HMM observation and its emission distribution has a defensible calibrated mapping to the event**. Standardizing features requires correctly transforming the return threshold into model space. If HMM emission assumptions are too restrictive, train a separate *training-only* state-to-event calibration mapping, then validate it; disclose that this becomes a two-stage model. Never use Viterbi state IDs as target truth.

### Secondary target: next-session closing price
Predict `r_(t+1)` or price change based only on information through t. Reconstruct predicted close from C_t and forecast return; evaluate MAE/RMSE on closing prices and naive previous-close comparator. Corporate action consistency is mandatory.

## 6. Data contract and acquisition
- Core: NSE equities and NSE Indices NIFTY 50, daily OHLC and volume as available. Preserve exact published values and original files.
- Optional: India VIX time-series and official corporate-action history.
- Source date, publication/retrieval time (IST), report format, URL, checksum, license/permission status, parsing version, original symbol/series and record count must be tracked.
- NSE has discontinued older CM bhavcopy variants from **8 July 2024**; use **CM-UDiFF Common Bhavcopy Final** for applicable later dates and a separately tested adapter for earlier data.
- NIFTY 50 should come from official NSE Indices historical-index reports, not the equity bhavcopy.
- Historical coverage: target 2015 onward if permitted and consistent; actual range depends on what is acquired/verified. *Latest* means most recently completed session with a **verified published source**, not today's calendar date.
- If downloads are blocked or automation isn't allowed, accept user-supplied official NSE exports with a transparent manual import flow. Never bypass restrictions, scrape behind access controls, or silently substitute Yahoo Finance while claiming official data.

## 7. Data preprocessing and quality gates
1. Validate file signatures/schema/date-format/encoding and preserve originals.
2. Normalize to canonical schema `instrument, session_date, open, high, low, close, volume, source_id, retrieved_at`, retaining source-specific extra fields separately.
3. Validate uniqueness (`instrument`, `session_date`), numeric types, OHLC invariants, positive price, nonnegative volume, and supported equity series.
4. Compare per-instrument dates to official trading calendar; holidays are not missing trading days. Suspensions, listing changes and absent source files are **gaps**, not filled price observations.
5. Flag corporate actions and abrupt breaks; never simply delete large genuine returns as outliers.
6. Construct returns and rolling features with `shift()` and `rolling()` in a causally correct pipeline; do not backfill future information.
7. Fit scaling, imputation rules, state models, thresholds, and feature selection **inside each training fold**. Persist all fitted transforms.
8. Export audit: rows in/out, duplicates, invalid entries, gaps, source disagreement, missingness and exclusion reasons.
9. Fail closed on stale/incompatible/new formats, and show reason on UI; do not label fallback snapshots as current.

## 8. Modelling specification
### Unit 4 methods (mandatory)
- Gaussian HMM (initially 2–4 hidden states; 2/3/4 selected **on validation** with convergence and stability diagnostics; covariance and regularization documented).
- HMM training via maximum-likelihood EM/Baum-Welch with repeated initializations, random seeds, log-likelihood trace and convergence assessment.
- Forward algorithm: scaled or log-space filtering; backward algorithm; forward-backward smoothing for **retrospective analysis only**.
- Viterbi algorithm: decode historical most-likely path, explicitly marked retrospective.
- Transition matrix: show persistence/transition estimates, separate from event-probability forecast.
- Independently implement at least one forward/Viterbi numerical check on a tiny *deterministic hand-calculated probability example* in tests. This is algorithm testing, not synthetic training data.

### Comparative baseline models
Primary: persistence of previously observed large-move label (with disclosure that it is not a state truth), training prevalence baseline, Logistic Regression, Random Forest, XGBoost, and a simple observable-category Markov chain. The HMM is primary research model. Use consistent supervised features and outcomes; mark which models can output calibrated probabilities.

Secondary: previous close, Ridge, ARIMA, Random Forest, XGBoost, HMM-based expected return, and XGBoost with/without HMM-filtered features. Start with original BullBench predictors but reconfirm parameterization.

### Selection and evaluation
- Fixed chronological train/validation/untouched test periods; optional expanding walk-forward **only on development windows**. No shuffled K-fold for time series.
- For model comparison use the **same asset/date prediction opportunities and timestamp-safe information**, with excluded-date lists.
- Select feature sets, thresholds, hyperparameters and probability calibration only from train/validation, not test.
- Primary: PR-AUC, Brier score, log loss, macro-F1/balanced accuracy at validation-set threshold; report base rate and reliability curves. Show raw forecasts and event count.
- Secondary: close MAE, RMSE, baseline relative change; include per-asset and per-year errors.
- HMM diagnostics: held-out predictive log likelihood, initialization stability, transition matrix, covariance regularization, convergence. These are **not directly equivalent** to supervised accuracy.
- Once locked, assess untouched test once; include honest negative findings and confidence/uncertainty where feasible.

## 9. System and architecture
`NSE official export/report -> ingestion/verification -> canonical data store -> feature pipeline -> time-safe experiments -> versioned HMM + baselines -> FastAPI inference -> React dashboard`.

Training and backtests run as offline reproducible jobs. Backend request uses saved trained model plus validated observations. Updates do not retrain automatically. No fabricated default predictions: if the latest verified source is unavailable, show last verified timestamp and status.

Suggested stack: Python 3.11+, pandas, numpy, scikit-learn, hmmlearn, statsmodels, xgboost, FastAPI + Pydantic; React/TypeScript frontend (retain existing `web/` implementation), TanStack Query and charting lib; PostgreSQL or local Parquet+SQLite for MVP; artifact storage. Python model must never be implemented as static JSON lookup.

## 10. Required frontend pages
1. Overview: assets, latest verified date, market context, prediction timestamp and clear research disclaimer.
2. Asset Explorer: close/return plots, dataset gaps, available date filters.
3. Hidden-State Lab: filtered vs smoothed state probabilities, Viterbi path, transition matrix and interpretation.
4. Forecasts: next-session event probability, threshold, model version and confidence/calibration caveats; secondary next-close table.
5. Experiments: baseline comparisons, per-date backtests, metrics, error and ablation analysis.
6. Data Quality: source links, missing dates, schema checks, cleaning functions, audit log and download.
7. Methodology: exact target, feature timing, data split dates, limits, Unit 4 algorithm explanation.

## 11. API requirements (details in docs/API_SPEC.md)
- `GET /health`
- `GET /v1/assets`
- `GET /v1/data/status`
- `GET /v1/assets/{asset}/history`
- `GET /v1/assets/{asset}/states?view=filtered|smoothed|viterbi`
- `GET /v1/assets/{asset}/transitions`
- `POST /v1/predict/large-move` (asset and as-of date; server verifies complete features)
- `POST /v1/predict/next-close`
- `GET /v1/experiments`, `GET /v1/experiments/{id}`
- `POST /v1/data/validate-upload` restricted, bounded, non-mutating unless explicitly committed by an authorized action.

Every forecast response must identify target session, `as_of_session`, `data_freshness`, model version, source provenance and warnings. Never return a probability without a target definition.

## 12. Functional acceptance criteria
- [ ] End-to-end official-data ingest on agreed sample, schema normalization and audit pass.
- [ ] Date continuity and corporate action policy documented per asset.
- [ ] A clean re-run reproduces derived features/model outcomes within documented tolerances.
- [ ] Forward, backward, filtering and Viterbi code verified with numerical checks and unit tests.
- [ ] No test observation leaks into fitted scalers, thresholds, HMM or model features.
- [ ] Primary experiment reports base-rate + >=3 competitors and honest separate per-asset test metrics.
- [ ] Original previous-close baseline retained for next-close comparison.
- [ ] Fresh authentic official observations (or uploaded official export) can produce new server-side prediction without rebuilding frontend.
- [ ] Results show exact as-of dates, data freshness and model source.
- [ ] Frontend handles missing/stale data, unsupported dates and server failures.
- [ ] README gives reproducible commands and data acquisition constraints.

## 13. Nonfunctional requirements
- Security: validation, bounded uploads, rate limiting, no secrets in repo/client, no unauthenticated training endpoint.
- Performance: precompute history/state plots; cache readonly views by model+data version; measured latency targets defined after implementation, not invented.
- Reliability: idempotent ingest, retry/backoff within provider terms, integrity hashes, atomic model deployment, clear stale/error status.
- Accessibility: keyboard/contrast/labelled charts, responsive frontend, explanatory legends and downloadable tables.
- Privacy: no personal financial information required.

## 14. Risks and mitigations
| Risk | Mitigation |
|---|---|
| Official history unavailable or restricted | Manual NSE export ingestion; document exact covered dates; no substitution without disclosure |
| Corporate actions create false price jumps | Official action reconciliation and comparison against adjusted series before model training |
| Nonstationary market | Per-period walk-forward backtesting, retrain-version policy, state stability checks |
| HMM degeneracy and state label switching | Multiple seeds, regularization, validation and state interpretation separate from numeric IDs |
| Look-ahead from smoothing | Never use smoothed/Viterbi retrospective states as features for past forecasts |
| High headline classification accuracy from imbalanced labels | PR-AUC/Brier/balanced accuracy and prevalence baseline |
| Trading/return claims | Academic research wording, no automated investment decisions |

## 15. Milestones and go/no-go gates
- **G0 Dataset:** All 6 assets sourced, validated, with agreed date range and corporate action policy. Gate: dataset manifest approved.
- **G1 Unit 4:** HMM algorithms demonstrated and unit-tested. Gate: forward/filter/Viterbi examples pass and valid convergence.
- **G2 Research:** Baseline comparison, leakage audit and locked evaluation. Gate: documented exact predictions and metrics.
- **G3 Application:** API integrated with React; fresh official observation inference works. Gate: recorded successful end-to-end demo.
- **G4 Submission:** docs, charts, sources, limitations and reproducible commands. Gate: independent local reproduction.

## 16. Attribution and ownership
BullBench is the starting point. Track reused modules and changes. Use only code/datasets with permitted rights and cite official sources. Do not claim results before training and validation.
