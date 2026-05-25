"""
orphan_run_janitor.py -- close stale RUNNING rows in script_execution_log

ENH-99 (S36) -- Component 2 of capture-layer resilience.

Scans script_execution_log for rows with:
  - exit_reason='RUNNING'
  - started_at older than --threshold-minutes (default 5)

Closes them with:
  - exit_reason='DATA_ERROR' (existing chk_exit_reason_valid CHECK valid value;
    'ORPHANED' is NOT in the constraint -- see patch_s36_enh99 header)
  - exit_code=137 (SIGKILL convention)
  - finished_at=now()
  - duration_ms=age_in_ms
  - notes='ORPHAN_RECOVERED: age_min=<N>'  <- daily audit greps this prefix

Cadence: run at intraday session start (~09:14 IST, before first ingest cycle)
via Task Scheduler. Manual invocation idempotent.

Empirical baseline S36 first run: 25 stale RUNNING rows accumulated since
2026-04-24 (mostly capture_spot_1m_v2.py and detect_ict_patterns_runner.py).
Daily warn threshold (deferred to merdian_daily_audit.py): 1 per day.

Filed under TD-080 closure path. See ENH-99.

v3 changes (S36 fix after first-run 400 on PATCH):
  - Removed 'Prefer: return=representation' header (was causing PostgREST 400
    on first run; not needed since we don't use returned body)
  - Per-row error tolerance: log failures, continue batch, summary at end
  - Print response body on HTTP errors for diagnosis
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import requests

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

DEFAULT_THRESHOLD_MINUTES = 5


def _headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def find_orphans(script_filter, threshold_minutes):
    """Return list of stale RUNNING rows older than threshold_minutes."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
    params = {
        "select": "id,script_name,started_at,host,symbol,trade_date",
        "exit_reason": "eq.RUNNING",
        "started_at": f"lt.{cutoff.isoformat()}",
    }
    if script_filter:
        params["script_name"] = f"eq.{script_filter}"
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/script_execution_log",
        headers=_headers(),
        params=params,
        timeout=30,
    )
    if not r.ok:
        print(f"[orphan_run_janitor] find_orphans HTTP {r.status_code}: {r.text}",
              file=sys.stderr)
        r.raise_for_status()
    return r.json() or []


def close_orphan(row):
    """Close a single orphan row. Returns dict with status + payload."""
    started_at = datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    age_min = int((now - started_at).total_seconds() / 60)
    age_ms = min(int((now - started_at).total_seconds() * 1000), 2_147_483_647)  # clamp to int32 max
    notes = f"ORPHAN_RECOVERED: age_min={age_min}"
    payload = {
        "exit_reason": "DATA_ERROR",
        "exit_code": 137,
        "finished_at": now.isoformat(),
        "duration_ms": age_ms,
        "notes": notes,
    }
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/script_execution_log",
        headers=_headers(),
        params={"id": f"eq.{row['id']}"},
        json=payload,
        timeout=30,
    )
    return {
        "id": row["id"],
        "script_name": row["script_name"],
        "ok": r.ok,
        "status_code": r.status_code,
        "body": r.text if not r.ok else None,
        "notes": notes,
    }


def main():
    ap = argparse.ArgumentParser(description="ORPHAN RUNNING janitor (ENH-99)")
    ap.add_argument("--script", default=None,
                    help="filter to specific script_name (default: all)")
    ap.add_argument("--threshold-minutes", type=int, default=DEFAULT_THRESHOLD_MINUTES,
                    help=f"min age to close (default: {DEFAULT_THRESHOLD_MINUTES})")
    ap.add_argument("--dry-run", action="store_true",
                    help="report only; do not UPDATE")
    args = ap.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("[orphan_run_janitor] missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY",
              file=sys.stderr)
        return 2

    orphans = find_orphans(args.script, args.threshold_minutes)

    print(f"[orphan_run_janitor] found {len(orphans)} stale RUNNING row(s) "
          f"older than {args.threshold_minutes}min")

    if not orphans:
        return 0

    for r in orphans:
        print(f"  - id={r['id']} script={r['script_name']} "
              f"started_at={r['started_at']} symbol={r.get('symbol')} "
              f"trade_date={r.get('trade_date')}")

    if args.dry_run:
        print("[orphan_run_janitor] DRY-RUN -- no rows updated")
        return 0

    closed_count = 0
    failed_count = 0
    failures = []
    for r in orphans:
        result = close_orphan(r)
        if result["ok"]:
            closed_count += 1
            print(f"  CLOSED id={result['id']} notes={result['notes']}")
        else:
            failed_count += 1
            failures.append(result)
            print(f"  FAILED id={result['id']} script={result['script_name']} "
                  f"status={result['status_code']} body={result['body']}",
                  file=sys.stderr)

    print(f"\n[orphan_run_janitor] closed {closed_count} / "
          f"failed {failed_count} / total {len(orphans)}")

    if failures:
        print("[orphan_run_janitor] first failure body for triage:", file=sys.stderr)
        print(f"  {failures[0]}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
