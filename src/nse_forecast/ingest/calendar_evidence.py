"""Annual circular evidence is provisional: amendments and special-session notices may override it."""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
from ..experiments.lab import read_snapshots
from .official import ASSETS

MONTHS='January|February|March|April|May|June|July|August|September|October|November|December'
ROW=re.compile(r'^\s*(?:\d{1,2}\s+)?('+MONTHS+r')\s+(\d{1,2}),\s*(\d{4})\b(.*)$')


def parse_circular(text):
    if not re.search(r'Department\s*:\s*CAPITAL MARKET SEGMENT',text):
        raise ValueError('Capital Market segment circular required')
    title=re.search(r'Trading holidays for the calendar year (\d{4})',text)
    reference=re.search(r'Download Ref No\s*:\s*NSE/CMTR/(\d+)',text)
    publication=re.search(r'Date\s*:\s*('+MONTHS+r')\s+(\d{1,2}),\s*(\d{4})',text)
    if not title or not reference or not publication:raise ValueError('Missing circular title/reference/publication date')
    year=int(title[1])
    published=datetime.strptime(' '.join(publication.groups()),'%B %d %Y').date().isoformat()
    rows=[];weekend=False;in_table=False
    for line in text.splitlines():
        if 'holidays falling on Saturday / Sunday' in line:weekend=True
        if 'Sr. No.' in line:in_table=True
        match=ROW.match(line)
        if not in_table or not match:continue
        month,day,row_year,description=match.groups()
        value=datetime.strptime(f'{month} {day} {row_year}','%B %d %Y').date()
        if value.year!=year:raise ValueError('Table date outside circular year')
        is_weekend=value.weekday()>=5
        if is_weekend!=weekend:raise ValueError('Table section/weekday mismatch')
        # The asterisk plus an explicit Muhurat sentence is positive evidence of an exception.
        special='*' in description and 'Muhurat Trading will be conducted' in text
        rows.append(dict(session_date=value.isoformat(),claim='muhurat_session_announced' if special else 'annual_weekend_holiday' if weekend else 'annual_weekday_closure',description=description.strip()))
    if not rows or len({row['session_date'] for row in rows})!=len(rows):raise ValueError('Empty or duplicate circular table dates')
    return dict(year=year,reference='NSE/CMTR/'+reference[1],published_date=published,
                published_at=None,retrieved_at=None,records=rows,complete_calendar=False,
                caveat='Annual notice only; later amendments and additional trading sessions are not established by this file.')


def reconcile(evidence, datasets, first, last):
    if len({item['year'] for item in evidence})!=len(evidence):raise ValueError('Multiple annual circulars for a year require explicit revision reconciliation')
    if {int(first[:4]),int(last[:4])}-set(item['year'] for item in evidence):raise ValueError('Missing boundary-year circulars')
    years=set(range(int(first[:4]),int(last[:4])+1))
    if not years.issubset({item['year'] for item in evidence}):raise ValueError('Missing annual circular year')
    records={row['session_date']:row for item in evidence for row in item['records']}
    closed={d for d,r in records.items() if r['claim']!='muhurat_session_announced'}
    muhurat={d for d,r in records.items() if r['claim']=='muhurat_session_announced'}
    candidate_weekdays={d.strftime('%Y-%m-%d') for d in pd.bdate_range(first,last)}-closed-muhurat
    results={}
    for asset,values in datasets.items():
        dates={d for d in values if first<=d<=last}
        results[asset]=dict(observed_on_annual_closure=sorted(dates&closed),
                           absent_from_candidate_weekdays=sorted(candidate_weekdays-dates),
                           announced_muhurat_present=sorted(dates&muhurat),
                           announced_muhurat_absent=sorted(d for d in muhurat-dates if first<=d<=last),
                           weekend_observations_without_annual_session_notice=sorted(d for d in dates if datetime.fromisoformat(d).weekday()>=5 and d not in muhurat))
    return dict(first_session=first,last_session=last,calendar_verified=False,g0_passed=False,
                comparisons=results,note='Candidate weekdays are NOT verified trading sessions. Conflicts require amendments; no observation is modified and no executable forecast calendar is produced.')


def main():
    parser=argparse.ArgumentParser(description='Read supplied annual PDFs and audit dates; no downloading, data edits or modelling')
    parser.add_argument('--files',nargs='+',required=True)
    parser.add_argument('--snapshots',default='data/exploratory_snapshots')
    parser.add_argument('--output',default='data/calendar_evidence')
    parser.add_argument('--first',default='2021-10-01');parser.add_argument('--last',default='2026-10-16')
    args=parser.parse_args()
    try:
        evidence=[];originals={}
        for value in args.files:
            path=Path(value);raw=path.read_bytes()
            if not raw.startswith(b'%PDF-'):raise ValueError('PDF input required')
            extracted=subprocess.run(['pdftotext','-layout',str(path),'-'],check=True,capture_output=True,text=True).stdout
            item=parse_circular(extracted);sha=hashlib.sha256(raw).hexdigest()
            item.update(filename=path.name,sha256=sha,source_authenticity='user_supplied_NSE_circular_not_independently_fetched')
            evidence.append(item);originals[sha]=raw
        evidence.sort(key=lambda x:x['year'])
        datasets={asset:read_snapshots(args.snapshots,asset)[0].session_date.tolist() for asset in ASSETS}
        report=reconcile(evidence,datasets,args.first,args.last)
        report['sources']=[{k:v for k,v in item.items() if k!='records'} | {'record_count':len(item['records'])} for item in evidence]
        payload={'evidence':evidence,'audit':report}
        encoded=(json.dumps(payload,indent=2,sort_keys=True)+'\n').encode()
        digest=hashlib.sha256(encoded).hexdigest();dest=Path(args.output)/digest
        contents={'evidence.json':encoded}
        contents.update({f'originals/{sha}.pdf':raw for sha,raw in originals.items()})
        if dest.exists():
            if any(not (dest/name).is_file() or (dest/name).read_bytes()!=raw for name,raw in contents.items()):
                raise ValueError('Existing evidence differs; refusing overwrite')
        else:
            dest.parent.mkdir(parents=True,exist_ok=True)
            with TemporaryDirectory(prefix='.pending-',dir=dest.parent) as temporary:
                stage=Path(temporary)/'evidence'
                for name,raw in contents.items():
                    path=stage/name;path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_bytes(raw);path.chmod(0o444)
                stage.rename(dest)
        print(json.dumps({'saved_to':str(dest),'audit':report},indent=2))
    except (ValueError,OSError,subprocess.CalledProcessError) as error:parser.exit(1,f'Calendar evidence rejected: {error}\n')

if __name__=='__main__':main()
