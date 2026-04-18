#!/usr/bin/env python3
"""
experiment_19_gamma_asymmetry.py
==================================
Experiment 19: LONG_GAMMA asymmetry — BULL_OB vs BEAR_OB

Question:
  MERDIAN blocks ALL signals under LONG_GAMMA (SE-02).
  Experiment 17 confirmed LONG_GAMMA correctly blocks BEAR_OB (54.6% WR — coin flip).
  Today's trade (BULL_OB morning, LONG_GAMMA, +25%) suggests the gate is wrong
  for BUY_CE signals.

  Hypothesis:
    LONG_GAMMA → dealers hedge by buying dips → BULL_OB edge INCREASES
    LONG_GAMMA → dealers hedge by selling rips → BEAR_OB edge DECREASES

  Decision gate:
    If BULL_OB WR under LONG_GAMMA >= 70% → build asymmetric gate:
      Block BUY_PE under LONG_GAMMA (keep current)
      Allow BUY_CE under LONG_GAMMA (new rule)

    If BEAR_OB WR under LONG_GAMMA < 60% → confirm current gate is correct

Tables:
  hist_pattern_signals (built by build_hist_pattern_signals.py)
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
PAGE_SIZE = 1000


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


def wr(wins, total):
    return wins / total * 100 if total > 0 else 0


def analyse(rows, label):
    """Print win rate breakdown by gamma_regime and session."""
    log(f"\n{'─'*60}")
    log(f"{label}")
    log(f"{'─'*60}")

    by_gamma   = defaultdict(lambda: {"w": 0, "n": 0, "ret": 0.0})
    by_session = defaultdict(lambda: {"w": 0, "n": 0})
    by_tf      = defaultdict(lambda: {"w": 0, "n": 0})
    total_w = total_n = 0

    for r in rows:
        w30  = r.get("win_30m")
        gam  = r.get("gamma_regime", "UNKNOWN")
        sess = r.get("session", "UNKNOWN")
        tf   = r.get("zone_timeframe", "?")
        ret  = r.get("ret_30m")

        if w30 is None:
            continue

        win = bool(w30)
        total_w += win
        total_n += 1
        by_gamma[gam]["w"]   += win
        by_gamma[gam]["n"]   += 1
        by_gamma[gam]["ret"] += float(ret) if ret else 0
        by_session[sess]["w"] += win
        by_session[sess]["n"] += 1
        by_tf[tf]["w"] += win
        by_tf[tf]["n"] += 1

    log(f"  OVERALL: {wr(total_w,total_n):.1f}% WR (N={total_n})")

    log(f"\n  By gamma regime:")
    for regime in ["SHORT_GAMMA","LONG_GAMMA","NO_FLIP"]:
        b = by_gamma.get(regime, {"w":0,"n":0,"ret":0})
        if b["n"] == 0: continue
        avg = b["ret"] / b["n"]
        log(f"    {regime:<15}: {wr(b['w'],b['n']):.1f}% WR  "
            f"avg ret30m {avg:+.3f}%  (N={b['n']})")

    log(f"\n  By session:")
    for sess in ["MORNING","MIDDAY","AFTERNOON","PRECLOSE"]:
        b = by_session.get(sess, {"w":0,"n":0})
        if b["n"] == 0: continue
        log(f"    {sess:<12}: {wr(b['w'],b['n']):.1f}% WR (N={b['n']})")

    log(f"\n  By timeframe:")
    for tf in ["W","D"]:
        b = by_tf.get(tf, {"w":0,"n":0})
        if b["n"] == 0: continue
        log(f"    {tf}: {wr(b['w'],b['n']):.1f}% WR (N={b['n']})")

    return by_gamma, total_w, total_n


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("Experiment 19: LONG_GAMMA Asymmetry — BULL_OB vs BEAR_OB")
    log("=" * 65)

    # Load all signals from hist_pattern_signals
    log("\nLoading hist_pattern_signals...")
    rows = fetch_all(
        sb, "hist_pattern_signals",
        "pattern_type,direction,session,zone_timeframe,"
        "gamma_regime,breadth_regime,iv_regime,"
        "ret_session,ret_30m,win_30m,win_60m,trade_date,symbol"
    )
    log(f"  {len(rows)} total signals")

    # Split by direction
    bear_ob  = [r for r in rows if r["pattern_type"] == "BEAR_OB"]
    bull_ob  = [r for r in rows if r["pattern_type"] == "BULL_OB"]
    bear_fvg = [r for r in rows if r["pattern_type"] == "BEAR_FVG"]
    bull_fvg = [r for r in rows if r["pattern_type"] == "BULL_FVG"]

    log(f"  BEAR_OB: {len(bear_ob)} | BULL_OB: {len(bull_ob)}")
    log(f"  BEAR_FVG: {len(bear_fvg)} | BULL_FVG: {len(bull_fvg)}")

    # Analyse each pattern
    bear_ob_gamma,  _, _ = analyse(bear_ob,  "BEAR_OB — Sell signals (BUY_PE)")
    bull_ob_gamma,  _, _ = analyse(bull_ob,  "BULL_OB — Buy signals (BUY_CE)")
    bear_fvg_gamma, _, _ = analyse(bear_fvg, "BEAR_FVG — Sell signals (BUY_PE)")
    bull_fvg_gamma, _, _ = analyse(bull_fvg, "BULL_FVG — Buy signals (BUY_CE)")

    # ── SYNTHESIS ────────────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("SYNTHESIS: LONG_GAMMA Asymmetry")
    log("=" * 65)

    for label, pattern_gamma, signal_type in [
        ("BEAR_OB (current gate blocks this)", bear_ob_gamma, "BUY_PE"),
        ("BULL_OB (current gate also blocks this)", bull_ob_gamma, "BUY_CE"),
        ("BEAR_FVG", bear_fvg_gamma, "BUY_PE"),
        ("BULL_FVG", bull_fvg_gamma, "BUY_CE"),
    ]:
        lg = pattern_gamma.get("LONG_GAMMA", {"w":0,"n":0})
        sg = pattern_gamma.get("SHORT_GAMMA", {"w":0,"n":0})
        nf = pattern_gamma.get("NO_FLIP", {"w":0,"n":0})
        lg_wr = wr(lg["w"], lg["n"])
        sg_wr = wr(sg["w"], sg["n"])
        nf_wr = wr(nf["w"], nf["n"])
        log(f"\n  {label}:")
        log(f"    SHORT_GAMMA: {sg_wr:.1f}% (N={sg['n']})")
        log(f"    LONG_GAMMA:  {lg_wr:.1f}% (N={lg['n']})")
        log(f"    NO_FLIP:     {nf_wr:.1f}% (N={nf['n']})")

    # Decision
    log("\n" + "=" * 65)
    log("VERDICT")
    log("=" * 65)

    bo_lg = bull_ob_gamma.get("LONG_GAMMA", {"w":0,"n":0})
    bo_lg_wr = wr(bo_lg["w"], bo_lg["n"])

    bear_lg = bear_ob_gamma.get("LONG_GAMMA", {"w":0,"n":0})
    bear_lg_wr = wr(bear_lg["w"], bear_lg["n"])

    log(f"\n  BEAR_OB under LONG_GAMMA: {bear_lg_wr:.1f}% WR (N={bear_lg['n']})")
    log(f"  BULL_OB under LONG_GAMMA: {bo_lg_wr:.1f}% WR (N={bo_lg['n']})")
    log("")

    if bo_lg["n"] < 5:
        log("  INCONCLUSIVE: Too few BULL_OB LONG_GAMMA signals")
    elif bo_lg_wr >= 70 and bear_lg_wr < 60:
        log(f"  ASYMMETRY CONFIRMED:")
        log(f"    BULL_OB LONG_GAMMA = {bo_lg_wr:.1f}% WR -> ALLOW BUY_CE")
        log(f"    BEAR_OB LONG_GAMMA = {bear_lg_wr:.1f}% WR -> KEEP BLOCKING BUY_PE")
        log(f"  -> BUILD: Asymmetric LONG_GAMMA gate in signal engine")
        log(f"     if gamma_regime == LONG_GAMMA and direction == BUY_PE: block")
        log(f"     if gamma_regime == LONG_GAMMA and direction == BUY_CE: allow")
    elif bo_lg_wr >= 70:
        log(f"  PARTIAL ASYMMETRY:")
        log(f"    BULL_OB LONG_GAMMA = {bo_lg_wr:.1f}% -> consider allowing BUY_CE")
        log(f"    BEAR_OB LONG_GAMMA = {bear_lg_wr:.1f}% -> borderline on blocking")
        log(f"  -> SHADOW TEST asymmetric gate before live deployment")
    elif bo_lg_wr >= 60:
        log(f"  WEAK ASYMMETRY: {bo_lg_wr:.1f}% BULL_OB — not sufficient for rule change")
        log(f"  -> KEEP current symmetric LONG_GAMMA block")
    else:
        log(f"  NO ASYMMETRY: BULL_OB also weak under LONG_GAMMA ({bo_lg_wr:.1f}%)")
        log(f"  -> KEEP current gate. Today's trade was an outlier.")

    log("\nExperiment 19 complete.")


if __name__ == "__main__":
    main()
