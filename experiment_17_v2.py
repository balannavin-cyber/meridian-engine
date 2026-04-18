#!/usr/bin/env python3
"""
experiment_17_bear_ob_gamma_override.py  (v2 — fixed timestamp handling)
=========================================
Experiment 17: Does BEAR_OB MORNING edge hold under LONG_GAMMA regime?

Fix: hist_market_state bar_ts is stored as IST time with +00:00 suffix
(incorrect UTC label). Use hour directly without timezone conversion.

Morning session: 09:15-10:30 IST = bar_ts hour 9 or (hour==10 and minute<=30)
"""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

PAGE_SIZE = 1000


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
        rows = q.execute().data
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def is_morning(bar_ts_str: str) -> bool:
    """
    Check if bar is in morning session 09:15-10:30 IST.
    NOTE: hist_market_state stores IST times with +00:00 suffix (incorrect UTC label).
    Use hour/minute directly without timezone conversion.
    """
    try:
        # Parse and use naive time directly — it's already IST
        dt = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
        h, m = dt.hour, dt.minute
        # 09:15 to 10:30 IST
        mins = h * 60 + m
        return (9 * 60 + 15) <= mins <= (10 * 60 + 30)
    except Exception:
        return False


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 60)
    log("Experiment 17: BEAR_OB MORNING x Gamma Regime (v2)")
    log("=" * 60)

    # ── Step 1: Load BEAR_OB zones ───────────────────────────────────────
    log("\nStep 1: Loading BEAR_OB zones from hist_ict_htf_zones...")
    raw_zones = fetch_all(
        sb, "hist_ict_htf_zones",
        "as_of_date,symbol,pattern_type,zone_high,zone_low",
        filters=[("eq", "pattern_type", "BEAR_OB")],
        order="as_of_date"
    )
    log(f"  Loaded {len(raw_zones)} BEAR_OB zone rows")

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

    # Quick sanity check on timestamps
    morning_count = sum(1 for r in mkt_rows[:500] if is_morning(r.get("bar_ts","")))
    log(f"  Morning bars in first 500: {morning_count} (sanity check)")

    # ── Step 3: Find BEAR_OB morning signals ─────────────────────────────
    log("\nStep 3: Finding BEAR_OB morning signals...")

    results = defaultdict(lambda: {"wins": 0, "losses": 0, "ret_sum": 0.0, "rets": []})
    signal_count = 0
    skipped_no_ret = 0
    skipped_no_zone = 0

    for row in mkt_rows:
        bar_ts     = row.get("bar_ts", "")
        trade_date = row.get("trade_date", "")
        symbol     = row.get("symbol", "")
        spot       = row.get("spot")
        gamma      = row.get("gamma_regime", "UNKNOWN")
        ret_30m    = row.get("ret_30m")

        if not bar_ts or not spot or not trade_date:
            continue

        if not is_morning(bar_ts):
            continue

        # Check if any BEAR_OB zone contains this spot price
        key = (trade_date, symbol)
        zones = zones_by_date.get(key, [])
        if not zones:
            skipped_no_zone += 1
            continue

        in_zone = any(z["low"] <= float(spot) <= z["high"] for z in zones)
        if not in_zone:
            continue

        signal_count += 1

        if ret_30m is None:
            skipped_no_ret += 1
            continue

        ret = float(ret_30m)
        win = ret < 0  # PE win = price fell

        bucket = gamma or "UNKNOWN"
        results[bucket]["wins"]    += 1 if win else 0
        results[bucket]["losses"]  += 0 if win else 1
        results[bucket]["ret_sum"] += ret
        results[bucket]["rets"].append(ret)

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
    log(f"  OVERALL     BEAR_OB MORNING: {overall_wr:.1f}% WR (N={total_n})")
    log("")

    if total_n == 0:
        log("  ZERO SIGNALS — check zone/spot matching and date overlap")
    elif lg_n < 5:
        log("  INCONCLUSIVE: Too few LONG_GAMMA signals (N<5)")
        log("  Cannot validate override rule with statistical confidence.")
    elif lg_wr >= 75:
        log(f"  STRONG EDGE: {lg_wr:.1f}% WR under LONG_GAMMA (N={lg_n})")
        log("  -> RECOMMEND: Build ENH-55 override for BEAR_OB TIER1 MORNING")
        log("     Override LONG_GAMMA gate when pattern = BEAR_OB + morning + MTF HIGH")
    elif lg_wr >= 60:
        log(f"  MODERATE EDGE: {lg_wr:.1f}% WR under LONG_GAMMA (N={lg_n})")
        log("  -> RECOMMEND: Shadow test override for 2 weeks before live")
    else:
        log(f"  WEAK/NO EDGE: {lg_wr:.1f}% WR under LONG_GAMMA (N={lg_n})")
        log("  -> KEEP: LONG_GAMMA gate is justified. Do not override.")

    log("")
    log("Experiment 17 complete.")


if __name__ == "__main__":
    main()
