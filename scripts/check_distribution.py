"""Check source vs private local package contents using only the standard library."""
import argparse
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ASSETS=('HDFCBANK','ICICIBANK','TCS','RELIANCE','TATASTEEL','NIFTY 50')
HELPERS=('START_HERE.md','requirements-local.lock','scripts/run_local.py','START_WINDOWS.bat','start_local.sh')


def check(root,local=False):
    root=Path(root);missing=[name for name in HELPERS if not (root/name).is_file()]
    available=set();data=root/'data/exploratory_snapshots'
    if data.is_dir():
        for p in data.glob('*/manifest.json'):
            try:
                asset=json.loads(p.read_text())['instrument']
                if all((p.parent/name).is_file() for name in ('source.csv','bars.csv')):available.add(asset)
            except (OSError,ValueError,KeyError):continue
    artifacts=[]
    for asset in ASSETS:
        pointer=root/'model_registry'/(asset.replace(' ','_')+'.json')
        try:
            bundle=(pointer.parent/json.loads(pointer.read_text())['bundle']).resolve()
            if not bundle.is_relative_to((root/'model_registry').resolve()):raise ValueError('Invalid pointer')
            required=('manifest.json','hmm.npz')
            if json.loads((bundle/'manifest.json').read_text()).get('status')!='inference_only':required+=('predictions.csv',)
            for name in required:
                if not (bundle/name).is_file():raise ValueError('Incomplete bundle')
            with zipfile.ZipFile(bundle/'hmm.npz') as z:
                if not {'mean.npy','scale.npy'}.issubset(z.namelist()):raise ValueError('Missing scaler arrays')
            artifacts.append(asset)
        except (OSError,ValueError,KeyError,zipfile.BadZipFile):pass
    if local:
        if not (root/'web/dist/index.html').is_file():missing.append('web/dist/index.html')
        missing += ['data/exploratory_snapshots/ ('+a+')' for a in ASSETS if a not in available]
        missing += ['model_registry/ ('+a+' bundle/pointer/scaler)' for a in ASSETS if a not in artifacts]
    return dict(mode='private local package' if local else 'source checkout',ok=not missing,missing=missing,
                data_directory='data/exploratory_snapshots',assets_with_data=sorted(available),assets_with_models=artifacts,
                note='GitHub source intentionally excludes private observations/models and compiled web/dist. The private local ZIP includes them. Scalers live inside hmm.npz, not a separate scaler.npz.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--local',action='store_true');args=p.parse_args()
    result=check(ROOT,args.local);print(json.dumps(result,indent=2));raise SystemExit(0 if result['ok'] else 1)

if __name__=='__main__':main()
