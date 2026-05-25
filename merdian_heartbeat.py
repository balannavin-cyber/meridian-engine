"""
merdian_heartbeat.py — TD-062 instrumentation.

Per-task heartbeat with phase / pid / timestamp.

Drop-in usage in any MERDIAN entry-point script:

    from merdian_heartbeat import heartbeat

    if __name__ == "__main__":
        with heartbeat("MERDIAN_Spot_1M"):
            main()

Optional phase markers inside long-running scripts to localize where a hang
occurs (write_phase is also safe to call before/after suspect Supabase calls):

    from merdian_heartbeat import heartbeat, write_phase

    with heartbeat("MERDIAN_Intraday_Supervisor_Start"):
        write_phase("MERDIAN_Intraday_Supervisor_Start", "CALENDAR_GATE_BEGIN")
        ok = check_calendar_gate()
        write_phase("MERDIAN_Intraday_Supervisor_Start", "CALENDAR_GATE_END",
                    extra=f"open={ok}")
        ...

Heartbeats are written to:
    C:\\GammaEnginePython\\heartbeats\\<task_name>.log

Local-file by design: if Supabase is what hangs, a Supabase-only heartbeat
won't fire when most needed. The watchdog reads these local files.

Instrumentation must NEVER break the host script. Every write is wrapped in
a broad except — heartbeat failures degrade silently.
"""

from __future__ import annotations

import os
import sys
import threading
import socket
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))

HEARTBEAT_DIR = Path(os.environ.get(
    "MERDIAN_HEARTBEAT_DIR",
    r"C:\GammaEnginePython\heartbeats",
))

ALIVE_INTERVAL_SEC_DEFAULT = 30


def _now_ist_str() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _ensure_dir() -> None:
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)


def _write_line(task_name: str, phase: str, extra: str = "") -> None:
    """Append one line to <task>.log. Never raises."""
    try:
        _ensure_dir()
        line = (
            f"{_now_ist_str()} | {phase} | "
            f"pid={os.getpid()} | host={socket.gethostname()}"
        )
        if extra:
            # Single-line constraint — no newlines in extra
            extra_clean = extra.replace("\n", " ").replace("\r", " ")
            line += f" | {extra_clean}"
        line += "\n"

        target = HEARTBEAT_DIR / f"{task_name}.log"
        with open(target, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            try:
                # fsync gives durability across hard kills on Windows
                os.fsync(f.fileno())
            except OSError:
                pass
    except Exception:
        # Instrumentation must not break the host script
        pass


def write_phase(task_name: str, phase: str, extra: str = "") -> None:
    """
    Standalone phase marker. Safe to call from anywhere inside an
    instrumented script. Use at meaningful boundaries:
        SUPABASE_CONNECT, CALENDAR_GATE_BEGIN/END, CYCLE_BEGIN/END,
        TOKEN_REFRESH, FETCH_BARS, UPSERT_SIGNAL, etc.
    """
    _write_line(task_name, phase, extra)


@contextmanager
def heartbeat(
    task_name: str,
    alive_interval_sec: int = ALIVE_INTERVAL_SEC_DEFAULT,
):
    """
    Context manager: writes START on enter, ALIVE every N seconds in a
    daemon thread, EXIT (clean) or ERROR (exception) on exit.

    Args:
        task_name: matches the Task Scheduler task name (e.g. MERDIAN_Spot_1M)
        alive_interval_sec: 0 disables the periodic ALIVE thread; useful for
                            short scripts where START/EXIT alone is enough.
    """
    stop_event = threading.Event()

    def _alive_loop() -> None:
        while not stop_event.wait(alive_interval_sec):
            _write_line(task_name, "ALIVE")

    # START
    argv_str = " ".join(sys.argv) if sys.argv else "<no argv>"
    _write_line(task_name, "START", extra=f"argv={argv_str}")

    alive_thread = None
    if alive_interval_sec and alive_interval_sec > 0:
        alive_thread = threading.Thread(
            target=_alive_loop,
            daemon=True,
            name=f"hb-{task_name}",
        )
        alive_thread.start()

    exit_phase = "EXIT"
    exit_extra = ""
    try:
        yield
    except SystemExit as e:
        exit_phase = "EXIT"
        exit_extra = f"sys_exit_code={e.code}"
        raise
    except KeyboardInterrupt:
        exit_phase = "EXIT"
        exit_extra = "keyboard_interrupt"
        raise
    except BaseException as e:
        exit_phase = "ERROR"
        msg = str(e)[:200].replace("\n", " ").replace("\r", " ")
        exit_extra = f"type={type(e).__name__} msg={msg}"
        raise
    finally:
        stop_event.set()
        # don't block on alive_thread.join — it's a daemon
        _write_line(task_name, exit_phase, extra=exit_extra)


# Convenience for ad-hoc instrumentation outside a context manager
def hb_start(task_name: str, extra: str = "") -> None:
    _write_line(task_name, "START", extra)


def hb_exit(task_name: str, extra: str = "") -> None:
    _write_line(task_name, "EXIT", extra)


def hb_error(task_name: str, extra: str = "") -> None:
    _write_line(task_name, "ERROR", extra)
