#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_s55_preflight_open_time.py  (Patch Script Canon v3)

TD-S54-NEW-4 (preflight half): V18A-03 (check_trading_calendar_today in
stage2_db_contract.py) passes the moment a trading_calendar row EXISTS, even if
open_time IS NULL -- but the capture gate requires open_time IS NOT NULL. So a
partial row (the hand-inserted kind) shows preflight GREEN while capture still
skips the day. This aligns the gate: PASS only when the row exists, is_open is
true, and open_time is populated; otherwise FAIL pointing at the seeder.

Replaces the body of check_trading_calendar_today() by anchored full-function
substring swap (the old body is unique in the file). ast.parse validated,
_PRE_S55 backup, dry-run default + --apply, idempotent (skips if already patched).

Usage:
  python3 patch_s55_preflight_open_time.py
  python3 patch_s55_preflight_open_time.py --apply
  python3 patch_s55_preflight_open_time.py --apply --file <path>
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

DEFAULT_FILE = "stage2_db_contract.py"
BACKUP_SUFFIX = "_PRE_S55.py"

OLD = '''def check_trading_calendar_today():
    today = datetime.date.today().isoformat()
    rows, err = _sb_table_get("trading_calendar", f"trade_date=eq.{today}&select=trade_date,is_open")
    if err:
        return FAIL, f"Could not query trading_calendar: {err}"
    if not rows:
        return FAIL, (f"V18A-03: No trading_calendar row for today ({today}). "
                      f"ALL calendar-gated scripts will treat today as a holiday and skip. "
                      f"INSERT a row immediately: INSERT INTO trading_calendar (trade_date, is_open) "
                      f"VALUES ('{today}', true/false);")
    row = rows[0]
    is_open = row.get("is_open")
    return PASS, f"trading_calendar row exists for {today}. is_open={is_open}"'''

NEW = '''def check_trading_calendar_today():
    today = datetime.date.today().isoformat()
    rows, err = _sb_table_get("trading_calendar", f"trade_date=eq.{today}&select=trade_date,is_open,open_time")
    if err:
        return FAIL, f"Could not query trading_calendar: {err}"
    if not rows:
        return FAIL, (f"V18A-03: No trading_calendar row for today ({today}). "
                      f"ALL calendar-gated scripts will treat today as a holiday and skip. "
                      f"Run the seeder: python3 seed_trading_calendar.py")
    row = rows[0]
    is_open = row.get("is_open")
    open_time = row.get("open_time")
    # Align with the capture gate: a row that exists but lacks open_time is a
    # false-green -- preflight would pass while capture still skips the day.
    if is_open and not open_time:
        return FAIL, (f"V18A-03: trading_calendar row for {today} has open_time NULL. "
                      f"The capture gate requires open_time IS NOT NULL, so capture will skip. "
                      f"Run the seeder: python3 seed_trading_calendar.py")
    return PASS, f"trading_calendar row exists for {today}. is_open={is_open}, open_time={open_time}"'''


def detect_eol(text: str) -> str:
    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    return "\r\n" if crlf >= lf and crlf > 0 else "\n"


def main() -> int:
    apply = "--apply" in sys.argv
    path_str = DEFAULT_FILE
    if "--file" in sys.argv:
        i = sys.argv.index("--file")
        if i + 1 >= len(sys.argv):
            print("ERROR: --file requires a path argument", file=sys.stderr)
            return 2
        path_str = sys.argv[i + 1]

    path = Path(path_str)
    if not path.is_file():
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        return 2

    raw = path.read_bytes()
    had_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    eol = detect_eol(text)
    norm = text.replace("\r\n", "\n")

    if "open_time IS NOT NULL" in norm or "open_time NULL" in norm or "seed_trading_calendar.py" in norm:
        print("Already patched (open_time gate present) -- no-op. Exiting 0.")
        return 0

    if OLD not in norm:
        print("ERROR: target function body not found verbatim. File may have changed; aborting.",
              file=sys.stderr)
        return 1

    new_norm = norm.replace(OLD, NEW, 1)

    try:
        ast.parse(new_norm)
    except SyntaxError as e:
        print(f"ERROR: patched source fails ast.parse: {e}", file=sys.stderr)
        return 1

    print(f"File:    {path}")
    print(f"EOL:     {'CRLF' if eol == chr(13)+chr(10) else 'LF'}"
          f"{'  (+BOM)' if had_bom else ''}")
    print("Change:  check_trading_calendar_today() -> requires open_time when is_open")
    print("-" * 60)
    print("  select adds open_time; PASS gated on open_time present; FAIL points at seeder")
    print("-" * 60)

    if not apply:
        print("DRY-RUN. Re-run with --apply to write the backup and patch.")
        return 0

    backup = path.with_name(path.stem + BACKUP_SUFFIX)
    backup.write_bytes(raw)
    print(f"Backup:  {backup}")

    out = (eol.join(new_norm.split("\n"))).encode("utf-8")
    if had_bom:
        out = b"\xef\xbb\xbf" + out
    path.write_bytes(out)
    print(f"WROTE:   {path} ({len(out)} bytes)")
    print("APPLIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
