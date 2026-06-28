"""
core/bs_engine.py  --  shared Black-Scholes engine (ENH-07 A / Phase 1).

Pure stdlib (math only). Extracted as the single source of truth for IV /
gamma / price so backfill_gamma_metrics.py, backfill_volatility_metrics.py,
the replay reconstructor, and the rate-sensitivity probe all share one
implementation (Enhancement Register noted the duplication; this is the fix).

r is a PARAMETER — there is no hardcoded 6.5% here. basis_implied_r() supplies
a futures-basis-derived rate when ENH-07 A is enabled; callers default to
0.065 only by explicit choice, not by the engine's default.

Validated against the documented worked example
(2025-10-15 NIFTY 24000 PE, S=25218, K=24000, P=18, T=8/365, r=0.065):
    IV = 21.45%  (doc 21.46%, within bisection tol)
    gamma = 0.000134  (exact)
Convention: T in YEARS as calendar-days/365.
"""
from __future__ import annotations

import math

SQRT_2PI = math.sqrt(2.0 * math.pi)


def norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / SQRT_2PI


def norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
    return (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * math.sqrt(T))


def bs_price(S: float, K: float, T: float, r: float, sigma: float, option_type: str) -> float:
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = _d1(S, K, T, r, sigma)
    d2 = d1 - sigma * math.sqrt(T)
    if option_type.upper() in ("CE", "CALL", "C"):
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)


def bs_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = _d1(S, K, T, r, sigma)
    return norm_pdf(d1) / (S * sigma * math.sqrt(T))


def implied_vol(price: float, S: float, K: float, T: float, r: float, option_type: str,
                lo: float = 1e-4, hi: float = 5.0, tol: float = 1e-3, max_iter: int = 100):
    """Bisection IV solve. Returns sigma (decimal fraction) or None if the
    market price is unreachable within [lo, hi] (no bracket)."""
    if price <= 0 or T <= 0 or S <= 0 or K <= 0:
        return None
    f_lo = bs_price(S, K, T, r, lo, option_type) - price
    f_hi = bs_price(S, K, T, r, hi, option_type) - price
    if f_lo * f_hi > 0:
        return None
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        f_mid = bs_price(S, K, T, r, mid, option_type) - price
        if abs(f_mid) < tol:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return 0.5 * (lo + hi)


def basis_implied_r(futures: float, spot: float, T: float):
    """ENH-07 A: r = ln(F/S) / T (annualized). For index futures this is the
    NET carry (r - q), which is what the cost-of-carry pricing relation uses —
    arguably more correct than a flat 6.5% that ignores dividend yield.
    Returns None on degenerate inputs (caller falls back to a default r)."""
    if futures is None or spot is None or spot <= 0 or futures <= 0 or T <= 0:
        return None
    return math.log(futures / spot) / T
