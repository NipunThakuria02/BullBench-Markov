# All-instrument development results

All six instruments have saved, locally enabled exploratory models. Training cutoff: 2023-03-31. Validation targets: 2023-04-05 through 2023-09-29, 122 sessions per instrument. These are development selection scores, not confirmatory or prospective evidence.

| Instrument | Events | HMM Brier | HMM skill vs prevalence | Lowest validation Brier model |
|---|---:|---:|---:|---|
| HDFCBANK | 8 | 0.0690 | 13.55% | GARCH-t |
| ICICIBANK | 4 | 0.0429 | 28.84% | EWMA |
| NIFTY 50 | 0 | 0.0067 | 83.62% | Persistence |
| RELIANCE | 9 | 0.0720 | 15.09% | HMM |
| TATASTEEL | 5 | 0.0504 | 22.72% | EWMA |
| TCS | 9 | 0.0766 | 9.61% | GARCH-t |

Each run has nine probability comparators and eight secondary price-model comparisons. Nonconverged HMM candidates remain in their run manifests. The original TCS run is retained and reused after input/configuration/integrity checks.

**NIFTY 50:** there are zero positive validation events at its unchanged training-fixed threshold (approximately 1.22% absolute log return). Brier and log loss remain computable; PR-AUC, balanced accuracy and macro-F1 are null/not estimable. The persistence baseline makes no positive calls in this window; its near-zero Brier does not establish useful large-move detection. No dates or event thresholds were changed to manufacture positive examples.

Index observations use an explicit index-close basis; equities retain vendor-adjusted prices. Exploratory observed-session sequences retain existing observations, including known Muhurat dates; types/durations remain unverified for modelling and are not falsely certified as a regular-session calendar. This is not acceptance of D-010 for the frozen official protocol.

Current fitted results, filtered states, transition matrices, convergence records, calibration bins and probability exports are available for every instrument. New-session risk requests still require a reconciled explicit target-session calendar. No data upload is required to view the completed development results.

Reproduce or resume: `python scripts/run_all_development.py --workers 2`. Existing compatible artifacts are checked and reused; incompatible immutable runs are not overwritten. Summaries are derived from saved predictions/manifests. Private snapshots and models stay outside Git.
