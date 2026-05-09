"""
merdian_watchdog.py — TD-062 active fix.

Periodic sweeper. Reads heartbeat files in C:\\GammaEnginePython\\heartbeats,
identifies stuck instances, and (optionally) kills the stuck PIDs.

A heartbeat is "stuck" when ALL of:
  - last line is NOT EXIT or ERROR (process didn't terminate cleanly)
  - last line's timestamp is older than --threshold-min (default 5 min)
  - last line's PID is still alive on this host

Output:
  - C:\\GammaEnginePython\\heartbeats\\watchdog.log  (append-only sweep history)
  - stdout (one line per stuck instance)

Run via Task Scheduler every 15 min:

    pythonw.exe C:\\GammaEnginePython\\merdian_watchdog.py --kill

Use register_merdian_watchdog.ps1 to install the schedule.

Design: itself instrumented via heartbeat under task name "MERDIAN_Watchdog"
so we can confirm the watchdog itself isn't getting stuck.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Allow this script to import merdian_heartbeat from same directory
sys.path.insert(0, str(Path(__file__).parent))
try:
    from merdian_heartbeat import heartbeat, write_phase
    HEARTBEAT_AVAILABLE = True
except Exception:
    HEARTBEAT_AVAILABLE = False

IST = timezone(timedelta(hours=5, minutes=30))

HEARTBEAT_DIR = Path(os.environ.get(
    "MERDIAN_HEARTBEAT_DIR",
    r"C:\GammaEnginePython\heartbeats",
))

WATCHDOG_LOG = HEARTBEAT_DIR / "watchdog.log"
STUCK_THRESHOLD_MIN_DEFAULT = 5

# Format produced by merdian_heartbeat:
#   2026-05-04 09:31:42.123 | START | pid=12345 | host=DESKTOP-X | argv=...
LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s\|\s"
    r"(?P<phase>\w+)\s\|\s"
    r"pid=(?P<pid>\d+)"
)


def _now_ist() -> datetime:
    return datetime.now(IST)


def _wlog(msg: str) -> None:
    HEARTBEAT_DIR.mkdir(parents=True, exist_ok=True)
    line = f"{_now_ist().strftime('%Y-%m-%d %H:%M:%S')} | {msg}\n"
    try:
        with open(WATCHDOG_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    print(line, end="", flush=True)


def _pid_alive(pid: int) -> bool:
    """Windows-friendly PID liveness check via tasklist."""
    if sys.platform == "win32":
        try:
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
                capture_output=True, text=True, timeout=10,
            )
            # tasklist prints "INFO: No tasks..." when no match
            if "No tasks" in r.stdout or "No tasks" in r.stderr:
                return False
            return f'"{pid}"' in r.stdout or str(pid) in r.stdout
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def _kill_pid(pid: int) -> bool:
    if sys.platform == "win32":
        try:
            r = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, text=True, timeout=10,
            )
            return r.returncode == 0
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 9)
            return True
        except OSError:
            return False


def _read_last_line(file: Path) -> str | None:
    """
    Return the last non-empty line of file, or None.
    Reads from the tail to avoid loading large logs into memory.
    """
    try:
        size = file.stat().st_size
        if size == 0:
            return None
        # Most heartbeat lines are well under 4 KB; 8 KB tail is plenty.
        chunk = min(8192, size)
        with open(file, "rb") as f:
            f.seek(size - chunk)
            tail = f.read()
        text = tail.decode("utf-8", errors="replace")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        return lines[-1] if lines else None
    except Exception:
        return None


def _parse_last(file: Path):
    """Return (ts_aware_ist, phase, pid) or None."""
    last = _read_last_line(file)
    if last is None:
        return None
    m = LINE_RE.match(last)
    if not m:
        return None
    try:
        ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=IST)
        return ts, m.group("phase"), int(m.group("pid"))
    except Exception:
        return None


def sweep(kill: bool, threshold_min: int) -> dict:
    if not HEARTBEAT_DIR.exists():
        _wlog(f"heartbeat dir missing: {HEARTBEAT_DIR}")
        return {"checked": 0, "stuck": 0, "killed": 0, "orphans": 0}

    hb_files = [
        p for p in HEARTBEAT_DIR.glob("*.log")
        if p.name not in ("watchdog.log",)
    ]
    now = _now_ist()
    cutoff = now - timedelta(minutes=threshold_min)

    stuck = []
    orphans = 0
    skipped_clean = 0

    for f in hb_files:
        parsed = _parse_last(f)
        if parsed is None:
            continue
        ts, phase, pid = parsed

        # Cleanly terminated — nothing to do
        if phase in ("EXIT", "ERROR"):
            skipped_clean += 1
            continue

        # Recent enough — still alive and progressing
        if ts > cutoff:
            continue

        # Old + non-terminal: check if PID still around
        if not _pid_alive(pid):
            # Process died but never wrote EXIT/ERROR (hard kill, OOM, etc.)
            _wlog(
                f"ORPHAN: task={f.stem} pid={pid} last_phase={phase} "
                f"last_ts={ts.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            orphans += 1
            continue

        stuck.append((f.stem, pid, phase, ts))

    killed = 0
    for task, pid, phase, ts in stuck:
        age_min = (now - ts).total_seconds() / 60.0
        _wlog(
            f"STUCK: task={task} pid={pid} last_phase={phase} "
            f"age_min={age_min:.1f}"
        )
        if kill:
            ok = _kill_pid(pid)
            _wlog(f"  KILL pid={pid} -> {'OK' if ok else 'FAIL'}")
            if ok:
                killed += 1

    summary = {
        "checked": len(hb_files),
        "skipped_clean": skipped_clean,
        "stuck": len(stuck),
        "killed": killed,
        "orphans": orphans,
        "threshold_min": threshold_min,
    }
    _wlog(f"SWEEP: {summary}")
    return summary


def main() -> int:
    p = argparse.ArgumentParser(description="MERDIAN watchdog (TD-062)")
    p.add_argument("--kill", action="store_true",
                   help="actually kill stuck PIDs (else dry-run)")
    p.add_argument("--threshold-min", type=int,
                   default=STUCK_THRESHOLD_MIN_DEFAULT,
                   help=f"stuck threshold in minutes "
                        f"(default {STUCK_THRESHOLD_MIN_DEFAULT})")
    args = p.parse_args()

    if HEARTBEAT_AVAILABLE:
        with heartbeat("MERDIAN_Watchdog", alive_interval_sec=0):
            write_phase("MERDIAN_Watchdog", "SWEEP_BEGIN",
                        extra=f"kill={args.kill} threshold_min={args.threshold_min}")
            summary = sweep(kill=args.kill, threshold_min=args.threshold_min)
            write_phase("MERDIAN_Watchdog", "SWEEP_END", extra=str(summary))
    else:
        sweep(kill=args.kill, threshold_min=args.threshold_min)
    return 0


if __name__ == "__main__":
    sys.exit(main())
