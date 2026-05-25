#!/usr/bin/env python3
"""
experiment_35d_po3_dte_option_selection.py
MERDIAN Experiment 35D — PO3 Sweep: DTE Context + Option Instrument Selection

Question:
    On PO3 sweep days with DTE < 3 (current-week options have severe theta),
    does the T+1D continuation justify buying next-week expiry options?

    And: does DTE at time of sweep affect the strength of the EOD move itself?
    Hypothesis: DTE=0/1 days (expiry pinning breaks at close) may have
    stronger T+1D continuation because pinning pressure lifts overnight.

DTE computation:
    NIFTY  expires Thursday (weekday=3)
    SENSEX expires Friday   (weekday=4)
    DTE = business days until next expiry from trade date.

Option instrument logic:
    DTE >= 3 → current-week expiry (standard)
    DTE < 3  → next-week expiry (DTE ~8-10)
    T+1D WR >= 60% AND mean|wins >= 0.3% → next-week viable
    T+1D WR <  60% OR  mean|wins <  0.3% → avoid next-week, skip or wait

Filters: same 35C (gap cap + depth exclusion)
Universe: NIFTY + SENSEX, 2025-04 to 2026-04

Run from: C:\\GammaEnginePython
Usage  : python experiment_35d_po3_dte_option_selection.py
Session: 11 (2026-04-28)
"""

import os, sys
from collections import defaultdict
from datetime import datetime, timedelta
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
EXPIRY_WEEKDAY = {"NIFTY": 3, "SENSEX": 4}  # 3=Thu, 4=Fri

# 35C filters
SWEEP_THRESHOLD    = 0.0005
REVERSAL_THRESHOLD = 0.001
REVERSAL_MAX_BARS  = 6
OPEN_END           = (10, 0)
PDH_GAP_MAX        = 0.005
PDH_DEPTH_BLOCK_LO = 0.10
PDH_DEPTH_BLOCK_HI = 0.20
PDL_DEPTH_MIN      = 0.10

PASS_N  = 8
PASS_WR = 0.60
PASS_MEAN_WIN = 0.003  # 0.3% mean on winning days for next-week viability


def parse_ts(ts_str):
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)

def bar_minutes(dt): return dt.hour*60 + dt.minute
def pct(v): return f"{v:.1%}"
def mean(lst): return sum(lst)/len(lst) if lst else None
def median(lst):
    if not lst: return None
    s = sorted(lst); n = len(s)
    return s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2


def compute_dte(date_str: str, symbol: str) -> int:
    """Business-days until next expiry from date_str."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    exp_wd = EXPIRY_WEEKDAY[symbol]
    # Find next expiry on or after d
    days_ahead = (exp_wd - d.weekday()) % 7
    if days_ahead == 0:
        next_exp = d  # today IS expiry
    else:
        next_exp = d + timedelta(days=days_ahead)
    # Count business days (Mon-Fri)
    dte = 0
    cursor = d
    while cursor.date() < next_exp.date():
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            dte += 1
    return dte


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
    resp = (supabase.table("hist_ict_htf_zones")
            .select("as_of_date,pattern_type,zone_high,zone_low")
            .eq("symbol", symbol).eq("timeframe", "D")
            .in_("pattern_type", ["PDH","PDL"]).execute())
    zones = defaultdict(dict)
    for row in (resp.data or []):
        d = row["as_of_date"][:10]; pt = row["pattern_type"]
        if pt == "PDH": zones[d]["PDH"] = float(row["zone_high"])
        else: zones[d]["PDL"] = float(row.get("zone_low") or row["zone_high"])
    return dict(zones)


def detect_events(symbol, bars_by_date, zones):
    cutoff       = OPEN_END[0]*60 + OPEN_END[1]
    sorted_dates = sorted(bars_by_date.keys())
    prior_close  = {}
    for i, d in enumerate(sorted_dates):
        if i > 0:
            prev = bars_by_date.get(sorted_dates[i-1], [])
            if prev: prior_close[d] = float(prev[-1]["close"])
    eod_close = {d: float(bars_by_date[d][-1]["close"]) for d in sorted_dates if bars_by_date[d]}

    def nd_ret(from_date, direction, n):
        idx = sorted_dates.index(from_date)
        if idx + n >= len(sorted_dates): return None
        base = eod_close.get(from_date); tgt = eod_close.get(sorted_dates[idx+n])
        if not base or not tgt: return None
        ret = (tgt - base) / base
        return ret * (1 if direction == "BULLISH" else -1)

    events = []
    for session_date in sorted_dates:
        if session_date not in zones: continue
        day_bars = bars_by_date[session_date]
        if len(day_bars) < 8: continue
        z = zones[session_date]
        pdh = z.get("PDH"); pdl = z.get("PDL")
        session_open = float(day_bars[0]["open"])
        prev_cls = prior_close.get(session_date)
        gap_pct  = (session_open - prev_cls)/prev_cls if prev_cls else None
        dte      = compute_dte(session_date, symbol)
        session_ret = (float(day_bars[-1]["close"]) - session_open) / session_open
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
                        if not gap_up: pdh_found = True; break
                        sweep_pct = (high-pdh)/pdh*100
                        filtered = ((gap_pct and abs(gap_pct) > PDH_GAP_MAX) or
                                    PDH_DEPTH_BLOCK_LO <= sweep_pct < PDH_DEPTH_BLOCK_HI)
                        t1d = nd_ret(session_date, "BEARISH", 1)
                        events.append({
                            "symbol": symbol, "date": session_date,
                            "type": "PDH", "filtered": filtered,
                            "dte": dte, "gap_pct": gap_pct,
                            "sweep_pct": sweep_pct,
                            "ret_eod": session_ret,
                            "ret_t1d": t1d, "ret_t2d": nd_ret(session_date,"BEARISH",2),
                            "win_eod": session_ret < 0,
                            "win_t1d": t1d is not None and t1d > 0,
                            "win_t2d": nd_ret(session_date,"BEARISH",2) is not None and nd_ret(session_date,"BEARISH",2) > 0,
                            "dte_bucket": "DTE<3" if dte < 3 else "DTE3+",
                        })
                        pdh_found = True; break

            if not pdl_found and pdl and low <= pdl*(1-SWEEP_THRESHOLD):
                for j in range(i+1, min(i+REVERSAL_MAX_BARS+1, n)):
                    if float(day_bars[j]["close"]) >= pdl*(1+REVERSAL_THRESHOLD):
                        gap_down = session_open <= pdl*1.001
                        if not gap_down: pdl_found = True; break
                        sweep_pct = (pdl-low)/pdl*100
                        filtered = sweep_pct < PDL_DEPTH_MIN
                        t1d = nd_ret(session_date, "BULLISH", 1)
                        events.append({
                            "symbol": symbol, "date": session_date,
                            "type": "PDL", "filtered": filtered,
                            "dte": dte, "gap_pct": gap_pct,
                            "sweep_pct": sweep_pct,
                            "ret_eod": session_ret,
                            "ret_t1d": t1d, "ret_t2d": nd_ret(session_date,"BULLISH",2),
                            "win_eod": session_ret > 0,
                            "win_t1d": t1d is not None and t1d > 0,
                            "win_t2d": nd_ret(session_date,"BULLISH",2) is not None and nd_ret(session_date,"BULLISH",2) > 0,
                            "dte_bucket": "DTE<3" if dte < 3 else "DTE3+",
                        })
                        pdl_found = True; break

            if pdh_found and pdl_found: break
    return events


def section(label):
    print(f"\n{'─'*65}\n  {label}\n{'─'*65}")


def wr_row(evs, win_key, ret_key, label, n_min=4):
    valid = [e for e in evs if e.get(win_key) is not None]
    if len(valid) < n_min:
        print(f"  {label:<55}  N={len(valid):>3}  (insufficient)")
        return None, None
    wr    = sum(1 for e in valid if e[win_key]) / len(valid)
    rets  = [e[ret_key] for e in valid if e.get(ret_key) is not None]
    wins  = [e[ret_key] for e in valid if e[win_key] and e.get(ret_key) is not None]
    avg   = mean(rets); mavg = mean(wins)
    print(f"  {label:<55}  N={len(valid):>3}  WR={pct(wr)}  "
          f"mean={avg:.3%}  mean|wins={mavg:.3%}" if mavg else
          f"  {label:<55}  N={len(valid):>3}  WR={pct(wr)}")
    return wr, mavg


def print_results(all_events):
    filt = [e for e in all_events if not e["filtered"]]
    pdh  = [e for e in filt if e["type"] == "PDH"]
    pdl  = [e for e in filt if e["type"] == "PDL"]

    section("DTE DISTRIBUTION — filtered events")
    print()
    for ev_list, label in [(pdh, "PDH"), (pdl, "PDL")]:
        for dte in sorted(set(e["dte"] for e in ev_list)):
            sub = [e for e in ev_list if e["dte"] == dte]
            wr  = sum(1 for e in sub if e["win_eod"]) / len(sub)
            print(f"  {label} DTE={dte}  N={len(sub):>3}  EOD WR={pct(wr)}")

    section("EOD WR BY DTE BUCKET")
    for ev_list, label in [(pdh, "PDH"), (pdl, "PDL")]:
        for bucket in ["DTE<3", "DTE3+"]:
            sub = [e for e in ev_list if e["dte_bucket"] == bucket]
            wr_row(sub, "win_eod", "ret_eod", f"{label} {bucket} EOD", n_min=3)

    section("T+1D CONTINUATION BY DTE BUCKET — core question")
    print()
    print("  If DTE<3 events show T+1D WR>=60% AND mean|wins>=0.3%")
    print("  → next-week expiry viable on those days")
    print()
    for ev_list, label in [(pdh, "PDH"), (pdl, "PDL")]:
        for bucket in ["DTE<3", "DTE3+"]:
            sub = [e for e in ev_list if e["dte_bucket"] == bucket]
            wr, mavg = wr_row(sub, "win_t1d", "ret_t1d", f"{label} {bucket} T+1D", n_min=3)

    section("T+1D BY EXACT DTE")
    for ev_list, label in [(pdh, "PDH"), (pdl, "PDL")]:
        print(f"\n  {label}:")
        for dte in sorted(set(e["dte"] for e in ev_list)):
            sub = [e for e in ev_list if e["dte"] == dte]
            wr_row(sub, "win_t1d", "ret_t1d", f"  {label} DTE={dte} T+1D", n_min=3)

    section("OPTION INSTRUMENT DECISION TABLE")
    print()
    print(f"  {'Scenario':<40}  {'EOD WR':>8}  {'T+1D WR':>9}  {'T+1D mean|W':>12}  {'Recommendation'}")
    print(f"  {'-'*40}  {'-'*8}  {'-'*9}  {'-'*12}  {'-'*20}")

    for ev_list, label in [(pdh, "PDH"), (pdl, "PDL")]:
        for bucket in ["DTE<3", "DTE3+"]:
            sub = [e for e in ev_list if e["dte_bucket"] == bucket]
            ev  = [e for e in sub if e.get("win_eod") is not None]
            t1  = [e for e in sub if e.get("win_t1d") is not None]
            if not ev: continue
            eod_wr = sum(1 for e in ev if e["win_eod"]) / len(ev)
            t1_wr  = sum(1 for e in t1 if e["win_t1d"]) / len(t1) if t1 else None
            t1_wins = [e["ret_t1d"] for e in t1 if e["win_t1d"] and e.get("ret_t1d") is not None]
            t1_mavg = mean(t1_wins)
            next_wk_ok = (t1_wr is not None and t1_wr >= PASS_WR and
                          t1_mavg is not None and t1_mavg >= PASS_MEAN_WIN)
            rec = "NEXT-WEEK ✅" if (bucket == "DTE<3" and next_wk_ok) else \
                  "CURRENT-WEEK" if bucket == "DTE3+" else \
                  "SKIP/WAIT ❌"
            t1_str  = f"{pct(t1_wr)}" if t1_wr else "n/a"
            mw_str  = f"{t1_mavg:.3%}" if t1_mavg else "n/a"
            print(f"  {label+' '+bucket:<40}  {pct(eod_wr):>8}  {t1_str:>9}  {mw_str:>12}  {rec}")

    section("ALL DTE<3 EVENTS (for manual review)")
    dte3 = [e for e in filt if e["dte_bucket"] == "DTE<3"]
    for e in sorted(dte3, key=lambda x: x["date"]):
        win1 = "T+1W" if e.get("win_t1d") else "    "
        print(f"  {e['date']}  {e['symbol']:<8}  {e['type']}  DTE={e['dte']}  "
              f"EOD={'WIN' if e['win_eod'] else 'LOSE'}  "
              f"{win1}  gap={e['gap_pct']:.3%}" if e.get('gap_pct') else
              f"  {e['date']}  {e['symbol']:<8}  {e['type']}  DTE={e['dte']}")


def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 35D — PO3 Sweep: DTE Context + Option Selection  ║")
    print("║  Session 11 · 2026-04-28 · MERDIAN                          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("Question: On DTE<3 days, does T+1D continuation justify next-week options?")
    print(f"Next-week viable if: T+1D WR>={pct(PASS_WR)}, mean|wins>={PASS_MEAN_WIN:.1%}")
    print()
    all_events = []
    for symbol, inst_id in INSTRUMENTS.items():
        print(f"\n[{symbol}]")
        bars   = fetch_bars_by_date(inst_id, symbol)
        zones  = fetch_zones(symbol)
        events = detect_events(symbol, bars, zones)
        filt_n = sum(1 for e in events if not e["filtered"])
        print(f"  Events total={len(events)}  filtered={filt_n}")
        all_events.extend(events)
    if not all_events: print("NO EVENTS."); sys.exit(1)
    print_results(all_events)

if __name__ == "__main__":
    main()
