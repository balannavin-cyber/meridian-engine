"""
verify_d_ob_thresholds.py

Quick verification: for the last 7 trading days, what was the actual
open-to-close body % per symbol? Confirms whether D-OB threshold
(>= 0.40%) explains why D-OB count is low.

Output:
  Per symbol, last 7 trading days, with body % and D-OB qualification flag.

Author: Session 15 quick check.
"""
from __future__ import annotations

import os
from datetime import datetime, date, timedelta

from dotenv import load_dotenv
from supabase import create_client


PAGE_SIZE = 1000
SYMBOLS = ["NIFTY", "SENSEX"]
OB_MIN_MOVE_PCT = 0.40
LOOKBACK_DAYS = 7


def main():
    load_dotenv()
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"],
    )

    print("=" * 78)
    print("D-OB threshold verification — last 7 trading days")
    print("=" * 78)
    print(f"OB threshold: |body %| >= {OB_MIN_MOVE_PCT}%")
    print()

    for symbol in SYMBOLS:
        print(f"--- {symbol} ---")

        # Get instrument_id
        r = sb.table("instruments").select("id").eq("symbol", symbol).execute()
        if not r.data:
            print(f"  no instrument row")
            continue
        inst_id = r.data[0]["id"]

        # Find recent trading dates from hist_spot_bars_5m (using symbol col)
        # Page through until we have LOOKBACK_DAYS distinct trade_dates.
        # A single day = 75 bars, so a single 1000-row page typically covers
        # ~13 days of bars but we don't rely on that — we paginate.
        dates_seen = []
        offset = 0
        while len(dates_seen) < LOOKBACK_DAYS and offset < 50000:
            rr = (sb.table("hist_spot_bars_5m").select("trade_date")
                  .eq("symbol", symbol).order("trade_date", desc=True)
                  .range(offset, offset + PAGE_SIZE - 1).execute())
            batch = rr.data or []
            if not batch:
                break
            for row in batch:
                d = row.get("trade_date")
                if d and d not in dates_seen:
                    dates_seen.append(d)
                if len(dates_seen) >= LOOKBACK_DAYS:
                    break
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        if not dates_seen:
            print("  no dates found")
            continue

        print(f"{'Date':<12} {'Open':>10} {'Close':>10} {'Body $':>10} {'Body %':>9} {'D-OB?':<10}")
        for d in sorted(dates_seen, reverse=True):
            # Pull all 5m bars for that day; first.open and last.close
            rb = (sb.table("hist_spot_bars_5m")
                  .select("bar_ts, open, close, high, low, trade_date")
                  .eq("symbol", symbol).eq("trade_date", d)
                  .order("bar_ts").limit(PAGE_SIZE).execute())
            bars = rb.data or []
            if not bars:
                print(f"{d:<12} (no bars)")
                continue
            try:
                op = float(bars[0]["open"])
                cl = float(bars[-1]["close"])
                hi = max(float(b["high"]) for b in bars)
                lo = min(float(b["low"]) for b in bars)
            except (TypeError, ValueError):
                print(f"{d:<12} (parse error)")
                continue
            body_dollar = cl - op
            body_pct = (cl - op) / op * 100 if op else 0
            range_pct = (hi - lo) / op * 100 if op else 0
            qualifies = abs(body_pct) >= OB_MIN_MOVE_PCT
            flag = ""
            if qualifies:
                flag = "BULL_OB" if body_pct > 0 else "BEAR_OB"
            else:
                flag = "no"
            print(f"{d:<12} {op:>10.2f} {cl:>10.2f} {body_dollar:>+10.2f} "
                  f"{body_pct:>+8.2f}% {flag:<10} (range {range_pct:.2f}%)")
        print()


if __name__ == "__main__":
    main()
