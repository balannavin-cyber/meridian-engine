#!/usr/bin/env python3
"""Tape live L0 mutant harness (docs/tape/L0_plan.md section 7), same shape as tests/tape_t1b_mutants.py.

For each mutant: copy the tree to a temp dir, apply ONE exact-string patch (it must match exactly once -- "MUTANT NOT
APPLIED" is a FAIL, never a skip), run the named guard against the copy with tests/test_tape_live.py --root, and require
FAIL (exit 1; a rule-23 refusal, exit 2, is NOT a catch). Every repeat also runs each guard's control (an unpatched copy),
which must PASS (exit 0).

  python tests/tape_live_mutants.py [--repeat N] [--only M-L-...]
  (Local, inside 08:30-15:45 IST on a weekday: set TAPE_RULE23_OVERRIDE_R1=1, operator ruling R-1, 2026-11-03)

Last line: "TAPE LIVE MUTANTS PASS (195/195 caught xN, 35/35 controls xN)" or FAIL (61 + 134; the 134 are the stage 2b mutants). Exit 0 / 1.
A mutant named in SKIP is not run where its condition holds and is reported SKIPPED, never counted as caught: on Python < 3.11
M-W-NUL-PASSES is skipped (csv rejects the NUL before the writer, operator ruling 3, 2026-11-22) and the line reads
"PASS (194/194 caught xN, 1 skipped (M-W-NUL-PASSES), 35/35 controls xN)". Its guard still runs as a control.
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
        "docs/tape/L2_live_runner_install.md", "docs/tape/L2_live_runner.service.template", "docs/tape/L2_live_runner.timer.template",
        "docs/tape/L2_live_runner_2b.service.template"]
R, W, WS = "services/tape_live/rules.py", "services/tape_live/writer.py", "services/tape_live/wall_source.py"
LS, LR = "services/tape_live/live_sources.py", "services/tape_live/live_runner.py"
DBS = "services/tape_live/dbshape.py"
DBW = "services/tape_live/dbwrite.py"
T2A, T2B = "docs/tape/L2_live_runner.service.template", "docs/tape/L2_live_runner_2b.service.template"
SCRIPT_LINE = r'''        script = SCRIPT_HEAD + "\n".join(s for _t, s, _n in plan["stmts"]) + "\n" + SCRIPT_TAIL''' + "\n"
V, CLI, SQL = "services/tape_live/verify_day.py", "services/tape_live/cli.py", "sql/2026-11-06_tape_live_tables.sql"
UNTR = '    if f["untraded"]:\n        return ("NO_READ", False, "untraded wall (vendor OI)")\n'
INWIN = '    if not f["in_window"]:\n        return ("NO_READ", False, "wall outside subscribed window")\n'
GRANT_L = "GRANT SELECT ON public.tape_live_label TO tape_ro, merdian_ro;\n"

# name -> (skip when this is true, why). Python < 3.11: csv.writer raises on a NUL in dbshape.line before the writer's own
# refusal is reached, so removing that refusal changes nothing there; 3r asserts the fail-safe crash instead (operator ruling 3).
SKIP = {"M-W-NUL-PASSES": (sys.version_info < (3, 11), "python < 3.11: asserted, not proven able to fail")}

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
    # Stage 2b (docs/tape/L2_live_runner_plan.md section 16; _l2_logs/2b_writer_plan.md section 10): 134 mutants over the 12 live-2b guards (129 + 5 for ruling R9-B)
    # live-2b-off (6)
    ("M-W-OFF-WRITES", "live-2b-off", LR,
     '        if self.writer is not None:\n            self.writer.cycle(T, self.ld if T >= GRID_FIRST else None',
     '        if True:\n            self.writer.cycle(T, self.ld if T >= GRID_FIRST else None'),
    ("M-W-OFF-COLS", "live-2b-off", LR, '            if new:\n                wr.writerow(cols)\n',
     '            if new:\n                wr.writerow(tuple(cols) + ("write_state",))\n'),
    ("M-W-OFF-HB", "live-2b-off", LR, '        if self.writer is not None:\n            hb["write"] = self.writer.status()\n',
     '        hb["write"] = None if self.writer is None else self.writer.status()\n'),
    ("M-W-OFF-STATE-KEYS", "live-2b-off", LR, '        if self.writer is not None:\n            st.update(self.writer.persist())\n',
     '        st["db_written"] = None\n        if self.writer is not None:\n            st.update(self.writer.persist())\n'),
    ("M-W-DSN-IGNORED", "live-2b-off", CLI, '    if wdsn and not a.db_write:\n', '    if False:\n'),
    ("M-W-OFF-LATCH", "live-2b-off", CLI, '    sink = None\n    if a.db_write:\n',
     '    sink = None\n    os.makedirs(out, exist_ok=True)\n    open(os.path.join(out, "WRITE_LATCH.json"), "w").close()\n    if a.db_write:\n'),
    # live-2b-upsert-only (8)
    ("M-W-D-AS-DELETE", "live-2b-upsert-only", DBW, '        stmts = []\n        for t in TABLES:\n',
     '        stmts = []\n        for _k in [k for k in sorted(self.model["tape_live_events"]) if k not in ld.db["tape_live_events"]]:\n'
     '            stmts.append(("tape_live_events", "DE" + "LETE FROM public.tape_live_events WHERE symbol = \'x\';", 1))\n        for t in TABLES:\n'),
    ("M-W-D-AS-UPSERT", "live-2b-upsert-only", DBW,
     '            per[t] = [(k, r) for k, r in sorted(ld.db[t].items()) if self.model[t].get(k) != r]\n',
     '            per[t] = [(k, r) for k, r in sorted(ld.db[t].items()) if self.model[t].get(k) != r]\n'
     '            per[t] += [(k, r) for k, r in sorted(self.model[t].items()) if k not in ld.db[t]]\n'),
    ("M-W-SENDS-STALE", "live-2b-upsert-only", DBW,
     'sorted(ld.db[t].items()) if self.model[t].get(k) != r]', 'sorted(ld.db[t].items()) if k not in self.model[t]]'),
    ("M-W-WRITE-BEFORE-FILES", "live-2b-upsert-only", LR, '            self._emit(_hhmm(T), d)\n            self.last_t = T\n',
     '            if self.writer is not None:\n                self.writer.cycle(T, self.ld, self.stats["missed"], self.fresh_first)\n'
     '            self._emit(_hhmm(T), d)\n            self.last_t = T\n'),
    ("M-W-TRUNCATE-CONST", "live-2b-upsert-only", DBW, 'BATCH_ROWS = 500\n', 'BATCH_ROWS = 500\nRESET_SQL = "TRUNCATE public.tape_live_cycle;"\n'),
    ("M-W-FIFTH-INSERT", "live-2b-upsert-only", DBW,
     r'''    "tape_live_label": "INSERT INTO public.tape_live_label (%s) VALUES\n%s\n%s;",''' + "\n}",
     r'''    "tape_live_label": "INSERT INTO public.tape_live_label (%s) VALUES\n%s\n%s;",''' + "\n"
     + r'''    "tape_live_extra": "INSERT INTO public.tape_live_extra (%s) VALUES\n%s\n%s;",''' + "\n}"),
    ("M-W-LABELS-ALL-EVERY-CYCLE", "live-2b-upsert-only", DBW, 'for k, lab in sorted(ld.labels.items()) if k not in self.labels]',
     'for k, lab in sorted(ld.labels.items())]'),
    ("M-W-LABELS-NOT-SENT", "live-2b-upsert-only", DBW, '                "tape_live_label": new_labels}\n', '                "tape_live_label": []}\n'),
    # live-2b-statements (22)
    ("M-W-TWO-CONNECTIONS", "live-2b-statements", DBW,
     '        _rc, out, cat = self.sink.run_script(script, classify)\n        self.cur["up_proc_s"]',
     '        _rc, out, cat = self.sink.run_script(script, classify)\n        _rc, out, cat = self.sink.run_script(script, classify)\n        self.cur["up_proc_s"]'),
    ("M-W-AUTOCOMMIT", "live-2b-statements", DBW, r'''SCRIPT_TAIL = "COMMIT;\n"''', 'SCRIPT_TAIL = ""'),
    ("M-W-NO-LOCK-TIMEOUT", "live-2b-statements", DBW, r'''\nSET LOCAL lock_timeout = '5s';\n")''', r'''\n")'''),
    ("M-W-NO-SCS", "live-2b-statements", DBW, r'''"SET LOCAL standard_conforming_strings = on;\nSET LOCAL lock_timeout = '5s';\n")''',
     r'''"SET LOCAL lock_timeout = '5s';\n")'''),
    ("M-W-N-IGNORED", "live-2b-statements", DBW, '            for i in range(0, len(rows), self.n):\n                chunk = rows[i:i + self.n]\n',
     '            for i in range(0, len(rows), len(rows) or 1):\n                chunk = rows[i:i + len(rows)]\n'),
    ("M-W-N-HALF", "live-2b-statements", DBW, '            for i in range(0, len(rows), self.n):\n                chunk = rows[i:i + self.n]\n',
     '            for i in range(0, len(rows), max(1, self.n // 2)):\n                chunk = rows[i:i + max(1, self.n // 2)]\n'),
    ("M-W-COLS-RETYPED", "live-2b-statements", DBW, 'stmts.append((t, TEMPLATES[t] % (", ".join(COLUMNS[t]), vals, cf), len(chunk)))',
     'stmts.append((t, TEMPLATES[t] % (", ".join(reversed(COLUMNS[t])), vals, cf), len(chunk)))'),
    ("M-W-CONFLICT-WRONG-TARGET", "live-2b-statements", DBW,
     'CONSTRAINT = dict((t, t + ("_pk" if _DDL[t][1] else "_grain_uq")) for t in TABLES[:3])',
     'CONSTRAINT = dict((t, t + "_grain_uq") for t in TABLES[:3])'),
    ("M-W-EVENTS-NO-TARGET", "live-2b-statements", DBW, '                if t == "tape_live_label":\n                    cf = CONFLICT_FIRST_WINS\n',
     '                if t in ("tape_live_label", "tape_live_events"):\n                    cf = CONFLICT_FIRST_WINS\n'),
    ("M-W-WALL-DO-NOTHING", "live-2b-statements", DBW, '                if t == "tape_live_label":\n                    cf = CONFLICT_FIRST_WINS\n',
     '                if t in ("tape_live_label", "tape_live_wall"):\n                    cf = CONFLICT_FIRST_WINS\n'),
    ("M-W-LABEL-UPDATE", "live-2b-statements", DBW, '                    cf = CONFLICT_FIRST_WINS\n',
     '                    cf = CONFLICT_UPSERT % ("tape_live_label_pk", "label = EXCLUDED.label")\n'),
    ("M-W-LABEL-TARGET", "live-2b-statements", DBW, 'CONFLICT_FIRST_WINS = "ON CONFLICT DO NOTHING"',
     'CONFLICT_FIRST_WINS = "ON CONFLICT ON CONSTRAINT tape_live_label_pk DO NOTHING"'),
    ("M-W-RETURNING", "live-2b-statements", DBW, 'CONFLICT_FIRST_WINS = "ON CONFLICT DO NOTHING"',
     'CONFLICT_FIRST_WINS = "ON CONFLICT DO NOTHING RETURNING 1"'),
    ("M-W-UPDATE-SKIPS-PROV", "live-2b-statements", DBW, 'for c in COLUMNS[t] if c not in keyset))',
     'for c in COLUMNS[t] if c not in keyset and c not in PROV))'),
    ("M-W-NO-DUP-CHECK", "live-2b-statements", DBW, '        if dup:\n            self._write_list("db_dupkeys.csv"',
     '        if False:\n            self._write_list("db_dupkeys.csv"'),
    ("M-W-DUP-TEXT-KEY", "live-2b-statements", DBW, '        if ty == "numeric":\n            return Decimal(v).normalize()\n        if ty in ("bigint", "integer"):\n            return int(v)\n',
     '        if ty in ("numeric", "bigint", "integer"):\n            return v\n'),
    ("M-W-DUP-TS-TEXT-KEY", "live-2b-statements", DBW, '    if ty == "timestamptz":\n        return _instant(v)\n',
     '    if ty == "timestamptz":\n        return v\n'),
    ("M-W-DUP-CHECK-WALL-ONLY", "live-2b-statements", DBW, '        for t, rows in per.items():\n            seen = set()\n',
     '        for t, rows in [(x, y) for x, y in per.items() if x == "tape_live_wall"]:\n            seen = set()\n'),
    ("M-W-QUOTE-NAIVE", "live-2b-statements", DBW, '''    return "'" + value.replace("'", "''") + "'::" + ty''', '''    return "'" + value + "'::" + ty'''),
    ("M-W-EMPTY-AS-TEXT", "live-2b-statements", DBW, '''        return ("''::" + ty) if notnull else "NULL"''', '''        return "''::" + ty'''),
    ("M-W-NUL-PASSES", "live-2b-statements", DBW, '    if "\\x00" in value:\n        raise Refused("other")\n', ''),
    ("M-W-LITCHECK-NOT-READONLY", "live-2b-statements", DBW, 'BEGIN READ ONLY;', 'BEGIN;'),
    # live-2b-metrics (15)
    ("M-W-STMT-TABLE-OFF-BY-ONE", "live-2b-metrics", DBW, 'in zip(plan["stmts"], res):', 'in zip(plan["stmts"][1:], res):'),
    ("M-W-MAX-IS-SUM", "live-2b-metrics", DBW,
     '            self.cur["up_max_stmt_s_" + sh] = max(self.cur["up_max_stmt_s_" + sh], ms / 1000.0)',
     '            self.cur["up_max_stmt_s_" + sh] = self.cur["up_max_stmt_s_" + sh] + ms / 1000.0'),
    ("M-W-ROWS-ARE-INSERTED", "live-2b-metrics", DBW, '            self.cur["up_rows_" + sh] += nrows', '            self.cur["up_rows_" + sh] += n_rep'),
    ("M-W-STMTS-PER-CYCLE", "live-2b-metrics", DBW, '            self.cur["up_stmts_" + sh] += 1', '            self.cur["up_stmts_" + sh] = 1'),
    ("M-W-SKIPPED-ZERO", "live-2b-metrics", DBW, '        self.cur["up_label_skipped"] = sent_l', '        self.cur["up_label_skipped"] = 0'),
    ("M-W-TIMEOUT-AS-OTHER", "live-2b-metrics", DBW, 'STATE_CATEGORY = {"57014": "statement_timeout",', 'STATE_CATEGORY = {"57014": "other",'),
    ("M-W-LOCK-AS-TIMEOUT", "live-2b-metrics", DBW, '"55P03": "lock",', '"55P03": "statement_timeout",'),
    ("M-W-DEADLOCK-AS-OTHER", "live-2b-metrics", DBW, '"40P01": "lock",', '"40P01": "other",'),
    ("M-W-IDLE-AS-OTHER", "live-2b-metrics", DBW, '"25P03": "idle_tx_timeout",', '"25P03": "other",'),
    ("M-W-RLS-AS-OTHER", "live-2b-metrics", DBW, '"42501": "rls_refused",', '"42501": "other",'),
    ("M-W-CONNLIMIT-AS-OTHER", "live-2b-metrics", DBW, '"53300": "connection_limit",', '"53300": "other",'),
    ("M-W-CONNECT-AS-OTHER", "live-2b-metrics", DBW, '    return "connect"\n', '    return "other"\n'),
    ("M-W-UNKNOWN-AS-TIMEOUT", "live-2b-metrics", DBW, '        return STATE_CATEGORY.get(m.group(1), "other")',
     '        return STATE_CATEGORY.get(m.group(1), "statement_timeout")'),
    ("M-W-PROC-TIMEOUT-AS-OTHER", "live-2b-metrics", DBW, '    if rc == 124:\n        return "statement_timeout"\n',
     '    if rc == 124:\n        return "other"\n'),
    ("M-W-CONNLIMIT-BROAD", "live-2b-metrics", DBW, '    if CONN_LIMIT_TEXT in text:\n        return "connection_limit"',
     '    if CONN_LIMIT_TEXT in text or "max clients" in text or "too many" in text:\n        return "connection_limit"'),
    # live-2b-stop (21)
    ("M-W-RLS-SKIPS", "live-2b-stop", DBW, 'SKIP_TIER = ("statement_timeout", "lock", "connect")',
     'SKIP_TIER = ("statement_timeout", "lock", "connect", "rls_refused")'),
    ("M-W-CONNLIMIT-SKIPS", "live-2b-stop", DBW, 'SKIP_TIER = ("statement_timeout", "lock", "connect")',
     'SKIP_TIER = ("statement_timeout", "lock", "connect", "connection_limit")'),
    ("M-W-IDLE-SKIPS", "live-2b-stop", DBW, 'SKIP_TIER = ("statement_timeout", "lock", "connect")',
     'SKIP_TIER = ("statement_timeout", "lock", "connect", "idle_tx_timeout")'),
    ("M-W-OTHER-SKIPS", "live-2b-stop", DBW, 'SKIP_TIER = ("statement_timeout", "lock", "connect")',
     'SKIP_TIER = ("statement_timeout", "lock", "connect", "other")'),
    ("M-W-CONNECT-STOPS", "live-2b-stop", DBW, 'SKIP_TIER = ("statement_timeout", "lock", "connect")', 'SKIP_TIER = ("statement_timeout", "lock")'),
    ("M-W-OVERRUN-NO-STOP", "live-2b-stop", DBW, '        if lag + wall_s > OVERRUN_S:', '        if False:'),
    ("M-W-MISSED-NO-STOP", "live-2b-stop", DBW, '        if missed and not ignore_missed:', '        if False:'),
    ("M-W-FRESH-START-LATCHES", "live-2b-stop", LR, '            self.fresh_first = committed is None\n', '            self.fresh_first = False\n'),
    ("M-W-7A-IGNORED", "live-2b-stop", DBW, '            if excess > REL_EXCESS_7A * med and excess > MIN_EXCESS_S_7A:', '            if False:'),
    ("M-W-7A-EARLY", "live-2b-stop", DBW, 'MIN_CYCLES_7A = 6', 'MIN_CYCLES_7A = 1'),
    # ruling R9-B: one mutant per clause of the item 7a rule (5i0 cases a, e, d, b / b2, b / d)
    ("M-W-7A-WINDOW-ALL", "live-2b-stop", DBW, 'FROM_T_7A = tape_cycle.FIRST_T', 'FROM_T_7A = 0'),
    ("M-W-7A-COUNT-5", "live-2b-stop", DBW, 'MIN_CYCLES_7A = 6', 'MIN_CYCLES_7A = 5'),
    ("M-W-7A-NO-REL", "live-2b-stop", DBW, '            if excess > REL_EXCESS_7A * med and excess > MIN_EXCESS_S_7A:', '            if excess > MIN_EXCESS_S_7A:'),
    ("M-W-7A-NO-ABS", "live-2b-stop", DBW, '            if excess > REL_EXCESS_7A * med and excess > MIN_EXCESS_S_7A:', '            if excess > REL_EXCESS_7A * med:'),
    ("M-W-7A-OR", "live-2b-stop", DBW, '            if excess > REL_EXCESS_7A * med and excess > MIN_EXCESS_S_7A:', '            if excess > REL_EXCESS_7A * med or excess > MIN_EXCESS_S_7A:'),
    ("M-W-STOP-ENDS-RUN", "live-2b-stop", LR, '            self.fresh_first = False\n        self._save_state(T, False)\n',
     '            self.fresh_first = False\n            if self.writer.stopped:\n                raise _Stop(0)\n        self._save_state(T, False)\n'),
    ("M-W-STOP-NOT-LATCHED", "live-2b-stop", DBW, '        lt = read_latch(self.out_root, self.redate)\n        if lt is not None:\n',
     '        lt = None\n        if lt is not None:\n'),
    ("M-W-NO-SENTINEL", "live-2b-stop", DBW, 'os.path.join(self.out_day, "WRITE_STOPPED"), "w"', 'os.path.join(self.out_day, "WRITE_STOP"), "w"'),
    ("M-W-HB-REASON-MISSING", "live-2b-stop", DBW, '"reason": (self.stopped or {}).get("reason"), "skips": self.skips,',
     '"reason": None, "skips": self.skips,'),
    ("M-W-SENTINEL-REMOVED", "live-2b-stop", DBW,
     '            self.latch_day, self.state = lt.get("day"), "stopped"\n            self._sentinel()\n',
     '            self.latch_day, self.state = lt.get("day"), "stopped"\n'
     '            if os.path.exists(os.path.join(self.out_day, "WRITE_STOPPED")):\n'
     '                os.remove(os.path.join(self.out_day, "WRITE_STOPPED"))\n'),
    ("M-W-RETRY-LOOP", "live-2b-stop", DBW, '        if cat != "ok":\n            self._failed(cat, T)\n            return\n        res = parse_output(out)',
     '        if cat != "ok":\n            _rc, out, cat = self.sink.run_script(script, classify)\n            if cat != "ok":\n                self._failed(cat, T)\n'
     '                return\n        res = parse_output(out)'),
    ("M-W-SKIP-LOSES-ROWS", "live-2b-stop", DBW, SCRIPT_LINE,
     '        for t, rows in plan["keep"].items():\n            for k, r in rows:\n                self.model[t][k] = r\n' + SCRIPT_LINE),
    ("M-W-SECOND-SKIP-NO-STOP", "live-2b-stop", DBW, '            if self.skips >= 2:', '            if self.skips >= 3:'),
    ("M-W-SKIPS-NOT-PERSISTED", "live-2b-stop", DBW, '        self.skips = int(st.get("write_skips", 0))', '        self.skips = 0'),
    ("M-W-CLEAR-WHILE-RUNNING", "live-2b-stop", CLI,
     '    if running:\n        day, pid, age, state = running[0]\n', '    if False:\n        day, pid, age, state = running[0]\n'),
    ("M-W-CLEAR-NOOP", "live-2b-stop", CLI, '    os.replace(pth, os.path.join(out, "%s.cleared.%s.json" % (base, stamp)))\n', '    pass\n'),
    # live-2b-latch (11): R8-I, the stop latch is the root file and carries across days
    ("M-W-LATCH-IN-DAY-DIR", "live-2b-latch", DBW,
     '        self.out_root, self.redate, self.latch_day = os.path.dirname(os.path.abspath(out_day)), shift is not None, None\n',
     '        self.out_root, self.redate, self.latch_day = os.path.abspath(out_day), shift is not None, None\n'),
    ("M-W-LATCH-IGNORED-NEXT-DAY", "live-2b-latch", DBW, '        if lt is not None:\n            self.stopped = dict(',
     '        if lt is not None and lt.get("day") == self.day:\n            self.stopped = dict('),
    ("M-W-CHECK-WHEN-LATCHED", "live-2b-latch", CLI, '        if latch is None:\n            try:\n                chk = dbwrite.parse_check(',
     '        if True:\n            try:\n                chk = dbwrite.parse_check('),
    ("M-W-LATCH-NOT-WRITTEN", "live-2b-latch", DBW, '        self._latch()\n        self._sentinel()\n', '        self._sentinel()\n'),
    ("M-W-HB-LATCH-DAY-MISSING", "live-2b-latch", DBW,
     '            out["latch_day"], out["carried"] = self.latch_day, self.latch_day != self.day\n',
     '            out["carried"] = self.latch_day != self.day\n'),
    ("M-W-CLEAR-DAY-ONLY", "live-2b-latch", CLI, 'or (first and name < first) or', 'or (first and name != first) or'),
    ("M-W-CLEAR-KEEPS-LATCH", "live-2b-latch", CLI, '    os.replace(pth, os.path.join(out, "%s.cleared.%s.json" % (base, stamp)))\n',
     '    shutil.copy(pth, os.path.join(out, "%s.cleared.%s.json" % (base, stamp)))\n'),
    ("M-W-LATCH-CORRUPT-OPENS", "live-2b-latch", DBW,
     '        return {"reason": "latch_unreadable", "category": "latch_unreadable", "at": None, "day": None, "set_utc": None}\n',
     '        return None\n'),
    ("M-W-LATCH-FAIL-CRASHES", "live-2b-latch", DBW, '        except OSError:\n            # Disk full or permission: the run must go on',
     '        except ZeroDivisionError:\n            # Disk full or permission: the run must go on'),
    ("M-W-CLEAR-NO-AGE", "live-2b-latch", CLI, '(hb.get("state") in ACTIVE_STATES and (age is None or age < dbwrite.CLEAR_STALE_S))',
     '(hb.get("state") in ACTIVE_STATES)'),
    ("M-W-CLEAR-SCANS-OLDER", "live-2b-latch", CLI, 'or (first and name < first) or', 'or'),
    # live-2b-startup (11)
    ("M-W-ROLE-UNCHECKED", "live-2b-startup", DBW, '    if role != "tape_w":', '    if False:'),
    ("M-W-RO-USER-UNCHECKED", "live-2b-startup", DBW, '    if ro_user is not None and role == ro_user:', '    if False:'),
    ("M-W-SUPER-UNCHECKED", "live-2b-startup", DBW, '    if chk.get("super") != "f" or chk.get("bypassrls") != "f":',
     '    if chk.get("bypassrls") != "f":'),
    ("M-W-BYPASSRLS-UNCHECKED", "live-2b-startup", DBW, '    if chk.get("super") != "f" or chk.get("bypassrls") != "f":',
     '    if chk.get("super") != "f":'),
    ("M-W-PRIV-ONE-TABLE", "live-2b-startup", DBW, '            if chk["priv"].get((t, p)) != "f":',
     '            if t == "tape_live_cycle" and chk["priv"].get((t, p)) != "f":'),
    ("M-W-TRUNCATE-UNCHECKED", "live-2b-startup", DBW, '        for p in P_REMOVAL:\n', '        for p in P_REMOVAL[:1]:\n'),
    ("M-W-INSERT-PRIV-UNCHECKED", "live-2b-startup", DBW, '        if chk["priv"].get((t, P_WRITE)) != "t":', '        if False:'),
    ("M-W-UPDATE-PRIV-UNCHECKED", "live-2b-startup", DBW,
     '        if t != "tape_live_label" and chk["priv"].get((t, P_CHANGE)) != "t":', '        if False:'),
    ("M-W-DAY-UNCHECKED", "live-2b-startup", DBW, '    if chk.get("ist_date") != target:', '    if False:'),
    ("M-W-LOCALDATE-UNCHECKED", "live-2b-startup", DBW, '    if local_today != target:', '    if False:'),
    ("M-W-SCS-UNCHECKED", "live-2b-startup", DBW, '    if chk.get("scs") != "on":', '    if False:'),
    # live-2b-redate (16)
    ("M-W-REDATE-REAL-CLOCK", "live-2b-redate", DBW, '    if clock != "sim":', '    if False:'),
    ("M-W-REDATE-NO-WRITE-FLAG", "live-2b-redate", DBW, '    if not db_write:', '    if False:'),
    ("M-W-REDATE-ENV-UNCHECKED", "live-2b-redate", DBW, '    if env_value != day:', '    if False:'),
    ("M-W-REDATE-DAY-UNCHECKED", "live-2b-redate", DBW, '    if not day < today.isoformat():', '    if False:'),
    ("M-W-REDATE-WEEKDAY", "live-2b-redate", DBW, '    if today.weekday() < 5:', '    if False:'),
    ("M-W-REDATE-TS-ONLY", "live-2b-redate", DBW, '        if c == "trading_day":\n            out[i] = today_iso\n',
     '        if c == "trading_day":\n            pass\n'),
    ("M-W-REDATE-NAMES", "live-2b-redate", DBW, '        elif TYPES[t][c] == "timestamptz" and out[i]:', '        elif c == "ts_ist" and out[i]:'),
    ("M-W-REDATE-EXPIRY", "live-2b-redate", DBW, '        elif TYPES[t][c] == "timestamptz" and out[i]:',
     '        elif (TYPES[t][c] == "timestamptz" or c == "expiry") and out[i]:'),
    ("M-W-REDATE-FILES", "live-2b-redate", CLI,
     '        shift = (today.isoformat(), (today - datetime.strptime(a.day, "%Y-%m-%d").date()).days)\n',
     '        shift = (today.isoformat(), (today - datetime.strptime(a.day, "%Y-%m-%d").date()).days)\n        a.day = today.isoformat()\n'),
    ("M-W-REDATE-IN-TEMPLATE", "live-2b-redate", T2B, '--clock real --db-write --kill-file', '--clock real --db-write --test-redate-today --kill-file'),
    ("M-W-REDATE-IN-2A-TEMPLATE", "live-2b-redate", T2A, '--clock real --kill-file', '--clock real --test-redate-today --kill-file'),
    ("M-W-CLEAR-IN-TEMPLATE", "live-2b-redate", T2B, 'Description=MERIDIAN tape live runner (stage 2b,',
     'Description=MERIDIAN tape live runner write-clear (stage 2b,'),
    ("M-W-REDATE-READS-REAL-LATCH", "live-2b-redate", DBW, '        lt = read_latch(self.out_root, self.redate)\n',
     '        lt = read_latch(self.out_root, False)\n'),
    ("M-W-REDATE-WRITES-REAL-LATCH", "live-2b-redate", DBW, '        pth = latch_path(self.out_root, self.redate)\n',
     '        pth = latch_path(self.out_root, False)\n'),
    ("M-W-CLEAR-PLAIN-CLEARS-REDATE", "live-2b-redate", CLI, '    pth = dbwrite.latch_path(out, a.test_redate)\n',
     '    pth = dbwrite.latch_path(out, True)\n'),
    ("M-W-CLEAR-REDATE-CLEARS-REAL", "live-2b-redate", CLI, '    pth = dbwrite.latch_path(out, a.test_redate)\n',
     '    pth = dbwrite.latch_path(out, False)\n'),
    # live-2b-restart (3)
    ("M-W-RESTART-MODEL-EMPTY", "live-2b-restart", DBW, '        if not fresh and self.db_written is not None:\n            self._rebuild(live_dir)\n',
     '        if False:\n            self._rebuild(live_dir)\n'),
    ("M-W-RESTART-MODEL-COMMITTED", "live-2b-restart", DBW, '        self.db_written = st.get("db_written")\n',
     '        self.db_written = st.get("committed", st.get("db_written"))\n'),
    ("M-W-DBWRITTEN-BEFORE-WRITE", "live-2b-restart", DBW, SCRIPT_LINE, '        self.db_written = T\n' + SCRIPT_LINE),
    # live-2b-grain-uq (6)
    ("M-W-NO-PREFILTER", "live-2b-grain-uq", DBW, '            if holder is not None and holder != pk:', '            if False:'),
    ("M-W-NO-WRITESET-GRAIN", "live-2b-grain-uq", DBW, '            self._hold(pk, g, grain, held)\n            keep_c.append((k, r))\n',
     '            keep_c.append((k, r))\n'),
    ("M-W-GRAIN-COUNT-PER-CYCLE", "live-2b-grain-uq", DBW, '                if g not in self.withheld:\n', '                if True:\n'),
    ("M-W-WITHHELD-NOT-LISTED", "live-2b-grain-uq", DBW,
     '        self._write_list("db_withheld.csv", GRAIN_COLS + ("instrument_token",), sorted(self.withheld.values()))', '        pass'),
    ("M-W-MODEL-APPLIES-D", "live-2b-grain-uq", DBW, '        self.grain, self.held = plan["grain"], plan["held"]\n',
     '        self.grain, self.held = plan["grain"], plan["held"]\n'
     '        live = set(typed("tape_live_cycle", r, KEY_COLS["tape_live_cycle"]) for r in ld.db["tape_live_cycle"].values())\n'
     '        self.grain = dict((g, pk) for g, pk in self.grain.items() if pk in live)\n'),
    ("M-W-UNPREDICTED-SKIPS", "live-2b-grain-uq", DBW, '"23505": "unique"}', '"23505": "lock"}'),
    # live-2b-confined (8)
    ("M-W-WDSN-LEFT-IN-ENV", "live-2b-confined", CLI, 'wdsn = os.environ.pop(W_CONN_ENV, None)  ', 'wdsn = os.environ.get(W_CONN_ENV, None)  '),
    ("M-W-WDSN-IN-ARGV", "live-2b-confined", LS, '        argv = ["psql", "-X", "-f", "-"]\n        try:',
     '        argv = ["psql", "-X", "-f", "-", "-v", "pw=" + self.env["PGPASSWORD"]]\n        try:'),
    ("M-W-STDERR-KEPT", "live-2b-confined", LS, '        cat = classify(rc, err)\n', '        cat = classify(rc, err)\n        if cat != "ok":\n            print(err)\n'),
    ("M-W-ENV-CROSS", "live-2b-confined", LS, '        self.env = w_env(os.environ if base_env is None else base_env, parts)',
     '        self.env = pg_env(os.environ if base_env is None else base_env, parts)'),
    ("M-W-WENV-ALLOWLIST", "live-2b-confined", LS, '    env.update(parts)\n    env["PGCONNECT_TIMEOUT"] = "5"\n    env["PGAPPNAME"] = "tape-live-writer"',
     '    env = dict(base)\n    env.update(parts)\n    env["PGCONNECT_TIMEOUT"] = "5"\n    env["PGAPPNAME"] = "tape-live-writer"'),
    ("M-W-DBWRITE-SUBPROCESS", "live-2b-confined", DBW, 'import statistics\n', 'import statistics\nimport subprocess\n'),
    ("M-W-DBWRITE-SECRET", "live-2b-confined", DBW, 'BATCH_ROWS = 500\n', 'BATCH_ROWS = 500\nDEMO_URL = "https://user:hunter2' + '@example.invalid/x"\n'),
    ("M-W-WRITE-WORD-IN-WRITER", "live-2b-confined", W, 'SYMBOLS = ("NIFTY", "SENSEX")\n',
     'SYMBOLS = ("NIFTY", "SENSEX")\nSTALE_SQL = "DELETE FROM public.tape_live_cycle;"\n'),
    # live-2b-restart-withheld (2)
    ("M-W-RESTART-MODEL-WITHHELD", "live-2b-restart-withheld", DBW,
     '                        if t == "tape_live_cycle" and self._is_withheld(r[1:]):\n', '                        if False:\n'),
    ("M-W-RESTART-EXCLUDES-BY-GRAIN", "live-2b-restart-withheld", DBW,
     '        return w is not None and _norm("bigint", w[-1]) == _norm("bigint", row[IDX["tape_live_cycle"]["instrument_token"]])',
     '        return w is not None'),
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
    skipped = sorted(m[0] for m in sel if SKIP.get(m[0], (False, ""))[0])
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
            if name in skipped:
                print("rep %d %-26s %-20s SKIPPED (%s)" % (rep + 1, name, guard, SKIP[name][1]))
                continue
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
    n_m, n_g = len(sel) - len(skipped), len(guards)
    sk = ", %d skipped (%s)" % (len(skipped), ", ".join(skipped)) if skipped else ""
    if not fails:
        print("TAPE LIVE MUTANTS PASS (%d/%d caught x%d%s, %d/%d controls x%d)" % (n_m, n_m, a.repeat, sk, n_g, n_g, a.repeat))
        return 0
    print("TAPE LIVE MUTANTS FAIL (%d/%d caught%s, %d/%d controls; %s)" % (
        caught, n_m * a.repeat, sk, ctl_ok, n_g * a.repeat, "; ".join(fails[:10])))
    return 1


if __name__ == "__main__":
    sys.exit(main())
