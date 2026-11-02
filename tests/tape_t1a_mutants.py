#!/usr/bin/env python3
"""Tape T1a mutant harness (docs/tape/T1a_plan.md section 2), same shape as tests/tape_mutants.py.

For each mutant: copy the tree to a temp dir, apply ONE exact-string patch (it must match exactly once --
"MUTANT NOT APPLIED" is a FAIL, never a skip), run the named guard against the copy with
tests/test_tape_t1a.py --root, and require FAIL. The control (unpatched copy) must PASS.

  ( ulimit -v 2000000; python3 tests/tape_t1a_mutants.py [--repeat N] [--only M-T1A-...] )

Last line: "TAPE T1A MUTANTS PASS (15/15 caught xN, 12/12 controls xN)" or FAIL. Exit 0 / 1.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY = ["merdian_compute", "services", "tests/test_tape_t1a.py", "tests/tape_t1a"]
MIN, REP, CLI = "merdian_compute/tape/minute.py", "merdian_compute/tape/replay.py", "services/tape_offline/process_day.py"

M = [
    ("M-T1A-SIDES-SWAPPED", "proc-planted-sides", MIN,
     '        if side == "BUY": r[0] += qty\n        elif side == "SELL": r[1] += qty\n',
     '        if side == "BUY": r[1] += qty\n        elif side == "SELL": r[0] += qty\n'),
    ("M-T1A-UNCL-DROPPED", "proc-planted-sides", MIN,
     '        elif side == "UNCL": r[2] += qty\n', '        elif side == "UNCL": pass\n'),
    ("M-T1A-GAP-AS-CLASSIFIED", "proc-invariant", REP,
     'self._book(m, pk, "GAP", "gap", dv, None)', 'self._book(m, pk, "UNCL", "gap", dv, None)'),
    ("M-T1A-NO-GAP-SPLIT", "proc-gap", REP,
     "        return i < len(self.events) and self.events[i] <= hi\n", "        return False\n"),
    ("M-T1A-SEGMENT-RESET", "proc-boundary", REP,
     "        self._release(wm)\n", "        self._release(wm)\n        self.state.clear()\n"),
    ("M-T1A-ORDER-BY-FILE", "proc-order", REP,
     "heapq.heappush(self.heap, (val.ex, val.recv, val.dg, self.seq, val))",
     "heapq.heappush(self.heap, (0, 0, b'', self.seq, val))"),
    ("M-T1A-NONDETERMINISTIC", "proc-deterministic", CLI,
     '"code": code, "inputs"', '"code": code, "generated": __import__("time").time(), "inputs"'),
    ("M-T1A-G3-THRESHOLD-OFF", "proc-g3-verdict", MIN, "LATE_MIN_PCT = 70\n", "LATE_MIN_PCT = 30\n"),
    ("M-T1A-MANIFEST-IGNORED", "proc-manifest", CLI,
     "    if args.verify_manifest:\n        problems = verify_manifest", "    if False:\n        problems = verify_manifest"),
    ("M-T1A-WALLCLOCK", "proc-pure", REP, "import heapq\n", "import heapq\nimport time\n_LOADED_AT = time.time()\n"),
    ("M-T1A-JOINS-CHAIN", "proc-no-outcomes", CLI, "import argparse\n", 'import argparse\nCHAIN = "gex_strike_snapshots"\n'),
    ("M-T1A-RUNNER-IMPORTS", "proc-isolated", "services/tape_runner/recorder.py",
     "import json\n", "import json\nfrom services import tape_offline  # noqa\n"),
    ("M-T1A-INSTALL-SHIPS-ALL", "proc-isolated", "services/tape_runner/install.sh",
     "archive HEAD services/__init__.py services/tape_runner | tar", "archive HEAD services | tar"),
    ("M-T1A-SILENT-DROP", "proc-no-silent-drop", REP,
     '            self.disc("volume_regression", pk.bk)\n', "            pass\n"),
    ("M-T1A-SILENT-STALE", "proc-no-silent-drop", REP, "            self.disc(val[0], val[1])\n", "            pass\n"),
]


def make_copy():
    d = tempfile.mkdtemp(prefix="tape_t1a_mut_")
    for rel in COPY:
        src, dst = os.path.join(REPO, rel), os.path.join(d, rel)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    return d


def run_guard(root, guard):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, os.path.join(root, "tests", "test_tape_t1a.py"), "--root", root,
                        "--only", guard], capture_output=True, text=True, env=env, timeout=900)
    last = (p.stdout.strip().splitlines() or [""])[-1]
    return p.returncode, last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    muts = [m for m in M if a.only in (None, m[0])]
    ok_all, caught_rows = True, 0
    for name, guard, rel, old, new in muts:
        caught = 0
        for _ in range(a.repeat):
            d = make_copy()
            try:
                path = os.path.join(d, rel)
                with open(path, encoding="utf-8", newline="") as fh:
                    text = fh.read()
                n = text.count(old)
                if n != 1:
                    print("MUTANT NOT APPLIED %s (%d matches in %s)" % (name, n, rel))
                    break
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(text.replace(old, new))
                rc, last = run_guard(d, guard)
                if rc == 1 and "FAIL" in last:
                    caught += 1
            finally:
                shutil.rmtree(d, ignore_errors=True)
        row_ok = caught == a.repeat
        caught_rows += row_ok
        ok_all &= row_ok
        print("%s %s guard=%s %d/%d" % ("CAUGHT" if row_ok else "MISSED", name, guard, caught, a.repeat), flush=True)
    guards = sorted({m[1] for m in muts}, key=[m[1] for m in M].index)
    ctl_rows = 0
    for guard in guards:
        passed = 0
        for _ in range(a.repeat):
            d = make_copy()
            try:
                rc, last = run_guard(d, guard)
                passed += (rc == 0 and "PASS" in last)
            finally:
                shutil.rmtree(d, ignore_errors=True)
        row_ok = passed == a.repeat
        ctl_rows += row_ok
        ok_all &= row_ok
        print("CONTROL %s guard=%s %d/%d" % ("PASS" if row_ok else "FAIL", guard, passed, a.repeat), flush=True)
    print("TAPE T1A MUTANTS %s (%d/%d caught x%d, %d/%d controls x%d)" % (
        "PASS" if ok_all else "FAIL", caught_rows, len(muts), a.repeat, ctl_rows, len(guards), a.repeat))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
