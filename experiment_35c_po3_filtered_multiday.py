#!/usr/bin/env python3
"""
experiment_35c_po3_filtered_multiday.py
MERDIAN Experiment 35C — PO3 Filtered Config + Multi-Day Return Extension

Origin:
    Exp 35B revealed two key findings:
    1. Filters from Q3 failure mode analysis:
         PDH: block large gaps >0.5% (42.9% WR → likely real breakouts)
               block sweep depth 0.10-0.20% (50% WR → ambiguous zone)
         PDL: block shallow sweeps <0.10% (37.5% WR → noise ticks)
    2. Edge is entirely back-loaded (EOD WR 75.9%/63.6% vs T+30m 27.6%/15.2%)
       → raises question: do these sessions continue moving for 2-3 days?

    This experiment:
    A) Re-runs with filtered config → expected lift to ~88% PDH, ~72% PDL EOD WR
    B) Measures T+1D, T+2D, T+3D continuation from sweep day's close
       → answers whether these are multi-session institutional moves
       → informs option instrument selection (current week vs next week expiry)

Filters applied (from 35B analysis):
    PDH blocks:
      - Gap >0.5% (large gap = potential gap-fill day, not manipulation)
      - Sweep depth 0.10-0.20% (ambiguous zone, 50% WR)
    PDL blocks:
      - Sweep depth <0.10% (noise ticks, 37.5% WR)

Pass criteria:
    A) EOD WR >= 85% PDH, >= 72% PDL (filtered universe)
    B) T+1D WR >= 60% (continuation evidence for multi-session holds)

Multi-day methodology:
    For each event on date D:
      T+1D close = first session's close after D
      T+2D close = second session's close after D
      T+3D close = third session's close after D
    Return measured from event-day EOD close (not from rejection bar)
    Win = continuation in predicted direction (bearish for PDH, bullish for PDL)

TD-029 / pagination: fixes from Exp 34 baked in.

Run from: C:\\GammaEnginePython
Usage  : python experiment_35c_po3_filtered_multiday.py

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

# ── Core parameters ───────────────────────────────────────────────────────────
SWEEP_THRESHOLD    = 0.0005
REVERSAL_THRESHOLD = 0.001
REVERSAL_MAX_BARS  = 6
OPEN_END           = (10, 0)

# ── Filters from 35B failure mode analysis ────────────────────────────────────
PDH_GAP_MAX        = 0.005    # block gap > 0.5%
PDH_DEPTH_BLOCK_LO = 0.10     # block depth 0.10-0.20% range
PDH_DEPTH_BLOCK_HI = 0.20
PDL_DEPTH_MIN      = 0.10     # block shallow PDL sweeps < 0.10%

# ── Pass criteria ─────────────────────────────────────────────────────────────
PASS_EOD_PDH = 0.85
PASS_EOD_PDL = 0.72
PASS_T1D_WR  = 0.60
PASS_N       = 15


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_ts(ts_str):
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)

def bar_minutes(dt):
    return dt.hour * 60 + dt.minute

def pct(v):
    return f"{v:.1%}"

def mean(lst):
    return sum(lst) / len(lst) if lst else None

def median(lst):
    if not lst: return None
    s = sorted(lst); n = len(s)
    return s[n//2] if n % 2 else (s[n//2-1] + s[n//2]) / 2


# ── Fetch ─────────────────────────────────────────────────────────────────────
def fetch_bars_by_date(instrument_id, label):
    print(f"  [{label}] Fetching 5m bars...", end="", flush=True)
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
        dt = parse_ts(bar["bar_ts"])
        t  = bar_minutes(dt)
        if 9*60+15 <= t <= 15*60+30:
            bar["_dt"] = dt; bar["_date"] = dt.date().isoformat()
            by_date[bar["_date"]].append(bar)
    for d in by_date:
        by_date[d].sort(key=lambda b: b["_dt"])
    total = sum(len(v) for v in by_date.values())
    print(f" {total} bars / {len(by_date)} sessions")
    return dict(by_date)


def fetch_zones(symbol):
    print(f"  [{symbol}] Fetching D PDH/PDL zones...", end="", flush=True)
    resp = (supabase.table("hist_ict_htf_zones")
            .select("as_of_date,pattern_type,zone_high,zone_low")
            .eq("symbol", symbol).eq("timeframe", "D")
            .in_("pattern_type", ["PDH", "PDL"]).execute())
    zones = defaultdict(dict)
    for row in (resp.data or []):
        d = row["as_of_date"][:10]; pt = row["pattern_type"]
        if pt == "PDH":
            zones[d]["PDH"] = float(row["zone_high"])
        else:
            zones[d]["PDL"] = float(row.get("zone_low") or row["zone_high"])
    print(f" {len(zones)} dates")
    return dict(zones)


# ── Detection ─────────────────────────────────────────────────────────────────
def detect_events(symbol, bars_by_date, zones):
    cutoff       = OPEN_END[0]*60 + OPEN_END[1]
    sorted_dates = sorted(bars_by_date.keys())

    # Prior close map for gap calculation
    prior_close = {}
    for i, d in enumerate(sorted_dates):
        if i > 0:
            prev = bars_by_date.get(sorted_dates[i-1], [])
            if prev: prior_close[d] = float(prev[-1]["close"])

    # EOD close map for multi-day returns
    eod_close = {d: float(bars_by_date[d][-1]["close"])
                 for d in sorted_dates if bars_by_date[d]}

    events = []
    for session_date in sorted_dates:
        if session_date not in zones: continue
        day_bars = bars_by_date[session_date]
        if len(day_bars) < 8: continue

        z            = zones[session_date]
        pdh          = z.get("PDH")
        pdl          = z.get("PDL")
        session_open = float(day_bars[0]["open"])
        session_eod  = float(day_bars[-1]["close"])
        session_ret  = (session_eod - session_open) / session_open

        prev_cls  = prior_close.get(session_date)
        gap_pct   = (session_open - prev_cls) / prev_cls if prev_cls else None
        gap_pts   = (session_open - prev_cls) if prev_cls else None

        # Multi-day returns from EOD close of event session
        idx_d = sorted_dates.index(session_date)
        def nd_ret(offset, direction):
            target = idx_d + offset
            if target >= len(sorted_dates): return None
            tgt_close = eod_close.get(sorted_dates[target])
            if tgt_close is None: return None
            return (tgt_close - session_eod) / session_eod * (1 if direction == "BULLISH" else -1)

        pdh_found = pdl_found = False
        for i, bar in enumerate(day_bars):
            t = bar_minutes(bar["_dt"])
            if t >= cutoff: break
            high = float(bar["high"]); low = float(bar["low"])
            n = len(day_bars)

            # PDH sweep
            if not pdh_found and pdh and high >= pdh*(1+SWEEP_THRESHOLD):
                for j in range(i+1, min(i+REVERSAL_MAX_BARS+1, n)):
                    if float(day_bars[j]["close"]) <= pdh*(1-REVERSAL_THRESHOLD):
                        gap_up = session_open >= pdh*0.999
                        if not gap_up: pdh_found = True; break
                        sweep_pct = (high - pdh) / pdh * 100
                        bars_to_rev = j - i

                        # Apply 35B filters
                        filtered = False
                        filter_reason = ""
                        if gap_pct is not None and abs(gap_pct) > PDH_GAP_MAX:
                            filtered = True; filter_reason = f"gap_too_large({abs(gap_pct):.3%})"
                        elif PDH_DEPTH_BLOCK_LO <= sweep_pct < PDH_DEPTH_BLOCK_HI:
                            filtered = True; filter_reason = f"depth_ambiguous({sweep_pct:.2f}%)"

                        events.append({
                            "symbol": symbol, "date": session_date,
                            "type": "PDH", "direction": "BEARISH",
                            "sweep_pct": sweep_pct, "bars_to_rev": bars_to_rev,
                            "gap_pct": gap_pct, "gap_pts": gap_pts,
                            "filtered": filtered, "filter_reason": filter_reason,
                            "ret_eod":  session_ret,
                            "ret_t1d":  nd_ret(1, "BEARISH"),
                            "ret_t2d":  nd_ret(2, "BEARISH"),
                            "ret_t3d":  nd_ret(3, "BEARISH"),
                            "win_eod":  session_ret < 0,
                            "win_t1d":  nd_ret(1, "BEARISH") is not None and nd_ret(1, "BEARISH") > 0,
                            "win_t2d":  nd_ret(2, "BEARISH") is not None and nd_ret(2, "BEARISH") > 0,
                            "win_t3d":  nd_ret(3, "BEARISH") is not None and nd_ret(3, "BEARISH") > 0,
                        })
                        pdh_found = True; break

            # PDL sweep
            if not pdl_found and pdl and low <= pdl*(1-SWEEP_THRESHOLD):
                for j in range(i+1, min(i+REVERSAL_MAX_BARS+1, n)):
                    if float(day_bars[j]["close"]) >= pdl*(1+REVERSAL_THRESHOLD):
                        gap_down = session_open <= pdl*1.001
                        if not gap_down: pdl_found = True; break
                        sweep_pct = (pdl - low) / pdl * 100
                        bars_to_rev = j - i

                        filtered = False; filter_reason = ""
                        if sweep_pct < PDL_DEPTH_MIN:
                            filtered = True; filter_reason = f"depth_too_shallow({sweep_pct:.2f}%)"

                        events.append({
                            "symbol": symbol, "date": session_date,
                            "type": "PDL", "direction": "BULLISH",
                            "sweep_pct": sweep_pct, "bars_to_rev": bars_to_rev,
                            "gap_pct": gap_pct, "gap_pts": gap_pts,
                            "filtered": filtered, "filter_reason": filter_reason,
                            "ret_eod":  session_ret,
                            "ret_t1d":  nd_ret(1, "BULLISH"),
                            "ret_t2d":  nd_ret(2, "BULLISH"),
                            "ret_t3d":  nd_ret(3, "BULLISH"),
                            "win_eod":  session_ret > 0,
                            "win_t1d":  nd_ret(1, "BULLISH") is not None and nd_ret(1, "BULLISH") > 0,
                            "win_t2d":  nd_ret(2, "BULLISH") is not None and nd_ret(2, "BULLISH") > 0,
                            "win_t3d":  nd_ret(3, "BULLISH") is not None and nd_ret(3, "BULLISH") > 0,
                        })
                        pdl_found = True; break

            if pdh_found and pdl_found: break
    return events


# ── Reporting ─────────────────────────────────────────────────────────────────
def section(label):
    print(f"\n{'─'*65}\n  {label}\n{'─'*65}")

def wr_row(events, win_key, ret_key, label, n_min=5):
    valid = [e for e in events if e.get(win_key) is not None]
    if len(valid) < n_min:
        print(f"  {label:<52}  N={len(valid):>3}  (insufficient)")
        return None
    wr   = sum(1 for e in valid if e[win_key]) / len(valid)
    rets = [e[ret_key] for e in valid if e.get(ret_key) is not None]
    avg  = mean(rets); med = median(rets)
    print(f"  {label:<52}  N={len(valid):>3}  WR={pct(wr)}  "
          f"mean={avg:.3%}  median={med:.3%}" if avg is not None else
          f"  {label:<52}  N={len(valid):>3}  WR={pct(wr)}")
    return wr

def multiday_table(events, label):
    print(f"\n  [{label}]")
    print(f"  {'Horizon':<10}  {'N':>4}  {'WR':>7}  {'Mean ret':>10}  {'Median':>9}  {'Cum mean|wins':>14}")
    print(f"  {'-'*10}  {'-'*4}  {'-'*7}  {'-'*10}  {'-'*9}  {'-'*14}")
    for horizon, wk, rk in [
        ("EOD",  "win_eod",  "ret_eod"),
        ("T+1D", "win_t1d",  "ret_t1d"),
        ("T+2D", "win_t2d",  "ret_t2d"),
        ("T+3D", "win_t3d",  "ret_t3d"),
    ]:
        valid = [e for e in events if e.get(wk) is not None]
        if not valid:
            print(f"  {horizon:<10}  {0:>4}"); continue
        wr   = sum(1 for e in valid if e[wk]) / len(valid)
        rets = [e[rk] for e in valid if e.get(rk) is not None]
        avg  = mean(rets); med = median(rets)
        wins = [e[rk] for e in valid if e[wk] and e.get(rk) is not None]
        cavg = mean(wins)
        print(f"  {horizon:<10}  {len(valid):>4}  {pct(wr):>7}  "
              f"{avg:.3%}  {med:.3%}  "
              f"{cavg:.3%}" if cavg else f"  {horizon:<10}  {len(valid):>4}  {pct(wr):>7}  {avg:.3%}" if avg else "")


def print_results(all_events):
    unfiltered = all_events
    filtered   = [e for e in all_events if not e["filtered"]]
    blocked    = [e for e in all_events if e["filtered"]]

    pdh_all  = [e for e in unfiltered if e["type"] == "PDH"]
    pdl_all  = [e for e in unfiltered if e["type"] == "PDL"]
    pdh_filt = [e for e in filtered   if e["type"] == "PDH"]
    pdl_filt = [e for e in filtered   if e["type"] == "PDL"]

    section("FILTER IMPACT SUMMARY")
    print(f"\n  Total events   : {len(all_events)} (PDH={len(pdh_all)}, PDL={len(pdl_all)})")
    print(f"  Passed filter  : {len(filtered)} (PDH={len(pdh_filt)}, PDL={len(pdl_filt)})")
    print(f"  Blocked        : {len(blocked)}")
    if blocked:
        from collections import Counter
        reasons = Counter(e["filter_reason"] for e in blocked)
        for r, c in reasons.most_common():
            print(f"    {r}: {c}")

    section("PART A — EOD WR: UNFILTERED vs FILTERED")
    print()
    wr_row(pdh_all,  "win_eod", "ret_eod", "PDH unfiltered (Exp 35B replication)")
    wr_row(pdh_filt, "win_eod", "ret_eod", "PDH filtered (35B filters applied)")
    print()
    wr_row(pdl_all,  "win_eod", "ret_eod", "PDL unfiltered (Exp 35B replication)")
    wr_row(pdl_filt, "win_eod", "ret_eod", "PDL filtered (35B filters applied)")

    section("PART B — MULTI-DAY CONTINUATION (filtered events)")
    multiday_table(pdh_filt, "PDH filtered → bearish continuation")
    multiday_table(pdl_filt, "PDL filtered → bullish continuation")

    section("PART B — BY SYMBOL (filtered, multi-day)")
    for sym in ["NIFTY", "SENSEX"]:
        multiday_table([e for e in pdh_filt if e["symbol"] == sym], f"PDH {sym}")
        multiday_table([e for e in pdl_filt if e["symbol"] == sym], f"PDL {sym}")

    section("PART B — REVERSAL SPEED × MULTI-DAY WR (filtered)")
    for speed_label, lo, hi in [("Fast ≤T+2", 1, 3), ("Slow ≥T+5", 5, 7)]:
        sub_p = [e for e in pdh_filt if lo <= e["bars_to_rev"] < hi]
        sub_l = [e for e in pdl_filt if lo <= e["bars_to_rev"] < hi]
        if sub_p:
            print(f"\n  PDH {speed_label} (N={len(sub_p)}):")
            for wk, rk, h in [("win_eod","ret_eod","EOD"),("win_t1d","ret_t1d","T+1D"),("win_t2d","ret_t2d","T+2D")]:
                wr_row(sub_p, wk, rk, f"    PDH {speed_label} {h}", n_min=3)
        if sub_l:
            print(f"\n  PDL {speed_label} (N={len(sub_l)}):")
            for wk, rk, h in [("win_eod","ret_eod","EOD"),("win_t1d","ret_t1d","T+1D"),("win_t2d","ret_t2d","T+2D")]:
                wr_row(sub_l, wk, rk, f"    PDL {speed_label} {h}", n_min=3)

    section("PART B — MAGNITUDE: WINNING MULTI-DAY MOVES")
    print()
    for ev_list, label in [(pdh_filt, "PDH"), (pdl_filt, "PDL")]:
        for wk, rk, h in [("win_t1d","ret_t1d","T+1D"),("win_t2d","ret_t2d","T+2D"),("win_t3d","ret_t3d","T+3D")]:
            wins = [e[rk] for e in ev_list if e.get(wk) and e.get(rk) is not None]
            if wins:
                print(f"  {label} {h} wins  N={len(wins):>3}  "
                      f"mean={mean(wins):.3%}  median={median(wins):.3%}  "
                      f"max={max(wins):.3%}")

    section("OPTION INSTRUMENT IMPLICATION")
    print()
    print("  Multi-day WR and mean return inform option instrument choice:")
    print("  T+1D WR >= 60% AND mean >= 0.3% → next-week expiry valid (DTE ~8-10)")
    print("  T+1D WR <  60% OR  mean <  0.3% → current-week expiry only (DTE 2-4)")
    print("  T+2D WR >= 55% → consider 2-week expiry for swing hold")
    print()
    for ev_list, label in [(pdh_filt, "PDH"), (pdl_filt, "PDL")]:
        t1_valid = [e for e in ev_list if e.get("win_t1d") is not None]
        if t1_valid:
            t1_wr  = sum(1 for e in t1_valid if e["win_t1d"]) / len(t1_valid)
            t1_ret = mean([e["ret_t1d"] for e in t1_valid if e.get("ret_t1d") is not None])
            rec = "NEXT-WEEK EXPIRY" if (t1_wr >= 0.60 and t1_ret and abs(t1_ret) >= 0.003) else "CURRENT-WEEK EXPIRY"
            print(f"  {label}: T+1D WR={pct(t1_wr)}  mean={t1_ret:.3%}  → RECOMMENDATION: {rec}")

    section("PASS / FAIL")
    def assess(events, label, pass_wr, key="win_eod"):
        valid = [e for e in events if e.get(key) is not None]
        if not valid: print(f"  {label}: INSUFFICIENT DATA"); return False
        wr = sum(1 for e in valid if e[key]) / len(valid)
        ok = len(valid) >= PASS_N and wr >= pass_wr
        print(f"  {label}: {'✅ PASS' if ok else '❌ FAIL'}  N={len(valid)}  WR={pct(wr)}  (criteria N>={PASS_N} WR>={pct(pass_wr)})")
        return ok

    p1 = assess(pdh_filt, "PDH filtered EOD", PASS_EOD_PDH)
    p2 = assess(pdl_filt, "PDL filtered EOD", PASS_EOD_PDL)
    p3 = assess(pdh_filt, "PDH T+1D continuation", PASS_T1D_WR, key="win_t1d")
    p4 = assess(pdl_filt, "PDL T+1D continuation", PASS_T1D_WR, key="win_t1d")
    print()
    print(f"  EOD signal quality   : {'STRONG' if p1 and p2 else 'PARTIAL' if p1 or p2 else 'FAIL'}")
    print(f"  Multi-day continuation: {'CONFIRMED' if p3 and p4 else 'PARTIAL' if p3 or p4 else 'NOT CONFIRMED'}")
    if p3 or p4:
        print("  → Multi-day confirmed: next-week expiry valid for sweep-day entries")
    else:
        print("  → Multi-day not confirmed: T+30m/EOD-only exit discipline correct")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 35C — PO3 Filtered Config + Multi-Day Extension  ║")
    print("║  Session 11 · 2026-04-28 · MERDIAN                          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("Filters applied (from 35B failure mode analysis):")
    print(f"  PDH: block gap > {PDH_GAP_MAX:.1%} (real breakout risk)")
    print(f"  PDH: block sweep depth {PDH_DEPTH_BLOCK_LO:.0%}–{PDH_DEPTH_BLOCK_HI:.0%} (ambiguous zone, 50% WR)")
    print(f"  PDL: block depth < {PDL_DEPTH_MIN:.0%} (noise ticks, 37.5% WR)")
    print()
    print("Multi-day horizons: EOD, T+1D, T+2D, T+3D")
    print()

    all_events = []
    for symbol, inst_id in INSTRUMENTS.items():
        print(f"\n[{symbol}]")
        bars = fetch_bars_by_date(inst_id, symbol)
        zones = fetch_zones(symbol)
        events = detect_events(symbol, bars, zones)
        pdh_n = sum(1 for e in events if e["type"] == "PDH")
        pdl_n = sum(1 for e in events if e["type"] == "PDL")
        filt_n = sum(1 for e in events if not e["filtered"])
        print(f"  Events: PDH={pdh_n}  PDL={pdl_n}  passed_filter={filt_n}")
        all_events.extend(events)

    if not all_events: print("NO EVENTS."); sys.exit(1)
    print_results(all_events)

if __name__ == "__main__":
    main()
