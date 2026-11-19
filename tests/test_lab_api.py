from fastapi.testclient import TestClient
from backend.app.main import create_app


def test_missing_data_never_returns_forecasts(tmp_path):
    client=TestClient(create_app(tmp_path/'data',tmp_path/'registry'))
    assert client.get('/health').json()['status']=='ok'
    assert len(client.get('/v1/assets').json()['assets'])==6
    status=client.get('/v1/data/status').json()
    assert status['g0_passed'] is False
    assert all(not a['available'] for a in status['assets'])
    assert client.get('/ready?asset=TCS').status_code==503
    payload={'asset':'TCS','as_of_session':'2024-07-08'}
    assert client.post('/v1/predict/large-move',json=payload).status_code==503
    assert client.post('/v1/predict/next-close',json=payload).status_code==503
    assert client.get('/v1/assets/TCS/history').status_code==403
    assert client.get('/v1/assets/INVALID/states').status_code==400
    assert client.get('/v1/assets/TCS/states?view=invalid').status_code==400
    assert client.post('/v1/train').status_code==404
    assert client.post('/v1/data/validate-upload').status_code==404


def test_request_validation_and_body_limits(tmp_path):
    client=TestClient(create_app(tmp_path/'data',tmp_path/'registry'))
    for payload in [{'asset':'TCS','as_of_session':'2999-01-01'},
                    {'asset':'TCS','as_of_session':'20240101'},
                    {'asset':'TCS','as_of_session':'2024-01-01','retrain':True}]:
        assert client.post('/v1/predict/large-move',json=payload).status_code==422
    assert client.post('/v1/predict/large-move',content=b'x'*5000).status_code==413
    for _ in range(120):client.get('/health')
    assert client.get('/health').status_code==429


def test_real_audit_contract_reports_missing_evidence_without_claiming_validation(tmp_path):
    client=TestClient(create_app(tmp_path/'data',tmp_path/'registry',evidence_root=tmp_path/'docs'))
    r=client.get('/v1/data/evidence')
    assert r.status_code==200
    assert len(r.json()['items'])==3
    assert all(item['status']=='unavailable' for item in r.json()['items'])


def test_saved_results_verified_against_predictions_and_exported(tmp_path):
    # Two-session hand-checkable fixture, never research evidence.
    import json,hashlib
    import numpy as np
    import pandas as pd
    from nse_forecast.experiments.lab import scoring
    root=tmp_path/'registry'/'tiny';root.mkdir(parents=True)
    predictions=pd.DataFrame([dict(asset='TCS',origin_session=origin,target_session=target,model=model,actual=y,probability=p)
        for model,values in [('HMM',[.2,.8]),('Prevalence',[.5,.5])]
        for origin,target,y,p in zip(['2023-04-03','2023-04-04'],['2023-04-04','2023-04-05'],[0,1],values)])
    predictions.to_csv(root/'predictions.csv',index=False)
    np.savez(root/'hmm.npz',theta=.01)
    metrics={name:scoring(part.actual.to_numpy(),part.probability.to_numpy(),.5) for name,part in predictions.groupby('model')}
    metrics['HMM']['brier']=float(np.float32(metrics['HMM']['brier']))
    m=dict(asset='TCS',status='development_candidate',metrics=metrics,price_metrics={},failed_models={},hmm_runs=[],calibration='raw',caveat='Test fixture only',final_test_evaluated=False,
           config={'train_end':'2023-03-31'},research_track='exploratory',
           files_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()})
    path=root/'manifest.json';path.write_text(json.dumps(m))
    client=TestClient(create_app(tmp_path/'data',tmp_path/'registry'))
    r=client.get('/v1/experiments/tiny');assert r.status_code==200,r.text
    result=r.json();assert abs(result['metrics']['HMM']['brier']-.04)<1e-12
    assert result['evaluation']['validation_start']=='2023-04-04'
    assert result['final_test_evaluated'] is False
    csv=client.get('/v1/experiments/tiny/predictions')
    assert csv.status_code==200 and 'text/csv' in csv.headers['content-type']
    assert 'origin_session' in csv.text and 'actual_price' not in csv.text
    historical=json.loads(json.dumps(m))
    historical.update(final_test_evaluated=True,status='locked_historical_test',protocol_sha256='fixture-protocol')
    historical['config'].update(test_start='2023-04-03',test_end='2023-04-05')
    path.write_text(json.dumps(historical))
    checked=client.get('/v1/experiments/tiny')
    assert checked.status_code==200
    assert checked.json()['evaluation']['kind']=='locked_historical_test'
    historical['config']['test_end']='2023-04-04'
    path.write_text(json.dumps(historical))
    assert client.get('/v1/experiments/tiny').status_code==503
    m['metrics']['HMM']['brier']+=.02;path.write_text(json.dumps(m))
    assert client.get('/v1/experiments/tiny').status_code==503
    m['metrics']=metrics;path.write_text(json.dumps(m))
    (root/'predictions.csv').write_text('tampered')
    assert client.get('/v1/experiments/tiny').status_code==503


def test_legacy_prices_require_explicit_local_mode_and_valid_checksums(tmp_path,monkeypatch):
    import hashlib,json
    root=tmp_path/'legacy';root.mkdir();(root/'history').mkdir()
    files={'results.json':dict(available=True,rows=[],source='local fixture'),
           'history/TCS.NS.json':dict(available=True,symbol='TCS.NS',rows=[])}
    for name,payload in files.items():(root/name).write_text(json.dumps(payload))
    (root/'manifest.json').write_text(json.dumps({'files_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in files}}))
    monkeypatch.setenv('BULLBENCH_LEGACY_SITE',str(root))
    monkeypatch.delenv('BULLBENCH_LOCAL_LEGACY',raising=False)
    client=TestClient(create_app(tmp_path/'data',tmp_path/'registry'))
    assert client.get('/api/results').status_code==404
    monkeypatch.setenv('BULLBENCH_LOCAL_LEGACY','1')
    assert client.get('/api/results').json()['source']=='local fixture'
    assert client.get('/api/history?symbol=TCS.NS').status_code==200
    assert client.get('/api/history?symbol=../secret').status_code==400
    remote=TestClient(client.app,client=('203.0.113.1',1234))
    assert remote.get('/api/results').status_code==403
    (root/'results.json').write_text('modified')
    assert client.get('/api/results').status_code==503
    assert client.get('/v1/assets/TCS/history').status_code==403
