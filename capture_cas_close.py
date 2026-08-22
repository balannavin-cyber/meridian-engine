#!/usr/bin/env python3
"""
capture_cas_close.py  --  CAS settled-close bar writer (Session 70)
===================================================================
ADR-022 D1/D2. Companion to capture_spot_1m_v2.py.

WHY THIS EXISTS
---------------
SEBI's Closing Auction Session went live 2026-08-03. NIFTY and SENSEX are
computed from Category-I (F&O) constituents, which stop continuous trading
at 15:15 and settle by auction. Consequences observed on the Dhan feed
(probed 2026-08-20 and 2026-08-21, both symbols):

  15:06-15:14  real varying OHLC, volume 1.2-3.0M      <- normal trading
  15:15-15:28  O=H=L=C frozen, volume = the 15:14 bar's <- index frozen
  15:29        open = frozen value, high/close = SETTLED close, e.g.
               2026-08-20  24211.60 -> 24231.85
               2026-08-21  24234.75 -> 24252.00

The settled close therefore lands in the 15:29 bar. capture_spot_1m_v2.py
never sees it: its cron ends at 09:59 UTC (15:29 IST), which requests the
15:28 bar. Result -- hist_spot_bars_1m has been closing each session on the
frozen 15:14 value since 2026-08-03, ~20 points adrift, and every daily and
weekly ICT zone built by build_ict_htf_zones.py inherits that error.

Dhan's /charts/historical daily endpoint was checked as an alternative
source and REJECTED: at 18:32 IST it still returned only the PREVIOUS
session's row. Same-day daily OHLC is not available in time.

WHAT IT DOES
------------
Runs once per session at 15:50 IST. Requests a WIDE window (15:25-15:35)
rather than a single minute -- single-minute requests inside the auction
return an empty array. fetch_ohlc-equivalent takes the LAST bar in the
window, which is 15:29.

Guards, in order:
  1. Holiday gate (trading_calendar), same as capture_spot_1m_v2.
  2. Bar-timestamp assertion: the returned bar MUST be stamped 15:29 IST.
     Anything else means the vendor's shape changed -- refuse and exit
     DATA_ERROR rather than write a bar of unknown provenance.
  3. Settled-vs-frozen check: a genuine settled bar has close != open.
     If close == open the auction result has not landed yet; exit
     SKIPPED_NO_INPUT so a later manual run can retry. Never write a
     frozen value as the close (ADR-001: a plausible wrong close is worse
     than a missing one).

Writes the 15:29 bar to hist_spot_bars_1m (upsert on instrument_id,bar_ts)
and market_spot_snapshots, matching capture_spot_1m_v2's row shapes exactly.

BACKFILL
--------
  python3 capture_cas_close.py --date 2026-08-03
Historical windows are served fine by /charts/intraday, so every session
from 2026-08-03 forward is recoverable. Re-run build_ict_htf_zones.py
afterwards -- the daily closes will have changed.

Schedule (MERDIAN AWS crontab, UTC):
  20 10 * * 1-5  cd /home/ssm-user/meridian-engine && source .env && \
                 /usr/bin/python3 capture_cas_close.py >> logs/cas_close.log 2>&1
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone, timedelta, date as ddate
from typing import Dict, List
from zoneinfo import ZoneInfo

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.execution_log import ExecutionLog


# ── Config ────────────────────────────────────────────────────────────────────

SUPABASE_URL   = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY   = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "").strip()
DHAN_API_TOKEN = os.getenv("DHAN_API_TOKEN", "").strip()

DHAN_INTRADAY_URL = "https://api.dhan.co/v2/charts/intraday"
TIMEOUT     = 30
MAX_RETRIES = 4

IST = ZoneInfo("Asia/Kolkata")

# The window we request. Wide on purpose: single-minute requests inside the
# auction return an empty array. 15:35 is exclusive on Dhan's contract.
CAS_WINDOW_FROM = (15, 25)
CAS_WINDOW_TO   = (15, 35)

# The bar we expect back. Assertion, not a preference.
CAS_CLOSE_BAR   = (15, 29)

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


# ── Supabase helpers (identical shape to capture_spot_1m_v2.py) ──────────────

def sb_headers() -> Dict[str, str]:
    return {
        "apikey":        SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type":  "application/json",
        "Accept":        "application/json",
    }


def sb_insert(table: str, rows: List[Dict]) -> None:
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}",
                      headers=sb_headers(), json=rows, timeout=TIMEOUT)
    if r.status_code >= 300:
        raise RuntimeError(f"Supabase INSERT {table} failed: "
                           f"{r.status_code} {r.text[:200]}")


def sb_upsert(table: str, rows: List[Dict], on_conflict: str) -> None:
    r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}",
                      headers={**sb_headers(),
                               "Prefer": "resolution=merge-duplicates"},
                      params={"on_conflict": on_conflict},
                      json=rows, timeout=TIMEOUT)
    if r.status_code >= 300:
        raise RuntimeError(f"Supabase UPSERT {table} failed: "
                           f"{r.status_code} {r.text[:200]}")


def check_market_open(today_str: str) -> bool | None:
    try:
        r = requests.get(f"{SUPABASE_URL}/rest/v1/trading_calendar",
                         headers=sb_headers(),
                         params={"trade_date": f"eq.{today_str}",
                                 "select": "is_open,open_time"},
                         timeout=10)
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


# ── Dhan fetch ────────────────────────────────────────────────────────────────

def fetch_cas_bar(symbol: str, trade_day: ddate) -> Dict | None:
    """
    Fetch the LAST bar in the 15:25-15:35 IST window -- expected to be 15:29,
    the bar carrying the CAS settled close. Returns None on empty window.
    """
    cfg = INSTRUMENTS[symbol]
    frm = datetime.combine(trade_day, datetime.min.time(), IST).replace(
        hour=CAS_WINDOW_FROM[0], minute=CAS_WINDOW_FROM[1])
    to = datetime.combine(trade_day, datetime.min.time(), IST).replace(
        hour=CAS_WINDOW_TO[0], minute=CAS_WINDOW_TO[1])

    headers = {
        "Accept":       "application/json",
        "Content-Type": "application/json",
        "access-token": DHAN_API_TOKEN,
        "client-id":    DHAN_CLIENT_ID,
    }
    payload = {
        "securityId":      cfg["security_id"],
        "exchangeSegment": cfg["exchange_segment"],
        "instrument":      cfg["instrument_type"],
        "interval":        "1",
        "oi":              False,
        "fromDate":        frm.strftime("%Y-%m-%d %H:%M:%S"),
        "toDate":          to.strftime("%Y-%m-%d %H:%M:%S"),
    }

    backoff = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        r = requests.post(DHAN_INTRADAY_URL, headers=headers,
                          json=payload, timeout=TIMEOUT)
        if r.status_code == 200:
            body = r.json()
            opens = body.get("open", [])
            if not opens:
                return None
            return {
                "open":      float(body["open"][-1]),
                "high":      float(body["high"][-1]),
                "low":       float(body["low"][-1]),
                "close":     float(body["close"][-1]),
                "volume":    int(body.get("volume", [0])[-1] or 0),
                "timestamp": int(body.get("timestamp", [0])[-1] or 0),
                "n_bars":    len(opens),
            }
        if r.status_code == 429 and attempt < MAX_RETRIES:
            print(f"  [429] {symbol} rate limit, retry {attempt}/{MAX_RETRIES} "
                  f"in {backoff:.0f}s")
            time.sleep(backoff)
            backoff *= 2
            continue
        raise RuntimeError(f"Dhan /charts/intraday {symbol} "
                           f"HTTP {r.status_code}: {r.text[:300]}")

    raise RuntimeError(f"Dhan fetch_cas_bar({symbol}) failed after all retries")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description="CAS settled-close bar writer")
    ap.add_argument("--date", help="YYYY-MM-DD backfill target (default: today)")
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch and report, write nothing")
    args = ap.parse_args()

    log = ExecutionLog(
        script_name="capture_cas_close.py",
        expected_writes={
            "market_spot_snapshots": 2,
            "hist_spot_bars_1m":     2,
        },
        notes="CAS settled-close bar (15:29 IST), NIFTY+SENSEX, ADR-022 D2",
    )

    missing = [v for v, val in [
        ("SUPABASE_URL", SUPABASE_URL),
        ("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_KEY),
        ("DHAN_CLIENT_ID", DHAN_CLIENT_ID),
        ("DHAN_API_TOKEN", DHAN_API_TOKEN),
    ] if not val]
    if missing:
        for v in missing:
            print(f"[ERROR] Missing {v}", file=sys.stderr)
        return log.exit_with_reason(
            "DEPENDENCY_MISSING", exit_code=1,
            error_message=f"Missing env vars: {', '.join(missing)}")

    now_ist = datetime.now(IST)
    if args.date:
        try:
            trade_day = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print(f"[ERROR] --date must be YYYY-MM-DD, got {args.date!r}",
                  file=sys.stderr)
            return log.exit_with_reason("DEPENDENCY_MISSING", exit_code=1,
                                        error_message="bad --date")
    else:
        trade_day = now_ist.date()
    today_str = str(trade_day)

    print(f"[{now_ist.strftime('%H:%M:%S IST')}] capture_cas_close.py")
    print(f"  Target session: {today_str}")
    print(f"  Window: {CAS_WINDOW_FROM[0]:02d}:{CAS_WINDOW_FROM[1]:02d} -> "
          f"{CAS_WINDOW_TO[0]:02d}:{CAS_WINDOW_TO[1]:02d} IST "
          f"(expect last bar at {CAS_CLOSE_BAR[0]:02d}:{CAS_CLOSE_BAR[1]:02d})")

    if check_market_open(today_str) is False:
        print(f"[{today_str}] Market holiday -- exiting cleanly.")
        return log.exit_with_reason(
            "HOLIDAY_GATE", notes=f"trading_calendar says closed for {today_str}")

    bars: Dict[str, Dict] = {}
    errors: List[str] = []
    auth_failed = False
    rejects: List[str] = []

    for symbol in INSTRUMENTS:
        try:
            bar = fetch_cas_bar(symbol, trade_day)
            if bar is None:
                print(f"  [INFO] {symbol}: empty window")
                rejects.append(f"{symbol}:empty")
                continue

            bar_ist = datetime.fromtimestamp(bar["timestamp"], IST)

            # Guard 2 -- bar-timestamp assertion.
            if (bar_ist.hour, bar_ist.minute) != CAS_CLOSE_BAR:
                msg = (f"{symbol}: last bar is {bar_ist.strftime('%H:%M')} IST, "
                       f"expected {CAS_CLOSE_BAR[0]:02d}:{CAS_CLOSE_BAR[1]:02d} "
                       f"-- vendor bar shape changed, refusing to write")
                print(f"  [REJECT] {msg}", file=sys.stderr)
                rejects.append(f"{symbol}:wrong_bar_{bar_ist.strftime('%H:%M')}")
                continue

            # Guard 3 -- settled vs still-frozen.
            if bar["close"] == bar["open"]:
                msg = (f"{symbol}: 15:29 bar still frozen "
                       f"(O=C={bar['close']:.2f}); auction result not landed")
                print(f"  [REJECT] {msg}")
                rejects.append(f"{symbol}:frozen")
                continue

            bars[symbol] = bar
            print(f"  {symbol}: bar={bar_ist.strftime('%H:%M')} IST  "
                  f"O={bar['open']:.2f} H={bar['high']:.2f} "
                  f"L={bar['low']:.2f} C={bar['close']:.2f} "
                  f"V={bar['volume']}  (settled move "
                  f"{bar['close'] - bar['open']:+.2f})")

        except Exception as e:
            err = str(e)
            print(f"  [ERROR] {symbol} fetch failed: {err}", file=sys.stderr)
            errors.append(f"{symbol}: {err[:200]}")
            if "401" in err or "Authentication" in err or \
               "token invalid" in err.lower():
                auth_failed = True

    if auth_failed:
        return log.exit_with_reason("TOKEN_EXPIRED", exit_code=1,
                                    error_message="; ".join(errors)[:2000])

    if not bars:
        reason = "DATA_ERROR" if errors else "SKIPPED_NO_INPUT"
        return log.exit_with_reason(
            reason,
            exit_code=(1 if errors else 0),
            error_message=("; ".join(errors)[:2000] if errors else None),
            notes=f"No settled CAS bar for any symbol; rejects={rejects}")

    if args.dry_run:
        print("  DRY-RUN: no writes performed.")
        return log.exit_with_reason("DRY_RUN", notes=f"would write {len(bars)} symbols")

    capture_ts = datetime.now(IST).astimezone(timezone.utc).isoformat()

    # ── 1. market_spot_snapshots ─────────────────────────────────────────────
    snap_rows = []
    for symbol, bar in bars.items():
        bar_ist = datetime.fromtimestamp(bar["timestamp"], IST)
        snap_rows.append({
            "ts":           capture_ts,
            "symbol":       symbol,
            "spot":         bar["close"],
            "source_table": "dhan_charts_intraday",
            "raw": {
                "provider":         "dhan",
                "endpoint":         "charts/intraday",
                "exchange_segment": INSTRUMENTS[symbol]["exchange_segment"],
                "security_id":      INSTRUMENTS[symbol]["security_id"],
                "source_script":    "capture_cas_close",
                "cas_settled":      True,
                "bar_ts_ist":       bar_ist.isoformat(),
                "bar_window_from":  f"{today_str} "
                                    f"{CAS_WINDOW_FROM[0]:02d}:{CAS_WINDOW_FROM[1]:02d}:00",
                "bar_window_to":    f"{today_str} "
                                    f"{CAS_WINDOW_TO[0]:02d}:{CAS_WINDOW_TO[1]:02d}:00",
                "bars_in_window":   bar["n_bars"],
                "frozen_open":      bar["open"],
                "settled_close":    bar["close"],
                "settled_move":     round(bar["close"] - bar["open"], 4),
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

    # ── 2. hist_spot_bars_1m ─────────────────────────────────────────────────
    bar_rows = []
    for symbol, bar in bars.items():
        bar_ts_utc = datetime.fromtimestamp(
            bar["timestamp"], IST).astimezone(timezone.utc).isoformat()
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
        print(f"  hist_spot_bars_1m:     {len(bar_rows)} rows upserted "
              f"(CAS settled close)")
        log.record_write("hist_spot_bars_1m", len(bar_rows))
    except Exception as e:
        print(f"  [WARN] hist_spot_bars_1m write failed: {e}", file=sys.stderr)

    if rejects:
        print(f"  NOTE: {len(rejects)} symbol(s) rejected: {rejects}")

    print("  Done.")
    return log.complete()


if __name__ == "__main__":
    sys.exit(main())
