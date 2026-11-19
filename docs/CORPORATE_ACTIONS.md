# Corporate actions

Status: unverified; no official-data adjustment policy has been validated.

The official parser preserves raw published close and same-file previous close. It does not assume the latter is action adjusted. D-003 remains subject to empirical ex-date verification. Required evidence: original report, published previous close, original prior session close, action announcement and ratio, expected return denominator, and resulting reconciliation. The supplied NSE corporate-action exports now corroborate HDFCBANK 2025-08-26 and RELIANCE 2024-10-28 bonus ex-dates, and identify TATASTEEL’s split ex-date as 2022-07-28. Event evidence is not a verification of official previous-close adjustment.

The authorized exploratory track uses Yahoo auto-adjusted OHLC and consistently computes close-to-close log returns. Yahoo histories may be revised and must not be mixed with official raw equity closes. NIFTY 50 index points are a separate instrument, never pooled as currency errors.

Price backtests refuse comparisons when next-file previous close differs from current close until an as-of action-factor contract is available. Future previous-close fields are never used to reconstruct a forecast. Official raw-close serving remains blocked for the same reason. Exploratory HMM next-close inference is on the adjusted vendor/index basis and labelled accordingly.

## Supplied event exports

Six owner-supplied CSVs (including a supplemental TCS export) contain 61 records: 48 with ex-dates inside 2021-10-01–2026-10-16 and 13 older RELIANCE records. All original bytes and all rows are preserved privately under data/corporate_action_evidence/. Only the audit is scoped; the source files were not trimmed. The export dates in filenames are not treated as download or announcement timestamps.

| Instrument | Total rows | In-scope rows | Note |
|---|---:|---:|---|
| HDFCBANK | 7 | 7 | 1:1 bonus, ex-date 2025-08-26 |
| ICICIBANK | 5 | 5 | Dividend records |
| RELIANCE | 20 | 7 | 1:1 bonus 2024-10-28; demerger 2023-07-20; older rows retained |
| TATASTEEL | 6 | 6 | Face-value split from ₹10 to ₹1, ex-date 2022-07-28 |
| TCS | 23 | 23 | Two exports, now extending to 2021-10-14; no overlapping event dates |

The four in-scope structural events have an ex-date observation and an earlier observation in the existing Yahoo-adjusted caches. This establishes availability for later checking, not correctness of a published official previous-close field. No adjustment factor, price edit, return calculation or model refit was made during evidence import. The RELIANCE demerger needs its own reconciliation; a bonus/split ratio cannot stand in for a demerger adjustment. Current face value is not used to infer historical adjustment factors.

## TCS coverage follow-up received

The original TCS CSV had exactly 20 entries and stopped at 25 May 2022. The owner supplied the requested 1 October 2021–30 April 2022 export. It adds three records: interim dividends on **2021-10-14** and **2022-01-19**, and a buyback on **2022-02-22**. There are no overlapping ex-dates with the original file. Both original CSVs and their per-event source hashes are preserved. TCS now has 23 supplied events within the requested full period; the specific earlier-export request is addressed, and no additional TCS export is requested for this check. This does not certify independent completeness or price-adjustment policy.

All instruments’ event-list completeness remains unverified. Ex-date and record date do not establish when an announcement became public, so these event files must not create hindsight-only historical predictors. Retrieval and publication timestamps remain unknown. Data usage and public-display rights are not inferred from the exports.

## Reproduction

```bash
python -m nse_forecast.ingest.corporate_actions --files imports/actions/CF-CA*.csv
```

The importer requires supported EQ-series exports for all five stocks and accepts multiple nonoverlapping chunks for an instrument. Cross-file overlapping ex-dates and repeated export bytes fail closed for explicit reconciliation. It rejects malformed schemas, duplicate records, invalid face values and dates. Exact originals and normalized event evidence are content-addressed and immutable; rerunning identical inputs is idempotent. See CORPORATE_ACTION_AUDIT.json for source hashes, coverage counts and structural-event checks. G0 and D-003 remain unresolved.
