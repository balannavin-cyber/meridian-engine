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

DESIGN: this module is deliberately self-sufficient -- it calls load_dotenv()
itself and reads os.getenv + raw requests, rather than routing through
core.config.get_settings() / SupabaseClient. Two reasons:
  1. core.config hardcodes a Windows BASE_DIR and loads .env from there, so on
     AWS it finds nothing (TD-S60-NEW-5) -- SupabaseClient would raise on missing
     env and the gate would silently fail-open every day (a no-op gate).
  2. Mirrors the proven inline gate in build_market_spot_session_markers.py /
     the S60 orchestrator gate, which work precisely because they self-load.

FAIL-OPEN by contract: any error (no creds, network, non-200, no row,
exception) returns True / allows the run. A gate can only ever SKIP a
confirmed-closed day, never BLOCK a real session on a calendar hiccup.
Correctness of the *closure* decision depends on the trading_calendar table
being correct (TD-S60-NEW-2: fixed at source in trading_calendar.json).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Optional, TYPE_CHECKING

import requests

try:
    from dotenv import load_dotenv as _load_dotenv
except ImportError:  # pragma: no cover
    _load_dotenv = None

if TYPE_CHECKING:
    from core.execution_log import ExecutionLog

_IST = ZoneInfo("Asia/Kolkata")
_TABLE = "trading_calendar"


def _today_ist_iso() -> str:
    return datetime.now(timezone.utc).astimezone(_IST).date().isoformat()


def _creds() -> tuple[str, str]:
    """Resolve Supabase URL + key, loading .env from the cwd/repo if needed.
    Self-sufficient: does NOT depend on core.config (which hardcodes a Windows
    path and finds nothing on AWS -- TD-S60-NEW-5)."""
    url = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if (not url or not key) and _load_dotenv is not None:
        _load_dotenv()  # default search: cwd and parents
        url = os.getenv("SUPABASE_URL", "").rstrip("/")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    return url, key


def is_trading_day_today() -> bool:
    """True if today (IST) is an open trading day. FAIL-OPEN on any error."""
    return is_trading_day(_today_ist_iso())


def is_trading_day(trade_date_iso: str) -> bool:
    """True if `trade_date_iso` (YYYY-MM-DD, IST) is an open trading day.
    A day is closed only when the calendar explicitly says so: a row exists
    with is_open=false OR open_time null. Missing row / any error -> allow."""
    try:
        url, key = _creds()
        if not url or not key:
            print("[trading_calendar_gate] no Supabase creds; failing open (allow run)",
                  file=sys.stderr, flush=True)
            return True
        r = requests.get(
            f"{url}/rest/v1/{_TABLE}",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            params={"trade_date": f"eq.{trade_date_iso}", "select": "is_open,open_time"},
            timeout=10,
        )
        if r.status_code == 200:
            rows = r.json()
            if rows:
                row = rows[0]
                return bool(row.get("is_open", True)) and row.get("open_time") is not None
            # _RESOLVE_ABSENCE_S68 -- no row: the seeder only writes OPEN days
            # ("absence == closed" doctrine), so allowing here made every unseeded
            # weekend / NSE holiday read as a trading day. Resolve absence against
            # the V18E rule engine (the seeder's own source of truth) instead of
            # guessing. Weekend/holiday -> closed; Muhurat special session -> open.
            # Fail-open contract preserved: ONLY a computed is_open=False returns
            # False; any engine error falls through to the allow below.
            return _resolve_absent_day(trade_date_iso)
        return True  # non-200 -> allow run (fail-open)
    except Exception as e:  # noqa: BLE001 -- fail-open is the contract
        print(f"[trading_calendar_gate] check failed ({e}); failing open (allow run)",
              file=sys.stderr, flush=True)
        return True


def _resolve_absent_day(trade_date_iso: str) -> bool:
    """_RESOLVE_ABSENCE_S68 -- decide a date with NO trading_calendar row.

    Defers to the V18E rule engine (trading_calendar.get_session_config_for_date),
    which encodes: weekend -> closed, NSE holiday (trading_calendar.json) -> closed,
    special session (muhurat) -> OPEN, else open. This is the same authority
    seed_trading_calendar.py uses, so gate and seeder can no longer disagree.

    Import is lazy and every failure path returns True: the gate must never block a
    live session because the rule engine could not be loaded or a date could not be
    parsed. Only a confidently-computed closure returns False.
    """
    try:
        from trading_calendar import get_session_config_for_date
        cfg = get_session_config_for_date(trade_date_iso)
        if not cfg.is_open:
            print(f"[trading_calendar_gate] {trade_date_iso}: no row; rule engine says "
                  f"CLOSED ({getattr(cfg, 'notes', 'closed')})",
                  file=sys.stderr, flush=True)
            return False
        return True
    except Exception as e:  # noqa: BLE001 -- fail-open is the contract
        print(f"[trading_calendar_gate] {trade_date_iso}: no row and rule engine "
              f"unavailable ({e}); failing open (allow run)",
              file=sys.stderr, flush=True)
        return True


def previous_trading_day(from_date_iso: str,
                         max_lookback: int = 10) -> "tuple[str, str]":
    """S82-ENH129 — the most recent OPEN trading day STRICTLY BEFORE from_date_iso.

    Returns (date_iso, provenance). Provenance is one of:
        "rule-engine"          the V18E engine computed the answer
        "fail-open:import"     the engine could not be imported
        "fail-open:error"      the engine raised on a candidate date
        "fail-open:exhausted"  max_lookback days produced no open day

    OFFLINE BY CONSTRUCTION — this makes NO database query. It consults
    trading_calendar.json through the V18E rule engine, which is the seeder's own
    source of truth (Rule 18: the table is seeded FROM the json) and the same
    authority _resolve_absent_day already defers to. Two things follow: the
    resolver works with no credentials and no network, and the path exercised by
    an offline test IS the path that runs in cron.

    FAIL-OPEN, and the caller is told so. Every failure path returns the previous
    CALENDAR day with a fail-open provenance rather than raising. That inherits
    the gate's contract, and it is wrong in one specific way the caller must
    handle: on a rule-engine outage this can name a closed day, and the audit of
    that day will report failures that are artefacts of the outage, not data loss.
    That is loud rather than silent and self-corrects the next day — but a caller
    that does not LOG the provenance turns it back into a silent lie.
    """
    from datetime import date as _date, timedelta as _td

    d0 = _date.fromisoformat(from_date_iso)
    fallback = (d0 - _td(days=1)).isoformat()

    try:
        from trading_calendar import get_session_config_for_date
    except Exception as e:  # noqa: BLE001 -- fail-open is the contract
        print(f"[trading_calendar_gate] previous_trading_day({from_date_iso}): rule "
              f"engine unavailable ({e}); falling back to {fallback}",
              file=sys.stderr, flush=True)
        return fallback, "fail-open:import"

    for back in range(1, max_lookback + 1):
        cand = (d0 - _td(days=back)).isoformat()
        try:
            _cfg = get_session_config_for_date(cand)
            # S82 special-session exclusion -- a special session (Muhurat) is an
            # OPEN day, but a ~15-minute evening one. It must never become the
            # audit target: every row-count floor downstream is calibrated for a
            # ~6-hour session, so auditing it would FAIL for a reason that is not
            # data loss.
            #
            # This is deliberately defensive. As measured at S82 the engine checks
            # Rule 1 (weekend) BEFORE Rule 3 (special session) and returns early,
            # so a Sunday Muhurat already reads is_open=False and is skipped by
            # accident (TD-S82-NEW-4). This clause is what keeps the resolver
            # correct AFTER that engine defect is fixed, so the two can be
            # repaired independently. It reads the PUBLIC SessionConfig contract,
            # never a private helper.
            if _cfg.is_open and not getattr(_cfg, "special_session", False):
                return cand, "rule-engine"
        except Exception as e:  # noqa: BLE001 -- fail-open is the contract
            print(f"[trading_calendar_gate] previous_trading_day({from_date_iso}): "
                  f"engine raised on {cand} ({e}); falling back to {fallback}",
                  file=sys.stderr, flush=True)
            return fallback, "fail-open:error"

    print(f"[trading_calendar_gate] previous_trading_day({from_date_iso}): no open day "
          f"in {max_lookback} days; falling back to {fallback}",
          file=sys.stderr, flush=True)
    return fallback, "fail-open:exhausted"


def assert_trading_day_or_exit(log: "Optional[ExecutionLog]" = None) -> None:
    """If today is closed, exit the process cleanly.

    With an ExecutionLog: SystemExit(log.exit_with_reason("HOLIDAY_GATE")) so the
    run is recorded with the canonical exit reason. Without one: print a
    [HOLIDAY GATE] line and SystemExit(0). No-op on an open day."""
    if is_trading_day_today():
        return
    if log is not None:
        raise SystemExit(log.exit_with_reason("HOLIDAY_GATE"))
    print("[HOLIDAY GATE] Market closed today -- exiting (no work).",
          file=sys.stderr, flush=True)
    raise SystemExit(0)
