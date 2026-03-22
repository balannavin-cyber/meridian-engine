from __future__ import annotations

import subprocess
from datetime import datetime


SYMBOLS = [
    "NIFTY",
    "SENSEX",
]


def run_command(cmd: list[str]) -> int:
    print(f"[{datetime.now()}] Running: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print(result.stderr)

    if result.returncode != 0:
        print(f"ERROR: command failed with code {result.returncode}")
        return result.returncode

    return 0


def run_ingest(symbol: str) -> str | None:
    cmd = ["python", "ingest_option_chain_local.py", symbol]

    print("------------------------------------------------------------")
    print(f"INGESTING OPTION CHAIN FOR {symbol}")
    print("------------------------------------------------------------")

    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.stdout:
        print(proc.stdout)

    if proc.stderr:
        print(proc.stderr)

    if proc.returncode != 0:
        print("ERROR during ingest")
        return None

    run_id = None
    for line in proc.stdout.splitlines():
        if "Run ID:" in line:
            run_id = line.split("Run ID:")[-1].strip()

    return run_id


def run_gamma(run_id: str) -> int:
    print("------------------------------------------------------------")
    print("COMPUTING GAMMA METRICS")
    print("------------------------------------------------------------")

    cmd = ["python", "compute_gamma_metrics_local.py", run_id]
    return run_command(cmd)


def run_volatility(run_id: str) -> int:
    print("------------------------------------------------------------")
    print("COMPUTING VOLATILITY METRICS")
    print("------------------------------------------------------------")

    cmd = ["python", "compute_volatility_metrics_local.py", run_id]
    return run_command(cmd)


def run_market_state(symbol: str) -> int:
    print("------------------------------------------------------------")
    print("BUILDING MARKET STATE SNAPSHOT")
    print("------------------------------------------------------------")

    cmd = ["python", "build_market_state_snapshot_local.py", symbol]
    return run_command(cmd)


def run_pipeline(symbol: str) -> None:
    run_id = run_ingest(symbol)

    if not run_id:
        print("ERROR: run_id not found, skipping downstream computation")
        return

    print(f"Run ID detected: {run_id}")

    gamma_rc = run_gamma(run_id)
    if gamma_rc != 0:
        print("ERROR: gamma metrics failed, skipping downstream steps")
        return

    vol_rc = run_volatility(run_id)
    if vol_rc != 0:
        print("ERROR: volatility metrics failed, skipping market-state build")
        return

    ms_rc = run_market_state(symbol)
    if ms_rc != 0:
        print("ERROR: market-state snapshot build failed")
        return


def main() -> None:
    print("=" * 72)
    print("Gamma Engine - Options Snapshot + Gamma + Volatility + Market State Runner")
    print("=" * 72)

    for symbol in SYMBOLS:
        run_pipeline(symbol)

    print("=" * 72)
    print("OPTIONS PIPELINE COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    main()