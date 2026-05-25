"""
adr003_phase1_zone_availability_audit.py — Phase 1 follow-up.

Same 60-day window as adr003_phase1_respect_rate.py.
Same data (ict_htf_zones).
Different aggregation: per-(symbol, timeframe, pattern_type):
  - zones_in_window       — count of zones whose validity overlaps the window
  - coverage_days         — distinct trading days with >=1 active zone of that type
  - coverage_pct          — coverage_days / total_trading_days_in_window
  - last_created_at       — most recent created_at for any zone of that type
  - last_valid_from       — most recent valid_from for any zone of that type
  - oldest_active_today   — earliest valid_from of zones still active right now

Purpose: separate "zone respect is low because zones don't exist" from
"zone respect is low because zones are misaligned with pivots."

Output: console table only. No markdown — appends a section to the existing
Phase 1 markdown report would be cleaner, but keeping it as a separate run
so the operator can choose whether to merge.

Run on Local Windows from C:\\GammaEnginePython:
    python adr003_phase1_zone_availability_audit.py
"""

import os
from datetime import datetime, date, timedelta
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client


load_dotenv()
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]

PAGE_SIZE = 1000
SYMBOLS = ["NIFTY", "SENSEX"]
LOOKBACK_TRADING_DAYS = 60

OUTPUT_MD = Path("docs/research") / f"adr003_phase1_zone_availability_{date.today().isoformat()}.md"


def parse_date(s):
    if s is None:
        return None
    if isinstance(s, date) and not isinstance(s, datetime):
        return s
    if isinstance(s, datetime):
        return s.date()
    return date.fromisoformat(s)


def parse_ts(s):
    if not isinstance(s, str):
        return s
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fetch_paginated(client, table, eq_filters=None, order_col="id"):
    rows = []
    offset = 0
    while True:
        q = client.table(table).select("*")
        for col, val in (eq_filters or []):
            q = q.eq(col, val)
        q = q.order(order_col).range(offset, offset + PAGE_SIZE - 1)
        batch = q.execute().data
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def trading_days_between(start, end, client, symbol):
    """
    Use hist_spot_bars_5m as the source of truth for trading days.
    Returns sorted list of distinct trade_dates with at least one bar in window for symbol.

    Rule 15 (Supabase 1000-row cap): paginates explicitly. Earlier version was a
    one-shot query that silently truncated at 1000 rows = ~13 trading days,
    biasing the sample to the earliest dates in the window.
    """
    seen = set()
    offset = 0
    while True:
        batch = client.table("hist_spot_bars_5m").select("trade_date") \
            .eq("symbol", symbol) \
            .gte("trade_date", start.isoformat()) \
            .lte("trade_date", end.isoformat()) \
            .order("trade_date") \
            .range(offset, offset + PAGE_SIZE - 1) \
            .execute().data
        if not batch:
            break
        for r in batch:
            seen.add(parse_date(r["trade_date"]))
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return sorted(seen)


def main():
    print("=== ADR-003 Phase 1 — Zone Availability Audit ===")
    today = date.today()
    window_start = today - timedelta(days=int(LOOKBACK_TRADING_DAYS * 1.45))
    window_end = today - timedelta(days=1)
    print(f"Run date: {today.isoformat()} | Window: {window_start} → {window_end}")

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    md = []
    md.append(f"# ADR-003 Phase 1 — Zone Availability Audit")
    md.append("")
    md.append(f"**Run date:** {today.isoformat()}  ")
    md.append(f"**Window:** {window_start} → {window_end}  ")
    md.append(f"**Purpose:** Separate \"zone respect is low because zones don't exist\" from \"zone respect is low because zones are misaligned.\" Companion to `adr003_phase1_respect_rate.py`.  ")
    md.append("")

    for symbol in SYMBOLS:
        print(f"\n--- {symbol} ---")

        # Trading days in window from spot bars (ground truth)
        trading_days = trading_days_between(window_start, window_end, client, symbol)
        n_days = len(trading_days)
        print(f"  trading days in window: {n_days}")

        # All zones for symbol
        zones_all = fetch_paginated(
            client, "ict_htf_zones",
            eq_filters=[("symbol", symbol)],
            order_col="valid_from",
        )
        for z in zones_all:
            z["valid_from"] = parse_date(z.get("valid_from"))
            z["valid_to"] = parse_date(z.get("valid_to"))
            z["broken_at_date"] = parse_date(z.get("broken_at_date"))
            z["created_at"] = parse_ts(z.get("created_at"))

        # Filter zones overlapping window (for the in-window count)
        in_window = []
        for z in zones_all:
            if z["valid_from"] is None:
                continue
            if z["valid_from"] > window_end:
                continue
            if z["valid_to"] and z["valid_to"] < window_start:
                continue
            if z["broken_at_date"] and z["broken_at_date"] < window_start:
                continue
            in_window.append(z)
        print(f"  zones overlapping window: {len(in_window)}")

        # Per-(tf, pt) aggregation
        agg = defaultdict(lambda: {
            "zones": 0,
            "active_dates": set(),
            "last_created_at": None,
            "last_valid_from": None,
        })

        for z in in_window:
            key = (z.get("timeframe") or "?", z.get("pattern_type") or "?")
            cell = agg[key]
            cell["zones"] += 1

            # Trading days this zone was active
            for d in trading_days:
                if z["valid_from"] and d < z["valid_from"]:
                    continue
                if z["valid_to"] and d > z["valid_to"]:
                    continue
                if z["broken_at_date"] and d >= z["broken_at_date"]:
                    continue
                cell["active_dates"].add(d)

            ca = z.get("created_at")
            if ca and (cell["last_created_at"] is None or ca > cell["last_created_at"]):
                cell["last_created_at"] = ca
            vf = z.get("valid_from")
            if vf and (cell["last_valid_from"] is None or vf > cell["last_valid_from"]):
                cell["last_valid_from"] = vf

        # Print
        md.append(f"## {symbol} — {n_days} trading days in window")
        md.append("")
        md.append("| Timeframe | Pattern | Zones | Coverage days | Coverage % | Last created (UTC) | Last valid_from |")
        md.append("|---|---|---|---|---|---|---|")
        print(f"\n  per-(tf, pt):")
        print(f"  {'tf':>4} {'pattern':<14} {'zones':>6} {'cov_days':>9} {'cov%':>7} {'last_created':<22} last_valid_from")
        for key in sorted(agg.keys()):
            tf, pt = key
            cell = agg[key]
            cov_days = len(cell["active_dates"])
            cov_pct = f"{100 * cov_days / n_days:.1f}%" if n_days else "n/a"
            lc = cell["last_created_at"].isoformat(timespec="minutes") if cell["last_created_at"] else "—"
            lvf = cell["last_valid_from"].isoformat() if cell["last_valid_from"] else "—"
            md.append(f"| {tf} | {pt} | {cell['zones']} | {cov_days} | {cov_pct} | {lc} | {lvf} |")
            print(f"  {tf:>4} {pt:<14} {cell['zones']:>6} {cov_days:>9} {cov_pct:>7} {lc:<22} {lvf}")
        md.append("")

    md.append("## Reading the table")
    md.append("")
    md.append("- **Coverage % near 100** → that zone type was effectively always available; respect rate from Phase 1 reflects calibration, not availability.")
    md.append("- **Coverage % low (<20%)** → that zone type was rarely or never present; Phase 1 respect rate cannot be interpreted, treat as data-quality flag, not edge evidence.")
    md.append("- **Last created stale** (e.g. weeks old) → producer for that pattern type is not running on cadence. Operational issue, not architectural.")
    md.append("- **Zones high but coverage % low** → many short-validity zones (e.g. PDH/PDL valid one day each); arithmetic of zones × validity, not a bug.")
    md.append("")
    md.append(f"*Generated by `adr003_phase1_zone_availability_audit.py` at {datetime.now().isoformat(timespec='seconds')}*")

    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"\nMarkdown report → {OUTPUT_MD}")


if __name__ == "__main__":
    main()
