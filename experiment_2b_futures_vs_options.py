#!/usr/bin/env python3
"""
experiment_2b_futures_vs_options.py
MERDIAN Experiment 2b — Futures vs Options vs Combined Position

For each proven ICT pattern, computes P&L for three execution structures:

  STRUCTURE 1 — OPTIONS ONLY
    Buy ATM CE (bullish) or ATM PE (bearish) at pattern detection bar.
    Hold to T+15m, T+30m, T+60m. Exit at option close price.
    Max loss: 100% of premium paid.

  STRUCTURE 2 — FUTURES ONLY WITH STOP
    Enter futures long (bullish) or short (bearish) at pattern detection bar.
    Stop-loss at STOP_PCT% adverse move (checked against bar extremes).
    Exit at T+15m, T+30m, T+60m if not stopped.
    P&L expressed as % of futures entry price.

  STRUCTURE 3 — FUTURES + INSURANCE OPTION (COMBINED)
    Long/short futures + buy the opposite-direction option as insurance.
    Example: BULL trade = Long futures + Buy ATM PE (floor on loss).
    If futures stop triggers, PE gain partially/fully offsets the loss.
    Combined P&L normalised to % of spot price for fair comparison:
      combined_pct = futures_pnl_pct + option_pnl_pct × (option_price / futures_price)

Key questions answered:
  1. Which instrument wins at each DTE bucket?
     Hypothesis: DTE=0 → options (gamma explosion)
                 DTE=4+ → futures (no theta drag)
  2. Does the combined position outperform either standalone?
  3. What % of futures stops are recovered by the insurance option?
  4. What is the risk-adjusted return of each structure?

Patterns tested:
  BEAR_OB, BULL_OB   — proven in Exp 10/10b/10c
  JUDAS_BEAR/BULL    — proven in Exp 10/10b/10c
  BULL_FVG           — positive expectancy in Exp 10c
  BOS_BULL, MSS_BULL — high N, positive expectancy in Exp 10c

Futures data: hist_future_bars_1m
  NIFTY:  contract_series=1 (front-month continuous backadjusted)
  SENSEX: contract_series=0, nearest expiry (individual dated)

STOP_PCT = 0.20% (approximately 46pt NIFTY / 154pt SENSEX at current levels)
  Rationale: ~2× average 1-min ATR, mechanically tight, executable on liquid futures.

Read-only. Runtime: ~20-30 minutes.

Usage:
    python experiment_2b_futures_vs_options.py
"""

import os
import bisect
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
HORIZONS  = [15, 30, 60]
SESSION_END = dtime(15, 30)

# ── Execution parameters ──────────────────────────────────────────────
STOP_PCT         = 0.20   # % adverse move triggers futures stop
MIN_OPTION_PRICE = 5.0
ATM_RADIUS       = 3
MAX_GAP_MIN      = 3

# ── Instrument conventions ────────────────────────────────────────────
STRIKE_STEP = {"NIFTY": 50, "SENSEX": 100}

# ── Patterns and their option direction ──────────────────────────────
TARGET_PATTERNS = {
    "BEAR_OB": "PE", "BULL_OB": "CE",
    "JUDAS_BEAR": "PE", "JUDAS_BULL": "CE",
    "BULL_FVG": "CE", "BEAR_FVG": "PE",
    "BOS_BULL": "CE", "MSS_BULL": "CE",
    "BOS_BEAR": "PE", "MSS_BEAR": "PE",
}

# Direction multiplier: +1 = long (profit if price rises), -1 = short
DIRECTION = {
    "BEAR_OB": -1, "BEAR_FVG": -1, "BOS_BEAR": -1,
    "MSS_BEAR": -1, "JUDAS_BEAR": -1,
    "BULL_OB": +1, "BULL_FVG": +1, "BOS_BULL": +1,
    "MSS_BULL": +1, "JUDAS_BULL": +1,
}

# ── Detection parameters ──────────────────────────────────────────────
SWING_LB        = 5
OB_MIN_MOVE_PCT = 0.40
FVG_MIN_PCT     = 0.10
JUDAS_MIN_PCT   = 0.25


# ── Utilities ─────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def pct(a, b):
    return 100.0 * (b - a) / a if a else 0.0

def in_session(ts, h):
    return (ts + timedelta(minutes=h)).time() <= SESSION_END

def atm_strike(spot, symbol):
    s = STRIKE_STEP[symbol]
    return round(spot / s) * s

def compute_dte(td, expiry_idx):
    ed = nearest_expiry_db(td, expiry_idx)
    return (ed - td).days if ed else 0

def dte_bucket(dte):
    if dte == 0: return "DTE=0"
    if dte == 1: return "DTE=1"
    if dte <= 3: return "DTE=2-3"
    return "DTE=4+"


# ── Data loading ──────────────────────────────────────────────────────

def fetch_bars(sb, table, filters, select="bar_ts, trade_date, open, high, low, close"):
    """Generic paginated bar fetch with retry on transient connection errors."""
    import time
    all_rows, offset = [], 0
    while True:
        q = sb.table(table).select(select).order("bar_ts").range(offset, offset+PAGE_SIZE-1)
        for method, *args in filters:
            q = getattr(q, method)(*args)
        rows = None
        for attempt in range(4):
            try:
                rows = q.execute().data
                break
            except Exception as e:
                if attempt == 3:
                    raise
                wait = 2 ** attempt
                log(f"    Connection error (attempt {attempt+1}/4), retrying in {wait}s...")
                time.sleep(wait)
        for r in rows:
            r["bar_ts"]     = datetime.fromisoformat(r["bar_ts"])
            r["trade_date"] = date.fromisoformat(r["trade_date"])
            for k in ("open","high","low","close"):
                if k in r and r[k] is not None:
                    r[k] = float(r[k])
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset % 20_000 == 0:
            log(f"    {offset:,} bars loaded...")
    return all_rows


def sessions_from_bars(bars):
    result = {}
    for k, g in groupby(bars, key=lambda b: b["trade_date"]):
        result[k] = list(g)
    return result


def nearest_bar_price(bars, target_ts, max_gap=MAX_GAP_MIN):
    """Binary search for close price nearest to target_ts in sorted bar list."""
    if not bars:
        return None, None
    tss = [b["bar_ts"] for b in bars]
    idx = bisect.bisect_left(tss, target_ts)
    best_p, best_g, best_b = None, timedelta(minutes=max_gap+1), None
    for i in (idx-1, idx):
        if 0 <= i < len(bars):
            g = abs(bars[i]["bar_ts"] - target_ts)
            if g < best_g:
                best_g, best_p, best_b = g, bars[i]["close"], bars[i]
    return (best_p, best_b) if best_g <= timedelta(minutes=max_gap) else (None, None)


def check_stop(bars_session, entry_ts, exit_ts, entry_price, direction, stop_pct=STOP_PCT):
    """
    Check if stop was triggered between entry_ts and exit_ts.
    Scans bar extremes (high/low) in the window.
    Returns True if stop was triggered, False otherwise.
    """
    stop_level = entry_price * (1 - direction * stop_pct / 100)
    tss = [b["bar_ts"] for b in bars_session]
    start_idx = bisect.bisect_left(tss, entry_ts)
    end_idx   = bisect.bisect_right(tss, exit_ts)
    for i in range(start_idx, end_idx):
        b = bars_session[i]
        if direction == +1 and b["low"] <= stop_level:
            return True   # long stop hit
        if direction == -1 and b["high"] >= stop_level:
            return True   # short stop hit
    return False


def fetch_option_day(sb, inst_id, td, ed, strikes, opt_types):
    """Fetch option bars for one day. Returns lookup (strike, opt_type, bar_ts) → close."""
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


def get_option_price(lookup, strike, ot, target_ts, symbol):
    step = STRIKE_STEP[symbol]
    candidates = [strike + i*step for i in range(-ATM_RADIUS, ATM_RADIUS+1)]
    best_p, best_g, best_stk = None, timedelta(minutes=MAX_GAP_MIN+1), None
    for stk in candidates:
        ts_list = sorted(ts for (s,o,ts) in lookup if s==stk and o==ot)
        if not ts_list:
            continue
        idx = bisect.bisect_left(ts_list, target_ts)
        for i in (idx-1, idx):
            if 0 <= i < len(ts_list):
                gap = abs(ts_list[i] - target_ts)
                if gap < best_g:
                    p = lookup.get((stk, ot, ts_list[i]))
                    if p:
                        best_g, best_p, best_stk = gap, p, stk
    return (best_p, best_stk) if best_g <= timedelta(minutes=MAX_GAP_MIN) else (None, None)


# ── Pattern detectors ─────────────────────────────────────────────────

def find_swings(bars, lb=SWING_LB):
    swings, n = [], len(bars)
    for i in range(lb, n-lb):
        w = range(i-lb, i+lb+1)
        h, l = bars[i]["high"], bars[i]["low"]
        if all(bars[j]["high"] <= h for j in w if j != i):
            swings.append((i,"HIGH",h))
        if all(bars[j]["low"]  >= l for j in w if j != i):
            swings.append((i,"LOW",l))
    return swings


def detect_obs(bars):
    out, seen, n = [], set(), len(bars)
    for i in range(n-6):
        mv = pct(bars[i]["close"], bars[min(i+5,n-1)]["close"])
        if mv <= -OB_MIN_MOVE_PCT:
            for j in range(i, max(i-6,-1), -1):
                if bars[j]["close"] > bars[j]["open"] and j not in seen:
                    seen.add(j)
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BEAR_OB"))
                    break
        elif mv >= OB_MIN_MOVE_PCT:
            for j in range(i, max(i-6,-1), -1):
                if bars[j]["close"] < bars[j]["open"] and j not in seen:
                    seen.add(j)
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BULL_OB"))
                    break
    return out


def detect_fvg(bars):
    out, min_g = [], FVG_MIN_PCT/100.0
    for i in range(1, len(bars)-1):
        p, c, n = bars[i-1], bars[i], bars[i+1]
        ref = c["close"]
        if p["low"] > n["high"] and (p["low"]-n["high"])/ref >= min_g:
            out.append(dict(bar_idx=i, bar=c, pattern="BEAR_FVG"))
        if p["high"] < n["low"] and (n["low"]-p["high"])/ref >= min_g:
            out.append(dict(bar_idx=i, bar=c, pattern="BULL_FVG"))
    return out


def detect_mss_bos(bars, swings):
    out = []
    if len(swings) < 4:
        return out
    highs = [(idx,p) for idx,t,p in swings if t=="HIGH"]
    lows  = [(idx,p) for idx,t,p in swings if t=="LOW"]
    for i in range(1, len(bars)):
        ph = [(idx,p) for idx,p in highs if idx<i]
        pl = [(idx,p) for idx,t,p in lows  if t=="LOW" and idx<i] \
             if False else [(idx,p) for idx,p in lows if idx<i]
        if len(ph)<2 or len(pl)<2:
            continue
        lsh,psh = ph[-1][1],ph[-2][1]
        lsl,psl = pl[-1][1],pl[-2][1]
        c,pc = bars[i]["close"], bars[i-1]["close"]
        up   = lsh>psh and lsl>psl
        down = lsh<psh and lsl<psl
        if   up   and c>lsh and pc<=lsh:
            out.append(dict(bar_idx=i,bar=bars[i],pattern="BOS_BULL"))
        elif down and c<lsl and pc>=lsl:
            out.append(dict(bar_idx=i,bar=bars[i],pattern="BOS_BEAR"))
        elif down and c>lsh and pc<=lsh:
            out.append(dict(bar_idx=i,bar=bars[i],pattern="MSS_BULL"))
        elif up   and c<lsl and pc>=lsl:
            out.append(dict(bar_idx=i,bar=bars[i],pattern="MSS_BEAR"))
    return out


def detect_judas(bars):
    out = []
    if len(bars) < 46:
        return out
    mv = pct(bars[0]["open"], bars[14]["close"])
    if abs(mv) < JUDAS_MIN_PCT:
        return out
    rev = bars[15:45]
    if mv > 0:
        if pct(bars[14]["close"], min(b["low"] for b in rev)) <= -mv*0.50:
            out.append(dict(bar_idx=14, bar=bars[14], pattern="JUDAS_BEAR"))
    else:
        if pct(bars[14]["close"], max(b["high"] for b in rev)) >= abs(mv)*0.50:
            out.append(dict(bar_idx=14, bar=bars[14], pattern="JUDAS_BULL"))
    return out


# ── P&L aggregation ───────────────────────────────────────────────────

class TripleBucket:
    """Tracks P&L for options, futures, and combined positions."""
    def __init__(self):
        self.n_pats    = 0
        self.opt_pnl   = {h: [] for h in HORIZONS}  # % of option premium
        self.fut_pnl   = {h: [] for h in HORIZONS}  # % of futures price
        self.comb_pnl  = {h: [] for h in HORIZONS}  # % of spot (normalised)
        self.stops_hit = {h: 0   for h in HORIZONS}
        self.stops_recovered = {h: 0 for h in HORIZONS}

    def add(self, opt_dict, fut_dict, comb_dict, stop_dict):
        self.n_pats += 1
        for h in HORIZONS:
            if opt_dict.get(h) is not None:
                self.opt_pnl[h].append(opt_dict[h])
            if fut_dict.get(h) is not None:
                self.fut_pnl[h].append(fut_dict[h])
                if stop_dict.get(h):
                    self.stops_hit[h] += 1
            if comb_dict.get(h) is not None:
                self.comb_pnl[h].append(comb_dict[h])
                if stop_dict.get(h) and opt_dict.get(h) is not None and opt_dict[h] > 0:
                    self.stops_recovered[h] += 1

    def stats(self, pnl_list):
        if not pnl_list:
            return None
        wins = [x for x in pnl_list if x > 0]
        loss = [x for x in pnl_list if x <= 0]
        wr   = len(wins)/len(pnl_list)
        aw   = sum(wins)/len(wins) if wins else 0.0
        al   = sum(loss)/len(loss) if loss else 0.0
        return dict(n=len(pnl_list), wr=wr*100,
                    avg=sum(pnl_list)/len(pnl_list),
                    exp=wr*aw+(1-wr)*al,
                    best=max(pnl_list), worst=min(pnl_list))


def fmt(v, w=9):
    if v is None: return f"{'n/a':>{w}}"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%".rjust(w)


def print_triple_table(title, rows_data, sort_h=30, min_n=5):
    print(f"\n{'='*130}")
    print(f"  {title}")
    print(f"{'='*130}")
    print(f"  {'Label':<35} {'N':>5}  "
          f"{'Opt Exp T+30':>13}  {'Fut Exp T+30':>13}  {'Comb Exp T+30':>14}  "
          f"{'Opt WR':>8}  {'Fut WR':>8}  {'Stops%':>8}  {'Stops Recov%':>13}  Winner")
    print(f"  {'-'*125}")

    rows = [(label, b) for label,b in rows_data if b.n_pats >= min_n]

    def sort_key(x):
        s = x[1].stats(x[1].opt_pnl[sort_h])
        return s["exp"] if s else -999
    rows.sort(key=sort_key, reverse=True)

    for label, b in rows:
        so = b.stats(b.opt_pnl[30])
        sf = b.stats(b.fut_pnl[30])
        sc = b.stats(b.comb_pnl[30])
        n_fut = len(b.fut_pnl[30])

        opt_exp  = so["exp"]  if so else None
        fut_exp  = sf["exp"]  if sf else None
        comb_exp = sc["exp"]  if sc else None
        opt_wr   = f"{so['wr']:.0f}%" if so else "n/a"
        fut_wr   = f"{sf['wr']:.0f}%" if sf else "n/a"
        stops_pct = f"{100*b.stops_hit[30]/n_fut:.0f}%" if n_fut else "n/a"
        recov_pct = (f"{100*b.stops_recovered[30]/max(b.stops_hit[30],1):.0f}%"
                     if b.stops_hit[30] > 0 else "0%")

        # Determine winner
        exps = {
            "Options": opt_exp or -999,
            "Futures": fut_exp or -999,
            "Combined": comb_exp or -999,
        }
        winner = max(exps, key=exps.get) if any(v > -999 for v in exps.values()) else "n/a"
        flag = " ◄" if (opt_exp or 0) > 5 or (fut_exp or 0) > 5 else ""

        print(f"  {label:<35} {b.n_pats:>5}  "
              f"{fmt(opt_exp):>13}  {fmt(fut_exp):>13}  {fmt(comb_exp):>14}  "
              f"{opt_wr:>8}  {fut_wr:>8}  {stops_pct:>8}  {recov_pct:>13}  "
              f"{winner}{flag}")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    # Aggregation buckets
    by_pattern  = defaultdict(TripleBucket)  # pattern
    by_pat_dte  = defaultdict(TripleBucket)  # pattern|DTE
    by_pat_sym  = defaultdict(TripleBucket)  # pattern|symbol

    for symbol in ["NIFTY", "SENSEX"]:
        expiry_idx = build_expiry_index_simple(sb, inst[symbol])
        log(f"\n── {symbol} ─────────────────────────────────────────────")

        # ── Load spot bars ────────────────────────────────────────────
        log("  Loading spot bars...")
        spot_bars = fetch_bars(
            sb, "hist_spot_bars_1m",
            [("eq","instrument_id",inst[symbol]),("eq","is_pre_market",False)]
        )
        spot_sessions = sessions_from_bars(spot_bars)
        dates = sorted(spot_sessions.keys())
        log(f"  {len(spot_bars):,} spot bars | {len(dates)} sessions")

        # ── Load futures bars ─────────────────────────────────────────
        log("  Loading futures bars...")
        cs = 1 if symbol == "NIFTY" else 0  # NIFTY=continuous, SENSEX=individual
        fut_bars = fetch_bars(
            sb, "hist_future_bars_1m",
            [("eq","instrument_id",inst[symbol]),("eq","contract_series",cs)],
            select="bar_ts, trade_date, open, high, low, close"
        )
        fut_sessions = sessions_from_bars(fut_bars)
        log(f"  {len(fut_bars):,} futures bars")

        # ── Detect patterns ───────────────────────────────────────────
        log("  Detecting patterns...")
        all_patterns = []
        for i, d in enumerate(dates):
            bars = spot_sessions[d]
            if len(bars) < 30:
                continue
            sw   = find_swings(bars)
            pats = (detect_obs(bars)
                    + detect_fvg(bars)
                    + detect_mss_bos(bars, sw)
                    + detect_judas(bars))
            for pat in pats:
                if pat["pattern"] not in TARGET_PATTERNS:
                    continue
                bar     = pat["bar"]
                spot    = bar["close"]
                dte     = compute_dte(d, expiry_idx)
                exp_d   = nearest_expiry_db(d, expiry_idx)
                all_patterns.append({
                    "pattern":  pat["pattern"],
                    "bar":      bar,
                    "td":       d,
                    "exp_date": exp_d,
                    "atm":      atm_strike(spot, symbol),
                    "opt_type": TARGET_PATTERNS[pat["pattern"]],
                    "ins_type": "CE" if TARGET_PATTERNS[pat["pattern"]]=="PE" else "PE",
                    "direction":DIRECTION[pat["pattern"]],
                    "dte":      dte,
                    "dteb":     dte_bucket(dte),
                })

        log(f"  {len(all_patterns)} patterns detected")

        # ── Fetch options and score all structures ────────────────────
        day_groups = defaultdict(list)
        for pat in all_patterns:
            day_groups[(pat["td"], pat["exp_date"])].append(pat)

        log(f"  Scoring {len(day_groups)} day/expiry groups...")

        for gi, ((td, ed), pats_today) in enumerate(sorted(day_groups.items())):
            # Strikes needed — both option type AND insurance type
            step = STRIKE_STEP[symbol]
            strikes_needed   = set()
            opt_types_needed = set()
            for pat in pats_today:
                base = pat["atm"]
                for r in range(-ATM_RADIUS, ATM_RADIUS+1):
                    strikes_needed.add(base + r*step)
                opt_types_needed.add(pat["opt_type"])
                opt_types_needed.add(pat["ins_type"])  # insurance option

            try:
                opt_lookup = fetch_option_day(
                    sb, inst[symbol], td, ed,
                    sorted(strikes_needed), sorted(opt_types_needed)
                )
            except Exception as e:
                log(f"    WARNING {td}: {e}")
                continue

            if gi % 40 == 0:
                log(f"    {gi}/{len(day_groups)} groups...")

            fut_session = fut_sessions.get(td, [])
            spot_session = spot_sessions.get(td, [])

            for pat in pats_today:
                ts        = pat["bar"]["bar_ts"]
                stk       = pat["atm"]
                ot        = pat["opt_type"]
                ins_t     = pat["ins_type"]
                direction = pat["direction"]
                pat_name  = pat["pattern"]
                dteb      = pat["dteb"]

                # ── Futures entry ─────────────────────────────────────
                fut_entry, _ = nearest_bar_price(fut_session, ts)
                if fut_entry is None:
                    continue

                # ── Options entry ─────────────────────────────────────
                opt_entry, opt_stk = get_option_price(opt_lookup, stk, ot, ts, symbol)
                ins_entry, ins_stk = get_option_price(opt_lookup, stk, ins_t, ts, symbol)

                # Insurance normalisation factor
                ins_factor = (ins_entry / fut_entry) if (ins_entry and fut_entry) else None

                opt_dict  = {}
                fut_dict  = {}
                comb_dict = {}
                stop_dict = {}

                for h in HORIZONS:
                    if not in_session(ts, h):
                        opt_dict[h] = fut_dict[h] = comb_dict[h] = stop_dict[h] = None
                        continue

                    exit_ts = ts + timedelta(minutes=h)

                    # Futures P&L
                    fut_exit, _ = nearest_bar_price(fut_session, exit_ts)
                    if fut_exit is None:
                        fut_dict[h] = stop_dict[h] = None
                    else:
                        stopped = check_stop(
                            fut_session, ts, exit_ts,
                            fut_entry, direction
                        )
                        stop_dict[h] = stopped
                        if stopped:
                            fut_dict[h] = -STOP_PCT  # capped loss
                        else:
                            fut_dict[h] = pct(fut_entry, fut_exit) * direction

                    # Options P&L (hold original ATM strike)
                    if opt_entry and opt_stk:
                        opt_exit, _ = get_option_price(opt_lookup, opt_stk, ot, exit_ts, symbol)
                        opt_dict[h] = pct(opt_entry, opt_exit) if opt_exit else None
                    else:
                        opt_dict[h] = None

                    # Combined P&L (futures + insurance option)
                    if fut_dict[h] is not None and ins_entry and ins_stk and ins_factor:
                        ins_exit, _ = get_option_price(opt_lookup, ins_stk, ins_t, exit_ts, symbol)
                        if ins_exit:
                            ins_pnl_spot = pct(ins_entry, ins_exit) * ins_factor
                            comb_dict[h] = fut_dict[h] + ins_pnl_spot
                        else:
                            comb_dict[h] = fut_dict[h]
                    else:
                        comb_dict[h] = None

                # Record
                by_pattern[pat_name].add(opt_dict, fut_dict, comb_dict, stop_dict)
                by_pat_dte[f"{pat_name}|{dteb}"].add(opt_dict, fut_dict, comb_dict, stop_dict)
                by_pat_sym[f"{pat_name}|{symbol}"].add(opt_dict, fut_dict, comb_dict, stop_dict)

        log(f"  {symbol} complete.")

    # ── Output ────────────────────────────────────────────────────────
    print("\n" + "=" * 130)
    print("  MERDIAN EXPERIMENT 2b — FUTURES vs OPTIONS vs COMBINED POSITION")
    print(f"  Period: Apr 2025 – Mar 2026  |  NIFTY + SENSEX  |  Stop-loss: {STOP_PCT}%")
    print("  Opt Exp = options expectancy (% of premium)  |  "
          "Fut Exp = futures expectancy (% of spot)  |  "
          "Comb = futures+insurance option")
    print("  Stops% = % of futures trades that hit the stop  |  "
          "Stops Recov% = % of stops where insurance option was profitable")
    print("  Winner = which structure had highest T+30m expectancy")
    print("=" * 130)

    print_triple_table(
        "SECTION 1 — BASELINE: All patterns, all DTE, both symbols",
        [(k,v) for k,v in by_pattern.items()],
        min_n=5
    )

    print_triple_table(
        "SECTION 2 — BY PATTERN × DTE\n"
        "  Key hypothesis: DTE=0→Options win (gamma) | DTE=4+→Futures win (no theta)",
        [(k,v) for k,v in by_pat_dte.items()],
        min_n=5
    )

    print_triple_table(
        "SECTION 3 — BY PATTERN × SYMBOL",
        [(k,v) for k,v in by_pat_sym.items()],
        min_n=5
    )

    # ── Section 4: DTE pivot table ────────────────────────────────────
    print(f"\n{'='*130}")
    print("  SECTION 4 — DTE PIVOT: Which instrument wins at each DTE?")
    print("  Aggregated across ALL bullish patterns (OB+FVG+BOS+MSS+Judas)")
    print(f"{'='*130}")
    print(f"  {'DTE':>12}  {'N':>6}  {'Opt Exp T+30':>14}  "
          f"{'Fut Exp T+30':>14}  {'Comb Exp T+30':>15}  "
          f"{'Stops%':>8}  {'Recov%':>8}  Winner")
    print(f"  {'-'*105}")

    bull_patterns = ["BULL_OB","BULL_FVG","BOS_BULL","MSS_BULL","JUDAS_BULL"]
    for dteb in ["DTE=0", "DTE=1", "DTE=2-3", "DTE=4+"]:
        agg = TripleBucket()
        for pat in bull_patterns:
            key = f"{pat}|{dteb}"
            b   = by_pat_dte.get(key)
            if b:
                for h in HORIZONS:
                    agg.opt_pnl[h].extend(b.opt_pnl[h])
                    agg.fut_pnl[h].extend(b.fut_pnl[h])
                    agg.comb_pnl[h].extend(b.comb_pnl[h])
                    agg.stops_hit[h] += b.stops_hit[h]
                    agg.stops_recovered[h] += b.stops_recovered[h]
                agg.n_pats += b.n_pats

        if agg.n_pats < 5:
            continue
        so = agg.stats(agg.opt_pnl[30])
        sf = agg.stats(agg.fut_pnl[30])
        sc = agg.stats(agg.comb_pnl[30])
        n_fut = len(agg.fut_pnl[30])
        stops_pct = f"{100*agg.stops_hit[30]/n_fut:.0f}%" if n_fut else "n/a"
        recov_pct = f"{100*agg.stops_recovered[30]/max(agg.stops_hit[30],1):.0f}%" \
                    if agg.stops_hit[30] > 0 else "0%"
        exps = {"Options": (so["exp"] if so else -999),
                "Futures": (sf["exp"] if sf else -999),
                "Combined":(sc["exp"] if sc else -999)}
        winner = max(exps, key=exps.get)
        print(f"  {dteb:>12}  {agg.n_pats:>6}  "
              f"{fmt(so['exp'] if so else None):>14}  "
              f"{fmt(sf['exp'] if sf else None):>14}  "
              f"{fmt(sc['exp'] if sc else None):>15}  "
              f"{stops_pct:>8}  {recov_pct:>8}  {winner}")

    # ── Section 5: Insurance effectiveness ───────────────────────────
    print(f"\n{'='*130}")
    print("  SECTION 5 — INSURANCE OPTION EFFECTIVENESS")
    print("  When futures stop was triggered, how much did the insurance option recover?")
    print(f"  Stop distance: {STOP_PCT}% | Insurance = opposite ATM option bought at entry")
    print(f"{'='*130}")
    print(f"  {'Pattern':<20} {'Stops T+30':>12}  {'Recov>0':>10}  "
          f"{'Recov Rate':>12}  Interpretation")
    print(f"  {'-'*80}")

    for pat_name in sorted(by_pattern.keys()):
        b = by_pattern[pat_name]
        n_fut = len(b.fut_pnl[30])
        if n_fut == 0:
            continue
        stops = b.stops_hit[30]
        recov = b.stops_recovered[30]
        rate  = 100*recov/max(stops,1)
        interp = ""
        if stops == 0:
            interp = "No stops triggered"
        elif rate >= 75:
            interp = "Insurance highly effective — covers most stops"
        elif rate >= 50:
            interp = "Insurance partially effective"
        elif rate >= 25:
            interp = "Insurance marginal"
        else:
            interp = "Insurance rarely helps — market moves one-way"
        print(f"  {pat_name:<20} {stops:>12}  {recov:>10}  {rate:>10.0f}%  {interp}")

    # ── Summary ───────────────────────────────────────────────────────
    print(f"\n{'='*130}")
    print("  SUMMARY — RECOMMENDED EXECUTION STRUCTURE BY PATTERN + DTE")
    print(f"  Based on T+30m expectancy comparison")
    print(f"{'='*130}")
    print(f"  {'Pattern × DTE':<30} {'Opt Exp':>10}  {'Fut Exp':>10}  "
          f"{'Comb Exp':>10}  Recommended")
    print(f"  {'-'*80}")

    priority_patterns = ["BULL_OB","BEAR_OB","JUDAS_BULL","JUDAS_BEAR","BULL_FVG"]
    for pat in priority_patterns:
        for dteb in ["DTE=0","DTE=1","DTE=2-3","DTE=4+"]:
            key = f"{pat}|{dteb}"
            b   = by_pat_dte.get(key)
            if not b or b.n_pats < 3:
                continue
            so = b.stats(b.opt_pnl[30])
            sf = b.stats(b.fut_pnl[30])
            sc = b.stats(b.comb_pnl[30])
            opt_e  = so["exp"] if so else None
            fut_e  = sf["exp"] if sf else None
            comb_e = sc["exp"] if sc else None

            exps = {}
            if opt_e  is not None: exps["Options"]  = opt_e
            if fut_e  is not None: exps["Futures"]  = fut_e
            if comb_e is not None: exps["Combined"] = comb_e
            if not exps:
                continue
            rec = max(exps, key=exps.get)
            best_exp = exps[rec]
            flag = " ← use this" if best_exp > 10 else ""

            print(f"  {pat+' '+dteb:<30} {fmt(opt_e):>10}  "
                  f"{fmt(fut_e):>10}  {fmt(comb_e):>10}  {rec}{flag}")

    print(f"\n{'='*130}")
    print(f"  NOTE: Futures P&L is % of spot price (point move / entry × 100)")
    print(f"  NOTE: Options P&L is % of option premium (much higher leverage)")
    print(f"  NOTE: Combined normalises to % of spot — direct comparison to futures")
    print(f"  NOTE: Stop = {STOP_PCT}% adverse move on futures (tight, executable on NIFTY/SENSEX)")
    print(f"  NOTE: Insurance option = opposite ATM option bought simultaneously at entry")
    print(f"{'='*130}\n")


if __name__ == "__main__":
    main()



