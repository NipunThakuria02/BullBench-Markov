import csv
import io
import hashlib
import pandas as pd
import pytest
from nse_forecast.ingest import corporate_actions as ca


def raw(symbol='TCS',purpose='Dividend - Rs 1 Per Share',ex_date='01-Jun-2022',face='1'):
    stream=io.StringIO();writer=csv.writer(stream)
    writer.writerow(ca.COLUMNS)
    writer.writerow([symbol,'Company','EQ',purpose,face,ex_date,'02-Jun-2022','-','-'])
    return stream.getvalue().encode()


def test_dates_and_events_do_not_imply_adjustment():
    event=ca.parse_actions(raw('TATASTEEL','Face Value Split (Sub-Division) - From Rs 10/- Per Share To Re 1/- Per Share'))[0]
    assert event['ex_date']=='2022-06-01' and event['action_type']=='split'
    assert event['book_closure_start'] is None
    assert event['announcement_at'] is None
    assert event['price_adjustment_verified'] is False
    assert 'adjustment_factor' not in event


@pytest.mark.parametrize('content',[
    raw().replace(b'EX-DATE',b'UNKNOWN'),
    raw('UNKNOWN'),raw(face='nan'),raw(face='0'),raw(ex_date='31-Feb-2022'),
    raw().replace(b',EQ,',b',BE,'),
    raw()+raw().splitlines(keepends=True)[1],
])
def test_invalid_files_fail_closed(content):
    with pytest.raises(ValueError):ca.parse_actions(content)


def test_distinct_events_on_same_date_are_retained():
    content=raw('TCS','Dividend')+raw('TCS','Bonus 1:1').splitlines(keepends=True)[1]
    assert len(ca.parse_actions(content))==2


def test_complete_batch_preserves_originals_and_reports_scope(tmp_path,monkeypatch):
    def prices(root,asset):
        return pd.DataFrame({'session_date':['2022-05-31','2022-06-01'],'price_basis':['yahoo_auto_adjusted']*2}),[]
    monkeypatch.setattr(ca,'read_snapshots',prices)
    paths=[]
    for asset in ca.EQUITIES:
        p=tmp_path/(asset+'.csv');p.write_bytes(raw(asset,'Bonus 1:1'));paths.append(p)
    payload,originals=ca.prepare_evidence(paths,'unused','2021-10-01','2026-10-16')
    assert len(payload['audit']['structural_events'])==5
    assert not payload['audit']['corporate_action_policy_verified']
    dest=ca.save_evidence(payload,originals,tmp_path/'evidence')
    assert ca.save_evidence(payload,originals,tmp_path/'evidence')==dest
    for p in paths:
        sha=hashlib.sha256(p.read_bytes()).hexdigest()
        assert (dest/'originals'/(sha+'.csv')).read_bytes()==p.read_bytes()
    with pytest.raises(ValueError,match='all five'):
        ca.prepare_evidence(paths[:-1],'unused')
    with pytest.raises(ValueError,match='Repeated instrument'):
        ca.prepare_evidence(paths+[paths[0]],'unused')


def test_nonoverlapping_supplement_retained_with_separate_provenance(tmp_path,monkeypatch):
    monkeypatch.setattr(ca,'read_snapshots',lambda root,asset:(pd.DataFrame({'session_date':['2022-05-31','2022-06-01'],'price_basis':['yahoo_auto_adjusted']*2}),[]))
    paths=[]
    for asset in ca.EQUITIES:
        p=tmp_path/(asset+'.csv');p.write_bytes(raw(asset));paths.append(p)
    extra=tmp_path/'TCS-earlier.csv';extra.write_bytes(raw('TCS','Interim Dividend','14-Oct-2021'))
    paths.append(extra)
    payload,originals=ca.prepare_evidence(paths,'unused')
    tcs=[e for e in payload['events'] if e['instrument']=='TCS']
    assert [e['ex_date'] for e in tcs]==['2021-10-14','2022-06-01']
    assert len({e['source_sha256'] for e in tcs})==2
    assert len(originals)==6
    summary=next(s for s in payload['audit']['instruments'] if s['instrument']=='TCS')
    assert summary['input_files']==2 and summary['full_period_completeness']=='unverified'
    assert payload['audit']['corporate_action_policy_verified'] is False
    extra.write_bytes(raw('TCS','Buyback','01-Jun-2022'))
    with pytest.raises(ValueError,match='Overlapping event dates'):
        ca.prepare_evidence(paths,'unused')
