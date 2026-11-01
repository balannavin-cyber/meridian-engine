#!/usr/bin/env python3
"""Tape T0 mutant harness (docs/tape/T0_plan.md §8).

For each mutant: copy the tape tree to a temp dir, apply ONE exact-string patch (it must match
exactly once -- "MUTANT NOT APPLIED" is a FAIL, never a skip), run the named guard against the copy
with tests/test_tape_t0.py --root, and require FAIL. The control (unpatched copy) must PASS.

  python3 tests/tape_mutants.py [--repeat N] [--only M-T0-...]

Last line: "TAPE T0 MUTANTS PASS (36/36 caught xN, 20/20 controls xN)" or FAIL. Exit 0 / 1.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY = ["merdian_compute", "services", "tests/test_tape_t0.py"]

M = [
    ("M-T0-MID-RULE-FLIPPED", "classify-synthetic", "merdian_compute/tape/classify.py",
     "    if p > mid:\n        return Trade(dv, BUY, price)\n    if p < mid:\n        return Trade(dv, SELL, price)\n",
     "    if p > mid:\n        return Trade(dv, SELL, price)\n    if p < mid:\n        return Trade(dv, BUY, price)\n"),
    ("M-T0-UNCL-DROPPED", "classify-synthetic", "merdian_compute/tape/classify.py",
     '            row["uncl_qty"] += trade.qty\n', "            pass\n"),
    ("M-T0-WALLCLOCK", "classify-purity", "merdian_compute/tape/classify.py",
     "from collections import namedtuple\n",
     "import time\nfrom collections import namedtuple\n_LOADED_AT = time.time()\n"),
    ("M-T0-NO-ROTATE", "segments-rotate", "services/tape_runner/segments.py",
     "        return cur_seg_ns != seg_ns\n", "        return False\n"),
    ("M-T0-DELETE-BEFORE-UPLOAD", "upload-verify", "services/tape_runner/uploader.py",
     '            with open(path, "rb") as body:\n',
     '            os.unlink(path)\n            with open(path, "rb") as body:\n'),
    ("M-T0-ETAG-IGNORED", "upload-verify", "services/tape_runner/uploader.py",
     "            if etag == md5_hex:\n", "            if True:\n"),
    ("M-T0-SHRINK-SUBS", "subs-grow-only", "services/tape_runner/recorder.py",
     '                self._subscribe(sym, su.window_tokens(pos), "grow", now,',
     '                old = [t for t, m in self.subscribed.items() if m["sym"] == sym and m["role"] == "OPT"]\n'
     '                self.ticker.unsubscribe(old)\n'
     '                for t in old:\n'
     '                    del self.subscribed[t]\n'
     '                self._subscribe(sym, su.window_tokens(pos), "grow", now,'),
    ("M-T0-DROP-CTL", "ctl-records", "services/tape_runner/recorder.py",
     '            self._ctl_all("disconnect", now, code=code, reason=self._clean(reason))\n',
     "            pass\n"),
    ("M-T0-DROP-CTL-RECONNECT", "ctl-records", "services/tape_runner/recorder.py",
     '            self._ctl_all("reconnect", now, attempt=attempt)\n', "            pass\n"),
    ("M-T0-CAP-DISABLED", "spool-cap", "services/tape_runner/recorder.py",
     "    def _over_cap(self):\n", "    def _over_cap(self):\n        return False\n"),
    ("M-T0-RESTART-ON-78", "token-fail", "services/tape_runner/tape-runner.service",
     "RestartPreventExitStatus=78 75\n", "RestartPreventExitStatus=75\n"),
    ("M-T0-NO-CLOSED-CHECK", "closed-day", "services/tape_runner/recorder.py",
     "        verdict, source = self._closed_verdict(now)\n", '        verdict, source = "OPEN", "mutant"\n'),
    ("M-T0-CLOSED-BEFORE-0920", "closed-day", "services/tape_runner/config.py",
     'T_CLOSED_CHECK = "09:20"', 'T_CLOSED_CHECK = "09:16"'),
    ("M-T0-CLOSED-ON-SNAPSHOT", "closed-day", "services/tape_runner/recorder.py",
     '        try:\n            keys = [c["ltp_key"] for c in self.symbol_cfg.values()]\n            q = self.kite.quote(keys)\n',
     '        return "CLOSED", "mutant"\n        try:\n            keys = [c["ltp_key"] for c in self.symbol_cfg.values()]\n            q = self.kite.quote(keys)\n'),
    ("M-T0-CLOSED-ONE-WITNESS", "closed-day", "services/tape_runner/recorder.py",
     "        if missing:\n", "        if len(missing) == len(need):\n"),
    ("M-T0-SMOKE-ETAG-IGNORED", "smoke-s3", "services/tape_runner/smoke.py",
     "    if etag == md5.hexdigest():\n", "    if True:\n"),
    ("M-T0-SMOKE-NO-PUT", "smoke-s3", "services/tape_runner/smoke.py",
     "    if s3 is not None:\n        s3_ok = s3_check(", "    if False:\n        s3_ok = s3_check("),
    ("M-T0-TIME-BEFORE-LOCK", "segment-race", "services/tape_runner/recorder.py",
     "        with self.lock:\n            now = self.clock.now_ns()\n            if self.stopping:\n                return\n            try:\n                for pkt in ticks:",
     "        now = self.clock.now_ns()\n        with self.lock:\n            if self.stopping:\n                return\n            try:\n                for pkt in ticks:"),
    ("M-T0-REOPEN-CLOSED", "segment-race", "services/tape_runner/segments.py",
     "        if last is not None and seg_ns <= last:\n", "        if False:\n"),
    ("M-T0-GZ-OVERWRITE", "segment-race", "services/tape_runner/segments.py",
     "    while os.path.exists(dst) or taken(dst):\n", "    while False:\n"),
    ("M-T0-NO-TOKEN-PROBE", "token-midsession", "services/tape_runner/recorder.py",
     "        if self._token_probe_due(now):\n", "        if False:\n"),
    ("M-T0-PROBE-UNDER-LOCK", "token-midsession", "services/tape_runner/recorder.py",
     "            code = self._token_probe(now)      # REST call made WITHOUT the recorder lock\n",
     "            with self.lock:\n                code = self._token_probe(now)\n"),
    ("M-T0-NO-SIGTERM-HANDLER", "sigterm", "services/tape_runner/__main__.py",
     "    signal.signal(signal.SIGTERM, rec.request_stop)\n", "    pass\n"),
    ("M-T0-TERM-NO-CLOSE", "sigterm", "services/tape_runner/recorder.py",
     '            self._ctl_all("error", now, code="SIGTERM", reason="stop requested")\n            self.stopping = True\n            self.connected = False\n            self.writer.close_all()\n',
     '            self._ctl_all("error", now, code="SIGTERM", reason="stop requested")\n            self.stopping = True\n            self.connected = False\n'),
    ("M-T0-NO-NEWLINE-REPAIR", "torn-line", "services/tape_runner/segments.py",
     "            torn = _ends_torn(path)\n", "            torn = False\n"),
    ("M-T0-NO-ONBOOT", "boot-start", "services/tape_runner/tape-runner.timer", "OnBootSec=60\n", ""),
    ("M-T0-EARLY-START-RUNS", "boot-start", "services/tape_runner/recorder.py",
     "            if not clk.at(now, config.T_START):\n", "            if False:\n"),
    ("M-T0-GZIP-ON-WS-THREAD", "gzip-offthread", "services/tape_runner/segments.py",
     "        closed = free_closed_path(cur.path)\n        os.rename(cur.path, closed)\n",
     "        closed = finish_part(cur.path, self.taken)\n"),
    ("M-T0-CLOSED-OVERWRITE", "gzip-offthread", "services/tape_runner/segments.py",
     "    while os.path.exists(dst):\n        n += 1\n        dst = \"%s_c%d%s\" % (base, n, CLOSED)\n", ""),
    ("M-T0-CLOSED-NO-SETTLE", "closed-day", "services/tape_runner/recorder.py",
     "                    and self._feed_settled(now)):\n", "                    and True):\n"),
    ("M-T0-PREFIX-DEFAULT-SET", "rehearsal-hooks-unset", "services/tape_runner/config.py",
     'KEY_PREFIX = os.environ.get("TAPE_KEY_PREFIX", "")', 'KEY_PREFIX = os.environ.get("TAPE_KEY_PREFIX", "_rehearsal/default/")'),
    ("M-T0-KEEP-WHEN-UNSET", "rehearsal-hooks-unset", "services/tape_runner/uploader.py",
     '            if self.keep_dir and not st.get("kept"):', '            if not st.get("kept"):'),
    ("M-T0-FSYNC-UNDER-LOCK", "fsync-offlock", "services/tape_runner/segments.py",
     "        cur.fh.flush()\n        cur.fh.close()      # no fsync here",
     "        cur.fh.flush()\n        os.fsync(cur.fh.fileno())\n        cur.fh.close()      # no fsync here"),
    ("M-T0-NO-FSYNC-BEFORE-GZIP", "fsync-offlock", "services/tape_runner/uploader.py",
     "        sync_file(path)\n        gz = finish_part(path, self.is_taken)",
     "        gz = finish_part(path, self.is_taken)"),
    ("M-T0-NO-MEMORYMAX", "fence", "services/tape_runner/tape-runner.service", "MemoryMax=400M\n", ""),
    ("M-T0-IMPORTS-DHAN", "no-db-no-dhan", "services/tape_runner/recorder.py",
     "import json\n", "import json\nimport dhanhq  # noqa\n"),
]


def make_copy():
    d = tempfile.mkdtemp(prefix="tape_mut_")
    for rel in COPY:
        src = os.path.join(REPO, rel)
        dst = os.path.join(d, rel)
        if os.path.isdir(src):
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    return d


def run_guard(root, guard):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, os.path.join(root, "tests", "test_tape_t0.py"), "--root", root,
                        "--only", guard], capture_output=True, text=True, env=env, timeout=600)
    last = (p.stdout.strip().splitlines() or [""])[-1]
    return p.returncode, last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    muts = [m for m in M if a.only in (None, m[0])]
    ok_all = True
    caught_rows = 0
    for name, guard, rel, old, new in muts:
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
                open(path, "w", encoding="utf-8").write(text.replace(old, new))
                rc, last = run_guard(d, guard)
                if rc != 0 and "FAIL" in last:
                    caught += 1
            finally:
                shutil.rmtree(d, ignore_errors=True)
        row_ok = caught == a.repeat
        caught_rows += row_ok
        ok_all &= row_ok
        print("%s %s guard=%s %d/%d" % ("CAUGHT" if row_ok else "MISSED", name, guard, caught, a.repeat))
    guards = sorted({m[1] for m in muts}, key=[m[1] for m in M].index)
    ctl_rows = 0
    for guard in guards:
        passed = 0
        for _ in range(a.repeat):
            d = make_copy()
            try:
                rc, last = run_guard(d, guard)
                passed += (rc == 0 and "PASS" in last)
            finally:
                shutil.rmtree(d, ignore_errors=True)
        row_ok = passed == a.repeat
        ctl_rows += row_ok
        ok_all &= row_ok
        print("CONTROL %s guard=%s %d/%d" % ("PASS" if row_ok else "FAIL", guard, passed, a.repeat))
    print("TAPE T0 MUTANTS %s (%d/%d caught x%d, %d/%d controls x%d)" % (
        "PASS" if ok_all else "FAIL", caught_rows, len(muts), a.repeat, ctl_rows, len(guards), a.repeat))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
