import itertools
import numpy as np
import pytest
from nse_forecast.unit4.hmm import GaussianHMM, forward_backward, viterbi


def test_hand_check_forward_backward_and_viterbi():
    # Two observations, two states: enumerate all four paths independently.
    pi = np.array([.6,.4]); a=np.array([[.7,.3],[.4,.6]])
    b=np.array([[.5,.1],[.4,.3]])
    paths=list(itertools.product(range(2),repeat=2))
    weights=np.array([pi[i]*b[0,i]*a[i,j]*b[1,j] for i,j in paths])
    ll, filt, smooth, counts=forward_backward(np.log(b),pi,a)
    assert np.exp(ll)==pytest.approx(.1246)
    np.testing.assert_allclose(filt[0],[.3/.34,.04/.34])
    np.testing.assert_allclose(smooth[0],[sum(w for w,p in zip(weights,paths) if p[0]==i)/weights.sum() for i in range(2)])
    np.testing.assert_allclose(counts, weights.reshape(2,2)/weights.sum())
    assert tuple(viterbi(np.log(b),pi,a)) == paths[weights.argmax()]
    np.testing.assert_allclose(filt.sum(axis=1),1)
    np.testing.assert_allclose(smooth.sum(axis=1),1)


def test_filter_cannot_see_future_but_smoothing_can():
    pi=np.array([.6,.4]);a=np.array([[.9,.1],[.1,.9]])
    b=np.log([[.5,.1],[.4,.3],[.2,.8]])
    original=forward_backward(b,pi,a)
    altered=b.copy();altered[2]=np.log([.99,.01])
    changed=forward_backward(altered,pi,a)
    np.testing.assert_allclose(original[1][:2],changed[1][:2])
    assert not np.allclose(original[2][:2],changed[2][:2])


def test_em_and_scaled_tail_probability():
    # Small deterministic numerical fixture, not market training data.
    x=np.array([[-2.],[-1.8],[-2.2],[2.],[1.8],[2.2],[-2.],[-1.9],[2.1],[1.9]])
    h=GaussianHMM(max_iter=100).fit(x)
    assert np.all(np.diff(h.trace_) >= -1e-5)
    assert np.isfinite(h.trace_).all()
    np.testing.assert_allclose(h.filter(x).sum(axis=1),1)
    risk=h.risk(x,threshold=1,return_mean=.2,return_scale=.5)
    from scipy.stats import norm
    mu=.2+.5*h.means_[:,0];sd=.5*np.sqrt(h.variances_[:,0])
    expected=h.filter(x)@h.transition_@(norm.sf(1,mu,sd)+norm.cdf(-1,mu,sd))
    np.testing.assert_allclose(risk,expected)
    assert ((risk>=0)&(risk<=1)).all()


def test_underflow_and_invalid_parameters():
    result=forward_backward(np.full((1000,2),-1000.),[.5,.5],[[.9,.1],[.1,.9]])
    assert np.isfinite(result[0])
    with pytest.raises(ValueError):forward_backward([[0,0]],[1,1],[[.5,.5],[.5,.5]])


def test_batched_transition_counts_match_reference_recursions():
    from scipy.special import logsumexp
    pi=np.array([.6,.4]);a=np.array([[.7,.3],[.4,.6]])
    emission=np.log([[.5,.1],[.4,.3],[.2,.6],[.3,.4]])
    alpha=np.empty_like(emission);alpha[0]=np.log(pi)+emission[0]
    for i in range(1,len(emission)):
        alpha[i]=emission[i]+logsumexp(alpha[i-1,:,None]+np.log(a),axis=0)
    beta=np.zeros_like(emission)
    for i in range(len(emission)-2,-1,-1):beta[i]=logsumexp(np.log(a)+emission[i+1]+beta[i+1],axis=1)
    counts=np.zeros_like(a)
    for i in range(len(emission)-1):
        xi=alpha[i,:,None]+np.log(a)+emission[i+1]+beta[i+1]
        counts+=np.exp(xi-logsumexp(xi))
    ll,filtered,gamma,actual=forward_backward(emission,pi,a)
    np.testing.assert_allclose(actual,counts,rtol=1e-12,atol=1e-14)
    np.testing.assert_allclose(filtered,np.exp(alpha-logsumexp(alpha,axis=1,keepdims=True)),rtol=1e-12)
    assert ll==pytest.approx(logsumexp(alpha[-1]))
