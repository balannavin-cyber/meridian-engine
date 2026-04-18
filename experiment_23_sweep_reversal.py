#!/usr/bin/env python3
"""
experiment_23_sweep_reversal.py
=================================
Experiment 23: Liquidity Sweep Reversal Edge

Question:
  When price sweeps below a key HTF level (PDL/PDH) in the morning session
  and then closes back above it within 1-3 bars, what is the reversal
  win rate and expectancy?

  Today's example (2026-04-17 NIFTY):
    - PDL was 24,136-24,156
    - Price swept to 24,146 (below PDL)
    - Rejected off W PDH zone 24,054-24,094
    - Closed back above PDL → BUY_CE entry
    - Delivered +25% in 30 min

Setup definition:
  1. In MORNING session (09:15-10:30 IST)
  2. Price closes BELOW D PDL (or above D PDH) — the sweep bar
  3. Within 1-3 bars, price closes back ABOVE D PDL (or below D PDH)
  4. Signal bar = the close-back bar
  5. Outcome = ret_30m from signal bar

Secondary questions:
  - Does gamma_regime matter for sweep reversals?
  - Does the depth of sweep matter?
  - Is W PDH/PDL confluence at the sweep level stronger?

Data:
  hist_spot_bars_1m    — 1-min bars for precise sweep detection
  hist_ict_htf_zones   — PDL/PDH levels per date
  hist_market_state    — regime context + ret_30m outcome
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
PAGE_SIZE    = 1000

INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

# Sweep must go AT LEAST this far below/above the level
MIN_SWEEP_PCT = 0.0003   # 0.03% — ~7 NIFTY points minimum

# Close-back must happen within this many bars
MAX_BARS_TO_RETURN = 5


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
                    log(f"  ERROR: {e}")
                    return all_rows
                time.sleep(2 ** attempt)
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def get_mins(bar_ts_str):
    """Return minutes since midnight — bar_ts stored as IST with +00:00."""
    try:
        dt = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
        return dt.hour * 60 + dt.minute
    except:
        return 0


def is_morning(bar_ts_str):
    mins = get_mins(bar_ts_str)
    return (9*60+15) <= mins <= (10*60+30)


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("Experiment 23: Liquidity Sweep Reversal Edge")
    log("=" * 65)

    # ── Step 1: Load PDL/PDH levels ─────────────────────────────────────
    log("\nStep 1: Loading PDL/PDH levels from hist_ict_htf_zones...")
    raw_zones = fetch_all(
        sb, "hist_ict_htf_zones",
        "as_of_date,symbol,pattern_type,zone_high,zone_low,timeframe",
        filters=[("in_", "pattern_type", ["PDL","PDH"])],
        order="as_of_date"
    )
    log(f"  {len(raw_zones)} PDL/PDH rows")

    levels = defaultdict(dict)  # (date, symbol) -> {pdl, pdh, pdl_tf, pdh_tf}
    for z in raw_zones:
        key = (z["as_of_date"], z["symbol"])
        if z["pattern_type"] == "PDL":
            # Keep nearest D PDL (prefer D over W)
            if "pdl" not in levels[key] or z["timeframe"] == "D":
                levels[key]["pdl"]    = float(z["zone_low"])
                levels[key]["pdl_tf"] = z["timeframe"]
        elif z["pattern_type"] == "PDH":
            if "pdh" not in levels[key] or z["timeframe"] == "D":
                levels[key]["pdh"]    = float(z["zone_high"])
                levels[key]["pdh_tf"] = z["timeframe"]

    log(f"  {len(levels)} date/symbol pairs with PDL/PDH")

    # ── Step 2: Load market state for regime context ─────────────────────
    log("\nStep 2: Loading hist_market_state for regime context...")
    mkt_rows = fetch_all(
        sb, "hist_market_state",
        "bar_ts,trade_date,symbol,spot,gamma_regime,breadth_regime,"
        "iv_regime,ret_session,ret_30m",
        order="bar_ts"
    )
    log(f"  {len(mkt_rows)} market state rows")

    # Index market state by (date, symbol, bar_ts_mins) for fast lookup
    mkt_idx = {}
    for r in mkt_rows:
        key = (r["trade_date"], r["symbol"], get_mins(r["bar_ts"]))
        mkt_idx[key] = r

    mkt_by_date = defaultdict(list)
    for r in mkt_rows:
        mkt_by_date[(r["trade_date"], r["symbol"])].append(r)

    # ── Step 3: Load 1-min spot bars ─────────────────────────────────────
    log("\nStep 3: Loading 1-min spot bars...")
    spot_by = defaultdict(list)
    for symbol, inst_id in INSTRUMENTS.items():
        rows = fetch_all(
            sb, "hist_spot_bars_1m",
            "trade_date,bar_ts,open,high,low,close",
            filters=[("eq","instrument_id",inst_id),
                     ("eq","is_pre_market",False)],
            order="bar_ts"
        )
        for r in rows:
            spot_by[(r["trade_date"], symbol)].append(r)
        log(f"  {symbol}: {len(rows)} bars")

    # ── Step 4: Detect sweep reversals ───────────────────────────────────
    log("\nStep 4: Detecting sweep reversals...")

    signals = []
    dates_processed = 0

    for (trade_date, symbol), bars in sorted(spot_by.items()):
        # Morning bars only, sorted by time
        morning_bars = [b for b in bars if is_morning(b["bar_ts"])]
        if not morning_bars:
            continue

        lvl = levels.get((trade_date, symbol), {})
        pdl = lvl.get("pdl")
        pdh = lvl.get("pdh")
        dates_processed += 1

        # ── Bull sweep reversal: sweep below PDL, close back above ───────
        if pdl:
            swept = False
            sweep_low = None
            for i, bar in enumerate(morning_bars):
                low   = float(bar["low"])
                close = float(bar["close"])

                # Detect sweep: bar closes BELOW pdl
                if not swept and close < pdl * (1 - MIN_SWEEP_PCT):
                    swept     = True
                    sweep_low = low
                    sweep_bar = i
                    continue

                # After sweep: look for close back above PDL
                if swept and close > pdl:
                    bars_to_return = i - sweep_bar
                    if bars_to_return <= MAX_BARS_TO_RETURN:
                        # Signal bar found — get regime context
                        bar_ts = bar["bar_ts"]
                        mins   = get_mins(bar_ts)
                        mkt    = mkt_idx.get((trade_date, symbol, mins))
                        if not mkt:
                            # Try nearby minute
                            for dm in [-1, 1, -2, 2]:
                                mkt = mkt_idx.get((trade_date, symbol, mins+dm))
                                if mkt:
                                    break

                        sweep_depth_pct = (pdl - sweep_low) / pdl * 100

                        signals.append({
                            "type":          "BULL_SWEEP",
                            "trade_date":    trade_date,
                            "symbol":        symbol,
                            "bar_ts":        bar_ts,
                            "pdl":           pdl,
                            "sweep_low":     sweep_low,
                            "sweep_depth_pct": sweep_depth_pct,
                            "bars_to_return": bars_to_return,
                            "close_back":    close,
                            "gamma_regime":  mkt.get("gamma_regime") if mkt else None,
                            "breadth_regime": mkt.get("breadth_regime") if mkt else None,
                            "iv_regime":     mkt.get("iv_regime") if mkt else None,
                            "ret_30m":       float(mkt["ret_30m"]) if mkt and mkt.get("ret_30m") else None,
                            "win_30m":       float(mkt["ret_30m"]) > 0 if mkt and mkt.get("ret_30m") else None,
                        })
                    swept = False  # Reset

        # ── Bear sweep reversal: sweep above PDH, close back below ───────
        if pdh:
            swept = False
            sweep_high = None
            for i, bar in enumerate(morning_bars):
                high  = float(bar["high"])
                close = float(bar["close"])

                if not swept and close > pdh * (1 + MIN_SWEEP_PCT):
                    swept      = True
                    sweep_high = high
                    sweep_bar  = i
                    continue

                if swept and close < pdh:
                    bars_to_return = i - sweep_bar
                    if bars_to_return <= MAX_BARS_TO_RETURN:
                        bar_ts = bar["bar_ts"]
                        mins   = get_mins(bar_ts)
                        mkt    = mkt_idx.get((trade_date, symbol, mins))
                        if not mkt:
                            for dm in [-1,1,-2,2]:
                                mkt = mkt_idx.get((trade_date, symbol, mins+dm))
                                if mkt: break

                        sweep_depth_pct = (sweep_high - pdh) / pdh * 100
                        signals.append({
                            "type":          "BEAR_SWEEP",
                            "trade_date":    trade_date,
                            "symbol":        symbol,
                            "bar_ts":        bar_ts,
                            "pdh":           pdh,
                            "sweep_high":    sweep_high,
                            "sweep_depth_pct": sweep_depth_pct,
                            "bars_to_return": bars_to_return,
                            "close_back":    close,
                            "gamma_regime":  mkt.get("gamma_regime") if mkt else None,
                            "breadth_regime": mkt.get("breadth_regime") if mkt else None,
                            "iv_regime":     mkt.get("iv_regime") if mkt else None,
                            "ret_30m":       float(mkt["ret_30m"]) if mkt and mkt.get("ret_30m") else None,
                            "win_30m":       float(mkt["ret_30m"]) < 0 if mkt and mkt.get("ret_30m") else None,
                        })
                    swept = False

    log(f"  Dates processed: {dates_processed}")
    log(f"  Bull sweep reversals: {sum(1 for s in signals if s['type']=='BULL_SWEEP')}")
    log(f"  Bear sweep reversals: {sum(1 for s in signals if s['type']=='BEAR_SWEEP')}")
    log(f"  Total: {len(signals)}")

    # ── Step 5: Results ──────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("RESULTS")
    log("=" * 65)

    def analyse_group(group, label):
        with_ret = [s for s in group if s["win_30m"] is not None]
        if not with_ret:
            log(f"\n  {label}: NO DATA")
            return

        wins = sum(1 for s in with_ret if s["win_30m"])
        n    = len(with_ret)
        wr   = wins / n * 100
        avg  = sum(s["ret_30m"] for s in with_ret) / n

        log(f"\n  {label} (N={n}):")
        log(f"    Win rate:    {wr:.1f}%")
        log(f"    Avg ret30m:  {avg:+.3f}%")
        log(f"    Avg sweep depth: {sum(s['sweep_depth_pct'] for s in group)/len(group):.3f}%")
        log(f"    Avg bars to return: {sum(s['bars_to_return'] for s in group)/len(group):.1f}")

        # By gamma
        by_gamma = defaultdict(lambda: {"w":0,"n":0})
        for s in with_ret:
            g = s.get("gamma_regime","UNKNOWN")
            by_gamma[g]["w"] += s["win_30m"]
            by_gamma[g]["n"] += 1
        log(f"    By gamma:")
        for g in ["SHORT_GAMMA","LONG_GAMMA","NO_FLIP"]:
            b = by_gamma.get(g, {"w":0,"n":0})
            if b["n"] == 0: continue
            log(f"      {g:<15}: {b['w']/b['n']*100:.1f}% WR (N={b['n']})")

        # By breadth
        by_breadth = defaultdict(lambda: {"w":0,"n":0})
        for s in with_ret:
            br = s.get("breadth_regime","UNKNOWN")
            by_breadth[br]["w"] += s["win_30m"]
            by_breadth[br]["n"] += 1
        log(f"    By breadth:")
        for br in ["BULLISH","BEARISH","NEUTRAL","TRANSITION"]:
            b = by_breadth.get(br, {"w":0,"n":0})
            if b["n"] == 0: continue
            log(f"      {br:<12}: {b['w']/b['n']*100:.1f}% WR (N={b['n']})")

        # By bars to return
        by_speed = defaultdict(lambda: {"w":0,"n":0})
        for s in with_ret:
            by_speed[s["bars_to_return"]]["w"] += s["win_30m"]
            by_speed[s["bars_to_return"]]["n"] += 1
        log(f"    By bars to return (speed of reversal):")
        for spd in sorted(by_speed.keys()):
            b = by_speed[spd]
            log(f"      {spd} bar(s): {b['w']/b['n']*100:.1f}% WR (N={b['n']})")

        return wr, n

    bull_signals = [s for s in signals if s["type"] == "BULL_SWEEP"]
    bear_signals = [s for s in signals if s["type"] == "BEAR_SWEEP"]

    bull_result = analyse_group(bull_signals, "BULL SWEEP REVERSAL (BUY_CE)")
    bear_result = analyse_group(bear_signals, "BEAR SWEEP REVERSAL (BUY_PE)")

    # ── Verdict ──────────────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("VERDICT")
    log("=" * 65)

    if not signals:
        log("\n  ZERO sweeps detected — check PDL/PDH levels or MIN_SWEEP_PCT")
        log("  Try reducing MIN_SWEEP_PCT from 0.0003 to 0.0001")
    else:
        bull_wr = bull_result[0] if bull_result else 0
        bull_n  = bull_result[1] if bull_result else 0
        bear_wr = bear_result[0] if bear_result else 0
        bear_n  = bear_result[1] if bear_result else 0

        log(f"\n  BULL SWEEP: {bull_wr:.1f}% WR (N={bull_n})")
        log(f"  BEAR SWEEP: {bear_wr:.1f}% WR (N={bear_n})")
        log("")

        if bull_wr >= 75 and bull_n >= 10:
            log(f"  STRONG EDGE: Bull sweep reversal {bull_wr:.1f}% WR")
            log(f"  -> BUILD ENH-54: Sweep Reversal detector")
            log(f"     Signal: Morning PDL sweep + close back above = BUY_CE")
            log(f"     This explains today's NIFTY trade (+25%)")
        elif bull_wr >= 65 and bull_n >= 10:
            log(f"  MODERATE EDGE: Shadow test before live deployment")
        else:
            log(f"  INSUFFICIENT EDGE or DATA")

    log("\nExperiment 23 complete.")


if __name__ == "__main__":
    main()
