#!/usr/bin/env python3
"""Tape live L2 runner, Phase A real-day gate (docs/tape/L2_live_runner_plan.md sections 9 and 12). NOT a run_offline.sh step.

  python tests/tape_live_runner_equal.py --data C:\\tape_data --work <dir> --day 2026-11-06 --variant clean|late|ooo [--keep] [--write none|fake|count] [--slice-from HH:MM]

--write fake (stage 2b): the runner is run with --db-write against the guard suite's FakeTable (no database, no DSN) and
tests/tape_live_write_checks.write_checks() adds W0 to W4 (rows sent, FakeTable == U-only files at every script, no duplicate conflict
key, no write skip or stop). The writer's db_withheld.csv is counted and reported, not compared. The default is --write none.

--write count (stage 2b memory measurement): as fake, but RUN is the CountShell (tests/tape_live_write_checks.py), which answers the
writer and keeps nothing per row, so the runner's peak_ws_mb is the writer's and not the harness's. Asserted: everything flag-off
asserts, plus count_checks (C0, C1 counts, W4). W1-W3 are not run in this mode. The memory verdict is
tests/tape_live_peak_compare.py --bound-mb B_day (the +100 MB margin does not apply to a count log).

--slice-from HH:MM (needs --write fake): a SMOKE of the flag-on path on a real day, not the gate. No replay, no byte comparison, no db_checks,
no flag-off run, no memory criterion: the runner alone is started at HH:MM (its first cycle builds the whole day, the writer sends from that
cycle on) against the FakeTable, and only W0 to W4 are asserted. The peak working set is printed for information. A slice PASS is W0 to W4
on that slice and is NOT a gate PASS; the three full runs stay the gate. Exit 0 PASS, 1 FAIL.

One (day, variant) per process, so the runs can be started side by side. For the recorded day under <data>/<day> (+ chain export
under <data>/chain_<day>) it runs
  1. cli replay (the L0 path, with the variant's arrival map), and
  2. the runner (cli live --source local --chain local --clock sim): the same recorded files, appearing on a schedule,
and requires every output file byte-equal (both shapes, epoch ids included, plan section 4), except run_manifest.json,
whose rebuild / late / bad-file / conflict / label-count / epoch fields are compared. It also requires
the runner's final cycle and events to equal the offline cyc_<day>/tape_strike_cycle.csv and tape_events.csv byte for byte.
Control: the comparison is run once on a copy with one byte changed and must report a difference; if it does not, the gate FAILS.
Phase B (plan section 4): also (i) the newest epoch of the runner's DB-shaped cycle / events state equals the offline cyc_<day>
rendered through dbshape; (ii) at EVERY cycle, the DB deltas applied with U lines only (D a no-op, the 2b writer) and then the
newest-run filter equal the deltas applied with D. Reported, not gating: the grid point of the slowest cycle with its rebuild /
db / s3 / re-emit figures, the epoch bumps per symbol and trigger with the rows each re-sent, and a FLAG when a bump cycle passes the
item 7a test of ruling R9-B, computed with services/tape_live/dbwrite.py's own constants (r9b_flag). live_metrics.csv is kept as <work>/<day>_<variant>_metrics.csv.
Variants: clean (no arrival map); late (NIFTY seg_1100 arrives 11:10); ooo (NIFTY seg_1200 arrives 12:20, after two later ones).
Read-only on --data. Writes only under --work (deleted at the end unless --keep). Exit 0 PASS, 1 FAIL, 2 refused / bad input.
Rule 23 window as tests/test_tape_live.py (Local override TAPE_RULE23_OVERRIDE_R1=1, ruling R-1).
"""
import argparse
import contextlib
import csv
import functools
import hashlib
import io
import json
import os
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone

csv.field_size_limit(1 << 24)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
IST = timezone(timedelta(hours=5, minutes=30))
print = functools.partial(print, flush=True)  # noqa: A001 - a stopped run must still leave its lines in the log
ARRIVAL = {"clean": {}, "late": {"NIFTY/seg_1100.ndjson.gz": "11:10"}, "ooo": {"NIFTY/seg_1200.ndjson.gz": "12:20"},
           # fixture only (tests/tape_live/gen_live.py EPOCH_ARRIVAL): the epoch day's two late segments (smoke test of Phase B)
           "epoch": {"NIFTY/seg_1330.ndjson.gz": "13:50", "SENSEX/seg_1030.ndjson.gz": "10:50"}}


def refused():
    now = datetime.now(IST)
    if now.weekday() < 5 and 830 <= now.hour * 100 + now.minute < 1545:
        if os.environ.get("TAPE_RULE23_OVERRIDE_R1") == "1":
            print("RULE23 WINDOW LIFTED by operator ruling R-1 (2026-11-03): Local machine, not the retail box")
            return False
        print("REFUSED: rule 23 window (Local: set TAPE_RULE23_OVERRIDE_R1=1 under ruling R-1)")
        return True
    return False


def rd(p):
    with open(p, "rb") as fh:
        return fh.read()


def files_of(d):
    return sorted(os.path.relpath(os.path.join(dp, n), d).replace(os.sep, "/") for dp, _, ns in os.walk(d) for n in ns)


def compare_dirs(cdir, ldir):
    """-> list of differences between the cli replay out dir and the runner's live dir."""
    bad = []
    fa = [x for x in files_of(cdir) if x != "run_manifest.json"]
    fb = [x for x in files_of(ldir) if x != "run_manifest.json"]
    if fa != fb:
        bad.append("file sets differ: only cli %s, only runner %s" % (sorted(set(fa) - set(fb))[:5], sorted(set(fb) - set(fa))[:5]))
    for rel in sorted(set(fa) & set(fb)):
        x, y = rd(os.path.join(cdir, rel)), rd(os.path.join(ldir, rel))
        if x != y:
            bad.append("differs: " + rel)
    with open(os.path.join(cdir, "run_manifest.json"), encoding="utf-8") as fh:
        ma = json.load(fh)
    with open(os.path.join(ldir, "run_manifest.json"), encoding="utf-8") as fh:
        mb = json.load(fh)
    for k in ("rebuilds", "late_segments", "bad_files", "token_map_conflicts", "label_counts", "rule_version", "epochs",
              "epoch_log"):
        if k not in ma or ma.get(k) != mb.get(k):
            bad.append("manifest %s: cli %r runner %r" % (k, ma.get(k), mb.get(k)))
    return bad, len(fa), ma


def _db_rows(path):
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    return rows[0], rows[1:]


def _newest(state):
    """Ruling R6-H: state {table: (header, rows)}; per (trading_day, symbol) one newest id, that of the row with the latest as_of
    across the three tables together; keep only its rows in each. Also returns the ties: keys whose rows at the latest as_of
    carry more than one id. -> ({table: rows}, {key: ids})."""
    top = {}
    for t, (h, rows) in state.items():
        i_d, i_s, i_a, i_r = (h.index(c) for c in ("trading_day", "symbol", "as_of", "live_run_id"))
        for r in rows:
            k = (r[i_d], r[i_s])
            if k not in top or r[i_a] > top[k][0]:
                top[k] = [r[i_a], r[i_r], {r[i_r]}]
            elif r[i_a] == top[k][0]:
                top[k][2].add(r[i_r])
    out = {}
    for t, (h, rows) in state.items():
        i_d, i_s, i_r = (h.index(c) for c in ("trading_day", "symbol", "live_run_id"))
        out[t] = [r for r in rows if r[i_r] == top[(r[i_d], r[i_s])][1]]
    return out, dict((k, v[2]) for k, v in top.items() if len(v[2]) > 1)


def db_checks(ldir, cyc, day):
    """(i) newest epoch == batch through dbshape; (ii) U-only + newest view == D applied at every cycle. -> list of failures."""
    from services.tape_live import dbshape
    bad = []
    keys = {"tape_live_cycle": ("symbol", "instrument_token", "ts_ist"),
            "tape_live_events": ("symbol", "expiry", "strike", "leg", "kind", "ts_ist", "side"),
            "tape_live_wall": ("symbol", "expiry", "ts_ist")}
    end = dict((t, _db_rows(os.path.join(ldir, t + ".db.csv"))) for t in keys)
    end_view, ties = _newest(end)
    if ties:
        bad.append("tie at the day-end latest as_of: %s" % sorted((k, sorted(v)) for k, v in ties.items())[:2])
    for t, src in (("tape_live_cycle", "tape_strike_cycle.csv"), ("tape_live_events", "tape_events.csv")):
        nd = len(end[t][0]) - 3
        live = sorted(r[:nd] for r in end_view[t])
        with open(os.path.join(cyc, src), encoding="utf-8", newline="") as fh:
            batch = sorted(dbshape.data_row(t, day, r) for r in list(csv.reader(fh))[1:])
        if live != batch:
            bad.append("(i) %s newest epoch (%d rows) != batch through dbshape (%d rows)" % (t, len(live), len(batch)))
    cdir = os.path.join(ldir, "cycles")
    names = sorted(n[:4] for n in os.listdir(cdir) if n.endswith(".db.csv") and n[:4] != "fina")
    names = sorted(set(names)) + ["final"]
    full = dict((t, {}) for t in keys)
    uo = dict((t, {}) for t in keys)
    n_pts = 0
    for name in names:
        for t, part in (("tape_live_cycle", "cycle"), ("tape_live_events", "events"), ("tape_live_wall", "wall")):
            p = os.path.join(cdir, "%s_%s.db.csv" % (name, part))
            if os.path.exists(p):
                h, rows = _db_rows(p)
                idx = [h.index(c) for c in keys[t]]
                for r in rows:
                    k = tuple(r[i] for i in idx)
                    if r[0] == "U":
                        full[t][k] = r[1:]
                        uo[t][k] = r[1:]
                    else:
                        full[t].pop(k, None)
        view, ties = _newest(dict((t, (dbshape.header(t).split(","), list(uo[t].values()))) for t in keys))
        if ties:
            bad.append("tie at cycle %s: %s" % (name, sorted((k, sorted(v)) for k, v in ties.items())[:2]))
        for t in keys:
            if sorted(view[t]) != sorted(full[t].values()):
                bad.append("(ii) cycle %s %s: U-only + newest view != D applied" % (name, t))
            n_pts += 1
    print("GATE: DB checks: newest epoch vs batch (cycle, events); U-only == D-applied at %d (cycle, table) points" % n_pts)
    return bad


def tie_selftest():
    """The tie check must be able to fire: a planted state with two wall rows of one (trading_day, symbol) at the same latest
    as_of under two ids. -> True if _newest reports it."""
    h = ["symbol", "trading_day", "ts_ist", "as_of", "live_run_id"]
    rows = [["NIFTY", "2026-11-06", "2026-11-06T10:00:00+05:30", "2026-11-06T05:00:00+00:00", "id-a"],
            ["NIFTY", "2026-11-06", "2026-11-06T10:05:00+05:30", "2026-11-06T05:00:00+00:00", "id-b"]]
    _view, ties = _newest({"tape_live_wall": (h, rows)})
    return ties == {("2026-11-06", "NIFTY"): {"id-a", "id-b"}}


def tree_hash(root):
    """40-hex content hash of a code tree: sha1 over the sorted lines 'relpath NUL sha256 LF' of every file, skipping .git,
    __pycache__ and the root's own CODE_SHA. The one implementation; _l2_logs/2b_code_sha.py imports it to write CODE_SHA."""
    lines = []
    for dp, dns, ns in os.walk(root):
        dns[:] = [x for x in dns if x not in (".git", "__pycache__")]
        for n in ns:
            p = os.path.join(dp, n)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            if rel == "CODE_SHA":
                continue
            lines.append("%s\0%s\n" % (rel, hashlib.sha256(rd(p)).hexdigest()))
    return hashlib.sha1("".join(sorted(lines)).encode("utf-8")).hexdigest()


def resolve_sha(cli):
    """One code sha for the whole gate, read with the REAL cli.code_info (call before load_ttl() pins TEST_SHA).
    -> (sha, dirty, note) or (None, None, reason)."""
    import re
    info = cli.code_info()
    sha = cli._code_sha()                                   # git HEAD, else the CODE_SHA file at the code root
    if sha == "unknown" or not re.match(r"^[0-9a-f]{7,40}$", sha):
        return None, None, "no code sha (git or CODE_SHA file)"
    if info["git_sha"] != "unknown":
        return sha, info["dirty"], "code sha %s from git HEAD, tree dirty=%s" % (sha, info["dirty"])
    if sha == tree_hash(ROOT):
        return sha, None, "PRE-COMMIT GATE: code sha %s is the content hash of this tree (CODE_SHA), not a commit" % sha
    return sha, None, "code sha %s from CODE_SHA file, not this tree's content hash: taken as a commit sha, not verified" % sha


def r9b_flag(ms, at, trigger):
    """Reported, not gating: the item 7a test of ruling R9-B, with dbwrite's own constants, on the bump cycle at `at` (an int
    minute; 'final' never qualifies). Window: wall_s of the metrics rows from FROM_T_7A up to and including `at`."""
    import statistics
    from services.tape_live import dbwrite
    mins = dict((int(r["T"][:2]) * 60 + int(r["T"][3:5]), float(r["wall_s"])) for r in ms if r["T"] != "final")
    if not isinstance(at, int) or at not in mins:
        return ""
    win = [w for m, w in sorted(mins.items()) if dbwrite.FROM_T_7A <= m <= at]
    if len(win) < dbwrite.MIN_CYCLES_7A:
        return ""
    med = statistics.median(win)
    excess = mins[at] - med
    if not (excess > dbwrite.REL_EXCESS_7A * med and excess > dbwrite.MIN_EXCESS_S_7A):
        return ""
    if trigger in dbwrite.REBUILD_TRIGGERS:
        return "  FLAG: above the R9-B 7a test (window median %.3f, n %d), but a rebuild bump: 7a does not apply" % (med, len(win))
    return "  FLAG: R9-B item 7a stops the writer here (window median %.3f, n %d, excess %.3f s)" % (med, len(win), excess)


SHA_TABLES = ("tape_live_cycle", "tape_live_events", "tape_live_wall", "tape_live_label")


def _shas(d):
    """The distinct code_sha values of the four day-end .db.csv files in d (a missing file adds '<missing name>')."""
    out = set()
    for t in SHA_TABLES:
        p = os.path.join(d, t + ".db.csv")
        if not os.path.exists(p):
            out.add("<missing %s.db.csv>" % t)
            continue
        h, rows = _db_rows(p)
        i = h.index("code_sha")
        out.update(r[i] for r in rows)
    return out


def sha_check(rdir, ldir, want=None):
    """Named check: replay and runner must carry one and the same code_sha (and, when given, the sha this gate resolved).
    -> [] or ["sha mismatch: ..."]. It fails on a replay stamped 'unknown' beside a runner stamped with the test pin."""
    a, b = _shas(rdir), _shas(ldir)
    if len(a) == 1 and a == b and (want is None or a == {want}):
        return []
    return ["sha mismatch: replay %s runner %s%s" % (sorted(a), sorted(b), "" if want is None else " want %s" % want)]


def sha_selftest():
    """The sha check must be able to fire: a planted pair with different shas must be reported, an equal pair must not."""
    import tempfile
    root = tempfile.mkdtemp(prefix="sha_selftest_")
    try:
        def plant(name, sha):
            d = os.path.join(root, name)
            os.makedirs(d)
            for t in SHA_TABLES:
                with open(os.path.join(d, t + ".db.csv"), "w", encoding="utf-8", newline="\n") as fh:
                    fh.write("symbol,code_sha\nNIFTY,%s\n" % sha)
            return d
        r, x, y = plant("r", "aaaaaaa"), plant("x", "bbbbbbb"), plant("y", "aaaaaaa")
        fired = sha_check(r, x) != [] and sha_check(r, x)[0].startswith("sha mismatch")
        quiet = sha_check(r, y) == [] and sha_check(r, y, "aaaaaaa") == [] and sha_check(r, y, "ccccccc") != []
        return fired and quiet
    finally:
        shutil.rmtree(root, ignore_errors=True)


def slice_main(a):
    """--slice-from: the runner alone from a.slice_from against the FakeTable; W0 to W4 only (see the module docstring)."""
    raw = os.path.join(a.data, a.day)
    chain = [os.path.join(a.data, "chain_" + a.day, "gex_strike_snapshots_%s.csv" % s) for s in ("NIFTY", "SENSEX")]
    for p in [raw] + chain:
        if not os.path.exists(p):
            print("missing input %s" % p)
            return 2
    from services.tape_offline.cycle_day import peak_mb
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import tape_live_write_checks as W
    T = W.load_ttl()
    tag = "%s_%s_slice%s" % (a.day, a.variant, a.slice_from.replace(":", ""))
    work = os.path.join(a.work, tag)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    arr = os.path.join(work, "arrival.json")
    with open(arr, "w", encoding="utf-8") as fh:
        json.dump(ARRIVAL[a.variant], fh)
    print("SLICE %s: runner from %s, fake writer, no replay ..." % (tag, a.slice_from))
    res, fails, info = W.slice_run(T, a.day, os.path.join(work, "runner"), raw, chain, a.slice_from,
                                   arrival=arr if ARRIVAL[a.variant] else None)
    print("SLICE %s: runner rc=%s %.0f s peak_ws_mb=%s (information only: no memory criterion on a slice)" % (tag, res.rc, info["secs"], peak_mb()))
    print("SLICE %s: write fake: %d scripts, rows sent %s, withheld (grain_uq, reported) %d, W0-W4 %s" % (
        tag, info["scripts"], json.dumps(info["sent"], sort_keys=True), info["withheld"], "PASS" if not fails else "FAIL %d" % len(fails)))
    if res.rc == 0:
        ms = T.w_metrics(res)
        top = max(ms, key=lambda r: float(r["wall_s"]))
        print("SLICE %s: %d cycles; first cycle T=%s wall_s %s; slowest T=%s wall_s %s" % (
            tag, len(ms), ms[0]["T"], ms[0]["wall_s"], top["T"], top["wall_s"]))
    for k, f in enumerate(fails, 1):                   # every failure, one per line (the verdict line keeps its first six)
        print("SLICE %s failure %d/%d: %s" % (tag, k, len(fails), f))
    print("SLICE %s W0-W4 %s%s  (a slice PASS is W0-W4 only, NOT a gate PASS)" % (
        tag, "PASS" if not fails else "FAIL", "" if not fails else ": " + "; ".join(fails[:6])))
    if not a.keep:
        shutil.rmtree(work, ignore_errors=True)
    return 0 if not fails else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--day", required=True)
    ap.add_argument("--variant", choices=sorted(ARRIVAL), required=True)
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--write", choices=("none", "fake", "count"), default="none",
                    help="fake: the runner also runs --db-write against the guard suite's FakeTable (tests/tape_live_write_checks.py); "
                         "count: against the CountShell, which keeps nothing per row (the memory measurement)")
    ap.add_argument("--slice-from", default=None, metavar="HH:MM",
                    help="smoke: runner only from HH:MM against the FakeTable, W0 to W4 only (needs --write fake); NOT a gate PASS")
    a = ap.parse_args()
    if a.slice_from is not None:
        try:
            hh, mm = (int(x) for x in a.slice_from.split(":"))
            ok_t = 0 <= hh < 24 and 0 <= mm < 60 and len(a.slice_from) == 5
        except ValueError:
            ok_t = False
        if not ok_t or a.write != "fake":
            print("--slice-from needs HH:MM and --write fake")
            return 2
    if refused():
        return 2
    if a.slice_from is not None:
        return slice_main(a)
    if not tie_selftest():
        print("TIE SELFTEST did NOT fire: the tie check cannot fail; gate FAIL")
        return 1
    print("TIE SELFTEST fired")
    if not sha_selftest():
        print("SHA SELFTEST did NOT fire: the sha check cannot fail; gate FAIL")
        return 1
    print("SHA SELFTEST fired")
    raw = os.path.join(a.data, a.day)
    chain = [os.path.join(a.data, "chain_" + a.day, "gex_strike_snapshots_%s.csv" % s) for s in ("NIFTY", "SENSEX")]
    cyc = os.path.join(a.data, "cyc_" + a.day)
    for p in [raw] + chain + [os.path.join(cyc, "tape_strike_cycle.csv"), os.path.join(cyc, "tape_events.csv")]:
        if not os.path.exists(p):
            print("missing input %s" % p)
            return 2
    from services.tape_live import cli
    from services.tape_offline.cycle_day import peak_mb
    tag = "%s_%s" % (a.day, a.variant)
    # one code sha for replay and runner, both modes: read with the REAL code_info, before load_ttl() pins TEST_SHA
    sha, dirty, note = resolve_sha(cli)
    if sha is None:
        print("REFUSED: %s" % note)
        return 2
    W = T = None
    if a.write in ("fake", "count"):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import tape_live_write_checks as W
        T = W.load_ttl()                                   # pins cli.code_info to TEST_SHA at import ...
        if T.mods()[0] is not cli:
            print("REFUSED: the write checks' cli module is not the gate's (the sha pin would miss the runner)")
            return 2
    cli.code_info = lambda: {"git_sha": sha, "dirty": dirty}   # ... which this overrides, for the rest of the process
    print("GATE %s: %s" % (tag, note))
    work = os.path.join(a.work, tag)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    arr = os.path.join(work, "arrival.json")
    with open(arr, "w", encoding="utf-8") as fh:
        json.dump(ARRIVAL[a.variant], fh)
    t0 = time.time()
    print("GATE %s: cli replay ..." % tag)
    rdir = os.path.join(work, "replay")
    argv = ["replay", "--day", a.day, "--raw", raw, "--out", rdir]
    for p in chain:
        argv += ["--chain-runs", p]
    if ARRIVAL[a.variant]:
        argv += ["--arrival", arr]
    with contextlib.redirect_stderr(io.StringIO()):
        rc1 = cli.main(argv)
    t1 = time.time()
    print("GATE %s: replay rc=%s %.0f s peak_ws_mb=%s" % (tag, rc1, t1 - t0, peak_mb()))
    print("GATE %s: runner (sim clock) ..." % tag)
    odir = os.path.join(work, "runner")
    argv = ["live", "--day", a.day, "--out", odir, "--source", "local", "--raw", raw, "--chain", "local", "--clock", "sim",
            "--start", "08:50", "--disk-floor-mb", "20", "--rss-cap-mb", "3000"]
    for p in chain:
        argv += ["--chain-csv", p]
    if ARRIVAL[a.variant]:
        argv += ["--arrival", arr]
    wres = None
    if a.write == "fake":
        # the same runner argv (tests/tape_live_write_checks.run_live_fake builds it), with --db-write and RUN replaced by the fake
        wres = W.run_live_fake(T, a.day, odir, raw, chain, "08:50", arrival=arr if ARRIVAL[a.variant] else None)
        rc2 = wres.rc
        if rc2 != 0:
            print("GATE %s: runner (fake writer) log tail: %s" % (tag, wres.log.strip()[-300:]))
    elif a.write == "count":
        # the same runner argv, with --db-write and RUN replaced by the CountShell (no FakeTable, no recorded scripts)
        wres = W.run_live_count(T, a.day, odir, raw, chain, "08:50", arrival=arr if ARRIVAL[a.variant] else None)
        rc2 = wres.rc
        if rc2 != 0:
            print("GATE %s: runner (count writer) log tail: %s" % (tag, wres.log.strip()[-300:]))
    else:
        rc2 = cli.main(argv)
    t2 = time.time()
    print("GATE %s: runner rc=%s %.0f s peak_ws_mb=%s" % (tag, rc2, t2 - t1, peak_mb()))
    fails = []
    if rc1 != 0 or rc2 != 0:
        fails.append("rc replay=%s runner=%s" % (rc1, rc2))
    else:
        ldir = os.path.join(odir, a.day, "live")
        withheld = 0
        if wres is not None:                               # the writer's own reports are not part of the byte comparison
            for n in ("db_withheld.csv", "db_dupkeys.csv"):
                p = os.path.join(ldir, n)
                if os.path.exists(p):
                    if n == "db_withheld.csv":
                        withheld = max(0, rd(p).count(b"\n") - 1)
                    else:
                        fails.append("db_dupkeys.csv exists: the writer found a duplicate conflict key")
                    shutil.move(p, os.path.join(work, "%s_%s" % (tag, n)))
        fails[:0] = sha_check(rdir, ldir, sha)             # first, so the six-item verdict line always carries it
        diff, nfiles, man = compare_dirs(rdir, ldir)
        fails += diff
        for n, src in (("tape_live_cycle.csv", "tape_strike_cycle.csv"), ("tape_live_events.csv", "tape_events.csv")):
            if rd(os.path.join(ldir, n)) != rd(os.path.join(cyc, src)):
                fails.append("%s != offline %s" % (n, src))
        # control: one byte changed in a copy of the runner's cycle file must be reported
        ctl = os.path.join(work, "ctl")
        shutil.copytree(ldir, ctl)
        p = os.path.join(ctl, "tape_live_cycle.csv")
        b = bytearray(rd(p))
        b[len(b) // 2] = (b[len(b) // 2] + 1) % 256
        with open(p, "wb") as fh:
            fh.write(bytes(b))
        if not compare_dirs(rdir, ctl)[0]:
            fails.append("CONTROL FAILED: a changed byte was not reported (the comparison cannot fail)")
        n_c = rd(os.path.join(ldir, "tape_live_cycle.csv")).count(b"\n") - 1
        n_e = rd(os.path.join(ldir, "tape_live_events.csv")).count(b"\n") - 1
        with open(os.path.join(odir, a.day, "state.json"), encoding="utf-8") as fh:
            st = json.load(fh)
        with open(os.path.join(odir, a.day, "heartbeat.json"), encoding="utf-8") as fh:
            hb = json.load(fh)
        print("GATE %s: %d files compared, cycle rows %d, event rows %d, runner state=%s missed=%d" % (
            tag, nfiles, n_c, n_e, hb["state"], len(st.get("missed", []))))
        print("GATE %s: rebuilds %s" % (tag, json.dumps([(r["trigger"], r["at"], r["symbol"]) for r in man["rebuilds"]])))
        print("GATE %s: late segments %s; label counts %s" % (
            tag, [x["symbol"] + "/" + x["segment"] for x in man["late_segments"]], json.dumps(man["label_counts"], sort_keys=True)))
        with open(os.path.join(odir, a.day, "live_metrics.csv"), encoding="utf-8", newline="") as fh:
            ms = list(csv.DictReader(fh))
        walls = sorted(float(r["wall_s"]) for r in ms)
        med = walls[len(walls) // 2]
        print("GATE %s: %d runner cycles, wall_s median %.2f max %.2f" % (tag, len(ms), med, walls[-1]))
        top = max(ms, key=lambda r: float(r["wall_s"]))
        print("GATE %s: slowest cycle T=%s wall_s %s rebuild_s %s db_s %s s3_list_s %s chain_wait_s %s reemit_rows %s rebuilds %s" % (
            tag, top["T"], top["wall_s"], top["rebuild_s"], top["db_s"], top["s3_list_s"], top["chain_wait_s"],
            top["reemit_rows"], top["rebuilds"]))
        shutil.copyfile(os.path.join(odir, a.day, "live_metrics.csv"), os.path.join(a.work, "%s_metrics.csv" % tag))
        by_t = dict((r["T"], r) for r in ms)
        for e in man["epoch_log"]:
            at = e["at"]
            hm = "final" if at == "final" else "%02d:%02d" % (at // 60, at % 60)
            r = by_t.get(hm)
            print("GATE %s: epoch %s n=%d trigger=%s at=%s reemit_rows=%d cycle wall_s=%s rebuild_s=%s%s" % (
                tag, e["symbol"], e["n"], e["trigger"], hm, e["reemit_rows"], "-" if r is None else r["wall_s"],
                "-" if r is None else r["rebuild_s"], r9b_flag(ms, at, e["trigger"])))
        cnt = {}
        for e in man["epoch_log"]:
            cnt.setdefault(e["symbol"], {}).setdefault(e["trigger"], 0)
            cnt[e["symbol"]][e["trigger"]] += 1
        print("GATE %s: epochs per symbol/trigger %s; re-sent rows total %d" % (
            tag, json.dumps(cnt, sort_keys=True), sum(e["reemit_rows"] for e in man["epoch_log"])))
        fails += db_checks(ldir, cyc, a.day)
        if wres is not None and a.write == "count":
            wf = W.count_checks(T, wres, a.day)
            fails += wf
            tot = dict((t, sum(r[2][i] for r in wres.fake.records)) for i, t in enumerate(T.DB_TABLES))
            print("GATE %s: write count: %d scripts, rows sent %s, withheld (grain_uq, reported) %d, count checks %s; shell deep size %.1f KB" % (
                tag, len(wres.fake.records), json.dumps(tot, sort_keys=True), withheld, "PASS" if not wf else "FAIL %d" % len(wf),
                W.deep_size(wres.fake) / 1024.0))
        elif wres is not None:
            wf = W.write_checks(T, wres, a.day)
            fails += wf
            sc = T.w_scripts(wres)
            tot = {}
            for c in sc:
                for t, rows in T.sent_rows(c).items():
                    tot[t] = tot.get(t, 0) + len(rows)
            print("GATE %s: write fake: %d scripts, rows sent %s, withheld (grain_uq, reported) %d, write checks %s" % (
                tag, len(sc), json.dumps(tot, sort_keys=True), withheld, "PASS" if not wf else "FAIL %d" % len(wf)))
    for k, f in enumerate(fails, 1):                       # every failure, one per line (the verdict line keeps its first six)
        print("GATE %s failure %d/%d: %s" % (tag, k, len(fails), f))
    print("GATE %s %s%s" % (tag, "PASS" if not fails else "FAIL", "" if not fails else ": " + "; ".join(fails[:6])))
    if not a.keep:
        shutil.rmtree(work, ignore_errors=True)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
