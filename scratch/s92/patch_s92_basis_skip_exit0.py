#!/usr/bin/env python3
"""
patch_s92_basis_skip_exit0.py -- S92, TD-S91-NEW-15.

WHAT
  compute_basis_context_local.py ONLY: the SKIPPED_NO_INPUT early exit changes
  exit_code 1 -> 0. The ledger's exit_reason is UNCHANGED ("SKIPPED_NO_INPUT"),
  so the 12 structural cycles a day stay countable; they stop being
  indistinguishable from DATA_ERROR in the exit code.

WHAT THIS DOES NOT TOUCH
  run_merdian_shadow_runner_aws.py:364 carries the same reason with exit_code=1
  and is DELIBERATELY left alone (operator scope: "this file ONLY"). That site is
  reported read-only in scratch/s92/build_report_S92.md and stays open on
  TD-S91-NEW-15.

CANON-V3 (.claude/rules/python-writers.md)
  read_bytes + decode('utf-8-sig') | BOM round-tripped via enc | predominant EOL
  restored on write | anchors matched in LF-space | every anchor count==1 or
  ABORT | ast.parse gate before write | <name>_PRE_S92 backup | dry-run default,
  --apply required | idempotency marker per file-entry | summary COMPUTED from
  the per-file results, never a literal.

USAGE
  python3 scratch/s92/patch_s92_basis_skip_exit0.py            # dry run
  python3 scratch/s92/patch_s92_basis_skip_exit0.py --apply

ROLLBACK
  cp compute_basis_context_local.py_PRE_S92 compute_basis_context_local.py
  or: git checkout -- compute_basis_context_local.py   (pre-commit)
  or: git revert <sha>                                 (post-commit; 1 line, no DDL)
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TARGET = REPO / "compute_basis_context_local.py"
BACKUP = TARGET.with_name(TARGET.name + "_PRE_S92")
MARKER = "S92-SKIP-EXIT0"

OLD = """            return log.exit_with_reason(
                "SKIPPED_NO_INPUT", exit_code=1,
                error_message=f"No recent index_futures_snapshots for either symbol. statuses={per_symbol_status}",
            )
"""

NEW = """            # S92-SKIP-EXIT0 -- TD-S91-NEW-15, operator ruling 2026-10-08.
            # A skip is not a failure. exit_code 0; exit_reason UNCHANGED, so the
            # ledger still records SKIPPED_NO_INPUT and the 12 structural cycles
            # (08:31-09:26 IST, before futures capture starts at 09:30) remain
            # countable instead of reading as DATA_ERROR in the exit code.
            # error_message is kept: it is the only place statuses= survives.
            # SCOPE: this call site only. run_merdian_shadow_runner_aws.py:364
            # carries the same reason with exit_code=1 and is untouched.
            return log.exit_with_reason(
                "SKIPPED_NO_INPUT", exit_code=0,
                error_message=f"No recent index_futures_snapshots for either symbol. statuses={per_symbol_status}",
            )
"""


def main() -> int:
    apply = "--apply" in sys.argv[1:]
    print("=" * 72)
    print(f"patch_s92_basis_skip_exit0 -- {'APPLY' if apply else 'DRY RUN'}")
    print("=" * 72)

    if not TARGET.exists():
        print(f"ABORT: target not found: {TARGET}")
        return 2

    raw = TARGET.read_bytes()
    has_bom = raw[:3] == b"\xef\xbb\xbf"
    enc = "utf-8-sig" if has_bom else "utf-8"
    src_raw = raw.decode("utf-8-sig")
    crlf = src_raw.count("\r\n")
    bare_lf = src_raw.count("\n") - crlf
    write_eol = "\r\n" if crlf >= bare_lf else "\n"
    print(f"  file      : {TARGET}")
    print(f"  bytes     : {len(raw)}")
    print(f"  bom       : {has_bom}  (enc={enc})")
    print(f"  eol       : crlf={crlf} bare_lf={bare_lf} -> write as "
          f"{'CRLF' if write_eol == chr(13) + chr(10) else 'LF'}")

    src_lf = src_raw.replace("\r\n", "\n")

    # --- idempotency gate, this file-entry's own -----------------------------
    if MARKER in src_lf:
        print(f"  SKIP      : marker {MARKER!r} already present; nothing to do")
        print("\nRESULT: 0 of 1 entries need patching (already applied).")
        return 0

    # --- anchor, count must be exactly 1 ------------------------------------
    n = src_lf.count(OLD)
    print(f"  anchor    : count={n} (require exactly 1)")
    if n != 1:
        print("ABORT: anchor count != 1. Nothing written.")
        print("       0 means the file has drifted from the anchor (re-dump its")
        print("       bytes with repr and rebuild); >1 means the anchor is not")
        print("       unique and the edit would land in more than one place.")
        return 2

    patched_lf = src_lf.replace(OLD, NEW, 1)
    if patched_lf == src_lf:
        print("ABORT: replacement was a no-op. Nothing written.")
        return 2

    # --- ast gate: parse the PATCHED text, before any write -----------------
    try:
        ast.parse(patched_lf, filename=str(TARGET))
    except SyntaxError as e:
        print(f"ABORT: ast.parse failed on the patched text: {e}")
        return 2
    print("  ast.parse : OK on patched text")

    # --- the diff ------------------------------------------------------------
    print("\n--- diff (unified, LF-space) ---")
    import difflib
    for line in difflib.unified_diff(
            src_lf.splitlines(True), patched_lf.splitlines(True),
            fromfile=f"a/{TARGET.name}", tofile=f"b/{TARGET.name}", n=3):
        sys.stdout.write(line)
    print("--- end diff ---\n")

    if not apply:
        print("DRY RUN: nothing written. Re-run with --apply.")
        print("RESULT: 1 of 1 entries would be patched.")
        return 0

    # --- backup, then write --------------------------------------------------
    if BACKUP.exists():
        print(f"  backup    : {BACKUP.name} already exists; left as-is (older baseline wins)")
    else:
        BACKUP.write_bytes(raw)
        print(f"  backup    : wrote {BACKUP.name} ({len(raw)} bytes)")

    out = patched_lf.replace("\n", write_eol) if write_eol == "\r\n" else patched_lf
    TARGET.write_bytes(out.encode(enc))

    # --- artefact identity check, not "exited zero" -------------------------
    back = TARGET.read_bytes().decode("utf-8-sig")
    ok_marker = MARKER in back
    ok_exit0 = '"SKIPPED_NO_INPUT", exit_code=0,' in back
    ok_no_exit1 = '"SKIPPED_NO_INPUT", exit_code=1,' not in back
    print(f"  verify    : marker={ok_marker} exit_code=0 present={ok_exit0} "
          f"exit_code=1 gone={ok_no_exit1} bytes={TARGET.stat().st_size}")
    applied = 1 if (ok_marker and ok_exit0 and ok_no_exit1) else 0
    print(f"\nRESULT: {applied} of 1 entries patched and verified.")
    return 0 if applied == 1 else 2


if __name__ == "__main__":
    sys.exit(main())
