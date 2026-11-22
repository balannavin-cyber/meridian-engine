#!/usr/bin/env python3
"""Stage 2b real-day gate: the memory criterion, fixed before any measurement.

  python tests/tape_live_peak_compare.py --off <flag-off gate log> --on <flag-on gate log> [--margin-mb 100]
  python tests/tape_live_peak_compare.py --off <flag-off gate log> --on <count-mode gate log> --bound-mb <B_day>
  python tests/tape_live_peak_compare.py --selftest

Each log is the output of tests/tape_live_runner_equal.py for the same day and variant (--write none, then --write fake). Per log it reads
  GATE <tag>: replay rc=.. peak_ws_mb=<A>        (process-wide peak after the replay)
  GATE <tag>: runner rc=.. peak_ws_mb=<B>        (the same process-wide peak after the runner: it never falls, so B >= A)
  GATE <tag> PASS | FAIL
Verdict (exit code):
  0 PASS          both gates PASS, the flag-off runner phase set its peak (B_off > A_off), and B_on <= B_off + margin
  1 FAIL          a gate did not PASS, a line is missing, or B_on > B_off + margin
  3 INCONCLUSIVE  B_off == A_off: the replay set the flag-off peak, so the runner's own peak is hidden and the difference would understate
Flag-on minus flag-off is an UPPER BOUND on the writer's memory: the FakeTable, the recorded scripts and their parsed rows are held in the
same process by the test harness and are counted in the flag-on figure. The box's own RSS is a box-only item.

Count mode (--write count; the on-log carries a 'GATE <tag>: write count:' line): the harness keeps nothing per row, so the difference
is the writer's own. Its verdict is B_on <= B_off + B_day, B_day computed by hand before the run (docs/tape/L2_live_runner_plan.md
section 16). The two paths do not mix: a count log needs --bound-mb and never takes --margin-mb; --bound-mb needs a count log.
Either mismatch is rc 2 (refused), never a PASS.
"""
import re
import sys


def text_of(path):
    with open(path, "rb") as fh:
        b = fh.read()
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16", errors="replace")
    return b.decode("utf-8", errors="replace").replace("\x00", "")


def read_log(s):
    a = re.findall(r"GATE (\S+): replay rc=(\S+) [\d.]+ s peak_ws_mb=([\d.]+)", s)
    b = re.findall(r"GATE (\S+): runner rc=(\S+) [\d.]+ s peak_ws_mb=([\d.]+)", s)
    g = re.findall(r"^GATE (\S+) (PASS|FAIL)", s, re.M)
    if len(a) != 1 or len(b) != 1 or len(g) != 1:
        return None
    count = re.search(r"^GATE \S+: write count: ", s, re.M) is not None
    return {"tag": g[0][0], "gate": g[0][1], "A": float(a[0][2]), "B": float(b[0][2]), "count": count}


def verdict(off_s, on_s, margin=100.0, bound=None):
    """margin: the +margin path (fake log). bound: B_day (count log). Exactly one applies, chosen by the on-log."""
    off, on = read_log(off_s), read_log(on_s)
    if off is None or on is None:
        return 1, "FAIL: a log lacks its replay / runner / gate line (off %s, on %s)" % (off is not None, on is not None)
    if off["count"]:
        return 2, "REFUSED: the flag-off log is a count-mode log"
    if on["count"] and bound is None:
        return 2, "REFUSED: a count-mode log is judged against --bound-mb B_day only, never the +%.0f MB margin" % margin
    if bound is not None and not on["count"]:
        return 2, "REFUSED: --bound-mb applies to a count-mode log only (this on-log has no 'write count:' line)"
    if off["tag"] != on["tag"]:
        return 1, "FAIL: the logs are for different runs (%s vs %s)" % (off["tag"], on["tag"])
    if off["gate"] != "PASS" or on["gate"] != "PASS":
        return 1, "FAIL: gate off=%s on=%s" % (off["gate"], on["gate"])
    if not off["B"] > off["A"]:
        return 3, "INCONCLUSIVE: flag-off peak %.1f MB after the runner == %.1f MB after the replay (the replay set the peak)" % (off["B"], off["A"])
    d = on["B"] - off["B"]
    if bound is not None:
        if d > bound:
            return 1, "FAIL: count-mode peak %.1f MB - flag-off %.1f MB = %+.1f MB > B_day %.1f MB" % (on["B"], off["B"], d, bound)
        return 0, "PASS: count-mode peak %.1f MB - flag-off %.1f MB = %+.1f MB <= B_day %.1f MB (flag-off: replay %.1f, runner %.1f)" % (
            on["B"], off["B"], d, bound, off["A"], off["B"])
    if d > margin:
        return 1, "FAIL: flag-on peak %.1f MB - flag-off %.1f MB = %+.1f MB > %.0f MB" % (on["B"], off["B"], d, margin)
    return 0, "PASS: flag-on peak %.1f MB - flag-off %.1f MB = %+.1f MB <= %.0f MB (flag-off: replay %.1f, runner %.1f; upper bound, includes the FakeTable)" % (
        on["B"], off["B"], d, margin, off["A"], off["B"])


def log(tag, a, b, gate="PASS", count=False):
    w = ("GATE %s: write count: 75 scripts, rows sent {}, withheld (grain_uq, reported) 0, count checks PASS; shell deep size 1.0 KB\n" % tag
         if count else "")
    return "GATE %s: replay rc=0 10 s peak_ws_mb=%s\nGATE %s: runner rc=0 10 s peak_ws_mb=%s\n%sGATE %s %s\n" % (tag, a, tag, b, w, tag, gate)


def selftest():
    t = "2026-11-04_clean"
    off = log(t, 350.0, 400.0)
    cases = [
        ("within the margin", off, log(t, 350.0, 480.0), 0),
        ("exactly at the margin", off, log(t, 350.0, 500.0), 0),
        ("over the margin", off, log(t, 350.0, 500.1), 1),
        ("flag-off runner did not set the peak", log(t, 400.0, 400.0), log(t, 400.0, 420.0), 3),
        ("flag-on gate FAIL", off, log(t, 350.0, 420.0, "FAIL"), 1),
        ("a line missing", off, "GATE %s PASS\n" % t, 1),
        ("different runs", off, log("2026-11-05_clean", 350.0, 420.0), 1),
        ("UTF-16 log (what Tee-Object writes)", None, None, 0),
        # count mode: (name, off, on, want, bound)
        ("count: within B_day", off, log(t, 350.0, 430.0, count=True), 0, 30.0),
        ("count: over B_day", off, log(t, 350.0, 430.1, count=True), 1, 30.0),
        ("count: log without --bound-mb (no margin path)", off, log(t, 350.0, 401.0, count=True), 2, None),
        ("count: --bound-mb with a fake log", off, log(t, 350.0, 401.0), 2, 30.0),
    ]
    bad = []
    for case in cases:
        name, o, n, want = case[:4]
        bound = case[4] if len(case) > 4 else None
        if o is None:
            import os
            import tempfile
            d = tempfile.mkdtemp()
            po, pn = os.path.join(d, "o.log"), os.path.join(d, "n.log")
            for p, s in ((po, off), (pn, log(t, 350.0, 450.0))):
                with open(p, "wb") as fh:
                    fh.write(b"\xff\xfe" + s.encode("utf-16-le"))
            o, n = text_of(po), text_of(pn)
        rc, msg = verdict(o, n, 100.0, bound)
        print("SELFTEST %-40s rc=%d (want %d) %s" % (name, rc, want, msg[:70]))
        if rc != want:
            bad.append(name)
    print("PEAK COMPARE SELFTEST %s (%d/%d)" % ("PASS" if not bad else "FAIL: " + ", ".join(bad), len(cases) - len(bad), len(cases)))
    return 0 if not bad else 1


def main():
    argv = sys.argv[1:]
    if "--selftest" in argv:
        return selftest()
    if "--off" not in argv or "--on" not in argv:
        print(__doc__)
        return 2
    if "--margin-mb" in argv and "--bound-mb" in argv:
        print("PEAK COMPARE REFUSED: --margin-mb and --bound-mb do not combine (fake log: margin; count log: B_day)")
        return 2
    margin = float(argv[argv.index("--margin-mb") + 1]) if "--margin-mb" in argv else 100.0
    bound = float(argv[argv.index("--bound-mb") + 1]) if "--bound-mb" in argv else None
    rc, msg = verdict(text_of(argv[argv.index("--off") + 1]), text_of(argv[argv.index("--on") + 1]), margin, bound)
    print("PEAK COMPARE " + msg)
    return rc


if __name__ == "__main__":
    sys.exit(main())
