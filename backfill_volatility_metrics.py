"""
backfill_volatility_metrics.py

Computes volatility snapshots for historical dates using:
- hist_option_bars_1m (ATM IV via Black-Scholes)
- hist_spot_bars_1m (spot price)
- india_vix_history (actual VIX for percentile computation)

Writes to hist_volatility_snapshots (separate from live volatility_snapshots).

Usage:
    python backfill_volatility_metrics.py 2025-10-15
    python backfill_volatility_metrics.py 2025-10-15 NIFTY
"""
from __future__ import annotations
import math, os, sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
RISK_FREE_RATE = 0.065
IST = timezone(timedelta(hours=5, minutes=30))

# ── Supabase helpers ──────────────────────────────────────────────────────────

def sb_headers():
    return {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"}

def sb_get(path, params=""):
    url = f"{SUPABASE_URL}/rest/v1/{path}{'?' + params if params else ''}"
    r = requests.get(url, headers=sb_headers(), timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"GET {path} failed {r.status_code}: {r.text[:200]}")
    return r.json()

def sb_upsert(table, rows):
    if not rows: return 0
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    h = {**sb_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"}
    inserted = 0
    for i in range(0, len(rows), 500):
        batch = rows[i:i+500]
        r = requests.post(url, headers=h, json=batch, timeout=60)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"UPSERT {table} failed {r.status_code}: {r.text[:200]}")
        inserted += len(batch)
    return inserted

# ── Black-Scholes ─────────────────────────────────────────────────────────────

def norm_cdf(x): return 0.5 * math.erfc(-x / math.sqrt(2))
def norm_pdf(x): return math.exp(-0.5*x*x) / math.sqrt(2*math.pi)

def bs_price(S, K, T, r, sigma, opt):
    if T <= 1e-6 or sigma <= 1e-6:
        return max(S-K,0) if opt=="CE" else max(K-S,0)
    d1 = (math.log(S/K)+(r+0.5*sigma**2)*T)/(sigma*math.sqrt(T))
    d2 = d1 - sigma*math.sqrt(T)
    if opt=="CE": return S*norm_cdf(d1)-K*math.exp(-r*T)*norm_cdf(d2)
    return K*math.exp(-r*T)*norm_cdf(-d2)-S*norm_cdf(-d1)

def implied_vol(S, K, T, r, price, opt):
    if T<=1e-6: return None
    intrinsic = max(S-K,0) if opt=="CE" else max(K-S,0)
    if price <= intrinsic+0.01: return None
    lo, hi = 0.001, 10.0
    for _ in range(100):
        mid = (lo+hi)/2
        p = bs_price(S,K,T,r,mid,opt)
        if abs(p-price)<0.001: return mid
        if p<price: lo=mid
        else: hi=mid
    return (lo+hi)/2

# ── Classification (mirrors live script) ─────────────────────────────────────

def get_strike_step(symbol):
    return 50 if symbol == "NIFTY" else 100

def find_atm_strike(spot, symbol):
    step = get_strike_step(symbol)
    return int(round(float(spot)/step)*step)

def classify_vix_regime(vix):
    if vix is None: return None
    if vix < 12: return "LOW"
    if vix < 18: return "NORMAL"
    if vix < 25: return "HIGH"
    return "PANIC"

def classify_vix_level_bucket(vix):
    if vix is None: return None
    buckets = [11,12,13,14,15,16,17,18,19,20]
    labels = ["UNDER_11","11_12","12_13","13_14","14_15","15_16","16_17","17_18","18_19","19_20"]
    for threshold, label in zip(buckets, labels):
        if vix < threshold: return label
    return "20_PLUS"

def classify_percentile_regime(pct):
    if pct is None: return None
    if pct < 20: return "VERY_LOW"
    if pct < 40: return "LOW"
    if pct < 60: return "NORMAL"
    if pct < 80: return "HIGH"
    return "EXTREME"

def classify_context_regime(pct):
    if pct is None: return None
    if pct >= 80: return "HIGH_CONTEXT"
    if pct <= 20: return "LOW_CONTEXT"
    return "NORMAL_CONTEXT"

def percentile_of(values, current):
    if not values: return None
    return (sum(1 for x in values if x <= current) / len(values)) * 100.0

def classify_interday_velocity(change_3d):
    if change_3d is None: return None
    if change_3d >= 1.5: return "VIX_UPTREND"
    if change_3d > 0: return "VIX_UP_BIAS"
    if change_3d <= -1.5: return "VIX_DOWNTREND"
    if change_3d < 0: return "VIX_DOWN_BIAS"
    return "VIX_FLAT"

# ── VIX history helpers ───────────────────────────────────────────────────────

def load_vix_history() -> Dict[str, float]:
    """Returns {trade_date_str: vix_value}"""
    rows = sb_get("india_vix_history", "select=trade_date,vix_value&limit=5000&order=trade_date")
    return {r["trade_date"]: float(r["vix_value"]) for r in rows if r.get("vix_value")}

def get_vix_for_date(vix_history: Dict[str, float], trade_date: str) -> Optional[float]:
    """Get VIX for a specific date or nearest prior date."""
    if trade_date in vix_history:
        return vix_history[trade_date]
    # Find nearest prior date
    prior = [v for d, v in vix_history.items() if d <= trade_date]
    return prior[-1] if prior else None

def compute_vix_percentile(vix_history: Dict[str, float], trade_date: str, vix_value: float) -> Optional[float]:
    sorted_dates = sorted(vix_history.keys())
    eligible = [vix_history[d] for d in sorted_dates if d <= trade_date]
    if not eligible: return None
    last_252 = eligible[-252:]
    return percentile_of(last_252, vix_value)

def get_prior_vix(vix_history: Dict[str, float], trade_date: str, days_back: int) -> Optional[float]:
    target = (date.fromisoformat(trade_date) - timedelta(days=days_back)).isoformat()
    prior = [(d, v) for d, v in vix_history.items() if d <= target]
    if not prior: return None
    return sorted(prior)[-1][1]

# ── Data fetching ─────────────────────────────────────────────────────────────

def get_instrument_id(symbol):
    rows = sb_get("instruments", f"symbol=eq.{symbol}&select=id")
    if not rows: raise RuntimeError(f"Instrument not found: {symbol}")
    return rows[0]["id"]

def get_spot_map(instrument_id, trade_date):
    rows = sb_get("hist_spot_bars_1m",
                  f"instrument_id=eq.{instrument_id}&trade_date=eq.{trade_date}&select=bar_ts,close&limit=1000")
    return {r["bar_ts"]: float(r["close"]) for r in rows if r.get("close")}

def get_option_bars(instrument_id, trade_date):
    all_rows = []; offset = 0
    while True:
        rows = sb_get("hist_option_bars_1m",
                      f"instrument_id=eq.{instrument_id}&trade_date=eq.{trade_date}"
                      f"&select=bar_ts,strike,option_type,close,expiry_date&limit=1000&offset={offset}")
        all_rows.extend(rows)
        if len(rows) < 1000: break
        offset += 1000
    return all_rows

def already_done(symbol, trade_date):
    rows = sb_get("hist_volatility_snapshots",
                  f"symbol=eq.{symbol}&trade_date=eq.{trade_date}&select=id&limit=1")
    return len(rows) > 0

def get_expiry_type(expiry_date: date, symbol: str) -> str:
    if symbol == "NIFTY":
        return "WEEKLY" if expiry_date.weekday() == 1 else "MONTHLY"
    if symbol == "SENSEX":
        return "WEEKLY" if expiry_date.weekday() == 3 else "MONTHLY"
    return "UNKNOWN"

# ── Core computation ──────────────────────────────────────────────────────────

def process_timestamp(ts, spot, option_rows, expiry_date_str, symbol,
                      instrument_id, trade_date, vix_value, atm_strike):
    """Compute volatility metrics for one timestamp."""
    bar_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    exp_dt = datetime.strptime(expiry_date_str, "%Y-%m-%d").replace(
        hour=15, minute=30, tzinfo=timezone.utc)
    T = max((exp_dt - bar_dt).total_seconds() / (365.25 * 24 * 3600), 1e-6)

    # Find ATM CE and PE rows for this timestamp
    atm_ce = atm_pe = None
    for row in option_rows:
        if int(float(row.get("strike", 0))) != atm_strike:
            continue
        opt = str(row.get("option_type", "")).upper()
        price = float(row.get("close") or 0)
        if price <= 0:
            continue
        if opt == "CE" and atm_ce is None:
            atm_ce = row
        elif opt == "PE" and atm_pe is None:
            atm_pe = row

    if not atm_ce or not atm_pe:
        return None

    ce_price = float(atm_ce.get("close", 0))
    pe_price = float(atm_pe.get("close", 0))

    ce_iv = implied_vol(spot, atm_strike, T, RISK_FREE_RATE, ce_price, "CE")
    pe_iv = implied_vol(spot, atm_strike, T, RISK_FREE_RATE, pe_price, "PE")

    if ce_iv is None or pe_iv is None:
        return None

    # Convert to percentage (multiply by 100 to match live system)
    ce_iv_pct = ce_iv * 100
    pe_iv_pct = pe_iv * 100
    atm_iv_avg = (ce_iv_pct + pe_iv_pct) / 2
    iv_skew = pe_iv_pct - ce_iv_pct
    atm_iv_vs_vix = (atm_iv_avg - vix_value) if vix_value else None

    expiry_date = date.fromisoformat(expiry_date_str)
    dte = (expiry_date - date.fromisoformat(trade_date)).days
    expiry_type = get_expiry_type(expiry_date, symbol)

    return {
        "instrument_id": instrument_id,
        "symbol": symbol,
        "bar_ts": ts,
        "trade_date": trade_date,
        "spot": spot,
        "atm_strike": atm_strike,
        "atm_call_iv": round(ce_iv_pct, 4),
        "atm_put_iv": round(pe_iv_pct, 4),
        "atm_iv_avg": round(atm_iv_avg, 4),
        "iv_skew": round(iv_skew, 4),
        "iv_regime": None,  # filled in by caller with VIX context
        "india_vix_proxy": round(vix_value, 4) if vix_value else None,
        "atm_iv_vs_vix_spread": round(atm_iv_vs_vix, 4) if atm_iv_vs_vix else None,
        "expiry_date": expiry_date_str,
        "expiry_type": expiry_type,
        "dte": dte,
    }

# ── Main ──────────────────────────────────────────────────────────────────────

def run(trade_date, symbol):
    print(f"{'='*72}\nBACKFILL VOLATILITY METRICS — {symbol} — {trade_date}\n{'='*72}")

    if already_done(symbol, trade_date):
        print("Already done. Skipping."); return 0

    # Load VIX history once
    print("Loading VIX history...")
    vix_history = load_vix_history()
    vix_value = get_vix_for_date(vix_history, trade_date)
    print(f"VIX for {trade_date}: {vix_value}")

    vix_percentile = compute_vix_percentile(vix_history, trade_date, vix_value) if vix_value else None
    vix_regime = classify_vix_regime(vix_value)
    vix_bucket = classify_vix_level_bucket(vix_value)
    vix_pct_regime = classify_percentile_regime(vix_percentile)
    vix_ctx_regime = classify_context_regime(vix_percentile)

    # VIX interday changes
    prev_1d = get_prior_vix(vix_history, trade_date, 1)
    prev_3d = get_prior_vix(vix_history, trade_date, 3)
    prev_5d = get_prior_vix(vix_history, trade_date, 5)
    vix_change_1d = (vix_value - prev_1d) if (vix_value and prev_1d) else None
    vix_change_3d = (vix_value - prev_3d) if (vix_value and prev_3d) else None
    vix_change_5d = (vix_value - prev_5d) if (vix_value and prev_5d) else None
    vix_interday = classify_interday_velocity(vix_change_3d)

    iid = get_instrument_id(symbol)
    spot_map = get_spot_map(iid, trade_date)
    print(f"Spot timestamps: {len(spot_map)}")
    if not spot_map: print("No spot data."); return 1

    bars = get_option_bars(iid, trade_date)
    print(f"Option rows: {len(bars)}")
    if not bars: print("No option data."); return 1

    # Use nearest expiry
    expiries = sorted(set(r["expiry_date"] for r in bars if r.get("expiry_date")))
    upcoming = [e for e in expiries if date.fromisoformat(e) >= date.fromisoformat(trade_date)]
    if not upcoming: print("No upcoming expiry."); return 1
    expiry = upcoming[0]
    print(f"Using expiry: {expiry}")

    near = [r for r in bars if r.get("expiry_date") == expiry]

    # Group by timestamp
    ts_groups = {}
    for r in near:
        ts_groups.setdefault(r["bar_ts"], []).append(r)
    print(f"Timestamps: {len(ts_groups)}")

    out = []; skipped = 0
    for ts, rows in sorted(ts_groups.items()):
        spot = spot_map.get(ts)
        if not spot: skipped += 1; continue

        atm_strike = find_atm_strike(spot, symbol)
        res = process_timestamp(ts, spot, rows, expiry, symbol, iid, trade_date, vix_value, atm_strike)
        if res:
            # Add VIX context fields
            res.update({
                "vix_regime": vix_regime,
                "vix_level_bucket": vix_bucket,
                "vix_percentile": round(vix_percentile, 2) if vix_percentile else None,
                "vix_percentile_regime": vix_pct_regime,
                "vix_context_regime": vix_ctx_regime,
                "vix_change_1d": round(vix_change_1d, 4) if vix_change_1d else None,
                "vix_change_3d": round(vix_change_3d, 4) if vix_change_3d else None,
                "vix_change_5d": round(vix_change_5d, 4) if vix_change_5d else None,
                "vix_interday_velocity": vix_interday,
            })
            out.append(res)
        else:
            skipped += 1

    print(f"Computed: {len(out)} | Skipped: {skipped}")
    if not out: print("No rows."); return 1

    inserted = sb_upsert("hist_volatility_snapshots", out)
    print(f"Upserted: {inserted} rows\nBACKFILL VOLATILITY METRICS COMPLETE")
    return 0

def main():
    if len(sys.argv) < 2:
        print("Usage: python backfill_volatility_metrics.py YYYY-MM-DD [NIFTY|SENSEX]"); return 1
    trade_date = sys.argv[1]
    symbols = ["NIFTY", "SENSEX"] if len(sys.argv) < 3 else [sys.argv[2].upper()]
    return max(run(trade_date, s) for s in symbols)

if __name__ == "__main__":
    raise SystemExit(main())
