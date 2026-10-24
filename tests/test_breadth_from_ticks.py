#!/usr/bin/env python3
"""S100 R40 (ruling S100-I): ingest_breadth_from_ticks.py -- holiday gate, no-input path, ledger via
core.execution_log -- offline, with controls and mutants.

The writer is loaded from source with `supabase`, `dotenv`, `core.execution_log` and
`core.trading_calendar_gate` replaced by stubs; no database, network or credential.

Rule 0 -- what each cell would catch:
  B1 a holiday computes and writes          B4 low coverage stops writing history (the graph loses the session)
  B2 a minute with no ticks writes a zero row or exits non-zero (the S99-H precedent reversed)
  B3 a normal minute stops writing either table, or is not SUCCESS
  B5 a failed upsert reads as success       B6 a calendar error silences a live session (gate must fail open)
  B7 the hand-rolled ledger insert is back (status / kind / host lost)
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
WRITER = REPO / "ingest_breadth_from_ticks.py"


class Q:
    """Chained supabase-py query stub over in-memory tables."""
    def __init__(self, db, name):
        self.db, self.name, self.op, self.payload = db, name, "select", None
        self.lo = self.hi = None
    def select(self, *_a): return self
    def eq(self, *_a): return self
    def gte(self, *_a): return self
    def order(self, *_a, **_k): return self
    def range(self, lo, hi): self.lo, self.hi = lo, hi; return self
    def insert(self, payload): self.op, self.payload = "insert", payload; return self
    def upsert(self, payload, on_conflict=None): self.op, self.payload = "upsert", payload; return self
    def execute(self):
        self.db.calls.append((self.name, self.op))
        if self.op != "select":
            if self.name in self.db.fail:
                raise RuntimeError(f"simulated {self.name} failure")
            self.db.writes.setdefault(self.name, []).append(self.payload)
            return types.SimpleNamespace(data=[self.payload])
        rows = self.db.rows.get(self.name, [])
        return types.SimpleNamespace(data=rows[self.lo:self.hi + 1] if self.lo is not None else rows)


class DB:
    def __init__(self, ticks, prev, fail=()):
        self.rows = {"market_ticks": ticks, "equity_intraday_last": prev}
        self.calls, self.writes, self.fail = [], {}, set(fail)
    def table(self, name): return Q(self, name)


class Ledger:
    last = None
    def __init__(self, script_name, expected_writes=None, notes=None, **_k):
        Ledger.last = self; self.final = None; self.writes = {}
    def record_write(self, t, n): self.writes[t] = self.writes.get(t, 0) + n
    def complete(self, notes=None): self.final = ("SUCCESS", 0); return 0
    def exit_with_reason(self, reason, exit_code=0, notes=None, error_message=None):
        self.final = (reason, exit_code); return exit_code


def load(src: str, name: str, db: DB, trading=True, gate_raises=False):
    sup = types.ModuleType("supabase"); sup.create_client = lambda *_a: db
    dot = types.ModuleType("dotenv"); dot.load_dotenv = lambda *_a, **_k: None
    core = types.ModuleType("core"); core.__path__ = []
    el = types.ModuleType("core.execution_log"); el.ExecutionLog = Ledger
    gate = types.ModuleType("core.trading_calendar_gate")
    def _g():
        if gate_raises: raise RuntimeError("calendar down")
        return trading
    gate.is_trading_day_today = _g
    sys.modules.update({"supabase": sup, "dotenv": dot, "core": core, "core.execution_log": el,
                        "core.trading_calendar_gate": gate})
    os.environ.setdefault("SUPABASE_URL", "https://offline.invalid")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "offline-dummy-not-a-credential")
    mod = types.ModuleType(name); mod.__file__ = str(WRITER); sys.modules[name] = mod
    exec(compile(src, str(WRITER), "exec"), mod.__dict__)
    return mod


def ticks(n_up=60, n_down=40):
    t = [{"symbol": f"U{i}", "tradingsymbol": f"U{i}", "last_price": 101.0, "ts": "x"} for i in range(n_up)]
    return t + [{"symbol": f"D{i}", "tradingsymbol": f"D{i}", "last_price": 99.0, "ts": "x"} for i in range(n_down)]


def prev(syms):
    return [{"ticker": f"NSE:{s}", "last_price": 100.0} for s in syms]


def run(src, i, db, **kw):
    mod = load(src, f"bft_{i}", db, **kw)
    with contextlib.redirect_stdout(io.StringIO()):
        rc = mod.main()
    return rc, Ledger.last, db


def cells(src: str, tag: str) -> list[tuple[str, bool, str]]:
    out = []
    chk = lambda n, ok, f: out.append((n, bool(ok), f))
    t = ticks(); allsyms = [x["tradingsymbol"] for x in t]
    rc, led, db = run(src, tag + "1", DB(t, prev(allsyms)), trading=False)
    chk("B1 holiday -> HOLIDAY_GATE exit 0, no market_ticks read, nothing written",
        rc == 0 and led.final == ("HOLIDAY_GATE", 0) and db.calls == [] and db.writes == {}, "a holiday computes")
    rc, led, db = run(src, tag + "2", DB([], prev(allsyms)))
    chk("B2 no ticks -> nothing written, SKIPPED_NO_INPUT exit 0",
        rc == 0 and led.final == ("SKIPPED_NO_INPUT", 0) and db.writes == {}, "zero row written, or exit 1")
    rc, led, db = run(src, tag + "3", DB(t, prev(allsyms)))
    chk("B3 normal minute -> one history row + one intraday upsert, SUCCESS exit 0, writes recorded",
        rc == 0 and led.final == ("SUCCESS", 0) and len(db.writes.get("breadth_intraday_history", [])) == 1
        and len(db.writes.get("market_breadth_intraday", [])) == 1
        and led.writes == {"breadth_intraday_history": 1, "market_breadth_intraday": 1}, "a table not written or not recorded")
    rc, led, db = run(src, tag + "4", DB(t, prev(allsyms[:30])))
    chk("B4 coverage 30 % -> history row kept, no intraday upsert, SKIPPED_NO_INPUT exit 0",
        rc == 0 and led.final == ("SKIPPED_NO_INPUT", 0) and len(db.writes.get("breadth_intraday_history", [])) == 1
        and "market_breadth_intraday" not in db.writes, "low coverage behaviour changed")
    rc, led, db = run(src, tag + "5", DB(t, prev(allsyms), fail={"market_breadth_intraday"}))
    chk("B5 upsert fails -> DATA_ERROR exit 2", rc == 2 and led.final == ("DATA_ERROR", 2), "a failed write reads as success")
    rc, led, db = run(src, tag + "6", DB(t, prev(allsyms)), gate_raises=True)
    chk("B6 calendar unavailable -> fail open, the minute is computed", rc == 0 and led.final == ("SUCCESS", 0),
        "a calendar error silences a live session")
    names = {n for n, _ in db.calls}
    chk("B7 no hand-rolled script_execution_log insert", "script_execution_log" not in names,
        "the ledger is written outside core.execution_log again")
    return out


MUTANTS = {
    "M1 holiday gate removed": ("    if not _trading_day():\n", "    if False:\n",
                                {"B1 holiday -> HOLIDAY_GATE exit 0, no market_ticks read, nothing written"}),
    "M2 zero row back on no ticks": (
        '        log("  No EQ ticks found - WebSocket not running yet, or down. Nothing written.")\n',
        '        _write_history(sb, now_utc, now_ist.date(), 0, 0, 0, 0, 0, 0.0)\n',
        {"B2 no ticks -> nothing written, SKIPPED_NO_INPUT exit 0"}),
    "M3 gate fails closed": ('        log(f"  WARN: calendar gate unavailable ({e}); proceeding")\n        return True\n',
                             '        log(f"  WARN: calendar gate unavailable ({e}); proceeding")\n        return False\n',
                             {"B6 calendar unavailable -> fail open, the minute is computed"}),
    "M4 upsert failure swallowed": ('            return xlog.exit_with_reason(\n                "DATA_ERROR", exit_code=2,',
                                    '            return 0 or xlog.exit_with_reason(\n                "DATA_ERROR", exit_code=2,',
                                    set()),
}
# M4 is a control on the driver, not on a cell: `0 or f()` still calls f -- it must SURVIVE, proving the
# driver does not count every edit as a kill. Its expected outcome is checked separately below.


def main() -> int:
    src = WRITER.read_text(encoding="utf-8-sig")
    if "S100_R40_BREADTH" not in src:
        print("BREADTH FROM TICKS FAIL: writer lacks S100_R40_BREADTH"); return 1
    res = cells(src, "base")
    fails = [n for n, ok, _ in res if not ok]
    names = {n for n, _, _ in res}
    survivors, not_applied, unknown = [], [], []
    m4_all_pass = None
    for i, (mname, (old, new, must_fail)) in enumerate(MUTANTS.items()):
        unknown += [f"{mname}: {n}" for n in must_fail if n not in names]
        if src.count(old) != 1:
            not_applied.append(mname); continue
        mres = {n: ok for n, ok, _ in cells(src.replace(old, new, 1), f"m{i}_")}
        if mname.startswith("M4"):
            m4_all_pass = all(mres.values())
        survivors += [f"{mname}: {n}" for n in must_fail if mres.get(n, True)]
    for n, ok, f in res:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}" + ("" if ok else f"   (fails if: {f})"))
    print(f"  {'PASS' if m4_all_pass else 'FAIL'}  M4 control: an edit with no behavioural effect kills no cell")
    killed = sum(len(v[2]) for k, v in MUTANTS.items() if k not in not_applied) - len(survivors)
    print(f"  cells {len(res)}, failing {len(fails)}; mutants {len(MUTANTS)} (M4 a no-op control), not applied "
          f"{len(not_applied)}, mutant cells killed {killed}, surviving {len(survivors)} (must be 0)")
    for s in not_applied: print(f"  MUTANT NOT APPLIED: {s}")
    for s in unknown: print(f"  MUTANT NAMES NO CELL: {s}")
    for s in survivors: print(f"  MUTANT SURVIVED: {s}")
    if fails or survivors or not_applied or unknown or not m4_all_pass:
        print("BREADTH FROM TICKS FAIL"); return 1
    print("BREADTH FROM TICKS ALL PASS"); return 0


if __name__ == "__main__":
    sys.exit(main())
