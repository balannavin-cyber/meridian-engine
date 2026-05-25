"""
diagnostic_d_zone_replay.py

DIAGNOSTIC — D BEAR_OB / D BULL_OB candidate replay (TD-031 follow-up)

Question:
    For the last 30 trading days, how many D BEAR_OB and D BULL_OB candidates
    SHOULD have been written to ict_htf_zones based on standard ICT criteria,
    vs. how many actually were?

Method:
    1. Aggregate daily OHLC from hist_spot_bars_1m (more complete than 5m per
       diagnostic_bar_coverage_audit). Apply Rule 16 + in-session filter.
    2. For each daily candle K, identify candidate D BEAR_OB:
         - K is an UP candle (close > open)
         - K+1 is a strong DOWN candle (open > close, body >= 0.40% of close
           per Exp 29 v2 / F2 finding)
         - K+1 candle low < K candle low (displacement)
       Mirror for D BULL_OB.
    3. Pull actual D zones from ict_htf_zones with source_bar_date in window.
    4. Match candidates to actual zones; flag candidates that have NO match.

Output:
    - Daily OHLC table for last 30 days, both symbols
    - Candidate D BEAR_OB / D BULL_OB list per symbol
    - Actual D zones in ict_htf_zones for same window
    - Mismatch count -> closes / re-attributes TD-031

Author: Session 15 batch v2.
"""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timedelta, time as dt_time, date as date_t

from dotenv import load_dotenv
from supabase import create_client


PAGE_SIZE = 1000
LOOKBACK_DAYS = 30
SYMBOLS = ["NIFTY", "SENSEX"]
BODY_THRESHOLD_PCT = 0.40  # Exp 29 v2 / F2 — used by 1H detector; testing same for D


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def fetch_1m_bars_window(sb, symbol: str, start_dt: datetime, end_dt: datetime) -> list[dict]:
    rows = []
    offset = 0
    while True:
        r = (sb.table("hist_spot_bars_1m")
             .select("bar_ts, open, high, low, close")
             .eq("symbol", symbol)
             .gte("bar_ts", start_dt.isoformat())
             .lte("bar_ts", end_dt.isoformat())
             .order("bar_ts")
             .range(offset, offset + PAGE_SIZE - 1).execute())
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > 200_000:
            break
    out = []
    for row in rows:
        try:
            dt = datetime.fromisoformat(row["bar_ts"].replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, KeyError):
            continue
        t = dt.time()
        if dt_time(9, 15) <= t <= dt_time(15, 30):
            row["_dt"] = dt
            try:
                row["open"] = float(row["open"])
                row["high"] = float(row["high"])
                row["low"] = float(row["low"])
                row["close"] = float(row["close"])
            except (TypeError, ValueError):
                continue
            out.append(row)
    return out


def aggregate_daily(bars_1m: list[dict]) -> list[dict]:
    """Group 1m bars by trade_date, return daily OHLC."""
    by_date: dict[date_t, list[dict]] = defaultdict(list)
    for b in bars_1m:
        by_date[b["_dt"].date()].append(b)
    daily = []
    for d in sorted(by_date.keys()):
        bs = by_date[d]
        if not bs:
            continue
        bs.sort(key=lambda x: x["_dt"])
        daily.append({
            "date": d,
            "open": bs[0]["open"],
            "high": max(b["high"] for b in bs),
            "low": min(b["low"] for b in bs),
            "close": bs[-1]["close"],
            "n_bars": len(bs),
        })
    return daily


def find_d_ob_candidates(daily: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (bear_ob_candidates, bull_ob_candidates).
    BEAR_OB: K is UP candle, K+1 is strong DOWN candle, K+1.low < K.low.
    BULL_OB: K is DOWN candle, K+1 is strong UP candle, K+1.high > K.high.
    """
    bear, bull = [], []
    for i in range(len(daily) - 1):
        k = daily[i]
        k1 = daily[i + 1]
        # BEAR_OB
        k_up = k["close"] > k["open"]
        k1_down = k1["open"] > k1["close"]
        k1_body = abs(k1["close"] - k1["open"])
        k1_body_pct = k1_body / k1["close"] * 100 if k1["close"] else 0
        k1_displaced_down = k1["low"] < k["low"]
        if k_up and k1_down and k1_body_pct >= BODY_THRESHOLD_PCT and k1_displaced_down:
            bear.append({
                "candidate_date": k["date"],
                "trigger_date": k1["date"],
                "zone_low": k["low"],
                "zone_high": k["high"],
                "k_body_pct": (k["close"] - k["open"]) / k["open"] * 100,
                "k1_body_pct": -k1_body_pct,
            })
        # BULL_OB (mirror)
        k_down = k["close"] < k["open"]
        k1_up = k1["close"] > k1["open"]
        k1_displaced_up = k1["high"] > k["high"]
        if k_down and k1_up and k1_body_pct >= BODY_THRESHOLD_PCT and k1_displaced_up:
            bull.append({
                "candidate_date": k["date"],
                "trigger_date": k1["date"],
                "zone_low": k["low"],
                "zone_high": k["high"],
                "k_body_pct": (k["close"] - k["open"]) / k["open"] * 100,
                "k1_body_pct": k1_body_pct,
            })
    return bear, bull


def fetch_actual_d_zones(sb, symbol: str, start_date: str, end_date: str) -> list[dict]:
    """Pull D zones with source_bar_date in window."""
    rows = []
    offset = 0
    while True:
        r = (sb.table("ict_htf_zones")
             .select("*")
             .eq("symbol", symbol)
             .eq("timeframe", "D")
             .gte("source_bar_date", start_date)
             .lte("source_bar_date", end_date)
             .range(offset, offset + PAGE_SIZE - 1).execute())
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def main():
    sb = get_client()
    print("=" * 96)
    print("DIAGNOSTIC — D BEAR_OB / D BULL_OB candidate replay (TD-031)")
    print("=" * 96)
    print(f"Lookback: {LOOKBACK_DAYS} trading days, both symbols")
    print(f"OB body threshold: {BODY_THRESHOLD_PCT}% (per Exp 29 v2 / F2)")
    print()

    # We need approx LOOKBACK_DAYS * 1.6 calendar days to find that many trading days
    end = datetime.now().replace(hour=23, minute=59, second=59)
    start = end - timedelta(days=int(LOOKBACK_DAYS * 1.6) + 5)

    for symbol in SYMBOLS:
        print(f"--- {symbol} ---")
        bars = fetch_1m_bars_window(sb, symbol, start, end)
        daily = aggregate_daily(bars)
        # Take last LOOKBACK_DAYS
        daily = daily[-LOOKBACK_DAYS:]
        print(f"Daily OHLC ({len(daily)} sessions):")
        print(f"{'Date':<12} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10} "
              f"{'Body%':>8} {'1m_bars':>8}")
        for d in daily:
            body_pct = (d["close"] - d["open"]) / d["open"] * 100 if d["open"] else 0
            print(f"{d['date']!s:<12} {d['open']:>10.2f} {d['high']:>10.2f} "
                  f"{d['low']:>10.2f} {d['close']:>10.2f} {body_pct:>+7.2f}% {d['n_bars']:>8}")
        print()

        bear, bull = find_d_ob_candidates(daily)
        print(f"D BEAR_OB candidates ({len(bear)}):")
        if bear:
            for c in bear:
                print(f"  candidate_K={c['candidate_date']!s} trigger_K+1={c['trigger_date']!s} "
                      f"zone={c['zone_low']:.2f}-{c['zone_high']:.2f} "
                      f"K_body={c['k_body_pct']:+.2f}% K+1_body={c['k1_body_pct']:+.2f}%")
        else:
            print("  none")
        print()
        print(f"D BULL_OB candidates ({len(bull)}):")
        if bull:
            for c in bull:
                print(f"  candidate_K={c['candidate_date']!s} trigger_K+1={c['trigger_date']!s} "
                      f"zone={c['zone_low']:.2f}-{c['zone_high']:.2f} "
                      f"K_body={c['k_body_pct']:+.2f}% K+1_body={c['k1_body_pct']:+.2f}%")
        else:
            print("  none")
        print()

        if daily:
            window_start = str(daily[0]["date"])
            window_end = str(daily[-1]["date"])
            actual = fetch_actual_d_zones(sb, symbol, window_start, window_end)
            actual_bear = [z for z in actual if (z.get("pattern_type") or "").upper() == "BEAR_OB"]
            actual_bull = [z for z in actual if (z.get("pattern_type") or "").upper() == "BULL_OB"]
            print(f"Actual D zones in ict_htf_zones for {window_start} .. {window_end}: "
                  f"BEAR_OB={len(actual_bear)}, BULL_OB={len(actual_bull)}")
            for z in actual_bear + actual_bull:
                print(f"  {(z.get('pattern_type') or '?'):<10} "
                      f"source_bar_date={z.get('source_bar_date')} "
                      f"zone={z.get('zone_low')}-{z.get('zone_high')} "
                      f"status={z.get('status')}")
            print()
            # Mismatch
            cand_bear_dates = {c["candidate_date"] for c in bear}
            cand_bull_dates = {c["candidate_date"] for c in bull}
            actual_bear_dates = {z.get("source_bar_date") for z in actual_bear}
            actual_bull_dates = {z.get("source_bar_date") for z in actual_bull}
            missing_bear = cand_bear_dates - {parse_str_date(d) for d in actual_bear_dates if d}
            missing_bull = cand_bull_dates - {parse_str_date(d) for d in actual_bull_dates if d}
            print(f"BEAR_OB candidates that should have fired but did NOT: {len(missing_bear)}")
            for d in sorted(missing_bear):
                print(f"  {d!s}")
            print(f"BULL_OB candidates that should have fired but did NOT: {len(missing_bull)}")
            for d in sorted(missing_bull):
                print(f"  {d!s}")
        print()
        print()

    print("=" * 96)
    print("DIAGNOSIS:")
    print("If candidates >> actual, detector logic in build_ict_htf_zones.py is")
    print("incorrectly filtering out valid D zones. Likely candidates:")
    print("  (a) breach filter applied at write time eliminates already-violated candidates")
    print("  (b) body threshold mis-tuned (we tested 0.40%; daily candles often smaller)")
    print("  (c) detector requires additional confirmation that doesn't apply at D timeframe")
    print("If candidates ~= actual, TD-031 is wrong framing. The detector is correct;")
    print("there genuinely aren't many qualifying daily structures.")
    print("=" * 96)


def parse_str_date(s):
    if s is None:
        return None
    if isinstance(s, str):
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    if hasattr(s, "year"):
        return s
    return None


if __name__ == "__main__":
    main()
