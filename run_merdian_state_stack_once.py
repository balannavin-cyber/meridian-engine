from __future__ import annotations

import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
PYTHON_EXE = sys.executable


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def print_banner(title: str) -> None:
    print("=" * 72)
    print(title)
    print("=" * 72)


def run_command(label: str, args: list[str]) -> None:
    print_banner(f"RUNNING: {label}")
    print(f"Command: {' '.join(args)}")
    print("-" * 72)

    result = subprocess.run(args, cwd=ROOT)

    print("-" * 72)
    if result.returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {result.returncode}")

    print(f"COMPLETED: {label}")


def get_env(name: str, required: bool = True) -> str:
    value = os.getenv(name, "").strip()
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def fetch_latest_gamma_run_id(symbol: str) -> str:
    supabase_url = get_env("SUPABASE_URL")
    service_role = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()

    api_key = service_role or anon_key
    if not api_key:
        raise RuntimeError(
            "Missing SUPABASE_SERVICE_ROLE_KEY and SUPABASE_ANON_KEY in environment/.env"
        )

    url = (
        f"{supabase_url.rstrip('/')}/rest/v1/gamma_metrics"
        f"?symbol=eq.{symbol}"
        f"&select=run_id,ts,created_at"
        f"&order=ts.desc"
        f"&limit=1"
    )

    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code >= 400:
        raise RuntimeError(
            f"Failed to fetch latest gamma run_id for {symbol} | "
            f"HTTP {response.status_code} | response={response.text}"
        )

    rows = response.json()
    if not rows:
        raise RuntimeError(f"No gamma_metrics row found for symbol={symbol}")

    run_id = rows[0].get("run_id")
    if not run_id:
        raise RuntimeError(f"Latest gamma_metrics row missing run_id for symbol={symbol}")

    return run_id


def main() -> None:
    load_dotenv(ROOT / ".env", override=True)

    print_banner("MERDIAN - Run Full State Stack Once")
    print(f"Started at UTC: {utc_now_iso()}")
    print("Symbols: NIFTY, SENSEX")
    print("-" * 72)

    # IMPORTANT:
    # DO NOT capture market spot or futures here.
    # The 1-minute market tape runner owns those writes.
    # This stack must consume the latest tape already present in:
    #   - market_spot_snapshots
    #   - index_futures_snapshots

    print_banner("FETCHING LATEST GAMMA RUN IDS")
    nifty_run_id = fetch_latest_gamma_run_id("NIFTY")
    sensex_run_id = fetch_latest_gamma_run_id("SENSEX")
    print(f"NIFTY: latest gamma run_id = {nifty_run_id}")
    print(f"SENSEX: latest gamma run_id = {sensex_run_id}")
    print("-" * 72)

    run_command(
        f"compute_volatility_metrics_local.py NIFTY run_id={nifty_run_id}",
        [PYTHON_EXE, ".\\compute_volatility_metrics_local.py", nifty_run_id],
    )
    run_command(
        f"compute_volatility_metrics_local.py SENSEX run_id={sensex_run_id}",
        [PYTHON_EXE, ".\\compute_volatility_metrics_local.py", sensex_run_id],
    )

    run_command(
        "build_market_state_snapshot_local.py NIFTY",
        [PYTHON_EXE, ".\\build_market_state_snapshot_local.py", "NIFTY"],
    )
    run_command(
        "build_market_state_snapshot_local.py SENSEX",
        [PYTHON_EXE, ".\\build_market_state_snapshot_local.py", "SENSEX"],
    )

    run_command(
        "build_signal_state_snapshot_local.py NIFTY",
        [PYTHON_EXE, ".\\build_signal_state_snapshot_local.py", "NIFTY"],
    )
    run_command(
        "build_signal_state_snapshot_local.py SENSEX",
        [PYTHON_EXE, ".\\build_signal_state_snapshot_local.py", "SENSEX"],
    )

    run_command(
        "build_shadow_state_signal_local.py NIFTY",
        [PYTHON_EXE, ".\\build_shadow_state_signal_local.py", "NIFTY"],
    )
    run_command(
        "build_shadow_state_signal_local.py SENSEX",
        [PYTHON_EXE, ".\\build_shadow_state_signal_local.py", "SENSEX"],
    )

    run_command(
        "build_shadow_state_signal_outcomes_local.py",
        [PYTHON_EXE, ".\\build_shadow_state_signal_outcomes_local.py"],
    )

    print_banner("MERDIAN - FULL STATE STACK COMPLETED")
    print(f"Finished at UTC: {utc_now_iso()}")


if __name__ == "__main__":
    main()