"""Log-space Gaussian HMM. Filtering and retrospective decoding are separate."""
from dataclasses import dataclass
import numpy as np
from scipy.special import logsumexp


def probability_array(value, shape, name):
    value = np.asarray(value, dtype=float)
    if value.shape != shape or not np.isfinite(value).all() or (value < 0).any():
        raise ValueError(f'Invalid {name}')
    if not np.allclose(value.sum(axis=-1), 1):
        raise ValueError(f'{name} must sum to one')
    return value


def forward(log_emissions, initial, transition):
    """Forward likelihood and causal filtering only; no backward pass."""
    emission = np.asarray(log_emissions, dtype=float)
    if emission.ndim != 2 or not len(emission) or not np.isfinite(emission).all():
        raise ValueError('Finite, nonempty T x K log emissions required')
    t, k = emission.shape
    pi = probability_array(initial, (k,), 'initial')
    a = probability_array(transition, (k, k), 'transition')
    with np.errstate(divide='ignore'):
        la, lp = np.log(a), np.log(pi)
    alpha = np.empty_like(emission)
    alpha[0] = lp + emission[0]
    for i in range(1, t):
        alpha[i] = emission[i] + np.logaddexp.reduce(alpha[i-1, :, None] + la, axis=0)
    likelihood = logsumexp(alpha[-1])
    if not np.isfinite(likelihood):
        raise ValueError('Sequence has zero likelihood')
    filters = np.exp(alpha - logsumexp(alpha, axis=1, keepdims=True))
    return float(likelihood), filters, alpha


def forward_backward(log_emissions, initial, transition):
    """Retrospective posteriors and expected transition counts for EM/diagnostics."""
    emission=np.asarray(log_emissions,dtype=float)
    likelihood,filters,alpha=forward(emission,initial,transition)
    t,k=emission.shape
    with np.errstate(divide='ignore'):la=np.log(transition)
    beta = np.zeros_like(alpha)
    for i in range(t-2, -1, -1):
        beta[i] = np.logaddexp.reduce(la + emission[i+1] + beta[i+1], axis=1)
    joint = alpha + beta
    gamma = np.exp(joint - logsumexp(joint, axis=1, keepdims=True))
    counts = np.zeros((k, k))
    if t > 1:
        log_xi = alpha[:-1, :, None] + la[None, :, :] + emission[1:, None, :] + beta[1:, None, :]
        counts = np.exp(log_xi-logsumexp(log_xi,axis=(1,2),keepdims=True)).sum(axis=0)
    return float(likelihood), filters, gamma, counts


def viterbi(log_emissions, initial, transition):
    """Retrospective maximum joint-probability path; never a forecasting feature."""
    emission = np.asarray(log_emissions, dtype=float)
    forward_backward(emission, initial, transition)  # validate stochastic parameters
    with np.errstate(divide='ignore'):
        la, lp = np.log(transition), np.log(initial)
    score = lp + emission[0]
    parents = np.zeros(emission.shape, dtype=int)
    for i in range(1, len(emission)):
        candidate = score[:, None] + la
        parents[i] = candidate.argmax(axis=0)
        score = candidate.max(axis=0) + emission[i]
    path = np.empty(len(emission), dtype=int)
    path[-1] = score.argmax()
    for i in range(len(emission)-1, 0, -1):
        path[i-1] = parents[i, path[i]]
    return path


@dataclass
class GaussianHMM:
    n_states: int = 2
    max_iter: int = 200
    tolerance: float = 1e-5
    covariance_floor: float = 1e-4
    seed: int = 42

    def _observations(self, x):
        x = np.asarray(x, dtype=float)
        if x.ndim != 2 or not len(x) or not np.isfinite(x).all():
            raise ValueError('Finite nonempty T x D observations required')
        return x

    def log_emissions(self, x):
        x = self._observations(x)
        if x.shape[1] != self.means_.shape[1]:
            raise ValueError('Observation dimensions differ from fitted model')
        delta = x[:, None, :] - self.means_[None, :, :]
        return -.5 * (np.log(2*np.pi*self.variances_)[None, :, :] + delta**2/self.variances_[None, :, :]).sum(axis=2)

    def fit(self, x):
        x = self._observations(x)
        if self.n_states < 2 or len(x) < self.n_states or self.covariance_floor <= 0 or self.max_iter < 1:
            raise ValueError('Invalid state count, covariance floor, iteration count or insufficient rows')
        rng = np.random.default_rng(self.seed)
        self.initial_ = np.full(self.n_states, 1/self.n_states)
        self.transition_ = np.full((self.n_states, self.n_states), .1/self.n_states) + np.eye(self.n_states)*.9
        self.means_ = x[rng.choice(len(x), self.n_states, replace=False)].copy()
        self.variances_ = np.tile(np.maximum(x.var(axis=0), self.covariance_floor), (self.n_states, 1))
        self.trace_ = []
        self.converged_ = False
        for iteration in range(self.max_iter):
            ll, _, gamma, counts = forward_backward(self.log_emissions(x), self.initial_, self.transition_)
            self.trace_.append(ll)
            if len(self.trace_) > 1:
                gain = ll-self.trace_[-2]
                if gain < -1e-5:
                    # Covariance constraints or numeric issues must not be hidden.
                    raise ValueError('EM likelihood decreased beyond numeric tolerance')
                if gain <= self.tolerance:
                    self.converged_ = True
                    break
            if iteration == self.max_iter-1:
                break  # final recorded likelihood corresponds to saved parameters
            weight = gamma.sum(axis=0)
            if (weight < 1e-8).any():
                raise ValueError('Degenerate HMM state occupancy')
            self.initial_ = np.maximum(gamma[0], 1e-12); self.initial_ /= self.initial_.sum()
            counts = np.maximum(counts, 1e-12)
            self.transition_ = counts/counts.sum(axis=1, keepdims=True)
            self.means_ = gamma.T @ x / weight[:, None]
            delta = x[:, None, :] - self.means_[None, :, :]
            self.variances_ = np.maximum((gamma[:, :, None]*delta**2).sum(axis=0)/weight[:, None], self.covariance_floor)
        return self

    def filter(self, x):
        return forward(self.log_emissions(x), self.initial_, self.transition_)[1]

    def smooth(self, x):
        return forward_backward(self.log_emissions(x), self.initial_, self.transition_)[2]

    def decode(self, x):
        return viterbi(self.log_emissions(x), self.initial_, self.transition_)

    def risk(self, x, threshold, return_mean=0., return_scale=1.):
        from scipy.special import ndtr
        if threshold <= 0 or return_scale <= 0:
            raise ValueError('Positive event threshold and return scale required')
        mu, sigma = self.means_[:, 0], np.sqrt(self.variances_[:, 0])
        # Transform BOTH bounds; centering makes them asymmetric in model space.
        upper = (threshold-return_mean)/return_scale
        lower = (-threshold-return_mean)/return_scale
        tails = ndtr((mu-upper)/sigma) + ndtr((lower-mu)/sigma)
        return self.filter(x) @ self.transition_ @ tails
