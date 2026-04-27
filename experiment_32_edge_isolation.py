"""
experiment_32_edge_isolation.py

Purpose
-------
Find buckets of ICT detections where edge is real and replicable.

Exp 31 showed compendium WRs (86-100%) don't replicate at 48% baseline,
but average PnL is positive on most NIFTY buckets and very large on
some (e.g., BULL_FVG TIER2 LOW = +30.83% avg/trade). That suggests
edge exists but is NOT in the buckets the compendium named — or it's
in narrower sub-buckets we haven't isolated yet.

This experiment stratifies the same trade population by a richer set
of ambient conditions and finds the buckets where edge concentrates.

Methodology
-----------
1. Re-run Exp 31's detector + PnL calc, capturing additional features
   per trade:
     - dte (days to expiry)
     - day_of_week
     - is_expiry_day (Tuesday for NIFTY/SENSEX)
     - atm_iv_level at entry (LOW <12, NORM 12-18, HIGH >=18)
     - pcr_bucket at entry (from pcr_5m: <0.8 / 0.8-1.2 / >1.2)
     - or_range_pct (computed from first 3 5m bars of day)
     - prior_day_move_pct (computed per symbol per day)
     - ret_session_pct at entry (running session return)

2. Train/Held-out split:
     TRAIN:    2025-04-01 to 2026-01-14 (~190 days)
     HELDOUT:  2026-01-15 to 2026-04-24 (~70 days)

3. Pass 1: single-feature stratification on TRAIN.
   For each feature, bucket trades, compute WR + avg PnL per bucket.
   Surface buckets with N>=20 AND (WR>=60% OR avg_pnl>=10%).

4. Pass 2: two-feature interactions on top single features.
   Cross top 5 single features pairwise, find bucket-combos with
   N>=15 AND clear lift over either parent bucket.

5. Pass 3: held-out validation.
   Take top 5 rules from Pass 2 (or Pass 1 if 2 yields nothing).
   Re-evaluate each rule on HELDOUT data. Report:
     - HELDOUT N
     - HELDOUT WR
     - HELDOUT avg PnL
     - replicates? (TRUE if held-out WR within 10pp of train AND
                    held-out N >= 10 AND held-out avg_pnl > 0)

Decision rule
-------------
A rule that survives held-out validation with:
  - N_heldout >= 10
  - WR_heldout >= 60%
  - avg_pnl_heldout > 0
  - WR drop from train to heldout <= 15pp
is treated as a "candidate replicable edge" worth wiring into MERDIAN.

If multiple rules survive: rank by held-out total PnL.
If zero rules survive: edge is not isolated; conclude no replicable
edge in current data within the feature set tested.

Run
---
    python experiment_32_edge_isolation.py
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from typing import Optional, Callable
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

IST = ZoneInfo("Asia/Kolkata")
UTC = timezone.utc

# --- experiment config -------------------------------------------------

DATE_FROM = "2025-04-01"
DATE_TO   = "2026-04-24"
TZ_ERA_BOUNDARY = date(2026, 4, 7)
PAGE_SIZE = 1000

# Train/held-out split
HELDOUT_START = date(2026, 1, 15)

# ICT detector constants (mirror Exp 31 / detect_ict_patterns.py)
OB_MIN_MOVE_PCT   = 0.40
FVG_MIN_PCT       = 0.10
JUDAS_MIN_PCT     = 0.25
SWEEP_LOOKBACK    = 5
SWEEP_MIN_PCT     = 0.10
STRONG_IMPULSE    = 0.30
LOOKBACK_BARS     = 3

# Time zones (IST minutes-of-day)
SESSION_START = 9 * 60 + 15
MORNING_START = 10 * 60
MIDDAY_START  = 11 * 60 + 30
AFTNOON_START = 13 * 60 + 30
SESSION_END   = 15 * 60 + 30
POWER_HOUR    = 15 * 60

# Trade simulation
EXIT_MINUTES = 30
TIER1_MULT = 1.5
TIER2_MULT = 1.0

# Pass 1 thresholds for "interesting bucket"
P1_MIN_N = 20
P1_MIN_WR = 60.0
P1_MIN_AVG_PNL = 10.0  # %

# Pass 2 thresholds
P2_MIN_N = 15

# Pass 3 (held-out) thresholds
P3_MIN_HELDOUT_N = 10
P3_MIN_HELDOUT_WR = 60.0
P3_MAX_WR_DROP = 15.0  # train-to-heldout WR drop in pp

SYMBOLS = ["NIFTY", "SENSEX"]


# --- data structures ---------------------------------------------------

@dataclass
class Bar1m:
    ts_ist: datetime
    trade_date: date
    open: float
    high: float
    low: float
    close: float


@dataclass
class Bar5m:
    bucket_start_ist: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass
class HTFZone:
    zone_id: str
    timeframe: str
    direction: int
    zone_high: float
    zone_low: float
    valid_from: date
    valid_to: date


@dataclass
class Trade:
    # Identity
    symbol: str
    trade_date: date
    bar_ts_ist: datetime
    is_heldout: bool

    # Pattern
    pattern_type: str
    direction: int
    opt_type: str
    tier: str
    mtf_context: str
    tz_label: str
    mom_aligned: bool
    impulse_strong: bool

    # Spot/option
    spot_at_entry: float
    entry_premium: float
    exit_premium_t30: float
    pnl_pct_t30: float
    pnl_pct_sized: float
    outcome_t30: str  # WIN / LOSS

    # Ambient features
    dte: Optional[int]
    day_of_week: int  # 0=Mon
    is_expiry_day: bool
    atm_iv_level: str  # LOW / NORM / HIGH
    pcr_bucket: str  # PCR_LOW / PCR_NEUTRAL / PCR_HIGH / UNKNOWN
    or_range_bucket: str  # OR_TIGHT / OR_NORMAL / OR_WIDE / UNKNOWN
    prior_day_move_bucket: str  # PD_DOWN / PD_FLAT / PD_UP / UNKNOWN
    ret_session_bucket: str  # RS_DOWN / RS_FLAT / RS_UP


# --- helpers -----------------------------------------------------------

def pct(a: float, b: float) -> float:
    return 100.0 * (b - a) / a if a else 0.0


def canonicalize_ts_to_ist(bar_ts_iso: str, trade_date: date) -> datetime:
    raw = datetime.fromisoformat(bar_ts_iso)
    if trade_date < TZ_ERA_BOUNDARY:
        if raw.tzinfo is not None:
            raw = raw.replace(tzinfo=None)
        return raw.replace(tzinfo=IST)
    if raw.tzinfo is None:
        raw = raw.replace(tzinfo=UTC)
    return raw.astimezone(IST)


def minutes_of_day(ts_ist: datetime) -> int:
    return ts_ist.hour * 60 + ts_ist.minute


def in_session(ts_ist: datetime) -> bool:
    m = minutes_of_day(ts_ist)
    return SESSION_START <= m < SESSION_END


def time_zone_label(ts_ist: datetime) -> str:
    m = minutes_of_day(ts_ist)
    if SESSION_START <= m < MORNING_START:
        return "OPEN"
    if MORNING_START <= m < MIDDAY_START:
        return "MORNING"
    if MIDDAY_START <= m < AFTNOON_START:
        return "MIDDAY"
    if AFTNOON_START <= m <= SESSION_END:
        return "AFTNOON"
    return "OTHER"


def is_power_hour(ts_ist: datetime) -> bool:
    return minutes_of_day(ts_ist) >= POWER_HOUR


def bucket_iv(iv: float) -> str:
    if iv < 12.0:
        return "LOW_IV"
    if iv < 18.0:
        return "NORM_IV"
    return "HIGH_IV"


def bucket_pcr(pcr: Optional[float]) -> str:
    if pcr is None:
        return "PCR_UNKNOWN"
    if pcr < 0.8:
        return "PCR_LOW"
    if pcr < 1.2:
        return "PCR_NEUTRAL"
    return "PCR_HIGH"


def bucket_or_range(or_pct: Optional[float]) -> str:
    if or_pct is None:
        return "OR_UNKNOWN"
    if or_pct < 0.30:
        return "OR_TIGHT"
    if or_pct < 0.60:
        return "OR_NORMAL"
    return "OR_WIDE"


def bucket_signed(value: Optional[float], thresh: float, low: str, mid: str, high: str) -> str:
    if value is None:
        return f"{mid}_UNKNOWN"
    if value < -thresh:
        return low
    if value > thresh:
        return high
    return mid


def bucket_pd_move(pct_val: Optional[float]) -> str:
    return bucket_signed(pct_val, 0.30, "PD_DOWN", "PD_FLAT", "PD_UP")


def bucket_ret_session(rs_pct: Optional[float]) -> str:
    return bucket_signed(rs_pct, 0.10, "RS_DOWN", "RS_FLAT", "RS_UP")


# --- data loaders ------------------------------------------------------

def fetch_1m_bars(sb, symbol: str) -> list[Bar1m]:
    inst = sb.table("instruments").select("id").eq("symbol", symbol).execute().data
    if not inst:
        raise RuntimeError(f"instrument not found: {symbol}")
    inst_id = inst[0]["id"]
    out: list[Bar1m] = []
    offset = 0
    while True:
        rows = (
            sb.table("hist_spot_bars_1m")
            .select("bar_ts, trade_date, open, high, low, close")
            .eq("instrument_id", inst_id)
            .gte("trade_date", DATE_FROM)
            .lte("trade_date", DATE_TO)
            .order("bar_ts")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute().data
        )
        if not rows:
            break
        for r in rows:
            td = date.fromisoformat(r["trade_date"])
            ts_ist = canonicalize_ts_to_ist(r["bar_ts"], td)
            if not in_session(ts_ist):
                continue
            out.append(Bar1m(
                ts_ist=ts_ist, trade_date=td,
                open=float(r["open"]), high=float(r["high"]),
                low=float(r["low"]), close=float(r["close"]),
            ))
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return out


def fetch_w_zones(sb, symbol: str) -> list[HTFZone]:
    rows = (
        sb.table("ict_htf_zones")
        .select("id, timeframe, direction, zone_high, zone_low, valid_from, valid_to")
        .eq("symbol", symbol)
        .eq("timeframe", "W")
        .execute().data
    )
    out = []
    for r in rows:
        out.append(HTFZone(
            zone_id=r["id"], timeframe=r["timeframe"],
            direction=int(r["direction"]),
            zone_high=float(r["zone_high"]), zone_low=float(r["zone_low"]),
            valid_from=date.fromisoformat(r["valid_from"]),
            valid_to=date.fromisoformat(r["valid_to"]),
        ))
    return out


def fetch_atm_option_bars(sb, symbol: str) -> dict[tuple[date, datetime], dict]:
    out = {}
    offset = 0
    while True:
        rows = (
            sb.table("hist_atm_option_bars_5m")
            .select("trade_date, bar_ts, atm_strike, expiry_date, dte, "
                    "ce_close, pe_close, ce_iv_close, pe_iv_close, "
                    "spot_close, pcr_5m")
            .eq("symbol", symbol)
            .gte("trade_date", DATE_FROM)
            .lte("trade_date", DATE_TO)
            .order("bar_ts")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute().data
        )
        if not rows:
            break
        for r in rows:
            td = date.fromisoformat(r["trade_date"])
            ts_ist = canonicalize_ts_to_ist(r["bar_ts"], td)
            bucket_min = (ts_ist.minute // 5) * 5
            bucket = ts_ist.replace(minute=bucket_min, second=0, microsecond=0)
            out[(td, bucket)] = r
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return out


# --- aggregation -------------------------------------------------------

def aggregate_1m_to_5m(bars: list[Bar1m]) -> list[Bar5m]:
    if not bars:
        return []
    grouped: dict[datetime, list[Bar1m]] = defaultdict(list)
    for b in bars:
        bucket_min = (b.ts_ist.minute // 5) * 5
        bucket = b.ts_ist.replace(minute=bucket_min, second=0, microsecond=0)
        grouped[bucket].append(b)
    out: list[Bar5m] = []
    for bucket, bs in sorted(grouped.items()):
        bs.sort(key=lambda x: x.ts_ist)
        out.append(Bar5m(
            bucket_start_ist=bucket,
            open=bs[0].open,
            high=max(b.high for b in bs),
            low=min(b.low for b in bs),
            close=bs[-1].close,
        ))
    return out


# --- detection logic ---------------------------------------------------

def detect_obs(bars: list[Bar5m]) -> list[tuple[int, str, int]]:
    results = []
    seen = set()
    n = len(bars)
    for i in range(n - 6):
        end_idx = min(i + 5, n - 1)
        if i == end_idx:
            continue
        mv = pct(bars[i].close, bars[end_idx].close)
        if mv <= -OB_MIN_MOVE_PCT:
            for j in range(i, max(i - 6, -1), -1):
                if bars[j].close > bars[j].open and j not in seen:
                    seen.add(j)
                    results.append((j, "BEAR_OB", -1))
                    break
        elif mv >= OB_MIN_MOVE_PCT:
            for j in range(i, max(i - 6, -1), -1):
                if bars[j].close < bars[j].open and j not in seen:
                    seen.add(j)
                    results.append((j, "BULL_OB", +1))
                    break
    return results


def detect_fvgs(bars: list[Bar5m]) -> list[tuple[int, str, int]]:
    results = []
    min_g = FVG_MIN_PCT / 100.0
    for i in range(1, len(bars) - 1):
        prev, curr, nxt = bars[i - 1], bars[i], bars[i + 1]
        ref = curr.close
        if prev.high < nxt.low and (nxt.low - prev.high) / ref >= min_g:
            results.append((i, "BULL_FVG", +1))
    return results


def detect_judas(bars: list[Bar5m]) -> list[tuple[int, str, int]]:
    if len(bars) < 46:
        return []
    mv = pct(bars[0].open, bars[14].close)
    if abs(mv) < JUDAS_MIN_PCT:
        return []
    if mv < 0:
        rev = bars[15:45]
        max_rec = pct(bars[14].close, max(b.high for b in rev))
        if max_rec >= abs(mv) * 0.50:
            return [(14, "JUDAS_BULL", +1)]
    return []


def compute_sequence_features(
    bars: list[Bar5m], idx: int, direction: int
) -> tuple[bool, bool]:
    mom_aligned = False
    if idx >= LOOKBACK_BARS:
        preceding = bars[idx - LOOKBACK_BARS:idx]
        counter = sum(
            1 for b in preceding
            if (direction == +1 and b.close < b.open) or
               (direction == -1 and b.close > b.open)
        )
        mom_aligned = counter >= 2
    impulse_strong = False
    if idx >= LOOKBACK_BARS:
        preceding = bars[idx - LOOKBACK_BARS:idx]
        total = sum(abs(pct(b.open, b.close)) for b in preceding)
        impulse_strong = total >= STRONG_IMPULSE
    return mom_aligned, impulse_strong


def assign_tier(
    pattern_type: str,
    mom_aligned: bool,
    impulse_strong: bool,
    tz_label: str,
) -> tuple[str, float]:
    if pattern_type == "BEAR_OB":
        if tz_label == "AFTNOON":
            return "SKIP", 0.0
        if impulse_strong:
            return "SKIP", 0.0
        if mom_aligned and tz_label == "MORNING":
            return "TIER1", TIER1_MULT
        return "TIER2", TIER2_MULT
    if pattern_type == "BULL_OB":
        if impulse_strong:
            return "TIER2", TIER2_MULT
        if tz_label == "OPEN":
            return "SKIP", 0.0
        if tz_label in ("MORNING", "AFTNOON"):
            return "TIER1", TIER1_MULT
        return "TIER2", TIER2_MULT
    return "TIER2", TIER2_MULT


def get_mtf_context(spot: float, direction: int, w_zones_active: list[HTFZone]) -> str:
    for z in w_zones_active:
        if z.direction != direction:
            continue
        if z.zone_low <= spot <= z.zone_high:
            return "VERY_HIGH"
    return "LOW"


# --- daily features ----------------------------------------------------

def compute_or_range_pct(bars_5m: list[Bar5m]) -> Optional[float]:
    """Opening range = (max high - min low) / open over first 3 5m bars
    (09:15-09:29 IST). Returns % or None."""
    open_bars = [b for b in bars_5m
                 if minutes_of_day(b.bucket_start_ist) < 9 * 60 + 30]
    if len(open_bars) < 1:
        return None
    open_bars.sort(key=lambda b: b.bucket_start_ist)
    first = open_bars[0]
    if first.open == 0:
        return None
    or_h = max(b.high for b in open_bars)
    or_l = min(b.low for b in open_bars)
    return 100.0 * (or_h - or_l) / first.open


def compute_prior_day_close_first_open(by_date: dict[date, list[Bar1m]]) -> dict[date, Optional[float]]:
    """Map each trade_date -> (prior day close, this day open) PnL."""
    out = {}
    sorted_dates = sorted(by_date.keys())
    for i, d in enumerate(sorted_dates):
        if i == 0:
            out[d] = None
            continue
        prev = sorted_dates[i - 1]
        prev_bars = by_date[prev]
        curr_bars = by_date[d]
        if not prev_bars or not curr_bars:
            out[d] = None
            continue
        prev_close = prev_bars[-1].close
        curr_open = curr_bars[0].open
        if prev_close == 0:
            out[d] = None
            continue
        # Use prior day open->close as the prior_day_move
        prev_open = prev_bars[0].open
        if prev_open == 0:
            out[d] = None
            continue
        out[d] = pct(prev_open, prev_close)
    return out


def compute_session_open(bars_5m: list[Bar5m]) -> Optional[float]:
    if not bars_5m:
        return None
    sorted_bars = sorted(bars_5m, key=lambda b: b.bucket_start_ist)
    return sorted_bars[0].open


# --- per-day replay ----------------------------------------------------

def replay_day(
    bars_5m: list[Bar5m],
    trade_date: date,
    symbol: str,
    w_zones_for_date: list[HTFZone],
    options_lookup: dict,
    or_range_pct: Optional[float],
    prior_day_move_pct: Optional[float],
    session_open: Optional[float],
) -> list[Trade]:
    candidates = []
    candidates.extend(detect_obs(bars_5m))
    candidates.extend(detect_fvgs(bars_5m))
    candidates.extend(detect_judas(bars_5m))

    trades: list[Trade] = []

    for idx, pattern, direction in candidates:
        bar = bars_5m[idx]
        if not in_session(bar.bucket_start_ist):
            continue
        if is_power_hour(bar.bucket_start_ist):
            continue
        tz_label_v = time_zone_label(bar.bucket_start_ist)
        mom_aligned, impulse_strong = compute_sequence_features(bars_5m, idx, direction)
        tier, mult = assign_tier(pattern, mom_aligned, impulse_strong, tz_label_v)
        if tier == "SKIP":
            continue
        opt_type = "CE" if direction == +1 else "PE"
        mtf_ctx = get_mtf_context(bar.close, direction, w_zones_for_date)

        # PnL lookup
        entry_key = (trade_date, bar.bucket_start_ist)
        entry_row = options_lookup.get(entry_key)
        if not entry_row:
            continue
        exit_ts = bar.bucket_start_ist + timedelta(minutes=EXIT_MINUTES)
        exit_bucket = exit_ts.replace(
            minute=(exit_ts.minute // 5) * 5, second=0, microsecond=0,
        )
        exit_row = options_lookup.get((trade_date, exit_bucket))
        if not exit_row:
            for skip in range(1, 7):
                ex2 = exit_bucket - timedelta(minutes=5 * skip)
                if (trade_date, ex2) in options_lookup:
                    exit_row = options_lookup[(trade_date, ex2)]
                    break
            if not exit_row:
                continue

        if opt_type == "CE":
            entry_p = float(entry_row.get("ce_close") or 0)
            exit_p = float(exit_row.get("ce_close") or 0)
            iv_at_entry = float(entry_row.get("ce_iv_close") or 0)
        else:
            entry_p = float(entry_row.get("pe_close") or 0)
            exit_p = float(exit_row.get("pe_close") or 0)
            iv_at_entry = float(entry_row.get("pe_iv_close") or 0)

        if entry_p <= 0:
            continue
        pnl_pct = pct(entry_p, exit_p)
        pnl_sized = pnl_pct * mult
        outcome = "WIN" if pnl_pct > 0 else "LOSS"

        # Ambient features
        dte_val = entry_row.get("dte")
        if dte_val is not None:
            dte_val = int(dte_val)
        pcr_val = entry_row.get("pcr_5m")
        if pcr_val is not None:
            pcr_val = float(pcr_val)

        ret_session_pct = None
        if session_open and session_open > 0:
            ret_session_pct = pct(session_open, bar.close)

        trades.append(Trade(
            symbol=symbol, trade_date=trade_date, bar_ts_ist=bar.bucket_start_ist,
            is_heldout=(trade_date >= HELDOUT_START),
            pattern_type=pattern, direction=direction, opt_type=opt_type,
            tier=tier, mtf_context=mtf_ctx, tz_label=tz_label_v,
            mom_aligned=mom_aligned, impulse_strong=impulse_strong,
            spot_at_entry=bar.close, entry_premium=entry_p,
            exit_premium_t30=exit_p, pnl_pct_t30=pnl_pct, pnl_pct_sized=pnl_sized,
            outcome_t30=outcome,
            dte=dte_val, day_of_week=trade_date.weekday(),
            is_expiry_day=(trade_date.weekday() == 1),  # Tuesday
            atm_iv_level=bucket_iv(iv_at_entry) if iv_at_entry > 0 else "IV_UNKNOWN",
            pcr_bucket=bucket_pcr(pcr_val),
            or_range_bucket=bucket_or_range(or_range_pct),
            prior_day_move_bucket=bucket_pd_move(prior_day_move_pct),
            ret_session_bucket=bucket_ret_session(ret_session_pct),
        ))

    return trades


def run_for_symbol(sb, symbol: str) -> list[Trade]:
    print(f"\n=== {symbol} ===")
    print("  Fetching 1m bars...")
    bars = fetch_1m_bars(sb, symbol)
    print(f"  Loaded {len(bars):,} 1m bars")
    print("  Fetching W zones + option bars...")
    w_zones = fetch_w_zones(sb, symbol)
    options_lookup = fetch_atm_option_bars(sb, symbol)
    print(f"  Loaded {len(w_zones)} W zones, {len(options_lookup):,} option bars")

    by_date: dict[date, list[Bar1m]] = defaultdict(list)
    for b in bars:
        by_date[b.trade_date].append(b)

    pd_move_lookup = compute_prior_day_close_first_open(by_date)

    print(f"  Replaying {len(by_date)} days...")
    all_trades: list[Trade] = []
    for d in sorted(by_date.keys()):
        bars_5m = aggregate_1m_to_5m(by_date[d])
        if len(bars_5m) < 10:
            continue
        w_active = [z for z in w_zones if z.valid_from <= d <= z.valid_to]
        or_pct = compute_or_range_pct(bars_5m)
        sess_open = compute_session_open(bars_5m)
        pd_move = pd_move_lookup.get(d)
        trades = replay_day(bars_5m, d, symbol, w_active, options_lookup,
                            or_pct, pd_move, sess_open)
        all_trades.extend(trades)

    print(f"  Trades with PnL: {len(all_trades)}")
    return all_trades


# --- stratified analysis -----------------------------------------------

def bucket_stats(trades: list[Trade]) -> tuple[int, int, int, float, float, float]:
    """Returns (n, wins, losses, wr, avg_pnl, total_pnl)."""
    n = len(trades)
    if n == 0:
        return 0, 0, 0, 0.0, 0.0, 0.0
    wins = sum(1 for t in trades if t.outcome_t30 == "WIN")
    losses = n - wins
    wr = 100.0 * wins / n
    total = sum(t.pnl_pct_t30 for t in trades)
    avg = total / n
    return n, wins, losses, wr, avg, total


def stratify_single(trades: list[Trade], feature_name: str, getter: Callable) -> dict:
    by_val: dict[str, list[Trade]] = defaultdict(list)
    for t in trades:
        by_val[str(getter(t))].append(t)
    return {val: bucket_stats(ts) for val, ts in by_val.items()}


def pass1_single_features(train: list[Trade]) -> list[tuple]:
    """Return list of (feature, value, n, wr, avg_pnl, total_pnl) for
    interesting buckets only."""
    features: list[tuple[str, Callable]] = [
        ("symbol", lambda t: t.symbol),
        ("pattern_type", lambda t: t.pattern_type),
        ("tier", lambda t: t.tier),
        ("mtf_context", lambda t: t.mtf_context),
        ("tz_label", lambda t: t.tz_label),
        ("mom_aligned", lambda t: t.mom_aligned),
        ("impulse_strong", lambda t: t.impulse_strong),
        ("dte_bucket", lambda t: "DTE_0_1" if t.dte is not None and t.dte <= 1
                                  else "DTE_2_3" if t.dte is not None and t.dte <= 3
                                  else "DTE_4PLUS" if t.dte is not None
                                  else "DTE_UNKNOWN"),
        ("day_of_week", lambda t: ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][t.day_of_week]),
        ("is_expiry_day", lambda t: t.is_expiry_day),
        ("atm_iv_level", lambda t: t.atm_iv_level),
        ("pcr_bucket", lambda t: t.pcr_bucket),
        ("or_range_bucket", lambda t: t.or_range_bucket),
        ("prior_day_move_bucket", lambda t: t.prior_day_move_bucket),
        ("ret_session_bucket", lambda t: t.ret_session_bucket),
        ("opt_type", lambda t: t.opt_type),
    ]
    interesting = []
    print("\n--- PASS 1: single-feature stratification on TRAIN ---")
    print(f"{'Feature':<22} {'Value':<22} {'N':>5} {'WR%':>7} {'AvgPnL%':>9} {'TotPnL%':>9}")
    print("-" * 78)
    for fname, getter in features:
        bs = stratify_single(train, fname, getter)
        for val, (n, w, l, wr, avg, total) in sorted(bs.items()):
            mark = ""
            if n >= P1_MIN_N and (wr >= P1_MIN_WR or avg >= P1_MIN_AVG_PNL):
                interesting.append((fname, val, n, wr, avg, total))
                mark = "  *"
            print(f"{fname:<22} {val:<22} {n:>5} {wr:>6.1f}% {avg:>8.2f}% {total:>8.1f}%{mark}")
    print(f"\n* = Interesting (N>={P1_MIN_N} AND (WR>={P1_MIN_WR}% OR avg>={P1_MIN_AVG_PNL}%))")
    return interesting


def pass2_two_feature_interactions(
    train: list[Trade],
    pass1_results: list[tuple],
) -> list[dict]:
    """Cross top features pairwise. Return rules with N >= P2_MIN_N
    AND meaningful lift over baseline."""
    # Pick top features by interesting bucket count
    feature_counts: dict[str, int] = defaultdict(int)
    for fname, _val, _n, _wr, _avg, _tot in pass1_results:
        feature_counts[fname] += 1
    top_features = sorted(feature_counts.keys(), key=lambda k: -feature_counts[k])[:5]
    if len(top_features) < 2:
        # fall back: include high-cardinality always-relevant ones
        top_features = ["pattern_type", "tier", "mtf_context", "atm_iv_level",
                        "ret_session_bucket"][:5]

    print(f"\n--- PASS 2: 2-feature interactions on top features: {top_features} ---")

    getters = {
        "symbol": lambda t: t.symbol,
        "pattern_type": lambda t: t.pattern_type,
        "tier": lambda t: t.tier,
        "mtf_context": lambda t: t.mtf_context,
        "tz_label": lambda t: t.tz_label,
        "mom_aligned": lambda t: t.mom_aligned,
        "impulse_strong": lambda t: t.impulse_strong,
        "dte_bucket": lambda t: ("DTE_0_1" if t.dte is not None and t.dte <= 1
                                  else "DTE_2_3" if t.dte is not None and t.dte <= 3
                                  else "DTE_4PLUS" if t.dte is not None
                                  else "DTE_UNKNOWN"),
        "day_of_week": lambda t: ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][t.day_of_week],
        "is_expiry_day": lambda t: t.is_expiry_day,
        "atm_iv_level": lambda t: t.atm_iv_level,
        "pcr_bucket": lambda t: t.pcr_bucket,
        "or_range_bucket": lambda t: t.or_range_bucket,
        "prior_day_move_bucket": lambda t: t.prior_day_move_bucket,
        "ret_session_bucket": lambda t: t.ret_session_bucket,
        "opt_type": lambda t: t.opt_type,
    }

    rules = []
    for i, f1 in enumerate(top_features):
        for f2 in top_features[i+1:]:
            g1, g2 = getters[f1], getters[f2]
            by_val: dict[tuple, list[Trade]] = defaultdict(list)
            for t in train:
                by_val[(str(g1(t)), str(g2(t)))].append(t)
            for (v1, v2), ts in by_val.items():
                n, w, l, wr, avg, total = bucket_stats(ts)
                if n >= P2_MIN_N and (wr >= P1_MIN_WR or avg >= P1_MIN_AVG_PNL):
                    rules.append({
                        "f1": f1, "v1": v1, "f2": f2, "v2": v2,
                        "n": n, "wr": wr, "avg": avg, "total": total,
                        "getters": (g1, g2),
                    })

    rules.sort(key=lambda r: -r["total"])
    print(f"{'Rule':<70} {'N':>5} {'WR%':>7} {'AvgPnL%':>9} {'TotPnL%':>9}")
    print("-" * 105)
    for r in rules[:25]:
        rule_str = f"{r['f1']}={r['v1']} & {r['f2']}={r['v2']}"
        print(f"{rule_str:<70} {r['n']:>5} {r['wr']:>6.1f}% {r['avg']:>8.2f}% {r['total']:>8.1f}%")
    return rules


def pass3_heldout_validation(
    rules: list[dict],
    heldout: list[Trade],
) -> list[dict]:
    """Re-evaluate top rules on held-out data."""
    print(f"\n--- PASS 3: held-out validation (>= {HELDOUT_START}) ---")
    print(f"Held-out total trades: {len(heldout)}")
    if not rules:
        print("No rules from Pass 2 to validate.")
        return []

    survivors = []
    print(f"\n{'Rule':<70} {'TrN':>4} {'TrWR':>6} {'HoN':>4} {'HoWR':>6} {'HoAvg':>7} {'HoTot':>8} {'?':>3}")
    print("-" * 115)
    for r in rules[:15]:  # top 15 from pass 2
        g1, g2 = r["getters"]
        v1, v2 = r["v1"], r["v2"]
        ho_trades = [t for t in heldout if str(g1(t)) == v1 and str(g2(t)) == v2]
        ho_n, ho_w, ho_l, ho_wr, ho_avg, ho_tot = bucket_stats(ho_trades)
        wr_drop = r["wr"] - ho_wr
        replicates = (
            ho_n >= P3_MIN_HELDOUT_N and
            ho_wr >= P3_MIN_HELDOUT_WR and
            ho_avg > 0 and
            wr_drop <= P3_MAX_WR_DROP
        )
        rule_str = f"{r['f1']}={r['v1']} & {r['f2']}={r['v2']}"
        flag = "YES" if replicates else "no"
        print(f"{rule_str:<70} {r['n']:>4} {r['wr']:>5.1f}% {ho_n:>4} {ho_wr:>5.1f}% {ho_avg:>6.2f}% {ho_tot:>7.1f}% {flag:>3}")
        if replicates:
            survivors.append({**r, "ho_n": ho_n, "ho_wr": ho_wr,
                              "ho_avg": ho_avg, "ho_total": ho_tot})

    print()
    if survivors:
        print(f"VALIDATED RULES ({len(survivors)}):")
        for r in sorted(survivors, key=lambda x: -x["ho_total"]):
            print(f"  - {r['f1']}={r['v1']} AND {r['f2']}={r['v2']}")
            print(f"      Train: N={r['n']} WR={r['wr']:.1f}% Avg={r['avg']:.2f}% Total={r['total']:.1f}%")
            print(f"      Heldout: N={r['ho_n']} WR={r['ho_wr']:.1f}% Avg={r['ho_avg']:.2f}% Total={r['ho_total']:.1f}%")
    else:
        print("No rules survived held-out validation. No replicable edge isolated in tested feature set.")

    return survivors


# --- main --------------------------------------------------------------

def main() -> int:
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    all_trades: list[Trade] = []
    for symbol in SYMBOLS:
        all_trades.extend(run_for_symbol(sb, symbol))

    print(f"\nTotal trades with PnL data: {len(all_trades)}")
    train = [t for t in all_trades if not t.is_heldout]
    heldout = [t for t in all_trades if t.is_heldout]
    print(f"  Train (< {HELDOUT_START}):    {len(train)}")
    print(f"  Heldout (>= {HELDOUT_START}): {len(heldout)}")

    # Baseline on train
    n, w, l, wr, avg, total = bucket_stats(train)
    print(f"\nTRAIN baseline: N={n} WR={wr:.1f}% Avg={avg:.2f}% Total={total:.1f}%")
    n, w, l, wr, avg, total = bucket_stats(heldout)
    print(f"HELDOUT baseline: N={n} WR={wr:.1f}% Avg={avg:.2f}% Total={total:.1f}%")

    p1 = pass1_single_features(train)
    p2 = pass2_two_feature_interactions(train, p1)
    p3 = pass3_heldout_validation(p2, heldout)

    # Write CSV of all trades for further offline analysis
    with open("experiment_32_trades.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "symbol", "trade_date", "bar_ts_ist", "is_heldout",
            "pattern_type", "tier", "mtf_context", "tz_label",
            "mom_aligned", "impulse_strong", "opt_type",
            "spot_at_entry", "entry_premium", "exit_premium_t30",
            "pnl_pct_t30", "pnl_pct_sized", "outcome_t30",
            "dte", "day_of_week", "is_expiry_day",
            "atm_iv_level", "pcr_bucket", "or_range_bucket",
            "prior_day_move_bucket", "ret_session_bucket",
        ])
        for t in all_trades:
            writer.writerow([
                t.symbol, t.trade_date.isoformat(),
                t.bar_ts_ist.isoformat(), int(t.is_heldout),
                t.pattern_type, t.tier, t.mtf_context, t.tz_label,
                int(t.mom_aligned), int(t.impulse_strong), t.opt_type,
                f"{t.spot_at_entry:.2f}", f"{t.entry_premium:.2f}",
                f"{t.exit_premium_t30:.2f}",
                f"{t.pnl_pct_t30:.4f}", f"{t.pnl_pct_sized:.4f}",
                t.outcome_t30,
                t.dte if t.dte is not None else "", t.day_of_week,
                int(t.is_expiry_day),
                t.atm_iv_level, t.pcr_bucket, t.or_range_bucket,
                t.prior_day_move_bucket, t.ret_session_bucket,
            ])
    print(f"\nWrote: experiment_32_trades.csv")

    return 0


if __name__ == "__main__":
    sys.exit(main())
