#!/usr/bin/env python3
"""Rule 0 for verify_p7_p8.py: each check must be able to fail for the reason it names.

  python3 selftest_p7_p8.py --p7 <run_dir> [--p8 <run_dir>]

P7 (on a real P7 run, copied to a temp dir): control -> PASS; delete the ctl watchdog line -> FAIL (trip count);
delete one packet -> FAIL (sequence); make the trip late (shift the watchdog ctl 10 s later) -> FAIL (delay);
swap the order of disconnect and connect -> FAIL (order).
P8 (on a real P8 run): control -> PASS; log the closed check 60 s early -> FAIL; log the SESSION closed_check
a minute off -> FAIL.
Last line: "P7/P8 VERIFIER SELFTEST PASS (n/n)" or FAIL.
"""
import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SEG = re.compile(r"^seg_\d{4}.*\.ndjson\.gz$")


def copy_run(run_dir):
    run = json.load(open(os.path.join(run_dir, "run.json")))
    tmp = tempfile.mkdtemp(prefix="reh_self78_")
    out = os.path.join(tmp, "out")
    shutil.copytree(run_dir, out)
    keep = os.path.join(tmp, "keep")
    shutil.copytree(run["keep"], keep)
    run.update(out=out, keep=keep)
    json.dump(run, open(os.path.join(out, "run.json"), "w"))
    return tmp, out, run


def rewrite_segments(run, sym, fn):
    d = os.path.join(run["keep"], run["prefix"], sym, run["day"])
    for name in sorted(os.listdir(d)):
        if SEG.match(name):
            p = os.path.join(d, name)
            lines = gzip.decompress(open(p, "rb").read()).decode().splitlines()
            new = fn(lines)
            if new is not None:
                open(p, "wb").write(gzip.compress(("\n".join(new) + "\n").encode()))


def verify(out, scenario):
    p = subprocess.run([sys.executable, os.path.join(HERE, "verify_p7_p8.py"), "--scenario", scenario, "--run", out],
                       capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def case(label, want_rc, scenario, run_dir, mutate, named=None):
    """A mutated run must make verify return 1 AND the check called `named` must be the one that reports FAIL;
    a crash or a different failing check does not count (that would pass for the wrong reason)."""
    tmp, out, run = copy_run(run_dir)
    try:
        mutate(out, run)
        rc, so, se = verify(out, scenario)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    fails = [l for l in so.splitlines() if l.startswith("FAIL ")]
    if want_rc == 0:
        ok = rc == 0 and not fails and "Traceback" not in se
    else:
        ok = rc == 1 and "Traceback" not in se and any(named in l for l in fails)
    print("%s %s -> rc=%s, failing checks: %s%s" % ("ok" if ok else "XX", label, rc,
                                                    [l[:70] for l in fails] or "none", (" STDERR " + se[-150:]) if se else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--p7")
    ap.add_argument("--p8")
    a = ap.parse_args()
    cells = []
    if a.p7:
        def drop_wd(out, run):
            rewrite_segments(run, "NIFTY", lambda L: [l for l in L if '"ctl":"watchdog"' not in l])

        def drop_pkt(out, run):
            done = [False]

            def f(L):
                if done[0]:
                    return None
                for i, l in enumerate(L):
                    if '"k":"pkt"' in l and '"role":"OPT"' in l:
                        done[0] = True
                        return L[:i] + L[i + 1:]
                return None
            rewrite_segments(run, "NIFTY", f)

        def late_wd(out, run):
            def f(L):
                o = []
                for l in L:
                    if '"ctl":"watchdog"' in l:
                        r = json.loads(l)
                        r["recv_ns"] += 10 * 10 ** 9
                        l = json.dumps(r, separators=(",", ":"))
                    o.append(l)
                return o
            rewrite_segments(run, "NIFTY", f)

        def swap_order(out, run):
            def f(L):
                o = []
                for l in L:
                    if '"ctl":"disconnect"' in l:
                        r = json.loads(l)
                        r["recv_ns"] += 5 * 10 ** 9      # disconnect now AFTER the reconnect's connect
                        l = json.dumps(r, separators=(",", ":"))
                    o.append(l)
                return o
            rewrite_segments(run, "NIFTY", f)
        cells += [case("P7 control", 0, "silent", a.p7, lambda o, r: None),
                  case("P7 watchdog ctl removed", 1, "silent", a.p7, drop_wd, "exactly one watchdog trip"),
                  case("P7 one packet removed", 1, "silent", a.p7, drop_pkt, "sequence contiguous"),
                  case("P7 trip 10 s late", 1, "silent", a.p7, late_wd, "detection delay"),
                  case("P7 disconnect after connect", 1, "silent", a.p7, swap_order, "order watchdog")]
    if a.p8:
        def early_cc(out, run):
            p = os.path.join(out, "driver.log")
            L = open(p).read().splitlines()
            for i, l in enumerate(L):
                if "CLOSED_CHECK verdict=" in l:
                    h, m, s = l.split()[0].split(":")
                    L[i] = "%02d:%02d:%s %s" % (int(h), int(m) - 1, s, l.split(" ", 1)[1])
            open(p, "w").write("\n".join(L) + "\n")

        def wrong_window(out, run):
            p = os.path.join(out, "driver.log")
            s = open(p).read()
            s = re.sub(r"closed_check=(\d\d):(\d\d)", lambda m: "closed_check=%s:%02d" % (m.group(1), (int(m.group(2)) + 1) % 60), s, 1)
            open(p, "w").write(s)
        cells += [case("P8 control", 0, "special", a.p8, lambda o, r: None),
                  case("P8 closed check logged 60 s early", 1, "special", a.p8, early_cc, "closed check at open+5"),
                  case("P8 SESSION closed_check one minute off", 1, "special", a.p8, wrong_window, "calendar window")]
    n = sum(cells)
    print("P7/P8 VERIFIER SELFTEST %s (%d/%d)" % ("PASS" if n == len(cells) and cells else "FAIL", n, len(cells)))
    return 0 if n == len(cells) and cells else 1


if __name__ == "__main__":
    sys.exit(main())
