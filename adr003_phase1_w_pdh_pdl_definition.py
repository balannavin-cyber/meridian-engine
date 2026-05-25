"""
adr003_phase1_w_pdh_pdl_definition.py — Phase 1 deep dive on the broken layer.

The Phase 1 respect-rate run showed SENSEX W PDH at 0.0% / 0.0% / 0.1% across
5/10/20pt bands with 85.5% availability. That cannot be price ignoring the
level — that is the level being wrong. This script tells us how it is wrong.

For each W PDH and W PDL zone with valid_from in the last 8 weeks (NIFTY +
SENSEX), it:

  1. Identifies "previous week" as the Mon-Fri containing zone.valid_from minus 7 days
  2. Computes the TRUE previous-week-high (max bar.high in IST session) and
     previous-week-low (min bar.low) from hist_spot_bars_5m
  3. Compares the stored zone_high / zone_low / zone_mid against TRUE
  4. Prints per-zone diff and aggregate stats

If the diff is consistent (e.g., always ~+0.25% off), it's a calculation bug.
If inconsistent, the producer is sourcing from somewhere else (wrong week,
wrong table, futures vs cash, derivative vs underlying, etc.).

Run on Local Windows from C:\\GammaEnginePython:
    python adr003_phase1_w_pdh_pdl_definition.py
"""

import os
import statistics
from datetime import datetime, date, timedelta, time as dtime
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client


load_dotenv()
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]

PAGE_SIZE = 1000
ERA_BOUNDARY = date(2026, 4, 7)
SYMBOLS = ["NIFTY", "SENSEX"]
LOOKBACK_WEEKS = 8
SESSION_START = dtime(9, 15)
SESSION_END = dtime(15, 30)
PATTERNS = ["PDH", "PDL"]


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


def canonicalize_ts_to_ist(bar_ts, trade_date):
    if trade_date < ERA_BOUNDARY:
        return bar_ts.replace(tzinfo=None)
    return (bar_ts + timedelta(hours=5, minutes=30)).replace(tzinfo=None)


def fetch_paginated_bars(client, symbol, start_d, end_d):
    rows = []
    offset = 0
    while True:
        batch = client.table("hist_spot_bars_5m").select("*") \
            .eq("symbol", symbol) \
            .gte("trade_date", start_d.isoformat()) \
            .lte("trade_date", end_d.isoformat()) \
            .order("bar_ts").range(offset, offset + PAGE_SIZE - 1) \
            .execute().data
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def fetch_zones(client, symbol, since_d):
    rows = []
    offset = 0
    while True:
        batch = client.table("ict_htf_zones").select("*") \
            .eq("symbol", symbol) \
            .eq("timeframe", "W") \
            .in_("pattern_type", PATTERNS) \
            .gte("valid_from", since_d.isoformat()) \
            .order("valid_from").range(offset, offset + PAGE_SIZE - 1) \
            .execute().data
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def previous_week_range(anchor_date):
    """Return (Mon, Fri) of the week BEFORE the week containing anchor_date."""
    weekday = anchor_date.weekday()  # Mon=0 ... Sun=6
    this_mon = anchor_date - timedelta(days=weekday)
    prev_mon = this_mon - timedelta(days=7)
    prev_fri = prev_mon + timedelta(days=4)
    return prev_mon, prev_fri


def session_bars_in_range(bars, start_d, end_d):
    """Filter pre-canonicalized bars to [start_d, end_d] IST sessions."""
    out = []
    for b in bars:
        ist = b["bar_ts_ist"]
        if start_d <= ist.date() <= end_d and SESSION_START <= ist.time() <= SESSION_END:
            out.append(b)
    return out


def main():
    print("=== ADR-003 Phase 1 — W PDH/PDL Definition Probe ===")
    today = date.today()
    since = today - timedelta(weeks=LOOKBACK_WEEKS + 2)  # extra slack for prev-week lookups
    print(f"Run date: {today.isoformat()} | Zones since: {since}")

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    for symbol in SYMBOLS:
        print(f"\n========== {symbol} ==========")

        zones = fetch_zones(client, symbol, since)
        print(f"  W PDH/PDL zones since {since}: {len(zones)}")
        if not zones:
            continue

        # Pull bars covering the earliest needed prev-week through today
        earliest_anchor = min(parse_date(z["valid_from"]) for z in zones)
        bar_start = earliest_anchor - timedelta(days=14)
        print(f"  fetching bars {bar_start} -> {today} ...")
        raw = fetch_paginated_bars(client, symbol, bar_start, today)
        bars = []
        for b in raw:
            td = parse_date(b["trade_date"])
            ts = parse_ts(b["bar_ts"])
            b["bar_ts_ist"] = canonicalize_ts_to_ist(ts, td)
            b["high"] = float(b["high"])
            b["low"] = float(b["low"])
            bars.append(b)
        print(f"  bars (canonicalized): {len(bars)}")

        # Per-zone analysis
        diffs_high = []
        diffs_low = []
        rows_out = []

        for z in zones:
            vf = parse_date(z["valid_from"])
            sbd = parse_date(z.get("source_bar_date"))
            pt = z.get("pattern_type")
            zh = float(z["zone_high"])
            zl = float(z["zone_low"])
            zm = float(z["zone_mid"]) if z.get("zone_mid") is not None else (zh + zl) / 2
            vf_weekday = vf.strftime("%a")  # Mon, Tue, ...

            prev_mon, prev_fri = previous_week_range(vf)
            wk_bars = session_bars_in_range(bars, prev_mon, prev_fri)
            if not wk_bars:
                rows_out.append({
                    "zone_id": z.get("id"),
                    "pt": pt,
                    "vf": vf,
                    "vf_dow": vf_weekday,
                    "sbd": sbd,
                    "prev_wk": f"{prev_mon}→{prev_fri}",
                    "zh": zh, "zl": zl, "zm": zm,
                    "true_pwh": None, "true_pwl": None,
                    "diff_h": None, "diff_l": None,
                    "note": "no_bars_in_prev_week",
                })
                continue

            true_pwh = max(b["high"] for b in wk_bars)
            true_pwl = min(b["low"] for b in wk_bars)

            # Pick the "stored level" relevant to this pattern
            if pt == "PDH":
                stored_level = zh  # PDH stored as zone_high typically
                true_level = true_pwh
                diff = stored_level - true_level
                diffs_high.append(diff)
            else:  # PDL
                stored_level = zl
                true_level = true_pwl
                diff = stored_level - true_level
                diffs_low.append(diff)

            rows_out.append({
                "zone_id": z.get("id"),
                "pt": pt,
                "vf": vf,
                "vf_dow": vf_weekday,
                "sbd": sbd,
                "prev_wk": f"{prev_mon}→{prev_fri}",
                "zh": zh, "zl": zl, "zm": zm,
                "true_pwh": true_pwh, "true_pwl": true_pwl,
                "diff_h": zh - true_pwh,
                "diff_l": zl - true_pwl,
                "note": "",
            })

        # Print per-zone
        print(f"\n  Per-zone comparison (stored vs computed previous-week H/L):")
        print(f"  {'pt':<3} {'vf':<11} {'dow':<4} {'sbd':<11} {'prev_week':<24} "
              f"{'zh':>10} {'zl':>10} {'zm':>10} {'true_pwh':>10} {'true_pwl':>10} "
              f"{'diff_h':>9} {'diff_l':>9}  {'note'}")
        for r in rows_out:
            zh = f"{r['zh']:.2f}"
            zl = f"{r['zl']:.2f}"
            zm = f"{r['zm']:.2f}"
            tph = f"{r['true_pwh']:.2f}" if r["true_pwh"] is not None else "—"
            tpl = f"{r['true_pwl']:.2f}" if r["true_pwl"] is not None else "—"
            dh = f"{r['diff_h']:+.2f}" if r["diff_h"] is not None else "—"
            dl = f"{r['diff_l']:+.2f}" if r["diff_l"] is not None else "—"
            sbd = r["sbd"].isoformat() if r["sbd"] else "—"
            print(f"  {r['pt']:<3} {r['vf'].isoformat():<11} {r['vf_dow']:<4} "
                  f"{sbd:<11} {r['prev_wk']:<24} "
                  f"{zh:>10} {zl:>10} {zm:>10} {tph:>10} {tpl:>10} "
                  f"{dh:>9} {dl:>9}  {r['note']}")

        # Aggregate
        print(f"\n  --- {symbol} aggregate ---")
        if diffs_high:
            print(f"  W PDH (N={len(diffs_high)}): "
                  f"mean diff={statistics.mean(diffs_high):+.2f}  "
                  f"median={statistics.median(diffs_high):+.2f}  "
                  f"stdev={statistics.stdev(diffs_high) if len(diffs_high) > 1 else 0:.2f}  "
                  f"|diff|<=5pt: {sum(1 for d in diffs_high if abs(d) <= 5)}/{len(diffs_high)}")
        if diffs_low:
            print(f"  W PDL (N={len(diffs_low)}): "
                  f"mean diff={statistics.mean(diffs_low):+.2f}  "
                  f"median={statistics.median(diffs_low):+.2f}  "
                  f"stdev={statistics.stdev(diffs_low) if len(diffs_low) > 1 else 0:.2f}  "
                  f"|diff|<=5pt: {sum(1 for d in diffs_low if abs(d) <= 5)}/{len(diffs_low)}")

    print("\n=== reading the diff column ===")
    print("  diff_h = stored zone_high - true previous-week high")
    print("  diff_l = stored zone_low  - true previous-week low")
    print("  small consistent diff (e.g. ~0)              -> definition matches, respect rate is real misalignment")
    print("  large consistent diff (e.g. always +200pts)  -> calculation bug, fix the producer offset")
    print("  inconsistent diff (varies wildly)            -> wrong source (not last week, or different feed)")
    print("  diff = 0 but respect = 0% in Phase 1         -> levels are right but proximity logic is wrong (escalate)")


if __name__ == "__main__":
    main()
