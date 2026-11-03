#!/usr/bin/env python3
"""T0 load rehearsal driver. Runs the REAL Recorder (real SegmentWriter, real upload thread, real
boto3 S3 client from the unit's aws.env, real clock) against a synthetic Kite feed.
NOT shipped by install.sh; staged by tests/rehearsal/stage.sh into /var/lib/tape/rehearsal_app.

  python run_rehearsal.py --schedule 2x:35m,4x:15m          # real S3, under _rehearsal/<id>/
  python run_rehearsal.py --schedule 2x:60s --fake-s3 0.3   # offline: fake S3 with 0.3 s latency
  python run_rehearsal.py --calibrate 2x:60s                # generator CPU only (no recorder)

What is rehearsal-only (nothing here changes the runner's code paths):
- TAPE_KEY_PREFIX=_rehearsal/<id>/ and TAPE_REHEARSAL_KEEP=<keep>/<id> are set in os.environ BEFORE
  the runner is imported, so the runner's own env hooks are what move the keys and keep the copies;
- the session timeline constants are moved to "now" (start = next whole minute, stop = start +
  schedule, rounded up to a minute), because the rehearsal runs outside market hours;
- its own root (/var/lib/tape/rehearsal_root/<id>): production's spool/state/manifest are never
  touched, so nothing a rehearsal leaves behind can be shipped by Monday's runner to real keys;
- instrumentation: on_ticks stall (timed by the synthetic ticker, which is the caller), gzip time
  (a timing wrapper around segments._gzip_into), PutObject latency (a timing wrapper around the
  S3 client), and a 1 s sampler of RSS, CPU, spool bytes and the upload queue.
Outputs in --out/<id>/: run.json, batches.ndjson, sent.json, samples.ndjson, heartbeats.ndjson,
uploads.ndjson, metrics.json, driver.log. Verify with verify_rehearsal.py --run <out>/<id>.
"""
import argparse
import json
import os
import resource
import signal
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

IST = timezone(timedelta(hours=5, minutes=30))


def parse_schedule(s):
    out = []
    for part in s.split(","):
        m, d = part.split(":")
        mult = float(m.rstrip("x"))
        secs = float(d[:-1]) * (60 if d.endswith("m") else 1) if d[-1] in "ms" else float(d)
        out.append((mult, secs))
    return out


def proc_status():
    rss = hwm = 0
    with open("/proc/self/status") as fh:
        for line in fh:
            if line.startswith("VmRSS:"):
                rss = int(line.split()[1]) * 1024
            elif line.startswith("VmHWM:"):
                hwm = int(line.split()[1]) * 1024
    return rss, hwm


def cgroup_file(name):
    try:
        with open("/proc/self/cgroup") as fh:
            rel = fh.read().strip().split("::", 1)[1]
        with open("/sys/fs/cgroup" + rel + "/" + name) as fh:
            return fh.read().strip()
    except Exception:  # noqa: BLE001
        return None


class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.stalls = []          # (stall_s, n_packets, mult)
        self.gzip = []            # (src, seconds, bytes_in)
        self.puts = []            # (key, seconds, bytes, ok)

    def on_ticks_call(self, stall, n, mult):
        with self.lock:
            self.stalls.append((stall, n, mult))


class TimedS3:
    def __init__(self, inner, metrics, log):
        self.inner = inner
        self.metrics = metrics
        self.log = log

    def put_object(self, **kw):
        body = kw["Body"]
        size = os.fstat(body.fileno()).st_size if hasattr(body, "fileno") else len(body)
        t0 = time.perf_counter()
        ok = False
        try:
            resp = self.inner.put_object(**kw)
            ok = True
            return resp
        finally:
            dt = time.perf_counter() - t0
            with self.metrics.lock:
                self.metrics.puts.append((kw["Key"], dt, size, ok))
            self.log.write(json.dumps({"key": kw["Key"], "put_s": round(dt, 4), "bytes": size, "ok": ok,
                                       "t": time.time_ns()}) + "\n")
            self.log.flush()


class FakeS3:
    def __init__(self, latency):
        import hashlib
        self.h = hashlib
        self.latency = latency

    def put_object(self, Body, ContentMD5=None, **kw):
        data = Body.read()
        time.sleep(self.latency)
        return {"ETag": '"%s"' % self.h.md5(data).hexdigest()}


def pct(xs, q):
    if not xs:
        return None
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * (len(xs) - 1) + 0.5))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schedule", default="2x:35m,4x:15m")
    ap.add_argument("--out", default="/var/lib/tape/rehearsal_out")
    ap.add_argument("--root", default="/var/lib/tape/rehearsal_root")
    ap.add_argument("--keep", default="/var/lib/tape/rehearsal_keep")
    ap.add_argument("--fake-s3", type=float, default=None, help="offline: fake S3 with this latency (s)")
    ap.add_argument("--calibrate", default=None, help="generator-only CPU, e.g. 2x:60s")
    ap.add_argument("--seg-seconds", type=int, default=None, help="self-test only: shorter segments")
    ap.add_argument("--allow-market-hours", action="store_true", help="self-test only")
    ap.add_argument("--silence", default=None, help="P7: START:DUR seconds after connect the socket goes silent, e.g. 120:40")
    ap.add_argument("--special", action="store_true",
                    help="P8: today is a special session (temp calendar: open = start+1 min, close = stop); the "
                         "T_* constants are NOT moved, the calendar alone drives the timeline")
    ap.add_argument("--terminate-after", type=float, default=None, help="P8: SIGTERM-equivalent after this many seconds")
    a = ap.parse_args()

    now_utc = datetime.now(timezone.utc)
    rid = now_utc.strftime("%Y%m%dT%H%M%SZ")
    now_ist = now_utc.astimezone(IST)
    if (not a.allow_market_hours and now_ist.isoweekday() <= 5
            and (8, 30) <= (now_ist.hour, now_ist.minute) < (15, 45)):
        print("REHEARSAL REFUSED: Mon-Fri 08:30-15:45 IST belongs to the live recorder")
        return 2

    if a.calibrate:
        return calibrate(parse_schedule(a.calibrate))

    schedule = parse_schedule(a.schedule)
    total_s = sum(s for _, s in schedule)
    start = (now_ist + timedelta(minutes=1)).replace(second=0, microsecond=0)
    stop = start + timedelta(seconds=total_s)
    if stop.second or stop.microsecond:
        stop = (stop + timedelta(minutes=1)).replace(second=0, microsecond=0)
    if stop.date() != start.date():
        print("REHEARSAL REFUSED: the run would cross IST midnight")
        return 2

    out = os.path.join(a.out, rid)
    root = os.path.join(a.root, rid)
    keep = os.path.join(a.keep, rid)
    prefix = "_rehearsal/%s/" % rid
    for d in (out, root, keep):
        os.makedirs(d, exist_ok=True)
    # the runner's own env hooks move the keys and keep the copies (set BEFORE import)
    os.environ["TAPE_KEY_PREFIX"] = prefix
    os.environ["TAPE_REHEARSAL_KEEP"] = keep

    from services.tape_runner import config, segments
    from services.tape_runner.clock import SystemClock
    from services.tape_runner.recorder import Recorder
    from services.tape_runner.segments import spool_bytes
    from feed import SyntheticKite, SyntheticTicker, universe_tokens

    hm = lambda d: d.strftime("%H:%M")  # noqa: E731
    if a.special:
        cal = os.path.join(out, "special_sessions.json")
        json.dump([{"date": start.strftime("%Y-%m-%d"), "open": hm(start + timedelta(minutes=1)), "close": hm(stop),
                    "label": "Rehearsal"}], open(cal, "w"))
        config.SPECIAL_SESSIONS_PATH = cal
    else:
        for k in ("T_START", "T_RESOLVE", "T_OPTIONS", "T_SESSION_START", "T_CLOSED_CHECK"):
            setattr(config, k, hm(start))
        config.T_RESOLVE_GIVEUP = hm(start + timedelta(minutes=5))
        config.T_STOP = hm(stop)
        config.T_SESSION_END = hm(stop)
    config.CLOSED_CHECK_SETTLE_S = 5
    if a.seg_seconds:
        config.SEG_SECONDS = a.seg_seconds

    logf = open(os.path.join(out, "driver.log"), "a", buffering=1)

    def log(msg):
        line = "%s TAPE %s" % (datetime.now(IST).strftime("%H:%M:%S"), msg)
        logf.write(line + "\n")
        print(line, flush=True)

    metrics = Metrics()
    real_gzip = segments._gzip_into

    def timed_gzip(src, path):
        t0 = time.perf_counter()
        size = os.path.getsize(src)
        real_gzip(src, path)
        with metrics.lock:
            metrics.gzip.append((os.path.basename(src), time.perf_counter() - t0, size,
                                 os.path.getsize(path), threading.current_thread().name))
    segments._gzip_into = timed_gzip

    uploads_log = open(os.path.join(out, "uploads.ndjson"), "a")
    if a.fake_s3 is not None:
        inner = FakeS3(a.fake_s3)
        region = "fake"
    else:
        import boto3
        from botocore.config import Config
        region = os.environ["AWS_DEFAULT_REGION"]
        inner = boto3.client("s3", region_name=region, config=Config(
            retries={"mode": "standard", "max_attempts": 3}, connect_timeout=5, read_timeout=30))
    s3 = TimedS3(inner, metrics, uploads_log)

    kite = SyntheticKite(today=start.date())
    utoks = universe_tokens(kite, start.date())
    batch_log = open(os.path.join(out, "batches.ndjson"), "a", buffering=1024 * 1024)
    tickers = []

    silence = None
    if a.silence:
        s0, d0 = a.silence.split(":")
        silence = [(float(s0), float(d0))]

    def factory():
        t = SyntheticTicker(utoks, schedule, metrics, batch_log=batch_log, silence=silence)
        tickers.append(t)
        return t

    run = {"id": rid, "prefix": prefix, "bucket": config.BUCKET, "region": region, "schedule": schedule,
           "start_ist": start.isoformat(), "stop_ist": stop.isoformat(), "day": start.strftime("%Y-%m-%d"),
           "seg_seconds": config.SEG_SECONDS, "root": root, "keep": keep, "out": out,
           "fake_s3": a.fake_s3, "pid": os.getpid(), "argv": sys.argv[1:]}
    json.dump(run, open(os.path.join(out, "run.json"), "w"), indent=1)
    log("REHEARSAL id=%s prefix=%s bucket=%s region=%s start=%s stop=%s schedule=%s"
        % (rid, prefix, config.BUCKET, region, hm(start), hm(stop), a.schedule))

    while datetime.now(IST) < start:
        time.sleep(0.2)

    clock = SystemClock()
    rec = Recorder(kite, factory, s3, clock, root=root, bucket=config.BUCKET, threaded=True, log=log)
    signal.signal(signal.SIGTERM, rec.request_stop)

    samples = open(os.path.join(out, "samples.ndjson"), "a", buffering=1)
    hbs = open(os.path.join(out, "heartbeats.ndjson"), "a", buffering=1)
    stop_sampler = threading.Event()
    t_mono0 = time.monotonic()

    def sampler():
        last_cpu, last_t, last_hb = None, None, None
        while not stop_sampler.is_set():
            t = time.monotonic()
            ct = os.times()
            cpu = ct.user + ct.system
            rss, hwm = proc_status()
            try:
                sp = spool_bytes(rec.spool)
            except Exception:  # noqa: BLE001
                sp = None
            frac = None if last_cpu is None else (cpu - last_cpu) / max(1e-6, t - last_t)
            st = {"t": time.time_ns(), "el": round(t - t_mono0, 2), "rss": rss, "hwm": hwm,
                  "cpu_frac": None if frac is None else round(frac, 4), "spool": sp,
                  "queue": len(rec.uploader.pending()), "state": rec.state}
            samples.write(json.dumps(st) + "\n")
            last_cpu, last_t = cpu, t
            try:
                hb = open(rec.heartbeat_path).read()
                if hb != last_hb:
                    hbs.write(hb.strip() + "\n")
                    last_hb = hb
            except OSError:
                pass
            stop_sampler.wait(1.0)
    th = threading.Thread(target=sampler, name="sampler", daemon=True)
    th.start()

    code = None
    t_loop = time.monotonic()
    try:
        while code is None:
            if a.terminate_after is not None and time.monotonic() - t_loop >= a.terminate_after:
                rec.request_stop()
                a.terminate_after = None
            code = rec.step(clock.now_ns())
            if code is None:
                time.sleep(1.0 - (time.time() % 1.0))
    finally:
        stop_sampler.set()
        th.join(5)
        batch_log.flush()
    sent = {str(t): n for tk in tickers for t, n in tk.seq.items()}
    json.dump(sent, open(os.path.join(out, "sent.json"), "w"))
    write_metrics(out, metrics, code, rec, schedule)
    log("REHEARSAL DONE exit=%s out=%s" % (code, out))
    logf.flush()
    return 0 if code == 0 else 1


def write_metrics(out, m, code, rec, schedule):
    stalls = [s for s, _, _ in m.stalls]
    rows = [json.loads(l) for l in open(os.path.join(out, "samples.ndjson"))]
    phase_end, acc = [], 0.0
    for mult, secs in schedule:
        acc += secs
        phase_end.append((mult, acc))
    by_phase = {}
    for r in rows:
        if r["cpu_frac"] is None or r["state"] not in ("RECORDING", "WAITING"):
            continue
        for mult, end in phase_end:
            if r["el"] < end:
                by_phase.setdefault(str(mult), []).append(r["cpu_frac"])
                break
    cpu = {}
    for k, xs in by_phase.items():
        win = [sum(xs[i:i + 10]) / len(xs[i:i + 10]) for i in range(0, len(xs), 10)]
        cpu[k + "x"] = {"mean": round(sum(xs) / len(xs), 4), "peak_10s": round(max(win), 4), "n": len(xs)}
    rss_peak = max(r["hwm"] for r in rows) if rows else None
    seg_gz = [g for g in m.gzip if g[0].startswith("seg_")]
    puts_ok = [p for p in m.puts if p[3]]
    metrics = {
        "exit_code": code,
        "peak_rss_mb": round(rss_peak / 2 ** 20, 1) if rss_peak else None,
        "ru_maxrss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "cgroup_memory_peak_mb": (lambda v: round(int(v) / 2 ** 20, 1) if v and v.isdigit() else v)(cgroup_file("memory.peak")),
        "cpu_fraction_of_one_core": cpu,
        "on_ticks": {"calls": len(stalls), "max_ms": round(1000 * max(stalls), 2) if stalls else None,
                     "p99_ms": round(1000 * pct(stalls, 0.99), 2) if stalls else None,
                     "p50_ms": round(1000 * pct(stalls, 0.5), 2) if stalls else None,
                     "over_200ms": sum(1 for s in stalls if s >= 0.2),
                     "packets": sum(n for _, n, _ in m.stalls)},
        "gzip_per_segment": {"n": len(seg_gz), "max_s": round(max(g[1] for g in seg_gz), 3) if seg_gz else None,
                             "mean_s": round(sum(g[1] for g in seg_gz) / len(seg_gz), 3) if seg_gz else None,
                             "max_raw_mb": round(max(g[2] for g in seg_gz) / 2 ** 20, 1) if seg_gz else None,
                             "max_gz_mb": round(max(g[3] for g in seg_gz) / 2 ** 20, 1) if seg_gz else None,
                             "threads": sorted({g[4] for g in seg_gz})},
        "put_latency": {"n": len(m.puts), "ok": len(puts_ok),
                        "max_s": round(max(p[1] for p in m.puts), 3) if m.puts else None,
                        "p50_s": round(pct([p[1] for p in m.puts], 0.5), 3) if m.puts else None,
                        "seg_max_s": round(max((p[1] for p in puts_ok if "/seg_" in p[0]), default=0), 3)},
        "spool_high_water_mb_sampled": round(max((r["spool"] or 0) for r in rows) / 2 ** 20, 1) if rows else None,
        "upload_queue_max": max((r["queue"] for r in rows), default=None),
        "late_records": rec.writer.late_records,
        "keep_dups": rec.uploader.keep_dups,
    }
    gz_by = {g[0].replace(".ndjson.closed", "").replace(".ndjson.part", ""): g[1] for g in seg_gz}
    per_seg = []
    for key, dt, size, ok in m.puts:
        if "/seg_" in key:
            name = key.rsplit("/", 1)[1].replace(".ndjson.gz", "")
            per_seg.append({"key": key, "gzip_s": round(gz_by.get(name, 0.0), 3), "put_s": round(dt, 3),
                            "gz_mb": round(size / 2 ** 20, 2)})
    metrics["per_segment"] = per_seg
    json.dump(metrics, open(os.path.join(out, "metrics.json"), "w"), indent=1)


def calibrate(schedule):
    """CPU of the synthetic generator alone (on_ticks is a no-op), to separate the harness's own
    cost from the recorder's in the 2x/4x CPU figures."""
    from feed import SyntheticKite, SyntheticTicker, universe_tokens
    from datetime import date
    kite = SyntheticKite(today=date.today())
    utoks = universe_tokens(kite, date.today())
    m = Metrics()
    t = SyntheticTicker(utoks, schedule, m)
    t.on_connect = lambda ws, r: ws.subscribe(_window(utoks))
    t.on_ticks = lambda ws, ticks: None
    c0, w0 = os.times(), time.monotonic()
    t.connect()
    t.done.wait(sum(s for _, s in schedule) + 30)
    c1, w1 = os.times(), time.monotonic()
    frac = ((c1.user + c1.system) - (c0.user + c0.system)) / (w1 - w0)
    n = sum(x[1] for x in m.stalls)
    print(json.dumps({"calibrate": schedule, "generator_cpu_fraction": round(frac, 4), "packets": n,
                      "packets_per_s": round(n / (w1 - w0), 1)}))
    return 0


def _window(utoks):
    """148 tokens shaped like the real window: 2 indexes, 2 futures, 82 NIFTY + 62 SENSEX options."""
    out = [t for t, v in utoks.items() if v[1] in ("IDX", "FUT")]
    for sym, n in (("NIFTY", 82), ("SENSEX", 62)):
        out += [t for t, v in utoks.items() if v[0] == sym and v[1] == "OPT"][:n]
    return out


if __name__ == "__main__":
    sys.exit(main())
