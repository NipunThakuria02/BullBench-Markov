import numpy as np
import pandas as pd
import pytest
from nse_forecast.experiments.lab import observations, scoring
from nse_forecast.ingest.exploratory import prepare_exploratory


def test_exploratory_import_preserves_missing_first_previous_close():
    raw=b'Date,Open,High,Low,Close,Volume\n2024-07-08,100,110,90,105,10\n2024-07-09,105,112,100,110,20\n'
    _,canonical,manifest,audit=prepare_exploratory(raw,'TCS','https://finance.yahoo.com','2024-07-10T10:00:00Z','yfinance')
    from io import BytesIO
    bars=pd.read_csv(BytesIO(canonical))
    assert np.isnan(bars.previous_close.iloc[0])
    assert bars.previous_close.iloc[1]==105
    assert manifest['research_track']=='exploratory'
    assert manifest['published_at'] is None
    assert audit['g0_passed'] is False


def test_calendar_gaps_never_create_imputed_bars():
    bars=pd.DataFrame({'session_date':['2024-07-08','2024-07-10'],'close':[100.,102.],'previous_close':[99.,101.]})
    calendar=[dict(session_date=d,session_type='regular') for d in ['2024-07-08','2024-07-09','2024-07-10']]
    with pytest.raises(ValueError,match='Missing/noncalendar'):
        observations(bars,calendar,'verified_exchange_previous_close')
    with pytest.raises(ValueError,match='verified'):
        observations(bars,calendar,'mixed_adjusted_unadjusted')


def test_metrics_can_be_recomputed_from_predictions():
    y=np.array([0,1]);p=np.array([.2,.8])
    metric=scoring(y,p,.5)
    assert metric['brier']==pytest.approx(.04)
    assert metric['log_loss']==pytest.approx(-np.log(.8))
    assert metric['events']==1 and metric['macro_f1']==1


def test_index_basis_is_explicit_and_calendar_is_not_claimed_verified():
    bars=pd.DataFrame({'instrument':['NIFTY 50']*2,'session_date':['2023-04-03','2023-04-04'],
                       'close':[100.,101.],'previous_close':[np.nan,100.],'price_basis':['official_index_points']*2})
    calendar=[dict(session_date=d,session_type='unverified_observed') for d in bars.session_date]
    result=observations(bars,calendar,'exploratory_index_close')
    assert result.empty  # Two supplied observations cannot satisfy the 60-session warm-up.
    altered=bars.copy();altered['instrument']='TCS'
    with pytest.raises(ValueError,match='NIFTY 50'):
        observations(altered,calendar,'exploratory_index_close')
    with pytest.raises(ValueError,match='Special-session'):
        observations(bars,calendar,'verified_exchange_previous_close')


def test_one_class_validation_has_probability_scores_but_no_invented_classification_metrics():
    metric=scoring(np.array([0,0]),np.array([.1,.2]),.5)
    assert metric['n']==2 and metric['events']==0 and metric['base_rate']==0
    assert metric['brier']==pytest.approx(.025)
    assert np.isfinite(metric['log_loss'])
    assert metric['pr_auc'] is None and metric['balanced_accuracy'] is None and metric['macro_f1'] is None
