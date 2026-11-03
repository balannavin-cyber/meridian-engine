#!/usr/bin/env python3
"""Tape scoring mutant harness (docs/tape/scoring_plan.md section 2), same shape as tests/tape_t1db_mutants.py.

For each mutant: copy the tree pieces to a temp dir, apply ONE exact-string patch (it must match exactly once --
"MUTANT NOT APPLIED" is a FAIL, never a skip), run the named guard against the copy with tests/test_tape_scoring.py
--root, and require a clean FAIL (exit 1, last line FAIL, no EXCEPTION in the output; a rule-23 refusal, exit 2, is NOT
a catch). The control (the unpatched copy, whole suite) must PASS.

  python tests/tape_scoring_mutants.py [--repeat N] [--only M-SC-...] [--jobs K]
  (Local, inside 08:30-15:45 IST on a weekday: set TAPE_RULE23_OVERRIDE_R1=1, operator ruling R-1, 2026-11-03)

Last line: "TAPE SCORING MUTANTS PASS (29/29 caught xN, N/N controls)" or FAIL. Exit 0 / 1.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY = ["services/__init__.py", "services/tape_scoring", "services/tape_runner", "tests/test_tape_scoring.py", "tests/tape_scoring"]
SC, WX, SQL = "services/tape_scoring/score.py", "services/tape_scoring/wilcoxon.py", "services/tape_scoring/scoring_extract.sql"

REMERGE = ('    counted, anchor = [], {}\n    for e in events:\n        a = anchor.get((e["kind"], e["K"]))\n'
           '        if a is not None and e["us"] - a["us"] <= 900 * 10 ** 6:\n            continue\n'
           '        anchor[(e["kind"], e["K"])] = e\n        counted.append(e)\n')

M = [
    ("M-SC-USES-MAGNITUDE", "sc-sign-only", SC, "    U = (total > 0) - (total < 0)\n", "    U = (total > 1) - (total < -1)\n"),
    ("M-SC-S-NO-NEGATION", "ha-s-definition", SC, "    D = -d_sum\n", "    D = d_sum\n"),
    ("M-SC-S-THRESHOLD-40", "ha-s-definition", SC, '    "cycle_share_min_pct": 50,\n', '    "cycle_share_min_pct": 40,\n'),
    ("M-SC-HA-INCLUDES-OPEN", "ha-clock", SC, '    return PARAMS["ha_first_G_min"] <= G <= PARAMS["ha_last_G_min"]\n',
     '    return G <= PARAMS["ha_last_G_min"]\n'),
    ("M-SC-HA-INCLUDES-LATE", "ha-clock", SC, '    return PARAMS["ha_first_G_min"] <= G <= PARAMS["ha_last_G_min"]\n',
     '    return PARAMS["ha_first_G_min"] <= G\n'),
    ("M-SC-DELTA-MEAN-NOT-MEDIAN", "ha-delta", SC,
     "    return Fraction(s[n // 2]) if n % 2 else Fraction(s[n // 2 - 1] + s[n // 2], 2)\n", "    return Fraction(sum(s), n)\n"),
    ("M-SC-MIN-2-CYCLES", "ha-delta", SC, '    "min_cycles_per_group": 3,\n', '    "min_cycles_per_group": 2,\n'),
    ("M-SC-WILCOXON-TWO-SIDED", "ha-wilcoxon", WX, "    return Fraction(cnt, 2 ** n)\n",
     "    return min(Fraction(1), 2 * Fraction(cnt, 2 ** n))\n"),
    ("M-SC-TIES-IGNORED", "ha-wilcoxon", WX, "            ranks[order[k]] = r\n", "            ranks[order[k]] = Fraction(k + 1)\n"),
    ("M-SC-N-19", "ha-decision", SC, '    if n < PARAMS["ha_min_days"]:\n', "    if n < 19:\n"),
    ("M-SC-EFFECT-005", "ha-decision", SC, '    "ha_min_median_delta": Fraction(1, 10),\n', '    "ha_min_median_delta": Fraction(1, 20),\n'),
    ("M-SC-P-020", "ha-decision", SC, '    "ha_p_max": Fraction(1, 10),\n', '    "ha_p_max": Fraction(1, 5),\n'),
    ("M-SC-ANY-STRIKE-IS-T1", "hb-labels", SC, '        if (leg == "CE" and strike == cw) or (leg == "PE" and strike == pw):\n',
     '        if leg in ("CE", "PE"):\n'),
    ("M-SC-E1-MATCHES-T3", "hb-match-kinds", SC, '    "E1": frozenset(("T1", "T2")),\n', '    "E1": frozenset(("T1", "T2", "T3")),\n'),
    ("M-SC-LEAD-EARLIEST", "hb-lead-nearest", SC, "    best = max(cands, key=lambda e: e[0])\n", "    best = min(cands, key=lambda e: e[0])\n"),
    ("M-SC-WINDOW-IGNORED", "hb-window", SC, "        if K not in win:\n", "        if False:\n"),
    ("M-SC-NULL-UNSEEDED", "hb-null", SC,
     '    return random.Random(int.from_bytes(hashlib.sha256(seed_bytes() + b"|" + sym.encode()).digest()[:8], "big"))\n',
     "    return random.Random()\n"),
    ("M-SC-NULL-50-DRAWS", "hb-null", SC, '    "null_draws": 100,\n', '    "null_draws": 50,\n'),
    ("M-SC-MARGINAL-AS-YES", "hb-decision", SC, '    return "MARGINAL", []\n', '    return "YES", []\n'),
    ("M-SC-N-299-OK", "hb-decision", SC, '    "hb_min_events": 300,\n', '    "hb_min_events": 299,\n'),
    ("M-SC-QUARANTINE-OFF", "sc-quarantine", SC, "    return reasons  # quarantine verdict\n", "    return []  # quarantine verdict\n"),
    ("M-SC-COMPLETENESS-90", "sc-quarantine", SC, '    "completeness_min_pct": 95,\n', '    "completeness_min_pct": 90,\n'),
    ("M-SC-REMERGE", "sc-no-remerge", SC, "    counted = events\n", REMERGE),
    ("M-SC-RUN-TWICE", "sc-run-once", SC, "    if prev == 0:\n        return None\n", "    if True:\n        return None\n"),
    ("M-SC-HASH-SKIPPED", "sc-hash-check", SC, "    return diffs\n", "    return []\n"),
    ("M-SC-EXTRACT-JOIN", "sc-extract-pure", SQL, "FROM public.gamma_metrics\n",
     "FROM public.gamma_metrics g JOIN public.gex_strike_snapshots s ON s.run_id = g.run_id\n"),
    ("M-SC-IMPORTS-SUPABASE", "sc-isolated", SC, "import hashlib\n", "import hashlib\nfrom supabase import create_client\n"),
    ("M-SC-RUNS-JOIN-MICROSECOND", "hb-labels", SC, "        cr = cruns.get(us // 10 ** 6)\n", "        cr = cruns.get(us)\n"),
    ("M-SC-PARAM-CHANGED", "sc-params", SC, '    "bootstrap_B": 1000,\n', '    "bootstrap_B": 500,\n'),
]


def make_copy():
    d = tempfile.mkdtemp(prefix="tape_score_mut_")
    for rel in COPY:
        src, dst = os.path.join(REPO, rel), os.path.join(d, rel)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    return d


def run_suite(root, guard=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    cmd = [sys.executable, os.path.join(root, "tests", "test_tape_scoring.py"), "--root", root]
    if guard:
        cmd += ["--only", guard]
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=1200)
    lines = p.stdout.strip().splitlines()
    return p.returncode, (lines[-1] if lines else ""), any("EXCEPTION" in ln for ln in lines)


def one(m):
    name, guard, rel, old, new = m
    d = make_copy()
    try:
        fp = os.path.join(d, rel)
        with open(fp, "rb") as fh:
            text = fh.read().decode("utf-8")
        if text.count(old) != 1:
            return name, False, "MUTANT NOT APPLIED (anchor matched %d times)" % text.count(old)
        with open(fp, "wb") as fh:
            fh.write(text.replace(old, new).encode("utf-8"))
        rc, last, exc = run_suite(d, guard)
        caught = rc == 1 and "FAIL" in last and not exc
        return name, caught, "rc=%d exception=%s %s" % (rc, exc, last)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", default=None)
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    muts = [m for m in M if not a.only or m[0] == a.only]
    caught = {m[0]: 0 for m in muts}
    detail = {}
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for name, ok, msg in ex.map(one, [m for m in muts for _ in range(a.repeat)]):
            caught[name] += bool(ok)
            if not ok:
                detail[name] = msg
    ctl = 0
    if not a.only:
        for _ in range(a.repeat):
            d = make_copy()
            try:
                rc, last, exc = run_suite(d)
                ctl += rc == 0 and "PASS" in last
            finally:
                shutil.rmtree(d, ignore_errors=True)
    for m in muts:
        print("%s %s %d/%d (guard %s)%s" % ("CAUGHT" if caught[m[0]] == a.repeat else "MISSED", m[0], caught[m[0]], a.repeat, m[1],
                                           "" if m[0] not in detail else "  -> " + detail[m[0]]))
    n_ok = sum(1 for m in muts if caught[m[0]] == a.repeat)
    good = n_ok == len(muts) and (a.only or ctl == a.repeat)
    print("TAPE SCORING MUTANTS %s (%d/%d caught x%d, %s controls)" % ("PASS" if good else "FAIL", n_ok, len(muts), a.repeat,
                                                                      "n/a" if a.only else "%d/%d" % (ctl, a.repeat)))
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
