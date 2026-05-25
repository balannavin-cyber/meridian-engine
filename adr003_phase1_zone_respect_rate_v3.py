"""
adr003_phase1_zone_respect_rate_v3.py  --  Session 16 item 5

ADR-003 PHASE 1 v3  --  ICT Zone Respect-Rate Diagnostic

v3 deltas vs v2
---------------
1) Table name fix: queries `hist_ict_htf_zones` (the historical-batch table
   Session 15 backfilled to 40,384 rows), NOT `ict_htf_zones` (the live
   runtime table that may be near-empty). v1/v2 likely hit the wrong table.

2) Drop valid_to filter, take most-recent ACTIVE zone per (timeframe,
   pattern_type) at trade_date. Schema confirms valid_from / valid_to are
   single dates, so historical zones often have valid_from = valid_to =
   source_bar_date — the v2 client-side filter
   (valid_from <= target <= valid_to) excludes them on any later date.
   v3 selects, for each (timeframe, pattern_type), the row with the
   latest valid_from <= trade_date AND status='ACTIVE'.

3) Era-aware Rule 20 timestamp handling. v2 used naive
   replace(tzinfo=None) for all bar_ts; post 2026-04-07 bars need
   astimezone(IST) first or in-session filtering misclassifies them.

4) Use `trade_date` column directly in queries where available
   (hist_spot_bars_5m exposes it, removes any TZ ambiguity).

5) EXPECTED_BARS_PER_SESSION = 81 (empirical from Items 1/3/4: NIFTY
   averages 81.5 bars/day, SENSEX same). Coverage warning threshold
   relaxed from 80% to 85% so 75-bar legacy days still pass.

6) Per-pivot zone-distance histogram diagnostic added: when respect-rate
   is low, this surfaces whether the failure is "no zones near pivots"
   vs "zones near pivots but band too tight."

Decision rule (unchanged from v2)
---------------------------------
  >= 40% aggregate respect: FUNCTIONAL
  25 - 40%                : MARGINAL
  < 25%                   : PHASE 2 REDESIGN JUSTIFIED

Author: Session 16, item 5.
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, time as dt_time, date as date_t, timezone

from dotenv import load_dotenv
from supabase import create_client


# --- Constants ---------------------------------------------------------------
PAGE_SIZE = 1000
LOOKBACK_TRADING_DAYS = 10
RESPECT_BAND_PCT = 0.10
SYMBOLS = ["NIFTY", "SENSEX"]
EXPECTED_BARS_PER_SESSION = 81  # empirical, not 75
COVERAGE_WARN_THRESHOLD = 0.85

# --- Rule 20 era-aware helpers -----------------------------------------------
IST = timezone(timedelta(hours=5, minutes=30))
ERA_BOUNDARY = "2026-04-07"


def to_ist_naive(ts_aware, trade_date_str):
    if trade_date_str < ERA_BOUNDARY:
        return ts_aware.replace(tzinfo=None)
    return ts_aware.astimezone(IST).replace(tzinfo=None)


def parse_ts(s):
    if s is None:
        return None
    if isinstance(s, datetime):
        return s
    if isinstance(s, str):
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    return None


def parse_iso_to_date(value):
    """Parse string/datetime/date to a date object. Returns None on failure."""
    if value is None:
        return None
    if isinstance(value, date_t) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_KEY")
    )
    if not url or not key:
        sys.exit("Missing SUPABASE_URL or SUPABASE_*_KEY in .env")
    return create_client(url, key)


def fetch_all(qb, page=PAGE_SIZE, hard_cap=200_000):
    rows, start = [], 0
    while True:
        chunk = qb.range(start, start + page - 1).execute().data or []
        rows.extend(chunk)
        if len(chunk) < page:
            return rows
        start += page
        if start > hard_cap:
            return rows


# --- Trading-date discovery (uses trade_date column, era-clean) -------------
def fetch_recent_trading_dates(sb, symbol, n):
    """Last n distinct trade_dates seen in hist_spot_bars_5m for symbol."""
    rows = fetch_all(
        sb.table("hist_spot_bars_5m")
          .select("trade_date")
          .eq("symbol", symbol)
          .order("trade_date", desc=True)
          .limit(n * 100)  # safety overshoot for weekends/holidays
    )
    seen, out = set(), []
    for r in rows:
        td = r.get("trade_date")
        if td and td not in seen:
            seen.add(td)
            out.append(td)
            if len(out) == n:
                break
    return out


# --- Bar fetch (era-aware Rule 20) ------------------------------------------
def fetch_5m_bars_for_date(sb, symbol, trade_date):
    """All in-session 5m bars for symbol on trade_date. Era-aware."""
    rows = fetch_all(
        sb.table("hist_spot_bars_5m")
          .select("bar_ts, open, high, low, close, symbol, trade_date")
          .eq("symbol", symbol)
          .eq("trade_date", trade_date)
          .order("bar_ts")
    )
    out = []
    for row in rows:
        ts = parse_ts(row["bar_ts"])
        if ts is None:
            continue
        ist = to_ist_naive(ts, row["trade_date"])
        t = ist.time()
        if dt_time(9, 15) <= t <= dt_time(15, 30):
            row["_dt"] = ist
            out.append(row)
    return out


# --- Zone fetch + most-recent ACTIVE selection ------------------------------
def fetch_all_active_zones(sb, symbol):
    """All status='ACTIVE' zones from hist_ict_htf_zones (Session 15 backfilled)."""
    return fetch_all(
        sb.table("hist_ict_htf_zones")
          .select("*")
          .eq("symbol", symbol)
          .eq("status", "ACTIVE")
          .order("valid_from")
    )


def select_active_at(zones, trade_date_str):
    """v3 selection rule: drop valid_to filter; take most recent ACTIVE zone
    per (timeframe, pattern_type) where valid_from <= trade_date.

    This treats "ACTIVE" as state, not a date-window. The zone with the latest
    valid_from <= trade_date is the one in effect at evaluation time.
    """
    target = parse_iso_to_date(trade_date_str)
    if target is None:
        return []
    by_key = {}  # (tf, pt) -> (vf_date, zone_dict)
    for z in zones:
        vf = parse_iso_to_date(z.get("valid_from"))
        if vf is None or vf > target:
            continue
        tf = (z.get("timeframe") or "").upper()
        pt = (z.get("pattern_type") or "").upper()
        if not tf or not pt:
            continue
        key = (tf, pt)
        if key not in by_key or vf > by_key[key][0]:
            by_key[key] = (vf, z)
    return [v[1] for v in by_key.values()]


# --- Pivot detection ---------------------------------------------------------
def find_pivots(bars):
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


def zone_label(z):
    tf = (z.get("timeframe") or "").upper()
    pt = (z.get("pattern_type") or "").upper()
    return f"{tf}_{pt}" if tf and pt else (pt or tf or "UNKNOWN")


# --- Zombie filter (zone broken pre-pivot) ----------------------------------
def is_zombie(zone, bars_before_pivot):
    if not bars_before_pivot:
        return False
    pt = (zone.get("pattern_type") or "").upper()
    try:
        zlow = float(zone.get("zone_low") or 0)
        zhigh = float(zone.get("zone_high") or 0)
    except (TypeError, ValueError):
        return False
    if pt in ("BULL_OB", "BULL_FVG", "PDL"):
        return any(float(b["low"]) < zlow for b in bars_before_pivot
                   if b.get("low") is not None)
    if pt in ("BEAR_OB", "BEAR_FVG", "PDH"):
        return any(float(b["high"]) > zhigh for b in bars_before_pivot
                   if b.get("high") is not None)
    return False


# --- Pivot evaluation + distance diagnostic ---------------------------------
def evaluate_pivot(pivot, zones, bars, band_pct):
    """Returns (respected_bool, [respected_zone_labels], min_distance_pct)."""
    price = pivot["price"]
    band = price * band_pct / 100.0
    bars_before = [b for b in bars if b["_dt"] < pivot["dt"]]
    respected = []
    min_d_abs = None
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
        if min_d_abs is None or d < min_d_abs:
            min_d_abs = d
        if d <= band and not is_zombie(z, bars_before):
            respected.append(zone_label(z))
    min_d_pct = (min_d_abs / price * 100.0) if min_d_abs is not None else None
    return (len(respected) > 0, respected, min_d_pct)


def histogram_buckets(distances_pct):
    """Bucket distances (in %) into bands."""
    buckets = [
        ("0.00%-0.05%", 0.0, 0.05),
        ("0.05%-0.10%", 0.05, 0.10),
        ("0.10%-0.20%", 0.10, 0.20),
        ("0.20%-0.50%", 0.20, 0.50),
        ("0.50%-1.00%", 0.50, 1.00),
        (">=1.00%",     1.00, float("inf")),
    ]
    labels = [b[0] for b in buckets]
    counts = [0] * len(buckets)
    none_n = 0
    for d in distances_pct:
        if d is None:
            none_n += 1
            continue
        for i, (_, lo, hi) in enumerate(buckets):
            if lo <= d < hi:
                counts[i] += 1
                break
    return labels, counts, none_n


# --- Main --------------------------------------------------------------------
def main():
    sb = get_client()

    print("=" * 88)
    print("ADR-003 PHASE 1 v3  --  ICT ZONE RESPECT-RATE DIAGNOSTIC")
    print(f"Run at: {datetime.now(IST).isoformat(timespec='seconds')}")
    print("=" * 88)
    print(f"Lookback         : {LOOKBACK_TRADING_DAYS} trading days per symbol")
    print(f"Respect band     : {RESPECT_BAND_PCT}% of pivot price")
    print(f"Zone source      : hist_ict_htf_zones (Session 15 backfilled, 40,384 rows total)")
    print(f"Zone selection   : most-recent ACTIVE per (timeframe, pattern_type), no valid_to filter")
    print(f"TZ handling      : Rule 20 era-aware (boundary {ERA_BOUNDARY})")
    print(f"Coverage thresh  : {EXPECTED_BARS_PER_SESSION} bars/session, warn below "
          f"{COVERAGE_WARN_THRESHOLD*100:.0f}%")
    print()

    # === Pre-flight: all ACTIVE zones per symbol ===
    all_zones_by_sym = {}
    for sym in SYMBOLS:
        zs = fetch_all_active_zones(sb, sym)
        all_zones_by_sym[sym] = zs
        print(f"[{sym}] total ACTIVE zones in hist_ict_htf_zones: {len(zs)}")
        by_label = defaultdict(int)
        for z in zs:
            by_label[zone_label(z)] += 1
        for lbl, n in sorted(by_label.items()):
            print(f"    {lbl:<14} {n}")
    print()

    # === Per-day evaluation ===
    overall = {"pivots": 0, "respected": 0}
    per_sym = defaultdict(lambda: {"pivots": 0, "respected": 0})
    per_zone_type_resp = defaultdict(int)
    per_zone_type_chances = defaultdict(int)
    bar_coverage = []
    all_distances = []
    respected_distances = []

    for symbol in SYMBOLS:
        print(f"--- {symbol} ---")
        dates = fetch_recent_trading_dates(sb, symbol, LOOKBACK_TRADING_DAYS)
        if not dates:
            print(f"[WARN] no trading dates for {symbol}")
            continue
        print(f"Dates: {dates}")
        for d in dates:
            bars = fetch_5m_bars_for_date(sb, symbol, d)
            zones_today = select_active_at(all_zones_by_sym[symbol], d)
            zone_label_set = {zone_label(z) for z in zones_today}
            pivots = find_pivots(bars)

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
                respected, labels, min_d_pct = evaluate_pivot(
                    p, zones_today, bars, RESPECT_BAND_PCT
                )
                overall["pivots"] += 1
                per_sym[symbol]["pivots"] += 1
                all_distances.append(min_d_pct)
                if respected:
                    overall["respected"] += 1
                    per_sym[symbol]["respected"] += 1
                    day_resp += 1
                    respected_distances.append(min_d_pct)
                    for lbl in set(labels):
                        per_zone_type_resp[lbl] += 1
                for lbl in zone_label_set:
                    per_zone_type_chances[lbl] += 1
            n_pivots = len(pivots)
            rate = day_resp / n_pivots * 100 if n_pivots else 0
            print(f"    -> respected={day_resp}/{n_pivots} ({rate:.1f}%)")
        print()

    # === Aggregate ===
    print("=" * 88)
    print("AGGREGATE RESULTS")
    print("=" * 88)
    agg_rate = (overall["respected"] / overall["pivots"] * 100) if overall["pivots"] else 0
    print(f"Overall: pivots={overall['pivots']}, respected={overall['respected']}, "
          f"rate={agg_rate:.1f}%")
    print()
    print("Per symbol:")
    for sym in SYMBOLS:
        s = per_sym[sym]
        r = (s["respected"] / s["pivots"] * 100) if s["pivots"] else 0
        print(f"  {sym}: pivots={s['pivots']}, respected={s['respected']}, rate={r:.1f}%")
    print()
    print("Per zone-type respect rate:")
    print(f"{'Zone-type':<20} {'Respected':>10} {'Chances':>10} {'Rate':>8}")
    for lbl in sorted(per_zone_type_chances.keys()):
        resp = per_zone_type_resp.get(lbl, 0)
        chances = per_zone_type_chances[lbl]
        rate = (resp / chances * 100) if chances else 0
        print(f"{lbl:<20} {resp:>10} {chances:>10} {rate:>7.1f}%")

    # === Distance histogram ===
    print()
    print("Pivot-to-nearest-zone distance histogram (all pivots):")
    labels, counts, none_n = histogram_buckets(all_distances)
    total = sum(counts) + none_n
    print(f"{'Distance band':<16} {'Count':>8} {'Share':>8}")
    for lbl, c in zip(labels, counts):
        share = (c / total * 100) if total else 0
        print(f"{lbl:<16} {c:>8} {share:>7.1f}%")
    if none_n:
        print(f"{'(no zones)':<16} {none_n:>8} {none_n/total*100:>7.1f}%")
    if respected_distances:
        rd = [d for d in respected_distances if d is not None]
        if rd:
            print(f"\nRespected pivots: median distance "
                  f"{sorted(rd)[len(rd)//2]:.4f}%, "
                  f"max {max(rd):.4f}% (band cap {RESPECT_BAND_PCT}%)")
    print()

    # === Bar coverage ===
    print("Bar-coverage diagnostic:")
    print(f"{'Date':<12} {'Symbol':<8} {'Bars':>6} {'Expected':>9} {'Coverage':>9}")
    total_bars = 0
    total_expected = 0
    for d, sym, n in bar_coverage:
        cov = n / EXPECTED_BARS_PER_SESSION * 100
        marker = " <- LOW" if cov < COVERAGE_WARN_THRESHOLD * 100 else ""
        print(f"{d:<12} {sym:<8} {n:>6} {EXPECTED_BARS_PER_SESSION:>9} {cov:>8.1f}%{marker}")
        total_bars += n
        total_expected += EXPECTED_BARS_PER_SESSION
    if total_expected:
        overall_cov = total_bars / total_expected * 100
        print(f"\nOverall bar coverage: {total_bars}/{total_expected} = {overall_cov:.1f}%")
    print()

    # === Verdict ===
    print("=" * 88)
    print("DECISION RULE:")
    print("  >= 40% aggregate respect: FUNCTIONAL")
    print("  25 - 40%                : MARGINAL")
    print("  < 25%                   : PHASE 2 REDESIGN JUSTIFIED")
    print(f"  -> Aggregate rate: {agg_rate:.1f}%")
    if agg_rate >= 40:
        verdict = "FUNCTIONAL"
    elif agg_rate >= 25:
        verdict = "MARGINAL"
    else:
        verdict = "PHASE 2 REDESIGN JUSTIFIED"
    print(f"  -> VERDICT: {verdict}")
    print()
    print("CAVEATS:")
    print("- Distance histogram tells you WHY respect-rate is what it is.")
    print("  Many pivots in 0.10%-0.20% band -> band may be too tight.")
    print("  Many pivots in (no zones) bucket -> zone coverage gap.")
    print("- v3 takes most-recent ACTIVE per (TF, pattern). If multiple zones")
    print("  per timeframe layer existed in original ICT spec, this collapses")
    print("  them. Trade-off accepted to escape the v1/v2 valid_to bug.")
    print("=" * 88)


if __name__ == "__main__":
    main()
