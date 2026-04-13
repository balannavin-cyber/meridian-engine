#!/usr/bin/env python3
"""
experiment_10_ict_patterns.py
MERDIAN Experiment 10 — ICT Geometric Pattern Detection

Detects 8 ICT concepts on 1-minute OHLC bars across full year (Apr 2025 – Mar 2026)
and measures Pattern-Implied Accuracy (PIA) at T+15m, T+30m, T+60m for each.

Patterns detected:
  1. Fair Value Gap (FVG) — bullish and bearish
  2. Order Block (OB) — bullish and bearish
  3. Breaker Block — failed OB that flips direction
  4. Liquidity Sweep — PDH/PDL raids + equal highs/lows
  5. Market Structure Shift (MSS) — reversal signal
  6. Break of Structure (BOS) — continuation signal
  7. Judas Swing — opening trap reversal
  8. Optimal Trade Entry (OTE) — Fibonacci 61.8-79% retracement
  9. Kill Zone analysis — where large moves concentrate intraday

PIA = Pattern-Implied Accuracy
  Did spot move in the direction the ICT pattern predicted?
  >60% = edge  |  40-60% = noise  |  <40% = inverse edge

Thresholds calibrated for NIFTY/SENSEX 1-minute bars.
Read-only. Does NOT write to any table.
Runtime: ~5-8 minutes.

Usage:
    python experiment_10_ict_patterns.py
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

HORIZONS      = [15, 30, 60]
SESSION_START = dtime(9, 15)
SESSION_END   = dtime(15, 30)

# Calibrated for NIFTY/SENSEX 1-min bars
# NIFTY ~24000: 0.1% = 24pts, 0.3% = 72pts, 0.5% = 120pts
SWING_LOOKBACK   = 5      # bars each side for fractal swing detection
FVG_MIN_PCT      = 0.10   # minimum FVG size as % — filters micro-noise
OB_MIN_MOVE_PCT  = 0.40   # initiating move must be this large to create valid OB
LIQ_SWEEP_PCT    = 0.15   # spike beyond level must exceed this to qualify
EQUAL_HL_TOL_PCT = 0.15   # two levels are "equal" if within this %
JUDAS_MIN_PCT    = 0.25   # opening 15-bar move must exceed this for Judas detection
OTE_FIB_LO       = 0.618  # OTE zone lower Fibonacci
OTE_FIB_HI       = 0.786  # OTE zone upper Fibonacci
MIN_SWING_PCT    = 0.50   # minimum swing size for MSS/BOS/OTE
MAX_GAP_MIN      = 2      # nearest-bar lookup tolerance


# ── Logging ───────────────────────────────────────────────────────────

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ── Data loading ──────────────────────────────────────────────────────

def fetch_ohlc(sb, instrument_id):
    """
    Load all market-hours OHLC bars for one symbol.
    NOTE: bar_ts stored as IST wall-clock time with +00:00 offset.
    Use .time() directly — do NOT call .astimezone().
    """
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
    """Group sorted bars by trade_date. Returns OrderedDict date→[bars]."""
    result = {}
    for k, g in groupby(bars, key=lambda b: b["trade_date"]):
        result[k] = list(g)
    return result


# ── Geometry helpers ──────────────────────────────────────────────────

def pct(a, b):
    """% move from a to b."""
    return 100.0 * (b - a) / a if a else 0.0


def bar_t(bar):
    """Wall-clock time. IST stored as UTC — use .time() directly."""
    return bar["bar_ts"].time()


def in_session(ts, horizon_min):
    """True if ts + horizon_min is before SESSION_END."""
    return (ts + timedelta(minutes=horizon_min)).time() <= SESSION_END


def nearest_price(all_bars, target_ts, max_gap=MAX_GAP_MIN):
    """Binary search close price nearest to target_ts."""
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
    """
    Compute T+15/30/60 outcomes.
    Returns dict h → True (correct) / False (wrong) / None (no data or OOB).
    direction: 'BULL' or 'BEAR'
    """
    ts = entry_bar["bar_ts"]
    ep = entry_bar["close"]
    out = {}
    for h in HORIZONS:
        if not in_session(ts, h):
            out[h] = None
            continue
        xp = nearest_price(all_bars, ts + timedelta(minutes=h))
        if xp is None:
            out[h] = None
        else:
            move = xp - ep
            out[h] = (move > 0) if direction == "BULL" else (move < 0)
    return out


# ── Swing detection ───────────────────────────────────────────────────

def find_swings(bars, lb=SWING_LOOKBACK):
    """
    5-bar fractal swing detection.
    Returns list of (bar_index, 'HIGH'|'LOW', price).
    """
    swings = []
    n = len(bars)
    for i in range(lb, n - lb):
        window = range(i - lb, i + lb + 1)
        h = bars[i]["high"]
        l = bars[i]["low"]
        if all(bars[j]["high"] <= h for j in window if j != i):
            swings.append((i, "HIGH", h))
        if all(bars[j]["low"] >= l for j in window if j != i):
            swings.append((i, "LOW", l))
    return swings


# ── Pattern detectors ─────────────────────────────────────────────────

def fvg(bars):
    """
    Fair Value Gap.
    Bearish FVG: bars[i-1].low > bars[i+1].high  → gap between them (price left an imbalance going down)
    Bullish FVG: bars[i-1].high < bars[i+1].low  → gap between them (price left an imbalance going up)
    Implied: price will return to fill the gap. Entry at the FVG candle.
    Direction is continuation of the move that created the gap.
    """
    out = []
    min_gap = FVG_MIN_PCT / 100.0
    for i in range(1, len(bars) - 1):
        p, c, n = bars[i-1], bars[i], bars[i+1]
        ref = c["close"]
        # Bearish FVG
        if p["low"] > n["high"]:
            size = abs(p["low"] - n["high"]) / ref
            if size >= min_gap:
                out.append(dict(bar_idx=i, bar=c, pattern="BEAR_FVG",
                                gap_top=p["low"], gap_bot=n["high"],
                                gap_pct=size*100, implied="BEAR"))
        # Bullish FVG
        if p["high"] < n["low"]:
            size = abs(n["low"] - p["high"]) / ref
            if size >= min_gap:
                out.append(dict(bar_idx=i, bar=c, pattern="BULL_FVG",
                                gap_top=n["low"], gap_bot=p["high"],
                                gap_pct=size*100, implied="BULL"))
    return out


def order_blocks(bars, min_move=OB_MIN_MOVE_PCT):
    """
    Order Block detection.
    Bearish OB: last bullish candle (close>open) before a significant down move (>min_move%).
    Bullish OB:  last bearish candle (close<open) before a significant up move.
    Implied: when price returns to OB zone it should reverse — direction = opposite of OB type's body.
    Bearish OB → implied BEAR (price returning to OB zone = sell).
    Bullish OB  → implied BULL (price returning to OB zone = buy).
    Also detect Breaker Blocks: OBs that were violated (price ran through them).
    """
    out = []
    n = len(bars)
    seen = set()

    for i in range(n - 6):
        future = bars[min(i+5, n-1)]["close"]
        move   = pct(bars[i]["close"], future)

        if move <= -min_move:
            # Significant down move — find last bullish candle before i
            for j in range(i, max(i-6, -1), -1):
                if bars[j]["close"] > bars[j]["open"] and j not in seen:
                    seen.add(j)
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BEAR_OB",
                                    ob_high=bars[j]["high"], ob_low=bars[j]["low"],
                                    move_pct=move, implied="BEAR"))
                    break
        elif move >= min_move:
            # Significant up move — find last bearish candle before i
            for j in range(i, max(i-6, -1), -1):
                if bars[j]["close"] < bars[j]["open"] and j not in seen:
                    seen.add(j)
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BULL_OB",
                                    ob_high=bars[j]["high"], ob_low=bars[j]["low"],
                                    move_pct=move, implied="BULL"))
                    break
    return out


def breaker_blocks(bars, obs):
    """
    Breaker Block: an OB that was violated — price ran through it.
    A violated BEAR_OB (price went above ob_high) becomes a BULL_BREAKER (bullish support).
    A violated BULL_OB  (price went below ob_low)  becomes a BEAR_BREAKER (bearish resistance).
    Detect violation in the 30 bars following the OB bar.
    """
    out = []
    n = len(bars)
    for ob in obs:
        idx = ob["bar_idx"]
        look_end = min(idx + 30, n)
        if ob["pattern"] == "BEAR_OB":
            # Violated if price closes above ob_high
            for j in range(idx+1, look_end):
                if bars[j]["close"] > ob["ob_high"]:
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BULL_BREAKER",
                                    level=ob["ob_high"], implied="BULL"))
                    break
        elif ob["pattern"] == "BULL_OB":
            # Violated if price closes below ob_low
            for j in range(idx+1, look_end):
                if bars[j]["close"] < ob["ob_low"]:
                    out.append(dict(bar_idx=j, bar=bars[j], pattern="BEAR_BREAKER",
                                    level=ob["ob_low"], implied="BEAR"))
                    break
    return out


def liquidity_sweeps(bars, pdh=None, pdl=None):
    """
    Liquidity sweeps — price raids a liquidity pool then reverses.
    Types:
      PDH sweep (BEAR): spike above previous day high, closes back below → BEAR
      PDL sweep (BULL): spike below previous day low, closes back above → BULL
      Equal-highs sweep (BEAR): spike above clustered highs, closes back below → BEAR
      Equal-lows sweep (BULL):  spike below clustered lows, closes back above → BULL
    """
    out = []
    n = len(bars)
    tol   = EQUAL_HL_TOL_PCT / 100.0
    spike = LIQ_SWEEP_PCT / 100.0

    for i in range(1, n):
        c = bars[i]

        # PDH sweep
        if pdh and c["high"] > pdh and c["close"] < pdh:
            if pct(pdh, c["high"]) >= LIQ_SWEEP_PCT:
                out.append(dict(bar_idx=i, bar=c, pattern="BEAR_SWEEP_PDH",
                                level=pdh, spike_pct=pct(pdh, c["high"]),
                                implied="BEAR"))

        # PDL sweep
        if pdl and c["low"] < pdl and c["close"] > pdl:
            if abs(pct(pdl, c["low"])) >= LIQ_SWEEP_PCT:
                out.append(dict(bar_idx=i, bar=c, pattern="BULL_SWEEP_PDL",
                                level=pdl, spike_pct=abs(pct(pdl, c["low"])),
                                implied="BULL"))

        # Equal-highs sweep — look back 5-25 bars
        look = [bars[j]["high"] for j in range(max(0, i-25), i)]
        if len(look) >= 3:
            ref_h = max(look)
            cluster = [h for h in look if abs(pct(h, ref_h)) <= tol*100]
            if len(cluster) >= 2 and c["high"] > ref_h and c["close"] < ref_h:
                if pct(ref_h, c["high"]) >= LIQ_SWEEP_PCT:
                    out.append(dict(bar_idx=i, bar=c, pattern="BEAR_SWEEP_EQH",
                                    level=ref_h, spike_pct=pct(ref_h, c["high"]),
                                    implied="BEAR"))

        # Equal-lows sweep
        look_l = [bars[j]["low"] for j in range(max(0, i-25), i)]
        if len(look_l) >= 3:
            ref_l = min(look_l)
            cluster_l = [l for l in look_l if abs(pct(l, ref_l)) <= tol*100]
            if len(cluster_l) >= 2 and c["low"] < ref_l and c["close"] > ref_l:
                if abs(pct(ref_l, c["low"])) >= LIQ_SWEEP_PCT:
                    out.append(dict(bar_idx=i, bar=c, pattern="BULL_SWEEP_EQL",
                                    level=ref_l, spike_pct=abs(pct(ref_l, c["low"])),
                                    implied="BULL"))
    return out


def mss_bos(bars, swings):
    """
    Market Structure Shift (MSS) and Break of Structure (BOS).
    Requires 2+ swing highs AND 2+ swing lows to establish structure.

    Trend determination from last 2 swings:
      Uptrend:   last_SH > prev_SH AND last_SL > prev_SL
      Downtrend: last_SH < prev_SH AND last_SL < prev_SL

    BOS_BULL: uptrend continues — price closes above last swing high
    BOS_BEAR: downtrend continues — price closes below last swing low
    MSS_BULL: was downtrend, price closes above last swing high → reversal
    MSS_BEAR: was uptrend,  price closes below last swing low  → reversal
    """
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
        c = bars[i]["close"]

        up   = lsh > psh and lsl > psl
        down = lsh < psh and lsl < psl

        prev_close = bars[i-1]["close"]

        if up and c > lsh and prev_close <= lsh:
            out.append(dict(bar_idx=i, bar=bars[i], pattern="BOS_BULL",
                            level=lsh, implied="BULL"))
        elif down and c < lsl and prev_close >= lsl:
            out.append(dict(bar_idx=i, bar=bars[i], pattern="BOS_BEAR",
                            level=lsl, implied="BEAR"))
        elif down and c > lsh and prev_close <= lsh:
            out.append(dict(bar_idx=i, bar=bars[i], pattern="MSS_BULL",
                            level=lsh, implied="BULL"))
        elif up and c < lsl and prev_close >= lsl:
            out.append(dict(bar_idx=i, bar=bars[i], pattern="MSS_BEAR",
                            level=lsl, implied="BEAR"))
    return out


def judas_swing(bars):
    """
    Judas Swing: opening 15-bar move in one direction, followed by reversal.
    The opening move traps retail. The reversal is the institutional direction.
    Entry: at bar 15 (09:30 IST), direction = opposite of opening move.

    JUDAS_BEAR: opened up > JUDAS_MIN_PCT, then reversed → real move is DOWN
    JUDAS_BULL: opened down > JUDAS_MIN_PCT, then reversed → real move is UP
    """
    out = []
    if len(bars) < 46:
        return out

    open_p     = bars[0]["open"]
    first15    = bars[:15]
    close15    = bars[14]["close"]
    opening_mv = pct(open_p, close15)

    if abs(opening_mv) < JUDAS_MIN_PCT:
        return out

    reversal_bars = bars[15:45]
    if not reversal_bars:
        return out

    if opening_mv > 0:
        # Opened up — Judas if reversal low is below 50% of the opening move
        rev_low = min(b["low"] for b in reversal_bars)
        if pct(close15, rev_low) <= -opening_mv * 0.50:
            out.append(dict(bar_idx=14, bar=bars[14], pattern="JUDAS_BEAR",
                            opening_mv_pct=opening_mv, implied="BEAR"))
    else:
        rev_high = max(b["high"] for b in reversal_bars)
        if pct(close15, rev_high) >= abs(opening_mv) * 0.50:
            out.append(dict(bar_idx=14, bar=bars[14], pattern="JUDAS_BULL",
                            opening_mv_pct=opening_mv, implied="BULL"))
    return out


def ote(bars, swings, min_swing=MIN_SWING_PCT):
    """
    Optimal Trade Entry — Fibonacci 61.8%-78.6% retracement.
    After a significant swing, price retraces into OTE zone.
    Entry in OTE zone, direction = continuation of prior swing.

    BULL_OTE: swing was up, retrace to 61.8-78.6% → continue BULL
    BEAR_OTE: swing was down, retrace to 61.8-78.6% → continue BEAR
    """
    out = []
    n = len(bars)
    done = set()

    highs = [(idx, p) for idx, t, p in swings if t == "HIGH"]
    lows  = [(idx, p) for idx, t, p in swings if t == "LOW"]

    # Bearish OTE: SH → SL → retrace up into OTE zone → continue BEAR
    for h_idx, h_p in highs:
        nx_lows = [(idx, p) for idx, p in lows if idx > h_idx]
        if not nx_lows:
            continue
        l_idx, l_p = nx_lows[0]
        if abs(pct(h_p, l_p)) < min_swing:
            continue
        rng = h_p - l_p
        z_lo = l_p + rng * OTE_FIB_LO
        z_hi = l_p + rng * OTE_FIB_HI
        for i in range(l_idx+1, min(l_idx+40, n)):
            if bars[i]["high"] >= z_lo and bars[i]["low"] <= z_hi:
                key = (h_idx, l_idx)
                if key not in done:
                    done.add(key)
                    out.append(dict(bar_idx=i, bar=bars[i], pattern="BEAR_OTE",
                                    swing_pct=abs(pct(h_p, l_p)),
                                    ote_lo=z_lo, ote_hi=z_hi, implied="BEAR"))
                break

    # Bullish OTE: SL → SH → retrace down into OTE zone → continue BULL
    for l_idx, l_p in lows:
        nx_highs = [(idx, p) for idx, p in highs if idx > l_idx]
        if not nx_highs:
            continue
        h_idx, h_p = nx_highs[0]
        if abs(pct(l_p, h_p)) < min_swing:
            continue
        rng = h_p - l_p
        z_hi = h_p - rng * OTE_FIB_LO
        z_lo = h_p - rng * OTE_FIB_HI
        for i in range(h_idx+1, min(h_idx+40, n)):
            if bars[i]["low"] <= z_hi and bars[i]["high"] >= z_lo:
                key = (l_idx, h_idx)
                if key not in done:
                    done.add(key)
                    out.append(dict(bar_idx=i, bar=bars[i], pattern="BULL_OTE",
                                    swing_pct=abs(pct(l_p, h_p)),
                                    ote_lo=z_lo, ote_hi=z_hi, implied="BULL"))
                break
    return out


def kill_zones(bars):
    """
    Indian market kill zones — time buckets for institutional activity analysis.
    Returns dict of zone_label → list of bars in that zone.
    """
    zones = {
        "09:15-09:45 OPEN_RANGE": [],
        "09:45-11:00 MORNING"   : [],
        "11:00-13:00 MIDDAY"    : [],
        "13:00-14:30 AFTERNOON" : [],
        "14:30-15:30 POWER_HOUR": [],
    }
    for b in bars:
        t = bar_t(b)
        if   t < dtime(9,  45): zones["09:15-09:45 OPEN_RANGE"].append(b)
        elif t < dtime(11,  0): zones["09:45-11:00 MORNING"].append(b)
        elif t < dtime(13,  0): zones["11:00-13:00 MIDDAY"].append(b)
        elif t < dtime(14, 30): zones["13:00-14:30 AFTERNOON"].append(b)
        else:                   zones["14:30-15:30 POWER_HOUR"].append(b)
    return zones


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
            return "       n/a      "
        filled = int(p / 10)
        flag = " ◄EDGE" if p >= 60 else ("  ▼INV" if p < 40 else "      ")
        return f"{'▓'*filled}{'░'*(10-filled)} {p:4.1f}%{flag}"


def print_table(title, buckets, min_n=15):
    print(f"\n{'='*120}")
    print(f"  {title}")
    print(f"{'='*120}")
    print(f"  {'Pattern':<30} {'N':>6}   {'T+15m PIA':<22}  {'T+30m PIA':<22}  {'T+60m PIA':<22}")
    print(f"  {'-'*110}")
    rows = [(k, v) for k, v in buckets.items() if v.n >= min_n]
    rows.sort(key=lambda x: x[1].pia(30) or 0, reverse=True)
    for label, b in rows:
        print(f"  {label:<30} {b.n:>6}   {b.fmt(15):<22}  {b.fmt(30):<22}  {b.fmt(60):<22}")
    if not rows:
        print("  (no patterns with sufficient N)")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("Fetching instrument IDs...")
    inst = {r["symbol"]: r["id"] for r in
            sb.table("instruments").select("id, symbol").execute().data}

    all_results  = {}   # symbol → pattern_label → Bucket
    kz_results   = defaultdict(Bucket)   # "SYMBOL zone" → Bucket (large moves)
    kz_all_bars  = defaultdict(Bucket)   # "SYMBOL zone" → Bucket (all bars)

    for symbol in ["NIFTY", "SENSEX"]:
        log(f"\n── {symbol} ──────────────────────────────────────────────")
        log("  Loading OHLC bars...")
        all_bars = fetch_ohlc(sb, inst[symbol])
        log(f"  {len(all_bars):,} bars")

        sessions    = sessions_from_bars(all_bars)
        dates       = sorted(sessions.keys())
        pat_buckets = defaultdict(Bucket)
        total_pats  = 0

        for i, d in enumerate(dates):
            bars = sessions[d]
            if len(bars) < 30:
                continue

            # Previous session reference levels
            pdh = pdl = None
            if i > 0:
                pb = sessions[dates[i-1]]
                pdh = max(b["high"] for b in pb)
                pdl = min(b["low"]  for b in pb)

            # Swing detection
            sw = find_swings(bars)

            # Run all detectors
            obs_list = order_blocks(bars)
            patterns = (
                fvg(bars)
                + obs_list
                + breaker_blocks(bars, obs_list)
                + liquidity_sweeps(bars, pdh, pdl)
                + mss_bos(bars, sw)
                + judas_swing(bars)
                + ote(bars, sw)
            )

            # Score each pattern against actual outcomes
            for pat in patterns:
                outcomes = measure(all_bars, pat["bar"], pat["implied"])
                pat_buckets[pat["pattern"]].add(outcomes)
                total_pats += 1

            # Kill zone: measure T+30m move direction for each bar by zone
            for zone_label, zone_bars in kill_zones(bars).items():
                key_all   = f"{symbol} {zone_label} [all bars]"
                key_large = f"{symbol} {zone_label} [large moves >0.3%]"
                for b in zone_bars:
                    if not in_session(b["bar_ts"], 30):
                        continue
                    xp = nearest_price(all_bars, b["bar_ts"] + timedelta(minutes=30))
                    if xp is None:
                        continue
                    mv = pct(b["close"], xp)
                    # For all-bars bucket: track BEAR accuracy (any pattern)
                    kz_all_bars[key_all].add({30: mv < 0, 15: None, 60: None})
                    if abs(mv) >= 0.30:
                        kz_results[key_large].add({30: mv < 0, 15: None, 60: None})

        all_results[symbol] = pat_buckets
        log(f"  {total_pats:,} pattern occurrences detected across {len(dates)} sessions")

    # ── Merge ─────────────────────────────────────────────────────────
    combined = defaultdict(Bucket)
    for symbol in ["NIFTY", "SENSEX"]:
        for pat_type, bucket in all_results[symbol].items():
            cb = combined[pat_type]
            cb.n += bucket.n
            for h in HORIZONS:
                cb.correct[h] += bucket.correct[h]
                cb.valid[h]   += bucket.valid[h]

    # ── Output ────────────────────────────────────────────────────────
    print("\n" + "=" * 120)
    print("  MERDIAN EXPERIMENT 10 — ICT GEOMETRIC PATTERN DETECTION")
    print("  Period: Apr 2025 – Mar 2026  |  NIFTY (247 sessions) + SENSEX (246 sessions)")
    print("  PIA = Pattern-Implied Accuracy: % of time spot moved in pattern-predicted direction")
    print("  ◄EDGE = PIA > 60% (tradeable edge)  |  ▼INV = PIA < 40% (inverse edge)  |  blank = noise")
    print("  Patterns sorted by T+30m PIA descending")
    print("=" * 120)

    print_table("ALL PATTERNS — NIFTY + SENSEX COMBINED", combined, min_n=20)
    print_table("NIFTY", all_results["NIFTY"], min_n=10)
    print_table("SENSEX", all_results["SENSEX"], min_n=10)

    # Kill zone large move distribution
    print(f"\n{'='*120}")
    print("  KILL ZONE ANALYSIS — T+30m bearish hit rate by time zone")
    print("  Tells you WHEN the market is directional — not whether it goes up or down")
    print(f"{'='*120}")
    print(f"  {'Zone':<50} {'N all bars':>10}  {'Bear%':>8}  {'N large':>10}  {'Bear% large':>12}")
    print(f"  {'-'*95}")

    for symbol in ["NIFTY", "SENSEX"]:
        print(f"\n  {symbol}")
        for zone in ["09:15-09:45 OPEN_RANGE", "09:45-11:00 MORNING",
                     "11:00-13:00 MIDDAY", "13:00-14:30 AFTERNOON",
                     "14:30-15:30 POWER_HOUR"]:
            key_all   = f"{symbol} {zone} [all bars]"
            key_large = f"{symbol} {zone} [large moves >0.3%]"
            ba = kz_all_bars.get(key_all)
            bl = kz_results.get(key_large)
            n_all   = ba.n        if ba else 0
            p_all   = ba.pia(30)  if ba else None
            n_large = bl.n        if bl else 0
            p_large = bl.pia(30)  if bl else None
            pa_str  = f"{p_all:5.1f}%"   if p_all   is not None else "   n/a"
            pl_str  = f"{p_large:5.1f}%" if p_large is not None else "    n/a"
            print(f"  {zone:<50} {n_all:>10,}  {pa_str:>8}  {n_large:>10,}  {pl_str:>12}")

    print(f"\n{'='*120}")
    print("  PATTERN GLOSSARY")
    print("  BEAR/BULL_FVG      Fair Value Gap — 3-bar imbalance, price fills the gap")
    print("  BEAR/BULL_OB       Order Block — institutional candle before significant move")
    print("  BEAR/BULL_BREAKER  Breaker Block — violated OB that flips to opposite role")
    print("  BEAR_SWEEP_PDH     Liquidity sweep above previous day high → reversal down")
    print("  BULL_SWEEP_PDL     Liquidity sweep below previous day low  → reversal up")
    print("  BEAR_SWEEP_EQH     Equal-highs sweep → reversal down")
    print("  BULL_SWEEP_EQL     Equal-lows sweep  → reversal up")
    print("  BOS_BULL/BEAR      Break of Structure — trend continuation signal")
    print("  MSS_BULL/BEAR      Market Structure Shift — trend reversal signal")
    print("  JUDAS_BEAR/BULL    Judas Swing — opening trap, fade the opening move")
    print("  BEAR/BULL_OTE      Optimal Trade Entry — Fibonacci 61.8-78.6% retracement")
    print(f"{'='*120}\n")


if __name__ == "__main__":
    main()
