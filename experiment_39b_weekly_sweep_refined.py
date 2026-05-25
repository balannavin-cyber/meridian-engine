#!/usr/bin/env python3
"""
experiment_39b_weekly_sweep_refined.py
MERDIAN Experiment 39B — Weekly Sweep Refined: Genuine Reversal Detection

Origin:
    Exp 39 FAIL analysis identified three problems with the detection:
    1. Reversal too loose — close just needs to be "not above PWH".
       Trending markets pass this trivially. PWL EOW WR = 35.3% (worse than random).
    2. No gap context — daily sweep insight (gap-aligned = institutional fake)
       should apply weekly: gap-up open + PWH sweep = institutional manipulation.
       Gap-down + PWH sweep = real breakout attempt, not fake.
    3. No day-of-week filter — ICT specifically says Monday sets the weekly
       manipulation leg. Tuesday+ sweeps may just be trend continuation.

Refined detection:
    Genuine PWH sweep requires ALL of:
      a) Wick penetrates PWH by >= 0.05%  (same as before)
      b) Close returns BELOW PWH by >= 0.15% of prior week range
         (not just below the touch — must show conviction in rejection)
         Filter: close <= PWH - (PWH - PWL) * 0.15
      c) Gap-up context: today's open >= PWH * 0.999
         (open near or above PWH = institutions gapped above stops, then reversed)
      d) [Optional] Monday-only sweep: test with and without Monday filter

    Genuine PWL sweep requires ALL of:
      a) Wick penetrates PWL by >= 0.05%
      b) Close returns ABOVE PWL by >= 0.15% of prior week range
      c) Gap-down context: today's open <= PWL * 1.001
      d) [Optional] Monday-only

Pass criteria:
    - Refined weekly sweep standalone: N>=8, EOW WR>=65%
    - Monday-only subset: N>=5, EOW WR>=70%
    - With daily confluence: N>=5, conf day EOD WR>=72%

Run from: C:\\GammaEnginePython
Usage  : python experiment_39b_weekly_sweep_refined.py
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
    print("ERROR"); sys.exit(1)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

SWEEP_THRESHOLD     = 0.0005
DAILY_REVERSAL_BARS = 6
DAILY_REV_THRESHOLD = 0.001
# Genuine reversal filter: close must retreat >= this fraction of prior week range
RANGE_REVERSAL_FRAC = 0.15

PASS_N_STANDALONE = 8
PASS_WR_STANDALONE = 0.65
PASS_N_MONDAY = 5
PASS_WR_MONDAY = 0.70
PASS_N_CONF = 5
PASS_WR_CONF = 0.72


def parse_ts(ts_str):
    return datetime.fromisoformat(ts_str.replace("Z","+00:00")).replace(tzinfo=None)
def bar_minutes(dt): return dt.hour*60+dt.minute
def pct(v): return f"{v:.1%}"
def mean(lst): return sum(lst)/len(lst) if lst else None

def week_key(date_str):
    d=datetime.strptime(date_str,"%Y-%m-%d"); iso=d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"

def is_monday(date_str):
    return datetime.strptime(date_str,"%Y-%m-%d").weekday() == 0


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


def fetch_daily_zones(symbol):
    resp=(supabase.table("hist_ict_htf_zones").select("as_of_date,pattern_type,zone_high,zone_low")
          .eq("symbol",symbol).eq("timeframe","D").in_("pattern_type",["PDH","PDL"]).execute())
    zones=defaultdict(dict)
    for row in (resp.data or []):
        d=row["as_of_date"][:10]; pt=row["pattern_type"]
        if pt=="PDH": zones[d]["PDH"]=float(row["zone_high"])
        else: zones[d]["PDL"]=float(row.get("zone_low") or row["zone_high"])
    return dict(zones)


def build_weekly_levels(bars_by_date):
    week_bars=defaultdict(list); week_dates=defaultdict(list)
    for d, bars in sorted(bars_by_date.items()):
        wk=week_key(d); week_bars[wk].extend(bars); week_dates[wk].append(d)
    weekly={}
    sorted_weeks=sorted(week_bars.keys())
    for wk in sorted_weeks:
        bars=sorted(week_bars[wk],key=lambda b:b["_dt"])
        weekly[wk]={
            "high": max(float(b["high"]) for b in bars),
            "low":  min(float(b["low"])  for b in bars),
            "open": float(bars[0]["open"]),
            "close":float(bars[-1]["close"]),
            "days": sorted(week_dates[wk]),
        }
    result={}
    for i,wk in enumerate(sorted_weeks):
        if i==0: continue
        prev=sorted_weeks[i-1]
        result[wk]={
            "PWH": weekly[prev]["high"], "PWL": weekly[prev]["low"],
            "prior_range": weekly[prev]["high"]-weekly[prev]["low"],
            "week_open": weekly[wk]["open"], "week_close": weekly[wk]["close"],
            "days": weekly[wk]["days"], "prev_week": prev,
        }
    return result


def detect_refined_sweeps(symbol, bars_by_date, weekly_levels):
    sorted_dates = sorted(bars_by_date.keys())
    eod_close = {d: float(bars_by_date[d][-1]["close"]) for d in sorted_dates if bars_by_date[d]}

    def nd_ret(from_date, direction, n):
        idx = sorted_dates.index(from_date) if from_date in sorted_dates else -1
        if idx<0 or idx+n>=len(sorted_dates): return None
        base=eod_close.get(from_date); tgt=eod_close.get(sorted_dates[idx+n])
        if not base or not tgt: return None
        ret=(tgt-base)/base
        return ret*(1 if direction=="BULLISH" else -1)

    # Build prior close for gap computation
    prior_close={}
    for i,d in enumerate(sorted_dates):
        if i>0:
            prev=bars_by_date.get(sorted_dates[i-1],[])
            if prev: prior_close[d]=float(prev[-1]["close"])

    events=[]
    for wk, wl in sorted(weekly_levels.items()):
        pwh=wl["PWH"]; pwl=wl["PWL"]
        prior_range=wl["prior_range"]
        week_days=wl["days"]
        week_open=wl["week_open"]; week_close=wl["week_close"]
        week_ret=(week_close-week_open)/week_open

        reversal_min_pwh = prior_range * RANGE_REVERSAL_FRAC  # must close below by this much
        reversal_min_pwl = prior_range * RANGE_REVERSAL_FRAC

        pwh_found=pwl_found=False

        for d in week_days:
            day_bars=bars_by_date.get(d,[])
            if not day_bars: continue
            day_open  = float(day_bars[0]["open"])
            day_high  = max(float(b["high"]) for b in day_bars)
            day_low   = min(float(b["low"])  for b in day_bars)
            day_close = float(day_bars[-1]["close"])
            prev_cls  = prior_close.get(d)
            gap_pct   = (day_open-prev_cls)/prev_cls if prev_cls else None
            is_mon    = is_monday(d)

            # ── Refined PWH sweep ─────────────────────────────────────────────
            if not pwh_found and day_high >= pwh*(1+SWEEP_THRESHOLD):
                # Condition b: close retreats >= 15% of prior week range below PWH
                close_ok  = day_close <= pwh - reversal_min_pwh
                # Condition c: gap-up context
                gap_up_ok = day_open >= pwh*0.999
                # Both required
                if close_ok and gap_up_ok:
                    sweep_depth = (day_high-pwh)/pwh*100
                    eow_win = week_ret < 0
                    t1d = nd_ret(d,"BEARISH",1); t2d = nd_ret(d,"BEARISH",2)
                    events.append({
                        "symbol": symbol, "week": wk, "sweep_day": d,
                        "type": "PWH", "direction": "BEARISH",
                        "sweep_depth": sweep_depth,
                        "gap_pct": gap_pct,
                        "is_monday": is_mon,
                        "range_reversal_pts": pwh - day_close,
                        "range_reversal_frac": (pwh-day_close)/prior_range if prior_range else 0,
                        "week_ret": week_ret, "eow_win": eow_win,
                        "ret_t1d": t1d, "ret_t2d": t2d,
                        "win_t1d": t1d is not None and t1d > 0,
                        "win_t2d": t2d is not None and t2d > 0,
                        # Exp 39 loose version (for comparison)
                        "loose_pass": day_close <= pwh*1.001,
                    })
                    pwh_found=True

            # ── Refined PWL sweep ─────────────────────────────────────────────
            if not pwl_found and day_low <= pwl*(1-SWEEP_THRESHOLD):
                close_ok   = day_close >= pwl + reversal_min_pwl
                gap_down_ok = day_open <= pwl*1.001
                if close_ok and gap_down_ok:
                    sweep_depth = (pwl-day_low)/pwl*100
                    eow_win = week_ret > 0
                    t1d = nd_ret(d,"BULLISH",1); t2d = nd_ret(d,"BULLISH",2)
                    events.append({
                        "symbol": symbol, "week": wk, "sweep_day": d,
                        "type": "PWL", "direction": "BULLISH",
                        "sweep_depth": sweep_depth,
                        "gap_pct": gap_pct,
                        "is_monday": is_mon,
                        "range_reversal_pts": day_close - pwl,
                        "range_reversal_frac": (day_close-pwl)/prior_range if prior_range else 0,
                        "week_ret": week_ret, "eow_win": eow_win,
                        "ret_t1d": t1d, "ret_t2d": t2d,
                        "win_t1d": t1d is not None and t1d > 0,
                        "win_t2d": t2d is not None and t2d > 0,
                        "loose_pass": day_close >= pwl*0.999,
                    })
                    pwl_found=True

        # End of week_days loop
    return events


def find_daily_confluence(events, daily_zones, bars_by_date, sorted_dates):
    """Mark events where sweep day ALSO has a daily PDH/PDL sweep in same direction."""
    for ev in events:
        d         = ev["sweep_day"]
        direction = ev["direction"]
        dz        = daily_zones.get(d, {})
        level     = dz.get("PDH") if direction=="BEARISH" else dz.get("PDL")
        day_bars  = bars_by_date.get(d, [])
        conf      = False
        if level and day_bars:
            n = len(day_bars)
            for i, bar in enumerate(day_bars):
                high=float(bar["high"]); low=float(bar["low"])
                if direction=="BEARISH" and high>=level*(1+0.0005):
                    for j in range(i+1, min(i+DAILY_REVERSAL_BARS+1, n)):
                        if float(day_bars[j]["close"])<=level*(1-DAILY_REV_THRESHOLD):
                            conf=True; break
                elif direction=="BULLISH" and low<=level*(1-0.0005):
                    for j in range(i+1, min(i+DAILY_REVERSAL_BARS+1, n)):
                        if float(day_bars[j]["close"])>=level*(1+DAILY_REV_THRESHOLD):
                            conf=True; break
                if conf: break
        ev["daily_conf"] = conf
        if conf and day_bars:
            d_ret=(float(day_bars[-1]["close"])-float(day_bars[0]["open"]))/float(day_bars[0]["open"])
            ev["conf_day_win"] = d_ret<0 if direction=="BEARISH" else d_ret>0
        else:
            ev["conf_day_win"] = None
    return events


def section(label):
    print(f"\n{'─'*65}\n  {label}\n{'─'*65}")


def wr_row(evs, win_key, label, n_min=3):
    valid=[e for e in evs if e.get(win_key) is not None]
    if len(valid)<n_min:
        print(f"  {label:<58}  N={len(valid):>3}  (insufficient)")
        return None
    wr=sum(1 for e in valid if e[win_key])/len(valid)
    rets_key="week_ret" if win_key=="eow_win" else win_key.replace("win_","ret_")
    rets=[e[rets_key] for e in valid if e.get(rets_key) is not None]
    avg=mean(rets)
    print(f"  {label:<58}  N={len(valid):>3}  WR={pct(wr)}  mean={avg:.3%}" if avg else
          f"  {label:<58}  N={len(valid):>3}  WR={pct(wr)}")
    return wr


def print_results(all_events):
    pwh=[e for e in all_events if e["type"]=="PWH"]
    pwl=[e for e in all_events if e["type"]=="PWL"]

    section("FILTER IMPACT — Refined vs Loose (Exp 39 definition)")
    loose_pwh=sum(1 for e in all_events if e["type"]=="PWH" and e["loose_pass"])
    loose_pwl=sum(1 for e in all_events if e["type"]=="PWL" and e["loose_pass"])
    print(f"\n  Exp 39 (loose): PWH={loose_pwh}  PWL={loose_pwl}")
    print(f"  Exp 39B (refined): PWH={len(pwh)}  PWL={len(pwl)}")
    print(f"  Blocked by refinement: PWH={loose_pwh-len(pwh)}  PWL={loose_pwl-len(pwl)}")

    section("REFINED SWEEP — STANDALONE EOW WR")
    wr_row(pwh, "eow_win", "PWH refined → bearish EOW")
    wr_row(pwl, "eow_win", "PWL refined → bullish EOW")

    section("MONDAY-ONLY FILTER")
    pwh_mon=[e for e in pwh if e["is_monday"]]
    pwl_mon=[e for e in pwl if e["is_monday"]]
    pwh_non=[e for e in pwh if not e["is_monday"]]
    pwl_non=[e for e in pwl if not e["is_monday"]]
    wr_row(pwh_mon, "eow_win", "PWH sweep on MONDAY")
    wr_row(pwh_non, "eow_win", "PWH sweep NOT Monday")
    wr_row(pwl_mon, "eow_win", "PWL sweep on MONDAY")
    wr_row(pwl_non, "eow_win", "PWL sweep NOT Monday")

    section("BY SYMBOL")
    for sym in ["NIFTY","SENSEX"]:
        wr_row([e for e in pwh if e["symbol"]==sym], "eow_win", f"PWH refined {sym}")
        wr_row([e for e in pwl if e["symbol"]==sym], "eow_win", f"PWL refined {sym}")

    section("SWEEP DEPTH × EOW WR")
    for lo,hi,lbl in [(0.05,0.15,"shallow 0.05-0.15%"),(0.15,99,"deep >0.15%")]:
        wr_row([e for e in pwh if lo<=e["sweep_depth"]<hi], "eow_win", f"PWH {lbl}", n_min=3)
        wr_row([e for e in pwl if lo<=e["sweep_depth"]<hi], "eow_win", f"PWL {lbl}", n_min=3)

    section("MULTI-DAY CONTINUATION")
    for ev_list, label in [(pwh,"PWH"),(pwl,"PWL")]:
        wr_row(ev_list, "win_t1d", f"{label} T+1D continuation")
        wr_row(ev_list, "win_t2d", f"{label} T+2D continuation")

    section("DAILY CONFLUENCE")
    conf_pwh=[e for e in pwh if e.get("daily_conf")]
    conf_pwl=[e for e in pwl if e.get("daily_conf")]
    print(f"\n  PWH with daily PDH confluence: {len(conf_pwh)}/{len(pwh)}")
    print(f"  PWL with daily PDL confluence: {len(conf_pwl)}/{len(pwl)}")
    wr_row(conf_pwh, "conf_day_win", "PWH + daily PDH → conf day EOD", n_min=3)
    wr_row(conf_pwh, "eow_win",      "PWH + daily PDH → EOW")
    wr_row(conf_pwl, "conf_day_win", "PWL + daily PDL → conf day EOD", n_min=3)
    wr_row(conf_pwl, "eow_win",      "PWL + daily PDL → EOW")

    section("ALL REFINED EVENTS")
    print(f"\n  PWH ({len(pwh)}):")
    for e in sorted(pwh, key=lambda x: x["sweep_day"]):
        mon="MON" if e["is_monday"] else "   "
        conf="CONF" if e.get("daily_conf") else "    "
        print(f"    {e['sweep_day']}  {e['symbol']:<8}  {mon}  "
              f"depth={e['sweep_depth']:.2f}%  "
              f"rev_frac={e['range_reversal_frac']:.2f}  "
              f"EOW={'WIN' if e['eow_win'] else 'LOSE'}  "
              f"wk={e['week_ret']:.2%}  {conf}")
    print(f"\n  PWL ({len(pwl)}):")
    for e in sorted(pwl, key=lambda x: x["sweep_day"]):
        mon="MON" if e["is_monday"] else "   "
        conf="CONF" if e.get("daily_conf") else "    "
        print(f"    {e['sweep_day']}  {e['symbol']:<8}  {mon}  "
              f"depth={e['sweep_depth']:.2f}%  "
              f"rev_frac={e['range_reversal_frac']:.2f}  "
              f"EOW={'WIN' if e['eow_win'] else 'LOSE'}  "
              f"wk={e['week_ret']:.2%}  {conf}")

    section("PASS / FAIL")
    def assess(evs, label, pass_wr, n_req, key="eow_win"):
        valid=[e for e in evs if e.get(key) is not None]
        if not valid: print(f"  {label}: INSUFFICIENT DATA"); return False
        wr=sum(1 for e in valid if e[key])/len(valid)
        ok=len(valid)>=n_req and wr>=pass_wr
        print(f"  {label}: {'✅ PASS' if ok else '❌ FAIL'}  N={len(valid)}  WR={pct(wr)}")
        return ok

    p1=assess(pwh, "PWH refined standalone EOW", PASS_WR_STANDALONE, PASS_N_STANDALONE)
    p2=assess(pwl, "PWL refined standalone EOW", PASS_WR_STANDALONE, PASS_N_STANDALONE)
    p3=assess(pwh_mon, "PWH Monday-only EOW", PASS_WR_MONDAY, PASS_N_MONDAY)
    p4=assess(pwl_mon, "PWL Monday-only EOW", PASS_WR_MONDAY, PASS_N_MONDAY)
    p5=assess(conf_pwh, "PWH+daily confluence conf-day EOD", PASS_WR_CONF, PASS_N_CONF, "conf_day_win")
    p6=assess(conf_pwl, "PWL+daily confluence conf-day EOD", PASS_WR_CONF, PASS_N_CONF, "conf_day_win")
    print()
    results=[]
    if p1 or p2: results.append("Refined standalone weekly sweep has edge")
    if p3 or p4: results.append("Monday weekly sweep is the highest-conviction subset")
    if p5 or p6: results.append("Weekly + daily confluence is valid session entry signal")
    if results:
        for r in results: print(f"  ✅ {r}")
    else:
        print("  ❌ Weekly sweep edge not confirmed even with refinements")
        print("     Next step: require weekly sweep on W BULL_OB/BEAR_OB zone (not just PWH/PWL level)")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 39B — Weekly Sweep Refined                      ║")
    print("║  Session 11 · 2026-04-28 · MERDIAN                          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print(f"Refinements vs Exp 39:")
    print(f"  (a) Close must retreat >= {RANGE_REVERSAL_FRAC:.0%} of prior week range below PWH/PWL")
    print(f"  (b) Gap context required (gap-up for PWH / gap-down for PWL)")
    print(f"  (c) Monday-only subset tested separately")
    print()
    all_events=[]
    for symbol, inst_id in INSTRUMENTS.items():
        print(f"\n[{symbol}]")
        bars       = fetch_bars_by_date(inst_id, symbol)
        d_zones    = fetch_daily_zones(symbol)
        sorted_dates = sorted(bars.keys())
        weekly     = build_weekly_levels(bars)
        events     = detect_refined_sweeps(symbol, bars, weekly)
        events     = find_daily_confluence(events, d_zones, bars, sorted_dates)
        pwh_n=sum(1 for e in events if e["type"]=="PWH")
        pwl_n=sum(1 for e in events if e["type"]=="PWL")
        print(f"  Events: PWH={pwh_n}  PWL={pwl_n}")
        all_events.extend(events)
    if not all_events:
        print("\nNO REFINED SWEEP EVENTS. The filters may be too tight.")
        print("Consider reducing RANGE_REVERSAL_FRAC from 0.15 to 0.10")
        sys.exit(1)
    print_results(all_events)

if __name__ == "__main__":
    main()
