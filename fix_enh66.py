"""
ENH-66: Holiday-gate root cause fix.

Today (2026-04-20) MERDIAN was silently blocked for 3 hours because 7
production scripts treated `open_time IS NULL` as a market holiday.

The trading_calendar row for today had:
  is_open=True, open_time=NULL, close_time=NULL, holiday_name=NULL

That's a valid but incomplete row. Gate-reading scripts interpreted
open_time=NULL as "market closed" and exited silently.

Root cause: merdian_start.py ensure_calendar_row() inserts trading days
with only {trade_date, is_open=True}. Never populates open_time /
close_time for regular sessions.

Fix: populate open_time='09:15:00' and close_time='15:30:00' for every
regular trading day row, in two places:
  1. INSERT path when creating a new row for a weekday.
  2. TRADING DAY branch when row already exists but columns are NULL --
     PATCH to backfill the missing times (covers today's exact state for
     any future reruns).

Single authoritative source. 7 downstream scripts unchanged (they keep
their gate logic; data becomes consistent).

Target: merdian_start.py
Validation: ast.parse() on patched file.
"""
from __future__ import annotations

import argparse
import ast
import shutil
import sys
from pathlib import Path


TARGET_DEFAULT = r"C:\GammaEnginePython\merdian_start.py"


# ---------------------------------------------------------------------------
# Edit 1: Upgrade the "row exists and is_open=True" branch so it backfills
# open_time/close_time if they are NULL. Idempotent: if the times are
# already set correctly, it's a no-op.
# ---------------------------------------------------------------------------

EDIT1_OLD = '''                else:
                    # Row exists and is_open=True - already correct
                    return True, f"{today} -> TRADING DAY -- row exists, no change"'''

EDIT1_NEW = '''                else:
                    # Row exists and is_open=True. Ensure open_time/close_time
                    # are populated -- ENH-66: gate-reading scripts treat
                    # open_time=NULL as "market closed" and exit silently.
                    needs_patch = (
                        row.get("open_time") is None
                        or row.get("close_time") is None
                    )
                    if needs_patch:
                        pr = requests.patch(
                            f"{SUPABASE_URL}/rest/v1/trading_calendar",
                            headers=headers,
                            params={"trade_date": f"eq.{today}"},
                            json={
                                "open_time": "09:15:00",
                                "close_time": "15:30:00",
                            },
                            timeout=10,
                        )
                        if pr.status_code < 300:
                            return True, f"{today} -> TRADING DAY -- open_time/close_time backfilled (ENH-66)"
                        return False, f"ENH-66 backfill failed: Supabase {pr.status_code}: {pr.text[:80]}"
                    return True, f"{today} -> TRADING DAY -- row exists, no change"'''


# ---------------------------------------------------------------------------
# Edit 2: Include open_time/close_time in the INSERT payload when creating
# a fresh row for a weekday. Only populate for is_open=True (weekends stay
# as {trade_date, is_open=False} -- gate scripts correctly skip them).
# ---------------------------------------------------------------------------

EDIT2_OLD = '''        # Step 2: No row exists - insert using weekday rule
        is_open = today.weekday() < 5   # Mon-Fri open, Sat-Sun closed
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/trading_calendar",
            headers={**headers, "Prefer": "resolution=merge-duplicates"},
            params={"on_conflict": "trade_date"},
            json=[{"trade_date": str(today), "is_open": is_open}],
            timeout=10,
        )'''

EDIT2_NEW = '''        # Step 2: No row exists - insert using weekday rule.
        # ENH-66: populate open_time/close_time for trading days. Gate-reading
        # scripts (capture_spot_1m, ingest_breadth_intraday, compute_iv_context,
        # etc) treat open_time=NULL as "market closed" and exit silently.
        is_open = today.weekday() < 5   # Mon-Fri open, Sat-Sun closed
        payload = {"trade_date": str(today), "is_open": is_open}
        if is_open:
            payload["open_time"] = "09:15:00"
            payload["close_time"] = "15:30:00"
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/trading_calendar",
            headers={**headers, "Prefer": "resolution=merge-duplicates"},
            params={"on_conflict": "trade_date"},
            json=[payload],
            timeout=10,
        )'''


def apply_patch(text: str) -> str:
    # Idempotence guards
    if "ENH-66" in text:
        raise RuntimeError("ENH-66 marker already present in file. Refusing to re-patch.")

    # Edit 1
    c1 = text.count(EDIT1_OLD)
    if c1 != 1:
        raise RuntimeError(f"Edit 1 anchor matched {c1} times (need exactly 1).")
    text = text.replace(EDIT1_OLD, EDIT1_NEW, 1)

    # Edit 2
    c2 = text.count(EDIT2_OLD)
    if c2 != 1:
        raise RuntimeError(f"Edit 2 anchor matched {c2} times (need exactly 1).")
    text = text.replace(EDIT2_OLD, EDIT2_NEW, 1)

    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=TARGET_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    # Self-syntax check
    try:
        ast.parse(Path(__file__).read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"FAIL: self-syntax: {e}", file=sys.stderr)
        return 1

    target = Path(args.target)
    if not target.exists():
        print(f"FAIL: target not found: {target.resolve()}", file=sys.stderr)
        return 2

    # Read as utf-8-sig to strip a leading BOM if present. Write back as
    # plain utf-8 (no BOM). This keeps Python AST-clean on Windows files
    # authored by editors that insert BOM.
    original = target.read_text(encoding="utf-8-sig")
    had_bom = target.read_bytes().startswith(b"\xef\xbb\xbf")

    try:
        patched = apply_patch(original)
    except RuntimeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 3

    # Syntax check on patched content before writing
    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"FAIL: patched file does not parse: {e}", file=sys.stderr)
        return 4

    # Structural sanity
    enh66_count = patched.count("ENH-66")
    if enh66_count < 3:
        print(f"FAIL: expected >=3 ENH-66 markers in patched file, found {enh66_count}", file=sys.stderr)
        return 5

    orig_lines = original.count("\n")
    new_lines = patched.count("\n")

    print(f"target:   {target.resolve()}")
    print(f"mode:     {'DRY RUN' if args.dry_run else 'APPLY'}")
    print(f"backup:   {'off' if args.no_backup else 'on'}")
    print(f"BOM:      {'present -> will strip' if had_bom else 'none'}")
    print(f"size:     {len(original)} -> {len(patched)} bytes ({len(patched)-len(original):+d})")
    print(f"lines:    {orig_lines} -> {new_lines} ({new_lines-orig_lines:+d})")
    print()
    print("Edits:")
    print("  [ENH-66/1] Row-exists branch: PATCH open_time/close_time if NULL")
    print("  [ENH-66/2] Insert branch: include open_time/close_time for weekdays")

    if args.dry_run:
        print()
        print("DRY RUN - nothing written.")
        return 0

    if not args.no_backup:
        backup = target.with_suffix(target.suffix + ".pre_enh66.bak")
        shutil.copy2(target, backup)
        print(f"backup:   {backup.name}")

    target.write_text(patched, encoding="utf-8")
    print()
    print("APPLIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
