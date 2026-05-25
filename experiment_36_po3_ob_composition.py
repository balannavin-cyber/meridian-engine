#!/usr/bin/env python3
"""
experiment_36_po3_ob_composition.py
MERDIAN Experiment 36 — PO3 Session Bias × OB Pattern Composition

Question:
    When a BEAR_OB fires on a session where a PDH first-sweep
    established a bearish PO3 session bias, is the T+30m WR
    materially higher than BEAR_OB alone?

    Mirror: BULL_OB on a PDL first-sweep bullish session.

Origin:
    Experiment 35 showed:
      - PDH first-sweep (OPEN, gap-up) → 74.3% bearish EOD WR
      - PDL first-sweep (OPEN, gap-down) → 67.6% bullish EOD WR
    Compendium baseline (Exp 15 re-run, Session 10):
      - BEAR_OB standalone → ~92% WR (MEDIUM context)
      - BULL_OB standalone → ~84% WR (MEDIUM context)

    Hypothesis: PO3 bias is an additive filter that:
      (a) Increases WR when aligned with OB direction
      (b) Provides a WARNING when OB fires AGAINST PO3 bias

Pass criteria:
    - BEAR_OB + PO3-BEARISH: WR >= 85%, N >= 15
    - BULL_OB + PO3-BULLISH: WR >= 75%, N >= 15
    - BEAR_OB + PO3-BULLISH (counter-bias): WR <= 60% (shows bias reduces WR)
    - BULL_OB + PO3-BEARISH (counter-bias): WR <= 60%

Data sources:
    - hist_pattern_signals   (BEAR_OB, BULL_OB detections with T+30m outcomes)
    - hist_spot_bars_5m      (to detect PO3 first-sweep per session)
    - hist_ict_htf_zones     (timeframe='D', PDH/PDL)

Methodology:
    Step 1: Run PO3 first-sweep detection for all sessions (Exp 35 logic).
            Classify each session as: PO3_BEARISH / PO3_BULLISH / PO3_NONE.
            Use OPEN window + gap context for highest fidelity:
              PO3_BEARISH = PDH first-sweep before 10:00 IST + gap-up context
              PO3_BULLISH = PDL first-sweep before 10:00 IST + gap-down context
              PO3_NONE    = no qualifying first-sweep

    Step 2: For each BEAR_OB / BULL_OB in hist_pattern_signals,
            look up the session's PO3 label.
            Split into: aligned / counter / neutral groups.

    Step 3: Compare T+30m WR across groups.

TD-029 / pagination fixes from Exp 34 baked in.

Run from: C:\\GammaEnginePython
Usage  : python experiment_36_po3_ob_composition.py

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

INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

# ── PO3 parameters (best-performing config from Exp 35) ──────────────────────
SWEEP_THRESHOLD    = 0.0005
REVERSAL_THRESHOLD = 0.001
REVERSAL_MAX_BARS  = 6
PO3_WINDOW_END     = (10, 0)    # OPEN window only — 09:15-10:00 IST

# ── Pass criteria ─────────────────────────────────────────────────────────────
PASS_N_ALIGNED  = 15
PASS_WR_BEAR_OB = 0.85
PASS_WR_BULL_OB = 0.75
COUNTER_WR_CAP  = 0.60


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_ts(ts_str: str) -> datetime:
    # TD-029: IST labeled as +00:00; treat as naive IST directly.
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)


def bar_minutes(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def pct(v: float) -> str:
    return f"{v:.1%}"


def mean(lst):
    return sum(lst) / len(lst) if lst else None


# ── Step 1: Build PO3 session map ─────────────────────────────────────────────
def fetch_bars_by_date(instrument_id: str, label: str) -> dict:
    print(f"  [{label}] Fetching 5m bars...", end="", flush=True)
    rows, page = [], 0
    while True:
        resp = (
            supabase.table("hist_spot_bars_5m")
            .select("bar_ts,open,high,low,close")
            .eq("instrument_id", instrument_id)
            .order("bar_ts")
            .range(page, page + 999)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < 1000:
            break
        page += 1000

    by_date = defaultdict(list)
    for bar in rows:
        dt = parse_ts(bar["bar_ts"])
        t  = bar_minutes(dt)
        if 9*60+15 <= t <= 15*60+30:
            bar["_dt"]   = dt
            bar["_date"] = dt.date().isoformat()
            by_date[bar["_date"]].append(bar)

    for d in by_date:
        by_date[d].sort(key=lambda b: b["_dt"])

    total = sum(len(v) for v in by_date.values())
    print(f" {total} bars / {len(by_date)} sessions")
    return dict(by_date)


def fetch_zones(symbol: str) -> dict:
    print(f"  [{symbol}] Fetching D zones...", end="", flush=True)
    resp = (
        supabase.table("hist_ict_htf_zones")
        .select("as_of_date,pattern_type,zone_high,zone_low")
        .eq("symbol", symbol)
        .eq("timeframe", "D")
        .in_("pattern_type", ["PDH", "PDL"])
        .execute()
    )
    zones = defaultdict(dict)
    for row in (resp.data or []):
        d  = row["as_of_date"][:10]
        pt = row["pattern_type"]
        if pt == "PDH":
            zones[d]["PDH"] = float(row["zone_high"])
        else:
            val = row.get("zone_low") or row.get("zone_high")
            zones[d]["PDL"] = float(val)
    print(f" {len(zones)} dates")
    return dict(zones)


def build_po3_session_map(symbol: str, bars_by_date: dict, zones: dict) -> dict:
    """
    Returns {date_str: 'PO3_BEARISH' | 'PO3_BULLISH' | 'PO3_NONE'}
    Uses OPEN window (09:15-10:00) + gap context for highest fidelity.
    """
    cutoff = PO3_WINDOW_END[0] * 60 + PO3_WINDOW_END[1]
    session_map = {}

    for session_date in sorted(bars_by_date.keys()):
        if session_date not in zones:
            session_map[session_date] = "PO3_NONE"
            continue

        day_bars = bars_by_date[session_date]
        if len(day_bars) < 4:
            session_map[session_date] = "PO3_NONE"
            continue

        z   = zones[session_date]
        pdh = z.get("PDH")
        pdl = z.get("PDL")
        session_open = float(day_bars[0]["open"])

        label     = "PO3_NONE"
        pdh_found = False
        pdl_found = False

        for i, bar in enumerate(day_bars):
            t = bar_minutes(bar["_dt"])
            if t >= cutoff:
                break

            high = float(bar["high"])
            low  = float(bar["low"])
            n    = len(day_bars)

            if not pdh_found and pdh and high >= pdh * (1 + SWEEP_THRESHOLD):
                for j in range(i + 1, min(i + REVERSAL_MAX_BARS + 1, n)):
                    if float(day_bars[j]["close"]) <= pdh * (1 - REVERSAL_THRESHOLD):
                        gap_up = session_open >= pdh * 0.999
                        if gap_up:
                            label = "PO3_BEARISH"
                        pdh_found = True
                        break

            if not pdl_found and pdl and low <= pdl * (1 - SWEEP_THRESHOLD):
                for j in range(i + 1, min(i + REVERSAL_MAX_BARS + 1, n)):
                    if float(day_bars[j]["close"]) >= pdl * (1 + REVERSAL_THRESHOLD):
                        gap_down = session_open <= pdl * 1.001
                        if gap_down and label == "PO3_NONE":
                            label = "PO3_BULLISH"
                        pdl_found = True
                        break

            if pdh_found and pdl_found:
                break

        session_map[session_date] = label

    return session_map


# ── Step 2: Fetch OB signals from hist_pattern_signals ────────────────────────
def fetch_ob_signals(symbol: str) -> list:
    print(f"  [{symbol}] Fetching OB signals...", end="", flush=True)
    rows, page = [], 0
    while True:
        resp = (
            supabase.table("hist_pattern_signals")
            .select("trade_date,pattern_type,session,win_30m,gamma_regime,tier")
            .eq("symbol", symbol)
            .in_("pattern_type", ["BEAR_OB", "BULL_OB"])
            .order("trade_date")
            .range(page, page + 999)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < 1000:
            break
        page += 1000
    print(f" {len(rows)} signals")
    return rows


# ── Step 3: Compose and report ────────────────────────────────────────────────
def section(label: str):
    print(f"\n{'─' * 62}")
    print(f"  {label}")
    print(f"{'─' * 62}")


def report(signals, label, pass_wr=None):
    valid = [s for s in signals if s.get("win_30m") is not None]
    n     = len(valid)
    if not valid:
        print(f"  {label:<52}  N=  0  (no outcome data)")
        return None
    wr  = sum(1 for s in valid if s["win_30m"]) / n
    flag = ""
    if pass_wr is not None:
        flag = " ✅" if wr >= pass_wr else " ❌"
    print(f"  {label:<52}  N={n:>3}  T+30m WR={pct(wr)}{flag}")
    return wr


def print_results(all_signals, all_po3_maps):
    # Attach PO3 label to each signal
    for sig in all_signals:
        sym  = sig["symbol"]
        date = sig["trade_date"]
        sig["po3"] = all_po3_maps.get(sym, {}).get(date, "PO3_NONE")

    bear = [s for s in all_signals if s["pattern_type"] == "BEAR_OB"]
    bull = [s for s in all_signals if s["pattern_type"] == "BULL_OB"]

    section("BASELINE — OB signals regardless of PO3 (replication check)")
    report(bear, "BEAR_OB all")
    report(bull, "BULL_OB all")

    section("PRIMARY — OB aligned with PO3 session bias")
    bear_aligned = [s for s in bear if s["po3"] == "PO3_BEARISH"]
    bull_aligned = [s for s in bull if s["po3"] == "PO3_BULLISH"]
    report(bear_aligned, "BEAR_OB + PO3_BEARISH (aligned)", pass_wr=PASS_WR_BEAR_OB)
    report(bull_aligned, "BULL_OB + PO3_BULLISH (aligned)", pass_wr=PASS_WR_BULL_OB)

    section("COUNTER — OB firing AGAINST PO3 bias (should be worse)")
    bear_counter = [s for s in bear if s["po3"] == "PO3_BULLISH"]
    bull_counter = [s for s in bull if s["po3"] == "PO3_BEARISH"]
    report(bear_counter, "BEAR_OB + PO3_BULLISH (counter-bias)", pass_wr=COUNTER_WR_CAP)
    report(bull_counter, "BULL_OB + PO3_BEARISH (counter-bias)", pass_wr=COUNTER_WR_CAP)

    section("NO PO3 LABEL — OB on neutral sessions")
    report([s for s in bear if s["po3"] == "PO3_NONE"], "BEAR_OB + PO3_NONE")
    report([s for s in bull if s["po3"] == "PO3_NONE"], "BULL_OB + PO3_NONE")

    section("BY SYMBOL — Aligned only")
    for sym in ["NIFTY", "SENSEX"]:
        report([s for s in bear_aligned if s["symbol"] == sym],
               f"BEAR_OB + PO3_BEARISH [{sym}]", pass_wr=PASS_WR_BEAR_OB)
        report([s for s in bull_aligned if s["symbol"] == sym],
               f"BULL_OB + PO3_BULLISH [{sym}]", pass_wr=PASS_WR_BULL_OB)

    section("BY TIER — Aligned only")
    for tier in ["TIER1", "TIER2", "TIER3"]:
        sub_bear = [s for s in bear_aligned if s.get("tier") == tier]
        sub_bull = [s for s in bull_aligned if s.get("tier") == tier]
        if sub_bear:
            report(sub_bear, f"BEAR_OB + PO3_BEARISH + {tier}")
        if sub_bull:
            report(sub_bull, f"BULL_OB + PO3_BULLISH + {tier}")

    section("BY TIME ZONE — Aligned only")
    for tz in ["OPEN", "MORNING", "MIDDAY", "AFTERNOON"]:
        sub_bear = [s for s in bear_aligned if s.get("session") == tz]
        sub_bull = [s for s in bull_aligned if s.get("session") == tz]
        if sub_bear:
            report(sub_bear, f"BEAR_OB + PO3_BEARISH + TZ={tz}")
        if sub_bull:
            report(sub_bull, f"BULL_OB + PO3_BULLISH + TZ={tz}")

    section("PO3 SESSION MAP SUMMARY")
    for sym in ["NIFTY", "SENSEX"]:
        sm = all_po3_maps.get(sym, {})
        n_bear = sum(1 for v in sm.values() if v == "PO3_BEARISH")
        n_bull = sum(1 for v in sm.values() if v == "PO3_BULLISH")
        n_none = sum(1 for v in sm.values() if v == "PO3_NONE")
        total  = len(sm)
        print(f"  {sym}: {total} sessions → PO3_BEARISH={n_bear}  PO3_BULLISH={n_bull}  PO3_NONE={n_none}")

    section("PASS / FAIL ASSESSMENT")
    def assess(signals, label, pass_wr, n_req):
        valid = [s for s in signals if s.get("win_30m") is not None]
        if not valid:
            print(f"  {label}: INSUFFICIENT DATA (N=0)")
            return False
        wr = sum(1 for s in valid if s["win_30m"]) / len(valid)
        passed = len(valid) >= n_req and wr >= pass_wr
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {label}: {status}  N={len(valid)}  WR={pct(wr)}")
        return passed

    p1 = assess(bear_aligned, "BEAR_OB + PO3_BEARISH aligned", PASS_WR_BEAR_OB, PASS_N_ALIGNED)
    p2 = assess(bull_aligned, "BULL_OB + PO3_BULLISH aligned", PASS_WR_BULL_OB, PASS_N_ALIGNED)

    print()
    if p1 and p2:
        verdict = "FULL PASS — PO3 bias is a valid additive filter for both OB directions. ENH candidate: po3_session_bias field in market_state."
    elif p1 or p2:
        side = "BEAR_OB" if p1 else "BULL_OB"
        verdict = f"PARTIAL PASS — {side} benefits from PO3 alignment. One-sided enhancement."
    else:
        verdict = "FAIL — PO3 session bias does not materially improve OB WR at current thresholds."
    print(f"  OVERALL VERDICT: {verdict}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 36 — PO3 Session Bias × OB Pattern Composition  ║")
    print("║  Session 11 · 2026-04-28 · MERDIAN                         ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("Parameters:")
    print(f"  PO3 window          : OPEN only (09:15–{PO3_WINDOW_END[0]:02d}:{PO3_WINDOW_END[1]:02d} IST)")
    print(f"  Gap context required: YES (gap-up for PDH / gap-down for PDL)")
    print(f"  OB outcome metric   : T+30m win_30m from hist_pattern_signals")
    print(f"  Pass (aligned)      : N>={PASS_N_ALIGNED}, BEAR_OB WR>={pct(PASS_WR_BEAR_OB)}, BULL_OB WR>={pct(PASS_WR_BULL_OB)}")
    print(f"  Counter signal check: WR<={pct(COUNTER_WR_CAP)} confirms bias degrades counter-direction OBs")
    print()

    all_po3_maps = {}
    all_signals  = []

    for symbol, instrument_id in INSTRUMENTS.items():
        print(f"\n[{symbol}]")
        bars_by_date = fetch_bars_by_date(instrument_id, symbol)
        zones        = fetch_zones(symbol)

        print(f"  [{symbol}] Building PO3 session map...", end="", flush=True)
        po3_map = build_po3_session_map(symbol, bars_by_date, zones)
        all_po3_maps[symbol] = po3_map
        n_labeled = sum(1 for v in po3_map.values() if v != "PO3_NONE")
        print(f" {n_labeled} labelled sessions")

        signals = fetch_ob_signals(symbol)
        for s in signals:
            s["symbol"] = symbol
        all_signals.extend(signals)

    if not all_signals:
        print("\nNO OB SIGNALS FOUND in hist_pattern_signals.")
        sys.exit(1)

    print_results(all_signals, all_po3_maps)


if __name__ == "__main__":
    main()
