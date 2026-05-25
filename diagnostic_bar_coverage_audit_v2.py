"""
diagnostic_bar_coverage_audit_v2.py

v2 fix: column discovery for hist_spot_bars_1m (no `symbol` column in that
table; v1 assumed there was). Discovers the symbol-discriminator column at
runtime and uses it. If no obvious discriminator exists, dumps all columns
and exits with guidance.
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


def discover_columns(sb, table: str) -> list[str]:
    """Return list of column names for table, via select * limit 1."""
    r = sb.table(table).select("*").limit(1).execute()
    if not r.data:
        return []
    return list(r.data[0].keys())


def discover_symbol_column(sb, table: str) -> tuple[str | None, list[str]]:
    """Return (symbol_column_name, all_columns).
    Tries common symbol-discriminator names. Returns first match or None."""
    cols = discover_columns(sb, table)
    candidates = ["symbol", "instrument", "instrument_name", "ticker",
                  "index_name", "idx_name", "symbol_name", "symbol_id",
                  "tradingsymbol", "trading_symbol"]
    for c in candidates:
        if c in cols:
            return c, cols
    return None, cols


def discover_value_for_symbol(sb, table: str, sym_col: str, want: str) -> str | None:
    """Given known symbol_col, find the value used for `want` (e.g. NIFTY).
    Tries direct match first, then case variations."""
    # Try direct
    r = sb.table(table).select(sym_col).eq(sym_col, want).limit(1).execute()
    if r.data:
        return want
    # Try lowercase/uppercase
    for v in (want.lower(), want.upper(), want.capitalize()):
        if v == want:
            continue
        r = sb.table(table).select(sym_col).eq(sym_col, v).limit(1).execute()
        if r.data:
            return v
    # Try fuzzy: pull distinct-ish sample and find one containing the symbol
    r = sb.table(table).select(sym_col).limit(50).execute()
    seen = {row.get(sym_col) for row in (r.data or [])}
    for s in seen:
        if s and want.upper() in str(s).upper():
            return s
    return None


def fetch_distinct_dates(sb, table: str, sym_col: str, sym_val: str, n_days: int) -> list[str]:
    seen: set[str] = set()
    r = (sb.table(table).select("bar_ts").eq(sym_col, sym_val)
         .order("bar_ts", desc=True).limit(1).execute())
    if not r.data:
        return []
    last = datetime.fromisoformat(r.data[0]["bar_ts"].replace("Z", "+00:00")).replace(tzinfo=None)
    cutoff = last - timedelta(days=int(n_days * 1.6) + 5)
    offset = 0
    while offset < 200_000 and len(seen) < n_days:
        rr = (sb.table(table).select("bar_ts").eq(sym_col, sym_val)
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


def fetch_bar_ts(sb, table: str, sym_col: str, sym_val: str, trade_date: str) -> list[datetime]:
    rows = []
    offset = 0
    day_start = f"{trade_date}T00:00:00+00:00"
    day_end = f"{trade_date}T23:59:59+00:00"
    while True:
        r = (sb.table(table).select("bar_ts").eq(sym_col, sym_val)
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
        if dt_time(9, 15) <= dt.time() <= dt_time(15, 30):
            out.append(dt)
    return out


def main():
    sb = get_client()
    print("=" * 96)
    print("DIAGNOSTIC v2 — hist_spot_bars_5m + hist_spot_bars_1m coverage")
    print("=" * 96)

    # Discover schema
    print("[INFO] schema discovery ...")
    sym_col_5m, cols_5m = discover_symbol_column(sb, "hist_spot_bars_5m")
    sym_col_1m, cols_1m = discover_symbol_column(sb, "hist_spot_bars_1m")
    print(f"  hist_spot_bars_5m columns: {cols_5m}")
    print(f"  hist_spot_bars_5m symbol column: {sym_col_5m!r}")
    print(f"  hist_spot_bars_1m columns: {cols_1m}")
    print(f"  hist_spot_bars_1m symbol column: {sym_col_1m!r}")
    print()

    if sym_col_1m is None:
        print("[FATAL] could not auto-detect a symbol-discriminator column for")
        print("        hist_spot_bars_1m. The table may use a column name not in")
        print("        the candidate list. Inspect the columns above and tell me")
        print("        which one to use, or this script can run on 5m only.")
        print()
        print("[INFO] proceeding with 5m-only audit since 5m has 'symbol' column.")
        sym_col_1m_real = None
    else:
        # Find the value the 1m table uses for each logical symbol
        sym_val_map_1m = {}
        for s in SYMBOLS:
            v = discover_value_for_symbol(sb, "hist_spot_bars_1m", sym_col_1m, s)
            sym_val_map_1m[s] = v
            print(f"  hist_spot_bars_1m.{sym_col_1m} value for {s}: {v!r}")
        sym_col_1m_real = sym_col_1m
    print()

    # Use 5m column we know (`symbol`) for sym_val mapping
    sym_val_map_5m = {s: s for s in SYMBOLS}

    overall = []
    for symbol in SYMBOLS:
        # Discover dates from 5m (always works)
        dates = fetch_distinct_dates(sb, "hist_spot_bars_5m", "symbol", symbol, LOOKBACK_DAYS)
        print(f"--- {symbol} ({len(dates)} trading days from 5m) ---")
        print(f"{'Date':<12} "
              f"{'5m N':>6} {'5m %':>7} {'5m_first':>10} {'5m_last':>10}  "
              f"{'1m N':>6} {'1m %':>7} {'1m_first':>10} {'1m_last':>10}")
        for d in dates:
            ts5 = fetch_bar_ts(sb, "hist_spot_bars_5m", "symbol", symbol, d)
            n5 = len(ts5)
            cov5 = n5 / EXPECTED_5M * 100
            f5 = ts5[0].strftime("%H:%M") if ts5 else "-"
            l5 = ts5[-1].strftime("%H:%M") if ts5 else "-"

            if sym_col_1m_real and sym_val_map_1m.get(symbol):
                ts1 = fetch_bar_ts(sb, "hist_spot_bars_1m",
                                   sym_col_1m_real, sym_val_map_1m[symbol], d)
            else:
                ts1 = []
            n1 = len(ts1)
            cov1 = n1 / EXPECTED_1M * 100
            f1 = ts1[0].strftime("%H:%M") if ts1 else "-"
            l1 = ts1[-1].strftime("%H:%M") if ts1 else "-"

            print(f"{d:<12} "
                  f"{n5:>6} {cov5:>6.1f}% {f5:>10} {l5:>10}  "
                  f"{n1:>6} {cov1:>6.1f}% {f1:>10} {l1:>10}")
            overall.append({"date": d, "symbol": symbol, "n5": n5, "n1": n1,
                            "cov5": cov5, "cov1": cov1})
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
    print(f"5m total: {total_5}/{expected_5} = {cov5:.1f}%")
    print(f"1m total: {total_1}/{expected_1} = {cov1:.1f}%")
    print()

    # Hour distribution on most-recent day
    if overall:
        most_recent = max(set(x["date"] for x in overall))
        print(f"Hour distribution on {most_recent}:")
        for symbol in SYMBOLS:
            for table, label, sym_col, sym_val in [
                ("hist_spot_bars_5m", "5m", "symbol", symbol),
                ("hist_spot_bars_1m", "1m", sym_col_1m_real, sym_val_map_1m.get(symbol) if sym_col_1m_real else None),
            ]:
                if sym_col is None or sym_val is None:
                    continue
                ts = fetch_bar_ts(sb, table, sym_col, sym_val, most_recent)
                hdist = defaultdict(int)
                for dt in ts:
                    hdist[dt.hour] += 1
                print(f"  {symbol} {label} (total {len(ts)}):")
                for hour in range(9, 16):
                    n = hdist.get(hour, 0)
                    print(f"    {hour:02d}h: {n:>3} {'#' * min(n, 60)}")
    print()

    # Diagnosis
    print("=" * 96)
    print("DIAGNOSIS:")
    if cov1 >= 80 and cov5 < 50:
        print("  -> 1m FULL, 5m SHORT. ROOT CAUSE: build_spot_bars_mtf.py rollup.")
        print("     Inspect script for date-range filters or LIMIT clauses.")
    elif cov1 < 50 and cov5 < 50:
        print("  -> Both SHORT. ROOT CAUSE: capture_spot_1m or upstream.")
    elif cov5 >= 80 and cov1 >= 80:
        print("  -> Both >= 80%. ADR-003 Phase 1 v2 query was the issue.")
    else:
        print(f"  -> Mixed (1m={cov1:.1f}%, 5m={cov5:.1f}%). Inspect per-symbol asymmetry.")
    print("=" * 96)


if __name__ == "__main__":
    main()
