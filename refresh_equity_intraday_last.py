#!/usr/bin/env python3
"""
refresh_equity_intraday_last.py
================================
Populates equity_intraday_last with fresh previous-session closes from Kite REST.
Runs once per morning pre-market (cron @ 09:05 IST).

Replaces the retired ingest_breadth_intraday_local.py for the reference-price
responsibility. Does NOT compute breadth — that job belongs to 
ingest_breadth_from_ticks.py (which reads from this table).

Contract:
  - Fetches prev_close via Kite REST ohlc() endpoint (single call, all symbols)
  - UPSERTs to equity_intraday_last with fresh ts = now()
  - Writes its script_execution_log row through core.execution_log (S102_TD_S77_NEW_8: was a
    hand-rolled insert with no opening RUNNING row, no status / kind)
  - Fails loudly on partial data or Kite errors
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
from kiteconnect import KiteConnect
from supabase import create_client

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

API_KEY      = os.environ["ZERODHA_API_KEY"]
ACCESS_TOKEN = os.environ["ZERODHA_ACCESS_TOKEN"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
IST          = timezone(timedelta(hours=5, minutes=30))

def log(msg):
    print(f"[{datetime.now(IST).strftime('%H:%M:%S IST')}] {msg}", flush=True)

def _classify_exit_reason(ok: bool, err: str) -> str:
    """S61 / TD-S59-NEW-2: pick a VALID chk_exit_reason_valid enum.
    'FAILURE' is not in the closed set, so failure rows were rejected
    (23514) and never persisted -- masking the S59 5-week freeze.
    Free-text detail stays in error_message; this only picks the bucket."""
    if ok:
        return "SUCCESS"
    e = (err or "").lower()
    if any(s in e for s in ("incorrect api_key", "access_token",
                            "tokenexception", "invalid session")):
        return "TOKEN_EXPIRED"
    return "DATA_ERROR"


# Floor kept from the hand-rolled row (contract_met = ok and rows >= 1000); the old row also stated an
# expected 1300 that the contract never used.
EXPECTED_MIN_ROWS = 1000


def main() -> int:
    from core.execution_log import ExecutionLog  # S102_TD_S77_NEW_8
    xlog = ExecutionLog(
        script_name="refresh_equity_intraday_last.py",
        expected_writes={"equity_intraday_last": EXPECTED_MIN_ROWS},
        notes="prev_close refresh via Kite ohlc()",
    )
    started_at = datetime.now(timezone.utc)
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(ACCESS_TOKEN)

    log("=" * 60)
    log("refresh_equity_intraday_last — prev_close from Kite REST")
    log("=" * 60)

    # Step 1: Load breadth universe symbols
    log("Loading breadth universe from Supabase...")
    members = []
    offset = 0
    while True:
        r = sb.table("breadth_universe_members").select(
            "symbol,exchange"
        ).eq("is_active", True).eq("active", True).range(offset, offset + 999).execute()
        if not r.data:
            break
        members.extend(r.data)
        if len(r.data) < 1000:
            break
        offset += 1000
    nse_symbols = [f"NSE:{m['symbol']}" for m in members if m.get("exchange") == "NSE"]
    log(f"  NSE breadth universe: {len(nse_symbols)} symbols")

    if len(nse_symbols) < 100:
        log("  ERROR: Universe too small, refusing to write")
        return xlog.exit_with_reason("DATA_ERROR", exit_code=1, error_message="universe<100")

    # Step 2: Fetch OHLC from Kite (returns prev day's close in .ohlc.close)
    log(f"Calling Kite ohlc() for {len(nse_symbols)} symbols...")
    try:
        # Kite ohlc() caps at 500 per call; chunk it
        ohlc_data = {}
        chunk_size = 250
        for i in range(0, len(nse_symbols), chunk_size):
            chunk = nse_symbols[i:i + chunk_size]
            result = kite.ohlc(chunk)
            ohlc_data.update(result)
            log(f"  chunk {i // chunk_size + 1}: {len(result)} symbols returned")
    except Exception as e:
        log(f"  ERROR: Kite ohlc() failed: {e}")
        return xlog.exit_with_reason(_classify_exit_reason(False, str(e)), exit_code=1,
                                     error_message=str(e)[:1000])

    # Step 3: Build payload — one row per symbol with prev_close
    now_iso = datetime.now(timezone.utc).isoformat()
    rows = []
    for ticker, data in ohlc_data.items():
        ohlc = data.get("ohlc") or {}
        prev_close = ohlc.get("close")  # close from prior session
        if prev_close is None or prev_close <= 0:
            continue
        rows.append({
            "ticker": ticker,
            "last_price": float(prev_close),
            "ts": now_iso,
        })

    log(f"  Payload built: {len(rows)} rows with prev_close")

    if len(rows) < 1000:
        log(f"  WARNING: Only {len(rows)} rows — below expected 1300")

    # Step 4: UPSERT to equity_intraday_last
    try:
        for i in range(0, len(rows), 500):
            chunk = rows[i:i + 500]
            sb.table("equity_intraday_last").upsert(
                chunk, on_conflict="ticker"
            ).execute()
            log(f"  upserted chunk {i // 500 + 1}: {len(chunk)} rows")
    except Exception as e:
        log(f"  ERROR: upsert failed: {e}")
        return xlog.exit_with_reason("DATA_ERROR", exit_code=1, error_message=str(e)[:1000],
                                     notes=f"payload {len(rows)} rows; upsert failed")

    xlog.record_write("equity_intraday_last", len(rows))
    finished_at = datetime.now(timezone.utc)
    log(f"Done. Wrote {len(rows)} rows in {(finished_at - started_at).total_seconds():.1f}s")
    return xlog.complete(notes=f"{len(rows)} rows; floor {EXPECTED_MIN_ROWS}")

if __name__ == "__main__":
    raise SystemExit(main())
