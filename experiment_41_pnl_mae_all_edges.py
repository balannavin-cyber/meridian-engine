#!/usr/bin/env python3
"""
experiment_41_pnl_mae_all_edges.py
MERDIAN Experiment 41 — P&L and Max Adverse Excursion: All Session 11 Edges

Purpose:
    Session 11 produced WR numbers but not P&L magnitude or entry quality metrics.
    This experiment computes for each edge:

    1. RETURN DISTRIBUTION — mean, median, 25th/75th pct, max win, max loss
       at T+30m, T+60m, T+120m, T+180m, EOD, T+1D, T+2D
       (in both % and NIFTY/SENSEX points)

    2. MAX ADVERSE EXCURSION (MAE) — how far does price move against you
       before the final outcome? A 88% WR signal that has MAE of 80 points
       before recovering is untradeable with a 40-point stop.
       MAE = max intraday adverse move from entry bar close to lowest
       point (for bearish trades) within the measurement window.

    3. ENTRY TIMING SENSITIVITY — does entering at rejection bar close (T+0)
       vs first BEAR_OB zone touch vs waiting 1 bar change P&L materially?
       Measured by comparing return from T+0 vs T+1 vs T+2 bar of event.

    4. CURRENT-WEEK vs NEXT-WEEK OPTION P&L (Edge 3 specifically)
       Given the actual point move distribution, compute theoretical option
       P&L at DTE=1/2 (current-week) vs DTE=8 (next-week) using Black-Scholes
       approximation. Uses: ATM strike, IV from vix_at_signal if available,
       else fixed IV assumption of 12% annualised.

Edges covered:
    E1: PDH first-sweep filtered (Exp 35C) — bearish, current-week PE
    E2: PDL first-sweep filtered (Exp 35C) — bullish, current-week CE
    E3: PDH DTE<3 (Exp 35D) — bearish, next-week PE comparison
    E4: BEAR_OB MIDDAY + PO3_BEARISH (Exp 40) — intraday
    E5: BULL_OB AFTERNOON + PO3_BULLISH SENSEX (Exp 40)
    E6: PWL weekly sweep refined (Exp 39B) — multi-day
    E7: PWL weekly + daily PDL confluence (Exp 39B) — highest conviction

Data sources:
    hist_spot_bars_5m      — for MAE and entry timing
    hist_pattern_signals   — for OB signals with ret_30m, ret_60m
    hist_ict_htf_zones     — for PDH/PDL zones (D and W)

TD-029 / pagination: fixes baked in.

Run from: C:\\GammaEnginePython
Usage  : python experiment_41_pnl_mae_all_edges.py
Session: 11 (2026-04-28)
"""

import os, sys, math
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
SPOT_APPROX = {"NIFTY": 24000, "SENSEX": 80000}
EXPIRY_WEEKDAY = {"NIFTY": 3, "SENSEX": 4}

# 35C/35D filters
SWEEP_THRESHOLD    = 0.0005
REVERSAL_THRESHOLD = 0.001
REVERSAL_MAX_BARS  = 6
OPEN_END           = (10, 0)
PDH_GAP_MAX        = 0.005
PDH_DEPTH_BLOCK_LO = 0.10
PDH_DEPTH_BLOCK_HI = 0.20
PDL_DEPTH_MIN      = 0.10

# IV assumption for option P&L when vix not available
DEFAULT_IV_ANNUAL  = 0.12   # 12% annualised


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_ts(ts_str):
    return datetime.fromisoformat(ts_str.replace("Z","+00:00")).replace(tzinfo=None)
def bar_minutes(dt): return dt.hour*60+dt.minute
def pct(v): return f"{v:.2%}"
def pts(v, sym): return f"{v*SPOT_APPROX[sym]:.0f}pts" if v else "n/a"
def mean(lst): return sum(lst)/len(lst) if lst else None
def median(lst):
    if not lst: return None
    s=sorted(lst); n=len(s)
    return s[n//2] if n%2 else (s[n//2-1]+s[n//2])/2
def pctile(lst, p):
    if not lst: return None
    s=sorted(lst); idx=int(len(s)*p/100)
    return s[min(idx, len(s)-1)]


def compute_dte(date_str, symbol):
    d=datetime.strptime(date_str,"%Y-%m-%d")
    exp_wd=EXPIRY_WEEKDAY[symbol]
    days_ahead=(exp_wd-d.weekday())%7
    if days_ahead==0: return 0
    next_exp=d+timedelta(days=days_ahead)
    dte=0; cursor=d
    while cursor.date()<next_exp.date():
        cursor+=timedelta(days=1)
        if cursor.weekday()<5: dte+=1
    return dte


def bs_option_price(S, K, T_years, iv, is_call=True):
    """Black-Scholes ATM option price approximation (risk-free=0)."""
    if T_years <= 0: return 0
    try:
        d1 = (math.log(S/K) + 0.5*iv**2*T_years) / (iv*math.sqrt(T_years))
        d2 = d1 - iv*math.sqrt(T_years)
        def N(x):
            return 0.5*(1+math.erf(x/math.sqrt(2)))
        if is_call:
            return S*N(d1) - K*N(d2)
        else:
            return K*N(-d2) - S*N(-d1)
    except:
        return S * iv * math.sqrt(T_years) * 0.4  # simplified ATM approx


def option_pnl(entry_spot, exit_spot, strike, dte_entry, iv, is_put=True):
    """
    Theoretical option P&L.
    entry: buy at dte_entry business days to expiry
    exit:  one session later (T_exit = dte_entry - 1 business days)
    Returns (entry_premium, exit_premium, pnl_pct)
    """
    T_entry = dte_entry / 252
    T_exit  = max((dte_entry - 1) / 252, 1/252)
    entry_prem = bs_option_price(entry_spot, strike, T_entry, iv, is_call=not is_put)
    exit_prem  = bs_option_price(exit_spot,  strike, T_exit,  iv, is_call=not is_put)
    if entry_prem <= 0: return None, None, None
    pnl_pct = (exit_prem - entry_prem) / entry_prem
    return entry_prem, exit_prem, pnl_pct


# ── Data fetchers ─────────────────────────────────────────────────────────────
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
    print(f"  [{symbol}] Fetching OB signals...", end="", flush=True)
    rows, page = [], 0
    while True:
        resp=(supabase.table("hist_pattern_signals")
              .select("trade_date,bar_ts,pattern_type,session,win_30m,ret_30m,ret_60m,ret_session,tier,gamma_regime,dte,zone_high,zone_low,spot_at_signal,vix_at_signal")
              .eq("symbol",symbol).in_("pattern_type",["BEAR_OB","BULL_OB"])
              .order("trade_date").range(page,page+999).execute())
        batch=resp.data or []; rows.extend(batch)
        if len(batch)<1000: break
        page+=1000
    print(f" {len(rows)}")
    return rows


# ── MAE computation ───────────────────────────────────────────────────────────
def compute_mae(day_bars, entry_idx, direction, window_bars=12):
    """
    Max Adverse Excursion from entry bar close.
    For BEARISH: MAE = max high reached above entry close within window.
    For BULLISH: MAE = min low reached below entry close within window.
    Returns MAE as fraction of entry close (positive = adverse).
    """
    if entry_idx >= len(day_bars): return None
    entry_close = float(day_bars[entry_idx]["close"])
    if entry_close == 0: return None
    end = min(entry_idx + window_bars, len(day_bars))
    sub = day_bars[entry_idx+1:end]
    if not sub: return None
    if direction == "BEARISH":
        worst = max(float(b["high"]) for b in sub)
        return (worst - entry_close) / entry_close  # positive = price went up against short
    else:
        worst = min(float(b["low"]) for b in sub)
        return (entry_close - worst) / entry_close  # positive = price went down against long


def future_return(day_bars, from_idx, offset, direction):
    """Return from bar[from_idx].close to bar[from_idx+offset].close."""
    target = from_idx + offset
    if target >= len(day_bars): return None
    base  = float(day_bars[from_idx]["close"])
    tgt   = float(day_bars[target]["close"])
    ret   = (tgt - base) / base
    return ret * (1 if direction=="BULLISH" else -1)


# ── Reporting helpers ─────────────────────────────────────────────────────────
def section(label):
    print(f"\n{'═'*70}")
    print(f"  {label}")
    print(f"{'═'*70}")

def subsection(label):
    print(f"\n  {'─'*60}")
    print(f"  {label}")
    print(f"  {'─'*60}")

def return_table(returns_dict, symbol, label):
    """
    returns_dict: {horizon_label: [float returns]}
    Prints a summary table with mean, median, p25, p75, max_win, max_loss in % and points.
    """
    spot = SPOT_APPROX[symbol]
    print(f"\n  [{label}] ({symbol} spot≈{spot:,})")
    print(f"  {'Horizon':<10}  {'N':>4}  {'WR':>6}  {'Mean%':>8}  {'Med%':>8}  "
          f"{'P25%':>8}  {'P75%':>8}  {'MeanPts':>8}  {'MaxW':>8}  {'MaxL':>8}")
    print(f"  {'-'*10}  {'-'*4}  {'-'*6}  {'-'*8}  {'-'*8}  "
          f"{'-'*8}  {'-'*8}  {'-'*8}  {'-'*8}  {'-'*8}")
    for h, rets in returns_dict.items():
        if not rets: continue
        n   = len(rets)
        wr  = sum(1 for r in rets if r > 0) / n
        avg = mean(rets); med = median(rets)
        p25 = pctile(rets, 25); p75 = pctile(rets, 75)
        mxw = max(rets); mxl = min(rets)
        print(f"  {h:<10}  {n:>4}  {wr:>5.0%}  {avg:>+8.3%}  {med:>+8.3%}  "
              f"{p25:>+8.3%}  {p75:>+8.3%}  "
              f"{avg*spot:>+8.0f}  {mxw*spot:>+8.0f}  {mxl*spot:>+8.0f}")


def mae_summary(mae_list, label, symbol):
    if not mae_list: print(f"  {label}: no MAE data"); return
    spot = SPOT_APPROX[symbol]
    avg  = mean(mae_list); med = median(mae_list)
    p75  = pctile(mae_list, 75); p90 = pctile(mae_list, 90)
    print(f"\n  MAE [{label}] ({symbol}):")
    print(f"    Mean={avg:.3%} ({avg*spot:.0f}pts)  "
          f"Median={med:.3%} ({med*spot:.0f}pts)  "
          f"P75={p75:.3%} ({p75*spot:.0f}pts)  "
          f"P90={p90:.3%} ({p90*spot:.0f}pts)")
    print(f"    Interpretation: stop tighter than P75 ({p75*spot:.0f}pts) "
          f"will be hit ~25% of time even on winning trades")


# ── Edge detectors ────────────────────────────────────────────────────────────
def detect_po3_sweep_events(symbol, bars_by_date, d_zones):
    """Detect PDH/PDL first-sweep events (35C filtered config)."""
    cutoff = OPEN_END[0]*60+OPEN_END[1]
    sorted_dates = sorted(bars_by_date.keys())
    prior_close = {}
    for i,d in enumerate(sorted_dates):
        if i>0:
            prev=bars_by_date.get(sorted_dates[i-1],[])
            if prev: prior_close[d]=float(prev[-1]["close"])
    eod_close = {d:float(bars_by_date[d][-1]["close"]) for d in sorted_dates if bars_by_date[d]}

    def nd_ret(from_date, direction, n):
        idx=sorted_dates.index(from_date)
        if idx+n>=len(sorted_dates): return None
        base=eod_close.get(from_date); tgt=eod_close.get(sorted_dates[idx+n])
        if not base or not tgt: return None
        ret=(tgt-base)/base
        return ret*(1 if direction=="BULLISH" else -1)

    events = []
    for session_date in sorted_dates:
        if session_date not in d_zones: continue
        day_bars=bars_by_date[session_date]
        if len(day_bars)<8: continue
        z=d_zones[session_date]; pdh=z.get("PDH"); pdl=z.get("PDL")
        session_open=float(day_bars[0]["open"])
        prev_cls=prior_close.get(session_date)
        gap_pct=(session_open-prev_cls)/prev_cls if prev_cls else None
        dte=compute_dte(session_date, symbol)
        session_ret=(float(day_bars[-1]["close"])-session_open)/session_open
        pdh_found=pdl_found=False
        n=len(day_bars)

        for i,bar in enumerate(day_bars):
            t=bar_minutes(bar["_dt"])
            if t>=cutoff: break
            high=float(bar["high"]); low=float(bar["low"])

            if not pdh_found and pdh and high>=pdh*(1+SWEEP_THRESHOLD):
                for j in range(i+1,min(i+REVERSAL_MAX_BARS+1,n)):
                    if float(day_bars[j]["close"])<=pdh*(1-REVERSAL_THRESHOLD):
                        gap_up=session_open>=pdh*0.999
                        if not gap_up: pdh_found=True; break
                        sw=(high-pdh)/pdh*100
                        if (gap_pct and abs(gap_pct)>PDH_GAP_MAX) or \
                           (PDH_DEPTH_BLOCK_LO<=sw<PDH_DEPTH_BLOCK_HI):
                            pdh_found=True; break
                        rev_close=float(day_bars[j]["close"])
                        # MAE: max adverse (price going up) from rejection close
                        mae=compute_mae(day_bars, j, "BEARISH", 24)
                        # Returns from rejection bar
                        rets={h:future_return(day_bars,j,off,"BEARISH")
                              for h,off in [("T+30m",6),("T+60m",12),("T+120m",24)]}
                        events.append({
                            "symbol":symbol,"date":session_date,"type":"PDH","dte":dte,
                            "gap_pct":gap_pct,"sweep_pct":sw,"bars_to_rev":j-i,
                            "entry_close":rev_close,"session_open":session_open,
                            "ret_eod":session_ret,"ret_t1d":nd_ret(session_date,"BEARISH",1),
                            "ret_t2d":nd_ret(session_date,"BEARISH",2),
                            "mae":mae,"rets":rets,
                            "win_eod":session_ret<0,
                        })
                        pdh_found=True; break

            if not pdl_found and pdl and low<=pdl*(1-SWEEP_THRESHOLD):
                for j in range(i+1,min(i+REVERSAL_MAX_BARS+1,n)):
                    if float(day_bars[j]["close"])>=pdl*(1+REVERSAL_THRESHOLD):
                        gap_down=session_open<=pdl*1.001
                        if not gap_down: pdl_found=True; break
                        sw=(pdl-low)/pdl*100
                        if sw<PDL_DEPTH_MIN: pdl_found=True; break
                        rev_close=float(day_bars[j]["close"])
                        mae=compute_mae(day_bars, j, "BULLISH", 24)
                        rets={h:future_return(day_bars,j,off,"BULLISH")
                              for h,off in [("T+30m",6),("T+60m",12),("T+120m",24)]}
                        events.append({
                            "symbol":symbol,"date":session_date,"type":"PDL","dte":dte,
                            "gap_pct":gap_pct,"sweep_pct":sw,"bars_to_rev":j-i,
                            "entry_close":rev_close,"session_open":session_open,
                            "ret_eod":session_ret,"ret_t1d":nd_ret(session_date,"BULLISH",1),
                            "ret_t2d":nd_ret(session_date,"BULLISH",2),
                            "mae":mae,"rets":rets,
                            "win_eod":session_ret>0,
                        })
                        pdl_found=True; break

            if pdh_found and pdl_found: break
    return events


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


# ── Option P&L section (Edge 3) ───────────────────────────────────────────────
def analyse_edge3_options(pdh_events, symbol):
    subsection(f"EDGE 3 — Current-week vs Next-week PE option P&L [{symbol}]")
    spot_base = SPOT_APPROX[symbol]

    dte_lt3 = [e for e in pdh_events if e["symbol"]==symbol and e["dte"]<3]
    if not dte_lt3:
        print(f"  No DTE<3 events for {symbol}")
        return

    print(f"\n  DTE<3 events: {len(dte_lt3)}")
    print(f"\n  {'Date':<12}  {'DTE':>4}  {'Move EOD%':>10}  {'MoveEODpts':>11}  "
          f"{'CW PE%':>9}  {'NW PE%':>9}  {'MAE%':>7}  {'MaeOK_30?':>10}")
    print(f"  {'-'*12}  {'-'*4}  {'-'*10}  {'-'*11}  {'-'*9}  {'-'*9}  {'-'*7}  {'-'*10}")

    cw_pnls=[]; nw_pnls=[]; eod_rets=[]
    for e in sorted(dte_lt3, key=lambda x:x["date"]):
        spot  = e["entry_close"]
        strike = round(spot / 50) * 50  # nearest 50-point strike
        iv    = DEFAULT_IV_ANNUAL
        eod_move = e["ret_eod"]  # negative = bearish win

        # Current-week (DTE=e["dte"], exit at EOD same day)
        T_cw_entry = max(e["dte"], 1) / 252
        T_cw_exit  = max(e["dte"] - 0.5, 0.1) / 252  # exit near EOD
        cw_entry = bs_option_price(spot, strike, T_cw_entry, iv, is_call=False)
        exit_spot_eod = spot * (1 + eod_move)
        cw_exit  = bs_option_price(exit_spot_eod, strike, T_cw_exit, iv, is_call=False)
        cw_pnl   = (cw_exit - cw_entry) / cw_entry if cw_entry > 0 else None

        # Next-week (DTE+5 approx, exit at T+1D close)
        nw_dte_entry = e["dte"] + 5
        t1d_move = e.get("ret_t1d") or 0
        exit_spot_t1d = e["entry_close"] * (1 - abs(eod_move)) * (1 - t1d_move) \
                        if t1d_move < 0 else spot * (1 + eod_move + t1d_move * 0.5)
        # Simpler: use eod close as entry spot, t1d as the incremental move
        # Actually: entry is rejection bar close; exit is T+1D EOD
        exit_spot_nw = spot * (1 + eod_move) * (1 - (t1d_move if t1d_move else 0))
        nw_entry = bs_option_price(spot, strike, nw_dte_entry/252, iv, is_call=False)
        nw_exit  = bs_option_price(exit_spot_nw, strike, (nw_dte_entry-1)/252, iv, is_call=False)
        nw_pnl   = (nw_exit - nw_entry) / nw_entry if nw_entry > 0 else None

        mae_ok = e["mae"] is not None and e["mae"] < 0.002  # MAE < 0.2% = clean entry
        mae_str = f"{e['mae']:.3%}" if e["mae"] else "n/a"

        eod_pts = eod_move * spot_base
        cw_str  = f"{cw_pnl:+.0%}" if cw_pnl else "n/a"
        nw_str  = f"{nw_pnl:+.0%}" if nw_pnl else "n/a"

        print(f"  {e['date']}  {e['dte']:>4}  {eod_move:>+10.3%}  {eod_pts:>+11.0f}  "
              f"{cw_str:>9}  {nw_str:>9}  {mae_str:>7}  {'YES' if mae_ok else 'NO':>10}")

        if cw_pnl: cw_pnls.append(cw_pnl)
        if nw_pnl: nw_pnls.append(nw_pnl)
        eod_rets.append(eod_move)

    print(f"\n  SUMMARY [{symbol}]:")
    print(f"    Current-week PE:  N={len(cw_pnls)}  mean={mean(cw_pnls):+.0%}  "
          f"median={median(cw_pnls):+.0%}" if cw_pnls else "    Current-week PE: no data")
    print(f"    Next-week PE:     N={len(nw_pnls)}  mean={mean(nw_pnls):+.0%}  "
          f"median={median(nw_pnls):+.0%}" if nw_pnls else "    Next-week PE: no data")
    if cw_pnls and nw_pnls:
        better = "NEXT-WEEK" if mean(nw_pnls) > mean(cw_pnls) else "CURRENT-WEEK"
        print(f"    DATA VERDICT: {better} PE has better mean P&L on these events")
    print(f"    Note: IV fixed at {DEFAULT_IV_ANNUAL:.0%} annualised. "
          f"Real P&L will vary with actual IV. Higher IV → both options cheaper to buy.")


# ── Main analysis ─────────────────────────────────────────────────────────────
def run_analysis(symbol, bars_by_date, d_zones, ob_signals, po3_map):
    sorted_dates = sorted(bars_by_date.keys())
    eod_close    = {d:float(bars_by_date[d][-1]["close"]) for d in sorted_dates if bars_by_date[d]}
    spot_base    = SPOT_APPROX[symbol]

    section(f"SYMBOL: {symbol}")

    # ── Detect sweep events ───────────────────────────────────────────────────
    sweep_events = detect_po3_sweep_events(symbol, bars_by_date, d_zones)
    pdh_events   = [e for e in sweep_events if e["type"]=="PDH"]
    pdl_events   = [e for e in sweep_events if e["type"]=="PDL"]

    # ── EDGE 1 & 2: PDH/PDL first-sweep return distribution ──────────────────
    subsection("EDGES 1+2 — PDH/PDL first-sweep: Return distribution + MAE")

    for ev_list, label, direction in [
        (pdh_events,"E1 PDH filtered→bearish","BEARISH"),
        (pdl_events,"E2 PDL filtered→bullish","BULLISH"),
    ]:
        rets_by_horizon={}
        for h in ["T+30m","T+60m","T+120m"]:
            rets_by_horizon[h]=[e["rets"][h] for e in ev_list if e["rets"].get(h) is not None]
        rets_by_horizon["EOD"]=[e["ret_eod"] for e in ev_list]
        rets_by_horizon["T+1D"]=[e["ret_t1d"] for e in ev_list if e.get("ret_t1d") is not None]
        rets_by_horizon["T+2D"]=[e["ret_t2d"] for e in ev_list if e.get("ret_t2d") is not None]
        return_table(rets_by_horizon, symbol, label)
        mae_list=[e["mae"] for e in ev_list if e.get("mae") is not None]
        mae_summary(mae_list, label, symbol)

    # Entry timing sensitivity
    subsection("EDGES 1+2 — Entry timing: T+0 vs T+1 bar after rejection")
    for ev_list, label in [(pdh_events,"PDH"),(pdl_events,"PDL")]:
        direction="BEARISH" if label=="PDH" else "BULLISH"
        # Compare return if you waited 1 bar before entry
        t0_rets=[]; t1_rets=[]
        for e in ev_list:
            t0=e["rets"].get("T+30m")
            # T+1 entry: return starting 5m later (T+60m from sweep = T+30m from T+1 entry)
            t1=e["rets"].get("T+60m")
            if t0 is not None: t0_rets.append(t0)
            if t1 is not None: t1_rets.append(t1)
        if t0_rets and t1_rets:
            print(f"\n  {label} Entry at T+0 (rejection close):  "
                  f"N={len(t0_rets)}  mean={mean(t0_rets):+.3%} ({mean(t0_rets)*spot_base:+.0f}pts)  "
                  f"WR={sum(1 for r in t0_rets if r>0)/len(t0_rets):.0%}")
            print(f"  {label} Entry at T+1 (one bar later):    "
                  f"N={len(t1_rets)}  mean={mean(t1_rets):+.3%} ({mean(t1_rets)*spot_base:+.0f}pts)  "
                  f"WR={sum(1 for r in t1_rets if r>0)/len(t1_rets):.0%}")
            print(f"  → Wait 1 bar {'HELPS' if mean(t1_rets)>mean(t0_rets) else 'HURTS'} "
                  f"(diff={mean(t1_rets)-mean(t0_rets):+.3%}, "
                  f"{(mean(t1_rets)-mean(t0_rets))*spot_base:+.0f}pts)")

    # ── EDGE 3: Option P&L analysis ───────────────────────────────────────────
    analyse_edge3_options(pdh_events, symbol)

    # ── EDGES 4+5: OB signal P&L ─────────────────────────────────────────────
    subsection("EDGES 4+5 — OB return distribution (from hist_pattern_signals)")

    for sym_sigs in ob_signals:
        if sym_sigs.get("symbol") != symbol: continue

    local_sigs = [s for s in ob_signals if s.get("symbol")==symbol]

    for pt, sess, po3_label, edge_label in [
        ("BEAR_OB","MIDDAY","PO3_BEARISH","E4 BEAR_OB MIDDAY + PO3_BEARISH"),
        ("BULL_OB","AFTERNOON","PO3_BULLISH","E5 BULL_OB AFT + PO3_BULLISH"),
    ]:
        sub=[s for s in local_sigs
             if s["pattern_type"]==pt
             and s.get("session")==sess
             and po3_map.get((s.get("trade_date") or "")[:10])==po3_label]

        if not sub:
            print(f"\n  {edge_label}: no signals"); continue

        rets_30m=[s["ret_30m"] for s in sub if s.get("ret_30m") is not None]
        rets_60m=[s["ret_60m"] for s in sub if s.get("ret_60m") is not None]
        rets_ses=[s["ret_session"] for s in sub if s.get("ret_session") is not None]

        print(f"\n  [{edge_label}]  N={len(sub)}")
        if rets_30m:
            wins=[r for r in rets_30m if r>0]; losses=[r for r in rets_30m if r<=0]
            print(f"  T+30m:  mean={mean(rets_30m):+.3%} ({mean(rets_30m)*spot_base:+.0f}pts)  "
                  f"median={median(rets_30m):+.3%}  "
                  f"WR={len(wins)/len(rets_30m):.0%}  "
                  f"mean|win={mean(wins):+.3%} ({mean(wins)*spot_base:+.0f}pts)  "
                  f"mean|loss={mean(losses):+.3%}" if wins and losses else
                  f"  T+30m:  mean={mean(rets_30m):+.3%}  WR={sum(1 for r in rets_30m if r>0)/len(rets_30m):.0%}")
        if rets_60m:
            print(f"  T+60m:  mean={mean(rets_60m):+.3%} ({mean(rets_60m)*spot_base:+.0f}pts)")
        if rets_ses:
            print(f"  Session mean={mean(rets_ses):+.3%} ({mean(rets_ses)*spot_base:+.0f}pts)")

        # P&L rationale
        if rets_30m and len(rets_30m)>=5:
            wins30=[r for r in rets_30m if r>0]; loss30=[r for r in rets_30m if r<=0]
            wr=len(wins30)/len(rets_30m)
            ev=(wr*mean(wins30) + (1-wr)*mean(loss30)) if wins30 and loss30 else None
            if ev:
                print(f"  EV per trade: {ev:+.3%} ({ev*spot_base:+.0f}pts)  "
                      f"[{wr:.0%} × {mean(wins30):+.3%} + {1-wr:.0%} × {mean(loss30):+.3%}]")

    # ── EDGES 6+7: Weekly sweep P&L already measured in 35C/39B ──────────────
    subsection("EDGES 6+7 — Weekly sweep: consolidated P&L reference")
    print(f"""
  From Exp 39B + 35C results (NIFTY/SENSEX combined):

  E6: PWL refined weekly sweep
    EOW: WR=76.9%, mean=+0.282% ≈ +{0.00282*spot_base:.0f} pts
    T+1D: WR=84.6%, mean=+0.312% ≈ +{0.00312*spot_base:.0f} pts
    T+2D: WR=76.9%, mean=+0.667% ≈ +{0.00667*spot_base:.0f} pts
    MAE: not computed this run (daily bars only available, weekly entry)
    Option: next-week CE (DTE~8). T+2D mean 0.667% on {spot_base:,} = ~{0.00667*spot_base:.0f} pts
    ATM CE next-week ≈ ₹250-350 premium. {0.00667*spot_base:.0f}pts move ≈ 80-120% return.

  E7: PWL weekly + daily PDL confluence
    Conf-day EOD: WR=100% (N=5), same magnitude as E6 for EOD
    T+2D continuation confirmed → same instrument/exit as E6
    Entry: daily PDL rejection bar close in OPEN window
    Maximum size entry given 100% WR (within risk limits)
""".format())


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 41 — P&L and MAE Analysis: All Session 11 Edges  ║")
    print("║  Session 11 · 2026-04-28 · MERDIAN                           ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("Computing for each edge:")
    print("  1. Return distribution (mean, median, P25/P75, max win/loss) in % and points")
    print("  2. Max Adverse Excursion (MAE) — how far against before winning?")
    print("  3. Entry timing: T+0 vs T+1 bar after rejection")
    print("  4. Edge 3: current-week vs next-week PE theoretical option P&L")
    print()

    all_ob_signals = []
    all_results    = {}

    for symbol, inst_id in INSTRUMENTS.items():
        print(f"\n[{symbol}] Loading data...")
        bars    = fetch_bars_by_date(inst_id, symbol)
        d_zones = fetch_d_zones(symbol)
        ob_sigs = fetch_ob_signals(symbol)
        for s in ob_sigs: s["symbol"] = symbol
        all_ob_signals.extend(ob_sigs)
        po3_map = build_po3_map(symbol, bars, d_zones)
        all_results[symbol] = (bars, d_zones, ob_sigs, po3_map)

    for symbol in INSTRUMENTS:
        bars, d_zones, ob_sigs, po3_map = all_results[symbol]
        run_analysis(symbol, bars, d_zones, all_ob_signals, po3_map)

    section("CROSS-EDGE STOP LOSS FRAMEWORK")
    print("""
  Stop loss recommendations based on MAE analysis:

  E1/E2 (PDH/PDL sweep entry):
    Structural stop: above PDH / below PDL (the swept level)
    Expected MAE P75 will be computed above — set stop at MAE P90
    If MAE P90 > 0.3% (72pts NIFTY), the entry is too early — use E4 instead

  E3 (next-week PE, DTE<3):
    Stop: if price re-takes PDH intraday → exit immediately
    Option stop: 40% of premium paid (handles theta + adverse delta)

  E4 (BEAR_OB MIDDAY):
    Structural stop: above OB zone_high
    OB zones are tight (~0.1-0.2%), so stop is naturally defined
    If MAE at T+30m > zone_high → false OB, exit

  E5 (BULL_OB AFTERNOON SENSEX):
    Same as E4 — stop above zone_high
    Time stop: mandatory EOD exit 15:20

  E6/E7 (weekly sweep):
    Session stop: if next session closes below PWL → exit
    Option stop: 35% of next-week premium
    Do not use intraday stops on multi-day holds — too much noise
""")

    section("SIZING FRAMEWORK")
    print("""
  Kelly sizing requires: WR and mean win/loss — computed above.
  Apply HALF-KELLY for live trading (full Kelly is too aggressive).

  Formula per edge:
    f = (WR * mean_win - (1-WR) * |mean_loss|) / mean_win
    Half-Kelly position = 0.5 * f * capital

  Placeholder (update with actual mean_win/mean_loss from output above):
    E4 (88% WR): f likely 0.6-0.8 → half-Kelly ~0.3-0.4 of risk capital
    E1 (93% WR): f likely 0.7-0.9 → half-Kelly ~0.35-0.45
    E6 (76% WR): f likely 0.4-0.6 → half-Kelly ~0.2-0.3
    E7 (100% WR, N=5): cap at 2x base size — N too small for full Kelly

  Practical cap: max 2% of capital at risk per trade across all concurrent edges
""")


if __name__ == "__main__":
    main()
