#!/usr/bin/env python3
"""S100 TD-S81-NEW-11 (TD-S81-NEW-11 Proper fix; no new ruling): the chain ingest's Dhan retry predicate -- offline, with mutants.

The three predicate functions are taken from ingest_option_chain_local.py's own source (ast), not
re-implemented, and driven through the real gamma_engine_retry_utils.retry_call with time.sleep stubbed.
No network, no Dhan, no database.

Rule 0 -- what each cell would catch:
  C1 a single 500 still drops the cycle (the defect)    C4 an auth failure is retried (masks a dead token)
  C2 a persistent 500 retries without bound (the cycle overruns the runner's 120 s wait)
  C3 the 429 behaviour of ENH-99 changed                C5 the 5xx budget leaks across calls
  C6 a call site still uses the 429-only predicate      C7 the worst-case delay no longer fits 120 s
Mutants M1-M3 each remove one part; a mutant whose named cells all pass means those cells assert nothing.
"""
from __future__ import annotations

import ast
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INGEST = REPO / "ingest_option_chain_local.py"
WANT = ("is_dhan_429", "is_dhan_5xx", "dhan_retry_predicate")
E500 = RuntimeError('Dhan HTTP error | status=500 | path=/v2/optionchain | response={"800":"Internal Server Error"}')
E429 = RuntimeError('Dhan HTTP error | status=429 | path=/v2/optionchain | response={"805":"Too many requests"}')
E401 = RuntimeError('Dhan HTTP error | status=401 | response={"808":"Authentication Failed"}')


def extract(src: str) -> types.ModuleType:
    tree = ast.parse(src)
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in WANT)
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "DHAN_5XX_RETRIES" for t in n.targets))]
    mod = types.ModuleType("chain_predicates")
    exec(compile(ast.Module(body=keep, type_ignores=[]), str(INGEST), "exec"), mod.__dict__)
    return mod


def retry_util():
    sys.path.insert(0, str(REPO))
    import gamma_engine_retry_utils as R
    sleeps = []
    R.time.sleep = sleeps.append          # module-level `import time` in the util
    return R, sleeps


def drive(R, pred, seq):
    """seq: exceptions to raise in order, then succeed. Returns (ok, calls)."""
    calls = {"n": 0}

    def fn():
        i = calls["n"]; calls["n"] += 1
        if i < len(seq):
            raise seq[i]
        return {"data": "ok"}
    try:
        R.retry_call(fn, attempts=6, delay_seconds=15.0, backoff_multiplier=1.5, retry_predicate=pred, label="t")
        return True, calls["n"]
    except Exception:
        return False, calls["n"]


def cells(src: str) -> list[tuple[str, bool, str]]:
    out = []
    chk = lambda n, ok, f: out.append((n, bool(ok), f))
    P = extract(src)
    R, sleeps = retry_util()
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        r1 = drive(R, P.dhan_retry_predicate(), [E500])
        r2 = drive(R, P.dhan_retry_predicate(), [E500] * 5)
        r3 = drive(R, P.dhan_retry_predicate(), [E429] * 5)
        r4 = drive(R, P.dhan_retry_predicate(), [E401])
        pred = P.dhan_retry_predicate()
        a = drive(R, pred, [E500, E500])
        b = drive(R, P.dhan_retry_predicate(), [E500, E500])
    chk("C1 one 500 -> retried, the call succeeds (2 calls)", r1 == (True, 2), "a single 500 drops the cycle")
    chk("C2 persistent 500 -> gives up after 1 + 2 retries (3 calls)", r2 == (False, 3), "unbounded 5xx retries")
    chk("C3 five 429s then OK -> retried as before (6 calls)", r3 == (True, 6), "ENH-99's 429 behaviour changed")
    chk("C4 401 -> fails fast (1 call)", r4 == (False, 1), "a dead token retried")
    chk("C5 each call gets its own 2-retry budget", a == (True, 3) and b == (True, 3), "budget shared across calls")
    chk("C6 all three Dhan call sites use dhan_retry_predicate()",
        src.count("retry_predicate=dhan_retry_predicate(),") == 3 and "retry_predicate=is_dhan_429," not in src,
        "a call site still fails fast on 500")
    worst = sum(15.0 * 1.5 ** k for k in range(getattr(P, "DHAN_5XX_RETRIES", 99)))
    chk(f"C7 worst-case 5xx wait {worst:.1f} s < the runner's 120 s cycle wait", worst < 120, "a retried cycle misses the runner")
    return out


MUTANTS = {
    "M1 5xx not retryable": ("        if is_dhan_5xx(exc):\n", "        if False:\n",
                             {"C1 one 500 -> retried, the call succeeds (2 calls)",
                              "C5 each call gets its own 2-retry budget"}),
    "M2 5xx budget removed": ("            return seen[\"5xx\"] <= max_5xx\n", "            return True\n",
                              {"C2 persistent 500 -> gives up after 1 + 2 retries (3 calls)"}),
    "M3 one call site reverted": ("retry_predicate=dhan_retry_predicate(),", "retry_predicate=is_dhan_429,",
                                  {"C6 all three Dhan call sites use dhan_retry_predicate()"}),
}


def main() -> int:
    src = INGEST.read_text(encoding="utf-8-sig")
    if "S100_CHAIN_5XX" not in src:
        print("CHAIN DHAN RETRY FAIL: ingest_option_chain_local.py lacks S100_CHAIN_5XX"); return 1
    res = cells(src)
    fails = [n for n, ok, _ in res if not ok]
    names = {n for n, _, _ in res}
    survivors, not_applied, unknown = [], [], []
    for mname, (old, new, must_fail) in MUTANTS.items():
        unknown += [f"{mname}: {n}" for n in must_fail if n not in names]
        if old not in src:
            not_applied.append(mname); continue
        mres = {n: ok for n, ok, _ in cells(src.replace(old, new, 1))}
        survivors += [f"{mname}: {n}" for n in must_fail if mres.get(n, True)]
    for n, ok, f in res:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}" + ("" if ok else f"   (fails if: {f})"))
    killed = sum(len(v[2]) for k, v in MUTANTS.items() if k not in not_applied) - len(survivors)
    print(f"  cells {len(res)}, failing {len(fails)}; mutants {len(MUTANTS)}, not applied {len(not_applied)}, "
          f"mutant cells killed {killed}, surviving {len(survivors)} (must be 0)")
    for s in not_applied: print(f"  MUTANT NOT APPLIED: {s}")
    for s in unknown: print(f"  MUTANT NAMES NO CELL: {s}")
    for s in survivors: print(f"  MUTANT SURVIVED: {s}")
    if fails or survivors or not_applied or unknown:
        print("CHAIN DHAN RETRY FAIL"); return 1
    print("CHAIN DHAN RETRY ALL PASS"); return 0


if __name__ == "__main__":
    sys.exit(main())
