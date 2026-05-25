"""
diagnostic_d_zone_replay_v2.py

v2 fix: column discovery for hist_spot_bars_1m. Falls back to hist_spot_bars_5m
if 1m schema not auto-detectable. 5m is sufficient for daily aggregation
(each daily candle aggregates 75 bars = ~9000pts per symbol, plenty of
precision for OB candidate detection).
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
BODY_THRESHOLD_PCT = 0.40


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def discover_symbol_column(sb, table: str) -> tuple[str | None, list[str]]:
    r = sb.table(table).select("*").limit(1).execute()
    if not r.data:
        return None, []
    cols = list(r.data[0].keys())
    candidates = ["symbol", "instrument", "instrument_name", "ticker",
                  "index_name", "idx_name", "symbol_name", "symbol_id",
                  "tradingsymbol", "trading_symbol"]
    for c in candidates:
        if c in cols:
            return c, cols
    return None, cols


def discover_value_for_symbol(sb, table: str, sym_col: str, want: str) -> str | None:
    r = sb.table(table).select(sym_col).eq(sym_col, want).limit(1).execute()
    if r.data:
        return want
    for v in (want.lower(), want.upper(), want.capitalize()):
        if v == want:
            continue
        r = sb.table(table).select(sym_col).eq(sym_col, v).limit(1).execute()
        if r.data:
            return v
    r = sb.table(table).select(sym_col).limit(50).execute()
    seen = {row.get(sym_col) for row in (r.data or [])}
    for s in seen:
        if s and want.upper() in str(s).upper():
            return s
    return None


def fetch_bars_window(sb, table: str, sym_col: str, sym_val: str,
                      start_dt: datetime, end_dt: datetime) -> list[dict]:
    rows = []
    offset = 0
    while True:
        r = (sb.table(table)
             .select("bar_ts, open, high, low, close")
             .eq(sym_col, sym_val)
             .gte("bar_ts", start_dt.isoformat())
             .lte("bar_ts", end_dt.isoformat())
             .order("bar_ts")
             .range(offset, offset + PAGE_SIZE - 1).execute())
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > 500_000:
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


def aggregate_daily(bars: list[dict]) -> list[dict]:
    by_date: dict[date_t, list[dict]] = defaultdict(list)
    for b in bars:
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


def find_d_ob_candidates(daily: list[dict]):
    bear, bull = [], []
    for i in range(len(daily) - 1):
        k = daily[i]
        k1 = daily[i + 1]
        k_up = k["close"] > k["open"]
        k1_down = k1["open"] > k1["close"]
        k_down = k["close"] < k["open"]
        k1_up = k1["close"] > k1["open"]
        k1_body = abs(k1["close"] - k1["open"])
        k1_body_pct = k1_body / k1["close"] * 100 if k1["close"] else 0
        if k_up and k1_down and k1_body_pct >= BODY_THRESHOLD_PCT and k1["low"] < k["low"]:
            bear.append({
                "candidate_date": k["date"], "trigger_date": k1["date"],
                "zone_low": k["low"], "zone_high": k["high"],
                "k_body_pct": (k["close"] - k["open"]) / k["open"] * 100,
                "k1_body_pct": -k1_body_pct,
            })
        if k_down and k1_up and k1_body_pct >= BODY_THRESHOLD_PCT and k1["high"] > k["high"]:
            bull.append({
                "candidate_date": k["date"], "trigger_date": k1["date"],
                "zone_low": k["low"], "zone_high": k["high"],
                "k_body_pct": (k["close"] - k["open"]) / k["open"] * 100,
                "k1_body_pct": k1_body_pct,
            })
    return bear, bull


def fetch_actual_d_zones(sb, symbol: str, start_date: str, end_date: str):
    rows = []
    offset = 0
    while True:
        r = (sb.table("ict_htf_zones").select("*")
             .eq("symbol", symbol).eq("timeframe", "D")
             .gte("source_bar_date", start_date)
             .lte("source_bar_date", end_date)
             .range(offset, offset + PAGE_SIZE - 1).execute())
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


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


def main():
    sb = get_client()
    print("=" * 96)
    print("DIAGNOSTIC v2 — D BEAR_OB / D BULL_OB candidate replay (TD-031)")
    print("=" * 96)
    print(f"Lookback: {LOOKBACK_DAYS} trading days, both symbols")
    print(f"OB body threshold: {BODY_THRESHOLD_PCT}%")
    print()

    # Schema discovery — try 1m first, fall back to 5m
    sym_col_1m, cols_1m = discover_symbol_column(sb, "hist_spot_bars_1m")
    sym_col_5m, _ = discover_symbol_column(sb, "hist_spot_bars_5m")
    print(f"[INFO] 1m symbol col: {sym_col_1m!r}, 5m symbol col: {sym_col_5m!r}")

    use_1m = sym_col_1m is not None
    if use_1m:
        sym_val_map = {s: discover_value_for_symbol(sb, "hist_spot_bars_1m", sym_col_1m, s)
                       for s in SYMBOLS}
        for s, v in sym_val_map.items():
            print(f"  1m.{sym_col_1m} for {s}: {v!r}")
            if v is None:
                use_1m = False
                break
    if not use_1m:
        print("[INFO] falling back to hist_spot_bars_5m for daily aggregation.")
        source_table = "hist_spot_bars_5m"
        source_sym_col = sym_col_5m or "symbol"
        sym_val_map = {s: s for s in SYMBOLS}
    else:
        source_table = "hist_spot_bars_1m"
        source_sym_col = sym_col_1m
    print(f"[INFO] aggregating from {source_table} via column {source_sym_col!r}")
    print()

    end = datetime.now().replace(hour=23, minute=59, second=59)
    start = end - timedelta(days=int(LOOKBACK_DAYS * 1.6) + 5)

    for symbol in SYMBOLS:
        print(f"--- {symbol} ---")
        sym_val = sym_val_map[symbol]
        bars = fetch_bars_window(sb, source_table, source_sym_col, sym_val, start, end)
        daily = aggregate_daily(bars)
        daily = daily[-LOOKBACK_DAYS:]
        print(f"Daily OHLC ({len(daily)} sessions, source={source_table}):")
        print(f"{'Date':<12} {'Open':>10} {'High':>10} {'Low':>10} {'Close':>10} "
              f"{'Body%':>8} {'src_bars':>9}")
        for d in daily:
            body_pct = (d["close"] - d["open"]) / d["open"] * 100 if d["open"] else 0
            print(f"{d['date']!s:<12} {d['open']:>10.2f} {d['high']:>10.2f} "
                  f"{d['low']:>10.2f} {d['close']:>10.2f} {body_pct:>+7.2f}% {d['n_bars']:>9}")
        print()

        bear, bull = find_d_ob_candidates(daily)
        print(f"D BEAR_OB candidates ({len(bear)}):")
        for c in bear:
            print(f"  K={c['candidate_date']!s} K+1={c['trigger_date']!s} "
                  f"zone={c['zone_low']:.2f}-{c['zone_high']:.2f} "
                  f"K_body={c['k_body_pct']:+.2f}% K+1_body={c['k1_body_pct']:+.2f}%")
        if not bear:
            print("  none")
        print()
        print(f"D BULL_OB candidates ({len(bull)}):")
        for c in bull:
            print(f"  K={c['candidate_date']!s} K+1={c['trigger_date']!s} "
                  f"zone={c['zone_low']:.2f}-{c['zone_high']:.2f} "
                  f"K_body={c['k_body_pct']:+.2f}% K+1_body={c['k1_body_pct']:+.2f}%")
        if not bull:
            print("  none")
        print()

        if daily:
            window_start = str(daily[0]["date"])
            window_end = str(daily[-1]["date"])
            actual = fetch_actual_d_zones(sb, symbol, window_start, window_end)
            actual_bear = [z for z in actual if (z.get("pattern_type") or "").upper() == "BEAR_OB"]
            actual_bull = [z for z in actual if (z.get("pattern_type") or "").upper() == "BULL_OB"]
            print(f"Actual D zones in ict_htf_zones for {window_start}..{window_end}: "
                  f"BEAR_OB={len(actual_bear)}, BULL_OB={len(actual_bull)}")
            for z in actual_bear + actual_bull:
                print(f"  {(z.get('pattern_type') or '?'):<10} "
                      f"source_bar_date={z.get('source_bar_date')} "
                      f"zone={z.get('zone_low')}-{z.get('zone_high')} status={z.get('status')}")
            cand_bear_dates = {c["candidate_date"] for c in bear}
            cand_bull_dates = {c["candidate_date"] for c in bull}
            actual_bear_dates = {parse_str_date(z.get("source_bar_date")) for z in actual_bear}
            actual_bull_dates = {parse_str_date(z.get("source_bar_date")) for z in actual_bull}
            missing_bear = cand_bear_dates - {d for d in actual_bear_dates if d}
            missing_bull = cand_bull_dates - {d for d in actual_bull_dates if d}
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
    print("If candidates >> actual: detector logic in build_ict_htf_zones.py is")
    print("filtering out valid D zones (breach filter at write-time most likely).")
    print("If candidates ~= actual: detector is correct; daily structure is just rare.")
    print("=" * 96)


if __name__ == "__main__":
    main()
