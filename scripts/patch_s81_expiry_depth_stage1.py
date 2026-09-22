#!/usr/bin/env python3
"""S81 -- ADR-025 A1 stage 1: EXPIRY_DEPTH {NIFTY: 2, SENSEX: 2}, and fix the
stage-numbering comment that is off by one against A1.

WHAT CHANGES (one file, one anchor covering both)
  ingest_option_chain_local.py lines 57-60:
    * EXPIRY_DEPTH  {"NIFTY": 1, "SENSEX": 1} -> {"NIFTY": 2, "SENSEX": 2}
    * the stage table renumbered to ADR-025 A1: stage 0 = depth 1 (inert),
      stage 1 = W1+W2, stage 2 = NIFTY 4.

WHY THE COMMENT MATTERS AS MUCH AS THE CONSTANT
  The block read `stage 1 = depth 1 / stage 2 = depth 2 / stage 3 = depth 4`,
  which is off by one against ADR-025 Amendment A1 -- "a stage 0 at depth 1,
  provably inert, precedes W1+W2".  TD-S80-NEW-1's Status row carries the same
  error.  A1 governs.  The comment is what an implementer reads when choosing a
  value, so leaving it wrong while flipping the constant would guarantee the
  next person mis-stages.

PRECONDITION, ALREADY LANDED (commit 89ad2bb)
  Both latest-run selectors resolve the FRONT expiry's run_id rather than the
  newest-written row.  Without that, this flip would silently re-point gamma,
  volatility and options flow onto W2 from the first cycle, with no guard
  tripping.  Do not apply this patch to a tree that lacks 89ad2bb.

BLAST RADIUS, MEASURED
  Nothing fires until the 08:30 IST ingest.  W1 is written and committed
  before any extra expiry is attempted, and the "Run ID:" stdout contract is
  printed before the extra-expiry block, so a W2 failure degrades to exactly
  today's behaviour.

USAGE
  python3 scripts/patch_s81_expiry_depth_stage1.py            # dry run
  python3 scripts/patch_s81_expiry_depth_stage1.py --apply
"""
from __future__ import annotations

import ast
import py_compile
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path("/home/ssm-user/meridian-cc")
MARKER = "S81-EXPIRY-DEPTH-STAGE1"
BACKUP_SUFFIX = "_PRE_S81"
BOM = b"\xef\xbb\xbf"

OLD = '''#   stage 1  {"NIFTY": 1, "SENSEX": 1}  inert, behaviour identical to S79
#   stage 2  {"NIFTY": 2, "SENSEX": 2}  non-expiry day, after stage 1 verified
#   stage 3  {"NIFTY": 4, "SENSEX": 2}  after a week of ENH-99 retry telemetry
EXPIRY_DEPTH = {"NIFTY": 1, "SENSEX": 1}
'''

NEW = '''# ADR-025 A1 NUMBERING. CORRECTED S81: this table previously called depth 1
# "stage 1", which is off by one against Amendment A1 -- "a stage 0 at depth 1,
# provably inert, precedes W1+W2". TD-S80-NEW-1's Status row carries the same
# error. A1 governs; both were corrected at S81.
#
#   stage 0  {"NIFTY": 1, "SENSEX": 1}  inert, behaviour identical to S79
#   stage 1  {"NIFTY": 2, "SENSEX": 2}  W1+W2, ships on a non-expiry day
#   stage 2  {"NIFTY": 4, "SENSEX": 2}  after a week of ENH-99 retry telemetry
#
# S81-EXPIRY-DEPTH-STAGE1 -- at stage 1 since 2026-09-22, first live cycle the
# 08:30 IST ingest of 2026-09-23. PRECONDITION, landed in 89ad2bb: both
# latest-run selectors resolve the FRONT expiry's run_id, not the newest
# created_at. Without it this constant silently re-points gamma, volatility
# and options flow onto W2 from the first cycle, with no guard tripping.
# ROLLBACK is this one line back to {"NIFTY": 1, "SENSEX": 1}; it takes effect
# on the next cron fire, within 5 minutes, because run_ingest.sh re-execs
# Python each cycle and this constant is read at import.
EXPIRY_DEPTH = {"NIFTY": 2, "SENSEX": 2}
'''

TARGETS = [
    {
        "path": ROOT / "ingest_option_chain_local.py",
        "old": OLD,
        "new": NEW,
        "symbols": ["select_expiries", "extract_option_rows"],
    },
]


def named_symbols(src: str) -> set[str]:
    """Top-level def/class names. S64: ast.parse alone does not prove a `def`
    header survived the edit -- an orphaned body parses clean and NameErrors
    only at runtime."""
    return {
        n.name
        for n in ast.parse(src).body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def validate(target: dict) -> dict:
    """Phase 1. Validates and returns a plan. Writes NOTHING."""
    path: Path = target["path"]
    plan = {"status": "ABORT", "name": path.name, "detail": "",
            "path": path, "out_bytes": None, "eol_note": ""}

    if not path.exists():
        plan["detail"] = "file not found"
        return plan

    raw = path.read_bytes()
    has_bom = raw.startswith(BOM)
    src_raw = raw.decode("utf-8-sig")

    crlf = src_raw.count("\r\n")
    bare_lf = src_raw.count("\n") - crlf
    write_eol = "\r\n" if crlf >= bare_lf else "\n"
    mixed = crlf > 0 and bare_lf > 0
    plan["eol_note"] = (
        f"bom={'yes' if has_bom else 'no'} crlf={crlf} bare_lf={bare_lf} "
        f"write_eol={'CRLF' if write_eol != chr(10) else 'LF'}"
        + ("  *** MIXED EOL: write WILL normalise ***" if mixed else "")
    )

    src_lf = src_raw.replace("\r\n", "\n")

    if MARKER in src_lf:
        plan["status"] = "SKIP"
        plan["detail"] = "marker already present, nothing to do"
        return plan

    n = src_lf.count(target["old"])
    if n != 1:
        plan["detail"] = f"anchor count == {n}, expected exactly 1"
        return plan

    patched_lf = src_lf.replace(target["old"], target["new"])
    if patched_lf == src_lf:
        plan["detail"] = "replacement produced no change"
        return plan

    try:
        ast.parse(patched_lf)
    except SyntaxError as e:
        plan["detail"] = f"ast.parse failed: {e}"
        return plan

    lost = named_symbols(src_lf) - named_symbols(patched_lf)
    if lost:
        plan["detail"] = f"symbols LOST by the edit: {sorted(lost)}"
        return plan
    after = named_symbols(patched_lf)
    missing = [s for s in target["symbols"] if s not in after]
    if missing:
        plan["detail"] = f"required symbols absent after edit: {missing}"
        return plan

    # the constant must actually carry the new value, and the old one must be
    # gone from executable space (it survives only inside the stage table).
    if 'EXPIRY_DEPTH = {"NIFTY": 2, "SENSEX": 2}' not in patched_lf:
        plan["detail"] = "new EXPIRY_DEPTH assignment not present after edit"
        return plan
    if 'EXPIRY_DEPTH = {"NIFTY": 1, "SENSEX": 1}' in patched_lf:
        plan["detail"] = "old EXPIRY_DEPTH assignment still present"
        return plan

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8", newline="\n") as tf:
        tf.write(patched_lf)
        tmp = Path(tf.name)
    try:
        py_compile.compile(str(tmp), doraise=True)
    except py_compile.PyCompileError as e:
        plan["detail"] = f"py_compile failed: {e}"
        return plan
    finally:
        tmp.unlink(missing_ok=True)

    out_text = patched_lf.replace("\n", write_eol) if write_eol == "\r\n" else patched_lf
    out_bytes = out_text.encode("utf-8")
    if has_bom:
        out_bytes = BOM + out_bytes

    plan["status"] = "OK"
    plan["out_bytes"] = out_bytes
    plan["detail"] = "anchor 1, parse OK, compile OK, symbols intact, constant flipped"
    return plan


def main() -> int:
    apply = "--apply" in sys.argv
    print("=" * 74)
    print(f"S81 EXPIRY_DEPTH stage 1 (ADR-025 A1) -- {'APPLY' if apply else 'DRY RUN'}")
    print("=" * 74)

    plans = [validate(t) for t in TARGETS]
    for p in plans:
        print(f"  [{p['status']}] {p['name']}: {p['detail']}")
        print(f"          {p['eol_note']}")

    n_abort = sum(1 for p in plans if p["status"] == "ABORT")
    n_ok = sum(1 for p in plans if p["status"] == "OK")
    n_skip = sum(1 for p in plans if p["status"] == "SKIP")

    print("-" * 74)
    if n_abort:
        print(f"  files={len(plans)} ok={n_ok} skipped={n_skip} aborted={n_abort}")
        print("  RESULT: ABORTED in phase 1. NOTHING was written, by construction.")
        return 1
    if not apply:
        print(f"  files={len(plans)} would_patch={n_ok} skipped={n_skip}")
        print("  RESULT: dry run clean. Re-run with --apply.")
        return 0

    written: list[str] = []
    for p in plans:
        if p["status"] != "OK":
            continue
        path: Path = p["path"]
        backup = path.with_name(path.stem + BACKUP_SUFFIX + path.suffix)
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_bytes(p["out_bytes"])
        written.append(path.name)
        print(f"  WROTE {path.name} (backup {backup.name})")

    print("-" * 74)
    print(f"  files={len(plans)} written={len(written)} skipped={n_skip} aborted=0")
    print(f"  RESULT: applied to {written if written else 'NOTHING'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
