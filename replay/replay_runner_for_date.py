"""
replay.replay_runner_for_date — ENH-93 orchestrator.

Phase 4 of ENH-93. Drives the entire 7-script replay pipeline for one date 
across all 5-min boundaries (09:15-15:30 IST).

Usage:
    python -m replay.replay_runner_for_date YYYY-MM-DD

Steps:
  1. Acquire file-based lock at replay/runtime/replay.lock
  2. Out-of-hours guard via replay_clock.assert_outside_market_hours()
  3. TRUNCATE 9 _replay tables (excluding script_execution_log_replay audit)
  4. Reconstruct chain + spot for replay_date (replay_chain_reconstructor)
  5. For each of ~75 boundaries:
       For each symbol (NIFTY, SENSEX):
         Run scripts in V19 §5.2 order (adjusted for replay):
           gamma -> volatility -> momentum -> market_state -> ICT 
           -> options_flow -> signal
  6. Release lock
  7. Print summary

CRITICAL CONTRACT: Scripts run in order PER BOUNDARY, NOT script-by-script 
across all boundaries. This matches live's incremental cycle behavior and 
ensures each downstream script sees the upstream output it expects.

Subprocess invocation isolates failures: one boundary's script crash does 
NOT halt the orchestrator. Full-day picture captured in summary.

Author: Session 24 (2026-05-09)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
import requests

from replay.replay_clock import IST, UTC, assert_outside_market_hours, to_iso_utc
from replay.replay_chain_reconstructor import reconstruct as reconstruct_chain


REPLAY_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = REPLAY_DIR / "runtime"
LOCK_FILE = RUNTIME_DIR / "replay.lock"

REPLAY_TABLES_TO_TRUNCATE = [
    "market_spot_snapshots_replay",
    "option_chain_snapshots_replay",
    "gamma_metrics_replay",
    "volatility_snapshots_replay",
    "momentum_snapshots_replay",
    "market_state_snapshots_replay",
    "ict_zones_replay",
    "signal_snapshots_replay",
    "options_flow_snapshots_replay",
    # script_execution_log_replay deliberately NOT truncated (audit)
]

SYMBOLS = ["NIFTY", "SENSEX"]

# Pipeline order per boundary (replay-adjusted; see module docstring).
# Each entry: (script_module, needs_run_id)
PIPELINE_PER_SYMBOL: List[Tuple[str, bool]] = [
    ("replay.replay_compute_gamma_metrics", True),
    ("replay.replay_compute_volatility_metrics", True),
    ("replay.replay_build_momentum_features", False),
    ("replay.replay_build_market_state_snapshot", False),
    ("replay.replay_detect_ict_patterns_runner", False),
    ("replay.replay_compute_options_flow", True),
    ("replay.replay_build_trade_signal", False),
]


def _load_supabase_creds() -> Tuple[str, str]:
    load_dotenv()
    url = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing")
    return url, key


def _truncate_replay_tables() -> None:
    """TRUNCATE all 9 _replay tables via PostgREST DELETE.
    PostgREST has no TRUNCATE; we use DELETE with tautology filter."""
    url, key = _load_supabase_creds()
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    for table in REPLAY_TABLES_TO_TRUNCATE:
        # DELETE all rows. id column exists on all _replay tables (mirror of live).
        # Use PostgREST: DELETE /table?<filter> requires non-empty filter.
        # Trick: filter on id != impossible value.
        full_url = f"{url}/rest/v1/{table}?id=not.is.null"
        try:
            resp = requests.delete(full_url, headers=headers, timeout=60)
            if resp.status_code in (200, 204):
                print(f"  TRUNCATE {table}: ok")
            else:
                print(f"  TRUNCATE {table}: HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"  TRUNCATE {table}: error {e}")


def acquire_lock() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            content = LOCK_FILE.read_text().strip()
        except Exception:
            content = "(unreadable)"
        raise RuntimeError(
            f"Replay lock held at {LOCK_FILE}.\n"
            f"Lock contents: {content}\n"
            f"Another replay run may be in progress. If stale, delete the lock file."
        )
    LOCK_FILE.write_text(
        f"pid={os.getpid()}\nstarted_at={datetime.now(UTC).isoformat()}\n"
    )


def release_lock() -> None:
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception as e:
        print(f"  WARNING: could not release lock: {e}")


def generate_boundaries(replay_date: date) -> List[datetime]:
    """5-min boundaries from 09:15 to 15:30 IST inclusive, in UTC."""
    boundaries: List[datetime] = []
    current_ist = datetime.combine(replay_date, datetime.min.time().replace(hour=9, minute=15), tzinfo=IST)
    end_ist = datetime.combine(replay_date, datetime.min.time().replace(hour=15, minute=30), tzinfo=IST)
    while current_ist <= end_ist:
        boundaries.append(current_ist.astimezone(UTC))
        current_ist += timedelta(minutes=5)
    return boundaries


def run_script(
    module: str,
    replay_ts_iso: str,
    symbol: str,
    run_id: Optional[str] = None,
    timeout: int = 120,
) -> Tuple[bool, str, str]:
    """Run a replay script via subprocess. Returns (success, stdout, stderr)."""
    cmd = [sys.executable, "-m", module, "--replay-ts", replay_ts_iso, "--symbol", symbol]
    if run_id is not None:
        cmd.extend(["--run-id", run_id])
    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPLAY_DIR.parent),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return (result.returncode == 0, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (False, "", f"TIMEOUT after {timeout}s")
    except Exception as e:
        return (False, "", f"subprocess error: {e}")


def run_boundary_for_symbol(
    boundary_utc: datetime,
    symbol: str,
    run_id: Optional[str],
) -> Dict[str, bool]:
    """Run all 7 scripts for one (boundary, symbol). Returns per-script success dict."""
    replay_ts_iso = to_iso_utc(boundary_utc)
    results: Dict[str, bool] = {}

    for module, needs_run_id in PIPELINE_PER_SYMBOL:
        rid = run_id if needs_run_id else None
        if needs_run_id and rid is None:
            results[module] = False
            continue
        success, stdout, stderr = run_script(module, replay_ts_iso, symbol, run_id=rid)
        results[module] = success
        if not success:
            print(f"    [{symbol}] {module} FAIL")
            if stderr.strip():
                print(f"      stderr: {stderr.strip()[:300]}")

    return results


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="replay_runner_for_date")
    parser.add_argument("replay_date", help="YYYY-MM-DD")
    parser.add_argument("--skip-truncate", action="store_true",
                        help="Skip TRUNCATE step (use with caution; will fail on idempotency check)")
    parser.add_argument("--skip-reconstruct", action="store_true",
                        help="Skip reconstructor (chain + spot already populated)")
    parser.add_argument("--first-n-boundaries", type=int, default=None,
                        help="Run only first N boundaries (debugging; default = all)")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])

    try:
        replay_date = date.fromisoformat(args.replay_date)
    except ValueError as e:
        print(f"[ERROR] Invalid replay_date: {e}", file=sys.stderr)
        return 2

    if replay_date >= datetime.now(IST).date():
        print(f"[ERROR] replay_date {replay_date} must be in the past", file=sys.stderr)
        return 2

    print("=" * 72)
    print(f"REPLAY RUNNER — {replay_date}")
    print("=" * 72)

    # Out-of-hours guard
    try:
        assert_outside_market_hours()
        print("Market-hours guard: outside-hours OK")
    except RuntimeError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    # File lock
    try:
        acquire_lock()
        print(f"Lock acquired at {LOCK_FILE}")
    except RuntimeError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1

    try:
        # TRUNCATE
        if not args.skip_truncate:
            print("-" * 72)
            print("TRUNCATE _replay tables...")
            _truncate_replay_tables()

        # Reconstruct
        run_id_by_boundary: Dict[str, Dict[str, str]] = {}
        if not args.skip_reconstruct:
            print("-" * 72)
            print("Reconstructing chain + spot...")
            run_id_by_boundary = reconstruct_chain(replay_date)
        else:
            print("Skipping reconstruct (--skip-reconstruct)")
            # In skip mode, we'd need to query existing run_ids from the replay table.
            # Out of scope for first cut; user must not skip reconstruct on first run.

        # Boundary loop
        boundaries = generate_boundaries(replay_date)
        if args.first_n_boundaries is not None:
            boundaries = boundaries[:args.first_n_boundaries]
            print(f"DEBUG: limited to first {len(boundaries)} boundaries")

        print("-" * 72)
        print(f"Running pipeline across {len(boundaries)} boundaries x {len(SYMBOLS)} symbols")
        print(f"Pipeline per (boundary, symbol): {[m.split('.')[-1] for m, _ in PIPELINE_PER_SYMBOL]}")
        print("-" * 72)

        # Per-script success counters
        total_runs: Dict[str, int] = {m: 0 for m, _ in PIPELINE_PER_SYMBOL}
        total_succ: Dict[str, int] = {m: 0 for m, _ in PIPELINE_PER_SYMBOL}

        start_wall = time.time()
        for i, boundary in enumerate(boundaries, start=1):
            boundary_iso = boundary.isoformat()
            ist_str = boundary.astimezone(IST).strftime("%H:%M")

            symbol_runids = run_id_by_boundary.get(boundary_iso, {})

            results_per_symbol: Dict[str, Dict[str, bool]] = {}
            for symbol in SYMBOLS:
                run_id = symbol_runids.get(symbol)
                results = run_boundary_for_symbol(boundary, symbol, run_id)
                results_per_symbol[symbol] = results
                for m, ok in results.items():
                    total_runs[m] += 1
                    if ok:
                        total_succ[m] += 1

            nifty_ok = sum(1 for v in results_per_symbol.get("NIFTY", {}).values() if v)
            sensex_ok = sum(1 for v in results_per_symbol.get("SENSEX", {}).values() if v)
            print(f"[{ist_str} IST | {i:2}/{len(boundaries)}] "
                  f"NIFTY {nifty_ok}/{len(PIPELINE_PER_SYMBOL)} | "
                  f"SENSEX {sensex_ok}/{len(PIPELINE_PER_SYMBOL)}")

        elapsed = time.time() - start_wall
        print("-" * 72)
        print(f"Pipeline complete in {elapsed:.1f}s")
        print("Per-script success rates:")
        for module, _ in PIPELINE_PER_SYMBOL:
            short = module.split(".")[-1]
            r = total_runs[module]
            s = total_succ[module]
            pct = (s / r * 100) if r > 0 else 0
            print(f"  {short:50s}: {s:3}/{r:3} ({pct:.0f}%)")

        print("=" * 72)
        print("REPLAY RUNNER COMPLETE")
        print("=" * 72)
        return 0

    finally:
        release_lock()
        print(f"Lock released")


if __name__ == "__main__":
    sys.exit(main())