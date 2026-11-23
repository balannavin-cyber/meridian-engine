#!/usr/bin/env python3
"""Tape live L0 guards (docs/tape/L0_plan.md sections 7-8): rules v1, the replay-mode writer, the wall source, verify, the SQL.

  python tests/test_tape_live.py [--root DIR] [--only GUARD]

--root runs the guards against another copy of the tree (tests/tape_live_mutants.py uses it). Every fixture is generated under a
temp dir by tests/tape_live/gen_live.py; no golden day, no network, no database, no .env.

Rule 23 (CLAUDE.md): refuses an unlimited `ulimit -v` where the `resource` module exists, and Mon-Fri 08:30-15:45 IST.
OPERATOR RULING R-1 (2026-11-03): the time-window refusal is a retail-box rule; this machine is Local. The window is lifted ONLY
when TAPE_RULE23_OVERRIDE_R1=1 is set, and every such run says so on its first line.

Last line: "TAPE LIVE GUARDS PASS (21/21)" or "TAPE LIVE GUARDS FAIL (...)". Exit 0 / 1; 2 = refused.
"""
import argparse
import ast
import contextlib
import errno
import csv
import decimal
import gzip
import hashlib
import importlib
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import types
import uuid
from datetime import datetime, timedelta, timezone

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument("--only", default=None)
ARGS = ap.parse_args()
ROOT = os.path.abspath(ARGS.root)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests", "tape_live"))

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
        print("REFUSED: rule 23 - fixture tests blocked 08:30-15:45 IST on weekdays (Local: set TAPE_RULE23_OVERRIDE_R1=1 under ruling R-1)")
        return 2
    return 0


if rule23():
    sys.exit(2)

import gen_live  # noqa: E402
from merdian_compute.tape import chain_events, cycle, events  # noqa: E402
from services.tape_live import cli as _cli0  # noqa: E402

# A mutant copy and a `git archive` export have no .git, so code_info() would read "unknown" and `cli live` refuses without a sha.
# One fixed test sha for the whole process, for cli replay and the runner alike, so their code_sha columns compare equal anywhere.
TEST_SHA = "0123456789abcdef0123456789abcdef01234567"
_cli0.code_info = lambda: {"git_sha": TEST_SHA, "dirty": False}

LIVE = os.path.join(ROOT, "services", "tape_live")
SQL = os.path.join(ROOT, "sql", "2026-11-06_tape_live_tables.sql")
DAY = gen_live.DAY
SIX = r"\btape_(minute|strike_cycle|events|chain_runs|chain_events|daily_report)\b"

_TMP = tempfile.mkdtemp(prefix="tape_live_")
_CACHE = {}


def mods():
    from services.tape_live import cli, ddl, rules, verify_day, wall_source, writer
    return cli, ddl, rules, verify_day, wall_source, writer


def quiet(fn, *a):
    buf_o, buf_e = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf_o), contextlib.redirect_stderr(buf_e):
        rc = fn(*a)
    return rc, buf_o.getvalue() + buf_e.getvalue()


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def rd(path):
    with open(path, "rb") as fh:
        return fh.read()


# ------------------------------------------------------------------------------------------- shared fixture
def fixture():
    if "fix" not in _CACHE:
        root = os.path.join(_TMP, "fix")
        f = gen_live.build(root)
        from services.tape_offline import cycle_day, process_day
        out, cyc = os.path.join(root, "batch_out"), os.path.join(root, "batch_cyc")
        rc1, log1 = quiet(process_day.main, [f["raw"], "--day", DAY, "--out", out])
        rc2, log2 = quiet(cycle_day.main, ["--in", out, "--session", os.path.join(f["raw"], "session"), "--out", cyc])
        if rc1 != 0 or rc2 != 0:
            raise AssertionError("batch fixture failed: %s %s\n%s\n%s" % (rc1, rc2, log1[-2000:], log2[-2000:]))
        rows = []
        for p in f["chain"]:
            with open(p, encoding="utf-8", newline="") as fh:
                rows += list(csv.DictReader(fh))
        res = chain_events.process(rows, DAY)
        runs = os.path.join(root, "chain_runs.csv")
        with open(runs, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(chain_events.render_runs_csv(res["runs"]))
        f.update(out=out, cyc=cyc, runs=runs)
        _CACHE["fix"] = f
    return _CACHE["fix"]


def replay(name, extra=(), out=None):
    """cli replay on the fixture; cached by name unless out is given."""
    if out is None and name in _CACHE:
        return _CACHE[name]
    cli = mods()[0]
    f = fixture()
    d = out or os.path.join(_TMP, "rp_" + name)
    argv = ["replay", "--day", DAY, "--raw", f["raw"], "--out", d]
    for p in f["chain"]:
        argv += ["--chain-runs", p]
    rc, log = quiet(cli.main, argv + list(extra))
    if rc != 0:
        raise AssertionError("replay %s rc=%s\n%s" % (name, rc, log[-3000:]))
    if out is None:
        _CACHE[name] = d
    return d


def arrival_file(name, mapping):
    p = os.path.join(_TMP, "arrival_%s.json" % name)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(mapping, fh)
    return p


def late_replay():
    sym, seg, at = gen_live.LATE_SEG
    return replay("late", ["--arrival", arrival_file("late", {"%s/%s" % (sym, seg): at})])


def ooo_replay():
    sym, seg, at = gen_live.LATE_SEG_OOO
    return replay("ooo", ["--arrival", arrival_file("ooo", {"%s/%s" % (sym, seg): at})])


def labels(d):
    with open(os.path.join(d, "tape_live_label.csv"), encoding="utf-8", newline="") as fh:
        return {(r["symbol"], r["ts_ist"][11:16], r["wall"]): r for r in csv.DictReader(fh)}


def verify(live, runs=None, name="v"):
    cli = mods()[0]
    f = fixture()
    rep = os.path.join(_TMP, "verify_" + name)
    argv = ["verify", "--day", DAY, "--live", live, "--final-cycle", os.path.join(f["cyc"], "tape_strike_cycle.csv"),
            "--final-events", os.path.join(f["cyc"], "tape_events.csv"), "--final-chain-runs", runs or f["runs"],
            "--report", rep]
    rc, log = quiet(cli.main, argv)
    with open(os.path.join(rep, "verify_report.json"), encoding="utf-8") as fh:
        return rc, json.load(fh), log


# ------------------------------------------------------------------------------------------- planted cycle rows
TOK = {"CE": "10103", "PE": "10104"}


def ts(hhmm):
    return "%sT%s:00+05:30" % (DAY, hhmm)


def hm_add(hhmm, d):
    m = int(hhmm[:2]) * 60 + int(hhmm[3:]) + d
    return "%02d:%02d" % (m // 60, m % 60)


def crow(hhmm, strike="23550", leg="CE", expiry="2026-11-09", sym="NIFTY", **kw):
    r = {c: "" for c in cycle.CYCLE_COLS}
    r.update({"symbol": sym, "expiry": expiry, "strike": strike, "leg": leg, "token": TOK.get(leg, "10190"),
              "tradingsymbol": "NIFTY26N09%s%s" % (strike, leg), "T": ts(hhmm), "buy_5": "650", "sell_5": "715",
              "uncl_5": "130", "gap_5": "0", "trades_5": "5", "buy_15": "1950", "sell_15": "2145", "buy_30": "3900",
              "sell_30": "4290", "balance_5": "-0.047619", "balance_15": "-0.047619", "balance_30": "-0.047619",
              "resting_imb": "0.090909", "classified_share_5": "0.913043", "buy_cum": "6500", "sell_cum": "7150",
              "uncl_cum": "1300", "gap_cum": "0", "oi_last": "250650", "oi_delta_5": "130", "minutes_present_5": "5",
              "first_seen_T": ts("09:20")})
    for k, v in kw.items():
        r[k] = v
    return r


def series(a, b, **kw):
    out, h = [], a
    while h <= b:
        out.append(crow(h, **kw))
        h = hm_add(h, 5)
    return out


def ev(kind, hhmm_close, side, strike="23550", leg="CE", expiry="2026-11-09", sym="NIFTY"):
    return {"symbol": sym, "expiry": expiry, "strike": strike, "leg": leg, "kind": kind, "ts_ist": ts(hhmm_close),
            "side": side, "magnitude": "3.512345", "detail_json": "{}"}


def wall(hhmm, call="23550", put="23500", sym="NIFTY", expiry="2026-11-09"):
    return {"symbol": sym, "trading_day": DAY, "expiry": expiry, "ts_ist": ts(hhmm), "chain_run_id": "r-%s" % hhmm,
            "chain_run_ts": ts(hhmm)[:17] + "21+05:30", "call_wall": call, "put_wall": put,
            "call_wall_oi_call": "4003900", "put_wall_oi_put": "4502600"}


# ------------------------------------------------------------------------------------------- guards
SPEC_TABLE = [  # spec s4 shared vectors, retyped here on purpose: an independent copy to catch drift in the JSON
    (1, 1, 1, 0, 1, 1, 1, 1, "HIT", 0), (2, 1, 1, 0, 1, 1, 1, 0, "ABSORBED", 0), (3, 1, 1, 0, 1, 1, 0, 1, "THINNING", 0),
    (4, 1, 1, 0, 1, 1, 0, 0, "QUIET", 0), (5, 0, 1, 0, 1, 1, 1, 1, "NO_READ", 0), (6, 1, 0, 0, 1, 1, 1, 1, "NO_READ", 0),
    (7, 1, 1, 1, 1, 1, 1, 1, "NO_READ", 0), (8, 1, 1, 0, 0, 1, 0, 1, "THINNING", 1), (9, 1, 1, 0, 0, 1, 0, 0, "NO_READ", 0),
    (10, 1, 1, 0, 1, 0, 1, 0, "NO_READ", 0), (11, 1, 1, 0, 0, 0, 0, 0, "NO_READ", 0)]
FLAG_KEYS = ("wall_known", "in_window", "untraded", "conc_evaluable", "thin_evaluable", "C", "N")


def g_vectors():
    rules = mods()[2]
    with open(os.path.join(LIVE, "tapeLabels.vectors.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    vec = {v["id"]: v for v in doc["vectors"]}
    bad = []
    for row in SPEC_TABLE:
        v = vec.get(row[0])
        want_flags = {k: bool(x) for k, x in zip(FLAG_KEYS, row[1:8])}
        if v is None or v["flags"] != want_flags or v["expected"]["label"] != row[8] or v["expected"]["partial"] != bool(row[9]):
            bad.append("spec vector %d differs in the JSON" % row[0])
    for v in doc["vectors"]:
        got = rules.label_wall(dict(v["flags"]))
        want = (v["expected"]["label"], v["expected"]["partial"], v["expected"]["reason"])
        if tuple(got) != want:
            bad.append("vector %d: got %r want %r" % (v["id"], tuple(got), want))
    if doc.get("rule_version") != rules.RULE_VERSION:
        bad.append("rule_version %r != %r" % (doc.get("rule_version"), rules.RULE_VERSION))
    return not bad, "; ".join(bad) or "%d vectors (11 spec + %d L0)" % (len(vec), len(vec) - 11)


def g_derive():
    rules = mods()[2]
    D = rules.derive_flags
    bad, n_chk = [], [0]

    def chk(name, got, **want):
        n_chk[0] += 1
        for k, v in want.items():
            if got.get(k) != v:
                bad.append("%s: %s=%r want %r" % (name, k, got.get(k), v))

    base = series("09:20", "11:00")
    w = wall("11:00")
    chk("C at T-10", D(base, [ev("CONC", "10:50", "buy")], w, ts("11:00"), "call"), C=True, N=False)
    chk("C at T-15 excluded", D(base, [ev("CONC", "10:45", "buy")], w, ts("11:00"), "call"), C=False)
    chk("C at T", D(base, [ev("CONC", "11:00", "sell")], w, ts("11:00"), "call"), C=True)
    chk("N ask at T-14", D(base, [ev("THIN", "10:46", "ask")], w, ts("11:00"), "call"), N=True, C=False)
    chk("N ask at T-15 excluded", D(base, [ev("THIN", "10:45", "ask")], w, ts("11:00"), "call"), N=False)
    chk("N ask at T-19 excluded", D(base, [ev("THIN", "10:41", "ask")], w, ts("11:00"), "call"), N=False)
    chk("C at T-20 excluded", D(base, [ev("CONC", "10:40", "buy")], w, ts("11:00"), "call"), C=False)
    chk("bid THIN is not N", D(base, [ev("THIN", "10:55", "bid")], w, ts("11:00"), "call"), N=False)
    chk("other strike / leg / expiry ignored", D(base, [ev("THIN", "10:55", "ask", strike="23600"),
                                                       ev("CONC", "10:55", "buy", leg="PE"),
                                                       ev("CONC", "10:55", "buy", expiry="2026-11-16")], w, ts("11:00"), "call"),
        C=False, N=False)
    chk("THIN is not C", D(base, [ev("THIN", "10:55", "ask")], w, ts("11:00"), "call"), C=False, N=True)
    chk("future event ignored", D(base + series("11:05", "11:10"), [ev("CONC", "11:05", "buy")], w, ts("11:00"), "call"), C=False)
    # put wall: PE leg at 23500 (ask on both legs, R-3)
    pe = series("09:20", "11:00", strike="23500", leg="PE")
    chk("put wall N ask on PE", D(pe, [ev("THIN", "10:58", "ask", strike="23500", leg="PE")], w, ts("11:00"), "put"),
        N=True, in_window=True)
    # conc_evaluable: 12 prior rows
    chk("11 prior rows", D(series("09:20", "10:15"), [], wall("10:15"), ts("10:15"), "call"), conc_evaluable=False, n_prior_bins=11)
    chk("12 prior rows", D(series("09:20", "10:20"), [], wall("10:20"), ts("10:20"), "call"), conc_evaluable=True, n_prior_bins=12)
    # thin_evaluable: sum minutes_present_5 over rows T-25..T >= 20
    mp = {"09:30": "5", "09:35": "5", "09:40": "5", "09:45": "5", "09:50": "1", "09:55": "2", "10:00": "2"}
    rows = [crow(h, minutes_present_5=v) for h, v in sorted(mp.items())]
    chk("present 20 (T-30 row not counted)", D(rows, [], wall("10:00"), ts("10:00"), "call"),
        thin_evaluable=True, minutes_present_30=20)
    rows19 = [crow(h, minutes_present_5=("1" if h == "10:00" else v)) for h, v in sorted(mp.items())]
    chk("present 19", D(rows19, [], wall("10:00"), ts("10:00"), "call"), thin_evaluable=False, minutes_present_30=19)
    # untraded: no trades since the open AND T >= 10:00
    zt = series("09:20", "10:05", trades_5="0")
    chk("untraded 09:55", D(zt, [], wall("09:55"), ts("09:55"), "call"), untraded=False, trades_cum=0)
    chk("untraded 10:00", D(zt, [], wall("10:00"), ts("10:00"), "call"), untraded=True, trades_cum=0)
    one = [dict(r, trades_5=("1" if r["T"] == ts("09:40") else "0")) for r in zt]
    chk("one trade at 09:40", D(one, [], wall("10:00"), ts("10:00"), "call"), untraded=False, trades_cum=1)
    later = [dict(r, trades_5=("4" if r["T"] == ts("10:05") else "0")) for r in zt]
    chk("trade only after T", D(later, [], wall("10:00"), ts("10:00"), "call"), untraded=True, trades_cum=0)
    # in_window / wall_known
    chk("no row at T", D(series("09:20", "10:55"), [], w, ts("11:00"), "call"), in_window=False)
    chk("row at T on another expiry", D(series("09:20", "11:00", expiry="2026-11-16"), [], w, ts("11:00"), "call"), in_window=False)
    chk("strike 23550.0 vs 23550", D(base, [], wall("11:00", call="23550.0"), ts("11:00"), "call"), in_window=True)
    chk("no wall row", D(base, [], None, ts("11:00"), "call"), wall_known=False)
    chk("wall row without a call wall", D(base, [], wall("11:00", call=""), ts("11:00"), "call"), wall_known=False)
    # display: OI build over the window, NULL never 0
    ob = [dict(r, oi_delta_5=("" if r["T"] < ts("10:50") else "195")) for r in base]
    chk("oi build", D(ob, [], w, ts("11:00"), "call"), oi_build_15=585)
    ob0 = [dict(r, oi_delta_5="") for r in base]
    chk("oi build all NULL", D(ob0, [], w, ts("11:00"), "call"), oi_build_15=None)
    return not bad, "; ".join(bad) or "%d planted derivations" % n_chk[0]


def g_rule_inputs():
    path = os.path.join(LIVE, "rules.py")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    tree = ast.parse(text)
    bad = []
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "derive_flags"]
    if len(fn) != 1:
        return False, "derive_flags not found once"
    a = fn[0].args
    names = [x.arg for x in a.posonlyargs + a.args]
    if names != ["cycle_rows", "events", "wall_row", "T", "wall"] or a.vararg or a.kwarg or a.kwonlyargs or a.defaults:
        bad.append("derive_flags signature %r (vararg=%s kwarg=%s kwonly=%s defaults=%d)"
                   % (names, bool(a.vararg), bool(a.kwarg), [k.arg for k in a.kwonlyargs], len(a.defaults)))
    for w in sorted(set(re.findall(r"\b(depth\w*|bid_qty_5|ask_qty_5|minute_ist|tape_minute)\b", text))):
        bad.append("rules.py names minute-level field %r" % w)
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            mod = n.module if isinstance(n, ast.ImportFrom) else n.names[0].name
            if (mod or "").split(".")[0] not in sys.stdlib_module_names:
                bad.append("rules.py imports %r" % mod)
    with open(os.path.join(LIVE, "writer.py"), encoding="utf-8") as fh:
        wt = ast.parse(fh.read())
    calls = [n for n in ast.walk(wt) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "derive_flags"]
    if not calls or any(len(c.args) != 5 or c.keywords for c in calls):
        bad.append("writer.py derive_flags calls: %d, not all 5-positional" % len(calls))
    return not bad, "; ".join(bad) or "signature (cycle_rows, events, wall_row, T, wall); no depth field; stdlib only"


def g_wall_floor():
    ws = mods()[4]
    f = fixture()
    runs = ws.runs_from_snapshot_csv(f["chain"], DAY)
    bad = []

    def chk(sym, hhmm, run_hms, cw, pw, oi_c=None):
        w = ws.wall_row(runs.get(sym, []), DAY, hhmm)
        got = None if w is None else (w["chain_run_ts"][11:19], w["call_wall"], w["put_wall"], w["call_wall_oi_call"])
        want = None if run_hms is None else (run_hms, cw, pw, oi_c if oi_c is not None else got and got[3])
        if got != want:
            bad.append("%s %s: got %r want %r" % (sym, hhmm, got, want))

    m = 13 * 60   # the generator's call-wall OI is 4000000 + 1300 * (minute % 7) at the wall
    chk("NIFTY", "13:00", "13:00:21", "23700", "23500", str(4000000 + 1300 * (m % 7)))
    chk("NIFTY", "12:55", "12:55:21", "23550", "23500", str(4000000 + 1300 * ((m - 5) % 7)))
    chk("NIFTY", "13:15", "13:15:21", "23550", "23500")
    chk("NIFTY", "09:20", "09:20:21", "23550", "23500")
    chk("SENSEX", "09:25", None, None, None)
    chk("SENSEX", "09:30", "09:30:21", "77000", "77100")
    # irregular run times: the run used for T is the latest whose ts floored to 5 min is <= T
    synth = [{"symbol": "NIFTY", "expiry": "2026-11-09", "ts_ist": "%sT%s+05:30" % (DAY, t), "run_id": "r" + t,
              "call_wall": c, "put_wall": "23500", "call_wall_oi_call": "", "put_wall_oi_put": ""}
             for t, c in (("13:58:40", "23500"), ("14:03:10", "23550"), ("14:07:59", "23600"), ("14:11:02", "23650"))]
    for T, want in (("13:55", "13:58:40"), ("14:00", "14:03:10"), ("14:05", "14:07:59"), ("14:10", "14:11:02"), ("13:50", None)):
        w = ws.wall_row(synth, DAY, T)
        got = None if w is None else w["chain_run_ts"][11:19]
        if got != want:
            bad.append("synthetic T=%s: run %r want %r" % (T, got, want))
    return not bad, "; ".join(bad) or "fixture runs + 5 irregular-time cases; back expiry ignored"


def g_first_wins():
    f = fixture()
    (lk, lwant) = gen_live.LATE_LABEL
    sym, seg, at = gen_live.LATE_SEG
    d = os.path.join(_TMP, "fw")
    shutil.rmtree(d, ignore_errors=True)
    replay("fw1", ["--until", lk[1], "--arrival", arrival_file("fw", {"%s/%s" % (sym, seg): at})], out=d)
    first = labels(d)
    bad = []
    r1 = first.get(lk)
    if r1 is None or (r1["label"], r1["partial"] == "true", r1["reason"]) != lwant:
        bad.append("first pass label %r want %r" % (r1 and r1["label"], lwant))
    replay("fw2", ["--resume"], out=d)
    second = labels(d)
    if second.get(lk) != r1:
        bad.append("label row changed on resume: %r -> %r" % (r1 and r1["label"], second.get(lk, {}).get("label")))
    if second.get(("NIFTY", "11:10", "call"), {}).get("label") != "HIT":
        bad.append("11:10 call label after resume %r want HIT" % second.get(("NIFTY", "11:10", "call"), {}).get("label"))
    if rd(os.path.join(d, "tape_live_cycle.csv")) != rd(os.path.join(f["cyc"], "tape_strike_cycle.csv")):
        bad.append("live-cycle rows were not upserted to the final values on resume")
    return not bad, "; ".join(bad) or "as-seen %s %s kept (%s) while live-cycle rows were upserted" % (lk[1], lk[2], lwant[0])


def _reconstruct(d):
    writer = mods()[5]
    names = sorted(n for n in os.listdir(os.path.join(d, "cycles")) if not n.endswith(".db.csv"))
    texts = []
    for n in names:
        with open(os.path.join(d, "cycles", n), encoding="utf-8", newline="") as fh:
            texts.append(fh.read())
    return writer.apply_deltas(texts)


def g_equal_offline():
    f = fixture()
    want_c = rd(os.path.join(f["cyc"], "tape_strike_cycle.csv"))
    want_e = rd(os.path.join(f["cyc"], "tape_events.csv"))
    bad, notes = [], []
    for name, d in (("clean", replay("clean")), ("late", late_replay()), ("out-of-order", ooo_replay())):
        if rd(os.path.join(d, "tape_live_cycle.csv")) != want_c:
            bad.append("%s: tape_live_cycle.csv != batch" % name)
        if rd(os.path.join(d, "tape_live_events.csv")) != want_e:
            bad.append("%s: tape_live_events.csv != batch" % name)
        rc, re_ = _reconstruct(d)
        if rc.encode("utf-8") != want_c or re_.encode("utf-8") != want_e:
            bad.append("%s: state rebuilt from the per-cycle deltas != batch" % name)
        with open(os.path.join(d, "run_manifest.json"), encoding="utf-8") as fh:
            man = json.load(fh)
        trig = sorted(set((r["trigger"], r["at"]) for r in man["rebuilds"]))
        notes.append("%s rebuilds=%s" % (name, ",".join("%s@%s" % t for t in trig)))
        if name == "out-of-order" and not any(t[0] == "late_segment" for t in trig):
            bad.append("out-of-order replay did not rebuild on the late segment")
        if not any(t[0] == "subscriptions" for t in trig):
            bad.append("%s replay did not rebuild on the 11:33 subscriptions file" % name)
    lab = labels(replay("clean"))
    for k, want in sorted(gen_live.PLANTED.items()):
        r = lab.get(k)
        got = None if r is None else (r["label"], r["partial"] == "true", r["reason"])
        if got != want:
            bad.append("planted %s: got %r want %r" % ("/".join(k), got, want))
    rc_, rep, _log = verify(replay("clean"), name="eq")
    if rep["totals"]["differences"] != 0 or rep["totals"]["missing"] != 0:
        bad.append("clean labels != labels recomputed from the final rows: %r" % rep["totals"])
    n = sum(1 for _ in want_c.splitlines()) - 1
    return not bad, "; ".join(bad) or "clean, late and out-of-order replays byte-equal to batch (%d cycle rows, %d event rows); %d planted labels; %s" % (
        n, sum(1 for _ in want_e.splitlines()) - 1, len(gen_live.PLANTED), "; ".join(notes))


def g_causal():
    rules = mods()[2]
    d = replay("clean")
    with open(os.path.join(d, "tape_live_cycle.csv"), encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    with open(os.path.join(d, "tape_live_events.csv"), encoding="utf-8", newline="") as fh:
        evs = list(csv.DictReader(fh))
    with open(os.path.join(d, "tape_live_wall.csv"), encoding="utf-8", newline="") as fh:
        walls = {(r["symbol"], r["ts_ist"]): r for r in csv.DictReader(fh)}
    rng = random.Random(7)
    bad, n = [], 0
    numeric = ("buy_5", "sell_5", "trades_5", "minutes_present_5", "oi_delta_5", "oi_last")
    for (sym, T), w in sorted(walls.items()):
        if T[11:16] > "15:30":
            continue
        rs = [r for r in rows if r["symbol"] == sym]
        es = [e for e in evs if e["symbol"] == sym]
        past = [r for r in rs if r["T"] <= T]
        fut = [dict(r) for r in rs if r["T"] > T]
        for c in numeric:   # shuffle every value among the bins after T
            vals = [r[c] for r in fut]
            rng.shuffle(vals)
            for r, v in zip(fut, vals):
                r[c] = v
        fut_ev = [dict(e, ts_ist="%sT%s:00+05:30" % (DAY, rng.choice(["11:05", "12:05", "13:35", "14:20", "15:30"])))
                  for e in es if e["ts_ist"] > T]
        fut_ev = [e for e in fut_ev if e["ts_ist"] > T]
        for wl in ("call", "put"):
            full = rules.derive_flags(rs, es, w, T, wl)
            cut = rules.derive_flags(past, [e for e in es if e["ts_ist"] <= T], w, T, wl)
            shuf = rules.derive_flags(past + fut, [e for e in es if e["ts_ist"] <= T] + fut_ev, w, T, wl)
            n += 1
            if not (full == cut == shuf):
                bad.append("%s %s %s" % (sym, T[11:16], wl))
    # the writer itself: a replay stopped at 12:00 wrote the same labels for every T <= 12:00
    d2 = os.path.join(_TMP, "causal_until")
    shutil.rmtree(d2, ignore_errors=True)
    replay("cu", ["--until", "12:00"], out=d2)
    a, b = labels(d2), labels(d)
    for k, r in a.items():
        if b.get(k) != r:
            bad.append("writer label %s differs between --until 12:00 and the full run" % "/".join(k))
    return not bad, "; ".join(bad[:10]) or "%d (symbol, T, wall) derivations unchanged under cut / shuffled future; %d writer labels <= 12:00 equal" % (n, len(a))


def g_verify():
    f = fixture()
    bad = []
    rc, rep, log = verify(replay("clean"), name="clean")
    if rep["totals"]["differences"] or rep["totals"]["missing"] or rc != 0:
        bad.append("clean: %r rc=%s" % (rep["totals"], rc))
    for s in rep["symbols"].values():
        if s["match_pct"] != 100.0:
            bad.append("clean match_pct %r" % s["match_pct"])
    rc, rep, log = verify(late_replay(), name="late")
    got = [(x["symbol"], x["ts_ist"][11:16], x["wall"], x["cause"]) for x in rep["differences"]]
    lk = gen_live.LATE_LABEL[0]
    if got != [(lk[0], lk[1], lk[2], "late_segment")]:
        bad.append("late: differences %r" % got)
    # planted wall change: the final run for one grid point names a different call wall
    sym, hhmm, col, val, key = gen_live.WALL_CHANGE
    with open(f["runs"], encoding="utf-8", newline="") as fh:
        rr = list(csv.DictReader(fh))
    hit = 0
    for r in rr:
        if r["symbol"] == sym and r["ts_ist"][11:16] == hhmm:
            r[col] = val
            hit += 1
    p = os.path.join(_TMP, "runs_wall_change.csv")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rr[0].keys()), lineterminator="\n")
        wr.writeheader()
        wr.writerows(rr)
    rc, rep, log = verify(replay("clean"), runs=p, name="wall")
    got = [(x["symbol"], x["ts_ist"][11:16], x["wall"], x["cause"]) for x in rep["differences"]]
    if hit != 1 or got != [(key[0], key[1], key[2], "chain_run_differs")]:
        bad.append("wall change (%d runs edited): differences %r" % (hit, got))
    return not bad, "; ".join(bad) or "clean 100 %; late segment -> exactly 1 late_segment; wall change -> exactly 1 chain_run_differs"


def g_deterministic():
    a = replay("clean")
    b = replay("clean2")
    bad = []
    fa = sorted(os.path.relpath(os.path.join(dp, n), a) for dp, _, ns in os.walk(a) for n in ns)
    fb = sorted(os.path.relpath(os.path.join(dp, n), b) for dp, _, ns in os.walk(b) for n in ns)
    if fa != fb:
        bad.append("file sets differ")
    for rel in fa:
        if rel in fb and rd(os.path.join(a, rel)) != rd(os.path.join(b, rel)):
            bad.append("differs: " + rel)
    with open(os.path.join(a, "run_manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    for rel, h in man["outputs"].items():
        if sha(os.path.join(a, rel)) != h:
            bad.append("manifest hash wrong: " + rel)
    if len(man["outputs"]) + 1 != len(fa):
        bad.append("manifest lists %d outputs, dir holds %d files" % (len(man["outputs"]), len(fa)))
    return not bad, "; ".join(bad[:10]) or "%d files byte-identical across two runs; manifest hashes match" % len(fa)


def _live_py():
    return sorted(os.path.join(LIVE, n) for n in os.listdir(LIVE) if n.endswith(".py"))


def g_no_outcomes():
    bad = []
    pat = re.compile(r"(?i)\b(spot\w*|outcome\w*|agreement\w*|lead|lead_\w+|coverage\w*|straddle\w*|range_by_group)\b")
    chain_pat = re.compile(r"\b(gex_strike_snapshots|oi_call|oi_put|tape_chain_\w+|chain_events)\b")
    for p in _live_py() + [SQL]:
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        for w in sorted(set(m.group(0) for m in pat.finditer(text))):
            bad.append("%s names %r" % (os.path.basename(p), w))
        if os.path.basename(p) != "wall_source.py":
            for w in sorted(set(m.group(0) for m in chain_pat.finditer(text))):
                bad.append("%s touches the chain side (%r) outside wall_source.py" % (os.path.basename(p), w))
        if p.endswith(".py"):
            for n in ast.walk(ast.parse(text)):
                if isinstance(n, ast.ImportFrom) and n.module and "chain_events" in n.module + "".join(a.name for a in n.names) \
                        and os.path.basename(p) != "wall_source.py":
                    bad.append("%s imports chain_events" % os.path.basename(p))
    return not bad, "; ".join(bad) or "%d files scanned; chain access only in wall_source.py" % (len(_live_py()) + 1)


def g_isolated():
    bad = []
    for sub in ("tape_runner", "tape_scoring"):
        for dp, _, ns in os.walk(os.path.join(ROOT, "services", sub)):
            for n in ns:
                with open(os.path.join(dp, n), "rb") as fh:
                    if b"tape_live" in fh.read():
                        bad.append("services/%s/%s mentions tape_live" % (sub, n))
    with open(os.path.join(ROOT, "services", "tape_runner", "install.sh"), encoding="utf-8") as fh:
        inst = fh.read()
    if "tape_live" in inst or not re.search(r"archive HEAD services/__init__\.py services/tape_runner \|", inst):
        bad.append("install.sh ships more than services/__init__.py services/tape_runner")
    allowed = {"merdian_compute.tape", "services.tape_live", "services.tape_offline", "services.tape_db"}
    for p in _live_py():
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        for n in ast.walk(ast.parse(text)):
            mods_ = []
            if isinstance(n, ast.Import):
                mods_ = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                mods_ = [n.module or ""]
            for m in mods_:
                top = m.split(".")[0]
                if top in sys.stdlib_module_names:
                    continue
                if not any(m == a or m.startswith(a + ".") for a in allowed):
                    bad.append("%s imports %r" % (os.path.basename(p), m))
    for p in _live_py() + [SQL]:
        with open(p, encoding="utf-8") as fh:
            for w in sorted(set(m.group(0) for m in re.finditer(SIX, fh.read()))):
                bad.append("%s names %r" % (os.path.basename(p), w))
    return not bad, "; ".join(bad) or "not imported by runner/scoring; not shipped; stdlib + tape packages only; no six-table name"


def g_sql():
    ddl = mods()[1]
    from services.tape_db import tape_schema as S
    with open(SQL, encoding="utf-8") as fh:
        text = fh.read()
    bad = []
    if text != ddl.render():
        bad.append("file != services/tape_live/ddl.py render()")
    tables = ("tape_live_cycle", "tape_live_events", "tape_live_wall", "tape_live_label")
    for t in tables:
        if not re.search(r"CREATE TABLE IF NOT EXISTS public\.%s \(" % t, text):
            bad.append("%s: no CREATE TABLE IF NOT EXISTS" % t)
        if "ALTER TABLE public.%s ENABLE ROW LEVEL SECURITY;" % t not in text:
            bad.append("%s: RLS not enabled" % t)
        if "REVOKE ALL ON public.%s FROM anon, authenticated;" % t not in text:
            bad.append("%s: no REVOKE from anon, authenticated" % t)
        pol = re.findall(r"CREATE POLICY (\w+) ON public\.%s FOR (\w+) TO (\w+) USING \(true\);" % t, text)
        if sorted((p[1], p[2]) for p in pol) != [("SELECT", "merdian_ro"), ("SELECT", "tape_ro")]:
            bad.append("%s: policies %r" % (t, pol))
        if len(re.findall(r"CREATE POLICY \w+ ON public\.%s\b" % t, text)) != 2:
            bad.append("%s: not exactly two policies" % t)
        if not re.search(r"COMMENT ON TABLE public\.%s IS '[^']*display only, never scored" % t, text):
            bad.append("%s: no 'display only, never scored' comment" % t)
    for g in re.findall(r"GRANT [^;]+;", text):
        roles = re.search(r"\bTO (.+);", g).group(1)
        if set(r.strip() for r in roles.split(",")) - {"tape_ro", "merdian_ro"}:
            bad.append("grant to another role: %s" % g)
    for g in re.findall(r"GRANT [^;]+;", text):
        if re.search(r"(?i)\bTO\b.*\b(anon|authenticated|public)\b", g):
            bad.append("a GRANT goes to anon / authenticated / public: %s" % g)
    if re.search(SIX, text):
        bad.append("names one of the six tables")
    if "server_version_num')::int < 150000" not in text:
        bad.append("no PostgreSQL >= 15 guard")
    # columns: the two copied tables carry exactly the tape_schema data columns + live provenance
    for t, cols in (("tape_live_cycle", cycle.CYCLE_COLS), ("tape_live_events", events.EVENT_COLS)):
        src = [n for n, s in S.TABLES.items() if s["cols"] is cols][0]
        want = [c for c in S.db_columns(src) if c not in dict(S.PROVENANCE)] + ["as_of", "live_run_id", "code_sha"]
        body = re.search(r"CREATE TABLE IF NOT EXISTS public\.%s \((.*?)\n\);" % t, text, re.S).group(1)
        got = [ln.split()[0] for ln in body.strip().split("\n") if not ln.strip().startswith("CONSTRAINT")]
        if got != want:
            bad.append("%s columns %r != %r" % (t, got, want))
        types = S.db_types(src)
        for ln in body.strip().split("\n"):
            m = re.match(r"\s*(\w+)\s+(.+?)( NOT NULL)?,?$", ln)
            if m and m.group(1) in types and m.group(1) not in dict(S.PROVENANCE) and m.group(1) != "CONSTRAINT":
                if m.group(2) != types[m.group(1)]:
                    bad.append("%s.%s type %r differs from tape_schema %r" % (t, m.group(1), m.group(2), types[m.group(1)]))
                nn_want = m.group(1) in S.spec(src)["not_null"]
                if bool(m.group(3)) != nn_want:
                    bad.append("%s.%s NOT NULL %s, tape_schema %s" % (t, m.group(1), bool(m.group(3)), nn_want))
    return not bad, "; ".join(bad) or "4 tables, RLS, 2 SELECT policies each, no anon grant, columns from tape_schema"


# ------------------------------------------------------------------------------------------- snapshot ts width
# Python 3.10 fromisoformat accepts a fraction of 0, 3 or 6 digits only; Postgres trims trailing zeros, so a gex_strike_snapshots
# ts arrives with 1-6. The property asserted here is about the STRINGS handed to chain_events.build_runs, so it fails on 3.12 too.
TSW_STRIKES = ("23500.0", "23550.0", "23600.0")
TSW = [   # UTC h, m, s | fraction text as planted | that fraction in microseconds (chosen, not derived) | oi_call | oi_put
    (3, 10, 6, "43966", 439660, (100, 300, 200), (500, 100, 150)),       # the string that failed on the box (width 5)
    (4, 30, 21, None, 0, (100, 200, 400), (50, 600, 150)),               # width 0, must pass through byte-identical
    (4, 35, 21, "5", 500000, (900, 200, 400), (50, 60, 700)),            # 1
    (4, 40, 21, "25", 250000, (100, 800, 400), (650, 60, 70)),           # 2
    (4, 45, 21, "125", 125000, (100, 200, 1000), (50, 660, 70)),         # 3
    (4, 50, 21, "4396", 439600, (1100, 200, 400), (50, 60, 670)),        # 4: stored .439600, trailing zeros dropped
    (4, 55, 21, "43966", 439660, (100, 1200, 400), (680, 60, 70)),       # 5
    (5, 0, 21, "439660", 439660, (100, 200, 1300), (50, 690, 70))]       # 6
# Hand-computed from the table above (argmax of each OI column, strikes in the order TSW_STRIKES; the back-expiry row is ignored):
# grid HH:MM -> (run time IST hh:mm:ss, call wall, its oi_call, put wall, its oi_put); None = no run yet
TSW_WALLS = {"08:35": None, "08:40": ("08:40:06", "23550", "300", "23500", "500"),
             "10:00": ("10:00:21", "23600", "400", "23550", "600"), "10:02": ("10:00:21", "23600", "400", "23550", "600"),
             "10:05": ("10:05:21", "23500", "900", "23600", "700"), "10:10": ("10:10:21", "23550", "800", "23500", "650"),
             "10:15": ("10:15:21", "23600", "1000", "23550", "660"), "10:20": ("10:20:21", "23500", "1100", "23600", "670"),
             "10:25": ("10:25:21", "23550", "1200", "23500", "680"), "10:30": ("10:30:21", "23600", "1300", "23550", "690")}
TSW_TS_RE = re.compile(r"^2026-11-06T(\d\d):(\d\d):(\d\d)(?:\.(\d+))?\+00:00$")


def _tsw_csv(name, ts_list_rows):
    d = os.path.join(_TMP, "tsw")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("run_id,symbol,ts,expiry_date,strike,oi_call,oi_put,gex_cr\n")
        for r in ts_list_rows:
            fh.write(",".join(r) + "\n")
    return p


def _tsw_rows(ts_of_run):
    rows = []
    for i, (_h, _m, _s, _f, _us, calls, puts) in enumerate(TSW):
        ts_ = ts_of_run(i)
        for k, oc, op in zip(TSW_STRIKES, calls, puts):
            rows.append(["run%d" % i, "NIFTY", ts_, "2026-11-10", k, str(oc), str(op), "0.100000"])
        rows.append(["run%d" % i, "NIFTY", ts_, "2026-11-17", TSW_STRIKES[1], "9000000", "9100000", "0.500000"])   # back expiry
    return rows


def g_ts_width():
    ws = mods()[4]
    bad = []
    planted = [("2026-11-06T%02d:%02d:%02d%s+00:00" % (h, m, s, "" if f is None else "." + f)) for h, m, s, f, _u, _c, _p in TSW]
    want_us = [((h * 60 + m) * 60 + s) * 1000000 + u for h, m, s, _f, u, _c, _p in TSW]
    p = _tsw_csv("planted.csv", _tsw_rows(lambda i: planted[i]))
    seen = []
    orig = chain_events.build_runs

    def spy(rows, day=None):
        rows = list(rows)
        seen.extend(r["ts"] for r in rows)
        return orig(rows, day)

    chain_events.build_runs = spy
    try:
        runs = ws.runs_from_snapshot_csv([p], DAY)
    finally:
        chain_events.build_runs = orig
    # 1 the rows really went through chain_events.build_runs (8 runs x (3 front strikes + 1 back-expiry row))
    if len(seen) != 32:
        bad.append("cell1: build_runs saw %d rows, expected exactly 32" % len(seen))
    # 2 width is a property of the string, not of the interpreter
    for s in seen:
        m = re.search(r"\.(\d+)", s)
        w = 0 if m is None else len(m.group(1))
        if w not in (0, 3, 6):
            bad.append("cell2: ts %r reached build_runs with fraction width %d" % (s, w))
            break
    # 3 same instant, from the generator's integers (a test-local integer reader; no datetime, no code under test)
    for j, s in enumerate(seen[:32]):
        m = TSW_TS_RE.match(s)
        if m is None:
            bad.append("cell3: ts %r no longer has the planted shape" % s)
            break
        f = m.group(4) or ""
        us = ((int(m.group(1)) * 60 + int(m.group(2))) * 60 + int(m.group(3))) * 1000000 + (int(f) * 10 ** (6 - len(f)) if f else 0)
        if us != want_us[j // 4]:
            bad.append("cell3: row %d ts %r is %d us, the planted instant is %d us" % (j, s, us, want_us[j // 4]))
            break
    # 4 a ts with no fraction passes through byte-identical
    if 4 < len(seen) and seen[4:8] != [planted[1]] * 4:
        bad.append("cell4: the no-fraction ts did not pass through unchanged: %r" % seen[4:8])
    # 5 runs, walls and wall OI equal the hand-computed table
    for hhmm, want in TSW_WALLS.items():
        w = ws.wall_row(runs.get("NIFTY", []), DAY, hhmm)
        got = None if w is None else (w["chain_run_ts"][11:19], w["call_wall"], w["call_wall_oi_call"], w["put_wall"],
                                      w["put_wall_oi_put"])
        if got != want:
            bad.append("cell5: %s got %r want %r" % (hhmm, got, want))
    if len(runs.get("NIFTY", [])) != 8:
        bad.append("cell5: %d runs, expected 8" % len(runs.get("NIFTY", [])))
    # 6 a fraction wider than 6 raises (never rounds); the strict grammar rejects forms never seen in the exports
    p7 = _tsw_csv("wide.csv", _tsw_rows(lambda i: "2026-11-06T03:10:06.4396601+00:00" if i == 0 else planted[i]))
    try:
        ws.runs_from_snapshot_csv([p7], DAY)
        bad.append("cell6: a 7-digit fraction did not raise")
    except ValueError as exc:
        if "wider than 6" not in str(exc):
            bad.append("cell6: ValueError without 'wider than 6': %s" % exc)
    norm = getattr(ws, "norm_snapshot_ts", None)
    if norm is None:
        bad.append("cell6: wall_source.norm_snapshot_ts does not exist")
    else:
        for s in ("2026-11-06T03:10:06.43966Z", "2026-11-06T03:10:06.43966+00", "2026-11-06 03:10:06.43966+00:00",
                  " 2026-11-06T03:10:06+00:00"):
            try:
                norm(s)
                bad.append("cell6: %r did not raise" % s)
            except ValueError:
                pass
    # 7 one entry point: the only reference to chain_events.build_runs in services/tape_live is inside wall_source.build_runs
    refs = []
    for path in _live_py():
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        owner = {}
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for n in ast.walk(fn):
                    owner[id(n)] = fn.name
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and n.attr == "build_runs" and isinstance(n.value, ast.Name) \
                    and n.value.id == "chain_events":
                refs.append((os.path.basename(path), owner.get(id(n), "<module>")))
    if refs != [("wall_source.py", "build_runs")]:
        bad.append("cell7: chain_events.build_runs referenced at %r, expected only wall_source.py build_runs" % (refs,))
    return not bad, "; ".join(bad[:6]) or "widths 0-6 -> {0,3,6}, same instants, hand-computed walls + OI, 7 digits raise, one entry point"


# --------------------------------------------------------------------- R-F step one (docs/tape/L2_rebuild_scope_plan.md section 4)
# The rebuilds the scope day must produce, as (trigger, at minute, symbol), written by hand from the plan table -- never by running
# the writer. 695 = 11:35 (b: NIFTY only), 725 = 12:05 (a: SENSEX only), 755 = 12:35 (c: both, once each), 785 = 13:05 (d: no
# change, no entry), 815 = 13:35 (e: one SENSEX token's metadata), 845 = 14:05 (f: SENSEX subscriptions + a late SENSEX segment).
SCOPE_REBUILDS = [("subscriptions", 695, "NIFTY"), ("subscriptions", 725, "SENSEX"), ("subscriptions", 755, "NIFTY"),
                  ("subscriptions", 755, "SENSEX"), ("subscriptions", 815, "SENSEX"), ("subscriptions", 845, "SENSEX")]
# The default fixture's raw + chain files, pinned by CONTENT: (file count, digest of the sorted "relpath sha256" lines with every
# .gz file gunzipped before hashing). Measured on the generator at 276e221 BEFORE the scope variant was added: the scope variant
# must leave the default day unchanged. The raw-byte digest of the compressed segments (Windows d9335e6b...) did NOT travel to
# Linux (box, Python 3.10: afd2f121..., same decompressed content), so it is reported for diagnosis and never compared.
DEFAULT_FIXTURE_CONTENT = (164, "a83d2adbaffe9b620a695d3d072f4c3a983ec59c39d2511a16e0f70df58494a8")


def _tree_digest(root):
    """-> (file count, content digest, raw-byte digest) over raw/ and chain/; the content digest gunzips .gz files first."""
    raw_items, con_items = [], []
    for sub in ("raw", "chain"):
        for dp, _ds, ns in os.walk(os.path.join(root, sub)):
            for n in ns:
                p = os.path.join(dp, n)
                rel = os.path.relpath(p, root).replace(os.sep, "/")
                b = rd(p)
                raw_items.append((rel, hashlib.sha256(b).hexdigest()))
                con_items.append((rel, hashlib.sha256(gzip.decompress(b) if n.endswith(".gz") else b).hexdigest()))

    def d(items):
        return hashlib.sha256("".join("%s %s\n" % i for i in sorted(items)).encode("utf-8")).hexdigest()
    return len(raw_items), d(con_items), d(raw_items)


def scope_fixture():
    if "scope" not in _CACHE:
        root = os.path.join(_TMP, "scope")
        f = gen_live.build(root, scope=True)
        from services.tape_offline import cycle_day, process_day
        out, cyc = os.path.join(root, "batch_out"), os.path.join(root, "batch_cyc")
        rc1, log1 = quiet(process_day.main, [f["raw"], "--day", DAY, "--out", out])
        rc2, log2 = quiet(cycle_day.main, ["--in", out, "--session", os.path.join(f["raw"], "session"), "--out", cyc])
        if rc1 != 0 or rc2 != 0:
            raise AssertionError("scope batch failed: %s %s\n%s\n%s" % (rc1, rc2, log1[-2000:], log2[-2000:]))
        f.update(cyc=cyc)
        _CACHE["scope"] = f
    return _CACHE["scope"]


def _scope_inprocess(f, swap):
    """Drive LiveDay as cli replay does (same events, same order, same grid), except that with swap=True the two SENSEX segments
    available at 14:05 are added in the order seg_1400, seg_1350 -- the order cli's sort can never produce."""
    import gzip
    cli, writer = mods()[0], mods()[5]
    segs, subs, _files = cli.plan_inputs(f["raw"], DAY, dict(gen_live.SCOPE_ARRIVAL))
    segs.sort(key=lambda e: (e[0], e[1], e[2], e[3]))
    subs.sort(key=lambda e: (e[0], e[1]))
    if swap:
        i = next(k for k, e in enumerate(segs) if e[4] == "SENSEX" and e[3] == "seg_1350.ndjson.gz")
        j = next(k for k, e in enumerate(segs) if e[4] == "SENSEX" and e[3] == "seg_1400.ndjson.gz")
        if not (segs[i][0] == segs[j][0] == 845 and i < j):
            raise AssertionError("scope day: seg_1350 / seg_1400 not both available at 14:05 in that order")
        segs[i], segs[j] = segs[j], segs[i]

    def reader(sym, name):
        with gzip.open(os.path.join(f["raw"], sym, DAY, name), "rb") as fh:
            for line in fh:
                yield line

    w = cli.special.special_window(DAY, None)
    ld = writer.LiveDay(DAY, reader, (w["open"], w["close"]) if w else None)
    grid = sorted(set(range(min(e[0] for e in segs + subs), max(e[0] for e in segs + subs) + 1, 5))
                  | set(range(writer.GRID_FIRST, writer.GRID_LAST + 1, 5)))
    si = ui = 0
    for t in grid:
        while ui < len(subs) and subs[ui][0] <= t:
            ld.add_subscriptions(subs[ui][2], subs[ui][3], t)
            ui += 1
        while si < len(segs) and segs[si][0] <= t:
            ld.add_segment(segs[si][4], segs[si][3], t)
            si += 1
        if t >= writer.GRID_FIRST:
            ld.cycle(t, {}, "")
    ld.cycle(None, {}, "")
    return ld


def g_rebuild_scope():
    bad = []
    ctl_root = os.path.join(_TMP, "scope_ctl")
    gen_live.build(ctl_root)
    n_f, content, raw_digest = _tree_digest(ctl_root)
    if (n_f, content) != DEFAULT_FIXTURE_CONTENT:
        bad.append("control: default fixture changed: (files, content digest) %r != %r (raw-byte digest %s, diagnosis only)" % (
            (n_f, content), DEFAULT_FIXTURE_CONTENT, raw_digest))
    f = scope_fixture()
    want_c = rd(os.path.join(f["cyc"], "tape_strike_cycle.csv"))
    want_e = rd(os.path.join(f["cyc"], "tape_events.csv"))
    cli = mods()[0]
    d = os.path.join(_TMP, "rp_scope")
    argv = ["replay", "--day", DAY, "--raw", f["raw"], "--out", d, "--arrival", arrival_file("scope", gen_live.SCOPE_ARRIVAL)]
    for p in f["chain"]:
        argv += ["--chain-runs", p]
    rc, log = quiet(cli.main, argv)
    if rc != 0:
        raise AssertionError("scope replay rc=%s\n%s" % (rc, log[-3000:]))
    with open(os.path.join(d, "run_manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    got = [(r["trigger"], r["at"], r["symbol"]) for r in man["rebuilds"]]
    if got != SCOPE_REBUILDS:
        bad.append("(1) rebuilds %s != expected %s" % (got, SCOPE_REBUILDS))
    lates = [x["symbol"] + "/" + x["segment"] for x in man["late_segments"]]
    if lates != ["SENSEX/seg_1350.ndjson.gz"]:
        bad.append("(1) late_segments %r != ['SENSEX/seg_1350.ndjson.gz']" % lates)
    if rd(os.path.join(d, "tape_live_cycle.csv")) != want_c:
        bad.append("(2) tape_live_cycle.csv != batch")
    if rd(os.path.join(d, "tape_live_events.csv")) != want_e:
        bad.append("(2) tape_live_events.csv != batch")
    rc_, re_ = _reconstruct(d)
    if rc_.encode("utf-8") != want_c or re_.encode("utf-8") != want_e:
        bad.append("(2) state rebuilt from the per-cycle deltas != batch")
    ld = _scope_inprocess(f, swap=True)
    got2 = [(r["trigger"], r["at"], r["symbol"]) for r in ld.rebuilds if r["at"] == 845]
    if got2 != [("subscriptions", 845, "SENSEX")]:
        bad.append("(3) f2 (seg_1400 before seg_1350 at 14:05): rebuilds at 845 = %s, want one SENSEX" % got2)
    if ld.state_cycle_csv().encode("utf-8") != want_c or ld.state_events_csv().encode("utf-8") != want_e:
        bad.append("(3) f2 final state != batch")
    n = want_c.count(b"\n") - 1
    return not bad, "; ".join(bad[:6]) or "6 rebuilds as written by hand (b,a,c,c,e,f; d none), live == batch byte for byte (%d cycle rows), f2 once, default fixture unchanged" % n


# =================================================================================== L2 live runner, Phase A
# docs/tape/L2_live_runner_plan.md sections 3, 5, 6, 7, 9, 12. Seven guards: equal, readonly, secrets, bounded-sql, keyset,
# lifecycle, restart. Everything runs on the generated fixture with a simulated clock; no network, no database, no S3.
RUN_MODS = ("services/tape_live/live_sources.py", "services/tape_live/live_runner.py", "services/tape_live/wall_source.py",
            "services/tape_live/cli.py")
NEW_FILES = RUN_MODS + ("tests/test_tape_live.py", "tests/tape_live_mutants.py", "tests/tape_live_runner_equal.py",
                        "tests/run_offline.sh", "docs/tape/L2_live_runner_plan.md", "docs/tape/L2_live_runner_install.md",
                        "docs/tape/L2_live_runner.service.template", "docs/tape/L2_live_runner.timer.template")
# A test credential, assembled so that no file carries it (or a URI with userinfo) as one literal.
TEST_PW = "Tq" + "7-x" + "Lp2v9-Rk"
TEST_DSN = "postgres" + "ql:" + "//" + "merdian_ro:" + TEST_PW + "@" + "db.example.invalid:5432/postgres?sslmode=require"
STDERR_MARK = "STDERR-" + "MARK-7731"
TIMING_FILES = ("heartbeat.json", "live_metrics.csv", "runner.log")


def rmods():
    from services.tape_live import live_runner, live_sources, wall_source
    return live_runner, live_sources, wall_source


def ist_epoch(m, secs=0, day=DAY):
    d = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=IST) + timedelta(minutes=m, seconds=secs)
    return d.timestamp()


def _hm_min(hhmm):
    return int(hhmm[:2]) * 60 + int(hhmm[3:5])


def code_sha_t():
    return mods()[0].code_info()["git_sha"]


def live_dir(root):
    return os.path.join(root, DAY, "live")


def _arr(spec):
    sym, seg, at = spec
    return {"%s/%s" % (sym, seg): at}


def runner_sim(name, arrival=None, out=None, start="08:50", events=(), hooks=None, rss_fn=None, chain_delay=None,
               objects_wrap=None, chain_wrap=None, fix=None, disk_floor=20.0):
    """The runner on the fixture day: LocalDirSource (cli's availability rule, + 2 s) + LocalChainSource + SimClock."""
    if out is None and name in _CACHE:
        return _CACHE[name]
    lr, ls, ws = rmods()
    f = fix or fixture()
    d = out or os.path.join(_TMP, "run_" + name)
    clock = lr.SimClock(ist_epoch(_hm_min(start)), list(events))
    vis = mods()[0].local_schedule(f["raw"], DAY, dict(arrival or {}))
    obj = ls.LocalDirSource(f["raw"], DAY, vis, clock)
    ch = ws.LocalChainSource(f["chain"], DAY, delay_fn=chain_delay)
    if objects_wrap:
        obj = objects_wrap(obj)
    if chain_wrap:
        ch = chain_wrap(ch)
    cfg = lr.Config(day=DAY, out=d, code_sha=code_sha_t(), kill_file=os.path.join(d, "KILL"),
                    disk_floor_mb=disk_floor, disk_stop_mb=disk_floor / 5.0)
    rc, log = quiet(lr.run_day, cfg, obj, ch, clock, hooks or {}, rss_fn or (lambda: 100.0))
    res = (rc, d, log)
    if out is None:
        _CACHE[name] = res
    return res


def _files(d):
    return sorted(os.path.relpath(os.path.join(dp, n), d).replace(os.sep, "/") for dp, _, ns in os.walk(d) for n in ns)


def compare_live(cdir, ldir):
    """cli replay out dir vs the runner's live dir: every file byte-equal (both shapes, live_run_id included: the epoch ids of
    plan section 4), except run_manifest.json, whose fields are compared."""
    bad = []
    fa = [x for x in _files(cdir) if x != "run_manifest.json"]
    fb = [x for x in _files(ldir) if x != "run_manifest.json"]
    if fa != fb:
        bad.append("file sets differ: only cli %s, only runner %s" % (sorted(set(fa) - set(fb))[:5], sorted(set(fb) - set(fa))[:5]))
    for rel in sorted(set(fa) & set(fb)):
        x, y = rd(os.path.join(cdir, rel)), rd(os.path.join(ldir, rel))
        if x != y:
            bad.append("differs: " + rel)
    try:
        with open(os.path.join(cdir, "run_manifest.json"), encoding="utf-8") as fh:
            ma = json.load(fh)
        with open(os.path.join(ldir, "run_manifest.json"), encoding="utf-8") as fh:
            mb = json.load(fh)
        for k in ("rebuilds", "late_segments", "bad_files", "token_map_conflicts", "label_counts", "rule_version", "epochs",
                  "epoch_log"):
            if k not in ma or ma.get(k) != mb.get(k):
                bad.append("manifest %s: cli %r runner %r" % (k, ma.get(k), mb.get(k)))
    except (OSError, ValueError) as exc:
        bad.append("manifest: %s" % exc)
    return bad


_REAL_DT = datetime


class _Strict310(_REAL_DT):
    """datetime whose fromisoformat has Python 3.10's limit: a fraction of 0, 3 or 6 digits and no other width (3.11+ accept any).
    cli_live_fake runs the fake under it (strict_iso), so a fake that hands an unpadded fraction to the parser fails on any
    interpreter as it did on the production box (3.10.12: 1028 of 1046 fake psql calls raised at 670ea84).
    A trailing Z is refused too: 3.10 rejects it (3.11+ accept it), and the real `aws s3api list-objects-v2` prints LastModified as
    '2026-11-06T03:25:03.000Z' (the production rehearsal of 2026-11-06 died on it at live_sources.py:191 under 3.10.12)."""

    @classmethod
    def fromisoformat(cls, s):
        if s.endswith(("Z", "z")):
            raise ValueError("Invalid isoformat string: %r (strict 3.10 stand-in: trailing Z)" % (s,))
        m = re.search(r"\.(\d+)", s)
        if m is not None and len(m.group(1)) not in (3, 6):
            raise ValueError("Invalid isoformat string: %r (strict 3.10 stand-in)" % (s,))
        return _REAL_DT.fromisoformat(s)


@contextlib.contextmanager
def strict_iso():
    """While the block runs, every `datetime` looked up in this module (the fakes) AND in the runner's source modules
    (services/tape_live/live_sources.py, wall_source.py) is the strict 3.10 stand-in, so the code under test parses as 3.10 does."""
    g = globals()
    _lr, ls, ws = rmods()
    saved = g["datetime"], ls.datetime, ws.datetime
    g["datetime"] = ls.datetime = ws.datetime = _Strict310
    try:
        yield
    finally:
        g["datetime"], ls.datetime, ws.datetime = saved


FAKE_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?([+-]\d{2}:\d{2})$")


def fake_pg_ts(s):
    """FakeShell's ONE timestamp parse. Postgres accepts a fraction of any width 0..6, so the fake pads it on the right to 6 digits
    (.5 -> .500000; never truncated, never rounded) before datetime parses it: Python 3.10 parses only 0, 3 or 6 digits."""
    m = FAKE_TS_RE.match(s)
    if m is None:
        raise ValueError("fake: timestamp %r is not YYYY-MM-DDTHH:MM:SS[.f]+HH:MM" % (s,))
    frac = "" if m.group(2) is None else "." + m.group(2).ljust(6, "0")
    return datetime.fromisoformat(m.group(1) + frac + m.group(3))


class FakeShell:
    """Stands in for the aws CLI and psql (live_sources.RUN). Its keyset, LIMIT and psql text shape are written here, not taken
    from services/tape_live. Records every call (argv, env, stdin) for the read-only and secrets checks."""

    def __init__(self, raw, chain_paths, schedule, psql_fail=None):
        self.calls = []
        self.vis = dict(schedule)
        self.files = {}
        for dp, _, ns in os.walk(raw):
            for n in ns:
                p = os.path.join(dp, n)
                rel = os.path.relpath(p, raw).replace(os.sep, "/")
                self.files[rel] = p
        self.rows = {}
        for p in chain_paths:
            with open(p, encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh):
                    self.rows.setdefault(r["symbol"], []).append(r)
        for s in self.rows:
            self.rows[s].sort(key=self.key)
        self.psql_fail = psql_fail
        self.md5 = {}
        self.raised = 0
        self.lm_shapes = {"Z": 0, "+00:00": 0}

    def _md5(self, rel):
        if rel not in self.md5:
            self.md5[rel] = hashlib.md5(rd(self.files[rel])).hexdigest()
        return self.md5[rel]

    @staticmethod
    def key(r):
        return (fake_pg_ts(r["ts"]), r["expiry_date"], float(r["strike"]), r["run_id"])

    @staticmethod
    def psql_shape(ts):
        d, rest = ts.split("T")
        clock, off = rest[:-6], rest[-6:]
        if off != "+00:00":
            raise AssertionError("fixture ts not UTC: %s" % ts)
        if "." in clock:
            clock = clock.rstrip("0").rstrip(".")
        return "%s %s+00" % (d, clock)

    def __call__(self, argv, env, stdin, timeout):
        try:
            return self._call(argv, env, stdin, timeout)
        except Exception:
            self.raised += 1
            raise

    def _call(self, argv, env, stdin, timeout):
        self.calls.append((list(argv), dict(env), stdin, timeout))
        if argv[:3] == ["aws", "s3api", "list-objects-v2"]:
            pre = argv[argv.index("--prefix") + 1]
            cont = []
            for i, (rel, p) in enumerate(sorted((r, q) for r, q in self.files.items() if r.startswith(pre))):
                vis = self.vis.get(rel, ist_epoch(16 * 60))
                if vis != int(vis):
                    raise AssertionError("fake: visibility %r is not whole seconds; the LastModified shapes below would drop it" % vis)
                # The two shapes the real CLI prints (production box, 2026-11-06): '2026-11-06T03:25:03.000Z' (millisecond
                # fraction, Z) and '2026-11-06T10:10:06+00:00'. Alternating, so every prefix listing carries both.
                clock = datetime.fromtimestamp(vis, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
                lm = clock + (".000Z" if i % 2 == 0 else "+00:00")
                self.lm_shapes["Z" if lm.endswith("Z") else "+00:00"] += 1
                cont.append({"Key": rel, "Size": os.path.getsize(p), "ETag": '"%s"' % self._md5(rel), "LastModified": lm})
            return 0, (json.dumps({"Contents": cont}) if cont else "").encode(), b""
        if argv[:3] == ["aws", "s3api", "get-object"]:
            key, dest = argv[argv.index("--key") + 1], argv[-1]
            shutil.copyfile(self.files[key], dest)
            return 0, json.dumps({"ETag": '"%s"' % self._md5(key)}).encode(), b""
        if argv and argv[0] == "psql":
            v = dict(argv[i + 1].split("=", 1) for i in range(len(argv) - 1) if argv[i] == "-v")
            sql = stdin.decode("utf-8")
            if self.psql_fail is not None:
                r = self.psql_fail(v, sql)
                if r is not None:
                    return r
            if "has_table_privilege" in sql:
                return 0, b"merdian_ro,on,f\n", b""
            until = fake_pg_ts(v["until"])
            cur = (fake_pg_ts(v["k_ts"]), v["k_exp"], float(v["k_strike"]), v["k_run"])
            rows = [r for r in self.rows.get(v["sym"], []) if fake_pg_ts(r["ts"]) <= until]
            if "count(*)" in sql:
                return 0, ("%d\n" % sum(1 for r in rows if self.key(r) <= cur)).encode(), b""
            rows = [r for r in rows if self.key(r) > cur][:5000]
            buf = io.StringIO()
            wr = csv.writer(buf, lineterminator="\n")
            for r in rows:
                wr.writerow([r["run_id"], r["symbol"], self.psql_shape(r["ts"]), r["expiry_date"], r["strike"], r["oi_call"],
                             r["oi_put"], r["gex_cr"]])
            return 0, buf.getvalue().encode(), b""
        raise AssertionError("FakeShell: unexpected argv %r" % (argv[:4],))


@contextlib.contextmanager
def _env(set_=None, drop=()):
    saved = dict(os.environ)
    try:
        for k in drop:
            os.environ.pop(k, None)
        os.environ.update(set_ or {})
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)


def cli_live_fake(name, psql_fail=None, extra_env=None):
    """cli live --source s3 --chain psql --clock sim on the fixture, through FakeShell. Cached by name."""
    if name in _CACHE:
        return _CACHE[name]
    cli = mods()[0]
    ls = rmods()[1]
    f = fixture()
    d = os.path.join(_TMP, "cli_" + name)
    fake = FakeShell(f["raw"], f["chain"], cli.local_schedule(f["raw"], DAY, {}), psql_fail)
    saved_run = ls.RUN
    ls.RUN = fake
    env = {"TAPE_LIVE_RO_DSN": TEST_DSN}
    env.update(extra_env or {})
    try:
        with _env(env, drop=("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")), strict_iso():
            rc, log = quiet(cli.main, ["live", "--day", DAY, "--out", d, "--source", "s3", "--chain", "psql", "--clock", "sim",
                                       "--start", "08:50", "--bucket", "meridian-tape-raw", "--disk-floor-mb", "20",
                                       "--rss-cap-mb", "100000"])
            dsn_left = "TAPE_LIVE_RO_DSN" in os.environ
    finally:
        ls.RUN = saved_run
    res = (rc, d, fake, log, dsn_left)
    _CACHE[name] = res
    return res


def _scope_cli():
    if "scope_cli" not in _CACHE:
        cli = mods()[0]
        f = scope_fixture()
        d = os.path.join(_TMP, "rp_scope_runner_eq")
        argv = ["replay", "--day", DAY, "--raw", f["raw"], "--out", d, "--arrival", arrival_file("scope_eq", gen_live.SCOPE_ARRIVAL)]
        for p in f["chain"]:
            argv += ["--chain-runs", p]
        rc, log = quiet(cli.main, argv)
        if rc != 0:
            raise AssertionError("scope replay rc=%s\n%s" % (rc, log[-2000:]))
        _CACHE["scope_cli"] = d
    return _CACHE["scope_cli"]


def _fake_ts_width():
    """Rule 0 on any interpreter for the fake's timestamp parsing (operator, 2026-11-11). Postgres accepts and emits a fraction of any
    width 0..6 (it trims trailing zeros), so the fake must parse every width. Under the strict 3.10 stand-in, seven rows whose ts
    carry fractions of width 0..6 are counted and paged with each row in turn as the cursor. By hand: '', .1, .12, .123, .1234,
    .12345, .123456 are 0, 100000, 120000, 123000, 123400, 123450, 123456 microseconds, strictly increasing, so with cursor = row w,
    count(*) = w + 1 and the page is rows w+1..6. Fails if the stand-in is not strict, if any call raises, or if a count or page is
    off."""
    bad = []
    try:
        _Strict310.fromisoformat("2026-11-06T03:45:21.5+00:00")
        bad.append("the strict stand-in accepted a 1-digit fraction (the check would be vacuous)")
    except ValueError:
        pass
    for ok in ("2026-11-06T03:45:21+00:00", "2026-11-06T03:45:21.500+00:00", "2026-11-06T03:45:21.500000+00:00"):
        try:
            _Strict310.fromisoformat(ok)
        except ValueError:
            bad.append("the strict stand-in refused %s" % ok)
    fr = ("", ".1", ".12", ".123", ".1234", ".12345", ".123456")
    rows = [{"run_id": "r%d" % w, "symbol": "NIFTY", "ts": "2026-11-06T03:45:21%s+00:00" % f, "expiry_date": "2026-11-10",
             "strike": "23500.0", "oi_call": "1", "oi_put": "1", "gex_cr": "0.000000"} for w, f in enumerate(fr)]
    fake = FakeShell.__new__(FakeShell)
    fake.calls, fake.psql_fail, fake.raised, fake.md5, fake.files, fake.vis = [], None, 0, {}, {}, {}
    with strict_iso():
        try:
            fake.rows = {"NIFTY": sorted(rows, key=fake.key)}
        except ValueError as exc:
            return bad + ["the fake's sort key raised: %s" % exc]
        for w, r in enumerate(rows):
            argv = ["psql"]
            for k, v in (("sym", "NIFTY"), ("until", "2026-11-06T10:00:00+00:00"), ("k_ts", r["ts"]), ("k_exp", r["expiry_date"]),
                         ("k_strike", r["strike"]), ("k_run", r["run_id"])):
                argv += ["-v", "%s=%s" % (k, v)]
            try:
                n = int(fake(argv, {}, b"SELECT count(*)", 15)[1].decode().strip())
                got = [ln.split(",")[0] for ln in fake(argv, {}, b"SELECT run_id", 15)[1].decode().splitlines() if ln]
            except Exception as exc:  # noqa: BLE001 - a raise is the finding
                bad.append("width %d: the fake raised %s: %s" % (w, type(exc).__name__, exc))
                continue
            want = ["r%d" % j for j in range(w + 1, len(fr))]
            if n != w + 1 or got != want:
                bad.append("width %d: count %d page %s, by hand %d %s" % (w, n, got, w + 1, want))
    return bad


# By hand (operator finding, production box 3.10.12, 2026-11-06): the real CLI prints these; Z becomes +00:00, the fraction is kept
# digit for digit, the instant is the one written. Expected instants are constructed here, not obtained by running the parser.
S3_LM_OK = (("2026-11-06T03:25:03.000Z", "2026-11-06T03:25:03.000+00:00", (2026, 11, 6, 3, 25, 3, 0)),
            ("2026-11-06T10:10:06.000Z", "2026-11-06T10:10:06.000+00:00", (2026, 11, 6, 10, 10, 6, 0)),
            ("2026-11-06T10:10:06+00:00", "2026-11-06T10:10:06+00:00", (2026, 11, 6, 10, 10, 6, 0)),
            ("2026-11-06T10:10:06Z", "2026-11-06T10:10:06+00:00", (2026, 11, 6, 10, 10, 6, 0)),
            ("2026-11-06T10:10:06.123Z", "2026-11-06T10:10:06.123+00:00", (2026, 11, 6, 10, 10, 6, 123000)),
            ("2026-11-06T10:10:06.999999+00:00", "2026-11-06T10:10:06.999999+00:00", (2026, 11, 6, 10, 10, 6, 999999)))
S3_LM_BAD = ("2026-11-06T10:10:06", "2026-11-06T10:10:06+05:30", "2026-11-06T10:10:06+00", "2026-11-06 10:10:06+00:00",
             "2026-11-06T10:10:06.5Z", "2026-11-06T10:10:06.1234Z", "2026-11-06T10:10:06z", " 2026-11-06T10:10:06Z",
             "2026-11-06T10:10:06Z\n", "", None)


def _s3_lm_vectors():
    """Rule 0 for the S3 LastModified normaliser: each accepted shape -> the exact string by hand and, through the strict 3.10
    stand-in, the instant by hand; each refused shape -> SourceError('other') and nothing else. Fails if the normaliser is
    removed, rounds or truncates a fraction, keeps a Z, or lets an unexpected shape through."""
    ls = rmods()[1]
    bad = []
    for raw, want, parts in S3_LM_OK:
        try:
            got = ls.s3_last_modified_iso(raw)
        except Exception as exc:  # noqa: BLE001
            bad.append("%r raised %s" % (raw, type(exc).__name__))
            continue
        if got != want:
            bad.append("%r -> %r, want %r" % (raw, got, want))
            continue
        try:
            inst = _Strict310.fromisoformat(got)
        except ValueError:
            bad.append("%r -> %r does not parse under the strict 3.10 stand-in" % (raw, got))
            continue
        if inst != _REAL_DT(*parts, tzinfo=timezone.utc):
            bad.append("%r -> instant %s, want %r" % (raw, inst, parts))
    for raw in S3_LM_BAD:
        try:
            got = ls.s3_last_modified_iso(raw)
            bad.append("%r accepted as %r (want SourceError other)" % (raw, got))
        except ls.SourceError as exc:
            if exc.category != "other":
                bad.append("%r refused with category %r, want 'other'" % (raw, exc.category))
        except Exception as exc:  # noqa: BLE001
            bad.append("%r raised %s, want SourceError" % (raw, type(exc).__name__))
    return bad


def _hb_last_error(root):
    """heartbeat.json last_error of a cli live run (the runner records a fatal as 'Type at file:line'); '' when absent."""
    try:
        with open(os.path.join(root, DAY, "heartbeat.json"), encoding="utf-8") as fh:
            return json.load(fh).get("last_error", "")
    except (OSError, ValueError):
        return ""


def g_runner_equal():
    bad, notes = [], []
    variants = (("clean", None, replay("clean"), None), ("late", _arr(gen_live.LATE_SEG), late_replay(), None),
                ("out-of-order", _arr(gen_live.LATE_SEG_OOO), ooo_replay(), None),
                ("scope", gen_live.SCOPE_ARRIVAL, _scope_cli(), scope_fixture()))
    for name, arr, cdir, fix in variants:
        rc, root, log = runner_sim("eq_" + name, arr, fix=fix)
        if rc != 0:
            bad.append("%s: runner rc=%s %s" % (name, rc, log[-800:]))
            continue
        diff = compare_live(cdir, live_dir(root))
        bad += ["%s: %s" % (name, x) for x in diff]
        notes.append("%s %d files" % (name, len(_files(live_dir(root)))))
    bad += ["fake ts width: %s" % x for x in _fake_ts_width()]
    rc, root, fake, log, _left = cli_live_fake("eq_psql")
    if rc != 0:
        bad.append("psql path: cli live rc=%s last_error=%r %s" % (rc, _hb_last_error(root), log[-800:]))
    else:
        n_psql = sum(1 for c in fake.calls if c[0][:1] == ["psql"])
        if fake.raised != 0:
            bad.append("psql path: the fake raised %d calls (%d psql calls), want 0" % (fake.raised, n_psql))
        with open(os.path.join(root, DAY, "heartbeat.json"), encoding="utf-8") as fh:
            hb_db = json.load(fh)["errors"]["db"]
        if hb_db != 0:
            bad.append("psql path: heartbeat errors.db = %d, want 0" % hb_db)
        with open(os.path.join(root, DAY, "live_metrics.csv"), encoding="utf-8", newline="") as fh:
            m_err = sum(int(r["errors"]) for r in csv.DictReader(fh))
        if m_err != 0:
            bad.append("psql path: live_metrics.csv errors over all cycles = %d, want 0 (no per-kind column; db is one kind)" % m_err)
        bad += ["psql path: %s" % x for x in compare_live(replay("clean"), live_dir(root))]
        kinds = {tuple(c[0][:3]) if c[0][0] == "aws" else ("psql",) for c in fake.calls}
        if not {("aws", "s3api", "list-objects-v2"), ("aws", "s3api", "get-object"), ("psql",)} <= kinds:
            bad.append("psql path did not exercise list, get and psql: %r" % sorted(kinds))
        notes.append("psql/S3 path %d shell calls, fake raised 0, heartbeat errors.db 0, metrics errors 0" % len(fake.calls))
        if fake.lm_shapes["Z"] == 0 or fake.lm_shapes["+00:00"] == 0:
            bad.append("S3 LastModified: the fake listed %r; both real shapes must occur (the check would be vacuous)" % fake.lm_shapes)
        notes.append("S3 LastModified listed as .000Z x%d and +00:00 x%d" % (fake.lm_shapes["Z"], fake.lm_shapes["+00:00"]))
    try:
        _Strict310.fromisoformat("2026-11-06T03:25:03.000Z")
        bad.append("the strict stand-in accepted a trailing Z (the S3 LastModified check would be vacuous)")
    except ValueError:
        pass
    bad += ["S3 LastModified: %s" % x for x in _s3_lm_vectors()]
    notes.append("S3 LastModified normaliser: %d hand vectors under the strict stand-in" % (len(S3_LM_OK) + len(S3_LM_BAD)))
    notes.append("fake parses ts fractions of width 0-6 under the strict 3.10 stand-in")
    return not bad, "; ".join(bad[:8]) or "runner == cli replay byte for byte, both shapes, epoch ids included: " + ", ".join(notes)


def _consts(path):
    """Non-docstring string constants of a module, with line numbers."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    docs = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and n.body:
            b = n.body[0]
            if isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant) and isinstance(b.value.value, str):
                docs.add(id(b.value))
    return tree, [(n.lineno, n.value) for n in ast.walk(tree)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]


S3_WRITE = {"cp", "sync", "mv", "rm", "put", "put-object", "delete-object", "delete-objects", "copy-object", "upload-part",
            "create-multipart-upload", "complete-multipart-upload", "presign", "restore-object"}
SQL_WRITE = re.compile(r"(?i)\b(INSERT|UPDATE|DELETE|COPY|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|MERGE|CALL|VACUUM|"
                       r"REINDEX|CLUSTER|LOCK|NOTIFY|DO)\b")
CRED_NAME = re.compile(r"(?i)(pass|pwd|secret|token|dsn|credential|api_?key|access_key)")
NET_MODS = ("socket", "http", "urllib.request", "ssl", "ftplib", "smtplib", "telnetlib", "xmlrpc", "asyncio", "requests")


def _names_in(node):
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            out.append(n.id)
        elif isinstance(n, ast.Attribute):
            out.append(n.attr)
    return out


def _probe_const(tree):
    """The one exempted constant: the privilege list of the start-up refusal query (wall_source.WRITE_PRIVS_PROBE)."""
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "WRITE_PRIVS_PROBE" for t in n.targets):
            if isinstance(n.value, ast.Constant):
                return n.value.value
    return None


def argv_shape_ok(a):
    t = ["--cli-read-timeout", "10", "--cli-connect-timeout", "5"]
    if a[:3] == ["aws", "s3api", "list-objects-v2"]:
        return (len(a) == 13 and a[3] == "--bucket" and a[5] == "--prefix" and a[7:9] == ["--output", "json"] and a[9:] == t
                and re.match(r"^(NIFTY|SENSEX|session)/\d{4}-\d{2}-\d{2}/$", a[6]) is not None)
    if a[:3] == ["aws", "s3api", "get-object"]:
        return (len(a) == 12 and a[3] == "--bucket" and a[5] == "--key" and a[7:11] == t
                and re.match(r"^(NIFTY|SENSEX|session)/\d{4}-\d{2}-\d{2}/[A-Za-z0-9_.]+$", a[6]) is not None)
    if a and a[0] == "psql":
        if a[1:7] != ["-X", "-q", "-t", "--csv", "-v", "ON_ERROR_STOP=1"] or a[-2:] != ["-f", "-"]:
            return False
        mid = a[7:-2]
        if len(mid) % 2:
            return False
        for i in range(0, len(mid), 2):
            if mid[i] != "-v" or mid[i + 1].split("=", 1)[0] not in ("sym", "day", "until", "k_ts", "k_exp", "k_strike",
                                                                       "k_run", "privs"):
                return False
        return True
    return False


def g_runner_readonly():
    bad = []
    for rel in RUN_MODS:
        p = os.path.join(ROOT, rel)
        tree, consts = _consts(p)
        probe = _probe_const(tree)
        for ln, s in consts:
            if s.strip().lower() in S3_WRITE:
                bad.append("%s:%d S3 write verb %r" % (rel, ln, s))
            if s != probe and SQL_WRITE.search(s):
                bad.append("%s:%d SQL write keyword in %r" % (rel, ln, s[:60]))
        for n in ast.walk(tree):
            if isinstance(n, ast.Call):
                fn = n.func
                fname = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
                owner = fn.value.id if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) else ""
                for kw in n.keywords:
                    if kw.arg == "shell" and not (isinstance(kw.value, ast.Constant) and kw.value.value is False):
                        bad.append("%s:%d shell= is not False" % (rel, n.lineno))
                if owner == "os" and fname in ("system", "popen", "execv", "execve", "execvp", "spawnv", "spawnl"):
                    bad.append("%s:%d os.%s" % (rel, n.lineno, fname))
                if owner == "subprocess" and fname != "run":
                    bad.append("%s:%d subprocess.%s (only subprocess.run is allowed)" % (rel, n.lineno, fname))
                if owner == "subprocess" and fname == "run" and not any(k.arg == "timeout" for k in n.keywords):
                    bad.append("%s:%d subprocess.run without timeout=" % (rel, n.lineno))
                if isinstance(fn, ast.Attribute) and fn.attr == "format":
                    for w in _names_in(ast.Tuple(elts=list(n.args) + [k.value for k in n.keywords], ctx=ast.Load())):
                        if CRED_NAME.search(w):
                            bad.append("%s:%d .format of %r" % (rel, n.lineno, w))
            if isinstance(n, ast.JoinedStr):
                for w in _names_in(n):
                    if CRED_NAME.search(w):
                        bad.append("%s:%d f-string of %r" % (rel, n.lineno, w))
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) and isinstance(n.left, ast.Constant) \
                    and isinstance(n.left.value, str):
                for w in _names_in(n.right):
                    if CRED_NAME.search(w):
                        bad.append("%s:%d %%-format of %r" % (rel, n.lineno, w))
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                ms = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
                for m in ms:
                    if any(m == x or m.startswith(x + ".") for x in NET_MODS):
                        bad.append("%s:%d imports network module %r" % (rel, n.lineno, m))
    # runtime: every argv the runner built on the fixture day (S3 + psql path)
    rc, root, fake, log, _left = cli_live_fake("eq_psql")
    if rc != 0:
        bad.append("runtime run rc=%s" % rc)
    nbad = 0
    for argv, env, stdin, timeout in fake.calls:
        if not argv_shape_ok(argv):
            nbad += 1
            if nbad <= 3:
                bad.append("argv shape not allowed: %r" % (argv[:8],))
        if any(TEST_PW in x or "PGPASSWORD" in x for x in argv):
            bad.append("credential in argv: %r" % (argv[:3],))
        if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 60:
            bad.append("call without a bounded timeout: %r" % (argv[:3],))
    return not bad, "; ".join(bad[:8]) or "%d modules scanned; %d runtime calls, all of the 3 allowed shapes, no credential" % (
        len(RUN_MODS), len(fake.calls))


def _secret_patterns():
    j = "".join
    return [("uri-userinfo", re.compile(j([r"[a-z][a-z0-9+.-]*", ":", "//", r"[^\s/:@'\"<>]+:[^\s/@'\"<>]+@"]))),
            ("password-assign", re.compile(j([r"(?i)\bpass", r"(word|wd)?\s*[:=]\s*['\"][^'\"\s]{3,}['\"]"]))),
            ("env-password", re.compile(j([r"(?im)^\s*[A-Z_]*PASS", r"(WORD)?\s*=\s*\S+"]))),
            ("jwt", re.compile(j(["ey", r"J[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"]))),
            ("aws-key-id", re.compile(j([r"\b(AK", r"IA|AS", r"IA)[0-9A-Z]{16}\b"]))),
            ("aws-secret", re.compile(j([r"(?i)aws_secret_", r"access_key\s*[=:]\s*\S{8,}"]))),
            ("supabase-key", re.compile(j([r"\bsb_(sec", r"ret|publishable)_[A-Za-z0-9_-]{10,}|\bsb", r"p_[0-9a-f]{20,}"]))),
            ("privileged-role-name", re.compile(j(["(?i)service", "[_ -]", "role"]))),
            ("private-key", re.compile(j(["-----BEGIN ", "[A-Z ]*PRIVATE", " KEY-----"]))),
            ("test-credential", re.compile(re.escape(TEST_PW)))]


def g_runner_secrets():
    bad = []
    pats = _secret_patterns()
    for rel in NEW_FILES:
        p = os.path.join(ROOT, rel)
        if not os.path.isfile(p):
            bad.append("missing %s" % rel)
            continue
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        for name, rx in pats:
            for m in rx.finditer(text):
                bad.append("%s:%d %s" % (rel, text.count("\n", 0, m.start()) + 1, name))
    # runtime 1: psql fails with the credential and a marker in stderr, and once by raising with the credential in the message
    def fail(v, sql):
        if "count(*)" in sql and v.get("sym") == "NIFTY":
            return 2, b"", ("FATAL: %s %s %s" % (TEST_PW, TEST_DSN, STDERR_MARK)).encode()    # (rc, stdout, STDERR)
        if "count(*)" in sql and v.get("sym") == "SENSEX" and v.get("until", "") > "2026-11-06T05":
            raise OSError("exec failed near " + TEST_PW + " " + STDERR_MARK)
        return None
    rc, root, fake, log, dsn_left = cli_live_fake("sec_fail", psql_fail=fail)
    if rc != 0:
        bad.append("failing-psql run rc=%s (a failed read must not end the day)" % rc)
    blobs = [("log", log.encode("utf-8"))]
    for rel in _files(os.path.join(root, DAY)):
        if not rel.startswith("raw/"):
            blobs.append((rel, rd(os.path.join(root, DAY, rel))))
    for name, b in blobs:
        for needle in (TEST_PW, STDERR_MARK, TEST_DSN):
            if needle.encode() in b:
                bad.append("%s contains %s" % (name, "the credential" if needle == TEST_PW else
                                               ("raw stderr" if needle == STDERR_MARK else "the DSN")))
    with open(os.path.join(root, DAY, "heartbeat.json"), encoding="utf-8") as fh:
        hb = json.load(fh)
    if not hb.get("errors", {}).get("db"):
        bad.append("the failing psql was not counted in heartbeat errors.db (the check would be vacuous)")
    if dsn_left:
        bad.append("TAPE_LIVE_RO_DSN still in os.environ after start")
    for argv, env, _stdin, _t in fake.calls:
        if argv[0] == "aws" and any(k.startswith("PG") or TEST_PW in str(v) for k, v in env.items()):
            bad.append("aws child env carries PG* / the credential")
            break
    for argv, env, _stdin, _t in fake.calls:
        if argv[0] == "psql" and any(k.startswith("AWS_ACCESS") or k.startswith("AWS_SECRET") or k == "TAPE_LIVE_RO_DSN"
                                     for k in env):
            bad.append("psql child env carries AWS keys or the DSN variable")
            break
    if not any(argv[0] == "psql" and env.get("PGPASSWORD") == TEST_PW for argv, env, _s, _t in fake.calls):
        bad.append("psql never received the credential through its environment (wiring broken; check vacuous)")
    # runtime 2: refuses AWS keys in its environment, without echoing the value
    keyval = "AK" + "IA" + "TESTONLY0000ZZZZ"
    cli = mods()[0]
    d = os.path.join(_TMP, "cli_awskey")
    with _env({"TAPE_LIVE_RO_DSN": TEST_DSN, "AWS_ACCESS_KEY_ID": keyval}):
        rc2, log2 = quiet(cli.main, ["live", "--day", DAY, "--out", d, "--source", "s3", "--chain", "psql", "--clock", "sim",
                                     "--start", "08:50"])
    if rc2 != 2:
        bad.append("AWS_ACCESS_KEY_ID set: rc=%s, want 2 (refused)" % rc2)
    if keyval in log2 or TEST_PW in log2:
        bad.append("refusal message echoes a credential")
    return not bad, "; ".join(bad[:8]) or "%d files clean of %d patterns; stderr and exceptions scrubbed; env allowlists hold; AWS keys refused" % (
        len(NEW_FILES), len(pats))


SNAP_COLS = ("run_id", "symbol", "ts", "expiry_date", "strike", "oi_call", "oi_put", "gex_cr")


def g_runner_bounded_sql():
    bad = []
    ws, ls = rmods()[2], rmods()[1]
    named = {"SNAPSHOT_SQL": ws.SNAPSHOT_SQL, "COUNT_SQL": ws.COUNT_SQL, "CHECK_SQL": ws.CHECK_SQL}
    # the runner's modules only: ddl.py renders the offline SQL file and is not a path the runner can reach
    for rel in RUN_MODS + ("services/tape_live/live_sources.py",):
        tree, consts = _consts(os.path.join(ROOT, rel))
        for ln, s in consts:
            if re.search(r"(?i)\bselect\b", s) and s not in named.values():
                bad.append("%s:%d SQL text outside the named queries: %r" % (rel, ln, s[:60]))
    for name, sql in named.items():
        if re.search(r"(?i)\bselect\s+\*", sql) or re.search(r"(?i)\.\*", sql):
            bad.append("%s selects *" % name)
        if "SET LOCAL statement_timeout = '8s';" not in sql:
            bad.append("%s: no 8 s statement_timeout" % name)
        if not re.search(r"(?i)^BEGIN TRANSACTION READ ONLY;", sql.strip()) or not sql.strip().endswith("COMMIT;"):
            bad.append("%s: not one READ ONLY transaction" % name)
    for name in ("SNAPSHOT_SQL", "COUNT_SQL"):
        sql = named[name]
        for need in ("FROM public.gex_strike_snapshots", "symbol = :'sym'",
                     "ts >= (:'day')::date::timestamp AT TIME ZONE 'Asia/Kolkata'",
                     "ts < ((:'day')::date + 1)::timestamp AT TIME ZONE 'Asia/Kolkata'", "ts <= (:'until')::timestamptz"):
            if need not in sql:
                bad.append("%s lacks %r" % (name, need))
    tup = "(ts, expiry_date, strike, run_id::text)"
    cur = "((:'k_ts')::timestamptz, (:'k_exp')::date, (:'k_strike')::numeric, :'k_run')"
    s = ws.SNAPSHOT_SQL
    m = re.search(r"(?is)SELECT\s+(.*?)\s+FROM", s)
    if not m or tuple(c.strip() for c in m.group(1).split(",")) != SNAP_COLS:
        bad.append("SNAPSHOT_SQL column list is not exactly %s" % (SNAP_COLS,))
    if "AND %s > %s" % (tup, cur) not in s:
        bad.append("SNAPSHOT_SQL keyset predicate is not the strict tuple %s > cursor" % tup)
    if "ORDER BY ts, expiry_date, strike, run_id::text" not in s:
        bad.append("SNAPSHOT_SQL ORDER BY is not the keyset tuple")
    lim = re.findall(r"(?i)\bLIMIT\s+(\d+)\s*;", s)
    if len(lim) != 1 or not 1 <= int(lim[0]) <= 5000 or int(lim[0]) != ws.PAGE_LIMIT:
        bad.append("SNAPSHOT_SQL LIMIT %r (want one LIMIT == PAGE_LIMIT <= 5000)" % (lim,))
    c = ws.COUNT_SQL
    m = re.search(r"(?is)SELECT\s+(.*?)\s+FROM", c)
    if not m or m.group(1).strip() != "count(*)":
        bad.append("COUNT_SQL does not select exactly count(*)")
    if "AND %s <= %s" % (tup, cur) not in c:
        bad.append("COUNT_SQL keyset predicate is not tuple <= cursor")
    if "FROM" in ws.CHECK_SQL.upper():
        bad.append("CHECK_SQL reads a relation")
    env = ls.pg_env({"PATH": "x"}, ls.parse_dsn(TEST_DSN))
    if env.get("PGOPTIONS") != "-c default_transaction_read_only=on -c statement_timeout=8000":
        bad.append("PGOPTIONS %r" % env.get("PGOPTIONS"))
    if env.get("PGCONNECT_TIMEOUT") != "5":
        bad.append("PGCONNECT_TIMEOUT %r" % env.get("PGCONNECT_TIMEOUT"))
    if not 0 < ls.PSQL_TIMEOUT_S <= 15 or not 0 < ls.LIST_TIMEOUT_S <= 30 or not 0 < ls.GET_TIMEOUT_S <= 60:
        bad.append("timeouts %s/%s/%s" % (ls.PSQL_TIMEOUT_S, ls.LIST_TIMEOUT_S, ls.GET_TIMEOUT_S))
    return not bad, "; ".join(bad[:8]) or "3 named queries: explicit columns (count(*) only in the count query), day/until/keyset bounds, LIMIT %d, 8 s timeout, read-only" % ws.PAGE_LIMIT


# ---------------------------------------------------------------- keyset
def _keyset_rows():
    """Planted chain rows for one symbol: ts ties across two expiries and many strikes, so 7-row pages split inside a tie."""
    rows = []
    for i, m in enumerate((600, 605, 610, 615, 620)):
        ts = datetime.fromtimestamp(ist_epoch(m, 21.5), timezone.utc).isoformat()
        for exp in ("2026-11-09", "2026-11-16"):
            for k in (23400, 23450, 23500, 23550, 23600, 23650, 23700):
                rows.append({"run_id": "%08d-0000-4000-8000-000000000000" % i, "symbol": "NIFTY", "ts": ts, "expiry_date": exp,
                             "strike": "%.1f" % k, "oi_call": str(1000 + k), "oi_put": str(2000 + k), "gex_cr": "0.1"})
    return rows


class KeysetTable:
    """Test-side table: visibility by a per-row commit time, strict tuple >, LIMIT. Written here, independently."""

    def __init__(self, rows, commit):
        self.rows, self.commit = rows, commit
        self.pages = []

    @staticmethod
    def key(r):
        return (datetime.fromisoformat(r["ts"]), r["expiry_date"], float(r["strike"]), r["run_id"])

    def _cur(self, c):
        return (datetime.fromisoformat(c[0]), c[1], float(c[2]), c[3])

    def read_page(self, sym, cursor, until, limit):
        cur = self._cur(cursor)
        out = sorted((r for r in self.rows if r["symbol"] == sym and self.commit(r) <= until and self.key(r) > cur), key=self.key)
        page = [dict(r) for r in out[:limit]]
        self.pages.append(page)
        return page

    def count_upto(self, sym, cursor, until):
        cur = self._cur(cursor)
        return sum(1 for r in self.rows if r["symbol"] == sym and self.commit(r) <= until and self.key(r) <= cur)


class RecordingChain:
    def __init__(self, inner):
        self.inner, self.pages = inner, []

    def read_page(self, sym, cursor, until, limit):
        page = self.inner.read_page(sym, cursor, until, limit)
        self.pages.append([dict(r) for r in page])
        return page

    def count_upto(self, sym, cursor, until):
        return self.inner.count_upto(sym, cursor, until)


def _keyset_case(make_src, label):
    lr, ls, ws = rmods()
    bad = []
    rows = _keyset_rows()                                           # 70 rows
    late = rows[5]                                                  # sorts low (first run), committed late
    t_all = ist_epoch(700)

    def commit(r):
        return t_all + 600 if r is late else ist_epoch(600)
    src = RecordingChain(make_src(rows, commit))
    counters = {}
    poller = lr.ChainPoller(src, DAY, limit=7, max_pages=8, counters=counters)
    k = KeysetTable.key

    def raw(pages):
        return [k(r) for p in pages for r in p]
    want = sorted(k(r) for r in rows if r is not late)
    # poll 1: 69 visible rows, 8 pages x 7 = 56, stops at max_pages
    poller.poll("NIFTY", t_all)
    got1 = raw(src.pages)
    if got1 != want[:56]:
        bad.append("%s poll 1: %d rows, want the first 56 in order" % (label, len(got1)))
    if len(src.pages) != 8:
        bad.append("%s poll 1: %d pages, want 8 (max_pages)" % (label, len(src.pages)))
    n1 = len(src.pages)
    poller.poll("NIFTY", t_all)                                     # resumes: 7, 6 (short page ends the poll)
    got2 = raw(src.pages[n1:])
    if got1 + got2 != want:
        bad.append("%s polls 1+2: concatenation != the full ordered set (dups %d, missing %d)" % (
            label, len(got1 + got2) - len(set(got1 + got2)), len(set(want) - set(got1 + got2))))
    if poller.cursor["NIFTY"] != ws.cursor_of(max(rows, key=k) if True else None):
        bad.append("%s cursor %r != last row" % (label, poller.cursor["NIFTY"]))
    if counters.get("chain_skipped"):
        bad.append("%s count check fired with nothing skipped" % label)
    # the late commit below the cursor: the count check must fire once, reset, and recover it with no duplicate kept
    poller.poll("NIFTY", t_all + 700)
    if counters.get("chain_skipped") != 1:
        bad.append("%s late commit below the cursor: chain_skipped=%r, want 1" % (label, counters.get("chain_skipped")))
    poller.poll("NIFTY", t_all + 700)
    held = sorted(k(r) for r in poller.acc.rows_of("NIFTY"))
    if held != sorted(k(r) for r in rows):
        bad.append("%s after recovery: %d rows held, want %d distinct" % (label, len(held), len(rows)))
    return bad


def g_runner_keyset():
    ws = rmods()[2]
    bad = _keyset_case(lambda rows, commit: KeysetTable(rows, commit), "table")

    def local(rows, commit):
        d = os.path.join(_TMP, "keyset_csv")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "rows.csv")
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(SNAP_COLS), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        late_key = KeysetTable.key(rows[5])
        return ws.LocalChainSource([p], DAY, delay_fn=lambda r: 6300 if KeysetTable.key(r) == late_key else 0,
                                   visible_from=lambda r: ist_epoch(600) - 1)
    bad += _keyset_case(local, "LocalChainSource")
    return not bad, "; ".join(bad[:8]) or "7-row pages through ts ties: no overlap, no gap, 8-page cap resumes, late commit below cursor recovered once (in-test table and LocalChainSource)"


# ---------------------------------------------------------------- lifecycle
def _hb(root):
    with open(os.path.join(root, DAY, "heartbeat.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _state(root):
    with open(os.path.join(root, DAY, "state.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _delta_names(root):
    d = os.path.join(live_dir(root), "cycles")
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


HB_FIELDS = ("state", "day", "last_cycle", "last_cycle_wall_s", "lag_s", "peak_rss_mb", "rss_mb", "errors", "last_error", "pid",
             "code_sha", "updated_utc")


def g_runner_lifecycle():
    lr, ls, ws = rmods()
    bad = []
    # (1) full day: heartbeat after every cycle, self-exit after 15:45, nothing later
    seen = []

    def after_cycle(t, runner):
        seen.append((t, _hb(runner.cfg.out)))
    rc, root, log = runner_sim("lc_full", out=os.path.join(_TMP, "lc_full"), hooks={"after_cycle": after_cycle})
    if rc != 0:
        bad.append("full day rc=%s" % rc)
    for t, hb in seen:
        miss = [k for k in HB_FIELDS if k not in hb]
        if miss or hb["last_cycle"] != "%02d:%02d" % (t // 60, t % 60):
            bad.append("heartbeat after %d: missing %s, last_cycle %r" % (t, miss, hb.get("last_cycle")))
            break
    ts = [t for t, _ in seen]
    if not ts or ts[-1] != 15 * 60 + 45 or any(b - a != 5 for a, b in zip(ts, ts[1:])):
        bad.append("cycles %s..%s, want every 5 min ending 15:45" % (ts[:1], ts[-1:]))
    hb = _hb(root)
    if hb["state"] != "done":
        bad.append("end state %r, want done" % hb["state"])
    if lr.SimClock.last_now is not None and lr.SimClock.last_now >= ist_epoch(15 * 60 + 50):
        bad.append("the runner was still awake at or after 15:50")
    # (2) kill switch at 10:02 -> exit 0 at the next check, nothing after 10:00
    dk = os.path.join(_TMP, "lc_kill")

    def kill():
        with open(os.path.join(dk, "KILL"), "w") as fh:
            fh.write("")
    rc, root, log = runner_sim("lc_kill", out=dk, events=[(ist_epoch(10 * 60 + 2), kill)])
    if rc != 0 or _hb(root)["state"] != "killed":
        bad.append("kill switch: rc=%s state=%r" % (rc, _hb(root).get("state")))
    late = [n for n in _delta_names(root) if n[:4].isdigit() and n[:4] > "1000"]
    if late or _state(root).get("committed") != 600:
        bad.append("kill switch: cycles after 10:00 %s, committed %r" % (late[:3], _state(root).get("committed")))
    # (3) MemoryError -> exit 3, state memory_error
    def boom(t, runner):
        if t == 660:
            raise MemoryError()
    rc, root, log = runner_sim("lc_mem", out=os.path.join(_TMP, "lc_mem"), hooks={"before_cycle": boom})
    if rc != 3 or _hb(root)["state"] != "memory_error":
        bad.append("MemoryError: rc=%s state=%r, want 3 memory_error" % (rc, _hb(root).get("state")))
    # (4) RSS over the soft cap -> exit 3, state memory_cap
    clk = {}

    def rss():
        return 700.0 if clk.get("t", 0) >= 660 else 100.0

    def mark(t, runner):
        clk["t"] = t
    rc, root, log = runner_sim("lc_rss", out=os.path.join(_TMP, "lc_rss"), hooks={"before_cycle": mark}, rss_fn=rss)
    if rc != 3 or _hb(root)["state"] != "memory_cap":
        bad.append("RSS cap: rc=%s state=%r, want 3 memory_cap" % (rc, _hb(root).get("state")))
    # (5) one failed S3 list at 10:00: counted, the cycle still runs, the next wake recovers, no tight retry
    calls = {"n": 0, "failed": 0}

    class FlakyList:
        def __init__(self, inner):
            self.inner = inner

        def list(self, prefix):
            calls["n"] += 1
            if prefix.startswith("NIFTY/") and not calls["failed"] and self.inner.clock.now() >= ist_epoch(600):
                calls["failed"] = 1
                raise ls.SourceError("connect")
            return self.inner.list(prefix)

        def get(self, key, dest):
            return self.inner.get(key, dest)
    wakes = []
    rc, root, log = runner_sim("lc_flaky", out=os.path.join(_TMP, "lc_flaky"), objects_wrap=FlakyList,
                               hooks={"after_wake": lambda t, r: wakes.append(t)})
    hb = _hb(root)
    if rc != 0 or hb["errors"].get("s3_list") != 1:
        bad.append("flaky list: rc=%s errors.s3_list=%r, want 1" % (rc, hb["errors"].get("s3_list")))
    if calls["n"] != 3 * len(wakes):
        bad.append("flaky list: %d list calls for %d wakes (want exactly 3 per wake: no retry loop)" % (calls["n"], len(wakes)))
    if "1000_cycle.csv" not in _delta_names(root) and "1000_events.csv" not in _delta_names(root):
        rows = rd(os.path.join(root, DAY, "live_metrics.csv")).decode()
        if "\n%s,10:00," % DAY not in rows:
            bad.append("flaky list: no cycle recorded at 10:00")
    # (5b) free disk below the floor at start -> refused with exit 3 and state disk_floor, before any object is fetched
    rc, root, log = runner_sim("lc_disk", out=os.path.join(_TMP, "lc_disk"), disk_floor=10 ** 9)
    if rc != 3 or _hb(root)["state"] != "disk_floor" or os.path.exists(os.path.join(root, DAY, "arrival_log.csv")):
        bad.append("disk floor: rc=%s state=%r (want 3 disk_floor, nothing fetched)" % (rc, _hb(root).get("state")))
    # (6) chain wait: at most 8 polls; a run delayed past the deadline -> the older run's id, empty readiness lag
    polls = {}

    class CountPolls:
        def __init__(self, inner):
            self.inner = inner

        def read_page(self, sym, cursor, until, limit):
            return self.inner.read_page(sym, cursor, until, limit)

        def count_upto(self, sym, cursor, until):
            polls.setdefault(until // 300, set()).add(until)
            return self.inner.count_upto(sym, cursor, until)
    late_run = ist_epoch(630, 21.5)

    def delay(r):
        return 400 if r["symbol"] == "NIFTY" and abs(datetime.fromisoformat(r["ts"]).timestamp() - late_run) < 1 else 0
    rc, root, log = runner_sim("lc_chain", out=os.path.join(_TMP, "lc_chain"), chain_delay=delay, chain_wrap=CountPolls)
    per_cycle = {}
    for slot, us in polls.items():
        per_cycle[slot] = len(us)
    if rc != 0 or max(per_cycle.values() or [0]) > 8:
        bad.append("chain wait: rc=%s, max polls in one cycle %s (want <= 8)" % (rc, max(per_cycle.values() or [0])))
    with open(os.path.join(live_dir(root), "tape_live_wall.csv"), encoding="utf-8", newline="") as fh:
        wr = {(r["symbol"], r["ts_ist"][11:16]): r for r in csv.DictReader(fh)}
    w1030, w1025 = wr.get(("NIFTY", "10:30")), wr.get(("NIFTY", "10:25"))
    if not w1030 or not w1025 or w1030["chain_run_id"] != w1025["chain_run_id"]:
        bad.append("delayed run: wall 10:30 should fall back to the 10:25 run")
    with open(os.path.join(root, DAY, "live_metrics.csv"), encoding="utf-8", newline="") as fh:
        mrows = {r["T"]: r for r in csv.DictReader(fh)}
    if mrows.get("10:30", {}).get("ready_lag_s_NIFTY", "x") != "" or not mrows.get("10:25", {}).get("ready_lag_s_NIFTY"):
        bad.append("delayed run: ready_lag_s_NIFTY at 10:30 %r (want empty), 10:25 %r (want a value)" % (
            mrows.get("10:30", {}).get("ready_lag_s_NIFTY"), mrows.get("10:25", {}).get("ready_lag_s_NIFTY")))
    # metrics rebuilds: per cycle, live_metrics.csv's rebuilds == the rebuilds the manifest records at that grid point, and
    # rebuild_s > 0 there; on the out-of-order day (late_segment at 12:20, by hand gen_live.LATE_SEG_OOO; subscriptions at 11:35)
    rc_o, root_o, _log = runner_sim("eq_out-of-order", _arr(gen_live.LATE_SEG_OOO))
    with open(os.path.join(live_dir(root_o), "run_manifest.json"), encoding="utf-8") as fh:
        man_o = json.load(fh)
    want_reb = {}
    for r in man_o["rebuilds"]:
        hm = "%02d:%02d" % (r["at"] // 60, r["at"] % 60)
        want_reb[hm] = want_reb.get(hm, []) + [r["trigger"]]
    if sorted(want_reb) != ["11:35", "12:20"]:
        bad.append("metrics precondition: manifest rebuilds at %s, want 11:35 and 12:20" % sorted(want_reb))
    with open(os.path.join(root_o, DAY, "live_metrics.csv"), encoding="utf-8", newline="") as fh:
        mo = list(csv.DictReader(fh))
    for r in mo:
        want_n = len(want_reb.get(r["T"], []))
        if int(r["rebuilds"]) != want_n or (want_n and not float(r["rebuild_s"]) > 0):
            bad.append("metrics rebuilds at %s: %s (rebuild_s %s), manifest %d %s" % (
                r["T"], r["rebuilds"], r["rebuild_s"], want_n, want_reb.get(r["T"], [])))
    return not bad, "; ".join(bad[:8]) or "heartbeat every cycle; self-exit 15:45; kill -> 0; MemoryError / RSS cap -> 3; one failed list counted, 3 lists per wake; chain wait <= 8 polls, deadline falls back; metrics rebuilds == manifest per cycle (late_segment 12:20, subscriptions 11:35)"


# ---------------------------------------------------------------- restart
def compare_day(a, b, mask_chain_seen=False):
    bad = []
    da, db = os.path.join(a, DAY), os.path.join(b, DAY)
    fa = [x for x in _files(da) if x not in TIMING_FILES]
    fb = [x for x in _files(db) if x not in TIMING_FILES]
    if fa != fb:
        bad.append("file sets differ: %s / %s" % (sorted(set(fa) - set(fb))[:4], sorted(set(fb) - set(fa))[:4]))
    for rel in sorted(set(fa) & set(fb)):
        x, y = rd(os.path.join(da, rel)), rd(os.path.join(db, rel))
        if rel == "arrival_log.csv" and mask_chain_seen:
            x, y = _mask_chain(x), _mask_chain(y)
        if x != y:
            bad.append("differs: " + rel)
    return bad


def _mask_chain(b):
    out = []
    for r in csv.reader(io.StringIO(b.decode())):
        if r and r[0] == "chain_run":
            r = [("" if i == 5 else v) for i, v in enumerate(r)]
        out.append(r)
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(out)
    return buf.getvalue().encode()


def _asof_rule(ta, tb, missed_min, restart_min, drop_ts=()):
    """A (uninterrupted) vs D (restarted after missed points), one CSV with an as_of column. Rows of the missed grid points
    (drop_ts) are absent from D. Every other row is equal except as_of, and as_of may differ only where A's as_of is the grid
    time of a MISSED cycle; D's is then the first cycle after the restart (re-sent there, never back-filled)."""
    cli = mods()[0]
    ra, rb = list(csv.reader(io.StringIO(ta))), list(csv.reader(io.StringIO(tb)))
    h = ra[0]
    if rb[0] != h:
        return ["header differs"]
    ia, its = h.index("as_of"), h.index("ts_ist")
    keep = [r for r in ra[1:] if r[its][11:16] not in drop_ts]
    if len(keep) != len(rb) - 1:
        return ["%d rows, want %d (the missed points' rows absent)" % (len(rb) - 1, len(keep))]
    missed_asof = {cli.as_of(DAY, m) for m in missed_min}
    first = cli.as_of(DAY, restart_min)
    bad, n_moved = [], 0
    for x, y in zip(sorted(keep, key=lambda r: r[:ia] + r[ia + 1:]), sorted(rb[1:], key=lambda r: r[:ia] + r[ia + 1:])):
        if x[:ia] + x[ia + 1:] != y[:ia] + y[ia + 1:]:
            bad.append("row differs beyond as_of: %s" % x[:5])
        elif x[ia] != y[ia]:
            n_moved += 1
            if x[ia] not in missed_asof or y[ia] != first:
                bad.append("as_of %s -> %s for %s (A's must be a missed cycle, D's %s)" % (x[ia], y[ia], x[:4], first))
        if len(bad) > 3:
            break
    return bad or n_moved


def g_runner_restart():
    bad = []
    rc, A, _ = runner_sim("eq_clean")
    if rc != 0:
        return False, "reference run rc=%s" % rc

    def killer(d, hhmm):
        def k():
            with open(os.path.join(d, "KILL"), "w") as fh:
                fh.write("")
        return [(ist_epoch(_hm_min(hhmm)), k)]
    # B: kill after 11:00, restart before 11:05
    dB = os.path.join(_TMP, "rs_B")
    rc1, _, _ = runner_sim("rs_B1", out=dB, events=killer(dB, "11:01"))
    os.remove(os.path.join(dB, "KILL"))
    rc2, _, _ = runner_sim("rs_B2", out=dB, start="11:03")
    if (rc1, rc2) != (0, 0):
        bad.append("B rc %s/%s" % (rc1, rc2))
    bad += ["B: " + x for x in compare_day(A, dB)]
    # C: crash after the journal append in cycle 12:10, restart at 12:11
    dC = os.path.join(_TMP, "rs_C")

    def crash(t, runner):
        if t == 730:
            raise RuntimeError("injected crash")
    rc1, _, _ = runner_sim("rs_C1", out=dC, hooks={"after_journal": crash})
    rc2, _, _ = runner_sim("rs_C2", out=dC, start="12:11")
    if rc1 != 1 or rc2 != 0:
        bad.append("C rc %s/%s (want 1 then 0)" % (rc1, rc2))
    bad += ["C: " + x for x in compare_day(A, dC, mask_chain_seen=True)]
    # D: kill at 11:01, restart at 12:01: 11:05..11:55 missed, never back-filled
    dD = os.path.join(_TMP, "rs_D")
    runner_sim("rs_D1", out=dD, events=killer(dD, "11:01"))
    os.remove(os.path.join(dD, "KILL"))
    rc2, _, _ = runner_sim("rs_D2", out=dD, start="12:01")
    missed = ["%02d:%02d" % (m // 60, m % 60) for m in range(665, 720, 5)]
    if rc2 != 0 or _state(dD).get("missed") != [_hm_min(x) for x in missed]:
        bad.append("D: rc=%s missed %r, want %s" % (rc2, _state(dD).get("missed"), missed))
    for n in ("tape_live_cycle.csv", "tape_live_events.csv"):
        if rd(os.path.join(live_dir(A), n)) != rd(os.path.join(live_dir(dD), n)):
            bad.append("D: %s != uninterrupted" % n)
    missed_min = [_hm_min(x) for x in missed]
    moved = {}
    for n, drop in (("tape_live_cycle.db.csv", ()), ("tape_live_events.db.csv", ()), ("tape_live_wall.db.csv", missed),
                    ("tape_live_wall.csv", missed)):
        r = _asof_rule(rd(os.path.join(live_dir(A), n)).decode(), rd(os.path.join(live_dir(dD), n)).decode(), missed_min,
                       _hm_min("12:00"), set(drop))
        if isinstance(r, list):
            bad += ["D: %s: %s" % (n, x) for x in r]
        else:
            moved[n] = r
    # epochs: ids and count equal; epoch_log equal except, by hand, the one bump the default day has (NIFTY subscriptions, file
    # subscriptions_113300.json): uninterrupted at 11:35 (695); in D that file is first seen after the restart, so its bump is at
    # 12:00 (720), and its reemit_rows (rows re-sent only for the new id) count the rows present then, so it may differ too.
    with open(os.path.join(live_dir(A), "run_manifest.json"), encoding="utf-8") as fh:
        man_a = json.load(fh)
    with open(os.path.join(live_dir(dD), "run_manifest.json"), encoding="utf-8") as fh:
        man_d = json.load(fh)
    if man_a.get("epochs") != man_d.get("epochs") or not man_a.get("epochs"):
        bad.append("D: manifest epochs differ: %r / %r" % (man_a.get("epochs"), man_d.get("epochs")))
    la_ = [(e["symbol"], e["trigger"], e["at"]) for e in man_a.get("epoch_log", [])]
    ld_ = [(e["symbol"], e["trigger"], e["at"]) for e in man_d.get("epoch_log", [])]
    if la_ != [("NIFTY", "subscriptions", 695)] or ld_ != [("NIFTY", "subscriptions", 720)]:
        bad.append("D: epoch_log uninterrupted %s, restarted %s; want exactly NIFTY/subscriptions at 695 and at 720" % (la_, ld_))
    # reemit_rows, by hand: at the bump every NIFTY row of the last emitted state is re-sent only for its new id (the 11:33 file
    # changes no row's data). Those rows: one cycle row per NIFTY leg (OPT and FUT tokens of gen_live.TOKENS; the 11:33 token is
    # not in that state) per grid point 09:20..last, one wall per grid point, and the events stamped by then (THIN 11:03 and
    # CONC 11:05 of the plan; none by 11:00). Uninterrupted: last state 11:30, 27 points, 2 events. D: last state 11:00 (the
    # restart skipped 11:05-11:55), 21 points, 0 events. (First stated as 219 / 147: the FUT leg was left out and 09:20..11:30
    # was counted as 31 points; corrected from the code, see _l2_logs/phaseB_reemit_why.log.)
    legs = sum(1 for t in gen_live.TOKENS if t[1] == "NIFTY" and t[2] in ("OPT", "FUT"))
    want_re = (legs * 27 + 27 + 2, legs * 21 + 21 + 0)
    got_re = tuple(m.get("epoch_log", [{}])[0].get("reemit_rows") if m.get("epoch_log") else None for m in (man_a, man_d))
    if got_re != want_re:
        bad.append("D: reemit_rows of the NIFTY subscriptions bump %s (uninterrupted, restarted), by hand %s" % (got_re, want_re))
    for ea, ed in zip(man_a.get("epoch_log", []), man_d.get("epoch_log", [])):
        if dict(ea, at=0, reemit_rows=0) != dict(ed, at=0, reemit_rows=0):
            bad.append("D: epoch_log entries differ beyond at / reemit_rows: %r / %r" % (ea, ed))
    for n, per in (("tape_live_label.csv", 4), ("tape_live_label.db.csv", 4)):
        la = rd(os.path.join(live_dir(A), n)).decode().splitlines()
        lb = rd(os.path.join(live_dir(dD), n)).decode().splitlines()
        gone = [l for l in la if l not in lb]
        extra = [l for l in lb if l not in la]
        want_gone = [l for l in la if any("T%s:00+05:30" % x in l for x in missed)]
        if extra or sorted(gone) != sorted(want_gone) or len(gone) != per * len(missed):
            bad.append("D: %s %d rows gone (want exactly %d, those of the missed points), %d extra" % (
                n, len(gone), per * len(missed), len(extra)))
    # E: the day twice -> identical; a restart of a finished day changes nothing
    dE = os.path.join(_TMP, "rs_E")
    rc, _, _ = runner_sim("rs_E", out=dE)
    bad += ["E: " + x for x in compare_day(A, dE)]
    before = {rel: rd(os.path.join(dE, DAY, rel)) for rel in _files(os.path.join(dE, DAY)) if rel not in TIMING_FILES}
    rc, _, _ = runner_sim("rs_E2", out=dE, start="15:50")
    after = {rel: rd(os.path.join(dE, DAY, rel)) for rel in _files(os.path.join(dE, DAY)) if rel not in TIMING_FILES}
    if rc != 0 or before != after:
        bad.append("E: restart of a finished day rc=%s, changed %d files" % (rc, sum(1 for k in set(before) | set(after)
                                                                                     if before.get(k) != after.get(k))))
    return not bad, "; ".join(bad[:8]) or (
        "B kill/restart, C crash mid-cycle, E twice: byte-identical (both shapes); D: 11 missed points absent (44 labels, 22 walls), "
        "L0 finals equal, DB rows equal but as_of, which moved only from a missed cycle to the first cycle after the restart "
        "(%s); D epochs equal (ids and count); D epoch_log = NIFTY/subscriptions at 695 vs 720, reemit_rows %d vs %d by hand, "
        "else equal; D tape_live_label.db.csv = the missed points' rows absent; finished day untouched" % (
            ", ".join("%s %d" % (k, v) for k, v in sorted(moved.items())), want_re[0], want_re[1]))


# ------------------------------------------------------------------------------------------- epoch + DB shape (Phase B)
# docs/tape/L2_live_runner_plan.md section 4. Everything here reads the files; the expected epochs, the dropped and added events
# and the drop case are written by hand in tests/tape_live/gen_live.py (EPOCH_*), never taken from a run.
DB_TABLES = ("tape_live_cycle", "tape_live_events", "tape_live_wall", "tape_live_label")
DELTA_TABLES = ("tape_live_cycle", "tape_live_events", "tape_live_wall")
DB_PART = {"tape_live_cycle": "cycle", "tape_live_events": "events", "tape_live_wall": "wall"}


def sql_columns():
    """{table: [columns in DDL order]} parsed from the committed SQL file (not from ddl.py)."""
    with open(SQL, encoding="utf-8") as fh:
        text = fh.read()
    out = {}
    for t in DB_TABLES:
        body = re.search(r"CREATE TABLE IF NOT EXISTS public\.%s \((.*?)\n\);" % t, text, re.S).group(1)
        out[t] = [ln.split()[0] for ln in body.strip().split("\n") if not ln.strip().startswith("CONSTRAINT")]
    return out


def sql_key(t):
    """The upsert key of a table from the SQL file: the PK, else the grain UNIQUE (tape_live_events has no PK)."""
    with open(SQL, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"CONSTRAINT %s_pk PRIMARY KEY \(([^)]*)\)" % t, text) or \
        re.search(r"CONSTRAINT %s_grain_uq UNIQUE NULLS NOT DISTINCT \(([^)]*)\)" % t, text)
    return [c.strip() for c in m.group(1).split(",")]


def epoch_fixture():
    if "epoch" not in _CACHE:
        root = os.path.join(_TMP, "epoch")
        f = gen_live.build(root, epoch=True)
        from services.tape_offline import cycle_day, process_day
        out, cyc = os.path.join(root, "batch_out"), os.path.join(root, "batch_cyc")
        rc1, log1 = quiet(process_day.main, [f["raw"], "--day", DAY, "--out", out])
        rc2, log2 = quiet(cycle_day.main, ["--in", out, "--session", os.path.join(f["raw"], "session"), "--out", cyc])
        if rc1 != 0 or rc2 != 0:
            raise AssertionError("epoch batch failed: %s %s\n%s\n%s" % (rc1, rc2, log1[-2000:], log2[-2000:]))
        f.update(cyc=cyc)
        _CACHE["epoch"] = f
    return _CACHE["epoch"]


def epoch_replay():
    if "rp_epoch" not in _CACHE:
        cli = mods()[0]
        f = epoch_fixture()
        d = os.path.join(_TMP, "rp_epoch")
        argv = ["replay", "--day", DAY, "--raw", f["raw"], "--out", d,
                "--arrival", arrival_file("epoch", gen_live.EPOCH_ARRIVAL)]
        for p in f["chain"]:
            argv += ["--chain-runs", p]
        rc, log = quiet(cli.main, argv)
        if rc != 0:
            raise AssertionError("epoch replay rc=%s\n%s" % (rc, log[-3000:]))
        _CACHE["rp_epoch"] = d
    return _CACHE["rp_epoch"]


def _db_read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    return rows[0], rows[1:]


def db_deltas(d):
    """[(cycle name, grid minute or None for final, {table: (header, rows)})] in cycle order, from cycles/*.db.csv."""
    by = {}
    for n in os.listdir(os.path.join(d, "cycles")):
        m = re.match(r"^(\d{4}|final)_(cycle|events|wall)\.db\.csv$", n)
        if m:
            t = [k for k, v in DB_PART.items() if v == m.group(2)][0]
            by.setdefault(m.group(1), {})[t] = _db_read(os.path.join(d, "cycles", n))
    names = sorted(k for k in by if k != "final") + (["final"] if "final" in by else [])
    return [(k, None if k == "final" else int(k[:2]) * 60 + int(k[2:]), by[k]) for k in names]


def _keyf(t, header):
    idx = [header.index(c) for c in sql_key(t)]
    return lambda r: tuple(r[i] for i in idx)


def apply_db(deltas, upto=None, u_only=False):
    """{table: {key: row}}: the delta files applied in order (D removes), or U lines only (the 2b writer: D is a no-op)."""
    st = {t: {} for t in DELTA_TABLES}
    for name, _m, parts in deltas:
        for t, (h, rows) in parts.items():
            kf = _keyf(t, h[1:])
            for r in rows:
                if r[0] == "U":
                    st[t][kf(r[1:])] = r[1:]
                elif not u_only:
                    st[t].pop(kf(r[1:]), None)
        if name == upto:
            break
    return st


def newest_view(state):
    """The newest-run filter of ruling R6-H, written here independently of writer.newest_epoch_view. state: {table: [rows]} of
    the three state tables (columns as in the SQL file). Per (trading_day, symbol), one newest id: that of the row with the
    latest as_of across cycle, events and wall together; every table keeps only rows with it. -> {table: [rows]}."""
    cols = sql_columns()
    pos = dict((t, dict((c, cols[t].index(c)) for c in ("trading_day", "symbol", "as_of", "live_run_id"))) for t in state)
    best = {}
    for t, rows in state.items():
        p = pos[t]
        for r in rows:
            k = (r[p["trading_day"]], r[p["symbol"]])
            if k not in best or r[p["as_of"]] > best[k][0]:
                best[k] = (r[p["as_of"]], r[p["live_run_id"]])
    return dict((t, [r for r in rows if r[pos[t]["live_run_id"]] == best[(r[pos[t]["trading_day"]], r[pos[t]["symbol"]])][1]])
                for t, rows in state.items())


def _first_diff(t, got, want):
    """The first differing row between two row lists, named by symbol: 'extra <symbol> <row>' or 'missing <symbol> <row>'."""
    h = sql_columns()[t]
    a, b = set(map(tuple, got)), set(map(tuple, want))
    for kind, rows in (("extra", sorted(a - b)), ("missing", sorted(b - a))):
        if rows:
            r = dict(zip(h, rows[0]))
            return "%s %s row (%d %s): %s" % (kind, r.get("symbol"), len(rows), kind,
                                             ",".join(str(r.get(c, "")) for c in ("strike", "leg", "kind", "ts_ist", "as_of",
                                                                                   "live_run_id") if c in r))
    return "same rows, different multiplicity"


def tie_ids(state):
    """{table: [rows]} of the three state tables -> {(trading_day, symbol): ids} for every key whose rows at the latest as_of,
    taken across cycle, events and wall together, carry more than one live_run_id (ruling R6-H: must never happen)."""
    cols = sql_columns()
    top = {}
    for t, rows in state.items():
        h = cols[t]
        i_d, i_s, i_a, i_r = (h.index(c) for c in ("trading_day", "symbol", "as_of", "live_run_id"))
        for r in rows:
            k = (r[i_d], r[i_s])
            if k not in top or r[i_a] > top[k][0]:
                top[k] = (r[i_a], {r[i_r]})
            elif r[i_a] == top[k][0]:
                top[k][1].add(r[i_r])
    ids = dict((k, v[1]) for k, v in top.items())
    return dict((k, v) for k, v in ids.items() if len(v) > 1)


def _planted_tie():
    """A state that holds a tie by construction: two wall rows of one (day, symbol) at the same latest as_of, two ids."""
    h = sql_columns()["tape_live_wall"]
    row = dict((c, "") for c in h)
    row.update(symbol="NIFTY", trading_day=DAY, ts_ist=DAY + "T10:00:00+05:30", as_of=DAY + "T05:00:00+00:00", code_sha=TEST_SHA)
    a = [dict(row, live_run_id="00000000-0000-5000-8000-000000000001")[c] for c in h]
    b = [dict(row, ts_ist=DAY + "T10:05:00+05:30", live_run_id="00000000-0000-5000-8000-000000000002")[c] for c in h]
    return {"tape_live_cycle": [], "tape_live_events": [], "tape_live_wall": [a, b]}


def _ist_date(ts):
    return datetime.fromisoformat(ts).astimezone(IST).strftime("%Y-%m-%d")


def g_dbshape():
    from services.tape_live import dbshape
    cols = sql_columns()
    bad, n_rows, n_files = [], 0, 0
    # (b) unit: a grid time at 00:30 IST is the previous UTC date; trading_day must be the IST date
    for ts, want in (("2026-11-06T00:30:00+05:30", "2026-11-06"), ("2026-11-05T19:00:00+00:00", "2026-11-06"),
                     ("2026-11-06T23:59:00+05:30", "2026-11-06"), ("2026-11-06T18:31:00+00:00", "2026-11-07")):
        got = dbshape.trading_day_of(ts)
        if got != want:
            bad.append("trading_day_of(%s) = %r, want the IST date %r" % (ts, got, want))
    for name, d in (("clean", replay("clean")), ("epoch", epoch_replay())):
        deltas = db_deltas(d)
        if not deltas:
            bad.append("%s: no cycles/*.db.csv delta files" % name)
            continue
        files = []
        for cname, m, parts in deltas:
            limit = None if m is None else mods()[0].as_of(DAY, m)
            for t, (h, rows) in parts.items():
                files.append(("cycles/%s_%s.db.csv" % (cname, DB_PART[t]), t, h, rows, True, limit))
        last_m = max(m for _c, m, _p in deltas if m is not None)
        last = mods()[0].as_of(DAY, last_m)
        files = [(a, b, c, e, f_, g if g is not None else last) for a, b, c, e, f_, g in files]
        for t in DB_TABLES:
            p = os.path.join(d, "%s.db.csv" % t)
            if not os.path.exists(p):
                bad.append("%s: %s.db.csv missing" % (name, t))
                continue
            h, rows = _db_read(p)
            files.append(("%s.db.csv" % t, t, h, rows, False, last))
        for rel, t, h, rows, is_delta, limit in files:
            n_files += 1
            want_h = (["op"] if is_delta else []) + cols[t]
            if h != want_h:                                                              # (a)
                bad.append("%s %s: header %s != DDL %s" % (name, rel, h, want_h))
                continue
            data_h = h[1:] if is_delta else h
            i_td, i_ts, i_as = data_h.index("trading_day"), data_h.index("ts_ist"), data_h.index("as_of")
            i_cs, i_id = data_h.index("code_sha"), data_h.index("live_run_id")
            for r in rows:
                n_rows += 1
                op, r = (r[0], r[1:]) if is_delta else ("", r)
                if is_delta and op not in ("U", "D"):
                    bad.append("%s %s: op %r" % (name, rel, op))
                if len(r) != len(data_h):
                    bad.append("%s %s: %d fields, header %d" % (name, rel, len(r), len(data_h)))
                    continue
                if any(v in ("None", "null", "NULL", "nan") for v in r):                 # (a) empty = NULL
                    bad.append("%s %s: a NULL written as text: %r" % (name, rel, r[:6]))
                if r[i_td] != DAY or r[i_td] != _ist_date(r[i_ts]):                       # (b)
                    bad.append("%s %s: trading_day %s, ts_ist %s (IST date %s)" % (name, rel, r[i_td], r[i_ts],
                                                                                 _ist_date(r[i_ts])))
                if not re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00$", r[i_as]) or r[i_as] > limit:   # (c)
                    bad.append("%s %s: as_of %s (limit %s, UTC +00:00 required)" % (name, rel, r[i_as], limit))
                if not r[i_cs] or not r[i_id]:
                    bad.append("%s %s: empty provenance" % (name, rel))
                if len(bad) > 12:
                    break
    # (d) D lines are file-only: no state file carries an op column (the headers above); no statement path reads an op:
    # outside the two file-to-memory appliers no code compares anything with the D op; and the SQL grants SELECT only.
    allowed = {"apply_deltas", "apply_db_deltas"}
    for path in [os.path.join(LIVE, n) for n in sorted(os.listdir(LIVE)) if n.endswith(".py")]:
        tree = ast.parse(rd(path).decode("utf-8"))
        for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            if fn.name in allowed:
                continue
            for node in ast.walk(fn):
                if isinstance(node, ast.Compare):
                    for c in [node.left] + list(node.comparators):
                        if isinstance(c, ast.Constant) and c.value in ("D", "D,"):
                            bad.append("%s:%d %s() compares with the D op outside the file appliers" % (
                                os.path.basename(path), node.lineno, fn.name))
    with open(SQL, encoding="utf-8") as fh:
        grants = re.findall(r"GRANT ([^;]+?) ON", fh.read())
    if not grants or any(g.strip() != "SELECT" for g in grants):
        bad.append("SQL grants other than SELECT: %r" % grants)
    return not bad, "; ".join(bad[:8]) or (
        "%d files, %d rows: headers == DDL, trading_day == IST date of ts_ist (+4 planted UTC/IST edges), as_of <= cycle grid "
        "time, UTC; D ops only in delta files, read only by the file appliers; SQL grants SELECT only" % (n_files, n_rows))


def g_epoch():
    writer = mods()[5]
    from services.tape_live import dbshape
    f = epoch_fixture()
    d = epoch_replay()
    cols = sql_columns()
    bad = []
    with open(os.path.join(d, "run_manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    got = [(e["symbol"], e["trigger"], e["at"]) for e in man.get("epoch_log", [])]
    if got != gen_live.EPOCH_BUMPS:
        bad.append("epoch bumps %s != by hand %s" % (got, gen_live.EPOCH_BUMPS))
    if [(r["symbol"], r["trigger"], r["at"]) for r in man["rebuilds"]] != [b for b in gen_live.EPOCH_BUMPS if b[1] != "drop"]:
        bad.append("rebuilds %s are not the two rebuilds (a drop is never a rebuild)" % man["rebuilds"])
    n_by = {s: sum(1 for b in gen_live.EPOCH_BUMPS if b[0] == s) for s in writer.SYMBOLS}
    want_ids = {s: [writer.epoch_id(DAY, s, TEST_SHA, n) for n in range(1 + n_by[s])] for s in writer.SYMBOLS}
    if man.get("epochs") != want_ids:
        bad.append("manifest epochs %s != %s" % (man.get("epochs"), want_ids))
    if len({i for v in want_ids.values() for i in v}) != sum(len(v) for v in want_ids.values()):
        bad.append("epoch ids are not distinct")
    deltas = db_deltas(d)
    names = [n for n, _m, _p in deltas]
    ev_h = cols["tape_live_events"]
    ix = [ev_h.index(c) for c in ("symbol", "strike", "leg", "kind", "ts_ist")]
    i_id = ev_h.index("live_run_id")

    def ev_ids(state, key):
        return [r[i_id] for r in state["tape_live_events"].values() if tuple(r[i] for i in ix) == key]

    nifty = want_ids["NIFTY"]
    # (0) preconditions: the planted events exist before they are dropped, else this guard would pass vacuously
    st1345, st1350 = apply_db(deltas, "1345"), apply_db(deltas, "1350")
    if ev_ids(st1345, gen_live.EPOCH_DROPPED) != [nifty[1]]:
        bad.append("(0) precondition: %s not in the 13:45 state under epoch 1: %r" % (
            gen_live.EPOCH_DROPPED, ev_ids(st1345, gen_live.EPOCH_DROPPED)))
    if ev_ids(apply_db(deltas, "1430"), gen_live.EPOCH_THIN) != [nifty[2]]:
        bad.append("(0) precondition: %s not in the 14:30 state under epoch 2" % (gen_live.EPOCH_THIN,))
    sensex = want_ids["SENSEX"]
    i_es = ev_h.index("symbol")

    def sx_events(state):
        return [r for r in state["tape_live_events"].values() if r[i_es] == "SENSEX"]
    if ev_ids(apply_db(deltas, "1045"), gen_live.EPOCH_SX_DROPPED) != [sensex[0]] or len(sx_events(apply_db(deltas, "1045"))) != 1:
        bad.append("(0) precondition: %s is not SENSEX's only event in the 10:45 state under epoch 0" % (gen_live.EPOCH_SX_DROPPED,))
    sx_after = [n for n, _m, _p in deltas if (n == "final" or n >= "1050") and sx_events(apply_db(deltas, n))]
    if sx_after:
        bad.append("(0) SENSEX event rows in the D-applied state from 10:50 on, at %s; want none" % sx_after[:3])
    # (1) the rebuild cycle: a D line for the dropped event; every surviving NIFTY row re-sent with the epoch-2 id
    parts = [p for n, _m, p in deltas if n == "1350"]
    parts = parts[0] if parts else {}
    rows = parts.get("tape_live_events", (None, []))[1]
    if len([r for r in rows if r[0] == "D" and tuple(r[1:][i] for i in ix) == gen_live.EPOCH_DROPPED]) != 1:
        bad.append("(1) 13:50 delta: not exactly one D line for the dropped event")
    for t in DELTA_TABLES:
        hh = cols[t]
        si, ri = hh.index("symbol"), hh.index("live_run_id")
        sent = {_keyf(t, hh)(r[1:]): r[1:] for r in parts.get(t, (None, []))[1] if r[0] == "U"}
        nn = [k for k, r in st1350[t].items() if r[si] == "NIFTY" and (r[ri] != nifty[2] or sent.get(k) != r)]
        if nn or not any(r[si] == "NIFTY" for r in st1350[t].values()):
            bad.append("(1) %s: %d NIFTY rows not re-sent at 13:50 with the epoch-2 id" % (t, len(nn)))
    # (2) D applied: no NIFTY row of an older epoch survives, at 13:50 and at the end
    for label, st, cur in (("13:50", st1350, nifty[2]), ("end", apply_db(deltas), nifty[3])):
        for t in DELTA_TABLES:
            hh = cols[t]
            si, ri = hh.index("symbol"), hh.index("live_run_id")
            old = [r for r in st[t].values() if r[si] == "NIFTY" and r[ri] != cur]
            if old:
                bad.append("(2) %s %s: %d NIFTY rows of an older epoch" % (label, t, len(old)))
    # (2b) at EVERY cycle: U lines only (D a no-op, the 2b writer) + newest-run filter == D applied
    n_checked = 0
    for name in names:
        full, uo = apply_db(deltas, name), apply_db(deltas, name, u_only=True)
        view = newest_view(dict((t, list(uo[t].values())) for t in DELTA_TABLES))
        for t in DELTA_TABLES:
            if sorted(view[t]) != sorted(full[t].values()):
                bad.append("(2b) cycle %s %s: U-only + newest-run filter != D applied: %s" % (name, t, _first_diff(t, view[t],
                                                                                                          full[t].values())))
            n_checked += 1
    # (2c) the final state, asserted, not inferred: the day-end tape_live_{cycle,events,wall}.db.csv files through the newest
    # view equal the D-applied state after the last delta; SENSEX has zero event rows in it
    last = apply_db(deltas)
    files = dict((t, _db_read(os.path.join(d, "%s.db.csv" % t))) for t in DELTA_TABLES)
    fview = newest_view(dict((t, files[t][1]) for t in DELTA_TABLES))
    for t in DELTA_TABLES:
        if files[t][0] != cols[t] or sorted(fview[t]) != sorted(last[t].values()):
            bad.append("(2c) day-end %s.db.csv through the newest view != D-applied state after the last delta: %s" % (
                t, _first_diff(t, fview[t], last[t].values())))
    if [r for r in fview["tape_live_events"] if r[cols["tape_live_events"].index("symbol")] == "SENSEX"]:
        bad.append("(2c) day-end tape_live_events.db.csv holds SENSEX rows in the newest epoch; want zero")
    # (3) the latest epoch's data columns == the batch output for the day, byte for byte (rendered through dbshape)
    end = apply_db(deltas)
    end_view = newest_view(dict((t, list(end[t].values())) for t in DELTA_TABLES))
    for t, src in (("tape_live_cycle", "tape_strike_cycle.csv"), ("tape_live_events", "tape_events.csv")):
        nd = len(cols[t]) - 3
        live = sorted(r[:nd] for r in end_view[t])
        with open(os.path.join(f["cyc"], src), encoding="utf-8", newline="") as fh:
            batch = sorted(dbshape.data_row(t, DAY, r) for r in list(csv.reader(fh))[1:])
        if live != batch:
            bad.append("(3) %s: latest epoch (%d rows) != batch through dbshape (%d rows)" % (t, len(live), len(batch)))
    if ev_ids(end, gen_live.EPOCH_ADDED) != [nifty[3]] or ev_ids(end, gen_live.EPOCH_DROPPED) or ev_ids(end, gen_live.EPOCH_THIN):
        bad.append("(3) end state: added %r dropped %r thin %r" % (
            ev_ids(end, gen_live.EPOCH_ADDED), ev_ids(end, gen_live.EPOCH_DROPPED), ev_ids(end, gen_live.EPOCH_THIN)))
    # (4) every U row of every cycle carries its OWN symbol's epoch at that cycle (bumps by hand: n = bumps of that symbol with
    # at <= the cycle); another symbol's bump never changes it
    n_wrong = 0
    first_wrong = None
    for name, m, parts in deltas:
        for t, (hh, rows) in parts.items():
            si, ri = hh.index("symbol"), hh.index("live_run_id")
            for r in rows:
                if r[0] != "U":
                    continue
                n = sum(1 for b in gen_live.EPOCH_BUMPS if b[0] == r[si] and (m is None or b[2] <= m))
                if r[ri] != want_ids[r[si]][n]:
                    n_wrong += 1
                    first_wrong = first_wrong or "%s %s %s" % (name, t, r[si])
    if n_wrong:
        bad.append("(4) %d U rows carry another epoch than their symbol's at that cycle (first: %s)" % (n_wrong, first_wrong))
    # tie (ruling R6-H, step 3): per (trading_day, symbol), all rows at the latest as_of across the three tables carry one id,
    # in the U-only state (what 2b holds) and the D-applied state, at every cycle; the check must fire on a planted tie
    n_tie = 0
    for name in names:
        for st in (apply_db(deltas, name), apply_db(deltas, name, u_only=True)):
            ties = tie_ids(dict((t, list(st[t].values())) for t in DELTA_TABLES))
            if ties:
                n_tie += 1
                bad.append("tie at cycle %s: %s" % (name, sorted((k, sorted(v)) for k, v in ties.items())[:2]))
    if not tie_ids(_planted_tie()):
        bad.append("tie check did not fire on a planted tie (it cannot fail)")
    # (5) a cycle with no bump re-sends no row whose data and id are unchanged
    bump_cycles = {"%02d%02d" % (a // 60, a % 60) for _s, _t, a in gen_live.EPOCH_BUMPS}
    prev = {t: {} for t in DELTA_TABLES}
    n_same = n_u = 0
    for name, _m, parts in deltas:
        for t in DELTA_TABLES:
            hh = cols[t]
            kf, ai = _keyf(t, hh), hh.index("as_of")
            for r in parts.get(t, (None, []))[1]:
                if r[0] == "U" and name not in bump_cycles:
                    n_u += 1
                    old = prev[t].get(kf(r[1:]))
                    if old is not None and old[:ai] + old[ai + 1:] == r[1:][:ai] + r[1:][ai + 1:]:
                        n_same += 1
        prev = apply_db(deltas, name)
    if n_same:
        bad.append("(5) %d of %d rows re-sent unchanged in cycles without a bump" % (n_same, n_u))
    # (6) labels: written before the rebuild they keep their epoch-1 id; the reference view never filters labels
    lh, lrows = _db_read(os.path.join(d, "tape_live_label.db.csv"))
    li, ls_, lt = lh.index("live_run_id"), lh.index("symbol"), lh.index("ts_ist")
    early = [r for r in lrows if r[ls_] == "NIFTY" and "11:35" <= r[lt][11:16] < "13:50"]
    if not early or any(r[li] != nifty[1] for r in early):
        bad.append("(6) NIFTY labels 11:35-13:45: %d rows, ids %s, want all epoch 1" % (len(early), sorted({r[li] for r in early})))
    uo_end = apply_db(deltas, u_only=True)
    tabs = dict((t, (cols[t], list(uo_end[t].values()))) for t in DELTA_TABLES)
    tabs["tape_live_label"] = (lh, lrows)
    wv = writer.newest_epoch_view(tabs)
    if sorted(wv["tape_live_label"]) != sorted(lrows):
        bad.append("(6) writer.newest_epoch_view filtered labels (%d -> %d rows)" % (len(lrows), len(wv["tape_live_label"])))
    ref = newest_view(dict((t, tabs[t][1]) for t in DELTA_TABLES))
    for t in DELTA_TABLES:
        if sorted(wv[t]) != sorted(ref[t]):
            bad.append("writer.newest_epoch_view(%s) != the independent filter (%d vs %d rows)" % (t, len(wv[t]), len(ref[t])))
    return not bad, "; ".join(bad[:8]) or (
        "bumps %s; CONC 13:45 D'd at 13:50 with every NIFTY row re-sent under epoch 2; THIN 14:30 drop bumped; SENSEX's only "
        "event (CONC 10:45) gone in the 10:50 rebuild, zero SENSEX events after; U-only + newest view == D applied at %d (cycle, "
        "table) points; (2c) day-end .db.csv state through the newest view == D-applied after the last delta, no SENSEX event; latest epoch == batch; every U row on its own symbol's epoch; no tie at the latest as_of (planted tie "
        "detected); %d unbumped U rows all changed; %d early labels keep epoch 1" % (
            ",".join("%s/%s@%d" % b for b in got), n_checked, n_u, len(early)))


# ------------------------------------------------------------------------------------------- stage 2b: the DB writer (live-2b-*)
# Plan: _l2_logs/2b_writer_plan.md (revision 2). WRITTEN BEFORE services/tape_live/dbwrite.py EXISTS (red first): every guard here
# must FAIL on the tree as it is, for the reason the plan names. The fakes below are written from the plan and the DDL, never from
# the writer; a self-test (_w2b_selftest) proves they can fire without it.
#
# TEST-SIDE CONTRACTS the writer is built to (the plan leaves these open; each is a choice made here, to be ruled on):
#   CLI      cli live --db-write [--db-batch-rows N] [--test-redate-today]; env TAPE_LIVE_W_DSN (popped at start) and
#            TAPE_LIVE_TEST_REDATE; cli write-clear --day D --out DIR --note TEXT; cli db-literal-check (no arguments).
#            --check with --db-write runs the write start-up check too and prints CHECK PASS only if it passes.
#   SEAM     services.tape_live.dbwrite.now_ist() -> aware IST datetime: the writer's "local today". The guards replace it, so a
#            sim-clock run on 2026-11-06 can be a trading day (Friday) or a Saturday.
#   ROUTING  a write psql call is told apart by its environment: PGPASSWORD is the write role's. The script is on stdin; no value
#            is ever in argv. A read psql call carries the read role's PGPASSWORD.
#   SCRIPT   \set ON_ERROR_STOP 1, \set VERBOSITY sqlstate, \timing on; BEGIN; SET LOCAL standard_conforming_strings = on;
#            SET LOCAL lock_timeout = '5s'; INSERT ... (each value '<text>'::<DDL type>, empty = NULL); COMMIT. Tables in the
#            order cycle, events, wall, label; at most one write psql per cycle (plus the final).
#   PSQL OUT per statement a command tag line and a "Time: x ms" line (what `psql` prints without -q under \timing); an error is
#            "ERROR:  <SQLSTATE>" on stderr with rc 3; a failed connect is "psql: error: connection to server ..." with rc 2 (no
#            SQLSTATE, so a connection-limit refusal there is recognised by its text); rc 124 = the 60 s process timeout.
#   CHECK    start-up check output (psql --csv -t): role,<name> / super,t|f / bypassrls,t|f / scs,<setting> / ist_date,<date> /
#            priv,<table>,<DELETE|TRUNCATE|INSERT|UPDATE>,t|f.
#   LITCHECK db-literal-check: BEGIN READ ONLY; ... one SELECT '<literal>'::<type>::text per case ...; ROLLBACK; the server's text
#            form of each value comes back one csv row per SELECT, under SET LOCAL TIME ZONE 'UTC'.
#   STATE    heartbeat.json write {state: none|sent|skipped|stopped, reason, skips, db_written}; write.latch_day / write.carried when stopped;
#            R8-I: the stop latch is <out>/WRITE_LATCH.json {reason, category, at, day, set_utc} (test-only runs: WRITE_LATCH.redate.json),
#            carried across days; state.json keeps write_skips, db_written only; <day>/WRITE_STOPPED (json, informational);
#            write-clear --out DIR --note TEXT [--day D] [--test-redate]: refused while a heartbeat of the latch day or later is alive
#            (POSIX pid alive, or state starting/cycling/waiting and updated_utc younger than 600 s), the refusal prints each day, pid,
#            heartbeat age in seconds and the 600 s bound; a clear renames the latch to WRITE_LATCH.cleared.<utc>.json (redate:
#            WRITE_LATCH.redate.cleared.<utc>.json); a latch that cannot be parsed stops writes with reason latch_unreadable; <day>/live/db_withheld.csv, db_dupkeys.csv;
#            live_metrics.csv gains the plan's columns. Reasons by hand: W_REASON below, plus dup_conflict_key,
#            cycle_grain_uq_unpredicted, missed_grid_point, overrun, item_7a_drop_bump, second_skip.
W_USER = "tape_w"
W_PW = "Wz" + "4-q" + "Nm8y-Hd"
W_DSN = "postgres" + "ql:" + "//" + W_USER + ":" + W_PW + "@" + "db.example.invalid:5432/postgres?sslmode=require"
W_ENV = "TAPE_LIVE_W_DSN"
REDATE_ENV = "TAPE_LIVE_TEST_REDATE"
W_CONSTRAINT = {"tape_live_cycle": "tape_live_cycle_pk", "tape_live_events": "tape_live_events_grain_uq",
                "tape_live_wall": "tape_live_wall_pk"}
# conflict keys and the cycle grain, by hand from sql/2026-11-06_tape_live_tables.sql (_w2b_selftest compares them with the file)
W_PK = {"tape_live_cycle": ("symbol", "trading_day", "instrument_token", "ts_ist"),
        "tape_live_wall": ("symbol", "trading_day", "expiry", "ts_ist"),
        "tape_live_label": ("symbol", "trading_day", "ts_ist", "wall", "rule_version")}
W_GRAIN = {"tape_live_cycle": ("symbol", "trading_day", "expiry", "strike", "leg", "ts_ist"),
           "tape_live_events": ("symbol", "trading_day", "expiry", "strike", "leg", "kind", "ts_ist", "side")}
W_REASON = {"42501": "rls_refused", "53300": "connection_limit", "25P03": "idle_tx_timeout", "XX000": "other"}
W_DUR_BASE = {"tape_live_cycle": 11.0, "tape_live_events": 22.0, "tape_live_wall": 33.0, "tape_live_label": 44.0}
W_HOSTILE = ["it's", "back\\slash", "a,b;c", "line1\nline2", "ünï☃", "$$x$$ --c /*d*/", "'' ; DROP TABLE x; --",
             "  lead and trail  ", "tab\there", "q\"uote"]
W_HOSTILE_JSON = [json.dumps({"k": "it's \\ \"q\", ; -- $$"}), json.dumps({"note": "line1\nline2 ü", "b": [1, 2.5, None]})]
W_METRIC_COLS = tuple("%s_%s" % (p, t) for t in ("cycle", "events", "wall", "label")
                      for p in ("up_s", "up_max_stmt_s", "up_rows", "up_stmts")) + (
    "up_label_skipped", "cycle_grain_uq_violations", "up_proc_s", "write_state", "werr_statement_timeout", "werr_lock",
    "werr_idle_tx_timeout", "werr_rls_refused", "werr_connection_limit", "werr_connect", "werr_other")
_AWS_KEYS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")


def w_dur(table, k, ordn):
    """The planted server time of the k-th INSERT of a table in the ordn-th write script, in ms. By hand."""
    if ordn == 3 and table == "tape_live_cycle" and k == 0:
        return 5300.0
    return W_DUR_BASE[table] + 3.0 * k


def pg_time(ms):
    s = "Time: %.3f ms" % ms
    if ms >= 1000.0:
        t = ms / 1000.0
        h, m = int(t // 3600), int((t % 3600) // 60)
        s += (" (%02d:%06.3f)" % (m, t % 60)) if h == 0 else (" (%02d:%02d:%06.3f)" % (h, m, t % 60))
    return s


# ---- scanning and parsing a write script (the test's own, written from the plan)
def sql_split(script):
    """-> (psql meta lines, statements, unterminated tail). Quote-aware: ';' and newlines inside '...' ('' escapes) never split;
    a line whose first non-blank character, at a statement start, is a backslash is a psql meta-command."""
    metas, stmts, cur = [], [], []
    i, n, in_q, at_start = 0, len(script), False, True
    while i < n:
        c = script[i]
        if in_q:
            cur.append(c)
            if c == "'":
                if i + 1 < n and script[i + 1] == "'":
                    cur.append("'")
                    i += 2
                    continue
                in_q = False
        elif c == "'":
            in_q, at_start = True, False
            cur.append(c)
        elif at_start and c == "\\":
            j = script.find("\n", i)
            j = n if j < 0 else j
            metas.append(script[i:j].strip())
            i = j
        elif c == ";":
            stmts.append("".join(cur).strip())
            cur, at_start = [], True
        else:
            if not c.isspace():
                at_start = False
            cur.append(c)
        i += 1
    return metas, [s for s in stmts if s], "".join(cur).strip()


_W_LIT = re.compile(r"\s*(?:(NULL)\b|'((?:[^']|'')*)')(?:\s*::\s*([A-Za-z_][A-Za-z0-9_]*(?: precision)?))?", re.S)
_W_WS = re.compile(r"\s*")


def parse_insert(stmt):
    """INSERT INTO public.<t> (cols) VALUES (...),(...) <rest>  ->  {table, cols, rows (None | text), types (per row), conflict}."""
    m = re.match(r"INSERT\s+INTO\s+public\.(\w+)\s*\(([^)]*)\)\s*VALUES\s*", stmt, re.S | re.I)
    if m is None:
        raise ValueError("not an INSERT into public.<table>")
    cols = [c.strip() for c in m.group(2).split(",")]
    pos, rows, tys = m.end(), [], []
    while True:
        pos = _W_WS.match(stmt, pos).end()
        if stmt[pos:pos + 1] != "(":
            raise ValueError("expected ( at %d" % pos)
        pos += 1
        row, ty = [], []
        while True:
            lm = _W_LIT.match(stmt, pos)
            if lm is None:
                raise ValueError("bad literal at %d" % pos)
            row.append(None if lm.group(1) else lm.group(2).replace("''", "'"))
            ty.append(lm.group(3))
            pos = _W_WS.match(stmt, lm.end()).end()
            if stmt[pos:pos + 1] == ",":
                pos += 1
                continue
            if stmt[pos:pos + 1] == ")":
                pos += 1
                break
            raise ValueError("unexpected %r at %d" % (stmt[pos:pos + 1], pos))
        rows.append(row)
        tys.append(ty)
        pos = _W_WS.match(stmt, pos).end()
        if stmt[pos:pos + 1] == ",":
            pos += 1
            continue
        break
    rest = " ".join(stmt[pos:].split())
    cm = re.match(r"^ON CONFLICT ON CONSTRAINT (\w+) DO UPDATE SET (.+)$", rest, re.I)
    if cm is not None:
        sets = re.findall(r"(\w+)\s*=\s*(EXCLUDED\.\w+)", cm.group(2))
        if ", ".join("%s = %s" % s for s in sets).lower() != cm.group(2).lower():
            conflict = {"action": "other", "raw": rest}
        else:
            conflict = {"action": "update", "constraint": cm.group(1), "set": sets, "raw": rest}
    elif re.match(r"^ON CONFLICT DO NOTHING$", rest, re.I):
        conflict = {"action": "nothing", "constraint": None, "raw": rest}
    else:
        conflict = {"action": "other", "raw": rest}
    return {"table": m.group(1), "cols": cols, "rows": rows, "types": tys, "conflict": conflict, "rest": rest}


def parse_script(text):
    metas, stmts, tail = sql_split(text)
    out = []
    for s in stmts:
        d = {"text": s, "kind": s.split(None, 1)[0].upper() if s.split() else ""}
        if d["kind"] == "INSERT":
            d["insert"] = parse_insert(s)
        out.append(d)
    return {"metas": metas, "stmts": out, "tail": tail}


def strip_literals(s):
    return re.sub(r"'(?:[^']|'')*'", "''", s, flags=re.S)


def sql_types():
    """({table: {column: type}}, {table: {NOT NULL columns}}) parsed from the committed SQL file."""
    if "sql_types" not in _CACHE:
        with open(SQL, encoding="utf-8") as fh:
            text = fh.read()
        ty, nn = {}, {}
        for t in DB_TABLES:
            body = re.search(r"CREATE TABLE IF NOT EXISTS public\.%s \((.*?)\n\);" % t, text, re.S).group(1)
            ty[t], nn[t] = {}, set()
            for ln in body.strip().split("\n"):
                ln = ln.strip().rstrip(",")
                if not ln or ln.startswith("CONSTRAINT"):
                    continue
                parts = ln.split()
                ty[t][parts[0]] = "double precision" if parts[1] == "double" else parts[1]
                if "NOT NULL" in ln:
                    nn[t].add(parts[0])
        _CACHE["sql_types"] = (ty, nn)
    return _CACHE["sql_types"]


# ---- the fake database: typed values, the DDL's keys, RLS, atomic scripts
class SqlError(Exception):
    def __init__(self, state):
        Exception.__init__(self, state)
        self.state = state


def pg_norm(ty, text):
    """The typed value Postgres would hold for a literal of a type (hashable); an invalid one is SQLSTATE 22P02."""
    if text is None:
        return None
    try:
        if ty == "text":
            return text
        if ty == "numeric":
            d = decimal.Decimal(text)
            if not d.is_finite():
                raise ValueError("nan")
            return d.normalize()
        if ty in ("bigint", "integer"):
            return int(text)
        if ty == "double precision":
            return float(text)
        if ty == "date":
            return datetime.strptime(text, "%Y-%m-%d").date()
        if ty == "timestamptz":
            return fake_pg_ts(text).astimezone(timezone.utc)
        if ty == "boolean":
            v = text.strip().lower()
            if v in ("true", "t", "yes", "y", "on", "1"):
                return True
            if v in ("false", "f", "no", "n", "off", "0"):
                return False
            raise ValueError("bool")
        if ty == "uuid":
            return str(uuid.UUID(text))
        if ty == "jsonb":
            return json.dumps(json.loads(text), sort_keys=True)
    except (ValueError, decimal.InvalidOperation, TypeError):
        raise SqlError("22P02")
    raise SqlError("42704")


def pg_jsonb(o):
    if isinstance(o, dict):
        ks = sorted(o, key=lambda k: (len(k.encode("utf-8")), k.encode("utf-8")))
        return "{" + ", ".join("%s: %s" % (json.dumps(k, ensure_ascii=False), pg_jsonb(o[k])) for k in ks) + "}"
    if isinstance(o, list):
        return "[" + ", ".join(pg_jsonb(x) for x in o) + "]"
    return json.dumps(o, ensure_ascii=False)


def pg_text(ty, text):
    """What `SELECT '<text>'::<ty>::text` prints under SET TIME ZONE 'UTC'."""
    v = pg_norm(ty, text)
    if ty == "numeric":
        return format(decimal.Decimal(text), "f")
    if ty == "timestamptz":
        s = v.strftime("%Y-%m-%d %H:%M:%S")
        if v.microsecond:
            s += (".%06d" % v.microsecond).rstrip("0")
        return s + "+00"
    if ty == "boolean":
        return "true" if v else "false"
    if ty == "jsonb":
        return pg_jsonb(json.loads(text))
    if ty == "date":
        return v.isoformat()
    return str(v)


class FakeTable:
    """The four tape_live_* tables as Postgres holds them (types, NOT NULL, the primary keys, the cycle grain unique, events'
    grain as its only key, RLS trading_day = today). A script is atomic: any error and nothing is applied."""

    def __init__(self, today):
        self.today = today
        self.cols = sql_columns()
        self.types, self.notnull = sql_types()
        self.rows = dict((t, {}) for t in DB_TABLES)
        self.grain = {}                                    # cycle only: grain key -> primary key

    def _key(self, t, row):
        if t == "tape_live_events":
            return tuple(row[c] for c in W_GRAIN[t])
        return tuple(row[c] for c in W_PK[t])

    def typed(self, t, text_row):
        """{column: typed value} of a text row (a dict column -> text | None)."""
        return dict((c, pg_norm(self.types[t][c], text_row.get(c))) for c in self.cols[t])

    def insert_foreign(self, t, text_row):
        row = self.typed(t, text_row)
        k = self._key(t, row)
        self.rows[t][k] = row
        if t == "tape_live_cycle":
            self.grain[tuple(row[c] for c in W_GRAIN[t])] = k

    def tuples(self, t):
        return set(tuple(r[c] for c in self.cols[t]) for r in self.rows[t].values())

    def text_tuple(self, t, text_row):
        """The typed tuple of a text row given in DDL column order ('' = NULL), comparable with tuples()."""
        return tuple(pg_norm(self.types[t][c], None if v == "" else v) for c, v in zip(self.cols[t], text_row))

    def run(self, parsed):
        """Apply a parsed script. -> [{kind, table, k, n, sent}] in statement order, or raises SqlError."""
        rows = dict((t, dict(v)) for t, v in self.rows.items())
        grain = dict(self.grain)
        out, per_table = [], {}
        today = datetime.strptime(self.today, "%Y-%m-%d").date()
        for st in parsed["stmts"]:
            kind = st["kind"]
            if kind in ("BEGIN", "SET", "COMMIT", "ROLLBACK"):
                out.append({"kind": kind})
                continue
            if kind != "INSERT":
                raise SqlError("42601")
            ins = st["insert"]
            t = ins["table"]
            if t not in rows:
                raise SqlError("42P01")
            cf, touched, n = ins["conflict"], set(), 0
            for vals, tys in zip(ins["rows"], ins["types"]):
                if len(vals) != len(ins["cols"]):
                    raise SqlError("42601")
                text_row = dict(zip(ins["cols"], vals))
                for c, ty in zip(ins["cols"], tys):
                    if c not in self.types[t]:
                        raise SqlError("42703")
                    if ty is not None and ty != self.types[t][c]:
                        raise SqlError("42804")
                row = self.typed(t, text_row)
                if any(row[c] is None for c in self.notnull[t]):
                    raise SqlError("23502")
                if row["trading_day"] != today:
                    raise SqlError("42501")
                pk = self._key(t, row)
                g = tuple(row[c] for c in W_GRAIN[t]) if t == "tape_live_cycle" else None
                if cf["action"] == "nothing":
                    if pk in rows[t]:
                        continue
                    rows[t][pk] = row
                    n += 1
                    continue
                if cf["action"] != "update" or cf["constraint"] != W_CONSTRAINT.get(t):
                    raise SqlError("42704")
                if pk in touched:
                    raise SqlError("21000")
                touched.add(pk)
                old = rows[t].get(pk)
                if old is not None:
                    for c, e in cf["set"]:
                        if e != "EXCLUDED." + c:
                            raise SqlError("42703")
                    new = dict(old)
                    for c, _e in cf["set"]:
                        new[c] = row[c]
                    row = new
                    if t == "tape_live_cycle":
                        g2 = tuple(row[c] for c in W_GRAIN[t])
                        if grain.get(g2, pk) != pk:
                            raise SqlError("23505")
                        grain.pop(tuple(old[c] for c in W_GRAIN[t]), None)
                        grain[g2] = pk
                elif t == "tape_live_cycle":
                    if g in grain:
                        raise SqlError("23505")
                    grain[g] = pk
                rows[t][pk] = row
                n += 1
            k = per_table.get(t, 0)
            per_table[t] = k + 1
            out.append({"kind": "INSERT", "table": t, "k": k, "n": n, "sent": len(ins["rows"])})
        self.rows, self.grain = rows, grain
        return out


def w_default_check():
    priv = dict((t, {"DELETE": "f", "TRUNCATE": "f", "INSERT": "t", "UPDATE": "t"}) for t in DB_TABLES)
    priv["tape_live_label"]["UPDATE"] = "f"
    return {"role": W_USER, "super": "f", "bypassrls": "f", "scs": "on", "ist_date": None, "priv": priv}


def w_check_csv(chk, today):
    rows = [["role", chk["role"]], ["super", chk["super"]], ["bypassrls", chk["bypassrls"]], ["scs", chk["scs"]],
            ["ist_date", chk.get("ist_date") or today]]
    for t in DB_TABLES:
        for p in ("DELETE", "TRUNCATE", "INSERT", "UPDATE"):
            rows.append(["priv", t, p, chk["priv"][t][p]])
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return buf.getvalue()


class _Crash(BaseException):
    """A process death planted by the fake: not an Exception, so nothing in the runner can catch it."""


def _committed_now(day_dir):
    try:
        with open(os.path.join(day_dir, "state.json"), encoding="utf-8") as fh:
            return json.load(fh).get("committed")
    except (OSError, ValueError):
        return None


class FakeWriteShell:
    """live_sources.RUN for a run with the writer: read calls go to the unchanged FakeShell; calls carrying the write role's
    password are the write sink's: a start-up check, a literal check or a script, applied to a FakeTable. Plants, keyed
    ("n", k) = the k-th script or ("T", m) = the first script at grid minute m: err (an SQLSTATE | connect | conn_text | timeout
    | stderr_secret), slow (seconds added to the runner's clock of cpu-free time), crash_before / crash_after (the process dies),
    kill (the KILL file appears after the call), preload (a function(table, parsed))."""

    def __init__(self, inner, table, day_dir, plants=None, check=None, dur=None, kill_path=None, *, day):
        datetime.strptime(day, "%Y-%m-%d")            # the run's own trading day, required: no fallback to the fixture DAY
        self.inner, self.table, self.day_dir, self.day = inner, table, day_dir, day
        self.plants, self.dur, self.kill_path = dict(plants or {}), dur or w_dur, kill_path
        self.check = check if check is not None else w_default_check()
        self.wcalls, self.nwrite, self.perf_offset, self.misrouted = [], 0, 0.0, []
        self.lit_corrupt, self._tfired = None, set()
        self.calls = inner.calls

    @property
    def raised(self):
        return self.inner.raised

    def _T(self):
        m = int((rmods()[0].SimClock.last_now - ist_epoch(0, day=self.day)) // 60)
        return m - m % 5

    def __call__(self, argv, env, stdin, timeout):
        if argv and argv[0] == "psql":
            if env.get("PGPASSWORD") == W_PW:
                return self._w(argv, env, stdin, timeout)
            if stdin is not None and b"INSERT INTO" in stdin:
                self.misrouted.append((list(argv), dict(env)))
                return 3, b"", b"ERROR:  XX000\n"
        return self.inner(argv, env, stdin, timeout)

    def _w(self, argv, env, stdin, timeout):
        text = stdin.decode("utf-8")
        up = text.upper()
        kind = "write" if "INSERT INTO" in up else ("litcheck" if "READ ONLY" in up else "check")
        T = self._T()
        rec = {"kind": kind, "argv": list(argv), "env": dict(env), "stdin": stdin, "timeout": timeout, "T": T, "text": text,
               "committed_at_call": _committed_now(self.day_dir)}
        self.wcalls.append(rec)
        if kind == "check":
            return 0, w_check_csv(self.check, self.table.today).encode(), b""
        if kind == "litcheck":
            return self._lit(text)
        self.nwrite += 1
        ordn = rec["ord"] = self.nwrite
        plant = dict(self.plants.get(("n", ordn)) or {})
        if ("T", T) in self.plants and ("T", T) not in self._tfired:
            self._tfired.add(("T", T))
            plant.update(self.plants[("T", T)])
        hhmm = "%02d%02d" % (T // 60, T % 60)
        cdir = os.path.join(self.day_dir, "live", "cycles")
        rec["files"] = {}
        if os.path.isdir(cdir):
            for n in sorted(os.listdir(cdir)):
                if n.startswith(hhmm + "_") or n.startswith("final_"):
                    rec["files"][n] = sha(os.path.join(cdir, n))
        rec["parsed"] = parse_script(text)
        res = self._apply(rec, plant, ordn)
        if plant.get("kill") and self.kill_path:
            with open(self.kill_path, "w") as fh:
                fh.write("")
        if plant.get("crash_after"):
            raise _Crash()
        return res

    def _apply(self, rec, plant, ordn):
        if plant.get("preload"):
            plant["preload"](self.table, rec["parsed"])
        if plant.get("slow"):
            self.perf_offset += plant["slow"]
        if plant.get("crash_before"):
            raise _Crash()
        err = plant.get("err")
        if err == "connect":
            return 2, b"", b'psql: error: connection to server at "db.example.invalid" (203.0.113.7), port 5432 failed: could not translate host name\n'
        if err == "conn_text":
            return 2, b"", b'psql: error: connection to server at "db.example.invalid" (203.0.113.7), port 5432 failed: FATAL:  too many connections for role "tape_w"\n'
        if err == "pooler_text":
            return 2, b"", b'psql: error: connection to server at "pooler.example.invalid" (203.0.113.9), port 5432 failed: FATAL:  (EMAXCONNSESSION) max clients reached in session mode\n'
        if err == "timeout":
            return 124, b"", b"timeout"
        if err == "stderr_secret":
            return 3, b"", ("ERROR:  XX000 %s %s\n" % (W_PW, STDERR_MARK)).encode()
        if err:
            return 3, b"", ("ERROR:  %s\n" % err).encode()
        if "\x00" in rec["text"]:
            return 3, b"", b"ERROR:  22021\n"
        try:
            res = self.table.run(rec["parsed"])
        except SqlError as exc:
            return 3, b"", ("ERROR:  %s\n" % exc.state).encode()
        rec["tags"] = res
        lines = ["Timing is on."]
        for r in res:
            if r["kind"] == "INSERT":
                lines += ["INSERT 0 %d" % r["n"], pg_time(self.dur(r["table"], r["k"], ordn))]
            else:
                lines += [r["kind"], pg_time(0.2)]
        return 0, ("\n".join(lines) + "\n").encode(), b""

    def _lit(self, text):
        metas, stmts, _tail = sql_split(text)
        buf, i = io.StringIO(), 0
        wr = csv.writer(buf, lineterminator="\n")
        for s in stmts:
            if s.split()[0].upper() != "SELECT":
                continue
            m = re.search(r"'((?:[^']|'')*)'\s*::\s*(\w+(?: precision)?)", s, re.S)
            if m is None:
                return 3, b"", b"ERROR:  42601\n"
            try:
                v = pg_text(m.group(2), m.group(1).replace("''", "'"))
            except SqlError as exc:
                return 3, b"", ("ERROR:  %s\n" % exc.state).encode()
            wr.writerow([v + "X" if self.lit_corrupt == i else v])
            i += 1
        return 0, buf.getvalue().encode("utf-8"), b""


# ---- plants on the writer's own rows (test side only; the files carry the same rows the writer is told to send)
@contextlib.contextmanager
def ld_plant(db_rows=None, before_db_cycle=None, after_label=None):
    """Wrap LiveDay._db_rows / _db_cycle / _label for one run. db_rows(self, table, rows, as_of) edits `rows` (dict key -> data
    list) by REPLACING entries; before_db_cycle(self, as_of) may edit self.walls; after_label(self, T, as_of) may edit
    self.labels. The writer's own state (state_c, state_e) is never touched: only the DB-shaped rows are."""
    LD = mods()[5].LiveDay
    o_rows, o_cycle, o_label = LD._db_rows, LD._db_cycle, LD._label

    def rows_w(self, table, state):
        rows = o_rows(self, table, state)
        if db_rows is not None:
            db_rows(self, table, rows, getattr(self, "_plant_asof", ""))
        return rows

    def cycle_w(self, as_of):
        self._plant_asof = as_of
        if before_db_cycle is not None:
            before_db_cycle(self, as_of)
        return o_cycle(self, as_of)

    def label_w(self, T, walls, c_text, e_text, as_of):
        r = o_label(self, T, walls, c_text, e_text, as_of)
        if after_label is not None:
            after_label(self, T, as_of)
        return r
    LD._db_rows, LD._db_cycle, LD._label = rows_w, cycle_w, label_w
    try:
        yield
    finally:
        LD._db_rows, LD._db_cycle, LD._label = o_rows, o_cycle, o_label


def _utc_text(ts):
    return datetime.fromisoformat(ts).astimezone(timezone.utc).isoformat()


def plant_hostile():
    """Hostile text in rows of all four tables (cycle tradingsymbol, events detail_json, wall chain_run_id, label reason)."""
    from services.tape_live import dbshape
    cc, ec = dbshape.COLUMNS["tape_live_cycle"], dbshape.COLUMNS["tape_live_events"]
    rules_ = mods()[2]
    t10 = DAY + "T10:00:00+05:30"

    def db_rows(self, table, rows, as_of):
        if table == "tape_live_cycle":
            ti = cc.index("ts_ist")
            sel = sorted(k for k, d in rows.items() if d[ti] == t10)[:len(W_HOSTILE)]
            for i, k in enumerate(sel):
                d = list(rows[k])
                d[cc.index("tradingsymbol")] = W_HOSTILE[i]
                rows[k] = d
        elif table == "tape_live_events":
            si, ki, ti = ec.index("symbol"), ec.index("kind"), ec.index("ts_ist")
            for k, d in list(rows.items()):
                for j, hh in enumerate(("T11:05:00", "T12:05:00")):
                    if d[si] == "NIFTY" and d[ki] == "CONC" and d[ti].startswith(DAY + hh):
                        d = list(d)
                        d[ec.index("detail")] = W_HOSTILE_JSON[j]
                        rows[k] = d

    def before(self, as_of):
        w = self.walls.get(("NIFTY", t10))
        if w is not None:
            w["chain_run_id"] = W_HOSTILE[4]

    def after(self, T, as_of):
        r = self.labels.get(("NIFTY", DAY, t10, "call", rules_.RULE_VERSION))
        if r is not None:
            r["reason"] = W_HOSTILE[5]
    return ld_plant(db_rows, before, after)


def plant_dup(kind, at_first=True):
    """A second row whose DB conflict key equals another row's, by VALUE (the same instant written in UTC, or a numeric written
    with another scale), but whose writer key differs: the case the write set's uniqueness check exists for."""
    from services.tape_live import dbshape
    cc, ec = dbshape.COLUMNS["tape_live_cycle"], dbshape.COLUMNS["tape_live_events"]
    done = {"n": 0}

    def db_rows(self, table, rows, as_of):
        if done["n"] or table != {"cycle": "tape_live_cycle", "events": "tape_live_events", "events_num": "tape_live_events",
                                  "cycle_tok": "tape_live_cycle"}.get(kind):
            return
        if kind == "cycle_tok":                           # one bigint token in two texts: 12345 and 012345
            k = sorted(rows)[0]
            d = list(rows[k])
            d[cc.index("instrument_token")] = "0" + d[cc.index("instrument_token")]
            rows[(k[0], k[1], "tok" + str(k[2]))] = d
            done["n"] = 1
        elif kind == "events_num":                        # one numeric strike in two scales: 24000 and 24000.0, same instant text
            if rows:
                k = sorted(rows)[0]
                d1 = list(rows.pop(k))
                d1[ec.index("strike")] = "24000"
                d2 = list(d1)
                d2[ec.index("strike")] = "24000.0"
                rows[tuple(d1[1:8])], rows[tuple(d2[1:8])] = d1, d2
                done["n"] = 1
        elif kind == "cycle":
            k = sorted(rows)[0]
            d = list(rows[k])
            d[cc.index("ts_ist")] = _utc_text(d[cc.index("ts_ist")])
            rows[(k[0], k[1], d[cc.index("ts_ist")])] = d
            done["n"] = 1
        elif kind == "events":
            if rows:
                k = sorted(rows)[0]                       # two rows, strike NULL in both (NULLS NOT DISTINCT), one instant in two texts
                d1 = list(rows.pop(k))
                d1[ec.index("strike")] = ""
                d2 = list(d1)
                d2[ec.index("ts_ist")] = _utc_text(d1[ec.index("ts_ist")])
                rows[tuple(d1[1:8])], rows[tuple(d2[1:8])] = d1, d2
                done["n"] = 1

    def before(self, as_of):
        if kind == "wall" and not done["n"] and self.walls:
            k = sorted(self.walls)[-1]
            alt = _utc_text(k[1])
            self.walls[(k[0], alt)] = dict(self.walls[k], ts_ist=alt)
            done["n"] = 1

    def after(self, T, as_of):
        if kind == "label" and not done["n"] and self.labels:
            k = sorted(self.labels)[0]
            alt = _utc_text(k[2])
            self.labels[(k[0], k[1], alt, k[3], k[4])] = dict(self.labels[k], ts_ist=alt)
            done["n"] = 1
    return ld_plant(db_rows, before, after)


def plant_nul():
    from services.tape_live import dbshape
    cc = dbshape.COLUMNS["tape_live_cycle"]
    done = {"n": 0}

    def db_rows(self, table, rows, as_of):
        if table == "tape_live_cycle" and not done["n"] and rows:
            k = sorted(rows)[0]
            d = list(rows[k])
            d[cc.index("tradingsymbol")] = "A\x00B"
            rows[k] = d
            done["n"] = 1
    return ld_plant(db_rows)


def plant_remap(mode, from_asof, old="10103", new="99103"):
    """Token remap at the DB boundary (cycle.py:92 raises on two tokens for one strike-leg, so a remap cannot come through the
    real pipeline; plan section 2's gen_live remap variant is replaced by this plant). mode 'all': from from_asof on every row of
    NIFTY's old token is re-keyed to the new token (the old rows stay in the table: cross-cycle grain collisions). mode 'inset':
    once, at the first cycle at or after from_asof, the old token's newest row is duplicated under the new token (the collision
    is inside one write set, with different primary keys)."""
    from services.tape_live import dbshape
    cc = dbshape.COLUMNS["tape_live_cycle"]
    si, ki, ti = cc.index("symbol"), cc.index("instrument_token"), cc.index("ts_ist")
    key = mods()[5]._db_key
    state = {"fired": False}

    def db_rows(self, table, rows, as_of):
        if table != "tape_live_cycle" or as_of < from_asof:
            return
        sel = [k for k, d in rows.items() if d[si] == "NIFTY" and d[ki] == old]
        if mode == "all":
            for k in sel:
                d = list(rows.pop(k))
                d[ki] = new
                rows[key("tape_live_cycle", d + ["", "", ""])] = d
        elif mode == "inset" and not state["fired"] and sel:
            state["fired"] = True
            k = max(sel, key=lambda x: x[2])
            d = list(rows[k])
            d[ki] = new
            rows[key("tape_live_cycle", d + ["", "", ""])] = d
    return ld_plant(db_rows)


# ---- running the CLI against the fakes
def quiet_exit(fn, *a):
    buf_o, buf_e = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(buf_o), contextlib.redirect_stderr(buf_e):
            rc = fn(*a)
    except SystemExit as exc:                      # argparse: an unknown flag is SystemExit(2)
        rc = exc.code if isinstance(exc.code, int) else 2
    return rc, buf_o.getvalue() + buf_e.getvalue()


def _dbw():
    """services.tape_live.dbwrite, or None while it does not exist (red first)."""
    try:
        return importlib.import_module("services.tape_live.dbwrite")
    except ImportError:
        return None


def epoch_raw():
    if "epoch_raw" not in _CACHE:
        _CACHE["epoch_raw"] = gen_live.build(os.path.join(_TMP, "epoch_w"), epoch=True)
    return _CACHE["epoch_raw"]


_W_TABLE = {"t": None}


def w_cli(name=None, out=None, fix=None, arrival=None, day=DAY, start="15:20", rows=7, plants=None, db_write=True, w_env=True,
          flags=(), env=None, now_date=DAY, server_date=None, check=False, chk=None, plant=None, table=None, ro_dsn=None,
          sha=None, clock="sim", dur=None):
    """cli live on a fixture day through FakeWriteShell. Cached by name unless `out` is given (a restart of the same day)."""
    if name is not None and out is None and name in _CACHE:
        return _CACHE[name]
    cli = mods()[0]
    ls = rmods()[1]
    f = fix or fixture()
    d = out or os.path.join(_TMP, "w_" + name)
    tbl = table or FakeTable(server_date or now_date or DAY)
    _W_TABLE["t"] = tbl
    inner = FakeShell(f["raw"], f["chain"], cli.local_schedule(f["raw"], DAY, dict(arrival or {})))
    fake = FakeWriteShell(inner, tbl, os.path.join(d, DAY), plants, chk, dur, kill_path=os.path.join(d, "KILL"), day=DAY)
    argv = ["live", "--day", day, "--out", d, "--source", "s3", "--chain", "psql", "--clock", clock, "--start", start,
            "--bucket", "meridian-tape-raw", "--disk-floor-mb", "20", "--rss-cap-mb", "100000"]
    if db_write:
        argv += ["--db-write", "--db-batch-rows", str(rows)]
    argv += list(flags)
    if check:
        argv.append("--check")
    envv = {"TAPE_LIVE_RO_DSN": ro_dsn or TEST_DSN}
    if w_env:
        envv[W_ENV] = W_DSN
    envv.update(env or {})
    dbw, prev_now = _dbw(), None
    saved_run, saved_info, perf = ls.RUN, _cli0.code_info, time.perf_counter
    ls.RUN = fake
    if dbw is not None and hasattr(dbw, "now_ist") and now_date:
        prev_now = dbw.now_ist
        y, mo, dd = (int(x) for x in now_date.split("-"))
        dbw.now_ist = lambda: _REAL_DT(y, mo, dd, 10, 0, 0, tzinfo=IST)
    time.perf_counter = lambda: perf() + fake.perf_offset
    if sha:
        _cli0.code_info = lambda: {"git_sha": sha, "dirty": False}
    crashed, w_left = False, False
    try:
        with (plant() if plant else contextlib.nullcontext()), _env(envv, drop=_AWS_KEYS), strict_iso():
            try:
                rc, log = quiet_exit(cli.main, argv)
            except _Crash:
                rc, log, crashed = "CRASH", "", True
            w_left = W_ENV in os.environ
    finally:
        time.perf_counter, ls.RUN, _cli0.code_info = perf, saved_run, saved_info
        if prev_now is not None:
            dbw.now_ist = prev_now
    res = types.SimpleNamespace(rc=rc, out=d, root=os.path.join(d, DAY), fake=fake, table=tbl, log=log, w_left=w_left,
                                crashed=crashed, argv=argv)
    if name is not None and out is None:
        _CACHE[name] = res
    return res


def w_phases(name, phases, **common):
    """Run the same day several times on one out dir and one FakeTable (kill / crash then restart). -> [result per phase]."""
    if name in _CACHE:
        return _CACHE[name]
    d = os.path.join(_TMP, "w_" + name)
    tbl = FakeTable(common.get("now_date") or DAY)
    out = []
    for ph in phases:
        ph = dict(ph)
        pre = ph.pop("pre", None)
        kp = os.path.join(d, "KILL")
        if os.path.exists(kp):
            os.remove(kp)
        if pre is not None:
            pre(os.path.join(d, DAY))
        out.append(w_cli(None, out=d, table=tbl, **dict(common, **ph)))
    _CACHE[name] = out
    return out


def plants_of(*ps):
    return dict((("n", i + 1), p) for i, p in enumerate(ps) if p)


def w_canon():
    """The epoch day, the whole day, N = 7, hostile text in all four tables, one preloaded duplicate label (ordinal 5)."""
    def pre_label(table, parsed):
        ins = [s["insert"] for s in parsed["stmts"] if s.get("insert") and s["insert"]["table"] == "tape_live_label"][0]
        table.insert_foreign("tape_live_label", dict(zip(ins["cols"], ins["rows"][0])))
    # No timing plant (removed with ruling R9-B): item 7a needs an excess over the 09:20 window median above 30 s, which this
    # fixture's sub-second cycles cannot reach, so the canon run also checks end to end that ordinary drop bumps do not stop it.
    plants = {("n", 5): {"preload": pre_label}}
    return w_cli("canon", fix=epoch_raw(), arrival=gen_live.EPOCH_ARRIVAL, start="08:50", rows=7,
                 plants=plants, plant=plant_hostile, dur=w_dur)


def w_off(name, start="15:20", **kw):
    """The same short run with the flag off (no write environment): the reference for 'files unchanged'."""
    return w_cli(name, start=start, db_write=False, w_env=False, **kw)


# ---- reading what a run left
def live_of(res):
    return os.path.join(res.root, "live")


def w_metrics(res):
    with open(os.path.join(res.root, "live_metrics.csv"), encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def w_json(res, name):
    try:
        with open(os.path.join(res.root, name), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def w_scripts(res):
    return [c for c in res.fake.wcalls if c["kind"] == "write"]


def sent_rows(call):
    """{table: [row tuples]} of a script, '' for NULL (the form of the .db.csv files)."""
    out = {}
    for s in call["parsed"]["stmts"]:
        if s.get("insert"):
            ins = s["insert"]
            out.setdefault(ins["table"], []).extend(tuple("" if v is None else v for v in r) for r in ins["rows"])
    return out


def cycle_names(res):
    cdir = os.path.join(live_of(res), "cycles")
    return sorted({n.split("_")[0] for n in os.listdir(cdir) if n.endswith(".db.csv")}) if os.path.isdir(cdir) else []


def u_rows(res, name, t):
    p = os.path.join(live_of(res), "cycles", "%s_%s.db.csv" % (name, DB_PART[t]))
    if not os.path.exists(p):
        return []
    _h, rows = _db_read(p)
    return [tuple(r[1:]) for r in rows if r[0] == "U"]


def label_rows(res):
    h, rows = _db_read(os.path.join(live_of(res), "tape_live_label.db.csv"))
    return h, [tuple(r) for r in rows]


def ins_by_table(call):
    out = {}
    for s in call["parsed"]["stmts"]:
        if s.get("insert"):
            out.setdefault(s["insert"]["table"], []).append(s["insert"])
    return out


def need_run(res, what):
    """None if the run completed, else the failure text (red first: the write flags are unknown to argparse)."""
    if res.rc == 0:
        return None
    tail = " | ".join(res.log.strip().splitlines()[-2:])[:220]
    return "%s: rc=%s%s %s" % (what, res.rc, " (argparse: unrecognized arguments, the write flags do not exist)"
                               if "unrecognized arguments" in res.log else "", tail)


def w_stmt_findings(t, ins, n_max):
    """Findings on ONE parsed INSERT against the plan: column list, batch size, conflict clause, SET list."""
    bad = []
    cols = sql_columns()[t]
    if ins["cols"] != cols:
        bad.append("3g %s: column list != the DDL's" % t)
    if len(ins["rows"]) > n_max:
        bad.append("3e %s: %d rows in one statement, N = %d" % (t, len(ins["rows"]), n_max))
    cf = ins["conflict"]
    if t == "tape_live_label":
        if cf["action"] != "nothing":
            bad.append("3k label: not ON CONFLICT DO NOTHING (%r)" % cf.get("raw"))
        elif cf.get("constraint") is not None:
            bad.append("3l label: DO NOTHING with a target")
    else:
        tag = {"tape_live_cycle": "3h", "tape_live_events": "3i", "tape_live_wall": "3j"}[t]
        if cf["action"] != "update" or cf.get("constraint") != W_CONSTRAINT[t]:
            bad.append("%s %s: conflict clause %r, want ON CONFLICT ON CONSTRAINT %s DO UPDATE" % (tag, t, cf.get("raw"), W_CONSTRAINT[t]))
        else:
            want = [c for c in cols if c not in set(sql_key(t))]
            got = [c for c, _e in cf["set"]]
            if sorted(got) != sorted(want) or len(got) != len(set(got)):
                bad.append("3n %s: SET list %s != every non-key column %s" % (t, got, want))
    if re.search(r"\bRETURNING\b", strip_literals(ins_text(ins)), re.I):
        bad.append("3m %s: RETURNING" % t)
    return bad


def ins_text(ins):
    return ins["rest"]


# ---- the fakes' own checks: they must be able to fire without any writer
def _ref_literal(v, ty):
    return "NULL" if v is None else "'%s'::%s" % (v.replace("'", "''"), ty)


def w_ref_insert(t, text_rows, conflict=None):
    """A reference INSERT, rendered here from the plan: the control the fake and the finders are proven against."""
    cols, ty = sql_columns()[t], sql_types()[0][t]
    vals = ",\n".join("(" + ", ".join(_ref_literal(r.get(c), ty[c]) for c in cols) + ")" for r in text_rows)
    if conflict is None:
        if t == "tape_live_label":
            conflict = "ON CONFLICT DO NOTHING"
        else:
            keyset = set(sql_key(t))
            conflict = "ON CONFLICT ON CONSTRAINT %s DO UPDATE SET %s" % (
                W_CONSTRAINT[t], ", ".join("%s = EXCLUDED.%s" % (c, c) for c in cols if c not in keyset))
    return "INSERT INTO public.%s (%s) VALUES\n%s\n%s;" % (t, ", ".join(cols), vals, conflict)


def w_text_row(t, **over):
    ty = sql_types()[0][t]
    sample = {"text": "x", "numeric": "1", "bigint": "1", "date": DAY, "timestamptz": DAY + "T10:00:00+05:30", "boolean": "true",
              "uuid": "00000000-0000-5000-8000-000000000001", "jsonb": "{}", "integer": "1", "double precision": "1.5"}
    row = dict((c, sample[ty[c]]) for c in sql_columns()[t])
    row.update(over)
    return row


def _w2b_selftest():
    """Rule 0 for the fakes: each can fire. -> findings (empty = all fire as they must)."""
    bad = []
    cols = sql_columns()
    for t, k in (("tape_live_cycle", W_PK["tape_live_cycle"]), ("tape_live_wall", W_PK["tape_live_wall"]),
                 ("tape_live_label", W_PK["tape_live_label"])):
        if tuple(sql_key(t)) != k:
            bad.append("selftest: W_PK[%s] %s != the SQL file's %s" % (t, k, sql_key(t)))
    if tuple(sql_key("tape_live_events")) != W_GRAIN["tape_live_events"]:
        bad.append("selftest: events grain differs from the SQL file")
    with open(SQL, encoding="utf-8") as fh:
        m = re.search(r"CONSTRAINT tape_live_cycle_grain_uq UNIQUE NULLS NOT DISTINCT \(([^)]*)\)", fh.read())
    if tuple(c.strip() for c in m.group(1).split(",")) != W_GRAIN["tape_live_cycle"]:
        bad.append("selftest: cycle grain differs from the SQL file")
    # the scanner and the parser: hostile values survive, a ';' inside a literal does not split
    rows = [w_text_row("tape_live_cycle", tradingsymbol=v) for v in W_HOSTILE + [None, ""]]
    script = "\\set ON_ERROR_STOP 1\n\\timing on\nBEGIN;\n" + w_ref_insert("tape_live_cycle", rows) + "\nCOMMIT;\n"
    p = parse_script(script)
    got = [r[cols["tape_live_cycle"].index("tradingsymbol")] for r in p["stmts"][1]["insert"]["rows"]]
    if [s["kind"] for s in p["stmts"]] != ["BEGIN", "INSERT", "COMMIT"] or got != W_HOSTILE + [None, ""] or p["tail"]:
        bad.append("selftest: parse round trip failed: %s" % ([s["kind"] for s in p["stmts"]], got[:3]))
    if w_stmt_findings("tape_live_cycle", p["stmts"][1]["insert"], 12):
        bad.append("selftest: the reference script has findings: %s" % w_stmt_findings("tape_live_cycle", p["stmts"][1]["insert"], 12))
    broken = [("wrong target", w_ref_insert("tape_live_cycle", rows[:1]).replace("tape_live_cycle_pk", "tape_live_cycle_grain_uq")),
              ("returning", w_ref_insert("tape_live_cycle", rows[:1])[:-1] + " RETURNING 1;"),
              ("short set", w_ref_insert("tape_live_cycle", rows[:1]).replace("as_of = EXCLUDED.as_of, ", "")),
              ("label update", w_ref_insert("tape_live_label", [w_text_row("tape_live_label")], "ON CONFLICT ON CONSTRAINT tape_live_label_pk DO UPDATE SET label = EXCLUDED.label"))]
    for what, s in broken:
        t = "tape_live_label" if what == "label update" else "tape_live_cycle"
        if not w_stmt_findings(t, parse_script(s)["stmts"][0]["insert"], 12) and what != "returning":
            bad.append("selftest: a %s statement raised no finding" % what)
    if not w_stmt_findings("tape_live_cycle", parse_script(broken[1][1])["stmts"][0]["insert"], 12):
        bad.append("selftest: RETURNING raised no finding")
    # FakeTable
    tb = FakeTable(DAY)
    r1, r2 = w_text_row("tape_live_cycle", instrument_token="5", strike="1"), w_text_row("tape_live_cycle", instrument_token="6", strike="2")
    res = tb.run(parse_script("BEGIN;\n" + w_ref_insert("tape_live_cycle", [r1, r2]) + "\nCOMMIT;"))
    if [x.get("n") for x in res if x["kind"] == "INSERT"] != [2] or len(tb.rows["tape_live_cycle"]) != 2:
        bad.append("selftest: FakeTable did not insert two rows")

    def fires(label, state, script, t=None):
        before = dict((k, dict(v)) for k, v in tb.rows.items())
        try:
            tb.run(parse_script(script))
        except SqlError as exc:
            if exc.state != state:
                bad.append("selftest: %s raised %s, want %s" % (label, exc.state, state))
            if dict((k, dict(v)) for k, v in tb.rows.items()) != before:
                bad.append("selftest: %s changed the table (a script is atomic)" % label)
            return
        bad.append("selftest: %s raised nothing, want %s" % (label, state))
    fires("a duplicate conflict key by value (token 5 and 05)", "21000", w_ref_insert(
        "tape_live_cycle", [w_text_row("tape_live_cycle", instrument_token="5"), w_text_row("tape_live_cycle", instrument_token="05")]))
    fires("an events grain duplicate (strike NULL in both, one instant in two texts)", "21000", w_ref_insert(
        "tape_live_events", [w_text_row("tape_live_events", strike=None), w_text_row("tape_live_events", strike=None, ts_ist=DAY + "T04:30:00+00:00")]))
    fires("a grain collision with another primary key", "23505", w_ref_insert(
        "tape_live_cycle", [w_text_row("tape_live_cycle", instrument_token="7", strike="1")]))
    fires("a row of another trading day (RLS)", "42501", w_ref_insert("tape_live_cycle", [w_text_row("tape_live_cycle", instrument_token="8", trading_day="2026-11-05")]))
    fires("a NULL in a NOT NULL column", "23502", w_ref_insert("tape_live_cycle", [w_text_row("tape_live_cycle", instrument_token="9", symbol=None)]))
    fires("a non-number in a numeric column", "22P02", w_ref_insert("tape_live_cycle", [w_text_row("tape_live_cycle", instrument_token="9", strike="abc")]))
    lab = w_text_row("tape_live_label")
    a = tb.run(parse_script("BEGIN;\n" + w_ref_insert("tape_live_label", [lab]) + "\nCOMMIT;"))
    b = tb.run(parse_script("BEGIN;\n" + w_ref_insert("tape_live_label", [lab]) + "\nCOMMIT;"))
    if [x["n"] for x in a if x["kind"] == "INSERT"] != [1] or [x["n"] for x in b if x["kind"] == "INSERT"] != [0]:
        bad.append("selftest: DO NOTHING did not report 1 then 0 inserted rows")
    upd = tb.run(parse_script("BEGIN;\n" + w_ref_insert("tape_live_cycle", [dict(r1, buy_5="9")]) + "\nCOMMIT;"))
    if [x["n"] for x in upd if x["kind"] == "INSERT"] != [1] or len(tb.rows["tape_live_cycle"]) != 2:
        bad.append("selftest: an upsert on an existing key did not update in place")
    for ty, v, want in (("timestamptz", DAY + "T10:00:00+05:30", DAY + " 04:30:00+00"), ("numeric", "24000.0", "24000.0"),
                        ("jsonb", '{"b":1,"aa":2}', '{"b": 1, "aa": 2}'), ("boolean", "true", "true")):
        if pg_text(ty, v) != want:
            bad.append("selftest: pg_text(%s, %s) = %r, want %r" % (ty, v, pg_text(ty, v), want))
    if pg_time(5300.0) != "Time: 5300.000 ms (00:05.300)" or pg_time(12.0) != "Time: 12.000 ms":
        bad.append("selftest: pg_time format")
    return bad


# ---- the ten guards
GOLDEN = os.path.join(ROOT, "tests", "tape_live", "off_golden_56bf055.json")
W_ORDER = ("tape_live_cycle", "tape_live_events", "tape_live_wall", "tape_live_label")


def _hh(m):
    return "%02d:%02d" % (m // 60, m % 60)


def _nm(m):
    return "%02d%02d" % (m // 60, m % 60)


def _mog():
    """tests/tape_live/make_off_golden.py: the one form-2 digest both the golden and this guard use."""
    return importlib.import_module("make_off_golden")


def _arrival_size_etag(dd, raw):
    """1a, the two columns form 2 drops from arrival_log.csv: a segment or subscriptions row's size and etag are the size and md5
    of the fixture's own file at that key (what the fake listed and served); a chain_run row carries neither. Findings, [] if none."""
    bad, n = [], {"segment": 0, "subscriptions": 0, "chain_run": 0}
    with open(os.path.join(dd, "arrival_log.csv"), encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        k = r.get("kind")
        if k not in n:
            bad.append("1a arrival_log.csv: unknown kind %r at %s" % (k, r.get("key")))
            continue
        n[k] += 1
        if k == "chain_run":
            if r["size"] != "" or r["etag"] != "":
                bad.append("1a arrival_log.csv chain_run %s: size %r etag %r (want both empty)" % (r["key"], r["size"], r["etag"]))
            continue
        p = os.path.join(raw, *r["key"].split("/"))
        if not os.path.isfile(p):
            bad.append("1a arrival_log.csv %s: no fixture file at that key" % r["key"])
            continue
        if r["size"] != str(os.path.getsize(p)):
            bad.append("1a arrival_log.csv %s: size %s, the fixture file is %d bytes" % (r["key"], r["size"], os.path.getsize(p)))
        want = hashlib.md5(rd(p)).hexdigest()
        if r["etag"] != want:
            bad.append("1a arrival_log.csv %s: etag %s, the fixture file's md5 is %s" % (r["key"], r["etag"], want))
    if not n["segment"] or not n["subscriptions"] or not n["chain_run"]:
        bad.append("1a arrival_log.csv precondition: rows by kind %s (want every kind present; the size/etag check would be vacuous)" % n)
    return bad


def _off_1a(dd, gold, raw):
    """1a: every non-timing output file equals 56bf055's in form 2 (make_off_golden.py), and the dropped arrival_log.csv columns
    match the fixture. Findings, [] if none."""
    mog = _mog()
    if gold.get("form") != mog.FORM:
        return ["1a the golden is form %r, the guard compares form %r (regenerate it with tests/tape_live/make_off_golden.py)" % (
            gold.get("form"), mog.FORM)]
    try:
        got = mog.file_digests(dd, TIMING_FILES)
    except ValueError as exc:
        return ["1a %s" % exc]
    bad = []
    if got != gold["files"]:
        diff = sorted(k for k in set(got) | set(gold["files"]) if got.get(k) != gold["files"].get(k))
        bad.append("1a %d of %d output files differ from 56bf055 (first: %s)" % (len(diff), len(got), diff[:3]))
    return bad + _arrival_size_etag(dd, raw)


def g_2b_off():
    """Plan 9 guard 1: with the flag absent the runner is what it was at 56bf055. Red first: --db-write is unknown to argparse."""
    bad = []
    if not os.path.isfile(GOLDEN):
        return False, "tests/tape_live/off_golden_56bf055.json missing (tests/tape_live/make_off_golden.py writes it from a git archive of 56bf055)"
    with open(GOLDEN, encoding="utf-8") as fh:
        gold = json.load(fh)
    rc, root, fake, log, _left = cli_live_fake("eq_psql")
    dd = os.path.join(root, DAY)
    if rc != 0:
        return False, "1a flag-off run rc=%s %s" % (rc, log[-300:])
    bad += _off_1a(dd, gold, fixture()["raw"])
    with open(os.path.join(dd, "heartbeat.json"), encoding="utf-8") as fh:
        hb = json.load(fh)
    with open(os.path.join(dd, "state.json"), encoding="utf-8") as fh:
        st = json.load(fh)
    with open(os.path.join(dd, "live_metrics.csv"), encoding="utf-8", newline="") as fh:
        header = next(csv.reader(fh))
    if sorted(hb) != gold["heartbeat_keys"]:
        bad.append("1b heartbeat keys %s != 56bf055's" % sorted(set(hb) ^ set(gold["heartbeat_keys"])))
    if sorted(st) != gold["state_keys"]:
        bad.append("1c state.json keys %s != 56bf055's" % sorted(set(st) ^ set(gold["state_keys"])))
    if header != gold["metrics_header"] or len(header) != 27:
        bad.append("1d live_metrics.csv header is not the 27 columns of 56bf055 (%d columns)" % len(header))
    for argv, env, stdin, _t in fake.calls:
        if argv[0] == "psql" and (env.get("PGPASSWORD") == W_PW or re.search(r"(?i)\b(INSERT|UPDATE|DELETE|TRUNCATE)\b", (stdin or b"").decode("utf-8", "replace"))):
            bad.append("1e a write-shaped psql call with the flag off")
            break
    res = w_cli("off_wdsn", db_write=False, check=True, start="08:50")
    if res.rc != 2 or "unrecognized arguments" in res.log or res.fake.wcalls:
        bad.append("1f the write DSN without --db-write: rc=%s, %d write calls (want rc 2 before any connection)" % (res.rc, len(res.fake.wcalls)))
    on = w_cli("on_short", start="15:25")
    why = need_run(on, "1g flag on")
    if why:
        bad.append(why)
    else:
        miss = [c for c in W_METRIC_COLS if c not in w_metrics(on)[0]]
        if miss:
            bad.append("1g flag on: live_metrics.csv lacks %s" % miss[:4])
    stray = _latch_files(root, "WRITE_LATCH") + _latch_files(os.path.join(on.out), "WRITE_LATCH")
    if stray:
        bad.append("1h a latch file with the flag off or on a clean run: %s" % stray)
    return not bad, "; ".join(bad[:8]) or "flag off: %d files == 56bf055 (sha256, form 2: raw .gz unzipped, arrival_log.csv without size/etag; arrival size/etag checked against the fixture), heartbeat / state / 27-column header equal, no write call; the write DSN alone refused; flag on adds the %d write columns" % (len(gold["files"]), len(W_METRIC_COLS))


def g_2b_upsert_only():
    """Plan guard 2. Red first: services/tape_live/dbwrite.py does not exist."""
    bad = []
    dbw = _dbw()
    if dbw is None:
        return False, "ImportError: services.tape_live.dbwrite does not exist"
    path = os.path.join(LIVE, "dbwrite.py")
    tree, consts = _consts(path)
    skip = set()
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PRIV_PROBE" for t in n.targets):
            skip = set(id(c) for c in ast.walk(n.value))
    verbs = re.compile(r"(?i)\b(DELETE|TRUNCATE|DROP|ALTER|CREATE|GRANT|REVOKE|COPY|MERGE|CALL|VACUUM|REINDEX|CLUSTER|NOTIFY)\b")
    tables = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in skip:
            if verbs.search(n.value):
                bad.append("2a dbwrite.py:%d names a write verb outside PRIV_PROBE: %r" % (n.lineno, n.value[:50]))
            if re.search(r"\bINSERT\b", n.value, re.I):
                m = re.search(r"INSERT INTO public\.(tape_live_(?:cycle|events|wall|label))\b", n.value)
                if m is None:
                    bad.append("2b dbwrite.py:%d INSERT that is not one of the four templates: %r" % (n.lineno, n.value[:50]))
                else:
                    tables.add(m.group(1))
    if tables != set(W_ORDER):
        bad.append("2b INSERT templates found for %s, want all four tables" % sorted(tables))
    res = w_canon()
    why = need_run(res, "canon run")
    if why:
        return False, "; ".join(bad[:4] + [why])
    calls = w_scripts(res)
    ld = live_of(res)
    names = cycle_names(res)
    n_d = _count_d(ld)
    if not calls or not n_d:
        bad.append("precondition: %d write scripts, %d D lines in the files (the guard would be vacuous)" % (len(calls), n_d))
    for c in calls:
        if re.search(r"(?i)\b(DELETE|TRUNCATE)\b", strip_literals(c["text"])):
            bad.append("2c a DELETE or TRUNCATE in the script of cycle %s" % _hh(c["T"]))
            break
    matched = set()
    lh, lrows = label_rows(res)
    ai = lh.index("as_of")
    for c in calls:
        sent = sent_rows(c)
        cands = [_nm(c["T"])] + (["final"] if "final" in names else [])
        ok = None
        for nm in cands:
            if all(sorted(sent.get(t, [])) == sorted(u_rows(res, nm, t)) for t in DELTA_TABLES):
                ok = nm
                break
        if ok is None:
            bad.append("2d the script of %s != the U lines of its cycle's .db.csv files" % _hh(c["T"]))
            continue
        matched.add(ok)
        if ok != "final":
            want = sorted(r[:len(lh)] for r in lrows if r[ai] == mods()[0].as_of(DAY, _hm_min(ok[:2] + ":" + ok[2:])))
            if sorted(sent.get("tape_live_label", [])) != want:
                bad.append("2e cycle %s: %d label rows sent, %d new labels in tape_live_label.db.csv" % (_hh(c["T"]), len(sent.get("tape_live_label", [])), len(want)))
        for fn, h in c["files"].items():
            if sha(os.path.join(ld, "cycles", fn)) != h:
                bad.append("2f %s changed after the write call" % fn)
        if c["committed_at_call"] is not None and c["committed_at_call"] >= c["T"]:
            bad.append("2f state.json already committed %s when the script of %s was sent (write after commit)" % (c["committed_at_call"], _hh(c["T"])))
        for t in DELTA_TABLES:
            if sent.get(t) and ok != "final" and not any(fn.startswith(_nm(c["T"]) + "_") and fn.endswith(".db.csv") for fn in c["files"]):
                bad.append("2f the .db.csv files of %s did not exist at the write call" % _hh(c["T"]))
                break
    for nm in names:
        if any(u_rows(res, nm, t) for t in DELTA_TABLES) and nm not in matched:
            bad.append("2d cycle %s has U lines and no write" % nm)
            break
    return not bad, "; ".join(bad[:8]) or "%d scripts: no DELETE/TRUNCATE (%d D lines in the files), rows == the U lines and labels == the new labels of their cycles, files written first" % (len(calls), n_d)


def _count_d(ld):
    n = 0
    for fn in os.listdir(os.path.join(ld, "cycles")):
        if fn.endswith(".db.csv"):
            with open(os.path.join(ld, "cycles", fn), encoding="utf-8", newline="") as fh:
                n += sum(1 for line in fh if line.startswith("D,"))
    return n


def _calls_by_t(calls):
    out = {}
    for c in calls:
        out.setdefault(c["T"], []).append(c)
    return out


def g_2b_statements():
    """Plan guard 3. Red first: no renderer (the write flags are unknown)."""
    bad = _w2b_selftest()
    if bad:
        return False, "; ".join(bad[:6])
    res = w_canon()
    why = need_run(res, "canon run")
    if why:
        return False, why
    calls = w_scripts(res)
    unparsed = [c for c in calls if "parsed" not in c]
    if unparsed:
        return False, "3p %d of %d scripts did not parse with the test's own parser (a hostile value broke out of its quotes), first at %s" % (
            len(unparsed), len(calls), _hh(unparsed[0]["T"]))
    N = 7
    n_rows = n_stmt = 0
    for c in calls:
        p = c["parsed"]
        kinds = [s["kind"] for s in p["stmts"]]
        if p["tail"] or kinds[0] != "BEGIN" or kinds[-1] != "COMMIT" or kinds.count("COMMIT") != 1 or kinds.count("BEGIN") != 1:
            bad.append("3b %s: not exactly BEGIN ... COMMIT (%s)" % (_hh(c["T"]), kinds[:3] + kinds[-2:]))
        if "\\set ON_ERROR_STOP 1" not in [" ".join(m.split()) for m in p["metas"]]:
            bad.append("3b %s: no \\set ON_ERROR_STOP 1" % _hh(c["T"]))
        firsti = kinds.index("INSERT") if "INSERT" in kinds else len(kinds)
        pre = [" ".join(s["text"].split()).lower() for s in p["stmts"][:firsti]]
        if not any(re.match(r"^set local lock_timeout (=|to) '?(5s|5000|5000ms)'?$", x) for x in pre):
            bad.append("3c %s: no SET LOCAL lock_timeout = '5s' before the first INSERT" % _hh(c["T"]))
        if not any(re.match(r"^set local standard_conforming_strings (=|to) '?on'?$", x) for x in pre):
            bad.append("3d %s: no SET LOCAL standard_conforming_strings = on before the first INSERT" % _hh(c["T"]))
        by = ins_by_table(c)
        order = [s["insert"]["table"] for s in p["stmts"] if s.get("insert")]
        if order != sorted(order, key=W_ORDER.index):
            bad.append("3f %s: tables out of order %s" % (_hh(c["T"]), sorted(set(order), key=order.index)))
        for t, stmts in by.items():
            total = sum(len(i["rows"]) for i in stmts)
            if len(stmts) != -(-total // N):
                bad.append("3f %s %s: %d statements for %d rows at N = %d (want %d)" % (_hh(c["T"]), t, len(stmts), total, N, -(-total // N)))
            for i in stmts:
                bad += ["%s %s" % (_hh(c["T"]), f) for f in w_stmt_findings(t, i, N)]
            n_rows += total
            n_stmt += len(stmts)
        if not isinstance(c["stdin"], bytes) or max(len(a) for a in c["argv"]) > 200:
            bad.append("3t %s: the script is not whole on stdin / an argv element is long" % _hh(c["T"]))
        if "\x00" in c["text"]:
            bad.append("3r a NUL byte in a script")
    for T, cs in _calls_by_t(calls).items():
        if len(cs) > (2 if T == 15 * 60 + 45 else 1):
            bad.append("3a %d write psql calls at %s" % (len(cs), _hh(T)))
    vals = [v for c in calls for rs in sent_rows(c).values() for r in rs for v in r]
    got_h = set(W_HOSTILE + [W_HOSTILE_JSON[0], W_HOSTILE_JSON[1]])
    seen = set(v for v in vals if v in got_h)
    if seen != got_h:
        bad.append("3p hostile values never reached a script as themselves: %s" % sorted(got_h - seen)[:3])
    if not any(r.get("tradingsymbol") in W_HOSTILE for r in res.table.rows["tape_live_cycle"].values()):
        bad.append("3p the fake table did not store a hostile tradingsymbol")
    nn = sql_types()[1]
    if any(v == "" and col not in nn[s["insert"]["table"]] for c in calls for s in c["parsed"]["stmts"] if s.get("insert")
           for r in s["insert"]["rows"] for col, v in zip(s["insert"]["cols"], r)):
        bad.append("3q an empty string written as '' in a nullable column (want NULL; '' only where the column is NOT NULL)")
    if not any(v == "" for c in calls for s in c["parsed"]["stmts"] if s.get("insert") for r in s["insert"]["rows"] for v in r):
        bad.append("3q precondition: no '' in a NOT NULL column in any script (a label's empty reason must reach the table as '')")
    if not any(v is None for c in calls for s in c["parsed"]["stmts"] if s.get("insert") for r in s["insert"]["rows"] for v in r):
        bad.append("3q precondition: no NULL value in any script (the check would be vacuous)")
    if bad:
        return False, "; ".join(bad[:8])
    # 3o: a duplicate conflict key by value in the write set: nothing is sent, the keys are listed, the writer stops
    for kind in ("cycle", "events", "wall", "label", "events_num", "cycle_tok"):
        tag = "3o-num" if kind in ("events_num", "cycle_tok") else "3o-ts"      # a number in two scales / an instant in two texts
        r = w_cli("dup_" + kind, start="15:20", plant=lambda k=kind: plant_dup(k))
        why = need_run(r, "dup %s run" % kind)
        hb, stj = w_json(r, "heartbeat.json"), w_json(r, "state.json")
        dk = os.path.join(live_of(r), "db_dupkeys.csv")
        if why:
            bad.append(tag + " " + why)
        elif w_scripts(r) or hb.get("write", {}).get("state") != "stopped" or hb["write"].get("reason") != "dup_conflict_key" \
                or _latch_of(r.out).get("reason") != "dup_conflict_key" or not os.path.exists(dk) or len(open(dk, encoding="utf-8").read().splitlines()) < 2:
            bad.append("%s %s: %d scripts sent, write %s, db_dupkeys.csv %s (want 0, stopped / dup_conflict_key, keys listed)" % (
                tag, kind, len(w_scripts(r)), hb.get("write"), os.path.exists(dk)))
    nul_bad, nul_branch = _nul_3r(w_cli("nul", start="15:20", plant=plant_nul))
    bad += nul_bad
    # 3s: the literal check: read only, no INSERT, no table; the server's text must equal the expected, and it can fail
    lit = w_literal_check(None)
    bad += lit
    return not bad, ("; ".join(bad[:8]) + " [3r branch: %s]" % nul_branch) if bad else "%d scripts, %d INSERT statements, %d rows at N = %d: BEGIN..COMMIT, lock_timeout, scs on, exact clauses, SET lists, no RETURNING, hostile values and NULLs round trip; 4 duplicate plants stop the writer; 3r branch: %s; literal check is read only and can fail" % (len(calls), n_stmt, n_rows, N, nul_branch)


NUL_3R_BRANCH = {False: "python >= 3.11, NUL stops the writer (stopped / other, no NUL sent)",
                 True: "python < 3.11, csv rejects the NUL first: asserted fail-safe crash (rc 1, state error, no write script)"}


def _nul_3r(r, csv_rejects_nul=None):
    """3r: a NUL in a data row never reaches a script. On Python >= 3.11 csv quotes the NUL, and the writer's own refusal must stop
    it: rc 0, writer stopped / other, no script with a NUL. On Python < 3.11 csv.writer raises ('need to escape, but no escapechar
    set') in dbshape.line before the writer sees the row (box, 3.10.12, 2026-11-22), so the safe outcome is asserted instead: rc 1,
    heartbeat state error, no write script (the write role's start-up check, a non-write call, still runs), no script with a NUL,
    writer state 'none' (operator ruling 3, 2026-11-22). That branch is asserted, not proven able to fail, on an interpreter >= 3.11;
    the box suite is its only real run. -> (findings, branch text)."""
    old_csv = sys.version_info < (3, 11) if csv_rejects_nul is None else csv_rejects_nul
    branch = NUL_3R_BRANCH[old_csv]
    hb = w_json(r, "heartbeat.json")
    hbw = hb.get("write") or {}
    nul_sent = any("\x00" in c["text"] for c in r.fake.wcalls)
    if not old_csv:
        if need_run(r, "nul run") or nul_sent or hbw.get("state") != "stopped" or hbw.get("reason") != "other":
            return ["3r NUL (%s): rc %s, %d scripts, write %s (want 0 scripts with a NUL, stopped / other)" % (
                branch, r.rc, len(w_scripts(r)), hb.get("write"))], branch
        return [], branch
    if r.rc != 1 or hb.get("state") != "error" or w_scripts(r) or nul_sent or hbw.get("state") != "none":
        return ["3r NUL (%s): rc %s, state %s, last_error %r, %d write scripts (%d write-role calls: %s), NUL sent %s, write %s (want rc 1, "
                "error, 0 write scripts, False, writer state 'none')" % (branch, r.rc, hb.get("state"), hb.get("last_error"), len(w_scripts(r)),
                                                                        len(r.fake.wcalls), [c["kind"] for c in r.fake.wcalls], nul_sent, hb.get("write"))], branch
    return [], branch


def w_literal_check(_unused):
    cli = mods()[0]
    ls = rmods()[1]
    out = []
    for corrupt, want_rc0 in ((None, True), (2, False)):
        inner = FakeShell.__new__(FakeShell)
        inner.calls, inner.raised, inner.psql_fail, inner.md5, inner.files, inner.vis, inner.rows = [], 0, None, {}, {}, {}, {}
        fake = FakeWriteShell(inner, FakeTable(DAY), os.path.join(_TMP, "litcheck"), day=DAY)
        fake.lit_corrupt = corrupt
        saved = ls.RUN
        ls.RUN = fake
        try:
            with _env({W_ENV: W_DSN}, drop=_AWS_KEYS), strict_iso():
                rc, log = quiet_exit(cli.main, ["db-literal-check"])
        finally:
            ls.RUN = saved
        if "unrecognized arguments" in log or "invalid choice" in log:
            return ["3s db-literal-check does not exist (%s)" % log.strip().splitlines()[-1][:120]]
        calls = [c for c in fake.wcalls if c["kind"] == "litcheck"]
        if len(calls) != 1 or len(fake.wcalls) != 1:
            return ["3s db-literal-check made %d write-role calls, want exactly 1 literal-check script" % len(fake.wcalls)]
        metas, stmts, tail = sql_split(calls[0]["text"])
        kinds = [s.split()[0].upper() for s in stmts]
        if not stmts[0].upper().startswith("BEGIN READ ONLY") or kinds[-1] != "ROLLBACK" or "COMMIT" in kinds \
                or re.search(r"(?i)\b(INSERT|UPDATE|DELETE|TRUNCATE)\b|tape_live_", strip_literals(calls[0]["text"])) \
                or sum(1 for k in kinds if k == "SELECT") < len(W_HOSTILE):
            out.append("3s the literal check is not BEGIN READ ONLY ... SELECTs ... ROLLBACK without a table (%s)" % kinds[:3])
        if (rc == 0) != want_rc0:
            out.append("3s literal check rc=%s with %s server text (want %s)" % (rc, "a corrupted" if corrupt is not None else "the right", "0" if want_rc0 else "non-zero"))
    return out


W_ERR_RUNS = {"err_to": [{"err": "57014"}, None], "err_lock_to": [{"err": "55P03"}, {"err": "57014"}],
              "err_dead_to": [{"err": "40P01"}, {"err": "timeout"}], "err_conn2": [{"err": "connect"}, {"err": "connect"}],
              "err_rls": [{"err": "42501"}], "err_cl": [{"err": "53300"}], "err_cl_text": [{"err": "conn_text"}],
              "err_idle": [{"err": "25P03"}], "err_other": [{"err": "XX000"}],
              "err_pooler": [{"err": "pooler_text"}, None]}
# by hand: (grid minute, the one werr_ column that reads 1 there); the reason the run ends with (None = still writing)
W_ERR_EXPECT = {"err_to": ([(920, "werr_statement_timeout")], None),
                "err_lock_to": ([(920, "werr_lock"), (925, "werr_statement_timeout")], "second_skip"),
                "err_dead_to": ([(920, "werr_lock"), (925, "werr_statement_timeout")], "second_skip"),
                "err_conn2": ([(920, "werr_connect"), (925, "werr_connect")], "second_skip"),
                "err_rls": ([(920, "werr_rls_refused")], "rls_refused"),
                "err_cl": ([(920, "werr_connection_limit")], "connection_limit"),
                "err_cl_text": ([(920, "werr_connection_limit")], "connection_limit"),
                "err_idle": ([(920, "werr_idle_tx_timeout")], "idle_tx_timeout"),
                "err_other": ([(920, "werr_other")], "other"),
                "err_pooler": ([(920, "werr_connect")], None)}
W_WERR = ("werr_statement_timeout", "werr_lock", "werr_idle_tx_timeout", "werr_rls_refused", "werr_connection_limit",
          "werr_connect", "werr_other")


def err_run(name):
    return w_cli(name, start="15:20", plants=plants_of(*W_ERR_RUNS[name]))


def _f(row, col):
    try:
        return float(row[col])
    except (KeyError, ValueError):
        return float("nan")


def g_2b_metrics():
    """Plan guard 4. Red first: no write columns (the write flags are unknown)."""
    bad = _w2b_selftest()
    if bad:
        return False, "; ".join(bad[:6])
    res = w_canon()
    why = need_run(res, "canon run")
    if why:
        return False, why
    rows = dict((r["T"], r) for r in w_metrics(res))
    calls = [c for c in w_scripts(res) if 560 <= c["T"] <= 930]
    n_skipped = 0
    for c in calls:
        row = rows.get(_hh(c["T"]))
        if row is None or any(col not in row for col in W_METRIC_COLS):
            bad.append("4 no metrics row with the write columns at %s" % _hh(c["T"]))
            break
        by = ins_by_table(c)
        for t in W_ORDER:
            sh = t.replace("tape_live_", "")
            stm = by.get(t, [])
            d = [w_dur(t, k, c["ord"]) for k in range(len(stm))]
            want = {"up_stmts_" + sh: len(stm), "up_rows_" + sh: sum(len(i["rows"]) for i in stm),
                    "up_s_" + sh: sum(d) / 1000.0, "up_max_stmt_s_" + sh: (max(d) if d else 0.0) / 1000.0}
            for col, w in want.items():
                if abs(_f(row, col) - w) > 0.0006:
                    bad.append("4a-d %s %s = %s, by hand %s" % (_hh(c["T"]), col, row.get(col), w))
        sent_l = sum(len(i["rows"]) for i in by.get("tape_live_label", []))
        ins_l = sum(x["n"] for x in c["tags"] if x.get("table") == "tape_live_label")
        if int(_f(row, "up_label_skipped")) != sent_l - ins_l:
            bad.append("4e %s up_label_skipped = %s, rows sent - rows inserted = %d" % (_hh(c["T"]), row.get("up_label_skipped"), sent_l - ins_l))
        n_skipped += sent_l - ins_l
        if row["write_state"] != "sent" or not _f(row, "up_proc_s") > 0:
            bad.append("4f %s write_state %r, up_proc_s %s (want sent, > 0)" % (_hh(c["T"]), row["write_state"], row.get("up_proc_s")))
        if any(int(_f(row, w)) for w in W_WERR):
            bad.append("4 %s: an error counter on a clean cycle" % _hh(c["T"]))
    if n_skipped != 1:
        bad.append("4e precondition: %d label rows skipped by DO NOTHING in the canon run, by hand 1 (the preloaded duplicate)" % n_skipped)
    if not any(abs(_f(rows[_hh(c["T"])], "up_max_stmt_s_cycle") - 5.3) < 0.0006 for c in calls if c["ord"] == 3):
        bad.append("4b the planted 5300 ms statement (Time: ... (00:05.300)) was not read as 5.300 s")
    if bad:
        return False, "; ".join(bad[:8])
    sh = {"4g": "err_to", "4h": "err_lock_to", "4i": "err_dead_to", "4j": "err_idle", "4k": "err_rls", "4l": "err_cl",
          "4l'": "err_cl_text", "4l2": "err_pooler", "4m": "err_conn2", "4n": "err_other", "4o": "err_dead_to"}
    for tag, name in sh.items():
        r = err_run(name)
        why = need_run(r, "%s run %s" % (tag, name))
        if why:
            bad.append(why)
            continue
        mrows = dict((x["T"], x) for x in w_metrics(r))
        for minute, col in W_ERR_EXPECT[name][0]:
            x = mrows.get(_hh(minute), {})
            got = dict((w, x.get(w)) for w in W_WERR)
            if got != dict((w, "1" if w == col else "0") for w in W_WERR):
                bad.append("%s %s at %s: error counters %s, by hand exactly %s = 1" % (tag, name, _hh(minute), got, col))
    return not bad, "; ".join(bad[:8]) or "%d cycles: per-table seconds, longest statement (5.300 s from a 'Time: ... (00:05.300)' line), rows, statements and labels skipped equal the hand values; the categories 57014 / 55P03 / 40P01 / 25P03 / 42501 / 53300 (and its text form) / connect / XX000 / rc 124 each land in their column" % len(calls)


LATCH_NAME, LATCH_REDATE = "WRITE_LATCH.json", "WRITE_LATCH.redate.json"
LATCH_KEYS = {"reason", "category", "at", "day", "set_utc"}
LATCH_HAND = {"reason": "rls_refused", "category": "rls_refused", "at": 920, "day": "2026-11-05", "set_utc": "2026-11-05T10:15:00Z"}
CLEAR_STALE_S = 600


def _latch_of(out, redate=False):
    try:
        with open(os.path.join(out, LATCH_REDATE if redate else LATCH_NAME), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _plant_latch(out, redate=False, **kw):
    """A latch written by hand in the contract's form (not by the writer): the carried-from-an-earlier-day case."""
    os.makedirs(out, exist_ok=True)
    pth = os.path.join(out, LATCH_REDATE if redate else LATCH_NAME)
    with open(pth, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(dict(LATCH_HAND, **kw), sort_keys=True) + "\n")
    return pth


def _bytes_of(pth):
    """The file's bytes, or None when it is gone (a guard asserts on a vanished latch instead of crashing on it)."""
    try:
        with open(pth, "rb") as fh:
            return fh.read()
    except OSError:
        return None


class _OsShim:
    """Stands in for `os` inside services.tape_live.dbwrite only: every attribute is the real one except the one planted to fail."""

    def __init__(self, real, fail, err):
        self._real, self._fail, self._err = real, fail, err

    def __getattr__(self, name):
        if name == self._fail:
            def boom(*_a, **_k):
                raise OSError(self._err, os.strerror(self._err))
            return boom
        return getattr(self._real, name)


@contextlib.contextmanager
def _latch_write_fails(fail, err):
    """L-j plant: the latch's own write fails (fail = 'fsync' with ENOSPC: disk full; 'replace' with EACCES: permission)."""
    dbw = _dbw()
    real = dbw.os
    dbw.os = _OsShim(real, fail, err)
    try:
        yield
    finally:
        dbw.os = real


def _copy_latch(data, out):
    """Byte copy of a latch the writer itself produced (None if it produced none: nothing is planted, and L-c then fails)."""
    if data is not None:
        with open(os.path.join(out, LATCH_NAME), "wb") as fh:
            fh.write(data)


def _plant_hb(out, day, state, pid, age_s):
    dd = os.path.join(out, day)
    os.makedirs(dd, exist_ok=True)
    when = datetime.now(timezone.utc) - timedelta(seconds=age_s)
    with open(os.path.join(dd, "heartbeat.json"), "w", encoding="utf-8") as fh:
        json.dump({"state": state, "pid": pid, "day": day, "updated_utc": when.strftime("%Y-%m-%dT%H:%M:%SZ")}, fh)
    with open(os.path.join(dd, "state.json"), "w", encoding="utf-8") as fh:
        json.dump({"write_skips": 1}, fh)


def _dead_pid():
    pr = subprocess.Popen([sys.executable, "-c", "pass"])
    pr.wait()
    return pr.pid


def _lg_corrupt_latch():
    """L-g: a latch that cannot be parsed stops writes (fail closed) and can still be cleared. The corrupt-latch run is in-process,
    so its heartbeat carries THIS process's pid, which write-clear rightly counts as alive where a zero signal exists (posix): a
    dead runner's stale 'done' heartbeat is planted in its place before write-clear, so the clear is decided by the latch alone
    (operator ruling 2, 2026-11-22). Findings, [] if none."""
    bad = []
    d = _fresh_dir("corrupt")
    with open(os.path.join(d, LATCH_NAME), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("{not json\n")
    r = w_cli(None, out=d, start="15:20")
    hbw = w_json(r, "heartbeat.json").get("write", {})
    if r.fake.wcalls or hbw.get("state") != "stopped" or hbw.get("reason") != "latch_unreadable":
        bad.append("L-g a corrupt latch: %d write-role calls, write %s (want none, stopped / latch_unreadable)" % (len(r.fake.wcalls), hbw))
    _plant_hb(d, DAY, "done", _dead_pid(), 7200)
    rc, log = _wc(d)
    if rc != 0 or os.path.exists(os.path.join(d, LATCH_NAME)) or not _latch_files(d, "WRITE_LATCH.cleared."):
        bad.append("L-g write-clear on a corrupt latch, no runner alive: rc=%s %r (want cleared)" % (rc, log[-160:]))
    return bad


def _wc(out, *extra, note="t"):
    return quiet_exit(mods()[0].main, ["write-clear", "--out", out, "--note", note] + list(extra))


def _fresh_dir(name):
    d = os.path.join(_TMP, "lt_" + name)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    return d


def _latch_files(out, prefix):
    return sorted(n for n in os.listdir(out) if n.startswith(prefix))


def _stop_of(res):
    return w_json(res, "heartbeat.json").get("write", {}), _latch_of(res.out), os.path.exists(os.path.join(res.root, "WRITE_STOPPED"))


def _same_outputs(a, b):
    """The files a run leaves besides the write-only ones: live/ (minus db_*.csv) and arrival_log.csv, byte for byte."""
    def files(r):
        out = {}
        for rel in _files(r.root):
            if rel == "arrival_log.csv" or (rel.startswith("live/") and not os.path.basename(rel).startswith("db_")):
                out[rel] = sha(os.path.join(r.root, rel))
        return out
    fa, fb = files(a), files(b)
    return [k for k in sorted(set(fa) | set(fb)) if fa.get(k) != fb.get(k)]


def _hand_7a(dbw):
    """Item 7a (ruling R9-B) on hand-fed numbers: no clock, no run, no planted cost. The rule: on a cycle whose epoch-log entry is a
    drop bump, with the median of wall_s over the cycles from the 09:20 grid point on (the current one included) and at least 6 such
    cycles, stop only if wall_s - median > median AND wall_s - median > 30 s. Every expected value below is by hand (median of the
    window, current cycle included); cycles are 5 minutes apart, the last is the bump; start 560 = 09:20 unless 530 = 08:50.
      a      6 x 0.05 (08:50-09:15), 5 x 40.0, bump 75.0: window 6, median 40.0, excess 35.0, not > 40.0 -> no stop
      a2     the real 2026-11-05 walls 08:50-09:45: window 3.67 5.02 6.60 8.24 8.60 9.03, median 7.42, excess 1.61 -> no stop
      b      6 x 1.0, bump 30.0: median 1.0, excess 29.0, not > 30 -> no stop
      b2     6 x 1.0, bump 31.0: median 1.0, excess 30.0, not > 30 (strict) -> no stop
      c      6 x 1.0, bump 32.0: median 1.0, excess 31.0 > 1.0 and > 30 -> stop
      d      6 x 40.0, bump 75.0: median 40.0, excess 35.0 > 30 but not > 40.0 -> no stop
      e      6 x 0.05 (08:50-09:15), 4 x 1.0, bump 40.0 at 09:40: window 5 < 6 -> no stop
      steady 6 x 1.0, bump 1.9 -> no stop; non_drop / rebuild: 6 x 1.0 then 32.0 with no bump / a rebuild bump -> no stop;
      sixth  5 x 1.0, bump 32.0: window 6, median 1.0, excess 31.0 -> stop; early 3 x 1.0, bump 32.0: window 4 -> no stop.
    -> findings."""
    def run(case, walls, last_log, start=560):
        w = dbw.DbWriter(None, DAY, 7, os.path.join(_TMP, "hand7a_" + case))
        for i, s in enumerate(walls):
            T = start + 5 * i
            w.end_cycle(T, s, 20.0, [dict(e, at=T) for e in last_log] if i == len(walls) - 1 else [])
        return w.stopped
    drop, rebuild = [{"trigger": "drop"}], [{"trigger": "late_segment"}]
    stop = "item_7a_drop_bump"
    real_1105 = [0.05, 0.01, 0.07, 0.07, 0.04, 0.04, 3.67, 5.02, 6.60, 8.24, 8.60, 9.03]
    cases = (("a", [0.05] * 6 + [40.0] * 5 + [75.0], drop, None, 530), ("a2", real_1105, drop, None, 530),
             ("b", [1.0] * 6 + [30.0], drop, None, 560), ("b2", [1.0] * 6 + [31.0], drop, None, 560),
             ("c", [1.0] * 6 + [32.0], drop, stop, 560), ("d", [40.0] * 6 + [75.0], drop, None, 560),
             ("e", [0.05] * 6 + [1.0] * 4 + [40.0], drop, None, 530), ("steady", [1.0] * 6 + [1.9], drop, None, 560),
             ("non_drop", [1.0] * 6 + [32.0], [], None, 560), ("rebuild", [1.0] * 6 + [32.0], rebuild, None, 560),
             ("sixth", [1.0] * 5 + [32.0], drop, stop, 560), ("early", [1.0] * 3 + [32.0], drop, None, 560))
    bad = []
    for case, walls, log, want, start in cases:
        got = (run(case, walls, log, start) or {}).get("reason")
        if got != want:
            bad.append("5i0 hand-fed 7a, %s: %d cycles ending %.2f s -> %r, by hand %r" % (case, len(walls), walls[-1], got, want))
    return bad


def g_2b_stop():
    """Plan guard 5. Red first: no DbWriter (the write flags are unknown)."""
    dbw = _dbw()
    if dbw is None:
        return False, "ImportError: services.tape_live.dbwrite does not exist"
    bad = _hand_7a(dbw)
    if bad:
        return False, "; ".join(bad[:6])
    off = w_off("off_1520")
    for name in ("err_rls", "err_cl", "err_cl_text", "err_idle", "err_other", "err_conn2", "err_to", "err_lock_to", "err_dead_to", "err_pooler"):
        r = err_run(name)
        why = need_run(r, "%s" % name)
        if why:
            return False, why
        hb, ws, sent = _stop_of(r)
        want_cols, reason = W_ERR_EXPECT[name]
        n_sc = len(w_scripts(r))
        if reason is None:
            if hb.get("state") == "stopped" or ws:
                bad.append("5p %s: stopped after one 57014 (want skipped, then writing)" % name)
            if sum(1 for c in w_scripts(r) if c["T"] == 920) != 1:
                bad.append("5p %s: the 15:20 cycle's write was retried in the same cycle" % name)
            s2 = [c for c in w_scripts(r) if c["T"] == 925]
            want = apply_db(_deltas_of(r), "1525", u_only=True)
            for t in DELTA_TABLES:
                got = sorted(sent_rows(s2[0]).get(t, [])) if s2 else None
                exp = sorted(tuple("" if v is None else v for v in row) for row in want[t].values())
                if got != exp:
                    bad.append("5q %s: the 15:25 write did not carry every row the skipped 15:20 write held (%s)" % (name, t))
                    break
            continue
        if hb.get("state") != "stopped" or hb.get("reason") != reason or ws.get("reason") != reason or not sent:
            bad.append("5a-e %s: heartbeat %s, latch file %s, sentinel %s (want stopped / %s)" % (name, hb, ws, sent, reason))
        if ws.get("day") != DAY or os.path.exists(os.path.join(r.root, LATCH_NAME)) or "write_stop" in w_json(r, "state.json"):
            bad.append("5a-e %s: the latch is not the root file %s with day %s (day %r; in the day directory %s, in state.json %s)" % (
                name, LATCH_NAME, DAY, ws.get("day"), os.path.exists(os.path.join(r.root, LATCH_NAME)), "write_stop" in w_json(r, "state.json")))
        if n_sc != len(W_ERR_RUNS[name]):
            bad.append("5a-e %s: %d write calls, by hand %d (no write after the stop, none retried)" % (name, n_sc, len(W_ERR_RUNS[name])))
        if r.rc != 0 or w_json(r, "heartbeat.json").get("state") != "done" or _same_outputs(r, off):
            bad.append("5k %s: rc %s, state %s, files that differ from the flag-off run: %s" % (
                name, r.rc, w_json(r, "heartbeat.json").get("state"), _same_outputs(r, off)[:3]))
        if not os.path.exists(os.path.join(r.root, "live_metrics.csv")):
            bad.append("5k %s: no live_metrics.csv: the run ended at the stop instead of cycling on to the final" % name)
            continue
        m = w_metrics(r)
        if [x["write_state"] for x in m if x["T"] == _hh(945)] not in (["stopped"], []):
            bad.append("5 %s: write_state after the stop is not 'stopped'" % name)
    if bad:
        return False, "; ".join(bad[:8])
    # 5f overrun: lag + wall_s over 300 s stops the writer after that cycle's write
    r = w_cli("overrun", start="15:20", plants=plants_of(None, {"slow": 400}))
    hb, ws, sent = _stop_of(r)
    if need_run(r, "overrun") or len(w_scripts(r)) != 2 or hb.get("reason") != "overrun" or hb.get("state") != "stopped":
        bad.append("5f overrun: %d scripts, write %s (want 2 scripts, stopped / overrun)" % (len(w_scripts(r)), hb))
    # 5g: a grid point lost across a restart latches before that cycle's write
    ph = w_phases("gap", [{"start": "15:20", "plants": plants_of(None, {"kill": True})}, {"start": "15:37"}])
    hb, ws, sent = _stop_of(ph[1])
    if ph[0].rc != 0 or ph[1].rc != 0 or w_scripts(ph[1]) or hb.get("reason") != "missed_grid_point" or not sent or len(w_scripts(ph[0])) != 2:
        bad.append("5g restart gap: rc %s/%s, %d scripts after the restart, write %s (want 0, stopped / missed_grid_point)" % (
            ph[0].rc, ph[1].rc, len(w_scripts(ph[1])), hb))
    # 5h: the grid points before a fresh start's first cycle do not latch (2026-11-12: started 08:58, 83 rows, missed 0)
    r = w_cli("fresh_1002", start="10:02")
    why = need_run(r, "5h fresh start")
    if why:
        bad.append(why)
    else:
        m0 = [x for x in w_metrics(r) if x["T"] == "10:00"]
        hb, ws, sent = _stop_of(r)
        if not m0 or m0[0]["missed_grid_points"] != "8" or len(w_json(r, "state.json").get("missed", [])) != 8 or not w_scripts(r) or hb.get("state") == "stopped" or sent:
            bad.append("5h fresh start 10:02: missed_grid_points %s (by hand 8: 09:20..09:55), %d scripts, write %s" % (
                m0[0]["missed_grid_points"] if m0 else None, len(w_scripts(r)), hb))
    # 5i / 5j: item 7a (R9-B) on a drop bump cycle. By hand: the window median from 09:20 is about 0.3 s on this fixture, so the planted
    # 60 s at 14:35 exceeds it by about 60 s, above the median and above 30 s: stop. 5j starts at 14:20: 4 window cycles at 14:35, no stop.
    slow = {("T", 600): {"slow": 60}, ("T", 650): {"slow": 60}, ("T", 875): {"slow": 60}}
    r = w_cli("slow7a", fix=epoch_raw(), arrival=gen_live.EPOCH_ARRIVAL, start="08:50", plants=slow)
    why = need_run(r, "5i slow run")
    hb, ws, sent = _stop_of(r)
    ts_ = sorted(c["T"] for c in w_scripts(r))
    if why:
        bad.append(why)
    elif not ts_ or ts_[-1] != 875 or not any(650 < t < 875 for t in ts_) or hb.get("reason") != "item_7a_drop_bump":
        bad.append("5i 7a: last write at %s, write %s (want the write at 14:35, the drop bump, then stopped / item_7a_drop_bump; the slow cycles at 10:00 and 10:50 are not drops)" % (
            _hh(ts_[-1]) if ts_ else None, hb))
    r = w_cli("slow7a_early", fix=epoch_raw(), arrival=gen_live.EPOCH_ARRIVAL, start="14:20", plants={("T", 875): {"slow": 60}})
    why = need_run(r, "5j early run")
    hb, ws, sent = _stop_of(r)
    if why:
        bad.append(why)
    elif hb.get("state") == "stopped" or not any(c["T"] > 875 for c in w_scripts(r)):
        bad.append("5j 7a before 6 cycles: write %s, last write %s (want writing on)" % (hb, max([c["T"] for c in w_scripts(r)] or [0])))
    # 5l / 5o: the latch is the root file; a restart writes nothing, with the day sentinel and without it
    stop1 = {"start": "15:20", "plants": plants_of({"err": "42501", "kill": True})}
    ph = w_phases("stop_restart", [stop1, {"start": "15:28"}])
    hb, ws, sent = _stop_of(ph[1])
    if w_scripts(ph[1]) or hb.get("state") != "stopped" or not sent or ph[0].rc != 0 or ws.get("reason") != "rls_refused":
        bad.append("5l restart after a stop: %d scripts, write %s, latch %s, sentinel %s (want none, stopped, root latch rls_refused, sentinel kept)" % (
            len(w_scripts(ph[1])), hb, ws, sent))
    ph = w_phases("stop_restart_nosent", [stop1, {"start": "15:28", "pre": lambda d: os.remove(os.path.join(d, "WRITE_STOPPED"))}])
    hb, ws, sent = _stop_of(ph[1])
    if w_scripts(ph[1]) or hb.get("state") != "stopped" or ws.get("reason") != "rls_refused":
        bad.append("5o restart with the sentinel deleted wrote %d scripts, write %s, latch %s (the latch is the root file)" % (len(w_scripts(ph[1])), hb, ws))
    # 5s: one skip, a restart, a second skip: the count survives the restart and latches
    ph = w_phases("skip_restart_skip", [{"start": "15:20", "plants": plants_of({"err": "57014", "kill": True})},
                                        {"start": "15:28", "plants": plants_of({"err": "55P03"})}])
    hb, ws, sent = _stop_of(ph[1])
    if len(w_scripts(ph[1])) != 1 or hb.get("reason") != "second_skip" or hb.get("state") != "stopped":
        bad.append("5s skip, restart, skip: %d scripts, write %s (want 1, stopped / second_skip)" % (len(w_scripts(ph[1])), hb))
    # 5t / 5u: write-clear on the root latch: refused while a runner of the latch day or later is alive, clears when it is not
    cli = mods()[0]
    base = err_run("err_rls")
    c1, c2 = os.path.join(_TMP, "wc_run"), os.path.join(_TMP, "wc_stopped")
    for dst in (c1, c2):
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(base.out, dst)
        if not os.path.exists(os.path.join(dst, LATCH_NAME)):
            bad.append("5t/5u the stop run left no %s at the out root" % LATCH_NAME)
    dead = _dead_pid()
    _plant_hb(c1, DAY, "waiting", os.getpid(), 5)
    _plant_hb(c2, DAY, "done", dead, 7200)
    rc1, log1 = _wc(c1)
    rc2, log2 = _wc(c2, note="clear-note-9")
    if "invalid choice" in log1 or "unrecognized arguments" in log1:
        bad.append("5t/5u write-clear does not exist")
    else:
        if rc1 == 0 or not _latch_of(c1) or not os.path.exists(os.path.join(base.out, DAY, "WRITE_STOPPED")):
            bad.append("5t write-clear on a running runner: rc=%s, latch kept %s (want refused, latch kept)" % (rc1, bool(_latch_of(c1))))
        cleared = _latch_files(c2, "WRITE_LATCH.cleared.")
        if rc2 != 0 or _latch_of(c2) or not cleared or os.path.exists(os.path.join(c2, DAY, "WRITE_STOPPED")) \
                or "clear-note-9" not in open(os.path.join(c2, DAY, "runner.log"), encoding="utf-8").read() \
                or json.load(open(os.path.join(c2, DAY, "state.json"), encoding="utf-8")).get("write_skips") != 0:
            bad.append("5u write-clear on a stopped day: rc=%s, latch %s, latch renamed %s, note logged, write_skips reset (want cleared)" % (rc2, _latch_of(c2), bool(cleared)))
    return not bad, "; ".join(bad[:8]) or "immediate stops (42501, 53300 both forms, 25P03, other), connect / lock / timeouts skip once and stop on the second, overrun, restart gap, fresh start 10:02 (8 missed points) keeps writing, 7a (R9-B) only on a drop bump, 6 cycles from 09:20, excess above the median and 30 s, latch survives restart with and without the sentinel, write-clear"


def g_2b_latch():
    """R8-I: the stop latch is the root file <out>/WRITE_LATCH.json and carries across days. Red first: the latch is in state.json."""
    bad = []
    off = w_off("off_1520")
    # L-a: a stop writes the root latch (and not a day-directory copy)
    r = err_run("err_rls")
    why = need_run(r, "L-a stop run")
    if why:
        return False, why
    lt, hbw = _latch_of(r.out), w_json(r, "heartbeat.json").get("write", {})
    try:
        with open(os.path.join(r.out, LATCH_NAME), "rb") as fh:
            real_latch = fh.read()          # the bytes L-a's real stop produced: L-c plants exactly these
    except OSError:
        real_latch = None
    if set(lt) != LATCH_KEYS or lt.get("reason") != "rls_refused" or lt.get("day") != DAY or lt.get("at") != 920 \
            or not re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$", str(lt.get("set_utc", ""))):
        bad.append("L-a stop on %s: latch %s (want keys %s, rls_refused, day %s, at 920)" % (DAY, lt, sorted(LATCH_KEYS), DAY))
    if os.path.exists(os.path.join(r.root, LATCH_NAME)) or hbw.get("latch_day") != DAY or hbw.get("carried") is not False:
        bad.append("L-a the latch is in the day directory %s, heartbeat latch_day %r carried %r (want root only, %s, False)" % (
            os.path.exists(os.path.join(r.root, LATCH_NAME)), hbw.get("latch_day"), hbw.get("carried"), DAY))
    # L-b: a run on a later day than the latch's writes nothing, makes no connection, and keeps producing files
    d = _fresh_dir("carry")
    pth = _plant_latch(d)
    before = _bytes_of(pth)
    r = w_cli(None, out=d, start="15:20")
    hbw = w_json(r, "heartbeat.json").get("write", {})
    if r.rc != 0 or r.fake.wcalls or hbw.get("state") != "stopped" or hbw.get("reason") != "rls_refused" \
            or hbw.get("latch_day") != "2026-11-05" or hbw.get("carried") is not True:
        bad.append("L-b carried latch: rc %s, %d write-role calls, write %s (want rc 0, none, stopped / rls_refused, latch_day 2026-11-05, carried)" % (
            r.rc, len(r.fake.wcalls), hbw))
    if _same_outputs(r, off) or not os.path.exists(os.path.join(r.root, "WRITE_STOPPED")) or _bytes_of(pth) != before \
            or os.path.exists(os.path.join(r.root, LATCH_NAME)):
        bad.append("L-b carried latch: files that differ from the flag-off run %s, sentinel %s, latch unchanged %s, latch copied into the day %s" % (
            _same_outputs(r, off)[:3], os.path.exists(os.path.join(r.root, "WRITE_STOPPED")), _bytes_of(pth) == before,
            os.path.exists(os.path.join(r.root, LATCH_NAME))))
    if os.path.exists(os.path.join(r.root, "live_metrics.csv")) and any(x["write_state"] != "stopped" for x in w_metrics(r)):
        bad.append("L-b write_state is not 'stopped' on every row of a carried-latch day")
    # L-c: a restart in the middle of a day that began unlatched, then a latch appears at the root: nothing is written
    ph = w_phases("latch_mid", [{"start": "15:20", "plants": plants_of({"kill": True})},
                                {"start": "15:28", "pre": lambda dd: _copy_latch(real_latch, os.path.dirname(dd))}])
    hbw = w_json(ph[1], "heartbeat.json").get("write", {})
    if len(w_scripts(ph[0])) != 1 or w_scripts(ph[1]) or hbw.get("state") != "stopped" or ph[1].fake.wcalls:
        bad.append("L-c restart under a root latch: %d scripts before, %d after, %d write-role calls, write %s (want 1, 0, 0, stopped)" % (
            len(w_scripts(ph[0])), len(w_scripts(ph[1])), len(ph[1].fake.wcalls), hbw))
    # L-d / L-h / L-i: what write-clear counts as alive: the latch day and later; fresh heartbeat or live pid; stale + dead pid is not alive
    dead = _dead_pid()
    d = _fresh_dir("clear_later")
    pth = _plant_latch(d, day=DAY)
    before = _bytes_of(pth)
    _plant_hb(d, DAY, "done", dead, 7200)
    _plant_hb(d, "2026-11-09", "cycling", dead, 30)
    rc, log = _wc(d)
    if rc != 2 or _bytes_of(pth) != before or "2026-11-09" not in log or str(dead) not in log or "600" not in log \
            or not re.search(r"\b\d+(\.\d+)? ?s\b", log):
        bad.append("L-d a later day with a fresh cycling heartbeat: rc=%s, latch kept %s, message %r (want rc 2, latch kept, the day, the pid, the age in s and 600)" % (
            rc, _bytes_of(pth) == before, log[-200:]))
    d = _fresh_dir("clear_stale")
    _plant_latch(d, day=DAY)
    _plant_hb(d, DAY, "cycling", dead, CLEAR_STALE_S * 6)
    rc, log = _wc(d)
    if rc != 0 or _latch_of(d) or not _latch_files(d, "WRITE_LATCH.cleared."):
        bad.append("L-h a stale cycling heartbeat with a dead pid: rc=%s, latch %s (want cleared)" % (rc, _latch_of(d)))
    d = _fresh_dir("clear_fresh")
    _plant_latch(d, day=DAY)
    _plant_hb(d, DAY, "cycling", dead, 30)
    rc, log = _wc(d)
    if rc != 2 or not _latch_of(d):
        bad.append("L-h a fresh cycling heartbeat with a dead pid: rc=%s, latch kept %s (want refused: age decides when no pid is alive)" % (rc, bool(_latch_of(d))))
    d = _fresh_dir("clear_earlier")
    _plant_latch(d, day=DAY)
    _plant_hb(d, DAY, "done", dead, 7200)
    _plant_hb(d, "2026-11-05", "cycling", dead, 30)
    rc, log = _wc(d)
    if rc != 0 or _latch_of(d):
        bad.append("L-i a fresh cycling heartbeat on a day before the latch day: rc=%s, latch %s (want cleared: earlier days are not scanned)" % (rc, _latch_of(d)))
    # L-e: nothing to clear; L-f: after a clear the next run writes
    d = _fresh_dir("clear_none")
    rc, log = _wc(d)
    if rc != 0 or "nothing to clear" not in log:
        bad.append("L-e write-clear with no latch: rc=%s, %r (want rc 0, 'nothing to clear')" % (rc, log[-80:]))
    d = _fresh_dir("clear_then_run")
    _plant_latch(d)
    rc, log = _wc(d)
    r = w_cli(None, out=d, start="15:20")
    if rc != 0 or need_run(r, "L-f run after a clear") or not w_scripts(r) or w_json(r, "heartbeat.json").get("write", {}).get("state") == "stopped" or _latch_of(d):
        bad.append("L-f after write-clear: rc=%s, %d scripts, write %s, latch %s (want writing, no latch)" % (
            rc, len(w_scripts(r)), w_json(r, "heartbeat.json").get("write"), _latch_of(d)))
    bad += _lg_corrupt_latch()
    # L-j: the latch cannot be written (disk full, permission): the writer stays stopped in memory, the sentinel is written, the heartbeat says
    # latch_write_failed, the runner does not exit, and no further write-role call is made
    for tag, fail, err in (("disk full (fsync ENOSPC)", "fsync", errno.ENOSPC), ("permission (rename EACCES)", "replace", errno.EACCES)):
        r = w_cli("latch_fail_" + fail, start="15:20", plants=plants_of({"err": "42501"}), plant=lambda f=fail, e=err: _latch_write_fails(f, e))
        hbj = w_json(r, "heartbeat.json")
        hbw = hbj.get("write", {})
        n_sent = len(w_scripts(r))
        if r.rc != 0 or hbj.get("state") != "done":
            bad.append("L-j %s: the runner did not finish: rc=%s, state %r (want rc 0, done: a failed latch write must not end the run)" % (tag, r.rc, hbj.get("state")))
        if hbw.get("state") != "stopped" or hbw.get("reason") != "latch_write_failed":
            bad.append("L-j %s: heartbeat write %s (want stopped / latch_write_failed)" % (tag, hbw))
        if not os.path.exists(os.path.join(r.root, "WRITE_STOPPED")):
            bad.append("L-j %s: no day sentinel after a stop whose latch could not be written" % tag)
        if n_sent != 1:
            bad.append("L-j %s: %d write scripts (want 1: the stopping cycle's, then none)" % (tag, n_sent))
        if os.path.exists(os.path.join(r.root, "live_metrics.csv")):
            if any(x["write_state"] != "stopped" for x in w_metrics(r) if x["T"] > _hh(920)):
                bad.append("L-j %s: write_state is not 'stopped' after the stop" % tag)
        elif r.rc == 0:
            bad.append("L-j %s: no live_metrics.csv" % tag)
        if r.rc == 0 and _same_outputs(r, off):
            bad.append("L-j %s: files that differ from the flag-off run: %s" % (tag, _same_outputs(r, off)[:3]))
    return not bad, "; ".join(bad[:24]) or "the stop latch is the root file with day / at / reason; a later day makes no write-role call, keeps producing files and says carried; a mid-day restart under a latch writes nothing; write-clear counts a later day with a fresh heartbeat (and not an earlier day, nor a stale one with a dead pid) and prints day, pid, age and the 600 s bound; nothing to clear is rc 0; the next run after a clear writes; a corrupt latch fails closed and can be cleared; a latch that cannot be written (disk full, permission) leaves the writer stopped with reason latch_write_failed, the sentinel written and the run finishing"


def _deltas_of(res):
    return _db_deltas_dir(live_of(res))


def _db_deltas_dir(ld):
    by = {}
    for n in os.listdir(os.path.join(ld, "cycles")):
        m = re.match(r"^(\d{4}|final)_(cycle|events|wall)\.db\.csv$", n)
        if m:
            t = [k for k, v in DB_PART.items() if v == m.group(2)][0]
            by.setdefault(m.group(1), {})[t] = _db_read(os.path.join(ld, "cycles", n))
    names = sorted(k for k in by if k != "final") + (["final"] if "final" in by else [])
    return [(k, None if k == "final" else int(k[:2]) * 60 + int(k[2:]), by[k]) for k in names]


def _redate_variant(name, **kw):
    base = dict(start="15:20", check=True, flags=["--test-redate-today"], env={REDATE_ENV: DAY}, now_date="2026-11-14")
    base.update(kw)
    return w_cli(name, **base)


def _template_text(rel):
    p = os.path.join(ROOT, rel)
    return open(p, encoding="utf-8").read() if os.path.isfile(p) else None


def g_2b_startup():
    """Plan guard 6. Red first: no start-up check (the write flags are unknown)."""
    bad = []
    ok = w_cli("su_pass", check=True)
    if ok.rc != 0:
        return False, need_run(ok, "6 pass variant") or "6 pass variant refused"
    mod = lambda **kw: dict(w_default_check(), **kw)

    def priv(t, p, v):
        c = w_default_check()
        c["priv"][t][p] = v
        return c
    ro_dsn = TEST_DSN.replace("merdian_ro:", W_USER + ":")
    variants = [("6a", dict(chk=mod(role="someone_else"))), ("6b", dict(ro_dsn=ro_dsn)), ("6c", dict(chk=mod(super="t"))),
                ("6d", dict(chk=mod(bypassrls="t"))), ("6e", dict(chk=priv("tape_live_label", "DELETE", "t"))),
                ("6f", dict(chk=priv("tape_live_events", "TRUNCATE", "t"))), ("6g", dict(chk=priv("tape_live_wall", "INSERT", "f"))),
                ("6h", dict(chk=priv("tape_live_events", "UPDATE", "f"))), ("6i", dict(chk=mod(ist_date="2026-11-07"))),
                ("6j", dict(now_date="2026-11-07", server_date=DAY)), ("6k", dict(chk=mod(scs="off")))]
    for tag, kw in variants:
        r = w_cli("su_" + tag, check=True, **kw)
        if r.rc != 2 or "unrecognized arguments" in r.log or any(c["kind"] == "write" for c in r.fake.wcalls) \
                or len(r.fake.wcalls) > 1 or (tag != "6j" and len(r.fake.wcalls) != 1) \
                or any(x in r.log for x in (W_PW, W_DSN)):
            bad.append("%s: rc=%s, %d write-role calls (%s), argparse %s (want rc 2 after exactly one check call, no INSERT, no credential)" % (
                tag, r.rc, len(r.fake.wcalls), [c["kind"] for c in r.fake.wcalls], "unrecognized arguments" in r.log))
    return not bad, "; ".join(bad[:8]) or "pass variant rc 0; 11 refusals (role, RO user, super, BYPASSRLS, DELETE, TRUNCATE, INSERT, UPDATE, server date, local date, scs) rc 2 after one check call, no INSERT"


def g_2b_redate():
    """Plan guard 7. Red first: the flag is unknown."""
    bad = []
    okr = _redate_variant("rd_ok")
    if okr.rc != 0:
        return False, need_run(okr, "7 all conditions met") or "7 refused with all conditions met: %s" % okr.log[-200:]
    variants = [("7a", dict(clock="real")), ("7b", dict(db_write=False, w_env=False)), ("7c", dict(env={REDATE_ENV: "2026-11-05"})),
                ("7d", dict(day="2026-11-14", env={REDATE_ENV: "2026-11-14"})), ("7e", dict(now_date="2026-11-16"))]
    for tag, kw in variants:
        r = _redate_variant("rd_" + tag, **kw)
        if r.rc != 2 or "unrecognized arguments" in r.log or r.fake.wcalls:
            bad.append("%s: rc=%s, %d write-role calls (want rc 2 before any connection)" % (tag, r.rc, len(r.fake.wcalls)))
    res = w_cli("redate", start="15:20", flags=["--test-redate-today"], env={REDATE_ENV: DAY}, now_date="2026-11-14")
    why = need_run(res, "7f run")
    if why:
        return False, "; ".join(bad[:4] + [why])
    calls = w_scripts(res)
    names = cycle_names(res)
    ty, _nn = sql_types()
    tbl = FakeTable("2026-11-14")
    if not calls:
        bad.append("7 no script sent")
    for c in calls:
        sent = sent_rows(c)
        cands = [_nm(c["T"])] + (["final"] if "final" in names else [])
        okc = False
        for nm in cands:
            good = True
            for t in DELTA_TABLES:
                exp = []
                for row in u_rows(res, nm, t):
                    r = dict(zip(sql_columns()[t], row))
                    r["trading_day"] = "2026-11-14"
                    for col, tyc in ty[t].items():
                        if tyc == "timestamptz" and r[col] != "":
                            r[col] = (datetime.fromisoformat(r[col]) + timedelta(days=8)).isoformat()
                    exp.append(tuple(r[col] for col in sql_columns()[t]))
                if set(tbl.text_tuple(t, x) for x in exp) != set(tbl.text_tuple(t, x) for x in sent.get(t, [])):
                    good = False
            okc = okc or good
        if not okc:
            bad.append("7f-h the script of %s is not its cycle's rows with trading_day = 2026-11-14 and every timestamptz + 8 days (expiry unchanged)" % _hh(c["T"]))
            break
    diff = _same_outputs(res, w_off("off_1520"))
    if diff:
        bad.append("7i the files of a re-dated run differ from the flag-off run: %s" % diff[:3])
    for rel, tag in (("docs/tape/L2_live_runner_2b.service.template", "7k 2b"), ("docs/tape/L2_live_runner.service.template", "7l 2a")):
        t = _template_text(rel)
        if t is None:
            bad.append("%s template %s missing" % (tag, rel))
            continue
        if "--clock real" not in t or re.search(r"(?i)redate", t) or "--clock sim" in t or "write-clear" in t:
            bad.append("%s template: must run --clock real and carry no redate flag, --clock sim or write-clear" % tag)
        if rel.endswith("2b.service.template") and ("--db-write" not in t or "tape-w.env" not in t):
            bad.append("7k the 2b template lacks --db-write or EnvironmentFile tape-w.env")
    # 7n-7p: a test-only run has its own latch: it is not blocked by, and never writes or clears, the real one
    rdk = dict(start="15:20", flags=["--test-redate-today"], env={REDATE_ENV: DAY}, now_date="2026-11-14")
    d7 = _fresh_dir("rd_real")
    real = _plant_latch(d7)
    before = open(real, "rb").read()
    r7 = w_cli(None, out=d7, **rdk)
    why = need_run(r7, "7n run with a real latch present")
    if why:
        bad.append(why)
    elif not w_scripts(r7) or w_json(r7, "heartbeat.json").get("write", {}).get("state") == "stopped" or open(real, "rb").read() != before \
            or _latch_of(d7, redate=True):
        bad.append("7n a re-dated run with a real latch present: %d scripts, write %s, real latch unchanged %s (want it writing, the real latch byte-equal)" % (
            len(w_scripts(r7)), w_json(r7, "heartbeat.json").get("write"), open(real, "rb").read() == before))
    d7b = _fresh_dir("rd_stop")
    r7b = w_cli(None, out=d7b, plants=plants_of({"err": "42501"}), **rdk)
    if _latch_of(d7b, redate=True).get("reason") != "rls_refused" or os.path.exists(os.path.join(d7b, LATCH_NAME)):
        bad.append("7o a re-dated stop: redate latch %s, real latch present %s (want only %s)" % (
            _latch_of(d7b, redate=True), os.path.exists(os.path.join(d7b, LATCH_NAME)), LATCH_REDATE))
    for tag, extra, gone, kept in (("plain", (), LATCH_NAME, LATCH_REDATE), ("redate", ("--test-redate",), LATCH_REDATE, LATCH_NAME)):
        dd7 = _fresh_dir("rd_clear_" + tag)
        _plant_latch(dd7)
        _plant_latch(dd7, redate=True)
        rcc, logc = _wc(dd7, *extra)
        if rcc != 0 or os.path.exists(os.path.join(dd7, gone)) or not os.path.exists(os.path.join(dd7, kept)):
            bad.append("7p write-clear %s: rc=%s, %s present %s, %s present %s (want only %s cleared)" % (
                tag, rcc, gone, os.path.exists(os.path.join(dd7, gone)), kept, os.path.exists(os.path.join(dd7, kept)), gone))
    return not bad, "; ".join(bad[:8]) or "5 refusals (clock, flag, env day, day < today, weekend) rc 2 before any connection; Saturday run: trading_day = today, every timestamptz + 8 days, expiry unchanged, files byte-equal to the flag-off run; both templates --clock real, no redate"


def _typed_newest(tbl, t_view):
    """{table: set of typed tuples} of the three state tables through the newest-epoch rule, on typed values."""
    best = {}
    for t in DELTA_TABLES:
        for r in tbl.rows[t].values():
            k = (r["trading_day"], r["symbol"])
            if k not in best or r["as_of"] > best[k][0]:
                best[k] = (r["as_of"], r["live_run_id"])
    return dict((t, set(tuple(r[c] for c in tbl.cols[t]) for r in tbl.rows[t].values()
                        if r["live_run_id"] == best[(r["trading_day"], r["symbol"])][1])) for t in DELTA_TABLES)


def g_2b_restart():
    """Plan guard 8. Red first: no db_written (the write flags are unknown)."""
    bad = []
    res = w_canon()
    why = need_run(res, "8e canon run")
    if why:
        return False, why
    deltas = _deltas_of(res)
    dtbl = FakeTable(DAY)
    full = apply_db(deltas)
    want = dict((t, set(dtbl.text_tuple(t, r) for r in full[t].values())) for t in DELTA_TABLES)
    got = _typed_newest(res.table, None)
    for t in DELTA_TABLES:
        if got[t] != want[t]:
            bad.append("8e %s: U-only FakeTable through the newest-epoch rule != the D-applied state of the files (%d vs %d rows)" % (t, len(got[t]), len(want[t])))
    cli = mods()[0]
    for tag, plant, labels_skipped in (("A", {"crash_after": True}, True), ("A'", {"crash_before": True}, False)):
        ph = w_phases("rs_" + tag.replace("'", "p"), [{"start": "15:20", "plants": plants_of(None, plant)}, {"start": "15:28"}])
        if ph[0].rc != "CRASH" or ph[1].rc != 0:
            bad.append("8%s rc %s/%s (want CRASH then 0)" % (tag, ph[0].rc, ph[1].rc))
            continue
        crashed, first = w_scripts(ph[0])[1], w_scripts(ph[1])[0]
        if first["T"] != 925 or any(sorted(sent_rows(crashed).get(t, [])) != sorted(sent_rows(first).get(t, [])) for t in W_ORDER):
            bad.append("8%s the restart did not resend exactly the cycle that died (T %s)" % (tag, first["T"]))
        m = [x for x in w_metrics(ph[1]) if x["T"] == "15:25"]
        n_lab = len(sent_rows(first).get("tape_live_label", []))
        if not m or int(_f(m[0], "up_label_skipped")) != (n_lab if labels_skipped else 0) or n_lab == 0:
            bad.append("8c %s up_label_skipped %s, want %d" % (tag, m[0].get("up_label_skipped") if m else None, n_lab if labels_skipped else 0))
        st = apply_db(_deltas_of(ph[1]), u_only=True)
        for t in DELTA_TABLES:
            if ph[1].table.tuples(t) != set(ph[1].table.text_tuple(t, r) for r in st[t].values()):
                bad.append("8%s %s: the table after the restart != the U-only state of the files" % (tag, t))
        man = w_json_live(ph[1], "run_manifest.json")
        by_hand = dict((s, [mods()[5].epoch_id(DAY, s, TEST_SHA, 0)]) for s in ("NIFTY", "SENSEX"))
        if man.get("epochs") != by_hand or w_json(ph[1], "state.json").get("epoch") != {"NIFTY": 0, "SENSEX": 0}:
            bad.append("8d %s epochs %s, by hand %s" % (tag, man.get("epochs"), by_hand))
    # 8b: a skipped cycle, a kill, a restart: the first write is exactly the rows changed since db_written
    ph = w_phases("skip_kill_restart", [{"start": "15:20", "plants": plants_of(None, {"err": "57014", "kill": True})}, {"start": "15:33"}])
    first = w_scripts(ph[1])[0] if w_scripts(ph[1]) else None
    if first is None or first["T"] != 930:
        bad.append("8b no write at 15:30 after the restart")
    else:
        dl = _deltas_of(ph[1])
        s930, s920 = apply_db(dl, "1530", u_only=True), apply_db(dl, "1520", u_only=True)
        for t in DELTA_TABLES:
            exp = sorted(tuple("" if v is None else v for v in r) for k, r in s930[t].items() if s920[t].get(k) != r)
            if sorted(sent_rows(first).get(t, [])) != exp:
                bad.append("8b %s: %d rows sent, %d changed since the last committed write" % (t, len(sent_rows(first).get(t, [])), len(exp)))
    # 8f case D: another code sha re-emits every row under new ids
    sha2 = "fedcba9876543210fedcba9876543210fedcba98"
    ph = w_phases("sha_change", [{"start": "15:20", "plants": plants_of(None, {"kill": True})}, {"start": "15:33", "sha": sha2}])
    m = [x for x in w_metrics(ph[1]) if x["T"] == "15:30"]
    dl = _deltas_of(ph[1])
    full = apply_db(dl, "1530")
    for t in DELTA_TABLES:
        n = len(full[t])
        if not m or int(_f(m[0], "up_rows_" + t.replace("tape_live_", ""))) != n or len(u_rows(ph[1], "1530", t)) != n:
            bad.append("8f %s: rows sent at the restart under another sha %s, state holds %d (want every row)" % (t, m[0].get("up_rows_" + t.replace("tape_live_", "")) if m else None, n))
    v = _typed_newest(ph[1].table, None)
    shas = set(r[-1] for t in DELTA_TABLES for r in v[t])
    if shas != {sha2}:
        bad.append("8f the newest epoch still carries code_sha %s" % sorted(shas))
    return not bad, "; ".join(bad[:8]) or "U-only table through the newest-epoch rule == D-applied files; crash after commit and before commit both resend exactly the dead cycle (labels skipped / not), table == files; epochs by hand; skip + kill + restart resends exactly the rows changed since the last write; another sha re-emits every row"


def w_json_live(res, name):
    try:
        with open(os.path.join(live_of(res), name), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _naive(res_off):
    """Every U line of every cycle, in order, as a plain upsert (a writer with no prediction). -> (SQLSTATE or None, cycle name)."""
    tb = FakeTable(DAY)
    for nm in cycle_names(res_off):
        parts = []
        for t in DELTA_TABLES:
            rows = [dict((c, None if v == "" else v) for c, v in zip(sql_columns()[t], r)) for r in u_rows(res_off, nm, t)]
            if rows:
                parts.append(w_ref_insert(t, rows))
        try:
            tb.run(parse_script("BEGIN;\n" + "\n".join(parts) + "\nCOMMIT;"))
        except SqlError as exc:
            return exc.state, nm
    return None, None


def g_2b_grain_uq():
    """Plan guard 9. Red first (plan: the fake raises 23505): here the write flags are unknown, so only the preconditions run."""
    bad = []
    # the plants really produce the collision: a naive upsert of the files' U lines raises 23505 (else the guard is vacuous)
    for mode, frm in (("all", DAY + "T10:00:00+00:00"), ("inset", DAY + "T09:55:00+00:00")):
        off = w_off("remap_off_" + mode, plant=lambda m=mode, f=frm: plant_remap(m, f))
        if need_run(off, "remap %s flag-off" % mode):
            return False, need_run(off, "remap %s flag-off" % mode)
        st, nm = _naive(off)
        if st != "23505":
            bad.append("precondition %s: a naive upsert of the U lines gave %s at %s, want 23505" % (mode, st, nm))
    if _naive(w_off("off_1520"))[0] is not None:
        bad.append("precondition: the unplanted day collides in a naive upsert")
    if bad:
        return False, "; ".join(bad[:4])
    r = w_cli("remap_all", start="15:20", plant=lambda: plant_remap("all", DAY + "T10:00:00+00:00"))
    why = need_run(r, "9a remap run")
    if why:
        return False, why
    old = [x for x in r.table.rows["tape_live_cycle"].values() if x["symbol"] == "NIFTY" and x["instrument_token"] == 10103]
    new = [x for x in r.table.rows["tape_live_cycle"].values() if x["symbol"] == "NIFTY" and x["instrument_token"] == 99103]
    m = w_metrics(r)
    n_cnt = sum(int(_f(x, "cycle_grain_uq_violations")) for x in m)
    hb, ws, sent = _stop_of(r)
    wf = os.path.join(live_of(r), "db_withheld.csv")
    lines = open(wf, encoding="utf-8").read().splitlines() if os.path.exists(wf) else []
    if any(c["kind"] == "write" and "tags" not in c for c in r.fake.wcalls) or not old:
        bad.append("9a a script raised in the fake (an unpredicted 23505?) or the old token has no rows")
    if n_cnt != len(old):
        bad.append("9c cycle_grain_uq_violations summed over the day = %d, by hand %d (one per distinct key, not per cycle)" % (n_cnt, len(old)))
    if len(lines) != len(old) + 1:
        bad.append("9d db_withheld.csv has %d lines for %d withheld keys (header + keys)" % (len(lines), len(old)))
    if hb.get("state") == "stopped" or not new or not any(x["instrument_token"] != 99103 and x["ts_ist"] >= max(y["ts_ist"] for y in new) for x in r.table.rows["tape_live_cycle"].values()):
        bad.append("9e writes did not continue after the withheld rows: write %s, %d rows under the new token" % (hb, len(new)))
    # 9b: the collision is inside one write set (different primary keys, one grain)
    r = w_cli("remap_inset", start="15:20", plant=lambda: plant_remap("inset", DAY + "T09:55:00+00:00"))
    why = need_run(r, "9b run")
    if why:
        bad.append(why)
    else:
        dup_t = max(x["ts_ist"] for x in r.table.rows["tape_live_cycle"].values() if x["symbol"] == "NIFTY" and x["instrument_token"] in (10103, 99103))
        held = [x for x in r.table.rows["tape_live_cycle"].values() if x["symbol"] == "NIFTY" and x["instrument_token"] in (10103, 99103) and x["ts_ist"] == dup_t]
        n9 = sum(int(_f(x, "cycle_grain_uq_violations")) for x in w_metrics(r))
        if len(held) != 1 or n9 != 1 or _stop_of(r)[0].get("state") == "stopped":
            bad.append("9b in-set collision: %d rows hold the grain, %d counted, write %s (want 1, 1, writing)" % (len(held), n9, _stop_of(r)[0]))
    # 9f: a row the writer does not know about: counted, the write stops, nothing of that cycle lands
    def pre_foreign(table, parsed):
        ins = [s["insert"] for s in parsed["stmts"] if s.get("insert") and s["insert"]["table"] == "tape_live_cycle"][0]
        row = dict(zip(ins["cols"], ins["rows"][-1]))
        row["instrument_token"] = "77777"
        table.insert_foreign("tape_live_cycle", row)
    r = w_cli("grain_foreign", start="15:20", plants=plants_of(None, {"preload": pre_foreign}))
    hb, ws, sent = _stop_of(r)
    m = dict((x["T"], x) for x in w_metrics(r))
    at = [x for x in r.table.rows["tape_live_cycle"].values() if x["ts_ist"] == max(y["ts_ist"] for y in r.table.rows["tape_live_cycle"].values())]
    if need_run(r, "9f run") or hb.get("reason") != "cycle_grain_uq_unpredicted" or hb.get("state") != "stopped" or m.get("15:25", {}).get("cycle_grain_uq_violations") != "1" \
            or len(w_scripts(r)) != 2 or len(at) != 1:
        bad.append("9f unpredicted 23505: write %s, counted %s, %d scripts, %d rows at the newest instant (want stopped / cycle_grain_uq_unpredicted, 1, 2, 1: the foreign row only)" % (
            hb, m.get("15:25", {}).get("cycle_grain_uq_violations"), len(w_scripts(r)), len(at)))
    return not bad, "; ".join(bad[:8]) or "naive upserts of the plants raise 23505; cross-cycle remap: %d keys withheld once each and listed, writing on; in-set: 1 withheld; an unknown holder: counted, stopped, nothing of the cycle landed" % len(old)


def g_2b_confined():
    """Plan guard 10. Red first: no sink."""
    bad = []
    res = w_cli("on_short", start="15:25")
    why = need_run(res, "10 run")
    if why:
        return False, why
    if res.w_left:
        bad.append("10a %s is still in os.environ after start" % W_ENV)
    allcalls = list(res.fake.calls) + [(c["argv"], c["env"], c["stdin"], c["timeout"]) for c in res.fake.wcalls]
    for argv, _env, _stdin, _t in allcalls:
        if any(W_PW in a or W_DSN in a or "PGPASSWORD" in a for a in argv):
            bad.append("10b a secret or PGPASSWORD in an argv")
            break
    allowed = {"PATH", "LANG", "SystemRoot", "PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE", "PGSSLMODE", "PGOPTIONS",
               "PGCONNECT_TIMEOUT", "PGAPPNAME"}
    if not res.fake.wcalls:
        bad.append("10d no write-role call to inspect")
    for c in res.fake.wcalls:
        e = c["env"]
        if e.get("PGUSER") != W_USER or TEST_PW in "".join(str(v) for v in e.values()) or set(e) - allowed or "default_transaction_read_only=on" in e.get("PGOPTIONS", ""):
            bad.append("10d/e write env: user %r, keys beyond the allowlist %s, read-only option %s" % (e.get("PGUSER"), sorted(set(e) - allowed), "default_transaction_read_only=on" in e.get("PGOPTIONS", "")))
            break
    for argv, env, _s, _t in res.fake.calls:
        if argv[0] == "psql" and (W_PW in "".join(str(v) for v in env.values()) or env.get("PGUSER") == W_USER):
            bad.append("10d a read psql call carries the write role or its password")
            break
        if argv[0] == "aws" and any(k.startswith("PG") or W_PW in str(v) for k, v in env.items()):
            bad.append("10e the aws child environment carries PG* or the write password")
            break
    if res.fake.misrouted:
        bad.append("10d a write script was sent with the read role's environment (%d calls)" % len(res.fake.misrouted))
    r = w_cli("stderr_secret", start="15:20", plants=plants_of({"err": "stderr_secret"}))
    if need_run(r, "10c run") or w_json(r, "heartbeat.json").get("write", {}).get("state") != "stopped":
        bad.append("10c the failing write did not stop the writer (the check would be vacuous)")
    blobs = [("log", r.log.encode("utf-8"))] + [(rel, rd(os.path.join(r.root, rel))) for rel in _files(r.root) if not rel.startswith("raw/")]
    for name, b in blobs:
        for needle, what in ((W_PW, "the write password"), (W_DSN, "the write DSN"), (STDERR_MARK, "raw stderr")):
            if needle.encode() in b:
                bad.append("10c %s contains %s" % (name, what))
    # static: dbwrite.py and the rest of services/tape_live
    path = os.path.join(LIVE, "dbwrite.py")
    if not os.path.isfile(path):
        bad.append("10f/g dbwrite.py does not exist")
    else:
        tree = ast.parse(rd(path).decode("utf-8"))
        for n in ast.walk(tree):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                for m_ in [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]:
                    if m_.split(".")[0] == "subprocess" or any(m_ == x or m_.startswith(x + ".") for x in NET_MODS):
                        bad.append("10f dbwrite.py imports %s" % m_)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "os" \
                    and n.func.attr in ("system", "popen", "execv", "execve", "execvp", "spawnv", "spawnl"):
                bad.append("10f dbwrite.py calls os.%s" % n.func.attr)
        text = rd(path).decode("utf-8")
        for pname, rx in _secret_patterns():
            if pname != "test-credential" and rx.search(text):
                bad.append("10g dbwrite.py matches the secret pattern %s" % pname)
    write_words = re.compile(r"\b(INSERT|UPDATE|DELETE|TRUNCATE|DROP|ALTER|CREATE|GRANT|REVOKE|MERGE|COPY)\b")
    for n in sorted(os.listdir(LIVE)):
        if not n.endswith(".py") or n in ("dbwrite.py", "ddl.py"):
            continue
        _tree, consts = _consts(os.path.join(LIVE, n))
        for ln, s in consts:
            if write_words.search(s) and not (n == "wall_source.py" and s == "INSERT,UPDATE,DELETE,TRUNCATE"):
                bad.append("10h %s:%d names write SQL outside dbwrite.py: %r" % (n, ln, s[:40]))
    return not bad, "; ".join(bad[:8]) or "the write DSN leaves os.environ and argv, files and logs (also on a failing write whose stderr carries it); write and read environments never cross, the write one has no read-only option; dbwrite.py imports no subprocess or network module and matches no secret pattern; write SQL exists only in dbwrite.py"


def g_2b_restart_withheld():
    """Guard 34 (operator, 2026-11-14): a restart on a day that withheld rows rebuilds the writer's model WITHOUT them. A withheld
    row never reached the table, so a model that holds it is wrong: it stops predicting the collision and hides the row's holder.
    Remap plant from 15:30 (74 NIFTY rows withheld at 15:30), kill after that write, restart at 15:38: at the restart's start() the
    model of the cycle table must equal what the table holds, exactly. Red first: the model is rebuilt from every U line."""
    dbw = _dbw()
    if dbw is None:
        return False, "ImportError: services.tape_live.dbwrite does not exist"
    ft = FakeTable(DAY)
    snaps = []
    orig = dbw.DbWriter.start

    def start(self, st, live_dir, fresh):
        orig(self, st, live_dir, fresh)
        snaps.append((fresh, set(ft.text_tuple("tape_live_cycle", r) for r in self.model["tape_live_cycle"].values()),
                      set(_W_TABLE["t"].tuples("tape_live_cycle"))))
    dbw.DbWriter.start = start
    try:
        ph = w_phases("withheld_restart", [{"start": "15:20", "plants": plants_of(None, None, {"kill": True})}, {"start": "15:38"}],
                      plant=lambda: plant_remap("all", DAY + "T10:00:00+00:00"))
    finally:
        dbw.DbWriter.start = orig
    bad = []
    for i, r in enumerate(ph):
        why = need_run(r, "phase %d" % (i + 1))
        if why:
            return False, why
    old = [x for x in ph[1].table.rows["tape_live_cycle"].values() if x["symbol"] == "NIFTY" and x["instrument_token"] == 10103]
    wf = os.path.join(live_of(ph[1]), "db_withheld.csv")
    n_lines = len(open(wf, encoding="utf-8").read().splitlines()) if os.path.exists(wf) else 0
    if len(snaps) != 2 or snaps[1][0] or not old or n_lines != len(old) + 1:
        return False, "precondition: %d start() calls (the second must be a restart), %d old-token rows, db_withheld.csv has %d lines (want header + %d)" % (
            len(snaps), len(old), n_lines, len(old))
    _fresh, model, held = snaps[1]
    if model != held:
        bad.append("8g the model rebuilt at the restart holds %d rows the table never received (the withheld rows) and lacks %d the table holds" % (
            len(model - held), len(held - model)))
    m2 = [x for x in w_metrics(ph[1]) if x["T"] >= "15:35"]
    hb, _ws, _sent = _stop_of(ph[1])
    if not m2 or sum(int(_f(x, "cycle_grain_uq_violations")) for x in m2) != 0 or hb.get("state") == "stopped":
        bad.append("8g after the restart: %d new grain violations counted, write %s (want none counted, still writing)" % (
            sum(int(_f(x, "cycle_grain_uq_violations")) for x in m2), hb))
    return not bad, "; ".join(bad[:4]) or "after a kill and a restart on a day that withheld %d rows, the rebuilt model equals the table (withheld rows excluded, their holders kept); nothing is counted twice" % len(old)


GUARDS_2B = [("live-2b-off", g_2b_off), ("live-2b-upsert-only", g_2b_upsert_only), ("live-2b-statements", g_2b_statements),
             ("live-2b-metrics", g_2b_metrics), ("live-2b-stop", g_2b_stop), ("live-2b-latch", g_2b_latch), ("live-2b-startup", g_2b_startup),
             ("live-2b-redate", g_2b_redate), ("live-2b-restart", g_2b_restart), ("live-2b-grain-uq", g_2b_grain_uq),
             ("live-2b-confined", g_2b_confined),
             ("live-2b-restart-withheld", g_2b_restart_withheld)]


GUARDS = [("live-vectors", g_vectors), ("live-derive", g_derive), ("live-rule-inputs", g_rule_inputs),
          ("live-wall-floor", g_wall_floor), ("live-first-wins", g_first_wins), ("live-equal-offline", g_equal_offline),
          ("live-causal", g_causal), ("live-verify", g_verify), ("live-deterministic", g_deterministic),
          ("live-no-outcomes", g_no_outcomes), ("live-isolated", g_isolated), ("live-sql", g_sql),
          ("live-ts-width", g_ts_width), ("live-rebuild-scope", g_rebuild_scope),
          ("live-runner-equal", g_runner_equal), ("live-runner-readonly", g_runner_readonly),
          ("live-runner-secrets", g_runner_secrets), ("live-runner-bounded-sql", g_runner_bounded_sql),
          ("live-runner-keyset", g_runner_keyset), ("live-runner-lifecycle", g_runner_lifecycle),
          ("live-runner-restart", g_runner_restart), ("live-epoch", g_epoch), ("live-dbshape", g_dbshape)] + GUARDS_2B


def main():
    sel = [g for g in GUARDS if ARGS.only in (None, g[0])]
    if not sel:
        print("unknown guard %r" % ARGS.only)
        return 2
    ok_n = 0
    for name, fn in sel:
        try:
            ok, msg = fn()
        except Exception as exc:  # noqa: BLE001 - a crash is a FAIL with its traceback, never a skip
            ok, msg = False, "%s: %s\n%s" % (type(exc).__name__, exc, traceback.format_exc()[-1500:])
        ok_n += ok
        print("GUARD %-20s %s  %s" % (name, "PASS" if ok else "FAIL", msg))
    shutil.rmtree(_TMP, ignore_errors=True)
    if ok_n == len(sel):
        print("TAPE LIVE GUARDS PASS (%d/%d)" % (ok_n, len(sel)))
        return 0
    print("TAPE LIVE GUARDS FAIL (%d/%d passed)" % (ok_n, len(sel)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
