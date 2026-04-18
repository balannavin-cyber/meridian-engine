#!/usr/bin/env python3
"""
experiment_26_option_wick_reversal.py
=======================================
Experiment 26: Option Premium Wick as Reversal Signal

Hypothesis (from live observation 2026-04-17):
  When spot sweeps below a key level in the morning session,
  the ATM PE premium bar shows a long UPPER wick — premium
  expanded (spot fell hard) then collapsed back (rejection).

  This option wick is a stronger reversal signal than spot wick alone
  because it captures IV spike + delta collapse + volume absorption
  all in one metric.

  Similarly for bear reversals: CE premium upper wick = CE buying
  absorbed at the sweep high → reversal down.

Test:
  For each morning session bar in hist_atm_option_bars_5m:
    - Is there a PE reversal wick? (pe_upper_wick_ratio >= 0.40)
    - Is ret_30m > 0? (spot rose after = PE wick correctly called reversal)

  Compare:
    PE wick present vs absent → WR difference
    CE wick present vs absent → WR difference
    Option wick + momentum aligned → combined edge

Tables:
  hist_atm_option_bars_5m  — PE/CE wick metrics
  hist_market_state         — regime context + ret_30m
  hist_pattern_signals      — for cross-reference with ICT zones
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

PE_WICK_MIN  = 0.35   # PE upper wick >= 35% of range = reversal signal
CE_WICK_MIN  = 0.35   # CE upper wick >= 35% of range


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
    try:
        dt = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
        return dt.hour * 60 + dt.minute
    except:
        return 0


def is_morning(bar_ts_str):
    m = get_mins(bar_ts_str)
    return (9*60+15) <= m <= (10*60+30)


def wr(w, n):
    return w/n*100 if n > 0 else 0


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("Experiment 26: Option Premium Wick as Reversal Signal")
    log("=" * 65)

    # ── Step 1: Load ATM option 5m bars ─────────────────────────────────
    log("\nStep 1: Loading hist_atm_option_bars_5m...")
    atm_rows = fetch_all(
        sb, "hist_atm_option_bars_5m",
        "trade_date,bar_ts,symbol,atm_strike,"
        "pe_open,pe_high,pe_low,pe_close,pe_upper_wick_ratio,pe_reversal_wick,"
        "ce_open,ce_high,ce_low,ce_close,ce_upper_wick_ratio,ce_reversal_wick,"
        "pcr_5m",
        order="bar_ts"
    )
    log(f"  {len(atm_rows)} ATM option bars")

    # ── Step 2: Load market state for regime + ret_30m ───────────────────
    log("\nStep 2: Loading hist_market_state...")
    mkt_rows = fetch_all(
        sb, "hist_market_state",
        "bar_ts,trade_date,symbol,spot,gamma_regime,breadth_regime,"
        "ret_session,ret_30m",
        order="bar_ts"
    )
    log(f"  {len(mkt_rows)} market state rows")

    # Index market state by (date, symbol, 5m_bucket)
    mkt_idx = {}
    for r in mkt_rows:
        mins   = get_mins(r["bar_ts"])
        bucket = (mins // 5) * 5
        key    = (r["trade_date"], r["symbol"], bucket)
        mkt_idx[key] = r  # last write wins = most recent 1m bar in bucket

    def get_mkt(trade_date, symbol, bar_ts):
        mins   = get_mins(bar_ts)
        bucket = (mins // 5) * 5
        m = mkt_idx.get((trade_date, symbol, bucket))
        if not m:
            for db in [-5, 5, -10, 10]:
                m = mkt_idx.get((trade_date, symbol, bucket+db))
                if m: break
        return m or {}

    # ── Step 3: Analyse morning bars ─────────────────────────────────────
    log("\nStep 3: Analysing morning option bars...")

    # Buckets: (pe_wick, ce_wick) boolean pairs
    results = defaultdict(lambda: {
        "bull_wins": 0, "bull_n": 0,  # bull = spot rose (PE wick reversal)
        "bear_wins": 0, "bear_n": 0,  # bear = spot fell (CE wick reversal)
        "ret_sum":   0.0,
    })

    # Detailed tracking
    pe_wick_yes = {"w": 0, "n": 0, "ret": 0.0}
    pe_wick_no  = {"w": 0, "n": 0, "ret": 0.0}
    ce_wick_yes = {"w": 0, "n": 0, "ret": 0.0}
    ce_wick_no  = {"w": 0, "n": 0, "ret": 0.0}

    # By regime
    by_gamma_pe = defaultdict(lambda: {"w": 0, "n": 0})
    by_gamma_ce = defaultdict(lambda: {"w": 0, "n": 0})

    # PE wick strength buckets
    pe_wick_strength = defaultdict(lambda: {"w": 0, "n": 0})

    morning_bars = 0

    for row in atm_rows:
        bar_ts    = row["bar_ts"]
        trade_date = row["trade_date"]
        symbol    = row["symbol"]

        if not is_morning(bar_ts):
            continue

        morning_bars += 1

        mkt     = get_mkt(trade_date, symbol, bar_ts)
        ret_30m = mkt.get("ret_30m")
        if ret_30m is None:
            continue
        ret_30m = float(ret_30m)
        gamma   = mkt.get("gamma_regime", "UNKNOWN")
        ret_sess = float(mkt["ret_session"]) if mkt.get("ret_session") else None

        # PE upper wick = spot fell hard then recovered → BUY_CE signal
        pe_wick = row.get("pe_upper_wick_ratio")
        pe_wick = float(pe_wick) if pe_wick is not None else 0
        pe_reversal = pe_wick >= PE_WICK_MIN

        # CE upper wick = spot rose hard then fell → BUY_PE signal
        ce_wick = row.get("ce_upper_wick_ratio")
        ce_wick = float(ce_wick) if ce_wick is not None else 0
        ce_reversal = ce_wick >= CE_WICK_MIN

        # PE reversal = predict spot rises → win if ret_30m > 0
        bull_win = ret_30m > 0
        bear_win = ret_30m < 0

        # PE wick analysis
        if pe_reversal:
            pe_wick_yes["w"] += bull_win
            pe_wick_yes["n"] += 1
            pe_wick_yes["ret"] += ret_30m
            by_gamma_pe[gamma]["w"] += bull_win
            by_gamma_pe[gamma]["n"] += 1
        else:
            pe_wick_no["w"] += bull_win
            pe_wick_no["n"] += 1
            pe_wick_no["ret"] += ret_30m

        # CE wick analysis
        if ce_reversal:
            ce_wick_yes["w"] += bear_win
            ce_wick_yes["n"] += 1
            by_gamma_ce[gamma]["w"] += bear_win
            by_gamma_ce[gamma]["n"] += 1
        else:
            ce_wick_no["w"] += bear_win
            ce_wick_no["n"] += 1

        # PE wick strength buckets
        if pe_wick >= 0.60:
            pe_wick_strength[">=60%"]["w"] += bull_win
            pe_wick_strength[">=60%"]["n"] += 1
        elif pe_wick >= 0.45:
            pe_wick_strength["45-60%"]["w"] += bull_win
            pe_wick_strength["45-60%"]["n"] += 1
        elif pe_wick >= 0.35:
            pe_wick_strength["35-45%"]["w"] += bull_win
            pe_wick_strength["35-45%"]["n"] += 1
        else:
            pe_wick_strength["<35%"]["w"] += bull_win
            pe_wick_strength["<35%"]["n"] += 1

        # Combined: PE wick + momentum aligned
        if pe_reversal and ret_sess is not None and ret_sess < -0.05:
            results["pe_wick_mom_aligned"]["bull_wins"] += bull_win
            results["pe_wick_mom_aligned"]["bull_n"] += 1

    log(f"  Morning bars analysed: {morning_bars}")
    log(f"  PE reversal wicks: {pe_wick_yes['n']}")
    log(f"  CE reversal wicks: {ce_wick_yes['n']}")

    # ── Step 4: Results ──────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("RESULTS: PE Upper Wick (Bullish Reversal Signal)")
    log("=" * 65)

    log(f"\n  PE wick >= {PE_WICK_MIN*100:.0f}%: "
        f"{wr(pe_wick_yes['w'], pe_wick_yes['n']):.1f}% WR "
        f"(N={pe_wick_yes['n']}) "
        f"avg ret {pe_wick_yes['ret']/pe_wick_yes['n']:+.3f}%"
        if pe_wick_yes['n'] > 0 else f"\n  PE wick YES: NO DATA")

    log(f"  PE wick < {PE_WICK_MIN*100:.0f}%:  "
        f"{wr(pe_wick_no['w'], pe_wick_no['n']):.1f}% WR "
        f"(N={pe_wick_no['n']}) "
        f"avg ret {pe_wick_no['ret']/pe_wick_no['n']:+.3f}%"
        if pe_wick_no['n'] > 0 else "  PE wick NO: NO DATA")

    lift_pe = (wr(pe_wick_yes['w'], pe_wick_yes['n']) -
               wr(pe_wick_no['w'], pe_wick_no['n']))
    log(f"\n  PE wick lift: {lift_pe:+.1f}pp")

    log(f"\n  PE wick strength breakdown:")
    for bucket in [">=60%", "45-60%", "35-45%", "<35%"]:
        b = pe_wick_strength.get(bucket, {"w":0,"n":0})
        if b["n"] == 0: continue
        log(f"    {bucket}: {wr(b['w'],b['n']):.1f}% WR (N={b['n']})")

    log(f"\n  PE wick by gamma regime:")
    for regime in ["SHORT_GAMMA","LONG_GAMMA","NO_FLIP"]:
        b = by_gamma_pe.get(regime, {"w":0,"n":0})
        if b["n"] == 0: continue
        log(f"    {regime:<15}: {wr(b['w'],b['n']):.1f}% WR (N={b['n']})")

    log("\n" + "=" * 65)
    log("RESULTS: CE Upper Wick (Bearish Reversal Signal)")
    log("=" * 65)

    log(f"\n  CE wick >= {CE_WICK_MIN*100:.0f}%: "
        f"{wr(ce_wick_yes['w'], ce_wick_yes['n']):.1f}% WR "
        f"(N={ce_wick_yes['n']})"
        if ce_wick_yes['n'] > 0 else "\n  CE wick YES: NO DATA")

    log(f"  CE wick < {CE_WICK_MIN*100:.0f}%:  "
        f"{wr(ce_wick_no['w'], ce_wick_no['n']):.1f}% WR "
        f"(N={ce_wick_no['n']})"
        if ce_wick_no['n'] > 0 else "  CE wick NO: NO DATA")

    lift_ce = (wr(ce_wick_yes['w'], ce_wick_yes['n']) -
               wr(ce_wick_no['w'], ce_wick_no['n']))
    log(f"\n  CE wick lift: {lift_ce:+.1f}pp")

    # Combined signal
    combo = results.get("pe_wick_mom_aligned", {"bull_wins":0,"bull_n":0})
    log(f"\n  PE wick + momentum aligned (ret_session < -0.05%):")
    log(f"    {wr(combo['bull_wins'],combo['bull_n']):.1f}% WR "
        f"(N={combo['bull_n']})")

    # ── Verdict ──────────────────────────────────────────────────────────
    log("\n" + "=" * 65)
    log("VERDICT")
    log("=" * 65)

    log(f"\n  PE upper wick lift: {lift_pe:+.1f}pp")
    log(f"  CE upper wick lift: {lift_ce:+.1f}pp")
    log("")

    if lift_pe >= 15 and pe_wick_yes['n'] >= 20:
        log(f"  PE WICK STRONG EDGE: {lift_pe:+.1f}pp lift (N={pe_wick_yes['n']})")
        log(f"  -> BUILD: Option wick reversal filter in signal engine")
        log(f"     When morning PE wick >= {PE_WICK_MIN*100:.0f}%, look for BUY_CE opportunity")
        log(f"     Combine with: momentum aligned + near HTF demand zone")
    elif lift_pe >= 8 and pe_wick_yes['n'] >= 10:
        log(f"  PE WICK MODERATE EDGE: {lift_pe:+.1f}pp — shadow test before live")
    elif pe_wick_yes['n'] < 10:
        log(f"  INSUFFICIENT DATA: only {pe_wick_yes['n']} PE wick bars in morning session")
        log(f"  The hist_atm_option_bars_5m may have limited coverage")
        log(f"  Check: do ATM option bars cover the full year?")
    else:
        log(f"  WEAK/NO EDGE: Option wick does not predict reversal ({lift_pe:+.1f}pp)")
        log(f"  Option wicks are noise — stick to spot structure for reversals")

    if lift_ce >= 15 and ce_wick_yes['n'] >= 20:
        log(f"\n  CE WICK STRONG EDGE: {lift_ce:+.1f}pp lift (N={ce_wick_yes['n']})")
    else:
        log(f"\n  CE wick: insufficient edge or data")

    log("\nExperiment 26 complete.")


if __name__ == "__main__":
    main()
