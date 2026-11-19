"""Separate newest-data HMM fit: state exploration only, never a new test score."""
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT);sys.path.insert(0,str(ROOT/'src'))
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import numpy as np
from nse_forecast.experiments.lab import read_snapshots,observations,FEATURES
from nse_forecast.unit4.hmm import GaussianHMM


def main():
    report=[]
    for slug in ('hdfcbank','icicibank','tcs','reliance','tatasteel','nifty50'):
        reference=ROOT/'model_registry'/f'{slug}-historical-v1'
        m=json.loads((reference/'manifest.json').read_text());out=ROOT/'model_registry'/f'{slug}-latest-v1'
        if not out.exists():
            c=dict(m['config']);c['train_end']=c['test_end'];c['evaluation_mode']='inference_only'
            bars,hashes=read_snapshots(c['snapshots'],m['asset']);bars=bars.loc[bars.session_date<=c['train_end']]
            f=observations(bars,[dict(session_date=d,session_type='unverified_observed') for d in bars.session_date],c['price_basis'])
            x=f[FEATURES].to_numpy();mean=x.mean(axis=0);scale=np.maximum(x.std(axis=0),1e-12);z=(x-mean)/scale
            attempts=[]
            for budget in (300,1200):
                h=GaussianHMM(n_states=m['selected_states'],seed=m['selected_seed'],max_iter=budget).fit(z[:,:1])
                attempts.append(dict(max_iter=budget,steps=len(h.trace_),converged=h.converged_))
                if h.converged_:break
            if not h.converged_:
                report.append(dict(asset=m['asset'],status='blocked_nonconvergence'));continue
            with np.load(reference/'hmm.npz') as arrays:theta=float(arrays['theta'])
            out.mkdir()
            np.savez(out/'hmm.npz',initial=h.initial_,transition=h.transition_,means=h.means_,variances=h.variances_,mean=mean,scale=scale,theta=theta)
            record=dict(schema_version=1,asset=m['asset'],status='inference_only',research_track='exploratory',config=c,features=FEATURES,
                        trained_through=str(f.session_date.max()),fit_attempts=attempts,snapshot_manifest_sha256=hashes,selected_states=h.n_states,selected_seed=h.seed,
                        metrics={},price_metrics={},final_test_evaluated=False,reference_evaluation=reference.name,
                        notice='Newest-data state explorer model. No out-of-sample score. Forecasting requires later verified observations/calendar.',
                        files_sha256={'hmm.npz':hashlib.sha256((out/'hmm.npz').read_bytes()).hexdigest()})
            (out/'manifest.json').write_text(json.dumps(record,indent=2))
        raw=(out/'manifest.json').read_bytes();latest=json.loads(raw)
        for name,digest in latest['files_sha256'].items():
            if hashlib.sha256((out/name).read_bytes()).hexdigest()!=digest:raise ValueError('Newest model integrity failure')
        pointer=dict(bundle=out.name,manifest_sha256=hashlib.sha256(raw).hexdigest(),approved=True,approval_scope='local_exploratory_only')
        p=ROOT/'model_registry'/(m['asset'].replace(' ','_')+'.json');temporary=p.with_suffix('.tmp');temporary.write_text(json.dumps(pointer));os.replace(temporary,p)
        report.append(dict(asset=m['asset'],status='inference_only',trained_through=latest['trained_through']))
        print(report[-1],flush=True)
    (ROOT/'docs/LATEST_MODELS.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
