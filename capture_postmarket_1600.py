#!/usr/bin/env python3

"""
Capture MERDIAN post-market weighted close at 16:00 IST
"""

import os
import sys
from datetime import datetime, timezone, timedelta
import subprocess

IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    return datetime.now(IST)

def log(msg):
    print(f"[{now_ist().isoformat()}] {msg}", flush=True)

def main():
    log("POSTMARKET 16:00 capture starting")

    result = subprocess.run(
        [sys.executable, "run_market_close_capture_once.py"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        log(f"FAILED postmarket capture: {result.stderr}")
        return 1

    log("POSTMARKET 16:00 capture complete")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
