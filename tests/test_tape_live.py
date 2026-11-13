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
import csv
import gzip
import hashlib
import io
import json
import os
import random
import re
import shutil
import sys
import tempfile
import traceback
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


GUARDS = [("live-vectors", g_vectors), ("live-derive", g_derive), ("live-rule-inputs", g_rule_inputs),
          ("live-wall-floor", g_wall_floor), ("live-first-wins", g_first_wins), ("live-equal-offline", g_equal_offline),
          ("live-causal", g_causal), ("live-verify", g_verify), ("live-deterministic", g_deterministic),
          ("live-no-outcomes", g_no_outcomes), ("live-isolated", g_isolated), ("live-sql", g_sql),
          ("live-ts-width", g_ts_width), ("live-rebuild-scope", g_rebuild_scope),
          ("live-runner-equal", g_runner_equal), ("live-runner-readonly", g_runner_readonly),
          ("live-runner-secrets", g_runner_secrets), ("live-runner-bounded-sql", g_runner_bounded_sql),
          ("live-runner-keyset", g_runner_keyset), ("live-runner-lifecycle", g_runner_lifecycle),
          ("live-runner-restart", g_runner_restart), ("live-epoch", g_epoch), ("live-dbshape", g_dbshape)]


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
