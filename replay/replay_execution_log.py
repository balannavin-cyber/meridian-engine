"""
replay.replay_execution_log — Mirror of core.execution_log for ENH-93 replay harness.

Differences from core.execution_log:
  1. All Supabase writes target `script_execution_log_replay`, not `script_execution_log`.
  2. `_detect_host()` returns 'replay' unconditionally — replay rows are filterable
     from any other rows that might leak in.
  3. Otherwise byte-identical: atexit crash hook, contract_met logic, set_symbol PATCH,
     VALID_EXIT_REASONS frozenset all match live behavior.

Live impact: ZERO. This module never touches live `script_execution_log`.

Author: Session 24 (2026-05-09)
"""
from __future__ import annotations

import atexit
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

# Replay target table — the only material divergence from core.execution_log.
_REPLAY_TABLE = "script_execution_log_replay"

load_dotenv()

_SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
_SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")


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
    """Replay context: always 'replay'. Filter audit rows by host='replay' to find
    them. Optional override via MERDIAN_HOST env var still respected."""
    override = os.environ.get("MERDIAN_HOST")
    if override:
        return override
    return "replay"


class ExecutionLog:
    """Mirror of core.execution_log.ExecutionLog targeting script_execution_log_replay.

    See core.execution_log module docstring for usage. Behaviorally identical
    except for table target and host tag.
    """

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

        self._insert_opening_row()
        atexit.register(self._atexit_finalise)

    def record_write(self, table: str, n_rows: int) -> None:
        if n_rows < 0:
            raise ValueError(f"record_write: n_rows must be >=0, got {n_rows}")
        self.actual[table] = self.actual.get(table, 0) + int(n_rows)

    def set_symbol(self, symbol: str | None) -> None:
        if self._finalised:
            return
        if symbol is None:
            return
        self.symbol = symbol

        if not _SUPABASE_URL or not _SUPABASE_KEY:
            return

        try:
            r = requests.patch(
                f"{_SUPABASE_URL}/rest/v1/{_REPLAY_TABLE}",
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
        reason = "DRY_RUN" if self.dry_run else "SUCCESS"
        return self._finalise(exit_reason=reason, exit_code=0, notes=notes)

    def exit_with_reason(
        self,
        reason: str,
        exit_code: int = 0,
        notes: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> int:
        if reason not in VALID_EXIT_REASONS:
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
            self._warn("No Supabase credentials; replay execution_log disabled for this run")
            self._finalised = True
            return
        payload = self._payload_common()
        payload.update({
            "exit_reason": "RUNNING",
            "actual_writes": {},
            "contract_met": None,
        })
        try:
            r = requests.post(
                f"{_SUPABASE_URL}/rest/v1/{_REPLAY_TABLE}",
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
        contract_met = self._compute_contract_met(exit_code)

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
            patch_body["error_message"] = error_message[:4000]

        try:
            r = requests.patch(
                f"{_SUPABASE_URL}/rest/v1/{_REPLAY_TABLE}",
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
        if self._finalised:
            return
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
        print(f"[replay_execution_log WARN] {msg}", file=sys.stderr)