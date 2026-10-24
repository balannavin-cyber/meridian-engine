#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S99 R2 / TD-S97-NEW-9, -10 (rulings S99-H, S99-I) -- tests for the WCB writer's no-input guard.

Target under test: build_wcb_snapshot_local.py at the repo root, loaded from source with its
collaborators stubbed (core.supabase_client, core.execution_log, gamma_engine_retry_utils).
core.ts_parse is the real module (pure Python). No network, no database, no credentials, no
fixtures, no golden day.

Claim: the writer upserts ONLY when the breadth ts is <= 10 min old AND at least one constituent
is priced; otherwise it writes nothing and exits 0 with SKIPPED_NO_INPUT. Measured defect it
guards (2026-10-24 read): every session's first cycle (08:31 IST) wrote a zero row onto the
previous session's 15:40 breadth ts.

Rule 0: each cell states what would make it fail, and three mutants prove the guard's three
parts are each load-bearing -- a mutant whose cells all still pass means the cells assert nothing.

Run:  ( ulimit -v 700000; python3 tests/test_wcb_no_input.py )
"""
from __future__ import annotations

import importlib.util
import io
import sys
import types
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WRITER = REPO / "build_wcb_snapshot_local.py"

UTC = timezone.utc
NOW_SESSION = datetime(2026, 10, 26, 7, 32, 10, tzinfo=UTC)    # Mon 13:02 IST
NOW_PREOPEN = datetime(2026, 10, 26, 3, 1, 20, tzinfo=UTC)     # Mon 08:31 IST, first cycle
FRI_1540 = "2026-10-23T10:10:05.597305+00:00"                  # Friday's last breadth ts
HOL_0920 = "2026-10-20T03:50:05.887201+00:00"                  # the 10-20 holiday breadth row
NOW_AFTER_HOL = datetime(2026, 10, 21, 3, 1, 19, tzinfo=UTC)

WEIGHTS = [{"ticker": "AAA", "company_name": "A", "weight_pct": 60.0},
           {"ticker": "BBB", "company_name": "B", "weight_pct": 40.0}]
PREV = [{"ticker": "AAA", "last_price": 100.0}, {"ticker": "BBB", "last_price": 200.0}]
DAILY = [{"ticker": t, "trade_date": "2026-10-23", "dma10": 1, "dma20": 1, "dma40": 1,
          "above_10": True, "above_20": True, "above_40": False,
          "dma10_gt_20": True, "dma20_gt_40": False} for t in ("AAA", "BBB")]


def ticks(now):
    return [{"tradingsymbol": "AAA", "last_price": 101.0, "ts": (now - timedelta(seconds=30)).isoformat()},
            {"tradingsymbol": "BBB", "last_price": 199.0, "ts": (now - timedelta(seconds=40)).isoformat()}]


def pg(dt: datetime) -> str:
    return dt.isoformat()


class FakeSB:
    def __init__(self, data):
        self.data = data
        self.upserts = []

    def select(self, table, filters=None, order=None, limit=None, offset=0, columns=None):
        rows = self.data.get(table, [])
        return list(rows[offset:offset + limit]) if limit else list(rows)

    def upsert(self, table, rows, on_conflict=None):
        self.upserts.append((table, rows, on_conflict))
        return rows


class StubLog:
    last = None

    def __init__(self, **kw):
        self.kw = kw
        self.reason = None
        self.exit_code = None
        self.writes = {}
        StubLog.last = self

    def record_write(self, table, n):
        self.writes[table] = self.writes.get(table, 0) + n

    def complete(self, notes=None):
        self.reason, self.exit_code = "SUCCESS", 0
        return 0

    def exit_with_reason(self, reason, exit_code=0, notes=None, error_message=None):
        self.reason, self.exit_code, self.error = reason, exit_code, error_message
        return exit_code


def load(source: str):
    core = types.ModuleType("core"); core.__path__ = [str(REPO / "core")]
    sbmod = types.ModuleType("core.supabase_client"); sbmod.SupabaseClient = object
    elmod = types.ModuleType("core.execution_log"); elmod.ExecutionLog = StubLog
    rt = types.ModuleType("gamma_engine_retry_utils"); rt.retry_call = lambda fn, **kw: fn()
    sys.modules.update({"core": core, "core.supabase_client": sbmod,
                        "core.execution_log": elmod, "gamma_engine_retry_utils": rt})
    spec = importlib.util.spec_from_file_location("core.ts_parse", REPO / "core" / "ts_parse.py")
    tsm = importlib.util.module_from_spec(spec); sys.modules["core.ts_parse"] = tsm; spec.loader.exec_module(tsm)
    mod = types.ModuleType("wcb_under_test")
    exec(compile(source, str(WRITER), "exec"), mod.__dict__)
    return mod


def run_case(mod, now, breadth_ts, tick_rows, prev=PREV, daily=DAILY, breadth_none=False):
    data = {"index_constituent_weights": WEIGHTS, "market_ticks": tick_rows,
            "equity_intraday_last": prev, "breadth_indicators_daily": daily,
            "latest_market_breadth_intraday": [] if breadth_none else [{"ts": breadth_ts}]}
    sb = FakeSB(data)
    mod.SupabaseClient = lambda: sb
    mod._now_utc = lambda: now
    sys.argv = ["build_wcb_snapshot_local.py", "NIFTY"]
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = mod.main()
    return rc, sb, StubLog.last, buf.getvalue()


def cells(mod):
    out = []
    def chk(name, cond, fail_if):
        out.append((name, bool(cond), fail_if))
    # T1 healthy, breadth 2 min old: exactly one upsert, SUCCESS, exit 0.
    rc, sb, lg, _ = run_case(mod, NOW_SESSION, pg(NOW_SESSION - timedelta(minutes=2)), ticks(NOW_SESSION))
    chk("T1 healthy writes 1 row", len(sb.upserts) == 1 and lg.reason == "SUCCESS" and rc == 0, "0 upserts or a skip")
    chk("T1 row carries 2 constituents", sb.upserts and sb.upserts[0][1][0]["constituent_count"] == 2, "count != 2")
    # T2 Monday first cycle on Friday's 15:40 ts, no ticks: nothing written, skip, exit 0.
    rc, sb, lg, o = run_case(mod, NOW_PREOPEN, FRI_1540, [])
    chk("T2 pre-open writes nothing", len(sb.upserts) == 0, "an upsert onto Friday 15:40")
    chk("T2 reason SKIPPED_NO_INPUT, exit 0", lg.reason == "SKIPPED_NO_INPUT" and rc == 0, "other reason or exit 1")
    # T3 stale breadth (20 min) although ticks exist: nothing written.
    rc, sb, lg, _ = run_case(mod, NOW_SESSION, pg(NOW_SESSION - timedelta(minutes=20)), ticks(NOW_SESSION))
    chk("T3 stale breadth with ticks writes nothing", len(sb.upserts) == 0 and lg.reason == "SKIPPED_NO_INPUT", "upsert on a stale key")
    # T4 fresh breadth, no ticks (feed down mid-session): nothing written.
    rc, sb, lg, _ = run_case(mod, NOW_SESSION, pg(NOW_SESSION - timedelta(minutes=1)), [])
    chk("T4 no ticks writes nothing", len(sb.upserts) == 0 and lg.reason == "SKIPPED_NO_INPUT" and rc == 0, "upsert of a zero row")
    # T5 fresh breadth, ticks, but no prior close and no DMA rows: 0 priced -> nothing written.
    rc, sb, lg, _ = run_case(mod, NOW_SESSION, pg(NOW_SESSION - timedelta(minutes=1)), ticks(NOW_SESSION), prev=[], daily=[])
    chk("T5 zero constituents priced writes nothing", len(sb.upserts) == 0 and lg.reason == "SKIPPED_NO_INPUT", "upsert of a zero row")
    # T6 no breadth row at all: nothing written (the old code fell back to now()).
    rc, sb, lg, _ = run_case(mod, NOW_SESSION, None, ticks(NOW_SESSION), breadth_none=True)
    chk("T6 no breadth row writes nothing", len(sb.upserts) == 0 and lg.reason == "SKIPPED_NO_INPUT", "upsert keyed on now()")
    # T7 / T8 the boundary: 600 s writes, 601 s skips.
    rc, sb, lg, _ = run_case(mod, NOW_SESSION, pg(NOW_SESSION - timedelta(seconds=600)), ticks(NOW_SESSION))
    chk("T7 age 600 s writes", len(sb.upserts) == 1, "boundary moved below 10 min")
    rc, sb, lg, _ = run_case(mod, NOW_SESSION, pg(NOW_SESSION - timedelta(seconds=601)), ticks(NOW_SESSION))
    chk("T8 age 601 s skips", len(sb.upserts) == 0, "boundary moved above 10 min")
    # T9 the measured 10-21 08:31 shape: holiday breadth ts, next morning: nothing written.
    rc, sb, lg, _ = run_case(mod, NOW_AFTER_HOL, HOL_0920, [])
    chk("T9 day-after-holiday writes nothing", len(sb.upserts) == 0, "the 10-20 placeholder row again")
    # T10 the psql wire form (+00, two-digit offset) parses and gates the same way.
    rc, sb, lg, _ = run_case(mod, NOW_SESSION, (NOW_SESSION - timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S.%f+00"), ticks(NOW_SESSION))
    chk("T10 psql-form fresh ts writes", len(sb.upserts) == 1, "ts unparsed -> skip on a healthy cycle")
    return out


MUTANTS = {
    # M1: the age check disabled -> T3 and T8 must fail.
    "M1 no age check": ("    if age_s > WCB_MAX_BREADTH_AGE_MIN * 60:\n", "    if False:\n",
                        {"T3 stale breadth with ticks writes nothing", "T8 age 601 s skips"}),
    # M2: the zero-constituent check disabled -> T5 must fail.
    "M2 no zero-constituent check": ('        if not snapshot_row.get("constituent_count"):  # S99_WCB_NO_INPUT\n',
                                     "        if False:\n", {"T5 zero constituents priced writes nothing"}),
    # M3: the input guard never consulted -> T3, T6, T8 must fail. (T2, T4, T9 have no ticks, so the
    # zero-constituent check still catches them: two layers, measured -- that is why they are not here.)
    "M3 guard not called": ("        if skip:\n            print(f\"[WCB] SKIPPED_NO_INPUT: {skip} -- nothing written\")\n            return log.exit_with_reason(\"SKIPPED_NO_INPUT\", exit_code=0,\n                                        error_message=f\"WCB {index_symbol}: {skip}\")\n\n        snapshot_row",
                            "        snapshot_row",
                            {"T3 stale breadth with ticks writes nothing", "T6 no breadth row writes nothing",
                             "T8 age 601 s skips"}),
}


def main() -> int:
    src = WRITER.read_text(encoding="utf-8")
    patched = cells(load(src))
    fails = [(n, f) for n, ok, f in patched if not ok]
    survivors, not_applied = [], []
    for mname, (old, new, must_fail) in MUTANTS.items():
        if src.count(old) != 1:
            not_applied.append(mname); continue
        res = {n: ok for n, ok, _ in cells(load(src.replace(old, new, 1)))}
        for n in must_fail:
            if res.get(n, True):
                survivors.append(f"{mname}: {n}")
    for n, ok, f in patched:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}" + ("" if ok else f"   (fails if: {f})"))
    print(f"  cells {len(patched)}, failing {len(fails)}; mutants {len(MUTANTS)}, "
          f"not applied {len(not_applied)}, surviving cells {len(survivors)} (must be 0)")
    for s in not_applied: print(f"  MUTANT NOT APPLIED: {s}")
    for s in survivors: print(f"  MUTANT SURVIVED: {s}")
    if fails or survivors or not_applied:
        print("WCB NO-INPUT FAIL"); return 1
    print("WCB NO-INPUT ALL PASS"); return 0


if __name__ == "__main__":
    sys.exit(main())
