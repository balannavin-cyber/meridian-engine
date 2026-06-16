#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seed_trading_calendar.py  (S55, TD-S54-NEW-4)

Pre-populates the Supabase `trading_calendar` table for the next N calendar
days, so every trading morning the authoritative gate row already exists --
fully populated -- before the 03:45 UTC open. Ends the daily manual insert.

Source of truth: trading_calendar.py (the V18E rule engine). For each date we
call get_session_config_for_date(); only OPEN days get a row (weekends and NSE
holidays need none -- a missing row is correctly read as "closed", matching the
module doctrine). Every seeded row carries the full session schema the module
computes: open_time, close_time, final_eod_ltp_time, is_special_session,
holiday_name, notes.

Idempotent: upsert on trade_date (Prefer: resolution=merge-duplicates). Safe to
run daily; re-affirms existing rows and repairs any row with a NULL close_time
(e.g. the hand-inserted 2026-06-15 / 06-16 rows).

House convention: raw HTTP against /rest/v1 with SUPABASE_SERVICE_ROLE_KEY.

Usage:
  python3 seed_trading_calendar.py                 # seed next 14 days
  python3 seed_trading_calendar.py --days 30
  python3 seed_trading_calendar.py --dry-run       # print plan, write nothing
"""

from __future__ import annotations

import os
import sys
import json
from datetime import timedelta

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from trading_calendar import now_ist, get_session_config_for_date

TABLE = "trading_calendar"
DEFAULT_DAYS = 14


def _env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        print(f"[ERROR] missing env var {name}", file=sys.stderr)
        sys.exit(2)
    return val


def _arg_int(flag: str, default: int) -> int:
    if flag in sys.argv:
        i = sys.argv.index(flag)
        if i + 1 < len(sys.argv):
            try:
                return int(sys.argv[i + 1])
            except ValueError:
                print(f"[ERROR] {flag} needs an integer", file=sys.stderr)
                sys.exit(2)
    return default


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    days = _arg_int("--days", DEFAULT_DAYS)

    supabase_url = _env("SUPABASE_URL").rstrip("/")
    service_key = _env("SUPABASE_SERVICE_ROLE_KEY")

    today = now_ist().date()
    rows = []
    skipped = []
    for offset in range(days):
        d = today + timedelta(days=offset)
        date_str = d.strftime("%Y-%m-%d")
        cfg = get_session_config_for_date(date_str)
        if not cfg.is_open:
            skipped.append((date_str, cfg.notes))
            continue
        rows.append({
            "trade_date": date_str,
            "is_open": True,
            "is_special_session": cfg.special_session,
            "open_time": cfg.open_time.strftime("%H:%M:%S"),
            "close_time": cfg.close_time.strftime("%H:%M:%S"),
            "final_eod_ltp_time": cfg.final_eod_ltp_time.strftime("%H:%M:%S"),
            "holiday_name": None,
            "notes": cfg.notes,
        })

    print(f"[PLAN] window: {today} .. {today + timedelta(days=days - 1)} ({days} days)")
    print(f"[PLAN] {len(rows)} open day(s) to upsert; {len(skipped)} closed day(s) skipped")
    for date_str, note in skipped:
        print(f"        skip {date_str}  ({note})")
    for r in rows:
        print(f"        seed {r['trade_date']}  open={r['open_time']} close={r['close_time']}"
              f" eod={r['final_eod_ltp_time']} special={r['is_special_session']} | {r['notes']}")

    if dry_run:
        print("[DRY-RUN] no writes performed.")
        return 0

    if not rows:
        print("[OK] nothing to seed (all days in window are closed).")
        return 0

    url = f"{supabase_url}/rest/v1/{TABLE}?on_conflict=trade_date"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=representation",
    }
    resp = requests.post(url, headers=headers, data=json.dumps(rows), timeout=30)
    if resp.status_code not in (200, 201):
        print(f"[ERROR] upsert failed: HTTP {resp.status_code} | {resp.text[:500]}",
              file=sys.stderr)
        return 1

    written = resp.json() if resp.text else []
    print(f"[OK] upserted {len(written) if isinstance(written, list) else len(rows)} row(s) "
          f"into {TABLE}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
