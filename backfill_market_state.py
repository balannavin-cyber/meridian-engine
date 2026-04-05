"""
backfill_market_state.py

Assembles historical market state snapshots from:
- hist_gamma_metrics      -> gamma_features
- hist_volatility_snapshots -> volatility_features
- equity_eod              -> breadth_features (EOD daily, where available)
- hist_spot_bars_1m       -> momentum_features (computed from price returns)

Writes to hist_market_state (separate from live market_state_snapshots).

Usage:
    python backfill_market_state.py 2025-10-15
    python backfill_market_state.py 2025-10-15 NIFTY
"""
from __future__ import annotations
import os, sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
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

def to_float(v):
    try: return float(v) if v is not None else None
    except: return None

# ── Feature builders (mirror live build_market_state_snapshot_local.py) ───────

def build_gamma_features(row: Dict) -> Dict:
    flip_dist_pts = to_float(row.get("flip_distance"))
    flip_dist_pct = to_float(row.get("flip_distance_pct"))
    return {
        "gamma_regime": row.get("regime"),
        "net_gex": row.get("net_gex"),
        "gamma_concentration": row.get("gamma_concentration"),
        "flip_level": row.get("flip_level"),
        "flip_distance": flip_dist_pts,
        "flip_distance_points": flip_dist_pts,
        "flip_distance_pct": flip_dist_pct,
        "flip_distance_canonical": flip_dist_pct,
        "flip_distance_canonical_unit": "pct",
        "straddle_slope": row.get("straddle_slope"),
        "source_table": "hist_gamma_metrics",
        "raw_ref_ts": row.get("bar_ts"),
    }

def build_volatility_features(row: Optional[Dict]) -> Dict:
    if not row:
        return {"source_table": None}
    return {
        "india_vix": row.get("india_vix_proxy"),
        "vix_regime": row.get("vix_regime"),
        "atm_strike": row.get("atm_strike"),
        "atm_call_iv": row.get("atm_call_iv"),
        "atm_put_iv": row.get("atm_put_iv"),
        "atm_iv_avg": row.get("atm_iv_avg"),
        "iv_skew": row.get("iv_skew"),
        "vix_percentile": row.get("vix_percentile"),
        "vix_percentile_regime": row.get("vix_percentile_regime"),
        "source_table": "hist_volatility_snapshots",
        "raw_ref_ts": row.get("bar_ts"),
    }

def build_breadth_features(row: Optional[Dict]) -> Dict:
    if not row:
        return {"breadth_regime": None, "breadth_score": None, "source_table": None}
    advances = to_float(row.get("advances"))
    declines = to_float(row.get("declines"))
    total = (advances or 0) + (declines or 0)
    # Compute breadth score and regime from advances/declines
    breadth_score = None
    breadth_regime = None
    if total > 0:
        adv_pct = (advances / total) * 100
        breadth_score = round(adv_pct, 2)
        if adv_pct >= 60: breadth_regime = "BULLISH"
        elif adv_pct <= 40: breadth_regime = "BEARISH"
        else: breadth_regime = "NEUTRAL"
    return {
        "breadth_regime": breadth_regime,
        "breadth_score": breadth_score,
        "advances": advances,
        "declines": declines,
        "source_table": "equity_eod",
        "raw_ref_ts": row.get("trade_date"),
    }

def build_momentum_features(spot_map: Dict[str, float], bar_ts: str,
                             open_spot: Optional[float]) -> Dict:
    spot = spot_map.get(bar_ts)
    if not spot:
        return {"momentum_regime": None, "source_table": None}

    bar_dt = datetime.fromisoformat(bar_ts.replace("Z", "+00:00"))

    def spot_n_min_ago(n: int) -> Optional[float]:
        target = (bar_dt - timedelta(minutes=n)).isoformat()
        # Find closest timestamp at or before target
        best = None
        best_ts = None
        for ts, s in spot_map.items():
            ts_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            ts_str = ts_dt.isoformat()
            if ts_str <= target:
                if best_ts is None or ts_str > best_ts:
                    best = s
                    best_ts = ts_str
        return best

    spot_30m = spot_n_min_ago(30)
    spot_60m = spot_n_min_ago(60)

    ret_session = ((spot - open_spot) / open_spot * 100) if open_spot else None
    ret_30m = ((spot - spot_30m) / spot_30m * 100) if spot_30m else None
    ret_60m = ((spot - spot_60m) / spot_60m * 100) if spot_60m else None

    # Momentum regime from ret_session
    regime = None
    if ret_session is not None:
        if ret_session > 0.3: regime = "BULLISH"
        elif ret_session < -0.3: regime = "BEARISH"
        else: regime = "NEUTRAL"

    return {
        "momentum_regime": regime,
        "ret_session": round(ret_session, 4) if ret_session is not None else None,
        "ret_30m": round(ret_30m, 4) if ret_30m is not None else None,
        "ret_60m": round(ret_60m, 4) if ret_60m is not None else None,
        "source_table": "hist_spot_bars_1m",
    }

# ── Data fetching ─────────────────────────────────────────────────────────────

def get_instrument_id(symbol):
    rows = sb_get("instruments", f"symbol=eq.{symbol}&select=id")
    if not rows: raise RuntimeError(f"Instrument not found: {symbol}")
    return rows[0]["id"]

def get_gamma_rows(symbol, trade_date) -> List[Dict]:
    return sb_get("hist_gamma_metrics",
                  f"symbol=eq.{symbol}&trade_date=eq.{trade_date}&select=*&limit=1000&order=bar_ts")

def get_vol_map(symbol, trade_date) -> Dict[str, Dict]:
    rows = sb_get("hist_volatility_snapshots",
                  f"symbol=eq.{symbol}&trade_date=eq.{trade_date}&select=*&limit=1000")
    return {r["bar_ts"]: r for r in rows}

def get_spot_map(instrument_id, trade_date) -> Dict[str, float]:
    rows = sb_get("hist_spot_bars_1m",
                  f"instrument_id=eq.{instrument_id}&trade_date=eq.{trade_date}"
                  f"&select=bar_ts,close&limit=1000&order=bar_ts")
    return {r["bar_ts"]: float(r["close"]) for r in rows if r.get("close")}

def get_breadth_row(trade_date) -> Optional[Dict]:
    # Use equity_eod close vs open as breadth proxy (prev_close not available)
    rows = sb_get("equity_eod",
                  f"trade_date=eq.{trade_date}&select=close,open&limit=2000")
    if not rows: return None
    advances = sum(1 for r in rows if to_float(r.get("close")) and to_float(r.get("open"))
                   and to_float(r["close"]) > to_float(r["open"]))
    declines = sum(1 for r in rows if to_float(r.get("close")) and to_float(r.get("open"))
                   and to_float(r["close"]) < to_float(r["open"]))
    return {"advances": advances, "declines": declines, "trade_date": trade_date}

def already_done(symbol, trade_date) -> bool:
    rows = sb_get("hist_market_state",
                  f"symbol=eq.{symbol}&trade_date=eq.{trade_date}&select=id&limit=1")
    return len(rows) > 0

# ── Main ──────────────────────────────────────────────────────────────────────

def run(trade_date, symbol):
    print(f"{'='*72}\nBACKFILL MARKET STATE — {symbol} — {trade_date}\n{'='*72}")

    if already_done(symbol, trade_date):
        print("Already done. Skipping."); return 0

    iid = get_instrument_id(symbol)

    print("Fetching gamma rows...")
    gamma_rows = get_gamma_rows(symbol, trade_date)
    print(f"Gamma rows: {len(gamma_rows)}")
    if not gamma_rows: print("No gamma data."); return 1

    print("Fetching volatility map...")
    vol_map = get_vol_map(symbol, trade_date)
    print(f"Volatility timestamps: {len(vol_map)}")

    print("Fetching spot map...")
    spot_map = get_spot_map(iid, trade_date)
    print(f"Spot timestamps: {len(spot_map)}")

    print("Fetching breadth...")
    breadth_row = get_breadth_row(trade_date)
    breadth_feat = build_breadth_features(breadth_row)
    if breadth_row:
        print(f"Breadth: advances={breadth_row['advances']} declines={breadth_row['declines']}")
    else:
        print("No breadth data for this date")

    # Get session open spot for ret_session
    open_spot = None
    if spot_map:
        earliest_ts = min(spot_map.keys())
        open_spot = spot_map[earliest_ts]

    out = []; skipped = 0
    for gamma_row in gamma_rows:
        bar_ts = gamma_row.get("bar_ts")
        if not bar_ts: skipped += 1; continue

        vol_row = vol_map.get(bar_ts)
        gamma_feat = build_gamma_features(gamma_row)
        vol_feat = build_volatility_features(vol_row)
        mom_feat = build_momentum_features(spot_map, bar_ts, open_spot)

        spot = to_float(gamma_row.get("spot"))

        out.append({
            "symbol": symbol,
            "bar_ts": bar_ts,
            "trade_date": trade_date,
            "spot": spot,
            "gamma_regime": gamma_feat.get("gamma_regime"),
            "gamma_zone": gamma_row.get("gamma_zone"),
            "net_gex": gamma_feat.get("net_gex"),
            "flip_level": gamma_feat.get("flip_level"),
            "flip_distance_pct": gamma_feat.get("flip_distance_pct"),
            "breadth_regime": breadth_feat.get("breadth_regime"),
            "breadth_score": breadth_feat.get("breadth_score"),
            "iv_regime": vol_feat.get("vix_regime"),
            "atm_iv": vol_feat.get("atm_iv_avg"),
            "iv_skew": vol_feat.get("iv_skew"),
            "momentum_regime": mom_feat.get("momentum_regime"),
            "ret_5m": None,
            "ret_15m": None,
            "ret_30m": mom_feat.get("ret_30m"),
            "ret_session": mom_feat.get("ret_session"),
        })

    print(f"Assembled: {len(out)} rows | Skipped: {skipped}")
    if not out: print("No rows."); return 1

    inserted = sb_upsert("hist_market_state", out)
    print(f"Upserted: {inserted} rows\nBACKFILL MARKET STATE COMPLETE")
    return 0

def main():
    if len(sys.argv) < 2:
        print("Usage: python backfill_market_state.py YYYY-MM-DD [NIFTY|SENSEX]"); return 1
    trade_date = sys.argv[1]
    symbols = ["NIFTY", "SENSEX"] if len(sys.argv) < 3 else [sys.argv[2].upper()]
    return max(run(trade_date, s) for s in symbols)

if __name__ == "__main__":
    raise SystemExit(main())
