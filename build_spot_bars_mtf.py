#!/usr/bin/env python3
"""
build_spot_bars_mtf.py
========================
Aggregates hist_spot_bars_1m into 5m and 15m OHLCV bars.
Writes to hist_spot_bars_5m and hist_spot_bars_15m.

Runtime: ~5-10 minutes (pure in-memory grouping, no heavy DB queries)
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
PAGE_SIZE    = 1000

INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fetch_all(sb, table, select, filters=None, order=None):
    all_rows, offset = [], 0
    while True:
        q = sb.table(table).select(select)
        if filters:
            for f in filters:
                method, *args = f
                q = getattr(q, method)(*args)
        if order:
            q = q.order(order)
        q = q.range(offset, offset + PAGE_SIZE - 1)
        for attempt in range(3):
            try:
                rows = q.execute().data
                break
            except Exception as e:
                if attempt == 2:
                    log(f"  ERROR: {e}")
                    return all_rows
                time.sleep(2 ** attempt)
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def get_bar_bucket(bar_ts_str, interval_mins):
    """Return the bar open time for the given interval bucket."""
    try:
        dt = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
        # Floor to interval boundary
        mins = dt.hour * 60 + dt.minute
        bucket_mins = (mins // interval_mins) * interval_mins
        bucket_h = bucket_mins // 60
        bucket_m = bucket_mins % 60
        # Return as string preserving the timezone format
        return dt.replace(hour=bucket_h, minute=bucket_m, second=0,
                          microsecond=0).isoformat()
    except:
        return None


def aggregate_bars(bars_1m, interval_mins):
    """
    Aggregate 1m OHLCV bars into interval_mins bars.
    Returns list of aggregated bar dicts.
    """
    # Group by (trade_date, bucket_ts)
    buckets = defaultdict(list)
    for bar in bars_1m:
        bucket = get_bar_bucket(bar["bar_ts"], interval_mins)
        if bucket:
            buckets[(bar["trade_date"], bucket)].append(bar)

    result = []
    for (trade_date, bucket_ts), group in sorted(buckets.items()):
        group = sorted(group, key=lambda b: b["bar_ts"])
        result.append({
            "trade_date": trade_date,
            "bar_ts":     bucket_ts,
            "open":       float(group[0]["open"]),
            "high":       max(float(b["high"]) for b in group),
            "low":        min(float(b["low"])  for b in group),
            "close":      float(group[-1]["close"]),
            "volume":     None,  # spot bars don't have volume
        })

    return result


def upsert_batch(sb, table, rows, conflict_cols):
    if not rows:
        return 0
    for attempt in range(3):
        try:
            sb.table(table).upsert(
                rows, on_conflict=conflict_cols
            ).execute()
            return len(rows)
        except Exception as e:
            if attempt == 2:
                log(f"  UPSERT ERROR ({table}): {e}")
                return 0
            time.sleep(2 ** attempt)
    return 0


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("build_spot_bars_mtf.py — 5m + 15m spot bars")
    log("=" * 65)

    for symbol, inst_id in INSTRUMENTS.items():
        log(f"\n{'='*20} {symbol} {'='*20}")

        # Load all 1m bars for this instrument
        log(f"  Loading hist_spot_bars_1m for {symbol}...")
        bars_1m = fetch_all(
            sb, "hist_spot_bars_1m",
            "trade_date,bar_ts,open,high,low,close",
            filters=[
                ("eq", "instrument_id", inst_id),
                ("eq", "is_pre_market", False),
            ],
            order="bar_ts"
        )
        log(f"  Loaded {len(bars_1m):,} 1m bars")

        # ── 5m bars ──────────────────────────────────────────────────────
        log(f"  Aggregating to 5m...")
        bars_5m = aggregate_bars(bars_1m, 5)
        log(f"  {len(bars_5m):,} 5m bars")

        # Add instrument_id and symbol
        rows_5m = []
        for bar in bars_5m:
            rows_5m.append({
                "instrument_id": inst_id,
                "symbol":        symbol,
                "trade_date":    bar["trade_date"],
                "bar_ts":        bar["bar_ts"],
                "open":          bar["open"],
                "high":          bar["high"],
                "low":           bar["low"],
                "close":         bar["close"],
                "volume":        bar["volume"],
            })

        # Upsert in batches of 500
        written_5m = 0
        for i in range(0, len(rows_5m), 500):
            written_5m += upsert_batch(
                sb, "hist_spot_bars_5m",
                rows_5m[i:i+500],
                "instrument_id,bar_ts"
            )
        log(f"  Written {written_5m:,} 5m bars")

        # ── 15m bars ─────────────────────────────────────────────────────
        log(f"  Aggregating to 15m...")
        bars_15m = aggregate_bars(bars_1m, 15)
        log(f"  {len(bars_15m):,} 15m bars")

        rows_15m = []
        for bar in bars_15m:
            rows_15m.append({
                "instrument_id": inst_id,
                "symbol":        symbol,
                "trade_date":    bar["trade_date"],
                "bar_ts":        bar["bar_ts"],
                "open":          bar["open"],
                "high":          bar["high"],
                "low":           bar["low"],
                "close":         bar["close"],
                "volume":        bar["volume"],
            })

        written_15m = 0
        for i in range(0, len(rows_15m), 500):
            written_15m += upsert_batch(
                sb, "hist_spot_bars_15m",
                rows_15m[i:i+500],
                "instrument_id,bar_ts"
            )
        log(f"  Written {written_15m:,} 15m bars")

    # Verify
    log("\n" + "=" * 65)
    log("Verification")
    log("=" * 65)
    for table in ["hist_spot_bars_5m", "hist_spot_bars_15m"]:
        r = sb.table(table).select("*", count="exact").limit(1).execute()
        log(f"  {table}: {r.count} rows")

    log("\nSpot MTF bars complete.")
    log("Next: python build_atm_option_bars_mtf.py")


if __name__ == "__main__":
    main()
