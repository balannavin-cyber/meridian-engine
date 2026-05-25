#!/usr/bin/env python3
"""
capture_spot_1m_v2.py  --  Real-OHLC live spot bar writer (Session 20)
======================================================================
v2.1 (2026-05-05 evening): adds market-hours guard + filler-bar skip.
v2.0 (2026-05-05 evening): replaced LTP synthetic O=H=L=C with real OHLC
     from Dhan /charts/intraday.

What changed vs v1:
  v1: hits /v2/marketfeed/ltp, gets a single price, writes O=H=L=C=spot.
  v2: hits /v2/charts/intraday for the previous minute, writes real OHLC.

What changed v2.0 -> v2.1:
  - Market-hours guard: skip the API call entirely when the requested bar
    window is outside 09:14-15:31 IST. Defensive in case Task Scheduler
    fires outside its window (or the script runs manually post-close).
    Saves API quota and prevents writing filler bars.
  - Filler-bar skip: Dhan returns "filler" rows for closed-market minute
    queries with O=H=L=C and volume=0. v2.1 skips writes when volume=0
    AND OHLC are all equal. Real low-volatility minutes during market
    hours always have V > 0 for NIFTY/SENSEX index segments (verified
    empirically 2026-05-05).

What stayed the same:
  - Task Scheduler trigger (every minute, 09:14 -> 15:31 IST, Mon-Fri)
  - .env vars (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DHAN_CLIENT_ID,
    DHAN_API_TOKEN)
  - Writes to market_spot_snapshots and hist_spot_bars_1m
  - bar_ts convention (truncated to minute boundary)
  - Holiday gate (trading_calendar lookup)
  - ExecutionLog instrumentation (expected_writes contract preserved)
  - Heartbeat wrapper (MERDIAN_Spot_1M)

Edge case handling:
  - First cycle of the day (09:15:02 IST asking for 09:14 bar): pre-market
    period; market-hours guard skips with reason OUTSIDE_MARKET_HOURS.
  - 09:16:02 -> request 09:15:00 bar: first valid bar of the day.
  - 15:30:02 -> request 15:29:00 bar: last valid bar of the day.
  - 15:31:02 -> request 15:30:00 bar: market-hours guard skips.
  - 429 rate limit: 4 retries with exponential backoff (same as v1).
  - Empty response (e.g. holiday partial day, gap): log warning, skip.
  - Filler bar (V=0 + flat OHLC): log INFO, skip both writes for that
    symbol; if both symbols are filler, exit with NO_DATA.

Rollback: if v2 misbehaves, repoint Task Scheduler at capture_spot_1m.py.
v1 stays in place untouched.

Schedule via Windows Task Scheduler:
  Program:   python
  Arguments: C:\\GammaEnginePython\\capture_spot_1m_v2.py
  Start in:  C:\\GammaEnginePython
  Trigger:   Daily, repeat every 1 minute from 09:14 to 15:31 IST, Mon-Fri

Run manually:
    python capture_spot_1m_v2.py
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone, timedelta, time as dtime
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ENH-71 write-contract layer. Same instrumentation as v1.
from core.execution_log import ExecutionLog


# ── Config ────────────────────────────────────────────────────────────────────

SUPABASE_URL     = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY     = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
DHAN_CLIENT_ID   = os.getenv("DHAN_CLIENT_ID", "").strip()
DHAN_API_TOKEN   = os.getenv("DHAN_API_TOKEN", "").strip()

DHAN_INTRADAY_URL = "https://api.dhan.co/v2/charts/intraday"
TIMEOUT          = 30
MAX_RETRIES      = 4

IST = ZoneInfo("Asia/Kolkata")

# Market-hours window (IST). v2.1 guard.
# We check the REQUESTED BAR'S start time, not now(). When now=09:15:02 we
# request the 09:14 bar -> guard rejects (pre-open). When now=09:16:02 we
# request the 09:15 bar -> guard accepts (first valid intraday bar).
# When now=15:30:02 we request 15:29 -> guard accepts. When now=15:31:02
# we request 15:30 -> guard rejects.
MARKET_OPEN_GUARD  = dtime(9, 15)   # inclusive
MARKET_CLOSE_GUARD = dtime(15, 30)  # exclusive (15:29 valid, 15:30 not)

# Instrument identifiers.
# securityId / exchangeSegment / instrument follow the v2 charts/intraday
# contract -- "INDEX" type is required for IDX_I segment indices.
# instrument_id is the Supabase UUID for the foreign key into the bars table.
INSTRUMENTS = {
    "NIFTY": {
        "exchange_segment": "IDX_I",
        "security_id":      "13",
        "instrument_type":  "INDEX",
        "instrument_id":    "9992f600-51b3-4009-b487-f878692a0bc5",
    },
    "SENSEX": {
        "exchange_segment": "IDX_I",
        "security_id":      "51",
        "instrument_type":  "INDEX",
        "instrument_id":    "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71",
    },
}


# ── Supabase helpers ──────────────────────────────────────────────────────────

def sb_headers() -> Dict[str, str]:
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }


def sb_insert(table: str, rows: List[Dict]) -> None:
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers=sb_headers(),
        json=rows,
        timeout=TIMEOUT,
    )
    if r.status_code >= 300:
        raise RuntimeError(
            f"Supabase INSERT {table} failed: {r.status_code} {r.text[:200]}"
        )


def sb_upsert(table: str, rows: List[Dict], on_conflict: str) -> None:
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/{table}",
        headers={**sb_headers(), "Prefer": "resolution=merge-duplicates"},
        params={"on_conflict": on_conflict},
        json=rows,
        timeout=TIMEOUT,
    )
    if r.status_code >= 300:
        raise RuntimeError(
            f"Supabase UPSERT {table} failed: {r.status_code} {r.text[:200]}"
        )


# ── Dhan /charts/intraday fetch ───────────────────────────────────────────────

def previous_minute_window(now_ist: datetime) -> Tuple[datetime, datetime]:
    """
    Return (from_ts, to_ts) in IST for the just-completed minute.

    If `now_ist` is 10:30:02, the previous minute is 10:29:00 - 10:30:00.
    Dhan's toDate is exclusive, so we set toDate to the start of the
    current minute (10:30:00) and fromDate to one minute earlier.
    """
    minute_floor = now_ist.replace(second=0, microsecond=0)
    from_ts = minute_floor - timedelta(minutes=1)
    to_ts = minute_floor
    return from_ts, to_ts


def fetch_ohlc(symbol: str, from_ts_ist: datetime,
               to_ts_ist: datetime) -> Dict[str, float] | None:
    """
    Fetch the 1-min OHLC bar for the given window from Dhan.

    Returns dict with keys open/high/low/close/volume/timestamp for the
    single most recent bar in the window. Returns None if Dhan returned no
    data (pre-market, holiday, or edge case).

    Raises RuntimeError on auth/data errors so caller can classify.
    """
    cfg = INSTRUMENTS[symbol]
    headers = {
        "Accept":        "application/json",
        "Content-Type":  "application/json",
        "access-token":  DHAN_API_TOKEN,
        "client-id":     DHAN_CLIENT_ID,
    }
    payload = {
        "securityId":      cfg["security_id"],
        "exchangeSegment": cfg["exchange_segment"],
        "instrument":      cfg["instrument_type"],
        "interval":        "1",
        "oi":              False,
        "fromDate":        from_ts_ist.strftime("%Y-%m-%d %H:%M:%S"),
        "toDate":          to_ts_ist.strftime("%Y-%m-%d %H:%M:%S"),
    }

    backoff = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        r = requests.post(
            DHAN_INTRADAY_URL, headers=headers, json=payload, timeout=TIMEOUT
        )
        if r.status_code == 200:
            body = r.json()
            opens = body.get("open", [])
            if not opens:
                return None  # empty window
            # Take the LAST entry in each array -- represents the most recent
            # bar in the requested window. For a 1-minute window this is the
            # only entry; for any wider window we still want the latest.
            return {
                "open":      float(body["open"][-1]),
                "high":      float(body["high"][-1]),
                "low":       float(body["low"][-1]),
                "close":     float(body["close"][-1]),
                "volume":    int(body.get("volume", [0])[-1] or 0),
                "timestamp": int(body.get("timestamp", [0])[-1] or 0),
            }
        if r.status_code == 429:
            if attempt < MAX_RETRIES:
                print(
                    f"  [429] {symbol} rate limit, retry {attempt}/{MAX_RETRIES} "
                    f"in {backoff:.0f}s"
                )
                time.sleep(backoff)
                backoff *= 2
                continue
        # Any non-200/non-429 is a hard error
        raise RuntimeError(
            f"Dhan /charts/intraday {symbol} HTTP {r.status_code}: {r.text[:300]}"
        )

    raise RuntimeError(f"Dhan fetch_ohlc({symbol}) failed after all retries")


def is_filler_bar(bar: Dict) -> bool:
    """
    Detect Dhan's post-market 'filler' bars.

    Dhan returns synthetic bars for closed-market minute queries: O=H=L=C
    matching the last known price, with volume=0. These are not real ticks
    and must not be written to hist_spot_bars_1m.

    Real low-volatility minutes during market hours always have V > 0
    for NIFTY/SENSEX index segments (verified empirically 2026-05-05).
    """
    return (
        bar.get("volume", 0) == 0
        and bar["open"] == bar["high"] == bar["low"] == bar["close"]
    )


# ── Holiday gate (preserved from v1) ──────────────────────────────────────────

def check_market_open(today_str: str) -> bool | None:
    """
    Returns True if market is open today, False if explicitly closed,
    None if no calendar row exists (allow run; merdian_start.py will
    upsert later).
    """
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/trading_calendar",
            headers=sb_headers(),
            params={"trade_date": f"eq.{today_str}",
                    "select": "is_open,open_time"},
            timeout=10,
        )
        if r.status_code == 200:
            rows = r.json()
            if not rows:
                return None
            row = rows[0]
            if not row.get("is_open", True) or row.get("open_time") is None:
                return False
            return True
    except Exception as e:
        print(f"  [WARN] Calendar check failed (proceeding): {e}")
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    log = ExecutionLog(
        script_name="capture_spot_1m_v2.py",
        expected_writes={
            "market_spot_snapshots": 2,
            "hist_spot_bars_1m":     2,
        },
        notes="v2.1 real OHLC capture (Dhan /charts/intraday), NIFTY+SENSEX",
    )

    # ── Env validation ────────────────────────────────────────────────────────
    missing = []
    for var, val in [
        ("SUPABASE_URL", SUPABASE_URL),
        ("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_KEY),
        ("DHAN_CLIENT_ID", DHAN_CLIENT_ID),
        ("DHAN_API_TOKEN", DHAN_API_TOKEN),
    ]:
        if not val:
            print(f"[ERROR] Missing {var}", file=sys.stderr)
            missing.append(var)
    if missing:
        return log.exit_with_reason(
            "DEPENDENCY_MISSING",
            exit_code=1,
            error_message=f"Missing env vars: {', '.join(missing)}",
        )

    # ── Time anchors ──────────────────────────────────────────────────────────
    now_ist    = datetime.now(IST)
    today_str  = str(now_ist.date())
    from_ts_ist, to_ts_ist = previous_minute_window(now_ist)

    # The bar we're writing is identified by from_ts (the start of the
    # just-completed minute). bar_ts in DB is UTC.
    bar_ts_utc = from_ts_ist.astimezone(timezone.utc).isoformat()
    capture_ts = now_ist.astimezone(timezone.utc).isoformat()

    print(f"[{now_ist.strftime('%H:%M:%S IST')}] capture_spot_1m_v2.py")
    print(f"  Requesting OHLC window: "
          f"{from_ts_ist.strftime('%H:%M:%S')} -> "
          f"{to_ts_ist.strftime('%H:%M:%S')} IST")

    # ── v2.1: Market-hours guard ──────────────────────────────────────────────
    # Skip API calls if the requested bar's start time is outside market
    # hours. Examples (IST):
    #   now=09:15:02 -> request 09:14 bar -> guard skips (pre-open)
    #   now=09:16:02 -> request 09:15 bar -> guard allows (first valid)
    #   now=15:30:02 -> request 15:29 bar -> guard allows (last valid)
    #   now=15:31:02 -> request 15:30 bar -> guard skips (post-close)
    requested_time = from_ts_ist.time()
    if not (MARKET_OPEN_GUARD <= requested_time < MARKET_CLOSE_GUARD):
        print(
            f"  Outside market hours window "
            f"({MARKET_OPEN_GUARD}-{MARKET_CLOSE_GUARD} IST); skipping."
        )
        return log.exit_with_reason(
            "OUTSIDE_MARKET_HOURS",
            notes=(
                f"requested bar {from_ts_ist.strftime('%H:%M')} IST is "
                f"outside {MARKET_OPEN_GUARD}-{MARKET_CLOSE_GUARD}"
            ),
        )

    # ── Holiday gate ──────────────────────────────────────────────────────────
    is_open = check_market_open(today_str)
    if is_open is False:
        print(f"[{today_str}] Market holiday -- exiting cleanly.")
        return log.exit_with_reason(
            "HOLIDAY_GATE",
            notes=f"trading_calendar says closed for {today_str}",
        )

    # ── Fetch OHLC for both symbols ──────────────────────────────────────────
    bars_by_symbol: Dict[str, Dict] = {}
    auth_failed = False
    fetch_errors: List[str] = []

    for symbol in INSTRUMENTS:
        try:
            ohlc = fetch_ohlc(symbol, from_ts_ist, to_ts_ist)
            if ohlc is None:
                print(f"  [INFO] {symbol}: empty window")
                continue
            # v2.1: Filler-bar guard
            if is_filler_bar(ohlc):
                print(
                    f"  [INFO] {symbol}: filler bar (V=0, "
                    f"O=H=L=C={ohlc['close']:.2f}); skipping write"
                )
                continue
            bars_by_symbol[symbol] = ohlc
            print(
                f"  {symbol}: O={ohlc['open']:.2f} H={ohlc['high']:.2f} "
                f"L={ohlc['low']:.2f} C={ohlc['close']:.2f} "
                f"V={ohlc['volume']}"
            )
        except Exception as e:
            err_msg = str(e)
            print(f"  [ERROR] {symbol} fetch failed: {err_msg}", file=sys.stderr)
            fetch_errors.append(f"{symbol}: {err_msg[:200]}")
            if "401" in err_msg or "Authentication" in err_msg or \
               "token invalid" in err_msg.lower():
                auth_failed = True

    if auth_failed:
        return log.exit_with_reason(
            "TOKEN_EXPIRED",
            exit_code=1,
            error_message="; ".join(fetch_errors)[:2000],
        )

    if not bars_by_symbol:
        # All symbols returned empty/filler/error. Pre-market gap is the
        # most common cause; not a hard failure unless fetch errored.
        reason = "DATA_ERROR" if fetch_errors else "NO_DATA"
        return log.exit_with_reason(
            reason,
            exit_code=(1 if fetch_errors else 0),
            error_message=("; ".join(fetch_errors)[:2000] if fetch_errors else None),
            notes="No usable OHLC for any symbol (empty/filler/error)",
        )

    # ── 1. Write to market_spot_snapshots ─────────────────────────────────────
    snap_rows = []
    for symbol, bar in bars_by_symbol.items():
        snap_rows.append({
            "ts":           capture_ts,
            "symbol":       symbol,
            "spot":         bar["close"],   # close = current spot
            "source_table": "dhan_charts_intraday",
            "raw": {
                "provider":         "dhan",
                "endpoint":         "charts/intraday",
                "exchange_segment": INSTRUMENTS[symbol]["exchange_segment"],
                "security_id":      INSTRUMENTS[symbol]["security_id"],
                "source_script":    "capture_spot_1m_v2",
                "bar_window_from":  from_ts_ist.isoformat(),
                "bar_window_to":    to_ts_ist.isoformat(),
                "ohlc_open":        bar["open"],
                "ohlc_high":        bar["high"],
                "ohlc_low":         bar["low"],
                "ohlc_close":       bar["close"],
                "ohlc_volume":      bar["volume"],
            },
        })

    try:
        sb_insert("market_spot_snapshots", snap_rows)
        print(f"  market_spot_snapshots: {len(snap_rows)} rows inserted")
        log.record_write("market_spot_snapshots", len(snap_rows))
    except Exception as e:
        print(f"  [WARN] market_spot_snapshots write failed: {e}", file=sys.stderr)

    # ── 2. Write real-OHLC 1-min bar to hist_spot_bars_1m ────────────────────
    bar_rows = []
    for symbol, bar in bars_by_symbol.items():
        bar_rows.append({
            "instrument_id": INSTRUMENTS[symbol]["instrument_id"],
            "trade_date":    today_str,
            "bar_ts":        bar_ts_utc,
            "open":          bar["open"],
            "high":          bar["high"],
            "low":           bar["low"],
            "close":         bar["close"],
            "is_pre_market": False,
        })

    try:
        sb_upsert("hist_spot_bars_1m", bar_rows,
                  on_conflict="instrument_id,bar_ts")
        print(
            f"  hist_spot_bars_1m:     {len(bar_rows)} rows upserted "
            f"(bar_ts={bar_ts_utc[:16]})"
        )
        log.record_write("hist_spot_bars_1m", len(bar_rows))
    except Exception as e:
        print(f"  [WARN] hist_spot_bars_1m write failed: {e}", file=sys.stderr)

    print(f"  Done.")
    return log.complete()


if __name__ == "__main__":
    from merdian_heartbeat import heartbeat
    with heartbeat("MERDIAN_Spot_1M"):
        sys.exit(main())
