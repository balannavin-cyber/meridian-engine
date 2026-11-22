#!/usr/bin/env python3
"""Stage 2b, real-day gate with the fake writer: the run helper, the write-path assertions, and their self-test.

  python tests/tape_live_write_checks.py --selftest      (the default fixture: each assertion must fire on a planted fault)

tests/tape_live_runner_equal.py --write fake runs `cli live --db-write` with live_sources.RUN replaced by the guard suite's own
FakeWriteShell over a FakeTable (no DSN, no database, no network), then calls write_checks(). The assertions, each tagged:
  W0  the run wrote: at least one script, one table snapshot per script
  W1  rows sent: every script's rows per table == the U lines of its cycle's .db.csv files, and its labels == that cycle's new labels;
      every cycle that has U lines was written
  W2  after every script the FakeTable (what the database would hold, old epochs included) == the U-only state of the files
      through that cycle (the same-as-D-applied part is db_checks (ii), which compares the newest view of that U-only state)
  W3  no script carries two rows with one database conflict key per table (compared by DB-typed value, NULL = NULL)
  W4  no write skips and no stop: heartbeat write state, skips == 0, every write_state sent|none, no werr_* count, db_written == final
Read-only on everything but its own out dir. Exit 0 PASS, 1 FAIL.

Count mode (tests/tape_live_runner_equal.py --write count): the same runner argv with the CountShell in place of the fake. It answers
the writer as the FakeTable would on a clean day and keeps nothing per row (scan_script counts statements and rows over the script
bytes; labels keep a 16-byte digest per key), so the gate's peak measures the writer and not the harness. Asserted: C0, C1 (counts
per script == U-line counts of the cycle's files, labels per cycle) and W4. W1-W3 are NOT run in this mode (they need the scripts).
Self-test S7: the count shell's deep size after the canon run <= SHELL_BOUND_KB, with the fake shell as the control above it.

slice_run() (tests/tape_live_runner_equal.py --write fake --slice-from HH:MM): the runner only, started at HH:MM, no replay, W0 to W4 only.
A slice PASS is W0 to W4 on that slice and NOTHING more: no byte equality with the replay, no offline-batch or D-applied comparison
(db_checks), no memory criterion. It is not a gate PASS.
"""
import contextlib
import copy
import gc
import hashlib
import importlib.util
import os
import re
import shutil
import sys
import time
import types
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IST = timezone(timedelta(hours=5, minutes=30))
_T = {}


def load_ttl():
    """tests/test_tape_live.py as a module (it parses sys.argv at import, so argv is held to its own for that moment)."""
    if "m" not in _T:
        path = os.path.join(ROOT, "tests", "test_tape_live.py")
        spec = importlib.util.spec_from_file_location("ttl_for_write_checks", path)
        mod = importlib.util.module_from_spec(spec)
        saved = sys.argv
        sys.argv = [path]
        try:
            spec.loader.exec_module(mod)
        finally:
            sys.argv = saved
        _T["m"] = mod
    return _T["m"]


class NoRead:
    """The inner shell of a local-source run: nothing may read through RUN."""
    calls, raised = [], []

    def __call__(self, argv, env, stdin, timeout):
        raise AssertionError("a read went through RUN in a local-source run: %r" % (argv[:2],))


def digest(T, tbl):
    """{table: (rows, md5 of the sorted reprs of its typed tuples)}: the FakeTable's content, small enough to keep per script."""
    out = {}
    for t in T.DB_TABLES:
        reps = sorted(repr(x) for x in tbl.tuples(t))
        out[t] = (len(reps), hashlib.md5("\n".join(reps).encode("utf-8")).hexdigest())
    return out


SHELL_BOUND_KB = 256      # by hand (operator, 2026-11-17): a shell that keeps no row of what it is sent stays far below this


def deep_size(root):
    """Bytes reachable from root (sys.getsizeof over gc referents, each object once), not counting classes, modules,
    functions and code: what an instance holds, not the program it runs."""
    skip = (type, types.ModuleType, types.FunctionType, types.BuiltinFunctionType, types.MethodType, types.CodeType)
    seen, stack, total = set(), [root], 0
    while stack:
        o = stack.pop()
        if id(o) in seen or isinstance(o, skip):
            continue
        seen.add(id(o))
        total += sys.getsizeof(o)
        stack.extend(gc.get_referents(o))
    return total


def make_snap(T):
    class Snap(T.FakeWriteShell):
        """FakeWriteShell that keeps (grid minute, ordinal, table digest) after every script."""

        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.snaps = []

        def _apply(self, rec, plant, ordn):
            r = super()._apply(rec, plant, ordn)
            self.snaps.append((rec["T"], ordn, digest(T, self.table)))
            return r
    return Snap


# Count mode: one pass over the script bytes. A quoted literal ('' escapes) is skipped whole, so ( ) ; inside a value never count.
_SCAN = re.compile(rb"'[^']*(?:''[^']*)*'|[();]|INSERT\s+INTO\s+public\.(\w+)")
_KIND = re.compile(rb"(?:[ \t\r\n]*\\[^\n]*\n)*[ \t\r\n]*([A-Za-z]+)")


def scan_script(b):
    """Script bytes -> [(kind, table or None, rows, start, end)] per statement, in order, without decoding or copying the script.
    rows: the parenthesised groups at depth 0 after the column list of an INSERT (0 for other statements)."""
    out, depth, groups, table, start = [], 0, 0, None, 0
    for m in _SCAN.finditer(b):
        c = m.group(0)
        if c[:1] == b"'":
            continue
        if m.group(1) is not None:
            if depth == 0:
                table, groups = m.group(1).decode("ascii"), 0
            continue
        if c == b"(":
            depth += 1
            if depth == 1 and table is not None:
                groups += 1
        elif c == b")":
            depth -= 1
        elif depth == 0:                                    # ';' ends a statement
            km = _KIND.match(b, start)
            kind = km.group(1).decode("ascii").upper() if km is not None else ""
            out.append((kind, table, max(0, groups - 1) if table is not None else 0, start, m.end()))
            table, groups, start = None, 0, m.end()
    return out


class CountShell:
    """live_sources.RUN for a memory measurement with the writer on (--write count): answers the write role as the FakeTable would
    for a clean day, and KEEPS NOTHING PER ROW. Per script it keeps (grid minute, ordinal, rows per table); for labels only, a
    16-byte digest of each DB-typed key, so ON CONFLICT DO NOTHING reports what Postgres would (a label key sent before is skipped).
    Cycle, events and wall rows are counted by scan_script and never materialised. Plants: ("n", k) -> {"err": SQLSTATE}."""

    def __init__(self, T, day, plants=None):
        datetime.strptime(day, "%Y-%m-%d")
        self.T, self.day, self.plants = T, day, dict(plants or {})
        types_, _nn = T.sql_types()
        self.ltypes = dict(types_["tape_live_label"])
        self.check = T.w_default_check()
        self.records, self.label_keys, self.nwrite, self.misrouted = [], set(), 0, []
        self.calls, self.raised, self.lit_corrupt = [], [], None

    def _T(self):
        m = int((self.T.rmods()[0].SimClock.last_now - self.T.ist_epoch(0, day=self.day)) // 60)
        return m - m % 5

    def __call__(self, argv, env, stdin, timeout):
        if argv and argv[0] == "psql":
            if env.get("PGPASSWORD") == self.T.W_PW:
                return self._w(stdin)
            if stdin is not None and b"INSERT INTO" in stdin:
                self.misrouted.append(argv[0])
                return 3, b"", b"ERROR:  XX000\n"
        raise AssertionError("a read went through RUN in a local-source run: %r" % (argv[:2],))

    def _w(self, stdin):
        T = self.T
        if b"INSERT INTO" not in stdin:
            if b"READ ONLY" in stdin:
                return T.FakeWriteShell._lit(self, stdin.decode("utf-8"))
            return 0, T.w_check_csv(self.check, self.day).encode(), b""
        self.nwrite += 1
        ordn = self.nwrite
        err = (self.plants.get(("n", ordn)) or {}).get("err")
        if err:
            return 3, b"", ("ERROR:  %s\n" % err).encode()
        if b"\x00" in stdin:
            return 3, b"", b"ERROR:  22021\n"
        stmts = scan_script(stdin)
        counts, lines, per_table, new_keys = {}, ["Timing is on."], {}, set()
        for kind, table, nrows, a, z in stmts:
            if kind != "INSERT":
                lines += [kind, T.pg_time(0.2)]
                continue
            n = nrows
            if table == "tape_live_label":
                ins = T.parse_insert(stdin[a:z].decode("utf-8").strip().rstrip(";"))
                cols, n = ins["cols"], 0
                for vals in ins["rows"]:
                    row = dict(zip(cols, vals))
                    key = tuple(T.pg_norm(self.ltypes[c], row.get(c)) for c in T.W_PK["tape_live_label"])
                    dg = hashlib.md5(repr(key).encode("utf-8")).digest()
                    if dg not in self.label_keys and dg not in new_keys:
                        new_keys.add(dg)
                        n += 1
                del ins
            k = per_table.get(table, 0)
            per_table[table] = k + 1
            counts[table] = counts.get(table, 0) + nrows
            lines += ["INSERT 0 %d" % n, T.pg_time(T.w_dur(table, k, ordn))]
        self.label_keys |= new_keys
        self.records.append((self._T(), ordn, tuple(counts.get(t, 0) for t in T.DB_TABLES)))
        return 0, ("\n".join(lines) + "\n").encode(), b""


def run_live_count(T, day, odir, raw, chain_csvs, start, arrival=None, plants=None, rows=500):
    """run_live_fake with the CountShell in place of the FakeWriteShell (no FakeTable). Same argv."""
    return run_live_fake(T, day, odir, raw, chain_csvs, start, arrival=arrival, plants=plants, rows=rows, shell="count")


def run_live_fake(T, day, odir, raw, chain_csvs, start, arrival=None, plants=None, rows=500, shell="fake"):
    """cli live --source local --chain local --clock sim --db-write, writes to a FakeTable (shell "fake") or to the CountShell
    (shell "count": no table, table is None). -> SimpleNamespace(rc, root, fake, table, log)."""
    cli = T.mods()[0]
    ls = T.rmods()[1]
    dbw = T._dbw()
    if shell == "count":
        tbl, fake = None, CountShell(T, day, plants)
    else:
        tbl = T.FakeTable(day)
        fake = make_snap(T)(NoRead(), tbl, os.path.join(odir, day), plants, None, None, kill_path=os.path.join(odir, "KILL"), day=day)
    argv = ["live", "--day", day, "--out", odir, "--source", "local", "--raw", raw, "--chain", "local", "--clock", "sim",
            "--start", start, "--disk-floor-mb", "20", "--rss-cap-mb", "3000", "--db-write", "--db-batch-rows", str(rows)]
    for p in chain_csvs:
        argv += ["--chain-csv", p]
    if arrival:
        argv += ["--arrival", arrival]
    y, mo, dd = (int(x) for x in day.split("-"))
    saved_run, prev_now = ls.RUN, dbw.now_ist
    ls.RUN = fake
    dbw.now_ist = lambda: datetime(y, mo, dd, 10, 0, 0, tzinfo=IST)
    try:
        with T._env({T.W_ENV: T.W_DSN}, drop=T._AWS_KEYS), T.strict_iso():
            rc, log = T.quiet_exit(cli.main, argv)
    finally:
        ls.RUN, dbw.now_ist = saved_run, prev_now
    return types.SimpleNamespace(rc=rc, out=odir, root=os.path.join(odir, day), fake=fake, table=tbl, log=log, argv=argv)


def _typed(tbl, t, row):
    # empty = NULL, except in a NOT NULL column of the DDL, where '' is the value (plan section 4; guard case 3q)
    return tbl.typed(t, dict((c, None if v == "" and c not in tbl.notnull[t] else v) for c, v in zip(tbl.cols[t], row)))


def _expected_after(T, res, day):
    """-> {cycle name: digest} of the U-only state of the .db.csv files through that cycle (labels: the first row per key wins)."""
    tbl = res.table
    names = T.cycle_names(res)
    state = dict((t, {}) for t in T.DB_TABLES)
    lh, lrows = T.label_rows(res)
    ai = lh.index("as_of")
    done, out = 0, {}
    as_of = T.mods()[0].as_of
    for nm in names:
        for t in T.DELTA_TABLES:
            for r in T.u_rows(res, nm, t):
                typed = _typed(tbl, t, r)
                state[t][tbl._key(t, typed)] = tuple(typed[c] for c in tbl.cols[t])
        upto = None if nm == "final" else as_of(day, int(nm[:2]) * 60 + int(nm[2:]))
        for r in lrows:
            if upto is None or r[ai] <= upto:
                typed = _typed(tbl, "tape_live_label", r)
                state["tape_live_label"].setdefault(tbl._key("tape_live_label", typed), tuple(typed[c] for c in tbl.cols["tape_live_label"]))
        d = {}
        for t in T.DB_TABLES:
            reps = sorted(repr(x) for x in state[t].values())
            d[t] = (len(reps), hashlib.md5("\n".join(reps).encode("utf-8")).hexdigest())
        out[nm] = d
    return out


def write_checks(T, res, day, calls=None):
    """-> list of failure texts (empty = every assertion held). calls: the recorded write scripts (default: the fake's)."""
    bad = []
    tbl = res.table
    calls = T.w_scripts(res) if calls is None else calls
    snaps = dict((s[1], s[2]) for s in res.fake.snaps)
    as_of = T.mods()[0].as_of
    names = T.cycle_names(res)
    lh, lrows = T.label_rows(res)
    ai = lh.index("as_of")
    # W0
    if not calls:
        bad.append("W0 no write script was sent (the assertions would be vacuous)")
    if len(snaps) != len(calls):
        bad.append("W0 %d table snapshots for %d write scripts" % (len(snaps), len(calls)))
    # W1
    matched, name_of = set(), {}
    for c in calls:
        sent = T.sent_rows(c)
        cands = [T._nm(c["T"])] + (["final"] if "final" in names else [])
        ok = None
        for nm in cands:
            if all(sorted(sent.get(t, [])) == sorted(T.u_rows(res, nm, t)) for t in T.DELTA_TABLES):
                ok = nm
                break
        if ok is None:
            bad.append("W1 rows sent: the script of %s != the U lines of its cycle's .db.csv files" % T._hh(c["T"]))
            continue
        matched.add(ok)
        name_of[c["ord"]] = ok
        if ok != "final":
            want = sorted(r[:len(lh)] for r in lrows if r[ai] == as_of(day, int(ok[:2]) * 60 + int(ok[2:])))
            if sorted(sent.get("tape_live_label", [])) != want:
                bad.append("W1 rows sent: cycle %s sent %d label rows, the file has %d new labels" % (
                    T._hh(c["T"]), len(sent.get("tape_live_label", [])), len(want)))
    for nm in names:
        if any(T.u_rows(res, nm, t) for t in T.DELTA_TABLES) and nm not in matched:
            bad.append("W1 rows sent: cycle %s has U lines and no write" % nm)
            break
    # W2
    exp = _expected_after(T, res, day)
    for c in calls:
        nm, got = name_of.get(c["ord"]), snaps.get(c["ord"])
        if nm is None or got is None:
            continue
        diff = [t for t in T.DB_TABLES if got[t] != exp[nm][t]]
        if diff:
            bad.append("W2 FakeTable after the script of %s != the U-only state of the files: %s (table %s, files %s)" % (
                T._hh(c["T"]), diff[0], got[diff[0]], exp[nm][diff[0]]))
            break
    # W3
    for c in calls:
        for t, rows in T.sent_rows(c).items():
            seen = set()
            for r in rows:
                k = tbl._key(t, _typed(tbl, t, r))
                if k in seen:
                    bad.append("W3 duplicate conflict key in the script of %s, table %s: %s" % (T._hh(c["T"]), t, k))
                    break
                seen.add(k)
            else:
                continue
            break
    return bad + w4(T, res)


def w4(T, res):
    """W4: no write skips and no stop (both write modes)."""
    bad = []
    hb = T.w_json(res, "heartbeat.json").get("write", {})
    st = T.w_json(res, "state.json")
    if hb.get("state") == "stopped" or hb.get("skips", 0) != 0:
        bad.append("W4 write skips: heartbeat write %s" % hb)
    met = T.w_metrics(res)
    odd = [r["T"] + ":" + r["write_state"] for r in met if r["write_state"] not in ("sent", "none")]
    if odd:
        bad.append("W4 write skips: write_state %s" % odd[:4])
    errs = [(k, r["T"]) for r in met for k in r if k.startswith("werr_") and r[k] not in ("", "0")]
    if errs:
        bad.append("W4 write skips: write errors %s" % errs[:3])
    if st.get("db_written") != "final":
        bad.append("W4 write skips: db_written is %r, want 'final'" % st.get("db_written"))
    return bad


def count_checks(T, res, day, records=None):
    """Count mode (--write count): what can be asserted without the scripts. -> list of failure texts.
      C0  at least one script was sent
      C1  per script, the rows per table == the U-line count of its cycle's .db.csv files, and its labels == that cycle's new
          labels (a COUNT, not the content: W1-W3 need the scripts and are not run in this mode); every cycle with U lines was written
      W4  as in fake mode
    records: the CountShell's (T, ord, rows per DB_TABLES) list (default: the shell's own)."""
    bad = []
    recs = res.fake.records if records is None else records
    names = T.cycle_names(res)
    lh, lrows = T.label_rows(res)
    ai = lh.index("as_of")
    as_of = T.mods()[0].as_of
    li = T.DB_TABLES.index("tape_live_label")
    if not recs:
        bad.append("C0 no write script was sent (the assertions would be vacuous)")
    matched = set()
    for Tm, _ordn, counts in recs:
        got = dict(zip(T.DB_TABLES, counts))
        cands = [T._nm(Tm)] + (["final"] if "final" in names else [])
        ok = None
        for nm in cands:
            if all(got[t] == len(T.u_rows(res, nm, t)) for t in T.DELTA_TABLES):
                ok = nm
                break
        if ok is None:
            bad.append("C1 rows sent: the script of %s sent %s, not the U-line counts of its cycle's .db.csv files" % (
                T._hh(Tm), dict((t, got[t]) for t in T.DELTA_TABLES)))
            continue
        matched.add(ok)
        if ok != "final":
            want = sum(1 for r in lrows if r[ai] == as_of(day, int(ok[:2]) * 60 + int(ok[2:])))
            if counts[li] != want:
                bad.append("C1 rows sent: cycle %s sent %d label rows, the file has %d new labels" % (T._hh(Tm), counts[li], want))
    for nm in names:
        if any(T.u_rows(res, nm, t) for t in T.DELTA_TABLES) and nm not in matched:
            bad.append("C1 rows sent: cycle %s has U lines and no write" % nm)
            break
    return bad + w4(T, res)


def slice_run(T, day, odir, raw, chain_csvs, start, arrival=None, plants=None, rows=500):
    """The slice smoke: the runner from `start` against the FakeTable, then W0 to W4 (and db_dupkeys.csv = failure).
    -> (res, fails, info{secs, scripts, sent, withheld}). A PASS here is not a gate PASS."""
    t0 = time.time()
    res = run_live_fake(T, day, odir, raw, chain_csvs, start, arrival=arrival, plants=plants, rows=rows)
    secs = time.time() - t0
    if res.rc != 0:
        fails = ["runner rc=%s: %s" % (res.rc, res.log.strip()[-300:])]
        return res, fails, {"secs": secs, "scripts": 0, "sent": {}, "withheld": 0}
    fails = write_checks(T, res, day)
    live = os.path.join(res.root, "live")
    if os.path.exists(os.path.join(live, "db_dupkeys.csv")):
        fails.append("W3 db_dupkeys.csv exists: the writer found a duplicate conflict key")
    wp = os.path.join(live, "db_withheld.csv")
    withheld = 0
    if os.path.exists(wp):
        with open(wp, "rb") as fh:
            withheld = max(0, fh.read().count(b"\n") - 1)
    sent, sc = {}, T.w_scripts(res)
    for c in sc:
        for t, rws in T.sent_rows(c).items():
            sent[t] = sent.get(t, 0) + len(rws)
    return res, fails, {"secs": secs, "scripts": len(sc), "sent": sent, "withheld": withheld}


# ---------------------------------------------------------------------------------------------------------------- self-test
def _fresh(name):
    T = load_ttl()
    d = os.path.join(T._TMP, "wc_" + name)
    shutil.rmtree(d, ignore_errors=True)
    return d


def _run(name, plants=None):
    T = load_ttl()
    f = T.fixture()
    return run_live_fake(T, T.DAY, _fresh(name), f["raw"], f["chain"], "15:20", plants=plants, rows=7)


def _first_insert(call, table):
    for s in call["parsed"]["stmts"]:
        if s.get("insert") and s["insert"]["table"] == table:
            return s["insert"]
    return None


def selftest():
    T = load_ttl()
    bad = []
    clean = _run("clean")
    calls = T.w_scripts(clean)
    print("SELFTEST substrate: rc=%s, %d write scripts, %d snapshots" % (clean.rc, len(calls), len(clean.fake.snaps)))
    f0 = write_checks(T, clean, T.DAY) if clean.rc == 0 else ["the clean run did not finish: rc=%s %s" % (clean.rc, clean.log[-200:])]
    print("SELFTEST S0 clean run: %s" % ("OK (no failure)" if not f0 else "FAIL " + "; ".join(f0[:3])))
    bad += ["S0: " + x for x in f0]

    def expect(tag, want, fails):
        hit = [x for x in fails if x.startswith(want)]
        print("SELFTEST %s: %s" % (tag, ("fired: " + hit[0][:150]) if hit else "NOT DETECTED (failures: %s)" % ("; ".join(fails[:2]) or "none")))
        if not hit:
            bad.append("%s: planted fault not detected by %s" % (tag, want))

    # S1: wrong rows-sent count: one cycle row dropped from a recorded script
    c1 = copy.deepcopy(calls)
    ins = _first_insert(c1[0], "tape_live_cycle")
    ins["rows"].pop()
    expect("S1 wrong rows-sent count", "W1", write_checks(T, clean, T.DAY, calls=c1))

    # S3: a duplicate conflict key: a row of the cycle insert sent twice
    c3 = copy.deepcopy(calls)
    ins = _first_insert(c3[0], "tape_live_cycle")
    ins["rows"].append(ins["rows"][0])
    expect("S3 duplicate conflict key", "W3", write_checks(T, clean, T.DAY, calls=c3))

    # S2: the FakeTable differs from the files' state: a foreign cycle row appears in the table at the first script
    def foreign(table, parsed):
        i = [s["insert"] for s in parsed["stmts"] if s.get("insert") and s["insert"]["table"] == "tape_live_cycle"][0]
        d = dict(zip(i["cols"], i["rows"][0]))
        d["instrument_token"], d["strike"] = "999999999", "99999"
        table.insert_foreign("tape_live_cycle", d)
    r2 = _run("foreign", plants={("n", 1): {"preload": foreign}})
    f2 = write_checks(T, r2, T.DAY) if r2.rc == 0 else ["run rc=%s" % r2.rc]
    expect("S2 FakeTable != files' state", "W2", f2)

    # S4: a write skip (statement timeout) on the first script
    r4 = _run("skip", plants={("n", 1): {"err": "57014"}})
    f4 = write_checks(T, r4, T.DAY) if r4.rc == 0 else ["run rc=%s" % r4.rc]
    expect("S4 a write skip", "W4", f4)

    # slice mode (slice_run): a clean slice passes; a planted write skip and a planted foreign row each fail it, with their own tag
    fx = T.fixture()
    for nm, pl, want in (("slice-clean", None, None),
                         ("slice-skip", {("n", 1): {"err": "57014"}}, "W4"),
                         ("slice-foreign", {("n", 1): {"preload": foreign}}, "W2")):
        _r, fl, info = slice_run(T, T.DAY, _fresh(nm), fx["raw"], fx["chain"], "15:20", plants=pl, rows=7)
        if want is None:
            print("SELFTEST S5 %s: %s (%d scripts, %.1f s)" % (nm, "OK (no failure)" if not fl else "FAIL " + "; ".join(fl[:2]), info["scripts"], info["secs"]))
            bad += ["S5: " + x for x in fl]
        else:
            expect("S5 " + nm, want, fl)

    # S6: the grid minute of a script on a day that is not the fixture day (2026-11-04, two days before it) must be 14:00
    d2 = "2026-11-04"
    lr = T.rmods()[0]
    saved_now = lr.SimClock.last_now
    try:
        lr.SimClock.last_now = T.ist_epoch(840, day=d2)
        try:
            sh = make_snap(T)(NoRead(), T.FakeTable(d2), os.path.join(T._TMP, "s6", d2), day=d2)
            got, note = T._hh(sh._T()), ""
        except TypeError:
            sh = make_snap(T)(NoRead(), T.FakeTable(d2), os.path.join(T._TMP, "s6", d2))
            got, note = T._hh(sh._T()), "no day argument; "
    finally:
        lr.SimClock.last_now = saved_now
    ok6 = got == "14:00" and not note
    print("SELFTEST S6 grid minute on another day: %s%sgrid minute %s (want 14:00)" % ("OK " if ok6 else "FAIL ", note, got))
    if not ok6:
        bad.append("S6: %sgrid minute %s (want 14:00)" % (note, got))

    # S7: the count shell holds nothing per row sent: its deep size after the canon run (fixture from 08:50, N = 7: 75 scripts,
    # 2,738 rows) is at most SHELL_BOUND_KB. Control, so the check can fail for the reason it names: the fake shell of the same
    # run must exceed the bound (red on 2026-11-17: 13,684.1 KB, _l2_logs/2b_count_red_selftest.log).
    rf = run_live_fake(T, T.DAY, _fresh("deep_fake"), fx["raw"], fx["chain"], "08:50", rows=7)
    kf = deep_size(rf.fake) / 1024.0
    rc7 = run_live_count(T, T.DAY, _fresh("deep_count"), fx["raw"], fx["chain"], "08:50", rows=7)
    kc = deep_size(rc7.fake) / 1024.0
    nrc = len(rc7.fake.records)
    ok7 = rf.rc == 0 and rc7.rc == 0 and kf > SHELL_BOUND_KB and kc <= SHELL_BOUND_KB and nrc == len(T.w_scripts(rf))
    print("SELFTEST S7 shell deep size: %scount %.1f KB after %d scripts, bound %d KB; control fake %.1f KB after %d scripts (must exceed)" % (
        "OK " if ok7 else "FAIL ", kc, nrc, SHELL_BOUND_KB, kf, len(T.w_scripts(rf)) if rf.rc == 0 else -1))
    if not ok7:
        bad.append("S7: count %.1f KB, control fake %.1f KB, bound %d KB, scripts %d vs %d (rc %s/%s)" % (
            kc, kf, SHELL_BOUND_KB, nrc, len(T.w_scripts(rf)) if rf.rc == 0 else -1, rf.rc, rc7.rc))

    # S8: count mode on the canon run: no failure; and its per-script counts equal the fake's rows sent, script by script
    f8 = count_checks(T, rc7, T.DAY) if rc7.rc == 0 else ["run rc=%s" % rc7.rc]
    fake_counts = [tuple(len(T.sent_rows(c).get(t, [])) for t in T.DB_TABLES) for c in T.w_scripts(rf)] if rf.rc == 0 else []
    same = [r[2] for r in rc7.fake.records] == fake_counts
    print("SELFTEST S8 count mode clean: %s; per-script counts == the fake's rows sent: %s" % (
        "OK (no failure)" if not f8 else "FAIL " + "; ".join(f8[:2]), same))
    bad += ["S8: " + x for x in f8] + ([] if same else ["S8: the count shell's per-script counts differ from the fake's rows sent"])

    # S9: a wrong count (one cycle row less in the first record) must fail C1
    recs = list(rc7.fake.records)
    t0, o0, c0 = recs[0]
    recs[0] = (t0, o0, (c0[0] - 1,) + tuple(c0[1:]))
    expect("S9 count mode wrong rows-sent count", "C1", count_checks(T, rc7, T.DAY, records=recs))

    # S10: a write skip (statement timeout) on the first script must fail W4 in count mode
    r10 = run_live_count(T, T.DAY, _fresh("count_skip"), fx["raw"], fx["chain"], "15:20", plants={("n", 1): {"err": "57014"}}, rows=7)
    expect("S10 count mode write skip", "W4", count_checks(T, r10, T.DAY) if r10.rc == 0 else ["run rc=%s" % r10.rc])

    n = 13
    ok = n - len(bad)
    print("WRITE CHECK SELFTEST %s (%d/%d)" % ("PASS" if not bad else "FAIL: " + " | ".join(bad)[:400], ok, n))
    shutil.rmtree(os.path.join(T._TMP), ignore_errors=True)
    return 0 if not bad else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    print(__doc__)
    sys.exit(2)
