#!/usr/bin/env python3
"""
patch_s92_site7_adopt_core_ts.py -- S92 build #2.
TD-S91-NEW-2 site 7 / TD-S91-NEW-6.

WHAT
  compute_basis_context_local.py ONLY: `parse_ts` (:61-71) stops carrying its own
  unpadded `fromisoformat` body and delegates to the new shared
  `core.ts_parse.parse_pg_ts`. Two edits: the import, and the function body.

WHAT IS NOT TOUCHED, deliberately
  TD-S91-NEW-2 sites 1, 3, 4, 5, 6 and site 2. Site 2 (`build_market_spot_session_
  markers.parse_ts`) is already fixed by b48532e and its contract DIFFERS from the
  helper's: it preserves the input's own offset and has no naive-input branch,
  where `parse_pg_ts` normalises to UTC. Swapping the helper in there would be a
  silent behaviour change, not a refactor. The ~40 `ljust(6` copies also stay;
  retiring them is site-by-site work with a caller read each time.

WHY THIS IS A CAPTURE-PATH CHANGE
  `compute_basis_context_local.py` is an orchestrator STEP (:273 of
  run_merdian_shadow_runner_aws.py), so a defect here fails the whole cycle under
  the one-failing-step rule. Measured 2026-10-08: 3 of 84 runs exited DATA_ERROR,
  each with a trimmed-fraction `rows[0]` (widths 4, 5, 5), and 0 of the 69
  SUCCESS runs carried a failing width.

CANON-V3 (.claude/rules/python-writers.md)
  read_bytes + decode('utf-8-sig') | BOM round-tripped via enc | predominant EOL
  restored on write | anchors matched in LF-space | every anchor count==1 or
  ABORT, checked before any replacement | ast.parse AND py_compile AND a
  named-def existence check on the patched text before the write (the S64 lesson:
  an insertion can eat a `def` header and leave an orphaned body that parses
  clean) | <name>_PRE_S92B backup | dry-run default, --apply required |
  idempotency marker | summary COMPUTED from the per-edit results.

USAGE
  python3 scratch/s92/patch_s92_site7_adopt_core_ts.py            # dry run
  python3 scratch/s92/patch_s92_site7_adopt_core_ts.py --apply

ROLLBACK
  cp compute_basis_context_local.py_PRE_S92B compute_basis_context_local.py
  or: git restore -- compute_basis_context_local.py   (pre-commit)
  or: git revert <sha>                                (post-commit)
  NOTE: `git checkout` is denied in this session's permission set; use
  `git restore` or the cp above. Reverting this commit leaves core/ts_parse.py in
  place and unused, which is inert -- revert both commits to remove it.
"""
from __future__ import annotations

import ast
import difflib
import py_compile
import sys
import tempfile
from pathlib import Path

REPO = Path("/home/ssm-user/meridian-cc")
TARGET = REPO / "compute_basis_context_local.py"
BACKUP = TARGET.with_name(TARGET.name + "_PRE_S92B")
MARKER = "S92-SITE7"

# ---- edit 1: the import, beside the one core import already there ----------
E1_OLD = """from core.execution_log import ExecutionLog
"""
E1_NEW = """from core.execution_log import ExecutionLog
from core.ts_parse import parse_pg_ts
"""

# ---- edit 2: parse_ts delegates ---------------------------------------------
E2_OLD = '''def parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except Exception:
        return None
'''

E2_NEW = '''def parse_ts(value: Any) -> Optional[datetime]:
    """S92-SITE7 -- TD-S91-NEW-2 site 7 / TD-S91-NEW-6.

    Delegates to core.ts_parse.parse_pg_ts. The contract is UNCHANGED: falsy ->
    None, naive -> assumed UTC, aware -> converted to UTC, bad input -> None.
    The ONLY behavioural difference is that a microsecond fraction of 1, 2, 4 or
    5 digits now parses instead of raising.

    Why that mattered here. PostgREST trims trailing zeros, Python 3.10 (the box)
    accepts widths 0/3/6 only, and the old body called a bare `fromisoformat`.
    The `except -> None` then turned the ValueError into None, which
    `compute_for_symbol` reads as `no_rows` for that symbol -- and because the
    futures writer stamps ONE ts and reuses it for both symbols (measured: 203 of
    203 distinct ts carry both), a single trimmed timestamp failed BOTH symbols
    in the same cycle and the step exited DATA_ERROR, failing the whole
    orchestrator cycle. Measured on 2026-10-08: 3 of 84 runs, rows[0] widths
    4/5/5, against 0 of 69 successful runs carrying a failing width.

    The padding logic is NOT reimplemented here -- see core/ts_parse.py, which
    lifts it from write_gex_cycle_history_local.py:80-98 (bcadfa6).
    """
    return parse_pg_ts(value)
'''

EDITS = [
    ("E1 import core.ts_parse", E1_OLD, E1_NEW),
    ("E2 parse_ts delegates", E2_OLD, E2_NEW),
]


def _parses(text: str) -> bool:
    try:
        ast.parse(text)
        return True
    except SyntaxError:
        return False


def _defs(text: str) -> set:
    try:
        return {n.name for n in ast.walk(ast.parse(text))
                if isinstance(n, ast.FunctionDef)}
    except SyntaxError:
        return set()


def main() -> int:
    apply = "--apply" in sys.argv[1:]
    print("=" * 72)
    print(f"patch_s92_site7_adopt_core_ts -- {'APPLY' if apply else 'DRY RUN'}")
    print("=" * 72)

    helper = REPO / "core" / "ts_parse.py"
    if not helper.exists():
        print(f"ABORT: {helper} does not exist. The helper must land first -- "
              f"otherwise this patch makes the target import a missing module.")
        return 2
    print(f"  helper    : {helper} present ({helper.stat().st_size} bytes)")

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

    if MARKER in src_lf:
        print(f"  SKIP      : marker {MARKER!r} already present; nothing to do")
        print("\nRESULT: 0 of 2 edits need applying (already applied).")
        return 0

    bad = []
    for name, old, _new in EDITS:
        n = src_lf.count(old)
        print(f"  anchor    : {name:<28s} count={n}")
        if n != 1:
            bad.append((name, n))
    if bad:
        print("\nABORT: anchors not unique-and-present. Nothing written.")
        for name, n in bad:
            print(f"         {name}: count={n}")
        return 2

    patched_lf = src_lf
    applied = []
    for name, old, new in EDITS:
        before = patched_lf
        patched_lf = patched_lf.replace(old, new, 1)
        applied.append((name, patched_lf != before))
    if any(not ok for _n, ok in applied):
        print(f"ABORT: no-op edits: {[n for n, ok in applied if not ok]}")
        return 2

    # ---- three gates on the patched text, before any write -----------------
    if not _parses(patched_lf):
        try:
            ast.parse(patched_lf)
        except SyntaxError as e:
            print(f"ABORT: ast.parse failed on the patched text: {e}")
        return 2
    print("  ast.parse : OK on patched text")

    defs_before, defs_after = _defs(src_lf), _defs(patched_lf)
    lost = defs_before - defs_after
    print(f"  named defs: {len(defs_before)} -> {len(defs_after)}; "
          f"parse_ts present={'parse_ts' in defs_after}; lost={sorted(lost) or 'none'}")
    if lost or "parse_ts" not in defs_after:
        print("ABORT: a def disappeared, or parse_ts is gone. Nothing written.")
        return 2

    print("\n--- diff (unified, LF-space) ---")
    for line in difflib.unified_diff(
            src_lf.splitlines(True), patched_lf.splitlines(True),
            fromfile=f"a/{TARGET.name}", tofile=f"b/{TARGET.name}", n=3):
        sys.stdout.write(line)
    print("--- end diff ---\n")

    if not apply:
        print("DRY RUN: nothing written. Re-run with --apply.")
        print(f"RESULT: {sum(1 for _n, ok in applied if ok)} of {len(EDITS)} "
              f"edits would be applied; ast.parse OK; no def lost.")
        return 0

    if BACKUP.exists():
        print(f"  backup    : {BACKUP.name} already exists; left as-is")
    else:
        BACKUP.write_bytes(raw)
        print(f"  backup    : wrote {BACKUP.name} ({len(raw)} bytes)")

    out = patched_lf.replace("\n", write_eol) if write_eol == "\r\n" else patched_lf
    TARGET.write_bytes(out.encode(enc))

    # ---- artefact identity on what is now on disk --------------------------
    nraw = TARGET.read_bytes()
    back = nraw.decode("utf-8-sig")
    try:
        py_compile.compile(str(TARGET), cfile=tempfile.mktemp(), doraise=True)
        pyc = True
    except Exception as e:  # noqa: BLE001
        pyc = False
        print(f"  py_compile FAILED: {e}")
    checks = {
        "marker present": MARKER in back,
        "import added": "from core.ts_parse import parse_pg_ts" in back,
        "delegates": "return parse_pg_ts(value)" in back,
        "old body gone": "dt = datetime.fromisoformat(text)" not in back,
        "parse_ts still defined": "parse_ts" in _defs(back),
        "no def lost": not (_defs(src_lf) - _defs(back)),
        "ast reparses on disk": _parses(back),
        "py_compile on disk": pyc,
    }
    for k, v in checks.items():
        print(f"  verify    : {k:<24s} {v}")
    print(f"  verify    : bytes {len(raw)} -> {len(nraw)}")
    ok = all(checks.values())
    print(f"\nRESULT: {sum(1 for _n, a in applied if a)} of {len(EDITS)} edits "
          f"applied; artefact checks {'ALL PASS' if ok else 'FAILED'}.")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
