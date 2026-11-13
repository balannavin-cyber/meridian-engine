#!/usr/bin/env python3
"""Tape live L0 mutant harness (docs/tape/L0_plan.md section 7), same shape as tests/tape_t1b_mutants.py.

For each mutant: copy the tree to a temp dir, apply ONE exact-string patch (it must match exactly once -- "MUTANT NOT
APPLIED" is a FAIL, never a skip), run the named guard against the copy with tests/test_tape_live.py --root, and require
FAIL (exit 1; a rule-23 refusal, exit 2, is NOT a catch). Every repeat also runs each guard's control (an unpatched copy),
which must PASS (exit 0).

  python tests/tape_live_mutants.py [--repeat N] [--only M-L-...]
  (Local, inside 08:30-15:45 IST on a weekday: set TAPE_RULE23_OVERRIDE_R1=1, operator ruling R-1, 2026-11-03)

Last line: "TAPE LIVE MUTANTS PASS (61/61 caught xN, 23/23 controls xN)" or FAIL. Exit 0 / 1.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPY = ["merdian_compute", "services", "sql/2026-11-06_tape_live_tables.sql", "tests/test_tape_live.py", "tests/tape_live",
        "tests/tape_live_mutants.py", "tests/tape_live_runner_equal.py", "tests/run_offline.sh", "docs/tape/L2_live_runner_plan.md",
        "docs/tape/L2_live_runner_install.md", "docs/tape/L2_live_runner.service.template", "docs/tape/L2_live_runner.timer.template"]
R, W, WS = "services/tape_live/rules.py", "services/tape_live/writer.py", "services/tape_live/wall_source.py"
LS, LR = "services/tape_live/live_sources.py", "services/tape_live/live_runner.py"
DBS = "services/tape_live/dbshape.py"
V, CLI, SQL = "services/tape_live/verify_day.py", "services/tape_live/cli.py", "sql/2026-11-06_tape_live_tables.sql"
UNTR = '    if f["untraded"]:\n        return ("NO_READ", False, "untraded wall (vendor OI)")\n'
INWIN = '    if not f["in_window"]:\n        return ("NO_READ", False, "wall outside subscribed window")\n'
GRANT_L = "GRANT SELECT ON public.tape_live_label TO tape_ro, merdian_ro;\n"

M = [
    ("M-L-HIT-ABSORBED-SWAPPED", "live-vectors", R,
     '        if f["C"] and f["N"]:\n            return ("HIT", False, "")\n        if f["C"]:\n            return ("ABSORBED", False, "")\n',
     '        if f["C"] and f["N"]:\n            return ("ABSORBED", False, "")\n        if f["C"]:\n            return ("HIT", False, "")\n'),
    ("M-L-NOREAD-AS-QUIET", "live-vectors", R,
     '        return ("NO_READ", False, "flow not yet evaluable")\n', '        return ("QUIET", False, "")\n'),
    ("M-L-C-WHEN-NOT-EVALUABLE", "live-vectors", R, '    if f["thin_evaluable"]:\n        if f["N"]:\n',
     '    if f["thin_evaluable"]:\n        if f["C"]:\n            return ("ABSORBED", True, "flow n/a")\n        if f["N"]:\n'),
    ("M-L-ORDER-CHANGED", "live-vectors", R, INWIN + UNTR, UNTR + INWIN),
    ("M-L-UNTRADED-REMOVED", "live-vectors", R, UNTR, ""),
    ("M-L-LOOKBACK-10", "live-derive", R, "LOOKBACK_MIN = 15\n", "LOOKBACK_MIN = 10\n"),
    ("M-L-LOOKBACK-20", "live-derive", R, "LOOKBACK_MIN = 15\n", "LOOKBACK_MIN = 20\n"),
    ("M-L-BID-COUNTED", "live-derive", R, 'elif e["kind"] == "THIN" and e["side"] == "ask":', 'elif e["kind"] == "THIN":'),
    ("M-L-EVAL-11", "live-derive", R, "CONC_MIN_PRIOR = 12\n", "CONC_MIN_PRIOR = 11\n"),
    ("M-L-UNTRADED-ALWAYS", "live-derive", R, 'f["trades_cum"] == 0 and tm >= UNTRADED_FROM_MIN', 'f["trades_cum"] == 0'),
    ("M-L-READS-DEPTH", "live-rule-inputs", R, "def derive_flags(cycle_rows, events, wall_row, T, wall):\n",
     "def derive_flags(cycle_rows, events, wall_row, T, wall, depth=None):\n"),
    ("M-L-WALL-NEXT-RUN", "live-wall-floor", WS, '        if _floor5(r["ts_ist"]) <= tm:\n',
     '        if _floor5(r["ts_ist"]) <= tm + 5:\n'),
    ("M-L-LABEL-OVERWRITE", "live-first-wins", W, "        if key in self.labels:\n            return\n", ""),
    ("M-L-DROPS-LATE-SEGMENT", "live-equal-offline", W,
     '            self._rebuild_sym(sym, {"trigger": "late_segment", "at": at, "file": "%s/%s" % (sym, name)})\n',
     "            self.known[sym].pop()\n"),
    ("M-L-CUM-RESET-AT-SEGMENT", "live-equal-offline", W, "        rp = self.rp[sym]\n",
     "        rp = self.rp[sym] = self._new_replay(sym)\n"),
    ("M-L-USES-FUTURE-BIN", "live-causal", R, '        if lo < _min(e["ts_ist"]) <= tm:\n',
     '        if lo < _min(e["ts_ist"]) <= tm + 5:\n'),
    ("M-L-VERIFY-IGNORES-DIFF", "live-verify", V, "                if got == fl:\n", "                if True:\n"),
    ("M-L-NONDETERMINISTIC", "live-deterministic", W, "    return str(uuid.uuid5(uuid.NAMESPACE_URL, \"meridian-tape-live:%s:%s:%s:%d\"",
     "    return str(uuid.uuid4()) or str(uuid.uuid5(uuid.NAMESPACE_URL, \"meridian-tape-live:%s:%s:%s:%d\""),
    ("M-L-JOINS-OUTCOMES", "live-no-outcomes", V, "CAUSES = (", 'OUTCOME_COLS = ("spot_close", "straddle_atm")\nCAUSES = ('),
    ("M-L-WRITES-SIX-TABLES", "live-isolated", W, 'SYMBOLS = ("NIFTY", "SENSEX")\n',
     'SYMBOLS = ("NIFTY", "SENSEX")\nTARGET_TABLE = "tape_strike_cycle"\n'),
    ("M-L-IMPORTS-SUPABASE", "live-isolated", CLI, "def code_info():\n",
     "def code_info():\n    if False:\n        import supabase  # noqa: F401\n"),
    ("M-L-SQL-ANON-GRANT", "live-sql", SQL, GRANT_L, GRANT_L + "GRANT SELECT ON public.tape_live_label TO anon;\n"),
    ("M-L-TS-NOT-NORMALISED", "live-ts-width", WS, '    return "%s.%s%s" % (m.group(1), frac.ljust(6, "0"), m.group(3))\n',
     "    return s\n"),
    ("M-L-TS-TRUNCATES", "live-ts-width", WS, 'frac.ljust(6, "0")', 'frac[:3].ljust(3, "0")'),
    # R-F step one (docs/tape/L2_rebuild_scope_plan.md section 4)
    ("M-L-REBUILD-BOTH", "live-rebuild-scope", W,
     "            if sym in self.rp and self._filtered(meta, sym) != self._filtered(old, sym):\n",
     "            if sym in self.rp:\n"),
    ("M-L-REBUILD-NONE", "live-rebuild-scope", W,
     '                self.dirty[sym] = {"trigger": "subscriptions", "at": at, "file": name}\n', "                pass\n"),
    ("M-L-FILTER-FULL-MAP", "live-rebuild-scope", W,
     "        return replay.SymbolReplay(sym, self.day, meta, self.win).meta\n", "        return meta\n"),
    ("M-L-DIRTY-REBUILDS-AT-SEGMENT", "live-rebuild-scope", W,
     "        if sym in self.dirty:\n            return\n",
     "        if sym in self.dirty:\n            self._rebuild_dirty()\n            return\n"),
    # L2 live runner, Phase A (docs/tape/L2_live_runner_plan.md section 9)
    ("M-R-S3-WRITE", "live-runner-readonly", LS,
     '"s3api", "get-object", "--bucket", self.bucket, "--key", key]', '"s3api", "put-object", "--bucket", self.bucket, "--key", key]'),
    ("M-R-SQL-WRITE", "live-runner-readonly", WS, '    "LIMIT 5000;\\n"\n',
     '    "LIMIT 5000;\\n"\n    "DELETE FROM public.gex_strike_snapshots;\\n"\n'),
    ("M-R-SHELL-TRUE", "live-runner-readonly", LS, "shell=False, check=False", "shell=True, check=False"),
    ("M-R-CRED-IN-ARGV", "live-runner-readonly", LS, '"-v", "ON_ERROR_STOP=1"]\n',
     '"-v", "ON_ERROR_STOP=1", "-v", "privs=" + self.env["PGPASSWORD"]]\n'),
    ("M-R-STDERR-RAW", "live-runner-secrets", LS, "        raise SourceError(classify(rc, err, other))\n",
     '        raise SourceError(classify(rc, err, other) + " " + (err or b"").decode("utf-8", "replace"))\n'),
    ("M-R-DSN-LEFT-IN-ENV", "live-runner-secrets", CLI, "dsn = os.environ.pop(RO_CONN_ENV, None)",
     "dsn = os.environ.get(RO_CONN_ENV, None)"),
    ("M-R-NO-LIMIT", "live-runner-bounded-sql", WS, '    "LIMIT 5000;\\n"\n', '    ";\\n"\n'),
    ("M-R-NO-TIMEOUT", "live-runner-bounded-sql", WS,
     "    \"SET LOCAL statement_timeout = '8s';\\n\"\n    \"SET LOCAL TIME ZONE 'UTC';\\n\"\n    \"SELECT run_id, symbol",
     "    \"SET LOCAL TIME ZONE 'UTC';\\n\"\n    \"SELECT run_id, symbol"),
    ("M-R-SELECT-STAR", "live-runner-bounded-sql", WS, '    "SELECT run_id, symbol, ts, expiry_date, strike, oi_call, oi_put, gex_cr\\n"\n',
     '    "SELECT *\\n"\n'),
    ("M-R-KEYSET-GE", "live-runner-keyset", WS, "            if k > ck and av <= until:\n", "            if k >= ck and av <= until:\n"),
    ("M-R-KEYSET-TS-ONLY", "live-runner-keyset", LR, "cur = self.cursor[sym] = wall_source.cursor_of(page[-1])",
     'cur = self.cursor[sym] = (page[-1]["ts"], "0001-01-01", "-1", "")'),
    ("M-R-NO-COUNT-CHECK", "live-runner-keyset", LR,
     "            if self.src.count_upto(sym, cur, until) != self.acc.count_upto(sym, cur):\n", "            if False:\n"),
    ("M-R-SUBS-AFTER-SEGS", "live-runner-equal", LR, "order.append(((0, replay.sub_sort_key(", "order.append(((2, replay.sub_sort_key("),
    ("M-R-NO-CHAIN-WAIT", "live-runner-equal", LR,
     "            if all(v is not None for v in lag.values()) or now + self.cfg.poll_s > deadline or polls >= 8 or self._stopped():\n",
     "            if True:\n"),
    ("M-R-FAKE-TS-UNPADDED", "live-runner-equal", "tests/test_tape_live.py", '"." + m.group(2).ljust(6, "0")', '"." + m.group(2)'),
    ("M-R-S3-LM-NOT-NORMALISED", "live-runner-equal", LS, "datetime.fromisoformat(s3_last_modified_iso(o.last_modified))",
     "datetime.fromisoformat(o.last_modified)"),
    ("M-R-KILL-IGNORED", "live-runner-lifecycle", LR, '        return self.cfg.term["hit"] or os.path.exists(self.cfg.kill_file)\n',
     '        return self.cfg.term["hit"]\n'),
    ("M-R-NO-SELF-EXIT", "live-runner-lifecycle", LR, "for T in range(T0, self.cfg.end_t + 1, 5):",
     "for T in range(T0, self.cfg.end_t + 61, 5):"),
    ("M-R-TIGHT-RETRY", "live-runner-lifecycle", LR, '                self._err("s3_list", exc.category)\n                infos = []\n',
     '                self._err("s3_list", exc.category)\n                infos = self.objs.list(prefix)\n'),
    ("M-R-MEMERR-EXIT-0", "live-runner-lifecycle", LR, '            self._hb("memory_error")\n            return 3\n',
     '            self._hb("memory_error")\n            return 0\n'),
    ("M-R-RESTART-IGNORES-JOURNAL", "live-runner-restart", LR, "        self._journal_load()\n        objs = ", "        objs = "),
    ("M-R-METRICS-SNAPSHOT-LATE", "live-runner-lifecycle", LR, "        n_late = len(self.ld.late)\n",
     "        n_reb = len(self.ld.rebuilds)\n        n_late = len(self.ld.late)\n"),
    # Phase B (docs/tape/L2_live_runner_plan.md sections 4 and 9): epochs and the DB shape
    ("M-L-ID-EVERY-CYCLE", "live-epoch", W, '        out["db"] = self._db_cycle(as_of)\n',
     '        for s_ in SYMBOLS:\n            self.epoch[s_] += 1\n        out["db"] = self._db_cycle(as_of)\n'),
    ("M-L-OLD-ROWS-KEPT", "live-epoch", W,
     '            for k in sorted(set(old) - set(cur)):\n                lines.append("D," + dbshape.line(old[k]))\n',
     '            for k in sorted(set(old) - set(cur)):\n'
     '                s_ = old[k][1] if t != "tape_live_wall" else old[k][0]\n'
     '                if s_ in self._bumped:\n'
     '                    cur[k] = old[k][:-2] + [self.live_run_id(s_), self.code_sha]\n'
     '                    lines.append("U," + dbshape.line(cur[k]))\n'
     '                    continue\n'
     '                lines.append("D," + dbshape.line(old[k]))\n'),
    ("M-L-ID-NOT-BUMPED", "live-epoch", W, "        self.epoch[sym] += 1\n", "        self.epoch[sym] += 0\n"),
    ("M-L-ID-GLOBAL", "live-epoch", W, "        self.epoch[sym] += 1\n",
     "        for s_ in SYMBOLS:\n            self.epoch[s_] += 1\n"),
    ("M-L-LABELS-FILTERED", "live-epoch", W, '        if t == "tape_live_label":\n            out[t] = list(rows)\n            continue\n', ""),
    ("M-L-NEWEST-PER-TABLE", "live-epoch", W, "    return (trading_day, symbol)\n", "    return (table, trading_day, symbol)\n"),
    ("M-L-TIE-NOT-ASSERTED", "live-epoch", "tests/test_tape_live.py",
     "    return dict((k, v) for k, v in ids.items() if len(v) > 1)\n", "    return {}\n"),
    ("M-L-DROP-NO-BUMP", "live-epoch", W, '                self._bump(sym, "drop", tm if tm is not None else "final")\n',
     "                pass\n"),
    ("M-R-DBSHAPE-DROPS-ASOF", "live-dbshape", DBS, '    return ",".join((("op",) if delta else ()) + COLUMNS[table])\n',
     '    return ",".join((("op",) if delta else ()) + tuple(c for c in COLUMNS[table] if c != "as_of"))\n'),
    ("M-R-DBSHAPE-UTC-DATE", "live-dbshape", DBS, '    return datetime.fromisoformat(ts).astimezone(IST).strftime("%Y-%m-%d")\n',
     '    return datetime.fromisoformat(ts).astimezone(timezone.utc).strftime("%Y-%m-%d")\n'),
    ("M-R-DBSHAPE-ASOF-WALLCLOCK", "live-dbshape", W, "                cur[k] = dbshape.full(data, as_of, rid, self.code_sha)\n",
     '                cur[k] = dbshape.full(data, __import__("datetime").datetime.now(__import__("datetime").timezone.utc)'
     '.isoformat(timespec="seconds"), rid, self.code_sha)\n'),
]


def copy_tree(dst):
    for rel in COPY:
        src = os.path.join(REPO, rel)
        out = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, out, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(src, out)


def patch(root, rel, old, new):
    p = os.path.join(root, rel)
    with open(p, "rb") as fh:
        text = fh.read().decode("utf-8")
    if text.count(old) != 1:
        return False
    with open(p, "wb") as fh:
        fh.write(text.replace(old, new).encode("utf-8"))
    return True


def run_guard(root, guard):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, os.path.join(root, "tests", "test_tape_live.py"), "--root", root, "--only", guard],
                       capture_output=True, text=True, env=env, timeout=1800)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    sel = [m for m in M if a.only in (None, m[0])]
    guards = sorted({m[1] for m in sel})
    caught, ctl_ok, fails = 0, 0, []
    for rep in range(a.repeat):
        for g in guards:
            tmp = tempfile.mkdtemp(prefix="tlm_ctl_")
            try:
                copy_tree(tmp)
                rc, out = run_guard(tmp, g)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            ok = rc == 0
            ctl_ok += ok
            print("rep %d CONTROL %-20s %s" % (rep + 1, g, "PASS" if ok else "FAIL rc=%s %s" % (rc, out[-1:] )))
            if not ok:
                fails.append("control %s rep %d" % (g, rep + 1))
        for name, guard, rel, old, new in sel:
            tmp = tempfile.mkdtemp(prefix="tlm_")
            try:
                copy_tree(tmp)
                if not patch(tmp, rel, old, new):
                    print("rep %d %-26s MUTANT NOT APPLIED (%s)" % (rep + 1, name, rel))
                    fails.append("%s not applied" % name)
                    continue
                rc, out = run_guard(tmp, guard)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            line = next((l for l in out if l.startswith("GUARD ")), out[-1] if out else "")
            ok = rc == 1
            caught += ok
            print("rep %d %-26s %-20s %s  %s" % (rep + 1, name, guard, "CAUGHT" if ok else "MISSED rc=%s" % rc, line[:160]))
            if not ok:
                fails.append("%s rep %d" % (name, rep + 1))
    n_m, n_g = len(sel), len(guards)
    if not fails:
        print("TAPE LIVE MUTANTS PASS (%d/%d caught x%d, %d/%d controls x%d)" % (n_m, n_m, a.repeat, n_g, n_g, a.repeat))
        return 0
    print("TAPE LIVE MUTANTS FAIL (%d/%d caught, %d/%d controls; %s)" % (
        caught, n_m * a.repeat, ctl_ok, n_g * a.repeat, "; ".join(fails[:10])))
    return 1


if __name__ == "__main__":
    sys.exit(main())
