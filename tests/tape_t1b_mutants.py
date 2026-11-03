#!/usr/bin/env python3
"""Tape T1b mutant harness (docs/tape/T1b_plan.md section 2), same shape as tests/tape_t1a_mutants.py.

For each mutant: copy the tree to a temp dir, apply ONE exact-string patch (it must match exactly once --
"MUTANT NOT APPLIED" is a FAIL, never a skip), run the named guard against the copy with
tests/test_tape_t1b.py --root, and require FAIL (exit 1; a rule-23 refusal, exit 2, is NOT a catch).
The control (unpatched copy) must PASS.

  python tests/tape_t1b_mutants.py [--repeat N] [--only M-T1B-...]
  (Local, inside 08:30-15:45 IST on a weekday: set TAPE_RULE23_OVERRIDE_R1=1, operator ruling R-1, 2026-11-03)

Last line: "TAPE T1B MUTANTS PASS (21/21 caught xN, 14/14 controls xN)" or FAIL. Exit 0 / 1.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY = ["merdian_compute", "services", "tests/test_tape_t1b.py", "tests/tape_t1b"]
CYC, EVT, CHN = "merdian_compute/tape/cycle.py", "merdian_compute/tape/events.py", "merdian_compute/tape/chain_events.py"
CLI = "services/tape_offline/cycle_day.py"
FOR_T = "        for T in range(first_T, LAST_T + 1, STEP):\n"

M = [
    ("M-T1B-BIN-OFF-BY-ONE", "cyc-bins", CYC,
     "    return 555 + 5 * ((m - 555) // 5 + 1)\n", "    return 555 + 5 * ((m - 555 + 4) // 5)\n"),
    ("M-T1B-CUM-RESET", "cyc-bins", CYC, FOR_T, FOR_T + "            if T % 60 == 0:\n                cb = cs = cu = cg = 0\n"),
    ("M-T1B-ZERO-FILL", "cyc-window", CYC, FOR_T, "        for T in range(FIRST_T, LAST_T + 1, STEP):\n"),
    ("M-T1B-DROPS-UNCL", "cyc-invariant", CYC, "            b[2] += uncl\n", "            b[2] += 0\n"),
    ("M-T1B-Z-INCLUDES-CURRENT", "ev-conc-z", EVT,
     "            v = n * Q - S * S\n            d = n * agg - S\n",
     "            n2, S2, Q2 = n + 1, S + agg, Q + agg * agg\n            v = n2 * Q2 - S2 * S2\n            d = n2 * agg - S2\n"),
    ("M-T1B-Z-THRESHOLD-2", "ev-conc-z", EVT, "d * d >= 9 * v", "d * d >= 4 * v"),
    ("M-T1B-ONE-BIN-FIRES", "ev-conc-z", EVT, "if c and prev_c and armed:", "if c and armed:"),
    ("M-T1B-HIST-11", "ev-conc-z", EVT, "MIN_PRIOR = 12\n", "MIN_PRIOR = 11\n"),
    ("M-T1B-THIN-MEAN-NOT-MEDIAN", "ev-thin", EVT, "            med2 = _median2(win)\n", "            med2 = 2 * sum(win) / w\n"),
    ("M-T1B-THIN-60PCT", "ev-thin", EVT, "4 * v <= med2", "10 * v <= 3 * med2"),
    ("M-T1B-REFIRE", "ev-onset", EVT, "if c and prev_c and armed:", "if c and prev_c:"),
    ("M-T1B-E2-4PCT", "ch-e1-e2", CHN, "OI_PCT = 5\n", "OI_PCT = 4\n"),
    ("M-T1B-ALL-EXPIRIES", "ch-e1-e2", CHN, 'fr = [g for g in grp if g["expiry_date"] == front]', "fr = list(grp)"),
    ("M-T1B-MERGE-20MIN", "ch-merge", CHN, "MERGE_SECONDS = 900\n", "MERGE_SECONDS = 1200\n"),
    ("M-T1B-NO-MERGE", "ch-merge", CHN, 'if a is not None and e["epoch"]', 'if False and a is not None and e["epoch"]'),
    ("M-T1B-E3-AS-EVENT", "ch-e3-count-only", CHN, "                e3 += 1\n",
     "                e3 += 1\n"
     '                ev.append(dict(symbol=cur["symbol"], expiry=cur["expiry"], epoch=cur["epoch"], ts_ist=cur["ts_ist"],'
     ' kind="E3", strike=0.0, prev_strike=0.0, prev_value=0.0, new_value=0.0))\n'),
    ("M-T1B-JOINS-CHAIN", "t1b-no-join", CLI, "import argparse\n", 'import argparse\nCHAIN = "gex_strike_snapshots"\n'),
    ("M-T1B-WALLCLOCK", "t1b-pure", EVT, "import json\nimport math\n", "import json\nimport math\nimport time\n_LOADED_AT = time.time()\n"),
    ("M-T1B-NONDETERMINISTIC", "t1b-deterministic", CLI,
     '"code": code_info(), "inputs": inputs', '"code": code_info(), "generated": __import__("time").time(), "inputs": inputs'),
    ("M-T1B-RUNNER-IMPORTS", "t1b-isolated", "services/tape_runner/recorder.py",
     "import json\n", "import json\nfrom services import tape_chain  # noqa\n"),
    ("M-T1B-EXPORT-UPSERT", "export-select-only", "services/tape_chain/export_chain.py",
     "client.select(TABLE, columns=COLUMNS,", "client.upsert(TABLE, columns=COLUMNS,"),
]


def make_copy():
    d = tempfile.mkdtemp(prefix="tape_t1b_mut_")
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
    p = subprocess.run([sys.executable, os.path.join(root, "tests", "test_tape_t1b.py"), "--root", root,
                        "--only", guard], capture_output=True, text=True, env=env, timeout=900)
    lines = p.stdout.strip().splitlines()
    last = lines[-1] if lines else ""
    exc = any("EXCEPTION" in ln for ln in lines)
    return p.returncode, last, exc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    muts = [m for m in M if a.only in (None, m[0])]
    ok_all, caught_rows = True, 0
    for name, guard, rel, old, new in muts:
        caught, by_exc = 0, 0
        for _ in range(a.repeat):
            d = make_copy()
            try:
                path = os.path.join(d, rel)
                with open(path, encoding="utf-8", newline="") as fh:
                    text = fh.read()
                o, nw = (old.replace("\n", "\r\n"), new.replace("\n", "\r\n")) if "\r\n" in text else (old, new)
                n = text.count(o)
                if n != 1:
                    print("MUTANT NOT APPLIED %s (%d matches in %s)" % (name, n, rel))
                    break
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(text.replace(o, nw))
                rc, last, exc = run_guard(d, guard)
                if rc == 1 and "FAIL" in last:
                    caught += 1
                    by_exc += exc
            finally:
                shutil.rmtree(d, ignore_errors=True)
        row_ok = caught == a.repeat
        caught_rows += row_ok
        ok_all &= row_ok
        print("%s %s guard=%s %d/%d%s" % ("CAUGHT" if row_ok else "MISSED", name, guard, caught, a.repeat,
                                         "  (via guard exception x%d)" % by_exc if by_exc else ""), flush=True)
    guards = sorted({m[1] for m in muts}, key=[m[1] for m in M].index)
    ctl_rows = 0
    for guard in guards:
        passed = 0
        for _ in range(a.repeat):
            d = make_copy()
            try:
                rc, last, _exc = run_guard(d, guard)
                passed += (rc == 0 and "PASS" in last)
            finally:
                shutil.rmtree(d, ignore_errors=True)
        row_ok = passed == a.repeat
        ctl_rows += row_ok
        ok_all &= row_ok
        print("CONTROL %s guard=%s %d/%d" % ("PASS" if row_ok else "FAIL", guard, passed, a.repeat), flush=True)
    print("TAPE T1B MUTANTS %s (%d/%d caught x%d, %d/%d controls x%d)" % (
        "PASS" if ok_all else "FAIL", caught_rows, len(muts), a.repeat, ctl_rows, len(guards), a.repeat))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
