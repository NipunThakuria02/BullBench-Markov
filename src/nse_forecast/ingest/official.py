"""Strict, versioned CSV adapters. No network access or inferred price adjustments."""
import csv
import io
from datetime import datetime

import numpy as np
import pandas as pd

EQUITIES = ('HDFCBANK', 'ICICIBANK', 'TCS', 'RELIANCE', 'TATASTEEL')
ASSETS = (*EQUITIES, 'NIFTY 50')
ADAPTER_VERSION = '2'
FORMATS = {
    'nse-legacy': {
        'session_date': 'TIMESTAMP', 'open': 'OPEN', 'high': 'HIGH',
        'low': 'LOW', 'close': 'CLOSE', 'previous_close': 'PREVCLOSE',
        'volume': 'TOTTRDQTY',
    },
    'nse-udiff': {
        'session_date': 'TradDt', 'open': 'OpnPric', 'high': 'HghPric',
        'low': 'LwPric', 'close': 'ClsPric', 'previous_close': 'PrvsClsgPric',
        'volume': 'TtlTradgVol',
    },
    'nifty-index': {
        'session_date': 'Index Date', 'open': 'Open Index Value',
        'high': 'High Index Value', 'low': 'Low Index Value',
        'close': 'Closing Index Value',
    },
}


def parse_session(value):
    """Explicit formats avoid ambiguous month/day inference."""
    for pattern in ('%Y-%m-%d', '%d-%b-%Y', '%d %b %Y', '%d/%m/%Y'):
        try:
            return datetime.strptime(value.strip(), pattern).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f'Unsupported session date: {value!r}')


def parse_export(raw: bytes, report_format: str, asset: str) -> pd.DataFrame:
    if report_format not in FORMATS:
        raise ValueError('Unknown report format; no schema guessing is allowed')
    if asset not in ASSETS:
        raise ValueError('Unsupported study asset')
    index_report = report_format == 'nifty-index'
    if index_report != (asset == 'NIFTY 50'):
        raise ValueError('NIFTY 50 requires the separate index-history adapter')
    text = raw.decode('utf-8-sig')
    headers = next(csv.reader(io.StringIO(text)), [])
    headers = [header.strip() for header in headers]
    if not headers or len(set(headers)) != len(headers):
        raise ValueError('Missing or duplicate CSV headers')
    if any(len(row) != len(headers) for row in list(csv.reader(io.StringIO(text)))[1:] if row):
        raise ValueError('Malformed CSV row width')
    mapping = FORMATS[report_format]
    if index_report:
        daily = {'session_date': 'Date', 'open': 'Open', 'high': 'High',
                 'low': 'Low', 'close': 'Close'}
        verbose_match = set(mapping.values()).issubset(headers)
        daily_match = set(daily.values()).issubset(headers)
        if verbose_match and daily_match:
            raise ValueError('Ambiguous index CSV: multiple complete schemas')
        if daily_match:
            mapping = daily
    symbol, series = ('SYMBOL', 'SERIES') if report_format == 'nse-legacy' else ('TckrSymb', 'SctySrs')
    required = set(mapping.values()) | ({'Index Name'} if index_report else {symbol, series})
    if not required.issubset(headers):
        raise ValueError(f'Unknown/incomplete {report_format} schema; missing {sorted(required-set(headers))}')
    frame = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    frame.columns = headers
    if index_report:
        selected = frame.loc[frame['Index Name'].str.strip() == asset].copy()
    else:
        # Other assets/series in a daily bhavcopy are outside the selected dataset.
        selected = frame.loc[(frame[symbol].str.strip() == asset)
                             & (frame[series].str.strip() == 'EQ')].copy()
    if selected.empty:
        raise ValueError(f'No rows for {asset}' + ('' if index_report else ' in EQ series'))
    out = selected[list(mapping.values())].rename(columns={v: k for k, v in mapping.items()})
    out.insert(0, 'instrument', asset)
    out['session_date'] = out.session_date.map(parse_session)
    for name in ('open', 'high', 'low', 'close', 'previous_close', 'volume'):
        if name not in out:
            out[name] = np.nan  # Index volume/previous close is unavailable, never fabricated.
            continue
        try:
            values = pd.to_numeric(out[name].str.strip(), errors='raise')
        except ValueError as error:
            raise ValueError(f'Invalid {name}: numeric values required') from error
        if not np.isfinite(values).all() or (values < 0 if name == 'volume' else values <= 0).any():
            raise ValueError(f'Invalid {name}: finite ' + ('nonnegative volume' if name == 'volume' else 'positive prices') + ' required')
        if name == 'volume' and (values % 1 != 0).any():
            raise ValueError('Volume must be an integer')
        out[name] = values
    if out.duplicated(['instrument', 'session_date']).any():
        raise ValueError('Duplicate instrument/session rows; no silent deduplication')
    if ((out.high < out[['open', 'close', 'low']].max(axis=1))
            | (out.low > out[['open', 'close', 'high']].min(axis=1))).any():
        raise ValueError('OHLC invariants violated')
    # Format cutover is strict. Original files remain untouched.
    if report_format == 'nse-legacy' and (out.session_date >= '2024-07-08').any():
        raise ValueError('Legacy bhavcopy adapter cannot accept dates from 2024-07-08')
    if report_format == 'nse-udiff' and (out.session_date < '2024-07-08').any():
        raise ValueError('UDiFF adapter cannot accept dates before 2024-07-08')
    out['price_basis'] = 'official_published_unadjusted'
    return out.sort_values('session_date').reset_index(drop=True)
