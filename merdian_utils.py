"""
merdian_utils.py  v3
MERDIAN Shared Utilities — data-driven expiry date lookup.

Replaces hardcoded nearest_expiry(td, symbol) which broke when
NIFTY switched from Thursday to Tuesday expiry in September 2025.

Usage:
    from merdian_utils import build_expiry_index_simple, nearest_expiry_db

    expiry_idx = build_expiry_index_simple(sb, inst[symbol])
    ed = nearest_expiry_db(td, expiry_idx)
"""

import bisect
import time
from datetime import date


def build_expiry_index_simple(sb, inst_id, page_size=1000):
    """
    Fetch all distinct weekly expiry dates for this instrument.

    Queries one row per month across the full date range to avoid
    scanning 54M rows. Fetches expiry_date from one sample row per
    calendar month — fast and avoids statement timeout.

    Returns sorted list of date objects (weekly expiries only).
    """
    all_dates = set()

    # Sample one trade_date per month across Apr 2025 – Mar 2026
    # Fetch expiry dates for that sample date only — fast indexed query
    sample_dates = [
        "2025-04-03", "2025-05-02", "2025-06-02",
        "2025-07-01", "2025-08-01", "2025-09-01",
        "2025-10-01", "2025-11-03", "2025-12-01",
        "2026-01-02", "2026-02-02", "2026-03-03",
    ]

    for sample_date in sample_dates:
        rows = None
        for attempt in range(4):
            try:
                rows = (
                    sb.table("hist_option_bars_1m")
                    .select("expiry_date")
                    .eq("instrument_id", str(inst_id))
                    .gte("trade_date", sample_date)
                    .lte("trade_date", sample_date)
                    .limit(page_size)
                    .execute().data
                )
                break
            except Exception:
                if attempt == 3:
                    rows = []
                time.sleep(2 ** attempt)

        for r in (rows or []):
            if r.get("expiry_date"):
                try:
                    all_dates.add(date.fromisoformat(r["expiry_date"]))
                except (ValueError, TypeError):
                    pass

    if not all_dates:
        return []

    # Filter to weekly expiries only (gap <= 10 days between consecutive dates)
    sorted_dates = sorted(all_dates)
    weekly = []
    for i, d in enumerate(sorted_dates):
        if i == len(sorted_dates) - 1:
            weekly.append(d)
        elif (sorted_dates[i + 1] - d).days <= 10:
            weekly.append(d)

    return weekly


def nearest_expiry_db(td, expiry_index):
    """
    Find the nearest weekly expiry on or after trade_date td.

    Args:
        td:           date — trading date
        expiry_index: sorted list of dates from build_expiry_index_simple()

    Returns:
        date — nearest expiry >= td
    """
    if not expiry_index:
        return None

    idx = bisect.bisect_left(expiry_index, td)
    if idx < len(expiry_index):
        return expiry_index[idx]

    return expiry_index[-1]
