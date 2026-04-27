#!/usr/bin/env python3
"""
experiment_18_oi_wall_ict_confluence.py
=========================================
Experiment 18: OI Wall + ICT Zone Confluence — Break vs Reject

Question:
  When price approaches a heavy OI concentration (resistance wall = max CE OI,
  support wall = max PE OI), does ICT zone confluence predict whether price
  breaks through or rejects?

  Secondary: Under what regime conditions does each outcome occur?

Method:
  For each trading date and symbol:
  1. Build daily OI profile — find dominant CE OI strike (resistance wall)
     and PE OI strike (support wall) from hist_option_bars_1m
     (use first bar of day 09:15 snapshot for daily OI structure)
  2. For each 5-min snapshot in hist_market_state where spot is within
     APPROACH_PCT of an OI wall:
     - Check ICT confluence: is there a BEAR_OB/BULL_OB in hist_ict_htf_zones
       within CONFLUENCE_PCT of the OI wall strike?
     - Record regime context: gamma_regime, breadth_regime, DTE, time of day
     - Outcome: ret_30m direction vs wall direction
       CE wall (resistance): break = ret_30m > 0 (went through), reject = ret_30m < 0
       PE wall (support):    break = ret_30m < 0 (went through), reject = ret_30m > 0
  3. Compare break rate:
     - ICT confluence present vs absent
     - By gamma_regime
     - By breadth_regime
     - By DTE
     - By time of day

Tables:
  hist_option_bars_1m        — per-strike OI (vendor data, real OI)
  hist_ict_htf_zones         — ICT zones per date
  hist_market_state          — regime context + ret_30m outcome
  hist_spot_bars_1m          — intraday price (for spot at each bar)

Instrument IDs:
  NIFTY:  9992f600-51b3-4009-b487-f878692a0bc5
  SENSEX: 73a1390a-30c9-46d6-9d3f-5f03c3f5ad71

Parameters:
  APPROACH_PCT    = 0.5%  — how close spot must be to OI wall to count
  CONFLUENCE_PCT  = 0.5%  — how close ICT zone must be to OI wall to count
  OI_WALL_RADIUS  = 1500  — strike range around spot to look for OI walls (pts)
  MIN_OI_MULTIPLE = 2.0   — wall OI must be >= 2x mean OI to qualify as a wall
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

APPROACH_PCT    = 0.005   # 0.5%
CONFLUENCE_PCT  = 0.005   # 0.5%
OI_WALL_RADIUS  = 1500    # points around spot
MIN_OI_MULTIPLE = 2.0
PAGE_SIZE       = 1000


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fetch_all(sb, table, select, filters=None, order=None):
    all_rows, offset = [], 0
    while True:
        q = sb.table(table).select(select)
        if filters:
            for method, *args in filters:
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


def build_oi_walls(sb, instrument_id: str, trade_date: str, spot: float) -> dict:
    """
    Find dominant CE (resistance) and PE (support) OI walls for a given date.
    Uses first bar of the day (09:15 snapshot).
    Returns: {
        "CE": {"strike": float, "oi": int} or None,
        "PE": {"strike": float, "oi": int} or None
    }
    """
    lo = spot - OI_WALL_RADIUS
    hi = spot + OI_WALL_RADIUS

    # Fetch all strikes near spot for this date (first bar only)
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

    if not rows:
        return {"CE": None, "PE": None}

    # Take only first timestamp per strike/type
    seen = set()
    first_rows = []
    for r in rows:
        key = (r["strike"], r["option_type"])
        if key not in seen:
            seen.add(key)
            first_rows.append(r)

    ce_rows = [(float(r["strike"]), int(r["oi"])) for r in first_rows if r["option_type"] == "CE"]
    pe_rows = [(float(r["strike"]), int(r["oi"])) for r in first_rows if r["option_type"] == "PE"]

    def find_wall(rows_list, wall_type):
        if not rows_list:
            return None
        total_oi = sum(oi for _, oi in rows_list)
        mean_oi  = total_oi / len(rows_list) if rows_list else 1
        best = max(rows_list, key=lambda x: x[1])
        if best[1] >= mean_oi * MIN_OI_MULTIPLE:
            return {"strike": best[0], "oi": best[1], "mean_oi": mean_oi,
                    "multiple": best[1] / mean_oi if mean_oi > 0 else 0}
        return None

    return {
        "CE": find_wall(ce_rows, "CE"),  # Resistance wall above
        "PE": find_wall(pe_rows, "PE"),  # Support wall below
    }


def get_ict_zones_for_date(zones_by_date: dict, trade_date: str, symbol: str) -> list:
    return zones_by_date.get((trade_date, symbol), [])


def ict_confluent(zones: list, wall_strike: float, spot: float) -> bool:
    """Check if any ICT zone is within CONFLUENCE_PCT of the wall strike."""
    for z in zones:
        z_mid = (z["high"] + z["low"]) / 2
        if abs(z_mid - wall_strike) / spot <= CONFLUENCE_PCT:
            return True
        # Also check if wall_strike is inside the zone
        if z["low"] <= wall_strike <= z["high"]:
            return True
    return False


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("Experiment 18: OI Wall + ICT Zone Confluence — Break vs Reject")
    log("=" * 65)

    # ── Step 1: Load ICT zones ───────────────────────────────────────────
    log("\nStep 1: Loading ICT zones from hist_ict_htf_zones...")
    raw_zones = fetch_all(
        sb, "hist_ict_htf_zones",
        "as_of_date,symbol,pattern_type,zone_high,zone_low",
        filters=[("in_", "pattern_type", '("BEAR_OB","BULL_OB","BULL_FVG","BEAR_FVG")')],
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

    # ── Step 2: Load market state ────────────────────────────────────────
    log("\nStep 2: Loading hist_market_state...")
    mkt_rows = fetch_all(
        sb, "hist_market_state",
        "bar_ts,trade_date,symbol,spot,gamma_regime,breadth_regime,ret_30m",
        order="bar_ts"
    )
    log(f"  Loaded {len(mkt_rows)} market state rows")

    # ── Step 3: Get unique dates per symbol ──────────────────────────────
    dates_by_symbol = defaultdict(set)
    for r in mkt_rows:
        dates_by_symbol[r["symbol"]].add(r["trade_date"])

    log(f"\n  NIFTY dates: {len(dates_by_symbol['NIFTY'])}")
    log(f"  SENSEX dates: {len(dates_by_symbol['SENSEX'])}")

    # ── Step 4: Build OI walls per date ──────────────────────────────────
    log("\nStep 3: Building OI walls per date/symbol...")
    oi_walls = {}  # (date, symbol) -> {"CE": wall, "PE": wall}

    for symbol, dates in dates_by_symbol.items():
        inst_id = INSTRUMENTS[symbol]
        log(f"  {symbol}: processing {len(dates)} dates...")
        for i, trade_date in enumerate(sorted(dates)):
            # Get approximate spot for this date from market state
            day_rows = [r for r in mkt_rows
                       if r["trade_date"] == trade_date and r["symbol"] == symbol
                       and r.get("spot")]
            if not day_rows:
                continue
            spot = float(day_rows[0]["spot"])
            walls = build_oi_walls(sb, inst_id, trade_date, spot)
            oi_walls[(trade_date, symbol)] = walls
            if (i + 1) % 20 == 0:
                log(f"    [{i+1}/{len(dates)}] {trade_date} done")

    log(f"  Built OI walls for {len(oi_walls)} date/symbol pairs")

    # ── Step 5: Match market state bars to OI walls ──────────────────────
    log("\nStep 4: Matching market state bars to OI walls...")

    # Results: keyed by (wall_type, ict_confluent, gamma_regime)
    results = defaultdict(lambda: {
        "breaks": 0, "rejects": 0, "ret_sum": 0.0,
        "gamma": defaultdict(lambda: {"breaks": 0, "rejects": 0}),
        "breadth": defaultdict(lambda: {"breaks": 0, "rejects": 0}),
        "session": defaultdict(lambda: {"breaks": 0, "rejects": 0}),
    })

    total_approaches = 0
    skipped = 0

    for row in mkt_rows:
        trade_date = row.get("trade_date", "")
        symbol     = row.get("symbol", "")
        spot       = row.get("spot")
        gamma      = row.get("gamma_regime", "UNKNOWN")
        breadth    = row.get("breadth_regime", "UNKNOWN")
        ret_30m    = row.get("ret_30m")
        bar_ts     = row.get("bar_ts", "")

        if not spot or ret_30m is None:
            skipped += 1
            continue

        spot = float(spot)
        ret  = float(ret_30m)

        walls = oi_walls.get((trade_date, symbol))
        if not walls:
            continue

        zones = get_ict_zones_for_date(zones_by_date, trade_date, symbol)

        # Get session time (bar_ts treated as IST directly)
        try:
            dt = datetime.fromisoformat(bar_ts.replace("Z", "+00:00"))
            h, m = dt.hour, dt.minute
            mins = h * 60 + m
            if mins < 9*60+15:
                session = "PRE"
            elif mins <= 10*60+30:
                session = "MORNING"
            elif mins <= 13*60:
                session = "MIDDAY"
            elif mins <= 14*60+30:
                session = "AFTERNOON"
            else:
                session = "PRECLOSE"
        except:
            session = "UNKNOWN"

        # Check CE wall (resistance above spot)
        ce_wall = walls.get("CE")
        if ce_wall and ce_wall["strike"] > spot:
            dist_pct = (ce_wall["strike"] - spot) / spot
            if dist_pct <= APPROACH_PCT:
                total_approaches += 1
                confluent = ict_confluent(zones, ce_wall["strike"], spot)
                # Break = price went up through resistance (ret_30m > 0)
                broke = ret > 0
                key = ("CE_WALL", confluent)
                results[key]["breaks"]   += 1 if broke else 0
                results[key]["rejects"]  += 0 if broke else 1
                results[key]["ret_sum"]  += ret
                results[key]["gamma"][gamma]["breaks"]   += 1 if broke else 0
                results[key]["gamma"][gamma]["rejects"]  += 0 if broke else 1
                results[key]["breadth"][breadth]["breaks"]  += 1 if broke else 0
                results[key]["breadth"][breadth]["rejects"] += 0 if broke else 1
                results[key]["session"][session]["breaks"]  += 1 if broke else 0
                results[key]["session"][session]["rejects"] += 0 if broke else 1

        # Check PE wall (support below spot)
        pe_wall = walls.get("PE")
        if pe_wall and pe_wall["strike"] < spot:
            dist_pct = (spot - pe_wall["strike"]) / spot
            if dist_pct <= APPROACH_PCT:
                total_approaches += 1
                confluent = ict_confluent(zones, pe_wall["strike"], spot)
                # Break = price went down through support (ret_30m < 0)
                broke = ret < 0
                key = ("PE_WALL", confluent)
                results[key]["breaks"]   += 1 if broke else 0
                results[key]["rejects"]  += 0 if broke else 1
                results[key]["ret_sum"]  += ret
                results[key]["gamma"][gamma]["breaks"]   += 1 if broke else 0
                results[key]["gamma"][gamma]["rejects"]  += 0 if broke else 1
                results[key]["breadth"][breadth]["breaks"]  += 1 if broke else 0
                results[key]["breadth"][breadth]["rejects"] += 0 if broke else 1
                results[key]["session"][session]["breaks"]  += 1 if broke else 0
                results[key]["session"][session]["rejects"] += 0 if broke else 1

    log(f"  Total wall approaches: {total_approaches}")

    # ── Step 6: Results ──────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("RESULTS")
    log("=" * 65)

    if total_approaches == 0:
        log("\nZERO wall approaches found.")
        log("Possible issues:")
        log("  1. OI walls not building (hist_option_bars_1m timeout?)")
        log("  2. APPROACH_PCT too tight (0.5%)")
        log("  3. Date/symbol mismatch between tables")
        # Diagnostic
        log("\nOI walls built:")
        sample = list(oi_walls.items())[:5]
        for k, v in sample:
            log(f"  {k}: CE={v.get('CE')} PE={v.get('PE')}")
        return

    for wall_type in ["CE_WALL", "PE_WALL"]:
        log(f"\n{'─'*60}")
        log(f"{wall_type} — {'Resistance above (break = up)' if wall_type == 'CE_WALL' else 'Support below (break = down)'}")
        log(f"{'─'*60}")

        for confluent in [True, False]:
            key = (wall_type, confluent)
            if key not in results:
                continue
            b = results[key]
            n      = b["breaks"] + b["rejects"]
            breaks = b["breaks"]
            br     = breaks / n * 100 if n > 0 else 0
            avg    = b["ret_sum"] / n if n > 0 else 0
            conf_str = "WITH ICT confluence" if confluent else "WITHOUT ICT confluence"
            log(f"\n  {conf_str} (N={n}):")
            log(f"    Break rate:  {br:.1f}% | Reject rate: {100-br:.1f}% | Avg ret30m: {avg:+.3f}%")

            # By gamma
            log(f"    By gamma regime:")
            for regime in ["SHORT_GAMMA", "LONG_GAMMA", "NO_FLIP"]:
                g = b["gamma"].get(regime, {})
                gn = g.get("breaks", 0) + g.get("rejects", 0)
                if gn == 0:
                    continue
                gbr = g.get("breaks", 0) / gn * 100
                log(f"      {regime:<15}: break {gbr:.1f}% (N={gn})")

            # By breadth
            log(f"    By breadth regime:")
            for regime in ["BULLISH", "BEARISH", "TRANSITION", "NEUTRAL"]:
                g = b["breadth"].get(regime, {})
                gn = g.get("breaks", 0) + g.get("rejects", 0)
                if gn == 0:
                    continue
                gbr = g.get("breaks", 0) / gn * 100
                log(f"      {regime:<15}: break {gbr:.1f}% (N={gn})")

            # By session
            log(f"    By session:")
            for sess in ["MORNING", "MIDDAY", "AFTERNOON", "PRECLOSE"]:
                g = b["session"].get(sess, {})
                gn = g.get("breaks", 0) + g.get("rejects", 0)
                if gn == 0:
                    continue
                gbr = g.get("breaks", 0) / gn * 100
                log(f"      {sess:<12}: break {gbr:.1f}% (N={gn})")

    # ── Synthesis Signal ─────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("SYNTHESIS — ICT + OI Confluence Signal")
    log("=" * 65)

    ce_with    = results.get(("CE_WALL", True), {})
    ce_without = results.get(("CE_WALL", False), {})
    pe_with    = results.get(("PE_WALL", True), {})
    pe_without = results.get(("PE_WALL", False), {})

    for label, with_r, without_r, direction in [
        ("CE RESISTANCE (BUY PE signal)", ce_with, ce_without, "reject"),
        ("PE SUPPORT (BUY CE signal)",    pe_with, pe_without, "reject"),
    ]:
        wn  = with_r.get("breaks", 0) + with_r.get("rejects", 0)
        wor = without_r.get("breaks", 0) + without_r.get("rejects", 0)
        if wn == 0 or wor == 0:
            continue

        w_reject  = with_r.get("rejects", 0) / wn * 100
        wo_reject = without_r.get("rejects", 0) / wor * 100
        lift      = w_reject - wo_reject

        log(f"\n  {label}:")
        log(f"    ICT confluent:     {w_reject:.1f}% reject rate (N={wn})")
        log(f"    No ICT confluence: {wo_reject:.1f}% reject rate (N={wor})")
        log(f"    ICT lift:          {lift:+.1f}pp")

        if lift >= 15:
            log(f"    -> STRONG EDGE: ICT confluence adds {lift:.1f}pp to rejection rate")
            log(f"       BUILD synthesis signal: OI wall + ICT zone = high conviction entry")
        elif lift >= 8:
            log(f"    -> MODERATE EDGE: Shadow test before implementing")
        else:
            log(f"    -> WEAK/NO EDGE: OI walls and ICT zones are independent")

    log("\nExperiment 18 complete.")


if __name__ == "__main__":
    main()
