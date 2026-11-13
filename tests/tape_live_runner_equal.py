#!/usr/bin/env python3
"""Tape live L2 runner, Phase A real-day gate (docs/tape/L2_live_runner_plan.md sections 9 and 12). NOT a run_offline.sh step.

  python tests/tape_live_runner_equal.py --data C:\\tape_data --work <dir> --day 2026-11-06 --variant clean|late|ooo [--keep]

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
db / s3 / re-emit figures, the epoch bumps per symbol and trigger with the rows each re-sent, and a FLAG when a bump cycle costs
more than a typical cycle (bump wall_s - median > median). live_metrics.csv is kept as <work>/<day>_<variant>_metrics.csv.
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--day", required=True)
    ap.add_argument("--variant", choices=sorted(ARRIVAL), required=True)
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    if refused():
        return 2
    if not tie_selftest():
        print("TIE SELFTEST did NOT fire: the tie check cannot fail; gate FAIL")
        return 1
    print("TIE SELFTEST fired")
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
    rc2 = cli.main(argv)
    t2 = time.time()
    print("GATE %s: runner rc=%s %.0f s peak_ws_mb=%s" % (tag, rc2, t2 - t1, peak_mb()))
    fails = []
    if rc1 != 0 or rc2 != 0:
        fails.append("rc replay=%s runner=%s" % (rc1, rc2))
    else:
        ldir = os.path.join(odir, a.day, "live")
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
            cost = None if r is None else float(r["wall_s"])
            flag = cost is not None and cost - med > med
            print("GATE %s: epoch %s n=%d trigger=%s at=%s reemit_rows=%d cycle wall_s=%s rebuild_s=%s%s" % (
                tag, e["symbol"], e["n"], e["trigger"], hm, e["reemit_rows"], "-" if r is None else r["wall_s"],
                "-" if r is None else r["rebuild_s"], "  FLAG: bump cycle costs more than a typical cycle" if flag else ""))
        cnt = {}
        for e in man["epoch_log"]:
            cnt.setdefault(e["symbol"], {}).setdefault(e["trigger"], 0)
            cnt[e["symbol"]][e["trigger"]] += 1
        print("GATE %s: epochs per symbol/trigger %s; re-sent rows total %d" % (
            tag, json.dumps(cnt, sort_keys=True), sum(e["reemit_rows"] for e in man["epoch_log"])))
        fails += db_checks(ldir, cyc, a.day)
    print("GATE %s %s%s" % (tag, "PASS" if not fails else "FAIL", "" if not fails else ": " + "; ".join(fails[:6])))
    if not a.keep:
        shutil.rmtree(work, ignore_errors=True)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
