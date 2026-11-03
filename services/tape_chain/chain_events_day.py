#!/usr/bin/env python3
"""Tape T1b chain events: a per-strike chain export for one day -> merged chain events + run table.

  python -m services.tape_chain.chain_events_day --in C:\\tape_data\\chain_2026-11-02 --out C:\\tape_data\\chain_2026-11-02\\events

--in holds gex_strike_snapshots_<SYMBOL>.csv with a .sha256 sidecar each (written by export_chain.py). Read-only.
Standard library only. No network, no database. Chain half only: it reads no tape data.

Outputs (deterministic): chain_events.csv, chain_runs.csv, chain_report.json, chain_report.txt, run_manifest.json.
Exit 0 written; 2 usage / input error; 3 sidecar sha256 mismatch (nothing written).
"""
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from merdian_compute.tape import chain_events  # noqa: E402

SYMBOLS = ("NIFTY", "SENSEX")
NEED = ("run_id", "symbol", "ts", "expiry_date", "strike", "oi_call", "oi_put", "gex_cr")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def code_info():
    def git(*a):
        try:
            r = subprocess.run(["git", "-C", _ROOT] + list(a), capture_output=True, text=True, timeout=30)
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None
    sha = git("rev-parse", "HEAD")
    st = git("status", "--porcelain", "--", "merdian_compute/tape", "services/tape_chain")
    return {"git_sha": sha or "unknown", "dirty": None if st is None else bool(st)}


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_rows(path):
    with open(path, encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        miss = [c for c in NEED if c not in (rd.fieldnames or [])]
        if miss:
            raise ValueError("%s lacks columns %s" % (os.path.basename(path), miss))
        return list(rd)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="chain_events_day", description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--day", default=None)
    args = ap.parse_args(argv)
    inp, out = os.path.abspath(args.inp), os.path.abspath(args.out)
    if not os.path.isdir(inp):
        print("not a directory: %s" % inp, file=sys.stderr)
        return 2
    if out == inp:
        print("--out must not be the input directory", file=sys.stderr)
        return 2
    day = args.day
    if day is None:
        m = re.search(r"chain_(\d{4}-\d{2}-\d{2})", os.path.basename(inp))
        day = m.group(1) if m else None
    if day is None or not re.match(r"^\d{4}-\d{2}-\d{2}$", day):
        print("cannot determine the day: name the directory chain_YYYY-MM-DD or pass --day", file=sys.stderr)
        return 2
    files = [(s, os.path.join(inp, "gex_strike_snapshots_%s.csv" % s)) for s in SYMBOLS]
    files = [(s, p) for s, p in files if os.path.isfile(p)]
    if not files:
        print("no gex_strike_snapshots_<SYMBOL>.csv under %s" % inp, file=sys.stderr)
        return 2
    inputs = []
    for s, p in files:
        side = p + ".sha256"
        if not os.path.isfile(side):
            print("missing sidecar %s" % os.path.basename(side), file=sys.stderr)
            return 2
        with open(side, encoding="utf-8") as fh:
            want = fh.read().split()[0]
        got = sha256_file(p)
        if want != got:
            print("SHA256 MISMATCH %s (sidecar %s, file %s); nothing written" % (os.path.basename(p), want, got), file=sys.stderr)
            return 3
        inputs.append({"path": os.path.basename(p), "sha256": got, "bytes": os.path.getsize(p)})
    try:
        rows = []
        for _s, p in files:
            rows += read_rows(p)
        res = chain_events.process(rows, day)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    rep = {"schema": "t1b_chain_report_v1", "day": day, "per_symbol": res["per_symbol"], "counters": res["counters"]}
    os.makedirs(out, exist_ok=True)
    outputs = {
        "chain_events.csv": _write(os.path.join(out, "chain_events.csv"), chain_events.render_events_csv(res["events"])),
        "chain_runs.csv": _write(os.path.join(out, "chain_runs.csv"), chain_events.render_runs_csv(res["runs"])),
        "chain_report.json": _write(os.path.join(out, "chain_report.json"), json.dumps(rep, sort_keys=True, indent=1) + "\n"),
        "chain_report.txt": _write(os.path.join(out, "chain_report.txt"), chain_events.render_text(day, res["per_symbol"], res["counters"])),
    }
    man = {"schema": "t1b_chain_manifest_v1", "args": {"day": day}, "code": code_info(), "inputs": inputs, "outputs": outputs}
    _write(os.path.join(out, "run_manifest.json"), json.dumps(man, sort_keys=True, indent=1) + "\n")
    for sym, s in res["per_symbol"].items():
        print("%s: %d runs (%d in window); counted events %s; E3 flips %d" % (
            sym, s["runs"], s["runs_in_window"], json.dumps(s["counted_events"], sort_keys=True), s["e3_flips"]))
        f = s.get("feasibility")
        if f and not f["within_x0.5_to_x2"]:
            print("  NOTE: %d events is far off the v0.2 rate of %.1f a day" % (f["this_day"], f["v02_per_day"]))
    print("T1B CHAIN_EVENTS_DAY PASS (%d events, %d runs) outputs in %s" % (len(res["events"]), len(res["runs"]), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
