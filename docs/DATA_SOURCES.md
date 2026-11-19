# Data input guide

## Current source decision
The owner explicitly authorized Yahoo Finance stocks plus a manual NSE Indices NIFTY 50 export for **exploratory** work. These are separate from official-data validation. Yahoo-adjusted prices must never be described as official NSE prices. No NSE website downloads are automated.

Five original stock caches have been imported locally with original retrieval metadata and checksums. Each has 1,247 rows ending 2026-10-16. They are legacy observations, not fresh data. The new Yahoo download attempt was blocked by the environment proxy (HTTP 403); it did not refresh these inputs. The owner has supplied six NIFTY 50 CSV chunks, now imported as 1,251 unique sessions spanning 2021-10-01 through 2026-10-16. See NIFTY_IMPORT_AUDIT.json; calendar differences remain unresolved. Source display/republication permission remains unverified.

## What you need to supply manually

1. NIFTY 50 historical CSV from NSE Indices, Reports → Historical Data: https://www.niftyindices.com/reports/historical-data . Supported headers: `Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value` or the observed daily export `Index Name,Date,Open,High,Low,Close`. Select **NIFTY 50**, not a TRI or sector series. Keep the export exactly as downloaded. If its headers differ, provide the original file so the adapter can be reviewed; do not rename fields to force acceptance.
2. For the official-only track: NSE equity bhavcopy files from https://www.nseindia.com/all-reports for HDFCBANK, ICICIBANK, TCS, RELIANCE, TATASTEEL, EQ series. Before 2024-07-08 use the historical CM bhavcopy schema; from that date use CM-UDiFF Common Bhavcopy Final. The parser's current schemas require verification against your actual files.
3. Official calendars, special-session notices and corporate-action reports for the covered period. Prioritize split/bonus evidence for HDFCBANK and RELIANCE and verify TATASTEEL's split date. Do not guess adjustments from extreme returns.
4. Actual retrieval time, source publication time when verified, source URL, and the usage/permission record. Missing publication metadata is allowed only in the explicitly exploratory track and is labelled unverified.

Aim for 2015 onward if available; actual verified coverage governs the dataset. There is no need to type prices into chat. Save CSV files under local, ignored `imports/`. Never upload cookies or tokens.

## Commands (from repository root)

Use the activated Python environment. Yahoo fetch has explicit bounds; it does not train or evaluate:

```bash
python -m nse_forecast.ingest.exploratory download-stocks --start 2015-01-01 --end YYYY-MM-DD
```

Import one or more manually downloaded NIFTY CSVs, substituting your **actual** retrieval timestamp if known (omit `--retrieved-at` to record it as unknown):

```bash
python -m nse_forecast.ingest.exploratory import-nifty --file imports/nifty50-2021.csv imports/nifty50-2022.csv --retrieved-at ACTUAL_ISO_TIMESTAMP_WITH_OFFSET
```

Official file validation is read-only by default. Add `--commit` only to save an immutable local snapshot (this does not approve G0):

```bash
python -m nse_forecast.cli import-official --file imports/report.csv --format nse-udiff --asset TCS --source-url https://www.nseindia.com/all-reports --retrieved-at ACTUAL_ISO_TIMESTAMP_WITH_OFFSET --published-at ACTUAL_ISO_TIMESTAMP_WITH_OFFSET
```

Supported official formats: `nse-legacy`, `nse-udiff`, `nifty-index`. Unrecognized schemas, duplicate sessions, invalid prices or incompatible format dates fail closed. No forward filling, row synthesis or guessed corporate-action adjustments occur.

Snapshots contain `source.csv`, `bars.csv`, `manifest.json`, `audit.json`. Checksums link source bytes to normalized bytes. Files are read-only and content-addressed; repeated identical imports reuse the snapshot, and tampering is rejected. New full-history downloads overlap existing snapshots: choose a new snapshot root or reconcile explicitly. Do not silently merge duplicates.

## Calendar file
A JSON list of explicit session dates and types: `[{"session_date":"<actual ISO session>","session_type":"regular"}, ...]`. It must be sorted and unique and include the forecast target session. Current modelling refuses special-session sequences pending a supported policy. Exploratory development may use the observed vendor calendar with an explicit unverified-calendar caveat; serving requires a supplied calendar.

## Boundaries
Official source URLs do not prove file authenticity or permission. No G0 pass is claimed. Licensed raw data and model artifacts are ignored by Git. Public OHLC history is disabled. The data directories are private local development inputs, not static web assets.

## Supplied NIFTY 50 batch

Six CSVs were imported without editing the originals. Schema and OHLC checks passed; 1,251 unique sessions cover 2021-10-01 to 2026-10-16. Batch parsing orders dates chronologically, derives previous close across file boundaries only for the exploratory track, and leaves the first previous close unavailable. Every normalized row identifies its original input checksum. Download/publication times are unknown and stored as null. Exact source files are retained under the private snapshot originals/ directory. source.csv is an explicitly labelled derived concatenation, not falsely presented as one original download.

Six weekend observations were retained for review; they are not automatically marked invalid. Five dates appear in NIFTY but not the legacy stock caches, and 2026-01-15 appears in stocks but not NIFTY. See NIFTY_IMPORT_AUDIT.json. This is a cross-source comparison, not an official holiday or special-session calendar. G0 remains pending and no rows have been filled or removed.

## Holiday PDFs received
All six annual Capital Market trading-holiday circulars for 2021–2026 are now preserved and audited. These annual schedules do not include all subsequent amendments or exceptional trading sessions. See CALENDAR_EVIDENCE.md for the verified source mapping, conflicts and targeted follow-up notices; CALENDAR_AUDIT.json contains per-instrument findings. No price observations have been deleted, filled or reclassified as regular sessions.

## Corporate-action exports received
The five stocks’ six exports, including the requested early TCS supplement, have been preserved and audited (61 original events, 48 in the requested ex-date window). The earlier TCS request is addressed; its two exports contain 23 distinct events. See CORPORATE_ACTIONS.md and CORPORATE_ACTION_AUDIT.json. Official bhavcopy previous-close adjustment still requires separate ex-date price-file evidence; event records alone do not establish it.
