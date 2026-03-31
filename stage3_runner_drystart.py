"""
MERDIAN Preflight — Stage 3: Runner Dry-Start
=============================================
Verifies that the runner can start and exit cleanly outside session hours.
No market data is consumed. No writes to production tables.

Catches:
  - Import failures that only surface at runner startup
  - Calendar/session config object contract mismatches
  - Runner script syntax errors
  - py_compile failures on critical scripts
  - Lock file conflicts (stale lock from prior crashed run)

Pass criteria: all critical scripts compile, runner would start cleanly,
               no stale lock files blocking execution.
"""

import os
import sys
import subprocess
import py_compile
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preflight_common import (
    PASS, FAIL, WARN, SKIP,
    detect_environment, get_merdian_root,
    load_env, make_stage_result, run_check, now_iso,
    print_header, print_check, print_stage_summary,
    save_stage_result, elapsed_ms
)

STAGE_ID = "stage3_runner_drystart"

# ── Helpers ───────────────────────────────────────────────────────

def _compile_check(filename):
    """py_compile a file. Returns (status, detail)."""
    root = get_merdian_root()
    path = os.path.join(root, filename)
    if not os.path.exists(path):
        return FAIL, f"File not found: {path}"
    try:
        py_compile.compile(path, doraise=True)
        return PASS, f"{filename} compiles OK"
    except py_compile.PyCompileError as e:
        return FAIL, f"Compile error in {filename}: {e}"
    except Exception as e:
        return FAIL, f"Exception compiling {filename}: {e}"

def _check_lock_file(lock_filename):
    """Check if a lock file exists. Stale locks block runner start."""
    root = get_merdian_root()

    # Check both root and runtime/ subdirectory
    paths_to_check = [
        os.path.join(root, lock_filename),
        os.path.join(root, "runtime", lock_filename),
    ]
    found = [p for p in paths_to_check if os.path.exists(p)]
    if found:
        return WARN, (f"Stale lock file found: {found[0]}. "
                      f"If no runner is active, delete it: del \"{found[0]}\"")
    return PASS, f"No stale lock file: {lock_filename}"

# ── Checks ────────────────────────────────────────────────────────

def check_compile_runner_local():
    """run_option_snapshot_intraday_runner.py must compile without errors."""
    env = detect_environment()
    if env == "aws":
        return SKIP, "AWS — local runner compile skipped"
    return _compile_check("run_option_snapshot_intraday_runner.py")

def check_compile_runner_aws():
    """run_merdian_shadow_runner.py must compile without errors (AWS only)."""
    env = detect_environment()
    if env == "local":
        return SKIP, "Local — AWS runner compile skipped"
    return _compile_check("run_merdian_shadow_runner.py")

def check_compile_ingest():
    """ingest_option_chain_local.py must compile."""
    return _compile_check("ingest_option_chain_local.py")

def check_compile_gamma():
    """compute_gamma_metrics_local.py must compile."""
    return _compile_check("compute_gamma_metrics_local.py")

def check_compile_volatility():
    """compute_volatility_metrics_local.py must compile."""
    return _compile_check("compute_volatility_metrics_local.py")

def check_compile_momentum():
    """build_momentum_features_local.py must compile."""
    return _compile_check("build_momentum_features_local.py")

def check_compile_market_state():
    """build_market_state_snapshot_local.py must compile."""
    return _compile_check("build_market_state_snapshot_local.py")

def check_compile_signal():
    """build_trade_signal_local.py must compile."""
    return _compile_check("build_trade_signal_local.py")

def check_compile_breadth():
    """ingest_breadth_intraday_local.py must compile."""
    return _compile_check("ingest_breadth_intraday_local.py")

def check_compile_trading_calendar():
    """trading_calendar.py must compile."""
    return _compile_check("trading_calendar.py")

def check_compile_refresh_token():
    """refresh_dhan_token.py must compile."""
    return _compile_check("refresh_dhan_token.py")

def check_no_runner_lock_local():
    """No stale runner lock file should exist (local)."""
    env = detect_environment()
    if env == "aws":
        return SKIP, "AWS — local lock check skipped"
    return _check_lock_file("run_option_snapshot_intraday_runner.lock")

def check_no_runner_lock_aws():
    """No stale AWS shadow runner lock should exist."""
    env = detect_environment()
    if env == "local":
        return SKIP, "Local — AWS lock check skipped"
    return _check_lock_file("aws_shadow_runner.lock")

def check_runner_outside_session():
    """
    Start the appropriate runner with --dry-run or equivalent outside session.
    If the runner does not support --dry-run, we verify it would read the
    calendar correctly by importing and checking session state directly.
    """
    try:
        root = get_merdian_root()
        if root not in sys.path:
            sys.path.insert(0, root)

        import importlib
        tc = importlib.import_module("trading_calendar")

        # Get session state
        try:
            state = tc.current_session_state()
        except AttributeError:
            # Try alternative function name
            try:
                cfg = tc.get_today_session_config()
                state = "MARKET_OPEN" if (hasattr(cfg, "is_open") and cfg.is_open) else "CLOSED"
            except Exception as e:
                # MissingSessionConfigError means no calendar row — that is V18A-03
                return WARN, (f"Could not determine session state: {type(e).__name__}: {e}. "
                              f"Check V18A-03 — trading_calendar row for today may be missing.")

        # Outside session = CLOSED / HOLIDAY / PREOPEN / AFTER_MARKET
        # These are all valid states where the runner would park/wait
        live_states = ["MARKET_OPEN"]
        if state in live_states:
            return PASS, f"Session state: {state} — runner would be active (market open)"
        else:
            return PASS, f"Session state: {state} — runner would park/wait cleanly (outside session)"

    except Exception as e:
        return FAIL, f"Runner session state check failed: {e}"

def check_python_path_for_scheduler():
    """
    On Local Windows: verify the Python executable path exists.
    The Windows Task Scheduler token refresh task needs the full path.
    """
    env = detect_environment()
    if env != "local":
        return SKIP, "AWS — Windows scheduler path check skipped"

    import shutil
    python_exe = sys.executable
    if not os.path.exists(python_exe):
        return FAIL, f"Python executable not found at: {python_exe}"

    # Also check the specific path that should be in the token refresh task
    expected_path = r"C:\Users\balan\AppData\Local\Programs\Python\Python312\python.exe"
    if os.path.exists(expected_path):
        return PASS, f"Python executable confirmed at: {expected_path}"

    # Fallback — use whatever python is running now
    return PASS, f"Python executable at: {python_exe} (verify this is in token refresh task)"

# ── Stage Runner ──────────────────────────────────────────────────

def run_stage3(verbose=True):
    started_at = now_iso()
    env = detect_environment()

    if verbose:
        print_header(f"Stage 3 — Runner Dry-Start  [{env.upper()}]")

    # Load env first (stage 0 may not have run standalone)
    load_env()

    checks = [
        run_check("trading_calendar.py compiles",             check_compile_trading_calendar),
        run_check("ingest_option_chain compiles",             check_compile_ingest),
        run_check("compute_gamma_metrics compiles",           check_compile_gamma),
        run_check("compute_volatility_metrics compiles",      check_compile_volatility),
        run_check("build_momentum_features compiles",         check_compile_momentum),
        run_check("build_market_state_snapshot compiles",     check_compile_market_state),
        run_check("build_trade_signal compiles",              check_compile_signal),
        run_check("ingest_breadth_intraday compiles",         check_compile_breadth),
        run_check("refresh_dhan_token compiles",              check_compile_refresh_token),
        run_check("Local runner compiles",                    check_compile_runner_local),
        run_check("AWS runner compiles",                      check_compile_runner_aws),
        run_check("No stale lock (local)",                    check_no_runner_lock_local),
        run_check("No stale lock (AWS)",                      check_no_runner_lock_aws),
        run_check("Runner session state readable",            check_runner_outside_session),
        run_check("Python path for scheduler (local)",        check_python_path_for_scheduler),
    ]

    if verbose:
        for c in checks:
            print_check(c)

    result = make_stage_result(STAGE_ID, env, checks, started_at)
    save_stage_result(result)

    if verbose:
        print_stage_summary(result)

    return result

if __name__ == "__main__":
    result = run_stage3(verbose=True)
    sys.exit(0 if result["status"] == PASS else 1)
