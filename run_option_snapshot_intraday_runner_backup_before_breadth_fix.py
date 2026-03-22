from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone


SYMBOLS = [
    "NIFTY",
    "SENSEX",
]

IST = timezone(timedelta(hours=5, minutes=30))

SESSION_START_HOUR = 9
SESSION_START_MINUTE = 15

SESSION_END_HOUR = 15
SESSION_END_MINUTE = 30

RUN_INTERVAL_MINUTES = 5

LOG_FILE = "option_snapshot_intraday_runner.log"


def now_ist() -> datetime:
    return datetime.now(IST)


def log(message: str) -> None:
    ts = now_ist().strftime("%Y-%m-%d %H:%M:%S IST")
    line = f"[{ts}] {message}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def append_process_output(text: str) -> None:
    if not text:
        return
    print(text)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")


def run_command(cmd: list[str]) -> int:
    log(f"Running: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    append_process_output(result.stdout)
    append_process_output(result.stderr)

    if result.returncode != 0:
        log(f"ERROR: command failed with code {result.returncode}")
        return result.returncode

    return 0


def run_breadth_ingest() -> int:
    log("------------------------------------------------------------")
    log("INGESTING BREADTH INTRADAY")
    log("------------------------------------------------------------")

    cmd = ["python", "ingest_breadth_intraday_local.py"]
    return run_command(cmd)


def run_ingest(symbol: str) -> str | None:
    cmd = ["python", "ingest_option_chain_local.py", symbol]

    log("------------------------------------------------------------")
    log(f"INGESTING OPTION CHAIN FOR {symbol}")
    log("------------------------------------------------------------")

    proc = subprocess.run(cmd, capture_output=True, text=True)

    append_process_output(proc.stdout)
    append_process_output(proc.stderr)

    if proc.returncode != 0:
        log(f"ERROR during ingest for {symbol}")
        return None

    run_id = None
    for line in proc.stdout.splitlines():
        if "Run ID:" in line:
            run_id = line.split("Run ID:")[-1].strip()

    if not run_id:
        log(f"ERROR: run_id not found in ingest output for {symbol}")
        return None

    log(f"Run ID detected for {symbol}: {run_id}")
    return run_id


def run_gamma(run_id: str) -> int:
    log("------------------------------------------------------------")
    log("COMPUTING GAMMA METRICS")
    log("------------------------------------------------------------")

    cmd = ["python", "compute_gamma_metrics_local.py", run_id]
    return run_command(cmd)


def run_volatility(run_id: str) -> int:
    log("------------------------------------------------------------")
    log("COMPUTING VOLATILITY METRICS")
    log("------------------------------------------------------------")

    cmd = ["python", "compute_volatility_metrics_local.py", run_id]
    return run_command(cmd)


def run_momentum(symbol: str) -> int:
    log("------------------------------------------------------------")
    log(f"BUILDING MOMENTUM FEATURES FOR {symbol}")
    log("------------------------------------------------------------")

    cmd = ["python", "build_momentum_features_local.py", symbol]
    return run_command(cmd)


def run_market_state(symbol: str) -> int:
    log("------------------------------------------------------------")
    log(f"BUILDING MARKET STATE SNAPSHOT FOR {symbol}")
    log("------------------------------------------------------------")

    cmd = ["python", "build_market_state_snapshot_local.py", symbol]
    return run_command(cmd)


def run_pipeline_for_symbol(symbol: str) -> bool:
    run_id = run_ingest(symbol)

    if not run_id:
        log(f"ERROR: run_id not found for {symbol}, skipping downstream computation")
        return False

    gamma_rc = run_gamma(run_id)
    if gamma_rc != 0:
        log(f"ERROR: gamma metrics failed for {symbol}, skipping downstream steps")
        return False

    vol_rc = run_volatility(run_id)
    if vol_rc != 0:
        log(f"ERROR: volatility metrics failed for {symbol}, skipping downstream steps")
        return False

    momentum_rc = run_momentum(symbol)
    if momentum_rc != 0:
        log(f"ERROR: momentum build failed for {symbol}, skipping market-state build")
        return False

    ms_rc = run_market_state(symbol)
    if ms_rc != 0:
        log(f"ERROR: market-state snapshot build failed for {symbol}")
        return False

    log(f"Pipeline completed successfully for {symbol}")
    return True


def align_to_next_interval(dt: datetime, interval_minutes: int) -> datetime:
    minute_block = (dt.minute // interval_minutes) * interval_minutes
    aligned = dt.replace(minute=minute_block, second=0, microsecond=0)

    if aligned <= dt:
        aligned = aligned + timedelta(minutes=interval_minutes)

    return aligned


def session_bounds_for_today(dt: datetime) -> tuple[datetime, datetime]:
    session_start = dt.replace(
        hour=SESSION_START_HOUR,
        minute=SESSION_START_MINUTE,
        second=0,
        microsecond=0,
    )
    session_end = dt.replace(
        hour=SESSION_END_HOUR,
        minute=SESSION_END_MINUTE,
        second=0,
        microsecond=0,
    )
    return session_start, session_end


def is_weekday(dt: datetime) -> bool:
    return dt.weekday() < 5


def sleep_until(target_dt: datetime) -> None:
    while True:
        now = now_ist()
        seconds = (target_dt - now).total_seconds()
        if seconds <= 0:
            return
        sleep_seconds = min(seconds, 30)
        time.sleep(sleep_seconds)


def main() -> None:
    log("=" * 72)
    log("Gamma Engine - Intraday Unified Runner")
    log("=" * 72)
    log(f"Symbols: {', '.join(SYMBOLS)}")
    log(f"Interval: every {RUN_INTERVAL_MINUTES} minutes")
    log("Cycle order: breadth -> option ingest -> gamma -> volatility -> momentum -> market state")
    log("This runner does NOT use exchange holiday calendar yet.")
    log("It only skips weekends.")
    log("=" * 72)

    today_now = now_ist()

    if not is_weekday(today_now):
        log("Today is weekend. Exiting without running.")
        sys.exit(0)

    session_start, session_end = session_bounds_for_today(today_now)

    if today_now > session_end:
        log("Market session already ended for today. Exiting.")
        sys.exit(0)

    if today_now < session_start:
        log(f"Waiting until market session start: {session_start.isoformat()}")
        sleep_until(session_start)

    next_run = align_to_next_interval(now_ist(), RUN_INTERVAL_MINUTES)

    if next_run < session_start:
        next_run = session_start

    while True:
        now = now_ist()
        if now > session_end:
            log("Market session ended. Exiting runner.")
            break

        log(f"Next scheduled run at: {next_run.isoformat()}")
        sleep_until(next_run)

        cycle_start = now_ist()
        if cycle_start > session_end:
            log("Reached session end before cycle start. Exiting runner.")
            break

        log("=" * 72)
        log(f"STARTING INTRADAY CYCLE AT {cycle_start.isoformat()}")
        log("=" * 72)

        breadth_rc = run_breadth_ingest()
        if breadth_rc != 0:
            log("ERROR: breadth intraday ingest failed for this cycle")
        else:
            log("Breadth intraday ingest completed successfully")

        for symbol in SYMBOLS:
            run_pipeline_for_symbol(symbol)

        cycle_end = now_ist()
        log("=" * 72)
        log(f"COMPLETED INTRADAY CYCLE AT {cycle_end.isoformat()}")
        log("=" * 72)

        next_run = next_run + timedelta(minutes=RUN_INTERVAL_MINUTES)

    log("RUNNER FINISHED")


if __name__ == "__main__":
    main()