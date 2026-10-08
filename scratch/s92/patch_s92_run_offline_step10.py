#!/usr/bin/env python3
"""
patch_s92_run_offline_step10.py -- S92 build #2.
Adds tests/test_ts_parse_core.py to tests/run_offline.sh as step 10/10 and
renumbers the nine existing steps from N/9 to N/10.

CANON-V3, adapted for a shell script: read_bytes + decode('utf-8-sig'), BOM
round-tripped, predominant EOL restored, every anchor count==1 or ABORT checked
before any replacement, _PRE_S92B backup, dry-run default with --apply,
idempotency marker, summary computed from the per-edit results. The syntax gate
is `bash -n` rather than ast.parse -- the same obligation applied to the right
language, since a broken suite runner would be discovered at the next run
instead of here.

WHY THE RENUMBER IS TEN SEPARATE EDITS, not one regex: a regex over `/9` would
also hit any other `/9` in the file (a date, a path, a comment), and a
count==1 anchor per line is the thing that makes a miss loud. The ten counts are
printed so a partial renumber cannot pass silently.
"""
from __future__ import annotations

import difflib
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path("/home/ssm-user/meridian-cc")
TARGET = REPO / "tests" / "run_offline.sh"
BACKUP = TARGET.with_name(TARGET.name + "_PRE_S92B")
MARKER = "test_ts_parse_core.py"

LABELS = [
    (1, "contract runner unit tests"),
    (2, "seeded defects on golden day"),
    (3, "replay vs pinned statuses"),
    (4, "ledger child runs (S90_CHILD_RUN)"),
    (5, "CAS close slot pick (S90_CAS_SLOT_PICK)"),
    (6, "CAS recon auto-correct (two sources)"),
    (7, "cycle-history ts fraction widths (ENH-133 _ist_date)"),
    (8, "marker writer ts fraction widths (TD-S91-NEW-2 site 2)"),
    (9, "orchestrator monitor alert gate + dedupe"),
]

EDITS = [(f"R{n} renumber {n}/9", f'echo "== {n}/9 {lab}"', f'echo "== {n}/10 {lab}"')
         for n, lab in LABELS]

# The new step goes AFTER 9/10 and BEFORE the summary echo.
STEP10_OLD = '''echo "OFFLINE $([ $rc -eq 0 ] && echo PASS || echo FAIL)"
'''
STEP10_NEW = '''# S92: TD-S91-NEW-2 site 7 / TD-S91-NEW-6. core.ts_parse is the shared PostgREST
# timestamp parser; this exercises widths 0-6, Z, offsets, naive and malformed input,
# and the five real wire strings from 2026-10-08 including the rows[0] of that day's
# three DATA_ERROR basis runs. Pure Python, no fixtures, no golden day -- it adds
# nothing to the rule 23 memory ceiling.
echo "== 10/10 core.ts_parse shared ts parser (TD-S91-NEW-2 site 7)"; python3 tests/test_ts_parse_core.py | tail -1; [ "${PIPESTATUS[0]}" -eq 0 ] || rc=1
echo "OFFLINE $([ $rc -eq 0 ] && echo PASS || echo FAIL)"
'''

ALL_EDITS = EDITS + [("S10 insert step 10", STEP10_OLD, STEP10_NEW)]


def bash_ok(text: str) -> tuple:
    p = Path(tempfile.mktemp(suffix=".sh"))
    p.write_text(text)
    r = subprocess.run(["bash", "-n", str(p)], capture_output=True, text=True)
    p.unlink(missing_ok=True)
    return r.returncode == 0, (r.stderr or "").strip()


def main() -> int:
    apply = "--apply" in sys.argv[1:]
    print("=" * 72)
    print(f"patch_s92_run_offline_step10 -- {'APPLY' if apply else 'DRY RUN'}")
    print("=" * 72)

    test_file = REPO / "tests" / "test_ts_parse_core.py"
    if not test_file.exists():
        print(f"ABORT: {test_file} missing -- the step would call a file that is "
              f"not there and the suite would fail on it.")
        return 2
    print(f"  test file : present ({test_file.stat().st_size} bytes)")

    raw = TARGET.read_bytes()
    has_bom = raw[:3] == b"\xef\xbb\xbf"
    enc = "utf-8-sig" if has_bom else "utf-8"
    src_raw = raw.decode("utf-8-sig")
    crlf = src_raw.count("\r\n")
    bare_lf = src_raw.count("\n") - crlf
    write_eol = "\r\n" if crlf >= bare_lf else "\n"
    print(f"  file      : {TARGET}")
    print(f"  bytes     : {len(raw)}  bom={has_bom}  crlf={crlf} bare_lf={bare_lf}")

    src_lf = src_raw.replace("\r\n", "\n")

    if MARKER in src_lf:
        print(f"  SKIP      : {MARKER} already referenced; nothing to do")
        print(f"\nRESULT: 0 of {len(ALL_EDITS)} edits need applying (already applied).")
        return 0

    bad = []
    for name, old, _new in ALL_EDITS:
        n = src_lf.count(old)
        print(f"  anchor    : {name:<24s} count={n}")
        if n != 1:
            bad.append((name, n))
    if bad:
        print("\nABORT: anchors not unique-and-present. Nothing written.")
        for name, n in bad:
            print(f"         {name}: count={n}")
        return 2

    patched_lf = src_lf
    applied = []
    for name, old, new in ALL_EDITS:
        before = patched_lf
        patched_lf = patched_lf.replace(old, new, 1)
        applied.append((name, patched_lf != before))
    if any(not ok for _n, ok in applied):
        print(f"ABORT: no-op edits: {[n for n, ok in applied if not ok]}")
        return 2

    ok, err = bash_ok(patched_lf)
    print(f"  bash -n   : {'OK' if ok else 'FAILED'}")
    if not ok:
        print(f"ABORT: {err}")
        return 2

    # the renumber must be complete: no "/9 " step labels may survive
    left = sum(1 for n, _lab in LABELS if f'== {n}/9 ' in patched_lf)
    print(f"  renumber  : surviving N/9 step labels = {left} (require 0)")
    if left:
        print("ABORT: partial renumber. Nothing written.")
        return 2

    print("\n--- diff ---")
    for line in difflib.unified_diff(
            src_lf.splitlines(True), patched_lf.splitlines(True),
            fromfile="a/run_offline.sh", tofile="b/run_offline.sh", n=1):
        sys.stdout.write(line)
    print("--- end diff ---\n")

    if not apply:
        print("DRY RUN: nothing written. Re-run with --apply.")
        print(f"RESULT: {sum(1 for _n, a in applied if a)} of {len(ALL_EDITS)} "
              f"edits would be applied; bash -n OK; renumber complete.")
        return 0

    if BACKUP.exists():
        print(f"  backup    : {BACKUP.name} already exists; left as-is")
    else:
        BACKUP.write_bytes(raw)
        print(f"  backup    : wrote {BACKUP.name} ({len(raw)} bytes)")

    out = patched_lf.replace("\n", write_eol) if write_eol == "\r\n" else patched_lf
    TARGET.write_bytes(out.encode(enc))
    TARGET.chmod(0o755)

    back = TARGET.read_bytes().decode("utf-8-sig")
    ok2, err2 = bash_ok(back)
    checks = {
        "step 10 present": "== 10/10 core.ts_parse" in back,
        "test referenced": MARKER in back,
        "renumber complete": not any(f'== {n}/9 ' in back for n, _l in LABELS),
        "ten step labels": sum(f'== {n}/10 ' in back for n in range(1, 11)) == 10,
        "bash -n on disk": ok2,
        "executable": bool(TARGET.stat().st_mode & 0o100),
    }
    for k, v in checks.items():
        print(f"  verify    : {k:<22s} {v}")
    if not ok2:
        print(f"  bash -n error: {err2}")
    allok = all(checks.values())
    print(f"\nRESULT: {sum(1 for _n, a in applied if a)} of {len(ALL_EDITS)} edits "
          f"applied; artefact checks {'ALL PASS' if allok else 'FAILED'}.")
    return 0 if allok else 2


if __name__ == "__main__":
    sys.exit(main())
