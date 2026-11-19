# Model card — locked exploratory historical evaluation

Descriptive historical result, not untouched/prospective, not official G0–G4 certification.

Models: own NumPy Gaussian HMM; diagonal covariance on scaled return; causal forward filtering. State count/seed chosen using 2025 validation only. Full frozen choices: EXPLORATORY_PROTOCOL_V1.md. Data: Yahoo auto-adjusted equities, manual NSE Indices NIFTY; original hashes retained. No official calendar/corporate-action certification. No fitted probability calibrator; reliability bins and raw probability losses are reported.

Training targets end 31 December 2024. Validation origin cutoff 15 April 2025; targets through 30 September 2025. Historical test targets 19 January–16 October 2026, with at least 60 observed-origin embargoes. Event threshold remains the first-block (through 31 March 2023) 80th percentile. This historical period was inspected for original price forecasts and is not untouched.

| Instrument | States | Seed | Event threshold | HMM Brier | HMM skill vs prevalence |
|---|---|---|---|---|---|
| HDFCBANK | 3 | 44 | 0.01746553 | 0.181014 | 0.081178 |
| ICICIBANK | 4 | 44 | 0.01753480 | 0.157094 | 0.042220 |
| NIFTY 50 | 4 | 42 | 0.01224921 | 0.147710 | 0.060370 |
| RELIANCE | 3 | 44 | 0.01903062 | 0.148467 | -0.024715 |
| TATASTEEL | 3 | 44 | 0.02525714 | 0.099301 | 0.022593 |
| TCS | 4 | 43 | 0.01738854 | 0.254948 | -0.039711 |

All nine comparators and eight secondary price comparisons, including negative findings and candidate convergence traces, are saved in manifests/predictions. Brier lower is better. Within-asset paired bootstrap block lengths 10/20/40, 4,000 draws, seed42 are saved in bootstrap_sensitivity.json. Intervals are conditional on fitted predictions; models are not refit and cross-asset multiplicity is not corrected.

Reproduce from imported artifacts: `python scripts/run_historical_evaluation.py`. Existing immutable runs are verified/reused, never silently overwritten. The code requires the pre-test exploratory-protocol-v1 Git tag and exact protocol SHA256. See each manifest for library versions, code/source hashes, candidate traces and protocol commit.

Separate latest-data models are not the evaluated model. Their scope/status is in LATEST_MODELS.json. Do not attach historical scores to them. No prospective, profitability, generalization or G0–G4 claim. Unknown source publication times, vendor historical revisions, sparse events, special sessions and corporate actions remain limitations.
