# SECURITY — BullBench MarkovLab

**Status:** TARGET policy, 4 Nov 2026. Items marked [ ] are not yet implemented. Scope: a public research website with a read-only inference API. No user accounts, no personal financial data.

## 1. Assets to protect
1. Integrity of data, models and published forecasts (a wrong or stale number shown as fresh is the main harm).
2. Licensed/raw market files and permissions status.
3. Server secrets and the model registry.
4. Availability of the API under abuse.

## 2. Threats and controls
| Threat | Control |
|---|---|
| Tampered or malformed data file | Checksum manifest, schema validation, OHLC invariants, atomic commit, fail closed, keep previous verified version as stale |
| Malicious upload (path traversal, zip bomb, formula injection, oversized file) | No public upload in v1 (D-009). Any admin import: size limit, extension and signature check, ignore client filename, no execution, parse in a temp dir |
| Unauthorized retraining or promotion | No training or promotion endpoint exists. Offline scripts only |
| Injection via query/path/JSON | Pydantic validation, allow-list of instruments, strict ISO date format, bounded payload size, typed enums for `view` |
| Abuse / scraping of the API | Rate limiting per client, response caching keyed by model+data version, pagination caps on history endpoints |
| Cross-site abuse | CORS allow-list of exact origins, no wildcard with credentials |
| XSS / clickjacking | Strict CSP (no remote scripts), `X-Content-Type-Options`, `X-Frame-Options`/`frame-ancestors`, no `dangerouslySetInnerHTML` with API text |
| Secret leakage | Secrets in server env only, `.env.example` placeholders, secret scanning in CI, never in the client bundle or repo |
| Vulnerable dependencies | Pinned lockfiles, scheduled `pip-audit` and `npm audit`, review before upgrading |
| Model/bundle substitution | Immutable versioned bundles, manifest hash checked at startup, atomic pointer switch, read-only mount in production |
| Misleading output | Forecast responses always carry target definition, `as_of_session`, freshness, model version and warnings; stale state visible in UI |

## 3. API rules
- [ ] Validate instrument against `config/assets.yaml`; unknown values return 4xx.
- [ ] Validate as-of date format and range; reject future dates and non-sessions.
- [ ] Limit request body size and history window size.
- [ ] Return generic error messages to clients; details go to server logs.
- [ ] Never return a probability without its target definition.
- [ ] No endpoint mutates data or models from a public request.

## 4. Data and licence handling
- [ ] Raw NSE files stay in `data/raw/` (git-ignored); only manifests (hashes, metadata) are committed.
- [ ] Permission/terms status recorded in `DATA_SOURCES.md`; automated collection only with written permission.
- [ ] Public serving of raw OHLC resolved in D-007 before the history endpoint is exposed.
- [ ] Attribution to NSE shown where NSE-derived data appears.

## 5. Repository hygiene (do now)
- [ ] Run `git ls-files docs/cache` and `git ls-files | grep -i -E "cookies|\.db$"`. The snapshot contains `docs/cache/.yfinance/cookies.db` and `tkr-tz.db`.
- [ ] If tracked, remove them and purge history (e.g., `git filter-repo`), then rotate nothing is needed unless real credentials were present; confirm contents first.
- [ ] Extend `.gitignore`: `docs/cache/`, `*.db`, `.env`, `data/`, `model_registry/` (if private), `imports/`.
- [ ] Add a LICENSE and attribution notes for the BullBench-derived code.
- [ ] Enable GitHub secret scanning and Dependabot alerts.

## 6. Logging and monitoring
- Log: import attempts and outcomes, readiness failures, model version per response, rate-limit hits.
- Do not log secrets or full request bodies.
- Keep logs for a documented period (TBD).

## 7. Incident response (minimum)
1. If wrong data was published: switch the active data version back to the last verified one, mark the UI stale, record in DECISIONS.md.
2. If a secret leaked: revoke and rotate it, remove from history, check logs.
3. If NSE or another provider objects to data use: take the affected endpoints/files offline, preserve the permission record.

## 8. Reporting a vulnerability
Contact: `TBD (add maintainer email or GitHub security advisory link)`. Please do not open public issues for undisclosed vulnerabilities.

## 9. Release security checklist
- [ ] CSP/CORS restricted to production origins
- [ ] Rate limiting enabled and tested
- [ ] Input validation tests pass (`tests/test_inference_contract.py`, API validation tests)
- [ ] Dependency audits clean or exceptions recorded
- [ ] No secrets or raw licensed data in repo, build output or logs
- [ ] Bundle hash verified at startup
