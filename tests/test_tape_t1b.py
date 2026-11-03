#!/usr/bin/env python3
"""Tape T1b guards (docs/tape/T1b_plan.md section 2): cycle aggregator, event candidates, merged chain events.

  python tests/test_tape_t1b.py [--root DIR] [--only GUARD]

--root runs the guards against another copy of the tree (tests/tape_t1b_mutants.py uses it).

Rule 23 (CLAUDE.md): refuses an unlimited `ulimit -v` where the `resource` module exists, and Mon-Fri 08:30-15:45 IST.
OPERATOR RULING R-1 (2026-11-03): the time-window refusal is a retail-box rule; this machine is Local. The window is
therefore lifted ONLY when TAPE_RULE23_OVERRIDE_R1=1 is set in the environment, and every such run says so on its
first line. This override belongs to THIS file; tests/test_tape_t1a.py and tests/run_offline.sh have no override and
were not edited.
"""
import argparse
import ast
import contextlib
import csv
import io
import json
import os
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
sys.path.insert(0, os.path.join(ROOT, "tests", "tape_t1b"))

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

import gen_chain  # noqa: E402
import gen_cycle as gen  # noqa: E402

DAY = gen.DAY
TMP = []
CYC_OUTS = ("tape_strike_cycle.csv", "tape_events.csv", "cycle_report.json", "cycle_report.txt", "run_manifest.json")
CH_OUTS = ("chain_events.csv", "chain_runs.csv", "chain_report.json", "chain_report.txt", "run_manifest.json")


def tmpdir():
    d = tempfile.mkdtemp(prefix="tape_t1b_")
    TMP.append(d)
    return d


def run_cycle(inp, sess, out):
    from services.tape_offline import cycle_day
    so, se = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(so), contextlib.redirect_stderr(se):
        rc = cycle_day.main(["--in", inp, "--session", sess, "--out", out])
    return rc, so.getvalue(), se.getvalue()


def run_chain(inp, out, extra=()):
    from services.tape_chain import chain_events_day
    so, se = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(so), contextlib.redirect_stderr(se):
        rc = chain_events_day.main(["--in", inp, "--out", out] + list(extra))
    return rc, so.getvalue(), se.getvalue()


def rd(d, name):
    with open(os.path.join(d, name), "rb") as fh:
        return fh.read()


def csv_rows(d, name):
    return list(csv.DictReader(io.StringIO(rd(d, name).decode("utf-8"))))


_C = {}


def cyc():
    if "c" not in _C:
        root, out = tmpdir(), tmpdir()
        T = gen.build(root)
        rc, so, se = run_cycle(T["inp"], T["sess"], out)
        _C["c"] = (root, out, T, rc, so, se)
    return _C["c"]


def chain(offset="+00:00", name=None):
    key = "ch" + offset
    if key not in _C:
        d = os.path.join(tmpdir(), name or "chain_%s" % DAY)
        gen_chain.write(d, "NIFTY", offset)
        out = tmpdir()
        rc, so, se = run_chain(d, out)
        _C[key] = (d, out, rc, so, se)
    return _C[key]


def cmp_fields(fields, label):
    root, out, T, rc, so, se = cyc()
    got = {(int(r["token"]), r["T"]): r for r in csv_rows(out, "tape_strike_cycle.csv")}
    bad, n = [], 0
    for t in T["toks"]:
        for Tm, want in gen.truth_cycle(t).items():
            r = got.get((t.token, gen.iso(Tm)))
            if r is None:
                bad.append("token %d %s: row missing" % (t.token, gen.hm(Tm)))
                continue
            for f in fields:
                n += 1
                if r[f] != want[f]:
                    bad.append("token %d %s %s: got %r want %r" % (t.token, gen.hm(Tm), f, r[f], want[f]))
    return [(rc == 0, "cycle_day exit 0 (got %d)" % rc),
            (not bad and n > 0, "%d %s cells equal the generator's brute-force truth; mismatches: %s" % (n, label, bad[:3] or "none"))]


# ====================================================================== cycle guards
def g_cyc_bins():
    cells = cmp_fields(("buy_5", "sell_5", "uncl_5", "gap_5", "trades_5", "buy_15", "sell_15", "buy_30", "sell_30",
                        "buy_cum", "sell_cum", "uncl_cum", "gap_cum", "balance_5", "balance_15", "balance_30",
                        "classified_share_5"), "bin / trailing / cumulative")
    return cells


def g_cyc_window():
    root, out, T, rc, so, se = cyc()
    got = {(int(r["token"]), r["T"]) for r in csv_rows(out, "tape_strike_cycle.csv")}
    want = {(t.token, gen.iso(Tm)) for t in T["toks"] for Tm in gen.truth_cycle(t)}
    late = [t for t in T["toks"] if t.token == 1005][0]
    early_rows = [k for k in got if k[0] == 1005 and k[1] < gen.iso(late.first_T)]
    cells = cmp_fields(("minutes_present_5", "first_seen_T", "resting_imb", "oi_last", "oi_delta_5"), "window / depth / OI")
    cells.append((got == want, "row keys equal the planted (token, T) set: %d rows, %d missing, %d extra"
                  % (len(got), len(want - got), len(got - want))))
    cells.append((not early_rows and any(k[0] == 1005 for k in got),
                  "late strike 1005 (added 10:03) has rows from %s and none earlier: %s" % (gen.hm(late.first_T), early_rows[:2] or "none")))
    return cells


def g_cyc_invariant():
    root, out, T, rc, so, se = cyc()
    rep = json.loads(rd(out, "cycle_report.json").decode("utf-8"))
    ins, oos = T["totals"]
    got = {"buy": 0, "sell": 0, "uncl": 0, "gap": 0}
    per = {}
    for r in csv_rows(out, "tape_strike_cycle.csv"):
        for c in got:
            got[c] += int(r[c + "_5"])
        p = per.setdefault(int(r["token"]), [0, 0, 0, 0])
        for i, c in enumerate(("buy", "sell", "uncl", "gap")):
            p[i] += int(r[c + "_5"])
    want_per = {t.token: [sum(r[c] for r in t.mins.values()) for c in ("buy", "sell", "uncl", "gap")] for t in T["toks"]}
    n_oos = sum(len(t.oos) for t in T["toks"])
    return [(rc == 0 and rep["invariant"]["ok"], "the run's own invariant is OK, exit 0 (got %d)" % rc),
            (got == ins, "cycle category totals %s == generator in-session totals %s" % (got, ins)),
            (per == want_per, "per-token category sums equal the generator's (%d tokens)" % len(want_per)),
            (rep["qty_out_of_session"] == oos and rep["rows_out_of_session"] == n_oos,
             "out-of-session rows %d and qty %s reported and kept out of the cycle rows" % (rep["rows_out_of_session"], rep["qty_out_of_session"]))]


# ====================================================================== event guards
def events_got():
    root, out, T, rc, so, se = cyc()
    rows = csv_rows(out, "tape_events.csv")
    return rows, {(r["symbol"], r["expiry"], r["strike"], r["leg"], r["kind"], r["ts_ist"], r["side"]) for r in rows}, T, rc


def g_ev_conc_z():
    rows, got, T, rc = events_got()
    conc = {k for k in got if k[4] == "CONC"}
    want = {k for k in T["events"] if k[4] == "CONC"}
    e = [r for r in rows if r["kind"] == "CONC" and r["strike"] == "25000"]
    z1, z2 = gen.conc_z_truth(T["c1"])
    det = json.loads(e[0]["detail_json"]) if e else {}
    cells = [(rc == 0, "cycle_day exit 0"), (conc == want, "CONC events equal the planted set %s; got %s" % (sorted(want), sorted(conc)))]
    cells.append((bool(e) and det.get("z_1") is not None and det.get("z_2") is not None and abs(det["z_1"] - z1) < 1e-5 and abs(det["z_2"] - z2) < 1e-5,
                  "planted burst z_1=%.6f z_2=%.6f (truth from statistics.pstdev on PRIOR bins only); got %s"
                  % (z1, z2, (det.get("z_1"), det.get("z_2")))))
    cells.append((det.get("n_prior_1") == 12 and det.get("n_prior_2") == 13 and det.get("agg_1") == 1000,
                  "n_prior 12 then 13, agg 1000: %s" % {k: det.get(k) for k in ("n_prior_1", "n_prior_2", "agg_1")}))
    quiet = {"25100": "1-bin burst", "25200": "11 prior bins", "25300": "std = 0 history", "25400": "2 < z < 3"}
    fired = [(s, why) for s, why in quiet.items() if any(k[2] == s and k[4] == "CONC" for k in got)]
    cells.append((not fired, "no CONC on the 1-bin burst, the 11-prior burst, the std=0 history or the 2<z<3 burst; fired: %s" % (fired or "none")))
    return cells


def g_ev_thin():
    rows, got, T, rc = events_got()
    thin = {k for k in got if k[4] == "THIN"}
    want = {k for k in T["events"] if k[4] == "THIN"}
    e = [r for r in rows if r["kind"] == "THIN" and r["strike"] == "26000"]
    det = json.loads(e[0]["detail_json"]) if e else {}
    quiet = {"26100": "1-minute collapse", "26200": "51 pct of the median", "26300": "mean-trap window"}
    fired = [(s, why) for s, why in quiet.items() if any(k[2] == s and k[4] == "THIN" for k in got)]
    return [(rc == 0, "cycle_day exit 0"),
            (thin == want, "THIN events equal the planted set %s; got %s" % (sorted(want), sorted(thin))),
            (det.get("depth") == 500 and det.get("median_30") == 1000.0 and det.get("n_window") == 30 and det.get("minute") == "09:46",
             "collapse detail (depth 500, median 1000, window 30, minute 09:46; stamped 09:47): %s" % det),
            (not fired, "no THIN on the 1-minute collapse, the 51 pct collapse or the mean trap; fired: %s" % (fired or "none"))]


def g_ev_onset():
    rows, got, T, rc = events_got()
    persist = [r for r in rows if r["kind"] == "CONC" and r["strike"] == "25500"]
    hole = [r for r in rows if r["kind"] == "THIN" and r["strike"] == "26400"]
    return [(rc == 0, "cycle_day exit 0"),
            (len(persist) == 1, "the persisting CONC condition (4 bursts, z>=3 on every bin) yields exactly one event: %d" % len(persist)),
            (len(hole) == 1, "the 6-minute depth collapse with one absent minute yields exactly one event: %d" % len(hole)),
            (got == T["events"], "the full event set equals the independent reference over all %d option tokens: %d vs %d"
             % (sum(1 for t in T["toks"] if t.leg in ("CE", "PE")), len(got), len(T["events"])))]


# ====================================================================== chain guards
def chain_rows():
    d, out, rc, so, se = chain()
    return csv_rows(out, "chain_events.csv"), json.loads(rd(out, "chain_report.json").decode("utf-8")), rc


def hmm(ts):
    return int(ts[11:13]) * 60 + int(ts[14:16])


def g_ch_e1_e2():
    rows, rep, rc = chain_rows()
    s = rep["per_symbol"].get("NIFTY")
    if s is None:
        return [(False, "no NIFTY runs survived (per_symbol %s, counters %s)" % (sorted(rep["per_symbol"]), rep["counters"]))]
    by = {(r["kind"], hmm(r["ts_ist"])): r for r in rows}
    cc, pp = by.get(("E2-call", gen_chain.hm(10, 10))), by.get(("E2-put", gen_chain.hm(10, 20)))
    return [(rc == 0, "chain_events_day exit 0 (got %d)" % rc),
            (cc is not None and cc["strike"] == "24600" and cc["prev_strike"] == "24700" and cc["prev_value"] == "100000" and cc["new_value"] == "100000",
             "call-wall move 24700 -> 24600 at 10:10: %s" % cc),
            (pp is not None and pp["strike"] == "24300" and pp["prev_value"] == "100000" and pp["new_value"] == "105000",
             "put-wall OI +5.0 pct (100000 -> 105000) at 10:20 fires: %s" % pp),
            (("E2-put", gen_chain.hm(10, 25)) not in by, "put-wall OI +4.9 pct (105000 -> 110145) at 10:25 does not fire"),
            (s["raw_events"] == gen_chain.EXPECTED_RAW, "raw (pre-merge) events per kind equal the hand count %s: %s" % (gen_chain.EXPECTED_RAW, s["raw_events"])),
            (not any(hmm(r["ts_ist"]) < 600 for r in rows) and s["runs_pre_window"] == 2,
             "the 09:50 and 09:55 runs are ignored (2 pre-window runs, no event before 10:00)"),
            (all(r["expiry"] == gen_chain.FRONT for r in rows) and s["raw_events"].get("E1") == 7,
             "only the front expiry %s produces events (the back expiry flips its leader every run)" % gen_chain.FRONT)]


def g_ch_merge():
    rows, rep, rc = chain_rows()
    e1 = [(hmm(r["ts_ist"]), int(r["strike"]), int(r["prev_strike"]), int(r["merged_n"])) for r in rows if r["kind"] == "E1"]
    want = [(m, k, p, n) for (kind, m, k, p, n) in gen_chain.EXPECTED if kind == "E1"]
    allexp = [(kind, m, k, p, n) for (kind, m, k, p, n) in gen_chain.EXPECTED]
    allgot = [(r["kind"], hmm(r["ts_ist"]), int(r["strike"]), int(r["prev_strike"]), int(r["merged_n"])) for r in rows]
    return [(rc == 0, "chain_events_day exit 0"),
            (sorted(e1) == sorted(want), "E1: the 10:30 / 10:34 / 10:38 triple is ONE event with merged_n=3, the 10:32 / 10:36 / 10:42 A-triple is one, "
             "and the 10:46 event (16 min after the counted one) is separate: got %s" % sorted(e1)),
            (sorted(allgot) == sorted(allexp), "the whole counted-event list equals the hand list (%d events)" % len(allexp))]


def g_ch_e3():
    rows, rep, rc = chain_rows()
    d, out, rc2, so, se = chain()
    runs = csv_rows(out, "chain_runs.csv")
    signs = [int(r["net_sign"]) for r in runs if r["in_window"] == "1"]
    e3 = rep["per_symbol"].get("NIFTY", {}).get("e3_flips")
    return [(e3 == gen_chain.EXPECTED_E3, "E3 net-sign flips counted: %s (hand count %d)" % (e3, gen_chain.EXPECTED_E3)),
            (not any(r["kind"].startswith("E3") for r in rows), "no E3 row in chain_events.csv: kinds %s" % sorted({r["kind"] for r in rows})),
            (signs.count(-1) == 1 and len(runs) == 16, "chain_runs.csv carries the sign per run (one negative run, %d runs)" % len(runs))]


# ====================================================================== guards on the code itself
def src(rel):
    return open(os.path.join(ROOT, rel), encoding="utf-8").read()


TAPE_FILES = ("merdian_compute/tape/cycle.py", "merdian_compute/tape/events.py", "services/tape_offline/cycle_day.py")
CHAIN_FILES = ("merdian_compute/tape/chain_events.py", "services/tape_chain/chain_events_day.py", "services/tape_chain/export_chain.py")
PURE3 = ("merdian_compute/tape/cycle.py", "merdian_compute/tape/events.py", "merdian_compute/tape/chain_events.py")
BOTH_BAN = (r"lead_time", r"\blead\b", r"coverage", r"agreement", r"straddle_atm", r"spot", r"outcome", r"ret_30m")
TAPE_BAN = BOTH_BAN + (r"\bgex", r"strike_snapshots", r"chain_events", r"tape_chain", r"oi_call", r"oi_put", r"\bwall", r"\bleader")
CHAIN_BAN = BOTH_BAN + (r"tape_minute", r"tape_strike_cycle", r"bid_qty", r"ask_qty", r"buy_5", r"sell_5", r"tape_offline")


def _imports(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name
        elif isinstance(node, ast.ImportFrom):
            yield ("." * node.level) + (node.module or "")
            for a in node.names:
                yield (node.module or "") + "." + a.name


def g_no_join():
    hits = []
    for rel in TAPE_FILES:
        text = src(rel).lower()
        hits += ["%s: /%s/" % (os.path.basename(rel), p) for p in TAPE_BAN if re.search(p, text)]
        for m in _imports(os.path.join(ROOT, rel)):
            if {"chain_events", "tape_chain"} & set(m.split(".")):
                hits.append("%s imports %s" % (os.path.basename(rel), m))
    for rel in CHAIN_FILES:
        text = src(rel).lower()
        hits += ["%s: /%s/" % (os.path.basename(rel), p) for p in CHAIN_BAN if re.search(p, text)]
        for m in _imports(os.path.join(ROOT, rel)):
            if {"cycle", "events", "minute", "replay", "classify", "tape_offline"} & set(m.split(".")):
                hits.append("%s imports %s" % (os.path.basename(rel), m))
    return [(not hits, "%d tape-side and %d chain-side files scanned (text and imports); hits: %s" % (len(TAPE_FILES), len(CHAIN_FILES), hits or "none"))]


FORBID = {"time", "random", "socket", "ssl", "http", "urllib", "requests", "asyncio", "secrets", "uuid", "boto3", "botocore",
          "kiteconnect", "os", "sys", "subprocess", "shutil", "pathlib", "gzip", "io", "tempfile", "threading",
          "multiprocessing", "supabase", "psycopg2", "dhanhq", "csv"}


def g_pure():
    bad = []
    for rel in PURE3:
        tree = ast.parse(src(rel))
        f = os.path.basename(rel)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                bad += ["%s: import %s" % (f, a.name) for a in node.names if a.name.split(".")[0] in FORBID]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and (node.module or "").split(".")[0] in FORBID:
                bad.append("%s: from %s" % (f, node.module))
            elif isinstance(node, ast.Call):
                fn = node.func
                if isinstance(fn, ast.Attribute) and fn.attr in ("now", "utcnow", "today", "time", "open", "monotonic"):
                    bad.append("%s: .%s(" % (f, fn.attr))
                if isinstance(fn, ast.Name) and fn.id in ("open", "print", "input", "__import__", "exec", "eval"):
                    bad.append("%s: %s(" % (f, fn.id))
    return [(not bad, "%d pure modules scanned; forbidden: %s" % (len(PURE3), bad or "none"))]


def _tree_equal(a, b, outs):
    return all(rd(a, n) == rd(b, n) for n in outs)


def g_deterministic():
    cells = []
    root, out1, T, rc, so, se = cyc()
    r2, o2 = tmpdir(), tmpdir()
    shutil.copytree(root, os.path.join(r2, "x"))
    rc2, _a, _b = run_cycle(os.path.join(r2, "x", "in"), os.path.join(r2, "x", "session"), o2)
    cells.append((rc2 == 0 and _tree_equal(out1, o2, CYC_OUTS), "cycle_day: two runs on two input copies are byte-identical (%s)" % ", ".join(CYC_OUTS)))
    man = json.loads(rd(out1, "run_manifest.json").decode("utf-8"))
    import hashlib
    ok = all(hashlib.sha256(rd(out1, n)).hexdigest() == h for n, h in man["outputs"].items())
    cells.append((ok and len(man["outputs"]) == 4, "cycle_day manifest hashes equal the files' sha256 (%d outputs)" % len(man["outputs"])))
    d, outc, rcc, so, se = chain()
    r3, o3 = tmpdir(), tmpdir()
    d2 = os.path.join(r3, "chain_%s" % DAY)
    shutil.copytree(d, d2)
    rc3, _a, _b = run_chain(d2, o3)
    cells.append((rc3 == 0 and _tree_equal(outc, o3, CH_OUTS), "chain_events_day: two runs on two input copies are byte-identical"))
    manc = json.loads(rd(outc, "run_manifest.json").decode("utf-8"))
    cells.append((all(hashlib.sha256(rd(outc, n)).hexdigest() == h for n, h in manc["outputs"].items()) and len(manc["outputs"]) == 4,
                  "chain_events_day manifest hashes equal the files' sha256"))
    return cells


def g_isolated():
    cells = []
    rdir = os.path.join(ROOT, "services", "tape_runner")
    bad = []
    for f in sorted(os.listdir(rdir)):
        if f.endswith(".py"):
            for m in _imports(os.path.join(rdir, f)):
                if "tape_offline" in m or "tape_chain" in m or m.startswith("merdian_compute"):
                    bad.append("%s: %s" % (f, m))
    cells.append((not bad, "no services/tape_runner module imports tape_offline, tape_chain or merdian_compute: %s" % (bad or "none")))
    inst = src("services/tape_runner/install.sh")
    m = re.search(r"archive HEAD ([^|]*?) \|", inst)
    cells.append((bool(m) and m.group(1).split() == ["services/__init__.py", "services/tape_runner"],
                  "install.sh archives only %s (so tape_offline / tape_chain are not shipped)" % (m.group(1) if m else "?")))
    std = set(sys.stdlib_module_names)
    badi = []
    files = PURE3 + ("services/tape_offline/cycle_day.py", "services/tape_chain/chain_events_day.py",
                     "services/tape_chain/export_chain.py", "services/tape_chain/__init__.py")
    for rel in files:
        for mod in _imports(os.path.join(ROOT, rel)):
            top = mod.split(".")[0]
            if not top or mod.startswith("."):
                continue
            if top in std or mod.startswith("merdian_compute.tape") or mod.startswith("services.tape_") \
                    or mod in ("merdian_compute", "services"):
                continue
            if rel.endswith("export_chain.py") and mod.startswith("core.supabase_client"):
                continue
            badi.append("%s: %s" % (os.path.basename(rel), mod))
    cells.append((not badi, "T1b imports are stdlib, merdian_compute.tape or services.tape_*; only export_chain.py may import core.supabase_client: %s" % (badi or "none")))
    return cells


WRITE_CALLS = {"insert", "upsert", "update", "delete", "rpc", "_request", "execute", "post", "patch", "put", "request"}


def g_export_select_only():
    rel = "services/tape_chain/export_chain.py"
    tree = ast.parse(src(rel))
    consts = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            consts[node.targets[0].id] = node.value.value
    writes, tables, selects = [], set(), 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in WRITE_CALLS:
                writes.append(node.func.attr)
            if node.func.attr == "select":
                selects += 1
                a = node.args[0] if node.args else None
                if isinstance(a, ast.Constant):
                    tables.add(a.value)
                elif isinstance(a, ast.Name):
                    tables.add(consts.get(a.id, "?" + a.id))
                else:
                    tables.add("?")
    text = src(rel)
    words = [w for w in ("requests.", "urllib", ".rpc(", "upsert(", ".insert(", ".delete(", ".update(") if w in text]
    return [(not writes and not words, "no write call in export_chain.py: attribute calls %s, text %s" % (writes or "none", words or "none")),
            (selects >= 1 and tables == {"gex_strike_snapshots"}, "every select() names exactly the table gex_strike_snapshots: %s (%d calls)" % (sorted(tables), selects))]


# ====================================================================== units
def u_ts_ist():
    a = chain("+00:00")
    b = chain("+05:30", name="chain_%s" % DAY)
    same = rd(a[1], "chain_events.csv") == rd(b[1], "chain_events.csv") and rd(a[1], "chain_runs.csv") == rd(b[1], "chain_runs.csv")
    return [(a[2] == 0 and b[2] == 0 and same, "the same chain stamped +00:00 and +05:30 gives identical events and runs")]


def u_session_dir():
    root, out, T, rc, so, se = cyc()
    o2 = tmpdir()
    rc2, _a, _b = run_cycle(T["inp"], os.path.join(T["sess"], DAY), o2)
    return [(rc2 == 0 and rd(o2, "tape_strike_cycle.csv") == rd(out, "tape_strike_cycle.csv"),
             "--session may be the subscriptions directory itself or its parent")]


def u_int_z():
    from merdian_compute.tape import events
    hist = [(560 + 5 * i, 90 if i % 2 == 0 else 110, 0) for i in range(12)]
    at3 = events.conc_events(hist + [(620, 130, 0), (625, 1000, 0)])
    under = events.conc_events(hist + [(620, 129, 0), (625, 1000, 0)])
    return [(len(at3) == 1 and abs(at3[0]["z1"] - 3.0) < 1e-12 and not under,
             "z = 3 exactly (12 bins at 90/110, burst 130) fires; burst 129 (z=2.9) does not")]


def u_windows_safe():
    bad = []
    for rel in PURE3 + ("services/tape_offline/cycle_day.py", "services/tape_chain/chain_events_day.py", "services/tape_chain/export_chain.py"):
        tree = ast.parse(src(rel))
        f = os.path.basename(rel)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                bad += ["%s: import %s" % (f, m) for m in names if m.split(".")[0] in ("resource", "fcntl", "termios", "pwd", "grp", "signal", "pty")]
            elif isinstance(node, ast.Attribute) and node.attr in ("fork", "getuid", "geteuid", "chown", "fchmod", "mkfifo"):
                bad.append("%s: .%s" % (f, node.attr))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
                kw = {k.arg: k.value for k in node.keywords}
                mode = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else \
                    (kw["mode"].value if "mode" in kw and isinstance(kw["mode"], ast.Constant) else "r")
                if "b" in mode:
                    continue
                if "encoding" not in kw:
                    bad.append("%s: text open() without encoding" % f)
                if ("w" in mode or "a" in mode) and "newline" not in kw:
                    bad.append("%s: text write open() without newline" % f)
    return [(not bad, "Windows-safe constructs in the T1b files: %s" % (bad or "none found"))]


def u_generator_header():
    from merdian_compute.tape import minute
    return [(list(minute.COLS) == gen.COLS, "the generator's tape_minute.csv header equals minute.COLS (T1a's writer)")]


GUARDS = [("cyc-bins", g_cyc_bins), ("cyc-window", g_cyc_window), ("cyc-invariant", g_cyc_invariant),
          ("ev-conc-z", g_ev_conc_z), ("ev-thin", g_ev_thin), ("ev-onset", g_ev_onset),
          ("ch-e1-e2", g_ch_e1_e2), ("ch-merge", g_ch_merge), ("ch-e3-count-only", g_ch_e3),
          ("t1b-no-join", g_no_join), ("t1b-pure", g_pure), ("t1b-deterministic", g_deterministic),
          ("t1b-isolated", g_isolated), ("export-select-only", g_export_select_only)]
UNITS = [u_ts_ist, u_session_dir, u_int_z, u_windows_safe, u_generator_header]


def main():
    results = []
    for name, fn in [(n, f) for n, f in GUARDS if ARGS.only in (None, n)]:
        try:
            cells = fn()
            ok = bool(cells) and all(c[0] for c in cells)
        except Exception:
            cells = [(False, "EXCEPTION " + traceback.format_exc().strip().splitlines()[-1])]
            ok = False
        results.append((name, ok))
        print("%s %s" % ("PASS" if ok else "FAIL", name))
        for c in cells:
            print("    [%s] %s" % ("ok" if c[0] else "XX", c[1]))
    unit_ok = unit_n = 0
    if ARGS.only is None:
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
    g_ok = sum(1 for _, ok in results if ok)
    passed = bool(results) and g_ok == len(results) and unit_ok == unit_n
    print("TAPE T1B %s (%d/%d guards, %d/%d unit checks)" % ("PASS" if passed else "FAIL", g_ok, len(results), unit_ok, unit_n))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
