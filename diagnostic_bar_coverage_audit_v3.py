"""
diagnostic_bar_coverage_audit_v3.py

v3 fix: hist_spot_bars_1m has no `symbol` column, uses `instrument_id` (FK).
Discover the instrument_id values for NIFTY and SENSEX via hist_spot_bars_5m
(which has BOTH `symbol` and `instrument_id`). Use those in 1m queries.

This finally enables the rollup-vs-capture diagnosis: if 1m coverage is full
but 5m is short -> build_spot_bars_mtf rollup is broken (likely TZ assumption).
If both are short -> capture_spot_1m or upstream is the issue.
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
EXPECTED_5M = 76  # corrected: 09:15 to 15:30 inclusive at 5m = 76
EXPECTED_1M = 376  # 09:15 to 15:30 inclusive at 1m = 376


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def discover_columns(sb, table: str) -> list[str]:
    r = sb.table(table).select("*").limit(1).execute()
    if not r.data:
        return []
    return list(r.data[0].keys())


def fetch_distinct_dates(sb, table: str, filter_col: str, filter_val,
                          n_days: int) -> list[str]:
    """Return last n_days distinct trade_date strings using trade_date column."""
    seen: set[str] = set()
    # Use trade_date column directly if present; else fall back to bar_ts
    cols = discover_columns(sb, table)
    if "trade_date" in cols:
        # Pull distinct trade_date via order desc + paging
        r = (sb.table(table).select("trade_date").eq(filter_col, filter_val)
             .order("trade_date", desc=True)
             .range(0, PAGE_SIZE - 1).execute())
        for row in (r.data or []):
            td = row.get("trade_date")
            if td:
                seen.add(str(td)[:10])
            if len(seen) >= n_days:
                break
        # If still need more, page further
        offset = PAGE_SIZE
        while len(seen) < n_days and offset < 50_000:
            rr = (sb.table(table).select("trade_date").eq(filter_col, filter_val)
                  .order("trade_date", desc=True)
                  .range(offset, offset + PAGE_SIZE - 1).execute())
            batch = rr.data or []
            if not batch:
                break
            for row in batch:
                td = row.get("trade_date")
                if td:
                    seen.add(str(td)[:10])
                if len(seen) >= n_days:
                    break
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        return sorted(seen, reverse=True)[:n_days]
    # fallback to bar_ts approach
    r = (sb.table(table).select("bar_ts").eq(filter_col, filter_val)
         .order("bar_ts", desc=True).limit(1).execute())
    if not r.data:
        return []
    last = datetime.fromisoformat(r.data[0]["bar_ts"].replace("Z", "+00:00")).replace(tzinfo=None)
    cutoff = last - timedelta(days=int(n_days * 1.6) + 5)
    offset = 0
    while offset < 200_000 and len(seen) < n_days:
        rr = (sb.table(table).select("bar_ts").eq(filter_col, filter_val)
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


def fetch_bar_count_by_trade_date(sb, table: str, filter_col: str, filter_val,
                                   trade_date: str) -> tuple[int, str | None, str | None]:
    """Return (count, first_bar_ts_str, last_bar_ts_str) for symbol on trade_date.
    Filter by `trade_date` column when present (avoids any TZ issues on bar_ts)."""
    cols = discover_columns(sb, table)
    rows = []
    offset = 0
    if "trade_date" in cols:
        while True:
            r = (sb.table(table).select("bar_ts")
                 .eq(filter_col, filter_val)
                 .eq("trade_date", trade_date)
                 .order("bar_ts")
                 .range(offset, offset + PAGE_SIZE - 1).execute())
            batch = r.data or []
            rows.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
    else:
        day_start = f"{trade_date}T00:00:00+00:00"
        day_end = f"{trade_date}T23:59:59+00:00"
        while True:
            r = (sb.table(table).select("bar_ts")
                 .eq(filter_col, filter_val)
                 .gte("bar_ts", day_start).lte("bar_ts", day_end)
                 .order("bar_ts")
                 .range(offset, offset + PAGE_SIZE - 1).execute())
            batch = r.data or []
            rows.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
    if not rows:
        return 0, None, None
    return len(rows), rows[0]["bar_ts"], rows[-1]["bar_ts"]


def main():
    sb = get_client()
    print("=" * 96)
    print("DIAGNOSTIC v3 — hist_spot_bars_5m + hist_spot_bars_1m coverage")
    print("=" * 96)

    cols_5m = discover_columns(sb, "hist_spot_bars_5m")
    cols_1m = discover_columns(sb, "hist_spot_bars_1m")
    print(f"hist_spot_bars_5m columns: {cols_5m}")
    print(f"hist_spot_bars_1m columns: {cols_1m}")

    # 5m can be queried via `symbol` directly
    sym_col_5m = "symbol" if "symbol" in cols_5m else None
    if sym_col_5m is None:
        print("[FATAL] hist_spot_bars_5m has no `symbol` column. Aborting.")
        return

    # 1m: discover via instrument_id mapping if symbol col missing
    inst_id_map = {}
    use_1m = "instrument_id" in cols_1m
    if "symbol" in cols_1m:
        # 1m has symbol after all — use directly
        sym_col_1m = "symbol"
        sym_val_map_1m = {s: s for s in SYMBOLS}
        print("[INFO] 1m has `symbol` column directly")
    elif use_1m:
        # Need instrument_id mapping
        print("[INFO] 1m has no `symbol`; discovering via instrument_id from 5m ...")
        for s in SYMBOLS:
            r = (sb.table("hist_spot_bars_5m").select("instrument_id")
                 .eq("symbol", s).limit(1).execute())
            if r.data:
                inst_id_map[s] = r.data[0]["instrument_id"]
                print(f"  {s} -> instrument_id = {inst_id_map[s]}")
            else:
                print(f"  {s} -> NOT FOUND in hist_spot_bars_5m")
        sym_col_1m = "instrument_id"
        sym_val_map_1m = inst_id_map
    else:
        print("[WARN] 1m has neither `symbol` nor `instrument_id`. Skipping 1m audit.")
        sym_col_1m = None
        sym_val_map_1m = {}

    print()
    overall = []
    for symbol in SYMBOLS:
        dates = fetch_distinct_dates(sb, "hist_spot_bars_5m", "symbol", symbol, LOOKBACK_DAYS)
        print(f"--- {symbol} ({len(dates)} trading days from 5m) ---")
        print(f"{'Date':<12} "
              f"{'5m N':>6} {'5m %':>7} {'5m_first':>10} {'5m_last':>10}  "
              f"{'1m N':>6} {'1m %':>7} {'1m_first':>10} {'1m_last':>10}")
        for d in dates:
            n5, f5_ts, l5_ts = fetch_bar_count_by_trade_date(
                sb, "hist_spot_bars_5m", "symbol", symbol, d)
            cov5 = n5 / EXPECTED_5M * 100
            f5 = (f5_ts or "")[11:16] if f5_ts else "-"
            l5 = (l5_ts or "")[11:16] if l5_ts else "-"

            if sym_col_1m and sym_val_map_1m.get(symbol) is not None:
                n1, f1_ts, l1_ts = fetch_bar_count_by_trade_date(
                    sb, "hist_spot_bars_1m", sym_col_1m, sym_val_map_1m[symbol], d)
            else:
                n1, f1_ts, l1_ts = 0, None, None
            cov1 = n1 / EXPECTED_1M * 100
            f1 = (f1_ts or "")[11:16] if f1_ts else "-"
            l1 = (l1_ts or "")[11:16] if l1_ts else "-"

            print(f"{d:<12} "
                  f"{n5:>6} {cov5:>6.1f}% {f5:>10} {l5:>10}  "
                  f"{n1:>6} {cov1:>6.1f}% {f1:>10} {l1:>10}")
            overall.append({"date": d, "symbol": symbol,
                            "n5": n5, "n1": n1, "cov5": cov5, "cov1": cov1})
        print()

    # Aggregate
    print("=" * 96)
    print("AGGREGATE")
    print("=" * 96)
    total_5 = sum(x["n5"] for x in overall)
    total_1 = sum(x["n1"] for x in overall)
    expected_5 = len(overall) * EXPECTED_5M
    expected_1 = len(overall) * EXPECTED_1M
    cov5 = total_5 / expected_5 * 100 if expected_5 else 0
    cov1 = total_1 / expected_1 * 100 if expected_1 else 0
    print(f"5m: {total_5}/{expected_5} = {cov5:.1f}%")
    print(f"1m: {total_1}/{expected_1} = {cov1:.1f}%")
    print()

    # === Era boundary breakdown (pre-04-07 vs post-04-07) ===
    print("Era boundary analysis (TD-029 boundary = 2026-04-07):")
    pre = [x for x in overall if x["date"] < "2026-04-07"]
    post = [x for x in overall if x["date"] >= "2026-04-07"]
    if pre:
        p_n5 = sum(x["n5"] for x in pre); p_n1 = sum(x["n1"] for x in pre)
        p_e5 = len(pre) * EXPECTED_5M; p_e1 = len(pre) * EXPECTED_1M
        print(f"  pre-04-07  ({len(pre)} sym-days): 5m {p_n5}/{p_e5} = {p_n5/p_e5*100:.1f}%, "
              f"1m {p_n1}/{p_e1} = {p_n1/p_e1*100:.1f}%")
    if post:
        o_n5 = sum(x["n5"] for x in post); o_n1 = sum(x["n1"] for x in post)
        o_e5 = len(post) * EXPECTED_5M; o_e1 = len(post) * EXPECTED_1M
        print(f"  post-04-07 ({len(post)} sym-days): 5m {o_n5}/{o_e5} = {o_n5/o_e5*100:.1f}%, "
              f"1m {o_n1}/{o_e1} = {o_n1/o_e1*100:.1f}%")
    print()

    # Diagnosis
    print("=" * 96)
    print("DIAGNOSIS:")
    if post and pre:
        post_5 = sum(x["n5"] for x in post) / (len(post) * EXPECTED_5M) * 100
        post_1 = sum(x["n1"] for x in post) / (len(post) * EXPECTED_1M) * 100
        if post_1 >= 80 and post_5 < 50:
            print("  -> POST-04-07: 1m FULL, 5m SHORT.")
            print("     ROOT CAUSE: build_spot_bars_mtf.py rollup is broken at TZ era boundary.")
            print("     Likely: rollup uses bar_ts in IST-stamped-as-UTC mode; post-04-07 is")
            print("     true UTC; rollup misses 5+:30h of bars.")
        elif post_1 < 50 and post_5 < 50:
            print("  -> POST-04-07: BOTH 1m AND 5m SHORT.")
            print("     ROOT CAUSE: capture_spot_1m or upstream broken at TZ era boundary.")
            print("     Less likely (capture is live and TD-019 closure validated 1m), but")
            print("     1m era-boundary handling may have a write-time bug.")
        else:
            print(f"  -> Post-04-07: 1m={post_1:.1f}%, 5m={post_5:.1f}%. Mixed.")
    print("=" * 96)


if __name__ == "__main__":
    main()
