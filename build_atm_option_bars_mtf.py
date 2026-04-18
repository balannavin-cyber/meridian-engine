#!/usr/bin/env python3
"""
build_atm_option_bars_mtf.py
==============================
Builds hist_atm_option_bars_5m and hist_atm_option_bars_15m.

For each 5m/15m bar:
  1. Get spot close from hist_spot_bars_5m
  2. Determine ATM strike (nearest 50 for NIFTY, nearest 100 for SENSEX)
  3. Find nearest weekly expiry
  4. Fetch ATM PE + CE 1m bars from hist_option_bars_1m for that date+strike
  5. Aggregate to 5m/15m OHLCV + greeks + IV OHLC + wick metrics
  6. Write to hist_atm_option_bars_5m and hist_atm_option_bars_15m

Runtime: ~3-6 hours (per-date queries on hist_option_bars_1m)
Run overnight.

Wick metric definitions:
  upper_wick_ratio = (high - max(open,close)) / (high - low)
  lower_wick_ratio = (min(open,close) - low) / (high - low)
  body_ratio       = abs(close - open) / (high - low)
  pe_reversal_wick = upper_wick_ratio >= 0.40 AND close < midpoint
                     (PE premium expanded then collapsed = spot reversal signal)
  ce_reversal_wick = upper_wick_ratio >= 0.40 AND close < midpoint
                     (CE premium expanded then collapsed = spot reversal down)
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from datetime import datetime, date, timedelta

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
PAGE_SIZE    = 1000

INSTRUMENTS = {
    "NIFTY":  {
        "id":       "9992f600-51b3-4009-b487-f878692a0bc5",
        "tick":     50,    # strike interval
        "exchange": "NSE",
    },
    "SENSEX": {
        "id":       "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
        "tick":     100,
        "exchange": "BSE",
    },
}

WICK_REVERSAL_MIN = 0.40   # wick must be >= 40% of range


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fetch_all(sb, table, select, filters=None, order=None):
    all_rows, offset = [], 0
    while True:
        q = sb.table(table).select(select)
        if filters:
            for f in filters:
                method, *args = f
                q = getattr(q, method)(*args)
        if order:
            q = q.order(order)
        q = q.range(offset, offset + PAGE_SIZE - 1)
        for attempt in range(3):
            try:
                rows = q.execute().data
                break
            except Exception as e:
                if attempt == 2:
                    log(f"  ERROR: {e}")
                    return all_rows
                time.sleep(2 ** attempt)
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def nearest_atm(spot, tick):
    """Round spot to nearest strike tick."""
    return round(round(spot / tick) * tick, 0)


def nearest_expiry(trade_date_str, expiry_dates):
    """Find nearest expiry >= trade_date."""
    td = date.fromisoformat(trade_date_str)
    future = [e for e in expiry_dates if e >= td]
    return min(future) if future else None


def get_bucket(bar_ts_str, interval_mins):
    """Return bar open time floored to interval.
    NOTE: option bars have seconds (09:15:59) — floor to minute first.
    """
    try:
        dt = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
        # Floor to minute first (handles 09:15:59 -> 09:15:00)
        dt = dt.replace(second=0, microsecond=0)
        mins = dt.hour * 60 + dt.minute
        bm   = (mins // interval_mins) * interval_mins
        return dt.replace(hour=bm//60, minute=bm%60).isoformat()
    except:
        return None


def wick_metrics(o, h, l, c):
    """Compute wick ratios and reversal flag."""
    rng = h - l
    if rng < 0.01:
        return {
            "upper_wick_ratio": 0,
            "lower_wick_ratio": 0,
            "body_ratio":       0,
            "reversal_wick":    False,
        }
    upper = (h - max(o, c)) / rng
    lower = (min(o, c) - l)  / rng
    body  = abs(c - o) / rng
    # Reversal wick: long upper wick + close below midpoint
    midpoint = (h + l) / 2
    reversal = upper >= WICK_REVERSAL_MIN and c < midpoint
    return {
        "upper_wick_ratio": round(upper, 4),
        "lower_wick_ratio": round(lower, 4),
        "body_ratio":       round(body, 4),
        "reversal_wick":    reversal,
    }


def aggregate_option_bars(bars_1m, interval_mins):
    """
    Aggregate 1m option bars into interval_mins buckets.
    Returns dict: bucket_ts -> aggregated bar
    """
    buckets = defaultdict(list)
    for bar in bars_1m:
        # Floor bar_ts to minute before bucketing (option bars have seconds)
        bar_ts_floored = bar["bar_ts"]
        try:
            dt = datetime.fromisoformat(bar["bar_ts"].replace("Z", "+00:00"))
            bar_ts_floored = dt.replace(second=0, microsecond=0).isoformat()
        except:
            pass
        bucket = get_bucket(bar_ts_floored, interval_mins)
        if bucket:
            buckets[bucket].append(bar)

    result = {}
    for bucket_ts, group in sorted(buckets.items()):
        group = sorted(group, key=lambda b: b["bar_ts"])
        first, last = group[0], group[-1]

        o = float(first["open"])   if first.get("open")  else None
        h = max((float(b["high"]) for b in group if b.get("high")), default=None)
        l = min((float(b["low"])  for b in group if b.get("low")),  default=None)
        c = float(last["close"])   if last.get("close")  else None

        vol = sum(float(b["volume"]) for b in group
                  if b.get("volume")) or None
        oi  = float(last["oi"]) if last.get("oi") else None

        # IV OHLC
        ivs  = [float(b["iv"]) for b in group if b.get("iv")]
        iv_o = float(first["iv"])  if first.get("iv") else None
        iv_h = max(ivs) if ivs else None
        iv_l = min(ivs) if ivs else None
        iv_c = float(last["iv"])   if last.get("iv")  else None
        iv_exp = (iv_h - iv_c) if (iv_h and iv_c) else None

        # Greeks from last bar
        delta = float(last["delta"]) if last.get("delta") else None
        gamma = float(last["gamma"]) if last.get("gamma") else None
        theta = float(last["theta"]) if last.get("theta") else None
        vega  = float(last["vega"])  if last.get("vega")  else None

        # Wick metrics
        wm = {}
        if o and h and l and c:
            wm = wick_metrics(o, h, l, c)

        result[bucket_ts] = {
            "open": o, "high": h, "low": l, "close": c,
            "volume": vol, "oi": oi,
            "iv_open": iv_o, "iv_high": iv_h, "iv_low": iv_l,
            "iv_close": iv_c, "iv_expansion": iv_exp,
            "delta": delta, "gamma": gamma, "theta": theta, "vega": vega,
            **wm,
        }

    return result


def upsert_batch(sb, table, rows, conflict_cols):
    if not rows:
        return 0
    for attempt in range(3):
        try:
            sb.table(table).upsert(
                rows, on_conflict=conflict_cols
            ).execute()
            return len(rows)
        except Exception as e:
            if attempt == 2:
                log(f"  UPSERT ERROR ({table}): {e}")
                return 0
            time.sleep(2 ** attempt)
    return 0


def build_for_symbol(sb, symbol, inst_info, expiry_dates):
    inst_id = inst_info["id"]
    tick    = inst_info["tick"]

    log(f"\n{'='*20} {symbol} {'='*20}")

    # Load 5m spot bars (already built)
    log(f"  Loading hist_spot_bars_5m...")
    spot_5m = fetch_all(
        sb, "hist_spot_bars_5m",
        "trade_date,bar_ts,close",
        filters=[("eq","instrument_id",inst_id)],
        order="bar_ts"
    )
    log(f"  {len(spot_5m):,} 5m spot bars")

    # Get unique trade dates
    dates = sorted(set(r["trade_date"] for r in spot_5m))
    log(f"  Processing {len(dates)} trade dates...")

    # Index spot by (trade_date, bar_ts)
    spot_idx = {(r["trade_date"], r["bar_ts"]): float(r["close"])
                for r in spot_5m}

    pending_5m  = []
    pending_15m = []
    written_5m  = written_15m = 0

    for di, trade_date in enumerate(dates):
        # Get expiry for this date directly from option bars
        exp_rows = sb.table("hist_option_bars_1m").select("expiry_date").eq(
            "instrument_id", inst_id).eq("trade_date", trade_date).limit(1).execute().data
        if not exp_rows or not exp_rows[0].get("expiry_date"):
            continue
        exp = date.fromisoformat(exp_rows[0]["expiry_date"])
        dte = (exp - date.fromisoformat(trade_date)).days

        # Get ATM strikes for this date (use first 5m bar spot)
        day_spots = [(r["bar_ts"], float(r["close"]))
                     for r in spot_5m if r["trade_date"] == trade_date]
        if not day_spots:
            continue

        # Unique ATM strikes for today (may shift during day)
        atm_strikes = set()
        for _, spot in day_spots:
            atm_strikes.add(nearest_atm(spot, tick))

        # Fetch option bars for this date, all ATM strikes
        for atm_strike in atm_strikes:
            # Fetch PE + CE 1m bars for this strike
            for opt_type in ["PE", "CE"]:
                pass  # fetched below together

        # Fetch all option bars for this date, strikes within ATM ± 2 ticks
        # Use first bar's spot to get center
        first_spot = day_spots[0][1]
        center_atm = nearest_atm(first_spot, tick)
        lo_strike  = center_atm - tick * 2
        hi_strike  = center_atm + tick * 2

        opt_bars_raw = fetch_all(
            sb, "hist_option_bars_1m",
            "bar_ts,strike,option_type,open,high,low,close,"
            "volume,oi,iv,delta,gamma,theta,vega",
            filters=[
                ("eq",  "instrument_id", inst_id),
                ("eq",  "trade_date",    trade_date),
                ("gte", "strike",        str(lo_strike)),
                ("lte", "strike",        str(hi_strike)),
                ("eq",  "is_pre_market", False),
            ],
            order="bar_ts"
        )

        if not opt_bars_raw:
            continue

        # Index by (strike, option_type) → list of 1m bars
        opt_by_strike = defaultdict(list)
        for r in opt_bars_raw:
            key = (float(r["strike"]), r["option_type"])
            opt_by_strike[key].append(r)

        # For each 5m spot bar on this date, build the ATM option bar
        day_5m_spots = sorted(
            [(r["bar_ts"], float(r["close"]))
             for r in spot_5m if r["trade_date"] == trade_date],
            key=lambda x: x[0]
        )

        for bar_ts, spot_close in day_5m_spots:
            atm = nearest_atm(spot_close, tick)

            # Get 5m aggregated PE bar
            pe_1m = opt_by_strike.get((atm, "PE"), [])
            ce_1m = opt_by_strike.get((atm, "CE"), [])

            if not pe_1m and not ce_1m:
                continue

            # Filter to this 5m bucket
            bucket_ts = bar_ts
            bucket_dt = datetime.fromisoformat(bucket_ts.replace("Z", "+00:00"))
            next_bucket = bucket_dt + timedelta(minutes=5)

            def in_bucket(b, interval=5):
                try:
                    bdt = datetime.fromisoformat(b["bar_ts"].replace("Z", "+00:00"))
                    # Floor to minute (option bars have seconds)
                    bdt = bdt.replace(second=0, microsecond=0)
                    return bucket_dt <= bdt < next_bucket
                except:
                    return False

            pe_bucket = [b for b in pe_1m if in_bucket(b)]
            ce_bucket = [b for b in ce_1m if in_bucket(b)]

            if not pe_bucket and not ce_bucket:
                continue

            pe_agg = aggregate_option_bars(pe_bucket, 5).get(bucket_ts, {}) if pe_bucket else {}
            ce_agg = aggregate_option_bars(ce_bucket, 5).get(bucket_ts, {}) if ce_bucket else {}

            # Also need spot OHLC for this 5m bar
            # (simplified: use spot_close, we don't have spot OHLC per 5m bar in memory)
            # Will compute from hist_spot_bars_5m join — for now use close only

            row_5m = {
                "instrument_id":    inst_id,
                "symbol":           symbol,
                "trade_date":       trade_date,
                "bar_ts":           bar_ts,
                "spot_close":       spot_close,
                "atm_strike":       atm,
                "expiry_date":      str(exp),
                "dte":              dte,

                # PE
                "pe_open":              pe_agg.get("open"),
                "pe_high":              pe_agg.get("high"),
                "pe_low":               pe_agg.get("low"),
                "pe_close":             pe_agg.get("close"),
                "pe_volume":            pe_agg.get("volume"),
                "pe_oi":                pe_agg.get("oi"),
                "pe_iv_open":           pe_agg.get("iv_open"),
                "pe_iv_high":           pe_agg.get("iv_high"),
                "pe_iv_low":            pe_agg.get("iv_low"),
                "pe_iv_close":          pe_agg.get("iv_close"),
                "pe_iv_expansion":      pe_agg.get("iv_expansion"),
                "pe_delta":             pe_agg.get("delta"),
                "pe_gamma":             pe_agg.get("gamma"),
                "pe_theta":             pe_agg.get("theta"),
                "pe_vega":              pe_agg.get("vega"),
                "pe_upper_wick_ratio":  pe_agg.get("upper_wick_ratio"),
                "pe_lower_wick_ratio":  pe_agg.get("lower_wick_ratio"),
                "pe_body_ratio":        pe_agg.get("body_ratio"),
                "pe_reversal_wick":     pe_agg.get("reversal_wick"),

                # CE
                "ce_open":              ce_agg.get("open"),
                "ce_high":              ce_agg.get("high"),
                "ce_low":               ce_agg.get("low"),
                "ce_close":             ce_agg.get("close"),
                "ce_volume":            ce_agg.get("volume"),
                "ce_oi":                ce_agg.get("oi"),
                "ce_iv_open":           ce_agg.get("iv_open"),
                "ce_iv_high":           ce_agg.get("iv_high"),
                "ce_iv_low":            ce_agg.get("iv_low"),
                "ce_iv_close":          ce_agg.get("iv_close"),
                "ce_iv_expansion":      ce_agg.get("iv_expansion"),
                "ce_delta":             ce_agg.get("delta"),
                "ce_gamma":             ce_agg.get("gamma"),
                "ce_theta":             ce_agg.get("theta"),
                "ce_vega":              ce_agg.get("vega"),
                "ce_upper_wick_ratio":  ce_agg.get("upper_wick_ratio"),
                "ce_lower_wick_ratio":  ce_agg.get("lower_wick_ratio"),
                "ce_body_ratio":        ce_agg.get("body_ratio"),
                "ce_reversal_wick":     ce_agg.get("reversal_wick"),

                # Combined
                "pcr_5m": (
                    pe_agg.get("volume") / ce_agg.get("volume")
                    if pe_agg.get("volume") and ce_agg.get("volume")
                    else None
                ),
                "pcr_oi_5m": (
                    pe_agg.get("oi") / ce_agg.get("oi")
                    if pe_agg.get("oi") and ce_agg.get("oi")
                    else None
                ),
            }
            pending_5m.append(row_5m)

            # Also build 15m bar (aggregate 3 x 5m bars)
            # Handled separately below

        # Flush 5m
        if len(pending_5m) >= 300:
            written_5m += upsert_batch(
                sb, "hist_atm_option_bars_5m",
                pending_5m,
                "instrument_id,bar_ts,expiry_date"
            )
            pending_5m = []

        if (di + 1) % 20 == 0:
            log(f"  [{di+1}/{len(dates)}] {trade_date} | "
                f"5m written: {written_5m}")

    # Final flush
    if pending_5m:
        written_5m += upsert_batch(
            sb, "hist_atm_option_bars_5m",
            pending_5m,
            "instrument_id,bar_ts,expiry_date"
        )

    log(f"  {symbol} complete: {written_5m} 5m option bars written")

    # ── Build 15m from the 5m data ────────────────────────────────────────
    log(f"\n  Building 15m bars from 5m data...")
    rows_5m_db = fetch_all(
        sb, "hist_atm_option_bars_5m",
        "trade_date,bar_ts,atm_strike,expiry_date,dte,spot_close,"
        "pe_open,pe_high,pe_low,pe_close,pe_volume,pe_oi,"
        "pe_iv_open,pe_iv_high,pe_iv_low,pe_iv_close,"
        "pe_delta,pe_gamma,pe_theta,pe_vega,"
        "ce_open,ce_high,ce_low,ce_close,ce_volume,ce_oi,"
        "ce_iv_open,ce_iv_high,ce_iv_low,ce_iv_close,"
        "ce_delta,ce_gamma,ce_theta,ce_vega",
        filters=[("eq","instrument_id",inst_id)],
        order="bar_ts"
    )

    # Group into 15m buckets
    buckets_15m = defaultdict(list)
    for r in rows_5m_db:
        bucket = get_bucket(r["bar_ts"], 15)
        if bucket:
            buckets_15m[(r["trade_date"], r["expiry_date"], bucket)].append(r)

    pending_15m = []
    for (td, exp_str, bucket_ts), group in sorted(buckets_15m.items()):
        group = sorted(group, key=lambda r: r["bar_ts"])
        first, last = group[0], group[-1]

        def agg_ohlc(key_o, key_h, key_l, key_c):
            o = first.get(key_o)
            h = max((float(r[key_h]) for r in group if r.get(key_h)), default=None)
            l = min((float(r[key_l]) for r in group if r.get(key_l)), default=None)
            c = last.get(key_c)
            return (float(o) if o else None, h, l,
                    float(c) if c else None)

        pe_o, pe_h, pe_l, pe_c = agg_ohlc("pe_open","pe_high","pe_low","pe_close")
        ce_o, ce_h, ce_l, ce_c = agg_ohlc("ce_open","ce_high","ce_low","ce_close")

        pe_wm = wick_metrics(pe_o, pe_h, pe_l, pe_c) if all([pe_o,pe_h,pe_l,pe_c]) else {}
        ce_wm = wick_metrics(ce_o, ce_h, ce_l, ce_c) if all([ce_o,ce_h,ce_l,ce_c]) else {}

        iv_highs_pe = [float(r["pe_iv_high"]) for r in group if r.get("pe_iv_high")]
        iv_lows_pe  = [float(r["pe_iv_low"])  for r in group if r.get("pe_iv_low")]
        iv_highs_ce = [float(r["ce_iv_high"]) for r in group if r.get("ce_iv_high")]
        iv_lows_ce  = [float(r["ce_iv_low"])  for r in group if r.get("ce_iv_low")]

        pe_iv_h = max(iv_highs_pe) if iv_highs_pe else None
        pe_iv_l = min(iv_lows_pe)  if iv_lows_pe  else None
        ce_iv_h = max(iv_highs_ce) if iv_highs_ce else None
        ce_iv_l = min(iv_lows_ce)  if iv_lows_ce  else None

        pe_iv_c = float(last["pe_iv_close"]) if last.get("pe_iv_close") else None
        ce_iv_c = float(last["ce_iv_close"]) if last.get("ce_iv_close") else None

        pe_vol = sum(float(r["pe_volume"]) for r in group if r.get("pe_volume")) or None
        ce_vol = sum(float(r["ce_volume"]) for r in group if r.get("ce_volume")) or None

        pending_15m.append({
            "instrument_id":    inst_id,
            "symbol":           symbol,
            "trade_date":       td,
            "bar_ts":           bucket_ts,
            "spot_close":       float(last["spot_close"]) if last.get("spot_close") else None,
            "atm_strike":       float(last["atm_strike"]),
            "expiry_date":      exp_str,
            "dte":              int(last["dte"]) if last.get("dte") else None,

            "pe_open": pe_o, "pe_high": pe_h, "pe_low": pe_l, "pe_close": pe_c,
            "pe_volume": pe_vol,
            "pe_oi": float(last["pe_oi"]) if last.get("pe_oi") else None,
            "pe_iv_open":  float(first["pe_iv_open"]) if first.get("pe_iv_open") else None,
            "pe_iv_high":  pe_iv_h, "pe_iv_low": pe_iv_l, "pe_iv_close": pe_iv_c,
            "pe_iv_expansion": (pe_iv_h - pe_iv_c) if pe_iv_h and pe_iv_c else None,
            "pe_delta": float(last["pe_delta"]) if last.get("pe_delta") else None,
            "pe_gamma": float(last["pe_gamma"]) if last.get("pe_gamma") else None,
            "pe_theta": float(last["pe_theta"]) if last.get("pe_theta") else None,
            "pe_vega":  float(last["pe_vega"])  if last.get("pe_vega")  else None,
            "pe_upper_wick_ratio": pe_wm.get("upper_wick_ratio"),
            "pe_lower_wick_ratio": pe_wm.get("lower_wick_ratio"),
            "pe_body_ratio":       pe_wm.get("body_ratio"),
            "pe_reversal_wick":    pe_wm.get("reversal_wick"),

            "ce_open": ce_o, "ce_high": ce_h, "ce_low": ce_l, "ce_close": ce_c,
            "ce_volume": ce_vol,
            "ce_oi": float(last["ce_oi"]) if last.get("ce_oi") else None,
            "ce_iv_open":  float(first["ce_iv_open"]) if first.get("ce_iv_open") else None,
            "ce_iv_high":  ce_iv_h, "ce_iv_low": ce_iv_l, "ce_iv_close": ce_iv_c,
            "ce_iv_expansion": (ce_iv_h - ce_iv_c) if ce_iv_h and ce_iv_c else None,
            "ce_delta": float(last["ce_delta"]) if last.get("ce_delta") else None,
            "ce_gamma": float(last["ce_gamma"]) if last.get("ce_gamma") else None,
            "ce_theta": float(last["ce_theta"]) if last.get("ce_theta") else None,
            "ce_vega":  float(last["ce_vega"])  if last.get("ce_vega")  else None,
            "ce_upper_wick_ratio": ce_wm.get("upper_wick_ratio"),
            "ce_lower_wick_ratio": ce_wm.get("lower_wick_ratio"),
            "ce_body_ratio":       ce_wm.get("body_ratio"),
            "ce_reversal_wick":    ce_wm.get("reversal_wick"),

            "pcr_15m":    pe_vol / ce_vol if pe_vol and ce_vol else None,
            "pcr_oi_15m": None,
        })

    written_15m = 0
    for i in range(0, len(pending_15m), 300):
        written_15m += upsert_batch(
            sb, "hist_atm_option_bars_15m",
            pending_15m[i:i+300],
            "instrument_id,bar_ts,expiry_date"
        )
    log(f"  {symbol}: {written_15m} 15m option bars written")

    return written_5m, written_15m


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("build_atm_option_bars_mtf.py — 5m + 15m ATM option bars")
    log("=" * 65)
    log("Runtime: 3-6 hours. Run overnight.")
    log("Prerequisite: run build_spot_bars_mtf.py first")

    # Expiry dates loaded per-date inside build_for_symbol
    log("\nExpiry dates will be loaded per trade date.")

    total_5m = total_15m = 0
    for symbol, inst_info in INSTRUMENTS.items():
        w5, w15 = build_for_symbol(sb, symbol, inst_info, [])
        total_5m  += w5
        total_15m += w15

    # Verify
    log("\n" + "=" * 65)
    log("Verification")
    log("=" * 65)
    for table in ["hist_atm_option_bars_5m", "hist_atm_option_bars_15m"]:
        r = sb.table(table).select("*", count="exact").limit(1).execute()
        log(f"  {table}: {r.count} rows")

    log(f"\nTotal: {total_5m} 5m rows | {total_15m} 15m rows")
    log("\nAll MTF option bars complete.")
    log("Next: rebuild hist_pattern_signals on 5m bars")
    log("Then: rerun experiments 19, 20, 23c, 25, 26")


if __name__ == "__main__":
    main()
