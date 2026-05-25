#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
canonical_ict_recall.py
=======================
Clean-room canonical ICT detector + 30-min move recall experiment.

Branched off MERDIAN production work at Session 31 (2026-05-19).

PURPOSE
-------
Measure how often canonical ICT pattern detection would have flagged tradeable
30-min moves (NIFTY >= 50pt, SENSEX >= 150pt) over the available history,
using ONLY primary 1m spot data and a from-scratch reference implementation.

INDEPENDENCE
------------
This script imports nothing from MERDIAN production code. No reuse of
detect_ict_patterns.py, build_ict_htf_zones.py, experiment_15_*.py, or any
helper that touches those. Bar fetch goes directly to hist_spot_bars_1m;
all detection / aggregation / alignment / recall logic is self-contained here.

PRIMITIVES IMPLEMENTED (per ICT canon, Dec-2016 Monthly Mentorship slides)
-------------------------------------------------------------------------
  - Order Block (BULL / BEAR): canonical definition with validation gate.
    BULL_OB = lowest down-close candle, anchored at swing low, validated
              when a later candle trades through OB high.
  - Fair Value Gap (BULL / BEAR): canonical 3-bar imbalance.
  - Dealing range + equilibrium per TF (from confirmed swing fractals).
  - Premium / Discount classification per TF at any time.

HTF BIAS FRAMEWORK
------------------
At each timestamp t and each TF in (M, W, D, 1H):
  - last confirmed swing high + last confirmed swing low => dealing range
  - equilibrium = midpoint
  - premium = price >= eq; discount = price < eq
  - leg direction = direction of most recent completed swing
    (last swing HIGH => leg up just confirmed => bullish bias on retrace)
HTF bias stack at t = (M_state, W_state, D_state, H_state) x (leg + position).

ALIGNMENT FOR ENTRY
-------------------
BULL primitive aligned at HTF level X iff X_leg == BULLISH and X_state == DISCOUNT.
BEAR primitive aligned at HTF level X iff X_leg == BEARISH and X_state == PREMIUM.

DISCIPLINE TIERS
----------------
  T0  no HTF filter                       (primitive recall upper bound)
  T1  H aligned
  T2  D + H aligned
  T3  W + D + H aligned
  T4  M + W + D + H aligned              (full canon, strictest)

ENTRY MODES
-----------
  FORMATION : entry_ts = primitive validation ts                       (loose)
  RETURN    : entry_ts = first re-entry to zone after displacement     (strict canon)

Primary report uses RETURN mode. FORMATION emitted as upper-bound reference.

MOVE COHORT
-----------
For each in-session 1m timestamp ts (ts.time() <= 15:00 IST):
  net_30m = close(ts+30m) - close(ts)
  qualifying if |net_30m| >= threshold[symbol]
  direction = UP if net_30m > 0 else DOWN

JOIN
----
For each qualifying move, look for an entry in [move_ts - 15m, move_ts]
with matching direction (BULL=>UP, BEAR=>DOWN). Latest entry in window is
the match.

OUTPUTS
-------
output_canonical_ict/
  primitives_<symbol>_<run>.csv       every detected primitive (with lifecycle)
  entries_<symbol>_<run>.csv          every entry (modes A and B) with bias stack
  moves_<symbol>_<run>.csv            every qualifying 30-min move
  recall_detail_<symbol>_<run>.csv    per-move match flag
  recall_summary_<symbol>_<run>.csv   recall % per (direction, mode, tier)
  recall_combined_<run>.csv           cross-symbol combined summary
  Console: live progress + recall matrix table

USAGE
-----
  pip install supabase pandas numpy python-dotenv
  Set SUPABASE_URL and SUPABASE_KEY (or SUPABASE_SERVICE_KEY) in .env
  python canonical_ict_recall.py [--start YYYY-MM-DD] [--end YYYY-MM-DD]
                                 [--symbols NIFTY,SENSEX] [--swing-n 5]

CAVEATS (read these)
--------------------
* 14 months of history => ~14 monthly bars. With swing N=5 (textbook), the
  first usable monthly swing-center is bar 5; only a handful of M swings
  will exist. M_state / M_leg often UNKNOWN. T4 recall will be artificially
  depressed for this reason; T3 (W+D+H) is the more honest strict number.
* Era boundary 2026-04-07: pre = bars stored as IST clock labelled +00:00;
  post = true UTC. Handled via trade_date filter + era-aware converter.
* Production tables are READ-ONLY here. No writes anywhere except local CSV.
"""

from __future__ import annotations
import argparse
import os
import sys
import time as _time
from dataclasses import dataclass
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client


# ==========================================================================
# CONFIG
# ==========================================================================

IST = timezone(timedelta(hours=5, minutes=30))
ERA_BOUNDARY_DATE = "2026-04-07"

DEFAULT_SYMBOLS = ["NIFTY", "SENSEX"]
MOVE_THRESHOLDS = {"NIFTY": 50.0, "SENSEX": 150.0}
MOVE_HORIZON_MIN = 30
RECALL_LOOKBACK_MIN = 15

DEFAULT_SWING_N = 5
OB_NEAR_SUPPORT_PCT = 0.005       # 0.5%
OB_MIN_BODY_PCT = 0.0010          # 0.10% min body (filters dojis)

SESSION_OPEN = dtime(9, 15)
SESSION_CLOSE = dtime(15, 30)
MOVE_WINDOW_LATEST_START = dtime(15, 0)

OUT_DIR = Path("output_canonical_ict")
OUT_DIR.mkdir(exist_ok=True)


# ==========================================================================
# 1. SUPABASE + BAR FETCH (era-aware)
# ==========================================================================

def _connect_supabase():
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    # Check every variant the MERDIAN codebase + disaster-rebuild runbook reference
    key_candidates = [
        "SUPABASE_SERVICE_ROLE_KEY",   # AWS .env convention (per runbook)
        "SUPABASE_KEY",                # Local .env convention (per disaster-rebuild runbook)
        "SUPABASE_SERVICE_KEY",        # legacy variant
        "SUPABASE_ANON_KEY",           # last resort
    ]
    key = None
    key_var = None
    for v in key_candidates:
        val = os.environ.get(v)
        if val:
            key = val
            key_var = v
            break
    if not (url and key):
        present = [v for v in (["SUPABASE_URL"] + key_candidates) if os.environ.get(v)]
        missing = [v for v in (["SUPABASE_URL"] + key_candidates) if not os.environ.get(v)]
        sys.stderr.write(
            "ERROR: Supabase env vars missing.\n"
            f"  found    : {present}\n"
            f"  expected : SUPABASE_URL + one of {key_candidates}\n"
            "  CWD .env : " + str(Path('.env').absolute()) + " exists=" + str(Path('.env').exists()) + "\n"
            "  hint     : run from C:\\GammaEnginePython where .env lives, OR set the vars in the shell\n"
        )
        sys.exit(1)
    print(f"  supabase: using {key_var}")
    return create_client(url, key)


def _ist_from_bar(bar_ts_utc: pd.Timestamp, trade_date_iso: str) -> datetime:
    """Era-aware IST clock-time conversion (CLAUDE.md Rule 20 era logic)."""
    if trade_date_iso < ERA_BOUNDARY_DATE:
        # Pre-04-07: stored as IST clock-time labelled +00:00. Drop tz to get IST.
        return bar_ts_utc.tz_localize(None).to_pydatetime()
    # Post-04-07: true UTC. Convert to IST, then drop tz.
    return bar_ts_utc.tz_convert(IST).tz_localize(None).to_pydatetime()


def _resolve_instrument_ids(sb, symbols: list) -> dict:
    """
    Look up instrument_id per symbol from hist_spot_bars_5m (which has both columns).
    hist_spot_bars_1m only has instrument_id, no symbol column.
    """
    out = {}
    for sym in symbols:
        resp = (sb.table("hist_spot_bars_5m")
                  .select("instrument_id")
                  .eq("symbol", sym)
                  .limit(1)
                  .execute())
        if not resp.data:
            sys.exit(f"ERROR: no instrument_id found for symbol {sym} in hist_spot_bars_5m")
        out[sym] = resp.data[0]["instrument_id"]
    return out


def fetch_1m_bars(sb, symbol: str, instrument_id: str,
                  start_date: str, end_date: str) -> pd.DataFrame:
    """
    Page through hist_spot_bars_1m for [start_date, end_date] for given instrument_id.
    Honors Supabase 1000-row pagination cap.
    Returns DataFrame with: ist (naive IST datetime), trade_date, open/high/low/close.
    """
    rows = []
    page_size = 1000
    page = 0
    print(f"  [{symbol} / {instrument_id[:8]}] fetching 1m bars {start_date}..{end_date}", end="", flush=True)
    while True:
        resp = (sb.table("hist_spot_bars_1m")
                  .select("bar_ts, trade_date, open, high, low, close")
                  .eq("instrument_id", instrument_id)
                  .gte("trade_date", start_date)
                  .lte("trade_date", end_date)
                  .order("bar_ts")
                  .range(page * page_size, (page + 1) * page_size - 1)
                  .execute())
        batch = resp.data
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += 1
        if page % 25 == 0:
            print(".", end="", flush=True)
    print(f" {len(rows)} rows")
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["bar_ts"] = pd.to_datetime(df["bar_ts"], utc=True)
    df["ist"] = df.apply(lambda r: _ist_from_bar(r["bar_ts"], r["trade_date"]), axis=1)
    df = df.drop(columns=["bar_ts"]).sort_values("ist").reset_index(drop=True)
    clock = df["ist"].dt.time
    df = df[(clock >= SESSION_OPEN) & (clock <= SESSION_CLOSE)].copy().reset_index(drop=True)
    for c in ("open", "high", "low", "close"):
        df[c] = df[c].astype(float)
    return df


# ==========================================================================
# 2. TIMEFRAME AGGREGATION
# ==========================================================================

def aggregate_intraday(df_1m: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """Aggregate 1m bars to intraday TF (5m, 15m, 60m). Bucket by floor of IST minute."""
    if df_1m.empty:
        return df_1m
    df = df_1m.copy()
    df["bucket"] = df["ist"].dt.floor(f"{minutes}min")
    agg = df.groupby("bucket", as_index=False).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        trade_date=("trade_date", "first"),
    )
    return agg.sort_values("bucket").reset_index(drop=True)


def aggregate_daily(df_1m: pd.DataFrame) -> pd.DataFrame:
    if df_1m.empty:
        return df_1m
    agg = df_1m.groupby("trade_date", as_index=False).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
    )
    agg = agg.rename(columns={"trade_date": "bucket"})
    agg["bucket"] = pd.to_datetime(agg["bucket"])
    return agg.sort_values("bucket").reset_index(drop=True)


def aggregate_weekly(df_d: pd.DataFrame) -> pd.DataFrame:
    """Daily -> Weekly. Week start = Monday."""
    if df_d.empty:
        return df_d
    df = df_d.copy()
    df["week_start"] = df["bucket"] - pd.to_timedelta(df["bucket"].dt.dayofweek, unit="D")
    agg = df.groupby("week_start", as_index=False).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
    )
    return agg.rename(columns={"week_start": "bucket"}).sort_values("bucket").reset_index(drop=True)


def aggregate_monthly(df_d: pd.DataFrame) -> pd.DataFrame:
    if df_d.empty:
        return df_d
    df = df_d.copy()
    df["month_start"] = df["bucket"].dt.to_period("M").dt.to_timestamp()
    agg = df.groupby("month_start", as_index=False).agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
    )
    return agg.rename(columns={"month_start": "bucket"}).sort_values("bucket").reset_index(drop=True)


# ==========================================================================
# 3. SWING FRACTALS (per-TF)
# ==========================================================================

def find_swings(df_tf: pd.DataFrame, n: int) -> list[dict]:
    """
    Strict fractal swings on df_tf bars.
    Swing high at i: high[i] > max(high[i-n..i-1]) AND high[i] > max(high[i+1..i+n]).
    Swing low at i: symmetric on lows.
    Confirmed at bucket[i+n] (right window completes).
    """
    swings = []
    if len(df_tf) < 2 * n + 1:
        return swings
    highs = df_tf["high"].values
    lows = df_tf["low"].values
    buckets = df_tf["bucket"].values
    for i in range(n, len(df_tf) - n):
        ch = highs[i]
        left_max = highs[i-n:i].max()
        right_max = highs[i+1:i+n+1].max()
        if ch > left_max and ch > right_max:
            swings.append({
                "ts": buckets[i],
                "confirmed_at": buckets[i+n],
                "type": "HIGH",
                "price": float(ch),
            })
        cl = lows[i]
        left_min = lows[i-n:i].min()
        right_min = lows[i+1:i+n+1].min()
        if cl < left_min and cl < right_min:
            swings.append({
                "ts": buckets[i],
                "confirmed_at": buckets[i+n],
                "type": "LOW",
                "price": float(cl),
            })
    return swings


# ==========================================================================
# 4. DEALING RANGE + HTF BIAS STATE
# ==========================================================================

def dealing_range_at(t: pd.Timestamp, swings: list[dict]) -> Optional[dict]:
    """
    Most recent dealing range as of time t.
    Uses only swings confirmed strictly before t (no look-ahead).
    Returns None if both a HIGH and a LOW swing are not yet confirmed before t.
    """
    t = pd.Timestamp(t)
    confirmed = [s for s in swings if pd.Timestamp(s["confirmed_at"]) < t]
    if not confirmed:
        return None
    last_high = None
    last_low = None
    for s in reversed(confirmed):
        if last_high is None and s["type"] == "HIGH":
            last_high = s
        if last_low is None and s["type"] == "LOW":
            last_low = s
        if last_high and last_low:
            break
    if not (last_high and last_low):
        return None
    most_recent = max(last_high, last_low, key=lambda s: pd.Timestamp(s["ts"]))
    leg_dir = "BULLISH" if most_recent["type"] == "HIGH" else "BEARISH"
    return {
        "high": last_high["price"],
        "low": last_low["price"],
        "eq": (last_high["price"] + last_low["price"]) / 2.0,
        "leg_dir": leg_dir,
        "last_swing_type": most_recent["type"],
        "last_swing_ts": most_recent["ts"],
    }


def state_for_price(price: float, dr: Optional[dict]) -> str:
    if dr is None:
        return "UNKNOWN"
    return "PREMIUM" if price >= dr["eq"] else "DISCOUNT"


# ==========================================================================
# 5. PRIMITIVE DETECTION
# ==========================================================================

def _most_recent_swing_price(swings: list[dict], swing_type: str,
                              before_ts: pd.Timestamp) -> Optional[float]:
    """Most recent swing price of given type confirmed at-or-before before_ts."""
    before_ts = pd.Timestamp(before_ts)
    cand = [s for s in swings
            if s["type"] == swing_type
            and pd.Timestamp(s["confirmed_at"]) <= before_ts]
    return cand[-1]["price"] if cand else None


def detect_obs_on_tf(df_tf: pd.DataFrame, swings: list[dict],
                     near_pct: float = OB_NEAR_SUPPORT_PCT,
                     min_body_pct: float = OB_MIN_BODY_PCT) -> list[dict]:
    """
    Canonical ICT Order Block detection.

    BULL_OB at bar i:
      - close[i] < open[i]  (down close)
      - abs(close-open)/close >= min_body_pct
      - low[i] within near_pct of the most recent confirmed swing low at-or-before bucket[i]
        (anchored at the structural support)
      - some j > i with high[j] > high[i]  (validation: trade-through of OB high)
      - zone = [low[i], high[i]]

    BEAR_OB: symmetric.
    """
    out = []
    if len(df_tf) < 3:
        return out
    opens = df_tf["open"].values
    closes = df_tf["close"].values
    highs = df_tf["high"].values
    lows = df_tf["low"].values
    buckets = df_tf["bucket"].values

    for i in range(len(df_tf)):
        body = closes[i] - opens[i]
        ref = closes[i] if closes[i] > 0 else 1.0
        body_pct = abs(body) / ref
        if body_pct < min_body_pct:
            continue

        bts = buckets[i]

        # BULL_OB candidate
        if closes[i] < opens[i]:
            sl = _most_recent_swing_price(swings, "LOW", bts)
            if sl is not None and abs(lows[i] - sl) / max(lows[i], 1.0) <= near_pct:
                vj = None
                for j in range(i + 1, len(df_tf)):
                    if highs[j] > highs[i]:
                        vj = j
                        break
                if vj is not None:
                    out.append({
                        "ts_origin": buckets[i],
                        "ts_validated": buckets[vj],
                        "direction": "BULL",
                        "primitive_type": "BULL_OB",
                        "zone_low": float(lows[i]),
                        "zone_high": float(highs[i]),
                    })

        # BEAR_OB candidate
        if closes[i] > opens[i]:
            sh = _most_recent_swing_price(swings, "HIGH", bts)
            if sh is not None and abs(highs[i] - sh) / max(highs[i], 1.0) <= near_pct:
                vj = None
                for j in range(i + 1, len(df_tf)):
                    if lows[j] < lows[i]:
                        vj = j
                        break
                if vj is not None:
                    out.append({
                        "ts_origin": buckets[i],
                        "ts_validated": buckets[vj],
                        "direction": "BEAR",
                        "primitive_type": "BEAR_OB",
                        "zone_low": float(lows[i]),
                        "zone_high": float(highs[i]),
                    })
    return out


def detect_fvgs_on_tf(df_tf: pd.DataFrame) -> list[dict]:
    """
    Canonical 3-bar Fair Value Gap.

    BULL_FVG at center bar i: high[i-1] < low[i+1]
      zone = [high[i-1], low[i+1]]; formed at bar i+1.
    BEAR_FVG at center bar i: low[i-1] > high[i+1]
      zone = [high[i+1], low[i-1]]; formed at bar i+1.
    """
    out = []
    if len(df_tf) < 3:
        return out
    highs = df_tf["high"].values
    lows = df_tf["low"].values
    buckets = df_tf["bucket"].values
    for i in range(1, len(df_tf) - 1):
        ph, pl = highs[i-1], lows[i-1]
        nh, nl = highs[i+1], lows[i+1]
        if ph < nl:
            out.append({
                "ts_origin": buckets[i],
                "ts_validated": buckets[i+1],
                "direction": "BULL",
                "primitive_type": "BULL_FVG",
                "zone_low": float(ph),
                "zone_high": float(nl),
            })
        if pl > nh:
            out.append({
                "ts_origin": buckets[i],
                "ts_validated": buckets[i+1],
                "direction": "BEAR",
                "primitive_type": "BEAR_FVG",
                "zone_low": float(nh),
                "zone_high": float(pl),
            })
    return out


# ==========================================================================
# 6. ZONE LIFECYCLE + RETURN-TO-PRIMITIVE
# ==========================================================================

def compute_zone_lifecycle(primitive: dict, df_1m: pd.DataFrame) -> dict:
    """
    Walk 1m bars after ts_validated to determine:
      displacement_end_ts  : first bar that has moved at least one zone-height away
      first_return_ts      : first bar that touches the near edge of the zone again
      filled_ts            : first bar that closes through the far edge (zone consumed)

    BULL zone: displacement = high >= zone_high + height
               return       = low <= zone_high (touch zone top)
               filled       = close < zone_low
    BEAR zone: symmetric.
    """
    out = dict(primitive)
    out["displacement_end_ts"] = None
    out["first_return_ts"] = None
    out["filled_ts"] = None

    if df_1m.empty:
        return out

    zlo = primitive["zone_low"]
    zhi = primitive["zone_high"]
    height = zhi - zlo
    if height <= 0:
        return out

    after = df_1m[df_1m["ist"] > pd.Timestamp(primitive["ts_validated"])]
    if after.empty:
        return out

    if primitive["direction"] == "BULL":
        disp_target = zhi + height
        disp_hit = after[after["high"] >= disp_target]
        if disp_hit.empty:
            return out
        out["displacement_end_ts"] = disp_hit.iloc[0]["ist"]
        after_disp = after[after["ist"] > out["displacement_end_ts"]]
        ret_hit = after_disp[after_disp["low"] <= zhi]
        if not ret_hit.empty:
            out["first_return_ts"] = ret_hit.iloc[0]["ist"]
        fill_hit = after[after["close"] < zlo]
        if not fill_hit.empty:
            out["filled_ts"] = fill_hit.iloc[0]["ist"]
    else:
        disp_target = zlo - height
        disp_hit = after[after["low"] <= disp_target]
        if disp_hit.empty:
            return out
        out["displacement_end_ts"] = disp_hit.iloc[0]["ist"]
        after_disp = after[after["ist"] > out["displacement_end_ts"]]
        ret_hit = after_disp[after_disp["high"] >= zlo]
        if not ret_hit.empty:
            out["first_return_ts"] = ret_hit.iloc[0]["ist"]
        fill_hit = after[after["close"] > zhi]
        if not fill_hit.empty:
            out["filled_ts"] = fill_hit.iloc[0]["ist"]
    return out


# ==========================================================================
# 7. HTF BIAS STACK AT A POINT
# ==========================================================================

@dataclass
class TFContext:
    bars: pd.DataFrame
    swings: list[dict]


def htf_bias_at(t: pd.Timestamp, ctx_m: TFContext, ctx_w: TFContext,
                ctx_d: TFContext, ctx_h: TFContext, spot: float) -> dict:
    out = {}
    for name, ctx in (("M", ctx_m), ("W", ctx_w), ("D", ctx_d), ("H", ctx_h)):
        dr = dealing_range_at(t, ctx.swings)
        if dr is None:
            out[f"{name}_leg"] = "UNKNOWN"
            out[f"{name}_state"] = "UNKNOWN"
        else:
            out[f"{name}_leg"] = dr["leg_dir"]
            out[f"{name}_state"] = state_for_price(spot, dr)
    return out


def alignment_for(direction: str, bias: dict, level: str) -> bool:
    leg = bias.get(f"{level}_leg")
    state = bias.get(f"{level}_state")
    if leg == "UNKNOWN" or state == "UNKNOWN":
        return False
    if direction == "BULL":
        return leg == "BULLISH" and state == "DISCOUNT"
    if direction == "BEAR":
        return leg == "BEARISH" and state == "PREMIUM"
    return False


# ==========================================================================
# 8. ENTRIES (modes A + B with alignment tiers)
# ==========================================================================

def build_entries(primitives_lc: list[dict], ctx_m, ctx_w, ctx_d, ctx_h,
                  df_1m: pd.DataFrame) -> pd.DataFrame:
    rows = []
    spot_idx = df_1m.set_index("ist")["close"].sort_index()

    def spot_at(t):
        if t is None or pd.isna(t):
            return None
        loc = spot_idx.index.searchsorted(pd.Timestamp(t), side="right") - 1
        if loc < 0:
            return None
        return float(spot_idx.iloc[loc])

    for p in primitives_lc:
        for mode, ets_field in (("FORMATION", "ts_validated"),
                                ("RETURN", "first_return_ts")):
            ets = p.get(ets_field)
            if ets is None or pd.isna(ets):
                continue
            ets = pd.Timestamp(ets)
            spot = spot_at(ets)
            if spot is None:
                continue
            bias = htf_bias_at(ets, ctx_m, ctx_w, ctx_d, ctx_h, spot)
            r = {
                "entry_ts": ets,
                "mode": mode,
                "primitive_type": p["primitive_type"],
                "direction": p["direction"],
                "primitive_tf": p.get("tf"),
                "zone_low": p["zone_low"],
                "zone_high": p["zone_high"],
                "spot_at_entry": spot,
                "ts_origin": p["ts_origin"],
                "ts_validated": p["ts_validated"],
                "displacement_end_ts": p.get("displacement_end_ts"),
                "filled_ts": p.get("filled_ts"),
                **bias,
            }
            r["align_H"] = alignment_for(p["direction"], bias, "H")
            r["align_D"] = alignment_for(p["direction"], bias, "D")
            r["align_W"] = alignment_for(p["direction"], bias, "W")
            r["align_M"] = alignment_for(p["direction"], bias, "M")
            r["align_T0"] = True
            r["align_T1"] = r["align_H"]
            r["align_T2"] = r["align_T1"] and r["align_D"]
            r["align_T3"] = r["align_T2"] and r["align_W"]
            r["align_T4"] = r["align_T3"] and r["align_M"]
            rows.append(r)
    return pd.DataFrame(rows)


# ==========================================================================
# 9. MOVE COHORT
# ==========================================================================

def build_move_cohort(df_1m: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if df_1m.empty:
        return df_1m
    df = df_1m[["ist", "close", "high", "low"]].copy().sort_values("ist").reset_index(drop=True)
    df["ts_30m"] = df["ist"] + timedelta(minutes=MOVE_HORIZON_MIN)
    close_idx = df.set_index("ist")["close"].sort_index()
    idx_arr = close_idx.index.values
    cl_arr = close_idx.values
    def close_at_or_before(t):
        loc = np.searchsorted(idx_arr, np.datetime64(pd.Timestamp(t).to_datetime64()), side="right") - 1
        if loc < 0 or loc >= len(cl_arr):
            return np.nan
        return float(cl_arr[loc])
    df["close_30m"] = [close_at_or_before(t) for t in df["ts_30m"]]
    df["net_30m"] = df["close_30m"] - df["close"]
    thr = MOVE_THRESHOLDS[symbol]
    df["qualifying"] = df["net_30m"].abs() >= thr
    df["direction"] = np.where(df["net_30m"] > 0, "UP",
                       np.where(df["net_30m"] < 0, "DOWN", "FLAT"))
    df["symbol"] = symbol
    clock = df["ist"].dt.time
    df = df[clock <= MOVE_WINDOW_LATEST_START].copy().reset_index(drop=True)
    return df[df["qualifying"]].copy().reset_index(drop=True)


# ==========================================================================
# 10. RECALL
# ==========================================================================

def compute_recall_detail(entries: pd.DataFrame, moves: pd.DataFrame) -> pd.DataFrame:
    """For each move, did a matching entry fire in [move_ts - 15m, move_ts]?"""
    results = []
    if moves.empty:
        return pd.DataFrame(results)
    if entries.empty:
        # zero recall, still emit move rows
        for mode in ("FORMATION", "RETURN"):
            for tier in ("T0", "T1", "T2", "T3", "T4"):
                for _, mrow in moves.iterrows():
                    results.append({
                        "symbol": mrow["symbol"], "direction": mrow["direction"],
                        "mode": mode, "tier": tier, "move_ts": mrow["ist"],
                        "net_30m": mrow["net_30m"], "matched": False,
                        "matched_primitive": None, "matched_tf": None, "lead_min": None,
                    })
        return pd.DataFrame(results)

    entries = entries.copy()
    entries["entry_ts"] = pd.to_datetime(entries["entry_ts"])
    moves = moves.copy()
    moves["ist"] = pd.to_datetime(moves["ist"])

    for mode in ("FORMATION", "RETURN"):
        em = entries[entries["mode"] == mode]
        for tier in ("T0", "T1", "T2", "T3", "T4"):
            et = em[em[f"align_{tier}"]]
            for dir_letter, move_dir in (("BULL", "UP"), ("BEAR", "DOWN")):
                etd = et[et["direction"] == dir_letter].sort_values("entry_ts").reset_index(drop=True)
                arr = etd["entry_ts"].values.astype("datetime64[ns]") if not etd.empty else np.array([], dtype="datetime64[ns]")
                m_dir = moves[moves["direction"] == move_dir]
                for _, mrow in m_dir.iterrows():
                    mt = pd.Timestamp(mrow["ist"])
                    win_lo = mt - timedelta(minutes=RECALL_LOOKBACK_MIN)
                    if arr.size:
                        i_lo = np.searchsorted(arr, np.datetime64(win_lo.to_datetime64()), side="left")
                        i_hi = np.searchsorted(arr, np.datetime64(mt.to_datetime64()), side="right")
                        matched = i_hi > i_lo
                    else:
                        i_lo = i_hi = 0
                        matched = False
                    matched_primitive = None
                    matched_tf = None
                    lead_min = None
                    if matched:
                        mr = etd.iloc[i_hi - 1]
                        matched_primitive = mr["primitive_type"]
                        matched_tf = mr["primitive_tf"]
                        lead_min = (mt - pd.Timestamp(mr["entry_ts"])).total_seconds() / 60.0
                    results.append({
                        "symbol": mrow["symbol"], "direction": move_dir,
                        "mode": mode, "tier": tier, "move_ts": mt,
                        "net_30m": float(mrow["net_30m"]), "matched": bool(matched),
                        "matched_primitive": matched_primitive,
                        "matched_tf": matched_tf, "lead_min": lead_min,
                    })
    return pd.DataFrame(results)


def recall_summary(detail: pd.DataFrame) -> pd.DataFrame:
    if detail.empty:
        return detail
    grp = detail.groupby(["symbol", "direction", "mode", "tier"])
    s = grp.agg(n_moves=("matched", "size"),
                n_matched=("matched", "sum"),
                median_lead_min=("lead_min", "median")).reset_index()
    s["recall_pct"] = (s["n_matched"] / s["n_moves"] * 100.0).round(2)
    return s


# ==========================================================================
# 11. PER-SYMBOL ORCHESTRATION
# ==========================================================================

def run_for_symbol(sb, symbol: str, instrument_id: str,
                   start_date: str, end_date: str,
                   swing_n: int, run_tag: str) -> Optional[pd.DataFrame]:
    print(f"\n=== {symbol} : {start_date} -> {end_date} ===")
    t0 = _time.time()
    df_1m = fetch_1m_bars(sb, symbol, instrument_id, start_date, end_date)
    if df_1m.empty:
        print(f"  no data for {symbol}")
        return None

    df_5m = aggregate_intraday(df_1m, 5)
    df_15m = aggregate_intraday(df_1m, 15)
    df_1h = aggregate_intraday(df_1m, 60)
    df_d = aggregate_daily(df_1m)
    df_w = aggregate_weekly(df_d)
    df_mo = aggregate_monthly(df_d)
    print(f"  TF bars : 5m={len(df_5m)} 15m={len(df_15m)} 1h={len(df_1h)} D={len(df_d)} W={len(df_w)} M={len(df_mo)}")

    sw_5m = find_swings(df_5m, swing_n)
    sw_15m = find_swings(df_15m, swing_n)
    sw_h = find_swings(df_1h, swing_n)
    sw_d = find_swings(df_d, swing_n)
    sw_w = find_swings(df_w, swing_n)
    sw_m = find_swings(df_mo, swing_n)
    print(f"  swings  : 5m={len(sw_5m)} 15m={len(sw_15m)} 1h={len(sw_h)} D={len(sw_d)} W={len(sw_w)} M={len(sw_m)}")
    if len(sw_m) < 2:
        print("  NOTE: monthly swings sparse — T4 recall is dominated by UNKNOWN. T3 (W+D+H) is the cleaner strict number.")

    primitives = []
    for tf_name, df_tf, swings_tf in (("5m", df_5m, sw_5m),
                                       ("15m", df_15m, sw_15m),
                                       ("1h", df_1h, sw_h)):
        obs = detect_obs_on_tf(df_tf, swings_tf)
        fvgs = detect_fvgs_on_tf(df_tf)
        for x in obs + fvgs:
            x["tf"] = tf_name
        primitives.extend(obs + fvgs)
    bull_ob = sum(1 for p in primitives if p["primitive_type"] == "BULL_OB")
    bear_ob = sum(1 for p in primitives if p["primitive_type"] == "BEAR_OB")
    bull_fvg = sum(1 for p in primitives if p["primitive_type"] == "BULL_FVG")
    bear_fvg = sum(1 for p in primitives if p["primitive_type"] == "BEAR_FVG")
    print(f"  primitives : total={len(primitives)}  BULL_OB={bull_ob} BEAR_OB={bear_ob} BULL_FVG={bull_fvg} BEAR_FVG={bear_fvg}")

    print(f"  computing zone lifecycles ...", end="", flush=True)
    t1 = _time.time()
    primitives_lc = [compute_zone_lifecycle(p, df_1m) for p in primitives]
    print(f" {_time.time()-t1:.1f}s")
    n_with_return = sum(1 for p in primitives_lc if p.get("first_return_ts") is not None)
    n_with_disp = sum(1 for p in primitives_lc if p.get("displacement_end_ts") is not None)
    print(f"  lifecycle  : displacement={n_with_disp} return_to_zone={n_with_return}")

    ctx_m = TFContext(df_mo, sw_m)
    ctx_w = TFContext(df_w, sw_w)
    ctx_d = TFContext(df_d, sw_d)
    ctx_h = TFContext(df_1h, sw_h)

    print(f"  building entries with HTF bias stack ...", end="", flush=True)
    t1 = _time.time()
    entries = build_entries(primitives_lc, ctx_m, ctx_w, ctx_d, ctx_h, df_1m)
    print(f" {_time.time()-t1:.1f}s  rows={len(entries)}")
    if not entries.empty:
        for tier in ("T1", "T2", "T3", "T4"):
            n_ret = int(((entries["mode"] == "RETURN") & (entries[f"align_{tier}"])).sum())
            print(f"    aligned {tier} (RETURN mode) : {n_ret}")

    moves = build_move_cohort(df_1m, symbol)
    n_up = int((moves["direction"] == "UP").sum())
    n_dn = int((moves["direction"] == "DOWN").sum())
    print(f"  qualifying moves : {len(moves)}  (UP={n_up} DOWN={n_dn}, threshold={MOVE_THRESHOLDS[symbol]}pts / {MOVE_HORIZON_MIN}min)")

    detail = compute_recall_detail(entries, moves)
    summary = recall_summary(detail)

    # Save
    primitives_df = pd.DataFrame(primitives_lc)
    if not primitives_df.empty:
        primitives_df["symbol"] = symbol
        primitives_df.to_csv(OUT_DIR / f"primitives_{symbol}_{run_tag}.csv", index=False)
    if not entries.empty:
        entries["symbol"] = symbol
        entries.to_csv(OUT_DIR / f"entries_{symbol}_{run_tag}.csv", index=False)
    moves.to_csv(OUT_DIR / f"moves_{symbol}_{run_tag}.csv", index=False)
    if not detail.empty:
        detail.to_csv(OUT_DIR / f"recall_detail_{symbol}_{run_tag}.csv", index=False)
    if not summary.empty:
        summary.to_csv(OUT_DIR / f"recall_summary_{symbol}_{run_tag}.csv", index=False)

    print(f"  total runtime for {symbol} : {_time.time()-t0:.1f}s")
    return summary


# ==========================================================================
# 12. MAIN
# ==========================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-03-01", help="start date YYYY-MM-DD")
    ap.add_argument("--end", default=datetime.now().strftime("%Y-%m-%d"),
                    help="end date YYYY-MM-DD (inclusive)")
    ap.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    ap.add_argument("--swing-n", type=int, default=DEFAULT_SWING_N)
    args = ap.parse_args()

    sb = _connect_supabase()
    syms = [s.strip() for s in args.symbols.split(",") if s.strip()]
    inst_ids = _resolve_instrument_ids(sb, syms)
    run_tag = datetime.now().strftime("%Y%m%d_%H%M")

    print("=" * 78)
    print(f"canonical_ict_recall  run={run_tag}")
    print(f"  symbols  = {syms}")
    print(f"  inst_ids = {inst_ids}")
    print(f"  range    = {args.start} -> {args.end}")
    print(f"  swing_n  = {args.swing_n}")
    print(f"  thresholds = {MOVE_THRESHOLDS}")
    print(f"  horizon  = {MOVE_HORIZON_MIN}min   recall lookback = {RECALL_LOOKBACK_MIN}min")
    print(f"  output   = {OUT_DIR.absolute()}")
    print("=" * 78)

    summaries = []
    for sym in syms:
        s = run_for_symbol(sb, sym, inst_ids[sym], args.start, args.end, args.swing_n, run_tag)
        if s is not None and not s.empty:
            summaries.append(s)

    if not summaries:
        print("\nno summaries produced; exiting.")
        return

    combined = pd.concat(summaries, ignore_index=True)
    combined.to_csv(OUT_DIR / f"recall_combined_{run_tag}.csv", index=False)

    print("\n" + "=" * 78)
    print("RECALL MATRIX  ( recall % = n_matched / n_moves )")
    print("=" * 78)
    for mode in ("RETURN", "FORMATION"):
        print(f"\n>>> mode = {mode}   {'(strict canon)' if mode=='RETURN' else '(upper bound)'}")
        pv = (combined[combined["mode"] == mode]
              .pivot_table(index=["symbol", "direction"], columns="tier",
                           values="recall_pct", aggfunc="first")
              .round(1))
        if not pv.empty:
            print(pv.to_string())
            n_pv = (combined[combined["mode"] == mode]
                    .pivot_table(index=["symbol", "direction"], columns="tier",
                                 values="n_moves", aggfunc="first")
                    .astype("Int64"))
            print("\nn_moves (denominator):")
            print(n_pv.to_string())

    print(f"\nall outputs : {OUT_DIR.absolute()}")
    print("done.")


if __name__ == "__main__":
    main()
