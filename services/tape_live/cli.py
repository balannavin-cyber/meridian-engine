#!/usr/bin/env python3
"""Tape live L0 command line (docs/tape/L0_plan.md section 6). Local, offline, replay mode only.

  python -m services.tape_live.cli replay --day 2026-11-06 --raw C:\\tape_data\\2026-11-06
      --chain-runs C:\\tape_data\\chain_2026-11-06\\gex_strike_snapshots_NIFTY.csv --chain-runs ...SENSEX.csv --out <dir>
      [--arrival <json>] [--until HH:MM] [--resume]
  python -m services.tape_live.cli verify --day D --live <replay dir> --final-cycle <csv> --final-events <csv>
      --final-chain-runs <csv> --report <dir>
  python -m services.tape_live.cli ddl --out sql/2026-11-06_tape_live_tables.sql

replay feeds the day's recorded segments one at a time, in the order they would have become available live: segment
seg_HHMM* at HHMM + 5 minutes (its receive window has closed), subscriptions_HHMMSS.json at the first 5-minute grid point at or
after HHMMSS; --arrival {"SYMBOL/seg_name": "HH:MM"} overrides a file's availability (tests plant late segments with it). After
each cycle it writes the per-cycle upserts / deletes under <out>/cycles/, and at the end the final state, the wall rows, the
labels and run_manifest.json (input and output sha256). Deterministic: no writer clock in replay (as_of is the simulated cycle
time, UTC) and live_run_id is a uuid5 of (day, code sha, input digest). Per-cycle timings go to stderr only.
--resume keeps the label rows already in <out> (first label wins) and recomputes everything else.

Read-only on --raw and the chain CSVs. Standard library only. No network, no database, no S3. Exit 0 written; 2 usage / input.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from merdian_compute.tape import replay, special  # noqa: E402
from services.tape_live import ddl, live_runner, live_sources, verify_day, wall_source, writer  # noqa: E402
from services.tape_offline.cycle_day import peak_mb  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))
HM_RE = re.compile(r"^\d{2}:\d{2}$")


class InputError(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _w(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _hm(m):
    return "%02d:%02d" % (m // 60, m % 60)


def _min(hhmm):
    return int(hhmm[:2]) * 60 + int(hhmm[3:5])


def code_info():
    def git(*a):
        try:
            r = subprocess.run(["git", "-C", _ROOT] + list(a), capture_output=True, text=True, timeout=30)
            return r.stdout.strip() if r.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None
    sha = git("rev-parse", "HEAD")
    st = git("status", "--porcelain", "--", "merdian_compute/tape", "services/tape_live", "services/tape_offline")
    return {"git_sha": sha or "unknown", "dirty": None if st is None else bool(st)}


def as_of(day, m):
    d = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=IST) + timedelta(minutes=m)
    return d.astimezone(timezone.utc).isoformat()


def _rows_csv(cols, rows):
    import io
    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(cols)
    for r in rows:
        wr.writerow([r[c] for c in cols])
    return buf.getvalue()


def plan_inputs(raw, day, arrival):
    """-> (segment events, subscription events, input file list). Events are (minute available, sort key, ...)."""
    segs, subs, files = [], [], []
    for si, sym in enumerate(writer.SYMBOLS):
        d = os.path.join(raw, sym, day)
        if not os.path.isdir(d):
            continue
        for n in sorted(os.listdir(d)):
            k = replay.parse_seg_name(n)
            if k is None:
                continue
            at = arrival.pop("%s/%s" % (sym, n), None)
            m = _min(at) if at is not None else _min(k[0][:2] + ":" + k[0][2:]) + 5
            segs.append((m, si, k, n, sym))
            files.append(("%s/%s/%s" % (sym, day, n), os.path.join(d, n)))
    sd = os.path.join(raw, "session", day)
    if os.path.isdir(sd):
        for n in sorted(os.listdir(sd), key=replay.sub_sort_key):
            mt = replay.SUB_RE.match(n)
            if not mt:
                continue
            hh, mm, ss = int(mt.group(1)[:2]), int(mt.group(1)[2:4]), int(mt.group(1)[4:])
            secs = hh * 3600 + mm * 60 + ss
            m = -(-secs // 300) * 5
            at = arrival.pop("session/%s" % n, None)
            p = os.path.join(sd, n)
            try:
                with open(p, encoding="utf-8") as fh:
                    doc = json.load(fh)
            except ValueError as exc:
                raise InputError("unreadable %s: %s" % (n, exc))
            subs.append((_min(at) if at is not None else m, replay.sub_sort_key(n), n, doc))
            files.append(("session/%s/%s" % (day, n), p))
    if arrival:
        raise InputError("--arrival names files that are not present: %s" % sorted(arrival))
    for e in segs + subs:
        if e[0] % 5:
            raise InputError("availability %s is not on the 5-minute grid" % _hm(e[0]))
    return segs, subs, files


def cmd_replay(a):
    day, raw, out = a.day, os.path.abspath(a.raw), os.path.abspath(a.out)
    if out == raw or out.startswith(raw + os.sep):
        print("--out must not be inside --raw (the input is read-only)", file=sys.stderr)
        return 2
    w = special.special_window(day, None)
    win = (w["open"], w["close"]) if w else None
    arrival = {}
    if a.arrival:
        with open(a.arrival, encoding="utf-8") as fh:
            arrival = json.load(fh)
    segs, subs, files = plan_inputs(raw, day, dict(arrival))
    if not segs:
        print("no segments under %s" % raw, file=sys.stderr)
        return 2
    runs = wall_source.runs_from_snapshot_csv(a.chain_runs, day)
    for p in a.chain_runs:
        files.append(("chain/%s" % os.path.basename(p), os.path.abspath(p)))
    inputs = [{"path": rel, "sha256": sha256_file(p), "bytes": os.path.getsize(p)} for rel, p in sorted(files)]
    code = code_info()
    digest = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode("utf-8")).hexdigest()
    live_run_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "meridian-tape-live:%s:%s:%s" % (day, code["git_sha"], digest)))
    paths = {(sym, n): os.path.join(raw, sym, day, n) for _m, _si, _k, n, sym in segs}

    def reader(sym, name):
        with gzip.open(paths[(sym, name)], "rb") as fh:
            for line in fh:
                yield line

    ld = writer.LiveDay(day, reader, win, live_run_id, code["git_sha"])
    os.makedirs(out, exist_ok=True)
    lab_path = os.path.join(out, "tape_live_label.csv")
    if a.resume and os.path.isfile(lab_path):
        with open(lab_path, encoding="utf-8", newline="") as fh:
            ld.load_labels(list(csv.DictReader(fh)))
    cdir = os.path.join(out, "cycles")
    shutil.rmtree(cdir, ignore_errors=True)
    os.makedirs(cdir)
    until = _min(a.until) if a.until else None
    grid = sorted(set(range(min(e[0] for e in segs + subs), max(e[0] for e in segs + subs) + 1, 5))
                  | set(range(writer.GRID_FIRST, writer.GRID_LAST + 1, 5)))
    segs.sort(key=lambda e: (e[0], e[1], e[2], e[3]))
    subs.sort(key=lambda e: (e[0], e[1]))
    si = ui = 0
    last_t = None
    stopped = False
    for t in grid:
        if until is not None and t > until:
            stopped = True
            break
        t0 = time.perf_counter()
        while ui < len(subs) and subs[ui][0] <= t:
            ld.add_subscriptions(subs[ui][2], subs[ui][3], t)
            ui += 1
        while si < len(segs) and segs[si][0] <= t:
            ld.add_segment(segs[si][4], segs[si][3], t)
            si += 1
        if t < writer.GRID_FIRST:
            continue
        walls = {}
        if t <= writer.GRID_LAST:
            walls = {s: wall_source.wall_row(runs.get(s, []), day, _hm(t)) for s in writer.SYMBOLS}
        d = ld.cycle(t, walls, as_of(day, t))
        _write_delta(cdir, _hm(t).replace(":", ""), d)
        last_t = t
        pk = peak_mb()
        print("cycle %s %.2f s peak_ws_mb=%s" % (_hm(t), time.perf_counter() - t0, "n/a" if pk is None else "%.1f" % pk),
              file=sys.stderr, flush=True)
    if not stopped:
        d = ld.cycle(None, {}, as_of(day, last_t))
        _write_delta(cdir, "final", d)
    outputs = {}
    texts = {"tape_live_cycle.csv": ld.state_cycle_csv(), "tape_live_events.csv": ld.state_events_csv(),
             "tape_live_wall.csv": _rows_csv(writer.WALL_COLS, [ld.walls[k] for k in sorted(ld.walls)]),
             "tape_live_label.csv": _rows_csv(writer.LABEL_COLS, [ld.labels[k] for k in sorted(ld.labels)])}
    for n, text in texts.items():
        _w(os.path.join(out, n), text)
    for dp, _ds, ns in os.walk(out):
        for n in ns:
            rel = os.path.relpath(os.path.join(dp, n), out).replace(os.sep, "/")
            if rel != "run_manifest.json":
                outputs[rel] = sha256_file(os.path.join(dp, n))
    counts = {}
    for r in ld.labels.values():
        c = counts.setdefault(r["symbol"], {})
        c[r["label"]] = c.get(r["label"], 0) + 1
        if r["label"] == "NO_READ":
            c["NO_READ: " + r["reason"]] = c.get("NO_READ: " + r["reason"], 0) + 1
    man = {"schema": "tape_live_replay_manifest_v1",
           "args": {"day": day, "until": a.until, "resume": bool(a.resume), "arrival": dict(sorted(arrival.items()))},
           "code": code, "live_run_id": live_run_id, "rule_version": writer.rules.RULE_VERSION, "inputs": inputs,
           "outputs": dict(sorted(outputs.items())), "rebuilds": ld.rebuilds, "late_segments": ld.late,
           "bad_files": ld.bad_files, "token_map_conflicts": ld.conflicts, "stopped_at_until": stopped,
           "label_counts": {s: dict(sorted(v.items())) for s, v in sorted(counts.items())}}
    _w(os.path.join(out, "run_manifest.json"), json.dumps(man, indent=1, sort_keys=True) + "\n")
    for s, v in man["label_counts"].items():
        print("%s labels: %s" % (s, json.dumps(v, sort_keys=True)))
    print("rebuilds: %s" % json.dumps([{k: r[k] for k in ("trigger", "at", "symbol")} for r in ld.rebuilds]))
    print("TAPE LIVE REPLAY written to %s (%d labels, %d wall rows)" % (out, len(ld.labels), len(ld.walls)))
    return 0


def local_schedule(raw, day, arrival):
    """{object key: epoch seconds it becomes visible}: cli replay's availability rule (segment seg_HHMM* at HHMM + 5 minutes,
    subscriptions at the first grid point at or after HHMMSS, --arrival overrides) plus 2 s, for the runner's simulated clock."""
    segs, subs, _files = plan_inputs(raw, day, dict(arrival))
    base = live_runner.day_epoch(day)
    vis = {}
    for m, _si, _k, n, sym in segs:
        vis["%s/%s/%s" % (sym, day, n)] = base + m * 60 + 2
    for m, _sk, n, _doc in subs:
        vis["session/%s/%s" % (day, n)] = base + m * 60 + 2
    return vis


AWS_KEY_VARS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")
RO_CONN_ENV = "TAPE_LIVE_RO_DSN"


def _code_sha():
    sha = code_info()["git_sha"]
    if sha == "unknown":
        try:
            with open(os.path.join(_ROOT, "CODE_SHA"), encoding="ascii") as fh:
                sha = fh.read().strip() or "unknown"
        except OSError:
            pass
    return sha


def cmd_live(a):
    """The live runner (docs/tape/L2_live_runner_plan.md). Read-only on S3 and the database; writes files under --out only."""
    dsn = os.environ.pop(RO_CONN_ENV, None)                       # read once, then gone from this process's environment
    for k in AWS_KEY_VARS:
        if os.environ.get(k):
            print("refused: AWS key variables are set; the runner signs with the instance role only", file=sys.stderr)
            return 2
    sha = _code_sha()
    if sha == "unknown" or not re.match(r"^[0-9a-f]{7,40}$", sha):
        print("refused: no code sha (git or CODE_SHA file)", file=sys.stderr)
        return 2
    day, out = a.day, os.path.abspath(a.out)
    if not HM_RE.match(a.start):
        print("--start must be HH:MM", file=sys.stderr)
        return 2
    if a.clock == "sim":
        clock = live_runner.SimClock(live_runner.day_epoch(day) + _min(a.start) * 60)
    else:
        clock = live_runner.RealClock()
    redact = []
    if a.chain == "psql":
        if not dsn:
            print("refused: %s is not set" % RO_CONN_ENV, file=sys.stderr)
            return 2
        try:
            parts = live_sources.parse_dsn(dsn)
        except ValueError as exc:
            print("refused: %s" % exc, file=sys.stderr)
            return 2
        redact = [parts["PGPASSWORD"], dsn]
        chain = live_sources.PsqlChainSource(parts, day)
        try:
            role, ro, priv = chain.check()
        except live_sources.SourceError as exc:
            print("refused: the database start-up check failed (%s)" % exc.category, file=sys.stderr)
            return 2
        if ro != "on" or priv != "f":
            print("refused: the database role is not read-only on the snapshot relation", file=sys.stderr)
            return 2
    else:
        chain = wall_source.LocalChainSource(a.chain_csv or [], day)
    if a.source == "s3":
        objs = live_sources.S3Source(a.bucket, clock=clock, filter_future=(a.clock == "sim"))
    else:
        if not a.raw:
            print("--source local needs --raw", file=sys.stderr)
            return 2
        arrival = {}
        if a.arrival:
            with open(a.arrival, encoding="utf-8") as fh:
                arrival = json.load(fh)
        objs = live_sources.LocalDirSource(os.path.abspath(a.raw), day, local_schedule(os.path.abspath(a.raw), day, arrival), clock)
    if a.check:
        print("CHECK PASS (environment, code sha, database role)")
        return 0
    cfg = live_runner.Config(day=day, out=out, code_sha=sha, kill_file=a.kill_file, lag=a.lag, rss_cap_mb=a.rss_cap_mb,
                             disk_floor_mb=a.disk_floor_mb, disk_stop_mb=a.disk_floor_mb / 5.0)
    if a.clock == "real":
        term = {"hit": False}

        def on_term(_signum, _frame):
            term["hit"] = True
        signal.signal(signal.SIGTERM, on_term)
        cfg.term = term
    rc = live_runner.run_day(cfg, objs, chain, clock, redact=redact)
    print("TAPE LIVE RUNNER exit %d (state in %s)" % (rc, os.path.join(out, day)))
    return rc


def _write_delta(cdir, name, d):
    for part in ("cycle", "events"):
        if d[part]:
            _w(os.path.join(cdir, "%s_%s.csv" % (name, part)), d[part])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="services.tape_live.cli", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("replay")
    r.add_argument("--day", required=True)
    r.add_argument("--raw", required=True)
    r.add_argument("--chain-runs", action="append", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--arrival", default=None)
    r.add_argument("--until", default=None)
    r.add_argument("--resume", action="store_true")
    v = sub.add_parser("verify")
    v.add_argument("--day", required=True)
    v.add_argument("--live", required=True)
    v.add_argument("--final-cycle", required=True)
    v.add_argument("--final-events", required=True)
    v.add_argument("--final-chain-runs", required=True)
    v.add_argument("--report", required=True)
    g = sub.add_parser("ddl")
    g.add_argument("--out", required=True)
    lv = sub.add_parser("live")
    lv.add_argument("--day", required=True)
    lv.add_argument("--out", required=True)
    lv.add_argument("--source", choices=("s3", "local"), default="s3")
    lv.add_argument("--chain", choices=("psql", "local"), default="psql")
    lv.add_argument("--clock", choices=("real", "sim"), default="real")
    lv.add_argument("--start", default="08:50")
    lv.add_argument("--bucket", default="meridian-tape-raw")
    lv.add_argument("--lag", type=float, default=20.0)
    lv.add_argument("--kill-file", default=None)
    lv.add_argument("--rss-cap-mb", type=float, default=600.0)
    lv.add_argument("--disk-floor-mb", type=float, default=1024.0)
    lv.add_argument("--raw", default=None)
    lv.add_argument("--arrival", default=None)
    lv.add_argument("--chain-csv", action="append", default=None)
    lv.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", getattr(a, "day", "2000-01-01")):
        print("--day must be YYYY-MM-DD", file=sys.stderr)
        return 2
    try:
        if a.cmd == "replay":
            if a.until and not HM_RE.match(a.until):
                print("--until must be HH:MM", file=sys.stderr)
                return 2
            return cmd_replay(a)
        if a.cmd == "live":
            return cmd_live(a)
        if a.cmd == "verify":
            return verify_day.run(a.day, a.live, a.final_cycle, a.final_events, a.final_chain_runs, a.report)
        _w(a.out, ddl.render())
        print("wrote %s" % a.out)
        return 0
    except (InputError, ValueError, OSError) as exc:
        print("%s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
