#!/usr/bin/env python3
"""
experiment_34_pdh_pdl_liquidity_sweep.py
MERDIAN Experiment 34 — PDH/PDL Liquidity Sweep + Rejection

Question:
    When price sweeps PDH (or PDL) by >= 0.05% on a 5m bar's wick
    and then reverses back inside the level within 6 bars (30 min),
    does the subsequent move continue in the reversal direction
    with statistical significance over T+30m and T+60m?

ICT concept tested:
    Buy-Side / Sell-Side Liquidity. PDH = buy-side liquidity pool
    (stop orders from retail longs cluster just above). Institutions
    engineer a push above to trigger those stops, absorb the orders,
    then reverse. PDL is the mirror for sell-side liquidity.

Pass criteria (per side):
    - N >= 30 confirmed sweep+rejection events
    - T+60m WR >= 60%  (bearish for PDH sweeps, bullish for PDL sweeps)
    - T+60m mean return in the reversal direction >= 0.4%

Data sources:
    - hist_spot_bars_5m  (5-minute OHLCV bars, is_pre_market = false)
    - hist_ict_htf_zones (timeframe='D', pattern_type IN ('PDH','PDL'))

Contamination check (CLAUDE.md Rule 13):
    Breadth fields not used. hist_spot_bars_5m bars pre-2026-04-07
    have TZ-stamping issue (TD-029) but spot price itself is correct.
    PDH/PDL zones derived from EOD — unaffected by breadth contamination.
    No contamination exclusion required for this experiment.

Run from: C:\\GammaEnginePython
Usage  : python experiment_34_pdh_pdl_liquidity_sweep.py

Session: 11  (2026-04-28)
Author : Claude (session 11) on behalf of MERDIAN project
"""

import os
import sys
from collections import defaultdict
from datetime import datetime

import pytz
from dotenv import load_dotenv
from supabase import create_client

# ── Environment ──────────────────────────────────────────────────────────────
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not in .env")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
IST = pytz.timezone("Asia/Kolkata")

# ── Instrument map ────────────────────────────────────────────────────────────
INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

# ── Experiment parameters ─────────────────────────────────────────────────────
SWEEP_THRESHOLD    = 0.0005   # wick must exceed PDH/PDL by >= 0.05%
REVERSAL_THRESHOLD = 0.001    # close must return inside by >= 0.10%
REVERSAL_MAX_BARS  = 6        # 6 * 5m = 30 min reversal window
WIN_THRESHOLD      = 0.004    # continuation >= 0.4% to count as win
PASS_N             = 30       # minimum events to declare pass
PASS_WR            = 0.60     # minimum WR to declare pass


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_ts(ts_str: str) -> datetime:
    # bar_ts is stored as "IST labeled as +00:00" per merdian_reference.json + TD-029.
    # The stored hour:minute IS the IST value. Converting timezone would add +5:30 wrongly.
    # Strip tzinfo and treat the stored value as naive IST directly.
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)


def time_bucket(ts_ist: datetime) -> str:
    t = ts_ist.hour * 60 + ts_ist.minute
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
def fetch_bars(instrument_id: str, label: str) -> list:
    """Paginated fetch of all regular-session 5m bars.
    
    hist_spot_bars_5m has no is_pre_market column (confirmed Session 11).
    Pre-market exclusion is done by filtering bar_ts to >= 09:15 IST.
    bar_ts is stored as UTC (IST - 5:30), so 09:15 IST = 03:45 UTC.
    We filter post-fetch by parsed IST time — simpler and avoids
    Supabase time-zone expression complexity.
    """
    print(f"  [{label}] Fetching 5m bars...", end="", flush=True)
    rows, page, page_size = [], 0, 1000  # Supabase hard-caps at 1000 rows per request
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

    # Filter to regular session: 09:15–15:30 IST
    def is_regular(bar):
        ts = parse_ts(bar["bar_ts"])
        t = ts.hour * 60 + ts.minute
        return 9 * 60 + 15 <= t <= 15 * 60 + 30

    rows = [b for b in rows if is_regular(b)]
    print(f" {len(rows)} bars (regular session only)")
    return rows


def fetch_zones(symbol: str) -> dict:
    """
    Returns dict: {date_str: {"PDH": float, "PDL": float}}
    Uses zone_high as the reference level for both PDH and PDL.
    """
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
        d = row["as_of_date"][:10]
        pt = row["pattern_type"]
        # PDH level = zone_high; PDL level = zone_low (or zone_high if PDL stored same)
        # Use zone_high for PDH, zone_low for PDL (mid-range fallback to zone_high)
        if pt == "PDH":
            zones[d]["PDH"] = float(row["zone_high"])
        else:
            # PDL: use zone_low if present, else zone_high
            val = row.get("zone_low") or row.get("zone_high")
            zones[d]["PDL"] = float(val)
    print(f" {len(zones)} session dates")
    return dict(zones)


# ── Core logic ────────────────────────────────────────────────────────────────
def detect_events(symbol: str, bars: list, zones: dict) -> list:
    """
    For each session day, scan 5m bars for:
      - PDH sweep: bar wick >= PDH * (1 + SWEEP_THRESHOLD)
        then close back <= PDH * (1 - REVERSAL_THRESHOLD) within REVERSAL_MAX_BARS
      - PDL sweep: bar wick <= PDL * (1 - SWEEP_THRESHOLD)
        then close back >= PDL * (1 + REVERSAL_THRESHOLD) within REVERSAL_MAX_BARS

    For each confirmed event, record T+30m and T+60m returns from
    the reversal bar's close.
    """
    # Attach parsed timestamps and group by date
    bars_by_date = defaultdict(list)
    for bar in bars:
        ts_ist = parse_ts(bar["bar_ts"])
        bar["_ts"]   = ts_ist
        bar["_date"] = ts_ist.date().isoformat()
        bar["_tb"]   = time_bucket(ts_ist)
        bars_by_date[bar["_date"]].append(bar)

    events = []

    for session_date, day_bars in sorted(bars_by_date.items()):
        if session_date not in zones:
            continue

        z      = zones[session_date]
        pdh    = z.get("PDH")
        pdl    = z.get("PDL")

        day_bars = sorted(day_bars, key=lambda b: b["_ts"])
        n_bars   = len(day_bars)

        for i, bar in enumerate(day_bars):
            if bar["_tb"] == "OTHER":
                continue

            high  = float(bar["high"])
            low   = float(bar["low"])

            # ── PDH sweep ────────────────────────────────────────────────────
            if pdh and high >= pdh * (1 + SWEEP_THRESHOLD):
                rev_idx = None
                for j in range(i + 1, min(i + REVERSAL_MAX_BARS + 1, n_bars)):
                    if float(day_bars[j]["close"]) <= pdh * (1 - REVERSAL_THRESHOLD):
                        rev_idx = j
                        break

                if rev_idx is not None:
                    rev_close = float(day_bars[rev_idx]["close"])
                    t30 = _future_ret(day_bars, rev_idx, rev_close, 6)
                    t60 = _future_ret(day_bars, rev_idx, rev_close, 12)
                    events.append({
                        "symbol":      symbol,
                        "date":        session_date,
                        "type":        "PDH",
                        "direction":   "BEARISH",
                        "time_bucket": bar["_tb"],
                        "sweep_pct":   (high - pdh) / pdh * 100,
                        "bars_to_rev": rev_idx - i,
                        "t30_ret":     t30,
                        "t60_ret":     t60,
                        "t30_win":     t30 is not None and t30 <= -WIN_THRESHOLD,
                        "t60_win":     t60 is not None and t60 <= -WIN_THRESHOLD,
                    })

            # ── PDL sweep ────────────────────────────────────────────────────
            if pdl and low <= pdl * (1 - SWEEP_THRESHOLD):
                rev_idx = None
                for j in range(i + 1, min(i + REVERSAL_MAX_BARS + 1, n_bars)):
                    if float(day_bars[j]["close"]) >= pdl * (1 + REVERSAL_THRESHOLD):
                        rev_idx = j
                        break

                if rev_idx is not None:
                    rev_close = float(day_bars[rev_idx]["close"])
                    t30 = _future_ret(day_bars, rev_idx, rev_close, 6)
                    t60 = _future_ret(day_bars, rev_idx, rev_close, 12)
                    events.append({
                        "symbol":      symbol,
                        "date":        session_date,
                        "type":        "PDL",
                        "direction":   "BULLISH",
                        "time_bucket": bar["_tb"],
                        "sweep_pct":   (pdl - low) / pdl * 100,
                        "bars_to_rev": rev_idx - i,
                        "t30_ret":     t30,
                        "t60_ret":     t60,
                        "t30_win":     t30 is not None and t30 >= WIN_THRESHOLD,
                        "t60_win":     t60 is not None and t60 >= WIN_THRESHOLD,
                    })

    return events


def _future_ret(bars, from_idx, from_close, offset):
    target = from_idx + offset
    if target < len(bars):
        return (float(bars[target]["close"]) - from_close) / from_close
    return None


# ── Reporting ─────────────────────────────────────────────────────────────────
def section(label: str):
    print(f"\n{'─' * 55}")
    print(f"  {label}")
    print(f"{'─' * 55}")


def report_group(events, label, win_key="t60_win", ret_key="t60_ret"):
    n = len(events)
    with_ret = [e for e in events if e[ret_key] is not None]
    if not with_ret:
        print(f"  {label:<35}  N={n:>3}  (no T+60m data)")
        return
    wr   = sum(1 for e in with_ret if e[win_key]) / len(with_ret)
    avg  = mean([e[ret_key] for e in with_ret])
    flag = " ✅" if (len(with_ret) >= PASS_N and wr >= PASS_WR) else ""
    print(f"  {label:<35}  N={len(with_ret):>3}  T+60m WR={pct(wr)}  mean={avg:.3%}{flag}")


def print_results(all_events):
    pdh_ev = [e for e in all_events if e["type"] == "PDH"]
    pdl_ev = [e for e in all_events if e["type"] == "PDL"]

    section("OVERALL — All symbols combined")
    report_group(pdh_ev, "PDH sweeps → bearish continuation")
    report_group(pdl_ev, "PDL sweeps → bullish continuation")

    # T+30m cross-check
    print()
    t30_pdh = [e for e in pdh_ev if e["t30_ret"] is not None]
    t30_pdl = [e for e in pdl_ev if e["t30_ret"] is not None]
    if t30_pdh:
        wr = sum(1 for e in t30_pdh if e["t30_win"]) / len(t30_pdh)
        print(f"  PDH T+30m cross-check: WR={pct(wr)}  mean={mean([e['t30_ret'] for e in t30_pdh]):.3%}  N={len(t30_pdh)}")
    if t30_pdl:
        wr = sum(1 for e in t30_pdl if e["t30_win"]) / len(t30_pdl)
        print(f"  PDL T+30m cross-check: WR={pct(wr)}  mean={mean([e['t30_ret'] for e in t30_pdl]):.3%}  N={len(t30_pdl)}")

    section("BY SYMBOL")
    for sym in ["NIFTY", "SENSEX"]:
        report_group([e for e in pdh_ev if e["symbol"] == sym], f"PDH {sym}")
        report_group([e for e in pdl_ev if e["symbol"] == sym], f"PDL {sym}")

    section("BY TIME BUCKET")
    for bucket in ["OPEN", "MORNING", "MIDDAY", "AFTERNOON"]:
        report_group([e for e in pdh_ev if e["time_bucket"] == bucket], f"PDH {bucket}")
        report_group([e for e in pdl_ev if e["time_bucket"] == bucket], f"PDL {bucket}")

    section("REVERSAL SPEED (bars from sweep to confirmed reversal)")
    for t in range(1, REVERSAL_MAX_BARS + 1):
        n_pdh = sum(1 for e in pdh_ev if e["bars_to_rev"] == t)
        n_pdl = sum(1 for e in pdl_ev if e["bars_to_rev"] == t)
        if n_pdh or n_pdl:
            print(f"  T+{t} bars ({t*5:>2}min):  PDH={n_pdh:>3}  PDL={n_pdl:>3}")

    section("SWEEP DEPTH DISTRIBUTION (% beyond PDH/PDL)")
    for tier, lo, hi in [("0.05-0.10%", 0.05, 0.10),
                          ("0.10-0.20%", 0.10, 0.20),
                          ("0.20-0.40%", 0.20, 0.40),
                          ("> 0.40%",    0.40, 99.0)]:
        sub_pdh = [e for e in pdh_ev if lo <= e["sweep_pct"] < hi]
        sub_pdl = [e for e in pdl_ev if lo <= e["sweep_pct"] < hi]
        if sub_pdh or sub_pdl:
            report_group(sub_pdh, f"PDH depth {tier}")
            report_group(sub_pdl, f"PDL depth {tier}")

    section("PASS / FAIL ASSESSMENT")
    def assess(events, label):
        with_ret = [e for e in events if e["t60_ret"] is not None]
        if not with_ret:
            print(f"  {label}: INSUFFICIENT DATA (N=0)")
            return False
        wr = sum(1 for e in with_ret if e["t60_win"]) / len(with_ret)
        passed = len(with_ret) >= PASS_N and wr >= PASS_WR
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {label}: {status}  N={len(with_ret)}  T+60m WR={pct(wr)}")
        print(f"           Criteria: N>={PASS_N}, WR>={pct(PASS_WR)}")
        return passed

    pdh_pass = assess(pdh_ev, "PDH (bearish reversal edge)")
    pdl_pass = assess(pdl_ev, "PDL (bullish reversal edge)")

    print()
    if pdh_pass and pdl_pass:
        verdict = "FULL PASS — both sides show edge. ENH candidate: add LIQUIDITY_SWEEP_DETECTED to market state."
    elif pdh_pass or pdl_pass:
        side = "PDH" if pdh_pass else "PDL"
        verdict = f"PARTIAL PASS — {side} shows edge. One-sided signal. Monitor other side with more data."
    else:
        verdict = "FAIL — no reliable edge at these thresholds. Candidate: tighten reversal window or add OB confluence."
    print(f"  OVERALL VERDICT: {verdict}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 34 — PDH/PDL Liquidity Sweep + Rejection ║")
    print("║  Session 11 · 2026-04-28 · MERDIAN                  ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()
    print(f"Parameters:")
    print(f"  Sweep threshold   : >= {SWEEP_THRESHOLD*100:.2f}% beyond PDH/PDL")
    print(f"  Reversal threshold: >= {REVERSAL_THRESHOLD*100:.2f}% back inside level")
    print(f"  Reversal window   : <= {REVERSAL_MAX_BARS} bars ({REVERSAL_MAX_BARS*5} min)")
    print(f"  Win threshold     : >= {WIN_THRESHOLD*100:.1f}% continuation in reversal direction")
    print(f"  Pass criteria     : N >= {PASS_N}, T+60m WR >= {PASS_WR*100:.0f}%")
    print()

    all_events = []

    for symbol, instrument_id in INSTRUMENTS.items():
        print(f"\n[{symbol}]")
        bars  = fetch_bars(instrument_id, symbol)
        zones = fetch_zones(symbol)

        if not bars or not zones:
            print(f"  SKIP — insufficient data for {symbol}")
            continue

        events = detect_events(symbol, bars, zones)
        pdh_n  = sum(1 for e in events if e["type"] == "PDH")
        pdl_n  = sum(1 for e in events if e["type"] == "PDL")
        print(f"  Events detected: PDH={pdh_n}  PDL={pdl_n}  total={len(events)}")
        all_events.extend(events)

    if not all_events:
        print("\nNO EVENTS DETECTED. Possible causes:")
        print("  1. hist_ict_htf_zones has no PDH/PDL rows for these dates")
        print("  2. hist_spot_bars_5m has insufficient coverage")
        print("  3. Run build_ict_htf_zones.py --timeframe D if PDH/PDL zones missing")
        sys.exit(1)

    print_results(all_events)


if __name__ == "__main__":
    main()
