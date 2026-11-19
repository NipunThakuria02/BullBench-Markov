# RULES — Non-negotiable engineering and scientific constraints

## A. Academic integrity and provenance
1. **Real observations only** for train, validation and test. No synthetic price rows, synthetic labels, SMOTE, made-up dates, generated returns or imputation across missing trading periods.
2. Use primary official NSE/NSE Indices sources where permitted. A public webpage is not an automatic data-storage/republication license. Record terms and attribution.
3. Do not call Yahoo Finance data official NSE data. Any emergency fallback requires explicit discussion and a changed source disclosure.
4. Do not invent backtest results, chart values, citations, model accuracies, endpoints or update timestamps.
5. Original BullBench artifacts remain intact. New project is a derivative with code provenance and distinct objective.

## B. Leakage and validity
6. For a forecast made after session t, use only observations and public metadata available by the end of t.
7. Do not `fit()` scalers, PCA, thresholds, imputers, HMMs or supervised models on validation/test observations.
8. No random shuffled train/test split, no smoothing output for forward-time prediction, no leakage via future state labels.
9. Large-move event target must be explicit and evaluable. Hidden state ID is **never** a ground-truth class label.
10. Pick all thresholds, hyperparameters and probability calibration from training/validation only; leave final test untouched until lock.
11. Never use current-day close to predict the same day's close and call it a next-day prediction.
12. Report preprocessing rejections, unsuccessful models, convergence problems and negative results.

## C. Data quality
13. Maintain raw immutable original downloads, checksums and a canonical normalized output.
14. Validate equity series, listing dates, price/volume data types, OHLC invariants, date gaps and official holidays.
15. No forward fill over suspended/untraded stock sessions. Do not remove genuine extreme returns without evidence of bad data.
16. Resolve corporate actions or consistently redefine the target. Do not mix adjusted and unadjusted prices.
17. Use separate adapters for pre- and post-July-2024 NSE bhavcopy formats; fail clearly on unknown schemas.
18. Include source identity, retrieval time, observation time and version in all datasets and model outputs.

## D. Unit 4 correctness
19. Implement Gaussian HMM, EM/Baum-Welch fit, stable forward, backward, forward-backward and Viterbi; document meanings and numerical checks.
20. Filtering is `P(state_t | observations_1:t)`; smoothing is `P(state_t | observations_1:T)` for T>t. Only filtering is permissible in real-time inference.
21. Viterbi decodes the retrospective most likely path; it does not itself predict future price or future regime truth.
22. Model next-session risk from causal state filtering plus transition/emission assumptions; verify probability calibration.
23. HMM numeric state labels have no stable meaning between runs. Interpret states after fitting and show uncertainty.
24. Compare baselines on common target/date pairs; don't treat HMM likelihood and supervised F1 as interchangeable.

## E. Software and UX
25. The deployed website must call Python FastAPI for inference; no fake `setTimeout()` predictions or only static `results.json`.
26. Retain selected model version and preprocessing artifact; never retrain on each viewer request.
27. New market data must pass validation before it changes published state or forecast. If ingestion fails, keep prior verified version visibly stale.
28. API must validate instruments, payload size, date format, data types and rate limits. Do not commit auth tokens, secrets or raw licensed datasets to public GitHub.
29. Feature processing in inference must match training exactly. Prefer serialized pipelines and schema validation.
30. Prefer simple, debuggable code with tests. Record every material algorithm, dataset or definition change.
31. No simulated live tickers; label completed-session EOD data honestly.
32. Add a non-investment-advice notice and no buy/sell order UI.

## F. Gate criteria
- **G0:** Validated official data and permissible use documented.
- **G1:** All Unit 4 algorithm tests passing.
- **G2:** Real out-of-time comparative evaluation reproducible.
- **G3:** Fresh authentic observation -> API -> prediction -> UI demonstrated.
- **G4:** Independent end-to-end reproduction and limitations documented.

## Pull request checklist
- [ ] Source/target/as-of dates documented
- [ ] Tests and data-audit checks passed
- [ ] No time leakage introduced
- [ ] Model metrics reproduced from saved predictions
- [ ] No fabricated/redistributed restricted data
- [ ] UI states freshness and uncertainty honestly
