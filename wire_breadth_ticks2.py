#!/usr/bin/env python3
"""Wire ingest_breadth_from_ticks.py into runner — replace retired comment block."""
import shutil
from pathlib import Path

TARGET = Path("run_option_snapshot_intraday_runner.py")
BACKUP = Path("run_option_snapshot_intraday_runner.py.bak_wire_breadth")

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

    if "ingest_breadth_from_ticks" in source and "run_with_fallbacks" in source.split("ingest_breadth_from_ticks")[1][:200]:
        print("Already wired with run_with_fallbacks.")
        return 0

    if OLD not in source:
        print("ERROR: retired comment block not found")
        # Show what's there
        for i, line in enumerate(source.splitlines(), 1):
            if "breadth" in line.lower() and i > 480:
                print(f"  Line {i}: {line.strip()}")
        return 1

    shutil.copy2(TARGET, BACKUP)
    patched = source.replace(OLD, NEW, 1)
    TARGET.write_text(patched, encoding="utf-8")

    result = TARGET.read_text(encoding="utf-8")
    if 'run_with_fallbacks(\n            "ingest_breadth_from_ticks' in result:
        print("OK: ingest_breadth_from_ticks.py wired into runner")
        return 0
    else:
        print("ERROR: restoring")
        shutil.copy2(BACKUP, TARGET)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
