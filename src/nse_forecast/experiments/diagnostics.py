"""Descriptive diagnostics from saved predictions; never refits or touches test data."""
import numpy as np
import pandas as pd


def probability_diagnostics(predictions, repetitions=4000, block_length=20, seed=42):
    if predictions.duplicated(['asset','target_session','model']).any():raise ValueError('Duplicate forecasts')
    calibration=[];intervals=[]
    for (asset,model),part in predictions.groupby(['asset','model']):
        bins=np.minimum((part.probability.to_numpy()*10).astype(int),9)
        for index in range(10):
            values=part.loc[bins==index]
            calibration.append(dict(asset=asset,model=model,bin=index,n=len(values),mean_probability=float(values.probability.mean()) if len(values) else None,event_rate=float(values.actual.mean()) if len(values) else None))
    for asset,part in predictions.groupby('asset'):
        outcomes=part.groupby('target_session').actual.nunique()
        if (outcomes!=1).any():raise ValueError('Comparator outcomes disagree')
        table=part.assign(loss=(part.probability-part.actual)**2).pivot(index='target_session',columns='model',values='loss').sort_index()
        if table.isna().any().any() or 'Prevalence' not in table:raise ValueError('Common target dates and prevalence baseline required')
        n=len(table)
        if n<2*block_length:continue
        rng=np.random.default_rng(seed);models=[m for m in table if m!='Prevalence']
        delta=table[models].to_numpy()-table.Prevalence.to_numpy()[:,None]
        values=[]
        for start in range(0,repetitions,128):
            count=min(128,repetitions-start)
            heads=rng.integers(0,n,size=(count,int(np.ceil(n/block_length))))
            idx=((heads[...,None]+np.arange(block_length))%n).reshape(count,-1)[:,:n]
            values.append(delta[idx].mean(axis=1))
        samples=np.concatenate(values)
        for i,model in enumerate(models):
            low,high=np.quantile(samples[:,i],[.025,.975])
            adjusted=np.quantile(samples[:,i],[.025/len(models),1-.025/len(models)])
            intervals.append(dict(asset=asset,model=model,endpoint='Brier loss difference vs prevalence (negative is better)',estimate=float(delta[:,i].mean()),low_95=float(low),high_95=float(high),simultaneous_low_95=float(adjusted[0]),simultaneous_high_95=float(adjusted[1]),block_length=block_length,repetitions=repetitions,seed=seed,limitation='Conditional on selected validation predictions; post-selection and cross-asset multiplicity not corrected'))
    return calibration,intervals
