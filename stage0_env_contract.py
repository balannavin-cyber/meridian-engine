"""
MERDIAN Preflight — Stage 0: Environment Contract
==================================================
Checks that the environment can boot correctly before any API or DB call.

Catches:
  - Missing .env file or required keys
  - Wrong Python version
  - Import failures in critical modules
  - Function signature drift (runner expects a function that no longer exists)
  - Object/dict contract drift
  - Hardcoded Windows paths in files destined for AWS
  - Required files missing from disk

Pass criteria: ALL checks pass.
Any FAIL means the environment is not safe to proceed.
"""

import os
import sys
import importlib
import inspect

# Add MERDIAN root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from preflight_common import (
    PASS, FAIL, WARN, SKIP,
    detect_environment, get_merdian_root, get_env_file_path,
    load_env, make_stage_result, run_check, now_iso, print_header,
    print_check, print_stage_summary, save_stage_result
)

STAGE_ID = "stage0_env_contract"

# ── Check Definitions ─────────────────────────────────────────────

def check_python_version():
    """Python 3.8+ required."""
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 8):
        return FAIL, f"Python {major}.{minor} — need 3.8+"
    return PASS, f"Python {major}.{minor}"

def check_env_file_exists():
    """Verify .env file exists at expected path."""
    path = get_env_file_path()
    if not os.path.exists(path):
        return FAIL, f"Not found: {path}"
    return PASS, path

def check_env_required_keys():
    """Verify all required environment variables are present and non-empty."""
    ok, msg, missing = load_env()
    if not ok:
        return FAIL, msg
    if missing:
        return FAIL, f"Missing keys: {missing}"
    # Spot-check values are not placeholders
    token = os.environ.get("DHAN_API_TOKEN", "")
    if len(token) < 10:
        return FAIL, "DHAN_API_TOKEN looks too short — may be stale or placeholder"
    return PASS, "All required keys present and non-empty"

def check_merdian_root_exists():
    """MERDIAN root directory must exist."""
    root = get_merdian_root()
    if not os.path.isdir(root):
        return FAIL, f"MERDIAN root not found: {root}"
    return PASS, root

def _check_file_exists(filename):
    """Check a specific file exists in MERDIAN root."""
    root = get_merdian_root()
    path = os.path.join(root, filename)
    if not os.path.exists(path):
        return FAIL, f"Missing: {path}"
    return PASS, f"Found: {filename}"

def check_critical_files():
    """All critical scripts must be present on disk."""
    critical = [
        "trading_calendar.py",
        "ingest_option_chain_local.py",
        "compute_gamma_metrics_local.py",
        "compute_volatility_metrics_local.py",
        "build_momentum_features_local.py",
        "build_market_state_snapshot_local.py",
        "build_trade_signal_local.py",
        "ingest_breadth_intraday_local.py",
        "build_wcb_snapshot_local.py",
        "refresh_dhan_token.py",
    ]
    missing = []
    root = get_merdian_root()
    for f in critical:
        if not os.path.exists(os.path.join(root, f)):
            missing.append(f)
    if missing:
        return FAIL, f"Missing critical files: {missing}"
    return PASS, f"All {len(critical)} critical files present"

def check_aws_runner_file():
    """AWS-specific: run_merdian_shadow_runner.py must exist on AWS."""
    env = detect_environment()
    if env != "aws":
        return SKIP, "Local environment — AWS runner check skipped"
    root = get_merdian_root()
    path = os.path.join(root, "run_merdian_shadow_runner.py")
    if not os.path.exists(path):
        return FAIL, f"Missing: {path}"
    return PASS, "run_merdian_shadow_runner.py present"

def check_trading_calendar_import():
    """trading_calendar.py must import without error."""
    try:
        root = get_merdian_root()
        if root not in sys.path:
            sys.path.insert(0, root)
        import importlib
        tc = importlib.import_module("trading_calendar")
        return PASS, "trading_calendar imported successfully"
    except ImportError as e:
        return FAIL, f"ImportError: {e}"
    except Exception as e:
        return FAIL, f"Exception on import: {e}"

def check_trading_calendar_functions():
    """
    trading_calendar must expose get_today_session_config() and
    current_session_state() — the functions the runner calls.
    """
    try:
        root = get_merdian_root()
        if root not in sys.path:
            sys.path.insert(0, root)
        tc = importlib.import_module("trading_calendar")
        required_fns = ["get_today_session_config", "current_session_state"]
        missing = [fn for fn in required_fns if not hasattr(tc, fn)]
        if missing:
            return FAIL, f"Missing functions: {missing}"
        return PASS, f"All required functions present: {required_fns}"
    except Exception as e:
        return FAIL, f"Exception: {e}"

def check_session_config_object_contract():
    """
    get_today_session_config() must return an object with is_open attribute.
    Catches the object-vs-dict contract drift that broke sessions in V17.
    NOTE: this may raise MissingSessionConfigError if no calendar row exists
    for today — that is caught and reported as WARN not FAIL (it is a data
    issue, not a code issue).
    """
    try:
        root = get_merdian_root()
        if root not in sys.path:
            sys.path.insert(0, root)
        tc = importlib.import_module("trading_calendar")

        try:
            cfg = tc.get_today_session_config()
            # Must have is_open attribute
            if not hasattr(cfg, "is_open") and not isinstance(cfg, dict):
                return FAIL, f"Config object has no is_open attribute. Type: {type(cfg)}"
            # Handle both object and dict
            _ = cfg.is_open if hasattr(cfg, "is_open") else cfg["is_open"]
            return PASS, "Session config contract valid (is_open accessible)"
        except Exception as inner:
            name = type(inner).__name__
            if "MissingSessionConfig" in name or "CalendarError" in name:
                return WARN, f"{name} — no calendar row for today (data gap, not code failure)"
            return FAIL, f"get_today_session_config() raised: {inner}"

    except Exception as e:
        return FAIL, f"Exception: {e}"

def check_no_hardcoded_windows_paths_on_aws():
    """
    On AWS: scan critical scripts for hardcoded Windows paths.
    C:\\ in any script on AWS is a latent cross-platform bug.
    """
    env = detect_environment()
    if env != "aws":
        return SKIP, "Local environment — Windows path check only runs on AWS"

    root = get_merdian_root()
    scripts_to_check = [
        "trading_calendar.py",
        "run_merdian_shadow_runner.py",
        "ingest_breadth_intraday_local.py",
        "capture_market_spot_snapshot_local.py",
        "ingest_option_chain_local.py",
        "compute_gamma_metrics_local.py",
        "build_market_state_snapshot_local.py",
    ]
    violations = []
    for script in scripts_to_check:
        path = os.path.join(root, script)
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    # Exclude comment lines and docstrings
                    stripped = line.strip()
                    if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                        continue
                    if "C:\\" in line or "C:/" in line:
                        violations.append(f"{script}:{i}: {stripped[:80]}")
        except Exception:
            pass

    if violations:
        return FAIL, f"Hardcoded Windows paths found:\n" + "\n".join(violations[:5])
    return PASS, f"No hardcoded Windows paths found in {len(scripts_to_check)} checked scripts"

def check_git_hash_readable():
    """Git hash must be readable — confirms we are in a Git repo."""
    from preflight_common import get_git_hash
    h, err = get_git_hash()
    if h is None:
        return FAIL, f"Could not read Git hash: {err}"
    return PASS, f"Git hash: {h}"

# ── Stage Runner ──────────────────────────────────────────────────

def run_stage0(verbose=True):
    started_at = now_iso()
    env = detect_environment()

    if verbose:
        print_header(f"Stage 0 — Environment Contract  [{env.upper()}]")

    checks = [
        run_check("Python version >= 3.8",          check_python_version),
        run_check(".env file exists",                check_env_file_exists),
        run_check(".env required keys present",      check_env_required_keys),
        run_check("MERDIAN root directory exists",   check_merdian_root_exists),
        run_check("Critical files on disk",          check_critical_files),
        run_check("AWS runner file present",         check_aws_runner_file),
        run_check("trading_calendar imports",        check_trading_calendar_import),
        run_check("trading_calendar functions",      check_trading_calendar_functions),
        run_check("Session config object contract",  check_session_config_object_contract),
        run_check("No hardcoded Windows paths (AWS)",check_no_hardcoded_windows_paths_on_aws),
        run_check("Git hash readable",               check_git_hash_readable),
    ]

    if verbose:
        for c in checks:
            print_check(c)

    result = make_stage_result(STAGE_ID, env, checks, started_at)
    save_stage_result(result)

    if verbose:
        print_stage_summary(result)

    return result

# ── Standalone Run ────────────────────────────────────────────────

if __name__ == "__main__":
    result = run_stage0(verbose=True)
    sys.exit(0 if result["status"] == PASS else 1)
