#!/usr/bin/env python3
"""Tape scoring guards (docs/tape/scoring_plan.md section 2): planted truth, every guard able to fail.

  python tests/test_tape_scoring.py [--root DIR] [--only GUARD[,GUARD]]

--root runs the guards against another copy of the tree (tests/tape_scoring_mutants.py uses it).
No database, no network, no .env. The scorer runs ONLY on fixtures built here (tests/tape_scoring/gen_fixture.py).
Rule 23 (CLAUDE.md): refuses an unlimited `ulimit -v` where `resource` exists, and Mon-Fri 08:30-15:45 IST unless
TAPE_RULE23_OVERRIDE_R1=1 (operator ruling R-1, 2026-11-03: Local machine, not the retail box).
Beliefs are stated in the comments before they are measured; an expected number is never read off a run.
"""
import argparse
import ast
import contextlib
import io
import itertools
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timedelta, timezone
from fractions import Fraction

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument("--only", default=None)
ARGS = ap.parse_args()
ROOT = os.path.abspath(ARGS.root)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests", "tape_scoring"))
IST = timezone(timedelta(hours=5, minutes=30))


def rule23():
    try:
        import resource
        if resource.getrlimit(resource.RLIMIT_AS)[0] == resource.RLIM_INFINITY:
            print("REFUSED: rule 23 - run under ( ulimit -v 2000000; ... )")
            return 2
    except ImportError:
        pass
    now = datetime.now(IST)
    if now.weekday() < 5 and 830 <= now.hour * 100 + now.minute < 1545:
        if os.environ.get("TAPE_RULE23_OVERRIDE_R1") == "1":
            print("RULE23 WINDOW LIFTED by operator ruling R-1 (2026-11-03): Local machine, not the retail box")
            return 0
        print("REFUSED: rule 23 - fixture tests blocked 08:30-15:45 IST on weekdays (Local: set TAPE_RULE23_OVERRIDE_R1=1)")
        return 2
    return 0


if rule23():
    sys.exit(2)

import gen_fixture as G  # noqa: E402

IMPORT_ERR = None
try:
    from services.tape_scoring import score, wilcoxon  # noqa: E402
except Exception as exc:  # a mutant that breaks the import must fail guards, not crash the runner
    IMPORT_ERR = repr(exc)
    score = wilcoxon = None

PKG = "services/tape_scoring"
SQL = os.path.join(ROOT, "services", "tape_scoring", "scoring_extract.sql")
TMP = []
D1, D2 = "2026-10-05", "2026-10-06"


def tmpdir():
    d = tempfile.mkdtemp(prefix="tape_score_")
    TMP.append(d)
    return d


def src(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def build(ds, truth=True, manifest=False):
    return ds.write(tmpdir(), SQL, truth={"fixture": True} if truth else None, manifest=manifest)


def run1(*plans):
    ds = G.Dataset()
    for p in plans:
        ds.add(p)
    keep = {}
    res = score.run(build(ds), keep)
    return res, keep


def dump(res):
    return json.dumps(score.jsonable(res), sort_keys=True)


def nifty(res):
    return res["symbols"]["NIFTY"]


def ok(cond, msg):
    return (bool(cond), msg)


# ====================================================================== guards (each returns [(ok, message)])

def g_sign_only():
    def plan(gs, gam):
        p = G.Plan("NIFTY", D1, gex_scale=gs, gamma_scale=gam)
        for i, g in enumerate(range(600, 840, 30)):
            p.add_run(g, 21, U=1 if i < 5 else -1, S=1 if i % 2 == 0 else -1, rng=30 + 5 * i)
        return p
    a, _ = run1(plan(1, 1))
    b, _ = run1(plan(1000, 1000))
    c, _ = run1(plan(1000, 1))
    d, _ = run1(plan(1, 1000))
    pop = nifty(a)["H_A"]["population_cycles"]
    return [ok(pop == 8, "base run is non-empty: 8 planted cycles reach the H-A population (got %s)" % pop),
            ok(dump(a) == dump(b), "gex_cr and gamma x1000: every output byte-identical"),
            ok(dump(a) == dump(c), "gex_cr x1000 alone: byte-identical"),
            ok(dump(a) == dump(d), "gamma x1000 alone: byte-identical")]


def g_s_definition():
    p = G.Plan("NIFTY", D1)
    plan = [(600, 1, 51), (630, -1, 51), (660, 1, 49), (690, -1, 49), (720, 1, 50)]
    for G_, S, sh in plan:
        p.add_run(G_, 21, U=1, S=S, share=sh)
    _, keep = run1(p)
    got = {c["G"]: c["S"] for c in keep["acc"]["NIFTY"][D1]["cycles"]}
    want = {600: 1, 630: -1, 660: None, 690: None, 720: 1}
    return [ok(got == want, "S equals the planted sign at 51 %% and 50 %%, undefined at 49 %% (got %s want %s)" % (got, want))]


def g_clock():
    p = G.Plan("NIFTY", D1)
    for G_ in (560, 595, 600, 650, 800, 885, 890, 900):
        p.add_run(G_, 21, U=1, S=1, rng=20)
    res, _ = run1(p)
    h = nifty(res)["H_A"]
    sec = h["secondary"]["agreement_all_cycles_ge_10"]
    return [ok(h["population_cycles"] == 4, "H-A population is the 4 cycles in 10:00..14:45 (got %s)" % h["population_cycles"]),
            ok(h["population_G_min"] == 600 and h["population_G_max"] == 885,
               "population G range 600..885 (got %s..%s)" % (h["population_G_min"], h["population_G_max"])),
            ok(sec["n"] == 6, "secondary agreement keeps the 2 late cycles (>= 10:00) and drops the 2 open ones: n=6 (got %s)" % sec["n"])]


def g_delta():
    p1 = G.Plan("NIFTY", D1)
    for G_, rng, S in ((600, 20, 1), (630, 40, -1), (660, 30, 1), (690, 50, -1), (720, 100, 1), (750, 60, -1)):
        p1.add_run(G_, 21, U=1, S=S, rng=rng)
    p2 = G.Plan("NIFTY", D2)
    for G_, rng, S in ((600, 20, 1), (630, 30, 1), (660, 40, -1), (690, 50, -1), (720, 60, -1), (750, 70, -1)):
        p2.add_run(G_, 21, U=1, S=S, rng=rng)
    res, _ = run1(p1, p2)
    h = nifty(res)["H_A"]
    # belief: agree R = .2 .3 1.0 (median .3, mean .5), disagree .4 .5 .6 (median = mean = .5) -> median delta 1/5, mean delta 0
    return [ok(h["n_days"] == 1, "day 2 (2 agree cycles) is excluded: 1 qualifying day (got %s)" % h["n_days"]),
            ok(h["median_delta"] == Fraction(1, 5), "per-day delta equals the planted 1/5 exactly (got %s)" % h["median_delta"])]


def _ref_p(d):
    """Independent reference: enumerate all 2^n sign patterns over midranks (n <= 12)."""
    d = [Fraction(x) for x in d if x != 0]
    n = len(d)
    a = sorted(abs(x) for x in d)
    rank = {v: Fraction(sum(i + 1 for i, x in enumerate(a) if x == v), a.count(v)) for v in set(a)}
    r = [rank[abs(x)] for x in d]
    w = sum(ri for ri, x in zip(r, d) if x > 0)
    cnt = sum(1 for s in itertools.product((0, 1), repeat=n) if sum(ri for ri, si in zip(r, s) if si) >= w)
    return Fraction(cnt, 2 ** n), w


def g_wilcoxon():
    A = [Fraction(5, 10), Fraction(12, 10), Fraction(-3, 10), 2, Fraction(9, 10)]
    B = [1, -2, 2, 3, 4, 5]
    C = [0, 1, 2, 3, 4, 5, 6, 7, -8]
    cells = []
    # hand-computed beliefs: A w+=14 p=2/32; B w+=18.5 (midranks) p=4/64; C (zero dropped) w+=28 p=25/256
    for name, d, w, p in (("A n=5", A, Fraction(14), Fraction(1, 16)), ("B n=6 tie", B, Fraction(37, 2), Fraction(1, 16)),
                          ("C n=8 zero", C, Fraction(28), Fraction(25, 256))):
        r = wilcoxon.signed_rank_greater(d)
        cells.append(ok(r["p"] == p and r["w_plus"] == w and r["method"] == "exact",
                        "%s: exact p = %s, W+ = %s (got %s, %s)" % (name, p, w, r["p"], r["w_plus"])))
    cells.append(ok(abs(float(wilcoxon.signed_rank_greater(A)["p"]) - 0.0625) < 1e-9, "A matches to 1e-9"))
    cells.append(ok(wilcoxon.signed_rank_greater([1, 2, 3, 4, 5])["p"] == Fraction(1, 32)
                    and wilcoxon.signed_rank_greater([-1, -2, -3, -4, -5])["p"] == 1,
                    "direction: all-positive p=1/32, all-negative p=1"))
    rnd = random.Random(11)
    bad = 0
    for _ in range(40):
        d = [rnd.randint(-6, 6) for _ in range(rnd.randint(1, 10))]
        want, w = _ref_p(d)
        got = wilcoxon.signed_rank_greater(d)
        if got["p"] != want and not (len([x for x in d if x]) == 0):
            bad += 1
    cells.append(ok(bad == 0, "40 random tied/zeroed cases agree with the brute-force enumeration (%d differ)" % bad))
    return cells


def _dp_p(d):
    """Independent reference for distinct magnitudes: rank i+1, integer DP over W+."""
    mags = sorted(range(len(d)), key=lambda i: abs(d[i]))
    ranks = {i: r + 1 for r, i in enumerate(mags)}
    w = sum(ranks[i] for i in range(len(d)) if d[i] > 0)
    dp = {0: 1}
    for r in range(1, len(d) + 1):
        nd = dict(dp)
        for s, c in dp.items():
            nd[s + r] = nd.get(s + r, 0) + c
        dp = nd
    return Fraction(sum(c for s, c in dp.items() if s >= w), 2 ** len(d))


def g_ha_decision():
    yes = [Fraction(20 + i, 100) for i in range(20)]
    n19 = yes[:19]
    eff9 = [Fraction(9, 100) + Fraction(i, 100000) for i in range(25)]
    rnd = random.Random(7)
    mags = [Fraction(10 + i, 100) for i in range(1, 21)]
    p11 = None
    for _ in range(20000):
        neg = set(rnd.sample(range(20), 5))
        d = [-m if i in neg else m for i, m in enumerate(mags)]
        if Fraction(21, 200) < _dp_p(d) < Fraction(23, 200):
            p11 = d
            break
    cells = [ok(p11 is not None, "a p in (0.105, 0.115) scenario exists among 5-negative sign patterns")]
    pr = _dp_p(p11) if p11 else None
    med = score._median(p11) if p11 else None
    cells.append(ok(p11 and med >= Fraction(1, 10) and Fraction(1, 10) < pr, "p~0.11 scenario: median >= 0.10 and independent p = %s > 0.10 (and < 0.20, the mutant's bar)" % (float(pr) if pr else None)))
    v = score.decide_ha
    cells += [ok(v(yes)["verdict"] == "YES", "n=20, median delta .295, tiny p -> YES"),
              ok(v(n19)["verdict"] == "INSUFFICIENT", "n=19 -> INSUFFICIENT"),
              ok(v(eff9)["verdict"] == "NO", "n=25, median .09, p tiny -> NO (effect)"),
              ok(p11 is not None and v(p11)["verdict"] == "NO", "median >= .10 but p ~ .11 -> NO (p)")]
    cells += [ok(score.combine("YES", "YES") == "YES" and score.combine("NO", "NO") == "NO"
                 and score.combine("YES", "NO") == "MIXED" and score.combine("INSUFFICIENT", "YES") == "MIXED",
                 "YES/YES, NO/NO, YES/NO -> MIXED, INSUFFICIENT/YES -> MIXED")]
    return cells


def _ev_plan(**kw):
    p = G.Plan("NIFTY", D1, **kw)
    p.add_run(630, 21, U=1, S=1)  # 10:30:21 - the reference run for every event after it
    return p


def g_hb_labels():
    p = _ev_plan()
    s, r = p.strikes, p.roles
    T = 650 * 60  # 10:50
    for kind, k, leg, side in (("CONC", r["cw"], "CE", "buy"), ("CONC", r["cw"], "PE", "buy"), ("CONC", r["pw"], "PE", "buy"),
                               ("CONC", r["pw"], "CE", "buy"), ("CONC", r["runner"], "CE", "buy"), ("CONC", r["runner"], "PE", "sell"),
                               ("CONC", s[0], "CE", "buy"), ("THIN", r["cw"], "CE", "ask"), ("THIN", r["cw"], "CE", "bid"),
                               ("THIN", r["pw"], "PE", "ask"), ("THIN", r["pw"], "PE", "bid"), ("THIN", r["pw"], "CE", "ask")):
        p.add_tape(T, kind, k, leg, side)
    p.add_tape(590 * 60, "CONC", r["cw"], "CE", "buy")  # 09:50: before 10:00, excluded
    res, _ = run1(p)
    L = nifty(res)["tape_labels"]
    want = {"T1": 2, "T2": 2, "T3": 2, "conc_unlabelled": 3, "thin_unlabelled": 3}
    return [ok(L == want, "labels %s (got %s)" % (want, L)),
            ok(nifty(res)["counts"].get("tape_events_before_10") == 1, "the 09:50 event is excluded and counted")]


def g_hb_match_kinds():
    p = _ev_plan()
    r = p.roles
    p.add_chain(660, 0, "E1", r["cw"])        # 11:00  E1 at cw, only a T3 (THIN ask CE at cw) 10 minutes before
    p.add_tape(650 * 60, "THIN", r["cw"], "CE", "ask")
    p.add_chain(720, 0, "E2-call", r["cw"])   # 12:00  E2 at cw, T3 10 minutes before -> covered
    p.add_tape(710 * 60, "THIN", r["cw"], "CE", "ask")
    p.add_chain(780, 0, "E1", r["runner"])    # 13:00  E1 at the runner-up, T2 10 minutes before -> covered
    p.add_tape(770 * 60, "CONC", r["runner"], "CE", "buy")
    res, _ = run1(p)
    h = nifty(res)["H_B"]
    return [ok(h["n_events"] == 3, "3 events (got %s)" % h["n_events"]),
            ok(h["coverage"] == Fraction(2, 3), "E1 does not match T3, E2 does; E1 matches T2: coverage 2/3 (got %s)" % h["coverage"]),
            ok(h["median_lead_min"] == 10, "median lead 10 (got %s)" % h["median_lead_min"])]


def g_hb_lead_nearest():
    p = _ev_plan()
    r = p.roles
    p.add_chain(720, 0, "E2-call", r["cw"])  # 12:00:00
    for m in (660, 670, 700, 725):            # T-60 (excluded: window is open at T-60), T-50, T-20, T+5 (after T)
        p.add_tape(m * 60, "CONC", r["cw"], "CE", "buy")
    res, _ = run1(p)
    h = nifty(res)["H_B"]
    return [ok(h["n_events"] == 1 and h["coverage"] == 1, "one covered event"),
            ok(h["median_lead_min"] == 20, "lead equals the nearer planted event, 20 min, not the earlier 50 or 60 (got %s)" % h["median_lead_min"])]


def g_hb_window():
    p = _ev_plan()
    p.unsub.add(p.strikes[11])
    r = p.roles
    p.add_chain(660, 0, "E2-call", r["cw"])
    p.add_chain(670, 0, "E2-call", p.strikes[11])
    p.add_tape(650 * 60, "CONC", r["cw"], "CE", "buy")
    res, _ = run1(p)
    n = nifty(res)
    return [ok(n["H_B"]["n_events"] == 1, "only the in-window event is scored (got %s)" % n["H_B"]["n_events"]),
            ok(n["counts"].get("chain_events_outside_window") == 1, "the out-of-window event is counted: %s" % n["counts"])]


_CACHE = {}


def omni(null=False, ndays=22):
    key = (null, ndays)
    if key not in _CACHE:
        d = tmpdir()
        G.omnibus(null=null, ndays=ndays).write(d, SQL, truth={"fixture": True})
        _CACHE[key] = score.run(d)
    return _CACHE[key]


def g_hb_null():
    cells = []
    a, b = omni(True, 6), score.run(build(G.omnibus(True, 6), True))
    cells.append(ok(dump(a) == dump(b), "two runs on one input: byte-identical (seeded from the sha256 of score.py)"))
    pl, nl = omni(False), omni(True)
    for s in ("NIFTY", "SENSEX"):
        h = pl["symbols"][s]["H_B"]
        cells.append(ok(h["null_draws_evaluated"] == h["n_events"] * 100,
                        "%s: 100 draws evaluated per event (%s = %s x 100)" % (s, h["null_draws_evaluated"], h["n_events"])))
        cells.append(ok(h["coverage"] > h["null95_coverage"] and h["median_lead_min"] > h["null95_lead_min"],
                        "%s planted: coverage %s > null95 %s and lead %s > null95 %s" % (
                            s, float(h["coverage"]), float(h["null95_coverage"]), float(h["median_lead_min"]), float(h["null95_lead_min"]))))
        hn = nl["symbols"][s]["H_B"]
        cells.append(ok(hn["verdict"] == "NO" and any("null95" in x for x in hn["no_reasons"]),
                        "%s --null fixture: NO, and a null clause fired (%s)" % (s, hn["no_reasons"])))
    return cells


def g_hb_decision():
    d = score.decide_hb
    F = Fraction
    return [ok(d(299, 20, F(4, 5), F(20), F(1, 10), F(3))[0] == "INSUFFICIENT", "299 events -> INSUFFICIENT"),
            ok(d(400, 14, F(4, 5), F(20), F(1, 10), F(3))[0] == "INSUFFICIENT", "14 non-quarantined days -> INSUFFICIENT"),
            ok(d(300, 15, F(4, 5), F(12), F(1, 5), F(4))[0] == "YES", "300 events, 15 days, 80 %, 12 min over a low null -> YES"),
            ok(d(300, 15, F(4, 5), F(10), F(1, 5), F(4))[0] == "YES", "lead exactly 10 -> YES"),
            ok(d(300, 15, F(4, 5), F(5), F(1, 5), F(4))[0] == "NO", "lead 5.0 -> NO"),
            ok(d(300, 15, F(4, 5), F(7), F(1, 5), F(4))[0] == "MARGINAL", "lead 7 -> MARGINAL, not YES"),
            ok(d(300, 15, F(49, 100), F(12), F(1, 5), F(4))[0] == "NO", "coverage 49 % -> NO"),
            ok(d(300, 15, F(3, 5), F(12), F(3, 5), F(4))[0] == "NO", "coverage == null95 -> NO"),
            ok(d(300, 15, F(4, 5), F(12), F(1, 5), F(12))[0] == "NO", "lead == null95 -> NO")]


def g_quarantine():
    plans = [G.Plan("NIFTY", "2026-10-05", minutes=356),
             G.Plan("NIFTY", "2026-10-06", minutes=357),
             G.Plan("NIFTY", "2026-10-07", late_share="49.9"),
             G.Plan("NIFTY", "2026-10-08", late_share="50.0"),
             G.Plan("NIFTY", "2026-10-09", restart_at=660),
             G.Plan("NIFTY", "2026-10-12", restart_at=535),
             G.Plan("NIFTY", "2026-10-13", daily_report=False),
             G.Plan("NIFTY", "2026-10-14")]
    res, _ = run1(*plans)
    q = res["quarantine"]["NIFTY"]
    want = {"2026-10-05": ["COMPLETENESS"], "2026-10-07": ["LATE_SHARE"], "2026-10-09": ["TOKEN_RESTART"],
            "2026-10-13": ["UNVERIFIABLE"]}
    kept = nifty(res)["non_quarantined_days"]
    wk = ["2026-10-06", "2026-10-08", "2026-10-12", "2026-10-14"]
    return [ok(q == want, "excluded days with reasons: %s (got %s)" % (want, q)),
            ok(kept == wk, "kept: 357/375 minutes (95.2 %%), share 50.0, pre-open restart, clean day (got %s)" % kept)]


def g_no_remerge():
    p = _ev_plan()
    r = p.roles
    p.add_chain(720, 0, "E2-call", r["cw"], merged_n=3)
    p.add_chain(725, 0, "E2-call", r["cw"], merged_n=1)
    res, _ = run1(p)
    h = nifty(res)["H_B"]
    return [ok(h["n_events"] == 2 and h["by_kind"]["E2-call"] == 2, "two counted events 5 min apart at one K stay two (got %s)" % h["n_events"])]


# ---- gates, in a copy of the package so ledgers and tamper edits never touch the tree under test

def _sha(p):
    import hashlib
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def make_tree():
    t = tmpdir()
    os.makedirs(os.path.join(t, "services", "tape_scoring"))
    os.makedirs(os.path.join(t, "docs", "tape"))
    shutil.copy(os.path.join(ROOT, "services", "__init__.py"), os.path.join(t, "services", "__init__.py"))
    names = ("__init__.py", "scoring_extract.sql", "run_extract.sh", "score.py", "wilcoxon.py")
    for n in names:
        shutil.copy(os.path.join(ROOT, "services", "tape_scoring", n), os.path.join(t, "services", "tape_scoring", n))
    with open(os.path.join(t, "docs", "tape", "scoring_hashes.md"), "w", encoding="utf-8", newline="\n") as fh:
        for n in ("scoring_extract.sql", "run_extract.sh", "score.py", "wilcoxon.py"):
            fh.write("| services/tape_scoring/%s | %s |\n" % (n, _sha(os.path.join(t, "services", "tape_scoring", n))))
    return t


def real_dataset(n_expiry=6):
    ds = G.Dataset()
    for i in range(n_expiry):
        day = (datetime(2026, 10, 5) + timedelta(days=i)).strftime("%Y-%m-%d")
        for sym in ("NIFTY", "SENSEX"):
            ds.add(G.Plan(sym, day, expiry=day)).add_run(855, 21, U=1, S=1, rng=20)
    return build(ds, truth=False, manifest=True)


def score_cli(tree, inputs, out, *extra):
    env = dict(os.environ, PYTHONPATH=tree, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, "-m", "services.tape_scoring.score", "--inputs", inputs, "--out", out] + list(extra),
                       cwd=tree, env=env, capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout + p.stderr


def g_run_once():
    inp = real_dataset(6)
    t = make_tree()
    o1, o2 = tmpdir(), tmpdir()
    r1 = score_cli(t, inp, o1)
    r2 = score_cli(t, inp, o1)
    r2b = score_cli(t, inp, o2)
    r3 = score_cli(t, inp, o1, "--rerun-defect", "defect in the code: planted for the guard")
    r4 = score_cli(t, inp, o1, "--rerun-defect", "another")
    led = json.load(open(os.path.join(o1, "scoring_runs.json"), encoding="utf-8")) if os.path.exists(os.path.join(o1, "scoring_runs.json")) else {"runs": []}
    t2 = make_tree()
    r5 = score_cli(t2, real_dataset(3), tmpdir())
    return [ok(r1[0] == 0, "first real run on the input passes the gates (rc %s: %s)" % (r1[0], r1[1].strip().splitlines()[-1:])),
            ok(r2[0] == 4, "second run, same --out, refused (rc %s)" % r2[0]),
            ok(r2b[0] == 4, "second run with a NEW --out also refused: the fixed ledger holds it (rc %s)" % r2b[0]),
            ok(r3[0] == 0 and len(led["runs"]) == 2 and "defect in the code" in (led["runs"][-1].get("rerun_defect") or ""),
               "--rerun-defect permits one re-run and records the text (rc %s, ledger %d)" % (r3[0], len(led["runs"]))),
            ok(r4[0] == 4, "a third run refused even with --rerun-defect (rc %s)" % r4[0]),
            ok(r5[0] == 6 and "NOT MET" in r5[1], "trigger unmet (3 expiries, 3 days): refused (rc %s)" % r5[0])]


def g_hash_check():
    inp = real_dataset(6)
    cells = []
    t = make_tree()
    rc, out = score_cli(t, inp, tmpdir())
    cells.append(ok(rc == 0, "control: untouched tree passes the hash check (rc %s)" % rc))
    for n in ("score.py", "wilcoxon.py", "scoring_extract.sql", "run_extract.sh"):
        t = make_tree()
        with open(os.path.join(t, "services", "tape_scoring", n), "ab") as fh:
            fh.write(b"\n")
        rc, out = score_cli(t, inp, tmpdir())
        cells.append(ok(rc == 3 and "HASH MISMATCH" in out and n in out, "one byte added to %s: refused with the diff (rc %s)" % (n, rc)))
    return cells


def g_extract_pure():
    cells = []
    text = src(PKG + "/scoring_extract.sql")
    body = "\n".join(ln for ln in text.splitlines() if not ln.strip().startswith("--"))
    stmts = [" ".join(s.split()) for s in body.split(";") if s.strip()]
    rx = re.compile(r"^SELECT ([a-z0-9_]+(?:, [a-z0-9_]+)*) FROM public\.([a-z0-9_]+) WHERE (.+)$")
    bad_kw = re.compile(r"\b(JOIN|UNION|GROUP|HAVING|OVER|WITH|DISTINCT|LIMIT|ORDER|SUM|COUNT|AVG|MIN|MAX|CASE|FILTER|INTO|EXCEPT|"
                        r"INTERSECT|LATERAL|COALESCE|CAST|EXTRACT|DATE_TRUNC)\b", re.I)
    rels, problems = [], []
    for s in stmts:
        m = rx.match(s)
        if not m:
            problems.append("not a plain SELECT ... FROM public.x WHERE ...: " + s[:80])
            continue
        cols, rel, where = m.groups()
        if bad_kw.search(s) or s.upper().count("SELECT") != 1:
            problems.append("forbidden construct in " + rel)
        w = re.sub(r"'[^']*'", "''", where)
        if re.search(r"[+*/%|]|\s-\s|\w\(", w):
            problems.append("arithmetic or a function call in the WHERE of " + rel)
        rels.append((rel, [c.strip() for c in cols.split(",")]))
    cells.append(ok(not problems, "every statement is a plain SELECT with fixed filters (%s)" % (problems or "10 statements")))
    named = sorted(r for r, _ in rels)
    cells.append(ok(named == sorted(list(score.COLS) + ["tape_daily_report"]),
                    "relations named = the nine in the plan (+ the day list from tape_daily_report): %s" % named))
    for rel, cols in rels:
        if (rel, cols) == ("tape_daily_report", ["trading_day", "symbol"]):
            continue
        cells.append(ok(cols == list(score.COLS[rel]), "%s: select list == the columns score.py reads" % rel))
    sh = "\n".join(ln for ln in src(PKG + "/run_extract.sh").splitlines() if not ln.strip().startswith("#"))
    cells.append(ok(not re.search(r"\b(INSERT|UPDATE|DELETE|TRUNCATE|DROP|ALTER|CREATE|GRANT|REVOKE|COPY)\b", sh, re.I)
                    and ".env" not in sh and "psql" not in sh,
                    "run_extract.sh: no write verb, no .env, no direct psql (everything goes through roq.sh)"))
    return cells


def _imports(path):
    tree = ast.parse(src(path))
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out += [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom):
            out.append(("." * n.level) + (n.module or ""))
    return out


def g_isolated():
    cells = []
    net = {"socket", "urllib", "http", "requests", "ssl", "ftplib", "smtplib", "dotenv", "supabase", "boto3", "psycopg2"}
    for f in ("score.py", "wilcoxon.py", "__init__.py"):
        bad = [m for m in _imports(PKG + "/" + f)
               if m.split(".")[0] not in sys.stdlib_module_names and not m.startswith("services.tape_scoring")]
        bad += [m for m in _imports(PKG + "/" + f) if m.split(".")[0] in net]
        cells.append(ok(not bad, "%s imports stdlib and services.tape_scoring only (offending: %s)" % (f, sorted(set(bad)))))
    code = src(PKG + "/score.py") + src(PKG + "/wilcoxon.py")
    cells.append(ok(not re.search(r"""["']\.env["']|getenv|environ|load_dotenv|core\.config""", code), "no .env, no environment access"))
    runner = ""
    for f in os.listdir(os.path.join(ROOT, "services", "tape_runner")):
        if f.endswith(".py"):
            runner += src("services/tape_runner/" + f)
    cells.append(ok("tape_scoring" not in runner, "nothing in services/tape_runner/ names tape_scoring"))
    inst = src("services/tape_runner/install.sh")
    m = re.search(r'archive HEAD (services/__init__\.py services/tape_runner)\b', inst)
    cells.append(ok(m is not None and "tape_scoring" not in inst, "install.sh archives only services/__init__.py services/tape_runner"))
    cells.append(ok(IMPORT_ERR is None, "the package imports (%s)" % IMPORT_ERR))
    return cells


EXPECTED_PARAMS = {
    "ha_first_G_min": 600, "ha_last_G_min": 885, "cycle_share_min_pct": 50, "min_cycles_per_group": 3, "ha_min_days": 20,
    "ha_min_median_delta": Fraction(1, 10), "ha_p_max": Fraction(1, 10), "r_horizon_min": 30, "r_min_bars": 25,
    "hb_min_events": 300, "hb_min_days": 15, "hb_cov_min": Fraction(1, 2), "hb_lead_yes_min": 10, "hb_lead_no_max": 5,
    "match_window_min": 60, "null_draws": 100, "bootstrap_B": 1000, "null_pctile": 95, "completeness_min_pct": 95,
    "completeness_minutes": 375, "late_share_min_pct": 50, "trigger_expiries": 6, "trigger_days": 30,
    "wilcoxon_normal_above": 60, "spot_clock_min_pct": 95, "passive_side": {"CE": "ask", "PE": "ask"}}


def g_params():
    diff = {k: (score.PARAMS.get(k), v) for k, v in EXPECTED_PARAMS.items() if score.PARAMS.get(k) != v}
    extra = sorted(set(score.PARAMS) - set(EXPECTED_PARAMS))
    return [ok(not diff and not extra, "every pre-registered parameter has its pre-registered value (differ: %s; unlisted: %s)" % (diff, extra)),
            ok(wilcoxon.NORMAL_ABOVE == EXPECTED_PARAMS["wilcoxon_normal_above"], "the Wilcoxon switch point equals the listed parameter"),
            ok(score.MATCH == {"E1": frozenset(("T1", "T2")), "E2-call": frozenset(("T1", "T3")), "E2-put": frozenset(("T1", "T3"))},
               "matching kinds: E1 <- T1/T2, E2 <- T1/T3")]


GUARDS = [("sc-sign-only", g_sign_only), ("ha-s-definition", g_s_definition), ("ha-clock", g_clock), ("ha-delta", g_delta),
          ("ha-wilcoxon", g_wilcoxon), ("ha-decision", g_ha_decision), ("hb-labels", g_hb_labels),
          ("hb-match-kinds", g_hb_match_kinds), ("hb-lead-nearest", g_hb_lead_nearest), ("hb-window", g_hb_window),
          ("hb-null", g_hb_null), ("hb-decision", g_hb_decision), ("sc-quarantine", g_quarantine),
          ("sc-no-remerge", g_no_remerge), ("sc-run-once", g_run_once), ("sc-hash-check", g_hash_check),
          ("sc-extract-pure", g_extract_pure), ("sc-isolated", g_isolated), ("sc-params", g_params)]


# ====================================================================== unit checks (no mutant)

def u_ts_parse():
    p = score.parse_ts
    bad = False
    try:
        p("2026-11-03 10:05:21")
    except ValueError:
        bad = True
    a, b, c, d = p("2026-11-03 10:05:21+00"), p("2026-11-03T10:05:21+05:30"), p("2026-11-03T10:05:21+0530"), p("2026-11-03T04:35:21Z")
    return [ok(a.hour == 15 and a.minute == 35, "+00 renders as 15:35 IST"), ok(b.hour == 10 and b == c, "+05:30 and +0530 agree"),
            ok(d == b, "Z agrees"), ok(p("2026-11-03 10:05:21.250000+05:30").microsecond == 250000, "fractional seconds"),
            ok(bad, "a timestamp without an offset is refused")]


def u_lookahead():
    T = score.parse_ts("2026-11-03T10:05:21+05:30")
    m = 10 * 60 + 5
    bars = {k: (Fraction(100), Fraction(100), Fraction(100)) for k in range(m + 1, m + 31)}
    bars[m] = (Fraction(9999), Fraction(1), Fraction(1))        # the minute that contains T: label <= T, excluded
    bars[m + 31] = (Fraction(9999), Fraction(1), Fraction(1))   # past the horizon: excluded
    bars[m + 2] = (Fraction(130), Fraction(100), Fraction(100))
    r, n = score.spot_range(bars, T)
    short = {k: v for k, v in bars.items() if k <= m + 24}
    r2, n2 = score.spot_range(short, T)
    short25 = {k: v for k, v in bars.items() if k <= m + 25}
    r3, _ = score.spot_range(short25, T)
    return [ok(r == 30 and n == 30, "R reads labels (T, T+30] only: range 30 over 30 bars (got %s over %s)" % (r, n)),
            ok(r2 is None and n2 == 24, "24 of 30 bars -> excluded"), ok(r3 == 30, "25 of 30 bars -> kept")]


def u_label_runs():
    p = G.Plan("NIFTY", D1)
    p.add_run(600, 21, U=1, S=1)                                         # roles A: cw = s8
    p.add_run(630, 21, U=1, S=1, cw=p.strikes[9])                        # roles B: cw = s9
    s8, s9 = p.strikes[8], p.strikes[9]
    p.add_tape(620 * 60, "CONC", s8, "CE", "buy")   # 10:20 -> run A -> T1
    p.add_tape(620 * 60, "CONC", s9, "CE", "buy")   # 10:20 -> still run A (B is not yet) -> none
    p.add_tape(631 * 60, "CONC", s9, "CE", "buy")   # 10:31 -> run B -> T1
    p.add_tape(631 * 60, "CONC", s8, "CE", "buy")   # 10:31 -> run B -> none
    res, _ = run1(p)
    L = nifty(res)["tape_labels"]
    return [ok(L["T1"] == 2 and L["conc_unlabelled"] == 2, "an event is labelled from the latest run at or before it (got %s)" % L)]


def u_lead_after_T():
    p = _ev_plan()
    p.add_chain(720, 0, "E2-call", p.roles["cw"])
    p.add_tape(721 * 60, "CONC", p.roles["cw"], "CE", "buy")
    res, _ = run1(p)
    h = nifty(res)["H_B"]
    return [ok(h["coverage"] == 0 and h["median_lead_min"] is None, "a tape event after T never counts (coverage %s)" % h["coverage"])]


def u_spot_clock():
    p = G.Plan("NIFTY", D1, spot="badclock")
    for g in (600, 630, 660):
        p.add_run(g, 21, U=1, S=1, rng=20)
    res, _ = run1(p)
    c = nifty(res)["counts"]
    return [ok(c.get("cycle_spot_clock_refused") == 3 and nifty(res)["H_A"]["population_cycles"] == 0,
               "IST-clock-as-UTC bars: day refused, 3 cycles excluded and counted (%s)" % c)]


def u_gates_fixture():
    real = real_dataset(2)
    fx = build(G.omnibus(True, 1), truth=True)
    so = io.StringIO()
    with contextlib.redirect_stdout(so):
        a = score.main(["--inputs", real, "--out", tmpdir(), "--fixture"])
        b = score.main(["--inputs", fx, "--out", tmpdir()])
    return [ok(a == 2, "--fixture without FIXTURE_TRUTH.json refused"), ok(b == 2, "a real run on a directory with FIXTURE_TRUTH.json refused")]


def u_manifest():
    d = real_dataset(2)
    clean = score.verify_manifest(d)
    f = os.path.join(d, "tape_minute", "2026-10-05.csv")
    with open(f, "ab") as fh:
        fh.write(b"x")
    return [ok(clean == [], "a written manifest verifies"), ok(any("sha256 differs" in x for x in score.verify_manifest(d)), "a changed CSV is caught")]


def u_median_switch():
    r60 = wilcoxon.signed_rank_greater(list(range(1, 61)))
    r61 = wilcoxon.signed_rank_greater(list(range(1, 62)))
    return [ok(score._median([1, 2, 3, 4]) == Fraction(5, 2) and score._median([3, 1, 2]) == 2, "median of even and odd lists"),
            ok(r60["method"] == "exact" and r61["method"] == "normal" and r61["normal_above"] == 60, "exact at n=60, normal at n=61; switch point reported")]


UNITS = [u_ts_parse, u_lookahead, u_label_runs, u_lead_after_T, u_spot_clock, u_gates_fixture, u_manifest, u_median_switch]


def main():
    only = set(ARGS.only.split(",")) if ARGS.only else None
    results = []
    for name, fn in GUARDS:
        if only and name not in only:
            continue
        try:
            cells = fn()
            good = bool(cells) and all(c[0] for c in cells)
        except Exception:
            cells = [(False, "EXCEPTION " + traceback.format_exc().strip().splitlines()[-1])]
            good = False
        results.append((name, good))
        print("%s %s" % ("PASS" if good else "FAIL", name))
        for c in cells:
            print("    [%s] %s" % ("ok" if c[0] else "XX", c[1]))
    unit_ok = unit_n = 0
    if only is None:
        for fn in UNITS:
            try:
                cells = fn()
            except Exception:
                cells = [(False, "EXCEPTION " + traceback.format_exc().strip().splitlines()[-1])]
            for c in cells:
                unit_n += 1
                unit_ok += bool(c[0])
                print("    unit %s [%s] %s" % (fn.__name__, "ok" if c[0] else "XX", c[1]))
    for d in TMP:
        shutil.rmtree(d, ignore_errors=True)
    g_ok = sum(1 for _, g in results if g)
    passed = bool(results) and g_ok == len(results) and unit_ok == unit_n
    print("TAPE SCORING %s (%d/%d guards, %d/%d unit checks)" % ("PASS" if passed else "FAIL", g_ok, len(results), unit_ok, unit_n))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
