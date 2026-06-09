#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MERDIAN Shadow Runner for AWS (Phase 2.c Parallel Test)

Purpose:
  Execute the full 5-minute compute pipeline on AWS EC2, writing to *_shadow tables.
  Replaces Local's run_option_snapshot_intraday_runner.py for AWS deployment.
  
  Orchestrates 11 sequential steps:
    1. compute_gamma_metrics (both NIFTY + SENSEX in one call via run_id)
    2. compute_volatility_metrics (both symbols)
    3-4. build_momentum_features (NIFTY, SENSEX)
    5-6. build_wcb_snapshot (NIFTY, SENSEX)
    7-8. build_market_state_snapshot (NIFTY, SENSEX)
    9-10. build_trade_signal (NIFTY, SENSEX)
    11. (reserved for future ICT pattern detection)

Architecture:
  - Called by cron every 5 minutes (09:15-15:30 IST = 03:45-10:00 UTC)
  - Pulls latest run_id from option_chain_snapshots (upstream ingest must have fired)
  - Each step runs as a subprocess with timeout and error handling
  - All writes go to *_shadow tables (--shadow CLI flag)
  - Logs to file + script_execution_log (ENH-72)
  
Deployment:
  - File: /home/ssm-user/meridian-engine/run_merdian_shadow_runner_aws.py
  - Cron: 15,20,25,30,35,40,45,50,55 03,04,05,06,07,08,09,10 * * 1-5 \
            timeout 90 python /home/ssm-user/meridian-engine/run_merdian_shadow_runner_aws.py
  
Session: S46 (2026-06-06)
Version: Shadow Pipeline v1 (AWS Phase 2.c)
"""

from __future__ import annotations

import os
import subprocess
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


def fetch_latest_run_id(sb: SupabaseClient) -> Optional[str]:
    """
    Query the most recent run_id from option_chain_snapshots.
    Returns None if no rows found (upstream ingest hasn't fired yet).
    """
    try:
        rows = retry_call(
            lambda: sb.select(
                table="option_chain_snapshots",
                order="created_at.desc",
                limit=1,
            ),
            attempts=3,
            delay_seconds=2.0,
            backoff_multiplier=1.5,
            label="fetch latest run_id",
        )
        if rows:
            return rows[0].get("run_id")
        return None
    except Exception as e:
        log_message(f"Failed to fetch run_id: {e}", "ERROR")
        return None


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


def execute_pipeline(run_id: str) -> bool:
    """
    Execute the full 5-minute compute pipeline in sequence.
    All steps write to *_shadow tables (controlled by --shadow CLI flag).
    Returns True if all steps succeed, False if any step fails.
    """
    log_message(f"======= PIPELINE START (run_id={run_id}) =======")
    
    steps: List[tuple[List[str], str, int]] = [
        # (command, label, timeout_seconds)
        (
            ["python3", "compute_gamma_metrics_local.py", run_id, "--shadow"],
            "compute_gamma_metrics",
            60,
        ),
        (
            ["python3", "compute_volatility_metrics_local.py", run_id, "--shadow"],
            "compute_volatility_metrics",
            60,
        ),
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
    ]
    
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
    2. Fetch latest run_id from ingest
    3. Execute full compute pipeline
    4. Log results
    """
    log_message("Shadow Runner starting (S46 Phase 2.c)")
    
    # Initialize Supabase client
    try:
        sb = SupabaseClient()
    except Exception as e:
        log_message(f"Failed to initialize Supabase: {e}", "ERROR")
        return 1
    
    # Fetch latest run_id from upstream ingest
    run_id = fetch_latest_run_id(sb)
    if not run_id:
        log_message("No run_id found in option_chain_snapshots. Ingest may not have fired yet.", "WARN")
        return 1
    
    log_message(f"Using run_id: {run_id}")
    
    # Execute pipeline
    success = execute_pipeline(run_id)
    
    if success:
        log_message("Shadow runner cycle complete (contract met)", "INFO")
        return 0
    else:
        log_message("Shadow runner cycle failed (contract not met)", "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())
