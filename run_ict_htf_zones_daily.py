"""
run_ict_htf_zones_daily.py
==========================

pythonw-friendly replacement for run_ict_htf_zones_daily.bat.
Closes TD-061 residual on MERDIAN_ICT_HTF_Zones_0845 (no cmd window flash).

Functionally equivalent to the .bat:
  Call 1:  python build_ict_htf_zones.py --timeframe both
  Call 2:  python build_ict_htf_zones.py --timeframe H
  Call 3:  python generate_pine_overlay.py            # TD-NEW-5 S28 chain

Behavior preserved:
  - Per-call START / END banners in logs\\task_output.log (same format).
  - Each call's stdout+stderr redirected to logs\\task_output.log.
  - Exits with max(rc_wd, rc_h, rc_pine) so any single failure surfaces.
  - cwd = C:\\GammaEnginePython.

Task Scheduler action (post-migration):
  Execute  : C:\\Users\\balan\\AppData\\Local\\Programs\\Python\\Python312\\pythonw.exe
  Argument : run_ict_htf_zones_daily.py
  WorkDir  : C:\\GammaEnginePython

Note: sys.executable resolves to pythonw.exe when this script is itself launched
by pythonw, so child python subprocesses also run windowless.
"""

import datetime
import subprocess
import sys
from pathlib import Path

BASE = Path(r"C:\GammaEnginePython")
LOG = BASE / "logs" / "task_output.log"


def _stamp() -> str:
    """Match .bat's %DATE% %TIME% format closely enough for grep continuity."""
    return datetime.datetime.now().strftime("%a %m/%d/%Y %H:%M:%S.%f")[:-3]


def log_line(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(msg + "\n")


def run_step(label: str, args: list[str]) -> int:
    log_line(f"--- {_stamp()} [{label}] start ---")
    with LOG.open("a", encoding="utf-8") as logfp:
        proc = subprocess.run(
            [sys.executable] + args,
            cwd=str(BASE),
            stdout=logfp,
            stderr=subprocess.STDOUT,
            text=True,
        )
    log_line(f"--- {_stamp()} [{label}] end (rc={proc.returncode}) ---")
    return proc.returncode


def main() -> int:
    log_line("")
    log_line(f"=== {_stamp()} MERDIAN_ICT_HTF_Zones_0845 START ===")

    rc_wd   = run_step("WD",   ["build_ict_htf_zones.py", "--timeframe", "both"])
    rc_h    = run_step("H",    ["build_ict_htf_zones.py", "--timeframe", "H"])
    rc_pine = run_step("PINE", ["generate_pine_overlay.py"])

    rc = max(rc_wd, rc_h, rc_pine)
    log_line(
        f"=== {_stamp()} MERDIAN_ICT_HTF_Zones_0845 END "
        f"(rc_wd={rc_wd} rc_h={rc_h} rc_pine={rc_pine} final={rc}) ==="
    )
    return rc


if __name__ == "__main__":
    sys.exit(main())
