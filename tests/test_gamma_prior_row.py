#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S103 / rulings S103-N, S103-O -- the gamma writer's prior-row read (TD-S101-NEW-3, TD-S101-NEW-4).

Target under test: compute_gamma_metrics_local.py at the repo root, function fetch_prior_gamma_metrics and its
helper _ist_session_floor_iso. Two defects, one function:
  (1) the read selected "straddle_atm,ts" only, so the prior row carried no `raw`, so compute_otm_oi_velocity
      (which reads prior_row["raw"]["otm_oi_snapshot"]) returned NULL in every production row;
  (2) the read had no date bound, so the first cycle of a day compared against the previous day's last row.

The module is loaded from source with its collaborators stubbed before exec (no database, no network, no .env):
dotenv.load_dotenv -> no-op; supabase.create_client -> a fake whose select() returns ONLY the requested columns
(that is what PostgREST does, and it is what makes defect (1) visible); core.execution_log -> stub;
requests -> stub module. core.ts_parse and merdian_compute are the real files.

Every cell names the value that would make it fail; the mutants at the end prove four of them do. If the mutant
run reports ALL PASS, this suite is documentation and the exit code says so.

Run:  ( ulimit -v 700000; python3 tests/test_gamma_prior_row.py )
"""
from __future__ import annotations

import importlib.util
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TARGET = REPO / "compute_gamma_metrics_local.py"
sys.path.insert(0, str(REPO))


class Result:
    def __init__(self, data):
        self.data = data


class Query:
    def __init__(self, rows):
        self.rows = rows
        self.cols = None
        self.filters = []
        self.desc = False
        self.n = None
        self.log = {"select": None, "filters": []}

    def select(self, cols):
        self.cols = [c.strip() for c in cols.split(",")]
        self.log["select"] = cols
        return self

    def eq(self, col, val):
        self.filters.append(("eq", col, val)); self.log["filters"].append(("eq", col, val)); return self

    def lt(self, col, val):
        self.filters.append(("lt", col, val)); self.log["filters"].append(("lt", col, val)); return self

    def gte(self, col, val):
        self.filters.append(("gte", col, val)); self.log["filters"].append(("gte", col, val)); return self

    def order(self, col, desc=False):
        self.desc = desc; return self

    def limit(self, n):
        self.n = n; return self

    def execute(self):
        from core.ts_parse import parse_pg_ts
        out = []
        for r in self.rows:
            ok = True
            for op, col, val in self.filters:
                v = r.get(col)
                if op == "eq":
                    ok = ok and v == val
                else:
                    a, b = parse_pg_ts(v), parse_pg_ts(val)
                    ok = ok and a is not None and b is not None and (a < b if op == "lt" else a >= b)
            if ok:
                out.append(r)
        out.sort(key=lambda r: parse_pg_ts(r["ts"]), reverse=self.desc)
        if self.n is not None:
            out = out[: self.n]
        return Result([{c: r[c] for c in self.cols if c in r} for r in out])


class FakeClient:
    last_query = None
    rows = []

    def table(self, name):
        q = Query(list(FakeClient.rows))
        FakeClient.last_query = q
        return q


def load(source: str):
    for m in ("compute_gamma_metrics_local",):
        sys.modules.pop(m, None)
    dot = types.ModuleType("dotenv"); dot.load_dotenv = lambda *a, **k: None
    sb = types.ModuleType("supabase"); sb.Client = object; sb.create_client = lambda url, key: FakeClient()
    rq = types.ModuleType("requests")
    el = types.ModuleType("core.execution_log")

    class ExecutionLog:  # never constructed by the functions under test
        def __init__(self, *a, **k): pass
    el.ExecutionLog = ExecutionLog
    sys.modules.update({"dotenv": dot, "supabase": sb, "requests": rq, "core.execution_log": el})
    import os
    os.environ["SUPABASE_URL"] = "https://example.invalid"
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-not-a-key"
    sys.argv = ["compute_gamma_metrics_local.py"]
    mod = types.ModuleType("gamma_under_test")
    exec(compile(source, str(TARGET), "exec"), mod.__dict__)
    return mod


def ce_rows(oi_far):
    # ATM 23000, step 50, two steps -> OTM CE threshold 23100; only the CE at 23100 and above counts.
    rows = []
    for k in (22900, 22950, 23000, 23050, 23100, 23150):
        rows.append({"strike": k, "option_type": "CE", "oi": oi_far if k >= 23100 else 5000})
        rows.append({"strike": k, "option_type": "PE", "oi": 5000})
    return rows


# IST 2026-10-31 09:20 = 03:50 UTC. IST midnight 2026-10-31 = 2026-10-30 18:30 UTC.
CUR = "2026-10-31T03:50:00+00:00"
ROW_SAME_SESSION = {"symbol": "NIFTY", "ts": "2026-10-31T03:45:00+00:00", "straddle_atm": 210.0,
                    "raw": {"otm_oi_snapshot": 1000.0}}
ROW_PREV_DAY = {"symbol": "NIFTY", "ts": "2026-10-30T10:10:00+00:00", "straddle_atm": 190.0,
                "raw": {"otm_oi_snapshot": 400.0}}                       # Friday 15:40 IST
ROW_JUST_BEFORE_MIDNIGHT = {"symbol": "NIFTY", "ts": "2026-10-30T18:29:59+00:00", "straddle_atm": 1.0,
                            "raw": {"otm_oi_snapshot": 7.0}}              # 23:59:59 IST on 10-30
ROW_AT_MIDNIGHT = {"symbol": "NIFTY", "ts": "2026-10-30T18:30:00+00:00", "straddle_atm": 2.0,
                   "raw": {"otm_oi_snapshot": 9.0}}                       # 00:00:00 IST on 10-31
ROW_OTHER_SYMBOL = {"symbol": "SENSEX", "ts": "2026-10-31T03:46:00+00:00", "straddle_atm": 999.0,
                    "raw": {"otm_oi_snapshot": 1.0}}


def fetch(mod, rows, ts=CUR, symbol="NIFTY"):
    FakeClient.rows = rows
    return mod.fetch_prior_gamma_metrics(symbol, ts)


def cells(mod):
    out = []

    def chk(name, cond, fail_if):
        out.append((name, bool(cond), fail_if))

    # T1 a same-session prior row comes back WITH raw, and the velocity is a number (the defect (1) cell).
    p = fetch(mod, [ROW_SAME_SESSION, ROW_PREV_DAY])
    chk("T1 prior row carries raw", p is not None and p.get("raw", {}).get("otm_oi_snapshot") == 1000.0,
        "raw absent: the select does not name it")
    v = mod.compute_otm_oi_velocity(ce_rows(1100.0), 23000.0, p) if p else None
    # current OTM CE OI: strikes 23100 and 23150 -> 2 * 1100 = 2200 vs prior 1000 -> +120 %
    chk("T1 velocity is 1.2 (2200 vs 1000)", v == 1.2, f"velocity {v!r}, not 1.2")
    chk("T1 straddle velocity uses the prior straddle", mod.compute_straddle_velocity(215.0, p) == 5.0,
        "straddle velocity not 215 - 210")
    # T2 only yesterday's row exists: no prior (first cycle of the session), so both velocities are NULL.
    p = fetch(mod, [ROW_PREV_DAY])
    chk("T2 a previous-day row is not a prior row", p is None, "yesterday's 15:40 row was returned")
    chk("T2 velocity NULL on the first cycle", mod.compute_otm_oi_velocity(ce_rows(1100.0), 23000.0, p) is None,
        "a cross-day velocity was computed")
    chk("T2 straddle velocity NULL on the first cycle", mod.compute_straddle_velocity(215.0, p) is None,
        "a cross-day straddle velocity was computed")
    # T3 / T4 the boundary is IST midnight, inclusive: 23:59:59 IST on the previous date is out, 00:00:00 IST is in.
    p = fetch(mod, [ROW_JUST_BEFORE_MIDNIGHT])
    chk("T3 23:59:59 IST the day before is out", p is None, "a row from the previous IST date was returned")
    p = fetch(mod, [ROW_AT_MIDNIGHT])
    chk("T4 00:00:00 IST of the session date is in", p is not None and p.get("straddle_atm") == 2.0,
        "the floor is not IST midnight (a UTC-date floor excludes it)")
    # T5 an unparseable current ts reads nothing and issues no query (fail to absent).
    FakeClient.last_query = None
    p = fetch(mod, [ROW_SAME_SESSION], ts="not-a-timestamp")
    chk("T5 unparseable ts: None", p is None, "a row was returned for a bad ts")
    chk("T5 unparseable ts: no query issued", FakeClient.last_query is None, "an unbounded read was issued")
    # T6 the second cycle of a session: the first cycle's row is the prior, and its straddle is used.
    p = fetch(mod, [ROW_SAME_SESSION, ROW_PREV_DAY], ts="2026-10-31T03:55:00+00:00")
    chk("T6 second cycle sees the first", p is not None and p["ts"] == "2026-10-31T03:45:00+00:00",
        "wrong prior row")
    # T7 only the same symbol, and the select names raw.
    p = fetch(mod, [ROW_OTHER_SYMBOL])
    chk("T7 another symbol's row is not a prior row", p is None, "a SENSEX row was returned for NIFTY")
    fetch(mod, [ROW_SAME_SESSION])
    sel = FakeClient.last_query.log["select"] if FakeClient.last_query else ""
    chk("T7 the select names raw", "raw" in [c.strip() for c in (sel or "").split(",")], "raw not selected")
    # T8 a time-of-day sanity case the other way: after IST midnight but before the open still bounds correctly.
    p = fetch(mod, [ROW_PREV_DAY, ROW_AT_MIDNIGHT], ts="2026-10-31T03:30:00+00:00")   # 09:00 IST pre-open
    chk("T8 pre-open cycle sees the 00:00 IST row only, never yesterday 15:40",
        p is not None and p["ts"] == "2026-10-30T18:30:00+00:00", "the pre-open cycle read a different row")
    return out


MUTANTS = [
    ("M1 select drops raw (the original defect)", 'select("straddle_atm,ts,raw")', 'select("straddle_atm,ts")'),
    ("M2 the IST-session bound is removed", '            .gte("ts", floor_iso)\n', ""),
    ("M3 the floor is the UTC date, not the IST date",
     "dt.astimezone(_IST).replace(hour=0, minute=0, second=0, microsecond=0)",
     "dt.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)"),
    ("M4 an unparseable ts reads unbounded instead of nothing",
     "    if floor_iso is None:\n        return None\n", "    if floor_iso is None:\n        floor_iso = '1970-01-01T00:00:00+00:00'\n"),
]


def main() -> int:
    src = TARGET.read_text(encoding="utf-8")
    ok_all = True
    base = cells(load(src))
    n_ok = sum(1 for _, ok, _ in base if ok)
    for name, ok, fail_if in base:
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"   [would fail if: {fail_if}]"))
        ok_all = ok_all and ok
    print(f"CELLS: {n_ok}/{len(base)} pass")
    surviving = 0
    for name, old, new in MUTANTS:
        assert src.count(old) == 1, f"mutant pattern for {name} occurs {src.count(old)} times"
        res = cells(load(src.replace(old, new)))
        failed = [n for n, ok, _ in res if not ok]
        print(("CAUGHT   " if failed else "SURVIVED ") + name + (f"  ({len(failed)} cells fail)" if failed else ""))
        if not failed:
            surviving += 1
    print(f"MUTANTS: {len(MUTANTS) - surviving}/{len(MUTANTS)} caught, {surviving} surviving")
    if not ok_all or surviving:
        print("GAMMA PRIOR ROW: FAIL")
        return 1
    print(f"GAMMA PRIOR ROW PASS ({len(base)} cells, {len(MUTANTS)} mutants, 0 surviving)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
