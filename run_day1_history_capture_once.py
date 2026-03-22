from __future__ import annotations

import sys
import subprocess


def run_command(args: list[str]) -> None:
    completed = subprocess.run(args, check=True)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(args)}")


def main() -> None:
    run_id = sys.argv[1] if len(sys.argv) > 1 else None

    run_command(["python", "archive_market_tape_history.py"])

    if run_id:
        run_command(["python", "archive_option_chain_history.py", run_id])

    print("Day-1 historical capture complete.")


if __name__ == "__main__":
    main()