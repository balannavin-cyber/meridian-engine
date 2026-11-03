#!/usr/bin/env python3
"""Tape T1-db guards (docs/tape/T1_db_plan.md section 2): sidecar DDL, access, contracts, offline loader.

  python tests/test_tape_t1db.py [--root DIR] [--only GUARD]

--root runs the guards against another copy of the tree (tests/tape_t1db_mutants.py uses it). In a copy that is not a
git checkout, the loader's git lookup is injected from TAPE_T1DB_HEAD (set by the harness from the real worktree).

No database, no network, no .env: the loader runs against tests/tape_t1db/fake_client.py, and the guard t1db-isolated
asserts core.config / core.execution_log / dotenv were never imported by this process.

Rule 23 (CLAUDE.md): refuses an unlimited `ulimit -v` where the `resource` module exists, and Mon-Fri 08:30-15:45 IST
unless TAPE_RULE23_OVERRIDE_R1=1 (operator ruling R-1, 2026-11-03: the window is a retail-box rule; Local only).

Fixtures are produced by the T1a / T1b generators and tools, never by new generators:
  REAL    gen_day -> process_day -> cycle_day ; gen_chain (NIFTY, SENSEX) -> chain_events_day. Every manifest is real.
          The gen_day day carries no CONC/THIN candidates (measured: 0 events even over 09:15-11:00).
  EVENTS  as REAL, but tape_minute.csv is gen_cycle's planted-event day, so tape_events gets rows. TEST PLUMBING: the
          T1a run_manifest.json of this fixture is re-hashed here (outputs.tape_minute.csv, session inputs), because
          that tape_minute.csv was not produced by process_day. Its cycle and chain manifests are real.
"""
import argparse
import ast
import contextlib
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime, timedelta, timezone

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument("--only", default=None)
ARGS = ap.parse_args()
ROOT = os.path.abspath(ARGS.root)
sys.path.insert(0, ROOT)
for sub in ("tape_t1db", "tape_t1b", "tape_t1a"):
    sys.path.insert(0, os.path.join(ROOT, "tests", sub))

IST = timezone(timedelta(hours=5, minutes=30))


def rule23():
    try:
        import resource
        if resource.getrlimit(resource.RLIMIT_AS)[0] == resource.RLIM_INFINITY:
            print("REFUSED: rule 23 - run under ( ulimit -v 2000000; ... )")
            return 2
    except ImportError:
        pass
    now = datetime.now(IST)
    if now.weekday() < 5 and 830 <= now.hour * 100 + now.minute < 1545:
        if os.environ.get("TAPE_RULE23_OVERRIDE_R1") == "1":
            print("RULE23 WINDOW LIFTED by operator ruling R-1 (2026-11-03): Local machine, not the retail box")
            return 0
        print("REFUSED: rule 23 - fixture tests blocked 08:30-15:45 IST on weekdays (Local: set TAPE_RULE23_OVERRIDE_R1=1 under ruling R-1)")
        return 2
    return 0


if rule23():
    sys.exit(2)

import gen_chain  # noqa: E402
import gen_cycle  # noqa: E402
import gen_day  # noqa: E402
from fake_client import FakeClient, FakeLedger  # noqa: E402
from services.tape_db import contract_seed, load_day, sidecar_sql, tape_schema as S  # noqa: E402

DAY = gen_chain.DAY
MIG = "sql/2026-11-03_tape_t1db_sidecar.sql"
SEED_SQL = "sql/2026-11-03_tape_t1db_contracts.sql"
ACCESS = "services/tape_db/check_tape_access.sql"
TMP = []


def tmpdir():
    d = tempfile.mkdtemp(prefix="tape_t1db_")
    TMP.append(d)
    return d


def src(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def quiet(fn, *a, **kw):
    so, se = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(so), contextlib.redirect_stderr(se):
        rc = fn(*a, **kw)
    return rc, so.getvalue(), se.getvalue()


def sha(p):
    return load_day.sha256_file(p)


# ====================================================================== fixtures
_F = {}


def head():
    try:
        r = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and os.path.exists(os.path.join(ROOT, ".git")):
            return r.stdout.strip(), True
    except OSError:
        pass
    return os.environ.get("TAPE_T1DB_HEAD", ""), False


def git_arg():
    """None (the loader reads git itself) in a real checkout; an injected lookup in a non-git copy."""
    h, real = head()
    return None if real else (lambda: (h, False))


def _chain(base):
    ch = os.path.join(base, "chain_%s" % DAY)
    gen_chain.write(ch, "NIFTY")
    gen_chain.write(ch, "SENSEX")
    from services.tape_chain import chain_events_day
    rc, so, se = quiet(chain_events_day.main, ["--in", ch, "--out", os.path.join(ch, "events"), "--day", DAY])
    assert rc == 0, "fixture: chain_events_day rc=%s %s" % (rc, se[-400:])
    return os.path.join(ch, "events")


def fx_real():
    if "real" not in _F:
        from services.tape_offline import cycle_day, process_day
        base = tmpdir()
        day_dir = os.path.join(base, DAY)
        gen_day.build_day(day_dir, gen_day.Spec(day=DAY))
        out, cyc = os.path.join(base, "out_" + DAY), os.path.join(base, "cyc_" + DAY)
        rc, so, se = quiet(process_day.main, [day_dir, "--day", DAY, "--out", out, "--verify-manifest"])
        assert rc == 0, "fixture: process_day rc=%s %s" % (rc, se[-400:])
        sess = os.path.join(day_dir, "session")
        rc, so, se = quiet(cycle_day.main, ["--in", out, "--session", sess, "--out", cyc])
        assert rc == 0, "fixture: cycle_day rc=%s %s" % (rc, se[-400:])
        _F["real"] = {"day": DAY, "out": out, "cyc": cyc, "chain": _chain(base), "session": sess}
    return dict(_F["real"])


def fx_events():
    if "events" not in _F:
        from services.tape_offline import cycle_day
        r = fx_real()
        base = tmpdir()
        g = gen_cycle.build(os.path.join(base, "gen"))
        assert gen_cycle.DAY == DAY, "fixture: gen_cycle day %s != %s" % (gen_cycle.DAY, DAY)
        sess = os.path.join(base, "session")
        os.makedirs(os.path.join(sess, DAY))
        for n in os.listdir(os.path.join(g["sess"], DAY)):
            shutil.copy2(os.path.join(g["sess"], DAY, n), os.path.join(sess, DAY, n))
        rp = "daily_report_%s.json" % DAY
        shutil.copy2(os.path.join(r["session"], DAY, rp), os.path.join(sess, DAY, rp))
        out = os.path.join(base, "out_" + DAY)
        os.makedirs(out)
        for n in ("g3_report.json", "g3_report.txt"):
            shutil.copy2(os.path.join(r["out"], n), os.path.join(out, n))
        shutil.copy2(os.path.join(g["inp"], "tape_minute.csv"), os.path.join(out, "tape_minute.csv"))
        with open(os.path.join(r["out"], "run_manifest.json"), encoding="utf-8") as fh:
            man = json.load(fh)
        man["outputs"]["tape_minute.csv"] = sha(os.path.join(out, "tape_minute.csv"))
        man["inputs"] = [e for e in man["inputs"] if not e["path"].startswith("session/")] + [
            {"path": "session/%s/%s" % (DAY, n), "sha256": sha(os.path.join(sess, DAY, n)),
             "bytes": os.path.getsize(os.path.join(sess, DAY, n))} for n in sorted(os.listdir(os.path.join(sess, DAY)))]
        man["test_plumbing"] = "T1a manifest re-hashed by tests/test_tape_t1db.py fx_events"
        with open(os.path.join(out, "run_manifest.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(man, fh, sort_keys=True, indent=1)
        cyc = os.path.join(base, "cyc_" + DAY)
        rc, so, se = quiet(cycle_day.main, ["--in", out, "--session", sess, "--out", cyc])
        assert rc in (0, 4), "fixture: cycle_day rc=%s %s" % (rc, se[-400:])
        _F["events"] = {"day": DAY, "out": out, "cyc": cyc, "chain": r["chain"], "session": sess}
    return dict(_F["events"])


def copy_fx(fx):
    """A private copy of a fixture (out/cyc/session/chain parent), so a guard may corrupt it."""
    base = tmpdir()
    m = {}
    for k in ("out", "cyc", "session"):
        m[k] = os.path.join(base, k)
        shutil.copytree(fx[k], m[k])
    parent = os.path.dirname(fx["chain"])
    cp = os.path.join(base, os.path.basename(parent))
    shutil.copytree(parent, cp)
    m["chain"] = os.path.join(cp, os.path.basename(fx["chain"]))
    m["day"] = fx["day"]
    return m


def argv(fx, *extra):
    return ["--day", fx["day"], "--out", fx["out"], "--cyc", fx["cyc"], "--chain", fx["chain"],
            "--session", fx["session"]] + list(extra)


def run_load(fx, *extra, client=None):
    FakeLedger.instances = []
    client = client if client is not None else FakeClient()
    rc, so, se = quiet(load_day.main, argv(fx, *extra), client=client, ledger_factory=FakeLedger, git=git_arg())
    return rc, so, se, client, list(FakeLedger.instances)


def csv_count(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return sum(1 for _ in csv.reader(fh)) - 1


def expected_counts(fx):
    """Independent of the loader: data lines of each CSV, symbols in g3_report.json."""
    d = {"out": fx["out"], "cyc": fx["cyc"], "chain": fx["chain"]}
    n = {t: csv_count(os.path.join(d[S.TABLES[t]["src"]], S.TABLES[t]["csv"])) for t in S.TABLES}
    with open(os.path.join(fx["out"], "g3_report.json"), encoding="utf-8") as fh:
        n["tape_daily_report"] = len(json.load(fh)["symbols"])
    return n


# ====================================================================== DDL parse
def parse_tables(sql):
    out = {}
    for m in re.finditer(r"CREATE TABLE IF NOT EXISTS public\.(\w+) \((.*?)\n\);", sql, re.S):
        cols = []
        for ln in m.group(2).splitlines():
            ln = ln.strip().rstrip(",")
            if not ln or ln.upper().startswith("CONSTRAINT"):
                continue
            name, rest = ln.split(None, 1)
            cols.append((name, re.sub(r"\s+NOT NULL$", "", rest).strip()))
        out[m.group(1)] = cols
    return out


# ====================================================================== guards
def g_ddl_columns():
    cells = []
    got = parse_tables(src(MIG))
    cells.append((set(got) == set(S.ORDER), "migration creates exactly the six tables: %s" % sorted(got)))
    for t in S.ORDER:
        want = [(c, S.db_types(t)[c]) for c in S.db_columns(t)]
        have = got.get(t, [])
        miss = sorted(set(want) - set(have))
        extra = sorted(set(have) - set(want))
        cells.append((not miss and not extra and len(have) == len(set(have)),
                      "%s: %d columns == tape_schema (CSV tuple + renames + added + provenance); missing %s extra %s"
                      % (t, len(have), miss or "none", extra or "none")))
    for t, sp in S.TABLES.items():
        dbc = [sp["rename"].get(c, c) for c in sp["cols"]]
        ok = set(sp["rename"]) <= set(sp["cols"]) and len(dbc) == len(set(dbc)) and not (set(dbc) & set(sp["added"]))
        cells.append((ok, "%s: every CSV column %s maps to exactly one DB column" % (t, sp["csv"])))
    fx = fx_events()
    d = {"out": fx["out"], "cyc": fx["cyc"], "chain": fx["chain"]}
    for t, sp in S.TABLES.items():
        with open(os.path.join(d[sp["src"]], sp["csv"]), encoding="utf-8", newline="") as fh:
            hdr = next(csv.reader(fh))
        cells.append((tuple(hdr) == tuple(sp["cols"]), "%s header written by the T1a/T1b tool == the imported tuple" % sp["csv"]))
    return cells


def g_ddl_access():
    sql, chk = src(MIG), src(ACCESS)
    cells = []
    for t in S.ORDER:
        e = re.escape(t)
        n_rls = len(re.findall(r"ALTER TABLE public\.%s ENABLE ROW LEVEL SECURITY;" % e, sql))
        pols = re.findall(r"CREATE POLICY (\w+) ON public\.%s (FOR \w+ TO [\w, ]+ USING \(true\));" % e, sql)
        n_rev = len(re.findall(r"REVOKE ALL ON public\.%s FROM anon, authenticated;" % e, sql))
        n_gr = len(re.findall(r"GRANT SELECT ON public\.%s TO merdian_ro;" % e, sql))
        bad = re.findall(r"(DISABLE ROW LEVEL SECURITY|GRANT [^;]*public\.%s[^;]* TO [^;]*(anon|authenticated))" % e, sql)
        ok = n_rls == 1 and pols == [("merdian_ro_select", "FOR SELECT TO merdian_ro USING (true)")] and n_rev == 1 \
            and n_gr == 1 and not bad
        cells.append((ok, "%s: RLS enabled x%d, policies %s, REVOKE anon+authenticated x%d, GRANT SELECT merdian_ro x%d, "
                          "forbidden %s" % (t, n_rls, pols, n_rev, n_gr, bad or "none")))
        cells.append(("'public.%s'::regclass" % t in chk, "%s is probed by check_tape_access.sql" % t))
    cells.append(("DISABLE ROW LEVEL SECURITY" not in sql, "no DISABLE ROW LEVEL SECURITY anywhere in the migration"))
    return cells


FORBIDDEN = re.compile(r"\bjoin\b|create\s+(or\s+replace\s+)?(materialized\s+)?(view|function|trigger|rule)\b|"
                       r"generated\s+(always|by)\b|\blead(_|\b)|coverage|agreement|straddle|\batm\b", re.I)
CHAIN_T = {t for t in S.ORDER if t.startswith("tape_chain_")}
TAPE_T = set(S.ORDER) - CHAIN_T
PY_NOJOIN = ("services/tape_db/load_day.py", "services/tape_db/contract_seed.py",
             "services/tape_db/tape_schema.py")


def g_no_join():
    cells = []
    for rel in (MIG, SEED_SQL):
        hits = sorted({m.group(0) for m in FORBIDDEN.finditer(src(rel))}) if os.path.isfile(os.path.join(ROOT, rel)) else ["<missing>"]
        cells.append((not hits, "%s: no JOIN / view / function / trigger / generated column / outcome word: %s" % (rel, hits or "none")))
    for rel in PY_NOJOIN:
        tree = ast.parse(src(rel))
        bad = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                s = node.value
                if FORBIDDEN.search(s):
                    bad.append("word:%r" % FORBIDDEN.search(s).group(0))
                names = set(re.findall(r"\btape_\w+", s))
                if names & CHAIN_T and names & TAPE_T:
                    bad.append("both sides in one string: %s" % sorted(names))
                if re.search(r"\btape_\w+\s*\(", s):
                    bad.append("embedded resource: %r" % s[:60])
        cells.append((not bad, "%s: no string joins, embeds or names both sides: %s" % (rel, bad[:5] or "none")))
    return cells


def g_load_manifest():
    good = copy_fx(fx_real())
    rc0, so0, _se, c0, l0 = run_load(good)
    bad = copy_fx(fx_real())
    p = os.path.join(bad["cyc"], "tape_strike_cycle.csv")
    b = bytearray(open(p, "rb").read())
    b[-2] = ord("9") if b[-2] != ord("9") else ord("8")
    open(p, "wb").write(bytes(b))
    rc, so, se, client, led = run_load(bad)
    bad2 = copy_fx(fx_real())
    with open(os.path.join(bad2["out"], "tape_minute.csv"), "a", encoding="utf-8", newline="") as fh:
        fh.write("\n")
    rc2, so2, _se2, client2, led2 = run_load(bad2)
    return [(rc0 == 0 and "LOAD PASS" in so0, "control: the real fixture's manifests verify and the day loads (rc=%s)" % rc0),
            (rc == 3 and not client.calls and not led and "MANIFEST FAIL" in so,
             "one byte flipped in tape_strike_cycle.csv after its manifest -> exit %s, %d client calls, %d ledgers"
             % (rc, len(client.calls), len(led))),
            (rc2 == 3 and not client2.calls and not led2,
             "tape_minute.csv changed after T1a (T1a output and T1b input sha both disagree) -> exit %s, %d calls" % (rc2, len(client2.calls)))]


def g_load_counts():
    fx = fx_events()
    want = expected_counts(fx)
    rc, so, se, client, led = run_load(fx)
    cells = [(rc == 0, "clean load exit %s" % rc)]
    cells.append((all(want[t] >= 1 for t in S.ORDER), "every table has rows in the fixture (not vacuous): %s" % want))
    for t in S.ORDER:
        n = len(client.inserted(t))
        line = "LOAD PASS %s rows=%d == csv=%d" % (t, want[t], want[t])
        cells.append((n == want[t] and line in so, "%s: inserted %d == csv %d, printed %r" % (t, n, want[t], line)))
    sizes = [c[3] for c in client.calls if c[0] == "insert"]
    cells.append((sizes and max(sizes) <= 1000 and any(s == 1000 for s in sizes),
                  "insert batches <= 1000 rows and at least one full batch exercised: max %s" % (max(sizes) if sizes else None)))
    rc2, so2, se2, client2, led2 = run_load(fx, client=FakeClient(drop_one_row_of="tape_strike_cycle"))
    fin = led2[0].final if led2 else []
    cells.append((rc2 == 1 and "LOAD FAIL tape_strike_cycle rows=%d != csv=%d" % (want["tape_strike_cycle"] - 1, want["tape_strike_cycle"]) in so2,
                  "a fake that loses one row -> LOAD FAIL tape_strike_cycle, exit %s" % rc2))
    cells.append((len(fin) == 1 and fin[0][:3] == ("exit_with_reason", "DATA_ERROR", 1),
                  "the ledger records the failure as DATA_ERROR exit 1: %s" % [f[:3] for f in fin]))
    return cells


def g_load_replace():
    fx = fx_events()
    old = "00000000-0000-4000-8000-000000000001"
    pre = {"tape_minute": [{"trading_day": DAY, "run_id": old, "symbol": "NIFTY"}],
           "tape_events": [{"trading_day": DAY, "run_id": old, "symbol": "NIFTY"}],
           "tape_minute_other_day": []}
    c1 = FakeClient(preseed={k: v for k, v in pre.items() if k in S.TAPE_TABLES})
    c1.tables["tape_minute"].append({"trading_day": "2026-11-02", "run_id": old, "symbol": "NIFTY"})
    rc, so, se, client, led = run_load(fx, client=c1)
    cells = [(rc == 2 and not client.writes() and not led and "REFUSED" in so,
              "existing day without --replace -> exit %s, %d writes, %d ledgers" % (rc, len(client.writes()), len(led)))]
    c2 = FakeClient(preseed={k: v for k, v in pre.items() if k in S.TAPE_TABLES})
    c2.tables["tape_minute"].append({"trading_day": "2026-11-02", "run_id": old, "symbol": "NIFTY"})
    rc, so, se, client, led = run_load(fx, "--replace", client=c2)
    ops = [(c[0], c[1]) for c in client.calls if c[0] in ("insert", "delete")]
    last_del = max([i for i, o in enumerate(ops) if o[0] == "delete"], default=-1)
    first_ins = min([i for i, o in enumerate(ops) if o[0] == "insert"], default=-1)
    notes = json.loads(led[0].final[0][3]) if led and led[0].final and led[0].final[0][3] else {}
    sup = notes.get("superseded_run_ids", {})
    day_rows = [r for t in S.ORDER for r in client.tables.get(t, []) if r.get("trading_day") == DAY]
    other = [r for r in client.tables.get("tape_minute", []) if r.get("trading_day") == "2026-11-02"]
    new = led[0].kw.get("run_id") if led else None
    cells += [(rc == 0, "--replace load exit %s" % rc),
              ({o[1] for o in ops if o[0] == "delete"} == {"tape_minute", "tape_events"} and -1 < last_del < first_ins,
               "deletes (%s) all precede the first insert" % sorted({o[1] for o in ops if o[0] == "delete"})),
              (sup.get("tape_minute") == [old] and sup.get("tape_events") == [old],
               "superseded run_id recorded in the ledger notes: %s" % sup),
              (day_rows and all(r.get("run_id") == new for r in day_rows),
               "every row of the day now carries the new run_id (%d rows)" % len(day_rows)),
              (len(other) == 1, "another trading_day is untouched by --replace")]
    return cells


def g_load_provenance():
    fx = fx_events()
    rc, so, se, client, led = run_load(fx)
    h, _real = head()
    cells = [(rc == 0, "load exit %s" % rc),
             (bool(re.match(r"^[0-9a-f]{40}$", h)), "worktree HEAD known: %s" % h)]
    cells.append((len(led) == 1 and len(led[0].final) == 1 and led[0].final[0][0] == "complete",
                  "exactly one ledger, finalised once by complete(): %d ledgers %s" % (len(led), [l.final for l in led][:1])))
    if led:
        kw = led[0].kw
        cells.append((kw.get("script_name") == "load_day.py" and kw.get("product_relation") == "tape_day"
                      and kw.get("symbol") is None and kw.get("expected_writes") == expected_counts(fx),
                      "ledger: script load_day.py, product tape_day, expected_writes == csv counts"))
        rid = kw.get("run_id")
        bad = []
        for t in S.ORDER:
            for r in client.inserted(t):
                if not (r.get("run_id") == rid and r.get("code_sha") == h and r.get("source") == "tape_offline_v1"
                        and r.get("config_version") is None and datetime.fromisoformat(r["loaded_at"]).tzinfo):
                    bad.append(t)
                    break
        cells.append((not bad and rid, "every row: run_id == ledger run_id, code_sha == git HEAD, source, loaded_at; bad %s" % (bad or "none")))
    return cells


CLIENT_OPS = {"insert", "upsert", "delete", "select", "count_exact", "rpc", "update"}


def g_tables_only():
    rel = "services/tape_db/load_day.py"
    tree = ast.parse(src(rel))
    bad, seen = [], set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in CLIENT_OPS \
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "client":
            a = node.args[0] if node.args else None
            if isinstance(a, ast.Constant):
                seen.add(a.value)
                if a.value not in S.TAPE_TABLES:
                    bad.append(a.value)
            elif not (isinstance(a, ast.Name) and a.id in ("t", "table")):
                bad.append(ast.dump(a)[:40] if a is not None else "no-arg")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                and node.func.value.id == "requests" and node.func.attr != "get":
            bad.append("requests.%s" % node.func.attr)
    loops = [n for n in ast.walk(tree) if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == "t"]
    loop_ok = all(ast.unparse(n.iter) == "S.ORDER" for n in loops)
    fx = fx_events()
    rc, so, se, client, led = run_load(fx)
    touched = {c[1] for c in client.calls}
    return [(not bad, "every client call names a tape_* table or a loop variable: bad %s" % (bad or "none")),
            (loop_ok and loops, "every `for t in ...` iterates tape_schema.ORDER (%d loops)" % len(loops)),
            (touched <= S.TAPE_TABLES and rc == 0, "at run time the client saw only %s" % sorted(touched))]


def _imports(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    top, inner = [], []
    for node in tree.body:
        for n in ast.walk(node):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                mods = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
                (inner if isinstance(node, (ast.FunctionDef, ast.ClassDef)) else top).extend(mods)
    return top, inner


def g_isolated():
    cells = []
    rdir = os.path.join(ROOT, "services", "tape_runner")
    bad = []
    for f in sorted(os.listdir(rdir)):
        if f.endswith(".py"):
            top, inner = _imports(os.path.join(rdir, f))
            text = open(os.path.join(rdir, f), encoding="utf-8").read()
            bad += ["%s: %s" % (f, m) for m in top + inner if "tape_db" in m or "tape_offline" in m or m == "services"]
            bad += ["%s: names load_day" % f] if "load_day" in text or "tape_db" in text or "tape_offline" in text else []
    cells.append((not bad, "no services/tape_runner module imports or names services.tape_db / tape_offline: %s" % (bad or "none")))
    inst = src("services/tape_runner/install.sh")
    m = re.search(r"archive HEAD ([^|]*?) \|", inst)
    cells.append((bool(m) and m.group(1).split() == ["services/__init__.py", "services/tape_runner"] and "tape_db" not in m.group(1) and "tape_offline" not in m.group(1),
                  "install.sh archives only %s" % (m.group(1) if m else "?")))
    std = set(sys.stdlib_module_names)
    badtop = []
    for rel in ("services/tape_db/load_day.py", "services/tape_db/contract_seed.py",
                "services/tape_db/tape_schema.py", "services/tape_db/sidecar_sql.py"):
        top, inner = _imports(os.path.join(ROOT, rel))
        for mod in top:
            if mod.split(".")[0] in std or mod.startswith("merdian_compute.tape") or mod.startswith("services.tape_db") \
                    or mod in ("merdian_compute", "services", "services.tape_db"):
                continue
            badtop.append("%s: %s" % (os.path.basename(rel), mod))
    cells.append((not badtop, "module-level imports are stdlib / merdian_compute.tape / services.tape_db only "
                              "(core.* only inside functions): %s" % (badtop or "none")))
    fx_events()
    run_load(fx_events())
    leaked = [m for m in ("core.config", "core.execution_log", "core.supabase_client", "dotenv") if m in sys.modules]
    cells.append((not leaked, "no .env-loading module imported by the tests: %s" % (leaked or "none")))
    return cells


# ====================================================================== units
def u_convert():
    c = load_day.convert
    rows = load_day.csv_rows("tape_minute", os.path.join(fx_events()["out"], "tape_minute.csv"), DAY)
    fut = [r for r in rows if r["role"] == "FUT"]
    return [(c("bigint", "") is None and c("bigint", "12") == 12 and c("double precision", "0.5") == 0.5,
             "empty string -> NULL, never 0; ints and floats typed"),
            (c("boolean", "1") is True and c("boolean", "0") is False and c("jsonb", '{"a":1}') == {"a": 1}, "bool and jsonb"),
            (rows and rows[0]["minute_ist"].endswith(":00+05:30") and rows[0]["minute_ist"].startswith(DAY + "T"),
             "minute HH:MM -> <day>T<HH:MM>:00+05:30: %s" % (rows[0]["minute_ist"] if rows else None)),
            (all(r["strike"] is None for r in fut) and fut, "FUT rows carry NULL strike (%d rows)" % len(fut))]


def u_rendered():
    return [(src(MIG) == sidecar_sql.render(), "%s == sidecar_sql.render() (not hand-edited)" % MIG),
            (src(ACCESS) == sidecar_sql.render_access_check(), "%s == render_access_check()" % ACCESS),
            (src(ACCESS).index("SET LOCAL ROLE merdian_ro;") < src(ACCESS).index("SELECT relation"),
             "the access check switches role before it reads, in one execution")]


def u_contract_runner():
    import check_contracts_shadow as ccs
    fx = fx_events()
    derived, inputs, subs = contract_seed.compute(fx["day"], fx["out"], fx["cyc"], fx["chain"], fx["session"])
    cons = {c["product"]: c for c in contract_seed.contracts(fx["day"], derived)}
    c = cons.get("tape_minute:NIFTY")
    cap = c["expected_per_cycle"]["rows"][1] if c else 0
    now = datetime.now(timezone.utc)
    st = lambda n, behind: ccs.own_status(c, DAY, [{}] * n, {}, now, False, behind)[0]
    edges = contract_seed.lineage(list(cons.values()))
    cross = [e for e in edges if (e[0].startswith("tape_chain_")) != (e[1].startswith("tape_chain_"))]
    sql = contract_seed.render_sql(fx["day"], list(cons.values()), edges, derived, inputs, subs)
    return [(c is not None and derived["NIFTY"]["minute_rows"] <= cap, "tape_minute:NIFTY ceiling %s >= measured %s"
             % (cap, derived["NIFTY"].get("minute_rows"))),
            (st(derived["NIFTY"]["minute_rows"], 0) == "OK", "the runner reads the seeded contract OK on the fixture day"),
            (st(cap + 1, 0) == "DEGRADED", "one row over the ceiling -> DEGRADED (the bound can fire)"),
            (st(1, 2) == "MISSING", "two trading days behind -> MISSING"),
            (len(edges) == 6 and not cross, "6 lineage edges, none crossing tape <-> chain: %s" % edges),
            (all(p in sql for p in cons) and all(v in sql for v in inputs.values()),
             "the SQL names every product and carries every manifest sha256")]


def u_seed_committed():
    t = src(SEED_SQL) if os.path.isfile(os.path.join(ROOT, SEED_SQL)) else ""
    shas = re.findall(r"^--\s+(out|cyc|chain)\s+run_manifest\.json\s+([0-9a-f]{64})$", t, re.M)
    return [(len(shas) == 3, "committed %s carries the three day-1 manifest sha256s in its header: %s" % (SEED_SQL, [s[0] for s in shas])),
            (t.count("ON CONFLICT (product) DO NOTHING") == 1 and "tape_minute:SENSEX" in t, "idempotent contract insert, both symbols")]


GUARDS = [("db-ddl-columns", g_ddl_columns), ("db-ddl-access", g_ddl_access), ("db-no-join", g_no_join),
          ("load-manifest", g_load_manifest), ("load-counts", g_load_counts), ("load-replace", g_load_replace),
          ("load-provenance", g_load_provenance), ("load-tables-only", g_tables_only), ("t1db-isolated", g_isolated)]
UNITS = [u_convert, u_rendered, u_contract_runner, u_seed_committed]


def main():
    results = []
    for name, fn in [(n, f) for n, f in GUARDS if ARGS.only in (None, n)]:
        try:
            cells = fn()
            ok = bool(cells) and all(c[0] for c in cells)
        except Exception:
            cells = [(False, "EXCEPTION " + traceback.format_exc().strip().splitlines()[-1])]
            ok = False
        results.append((name, ok))
        print("%s %s" % ("PASS" if ok else "FAIL", name))
        for c in cells:
            print("    [%s] %s" % ("ok" if c[0] else "XX", c[1]))
    unit_ok = unit_n = 0
    if ARGS.only is None:
        for fn in UNITS:
            try:
                cells = fn()
            except Exception:
                cells = [(False, "EXCEPTION " + traceback.format_exc().strip().splitlines()[-1])]
            for c in cells:
                unit_n += 1
                unit_ok += bool(c[0])
                print("    unit %s [%s] %s" % (fn.__name__, "ok" if c[0] else "XX", c[1]))
    for d in TMP:
        shutil.rmtree(d, ignore_errors=True)
    g_ok = sum(1 for _, ok in results if ok)
    passed = bool(results) and g_ok == len(results) and unit_ok == unit_n
    print("TAPE T1DB %s (%d/%d guards, %d/%d unit checks)" % ("PASS" if passed else "FAIL", g_ok, len(results), unit_ok, unit_n))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
