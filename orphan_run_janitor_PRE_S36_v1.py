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

Empirical baseline S36: 2 orphans in 8 weeks (2026-05-04, 2026-05-22).
Daily warn threshold (deferred to merdian_daily_audit.py): 1 per day.

Filed under TD-080 closure path. See ENH-99.

House conventions matched (per ingest_option_chain_local.py):
  - dotenv load
  - os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
  - raw HTTP via requests against /rest/v1/* (no supabase-py)
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
        "Prefer": "return=representation",
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
    r.raise_for_status()
    return r.json() or []


def close_orphan(row):
    """Close a single orphan row. Returns merged payload."""
    started_at = datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    age_min = int((now - started_at).total_seconds() / 60)
    age_ms = int((now - started_at).total_seconds() * 1000)
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
    r.raise_for_status()
    return {**row, **payload}


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
        print("[orphan_run_janitor] missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in env", file=sys.stderr)
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

    for r in orphans:
        closed = close_orphan(r)
        print(f"  CLOSED id={closed['id']} notes={closed['notes']}")

    print(f"[orphan_run_janitor] closed {len(orphans)} orphan(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
