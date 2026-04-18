#!/usr/bin/env python3
"""
build_hist_pattern_signals_5m.py
==================================
Rebuilds hist_pattern_signals using 5m spot bars for pattern detection.

Key improvements over v1 (1m bars):
  - Zone entry detection on 5m bars — less noise, cleaner signals
  - Sweep detection on 5m bars — proper candle structure
  - Wick quality on 5m bars — meaningful reversal signals
  - Regime context still from hist_market_state (1m) — join by nearest bar
  - Option P&L from hist_atm_option_bars_5m — real premium outcome

Clears existing hist_pattern_signals rows (source=backfill) before writing.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, Counter
from datetime import datetime, timedelta

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
PAGE_SIZE    = 1000

INSTRUMENTS = {
    "NIFTY":  "9992f600-51b3-4009-b487-f878692a0bc5",
    "SENSEX": "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
}

APPROACH_PCT     = 0.005   # 0.5% — spot within this of zone
SWEEP_MIN_PCT    = 0.0005  # 0.05% — minimum sweep on 5m bar
MAX_BARS_RETURN  = 3       # 5m bars = 15 min max to return
WICK_RATIO_MIN   = 0.40    # lower wick >= 40% of bar range

PATTERN_DIRECTION = {
    "BEAR_OB":  "BUY_PE",
    "BEAR_FVG": "BUY_PE",
    "BULL_OB":  "BUY_CE",
    "BULL_FVG": "BUY_CE",
}


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
                    log(f"  ERROR fetching {table}: {e}")
                    return all_rows
                time.sleep(2 ** attempt)
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return all_rows


def get_mins(bar_ts_str):
    """bar_ts stored as IST with +00:00 label — use directly."""
    try:
        dt = datetime.fromisoformat(bar_ts_str.replace("Z", "+00:00"))
        return dt.hour * 60 + dt.minute
    except:
        return 0


def get_session(bar_ts_str):
    mins = get_mins(bar_ts_str)
    if mins < 9*60+15:       return "PRE"
    elif mins <= 10*60+30:   return "MORNING"
    elif mins <= 13*60:      return "MIDDAY"
    elif mins <= 14*60+30:   return "AFTERNOON"
    else:                    return "PRECLOSE"


def is_morning(bar_ts_str):
    m = get_mins(bar_ts_str)
    return (9*60+15) <= m <= (10*60+30)


def infer_tier(pattern_type, zone_timeframe):
    if pattern_type in ("BEAR_OB", "BULL_OB"):
        return "TIER1" if zone_timeframe == "W" else "TIER2"
    elif pattern_type in ("BEAR_FVG", "BULL_FVG"):
        return "TIER2" if zone_timeframe == "W" else "TIER3"
    return "TIER2"


def wick_quality_5m(bar, direction="bull"):
    """Score wick quality on 5m bar."""
    try:
        h = float(bar["high"])
        l = float(bar["low"])
        o = float(bar["open"])
        c = float(bar["close"])
        rng = h - l
        if rng < 0.01:
            return False, 0, 0
        if direction == "bull":
            lower_wick = min(o, c) - l
            wick_ratio = lower_wick / rng
            close_pos  = (c - l) / rng
            quality    = wick_ratio >= WICK_RATIO_MIN and close_pos >= 0.6 and c > o
        else:
            upper_wick = h - max(o, c)
            wick_ratio = upper_wick / rng
            close_pos  = (h - c) / rng
            quality    = wick_ratio >= WICK_RATIO_MIN and close_pos >= 0.6 and c < o
        return quality, round(wick_ratio, 3), round(close_pos, 3)
    except:
        return False, 0, 0


def upsert_batch(sb, rows):
    if not rows:
        return 0
    for attempt in range(3):
        try:
            sb.table("hist_pattern_signals").upsert(
                rows,
                on_conflict="trade_date,symbol,bar_ts,pattern_type,zone_high,zone_low"
            ).execute()
            return len(rows)
        except Exception as e:
            if attempt == 2:
                log(f"  UPSERT ERROR: {e}")
                return 0
            time.sleep(2 ** attempt)
    return 0


def main():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)

    log("=" * 65)
    log("build_hist_pattern_signals_5m.py — 5m bar pattern detection")
    log("=" * 65)

    # ── Step 1: Clear existing backfill rows ─────────────────────────────
    log("\nStep 1: Clearing existing backfill rows...")
    try:
        sb.table("hist_pattern_signals").delete().eq(
            "source", "backfill").execute()
        log("  Cleared")
    except Exception as e:
        log(f"  WARNING: Could not clear: {e}")

    # ── Step 2: Load ICT zones ───────────────────────────────────────────
    log("\nStep 2: Loading ICT zones...")
    raw_zones = fetch_all(
        sb, "hist_ict_htf_zones",
        "as_of_date,symbol,pattern_type,zone_high,zone_low,timeframe",
        order="as_of_date"
    )
    log(f"  {len(raw_zones)} zone rows")

    zones_by_date  = defaultdict(list)
    pdlevels       = defaultdict(dict)

    for z in raw_zones:
        key = (z["as_of_date"], z["symbol"])
        pt  = z["pattern_type"]
        tf  = z["timeframe"]
        if pt in ("BEAR_OB","BULL_OB","BEAR_FVG","BULL_FVG"):
            zones_by_date[key].append({
                "high": float(z["zone_high"]),
                "low":  float(z["zone_low"]),
                "pattern": pt, "timeframe": tf,
            })
        elif pt == "PDL" and tf == "D":
            pdlevels[key]["pdl"] = float(z["zone_low"])
        elif pt == "PDH" and tf == "D":
            pdlevels[key]["pdh"] = float(z["zone_high"])

    # ── Step 3: Load market state (regime context) ───────────────────────
    log("\nStep 3: Loading hist_market_state for regime context...")
    mkt_rows = fetch_all(
        sb, "hist_market_state",
        "bar_ts,trade_date,symbol,spot,gamma_regime,breadth_regime,"
        "iv_regime,ret_session,ret_30m",
        order="bar_ts"
    )
    log(f"  {len(mkt_rows)} rows")

    # Index by (date, symbol, 5m_bucket_mins) for fast lookup
    mkt_by_5m = defaultdict(list)
    for r in mkt_rows:
        mins   = get_mins(r["bar_ts"])
        bucket = (mins // 5) * 5
        mkt_by_5m[(r["trade_date"], r["symbol"], bucket)].append(r)

    def get_regime(trade_date, symbol, bar_ts):
        """Get regime context for a 5m bar."""
        mins   = get_mins(bar_ts)
        bucket = (mins // 5) * 5
        rows   = mkt_by_5m.get((trade_date, symbol, bucket), [])
        if rows:
            return rows[-1]  # last 1m bar in the bucket
        # Try adjacent buckets
        for db in [-5, 5, -10, 10]:
            rows = mkt_by_5m.get((trade_date, symbol, bucket+db), [])
            if rows:
                return rows[-1]
        return {}

    # ── Step 4: Load ATM option bars for premium outcome ─────────────────
    log("\nStep 4: Loading ATM option bars for premium outcome...")
    atm_rows = fetch_all(
        sb, "hist_atm_option_bars_5m",
        "trade_date,bar_ts,symbol,atm_strike,pe_close,ce_close,"
        "pe_reversal_wick,ce_reversal_wick,pe_upper_wick_ratio,ce_upper_wick_ratio",
        order="bar_ts"
    )
    log(f"  {len(atm_rows)} ATM option bar rows")

    # Index: (date, symbol, bar_ts) -> row
    atm_idx = {}
    for r in atm_rows:
        atm_idx[(r["trade_date"], r["symbol"], r["bar_ts"])] = r

    def get_atm_at(trade_date, symbol, bar_ts):
        return atm_idx.get((trade_date, symbol, bar_ts), {})

    def get_atm_t30(trade_date, symbol, bar_ts):
        """Get ATM bar ~30 min after signal."""
        try:
            dt = datetime.fromisoformat(bar_ts.replace("Z", "+00:00"))
            t30 = (dt + timedelta(minutes=30)).replace(second=0).isoformat()
            return atm_idx.get((trade_date, symbol, t30), {})
        except:
            return {}

    # ── Step 5: Load 5m spot bars ────────────────────────────────────────
    log("\nStep 5: Loading 5m spot bars...")
    spot_by = defaultdict(list)
    for symbol, inst_id in INSTRUMENTS.items():
        rows = fetch_all(
            sb, "hist_spot_bars_5m",
            "trade_date,bar_ts,open,high,low,close",
            filters=[("eq","instrument_id",inst_id)],
            order="bar_ts"
        )
        for r in rows:
            spot_by[(r["trade_date"], symbol)].append(r)
        log(f"  {symbol}: {len(rows)} 5m bars")

    # ── Step 6: Detect signals on 5m bars ────────────────────────────────
    log("\nStep 6: Detecting signals on 5m bars...")

    pending = []
    seen    = set()
    total   = sweeps = written = 0

    for (trade_date, symbol), day_bars in sorted(spot_by.items()):
        day_bars  = sorted(day_bars, key=lambda b: b["bar_ts"])
        morning   = [b for b in day_bars if is_morning(b["bar_ts"])]
        zones     = zones_by_date.get((trade_date, symbol), [])
        pdl       = pdlevels.get((trade_date, symbol), {}).get("pdl")
        pdh       = pdlevels.get((trade_date, symbol), {}).get("pdh")

        # ── ICT zone signals ─────────────────────────────────────────────
        for bar in day_bars:
            bar_ts  = bar["bar_ts"]
            close   = float(bar["close"])
            session = get_session(bar_ts)

            for z in zones:
                pattern   = z["pattern"]
                direction = PATTERN_DIRECTION[pattern]
                zh, zl    = z["high"], z["low"]

                in_zone   = zl <= close <= zh
                near_bear = (pattern in ("BEAR_OB","BEAR_FVG") and
                             0 < (zl - close) / close <= APPROACH_PCT)
                near_bull = (pattern in ("BULL_OB","BULL_FVG") and
                             0 < (close - zh) / close <= APPROACH_PCT)

                if not (in_zone or near_bear or near_bull):
                    continue

                key = (trade_date, symbol, round(zh,1), round(zl,1), session)
                if key in seen:
                    continue
                seen.add(key)

                # Regime context
                mkt = get_regime(trade_date, symbol, bar_ts)
                ret_30m = float(mkt["ret_30m"]) if mkt.get("ret_30m") else None

                # Win on spot
                win_30m = None
                if ret_30m is not None:
                    win_30m = ret_30m < 0 if direction == "BUY_PE" else ret_30m > 0

                # ATM option premium outcome
                atm_now = get_atm_at(trade_date, symbol, bar_ts)
                atm_t30 = get_atm_t30(trade_date, symbol, bar_ts)

                pe_ret_30m = ce_ret_30m = win_option_30m = None
                if atm_now.get("pe_close") and atm_t30.get("pe_close"):
                    pe_now = float(atm_now["pe_close"])
                    pe_t30 = float(atm_t30["pe_close"])
                    if pe_now > 0:
                        pe_ret_30m = (pe_t30 - pe_now) / pe_now * 100
                if atm_now.get("ce_close") and atm_t30.get("ce_close"):
                    ce_now = float(atm_now["ce_close"])
                    ce_t30 = float(atm_t30["ce_close"])
                    if ce_now > 0:
                        ce_ret_30m = (ce_t30 - ce_now) / ce_now * 100

                if direction == "BUY_PE" and pe_ret_30m is not None:
                    win_option_30m = pe_ret_30m > 0
                elif direction == "BUY_CE" and ce_ret_30m is not None:
                    win_option_30m = ce_ret_30m > 0

                # Wick quality on this 5m bar
                wq, wr, cp = wick_quality_5m(
                    bar, "bull" if direction == "BUY_CE" else "bear")

                pending.append({
                    "trade_date":      trade_date,
                    "bar_ts":          bar_ts,
                    "symbol":          symbol,
                    "pattern_type":    pattern,
                    "tier":            infer_tier(pattern, z["timeframe"]),
                    "direction":       direction,
                    "session":         session,
                    "zone_high":       zh,
                    "zone_low":        zl,
                    "zone_timeframe":  z["timeframe"],
                    "spot_at_signal":  close,
                    "dte":             None,
                    "gamma_regime":    mkt.get("gamma_regime","UNKNOWN"),
                    "breadth_regime":  mkt.get("breadth_regime","UNKNOWN"),
                    "iv_regime":       mkt.get("iv_regime","UNKNOWN"),
                    "pcr_regime":      None,
                    "flow_regime":     None,
                    "skew_regime":     None,
                    "ret_session":     float(mkt["ret_session"]) if mkt.get("ret_session") else None,
                    "vix_at_signal":   None,
                    "ret_30m":         ret_30m,
                    "ret_60m":         None,
                    "win_30m":         win_30m,
                    "win_60m":         None,
                    "source":          "backfill_5m",
                })
                total += 1

        # ── Sweep reversals on 5m morning bars ───────────────────────────
        swept_pdl = swept_pdh = False

        for i, bar in enumerate(morning):
            if i == 0:
                continue
            bar_ts = bar["bar_ts"]
            close  = float(bar["close"])
            low    = float(bar["low"])
            high   = float(bar["high"])
            prev   = morning[i-1]
            prev_c = float(prev["close"])

            mkt     = get_regime(trade_date, symbol, bar_ts)
            ret_30m = float(mkt["ret_30m"]) if mkt.get("ret_30m") else None

            # Bull sweep: prev bar closes below PDL, this bar closes above
            if (pdl and not swept_pdl and
                    prev_c < pdl * (1 - SWEEP_MIN_PCT) and close > pdl):
                swept_pdl = True
                sk = (trade_date, symbol, "SWEEP_BULL")
                if sk not in seen:
                    seen.add(sk)

                    # Wick quality on signal bar
                    wq, wr_ratio, cp = wick_quality_5m(bar, "bull")
                    win_30m = ret_30m > 0 if ret_30m is not None else None

                    # Option outcome
                    atm_now = get_atm_at(trade_date, symbol, bar_ts)
                    atm_t30 = get_atm_t30(trade_date, symbol, bar_ts)
                    ce_ret = win_opt = None
                    if atm_now.get("ce_close") and atm_t30.get("ce_close"):
                        cn = float(atm_now["ce_close"])
                        ct = float(atm_t30["ce_close"])
                        if cn > 0:
                            ce_ret = (ct - cn) / cn * 100
                            win_opt = ce_ret > 0

                    pending.append({
                        "trade_date":      trade_date,
                        "bar_ts":          bar_ts,
                        "symbol":          symbol,
                        "pattern_type":    "SWEEP_REVERSAL",
                        "tier":            "TIER1",
                        "direction":       "BUY_CE",
                        "session":         "MORNING",
                        "zone_high":       pdl + 20,
                        "zone_low":        pdl - 20,
                        "zone_timeframe":  "D",
                        "spot_at_signal":  close,
                        "dte":             None,
                        "gamma_regime":    mkt.get("gamma_regime","UNKNOWN"),
                        "breadth_regime":  mkt.get("breadth_regime","UNKNOWN"),
                        "iv_regime":       mkt.get("iv_regime","UNKNOWN"),
                        "pcr_regime":      None,
                        "flow_regime":     None,
                        "skew_regime":     None,
                        "ret_session":     float(mkt["ret_session"]) if mkt.get("ret_session") else None,
                        "vix_at_signal":   None,
                        "ret_30m":         ret_30m,
                        "ret_60m":         None,
                        "win_30m":         win_30m,
                        "win_60m":         None,
                        "source":          "backfill_5m",
                    })
                    total += 1
                    sweeps += 1

            # Bear sweep: prev bar closes above PDH, this bar closes below
            if (pdh and not swept_pdh and
                    prev_c > pdh * (1 + SWEEP_MIN_PCT) and close < pdh):
                swept_pdh = True
                sk = (trade_date, symbol, "SWEEP_BEAR")
                if sk not in seen:
                    seen.add(sk)

                    wq, wr_ratio, cp = wick_quality_5m(bar, "bear")
                    win_30m = ret_30m < 0 if ret_30m is not None else None

                    atm_now = get_atm_at(trade_date, symbol, bar_ts)
                    atm_t30 = get_atm_t30(trade_date, symbol, bar_ts)
                    pe_ret = win_opt = None
                    if atm_now.get("pe_close") and atm_t30.get("pe_close"):
                        pn = float(atm_now["pe_close"])
                        pt = float(atm_t30["pe_close"])
                        if pn > 0:
                            pe_ret = (pt - pn) / pn * 100
                            win_opt = pe_ret > 0

                    pending.append({
                        "trade_date":      trade_date,
                        "bar_ts":          bar_ts,
                        "symbol":          symbol,
                        "pattern_type":    "SWEEP_REVERSAL",
                        "tier":            "TIER1",
                        "direction":       "BUY_PE",
                        "session":         "MORNING",
                        "zone_high":       pdh + 20,
                        "zone_low":        pdh - 20,
                        "zone_timeframe":  "D",
                        "spot_at_signal":  close,
                        "dte":             None,
                        "gamma_regime":    mkt.get("gamma_regime","UNKNOWN"),
                        "breadth_regime":  mkt.get("breadth_regime","UNKNOWN"),
                        "iv_regime":       mkt.get("iv_regime","UNKNOWN"),
                        "pcr_regime":      None,
                        "flow_regime":     None,
                        "skew_regime":     None,
                        "ret_session":     float(mkt["ret_session"]) if mkt.get("ret_session") else None,
                        "vix_at_signal":   None,
                        "ret_30m":         ret_30m,
                        "ret_60m":         None,
                        "win_30m":         win_30m,
                        "win_60m":         None,
                        "source":          "backfill_5m",
                    })
                    total += 1
                    sweeps += 1

            if len(pending) >= 200:
                written += upsert_batch(sb, pending)
                pending = []

    if pending:
        written += upsert_batch(sb, pending)

    log(f"\n  Signals: {total} (ICT: {total-sweeps}, Sweeps: {sweeps})")
    log(f"  Written: {written}")

    # ── Verify ───────────────────────────────────────────────────────────
    log("\nStep 7: Verifying...")
    r = sb.table("hist_pattern_signals").select(
        "pattern_type,source", count="exact").limit(5000).execute()
    log(f"  Total rows: {r.count}")
    counts = Counter(row["pattern_type"] for row in r.data)
    for pt, cnt in sorted(counts.items()):
        log(f"  {pt}: {cnt}")

    log("\nDone. Now run experiments on 5m data.")


if __name__ == "__main__":
    main()
