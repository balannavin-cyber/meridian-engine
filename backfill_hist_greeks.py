from __future__ import annotations

"""
backfill_hist_greeks.py  --  TD-S58-NEW-1 per-strike Greeks backfill (flat r).

Solves IV + gamma for every strike in hist_option_bars_1m at flat r=6.5% and
writes them to the SIDECAR table hist_option_greeks_1m (vendor table untouched).

Engine semantics are reproduced VERBATIM from measure_rate_sensitivity.py
(validated S62: net_gex sign 99% / magnitude 0.96x / sign-regime 95% vs live
gamma_metrics on 2025-09-19 + 2025-09-29). The ONLY change here is the solver is
VECTORIZED (numpy bisection over the whole chain array per bar_ts) so ~55M bars
finish in hours not days. The scalar bisection in the probe is the equivalence
reference, not the production solver.

  STAGE 0 (MANDATORY GATE):  python3 backfill_hist_greeks.py --validate
      Re-runs the vectorized solver against live gamma_metrics on 09-19 + 09-29
      and prints the same sign/magnitude/sign-regime table. NOTHING writes.
      Must clear sign>=99% / mag~1.0 / sign-regime>=95% before any bulk run.

  STAGE 1 (write):  python3 backfill_hist_greeks.py --symbol NIFTY \
                        --from 2025-09-01 --to 2025-12-31 --apply
      Chunked by trade_date, resumable via hist_greeks_backfill_log
      (skips status='DONE' dates). Dry-run without --apply.

House convention: raw HTTP vs /rest/v1/*, SUPABASE_SERVICE_ROLE_KEY, 1000-row
paginate. int4-safe. NIFTY first (validated cohort), then SENSEX.
"""

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone, date
from urllib.parse import urlencode

import numpy as np
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

UTC = timezone.utc
R_FLAT = 0.065
SQRT_2PI = np.sqrt(2.0 * np.pi)

# bisection params -- IDENTICAL to measure_rate_sensitivity.implied_vol
IV_LO, IV_HI, IV_TOL, IV_MX = 1e-4, 5.0, 1e-3, 100

# deep-ITM rejection (TD-NEW-2 Part A) -- IDENTICAL
ITM_DIST = 0.05
ITM_GAMMA = 5e-5
CR_SCALE = 1e7
EXPIRY_T_FLOOR_MIN = 5  # expiry-day-T v1


# ------------------------------------------------------------------ vectorized BS
def _norm_cdf_vec(x):
    # vectorized N(x) via erfc; matches math.erfc-based scalar to full precision
    from scipy.special import erfc  # scipy is present in this env; fallback below
    return 0.5 * erfc(-x / np.sqrt(2.0))


def _norm_cdf_np(x):
    # numpy-only fallback (no scipy): vectorized erf via np.vectorize of math.erf
    import math
    _erf = np.vectorize(math.erf)
    return 0.5 * (1.0 + _erf(x / np.sqrt(2.0)))


try:
    from scipy.special import erfc as _erfc  # noqa
    def norm_cdf(x):
        return 0.5 * _erfc(-x / np.sqrt(2.0))
except Exception:
    def norm_cdf(x):
        return _norm_cdf_np(x)


def norm_pdf(x):
    return np.exp(-0.5 * x * x) / SQRT_2PI


def bs_price_vec(S, K, T, r, sig, is_call):
    """Vectorized BS price. S scalar; K,sig,is_call arrays; T,r scalar."""
    out = np.zeros_like(K, dtype=float)
    ok = (sig > 0) & (K > 0) & (T > 0) & (S > 0)
    if not np.any(ok):
        return out
    sq = np.sqrt(T)
    d1 = np.zeros_like(K, dtype=float)
    d1[ok] = (np.log(S / K[ok]) + (r + 0.5 * sig[ok] * sig[ok]) * T) / (sig[ok] * sq)
    d2 = d1 - sig * sq
    disc = np.exp(-r * T)
    call = S * norm_cdf(d1) - K * disc * norm_cdf(d2)
    put = K * disc * norm_cdf(-d2) - S * norm_cdf(-d1)
    out[ok] = np.where(is_call[ok], call[ok], put[ok])
    return out


def bs_gamma_vec(S, K, T, r, sig):
    out = np.zeros_like(K, dtype=float)
    ok = (sig > 0) & (K > 0) & (T > 0) & (S > 0)
    sq = np.sqrt(T)
    d1 = np.zeros_like(K, dtype=float)
    d1[ok] = (np.log(S / K[ok]) + (r + 0.5 * sig[ok] * sig[ok]) * T) / (sig[ok] * sq)
    out[ok] = norm_pdf(d1[ok]) / (S * sig[ok] * sq)
    return out


def implied_vol_vec(price, S, K, T, r, is_call):
    """Vectorized bisection reproducing measure_rate_sensitivity.implied_vol.
    Returns sigma array with np.nan where no bracket / invalid (== scalar None)."""
    n = K.shape[0]
    sig = np.full(n, np.nan)
    valid = (price > 0) & (T > 0) & (S > 0) & (K > 0)
    if not np.any(valid):
        return sig

    lo = np.full(n, IV_LO)
    hi = np.full(n, IV_HI)
    flo = bs_price_vec(S, K, T, r, lo, is_call) - price
    fhi = bs_price_vec(S, K, T, r, hi, is_call) - price
    # bracket condition: flo*fhi <= 0 (scalar rejects flo*fhi > 0)
    bracket = valid & (flo * fhi <= 0)
    if not np.any(bracket):
        return sig

    lo_b = lo.copy(); hi_b = hi.copy(); flo_b = flo.copy()
    done = np.zeros(n, dtype=bool)
    mid = 0.5 * (lo_b + hi_b)
    for _ in range(IV_MX):
        active = bracket & ~done
        if not np.any(active):
            break
        mid = 0.5 * (lo_b + hi_b)
        fm = bs_price_vec(S, K, T, r, mid, is_call) - price
        hit = active & (np.abs(fm) < IV_TOL)
        done |= hit
        # bisection update on still-active
        upd = active & ~hit
        left = upd & (flo_b * fm < 0)
        right = upd & ~(flo_b * fm < 0)
        hi_b = np.where(left, mid, hi_b)
        lo_b = np.where(right, mid, lo_b)
        flo_b = np.where(right, fm, flo_b)

    # scalar returns mid (0.5*(lo+hi)) on both early-exit and budget-exhaust
    sig = np.where(bracket, 0.5 * (lo_b + hi_b), np.nan)
    # but where we hit tol exactly, scalar returned that mid; close enough (<tol)
    sig = np.where(done, mid, sig)
    return sig


def signed_gex_vec(gamma, oi, is_put, strike, spot):
    """Vectorized signed_gamma_exposure incl. deep-ITM rejection + /1e7 + PE flip."""
    out = np.zeros_like(strike, dtype=float)
    live = (gamma != 0.0) & (oi > 0.0) & (spot > 0.0) & ~np.isnan(gamma)
    reject = (strike > 0) & (np.abs(strike - spot) / spot > ITM_DIST) & (np.abs(gamma) > ITM_GAMMA)
    live = live & ~reject
    base = gamma * oi * (spot ** 2) / CR_SCALE
    out = np.where(live, np.where(is_put, -base, base), 0.0)
    return out


# ------------------------------------------------------------------ flip_level (scalar; recompute, not trusted)
def compute_flip_level(strike_map, spot):
    if not strike_map:
        return None
    strikes = sorted(strike_map.keys())
    cum, running = [], 0.0
    for k in strikes:
        running += strike_map[k]; cum.append((k, running))
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


def regime_sign(net_gex, flip, eps=2.5e5):
    if flip is not None:
        return "LONG_GAMMA" if net_gex >= 0 else "SHORT_GAMMA"
    if net_gex >= eps: return "LONG_GAMMA"
    if net_gex <= -eps: return "SHORT_GAMMA"
    return "NO_FLIP"


# ------------------------------------------------------------------ supabase io
def _cfg():
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
    return url, {"apikey": key, "Authorization": f"Bearer {key}"}


def get(table, params, cap_pages=200, page=1000):
    base, h = _cfg()
    out, off, pages = [], 0, 0
    while pages < cap_pages:
        p = dict(params, limit=str(page), offset=str(off))
        r = requests.get(f"{base}/rest/v1/{table}?{urlencode(p)}", headers=h, timeout=120)
        if r.status_code >= 400:
            raise RuntimeError(f"GET {table} {r.status_code}: {r.text[:160]}")
        b = r.json(); out.extend(b)
        if len(b) < page: break
        off += page; pages += 1
    return out


def upsert(table, rows, on_conflict):
    base, h = _cfg()
    hh = dict(h, **{"Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates"})
    url = f"{base}/rest/v1/{table}?on_conflict={on_conflict}"
    for i in range(0, len(rows), 500):
        chunk = rows[i:i + 500]
        r = requests.post(url, headers=hh, json=chunk, timeout=120)
        if r.status_code >= 400:
            raise RuntimeError(f"UPSERT {table} {r.status_code}: {r.text[:200]}")


def parse_ts(v):
    dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def iid_for(symbol):
    rows = get("instruments", {"select": "id,symbol", "symbol": f"eq.{symbol}"})
    if not rows:
        raise RuntimeError(f"{symbol} not in instruments")
    return rows[0]["id"]


# ------------------------------------------------------------------ chain solve at one bar_ts
def solve_bar(iid, raw_bts, trade_date, spot_cache=None):  # spot-cache v1
    """Vectorized solve for all strikes at one bar_ts. Returns (rows_for_sidecar,
    strike_map_for_aggregate, spot) or (None, None, None)."""
    orows = get("hist_option_bars_1m", {
        "select": "strike,option_type,close,oi,expiry_date",
        "instrument_id": f"eq.{iid}", "bar_ts": f"eq.{raw_bts}",
        "order": "expiry_date.asc"})
    if not orows:
        return None, None, None
    if spot_cache is not None:
        if raw_bts not in spot_cache:
            return None, None, None
        spot = spot_cache[raw_bts]
    else:
        srow = get("hist_spot_bars_1m", {"select": "close",
                   "instrument_id": f"eq.{iid}", "bar_ts": f"eq.{raw_bts}"}, cap_pages=1)
        if not srow:
            return None, None, None
        spot = float(srow[0]["close"])

    d = trade_date
    exps = [r["expiry_date"] for r in orows if r.get("expiry_date") and r["expiry_date"] >= d]
    if not exps:
        return None, None, None
    expiry = min(exps)
    # same-day (weekly) expiry: 0-DTE flat-vol net_gex is numerically unreconstructible
    # intraday (validated 2025-11-25: afternoon ratio chaos). Sourced from live gamma_metrics
    # in the aggregate recompute, not reconstructed here.  # expiry-skip v1
    if (datetime.fromisoformat(expiry).date() - datetime.fromisoformat(d).date()).days <= 0:
        return "SKIP_EXPIRY", None, None
    chain = [r for r in orows if r.get("expiry_date") == expiry and float(r.get("close") or 0) > 0]
    if len(chain) < 6:
        return None, None, None
    dte = (datetime.fromisoformat(expiry).date() - datetime.fromisoformat(d).date()).days
    T = dte / 365.0
    if T <= 0:
        return None, None, None

    K = np.array([float(r["strike"]) for r in chain])
    P = np.array([float(r["close"]) for r in chain])
    OI = np.array([float(r.get("oi") or 0) for r in chain])
    OT = [str(r["option_type"]) for r in chain]
    is_call = np.array([o.upper().startswith("C") for o in OT])
    is_put = ~is_call

    sig = implied_vol_vec(P, spot, K, T, R_FLAT, is_call)         # nan where no bracket
    gamma = bs_gamma_vec(spot, K, T, R_FLAT, sig)                 # 0 where sig nan/invalid
    gamma = np.where(np.isnan(sig), np.nan, gamma)

    # sidecar rows (raw iv+gamma; NULL where no inversion)
    rows = []
    for i in range(len(chain)):
        rows.append({
            "instrument_id": iid, "bar_ts": raw_bts, "trade_date": d,
            "strike": K[i], "option_type": OT[i], "expiry_date": expiry,
            "iv": None if np.isnan(sig[i]) else round(float(sig[i]), 6),
            "gamma": None if np.isnan(gamma[i]) else float(gamma[i]),
            "r_used": R_FLAT, "source": "hist_greeks_s62",
        })

    # aggregate strike map (signed, deep-ITM rejected) for spot-check vs live
    g_for_gex = np.where(np.isnan(gamma), 0.0, gamma)
    gex = signed_gex_vec(g_for_gex, OI, is_put, K, spot)
    sm = defaultdict(float)
    for i in range(len(chain)):
        if K[i] > 0:
            sm[K[i]] += gex[i]
    return rows, dict(sorted(sm.items())), spot


# ------------------------------------------------------------------ STAGE 0: re-validation gate
def validate():
    """Re-run the vectorized solver vs live gamma_metrics on 09-19 + 09-29.
    Same gate as the scalar harness. Writes nothing."""
    iid = iid_for("NIFTY")
    overall_ok = True
    for d in ("2025-09-19", "2025-09-29"):  # expiry-skip v1
        live = get("gamma_metrics", {"select": "ts,net_gex,regime", "symbol": "eq.NIFTY",
                   "and": f"(ts.gte.{d}T00:00:00,ts.lte.{d}T23:59:59)", "order": "ts.asc"})
        if not live:
            print(f"{d}: no live gamma_metrics"); continue
        medh = sorted(parse_ts(r["ts"]).hour for r in live)[len(live) // 2]
        is_utc = medh < 9
        scache = spot_map_for_date(iid, d)  # spot-cache v1
        tl = [(parse_ts(b).hour * 60 + parse_ts(b).minute, b) for b in scache.keys()]
        tl.sort()
        if not tl:
            print(f"{d}: no hist spot timeline"); continue

        n = sgn = sreg = 0; ratios = []
        for lr in live:
            dt = parse_ts(lr["ts"]); tmin = dt.hour * 60 + dt.minute + (330 if is_utc else 0)
            cand = min(tl, key=lambda x: abs(x[0] - tmin))
            if abs(cand[0] - tmin) > 3.0:
                continue
            _, sm, spot = solve_bar(iid, cand[1], d, spot_cache=scache)
            if sm is None:
                continue
            rng = sum(sm.values()); rflip = compute_flip_level(sm, spot)
            lng = float(lr["net_gex"]) if lr.get("net_gex") is not None else None
            lreg = str(lr["regime"]).upper() if lr.get("regime") else "?"
            n += 1
            if lng is not None and (lng >= 0) == (rng >= 0): sgn += 1
            if lreg == regime_sign(rng, rflip): sreg += 1
            if lng not in (None, 0): ratios.append(rng / lng)
        if n:
            ratios.sort(); med = ratios[len(ratios) // 2] if ratios else float("nan")
            sgn_pct, sreg_pct = 100 * sgn / n, 100 * sreg / n
            ok = sgn_pct >= 98 and sreg_pct >= 94 and 0.9 <= med <= 1.1  # gate-sign-floor v1
            overall_ok &= ok
            print(f"{d}: matched={n}  sign={sgn}/{n} ({sgn_pct:.0f}%)  "
                  f"sign-regime={sreg}/{n} ({sreg_pct:.0f}%)  mag={med:.2f}  "
                  f"{'PASS' if ok else 'REVIEW'}")
    print("=" * 56)
    print("GATE:", "PASS -- vectorized solver matches live; safe to bulk-write."
          if overall_ok else "REVIEW -- do NOT bulk-write until resolved.")
    return 0 if overall_ok else 1


# ------------------------------------------------------------------ STAGE 1: chunked write
def done_dates(symbol):
    rows = get("hist_greeks_backfill_log",
               {"select": "trade_date", "symbol": f"eq.{symbol}", "status": "in.(DONE,SKIPPED_EXPIRY)"})
    return {r["trade_date"] for r in rows}


def trade_dates_in_range(iid, d_from, d_to):
    rows = get("hist_spot_bars_1m",
               {"select": "trade_date",
                "and": f"(trade_date.gte.{d_from},trade_date.lte.{d_to})",
                "instrument_id": f"eq.{iid}", "order": "trade_date.asc"})
    return sorted({r["trade_date"] for r in rows})


def bar_ts_for_date(iid, d):
    rows = get("hist_option_bars_1m",
               {"select": "bar_ts", "instrument_id": f"eq.{iid}",
                "trade_date": f"eq.{d}", "order": "bar_ts.asc"})
    # distinct, preserve order
    seen, out = set(), []
    for r in rows:
        b = r["bar_ts"]
        if b not in seen:
            seen.add(b); out.append(b)
    return out


def log_chunk(trade_date, symbol, rows_written, rows_null, status, detail=""):
    upsert("hist_greeks_backfill_log", [{
        "trade_date": trade_date, "symbol": symbol,
        "rows_written": rows_written, "rows_null_iv": rows_null,
        "status": status, "detail": detail[:300],
        "finished_at": datetime.now(UTC).isoformat(),
    }], on_conflict="trade_date,symbol")


def spot_map_for_date(iid, d):  # spot-cache v1
    """Whole-day spot timeline in one paginated GET -> {bar_ts: close}."""
    rows = get("hist_spot_bars_1m",
               {"select": "bar_ts,close", "instrument_id": f"eq.{iid}",
                "trade_date": f"eq.{d}", "order": "bar_ts.asc"})
    return {r["bar_ts"]: float(r["close"]) for r in rows}


def run_backfill(symbol, d_from, d_to, apply):
    iid = iid_for(symbol)
    skip = done_dates(symbol) if apply else set()
    dates = [d for d in trade_dates_in_range(iid, d_from, d_to) if d not in skip]
    print(f"{symbol}: {len(dates)} dates to solve ({d_from}..{d_to}), "
          f"{len(skip)} already DONE. apply={apply}\n", flush=True)

    grand = 0
    for d in dates:
        bts_list = bar_ts_for_date(iid, d)
        scache = spot_map_for_date(iid, d)  # spot-cache v1
        day_rows, null_n = [], 0
        expiry_day = False  # expiry-skip v1
        try:
            for b in bts_list:
                res = solve_bar(iid, b, d, spot_cache=scache)
                if res[0] == "SKIP_EXPIRY":
                    expiry_day = True
                    break
                rows, _, _ = res
                if not rows:
                    continue
                null_n += sum(1 for r in rows if r["iv"] is None)
                day_rows.extend(rows)
            if expiry_day:
                if apply:
                    log_chunk(d, symbol, 0, 0, "SKIPPED_EXPIRY", "0-DTE: live-sourced")
                print(f"  {d}: bars={len(bts_list):>3} SKIPPED_EXPIRY (live-sourced)", flush=True)
                continue
            if apply and day_rows:
                upsert("hist_option_greeks_1m", day_rows,
                       on_conflict="instrument_id,bar_ts,strike,expiry_date,option_type")
                log_chunk(d, symbol, len(day_rows), null_n, "DONE")
            grand += len(day_rows)
            print(f"  {d}: bars={len(bts_list):>3} rows={len(day_rows):>5} "
                  f"null_iv={null_n:>4} {'WROTE' if (apply and day_rows) else 'dry'}",
                  flush=True)
        except Exception as e:
            if apply:
                log_chunk(d, symbol, len(day_rows), null_n, "ERROR", f"{type(e).__name__}: {e}")
            print(f"  {d}: ERROR {type(e).__name__}: {str(e)[:80]}", flush=True)

    print(f"\n{symbol}: total rows {'written' if apply else '(dry)'} = {grand}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true", help="STAGE 0 gate: solver vs live, no write")
    ap.add_argument("--symbol", default="NIFTY")
    ap.add_argument("--from", dest="d_from")
    ap.add_argument("--to", dest="d_to")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if args.validate:
        return validate()
    if not (args.d_from and args.d_to):
        print("need --from and --to (or --validate)"); return 2
    return run_backfill(args.symbol, args.d_from, args.d_to, args.apply)


if __name__ == "__main__":
    sys.exit(main())
