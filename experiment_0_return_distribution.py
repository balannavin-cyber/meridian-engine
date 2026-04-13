#!/usr/bin/env python3
"""
experiment_0_return_distribution.py
MERDIAN Experiment 0 — Symmetric Return Distribution

Full year Apr 2025 – Mar 2026. Monthly breakdown.
Uses hist_spot_bars_1m only — no options, no coverage gaps.

For every 1-minute bar in market hours, computes:
  - T+15m, T+30m, T+60m spot return (% move from bar close)
  - Direction: UP or DOWN
  - Magnitude buckets: <0.1%, 0.1-0.3%, 0.3-0.5%, 0.5-1.0%, >1.0%

Outputs:
  1. Monthly return distribution — UP% and DOWN% by magnitude bucket
     Shows market character month by month — identifies bull/bear phases
     empirically from price data, not assumed date boundaries.

  2. Base rate table — for a random bar, what % of time does spot
     move UP vs DOWN at T+15m, T+30m, T+60m by month.
     This is the benchmark every signal must beat.

  3. Large move analysis — bars where |return| > 0.5% at T+30m.
     What time of day do large moves cluster?
     What month had the most large moves?

  4. Phase identification — groups months into phases based on
     directional bias: >55% DOWN = BEAR, >55% UP = BULL, else NEUTRAL.
     Validates or challenges the Experiment 12 phase boundaries.

Read-only. No options. Runtime: ~3 minutes.

Usage:
    python experiment_0_return_distribution.py
"""

import os
import bisect
import time
from datetime import datetime, timedelta, date, time as dtime
from collections import defaultdict
from itertools import groupby

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

PAGE_SIZE   = 1_000
SESSION_END = dtime(15, 30)
HORIZONS    = [15, 30, 60]

# Return magnitude buckets (absolute %)
BUCKETS = [
    ("flat   <0.1%",  0.0,  0.1),
    ("small  0.1-0.3%", 0.1, 0.3),
    ("medium 0.3-0.5%", 0.3, 0.5),
    ("large  0.5-1.0%", 0.5, 1.0),
    ("xlarge >1.0%",  1.0, 999),
]

MONTH_NAMES = {
    1:"Jan", 2:"Feb", 3:"Mar", 4:"Apr", 5:"May", 6:"Jun",
    7:"Jul", 8:"Aug", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec"
}

TIME_ZONES = [
    ("OPEN    09:15-10:00", dtime(9,15),  dtime(10, 0)),
    ("MORNING 10:00-11:30", dtime(10, 0), dtime(11,30)),
    ("MIDDAY  11:30-13:00", dtime(11,30), dtime(13, 0)),
    ("AFTNOON 13:00-14:30", dtime(13, 0), dtime(14,30)),
    ("POWER   14:30-15:30", dtime(14,30), dtime(15,30)),
]


# ── Utilities ─────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def pct(a, b):
    return 100.0 * (b - a) / a if a else 0.0

def in_session(ts, h):
    return (ts + timedelta(minutes=h)).time() <= SESSION_END

def month_key(d):
    return (d.year, d.month)

def month_label(ym):
    return f"{MONTH_NAMES[ym[1]]} {ym[0]}"

def magnitude_bucket(ret_pct):
    abs_ret = abs(ret_pct)
    for label, lo, hi in BUCKETS:
        if lo <= abs_ret < hi:
            return label
    return BUCKETS[-1][0]

def time_zone(ts):
    t = ts.time()
    for label, start, end in TIME_ZONES:
        if start <= t < end:
            return label
    return "OTHER"


# ── Data loading ──────────────────────────────────────────────────────

def fetch_spot_bars(sb, inst_id):
    all_rows, offset = [], 0
    while True:
        q = (sb.table("hist_spot_bars_1m")
             .select("bar_ts, trade_date, close")
             .eq("instrument_id", inst_id)
             .eq("is_pre_market", False)
             .order("bar_ts")
             .range(offset, offset+PAGE_SIZE-1))
        rows = None
        for attempt in range(4):
            try:
                rows = q.execute().data
                break
            except Exception:
                if attempt == 3: raise
                time.sleep(2**attempt)
        for r in rows:
            r["bar_ts"]     = datetime.fromisoformat(r["bar_ts"])
            r["trade_date"] = date.fromisoformat(r["trade_date"])
            r["close"]      = float(r["close"])
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset % 20_000 == 0:
            log(f"    {offset:,} bars...")
    return all_rows


def nearest_close(bars, target_ts, max_gap=3):
    tss = [b["bar_ts"] for b in bars]
    idx = bisect.bisect_left(tss, target_ts)
    best_p, best_g = None, timedelta(minutes=max_gap+1)
    for i in (idx-1, idx):
        if 0 <= i < len(bars):
            gap = abs(bars[i]["bar_ts"] - target_ts)
            if gap < best_g:
                best_g, best_p = gap, bars[i]["close"]
    return best_p if best_g <= timedelta(minutes=max_gap) else None


# ── Aggregation ───────────────────────────────────────────────────────

class MonthBucket:
    def __init__(self):
        self.total   = 0
        self.up      = {h: 0 for h in HORIZONS}
        self.down    = {h: 0 for h in HORIZONS}
        self.valid   = {h: 0 for h in HORIZONS}
        self.mag_up  = {h: defaultdict(int) for h in HORIZONS}
        self.mag_dn  = {h: defaultdict(int) for h in HORIZONS}
        self.large   = {h: 0 for h in HORIZONS}  # |ret| > 0.5%

    def add(self, h, ret):
        if ret is None:
            return
        self.valid[h]  += 1
        bkt = magnitude_bucket(ret)
        if ret >= 0:
            self.up[h]          += 1
            self.mag_up[h][bkt] += 1
        else:
            self.down[h]        += 1
            self.mag_dn[h][bkt] += 1
        if abs(ret) >= 0.5:
            self.large[h] += 1

    def up_pct(self, h):
        return 100*self.up[h]/self.valid[h] if self.valid[h] else None

    def down_pct(self, h):
        return 100*self.down[h]/self.valid[h] if self.valid[h] else None

    def large_pct(self, h):
        return 100*self.large[h]/self.valid[h] if self.valid[h] else None

    def phase(self, h=30):
        dp = self.down_pct(h)
        if dp is None: return "?"
        if dp >= 55:   return "BEAR"
        if dp <= 45:   return "BULL"
        return "NEUTRAL"


# ── Print helpers ─────────────────────────────────────────────────────

def direction_bar(up_pct, width=20):
    if up_pct is None:
        return " " * width
    up_w  = int(up_pct / 100 * width)
    dn_w  = width - up_w
    return "▲" * up_w + "▽" * dn_w


def fmt_pct(v, w=6):
    if v is None: return f"{'n/a':>{w}}"
    return f"{v:.1f}%".rjust(w)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    # Combined results across both symbols
    month_data   = defaultdict(MonthBucket)   # month_key → MonthBucket
    zone_data    = defaultdict(MonthBucket)   # (month_key, time_zone) → MonthBucket
    sym_month    = defaultdict(MonthBucket)   # (symbol, month_key) → MonthBucket
    overall      = defaultdict(MonthBucket)   # "ALL" → MonthBucket (single entry)

    all_bars_combined = []

    for symbol in ["NIFTY", "SENSEX"]:
        log(f"\nLoading {symbol} spot bars...")
        bars = fetch_spot_bars(sb, inst[symbol])
        log(f"  {len(bars):,} bars")

        log(f"  Scoring {symbol}...")
        for i, bar in enumerate(bars):
            ts = bar["bar_ts"]
            ep = bar["close"]
            td = bar["trade_date"]
            mk = month_key(td)
            tz = time_zone(ts)

            for h in HORIZONS:
                if not in_session(ts, h):
                    continue
                xp = nearest_close(bars, ts + timedelta(minutes=h))
                if xp is None:
                    continue
                ret = pct(ep, xp)
                month_data[mk].add(h, ret)
                zone_data[(mk, tz)].add(h, ret)
                sym_month[(symbol, mk)].add(h, ret)
                overall["ALL"].add(h, ret)

            month_data[mk].total += 1

        log(f"  {symbol} complete.")

    # ── Output ────────────────────────────────────────────────────────
    months = sorted(month_data.keys())

    print("\n" + "=" * 110)
    print("  MERDIAN EXPERIMENT 0 — SYMMETRIC RETURN DISTRIBUTION")
    print("  Period: Apr 2025 – Mar 2026  |  NIFTY + SENSEX combined")
    print("  Base rate: what % of 1-min bars resulted in UP vs DOWN spot move")
    print("  at T+15m, T+30m, T+60m — the benchmark every signal must beat")
    print("=" * 110)

    # ── Section 1: Monthly base rate ─────────────────────────────────
    print(f"\n{'='*110}")
    print("  SECTION 1 — MONTHLY BASE RATE (T+30m primary)")
    print("  ▲=UP bars  ▽=DOWN bars  |  Phase determined by T+30m down%")
    print("  >55% DOWN = BEAR phase  |  <45% DOWN = BULL phase  |  else NEUTRAL")
    print(f"{'='*110}")
    print(f"  {'Month':<10} {'N':>6}  {'Direction T+30m':<22}  "
          f"{'UP%':>6}  {'DN%':>6}  {'Large>0.5%':>11}  Phase")
    print(f"  {'-'*85}")

    for mk in months:
        b    = month_data[mk]
        up   = b.up_pct(30)
        dn   = b.down_pct(30)
        lrg  = b.large_pct(30)
        bar  = direction_bar(up)
        ph   = b.phase(30)
        flag = " ◄" if ph == "BEAR" else (" ▲" if ph == "BULL" else "  ")
        print(f"  {month_label(mk):<10} {b.valid[30]:>6}  {bar}  "
              f"{fmt_pct(up):>6}  {fmt_pct(dn):>6}  {fmt_pct(lrg):>11}  {ph}{flag}")

    # ── Section 2: T+15 / T+30 / T+60 comparison ─────────────────────
    print(f"\n{'='*110}")
    print("  SECTION 2 — HORIZON COMPARISON: Does bearish bias deepen or fade over time?")
    print("  A market that is DOWN at T+15m and UP at T+60m = mean-reverting")
    print("  A market that is DOWN at T+15m and DOWN at T+60m = trending")
    print(f"{'='*110}")
    print(f"  {'Month':<10} {'Phase':>7}  "
          f"{'T+15 UP%':>9}  {'T+30 UP%':>9}  {'T+60 UP%':>9}  Character")
    print(f"  {'-'*75}")

    for mk in months:
        b  = month_data[mk]
        u15 = b.up_pct(15)
        u30 = b.up_pct(30)
        u60 = b.up_pct(60)
        ph  = b.phase(30)
        if u15 and u30 and u60:
            if u60 > u30 > u15:
                char = "REVERTING (down fades)"
            elif u60 < u30 < u15:
                char = "TRENDING  (up fades)"
            elif u30 < u15 and u60 > u30:
                char = "CHOPPY    (mixed)"
            else:
                char = "STABLE"
        else:
            char = "n/a"
        print(f"  {month_label(mk):<10} {ph:>7}  "
              f"{fmt_pct(u15):>9}  {fmt_pct(u30):>9}  {fmt_pct(u60):>9}  {char}")

    # ── Section 3: NIFTY vs SENSEX comparison ────────────────────────
    print(f"\n{'='*110}")
    print("  SECTION 3 — NIFTY vs SENSEX: Do they diverge in any phase?")
    print(f"{'='*110}")
    print(f"  {'Month':<10}  {'NIFTY DN%':>10}  {'SENSEX DN%':>11}  {'Diff':>6}  Note")
    print(f"  {'-'*60}")

    for mk in months:
        bn = sym_month[("NIFTY",  mk)]
        bs = sym_month[("SENSEX", mk)]
        dn_n = bn.down_pct(30)
        dn_s = bs.down_pct(30)
        if dn_n and dn_s:
            diff = dn_s - dn_n
            note = "SENSEX more bearish" if diff > 3 else \
                   "NIFTY more bearish"  if diff < -3 else \
                   "aligned"
        else:
            diff, note = None, "n/a"
        print(f"  {month_label(mk):<10}  {fmt_pct(dn_n):>10}  {fmt_pct(dn_s):>11}  "
              f"{fmt_pct(diff):>6}  {note}")

    # ── Section 4: Large move time-of-day ────────────────────────────
    print(f"\n{'='*110}")
    print("  SECTION 4 — LARGE MOVES (>0.5% at T+30m) BY TIME OF DAY")
    print("  When do large directional moves originate?")
    print(f"{'='*110}")

    tz_agg = defaultdict(lambda: {"total":0, "up":0, "dn":0, "large":0})
    for (mk, tz), b in zone_data.items():
        tz_agg[tz]["total"] += b.valid[30]
        tz_agg[tz]["up"]    += b.up[30]
        tz_agg[tz]["dn"]    += b.down[30]
        tz_agg[tz]["large"] += b.large[30]

    print(f"  {'Time Zone':<28} {'N':>7}  {'UP%':>6}  {'DN%':>6}  "
          f"{'Large>0.5%':>11}  {'Large UP%':>10}  {'Large DN%':>10}")
    print(f"  {'-'*90}")

    for tz_label, _ , _ in TIME_ZONES:
        a = tz_agg.get(tz_label, {})
        if not a or a["total"] == 0:
            continue
        tot   = a["total"]
        up    = 100*a["up"]/tot   if tot else None
        dn    = 100*a["dn"]/tot   if tot else None
        lrg   = 100*a["large"]/tot if tot else None
        print(f"  {tz_label:<28} {tot:>7}  "
              f"{fmt_pct(up):>6}  {fmt_pct(dn):>6}  {fmt_pct(lrg):>11}  "
              f"{'':>10}  {'':>10}")

    # ── Section 5: Phase summary ──────────────────────────────────────
    print(f"\n{'='*110}")
    print("  SECTION 5 — EMPIRICAL PHASE IDENTIFICATION")
    print("  Based on T+30m directional bias. Validates Experiment 12 boundaries.")
    print(f"{'='*110}")

    current_phase = None
    phase_start   = None

    for mk in months:
        ph = month_data[mk].phase(30)
        if ph != current_phase:
            if current_phase:
                print(f"  {current_phase:<8} {month_label(phase_start)} → "
                      f"{month_label(months[months.index(mk)-1])}")
            current_phase = ph
            phase_start   = mk
    if current_phase:
        print(f"  {current_phase:<8} {month_label(phase_start)} → "
              f"{month_label(months[-1])}")

    # ── Section 6: Overall base rate ─────────────────────────────────
    print(f"\n{'='*110}")
    print("  SECTION 6 — FULL YEAR BASE RATE (both symbols, all months)")
    print("  This is the benchmark. Every signal must show expectancy above this.")
    print(f"{'='*110}")

    ob = overall["ALL"]
    print(f"\n  Full year ({ob.valid[30]:,} bars scored at T+30m):")
    print(f"  UP  at T+15m: {fmt_pct(ob.up_pct(15))}  "
          f"T+30m: {fmt_pct(ob.up_pct(30))}  "
          f"T+60m: {fmt_pct(ob.up_pct(60))}")
    print(f"  DOWN at T+15m: {fmt_pct(ob.down_pct(15))}  "
          f"T+30m: {fmt_pct(ob.down_pct(30))}  "
          f"T+60m: {fmt_pct(ob.down_pct(60))}")
    print(f"\n  Large moves >0.5%:")
    print(f"  T+15m: {fmt_pct(ob.large_pct(15))}  "
          f"T+30m: {fmt_pct(ob.large_pct(30))}  "
          f"T+60m: {fmt_pct(ob.large_pct(60))}")

    print(f"\n  MAGNITUDE DISTRIBUTION (T+30m, all bars):")
    print(f"  {'Bucket':<25} {'UP bars':>8}  {'DOWN bars':>10}  {'Total':>8}")
    print(f"  {'-'*55}")
    all_mag_up = defaultdict(int)
    all_mag_dn = defaultdict(int)
    for b in month_data.values():
        for bkt, _, _ in BUCKETS:
            all_mag_up[bkt] += b.mag_up[30][bkt]
            all_mag_dn[bkt] += b.mag_dn[30][bkt]
    for bkt, _, _ in BUCKETS:
        u = all_mag_up[bkt]
        d = all_mag_dn[bkt]
        print(f"  {bkt:<25} {u:>8,}  {d:>10,}  {u+d:>8,}")

    print(f"\n{'='*110}")
    print("  INTERPRETATION GUIDE")
    print("  Base rate ~50% UP / 50% DOWN = random walk (no directional bias)")
    print("  Sustained >55% DOWN in a month = confirmed BEAR phase")
    print("  Sustained >55% UP  in a month = confirmed BULL phase")
    print("  Large move% = % of bars that produced >0.5% move at T+30m")
    print("    Higher large move% = higher volatility, better options environment")
    print("  Signal edge = signal UP% or DOWN% meaningfully above base rate")
    print(f"{'='*110}\n")


if __name__ == "__main__":
    main()
