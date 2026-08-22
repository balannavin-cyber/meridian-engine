#!/usr/bin/env python3
"""
backfill_cas_close_from_daily.py  --  CAS close reconciliation (Session 70)
===========================================================================
ADR-022 D2. Companion to capture_cas_close.py.

WHY THIS EXISTS
---------------
capture_cas_close.py reads the 15:29 IST intraday bar, which is the only
source available SAME-DAY (Dhan's daily endpoint does not publish the
current session until the next morning -- verified 2026-08-21 18:32 IST,
which still returned only 2026-08-20).

Its Guard 3 refused any bar where close == open, on the theory that a flat
bar meant the auction result had not landed. That theory was WRONG. The
2026-08-03..2026-08-21 backfill produced 10 such rejects, and every one of
them was cross-checked against Dhan's daily endpoint and found to already
hold the CORRECT settled close:

    2026-08-06 NIFTY  frozen 24636.00  daily 24636.00
    2026-08-10 SENSEX frozen 78542.44  daily 78542.44
    2026-08-12 NIFTY  frozen 24435.95  daily 24435.95
    ... (10 symbol-days total)

close == open does not mean "not settled". It means the auction settled at
the same price the index was already frozen at -- which is the common case
on a quiet close. The guard was over-fitted to two samples where the price
happened to move.

Separately, sessions 2026-08-03/04/05 place the last bar at 15:34 IST, not
15:29, so capture_cas_close.py's bar-timestamp assertion rejected them too.
The exchange/vendor window differed in the first CAS week.

THIS SCRIPT
-----------
Uses Dhan's DAILY endpoint (/v2/charts/historical) as the authoritative
settled close. Verified against all 18 successfully-written intraday bars
on 2026-08-22: 18/18 exact match, zero mismatches.

For each (trade_date, symbol) in the requested range it:
  1. reads the authoritative daily close,
  2. reads the existing 15:29 IST bar from hist_spot_bars_1m, if any,
  3. classifies:
       MATCH    -- bar exists and close agrees      -> no write
       MISMATCH -- bar exists and close disagrees   -> no write, REPORTED
       MISSING  -- no bar                           -> upsert
  4. upserts only the MISSING rows.

MISMATCH is never auto-corrected. A disagreement between the intraday bar
and the daily close means one of the two sources is wrong, and silently
overwriting one with the other would destroy the evidence needed to work
out which. It is reported and left alone -- decide deliberately.

The synthesised bar is marked in market_spot_snapshots.raw with
source_script=backfill_cas_close_from_daily and cas_source=daily_endpoint
so it is distinguishable from a live intraday capture forever after.

O/H/L are set equal to the daily close, NOT carried from the daily bar's
own O/H/L -- this row represents the closing print only, and the session's
real intraday range already lives in the 09:15-15:14 bars.

USAGE
-----
  python3 backfill_cas_close_from_daily.py --from 2026-08-03 --to 2026-08-21 --dry-run
  python3 backfill_cas_close_from_daily.py --from 2026-08-03 --to 2026-08-21
  python3 backfill_cas_close_from_daily.py --from 2026-08-24 --to 2026-08-28   # weekly recon

Recommended as a weekly reconciliation pass, since it is idempotent: it
writes only what is missing and reports anything that disagrees.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone, timedelta, date as ddate
from typing import Dict, List, Tuple
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

DHAN_DAILY_URL = "https://api.dhan.co/v2/charts/historical"
TIMEOUT     = 30
MAX_RETRIES = 4

IST = ZoneInfo("Asia/Kolkata")

# The canonical closing-bar slot. 15:29 IST is the last minute of the
# session as MERDIAN stores it; the settled close is written here so that
# max(bar_ts) per session is the settled close.
CLOSE_BAR_IST = (15, 29)

# Tolerance for MATCH classification. Index closes are quoted to 2dp;
# anything beyond half a paisa is a real disagreement, not float noise.
MATCH_EPSILON = 0.005

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


def fetch_existing_close_bars(frm: ddate, to: ddate) -> Dict[Tuple[str, str], float]:
    """
    Return {(trade_date_str, instrument_id): close} for every bar already
    sitting in the CLOSE_BAR_IST slot within the range.
    """
    bar_utc_time = (datetime.combine(frm, datetime.min.time(), IST)
                    .replace(hour=CLOSE_BAR_IST[0], minute=CLOSE_BAR_IST[1])
                    .astimezone(timezone.utc).time())
    out: Dict[Tuple[str, str], float] = {}
    offset = 0
    page = 1000
    while True:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/hist_spot_bars_1m",
            headers={**sb_headers(),
                     "Range-Unit": "items",
                     "Range": f"{offset}-{offset + page - 1}"},
            params={"select": "trade_date,instrument_id,bar_ts,close",
                    "trade_date": f"gte.{frm}",
                    "and": f"(trade_date.lte.{to})",
                    "order": "trade_date.asc"},
            timeout=TIMEOUT,
        )
        if r.status_code >= 300:
            raise RuntimeError(f"Supabase GET hist_spot_bars_1m failed: "
                               f"{r.status_code} {r.text[:200]}")
        rows = r.json()
        if not rows:
            break
        for row in rows:
            bts = str(row.get("bar_ts", ""))
            try:
                parsed = datetime.fromisoformat(bts.replace("Z", "+00:00"))
            except ValueError:
                continue
            if parsed.astimezone(timezone.utc).time() != bar_utc_time:
                continue
            out[(str(row["trade_date"]), str(row["instrument_id"]))] = \
                float(row["close"])
        if len(rows) < page:
            break
        offset += page
    return out


# ── Dhan daily fetch ──────────────────────────────────────────────────────────

def fetch_daily_closes(symbol: str, frm: ddate, to: ddate) -> Dict[str, float]:
    """
    Authoritative settled close per trade_date from Dhan's daily endpoint.
    Verified 2026-08-22 against 18 independently-captured intraday 15:29
    bars: 18/18 exact match.
    """
    cfg = INSTRUMENTS[symbol]
    payload = {
        "securityId":      cfg["security_id"],
        "exchangeSegment": cfg["exchange_segment"],
        "instrument":      cfg["instrument_type"],
        "fromDate":        str(frm),
        "toDate":          str(to + timedelta(days=1)),
    }
    headers = {
        "Accept":       "application/json",
        "Content-Type": "application/json",
        "access-token": DHAN_API_TOKEN,
        "client-id":    DHAN_CLIENT_ID,
    }

    backoff = 2.0
    for attempt in range(1, MAX_RETRIES + 1):
        r = requests.post(DHAN_DAILY_URL, headers=headers,
                          json=payload, timeout=TIMEOUT)
        if r.status_code == 200:
            body = r.json()
            ts = body.get("timestamp", [])
            cl = body.get("close", [])
            out: Dict[str, float] = {}
            for t, c in zip(ts, cl):
                d = datetime.fromtimestamp(t, IST).date()
                out[str(d)] = float(c)
            return out
        if r.status_code == 429 and attempt < MAX_RETRIES:
            print(f"  [429] {symbol} rate limit, retry {attempt}/{MAX_RETRIES} "
                  f"in {backoff:.0f}s")
            time.sleep(backoff)
            backoff *= 2
            continue
        raise RuntimeError(f"Dhan /charts/historical {symbol} "
                           f"HTTP {r.status_code}: {r.text[:300]}")

    raise RuntimeError(f"Dhan fetch_daily_closes({symbol}) failed after retries")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Reconcile CAS settled closes from Dhan daily endpoint")
    ap.add_argument("--from", dest="frm", required=True, help="YYYY-MM-DD")
    ap.add_argument("--to",   dest="to",  required=True, help="YYYY-MM-DD")
    ap.add_argument("--dry-run", action="store_true",
                    help="classify and report, write nothing")
    args = ap.parse_args()

    log = ExecutionLog(
        script_name="backfill_cas_close_from_daily.py",
        expected_writes={},
        notes="CAS close reconciliation from Dhan daily endpoint (ADR-022 D2)",
    )

    missing_env = [v for v, val in [
        ("SUPABASE_URL", SUPABASE_URL),
        ("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_KEY),
        ("DHAN_CLIENT_ID", DHAN_CLIENT_ID),
        ("DHAN_API_TOKEN", DHAN_API_TOKEN),
    ] if not val]
    if missing_env:
        for v in missing_env:
            print(f"[ERROR] Missing {v}", file=sys.stderr)
        return log.exit_with_reason(
            "DEPENDENCY_MISSING", exit_code=1,
            error_message=f"Missing env vars: {', '.join(missing_env)}")

    try:
        frm = datetime.strptime(args.frm, "%Y-%m-%d").date()
        to  = datetime.strptime(args.to,  "%Y-%m-%d").date()
    except ValueError:
        print("[ERROR] --from/--to must be YYYY-MM-DD", file=sys.stderr)
        return log.exit_with_reason("DEPENDENCY_MISSING", exit_code=1,
                                    error_message="bad date argument")
    if to < frm:
        print("[ERROR] --to is before --from", file=sys.stderr)
        return log.exit_with_reason("DEPENDENCY_MISSING", exit_code=1,
                                    error_message="range inverted")

    now_ist = datetime.now(IST)
    print(f"[{now_ist.strftime('%H:%M:%S IST')}] backfill_cas_close_from_daily.py")
    print(f"  Range: {frm} -> {to}")
    print(f"  Close-bar slot: {CLOSE_BAR_IST[0]:02d}:{CLOSE_BAR_IST[1]:02d} IST")
    print(f"  Authority: Dhan /charts/historical (daily)")

    # ── Gather ────────────────────────────────────────────────────────────────
    try:
        existing = fetch_existing_close_bars(frm, to)
    except Exception as e:
        print(f"[ERROR] could not read existing bars: {e}", file=sys.stderr)
        return log.exit_with_reason("DATA_ERROR", exit_code=1,
                                    error_message=str(e)[:2000])
    print(f"  Existing close bars in range: {len(existing)}")

    daily: Dict[str, Dict[str, float]] = {}
    for symbol in INSTRUMENTS:
        try:
            daily[symbol] = fetch_daily_closes(symbol, frm, to)
            print(f"  {symbol}: {len(daily[symbol])} daily closes fetched")
        except Exception as e:
            print(f"[ERROR] {symbol} daily fetch failed: {e}", file=sys.stderr)
            return log.exit_with_reason("DATA_ERROR", exit_code=1,
                                        error_message=str(e)[:2000])

    # ── Classify ──────────────────────────────────────────────────────────────
    matches:   List[str] = []
    mismatches: List[str] = []
    to_write:  List[Tuple[str, str, float]] = []   # (date, symbol, close)

    all_dates = sorted({d for m in daily.values() for d in m})
    for d in all_dates:
        for symbol in INSTRUMENTS:
            authoritative = daily[symbol].get(d)
            if authoritative is None:
                continue
            iid = INSTRUMENTS[symbol]["instrument_id"]
            have = existing.get((d, iid))
            if have is None:
                to_write.append((d, symbol, authoritative))
                print(f"  MISSING  {d} {symbol:6s} -> {authoritative:.2f}")
            elif abs(have - authoritative) <= MATCH_EPSILON:
                matches.append(f"{d}/{symbol}")
            else:
                mismatches.append(
                    f"{d}/{symbol} bar={have:.2f} daily={authoritative:.2f} "
                    f"delta={have - authoritative:+.2f}")
                print(f"  MISMATCH {d} {symbol:6s} bar={have:.2f} "
                      f"daily={authoritative:.2f} "
                      f"delta={have - authoritative:+.2f}  (NOT corrected)")

    print(f"\n  MATCH={len(matches)}  MISSING={len(to_write)}  "
          f"MISMATCH={len(mismatches)}")

    if mismatches:
        print("\n  *** MISMATCHES -- not auto-corrected, decide deliberately ***")
        for m in mismatches:
            print(f"    {m}")

    if not to_write:
        print("\n  Nothing to write.")
        return log.exit_with_reason(
            "SUCCESS" if not mismatches else "DATA_ERROR",
            exit_code=0,
            notes=(f"match={len(matches)} missing=0 mismatch={len(mismatches)}"))

    if args.dry_run:
        print(f"\n  DRY-RUN: would write {len(to_write)} bars.")
        return log.exit_with_reason(
            "DRY_RUN",
            notes=f"would write {len(to_write)}; mismatch={len(mismatches)}")

    # ── Write ─────────────────────────────────────────────────────────────────
    bar_rows: List[Dict] = []
    snap_rows: List[Dict] = []
    capture_ts = datetime.now(IST).astimezone(timezone.utc).isoformat()

    for d, symbol, close in to_write:
        day = datetime.strptime(d, "%Y-%m-%d").date()
        bar_ist = datetime.combine(day, datetime.min.time(), IST).replace(
            hour=CLOSE_BAR_IST[0], minute=CLOSE_BAR_IST[1])
        bar_ts_utc = bar_ist.astimezone(timezone.utc).isoformat()

        # O/H/L == close: this row is the closing print, not a range bar.
        bar_rows.append({
            "instrument_id": INSTRUMENTS[symbol]["instrument_id"],
            "trade_date":    d,
            "bar_ts":        bar_ts_utc,
            "open":          close,
            "high":          close,
            "low":           close,
            "close":         close,
            "is_pre_market": False,
        })
        snap_rows.append({
            "ts":           capture_ts,
            "symbol":       symbol,
            "spot":         close,
            "source_table": "dhan_charts_historical",
            "raw": {
                "provider":      "dhan",
                "endpoint":      "charts/historical",
                "source_script": "backfill_cas_close_from_daily",
                "cas_source":    "daily_endpoint",
                "cas_settled":   True,
                "synthesised":   True,
                "note":          ("closing print only; O/H/L set to close. "
                                  "Session intraday range lives in the "
                                  "09:15-15:14 bars."),
                "bar_ts_ist":    bar_ist.isoformat(),
                "trade_date":    d,
                "settled_close": close,
            },
        })

    try:
        sb_upsert("hist_spot_bars_1m", bar_rows,
                  on_conflict="instrument_id,bar_ts")
        print(f"\n  hist_spot_bars_1m:     {len(bar_rows)} rows upserted")
        log.record_write("hist_spot_bars_1m", len(bar_rows))
    except Exception as e:
        print(f"  [ERROR] hist_spot_bars_1m write failed: {e}", file=sys.stderr)
        return log.exit_with_reason("DATA_ERROR", exit_code=1,
                                    error_message=str(e)[:2000])

    try:
        sb_insert("market_spot_snapshots", snap_rows)
        print(f"  market_spot_snapshots: {len(snap_rows)} rows inserted")
        log.record_write("market_spot_snapshots", len(snap_rows))
    except Exception as e:
        print(f"  [WARN] market_spot_snapshots write failed: {e}", file=sys.stderr)

    print("\n  Done. Re-run build_ict_htf_zones.py -- daily/weekly closes changed.")
    return log.complete()


if __name__ == "__main__":
    sys.exit(main())
