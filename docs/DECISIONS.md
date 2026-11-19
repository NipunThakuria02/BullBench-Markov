# DECISIONS — BullBench MarkovLab

Lightweight decision log (satisfies RULES #30: record every material algorithm, dataset or definition change).
Statuses: **Open** (undecided), **Proposed** (recommended, not yet accepted), **Accepted**, **Superseded**.
Only entries explicitly approved by the owner and dated below are Accepted.

## Template
```
### D-XXX  Title
- Status: Open | Proposed | Accepted | Superseded by D-YYY
- Date:
- Context:
- Options considered:
- Decision:
- Consequences / what must change:
- Verification (test, doc or file that proves it):
```

## Index
| ID | Title | Status |
|---|---|---|
| D-001 | Keep `nse_forecast` package and CLI name during migration | Accepted |
| D-002 | Own NumPy HMM is the deliverable; hmmlearn is test oracle only | Proposed |
| D-003 | Return defined via exchange previous-close field | Proposed |
| D-004 | Manual-first official data ingestion | Accepted |
| D-005 | Primary target, fixed θ, and mandatory volatility baselines | Proposed |
| D-006 | One gate naming scheme (G0–G4) | Proposed |
| D-007 | Public serving of raw OHLC history | Open |
| D-008 | Final-test wording and prospective ledger | Proposed |
| D-009 | No public upload endpoint in v1 | Proposed |
| D-010 | Special/abbreviated session policy | Open |
| D-011 | Scope and date range of v1 data | Open |

---

### D-001  Keep `nse_forecast` package and CLI name during migration
- Status: Accepted
- Date: 2026-11-04
- Approval: Owner explicitly accepted in this session.
- Context: ARCHITECTURE_EXTENDED §4 recommends not combining a rename with new ML features.
- Decision: Keep `src/nse_forecast` and the `nse-forecast` entry point; rename only as a separate later change with all tests green.
- Consequences: new code lives in `unit4/`, `experiments/`, `ingest/`, `artifacts/` subpackages.

### D-002  Own NumPy HMM is the deliverable; hmmlearn is test oracle only
- Status: Proposed
- Context: PRD suggests hmmlearn; RULES #19 requires implementing Baum-Welch, forward, backward, forward-backward and Viterbi. Library posterior routines may be full-sequence smoothing, which is a leakage risk if used in inference (verify against hmmlearn docs before relying on either claim).
- Decision (proposed): Implement algorithms in `unit4/` in log-space/scaled form. Use hmmlearn only to cross-check likelihoods and Viterbi paths in tests.
- Verification: `tests/test_hmm_forward_backward.py`, `tests/test_hmm_viterbi.py`, `tests/test_hmm_no_lookahead.py`, hand example fixture.

### D-003  Return defined via exchange previous-close field
- Status: Proposed
- Context: Raw close-to-close returns turn bonus/split ex-dates into false ~−50% to −90% moves (HDFCBANK 1:1 bonus ex-date 2025-08-26; RELIANCE 1:1 bonus ex-date 2024-10-28; TATASTEEL split date to be verified).
- Decision (proposed): `r_t = ln(Close_t / PrevClose_t)` from the same official file, **only after** verifying on known ex-dates that the field is adjusted. Otherwise use a documented adjustment-factor table.
- Verification: ex-date check table in `CORPORATE_ACTIONS.md`; test `test_corporate_action_returns`.

### D-004  Manual-first official data ingestion
- Status: Accepted
- Date: 2026-11-04
- Approval: Owner explicitly accepted in this session.
- Context: NSE website terms prohibit systematic/automated collection; automation is not assumed permitted.
- Decision: Ingestion is manual file import with checksum manifest. Any automation requires written permission recorded in `DATA_SOURCES.md`.
- Consequences: `refresh_after_close.py` stays disabled/optional; G3 demo uses a manually imported new-session file.

### D-005  Primary target, fixed θ, and mandatory volatility baselines
- Status: Proposed
- Decision (proposed): θ per asset fixed from the first training block (80th percentile of |r|), not per fold. EWMA and GARCH(1,1)-t baselines are mandatory comparators. Details in `EXPERIMENT_PROTOCOL.md`.

### D-006  One gate naming scheme (G0–G4)
- Status: Proposed
- Context: PRD/RULES use G0–G4, ARCHITECTURE_EXTENDED uses M0–M5, WORKFLOW uses milestones 0–7. "G0" and "M0" mean different things.
- Decision (proposed): G0–G4 are the only gates. Map M0–M5 and milestones 0–7 to them or delete them.

### D-007  Public serving of raw OHLC history
- Status: Open
- Context: RULE 28 forbids raw licensed data in public GitHub; `/v1/assets/{asset}/history` and the Asset Explorer would serve raw OHLC publicly. Existing `web/public/history/*.json` appear derived from Yahoo caches.
- Options: (a) serve only derived series (returns, probabilities, states); (b) serve raw only with written permission; (c) gate raw charts behind access control or local-only mode.
- Decision: pending faculty/NSE guidance.

### D-008  Final-test wording and prospective ledger
- Status: Proposed
- Context: 2023-10 to 2026-10 was inspected for the original price task.
- Decision (proposed): call that window "not previously evaluated for this target", never "untouched". Freeze the protocol and bundle, then log forecasts for sessions after 2026-10-16 as the only truly untouched evidence.

### D-009  No public upload endpoint in v1
- Status: Proposed
- Decision (proposed): `POST /v1/data/validate-upload` is removed from the public API. Validation and commit are CLI/admin actions. Revisit only with an authentication design.

### D-010  Special/abbreviated session policy
- Status: Open
- Context: Audit flags weekend dates (e.g., 2023-11-12, 2024-01-20) that are probably special or Muhurat sessions (unverified).
- Options: exclude from targets and rolling windows; include with flag; include only in raw data.

### D-011  Scope and date range of v1 data
- Status: Open
- Context: PRD targets 2015 onward. Acquisition effort and corporate-action reconciliation grow with range; no deadline is recorded.
- Options: 2015+, 2018+, or 2021+ for v1 with extension later.
- Decision: pending deadline and permission outcome.

### D-012 Exploratory Yahoo/manual-index track and implementation scope
- Status: Accepted
- Date: 2026-11-04
- Approval: Owner explicitly selected “Use Yahoo + manual NIFTY 50 for exploratory work” and requested implementing the new features without routine permission prompts.
- Decision: Keep official validation separate; add an explicitly exploratory Yahoo-adjusted equities/manual NSE Indices track. Build and test the software across the planned components while real-data gate evidence is pending. Do not claim gates passed from implementation alone.
- Consequences: No silent data-source substitution. Original hard-coded date profile remains legacy-only. Development runs use explicit dates; no protocol freeze, final-test or prospective evaluation has been authorized by this decision. Model/UI artifacts must disclose exploratory status.
- Verification: source manifests, config/exploratory-tcs.json, new ingestion/HMM/API/browser tests, docs/IMPLEMENTATION_STATUS.md.

### D-013 Import supplied NIFTY 50 chunks into the exploratory track
- Status: Accepted
- Date: 2026-11-04
- Approval: Owner supplied the six requested files for integration; this implements the already accepted D-012 source choice.
- Decision: Support the observed NSE Indices daily CSV schema alongside the existing verbose schema; validate the complete batch before saving, reject all overlapping dates, preserve exact originals and row-level source hashes, and keep unspecified source timestamps null.
- Consequences: This adds index observations without changing the research target, threshold, frozen protocol, or special-session policy. Weekend and cross-source date differences remain unresolved audit items.
- Verification: tests/test_nifty_batch.py and docs/NIFTY_IMPORT_AUDIT.json.

### D-014 Preserve annual trading-holiday circulars as provisional evidence
- Status: Accepted
- Date: 2026-11-04
- Approval: Owner supplied the requested annual holiday PDFs for processing, under the existing instruction to proceed with routine implementation.
- Decision: Extract and preserve the six Capital Market annual notices, including explicit Muhurat exceptions; audit against observed dates without declaring a complete calendar or changing rows. Later amendments remain required where annual claims and observations conflict.
- Consequences: This does not settle D-010 special-session modelling policy, amend return definitions, or authorize dropping holiday/special-session observations. No protocol freeze or G0 approval.
- Verification: tests/test_calendar_evidence.py, docs/CALENDAR_AUDIT.json and docs/CALENDAR_EVIDENCE.md.

### D-015 Preserve corporate-action evidence separately from price adjustments
- Status: Accepted
- Date: 2026-11-04
- Approval: Owner supplied the five requested corporate-action exports for integration, under the standing instruction to proceed with routine implementation.
- Decision: Preserve all raw event records with checksums; scope the audit by ex-date, retain out-of-range records privately, flag possible TCS export truncation, and record bonus/split/demerger events without applying factors or inferring announcement timestamps.
- Consequences: D-003 is not accepted or verified by event presence. Official price files, action-specific adjustment reconciliation and source-availability timing remain required. No change to the target, model, protocol or final-test window.
- Verification: tests/test_corporate_actions.py and docs/CORPORATE_ACTION_AUDIT.json.

### D-016 Reconcile the supplied early TCS supplement
- Status: Accepted
- Date: 2026-11-04
- Approval: Owner supplied the specifically requested TCS 2021-10-01–2022-04-30 export for integration.
- Decision: Extend event evidence with the three earlier TCS records, retaining both original files and event-source hashes. Permit multiple chunks per instrument only when ex-dates do not overlap; repeated exports and conflicts require explicit reconciliation.
- Consequences: The targeted earlier-export request is addressed. Independent completeness and price adjustment remain unverified. No return, target, price, model, protocol-freeze or final-test change.
- Verification: tests/test_corporate_actions.py, docs/CORPORATE_ACTION_AUDIT.json.

### D-017 Top-level MarkovLab within the original BullBench design
- Status: Accepted
- Date: 2026-11-04
- Approval: Owner explicitly selected MARKOVLAB beside HOME and requested clear results while preserving the existing frontend design.
- Decision: Reuse the original shell and visual components; add dedicated lab routes carrying the selected instrument. Display actual saved development scores with evaluation dates, calibrated-probability caveats, baseline comparisons, diagnostics and unavailable states.
- Consequences: No UI-generated predictions or hard-coded metrics. Checksums and saved-prediction metric reproduction gate serving. Four float32 ULPs accommodate the older XGBoost score-reduction precision; displayed scores are recomputed from CSV predictions. No change to training, targets or final-test policy.
- Verification: tests/test_lab_api.py, web/tests/markov.spec.ts, real saved TCS bundle/API/browser smoke check; original dashboard browser suite retained.

### D-018 Complete all six exploratory development runs without changing the test policy
- Status: Accepted
- Date: 2026-11-04
- Approval: Owner explicitly requested running MarkovLab for every stock/instrument without routine permission prompts.
- Decision: Keep the TCS development dates, training-quantile event target, state grid and seeds for all instruments; use an explicit NIFTY index-point return basis; retain observed sessions as exploratory/unverified rather than certify regular-session types. Reuse compatible TCS artifacts.
- Consequences: The one-class NIFTY validation window is valid for Brier/log-loss but not class-dependent ranking/classification metrics, which remain null. Thresholds/dates are not tuned to create positives. No final-test or prospective evaluation, protocol freeze, or official G0 approval. Batched stable transition-count arithmetic is numerically checked against reference recursions and changes performance, not the HMM equations.
- Verification: tests/test_hmm.py, tests/test_lab_features.py, web/tests/markov.spec.ts, scripts/run_all_development.py, docs/ALL_INSTRUMENT_RESULTS.md/json, and all six checked private model bundles.

### D-019 Separate reproducible local distributions from public deployment source
- Status: Accepted
- Date: 2026-11-05
- Approval: Owner asked to verify the apparently missing distribution files and update local/Vercel deployment files.
- Decision: Track launch/deployment helpers in Git; keep generated frontend, datasets and model bundles out of public source. Produce explicitly labelled source, private local and private backend-data archives with content manifests. Keep the accepted exploratory data path explicit. Public Vercel builds use a separate output and a branding-only public directory, enforcing actual backend-origin/CSP matching.
- Consequences: Source ZIPs do not pretend to contain private model/data artifacts. Local packages remain runnable with provided data. Hosted frontend needs an actual backend URL; backend needs private persistent storage and exact CORS. No live deployment, training, protocol or scientific-gate change.
- Verification: scripts/check_distribution.py, scripts/package_release.py, isolated public-build sentinel test, launcher/extracted-package tests, Docker/backend smoke test where available.

### D-020 Authorize locked exploratory historical test and restore local legacy views
- Status: Accepted
- Date: 2026-11-05
- Approval: Owner explicitly requested completing the proposed final-evaluation work, newer training and fixing missing original dashboard values.
- Decision: Freeze a separate exploratory historical protocol, not the incomplete official protocol. Use chronological fit through December 2024, validation in 2025, and locked 2026 historical testing with at least 60-origin embargoes. Retain the first-training-block event threshold. Report this track as exploratory and the historically inspected window as not untouched. Preserve earlier development artifacts. A separate newest-data model has no test score.
- Consequences: User approval authorizes test access; it does not supply missing calendar amendments, official previous-close reconciliation, redistribution rights or independent reproduction. G0–G4 and official protocol freeze stay pending. Restore original local static results/history via an explicitly enabled local-only API and include their checksummed files in the owner-requested data archive. Do not expose raw history by default on hosted services.
- Verification: docs/EXPLORATORY_PROTOCOL_V1.md, historical configs, split/lock tests, saved prediction checksums and API/browser regression checks.

### D-021 Owner-requested archive branch for local installation
- Status: Accepted
- Date: 2026-11-05
- Approval: Owner explicitly instructed pushing data.zip and model_registry.zip unchanged to a new GitHub branch because chat downloads failed, and subsequently requested updated evaluation and restoration of original dashboard values.
- Decision: Keep the source main branch free of raw data/model files; maintain the two owner-requested downloadable archives on local-data-models with matching source. The data archive includes the original local legacy-site payload needed for dashboard values. Preserve archives' folder layout and validate checksums before publishing.
- Consequences: GitHub branch contents are accessible according to repository visibility. This owner direction supersedes the earlier source-only packaging preference for these two archives; it does not establish provider redistribution permission or enable hosted raw-history serving by default.
