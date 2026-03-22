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
from trading_calendar import get_session_times, is_trading_day


IST = timezone(timedelta(hours=5, minutes=30))

SUPERVISOR_LOCK_FILE = Path("gamma_engine_supervisor.lock")
RUNNER_LOCK_FILE = Path("run_option_snapshot_intraday_runner.lock")
SUPERVISOR_LOG_FILE = "gamma_engine_supervisor.log"

SUPERVISOR_CHECK_INTERVAL_SECONDS = 60
RUNNER_STALE_AFTER_SECONDS = 900
SUPERVISOR_HEARTBEAT_STALE_AFTER_SECONDS = 180

RUNNER_SCRIPT = "run_option_snapshot_intraday_runner.py"
SUPERVISOR_COMPONENT_NAME = "gamma_engine_supervisor"

PREMARKET_START_HOUR_FALLBACK = 9
PREMARKET_START_MINUTE_FALLBACK = 0
SESSION_START_HOUR_FALLBACK = 9
SESSION_START_MINUTE_FALLBACK = 15
SESSION_END_HOUR_FALLBACK = 15
SESSION_END_MINUTE_FALLBACK = 30


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


def parse_hhmm(value: str, fallback_hour: int, fallback_minute: int) -> tuple[int, int]:
    try:
        raw = str(value).strip()
        parts = raw.split(":")
        if len(parts) != 2:
            raise ValueError("Invalid HH:MM format")
        hour = int(parts[0])
        minute = int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid time values")
        return hour, minute
    except Exception:
        return fallback_hour, fallback_minute


def get_session_bounds_for_today() -> tuple[datetime, datetime]:
    session_cfg = get_session_times()

    if session_cfg:
        open_hour, open_minute = parse_hhmm(
            session_cfg.get("open", "09:15"),
            SESSION_START_HOUR_FALLBACK,
            SESSION_START_MINUTE_FALLBACK,
        )
        close_hour, close_minute = parse_hhmm(
            session_cfg.get("close", "15:30"),
            SESSION_END_HOUR_FALLBACK,
            SESSION_END_MINUTE_FALLBACK,
        )
    else:
        open_hour, open_minute = SESSION_START_HOUR_FALLBACK, SESSION_START_MINUTE_FALLBACK
        close_hour, close_minute = SESSION_END_HOUR_FALLBACK, SESSION_END_MINUTE_FALLBACK

    now = now_ist()

    session_start = now.replace(
        hour=open_hour,
        minute=open_minute,
        second=0,
        microsecond=0,
    )
    session_end = now.replace(
        hour=close_hour,
        minute=close_minute,
        second=0,
        microsecond=0,
    )

    return session_start, session_end


def get_premarket_start_for_today() -> datetime:
    now = now_ist()
    return now.replace(
        hour=PREMARKET_START_HOUR_FALLBACK,
        minute=PREMARKET_START_MINUTE_FALLBACK,
        second=0,
        microsecond=0,
    )


def current_session_label() -> str:
    now = now_ist()

    if not is_trading_day():
        return "Market Closed"

    premarket_start = get_premarket_start_for_today()
    session_start, session_end = get_session_bounds_for_today()

    if now < premarket_start:
        return "Market Closed"
    if now < session_start:
        return "PREMARKET"
    if now <= session_end:
        return "Market OPEN"
    return "Market Closed"


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

    session = current_session_label()

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

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_CONSOLE

    subprocess.Popen(
        cmd,
        cwd=str(Path(__file__).resolve().parent),
        creationflags=creationflags,
    )

    log(f"Started runner: {' '.join(cmd)}")


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
            if not is_trading_day():
                detail = "Trading calendar says CLOSED today. Supervisor idle."
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

            session_start, session_end = get_session_bounds_for_today()
            now = now_ist()

            if now < session_start:
                detail = f"Before session start. Waiting. Session starts at {session_start.isoformat()}"
                log(detail)
                _write_supervisor_heartbeat(
                    status="OK",
                    notes=detail,
                    last_successful_cycle_utc=now_utc_iso(),
                    runner_detail="Supervisor waiting for trading session",
                    runner_healthy=None,
                )
                time.sleep(SUPERVISOR_CHECK_INTERVAL_SECONDS)
                continue

            if now > session_end:
                detail = "Session already ended for today. Supervisor idle."
                log(detail)
                _write_supervisor_heartbeat(
                    status="OK",
                    notes=detail,
                    last_successful_cycle_utc=now_utc_iso(),
                    runner_detail="Supervisor idle after market close",
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