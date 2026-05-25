#!/usr/bin/env python3
"""
experiment_37_london_kill_zone.py
MERDIAN Experiment 37 — London Kill Zone Isolation

Question:
    Does the AFTERNOON OB edge (documented in compendium) concentrate
    specifically in the 13:30–14:30 IST window (London open kill zone)?
    And is 14:30–15:30 IST materially weaker?

Background:
    Compendium (Exp 15 re-run, Session 10):
      - BULL_OB AFTERNOON → 100% WR (small N)
      - BEAR_OB AFTERNOON → HARD SKIP (17% WR)
    ICT London kill zone: 08:00–09:00 London time = 13:30–14:30 IST.
    European institutional FII flows hit NIFTY/SENSEX at London open.
    If the AFTERNOON edge concentrates here, the kill zone becomes a
    time-gate for entries — significantly narrowing the trading window.

Hypothesis:
    BULL_OB in 13:30–14:30 IST >> BULL_OB in 14:30–15:30 IST
    BEAR_OB in 13:30–14:30 IST may also show directional signal
    (compendium says BEAR_OB AFTERNOON = hard skip, but that may mask
     a sub-window that is actually valid)

Data source:
    hist_pattern_signals — uses bar_ts to sub-classify within AFTERNOON.
    Columns used: bar_ts, pattern_type, session, win_30m, win_60m, symbol, tier

Sub-windows tested:
    - LKZ_EARLY  : 13:30–14:00 IST (first 30 min of London open)
    - LKZ_CORE   : 14:00–14:30 IST (core kill zone)
    - LKZ_LATE   : 14:30–15:00 IST (post-kill-zone fade)
    - LKZ_CLOSE  : 15:00–15:30 IST (closing window)

Pass criteria:
    - BULL_OB in LKZ (13:30–14:30 combined): WR >= 65%, N >= 20
    - LKZ WR >= 1.2× non-LKZ AFTERNOON WR (concentration ratio)

TD-029 workaround: bar_ts stored as IST labeled +00:00.
Pagination: 1000 rows/request.

Run from: C:\\GammaEnginePython
Usage  : python experiment_37_london_kill_zone.py

Session: 11  (2026-04-28)
"""

import os
import sys
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client

# ── Environment ───────────────────────────────────────────────────────────────
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not in .env")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

PASS_N        = 20
PASS_WR       = 0.65
CONCENTRATION = 1.20   # LKZ WR must be >= 1.2x non-LKZ to claim concentration


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_ts(ts_str: str) -> datetime:
    # TD-029: IST stored as +00:00. Treat as naive IST directly.
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)


def bar_minutes(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def lkz_label(dt: datetime) -> str:
    t = bar_minutes(dt)
    if   13*60+30 <= t < 14*60:    return "LKZ_EARLY"   # 13:30–14:00
    elif 14*60    <= t < 14*60+30: return "LKZ_CORE"    # 14:00–14:30
    elif 14*60+30 <= t < 15*60:    return "LKZ_LATE"    # 14:30–15:00
    elif 15*60    <= t < 15*60+30: return "LKZ_CLOSE"   # 15:00–15:30
    return "NON_AFTERNOON"


def pct(v: float) -> str:
    return f"{v:.1%}"


def mean(lst):
    return sum(lst) / len(lst) if lst else None


# ── Fetch ─────────────────────────────────────────────────────────────────────
def fetch_afternoon_signals() -> list:
    """
    Fetch all BEAR_OB and BULL_OB signals from hist_pattern_signals.
    We pull all sessions and sub-classify by bar_ts within AFTERNOON.
    bar_ts is the signal detection bar's IST time (TD-029 convention).
    """
    print("Fetching OB signals from hist_pattern_signals...", end="", flush=True)
    rows, page = [], 0
    while True:
        resp = (
            supabase.table("hist_pattern_signals")
            .select("bar_ts,symbol,pattern_type,session,win_30m,win_60m,tier,gamma_regime")
            .in_("pattern_type", ["BEAR_OB", "BULL_OB"])
            .order("bar_ts")
            .range(page, page + 999)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < 1000:
            break
        page += 1000

    # Attach parsed timestamp and LKZ label
    for row in rows:
        dt = parse_ts(row["bar_ts"])
        row["_dt"]  = dt
        row["_lkz"] = lkz_label(dt)

    print(f" {len(rows)} signals total")
    return rows


# ── Reporting ─────────────────────────────────────────────────────────────────
def section(label: str):
    print(f"\n{'─' * 62}")
    print(f"  {label}")
    print(f"{'─' * 62}")


def report(signals, label, win_key="win_30m", pass_wr=None):
    valid = [s for s in signals if s.get(win_key) is not None]
    n     = len(valid)
    if not valid:
        print(f"  {label:<52}  N=  0")
        return None
    wr  = sum(1 for s in valid if s[win_key]) / n
    avg = mean([1 if s[win_key] else 0 for s in valid])
    flag = ""
    if pass_wr is not None:
        flag = " ✅" if wr >= pass_wr else " ❌"
    print(f"  {label:<52}  N={n:>4}  WR={pct(wr)}{flag}")
    return wr


def print_results(signals):
    bear = [s for s in signals if s["pattern_type"] == "BEAR_OB"]
    bull = [s for s in signals if s["pattern_type"] == "BULL_OB"]

    # ── Baseline ──────────────────────────────────────────────────────────────
    section("BASELINE — All sessions by session label")
    for sess in ["OPEN", "MORNING", "MIDDAY", "AFTERNOON"]:
        report([s for s in bear if s.get("session") == sess], f"BEAR_OB {sess}")
        report([s for s in bull if s.get("session") == sess], f"BULL_OB {sess}")

    # ── LKZ sub-windows ───────────────────────────────────────────────────────
    section("LONDON KILL ZONE — AFTERNOON sub-windows (by bar_ts IST)")
    for label in ["LKZ_EARLY", "LKZ_CORE", "LKZ_LATE", "LKZ_CLOSE"]:
        times = {
            "LKZ_EARLY":  "13:30–14:00",
            "LKZ_CORE":   "14:00–14:30",
            "LKZ_LATE":   "14:30–15:00",
            "LKZ_CLOSE":  "15:00–15:30",
        }
        report([s for s in bear if s["_lkz"] == label],
               f"BEAR_OB {times[label]} ({label})")
        report([s for s in bull if s["_lkz"] == label],
               f"BULL_OB {times[label]} ({label})")

    # ── LKZ combined vs non-LKZ ───────────────────────────────────────────────
    section("LKZ COMBINED (13:30–14:30) vs NON-LKZ AFTERNOON (14:30–15:30)")
    lkz_labels = {"LKZ_EARLY", "LKZ_CORE"}

    bear_lkz     = [s for s in bear if s["_lkz"] in lkz_labels]
    bear_non_lkz = [s for s in bear if s["_lkz"] in {"LKZ_LATE", "LKZ_CLOSE"}]
    bull_lkz     = [s for s in bull if s["_lkz"] in lkz_labels]
    bull_non_lkz = [s for s in bull if s["_lkz"] in {"LKZ_LATE", "LKZ_CLOSE"}]

    bear_lkz_wr     = report(bear_lkz,     "BEAR_OB LKZ 13:30–14:30",  pass_wr=PASS_WR)
    bear_non_lkz_wr = report(bear_non_lkz, "BEAR_OB NON-LKZ 14:30–15:30")
    bull_lkz_wr     = report(bull_lkz,     "BULL_OB LKZ 13:30–14:30",  pass_wr=PASS_WR)
    bull_non_lkz_wr = report(bull_non_lkz, "BULL_OB NON-LKZ 14:30–15:30")

    # Concentration ratio
    print()
    if bear_lkz_wr and bear_non_lkz_wr and bear_non_lkz_wr > 0:
        ratio = bear_lkz_wr / bear_non_lkz_wr
        print(f"  BEAR_OB LKZ/non-LKZ ratio: {ratio:.2f}x  ({'concentrated ✅' if ratio >= CONCENTRATION else 'not concentrated'})")
    if bull_lkz_wr and bull_non_lkz_wr and bull_non_lkz_wr > 0:
        ratio = bull_lkz_wr / bull_non_lkz_wr
        print(f"  BULL_OB LKZ/non-LKZ ratio: {ratio:.2f}x  ({'concentrated ✅' if ratio >= CONCENTRATION else 'not concentrated'})")

    # ── T+60m cross-check ─────────────────────────────────────────────────────
    section("T+60m CROSS-CHECK — LKZ combined")
    report(bear_lkz, "BEAR_OB LKZ (T+60m)", win_key="win_60m")
    report(bull_lkz, "BULL_OB LKZ (T+60m)", win_key="win_60m")

    # ── By symbol ─────────────────────────────────────────────────────────────
    section("BY SYMBOL — LKZ combined")
    for sym in ["NIFTY", "SENSEX"]:
        report([s for s in bear_lkz if s["symbol"] == sym],
               f"BEAR_OB LKZ {sym}", pass_wr=PASS_WR)
        report([s for s in bull_lkz if s["symbol"] == sym],
               f"BULL_OB LKZ {sym}", pass_wr=PASS_WR)

    # ── By tier ───────────────────────────────────────────────────────────────
    section("BY TIER — LKZ combined")
    for tier in ["TIER1", "TIER2"]:
        sub_b = [s for s in bear_lkz if s.get("tier") == tier]
        sub_u = [s for s in bull_lkz if s.get("tier") == tier]
        if sub_b: report(sub_b, f"BEAR_OB LKZ {tier}")
        if sub_u: report(sub_u, f"BULL_OB LKZ {tier}")

    # ── Gamma regime ──────────────────────────────────────────────────────────
    section("BY GAMMA REGIME — LKZ combined")
    for regime in ["LONG_GAMMA", "SHORT_GAMMA"]:
        sub_b = [s for s in bear_lkz if s.get("gamma_regime") == regime]
        sub_u = [s for s in bull_lkz if s.get("gamma_regime") == regime]
        if sub_b: report(sub_b, f"BEAR_OB LKZ {regime}")
        if sub_u: report(sub_u, f"BULL_OB LKZ {regime}")

    # ── Pass / fail ───────────────────────────────────────────────────────────
    section("PASS / FAIL ASSESSMENT")

    def assess(signals, label, pass_wr, n_req, win_key="win_30m"):
        valid = [s for s in signals if s.get(win_key) is not None]
        if not valid:
            print(f"  {label}: INSUFFICIENT DATA")
            return False
        wr = sum(1 for s in valid if s[win_key]) / len(valid)
        passed = len(valid) >= n_req and wr >= pass_wr
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {label}: {status}  N={len(valid)}  WR={pct(wr)}")
        return passed

    p_bear = assess(bear_lkz, "BEAR_OB LKZ (13:30–14:30)", PASS_WR, PASS_N)
    p_bull = assess(bull_lkz, "BULL_OB LKZ (13:30–14:30)", PASS_WR, PASS_N)

    # Concentration check
    conc_bear = (bear_lkz_wr is not None and bear_non_lkz_wr is not None
                 and bear_non_lkz_wr > 0
                 and bear_lkz_wr / bear_non_lkz_wr >= CONCENTRATION)
    conc_bull = (bull_lkz_wr is not None and bull_non_lkz_wr is not None
                 and bull_non_lkz_wr > 0
                 and bull_lkz_wr / bull_non_lkz_wr >= CONCENTRATION)

    print(f"  BEAR_OB LKZ edge concentration: {'✅ YES' if conc_bear else '❌ NO'}")
    print(f"  BULL_OB LKZ edge concentration: {'✅ YES' if conc_bull else '❌ NO'}")

    print()
    if (p_bear or p_bull) and (conc_bear or conc_bull):
        verdict = "PASS — LKZ concentrates AFTERNOON edge. ENH candidate: add london_kill_zone boolean time-gate to market state."
    elif p_bear or p_bull:
        verdict = "PARTIAL — LKZ shows edge but not clearly concentrated vs non-LKZ AFTERNOON."
    elif conc_bear or conc_bull:
        verdict = "PARTIAL — LKZ is more concentrated than non-LKZ but absolute WR below threshold."
    else:
        verdict = "FAIL — London Kill Zone does not concentrate the AFTERNOON OB edge."
    print(f"  OVERALL VERDICT: {verdict}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 37 — London Kill Zone Isolation                 ║")
    print("║  Session 11 · 2026-04-28 · MERDIAN                         ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("Parameters:")
    print("  LKZ window    : 13:30–14:30 IST (London open = 08:00–09:00 BST)")
    print("  Non-LKZ       : 14:30–15:30 IST (post-kill-zone fade)")
    print(f"  Pass criteria : WR >= {pct(PASS_WR)}, N >= {PASS_N}")
    print(f"  Concentration : LKZ WR >= {CONCENTRATION}x non-LKZ WR")
    print("  Note          : Baseline WR expected ~50% (all unfiltered signals)")
    print("                  Looking for RELATIVE concentration, not absolute compendium WR")
    print()

    signals = fetch_afternoon_signals()
    if not signals:
        print("NO SIGNALS FOUND.")
        sys.exit(1)

    print_results(signals)


if __name__ == "__main__":
    main()
