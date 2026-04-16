#!/usr/bin/env python3
"""Force wire ingest_breadth_from_ticks into runner using line-based replacement."""
import shutil
from pathlib import Path

TARGET = Path("run_option_snapshot_intraday_runner.py")
BACKUP = Path("run_option_snapshot_intraday_runner.py.bak_wire2")

OLD = """        # DHAN BREADTH INGEST RETIRED 2026-04-16
        # Failure rate ~100% across 30+ sessions (Dhan 429 rate limiting).
        # Replaced by Zerodha WebSocket (ws_feed_zerodha.py) which subscribes
        # 1,385 NSE EQ breadth stocks. Breadth computed from market_ticks
        # by ingest_breadth_from_ticks.py (non-blocking, every 5 min cycle)."""

NEW = """        # Breadth from Zerodha WebSocket ticks (Dhan REST retired 2026-04-16)
        run_with_fallbacks(
            "ingest_breadth_from_ticks.py",
            [[]],
            timeout=TIMEOUT_BREADTH,
            step_name="ingest_breadth_from_ticks",
            non_blocking=True,
        )"""

def main():
    source = TARGET.read_text(encoding="utf-8")
    print(f"OLD in source: {OLD in source}")
    print(f"'ingest_breadth_from_ticks' occurrences: {source.count('ingest_breadth_from_ticks')}")

    if OLD not in source:
        print("ERROR: anchor not found — showing breadth lines:")
        for i, line in enumerate(source.splitlines(), 1):
            if "breadth" in line.lower():
                print(f"  {i}: {repr(line)}")
        return 1

    shutil.copy2(TARGET, BACKUP)
    patched = source.replace(OLD, NEW, 1)
    print(f"Replacement made: {OLD not in patched}")
    TARGET.write_text(patched, encoding="utf-8")

    # Verify
    result = TARGET.read_text(encoding="utf-8")
    print(f"run_with_fallbacks + breadth_from_ticks in result: {'ingest_breadth_from_ticks' in result and 'run_with_fallbacks' in result}")

    # Show the actual lines
    for i, line in enumerate(result.splitlines(), 1):
        if "breadth_from_ticks" in line or ("breadth" in line.lower() and "RETIRED" not in line and "Zerodha" not in line and i > 480 and i < 510):
            print(f"  Line {i}: {line}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
