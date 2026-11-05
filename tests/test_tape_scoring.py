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


V02_SHA = "71950f92eb1313f2e58a40772c8671a2beefce220d5222213d39e8a80dfa4800"
V04_SHA = "b45477d36eba6930ab41171a3405c10cf6ecb0bd1fbb04b52d09a5c2129acd57"
HASHED4 = ("scoring_extract.sql", "run_extract.sh", "score.py", "wilcoxon.py")


def make_tree(ledger="v04"):
    """ledger: 'v04' (one v0.4 entry for the current files), 'both' (a v0.2-style block with stale hashes, then the v0.4
    entry, as the real append-only ledger is), 'v02only' (only the stale v0.2 block), 'stale' (a v0.4 entry with stale
    hashes)."""
    t = tmpdir()
    os.makedirs(os.path.join(t, "services", "tape_scoring"))
    os.makedirs(os.path.join(t, "docs", "tape"))
    shutil.copy(os.path.join(ROOT, "services", "__init__.py"), os.path.join(t, "services", "__init__.py"))
    names = ("__init__.py", "scoring_extract.sql", "run_extract.sh", "score.py", "wilcoxon.py")
    for n in names:
        shutil.copy(os.path.join(ROOT, "services", "tape_scoring", n), os.path.join(t, "services", "tape_scoring", n))
    cur = {n: _sha(os.path.join(t, "services", "tape_scoring", n)) for n in HASHED4}
    old = {n: "%064x" % (i + 1) for i, n in enumerate(HASHED4)}
    v02 = "# Tape scoring hash ledger (pre-registration v0.2)\n\nPre-registration v0.2 sha256: `%s`\n\n" % V02_SHA
    v02 += "".join("| services/tape_scoring/%s | %s |\n" % (n, old[n]) for n in HASHED4)
    v04 = lambda h: "\n## Entry test - pre-registration v0.4\nPre-registration v0.4 sha256: `%s`\n\n%s" % (  # noqa: E731
        V04_SHA, "".join("| services/tape_scoring/%s | %s |\n" % (n, h[n]) for n in HASHED4))
    text = {"v04": "# ledger\n" + v04(cur), "both": v02 + v04(cur), "v02only": v02, "stale": "# ledger\n" + v04(old)}[ledger]
    with open(os.path.join(t, "docs", "tape", "scoring_hashes.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
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
    rc, out = score_cli(make_tree("both"), inp, tmpdir())
    cells.append(ok(rc == 0, "ledger with BOTH entries (stale v0.2 first, current v0.4 last): verified against the last, passes (rc %s)" % rc))
    rc, out = score_cli(make_tree("v02only"), inp, tmpdir())
    cells.append(ok(rc == 3 and "HASH MISMATCH" in out, "ledger with only the v0.2 entry: refused (rc %s)" % rc))
    rc, out = score_cli(make_tree("stale"), inp, tmpdir())
    cells.append(ok(rc == 3 and "HASH MISMATCH" in out, "a v0.4 entry listing stale hashes: refused (rc %s)" % rc))
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
    # v0.4: one relation can be read by two named statements (tape_minute and the optional tape_minute_oi), so each
    # statement is identified by its "-- @name" tag, not by its FROM.
    tagged = re.findall(r"--\s*@name\s+(\w+)\s*\n(.*?);", text, re.S)
    stmts = [(n, " ".join("\n".join(ln for ln in b.splitlines() if not ln.strip().startswith("--")).split())) for n, b in tagged]
    rx = re.compile(r"^SELECT ([a-z0-9_]+(?:, [a-z0-9_]+)*) FROM public\.([a-z0-9_]+) WHERE (.+)$")
    bad_kw = re.compile(r"\b(JOIN|UNION|GROUP|HAVING|OVER|WITH|DISTINCT|LIMIT|ORDER|SUM|COUNT|AVG|MIN|MAX|CASE|FILTER|INTO|EXCEPT|"
                        r"INTERSECT|LATERAL|COALESCE|CAST|EXTRACT|DATE_TRUNC)\b", re.I)
    rels, problems = [], []
    for name, s in stmts:
        m = rx.match(s)
        if not m:
            problems.append("not a plain SELECT ... FROM public.x WHERE ...: " + s[:80])
            continue
        cols, table, where = m.groups()
        rel = name
        if table != (name if name != "tape_minute_oi" else "tape_minute") and name != "days_list":
            problems.append("%s reads public.%s" % (name, table))
        if bad_kw.search(s) or s.upper().count("SELECT") != 1:
            problems.append("forbidden construct in " + rel)
        w = re.sub(r"'[^']*'", "''", where)
        if re.search(r"[+*/%|]|\s-\s|\w\(", w):
            problems.append("arithmetic or a function call in the WHERE of " + rel)
        rels.append((rel, [c.strip() for c in cols.split(",")]))
    cells.append(ok(not problems and len(stmts) == 11, "every statement is a plain SELECT with fixed filters (%s; %d statements)" % (
        problems or "ok", len(stmts))))
    named = sorted(r for r, _ in rels)
    cells.append(ok(named == sorted(list(score.COLS) + ["days_list"]),
                    "statements named = the nine relations + the optional tape_minute_oi + the day list: %s" % named))
    cells.append(ok(stmts and stmts[-1][0] == "tape_minute_oi", "the optional tape_minute_oi statement is last in the file"))
    for rel, cols in rels:
        if rel == "days_list":
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
    "wilcoxon_normal_above": 60, "spot_clock_min_pct": 95, "passive_side": {"CE": "ask", "PE": "ask"},
    # v0.4 section 1 definitions (not section 5 thresholds) and the section 5 E2 OI literal the T4 descriptive reuses
    "s_window_min": 30, "s_window_bins": 6, "e2_oi_move_pct": 5}


def g_params():
    diff = {k: (score.PARAMS.get(k), v) for k, v in EXPECTED_PARAMS.items() if score.PARAMS.get(k) != v}
    extra = sorted(set(score.PARAMS) - set(EXPECTED_PARAMS))
    return [ok(not diff and not extra, "every pre-registered parameter has its pre-registered value (differ: %s; unlisted: %s)" % (diff, extra)),
            ok(wilcoxon.NORMAL_ABOVE == EXPECTED_PARAMS["wilcoxon_normal_above"], "the Wilcoxon switch point equals the listed parameter"),
            ok(score.MATCH == {"E1": frozenset(("T1", "T2")), "E2-call": frozenset(("T1", "T3")), "E2-put": frozenset(("T1", "T3"))},
               "matching kinds: E1 <- T1/T2, E2 <- T1/T3 (no T4)"),
            ok(score.PARAMS["s_window_min"] == 5 * score.PARAMS["s_window_bins"] and score.window_stamps(700) == [700, 695, 690, 685, 680, 675],
               "the S window is six 5-minute stamps G..G-25 = 30 minutes"),
            ok(score.PREREG_SHA == V04_SHA, "score.py names pre-registration v0.4")]


def g_r_window():
    """v0.4 section 1 / 6: R over bars labelled hm(T)..hm(T)+29, the 15:29 bar never in a range. Beliefs (computed here from
    the planted spikes, straddle 100): G=600 spike at T -> 40/100; G=640 spike at T+30 -> 0; G=700 spike at T+29 -> 25/100;
    G=900 spike 10 at T+5 and 500 on the 15:29 bar -> 10/100; day 2 G=900: 24 regular bars + 15:29 -> excluded."""
    p = G.Plan("NIFTY", D1, high_1529=500)
    plant = {600: (40, 0), 640: (50, 30), 700: (25, 29), 900: (10, 5)}
    for g, (rng, at) in plant.items():
        p.add_run(g, 21, U=1, S=1, rng=rng, rng_at=at)
    want = {g: (Fraction(rng, 100) if at <= 29 else Fraction(0)) for g, (rng, at) in plant.items()}
    q = G.Plan("NIFTY", D2)
    q.add_run(900, 21, U=1, S=1, rng=10, rng_at=10)
    q.drop.update(range(900, 905))            # 905..928 = 24 regular bars, plus the 15:29 bar
    res, keep = run1(p, q)
    got = {c["G"]: c["R"] for c in keep["acc"]["NIFTY"][D1]["cycles"]}
    got2 = {c["G"]: c["R"] for c in keep["acc"]["NIFTY"][D2]["cycles"]}
    return [ok(got[600] == want[600], "extreme in the bar labelled T is included: R = %s (got %s)" % (want[600], got[600])),
            ok(got[640] == want[640], "extreme in the bar labelled T+30 is excluded: R = 0 (got %s)" % got[640]),
            ok(got[700] == want[700], "extreme in the bar labelled T+29 is included: R = %s (got %s)" % (want[700], got[700])),
            ok(got[900] == want[900], "the 15:29 extreme is excluded: R = %s, not %s (got %s)" % (want[900], Fraction(510, 100), got[900])),
            ok(got2[900] is None and nifty(res)["counts"].get("cycle_r_bars_lt_min") == 1,
               "24 regular bars + the 15:29 bar: excluded and counted (got R %s, counts %s)" % (got2[900], nifty(res)["counts"].get("cycle_r_bars_lt_min")))]


def g_s_window():
    """v0.4 section 1: S = sign of D30 over the six bins stamped G-25..G. Planted (U = 1 everywhere, gamma equal at every strike,
    so S = -sign(sum of buy - sell)): 600 S=+1 with S_cum=-1; 630 S=-1 with S_cum=+1; 660 +1; 690 six bins net -2000 (S +1)
    but the last five net +1000 (S -1); 720 a strike present at 4 of 6 stamps carries net -1500, the designated leg +500 ->
    S +1 (dropping the partial strike would give -1); 750 window share 49 % (cum 60 %) -> undefined; 780 window 51 % (cum 40 %)
    -> +1; 810 window net 0 -> undefined, d_zero."""
    p = G.Plan("NIFTY", D1)
    k0, k1 = p.strikes[0], p.strikes[1]
    p.add_run(600, 21, U=1, S=1, S_cum=-1)
    p.add_run(630, 21, U=1, S=-1, S_cum=1)
    p.add_run(660, 21, U=1, S=1)
    p.add_run(690, 21, U=1, bins=[(25, k0, "CE", 0, 3000, 0), (0, k0, "CE", 1000, 0, 0)])
    p.partial[k1] = {705, 710, 715, 720}
    p.add_run(720, 21, U=1, bins=[(0, k0, "CE", 500, 0, 0), (10, k1, "CE", 0, 1500, 0)])
    p.add_run(750, 21, U=1, S=1, share=49, share_cum=60)
    p.add_run(780, 21, U=1, S=1, share=51, share_cum=40)
    p.add_run(810, 21, U=1, bins=[(0, k0, "CE", 500, 500, 0)])
    nets = {690: 1000 - 3000, 720: 500 - 1500}
    want = {600: 1, 630: -1, 660: 1, 690: -(nets[690] > 0) + (nets[690] < 0), 720: -(nets[720] > 0) + (nets[720] < 0),
            750: None, 780: 1, 810: None}
    cum = {600: -1, 630: 1}
    res, keep = run1(p)
    got = {c["G"]: c["S"] for c in keep["acc"]["NIFTY"][D1]["cycles"]}
    c = nifty(res)["counts"]
    seq = [want[g] for g in sorted(want) if want[g] is not None]
    changes = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    dsc = res["descriptive"]["NIFTY"]["s_sign_changes_1000_1445"].get(D1)
    return [ok(got == want, "S equals the planted trailing-30 sign on every cycle (got %s want %s)" % (got, want)),
            ok(all(got[g] != cum[g] for g in cum), "and differs from the planted cumulative sign on the chosen cycles %s" % sorted(cum)),
            ok(got[690] == 1, "six bins, not five: the bin stamped G-25 decides 690 (got %s)" % got[690]),
            ok(got[720] == 1, "a strike with 4 of 6 bins contributes the bins present (got %s)" % got[720]),
            ok(got[750] is None and got[780] == 1, "share on the six-bin window volume: 49 %% undefined, 51 %% defined (got %s, %s)" % (got[750], got[780])),
            ok(c.get("cycle_s_undefined_d_zero") == 1 and c.get("cycle_s_undefined_share_below_min") == 1,
               "d_zero and share-below-min counted once each (%s)" % {k: v for k, v in c.items() if "undefined" in k}),
            ok(dsc == changes, "descriptive sign changes in 10:00-14:45 = %d (got %s)" % (changes, dsc))]


def _label_plan():
    p = _ev_plan()
    r = p.roles
    p.add_chain(660, 0, "E1", r["runner"])          # 11:00 <- T2 (CONC CE at the runner-up) at 10:50: lead 10
    p.add_tape(650 * 60, "CONC", r["runner"], "CE", "buy")
    p.add_chain(720, 0, "E2-call", r["cw"])         # 12:00 <- T1 (CONC CE at the call wall) at 11:50: lead 10
    p.add_tape(710 * 60, "CONC", r["cw"], "CE", "buy")
    p.add_chain(780, 0, "E2-put", r["pw"])          # 13:00 <- T3 (THIN ask PE at the put wall) at 12:40: lead 20
    p.add_tape(760 * 60, "THIN", r["pw"], "PE", "ask")
    p.add_chain(840, 0, "E2-call", r["cw"])         # 14:00 uncovered
    return p


def g_hb_per_label():
    res, _ = run1(_label_plan())
    h = nifty(res)["H_B"]
    d = res["descriptive"]["NIFTY"]["hb_by_label"]
    att = d["attribution"]
    covered = round(h["coverage"] * h["n_events"])
    want = {"T1": (1, 10), "T2": (1, 10), "T3": (1, 20)}
    gotc = {k: (v["covered"], v["median_lead_min"]) for k, v in att.items()}
    return [ok(h["n_events"] == 4 and covered == 3, "pooled: 4 events, 3 covered (got %s, %s)" % (h["n_events"], covered)),
            ok(d["attribution_covered_total"] == covered and sum(v["covered"] for v in att.values()) == covered,
               "per-label attribution sums to the pooled covered count %d (got %s)" % (covered, d["attribution_covered_total"])),
            ok(gotc == want, "each covered event is attributed to its planted label with its planted lead %s (got %s)" % (want, gotc)),
            ok(d["any_label"]["T3"]["events"] == 3 and d["any_label"]["T3"]["covered"] == 1,
               "any-label T3: admitted by the 3 E2 events, covers 1 (got %s)" % d["any_label"]["T3"])]


def _t4_plan():
    p = _ev_plan()
    r = p.roles
    p.add_chain(720, 0, "E2-call", r["cw"])         # 12:00:00
    p.add_tape(710 * 60, "CONC", r["cw"], "CE", "buy")   # T1 at 11:50 -> H-B lead 10
    p.add_oi(r["cw"], "CE", 713, 1000)              # base: the latest minute labelled < 11:55
    p.add_oi(r["cw"], "CE", 718, 1060)              # +6 % in minute 11:58 -> T4 stamped 11:59:00 -> lead 1
    return p


def g_hb_t4_separate():
    res, _ = run1(_t4_plan())
    h = nifty(res)["H_B"]
    t4 = res["descriptive"]["NIFTY"]["t4"]
    return [ok(h["coverage"] == 1 and h["median_lead_min"] == 10, "H-B lead is the T1's 10 min, not the T4's 1 (got %s)" % h["median_lead_min"]),
            ok(isinstance(t4, dict) and t4["coverage"] == 1 and t4["median_lead_min"] == 1 and t4["e2_events"] == 1,
               "T4 lead 1 min, coverage 1/1, reported under descriptive only (got %s)" % t4),
            ok(all("T4" not in v for v in score.MATCH.values()), "T4 is in no matching set")]


def _strip_desc(res):
    r = json.loads(dump(res))
    r.pop("descriptive", None)
    return json.dumps(r, sort_keys=True)


def g_descriptive_isolated():
    d = build(_build_ds(_label_plan(), _t4_plan_day2()))
    a = score.run(d)
    real = score.descriptive
    try:
        score.descriptive = lambda acc: {}
        b = score.run(d)
    finally:
        score.descriptive = real
    # walls outside the window (v0.4 section 1, reporting only): the call wall strike unsubscribed on day 3. Belief, computed
    # from the generator's planted gex_cr (U/100 per strike, U/2 leader, U/4 runner-up; 12 strikes): share inside =
    # (total - |gex at cw|) / total.
    w = G.Plan("NIFTY", "2026-10-07", unsub=())
    w.unsub.add(w.roles["cw"])
    for g in (600, 630):
        w.add_run(g, 21, U=1, S=1)
    tot = Fraction(10, 100) + Fraction(1, 2) + Fraction(1, 4)
    want_share = (tot - Fraction(1, 100)) / tot
    rw, _ = run1(w)
    cov = rw["descriptive"]["NIFTY"]["window_coverage_per_day"]["2026-10-07"]
    return [ok(a["descriptive"] and b["descriptive"] == {}, "control: the descriptive block was built, and the patched run built none"),
            ok(_strip_desc(a) == _strip_desc(b), "with the descriptive block replaced by {}, every verdict and figure is byte-identical"),
            ok(cov["call_wall_in_window_frac"] == 0 and cov["put_wall_in_window_frac"] == 1 and cov["gexabs_share_in_window_median"] == want_share,
               "call wall outside the window: in-window fraction 0, put wall 1, |gex| share %s (got %s)" % (want_share, cov))]


def _build_ds(*plans):
    ds = G.Dataset()
    for p in plans:
        ds.add(p)
    return ds


def _t4_plan_day2():
    p = _t4_plan()
    p.day = D2
    return p


def _fake_roq(d):
    py = os.path.join(d, "fake_roq.py")
    with open(py, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(
            "import os, re, sys\n"
            "q = [ln for ln in sys.stdin.read().splitlines() if ln.strip() and not ln.startswith(chr(92))]\n"
            "sql = ' '.join(q)\n"
            "fail = os.environ.get('FAKE_FAIL', '')\n"
            "m = re.search(r'SELECT (.*?) FROM public\\.(\\w+)', sql)\n"
            "cols, rel = m.group(1), m.group(2)\n"
            "names = [c.strip() for c in cols.split(',')]\n"
            "if fail == 'events' and rel == 'tape_events': sys.exit(1)\n"
            "if fail == 'oi' and 'oi' in names: sys.exit(1)\n"
            "if cols == 'count(*)': print('count'); print(3); sys.exit(0)\n"
            "if rel == 'tape_daily_report' and names == ['trading_day', 'symbol']: print('trading_day,symbol'); print('2026-11-05,NIFTY'); sys.exit(0)\n"
            "print(','.join(names)); print(','.join('x' for _ in names))\n")
    sh = os.path.join(d, "fake_roq.sh")
    with open(sh, "w", encoding="utf-8", newline="\n") as fh:
        fh.write('#!/usr/bin/env bash\nexec "%s" "%s"\n' % (sys.executable.replace("\\", "/"), py.replace("\\", "/")))
    os.chmod(sh, 0o755)
    return sh


def _run_extract(fail):
    bash = shutil.which("bash")
    if bash is None:
        return None, "bash not found", None
    d = tmpdir()
    roq = _fake_roq(d)
    out = os.path.join(d, "out")
    env = dict(os.environ, FAKE_FAIL=fail)
    p = subprocess.run([bash, os.path.join(ROOT, PKG, "run_extract.sh").replace("\\", "/"), "--from", "2026-11-05", "--to", "2026-11-05",
                        "--out", out.replace("\\", "/"), "--roq", roq.replace("\\", "/")], capture_output=True, text=True, env=env, timeout=300)
    return p.returncode, p.stdout + p.stderr, out


def g_t4_optional():
    """operator ruling 2026-11-05: tape_minute_oi is OPTIONAL. Absent -> descriptive t4 = NO_T4 and every verdict
    byte-identical; run_extract.sh skips a failed optional relation and still aborts on a failed required one."""
    d = build(_build_ds(_t4_plan()))
    a = score.run(d)
    shutil.rmtree(os.path.join(d, "tape_minute_oi"))
    b = score.run(d)
    cells = [ok(isinstance(a["descriptive"]["NIFTY"]["t4"], dict), "control: with the input present, T4 is computed"),
             ok(b["descriptive"]["NIFTY"]["t4"] == score.NO_T4, "input absent: t4 = %r (got %r)" % (score.NO_T4, b["descriptive"]["NIFTY"]["t4"])),
             ok(_strip_desc(a) == _strip_desc(b), "input absent: every verdict and non-descriptive figure byte-identical"),
             ok("missing_tape_minute_oi" not in json.dumps(b["files_missing"]), "an absent optional input is not listed as a missing file")]
    rc, txt, out = _run_extract("oi")
    f = os.path.join(out, "tape_minute_oi", "2026-11-05.csv") if out else ""
    cells.append(ok(rc == 0 and "OPTIONAL SKIP tape_minute_oi" in txt and not os.path.exists(f)
                    and os.path.exists(os.path.join(out, "tape_minute", "2026-11-05.csv")),
                    "run_extract.sh: the optional statement fails -> OPTIONAL SKIP, no file, the rest extracted, exit 0 (rc %s)" % rc))
    rc2, txt2, _ = _run_extract("events")
    cells.append(ok(rc2 == 1 and "PRECHECK FAIL tape_events" in txt2, "run_extract.sh: a required relation fails -> abort, exit 1 (rc %s)" % rc2))
    rc3, txt3, out3 = _run_extract("")
    cells.append(ok(rc3 == 0 and os.path.exists(os.path.join(out3, "tape_minute_oi", "2026-11-05.csv")),
                    "run_extract.sh: control, the optional relation is extracted when it reads (rc %s)" % rc3))
    return cells


GUARDS = [("sc-sign-only", g_sign_only), ("ha-s-definition", g_s_definition), ("ha-clock", g_clock), ("ha-delta", g_delta),
          ("ha-wilcoxon", g_wilcoxon), ("ha-decision", g_ha_decision), ("hb-labels", g_hb_labels),
          ("hb-match-kinds", g_hb_match_kinds), ("hb-lead-nearest", g_hb_lead_nearest), ("hb-window", g_hb_window),
          ("hb-null", g_hb_null), ("hb-decision", g_hb_decision), ("sc-quarantine", g_quarantine),
          ("sc-no-remerge", g_no_remerge), ("sc-run-once", g_run_once), ("sc-hash-check", g_hash_check),
          ("sc-extract-pure", g_extract_pure), ("sc-isolated", g_isolated), ("sc-params-v04", g_params),
          ("ha-r-window", g_r_window), ("ha-s-window", g_s_window), ("hb-per-label", g_hb_per_label),
          ("hb-t4-separate", g_hb_t4_separate), ("sc-descriptive-isolated", g_descriptive_isolated),
          ("sc-t4-optional", g_t4_optional)]


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
    bars = {k: (Fraction(100), Fraction(100), Fraction(100)) for k in range(m, m + 30)}
    bars[m - 1] = (Fraction(9999), Fraction(1), Fraction(1))    # the bar before T's minute: excluded
    bars[m + 30] = (Fraction(9999), Fraction(1), Fraction(1))   # past the horizon: excluded
    bars[m] = (Fraction(130), Fraction(100), Fraction(100))     # the bar labelled hm(T): included (v0.4)
    r, n = score.spot_range(bars, T)
    short = {k: v for k, v in bars.items() if k <= m + 23}
    r2, n2 = score.spot_range(short, T)
    short25 = {k: v for k, v in bars.items() if k <= m + 24}
    r3, _ = score.spot_range(short25, T)
    return [ok(r == 30 and n == 30, "R reads labels hm(T)..hm(T)+29 only: range 30 over 30 bars (got %s over %s)" % (r, n)),
            ok(r2 is None and n2 == 24, "24 of 30 bars -> excluded"), ok(r3 == 30, "25 of 30 bars -> kept")]


def u_oi_pct():
    """the T4 threshold equals the chain side's E2 literal; read by ast (score.py imports nothing from merdian_compute)."""
    tree = ast.parse(src("merdian_compute/tape/chain_events.py"))
    v = [n.value.value for n in tree.body if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "OI_PCT" for t in n.targets)]
    bad = [m for m in _imports(PKG + "/score.py") if m.startswith("merdian_compute")]
    return [ok(v == [score.PARAMS["e2_oi_move_pct"]], "e2_oi_move_pct %s == chain_events.OI_PCT %s" % (score.PARAMS["e2_oi_move_pct"], v)),
            ok(not bad, "score.py imports nothing from merdian_compute (%s)" % bad)]


def u_t4_stamp():
    """T4 is stamped at the CLOSE of its minute, never its start (Rule 0a)."""
    day = "2026-11-05"
    t0 = datetime(2026, 11, 5, 10, 30, 21, tzinfo=IST)
    runs = [{"us": score.us_of(t0), "expiry": "2026-11-10", "call_wall": Fraction(23000), "put_wall": Fraction(22000)}]
    row = lambda m, oi: {"symbol": "NIFTY", "opt_type": "CE", "expiry": "2026-11-10", "strike": "23000", "oi": str(oi),  # noqa: E731
                         "minute_ist": "%sT%02d:%02d:00+05:30" % (day, m // 60, m % 60)}
    ev = score.t4_events(day, "NIFTY", [row(713, 1000), row(718, 1060), row(719, 1100)], runs)
    want = score.us_of(datetime(2026, 11, 5, 11, 59, 0, tzinfo=IST))
    none = score.t4_events(day, "NIFTY", None, runs)
    return [ok(ev == {Fraction(23000): [(want, "CE")]}, "one T4 per cycle, stamped 11:59:00 for the 11:58 minute (got %s)" % ev),
            ok(none is None, "absent input -> None (T4 not computed)")]


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


UNITS = [u_ts_parse, u_lookahead, u_label_runs, u_lead_after_T, u_spot_clock, u_gates_fixture, u_manifest, u_median_switch,
         u_oi_pct, u_t4_stamp]


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
