#!/usr/bin/env python3
"""Rule 0 for the verifier: prove each integrity check can fail for the reason it names.

  python selftest.py --run <out>/<id>

Copies the run (out dir + keep dir) to a temp dir, re-points run.json at the copy, and:
  control            -> verify_rehearsal must PASS every integrity check
  drop one packet    -> I1 sequence must FAIL
  duplicate a packet -> I1 sequence must FAIL
  move a batch's packet into another segment -> I2 batches must FAIL
  rename a segment to _r1                     -> I3 names must FAIL
  flip one byte in a kept subscriptions object -> I4 manifest must FAIL (sha256 is its only check)
  P6 on synthetic samples: one interval -> NOT EVALUATED, flat -> PASS, rising troughs -> FAIL
Last line: VERIFIER SELFTEST PASS (9/9) or FAIL.
"""
import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def copy_run(run_dir):
    run = json.load(open(os.path.join(run_dir, "run.json")))
    tmp = tempfile.mkdtemp(prefix="reh_self_")
    out = os.path.join(tmp, "out", run["id"])
    shutil.copytree(run_dir, out)
    keep = os.path.join(tmp, "keep")
    shutil.copytree(run["keep"], keep)
    root = os.path.join(tmp, "root")
    shutil.copytree(os.path.join(run["root"], "manifest"), os.path.join(root, "manifest"))
    run.update(out=out, keep=keep, root=root)
    json.dump(run, open(os.path.join(out, "run.json"), "w"))
    return tmp, out, run


def segs(run, sym="NIFTY"):
    d = os.path.join(run["keep"], run["prefix"], sym, run["day"])
    return d, sorted(f for f in os.listdir(d) if f.startswith("seg_"))


def rewrite(path, fn):
    lines = gzip.decompress(open(path, "rb").read()).decode().splitlines(True)
    lines = fn(lines)
    open(path, "wb").write(gzip.compress("".join(lines).encode(), mtime=0))


def verify(out):
    p = subprocess.run([sys.executable, os.path.join(HERE, "verify_rehearsal.py"), "--run", out],
                       capture_output=True, text=True)
    return {l.split("] ", 1)[1].split(" --")[0]: l.strip().startswith("[PASS") for l in p.stdout.splitlines()
            if l.strip().startswith("[")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    cases = []

    def case(name, tamper, must_fail):
        tmp, out, run = copy_run(a.run)
        try:
            if tamper:
                tamper(run)
            got = verify(out)
            if must_fail is None:
                ok = all(v for k, v in got.items() if k.startswith("I"))
            else:
                ok = got.get(must_fail) is False
            cases.append((name, ok, {k: v for k, v in got.items() if k.startswith("I")}))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def first_pkt(lines):
        return next(i for i, l in enumerate(lines) if '"k":"pkt"' in l)

    def drop(run):
        d, fs = segs(run)
        rewrite(os.path.join(d, fs[1]), lambda ls: ls[:first_pkt(ls)] + ls[first_pkt(ls) + 1:])

    def dupl(run):
        d, fs = segs(run)
        rewrite(os.path.join(d, fs[1]), lambda ls: ls + [ls[first_pkt(ls)]])

    def move(run):
        d, fs = segs(run)
        taken = []
        rewrite(os.path.join(d, fs[1]), lambda ls: (taken.append(ls[first_pkt(ls)]), ls[:first_pkt(ls)] + ls[first_pkt(ls) + 1:])[1])
        rewrite(os.path.join(d, fs[0]), lambda ls: ls + taken)

    def rename(run):
        d, fs = segs(run)
        os.rename(os.path.join(d, fs[0]), os.path.join(d, fs[0].replace(".ndjson.gz", "_r1.ndjson.gz")))

    def flip(run):
        d = os.path.join(run["keep"], run["prefix"], "session", run["day"])
        p = os.path.join(d, sorted(f for f in os.listdir(d) if f.startswith("subscriptions_"))[0])
        b = bytearray(open(p, "rb").read())
        b[5] ^= 0x01
        open(p, "wb").write(bytes(b))

    case("control", None, None)
    case("drop one packet", drop, "I1 sequence")
    case("duplicate a packet", dupl, "I1 sequence")
    case("move a packet across segments", move, "I2 batches")
    case("rename a segment to _r1", rename, "I3 names")
    case("flip a byte in a kept object", flip, "I4 manifest")
    # P6 on synthetic 1 s spool samples (no run needed): it must be able to PASS, FAIL and abstain
    sys.path.insert(0, HERE)
    from verify_rehearsal import spool_trend
    seg = 300
    met = {"gzip_per_segment": {"max_gz_mb": 10}}

    def samples(n_intervals, trough_step_mb):
        out, t0 = [], 1_793_000_100 * 10 ** 9 // (seg * 10 ** 9) * seg * 10 ** 9   # a boundary
        for k in range(n_intervals * seg):
            iv = k // seg
            mb = trough_step_mb * iv + (k % seg) * 0.8      # saw-tooth: .part grows, rotates
            out.append({"t": t0 + k * 10 ** 9, "el": float(k), "spool": int(mb * 2 ** 20)})
        return out
    for name, n, step, want in (("P6 one full interval -> NOT EVALUATED", 1, 0, None),
                                ("P6 three flat intervals -> PASS", 3, 0, True),
                                ("P6 troughs rising 15 MB/interval -> FAIL", 3, 15, False)):
        run = {"seg_seconds": seg, "schedule": [[2.0, float(n * seg)]]}
        got = spool_trend(samples(n, step), run, met)[1]
        cases.append((name, got is want, {"P6": got}))
    for name, ok, got in cases:
        print("  [%s] %s -> %s" % ("ok" if ok else "XX", name, got))
    n = sum(ok for _, ok, _ in cases)
    print("VERIFIER SELFTEST %s (%d/%d)" % ("PASS" if n == len(cases) else "FAIL", n, len(cases)))
    return 0 if n == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
