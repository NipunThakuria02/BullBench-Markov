> This original file is the specification template. Current generated exploratory evidence is in [MODEL_CARD_HISTORICAL.md](MODEL_CARD_HISTORICAL.md); template statements below do not describe the current implementation.

# MODEL CARD — BullBench MarkovLab

**Status:** TEMPLATE. No model has been trained, validated or released. Every `—` below must be filled from the model registry manifest and saved predictions, never by hand-typing numbers (RULES #4, WORKFLOW working agreement).
**Generated from:** `model_registry/<model_id>/manifest.json` — `—`
**Card version / date:** — / —

## 1. Model details
| Field | Value |
|---|---|
| Model ID / bundle version | — |
| Code commit | — |
| Protocol freeze tag and sha256 | — (`docs/EXPERIMENT_PROTOCOL.md`) |
| Type | Gaussian HMM (own NumPy implementation) + calibration; baselines listed in §5 |
| Number of states / covariance | — |
| Observation vector | — |
| Seeds, restarts, convergence status | — |
| Trained through (last session) | — |
| Feature schema hash | — |
| Library versions | — |

## 2. Intended use
- Research and teaching: studying sequential dependence and regime structure in Indian equity end-of-day data, and comparing HMM-based risk probabilities with baselines.
- Audience: students, reviewers, researchers.

## 3. Out-of-scope use
- Trading, order generation, investment advice, profitability claims.
- Intraday or real-time use (data is completed-session end-of-day).
- Interpreting numeric state IDs as "bull/bear" truth. State IDs have no stable meaning across fits.
- Assets other than the six listed in `config/assets.yaml`.

## 4. Data
| Field | Value |
|---|---|
| Source(s), report formats | — (`docs/DATA_SOURCES.md`) |
| Date range per asset | — |
| Data version / manifest hash | — |
| Corporate-action policy | — (`docs/CORPORATE_ACTIONS.md`) |
| Excluded sessions and reasons | — (`data_quality_report.json`) |
| Permission/licence status | — |

## 5. Evaluation
Target: next-session large absolute price move, `|r_{t+1}| > θ_a`. Thresholds per asset: — .

**Split dates:** train — ; validation — ; final test — ; prospective ledger from — .

**Final-test results** (copied from `reports/<run_id>/metrics.csv`; checksum `—`):
| Asset | Model | Base rate | Events | Brier | Brier skill vs prevalence | Log loss | PR-AUC |
|---|---|---|---|---|---|---|---|
| — | — | — | — | — | — | — | — |

Include every model run, including failed ones, and the 95% paired block-bootstrap intervals. Report negative results.

**Calibration:** reliability curves with bin counts — `reports/<run_id>/calibration/`.
**HMM diagnostics:** held-out log-likelihood, restart stability, transition matrix, expected dwell times — `reports/<run_id>/hmm/`.
**Secondary task (next close):** MAE/RMSE and skill vs previous close, with and without HMM-filtered features — `reports/<run_id>/price/`.

## 6. Limitations (summary; full list in `docs/LIMITATIONS.md`)
- —

## 7. Ethical and legal considerations
- Not investment advice. NSE data used under the permission/terms recorded in DATA_SOURCES.md. No raw licensed data is redistributed beyond what that record allows.
- No personal data is collected.

## 8. How to reproduce
```
# commands to be filled in once scripts exist (see README)
```
Expected agreement: — (tolerance documented after the first clean re-run; note known cross-platform XGBoost differences recorded in `docs/RESEARCH_REVISION.md`).

## 9. Change log
| Date | Model ID | Change | Decision ID |
|---|---|---|---|
| — | — | — | — |
