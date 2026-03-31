from __future__ import annotations

import atexit
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from gamma_engine_heartbeat import mark_component_error, mark_component_ok, mark_component_warn
from trading_calendar import (
    MissingSessionConfigError,
    TradingCalendarError,
    current_session_state,
    get_today_session_config,
)


IST = timezone(timedelta(hours=5, minutes=30))

SUPERVISOR_LOCK_FILE = Path("gamma_engine_supervisor.lock")
RUNNER_LOCK_FILE = Path("run_option_snapshot_intraday_runner.lock")
SUPERVISOR_LOG_FILE = "gamma_engine_supervisor.log"

SUPERVISOR_CHECK_INTERVAL_SECONDS = 60
RUNNER_STALE_AFTER_SECONDS = 900
SUPERVISOR_HEARTBEAT_STALE_AFTER_SECONDS = 180

RUNNER_SCRIPT = "run_option_snapshot_intraday_runner.py"
SUPERVISOR_COMPONENT_NAME = "gamma_engine_supervisor"


def now_ist() -> datetime:
    return datetime.now(IST)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    ts = now_ist().strftime("%Y-%m-%d %H:%M:%S IST")
    line = f"[{ts}] {message}"
    print(line)
    with open(SUPERVISOR_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _safe_int(value) -> int | None:
    try:
        return int(str(value).strip())
    except Exception:
        return None


def _parse_iso_dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def _read_lock_payload(path: Path) -> dict:
    if not path.exists():
        return {}

    try:
        raw = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return {}

    payload = {}
    for line in raw:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = value.strip()
    return payload


def _write_lock_file(path: Path, script_name: str) -> None:
    content = [
        f"pid={os.getpid()}",
        f"started_at={datetime.now(timezone.utc).isoformat()}",
        f"heartbeat={datetime.now(timezone.utc).isoformat()}",
        f"script={script_name}",
    ]
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def _remove_lock_file(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except Exception:
        pass


def _update_lock_heartbeat(path: Path, script_name: str) -> None:
    if not path.exists():
        return

    payload = _read_lock_payload(path)
    payload["pid"] = str(os.getpid())
    payload["script"] = script_name
    payload["heartbeat"] = datetime.now(timezone.utc).isoformat()
    if "started_at" not in payload:
        payload["started_at"] = datetime.now(timezone.utc).isoformat()

    content = [f"{k}={v}" for k, v in payload.items()]
    path.write_text("\n".join(content) + "\n", encoding="utf-8")


def _process_is_running(pid: int) -> bool:
    try:
        if pid <= 0:
            return False
        os.kill(pid, 0)
        return True
    except OSError:
        return False
    except Exception:
        return False


def session_label_for_heartbeat() -> str:
    try:
        return current_session_state()
    except Exception:
        return "UNKNOWN"


def _write_supervisor_heartbeat(
    *,
    status: str,
    notes: str,
    last_successful_cycle_utc: Optional[str] = None,
    runner_detail: Optional[str] = None,
    runner_healthy: Optional[bool] = None,
) -> None:
    extra = {
        "runner_script": RUNNER_SCRIPT,
        "supervisor_check_interval_seconds": SUPERVISOR_CHECK_INTERVAL_SECONDS,
        "runner_stale_after_seconds": RUNNER_STALE_AFTER_SECONDS,
    }

    if runner_detail is not None:
        extra["runner_detail"] = runner_detail
    if runner_healthy is not None:
        extra["runner_healthy"] = runner_healthy

    session = session_label_for_heartbeat()

    if status == "OK":
        mark_component_ok(
            SUPERVISOR_COMPONENT_NAME,
            session=session,
            last_successful_cycle_utc=last_successful_cycle_utc,
            stale_after_seconds=SUPERVISOR_HEARTBEAT_STALE_AFTER_SECONDS,
            notes=notes,
            extra=extra,
        )
    elif status == "WARN":
        mark_component_warn(
            SUPERVISOR_COMPONENT_NAME,
            session=session,
            last_successful_cycle_utc=last_successful_cycle_utc,
            stale_after_seconds=SUPERVISOR_HEARTBEAT_STALE_AFTER_SECONDS,
            notes=notes,
            extra=extra,
        )
    else:
        mark_component_error(
            SUPERVISOR_COMPONENT_NAME,
            session=session,
            last_successful_cycle_utc=last_successful_cycle_utc,
            stale_after_seconds=SUPERVISOR_HEARTBEAT_STALE_AFTER_SECONDS,
            notes=notes,
            extra=extra,
        )


def acquire_supervisor_lock() -> None:
    if not SUPERVISOR_LOCK_FILE.exists():
        _write_lock_file(SUPERVISOR_LOCK_FILE, Path(__file__).name)
        atexit.register(lambda: _remove_lock_file(SUPERVISOR_LOCK_FILE))
        log(f"Supervisor lock acquired: {SUPERVISOR_LOCK_FILE.resolve()}")
        _write_supervisor_heartbeat(
            status="OK",
            notes="Supervisor lock acquired",
            last_successful_cycle_utc=now_utc_iso(),
        )
        return

    payload = _read_lock_payload(SUPERVISOR_LOCK_FILE)
    existing_pid = _safe_int(payload.get("pid"))
    heartbeat_dt = _parse_iso_dt(payload.get("heartbeat"))

    now_utc = datetime.now(timezone.utc)
    age_seconds = None
    if heartbeat_dt is not None:
        age_seconds = (now_utc - heartbeat_dt).total_seconds()

    existing_running = False
    if existing_pid is not None:
        existing_running = _process_is_running(existing_pid)

    if existing_running and age_seconds is not None and age_seconds <= RUNNER_STALE_AFTER_SECONDS:
        detail = (
            f"Another supervisor instance is already active "
            f"(pid={existing_pid}, heartbeat_age_seconds={age_seconds:.1f}). Exiting."
        )
        log(detail)
        _write_supervisor_heartbeat(
            status="WARN",
            notes=detail,
            runner_detail="Supervisor duplicate instance blocked",
            runner_healthy=None,
        )
        sys.exit(1)

    log("Existing supervisor lock is stale or owner is not running. Reclaiming lock.")
    _remove_lock_file(SUPERVISOR_LOCK_FILE)
    _write_lock_file(SUPERVISOR_LOCK_FILE, Path(__file__).name)
    atexit.register(lambda: _remove_lock_file(SUPERVISOR_LOCK_FILE))
    log(f"Supervisor lock acquired: {SUPERVISOR_LOCK_FILE.resolve()}")
    _write_supervisor_heartbeat(
        status="OK",
        notes="Supervisor lock reclaimed and acquired",
        last_successful_cycle_utc=now_utc_iso(),
    )


def _runner_status() -> tuple[bool, str]:
    if not RUNNER_LOCK_FILE.exists():
        return False, "Runner lock file missing"

    payload = _read_lock_payload(RUNNER_LOCK_FILE)
    runner_pid = _safe_int(payload.get("pid"))
    heartbeat_dt = _parse_iso_dt(payload.get("heartbeat"))

    if runner_pid is None:
        return False, "Runner lock missing pid"

    if not _process_is_running(runner_pid):
        return False, f"Runner pid {runner_pid} is not active"

    if heartbeat_dt is None:
        return False, "Runner heartbeat missing/invalid"

    age_seconds = (datetime.now(timezone.utc) - heartbeat_dt).total_seconds()
    if age_seconds > RUNNER_STALE_AFTER_SECONDS:
        return False, f"Runner heartbeat stale ({age_seconds:.1f}s)"

    return True, f"Runner healthy (pid={runner_pid}, heartbeat_age_seconds={age_seconds:.1f})"


def _start_runner() -> None:
    cmd = [sys.executable, RUNNER_SCRIPT]

    # IMPORTANT:
    # Do NOT open a new terminal window.
    # Use DETACHED_PROCESS + CREATE_NO_WINDOW on Windows so no console pops up.
    creationflags = 0
    startupinfo = None

    if os.name == "nt":
        creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW

    subprocess.Popen(
        cmd,
        cwd=str(Path(__file__).resolve().parent),
        creationflags=creationflags,
        startupinfo=startupinfo,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        close_fds=True,
    )

    log(f"Started runner without terminal window: {' '.join(cmd)}")


def main() -> None:
    acquire_supervisor_lock()

    atexit.register(
        lambda: _write_supervisor_heartbeat(
            status="WARN",
            notes="Supervisor process exiting",
            last_successful_cycle_utc=now_utc_iso(),
        )
    )

    log("=" * 72)
    log("Gamma Engine - Supervisor")
    log("=" * 72)
    log(f"Interpreter: {sys.executable}")
    log(f"Runner script: {RUNNER_SCRIPT}")
    log(f"Check interval seconds: {SUPERVISOR_CHECK_INTERVAL_SECONDS}")
    log("=" * 72)

    _write_supervisor_heartbeat(
        status="OK",
        notes="Supervisor started successfully",
        last_successful_cycle_utc=now_utc_iso(),
    )

    while True:
        _update_lock_heartbeat(SUPERVISOR_LOCK_FILE, Path(__file__).name)

        try:
            cfg = get_today_session_config()
            state = current_session_state()

            if not cfg.is_open:
                detail = f"Trading calendar marks {cfg.date} as CLOSED. Supervisor idle."
                log(detail)
                _write_supervisor_heartbeat(
                    status="OK",
                    notes=detail,
                    last_successful_cycle_utc=now_utc_iso(),
                    runner_detail="No runner action needed on closed day",
                    runner_healthy=None,
                )
                time.sleep(SUPERVISOR_CHECK_INTERVAL_SECONDS)
                continue

            if state in {"CLOSED", "PREMARKET_MONITOR", "PREMARKET_REF_DUE", "OPEN_WAIT"}:
                detail = f"Supervisor waiting for regular session. Current state={state}"
                log(detail)
                _write_supervisor_heartbeat(
                    status="OK",
                    notes=detail,
                    last_successful_cycle_utc=now_utc_iso(),
                    runner_detail="Supervisor waiting for regular session",
                    runner_healthy=None,
                )
                time.sleep(SUPERVISOR_CHECK_INTERVAL_SECONDS)
                continue

            if state in {"POST_CLOSE_WAIT", "POSTMARKET_REF_DUE", "POSTMARKET_COMPLETE"}:
                detail = f"Session no longer active for options runner. Current state={state}"
                log(detail)
                _write_supervisor_heartbeat(
                    status="OK",
                    notes=detail,
                    last_successful_cycle_utc=now_utc_iso(),
                    runner_detail="Supervisor idle after active session",
                    runner_healthy=None,
                )
                time.sleep(SUPERVISOR_CHECK_INTERVAL_SECONDS)
                continue

            if state != "REGULAR_SESSION":
                detail = f"Unexpected session state={state}. Supervisor idle."
                log(detail)
                _write_supervisor_heartbeat(
                    status="WARN",
                    notes=detail,
                    last_successful_cycle_utc=now_utc_iso(),
                    runner_detail="Supervisor encountered unexpected state",
                    runner_healthy=None,
                )
                time.sleep(SUPERVISOR_CHECK_INTERVAL_SECONDS)
                continue

            ok, detail = _runner_status()

            if ok:
                log(detail)
                _write_supervisor_heartbeat(
                    status="OK",
                    notes="Supervisor loop healthy",
                    last_successful_cycle_utc=now_utc_iso(),
                    runner_detail=detail,
                    runner_healthy=True,
                )
            else:
                log(f"Runner not healthy: {detail}")
                _write_supervisor_heartbeat(
                    status="WARN",
                    notes="Runner not healthy; attempting restart",
                    last_successful_cycle_utc=now_utc_iso(),
                    runner_detail=detail,
                    runner_healthy=False,
                )
                _start_runner()

            time.sleep(SUPERVISOR_CHECK_INTERVAL_SECONDS)

        except MissingSessionConfigError as exc:
            detail = f"Trading calendar coverage missing: {exc}"
            log(detail)
            _write_supervisor_heartbeat(
                status="ERROR",
                notes=detail,
                last_successful_cycle_utc=now_utc_iso(),
            )
            time.sleep(SUPERVISOR_CHECK_INTERVAL_SECONDS)

        except TradingCalendarError as exc:
            detail = f"Trading calendar configuration error: {exc}"
            log(detail)
            _write_supervisor_heartbeat(
                status="ERROR",
                notes=detail,
                last_successful_cycle_utc=now_utc_iso(),
            )
            time.sleep(SUPERVISOR_CHECK_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            log("Supervisor interrupted by user. Exiting.")
            _write_supervisor_heartbeat(
                status="WARN",
                notes="Supervisor interrupted by user",
                last_successful_cycle_utc=now_utc_iso(),
            )
            break

        except Exception as exc:
            detail = f"Supervisor error: {exc}"
            log(detail)
            _write_supervisor_heartbeat(
                status="ERROR",
                notes=detail,
                last_successful_cycle_utc=now_utc_iso(),
            )
            time.sleep(SUPERVISOR_CHECK_INTERVAL_SECONDS)

    log("SUPERVISOR FINISHED")


if __name__ == "__main__":
    main()