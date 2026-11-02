#!/usr/bin/env python3
"""Tape T1a guards (docs/tape/T1a_plan.md section 2). Offline: no network, no S3, no database.

  python3 tests/test_tape_t1a.py [--root DIR] [--only GUARD]

--root runs the guards against another copy of the tree (tests/tape_t1a_mutants.py uses it).
Refuses (exit 2) without an explicit `ulimit -v`, and Mon-Fri 08:30-15:45 IST (CLAUDE.md rule 23).
Last line: "TAPE T1A PASS (G/G guards, U/U unit checks)" or "TAPE T1A FAIL ...". Exit 0 / 1.
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
sys.path.insert(0, os.path.join(ROOT, "tests", "tape_t1a"))

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
        print("REFUSED: rule 23 - fixture tests blocked 08:30-15:45 IST on weekdays")
        return 2
    return 0


if rule23():
    sys.exit(2)

import gen_day as gen  # noqa: E402

DAY = gen.DAY
TMP = []
OUTS = ("tape_minute.csv", "g3_report.json", "g3_report.txt", "run_manifest.json")


def tmpdir():
    d = tempfile.mkdtemp(prefix="tape_t1a_")
    TMP.append(d)
    return d


def run(day_dir, out, extra=()):
    from services.tape_offline import process_day
    so, se = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(so), contextlib.redirect_stderr(se):
        rc = process_day.main([day_dir, "--day", DAY, "--out", out] + list(extra))
    return rc, so.getvalue(), se.getvalue()


def rd(out, name):
    with open(os.path.join(out, name), "rb") as fh:
        return fh.read()


def rows_of(out):
    return list(csv.DictReader(io.StringIO(rd(out, "tape_minute.csv").decode("utf-8"))))


def report_of(out):
    return json.loads(rd(out, "g3_report.json").decode("utf-8"))


_CACHE = {}


def default_run():
    """The default planted day, built and processed once per process."""
    if "d" not in _CACHE:
        d, out = tmpdir(), tmpdir()
        T = gen.build_day(d)
        rc, so, se = run(d, out)
        _CACHE["d"] = (d, out, T, rc, so, se)
    return _CACHE["d"]


# ====================================================================== guards
def g_planted_sides():
    d, out, T, rc, so, se = default_run()
    cells = [(rc == 0, "exit code %s (stderr tail: %s)" % (rc, se.strip()[-200:]))]
    rows = rows_of(out)
    got = {(int(r["token"]), r["minute"]): r for r in rows}
    exp = T.minute
    cells.append((set(got) == set(exp), "row keys: %d got, %d planted, symmetric difference %d"
                  % (len(got), len(exp), len(set(got) ^ set(exp)))))
    bad = []
    last_oi = {}
    for k in sorted(exp, key=lambda k: (k[0], k[1])):
        e, r = exp[k], got.get(k)
        if r is None:
            continue
        vw = e["pv"] / e["pq"] if e["pq"] else None
        oi_d = "" if k[0] not in last_oi else str(e["oi"] - last_oi[k[0]])
        last_oi[k[0]] = e["oi"]
        ok = ((int(r["buy_qty"]), int(r["sell_qty"]), int(r["uncl_qty"]), int(r["gap_qty"]), int(r["trades"]))
              == (e["B"], e["S"], e["U"], e["G"], e["trades"])
              and (r["vwap"] == "" if vw is None else abs(float(r["vwap"]) - vw) < 1e-5)
              and (int(r["bid_qty_5"]), int(r["ask_qty_5"]), int(r["oi"])) == (e["bq"], e["aq"], e["oi"])
              and r["oi_delta"] == oi_d and r["exch_ts_max"] == e["exts"])
        if not ok:
            bad.append((k, r, e))
    cells.append((not bad, "%d of %d (token, minute) rows differ from the planted truth%s"
                  % (len(bad), len(exp), "; first: %s" % (bad[0],) if bad else "")))
    rep = report_of(out)
    for sym in T.spec.syms:
        sr = rep["symbols"][sym]
        diff = []
        for (s, bk, grp), v in T.cells.items():
            if s != sym:
                continue
            c = sr["hours"].get(bk, {}).get(grp)
            g = [c["buy"], c["sell"], c["uncl"], c["gap"]] if c else [0, 0, 0, 0]
            if g != v:
                diff.append((bk, grp, g, v))
        extra = [(bk, grp) for bk, gs in sr["hours"].items() for grp, c in gs.items()
                 if (sym, bk, grp) not in T.cells and (c["buy"] or c["sell"] or c["uncl"] or c["gap"])]
        cells.append((not diff and not extra, "%s hour x group cells differ: %s; unplanted cells: %s"
                      % (sym, diff[:2] or "none", extra[:2] or "none")))
        rm = {r: [v["qty"], v["count"]] for r, v in sr["rule_mix"].items()}
        er = {r: v for (s, r), v in T.rules.items() if s == sym}
        cells.append((rm == er, "%s rule mix: %s vs planted %s" % (sym, rm, er)))
        cells.append((sorted(sr["tokens_no_packets"]) == sorted(T.nopkt[sym]),
                      "%s tokens with no packets %s vs %s" % (sym, sr["tokens_no_packets"], T.nopkt[sym])))
        cells.append((sr["baseline_qty"] == T.baseline[sym], "%s baseline_qty %s vs %s"
                      % (sym, sr["baseline_qty"], T.baseline[sym])))
    return cells


def g_invariant():
    d, out, T, rc, so, se = default_run()
    rep = report_of(out)
    cells = [(all(rep["symbols"][s]["invariants"]["ok"] for s in T.spec.syms) and rc == 0,
              "the run's own invariants all ok, exit %s" % rc)]
    per = {}
    for r in rows_of(out):
        a = per.setdefault(int(r["token"]), [0, 0, 0, 0])
        for i, c in enumerate(("buy_qty", "sell_qty", "uncl_qty", "gap_qty")):
            a[i] += int(r[c])
    exp = {}
    for (tok, mk), e in T.minute.items():
        a = exp.setdefault(tok, [0, 0, 0, 0])
        a[0] += e["B"]
        a[1] += e["S"]
        a[2] += e["U"]
        a[3] += e["G"]
    cells.append((per == exp, "per-token BUY/SELL/UNCL/GAP totals equal the planted totals (%d tokens, %d differ)"
                  % (len(exp), sum(1 for t in exp if per.get(t) != exp[t]))))
    badv = [t for t, a in per.items() if sum(a) != T.vol[t][1] - T.vol[t][0]]
    cells.append((not badv and per, "per token: B+S+U+G == cumulative volume last - first, generator's own volume "
                  "(%d tokens, %d differ)" % (len(per), len(badv))))
    return cells


def g_gap():
    d, out, T, rc, so, se = default_run()
    rows = {(int(r["token"]), r["minute"]): r for r in rows_of(out)}
    cells = []
    toks = [t for t, g in T.tok_group.items() if (t, "09:57") in T.minute and T.minute[(t, "09:57")]["G"] > 0]
    bad = [t for t in toks if int(rows[(t, "09:57")]["gap_qty"]) != T.minute[(t, "09:57")]["G"]
           or (int(rows[(t, "09:57")]["buy_qty"]), int(rows[(t, "09:57")]["sell_qty"]), int(rows[(t, "09:57")]["uncl_qty"]))
           != (T.minute[(t, "09:57")]["B"], T.minute[(t, "09:57")]["S"], T.minute[(t, "09:57")]["U"])]
    cells.append((len(toks) >= 30 and not bad, "%d tokens carry the planted reconnect jump; %d disagree "
                  "(jump in gap_qty, classified quantities unchanged)" % (len(toks), len(bad))))
    rep = report_of(out)
    t0 = gen.esec(DAY, "09:54:59")
    for sym in T.spec.syms:
        g = rep["symbols"][sym]["gaps"]
        ev = sorted((e["kind"], e["recv_ns"]) for e in g["events"])
        want = sorted(T.gap_events[sym] + [("connect", t0 * gen.NS - 3 * gen.NS)])
        cells.append((ev == want, "%s gap events %s" % (sym, [e[0] for e in ev])))
        cells.append((g["gap_pairs"] == T.gap_pairs[sym] and g["gap_qty"] == T.gap_qty[sym],
                      "%s gap_pairs %s/%s gap_qty %s/%s" % (sym, g["gap_pairs"], T.gap_pairs[sym],
                                                            g["gap_qty"], T.gap_qty[sym])))
    return cells


def _nodup(rep, sym):
    return {r: v for r, v in rep["symbols"][sym]["discards"].items() if r != "duplicate"}


LONG = dict(syms=("NIFTY",), events=False, n_strikes=3, t_start="09:44:59", t_end="10:14:59")


def _long_pair(**kw):
    """A 30-minute day (7 segment files): long enough that the 600 s reorder buffer RELEASES packets
    before the end of input, which the 10-minute default day never does."""
    a, b, oa, ob = tmpdir(), tmpdir(), tmpdir(), tmpdir()
    gen.build_day(a, gen.Spec(layout="segments", **dict(LONG, **kw)))
    gen.build_day(b, gen.Spec(layout="one_file", **dict(LONG, **kw)))
    return a, b, oa, ob, run(a, oa)[0], run(b, ob)[0]


def g_boundary():
    a, b, oa, ob = tmpdir(), tmpdir(), tmpdir(), tmpdir()
    Ta = gen.build_day(a, gen.Spec(layout="segments"))
    gen.build_day(b, gen.Spec(layout="one_file"))
    rca = run(a, oa)[0]
    rcb = run(b, ob)[0]
    ra, rb = report_of(oa), report_of(ob)
    cells = [(rca == 0 and rcb == 0, "exit codes %s / %s" % (rca, rcb)),
             (rd(oa, "tape_minute.csv") == rd(ob, "tape_minute.csv"),
              "tape_minute.csv byte-identical: segment-split day vs the same records in one segment"),
             (all(ra["symbols"][s]["hours"] == rb["symbols"][s]["hours"] and _nodup(ra, s) == _nodup(rb, s)
                  for s in Ta.spec.syms),
              "hour x group cells and every discard except `duplicate` identical in both layouts "
              "(the _r1 collision copies exist only in the split layout)")]
    bnd = [r for r in rows_of(oa) if r["minute"] in ("09:59", "10:00") and r["role"] == "OPT"]
    cells.append((len(bnd) > 20 and all(int(r["buy_qty"]) + int(r["sell_qty"]) > 0 for r in bnd),
                  "%d option rows around the 10:00 segment boundary all carry classified volume (not vacuous)"
                  % len(bnd)))
    a, b, oa, ob, rca, rcb = _long_pair()
    nseg = len([f for f in os.listdir(os.path.join(a, "NIFTY", DAY))])
    late = report_of(oa)["symbols"]["NIFTY"]["discards"]["late_beyond_watermark"]
    cells.append((rca == 0 and rcb == 0 and nseg >= 6 and rd(oa, "tape_minute.csv") == rd(ob, "tape_minute.csv")
                  and report_of(oa)["symbols"]["NIFTY"]["hours"] == report_of(ob)["symbols"]["NIFTY"]["hours"]
                  and not any(late.values()),
                  "%d-segment 30-minute day (packets released mid-run): csv and cells identical to the one-file "
                  "layout, nothing late beyond the watermark" % nseg))
    return cells


def g_order():
    from services.tape_offline import process_day
    a, b, oa, ob = tmpdir(), tmpdir(), tmpdir(), tmpdir()
    gen.build_day(a, gen.Spec())
    gen.build_day(b, gen.Spec(shuffle=7))
    run(a, oa)
    rcb = run(b, ob)[0]
    cells = [(rcb == 0 and all(rd(oa, n) == rd(ob, n) for n in OUTS[:3]),
              "lines shuffled inside every segment file -> csv, json and txt byte-identical")]
    meta, _conf = process_day.read_token_map(a, DAY)
    paths = process_day.list_symbol_files(a, "NIFTY", DAY)
    r1 = process_day.process_symbol("NIFTY", list(paths), DAY, meta)
    sh = list(paths)
    random.Random(3).shuffle(sh)
    r2 = process_day.process_symbol("NIFTY", sh, DAY, meta)
    r3 = process_day.process_symbol("NIFTY", list(reversed(paths)), DAY, meta)
    j = [json.dumps(r, sort_keys=True) for r in (r1, r2, r3)]
    cells.append((len(paths) == 4 and j[0] == j[1] == j[2],
                  "%d segment files fed in shuffled / reversed order give an identical result" % len(paths)))
    la, lb, oa2, ob2 = tmpdir(), tmpdir(), tmpdir(), tmpdir()
    gen.build_day(la, gen.Spec(**LONG))
    gen.build_day(lb, gen.Spec(shuffle=5, **LONG))
    run(la, oa2)
    rc = run(lb, ob2)[0]
    cells.append((rc == 0 and all(rd(oa2, n) == rd(ob2, n) for n in OUTS[:3]),
                  "30-minute day (packets released mid-run), lines shuffled -> csv, json and txt byte-identical"))
    return cells


def g_deterministic():
    a, oa, ob = tmpdir(), tmpdir(), tmpdir()
    gen.build_day(a, gen.Spec())
    a2 = os.path.join(tmpdir(), "copy")
    shutil.copytree(a, a2)
    rc1 = run(a, oa)[0]
    rc2 = run(a2, ob)[0]
    cells = [(rc1 == 0 and rc2 == 0, "exit codes %s / %s" % (rc1, rc2))]
    for n in OUTS:
        cells.append((rd(oa, n) == rd(ob, n), "%s byte-identical across two runs on two copies" % n))
    man = json.loads(rd(oa, "run_manifest.json").decode("utf-8"))
    bad = [n for n, h in man["outputs"].items() if hashlib.sha256(rd(oa, n)).hexdigest() != h]
    cells.append((set(man["outputs"]) == set(OUTS[:3]) and not bad, "run_manifest output sha256s match the files %s" % bad))
    badi = []
    for e in man["inputs"]:
        p = os.path.join(a, *e["path"].split("/"))
        if hashlib.sha256(open(p, "rb").read()).hexdigest() != e["sha256"]:
            badi.append(e["path"])
    cells.append((len(man["inputs"]) >= 9 and not badi, "run_manifest lists %d inputs, sha256 mismatches %s"
                  % (len(man["inputs"]), badi)))
    return cells


def g_g3_verdict():
    cases = [("80/80", 8, 8, "PASS"), ("50/70 boundary", 5, 7, "PASS"), ("40/80", 4, 8, "FAIL"),
             ("80/60", 8, 6, "FAIL"), ("60/60", 6, 6, "FAIL")]
    cells = []
    for name, ke, kl, want in cases:
        d, out = tmpdir(), tmpdir()
        gen.build_day(d, gen.Spec(syms=("NIFTY",), events=False, early=gen.share_cycle(ke),
                                  late=gen.share_cycle(kl), dv=[75]))
        rc = run(d, out)[0]
        sr = report_of(out)["symbols"]["NIFTY"]
        cells.append((rc == 0 and sr["verdict"] == want, "planted %s -> %s (want %s), exit %s, detail %s"
                      % (name, sr["verdict"], want, rc, sr["verdict_detail"])))
    d, out = tmpdir(), tmpdir()
    gen.build_day(d, gen.Spec(syms=("NIFTY",), events=False, t_start="09:59:57", t_end="10:00:03"))
    rc = run(d, out)[0]
    sr = report_of(out)["symbols"]["NIFTY"]
    cells.append((rc == 0 and sr["verdict"] == "NOT EVALUATED", "too little volume -> %s, exit %s" % (sr["verdict"], rc)))
    return cells


def _flip(path):
    b = bytearray(open(path, "rb").read())
    b[len(b) // 2] ^= 0x01
    open(path, "wb").write(bytes(b))


def g_manifest():
    cells = []
    sp = dict(syms=("NIFTY",), events=False, t_start="09:59:50", t_end="10:00:10")
    d, out = tmpdir(), tmpdir()
    gen.build_day(d, gen.Spec(**sp))
    rc, so, se = run(d, out, ["--verify-manifest"])
    cells.append((rc == 0 and all(os.path.exists(os.path.join(out, n)) for n in OUTS), "clean day verifies, exit %s" % rc))
    for what in ("flip", "missing", "unlisted"):
        d, out = tmpdir(), tmpdir()
        T = gen.build_day(d, gen.Spec(**sp))
        seg = sorted(f for f in T.files if "seg_" in f)[0]
        if what == "flip":
            _flip(seg)
        elif what == "missing":
            os.unlink(seg)
        else:
            shutil.copy(seg, os.path.join(os.path.dirname(seg), "seg_1030.ndjson.gz"))
        rc, so, se = run(d, out, ["--verify-manifest"])
        cells.append((rc == 3 and not any(os.path.exists(os.path.join(out, n)) for n in OUTS),
                      "%s: exit %s (want 3), no output files written" % (what, rc)))
    return cells


PURE_MODS = ("minute.py", "replay.py")
FORBID = {"time", "random", "socket", "ssl", "http", "urllib", "requests", "asyncio", "secrets", "uuid", "boto3",
          "botocore", "kiteconnect", "os", "sys", "subprocess", "shutil", "pathlib", "gzip", "io", "tempfile",
          "threading", "multiprocessing", "ftplib", "smtplib", "supabase", "psycopg2", "dhanhq"}


def g_pure():
    base = os.path.join(ROOT, "merdian_compute", "tape")
    bad = []
    for f in PURE_MODS:
        tree = ast.parse(open(os.path.join(base, f), encoding="utf-8").read())
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
    return [(not bad, "%d modules scanned; forbidden: %s" % (len(PURE_MODS), bad or "none"))]


OUTCOME_TOKENS = ("gex_", "strike_snapshots", "supabase", "outcome", "agreement", "lead_time", "ret_30m", "hist_",
                  "spot_bars", "range_by_group", "spot_outcome", "postgrest")


def tool_files():
    out = [os.path.join(ROOT, "merdian_compute", "tape", f) for f in PURE_MODS]
    d = os.path.join(ROOT, "services", "tape_offline")
    out += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".py")]
    return out


def g_no_outcomes():
    hits = []
    files = tool_files()
    for p in files:
        text = open(p, encoding="utf-8").read().lower()
        for t in OUTCOME_TOKENS:
            if t in text:
                hits.append("%s: %s" % (os.path.basename(p), t))
    return [(len(files) >= 4 and not hits, "%d tool files scanned for chain / scoring identifiers; hits: %s"
             % (len(files), hits or "none"))]


def _imports(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                yield a.name
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                yield "." * node.level + (node.module or "")
            else:
                yield node.module or ""
                for a in node.names:
                    yield (node.module or "") + "." + a.name


def g_isolated():
    cells = []
    rdir = os.path.join(ROOT, "services", "tape_runner")
    bad = []
    for f in sorted(os.listdir(rdir)):
        if f.endswith(".py"):
            for m in _imports(os.path.join(rdir, f)):
                if "tape_offline" in m or m.startswith("merdian_compute"):
                    bad.append("%s: %s" % (f, m))
    cells.append((not bad, "no services/tape_runner module imports tape_offline or merdian_compute: %s" % (bad or "none")))
    inst = open(os.path.join(rdir, "install.sh"), encoding="utf-8").read()
    m = re.search(r"archive HEAD ([^|]*?) \|", inst)
    cells.append((bool(m) and m.group(1).split() == ["services/__init__.py", "services/tape_runner"],
                  "install.sh archives only %s" % (m.group(1) if m else "?")))
    std = set(sys.stdlib_module_names)
    badi = []
    for p in tool_files():
        for mod in _imports(p):
            top = mod.split(".")[0]
            if not top or mod.startswith("."):
                continue
            if top in std or mod.startswith("merdian_compute.tape") or mod.startswith("services.tape_offline") \
                    or mod in ("merdian_compute", "services"):
                continue
            badi.append("%s: %s" % (os.path.basename(p), mod))
    cells.append((not badi, "tool imports are stdlib, merdian_compute.tape or services.tape_offline: %s" % (badi or "none")))
    return cells


def g_no_silent_drop():
    d, out, T, rc, so, se = default_run()
    rep = report_of(out)
    cells = []
    for sym in T.spec.syms:
        sr = rep["symbols"][sym]
        got = {(r, b): n for r, bs in sr["discards"].items() for b, n in bs.items() if n}
        want = {(r, b): n for (s, r, b), n in T.discards.items() if s == sym}
        cells.append((got == want, "%s discards by reason x hour equal the planted counts (%d cells, differ %s)"
                      % (sym, len(want), sorted(set(got.items()) ^ set(want.items()))[:3])))
        full = all(b in sr["discards"][r] for r in ("volume_regression", "stale_date") for b in
                   ("pre_0915", "0915_1000", "1000_1100", "1500_1530", "post_1530"))
        cells.append((full, "%s volume_regression and stale_date list every hour explicitly, zeros included" % sym))
        pk = sr["packets"]
        acc = pk["chain_pkts"] + pk["index_pkts"] + sum(n for (r, b), n in got.items() if r != "bad_line")
        cells.append((pk["pkt_lines"] == T.pkt_lines[sym] == acc and sr["invariants"]["packet_conservation_ok"],
                      "%s packet conservation: %s lines read = %s planted = %s accounted"
                      % (sym, pk["pkt_lines"], T.pkt_lines[sym], acc)))
    txt = rd(out, "g3_report.txt").decode("utf-8")
    cells.append((all(("  " + r) in txt for r in ("volume_regression", "stale_date")),
                  "g3_report.txt carries a row for volume_regression and for stale_date"))
    return cells


GUARDS = [("proc-planted-sides", g_planted_sides), ("proc-invariant", g_invariant), ("proc-gap", g_gap),
          ("proc-boundary", g_boundary), ("proc-order", g_order), ("proc-deterministic", g_deterministic),
          ("proc-g3-verdict", g_g3_verdict), ("proc-manifest", g_manifest), ("proc-pure", g_pure),
          ("proc-no-outcomes", g_no_outcomes), ("proc-isolated", g_isolated), ("proc-no-silent-drop", g_no_silent_drop)]


# ====================================================================== unit checks
def u_classify_minimal_parity():
    from merdian_compute.tape import classify, replay
    rnd = random.Random(11)
    bad = 0
    n = 3000

    def lvl(price):
        return [{"quantity": 5, "price": price, "orders": 1}] if price is not None else []

    def pkt(v, lp, atp, bid, ask):
        d = {"k": "pkt", "instrument_token": 1, "recv_ns": 1, "recv_ist": "2026-11-02T09:15:00+05:30",
             "exchange_timestamp": "2026-11-02T09:15:00+05:30", "volume_traded": v, "last_price": lp}
        if atp is not None:
            d["average_traded_price"] = atp
        if bid != "nodepth":
            d["depth"] = {"buy": lvl(bid), "sell": lvl(ask)}
        return d

    for _ in range(n):
        base = rnd.choice((100.0, 100.5, 0.0))
        bid = rnd.choice((99.5, 0.0, None, 101.0, "nodepth"))
        ask = rnd.choice((100.5, 0.0, None, 99.0))
        a = pkt(rnd.choice((100, 100.0, 150)), base, rnd.choice((None, 100.0, 99.0)), bid, ask)
        b = pkt(rnd.choice((100, 150, 175, 90)), rnd.choice((99.5, 100.0, 100.25, 100.5, 101.0, 0.0)),
                rnd.choice((None, 100.1)), rnd.choice((99.5, "nodepth")), rnd.choice((100.5,)))
        full = classify.classify(a, b)
        ka, pa = replay.parse_line(json.dumps(a).encode(), DAY)
        kb, pb = replay.parse_line(json.dumps(b).encode(), DAY)
        mini = classify.classify(replay.mini(pa), replay.mini(pb))
        bad += full != mini
    return [(bad == 0, "%d random packet pairs: classify(full) == classify(minimal dicts), %d differ" % (n, bad))]


def u_rule_parity_abort():
    from merdian_compute.tape import minute
    from services.tape_offline import process_day
    cells = []
    try:
        minute.check_rule("above_ask", "SELL")
        cells.append((False, "check_rule accepted a contradictory (rule, side)"))
    except minute.RuleParityError:
        cells.append((True, "check_rule raises RuleParityError on (above_ask, SELL)"))
    d, out = tmpdir(), tmpdir()
    gen.build_day(d, gen.Spec(syms=("NIFTY",), events=False, t_start="09:59:50", t_end="10:00:10"))
    real = minute.rule_of
    minute.rule_of = lambda prev, pkt: "above_ask" if real(prev, pkt) != "above_ask" else "below_bid"
    try:
        run(d, out)
        cells.append((False, "a wrong rule label did not abort the run"))
    except minute.RuleParityError:
        cells.append((True, "a wrong rule label aborts the run (RuleParityError)"))
    finally:
        minute.rule_of = real
    return cells


def u_segment_name_order():
    from merdian_compute.tape import replay
    names = ["seg_0925.ndjson.gz", "seg_0920_c1_r1.ndjson.gz", "seg_0920_r1.ndjson.gz", "seg_0920.ndjson.gz",
             "seg_0920_c1.ndjson.gz", "seg_0920_r2.ndjson.gz"]
    got = replay.order_segments(names)
    want = ["seg_0920.ndjson.gz", "seg_0920_r1.ndjson.gz", "seg_0920_r2.ndjson.gz", "seg_0920_c1.ndjson.gz",
            "seg_0920_c1_r1.ndjson.gz", "seg_0925.ndjson.gz"]
    return [(got == want, "collision names ordered by (HHMM, c, r): %s" % got),
            (replay.parse_seg_name("seg_0920.ndjson.gz.tmp") is None and replay.parse_seg_name("x.gz") is None,
             "non-segment names are not segments")]


def u_bucket_of():
    from merdian_compute.tape import minute
    want = {"09:14": "pre_0915", "09:15": "0915_1000", "09:59": "0915_1000", "10:00": "1000_1100",
            "14:59": "1400_1500", "15:00": "1500_1530", "15:29": "1500_1530", "15:30": "post_1530", "": "unknown"}
    got = {k: minute.bucket_of(k) for k in want}
    return [(got == want, "bucket boundaries: %s" % {k: v for k, v in got.items() if want[k] != v} or "ok")]


def u_token_map():
    from merdian_compute.tape import replay
    a = {"tokens": [{"token": 1, "sym": "NIFTY", "role": "OPT", "strike": 1.0, "opt_type": "CE", "tradingsymbol": "A",
                     "expiry": "2026-11-05"}]}
    b = {"tokens": [{"token": 1, "sym": "NIFTY", "role": "OPT", "strike": 1.0, "opt_type": "CE", "tradingsymbol": "A",
                     "expiry": "2026-11-05"},
                    {"token": 2, "sym": "NIFTY", "role": "FUT", "strike": None, "opt_type": None,
                     "tradingsymbol": "F", "expiry": "2026-11-26"}]}
    c = {"tokens": [{"token": 1, "sym": "NIFTY", "role": "OPT", "strike": 2.0, "opt_type": "CE", "tradingsymbol": "A",
                     "expiry": "2026-11-05"}]}
    meta, conf = replay.build_token_map([("subscriptions_100300.json", b), ("subscriptions_094500.json", a),
                                         ("subscriptions_094500_2.json", c)])
    return [(sorted(meta) == [1, 2] and meta[1]["strike"] == 1.0, "first file fixes a token's metadata: %s" % meta.get(1)),
            (len(conf) == 1 and conf[0]["token"] == 1, "a later differing record is reported, not applied: %s" % conf)]


def u_windows_safe():
    bad = []
    for p in tool_files():
        tree = ast.parse(open(p, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for m in _imports_of(node):
                    if m.split(".")[0] in ("resource", "fcntl", "termios", "pwd", "grp", "signal", "pty"):
                        bad.append("%s: import %s" % (os.path.basename(p), m))
            elif isinstance(node, ast.Attribute) and node.attr in ("fork", "getuid", "geteuid", "chown", "fchmod", "mkfifo"):
                bad.append("%s: .%s" % (os.path.basename(p), node.attr))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
                kw = {k.arg: k.value for k in node.keywords}
                mode = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else \
                    (kw["mode"].value if "mode" in kw and isinstance(kw["mode"], ast.Constant) else "r")
                if "b" in mode:
                    continue
                if "encoding" not in kw:
                    bad.append("%s: text open() without encoding" % os.path.basename(p))
                if ("w" in mode or "a" in mode) and "newline" not in kw:
                    bad.append("%s: text write open() without newline" % os.path.basename(p))
    return [(not bad, "Windows-safe constructs: %s" % (bad or "none found"))]


def _imports_of(node):
    if isinstance(node, ast.Import):
        return [a.name for a in node.names]
    return [node.module or ""]


UNITS = [u_classify_minimal_parity, u_rule_parity_abort, u_segment_name_order, u_bucket_of, u_token_map, u_windows_safe]


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
    passed = results and g_ok == len(results) and unit_ok == unit_n
    print("TAPE T1A %s (%d/%d guards, %d/%d unit checks)" % ("PASS" if passed else "FAIL", g_ok, len(results),
                                                            unit_ok, unit_n))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
