#!/usr/bin/env python3
"""Tape live L0 mutant harness (docs/tape/L0_plan.md section 7), same shape as tests/tape_t1b_mutants.py.

For each mutant: copy the tree to a temp dir, apply ONE exact-string patch (it must match exactly once -- "MUTANT NOT
APPLIED" is a FAIL, never a skip), run the named guard against the copy with tests/test_tape_live.py --root, and require
FAIL (exit 1; a rule-23 refusal, exit 2, is NOT a catch). Every repeat also runs each guard's control (an unpatched copy),
which must PASS (exit 0).

  python tests/tape_live_mutants.py [--repeat N] [--only M-L-...]
  (Local, inside 08:30-15:45 IST on a weekday: set TAPE_RULE23_OVERRIDE_R1=1, operator ruling R-1, 2026-11-03)

Last line: "TAPE LIVE MUTANTS PASS (22/22 caught xN, 12/12 controls xN)" or FAIL. Exit 0 / 1.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY = ["merdian_compute", "services", "sql/2026-11-06_tape_live_tables.sql", "tests/test_tape_live.py", "tests/tape_live"]
R, W, WS = "services/tape_live/rules.py", "services/tape_live/writer.py", "services/tape_live/wall_source.py"
V, CLI, SQL = "services/tape_live/verify_day.py", "services/tape_live/cli.py", "sql/2026-11-06_tape_live_tables.sql"
UNTR = '    if f["untraded"]:\n        return ("NO_READ", False, "untraded wall (vendor OI)")\n'
INWIN = '    if not f["in_window"]:\n        return ("NO_READ", False, "wall outside subscribed window")\n'
GRANT_L = "GRANT SELECT ON public.tape_live_label TO tape_ro, merdian_ro;\n"

M = [
    ("M-L-HIT-ABSORBED-SWAPPED", "live-vectors", R,
     '        if f["C"] and f["N"]:\n            return ("HIT", False, "")\n        if f["C"]:\n            return ("ABSORBED", False, "")\n',
     '        if f["C"] and f["N"]:\n            return ("ABSORBED", False, "")\n        if f["C"]:\n            return ("HIT", False, "")\n'),
    ("M-L-NOREAD-AS-QUIET", "live-vectors", R,
     '        return ("NO_READ", False, "flow not yet evaluable")\n', '        return ("QUIET", False, "")\n'),
    ("M-L-C-WHEN-NOT-EVALUABLE", "live-vectors", R, '    if f["thin_evaluable"]:\n        if f["N"]:\n',
     '    if f["thin_evaluable"]:\n        if f["C"]:\n            return ("ABSORBED", True, "flow n/a")\n        if f["N"]:\n'),
    ("M-L-ORDER-CHANGED", "live-vectors", R, INWIN + UNTR, UNTR + INWIN),
    ("M-L-UNTRADED-REMOVED", "live-vectors", R, UNTR, ""),
    ("M-L-LOOKBACK-10", "live-derive", R, "LOOKBACK_MIN = 15\n", "LOOKBACK_MIN = 10\n"),
    ("M-L-LOOKBACK-20", "live-derive", R, "LOOKBACK_MIN = 15\n", "LOOKBACK_MIN = 20\n"),
    ("M-L-BID-COUNTED", "live-derive", R, 'elif e["kind"] == "THIN" and e["side"] == "ask":', 'elif e["kind"] == "THIN":'),
    ("M-L-EVAL-11", "live-derive", R, "CONC_MIN_PRIOR = 12\n", "CONC_MIN_PRIOR = 11\n"),
    ("M-L-UNTRADED-ALWAYS", "live-derive", R, 'f["trades_cum"] == 0 and tm >= UNTRADED_FROM_MIN', 'f["trades_cum"] == 0'),
    ("M-L-READS-DEPTH", "live-rule-inputs", R, "def derive_flags(cycle_rows, events, wall_row, T, wall):\n",
     "def derive_flags(cycle_rows, events, wall_row, T, wall, depth=None):\n"),
    ("M-L-WALL-NEXT-RUN", "live-wall-floor", WS, '        if _floor5(r["ts_ist"]) <= tm:\n',
     '        if _floor5(r["ts_ist"]) <= tm + 5:\n'),
    ("M-L-LABEL-OVERWRITE", "live-first-wins", W, "        if key in self.labels:\n            return\n", ""),
    ("M-L-DROPS-LATE-SEGMENT", "live-equal-offline", W,
     '            self._rebuild_sym(sym, {"trigger": "late_segment", "at": at, "file": "%s/%s" % (sym, name)})\n',
     "            self.known[sym].pop()\n"),
    ("M-L-CUM-RESET-AT-SEGMENT", "live-equal-offline", W, "        rp = self.rp[sym]\n",
     "        rp = self.rp[sym] = self._new_replay(sym)\n"),
    ("M-L-USES-FUTURE-BIN", "live-causal", R, '        if lo < _min(e["ts_ist"]) <= tm:\n',
     '        if lo < _min(e["ts_ist"]) <= tm + 5:\n'),
    ("M-L-VERIFY-IGNORES-DIFF", "live-verify", V, "                if got == fl:\n", "                if True:\n"),
    ("M-L-NONDETERMINISTIC", "live-deterministic", CLI, "    live_run_id = str(uuid.uuid5(",
     "    live_run_id = str(uuid.uuid4()) or str(uuid.uuid5("),
    ("M-L-JOINS-OUTCOMES", "live-no-outcomes", V, "CAUSES = (", 'OUTCOME_COLS = ("spot_close", "straddle_atm")\nCAUSES = ('),
    ("M-L-WRITES-SIX-TABLES", "live-isolated", W, 'SYMBOLS = ("NIFTY", "SENSEX")\n',
     'SYMBOLS = ("NIFTY", "SENSEX")\nTARGET_TABLE = "tape_strike_cycle"\n'),
    ("M-L-IMPORTS-SUPABASE", "live-isolated", CLI, "def code_info():\n",
     "def code_info():\n    if False:\n        import supabase  # noqa: F401\n"),
    ("M-L-SQL-ANON-GRANT", "live-sql", SQL, GRANT_L, GRANT_L + "GRANT SELECT ON public.tape_live_label TO anon;\n"),
]


def copy_tree(dst):
    for rel in COPY:
        src = os.path.join(REPO, rel)
        out = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, out, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, out)


def patch(root, rel, old, new):
    p = os.path.join(root, rel)
    with open(p, "rb") as fh:
        text = fh.read().decode("utf-8")
    if text.count(old) != 1:
        return False
    with open(p, "wb") as fh:
        fh.write(text.replace(old, new).encode("utf-8"))
    return True


def run_guard(root, guard):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, os.path.join(root, "tests", "test_tape_live.py"), "--root", root, "--only", guard],
                       capture_output=True, text=True, env=env, timeout=1800)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    sel = [m for m in M if a.only in (None, m[0])]
    guards = sorted({m[1] for m in sel})
    caught, ctl_ok, fails = 0, 0, []
    for rep in range(a.repeat):
        for g in guards:
            tmp = tempfile.mkdtemp(prefix="tlm_ctl_")
            try:
                copy_tree(tmp)
                rc, out = run_guard(tmp, g)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            ok = rc == 0
            ctl_ok += ok
            print("rep %d CONTROL %-20s %s" % (rep + 1, g, "PASS" if ok else "FAIL rc=%s %s" % (rc, out[-1:] )))
            if not ok:
                fails.append("control %s rep %d" % (g, rep + 1))
        for name, guard, rel, old, new in sel:
            tmp = tempfile.mkdtemp(prefix="tlm_")
            try:
                copy_tree(tmp)
                if not patch(tmp, rel, old, new):
                    print("rep %d %-26s MUTANT NOT APPLIED (%s)" % (rep + 1, name, rel))
                    fails.append("%s not applied" % name)
                    continue
                rc, out = run_guard(tmp, guard)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            line = next((l for l in out if l.startswith("GUARD ")), out[-1] if out else "")
            ok = rc == 1
            caught += ok
            print("rep %d %-26s %-20s %s  %s" % (rep + 1, name, guard, "CAUGHT" if ok else "MISSED rc=%s" % rc, line[:160]))
            if not ok:
                fails.append("%s rep %d" % (name, rep + 1))
    n_m, n_g = len(sel), len(guards)
    if not fails:
        print("TAPE LIVE MUTANTS PASS (%d/%d caught x%d, %d/%d controls x%d)" % (n_m, n_m, a.repeat, n_g, n_g, a.repeat))
        return 0
    print("TAPE LIVE MUTANTS FAIL (%d/%d caught, %d/%d controls; %s)" % (
        caught, n_m * a.repeat, ctl_ok, n_g * a.repeat, "; ".join(fails[:10])))
    return 1


if __name__ == "__main__":
    sys.exit(main())
