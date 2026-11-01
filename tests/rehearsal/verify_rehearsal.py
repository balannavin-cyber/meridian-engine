#!/usr/bin/env python3
"""Verify a T0 load rehearsal from what it kept locally (S3 is write-only, so nothing is read back)
and score the PASS criteria fixed before the run.

  python verify_rehearsal.py --run /var/lib/tape/rehearsal_out/<id>      (or --latest)

Integrity checks (each names what makes it fail):
  I1 sequence  -- every token's rehearsal_seq 0..sent-1 present exactly once in the kept segments
                  (a lost packet leaves a hole, a duplicated one a second hit);
  I2 batches   -- every on_ticks batch is wholly inside ONE segment per symbol, that segment is the
                  segment of the call's start or end time, and its per-symbol count equals what was
                  sent; per-segment counts are the sum of their batches;
  I3 names     -- no _rN / _cN / .dupN file (a name collision or an overwrite attempt), and every
                  symbol's segments are contiguous, one file per 5-minute slot;
  I4 manifest  -- MANIFEST.sha256 lists every kept object and each sha256 equals the kept copy's
                  (the keep copy is the uploaded bytes);
  I5 report    -- daily report packets per symbol = counted packets; feed gaps > 10 s / > 60 s =
                  recomputed from recv_ns over the same window; uploads ok per prefix = kept objects
                  uploaded before the report; retried = failed = failed_attempts = 0; late records
                  = torn repairs = 0; spool high-water consistent with the 1 s samples.
PASS criteria (fixed 2026-11-01 before the run):
  P1 zero lost or duplicated packets (I1 and I2)
  P2 on_ticks max stall < 200 ms
  P3 peak RSS < 150 MB
  P4 mean CPU < 40 % of one core in the 2x phase
  P5 every upload verified by ETag on the first attempt, no retries
  P6 spool does not trend upward (per load phase, over the full 5-minute intervals: the trough after
     each boundary does not grow by more than one segment's gzip size, and the peak by more than 10 %)
What this cannot see: anything S3 did after acknowledging the PutObject (no GetObject, by design);
the generator's own CPU is inside P4's figure (measure it with run_rehearsal.py --calibrate).
"""
import argparse
import glob
import gzip
import hashlib
import json
import os
import re
import sys
from datetime import datetime

SEG_RE = re.compile(r"^seg_(\d{4})(_[rc]\d+)?\.ndjson\.gz(\.dup\d+)?$")


def seg_of(ns, seg_s):
    step = seg_s * 10 ** 9
    return (ns // step) * step


def label(ns):
    from datetime import timedelta, timezone
    return datetime.fromtimestamp(ns / 1e9, timezone(timedelta(hours=5, minutes=30))).strftime("%H%M")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--out-root", default="/var/lib/tape/rehearsal_out")
    a = ap.parse_args()
    run_dir = a.run or sorted(glob.glob(os.path.join(a.out_root, "*")))[-1]
    run = json.load(open(os.path.join(run_dir, "run.json")))
    seg_s = run["seg_seconds"]
    keep = os.path.join(run["keep"], run["prefix"])
    day = run["day"]
    res = []

    def check(name, ok, detail):
        res.append((name, bool(ok), detail))

    sent = {int(k): v for k, v in json.load(open(os.path.join(run_dir, "sent.json"))).items()}
    seen = {t: bytearray(n) for t, n in sent.items()}
    dup = unknown = beyond = 0
    batch_seen = {}          # (batch, sym) -> [count, set(seg labels)]
    pk_count = {}
    recv = {}                # sym -> list of recv_ns
    seg_files = {}           # sym -> [names]
    seg_counts = {}          # (sym, label) -> packets
    bad_names = []
    corrupt = []
    for sym in ("NIFTY", "SENSEX"):
        d = os.path.join(keep, sym, day)
        names = sorted(os.listdir(d)) if os.path.isdir(d) else []
        seg_files[sym] = names
        recv[sym] = []
        pk_count[sym] = 0
        for name in names:
            m = SEG_RE.match(name)
            if not m or m.group(2) or m.group(3):
                bad_names.append("%s/%s" % (sym, name))
            if not m:
                continue
            lab = m.group(1)
            try:
                lines = gzip.decompress(open(os.path.join(d, name), "rb").read()).decode().splitlines()
            except Exception as exc:  # noqa: BLE001 -- an unreadable segment is a failure, not a crash
                corrupt.append("%s/%s (%s)" % (sym, name, type(exc).__name__))
                lines = []
            if True:
                for line in lines:
                    if '"k":"pkt"' not in line:
                        continue
                    r = json.loads(line)
                    tok, seq = r["instrument_token"], r.get("rehearsal_seq")
                    pk_count[sym] += 1
                    recv[sym].append(r["recv_ns"])
                    seg_counts[(sym, lab)] = seg_counts.get((sym, lab), 0) + 1
                    arr = seen.get(tok)
                    if arr is None:
                        unknown += 1
                    elif seq is None or seq >= len(arr):
                        beyond += 1
                    elif arr[seq]:
                        dup += 1
                    else:
                        arr[seq] = 1
                    b = batch_seen.setdefault((r.get("rehearsal_batch"), sym), [0, set()])
                    b[0] += 1
                    b[1].add(lab)
    missing = sum(len(arr) - sum(arr) for arr in seen.values())
    total_sent = sum(sent.values())
    check("I1 sequence", missing == 0 and dup == 0 and unknown == 0 and beyond == 0 and not corrupt,
          "sent %d packets over %d tokens; missing %d, duplicated %d, unknown-token %d, beyond-sent %d, unreadable %s"
          % (total_sent, len(sent), missing, dup, unknown, beyond, corrupt or "none"))

    bad_batches, nb, per_seg_from_batches = [], 0, {}
    for line in open(os.path.join(run_dir, "batches.ndjson")):
        b = json.loads(line)
        nb += 1
        allowed = {label(seg_of(b["t0"], seg_s)), label(seg_of(b["t1"], seg_s))}
        for sym, n in b["n"].items():
            if n == 0:
                continue
            got = batch_seen.get((b["b"], sym))
            if not got or got[0] != n or len(got[1]) != 1 or not got[1] <= allowed:
                bad_batches.append((b["b"], sym, n, got and (got[0], sorted(got[1])), sorted(allowed)))
            else:
                lab = next(iter(got[1]))
                per_seg_from_batches[(sym, lab)] = per_seg_from_batches.get((sym, lab), 0) + n
    check("I2 batches", not bad_batches and per_seg_from_batches == seg_counts,
          "%d batches; misplaced/short %d %s; per-segment counts equal batch sums: %s"
          % (nb, len(bad_batches), bad_batches[:3], per_seg_from_batches == seg_counts))

    gaps_in_slots = []
    for sym, names in seg_files.items():
        labs = [SEG_RE.match(n).group(1) for n in names if SEG_RE.match(n)]
        mins = [int(l[:2]) * 60 + int(l[2:]) for l in labs]
        step = seg_s // 60 or 1
        if mins and (len(set(mins)) != len(mins) or mins != list(range(mins[0], mins[0] + step * len(mins), step))):
            gaps_in_slots.append(sym)
    check("I3 names", not bad_names and not gaps_in_slots,
          "segment files NIFTY %d, SENSEX %d; collision/overwrite names %s; non-contiguous %s"
          % (len(seg_files["NIFTY"]), len(seg_files["SENSEX"]), bad_names or "none", gaps_in_slots or "none"))

    kept = {}
    for dp, _, fs in os.walk(keep):
        for f in fs:
            p = os.path.join(dp, f)
            kept[run["prefix"] + os.path.relpath(p, keep).replace(os.sep, "/")] = p
    man_key = "%ssession/%s/MANIFEST.sha256" % (run["prefix"], day)
    man_bad, man_keys = [], set()
    if man_key in kept:
        for line in open(kept[man_key]):
            sha, key = line.rstrip("\n").split("  ", 1)
            man_keys.add(key)
            if key not in kept or hashlib.sha256(open(kept[key], "rb").read()).hexdigest() != sha:
                man_bad.append(key)
    check("I4 manifest", man_key in kept and not man_bad and man_keys == set(kept) - {man_key},
          "MANIFEST present %s; %d keys; sha mismatches %d; kept-but-unlisted %d"
          % (man_key in kept, len(man_keys), len(man_bad), len(set(kept) - {man_key} - man_keys)))

    rep_key = "%ssession/%s/daily_report_%s.json" % (run["prefix"], day, day)
    rep = json.load(open(kept[rep_key])) if rep_key in kept else None
    rep_ok, rep_detail = rep is not None, []
    samples = [json.loads(l) for l in open(os.path.join(run_dir, "samples.ndjson"))]
    if rep:
        start = int(datetime.fromisoformat(run["start_ist"]).timestamp() * 1e9)
        stop = int(datetime.fromisoformat(run["stop_ist"]).timestamp() * 1e9)
        for sym in ("NIFTY", "SENSEX"):
            rs = rep["symbols"][sym]
            g10, g60, prev = [], [], start
            for t in sorted(recv[sym]) + [stop]:
                t = min(t, stop)
                gap = (t - max(prev, start)) / 1e9
                if gap > 10:
                    g10.append(round(gap))
                    if gap > 60:
                        g60.append(round(gap))
                prev = max(prev, t)
            r10 = [round(g["seconds"]) for g in rs["feed_gaps_gt10s"]]
            r60 = [round(g["seconds"]) for g in rs["feed_gaps_gt60s"]]
            ok = rs["packets"] == pk_count[sym] and r10 == g10 and r60 == g60
            rep_ok &= ok
            rep_detail.append("%s packets report %d / counted %d, gaps>10s %s/%s, >60s %s/%s"
                              % (sym, rs["packets"], pk_count[sym], r10, g10, r60, g60))
        before = {}
        for k in kept:
            if k in (rep_key, man_key):
                continue
            comp = k[len(run["prefix"]):].split("/", 1)[0]
            before[comp] = before.get(comp, 0) + 1
        up = rep["uploads"]
        up_ok = all(up.get(c, {}).get("ok") == n for c, n in before.items())
        clean = all(v.get("retried", 0) == 0 and v.get("failed", 0) == 0 and v.get("failed_attempts", 0) == 0
                    for v in up.values())
        rep_ok &= up_ok and clean
        rep_detail.append("uploads ok per prefix report %s / kept-before-report %s; retried/failed all 0: %s"
                          % ({c: up.get(c, {}).get("ok") for c in before}, before, clean))
        late = rep.get("late_records_this_process", 0)
        torn = rep.get("torn_line_repairs_this_process", 0)
        rep_ok &= late == 0 and torn == 0
        hwm_r = rep["spool_high_water_bytes"]
        hwm_s = max((s["spool"] or 0) for s in samples)
        hwm_ok = 0.5 * hwm_s <= hwm_r <= 1.05 * hwm_s
        rep_ok &= hwm_ok
        rep_detail.append("late %d, torn %d; spool high-water report %.1f MB vs 1 s samples %.1f MB (within [0.5, 1.05]: %s)"
                          % (late, torn, hwm_r / 2 ** 20, hwm_s / 2 ** 20, hwm_ok))
    check("I5 report", rep_ok, "; ".join(rep_detail) if rep else "daily report not kept")

    met = json.load(open(os.path.join(run_dir, "metrics.json")))
    crit = []
    crit.append(("P1 zero lost/duplicated packets", res[0][1] and res[1][1],
                 "I1 %s, I2 %s" % (res[0][1], res[1][1])))
    st = met["on_ticks"]["max_ms"]
    crit.append(("P2 on_ticks max stall < 200 ms", st is not None and st < 200,
                 "max %s ms, p99 %s ms, calls >= 200 ms: %s" % (st, met["on_ticks"]["p99_ms"], met["on_ticks"]["over_200ms"])))
    rss = met["peak_rss_mb"]
    crit.append(("P3 peak RSS < 150 MB", rss is not None and rss < 150,
                 "VmHWM %s MB (cgroup memory.peak %s MB)" % (rss, met.get("cgroup_memory_peak_mb"))))
    c2 = met["cpu_fraction_of_one_core"].get("2.0x")
    crit.append(("P4 mean CPU < 40 % of one core at 2x", c2 is not None and c2["mean"] < 0.40,
                 "2x %s; all phases %s" % (c2, met["cpu_fraction_of_one_core"])))
    manifest_rows = []
    mdir = os.path.join(run["root"], "manifest")
    for f in glob.glob(os.path.join(mdir, "*.ndjson")):
        manifest_rows += [json.loads(l) for l in open(f) if l.strip()]
    puts = met["put_latency"]
    first_try = all(r["attempts"] == 1 for r in manifest_rows)
    crit.append(("P5 uploads verified by ETag, no retries",
                 puts["n"] == puts["ok"] == len(manifest_rows) == len(kept) and first_try and res[4][1],
                 "PutObject calls %d, ok %d, manifest rows %d, kept objects %d, all first attempt %s"
                 % (puts["n"], puts["ok"], len(manifest_rows), len(kept), first_try)))
    crit.append(spool_trend(samples, run, met))
    print("REHEARSAL %s  (%s, schedule %s)" % (run["id"], run_dir, run["schedule"]))
    for name, ok, detail in res + crit:
        print("  [%s] %s -- %s" % ("PASS" if ok else "FAIL", name, detail))
    print("  metrics: gzip/segment max %ss mean %ss (raw max %s MB -> gz %s MB, threads %s); PutObject p50 %ss max %ss "
          "(segments max %ss); upload_queue max %s; spool high-water (1 s samples) %s MB"
          % (met["gzip_per_segment"]["max_s"], met["gzip_per_segment"]["mean_s"], met["gzip_per_segment"]["max_raw_mb"],
             met["gzip_per_segment"]["max_gz_mb"], met["gzip_per_segment"]["threads"], puts["p50_s"], puts["max_s"],
             puts["seg_max_s"], met["upload_queue_max"], met["spool_high_water_mb_sampled"]))
    allok = all(ok for _, ok, _ in res + crit)
    print("REHEARSAL VERDICT %s" % ("PASS" if allok else "FAIL"))
    return 0 if allok else 1


def spool_trend(samples, run, met):
    seg_s = run["seg_seconds"]
    t0 = samples[0]["t"] if samples else 0
    phases, acc = [], 0.0
    for mult, secs in run["schedule"]:
        phases.append((mult, acc, acc + secs))
        acc += secs
    seg_gz = (met["gzip_per_segment"]["max_gz_mb"] or 0) * 2 ** 20
    out, ok = [], True
    for mult, a, b in phases:
        by = {}
        for s in samples:
            if a <= s["el"] < b and s["spool"] is not None:
                by.setdefault(seg_of(s["t"], seg_s), []).append(s["spool"])
        slots = sorted(by)
        full = [k for k in slots if len(by[k]) >= 0.9 * seg_s]
        if len(full) < 2:
            out.append("%gx: %d full intervals (need 2)" % (mult, len(full)))
            continue
        troughs = [min(by[k]) for k in full]
        peaks = [max(by[k]) for k in full]
        good = troughs[-1] <= troughs[0] + seg_gz and peaks[-1] <= 1.10 * peaks[0]
        ok &= good
        out.append("%gx: troughs %s MB, peaks %s MB" % (mult, [round(x / 2 ** 20, 1) for x in troughs],
                                                         [round(x / 2 ** 20, 1) for x in peaks]))
    return ("P6 spool does not trend upward", ok, "; ".join(out))


if __name__ == "__main__":
    sys.exit(main())
