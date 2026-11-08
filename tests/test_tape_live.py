#!/usr/bin/env python3
"""Tape live L0 guards (docs/tape/L0_plan.md sections 7-8): rules v1, the replay-mode writer, the wall source, verify, the SQL.

  python tests/test_tape_live.py [--root DIR] [--only GUARD]

--root runs the guards against another copy of the tree (tests/tape_live_mutants.py uses it). Every fixture is generated under a
temp dir by tests/tape_live/gen_live.py; no golden day, no network, no database, no .env.

Rule 23 (CLAUDE.md): refuses an unlimited `ulimit -v` where the `resource` module exists, and Mon-Fri 08:30-15:45 IST.
OPERATOR RULING R-1 (2026-11-03): the time-window refusal is a retail-box rule; this machine is Local. The window is lifted ONLY
when TAPE_RULE23_OVERRIDE_R1=1 is set, and every such run says so on its first line.

Last line: "TAPE LIVE GUARDS PASS (14/14)" or "TAPE LIVE GUARDS FAIL (...)". Exit 0 / 1; 2 = refused.
"""
import argparse
import ast
import contextlib
import csv
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
    names = sorted(n for n in os.listdir(os.path.join(d, "cycles")))
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
# The default fixture's raw + chain files, (file count, digest of the sorted "relpath sha256" lines), measured on the generator at
# 276e221 BEFORE the scope variant was added: the scope variant must leave the default day byte-unchanged.
DEFAULT_FIXTURE = (164, "d9335e6b784af9e7c5eea965dff1a0dd028b475d0fa951cda46b3fa371888c55")


def _tree_digest(root):
    items = sorted((os.path.relpath(os.path.join(dp, n), root).replace(os.sep, "/"), sha(os.path.join(dp, n)))
                   for sub in ("raw", "chain") for dp, _ds, ns in os.walk(os.path.join(root, sub)) for n in ns)
    return len(items), hashlib.sha256("".join("%s %s\n" % i for i in items).encode("utf-8")).hexdigest()


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
    if _tree_digest(ctl_root) != DEFAULT_FIXTURE:
        bad.append("control: default fixture changed %r != %r" % (_tree_digest(ctl_root), DEFAULT_FIXTURE))
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


GUARDS = [("live-vectors", g_vectors), ("live-derive", g_derive), ("live-rule-inputs", g_rule_inputs),
          ("live-wall-floor", g_wall_floor), ("live-first-wins", g_first_wins), ("live-equal-offline", g_equal_offline),
          ("live-causal", g_causal), ("live-verify", g_verify), ("live-deterministic", g_deterministic),
          ("live-no-outcomes", g_no_outcomes), ("live-isolated", g_isolated), ("live-sql", g_sql),
          ("live-ts-width", g_ts_width), ("live-rebuild-scope", g_rebuild_scope)]


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
