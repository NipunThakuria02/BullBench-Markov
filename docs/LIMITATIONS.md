# LIMITATIONS — BullBench MarkovLab

**Status:** living document, 4 Nov 2026. Items are stated as known facts or as risks. Update with measured evidence as it arrives. No model results exist yet.

## A. Scope
1. Research software only. Not investment advice, not a trading system, no profitability claim.
2. Data is completed-session end-of-day. "Latest" means the most recent session with a verified source file, not real-time.
3. Six instruments only (five equities and NIFTY 50). Conclusions do not generalize to other stocks, sectors or markets.

## B. Data
4. Official NSE data access is constrained by NSE terms (no systematic or automated collection on the website without permission). Coverage is limited by what can be obtained and verified manually or with written permission.
5. Corporate actions: bonus and split ex-dates (e.g., HDFC Bank 26 Aug 2025, Reliance 28 Oct 2024) create false price jumps unless handled. The adjustment policy is documented in `CORPORATE_ACTIONS.md`; dividends and other actions are not adjusted unless stated.
6. Special and abbreviated sessions (Muhurat, weekend special sessions) behave differently from regular days. Their treatment is a recorded decision (D-010).
7. HDFC Bank merged with HDFC Ltd in 2023, a structural change in the stock's character. Pre- and post-merger behavior may differ.
8. Legacy BullBench results used Yahoo auto-adjusted prices and a calendar with 69 unresolved audit findings; they are exploratory and not comparable to official-data results.
9. The original full evaluation cannot be re-run from the repository snapshot alone (several cached series are absent).

## C. Modelling
10. HMM state numbers have no stable meaning between fits. Any "calm/volatile" description is post-hoc, with uncertainty.
11. Gaussian emissions understate fat tails; state-count choice and covariance structure change results.
12. Viterbi paths and smoothed probabilities use future data and are retrospective displays only. Only filtered probabilities are forecasts.
13. The large-move target depends on a threshold fixed from training data. If market volatility changes, test prevalence can differ from training prevalence, which affects calibration and Brier comparisons.
14. The event is "large absolute price move", not realized volatility and not a latent regime.
15. Stronger simple models (EWMA/GARCH, logistic on lagged volatility) may match or beat the HMM. That outcome is expected to be possible and is reported as is.
16. Two-stage calibration (if used) makes the HMM a hybrid; this is disclosed.

## C2. Evaluation
17. Test periods contain limited events (roughly one hundred per asset for a two-year window at 20% prevalence, to be verified from actual counts). Differences between models may not be statistically distinguishable.
18. The 2023-10 to 2026-10 window was inspected for the original price-forecast task. For the new target it is "not previously evaluated for this target", not untouched. Only the prospective ledger after the protocol freeze is untouched.
19. Many assets, models and metrics create multiple-comparison risk; only the primary endpoint in the protocol is confirmatory.
20. Bootstrap intervals are conditional on the fitted predictions and the selected assets; models are not refitted inside the bootstrap.
21. Cross-platform numeric differences exist (the legacy XGBoost run differed by up to about 0.002 in decimal return between environments). Reproduction tolerances are defined after the first clean re-run.

## D. Application
22. The website serves saved model bundles; new data updates inference but never retrains models.
23. If the latest verified source is unavailable, the UI shows the last verified date as stale; it never shows generated placeholders.
24. Public display of raw price history depends on the data-licence decision (D-007).
25. Hosted free tiers may add latency or cold starts; no latency target is claimed before measurement.

## E. Not yet verified (to be replaced by evidence)
- Whether the exchange previous-close field is corporate-action adjusted in the actual files (D-003).
- Exact date ranges obtainable per asset.
- Identity of weekend/odd dates flagged in the legacy audit.
- Reproduction tolerance across machines.
