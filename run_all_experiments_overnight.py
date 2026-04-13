#!/usr/bin/env python3
"""
run_all_experiments_overnight.py
Runs all MERDIAN experiments on the full Apr 2025 - Mar 2026 dataset.

All scripts patched with merdian_utils.py (ENH-31 expiry fix).
Experiments 14 and 14b excluded — already run with full dataset.

Each experiment's stdout saved to:
  logs/exp_runs/YYYY-MM-DD/<script_name>.log

Usage:
    python run_all_experiments_overnight.py
    python run_all_experiments_overnight.py --dry-run
"""

import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR  = BASE_DIR / "logs" / "exp_runs" / datetime.now().strftime("%Y-%m-%d")
LOG_DIR.mkdir(parents=True, exist_ok=True)

EXPERIMENTS = [
    {
        "script":  "run_validation_analysis.py",
        "desc":    "ENH-35 -- Signal validation (baseline confirm)",
        "est_min": 5,
    },
    {
        "script":  "experiment_2_options_pnl.py",
        "desc":    "Exp 2 -- Options P&L by pattern (BULL_OB, BEAR_OB, FVG, Judas)",
        "est_min": 30,
    },
    {
        "script":  "experiment_2b_futures_vs_options.py",
        "desc":    "Exp 2b -- Futures vs options comparison",
        "est_min": 25,
    },
    {
        "script":  "experiment_2c_pyramid_entry.py",
        "desc":    "Exp 2c v1 -- Pyramid entry (T2 confirmation)",
        "est_min": 40,
    },
    {
        "script":  "experiment_2c_v2_judas.py",
        "desc":    "Exp 2c v2 -- Judas Bull pyramid variant",
        "est_min": 35,
    },
    {
        "script":  "experiment_5_vix_stress.py",
        "desc":    "Exp 5 -- VIX/IV stress test (HIGH_IV edge confirmation)",
        "est_min": 45,
    },
    {
        "script":  "experiment_8_sequence.py",
        "desc":    "Exp 8 -- Pre-pattern sequence detection (MOM_YES, IMP_STR)",
        "est_min": 60,
    },
    {
        "script":  "experiment_10c_mtf_pnl.py",
        "desc":    "Exp 10c -- MTF confluence P&L (MEDIUM/HIGH context lift)",
        "est_min": 90,
    },
    {
        "script":  "portfolio_simulation.py",
        "desc":    "Portfolio simulation v1 (fixed + pyramid, INR 4L capital)",
        "est_min": 120,
    },
    {
        "script":  "experiment_15_pure_ict_compounding.py",
        "desc":    "Exp 15 -- Pure ICT compounding (W/D/H zones, no MERDIAN gates)",
        "est_min": 180,
    },
    {
        "script":  "portfolio_simulation_v2.py",
        "desc":    "Portfolio simulation v2 (dynamic exit, 5-min gap filter)",
        "est_min": 120,
    },
]

DRY_RUN = "--dry-run" in sys.argv

# UTF-8 environment for all subprocesses (fixes cp1252 UnicodeEncodeError)
CHILD_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run_experiment(exp, idx, total):
    script   = exp["script"]
    desc     = exp["desc"]
    est      = exp.get("est_min", "?")
    log_path = LOG_DIR / f"{script.replace('.py', '')}.log"

    log("")
    log("=" * 65)
    log(f"  [{idx}/{total}] {desc}")
    log(f"  Script:   {script}")
    log(f"  Est:      ~{est} min")
    log(f"  Log:      {log_path}")
    log("=" * 65)

    if DRY_RUN:
        log("  DRY RUN -- skipping")
        return {"script": script, "status": "dry_run", "elapsed_s": 0}

    start = time.time()
    cmd   = [sys.executable, str(BASE_DIR / script)]

    with open(log_path, "w", encoding="utf-8") as lf:
        lf.write(f"# {desc}\n")
        lf.write(f"# Started: {datetime.now().isoformat()}\n\n")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=CHILD_ENV,
            cwd=str(BASE_DIR),
        )

        for line in proc.stdout:
            print(f"    {line}", end="", flush=True)
            lf.write(line)

        proc.wait()

    elapsed = time.time() - start
    status  = "OK" if proc.returncode == 0 else f"ERROR (rc={proc.returncode})"
    log(f"  {status} -- {elapsed/60:.1f} min elapsed")

    return {
        "script":    script,
        "status":    status,
        "elapsed_s": elapsed,
        "log":       str(log_path),
        "rc":        proc.returncode,
    }


def main():
    total     = len(EXPERIMENTS)
    total_est = sum(e.get("est_min", 0) for e in EXPERIMENTS)

    log("MERDIAN Overnight Experiment Runner")
    log(f"Experiments: {total}")
    log(f"Log dir:     {LOG_DIR}")
    log(f"Dry run:     {DRY_RUN}")
    log("")
    log("Experiment plan:")
    for i, exp in enumerate(EXPERIMENTS, 1):
        log(f"  {i:>2}. {exp['script']:<45} ~{exp.get('est_min','?')} min")
    log("")
    log(f"  Total estimated runtime: ~{total_est//60}h {total_est%60}m")
    log("")

    if not DRY_RUN:
        log("Starting in 5 seconds -- Ctrl+C to abort...")
        time.sleep(5)

    results       = []
    overall_start = time.time()

    for i, exp in enumerate(EXPERIMENTS, 1):
        result = run_experiment(exp, i, total)
        results.append(result)

    total_elapsed = time.time() - overall_start
    ok  = [r for r in results if r["status"] == "OK"]
    err = [r for r in results if r["status"] not in ("OK", "dry_run")]

    log("")
    log("=" * 65)
    log("  OVERNIGHT RUN COMPLETE")
    log(f"  Total time: {total_elapsed/3600:.1f}h")
    log(f"  OK:         {len(ok)}/{total}")
    log(f"  Errors:     {len(err)}/{total}")
    log("=" * 65)
    log("")

    log("Results:")
    for r in results:
        t = f"{r['elapsed_s']/60:.1f}m" if r["elapsed_s"] else "--"
        mark = "OK" if r["status"] == "OK" else "FAIL"
        log(f"  [{mark}] {r['script']:<45} {r['status']} ({t})")

    if err:
        log("")
        log("Failed:")
        for r in err:
            log(f"  {r['script']} -- see {r.get('log','?')}")

    log("")
    log(f"All logs saved to: {LOG_DIR}")


if __name__ == "__main__":
    main()
