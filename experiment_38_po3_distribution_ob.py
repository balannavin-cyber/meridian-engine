#!/usr/bin/env python3
"""
experiment_38_po3_distribution_ob.py
MERDIAN Experiment 38 — OB in Distribution Leg on PO3-Biased Sessions

Origin:
    35B showed: PO3 sweep edge is BACK-LOADED (EOD 75.9%, T+30m only 27.6%).
    The sweep confirms session direction but the move unfolds via the
    distribution leg (11:30–15:30 IST), not immediately.
    The correct trade is: wait for PO3 bias to form in OPEN window,
    then enter on first BEAR_OB or BULL_OB that aligns in MIDDAY/AFTERNOON.

    This tests the complete trade thesis end-to-end:
    PO3 sweep (OPEN) → wait → OB fires in distribution (MIDDAY/AFTERNOON) → execute

Question:
    When a BEAR_OB fires in MIDDAY or AFTERNOON on a session where the
    OPEN window established a PDH first-sweep bearish bias (35C filtered config),
    is the T+30m WR materially higher than BEAR_OB in those sessions without bias?

    Mirror for BULL_OB on PDL-sweep bullish sessions.

Pass criteria:
    - BEAR_OB + PO3_BEARISH MIDDAY/AFTERNOON: WR >= 65%, N >= 10
    - Lift vs baseline BEAR_OB MIDDAY/AFTERNOON >= 10pp

Data:
    - hist_pattern_signals (OB signals with session, win_30m)
    - hist_spot_bars_5m + hist_ict_htf_zones (to build PO3 session map)

Filters: same 35C filtered config (gap cap + depth exclusion)

TD-029 / pagination: fixes baked in.

Run from: C:\\GammaEnginePython
Usage  : python experiment_38_po3_distribution_ob.py
Session: 11  (2026-04-28)
"""

import os
import sys
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: missing env vars"); sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

# 35C filters
SWEEP_THRESHOLD    = 0.0005
REVERSAL_THRESHOLD = 0.001
REVERSAL_MAX_BARS  = 6
OPEN_END           = (10, 0)
PDH_GAP_MAX        = 0.005
PDH_DEPTH_BLOCK_LO = 0.10
PDH_DEPTH_BLOCK_HI = 0.20
PDL_DEPTH_MIN      = 0.10

PASS_N  = 10
PASS_WR = 0.65
LIFT_PP = 0.10   # required WR lift over baseline


def parse_ts(ts_str):
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)

def bar_minutes(dt): return dt.hour*60 + dt.minute
def pct(v): return f"{v:.1%}"
def mean(lst): return sum(lst)/len(lst) if lst else None


# ── Build PO3 session map (35C filtered logic) ────────────────────────────────
def fetch_bars_by_date(instrument_id, label):
    print(f"  [{label}] Fetching bars...", end="", flush=True)
    rows, page = [], 0
    while True:
        resp = (supabase.table("hist_spot_bars_5m")
                .select("bar_ts,open,high,low,close")
                .eq("instrument_id", instrument_id)
                .order("bar_ts").range(page, page+999).execute())
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < 1000: break
        page += 1000
    by_date = defaultdict(list)
    for bar in rows:
        dt = parse_ts(bar["bar_ts"]); t = bar_minutes(dt)
        if 9*60+15 <= t <= 15*60+30:
            bar["_dt"] = dt; bar["_date"] = dt.date().isoformat()
            by_date[bar["_date"]].append(bar)
    for d in by_date: by_date[d].sort(key=lambda b: b["_dt"])
    print(f" {len(by_date)} sessions")
    return dict(by_date)


def fetch_zones(symbol):
    print(f"  [{symbol}] Fetching D zones...", end="", flush=True)
    resp = (supabase.table("hist_ict_htf_zones")
            .select("as_of_date,pattern_type,zone_high,zone_low")
            .eq("symbol", symbol).eq("timeframe", "D")
            .in_("pattern_type", ["PDH","PDL"]).execute())
    zones = defaultdict(dict)
    for row in (resp.data or []):
        d = row["as_of_date"][:10]; pt = row["pattern_type"]
        if pt == "PDH": zones[d]["PDH"] = float(row["zone_high"])
        else: zones[d]["PDL"] = float(row.get("zone_low") or row["zone_high"])
    print(f" {len(zones)} dates")
    return dict(zones)


def build_po3_map(symbol, bars_by_date, zones):
    """Returns {date: 'PO3_BEARISH'|'PO3_BULLISH'|'PO3_NONE'}"""
    cutoff = OPEN_END[0]*60 + OPEN_END[1]
    sorted_dates = sorted(bars_by_date.keys())
    prior_close = {}
    for i, d in enumerate(sorted_dates):
        if i > 0:
            prev = bars_by_date.get(sorted_dates[i-1], [])
            if prev: prior_close[d] = float(prev[-1]["close"])

    result = {}
    for session_date in sorted_dates:
        if session_date not in zones:
            result[session_date] = "PO3_NONE"; continue
        day_bars = bars_by_date[session_date]
        if len(day_bars) < 4:
            result[session_date] = "PO3_NONE"; continue

        z = zones[session_date]
        pdh = z.get("PDH"); pdl = z.get("PDL")
        session_open = float(day_bars[0]["open"])
        prev_cls = prior_close.get(session_date)
        gap_pct  = (session_open - prev_cls)/prev_cls if prev_cls else None
        label = "PO3_NONE"
        pdh_found = pdl_found = False
        n = len(day_bars)

        for i, bar in enumerate(day_bars):
            t = bar_minutes(bar["_dt"])
            if t >= cutoff: break
            high = float(bar["high"]); low = float(bar["low"])

            if not pdh_found and pdh and high >= pdh*(1+SWEEP_THRESHOLD):
                for j in range(i+1, min(i+REVERSAL_MAX_BARS+1, n)):
                    if float(day_bars[j]["close"]) <= pdh*(1-REVERSAL_THRESHOLD):
                        gap_up = session_open >= pdh*0.999
                        if gap_up:
                            sweep_pct = (high-pdh)/pdh*100
                            # Apply 35C filters
                            if not (gap_pct and abs(gap_pct) > PDH_GAP_MAX) and \
                               not (PDH_DEPTH_BLOCK_LO <= sweep_pct < PDH_DEPTH_BLOCK_HI):
                                label = "PO3_BEARISH"
                        pdh_found = True; break

            if not pdl_found and pdl and low <= pdl*(1-SWEEP_THRESHOLD):
                for j in range(i+1, min(i+REVERSAL_MAX_BARS+1, n)):
                    if float(day_bars[j]["close"]) >= pdl*(1+REVERSAL_THRESHOLD):
                        gap_down = session_open <= pdl*1.001
                        if gap_down and label == "PO3_NONE":
                            sweep_pct = (pdl-low)/pdl*100
                            if sweep_pct >= PDL_DEPTH_MIN:
                                label = "PO3_BULLISH"
                        pdl_found = True; break

            if pdh_found and pdl_found: break
        result[session_date] = label
    return result


def fetch_ob_signals(symbol):
    print(f"  [{symbol}] Fetching OB signals...", end="", flush=True)
    rows, page = [], 0
    while True:
        resp = (supabase.table("hist_pattern_signals")
                .select("trade_date,bar_ts,pattern_type,session,win_30m,tier,gamma_regime")
                .eq("symbol", symbol)
                .in_("pattern_type", ["BEAR_OB","BULL_OB"])
                .order("trade_date").range(page, page+999).execute())
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < 1000: break
        page += 1000
    print(f" {len(rows)}")
    return rows


# ── Reporting ─────────────────────────────────────────────────────────────────
def section(label):
    print(f"\n{'─'*65}\n  {label}\n{'─'*65}")

def report(sigs, label, pass_wr=None, n_min=5):
    valid = [s for s in sigs if s.get("win_30m") is not None]
    if len(valid) < n_min:
        print(f"  {label:<58}  N={len(valid):>3}  (insufficient)")
        return None
    wr = sum(1 for s in valid if s["win_30m"]) / len(valid)
    flag = ""
    if pass_wr is not None:
        flag = " ✅" if wr >= pass_wr else " ❌"
    print(f"  {label:<58}  N={len(valid):>3}  WR={pct(wr)}{flag}")
    return wr


def print_results(all_signals, po3_maps):
    for s in all_signals:
        s["po3"] = po3_maps.get(s["symbol"], {}).get(s.get("trade_date","")[:10], "PO3_NONE")

    bear = [s for s in all_signals if s["pattern_type"] == "BEAR_OB"]
    bull = [s for s in all_signals if s["pattern_type"] == "BULL_OB"]
    dist_sessions = {"MIDDAY", "AFTERNOON"}

    section("BASELINE — OB in MIDDAY/AFTERNOON (all sessions, no PO3 filter)")
    bear_dist_base = [s for s in bear if s.get("session") in dist_sessions]
    bull_dist_base = [s for s in bull if s.get("session") in dist_sessions]
    base_bear_wr = report(bear_dist_base, "BEAR_OB MIDDAY+AFTERNOON (baseline)")
    base_bull_wr = report(bull_dist_base, "BULL_OB MIDDAY+AFTERNOON (baseline)")

    section("PRIMARY — OB in distribution leg on PO3-biased sessions")
    bear_aligned = [s for s in bear if s["po3"] == "PO3_BEARISH"
                    and s.get("session") in dist_sessions]
    bull_aligned = [s for s in bull if s["po3"] == "PO3_BULLISH"
                    and s.get("session") in dist_sessions]
    aligned_bear_wr = report(bear_aligned, "BEAR_OB MIDDAY+AFT + PO3_BEARISH", pass_wr=PASS_WR)
    aligned_bull_wr = report(bull_aligned, "BULL_OB MIDDAY+AFT + PO3_BULLISH", pass_wr=PASS_WR)

    if base_bear_wr and aligned_bear_wr:
        lift = aligned_bear_wr - base_bear_wr
        print(f"\n  BEAR_OB lift: {lift:+.1%}  ({'≥10pp ✅' if lift >= LIFT_PP else f'<10pp ❌'})")
    if base_bull_wr and aligned_bull_wr:
        lift = aligned_bull_wr - base_bull_wr
        print(f"  BULL_OB lift: {lift:+.1%}  ({'≥10pp ✅' if lift >= LIFT_PP else f'<10pp ❌'})")

    section("BY SESSION — aligned OB breakdown")
    for sess in ["MIDDAY", "AFTERNOON"]:
        sub_b = [s for s in bear_aligned if s.get("session") == sess]
        sub_u = [s for s in bull_aligned if s.get("session") == sess]
        if sub_b: report(sub_b, f"BEAR_OB {sess} + PO3_BEARISH", pass_wr=PASS_WR)
        if sub_u: report(sub_u, f"BULL_OB {sess} + PO3_BULLISH", pass_wr=PASS_WR)

    section("COUNTER — OB firing AGAINST PO3 bias in distribution window")
    bear_counter = [s for s in bear if s["po3"] == "PO3_BULLISH"
                    and s.get("session") in dist_sessions]
    bull_counter = [s for s in bull if s["po3"] == "PO3_BEARISH"
                    and s.get("session") in dist_sessions]
    report(bear_counter, "BEAR_OB MIDDAY+AFT + PO3_BULLISH (counter)")
    report(bull_counter, "BULL_OB MIDDAY+AFT + PO3_BEARISH (counter)")

    section("BY SYMBOL — aligned distribution OB")
    for sym in ["NIFTY","SENSEX"]:
        report([s for s in bear_aligned if s["symbol"]==sym],
               f"BEAR_OB dist + PO3_BEARISH [{sym}]", pass_wr=PASS_WR)
        report([s for s in bull_aligned if s["symbol"]==sym],
               f"BULL_OB dist + PO3_BULLISH [{sym}]", pass_wr=PASS_WR)

    section("BY TIER — aligned distribution OB")
    for tier in ["TIER1","TIER2"]:
        sub_b = [s for s in bear_aligned if s.get("tier")==tier]
        sub_u = [s for s in bull_aligned if s.get("tier")==tier]
        if sub_b: report(sub_b, f"BEAR_OB dist + PO3_BEARISH + {tier}")
        if sub_u: report(sub_u, f"BULL_OB dist + PO3_BULLISH + {tier}")

    section("BY GAMMA REGIME — aligned distribution OB")
    for regime in ["LONG_GAMMA","SHORT_GAMMA"]:
        sub_b = [s for s in bear_aligned if s.get("gamma_regime")==regime]
        sub_u = [s for s in bull_aligned if s.get("gamma_regime")==regime]
        if sub_b: report(sub_b, f"BEAR_OB dist + PO3_BEARISH + {regime}")
        if sub_u: report(sub_u, f"BULL_OB dist + PO3_BULLISH + {regime}")

    section("PO3 SESSION COUNTS")
    for sym in ["NIFTY","SENSEX"]:
        pm = po3_maps.get(sym, {})
        nb = sum(1 for v in pm.values() if v=="PO3_BEARISH")
        nu = sum(1 for v in pm.values() if v=="PO3_BULLISH")
        nn = sum(1 for v in pm.values() if v=="PO3_NONE")
        print(f"  {sym}: {len(pm)} sessions → PO3_BEARISH={nb}  PO3_BULLISH={nu}  PO3_NONE={nn}")

    section("PASS / FAIL")
    def assess(sigs, label, pass_wr, n_req):
        valid = [s for s in sigs if s.get("win_30m") is not None]
        if not valid: print(f"  {label}: INSUFFICIENT DATA"); return False
        wr = sum(1 for s in valid if s["win_30m"]) / len(valid)
        ok = len(valid) >= n_req and wr >= pass_wr
        print(f"  {label}: {'✅ PASS' if ok else '❌ FAIL'}  N={len(valid)}  WR={pct(wr)}")
        return ok

    p1 = assess(bear_aligned, "BEAR_OB dist + PO3_BEARISH", PASS_WR, PASS_N)
    p2 = assess(bull_aligned, "BULL_OB dist + PO3_BULLISH", PASS_WR, PASS_N)
    lift_ok_bear = (base_bear_wr and aligned_bear_wr and
                    aligned_bear_wr - base_bear_wr >= LIFT_PP)
    lift_ok_bull = (base_bull_wr and aligned_bull_wr and
                    aligned_bull_wr - base_bull_wr >= LIFT_PP)
    print(f"\n  BEAR_OB lift >= 10pp: {'✅' if lift_ok_bear else '❌'}")
    print(f"  BULL_OB lift >= 10pp: {'✅' if lift_ok_bull else '❌'}")

    print()
    if (p1 or p2) and (lift_ok_bear or lift_ok_bull):
        verdict = "PASS — PO3 bias + distribution OB is a valid compound entry signal. ENH candidate: gate OB entries on PO3 session bias direction."
    elif p1 or p2:
        verdict = "PARTIAL — WR threshold met but lift insufficient vs baseline noise."
    else:
        verdict = "FAIL — PO3 session bias does not lift distribution OB WR above threshold."
    print(f"  OVERALL VERDICT: {verdict}")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 38 — OB in Distribution Leg on PO3 Sessions     ║")
    print("║  Session 11 · 2026-04-28 · MERDIAN                          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("Thesis: PO3 sweep (OPEN) sets session bias.")
    print("        Wait for BEAR_OB/BULL_OB in MIDDAY/AFTERNOON aligned with bias.")
    print("        That is the distribution entry — not the sweep itself.")
    print(f"\nPass: WR>={pct(PASS_WR)}, N>={PASS_N}, lift>={pct(LIFT_PP)} vs baseline")
    print()

    po3_maps    = {}
    all_signals = []

    for symbol, inst_id in INSTRUMENTS.items():
        print(f"\n[{symbol}]")
        bars  = fetch_bars_by_date(inst_id, symbol)
        zones = fetch_zones(symbol)
        print(f"  [{symbol}] Building PO3 map...", end="", flush=True)
        po3   = build_po3_map(symbol, bars, zones)
        n_lab = sum(1 for v in po3.values() if v != "PO3_NONE")
        print(f" {n_lab} labelled")
        po3_maps[symbol] = po3
        sigs = fetch_ob_signals(symbol)
        for s in sigs: s["symbol"] = symbol
        all_signals.extend(sigs)

    if not all_signals: print("NO SIGNALS."); sys.exit(1)
    print_results(all_signals, po3_maps)

if __name__ == "__main__":
    main()
