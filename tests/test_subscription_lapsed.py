#!/usr/bin/env python3
"""S100-M (b): SUBSCRIPTION_LAPSED -- a Dhan 806 / DH-902 plan lapse is not logged as TOKEN_EXPIRED -- offline, with mutants.

Inputs are the real 2026-10-21 error texts from script_execution_log (read 2026-10-24 12:08 IST). Classifier functions
are lifted from each writer's own source (ast) and executed; the writers' exit paths are checked on their source,
because their main() needs a live Dhan session. preopen_probe.py's run() is covered by test_preopen_probe.py P2.

Rule 0 -- what each cell would catch:
  C1 core rejects the reason (coerced to CRASH) or the ledger status is not MISSING
  C2 the chain ingest logs the 10-21 806 as TOKEN_EXPIRED     C3 a real token failure is relabelled SUBSCRIPTION
  C4 a number containing 806 (strike 71806, LTP 806.45) is read as a lapse
  C5 capture_spot_1m_v2 / capture_cas_close test the token before the plan (the lapse is HTTP 401 too) or never exit
     SUBSCRIPTION_LAPSED                                       C6 the writers' patterns drift apart
  C7 the CHECK DDL and VALID_EXIT_REASONS disagree (a row refused by the database)
  C8 the alert daemon does not alert on it
Mutants M1-M6 each remove one part; a mutant whose named cells all pass means those cells assert nothing.
"""
from __future__ import annotations

import ast
import re
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FILES = {k: REPO / k for k in ("core/execution_log.py", "ingest_option_chain_local.py", "capture_spot_1m_v2.py",
                               "capture_cas_close.py", "preopen_probe.py", "merdian_pipeline_alert_daemon.py")}
DDL = REPO / "sql" / "2026-10-24_s100_m_exit_reason_subscription.sql"
CHAIN_1021 = ('get_expiry_list failed: Dhan HTTP error | status=401 | path=/v2/optionchain/expirylist | '
              'response={"data":{"806":"Data APIs not Subscribed"},"status":"failed"}')
SPOT_1021 = ('Dhan /charts/intraday NIFTY HTTP 401: {"errorType":"Invalid_Access","errorCode":"DH-902",'
             '"errorMessage":"This API requires a PLUS subscription. Current plan: FREE"}')
TOKEN_401 = 'Dhan HTTP error | status=401 | response={"errorType":"Invalid_Authentication","errorCode":"DH-901","errorMessage":"Client ID or user generated access token is invalid or expired."}'
E500 = 'Dhan HTTP error | status=500 | path=/v2/optionchain | response={"800":"Internal Server Error"}'
STRIKE = 'Dhan HTTP error | status=401 | Authentication Failed | strike 71806 CE ltp 806.45'


def lift(src: str, names: set[str], assigns: set[str] = frozenset(), imports=True) -> types.ModuleType:
    tree = ast.parse(src)
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names)
            or (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in assigns for t in n.targets))
            or (imports and isinstance(n, ast.Import) and any(a.asname == "_re_s100m" for a in n.names))]
    mod = types.ModuleType("lifted")
    exec(compile(ast.Module(body=keep, type_ignores=[]), "lifted", "exec"), mod.__dict__)
    return mod


def valid_set(src: str) -> set[str]:
    for n in ast.parse(src).body:
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "VALID_EXIT_REASONS" for t in n.targets):
            return {e.value for e in n.value.args[0].elts}
    return set()


def cells(S: dict[str, str]) -> list[tuple[str, bool, str]]:
    out = []
    chk = lambda n, ok, f: out.append((n, bool(ok), f))
    core = S["core/execution_log.py"]
    V = valid_set(core)
    L = lift(core, {"_ledger_status"})
    chk("C1 core accepts SUBSCRIPTION_LAPSED (12 reasons), ledger status MISSING",
        "SUBSCRIPTION_LAPSED" in V and len(V) == 12 and L._ledger_status("SUBSCRIPTION_LAPSED", None) == "MISSING",
        "coerced to CRASH, or ledger status wrong")
    C = lift(S["ingest_option_chain_local.py"], {"is_dhan_subscription_error", "_classify_dhan_error"}, {"_DHAN_SUBSCRIPTION_RE"})
    cls = lambda m: C._classify_dhan_error(RuntimeError(m))
    chk("C2 chain: the real 10-21 806 text -> SUBSCRIPTION_LAPSED", cls(CHAIN_1021) == "SUBSCRIPTION_LAPSED",
        "the lapse is logged as TOKEN_EXPIRED")
    chk("C3 chain: DH-901 token text -> TOKEN_EXPIRED, 500 -> DATA_ERROR",
        cls(TOKEN_401) == "TOKEN_EXPIRED" and cls(E500) == "DATA_ERROR", "a token failure relabelled")
    chk("C4 chain: '71806' / '806.45' in a 401 -> TOKEN_EXPIRED, not a lapse", cls(STRIKE) == "TOKEN_EXPIRED",
        "a number containing 806 read as a lapse")
    ok5 = True
    for f, var, errs in (("capture_spot_1m_v2.py", "err_msg", "fetch_errors"), ("capture_cas_close.py", "err", "errors")):
        s = S[f]
        W = lift(s, {"is_dhan_subscription_error"}, {"_DHAN_SUBSCRIPTION_RE"})
        sub_test = f"if is_dhan_subscription_error({var}):"
        tok_test = f'elif "401" in {var}'
        i_sub, i_tok = s.find(sub_test), s.find(tok_test)
        i_exit_sub = s.find("    if sub_failed:")
        i_exit_tok = s.find("    if auth_failed:")
        exit_block = s[i_exit_sub:i_exit_tok] if 0 <= i_exit_sub < i_exit_tok else ""
        ok5 &= (W.is_dhan_subscription_error(SPOT_1021) and not W.is_dhan_subscription_error(TOKEN_401)
                and 0 <= i_sub < i_tok and s.count("sub_failed = True") == 1
                and '"SUBSCRIPTION_LAPSED"' in exit_block and errs in exit_block)
    chk("C5 spot + CAS close: plan tested before token; exit SUBSCRIPTION_LAPSED before TOKEN_EXPIRED", ok5,
        "the 401-shaped lapse still lands as TOKEN_EXPIRED")
    pats = {f: re.findall(r"^_DHAN_SUBSCRIPTION_RE = .*$", S[f], re.M)
            for f in ("ingest_option_chain_local.py", "capture_spot_1m_v2.py", "capture_cas_close.py")}
    P = lift(S["preopen_probe.py"], {"classify"}, imports=False)
    chk("C6 one pattern in the three writers; the probe agrees on the real texts",
        all(len(v) == 1 for v in pats.values()) and len({v[0] for v in pats.values()}) == 1
        and P.classify(RuntimeError(CHAIN_1021)) == "SUBSCRIPTION" and P.classify(RuntimeError(SPOT_1021)) == "SUBSCRIPTION"
        and P.classify(RuntimeError(TOKEN_401)) == "TOKEN", "the writers classify the same text differently")
    m = re.search(r"ARRAY\[(.*?)\]::text\[\]", S["ddl"], re.S)
    ddl = set(re.findall(r"'([A-Z_]+)'", m.group(1))) if m else set()
    chk("C7 the CHECK DDL lists exactly VALID_EXIT_REASONS", ddl == V and len(ddl) == 12, "a row the database refuses")
    d = S["merdian_pipeline_alert_daemon.py"]
    blk = d[d.find("ALERT_EXIT_REASONS = ("):][:400]
    chk("C8 the alert daemon alerts on SUBSCRIPTION_LAPSED", '"SUBSCRIPTION_LAPSED"' in blk.split(")")[0],
        "a lapse alerts nobody")
    return out


MUTANTS = {
    "M1 chain plan check removed": ("ingest_option_chain_local.py",
        '    if is_dhan_subscription_error(msg):   # S100_SUBSCRIPTION_LAPSED\n', '    if False:\n',
        {"C2 chain: the real 10-21 806 text -> SUBSCRIPTION_LAPSED"}),
    "M2 core set not widened": ("core/execution_log.py",
        '    "SUBSCRIPTION_LAPSED",   # S100_SUBSCRIPTION_LAPSED (S100-M): Dhan 806 / DH-902\n', '',
        {"C1 core accepts SUBSCRIPTION_LAPSED (12 reasons), ledger status MISSING",
         "C7 the CHECK DDL lists exactly VALID_EXIT_REASONS"}),
    "M3 spot tests token first": ("capture_spot_1m_v2.py",
        '            if is_dhan_subscription_error(err_msg):   # S100_SUBSCRIPTION_LAPSED\n                sub_failed = True\n'
        '            elif "401" in err_msg',
        '            if "401" in err_msg',
        {"C5 spot + CAS close: plan tested before token; exit SUBSCRIPTION_LAPSED before TOKEN_EXPIRED"}),
    "M4 CAS exit block removed": ("capture_cas_close.py",
        '    if sub_failed:   # S100_SUBSCRIPTION_LAPSED\n        return log.exit_with_reason("SUBSCRIPTION_LAPSED", exit_code=1,\n'
        '                                    error_message="; ".join(errors)[:2000])\n\n', '',
        {"C5 spot + CAS close: plan tested before token; exit SUBSCRIPTION_LAPSED before TOKEN_EXPIRED"}),
    "M5 chain boundary dropped": ("ingest_option_chain_local.py", r'r"(?<![\d.])806(?![\d.])', 'r"806',
        {"C4 chain: '71806' / '806.45' in a 401 -> TOKEN_EXPIRED, not a lapse",
         "C6 one pattern in the three writers; the probe agrees on the real texts"}),
    "M6 daemon not told": ("merdian_pipeline_alert_daemon.py", '    "SUBSCRIPTION_LAPSED",   # S100_SUBSCRIPTION_LAPSED\n', '',
        {"C8 the alert daemon alerts on SUBSCRIPTION_LAPSED"}),
}


def main() -> int:
    S = {k: p.read_text(encoding="utf-8-sig") for k, p in FILES.items()}
    S["ddl"] = DDL.read_text(encoding="utf-8-sig") if DDL.exists() else ""
    if not all("S100_SUBSCRIPTION_LAPSED" in S[k] for k in FILES):
        print("SUBSCRIPTION LAPSED FAIL: a file lacks S100_SUBSCRIPTION_LAPSED"); return 1
    res = cells(S)
    fails = [n for n, ok, _ in res if not ok]
    names = {n for n, _, _ in res}
    survivors, not_applied, unknown = [], [], []
    for mname, (f, old, new, must_fail) in MUTANTS.items():
        unknown += [f"{mname}: {n}" for n in must_fail if n not in names]
        if S[f].count(old) != 1:
            not_applied.append(mname); continue
        M = dict(S); M[f] = S[f].replace(old, new, 1)
        try:
            mres = {n: ok for n, ok, _ in cells(M)}
        except Exception as e:
            mres = {n: False for n in must_fail}; print(f"  ({mname} raised {type(e).__name__}: {e})")
        survivors += [f"{mname}: {n}" for n in must_fail if mres.get(n, True)]
    for n, ok, f in res:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}" + ("" if ok else f"   (fails if: {f})"))
    killed = sum(len(v[3]) for k, v in MUTANTS.items() if k not in not_applied) - len(survivors)
    print(f"  cells {len(res)}, failing {len(fails)}; mutants {len(MUTANTS)}, not applied {len(not_applied)}, "
          f"mutant cells killed {killed}, surviving {len(survivors)} (must be 0)")
    for s in not_applied: print(f"  MUTANT NOT APPLIED: {s}")
    for s in unknown: print(f"  MUTANT NAMES NO CELL: {s}")
    for s in survivors: print(f"  MUTANT SURVIVED: {s}")
    if fails or survivors or not_applied or unknown:
        print("SUBSCRIPTION LAPSED FAIL"); return 1
    print("SUBSCRIPTION LAPSED ALL PASS"); return 0


if __name__ == "__main__":
    sys.exit(main())
