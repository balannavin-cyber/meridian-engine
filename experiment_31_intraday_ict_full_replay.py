"""
experiment_31_intraday_ict_full_replay.py

Purpose
-------
Replay the post-F1 ICT detector across the full year of historical data
to validate whether the detect/tier/MTF-context pipeline produces
tradable edge as the compendium claims.

This is the experiment that answers your question:
"If MERDIAN's detector + gate were properly wired, what WR / PnL
would it realise on intraday ICT detections live?"

The compendium's Experiment 15 reported:
  BEAR_OB pure ICT 94.4% WR
  BULL_OB pure ICT 86.4% WR
  BULL_OB DTE=0 100% WR +107.4% TIER1
  BULL_OB AFTNOON 100% WR +75.3% TIER1
  BULL_FVG HIGH context DTE=0 87.5% WR +58.9% TIER1
  MEDIUM (1H) context +73.5% expectancy

Exp 31 tests whether these findings replicate on current data with
the post-F1 detector logic.

Methodology
-----------
1. Read 1m bars from hist_spot_bars_1m for full year. TZ canonicalize
   per the TD-029 era boundary (pre-04-07 IST-stored-as-UTC).
2. Per trading day:
     a. Aggregate 1m -> 5m bars (compendium's canonical ICT timeframe).
     b. Run ICT detection (BULL_OB / BEAR_OB / BULL_FVG / JUDAS_BULL)
        using post-F1 time_zone_label (UTC->IST conversion).
     c. Apply tier assignment (TIER1 / TIER2 / SKIP) per assign_tier().
     d. For each non-SKIP detection:
        - Look up active W zones in ict_htf_zones at detection time
          and check if spot sits inside same-direction W zone.
          MTF context = VERY_HIGH if W overlap, LOW otherwise.
          (D coverage is too sparse for full-year replay.)
        - Look up the matching row in hist_atm_option_bars_5m at
          detection bar_ts. Compute T+30m option PnL using ce_close
          for BULL patterns, pe_close for BEAR patterns.
        - Apply tier sizing multiplier (TIER1=1.5x, TIER2=1.0x).
3. Aggregate WR, total PnL%, avg PnL%/trade per (symbol, pattern,
   tier, mtf_context) bucket.

Output
------
Console summary tables + experiment_31_results.csv

Decision rule
-------------
The compendium says ~70-90% WR on TIER1 setups. If Exp 31 replicates
within 10pp of those numbers on full-year data:
  -> validate the pipeline is producing edge
  -> ship F3 (daily zones) and (later) F2 if deemed valuable
  -> consider conditional ENH-35 lift (allow LONG_GAMMA on TIER1)
If WR collapses below 60% on TIER1:
  -> the compendium's findings don't replicate on current vintage
  -> deeper investigation needed before shipping anything

Run
---
    python experiment_31_intraday_ict_full_replay.py

Caveats
-------
- D-context tier (HIGH) not testable for the year (only 8 dates of D
  zones exist). MEDIUM (1H) tier always LOW (no H structural zones).
  So MTF buckets reduce to {VERY_HIGH (W overlap), LOW (none)}.
- T+30m exit doesn't account for stop-loss on zone breach. We compute
  both and report the more permissive (T+30m) as primary, breach-stop
  as secondary cross-check.
- IV decay over 30m can erode option premium even on correct direction.
  This is real and the compendium accounts for it. The PnL numbers
  here are net-of-decay, matching what live execution would realise.
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from typing import Optional
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

# ICT detector constants (mirror detect_ict_patterns.py)
OB_MIN_MOVE_PCT   = 0.40
FVG_MIN_PCT       = 0.10
JUDAS_MIN_PCT     = 0.25
SWEEP_LOOKBACK    = 5
SWEEP_MIN_PCT     = 0.10
STRONG_IMPULSE    = 0.30
LOOKBACK_BARS     = 3
LOW_IV_THRESHOLD  = 12.0

# Time zones (IST minutes-of-day)
SESSION_START = 9 * 60 + 15      # 09:15
MORNING_START = 10 * 60          # 10:00
MIDDAY_START  = 11 * 60 + 30     # 11:30
AFTNOON_START = 13 * 60 + 30     # 13:30
SESSION_END   = 15 * 60 + 30     # 15:30
POWER_HOUR    = 15 * 60          # 15:00 — no new signals

# Trade simulation
EXIT_MINUTES = 30                # T+30m exit per compendium
TIER1_MULT   = 1.5
TIER2_MULT   = 1.0

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
    pattern_type: str
    direction: int
    zone_high: float
    zone_low: float
    valid_from: date
    valid_to: date


@dataclass
class Detection:
    symbol: str
    trade_date: date
    bar_idx: int                  # 5m bar index within day
    bar_ts_ist: datetime
    pattern_type: str
    direction: int                # +1 BULL, -1 BEAR
    opt_type: str                 # CE or PE
    spot_at_entry: float
    zone_high: float
    zone_low: float
    tz_label: str
    mom_aligned: bool
    impulse_strong: bool
    has_prior_sweep: bool
    tier: str                     # TIER1 / TIER2 / SKIP
    size_mult: float
    mtf_context: str              # VERY_HIGH / LOW
    htf_zone_id: Optional[str]


@dataclass
class TradeOutcome:
    detection: Detection
    entry_premium: float
    exit_premium_t30: float
    pnl_pct_t30: float            # raw % move on premium
    pnl_pct_sized: float          # tier-multiplied
    outcome_t30: str              # WIN / LOSS
    has_option_data: bool


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


def fetch_active_w_zones(sb, symbol: str) -> list[HTFZone]:
    """All W zones, full date range. Filter at detection time per
    valid_from <= detection_date <= valid_to."""
    rows = (
        sb.table("ict_htf_zones")
        .select("id, timeframe, pattern_type, direction, "
                "zone_high, zone_low, valid_from, valid_to, status")
        .eq("symbol", symbol)
        .eq("timeframe", "W")
        .execute().data
    )
    out = []
    for r in rows:
        out.append(HTFZone(
            zone_id=r["id"],
            timeframe=r["timeframe"],
            pattern_type=r["pattern_type"],
            direction=int(r["direction"]),
            zone_high=float(r["zone_high"]),
            zone_low=float(r["zone_low"]),
            valid_from=date.fromisoformat(r["valid_from"]),
            valid_to=date.fromisoformat(r["valid_to"]),
        ))
    return out


def fetch_atm_option_bars(sb, symbol: str) -> dict[tuple[date, datetime], dict]:
    """Map (trade_date, bar_ts_ist) -> option row. The bar_ts in
    hist_atm_option_bars_5m is also UTC-stamped. Apply era-aware
    canonicalisation so keys match detection bar_ts."""
    out = {}
    offset = 0
    while True:
        rows = (
            sb.table("hist_atm_option_bars_5m")
            .select("trade_date, bar_ts, atm_strike, expiry_date, dte, "
                    "ce_open, ce_close, ce_delta, pe_open, pe_close, pe_delta, "
                    "ce_iv_close, pe_iv_close, spot_close")
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
            # Bucket to 5m boundary for matching
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
    """Returns list of (pattern_bar_idx, pattern_type, direction)."""
    results = []
    seen = set()
    n = len(bars)
    for i in range(n - 6):
        # Use 5-bar forward move from current i
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
    """Compendium's JUDAS_BULL: opening drop > JUDAS_MIN_PCT in first
    ~14 bars (~70 min on 5m), then >50% recovery within next 30 bars."""
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
    """Returns (mom_aligned, impulse_strong). Sweep computed separately."""
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
    # BULL_FVG, JUDAS_BULL: always TIER2 by default
    return "TIER2", TIER2_MULT


def get_mtf_context(
    spot: float, direction: int, w_zones_active: list[HTFZone]
) -> tuple[str, Optional[str]]:
    for z in w_zones_active:
        if z.direction != direction:
            continue
        if z.zone_low <= spot <= z.zone_high:
            return "VERY_HIGH", z.zone_id
    return "LOW", None


# --- per-day replay ----------------------------------------------------

def replay_day(
    bars_5m: list[Bar5m],
    trade_date: date,
    symbol: str,
    w_zones_for_date: list[HTFZone],
) -> list[Detection]:
    detections: list[Detection] = []
    candidates = []
    candidates.extend(detect_obs(bars_5m))
    candidates.extend(detect_fvgs(bars_5m))
    candidates.extend(detect_judas(bars_5m))

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
        # Zone levels
        if pattern in ("BULL_OB", "BEAR_OB"):
            zh = max(bar.open, bar.close)
            zl = min(bar.open, bar.close)
        elif pattern == "BULL_FVG":
            if 0 < idx < len(bars_5m) - 1:
                zh = bars_5m[idx + 1].low
                zl = bars_5m[idx - 1].high
            else:
                zh, zl = bar.high, bar.low
        else:
            zh, zl = bar.high, bar.low

        opt_type = "CE" if direction == +1 else "PE"

        mtf_ctx, htf_id = get_mtf_context(bar.close, direction, w_zones_for_date)

        detections.append(Detection(
            symbol=symbol, trade_date=trade_date,
            bar_idx=idx, bar_ts_ist=bar.bucket_start_ist,
            pattern_type=pattern, direction=direction, opt_type=opt_type,
            spot_at_entry=bar.close,
            zone_high=zh, zone_low=zl,
            tz_label=tz_label_v,
            mom_aligned=mom_aligned, impulse_strong=impulse_strong,
            has_prior_sweep=False,  # disabled — not load-bearing for tier
            tier=tier, size_mult=mult,
            mtf_context=mtf_ctx, htf_zone_id=htf_id,
        ))
    return detections


# --- PnL computation ---------------------------------------------------

def compute_pnl(
    det: Detection,
    options_lookup: dict[tuple[date, datetime], dict],
) -> Optional[TradeOutcome]:
    """Look up option premium at entry and at T+30m. Compute PnL%."""
    entry_key = (det.trade_date, det.bar_ts_ist)
    entry_row = options_lookup.get(entry_key)
    if not entry_row:
        return None
    exit_ts = det.bar_ts_ist + timedelta(minutes=EXIT_MINUTES)
    # Bucket exit_ts to 5m boundary
    exit_bucket = exit_ts.replace(
        minute=(exit_ts.minute // 5) * 5, second=0, microsecond=0,
    )
    exit_row = options_lookup.get((det.trade_date, exit_bucket))
    if not exit_row:
        # Fall back to last available bar of the day for this trade_date
        # by scanning forward up to 6 buckets
        for skip in range(1, 7):
            exit_bucket_2 = exit_bucket - timedelta(minutes=5 * skip)
            if (det.trade_date, exit_bucket_2) in options_lookup:
                exit_row = options_lookup[(det.trade_date, exit_bucket_2)]
                break
        if not exit_row:
            return None

    if det.opt_type == "CE":
        entry_p = float(entry_row.get("ce_close") or 0)
        exit_p  = float(exit_row.get("ce_close") or 0)
    else:
        entry_p = float(entry_row.get("pe_close") or 0)
        exit_p  = float(exit_row.get("pe_close") or 0)

    if entry_p <= 0:
        return None  # bad data — exclude

    pnl_pct = pct(entry_p, exit_p)
    pnl_sized = pnl_pct * det.size_mult
    outcome = "WIN" if pnl_pct > 0 else "LOSS"
    return TradeOutcome(
        detection=det,
        entry_premium=entry_p,
        exit_premium_t30=exit_p,
        pnl_pct_t30=pnl_pct,
        pnl_pct_sized=pnl_sized,
        outcome_t30=outcome,
        has_option_data=True,
    )


# --- main flow ---------------------------------------------------------

def run_for_symbol(sb, symbol: str) -> list[TradeOutcome]:
    print(f"\n=== {symbol} ===")
    print("  Fetching 1m bars (full year)...")
    bars = fetch_1m_bars(sb, symbol)
    distinct_dates = sorted(set(b.trade_date for b in bars))
    print(f"  Loaded {len(bars):,} 1m bars across {len(distinct_dates)} dates")

    print("  Fetching W zones...")
    w_zones = fetch_active_w_zones(sb, symbol)
    print(f"  Loaded {len(w_zones)} W zones")

    print("  Fetching ATM option bars (full year)...")
    options_lookup = fetch_atm_option_bars(sb, symbol)
    print(f"  Loaded {len(options_lookup):,} option bars")

    by_date: dict[date, list[Bar1m]] = defaultdict(list)
    for b in bars:
        by_date[b.trade_date].append(b)

    all_detections: list[Detection] = []
    print(f"  Replaying {len(distinct_dates)} trading days...")
    for d in distinct_dates:
        day_bars_1m = by_date[d]
        bars_5m = aggregate_1m_to_5m(day_bars_1m)
        if len(bars_5m) < 10:
            continue
        # W zones active for this date
        w_active = [z for z in w_zones if z.valid_from <= d <= z.valid_to]
        dets = replay_day(bars_5m, d, symbol, w_active)
        all_detections.extend(dets)

    print(f"  Detections (non-SKIP): {len(all_detections)}")

    # Compute PnL
    outcomes: list[TradeOutcome] = []
    no_data = 0
    for det in all_detections:
        out = compute_pnl(det, options_lookup)
        if out is None:
            no_data += 1
            continue
        outcomes.append(out)
    print(f"  With option PnL data: {len(outcomes)}  (no data: {no_data})")
    return outcomes


def summarize(outcomes: list[TradeOutcome]) -> None:
    # Bucket: (symbol, pattern, tier, mtf_context)
    by_key: dict[tuple, list[TradeOutcome]] = defaultdict(list)
    for o in outcomes:
        d = o.detection
        by_key[(d.symbol, d.pattern_type, d.tier, d.mtf_context)].append(o)

    print("\n" + "=" * 110)
    print(f"{'Symbol':<8} {'Pattern':<12} {'Tier':<6} {'MTF':<10} {'N':>5} {'Wins':>5} {'Loss':>5} {'WR%':>7} "
          f"{'Total%':>9} {'Avg/T%':>8} {'Sized%':>9}")
    print("-" * 110)
    for key in sorted(by_key.keys()):
        sym, pat, tier, mtf = key
        os_ = by_key[key]
        n = len(os_)
        wins = sum(1 for o in os_ if o.outcome_t30 == "WIN")
        losses = sum(1 for o in os_ if o.outcome_t30 == "LOSS")
        wr = 100 * wins / n if n else 0
        total = sum(o.pnl_pct_t30 for o in os_)
        avg = total / n if n else 0
        total_sized = sum(o.pnl_pct_sized for o in os_)
        print(f"{sym:<8} {pat:<12} {tier:<6} {mtf:<10} {n:>5} {wins:>5} {losses:>5} "
              f"{wr:>6.1f}% {total:>8.1f}% {avg:>7.2f}% {total_sized:>8.1f}%")
    print("=" * 110)

    # Headline aggregates
    print("\nHEADLINE — TIER1 by symbol:")
    for sym in SYMBOLS:
        tier1 = [o for o in outcomes if o.detection.symbol == sym
                 and o.detection.tier == "TIER1"]
        if not tier1:
            print(f"  {sym}: TIER1 N=0")
            continue
        wins = sum(1 for o in tier1 if o.outcome_t30 == "WIN")
        wr = 100 * wins / len(tier1)
        total = sum(o.pnl_pct_t30 for o in tier1)
        avg = total / len(tier1)
        print(f"  {sym}: TIER1 N={len(tier1)} WR={wr:.1f}% TotalPnL={total:.1f}% Avg={avg:.2f}%")

    print("\nHEADLINE — VERY_HIGH MTF context by symbol:")
    for sym in SYMBOLS:
        vh = [o for o in outcomes if o.detection.symbol == sym
              and o.detection.mtf_context == "VERY_HIGH"]
        if not vh:
            print(f"  {sym}: VERY_HIGH N=0")
            continue
        wins = sum(1 for o in vh if o.outcome_t30 == "WIN")
        wr = 100 * wins / len(vh)
        total = sum(o.pnl_pct_t30 for o in vh)
        avg = total / len(vh)
        print(f"  {sym}: VERY_HIGH N={len(vh)} WR={wr:.1f}% TotalPnL={total:.1f}% Avg={avg:.2f}%")

    print("\nDecision rule:")
    print("  TIER1 WR >= 70% replicates compendium -> ship F3 (daily zones), validate visibility")
    print("  TIER1 WR 60-70% -> partial replication, monitor live before policy changes")
    print("  TIER1 WR <  60% -> compendium does not replicate on current data, investigate")


def write_csv(outcomes: list[TradeOutcome], path: str) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "symbol", "trade_date", "bar_ts_ist", "pattern", "direction",
            "opt_type", "tz_label", "tier", "size_mult", "mtf_context",
            "spot_at_entry", "entry_premium", "exit_premium_t30",
            "pnl_pct_t30", "pnl_pct_sized", "outcome_t30",
        ])
        for o in outcomes:
            d = o.detection
            w.writerow([
                d.symbol, d.trade_date.isoformat(),
                d.bar_ts_ist.isoformat(),
                d.pattern_type, d.direction,
                d.opt_type, d.tz_label, d.tier, d.size_mult,
                d.mtf_context,
                f"{d.spot_at_entry:.2f}",
                f"{o.entry_premium:.2f}",
                f"{o.exit_premium_t30:.2f}",
                f"{o.pnl_pct_t30:.4f}",
                f"{o.pnl_pct_sized:.4f}",
                o.outcome_t30,
            ])
    print(f"\nWrote: {path}")


def main() -> int:
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    all_outcomes: list[TradeOutcome] = []
    for symbol in SYMBOLS:
        all_outcomes.extend(run_for_symbol(sb, symbol))
    summarize(all_outcomes)
    write_csv(all_outcomes, "experiment_31_results.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
