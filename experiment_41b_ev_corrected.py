#!/usr/bin/env python3
"""
experiment_41b_ev_corrected.py
MERDIAN Experiment 41B — Corrected EV for E4/E5

Issue found in Exp 41:
    ret_30m is stored as PERCENTAGE POINTS (e.g., 0.1351 = 0.1351% of spot)
    NOT as a decimal fraction.
    Exp 41 used ret_30m * spot directly → inflated by 100x.

    Sign convention for BEAR_OB (BUY_PE):
      win_30m=True when ret_30m is NEGATIVE (spot fell = PE wins)
    Sign convention for BULL_OB (BUY_CE):
      win_30m=True when ret_30m is POSITIVE (spot rose = CE wins)

This script:
    1. Correctly computes mean|wins, mean|losses, EV in % and points
       for E4 (BEAR_OB MIDDAY + PO3_BEARISH) and E5 (BULL_OB AFT + PO3_BULLISH)
    2. Computes same for E1/E2 from hist_pattern_signals where ret_30m available
    3. Outputs clean EV table for Kelly sizing

Run from: C:\\GammaEnginePython
Usage  : python experiment_41b_ev_corrected.py
Session: 11 (2026-04-28)
"""

import os, sys
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
SPOT_APPROX = {"NIFTY": 24000, "SENSEX": 80000}

# ret_30m unit: percentage points. Divide by 100 to get decimal fraction.
# e.g., ret_30m = 0.1351 → 0.001351 → 0.001351 * 24000 = 32.4 NIFTY points

# 35C/PO3 filters
SWEEP_THRESHOLD    = 0.0005
REVERSAL_THRESHOLD = 0.001
REVERSAL_MAX_BARS  = 6
OPEN_END           = (10, 0)
PDH_GAP_MAX        = 0.005
PDH_DEPTH_BLOCK_LO = 0.10
PDH_DEPTH_BLOCK_HI = 0.20
PDL_DEPTH_MIN      = 0.10


def parse_ts(ts_str):
    return datetime.fromisoformat(ts_str.replace("Z","+00:00")).replace(tzinfo=None)
def bar_minutes(dt): return dt.hour*60+dt.minute
def mean(lst): return sum(lst)/len(lst) if lst else None
def median(lst):
    if not lst: return None
    s=sorted(lst); n=len(s)
    return s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2
def pctile(lst, p):
    if not lst: return None
    s=sorted(lst); return s[int(len(s)*p/100)]


def fetch_bars_by_date(instrument_id, label):
    print(f"  [{label}] Fetching bars...", end="", flush=True)
    rows, page = [], 0
    while True:
        resp=(supabase.table("hist_spot_bars_5m").select("bar_ts,open,high,low,close")
              .eq("instrument_id",instrument_id).order("bar_ts").range(page,page+999).execute())
        batch=resp.data or []; rows.extend(batch)
        if len(batch)<1000: break
        page+=1000
    by_date=defaultdict(list)
    for bar in rows:
        dt=parse_ts(bar["bar_ts"]); t=bar_minutes(dt)
        if 9*60+15<=t<=15*60+30:
            bar["_dt"]=dt; bar["_date"]=dt.date().isoformat()
            by_date[bar["_date"]].append(bar)
    for d in by_date: by_date[d].sort(key=lambda b:b["_dt"])
    print(f" {len(by_date)} sessions")
    return dict(by_date)


def fetch_d_zones(symbol):
    resp=(supabase.table("hist_ict_htf_zones")
          .select("as_of_date,pattern_type,zone_high,zone_low")
          .eq("symbol",symbol).eq("timeframe","D")
          .in_("pattern_type",["PDH","PDL"]).execute())
    zones=defaultdict(dict)
    for row in (resp.data or []):
        d=row["as_of_date"][:10]; pt=row["pattern_type"]
        if pt=="PDH": zones[d]["PDH"]=float(row["zone_high"])
        else: zones[d]["PDL"]=float(row.get("zone_low") or row["zone_high"])
    return dict(zones)


def fetch_ob_signals(symbol):
    print(f"  [{symbol}] OB signals...", end="", flush=True)
    rows, page = [], 0
    while True:
        resp=(supabase.table("hist_pattern_signals")
              .select("trade_date,pattern_type,session,win_30m,ret_30m,ret_60m,ret_session,tier,gamma_regime,dte,spot_at_signal")
              .eq("symbol",symbol).in_("pattern_type",["BEAR_OB","BULL_OB"])
              .order("trade_date").range(page,page+999).execute())
        batch=resp.data or []; rows.extend(batch)
        if len(batch)<1000: break
        page+=1000
    print(f" {len(rows)}")
    return rows


def build_po3_map(symbol, bars_by_date, d_zones):
    cutoff=OPEN_END[0]*60+OPEN_END[1]
    sorted_dates=sorted(bars_by_date.keys())
    prior_close={}
    for i,d in enumerate(sorted_dates):
        if i>0:
            prev=bars_by_date.get(sorted_dates[i-1],[])
            if prev: prior_close[d]=float(prev[-1]["close"])
    result={}
    for session_date in sorted_dates:
        if session_date not in d_zones: result[session_date]="PO3_NONE"; continue
        day_bars=bars_by_date[session_date]
        if len(day_bars)<4: result[session_date]="PO3_NONE"; continue
        z=d_zones[session_date]; pdh=z.get("PDH"); pdl=z.get("PDL")
        session_open=float(day_bars[0]["open"])
        prev_cls=prior_close.get(session_date)
        gap_pct=(session_open-prev_cls)/prev_cls if prev_cls else None
        label="PO3_NONE"; pdh_found=pdl_found=False; n=len(day_bars)
        for i,bar in enumerate(day_bars):
            t=bar_minutes(bar["_dt"])
            if t>=cutoff: break
            high=float(bar["high"]); low=float(bar["low"])
            if not pdh_found and pdh and high>=pdh*(1+SWEEP_THRESHOLD):
                for j in range(i+1,min(i+REVERSAL_MAX_BARS+1,n)):
                    if float(day_bars[j]["close"])<=pdh*(1-REVERSAL_THRESHOLD):
                        if session_open>=pdh*0.999:
                            sw=(high-pdh)/pdh*100
                            if not(gap_pct and abs(gap_pct)>PDH_GAP_MAX) and \
                               not(PDH_DEPTH_BLOCK_LO<=sw<PDH_DEPTH_BLOCK_HI):
                                label="PO3_BEARISH"
                        pdh_found=True; break
            if not pdl_found and pdl and low<=pdl*(1-SWEEP_THRESHOLD):
                for j in range(i+1,min(i+REVERSAL_MAX_BARS+1,n)):
                    if float(day_bars[j]["close"])>=pdl*(1+REVERSAL_THRESHOLD):
                        if session_open<=pdl*1.001 and label=="PO3_NONE":
                            sw=(pdl-low)/pdl*100
                            if sw>=PDL_DEPTH_MIN: label="PO3_BULLISH"
                        pdl_found=True; break
            if pdh_found and pdl_found: break
        result[session_date]=label
    return result


def section(label):
    print(f"\n{'═'*68}\n  {label}\n{'═'*68}")

def subsection(label):
    print(f"\n  {'─'*58}\n  {label}\n  {'─'*58}")


def ev_table(signals, label, symbol, is_bear=True):
    """
    Compute EV metrics from hist_pattern_signals.
    ret_30m is in percentage points → divide by 100 for decimal.
    For BEAR_OB: win when ret_30m < 0 (spot fell).
    For BULL_OB: win when ret_30m > 0 (spot rose).
    """
    spot = SPOT_APPROX[symbol]
    valid = [s for s in signals if s.get("ret_30m") is not None]
    if not valid:
        print(f"\n  {label}: no ret_30m data (N={len(signals)})")
        return None

    # Convert to decimal fraction
    rets = [float(s["ret_30m"]) / 100 for s in valid]

    # Win = spot moved in predicted direction
    wins  = [r for r in rets if (r < 0 if is_bear else r > 0)]
    losses= [r for r in rets if (r >= 0 if is_bear else r <= 0)]

    wr    = len(wins) / len(rets) if rets else 0
    avg_w = mean([abs(r) for r in wins])   # magnitude of wins (always positive)
    avg_l = mean([abs(r) for r in losses]) # magnitude of losses (always positive)

    # EV: WR × avg_win - (1-WR) × avg_loss (in trader's direction)
    ev = (wr * (avg_w or 0)) - ((1-wr) * (avg_l or 0)) if (avg_w and avg_l) else None

    # Kelly fraction: f = (WR*avg_win - (1-WR)*avg_loss) / avg_win
    kelly = ev / avg_w if (ev and avg_w) else None

    print(f"\n  [{label}] N={len(valid)}  symbol={symbol}")
    print(f"  {'WR':<18}: {wr:.1%}  ({len(wins)} wins / {len(losses)} losses)")
    if avg_w:
        print(f"  {'Mean win (spot)':<18}: {avg_w:.4%}  = {avg_w*spot:.1f} pts")
    if avg_l:
        print(f"  {'Mean loss (spot)':<18}: {avg_l:.4%}  = {avg_l*spot:.1f} pts")
    if avg_w and avg_l:
        rr = avg_w / avg_l
        print(f"  {'Win/Loss ratio':<18}: {rr:.2f}x  ({'favourable' if rr >= 1 else 'unfavourable'})")
    if ev is not None:
        print(f"  {'EV per trade':<18}: {ev:.4%}  = {ev*spot:.1f} pts")
        print(f"  {'Full Kelly f':<18}: {kelly:.2f}  ({kelly*100:.0f}% of risk capital)")
        print(f"  {'Half Kelly f':<18}: {kelly/2:.2f}  ({kelly/2*100:.0f}% of risk capital)")

    # Percentile distribution of wins
    if wins:
        wins_abs = sorted([abs(r) for r in wins])
        p25 = pctile(wins_abs, 25); p75 = pctile(wins_abs, 75)
        print(f"  {'Win P25/P75':<18}: {p25:.4%}/{p75:.4%}  = {p25*spot:.0f}/{p75*spot:.0f} pts")
        print(f"  {'Max win':<18}: {max(wins_abs):.4%}  = {max(wins_abs)*spot:.0f} pts")
    if losses:
        losses_abs = sorted([abs(r) for r in losses])
        print(f"  {'Max loss':<18}: {max(losses_abs):.4%}  = {max(losses_abs)*spot:.0f} pts")

    return {"wr": wr, "avg_w": avg_w, "avg_l": avg_l, "ev": ev, "kelly": kelly}


def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 41B — Corrected EV: E4/E5 (ret_30m fix)         ║")
    print("║  Session 11 · 2026-04-28 · MERDIAN                          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("KEY FIX: ret_30m stored as percentage points (0.1351 = 0.1351%)")
    print("         Exp 41 used it as decimal fraction → 100x inflation")
    print("         Sign: BEAR_OB wins when ret_30m < 0 (spot fell)")
    print()

    all_sigs = {}
    po3_maps = {}

    for symbol, inst_id in INSTRUMENTS.items():
        print(f"\n[{symbol}]")
        bars    = fetch_bars_by_date(inst_id, symbol)
        d_zones = fetch_d_zones(symbol)
        sigs    = fetch_ob_signals(symbol)
        for s in sigs: s["symbol"] = symbol
        po3_map = build_po3_map(symbol, bars, d_zones)
        all_sigs[symbol] = sigs
        po3_maps[symbol] = po3_map

    # Attach PO3 label
    all_signals = []
    for sym, sigs in all_sigs.items():
        for s in sigs:
            s["po3"] = po3_maps[sym].get((s.get("trade_date") or "")[:10], "PO3_NONE")
            all_signals.append(s)

    section("BASELINE — All BEAR_OB / BULL_OB (replication of aggregate query)")
    for symbol in ["NIFTY", "SENSEX"]:
        bear_all = [s for s in all_signals if s["symbol"]==symbol and s["pattern_type"]=="BEAR_OB"]
        bull_all = [s for s in all_signals if s["symbol"]==symbol and s["pattern_type"]=="BULL_OB"]
        ev_table(bear_all, f"BEAR_OB all [{symbol}]", symbol, is_bear=True)
        ev_table(bull_all, f"BULL_OB all [{symbol}]", symbol, is_bear=False)

    section("EDGE 4 — BEAR_OB MIDDAY + PO3_BEARISH")
    for symbol in ["NIFTY", "SENSEX"]:
        sub = [s for s in all_signals
               if s["symbol"]==symbol
               and s["pattern_type"]=="BEAR_OB"
               and s.get("session")=="MIDDAY"
               and s["po3"]=="PO3_BEARISH"]
        ev_table(sub, f"E4 BEAR_OB MIDDAY + PO3_BEARISH [{symbol}]", symbol, is_bear=True)

    # Combined E4
    subsection("E4 COMBINED (NIFTY + SENSEX)")
    e4_all = [s for s in all_signals
              if s["pattern_type"]=="BEAR_OB"
              and s.get("session")=="MIDDAY"
              and s["po3"]=="PO3_BEARISH"]
    # Pool returns — use NIFTY spot as reference (SENSEX signals scaled separately above)
    # Just report combined WR and raw stat
    valid4 = [s for s in e4_all if s.get("ret_30m") is not None]
    if valid4:
        rets4 = [float(s["ret_30m"])/100 for s in valid4]
        wins4 = [r for r in rets4 if r < 0]
        wr4   = len(wins4)/len(rets4)
        print(f"\n  E4 combined: N={len(valid4)}  WR={wr4:.1%}")
        print(f"  (Per-symbol EV above — use symbol-specific numbers for sizing)")

    section("EDGE 5 — BULL_OB AFTERNOON + PO3_BULLISH")
    for symbol in ["NIFTY", "SENSEX"]:
        sub = [s for s in all_signals
               if s["symbol"]==symbol
               and s["pattern_type"]=="BULL_OB"
               and s.get("session")=="AFTERNOON"
               and s["po3"]=="PO3_BULLISH"]
        ev_table(sub, f"E5 BULL_OB AFT + PO3_BULLISH [{symbol}]", symbol, is_bear=False)

    section("EDGE 1 — BEAR_OB MIDDAY BASELINE vs E4 LIFT")
    for symbol in ["NIFTY", "SENSEX"]:
        base = [s for s in all_signals
                if s["symbol"]==symbol
                and s["pattern_type"]=="BEAR_OB"
                and s.get("session")=="MIDDAY"]
        print(f"\n  BEAR_OB MIDDAY baseline [{symbol}] (no PO3 filter):")
        r = ev_table(base, f"BEAR_OB MIDDAY baseline [{symbol}]", symbol, is_bear=True)

    section("SUMMARY TABLE — EV per trade across edges")
    print("""
  All returns in spot %. Multiply by spot price for points.
  Positive EV = edge exists. Half-Kelly = recommended position size.

  ┌──────────────────────────────────────┬──────┬──────────┬──────────┬───────┬──────────┐
  │ Edge                                 │  WR  │ Win(pts) │ Lose(pts)│  EV%  │ ½-Kelly  │
  ├──────────────────────────────────────┼──────┼──────────┼──────────┼───────┼──────────┤
  │ E1 PDH sweep EOD (NIFTY)             │ 93%  │  (see    │   35B/C) │       │          │
  │ E1 PDH sweep EOD (SENSEX)            │ 89%  │  Exp     │   35B/C) │       │          │
  │ E4 BEAR_OB MID+PO3 (NIFTY)          │ see  │  above   │          │  see  │  above   │
  │ E4 BEAR_OB MID+PO3 (SENSEX)         │ see  │  above   │          │  see  │  above   │
  │ E5 BULL_OB AFT+PO3 (SENSEX)         │ see  │  above   │          │  see  │  above   │
  └──────────────────────────────────────┴──────┴──────────┴──────────┴───────┴──────────┘

  E6/E7 (weekly sweeps): EV from Exp 39B
    E6 PWL EOW: mean=+0.282% ≈ +68pts NIFTY / +226pts SENSEX
    E6 T+2D:    mean=+0.667% ≈ +160pts NIFTY / +534pts SENSEX
    E7 confluence: same magnitude, 100% WR EOD day → maximum size
    Next-week CE: ~80-120% option return on T+2D move

  E3 PDH DTE<3 current-week PE (from Exp 41):
    NIFTY: mean +46%, median +24% on current-week PE
    SENSEX: mean +125%, median +57% on current-week PE
    ← Current-week confirmed winner over next-week
""")

    section("STOP LOSS FRAMEWORK — UPDATED with corrected MAE")
    print("""
  From Exp 41 MAE analysis (correctly computed — those are spot returns):
  MAE was computed correctly in Exp 41. Only ret_30m P&L was wrong.

  E1 PDH sweep (NIFTY):  MAE P90 = 94pts  → set stop at 100pts above PDH
  E1 PDH sweep (SENSEX): MAE P90 = 373pts → set stop at 400pts above PDH
  E2 PDL sweep (NIFTY):  MAE P90 = 116pts → set stop at 120pts below PDL
  E2 PDL sweep (SENSEX): MAE P90 = 379pts → set stop at 400pts below PDL

  IMPLICATION for SENSEX E1/E2:
    400pt stop on SENSEX ATM PE/CE (premium ~₹180-250):
    If adverse move = 400pts, option already down ~50-70% before recovery.
    Verdict: SENSEX E1/E2 entry at sweep is NOT practical with short-DTE options.
    Use SENSEX options only for E6/E7 (multi-day, next-week, wider premium).

    NIFTY E1 is clean: 94pt stop, ATM PE ~₹80-120.
    Adverse move = 94pts → option down ~30% → manageable before recovery.
""")


if __name__ == "__main__":
    main()
