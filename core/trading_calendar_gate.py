"""
core.trading_calendar_gate — shared holiday gate.

Single source of holiday-gating logic for every MERDIAN entrypoint, replacing
the ~30 bespoke inline `is_open` checks scattered across runners (and the
fix_*_holiday_gate.py archaeology). Reads the `trading_calendar` table.

Canonical usage (instrumented entrypoint):

    from core.execution_log import ExecutionLog
    from core.trading_calendar_gate import assert_trading_day_or_exit

    log = ExecutionLog(script_name="...", expected_writes={...})
    assert_trading_day_or_exit(log)        # exits via HOLIDAY_GATE if closed
    ... do work ...

Uninstrumented usage (orchestrators, scripts without ExecutionLog):

    from core.trading_calendar_gate import is_trading_day_today
    if not is_trading_day_today():
        log_message("[HOLIDAY GATE] Market closed -- exiting.")
        return 0

FAIL-OPEN by contract: any error (no creds, network, non-200, no row,
exception) returns True / allows the run. A gate can only ever SKIP a
confirmed-closed day, never BLOCK a real session on a calendar hiccup.
Correctness of the *closure* decision therefore depends entirely on the
trading_calendar table being correct (TD-S60-NEW-2: the table was wrong;
fixed at source in trading_calendar.json).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.execution_log import ExecutionLog

_IST = ZoneInfo("Asia/Kolkata")
_TABLE = "trading_calendar"


def _today_ist_iso() -> str:
    return datetime.now(timezone.utc).astimezone(_IST).date().isoformat()


def is_trading_day_today() -> bool:
    """True if today (IST) is an open trading day. FAIL-OPEN on any error.

    A day is closed only when the calendar explicitly says so: a row exists
    with is_open=false OR open_time is null. Missing row -> allow (fail-open).
    """
    return is_trading_day(_today_ist_iso())


def is_trading_day(trade_date_iso: str) -> bool:
    """True if `trade_date_iso` (YYYY-MM-DD, IST) is an open trading day.
    FAIL-OPEN: returns True on any credential/network/parse error."""
    try:
        # Lazy import so this module is import-safe even if core.config is
        # mid-init; mirrors the rest of core/ using SupabaseClient.
        from core.supabase_client import SupabaseClient

        client = SupabaseClient()
        rows = client.select(
            _TABLE,
            columns="is_open,open_time",
            filters={"trade_date": f"eq.{trade_date_iso}"},
            limit=1,
        )
        if not rows:
            return True  # no row -- allow run (fail-open)
        row = rows[0]
        return bool(row.get("is_open", True)) and row.get("open_time") is not None
    except Exception as e:  # noqa: BLE001 -- fail-open is the contract
        print(f"[trading_calendar_gate] check failed ({e}); failing open (allow run)",
              file=sys.stderr, flush=True)
        return True


def assert_trading_day_or_exit(log: "Optional[ExecutionLog]" = None) -> None:
    """If today is closed, exit the process cleanly.

    With an ExecutionLog: exits via SystemExit(log.exit_with_reason("HOLIDAY_GATE"))
    so the run is recorded with the canonical exit reason. Without one: prints a
    [HOLIDAY GATE] line and raises SystemExit(0). No-op on an open day.
    """
    if is_trading_day_today():
        return
    if log is not None:
        raise SystemExit(log.exit_with_reason("HOLIDAY_GATE"))
    print("[HOLIDAY GATE] Market closed today -- exiting (no work).",
          file=sys.stderr, flush=True)
    raise SystemExit(0)
