#!/usr/bin/env python3
"""
retire_dhan_breadth.py
=======================
Removes Dhan breadth ingest call from run_option_snapshot_intraday_runner.py.
Replaces it with a comment explaining the retirement.

Breadth is now sourced from Zerodha WebSocket (market_ticks, instrument_type='EQ').
Dhan REST breadth had ~100% failure rate across 30+ sessions due to 429 rate limiting.
"""
import shutil
from pathlib import Path

TARGET = Path("run_option_snapshot_intraday_runner.py")
BACKUP = Path("run_option_snapshot_intraday_runner.py.bak_breadth_retired")

def main():
    lines = TARGET.read_text(encoding="utf-8").splitlines(keepends=True)

    # Find the run_with_fallbacks block for breadth
    start = None
    end = None
    for i, line in enumerate(lines):
        if start is None and '"ingest_breadth_intraday_local.py"' in line:
            # Find the start of the run_with_fallbacks call (search back)
            for j in range(i, max(i-5, 0), -1):
                if "run_with_fallbacks(" in lines[j]:
                    start = j
                    break
            if start is None:
                start = i - 1

        if start is not None and end is None:
            if line.strip() == ")" and i > start:
                end = i + 1
                break

    if start is None or end is None:
        print(f"ERROR: breadth block not found (start={start}, end={end})")
        return 1

    print(f"Found breadth call at lines {start+1}–{end}")
    for line in lines[start:end]:
        print(f"  {line}", end="")

    shutil.copy2(TARGET, BACKUP)
    print(f"\nBackup: {BACKUP}")

    REPLACEMENT = [
        "        # DHAN BREADTH INGEST RETIRED 2026-04-16\n",
        "        # Failure rate ~100% across 30+ sessions (Dhan 429 rate limiting).\n",
        "        # Replaced by Zerodha WebSocket (ws_feed_zerodha.py) which subscribes\n",
        "        # 1,385 NSE EQ breadth stocks. Breadth computed from market_ticks\n",
        "        # by ingest_breadth_from_ticks.py (non-blocking, every 5 min cycle).\n",
    ]

    new_lines = lines[:start] + REPLACEMENT + lines[end:]
    TARGET.write_text("".join(new_lines), encoding="utf-8")

    result = TARGET.read_text(encoding="utf-8")
    if "ingest_breadth_intraday_local.py" not in result and "RETIRED" in result:
        print("OK: Dhan breadth ingest retired from runner")
        return 0
    else:
        print("ERROR: verification failed — restoring")
        shutil.copy2(BACKUP, TARGET)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
