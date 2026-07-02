"""ENH-115 P1 — NSE participant-OI backfill (>=1 year), seeds the ENH-116 cohort.

Walks the trading calendar over [--start, --end], fetching NSE participant-wise
OI per trading day via the proven single-day path (same fetch+parse+upsert as
ingest_participant_positioning.py). Idempotent (upsert on exchange,trade_date,
participant) and resumable (skips dates already present). One bad day is logged
and skipped, never aborts the run.

Usage:
    python backfill_participant_oi.py                         # ~13 months back to today
    python backfill_participant_oi.py --start 2025-06-01 --end 2026-06-30
    python backfill_participant_oi.py --dry-run               # plan only, no fetch/write
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

from datetime import date

from core.execution_log import ExecutionLog
from ingest_participant_positioning import _env, _fetch_nse_participant_csv, _upsert
from parse_participant_oi import parse_nse_participant_oi

IST = timezone(timedelta(hours=5, minutes=30))


def plan_dates(start_iso: str, end_iso: str, present: set[str]) -> list[str]:
    """Pure, testable: WEEKDAYS in [start,end] not already present, ascending.
    Holidays are not filtered here — NSE is ground truth: a weekday holiday 404s
    the archive and is recorded as a benign MISS. No trading-calendar dependency
    (that table's historical coverage isn't guaranteed; it fail-opens — Rule 18)."""
    d = date.fromisoformat(start_iso)
    end = date.fromisoformat(end_iso)
    out = []
    while d <= end:
        iso = d.isoformat()
        if d.weekday() < 5 and iso not in present:   # Mon-Fri only
            out.append(iso)
        d += timedelta(days=1)
    return out


def _present_dates(url: str, key: str, start_iso: str, end_iso: str) -> set[str]:
    """Dates already in participant_oi_daily (one row per date via participant=TOTAL,
    keeps the result under the PostgREST 1000-row cap)."""
    r = requests.get(
        f"{url}/rest/v1/participant_oi_daily",
        params=[("select", "trade_date"), ("exchange", "eq.NSE"),
                ("participant", "eq.TOTAL"),
                ("trade_date", f"gte.{start_iso}"), ("trade_date", f"lte.{end_iso}")],
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        timeout=60,
    )
    r.raise_for_status()
    return {row["trade_date"] for row in r.json()}


def main() -> int:
    today = datetime.now(IST).date()
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=(today - timedelta(days=400)).isoformat())
    ap.add_argument("--end", default=today.isoformat())
    ap.add_argument("--sleep", type=float, default=1.5, help="seconds between NSE fetches")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    url, key = _env()
    present = _present_dates(url, key, args.start, args.end)
    todo = plan_dates(args.start, args.end, present)

    print(f"[plan] {args.start}..{args.end}: {len(todo)} trading days to fetch "
          f"({len(present)} already present, skipped)")
    if args.dry_run:
        print("[DRY-RUN] no fetch/write. First/last to do:",
              (todo[0] if todo else None), (todo[-1] if todo else None))
        return 0

    log = ExecutionLog(
        script_name="backfill_participant_oi.py",
        expected_writes={"participant_oi_daily": len(todo) * 5},
        notes=f"start={args.start} end={args.end} todo={len(todo)}",
    )

    filled = 0
    missing: list[str] = []                         # no archive file -> weekday holiday
    failed: list[tuple[str, str]] = []              # real fetch/parse/upsert error
    for i, iso in enumerate(todo, 1):
        try:
            csv_text = _fetch_nse_participant_csv(iso)
            if csv_text is None:
                missing.append(iso)
                print(f"  [{i}/{len(todo)}] {iso}  MISS (no file - holiday)")
            else:
                _, rows = parse_nse_participant_oi(csv_text, exchange="NSE")
                n = _upsert(url, key, "participant_oi_daily", rows,
                            on_conflict="exchange,trade_date,participant")
                filled += 1
                print(f"  [{i}/{len(todo)}] {iso}  OK ({n} rows)")
        except Exception as e:                      # tolerate one bad day, keep going
            failed.append((iso, str(e)[:120]))
            print(f"  [{i}/{len(todo)}] {iso}  FAIL {str(e)[:120]}")
        time.sleep(args.sleep)

    log.record_write("participant_oi_daily", filled * 5)
    print(f"\n[done] filled={filled}  present_skipped={len(present)}  "
          f"missing_holidays={len(missing)}  failed={len(failed)}")
    if failed:
        print("[FAILED dates] (real errors; re-run retries, upsert makes it safe):")
        for iso, why in failed:
            print(f"    {iso}  {why}")
    if missing:
        print(f"[missing dates] (weekday holidays, expected): {', '.join(missing)}")
    return log.complete()


if __name__ == "__main__":
    sys.exit(main())
