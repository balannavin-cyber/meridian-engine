"""
diagnostic_bear_fvg_audit.py

DIAGNOSTIC — BEAR_FVG absence in hist_pattern_signals

Question:
    Exp 50 + 50b found 1,261 BULL_FVG and 0 BEAR_FVG over 13 months
    across NIFTY + SENSEX. The Apr-2025 -> Apr-2026 weekly chart shows
    multiple sustained bearish displacement periods (Aug 2024 -> Mar
    2025 -17%, Jan -> Mar 2026 sharp drop). Genuine BEAR_FVGs in price
    cannot be zero. The data path is the problem.

Hypotheses ranked from most to least likely:
    H1 — Detector-side asymmetry: build_pattern_signals.py emits BULL only.
    H2 — Schema-side filter / non-canonical labels: BEAR rows exist with
         pattern_type values we didn't query (FVG, BEARISH_FVG, etc).
    H3 — Direction encoded elsewhere: pattern_type='FVG' with direction
         in a separate column.
    H5 — Different table: BEAR FVGs in a sibling table.
    H6 — Genuine market asymmetry: REJECTED by user's weekly chart review.

Five-step audit:
    Step 1: Distinct pattern_type values + counts in hist_pattern_signals.
            Falsifies H1 if anything bear-flavoured exists.
            Falsifies H2 if non-canonical variants exist.
    Step 2: Full schema of hist_pattern_signals. Identifies any direction/
            side/bias/is_bull column. Distributes by (pattern_type x
            direction). Falsifies H3.
    Step 3: List public tables matching pattern/signal/fvg keywords.
            Falsifies H5 by surfacing where else FVG-like data may live.
    Step 4: Daily candle structure last 30 trading days. Confirms bear
            days exist (sanity check; the chart already proved this but
            we want the numbers in the audit).
    Step 5: Manual canonical-pattern scan of hist_spot_bars_5m for
            BEAR-FVG-shaped 3-bar structures over the last 60 trading
            days, both symbols. Bar-K low > Bar-(K+2) high (3-bar bearish
            FVG). Compare count vs hist_pattern_signals BEAR_FVG count
            for same window. Closes the question definitively.

Output:
    Diagnosis tree pointing to which H is true.
    Concrete next-action recommendation.

Author: Session 15 batch.
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from dotenv import load_dotenv
from supabase import create_client


PAGE_SIZE = 1000
SYMBOLS = ["NIFTY", "SENSEX"]
STEP4_LOOKBACK_DAYS = 30
STEP5_LOOKBACK_DAYS = 60


def get_client():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
    return create_client(url, key)


def parse_dt(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


# --------------------------------------------------------------------------
# STEP 1: distinct pattern_type values + counts
# --------------------------------------------------------------------------

def step1_pattern_type_distribution(sb) -> dict:
    print("=" * 96)
    print("STEP 1 — Distinct pattern_type values in hist_pattern_signals")
    print("=" * 96)
    counts = Counter()
    offset = 0
    while True:
        r = (sb.table("hist_pattern_signals").select("pattern_type")
             .range(offset, offset + PAGE_SIZE - 1).execute())
        batch = r.data or []
        for row in batch:
            counts[row.get("pattern_type") or "NULL"] += 1
        if len(batch) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        if offset > 500_000:
            break
    print(f"Total rows scanned: {sum(counts.values()):,}")
    print(f"Distinct pattern_type values: {len(counts)}")
    print()
    print(f"{'pattern_type':<24} {'count':>10}")
    print("-" * 36)
    for pt, n in counts.most_common():
        flag = ""
        upper = (pt or "").upper()
        if "BEAR" in upper or "BEARISH" in upper or "DOWN" in upper or "SHORT" in upper:
            flag = "  <- BEAR-flavoured"
        print(f"{pt:<24} {n:>10}{flag}")
    print()
    bear_flavoured = {pt: n for pt, n in counts.items()
                      if any(t in (pt or "").upper()
                             for t in ("BEAR", "DOWN", "SHORT", "BEARISH"))}
    fvg_flavoured = {pt: n for pt, n in counts.items()
                     if "FVG" in (pt or "").upper()}
    print(f"Bear-flavoured types: {bear_flavoured}")
    print(f"FVG-flavoured types: {fvg_flavoured}")
    print()
    return {"counts": counts, "bear_flavoured": bear_flavoured,
            "fvg_flavoured": fvg_flavoured}


# --------------------------------------------------------------------------
# STEP 2: schema + direction distribution
# --------------------------------------------------------------------------

def step2_schema_and_direction(sb) -> dict:
    print("=" * 96)
    print("STEP 2 — hist_pattern_signals schema + direction columns")
    print("=" * 96)
    r = sb.table("hist_pattern_signals").select("*").limit(1).execute()
    if not r.data:
        print("[FATAL] table empty")
        return {}
    cols = list(r.data[0].keys())
    print(f"Columns ({len(cols)}):")
    for c in cols:
        sample_val = r.data[0].get(c)
        print(f"  {c:<24} sample={sample_val!r}")
    print()
    direction_candidates = ["direction", "side", "bias", "is_bull",
                            "is_bullish", "trade_direction", "pattern_direction",
                            "signed", "long_short"]
    found = [c for c in direction_candidates if c in cols]
    print(f"Direction-like columns found: {found or 'NONE'}")
    print()
    if not found:
        print("[INFO] No direction column. H3 (direction-encoded-elsewhere) UNLIKELY")
        print("       unless direction is encoded numerically (e.g. ret_30m sign).")
        return {"cols": cols, "direction_cols": []}

    # For each direction col, show distribution conditional on FVG-ish patterns
    print("Direction distribution conditional on pattern_type containing 'FVG':")
    for dcol in found:
        # Pull a sample of FVG-typed rows
        rr = (sb.table("hist_pattern_signals").select(f"pattern_type, {dcol}")
              .ilike("pattern_type", "%FVG%")
              .limit(5000).execute())
        rows = rr.data or []
        cross = Counter()
        for row in rows:
            cross[(row.get("pattern_type"), row.get(dcol))] += 1
        print(f"  Column: {dcol}")
        for (pt, dv), n in cross.most_common(20):
            print(f"    {pt:<14} {dv!r:<14} {n:>6}")
        print()
    return {"cols": cols, "direction_cols": found}


# --------------------------------------------------------------------------
# STEP 3: list sibling tables
# --------------------------------------------------------------------------

def step3_sibling_tables(sb) -> dict:
    print("=" * 96)
    print("STEP 3 — Sibling tables matching pattern/signal/fvg")
    print("=" * 96)
    # Supabase Python client doesn't expose information_schema directly via
    # PostgREST. Try a curated list of likely sibling table names; report
    # which exist (return non-empty result for select limit 1).
    candidates = [
        "hist_pattern_signals", "hist_signals", "hist_fvg_signals",
        "hist_bull_signals", "hist_bear_signals",
        "pattern_signals", "fvg_signals", "ict_signals",
        "ict_fvg_signals", "ict_pattern_signals",
        "hist_ict_signals", "hist_pattern_signals_v2",
        "hist_ob_signals", "ict_zones", "ict_htf_zones",
    ]
    existing = []
    for tbl in candidates:
        try:
            r = sb.table(tbl).select("*", count="exact").limit(0).execute()
            cnt = r.count if hasattr(r, "count") else None
            existing.append((tbl, cnt))
            print(f"  {tbl:<32} EXISTS (count={cnt})")
        except Exception:
            pass
    if not existing:
        print("  (no candidate tables responded)")
    print()
    other = [t for (t, _) in existing
             if t not in ("hist_pattern_signals", "ict_htf_zones")]
    if other:
        print(f"[INFO] Other signal-like tables found: {other}")
        print("       Inspect these manually -- BEAR FVGs may live there.")
    else:
        print("[INFO] No alternate signal table found -- H5 less likely.")
    print()
    return {"existing": [t for (t, _) in existing]}


# --------------------------------------------------------------------------
# STEP 4: daily candle structure (sanity check on bear-day count)
# --------------------------------------------------------------------------

def step4_bear_day_count(sb) -> dict:
    print("=" * 96)
    print("STEP 4 — Daily candle structure last 30 trading days (sanity check)")
    print("=" * 96)
    out = {}
    for symbol in SYMBOLS:
        # Pull last ~ 60 calendar days of 5m bars; aggregate to daily
        r = (sb.table("hist_spot_bars_5m").select("bar_ts")
             .eq("symbol", symbol).order("bar_ts", desc=True).limit(1).execute())
        if not r.data:
            print(f"  {symbol}: no data")
            continue
        last = parse_dt(r.data[0]["bar_ts"])
        cutoff = last - timedelta(days=int(STEP4_LOOKBACK_DAYS * 1.6))
        rows = []
        offset = 0
        while True:
            rr = (sb.table("hist_spot_bars_5m")
                  .select("bar_ts, open, close, trade_date")
                  .eq("symbol", symbol)
                  .gte("bar_ts", cutoff.isoformat())
                  .order("bar_ts")
                  .range(offset, offset + PAGE_SIZE - 1).execute())
            batch = rr.data or []
            rows.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
            if offset > 100_000:
                break
        # Aggregate by trade_date: open=first bar's open, close=last bar's close
        by_date: dict = {}
        for row in rows:
            td = row.get("trade_date")
            if not td:
                continue
            if td not in by_date:
                by_date[td] = {"first": row, "last": row}
            else:
                by_date[td]["last"] = row
        days = sorted(by_date.keys(), reverse=True)[:STEP4_LOOKBACK_DAYS]
        bull_days, bear_days, doji_days = 0, 0, 0
        for d in days:
            try:
                o = float(by_date[d]["first"]["open"])
                c = float(by_date[d]["last"]["close"])
            except (TypeError, ValueError, KeyError):
                continue
            if c > o:
                bull_days += 1
            elif c < o:
                bear_days += 1
            else:
                doji_days += 1
        total = bull_days + bear_days + doji_days
        bear_pct = bear_days / total * 100 if total else 0
        print(f"  {symbol}: {total} sessions | "
              f"bull_days={bull_days} bear_days={bear_days} doji_days={doji_days} "
              f"| bear share={bear_pct:.1f}%")
        out[symbol] = {"bull": bull_days, "bear": bear_days,
                       "doji": doji_days, "total": total}
    print()
    print("[INFO] If bear_days > 5 in a 30-day window AND zero BEAR_FVG signals exist,")
    print("       H6 (market asymmetry) is rejected. The data path is the problem.")
    print()
    return out


# --------------------------------------------------------------------------
# STEP 5: manual canonical BEAR_FVG scan in hist_spot_bars_5m
# --------------------------------------------------------------------------

def step5_manual_fvg_scan(sb) -> dict:
    """Canonical 3-bar BEAR_FVG: bars K, K+1, K+2 where K.low > (K+2).high.
    The middle bar (K+1) creates the imbalance via downward displacement.
    Mirror BULL_FVG: K.high < (K+2).low."""
    print("=" * 96)
    print("STEP 5 — Manual canonical BEAR_FVG scan in hist_spot_bars_5m (last 60d)")
    print("=" * 96)
    out = {}
    for symbol in SYMBOLS:
        r = (sb.table("hist_spot_bars_5m").select("bar_ts")
             .eq("symbol", symbol).order("bar_ts", desc=True).limit(1).execute())
        if not r.data:
            continue
        last = parse_dt(r.data[0]["bar_ts"])
        cutoff = last - timedelta(days=int(STEP5_LOOKBACK_DAYS * 1.6))
        rows = []
        offset = 0
        while True:
            rr = (sb.table("hist_spot_bars_5m")
                  .select("bar_ts, open, high, low, close, trade_date")
                  .eq("symbol", symbol)
                  .gte("bar_ts", cutoff.isoformat())
                  .order("bar_ts")
                  .range(offset, offset + PAGE_SIZE - 1).execute())
            batch = rr.data or []
            rows.extend(batch)
            if len(batch) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
            if offset > 200_000:
                break
        if not rows:
            continue
        # Sort by bar_ts (already ordered, but be safe)
        rows.sort(key=lambda x: x["bar_ts"])
        # Cast price fields
        for row in rows:
            for col in ("open", "high", "low", "close"):
                try:
                    row[col] = float(row[col])
                except (TypeError, ValueError, KeyError):
                    row[col] = None
        # Limit to last STEP5_LOOKBACK_DAYS distinct trade_dates
        unique_dates = sorted({r["trade_date"] for r in rows if r.get("trade_date")},
                              reverse=True)[:STEP5_LOOKBACK_DAYS]
        date_set = set(unique_dates)
        rows = [r for r in rows if r.get("trade_date") in date_set]
        # Group by trade_date so FVGs don't span sessions
        by_date = defaultdict(list)
        for row in rows:
            by_date[row["trade_date"]].append(row)
        bear_count = 0
        bull_count = 0
        for td, day_rows in by_date.items():
            day_rows.sort(key=lambda x: x["bar_ts"])
            for i in range(len(day_rows) - 2):
                k, k1, k2 = day_rows[i], day_rows[i + 1], day_rows[i + 2]
                if any(b["high"] is None or b["low"] is None for b in (k, k1, k2)):
                    continue
                if k["low"] > k2["high"]:
                    bear_count += 1
                if k["high"] < k2["low"]:
                    bull_count += 1
        print(f"  {symbol}: scanned {len(unique_dates)} sessions, "
              f"{len(rows)} 5m bars")
        print(f"    Canonical BULL_FVG 3-bar shapes: {bull_count}")
        print(f"    Canonical BEAR_FVG 3-bar shapes: {bear_count}")
        out[symbol] = {"bull_fvg_shapes": bull_count, "bear_fvg_shapes": bear_count}
    # Cross-check vs hist_pattern_signals BULL/BEAR_FVG counts in same window
    print()
    print("Comparison vs hist_pattern_signals (same 60d window):")
    for symbol in SYMBOLS:
        r_last = (sb.table("hist_spot_bars_5m").select("bar_ts")
                  .eq("symbol", symbol).order("bar_ts", desc=True).limit(1).execute())
        if not r_last.data:
            continue
        last = parse_dt(r_last.data[0]["bar_ts"])
        cutoff = last - timedelta(days=int(STEP5_LOOKBACK_DAYS * 1.6))
        for ptype in ("BULL_FVG", "BEAR_FVG"):
            r_sig = (sb.table("hist_pattern_signals")
                     .select("*", count="exact")
                     .eq("symbol", symbol).eq("pattern_type", ptype)
                     .gte("bar_ts", cutoff.isoformat()).limit(0).execute())
            cnt = r_sig.count if hasattr(r_sig, "count") else "?"
            print(f"  {symbol} {ptype:<10} signals last 60d: {cnt}")
    print()
    return out


# --------------------------------------------------------------------------
# DIAGNOSIS
# --------------------------------------------------------------------------

def diagnose(s1: dict, s2: dict, s3: dict, s4: dict, s5: dict):
    print("=" * 96)
    print("DIAGNOSIS")
    print("=" * 96)
    fvg_types = s1.get("fvg_flavoured", {})
    bear_flavoured = s1.get("bear_flavoured", {})
    bear_fvg_in_s1 = any("BEAR" in (k or "").upper() and "FVG" in (k or "").upper()
                         for k in fvg_types)
    direction_cols = s2.get("direction_cols", [])
    siblings = [t for t in s3.get("existing", [])
                if t not in ("hist_pattern_signals", "ict_htf_zones")]
    bear_shapes_total = sum(v.get("bear_fvg_shapes", 0) for v in s5.values())
    bull_shapes_total = sum(v.get("bull_fvg_shapes", 0) for v in s5.values())
    bear_days_total = sum(v.get("bear", 0) for v in s4.values())

    print(f"S1: BEAR-FVG-flavoured pattern_types in table: {bear_fvg_in_s1}")
    print(f"S1: All FVG-flavoured types: {list(fvg_types.keys())}")
    print(f"S2: Direction columns in schema: {direction_cols}")
    print(f"S3: Sibling signal tables: {siblings}")
    print(f"S4: Bear-day count last 30d (both syms): {bear_days_total}")
    print(f"S5: Canonical BEAR-FVG shapes in 5m bars (60d): {bear_shapes_total}")
    print(f"S5: Canonical BULL-FVG shapes in 5m bars (60d): {bull_shapes_total}")
    print()

    # Decide
    if bear_fvg_in_s1:
        print("VERDICT: Database HAS BEAR_FVG rows but Exp 50 query missed them.")
        print("         Most likely H2 (non-canonical label) — check exact pattern_type")
        print("         strings in S1 output and re-run Exp 50 / 50b with the correct values.")
    elif direction_cols and any("FVG" in k for k in fvg_types
                                if k and "BULL" not in k.upper() and "BEAR" not in k.upper()):
        print("VERDICT: H3 (direction-encoded-elsewhere). Generic 'FVG' rows exist;")
        print(f"         direction is in: {direction_cols}. Re-run Exp 50 partitioning")
        print("         on (pattern_type='FVG', direction column).")
    elif siblings:
        print(f"VERDICT: H5 candidate. Sibling tables exist: {siblings}.")
        print("         Inspect their schema for BEAR_FVG-shaped rows.")
    elif bear_shapes_total > 0 and bear_days_total > 5:
        print("VERDICT: H1 (detector-side asymmetry) CONFIRMED.")
        print(f"         {bear_shapes_total} canonical BEAR-FVG shapes exist in 5m bars,")
        print(f"         {bear_days_total} bear-days in 30-day window, but 0 BEAR_FVG")
        print("         signals in hist_pattern_signals. The detector does not emit")
        print("         BEAR_FVG. Code review of build_pattern_signals.py needed before")
        print("         Exp 50 / 50b can be re-run with both directions.")
    else:
        print("VERDICT: UNRESOLVED. None of H1-H5 cleanly matches. Inspect raw output.")
    print()
    print("=" * 96)


def main():
    sb = get_client()
    print("=" * 96)
    print("BEAR_FVG ABSENCE AUDIT — five-step diagnostic")
    print("=" * 96)
    print()
    s1 = step1_pattern_type_distribution(sb)
    s2 = step2_schema_and_direction(sb)
    s3 = step3_sibling_tables(sb)
    s4 = step4_bear_day_count(sb)
    s5 = step5_manual_fvg_scan(sb)
    diagnose(s1, s2, s3, s4, s5)


if __name__ == "__main__":
    main()
