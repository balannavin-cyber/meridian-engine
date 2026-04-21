"""
core.execution_log — Write-contract helper.

Every production script declares a write contract at startup (which tables
it expects to write, with what row counts) and records actual writes as
they happen. On exit — normal, exceptional, or crash — a single row is
written to public.script_execution_log with contract_met computed.

Usage
-----
    from core.execution_log import ExecutionLog

    log = ExecutionLog(
        script_name="capture_spot_1m.py",
        expected_writes={
            "market_spot_snapshots": 2,
            "hist_spot_bars_1m": 2,
        },
        symbol=None,   # None for multi-symbol scripts
    )

    # Optional early exit cases: log.exit_with_reason returns exit_code.
    if is_market_holiday():
        raise SystemExit(log.exit_with_reason("HOLIDAY_GATE"))

    # Do work. Record writes as they land.
    rows = write_spot_snapshots()
    log.record_write("market_spot_snapshots", rows)

    rows = write_1m_bars()
    log.record_write("hist_spot_bars_1m", rows)

    # Normal exit path.
    raise SystemExit(log.complete())

Semantics
---------
* An initial row is INSERTed at construction with exit_reason='RUNNING',
  contract_met=NULL. The unique invocation_id is the handle for later UPDATE.
* record_write(table, n) increments an in-memory counter. No per-write
  round-trip to Supabase.
* complete() / exit_with_reason() UPDATEs the row with final fields and
  computes contract_met.
* atexit hook: if the process exits without calling complete() or
  exit_with_reason(), a finaliser records exit_reason='CRASH' with the
  current actual_writes tally.
* Signal handlers (SIGINT/SIGTERM) are NOT installed by ExecutionLog itself
  — callers who want graceful-shutdown semantics install their own, which
  should ultimately call sys.exit and let atexit drain.

Design notes
------------
* Writes are best-effort. If Supabase is unreachable at finalize, we log a
  warning to stderr and continue. The script's actual work is more important
  than its audit trail.
* git_sha is captured once at init via subprocess. Failure is silent.
* Dry-run: pass dry_run=True. This does NOT redirect writes to a shadow
  schema by itself — that is the caller's responsibility. What it does is
  force exit_reason='DRY_RUN' at completion regardless of writes, and
  tag the row in notes.
"""
from __future__ import annotations

import atexit
import json
import os
import subprocess
import sys
import traceback
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv


_IST = ZoneInfo("Asia/Kolkata")

# Load .env once at module import. Callers can reload later via live config
# (Session 5) or per-cycle load (ENH-68). This module just needs credentials
# to persist a row to Supabase at finalize.
load_dotenv()

_SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
_SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


# Valid exit reasons. Mirrors the CHECK constraint in 20260420_script_execution_log.sql.
VALID_EXIT_REASONS = frozenset({
    "SUCCESS",
    "HOLIDAY_GATE",
    "OFF_HOURS",
    "TOKEN_EXPIRED",
    "DATA_ERROR",
    "SKIPPED_NO_INPUT",
    "DEPENDENCY_MISSING",
    "CRASH",
    "TIMEOUT",
    "RUNNING",
    "DRY_RUN",
})


def _git_sha() -> str:
    """Best-effort HEAD SHA. Returns empty string on any failure."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=3,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return ""


def _today_ist() -> date:
    return datetime.now(_IST).date()


def _detect_host() -> str:
    """Infer where we are running. Dumb heuristic; can be made richer later."""
    # Check a couple of env vars an operator can set to override.
    override = os.environ.get("MERDIAN_HOST")
    if override:
        return override
    # Cheap default: Windows -> local; linux with /home/ssm-user -> aws; else unknown.
    if os.name == "nt":
        return "local"
    if os.path.isdir("/home/ssm-user/meridian-engine"):
        return "aws"
    if os.path.isdir("/home/ubuntu/meridian-alpha"):
        return "meridian_alpha"
    return "unknown"


class ExecutionLog:
    """Single-invocation write-contract tracker. See module docstring."""

    def __init__(
        self,
        script_name: str,
        expected_writes: Optional[Dict[str, int]] = None,
        symbol: Optional[str] = None,
        dry_run: bool = False,
        notes: Optional[str] = None,
    ):
        self.script_name = script_name
        self.invocation_id: UUID = uuid4()
        self.expected: Dict[str, int] = dict(expected_writes or {})
        self.actual: Dict[str, int] = {}
        self.symbol = symbol
        self.dry_run = dry_run
        self.notes = notes

        self.host = _detect_host()
        self.git_sha = _git_sha()
        self.trade_date = _today_ist()
        self.started_at = datetime.now(timezone.utc)

        self._finalised = False
        self._headers = {
            "apikey": _SUPABASE_KEY,
            "Authorization": f"Bearer {_SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }

        # Insert opening row with exit_reason='RUNNING', contract_met=NULL.
        self._insert_opening_row()

        # Install crash hook. Idempotent via _finalised flag.
        atexit.register(self._atexit_finalise)

    # ── Public API ──────────────────────────────────────────────────────────

    def record_write(self, table: str, n_rows: int) -> None:
        """Accumulate actual write count for a table. Cheap, in-memory only."""
        if n_rows < 0:
            raise ValueError(f"record_write: n_rows must be >=0, got {n_rows}")
        self.actual[table] = self.actual.get(table, 0) + int(n_rows)

    def set_symbol(self, symbol: str | None) -> None:
        """
        Update the symbol on this invocation's log row.

        For run_id-contract scripts (compute_gamma_metrics_local.py,
        compute_volatility_metrics_local.py, build_momentum_features_local.py)
        that only discover symbol after the first Supabase read. Best-effort:
        failures are logged to stderr but never raised -- the instrumentation
        layer must not break the calling script.

        Safe to call multiple times. Safe to call with None (no-op).
        Post-finalise calls are silently ignored.
        """
        if self._finalised:
            return
        if symbol is None:
            return
        self.symbol = symbol

        if not _SUPABASE_URL or not _SUPABASE_KEY:
            return

        try:
            r = requests.patch(
                f"{_SUPABASE_URL}/rest/v1/script_execution_log",
                headers=self._headers,
                params={"invocation_id": f"eq.{self.invocation_id}"},
                json={"symbol": symbol},
                timeout=10,
            )
            if r.status_code >= 300:
                self._warn(
                    f"set_symbol PATCH failed: status={r.status_code} "
                    f"body={r.text[:200]}"
                )
        except Exception as e:
            self._warn(f"set_symbol PATCH exception: {e}")

    def complete(self, notes: Optional[str] = None) -> int:
        """Normal completion path. Computes contract_met, writes final row,
        returns exit code (0). Caller typically does: sys.exit(log.complete())."""
        reason = "DRY_RUN" if self.dry_run else "SUCCESS"
        return self._finalise(exit_reason=reason, exit_code=0, notes=notes)

    def exit_with_reason(
        self,
        reason: str,
        exit_code: int = 0,
        notes: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> int:
        """Explicit early exit with a known reason (e.g. HOLIDAY_GATE, TOKEN_EXPIRED).
        Returns exit_code so callers can: sys.exit(log.exit_with_reason('HOLIDAY_GATE'))."""
        if reason not in VALID_EXIT_REASONS:
            # We still record but mark as CRASH, since an invalid reason from a
            # caller is a bug we want to see in the logs, not suppress.
            error_message = (
                f"ExecutionLog: caller passed invalid exit_reason={reason!r}; "
                f"recording as CRASH. Original error_message: {error_message!r}"
            )
            reason = "CRASH"
            exit_code = max(exit_code, 1)
        return self._finalise(
            exit_reason=reason,
            exit_code=exit_code,
            notes=notes,
            error_message=error_message,
        )

    # ── Internals ───────────────────────────────────────────────────────────

    def _payload_common(self) -> Dict[str, Any]:
        return {
            "invocation_id": str(self.invocation_id),
            "script_name": self.script_name,
            "host": self.host,
            "symbol": self.symbol,
            "trade_date": self.trade_date.isoformat(),
            "started_at": self.started_at.isoformat(),
            "expected_writes": self.expected,
            "git_sha": self.git_sha or None,
            "notes": self.notes,
        }

    def _insert_opening_row(self) -> None:
        if not _SUPABASE_URL or not _SUPABASE_KEY:
            self._warn("No Supabase credentials; execution_log disabled for this run")
            self._finalised = True  # short-circuit everything
            return
        payload = self._payload_common()
        payload.update({
            "exit_reason": "RUNNING",
            "actual_writes": {},
            "contract_met": None,
        })
        try:
            r = requests.post(
                f"{_SUPABASE_URL}/rest/v1/script_execution_log",
                headers=self._headers,
                json=payload,
                timeout=10,
            )
            if r.status_code >= 300:
                self._warn(
                    f"Opening-row insert failed: status={r.status_code} "
                    f"body={r.text[:200]}"
                )
        except Exception as e:
            self._warn(f"Opening-row insert exception: {e}")

    def _compute_contract_met(self, exit_code: int) -> bool:
        if exit_code != 0:
            return False
        for table, n_expected in self.expected.items():
            if self.actual.get(table, 0) < n_expected:
                return False
        return True

    def _finalise(
        self,
        exit_reason: str,
        exit_code: int,
        notes: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> int:
        if self._finalised:
            return exit_code
        self._finalised = True

        finished_at = datetime.now(timezone.utc)
        duration_ms = int((finished_at - self.started_at).total_seconds() * 1000)

        # HOLIDAY_GATE / OFF_HOURS / SKIPPED_NO_INPUT / DRY_RUN are "no writes
        # expected" scenarios — contract_met follows naturally:
        #   - if expected is empty OR all expectations met, contract_met=True
        #   - if expected is non-empty and not met, contract_met=False
        # This means HOLIDAY_GATE with empty expected_writes reads True.
        # SUCCESS with partial writes reads False. Exactly what we want.
        contract_met = self._compute_contract_met(exit_code)

        # For pure-gate reasons, contract semantics mean "we intentionally
        # did not run — don't flag as failure". If expected_writes was empty,
        # contract_met is True (nothing expected, nothing written).
        # If caller declared expected_writes AND hit a gate, contract_met=False
        # which is correct: the gate triggered unexpectedly given contract.
        # Today's bug would be: script expected 2 writes, hit HOLIDAY_GATE on
        # trading day, contract_met=False -> visible failure. Perfect.

        if not _SUPABASE_URL or not _SUPABASE_KEY:
            return exit_code

        patch_body = {
            "finished_at": finished_at.isoformat(),
            "duration_ms": duration_ms,
            "exit_code": exit_code,
            "exit_reason": exit_reason,
            "actual_writes": self.actual,
            "contract_met": contract_met,
        }
        if notes is not None:
            patch_body["notes"] = notes
        if error_message is not None:
            patch_body["error_message"] = error_message[:4000]  # safety cap

        try:
            r = requests.patch(
                f"{_SUPABASE_URL}/rest/v1/script_execution_log",
                headers=self._headers,
                params={"invocation_id": f"eq.{self.invocation_id}"},
                json=patch_body,
                timeout=10,
            )
            if r.status_code >= 300:
                self._warn(
                    f"Finalise PATCH failed: status={r.status_code} "
                    f"body={r.text[:200]}"
                )
        except Exception as e:
            self._warn(f"Finalise PATCH exception: {e}")

        return exit_code

    def _atexit_finalise(self) -> None:
        """atexit hook. Runs if script exited without calling complete()
        or exit_with_reason(). Records CRASH with whatever tally we have."""
        if self._finalised:
            return
        # Best-effort: capture any pending exception info.
        exc_type, exc_val, exc_tb = sys.exc_info()
        error_msg = None
        if exc_val is not None:
            error_msg = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
        self._finalise(
            exit_reason="CRASH",
            exit_code=1,
            notes="atexit hook fired without explicit completion",
            error_message=error_msg,
        )

    def _warn(self, msg: str) -> None:
        """Write to stderr. ExecutionLog must never break the calling script."""
        print(f"[execution_log WARN] {msg}", file=sys.stderr)
