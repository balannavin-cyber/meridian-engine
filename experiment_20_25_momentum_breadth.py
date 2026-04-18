#!/usr/bin/env python3
"""
experiment_20_25_momentum_breadth.py
======================================
Experiment 20: Momentum direction alignment
  Does ret_session direction matching ICT pattern direction lift WR?

Experiment 25: Breadth independence
  Is breadth_regime orthogonal to ICT edge, or does it add lift?

Both run against hist_pattern_signals — completes in <60 seconds.
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


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fetch_all(sb, table, select, filters=None):
    all_rows, offset = [], 0
    while True:
        q = sb.table(table).select(select)
        if filters:
            for f in filters:
                method, *args = f
                q = getattr(q, method)(*args)
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


def wr(wins, n):
    return wins / n * 100 if n > 0 else 0


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("Experiments 20 + 25: Momentum Alignment & Breadth Independence")
    log("=" * 65)

    log("\nLoading hist_pattern_signals...")
    rows = fetch_all(
        sb, "hist_pattern_signals",
        "pattern_type,direction,session,gamma_regime,breadth_regime,"
        "ret_session,win_30m,ret_30m,zone_timeframe"
    )
    log(f"  {len(rows)} signals")

    # Filter to signals with outcomes
    valid = [r for r in rows if r.get("win_30m") is not None]
    log(f"  {len(valid)} with win_30m outcome")

    # ════════════════════════════════════════════════════════════════════
    # EXPERIMENT 20: Momentum alignment
    # ════════════════════════════════════════════════════════════════════
    log("\n" + "=" * 65)
    log("EXPERIMENT 20: Momentum Direction Alignment")
    log("=" * 65)
    log("""
  Hypothesis: When ret_session direction aligns with ICT pattern direction,
  WR should be higher than when momentum is opposed or neutral.

  Aligned:
    BUY_PE (BEAR_OB) + ret_session < 0 (price already falling) = aligned
    BUY_CE (BULL_OB) + ret_session > 0 (price already rising)  = aligned

  Opposed:
    BUY_PE + ret_session > 0 = momentum against signal
    BUY_CE + ret_session < 0 = momentum against signal
""")

    aligned_wins = aligned_n = 0
    opposed_wins = opposed_n = 0
    neutral_wins = neutral_n = 0

    # By pattern type
    by_pattern_align = defaultdict(lambda: {
        "aligned": {"w":0,"n":0},
        "opposed": {"w":0,"n":0},
        "neutral": {"w":0,"n":0},
    })

    for r in valid:
        direction = r.get("direction")
        ret_sess  = r.get("ret_session")
        win       = bool(r["win_30m"])
        pattern   = r.get("pattern_type","?")

        if ret_sess is None:
            continue

        ret_sess = float(ret_sess)

        if abs(ret_sess) < 0.05:  # < 0.05% = neutral momentum
            neutral_wins += win
            neutral_n    += 1
            by_pattern_align[pattern]["neutral"]["w"] += win
            by_pattern_align[pattern]["neutral"]["n"] += 1
        elif (direction == "BUY_PE" and ret_sess < 0) or \
             (direction == "BUY_CE" and ret_sess > 0):
            aligned_wins += win
            aligned_n    += 1
            by_pattern_align[pattern]["aligned"]["w"] += win
            by_pattern_align[pattern]["aligned"]["n"] += 1
        else:
            opposed_wins += win
            opposed_n    += 1
            by_pattern_align[pattern]["opposed"]["w"] += win
            by_pattern_align[pattern]["opposed"]["n"] += 1

    log(f"  {'Momentum':<20} {'N':>5} {'WR':>8}")
    log(f"  {'-'*35}")
    log(f"  {'ALIGNED':<20} {aligned_n:>5} {wr(aligned_wins,aligned_n):>7.1f}%")
    log(f"  {'OPPOSED':<20} {opposed_n:>5} {wr(opposed_wins,opposed_n):>7.1f}%")
    log(f"  {'NEUTRAL':<20} {neutral_n:>5} {wr(neutral_wins,neutral_n):>7.1f}%")

    log(f"\n  By pattern:")
    for pattern in ["BEAR_OB","BULL_OB","BULL_FVG"]:
        b = by_pattern_align.get(pattern)
        if not b: continue
        al = b["aligned"]
        op = b["opposed"]
        log(f"  {pattern}:")
        log(f"    Aligned: {wr(al['w'],al['n']):.1f}% (N={al['n']})  "
            f"Opposed: {wr(op['w'],op['n']):.1f}% (N={op['n']})")

    lift_20 = wr(aligned_wins,aligned_n) - wr(opposed_wins,opposed_n)
    log(f"\n  Momentum alignment lift: {lift_20:+.1f}pp")
    if lift_20 >= 10:
        log(f"  -> STRONG: Add momentum alignment filter to signal engine")
        log(f"     Block signals where ret_session opposes pattern direction")
    elif lift_20 >= 5:
        log(f"  -> MODERATE: Consider as confidence modifier (+/- points)")
    else:
        log(f"  -> WEAK: Momentum alignment adds minimal edge")

    # ════════════════════════════════════════════════════════════════════
    # EXPERIMENT 25: Breadth independence
    # ════════════════════════════════════════════════════════════════════
    log("\n" + "=" * 65)
    log("EXPERIMENT 25: Breadth Regime Independence")
    log("=" * 65)
    log("""
  Hypothesis: MERDIAN gates signals on BEARISH breadth (allows) and
  BULLISH breadth. Does breadth regime actually predict ICT signal success?

  If breadth is INDEPENDENT of ICT edge:
    WR should be similar across BULLISH/BEARISH/NEUTRAL breadth
    -> Breadth gate is wrong (blocking valid BUY_CE on BULLISH days)
    -> Today: BULLISH breadth, valid BULL_OB, blocked

  If breadth PREDICTS ICT edge:
    WR should differ significantly across regimes
    -> Keep breadth gate
""")

    by_breadth = defaultdict(lambda: {"w":0,"n":0,"ret":0.0})
    by_breadth_pattern = defaultdict(lambda: defaultdict(lambda: {"w":0,"n":0}))

    for r in valid:
        breadth = r.get("breadth_regime","UNKNOWN")
        win     = bool(r["win_30m"])
        pattern = r.get("pattern_type","?")
        ret     = float(r.get("ret_30m") or 0)

        by_breadth[breadth]["w"]   += win
        by_breadth[breadth]["n"]   += 1
        by_breadth[breadth]["ret"] += ret
        by_breadth_pattern[pattern][breadth]["w"] += win
        by_breadth_pattern[pattern][breadth]["n"] += 1

    log(f"  {'Breadth':<15} {'N':>5} {'WR':>8} {'Avg ret':>10}")
    log(f"  {'-'*42}")
    for regime in ["BULLISH","BEARISH","NEUTRAL","TRANSITION"]:
        b = by_breadth.get(regime, {"w":0,"n":0,"ret":0})
        if b["n"] == 0: continue
        avg = b["ret"] / b["n"]
        log(f"  {regime:<15} {b['n']:>5} {wr(b['w'],b['n']):>7.1f}% {avg:>+9.3f}%")

    log(f"\n  By pattern + breadth:")
    for pattern in ["BEAR_OB","BULL_OB","BULL_FVG"]:
        bp = by_breadth_pattern.get(pattern,{})
        if not bp: continue
        log(f"  {pattern}:")
        for regime in ["BULLISH","BEARISH","NEUTRAL"]:
            b = bp.get(regime,{"w":0,"n":0})
            if b["n"] == 0: continue
            log(f"    {regime:<12}: {wr(b['w'],b['n']):.1f}% WR (N={b['n']})")

    # Check max spread across breadth regimes
    wrs = [wr(by_breadth[r]["w"], by_breadth[r]["n"])
           for r in ["BULLISH","BEARISH","NEUTRAL"]
           if by_breadth.get(r,{}).get("n",0) >= 10]
    spread = max(wrs) - min(wrs) if len(wrs) >= 2 else 0

    log(f"\n  WR spread across breadth regimes: {spread:.1f}pp")

    if spread >= 15:
        log(f"  -> BREADTH MATTERS: Keep breadth gate")
        log(f"     WR varies {spread:.1f}pp across regimes — signal has directional bias")
    elif spread >= 8:
        log(f"  -> MODERATE: Breadth adds some predictive value")
        log(f"     Consider as confidence modifier, not hard gate")
    else:
        log(f"  -> BREADTH IS INDEPENDENT: {spread:.1f}pp spread is noise")
        log(f"     Breadth gate is blocking valid trades for no edge")
        log(f"     -> RECOMMEND: Remove breadth as hard gate")
        log(f"        Keep as confidence modifier (+/- 5 points)")
        log(f"        Today's blocked BUY_CE on BULLISH breadth was unjustified")

    # ── Combined synthesis ───────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("COMBINED SYNTHESIS")
    log("=" * 65)
    log(f"""
  Experiment 20 — Momentum alignment lift:   {lift_20:+.1f}pp
  Experiment 25 — Breadth WR spread:         {spread:.1f}pp

  Current signal engine gates:
    LONG_GAMMA     → BLOCK (Exp 17/19 confirmed correct)
    BEARISH breadth → ALLOW BUY_PE (Exp 25 needed to validate)
    BULLISH breadth → BLOCK BUY_PE (Exp 25 needed to validate)
    Momentum        → confidence modifier (validate with Exp 20)
""")

    log("Experiments 20 + 25 complete.")


if __name__ == "__main__":
    main()
