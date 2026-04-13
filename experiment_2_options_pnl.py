#!/usr/bin/env python3
"""
experiment_2_options_pnl.py
MERDIAN Experiment 2 — Actual Options P&L Simulation

For the 4 proven patterns from Experiment 10/10b:
  BEAR_OB    → Buy ATM PE  (bearish institutional candle)
  BULL_OB    → Buy ATM CE  (bullish institutional candle)
  JUDAS_BEAR → Buy ATM PE  (opening trap: fade the rally)
  JUDAS_BULL → Buy ATM CE  (opening trap: fade the drop)

For each pattern occurrence:
  1. Compute ATM strike from spot at detection bar
     NIFTY:  round(spot / 50) × 50
     SENSEX: round(spot / 100) × 100
  2. Determine nearest weekly expiry
     NIFTY: next Thursday | SENSEX: next Tuesday
  3. Fetch ATM option close price at detection bar (entry)
  4. Fetch same option close price at T+15m, T+30m, T+60m (exits)
  5. P&L = (exit - entry) / entry × 100

This answers the real question:
  "Even when spot moved correctly, did the trade make money?"
  Theta decay and IV crush can turn a correct spot call into a losing option trade.

Key metrics:
  Win rate     — % of trades with P&L > 0
  Avg P&L      — mean return across all trades
  Avg winner   — mean return of profitable trades
  Avg loser    — mean return of losing trades
  Expectancy   — win_rate × avg_winner + loss_rate × avg_loser
                 Must be positive to be worth trading
  Best/Worst   — extremes of the distribution

Note: IV is NULL in hist_option_bars_1m (post_ingest_compute not yet run).
Total P&L is measured — delta/theta/vega decomposition deferred to Experiment 7.

Read-only. Runtime: ~8-12 minutes.

Usage:
    python experiment_2_options_pnl.py
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

# ── Pattern configuration ─────────────────────────────────────────────
TARGET_PATTERNS = {"BEAR_OB", "BULL_OB", "JUDAS_BEAR", "JUDAS_BULL"}

OPT_TYPE = {
    "BEAR_OB": "PE", "JUDAS_BEAR": "PE",
    "BULL_OB": "CE", "JUDAS_BULL": "CE",
}

STRIKE_STEP = {"NIFTY": 50, "SENSEX": 100}

# NIFTY expires Thursday (weekday=3), SENSEX expires Tuesday (weekday=1)

MIN_OPTION_PRICE = 5.0    # filter stale / illiquid quotes
ATM_RADIUS       = 3      # search ATM ± this many strikes if exact not found
MAX_GAP_MIN      = 3      # nearest bar tolerance in minutes
HORIZONS         = [15, 30, 60]
SESSION_END      = dtime(15, 30)

# ── Pattern detection parameters (same as Exp 10) ────────────────────
SWING_LB        = 5
FVG_MIN_PCT     = 0.10
OB_MIN_MOVE_PCT = 0.40
JUDAS_MIN_PCT   = 0.25


# ── Utilities ─────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def pct(a, b):
    return 100.0 * (b - a) / a if a else 0.0


def in_session(ts, horizon_min):
    return (ts + timedelta(minutes=horizon_min)).time() <= SESSION_END


def atm_strike(spot, symbol):
    step = STRIKE_STEP[symbol]
    return round(spot / step) * step


def compute_dte(td, expiry_idx):
    ed = nearest_expiry_db(td, expiry_idx)
    return (ed - td).days if ed else 0


def dte_bucket(dte):
    if dte == 0: return "DTE=0 (expiry)"
    if dte == 1: return "DTE=1"
    if dte <= 3: return "DTE=2-3"
    return "DTE=4+"


def time_bucket(ts):
    t = ts.time()
    if t < dtime(9,  45): return "09:15-09:45 OPEN"
    if t < dtime(11,  0): return "09:45-11:00 MORNING"
    if t < dtime(13,  0): return "11:00-13:00 MIDDAY"
    if t < dtime(14, 30): return "13:00-14:30 AFTERNOON"
    return                       "14:30-15:30 POWER_HOUR"


# ── Data loading ──────────────────────────────────────────────────────

def fetch_spot_bars(sb, instrument_id):
    """All market-hours 1-min OHLC bars. IST stored as UTC — .time() directly."""
    all_rows, offset = [], 0
    while True:
        rows = (
            sb.table("hist_spot_bars_1m")
            .select("bar_ts, trade_date, open, high, low, close")
            .eq("instrument_id", instrument_id)
            .eq("is_pre_market", False)
            .order("bar_ts")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
            .data
        )
        for r in rows:
            r["bar_ts"]     = datetime.fromisoformat(r["bar_ts"])
            r["trade_date"] = date.fromisoformat(r["trade_date"])
            r["open"]  = float(r["open"])
            r["high"]  = float(r["high"])
            r["low"]   = float(r["low"])
            r["close"] = float(r["close"])
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset % 20_000 == 0:
            log(f"    {offset:,} spot bars loaded...")
    return all_rows


def sessions_from_bars(bars):
    result = {}
    for k, g in groupby(bars, key=lambda b: b["trade_date"]):
        result[k] = list(g)
    return result


def fetch_option_day(sb, inst_id, trade_date, expiry_date, strikes, opt_types):
    """
    Fetch all option bars for one day, specific strikes and expiry.
    Returns dict: (strike_float, opt_type, bar_ts_datetime) → close_float
    Paginates automatically.
    """
    strike_strs = [f"{float(s):.2f}" for s in strikes]
    all_rows, offset = [], 0
    while True:
        rows = (
            sb.table("hist_option_bars_1m")
            .select("bar_ts, strike, option_type, close")
            .eq("instrument_id", str(inst_id))
            .eq("trade_date", str(trade_date))
            .eq("expiry_date", str(expiry_date))
            .in_("strike", strike_strs)
            .in_("option_type", list(opt_types))
            .order("bar_ts")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
            .data
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


def get_option_price(lookup, strike, opt_type, target_ts,
                     symbol, max_gap=MAX_GAP_MIN):
    """
    Find option close price nearest to target_ts.
    Tries ATM strike first, then adjacent strikes within ATM_RADIUS.
    Returns (price, actual_strike) or (None, None).
    """
    step = STRIKE_STEP[symbol]
    candidates = [strike + i * step
                  for i in range(-ATM_RADIUS, ATM_RADIUS + 1)]

    best_p, best_g, best_stk = None, timedelta(minutes=max_gap+1), None

    for stk in candidates:
        key_prefix = (stk, opt_type)
        # Find nearest ts in lookup for this (stk, opt_type)
        matching_ts = [ts for (s, o, ts) in lookup if s == stk and o == opt_type]
        if not matching_ts:
            continue
        matching_ts.sort()
        idx = bisect.bisect_left(matching_ts, target_ts)
        for i in (idx - 1, idx):
            if 0 <= i < len(matching_ts):
                ts  = matching_ts[i]
                gap = abs(ts - target_ts)
                if gap < best_g:
                    best_g   = gap
                    best_p   = lookup.get((stk, opt_type, ts))
                    best_stk = stk

    if best_g <= timedelta(minutes=max_gap) and best_p is not None:
        return best_p, best_stk
    return None, None


# ── Pattern detectors (OB + Judas only — proven patterns) ────────────

def find_swings(bars, lb=SWING_LB):
    swings = []
    n = len(bars)
    for i in range(lb, n - lb):
        w = range(i-lb, i+lb+1)
        h, l = bars[i]["high"], bars[i]["low"]
        if all(bars[j]["high"] <= h for j in w if j != i):
            swings.append((i, "HIGH", h))
        if all(bars[j]["low"] >= l for j in w if j != i):
            swings.append((i, "LOW", l))
    return swings


def detect_obs(bars, min_move=OB_MIN_MOVE_PCT):
    out = []
    n = len(bars)
    seen = set()
    for i in range(n - 6):
        future = bars[min(i+5, n-1)]["close"]
        move   = pct(bars[i]["close"], future)
        if move <= -min_move:
            for j in range(i, max(i-6, -1), -1):
                if bars[j]["close"] > bars[j]["open"] and j not in seen:
                    seen.add(j)
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BEAR_OB"))
                    break
        elif move >= min_move:
            for j in range(i, max(i-6, -1), -1):
                if bars[j]["close"] < bars[j]["open"] and j not in seen:
                    seen.add(j)
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BULL_OB"))
                    break
    return out


def detect_judas(bars):
    out = []
    if len(bars) < 46:
        return out
    open_p  = bars[0]["open"]
    close15 = bars[14]["close"]
    mv      = pct(open_p, close15)
    if abs(mv) < JUDAS_MIN_PCT:
        return out
    rev = bars[15:45]
    if not rev:
        return out
    if mv > 0:
        if pct(close15, min(b["low"] for b in rev)) <= -mv * 0.50:
            out.append(dict(bar_idx=14, bar=bars[14], pattern="JUDAS_BEAR"))
    else:
        if pct(close15, max(b["high"] for b in rev)) >= abs(mv) * 0.50:
            out.append(dict(bar_idx=14, bar=bars[14], pattern="JUDAS_BULL"))
    return out


# ── P&L aggregation ───────────────────────────────────────────────────

class PnlBucket:
    def __init__(self):
        self.n_patterns  = 0
        self.n_no_data   = 0
        self.pnl         = {h: [] for h in HORIZONS}

    def add_no_data(self):
        self.n_patterns += 1
        self.n_no_data  += 1

    def add(self, pnl_dict):
        self.n_patterns += 1
        for h in HORIZONS:
            if pnl_dict.get(h) is not None:
                self.pnl[h].append(pnl_dict[h])

    def stats(self, h):
        vals = self.pnl[h]
        if not vals:
            return None
        n       = len(vals)
        winners = [v for v in vals if v > 0]
        losers  = [v for v in vals if v <= 0]
        avg     = sum(vals) / n
        avg_w   = sum(winners) / len(winners) if winners else 0.0
        avg_l   = sum(losers)  / len(losers)  if losers  else 0.0
        wr      = len(winners) / n
        exp     = wr * avg_w + (1-wr) * avg_l
        best    = max(vals)
        worst   = min(vals)
        return dict(n=n, win_rate=wr*100, avg=avg, avg_w=avg_w,
                    avg_l=avg_l, expectancy=exp, best=best, worst=worst)


def fmt_pct(v, width=7):
    if v is None:
        return f"{'n/a':>{width}}"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%".rjust(width)


def print_bucket(label, bucket, indent="  "):
    cov = bucket.n_patterns - bucket.n_no_data
    print(f"\n{indent}{'─'*70}")
    print(f"{indent}{label}")
    print(f"{indent}Patterns: {bucket.n_patterns} | "
          f"With option data: {cov} | "
          f"No data: {bucket.n_no_data}")
    if cov == 0:
        print(f"{indent}  (no option data found)")
        return

    hdr = f"{'':30} {'T+15m':>10} {'T+30m':>10} {'T+60m':>10}"
    print(f"{indent}{hdr}")
    print(f"{indent}{'-'*62}")

    rows = [
        ("N scored",   lambda s: str(s["n"]).rjust(9)),
        ("Win rate",   lambda s: fmt_pct(s["win_rate"])),
        ("Avg P&L",    lambda s: fmt_pct(s["avg"])),
        ("Avg winner", lambda s: fmt_pct(s["avg_w"])),
        ("Avg loser",  lambda s: fmt_pct(s["avg_l"])),
        ("Expectancy", lambda s: fmt_pct(s["expectancy"])),
        ("Best trade", lambda s: fmt_pct(s["best"])),
        ("Worst trade",lambda s: fmt_pct(s["worst"])),
    ]

    for row_label, fmt_fn in rows:
        cells = []
        for h in HORIZONS:
            s = bucket.stats(h)
            cells.append(fmt_fn(s) if s else "     n/a")
        print(f"{indent}{row_label:<30} {cells[0]:>10} {cells[1]:>10} {cells[2]:>10}")


def expectancy_flag(bucket, h):
    s = bucket.stats(h)
    if s is None:
        return ""
    if s["expectancy"] > 5:
        return " ◄ TRADE"
    if s["expectancy"] > 0:
        return " ◄ marginal"
    return " ▼ avoid"


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    # Storage: pattern → PnlBucket (combined)
    by_pattern   = defaultdict(PnlBucket)
    by_dte       = defaultdict(PnlBucket)   # "pattern|dte_bucket"
    by_symbol    = defaultdict(PnlBucket)   # "pattern|symbol"
    by_time      = defaultdict(PnlBucket)   # "pattern|time_bucket"

    # Spot move vs option P&L comparison tracker
    spot_correct_opt_win  = defaultdict(lambda: {h: 0 for h in HORIZONS})
    spot_correct_opt_lose = defaultdict(lambda: {h: 0 for h in HORIZONS})
    spot_total            = defaultdict(lambda: {h: 0 for h in HORIZONS})

    total_patterns = 0
    total_no_data  = 0

    for symbol in ["NIFTY", "SENSEX"]:
        expiry_idx = build_expiry_index_simple(sb, inst[symbol])
        log(f"\n── {symbol} ─────────────────────────────────────────────")

        log("  Loading spot bars...")
        all_bars = fetch_spot_bars(sb, inst[symbol])
        sessions = sessions_from_bars(all_bars)
        dates    = sorted(sessions.keys())
        log(f"  {len(all_bars):,} bars | {len(dates)} sessions")

        # Step 1: detect patterns across all sessions
        log("  Detecting OB + Judas patterns...")
        all_patterns = []

        for i, d in enumerate(dates):
            bars = sessions[d]
            if len(bars) < 30:
                continue
            pats = detect_obs(bars) + detect_judas(bars)
            for pat in pats:
                if pat["pattern"] not in TARGET_PATTERNS:
                    continue
                bar     = pat["bar"]
                spot    = bar["close"]
                atm_stk = atm_strike(spot, symbol)
                dte     = compute_dte(d, expiry_idx)
                exp_dt  = nearest_expiry_db(d, expiry_idx)
                all_patterns.append({
                    "pattern":     pat["pattern"],
                    "bar":         bar,
                    "trade_date":  d,
                    "expiry_date": exp_dt,
                    "atm_strike":  atm_stk,
                    "opt_type":    OPT_TYPE[pat["pattern"]],
                    "dte":         dte,
                    "dte_bucket":  dte_bucket(dte),
                    "time_bucket": time_bucket(bar["bar_ts"]),
                })

        log(f"  {len(all_patterns)} target patterns detected")

        # Step 2: group by (trade_date, expiry_date) for batched option fetch
        day_groups = defaultdict(list)
        for pat in all_patterns:
            day_groups[(pat["trade_date"], pat["expiry_date"])].append(pat)

        log(f"  Fetching option data for {len(day_groups)} day/expiry groups...")

        for gi, ((td, ed), pats_today) in enumerate(sorted(day_groups.items())):
            # Collect all strikes needed for this day
            strikes_needed = set()
            opt_types_needed = set()
            for pat in pats_today:
                step = STRIKE_STEP[symbol]
                base = pat["atm_strike"]
                for r in range(-ATM_RADIUS, ATM_RADIUS + 1):
                    strikes_needed.add(base + r * step)
                opt_types_needed.add(pat["opt_type"])

            # Fetch option data for this day
            try:
                lookup = fetch_option_day(
                    sb, inst[symbol], td, ed,
                    sorted(strikes_needed), sorted(opt_types_needed)
                )
            except Exception as e:
                log(f"    WARNING: option fetch failed for {td}/{ed}: {e}")
                for pat in pats_today:
                    by_pattern[pat["pattern"]].add_no_data()
                    total_no_data += 1
                    total_patterns += 1
                continue

            if gi % 20 == 0:
                log(f"    {gi}/{len(day_groups)} groups processed, "
                    f"{sum(len(p) for p in list(day_groups.values())[:gi]):,} patterns...")

            # Step 3: score each pattern's option P&L
            for pat in pats_today:
                entry_ts  = pat["bar"]["bar_ts"]
                entry_spot = pat["bar"]["close"]
                stk       = pat["atm_strike"]
                ot        = pat["opt_type"]
                direction = "BEAR" if ot == "PE" else "BULL"
                pat_name  = pat["pattern"]

                # Entry price
                entry_p, entry_stk = get_option_price(
                    lookup, stk, ot, entry_ts, symbol
                )

                if entry_p is None:
                    by_pattern[pat_name].add_no_data()
                    total_no_data  += 1
                    total_patterns += 1
                    continue

                # Build P&L dict for each horizon
                pnl_dict = {}
                for h in HORIZONS:
                    if not in_session(entry_ts, h):
                        pnl_dict[h] = None
                        continue
                    exit_ts = entry_ts + timedelta(minutes=h)
                    # Use SAME strike as entry (realistic hold)
                    exit_p, _ = get_option_price(
                        lookup, entry_stk, ot, exit_ts, symbol
                    )
                    # Spot move for comparison
                    spot_tss = [b["bar_ts"] for b in all_bars]
                    idx = bisect.bisect_left(spot_tss, exit_ts)
                    exit_spot = None
                    for ii in (idx-1, idx):
                        if 0 <= ii < len(all_bars):
                            if abs(all_bars[ii]["bar_ts"] - exit_ts) <= timedelta(minutes=3):
                                exit_spot = all_bars[ii]["close"]
                                break

                    if exit_p is None:
                        pnl_dict[h] = None
                    else:
                        pnl_dict[h] = pct(entry_p, exit_p)

                    # Track spot vs option comparison
                    if exit_spot is not None and exit_p is not None:
                        spot_mv = pct(entry_spot, exit_spot)
                        spot_correct = (spot_mv < 0 and direction == "BEAR") or \
                                       (spot_mv > 0 and direction == "BULL")
                        opt_win = pct(entry_p, exit_p) > 0
                        spot_total[pat_name][h] += 1
                        if spot_correct and opt_win:
                            spot_correct_opt_win[pat_name][h] += 1
                        elif spot_correct and not opt_win:
                            spot_correct_opt_lose[pat_name][h] += 1

                # Record into all buckets
                by_pattern[pat_name].add(pnl_dict)
                by_dte[f"{pat_name}|{pat['dte_bucket']}"].add(pnl_dict)
                by_symbol[f"{pat_name}|{symbol}"].add(pnl_dict)
                by_time[f"{pat_name}|{pat['time_bucket']}"].add(pnl_dict)

                total_patterns += 1

        log(f"  {symbol} done.")

    # ── Output ────────────────────────────────────────────────────────
    print("\n" + "=" * 75)
    print("  MERDIAN EXPERIMENT 2 — ACTUAL OPTIONS P&L SIMULATION")
    print("  Patterns: BEAR_OB, BULL_OB, JUDAS_BEAR, JUDAS_BULL")
    print("  Period: Apr 2025 – Mar 2026  |  NIFTY + SENSEX")
    print(f"  Total patterns: {total_patterns} | No option data: {total_no_data}")
    print("  Expectancy = win_rate × avg_winner + loss_rate × avg_loser")
    print("  ◄ TRADE = Expectancy > 5% | ◄ marginal = 0-5% | ▼ avoid = negative")
    print("=" * 75)

    # ── Section 1: By pattern ─────────────────────────────────────────
    print("\n\n" + "═" * 75)
    print("  SECTION 1 — P&L BY PATTERN")
    print("  All occurrences combined, both symbols, all DTE")
    print("═" * 75)

    for pat_name in ["BEAR_OB", "BULL_OB", "JUDAS_BEAR", "JUDAS_BULL"]:
        b = by_pattern.get(pat_name)
        if b is None:
            continue
        opt = OPT_TYPE[pat_name]
        label = f"{pat_name} → Buy ATM {opt}"
        # Add expectancy flags
        flags = " | ".join(
            f"T+{h}m{expectancy_flag(b, h)}" for h in HORIZONS
        )
        print_bucket(f"{label}   [{flags}]", b)

    # ── Section 2: Spot correct vs option P&L ────────────────────────
    print("\n\n" + "═" * 75)
    print("  SECTION 2 — SPOT MOVE CORRECT BUT OPTION LOST MONEY")
    print("  How often did a correct spot call result in an option loss?")
    print("  This is where theta decay and IV crush destroy value.")
    print("═" * 75)
    print(f"\n  {'Pattern':<20} {'Horizon':>8}  {'Spot✓+Opt✓':>12}  "
          f"{'Spot✓+Opt✗':>12}  {'Theta kill%':>12}")
    print(f"  {'-'*68}")

    for pat_name in ["BEAR_OB", "BULL_OB", "JUDAS_BEAR", "JUDAS_BULL"]:
        for h in HORIZONS:
            tot = spot_total[pat_name][h]
            if tot == 0:
                continue
            sw = spot_correct_opt_win[pat_name][h]
            sl = spot_correct_opt_lose[pat_name][h]
            theta_kill = 100 * sl / (sw + sl) if (sw + sl) > 0 else 0
            flag = " ← significant" if theta_kill > 20 else ""
            print(f"  {pat_name:<20} T+{h:>2}m   "
                  f"{sw:>12}   {sl:>12}   "
                  f"{theta_kill:>10.1f}%{flag}")

    # ── Section 3: By DTE bucket ──────────────────────────────────────
    print("\n\n" + "═" * 75)
    print("  SECTION 3 — P&L BY DTE BUCKET")
    print("  Does expiry proximity improve or hurt option P&L?")
    print("  Hypothesis: DTE=0 has highest gamma but fastest theta decay")
    print("═" * 75)

    for pat_name in ["BEAR_OB", "BULL_OB", "JUDAS_BEAR", "JUDAS_BULL"]:
        print(f"\n  {pat_name}")
        for dteb in ["DTE=0 (expiry)", "DTE=1", "DTE=2-3", "DTE=4+"]:
            key = f"{pat_name}|{dteb}"
            b   = by_dte.get(key)
            if b and b.n_patterns >= 3:
                print_bucket(dteb, b, indent="    ")

    # ── Section 4: By symbol ──────────────────────────────────────────
    print("\n\n" + "═" * 75)
    print("  SECTION 4 — P&L BY SYMBOL")
    print("  NIFTY vs SENSEX: do options behave differently?")
    print("═" * 75)

    for pat_name in ["BEAR_OB", "BULL_OB", "JUDAS_BEAR", "JUDAS_BULL"]:
        print(f"\n  {pat_name}")
        for sym in ["NIFTY", "SENSEX"]:
            key = f"{pat_name}|{sym}"
            b   = by_symbol.get(key)
            if b and b.n_patterns >= 3:
                print_bucket(sym, b, indent="    ")

    # ── Section 5: By time of day ─────────────────────────────────────
    print("\n\n" + "═" * 75)
    print("  SECTION 5 — P&L BY TIME OF DAY")
    print("  Which kill zone produces the best option P&L?")
    print("═" * 75)

    time_zones = [
        "09:15-09:45 OPEN", "09:45-11:00 MORNING",
        "11:00-13:00 MIDDAY", "13:00-14:30 AFTERNOON",
        "14:30-15:30 POWER_HOUR"
    ]
    for pat_name in ["BEAR_OB", "BULL_OB", "JUDAS_BEAR", "JUDAS_BULL"]:
        print(f"\n  {pat_name}")
        for tz in time_zones:
            key = f"{pat_name}|{tz}"
            b   = by_time.get(key)
            if b and b.n_patterns >= 3:
                print_bucket(tz, b, indent="    ")

    # ── Summary ───────────────────────────────────────────────────────
    print("\n\n" + "═" * 75)
    print("  SUMMARY — EXPECTANCY RANKING (T+30m)")
    print("  Ranked by T+30m expectancy — the primary trading horizon")
    print("═" * 75)
    print(f"\n  {'Pattern':<25} {'N':>6}  {'Win%':>8}  "
          f"{'AvgP&L':>8}  {'Expect':>8}  {'Verdict':>12}")
    print(f"  {'-'*78}")

    summary_rows = []
    for pat_name in ["BEAR_OB", "BULL_OB", "JUDAS_BEAR", "JUDAS_BULL"]:
        b = by_pattern.get(pat_name)
        if not b:
            continue
        s = b.stats(30)
        if s is None:
            continue
        verdict = "TRADE" if s["expectancy"] > 5 else \
                  ("marginal" if s["expectancy"] > 0 else "avoid")
        summary_rows.append((pat_name, b, s, verdict))

    summary_rows.sort(key=lambda x: x[2]["expectancy"], reverse=True)
    for pat_name, b, s, verdict in summary_rows:
        print(f"  {pat_name:<25} {s['n']:>6}  {s['win_rate']:>7.1f}%  "
              f"{fmt_pct(s['avg']):>8}  {fmt_pct(s['expectancy']):>8}  "
              f"{verdict:>12}")

    print(f"\n  NOTE: Expectancy > 5% at T+30m = tradeable edge after costs")
    print(f"  NOTE: Entry at detection bar close price (no bid-ask spread modelled)")
    print(f"  NOTE: IV decomposition (theta vs delta) deferred to Experiment 7")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()


