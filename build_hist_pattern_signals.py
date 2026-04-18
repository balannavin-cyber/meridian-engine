#!/usr/bin/env python3
"""
build_hist_pattern_signals.py  (v2 — correct column names)
============================================================
Backfills hist_pattern_signals from hist_market_state + hist_ict_htf_zones.

Corrections vs v1:
  - hist_market_state: no pcr_regime/flow_regime/skew_regime/dte — removed
  - hist_spot_bars_1m: uses instrument_id not symbol — fixed
  - momentum_regime used instead of ret_session direction
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, Counter
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
PAGE_SIZE    = 1000

APPROACH_PCT  = 0.005
SWEEP_MIN_PCT = 0.001

INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

PATTERN_DIRECTION = {
    "BEAR_OB":  "BUY_PE",
    "BEAR_FVG": "BUY_PE",
    "BULL_OB":  "BUY_CE",
    "BULL_FVG": "BUY_CE",
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fetch_all(sb, table, select, filters=None, order=None):
    all_rows, offset = [], 0
    while True:
        q = sb.table(table).select(select)
        if filters:
            for f in filters:
                method, *args = f
                q = getattr(q, method)(*args)
        if order:
            q = q.order(order)
        q = q.range(offset, offset + PAGE_SIZE - 1)
        for attempt in range(3):
            try:
                rows = q.execute().data
                break
            except Exception as e:
                if attempt == 2:
                    log(f"  ERROR fetching {table}: {e}")
                    return all_rows
                time.sleep(2 ** attempt)
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def get_session(bar_ts_str):
    try:
        dt = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
        mins = dt.hour * 60 + dt.minute
        if mins < 9*60+15:       return "PRE"
        elif mins <= 10*60+30:   return "MORNING"
        elif mins <= 13*60:      return "MIDDAY"
        elif mins <= 14*60+30:   return "AFTERNOON"
        else:                    return "PRECLOSE"
    except:
        return "UNKNOWN"


def get_hour_min(bar_ts_str):
    try:
        dt = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
        return dt.hour, dt.minute
    except:
        return 0, 0


def infer_tier(pattern_type, zone_timeframe):
    if pattern_type in ("BEAR_OB", "BULL_OB"):
        return "TIER1" if zone_timeframe == "W" else "TIER2"
    elif pattern_type in ("BEAR_FVG", "BULL_FVG"):
        return "TIER2" if zone_timeframe == "W" else "TIER3"
    return "TIER2"


def compute_ret_60m(spot_bars, bar_ts_str, spot):
    try:
        dt_signal = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
        target_mins = dt_signal.hour * 60 + dt_signal.minute + 60
        for bar in spot_bars:
            dt_bar = datetime.fromisoformat(bar["bar_ts"].replace("Z", "+00:00"))
            if abs(dt_bar.hour * 60 + dt_bar.minute - target_mins) <= 2:
                return (float(bar["close"]) - spot) / spot * 100
    except:
        pass
    return None


def make_signal(trade_date, bar_ts, symbol, pattern_type, tier,
                direction, session, zone_high, zone_low, zone_tf,
                spot, row, ret_30m, ret_60m):
    win_30m = None
    if ret_30m is not None:
        win_30m = float(ret_30m) < 0 if direction == "BUY_PE" else float(ret_30m) > 0
    win_60m = None
    if ret_60m is not None:
        win_60m = ret_60m < 0 if direction == "BUY_PE" else ret_60m > 0
    return {
        "trade_date":    trade_date,
        "bar_ts":        bar_ts,
        "symbol":        symbol,
        "pattern_type":  pattern_type,
        "tier":          tier,
        "direction":     direction,
        "session":       session,
        "zone_high":     zone_high,
        "zone_low":      zone_low,
        "zone_timeframe": zone_tf,
        "spot_at_signal": spot,
        "dte":           None,
        "gamma_regime":  row.get("gamma_regime", "UNKNOWN"),
        "breadth_regime": row.get("breadth_regime", "UNKNOWN"),
        "iv_regime":     row.get("iv_regime", "UNKNOWN"),
        "pcr_regime":    None,
        "flow_regime":   None,
        "skew_regime":   None,
        "ret_session":   row.get("ret_session"),
        "vix_at_signal": row.get("atm_iv"),
        "ret_30m":       ret_30m,
        "ret_60m":       ret_60m,
        "win_30m":       win_30m,
        "win_60m":       win_60m,
        "source":        "backfill",
    }


def upsert_batch(sb, rows):
    if not rows:
        return 0
    for attempt in range(3):
        try:
            sb.table("hist_pattern_signals").upsert(
                rows,
                on_conflict="trade_date,symbol,bar_ts,pattern_type,zone_high,zone_low"
            ).execute()
            return len(rows)
        except Exception as e:
            if attempt == 2:
                log(f"  UPSERT ERROR: {e}")
                return 0
            time.sleep(2 ** attempt)
    return 0


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("build_hist_pattern_signals.py v2")
    log("=" * 65)

    # Step 1: ICT zones
    log("\nStep 1: Loading ICT zones...")
    raw_zones = fetch_all(
        sb, "hist_ict_htf_zones",
        "as_of_date,symbol,pattern_type,zone_high,zone_low,timeframe",
        filters=[("in_", "pattern_type",
                  ["BEAR_OB","BULL_OB","BULL_FVG","BEAR_FVG","PDH","PDL"])],
        order="as_of_date"
    )
    log(f"  {len(raw_zones)} zone rows")

    zones_by_date = defaultdict(list)
    pdlevels      = defaultdict(dict)
    for z in raw_zones:
        key = (z["as_of_date"], z["symbol"])
        pt  = z["pattern_type"]
        if pt in ("BEAR_OB","BULL_OB","BEAR_FVG","BULL_FVG"):
            zones_by_date[key].append({
                "high": float(z["zone_high"]), "low": float(z["zone_low"]),
                "pattern": pt, "timeframe": z["timeframe"],
            })
        elif pt == "PDL":
            pdlevels[key]["pdl"] = float(z["zone_low"])
        elif pt == "PDH":
            pdlevels[key]["pdh"] = float(z["zone_high"])

    # Step 2: Market state
    log("\nStep 2: Loading hist_market_state...")
    mkt_rows = fetch_all(
        sb, "hist_market_state",
        "bar_ts,trade_date,symbol,spot,gamma_regime,breadth_regime,"
        "iv_regime,atm_iv,momentum_regime,ret_session,ret_30m",
        order="bar_ts"
    )
    log(f"  {len(mkt_rows)} rows")

    # Step 3: Spot bars (for ret_60m)
    log("\nStep 3: Loading spot bars for ret_60m...")
    spot_by = defaultdict(list)
    for symbol, inst_id in INSTRUMENTS.items():
        rows = fetch_all(
            sb, "hist_spot_bars_1m",
            "trade_date,bar_ts,close",
            filters=[("eq","instrument_id",inst_id),
                     ("eq","is_pre_market",False)],
            order="bar_ts"
        )
        for r in rows:
            spot_by[(r["trade_date"], symbol)].append(r)
        log(f"  {symbol}: {len(rows)} bars")

    # Step 4: Detect
    log("\nStep 4: Detecting signals...")
    bars_by = defaultdict(list)
    for r in mkt_rows:
        bars_by[(r["trade_date"], r["symbol"])].append(r)

    pending = []
    seen    = set()
    total   = sweeps = written = 0

    for (trade_date, symbol), day_bars in sorted(bars_by.items()):
        day_bars  = sorted(day_bars, key=lambda r: r["bar_ts"])
        zones     = zones_by_date.get((trade_date, symbol), [])
        pdl_val   = pdlevels.get((trade_date, symbol), {}).get("pdl")
        pdh_val   = pdlevels.get((trade_date, symbol), {}).get("pdh")
        spot_bars = spot_by.get((trade_date, symbol), [])
        swept_pdl = swept_pdh = False

        for i, row in enumerate(day_bars):
            bar_ts  = row["bar_ts"]
            spot    = row.get("spot")
            if not spot:
                continue
            spot    = float(spot)
            session = get_session(bar_ts)
            h, m    = get_hour_min(bar_ts)
            ret_30m = row.get("ret_30m")

            # ICT zone signals
            for z in zones:
                pattern   = z["pattern"]
                direction = PATTERN_DIRECTION[pattern]
                zh, zl    = z["high"], z["low"]

                in_zone    = zl <= spot <= zh
                near_bear  = (pattern in ("BEAR_OB","BEAR_FVG") and
                              0 < (zl - spot) / spot <= APPROACH_PCT)
                near_bull  = (pattern in ("BULL_OB","BULL_FVG") and
                              0 < (spot - zh) / spot <= APPROACH_PCT)
                if not (in_zone or near_bear or near_bull):
                    continue

                key = (trade_date, symbol, round(zh,1), round(zl,1), session)
                if key in seen:
                    continue
                seen.add(key)

                ret_60m = compute_ret_60m(spot_bars, bar_ts, spot)
                pending.append(make_signal(
                    trade_date, bar_ts, symbol, pattern,
                    infer_tier(pattern, z["timeframe"]),
                    direction, session, zh, zl, z["timeframe"],
                    spot, row, ret_30m, ret_60m
                ))
                total += 1

            # Sweep reversal (morning only, first 6 bars)
            if session == "MORNING" and h == 9 and m <= 35 and i > 0:
                prev = day_bars[i-1].get("spot")
                if not prev:
                    continue
                prev = float(prev)

                if (pdl_val and not swept_pdl and
                        prev < pdl_val * (1 - SWEEP_MIN_PCT) and spot > pdl_val):
                    swept_pdl = True
                    sk = (trade_date, symbol, "SWEEP_BULL")
                    if sk not in seen:
                        seen.add(sk)
                        ret_60m = compute_ret_60m(spot_bars, bar_ts, spot)
                        pending.append(make_signal(
                            trade_date, bar_ts, symbol, "SWEEP_REVERSAL",
                            "TIER1", "BUY_CE", session,
                            pdl_val+20, pdl_val-20, "D",
                            spot, row, ret_30m, ret_60m
                        ))
                        total += 1; sweeps += 1

                if (pdh_val and not swept_pdh and
                        prev > pdh_val * (1 + SWEEP_MIN_PCT) and spot < pdh_val):
                    swept_pdh = True
                    sk = (trade_date, symbol, "SWEEP_BEAR")
                    if sk not in seen:
                        seen.add(sk)
                        ret_60m = compute_ret_60m(spot_bars, bar_ts, spot)
                        pending.append(make_signal(
                            trade_date, bar_ts, symbol, "SWEEP_REVERSAL",
                            "TIER1", "BUY_PE", session,
                            pdh_val+20, pdh_val-20, "D",
                            spot, row, ret_30m, ret_60m
                        ))
                        total += 1; sweeps += 1

            if len(pending) >= 200:
                written += upsert_batch(sb, pending)
                pending = []

    if pending:
        written += upsert_batch(sb, pending)

    log(f"\n  Signals detected: {total} (ICT: {total-sweeps}, Sweeps: {sweeps})")
    log(f"  Rows written: {written}")

    # Verify
    log("\nStep 5: Verifying...")
    r = sb.table("hist_pattern_signals").select(
        "pattern_type", count="exact").limit(10000).execute()
    log(f"  Total rows: {r.count}")
    for ptype, cnt in sorted(Counter(
            row["pattern_type"] for row in r.data).items()):
        log(f"  {ptype}: {cnt}")

    log("\nDone. Run experiment_19_bull_ob_long_gamma.py next.")


if __name__ == "__main__":
    main()
