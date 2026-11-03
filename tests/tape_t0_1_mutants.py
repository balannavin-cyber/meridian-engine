#!/usr/bin/env python3
"""Tape T0.1 mutant harness (docs/tape/T0_1_plan.md section 4). Same discipline as tests/tape_mutants.py:
copy the tree, apply ONE exact-string patch (it must match exactly once -- "MUTANT NOT APPLIED" is a FAIL,
never a skip), run the named guard of tests/test_tape_t0_1.py against the copy and require FAIL. The control
(the unpatched copy, same guard) must PASS. M1-M8 are the required set; X* are extras, reported separately.

  python3 tests/tape_t0_1_mutants.py [--repeat N] [--only NAME]

Last line: "TAPE T0.1 MUTANTS PASS (8/8 required caught xN, E/E extra caught, C/C controls)" or FAIL.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY = ["merdian_compute", "services", "tests/test_tape_t0.py", "tests/test_tape_t0_1.py", "tests/tape_t1a"]

R = "services/tape_runner/recorder.py"
M = [
    ("M1-WATCHDOG-DISABLED", "wd-trip", R,
     "            self._watchdog(now)\n            self.writer.tick(now)\n", "            self.writer.tick(now)\n", True),
    ("M2-THRESHOLD-MS-NOT-S", "wd-trip", R,
     "threshold = max(config.SILENCE_MIN_S, config.SILENCE_S) * clk.NS\n",
     "threshold = max(config.SILENCE_MIN_S, config.SILENCE_S) * 1_000_000\n", True),
    ("M3-ACTIVE-OUTSIDE-WINDOW", "wd-window", R,
     "if not self.connected or self.ticker is None or now < self._open_ns or now > self._close_ns:\n",
     "if not self.connected or self.ticker is None:\n", True),
    ("M4-CALENDAR-IGNORED", "special-day", "services/tape_runner/session.py",
     '        if e["date"] == day:\n            return derive(e)\n', '        if False:\n            return derive(e)\n', True),
    ("M5-TRIP-NOT-COUNTED", "wd-trip", R,
     "        self.stats.watchdog_trips += 1\n", "        pass\n", True),
    ("M6-COUNTERS-OLD-DEFINITION", "counters", R,
     '            if self.stopping:\n                self.stats.close_at_stop += 1     # our own shutdown close: no ctl line is written, so not a "disconnect"\n            else:\n                self.stats.disconnects += 1\n',
     "            self.stats.disconnects += 1\n", True),
    # M7: on_frame's try/except removed (it re-raises) -> the guard "frame-errors" must FAIL; its control passes unpatched.
    ("M7-ON-FRAME-RAISES", "frame-errors", R,
     "            self._frame_failed(exc)\n", "            raise\n", True),
    # M8: install.sh reads exit 1 (what a SyntaxError / import failure in session.py exits) as "outside" -> the
    # guard block run against a broken session.py proceeds -> the guard "timer-sync" must FAIL; control passes.
    ("M8-INSTALL-GUARD-1-IS-OUTSIDE", "timer-sync", "services/tape_runner/install.sh",
     '  "$OUTSIDE_RC") ;;\n', '  1|"$OUTSIDE_RC") ;;\n', True),
    ("X1-THRESHOLD-X1000", "wd-trip", R,
     "threshold = max(config.SILENCE_MIN_S, config.SILENCE_S) * clk.NS\n",
     "threshold = max(config.SILENCE_MIN_S, config.SILENCE_S) * clk.NS * 1000\n", False),
    ("X2-BACKOFF-FLAT", "wd-backoff", "services/tape_runner/config.py",
     "WD_BACKOFF_S = (1, 2, 4, 8, 15)", "WD_BACKOFF_S = (1,)", False),
    ("X3-NO-OPEN-FLOOR", "wd-window", R,
     "ref = max(self.last_frame_ns or 0, self.connected_since or 0, self._open_ns)\n",
     "ref = max(self.last_frame_ns or 0, self.connected_since or 0)\n", False),
    ("X4-CLOSED-CHECK-OFFSET", "special-day", "services/tape_runner/session.py",
     "OFF_START, OFF_RESOLVE, OFF_OPTIONS, OFF_CLOSED = -25, -20, -15, 5", "OFF_START, OFF_RESOLVE, OFF_OPTIONS, OFF_CLOSED = -25, -20, -15, -5", False),
    ("X5-NO-FORCED-OPEN", "special-day", R,
     '            if (self.win["special"] and self.universe is not None and not self.options_on and self.connected\n',
     '            if (False and self.universe is not None and not self.options_on and self.connected\n', False),
    ("X6-TIMER-PERSISTENT", "timer-sync", "services/tape_runner/session.py",
     '"Persistent=false\\n"', '"Persistent=true\\n"', False),
    ("X7-GUARD-ENDS-AT-CLOSE", "timer-sync", "services/tape_runner/session.py",
     '<= t < _mins(e["close"]) + GUARD_AFTER', '<= t < _mins(e["close"])', False),
    ("X8-LIB-JITTER-ON", "glue", "services/tape_runner/config.py",
     '"maxDelay": 15, "jitter": 0}', '"maxDelay": 15, "jitter": 0.1}', False),
    ("X9-SPECIAL-VERDICT-OFF", "processor-special", "merdian_compute/tape/minute.py",
     "    if special:\n        # G3's early / late split", "    if False:\n        # G3's early / late split", False),
    ("X12-CALENDAR-CLOSE-1530", "fo-close", "services/tape_runner/special_sessions.json",
     '"close": "15:40"', '"close": "15:30"', False),
    ("X11-GUARD-ERROR-READS-OUTSIDE", "timer-sync", "services/tape_runner/session.py",
     '        print("session.py: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)\n        return 2\n',
     '        print("session.py: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)\n        return 1\n', False),
    ("X10-SYNC-KEEPS-STALE", "timer-sync", "services/tape_runner/sync_special_timers.sh",
     '  if [ ! -e "$tmp/$n" ]; then\n', '  if false; then\n', False),
]


def make_copy():
    d = tempfile.mkdtemp(prefix="tape_mut01_")
    for rel in COPY:
        src, dst = os.path.join(REPO, rel), os.path.join(d, rel)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    return d


def run_guard(root, guard):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, os.path.join(root, "tests", "test_tape_t0_1.py"), "--root", root,
                        "--only", guard], capture_output=True, text=True, env=env, timeout=600)
    return p.returncode, (p.stdout.strip().splitlines() or [""])[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    muts = [m for m in M if a.only in (None, m[0])]
    ok_all, req_caught, req_n, ext_caught, ext_n = True, 0, 0, 0, 0
    for name, guard, rel, old, new, required in muts:
        caught = 0
        for _ in range(a.repeat):
            d = make_copy()
            try:
                path = os.path.join(d, rel)
                text = open(path, encoding="utf-8").read()
                n = text.count(old)
                if n != 1:
                    print("MUTANT NOT APPLIED %s (%d matches in %s)" % (name, n, rel))
                    break
                open(path, "w", encoding="utf-8", newline="").write(text.replace(old, new))
                rc, last = run_guard(d, guard)
                caught += (rc != 0 and "FAIL" in last)
            finally:
                shutil.rmtree(d, ignore_errors=True)
        row = caught == a.repeat
        if required:
            req_n += 1
            req_caught += row
            ok_all &= row
        else:
            ext_n += 1
            ext_caught += row
        print("%s %s guard=%s %d/%d%s" % ("CAUGHT" if row else "MISSED", name, guard, caught, a.repeat,
                                          "" if required else " (extra)"))
    guards = sorted({m[1] for m in muts})
    ctl_ok = 0
    for guard in guards:
        passed = 0
        for _ in range(a.repeat):
            d = make_copy()
            try:
                rc, last = run_guard(d, guard)
                passed += (rc == 0 and "PASS" in last)
            finally:
                shutil.rmtree(d, ignore_errors=True)
        row = passed == a.repeat
        ctl_ok += row
        ok_all &= row
        print("CONTROL %s guard=%s %d/%d" % ("PASS" if row else "FAIL", guard, passed, a.repeat))
    ok_all &= (ext_caught == ext_n)
    print("TAPE T0.1 MUTANTS %s (%d/%d required caught x%d, %d/%d extra caught, %d/%d controls x%d)" % (
        "PASS" if ok_all else "FAIL", req_caught, req_n, a.repeat, ext_caught, ext_n, ctl_ok, len(guards), a.repeat))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
