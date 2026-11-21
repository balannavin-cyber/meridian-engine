"""Statistics for the MR-FOI M1/M2 pre-registration run (2026-11-17).

scipy is NOT installed on this box and is not installed by this run. What the
pre-registration needs is therefore sourced three ways, all stated:

  * Wilcoxon signed-rank, one-sided        -> IMPORTED UNMODIFIED from
    services/tape_scoring/wilcoxon.py (exact permutation to n_eff <= 60, midrank
    tie correction, zeros dropped and counted). That file is hashed in
    docs/tape/scoring_hashes.md; it is imported, never edited.
  * N(d1) and the Black-Scholes pieces     -> core/bs_engine.py (norm_cdf, _d1).
    bs_engine has no delta function, so bs_delta is defined here on top of _d1.
  * Spearman rho, OLS, bootstrap           -> written here. Neither a rank
    correlation nor an OLS helper exists anywhere in the repo.

Every routine written here is checked against an INDEPENDENT brute-force
computation in selftest() before any outcome may be scored. The scorer refuses
to run with --score if selftest() fails. An expected value is computed, never
recalled.

Interval method, fixed by the pre-registration (sections 3 and 4):
  percentile bootstrap, 10,000 resamples, seed 20261117. M2 resamples whole
  SESSIONS (section 4, "session-clustered").
"""
import itertools
import math
import os
import random
import sys
from fractions import Fraction

import numpy as np

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "services", "tape_scoring"))

import wilcoxon as _wx                      # noqa: E402  (hashed, imported unmodified)
from core.bs_engine import norm_cdf, _d1    # noqa: E402

SEED = 20261117
B_RESAMPLES = 10000
PERM_EXACT_MAX = 8          # full enumeration of n! permutations at or below this
PERM_MC = 200000            # Monte-Carlo permutations above it, at SEED


# --------------------------------------------------------------------------
# Black-Scholes delta (bs_engine has price and gamma, but no delta)
# --------------------------------------------------------------------------
def bs_delta(S, K, T, r, sigma, option_type):
    """Call delta = N(d1); put delta = N(d1) - 1.  Pre-registration section 2."""
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return None
    nd1 = norm_cdf(_d1(S, K, T, r, sigma))
    return nd1 if option_type.upper() in ("CE", "C", "CALL") else nd1 - 1.0


# --------------------------------------------------------------------------
# Wilcoxon, one-sided, H: median < 0   (M1 Test 1)
# --------------------------------------------------------------------------
def wilcoxon_less(diffs):
    res = _wx.signed_rank_less(list(diffs))
    return {"p": float(res["p"]), "method": res["method"], "n_eff": res["n_eff"],
            "zeros_dropped": res["zeros_dropped"], "w_plus": float(res["w_plus"])}


# --------------------------------------------------------------------------
# Spearman rho  (M1 Test 2), one-sided H: rho > 0
# --------------------------------------------------------------------------
def _midranks(vals):
    """Average ranks for ties. Same convention as wilcoxon.midranks, on raw values."""
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [None] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        r = Fraction(i + j + 2, 2)
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return [float(r) for r in ranks]


def _pearson(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    xm, ym = x - x.mean(), y - y.mean()
    den = math.sqrt(float((xm * xm).sum()) * float((ym * ym).sum()))
    if den == 0.0:
        return float("nan")
    return float((xm * ym).sum()) / den


def spearman_rho(x, y):
    """rho = Pearson correlation of the midranks (correct under ties)."""
    return _pearson(_midranks(list(x)), _midranks(list(y)))


def spearman_greater(x, y, seed=SEED, n_mc=PERM_MC):
    """One-sided p for H: rho > 0.

    Primary p is a permutation p-value: exact (all n! relabellings) for
    n <= PERM_EXACT_MAX, Monte-Carlo at `seed` above it. The asymptotic t
    p-value is returned BESIDE it as a cross-check -- a parity claim is made by
    comparing the two numbers, never by asserting they agree.
    """
    x = list(x)
    y = list(y)
    n = len(x)
    rho = spearman_rho(x, y)
    rx, ry = _midranks(x), _midranks(y)

    if n <= PERM_EXACT_MAX:
        ge = tot = 0
        for perm in itertools.permutations(ry):
            tot += 1
            if _pearson(rx, list(perm)) >= rho - 1e-12:
                ge += 1
        p_perm, method = ge / tot, "exact"
    else:
        rnd = random.Random(seed)
        shuffled = list(ry)
        ge = 0
        for _ in range(n_mc):
            rnd.shuffle(shuffled)
            if _pearson(rx, shuffled) >= rho - 1e-12:
                ge += 1
        p_perm, method = (ge + 1) / (n_mc + 1), "monte-carlo"   # +1: never reports 0

    if n > 2 and abs(rho) < 1.0:
        t = rho * math.sqrt((n - 2) / (1 - rho * rho))
        p_t = _student_t_sf(t, n - 2)
    else:
        p_t = float("nan")
    return {"rho": rho, "p": p_perm, "method": method, "n": n, "p_asymptotic_t": p_t}


def _student_t_sf(t, df):
    """P(T > t) for Student t, via the regularised incomplete beta (stdlib only)."""
    if df <= 0:
        return float("nan")
    x = df / (df + t * t)
    ib = _betainc(df / 2.0, 0.5, x)
    return 0.5 * ib if t > 0 else 1.0 - 0.5 * ib


def _betainc(a, b, x):
    """Regularised incomplete beta I_x(a,b), continued fraction (NR 6.4)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta)
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1.0 - math.exp(math.log(1 - x) * b + math.log(x) * a - lbeta) * _betacf(b, a, 1 - x) / b


def _betacf(a, b, x, itmax=300, eps=3e-16):
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < 1e-300:
        d = 1e-300
    d = 1.0 / d
    h = d
    for m in range(1, itmax + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        c = 1.0 + aa / c
        if abs(d) < 1e-300:
            d = 1e-300
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        c = 1.0 + aa / c
        if abs(d) < 1e-300:
            d = 1e-300
        if abs(c) < 1e-300:
            c = 1e-300
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


# --------------------------------------------------------------------------
# OLS  (M2)
# --------------------------------------------------------------------------
def ols(X, y):
    """Least squares with an intercept prepended. Returns the coefficient vector
    [a, b0, b1, ...]. numpy.linalg.lstsq; checked against the normal equations
    in selftest()."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    A = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return beta


# --------------------------------------------------------------------------
# Bootstrap: percentile intervals, 10,000 resamples, seed 20261117
# --------------------------------------------------------------------------
def boot_percentile(values, stat, n=B_RESAMPLES, seed=SEED, alpha=0.05):
    """Percentile bootstrap over a flat list of items."""
    rnd = random.Random(seed)
    k = len(values)
    if k == 0:
        return {"point": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": 0,
                "resamples": 0, "method": "percentile"}
    reps = []
    for _ in range(n):
        sample = [values[rnd.randrange(k)] for _ in range(k)]
        s = stat(sample)
        if s is not None and not (isinstance(s, float) and math.isnan(s)):
            reps.append(s)
    reps.sort()
    return {"point": stat(values), "lo": _pct(reps, 100 * alpha / 2),
            "hi": _pct(reps, 100 * (1 - alpha / 2)), "n": k,
            "resamples": len(reps), "method": "percentile"}


def boot_cluster(clusters, stat, n=B_RESAMPLES, seed=SEED, alpha=0.05):
    """Session-clustered percentile bootstrap: whole clusters are resampled with
    replacement, then `stat` is applied to the concatenated rows."""
    rnd = random.Random(seed)
    keys = list(clusters.keys())
    k = len(keys)
    if k == 0:
        return {"point": float("nan"), "lo": float("nan"), "hi": float("nan"),
                "clusters": 0, "resamples": 0, "method": "percentile, session-clustered"}
    reps = []
    for _ in range(n):
        rows = []
        for _ in range(k):
            rows.extend(clusters[keys[rnd.randrange(k)]])
        s = stat(rows)
        if s is not None and not (isinstance(s, float) and math.isnan(s)):
            reps.append(s)
    reps.sort()
    allrows = [r for key in keys for r in clusters[key]]
    return {"point": stat(allrows), "lo": _pct(reps, 100 * alpha / 2),
            "hi": _pct(reps, 100 * (1 - alpha / 2)), "clusters": k,
            "resamples": len(reps), "method": "percentile, session-clustered"}


def _pct(sorted_vals, q):
    if not sorted_vals:
        return float("nan")
    pos = (len(sorted_vals) - 1) * q / 100.0
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def median(vals):
    v = sorted(float(x) for x in vals)
    if not v:
        return float("nan")
    m = len(v) // 2
    return v[m] if len(v) % 2 else 0.5 * (v[m - 1] + v[m])
