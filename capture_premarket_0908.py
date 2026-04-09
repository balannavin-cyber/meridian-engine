#!/usr/bin/env python3
"""
Capture MERDIAN pre-open reference at 09:08 IST
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
    log("PREMARKET 09:08 capture starting")
    # reuse existing spot ingestion (do NOT create new logic)
    result = subprocess.run(
        [sys.executable, "capture_market_spot_snapshot_local.py"],  # fixed: was ingest_market_spot_local.py (does not exist)
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        log(f"FAILED premarket capture: {result.stderr}")
        return 1
    log("PREMARKET 09:08 capture complete")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
