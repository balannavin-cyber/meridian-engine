"""
analyze_exp15_trades.py  --  Session 16 deep audit (Step 2)

Reads the trade-list CSV produced by experiment_15_with_csv_dump.py and
prints diagnostics that answer the question: IS THERE A REPLICABLE EDGE?

Each section addresses a specific concern about whether the aggregate
result reflects real edge or artefacts.

Usage:
    python analyze_exp15_trades.py exp15_trades_20260502_1900.csv

Sections
--------
9  -- Per-pattern WR with confidence intervals
10 -- Per (pattern x context) cell, CI lower bound vs 50%
11 -- Drop-one-session sensitivity (concentration check)
12 -- H1 vs H2 split (regime stability)
13 -- Per-symbol comparison (NIFTY vs SENSEX)
14 -- Time-of-day breakdown (intraday concentration)
15 -- Worst calendar month / monthly P&L distribution
16 -- Edge verdict synthesis
17 -- TD-056 bull-skew on live cohort (replicates Item 6 on 1m-detector)
18 -- FVG-on-OB clustering on live cohort (replicates Items 3-4 on 1m)

Sections 17-18 require Supabase access to fetch session_open prices.
If env vars are missing, those sections degrade gracefully to "skipped".

Author: Session 16 deep audit.
"""

from __future__ import annotations
import sys
import csv
import math
from collections import defaultdict
from datetime import datetime, date
from statistics import mean, median, stdev


def parse_csv(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for fld in ("entry_price", "strike", "entry_spot", "zone_high",
                        "zone_low", "capital_deployed",
                        "exit_t30_price", "pnl_t30",
                        "exit_ictexit_price", "pnl_ict"):
                v = r.get(fld)
                r[fld] = float(v) if v not in (None, "", "None") else None
            for fld in ("direction", "lots"):
                v = r.get(fld)
                r[fld] = int(v) if v not in (None, "", "None") else None
            rows.append(r)
    return rows


def wilson_ci(wins, n, z=1.96):
    """95% Wilson score interval for win rate."""
    if n == 0:
        return (0.0, 0.0)
    p = wins / n
    denom = 1 + z*z/n
    center = (p + z*z/(2*n)) / denom
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
    return (max(0, center - half) * 100, min(1, center + half) * 100)


def wr_with_ci(rows, pnl_key="pnl_t30"):
    vals = [r[pnl_key] for r in rows if r[pnl_key] is not None]
    if not vals:
        return None
    n = len(vals)
    wins = sum(1 for v in vals if v > 0)
    wr = wins / n * 100
    lo, hi = wilson_ci(wins, n)
    return {"n": n, "wins": wins, "wr": wr, "ci_lo": lo, "ci_hi": hi,
            "total_pnl": sum(vals), "mean_pnl": sum(vals)/n,
            "median_pnl": sorted(vals)[n//2]}


def section_9(trades):
    """Per-pattern WR with confidence intervals."""
    print("=" * 100)
    print("SECTION 9 -- Per-pattern WR with 95% Wilson confidence intervals")
    print("=" * 100)
    print(f"{'Pattern':<14} {'N':>5} {'WR':>7} {'95% CI':>16} "
          f"{'CI lower vs 50%':<18} {'mean PnL':>11} {'total PnL':>12}")
    print("-" * 100)
    patterns = sorted({t["pattern_type"] for t in trades})
    for pat in patterns:
        rs = [t for t in trades if t["pattern_type"] == pat]
        m = wr_with_ci(rs)
        if m is None:
            continue
        sig = "ABOVE 50%" if m["ci_lo"] > 50 else "below/spans 50%"
        print(f"{pat:<14} {m['n']:>5} {m['wr']:>6.1f}% "
              f"[{m['ci_lo']:>5.1f}, {m['ci_hi']:>5.1f}]  {sig:<18} "
              f"Rs {m['mean_pnl']:>+9,.0f}  Rs {m['total_pnl']:>+10,.0f}")
    print()


def section_10(trades):
    """Per (pattern x mtf_context) cell, CI lower bound vs 50%."""
    print("=" * 100)
    print("SECTION 10 -- Per (pattern x MTF context) cell  "
          "[* = CI lower bound > 50% i.e. edge above coin flip]")
    print("=" * 100)
    print(f"{'Pattern':<14} {'Context':<11} {'N':>4} {'WR':>7} "
          f"{'95% CI':>16} {'mean PnL':>10}")
    print("-" * 100)
    cells = defaultdict(list)
    for t in trades:
        cells[(t["pattern_type"], t["mtf_context"])].append(t)
    for (pat, ctx), rs in sorted(cells.items()):
        m = wr_with_ci(rs)
        if m is None or m["n"] < 5:
            continue
        flag = " *" if m["ci_lo"] > 50 else ""
        print(f"{pat:<14} {ctx:<11} {m['n']:>4} {m['wr']:>6.1f}% "
              f"[{m['ci_lo']:>5.1f}, {m['ci_hi']:>5.1f}]  "
              f"Rs {m['mean_pnl']:>+8,.0f}{flag}")
    print()


def section_11(trades):
    """Drop-one-session sensitivity. How concentrated is P&L?"""
    print("=" * 100)
    print("SECTION 11 -- P&L concentration (which sessions drive the result?)")
    print("=" * 100)
    sess_pnl = defaultdict(float)
    for t in trades:
        if t["pnl_t30"] is not None:
            sess_pnl[t["td"]] += t["pnl_t30"]
    if not sess_pnl:
        print("No P&L sessions.")
        return
    pnls = sorted(sess_pnl.values(), reverse=True)
    total = sum(pnls)
    print(f"Total P&L (T+30m) across all sessions: Rs {total:+,.0f}")
    print(f"Sessions with trades: {len(pnls)}")
    print(f"Sessions positive   : {sum(1 for p in pnls if p > 0)}")
    print(f"Sessions negative   : {sum(1 for p in pnls if p < 0)}")
    print(f"Sessions flat       : {sum(1 for p in pnls if p == 0)}")
    print()
    print("Top contributors (cumulative share of total P&L):")
    cum = 0.0
    for i, p in enumerate(pnls[:15], 1):
        cum += p
        share = cum / total * 100 if total else 0
        print(f"  Top {i:>2} session: Rs {p:>+10,.0f}   cumulative share = {share:>5.1f}%")
        if share > 90:
            print(f"  -> top {i} sessions account for >90% of P&L")
            break
    if total:
        # Concentration: how many sessions for 50% / 80% of P&L?
        cum = 0.0
        n50 = n80 = None
        for i, p in enumerate(pnls, 1):
            cum += p
            share = cum / total * 100 if total else 0
            if n50 is None and share >= 50:
                n50 = i
            if n80 is None and share >= 80:
                n80 = i
                break
        if n50:
            print(f"\nTop {n50} sessions = 50% of P&L  ({n50/len(pnls)*100:.1f}% of trading sessions)")
        if n80:
            print(f"Top {n80} sessions = 80% of P&L  ({n80/len(pnls)*100:.1f}% of trading sessions)")
        if n80 and n80 / len(pnls) < 0.10:
            print(">>> WARNING: <10% of sessions produce 80% of P&L. Edge is concentrated.")
        elif n80 and n80 / len(pnls) > 0.30:
            print(">>> Edge is broadly distributed across sessions (>30% sessions for 80% P&L).")
    print()


def section_12(trades):
    """First half vs second half of date range."""
    print("=" * 100)
    print("SECTION 12 -- H1 vs H2 split (regime stability)")
    print("=" * 100)
    dates = sorted({t["td"] for t in trades})
    if len(dates) < 4:
        print("Insufficient dates for H1/H2 split.")
        return
    midpoint_idx = len(dates) // 2
    midpoint_date = dates[midpoint_idx]
    h1_trades = [t for t in trades if t["td"] < midpoint_date]
    h2_trades = [t for t in trades if t["td"] >= midpoint_date]
    print(f"H1: {dates[0]} to {dates[midpoint_idx-1]}  ({len(h1_trades)} trades)")
    print(f"H2: {midpoint_date} to {dates[-1]}  ({len(h2_trades)} trades)")
    print()
    print(f"{'Pattern':<14} {'H1 N':>5} {'H1 WR':>7} {'H1 PnL':>11}    "
          f"{'H2 N':>5} {'H2 WR':>7} {'H2 PnL':>11}    {'consistent?':<12}")
    print("-" * 100)
    patterns = sorted({t["pattern_type"] for t in trades})
    for pat in patterns:
        h1 = wr_with_ci([t for t in h1_trades if t["pattern_type"] == pat])
        h2 = wr_with_ci([t for t in h2_trades if t["pattern_type"] == pat])
        if h1 is None or h2 is None:
            continue
        wr_delta = abs(h1["wr"] - h2["wr"])
        pnl_consistent = ((h1["total_pnl"] > 0) == (h2["total_pnl"] > 0))
        if wr_delta < 10 and pnl_consistent:
            tag = "STABLE"
        elif pnl_consistent:
            tag = "drift"
        else:
            tag = "UNSTABLE"
        print(f"{pat:<14} {h1['n']:>5} {h1['wr']:>6.1f}% Rs {h1['total_pnl']:>+8,.0f}    "
              f"{h2['n']:>5} {h2['wr']:>6.1f}% Rs {h2['total_pnl']:>+8,.0f}    {tag:<12}")
    print()


def section_13(trades):
    """Per-symbol breakdown."""
    print("=" * 100)
    print("SECTION 13 -- Per-symbol comparison")
    print("=" * 100)
    for sym in sorted({t["symbol"] for t in trades}):
        rs = [t for t in trades if t["symbol"] == sym]
        m = wr_with_ci(rs)
        if m is None:
            continue
        print(f"\n{sym}: N={m['n']}, WR={m['wr']:.1f}% [{m['ci_lo']:.1f}, {m['ci_hi']:.1f}], "
              f"total Rs {m['total_pnl']:+,.0f}")
        for pat in sorted({t["pattern_type"] for t in rs}):
            mp = wr_with_ci([t for t in rs if t["pattern_type"] == pat])
            if mp:
                print(f"  {pat:<14} N={mp['n']:>4}  WR={mp['wr']:>5.1f}% "
                      f"[{mp['ci_lo']:>5.1f},{mp['ci_hi']:>5.1f}]  "
                      f"Rs {mp['total_pnl']:>+9,.0f}")
    print()


def section_14(trades):
    """Time-of-day breakdown."""
    print("=" * 100)
    print("SECTION 14 -- Time-of-day breakdown")
    print("=" * 100)
    print(f"{'Time zone':<12} {'N':>5} {'WR':>7} {'95% CI':>16} {'mean PnL':>11}")
    print("-" * 100)
    for tz in sorted({t["time_zone"] for t in trades}):
        rs = [t for t in trades if t["time_zone"] == tz]
        m = wr_with_ci(rs)
        if m and m["n"] >= 5:
            flag = " *" if m["ci_lo"] > 50 else ""
            print(f"{tz:<12} {m['n']:>5} {m['wr']:>6.1f}% "
                  f"[{m['ci_lo']:>5.1f}, {m['ci_hi']:>5.1f}]  "
                  f"Rs {m['mean_pnl']:>+8,.0f}{flag}")
    print()


def section_15(trades):
    """Per-month P&L distribution."""
    print("=" * 100)
    print("SECTION 15 -- Per-month P&L distribution (worst-case month)")
    print("=" * 100)
    by_month = defaultdict(lambda: {"n": 0, "pnl": 0.0, "wins": 0})
    for t in trades:
        if t["pnl_t30"] is None:
            continue
        td = t["td"]
        # ISO date string YYYY-MM-DD
        month_key = td[:7] if isinstance(td, str) else f"{td.year}-{td.month:02d}"
        by_month[month_key]["n"] += 1
        by_month[month_key]["pnl"] += t["pnl_t30"]
        if t["pnl_t30"] > 0:
            by_month[month_key]["wins"] += 1
    print(f"{'Month':<10} {'N':>5} {'WR':>7} {'PnL':>14}")
    print("-" * 60)
    for mo in sorted(by_month):
        d = by_month[mo]
        wr = d["wins"]/d["n"]*100 if d["n"] else 0
        print(f"{mo:<10} {d['n']:>5} {wr:>6.1f}% Rs {d['pnl']:>+11,.0f}")
    pnls = [d["pnl"] for d in by_month.values()]
    pos = sum(1 for p in pnls if p > 0)
    neg = sum(1 for p in pnls if p < 0)
    print(f"\nMonths positive: {pos}/{len(pnls)}, negative: {neg}/{len(pnls)}")
    if pnls:
        print(f"Best month: Rs {max(pnls):+,.0f}")
        print(f"Worst month: Rs {min(pnls):+,.0f}")
    print()


def section_16(trades):
    """Synthesise: is there an edge?"""
    print("=" * 100)
    print("SECTION 16 -- EDGE VERDICT SYNTHESIS")
    print("=" * 100)

    pooled = wr_with_ci(trades)
    print(f"\nPooled across all trades: N={pooled['n']}, "
          f"WR={pooled['wr']:.1f}% [{pooled['ci_lo']:.1f}, {pooled['ci_hi']:.1f}], "
          f"total PnL Rs {pooled['total_pnl']:+,.0f}")

    pooled_above_50 = pooled["ci_lo"] > 50
    pooled_pnl_pos = pooled["total_pnl"] > 0

    # Per-pattern edge cells (CI > 50%)
    cells_above_50 = []
    cells_below_50 = []
    cell_groups = defaultdict(list)
    for t in trades:
        cell_groups[(t["pattern_type"], t["mtf_context"])].append(t)
    for cell, rs in cell_groups.items():
        m = wr_with_ci(rs)
        if m and m["n"] >= 20:
            if m["ci_lo"] > 50:
                cells_above_50.append((cell, m))
            else:
                cells_below_50.append((cell, m))

    print(f"\nCells with N>=20 AND CI lower bound > 50% (real edge above coin flip):")
    for (pat, ctx), m in sorted(cells_above_50, key=lambda x: -x[1]["wr"]):
        print(f"  {pat} | {ctx}: N={m['n']}, WR={m['wr']:.1f}% [{m['ci_lo']:.1f}, {m['ci_hi']:.1f}]")
    if not cells_above_50:
        print("  (none)")

    print(f"\nCells with N>=20 but CI spans / below 50%:")
    for (pat, ctx), m in sorted(cells_below_50, key=lambda x: -x[1]["wr"]):
        print(f"  {pat} | {ctx}: N={m['n']}, WR={m['wr']:.1f}% [{m['ci_lo']:.1f}, {m['ci_hi']:.1f}]")

    # H1/H2 stability
    dates = sorted({t["td"] for t in trades})
    if len(dates) >= 4:
        mid = dates[len(dates)//2]
        h1_pnl = sum(t["pnl_t30"] for t in trades
                     if t["td"] < mid and t["pnl_t30"] is not None)
        h2_pnl = sum(t["pnl_t30"] for t in trades
                     if t["td"] >= mid and t["pnl_t30"] is not None)
        h1_h2_consistent = (h1_pnl > 0) and (h2_pnl > 0)
        print(f"\nH1 P&L: Rs {h1_pnl:+,.0f}  H2 P&L: Rs {h2_pnl:+,.0f}  "
              f"Both halves positive: {h1_h2_consistent}")
    else:
        h1_h2_consistent = False

    # Concentration
    sess_pnl = defaultdict(float)
    for t in trades:
        if t["pnl_t30"] is not None:
            sess_pnl[t["td"]] += t["pnl_t30"]
    pnls = sorted(sess_pnl.values(), reverse=True)
    total = sum(pnls)
    n80 = None
    cum = 0.0
    for i, p in enumerate(pnls, 1):
        cum += p
        if total > 0 and cum / total >= 0.80:
            n80 = i
            break
    concentration_ok = (n80 is not None and len(pnls) > 0
                        and n80 / len(pnls) > 0.20)
    if n80 and len(pnls):
        print(f"\nP&L concentration: top {n80} sessions ({n80/len(pnls)*100:.1f}% of "
              f"trading sessions) = 80% of P&L. Broadly distributed: {concentration_ok}")

    # Final verdict
    print()
    print("=" * 100)
    if pooled_pnl_pos and pooled_above_50 and len(cells_above_50) >= 2 and h1_h2_consistent and concentration_ok:
        verdict = "STRONG EDGE"
        rationale = ("Pooled WR > 50% (CI clears coin flip), multiple per-cell edges, "
                     "stable across H1/H2, broadly distributed P&L.")
    elif pooled_pnl_pos and (pooled_above_50 or len(cells_above_50) >= 1):
        verdict = "EDGE PRESENT BUT NARROWER THAN HEADLINE"
        rationale = ("P&L positive overall and at least some cells clear coin flip, "
                     "but not all robustness checks pass. Edge is real but more "
                     "concentrated or less stable than the +180% headline implies.")
    elif pooled_pnl_pos:
        verdict = "POSITIVE P&L BUT WEAK STATISTICAL EVIDENCE"
        rationale = ("Capital grew, but no per-cell WR clears coin flip with "
                     "confidence and/or P&L is concentrated in a few sessions. "
                     "The dollar return could be regime tailwind, not pattern edge.")
    else:
        verdict = "NO EDGE"
        rationale = "Pooled P&L not positive; pattern selection does not produce profit."

    print(f"VERDICT: {verdict}")
    print(f"Rationale: {rationale}")
    print("=" * 100)


# ============================================================================
# SECTION 17 -- TD-056 bull-skew on live (1m-detector) cohort
# ============================================================================
# Item 6 in carry-forward register: bull-skew on hist_pattern_signals (5m batch)
# is regime-INDEPENDENT (5.6x BULL/BEAR ratio in NIFTY DOWN).
#
# This section asks: does the same bull-skew exist on the 1m live-detector
# cohort? If YES -> structural detector concern across both code paths.
# If NO  -> bull-skew is 5m-batch-specific, live path is fine.
#
# We need ret_session per trade to partition by regime. The trade list
# doesn't have it (1m detector doesn't write to hist_pattern_signals).
# We compute ret_session by fetching session-open spot from Supabase
# and using entry_spot already in the CSV:
#     ret_session = (entry_spot - session_open) / session_open * 100

RET_SESSION_FLAT_PCT = 0.05  # ENH-44 alignment threshold


def _try_supabase():
    """Returns (sb_client, error_msg). Both None if Supabase available."""
    try:
        import os
        from dotenv import load_dotenv
        from supabase import create_client
    except ImportError as e:
        return None, f"missing package: {e.name}"
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if not url or not key:
        return None, "SUPABASE_URL or SUPABASE_*_KEY missing in .env"
    try:
        return create_client(url, key), None
    except Exception as e:
        return None, f"Supabase client init failed: {e}"


def _fetch_session_opens(sb, trades):
    """Returns dict {(symbol, trade_date_str): session_open_close}."""
    pairs = sorted({(t["symbol"], t["td"][:10] if isinstance(t["td"], str)
                     else str(t["td"])) for t in trades})
    print(f"  Fetching session-open spot for {len(pairs)} (symbol, date) pairs...")
    inst_rows = sb.table("instruments").select("id, symbol").execute().data
    inst_id = {r["symbol"]: r["id"] for r in inst_rows}
    out = {}
    PAGE = 1000
    by_symbol = defaultdict(list)
    for sym, td in pairs:
        by_symbol[sym].append(td)
    for sym, dates in by_symbol.items():
        if sym not in inst_id:
            continue
        # Pull open spot for each date (one row per date — first bar of day)
        # We use trade_date filter and order by bar_ts; first bar in result is open.
        for td in dates:
            try:
                r = (sb.table("hist_spot_bars_1m")
                     .select("bar_ts, open")
                     .eq("instrument_id", inst_id[sym])
                     .eq("trade_date", td)
                     .order("bar_ts")
                     .limit(1)
                     .execute().data)
                if r:
                    out[(sym, td)] = float(r[0]["open"])
            except Exception:
                pass
    return out


def section_17(trades):
    """TD-056 bull-skew on live cohort."""
    print("=" * 100)
    print("SECTION 17 -- TD-056 bull-skew test on LIVE 1m-detector cohort")
    print("=" * 100)
    print("Reference: Item 6 found 5.6x BULL/BEAR ratio in NIFTY DOWN regime")
    print("on hist_pattern_signals (5m batch). This section tests the same")
    print("on the live 1m-detector cohort -- the path Exp 15 actually uses.")
    print()

    sb, err = _try_supabase()
    if sb is None:
        print(f"[SKIP] {err}")
        print(f"To enable: ensure .env has SUPABASE_URL and "
              f"SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY)")
        print()
        return

    # Fetch session opens
    session_opens = _fetch_session_opens(sb, trades)
    print(f"  Fetched {len(session_opens)} session opens")
    print()

    # Compute ret_session per trade
    enriched = 0
    for t in trades:
        td_str = t["td"][:10] if isinstance(t["td"], str) else str(t["td"])
        sopen = session_opens.get((t["symbol"], td_str))
        if sopen and t.get("entry_spot"):
            t["_ret_session"] = (t["entry_spot"] - sopen) / sopen * 100.0
            v = t["_ret_session"]
            if v > RET_SESSION_FLAT_PCT:
                t["_regime"] = "UP"
            elif v < -RET_SESSION_FLAT_PCT:
                t["_regime"] = "DOWN"
            else:
                t["_regime"] = "FLAT"
            enriched += 1
        else:
            t["_regime"] = None
    print(f"  Enriched {enriched}/{len(trades)} trades with regime")
    print()

    # OB ratio table
    print("BULL_OB vs BEAR_OB count by regime per symbol:")
    print(f"  {'Symbol':<8} {'Regime':<6} {'BULL_OB':>8} {'BEAR_OB':>8} "
          f"{'Ratio':>8}  Verdict")
    print("  " + "-" * 80)
    rows_for_verdict = []
    symbols = sorted({t["symbol"] for t in trades})
    for sym in symbols:
        for regime in ("UP", "FLAT", "DOWN"):
            bull_n = sum(1 for t in trades
                         if t["symbol"] == sym
                         and t["pattern_type"] == "BULL_OB"
                         and t.get("_regime") == regime)
            bear_n = sum(1 for t in trades
                         if t["symbol"] == sym
                         and t["pattern_type"] == "BEAR_OB"
                         and t.get("_regime") == regime)
            if bear_n == 0:
                ratio_str = (f"{bull_n}:0"
                             if bull_n > 0 else "0:0")
            else:
                ratio_str = f"{bull_n/bear_n:.2f}x"
            if regime == "UP" and bull_n > bear_n:
                v = "OK (bull regime)"
            elif regime == "DOWN" and bear_n > bull_n:
                v = "OK (bear regime)"
            elif regime == "DOWN" and bull_n > bear_n:
                v = "ANOMALY (bull-skew in DOWN)"
            elif regime == "UP" and bear_n > bull_n:
                v = "ANOMALY (bear-skew in UP)"
            else:
                v = "(flat / unclear)"
            print(f"  {sym:<8} {regime:<6} {bull_n:>8} {bear_n:>8} "
                  f"{ratio_str:>8}  {v}")
            rows_for_verdict.append({
                "symbol": sym, "regime": regime,
                "bull": bull_n, "bear": bear_n,
            })
        print()

    # Repeat for FVG patterns if present
    fvg_present = any(t["pattern_type"] in ("BULL_FVG", "BEAR_FVG")
                      for t in trades)
    if fvg_present:
        print("BULL_FVG vs BEAR_FVG count by regime per symbol:")
        print(f"  {'Symbol':<8} {'Regime':<6} {'BULL_FVG':>9} {'BEAR_FVG':>9} "
              f"{'Ratio':>8}  Verdict")
        print("  " + "-" * 80)
        for sym in symbols:
            for regime in ("UP", "FLAT", "DOWN"):
                bull_n = sum(1 for t in trades
                             if t["symbol"] == sym
                             and t["pattern_type"] == "BULL_FVG"
                             and t.get("_regime") == regime)
                bear_n = sum(1 for t in trades
                             if t["symbol"] == sym
                             and t["pattern_type"] == "BEAR_FVG"
                             and t.get("_regime") == regime)
                if bear_n == 0:
                    ratio_str = f"{bull_n}:0" if bull_n > 0 else "0:0"
                else:
                    ratio_str = f"{bull_n/bear_n:.2f}x"
                if regime == "UP" and bull_n > bear_n:
                    v = "OK"
                elif regime == "DOWN" and bear_n > bull_n:
                    v = "OK"
                elif regime == "DOWN" and bull_n > bear_n:
                    v = "ANOMALY (bull-skew in DOWN)"
                elif regime == "UP" and bear_n > bull_n:
                    v = "ANOMALY (bear-skew in UP)"
                else:
                    v = "(flat / unclear)"
                print(f"  {sym:<8} {regime:<6} {bull_n:>9} {bear_n:>9} "
                      f"{ratio_str:>8}  {v}")
            print()

    # Cross-cohort verdict
    print("VERDICT (compare to hist_pattern_signals 5m-batch baseline):")
    print("  5m-batch (Item 6): NIFTY DOWN 5.60x bull-skew, SENSEX DOWN 2.30x")
    print()
    nifty_down = next((r for r in rows_for_verdict
                       if r["symbol"] == "NIFTY" and r["regime"] == "DOWN"), None)
    if nifty_down and nifty_down["bear"] > 0:
        live_ratio = nifty_down["bull"] / nifty_down["bear"]
        print(f"  Live 1m: NIFTY DOWN {live_ratio:.2f}x  ({nifty_down['bull']} BULL_OB / "
              f"{nifty_down['bear']} BEAR_OB)")
        if nifty_down["bear"] > nifty_down["bull"]:
            print(f"  -> 1m live cohort INVERTS in DOWN regime. TD-056 bull-skew")
            print(f"     is 5m-batch-specific. Live detector path is fine.")
        else:
            print(f"  -> 1m live cohort STILL bull-skewed in DOWN. TD-056 expands")
            print(f"     to a structural concern across both code paths.")
    else:
        print(f"  Insufficient NIFTY DOWN trades on live cohort to call.")
    print()


# ============================================================================
# SECTION 18 -- FVG-on-OB clustering on live (1m-detector) cohort
# ============================================================================
# Items 3-4 in carry-forward register: Exp 50/50b found cluster effects on
# 5m-batch hist_pattern_signals data, with mixed verdicts. This section asks
# whether FVG outcomes are better when there's a recent same-direction OB.
#
# Definition: an FVG trade is "clustered" if any same-direction OB trade
# fired within the last 60 minutes on the same symbol. Compare WR of
# clustered vs standalone FVG trades.

def section_18(trades):
    """FVG-on-OB clustering on live cohort."""
    print("=" * 100)
    print("SECTION 18 -- FVG-on-OB clustering on LIVE 1m-detector cohort")
    print("=" * 100)
    print("Reference: Items 3-4 (Exp 50 / 50b) tested this on 5m-batch with")
    print("mixed verdicts. This re-tests on the live 1m-detector cohort.")
    print()

    # Need entry_ts as datetime. Trades CSV has it as ISO string.
    fvg_patterns = [t for t in trades if t["pattern_type"] in ("BULL_FVG", "BEAR_FVG")]
    if not fvg_patterns:
        print("No FVG trades present in this cohort. Skipping.")
        print()
        return

    # Parse entry_ts to datetime once
    for t in trades:
        ts_str = t.get("entry_ts")
        if isinstance(ts_str, str):
            try:
                t["_entry_dt"] = datetime.fromisoformat(ts_str)
            except ValueError:
                t["_entry_dt"] = None
        elif isinstance(ts_str, datetime):
            t["_entry_dt"] = ts_str
        else:
            t["_entry_dt"] = None

    from datetime import timedelta as td_delta
    LOOKBACKS = [30, 60, 90]  # minutes

    for fvg_dir, ob_pat in (("BULL_FVG", "BULL_OB"), ("BEAR_FVG", "BEAR_OB")):
        rs = [t for t in fvg_patterns if t["pattern_type"] == fvg_dir]
        if not rs:
            continue
        print(f"--- {fvg_dir} clustering with recent {ob_pat} ---")
        # Group OB trades by symbol for fast lookup
        ob_trades = [t for t in trades
                     if t["pattern_type"] == ob_pat and t.get("_entry_dt")]
        ob_by_sym = defaultdict(list)
        for t in ob_trades:
            ob_by_sym[t["symbol"]].append(t["_entry_dt"])
        for sym in ob_by_sym:
            ob_by_sym[sym].sort()

        print(f"  {'Lookback':<10} {'N clust':>8} {'WR clust':>9} "
              f"{'N stand':>8} {'WR stand':>9} {'Lift':>6}")
        print("  " + "-" * 56)
        for lb_min in LOOKBACKS:
            clustered = []
            standalone = []
            for r in rs:
                fvg_dt = r.get("_entry_dt")
                if fvg_dt is None:
                    continue
                ob_list = ob_by_sym.get(r["symbol"], [])
                # Linear scan: any OB within lb_min of fvg_dt and before it
                has_recent_ob = any(
                    fvg_dt - td_delta(minutes=lb_min) <= ob_dt < fvg_dt
                    for ob_dt in ob_list
                )
                if has_recent_ob:
                    clustered.append(r)
                else:
                    standalone.append(r)
            mc = wr_with_ci(clustered)
            ms = wr_with_ci(standalone)
            if mc and ms and mc["n"] >= 5 and ms["n"] >= 5:
                lift = mc["wr"] - ms["wr"]
                print(f"  {lb_min:>3} min   {mc['n']:>8} {mc['wr']:>8.1f}% "
                      f"{ms['n']:>8} {ms['wr']:>8.1f}% {lift:>+5.1f}pp")
            else:
                nc = mc["n"] if mc else 0
                ns = ms["n"] if ms else 0
                print(f"  {lb_min:>3} min   {nc:>8} (--){ns:>11} (--)  "
                      f"insufficient N")
        print()

    # Verdict
    print("VERDICT (compare to Exp 50/50b 5m-batch baseline):")
    print("  Exp 50 5m-batch (Item 3): BULL/60min/0.50% PASS at +8.3pp lift")
    print("                            BEAR/60min/0.50% FAIL at -4.2pp lift")
    print("  This section's lift figures above for each (FVG, lookback) cell")
    print("  tell us whether the cluster effect replicates on live cohort.")
    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_exp15_trades.py <trades_csv>")
        sys.exit(1)
    csv_path = sys.argv[1]
    print(f"Loading {csv_path} ...")
    trades = parse_csv(csv_path)
    print(f"Loaded {len(trades)} trades")
    print()
    section_9(trades)
    section_10(trades)
    section_11(trades)
    section_12(trades)
    section_13(trades)
    section_14(trades)
    section_15(trades)
    section_16(trades)
    section_17(trades)
    section_18(trades)


if __name__ == "__main__":
    main()
