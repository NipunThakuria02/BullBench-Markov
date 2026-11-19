"""Tiny deterministic import fixtures, never market training data."""
import hashlib
import io
import json
import pandas as pd
import pytest
from nse_forecast.ingest.exploratory import prepare_nifty_files
from nse_forecast.ingest.official import parse_export
from nse_forecast.ingest.snapshot import save_snapshot

HEADER=b'Index Name,Date,Open,High,Low,Close\n'
A=HEADER+b'NIFTY 50,31 Dec 2021,100,110,90,105\n'
B=HEADER+b'NIFTY 50,04 Jan 2022,106,112,100,110\nNIFTY 50,03 Jan 2022,105,111,99,106\n'


def test_daily_schema_and_cross_year_continuity(tmp_path):
    a=tmp_path/'2021.csv';b=tmp_path/'2022.csv'
    a.write_bytes(A);b.write_bytes(B)
    prepared,originals=prepare_nifty_files([b,a])
    raw,canonical,manifest,audit=prepared
    frame=pd.read_csv(io.BytesIO(canonical))
    assert frame.session_date.tolist()==['2021-12-31','2022-01-03','2022-01-04']
    assert pd.isna(frame.previous_close.iloc[0])
    assert frame.previous_close.iloc[1]==105
    assert frame.source_id.iloc[0]==hashlib.sha256(A).hexdigest()
    assert frame.source_id.iloc[1]==hashlib.sha256(B).hexdigest()
    assert manifest['retrieved_at'] is None and manifest['published_at'] is None
    assert audit['calendar_verified'] is False
    dest=save_snapshot(prepared,tmp_path/'snapshots',original_files=originals)
    for digest,content in originals.items():assert (dest/'originals'/f'{digest}.csv').read_bytes()==content
    again,again_originals=prepare_nifty_files([a,b])
    assert again[2]['snapshot_id']==manifest['snapshot_id']
    assert save_snapshot(again,tmp_path/'snapshots',original_files=again_originals)==dest
    assert a.read_bytes()==A and b.read_bytes()==B


def test_overlaps_and_invalid_chunks_reject_entire_batch(tmp_path):
    a=tmp_path/'a.csv';b=tmp_path/'b.csv'
    a.write_bytes(A);b.write_bytes(A.replace(b',105\n',b',106\n'))
    with pytest.raises(ValueError,match='Overlapping'):prepare_nifty_files([a,b])
    with pytest.raises(ValueError,match='Repeated input file'):prepare_nifty_files([a,a])
    b.write_bytes(B.replace(b',112,',b',99,'))
    with pytest.raises(ValueError,match='OHLC'):prepare_nifty_files([a,b])
    assert not (tmp_path/'snapshots').exists()


def test_wrong_index_and_ambiguous_headers_rejected():
    with pytest.raises(ValueError,match='No rows'):
        parse_export(A.replace(b'NIFTY 50',b'NIFTY ENERGY'),'nifty-index','NIFTY 50')
    with pytest.raises(ValueError,match='Ambiguous'):
        parse_export(b'Index Name,Date,Open,High,Low,Close,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value\n','nifty-index','NIFTY 50')
