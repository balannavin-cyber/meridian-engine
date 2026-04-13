#!/usr/bin/env python3
"""
experiment_9_smdm.py
MERDIAN Experiment 9 — SMDM: Expiry Day Liquidity Sweeps

HYPOTHESIS:
  On expiry day (NIFTY=Thursday, SENSEX=Tuesday), institutions sweep
  liquidity above the prior session high or below the prior session low
  in the opening 30-45 minutes, then reverse hard into the session.
  This is the "Smart Money Delivery Model" — the opening trap.

  If confirmed structurally:
    - Opening sweep UP then reversal → SHORT opportunity (buy PE)
    - Opening sweep DOWN then reversal → LONG opportunity (buy CE)
    - Trades entered at the reversal point with defined risk

WHAT THIS EXPERIMENT MEASURES:
  For every expiry day in the dataset:

  1. SWEEP DETECTION:
     Prior session high = max(high) of previous trading day
     Prior session low  = min(low)  of previous trading day
     Sweep UP:   price trades above prior high in bars 1-30 of session
     Sweep DOWN: price trades below prior low  in bars 1-30 of session

  2. REVERSAL MEASUREMENT:
     After the sweep, does price reverse?
     At the sweep bar: record direction + extent of sweep
     At T+15m, T+30m, T+60m from sweep: measure spot return
     Reversal confirmed if: direction opposite to sweep, |return| > 0.15%

  3. P&L SIMULATION (spot-only, no options needed):
     Entry: close of first reversal bar after sweep
     Direction: opposite to sweep (swept high → short, swept low → long)
     Exit: T+30m, T+60m, end of session
     P&L: % return from entry to exit

  4. COMPARISON:
     Expiry day sweeps vs non-expiry day sweeps (same detection)
     Does the sweep reversal work better on expiry day?
     Is it structurally different from any random day?

EXPIRY DAYS:
  NIFTY: every Thursday (weekly expiry)
  SENSEX: every Tuesday (weekly expiry)

DATA:
  hist_spot_bars_1m only — no options needed.
  hist_spot_bars_1m for prior session high/low.

Read-only. Spot only. Runtime: ~5 minutes.

Usage:
    python experiment_9_smdm.py
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

# ── Config ────────────────────────────────────────────────────────────
EXPIRY_WD     = {"NIFTY": 3, "SENSEX": 1}   # Thu=3, Tue=1
SWEEP_WINDOW  = 45   # minutes from open to check for sweep
SWEEP_MIN_PCT = 0.10 # minimum % beyond prior high/low to count as sweep
REV_MIN_PCT   = 0.15 # minimum % reversal to count as confirmed reversal
HORIZONS      = [15, 30, 60, 120]  # minutes from reversal entry

MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
               7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}


# ── Utilities ─────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def pct(a, b):
    return 100.0 * (b - a) / a if a else 0.0

def is_expiry(td, symbol):
    return td.weekday() == EXPIRY_WD[symbol]

def in_session(ts, h):
    return (ts + timedelta(minutes=h)).time() <= SESSION_END


# ── Data loading ──────────────────────────────────────────────────────

def fetch_spot_bars(sb, inst_id):
    all_rows, offset = [], 0
    while True:
        q = (sb.table("hist_spot_bars_1m")
             .select("bar_ts, trade_date, open, high, low, close")
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
            for k in ("open","high","low","close"):
                r[k] = float(r[k])
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset % 20_000 == 0:
            log(f"    {offset:,} bars...")
    return all_rows


def sessions_from_bars(bars):
    result = {}
    for k, g in groupby(bars, key=lambda b: b["trade_date"]):
        result[k] = list(g)
    return result


def get_price_at(bars, target_ts, max_gap=3):
    if not bars: return None
    tss = [b["bar_ts"] for b in bars]
    idx = bisect.bisect_left(tss, target_ts)
    best_p, best_g = None, timedelta(minutes=max_gap+1)
    for i in (idx-1, idx):
        if 0 <= i < len(bars):
            gap = abs(bars[i]["bar_ts"] - target_ts)
            if gap < best_g:
                best_g, best_p = gap, bars[i]["close"]
    return best_p if best_g <= timedelta(minutes=max_gap) else None


# ── Sweep detection ───────────────────────────────────────────────────

def detect_sweep(bars, prior_high, prior_low, sweep_window=SWEEP_WINDOW,
                 min_pct=SWEEP_MIN_PCT):
    """
    Scan first sweep_window bars for a sweep of prior high or low.
    Returns list of sweep events: {bar, direction, extent_pct, sweep_level}
    Only returns first occurrence per direction.
    """
    sweeps = []
    found_up = found_dn = False
    open_ts  = bars[0]["bar_ts"]
    cutoff   = open_ts + timedelta(minutes=sweep_window)

    for bar in bars:
        if bar["bar_ts"] > cutoff:
            break
        # Sweep UP: bar high exceeds prior high by min_pct
        if not found_up and prior_high:
            extent = pct(prior_high, bar["high"])
            if extent >= min_pct:
                found_up = True
                sweeps.append({
                    "bar":         bar,
                    "direction":   "UP",
                    "sweep_level": prior_high,
                    "extent_pct":  extent,
                })
        # Sweep DOWN: bar low below prior low by min_pct
        if not found_dn and prior_low:
            extent = pct(prior_low, bar["low"]) * -1  # positive = below
            if extent >= min_pct:
                found_dn = True
                sweeps.append({
                    "bar":         bar,
                    "direction":   "DN",
                    "sweep_level": prior_low,
                    "extent_pct":  extent,
                })
    return sweeps


def find_reversal(bars, sweep_bar, sweep_direction, min_pct=REV_MIN_PCT):
    """
    After a sweep bar, scan subsequent bars for the first reversal.
    UP sweep → look for price dropping below sweep bar close by min_pct
    DN sweep → look for price rising above sweep bar close by min_pct
    Returns (reversal_bar, reversal_pct) or (None, None).
    """
    ref_price = sweep_bar["bar"]["close"]
    ref_ts    = sweep_bar["bar"]["bar_ts"]
    tss       = [b["bar_ts"] for b in bars]
    idx       = bisect.bisect_right(tss, ref_ts)

    for i in range(idx, len(bars)):
        bar  = bars[i]
        move = pct(ref_price, bar["close"])
        if sweep_direction == "UP" and move <= -min_pct:
            return bar, abs(move)
        if sweep_direction == "DN" and move >= min_pct:
            return bar, abs(move)
    return None, None


# ── P&L bucket ───────────────────────────────────────────────────────

class SweepBucket:
    def __init__(self):
        self.n_sessions   = 0
        self.n_sweeps     = 0
        self.n_reversals  = 0
        self.sweep_extents = []   # how far beyond prior high/low
        self.reversal_pcts = []   # how far price reversed
        self.pnl          = {h: [] for h in HORIZONS}

    def add_session(self): self.n_sessions += 1

    def add_sweep(self, extent):
        self.n_sweeps += 1
        self.sweep_extents.append(extent)

    def add_reversal(self, rev_pct, pnl_dict):
        self.n_reversals += 1
        self.reversal_pcts.append(rev_pct)
        for h in HORIZONS:
            if pnl_dict.get(h) is not None:
                self.pnl[h].append(pnl_dict[h])

    def sweep_rate(self):
        return 100*self.n_sweeps/self.n_sessions if self.n_sessions else None

    def reversal_rate(self):
        return 100*self.n_reversals/self.n_sweeps if self.n_sweeps else None

    def stats(self, h):
        v = self.pnl[h]
        if not v: return None
        wins = [x for x in v if x > 0]
        loss = [x for x in v if x <= 0]
        wr   = len(wins)/len(v)
        aw   = sum(wins)/len(wins) if wins else 0.0
        al   = sum(loss)/len(loss) if loss else 0.0
        return dict(n=len(v), wr=wr*100, avg=sum(v)/len(v),
                    exp=wr*aw+(1-wr)*al)

    def avg_extent(self):
        return sum(self.sweep_extents)/len(self.sweep_extents) \
               if self.sweep_extents else None

    def avg_reversal(self):
        return sum(self.reversal_pcts)/len(self.reversal_pcts) \
               if self.reversal_pcts else None


def fmt(v, w=8):
    if v is None: return f"{'n/a':>{w}}"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%".rjust(w)

def fmtpct(v, w=7):
    if v is None: return f"{'n/a':>{w}}"
    return f"{v:.1f}%".rjust(w)


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    print("\n" + "=" * 110)
    print("  MERDIAN EXPERIMENT 9 — SMDM: EXPIRY DAY LIQUIDITY SWEEPS")
    print("  Hypothesis: Expiry day opening sweeps of prior high/low")
    print("  are structurally different from non-expiry days and provide")
    print("  a high-probability reversal trade opportunity.")
    print("=" * 110)

    for symbol in ["NIFTY", "SENSEX"]:
        log(f"\n── {symbol} ─────────────────────────────────────────────")

        log("  Loading spot bars...")
        bars = fetch_spot_bars(sb, inst[symbol])
        log(f"  {len(bars):,} bars")

        spot_sessions = sessions_from_bars(bars)
        dates         = sorted(spot_sessions.keys())

        # Buckets
        expiry_up  = SweepBucket()  # expiry day, sweep UP
        expiry_dn  = SweepBucket()  # expiry day, sweep DN
        normal_up  = SweepBucket()  # non-expiry, sweep UP
        normal_dn  = SweepBucket()  # non-expiry, sweep DN

        # Monthly breakdown
        monthly_expiry = defaultdict(SweepBucket)
        monthly_normal = defaultdict(SweepBucket)

        # Detailed sweep log
        sweep_log = []

        for i, d in enumerate(dates):
            if i == 0:
                continue   # need prior session

            session = spot_sessions[d]
            if len(session) < 30:
                continue

            # Prior session stats
            prior_d       = dates[i-1]
            prior_session = spot_sessions.get(prior_d, [])
            if not prior_session:
                continue

            prior_high = max(b["high"] for b in prior_session)
            prior_low  = min(b["low"]  for b in prior_session)

            is_exp  = is_expiry(d, symbol)
            mk      = (d.year, d.month)
            bkt_up  = expiry_up  if is_exp else normal_up
            bkt_dn  = expiry_dn  if is_exp else normal_dn
            mon_bkt = monthly_expiry[mk] if is_exp else monthly_normal[mk]

            bkt_up.add_session()
            bkt_dn.add_session()
            mon_bkt.add_session()

            # Detect sweeps
            sweeps = detect_sweep(session, prior_high, prior_low)

            for sweep in sweeps:
                direction = sweep["direction"]
                extent    = sweep["extent_pct"]

                if direction == "UP":
                    bkt_up.add_sweep(extent)
                else:
                    bkt_dn.add_sweep(extent)
                mon_bkt.add_sweep(extent)

                # Find reversal
                rev_bar, rev_pct = find_reversal(session, sweep, direction)
                if rev_bar is None:
                    sweep_log.append({
                        "date": d, "symbol": symbol,
                        "direction": direction, "expiry": is_exp,
                        "extent_pct": extent, "reversed": False,
                        "rev_pct": None, "pnl_30": None,
                    })
                    continue

                # P&L from reversal entry
                # Direction of trade: UP sweep → short (sell rally)
                #                     DN sweep → long (buy dip)
                trade_dir = -1 if direction == "UP" else +1
                entry_price = rev_bar["close"]
                entry_ts    = rev_bar["bar_ts"]

                pnl_dict = {}
                for h in HORIZONS:
                    if not in_session(entry_ts, h):
                        pnl_dict[h] = None
                        continue
                    exit_price = get_price_at(
                        session, entry_ts + timedelta(minutes=h)
                    )
                    if exit_price:
                        pnl_dict[h] = pct(entry_price, exit_price) * trade_dir
                    else:
                        pnl_dict[h] = None

                if direction == "UP":
                    bkt_up.add_reversal(rev_pct, pnl_dict)
                else:
                    bkt_dn.add_reversal(rev_pct, pnl_dict)
                mon_bkt.add_reversal(rev_pct, pnl_dict)

                sweep_log.append({
                    "date": d, "symbol": symbol,
                    "direction": direction, "expiry": is_exp,
                    "extent_pct": extent, "reversed": True,
                    "rev_pct": rev_pct,
                    "pnl_30": pnl_dict.get(30),
                })

        # ── Output ────────────────────────────────────────────────────

        print(f"\n{'#'*110}")
        print(f"  {symbol}")
        print(f"{'#'*110}")

        # Section 1: Sweep rates
        print(f"\n  {'='*105}")
        print(f"  SECTION 1 — SWEEP RATES: How often does expiry day sweep prior H/L?")
        print(f"  {'='*105}")
        print(f"  {'Category':<25} {'Sessions':>9}  {'Sweeps':>7}  "
              f"{'Sweep%':>8}  {'Reversals':>10}  {'Rev%':>6}  "
              f"{'Avg Extent':>11}  {'Avg Rev':>9}")
        print(f"  {'-'*95}")

        for label, bkt in [
            ("Expiry Day — Sweep UP",  expiry_up),
            ("Expiry Day — Sweep DN",  expiry_dn),
            ("Normal Day — Sweep UP",  normal_up),
            ("Normal Day — Sweep DN",  normal_dn),
        ]:
            print(f"  {label:<25} {bkt.n_sessions:>9}  {bkt.n_sweeps:>7}  "
                  f"{fmtpct(bkt.sweep_rate()):>8}  {bkt.n_reversals:>10}  "
                  f"{fmtpct(bkt.reversal_rate()):>6}  "
                  f"{fmtpct(bkt.avg_extent()):>11}  "
                  f"{fmtpct(bkt.avg_reversal()):>9}")

        # Section 2: P&L comparison
        print(f"\n  {'='*105}")
        print(f"  SECTION 2 — P&L AFTER REVERSAL ENTRY")
        print(f"  Trade entered at reversal bar. Direction: opposite to sweep.")
        print(f"  Expiry UP sweep → short (buy PE). DN sweep → long (buy CE).")
        print(f"  P&L = spot % return in trade direction.")
        print(f"  {'='*105}")
        print(f"  {'Category':<25} {'N':>5}  "
              f"{'T+15 Exp':>10}  {'T+30 Exp':>10}  "
              f"{'T+60 Exp':>10}  {'T+120 Exp':>11}  {'WR T+30':>9}")
        print(f"  {'-'*95}")

        for label, bkt in [
            ("Expiry — Sweep UP → Short", expiry_up),
            ("Expiry — Sweep DN → Long",  expiry_dn),
            ("Normal — Sweep UP → Short", normal_up),
            ("Normal — Sweep DN → Long",  normal_dn),
        ]:
            s30 = bkt.stats(30)
            print(f"  {label:<25} "
                  f"{bkt.n_reversals:>5}  "
                  f"{fmt(bkt.stats(15)['exp'] if bkt.stats(15) else None):>10}  "
                  f"{fmt(s30['exp'] if s30 else None):>10}  "
                  f"{fmt(bkt.stats(60)['exp'] if bkt.stats(60) else None):>10}  "
                  f"{fmt(bkt.stats(120)['exp'] if bkt.stats(120) else None):>11}  "
                  f"{(str(round(s30['wr']))+'%' if s30 else 'n/a'):>9}")

        # Section 3: Monthly breakdown
        print(f"\n  {'='*105}")
        print(f"  SECTION 3 — MONTHLY BREAKDOWN (Expiry days only, both directions)")
        print(f"  {'='*105}")
        print(f"  {'Month':<12} {'Sessions':>9}  {'Sweeps':>7}  {'Sweep%':>8}  "
              f"{'Reversals':>10}  {'Rev%':>6}  {'T+30 Exp':>10}  {'WR':>6}")
        print(f"  {'-'*80}")

        for mk in sorted(monthly_expiry.keys()):
            b   = monthly_expiry[mk]
            s30 = b.stats(30)
            mn  = f"{MONTH_NAMES[mk[1]]} {mk[0]}"
            print(f"  {mn:<12} {b.n_sessions:>9}  {b.n_sweeps:>7}  "
                  f"{fmtpct(b.sweep_rate()):>8}  {b.n_reversals:>10}  "
                  f"{fmtpct(b.reversal_rate()):>6}  "
                  f"{fmt(s30['exp'] if s30 else None):>10}  "
                  f"{(str(round(s30['wr']))+'%' if s30 else 'n/a'):>6}")

        # Section 4: Detailed sweep log — top 20 by P&L
        print(f"\n  {'='*105}")
        print(f"  SECTION 4 — TOP 10 EXPIRY DAY SWEEP TRADES (by T+30m P&L)")
        print(f"  {'='*105}")
        print(f"  {'Date':<12} {'Dir':<4} {'Extent':>8}  {'Rev%':>6}  "
              f"{'P&L T+30':>10}  {'Expiry?':>8}")
        print(f"  {'-'*60}")

        expiry_sweeps = [s for s in sweep_log
                         if s["expiry"] and s["reversed"] and s["pnl_30"] is not None]
        expiry_sweeps.sort(key=lambda x: x["pnl_30"], reverse=True)

        for s in expiry_sweeps[:10]:
            print(f"  {str(s['date']):<12} {s['direction']:<4} "
                  f"{fmtpct(s['extent_pct']):>8}  "
                  f"{fmtpct(s['rev_pct']):>6}  "
                  f"{fmt(s['pnl_30']):>10}  "
                  f"{'YES' if s['expiry'] else 'no':>8}")

        # Section 5: Verdict
        print(f"\n  {'='*105}")
        print(f"  SECTION 5 — SMDM VERDICT FOR {symbol}")
        print(f"  {'='*105}")

        # Compare expiry vs normal sweep reversal P&L
        exp_up_30 = expiry_up.stats(30)
        exp_dn_30 = expiry_dn.stats(30)
        nor_up_30 = normal_up.stats(30)
        nor_dn_30 = normal_dn.stats(30)

        expiry_exp = None
        normal_exp = None
        if exp_up_30 and exp_dn_30:
            n_eu = exp_up_30["n"]
            n_ed = exp_dn_30["n"]
            expiry_exp = (exp_up_30["exp"]*n_eu + exp_dn_30["exp"]*n_ed) / (n_eu+n_ed) \
                         if (n_eu+n_ed) > 0 else None
        if nor_up_30 and nor_dn_30:
            n_nu = nor_up_30["n"]
            n_nd = nor_dn_30["n"]
            normal_exp = (nor_up_30["exp"]*n_nu + nor_dn_30["exp"]*n_nd) / (n_nu+n_nd) \
                         if (n_nu+n_nd) > 0 else None

        print(f"\n  Expiry day sweep→reversal T+30m combined expectancy: "
              f"{fmt(expiry_exp) if expiry_exp else 'n/a'}")
        print(f"  Normal  day sweep→reversal T+30m combined expectancy: "
              f"{fmt(normal_exp) if normal_exp else 'n/a'}")

        if expiry_exp and normal_exp:
            if expiry_exp > normal_exp + 2:
                verdict = ("CONFIRMED — Expiry day sweeps have HIGHER expectancy "
                           "than normal days. SMDM is structurally valid.")
            elif expiry_exp < normal_exp - 2:
                verdict = ("NOT CONFIRMED — Expiry day sweeps are WEAKER than "
                           "normal days. SMDM hypothesis rejected.")
            else:
                verdict = ("NEUTRAL — No meaningful difference between expiry "
                           "and normal day sweep reversals.")
        else:
            verdict = "INSUFFICIENT DATA — cannot conclude"

        print(f"\n  VERDICT: {verdict}")
        print()

    print("=" * 110)
    print("  SMDM INTERPRETATION GUIDE")
    print("  If CONFIRMED:")
    print("    - Add EXPIRY_SWEEP_UP (buy PE) and EXPIRY_SWEEP_DN (buy CE) as signal patterns")
    print("    - Entry: close of first reversal bar after sweep (bar price drops/rises REV_MIN_PCT)")
    print("    - These trades only fire on NIFTY Thursday / SENSEX Tuesday")
    print("    - Combine with ICT OB/FVG at the reversal point for highest conviction")
    print("  If NOT CONFIRMED:")
    print("    - Expiry day is not structurally different — no special rules needed")
    print("    - Existing ICT patterns already capture the edge on expiry day")
    print("=" * 110)
    print()


if __name__ == "__main__":
    main()
