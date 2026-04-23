#!/usr/bin/env python3
"""
ingest_breadth_from_ticks.py
==============================
Computes market breadth from Zerodha WebSocket tick data in market_ticks.

Replaces ingest_breadth_intraday_local.py (Dhan REST - retired 2026-04-16).

Algorithm:
  1. Fetch latest LTP per EQ stock from market_ticks (last 10 minutes)
  2. Fetch prior day close from equity_intraday_last (prev session)
  3. Compute: advance if LTP > prev_close, decline if LTP < prev_close
  4. Write to:
     - market_breadth_intraday (append - view latest_market_breadth_intraday auto-reflects newest row)
     - breadth_intraday_history (append - dashboard graph, separate schema)

Run: called by run_option_snapshot_intraday_runner.py every 5 min cycle (non-blocking)

Instrumentation (added Session 7, 2026-04-23):
  Writes one row to script_execution_log per invocation.
  contract_met = True iff coverage_pct >= MIN_COVERAGE_PCT AND market_breadth_intraday write succeeded.
  Host tagged "local" (this is where the runner schedules this script).
"""
from __future__ import annotations
import os
import sys
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from supabase import create_client

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

IST = timezone(timedelta(hours=5, minutes=30))

# How far back to look for latest tick per stock
TICK_WINDOW_MINUTES = 10

# Minimum coverage to write latest_market_breadth_intraday
MIN_COVERAGE_PCT = 50.0  # Lower than Dhan (was 95%) - WebSocket is more reliable


def log(msg: str) -> None:
    ts = datetime.now(IST).strftime("%H:%M:%S IST")
    print(f"[{ts}] {msg}", flush=True)


def _write_exec_log(sb, started_at, invocation_id, contract_met, actual_writes,
                    exit_code, exit_reason, error_message=None, notes=None):
    """Write one row to script_execution_log. Never raises - telemetry failure
    must not crash the pipeline."""
    try:
        finished_at = datetime.now(timezone.utc)
        sb.table("script_execution_log").insert({
            "id": str(uuid4()),
            "script_name": "ingest_breadth_from_ticks.py",
            "invocation_id": invocation_id,
            "host": "local",
            "symbol": None,
            "trade_date": datetime.now(IST).date().isoformat(),
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_ms": int((finished_at - started_at).total_seconds() * 1000),
            "exit_code": exit_code,
            "exit_reason": exit_reason,
            "contract_met": contract_met,
            "expected_writes": {"market_breadth_intraday": 1, "breadth_intraday_history": 1},
            "actual_writes": actual_writes,
            "notes": notes or f"tick_window={TICK_WINDOW_MINUTES}m min_coverage={MIN_COVERAGE_PCT}%",
            "error_message": error_message,
            "git_sha": os.environ.get("GIT_SHA", ""),
        }).execute()
    except Exception as e:
        log(f"  WARN: script_execution_log write failed: {e}")


def main() -> int:
    started_at = datetime.now(timezone.utc)
    invocation_id = str(uuid4())

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    now_utc = datetime.now(timezone.utc)
    now_ist = datetime.now(IST)
    window_start = (now_utc - timedelta(minutes=TICK_WINDOW_MINUTES)).isoformat()

    # Track actual writes across the invocation for telemetry
    wrote_history = 0
    wrote_intraday = 0

    log("=" * 60)
    log("ingest_breadth_from_ticks - Zerodha WebSocket breadth")
    log("=" * 60)

    # Step 1: Get latest LTP per EQ stock from market_ticks
    log(f"Fetching EQ ticks from last {TICK_WINDOW_MINUTES} minutes...")

    # Paginate to get all EQ ticks in window
    all_ticks = []
    offset = 0
    page_size = 1000
    while True:
        r = sb.table("market_ticks").select(
            "symbol,tradingsymbol,last_price,ts"
        ).eq(
            "instrument_type", "EQ"
        ).gte(
            "ts", window_start
        ).order("ts", desc=True).range(offset, offset + page_size - 1).execute()

        if not r.data:
            break
        all_ticks.extend(r.data)
        if len(r.data) < page_size:
            break
        offset += page_size

    log(f"  Total EQ ticks in window: {len(all_ticks)}")

    if not all_ticks:
        log("  No EQ ticks found - WebSocket may not be running or market closed")
        log("  Writing zero-coverage row to breadth_intraday_history")
        _write_history(sb, now_utc, now_ist.date(), 0, 0, 0, 0, 0, 0.0)
        wrote_history = 1
        _write_exec_log(
            sb, started_at, invocation_id,
            contract_met=False,
            actual_writes={"market_breadth_intraday": 0, "breadth_intraday_history": wrote_history},
            exit_code=1,
            exit_reason="SKIPPED_NO_INPUT",
            notes="No EQ ticks in window - WebSocket down or market closed",
        )
        return 1

    # Get latest tick per symbol (already ordered desc by ts)
    latest_ltp: dict[str, float] = {}
    for tick in all_ticks:
        sym = tick.get("tradingsymbol") or tick.get("symbol", "")
        if sym and sym not in latest_ltp:
            ltp = tick.get("last_price")
            if ltp is not None:
                latest_ltp[sym] = float(ltp)

    log(f"  Unique EQ symbols with ticks: {len(latest_ltp)}")

    # Step 2: Get previous close from equity_intraday_last
    log("Fetching previous closes from equity_intraday_last...")

    prev_closes: dict[str, float] = {}
    # equity_intraday_last stores ticker as 'NSE:SYMBOL'
    # We need to match against our symbol names

    offset = 0
    while True:
        r = sb.table("equity_intraday_last").select(
            "ticker,last_price"
        ).range(offset, offset + page_size - 1).execute()

        if not r.data:
            break
        for row in r.data:
            ticker = row.get("ticker", "")
            # Strip 'NSE:' prefix
            sym = ticker.replace("NSE:", "").replace("BSE:", "")
            price = row.get("last_price")
            if sym and price:
                prev_closes[sym] = float(price)

        if len(r.data) < page_size:
            break
        offset += page_size

    log(f"  Previous closes available: {len(prev_closes)}")

    # Step 3: Compute breadth
    advances = 0
    declines = 0
    unchanged = 0
    up_4pct = 0
    down_4pct = 0
    matched = 0

    for sym, ltp in latest_ltp.items():
        prev = prev_closes.get(sym)
        if prev is None or prev <= 0:
            continue
        matched += 1
        chg_pct = (ltp - prev) / prev * 100

        if chg_pct > 0.05:  # Small threshold to avoid flat stocks
            advances += 1
            if chg_pct >= 4.0:
                up_4pct += 1
        elif chg_pct < -0.05:
            declines += 1
            if chg_pct <= -4.0:
                down_4pct += 1
        else:
            unchanged += 1

    total = advances + declines + unchanged
    coverage_pct = (matched / len(latest_ltp) * 100) if latest_ltp else 0.0

    # Breadth score: -100 to +100
    if total > 0:
        breadth_score = round((advances - declines) / total * 100, 1)
    else:
        breadth_score = 0

    # Breadth regime
    if breadth_score >= 20:
        regime = "BULLISH"
    elif breadth_score <= -20:
        regime = "BEARISH"
    else:
        regime = "NEUTRAL"

    log(f"  Advances: {advances} | Declines: {declines} | Unchanged: {unchanged}")
    log(f"  Up 4%+: {up_4pct} | Down 4%+: {down_4pct}")
    log(f"  Score: {breadth_score} | Regime: {regime} | Coverage: {coverage_pct:.1f}%")

    # Step 4: Write to breadth_intraday_history (always)
    _write_history(sb, now_utc, now_ist.date(),
                   advances, declines, up_4pct, down_4pct, breadth_score, coverage_pct)
    wrote_history = 1

    # Step 5: Write to latest_market_breadth_intraday if coverage OK
    if coverage_pct >= MIN_COVERAGE_PCT and total > 0:
        payload = {
            "ts": now_utc.isoformat(),
            "universe_id": "excel_v1",
            "universe_count": len(latest_ltp),
            "advances": advances,
            "declines": declines,
            "up_4pct": up_4pct,
            "down_4pct": down_4pct,
            "pct_above_10dma": None,  # Not computed from ticks
            "pct_above_20dma": None,
            "pct_above_40dma": None,
            "pct_10gt20": None,
            "pct_20gt40": None,
            "breadth_score": breadth_score,
            "breadth_regime": regime,
        }
        try:
            sb.table("market_breadth_intraday").upsert(
                payload, on_conflict="ts,universe_id"
            ).execute()
            log(f"  Written to market_breadth_intraday: {regime} (view auto-reflects latest)")
            wrote_intraday = 1
        except Exception as e:
            log(f"  WARNING: market_breadth_intraday write failed: {e}")
            _write_exec_log(
                sb, started_at, invocation_id,
                contract_met=False,
                actual_writes={"market_breadth_intraday": 0, "breadth_intraday_history": wrote_history},
                exit_code=2,
                exit_reason="DATA_ERROR",
                error_message=str(e),
                notes=f"adv={advances} dec={declines} cov={coverage_pct:.1f}%",
            )
            return 2
    else:
        log(f"  Coverage {coverage_pct:.1f}% < {MIN_COVERAGE_PCT}% - skipping market_breadth_intraday upsert")

    log("Done.")

    # Telemetry: contract met only if BOTH coverage threshold met AND intraday write succeeded
    contract_met = (coverage_pct >= MIN_COVERAGE_PCT) and (wrote_intraday == 1)
    exit_reason = "SUCCESS" if contract_met else "SKIPPED_NO_INPUT"
    _write_exec_log(
        sb, started_at, invocation_id,
        contract_met=contract_met,
        actual_writes={"market_breadth_intraday": wrote_intraday, "breadth_intraday_history": wrote_history},
        exit_code=0,
        exit_reason=exit_reason,
        notes=f"adv={advances} dec={declines} unch={unchanged} cov={coverage_pct:.1f}% regime={regime}",
    )
    return 0


def _write_history(sb, ts_utc, trade_date, advances, declines,
                   up_4pct, down_4pct, breadth_score, coverage_pct):
    """Append row to breadth_intraday_history."""
    try:
        sb.table("breadth_intraday_history").insert({
            "ts": ts_utc.isoformat(),
            "trade_date": str(trade_date),
            "advances": advances,
            "declines": declines,
            "up_4pct": up_4pct,
            "down_4pct": down_4pct,
            "breadth_score": breadth_score,
            "coverage_pct": round(coverage_pct, 2),
        }).execute()
        log(f"  Appended to breadth_intraday_history")
    except Exception as e:
        log(f"  WARNING: breadth_intraday_history write failed: {e}")


if __name__ == "__main__":
    raise SystemExit(main())