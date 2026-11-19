"""Preserve supplied event evidence without assuming price adjustment or announcement timing."""
import argparse
import csv
import hashlib
import io
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from tempfile import TemporaryDirectory

from .official import EQUITIES
from ..experiments.lab import read_snapshots

COLUMNS=['SYMBOL','COMPANY NAME','SERIES','PURPOSE','FACE VALUE','EX-DATE','RECORD DATE','BOOK CLOSURE START DATE','BOOK CLOSURE END DATE']


def event_date(value, required=False):
    value=value.strip()
    if value in ('','-'):
        if required:raise ValueError('Ex-date required')
        return None
    for fmt in ('%d-%b-%Y','%Y-%m-%d'):
        try:return datetime.strptime(value,fmt).date().isoformat()
        except ValueError:pass
    raise ValueError('Unsupported corporate-action date')


def action_type(purpose):
    text=purpose.casefold()
    if 'demerger' in text:return 'demerger'
    if 'split' in text or 'sub-division' in text:return 'split'
    if 'bonus' in text:return 'bonus'
    if 'rights' in text:return 'rights'
    if 'buy back' in text or 'buyback' in text:return 'buyback'
    if 'dividend' in text:return 'dividend'
    return 'other_requires_review'


def parse_actions(raw):
    reader=csv.reader(io.StringIO(raw.decode('utf-8-sig')))
    header=[v.strip() for v in next(reader,[])]
    if len(header)!=len(set(header)) or set(header)!=set(COLUMNS):raise ValueError('Unknown or duplicate corporate-action columns')
    events=[];seen=set()
    for cells in reader:
        if not cells:continue
        if len(cells)!=len(header):raise ValueError('Malformed corporate-action CSV row')
        row={k:v.strip() for k,v in zip(header,cells)}
        if row['SYMBOL'] not in EQUITIES or row['SERIES']!='EQ':raise ValueError('Expected supported stock in EQ series')
        if not row['COMPANY NAME'] or not row['PURPOSE']:raise ValueError('Company and purpose required')
        try:face=Decimal(row['FACE VALUE'])
        except InvalidOperation as error:raise ValueError('Invalid face value') from error
        if not face.is_finite() or face<=0:raise ValueError('Positive finite face value required')
        event=dict(instrument=row['SYMBOL'],company=row['COMPANY NAME'],series=row['SERIES'],purpose=row['PURPOSE'],face_value=row['FACE VALUE'],
                   ex_date=event_date(row['EX-DATE'],True),record_date=event_date(row['RECORD DATE']),
                   book_closure_start=event_date(row['BOOK CLOSURE START DATE']),book_closure_end=event_date(row['BOOK CLOSURE END DATE']),
                   action_type=action_type(row['PURPOSE']),announcement_at=None,price_adjustment_verified=False)
        if event['book_closure_start'] and event['book_closure_end'] and event['book_closure_start']>event['book_closure_end']:
            raise ValueError('Book closure dates reversed')
        key=tuple(row[c] for c in COLUMNS)
        if key in seen:raise ValueError('Duplicate corporate-action record')
        seen.add(key);events.append(event)
    if not events or len({e['instrument'] for e in events})!=1:raise ValueError('One nonempty instrument export required per file')
    return sorted(events,key=lambda e:(e['ex_date'],e['purpose']))


def prepare_evidence(files,snapshots,first='2021-10-01',last='2026-10-16'):
    sources=[];all_events=[];originals={};instruments=set();summaries=[];structural=[]
    dates_by_asset={}
    if event_date(first,True)>event_date(last,True):raise ValueError('Reversed requested period')
    for value in files:
        path=Path(value);raw=path.read_bytes();events=parse_actions(raw)
        asset=events[0]['instrument']
        sha=hashlib.sha256(raw).hexdigest()
        if sha in originals:raise ValueError('Repeated instrument export bytes; supply each original once')
        dates={e['ex_date'] for e in events}
        if dates & dates_by_asset.get(asset,set()):
            raise ValueError('Overlapping event dates across files require explicit reconciliation')
        dates_by_asset.setdefault(asset,set()).update(dates)
        instruments.add(asset);originals[sha]=raw
        scoped=[e for e in events if first<=e['ex_date']<=last]
        for event in events:event['source_sha256']=sha
        all_events+=events
        sources.append(dict(filename=path.name,sha256=sha,instrument=asset,rows=len(events),in_scope_rows=len(scoped),out_of_scope_rows=len(events)-len(scoped),
                            earliest_ex_date=events[0]['ex_date'],latest_ex_date=events[-1]['ex_date'],retrieved_at=None,published_at=None,source_authenticity='user_supplied_NSE_export_not_independently_fetched'))
        bars,_=read_snapshots(snapshots,asset)
        for event in scoped:
            if event['action_type'] not in ('bonus','split','demerger','rights'):continue
            price=bars.loc[bars.session_date==event['ex_date']]
            prior=bars.loc[bars.session_date<event['ex_date']]
            structural.append(dict(instrument=asset,ex_date=event['ex_date'],action_type=event['action_type'],purpose=event['purpose'],source_sha256=sha,
                                   ex_date_price_present=not price.empty,prior_observed_session=prior.session_date.iloc[-1] if not prior.empty else None,
                                   existing_price_basis=price.price_basis.iloc[0] if not price.empty else None,
                                   official_previous_close_adjustment_verified=False,
                                   note='Vendor-adjusted observations cannot prove how an official same-file previous-close field is adjusted. No factor is applied.'))
    if instruments!=set(EQUITIES):raise ValueError('Supply all five study stock exports')
    for asset in sorted(instruments):
        asset_sources=[s for s in sources if s['instrument']==asset]
        events=[e for e in all_events if e['instrument']==asset]
        scoped=[e for e in events if first<=e['ex_date']<=last]
        earliest=min(e['ex_date'] for e in events)
        limited=[s for s in asset_sources if s['rows']==20 and s['earliest_ex_date']>first]
        addressed=bool(limited) and all(earliest<s['earliest_ex_date'] for s in limited)
        warnings=[]
        if limited and not addressed:
            warnings.append('Possible export row limit: exactly 20 records and oldest ex-date lies inside requested period. Earlier events must be checked; absence is not established.')
        types={kind:sum(e['action_type']==kind for e in scoped) for kind in sorted({e['action_type'] for e in scoped})}
        summaries.append(dict(instrument=asset,action_counts_in_scope=types,full_period_completeness='unverified',
                              input_files=len(asset_sources),earlier_export_gap_addressed=addressed,warnings=warnings))
    sources.sort(key=lambda e:e['instrument']);summaries.sort(key=lambda e:e['instrument']);structural.sort(key=lambda e:(e['instrument'],e['ex_date']))
    audit=dict(first_session=first,last_session=last,sources=sources,instruments=summaries,structural_events=structural,
               corporate_action_policy_verified=False,g0_passed=False,
               notes=['All raw rows retained privately; out-of-range events are excluded only from this audit scope.',
                      'Unknown source retrieval/publication and event announcement timestamps remain null.',
                      'Event ex-dates are not historical announcement-availability timestamps.',
                      'No prices, return definitions, labels, model bundles or experiment splits changed.'])
    payload=dict(schema_version=1,source_identity='NSE corporate-action exports supplied by owner',source_url='https://www.nseindia.com/companies-listing/corporate-filings-actions',
                 events=sorted(all_events,key=lambda e:(e['instrument'],e['ex_date'],e['purpose'])),audit=audit)
    return payload,originals


def save_evidence(payload,originals,root):
    raw=(json.dumps(payload,indent=2,sort_keys=True)+'\n').encode()
    digest=hashlib.sha256(raw).hexdigest();root=Path(root);dest=root/digest
    contents={'evidence.json':raw}
    for sha,data in originals.items():
        if hashlib.sha256(data).hexdigest()!=sha:raise ValueError('Original checksum mismatch')
        contents[f'originals/{sha}.csv']=data
    if dest.exists():
        if any(not (dest/name).is_file() or (dest/name).read_bytes()!=data for name,data in contents.items()):raise ValueError('Existing evidence differs; refusing overwrite')
        return dest
    root.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='.pending-',dir=root) as temporary:
        stage=Path(temporary)/'evidence'
        for name,data in contents.items():
            path=stage/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);path.chmod(0o444)
        stage.rename(dest)
    return dest


def main():
    parser=argparse.ArgumentParser(description='Preserve stock event exports, allowing nonoverlapping chunks; never adjust prices or train')
    parser.add_argument('--files',nargs='+',required=True)
    parser.add_argument('--snapshots',default='data/exploratory_snapshots')
    parser.add_argument('--output',default='data/corporate_action_evidence')
    parser.add_argument('--first',default='2021-10-01');parser.add_argument('--last',default='2026-10-16')
    args=parser.parse_args()
    try:
        payload,originals=prepare_evidence(args.files,args.snapshots,args.first,args.last)
        dest=save_evidence(payload,originals,args.output)
        print(json.dumps(dict(saved_to=str(dest),audit=payload['audit']),indent=2))
    except (ValueError,OSError) as error:parser.exit(1,f'Corporate-action evidence rejected: {error}\n')

if __name__=='__main__':main()
