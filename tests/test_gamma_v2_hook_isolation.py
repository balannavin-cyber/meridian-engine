#!/usr/bin/env python3
"""ADR-033 step 11 gate, checks 1 and 7: the V2 writer hook against the V1 writer, offline.

Runs the real compute_gamma_metrics_local.main() on the frozen golden chains with a fake database
client (no network, no credentials, no database), three ways, and compares what V1 wrote:

  A  the script as committed (no hook)
  B  the script with the hook patch applied, MERDIAN_GAMMA_V2 unset (the hook compiled in, off)
  C  the script with the hook patch applied, MERDIAN_GAMMA_V2=1 (the hook writing to the fake V2 tables)

  python3 -B tests/test_gamma_v2_hook_isolation.py            all golden runs, then the cases, then the mutants
  python3 -B tests/test_gamma_v2_hook_isolation.py --quick    first 12 runs per golden day
  python3 -B tests/test_gamma_v2_hook_isolation.py --cases    the check-7 cases only
  python3 -B tests/test_gamma_v2_hook_isolation.py --script P --patcher Q   test another script / patcher
  python3 -B tests/test_gamma_v2_hook_isolation.py --expect-bound S   allow S seconds (default 2) for a 3 s V2 hang with the bound at 1 s

CHECK 1 compares, per run, A against B against C: every payload sent to gamma_metrics and
gex_strike_snapshots (canonical JSON), the exit code, and stdout without the hook's own lines.
Only gamma_metrics.created_at is blanked (it is datetime.now() in the writer). The hook adds one stdout
line per run (gamma_v2_status=...) and, when on, gex_strike_v2_rows_written=...; those are filtered
and named here, not hidden.

CHECK 7 cases (flag on, golden run, fake client misbehaving on the V2 tables only): strike upsert
raises; run-row upsert raises; the import of gamma_v2_writer fails; a V2 input error (two expiries);
--shadow; flag unset. Each must give V1 writes equal to A and exit code equal to A. A V2 hang (bound set to 1 s) must end
within 2 s with status TIMEOUT; a BaseException from the client must be contained (THREAD_ERROR).

WHAT MAKES IT FAIL (proved by --mutants, which this file runs itself): M1 a hook that truncates the
chain rows before V1 reads them (check 1 must fail); M2 the hook's `except Exception` narrowed to
ZeroDivisionError (the "write_v2 itself raises" case must fail); M3 the writer's join without a time limit
(the hang case must fail); M4 the writer thread's handler narrowed to Exception (the BaseException case must fail).

Limits, stated: the database client, the execution log and python-dotenv are fakes; V1's history reads
return nothing (prior row, VIX, range, recent strikes), so values differ from production but A, B and C
see the same inputs; Python here may be newer than the box's 3.10.12; the golden fixtures hold the
front expiry only.
"""
from __future__ import annotations

import contextlib
import copy
import csv
import gzip
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import types
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "golden"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
V1_TABLES = ("gamma_metrics", "gex_strike_snapshots")
V2_TABLES = ("gex_strike_v2", "gex_run_v2")
HOOK_LINES = ("gamma_v2_status=", "gex_strike_v2_rows_written=")


def _ts(v: str) -> datetime:
    v = v.replace(" ", "T", 1).replace("Z", "+00:00")
    if len(v) >= 3 and v[-3] in "+-" and v[-2:].isdigit():
        v += ":00"
    if "." in v:
        head, rest = v.split(".", 1)
        n = len(rest) - len(rest.lstrip("0123456789"))
        v = f"{head}.{rest[:n][:6].ljust(6, '0')}{rest[n:]}"
    return datetime.fromisoformat(v)


def load_runs(quick: bool) -> list[dict]:
    """One entry per golden chain run: day, symbol, run_id, rows (strings as the fixtures hold them)."""
    out = []
    for day in sorted(p for p in GOLDEN.iterdir() if p.is_dir()):
        sym = day.name.split("_")[1]
        with gzip.open(day / "inputs" / "ocs.csv.gz", "rt", newline="") as g:
            ocs = list(csv.DictReader(io.StringIO(g.read())))
        by_run: dict[str, list] = {}
        for r in ocs:
            if r["symbol"] == sym:
                for c in ("ts", "created_at"):
                    r[c] = _ts(r[c]).isoformat() if r[c] else r[c]
                by_run.setdefault(r["run_id"], []).append(r)
        ids = sorted(by_run, key=lambda k: by_run[k][0]["ts"])
        if quick:
            ids = ids[:12]
        out += [{"day": day.name, "symbol": sym, "run_id": k, "rows": by_run[k]} for k in ids]
    return out


# ---------------------------------------------------------------- fakes
class _Resp:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, client, table):
        self.c, self.table, self.op, self.filters, self.rng = client, table, "select", [], None
        self.payload, self.on_conflict = None, None

    def select(self, *a, **k): self.op = "select"; return self
    def eq(self, col, val): self.filters.append((col, val)); return self
    def range(self, a, b): self.rng = (a, b); return self
    def upsert(self, payload, on_conflict=None, **k): self.op, self.payload, self.on_conflict = "upsert", payload, on_conflict; return self
    def __getattr__(self, name):          # lt, gte, order, limit, neq, in_ ...: no-ops on the fake
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *a, **k: self

    def execute(self):
        c = self.c
        if self.op == "upsert":
            c.on_upsert(self.table, self.payload)
            return _Resp([])
        if self.table == "option_chain_snapshots":
            rows = [dict(r) for r in c.chain if all(r.get(col) == val for col, val in self.filters)]
            if self.rng:
                rows = rows[self.rng[0]:self.rng[1] + 1]
            return _Resp(rows)
        return _Resp([])


class FakeClient:
    def __init__(self, chain, behaviour=None):
        self.chain, self.behaviour, self.writes = chain, behaviour or {}, []

    def table(self, name):
        return _Query(self, name)

    def on_upsert(self, table, payload):
        b = self.behaviour.get(table)
        if b == "raise":
            raise RuntimeError(f"injected failure on {table}")
        if b == "base":
            raise SystemExit(7)
        if isinstance(b, tuple) and b[0] == "sleep":
            time.sleep(b[1])
        self.writes.append((table, copy.deepcopy(payload)))


class FakeLog:
    def __init__(self, *a, **k): self.w = []
    def set_symbol(self, s): pass
    def record_write(self, t, n): self.w.append((t, n))
    def complete(self): return 0
    def exit_with_reason(self, reason, exit_code=1, **k): return exit_code


def _install_fakes(client_box):
    sup = types.ModuleType("supabase"); sup.Client = object
    sup.create_client = lambda url, key: client_box[0]
    sys.modules["supabase"] = sup
    dot = types.ModuleType("dotenv"); dot.load_dotenv = lambda *a, **k: False
    sys.modules["dotenv"] = dot
    import core  # noqa: F401  (real package; only the logging module is faked)
    exl = types.ModuleType("core.execution_log"); exl.ExecutionLog = FakeLog
    sys.modules["core.execution_log"] = exl
    for k in ("DHAN_CLIENT_ID", "DHAN_API_TOKEN", "MERDIAN_GAMMA_V2"):
        os.environ.pop(k, None)
    os.environ["SUPABASE_URL"] = "https://fake.invalid"
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "fake-not-a-key"


def run_once(script: Path, run: dict, *, flag: bool, behaviour=None, shadow=False, block_writer_import=False, writer_stub=None, timeout_env=None) -> dict:
    """Import the script fresh, run main() once on one golden run, return what it did."""
    box = [FakeClient(run["rows"], behaviour)]
    _install_fakes(box)
    if flag:
        os.environ["MERDIAN_GAMMA_V2"] = "1"
    os.environ.pop("MERDIAN_GAMMA_V2_TIMEOUT_S", None)
    if timeout_env is not None:
        os.environ["MERDIAN_GAMMA_V2_TIMEOUT_S"] = timeout_env
    sys.modules.pop("gamma_v2_writer", None)
    if block_writer_import:
        sys.modules["gamma_v2_writer"] = None          # import raises ImportError
    if writer_stub is not None:
        sys.modules["gamma_v2_writer"] = writer_stub
    argv = [str(script), run["run_id"], run["symbol"]] + (["--shadow"] if shadow else [])
    old_argv, sys.argv = sys.argv, argv
    out, err = io.StringIO(), io.StringIO()
    res = {"exit": None, "exc": None, "elapsed": None}
    t0 = time.time()
    try:
        spec = importlib.util.spec_from_file_location(f"gcm_under_test_{time.time_ns()}", str(script))
        mod = importlib.util.module_from_spec(spec)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            spec.loader.exec_module(mod)
            res["exit"] = mod.main()
    except BaseException as e:  # noqa: BLE001 -- a test harness records everything
        res["exc"] = f"{type(e).__name__}: {e}"
    finally:
        sys.argv = old_argv
        sys.modules.pop("gamma_v2_writer", None)
    res["elapsed"] = time.time() - t0
    res["stdout"], res["stderr"] = out.getvalue(), err.getvalue()
    res["writes"] = box[0].writes
    return res


def v1_view(res: dict) -> dict:
    """What V1 did: its payloads, exit code and stdout without the hook's own lines."""
    w = []
    for table, payload in res["writes"]:
        if table in V1_TABLES:
            p = copy.deepcopy(payload)
            if table == "gamma_metrics" and isinstance(p, dict):
                p["created_at"] = "<blanked>"
            w.append((table, json.dumps(p, sort_keys=True, default=str)))
    so = "\n".join(l for l in res["stdout"].splitlines() if not l.startswith(HOOK_LINES))
    return {"exit": res["exit"], "exc": res["exc"], "writes": w, "stdout": so}


def status_of(res: dict):
    for l in res["stdout"].splitlines():
        if l.startswith("gamma_v2_status="):
            return l.split("=", 1)[1]
    return None


def patched_copy(script: Path, patcher: Path, tmp: Path, mutate=None) -> Path:
    d = Path(tempfile.mkdtemp(dir=tmp))
    target = d / "compute_gamma_metrics_local.py"
    target.write_bytes(script.read_bytes())
    p = subprocess.run([sys.executable, "-B", str(patcher), "--apply"], cwd=d, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"patcher failed: {p.stdout}{p.stderr}")
    if mutate:
        txt = target.read_text(encoding="utf-8")
        new = mutate(txt)
        if new == txt:
            raise SystemExit("mutant did not change the patched script")
        target.write_text(new, encoding="utf-8")
    return target


# ---------------------------------------------------------------- check 1
def check1(script, patched, runs) -> list[str]:
    errs, n_ok, statuses = [], 0, {}
    for r in runs:
        a = run_once(script, r, flag=False)
        b = run_once(patched, r, flag=False)
        c = run_once(patched, r, flag=True)
        va, vb, vc = v1_view(a), v1_view(b), v1_view(c)
        tag = f"{r['day']} {r['run_id'][:8]}"
        if va["exc"] or va["exit"] != 0 or not va["writes"]:
            errs.append(f"{tag}: baseline did not complete cleanly: {va['exc'] or va['exit']}")
            continue
        if va != vb:
            errs.append(f"{tag}: A != B (hook compiled in, off) in {[k for k in va if va[k] != vb[k]]}")
        if va != vc:
            errs.append(f"{tag}: A != C (hook on) in {[k for k in va if va[k] != vc[k]]}")
        st = status_of(c)
        statuses[st.split(" ")[0] if st else None] = statuses.get(st.split(" ")[0] if st else None, 0) + 1
        v2w = [t for t, _ in c["writes"] if t in V2_TABLES]
        if st and st.startswith("OK") and not ({"gex_strike_v2", "gex_run_v2"} <= set(v2w)):
            errs.append(f"{tag}: status {st} but V2 tables not both written ({sorted(set(v2w))})")
        if status_of(b) != "DISABLED" or any(t in V2_TABLES for t, _ in b["writes"]):
            errs.append(f"{tag}: hook off but status={status_of(b)} / V2 writes present")
        if any(t in V2_TABLES for t, _ in a["writes"]):
            errs.append(f"{tag}: baseline wrote V2 tables")
        n_ok += 1
    print(f"check 1: {len(runs)} runs; A==B==C on V1 payloads, exit code and stdout (hook lines filtered); hook-on statuses {statuses}")
    if not statuses.get("OK"):
        errs.append("no run reached status OK with the hook on: the hook was never exercised")
    return errs


# ---------------------------------------------------------------- check 7
def check7(script, patched, runs, expect_bound) -> tuple[list[str], list[str]]:
    errs, info = [], []
    r = runs[len(runs) // 2]
    base = v1_view(run_once(script, r, flag=False))

    def same(name, res, want_status=None, want_stderr=None):
        v = v1_view(res)
        if v != base:
            errs.append(f"case '{name}': V1 differs from baseline in {[k for k in base if base[k] != v[k]]}")
        if want_status is not None and status_of(res) != want_status:
            errs.append(f"case '{name}': status {status_of(res)!r}, wanted {want_status!r}")
        if want_stderr and want_stderr not in res["stderr"]:
            errs.append(f"case '{name}': stderr lacks {want_stderr!r}")

    same("strike upsert raises", run_once(patched, r, flag=True, behaviour={"gex_strike_v2": "raise"}), "WRITE_ERROR", "WRITE_ERROR")
    res = run_once(patched, r, flag=True, behaviour={"gex_run_v2": "raise"})
    same("run-row upsert raises", res, "WRITE_ERROR", "WRITE_ERROR")
    if not any(t == "gex_strike_v2" for t, _ in res["writes"]):
        errs.append("case 'run-row upsert raises': strike rows were not written before the run row failed (order changed?)")
    else:
        info.append("run-row upsert raises: strike rows written, no run row (the state p3b2 V0 reports and the backfill repairs)")
    same("import of gamma_v2_writer fails", run_once(patched, r, flag=True, block_writer_import=True), None)
    stub = types.ModuleType("gamma_v2_writer")
    def _boom(*a, **k): raise RuntimeError("injected: write_v2 itself raised")
    stub.write_v2_bounded = _boom
    same("write_v2 itself raises (outer hook handler)", run_once(patched, r, flag=True, writer_stub=stub), None, "HOOK_ERROR")
    bad = copy.deepcopy(r); bad["rows"][-1]["spot"] = str(float(bad["rows"][-1]["spot"]) + 1.0)   # two spots in the run
    res_bad = run_once(patched, bad, flag=True)
    base_bad = v1_view(run_once(script, bad, flag=False))
    if v1_view(res_bad) != base_bad:
        errs.append("case 'V2 input error (two spots)': V1 differs from baseline")
    elif base_bad["exit"] == 0 and status_of(res_bad) != "INPUT_ERROR":
        errs.append(f"case 'V2 input error (two spots)': status {status_of(res_bad)!r}, wanted INPUT_ERROR")
    elif base_bad["exit"] != 0:
        info.append("case 'V2 input error (two spots)': V1 itself refused the run, so the hook was not reached")
    sh_base = v1_view(run_once(script, r, flag=False, shadow=True))
    sh = run_once(patched, r, flag=True, shadow=True)
    if v1_view(sh) != sh_base or status_of(sh) != "SKIPPED_SHADOW" or any(t in V2_TABLES for t, _ in sh["writes"]):
        errs.append(f"case '--shadow': V1 differs, or status {status_of(sh)!r}, or V2 written")
    same("flag unset", run_once(patched, r, flag=False), "DISABLED")

    # the time bound: a 3 s V2 hang with the bound set to 1 s
    t = run_once(patched, r, flag=True, behaviour={"gex_strike_v2": ("sleep", 3)}, timeout_env="1")
    same("V2 hang, bound 1 s", t, "TIMEOUT after 1s", "TIMEOUT")
    limit = expect_bound if expect_bound is not None else 2.0
    if t["elapsed"] > limit:
        errs.append(f"case 'V2 hang, bound 1 s': main() took {t['elapsed']:.1f} s, above {limit} s")
    info.append(f"V2 hang of 3 s with the bound at 1 s: main() returned after {t['elapsed']:.1f} s")
    same("bound unparsable falls back to the default", run_once(patched, r, flag=True, timeout_env="abc"), None)
    b = run_once(patched, r, flag=True, behaviour={"gex_strike_v2": "base"})
    same("BaseException from the V2 client is contained", b, "THREAD_ERROR SystemExit")
    return errs, info


# ---------------------------------------------------------------- mutants
def mutants(script, patcher, tmp, runs) -> list[str]:
    errs = []
    m1 = patched_copy(script, patcher, tmp, lambda t: t.replace(
        '_V2_STASH["rows"] = option_rows_raw  # ADR-033 V2 hook: V1 does not read this',
        '_V2_STASH["rows"] = option_rows_raw; option_rows_raw[:] = option_rows_raw[:40]  # MUTANT'))
    e = check1(script, m1, runs[:3])
    print(f"mutant M1 (hook truncates the chain V1 reads): check 1 reported {len(e)} problem(s)")
    if not e:
        errs.append("mutant M1 survived: check 1 did not detect a hook that changes V1's input")
    m2 = patched_copy(script, patcher, tmp, lambda t: t.replace(
        "except Exception as _v2_error:  # noqa: BLE001  # ADR-033 V2 hook",
        "except ZeroDivisionError as _v2_error:  # noqa: BLE001  # ADR-033 V2 hook"))
    e, _ = check7(script, m2, runs, None)
    print(f"mutant M2 (hook except narrowed): check 7 reported {len(e)} problem(s)")
    if not e:
        errs.append("mutant M2 survived: check 7 did not detect a hook that lets an exception escape")
    patched = patched_copy(script, patcher, tmp)
    wsrc = (ROOT / "gamma_v2_writer.py").read_text(encoding="utf-8")
    for name, old, new, case in (
            ("M3 (time bound removed)", "    t.join(limit)\n", "    t.join()\n", "V2 hang"),
            ("M4 (thread handler narrowed to Exception)", "        except BaseException as e:", "        except Exception as e:", "BaseException")):
        if wsrc.count(old) != 1:
            errs.append(f"mutant {name}: target text not found exactly once in gamma_v2_writer.py"); continue
        stub = types.ModuleType("gamma_v2_writer")
        exec(compile(wsrc.replace(old, new), "gamma_v2_writer_mutant", "exec"), stub.__dict__)
        r = runs[len(runs) // 2]
        base = v1_view(run_once(script, r, flag=False))
        if case == "V2 hang":
            res = run_once(patched, r, flag=True, behaviour={"gex_strike_v2": ("sleep", 3)}, timeout_env="1", writer_stub=stub)
            caught = res["elapsed"] > 2.0 or status_of(res) != "TIMEOUT after 1s"
        else:
            res = run_once(patched, r, flag=True, behaviour={"gex_strike_v2": "base"}, writer_stub=stub)
            caught = status_of(res) != "THREAD_ERROR SystemExit" or v1_view(res) != base
        print(f"mutant {name}: {'caught' if caught else 'SURVIVED'}")
        if not caught:
            errs.append(f"mutant {name} survived")
    return errs


def main() -> int:
    a = sys.argv[1:]
    quick = "--quick" in a
    script = Path(a[a.index("--script") + 1]) if "--script" in a else ROOT / "compute_gamma_metrics_local.py"
    patcher = Path(a[a.index("--patcher") + 1]) if "--patcher" in a else ROOT / "scripts" / "gamma_v2_writer_hook_patch.py"
    bound = float(a[a.index("--expect-bound") + 1]) if "--expect-bound" in a else None
    runs = load_runs(quick)
    print(f"golden runs loaded: {len(runs)} ({len({r['day'] for r in runs})} days); python {sys.version.split()[0]}")
    errs: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        patched = patched_copy(script, patcher, tmp)
        if "--cases" not in a:
            errs += check1(script, patched, runs)
        e7, info = check7(script, patched, runs, bound)
        errs += e7
        for i in info:
            print("INFO:", i)
        if "--cases" not in a:
            errs += mutants(script, patcher, tmp, runs)
    if errs:
        print("FAIL"); [print(" -", e) for e in errs[:40]]
        return 1
    print("PASS -- hook isolation: check 1 on %d runs, check 7 cases, 4 mutants caught" % len(runs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
