#!/usr/bin/env python3
"""ADR-033 step 11 gate, check 8 (code half): the hook patch applies and reverts cleanly, offline.

  python3 -B tests/test_gamma_v2_hook_patch_roundtrip.py

On a scratch copy of compute_gamma_metrics_local.py (never the working file), for both LF and CRLF line
endings: dry run changes nothing; --apply changes it and the result still compiles; a second --apply
refuses and changes nothing; --revert restores the file BYTE FOR BYTE (sha256 equal to the original);
a second --revert refuses and changes nothing. Controls that can fail: (1) a copy with one anchor removed
must be refused by --apply and left unchanged; (2) a copy where a hook insertion was edited by hand must
be refused by --revert and left unchanged; (3) the sha256 comparison itself is exercised on a deliberately
altered copy and must report a difference.

Not covered: the database half of check 8 (switching MERDIAN_GAMMA_V2 off, cron.unschedule, dropping any
v_gex2_* view); those are in the gate document's ordered procedure.
"""
from __future__ import annotations

import hashlib
import py_compile
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "compute_gamma_metrics_local.py"
PATCHER = ROOT / "scripts" / "gamma_v2_writer_hook_patch.py"
NAME = "compute_gamma_metrics_local.py"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(cwd: Path, *flags: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(PATCHER), *flags], cwd=cwd, capture_output=True, text=True)


def roundtrip(crlf: bool, errs: list[str]) -> None:
    label = "CRLF" if crlf else "LF"
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        f = d / NAME
        raw = SCRIPT.read_bytes().replace(b"\r\n", b"\n")
        f.write_bytes(raw.replace(b"\n", b"\r\n") if crlf else raw)
        h0 = sha(f)

        p = run(d)
        if p.returncode != 0 or sha(f) != h0 or "dry run" not in p.stdout:
            errs.append(f"{label}: dry run changed the file or failed: {p.stdout}{p.stderr}")
        p = run(d, "--apply")
        if p.returncode != 0:
            errs.append(f"{label}: --apply failed: {p.stdout}{p.stderr}"); return
        h1 = sha(f)
        if h1 == h0:
            errs.append(f"{label}: --apply changed nothing")
        txt = f.read_bytes().decode("utf-8")
        if txt.count("ADR-033 V2 hook") < 3:
            errs.append(f"{label}: fewer than three hook markers after --apply")
        if crlf and txt.replace("\r\n", "").count("\n"):
            errs.append(f"{label}: line endings mixed after --apply")
        try:
            py_compile.compile(str(f), cfile=str(d / "x.pyc"), doraise=True)
        except py_compile.PyCompileError as e:
            errs.append(f"{label}: patched file does not compile: {e}")
        p = run(d, "--apply")
        if p.returncode == 0 or sha(f) != h1:
            errs.append(f"{label}: a second --apply was not refused or changed the file")
        p = run(d, "--revert")
        if p.returncode != 0:
            errs.append(f"{label}: --revert failed: {p.stdout}{p.stderr}"); return
        if sha(f) != h0:
            errs.append(f"{label}: after --revert the file is NOT byte-identical to the original")
        p = run(d, "--revert")
        if p.returncode == 0 or sha(f) != h0:
            errs.append(f"{label}: a second --revert was not refused or changed the file")
    print(f"{label}: dry/apply/apply/revert/revert as required; reverted sha256 equals original")


def controls(errs: list[str]) -> None:
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        f = d / NAME
        src = SCRIPT.read_bytes()
        # (1) one anchor missing
        anchor = b"    print(f\"gex_strike_snapshots_rows_written={gss_n}\")\n"
        if src.count(anchor) != 1:
            errs.append("control 1 setup: anchor not found exactly once in the script"); return
        f.write_bytes(src.replace(anchor, b"    pass\n"))
        h = sha(f)
        p = run(d, "--apply")
        if p.returncode == 0 or sha(f) != h:
            errs.append("control 1: --apply did not refuse a script with a missing anchor")
        # (2) hand-edited insertion
        f.write_bytes(src)
        run(d, "--apply")
        t = f.read_bytes().decode("utf-8").replace("V1 does not read this", "V1 does not read this EDITED")
        f.write_bytes(t.encode("utf-8"))
        h = sha(f)
        p = run(d, "--revert")
        if p.returncode == 0 or sha(f) != h:
            errs.append("control 2: --revert did not refuse a hand-edited insertion")
        # (3) the comparison can fail
        g = d / "orig.py"; g.write_bytes(src)
        g2 = d / "alt.py"; g2.write_bytes(src + b"\n")
        if sha(g) == sha(g2):
            errs.append("control 3: sha256 did not differ for different files")
    print("controls 1 to 3: refusals and the hash comparison behave as required")


def main() -> int:
    errs: list[str] = []
    roundtrip(False, errs)
    roundtrip(True, errs)
    controls(errs)
    if errs:
        print("FAIL"); [print(" -", e) for e in errs]
        return 1
    print("PASS -- hook patch round trip, LF and CRLF, 3 controls")
    return 0


if __name__ == "__main__":
    sys.exit(main())
