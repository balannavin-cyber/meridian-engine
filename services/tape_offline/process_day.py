#!/usr/bin/env python3
"""Tape T1a offline processor: one day of raw segments -> classified minute rows + G3 report.

  python -m services.tape_offline.process_day <day_dir> --day 2026-11-02 --out <out_dir> [--verify-manifest]

<day_dir> mirrors the bucket: <day_dir>/NIFTY/<day>/, <day_dir>/SENSEX/<day>/, <day_dir>/session/<day>/.
Read-only on <day_dir>. Standard library only. Never touches S3, a network or a database.
Data quality only: completeness, classified share, rule mix, invariants.

Outputs (deterministic, byte-identical across runs): tape_minute.csv, g3_report.json, g3_report.txt,
run_manifest.json. Exit 0 outputs written (a FAIL / NOT EVALUATED verdict is a finding, not a tool failure);
2 usage or input layout; 3 manifest verification failed (nothing written); 4 invariant violated (written).
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import zlib

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from merdian_compute.tape import minute, replay  # noqa: E402

SYMBOLS = ("NIFTY", "SENSEX")
PROGRESS_EVERY = 100000


class InputError(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def list_symbol_files(day_dir, sym, day):
    d = os.path.join(day_dir, sym, day)
    return [os.path.join(d, n) for n in sorted(os.listdir(d)) if replay.parse_seg_name(n) is not None]


def read_token_map(day_dir, day):
    d = os.path.join(day_dir, "session", day)
    items = []
    if os.path.isdir(d):
        for n in sorted(os.listdir(d)):
            if replay.SUB_RE.match(n):
                try:
                    with open(os.path.join(d, n), encoding="utf-8") as fh:
                        items.append((n, json.load(fh)))
                except ValueError as exc:
                    raise InputError("unreadable %s: %s" % (n, exc))
    return replay.build_token_map(items)


def process_symbol(sym, paths, day, meta, progress=None):
    rp = replay.SymbolReplay(sym, day, meta)
    cur, n, bad_files = None, 0, []
    for path in replay.order_segments(paths):
        base = os.path.basename(path)
        hhmm = replay.parse_seg_name(base)[0]
        if cur is not None and hhmm != cur:
            rp.end_group(cur)
        cur = hhmm
        try:
            with gzip.open(path, "rb") as fh:
                for raw in fh:
                    raw = raw.rstrip(b"\r\n")
                    if not raw:
                        continue
                    rp.feed(raw)
                    n += 1
                    if progress is not None and n % PROGRESS_EVERY == 0:
                        progress(sym, n)
        except (EOFError, OSError, zlib.error) as exc:
            bad_files.append({"file": base, "error": type(exc).__name__})
    if cur is not None:
        rp.end_group(cur)
    res = rp.finish()
    res["bad_files"] = bad_files
    return res


def collect_inputs(day_dir, day):
    out = []
    for top in SYMBOLS + ("session",):
        d = os.path.join(day_dir, top, day)
        if not os.path.isdir(d):
            continue
        for dirpath, _dirs, files in os.walk(d):
            for n in files:
                p = os.path.join(dirpath, n)
                rel = os.path.relpath(p, day_dir).replace(os.sep, "/")
                out.append({"path": rel, "sha256": sha256_file(p), "bytes": os.path.getsize(p)})
    out.sort(key=lambda e: e["path"])
    return out


def verify_manifest(day_dir, day, inputs):
    mp = os.path.join(day_dir, "session", day, "MANIFEST.sha256")
    if not os.path.isfile(mp):
        return ["session/%s/MANIFEST.sha256 is missing" % day]
    want = {}
    with open(mp, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if line:
                h, _, key = line.partition("  ")
                want[key] = h
    have = {e["path"]: e["sha256"] for e in inputs}
    problems = []
    for key, h in sorted(want.items()):
        if key.split("/")[0] not in SYMBOLS + ("session",) or ("/%s/" % day) not in key:
            continue
        if key not in have:
            problems.append("missing: " + key)
        elif have[key] != h:
            problems.append("sha256 mismatch: " + key)
    self_key = "session/%s/MANIFEST.sha256" % day
    for path in sorted(have):
        if path not in want and path != self_key:
            problems.append("unlisted: " + path)
    return problems


def read_daily(day_dir, day):
    p = os.path.join(day_dir, "session", day, "daily_report_%s.json" % day)
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
    except ValueError:
        return {"unreadable": True}

    def cnt(v):
        return len(v) if isinstance(v, (list, dict)) else v

    out = {k: cnt(d.get(k)) for k in ("closed", "restarts", "reconnects", "disconnects", "unknown_tokens")}
    out["symbols"] = {s: {"packets": v.get("packets"), "feed_gaps_gt10s": cnt(v.get("feed_gaps_gt10s")),
                          "feed_gaps_gt60s": cnt(v.get("feed_gaps_gt60s"))}
                      for s, v in sorted((d.get("symbols") or {}).items())}
    return out


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
    data = text.encode("utf-8")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return hashlib.sha256(data).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="process_day", description=__doc__.split("\n")[0])
    ap.add_argument("day_dir")
    ap.add_argument("--day", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--verify-manifest", action="store_true")
    args = ap.parse_args(argv)
    day = args.day
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", day):
        print("--day must be YYYY-MM-DD", file=sys.stderr)
        return 2
    day_dir, out = os.path.abspath(args.day_dir), os.path.abspath(args.out)
    if not os.path.isdir(day_dir):
        print("not a directory: %s" % day_dir, file=sys.stderr)
        return 2
    if out == day_dir or out.startswith(day_dir + os.sep):
        print("--out must not be inside the day directory (the input is read-only)", file=sys.stderr)
        return 2
    syms = [s for s in SYMBOLS if os.path.isdir(os.path.join(day_dir, s, day))]
    if not syms:
        print("no NIFTY/%s or SENSEX/%s directory under %s" % (day, day, day_dir), file=sys.stderr)
        return 2
    inputs = collect_inputs(day_dir, day)
    verified = None
    if args.verify_manifest:
        problems = verify_manifest(day_dir, day, inputs)
        if problems:
            print("MANIFEST VERIFICATION FAILED (%d problems); nothing written" % len(problems), file=sys.stderr)
            for p in problems[:20]:
                print("  " + p, file=sys.stderr)
            return 3
        verified = True
    try:
        meta, conflicts = read_token_map(day_dir, day)
    except InputError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not meta:
        print("no subscriptions_*.json under session/%s: the token map is empty" % day, file=sys.stderr)
        return 2

    def progress(sym, n):
        print("[%s] %d packets read" % (sym, n), file=sys.stderr)

    results = {}
    for sym in syms:
        results[sym] = process_symbol(sym, list_symbol_files(day_dir, sym, day), day, meta, progress)
    ignored = []
    for sym in syms:
        for n in sorted(os.listdir(os.path.join(day_dir, sym, day))):
            if replay.parse_seg_name(n) is None:
                ignored.append("%s/%s" % (sym, n))
    info = {"n_files": len(inputs), "manifest_verified": verified, "ignored_files": ignored,
            "bad_files": sorted(["%s/%s" % (s, b["file"]) for s, r in results.items() for b in r["bad_files"]]),
            "unknown_files": len(os.listdir(os.path.join(day_dir, "_UNKNOWN", day)))
            if os.path.isdir(os.path.join(day_dir, "_UNKNOWN", day)) else 0}
    rep = minute.build_report(day, results, read_daily(day_dir, day), conflicts, info)
    rows = [r for s in syms for r in results[s]["rows"]]
    os.makedirs(out, exist_ok=True)
    outputs = {
        "tape_minute.csv": _write(os.path.join(out, "tape_minute.csv"), minute.render_csv(rows)),
        "g3_report.json": _write(os.path.join(out, "g3_report.json"), minute.render_json(rep)),
        "g3_report.txt": _write(os.path.join(out, "g3_report.txt"), minute.render_text(rep)),
    }
    code = code_info()
    man = {"schema": "t1a_run_manifest_v1", "args": {"day": day, "verify_manifest": bool(args.verify_manifest)},
           "code": code, "inputs": inputs, "outputs": outputs}
    _write(os.path.join(out, "run_manifest.json"), minute.render_json(man))
    for s in syms:
        v = rep["symbols"][s]
        print("%s G3 VERDICT: %s  (early %s %%, late %s %%)" % (
            s, v["verdict"], v["verdict_detail"]["early"]["share_pct"], v["verdict_detail"]["late"]["share_pct"]))
    print("outputs in %s" % out)
    if not all(rep["symbols"][s]["invariants"]["ok"] for s in syms):
        print("INVARIANT VIOLATED - verdict INVALID; outputs written for inspection", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
