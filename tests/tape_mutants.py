#!/usr/bin/env python3
"""Tape T0 mutant harness (docs/tape/T0_plan.md §8).

For each mutant: copy the tape tree to a temp dir, apply ONE exact-string patch (it must match
exactly once -- "MUTANT NOT APPLIED" is a FAIL, never a skip), run the named guard against the copy
with tests/test_tape_t0.py --root, and require FAIL. The control (unpatched copy) must PASS.

  python3 tests/tape_mutants.py [--repeat N] [--only M-T0-...]

Last line: "TAPE T0 MUTANTS PASS (14/14 caught xN, 11/11 controls xN)" or FAIL. Exit 0 / 1.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY = ["merdian_compute", "services", "tests/test_tape_t0.py"]

M = [
    ("M-T0-MID-RULE-FLIPPED", "classify-synthetic", "merdian_compute/tape/classify.py",
     "    if p > mid:\n        return Trade(dv, BUY, price)\n    if p < mid:\n        return Trade(dv, SELL, price)\n",
     "    if p > mid:\n        return Trade(dv, SELL, price)\n    if p < mid:\n        return Trade(dv, BUY, price)\n"),
    ("M-T0-UNCL-DROPPED", "classify-synthetic", "merdian_compute/tape/classify.py",
     '            row["uncl_qty"] += trade.qty\n', "            pass\n"),
    ("M-T0-WALLCLOCK", "classify-purity", "merdian_compute/tape/classify.py",
     "from collections import namedtuple\n",
     "import time\nfrom collections import namedtuple\n_LOADED_AT = time.time()\n"),
    ("M-T0-NO-ROTATE", "segments-rotate", "services/tape_runner/segments.py",
     "        return cur_seg_ns != seg_ns\n", "        return False\n"),
    ("M-T0-DELETE-BEFORE-UPLOAD", "upload-verify", "services/tape_runner/uploader.py",
     '            with open(path, "rb") as body:\n',
     '            os.unlink(path)\n            with open(path, "rb") as body:\n'),
    ("M-T0-ETAG-IGNORED", "upload-verify", "services/tape_runner/uploader.py",
     "            if etag == md5_hex:\n", "            if True:\n"),
    ("M-T0-SHRINK-SUBS", "subs-grow-only", "services/tape_runner/recorder.py",
     '                self._subscribe(sym, su.window_tokens(pos), "grow", now,',
     '                old = [t for t, m in self.subscribed.items() if m["sym"] == sym and m["role"] == "OPT"]\n'
     '                self.ticker.unsubscribe(old)\n'
     '                for t in old:\n'
     '                    del self.subscribed[t]\n'
     '                self._subscribe(sym, su.window_tokens(pos), "grow", now,'),
    ("M-T0-DROP-CTL", "ctl-records", "services/tape_runner/recorder.py",
     '            self._ctl_all("disconnect", now, code=code, reason=self._clean(reason))\n',
     "            pass\n"),
    ("M-T0-DROP-CTL-RECONNECT", "ctl-records", "services/tape_runner/recorder.py",
     '            self._ctl_all("reconnect", now, attempt=attempt)\n', "            pass\n"),
    ("M-T0-CAP-DISABLED", "spool-cap", "services/tape_runner/recorder.py",
     "    def _over_cap(self):\n", "    def _over_cap(self):\n        return False\n"),
    ("M-T0-RESTART-ON-78", "token-fail", "services/tape_runner/tape-runner.service",
     "RestartPreventExitStatus=78 75\n", "RestartPreventExitStatus=75\n"),
    ("M-T0-NO-CLOSED-CHECK", "closed-day", "services/tape_runner/recorder.py",
     "        verdict, source = self._closed_verdict(now)\n", '        verdict, source = "OPEN", "mutant"\n'),
    ("M-T0-NO-MEMORYMAX", "fence", "services/tape_runner/tape-runner.service", "MemoryMax=400M\n", ""),
    ("M-T0-IMPORTS-DHAN", "no-db-no-dhan", "services/tape_runner/recorder.py",
     "import json\n", "import json\nimport dhanhq  # noqa\n"),
]


def make_copy():
    d = tempfile.mkdtemp(prefix="tape_mut_")
    for rel in COPY:
        src = os.path.join(REPO, rel)
        dst = os.path.join(d, rel)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    return d


def run_guard(root, guard):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, os.path.join(root, "tests", "test_tape_t0.py"), "--root", root,
                        "--only", guard], capture_output=True, text=True, env=env, timeout=600)
    last = (p.stdout.strip().splitlines() or [""])[-1]
    return p.returncode, last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    muts = [m for m in M if a.only in (None, m[0])]
    ok_all = True
    caught_rows = 0
    for name, guard, rel, old, new in muts:
        caught = 0
        for _ in range(a.repeat):
            d = make_copy()
            try:
                path = os.path.join(d, rel)
                text = open(path, encoding="utf-8").read()
                n = text.count(old)
                if n != 1:
                    print("MUTANT NOT APPLIED %s (%d matches in %s)" % (name, n, rel))
                    break
                open(path, "w", encoding="utf-8").write(text.replace(old, new))
                rc, last = run_guard(d, guard)
                if rc != 0 and "FAIL" in last:
                    caught += 1
            finally:
                shutil.rmtree(d, ignore_errors=True)
        row_ok = caught == a.repeat
        caught_rows += row_ok
        ok_all &= row_ok
        print("%s %s guard=%s %d/%d" % ("CAUGHT" if row_ok else "MISSED", name, guard, caught, a.repeat))
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
        print("CONTROL %s guard=%s %d/%d" % ("PASS" if row_ok else "FAIL", guard, passed, a.repeat))
    print("TAPE T0 MUTANTS %s (%d/%d caught x%d, %d/%d controls x%d)" % (
        "PASS" if ok_all else "FAIL", caught_rows, len(muts), a.repeat, ctl_rows, len(guards), a.repeat))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
