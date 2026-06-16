#!/usr/bin/env python3

"""
Capture MERDIAN post-market weighted close at 16:00 IST.

S55 (TD-S54-NEW-3): the prior version logged only result.stderr, so a child
that failed with output on stdout -- or a bare non-zero exit with no stderr --
produced a blank "FAILED postmarket capture:" line every day, hiding the cause.
This version always emits a non-blank reason (exit code + stderr + stdout tail)
and surfaces child stdout on success too, for audit.
"""

import os
import sys
import subprocess
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
CHILD = "run_market_close_capture_once.py"
TAIL = 800  # chars of child output to surface


def now_ist():
    return datetime.now(IST)


def log(msg):
    print(f"[{now_ist().isoformat()}] {msg}", flush=True)


def main():
    log("POSTMARKET 16:00 capture starting")

    script_dir = os.path.dirname(os.path.abspath(__file__)) or "."
    try:
        result = subprocess.run(
            [sys.executable, CHILD],
            capture_output=True,
            text=True,
            cwd=script_dir,
        )
    except Exception as e:
        log(f"FAILED postmarket capture: wrapper could not launch {CHILD}: {e!r}")
        return 1

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    if result.returncode != 0:
        reason = stderr or stdout or "(child produced no stdout/stderr)"
        log(f"FAILED postmarket capture: exit={result.returncode} | {reason[-TAIL:]}")
        # If stderr was the reason but stdout also has context, surface both.
        if stderr and stdout:
            log(f"  child stdout tail: {stdout[-TAIL:]}")
        return 1

    if stdout:
        log(f"child stdout tail: {stdout[-TAIL:]}")
    log("POSTMARKET 16:00 capture complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
