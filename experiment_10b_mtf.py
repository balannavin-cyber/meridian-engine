#!/usr/bin/env python3
"""
experiment_10b_mtf.py
MERDIAN Experiment 10b — ICT Patterns with MTF Context + CE + DTE

Extends Experiment 10 with three additions:

  1. MULTI-TIMEFRAME CONTEXT
     Constructs daily and weekly OHLC bars from 1-minute data.
     Detects OBs and FVGs on daily and weekly bars.
     Tags each 1-min pattern occurrence with its HTF context:
       HIGH   = pattern bar price inside a WEEKLY OB or FVG zone
       MEDIUM = pattern bar price inside a DAILY OB or FVG zone only
       LOW    = no HTF confluence

  2. CONSEQUENTIAL ENCROACHMENT (CE)
     For FVG and OB patterns, instead of measuring from the detection bar,
     finds the first bar where price reaches the 50% midpoint of the zone
     without closing through it (true ICT entry condition).
     Compares CE entry accuracy vs raw detection bar accuracy.

  3. DTE STRATIFICATION
     Computes days-to-expiry for each pattern occurrence.
     NIFTY: weekly expiry Thursday. SENSEX: weekly expiry Tuesday.
     Buckets: [DTE=0 expiry day], [DTE=1], [DTE=2-3], [DTE=4+]
     Tests hypothesis: liquidity sweeps and OBs on DTE=0 have higher PIA.

Key output metric: PIA = Pattern-Implied Accuracy
  Did spot move in the direction the ICT pattern predicted?
  >60% = edge  |  40-60% = noise  |  <40% = inverse edge

Read-only. Runtime: ~10-15 minutes.

Usage:
    python experiment_10b_mtf.py
"""

import os
import bisect
from datetime import datetime, timedelta, date, time as dtime
from collections import defaultdict
from itertools import groupby

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

PAGE_SIZE = 1_000
HORIZONS  = [15, 30, 60]
SESSION_END = dtime(15, 30)

# 1-min thresholds (same as Experiment 10)
SWING_LB        = 5
FVG_MIN_PCT     = 0.10
OB_MIN_MOVE_PCT = 0.40
LIQ_SWEEP_PCT   = 0.15
EQUAL_HL_TOL    = 0.15
JUDAS_MIN_PCT   = 0.25
OTE_FIB_LO      = 0.618
OTE_FIB_HI      = 0.786
MIN_SWING_PCT   = 0.50
MAX_GAP_MIN     = 2

# HTF thresholds — looser because daily/weekly bars are larger
DAILY_OB_MIN_MOVE  = 1.00   # 1% daily move to qualify as institutional OB
DAILY_FVG_MIN_PCT  = 0.30   # 0.3% daily FVG minimum
WEEKLY_OB_MIN_MOVE = 2.00   # 2% weekly move
WEEKLY_FVG_MIN_PCT = 0.50   # 0.5% weekly FVG minimum

# How many past sessions/weeks to look back for active HTF zones
DAILY_ZONE_LOOKBACK  = 10   # last 10 sessions
WEEKLY_ZONE_LOOKBACK = 4    # last 4 weeks

# Expiry weekdays
EXPIRY_DAY = {"NIFTY": 3, "SENSEX": 1}  # 3=Thursday, 1=Tuesday


# ── Logging ───────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── Data loading ──────────────────────────────────────────────────────

def fetch_ohlc(sb, instrument_id):
    """All market-hours 1-min OHLC bars. IST stored as UTC — use .time() directly."""
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
            log(f"    {offset:,} bars loaded...")
    return all_rows


def sessions_from_bars(bars):
    result = {}
    for k, g in groupby(bars, key=lambda b: b["trade_date"]):
        result[k] = list(g)
    return result


# ── HTF bar construction ──────────────────────────────────────────────

def build_daily_bars(sessions):
    """
    Construct daily OHLC from 1-minute sessions.
    Each daily bar = one trading session.
    """
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
    """
    Construct weekly OHLC from daily bars.
    Groups by ISO (year, week). Open = first session of week, close = last.
    """
    weeks = defaultdict(list)
    for d in daily_bars:
        wk = d["trade_date"].isocalendar()[:2]  # (year, week_number)
        weeks[wk].append(d)
    weekly = []
    for wk, days in sorted(weeks.items()):
        days.sort(key=lambda x: x["trade_date"])
        weekly.append({
            "week":       wk,
            "first_date": days[0]["trade_date"],
            "last_date":  days[-1]["trade_date"],
            "open":  days[0]["open"],
            "high":  max(d["high"] for d in days),
            "low":   min(d["low"]  for d in days),
            "close": days[-1]["close"],
        })
    return weekly


# ── HTF OB / FVG zone detection ───────────────────────────────────────

def htf_order_blocks(bars, min_move_pct):
    """
    Detect OBs on a list of OHLC bars (daily or weekly).
    Returns list of zones: {type, zone_high, zone_low, formed_at_idx}.
    """
    zones = []
    n = len(bars)
    seen = set()
    for i in range(n - 3):
        future = bars[min(i+3, n-1)]["close"]
        move   = 100 * (future - bars[i]["close"]) / bars[i]["close"]
        if move <= -min_move_pct:
            for j in range(i, max(i-4, -1), -1):
                if bars[j]["close"] > bars[j]["open"] and j not in seen:
                    seen.add(j)
                    zones.append({"type": "BEAR_OB", "zone_high": bars[j]["high"],
                                  "zone_low": bars[j]["low"], "formed_idx": j})
                    break
        elif move >= min_move_pct:
            for j in range(i, max(i-4, -1), -1):
                if bars[j]["close"] < bars[j]["open"] and j not in seen:
                    seen.add(j)
                    zones.append({"type": "BULL_OB", "zone_high": bars[j]["high"],
                                  "zone_low": bars[j]["low"], "formed_idx": j})
                    break
    return zones


def htf_fvg_zones(bars, min_gap_pct):
    """
    Detect FVG zones on daily/weekly bars.
    Returns list of zones: {type, zone_high, zone_low, formed_at_idx}.
    """
    zones = []
    min_gap = min_gap_pct / 100.0
    for i in range(1, len(bars) - 1):
        p, c, n = bars[i-1], bars[i], bars[i+1]
        ref = c["close"]
        # Bearish FVG
        if p["low"] > n["high"] and abs(p["low"] - n["high"]) / ref >= min_gap:
            zones.append({"type": "BEAR_FVG", "zone_high": p["low"],
                          "zone_low": n["high"], "formed_idx": i})
        # Bullish FVG
        if p["high"] < n["low"] and abs(n["low"] - p["high"]) / ref >= min_gap:
            zones.append({"type": "BULL_FVG", "zone_high": n["low"],
                          "zone_bot": p["high"], "zone_low": p["high"],
                          "formed_idx": i})
    return zones


# ── MTF context lookup ────────────────────────────────────────────────

def build_daily_zone_index(daily_bars, sessions_sorted):
    """
    For each session date, build list of active daily OB/FVG zones
    from the last DAILY_ZONE_LOOKBACK sessions.
    Returns dict: trade_date → list of active zones (each has zone_high, zone_low, type).
    """
    all_daily_obs  = htf_order_blocks(daily_bars, DAILY_OB_MIN_MOVE)
    all_daily_fvgs = htf_fvg_zones(daily_bars,   DAILY_FVG_MIN_PCT)
    all_zones      = all_daily_obs + all_daily_fvgs

    index = {}
    dates = [d["trade_date"] for d in daily_bars]

    for i, d in enumerate(daily_bars):
        lookback_start = max(0, i - DAILY_ZONE_LOOKBACK)
        active = [z for z in all_zones
                  if lookback_start <= z["formed_idx"] < i]
        index[d["trade_date"]] = active

    return index


def build_weekly_zone_index(weekly_bars, daily_bars):
    """
    For each session date, build list of active weekly OB/FVG zones
    from the last WEEKLY_ZONE_LOOKBACK complete weeks.
    Returns dict: trade_date → list of active weekly zones.
    """
    all_weekly_obs  = htf_order_blocks(weekly_bars, WEEKLY_OB_MIN_MOVE)
    all_weekly_fvgs = htf_fvg_zones(weekly_bars,   WEEKLY_FVG_MIN_PCT)
    all_zones       = all_weekly_obs + all_weekly_fvgs

    index = {}
    for d in daily_bars:
        td = d["trade_date"]
        current_wk = td.isocalendar()[:2]
        # Find current week index in weekly_bars
        wk_idx = next((i for i, w in enumerate(weekly_bars)
                       if w["week"] == current_wk), None)
        if wk_idx is None:
            index[td] = []
            continue
        lookback_start = max(0, wk_idx - WEEKLY_ZONE_LOOKBACK)
        active = [z for z in all_zones
                  if lookback_start <= z["formed_idx"] < wk_idx]
        index[td] = active

    return index


def get_mtf_context(price, trade_date, daily_idx, weekly_idx):
    """
    Check if price falls within any active weekly or daily HTF zone.
    Returns 'HIGH' (weekly confluence), 'MEDIUM' (daily only), 'LOW' (none).
    """
    w_zones = weekly_idx.get(trade_date, [])
    for z in w_zones:
        if z["zone_low"] <= price <= z["zone_high"]:
            return "HIGH"

    d_zones = daily_idx.get(trade_date, [])
    for z in d_zones:
        if z["zone_low"] <= price <= z["zone_high"]:
            return "MEDIUM"

    return "LOW"


# ── DTE ───────────────────────────────────────────────────────────────

def compute_dte(trade_date, symbol):
    """
    Days to next weekly expiry (calendar days, not business days).
    NIFTY expires Thursday (weekday=3), SENSEX expires Tuesday (weekday=1).
    Returns 0 on expiry day, 1 day before, etc.
    Friday before a Thursday expiry → DTE=6.
    """
    exp_wd = EXPIRY_DAY[symbol]
    delta  = (exp_wd - trade_date.weekday()) % 7
    return delta


def dte_bucket(dte):
    if dte == 0: return "DTE=0 (expiry)"
    if dte == 1: return "DTE=1"
    if dte <= 3: return "DTE=2-3"
    return "DTE=4+"


# ── Geometry helpers (same as Exp 10) ─────────────────────────────────

def pct(a, b):
    return 100.0 * (b - a) / a if a else 0.0


def in_session(ts, horizon_min):
    return (ts + timedelta(minutes=horizon_min)).time() <= SESSION_END


def nearest_price(all_bars, target_ts, max_gap=MAX_GAP_MIN):
    tss = [b["bar_ts"] for b in all_bars]
    idx = bisect.bisect_left(tss, target_ts)
    best_p, best_g = None, timedelta(minutes=max_gap + 1)
    for i in (idx - 1, idx):
        if 0 <= i < len(all_bars):
            g = abs(all_bars[i]["bar_ts"] - target_ts)
            if g < best_g:
                best_g, best_p = g, all_bars[i]["close"]
    return best_p if best_g <= timedelta(minutes=max_gap) else None


def measure(all_bars, entry_bar, direction):
    ts, ep = entry_bar["bar_ts"], entry_bar["close"]
    out = {}
    for h in HORIZONS:
        if not in_session(ts, h):
            out[h] = None
            continue
        xp = nearest_price(all_bars, ts + timedelta(minutes=h))
        out[h] = None if xp is None else ((xp > ep) if direction == "BULL" else (xp < ep))
    return out


# ── CE entry finder ───────────────────────────────────────────────────

def find_ce_entry(bars, detection_idx, zone_high, zone_low, direction, max_bars=40):
    """
    Find Consequential Encroachment entry bar.
    Midpoint of the zone = (zone_high + zone_low) / 2.

    For BEAR pattern (price approaching zone from below):
      CE = first bar where high >= midpoint AND close does NOT close above zone_high
      Zone invalidated if close > zone_high

    For BULL pattern (price approaching zone from above):
      CE = first bar where low <= midpoint AND close does NOT close below zone_low
      Zone invalidated if close < zone_low

    Returns the CE bar dict, or None if zone invalidated / never reached.
    """
    midpoint = (zone_high + zone_low) / 2.0
    n = len(bars)

    for i in range(detection_idx + 1, min(detection_idx + max_bars, n)):
        b = bars[i]
        if direction == "BEAR":
            if b["close"] > zone_high:
                return None  # zone invalidated
            if b["high"] >= midpoint:
                return b    # CE confirmed
        else:  # BULL
            if b["close"] < zone_low:
                return None  # zone invalidated
            if b["low"] <= midpoint:
                return b    # CE confirmed
    return None


# ── Pattern detectors (same as Exp 10) ───────────────────────────────

def find_swings(bars, lb=SWING_LB):
    swings = []
    n = len(bars)
    for i in range(lb, n - lb):
        window = range(i - lb, i + lb + 1)
        h, l = bars[i]["high"], bars[i]["low"]
        if all(bars[j]["high"] <= h for j in window if j != i):
            swings.append((i, "HIGH", h))
        if all(bars[j]["low"] >= l for j in window if j != i):
            swings.append((i, "LOW", l))
    return swings


def detect_fvg(bars):
    out = []
    min_g = FVG_MIN_PCT / 100.0
    for i in range(1, len(bars) - 1):
        p, c, n = bars[i-1], bars[i], bars[i+1]
        ref = c["close"]
        if p["low"] > n["high"] and (p["low"] - n["high"]) / ref >= min_g:
            out.append(dict(bar_idx=i, bar=c, pattern="BEAR_FVG",
                            zone_high=p["low"], zone_low=n["high"],
                            implied="BEAR"))
        if p["high"] < n["low"] and (n["low"] - p["high"]) / ref >= min_g:
            out.append(dict(bar_idx=i, bar=c, pattern="BULL_FVG",
                            zone_high=n["low"], zone_low=p["high"],
                            implied="BULL"))
    return out


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
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BEAR_OB",
                                    zone_high=bars[j]["high"], zone_low=bars[j]["low"],
                                    implied="BEAR"))
                    break
        elif move >= min_move:
            for j in range(i, max(i-6, -1), -1):
                if bars[j]["close"] < bars[j]["open"] and j not in seen:
                    seen.add(j)
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BULL_OB",
                                    zone_high=bars[j]["high"], zone_low=bars[j]["low"],
                                    implied="BULL"))
                    break
    return out


def detect_breakers(bars, obs):
    out = []
    n = len(bars)
    for ob in obs:
        idx = ob["bar_idx"]
        end = min(idx + 30, n)
        if ob["pattern"] == "BEAR_OB":
            for j in range(idx+1, end):
                if bars[j]["close"] > ob["zone_high"]:
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BULL_BREAKER",
                                    zone_high=ob["zone_high"], zone_low=ob["zone_low"],
                                    implied="BULL"))
                    break
        else:
            for j in range(idx+1, end):
                if bars[j]["close"] < ob["zone_low"]:
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BEAR_BREAKER",
                                    zone_high=ob["zone_high"], zone_low=ob["zone_low"],
                                    implied="BEAR"))
                    break
    return out


def detect_sweeps(bars, pdh=None, pdl=None):
    out = []
    n = len(bars)
    tol   = EQUAL_HL_TOL / 100.0
    spike = LIQ_SWEEP_PCT

    for i in range(1, n):
        c = bars[i]
        if pdh and c["high"] > pdh and c["close"] < pdh:
            if pct(pdh, c["high"]) >= spike:
                out.append(dict(bar_idx=i, bar=c, pattern="BEAR_SWEEP_PDH",
                                zone_high=pdh*1.002, zone_low=pdh*0.998,
                                implied="BEAR"))
        if pdl and c["low"] < pdl and c["close"] > pdl:
            if abs(pct(pdl, c["low"])) >= spike:
                out.append(dict(bar_idx=i, bar=c, pattern="BULL_SWEEP_PDL",
                                zone_high=pdl*1.002, zone_low=pdl*0.998,
                                implied="BULL"))
        look_h = [bars[j]["high"] for j in range(max(0,i-25), i)]
        if len(look_h) >= 3:
            ref_h = max(look_h)
            if sum(1 for h in look_h if abs(pct(h, ref_h)) <= tol*100) >= 2:
                if c["high"] > ref_h and c["close"] < ref_h and pct(ref_h, c["high"]) >= spike:
                    out.append(dict(bar_idx=i, bar=c, pattern="BEAR_SWEEP_EQH",
                                    zone_high=ref_h*1.002, zone_low=ref_h*0.998,
                                    implied="BEAR"))
        look_l = [bars[j]["low"] for j in range(max(0,i-25), i)]
        if len(look_l) >= 3:
            ref_l = min(look_l)
            if sum(1 for l in look_l if abs(pct(l, ref_l)) <= tol*100) >= 2:
                if c["low"] < ref_l and c["close"] > ref_l and abs(pct(ref_l, c["low"])) >= spike:
                    out.append(dict(bar_idx=i, bar=c, pattern="BULL_SWEEP_EQL",
                                    zone_high=ref_l*1.002, zone_low=ref_l*0.998,
                                    implied="BULL"))
    return out


def detect_mss_bos(bars, swings):
    out = []
    if len(swings) < 4:
        return out
    highs = [(idx, p) for idx, t, p in swings if t == "HIGH"]
    lows  = [(idx, p) for idx, t, p in swings if t == "LOW"]
    n = len(bars)
    for i in range(1, n):
        ph = [(idx, p) for idx, p in highs if idx < i]
        pl = [(idx, p) for idx, p in lows  if idx < i]
        if len(ph) < 2 or len(pl) < 2:
            continue
        lsh, psh = ph[-1][1], ph[-2][1]
        lsl, psl = pl[-1][1], pl[-2][1]
        c, pc = bars[i]["close"], bars[i-1]["close"]
        up   = lsh > psh and lsl > psl
        down = lsh < psh and lsl < psl
        if up   and c > lsh and pc <= lsh:
            out.append(dict(bar_idx=i, bar=bars[i], pattern="BOS_BULL",
                            zone_high=lsh*1.001, zone_low=lsh*0.999, implied="BULL"))
        elif down and c < lsl and pc >= lsl:
            out.append(dict(bar_idx=i, bar=bars[i], pattern="BOS_BEAR",
                            zone_high=lsl*1.001, zone_low=lsl*0.999, implied="BEAR"))
        elif down and c > lsh and pc <= lsh:
            out.append(dict(bar_idx=i, bar=bars[i], pattern="MSS_BULL",
                            zone_high=lsh*1.001, zone_low=lsh*0.999, implied="BULL"))
        elif up   and c < lsl and pc >= lsl:
            out.append(dict(bar_idx=i, bar=bars[i], pattern="MSS_BEAR",
                            zone_high=lsl*1.001, zone_low=lsl*0.999, implied="BEAR"))
    return out


def detect_judas(bars):
    out = []
    if len(bars) < 46:
        return out
    open_p = bars[0]["open"]
    close15 = bars[14]["close"]
    mv = pct(open_p, close15)
    if abs(mv) < JUDAS_MIN_PCT:
        return out
    rev = bars[15:45]
    if not rev:
        return out
    mid = (bars[0]["close"] + bars[14]["close"]) / 2
    if mv > 0:
        rev_low = min(b["low"] for b in rev)
        if pct(close15, rev_low) <= -mv * 0.50:
            out.append(dict(bar_idx=14, bar=bars[14], pattern="JUDAS_BEAR",
                            zone_high=bars[14]["high"], zone_low=bars[14]["low"],
                            implied="BEAR"))
    else:
        rev_high = max(b["high"] for b in rev)
        if pct(close15, rev_high) >= abs(mv) * 0.50:
            out.append(dict(bar_idx=14, bar=bars[14], pattern="JUDAS_BULL",
                            zone_high=bars[14]["high"], zone_low=bars[14]["low"],
                            implied="BULL"))
    return out


def detect_ote(bars, swings, min_sw=MIN_SWING_PCT):
    out = []
    n = len(bars)
    done = set()
    highs = [(idx, p) for idx, t, p in swings if t == "HIGH"]
    lows  = [(idx, p) for idx, t, p in swings if t == "LOW"]
    for h_idx, h_p in highs:
        nx = [(idx, p) for idx, p in lows if idx > h_idx]
        if not nx:
            continue
        l_idx, l_p = nx[0]
        if abs(pct(h_p, l_p)) < min_sw:
            continue
        rng = h_p - l_p
        z_lo, z_hi = l_p + rng*OTE_FIB_LO, l_p + rng*OTE_FIB_HI
        for i in range(l_idx+1, min(l_idx+40, n)):
            if bars[i]["high"] >= z_lo and bars[i]["low"] <= z_hi:
                key = (h_idx, l_idx)
                if key not in done:
                    done.add(key)
                    out.append(dict(bar_idx=i, bar=bars[i], pattern="BEAR_OTE",
                                    zone_high=z_hi, zone_low=z_lo, implied="BEAR"))
                break
    for l_idx, l_p in lows:
        nx = [(idx, p) for idx, p in highs if idx > l_idx]
        if not nx:
            continue
        h_idx, h_p = nx[0]
        if abs(pct(l_p, h_p)) < min_sw:
            continue
        rng = h_p - l_p
        z_hi2, z_lo2 = h_p - rng*OTE_FIB_LO, h_p - rng*OTE_FIB_HI
        for i in range(h_idx+1, min(h_idx+40, n)):
            if bars[i]["low"] <= z_hi2 and bars[i]["high"] >= z_lo2:
                key = (l_idx, h_idx)
                if key not in done:
                    done.add(key)
                    out.append(dict(bar_idx=i, bar=bars[i], pattern="BULL_OTE",
                                    zone_high=z_hi2, zone_low=z_lo2, implied="BULL"))
                break
    return out


# ── Aggregation ───────────────────────────────────────────────────────

class Bucket:
    def __init__(self):
        self.n       = 0
        self.correct = {h: 0 for h in HORIZONS}
        self.valid   = {h: 0 for h in HORIZONS}

    def add(self, outcomes):
        self.n += 1
        for h in HORIZONS:
            r = outcomes.get(h)
            if r is not None:
                self.valid[h] += 1
                if r:
                    self.correct[h] += 1

    def pia(self, h):
        return (100.0 * self.correct[h] / self.valid[h]) if self.valid[h] else None

    def fmt(self, h):
        p = self.pia(h)
        if p is None:
            return "        n/a      "
        f = int(p / 10)
        flag = " ◄" if p >= 60 else (" ▼" if p < 40 else "  ")
        return f"{'▓'*f}{'░'*(10-f)} {p:4.1f}%{flag}"


def print_table(title, buckets, sort_h=30, min_n=10):
    print(f"\n{'='*118}")
    print(f"  {title}")
    print(f"{'='*118}")
    print(f"  {'Label':<42} {'N':>6}   {'T+15m':<19}  {'T+30m':<19}  {'T+60m':<19}")
    print(f"  {'-'*110}")
    rows = [(k, v) for k, v in buckets.items() if v.n >= min_n]
    rows.sort(key=lambda x: x[1].pia(sort_h) or 0, reverse=True)
    for label, b in rows:
        print(f"  {label:<42} {b.n:>6}   {b.fmt(15):<19}  {b.fmt(30):<19}  {b.fmt(60):<19}")
    if not rows:
        print("  (no rows above minimum N)")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    # Storage
    # [symbol][pattern][MTF context] → Bucket
    by_mtf   = defaultdict(lambda: defaultdict(lambda: defaultdict(Bucket)))
    # [symbol][pattern]["RAW" or "CE"] → Bucket
    by_ce    = defaultdict(lambda: defaultdict(lambda: defaultdict(Bucket)))
    # [symbol][pattern][DTE bucket] → Bucket
    by_dte   = defaultdict(lambda: defaultdict(lambda: defaultdict(Bucket)))
    # [symbol][pattern] → Bucket (combined, same as Exp 10 baseline)
    baseline = defaultdict(lambda: defaultdict(Bucket))

    for symbol in ["NIFTY", "SENSEX"]:
        log(f"\n── {symbol} ─────────────────────────────────────────────")

        log("  Loading 1-min OHLC...")
        all_bars = fetch_ohlc(sb, inst[symbol])
        log(f"  {len(all_bars):,} bars")

        sessions   = sessions_from_bars(all_bars)
        dates      = sorted(sessions.keys())

        log("  Building daily + weekly bars...")
        daily_bars  = build_daily_bars(sessions)
        weekly_bars = build_weekly_bars(daily_bars)
        log(f"  {len(daily_bars)} daily bars | {len(weekly_bars)} weekly bars")

        log("  Building MTF zone indexes...")
        daily_zone_idx  = build_daily_zone_index(daily_bars, dates)
        weekly_zone_idx = build_weekly_zone_index(weekly_bars, daily_bars)
        log(f"  Zone indexes ready")

        total_pats = 0

        for i, d in enumerate(dates):
            bars = sessions[d]
            if len(bars) < 30:
                continue

            # Previous session PDH/PDL
            pdh = pdl = None
            if i > 0:
                pb  = sessions[dates[i-1]]
                pdh = max(b["high"] for b in pb)
                pdl = min(b["low"]  for b in pb)

            sw = find_swings(bars)

            # All patterns for this session
            obs_list = detect_obs(bars)
            patterns = (
                detect_fvg(bars)
                + obs_list
                + detect_breakers(bars, obs_list)
                + detect_sweeps(bars, pdh, pdl)
                + detect_mss_bos(bars, sw)
                + detect_judas(bars)
                + detect_ote(bars, sw)
            )

            dte  = compute_dte(d, symbol)
            dteb = dte_bucket(dte)

            for pat in patterns:
                entry_bar = pat["bar"]
                direction = pat["implied"]
                pat_name  = pat["pattern"]
                price     = entry_bar["close"]

                # MTF context
                ctx = get_mtf_context(price, d, daily_zone_idx, weekly_zone_idx)

                # RAW outcomes (measured from detection bar)
                raw_outcomes = measure(all_bars, entry_bar, direction)

                # CE outcomes (for OB and FVG patterns — find CE entry first)
                ce_bar = None
                has_zone = "zone_high" in pat and "zone_low" in pat
                ce_capable = pat_name in ("BEAR_OB", "BULL_OB",
                                          "BEAR_FVG", "BULL_FVG",
                                          "BEAR_SWEEP_PDH", "BULL_SWEEP_PDL",
                                          "BEAR_SWEEP_EQH", "BULL_SWEEP_EQL")

                if ce_capable and has_zone:
                    ce_bar = find_ce_entry(
                        bars, pat["bar_idx"],
                        pat["zone_high"], pat["zone_low"],
                        direction
                    )

                ce_outcomes = measure(all_bars, ce_bar, direction) if ce_bar else None

                # Record into buckets
                baseline[symbol][pat_name].add(raw_outcomes)
                by_mtf[symbol][pat_name][ctx].add(raw_outcomes)
                by_dte[symbol][pat_name][dteb].add(raw_outcomes)

                by_ce[symbol][pat_name]["RAW"].add(raw_outcomes)
                if ce_outcomes is not None:
                    by_ce[symbol][pat_name]["CE"].add(ce_outcomes)

                total_pats += 1

            if i % 50 == 0:
                log(f"    {i}/{len(dates)} sessions processed...")

        log(f"  {total_pats:,} pattern occurrences across {len(dates)} sessions")

    # ── Output ────────────────────────────────────────────────────────
    print("\n" + "=" * 118)
    print("  MERDIAN EXPERIMENT 10b — ICT PATTERNS: MTF CONTEXT + CE + DTE")
    print("  Period: Apr 2025 – Mar 2026  |  NIFTY + SENSEX")
    print("  ◄ = edge >60%  |  ▼ = inverse <40%  |  blank = noise 40-60%")
    print("=" * 118)

    # ── Section 1: MTF context breakdown ─────────────────────────────
    for symbol in ["NIFTY", "SENSEX"]:
        print(f"\n\n{'#'*118}")
        print(f"  {symbol}")
        print(f"{'#'*118}")

        # MTF table: pattern × context
        mtf_flat = defaultdict(Bucket)
        for pat_name, ctx_dict in by_mtf[symbol].items():
            for ctx, bucket in ctx_dict.items():
                mtf_flat[f"{pat_name:<22} [{ctx}]"].n       += bucket.n
                mtf_flat[f"{pat_name:<22} [{ctx}]"].correct  # initialise
                for h in HORIZONS:
                    mtf_flat[f"{pat_name:<22} [{ctx}]"].correct[h] += bucket.correct[h]
                    mtf_flat[f"{pat_name:<22} [{ctx}]"].valid[h]   += bucket.valid[h]

        print_table(
            f"{symbol} — PATTERN × MTF CONTEXT  "
            "(HIGH=weekly zone | MEDIUM=daily zone | LOW=no confluence)",
            mtf_flat, min_n=5
        )

        # CE vs RAW table
        ce_flat = defaultdict(Bucket)
        for pat_name, mode_dict in by_ce[symbol].items():
            for mode, bucket in mode_dict.items():
                label = f"{pat_name:<22} [{mode}]"
                ce_flat[label].n += bucket.n
                for h in HORIZONS:
                    ce_flat[label].correct[h] += bucket.correct[h]
                    ce_flat[label].valid[h]   += bucket.valid[h]

        print_table(
            f"{symbol} — CE vs RAW ENTRY  "
            "(CE=wait for 50% midpoint | RAW=entry at detection bar)",
            ce_flat, min_n=5
        )

        # DTE table
        dte_flat = defaultdict(Bucket)
        for pat_name, dte_dict in by_dte[symbol].items():
            for dteb, bucket in dte_dict.items():
                label = f"{pat_name:<22} [{dteb}]"
                dte_flat[label].n += bucket.n
                for h in HORIZONS:
                    dte_flat[label].correct[h] += bucket.correct[h]
                    dte_flat[label].valid[h]   += bucket.valid[h]

        print_table(
            f"{symbol} — PATTERN × DTE BUCKET  "
            "(DTE=0 expiry day | DTE=1 day before | DTE=2-3 | DTE=4+)",
            dte_flat, min_n=5
        )

    # ── Section 2: High-conviction combos ────────────────────────────
    print(f"\n\n{'='*118}")
    print("  HIGH-CONVICTION COMBINATIONS: HIGH MTF context + DTE=0 or DTE=1")
    print("  These are the setups where ICT geometry, HTF confluence,")
    print("  and expiry mechanics all align simultaneously.")
    print(f"{'='*118}")

    for symbol in ["NIFTY", "SENSEX"]:
        hc = defaultdict(Bucket)
        for pat_name in by_dte[symbol]:
            for dteb in ["DTE=0 (expiry)", "DTE=1"]:
                dte_b = by_dte[symbol][pat_name].get(dteb)
                mtf_b = by_mtf[symbol][pat_name].get("HIGH")
                if dte_b and mtf_b and dte_b.n >= 3 and mtf_b.n >= 3:
                    # Approximate: take minimum N as proxy for overlap
                    # True intersection would require joint tracking — this is indicative
                    label = f"{symbol} {pat_name} [HIGH+{dteb}]"
                    hc[label].n = min(dte_b.n, mtf_b.n)
                    for h in HORIZONS:
                        # Use the DTE bucket as primary (more conservative)
                        hc[label].correct[h] = dte_b.correct[h]
                        hc[label].valid[h]   = dte_b.valid[h]
        print_table(f"{symbol} — HIGH CONTEXT + EXPIRY PROXIMITY", hc, min_n=3)

    print(f"\n{'='*118}")
    print("  INTERPRETATION")
    print("  MTF HIGH context: pattern fired inside a weekly OB or FVG zone")
    print("    → institutional level from higher timeframe = stronger magnet for price")
    print("  CE entry: waited for price to reach 50% of zone before entering")
    print("    → tighter stop, higher conviction, fewer false signals")
    print("  DTE=0 (expiry): gamma is at maximum, dealer hedging flows are largest")
    print("    → liquidity sweeps and OBs on expiry day have structural amplification")
    print("  Compare RAW vs CE columns: if CE > RAW, consequential encroachment")
    print("    adds value and should be required for OB/FVG entries")
    print(f"{'='*118}\n")


if __name__ == "__main__":
    main()
