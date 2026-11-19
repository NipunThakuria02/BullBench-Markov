"""Tiny hand-checkable parser fixtures; never research observations."""
import hashlib
import json

import pandas as pd
import pytest

from nse_forecast.ingest.official import parse_export
from nse_forecast.ingest.snapshot import prepare_snapshot, save_snapshot
from nse_forecast.ingest.__main__ import main

LEGACY = b'SYMBOL,SERIES,TIMESTAMP,OPEN,HIGH,LOW,CLOSE,PREVCLOSE,TOTTRDQTY\nTCS,EQ,05-Jul-2024,100,110,90,105,100,10\n'
UDIFF = b'TckrSymb,SctySrs,TradDt,OpnPric,HghPric,LwPric,ClsPric,PrvsClsgPric,TtlTradgVol\nTCS,EQ,2024-07-08,100,110,90,105,100,10\n'
INDEX = b'Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value\nNIFTY 50,08 Jul 2024,100,110,90,105\n'


def prepared(tmp_path, raw=UDIFF, **overrides):
    path = tmp_path / 'input.csv'
    path.write_bytes(raw)
    kwargs = dict(path=path, report_format='nse-udiff', asset='TCS',
                  source_url='https://www.nseindia.com/reports',
                  retrieved_at='2024-07-09T10:00:00+05:30',
                  published_at='2024-07-08T18:00:00+05:30')
    return prepare_snapshot(**(kwargs | overrides))


@pytest.mark.parametrize('raw,kind,asset', [(LEGACY, 'nse-legacy', 'TCS'),
                                           (UDIFF, 'nse-udiff', 'TCS'),
                                           (INDEX, 'nifty-index', 'NIFTY 50')])
def test_adapter_preserves_published_prices(raw, kind, asset):
    bars = parse_export(raw, kind, asset)
    assert bars.close.tolist() == [105]
    assert bars.instrument.tolist() == [asset]
    assert bars.price_basis.tolist() == ['official_published_unadjusted']
    if asset == 'NIFTY 50':
        assert bars.volume.isna().all() and bars.previous_close.isna().all()


@pytest.mark.parametrize('raw,match', [
    (UDIFF.replace(b',110,', b',99,'), 'OHLC'),
    (UDIFF.replace(b',105,', b',nan,'), 'numeric|Invalid'),
    (UDIFF.replace(b',100,10', b',0,10'), 'previous_close'),
    (UDIFF.replace(b',10\n', b',-1\n'), 'volume'),
    (UDIFF.replace(b',10\n', b',1.5\n'), 'integer'),
    (UDIFF.replace(b',EQ,', b',BE,'), 'No rows'),
    (UDIFF.replace(b'2024-07-08', b'2024-02-30'), 'date'),
    (UDIFF.replace(b'2024-07-08', b'2024-07-05'), 'before'),
    (UDIFF + UDIFF.splitlines(keepends=True)[1], 'Duplicate'),
    (UDIFF.replace(b'ClsPric', b'new_close'), 'schema'),
    (UDIFF.replace(b'OpnPric', b'ClsPric'), 'duplicate'),
    (UDIFF.replace(b',10\n', b',10,extra\n'), 'row width'),
])
def test_bad_exports_fail_closed(raw, match):
    with pytest.raises(ValueError, match=match):
        parse_export(raw, 'nse-udiff', 'TCS')


def test_index_and_equity_schemas_cannot_be_interchanged():
    with pytest.raises(ValueError, match='separate'):
        parse_export(UDIFF, 'nse-udiff', 'NIFTY 50')
    with pytest.raises(ValueError, match='Unknown'):
        parse_export(UDIFF, 'guessed', 'TCS')
    with pytest.raises(ValueError, match='from 2024'):
        parse_export(LEGACY.replace(b'05-Jul', b'08-Jul'), 'nse-legacy', 'TCS')


def test_snapshot_is_idempotent_and_verifies_existing_files(tmp_path):
    data = prepared(tmp_path)
    original = (tmp_path / 'input.csv').read_bytes()
    destination = save_snapshot(data, tmp_path / 'snapshots')
    before = {p.name: p.read_bytes() for p in destination.iterdir()}
    assert save_snapshot(data, tmp_path / 'snapshots') == destination
    assert before == {p.name: p.read_bytes() for p in destination.iterdir()}
    assert before['source.csv'] == original
    manifest = json.loads(before['manifest.json'])
    assert manifest['canonical_sha256'] == hashlib.sha256(before['bars.csv']).hexdigest()
    assert manifest['raw_sha256'] == hashlib.sha256(original).hexdigest()
    bars = pd.read_csv(destination / 'bars.csv')
    assert bars.source_id.iloc[0] == manifest['raw_sha256']
    audit = json.loads(before['audit.json'])
    assert audit['g0_passed'] is False and len(audit['blockers']) == 4
    assert not {'return', 'target', 'label'}.intersection(bars.columns)
    (destination / 'bars.csv').chmod(0o644)
    (destination / 'bars.csv').write_text('tampered')
    with pytest.raises(ValueError, match='refusing overwrite'):
        save_snapshot(data, tmp_path / 'snapshots')


@pytest.mark.parametrize('overrides', [
    {'source_url': 'https://www.nseindia.com/reports?token=secret'},
    {'source_url': 'https://unrelated.example/reports'},
    {'published_at': '2024-07-08T18:00:00'},
    {'published_at': '2024-07-10T18:00:00+05:30'},
    {'published_at': '2024-07-07T18:00:00+05:30'},
    {'retrieved_at': '2999-07-09T10:00:00+05:30'},
])
def test_provenance_prerequisites(tmp_path, overrides):
    with pytest.raises(ValueError):
        prepared(tmp_path, **overrides)


def test_read_only_cli_and_explicit_commit(tmp_path, capsys):
    source = tmp_path / 'official.csv'
    source.write_bytes(UDIFF)
    output = tmp_path / 'snapshots'
    args = ['--file', str(source), '--format', 'nse-udiff', '--asset', 'TCS',
            '--source-url', 'https://www.nseindia.com/reports',
            '--retrieved-at', '2024-07-09T10:00:00+05:30',
            '--published-at', '2024-07-08T18:00:00+05:30', '--output', str(output)]
    main(args)
    assert not output.exists()
    assert json.loads(capsys.readouterr().out)['audit']['g0_passed'] is False
    main(args + ['--commit'])
    assert len(list(output.iterdir())) == 1
    capsys.readouterr()
    source.write_bytes(UDIFF.replace(b',105,', b',0,'))
    with pytest.raises(SystemExit) as error:
        main(args + ['--commit'])
    assert error.value.code == 1
    assert len(list(output.iterdir())) == 1
