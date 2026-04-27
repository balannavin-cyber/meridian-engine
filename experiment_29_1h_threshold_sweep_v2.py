"""
experiment_29_1h_threshold_sweep_v2.py

Purpose
-------
Tune build_ict_htf_zones.OB_MIN_MOVE_PCT for 1H structural zones.
v2 rewrite (Session 10 2026-04-26): full-year coverage from 1m source.

What changed vs v1
------------------
v1 read hist_spot_bars_5m and got only 13 days of usable data because:
  (a) 5m table only goes back to 2026-03-08
  (b) v1 deliberately skipped pre-04-07 to dodge the TD-029 TZ bug
v2 reads hist_spot_bars_1m which covers 2025-04-01 -> 2026-04-24
(260 trading days, 215k+ rows). TD-029 TZ bug is handled in-query
via the same CASE-on-trade_date workaround used elsewhere in this
session: pre-04-07 rows have IST clock-time stored under UTC tzinfo,
post-04-07 rows are correctly UTC-stamped.

This gives us a statistically meaningful sample.

Methodology
-----------
1. Read 1m bars from hist_spot_bars_1m for full year.
2. Convert bar_ts to true IST per-row using era-aware logic:
     pre-04-07: bar_ts is IST clock-time stored as UTC -> read as UTC
     post-04-07: bar_ts is correct UTC -> convert UTC -> IST
3. Filter to in-session bars (09:15-15:30 IST).
4. Aggregate 1m -> 1h (zone formation) and 1m -> 5m (forward simulation).
5. For each threshold x symbol:
     a. Per trading day, walk 1H bars chronologically; detect OB/FVG
        using mirror of build_ict_htf_zones.detect_1h_zones() logic.
     b. For each zone, simulate forward 6 hours of 5m bars within
        the same trading day. Determine WIN / LOSS / NO_TEST per the
        rules in v1 (zone tested if spot enters, win if spot moves
        ZONE_TARGET_PCT in zone direction, loss if zone breaks).
6. Aggregate -> WR, expectancy, N per (threshold, symbol).

Decision rule
-------------
- WR >= 70% AND zone_count >= 30 per symbol: SHIP that threshold.
- WR 60-70%: PROVISIONAL. Document, monitor live.
- WR < 60%: REJECT. Don't ship a sub-0.40 threshold.

Run
---
    python experiment_29_1h_threshold_sweep_v2.py

Output
------
Console table + experiment_29_v2_results.csv
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

THRESHOLDS = [0.15, 0.20, 0.25, 0.30, 0.40]
FVG_MIN_PCT = 0.15

# Full-year window. 1m table covers this entire span.
DATE_FROM = "2025-04-01"
DATE_TO   = "2026-04-24"

# TZ-stamping bug era boundary (TD-029)
TZ_ERA_BOUNDARY = date(2026, 4, 7)

# Forward simulation window (in hours) after a zone forms
SIM_HOURS_AFTER_ZONE = 6

# Win threshold: price must move this far in zone direction after a test
ZONE_TARGET_PCT = 0.30

# Break: close beyond zone in opposite direction by this much
BREAK_BUFFER_PCT = 0.05

PAGE_SIZE = 1000
SYMBOLS = ["NIFTY", "SENSEX"]

# Session window (IST)
SESSION_START_MINUTES = 9 * 60 + 15   # 09:15 IST
SESSION_END_MINUTES   = 15 * 60 + 30  # 15:30 IST


# --- data structures ---------------------------------------------------

@dataclass
class Bar1m:
    ts_ist: datetime  # canonicalised IST tzaware
    trade_date: date
    open: float
    high: float
    low: float
    close: float


@dataclass
class HourBar:
    hour_start_ist: datetime
    open: float
    high: float
    low: float
    close: float
    n_bars: int


@dataclass
class FiveMinBar:
    bucket_start_ist: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass
class HourZone:
    direction: int
    pattern_type: str
    formed_at_hour_ist: datetime
    zone_high: float
    zone_low: float


@dataclass
class ZoneOutcome:
    threshold: float
    symbol: str
    pattern_type: str
    direction: int
    formed_at_ist: datetime
    zone_low: float
    zone_high: float
    tested: bool
    test_at_ist: Optional[datetime]
    outcome: str
    return_pct: float


# --- helpers -----------------------------------------------------------

def pct(a: float, b: float) -> float:
    return 100.0 * (b - a) / a if a else 0.0


def canonicalize_ts_to_ist(bar_ts_iso: str, trade_date: date) -> datetime:
    """Apply era-aware TZ correction. Pre-04-07 rows have IST clock-time
    stored under a UTC tzinfo marker; post-04-07 rows are stored as
    correct UTC.

    Returns IST tzaware datetime."""
    raw = datetime.fromisoformat(bar_ts_iso)
    if trade_date < TZ_ERA_BOUNDARY:
        # Pre-era: the wall-clock time is IST already. Strip tzinfo and
        # re-attach as IST.
        if raw.tzinfo is not None:
            raw = raw.replace(tzinfo=None)
        return raw.replace(tzinfo=IST)
    else:
        # Post-era: standard UTC -> IST conversion
        if raw.tzinfo is None:
            raw = raw.replace(tzinfo=UTC)
        return raw.astimezone(IST)


def in_session(ts_ist: datetime) -> bool:
    """09:15 <= t < 15:30 IST."""
    minutes_of_day = ts_ist.hour * 60 + ts_ist.minute
    return SESSION_START_MINUTES <= minutes_of_day < SESSION_END_MINUTES


def fetch_1m_bars(sb, symbol: str, date_from: str, date_to: str) -> list[Bar1m]:
    """Read all 1m bars for symbol over date range. Apply TZ canonicalisation
    per row. Filter to in-session only."""
    inst = sb.table("instruments").select("id").eq("symbol", symbol).execute().data
    if not inst:
        raise RuntimeError(f"instrument not found: {symbol}")
    inst_id = inst[0]["id"]

    out: list[Bar1m] = []
    offset = 0
    fetched = 0
    while True:
        rows = (
            sb.table("hist_spot_bars_1m")
            .select("bar_ts, trade_date, open, high, low, close")
            .eq("instrument_id", inst_id)
            .gte("trade_date", date_from)
            .lte("trade_date", date_to)
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
                ts_ist=ts_ist,
                trade_date=td,
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
            ))
        fetched += len(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        # Progress every 10k rows
        if fetched % 10000 == 0:
            print(f"    fetched {fetched:,} raw rows...")

    return out


def aggregate_to_1h(bars: list[Bar1m]) -> list[HourBar]:
    """Group 1m bars by IST hour. Return one bar per hour."""
    if not bars:
        return []
    grouped: dict[datetime, list[Bar1m]] = defaultdict(list)
    for b in bars:
        hour_start = b.ts_ist.replace(minute=0, second=0, microsecond=0)
        grouped[hour_start].append(b)
    out: list[HourBar] = []
    for hour_start, bs in sorted(grouped.items()):
        bs.sort(key=lambda x: x.ts_ist)
        out.append(HourBar(
            hour_start_ist=hour_start,
            open=bs[0].open,
            high=max(b.high for b in bs),
            low=min(b.low for b in bs),
            close=bs[-1].close,
            n_bars=len(bs),
        ))
    return out


def aggregate_to_5m(bars: list[Bar1m]) -> list[FiveMinBar]:
    """Group 1m bars into 5m buckets aligned to wall-clock (09:15-09:19,
    09:20-09:24, ...)."""
    if not bars:
        return []
    grouped: dict[datetime, list[Bar1m]] = defaultdict(list)
    for b in bars:
        bucket_min = (b.ts_ist.minute // 5) * 5
        bucket = b.ts_ist.replace(minute=bucket_min, second=0, microsecond=0)
        grouped[bucket].append(b)
    out: list[FiveMinBar] = []
    for bucket, bs in sorted(grouped.items()):
        bs.sort(key=lambda x: x.ts_ist)
        out.append(FiveMinBar(
            bucket_start_ist=bucket,
            open=bs[0].open,
            high=max(b.high for b in bs),
            low=min(b.low for b in bs),
            close=bs[-1].close,
        ))
    return out


def detect_1h_zones_at_threshold(
    hours: list[HourBar],
    ob_threshold_pct: float,
    fvg_threshold_pct: float = FVG_MIN_PCT,
) -> list[HourZone]:
    """Mirror build_ict_htf_zones.detect_1h_zones() but parameterised."""
    zones: list[HourZone] = []
    n = len(hours)
    if n < 2:
        return zones

    for i in range(1, n):
        curr = hours[i]
        prev = hours[i - 1]
        curr_move = pct(curr.open, curr.close)

        if curr_move >= ob_threshold_pct and prev.close < prev.open:
            zones.append(HourZone(
                direction=+1, pattern_type="BULL_OB",
                formed_at_hour_ist=curr.hour_start_ist,
                zone_high=max(prev.open, prev.close),
                zone_low=min(prev.open, prev.close),
            ))
        if curr_move <= -ob_threshold_pct and prev.close > prev.open:
            zones.append(HourZone(
                direction=-1, pattern_type="BEAR_OB",
                formed_at_hour_ist=curr.hour_start_ist,
                zone_high=max(prev.open, prev.close),
                zone_low=min(prev.open, prev.close),
            ))
        if i >= 2:
            two_prev = hours[i - 2]
            ref = curr.open
            if two_prev.high < curr.low:
                gap_pct = (curr.low - two_prev.high) / ref * 100
                if gap_pct >= fvg_threshold_pct:
                    zones.append(HourZone(
                        direction=+1, pattern_type="BULL_FVG",
                        formed_at_hour_ist=curr.hour_start_ist,
                        zone_high=curr.low,
                        zone_low=two_prev.high,
                    ))
    return zones


def simulate_zone_outcome(
    zone: HourZone,
    forward_5m: list[FiveMinBar],
) -> tuple[bool, Optional[datetime], str, float]:
    """Walk forward through 5m bars after zone formation. Return
    (tested, test_at_ist, outcome, return_pct)."""
    tested = False
    test_at: Optional[datetime] = None
    test_price: Optional[float] = None
    target = ZONE_TARGET_PCT
    break_buffer = BREAK_BUFFER_PCT

    for b in forward_5m:
        if not tested:
            in_zone = (b.low <= zone.zone_high) and (b.high >= zone.zone_low)
            if in_zone:
                tested = True
                test_at = b.bucket_start_ist
                # Test price: midpoint of zone clamped to bar range
                mid = (zone.zone_high + zone.zone_low) / 2
                test_price = max(min(mid, b.high), b.low)
            continue

        # Post-test: check resolution
        if zone.direction == +1:
            if pct(test_price, b.close) >= target:
                return True, test_at, "WIN", pct(test_price, b.close)
            if pct(zone.zone_low, b.close) <= -break_buffer:
                return True, test_at, "LOSS", pct(test_price, b.close)
        else:
            if pct(test_price, b.close) <= -target:
                return True, test_at, "WIN", -pct(test_price, b.close)
            if pct(zone.zone_high, b.close) >= break_buffer:
                return True, test_at, "LOSS", -pct(test_price, b.close)

    if not tested:
        return False, None, "NO_TEST", 0.0
    final_ret = pct(test_price, forward_5m[-1].close)
    if zone.direction == -1:
        final_ret = -final_ret
    return True, test_at, "UNRESOLVED", final_ret


def run_for_symbol(sb, symbol: str) -> list[ZoneOutcome]:
    print(f"\n=== {symbol} ===")
    print(f"  Fetching 1m bars {DATE_FROM} -> {DATE_TO}...")
    bars = fetch_1m_bars(sb, symbol, DATE_FROM, DATE_TO)
    distinct_dates = len(set(b.trade_date for b in bars))
    print(f"  Loaded {len(bars):,} 1m bars across {distinct_dates} dates (in-session only)")

    # Group bars by trade_date
    by_date: dict[date, list[Bar1m]] = defaultdict(list)
    for b in bars:
        by_date[b.trade_date].append(b)

    # Pre-aggregate per day to avoid recomputing for each threshold
    day_hours: dict[date, list[HourBar]] = {}
    day_5m:    dict[date, list[FiveMinBar]] = {}
    for d, day_bars in by_date.items():
        day_hours[d] = aggregate_to_1h(day_bars)
        day_5m[d]    = aggregate_to_5m(day_bars)

    all_outcomes: list[ZoneOutcome] = []

    for threshold in THRESHOLDS:
        zones_count = 0
        for d in sorted(day_hours.keys()):
            hours = day_hours[d]
            if len(hours) < 2:
                continue
            zones = detect_1h_zones_at_threshold(hours, threshold)
            zones_count += len(zones)

            for z in zones:
                # Forward window: 5m bars within same day starting one full
                # hour after formation, ending at SIM_HOURS_AFTER_ZONE later
                start_after = z.formed_at_hour_ist + timedelta(hours=1)
                end_at      = z.formed_at_hour_ist + timedelta(hours=SIM_HOURS_AFTER_ZONE + 1)
                forward = [
                    b for b in day_5m[d]
                    if b.bucket_start_ist >= start_after
                    and b.bucket_start_ist < end_at
                ]
                if not forward:
                    continue
                tested, test_at, outcome_str, ret_pct = simulate_zone_outcome(z, forward)
                all_outcomes.append(ZoneOutcome(
                    threshold=threshold,
                    symbol=symbol,
                    pattern_type=z.pattern_type,
                    direction=z.direction,
                    formed_at_ist=z.formed_at_hour_ist,
                    zone_low=z.zone_low,
                    zone_high=z.zone_high,
                    tested=tested,
                    test_at_ist=test_at,
                    outcome=outcome_str,
                    return_pct=ret_pct,
                ))

        print(f"  threshold={threshold:.2f}%  zones_generated={zones_count}")

    return all_outcomes


def summarize(outcomes: list[ZoneOutcome]) -> None:
    by_key: dict[tuple, list[ZoneOutcome]] = defaultdict(list)
    for o in outcomes:
        by_key[(o.symbol, o.threshold)].append(o)

    print("\n" + "=" * 96)
    print(f"{'Symbol':<8} {'Threshold':>10} {'Total':>7} {'Tested':>7} {'Wins':>6} {'Loss':>6} {'NoTest':>7} {'Unres':>6} {'WR%':>7} {'AvgRet%':>9}")
    print("-" * 96)
    for (sym, thr), os_ in sorted(by_key.items()):
        total = len(os_)
        tested = [o for o in os_ if o.tested]
        wins = [o for o in tested if o.outcome == "WIN"]
        losses = [o for o in tested if o.outcome == "LOSS"]
        no_test = [o for o in os_ if o.outcome == "NO_TEST"]
        unresolved = [o for o in tested if o.outcome == "UNRESOLVED"]
        decisive = len(wins) + len(losses)
        wr = 100 * len(wins) / decisive if decisive else 0
        avg_ret = sum(o.return_pct for o in tested) / len(tested) if tested else 0
        print(f"{sym:<8} {thr:>10.2f} {total:>7} {len(tested):>7} {len(wins):>6} {len(losses):>6} {len(no_test):>7} {len(unresolved):>6} {wr:>6.1f}% {avg_ret:>8.3f}%")
    print("=" * 96)
    print("\nDecision rule:")
    print("  WR >= 70% AND decisive (Win+Loss) >= 30 -> SHIP that threshold")
    print("  WR 60-70%                                -> PROVISIONAL, monitor live")
    print("  WR <  60%                                -> REJECT, keep current 0.40")


def write_csv(outcomes: list[ZoneOutcome], path: str) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "threshold", "symbol", "pattern_type", "direction",
            "formed_at_ist", "zone_low", "zone_high",
            "tested", "test_at_ist", "outcome", "return_pct",
        ])
        for o in outcomes:
            w.writerow([
                o.threshold, o.symbol, o.pattern_type, o.direction,
                o.formed_at_ist.isoformat() if o.formed_at_ist else "",
                f"{o.zone_low:.2f}", f"{o.zone_high:.2f}",
                int(o.tested),
                o.test_at_ist.isoformat() if o.test_at_ist else "",
                o.outcome,
                f"{o.return_pct:.4f}",
            ])
    print(f"\nWrote: {path}")


def main() -> int:
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    all_outcomes: list[ZoneOutcome] = []
    for symbol in SYMBOLS:
        all_outcomes.extend(run_for_symbol(sb, symbol))
    summarize(all_outcomes)
    write_csv(all_outcomes, "experiment_29_v2_results.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
