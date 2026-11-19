# Calendar evidence and remaining reconciliation

The owner supplied six PDFs. They identify themselves as NSE **Capital Market Segment trading-holiday** circulars, not clearing-holiday lists. Original bytes are stored privately under `data/calendar_evidence/<evidence_hash>/originals/`, with SHA-256 references in `evidence.json`. Website retrieval times and exact publication timestamps remain unknown; publication dates are explicitly printed in the circulars. No NSE website was downloaded automatically.

| Calendar year | File | Printed publication date | Table records |
|---|---|---|---|
| 2021 | CMTR46623.pdf | 2020-12-11 | 19 |
| 2022 | CMTR50560.pdf | 2021-12-10 | 18 |
| 2023 | CMTR54757.pdf | 2022-12-08 | 19 |
| 2024 | CMTR59722.pdf | 2023-12-12 | 19 |
| 2025 | CMTR65587.pdf | 2024-12-13 | 18 |
| 2026 | CMTR71775.pdf | 2025-12-12 | 19 |

Records include holidays falling on weekends and Muhurat exceptions, so counts are not counts of closed weekdays. These are annual notices; they are not proof that no later amendment occurred.

## Findings

- The annual notices expressly announce Muhurat trading on 2021-11-04, 2022-10-24, 2023-11-12, 2024-11-01 and 2025-10-21. These dates are present in the supplied NIFTY data. Do not discard them as holidays. Session timings and the modelling treatment of abbreviated sessions remain unresolved.
- The 2026 notice announces Muhurat on 2026-11-08, beyond this dataset's 2026-10-16 endpoint; it is not inserted into observations or forecasts.
- 2023-11-12, previously flagged as a weekend NIFTY-only date, now has explicit annual-notice support as a Muhurat session.
- The 2023 notice lists 2023-06-28 as a closure. Both the NIFTY data and stock caches contain an observation on that date and none on 2023-06-29. A later amendment is needed to establish which closure applied. No shift or data correction is inferred automatically.
- Candidate weekdays absent from NIFTY but not listed as closed in these annual notices: 2023-06-29, 2024-01-22, 2024-05-20, 2024-11-20, 2026-01-15. These are potential calendar amendments to investigate, not automatically missing prices.
- The supplied screenshot shows a 2026-01-15 election closure. The earlier December-2025 annual PDF does not include it. The screenshot corroborates that the annual list is incomplete; a dated amendment circular is still needed for reproducible source evidence. Yahoo stock rows for this date remain unchanged and flagged.
- Weekend observations requiring separate notices: 2024-01-20, 2024-03-02, 2024-05-18, 2025-02-01 and 2026-02-01. Their presence in price files does not establish their official session type or duration.

Full per-instrument comparisons and source hashes: `CALENDAR_AUDIT.json`. No price rows, fitted models, experiment splits or target definitions changed. The protocol remains unfrozen, G0 is pending, and no executable “verified” calendar was generated from provisional evidence.

## Targeted follow-up files

The annual notices are complete for the six requested years; do not redownload them. In [NSE Circulars](https://www.nseindia.com/resources/exchange-communication-circulars), use the Capital Market segment and search by date/topic:

1. Revision to Bakri Id trading holiday in June 2023 (28/29 June).
2. Additional closures for 22 January, 20 May and 20 November 2024, and 15 January 2026.
3. Special trading-session notices for 20 January, 2 March and 18 May 2024, 1 February 2025, and 1 February 2026.
4. Muhurat timing circulars only where needed to establish session duration for modelling; the annual PDFs already announce their dates.

Do not supply a clearing-only circular as a substitute for an equity trading-session notice.

## Reproduce the audit

Requires `pdftotext` (Poppler), available in this environment. From repository root:

```bash
python -m nse_forecast.ingest.calendar_evidence --files imports/calendar/CMTR*.pdf
```

The command validates years/segment, hashes and preserves the PDFs, extracts the annual claims, and audits all six imported assets without changing observations. Repeat identical evidence reuses the immutable evidence directory. Candidate weekdays are explicitly unverified and never fed directly into forecasting.
