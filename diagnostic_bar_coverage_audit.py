"""
diagnostic_bar_coverage_audit.py

DIAGNOSTIC — hist_spot_bars_5m + hist_spot_bars_1m coverage audit

Question:
    Why does ADR-003 Phase 1 v2 see only 27.5% of expected 5m bars over the
    last 10 days? Is hist_spot_bars_1m equally short (capture problem) or
    full (rollup problem)?

Method:
    For last 30 trading days, both symbols, both tables:
    - Count rows per (symbol, trade_date), filtered to in-session 09:15-15:30 IST
    - First / last bar_ts per day
    - Compare to expected: 5m=75 bars/session, 1m=375 bars/session
    - Hour distribution on most-recent day

Diagnosis:
    1m full + 5m short = build_spot_bars_mtf rollup is broken
    1m short + 5m short = capture_spot_1m is broken (upstream)
    Both full = not the issue; my Phase 1 v2 query is broken

Author: Session 15 batch v2.
"""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timedelta, time as dt_time

from dotenv import load_dotenv
from supabase import create_client


PAGE_SIZE = 1000
LOOKBACK_DAYS = 30
SYMBOLS = ["NIFTY", "SENSEX"]
EXPECTED_5M = 75
EXPECTED_1M = 375


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def fetch_distinct_dates(sb, table: str, symbol: str, n_days: int) -> list[str]:
    seen: set[str] = set()
    r = (sb.table(table).select("bar_ts").eq("symbol", symbol)
         .order("bar_ts", desc=True).limit(1).execute())
    if not r.data:
        return []
    last = datetime.fromisoformat(r.data[0]["bar_ts"].replace("Z", "+00:00")).replace(tzinfo=None)
    cutoff = last - timedelta(days=int(n_days * 1.6) + 5)
    offset = 0
    while offset < 200_000 and len(seen) < n_days:
        rr = (sb.table(table).select("bar_ts").eq("symbol", symbol)
              .gte("bar_ts", cutoff.isoformat())
              .order("bar_ts", desc=True)
              .range(offset, offset + PAGE_SIZE - 1).execute())
        batch = rr.data or []
        if not batch:
            break
        for row in batch:
            dt = datetime.fromisoformat(row["bar_ts"].replace("Z", "+00:00")).replace(tzinfo=None)
            seen.add(dt.date().isoformat())
            if len(seen) >= n_days:
                break
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return sorted(seen, reverse=True)[:n_days]


def fetch_bar_ts_for_date(sb, table: str, symbol: str, trade_date: str) -> list[datetime]:
    rows = []
    offset = 0
    day_start = f"{trade_date}T00:00:00+00:00"
    day_end = f"{trade_date}T23:59:59+00:00"
    while True:
        r = (sb.table(table).select("bar_ts").eq("symbol", symbol)
             .gte("bar_ts", day_start).lte("bar_ts", day_end)
             .order("bar_ts").range(offset, offset + PAGE_SIZE - 1).execute())
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    out = []
    for row in rows:
        dt = datetime.fromisoformat(row["bar_ts"].replace("Z", "+00:00")).replace(tzinfo=None)
        t = dt.time()
        if dt_time(9, 15) <= t <= dt_time(15, 30):
            out.append(dt)
    return out


def main():
    sb = get_client()
    print("=" * 96)
    print("DIAGNOSTIC — hist_spot_bars_5m + hist_spot_bars_1m coverage")
    print("=" * 96)
    print(f"Lookback: {LOOKBACK_DAYS} trading days, both symbols")
    print(f"Expected: 5m={EXPECTED_5M}/session, 1m={EXPECTED_1M}/session")
    print()

    overall = []
    for symbol in SYMBOLS:
        # Use 1m for date discovery (typically more complete than 5m)
        dates = fetch_distinct_dates(sb, "hist_spot_bars_1m", symbol, LOOKBACK_DAYS)
        if not dates:
            dates = fetch_distinct_dates(sb, "hist_spot_bars_5m", symbol, LOOKBACK_DAYS)
        print(f"--- {symbol} ({len(dates)} trading days found via 1m table) ---")
        print(f"{'Date':<12} "
              f"{'5m N':>6} {'5m %':>7} {'5m_first':>10} {'5m_last':>10}  "
              f"{'1m N':>6} {'1m %':>7} {'1m_first':>10} {'1m_last':>10}")
        for d in dates:
            ts5 = fetch_bar_ts_for_date(sb, "hist_spot_bars_5m", symbol, d)
            ts1 = fetch_bar_ts_for_date(sb, "hist_spot_bars_1m", symbol, d)
            n5, n1 = len(ts5), len(ts1)
            cov5 = n5 / EXPECTED_5M * 100
            cov1 = n1 / EXPECTED_1M * 100
            f5 = ts5[0].strftime("%H:%M") if ts5 else "-"
            l5 = ts5[-1].strftime("%H:%M") if ts5 else "-"
            f1 = ts1[0].strftime("%H:%M") if ts1 else "-"
            l1 = ts1[-1].strftime("%H:%M") if ts1 else "-"
            print(f"{d:<12} "
                  f"{n5:>6} {cov5:>6.1f}% {f5:>10} {l5:>10}  "
                  f"{n1:>6} {cov1:>6.1f}% {f1:>10} {l1:>10}")
            overall.append({"date": d, "symbol": symbol,
                            "n5": n5, "n1": n1, "cov5": cov5, "cov1": cov1})
        print()

    # === Aggregate ===
    print("=" * 96)
    print("AGGREGATE")
    print("=" * 96)
    total_5 = sum(x["n5"] for x in overall)
    total_1 = sum(x["n1"] for x in overall)
    expected_5 = len(overall) * EXPECTED_5M
    expected_1 = len(overall) * EXPECTED_1M
    cov5 = total_5 / expected_5 * 100 if expected_5 else 0
    cov1 = total_1 / expected_1 * 100 if expected_1 else 0
    print(f"5m total: {total_5}/{expected_5} = {cov5:.1f}%")
    print(f"1m total: {total_1}/{expected_1} = {cov1:.1f}%")
    print()

    # === Hour distribution on most recent day per symbol/table ===
    print("Hour distribution on most-recent day (each row = one hour, # = bars):")
    if overall:
        most_recent = max(set(x["date"] for x in overall))
        for symbol in SYMBOLS:
            for table, label in [("hist_spot_bars_5m", "5m"), ("hist_spot_bars_1m", "1m")]:
                ts = fetch_bar_ts_for_date(sb, table, symbol, most_recent)
                hdist = defaultdict(int)
                for dt in ts:
                    hdist[dt.hour] += 1
                print(f"  {symbol} {label} on {most_recent} (total {len(ts)}):")
                for hour in range(9, 16):
                    n = hdist.get(hour, 0)
                    print(f"    {hour:02d}h: {n:>3} {'#' * min(n, 60)}")
    print()

    # === Verdict ===
    print("=" * 96)
    print("DIAGNOSIS:")
    if cov1 >= 80 and cov5 < 50:
        print("  -> 1m FULL, 5m SHORT. ROOT CAUSE: build_spot_bars_mtf.py rollup.")
        print("     Likely a per-run date window or row-cap bug in the rollup script.")
        print("     Hint: TD-025 already noted it 're-aggregates full history every run' --")
        print("     if it's NOT actually doing that, the script logic is broken.")
        print("     Fix: inspect build_spot_bars_mtf.py for date-range filters or LIMIT clauses.")
    elif cov1 < 50 and cov5 < 50:
        print("  -> Both 1m and 5m SHORT. ROOT CAUSE: capture_spot_1m or upstream.")
        print("     Capture_spot_1m runs intraday (09:14-15:31 IST per Task Scheduler).")
        print("     Check if MERDIAN_Spot_1M task is firing every minute, and whether")
        print("     write-contract failures are being swallowed silently.")
    elif cov5 >= 80 and cov1 >= 80:
        print("  -> Both >= 80%. The earlier 27.5% reading may have been a query-window")
        print("     edge effect. Re-check ADR-003 Phase 1 query logic.")
    else:
        print("  -> Mixed: 1m={:.1f}%, 5m={:.1f}%. Investigate per-symbol asymmetry.".format(cov1, cov5))
    print("=" * 96)


if __name__ == "__main__":
    main()
