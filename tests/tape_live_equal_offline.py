#!/usr/bin/env python3
"""Tape live L0 gate on real days (docs/tape/L0_plan.md sections 2, 6 and O-1). NOT a run_offline.sh step: it reads recorded days.

  python tests/tape_live_equal_offline.py --data C:\\tape_data --work <dir> [--days 2026-11-04 2026-11-05 2026-11-06]

Per day: replay the recorded segments through services/tape_live (cli replay), then
  1. the final live state equals the offline cyc_<day>/tape_strike_cycle.csv and tape_events.csv BYTE FOR BYTE, both as written
     and as rebuilt from the per-cycle delta files;
  2. verify the as-seen labels against labels recomputed from the offline rows and chain_<day>/events/chain_runs.csv. Under
     O-1 a difference is allowed only with cause partial_cycle (data that reached the writer after its cycle); any other cause
     fails the day. The match % and every difference are reported.
  3. the label distribution per symbol (counts only).
Read-only on --data (the chain export .sha256 sidecars are checked first). Writes only under --work. Exit 0 all days PASS; 1 FAIL.
Rule 23 window as tests/test_tape_live.py (Local override TAPE_RULE23_OVERRIDE_R1=1, ruling R-1).
"""
import argparse
import functools
import contextlib
import csv
import hashlib
import io
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
IST = timezone(timedelta(hours=5, minutes=30))
print = functools.partial(print, flush=True)  # noqa: A001 - a stopped run must still leave its lines in the log


def refused():
    now = datetime.now(IST)
    if now.weekday() < 5 and 830 <= now.hour * 100 + now.minute < 1545:
        if os.environ.get("TAPE_RULE23_OVERRIDE_R1") == "1":
            print("RULE23 WINDOW LIFTED by operator ruling R-1 (2026-11-03): Local machine, not the retail box")
            return False
        print("REFUSED: rule 23 window (Local: set TAPE_RULE23_OVERRIDE_R1=1 under ruling R-1)")
        return True
    return False


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rd(p):
    with open(p, "rb") as fh:
        return fh.read()


def lines(b):
    return b.count(b"\n") - 1


def stage(day, name):
    from services.tape_offline.cycle_day import peak_mb
    pk = peak_mb()
    print("STAGE %s %s start peak_ws_mb=%s" % (day, name, "n/a" if pk is None else "%.1f" % pk))
    return pk


def day_check(cli, writer, data, work, day):
    stage(day, "sidecar-sha")
    raw = os.path.join(data, day)
    chain_dir = os.path.join(data, "chain_%s" % day)
    cyc = os.path.join(data, "cyc_%s" % day)
    snaps = [os.path.join(chain_dir, "gex_strike_snapshots_%s.csv" % s) for s in ("NIFTY", "SENSEX")]
    bad = []
    for p in snaps:
        side = p + ".sha256"
        if os.path.isfile(side):
            with open(side, encoding="utf-8") as fh:
                want = fh.read().split()[0].lower()
            if sha(p) != want:
                bad.append("%s sha256 != sidecar" % os.path.basename(p))
    out = os.path.join(work, "replay_%s" % day)
    argv = ["replay", "--day", day, "--raw", raw, "--out", out]
    for p in snaps:
        argv += ["--chain-runs", p]
    stage(day, "replay")
    t0 = time.perf_counter()
    elog = os.path.join(work, "replay_%s.stderr.log" % day)
    with open(elog, "w", encoding="utf-8", newline="\n", buffering=1) as fh, contextlib.redirect_stderr(fh):
        rc = cli.main(argv)   # per-cycle lines (with the peak working set) reach the file as they are printed
    el = time.perf_counter() - t0
    with open(elog, encoding="utf-8") as fh:
        err = io.StringIO(fh.read())
    if rc != 0:
        return False, ["replay rc=%s: %s" % (rc, err.getvalue()[-800:])], {}
    cyc_times = [float(l.split()[2]) for l in err.getvalue().splitlines() if l.startswith("cycle ")]
    stage(day, "compare")
    want_c, want_e = rd(os.path.join(cyc, "tape_strike_cycle.csv")), rd(os.path.join(cyc, "tape_events.csv"))
    got_c, got_e = rd(os.path.join(out, "tape_live_cycle.csv")), rd(os.path.join(out, "tape_live_events.csv"))
    texts = []
    cdir = os.path.join(out, "cycles")
    for n in sorted(os.listdir(cdir)):
        with open(os.path.join(cdir, n), encoding="utf-8", newline="") as fh:
            texts.append(fh.read())
    rc_, re_ = writer.apply_deltas(texts)
    eq = {"cycle_written": got_c == want_c, "events_written": got_e == want_e,
          "cycle_from_deltas": rc_.encode("utf-8") == want_c, "events_from_deltas": re_.encode("utf-8") == want_e}
    for k, v in eq.items():
        if not v:
            bad.append("%s != offline" % k)
    stage(day, "verify")
    rep_dir = os.path.join(work, "verify_%s" % day)
    with contextlib.redirect_stdout(io.StringIO()):
        cli.main(["verify", "--day", day, "--live", out, "--final-cycle", os.path.join(cyc, "tape_strike_cycle.csv"),
                  "--final-events", os.path.join(cyc, "tape_events.csv"),
                  "--final-chain-runs", os.path.join(chain_dir, "events", "chain_runs.csv"), "--report", rep_dir])
    with open(os.path.join(rep_dir, "verify_report.json"), encoding="utf-8") as fh:
        rep = json.load(fh)
    other = {c: n for c, n in rep["totals"]["by_cause"].items() if n and c != "partial_cycle"}
    if other:
        bad.append("O-1: differences with causes other than partial_cycle %s" % json.dumps(other, sort_keys=True))
    with open(os.path.join(out, "run_manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    info = {"elapsed_s": round(el, 1), "cycles": len(cyc_times),
            "cycle_s_median": sorted(cyc_times)[len(cyc_times) // 2] if cyc_times else None,
            "cycle_s_max": max(cyc_times) if cyc_times else None,
            "cycle_rows": lines(want_c), "event_rows": lines(want_e), "equal": eq,
            "verify": {s: {k: v[k] for k in ("compared", "matched", "match_pct", "missing", "differences")}
                       for s, v in rep["symbols"].items()},
            "label_counts": man["label_counts"],
            "rebuilds": [{k: r[k] for k in ("trigger", "at", "symbol")} for r in man["rebuilds"]],
            "late_segments": len(man["late_segments"]), "bad_files": man["bad_files"]}
    info["peak_ws_mb"] = stage(day, "done")
    return not bad, bad, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--days", nargs="+", default=["2026-11-04", "2026-11-05", "2026-11-06"])
    a = ap.parse_args()
    if refused():
        return 2
    data, work = os.path.abspath(a.data), os.path.abspath(a.work)
    if work == data or work.startswith(data + os.sep):
        print("--work must not be inside --data (read-only)")
        return 2
    os.makedirs(work, exist_ok=True)
    from services.tape_live import cli, writer
    all_ok, summary = True, {}
    for day in a.days:
        ok, bad, info = day_check(cli, writer, data, work, day)
        all_ok &= ok
        summary[day] = {"ok": ok, "problems": bad, **info}
        if info:
            print("LIVE-EQUAL-OFFLINE %s %s: tape_strike_cycle %d rows, tape_events %d rows; written %s/%s, from deltas %s/%s; "
                  "replay %.1f s over %d cycles (median %.2f s, max %.2f s); peak working set %s MB; rebuilds %s" % (
                      day, "PASS" if ok else "FAIL", info["cycle_rows"], info["event_rows"],
                      "equal" if info["equal"]["cycle_written"] else "DIFFERS", "equal" if info["equal"]["events_written"] else "DIFFERS",
                      "equal" if info["equal"]["cycle_from_deltas"] else "DIFFERS", "equal" if info["equal"]["events_from_deltas"] else "DIFFERS",
                      info["elapsed_s"], info["cycles"], info["cycle_s_median"], info["cycle_s_max"],
                      "n/a" if info["peak_ws_mb"] is None else "%.1f" % info["peak_ws_mb"],
                      json.dumps(info["rebuilds"])))
            for s, v in info["verify"].items():
                print("  %s labels: %d/%d match (%s %%), missing %d, differences %s" % (
                    s, v["matched"], v["compared"], v["match_pct"], v["missing"],
                    json.dumps({k: n for k, n in v["differences"].items() if n}, sort_keys=True)))
            for s, v in info["label_counts"].items():
                print("  %s label counts: %s" % (s, json.dumps(v, sort_keys=True)))
        for b in bad:
            print("  PROBLEM: " + b)
    with open(os.path.join(work, "equal_offline_summary.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    print("TAPE LIVE EQUAL-OFFLINE %s (%d days)" % ("PASS" if all_ok else "FAIL", len(a.days)))
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
