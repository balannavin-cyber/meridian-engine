#!/usr/bin/env python3
"""
preopen_capture.py
==================
TD-064 dedicated wrapper for MERDIAN_PreOpen Task Scheduler task.

Why a separate wrapper:
- capture_spot_1m.py is shared by MERDIAN_PreOpen (09:05) and MERDIAN_Spot_1M
  (every minute 09:14-15:31). We want the heartbeat log file named per task
  so we can see which fire context produced which signal/error.
- This wrapper imports capture_spot_1m's main() so we inherit all logic
  without duplication; only the heartbeat label changes.

Update the MERDIAN_PreOpen task to call this script instead of
capture_spot_1m.py directly:
    Action.Execute   = pythonw.exe (already correct)
    Action.Arguments = C:\\GammaEnginePython\\preopen_capture.py
                       (was: C:\\GammaEnginePython\\capture_spot_1m.py)

Heartbeat output:
    C:\\GammaEnginePython\\heartbeats\\MERDIAN_PreOpen.log

Phases:
    START          (heartbeat context manager)
    EXIT           (clean) or ERROR (exception)

Tomorrow's 09:05 IST fire produces durable evidence regardless of whether
auth succeeds or fails. Closes the visibility gap that left 2026-05-01's
401 invisible until manual investigation tonight.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure we can import siblings
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from merdian_heartbeat import heartbeat
    HB_AVAILABLE = True
except Exception:
    HB_AVAILABLE = False

from capture_spot_1m import main as capture_main


if __name__ == "__main__":
    if HB_AVAILABLE:
        with heartbeat("MERDIAN_PreOpen"):
            sys.exit(capture_main())
    else:
        sys.exit(capture_main())
