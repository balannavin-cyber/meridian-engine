#!/usr/bin/env python3
"""Tape T1-db mutant harness (docs/tape/T1_db_plan.md section 2), same shape as tests/tape_t1b_mutants.py.

For each mutant: copy the tree to a temp dir, apply ONE exact-string patch (it must match exactly once --
"MUTANT NOT APPLIED" is a FAIL, never a skip), run the named guard against the copy with
tests/test_tape_t1db.py --root, and require FAIL (exit 1; a rule-23 refusal, exit 2, is NOT a catch).
The control (unpatched copy) must PASS. The copy is not a git checkout, so the worktree HEAD is passed to it in
TAPE_T1DB_HEAD (the loader's code_sha lookup is injected from it by the test, never by the loader).

  python tests/tape_t1db_mutants.py [--repeat N] [--only M-T1DB-...]
  (Local, inside 08:30-15:45 IST on a weekday: set TAPE_RULE23_OVERRIDE_R1=1, operator ruling R-1, 2026-11-03)

Last line: "TAPE T1DB MUTANTS PASS (10/10 caught xN, 9/9 controls xN)" or FAIL. Exit 0 / 1.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIG = "sql/2026-11-03_tape_t1db_sidecar.sql"
COPY = ["merdian_compute", "services", "tests/test_tape_t1db.py", "tests/tape_t1db", "tests/tape_t1a", "tests/tape_t1b",
        MIG, "sql/2026-11-03_tape_t1db_contracts.sql", "check_contracts_shadow.py"]
LD = "services/tape_db/load_day.py"
NULL_LEDGER = ('    ledger = (lambda **kw: type("NullLedger", (), {"record_write": lambda s, t, n: None, '
               '"complete": lambda s, notes=None: 0, '
               '"exit_with_reason": lambda s, *a, **k: k.get("exit_code", 1)})())(\n')

M = [
    ("M-T1DB-COLUMN-DROPPED", "db-ddl-columns", MIG, "    vwap                     double precision,\n", ""),
    ("M-T1DB-NO-REVOKE", "db-ddl-access", MIG, "REVOKE ALL ON public.tape_events FROM anon, authenticated;\n", ""),
    ("M-T1DB-RLS-OFF", "db-ddl-access", MIG, "ALTER TABLE public.tape_minute ENABLE ROW LEVEL SECURITY;",
     "ALTER TABLE public.tape_minute DISABLE ROW LEVEL SECURITY;"),
    ("M-T1DB-JOIN-VIEW", "db-no-join", MIG, "\nCOMMIT;\n",
     "\nCREATE VIEW public.v_tape_x AS SELECT m.symbol FROM public.tape_minute m "
     "JOIN public.tape_chain_events e ON e.symbol = m.symbol;\nCOMMIT;\n"),
    ("M-T1DB-MANIFEST-IGNORED", "load-manifest", LD, '    if problems:\n        raise Refused(3, "MANIFEST FAIL',
     '    if False:\n        raise Refused(3, "MANIFEST FAIL'),
    ("M-T1DB-COUNT-SKIPPED", "load-counts", LD, "            if got[t] == csv_n[t]:\n", "            if True:\n"),
    ("M-T1DB-SILENT-OVERWRITE", "load-replace", LD, "    if any(existing.values()) and not a.replace:\n", "    if False:\n"),
    ("M-T1DB-NO-LEDGER", "load-provenance", LD, "    ledger = (ledger_factory or _default_ledger)(\n", NULL_LEDGER),
    ("M-T1DB-WRITES-GEX", "load-tables-only", LD, "        # 7. read back\n",
     '        client.insert("gex_strike_snapshots", [])\n        # 7. read back\n'),
    ("M-T1DB-RUNNER-IMPORTS", "t1db-isolated", "services/tape_runner/recorder.py",
     "import json\n", "import json\nfrom services.tape_db import load_day  # noqa\n"),
]


def head():
    r = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30)
    return r.stdout.strip()


def make_copy():
    d = tempfile.mkdtemp(prefix="tape_t1db_mut_")
    for rel in COPY:
        src, dst = os.path.join(REPO, rel), os.path.join(d, rel)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    return d


def run_guard(root, guard, h):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TAPE_T1DB_HEAD=h)
    p = subprocess.run([sys.executable, os.path.join(root, "tests", "test_tape_t1db.py"), "--root", root,
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
    h = head()
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
                rc, last, exc = run_guard(d, guard, h)
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
                rc, last, _exc = run_guard(d, guard, h)
                passed += (rc == 0 and "PASS" in last)
            finally:
                shutil.rmtree(d, ignore_errors=True)
        row_ok = passed == a.repeat
        ctl_rows += row_ok
        ok_all &= row_ok
        print("CONTROL %s guard=%s %d/%d" % ("PASS" if row_ok else "FAIL", guard, passed, a.repeat), flush=True)
    print("TAPE T1DB MUTANTS %s (%d/%d caught x%d, %d/%d controls x%d)" % (
        "PASS" if ok_all else "FAIL", caught_rows, len(muts), a.repeat, ctl_rows, len(guards), a.repeat))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
