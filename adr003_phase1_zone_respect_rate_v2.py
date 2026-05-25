"""
adr003_phase1_zone_respect_rate_v2.py

ADR-003 PHASE 1 — ICT Zone Respect-Rate Diagnostic (v2)

v2 fixes vs v1:
    1. Zone filter: removed SQL valid_from/valid_to date-string filter (was
       silently excluding same-day zones whose valid_from has a time component
       greater than 00:00:00). Now pulls ALL ACTIVE zones for symbol and
       filters client-side after parsing to date.
    2. Per-day diagnostic: dumps each day's zone list (TF, pattern_type,
       zone_low, zone_high, valid_from, valid_to) so we can verify the script
       sees what merdian_reference.json claims is there.
    3. Bar coverage diagnostic: prints expected (75) vs actual bar count per
       session so we surface the underlying ingestion gap separately.
    4. Aggregate "ACTIVE zones for symbol regardless of date" check at start
       so we know the total candidate pool.

Otherwise identical to v1: Rule 15 pagination, Rule 16 timezone handling on
hist_spot_bars_5m, RESPECT_BAND_PCT = 0.10% of pivot price, last 10 trading
days, both symbols.

Author: Session 15 batch.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, time as dt_time, date as date_t

from dotenv import load_dotenv
from supabase import create_client


PAGE_SIZE = 1000
LOOKBACK_TRADING_DAYS = 10
RESPECT_BAND_PCT = 0.10
SYMBOLS = ["NIFTY", "SENSEX"]
EXPECTED_BARS_PER_SESSION = 75  # 09:15 -> 15:30 in 5m


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def parse_iso_to_date(value) -> date_t | None:
    """Parse a string OR datetime OR date to a date object. Returns None on failure."""
    if value is None:
        return None
    if isinstance(value, date_t) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        # Try common formats
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return datetime.strptime(value[:10], "%Y-%m-%d").date()
            except ValueError:
                return None
    return None


def fetch_recent_trading_dates(sb, symbol: str, n: int) -> list[str]:
    """Last n distinct trade_dates seen in hist_spot_bars_5m."""
    seen: set[str] = set()
    r = (sb.table("hist_spot_bars_5m")
         .select("bar_ts")
         .eq("symbol", symbol)
         .order("bar_ts", desc=True)
         .limit(1)
         .execute())
    if not r.data:
        return []
    last_dt = datetime.fromisoformat(r.data[0]["bar_ts"].replace("Z", "+00:00")).replace(tzinfo=None)
    cutoff = last_dt - timedelta(days=30)
    offset = 0
    while offset < 30000 and len(seen) < n:
        rr = (sb.table("hist_spot_bars_5m")
              .select("bar_ts")
              .eq("symbol", symbol)
              .gte("bar_ts", cutoff.isoformat())
              .order("bar_ts", desc=True)
              .range(offset, offset + PAGE_SIZE - 1)
              .execute())
        batch = rr.data or []
        if not batch:
            break
        for row in batch:
            dt = datetime.fromisoformat(row["bar_ts"].replace("Z", "+00:00")).replace(tzinfo=None)
            seen.add(dt.date().isoformat())
            if len(seen) >= n:
                break
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return sorted(seen, reverse=True)[:n]


def fetch_5m_bars_for_date(sb, symbol: str, trade_date: str) -> list[dict]:
    """All 5m bars for symbol-day. Apply Rule 16 + in-session filter."""
    rows: list[dict] = []
    offset = 0
    day_start = f"{trade_date}T00:00:00+00:00"
    day_end = f"{trade_date}T23:59:59+00:00"
    while True:
        r = (sb.table("hist_spot_bars_5m")
             .select("bar_ts, open, high, low, close, symbol")
             .eq("symbol", symbol)
             .gte("bar_ts", day_start)
             .lte("bar_ts", day_end)
             .order("bar_ts")
             .range(offset, offset + PAGE_SIZE - 1)
             .execute())
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
            row["_dt"] = dt
            out.append(row)
    return out


def fetch_all_active_zones(sb, symbol: str) -> list[dict]:
    """Pull ALL status='ACTIVE' zones for symbol. No SQL date filter (v2 fix).
    Parse valid_from/valid_to client-side."""
    rows: list[dict] = []
    offset = 0
    while True:
        r = (sb.table("ict_htf_zones")
             .select("*")
             .eq("symbol", symbol)
             .eq("status", "ACTIVE")
             .range(offset, offset + PAGE_SIZE - 1)
             .execute())
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def zones_active_on(zones: list[dict], trade_date: str) -> list[dict]:
    """Client-side filter: zones whose valid_from <= trade_date <= valid_to."""
    target = datetime.strptime(trade_date, "%Y-%m-%d").date()
    out = []
    for z in zones:
        vf = parse_iso_to_date(z.get("valid_from"))
        vt = parse_iso_to_date(z.get("valid_to"))
        if vf is None or vt is None:
            continue
        if vf <= target <= vt:
            out.append(z)
    return out


def find_pivots(bars: list[dict]) -> list[dict]:
    pivots = []
    for i in range(1, len(bars) - 1):
        prev_b, b, next_b = bars[i - 1], bars[i], bars[i + 1]
        try:
            if b["high"] > prev_b["high"] and b["high"] > next_b["high"]:
                pivots.append({"dt": b["_dt"], "kind": "HIGH",
                               "price": float(b["high"]), "idx": i})
            if b["low"] < prev_b["low"] and b["low"] < next_b["low"]:
                pivots.append({"dt": b["_dt"], "kind": "LOW",
                               "price": float(b["low"]), "idx": i})
        except (TypeError, KeyError):
            continue
    return pivots


def zone_label(z: dict) -> str:
    tf = (z.get("timeframe") or "").upper()
    pt = (z.get("pattern_type") or "").upper()
    return f"{tf}_{pt}" if tf and pt else (pt or tf or "UNKNOWN")


def is_zombie(zone: dict, bars_before_pivot: list[dict]) -> bool:
    if not bars_before_pivot:
        return False
    pt = (zone.get("pattern_type") or "").upper()
    try:
        zlow = float(zone.get("zone_low") or 0)
        zhigh = float(zone.get("zone_high") or 0)
    except (TypeError, ValueError):
        return False
    if pt in ("BULL_OB", "BULL_FVG", "PDL"):
        return any(float(b["low"]) < zlow for b in bars_before_pivot if b.get("low") is not None)
    if pt in ("BEAR_OB", "BEAR_FVG", "PDH"):
        return any(float(b["high"]) > zhigh for b in bars_before_pivot if b.get("high") is not None)
    return False


def evaluate_pivot(pivot, zones, bars, band_pct):
    price = pivot["price"]
    band = price * band_pct / 100.0
    respected = []
    bars_before = [b for b in bars if b["_dt"] < pivot["dt"]]
    for z in zones:
        try:
            zlow = float(z.get("zone_low") or 0)
            zhigh = float(z.get("zone_high") or 0)
        except (TypeError, ValueError):
            continue
        if zlow == 0 and zhigh == 0:
            continue
        if zlow <= price <= zhigh:
            d = 0.0
        else:
            d = min(abs(price - zlow), abs(price - zhigh))
        if d <= band and not is_zombie(z, bars_before):
            respected.append(zone_label(z))
    return (len(respected) > 0, respected)


def main():
    sb = get_client()

    print("=" * 78)
    print("ADR-003 PHASE 1 v2 — ICT ZONE RESPECT-RATE DIAGNOSTIC")
    print("=" * 78)
    print(f"Lookback: {LOOKBACK_TRADING_DAYS} trading days per symbol")
    print(f"Respect band: {RESPECT_BAND_PCT}% of pivot price")
    print(f"v2 changes: client-side zone date filter, per-day diagnostics, bar-coverage check")
    print()

    # === Pre-flight: all ACTIVE zones per symbol (regardless of date) ===
    all_zones_by_sym = {}
    for sym in SYMBOLS:
        zs = fetch_all_active_zones(sb, sym)
        all_zones_by_sym[sym] = zs
        print(f"[{sym}] total ACTIVE zones in ict_htf_zones: {len(zs)}")
        # Group by zone_label for quick visibility
        by_label = defaultdict(int)
        for z in zs:
            by_label[zone_label(z)] += 1
        for lbl, n in sorted(by_label.items()):
            print(f"    {lbl}: {n}")
    print()

    overall = {"pivots": 0, "respected": 0}
    per_sym = defaultdict(lambda: {"pivots": 0, "respected": 0})
    per_zone_type_resp = defaultdict(int)
    per_zone_type_chances = defaultdict(int)
    per_day = []
    bar_coverage = []

    for symbol in SYMBOLS:
        print(f"--- {symbol} ---")
        dates = fetch_recent_trading_dates(sb, symbol, LOOKBACK_TRADING_DAYS)
        if not dates:
            print(f"[WARN] no trading dates for {symbol}")
            continue
        print(f"Dates: {dates}")
        for d in dates:
            bars = fetch_5m_bars_for_date(sb, symbol, d)
            zones_today = zones_active_on(all_zones_by_sym[symbol], d)
            zone_label_set = {zone_label(z) for z in zones_today}
            pivots = find_pivots(bars)

            # Per-day diagnostic listing
            print(f"  {d}: bars={len(bars)} (expected {EXPECTED_BARS_PER_SESSION})  "
                  f"zones={len(zones_today)} pivots={len(pivots)}")
            bar_coverage.append((d, symbol, len(bars)))
            for z in zones_today:
                vf = parse_iso_to_date(z.get("valid_from"))
                vt = parse_iso_to_date(z.get("valid_to"))
                print(f"    zone: {zone_label(z):<14} "
                      f"low={z.get('zone_low')} high={z.get('zone_high')} "
                      f"valid={vf}..{vt}")

            day_resp = 0
            for p in pivots:
                respected, labels = evaluate_pivot(p, zones_today, bars, RESPECT_BAND_PCT)
                overall["pivots"] += 1
                per_sym[symbol]["pivots"] += 1
                if respected:
                    overall["respected"] += 1
                    per_sym[symbol]["respected"] += 1
                    day_resp += 1
                    for lbl in set(labels):
                        per_zone_type_resp[lbl] += 1
                for lbl in zone_label_set:
                    per_zone_type_chances[lbl] += 1
            n_pivots = len(pivots)
            rate = day_resp / n_pivots * 100 if n_pivots else 0
            print(f"    -> respected={day_resp}/{n_pivots} ({rate:.1f}%)")
            per_day.append((d, symbol, n_pivots, day_resp))
        print()

    # === Aggregate ===
    print("=" * 78)
    print("AGGREGATE RESULTS")
    print("=" * 78)
    if overall["pivots"]:
        agg_rate = overall["respected"] / overall["pivots"] * 100
    else:
        agg_rate = 0
    print(f"Overall: pivots={overall['pivots']}, respected={overall['respected']}, "
          f"rate={agg_rate:.1f}%")

    print()
    print("Per symbol:")
    for sym in SYMBOLS:
        s = per_sym[sym]
        r = s["respected"] / s["pivots"] * 100 if s["pivots"] else 0
        print(f"  {sym}: pivots={s['pivots']}, respected={s['respected']}, rate={r:.1f}%")

    print()
    print("Per zone-type respect rate:")
    print(f"{'Zone-type':<20} {'Respected':>10} {'Chances':>10} {'Rate':>8}")
    for lbl in sorted(per_zone_type_chances.keys()):
        resp = per_zone_type_resp.get(lbl, 0)
        chances = per_zone_type_chances[lbl]
        rate = resp / chances * 100 if chances else 0
        print(f"{lbl:<20} {resp:>10} {chances:>10} {rate:>7.1f}%")

    print()
    print("Bar-coverage diagnostic (separate from ADR-003 Phase 1 verdict):")
    print(f"{'Date':<12} {'Symbol':<8} {'Bars':>6} {'Expected':>9} {'Coverage':>9}")
    total_bars = 0
    total_expected = 0
    for d, sym, n in bar_coverage:
        cov = n / EXPECTED_BARS_PER_SESSION * 100
        marker = " <- LOW" if cov < 80 else ""
        print(f"{d:<12} {sym:<8} {n:>6} {EXPECTED_BARS_PER_SESSION:>9} {cov:>8.1f}%{marker}")
        total_bars += n
        total_expected += EXPECTED_BARS_PER_SESSION
    if total_expected:
        overall_cov = total_bars / total_expected * 100
        print(f"\nOverall bar coverage: {total_bars}/{total_expected} = {overall_cov:.1f}%")

    print()
    print("=" * 78)
    print("DECISION RULE:")
    print("  >=40% aggregate respect: zone layer functional")
    print("  25-40%: MARGINAL")
    print("  <25%: Phase 2 redesign justified")
    print(f"  -> Aggregate rate: {agg_rate:.1f}%")
    if agg_rate >= 40:
        verdict = "FUNCTIONAL"
    elif agg_rate >= 25:
        verdict = "MARGINAL"
    else:
        verdict = "PHASE 2 REDESIGN JUSTIFIED"
    print(f"  -> VERDICT: {verdict}")
    print()
    print("CAVEAT: If bar-coverage diagnostic shows <80% on most days, the respect-rate")
    print("number may be artificially deflated (fewer bars -> fewer pivots -> small N).")
    print("In that case the verdict reflects current data quality, not zone-layer truth.")
    print("=" * 78)


if __name__ == "__main__":
    main()
