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
  - Cron (AWS, UTC): TWO lines, the second APPENDED after the first (S98-E.1 D2).
      Order is load-bearing: monitor_orchestrator_health.parse_orchestrator_window
      returns on its FIRST matching line, so appending leaves the monitor's alert
      window at 03:10-10:00 UTC and prepending would collapse it to 10:10-10:15.
        */5 03-09 * * 1-5    -> 08:30-15:25 IST, the main session
        0,5,10 10 * * 1-5    -> 15:30 / 15:35 / 15:40 IST, the three closing cycles
      NO `timeout` wrapper: a cycle may now WAIT up to CYCLE_WAIT_S for its own
      chain run (S98_CYCLE_WAIT), so a wrapper shorter than that wait would kill
      the cycle it is meant to protect.

Session: S46 (2026-06-06); TD-S54-NEW-1 fix S55 (2026-06-17)
Version: Shadow Pipeline v2 (AWS Phase 2.c, per-symbol run_id)
"""

from __future__ import annotations

import os
import subprocess
from core.trading_calendar_gate import is_trading_day_today
import sys
import time
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

# S90_ENH133_WIRE (ruling S90-F, ADR-030): per-cycle layer history. OFF SWITCH: set False.
# A code constant, not a parameter: a parameter read can fail open (roadmap risk 14).
ENH133_WRITER_ENABLED: bool = True

# S98_CYCLE_WAIT (ruling S98-E): the runner waits for ITS OWN cycle's chain run.
# Code constants, not parameters -- a parameter read can fail open (roadmap risk 14),
# and failing open here restores exactly the behaviour this patch removes.
#
# CYCLE_WAIT_S is bounded by what the monitor tolerates, not by patience: the
# orchestrator's ledger row is written at cycle start, and
# monitor_orchestrator_health.LOOKBACK_MIN is 7 min, so a wait must stay well inside
# that or a waiting cycle reads as "not firing". 120 s = 2 min leaves 5 min of margin.
CYCLE_WAIT_S = 120
POLL_S = 5


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
                    # S81-FRONT-EXPIRY-RUNID -- was order="created_at.desc".
                    # W1 and the S80 extra expiries share ONE ts (ingest sets
                    # snapshot_ts once and reuses it) but NOT created_at, which
                    # is a DB default and is therefore LATER for the extra
                    # pass. Ordering by created_at.desc would hand every
                    # downstream compute W2's run_id the moment EXPIRY_DEPTH
                    # exceeds 1 -- silently, with no guard tripping, because
                    # each run_id is still single-expiry.
                    #
                    # NO ">= today" guard here, deliberately, and unlike the
                    # views. The ingest never writes past expiries, and a
                    # no-fallback guard in the orchestrator turns an edge case
                    # into a compute outage: no run_id means gamma does not run
                    # at all. Failing to absent is right for a display read; it
                    # is wrong for the thing that feeds the whole compute chain.
                    order="ts.desc,expiry_date.asc",
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


def _cycle_floor(now_utc: datetime) -> datetime:
    """Floor `now_utc` to the 5-minute cycle boundary it belongs to.

    ONE implementation, called by both fetch_cycle_run_ids and main(). A second
    copy in the caller would be a parity claim asserted by a comment (rule 0).
    """
    return now_utc.replace(minute=(now_utc.minute // 5) * 5, second=0, microsecond=0)


def _cycle_floor_z(now_utc: datetime) -> str:
    """The cycle floor as a PostgREST-safe timestamp string.

    Z form, NEVER isoformat(): a literal "+00:00" inside a filter decodes as a SPACE
    in any layer that builds the query string by hand rather than letting requests
    encode the params, and a mocked test cannot see that failure. astimezone first,
    so the literal "Z" is true by construction and not an assumption about the caller.

    ONE implementation, shared by fetch_cycle_run_ids and main(). Two copies would be
    a parity claim asserted by a comment (rule 0).
    """
    return _cycle_floor(now_utc).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# S98_CYCLE_WAIT: newest ts per symbol with NO cycle filter, populated ONLY for
# symbols that were missing when the wait ended. Read by main() for the ledger's
# error_message. A module-level handoff in the same shape as LAST_FAILED_STEPS
# (S90_RUNNER_LEDGER) -- the alternative is widening the function's return type,
# which ruling S98-E fixes as "return the found map".
LAST_NEWEST_TS: Dict[str, Optional[str]] = {}


def _newest_ts(sb: SupabaseClient, symbol: str) -> Optional[str]:
    """Newest `ts` for `symbol` with the cycle filter REMOVED. Diagnostics only.

    This is the one read that deliberately ignores the cycle boundary, and it exists
    so a stale-input log says WHAT it found instead of only what it wanted: "no chain
    run at or after 10:00Z" and "newest is yesterday 15:40" are the same exit code and
    different incidents. Same order and limit as the cycle read, so the row it names is
    the row the cycle read would have taken had the filter not excluded it.

    Never raises: a failed diagnostic must not change the exit path it is describing.
    """
    try:
        rows = retry_call(
            lambda: sb.select(
                table="option_chain_snapshots",
                filters={"symbol": f"eq.{symbol}"},
                order="ts.desc,expiry_date.asc",
                limit=1,
            ),
            attempts=2,
            delay_seconds=1.0,
            backoff_multiplier=1.5,
            label=f"newest ts probe for {symbol}",
        )
        if rows:
            return rows[0].get("ts")
    except Exception as e:
        log_message(f"newest-ts probe failed for {symbol}: {e}", "WARN")
    return None


def _newest_ts_phrase(symbols: List[str]) -> str:
    """`newest ts NIFTY=<ts|none> SENSEX=<ts|none>` -- one wording, three call sites."""
    return "newest ts " + " ".join(
        f"{s}={LAST_NEWEST_TS.get(s) or 'none'}" for s in symbols
    )


def fetch_cycle_run_ids(
    sb: SupabaseClient,
    now_utc: datetime,
    sleep=time.sleep,
    clock=time.monotonic,
) -> Dict[str, str]:
    """
    S98_CYCLE_WAIT (ruling S98-E): resolve the run_id of THIS CYCLE's chain run,
    per symbol, waiting up to CYCLE_WAIT_S for the ingest to land.

    The select is the one fetch_latest_run_ids uses -- same order, same limit, and
    the same front-expiry reasoning (S81-FRONT-EXPIRY-RUNID) -- plus ONE added
    filter: ts >= the cycle floor. That filter is the whole patch. Without it the
    newest row of ANY age qualifies, so a stalled ingest silently recomputes the
    previous cycle, or yesterday's close, and every step exits 0.

    No fallback to the newest row. A cycle with no chain run of its own has no
    input, and saying so is the point; computing something else is the defect.

    `sleep` and `clock` are injected so the wait is testable without wall time.
    """
    floor_iso = _cycle_floor_z(now_utc)
    run_ids: Dict[str, str] = {}
    # Before the loop: a previous cycle's probe values must never be readable as this
    # cycle's. clear(), not reassignment -- main() reads the module-level name.
    LAST_NEWEST_TS.clear()
    t0 = clock()
    polls = 0
    waited = 0.0

    while True:
        polls += 1
        for symbol in SYMBOLS:
            if symbol in run_ids:
                continue
            try:
                rows = retry_call(
                    lambda s=symbol: sb.select(
                        table="option_chain_snapshots",
                        filters={"symbol": f"eq.{s}", "ts": f"gte.{floor_iso}"},
                        order="ts.desc,expiry_date.asc",
                        limit=1,
                    ),
                    attempts=3,
                    delay_seconds=2.0,
                    backoff_multiplier=1.5,
                    label=f"fetch cycle run_id for {symbol}",
                )
                if rows:
                    rid = rows[0].get("run_id")
                    if rid:
                        run_ids[symbol] = rid
            except Exception as e:
                log_message(f"Failed to fetch cycle run_id for {symbol}: {e}", "ERROR")

        waited = clock() - t0
        if len(run_ids) == len(SYMBOLS):
            break
        if waited >= CYCLE_WAIT_S:
            break
        sleep(POLL_S)

    missing = [s for s in SYMBOLS if s not in run_ids]
    # One extra, unfiltered select per MISSING symbol only -- zero when the cycle is
    # complete, which is every healthy cycle. This is what turns "nothing at or after
    # 10:00Z" into a diagnosis.
    for symbol in missing:
        LAST_NEWEST_TS[symbol] = _newest_ts(sb, symbol)

    line = (f"[CYCLE WAIT] cycle_floor={floor_iso} "
            f"waited={waited:.1f}s/{CYCLE_WAIT_S}s polls={polls} "
            f"found={sorted(run_ids.keys())} missing={missing}")
    if missing:
        line += "; " + _newest_ts_phrase(missing)
    log_message(line, "WARN" if missing else "INFO")
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

    # S90_ENH133_WIRE: after gamma AND volatility (v_gex_strike_rank / v_gex_strike_walls read
    # volatility_snapshots), before the symbol-keyed steps. Non-fatal like every step.
    if ENH133_WRITER_ENABLED:
        for symbol, run_id in run_ids.items():
            steps.append((
                ["python3", "write_gex_cycle_history_local.py", run_id],
                f"write_gex_cycle_history {symbol}",
                90,
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
            ["python3", "compute_basis_context_local.py"],
            "compute_basis_context NIFTY+SENSEX",
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
    LAST_FAILED_STEPS.clear()  # S90_RUNNER_LEDGER

    for cmd, label, timeout in steps:
        if not run_compute_step(cmd, label, timeout):
            failed_steps.append(label)
            LAST_FAILED_STEPS.append(label)
            # Continue to next step (don't fail fast, so we see which steps break)

    if failed_steps:
        log_message(f"======= PIPELINE FAILED: {len(failed_steps)} step(s) =======", "ERROR")
        for step in failed_steps:
            log_message(f"  - {step}", "ERROR")
        return False

    log_message("======= PIPELINE COMPLETE =======")
    return True


# S90_RUNNER_LEDGER (ADR-031 D7.4, R01-F1): one script_execution_log row per cycle.
# The ledger never blocks compute: any ledger error is logged and swallowed.
LAST_FAILED_STEPS: List[str] = []


def _ledger_open():
    try:
        return ExecutionLog(script_name="run_merdian_shadow_runner_aws.py", expected_writes={})
    except Exception as e:
        log_message(f"[LEDGER] open failed (compute continues): {e}", "WARN")
        return None


def _ledger_close(led, rc: int, reason: str, notes: str = "", error: str = "") -> int:
    if led is not None:
        try:
            if reason == "SUCCESS":
                led.complete(notes=notes or None)
            else:
                led.exit_with_reason(reason, exit_code=rc, notes=notes or None, error_message=error or None)
        except Exception as e:
            log_message(f"[LEDGER] close failed: {e}", "WARN")
    return rc


def main() -> int:
    """
    Main entry point.
    1. Verify Supabase connectivity
    2. Fetch the latest run_id PER SYMBOL from ingest
    3. Execute full compute pipeline
    4. Log results
    """
    log_message("Shadow Runner starting (S46 Phase 2.c; TD-S54-NEW-1 per-symbol run_id)")
    led = _ledger_open()
    # Holiday gate (TD-S60-NEW-2): reads the corrected trading_calendar; fail-open.
    # Closes the gap that ran the full compute chain on Muharram 2026-06-26.
    if not is_trading_day_today():  # TD-S60-NEW-3: shared core helper
        log_message("[HOLIDAY GATE] Market closed today -- orchestrator exiting (no compute).")
        return _ledger_close(led, 0, "HOLIDAY_GATE")

    # Initialize Supabase client
    try:
        sb = SupabaseClient()
    except Exception as e:
        log_message(f"Failed to initialize Supabase: {e}", "ERROR")
        return _ledger_close(led, 1, "DATA_ERROR", error=f"supabase init: {e}")

    # S98_CYCLE_WAIT: THIS cycle's run_id per symbol, waiting up to CYCLE_WAIT_S.
    # fetch_latest_run_ids is deliberately no longer called -- it accepts the newest
    # row of any age, which is the behaviour ruling S98-E removes. It is kept in the
    # file, unused, so a rollback reader can see the previous contract.
    _now = datetime.now(timezone.utc)
    _floor_z = _cycle_floor_z(_now)
    run_ids = fetch_cycle_run_ids(sb, _now)
    if not run_ids:
        # Ruling S98-E.1 D3: SKIPPED_NO_INPUT, which is what this branch already
        # passed pre-patch and is already in VALID_EXIT_REASONS. The exit reason is
        # unchanged; what changed is that the input is now cycle-scoped, so this
        # branch now fires on a STALE ingest as well as an absent one -- and the
        # error text has to carry which of the two it was, because the reason cannot.
        _err = (f"S98_CYCLE_WAIT no chain run at or after {_floor_z} within "
                f"{CYCLE_WAIT_S}s; {_newest_ts_phrase(SYMBOLS)}")
        log_message(_err, "ERROR")
        return _ledger_close(led, 1, "SKIPPED_NO_INPUT", error=_err)

    missing = [s for s in SYMBOLS if s not in run_ids]
    if missing:
        log_message(
            f"No chain run at or after {_floor_z} for {missing} this cycle "
            f"(that symbol's ingest may not have fired); "
            f"{_newest_ts_phrase(missing)}; "
            f"computing {list(run_ids.keys())} only.",
            "WARN",
        )

    log_message(f"Using run_ids: {run_ids}")

    # Execute pipeline
    success = execute_pipeline(run_ids)

    if success:
        log_message("Shadow runner cycle complete (contract met)", "INFO")
        return _ledger_close(led, 0, "SUCCESS", notes=f"run_ids={run_ids}")
    else:
        log_message("Shadow runner cycle failed (contract not met)", "ERROR")
        return _ledger_close(led, 1, "DATA_ERROR", notes=f"run_ids={run_ids}",
                             error="failed steps: " + ", ".join(LAST_FAILED_STEPS))


if __name__ == "__main__":
    sys.exit(main())
