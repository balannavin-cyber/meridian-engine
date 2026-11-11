#!/usr/bin/env python3
"""Tape live L2 runner, Phase A real-day gate (docs/tape/L2_live_runner_plan.md sections 9 and 12). NOT a run_offline.sh step.

  python tests/tape_live_runner_equal.py --data C:\\tape_data --work <dir> --day 2026-11-06 --variant clean|late|ooo [--keep]

One (day, variant) per process, so the runs can be started side by side. For the recorded day under <data>/<day> (+ chain export
under <data>/chain_<day>) it runs
  1. cli replay (the L0 path, with the variant's arrival map), and
  2. the runner (cli live --source local --chain local --clock sim): the same recorded files, appearing on a schedule,
and requires every output file byte-equal, except the live_run_id column of the wall and label files (Phase A interim id, plan
section 12) and run_manifest.json, whose rebuild / late / bad-file / conflict / label-count fields are compared. It also requires
the runner's final cycle and events to equal the offline cyc_<day>/tape_strike_cycle.csv and tape_events.csv byte for byte.
Control: the comparison is run once on a copy with one byte changed and must report a difference; if it does not, the gate FAILS.
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
IST = timezone(timedelta(hours=5, minutes=30))
print = functools.partial(print, flush=True)  # noqa: A001 - a stopped run must still leave its lines in the log
ARRIVAL = {"clean": {}, "late": {"NIFTY/seg_1100.ndjson.gz": "11:10"}, "ooo": {"NIFTY/seg_1200.ndjson.gz": "12:20"}}


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


def strip_col(b, col):
    rows = list(csv.reader(io.StringIO(b.decode("utf-8"))))
    i = rows[0].index(col)
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows([r[:i] + r[i + 1:] for r in rows])
    return buf.getvalue().encode("utf-8")


def compare_dirs(cdir, ldir):
    """-> list of differences between the cli replay out dir and the runner's live dir."""
    bad = []
    fa = [x for x in files_of(cdir) if x != "run_manifest.json"]
    fb = [x for x in files_of(ldir) if x != "run_manifest.json"]
    if fa != fb:
        bad.append("file sets differ: only cli %s, only runner %s" % (sorted(set(fa) - set(fb))[:5], sorted(set(fb) - set(fa))[:5]))
    for rel in sorted(set(fa) & set(fb)):
        x, y = rd(os.path.join(cdir, rel)), rd(os.path.join(ldir, rel))
        if rel in ("tape_live_wall.csv", "tape_live_label.csv"):
            x, y = strip_col(x, "live_run_id"), strip_col(y, "live_run_id")
        if x != y:
            bad.append("differs: " + rel)
    with open(os.path.join(cdir, "run_manifest.json"), encoding="utf-8") as fh:
        ma = json.load(fh)
    with open(os.path.join(ldir, "run_manifest.json"), encoding="utf-8") as fh:
        mb = json.load(fh)
    for k in ("rebuilds", "late_segments", "bad_files", "token_map_conflicts", "label_counts", "rule_version"):
        if ma.get(k) != mb.get(k):
            bad.append("manifest %s: cli %r runner %r" % (k, ma.get(k), mb.get(k)))
    return bad, len(fa), ma


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
        print("GATE %s: %d runner cycles, wall_s median %.2f max %.2f" % (tag, len(ms), walls[len(walls) // 2], walls[-1]))
    print("GATE %s %s%s" % (tag, "PASS" if not fails else "FAIL", "" if not fails else ": " + "; ".join(fails[:6])))
    if not a.keep:
        shutil.rmtree(work, ignore_errors=True)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
