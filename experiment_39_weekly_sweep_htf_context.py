#!/usr/bin/env python3
"""
experiment_39_weekly_sweep_htf_context.py
MERDIAN Experiment 39 — Weekly Sweep as HTF Context + Daily Sweep Confirmation

Concept:
    Two-tier ICT liquidity hierarchy:
      Tier 1 (Weekly): PWH/PWL are strongest liquidity pools.
                       A week's worth of stop orders cluster above PWH and
                       below PWL. When price sweeps these, it's a larger
                       institutional move than a single day's stop run.
      Tier 2 (Daily):  PDH/PDL sweep within the weekly bias = confluent setup.
                       The weekly sweep sets the macro move direction.
                       The daily sweep within that week = entry timing.

    Prediction:
      Week where PWH is swept + same week PDH swept on a daily basis
      → highest conviction bearish session in that week.
      Week where PWL is swept + PDL swept daily → bullish.

    Also tests: weekly sweep alone as a multi-day predictor.

Data:
    hist_ict_htf_zones (timeframe='W') — check for PWH/PWL patterns
    hist_spot_bars_5m — to detect intra-week sweeps if W zones differ from D

    NOTE: If timeframe='W' only has BULL_OB/BEAR_OB/FVG (not PWH/PWL directly),
    the script falls back to computing PWH/PWL from weekly bar aggregates.

    Also uses: hist_ict_htf_zones (timeframe='D') for daily sweep detection.

Pass criteria:
    - Weekly sweep alone: N>=10, weekly WR (5-session net) >= 65%
    - Weekly + daily confluence: N>=8, same-session EOD WR >= 75%

TD-029 / pagination: fixes baked in.

Run from: C:\\GammaEnginePython
Usage  : python experiment_39_weekly_sweep_htf_context.py
Session: 11  (2026-04-28)
"""

import os
import sys
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

SWEEP_THRESHOLD    = 0.0005
REVERSAL_THRESHOLD = 0.001
REVERSAL_MAX_BARS  = 6

PASS_N_WEEKLY  = 10
PASS_WR_WEEKLY = 0.65
PASS_N_CONF    = 8
PASS_WR_CONF   = 0.75


def parse_ts(ts_str):
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    return dt.replace(tzinfo=None)

def bar_minutes(dt): return dt.hour*60 + dt.minute
def pct(v): return f"{v:.1%}"
def mean(lst): return sum(lst)/len(lst) if lst else None
def week_key(date_str):
    """Return ISO week string YYYY-WNN for grouping."""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


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
        dt = parse_ts(bar["bar_ts"]); t = bar_minutes(dt)
        if 9*60+15 <= t <= 15*60+30:
            bar["_dt"] = dt; bar["_date"] = dt.date().isoformat()
            by_date[bar["_date"]].append(bar)
    for d in by_date: by_date[d].sort(key=lambda b: b["_dt"])
    print(f" {len(by_date)} sessions")
    return dict(by_date)


def fetch_weekly_zones(symbol):
    """
    Fetch timeframe='W' zones from hist_ict_htf_zones.
    Returns dict keyed by as_of_date with all weekly zone rows.
    Also reports what pattern_types are available.
    """
    print(f"  [{symbol}] Fetching W zones...", end="", flush=True)
    resp = (supabase.table("hist_ict_htf_zones")
            .select("as_of_date,pattern_type,zone_high,zone_low,status")
            .eq("symbol", symbol)
            .eq("timeframe", "W")
            .execute())
    rows = resp.data or []
    print(f" {len(rows)} W zones")
    if rows:
        types = set(r["pattern_type"] for r in rows)
        print(f"  [{symbol}] W zone types: {types}")
    return rows


def fetch_daily_zones(symbol):
    print(f"  [{symbol}] Fetching D PDH/PDL zones...", end="", flush=True)
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


# ── Compute PWH/PWL from weekly bar aggregates ────────────────────────────────
def build_weekly_levels(bars_by_date):
    """
    Aggregate 5m bars into weekly sessions.
    Returns {week_key: {PWH: float, PWL: float, open: float, close: float,
                        days: [date_str], open_date: str}}
    where PWH = prior week's high, PWL = prior week's low.
    """
    week_bars = defaultdict(list)
    week_dates = defaultdict(list)
    for d, bars in sorted(bars_by_date.items()):
        wk = week_key(d)
        week_bars[wk].extend(bars)
        week_dates[wk].append(d)

    weekly = {}
    sorted_weeks = sorted(week_bars.keys())
    for i, wk in enumerate(sorted_weeks):
        bars = sorted(week_bars[wk], key=lambda b: b["_dt"])
        wk_high  = max(float(b["high"])  for b in bars)
        wk_low   = min(float(b["low"])   for b in bars)
        wk_open  = float(bars[0]["open"])
        wk_close = float(bars[-1]["close"])
        wk_days  = sorted(week_dates[wk])

        weekly[wk] = {
            "high": wk_high, "low": wk_low,
            "open": wk_open, "close": wk_close,
            "days": wk_days,
        }

    # Shift: PWH/PWL for week N = high/low of week N-1
    result = {}
    for i, wk in enumerate(sorted_weeks):
        if i == 0: continue
        prev_wk   = sorted_weeks[i-1]
        result[wk] = {
            "PWH":        weekly[prev_wk]["high"],
            "PWL":        weekly[prev_wk]["low"],
            "week_open":  weekly[wk]["open"],
            "week_close": weekly[wk]["close"],
            "days":       weekly[wk]["days"],
            "prev_week":  prev_wk,
        }
    return result


# ── Detect weekly sweep events ────────────────────────────────────────────────
def detect_weekly_sweeps(symbol, bars_by_date, weekly_levels):
    """
    For each week, detect if price sweeps PWH or PWL within the week
    and closes back inside by EOW (end of week).
    """
    events = []
    sorted_dates = sorted(bars_by_date.keys())

    # Build EOD close lookup
    eod_close = {d: float(bars_by_date[d][-1]["close"]) for d in sorted_dates if bars_by_date[d]}
    # Multi-day returns
    def nd_ret(from_date, direction, n_days=1):
        idx = sorted_dates.index(from_date) if from_date in sorted_dates else -1
        if idx < 0 or idx + n_days >= len(sorted_dates): return None
        tgt = sorted_dates[idx + n_days]
        base = eod_close.get(from_date); tgt_val = eod_close.get(tgt)
        if not base or not tgt_val: return None
        ret = (tgt_val - base) / base
        return ret * (1 if direction == "BULLISH" else -1)

    for wk, wl in sorted(weekly_levels.items()):
        pwh = wl["PWH"]; pwl = wl["PWL"]
        week_days = wl["days"]
        week_open = wl["week_open"]
        week_close = wl["week_close"]
        week_ret   = (week_close - week_open) / week_open

        # Check each day's bars for sweep
        pwh_swept = pwl_swept = False
        pwh_sweep_day = pwl_sweep_day = None
        pwh_depth = pwl_depth = 0.0

        for d in week_days:
            day_bars = bars_by_date.get(d, [])
            if not day_bars: continue
            day_high = max(float(b["high"]) for b in day_bars)
            day_low  = min(float(b["low"])  for b in day_bars)
            day_close = float(day_bars[-1]["close"])

            if not pwh_swept and day_high >= pwh*(1+SWEEP_THRESHOLD):
                # Confirm: close back below PWH that day or within next 2 days
                if day_close <= pwh*(1+0.001):
                    pwh_swept = True
                    pwh_sweep_day = d
                    pwh_depth = (day_high - pwh) / pwh * 100

            if not pwl_swept and day_low <= pwl*(1-SWEEP_THRESHOLD):
                if day_close >= pwl*(1-0.001):
                    pwl_swept = True
                    pwl_sweep_day = d
                    pwl_depth = (pwl - day_low) / pwl * 100

        if pwh_swept and pwh_sweep_day:
            # Weekly EOW outcome: does week close bearish from open?
            eow_win = week_ret < 0
            # Multi-day from sweep day
            t1d = nd_ret(pwh_sweep_day, "BEARISH", 1)
            t2d = nd_ret(pwh_sweep_day, "BEARISH", 2)
            t3d = nd_ret(pwh_sweep_day, "BEARISH", 3)
            events.append({
                "symbol": symbol, "week": wk,
                "sweep_day": pwh_sweep_day,
                "type": "PWH", "direction": "BEARISH",
                "pwh": pwh, "pwl": pwl,
                "sweep_depth": pwh_depth,
                "week_open": week_open, "week_close": week_close,
                "week_ret": week_ret, "eow_win": eow_win,
                "ret_t1d": t1d, "ret_t2d": t2d, "ret_t3d": t3d,
                "win_t1d": t1d is not None and t1d > 0,
                "win_t2d": t2d is not None and t2d > 0,
                "win_t3d": t3d is not None and t3d > 0,
                "n_days_remaining": len([d for d in week_days if d > pwh_sweep_day]),
            })

        if pwl_swept and pwl_sweep_day:
            eow_win = week_ret > 0
            t1d = nd_ret(pwl_sweep_day, "BULLISH", 1)
            t2d = nd_ret(pwl_sweep_day, "BULLISH", 2)
            t3d = nd_ret(pwl_sweep_day, "BULLISH", 3)
            events.append({
                "symbol": symbol, "week": wk,
                "sweep_day": pwl_sweep_day,
                "type": "PWL", "direction": "BULLISH",
                "pwh": pwh, "pwl": pwl,
                "sweep_depth": pwl_depth,
                "week_open": week_open, "week_close": week_close,
                "week_ret": week_ret, "eow_win": eow_win,
                "ret_t1d": t1d, "ret_t2d": t2d, "ret_t3d": t3d,
                "win_t1d": t1d is not None and t1d > 0,
                "win_t2d": t2d is not None and t2d > 0,
                "win_t3d": t3d is not None and t3d > 0,
                "n_days_remaining": len([d for d in week_days if d > pwl_sweep_day]),
            })

    return events


# ── Confluence: weekly sweep week + daily sweep ───────────────────────────────
def find_confluent_days(weekly_events, daily_d_zones, bars_by_date):
    """
    For each weekly sweep event, look for a daily PDH/PDL sweep on the
    same day or subsequent days in the same week (in the same direction).
    Returns enriched events with confluence flag.
    """
    sorted_dates = sorted(bars_by_date.keys())

    def has_daily_sweep(date_str, level, direction, day_bars):
        if not day_bars: return False, 0
        for i, bar in enumerate(day_bars):
            high = float(bar["high"]); low = float(bar["low"])
            n = len(day_bars)
            if direction == "BEARISH" and high >= level*(1+SWEEP_THRESHOLD):
                for j in range(i+1, min(i+REVERSAL_MAX_BARS+1, n)):
                    if float(day_bars[j]["close"]) <= level*(1-REVERSAL_THRESHOLD):
                        return True, (high-level)/level*100
            elif direction == "BULLISH" and low <= level*(1-SWEEP_THRESHOLD):
                for j in range(i+1, min(i+REVERSAL_MAX_BARS+1, n)):
                    if float(day_bars[j]["close"]) >= level*(1+REVERSAL_THRESHOLD):
                        return True, (level-low)/level*100
        return False, 0

    confluent = []
    for ev in weekly_events:
        sym  = ev["symbol"]
        direction = ev["direction"]
        # Check for daily sweep on sweep_day and next 2 days in week
        wk_days_after = [d for d in sorted_dates
                         if d >= ev["sweep_day"]
                         and d <= ev.get("sweep_day","")]

        # Simpler: check each day in the week after the weekly sweep day
        week_all_days = sorted(bars_by_date.keys())
        days_to_check = [d for d in week_all_days
                         if d >= ev["sweep_day"]][:3]

        daily_conf_found = False
        conf_day = None
        for d in days_to_check:
            dz = daily_d_zones.get(d, {})
            level = dz.get("PDH") if direction == "BEARISH" else dz.get("PDL")
            if level is None: continue
            day_bars = bars_by_date.get(d, [])
            found, depth = has_daily_sweep(d, level, direction, day_bars)
            if found:
                daily_conf_found = True
                conf_day = d
                ev_copy = dict(ev)
                ev_copy["daily_conf"] = True
                ev_copy["conf_day"]   = conf_day
                ev_copy["daily_sweep_depth"] = depth
                # EOD return on the confluence day itself
                if day_bars:
                    d_open  = float(day_bars[0]["open"])
                    d_close = float(day_bars[-1]["close"])
                    d_ret   = (d_close - d_open) / d_open
                    ev_copy["conf_day_ret"] = d_ret
                    ev_copy["conf_day_win"] = d_ret < 0 if direction == "BEARISH" else d_ret > 0
                confluent.append(ev_copy)
                break

        if not daily_conf_found:
            ev_copy = dict(ev)
            ev_copy["daily_conf"] = False
            ev_copy["conf_day"]   = None
            ev_copy["conf_day_win"] = None
            confluent.append(ev_copy)

    return confluent


# ── Reporting ─────────────────────────────────────────────────────────────────
def section(label):
    print(f"\n{'─'*65}\n  {label}\n{'─'*65}")

def wr_line(events, win_key, label, n_min=4):
    valid = [e for e in events if e.get(win_key) is not None]
    if len(valid) < n_min:
        print(f"  {label:<55}  N={len(valid):>3}  (insufficient)")
        return None
    wr = sum(1 for e in valid if e[win_key]) / len(valid)
    rets_key = win_key.replace("win_","ret_") if "t" in win_key else "week_ret"
    rets = [e[rets_key] for e in valid if e.get(rets_key) is not None]
    avg = mean(rets)
    print(f"  {label:<55}  N={len(valid):>3}  WR={pct(wr)}  mean={avg:.3%}" if avg else
          f"  {label:<55}  N={len(valid):>3}  WR={pct(wr)}")
    return wr


def print_results(all_events, w_zone_info):
    pwh = [e for e in all_events if e["type"] == "PWH"]
    pwl = [e for e in all_events if e["type"] == "PWL"]

    section("WEEKLY ZONE INFO")
    for sym, info in w_zone_info.items():
        print(f"  {sym}: {info}")

    section("WEEKLY SWEEP — STANDALONE (EOW outcome)")
    print()
    wr_line(pwh, "eow_win", "PWH sweep → bearish EOW")
    wr_line(pwl, "eow_win", "PWL sweep → bullish EOW")

    section("WEEKLY SWEEP — MULTI-DAY CONTINUATION FROM SWEEP DAY")
    print()
    for ev_list, label in [(pwh, "PWH"), (pwl, "PWL")]:
        print(f"  {label}:")
        for wk, rk in [("win_t1d","ret_t1d"),("win_t2d","ret_t2d"),("win_t3d","ret_t3d")]:
            wr_line(ev_list, wk, f"  {label} {wk.replace('win_','')}", n_min=3)

    section("WEEKLY SWEEP — BY SYMBOL")
    for sym in ["NIFTY","SENSEX"]:
        wr_line([e for e in pwh if e["symbol"]==sym], "eow_win", f"PWH {sym} EOW")
        wr_line([e for e in pwl if e["symbol"]==sym], "eow_win", f"PWL {sym} EOW")

    section("WEEKLY SWEEP — SWEEP DEPTH × EOW WR")
    for lo, hi, lbl in [(0.05,0.15,"shallow 0.05-0.15%"),(0.15,99,"deep >0.15%")]:
        sub_p = [e for e in pwh if lo <= e["sweep_depth"] < hi]
        sub_l = [e for e in pwl if lo <= e["sweep_depth"] < hi]
        if sub_p: wr_line(sub_p, "eow_win", f"PWH {lbl}", n_min=3)
        if sub_l: wr_line(sub_l, "eow_win", f"PWL {lbl}", n_min=3)

    section("CONFLUENCE — WEEKLY SWEEP + DAILY SWEEP IN SAME DIRECTION")
    conf_pwh = [e for e in pwh if e.get("daily_conf")]
    conf_pwl = [e for e in pwl if e.get("daily_conf")]
    no_conf_pwh = [e for e in pwh if not e.get("daily_conf")]
    no_conf_pwl = [e for e in pwl if not e.get("daily_conf")]

    print(f"\n  PWH events with daily confluence: {len(conf_pwh)} / {len(pwh)}")
    print(f"  PWL events with daily confluence: {len(conf_pwl)} / {len(pwl)}")
    print()
    wr_line(conf_pwh,    "conf_day_win", "PWH + daily PDH sweep (confluence day EOD)")
    wr_line(conf_pwh,    "eow_win",      "PWH + daily confluence → EOW")
    wr_line(no_conf_pwh, "eow_win",      "PWH no daily confluence → EOW")
    print()
    wr_line(conf_pwl,    "conf_day_win", "PWL + daily PDL sweep (confluence day EOD)")
    wr_line(conf_pwl,    "eow_win",      "PWL + daily confluence → EOW")
    wr_line(no_conf_pwl, "eow_win",      "PWL no daily confluence → EOW")

    section("ALL WEEKLY SWEEP EVENTS (for manual review)")
    print(f"\n  PWH sweeps ({len(pwh)}):")
    for e in sorted(pwh, key=lambda x: x["sweep_day"]):
        conf = "CONF" if e.get("daily_conf") else "    "
        print(f"    {e['sweep_day']}  {e['symbol']:<8}  "
              f"depth={e['sweep_depth']:.2f}%  "
              f"EOW={'WIN' if e['eow_win'] else 'LOSE'}  "
              f"week_ret={e['week_ret']:.2%}  {conf}")
    print(f"\n  PWL sweeps ({len(pwl)}):")
    for e in sorted(pwl, key=lambda x: x["sweep_day"]):
        conf = "CONF" if e.get("daily_conf") else "    "
        print(f"    {e['sweep_day']}  {e['symbol']:<8}  "
              f"depth={e['sweep_depth']:.2f}%  "
              f"EOW={'WIN' if e['eow_win'] else 'LOSE'}  "
              f"week_ret={e['week_ret']:.2%}  {conf}")

    section("PASS / FAIL")
    def assess(events, label, pass_wr, n_req, key="eow_win"):
        valid = [e for e in events if e.get(key) is not None]
        if not valid: print(f"  {label}: INSUFFICIENT DATA"); return False
        wr = sum(1 for e in valid if e[key]) / len(valid)
        ok = len(valid) >= n_req and wr >= pass_wr
        print(f"  {label}: {'✅ PASS' if ok else '❌ FAIL'}  N={len(valid)}  WR={pct(wr)}")
        return ok

    p1 = assess(pwh, "PWH weekly sweep → bearish EOW", PASS_WR_WEEKLY, PASS_N_WEEKLY)
    p2 = assess(pwl, "PWL weekly sweep → bullish EOW", PASS_WR_WEEKLY, PASS_N_WEEKLY)
    p3 = assess(conf_pwh, "PWH+daily confluence → conf day EOD", PASS_WR_CONF, PASS_N_CONF, "conf_day_win")
    p4 = assess(conf_pwl, "PWL+daily confluence → conf day EOD", PASS_WR_CONF, PASS_N_CONF, "conf_day_win")
    print()
    if p1 or p2: print("  Weekly sweep standalone: EDGE EXISTS — multi-day/swing trade candidate")
    if p3 or p4: print("  Weekly+daily confluence: HIGHEST CONVICTION daily entry signal")
    if not any([p1,p2,p3,p4]): print("  No weekly sweep edge found at current thresholds")
    print()


def main():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  EXPERIMENT 39 — Weekly Sweep HTF Context + Daily Confluence ║")
    print("║  Session 11 · 2026-04-28 · MERDIAN                          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("Hierarchy: PWH/PWL sweep (weekly) → PDH/PDL sweep (daily) = confluence")
    print("Weekly sweep computed from prior week's high/low via 5m bar aggregation")
    print()

    all_events  = []
    w_zone_info = {}

    for symbol, inst_id in INSTRUMENTS.items():
        print(f"\n[{symbol}]")
        bars        = fetch_bars_by_date(inst_id, symbol)
        w_zones_raw = fetch_weekly_zones(symbol)
        d_zones     = fetch_daily_zones(symbol)

        w_zone_info[symbol] = (f"{len(w_zones_raw)} W zones in hist_ict_htf_zones "
                               f"(types: {set(r['pattern_type'] for r in w_zones_raw) or 'none'})")

        print(f"  [{symbol}] Building weekly levels from bar data...", end="", flush=True)
        weekly_levels = build_weekly_levels(bars)
        print(f" {len(weekly_levels)} weeks")

        events = detect_weekly_sweeps(symbol, bars, weekly_levels)
        events = find_confluent_days(events, d_zones, bars)

        pwh_n = sum(1 for e in events if e["type"]=="PWH")
        pwl_n = sum(1 for e in events if e["type"]=="PWL")
        conf_n = sum(1 for e in events if e.get("daily_conf"))
        print(f"  Events: PWH={pwh_n}  PWL={pwl_n}  with_daily_confluence={conf_n}")
        all_events.extend(events)

    if not all_events: print("NO WEEKLY SWEEP EVENTS DETECTED."); sys.exit(1)
    print_results(all_events, w_zone_info)

if __name__ == "__main__":
    main()
