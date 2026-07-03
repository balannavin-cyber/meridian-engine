from __future__ import annotations

"""
measure_rate_sensitivity.py  --  ENH-07 A / Phase 2 (MEASUREMENT, read-only)

Answers the gate question: does swapping the BS risk-free rate (flat 6.5% ->
basis-implied r = ln(F/S)/T) actually move the gamma REGIME on real NIFTY
historical chains, or is it a no-op refinement?

For a sample of NIFTY (trade_date, bar_ts, nearest-expiry) cohorts it:
  1. reads every strike's close from hist_option_bars_1m
  2. reads spot (hist_spot_bars_1m) and front-month futures (hist_future_bars_1m
     series 1) at the SAME raw bar_ts  (all three tables share the IST-labeled
     clock -- proven in the basis backfill; pair on raw bar_ts, no shift)
  3. solves IV per strike at r=6.5% AND r=basis-implied, computes gamma both ways
  4. rebuilds net_gex / flip_level / regime BOTH ways using the LIVE engine's
     exact logic (signed_gamma_exposure incl. the TD-NEW-2 deep-ITM rejection,
     build_strike_exposure_map, compute_flip_level, determine_regime)
  5. reports per-cohort deltas + the aggregate REGIME-FLIP RATE.

Writes nothing. NIFTY-led (SENSEX basis too noisy for a per-bar rate).

    python3 measure_rate_sensitivity.py <from_date> <to_date> [--n 30] [--ist-hour 12]
"""

import argparse
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import os
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

UTC = timezone.utc
R_FLAT = 0.065
RATE_FLOOR_DAYS = 25   # ENH-07A-P2 rate-floor v1
FRONT_FUT_SERIES = 1   # NIFTY


# ── inline BS (validated against the documented worked example) ──────────
SQRT_2PI = math.sqrt(2.0 * math.pi)


def _norm_pdf(x): return math.exp(-0.5 * x * x) / SQRT_2PI
def _norm_cdf(x): return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _d1(S, K, T, r, sig): return (math.log(S / K) + (r + 0.5 * sig * sig) * T) / (sig * math.sqrt(T))


def bs_price(S, K, T, r, sig, otype):
    if T <= 0 or sig <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = _d1(S, K, T, r, sig)
    d2 = d1 - sig * math.sqrt(T)
    if otype.upper().startswith("C"):
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)


def bs_gamma(S, K, T, r, sig):
    if T <= 0 or sig <= 0 or S <= 0 or K <= 0:
        return 0.0
    return _norm_pdf(_d1(S, K, T, r, sig)) / (S * sig * math.sqrt(T))


def implied_vol(price, S, K, T, r, otype, lo=1e-4, hi=5.0, tol=1e-3, mx=100):
    if price <= 0 or T <= 0 or S <= 0 or K <= 0:
        return None
    flo = bs_price(S, K, T, r, lo, otype) - price
    fhi = bs_price(S, K, T, r, hi, otype) - price
    if flo * fhi > 0:
        return None
    for _ in range(mx):
        mid = 0.5 * (lo + hi)
        fm = bs_price(S, K, T, r, mid, otype) - price
        if abs(fm) < tol:
            return mid
        if flo * fm < 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


def basis_implied_r(F, S, T):
    if F is None or S is None or S <= 0 or F <= 0 or T <= 0:
        return None
    return math.log(F / S) / T


# ── live-engine gamma logic (verbatim semantics from compute_gamma_metrics_local) ──
def signed_gamma_exposure(gamma, oi, otype, strike, spot):
    if gamma == 0.0 or oi <= 0.0 or spot <= 0.0:
        return 0.0
    if strike > 0 and abs(strike - spot) / spot > 0.05 and abs(gamma) > 5e-5:
        return 0.0   # TD-NEW-2 Part A deep-ITM rejection
    base = gamma * oi * (spot ** 2) / 1e7
    return -base if otype.upper().startswith("P") else base


def build_strike_map(rows, spot, gamma_key):
    m = defaultdict(float)
    for r in rows:
        K = r["strike"]
        if K <= 0:
            continue
        m[K] += signed_gamma_exposure(r[gamma_key], r["oi"], r["otype"], K, spot)
    return dict(sorted(m.items()))


def compute_flip_level(strike_map, spot):
    if not strike_map:
        return None
    strikes = sorted(strike_map.keys())
    cum, running = [], 0.0
    for k in strikes:
        running += strike_map[k]
        cum.append((k, running))
    if len(cum) < 2 or spot is None or spot <= 0:
        return None
    atm = min(range(len(strikes)), key=lambda i: abs(strikes[i] - spot))
    cand = []
    for i in range(atm, 0, -1):
        kc, cc = cum[i]; kp, cp = cum[i - 1]
        if cp == 0.0: cand.append(kp); break
        if cc == 0.0: cand.append(kc); break
        if (cp < 0 < cc) or (cp > 0 > cc):
            d = cc - cp
            if d != 0: cand.append(kp + (-cp / d) * (kc - kp))
            break
    for i in range(atm, len(cum) - 1):
        kc, cc = cum[i]; kn, cn = cum[i + 1]
        if cc == 0.0: cand.append(kc); break
        if cn == 0.0: cand.append(kn); break
        if (cc < 0 < cn) or (cc > 0 > cn):
            d = cn - cc
            if d != 0: cand.append(kc + (-cc / d) * (kn - kc))
            break
    return min(cand, key=lambda x: abs(x - spot)) if cand else None


def regime(net_gex, flip):
    if flip is None:
        return "NO_FLIP"
    return "LONG_GAMMA" if net_gex >= 0 else "SHORT_GAMMA"


# ── supabase (read-only) ─────────────────────────────────────────────────
def _cfg():
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or os.getenv("SUPABASE_ANON_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL / key")
    return url, {"apikey": key, "Authorization": f"Bearer {key}"}


def sel(table, params, page=1000):
    base, h = _cfg()
    out, off = [], 0
    while True:
        p = dict(params, limit=str(page), offset=str(off))
        r = requests.get(f"{base}/rest/v1/{table}?{urlencode(p)}", headers=h, timeout=90)
        if r.status_code >= 400:
            raise RuntimeError(f"SELECT {table} {r.status_code}: {r.text}")
        b = r.json()
        out.extend(b)
        if len(b) < page:
            break
        off += page
    return out


def parse_ts(v):
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        return None


def nifty_iid():
    rows = sel("instruments", {"select": "id,symbol", "symbol": "eq.NIFTY"})
    if not rows:
        raise RuntimeError("NIFTY not in instruments")
    return rows[0]["id"]


def candidate_dates(d0, d1, n):
    """Pure-Python evenly-spaced calendar dates across [d0,d1]. No DB query.
    Oversamples ~3x so weekends/holidays/empty-bar days can be skipped while
    still reaching n measured cohorts. main() stops once n are measured."""
    from datetime import date
    start = date.fromisoformat(d0)
    end = date.fromisoformat(d1)
    span = (end - start).days
    if span <= 0:
        return [d0]
    k = max(1, span // max(1, n * 3))
    out, cur = [], start
    while cur <= end:
        out.append(cur.isoformat())
        cur = cur + timedelta(days=k)
    return out


def price_at(table, iid, d, ist_hour, extra=None):
    """nearest bar to <ist_hour>:00 on trade_date d, from `table` (close)."""
    params = {"select": "bar_ts,close",
              "instrument_id": f"eq.{iid}", "trade_date": f"eq.{d}", "order": "bar_ts.asc"}
    if extra:
        params.update(extra)
    rows = sel(table, params)
    if not rows:
        return None, None
    target = ist_hour
    best = min(rows, key=lambda r: abs((parse_ts(r["bar_ts"]).hour + parse_ts(r["bar_ts"]).minute / 60.0) - target))
    return parse_ts(best["bar_ts"]), best


def _measure_one(iid, d, ist_hour):
    """Measure one cohort for trade_date d. Returns a result dict or None if
    the date has no usable chain (weekend/holiday/empty)."""
    bts, spot_row = price_at("hist_spot_bars_1m", iid, d, ist_hour)
    if bts is None:
        return None
    spot = float(spot_row["close"])
    _, fut_row = price_at("hist_future_bars_1m", iid, d, ist_hour,
                          extra={"contract_series": "eq.1", "bar_ts": f"eq.{bts.isoformat()}"})
    if not fut_row:
        _, fut_row = price_at("hist_future_bars_1m", iid, d, ist_hour, extra={"contract_series": "eq.1"})
    F = float(fut_row["close"]) if fut_row else None

    orows = sel("hist_option_bars_1m", {
        "select": "strike,option_type,close,oi,expiry_date",
        "instrument_id": f"eq.{iid}", "bar_ts": f"eq.{bts.isoformat()}",
        "order": "expiry_date.asc",
    })
    if not orows:
        return None
    exps = [r.get("expiry_date") for r in orows if r.get("expiry_date") and r["expiry_date"] >= d]
    if not exps:
        return None
    expiry = min(exps)
    chain = [r for r in orows if r.get("expiry_date") == expiry and float(r.get("close") or 0) > 0]
    if len(chain) < 6:
        return None
    T = (datetime.fromisoformat(expiry).date() - datetime.fromisoformat(d).date()).days / 365.0
    if T <= 0:
        return None
    dte_days = (datetime.fromisoformat(expiry).date() - datetime.fromisoformat(d).date()).days
    T_rate = max(dte_days, RATE_FLOOR_DAYS) / 365.0   # ENH-07A-P2 rate-floor v1
    rb = basis_implied_r(F, spot, T_rate)
    if rb is None:
        return None

    built = []
    for r in chain:
        K = float(r["strike"]); P = float(r["close"]); ot = str(r["option_type"])
        oi = float(r.get("oi") or 0)
        iv0 = implied_vol(P, spot, K, T, R_FLAT, ot)
        ivb = implied_vol(P, spot, K, T, rb, ot)
        if iv0 is None or ivb is None:
            continue
        built.append({"strike": K, "otype": ot, "oi": oi,
                      "g0": bs_gamma(spot, K, T, R_FLAT, iv0),
                      "gb": bs_gamma(spot, K, T, rb, ivb)})
    if len(built) < 6:
        return None

    m0 = build_strike_map(built, spot, "g0")
    mb = build_strike_map(built, spot, "gb")
    ng0 = sum(m0.values()); ngb = sum(mb.values())
    f0 = compute_flip_level(m0, spot); fb = compute_flip_level(mb, spot)
    r0 = regime(ng0, f0); rbg = regime(ngb, fb)
    reg_flip = r0 != rbg
    line = (f"{d:>11} {spot:>8.0f} {F if F else 0:>8.0f} {rb*100:>7.2f}% "
            f"{ng0:>10.2f} {ngb:>10.2f} {f0 if f0 else 0:>9.0f} {fb if fb else 0:>9.0f} "
            f"{r0:>11} {rbg:>11} {'YES' if reg_flip else '.':>6}")
    return {
        "sign_flip": (ng0 >= 0) != (ngb >= 0),
        "reg_flip": reg_flip,
        "flip_shift": abs(fb - f0) if (f0 is not None and fb is not None) else None,
        "line": line,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("from_date"); ap.add_argument("to_date")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--ist-hour", type=float, default=12.0)
    args = ap.parse_args()

    iid = nifty_iid()
    candidates = candidate_dates(args.from_date, args.to_date, args.n)
    print(f"Scanning up to {len(candidates)} candidate dates for {args.n} cohorts "
          f"at ~{args.ist_hour:.0f}:00 IST\n", flush=True)

    hdr = f"{'date':>11} {'spot':>8} {'F':>8} {'r_basis':>8} {'ngex@6.5':>10} {'ngex@rb':>10} {'flip@6.5':>9} {'flip@rb':>9} {'reg@6.5':>11} {'reg@rb':>11} {'FLIP?':>6}"
    print(hdr); print("-" * len(hdr), flush=True)

    cohorts = 0
    sign_flips = 0
    regime_flips = 0
    flip_shifts = []

    for d in candidates:
        if cohorts >= args.n:
            break
        try:
            ok = _measure_one(iid, d, args.ist_hour)
        except Exception as e:
            print(f"{d:>11}  skip ({type(e).__name__}: {str(e)[:40]})", flush=True)
            continue
        if ok is None:
            continue
        cohorts += 1
        if ok["sign_flip"]:
            sign_flips += 1
        if ok["reg_flip"]:
            regime_flips += 1
        if ok["flip_shift"] is not None:
            flip_shifts.append(ok["flip_shift"])
        print(ok["line"], flush=True)

    print("\n" + "=" * 60)
    print(f"cohorts measured      : {cohorts}")
    if cohorts:
        print(f"net_gex sign flips    : {sign_flips}  ({100*sign_flips/cohorts:.1f}%)")
        print(f"regime classification flips : {regime_flips}  ({100*regime_flips/cohorts:.1f}%)")
        if flip_shifts:
            fs = sorted(flip_shifts)
            print(f"flip_level shift (pts): median={fs[len(fs)//2]:.1f}  max={fs[-1]:.1f}")
    print("=" * 60)
    print("VERDICT: regime-flip ~0% -> ENH-07 A is a no-op; solve with flat r.")
    print("         regime-flip non-trivial -> A is material; carry basis-r into the solve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
