"""
experiment_29_1h_threshold_sweep.py

Purpose
-------
Tune build_ict_htf_zones.OB_MIN_MOVE_PCT for 1H structural zones.

The compendium says MEDIUM mtf_context (1H zone alignment) drives +73.5%
expectancy on BULL_OB and is the highest-WR context tier per Exp 15.
But live MERDIAN produces zero 1H structural zones because the threshold
(currently 0.40%) is too tight for the 1H timeframe. This experiment
sweeps a range of thresholds and measures, for each:

  - How many 1H BULL_OB / BEAR_OB / BULL_FVG zones get generated
  - For each generated zone, did spot subsequently test it (within N hours)
  - When tested, did the zone hold (price reversed in zone direction) or fail
  - Win rate + average return per (threshold, symbol)

Methodology
-----------
1. Read 5m bars from hist_spot_bars_5m for the live-clean window
   2026-04-07 -> 2026-04-24 (skipping pre-04-07 to dodge TD-029 TZ bug).
2. Aggregate to 1H OHLCV bars per symbol.
3. For each threshold x symbol:
     a. Walk 1H bars chronologically, detect OB/FVG using mirror of
        build_ict_htf_zones.detect_1h_zones() logic.
     b. For each zone, simulate forward 6 hours of 5m bars:
          * "Tested" if spot revisits zone_low <= price <= zone_high
          * "Win" if after testing, price moves ZONE_TARGET% in zone direction
          * "Loss" if price breaks through zone (close beyond zone in
            opposite direction)
     c. Record outcome.
4. Aggregate -> WR, expectancy, N per (threshold, symbol).

Note on PnL
-----------
Because we don't have option premium data joined to 1H zone tests at
this granularity, "expectancy" here is spot return percentage in the
zone direction over a 6-hour window after the test. This is a proxy.
A 65%+ WR with positive avg return validates the threshold; the actual
options PnL when paired with intraday ICT zones inside is downstream
of this and follows compendium ratios.

Decision rule
-------------
- WR >= 70% on at least one threshold AND zone_count >= 30 per symbol:
    SHIP that threshold. Update build_ict_htf_zones.py OB_MIN_MOVE_PCT.
- WR 60-70%: PROVISIONAL. Document, monitor live, decide next session.
- WR < 60%: REJECT. Don't lower threshold below 0.40. The 1H timeframe
  doesn't yield structural zones in current vol regime; move on.

Run
---
    python experiment_29_1h_threshold_sweep.py

Output
------
Console table + experiment_29_results.csv

Author: Session 10 2026-04-26
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from itertools import groupby
from typing import Optional
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

IST = ZoneInfo("Asia/Kolkata")

# --- experiment config -------------------------------------------------

# Threshold candidates to sweep
THRESHOLDS = [0.15, 0.20, 0.25, 0.30, 0.40]

# Mirror of build_ict_htf_zones.FVG_MIN_PCT (held constant; we sweep OB only)
FVG_MIN_PCT = 0.15

# Window: post-TD-029 cutoff to last full trading day in DB
DATE_FROM = "2026-04-07"
DATE_TO   = "2026-04-24"

# Forward simulation window (in hours) after a zone forms
SIM_HOURS_AFTER_ZONE = 6

# Win threshold: price must move this far in zone direction after a test
# to count as a win. Below = loss.
ZONE_TARGET_PCT = 0.30  # 0.30% = ~80 NIFTY points; meaningful move

# How far through a zone counts as a "break" (zone failed)
# = full close outside zone on opposite side
BREAK_BUFFER_PCT = 0.05

PAGE_SIZE = 1000

SYMBOLS = ["NIFTY", "SENSEX"]


# --- data structures ---------------------------------------------------

@dataclass
class Bar5m:
    bar_ts: datetime  # UTC tzaware
    trade_date: date
    open: float
    high: float
    low: float
    close: float


@dataclass
class HourBar:
    hour_start_ist: datetime  # IST tzaware, minute=0
    open: float
    high: float
    low: float
    close: float
    n_bars: int


@dataclass
class HourZone:
    direction: int            # +1 = BULL, -1 = BEAR
    pattern_type: str         # BULL_OB / BEAR_OB / BULL_FVG
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
    outcome: str              # WIN / LOSS / NO_TEST
    return_pct: float         # spot return from test point in zone direction


# --- helpers -----------------------------------------------------------

def pct(a: float, b: float) -> float:
    return 100.0 * (b - a) / a if a else 0.0


def fetch_5m_bars(sb, symbol: str, date_from: str, date_to: str) -> list[Bar5m]:
    """Read 5m bars for symbol over date range. Handles TZ awareness:
    bars stored after 2026-04-07 are UTC-stamped correctly (per session 10
    diagnosis). We restrict the window to that era explicitly."""
    inst = sb.table("instruments").select("id").eq("symbol", symbol).execute().data
    if not inst:
        raise RuntimeError(f"instrument not found: {symbol}")
    inst_id = inst[0]["id"]

    out: list[Bar5m] = []
    offset = 0
    while True:
        rows = (
            sb.table("hist_spot_bars_5m")
            .select("bar_ts, trade_date, open, high, low, close")
            .eq("symbol", symbol)
            .gte("trade_date", date_from)
            .lte("trade_date", date_to)
            .order("bar_ts")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute().data
        )
        if not rows:
            break
        for r in rows:
            out.append(Bar5m(
                bar_ts=datetime.fromisoformat(r["bar_ts"]),
                trade_date=date.fromisoformat(r["trade_date"]),
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
            ))
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    return out


def aggregate_to_1h(bars_5m: list[Bar5m]) -> list[HourBar]:
    """Build hourly bars from 5m bars. Group by IST hour. Only complete
    in-session hours are returned. Sessions are 09:15-15:30 IST so we
    have hours 09 (partial), 10, 11, 12, 13, 14, 15 (partial)."""
    if not bars_5m:
        return []

    # Group by IST hour
    grouped: dict[datetime, list[Bar5m]] = defaultdict(list)
    for b in bars_5m:
        ts_ist = b.bar_ts.astimezone(IST)
        # Only in-session bars 09:15-15:30 IST
        if ts_ist.time() < datetime.strptime("09:15", "%H:%M").time():
            continue
        if ts_ist.time() >= datetime.strptime("15:30", "%H:%M").time():
            continue
        hour_start = ts_ist.replace(minute=0, second=0, microsecond=0)
        grouped[hour_start].append(b)

    hours: list[HourBar] = []
    for hour_start, bs in sorted(grouped.items()):
        bs.sort(key=lambda x: x.bar_ts)
        hours.append(HourBar(
            hour_start_ist=hour_start,
            open=bs[0].open,
            high=max(b.high for b in bs),
            low=min(b.low for b in bs),
            close=bs[-1].close,
            n_bars=len(bs),
        ))
    return hours


def detect_1h_zones_at_threshold(
    hours: list[HourBar],
    ob_threshold_pct: float,
    fvg_threshold_pct: float = FVG_MIN_PCT,
) -> list[HourZone]:
    """Mirror of build_ict_htf_zones.detect_1h_zones() OB/FVG branches,
    parameterised on the OB threshold. Operates on hourly bars within
    a single session (caller groups by date)."""
    zones: list[HourZone] = []
    n = len(hours)
    if n < 2:
        return zones

    for i in range(1, n):
        curr = hours[i]
        prev = hours[i - 1]

        curr_move = pct(curr.open, curr.close)

        # BULL_OB: bearish prev hour before bullish impulse hour
        if curr_move >= ob_threshold_pct and prev.close < prev.open:
            zones.append(HourZone(
                direction=+1,
                pattern_type="BULL_OB",
                formed_at_hour_ist=curr.hour_start_ist,
                zone_high=max(prev.open, prev.close),
                zone_low=min(prev.open, prev.close),
            ))

        # BEAR_OB
        if curr_move <= -ob_threshold_pct and prev.close > prev.open:
            zones.append(HourZone(
                direction=-1,
                pattern_type="BEAR_OB",
                formed_at_hour_ist=curr.hour_start_ist,
                zone_high=max(prev.open, prev.close),
                zone_low=min(prev.open, prev.close),
            ))

        # BULL_FVG: gap between two_prev.high and curr.low
        if i >= 2:
            two_prev = hours[i - 2]
            ref = curr.open
            if two_prev.high < curr.low:
                gap_pct = (curr.low - two_prev.high) / ref * 100
                if gap_pct >= fvg_threshold_pct:
                    zones.append(HourZone(
                        direction=+1,
                        pattern_type="BULL_FVG",
                        formed_at_hour_ist=curr.hour_start_ist,
                        zone_high=curr.low,
                        zone_low=two_prev.high,
                    ))
    return zones


def simulate_zone_outcome(
    zone: HourZone,
    bars_5m_after: list[Bar5m],  # 5m bars strictly after zone formation
) -> ZoneOutcome:
    """Walk forward through 5m bars after zone formation. Determine if
    spot tests the zone, then whether it holds (WIN) or breaks (LOSS).

    Test definition:
      Spot enters zone (zone_low <= bar_low or bar_high <= zone_high
      with overlap).

    Win definition (BULL zone):
      After zone is tested, subsequent 5m close moves ZONE_TARGET_PCT%
      ABOVE the test price (zone direction is up).

    Loss definition (BULL zone):
      5m close prints below zone_low - BREAK_BUFFER_PCT (zone broke).

    BEAR zone is mirror.

    NO_TEST: zone never revisited within sim window. Excluded from WR.
    """
    tested = False
    test_at: Optional[datetime] = None
    test_price: Optional[float] = None

    target_pct = ZONE_TARGET_PCT
    break_buffer = BREAK_BUFFER_PCT

    for b in bars_5m_after:
        # Detect entry into zone
        if not tested:
            in_zone = (b.low <= zone.zone_high) and (b.high >= zone.zone_low)
            if in_zone:
                tested = True
                test_at = b.bar_ts.astimezone(IST)
                # Test price: midpoint of zone clamped to bar range
                test_price = max(min((zone.zone_high + zone.zone_low) / 2, b.high), b.low)
            continue

        # Post-test outcome check
        if zone.direction == +1:
            # BULL: win = close above test_price by target%, loss = close below zone_low - buffer
            if pct(test_price, b.close) >= target_pct:
                return ZoneOutcome(
                    threshold=0,  # filled by caller
                    symbol="",
                    pattern_type=zone.pattern_type,
                    direction=zone.direction,
                    formed_at_ist=zone.formed_at_hour_ist,
                    zone_low=zone.zone_low, zone_high=zone.zone_high,
                    tested=True,
                    test_at_ist=test_at,
                    outcome="WIN",
                    return_pct=pct(test_price, b.close),
                )
            if pct(zone.zone_low, b.close) <= -break_buffer:
                return ZoneOutcome(
                    threshold=0, symbol="",
                    pattern_type=zone.pattern_type,
                    direction=zone.direction,
                    formed_at_ist=zone.formed_at_hour_ist,
                    zone_low=zone.zone_low, zone_high=zone.zone_high,
                    tested=True, test_at_ist=test_at,
                    outcome="LOSS",
                    return_pct=pct(test_price, b.close),
                )
        else:
            # BEAR
            if pct(test_price, b.close) <= -target_pct:
                return ZoneOutcome(
                    threshold=0, symbol="",
                    pattern_type=zone.pattern_type,
                    direction=zone.direction,
                    formed_at_ist=zone.formed_at_hour_ist,
                    zone_low=zone.zone_low, zone_high=zone.zone_high,
                    tested=True, test_at_ist=test_at,
                    outcome="WIN",
                    return_pct=-pct(test_price, b.close),  # positive = profit
                )
            if pct(zone.zone_high, b.close) >= break_buffer:
                return ZoneOutcome(
                    threshold=0, symbol="",
                    pattern_type=zone.pattern_type,
                    direction=zone.direction,
                    formed_at_ist=zone.formed_at_hour_ist,
                    zone_low=zone.zone_low, zone_high=zone.zone_high,
                    tested=True, test_at_ist=test_at,
                    outcome="LOSS",
                    return_pct=-pct(test_price, b.close),
                )

    # Either never tested or tested but no resolution within window
    if not tested:
        return ZoneOutcome(
            threshold=0, symbol="",
            pattern_type=zone.pattern_type,
            direction=zone.direction,
            formed_at_ist=zone.formed_at_hour_ist,
            zone_low=zone.zone_low, zone_high=zone.zone_high,
            tested=False, test_at_ist=None,
            outcome="NO_TEST",
            return_pct=0.0,
        )
    # Tested but window expired without resolution
    final = bars_5m_after[-1]
    final_return = pct(test_price, final.close)
    if zone.direction == -1:
        final_return = -final_return
    return ZoneOutcome(
        threshold=0, symbol="",
        pattern_type=zone.pattern_type,
        direction=zone.direction,
        formed_at_ist=zone.formed_at_hour_ist,
        zone_low=zone.zone_low, zone_high=zone.zone_high,
        tested=True, test_at_ist=test_at,
        outcome="UNRESOLVED",
        return_pct=final_return,
    )


def run_for_symbol(sb, symbol: str) -> list[ZoneOutcome]:
    print(f"\n=== {symbol} ===")
    print(f"  Fetching 5m bars {DATE_FROM} -> {DATE_TO}...")
    bars = fetch_5m_bars(sb, symbol, DATE_FROM, DATE_TO)
    print(f"  Loaded {len(bars):,} 5m bars across {len(set(b.trade_date for b in bars))} dates")

    # Group bars by trade date for per-day 1H aggregation and zone detection
    by_date: dict[date, list[Bar5m]] = defaultdict(list)
    for b in bars:
        by_date[b.trade_date].append(b)

    all_outcomes: list[ZoneOutcome] = []

    for threshold in THRESHOLDS:
        zones_count = 0
        for d, day_bars in sorted(by_date.items()):
            day_hours = aggregate_to_1h(day_bars)
            if len(day_hours) < 2:
                continue
            zones = detect_1h_zones_at_threshold(day_hours, threshold)
            zones_count += len(zones)

            for z in zones:
                # Build forward simulation window: 5m bars from formation+1 cycle
                # to formation + SIM_HOURS_AFTER_ZONE hours
                sim_end_ist = z.formed_at_hour_ist + timedelta(hours=SIM_HOURS_AFTER_ZONE + 1)
                forward = [
                    b for b in day_bars
                    if b.bar_ts.astimezone(IST) > z.formed_at_hour_ist + timedelta(hours=1)
                    and b.bar_ts.astimezone(IST) < sim_end_ist
                ]
                if not forward:
                    continue
                outcome = simulate_zone_outcome(z, forward)
                outcome.threshold = threshold
                outcome.symbol = symbol
                all_outcomes.append(outcome)

        print(f"  threshold={threshold:.2f}%  zones_generated={zones_count}")

    return all_outcomes


def summarize(outcomes: list[ZoneOutcome]) -> None:
    """Pretty-print results: per (symbol, threshold), WR/expectancy/N."""
    by_key: dict[tuple, list[ZoneOutcome]] = defaultdict(list)
    for o in outcomes:
        by_key[(o.symbol, o.threshold)].append(o)

    print("\n" + "=" * 90)
    print(f"{'Symbol':<8} {'Threshold':>10} {'Total':>7} {'Tested':>7} {'Wins':>6} {'Loss':>6} {'NoTest':>7} {'WR%':>7} {'AvgRet%':>9}")
    print("-" * 90)
    for (sym, thr), os_ in sorted(by_key.items()):
        total = len(os_)
        tested = [o for o in os_ if o.tested]
        wins = [o for o in tested if o.outcome == "WIN"]
        losses = [o for o in tested if o.outcome == "LOSS"]
        no_test = [o for o in os_ if o.outcome == "NO_TEST"]
        unresolved = [o for o in tested if o.outcome == "UNRESOLVED"]

        # WR over (wins + losses) — exclude unresolved
        decisive = len(wins) + len(losses)
        wr = 100 * len(wins) / decisive if decisive else 0
        avg_ret = sum(o.return_pct for o in tested) / len(tested) if tested else 0
        print(f"{sym:<8} {thr:>10.2f} {total:>7} {len(tested):>7} {len(wins):>6} {len(losses):>6} {len(no_test):>7} {wr:>6.1f}% {avg_ret:>8.3f}%")
    print("=" * 90)

    print("\nDecision rule:")
    print("  WR >= 70% AND zone_count >= 30 -> SHIP that threshold")
    print("  WR 60-70% -> PROVISIONAL, document and monitor")
    print("  WR <  60% -> REJECT, keep current 0.40")


def write_csv(outcomes: list[ZoneOutcome], path: str) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "threshold", "symbol", "pattern_type", "direction",
            "formed_at_ist", "zone_low", "zone_high",
            "tested", "test_at_ist", "outcome", "return_pct"
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
    write_csv(all_outcomes, "experiment_29_results.csv")

    return 0


if __name__ == "__main__":
    sys.exit(main())
