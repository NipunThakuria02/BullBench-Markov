"""Run the pre-tagged exploratory historical test once per immutable instrument bundle."""
import hashlib
import json
import os
from pathlib import Path
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

ROOT=Path(__file__).resolve().parents[1]
JOBS=('hdfcbank','icicibank','tcs','reliance','tatasteel','nifty50')


def execute(slug):
    os.chdir(ROOT);sys.path.insert(0,str(ROOT/'src'))
    from nse_forecast.experiments.lab import run
    c=json.loads((ROOT/'config'/f'historical-{slug}.json').read_text())
    out=ROOT/'model_registry'/f'{slug}-historical-v1'
    if out.exists():
        m=json.loads((out/'manifest.json').read_text())
        if m['config']!=c or m.get('final_test_evaluated') is not True:raise ValueError('Immutable test differs')
        for name,sha in m['files_sha256'].items():
            if hashlib.sha256((out/name).read_bytes()).hexdigest()!=sha:raise ValueError('Saved test integrity failure')
    else:m=run(c,out)
    return dict(asset=c['asset'],bundle=out.name,trained_through=m['trained_through'],
                evaluation_start=m['evaluation_start'],evaluation_end=m['evaluation_end'],
                metrics=m['metrics'],price_metrics=m['price_metrics'],failed_models=m['failed_models'])


def main():
    os.chdir(ROOT)
    for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
    results=[]
    with ProcessPoolExecutor(max_workers=2) as pool:
        for f in as_completed([pool.submit(execute,slug) for slug in JOBS]):
            r=f.result();results.append(r);print(json.dumps(r),flush=True)
            destination=ROOT/'reports/historical-v1.json';destination.parent.mkdir(exist_ok=True)
            destination.write_text(json.dumps(dict(status='exploratory_locked_historical_test',results=results),indent=2)+'\n')
    equities=[r['metrics']['HMM']['brier_skill'] for r in results if r['asset']!='NIFTY 50']
    report=dict(status='exploratory_locked_historical_test',mean_five_equity_hmm_brier_skill=sum(equities)/len(equities),
                notice='Descriptive historical result, not untouched/prospective, not official G0–G4 certification.',results=sorted(results,key=lambda r:r['asset']))
    (ROOT/'docs/HISTORICAL_RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# Locked exploratory historical results','',report['notice'],'',f"Mean five-equity HMM Brier skill: {report['mean_five_equity_hmm_brier_skill']:.6f}",'',
           '| Instrument | Test targets | Events / targets | HMM Brier | HMM skill | Lowest Brier model |','|---|---|---|---|---|---|']
    for r in report['results']:
        h=r['metrics']['HMM'];best=min(r['metrics'],key=lambda name:r['metrics'][name]['brier'])
        lines.append(f"| {r['asset']} | {r['evaluation_start']}–{r['evaluation_end']} | {h['events']} / {h['n']} | {h['brier']:.6f} | {h['brier_skill']:.6f} | {best} |")
    (ROOT/'docs/HISTORICAL_RESULTS.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':main()
