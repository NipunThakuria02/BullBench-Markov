"""Causal development benchmark and JSON/NumPy HMM bundles, without test access."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.special import ndtr
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss, log_loss, average_precision_score, balanced_accuracy_score, f1_score
from xgboost import XGBClassifier
from ..unit4.hmm import GaussianHMM

FEATURES = ['return', 'abs_return', 'vol_5', 'vol_10', 'vol_20', 'vol_60']


def read_snapshots(root, asset):
    frames=[]
    hashes=[]
    for directory in sorted(Path(root).iterdir()):
        path=directory/'manifest.json'
        if not path.exists() or directory.name.startswith('.'):continue
        manifest=json.loads(path.read_text())
        if manifest['instrument'] != asset:continue
        for name,key in [('source.csv','raw_sha256'),('bars.csv','canonical_sha256')]:
            if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=manifest[key]:
                raise ValueError(f'Snapshot integrity failure: {directory.name}/{name}')
        frames.append(pd.read_csv(directory/'bars.csv'))
        hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
    if not frames:raise ValueError('No imported snapshots for this asset')
    bars=pd.concat(frames).sort_values('session_date')
    if bars.duplicated(['instrument','session_date']).any():
        raise ValueError('Overlapping snapshots require explicit reconciliation; no silent deduplication')
    return bars.reset_index(drop=True), hashes


def observations(bars, calendar, price_basis):
    """Rows are forecast origins. Labels are added separately using next session."""
    exploratory=price_basis in ('exploratory_adjusted_close','exploratory_index_close')
    if not exploratory and price_basis != 'verified_exchange_previous_close':
        raise ValueError('Only explicitly verified same-file previous-close returns currently supported')
    calendar=pd.DataFrame(calendar)
    if not {'session_date','session_type'}.issubset(calendar):
        raise ValueError('Explicit official session calendar with session_type required')
    if calendar.session_date.duplicated().any() or not calendar.session_date.is_monotonic_increasing:
        raise ValueError('Calendar must be unique and sorted')
    allowed=('regular','unverified_observed') if exploratory else ('regular',)
    if not calendar.session_type.isin(allowed).all():
        raise ValueError('Special-session modelling policy unresolved; provide a regular-only research segment')
    if price_basis=='exploratory_index_close':
        if 'instrument' not in bars or not bars.instrument.eq('NIFTY 50').all() or not bars.price_basis.eq('official_index_points').all():
            raise ValueError('Index-close basis requires NIFTY 50 index-point observations')
    # No missing session is bridged. Dataset must match a contiguous calendar segment.
    dates=calendar.session_date.tolist()
    if bars.session_date.tolist() != [d for d in dates if bars.session_date.min()<=d<=bars.session_date.max()]:
        raise ValueError('Missing/noncalendar sessions; no return or rolling window may bridge gaps')
    if exploratory:
        bars=bars.copy()
        bars['previous_close']=bars.close.shift(1)
        bars=bars.iloc[1:].copy()
    if bars.previous_close.isna().any() or (bars.previous_close<=0).any():
        raise ValueError('Verified previous-close observations required; index adapter does not invent them')
    result=bars.copy()
    result['return']=np.log(result.close/result.previous_close)
    result['abs_return']=result['return'].abs()
    for n in [5,10,20,60]:result[f'vol_{n}']=result['return'].rolling(n).std()
    return result.replace([np.inf,-np.inf],np.nan).dropna(subset=FEATURES).reset_index(drop=True)


def scoring(y,p,threshold):
    p=np.clip(np.asarray(p,dtype=np.float64),1e-12,1-1e-12)
    two_classes=len(np.unique(y))==2
    return dict(n=len(y),events=int(np.sum(y)),base_rate=float(np.mean(y)),
                brier=float(brier_score_loss(y,p)),log_loss=float(log_loss(y,p,labels=[0,1])),
                pr_auc=float(average_precision_score(y,p)) if two_classes else None,
                balanced_accuracy=float(balanced_accuracy_score(y,p>=threshold)) if two_classes else None,
                macro_f1=float(f1_score(y,p>=threshold,average='macro',zero_division=0)) if two_classes else None,
                decision_threshold=float(threshold))


def split_masks(frame, config):
    train=frame.target_session<=config['train_end']
    val=(frame.session_date>config['train_end']) & (frame.target_session<=config['validation_end'])
    if config.get('evaluation_mode')=='locked_historical_test':
        val &= frame.session_date>=config['validation_start']
        test=(frame.session_date>=config['test_start']) & (frame.target_session<=config['test_end'])
        for left,right in [(config['train_end'],config['validation_start']),(config['validation_end'],config['test_start'])]:
            if ((frame.session_date>left)&(frame.session_date<right)).sum()<60:
                raise ValueError('At least 60 observed-session embargo origins required')
        if not train.any() or not val.any() or not test.any() or (train&val).any() or (val&test).any():
            raise ValueError('Invalid chronological split')
        return train,val,test
    return train,val,val


def run(config, output):
    """Development only; training and validation boundaries are explicit and mandatory."""
    out=Path(output)
    if out.exists():raise ValueError('Choose a new output directory; runs are immutable')
    locked=config.get('evaluation_mode')=='locked_historical_test'
    if locked:
        protocol=Path(config['protocol_file'])
        if hashlib.sha256(protocol.read_bytes()).hexdigest()!=config['protocol_sha256']:
            raise ValueError('Frozen exploratory protocol checksum differs')
        if not config['train_end']<config['validation_start']<config['validation_end']<config['test_start']<config['test_end']:
            raise ValueError('Invalid locked split ordering')
        import subprocess
        tag=subprocess.check_output(['git','rev-parse','exploratory-protocol-v1^{commit}'],text=True).strip()
        if not tag:raise ValueError('Protocol must be committed/tagged before test access')
    exploratory=config.get('research_track')=='exploratory'
    fields=['train_end','validation_end','asset','price_basis']
    if not exploratory:fields+=['calendar_file','corporate_action_evidence','permission_evidence']
    for field in fields:
        if not config.get(field):raise ValueError(f'Missing explicit configuration: {field}')
    if config['train_end']>=config['validation_end']:raise ValueError('Training must precede validation')
    # Evidence is user-reviewed documentation, not a self-certification produced by the parser.
    evidence={}
    for field in ['calendar_file','corporate_action_evidence','permission_evidence']:
        if field not in config:continue
        p=Path(config[field]);evidence[field]=hashlib.sha256(p.read_bytes()).hexdigest()
    bars,hashes=read_snapshots(config['snapshots'],config['asset'])
    # Do not inspect later observations, including any possible final-test window.
    bars=bars.loc[bars.session_date<=config['test_end' if locked else 'validation_end']]
    if exploratory and not config.get('calendar_file'):
        calendar=[dict(session_date=d,session_type='unverified_observed') for d in bars.session_date]
    else:calendar=json.loads(Path(config['calendar_file']).read_text())
    frame=observations(bars,calendar,config['price_basis'])
    if exploratory and (pd.to_datetime(frame.session_date).diff().dt.days.dropna()>5).any():
        raise ValueError('Long observed-calendar gaps require reconciliation before rolling features')
    frame['target_session']=frame.session_date.shift(-1)
    frame['next_return']=frame['return'].shift(-1)
    frame['next_close']=frame.close.shift(-1)
    frame['next_previous_close']=frame.previous_close.shift(-1)
    frame=frame.dropna(subset=['next_return'])
    train,val,evaluation=split_masks(frame,config)
    if train.sum()<120 or val.sum()<20:raise ValueError('Need at least 120 training pairs and 20 validation pairs after warmup')
    threshold_train=train & (frame.target_session<=config.get('threshold_train_end',config['train_end']))
    theta=float(frame.loc[threshold_train,'next_return'].abs().quantile(config.get('event_quantile',.8)))
    if theta<=0:raise ValueError('Degenerate event threshold')
    y=(frame.next_return.abs()>theta).astype(int).to_numpy()
    if len(np.unique(y[train]))<2:raise ValueError('Both classes required in training')
    validation_two_classes=len(np.unique(y[val]))==2
    x=frame[FEATURES].to_numpy();mean=x[train].mean(axis=0);scale=np.maximum(x[train].std(axis=0),1e-12)
    z=(x-mean)/scale
    # Include all chronological observations for filtering, never for fitting.
    runs=[];candidates=[]
    for k in config.get('states',[2,3,4]):
        for seed in config.get('seeds',[42,43,44]):
            try:
                h=GaussianHMM(n_states=k,seed=seed,max_iter=config.get('max_iter',200)).fit(z[train,:1])
                development=np.flatnonzero(val)[-1]+1
                p=h.risk(z[:development,:1],theta,mean[0],scale[0])
                brier=brier_score_loss(y[:development][val.to_numpy()[:development]],p[val.to_numpy()[:development]])
                runs.append(dict(states=k,seed=seed,converged=h.converged_,trace=h.trace_,validation_brier=float(brier)))
                if h.converged_:candidates.append((brier,h,p))
            except ValueError as error:runs.append(dict(states=k,seed=seed,error=str(error)))
            print(f"{config['asset']}: states={k}, seed={seed}, converged={runs[-1].get('converged',False)}",flush=True)
    if not candidates:
        out.mkdir(parents=True)
        (out/'candidate_failures.json').write_text(json.dumps(dict(config=config,hmm_runs=runs),indent=2))
        raise ValueError(f'No converged HMM candidate; diagnostics preserved in {out}')
    _,h,hmm_p=min(candidates,key=lambda v:v[0])
    if locked:hmm_p=h.risk(z[:,:1],theta,mean[0],scale[0])
    prevalence=float(y[train].mean())
    probabilities={'HMM':hmm_p,'Prevalence':np.full(len(y),prevalence),
                   'Persistence':(frame.abs_return.to_numpy()>theta).astype(float)}
    labels=(frame.abs_return.to_numpy()>theta).astype(int)
    counts=np.ones((2,2))
    for a,b in zip(labels[train],y[train]):counts[a,b]+=1
    probabilities['ObservableMarkov']=(counts/counts.sum(axis=1,keepdims=True))[labels,1]
    variance=np.empty(len(frame));variance[0]=float(np.var(frame.loc[train,'return']))
    for i in range(1,len(frame)):variance[i]=.94*variance[i-1]+.06*frame['return'].iloc[i]**2
    probabilities['EWMA']=2*ndtr(-theta/np.sqrt(np.maximum(variance,1e-12)))
    failures={}
    models={'LogisticRegression':LogisticRegression(max_iter=1000),
            'RandomForest':RandomForestClassifier(n_estimators=150,max_depth=6,min_samples_leaf=15,random_state=42,n_jobs=2),
            'XGBoost':XGBClassifier(n_estimators=150,max_depth=3,learning_rate=.03,random_state=42,n_jobs=1)}
    for name,model in models.items():
        try:
            model.fit(z[train],y[train]);probabilities[name]=model.predict_proba(z)[:,1]
        except Exception as error:failures[name]=str(error)
    try:
        from arch import arch_model
        from scipy.stats import t
        fitted=arch_model(frame.loc[train,'return'].to_numpy()*100,mean='Zero',vol='GARCH',p=1,q=1,dist='t').fit(disp='off')
        if fitted.convergence_flag!=0:raise ValueError('GARCH did not converge')
        pars=fitted.params;nu=float(pars['nu']);omega=float(pars['omega']);alpha=float(pars['alpha[1]']);beta=float(pars['beta[1]'])
        v=float(fitted.conditional_volatility[-1]**2);p=np.full(len(frame),np.nan)
        for i in range(int(np.flatnonzero(train)[-1]),len(frame)):
            v=omega+alpha*(100*frame['return'].iloc[i])**2+beta*v
            p[i]=2*t.sf(theta*100/np.sqrt(v)*np.sqrt(nu/(nu-2)),df=nu)
        probabilities['GARCH-t']=p
    except Exception as error:failures['GARCH-t']=str(error)
    rows=[];metrics={}
    for name,p in probabilities.items():
        # Threshold selected on validation; its F1 is descriptive, not confirmatory.
        choices=np.linspace(.05,.95,19)
        threshold=max(choices,key=lambda q:f1_score(y[val],p[val]>=q,average='macro',zero_division=0)) if validation_two_classes else .5
        metrics[name]=scoring(y[evaluation],p[evaluation],threshold)
        metrics[name]['brier_skill']=1-metrics[name]['brier']/brier_score_loss(y[evaluation],np.full(evaluation.sum(),prevalence))
        for i in np.flatnonzero(evaluation):rows.append(dict(asset=config['asset'],origin_session=frame.session_date.iloc[i],target_session=frame.target_session.iloc[i],model=name,actual=int(y[i]),probability=float(p[i])))
    # Never reconstruct with a future source-file previous close. Pending an as-of
    # adjustment-factor contract, block price comparisons containing action jumps.
    filters=h.filter(z[:,:1]);price_metrics={};price_rows=[]
    if not np.allclose(frame.next_previous_close,frame.close,rtol=1e-8,atol=1e-8):
        failures['SecondaryPrice']='Action-consistent as-of reconstruction factors required; future previous-close fields cannot be used as predictors'
    else:
        from ..models import predict_models
        for suffix,features in [('',z),('+HMM',np.column_stack([z,filters]))]:
            table=pd.DataFrame(features,columns=[f'f{i}' for i in range(features.shape[1])])
            table['target']=frame.next_return.to_numpy()
            columns=[c for c in table if c!='target']
            try:
                # Sequential ARIMA state updates must consume the embargo/validation
                # observations in order, without parameter refits or skipping time.
                future=frame.index>np.flatnonzero(train)[-1] if locked else val
                predictions=predict_models(table.loc[train],table.loc[future],columns)
                for name,returns in predictions.items():
                    if suffix and name in ('Naive','ARIMA'):continue
                    # Legacy forecasters learn log returns here, hence exp reconstruction.
                    if locked:returns=returns[evaluation[future].to_numpy()]
                    predicted=frame.loc[evaluation,'close'].to_numpy()*np.exp(returns)
                    error=predicted-frame.loc[evaluation,'next_close'].to_numpy()
                    price_metrics[name+suffix]=dict(mae=float(np.abs(error).mean()),rmse=float(np.sqrt((error**2).mean())))
                    for i,pred in zip(np.flatnonzero(evaluation),predicted):
                        price_rows.append(dict(model=name+suffix,origin_session=frame.session_date.iloc[i],target_session=frame.target_session.iloc[i],actual=float(frame.next_close.iloc[i]),predicted=float(pred)))
            except Exception as error:failures['SecondaryPrice'+suffix]=str(error)
    out.mkdir(parents=True)
    predictions=pd.DataFrame(rows)
    predictions.to_csv(out/'predictions.csv',index=False)
    from .diagnostics import probability_diagnostics
    reliability,intervals=probability_diagnostics(predictions)
    (out/'calibration.json').write_text(json.dumps(reliability,indent=2))
    (out/'uncertainty.json').write_text(json.dumps(intervals,indent=2))
    pd.DataFrame(price_rows).to_csv(out/'price_predictions.csv',index=False)
    np.savez(out/'hmm.npz',initial=h.initial_,transition=h.transition_,means=h.means_,variances=h.variances_,mean=mean,scale=scale,theta=theta)
    metadata=dict(schema_version=1,status='development_candidate',research_track=config.get('research_track','official_unverified'),asset=config['asset'],config=config,
                  evidence_sha256=evidence,snapshot_manifest_sha256=hashes,features=FEATURES,
                  metrics=metrics,price_metrics=price_metrics,failed_models=failures,hmm_runs=runs,
                  selected_states=h.n_states,selected_seed=h.seed,trained_through=config['train_end'],
                  calendar_policy='observed sessions, type/duration unverified' if exploratory and not config.get('calendar_file') else 'explicit supplied calendar',
                  final_test_evaluated=locked,calibration='Raw probabilities; no fitted probability calibrator. Reliability bins are descriptive.',
                  classification_metrics_estimable=len(np.unique(y[evaluation]))==2,
                  validation_warnings=[] if validation_two_classes else ['Only one outcome class occurred in validation; PR-AUC, balanced accuracy and macro-F1 are not estimable. Decision threshold fixed at 0.5 without tuning.'],
                  caveat='Model and decision thresholds selected on validation; all scores are exploratory.' if validation_two_classes else 'HMM state/seed selected on validation; classification threshold fixed at 0.5 because validation has one outcome class. All scores are exploratory.')
    if locked:
        metadata.update(status='locked_historical_test',evaluation_mode='locked_historical_test',
                        protocol_sha256=config['protocol_sha256'],protocol_commit=tag,
                        evaluation_start=predictions.target_session.min(),evaluation_end=predictions.target_session.max(),
                        validation_period=dict(start=config['validation_start'],end=config['validation_end']),
                        caveat='Locked historical test on the exploratory Yahoo/manual-index track. State/seed and decision cutoffs selected on validation only. This historical period was inspected for the original price task; it is not untouched or prospective. Official calendar/adjustment verification and G0–G4 certification remain pending.')
        sensitivity=[]
        for block in (10,20,40):
            _,interval=probability_diagnostics(predictions,block_length=block)
            for row in interval:row['limitation']='Conditional on frozen fitted predictions; no refitting; no cross-asset multiplicity correction.'
            sensitivity.extend(interval)
        (out/'bootstrap_sensitivity.json').write_text(json.dumps(sensitivity,indent=2))
    from importlib.metadata import version
    metadata['library_versions']={name:version(name) for name in ['numpy','pandas','scikit-learn','statsmodels','xgboost','arch']}
    metadata['code_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('src/nse_forecast').rglob('*.py')}
    metadata['files_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()}
    (out/'manifest.json').write_text(json.dumps(metadata,indent=2,allow_nan=False))
    return metadata


def main():
    import argparse
    parser=argparse.ArgumentParser(description='Offline development-only benchmark; never evaluate final test')
    parser.add_argument('--config',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    try:run(json.loads(Path(args.config).read_text()),args.output)
    except (ValueError,OSError,KeyError) as error:parser.exit(1,f'Experiment blocked: {error}\n')

if __name__=='__main__':main()
