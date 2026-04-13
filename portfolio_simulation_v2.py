#!/usr/bin/env python3
"""
portfolio_simulation_v2.py
MERDIAN Portfolio Simulation v2 — Dynamic Exit + Wider Gap Tolerance

Changes from v1:
  1. MAX_GAP_MIN = 5 (was 3)
     Option bars can be 2-5 minutes apart in less liquid periods.
     5-minute tolerance recovers more trades without meaningful price error.

  2. DYNAMIC EXIT — cut losers at T+30m, ride winners to T+60m
     At T+30m:
       If P&L < 0  → exit immediately (don't let losers run)
       If P&L ≥ 0  → hold to T+60m (give winners more room)
     At T+60m:
       Exit always — hard intraday close

  3. HALF-EXIT on large gains at T+30m
     If gain > HALF_EXIT_THRESHOLD (50% of premium) at T+30m:
       Exit HALF the position at T+30m price
       Hold remaining HALF to T+60m
     This locks in gains while preserving upside on strong moves.
     Only applies to PYRAMID structure (meaningful lot counts).
     Fixed structure always fully exits (1 lot = no point splitting).

Starting capital: ₹2,00,000 per symbol (₹4,00,000 total)
Patterns: BULL_OB, BEAR_OB, BULL_FVG, JUDAS_BULL (60%+ win rate)
Lot sizes: NIFTY=25, SENSEX=15
Position limit: 20% of capital per trade (premium × lots)

Read-only. Runtime: ~20 minutes.

Usage:
    python portfolio_simulation_v2.py
"""

import os
import bisect
import time
from datetime import datetime, timedelta, date, time as dtime
from collections import defaultdict
from itertools import groupby
from merdian_utils import build_expiry_index_simple, nearest_expiry_db

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

PAGE_SIZE = 1_000
SESSION_END = dtime(15, 30)

# ── v2 parameters ─────────────────────────────────────────────────────
MAX_GAP_MIN          = 5      # wider bar search (was 3)
HALF_EXIT_THRESHOLD  = 50.0  # % gain at T+30m triggers half-exit

# ── Portfolio parameters ──────────────────────────────────────────────
STARTING_CAPITAL = 200_000
MAX_TRADE_PCT    = 0.20
RUIN_THRESHOLD   = 10_000
LOT_SIZE         = {"NIFTY": 25, "SENSEX": 15}

# ── Pattern config ────────────────────────────────────────────────────
OPT_TYPE = {
    "BULL_OB":    "CE",
    "BEAR_OB":    "PE",
    "BULL_FVG":   "CE",
    "JUDAS_BULL": "CE",
}
TARGET_PATTERNS = set(OPT_TYPE.keys())

# ── Pyramid config ────────────────────────────────────────────────────
T2_H, T3_H       = 5, 10
T2_THRESH        = 0.20
T3_THRESH        = 0.40
T1_LOTS, T2_LOTS, T3_LOTS = 1, 2, 3

# ── Detection parameters ──────────────────────────────────────────────
OB_MIN_MOVE_PCT  = 0.40
FVG_MIN_PCT      = 0.10
JUDAS_MIN_PCT    = 0.25
ATM_RADIUS       = 3
STRIKE_STEP      = {"NIFTY": 50, "SENSEX": 100}
MIN_OPTION_PRICE = 5.0

MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}


# ── Utilities ─────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def pct(a, b):
    return 100.0 * (b - a) / a if a else 0.0

def pct_dir(a, b, direction):
    return pct(a, b) * direction

def in_session(ts, h):
    return (ts + timedelta(minutes=h)).time() <= SESSION_END

def atm_strike(spot, symbol):
    s = STRIKE_STEP[symbol]
    return round(spot / s) * s

def month_key(td):
    return (td.year, td.month)

def month_label(mk):
    return f"{MONTH_NAMES[mk[1]]} {mk[0]}"


# ── Data loading ──────────────────────────────────────────────────────

def fetch_paginated(sb, table, filters, select, order="bar_ts"):
    all_rows, offset = [], 0
    while True:
        q = sb.table(table).select(select).order(order).range(offset, offset+PAGE_SIZE-1)
        for method, *args in filters:
            q = getattr(q, method)(*args)
        rows = None
        for attempt in range(4):
            try:
                rows = q.execute().data
                break
            except Exception:
                if attempt == 3: raise
                time.sleep(2**attempt)
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset % 20_000 == 0:
            log(f"    {offset:,} rows...")
    return all_rows


def sessions_from_bars(bars):
    result = {}
    for k, g in groupby(bars, key=lambda b: b["trade_date"]):
        result[k] = list(g)
    return result


def fetch_option_day(sb, inst_id, td, ed, strikes, opt_types):
    strike_strs = [f"{float(s):.2f}" for s in strikes]
    all_rows, offset = [], 0
    while True:
        rows = (
            sb.table("hist_option_bars_1m")
            .select("bar_ts, strike, option_type, close")
            .eq("instrument_id", str(inst_id))
            .eq("trade_date", str(td))
            .eq("expiry_date", str(ed))
            .in_("strike", strike_strs)
            .in_("option_type", list(opt_types))
            .order("bar_ts")
            .range(offset, offset+PAGE_SIZE-1)
            .execute().data
        )
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    lookup = {}
    for r in all_rows:
        ts  = datetime.fromisoformat(r["bar_ts"])
        stk = float(r["strike"])
        ot  = r["option_type"]
        cl  = float(r["close"])
        if cl >= MIN_OPTION_PRICE:
            lookup[(stk, ot, ts)] = cl
    return lookup


def get_option_price(lookup, strike, ot, target_ts, symbol,
                     max_gap=MAX_GAP_MIN):
    step = STRIKE_STEP[symbol]
    candidates = [strike + i*step for i in range(-ATM_RADIUS, ATM_RADIUS+1)]
    best_p, best_g, best_stk = None, timedelta(minutes=max_gap+1), None
    for stk in candidates:
        ts_list = sorted(ts for (s,o,ts) in lookup if s==stk and o==ot)
        if not ts_list: continue
        idx = bisect.bisect_left(ts_list, target_ts)
        for i in (idx-1, idx):
            if 0 <= i < len(ts_list):
                gap = abs(ts_list[i] - target_ts)
                if gap < best_g:
                    p = lookup.get((stk, ot, ts_list[i]))
                    if p:
                        best_g, best_p, best_stk = gap, p, stk
    return (best_p, best_stk) if best_g <= timedelta(minutes=max_gap) else (None, None)


def get_spot_at(bars, target_ts):
    tss = [b["bar_ts"] for b in bars]
    idx = bisect.bisect_left(tss, target_ts)
    best_p, best_g = None, timedelta(minutes=MAX_GAP_MIN+1)
    for i in (idx-1, idx):
        if 0 <= i < len(bars):
            gap = abs(bars[i]["bar_ts"] - target_ts)
            if gap < best_g:
                best_g, best_p = gap, bars[i]["close"]
    return best_p if best_g <= timedelta(minutes=MAX_GAP_MIN) else None


# ── Pattern detectors ─────────────────────────────────────────────────

def detect_obs(bars):
    out, seen, n = [], set(), len(bars)
    for i in range(n-6):
        mv = pct(bars[i]["close"], bars[min(i+5,n-1)]["close"])
        if mv <= -OB_MIN_MOVE_PCT:
            for j in range(i, max(i-6,-1), -1):
                if bars[j]["close"] > bars[j]["open"] and j not in seen:
                    seen.add(j)
                    out.append(dict(bar_idx=j,bar=bars[j],pattern="BEAR_OB"))
                    break
        elif mv >= OB_MIN_MOVE_PCT:
            for j in range(i, max(i-6,-1), -1):
                if bars[j]["close"] < bars[j]["open"] and j not in seen:
                    seen.add(j)
                    out.append(dict(bar_idx=j,bar=bars[j],pattern="BULL_OB"))
                    break
    return out


def detect_fvg(bars):
    out, min_g = [], FVG_MIN_PCT/100.0
    for i in range(1, len(bars)-1):
        p, c, n = bars[i-1], bars[i], bars[i+1]
        ref = c["close"]
        if p["high"] < n["low"] and (n["low"]-p["high"])/ref >= min_g:
            out.append(dict(bar_idx=i,bar=c,pattern="BULL_FVG"))
    return out


def detect_judas(bars):
    out = []
    if len(bars) < 46: return out
    mv = pct(bars[0]["open"], bars[14]["close"])
    if abs(mv) < JUDAS_MIN_PCT: return out
    rev = bars[15:45]
    if mv < 0:
        if pct(bars[14]["close"], max(b["high"] for b in rev)) >= abs(mv)*0.50:
            out.append(dict(bar_idx=14,bar=bars[14],pattern="JUDAS_BULL"))
    return out


# ── Dynamic exit logic ────────────────────────────────────────────────

def compute_pnl_v2(lookup, entry_p, entry_stk, ot, ts, direction,
                   lots_fixed, lots_pyr, symbol, lot_size):
    """
    v2 dynamic exit:
      FIXED:
        T+30m: exit if losing. Hold if winning.
        T+60m: always exit.

      PYRAMID:
        T+30m: exit if losing.
        T+30m: if gain > HALF_EXIT_THRESHOLD → exit half lots at T+30m.
        T+60m: exit remaining lots.

    Returns:
      pnl_fixed (₹), pnl_pyr (₹),
      exit_note (string describing exit type)
    """
    p30, _ = get_option_price(lookup, entry_stk, ot,
                               ts + timedelta(minutes=30), symbol)
    p60, _ = get_option_price(lookup, entry_stk, ot,
                               ts + timedelta(minutes=60), symbol)

    in30 = in_session(ts, 30)
    in60 = in_session(ts, 60)

    # ── FIXED (1 lot always) ──────────────────────────────────────────
    if p30 is not None and in30:
        gain30 = pct(entry_p, p30)
        if gain30 < 0:
            # Cut loser at T+30m
            pnl_fixed = (p30 - entry_p) * lots_fixed * lot_size
            exit_note_fixed = "cut@30m"
        else:
            # Winner — ride to T+60m
            if p60 is not None and in60:
                pnl_fixed = (p60 - entry_p) * lots_fixed * lot_size
                exit_note_fixed = "ride@60m"
            else:
                pnl_fixed = (p30 - entry_p) * lots_fixed * lot_size
                exit_note_fixed = "win@30m(no60)"
    elif p60 is not None and in60:
        pnl_fixed = (p60 - entry_p) * lots_fixed * lot_size
        exit_note_fixed = "@60m(no30)"
    else:
        return None, None, "no_data"

    # ── PYRAMID ───────────────────────────────────────────────────────
    if p30 is not None and in30:
        gain30 = pct(entry_p, p30)
        if gain30 < 0:
            # Cut all lots at T+30m
            pnl_pyr = (p30 - entry_p) * lots_pyr * lot_size
            exit_note_pyr = "cut@30m"
        elif gain30 >= HALF_EXIT_THRESHOLD:
            # Big winner — exit half at T+30m, hold half to T+60m
            half_lots = max(1, lots_pyr // 2)
            rest_lots = lots_pyr - half_lots
            pnl_half = (p30 - entry_p) * half_lots * lot_size
            if p60 is not None and in60 and rest_lots > 0:
                pnl_rest = (p60 - entry_p) * rest_lots * lot_size
                pnl_pyr = pnl_half + pnl_rest
                exit_note_pyr = f"half@30m+rest@60m({gain30:.0f}%)"
            else:
                pnl_pyr = (p30 - entry_p) * lots_pyr * lot_size
                exit_note_pyr = f"full@30m({gain30:.0f}%,no60)"
        else:
            # Modest winner — ride to T+60m
            if p60 is not None and in60:
                pnl_pyr = (p60 - entry_p) * lots_pyr * lot_size
                exit_note_pyr = "ride@60m"
            else:
                pnl_pyr = (p30 - entry_p) * lots_pyr * lot_size
                exit_note_pyr = "win@30m(no60)"
    elif p60 is not None and in60:
        pnl_pyr = (p60 - entry_p) * lots_pyr * lot_size
        exit_note_pyr = "@60m(no30)"
    else:
        pnl_pyr = pnl_fixed  # fallback

    exit_note = f"F:{exit_note_fixed} P:{exit_note_pyr}"
    return pnl_fixed, pnl_pyr, exit_note


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    all_trades = {"NIFTY": [], "SENSEX": []}

    for symbol in ["NIFTY", "SENSEX"]:
        expiry_idx = build_expiry_index_simple(sb, inst[symbol])
        log(f"\n── {symbol} ─────────────────────────────────────────────")
        lot_size = LOT_SIZE[symbol]

        log("  Loading spot bars...")
        raw = fetch_paginated(
            sb, "hist_spot_bars_1m",
            [("eq","instrument_id",inst[symbol]),("eq","is_pre_market",False)],
            "bar_ts, trade_date, open, high, low, close"
        )
        for r in raw:
            r["bar_ts"]     = datetime.fromisoformat(r["bar_ts"])
            r["trade_date"] = date.fromisoformat(r["trade_date"])
            for k in ("open","high","low","close"):
                r[k] = float(r[k])
        spot_sessions = sessions_from_bars(raw)
        all_spot      = raw
        dates = sorted(spot_sessions.keys())
        log(f"  {len(raw):,} bars | {len(dates)} sessions")

        log("  Detecting patterns...")
        all_patterns = []
        for d in dates:
            bars = spot_sessions[d]
            if len(bars) < 30: continue
            pats = detect_obs(bars) + detect_fvg(bars) + detect_judas(bars)
            for pat in pats:
                if pat["pattern"] not in TARGET_PATTERNS: continue
                bar = pat["bar"]
                all_patterns.append({
                    "pattern":   pat["pattern"],
                    "bar":       bar,
                    "td":        d,
                    "exp_date":  nearest_expiry_db(d, expiry_idx),
                    "atm":       atm_strike(bar["close"], symbol),
                    "opt_type":  OPT_TYPE[pat["pattern"]],
                    "direction": +1 if OPT_TYPE[pat["pattern"]] == "CE" else -1,
                })
        log(f"  {len(all_patterns)} qualifying patterns")

        day_groups = defaultdict(list)
        for pat in all_patterns:
            day_groups[(pat["td"], pat["exp_date"])].append(pat)

        log("  Fetching options and scoring...")
        trades = []

        for gi, ((td, ed), pats_today) in enumerate(sorted(day_groups.items())):
            step = STRIKE_STEP[symbol]
            strikes_needed   = set()
            opt_types_needed = set()
            for pat in pats_today:
                base = pat["atm"]
                for r in range(-ATM_RADIUS, ATM_RADIUS+1):
                    strikes_needed.add(base + r*step)
                opt_types_needed.add(pat["opt_type"])

            try:
                lookup = fetch_option_day(
                    sb, inst[symbol], td, ed,
                    sorted(strikes_needed), sorted(opt_types_needed)
                )
            except Exception:
                continue

            if gi % 30 == 0:
                log(f"    {gi}/{len(day_groups)} groups...")

            for pat in pats_today:
                ts        = pat["bar"]["bar_ts"]
                stk       = pat["atm"]
                ot        = pat["opt_type"]
                direction = pat["direction"]
                spot      = pat["bar"]["close"]

                entry_p, entry_stk = get_option_price(lookup, stk, ot, ts, symbol)
                if entry_p is None:
                    continue

                # Pyramid tier check
                lots_pyr = T1_LOTS
                p5  = get_spot_at(all_spot, ts + timedelta(minutes=T2_H))
                p10 = get_spot_at(all_spot, ts + timedelta(minutes=T3_H))
                t2 = t3 = False
                if p5  and pct_dir(spot, p5,  direction) >= T2_THRESH:
                    lots_pyr += T2_LOTS; t2 = True
                if t2 and p10 and pct_dir(spot, p10, direction) >= T3_THRESH:
                    lots_pyr += T3_LOTS; t3 = True

                pnl_f, pnl_p, exit_note = compute_pnl_v2(
                    lookup, entry_p, entry_stk or stk, ot, ts,
                    direction, T1_LOTS, lots_pyr, symbol, lot_size
                )
                if pnl_f is None:
                    continue

                trades.append({
                    "td": td, "ts": ts, "symbol": symbol,
                    "pattern": pat["pattern"], "ot": ot,
                    "entry_p": entry_p, "lots_pyr": lots_pyr,
                    "t2": t2, "t3": t3,
                    "pnl_fixed": pnl_f,
                    "pnl_pyr":   pnl_p,
                    "exit_note": exit_note,
                })

        all_trades[symbol] = sorted(trades, key=lambda t: t["ts"])
        log(f"  {len(trades)} trades for {symbol}")

    # ── Portfolio simulation ──────────────────────────────────────────
    print("\n" + "=" * 120)
    print("  MERDIAN PORTFOLIO SIMULATION v2 — Dynamic Exit + 5-min Bar Gap")
    print(f"  Starting: ₹{STARTING_CAPITAL:,.0f} per symbol | "
          f"Patterns: BULL_OB, BEAR_OB, BULL_FVG, JUDAS_BULL")
    print(f"  Exit: Cut losers @T+30m | Ride winners to T+60m | "
          f"Half-exit @T+30m if gain >{HALF_EXIT_THRESHOLD:.0f}%")
    print(f"  FIXED=1 lot | PYRAMID=1→3→6 lots | Position limit: "
          f"{MAX_TRADE_PCT*100:.0f}% of capital")
    print("=" * 120)

    for symbol in ["NIFTY", "SENSEX"]:
        expiry_idx = build_expiry_index_simple(sb, inst[symbol])
        trades   = all_trades[symbol]
        lot_size = LOT_SIZE[symbol]

        print(f"\n{'#'*120}")
        print(f"  {symbol}  |  Lot={lot_size}  |  {len(trades)} trades")
        print(f"{'#'*120}")

        cap_f = cap_p = STARTING_CAPITAL
        peak_f = peak_p = STARTING_CAPITAL
        max_dd_f = max_dd_p = 0.0
        wins_f = loss_f = wins_p = loss_p = 0
        monthly_f = defaultdict(float)
        monthly_p = defaultdict(float)
        monthly_n = defaultdict(int)
        best_f = worst_f = best_p_t = worst_p_t = None

        print(f"\n  {'Date':<12} {'Time':<6} {'Pat':<12} {'OT':<3} "
              f"{'Entry':>6} {'Lots':>5} "
              f"{'Fixed P&L':>11} {'Cap F':>11}  "
              f"{'Pyr P&L':>11} {'Cap P':>11}  Exit")
        print(f"  {'-'*125}")

        for t in trades:
            mk       = month_key(t["td"])
            cost_f   = t["entry_p"] * T1_LOTS       * lot_size
            cost_p   = t["entry_p"] * t["lots_pyr"] * lot_size
            skip_f   = cap_f < RUIN_THRESHOLD or cost_f > cap_f * MAX_TRADE_PCT
            skip_p   = cap_p < RUIN_THRESHOLD or cost_p > cap_p * MAX_TRADE_PCT

            if skip_f and skip_p:
                continue

            pnl_f = t["pnl_fixed"] if not skip_f else 0.0
            pnl_p = t["pnl_pyr"]   if not skip_p else 0.0

            cap_f += pnl_f
            cap_p += pnl_p
            monthly_f[mk] += pnl_f
            monthly_p[mk] += pnl_p
            monthly_n[mk] += 1

            if pnl_f > 0: wins_f += 1
            elif pnl_f < 0: loss_f += 1
            if pnl_p > 0: wins_p += 1
            elif pnl_p < 0: loss_p += 1

            if cap_f > peak_f: peak_f = cap_f
            if cap_p > peak_p: peak_p = cap_p
            dd_f = (peak_f - cap_f) / peak_f * 100
            dd_p = (peak_p - cap_p) / peak_p * 100
            if dd_f > max_dd_f: max_dd_f = dd_f
            if dd_p > max_dd_p: max_dd_p = dd_p

            if best_f  is None or pnl_f > best_f[0]:  best_f  = (pnl_f, t)
            if worst_f is None or pnl_f < worst_f[0]: worst_f = (pnl_f, t)
            if best_p_t  is None or pnl_p > best_p_t[0]:  best_p_t  = (pnl_p, t)
            if worst_p_t is None or pnl_p < worst_p_t[0]: worst_p_t = (pnl_p, t)

            flag_f = "✓" if pnl_f > 0 else "✗"
            flag_p = "✓" if pnl_p > 0 else "✗"
            t2f    = "T2" if t["t2"] else "  "
            t3f    = "T3" if t["t3"] else "  "

            print(f"  {str(t['td']):<12} "
                  f"{t['ts'].strftime('%H:%M'):<6} "
                  f"{t['pattern']:<12} "
                  f"{t['ot']:<3} "
                  f"₹{t['entry_p']:>5.0f} "
                  f"{t['lots_pyr']:>5} "
                  f"{flag_f}₹{pnl_f:>+9,.0f} ₹{cap_f:>9,.0f}  "
                  f"{flag_p}₹{pnl_p:>+9,.0f} ₹{cap_p:>9,.0f}  "
                  f"{t2f}{t3f} {t['exit_note']}")

        # Monthly summary
        print(f"\n  MONTHLY P&L — {symbol}")
        print(f"  {'Month':<10} {'N':>5}  {'Fixed P&L':>12}  {'Pyr P&L':>12}  "
              f"{'Fixed Cap':>12}  {'Pyr Cap':>12}")
        print(f"  {'-'*70}")
        cf = cp = STARTING_CAPITAL
        for mk in sorted(monthly_f.keys()):
            cf += monthly_f[mk]
            cp += monthly_p[mk]
            print(f"  {month_label(mk):<10} {monthly_n[mk]:>5}  "
                  f"₹{monthly_f[mk]:>+10,.0f}  ₹{monthly_p[mk]:>+10,.0f}  "
                  f"₹{cf:>10,.0f}  ₹{cp:>10,.0f}")

        n_total = wins_f + loss_f
        print(f"\n  ── {symbol} SUMMARY ───────────────────────────────────────")
        print(f"  Trades: {n_total}  |  Gap tolerance: {MAX_GAP_MIN}min  |  "
              f"Half-exit threshold: >{HALF_EXIT_THRESHOLD:.0f}% gain")
        print(f"\n  FIXED (1 lot, dynamic exit):")
        ret_f = (cap_f - STARTING_CAPITAL) / STARTING_CAPITAL * 100
        print(f"    Final: ₹{cap_f:,.0f}  |  P&L: ₹{cap_f-STARTING_CAPITAL:+,.0f}  "
              f"|  Return: {ret_f:+.1f}%")
        print(f"    Win rate: {wins_f}/{n_total} = {100*wins_f/n_total:.1f}%  "
              f"|  Max DD: {max_dd_f:.1f}%")
        if best_f:
            print(f"    Best:  ₹{best_f[0]:+,.0f}  ({best_f[1]['pattern']} "
                  f"{best_f[1]['td']}  {best_f[1]['exit_note'][:20]})")
        if worst_f:
            print(f"    Worst: ₹{worst_f[0]:+,.0f}  ({worst_f[1]['pattern']} "
                  f"{worst_f[1]['td']}  {worst_f[1]['exit_note'][:20]})")

        print(f"\n  PYRAMID (1→3→6, dynamic exit + half-exit):")
        ret_p = (cap_p - STARTING_CAPITAL) / STARTING_CAPITAL * 100
        print(f"    Final: ₹{cap_p:,.0f}  |  P&L: ₹{cap_p-STARTING_CAPITAL:+,.0f}  "
              f"|  Return: {ret_p:+.1f}%")
        print(f"    Win rate: {wins_p}/{n_total} = {100*wins_p/n_total:.1f}%  "
              f"|  Max DD: {max_dd_p:.1f}%")
        if best_p_t:
            print(f"    Best:  ₹{best_p_t[0]:+,.0f}  ({best_p_t[1]['pattern']} "
                  f"{best_p_t[1]['td']}  {best_p_t[1]['exit_note'][:25]})")
        if worst_p_t:
            print(f"    Worst: ₹{worst_p_t[0]:+,.0f}  ({worst_p_t[1]['pattern']} "
                  f"{worst_p_t[1]['td']}  {worst_p_t[1]['exit_note'][:25]})")

    # ── Combined ──────────────────────────────────────────────────────
    print(f"\n{'='*120}")
    print("  v2 CHANGES vs v1:")
    print("  + MAX_GAP_MIN 3→5: recovers more trades from sparse option bars")
    print("  + Cut losers at T+30m: stops premium decay on wrong-direction trades")
    print("  + Ride winners to T+60m: captures full move on trending days")
    print(f"  + Half-exit at T+30m when gain >{HALF_EXIT_THRESHOLD:.0f}%: locks gains, "
          f"holds residual")
    print(f"\n  Combined starting: ₹{STARTING_CAPITAL*2:,.0f}")
    print(f"  Combined final = NIFTY final + SENSEX final (shown above)")
    print(f"\n  Realistic cost estimates:")
    print(f"  Bid-ask: ₹3-5 per option × lots × trades ≈ 3-8% of gross P&L")
    print(f"  Brokerage: ₹40-80 per lot per trade")
    print(f"  Net return ≈ gross return × 0.85-0.92")
    print(f"{'='*120}\n")


if __name__ == "__main__":
    main()


