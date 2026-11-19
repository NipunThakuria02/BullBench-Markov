"""Bounded, resumable development-only benchmarks for all six supplied instruments."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT=Path(__file__).resolve().parents[1]
JOBS=[('HDFCBANK','hdfcbank'),('ICICIBANK','icicibank'),('TCS','tcs'),('RELIANCE','reliance'),('TATASTEEL','tatasteel'),('NIFTY 50','nifty50')]


def execute(job):
    asset,slug=job
    os.chdir(ROOT);sys.path.insert(0,str(ROOT/'src'))
    from nse_forecast.experiments.lab import run,read_snapshots
    config=json.loads((ROOT/'config'/f'exploratory-{slug}.json').read_text())
    output=ROOT/'model_registry'/f'{slug}-development'
    reused=False
    try:
        if output.exists():
            manifest=json.loads((output/'manifest.json').read_text())
            if manifest['config']!=config or manifest.get('final_test_evaluated') is not False:
                raise ValueError('Existing run configuration differs; use a new explicit run version')
            for name,digest in manifest['files_sha256'].items():
                path=(output/name).resolve()
                if path.parent!=output.resolve() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Existing run integrity failure')
            _,current=read_snapshots(config['snapshots'],asset)
            if sorted(current)!=sorted(manifest['snapshot_manifest_sha256']):raise ValueError('Input snapshot versions differ')
            reused=True
        else:
            manifest=run(config,output)
        subprocess.run([sys.executable,'-m','nse_forecast.experiments.activate','--bundle',output.name,'--exploratory'],check=True,cwd=ROOT)
        metrics=manifest['metrics'];rank=sorted(metrics,key=lambda name:metrics[name]['brier'])
        return dict(asset=asset,bundle=output.name,status='completed',reused=reused,train_end=config['train_end'],
                    validation_end=config['validation_end'],sessions=metrics['HMM']['n'],events=metrics['HMM']['events'],
                    hmm_brier=metrics['HMM']['brier'],hmm_skill=metrics['HMM']['brier_skill'],best_model=rank[0],
                    best_brier=metrics[rank[0]]['brier'],risk_models=len(metrics),price_models=len(manifest['price_metrics']),
                    selected_states=manifest['selected_states'],selected_seed=manifest['selected_seed'],
                    failed_models=manifest['failed_models'],final_test_evaluated=False)
    except Exception as error:
        traceback.print_exc()
        return dict(asset=asset,bundle=output.name,status='failed',error=str(error),final_test_evaluated=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers',type=int,default=2)
    parser.add_argument('--report',default='reports/all-development.json')
    args=parser.parse_args()
    if args.workers not in (1,2):parser.error('Use one or two workers to bound native library concurrency')
    os.chdir(ROOT)
    for key in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
    results=[]
    destination=ROOT/args.report;destination.parent.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures=[executor.submit(execute,job) for job in JOBS]
        for future in as_completed(futures):
            result=future.result();results.append(result)
            destination.write_text(json.dumps(dict(status='development_only',results=sorted(results,key=lambda r:r['asset']),final_test_evaluated=False),indent=2)+'\n')
            print(json.dumps(result),flush=True)
    if any(r['status']!='completed' for r in results):raise SystemExit(1)
    print(f'All six development runs available; summary: {destination}',flush=True)

if __name__=='__main__':main()
