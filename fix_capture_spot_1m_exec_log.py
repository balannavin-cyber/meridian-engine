"""
ENH-71 reference: integrate ExecutionLog into capture_spot_1m.py.

This is the FIRST production script to use the write-contract layer.
Pattern established here is copied by Session 3 into the other 9 critical
scripts. Intentionally opinionated so the pattern is unambiguous.

Changes:
  1. Import ExecutionLog at top of module.
  2. Instantiate at top of main() with expected_writes declaring both tables.
  3. Convert silent "Market holiday -- exiting cleanly" print into
     log.exit_with_reason('HOLIDAY_GATE'). This is the killer win: today's
     exact bug goes from silent to queryable.
  4. Convert [WARN] catches around sb_insert / sb_upsert to exit_with_reason
     with DATA_ERROR / TOKEN_EXPIRED taxonomy (best-effort auth detection).
  5. On success, call log.record_write() for each table then log.complete().
  6. Dhan fetch failures become TOKEN_EXPIRED (if auth-like) or DATA_ERROR.
  7. Env-var missing becomes DEPENDENCY_MISSING.

What's intentionally NOT changed:
  - The holiday-gate logic itself (ENH-66 already fixed the data side).
  - The Dhan fetch, Supabase sb_insert/sb_upsert helpers, bar ts truncation.
  - Module-level imports / constants (above main()).
  - Any logic outside main().

Target: capture_spot_1m.py
Validation: ast.parse(), import test, live smoke (three scenarios).
"""
from __future__ import annotations

import argparse
import ast
import shutil
import sys
from pathlib import Path


TARGET_DEFAULT = r"C:\GammaEnginePython\capture_spot_1m.py"


# ---------------------------------------------------------------------------
# Edit 1: Add ExecutionLog import. Anchor on the existing dotenv import block
# so the new import sits with the other core/ project imports once we add it.
# We'll place the ExecutionLog import immediately after the dotenv block.
# ---------------------------------------------------------------------------

EDIT1_OLD = '''try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass'''

EDIT1_NEW = '''try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ENH-71 write-contract layer. ExecutionLog records every invocation to
# script_execution_log with expected vs actual writes, exit_reason, and
# contract_met. See docs/MERDIAN_Master_V19.docx Session 2.
from core.execution_log import ExecutionLog'''


# ---------------------------------------------------------------------------
# Edit 2: Env-var check -> DEPENDENCY_MISSING. Anchor on the for-loop header.
# We replace the whole check block.
# ---------------------------------------------------------------------------

EDIT2_OLD = '''def main() -> int:
    for var, val in [("SUPABASE_URL", SUPABASE_URL), ("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_KEY),
                     ("DHAN_CLIENT_ID", DHAN_CLIENT_ID), ("DHAN_API_TOKEN", DHAN_API_TOKEN)]:
        if not val:
            print(f"[ERROR] Missing {var}", file=sys.stderr)
            return 1'''

EDIT2_NEW = '''def main() -> int:
    # ── ENH-71 write-contract declaration ────────────────────────────────────
    # Every invocation of this script is expected to write exactly 2 rows to
    # each of market_spot_snapshots and hist_spot_bars_1m (NIFTY + SENSEX).
    # Any lower count = contract violation, surfaced in dashboard.
    log = ExecutionLog(
        script_name="capture_spot_1m.py",
        expected_writes={
            "market_spot_snapshots": 2,
            "hist_spot_bars_1m":     2,
        },
        notes="minute spot capture NIFTY+SENSEX",
    )

    missing_vars = []
    for var, val in [("SUPABASE_URL", SUPABASE_URL), ("SUPABASE_SERVICE_ROLE_KEY", SUPABASE_KEY),
                     ("DHAN_CLIENT_ID", DHAN_CLIENT_ID), ("DHAN_API_TOKEN", DHAN_API_TOKEN)]:
        if not val:
            print(f"[ERROR] Missing {var}", file=sys.stderr)
            missing_vars.append(var)
    if missing_vars:
        return log.exit_with_reason(
            "DEPENDENCY_MISSING",
            exit_code=1,
            error_message=f"Missing env vars: {', '.join(missing_vars)}",
        )'''


# ---------------------------------------------------------------------------
# Edit 3: Holiday gate -> log.exit_with_reason('HOLIDAY_GATE'). THIS is the
# win. Today's outage disappears from "silent exit" to "alert-grade row".
# Anchor on the print + return 0 inside the holiday branch.
# ---------------------------------------------------------------------------

EDIT3_OLD = '''                if not _row.get("is_open", True) or _row.get("open_time") is None:
                    print(f"[{_today}] Market holiday — capture_spot_1m exiting cleanly.")
                    return 0'''

EDIT3_NEW = '''                if not _row.get("is_open", True) or _row.get("open_time") is None:
                    print(f"[{_today}] Market holiday — capture_spot_1m exiting cleanly.")
                    # ENH-71: explicit HOLIDAY_GATE exit. Contract_met will be
                    # False because expected_writes was declared but we exited
                    # without writing -- exactly what we want for today's bug
                    # class (holiday gate firing on a trading day is now
                    # surfaced, not silent).
                    return log.exit_with_reason("HOLIDAY_GATE", notes=f"trading_calendar says closed for {_today}")'''


# ---------------------------------------------------------------------------
# Edit 4: Dhan fetch exception -> TOKEN_EXPIRED (if 401-ish) or DATA_ERROR.
# ---------------------------------------------------------------------------

EDIT4_OLD = '''    try:
        spots = fetch_spots()
    except Exception as e:
        print(f"  [ERROR] Dhan fetch failed: {e}", file=sys.stderr)
        return 1'''

EDIT4_NEW = '''    try:
        spots = fetch_spots()
    except Exception as e:
        print(f"  [ERROR] Dhan fetch failed: {e}", file=sys.stderr)
        # ENH-71: classify the failure. 401/auth hints -> TOKEN_EXPIRED so
        # alert daemon can distinguish "token needs refresh" from "Dhan down".
        _err = str(e)
        _auth_hint = ("401" in _err) or ("Authentication" in _err) or ("token invalid" in _err.lower())
        _reason = "TOKEN_EXPIRED" if _auth_hint else "DATA_ERROR"
        return log.exit_with_reason(_reason, exit_code=1, error_message=_err[:2000])'''


# ---------------------------------------------------------------------------
# Edit 5: Record writes after each sb_insert/sb_upsert success.
# We anchor on each success-print line and append a record_write call.
# ---------------------------------------------------------------------------

EDIT5A_OLD = '''    try:
        sb_insert("market_spot_snapshots", snap_rows)
        print(f"  market_spot_snapshots: {len(snap_rows)} rows inserted")
    except Exception as e:
        print(f"  [WARN] market_spot_snapshots write failed: {e}", file=sys.stderr)'''

EDIT5A_NEW = '''    try:
        sb_insert("market_spot_snapshots", snap_rows)
        print(f"  market_spot_snapshots: {len(snap_rows)} rows inserted")
        log.record_write("market_spot_snapshots", len(snap_rows))  # ENH-71
    except Exception as e:
        print(f"  [WARN] market_spot_snapshots write failed: {e}", file=sys.stderr)'''


EDIT5B_OLD = '''    try:
        sb_upsert("hist_spot_bars_1m", bar_rows, on_conflict="instrument_id,bar_ts")
        print(f"  hist_spot_bars_1m:     {len(bar_rows)} rows upserted (bar_ts={bar_ts[:16]})")
    except Exception as e:
        print(f"  [WARN] hist_spot_bars_1m write failed: {e}", file=sys.stderr)'''

EDIT5B_NEW = '''    try:
        sb_upsert("hist_spot_bars_1m", bar_rows, on_conflict="instrument_id,bar_ts")
        print(f"  hist_spot_bars_1m:     {len(bar_rows)} rows upserted (bar_ts={bar_ts[:16]})")
        log.record_write("hist_spot_bars_1m", len(bar_rows))  # ENH-71
    except Exception as e:
        print(f"  [WARN] hist_spot_bars_1m write failed: {e}", file=sys.stderr)'''


# ---------------------------------------------------------------------------
# Edit 6: Final return -> log.complete(). Anchor on the Done + return 0.
# ---------------------------------------------------------------------------

EDIT6_OLD = '''    print(f"  Done.")
    return 0'''

EDIT6_NEW = '''    print(f"  Done.")
    # ENH-71: complete() computes contract_met and writes the final audit
    # row. Returns exit_code (0) for the script to propagate via sys.exit.
    return log.complete()'''


EDITS = [
    ("[ENH-71/1] Import ExecutionLog",                     EDIT1_OLD, EDIT1_NEW),
    ("[ENH-71/2] Env-var check -> DEPENDENCY_MISSING",     EDIT2_OLD, EDIT2_NEW),
    ("[ENH-71/3] Holiday gate -> HOLIDAY_GATE (silent->loud)", EDIT3_OLD, EDIT3_NEW),
    ("[ENH-71/4] Dhan fetch -> TOKEN_EXPIRED/DATA_ERROR",  EDIT4_OLD, EDIT4_NEW),
    ("[ENH-71/5a] record_write(market_spot_snapshots)",    EDIT5A_OLD, EDIT5A_NEW),
    ("[ENH-71/5b] record_write(hist_spot_bars_1m)",        EDIT5B_OLD, EDIT5B_NEW),
    ("[ENH-71/6] Final -> log.complete()",                 EDIT6_OLD, EDIT6_NEW),
]


def apply_patch(text: str) -> str:
    if "ENH-71" in text:
        raise RuntimeError("ENH-71 marker already present in file. Refusing to re-patch.")
    for label, old, new in EDITS:
        n = text.count(old)
        if n != 1:
            raise RuntimeError(f"{label}: anchor matched {n} times (need exactly 1).")
        text = text.replace(old, new, 1)
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default=TARGET_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    try:
        ast.parse(Path(__file__).read_text(encoding="utf-8"))
    except SyntaxError as e:
        print(f"FAIL: self-syntax: {e}", file=sys.stderr)
        return 1

    target = Path(args.target)
    if not target.exists():
        print(f"FAIL: target not found: {target.resolve()}", file=sys.stderr)
        return 2

    original = target.read_text(encoding="utf-8-sig")
    had_bom = target.read_bytes().startswith(b"\xef\xbb\xbf")

    try:
        patched = apply_patch(original)
    except RuntimeError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 3

    try:
        ast.parse(patched)
    except SyntaxError as e:
        print(f"FAIL: patched file does not parse: {e}", file=sys.stderr)
        return 4

    enh71_count = patched.count("ENH-71")
    if enh71_count < 7:
        print(f"FAIL: expected >=7 ENH-71 markers, found {enh71_count}", file=sys.stderr)
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
    for label, _, _ in EDITS:
        print(f"  {label}")

    if args.dry_run:
        print()
        print("DRY RUN - nothing written.")
        return 0

    if not args.no_backup:
        backup = target.with_suffix(target.suffix + ".pre_enh71.bak")
        shutil.copy2(target, backup)
        print(f"backup:   {backup.name}")

    target.write_text(patched, encoding="utf-8")
    print()
    print("APPLIED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
