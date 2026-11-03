#!/usr/bin/env python3
"""Tape T1b cycle aggregator: tape_minute.csv -> 5-minute cycle table + event candidates.

  python -m services.tape_offline.cycle_day --in C:\\tape_data\\out_2026-11-02 --session C:\\tape_data\\2026-11-02\\session --out C:\\tape_data\\cyc_2026-11-02

--in holds tape_minute.csv (T1a output); --session holds subscriptions_*.json, either directly or under a
<day>/ subdirectory. Read-only on both. Standard library only. No network, no database.
Tape half only: it reads nothing but those two inputs.

Outputs (deterministic, byte-identical across runs): tape_strike_cycle.csv, tape_events.csv, cycle_report.json,
cycle_report.txt, run_manifest.json. Exit 0 written; 2 usage / input error; 4 invariant violated (written).
Elapsed time and peak working set go to stderr only, so the outputs stay reproducible.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from merdian_compute.tape import cycle, events, replay  # noqa: E402

CATS = ("buy", "sell", "uncl", "gap")


class InputError(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def peak_mb():
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class PMC(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
            k32, ps = ctypes.windll.kernel32, ctypes.windll.psapi
            k32.GetCurrentProcess.restype = wintypes.HANDLE
            ps.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
            pmc = PMC()
            pmc.cb = ctypes.sizeof(PMC)
            if ps.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb):
                return pmc.PeakWorkingSetSize / 1048576.0
        else:
            with open("/proc/self/status", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("VmHWM:"):
                        return int(line.split()[1]) / 1024.0
    except Exception:  # noqa: BLE001 - a missing figure must never fail the run
        pass
    return None


def find_session_files(session, day):
    for d in (session, os.path.join(session, day)):
        if os.path.isdir(d):
            names = sorted(n for n in os.listdir(d) if replay.SUB_RE.match(n))
            if names:
                return d, names
    return None, []


def read_added(d, names):
    added = {}
    for n in sorted(names, key=replay.sub_sort_key):
        with open(os.path.join(d, n), encoding="utf-8") as fh:
            try:
                doc = json.load(fh)
            except ValueError as exc:
                raise InputError("unreadable %s: %s" % (n, exc))
        for row in doc.get("tokens", []):
            try:
                tok = int(row["token"])
            except (KeyError, TypeError, ValueError):
                continue
            if tok not in added and row.get("added_minute"):
                added[tok] = row["added_minute"]
    return added


def read_minutes(path):
    with open(path, encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        for r in rd:
            yield r


def raw_sums(path):
    """In-session sums per token straight from the CSV, by string comparison, independent of cycle.py."""
    per, out_rows = {}, 0
    for r in read_minutes(path):
        if not ("09:15" <= r["minute"] < "15:30"):
            out_rows += 1
            continue
        s = per.setdefault(int(r["token"]), [0, 0, 0, 0])
        s[0] += int(r["buy_qty"])
        s[1] += int(r["sell_qty"])
        s[2] += int(r["uncl_qty"])
        s[3] += int(r["gap_qty"])
    return per, out_rows


def invariant(cyc_rows, per):
    got = {}
    for r in cyc_rows:
        s = got.setdefault(r["token"], [0, 0, 0, 0])
        s[0] += r["buy_5"]
        s[1] += r["sell_5"]
        s[2] += r["uncl_5"]
        s[3] += r["gap_5"]
    bad = []
    for tok in sorted(set(per) | set(got)):
        a, b = per.get(tok, [0, 0, 0, 0]), got.get(tok, [0, 0, 0, 0])
        if a != b:
            bad.append({"token": tok, "minute_csv": a, "cycle_rows": b})
    tot_a = [sum(v[i] for v in per.values()) for i in range(4)]
    tot_b = [sum(v[i] for v in got.values()) for i in range(4)]
    return {"ok": not bad and tot_a == tot_b, "failures": bad[:20],
            "minute_csv_totals": dict(zip(CATS, tot_a)), "cycle_totals": dict(zip(CATS, tot_b))}


def code_info():
    def git(*a):
        try:
            r = subprocess.run(["git", "-C", _ROOT] + list(a), capture_output=True, text=True, timeout=30)
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None
    sha = git("rev-parse", "HEAD")
    st = git("status", "--porcelain", "--", "merdian_compute/tape", "services/tape_offline")
    return {"git_sha": sha or "unknown", "dirty": None if st is None else bool(st)}


def _write(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_report_text(rep):
    L = ["MERIDIAN tape T1b - cycle report for %s" % rep["day"], ""]
    iv = rep["invariant"]
    L.append("invariant (cycle rows vs tape_minute.csv, per token and per category): %s" % ("OK" if iv["ok"] else "VIOLATED"))
    L.append("  minute csv totals %s" % json.dumps(iv["minute_csv_totals"], sort_keys=True))
    L.append("  cycle totals      %s" % json.dumps(iv["cycle_totals"], sort_keys=True))
    L.append("minute rows: %d in, %d in session, %d out of session; out-of-session qty %s"
             % (rep["rows_in"], rep["rows_in_session"], rep["rows_out_of_session"], json.dumps(rep["qty_out_of_session"], sort_keys=True)))
    for sym, s in rep["symbols"].items():
        L.append("=== %s: %d cycle rows, %d strike-legs ===" % (sym, s["cycle_rows"], s["strike_legs"]))
        L.append("  candidates: " + ", ".join("%s %d" % kv for kv in s["candidates"].items()))
    L.append("tokens in the map with no minute rows: %d; first-seen fallback: %d; data before added_minute: %d"
             % (len(rep["tokens_in_map_without_rows"]), len(rep["first_seen_fallback"]), len(rep["data_before_added"])))
    return "\n".join(L) + "\n"


def main(argv=None):
    t0 = time.perf_counter()
    ap = argparse.ArgumentParser(prog="cycle_day", description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--session", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    inp, sess, out = os.path.abspath(args.inp), os.path.abspath(args.session), os.path.abspath(args.out)
    csv_path = os.path.join(inp, "tape_minute.csv")
    if not os.path.isfile(csv_path):
        print("no tape_minute.csv under %s" % inp, file=sys.stderr)
        return 2
    for base in (inp, sess):
        if out == base or out.startswith(base + os.sep):
            print("--out must not be inside --in or --session (inputs are read-only)", file=sys.stderr)
            return 2
    days = sorted({r["day"] for r in read_minutes(csv_path)})
    if len(days) != 1:
        print("tape_minute.csv must hold exactly one day, found %s" % days, file=sys.stderr)
        return 2
    day = days[0]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", day):
        print("bad day value %r" % day, file=sys.stderr)
        return 2
    sdir, names = find_session_files(sess, day)
    if not names:
        print("no subscriptions_*.json under %s or %s" % (sess, os.path.join(sess, day)), file=sys.stderr)
        return 2
    try:
        added = read_added(sdir, names)
        res = cycle.build_cycle(read_minutes(csv_path), added)
    except (InputError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    per, out_rows = raw_sums(csv_path)
    iv = invariant(res["rows"], per)
    ev = events.candidates(res["tokens"])
    info = res["info"]
    syms = {}
    for r in res["rows"]:
        s = syms.setdefault(r["symbol"], {"cycle_rows": 0, "tokens": set(), "candidates": {"CONC": 0, "THIN": 0}})
        s["cycle_rows"] += 1
        s["tokens"].add(r["token"])
    for e in ev:
        syms[e[0]]["candidates"][e[4]] += 1
    rep = {"schema": "t1b_cycle_report_v1", "day": day, "invariant": iv, "rows_in": info["rows_in"],
           "rows_in_session": info["rows_in_session"], "rows_out_of_session": info["rows_out_of_session"],
           "qty_out_of_session": info["qty_out_of_session"], "rows_out_of_session_check": out_rows,
           "tokens_in_map_without_rows": info["tokens_in_map_without_rows"],
           "tokens_no_session_rows": info["tokens_no_session_rows"],
           "first_seen_fallback": info["first_seen_fallback"], "data_before_added": info["data_before_added"],
           "symbols": {k: {"cycle_rows": v["cycle_rows"], "strike_legs": len(v["tokens"]), "candidates": v["candidates"]}
                       for k, v in sorted(syms.items())}}
    os.makedirs(out, exist_ok=True)
    outputs = {
        "tape_strike_cycle.csv": _write(os.path.join(out, "tape_strike_cycle.csv"), cycle.render_cycle_csv(res["rows"])),
        "tape_events.csv": _write(os.path.join(out, "tape_events.csv"), events.render_events_csv(ev)),
        "cycle_report.json": _write(os.path.join(out, "cycle_report.json"), json.dumps(rep, sort_keys=True, indent=1) + "\n"),
        "cycle_report.txt": _write(os.path.join(out, "cycle_report.txt"), render_report_text(rep)),
    }
    inputs = [{"path": "in/tape_minute.csv", "sha256": sha256_file(csv_path), "bytes": os.path.getsize(csv_path)}]
    for n in names:
        p = os.path.join(sdir, n)
        inputs.append({"path": "session/" + n, "sha256": sha256_file(p), "bytes": os.path.getsize(p)})
    inputs.sort(key=lambda e: e["path"])
    man = {"schema": "t1b_cycle_manifest_v1", "args": {"day": day}, "code": code_info(), "inputs": inputs, "outputs": outputs}
    _write(os.path.join(out, "run_manifest.json"), json.dumps(man, sort_keys=True, indent=1) + "\n")
    for sym, s in rep["symbols"].items():
        print("%s: %d cycle rows over %d strike-legs; candidates %s" % (sym, s["cycle_rows"], s["strike_legs"],
                                                                         json.dumps(s["candidates"], sort_keys=True)))
    pk = peak_mb()
    print("elapsed_s=%.2f peak_working_set_mb=%s" % (time.perf_counter() - t0, "n/a" if pk is None else "%.1f" % pk), file=sys.stderr)
    if not iv["ok"]:
        print("INVARIANT VIOLATED - outputs written for inspection", file=sys.stderr)
        return 4
    print("T1B CYCLE_DAY PASS (invariant OK; %d cycle rows; %d candidates) outputs in %s" % (len(res["rows"]), len(ev), out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
