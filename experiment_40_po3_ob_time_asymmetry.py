#!/usr/bin/env python3
"""
experiment_40_po3_ob_time_asymmetry.py
MERDIAN Experiment 40 — PO3 × OB Time Asymmetry Deep Drill

Origin:
    Exp 38 found a buried asymmetry:
      BEAR_OB MIDDAY  + PO3_BEARISH = 88.2% WR (N=17) ← distribution begins midday
      BULL_OB AFTERNOON + PO3_BULLISH = 64.5% WR (N=31) ← accumulation resolves late
      BEAR_OB AFTERNOON + PO3_BEARISH = 33.3% ← move already done by afternoon
      BULL_OB MIDDAY  + PO3_BULLISH  = 30.3% ← premature, not ready yet

    Structural explanation:
      - Bearish distribution: institutions sell into the midday lull (11:30-13:30)
        after the morning manipulation. BEAR_OB in midday = distribution entry.
      - Bullish accumulation: buyers absorb selling pressure all day, resolve at
        London open (13:30+). BULL_OB in afternoon = accumulation breakout.
      - Mixing MIDDAY and AFTERNOON destroys both signals.

    This experiment tests each signal independently with full drill:
    1. BEAR_OB MIDDAY + PO3_BEARISH — primary signal
    2. BULL_OB AFTERNOON + PO3_BULLISH — secondary signal
    Adding: DTE, tier, gamma, trajectory (T+30m, T+60m), sweep depth as sub-buckets

Pass criteria:
    Signal 1: N>=12, WR>=80%
    Signal 2: N>=20, WR>=62%
    Lift vs same-session baseline >= 15pp for Signal 1, >= 12pp for Signal 2

Data: hist_pattern_signals + PO3 map (35C filtered config)
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
    print("ERROR"); sys.exit(1)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}
SWEEP_THRESHOLD=0.0005; REVERSAL_THRESHOLD=0.001; REVERSAL_MAX_BARS=6
OPEN_END=(10,0); PDH_GAP_MAX=0.005
PDH_DEPTH_BLOCK_LO=0.10; PDH_DEPTH_BLOCK_HI=0.20; PDL_DEPTH_MIN=0.10

PASS_N1=12; PASS_WR1=0.80; LIFT1=0.15
PASS_N2=20; PASS_WR2=0.62; LIFT2=0.12


def parse_ts(ts_str):
    return datetime.fromisoformat(ts_str.replace("Z","+00:00")).replace(tzinfo=None)
def bar_minutes(dt): return dt.hour*60+dt.minute
def pct(v): return f"{v:.1%}"
def mean(lst): return sum(lst)/len(lst) if lst else None


def fetch_bars_by_date(instrument_id, label):
    print(f"  [{label}] bars...", end="", flush=True)
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


def fetch_zones(symbol):
    resp=(supabase.table("hist_ict_htf_zones").select("as_of_date,pattern_type,zone_high,zone_low")
          .eq("symbol",symbol).eq("timeframe","D").in_("pattern_type",["PDH","PDL"]).execute())
    zones=defaultdict(dict)
    for row in (resp.data or []):
        d=row["as_of_date"][:10]; pt=row["pattern_type"]
        if pt=="PDH": zones[d]["PDH"]=float(row["zone_high"])
        else: zones[d]["PDL"]=float(row.get("zone_low") or row["zone_high"])
    return dict(zones)


def build_po3_map(symbol, bars_by_date, zones):
    cutoff=OPEN_END[0]*60+OPEN_END[1]
    sorted_dates=sorted(bars_by_date.keys())
    prior_close={}
    for i,d in enumerate(sorted_dates):
        if i>0:
            prev=bars_by_date.get(sorted_dates[i-1],[])
            if prev: prior_close[d]=float(prev[-1]["close"])
    result={}
    for session_date in sorted_dates:
        if session_date not in zones: result[session_date]="PO3_NONE"; continue
        day_bars=bars_by_date[session_date]
        if len(day_bars)<4: result[session_date]="PO3_NONE"; continue
        z=zones[session_date]; pdh=z.get("PDH"); pdl=z.get("PDL")
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


def fetch_ob_signals(symbol):
    print(f"  [{symbol}] OB signals...", end="", flush=True)
    rows, page = [], 0
    while True:
        resp=(supabase.table("hist_pattern_signals")
              .select("trade_date,bar_ts,pattern_type,session,win_30m,win_60m,tier,gamma_regime,dte")
              .eq("symbol",symbol).in_("pattern_type",["BEAR_OB","BULL_OB"])
              .order("trade_date").range(page,page+999).execute())
        batch=resp.data or []; rows.extend(batch)
        if len(batch)<1000: break
        page+=1000
    print(f" {len(rows)}")
    return rows


def section(label):
    print(f"\n{'─'*65}\n  {label}\n{'─'*65}")


def report(sigs, label, wk="win_30m", pass_wr=None, n_min=5):
    valid=[s for s in sigs if s.get(wk) is not None]
    if len(valid)<n_min:
        print(f"  {label:<60}  N={len(valid):>3}  (insufficient)")
        return None
    wr=sum(1 for s in valid if s[wk])/len(valid)
    flag=""
    if pass_wr is not None: flag=" ✅" if wr>=pass_wr else " ❌"
    print(f"  {label:<60}  N={len(valid):>3}  WR={pct(wr)}{flag}")
    return wr


def trajectory(sigs, label):
    print(f"\n  [{label}] T+30m vs T+60m:")
    for wk, lbl in [("win_30m","T+30m"),("win_60m","T+60m")]:
        valid=[s for s in sigs if s.get(wk) is not None]
        if not valid: continue
        wr=sum(1 for s in valid if s[wk])/len(valid)
        print(f"    {lbl}: N={len(valid):>3}  WR={pct(wr)}")


def print_results(all_signals, po3_maps):
    for s in all_signals:
        s["po3"]=po3_maps.get(s["symbol"],{}).get((s.get("trade_date") or "")[:10],"PO3_NONE")

    bear=[s for s in all_signals if s["pattern_type"]=="BEAR_OB"]
    bull=[s for s in all_signals if s["pattern_type"]=="BULL_OB"]

    # ── Signal 1: BEAR_OB MIDDAY + PO3_BEARISH ───────────────────────────────
    section("SIGNAL 1 — BEAR_OB MIDDAY + PO3_BEARISH")

    bear_mid_base = [s for s in bear if s.get("session")=="MIDDAY"]
    bear_mid_po3  = [s for s in bear_mid_base if s["po3"]=="PO3_BEARISH"]
    base_wr1 = report(bear_mid_base, "BEAR_OB MIDDAY baseline (no PO3)")
    s1_wr    = report(bear_mid_po3,  "BEAR_OB MIDDAY + PO3_BEARISH", pass_wr=PASS_WR1)
    if base_wr1 and s1_wr:
        lift = s1_wr - base_wr1
        print(f"\n  Lift vs baseline: {lift:+.1%}  ({'≥15pp ✅' if lift>=LIFT1 else f'<15pp ❌'})")
    trajectory(bear_mid_po3, "BEAR_OB MIDDAY + PO3_BEARISH")

    section("SIGNAL 1 — Sub-buckets")
    for sym in ["NIFTY","SENSEX"]:
        report([s for s in bear_mid_po3 if s["symbol"]==sym], f"  BEAR_OB MID+PO3 [{sym}]", n_min=3)
    print()
    for tier in ["TIER1","TIER2"]:
        sub=[s for s in bear_mid_po3 if s.get("tier")==tier]
        if sub: report(sub, f"  BEAR_OB MID+PO3 {tier}", n_min=3)
    print()
    for regime in ["LONG_GAMMA","SHORT_GAMMA"]:
        sub=[s for s in bear_mid_po3 if s.get("gamma_regime")==regime]
        if sub: report(sub, f"  BEAR_OB MID+PO3 {regime}", n_min=3)
    print()
    for dte_buck, lo, hi in [("DTE=0",0,1),("DTE=1",1,2),("DTE=2",2,3),("DTE3+",3,99)]:
        sub=[s for s in bear_mid_po3 if s.get("dte") is not None and lo<=s["dte"]<hi]
        if sub: report(sub, f"  BEAR_OB MID+PO3 {dte_buck}", n_min=3)

    # Counter signal 1
    bear_mid_counter=[s for s in bear_mid_base if s["po3"]=="PO3_BULLISH"]
    report(bear_mid_counter, "BEAR_OB MIDDAY + PO3_BULLISH (counter)")

    # ── Signal 2: BULL_OB AFTERNOON + PO3_BULLISH ────────────────────────────
    section("SIGNAL 2 — BULL_OB AFTERNOON + PO3_BULLISH")

    bull_aft_base = [s for s in bull if s.get("session")=="AFTERNOON"]
    bull_aft_po3  = [s for s in bull_aft_base if s["po3"]=="PO3_BULLISH"]
    base_wr2 = report(bull_aft_base, "BULL_OB AFTERNOON baseline (no PO3)")
    s2_wr    = report(bull_aft_po3,  "BULL_OB AFTERNOON + PO3_BULLISH", pass_wr=PASS_WR2)
    if base_wr2 and s2_wr:
        lift = s2_wr - base_wr2
        print(f"\n  Lift vs baseline: {lift:+.1%}  ({'≥12pp ✅' if lift>=LIFT2 else f'<12pp ❌'})")
    trajectory(bull_aft_po3, "BULL_OB AFTERNOON + PO3_BULLISH")

    section("SIGNAL 2 — Sub-buckets")
    for sym in ["NIFTY","SENSEX"]:
        report([s for s in bull_aft_po3 if s["symbol"]==sym], f"  BULL_OB AFT+PO3 [{sym}]", n_min=3)
    print()
    for tier in ["TIER1","TIER2"]:
        sub=[s for s in bull_aft_po3 if s.get("tier")==tier]
        if sub: report(sub, f"  BULL_OB AFT+PO3 {tier}", n_min=3)
    print()
    for regime in ["LONG_GAMMA","SHORT_GAMMA"]:
        sub=[s for s in bull_aft_po3 if s.get("gamma_regime")==regime]
        if sub: report(sub, f"  BULL_OB AFT+PO3 {regime}", n_min=3)
    print()
    for dte_buck, lo, hi in [("DTE=0",0,1),("DTE=1",1,2),("DTE=2",2,3),("DTE3+",3,99)]:
        sub=[s for s in bull_aft_po3 if s.get("dte") is not None and lo<=s["dte"]<hi]
        if sub: report(sub, f"  BULL_OB AFT+PO3 {dte_buck}", n_min=3)

    bull_aft_counter=[s for s in bull_aft_base if s["po3"]=="PO3_BEARISH"]
    report(bull_aft_counter, "BULL_OB AFTERNOON + PO3_BEARISH (counter)")

    # ── Why MIDDAY works for BEAR but not BULL ────────────────────────────────
    section("STRUCTURAL ASYMMETRY — Full 2×2 matrix")
    print()
    combos = [
        (bear, "MIDDAY",    "PO3_BEARISH", "BEAR_OB MIDDAY + PO3_BEARISH   (dist. entry)"),
        (bear, "AFTERNOON", "PO3_BEARISH", "BEAR_OB AFTERNOON + PO3_BEARISH (move done?)"),
        (bull, "MIDDAY",    "PO3_BULLISH", "BULL_OB MIDDAY + PO3_BULLISH   (premature?)"),
        (bull, "AFTERNOON", "PO3_BULLISH", "BULL_OB AFTERNOON + PO3_BULLISH (LKZ entry)"),
        (bear, "MIDDAY",    "PO3_BULLISH", "BEAR_OB MIDDAY + PO3_BULLISH   (counter)"),
        (bull, "AFTERNOON", "PO3_BEARISH", "BULL_OB AFTERNOON + PO3_BEARISH (counter)"),
    ]
    for src, sess, po3_label, label in combos:
        sub=[s for s in src if s.get("session")==sess and s["po3"]==po3_label]
        report(sub, label, n_min=3)

    # ── Pass/fail ─────────────────────────────────────────────────────────────
    section("PASS / FAIL")
    def assess(sigs, label, pass_wr, n_req):
        valid=[s for s in sigs if s.get("win_30m") is not None]
        if not valid: print(f"  {label}: INSUFFICIENT DATA"); return False
        wr=sum(1 for s in valid if s["win_30m"])/len(valid)
        ok=len(valid)>=n_req and wr>=pass_wr
        print(f"  {label}: {'✅ PASS' if ok else '❌ FAIL'}  N={len(valid)}  WR={pct(wr)}")
        return ok

    p1=assess(bear_mid_po3, "Signal 1: BEAR_OB MIDDAY + PO3_BEARISH", PASS_WR1, PASS_N1)
    p2=assess(bull_aft_po3, "Signal 2: BULL_OB AFTERNOON + PO3_BULLISH", PASS_WR2, PASS_N2)
    print()
    if p1:
        print("  Signal 1 PASS → ENH candidate: gate BEAR_OB MIDDAY entries on PO3_BEARISH morning sweep")
        print("                   Expected: fires ~6-9 times per symbol per quarter")
    if p2:
        print("  Signal 2 PASS → ENH candidate: gate BULL_OB AFTERNOON entries on PO3_BULLISH morning sweep")
    if not p1 and not p2:
        print("  Both fail — PO3 time-asymmetry thesis not confirmed at these thresholds")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 40 — PO3 × OB Time Asymmetry Deep Drill         ║")
    print("║  Session 11 · 2026-04-28 · MERDIAN                          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("Signal 1: BEAR_OB MIDDAY + PO3_BEARISH  (pass: N>=12, WR>=80%, lift>=15pp)")
    print("Signal 2: BULL_OB AFTERNOON + PO3_BULLISH (pass: N>=20, WR>=62%, lift>=12pp)")
    print()
    po3_maps=[]; all_signals=[]
    maps={}
    for symbol, inst_id in INSTRUMENTS.items():
        print(f"\n[{symbol}]")
        bars=fetch_bars_by_date(inst_id, symbol)
        zones=fetch_zones(symbol)
        print(f"  [{symbol}] Building PO3 map...", end="", flush=True)
        po3=build_po3_map(symbol, bars, zones)
        n_lab=sum(1 for v in po3.values() if v!="PO3_NONE")
        print(f" {n_lab} labelled sessions")
        maps[symbol]=po3
        sigs=fetch_ob_signals(symbol)
        for s in sigs: s["symbol"]=symbol
        all_signals.extend(sigs)
    if not all_signals: print("NO SIGNALS."); sys.exit(1)
    print_results(all_signals, maps)

if __name__ == "__main__":
    main()
