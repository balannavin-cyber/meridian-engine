"""
audit_s32_enh100_falsification_v3.py — ADR-010 v3 falsification audit (final).

v2 ran clean against forward returns (100% MATCH, 0 DISC) and DTE (100% MATCH on
populated cells). Surfaced two audit-side bugs that contaminated the MFE/MAE
and ATM PnL signal:

  Bug A — MFE/MAE upper-window inclusivity.
    Writer: iterates bars_1m with `if b.ts > window_end: break`. b.ts retains
    seconds (HH:MM:59); for window_end = HH+1:00:00, bar at HH+1:00:59 > end
    → break (excluded).
    Audit v2: indexed by minute-floored key; comparison `valid_from <= k <= window_end`
    INCLUDES the floored HH+1:00 bar.
    Effect: 5-6 DISC on mfe/mae (0.07-0.35 pp); 15 DISC on time_to_mfe_min (up to 7min).
    Fix: change to `valid_from <= k < window_end` (strict upper).

  Bug C — ATM PnL cross-tier timestamp alignment.
    Writer reads hist_atm_option_bars_5m.pe_close/ce_close at bar_ts = anchor_5m
    (5m bar START). The OHLC "close" in a 5m bar represents end-of-5m-window
    price (~5 minutes after bar_ts).
    Audit v2: queried hist_option_bars_1m for bars at [anchor_5m, anchor_5m+1min)
    — catches FIRST 1m bar in the 5m window (~1 min after anchor_5m).
    Effect: 100% disagreement (audited price was at 1-min-in, writer's was at
    5-min-in; different moments → 30-80% disc).
    Fix: query chain for LAST 1m bar in 5m window — [anchor_5m+4min, anchor_5m+5min).
    Bar stored as HH:(MM+4):59 represents close of [HH:(MM+4):00, HH:(MM+5):00)
    = price at end of 5m window. Aligns with ATM table close semantic.

Verified contracts from v2 (preserved in v3):
  - Forward returns: 100% MATCH, 0 DISC. Writer spot-return math clean.
  - DTE: 100% MATCH where populated. Vendor pre-compute reads correctly.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time as _time
from datetime import date, datetime, time as _time_t, timedelta, timezone
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

FWD_THRESHOLD_BP = 1.0
ATM_PNL_THRESHOLD_REL = 0.05
PAGE_SIZE = 1000


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


def normalize_hist_bar_ts(raw):
    raw_dt = parse_ts(raw)
    if raw_dt < ERA_BOUNDARY_UTC:
        ist_naive = raw_dt.replace(tzinfo=None)
        return ist_naive.replace(tzinfo=IST).astimezone(UTC)
    return raw_dt


def vendor_bar_ts_label(real_utc_dt):
    ist = real_utc_dt.astimezone(IST)
    return ist.replace(tzinfo=None).replace(tzinfo=UTC).isoformat()


def floor_5m(ts):
    f = ts.replace(second=0, microsecond=0)
    return f.replace(minute=(f.minute // 5) * 5)


def floor_minute(ts):
    return ts.replace(second=0, microsecond=0)


def eod_ts(anchor_ts):
    ist = anchor_ts.astimezone(IST)
    return ist.replace(hour=15, minute=30, second=0, microsecond=0).astimezone(UTC)


class SpotBarsCache:
    def __init__(self, sb):
        self.sb = sb
        self._cache = {}
        self.queries_made = 0

    def _fetch_ist_day(self, instrument_id, ist_d):
        day_start = datetime(ist_d.year, ist_d.month, ist_d.day, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)
        out = {}
        page = 0
        while True:
            offset = page * PAGE_SIZE
            res = (
                self.sb.table("hist_spot_bars_1m")
                  .select("bar_ts,open,high,low,close")
                  .eq("instrument_id", instrument_id)
                  .gte("bar_ts", day_start.isoformat())
                  .lt("bar_ts", day_end.isoformat())
                  .order("bar_ts", desc=False)
                  .range(offset, offset + PAGE_SIZE - 1)
                  .execute()
            )
            self.queries_made += 1
            rows = res.data or []
            for r in rows:
                ts_real = normalize_hist_bar_ts(r["bar_ts"])
                key = floor_minute(ts_real)
                out[key] = (float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
            if len(rows) < PAGE_SIZE:
                break
            page += 1
        return out

    def get_window(self, instrument_id, ts, window_minutes=150):
        ist_d_start = ts.astimezone(IST).date()
        ist_d_end = (ts + timedelta(minutes=window_minutes)).astimezone(IST).date()
        merged = {}
        d = ist_d_start
        while d <= ist_d_end:
            ck = (instrument_id, d)
            if ck not in self._cache:
                self._cache[ck] = self._fetch_ist_day(instrument_id, d)
            merged.update(self._cache[ck])
            d = d + timedelta(days=1)
        return merged


def spot_at(bars, ts):
    floored = floor_minute(ts)
    for delta_min in range(0, 5):
        probe = floored + timedelta(minutes=delta_min)
        bar = bars.get(probe)
        if bar is not None:
            return bar[3]
    return None


def recompute_forward_returns(bars, valid_from):
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
    eod = eod_ts(valid_from)
    if eod > valid_from:
        future_eod = spot_at(bars, eod)
        if future_eod is not None:
            out["forward_eod_pct"] = (future_eod - anchor) / anchor * 100.0
    return out


def recompute_mfe_mae(bars, valid_from, direction):
    """v3 fix (Bug A): strict upper boundary `k < window_end` to match writer
    behavior (writer's bars retain HH:MM:59 timestamps and the boundary bar at
    HH+1:00:59 satisfies `> window_end` and is broken-out of)."""
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
    # v3: strict less-than for upper bound
    sorted_keys = sorted(k for k in bars if floor_minute(valid_from) <= k < window_end)
    for k in sorted_keys:
        _, b_high, b_low, _ = bars[k]
        saw_any = True
        if b_high > max_high:
            max_high = b_high
            max_high_ts = k
        if b_low < min_low:
            min_low = b_low
            min_low_ts = k
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
        out["time_to_mfe_min"] = int((mfe_ts - floor_minute(valid_from)).total_seconds() // 60)
    return out


def recompute_dte(sb, instrument_id, valid_from):
    anchor_5m = floor_5m(valid_from)
    vendor_bts = vendor_bar_ts_label(anchor_5m)
    res = (
        sb.table("hist_atm_option_bars_5m")
          .select("dte")
          .eq("instrument_id", instrument_id)
          .eq("bar_ts", vendor_bts)
          .order("expiry_date", desc=False)
          .limit(1)
          .execute()
    )
    rows = res.data or []
    if not rows or rows[0].get("dte") is None:
        return None
    return int(rows[0]["dte"])


def _chain_premium_end_of_5m(sb, instrument_id, expiry_date_v, strike, option_type,
                              target_5m_start):
    """v3 fix (Bug C): query chain for LAST 1m bar within the 5m window starting
    at target_5m_start. Bar stored at HH:(MM+4):59 represents close of
    [HH:(MM+4):00, HH:(MM+5):00) = price at end of 5m window. Aligns with ATM
    table's pe_close/ce_close semantic (close of 5m bar)."""
    last_min_start = target_5m_start + timedelta(minutes=4)
    last_min_end = target_5m_start + timedelta(minutes=5)
    start_label = vendor_bar_ts_label(last_min_start)
    end_label = vendor_bar_ts_label(last_min_end)
    res = (
        sb.table("hist_option_bars_1m")
          .select("close")
          .eq("instrument_id", instrument_id)
          .eq("expiry_date", expiry_date_v)
          .eq("strike", strike)
          .eq("option_type", option_type)
          .gte("bar_ts", start_label)
          .lt("bar_ts", end_label)
          .limit(1)
          .execute()
    )
    rows = res.data or []
    if not rows:
        return None
    return float(rows[0]["close"])


def recompute_atm_pnl_from_chain(sb, instrument_id, valid_from, direction):
    if direction not in ("BULL", "BEAR"):
        return {}
    anchor_5m = floor_5m(valid_from)
    res = (
        sb.table("hist_atm_option_bars_5m")
          .select("atm_strike,expiry_date")
          .eq("instrument_id", instrument_id)
          .eq("bar_ts", vendor_bar_ts_label(anchor_5m))
          .order("expiry_date", desc=False)
          .limit(1)
          .execute()
    )
    rows = res.data or []
    if not rows:
        return {}
    strike = float(rows[0]["atm_strike"])
    expiry = rows[0]["expiry_date"]
    option_type = "CE" if direction == "BULL" else "PE"

    premium_t0 = _chain_premium_end_of_5m(sb, instrument_id, expiry, strike,
                                           option_type, anchor_5m)
    if premium_t0 is None or premium_t0 == 0:
        return {}

    out = {}
    for col, mins in [("atm_pnl_5m_pct", 5), ("atm_pnl_15m_pct", 15),
                       ("atm_pnl_30m_pct", 30), ("atm_pnl_60m_pct", 60)]:
        future_5m = anchor_5m + timedelta(minutes=mins)
        future_premium = _chain_premium_end_of_5m(sb, instrument_id, expiry, strike,
                                                   option_type, future_5m)
        if future_premium is None or future_premium == 0:
            continue
        out[col] = (future_premium - premium_t0) / premium_t0 * 100.0
    return out


def sample_outcomes(sb, n, symbol_filter, seed):
    random.seed(seed)
    pool_size = min(n * 10, 5000)
    q = (
        sb.table("ict_primitive_outcomes")
          .select("*,ict_primitives!inner(id,symbol,timeframe,primitive_type,direction,"
                  "source_bar_ts,valid_from,zone_low,zone_high,level)")
    )
    if symbol_filter and symbol_filter != "both":
        q = q.eq("ict_primitives.symbol", symbol_filter)
    res = q.limit(pool_size).execute()
    pool = res.data or []
    if symbol_filter and symbol_filter != "both":
        pool = [r for r in pool if r.get("ict_primitives", {}).get("symbol") == symbol_filter]
    if len(pool) < n:
        return pool
    return random.sample(pool, n)


def compare_value(col, stored, recomputed, kind, threshold):
    if stored is None and recomputed is None:
        return ("MISSING_BOTH", 0.0)
    if stored is None:
        return ("MISSING_STORED", 0.0)
    if recomputed is None:
        return ("MISSING_RECOMPUTED", 0.0)
    s, r = float(stored), float(recomputed)
    if kind == "absolute_bp":
        diff_pp = abs(s - r)
        return ("MATCH" if diff_pp <= threshold * 0.01 else "DISCREPANT", diff_pp)
    if kind == "relative":
        if abs(s) < 1e-9:
            diff = abs(s - r)
            return ("MATCH" if diff < 0.01 else "DISCREPANT", diff)
        rel_diff = abs(s - r) / abs(s)
        return ("MATCH" if rel_diff <= threshold else "DISCREPANT", rel_diff)
    if kind == "exact":
        return ("MATCH" if int(s) == int(r) else "DISCREPANT", abs(s - r))
    raise ValueError(kind)


def audit_primitive(sb, sample, spot_cache):
    prim = sample.get("ict_primitives", {})
    symbol = prim.get("symbol")
    instrument_id = INSTRUMENT_ID_BY_SYMBOL.get(symbol)
    if instrument_id is None:
        return {"_error": f"unknown symbol {symbol}"}
    valid_from = parse_ts(prim["valid_from"])
    direction = prim.get("direction", "NONE")

    bars = spot_cache.get_window(instrument_id, valid_from, window_minutes=150)
    rec_fwd = recompute_forward_returns(bars, valid_from)
    rec_mfe = recompute_mfe_mae(bars, valid_from, direction)
    rec_dte = recompute_dte(sb, instrument_id, valid_from)
    rec_atm = recompute_atm_pnl_from_chain(sb, instrument_id, valid_from, direction)

    out = {"primitive_id": prim.get("id"), "symbol": symbol, "direction": direction,
           "valid_from": valid_from.isoformat(), "columns": {}}
    for col in ["forward_5m_pct", "forward_15m_pct", "forward_30m_pct",
                "forward_1h_pct", "forward_120m_pct", "forward_eod_pct"]:
        out["columns"][col] = compare_value(col, sample.get(col), rec_fwd.get(col),
                                             "absolute_bp", FWD_THRESHOLD_BP)
    out["columns"]["mfe_pct"] = compare_value("mfe_pct", sample.get("mfe_pct"),
                                               rec_mfe.get("mfe_pct"),
                                               "absolute_bp", FWD_THRESHOLD_BP)
    out["columns"]["mae_pct"] = compare_value("mae_pct", sample.get("mae_pct"),
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


def print_report(results):
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
        print("\nWORST DISCREPANCY DETAIL (top 10):")
        worst_examples.sort(key=lambda x: -x[1])
        for col, disc, samp in worst_examples[:10]:
            print(f"  {col}: disc={disc:.4f}  pid={samp['primitive_id']}  "
                  f"symbol={samp['symbol']}  direction={samp['direction']}  "
                  f"valid_from={samp['valid_from']}")
    else:
        print("\nNo discrepancies found in any audited column.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--symbol", choices=["NIFTY", "SENSEX", "both"], default="both")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    print(f"[start] ENH-100 v3 falsification audit v5  n={args.n}  symbol={args.symbol}")
    sb = get_client()
    t0 = _time.time()
    samples = sample_outcomes(sb, args.n, args.symbol, args.seed)
    print(f"  sampled {len(samples)} primitives in {_time.time() - t0:.1f}s")

    spot_cache = SpotBarsCache(sb)
    results = []
    t1 = _time.time()
    for i, samp in enumerate(samples):
        try:
            r = audit_primitive(sb, samp, spot_cache)
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
