#!/usr/bin/env python3
"""
experiment_10c_mtf_pnl.py
MERDIAN Experiment 10c — ICT Patterns: MTF Context + Actual Options P&L

Combines Experiment 10b (MTF context tagging) with Experiment 2 (options P&L).

For every ICT pattern detected:
  1. Tags with MTF context: HIGH (weekly zone) / MEDIUM (daily zone) / LOW (none)
  2. Tags with DTE bucket: 0 / 1 / 2-3 / 4+
  3. Fetches actual ATM option price from hist_option_bars_1m
  4. Computes real P&L at T+15m, T+30m, T+60m

Key question:
  Does being inside a weekly institutional zone (HIGH context) produce
  materially better OPTION P&L — not just better spot direction accuracy?
  Does the intersection of HIGH context + DTE=0 create the highest-value trades?

Pattern → option mapping:
  BEAR_* → Buy ATM PE
  BULL_* → Buy ATM CE

ATM convention: NIFTY round(spot/50)×50 | SENSEX round(spot/100)×100
Expiry: nearest weekly (NIFTY=Thursday | SENSEX=Tuesday)

Read-only. Runtime: ~20-30 minutes.

Usage:
    python experiment_10c_mtf_pnl.py
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

# ── Pattern → option direction ────────────────────────────────────────
OPT_TYPE = {}
for p in ("BEAR_OB","BEAR_FVG","BEAR_SWEEP_PDH","BEAR_SWEEP_EQH",
          "BOS_BEAR","MSS_BEAR","JUDAS_BEAR","BEAR_OTE","BEAR_BREAKER"):
    OPT_TYPE[p] = "PE"
for p in ("BULL_OB","BULL_FVG","BULL_SWEEP_PDL","BULL_SWEEP_EQL",
          "BOS_BULL","MSS_BULL","JUDAS_BULL","BULL_OTE","BULL_BREAKER"):
    OPT_TYPE[p] = "CE"

# ── Thresholds ────────────────────────────────────────────────────────
STRIKE_STEP      = {"NIFTY": 50, "SENSEX": 100}

SWING_LB         = 5
OB_MIN_MOVE_PCT  = 0.40
FVG_MIN_PCT      = 0.10
LIQ_SWEEP_PCT    = 0.15
EQUAL_HL_TOL     = 0.15
JUDAS_MIN_PCT    = 0.25
OTE_FIB_LO       = 0.618
OTE_FIB_HI       = 0.786
MIN_SWING_PCT    = 0.50

DAILY_OB_MOVE    = 1.00
DAILY_FVG_PCT    = 0.30
WEEKLY_OB_MOVE   = 2.00
WEEKLY_FVG_PCT   = 0.50
DAILY_LOOKBACK   = 10
WEEKLY_LOOKBACK  = 4

MIN_OPTION_PRICE = 5.0
ATM_RADIUS       = 3
MAX_GAP_MIN      = 3


# ── Logging ───────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── Geometry helpers ──────────────────────────────────────────────────

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

def fetch_spot_bars(sb, inst_id):
    all_rows, offset = [], 0
    while True:
        rows = (
            sb.table("hist_spot_bars_1m")
            .select("bar_ts, trade_date, open, high, low, close")
            .eq("instrument_id", inst_id)
            .eq("is_pre_market", False)
            .order("bar_ts")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute().data
        )
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
            .range(offset, offset + PAGE_SIZE - 1)
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
    candidates = [strike + i * step for i in range(-ATM_RADIUS, ATM_RADIUS+1)]
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


# ── HTF bar construction ──────────────────────────────────────────────

def build_daily_bars(sessions):
    daily = []
    for d, bars in sorted(sessions.items()):
        daily.append({
            "trade_date": d,
            "open":  bars[0]["open"],
            "high":  max(b["high"] for b in bars),
            "low":   min(b["low"]  for b in bars),
            "close": bars[-1]["close"],
        })
    return daily


def build_weekly_bars(daily_bars):
    weeks = defaultdict(list)
    for d in daily_bars:
        weeks[d["trade_date"].isocalendar()[:2]].append(d)
    weekly = []
    for wk, days in sorted(weeks.items()):
        days.sort(key=lambda x: x["trade_date"])
        weekly.append({
            "week": wk,
            "first_date": days[0]["trade_date"],
            "open":  days[0]["open"],
            "high":  max(d["high"] for d in days),
            "low":   min(d["low"]  for d in days),
            "close": days[-1]["close"],
        })
    return weekly


def htf_obs(bars, min_move):
    zones, seen = [], set()
    n = len(bars)
    for i in range(n - 3):
        future = bars[min(i+3, n-1)]["close"]
        move   = pct(bars[i]["close"], future)
        if move <= -min_move:
            for j in range(i, max(i-4,-1), -1):
                if bars[j]["close"] > bars[j]["open"] and j not in seen:
                    seen.add(j)
                    zones.append({"type":"BEAR_OB","zone_high":bars[j]["high"],
                                  "zone_low":bars[j]["low"],"formed_idx":j})
                    break
        elif move >= min_move:
            for j in range(i, max(i-4,-1), -1):
                if bars[j]["close"] < bars[j]["open"] and j not in seen:
                    seen.add(j)
                    zones.append({"type":"BULL_OB","zone_high":bars[j]["high"],
                                  "zone_low":bars[j]["low"],"formed_idx":j})
                    break
    return zones


def htf_fvgs(bars, min_gap_pct):
    zones = []
    min_g = min_gap_pct / 100.0
    for i in range(1, len(bars)-1):
        p, c, n = bars[i-1], bars[i], bars[i+1]
        ref = c["close"]
        if p["low"] > n["high"] and (p["low"]-n["high"])/ref >= min_g:
            zones.append({"type":"BEAR_FVG","zone_high":p["low"],
                          "zone_low":n["high"],"formed_idx":i})
        if p["high"] < n["low"] and (n["low"]-p["high"])/ref >= min_g:
            zones.append({"type":"BULL_FVG","zone_high":n["low"],
                          "zone_low":p["high"],"formed_idx":i})
    return zones


def build_zone_indexes(daily_bars, weekly_bars):
    d_zones = htf_obs(daily_bars, DAILY_OB_MOVE) + htf_fvgs(daily_bars, DAILY_FVG_PCT)
    w_zones = htf_obs(weekly_bars, WEEKLY_OB_MOVE) + htf_fvgs(weekly_bars, WEEKLY_FVG_PCT)

    daily_idx  = {}
    weekly_idx = {}

    for i, d in enumerate(daily_bars):
        td = d["trade_date"]
        daily_idx[td] = [z for z in d_zones
                         if max(0, i-DAILY_LOOKBACK) <= z["formed_idx"] < i]
        wk = td.isocalendar()[:2]
        wi = next((j for j,w in enumerate(weekly_bars) if w["week"]==wk), None)
        if wi is not None:
            weekly_idx[td] = [z for z in w_zones
                               if max(0, wi-WEEKLY_LOOKBACK) <= z["formed_idx"] < wi]
        else:
            weekly_idx[td] = []

    return daily_idx, weekly_idx


def get_mtf_context(price, td, daily_idx, weekly_idx):
    for z in weekly_idx.get(td, []):
        if z["zone_low"] <= price <= z["zone_high"]:
            return "HIGH"
    for z in daily_idx.get(td, []):
        if z["zone_low"] <= price <= z["zone_high"]:
            return "MEDIUM"
    return "LOW"


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
        if p["low"] > n["high"] and (p["low"]-n["high"])/ref >= min_g:
            out.append(dict(bar_idx=i,bar=c,pattern="BEAR_FVG"))
        if p["high"] < n["low"] and (n["low"]-p["high"])/ref >= min_g:
            out.append(dict(bar_idx=i,bar=c,pattern="BULL_FVG"))
    return out


def detect_sweeps(bars, pdh=None, pdl=None):
    out, n = [], len(bars)
    tol, spk = EQUAL_HL_TOL/100.0, LIQ_SWEEP_PCT
    for i in range(1, n):
        c = bars[i]
        if pdh and c["high"]>pdh and c["close"]<pdh and pct(pdh,c["high"])>=spk:
            out.append(dict(bar_idx=i,bar=c,pattern="BEAR_SWEEP_PDH"))
        if pdl and c["low"]<pdl and c["close"]>pdl and abs(pct(pdl,c["low"]))>=spk:
            out.append(dict(bar_idx=i,bar=c,pattern="BULL_SWEEP_PDL"))
        lh = [bars[j]["high"] for j in range(max(0,i-25),i)]
        if len(lh)>=3:
            rh = max(lh)
            if sum(1 for h in lh if abs(pct(h,rh))<=tol*100)>=2:
                if c["high"]>rh and c["close"]<rh and pct(rh,c["high"])>=spk:
                    out.append(dict(bar_idx=i,bar=c,pattern="BEAR_SWEEP_EQH"))
        ll = [bars[j]["low"] for j in range(max(0,i-25),i)]
        if len(ll)>=3:
            rl = min(ll)
            if sum(1 for l in ll if abs(pct(l,rl))<=tol*100)>=2:
                if c["low"]<rl and c["close"]>rl and abs(pct(rl,c["low"]))>=spk:
                    out.append(dict(bar_idx=i,bar=c,pattern="BULL_SWEEP_EQL"))
    return out


def detect_mss_bos(bars, swings):
    out = []
    if len(swings) < 4:
        return out
    highs = [(idx,p) for idx,t,p in swings if t=="HIGH"]
    lows  = [(idx,p) for idx,t,p in swings if t=="LOW"]
    for i in range(1, len(bars)):
        ph = [(idx,p) for idx,p in highs if idx<i]
        pl = [(idx,p) for idx,p in lows  if idx<i]
        if len(ph)<2 or len(pl)<2:
            continue
        lsh,psh = ph[-1][1], ph[-2][1]
        lsl,psl = pl[-1][1], pl[-2][1]
        c, pc = bars[i]["close"], bars[i-1]["close"]
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
            out.append(dict(bar_idx=14,bar=bars[14],pattern="JUDAS_BEAR"))
    else:
        if pct(bars[14]["close"], max(b["high"] for b in rev)) >= abs(mv)*0.50:
            out.append(dict(bar_idx=14,bar=bars[14],pattern="JUDAS_BULL"))
    return out


def detect_ote(bars, swings):
    out, done, n = [], set(), len(bars)
    highs = [(idx,p) for idx,t,p in swings if t=="HIGH"]
    lows  = [(idx,p) for idx,t,p in swings if t=="LOW"]
    for h_idx,h_p in highs:
        nl = [(idx,p) for idx,p in lows if idx>h_idx]
        if not nl: continue
        l_idx,l_p = nl[0]
        if abs(pct(h_p,l_p)) < MIN_SWING_PCT: continue
        rng = h_p-l_p
        z_lo,z_hi = l_p+rng*OTE_FIB_LO, l_p+rng*OTE_FIB_HI
        for i in range(l_idx+1, min(l_idx+40,n)):
            if bars[i]["high"]>=z_lo and bars[i]["low"]<=z_hi:
                key=(h_idx,l_idx)
                if key not in done:
                    done.add(key)
                    out.append(dict(bar_idx=i,bar=bars[i],pattern="BEAR_OTE"))
                break
    for l_idx,l_p in lows:
        nh = [(idx,p) for idx,p in highs if idx>l_idx]
        if not nh: continue
        h_idx,h_p = nh[0]
        if abs(pct(l_p,h_p)) < MIN_SWING_PCT: continue
        rng = h_p-l_p
        z_hi2,z_lo2 = h_p-rng*OTE_FIB_LO, h_p-rng*OTE_FIB_HI
        for i in range(h_idx+1, min(h_idx+40,n)):
            if bars[i]["low"]<=z_hi2 and bars[i]["high"]>=z_lo2:
                key=(l_idx,h_idx)
                if key not in done:
                    done.add(key)
                    out.append(dict(bar_idx=i,bar=bars[i],pattern="BULL_OTE"))
                break
    return out


def detect_breakers(bars, obs):
    out, n = [], len(bars)
    for ob in obs:
        idx = ob["bar_idx"]
        end = min(idx+30, n)
        if ob["pattern"] == "BEAR_OB":
            for j in range(idx+1, end):
                if bars[j]["close"] > ob["bar"]["high"]:
                    out.append(dict(bar_idx=j,bar=bars[j],pattern="BULL_BREAKER"))
                    break
        else:
            for j in range(idx+1, end):
                if bars[j]["close"] < ob["bar"]["low"]:
                    out.append(dict(bar_idx=j,bar=bars[j],pattern="BEAR_BREAKER"))
                    break
    return out


# ── P&L aggregation ───────────────────────────────────────────────────

class PnlBucket:
    def __init__(self):
        self.n_pats   = 0
        self.n_nodata = 0
        self.pnl      = {h: [] for h in HORIZONS}

    def no_data(self):
        self.n_pats   += 1
        self.n_nodata += 1

    def add(self, pnl_dict):
        self.n_pats += 1
        for h in HORIZONS:
            if pnl_dict.get(h) is not None:
                self.pnl[h].append(pnl_dict[h])

    def stats(self, h):
        v = self.pnl[h]
        if not v:
            return None
        wins = [x for x in v if x > 0]
        loss = [x for x in v if x <= 0]
        wr   = len(wins)/len(v)
        aw   = sum(wins)/len(wins) if wins else 0.0
        al   = sum(loss)/len(loss) if loss else 0.0
        exp  = wr*aw + (1-wr)*al
        return dict(n=len(v), wr=wr*100, avg=sum(v)/len(v),
                    aw=aw, al=al, exp=exp,
                    best=max(v), worst=min(v))

    def exp30(self):
        s = self.stats(30)
        return s["exp"] if s else -999


def fmt(v, w=9):
    if v is None: return f"{'n/a':>{w}}"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.1f}%".rjust(w)


def print_pnl_table(title, rows_data, min_n=5):
    """
    rows_data: list of (label, PnlBucket)
    Prints P&L table sorted by T+30m expectancy.
    """
    print(f"\n{'='*112}")
    print(f"  {title}")
    print(f"{'='*112}")
    rows = [(label, b) for label, b in rows_data if b.n_pats >= min_n]
    rows.sort(key=lambda x: x[1].exp30(), reverse=True)
    if not rows:
        print("  (no rows above minimum N)")
        return

    print(f"  {'Label':<40} {'N':>5} {'NoD':>5}  "
          f"{'T+15m Exp':>12}  {'T+30m Exp':>12}  {'T+60m Exp':>12}  "
          f"{'T+30m WR':>10}  {'T+30m Avg':>11}")
    print(f"  {'-'*108}")

    for label, b in rows:
        s15 = b.stats(15)
        s30 = b.stats(30)
        s60 = b.stats(60)
        exp15 = fmt(s15["exp"] if s15 else None)
        exp30 = fmt(s30["exp"] if s30 else None)
        exp60 = fmt(s60["exp"] if s60 else None)
        wr30  = f"{s30['wr']:.1f}%".rjust(9) if s30 else "     n/a"
        avg30 = fmt(s30["avg"] if s30 else None)
        flag  = " ◄" if s30 and s30["exp"] > 5 else (" ▼" if s30 and s30["exp"] < 0 else "  ")
        print(f"  {label:<40} {b.n_pats:>5} {b.n_nodata:>5}  "
              f"{exp15:>12}  {exp30:>12}{flag} {exp60:>12}  "
              f"{wr30:>10}  {avg30:>11}")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    # Buckets: "pattern|ctx" → PnlBucket
    by_pat_ctx  = defaultdict(PnlBucket)   # pattern|MTF
    by_pat_dte  = defaultdict(PnlBucket)   # pattern|DTE
    by_pat_all  = defaultdict(PnlBucket)   # pattern (baseline)
    # Intersection: pattern|ctx|DTE
    by_intersect = defaultdict(PnlBucket)  # pattern|ctx|DTE

    for symbol in ["NIFTY", "SENSEX"]:
        expiry_idx = build_expiry_index_simple(sb, inst[symbol])
        log(f"\n── {symbol} ─────────────────────────────────────────────")

        log("  Loading spot bars...")
        all_bars = fetch_spot_bars(sb, inst[symbol])
        sessions = sessions_from_bars(all_bars)
        dates    = sorted(sessions.keys())
        log(f"  {len(all_bars):,} bars | {len(dates)} sessions")

        log("  Building HTF bars and zone indexes...")
        daily_bars  = build_daily_bars(sessions)
        weekly_bars = build_weekly_bars(daily_bars)
        daily_idx, weekly_idx = build_zone_indexes(daily_bars, weekly_bars)
        log(f"  {len(daily_bars)} daily | {len(weekly_bars)} weekly | zones indexed")

        log("  Detecting all patterns...")
        all_patterns = []

        for i, d in enumerate(dates):
            bars = sessions[d]
            if len(bars) < 30:
                continue
            pdh = pdl = None
            if i > 0:
                pb  = sessions[dates[i-1]]
                pdh = max(b["high"] for b in pb)
                pdl = min(b["low"]  for b in pb)

            sw       = find_swings(bars)
            obs_list = detect_obs(bars)
            pats     = (obs_list
                        + detect_breakers(bars, obs_list)
                        + detect_fvg(bars)
                        + detect_sweeps(bars, pdh, pdl)
                        + detect_mss_bos(bars, sw)
                        + detect_judas(bars)
                        + detect_ote(bars, sw))

            for pat in pats:
                pat_name = pat["pattern"]
                if pat_name not in OPT_TYPE:
                    continue
                bar   = pat["bar"]
                spot  = bar["close"]
                price = spot
                ctx   = get_mtf_context(price, d, daily_idx, weekly_idx)
                dte   = compute_dte(d, expiry_idx)
                dteb  = dte_bucket(dte)
                exp_d = nearest_expiry_db(d, expiry_idx)
                atm   = atm_strike(spot, symbol)

                all_patterns.append({
                    "pattern":  pat_name,
                    "bar":      bar,
                    "td":       d,
                    "exp_date": exp_d,
                    "atm":      atm,
                    "opt_type": OPT_TYPE[pat_name],
                    "ctx":      ctx,
                    "dte":      dte,
                    "dteb":     dteb,
                    "symbol":   symbol,
                })

        log(f"  {len(all_patterns)} patterns detected")

        # Group by (trade_date, expiry_date) for batch option fetch
        day_groups = defaultdict(list)
        for pat in all_patterns:
            day_groups[(pat["td"], pat["exp_date"])].append(pat)

        log(f"  Fetching option data for {len(day_groups)} day/expiry groups...")

        for gi, ((td, ed), pats_today) in enumerate(sorted(day_groups.items())):
            # All strikes needed this day
            strikes_needed  = set()
            opt_types_needed = set()
            step = STRIKE_STEP[symbol]
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
            except Exception as e:
                log(f"    WARNING {td}/{ed}: {e}")
                for pat in pats_today:
                    k = pat["pattern"]
                    by_pat_all[k].no_data()
                    by_pat_ctx[f"{k}|{pat['ctx']}"].no_data()
                    by_pat_dte[f"{k}|{pat['dteb']}"].no_data()
                    by_intersect[f"{k}|{pat['ctx']}|{pat['dteb']}"].no_data()
                continue

            if gi % 30 == 0:
                log(f"    {gi}/{len(day_groups)} groups...")

            for pat in pats_today:
                ts    = pat["bar"]["bar_ts"]
                stk   = pat["atm"]
                ot    = pat["opt_type"]
                k     = pat["pattern"]
                ctx   = pat["ctx"]
                dteb  = pat["dteb"]

                entry_p, entry_stk = get_option_price(lookup, stk, ot, ts, symbol)

                if entry_p is None:
                    by_pat_all[k].no_data()
                    by_pat_ctx[f"{k}|{ctx}"].no_data()
                    by_pat_dte[f"{k}|{dteb}"].no_data()
                    by_intersect[f"{k}|{ctx}|{dteb}"].no_data()
                    continue

                pnl_dict = {}
                for h in HORIZONS:
                    if not in_session(ts, h):
                        pnl_dict[h] = None
                        continue
                    exit_p, _ = get_option_price(
                        lookup, entry_stk, ot,
                        ts + timedelta(minutes=h), symbol
                    )
                    pnl_dict[h] = pct(entry_p, exit_p) if exit_p else None

                by_pat_all[k].add(pnl_dict)
                by_pat_ctx[f"{k}|{ctx}"].add(pnl_dict)
                by_pat_dte[f"{k}|{dteb}"].add(pnl_dict)
                by_intersect[f"{k}|{ctx}|{dteb}"].add(pnl_dict)

        log(f"  {symbol} complete.")

    # ── Output ────────────────────────────────────────────────────────
    print("\n" + "=" * 112)
    print("  MERDIAN EXPERIMENT 10c — ICT PATTERNS: MTF CONTEXT × OPTIONS P&L")
    print("  Period: Apr 2025 – Mar 2026  |  NIFTY + SENSEX")
    print("  N=patterns detected | NoD=no option data found")
    print("  Exp=Expectancy (win_rate × avg_winner + loss_rate × avg_loser)")
    print("  ◄ = Exp > 5% (tradeable) | ▼ = Exp < 0% (avoid) | blank = marginal")
    print("  Sorted by T+30m Expectancy descending within each section")
    print("=" * 112)

    # ── Section 1: Baseline — all patterns ───────────────────────────
    print_pnl_table(
        "SECTION 1 — BASELINE: All patterns, all context, all DTE",
        [(k, v) for k,v in by_pat_all.items()],
        min_n=5
    )

    # ── Section 2: Pattern × MTF context ─────────────────────────────
    print_pnl_table(
        "SECTION 2 — PATTERN × MTF CONTEXT\n"
        "  Key question: does HIGH (weekly zone) context improve option P&L?",
        [(k, v) for k,v in by_pat_ctx.items()],
        min_n=5
    )

    # ── Section 3: Pattern × DTE ──────────────────────────────────────
    print_pnl_table(
        "SECTION 3 — PATTERN × DTE BUCKET",
        [(k, v) for k,v in by_pat_dte.items()],
        min_n=5
    )

    # ── Section 4: HIGH context only — the best setups ───────────────
    high_only = [(k, v) for k, v in by_pat_ctx.items() if "|HIGH" in k]
    print_pnl_table(
        "SECTION 4 — HIGH MTF CONTEXT ONLY (weekly zone confluence)\n"
        "  These are the setups where institutional zone + ICT pattern align",
        high_only, min_n=3
    )

    # ── Section 5: HIGH context × DTE intersection ───────────────────
    high_dte = [(k,v) for k,v in by_intersect.items() if "|HIGH|" in k]
    print_pnl_table(
        "SECTION 5 — HIGH MTF CONTEXT × DTE  (the highest-conviction setups)\n"
        "  Weekly zone + ICT pattern + expiry proximity all aligned",
        high_dte, min_n=3
    )

    # ── Section 6: Summary comparison ────────────────────────────────
    print(f"\n{'='*112}")
    print("  SECTION 6 — MTF CONTEXT LIFT TABLE (T+30m Expectancy)")
    print("  Does HIGH context consistently outperform LOW context?")
    print(f"{'='*112}")
    print(f"  {'Pattern':<22} {'LOW Exp':>10}  {'MED Exp':>10}  "
          f"{'HIGH Exp':>10}  {'Lift H-L':>10}  {'Verdict'}")
    print(f"  {'-'*85}")

    all_pats = sorted(set(k.split("|")[0] for k in by_pat_ctx))
    for pat in all_pats:
        lo = by_pat_ctx.get(f"{pat}|LOW")
        me = by_pat_ctx.get(f"{pat}|MEDIUM")
        hi = by_pat_ctx.get(f"{pat}|HIGH")
        s_lo = lo.stats(30) if lo else None
        s_me = me.stats(30) if me else None
        s_hi = hi.stats(30) if hi else None
        if not s_lo and not s_hi:
            continue
        e_lo = s_lo["exp"] if s_lo else None
        e_me = s_me["exp"] if s_me else None
        e_hi = s_hi["exp"] if s_hi else None
        lift = (e_hi - e_lo) if (e_hi is not None and e_lo is not None) else None
        verdict = ""
        if lift is not None:
            if lift > 20:   verdict = "MTF adds major edge"
            elif lift > 5:  verdict = "MTF adds edge"
            elif lift > 0:  verdict = "MTF marginal"
            elif lift > -5: verdict = "MTF neutral"
            else:           verdict = "MTF no benefit"
        print(f"  {pat:<22} {fmt(e_lo):>10}  {fmt(e_me):>10}  "
              f"{fmt(e_hi):>10}  {fmt(lift):>10}  {verdict}")

    print(f"\n{'='*112}")
    print("  KEY FINDINGS GUIDE")
    print("  Section 2: MTF context breakdown — look for HIGH > LOW gap")
    print("  Section 4: HIGH context patterns — your best opportunity set")
    print("  Section 5: HIGH + DTE=0/1 — the highest conviction trade setups")
    print("  Section 6: Lift table — quantifies whether MTF context adds value")
    print(f"{'='*112}\n")


if __name__ == "__main__":
    main()



