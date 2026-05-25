#!/usr/bin/env python3

from __future__ import annotations

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import subprocess

IST = timezone(timedelta(hours=5, minutes=30))
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "run_market_close_capture_once.log"


def now_ist() -> datetime:
    return datetime.now(IST)


def log(msg: str) -> None:
    line = f"[{now_ist().isoformat()}] {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_step(args: list[str], label: str) -> int:
    log(f"START {label} :: {' '.join(args)}")
    result = subprocess.run(
        args,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
    )

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    if stdout:
        log(f"{label} STDOUT:\n{stdout}")
    if stderr:
        log(f"{label} STDERR:\n{stderr}")

    log(f"END {label} | returncode={result.returncode}")
    return result.returncode


def main() -> int:
    log("=" * 72)
    log("MERDIAN - AWS run_market_close_capture_once")
    log("=" * 72)

    rc_spot = run_step([sys.executable, "capture_market_spot_snapshot_local.py"], "spot_close_capture")
    rc_futures = run_step([sys.executable, "capture_index_futures_snapshot_local.py"], "futures_close_capture")

    if rc_spot == 0 and rc_futures == 0:
        rc_archive = run_step([sys.executable, "archive_market_tape_history.py"], "archive_market_tape_history")
    else:
        rc_archive = -1
        log(
            f"Skipping archive_market_tape_history because prerequisites failed "
            f"(spot={rc_spot}, futures={rc_futures})."
        )

    if rc_spot == 0 and rc_futures == 0 and rc_archive == 0:
        log("MARKET CLOSE CAPTURE SUCCESS")
        return 0

    log(
        f"MARKET CLOSE CAPTURE FAILED | "
        f"spot={rc_spot} | futures={rc_futures} | archive={rc_archive}"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
