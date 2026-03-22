import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PYTHON_EXE = sys.executable
BASE_DIR = Path(__file__).resolve().parent
INGEST_SCRIPT = BASE_DIR / "ingest_equity_eod_local.py"
DAILY_REBUILD_SCRIPT = BASE_DIR / "build_breadth_indicators_daily_local.py"
COVERAGE_SCRIPT = BASE_DIR / "coverage_check.py"
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

MAX_RUNS = 80
SLEEP_BETWEEN_RUNS_SEC = 3


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def parse_value(output: str, label: str):
    pattern = rf"{re.escape(label)}\s*:\s*(.+)"
    match = re.search(pattern, output)
    return match.group(1).strip() if match else None


def run_script(script_path: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [PYTHON_EXE, str(script_path)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
    )

    combined = []
    if proc.stdout:
        combined.append(proc.stdout)
    if proc.stderr:
        combined.append("\n[STDERR]\n")
        combined.append(proc.stderr)

    return proc.returncode, "".join(combined)


def main():
    print("=" * 72)
    print("Gamma Engine - Full Sweep Loop Runner")
    print("Manual catch-up mode (not trading-day gated)")
    print("=" * 72)

    session_id = now_stamp()
    session_log = LOG_DIR / f"loop_runner_full_sweep_{session_id}.log"

    print(f"Python executable     : {PYTHON_EXE}")
    print(f"Ingest script         : {INGEST_SCRIPT}")
    print(f"Daily rebuild script  : {DAILY_REBUILD_SCRIPT}")
    print(f"Coverage script       : {COVERAGE_SCRIPT}")
    print(f"Session log           : {session_log}")
    print(f"Max runs              : {MAX_RUNS}")
    print("=" * 72)

    if not INGEST_SCRIPT.exists():
        print(f"ERROR: Ingest script not found: {INGEST_SCRIPT}")
        sys.exit(1)

    if not DAILY_REBUILD_SCRIPT.exists():
        print(f"ERROR: Daily rebuild script not found: {DAILY_REBUILD_SCRIPT}")
        sys.exit(1)

    if not COVERAGE_SCRIPT.exists():
        print(f"ERROR: Coverage script not found: {COVERAGE_SCRIPT}")
        sys.exit(1)

    for run_no in range(1, MAX_RUNS + 1):
        print()
        print("-" * 72)
        print(f"Run {run_no}/{MAX_RUNS}")
        print("-" * 72)

        ingest_rc, ingest_output = run_script(INGEST_SCRIPT)
        print(ingest_output)

        daily_rc = None
        daily_output = ""
        coverage_rc = None
        coverage_output = ""

        next_cursor = parse_value(ingest_output, "Next cursor")
        status = parse_value(ingest_output, "Status")
        failures = parse_value(ingest_output, "Failures")
        processed = parse_value(ingest_output, "Processed")
        candles = parse_value(ingest_output, "Candles upserted")

        if ingest_rc == 0:
            daily_rc, daily_output = run_script(DAILY_REBUILD_SCRIPT)
            print("-" * 72)
            print("DAILY REBUILD OUTPUT")
            print("-" * 72)
            print(daily_output)

            coverage_rc, coverage_output = run_script(COVERAGE_SCRIPT)
            print("-" * 72)
            print("COVERAGE AFTER RUN")
            print("-" * 72)
            print(coverage_output)

        with session_log.open("a", encoding="utf-8") as f:
            f.write("\n" + "=" * 80 + "\n")
            f.write(f"RUN {run_no} | {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n")
            f.write("INGEST OUTPUT\n")
            f.write("-" * 80 + "\n")
            f.write(ingest_output)
            f.write("\n")
            f.write("DAILY REBUILD OUTPUT\n")
            f.write("-" * 80 + "\n")
            f.write(daily_output)
            f.write("\n")
            f.write("COVERAGE OUTPUT\n")
            f.write("-" * 80 + "\n")
            f.write(coverage_output)
            f.write("\n")

        print("-" * 72)
        print("Parsed summary")
        print(f"Processed       : {processed}")
        print(f"Candles upserted: {candles}")
        print(f"Failures        : {failures}")
        print(f"Next cursor     : {next_cursor}")
        print(f"Status          : {status}")
        print(f"Ingest rc       : {ingest_rc}")
        print(f"Daily rebuild rc: {daily_rc}")
        print(f"Coverage rc     : {coverage_rc}")

        if ingest_rc != 0:
            print(f"Stopping because ingest script returned non-zero exit code: {ingest_rc}")
            break

        if daily_rc not in (0, None):
            print(f"Stopping because daily rebuild script returned non-zero exit code: {daily_rc}")
            break

        if coverage_rc not in (0, None):
            print(f"Stopping because coverage script returned non-zero exit code: {coverage_rc}")
            break

        if next_cursor is None:
            print("Stopping because 'Next cursor' could not be parsed.")
            break

        if next_cursor == "0":
            print("Stopping because cursor returned to 0 after progressing through the universe.")
            break

        time.sleep(SLEEP_BETWEEN_RUNS_SEC)

    print()
    print("=" * 72)
    print("Full sweep loop runner finished")
    print(f"Session log saved to: {session_log}")
    print("=" * 72)


if __name__ == "__main__":
    main()