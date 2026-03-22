import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"C:\GammaEnginePython")
INGEST_SCRIPT = BASE_DIR / "ingest_ad_intraday_local.py"
PLOT_SCRIPT = BASE_DIR / "plot_ad_session.py"
LOG_FILE = BASE_DIR / "logs" / "run_ad_chart_refresh.log"
SLEEP_SECONDS = 60


def log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def run_script(script_path: Path) -> bool:
    if not script_path.exists():
        log(f"ERROR: Script not found: {script_path}")
        return False

    log(f"Running: {script_path.name}")
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True
    )

    if result.stdout.strip():
        log(f"{script_path.name} STDOUT:\n{result.stdout.strip()}")

    if result.stderr.strip():
        log(f"{script_path.name} STDERR:\n{result.stderr.strip()}")

    if result.returncode != 0:
        log(f"ERROR: {script_path.name} exited with code {result.returncode}")
        return False

    log(f"Completed: {script_path.name}")
    return True


def main() -> None:
    log("Starting A/D chart refresh loop. Press Ctrl+C to stop.")

    try:
        while True:
            ok_ingest = run_script(INGEST_SCRIPT)
            ok_plot = run_script(PLOT_SCRIPT) if ok_ingest else False

            if ok_ingest and ok_plot:
                log("Cycle complete: ingest + chart refresh successful.")
            else:
                log("Cycle complete with errors.")

            log(f"Sleeping for {SLEEP_SECONDS} seconds...")
            time.sleep(SLEEP_SECONDS)

    except KeyboardInterrupt:
        log("Stopped by user.")


if __name__ == "__main__":
    main()