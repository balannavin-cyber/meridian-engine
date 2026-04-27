#!/usr/bin/env python3
"""
experiment_17_bear_ob_gamma_override.py
=========================================
Experiment 17: Does BEAR_OB MORNING edge hold under LONG_GAMMA regime?

Question:
  BEAR_OB TIER1 MORNING has 94.4% WR overall (Experiment 2).
  MERDIAN currently blocks BUY_PE when gamma_regime = LONG_GAMMA.
  Should it override LONG_GAMMA when a BEAR_OB is detected in the morning session?

Method:
  1. For each trading date, fetch active BEAR_OB zones from hist_ict_htf_zones
  2. Find morning bars (09:15-10:30 IST) in hist_market_state where spot
     entered a BEAR_OB zone (zone_low <= spot <= zone_high)
  3. Record gamma_regime at signal bar
  4. Outcome: ret_30m < 0 = PE win (price fell as expected for BEAR_OB)
  5. Split by gamma_regime and compare win rates + expectancy

Tables used:
  - hist_ict_htf_zones (35,862 rows — backfilled 2026-04-16)
  - hist_market_state (gamma_regime, bar_ts, spot, ret_30m)

Output:
  Win rate and expectancy by gamma_regime for BEAR_OB MORNING signals
"""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

IST = ZoneInfo("Asia/Kolkata")

# Morning session: 09:15 to 10:30 IST
MORNING_START_H = 9
MORNING_START_M = 15
MORNING_END_H   = 10
MORNING_END_M   = 30

PAGE_SIZE = 1000


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fetch_all(sb, table, select, filters=None, order=None):
    """Paginated fetch."""
    all_rows, offset = [], 0
    while True:
        q = sb.table(table).select(select)
        if filters:
            for method, *args in filters:
                q = getattr(q, method)(*args)
        if order:
            q = q.order(order)
        q = q.range(offset, offset + PAGE_SIZE - 1)
        rows = q.execute().data
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def is_morning(bar_ts_str: str) -> bool:
    """Check if bar_ts is in morning session (09:15-10:30 IST)."""
    try:
        dt = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
        dt_ist = dt.astimezone(IST)
        mins = dt_ist.hour * 60 + dt_ist.minute
        start = MORNING_START_H * 60 + MORNING_START_M
        end   = MORNING_END_H * 60 + MORNING_END_M
        return start <= mins <= end
    except Exception:
        return False


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 60)
    log("Experiment 17: BEAR_OB MORNING x Gamma Regime")
    log("=" * 60)

    # ── Step 1: Load all BEAR_OB zones from hist_ict_htf_zones ──────────
    log("\nStep 1: Loading BEAR_OB zones from hist_ict_htf_zones...")
    raw_zones = fetch_all(
        sb, "hist_ict_htf_zones",
        "as_of_date,symbol,pattern_type,zone_high,zone_low",
        filters=[("eq", "pattern_type", "BEAR_OB")],
        order="as_of_date"
    )
    log(f"  Loaded {len(raw_zones)} BEAR_OB zone rows")

    # Index by (date, symbol) -> list of zones
    zones_by_date = defaultdict(list)
    for z in raw_zones:
        key = (z["as_of_date"], z["symbol"])
        zones_by_date[key].append({
            "high": float(z["zone_high"]),
            "low":  float(z["zone_low"]),
        })

    log(f"  Unique date/symbol combos with BEAR_OB: {len(zones_by_date)}")

    # ── Step 2: Load hist_market_state ───────────────────────────────────
    log("\nStep 2: Loading hist_market_state...")
    mkt_rows = fetch_all(
        sb, "hist_market_state",
        "bar_ts,trade_date,symbol,spot,gamma_regime,ret_30m",
        order="bar_ts"
    )
    log(f"  Loaded {len(mkt_rows)} market state rows")

    # ── Step 3: Find BEAR_OB morning signals ─────────────────────────────
    log("\nStep 3: Finding BEAR_OB morning signals...")

    # Results bucketed by gamma_regime
    results = defaultdict(lambda: {"wins": 0, "losses": 0, "ret_sum": 0.0, "signals": []})

    signal_count = 0
    skipped_no_ret = 0

    for row in mkt_rows:
        bar_ts    = row.get("bar_ts", "")
        trade_date = row.get("trade_date", "")
        symbol    = row.get("symbol", "")
        spot      = row.get("spot")
        gamma     = row.get("gamma_regime", "UNKNOWN")
        ret_30m   = row.get("ret_30m")

        if not bar_ts or not spot or not trade_date:
            continue

        # Morning session only
        if not is_morning(bar_ts):
            continue

        # Check if any BEAR_OB zone for this date/symbol contains spot
        key = (trade_date, symbol)
        zones = zones_by_date.get(key, [])
        if not zones:
            continue

        in_zone = any(z["low"] <= float(spot) <= z["high"] for z in zones)
        if not in_zone:
            continue

        # We have a BEAR_OB morning signal
        signal_count += 1

        if ret_30m is None:
            skipped_no_ret += 1
            continue

        ret = float(ret_30m)

        # PE win = price fell (ret_30m < 0)
        win = ret < 0

        bucket = gamma or "UNKNOWN"
        results[bucket]["wins"]     += 1 if win else 0
        results[bucket]["losses"]   += 0 if win else 1
        results[bucket]["ret_sum"]  += ret
        results[bucket]["signals"].append({
            "date": trade_date, "symbol": symbol,
            "spot": spot, "ret_30m": ret, "win": win
        })

    log(f"  Total BEAR_OB morning signals: {signal_count}")
    log(f"  Skipped (no ret_30m): {skipped_no_ret}")

    # ── Step 4: Results ──────────────────────────────────────────────────
    log("\n" + "=" * 60)
    log("RESULTS: BEAR_OB MORNING Win Rate by Gamma Regime")
    log("=" * 60)
    log(f"  {'Regime':<20} {'N':>5} {'Wins':>5} {'WR':>8} {'Avg ret30m':>12}")
    log(f"  {'-'*55}")

    total_n = total_wins = 0
    regime_order = ["SHORT_GAMMA", "LONG_GAMMA", "NO_FLIP", "UNKNOWN"]

    for regime in regime_order + [r for r in results if r not in regime_order]:
        if regime not in results:
            continue
        b = results[regime]
        n    = b["wins"] + b["losses"]
        wins = b["wins"]
        wr   = wins / n * 100 if n > 0 else 0
        avg  = b["ret_sum"] / n if n > 0 else 0
        total_n    += n
        total_wins += wins
        log(f"  {regime:<20} {n:>5} {wins:>5} {wr:>7.1f}% {avg:>+11.3f}%")

    log(f"  {'-'*55}")
    overall_wr = total_wins / total_n * 100 if total_n > 0 else 0
    log(f"  {'TOTAL':<20} {total_n:>5} {total_wins:>5} {overall_wr:>7.1f}%")

    log("\n" + "=" * 60)
    log("VERDICT")
    log("=" * 60)

    lg = results.get("LONG_GAMMA", {})
    lg_n  = lg.get("wins", 0) + lg.get("losses", 0)
    lg_wr = lg.get("wins", 0) / lg_n * 100 if lg_n > 0 else 0

    sg = results.get("SHORT_GAMMA", {})
    sg_n  = sg.get("wins", 0) + sg.get("losses", 0)
    sg_wr = sg.get("wins", 0) / sg_n * 100 if sg_n > 0 else 0

    log(f"  SHORT_GAMMA BEAR_OB MORNING: {sg_wr:.1f}% WR (N={sg_n})")
    log(f"  LONG_GAMMA  BEAR_OB MORNING: {lg_wr:.1f}% WR (N={lg_n})")
    log("")

    if lg_n < 5:
        log("  INCONCLUSIVE: Too few LONG_GAMMA BEAR_OB MORNING signals (N<5)")
        log("  Cannot validate override rule. More live data needed.")
    elif lg_wr >= 75:
        log(f"  STRONG EDGE CONFIRMED: {lg_wr:.1f}% WR under LONG_GAMMA")
        log("  -> RECOMMENDATION: Build override rule for BEAR_OB TIER1 MORNING")
        log("     even when gamma_regime = LONG_GAMMA")
    elif lg_wr >= 60:
        log(f"  MODERATE EDGE: {lg_wr:.1f}% WR under LONG_GAMMA")
        log("  -> RECOMMENDATION: Shadow test override before live implementation")
    else:
        log(f"  WEAK/NO EDGE: {lg_wr:.1f}% WR under LONG_GAMMA")
        log("  -> RECOMMENDATION: Keep LONG_GAMMA gate. Regime override not justified.")

    log("")
    log("Experiment 17 complete.")


if __name__ == "__main__":
    main()
