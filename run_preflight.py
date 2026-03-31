"""
MERDIAN Preflight Harness — Master Orchestrator
================================================
Runs all preflight stages in order and produces a single PASS/FAIL report.
Sends Telegram alert with result.

Usage:
  python run_preflight.py                      # default: preopen mode (stages 0-3)
  python run_preflight.py --mode preopen       # stages 0-3 (no live market needed)
  python run_preflight.py --mode auth_only     # stage 1 only
  python run_preflight.py --mode db_only       # stage 2 only
  python run_preflight.py --mode full          # all stages (live market required for stage 5)

Output:
  preflight/output/latest_preflight_report.json
  preflight/output/latest_preflight_summary.txt
  preflight/output/preflight_history.jsonl
  Telegram alert (if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set)

Exit codes:
  0 = PASS (live canary allowed)
  1 = FAIL (do not proceed to live session)
"""

import os
import sys
import argparse
import json
import time

# Add MERDIAN root to path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from preflight_common import (
    PASS, FAIL, WARN, SKIP,
    detect_environment, get_merdian_root,
    load_env, now_iso, now_ist_str,
    get_git_hash, save_final_report, build_summary_text,
    alert_preflight_result, print_header,
    make_stage_result
)

# ── Stage imports (lazy — only import what we need for the mode) ──

def _import_stages(mode):
    stages = {}
    if mode in ("preopen", "full", "auth_only"):
        from stage1_auth_smoke import run_stage1
        stages["stage1_auth_smoke"] = run_stage1
    if mode in ("preopen", "full", "db_only"):
        from stage2_db_contract import run_stage2
        stages["stage2_db_contract"] = run_stage2
    if mode in ("preopen", "full"):
        from stage0_env_contract import run_stage0
        from stage3_runner_drystart import run_stage3
        stages["stage0_env_contract"] = run_stage0
        stages["stage3_runner_drystart"] = run_stage3
    return stages

# Stage execution order per mode
STAGE_ORDER = {
    "preopen":   ["stage0_env_contract", "stage1_auth_smoke", "stage2_db_contract", "stage3_runner_drystart"],
    "auth_only": ["stage1_auth_smoke"],
    "db_only":   ["stage2_db_contract"],
    "full":      ["stage0_env_contract", "stage1_auth_smoke", "stage2_db_contract", "stage3_runner_drystart"],
}

# ── Main Orchestrator ─────────────────────────────────────────────

def run_preflight(mode="preopen", verbose=True, alert=True):
    started_at   = now_iso()
    started_ist  = now_ist_str()
    env          = detect_environment()
    git_hash, _  = get_git_hash()

    if verbose:
        print()
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║  MERDIAN PREFLIGHT HARNESS                                    ║")
        print(f"║  Environment: {env.upper():<10s}  Mode: {mode:<12s}              ║")
        print(f"║  {started_ist:<58s} ║")
        if git_hash:
            print(f"║  Git: {git_hash[:52]:<52s} ║")
        print("╚══════════════════════════════════════════════════════════════╝")

    # Load env for all stages
    load_env()

    # Import and run stages
    stages_to_run = STAGE_ORDER.get(mode, STAGE_ORDER["preopen"])
    stage_fns     = _import_stages(mode)

    stage_results = []
    overall_fail  = False

    for stage_id in stages_to_run:
        fn = stage_fns.get(stage_id)
        if fn is None:
            continue
        try:
            result = fn(verbose=verbose)
            stage_results.append(result)
            if result["status"] == FAIL:
                overall_fail = True
        except Exception as e:
            # Stage crashed entirely — treat as FAIL
            import traceback
            crash_result = {
                "stage": stage_id,
                "environment": env,
                "status": FAIL,
                "started_at": now_iso(),
                "finished_at": now_iso(),
                "summary": {"passed": 0, "failed": 1, "warned": 0, "skipped": 0, "total": 1},
                "checks": [{"name": "stage_execution", "status": FAIL,
                            "detail": f"Stage crashed: {e}\n{traceback.format_exc()}"}],
            }
            stage_results.append(crash_result)
            overall_fail = True

    overall_status    = FAIL if overall_fail else PASS
    live_canary_allowed = not overall_fail

    report = {
        "overall_status":       overall_status,
        "live_canary_allowed":  live_canary_allowed,
        "environment":          env,
        "mode":                 mode,
        "started_at":           started_at,
        "started_at_ist":       started_ist,
        "finished_at":          now_iso(),
        "git_hash":             git_hash,
        "stage_results":        stage_results,
    }

    # Save report
    report_path = save_final_report(report)

    # Print final summary
    if verbose:
        print()
        print("━" * 72)
        icon = "✅" if overall_status == PASS else "❌"
        canary_str = "🟢 LIVE CANARY ALLOWED" if live_canary_allowed else "⛔ LIVE CANARY BLOCKED"
        print(f"  {icon}  OVERALL: {overall_status}   {canary_str}")
        print()
        if not live_canary_allowed:
            print("  FAILED STAGES:")
            for sr in stage_results:
                if sr["status"] == FAIL:
                    print(f"    ❌ {sr['stage']}")
                    for c in sr["checks"]:
                        if c["status"] == FAIL:
                            print(f"         • {c['name']}: {c['detail']}")
        print(f"  Report: {report_path}")
        print("━" * 72)
        print()

    # Telegram alert
    if alert:
        alert_preflight_result(report)

    return report

# ── Entry Point ───────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MERDIAN Preflight Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  preopen    Run stages 0-3 (default). Use before market open.
  auth_only  Run stage 1 only (auth/API smoke).
  db_only    Run stage 2 only (database contract).
  full       Run all stages (stages 0-3 currently; stage 5 when implemented).

Examples:
  python run_preflight.py
  python run_preflight.py --mode auth_only
  python run_preflight.py --mode db_only
  python run_preflight.py --no-alert
        """
    )
    parser.add_argument(
        "--mode",
        choices=["preopen", "auth_only", "db_only", "full"],
        default="preopen",
        help="Which stages to run (default: preopen)"
    )
    parser.add_argument(
        "--no-alert",
        action="store_true",
        help="Suppress Telegram alert"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output (report saved but not printed)"
    )

    args = parser.parse_args()

    report = run_preflight(
        mode    = args.mode,
        verbose = not args.quiet,
        alert   = not args.no_alert,
    )

    sys.exit(0 if report["overall_status"] == PASS else 1)

if __name__ == "__main__":
    main()
