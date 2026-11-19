"""Run this private portable bundle locally, without downloading data or fitting models."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))


def create_local_app():
    os.environ['BULLBENCH_LOCAL_LEGACY']='1'
    os.environ['BULLBENCH_LEGACY_SITE']=str(ROOT/'data/legacy_site')
    from backend.app.main import create_app
    from fastapi.staticfiles import StaticFiles
    build = ROOT / 'web' / 'dist'
    if not (build / 'index.html').is_file():
        raise RuntimeError('Prebuilt frontend missing. Rebuild with npm --prefix web ci and npm --prefix web run build.')
    app = create_app(snapshot_root=ROOT / 'data' / 'exploratory_snapshots',
                     registry_root=ROOT / 'model_registry', evidence_root=ROOT / 'docs')
    app.mount('/', StaticFiles(directory=build, html=True), name='local_frontend')
    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--check', action='store_true', help='Check packaged data, model, results and UI without starting a server')
    args = parser.parse_args()
    app = create_local_app()
    if args.check:
        from fastapi.testclient import TestClient
        with TestClient(app) as client:
            assert client.get('/health').status_code == 200
            sources = client.get('/v1/data/status').json()['assets']
            assert len(sources) == 6 and all(item['available'] for item in sources)
            runs=client.get('/v1/experiments').json()['experiments']
            assert len(runs)>=6
            for run in runs:
                result=client.get('/v1/experiments/'+run['id'])
                assert result.status_code==200,result.text
                assert len(result.json()['metrics'])>=9
                assert len(result.json()['price_metrics'])==8
                assert client.get('/ready',params={'asset':run['asset']}).status_code==200
                assert client.get('/v1/assets/'+run['asset']+'/transitions').status_code==200
            assert client.get('/').status_code == 200
            if (ROOT/'data/legacy_site/manifest.json').is_file():
                legacy=client.get('/api/results')
                assert legacy.status_code==200 and legacy.json()['available'] is True
                for symbol in ('HDFCBANK.NS','ICICIBANK.NS','TCS.NS','RELIANCE.NS','TATASTEEL.NS','^NSEI'):
                    history=client.get('/api/history',params={'symbol':symbol})
                    assert history.status_code==200 and history.json()['available'] is True
            if (ROOT/'web/dist/results.json').is_file():
                legacy = client.get('/results.json')
                assert legacy.status_code == 200 and legacy.json()['available'] is True
                assert client.get('/history/INDEX_NSEI.json').status_code == 200
            else:
                print('No baked legacy static files; local legacy API is used when data/legacy_site is present.')
        print('Local package checks passed: 6 assets/models, 9 risk and 8 price comparisons per asset, frontend, and legacy results/history when bundled.')
        return
    import uvicorn
    print('\nBullBench MarkovLab - private local bundle')
    print(f'Open http://127.0.0.1:{args.port}/')
    print(f'MarkovLab results: http://127.0.0.1:{args.port}/#/markovlab/tcs/experiments')
    print('Keep this terminal open. Press Ctrl+C to stop. No data downloads or model training occur at startup.\n')
    uvicorn.run(app, host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
