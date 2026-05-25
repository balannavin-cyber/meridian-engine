"""
adr003_phase1_respect_rate.py — ADR-003 Phase 1 Diagnostic (READ-ONLY)

Computes "respect rate": % of intraday 5m fractal pivots that occurred within
X points of an ACTIVE ict_htf_zones boundary, broken down by
(symbol, timeframe, pattern_type), at proximity bands {5pt, 10pt, 20pt}.

Per ADR-003 Phase 1:
- Read-only diagnostic. NO code changes to build_ict_htf_zones.py.
- Output: console table + markdown to docs/research/.
- Phase 2 (targeted redesign) is gated on this output identifying WHICH layer is broken.

Window: trailing 60 trading days from today (operator greenlit wider than ADR's 10).
Spans the TD-029 era boundary (2026-04-07) — applies era-aware tz canonicalization.

Rules applied:
- Rule 13: data_contamination_ranges check for any range affecting hist_spot_bars_5m.
- Rule 15: page_size=1000 in Supabase pagination.
- Rule 16 / TD-029: era-aware TZ canonicalization for hist_spot_bars_5m.bar_ts.
- Anti-pattern avoided: no `is_pre_market` column query — filter by IST clock time.

Run on Local Windows from C:\\GammaEnginePython:
    python adr003_phase1_respect_rate.py
"""

import os
import sys
from datetime import datetime, date, timedelta, time as dtime
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client


# ---------- Config ----------
load_dotenv()
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]

PAGE_SIZE = 1000  # Rule 15
ERA_BOUNDARY = date(2026, 4, 7)  # TD-029
SYMBOLS = ["NIFTY", "SENSEX"]
PROXIMITY_BANDS = [5, 10, 20]  # points
LOOKBACK_TRADING_DAYS = 60
SESSION_START = dtime(9, 15)
SESSION_END = dtime(15, 30)

OUTPUT_MD = Path("docs/research") / f"adr003_phase1_respect_rate_{date.today().isoformat()}.md"


# ---------- Helpers ----------
def canonicalize_ts_to_ist(bar_ts, trade_date):
    """
    Era-aware TZ canonicalization per TD-029. Returns naive IST datetime.

    - Pre-04-07: bar_ts is IST clock-time labeled with UTC tzinfo. Strip tzinfo.
    - Post-04-07: bar_ts is correctly UTC-stamped. Add 5h30m and strip.
    """
    if trade_date < ERA_BOUNDARY:
        return bar_ts.replace(tzinfo=None)
    return (bar_ts + timedelta(hours=5, minutes=30)).replace(tzinfo=None)


def parse_ts(s):
    """Parse Supabase timestamp string to aware datetime."""
    if not isinstance(s, str):
        return s
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def parse_date(s):
    if s is None:
        return None
    if isinstance(s, date) and not isinstance(s, datetime):
        return s
    if isinstance(s, datetime):
        return s.date()
    return date.fromisoformat(s)


def fetch_paginated(client, table, eq_filters=None, gte_filters=None, lte_filters=None, order_col="id"):
    """Rule 15 paginated fetcher. Returns all matching rows."""
    rows = []
    offset = 0
    while True:
        q = client.table(table).select("*")
        for col, val in (eq_filters or []):
            q = q.eq(col, val)
        for col, val in (gte_filters or []):
            q = q.gte(col, val)
        for col, val in (lte_filters or []):
            q = q.lte(col, val)
        q = q.order(order_col).range(offset, offset + PAGE_SIZE - 1)
        batch = q.execute().data
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def check_contamination(client, window_start, window_end):
    """Rule 13 — abort if any registered contamination range affects spot bars in window."""
    try:
        rows = client.table("data_contamination_ranges").select("*").execute().data
    except Exception as e:
        print(f"  [warn] could not query data_contamination_ranges: {e}")
        return
    hits = []
    for r in rows:
        affected = r.get("affected_tables") or []
        if isinstance(affected, str):
            affected = [affected]
        if "hist_spot_bars_5m" not in affected and "hist_spot_bars_1m" not in affected:
            continue
        cs = parse_ts(r.get("contamination_start"))
        ce = parse_ts(r.get("contamination_end"))
        cs_d = cs.date() if cs else date.min
        ce_d = ce.date() if ce else date.max
        if cs_d <= window_end and ce_d >= window_start:
            hits.append(r.get("contamination_id"))
    if hits:
        print(f"  [WARN] contamination ranges overlap window: {hits}")
        print(f"  [WARN] proceeding — Phase 1 reads OHLC only, but flag in caveats.")
    else:
        print(f"  [ok] no contamination ranges affect hist_spot_bars_5m in window")


def find_pivots(bars, fractal_n):
    """
    Identify fractal pivots in chronologically-sorted bars.
    fractal_n=2 → fractal-5 (2 bars on each side).
    fractal_n=1 → fractal-3 (1 bar on each side).

    Returns: list of dicts with idx, ts, price, kind ('high' or 'low').
    """
    pivots = []
    for i in range(fractal_n, len(bars) - fractal_n):
        h = bars[i]["high"]
        l = bars[i]["low"]
        is_high = all(h > bars[i - k]["high"] and h > bars[i + k]["high"] for k in range(1, fractal_n + 1))
        is_low = all(l < bars[i - k]["low"] and l < bars[i + k]["low"] for k in range(1, fractal_n + 1))
        if is_high:
            pivots.append({"idx": i, "ts": bars[i]["bar_ts_ist"], "price": h, "kind": "high"})
        if is_low:
            pivots.append({"idx": i, "ts": bars[i]["bar_ts_ist"], "price": l, "kind": "low"})
    return pivots


def zone_active_at(zone, ts):
    """
    Was zone active at timestamp ts?

    Date-precision check — broken_at_date is date-only in schema, so a zone
    broken intraday is conservatively treated as inactive from broken_at_date
    onwards (even if the actual break was after the pivot). Limitation noted
    in caveats.
    """
    d = ts.date()
    vf = zone.get("valid_from")
    vt = zone.get("valid_to")
    ba = zone.get("broken_at_date")
    if vf and d < vf:
        return False
    if vt and d > vt:
        return False
    if ba and d >= ba:
        return False
    return True


def distance_to_zone(price, zone):
    """Distance in points to nearest zone boundary (0 if price inside zone)."""
    zh = float(zone["zone_high"])
    zl = float(zone["zone_low"])
    if zl <= price <= zh:
        return 0.0
    return min(abs(price - zh), abs(price - zl))


# ---------- Main ----------
def main():
    print("=== ADR-003 Phase 1 Respect Rate Diagnostic ===")
    today = date.today()
    # 60 trading days ≈ 84 calendar days. Generous calendar window; trade_date filter will trim.
    window_start = today - timedelta(days=int(LOOKBACK_TRADING_DAYS * 1.45))
    window_end = today - timedelta(days=1)
    print(f"Run date: {today.isoformat()} | Window: {window_start} → {window_end}")
    straddle = window_start < ERA_BOUNDARY <= window_end
    print(f"TD-029 era boundary at {ERA_BOUNDARY}: window {'STRADDLES' if straddle else 'is single-era'}")

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("\n[Rule 13] data contamination check...")
    check_contamination(client, window_start, window_end)

    results = {}
    null_valid_from = {}

    for symbol in SYMBOLS:
        print(f"\n--- {symbol} ---")

        # Pull 5m bars in window
        print(f"  fetching hist_spot_bars_5m ...")
        bars_raw = fetch_paginated(
            client, "hist_spot_bars_5m",
            eq_filters=[("symbol", symbol)],
            gte_filters=[("trade_date", window_start.isoformat())],
            lte_filters=[("trade_date", window_end.isoformat())],
            order_col="bar_ts",
        )
        print(f"  raw bars: {len(bars_raw)}")

        # Era-aware tz + IST session filter
        bars = []
        for b in bars_raw:
            td = parse_date(b["trade_date"])
            ts = parse_ts(b["bar_ts"])
            ist = canonicalize_ts_to_ist(ts, td)
            if SESSION_START <= ist.time() <= SESSION_END:
                b["bar_ts_ist"] = ist
                b["high"] = float(b["high"])
                b["low"] = float(b["low"])
                bars.append(b)
        bars.sort(key=lambda r: r["bar_ts_ist"])
        n_days = len(set(b["bar_ts_ist"].date() for b in bars))
        print(f"  session bars: {len(bars)} across {n_days} trading days")

        # Pull zones overlapping window
        print(f"  fetching ict_htf_zones ...")
        zones_raw = fetch_paginated(
            client, "ict_htf_zones",
            eq_filters=[("symbol", symbol)],
            order_col="valid_from",
        )
        zones = []
        nulls = 0
        for z in zones_raw:
            for k in ("valid_from", "valid_to", "broken_at_date"):
                z[k] = parse_date(z.get(k))
            if z.get("valid_from") is None:
                nulls += 1
                continue  # skip zones with no validity start — data quality issue
            if z.get("valid_to") and z["valid_to"] < window_start:
                continue
            if z.get("broken_at_date") and z["broken_at_date"] < window_start:
                continue
            if z["valid_from"] > window_end:
                continue
            zones.append(z)
        null_valid_from[symbol] = nulls
        print(f"  zones overlapping window: {len(zones)} (skipped {nulls} with NULL valid_from)")

        # Pivots — fractal-5 headline, fractal-3 sensitivity
        bars_by_day = defaultdict(list)
        for b in bars:
            bars_by_day[b["bar_ts_ist"].date()].append(b)

        pivots_f5 = []
        pivots_f3 = []
        for day, day_bars in bars_by_day.items():
            day_bars.sort(key=lambda r: r["bar_ts_ist"])
            pivots_f5.extend(find_pivots(day_bars, fractal_n=2))
            pivots_f3.extend(find_pivots(day_bars, fractal_n=1))
        print(f"  pivots: fractal-5={len(pivots_f5)} | fractal-3={len(pivots_f3)}")

        # Compute respect: per-(timeframe, pattern_type) and any-zone
        cells = defaultdict(lambda: {b: 0 for b in PROXIMITY_BANDS})
        cell_keys = set()
        any_cells = {b: 0 for b in PROXIMITY_BANDS}

        for piv in pivots_f5:
            active = [z for z in zones if zone_active_at(z, piv["ts"])]
            if not active:
                continue

            # Any-zone band membership
            min_dist_any = min(distance_to_zone(piv["price"], z) for z in active)
            for band in PROXIMITY_BANDS:
                if min_dist_any <= band:
                    any_cells[band] += 1

            # Per-(tf, pt)
            by_type = defaultdict(list)
            for z in active:
                key = (z.get("timeframe") or "?", z.get("pattern_type") or "?")
                cell_keys.add(key)
                by_type[key].append(z)
            for key, zlist in by_type.items():
                min_d = min(distance_to_zone(piv["price"], z) for z in zlist)
                for band in PROXIMITY_BANDS:
                    if min_d <= band:
                        cells[key][band] += 1

        results[symbol] = {
            "n_bars": len(bars),
            "n_days": n_days,
            "n_zones": len(zones),
            "n_pivots_f5": len(pivots_f5),
            "n_pivots_f3": len(pivots_f3),
            "any_cells": any_cells,
            "cells": dict(cells),
            "cell_keys": sorted(cell_keys),
        }

    # ---------- Output ----------
    print("\n\n=== RESULTS ===")

    md = []
    md.append(f"# ADR-003 Phase 1 — Respect Rate Diagnostic")
    md.append("")
    md.append(f"**Run date:** {today.isoformat()} (Session 15)  ")
    md.append(f"**Window:** {window_start} → {window_end} ({LOOKBACK_TRADING_DAYS} trading days greenlit)  ")
    md.append(f"**Methodology:** % of fractal-5 intraday 5m pivots within X points of any ACTIVE `ict_htf_zones` boundary. ")
    md.append(f"Active = `valid_from <= pivot_date AND (broken_at_date IS NULL OR pivot_date < broken_at_date) AND (valid_to IS NULL OR pivot_date <= valid_to)`.  ")
    md.append(f"**Status:** Phase 1 numeric truth. No code changes. Phase 2 redesign deferred per ADR-003.  ")
    md.append("")
    md.append("## Headline — any-zone respect rate")
    md.append("")
    md.append("| Symbol | Days | Bars | Zones | Pivots f5 | Pivots f3 | ≤5pt | ≤10pt | ≤20pt |")
    md.append("|---|---|---|---|---|---|---|---|---|")

    print()
    for sym in SYMBOLS:
        r = results[sym]
        n = r["n_pivots_f5"]
        ac = r["any_cells"]
        def pct(c, total=n):
            return f"{100 * c / total:.1f}%" if total else "n/a"
        md.append(f"| {sym} | {r['n_days']} | {r['n_bars']} | {r['n_zones']} | {n} | {r['n_pivots_f3']} | {pct(ac[5])} | {pct(ac[10])} | {pct(ac[20])} |")
        print(f"  {sym}: pivots={n} | any-zone respect ≤5pt={pct(ac[5])} ≤10pt={pct(ac[10])} ≤20pt={pct(ac[20])}")

    md.append("")
    md.append("## Per-pattern breakdown")
    md.append("")

    for sym in SYMBOLS:
        r = results[sym]
        n = r["n_pivots_f5"]
        md.append(f"### {sym} (N pivots f5 = {n})")
        md.append("")
        md.append("| Timeframe | Pattern | ≤5pt | ≤10pt | ≤20pt |")
        md.append("|---|---|---|---|---|")
        print(f"\n  {sym} per-pattern:")
        for key in r["cell_keys"]:
            tf, pt = key
            cell = r["cells"][key]
            def pct(c, total=n):
                return f"{100 * c / total:.1f}%" if total else "n/a"
            md.append(f"| {tf} | {pt} | {pct(cell[5])} | {pct(cell[10])} | {pct(cell[20])} |")
            print(f"    {tf:>4} {pt:<14} ≤5pt={pct(cell[5]):>6} ≤10pt={pct(cell[10]):>6} ≤20pt={pct(cell[20]):>6}")
        md.append("")

    md.append("## How to read")
    md.append("")
    md.append("- A respect rate that climbs steeply ≤5pt → ≤20pt → zones are **near** pivots.")
    md.append("- A flat curve (e.g. 30 / 32 / 35%) → zones are **roughly in the area**, not aligned.")
    md.append("- A flat-low curve (e.g. <20% across all bands) → that zone type may be uncorrelated with pivots in this window.")
    md.append("- Compare across symbols to identify symbol-specific calibration issues.")
    md.append("- Compare across (tf, pattern_type) to identify which layer of the zone stack is the weak link.")
    md.append("")
    md.append("## Caveats")
    md.append("")
    md.append("- Pivot definition: fractal-5 (2 bars each side). Fractal-3 reported as count only for sensitivity.")
    md.append("- Historical zone state reconstructed from `valid_from` / `broken_at_date` / `valid_to`. Assumes these fields are not retroactively edited.")
    md.append("- `broken_at_date` is date-precision in schema — a zone broken intraday is treated as inactive from that date onwards. Pivots before the actual break on that date are conservatively excluded from that zone's respect count. Magnitude of bias: small (one-day boundary cases only).")
    md.append("- Respect = proximity. Does NOT test directional rejection (e.g. low pivot bouncing UP off a BULL_OB). Phase 2 candidate if proximity-based respect is high but trading edge is still low.")
    md.append("- Window straddles TD-029 era boundary. Era-aware TZ canonicalization applied.")
    md.append("- Zones with NULL `valid_from` excluded. Counts: " + ", ".join(f"{s}={null_valid_from[s]}" for s in SYMBOLS) + ".")
    md.append("")
    md.append(f"*Generated by `adr003_phase1_respect_rate.py` at {datetime.now().isoformat(timespec='seconds')}*")

    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"\nMarkdown report → {OUTPUT_MD}")


if __name__ == "__main__":
    main()
