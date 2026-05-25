"""
adr003_phase1_zone_respect_rate.py

ADR-003 PHASE 1 — ICT Zone Respect-Rate Diagnostic

Question:
    For the last 10 trading days, what fraction of intraday pivots in
    hist_spot_bars_5m occurred within X points of an active ict_htf_zones
    boundary? Per symbol, per zone-type (W/D/H x OB/FVG/PDH/PDL).

Approach:
    1. For each of last 10 trading days, query ict_htf_zones for ACTIVE zones
       at session open (status='ACTIVE' AND valid_from <= trade_date <= valid_to).
    2. Identify intraday pivots in hist_spot_bars_5m: a 5m bar where
         - (high > prev high) AND (high > next high) -> local high pivot
         - (low < prev low)  AND (low < next low)   -> local low pivot
       Filter to in-session 09:15-15:30 IST.
    3. For each pivot, compute distance to nearest active zone boundary.
       Define "respect" = pivot within X pts (X = 0.10% of spot at pivot).
    4. Aggregate:
         a. % of pivots respecting any zone
         b. per-zone-type respect rate
         c. per-symbol respect rate
         d. day-by-day variance

Watch-outs:
    - TD-029: hist_spot_bars_5m bar_ts is IST labelled +00:00 for older rows.
      Per Rule 16: use replace(tzinfo=None) to treat as naive IST directly.
    - TD-030/040 zombie-zone risk: zones marked ACTIVE retrospectively when
      structurally broken. Mitigation: for each pivot, also compute whether
      any zone the pivot 'respects' should already have been BREACHED before
      the pivot bar (i.e. spot had clearly traded through the boundary on a
      prior intraday bar). If so, exclude from 'respect' count (zombie).
    - Rule 15: Supabase pagination max page_size=1000.
    - Rule 17: do NOT query market_spot_session_markers.

Decision rule:
    >=40% aggregate respect: zone layer functional, Phase 2 redesign not warranted.
    25-40%: MARGINAL, dig into which zone-type is weak.
    <25%: operator concern borne out, Phase 2 work justified.

Output:
    Stdout report. No DB writes.

Author: Session 15 batch.
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, time as dt_time

from dotenv import load_dotenv
from supabase import create_client


PAGE_SIZE = 1000  # Rule 15
LOOKBACK_TRADING_DAYS = 10
RESPECT_BAND_PCT = 0.10  # 0.10% of spot defines "respect" zone
SYMBOLS = ["NIFTY", "SENSEX"]


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def fetch_recent_trading_dates(sb, symbol: str, n: int) -> list[str]:
    """Return last n distinct trade_dates seen in hist_spot_bars_5m for a symbol."""
    # We'll select bar_ts and reduce to distinct dates client-side because
    # Supabase doesn't expose DISTINCT cleanly.
    seen: set[str] = set()
    offset = 0
    # Pull in reverse-chronological order
    # First find max bar_ts to bound the query
    r = (sb.table("hist_spot_bars_5m")
           .select("bar_ts")
           .eq("symbol", symbol)
           .order("bar_ts", desc=True)
           .limit(1)
           .execute())
    if not r.data:
        return []
    last_ts_raw = r.data[0]["bar_ts"]
    last_dt = datetime.fromisoformat(last_ts_raw.replace("Z", "+00:00")).replace(tzinfo=None)
    # Walk back; stop when we have n distinct dates or 30 calendar days exhausted.
    cutoff = last_dt - timedelta(days=30)
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
            ts_str = row["bar_ts"]
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).replace(tzinfo=None)
            seen.add(dt.date().isoformat())
            if len(seen) >= n:
                break
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return sorted(seen, reverse=True)[:n]


def fetch_5m_bars_for_date(sb, symbol: str, trade_date: str) -> list[dict]:
    """Pull all 5m bars for one symbol-day, in-session 09:15-15:30 IST.
    Rule 16: bar_ts is IST labelled +00:00 — use replace(tzinfo=None)."""
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
    # Apply Rule 16 + filter to in-session
    out = []
    for r in rows:
        dt = datetime.fromisoformat(r["bar_ts"].replace("Z", "+00:00")).replace(tzinfo=None)
        t = dt.time()
        if dt_time(9, 15) <= t <= dt_time(15, 30):
            r["_dt"] = dt
            out.append(r)
    return out


def fetch_active_zones_for_date(sb, symbol: str, trade_date: str) -> list[dict]:
    """Active zones at session open: status='ACTIVE' AND valid_from <= trade_date <= valid_to."""
    rows: list[dict] = []
    offset = 0
    while True:
        r = (sb.table("ict_htf_zones")
             .select("*")
             .eq("symbol", symbol)
             .eq("status", "ACTIVE")
             .lte("valid_from", trade_date)
             .gte("valid_to", trade_date)
             .range(offset, offset + PAGE_SIZE - 1)
             .execute())
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return rows


def find_pivots(bars: list[dict]) -> list[dict]:
    """Identify local 5m pivots. Returns list of {dt, kind, price, idx}."""
    pivots = []
    for i in range(1, len(bars) - 1):
        prev_b, b, next_b = bars[i - 1], bars[i], bars[i + 1]
        try:
            if b["high"] > prev_b["high"] and b["high"] > next_b["high"]:
                pivots.append({
                    "dt": b["_dt"], "kind": "HIGH",
                    "price": float(b["high"]), "idx": i,
                })
            if b["low"] < prev_b["low"] and b["low"] < next_b["low"]:
                pivots.append({
                    "dt": b["_dt"], "kind": "LOW",
                    "price": float(b["low"]), "idx": i,
                })
        except (TypeError, KeyError):
            continue
    return pivots


def zone_label(z: dict) -> str:
    """Return e.g. 'W_BULL_OB' or 'D_PDH'."""
    tf = (z.get("timeframe") or "").upper()
    pt = (z.get("pattern_type") or "").upper()
    return f"{tf}_{pt}" if tf and pt else (pt or tf or "UNKNOWN")


def is_zombie(zone: dict, bars_before_pivot: list[dict]) -> bool:
    """Was this zone structurally broken earlier in the session before the pivot?
    BULL zones (BULL_OB, BULL_FVG) are zombie if any prior bar's low < zone_low.
    BEAR zones (BEAR_OB, BEAR_FVG) are zombie if any prior bar's high > zone_high.
    PDH zone: zombie if any prior bar high > zone_high (already swept).
    PDL zone: zombie if any prior bar low < zone_low (already swept).
    """
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


def evaluate_pivot(pivot: dict, zones: list[dict], bars: list[dict],
                   band_pct: float) -> tuple[bool, list[str]]:
    """Returns (respected_any, list_of_zone_labels_respected_excluding_zombies)."""
    price = pivot["price"]
    band = price * band_pct / 100.0
    respected_labels = []
    bars_before = [b for b in bars if b["_dt"] < pivot["dt"]]
    for z in zones:
        try:
            zlow = float(z.get("zone_low") or 0)
            zhigh = float(z.get("zone_high") or 0)
        except (TypeError, ValueError):
            continue
        if zlow == 0 and zhigh == 0:
            continue
        # Distance to nearest boundary
        if zlow <= price <= zhigh:
            d = 0.0
        else:
            d = min(abs(price - zlow), abs(price - zhigh))
        if d <= band:
            if is_zombie(z, bars_before):
                continue
            respected_labels.append(zone_label(z))
    return (len(respected_labels) > 0, respected_labels)


def main():
    sb = get_client()

    print("=" * 76)
    print("ADR-003 PHASE 1 — ICT ZONE RESPECT-RATE DIAGNOSTIC")
    print("=" * 76)
    print(f"Lookback: {LOOKBACK_TRADING_DAYS} trading days per symbol")
    print(f"Respect band: {RESPECT_BAND_PCT}% of pivot price")
    print()

    # Aggregations
    overall = {"pivots": 0, "respected": 0}
    per_sym = defaultdict(lambda: {"pivots": 0, "respected": 0})
    per_zone_type_resp = defaultdict(int)
    per_zone_type_chances = defaultdict(int)  # how many pivots had this zone-type as ACTIVE
    per_day = []  # list of (date, symbol, pivots, respected)

    for symbol in SYMBOLS:
        print(f"--- {symbol} ---")
        dates = fetch_recent_trading_dates(sb, symbol, LOOKBACK_TRADING_DAYS)
        if not dates:
            print(f"[WARN] no trading dates found for {symbol}")
            continue
        print(f"Dates: {dates}")
        for d in dates:
            bars = fetch_5m_bars_for_date(sb, symbol, d)
            if len(bars) < 5:
                print(f"  {d}: only {len(bars)} bars, skipping")
                continue
            zones = fetch_active_zones_for_date(sb, symbol, d)
            zone_label_set = {zone_label(z) for z in zones}
            pivots = find_pivots(bars)
            day_resp = 0
            for p in pivots:
                respected, labels = evaluate_pivot(p, zones, bars, RESPECT_BAND_PCT)
                overall["pivots"] += 1
                per_sym[symbol]["pivots"] += 1
                if respected:
                    overall["respected"] += 1
                    per_sym[symbol]["respected"] += 1
                    day_resp += 1
                    for lbl in set(labels):
                        per_zone_type_resp[lbl] += 1
                # Each zone-type-active-on-this-day gets one chance per pivot
                for lbl in zone_label_set:
                    per_zone_type_chances[lbl] += 1
            n_pivots = len(pivots)
            rate = day_resp / n_pivots * 100 if n_pivots else 0
            print(f"  {d}: bars={len(bars)} zones={len(zones)} pivots={n_pivots} "
                  f"respected={day_resp} ({rate:.1f}%)")
            per_day.append((d, symbol, n_pivots, day_resp))
        print()

    # Final tables
    print("=" * 76)
    print("AGGREGATE RESULTS")
    print("=" * 76)

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
        if s["pivots"]:
            r = s["respected"] / s["pivots"] * 100
        else:
            r = 0
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
    print("Per-day variance:")
    print(f"{'Date':<12} {'Symbol':<8} {'Pivots':>7} {'Respected':>10} {'Rate':>8}")
    for d, sym, n, r in per_day:
        rate = r / n * 100 if n else 0
        print(f"{d:<12} {sym:<8} {n:>7} {r:>10} {rate:>7.1f}%")

    print()
    print("=" * 76)
    print("DECISION RULE:")
    print("  >=40% aggregate respect: zone layer functional, Phase 2 not warranted")
    print("  25-40%: MARGINAL, identify weak zone-type")
    print("  <25%: Phase 2 redesign justified")
    print(f"  -> Aggregate rate: {agg_rate:.1f}%")
    if agg_rate >= 40:
        print("  -> VERDICT: zone layer functional (per the 40% bar)")
    elif agg_rate >= 25:
        print("  -> VERDICT: MARGINAL — investigate per-zone-type breakdown")
    else:
        print("  -> VERDICT: Phase 2 redesign justified")
    print("=" * 76)


if __name__ == "__main__":
    main()
