#!/usr/bin/env python3
"""S102_TD_S77_NEW_8 -- refresh_equity_intraday_last.py writes its ledger row through core.execution_log.

The writer is loaded from source with `supabase`, `dotenv`, `kiteconnect` and `core.execution_log`
replaced by stubs; no database, network or credential.

Rule 0 -- what each cell would catch:
  E1 a normal morning is not SUCCESS, or the write is not recorded, or the ledger is hand-rolled again
  E2 a short universe writes rows, or exits 0
  E3 a Kite token error is not labelled TOKEN_EXPIRED (or exits 0)
  E4 a non-token Kite error is not DATA_ERROR exit 1
  E5 a failed upsert reads as success
  E6 the expected floor is not declared to the ledger (contract_met could not go false on a short payload)
  E7 the module cannot be imported (the stray `PYEOF` line at the end of the file, removed in S102)
Mutants M1-M4 each remove one part; a mutant whose named cells all pass means those cells assert nothing.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WRITER = REPO / "refresh_equity_intraday_last.py"


class Q:
    def __init__(self, db, name):
        self.db, self.name, self.op, self.payload, self.lo = db, name, "select", None, None
    def select(self, *_a): return self
    def eq(self, *_a): return self
    def range(self, lo, hi): self.lo, self.hi = lo, hi; return self
    def insert(self, payload): self.op, self.payload = "insert", payload; return self
    def upsert(self, payload, on_conflict=None): self.op, self.payload = "upsert", payload; return self
    def execute(self):
        self.db.calls.append((self.name, self.op))
        if self.op != "select":
            if self.name in self.db.fail:
                raise RuntimeError(f"simulated {self.name} failure")
            self.db.writes.setdefault(self.name, []).extend(self.payload if isinstance(self.payload, list) else [self.payload])
            return types.SimpleNamespace(data=[])
        rows = self.db.rows.get(self.name, [])
        return types.SimpleNamespace(data=rows[self.lo:self.hi + 1] if self.lo is not None else rows)


class DB:
    def __init__(self, n_members, fail=()):
        self.rows = {"breadth_universe_members": [{"symbol": f"S{i}", "exchange": "NSE"} for i in range(n_members)]}
        self.calls, self.writes, self.fail = [], {}, set(fail)
    def table(self, name): return Q(self, name)


class Kite:
    err = None
    def __init__(self, api_key=None): pass
    def set_access_token(self, _t): pass
    def ohlc(self, chunk):
        if Kite.err:
            raise RuntimeError(Kite.err)
        return {s: {"ohlc": {"close": 100.0}} for s in chunk}


class Ledger:
    last = None
    def __init__(self, script_name, expected_writes=None, notes=None, **_k):
        Ledger.last = self; self.final = None; self.writes = {}; self.expected = dict(expected_writes or {})
    def record_write(self, t, n): self.writes[t] = self.writes.get(t, 0) + n
    def complete(self, notes=None): self.final = ("SUCCESS", 0); return 0
    def exit_with_reason(self, reason, exit_code=0, notes=None, error_message=None):
        self.final = (reason, exit_code); return exit_code


def load(src, name, db):
    sup = types.ModuleType("supabase"); sup.create_client = lambda *_a: db
    dot = types.ModuleType("dotenv"); dot.load_dotenv = lambda *_a, **_k: None
    kc = types.ModuleType("kiteconnect"); kc.KiteConnect = Kite
    core = types.ModuleType("core"); core.__path__ = []
    el = types.ModuleType("core.execution_log"); el.ExecutionLog = Ledger
    sys.modules.update({"supabase": sup, "dotenv": dot, "kiteconnect": kc, "core": core, "core.execution_log": el})
    for k in ("ZERODHA_API_KEY", "ZERODHA_ACCESS_TOKEN", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        os.environ.setdefault(k, "offline-dummy-not-a-credential")
    mod = types.ModuleType(name); mod.__file__ = str(WRITER); mod.__name__ = name; sys.modules[name] = mod
    exec(compile(src, str(WRITER), "exec"), mod.__dict__)
    return mod


def run(src, tag, db, kite_err=None):
    Kite.err = kite_err; Ledger.last = None
    try:
        mod = load(src, f"reil_{tag}", db)
        with contextlib.redirect_stdout(io.StringIO()):
            rc = mod.main()
    except Exception:  # a crash is a failed cell, never a crashed driver
        return None, types.SimpleNamespace(final=None, writes={}, expected={}), db
    return rc, Ledger.last, db


def cells(src, tag):
    out = []
    chk = lambda n, ok, f: out.append((n, bool(ok), f))
    rc, led, db = run(src, tag + "1", DB(1313))
    chk("E1 normal morning -> SUCCESS exit 0, 1313 rows upserted and recorded, no hand-rolled ledger insert",
        rc == 0 and led is not None and led.final == ("SUCCESS", 0)
        and len(db.writes.get("equity_intraday_last", [])) == 1313
        and led.writes == {"equity_intraday_last": 1313}
        and "script_execution_log" not in {n for n, _ in db.calls}, "not SUCCESS / not recorded / hand-rolled")
    rc, led, db = run(src, tag + "2", DB(50))
    chk("E2 universe 50 -> DATA_ERROR exit 1, nothing written",
        rc == 1 and led.final == ("DATA_ERROR", 1) and db.writes == {}, "a short universe writes or exits 0")
    rc, led, db = run(src, tag + "3", DB(1313), kite_err="TokenException: Incorrect `api_key` or `access_token`.")
    chk("E3 Kite token error -> TOKEN_EXPIRED exit 1, nothing written",
        rc == 1 and led.final == ("TOKEN_EXPIRED", 1) and db.writes == {}, "token error mislabelled")
    rc, led, db = run(src, tag + "4", DB(1313), kite_err="Read timed out")
    chk("E4 other Kite error -> DATA_ERROR exit 1", rc == 1 and led.final == ("DATA_ERROR", 1), "mislabelled")
    rc, led, db = run(src, tag + "5", DB(1313, fail={"equity_intraday_last"}))
    chk("E5 upsert fails -> DATA_ERROR exit 1", rc == 1 and led.final == ("DATA_ERROR", 1), "a failed write reads as success")
    rc, led, db = run(src, tag + "6", DB(1313))
    chk("E6 ledger declares the 1000-row floor", led.expected == {"equity_intraday_last": 1000}, "no floor declared")
    try:
        load(src, f"reil_{tag}7", DB(1313)); ok7 = True
    except Exception:
        ok7 = False
    chk("E7 module imports cleanly (no trailing stray statement)", ok7, "the stray PYEOF line is back")
    return out


MUTANTS = {
    "M1 success not recorded": ('    xlog.record_write("equity_intraday_last", len(rows))\n', "",
                                {"E1 normal morning -> SUCCESS exit 0, 1313 rows upserted and recorded, no hand-rolled ledger insert"}),
    "M2 token error as DATA_ERROR": ("        return xlog.exit_with_reason(_classify_exit_reason(False, str(e)), exit_code=1,",
                                     '        return xlog.exit_with_reason("DATA_ERROR", exit_code=1,',
                                     {"E3 Kite token error -> TOKEN_EXPIRED exit 1, nothing written"}),
    "M3 floor dropped": ('        expected_writes={"equity_intraday_last": EXPECTED_MIN_ROWS},\n', "        expected_writes={},\n",
                         {"E6 ledger declares the 1000-row floor"}),
    "M4 stray PYEOF back": ("    raise SystemExit(main())\n", "    raise SystemExit(main())\nPYEOF\n",
                            {"E7 module imports cleanly (no trailing stray statement)"}),
}


def main() -> int:
    src = WRITER.read_text(encoding="utf-8-sig")
    if "S102_TD_S77_NEW_8" not in src:
        print("REFRESH EQUITY INTRADAY LAST FAIL: writer lacks S102_TD_S77_NEW_8"); return 1
    res = cells(src, "base")
    fails = [n for n, ok, _ in res if not ok]
    names = {n for n, _, _ in res}
    survivors, not_applied, unknown = [], [], []
    for i, (mname, (old, new, must_fail)) in enumerate(MUTANTS.items()):
        unknown += [f"{mname}: {n}" for n in must_fail if n not in names]
        if src.count(old) != 1:
            not_applied.append(mname); continue
        mres = {n: ok for n, ok, _ in cells(src.replace(old, new, 1), f"m{i}_")}
        survivors += [f"{mname}: {n}" for n in must_fail if mres.get(n, True)]
    for n, ok, f in res:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}" + ("" if ok else f"   (fails if: {f})"))
    print(f"  cells {len(res)}, failing {len(fails)}; mutants {len(MUTANTS)}, not applied {len(not_applied)}, "
          f"surviving {len(survivors)} (must be 0)")
    for s in not_applied: print(f"  MUTANT NOT APPLIED: {s}")
    for s in unknown: print(f"  MUTANT NAMES NO CELL: {s}")
    for s in survivors: print(f"  MUTANT SURVIVED: {s}")
    if fails or survivors or not_applied or unknown:
        print("REFRESH EQUITY INTRADAY LAST FAIL"); return 1
    print("REFRESH EQUITY INTRADAY LAST ALL PASS"); return 0


if __name__ == "__main__":
    sys.exit(main())
