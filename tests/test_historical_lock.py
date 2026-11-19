import hashlib
import pandas as pd
import pytest
from nse_forecast.experiments.lab import run, split_masks


def test_locked_splits_enforce_chronology_and_sixty_origin_embargoes():
    # Calendar-only fixture, not synthetic market prices or research evidence.
    dates=pd.bdate_range('2024-01-01','2026-10-16').strftime('%Y-%m-%d')
    frame=pd.DataFrame({'session_date':dates[:-1],'target_session':dates[1:]})
    config=dict(evaluation_mode='locked_historical_test',train_end='2024-12-31',validation_start='2025-04-15',validation_end='2025-09-30',test_start='2026-01-16',test_end='2026-10-16')
    train,val,test=split_masks(frame,config)
    assert frame.loc[train,'target_session'].max()<=config['train_end']
    assert frame.loc[val,'session_date'].min()>=config['validation_start']
    assert frame.loc[test,'session_date'].min()>=config['test_start']
    assert not (train&test).any() and not (val&test).any()
    altered=frame.copy();altered['unused_future_outcome']=100
    assert all(a.equals(b) for a,b in zip((train,val,test),split_masks(altered,config)))
    with pytest.raises(ValueError,match='embargo'):
        split_masks(frame,dict(config,test_start='2025-10-01'))


def test_modified_frozen_protocol_blocks_before_any_snapshot_or_test_access(tmp_path):
    p=tmp_path/'protocol.md';p.write_text('frozen')
    digest=hashlib.sha256(p.read_bytes()).hexdigest();p.write_text('modified')
    with pytest.raises(ValueError,match='checksum'):
        run(dict(evaluation_mode='locked_historical_test',protocol_file=str(p),protocol_sha256=digest),tmp_path/'never-created')
    assert not (tmp_path/'never-created').exists()
