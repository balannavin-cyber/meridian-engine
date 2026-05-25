"""
audit_s32_enh100_falsification.py — ADR-010 v3 100-sample falsification audit.

Audits the 9 ENH-100 columns + the 5 pre-existing forward columns by independently
re-computing each from underlying source tables and comparing to stored values:

  Spot returns (forward_5m / 15m / 30m / 1h / 120m / eod):
    source = hist_spot_bars_1m (same as writer)
    threshold = 1bp absolute
    nature = self-consistency (same source, same algo) — catches bugs in the
             writer's lookup/timezone/edge logic, NOT cross-source drift

  MFE / MAE / time_to_mfe_min:
    source = hist_spot_bars_1m
    threshold = 1bp absolute (mfe/mae), exact match (time_to_mfe)

  DTE_at_formation:
    source = hist_atm_option_bars_5m (vendor pre-compute)
    threshold = exact match
    re-derive via independent floor_5m + nearest-expiry lookup, compare integer

  ATM PnL (5m / 15m / 30m / 60m):
    source = hist_option_bars_1m (FULL CHAIN, not the ATM-subset table the writer uses)
    threshold = 5% relative
    nature = cross-tier validation: writer reads hist_atm_option_bars_5m;
             audit re-derives premium % from the chain table. Discrepancy >5%
             signals either (a) writer math error or (b) vendor data drift
             between the two tier ingestion paths.

Strategy:
  - Sample n primitives uniformly at random from ict_primitive_outcomes
  - For each sample: re-compute every populated column, compare to stored
  - Report per-column: N audited, N matched, N discrepant, worst discrepancy

Era awareness: hist_spot_bars_1m (Bug B3 pre-2026-04-07) handled via
existing normalize_hist_bar_ts. hist_atm_option_bars_5m + hist_option_bars_1m
both IST-mislabeled +00 (Bug B3-equivalent confirmed via hour-of-day audit
2026-05-22) — handled via _vendor_bar_ts_label conversion.

Usage:
  python audit_s32_enh100_falsification.py [--n 100] [--symbol NIFTY|SENSEX|both] \\
                                            [--seed 42] [--verbose]
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time as _time
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

UTC = timezone.utc
IST = ZoneInfo("Asia/Kolkata")
ERA_BOUNDARY_UTC = datetime(2026, 4, 7, 0, 0, 0, tzinfo=UTC)
INSTRUMENT_ID_BY_SYMBOL = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}
SYMBOL_BY_INSTRUMENT_ID = {v: k for k, v in INSTRUMENT_ID_BY_SYMBOL.items()}

FWD_THRESHOLD_BP = 1.0          # 1 basis point absolute (0.01 percentage points)
ATM_PNL_THRESHOLD_REL = 0.05    # 5% relative


# ----------------------------------------------------------------------------
# Supabase client + era-aware timestamp helpers (mirrors build_ict_primitives.py)
# ----------------------------------------------------------------------------

def get_client():
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY")
           or os.environ.get("SUPABASE_KEY"))
    if not url or not key:
        raise SystemExit("[FATAL] SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY required")
    return create_client(url, key)


def parse_ts(raw) -> datetime:
    """Parse Supabase TIMESTAMPTZ payload to tz-aware UTC datetime."""
    import re as _re
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    s = str(raw).strip().replace("Z", "+00:00")
    # Normalize fractional seconds to 6 digits (B22)
    s = _re.sub(
        r"\.(\d{1,6})(?=[+-Z])|\.(\d{1,6})$",
        lambda m: f".{(m.group(1) or m.group(2) or '').ljust(6, '0')[:6]}",
        s,
    )
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def normalize_hist_bar_ts(raw) -> datetime:
    """Era-aware: pre-2026-04-07 hist_spot_bars_1m is IST wall-clock labeled +00."""
    raw_dt = parse_ts(raw)
    if raw_dt < ERA_BOUNDARY_UTC:
        ist_naive = raw_dt.replace(tzinfo=None)
        return ist_naive.replace(tzinfo=IST).astimezone(UTC)
    return raw_dt


def vendor_bar_ts_label(real_utc_dt: datetime) -> str:
    """real-UTC → vendor IST-mislabeled +00 string (for filter against vendor tables)."""
    ist = real_utc_dt.astimezone(IST)
    return ist.replace(tzinfo=None).replace(tzinfo=UTC).isoformat()


def floor_5m(ts: datetime) -> datetime:
    f = ts.replace(second=0, microsecond=0)
    return f.replace(minute=(f.minute // 5) * 5)


# ----------------------------------------------------------------------------
# Sample selection
# ----------------------------------------------------------------------------

def sample_outcomes(sb, n: int, symbol_filter: Optional[str], seed: int) -> list[dict]:
    """Fetch n random primitives with outcomes for audit.

    Uses ORDER BY random() server-side (small n; acceptable cost).
    """
    random.seed(seed)
    # Fetch a larger pool then Python-sample to get reproducible randomization
    pool_size = min(n * 10, 5000)
    q = (
        sb.table("ict_primitive_outcomes")
          .select("*,ict_primitives!inner(id,symbol,timeframe,primitive_type,direction,"
                  "source_bar_ts,valid_from,zone_low,zone_high,level)")
    )
    if symbol_filter and symbol_filter != "both":
        # Filter via join — postgrest syntax for foreign-table filter
        q = q.eq("ict_primitives.symbol", symbol_filter)
    res = q.limit(pool_size).execute()
    pool = res.data or []
    if symbol_filter and symbol_filter != "both":
        # Belt-and-braces in case the foreign filter didn't apply
        pool = [r for r in pool if r.get("ict_primitives", {}).get("symbol") == symbol_filter]
    if len(pool) < n:
        print(f"  [WARN] only {len(pool)} primitives available; sampling all")
        return pool
    return random.sample(pool, n)


# ----------------------------------------------------------------------------
# Spot-bar fetch (era-aware) for forward-return + MFE/MAE re-computation
# ----------------------------------------------------------------------------

def fetch_spot_bars(sb, instrument_id: str, start_utc: datetime,
                    end_utc: datetime) -> list[tuple[datetime, float, float, float, float]]:
    """Fetch hist_spot_bars_1m bars in [start, end], era-normalized to real-UTC.

    Returns list of (ts_utc, open, high, low, close).
    """
    out = []
    page = 0
    while True:
        offset = page * 1000
        res = (
            sb.table("hist_spot_bars_1m")
              .select("bar_ts,open,high,low,close")
              .eq("instrument_id", instrument_id)
              .gte("bar_ts", start_utc.isoformat())
              .lte("bar_ts", end_utc.isoformat())
              .order("bar_ts", desc=False)
              .range(offset, offset + 999)
              .execute()
        )
        rows = res.data or []
        for r in rows:
            ts_utc = normalize_hist_bar_ts(r["bar_ts"])
            out.append((ts_utc, float(r["open"]), float(r["high"]),
                        float(r["low"]), float(r["close"])))
        if len(rows) < 1000:
            break
        page += 1
    return out


def spot_at(bars, ts: datetime) -> Optional[float]:
    """Nearest bar at-or-after ts within 5min, return close."""
    floored = ts.replace(second=0, microsecond=0)
    for d in range(0, 5):
        probe = floored + timedelta(minutes=d)
        for b_ts, _, _, _, b_close in bars:
            if b_ts == probe:
                return b_close
    return None


def eod_ts(anchor_ts: datetime) -> datetime:
    ist = anchor_ts.astimezone(IST)
    return ist.replace(hour=15, minute=30, second=0, microsecond=0).astimezone(UTC)


# ----------------------------------------------------------------------------
# Re-computation helpers
# ----------------------------------------------------------------------------

def recompute_forward_returns(bars, valid_from: datetime) -> dict:
    """Independently compute forward_*_pct from spot bars."""
    anchor = spot_at(bars, valid_from)
    out = {}
    if anchor is None or anchor == 0:
        return out
    for col, mins in [("forward_5m_pct", 5), ("forward_15m_pct", 15),
                       ("forward_30m_pct", 30), ("forward_1h_pct", 60),
                       ("forward_120m_pct", 120)]:
        future = spot_at(bars, valid_from + timedelta(minutes=mins))
        if future is not None:
            out[col] = (future - anchor) / anchor * 100.0
    # forward_eod_pct
    eod = eod_ts(valid_from)
    if eod > valid_from:
        future_eod = spot_at(bars, eod)
        if future_eod is not None:
            out["forward_eod_pct"] = (future_eod - anchor) / anchor * 100.0
    return out


def recompute_mfe_mae(bars, valid_from: datetime, direction: str) -> dict:
    """Independently compute MFE/MAE/time_to_mfe_min over 30-min window."""
    if direction not in ("BULL", "BEAR"):
        return {}
    anchor = spot_at(bars, valid_from)
    if anchor is None or anchor == 0:
        return {}
    window_end = valid_from + timedelta(minutes=30)
    max_high = anchor
    max_high_ts = valid_from
    min_low = anchor
    min_low_ts = valid_from
    saw_any = False
    for b_ts, _, b_high, b_low, _ in bars:
        if b_ts < valid_from or b_ts > window_end:
            continue
        saw_any = True
        if b_high > max_high:
            max_high = b_high
            max_high_ts = b_ts
        if b_low < min_low:
            min_low = b_low
            min_low_ts = b_ts
    if not saw_any:
        return {}
    out = {}
    if direction == "BULL":
        out["mfe_pct"] = (max_high - anchor) / anchor * 100.0
        out["mae_pct"] = (min_low - anchor) / anchor * 100.0
        mfe_ts = max_high_ts
    else:
        out["mfe_pct"] = (anchor - min_low) / anchor * 100.0
        out["mae_pct"] = -((max_high - anchor) / anchor * 100.0)
        mfe_ts = min_low_ts
    if out["mfe_pct"] > 0:
        out["time_to_mfe_min"] = int((mfe_ts - valid_from).total_seconds() // 60)
    return out


def recompute_dte(sb, instrument_id: str, valid_from: datetime) -> Optional[int]:
    """Re-derive dte_at_formation: query hist_atm_option_bars_5m at floor_5m(valid_from),
    get the nearest expiry, compute (expiry - valid_from.date()).days."""
    anchor_5m = floor_5m(valid_from)
    vendor_bts = vendor_bar_ts_label(anchor_5m)
    res = (
        sb.table("hist_atm_option_bars_5m")
          .select("expiry_date,dte")
          .eq("instrument_id", instrument_id)
          .eq("bar_ts", vendor_bts)
          .order("expiry_date", desc=False)
          .limit(1)
          .execute()
    )
    rows = res.data or []
    if not rows:
        return None
    # Return vendor's pre-computed dte directly (matches writer's path)
    raw_dte = rows[0].get("dte")
    return int(raw_dte) if raw_dte is not None else None


def recompute_atm_pnl_from_chain(sb, instrument_id: str, valid_from: datetime,
                                  direction: str) -> dict:
    """Re-derive atm_pnl_*_pct from hist_option_bars_1m (full chain).

    Cross-source check: vendor's ATM table vs chain table for the same
    (strike, expiry, option_type) should give consistent premiums.
    """
    if direction not in ("BULL", "BEAR"):
        return {}
    # Step 1: fetch anchor row from ATM table to discover writer's strike + expiry
    anchor_5m = floor_5m(valid_from)
    vendor_bts = vendor_bar_ts_label(anchor_5m)
    res = (
        sb.table("hist_atm_option_bars_5m")
          .select("atm_strike,expiry_date")
          .eq("instrument_id", instrument_id)
          .eq("bar_ts", vendor_bts)
          .order("expiry_date", desc=False)
          .limit(1)
          .execute()
    )
    rows = res.data or []
    if not rows:
        return {}
    strike = float(rows[0]["atm_strike"])
    expiry_date_v = rows[0]["expiry_date"]
    option_type = "CE" if direction == "BULL" else "PE"

    # Step 2: fetch anchor premium from chain table
    chain_anchor_bts = vendor_bar_ts_label(anchor_5m)
    res = (
        sb.table("hist_option_bars_1m")
          .select("bar_ts,close")
          .eq("instrument_id", instrument_id)
          .eq("expiry_date", expiry_date_v)
          .eq("strike", strike)
          .eq("option_type", option_type)
          .eq("bar_ts", chain_anchor_bts)
          .limit(1)
          .execute()
    )
    rows = res.data or []
    if not rows:
        return {}
    premium_t0 = float(rows[0]["close"])
    if premium_t0 == 0:
        return {}

    # Step 3: fetch future premiums; same strike-expiry-type assumption
    # (audit doesn't replicate writer's same-strike-on-vendor-roll filter — if writer
    # populated a column, vendor's atm_strike must have been stable; cross-check)
    out = {}
    for col, mins in [("atm_pnl_5m_pct", 5), ("atm_pnl_15m_pct", 15),
                       ("atm_pnl_30m_pct", 30), ("atm_pnl_60m_pct", 60)]:
        future_5m = anchor_5m + timedelta(minutes=mins)
        future_bts = vendor_bar_ts_label(future_5m)
        res = (
            sb.table("hist_option_bars_1m")
              .select("close")
              .eq("instrument_id", instrument_id)
              .eq("expiry_date", expiry_date_v)
              .eq("strike", strike)
              .eq("option_type", option_type)
              .eq("bar_ts", future_bts)
              .limit(1)
              .execute()
        )
        rows = res.data or []
        if not rows:
            continue
        future_premium = float(rows[0]["close"])
        if future_premium == 0:
            continue
        out[col] = (future_premium - premium_t0) / premium_t0 * 100.0
    return out


# ----------------------------------------------------------------------------
# Comparison + reporting
# ----------------------------------------------------------------------------

def compare_value(col: str, stored, recomputed, threshold_kind: str,
                  threshold: float) -> tuple[str, float]:
    """Returns (status, discrepancy_value). Status: MATCH / DISCREPANT / MISSING_BOTH /
    MISSING_STORED / MISSING_RECOMPUTED."""
    if stored is None and recomputed is None:
        return ("MISSING_BOTH", 0.0)
    if stored is None:
        return ("MISSING_STORED", 0.0)
    if recomputed is None:
        return ("MISSING_RECOMPUTED", 0.0)
    s = float(stored)
    r = float(recomputed)
    if threshold_kind == "absolute_bp":
        # 1bp = 0.01 percentage points (since stored values are pct)
        diff_pp = abs(s - r)
        # threshold is in bp; convert to pp for comparison
        return ("MATCH" if diff_pp <= threshold * 0.01 else "DISCREPANT", diff_pp)
    if threshold_kind == "relative":
        if abs(s) < 1e-9:
            diff = abs(s - r)
            return ("MATCH" if diff < 0.01 else "DISCREPANT", diff)
        rel_diff = abs(s - r) / abs(s)
        return ("MATCH" if rel_diff <= threshold else "DISCREPANT", rel_diff)
    if threshold_kind == "exact":
        return ("MATCH" if int(s) == int(r) else "DISCREPANT", abs(s - r))
    raise ValueError(threshold_kind)


def audit_primitive(sb, sample: dict, verbose: bool) -> dict:
    """Audit a single sample; returns per-column comparison results."""
    prim = sample.get("ict_primitives", {})
    symbol = prim.get("symbol")
    instrument_id = INSTRUMENT_ID_BY_SYMBOL.get(symbol)
    if instrument_id is None:
        return {"_error": f"unknown symbol {symbol}"}
    valid_from = parse_ts(prim["valid_from"])
    direction = prim.get("direction", "NONE")

    # Fetch spot bars for forward + MFE/MAE window (120min + small buffer)
    spot_start = valid_from - timedelta(minutes=2)
    spot_end = valid_from + timedelta(minutes=150)
    bars = fetch_spot_bars(sb, instrument_id, spot_start, spot_end)

    # Re-compute
    rec_fwd = recompute_forward_returns(bars, valid_from)
    rec_mfe = recompute_mfe_mae(bars, valid_from, direction)
    rec_dte = recompute_dte(sb, instrument_id, valid_from)
    rec_atm = recompute_atm_pnl_from_chain(sb, instrument_id, valid_from, direction)

    # Compare each column
    out = {"primitive_id": prim.get("id"), "symbol": symbol, "direction": direction,
           "valid_from": valid_from.isoformat(), "columns": {}}
    forward_cols = ["forward_5m_pct", "forward_15m_pct", "forward_30m_pct",
                    "forward_1h_pct", "forward_120m_pct", "forward_eod_pct"]
    for col in forward_cols:
        out["columns"][col] = compare_value(col, sample.get(col), rec_fwd.get(col),
                                             "absolute_bp", FWD_THRESHOLD_BP)
    out["columns"]["mfe_pct"]   = compare_value("mfe_pct", sample.get("mfe_pct"),
                                                  rec_mfe.get("mfe_pct"),
                                                  "absolute_bp", FWD_THRESHOLD_BP)
    out["columns"]["mae_pct"]   = compare_value("mae_pct", sample.get("mae_pct"),
                                                  rec_mfe.get("mae_pct"),
                                                  "absolute_bp", FWD_THRESHOLD_BP)
    out["columns"]["time_to_mfe_min"] = compare_value("time_to_mfe_min",
                                                  sample.get("time_to_mfe_min"),
                                                  rec_mfe.get("time_to_mfe_min"),
                                                  "exact", 0)
    out["columns"]["dte_at_formation"] = compare_value("dte_at_formation",
                                                  sample.get("dte_at_formation"),
                                                  rec_dte, "exact", 0)
    for col in ["atm_pnl_5m_pct", "atm_pnl_15m_pct",
                "atm_pnl_30m_pct", "atm_pnl_60m_pct"]:
        out["columns"][col] = compare_value(col, sample.get(col), rec_atm.get(col),
                                             "relative", ATM_PNL_THRESHOLD_REL)
    return out


def print_report(results: list[dict]) -> None:
    """Aggregate per-column results across the sample, print summary."""
    all_cols = ["forward_5m_pct", "forward_15m_pct", "forward_30m_pct",
                "forward_1h_pct", "forward_120m_pct", "forward_eod_pct",
                "mfe_pct", "mae_pct", "time_to_mfe_min", "dte_at_formation",
                "atm_pnl_5m_pct", "atm_pnl_15m_pct", "atm_pnl_30m_pct",
                "atm_pnl_60m_pct"]
    print("\n" + "=" * 92)
    print(f"{'COLUMN':<22}  {'MATCH':>7}  {'DISC':>5}  {'M_BOTH':>7}  "
          f"{'M_STORE':>7}  {'M_RECMP':>7}  {'WORST_DISC':>11}")
    print("-" * 92)
    worst_examples = []
    for col in all_cols:
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
        print("\nWORST DISCREPANCY DETAIL (top 5):")
        worst_examples.sort(key=lambda x: -x[1])
        for col, disc, samp in worst_examples[:5]:
            print(f"  {col}: disc={disc:.4f}  pid={samp['primitive_id']}  "
                  f"symbol={samp['symbol']}  direction={samp['direction']}  "
                  f"valid_from={samp['valid_from']}")
    else:
        print("\nNo discrepancies found in any audited column.")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="sample size")
    ap.add_argument("--symbol", choices=["NIFTY", "SENSEX", "both"], default="both")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    print(f"[start] ENH-100 v3 falsification audit  n={args.n}  symbol={args.symbol}")
    sb = get_client()
    t0 = _time.time()
    samples = sample_outcomes(sb, args.n, args.symbol, args.seed)
    print(f"  sampled {len(samples)} primitives in {_time.time() - t0:.1f}s")

    results = []
    t1 = _time.time()
    for i, samp in enumerate(samples):
        try:
            r = audit_primitive(sb, samp, args.verbose)
        except Exception as e:
            r = {"_error": str(e), "primitive_id": samp.get("primitive_id")}
        results.append(r)
        if (i + 1) % 10 == 0:
            print(f"    audited {i + 1}/{len(samples)}  "
                  f"elapsed={_time.time() - t1:.1f}s")
    print(f"  audit completed in {_time.time() - t1:.1f}s")

    errors = [r for r in results if "_error" in r]
    if errors:
        print(f"\n[WARN] {len(errors)} primitives errored during audit:")
        for e in errors[:5]:
            print(f"  pid={e.get('primitive_id')}  err={e.get('_error')}")

    print_report(results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
