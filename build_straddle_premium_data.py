#!/usr/bin/env python3
"""
build_straddle_premium_data.py — Generates JSON powering the Market View dashboard.

Per-symbol, per-DTE-bucket (0-6 days), per-minute-of-day:
  - Today's curve (most recent full trading day)
  - Avg curve (mean across all matching DTE trading days in scope)
  - P25 / P75 curves (25th and 75th percentile across days)

Plus latest IV elevation status + three insight strings.

Reads:    hist_atm_option_bars_5m (CE/PE close per ATM strike per 5m bar)
          vol_analytics (current vs 30d-rolling IV for elevation badge)
Writes:   market_view_data.json (single file consumed by market_view.html)

Run:
    python build_straddle_premium_data.py [--out market_view_data.json] [--days 420]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, date, time, timezone, timedelta
from collections import defaultdict

from dotenv import load_dotenv  # type: ignore
from supabase import Client, create_client  # type: ignore


SPOT_INSTRUMENT_ID = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}
INSTRUMENT_TO_SYMBOL = {v: k for k, v in SPOT_INSTRUMENT_ID.items()}
IST_TZ_OFFSET = timedelta(hours=5, minutes=30)

_MICROSECOND_RE = re.compile(r"\.(\d+)([+-]\d{2}:\d{2}|Z)?$")


def _normalize_microseconds(ts_str: str) -> str:
    m = _MICROSECOND_RE.search(ts_str)
    if m is None: return ts_str
    frac, tz = m.group(1), (m.group(2) or "")
    if len(frac) == 6: return ts_str
    frac6 = frac.ljust(6, "0") if len(frac) < 6 else frac[:6]
    return _MICROSECOND_RE.sub(f".{frac6}{tz}", ts_str)


def _ts_from_str(ts_str: str) -> datetime:
    return datetime.fromisoformat(_normalize_microseconds(ts_str.replace("Z", "+00:00")))


def _load_supabase_client() -> Client:
    load_dotenv(override=False)
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY"))
    if not url or not key: raise RuntimeError("env vars required")
    return create_client(url, key)


def _paginated_fetch(query_builder, page_size: int = 1000) -> list[dict]:
    out, offset = [], 0
    while True:
        resp = query_builder.range(offset, offset + page_size - 1).execute()
        rows = resp.data or []
        if not rows: break
        out.extend(rows)
        if len(rows) < page_size: break
        offset += page_size
    return out


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals: return 0.0
    idx = pct * (len(sorted_vals) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = idx - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def _minute_of_day(ts: datetime) -> str:
    """IST clock time as HH:MM string (bar_ts is IST-as-UTC)."""
    return ts.strftime("%H:%M")


def build_curves(rows: list[dict]) -> dict:
    """Returns {symbol: {dte: {today, avg, p25, p75}}}."""
    # Group: (symbol, dte) -> {trade_date: {minute: straddle}}
    by_key: dict[tuple[str, int], dict[date, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))
    for r in rows:
        symbol = INSTRUMENT_TO_SYMBOL.get(r.get("instrument_id"))
        if symbol is None: continue
        try:
            bar_ts = _ts_from_str(r["bar_ts"])
            expiry = date.fromisoformat(str(r["expiry_date"]))
            ce, pe = r.get("ce_close"), r.get("pe_close")
            if ce is None or pe is None: continue
            straddle = float(ce) + float(pe)
        except (KeyError, ValueError, TypeError): continue
        trade_date = bar_ts.date()
        dte = (expiry - trade_date).days
        if dte < 0 or dte > 6: continue  # current-week only
        minute = _minute_of_day(bar_ts)
        # Only keep current-week expiry (smallest valid expiry per trade_date)
        existing = by_key[(symbol, dte)].get(trade_date, {})
        if minute not in existing or existing.get(minute, 0) > straddle:
            # Keep the smallest expiry-based straddle per (date, minute) = current-week dominant
            existing[minute] = straddle
        by_key[(symbol, dte)][trade_date] = existing

    out: dict = {}
    for (symbol, dte), by_date in by_key.items():
        if symbol not in out: out[symbol] = {"dte_curves": {}}

        # Find most recent trade_date with data → today
        dates_sorted = sorted(by_date.keys(), reverse=True)
        if not dates_sorted: continue
        today_date = dates_sorted[0]
        today_curve = by_date[today_date]

        # All historical dates → avg/p25/p75 by minute
        all_minutes = set()
        for d_data in by_date.values():
            all_minutes.update(d_data.keys())
        avg_curve, p25_curve, p75_curve = {}, {}, {}
        for minute in sorted(all_minutes):
            vals = [d_data[minute] for d_data in by_date.values() if minute in d_data]
            if not vals: continue
            s = sorted(vals)
            avg_curve[minute] = sum(s) / len(s)
            p25_curve[minute] = _percentile(s, 0.25)
            p75_curve[minute] = _percentile(s, 0.75)

        # Convert to ordered lists for chart
        def _to_list(d):
            return [{"time": m, "value": round(v, 2)} for m, v in sorted(d.items())]

        out[symbol]["dte_curves"][str(dte)] = {
            "today_date": today_date.isoformat(),
            "today": _to_list(today_curve),
            "avg": _to_list(avg_curve),
            "p25": _to_list(p25_curve),
            "p75": _to_list(p75_curve),
            "n_days_in_avg": len(by_date),
        }
    return out


def compute_iv_insight(sb: Client) -> dict:
    """Latest vol_analytics row vs 30d rolling avg per symbol."""
    out = {}
    for symbol in ["NIFTY", "SENSEX"]:
        resp = (sb.table("vol_analytics")
                .select("ts, implied_vol_atm, realized_vol_30, rr_ratio, rr_regime")
                .eq("symbol", symbol)
                .order("ts", desc=True)
                .limit(1).execute())
        rows = resp.data or []
        if not rows: continue
        latest = rows[0]
        latest_iv = latest.get("implied_vol_atm")
        if latest_iv is None: continue
        try: latest_iv_f = float(latest_iv)
        except (TypeError, ValueError): continue

        # 30d rolling avg
        ts_latest = _ts_from_str(latest["ts"])
        ts_30d_ago = ts_latest - timedelta(days=30)
        resp30 = (sb.table("vol_analytics")
                  .select("implied_vol_atm")
                  .eq("symbol", symbol)
                  .gte("ts", ts_30d_ago.isoformat())
                  .lte("ts", ts_latest.isoformat())
                  .execute())
        ivs = [float(r["implied_vol_atm"]) for r in (resp30.data or [])
               if r.get("implied_vol_atm") is not None]
        if not ivs: continue
        avg_iv = sum(ivs) / len(ivs)
        pct_above = (latest_iv_f / avg_iv - 1) * 100 if avg_iv > 0 else 0

        out[symbol] = {
            "latest_iv": latest_iv_f * 100,  # back to percentage points for display
            "avg_30d_iv": avg_iv * 100,
            "pct_above_avg": pct_above,
            "elevated": pct_above > 15,
            "rr_regime": latest.get("rr_regime"),
            "latest_ts": latest["ts"],
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="market_view_data.json")
    ap.add_argument("--days", type=int, default=420, help="Lookback days")
    args = ap.parse_args()

    sb = _load_supabase_client()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).date().isoformat()
    print(f"Fetching hist_atm_option_bars_5m from {cutoff}...")
    q = (sb.table("hist_atm_option_bars_5m")
         .select("instrument_id, bar_ts, expiry_date, ce_close, pe_close")
         .gte("bar_ts", cutoff))
    rows = _paginated_fetch(q)
    print(f"  → {len(rows)} bars")

    print("Computing curves...")
    curves = build_curves(rows)

    print("Computing IV insight...")
    iv_insights = compute_iv_insight(sb)

    # Merge
    for symbol in curves:
        if symbol in iv_insights:
            curves[symbol]["iv_insight"] = iv_insights[symbol]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbols": curves,
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    # Summary
    print(f"\nWritten: {args.out}")
    for sym, data in curves.items():
        dtes = sorted(data.get("dte_curves", {}).keys(), key=int)
        print(f"  {sym}: DTEs {dtes}", end="")
        if "iv_insight" in data:
            iv = data["iv_insight"]
            print(f"  IV {iv['latest_iv']:.1f}% ({iv['pct_above_avg']:+.1f}% vs 30d avg) regime={iv.get('rr_regime')}")
        else:
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
