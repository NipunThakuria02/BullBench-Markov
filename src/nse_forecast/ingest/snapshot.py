"""Local, append-only snapshots. Parsed exports are not certified research data."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from ..provenance import public_source_url
from .official import ADAPTER_VERSION, parse_export


def aware_timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('Source timestamps must include a UTC offset')
    return parsed.astimezone(timezone.utc)


def prepare_snapshot(path, report_format, asset, source_url, retrieved_at, published_at):
    """Validate without creating files; explicit timestamps are source metadata."""
    if not public_source_url(source_url):
        raise ValueError('Use a public HTTPS source URL without credentials, query or fragment')
    host = urlsplit(source_url).hostname
    allowed = ('niftyindices.com', 'nseindices.com') if report_format == 'nifty-index' else ('nseindia.com',)
    if not any(host == domain or host.endswith('.' + domain) for domain in allowed):
        raise ValueError('Source URL must identify the matching official NSE/NSE Indices domain')
    retrieved, published = aware_timestamp(retrieved_at), aware_timestamp(published_at)
    now = datetime.now(timezone.utc)
    if published > retrieved or retrieved > now:
        raise ValueError('Require source publication <= retrieval <= current time')
    raw = Path(path).read_bytes()
    bars = parse_export(raw, report_format, asset)
    if bars.session_date.max() > published.astimezone(ZoneInfo('Asia/Kolkata')).date().isoformat():
        raise ValueError('Observation date is later than source publication')
    manifest = dict(schema_version=1, adapter_version=ADAPTER_VERSION,
                    source_identity='NSE Indices' if report_format == 'nifty-index' else 'NSE',
                    source_authenticity='unverified_user_supplied_export',
                    source_url=source_url, report_format=report_format, instrument=asset,
                    retrieved_at=retrieved.isoformat(), published_at=published.isoformat(),
                    original_filename=Path(path).name, raw_sha256=hashlib.sha256(raw).hexdigest(),
                    first_session=bars.session_date.min(), last_session=bars.session_date.max(),
                    rows=len(bars), permission_status='unverified')
    bars['source_id'] = manifest['raw_sha256']
    bars['retrieved_at'] = manifest['retrieved_at']
    bars['source_published_at'] = manifest['published_at']
    canonical = bars.to_csv(index=False).encode('utf-8')
    manifest['canonical_sha256'] = hashlib.sha256(canonical).hexdigest()
    # A snapshot identifies source, adapter, selected asset and metadata, not only raw bytes.
    snapshot_id = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    manifest['snapshot_id'] = snapshot_id
    audit = dict(status='parsed_not_research_ready', g0_passed=False,
                 rows_in_scope=len(bars), rejected_selected_rows=0,
                 rejection_policy='Any invalid selected row rejects the whole file.',
                 blockers=['Source authenticity and permitted use not verified',
                           'Official trading calendar and missing-session audit not verified',
                           'Corporate-action policy and previous-close adjustment not verified',
                           'Special-session policy and dataset scope not accepted'],
                 note='No returns, labels, splits, model fitting or forecasts generated.')
    return raw, canonical, manifest, audit


def save_snapshot(prepared, directory, original_files=None):
    raw, canonical, manifest, audit = prepared
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    dest = root / manifest['snapshot_id']
    contents = {'source.csv': raw, 'bars.csv': canonical,
                'manifest.json': (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode(),
                'audit.json': (json.dumps(audit, indent=2, sort_keys=True) + '\n').encode()}
    for digest, data in (original_files or {}).items():
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError('Original input checksum mismatch')
        contents[f'originals/{digest}.csv'] = data
    if dest.exists():
        if not dest.is_dir() or any(not (dest / name).is_file() or (dest / name).read_bytes() != data
                                    for name, data in contents.items()):
            raise ValueError('Existing snapshot differs; refusing overwrite')
        return dest
    with TemporaryDirectory(prefix='.pending-', dir=root) as staging:
        stage = Path(staging) / 'snapshot'
        stage.mkdir()
        for name, data in contents.items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(0o444)
        stage.rename(dest)
    return dest
