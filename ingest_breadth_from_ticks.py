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

Instrumentation (added Session 7, 2026-04-23; S100_R40_BREADTH, ruling S100-I):
  One script_execution_log row per invocation through core.execution_log.ExecutionLog (was a
  hand-rolled insert with no status / kind and host hard-coded "local" while the job runs on AWS).
  contract_met = True iff coverage_pct >= MIN_COVERAGE_PCT AND market_breadth_intraday write succeeded.
  S100: not a trading day -> HOLIDAY_GATE exit 0 (shared calendar gate, fail-open); no EQ ticks in the
  window -> nothing written, SKIPPED_NO_INPUT exit 0 (S99-H precedent): until S100 every pre-feed minute
  (08:30-09:10 IST), every feed-down day and every holiday wrote a zero-coverage history row and exit 1.
  Cron starts this every minute and a run takes ~160-180 s, so ~3 runs overlap; that is LEFT AS IS here:
  scripts/eod_health_check.py:119 floors market_breadth_intraday at 350 rows/day, which only the
  overlapping runs reach. The fix is a faster run, not a lock (tracker 2.2 R40 residual).
"""
from __future__ import annotations
import os
import sys
from datetime import datetime, timedelta, timezone, date
from pathlib import Path

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


def _trading_day() -> bool:
    """Shared gate (CLAUDE.md rule 18), fail-open as that module is: a calendar error never
    silences a live session."""
    try:
        from core.trading_calendar_gate import is_trading_day_today
        return is_trading_day_today()
    except Exception as e:  # noqa: BLE001
        log(f"  WARN: calendar gate unavailable ({e}); proceeding")
        return True


def main() -> int:
    from core.execution_log import ExecutionLog
    xlog = ExecutionLog(
        script_name="ingest_breadth_from_ticks.py",
        expected_writes={"market_breadth_intraday": 1, "breadth_intraday_history": 1},
        notes=f"tick_window={TICK_WINDOW_MINUTES}m min_coverage={MIN_COVERAGE_PCT}%",
    )
    if not _trading_day():
        log("Not a trading day - nothing to compute")
        return xlog.exit_with_reason("HOLIDAY_GATE", exit_code=0)

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

    # Step 1: Get latest LTP per EQ stock.
    # S102_R40_LATEST_VIEW: one row per stock from public.v_market_ticks_eq_latest (newest non-NULL
    # last_price per COALESCE(NULLIF(tradingsymbol,''), symbol), window = 10 min, the same key and the
    # same "first tick seen in ts-desc order" this loop used to compute in Python). The old read paged
    # every EQ tick in the window by offset (~161,000 rows, ~162 calls, 140-176 s per run, so ~3 runs
    # overlapped every minute; measured 2026-10-26..28). Keyset paging on sym: 1,313 rows = 2 calls.
    # The view's window is fixed at 10 minutes in its DDL and must equal TICK_WINDOW_MINUTES.
    log(f"Fetching latest EQ LTP per stock (v_market_ticks_eq_latest, {TICK_WINDOW_MINUTES} min)...")
    latest_ltp: dict[str, float] = {}
    page_size = 1000
    last_sym = None
    try:
        while True:
            q = sb.table("v_market_ticks_eq_latest").select("sym,last_price,ts").order("sym")
            if last_sym is not None:
                q = q.gt("sym", last_sym)
            r = q.limit(page_size).execute()
            rows = r.data or []
            for row in rows:
                sym, ltp = row.get("sym"), row.get("last_price")
                if sym and ltp is not None and sym not in latest_ltp:
                    latest_ltp[sym] = float(ltp)
            if len(rows) < page_size:
                break
            last_sym = rows[-1]["sym"]
    except Exception as e:
        log(f"  ERROR: latest-tick read failed: {e}")
        return xlog.exit_with_reason(
            "DATA_ERROR", exit_code=1, error_message=str(e)[:1000],
            notes="v_market_ticks_eq_latest read failed; nothing written",
        )
    all_ticks = latest_ltp  # the no-input test below reads "no stock has a tick in the window"

    if not all_ticks:
        log("  No EQ ticks found - WebSocket not running yet, or down. Nothing written.")
        return xlog.exit_with_reason(
            "SKIPPED_NO_INPUT", exit_code=0,
            notes=f"No EQ ticks in the last {TICK_WINDOW_MINUTES} min - feed not started or down; nothing written",
        )

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
    if _write_history(sb, now_utc, now_ist.date(),
                      advances, declines, up_4pct, down_4pct, breadth_score, coverage_pct):
        wrote_history = 1
        xlog.record_write("breadth_intraday_history", 1)

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
            xlog.record_write("market_breadth_intraday", 1)
        except Exception as e:
            log(f"  WARNING: market_breadth_intraday write failed: {e}")
            return xlog.exit_with_reason(
                "DATA_ERROR", exit_code=2, error_message=str(e)[:1000],
                notes=f"adv={advances} dec={declines} cov={coverage_pct:.1f}%",
            )
    else:
        log(f"  Coverage {coverage_pct:.1f}% < {MIN_COVERAGE_PCT}% - skipping market_breadth_intraday upsert")

    log("Done.")

    # Telemetry: contract met only if BOTH coverage threshold met AND intraday write succeeded
    contract_met = (coverage_pct >= MIN_COVERAGE_PCT) and (wrote_intraday == 1)
    notes = f"adv={advances} dec={declines} unch={unchanged} cov={coverage_pct:.1f}% regime={regime}"
    if contract_met:
        return xlog.complete(notes=notes)
    return xlog.exit_with_reason("SKIPPED_NO_INPUT", exit_code=0, notes=notes)


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
        return True
    except Exception as e:
        log(f"  WARNING: breadth_intraday_history write failed: {e}")
        return False


if __name__ == "__main__":
    raise SystemExit(main())