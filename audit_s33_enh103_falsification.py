"""
audit_s33_enh103_falsification.py — S33 ENH-103 falsification audit.

ADR-010 v3 (Path A) falsification commitment for the 5 retest-anchored ATM PnL
columns added by ENH-103: option_pnl_5m / 15m / 30m / 60m / eod.

Architecture mirrors S32 v5 audit (audit_s32_enh100_falsification_v5.py):
  - Sample n primitives uniformly at random from RETESTED cohort
  - For each, re-derive option PnL from hist_option_bars_1m (chain) at
    first_retest_ts + N min, using end-of-5m alignment (last 1m bar in the
    5m window starting at first_retest_ts + Nmin has bar_ts = +(N+4):59)
  - Compare to stored option_pnl_*; threshold 5% relative

Same Bug B3 + Bug C handling as v5 audit:
  - hist_option_bars_1m bar_ts is IST-mislabeled +00 (era-confirmed) →
    use _vendor_bar_ts_label for filter bounds
  - chain bars at HH:MM:59 → use 1-min range filter
  - 5m bar "close" = last 1m bar within the 5m window (end-of-5m semantic)

Cross-tier drift caveat: like v5, expect 5-10% relative discrepancy on most
populated cells because hist_atm_option_bars_5m and hist_option_bars_1m
appear to be independently-ingested vendor tier paths. The audit verifies
that writer's math is CORRECT (column populated when same-strike enforcement
passes and vendor coverage exists); it does NOT verify that the two vendor
tables agree. Writer correctness for the SAME source-table read+math is
already verified clean by S32 v5 audit on the formation-anchored ATM PnL
columns (same codepath, different anchor timestamp).

Usage:
  python audit_s33_enh103_falsification.py [--n 100] [--symbol NIFTY|SENSEX|both] \\
                                            [--seed 42]
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time as _time
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

UTC = timezone.utc
IST = ZoneInfo("Asia/Kolkata")
INSTRUMENT_ID_BY_SYMBOL = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

ATM_PNL_THRESHOLD_REL = 0.05  # 5% relative per ADR-010 v3 (soft per cross-tier drift)


def get_client():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if not url or not key:
        raise SystemExit("[FATAL] SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY required")
    return create_client(url, key)


def parse_ts(raw):
    import re as _re
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    s = str(raw).strip().replace("Z", "+00:00")
    s = _re.sub(r"\.(\d{1,6})(?=[+-Z])|\.(\d{1,6})$",
                lambda m: f".{(m.group(1) or m.group(2) or '').ljust(6, '0')[:6]}", s)
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def vendor_bar_ts_label(real_utc_dt):
    ist = real_utc_dt.astimezone(IST)
    return ist.replace(tzinfo=None).replace(tzinfo=UTC).isoformat()


def floor_5m(ts):
    f = ts.replace(second=0, microsecond=0)
    return f.replace(minute=(f.minute // 5) * 5)


def sample_retested(sb, n, symbol_filter, seed):
    """Sample primitives where retest_status='RETESTED' AND at least one
    option_pnl_* column is non-null (audit needs SOMETHING to compare)."""
    random.seed(seed)
    pool_size = min(n * 10, 5000)
    q = (
        sb.table("ict_primitive_outcomes")
          .select("primitive_id,first_retest_ts,retest_status,"
                  "option_pnl_5m,option_pnl_15m,option_pnl_30m,option_pnl_60m,option_pnl_eod,"
                  "ict_primitives!inner(id,symbol,timeframe,primitive_type,direction,valid_from)")
          .eq("retest_status", "RETESTED")
          .or_("option_pnl_5m.not.is.null,option_pnl_15m.not.is.null,"
               "option_pnl_30m.not.is.null,option_pnl_60m.not.is.null,option_pnl_eod.not.is.null")
    )
    if symbol_filter and symbol_filter != "both":
        q = q.eq("ict_primitives.symbol", symbol_filter)
    res = q.limit(pool_size).execute()
    pool = res.data or []
    if symbol_filter and symbol_filter != "both":
        pool = [r for r in pool if r.get("ict_primitives", {}).get("symbol") == symbol_filter]
    if len(pool) < n:
        print(f"  [WARN] only {len(pool)} eligible primitives; sampling all")
        return pool
    return random.sample(pool, n)


def _chain_premium_end_of_5m(sb, instrument_id, expiry_date_v, strike, option_type,
                              target_5m_start):
    """Chain table close at end of 5m window starting at target_5m_start.
    Bar stored at HH:(MM+4):59 represents close of [HH:(MM+4):00, HH:(MM+5):00)
    = price at end of 5m window. Same logic as v5 audit."""
    last_min_start = target_5m_start + timedelta(minutes=4)
    last_min_end = target_5m_start + timedelta(minutes=5)
    res = (
        sb.table("hist_option_bars_1m")
          .select("close")
          .eq("instrument_id", instrument_id)
          .eq("expiry_date", expiry_date_v)
          .eq("strike", strike)
          .eq("option_type", option_type)
          .gte("bar_ts", vendor_bar_ts_label(last_min_start))
          .lt("bar_ts", vendor_bar_ts_label(last_min_end))
          .limit(1)
          .execute()
    )
    rows = res.data or []
    if not rows:
        return None
    return float(rows[0]["close"])


def recompute_retest_option_pnl(sb, instrument_id, first_retest_ts, direction):
    """Re-derive option_pnl_*_pct at retest anchor from hist_option_bars_1m chain.

    Returns dict of populated columns. Mirrors writer's compute_retest_atm_pnl
    but reads from chain table not ATM-5m table (cross-tier check)."""
    if direction not in ("BULL", "BEAR"):
        return {}
    retest_5m = floor_5m(first_retest_ts)
    # Discover writer's strike + expiry via ATM-5m table
    res = (
        sb.table("hist_atm_option_bars_5m")
          .select("atm_strike,expiry_date")
          .eq("instrument_id", instrument_id)
          .eq("bar_ts", vendor_bar_ts_label(retest_5m))
          .order("expiry_date", desc=False)
          .limit(1)
          .execute()
    )
    rows = res.data or []
    if not rows:
        return {}
    try:
        strike = float(rows[0]["atm_strike"])
    except (ValueError, TypeError):
        return {}
    expiry = rows[0]["expiry_date"]
    option_type = "CE" if direction == "BULL" else "PE"

    premium_t0 = _chain_premium_end_of_5m(sb, instrument_id, expiry, strike,
                                           option_type, retest_5m)
    if premium_t0 is None or premium_t0 == 0:
        return {}

    out = {}
    for col, mins in [("option_pnl_5m", 5), ("option_pnl_15m", 15),
                       ("option_pnl_30m", 30), ("option_pnl_60m", 60)]:
        future_premium = _chain_premium_end_of_5m(
            sb, instrument_id, expiry, strike, option_type,
            retest_5m + timedelta(minutes=mins)
        )
        if future_premium is None or future_premium == 0:
            continue
        out[col] = (future_premium - premium_t0) / premium_t0 * 100.0

    # EOD horizon: last 5m bar of retest's IST trading day at IST 15:25
    ist_dt = first_retest_ts.astimezone(IST)
    eod_ist = ist_dt.replace(hour=15, minute=25, second=0, microsecond=0)
    eod_5m = eod_ist.astimezone(UTC)
    if eod_5m > retest_5m:
        future_premium = _chain_premium_end_of_5m(sb, instrument_id, expiry,
                                                   strike, option_type, eod_5m)
        if future_premium is not None and future_premium != 0:
            out["option_pnl_eod"] = (future_premium - premium_t0) / premium_t0 * 100.0
    return out


def compare_value(stored, recomputed, threshold):
    if stored is None and recomputed is None:
        return ("MISSING_BOTH", 0.0)
    if stored is None:
        return ("MISSING_STORED", 0.0)
    if recomputed is None:
        return ("MISSING_RECOMPUTED", 0.0)
    s, r = float(stored), float(recomputed)
    if abs(s) < 1e-9:
        diff = abs(s - r)
        return ("MATCH" if diff < 0.01 else "DISCREPANT", diff)
    rel_diff = abs(s - r) / abs(s)
    return ("MATCH" if rel_diff <= threshold else "DISCREPANT", rel_diff)


def audit_primitive(sb, sample):
    prim = sample.get("ict_primitives", {})
    symbol = prim.get("symbol")
    instrument_id = INSTRUMENT_ID_BY_SYMBOL.get(symbol)
    if instrument_id is None:
        return {"_error": f"unknown symbol {symbol}"}
    first_retest_ts = parse_ts(sample["first_retest_ts"])
    direction = prim.get("direction", "NONE")
    rec = recompute_retest_option_pnl(sb, instrument_id, first_retest_ts, direction)
    out = {"primitive_id": sample.get("primitive_id"), "symbol": symbol,
           "direction": direction, "first_retest_ts": first_retest_ts.isoformat(),
           "columns": {}}
    for col in ["option_pnl_5m", "option_pnl_15m", "option_pnl_30m",
                "option_pnl_60m", "option_pnl_eod"]:
        out["columns"][col] = compare_value(sample.get(col), rec.get(col),
                                              ATM_PNL_THRESHOLD_REL)
    return out


def print_report(results):
    cols = ["option_pnl_5m", "option_pnl_15m", "option_pnl_30m",
            "option_pnl_60m", "option_pnl_eod"]
    print("\n" + "=" * 92)
    print(f"{'COLUMN':<22}  {'MATCH':>7}  {'DISC':>5}  {'M_BOTH':>7}  "
          f"{'M_STORE':>7}  {'M_RECMP':>7}  {'WORST_DISC':>11}")
    print("-" * 92)
    worst_examples = []
    for col in cols:
        counts = {"MATCH": 0, "DISCREPANT": 0, "MISSING_BOTH": 0,
                  "MISSING_STORED": 0, "MISSING_RECOMPUTED": 0}
        worst = 0.0
        worst_sample = None
        for r in results:
            if "_error" in r:
                continue
            status, disc = r["columns"].get(col, ("MISSING_BOTH", 0.0))
            counts[status] = counts.get(status, 0) + 1
            if status == "DISCREPANT" and disc > worst:
                worst = disc
                worst_sample = r
        worst_str = f"{worst:.4f}" if worst > 0 else "—"
        print(f"{col:<22}  {counts['MATCH']:>7}  {counts['DISCREPANT']:>5}  "
              f"{counts['MISSING_BOTH']:>7}  {counts['MISSING_STORED']:>7}  "
              f"{counts['MISSING_RECOMPUTED']:>7}  {worst_str:>11}")
        if worst_sample is not None and counts["DISCREPANT"] > 0:
            worst_examples.append((col, worst, worst_sample))
    print("=" * 92)
    if worst_examples:
        print("\nWORST DISCREPANCY DETAIL (top 10):")
        worst_examples.sort(key=lambda x: -x[1])
        for col, disc, samp in worst_examples[:10]:
            print(f"  {col}: disc={disc:.4f}  pid={samp['primitive_id']}  "
                  f"symbol={samp['symbol']}  direction={samp['direction']}  "
                  f"first_retest_ts={samp['first_retest_ts']}")
    else:
        print("\nNo discrepancies found in any audited column.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--symbol", choices=["NIFTY", "SENSEX", "both"], default="both")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    print(f"[start] ENH-103 falsification audit  n={args.n}  symbol={args.symbol}")
    sb = get_client()
    t0 = _time.time()
    samples = sample_retested(sb, args.n, args.symbol, args.seed)
    print(f"  sampled {len(samples)} retested primitives in {_time.time() - t0:.1f}s")

    results = []
    t1 = _time.time()
    for i, samp in enumerate(samples):
        try:
            r = audit_primitive(sb, samp)
        except Exception as e:
            r = {"_error": str(e), "primitive_id": samp.get("primitive_id")}
        results.append(r)
        if (i + 1) % 10 == 0:
            print(f"    audited {i + 1}/{len(samples)}  elapsed={_time.time() - t1:.1f}s")
    print(f"  audit completed in {_time.time() - t1:.1f}s")

    errors = [r for r in results if "_error" in r]
    if errors:
        print(f"\n[WARN] {len(errors)} primitives errored:")
        for e in errors[:5]:
            print(f"  pid={e.get('primitive_id')}  err={e.get('_error')}")

    print_report(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
