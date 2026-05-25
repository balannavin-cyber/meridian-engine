#!/usr/bin/env python3
"""
experiment_35_po3_first_sweep_session_bias.py
MERDIAN Experiment 35 — First PDH/PDL Sweep as PO3 Session Bias

Question:
    When the FIRST touch-and-rejection of PDH (or PDL) occurs in the
    OPEN or MORNING window (09:15–11:30 IST), does the session close
    in the opposite direction to the sweep with WR >= 60%?

ICT concept tested:
    Power of Three (PO3) / AMD Cycle:
      Accumulation  09:15–09:45 — tight range, SM positioning
      Manipulation  09:45–11:30 — fake move, sweeps BSL/SSL
      Distribution  11:30–15:30 — real move, opposite to manipulation

    The first morning sweep of PDH = manipulation leg upward.
    ICT predicts the session then closes bearish (below session open).
    The first morning sweep of PDL = manipulation leg downward.
    ICT predicts the session then closes bullish (above session open).

Key difference from Experiment 34:
    Exp 34 tested ALL intraday PDH/PDL sweeps (~0.73/session) → noise.
    Exp 35 tests FIRST morning sweep only (~0.3/session estimated)
    and measures EOD outcome, not T+60m.

Pass criteria:
    - N >= 25 first-sweep events per side
    - EOD WR >= 60% in the predicted direction
      (bearish for PDH first-sweep; bullish for PDL first-sweep)

Data sources:
    - hist_spot_bars_5m
    - hist_ict_htf_zones (timeframe='D', pattern_type IN ('PDH','PDL'))

TD-029 workaround (confirmed Exp 34):
    bar_ts stored as IST labeled +00:00. Do NOT astimezone() — use
    replace(tzinfo=None) and treat stored value as naive IST directly.

Supabase pagination (confirmed Exp 34):
    Hard cap 1000 rows/request. page_size = 1000.

Run from: C:\\GammaEnginePython
Usage  : python experiment_35_po3_first_sweep_session_bias.py

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

# ── Instrument map ─────────────────────────────────────────────────────────────
INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

# ── Parameters ─────────────────────────────────────────────────────────────────
SWEEP_THRESHOLD    = 0.0005   # wick >= PDH/PDL * (1 ± threshold)
REVERSAL_THRESHOLD = 0.001    # close returns inside by >= 0.10%
REVERSAL_MAX_BARS  = 6        # 30 min reversal window
MANIPULATION_END   = (11, 30) # sweep must start before 11:30 IST
PASS_N             = 25
PASS_WR            = 0.60


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_ts(ts_str: str) -> datetime:
    # TD-029: bar_ts stored as IST labeled +00:00. Treat as naive IST directly.
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)


def bar_minutes(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def time_bucket(dt: datetime) -> str:
    t = bar_minutes(dt)
    if   9*60+15 <= t <  10*60:    return "OPEN"
    elif 10*60   <= t <  11*60+30: return "MORNING"
    elif 11*60+30 <= t < 13*60+30: return "MIDDAY"
    elif 13*60+30 <= t < 15*60+30: return "AFTERNOON"
    return "OTHER"


def pct(v: float) -> str:
    return f"{v:.1%}"


def mean(lst):
    return sum(lst) / len(lst) if lst else None


# ── Data fetchers ─────────────────────────────────────────────────────────────
def fetch_bars(instrument_id: str, label: str) -> dict:
    """Returns {date_str: [bars sorted by bar_ts]} for regular session only."""
    print(f"  [{label}] Fetching 5m bars...", end="", flush=True)
    rows, page, page_size = [], 0, 1000
    while True:
        resp = (
            supabase.table("hist_spot_bars_5m")
            .select("bar_ts,open,high,low,close")
            .eq("instrument_id", instrument_id)
            .order("bar_ts")
            .range(page, page + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        page += page_size

    # Parse and filter to regular session 09:15–15:30
    by_date = defaultdict(list)
    for bar in rows:
        dt = parse_ts(bar["bar_ts"])
        t  = bar_minutes(dt)
        if 9*60+15 <= t <= 15*60+30:
            bar["_dt"]   = dt
            bar["_date"] = dt.date().isoformat()
            bar["_tb"]   = time_bucket(dt)
            by_date[bar["_date"]].append(bar)

    # Sort each session
    for d in by_date:
        by_date[d].sort(key=lambda b: b["_dt"])

    total = sum(len(v) for v in by_date.values())
    print(f" {total} bars across {len(by_date)} sessions")
    return dict(by_date)


def fetch_zones(symbol: str) -> dict:
    """Returns {date_str: {'PDH': float, 'PDL': float}}."""
    print(f"  [{symbol}] Fetching D PDH/PDL zones...", end="", flush=True)
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
    print(f" {len(zones)} session dates")
    return dict(zones)


# ── Core detection ─────────────────────────────────────────────────────────────
def detect_first_sweeps(symbol: str, bars_by_date: dict, zones: dict) -> list:
    """
    For each session:
      - Find the FIRST bar whose wick sweeps PDH (or PDL)
        and which is confirmed reversed within REVERSAL_MAX_BARS.
      - The sweep bar must start before MANIPULATION_END (11:30 IST).
      - One event per level per session maximum.
      - Outcome: does EOD close (last bar close) beat session open?
    """
    events = []
    manip_cutoff = MANIPULATION_END[0] * 60 + MANIPULATION_END[1]

    for session_date in sorted(bars_by_date.keys()):
        if session_date not in zones:
            continue

        day_bars = bars_by_date[session_date]
        n        = len(day_bars)
        if n < 6:
            continue

        z   = zones[session_date]
        pdh = z.get("PDH")
        pdl = z.get("PDL")

        session_open = float(day_bars[0]["open"])
        session_eod  = float(day_bars[-1]["close"])
        session_ret  = (session_eod - session_open) / session_open

        pdh_found = False
        pdl_found = False

        for i, bar in enumerate(day_bars):
            t = bar_minutes(bar["_dt"])

            # Must be in manipulation window
            if t >= manip_cutoff:
                break

            high  = float(bar["high"])
            low   = float(bar["low"])

            # ── First PDH sweep ───────────────────────────────────────────────
            if not pdh_found and pdh and high >= pdh * (1 + SWEEP_THRESHOLD):
                # Look for reversal confirmation
                for j in range(i + 1, min(i + REVERSAL_MAX_BARS + 1, n)):
                    if float(day_bars[j]["close"]) <= pdh * (1 - REVERSAL_THRESHOLD):
                        # Confirmed first sweep + rejection
                        sweep_pct  = (high - pdh) / pdh * 100
                        bars_to_rev = j - i
                        eod_win    = session_ret < 0  # bearish EOD = win for PDH sweep
                        gap_pct    = (session_open - float(day_bars[0]["close"])) / float(day_bars[0]["close"]) if i == 0 else None

                        # Gap: today's open vs prior close (approximate via session_open vs PDH proximity)
                        # Use session return sign as gap proxy — positive open relative to PDH = gap-up context
                        gap_up = session_open >= pdh * 0.999

                        events.append({
                            "symbol":      symbol,
                            "date":        session_date,
                            "type":        "PDH",
                            "direction":   "BEARISH",
                            "time_bucket": bar["_tb"],
                            "sweep_bar_t": t,
                            "sweep_pct":   sweep_pct,
                            "bars_to_rev": bars_to_rev,
                            "session_ret": session_ret,
                            "eod_win":     eod_win,
                            "gap_up":      gap_up,
                        })
                        pdh_found = True
                        break

            # ── First PDL sweep ───────────────────────────────────────────────
            if not pdl_found and pdl and low <= pdl * (1 - SWEEP_THRESHOLD):
                for j in range(i + 1, min(i + REVERSAL_MAX_BARS + 1, n)):
                    if float(day_bars[j]["close"]) >= pdl * (1 + REVERSAL_THRESHOLD):
                        sweep_pct   = (pdl - low) / pdl * 100
                        bars_to_rev = j - i
                        eod_win     = session_ret > 0  # bullish EOD = win for PDL sweep
                        gap_down    = session_open <= pdl * 1.001

                        events.append({
                            "symbol":      symbol,
                            "date":        session_date,
                            "type":        "PDL",
                            "direction":   "BULLISH",
                            "time_bucket": bar["_tb"],
                            "sweep_bar_t": t,
                            "sweep_pct":   sweep_pct,
                            "bars_to_rev": bars_to_rev,
                            "session_ret": session_ret,
                            "eod_win":     eod_win,
                            "gap_up":      not gap_down,
                        })
                        pdl_found = True
                        break

            if pdh_found and pdl_found:
                break

    return events


# ── Reporting ─────────────────────────────────────────────────────────────────
def section(label: str):
    print(f"\n{'─' * 58}")
    print(f"  {label}")
    print(f"{'─' * 58}")


def report(events, label):
    n = len(events)
    if not events:
        print(f"  {label:<45}  N=  0")
        return
    wr  = sum(1 for e in events if e["eod_win"]) / n
    avg = mean([e["session_ret"] for e in events])
    flag = " ✅" if (n >= PASS_N and wr >= PASS_WR) else ""
    print(f"  {label:<45}  N={n:>3}  EOD WR={pct(wr)}  mean_ret={avg:.3%}{flag}")


def print_results(all_events):
    pdh = [e for e in all_events if e["type"] == "PDH"]
    pdl = [e for e in all_events if e["type"] == "PDL"]

    section("OVERALL — All symbols combined")
    report(pdh, "PDH first-sweep → bearish EOD")
    report(pdl, "PDL first-sweep → bullish EOD")

    section("BY SYMBOL")
    for sym in ["NIFTY", "SENSEX"]:
        report([e for e in pdh if e["symbol"] == sym], f"PDH {sym}")
        report([e for e in pdl if e["symbol"] == sym], f"PDL {sym}")

    section("BY TIME BUCKET OF SWEEP")
    for bucket in ["OPEN", "MORNING"]:
        report([e for e in pdh if e["time_bucket"] == bucket], f"PDH sweep in {bucket}")
        report([e for e in pdl if e["time_bucket"] == bucket], f"PDL sweep in {bucket}")

    section("BY GAP CONTEXT")
    report([e for e in pdh if e["gap_up"]],      "PDH sweep — gap-up session (open near PDH)")
    report([e for e in pdh if not e["gap_up"]],  "PDH sweep — gap-down / flat session")
    report([e for e in pdl if not e["gap_up"]],  "PDL sweep — gap-down session (open near PDL)")
    report([e for e in pdl if e["gap_up"]],      "PDL sweep — gap-up / flat session")

    section("BY SWEEP DEPTH")
    for lo, hi, label in [(0.05, 0.10, "0.05-0.10%"),
                           (0.10, 0.20, "0.10-0.20%"),
                           (0.20, 99.0, "> 0.20%")]:
        report([e for e in pdh if lo <= e["sweep_pct"] < hi], f"PDH depth {label}")
        report([e for e in pdl if lo <= e["sweep_pct"] < hi], f"PDL depth {label}")

    section("SESSION RETURN DISTRIBUTION (EOD wins)")
    for ev_list, label in [(pdh, "PDH"), (pdl, "PDL")]:
        wins  = [e["session_ret"] for e in ev_list if e["eod_win"]]
        loses = [e["session_ret"] for e in ev_list if not e["eod_win"]]
        if wins or loses:
            print(f"  {label} wins  N={len(wins):>3}  mean={mean(wins):.3%}" if wins else f"  {label} wins  N=  0")
            print(f"  {label} loses N={len(loses):>3}  mean={mean(loses):.3%}" if loses else f"  {label} loses N=  0")

    section("PASS / FAIL ASSESSMENT")
    def assess(events, label):
        if not events:
            print(f"  {label}: INSUFFICIENT DATA")
            return False
        wr = sum(1 for e in events if e["eod_win"]) / len(events)
        passed = len(events) >= PASS_N and wr >= PASS_WR
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {label}: {status}  N={len(events)}  EOD WR={pct(wr)}")
        print(f"           Criteria: N>={PASS_N}, WR>={pct(PASS_WR)}")
        return passed

    pdh_pass = assess(pdh, "PDH first-sweep → bearish EOD")
    pdl_pass = assess(pdl, "PDL first-sweep → bullish EOD")

    print()
    if pdh_pass and pdl_pass:
        verdict = "FULL PASS — PO3 manipulation detection has session-level edge. ENH candidate: add po3_session_bias to market state."
    elif pdh_pass or pdl_pass:
        side = "PDH" if pdh_pass else "PDL"
        verdict = f"PARTIAL PASS — {side} side has edge. One-sided session bias signal."
    else:
        verdict = "FAIL — first morning sweep alone insufficient. Next: add OB confluence at sweep level or tighten to OPEN window only."
    print(f"  OVERALL VERDICT: {verdict}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 35 — First PDH/PDL Sweep as PO3 Session Bias ║")
    print("║  Session 11 · 2026-04-28 · MERDIAN                      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    print("Parameters:")
    print(f"  Sweep threshold     : >= {SWEEP_THRESHOLD*100:.2f}% beyond PDH/PDL")
    print(f"  Reversal threshold  : >= {REVERSAL_THRESHOLD*100:.2f}% back inside level")
    print(f"  Reversal window     : <= {REVERSAL_MAX_BARS} bars ({REVERSAL_MAX_BARS*5} min)")
    print(f"  Manipulation window : sweep must start before {MANIPULATION_END[0]:02d}:{MANIPULATION_END[1]:02d} IST")
    print(f"  Outcome             : EOD close vs session open (full session direction)")
    print(f"  Pass criteria       : N >= {PASS_N}, EOD WR >= {pct(PASS_WR)}")
    print(f"  Key difference      : FIRST sweep per session only (not all sweeps)")
    print()

    all_events = []
    for symbol, instrument_id in INSTRUMENTS.items():
        print(f"\n[{symbol}]")
        bars_by_date = fetch_bars(instrument_id, symbol)
        zones        = fetch_zones(symbol)
        if not bars_by_date or not zones:
            print(f"  SKIP — insufficient data")
            continue
        events = detect_first_sweeps(symbol, bars_by_date, zones)
        pdh_n  = sum(1 for e in events if e["type"] == "PDH")
        pdl_n  = sum(1 for e in events if e["type"] == "PDL")
        print(f"  First sweeps detected: PDH={pdh_n}  PDL={pdl_n}  total={len(events)}")
        all_events.extend(events)

    if not all_events:
        print("\nNO FIRST-SWEEP EVENTS DETECTED.")
        print("  Possible: PDH/PDL zones missing for these dates.")
        print("  Run: build_ict_htf_zones.py --timeframe D")
        sys.exit(1)

    print_results(all_events)


if __name__ == "__main__":
    main()
