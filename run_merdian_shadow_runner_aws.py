#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MERDIAN Shadow Runner for AWS (Phase 2.c Parallel Test)

Purpose:
  Execute the full 5-minute compute pipeline on AWS EC2, writing to *_shadow tables.
  Replaces Local's run_option_snapshot_intraday_runner.py for AWS deployment.

  Orchestrates the per-cycle compute steps:
    1-2.  compute_gamma_metrics      (ONE call per symbol, via that symbol's run_id)
    3-4.  compute_volatility_metrics (ONE call per symbol, via that symbol's run_id)
    5-6.  build_momentum_features    (NIFTY, SENSEX)
    7-8.  build_wcb_snapshot         (NIFTY, SENSEX)
    9-10. build_market_state_snapshot(NIFTY, SENSEX)
    11-12.build_trade_signal         (NIFTY, SENSEX)

Architecture:
  - Called by cron every 5 minutes (09:15-15:30 IST = 03:45-10:00 UTC)
  - Pulls the latest run_id PER SYMBOL from option_chain_snapshots
    (upstream ingest must have fired for that symbol this cycle).
  - A single run_id maps to a SINGLE symbol's ingest. The run_id-keyed
    compute steps (gamma, volatility) therefore MUST be invoked once per
    symbol, each with that symbol's own run_id. (TD-S54-NEW-1: the prior
    single-run_id design silently computed only whichever symbol's ingest
    landed last in created_at order, dropping the other symbol's gamma/
    volatility/market_state row that cycle with an exit-0 "OK" log.)
  - Each step runs as a subprocess with timeout and error handling.
  - Writes go to production tables (no --shadow flag; ADR-006 / S48).
  - Logs to file + script_execution_log (ENH-72)

Deployment:
  - File: /home/ssm-user/meridian-engine/run_merdian_shadow_runner_aws.py
  - Cron: 15,20,25,30,35,40,45,50,55 03,04,05,06,07,08,09,10 * * 1-5 \
            timeout 90 python /home/ssm-user/meridian-engine/run_merdian_shadow_runner_aws.py

Session: S46 (2026-06-06); TD-S54-NEW-1 fix S55 (2026-06-17)
Version: Shadow Pipeline v2 (AWS Phase 2.c, per-symbol run_id)
"""

from __future__ import annotations

import os
import subprocess
from core.trading_calendar_gate import is_trading_day_today
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ENH-72 write-contract layer
from core.execution_log import ExecutionLog
from core.supabase_client import SupabaseClient
from gamma_engine_retry_utils import retry_call


IST = ZoneInfo("Asia/Kolkata")
LOG_FILE = "/home/ssm-user/meridian-engine/shadow_runner.log"

# Symbols computed every cycle. The run_id-keyed compute steps (gamma,
# volatility) are invoked once per symbol using each symbol's own latest
# run_id; the symbol-keyed downstream steps are invoked per symbol directly.
SYMBOLS: List[str] = ["NIFTY", "SENSEX"]


def log_message(msg: str, level: str = "INFO") -> None:
    """Log to file and stdout."""
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"[ERROR] Failed to write to log file: {e}", file=sys.stderr)


def fetch_latest_run_ids(sb: SupabaseClient) -> Dict[str, str]:
    """
    Query the most recent run_id PER SYMBOL from option_chain_snapshots.

    A run_id corresponds to a single ingest call, which is a single symbol.
    Returning the global latest run_id (the prior behaviour) computed only
    one symbol per cycle and silently dropped the other (TD-S54-NEW-1).

    Returns a {symbol: run_id} map containing only the symbols that have a
    row in option_chain_snapshots. A symbol whose ingest has not fired is
    omitted (its absence is logged by the caller).
    """
    run_ids: Dict[str, str] = {}
    for symbol in SYMBOLS:
        try:
            rows = retry_call(
                lambda s=symbol: sb.select(
                    table="option_chain_snapshots",
                    filters={"symbol": f"eq.{s}"},
                    order="created_at.desc",
                    limit=1,
                ),
                attempts=3,
                delay_seconds=2.0,
                backoff_multiplier=1.5,
                label=f"fetch latest run_id for {symbol}",
            )
            if rows:
                rid = rows[0].get("run_id")
                if rid:
                    run_ids[symbol] = rid
        except Exception as e:
            log_message(f"Failed to fetch run_id for {symbol}: {e}", "ERROR")
    return run_ids


def run_compute_step(
    cmd: List[str],
    label: str,
    timeout_seconds: int = 60,
) -> bool:
    """
    Execute a compute step subprocess.
    Returns True on success, False on failure.
    Logs output to file and stdout.
    """
    log_message(f"Starting: {label}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd="/home/ssm-user/meridian-engine",
        )

        # Log stdout
        if result.stdout:
            log_message(f"{label} stdout:\n{result.stdout}", "DEBUG")

        # Check return code
        if result.returncode != 0:
            log_message(f"{label} FAILED (exit code {result.returncode})", "ERROR")
            if result.stderr:
                log_message(f"{label} stderr:\n{result.stderr}", "ERROR")
            return False

        log_message(f"{label} OK", "INFO")
        return True

    except subprocess.TimeoutExpired:
        log_message(f"{label} TIMEOUT (exceeded {timeout_seconds}s)", "ERROR")
        return False
    except Exception as e:
        log_message(f"{label} EXCEPTION: {e}", "ERROR")
        return False


def execute_pipeline(run_ids: Dict[str, str]) -> bool:
    """
    Execute the full 5-minute compute pipeline in sequence.

    run_id-keyed steps (gamma, volatility) run ONCE PER SYMBOL, each with
    that symbol's own run_id, so both NIFTY and SENSEX are computed every
    cycle. symbol-keyed downstream steps run per symbol as before.

    Writes go to production tables (no --shadow flag; ADR-006 / S48).
    Returns True if all steps succeed, False if any step fails.
    """
    log_message(f"======= PIPELINE START (run_ids={run_ids}) =======")

    steps: List[tuple[List[str], str, int]] = []

    # --- run_id-keyed compute steps: one invocation per symbol ---
    for symbol, run_id in run_ids.items():
        steps.append((
            ["python3", "compute_gamma_metrics_local.py", run_id],
            f"compute_gamma_metrics {symbol}",
            60,
        ))
    for symbol, run_id in run_ids.items():
        steps.append((
            ["python3", "compute_volatility_metrics_local.py", run_id],
            f"compute_volatility_metrics {symbol}",
            60,
        ))

    # --- symbol-keyed downstream steps: always both symbols ---
    steps.extend([
        (
            ["python3", "build_momentum_features_local.py", "NIFTY"],
            "build_momentum_features NIFTY",
            30,
        ),
        (
            ["python3", "build_momentum_features_local.py", "SENSEX"],
            "build_momentum_features SENSEX",
            30,
        ),
        (
            ["python3", "build_wcb_snapshot_local.py", "NIFTY"],
            "build_wcb_snapshot NIFTY",
            45,
        ),
        (
            ["python3", "build_wcb_snapshot_local.py", "SENSEX"],
            "build_wcb_snapshot SENSEX",
            45,
        ),
        (
            ["python3", "build_market_state_snapshot_local.py", "NIFTY"],
            "build_market_state_snapshot NIFTY",
            30,
        ),
        (
            ["python3", "build_market_state_snapshot_local.py", "SENSEX"],
            "build_market_state_snapshot SENSEX",
            30,
        ),
        # ENH-SDM P2 (display-not-gate): reads gamma_metrics, writes
        # structural_divergence_snapshots. Placed after market_state, before
        # trade_signal; failure is non-fatal (failed_steps tally) and nothing
        # downstream routes on it.
        (
            ["python3", "compute_structural_divergence_local.py", "NIFTY"],
            "compute_structural_divergence NIFTY",
            30,
        ),
        (
            ["python3", "compute_structural_divergence_local.py", "SENSEX"],
            "compute_structural_divergence SENSEX",
            30,
        ),
        (
            ["python3", "compute_options_flow_local.py"],
            "compute_options_flow NIFTY+SENSEX",
            60,
        ),
        (
            ["python3", "build_trade_signal_local.py", "NIFTY"],
            "build_trade_signal NIFTY",
            45,
        ),
        (
            ["python3", "build_trade_signal_local.py", "SENSEX"],
            "build_trade_signal SENSEX",
            45,
        ),
    ])

    failed_steps: List[str] = []

    for cmd, label, timeout in steps:
        if not run_compute_step(cmd, label, timeout):
            failed_steps.append(label)
            # Continue to next step (don't fail fast, so we see which steps break)

    if failed_steps:
        log_message(f"======= PIPELINE FAILED: {len(failed_steps)} step(s) =======", "ERROR")
        for step in failed_steps:
            log_message(f"  - {step}", "ERROR")
        return False

    log_message("======= PIPELINE COMPLETE =======")
    return True


def main() -> int:
    """
    Main entry point.
    1. Verify Supabase connectivity
    2. Fetch the latest run_id PER SYMBOL from ingest
    3. Execute full compute pipeline
    4. Log results
    """
    log_message("Shadow Runner starting (S46 Phase 2.c; TD-S54-NEW-1 per-symbol run_id)")
    # Holiday gate (TD-S60-NEW-2): reads the corrected trading_calendar; fail-open.
    # Closes the gap that ran the full compute chain on Muharram 2026-06-26.
    if not is_trading_day_today():  # TD-S60-NEW-3: shared core helper
        log_message("[HOLIDAY GATE] Market closed today -- orchestrator exiting (no compute).")
        return 0

    # Initialize Supabase client
    try:
        sb = SupabaseClient()
    except Exception as e:
        log_message(f"Failed to initialize Supabase: {e}", "ERROR")
        return 1

    # Fetch latest run_id per symbol from upstream ingest
    run_ids = fetch_latest_run_ids(sb)
    if not run_ids:
        log_message(
            "No run_id found for any symbol in option_chain_snapshots. "
            "Ingest may not have fired yet.",
            "WARN",
        )
        return 1

    missing = [s for s in SYMBOLS if s not in run_ids]
    if missing:
        log_message(
            f"No latest run_id for {missing} this cycle "
            f"(that symbol's ingest may not have fired); computing {list(run_ids.keys())} only.",
            "WARN",
        )

    log_message(f"Using run_ids: {run_ids}")

    # Execute pipeline
    success = execute_pipeline(run_ids)

    if success:
        log_message("Shadow runner cycle complete (contract met)", "INFO")
        return 0
    else:
        log_message("Shadow runner cycle failed (contract not met)", "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())
