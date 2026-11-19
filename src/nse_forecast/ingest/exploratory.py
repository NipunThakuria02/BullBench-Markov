"""Explicit Yahoo/manual-index track authorized by owner; not official validation."""
import argparse
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from .official import EQUITIES, parse_export
from .snapshot import save_snapshot, aware_timestamp


def prepare_exploratory(raw, asset, source_url, retrieved_at, source):
    if source=='yfinance' and asset in EQUITIES:
        frame=pd.read_csv(__import__('io').BytesIO(raw))
        required={'Date','Open','High','Low','Close','Volume'}
        if not required.issubset(frame):raise ValueError('Incomplete Yahoo adjusted OHLCV export')
        bars=frame[list(required)].rename(columns={c:c.lower() for c in required})
        bars=bars.rename(columns={'date':'session_date'})
        bars['instrument']=asset
        bars['price_basis']='yahoo_auto_adjusted'
        identity='Yahoo Finance via yfinance'
    elif source=='manual-nifty' and asset=='NIFTY 50':
        bars=parse_export(raw,'nifty-index',asset)
        bars['price_basis']='official_index_points'
        identity='NSE Indices, user-supplied export'
    else:raise ValueError('Exploratory source/asset combination is unsupported')
    from ..provenance import public_source_url
    if not public_source_url(source_url):raise ValueError('Public source URL required')
    timestamp=aware_timestamp(retrieved_at) if retrieved_at else None
    if timestamp is None and source=='yfinance':raise ValueError('Yahoo retrieval timestamp required')
    if timestamp and timestamp>datetime.now(timezone.utc):raise ValueError('Retrieval timestamp cannot be in the future')
    bars['session_date']=pd.to_datetime(bars.session_date,format='%Y-%m-%d').dt.strftime('%Y-%m-%d')
    if bars.empty or bars.session_date.duplicated().any():raise ValueError('Empty or duplicate sessions')
    bars=bars.sort_values('session_date').reset_index(drop=True)
    cutoff=timestamp.date() if timestamp else datetime.now(timezone.utc).date()
    if bars.session_date.max()>cutoff.isoformat():raise ValueError('Future observation')
    for c in ['open','high','low','close']:
        bars[c]=pd.to_numeric(bars[c],errors='raise')
        if not np.isfinite(bars[c]).all() or (bars[c]<=0).any():raise ValueError('Invalid OHLC')
    if ((bars.high<bars[['open','low','close']].max(axis=1))|(bars.low>bars[['open','high','close']].min(axis=1))).any():raise ValueError('Invalid OHLC invariants')
    if source=='yfinance':
        bars['volume']=pd.to_numeric(bars.volume,errors='raise')
        if not np.isfinite(bars.volume).all() or (bars.volume<0).any():raise ValueError('Invalid volume')
    bars['previous_close']=bars.close.shift(1)
    retrieved=timestamp.isoformat() if timestamp else None
    sha=hashlib.sha256(raw).hexdigest();bars['source_id']=sha;bars['retrieved_at']=retrieved
    canonical=bars.to_csv(index=False).encode()
    manifest=dict(schema_version=1,adapter_version='exploratory-1',instrument=asset,source_identity=identity,
                  source_url=source_url,retrieved_at=retrieved,published_at=None,
                  retrieval_time_status='user_supplied' if timestamp else 'not_provided',
                  publication_time_status='unverified',raw_sha256=sha,canonical_sha256=hashlib.sha256(canonical).hexdigest(),
                  rows=len(bars),first_session=bars.session_date.min(),last_session=bars.session_date.max(),
                  research_track='exploratory',permission_status='unverified',source_authenticity='vendor_or_user_supplied')
    manifest['snapshot_id']=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    audit=dict(status='exploratory_not_officially_validated',g0_passed=False,
               blockers=['Official calendar not verified','Source usage/display rights not verified','Adjusted vendor histories may be revised'],
               note='First previous close is unavailable; never filled. No forecasts generated.')
    return raw,canonical,manifest,audit


def prepare_nifty_files(files, retrieved_at=None):
    """Validate all chunks before saving; preserve exact originals and row provenance."""
    paths=[Path(p) for p in files]
    if not paths:raise ValueError('Supply at least one NIFTY 50 CSV')
    if len({p.resolve() for p in paths})!=len(paths):raise ValueError('Repeated input file')
    frames=[];originals={};inputs=[]
    for path in paths:
        raw=path.read_bytes()
        frame=parse_export(raw,'nifty-index','NIFTY 50')
        digest=hashlib.sha256(raw).hexdigest()
        if digest in originals:raise ValueError('Repeated input content')
        originals[digest]=raw
        frame['input_sha256']=digest
        frames.append(frame)
        inputs.append(dict(filename=path.name,sha256=digest,rows=len(frame),
                           first_session=frame.session_date.min(),last_session=frame.session_date.max()))
    combined=pd.concat(frames).sort_values('session_date').reset_index(drop=True)
    if combined.session_date.duplicated().any():
        raise ValueError('Overlapping input sessions; reconcile explicitly before import')
    # This concatenation contains only supplied observations; exact raw inputs live in originals/.
    source=io.StringIO()
    writer=csv.writer(source,lineterminator='\n')
    writer.writerow(['Index Name','Date','Open','High','Low','Close'])
    for row in combined.itertuples(index=False):
        writer.writerow(['NIFTY 50',row.session_date,row.open,row.high,row.low,row.close])
    prepared=prepare_exploratory(source.getvalue().encode(),'NIFTY 50',
                                 'https://www.niftyindices.com/reports/historical-data',
                                 retrieved_at,'manual-nifty')
    raw,canonical,manifest,audit=prepared
    bars=pd.read_csv(io.BytesIO(canonical))
    bars['source_id']=combined.input_sha256.to_numpy()
    canonical=bars.to_csv(index=False).encode()
    manifest['adapter_version']='exploratory-nifty-batch-1'
    manifest['source_kind']='derived_concatenation_of_preserved_originals'
    manifest['input_files']=sorted(inputs,key=lambda item:(item['first_session'],item['sha256']))
    manifest['canonical_sha256']=hashlib.sha256(canonical).hexdigest()
    manifest.pop('snapshot_id',None)
    manifest['snapshot_id']=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    dates=pd.to_datetime(bars.session_date)
    audit['weekend_sessions']=bars.loc[dates.dt.dayofweek>=5,'session_date'].tolist()
    audit['calendar_verified']=False
    audit['duplicate_sessions']=0
    audit['note']='Observed sessions only. Weekend rows retained for official calendar review, not silently removed. Previous close derives across chunk boundaries; first value remains unavailable. No models fitted.'
    return (raw,canonical,manifest,audit),originals


def main():
    parser=argparse.ArgumentParser(description='Separate exploratory data track; never official-data certification')
    parser.add_argument('command',choices=['download-stocks','import-nifty'])
    parser.add_argument('--start');parser.add_argument('--end',help='Inclusive last session to collect')
    parser.add_argument('--file',nargs='+');parser.add_argument('--retrieved-at')
    parser.add_argument('--output',default='data/exploratory_snapshots')
    args=parser.parse_args()
    try:
        if args.command=='import-nifty':
            if not args.file:raise ValueError('Provide one or more --file paths')
            prepared,originals=prepare_nifty_files(args.file,args.retrieved_at)
            saved=save_snapshot(prepared,args.output,original_files=originals)
            print(saved)
        else:
            if not args.start or not args.end or args.start>=args.end:raise ValueError('Explicit chronological --start and --end required')
            import yfinance as yf
            # Keep vendor cookies in an ignored local data directory, never the repository tree.
            yf.set_tz_cache_location(str(Path(args.output).parent/'vendor_cache'))
            failed=[]
            for asset in EQUITIES:
                try:
                    frame=yf.download(asset+'.NS',start=args.start,end=(pd.Timestamp(args.end)+pd.Timedelta(days=1)).strftime('%Y-%m-%d'),auto_adjust=True,progress=False,threads=False,multi_level_index=False)
                    if frame.empty:raise ValueError('Vendor returned no rows')
                    raw=frame.to_csv(index_label='Date').encode()
                    print(asset,save_snapshot(prepare_exploratory(raw,asset,'https://finance.yahoo.com',datetime.now(timezone.utc).isoformat(),'yfinance'),args.output))
                except Exception as error:failed.append(f'{asset}: {error}')
            if failed:raise ValueError('Incomplete download; successful snapshots retained. '+'; '.join(failed))
    except (ValueError,OSError) as error:parser.exit(1,f'Exploratory import blocked: {error}\n')

if __name__=='__main__':main()
