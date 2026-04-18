#!/usr/bin/env python3
"""
experiment_18_confluence_rerun.py
===================================
Re-runs ONLY the ICT confluence matching step of Experiment 18.

Fixes:
1. ICT zone fetch now uses correct list syntax for in_ filter
2. Loads oi_walls from cache file (skips the 3-hour OI build)
3. Re-runs zone matching + confluence analysis

Run after experiment_18_oi_ict_confluence.py has completed.
The OI walls are re-built from hist_market_state + hist_option_bars_1m
in the main experiment — this script re-derives them faster by reading
from Supabase directly with correct instrument_id filters.
"""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

APPROACH_PCT   = 0.005  # 0.5%
CONFLUENCE_PCT = 0.005  # 0.5%
OI_WALL_RADIUS = 1500
MIN_OI_MULTIPLE = 2.0
PAGE_SIZE = 1000
CACHE_FILE = Path("runtime/exp18_oi_walls_cache.json")


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fetch_all(sb, table, select, filters=None, order=None):
    all_rows, offset = [], 0
    while True:
        q = sb.table(table).select(select)
        if filters:
            for f in filters:
                method = f[0]
                args   = f[1:]
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
                    log(f"  ERROR: {e}")
                    return all_rows
                time.sleep(2 ** attempt)
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def build_oi_walls_for_date(sb, instrument_id, trade_date, spot):
    lo = spot - OI_WALL_RADIUS
    hi = spot + OI_WALL_RADIUS

    rows = fetch_all(
        sb, "hist_option_bars_1m",
        "strike,option_type,oi",
        filters=[
            ("eq", "instrument_id", instrument_id),
            ("eq", "trade_date", trade_date),
            ("eq", "is_pre_market", False),
            ("gt", "strike", str(lo)),
            ("lt", "strike", str(hi)),
            ("gt", "oi", "0"),
        ],
        order="bar_ts"
    )

    seen = set()
    first_rows = []
    for r in rows:
        key = (r["strike"], r["option_type"])
        if key not in seen:
            seen.add(key)
            first_rows.append(r)

    ce_rows = [(float(r["strike"]), int(r["oi"])) for r in first_rows if r["option_type"] == "CE"]
    pe_rows = [(float(r["strike"]), int(r["oi"])) for r in first_rows if r["option_type"] == "PE"]

    def find_wall(rows_list):
        if not rows_list:
            return None
        mean_oi = sum(oi for _, oi in rows_list) / len(rows_list)
        best = max(rows_list, key=lambda x: x[1])
        if best[1] >= mean_oi * MIN_OI_MULTIPLE:
            return {"strike": best[0], "oi": best[1]}
        return None

    return {"CE": find_wall(ce_rows), "PE": find_wall(pe_rows)}


def ict_confluent(zones, wall_strike, spot):
    for z in zones:
        z_mid = (z["high"] + z["low"]) / 2
        if abs(z_mid - wall_strike) / spot <= CONFLUENCE_PCT:
            return True
        if z["low"] <= wall_strike <= z["high"]:
            return True
    return False


def is_morning(bar_ts_str):
    try:
        dt = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
        mins = dt.hour * 60 + dt.minute
        return (9*60+15) <= mins <= (10*60+30)
    except:
        return False


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


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("Experiment 18: ICT Confluence Re-run (fixed in_ filter)")
    log("=" * 65)

    # ── Step 1: Load ICT zones (FIXED: use list not string) ─────────────
    log("\nStep 1: Loading ICT zones (fixed filter)...")
    raw_zones = fetch_all(
        sb, "hist_ict_htf_zones",
        "as_of_date,symbol,pattern_type,zone_high,zone_low",
        filters=[
            ("in_", "pattern_type", ["BEAR_OB", "BULL_OB", "BULL_FVG", "BEAR_FVG"])
        ],
        order="as_of_date"
    )
    log(f"  Loaded {len(raw_zones)} ICT zone rows")

    zones_by_date = defaultdict(list)
    for z in raw_zones:
        key = (z["as_of_date"], z["symbol"])
        zones_by_date[key].append({
            "high":    float(z["zone_high"]),
            "low":     float(z["zone_low"]),
            "pattern": z["pattern_type"],
        })
    log(f"  Unique date/symbol combos: {len(zones_by_date)}")

    # ── Step 2: Load market state ────────────────────────────────────────
    log("\nStep 2: Loading hist_market_state...")
    mkt_rows = fetch_all(
        sb, "hist_market_state",
        "bar_ts,trade_date,symbol,spot,gamma_regime,breadth_regime,ret_30m",
        order="bar_ts"
    )
    log(f"  Loaded {len(mkt_rows)} rows")

    # ── Step 3: Load or rebuild OI walls ────────────────────────────────
    CACHE_FILE.parent.mkdir(exist_ok=True)

    if CACHE_FILE.exists():
        log(f"\nStep 3: Loading OI walls from cache ({CACHE_FILE})...")
        with open(CACHE_FILE, encoding="utf-8") as f:
            oi_walls_raw = json.load(f)
        # Convert string keys back
        oi_walls = {tuple(k.split("|")): v for k, v in oi_walls_raw.items()}
        log(f"  Loaded {len(oi_walls)} date/symbol pairs from cache")
    else:
        log(f"\nStep 3: Cache not found — rebuilding OI walls...")
        log(f"  This will take ~3 hours. Run experiment_18_oi_ict_confluence.py first.")
        log(f"  Building now anyway...")

        dates_by_symbol = defaultdict(set)
        for r in mkt_rows:
            dates_by_symbol[r["symbol"]].add(r["trade_date"])

        oi_walls = {}
        for symbol, dates in dates_by_symbol.items():
            inst_id = INSTRUMENTS[symbol]
            log(f"  {symbol}: {len(dates)} dates...")
            for i, trade_date in enumerate(sorted(dates)):
                day_rows = [r for r in mkt_rows
                           if r["trade_date"] == trade_date
                           and r["symbol"] == symbol
                           and r.get("spot")]
                if not day_rows:
                    continue
                spot = float(day_rows[0]["spot"])
                walls = build_oi_walls_for_date(sb, inst_id, trade_date, spot)
                oi_walls[(trade_date, symbol)] = walls
                if (i + 1) % 20 == 0:
                    log(f"    [{i+1}/{len(dates)}] {trade_date}")

        # Save cache
        cache_data = {f"{k[0]}|{k[1]}": v for k, v in oi_walls.items()}
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)
        log(f"  Saved {len(oi_walls)} pairs to cache")

    # ── Step 4: Match bars to OI walls WITH ICT confluence ───────────────
    log("\nStep 4: Matching bars to OI walls (with ICT confluence)...")

    results = defaultdict(lambda: {
        "breaks": 0, "rejects": 0, "ret_sum": 0.0,
        "gamma":   defaultdict(lambda: {"breaks": 0, "rejects": 0}),
        "breadth": defaultdict(lambda: {"breaks": 0, "rejects": 0}),
        "session": defaultdict(lambda: {"breaks": 0, "rejects": 0}),
    })

    total_approaches = 0

    for row in mkt_rows:
        trade_date = row.get("trade_date", "")
        symbol     = row.get("symbol", "")
        spot       = row.get("spot")
        gamma      = row.get("gamma_regime", "UNKNOWN")
        breadth    = row.get("breadth_regime", "UNKNOWN")
        ret_30m    = row.get("ret_30m")
        bar_ts     = row.get("bar_ts", "")

        if not spot or ret_30m is None:
            continue

        spot = float(spot)
        ret  = float(ret_30m)

        walls = oi_walls.get((trade_date, symbol))
        if not walls:
            continue

        zones   = zones_by_date.get((trade_date, symbol), [])
        session = get_session(bar_ts)

        # CE wall
        ce_wall = walls.get("CE")
        if ce_wall and ce_wall["strike"] > spot:
            dist_pct = (ce_wall["strike"] - spot) / spot
            if dist_pct <= APPROACH_PCT:
                total_approaches += 1
                confluent = ict_confluent(zones, ce_wall["strike"], spot)
                broke = ret > 0
                key = ("CE_WALL", confluent)
                results[key]["breaks"]  += 1 if broke else 0
                results[key]["rejects"] += 0 if broke else 1
                results[key]["ret_sum"] += ret
                results[key]["gamma"][gamma]["breaks"]    += 1 if broke else 0
                results[key]["gamma"][gamma]["rejects"]   += 0 if broke else 1
                results[key]["breadth"][breadth]["breaks"]  += 1 if broke else 0
                results[key]["breadth"][breadth]["rejects"] += 0 if broke else 1
                results[key]["session"][session]["breaks"]  += 1 if broke else 0
                results[key]["session"][session]["rejects"] += 0 if broke else 1

        # PE wall
        pe_wall = walls.get("PE")
        if pe_wall and pe_wall["strike"] < spot:
            dist_pct = (spot - pe_wall["strike"]) / spot
            if dist_pct <= APPROACH_PCT:
                total_approaches += 1
                confluent = ict_confluent(zones, pe_wall["strike"], spot)
                broke = ret < 0
                key = ("PE_WALL", confluent)
                results[key]["breaks"]  += 1 if broke else 0
                results[key]["rejects"] += 0 if broke else 1
                results[key]["ret_sum"] += ret
                results[key]["gamma"][gamma]["breaks"]    += 1 if broke else 0
                results[key]["gamma"][gamma]["rejects"]   += 0 if broke else 1
                results[key]["breadth"][breadth]["breaks"]  += 1 if broke else 0
                results[key]["breadth"][breadth]["rejects"] += 0 if broke else 1
                results[key]["session"][session]["breaks"]  += 1 if broke else 0
                results[key]["session"][session]["rejects"] += 0 if broke else 1

    log(f"  Total wall approaches: {total_approaches}")

    # ── Step 5: Results ──────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("RESULTS: OI Wall Break vs Reject — WITH vs WITHOUT ICT Confluence")
    log("=" * 65)

    for wall_type in ["CE_WALL", "PE_WALL"]:
        direction = "Resistance — break=up, reject=down" if wall_type == "CE_WALL" else "Support — break=down, reject=up"
        log(f"\n{'─'*60}")
        log(f"{wall_type} ({direction})")
        log(f"{'─'*60}")

        for confluent in [True, False]:
            key = (wall_type, confluent)
            if key not in results:
                log(f"\n  {'WITH' if confluent else 'WITHOUT'} ICT confluence: NO DATA")
                continue
            b = results[key]
            n      = b["breaks"] + b["rejects"]
            breaks = b["breaks"]
            br     = breaks / n * 100 if n > 0 else 0
            avg    = b["ret_sum"] / n if n > 0 else 0
            label  = "WITH ICT confluence   " if confluent else "WITHOUT ICT confluence"

            log(f"\n  {label} (N={n}):")
            log(f"    Break rate:  {br:.1f}% | Reject rate: {100-br:.1f}% | Avg ret30m: {avg:+.3f}%")

            for regime in ["SHORT_GAMMA", "LONG_GAMMA", "NO_FLIP"]:
                g = b["gamma"].get(regime, {})
                gn = g.get("breaks", 0) + g.get("rejects", 0)
                if gn == 0: continue
                gbr = g.get("breaks", 0) / gn * 100
                log(f"      {regime:<15}: break {gbr:.1f}% reject {100-gbr:.1f}% (N={gn})")

            for regime in ["BULLISH", "BEARISH", "NEUTRAL"]:
                g = b["breadth"].get(regime, {})
                gn = g.get("breaks", 0) + g.get("rejects", 0)
                if gn == 0: continue
                gbr = g.get("breaks", 0) / gn * 100
                log(f"      {regime:<15}: break {gbr:.1f}% reject {100-gbr:.1f}% (N={gn})")

            for sess in ["MORNING", "MIDDAY", "AFTERNOON", "PRECLOSE"]:
                g = b["session"].get(sess, {})
                gn = g.get("breaks", 0) + g.get("rejects", 0)
                if gn == 0: continue
                gbr = g.get("breaks", 0) / gn * 100
                log(f"      {sess:<15}: break {gbr:.1f}% reject {100-gbr:.1f}% (N={gn})")

    # ── Synthesis ────────────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("SYNTHESIS: Does ICT confluence improve OI wall reject rate?")
    log("=" * 65)

    for wall_type, signal_label in [
        ("CE_WALL", "BUY PE (fade resistance)"),
        ("PE_WALL", "BUY CE (fade support break)"),
    ]:
        with_r    = results.get((wall_type, True), {})
        without_r = results.get((wall_type, False), {})
        wn  = with_r.get("breaks", 0) + with_r.get("rejects", 0)
        won = without_r.get("breaks", 0) + without_r.get("rejects", 0)

        if wn == 0 or won == 0:
            log(f"\n  {wall_type}: INSUFFICIENT DATA (ICT confluence N={wn})")
            continue

        w_reject  = with_r.get("rejects", 0) / wn * 100
        wo_reject = without_r.get("rejects", 0) / won * 100
        lift      = w_reject - wo_reject

        log(f"\n  {wall_type} — {signal_label}:")
        log(f"    ICT confluent:     {w_reject:.1f}% reject rate (N={wn})")
        log(f"    No ICT confluence: {wo_reject:.1f}% reject rate (N={won})")
        log(f"    ICT lift:          {lift:+.1f}pp")

        if lift >= 15:
            log(f"    -> STRONG EDGE: Build ENH-56 synthesis signal")
            log(f"       OI wall + ICT zone = high conviction entry")
        elif lift >= 8:
            log(f"    -> MODERATE EDGE: Shadow test before implementing")
        else:
            log(f"    -> WEAK/NO EDGE: ICT zones and OI walls are independent")

    log("\nExperiment 18 confluence re-run complete.")


if __name__ == "__main__":
    main()
