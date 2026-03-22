from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from typing import List


SYMBOLS = ["NIFTY", "SENSEX"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_command(cmd: List[str], label: str) -> None:
    print("=" * 72)
    print(f"RUNNING: {label}")
    print("=" * 72)
    print("Command:", " ".join(cmd))
    print("-" * 72)

    result = subprocess.run(cmd, text=True)

    if result.returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {result.returncode}")

    print("-" * 72)
    print(f"COMPLETED: {label}")


def main() -> None:
    print("=" * 72)
    print("MERDIAN - Run Shadow State Pipeline Once")
    print("=" * 72)
    print(f"Started at UTC: {utc_now_iso()}")
    print(f"Symbols: {', '.join(SYMBOLS)}")
    print("-" * 72)

    python_exe = sys.executable

    # Step 1: Build market state
    for symbol in SYMBOLS:
        run_command(
            [python_exe, ".\\build_market_state_snapshot_local.py", symbol],
            f"build_market_state_snapshot_local.py {symbol}",
        )

    # Step 2: Build signal state
    for symbol in SYMBOLS:
        run_command(
            [python_exe, ".\\build_signal_state_snapshot_local.py", symbol],
            f"build_signal_state_snapshot_local.py {symbol}",
        )

    # Step 3: Build shadow state signal
    for symbol in SYMBOLS:
        run_command(
            [python_exe, ".\\build_shadow_state_signal_local.py", symbol],
            f"build_shadow_state_signal_local.py {symbol}",
        )

    # Step 4: Build shadow state outcomes
    run_command(
        [python_exe, ".\\build_shadow_state_signal_outcomes_local.py"],
        "build_shadow_state_signal_outcomes_local.py",
    )

    print("=" * 72)
    print("MERDIAN - SHADOW STATE PIPELINE COMPLETED")
    print("=" * 72)
    print(f"Finished at UTC: {utc_now_iso()}")


if __name__ == "__main__":
    main()