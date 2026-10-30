#!/usr/bin/env python3
"""S102_CLOSE_CAS -- build_market_spot_session_markers.get_close_1530 reads the CAS-settled 15:29 bar.

capture_cas_close.py writes the settled close at ~16:20 IST with ts = capture time and the bar's own time
in raw.bar_ts_ist; the old 15:29:00-15:30:59 window never contained it, so capture_quality read
MISSING_CLOSE_1530 every session (2026-10-12 .. 10-27). The writer is loaded from source with `supabase`
and `dotenv` stubbed and select_rows replaced by an in-memory filter; no database, network or credential.

Rule 0 -- what each cell would catch:
  C1 the CAS row (ts 16:20, cas_settled, bar 15:29) is not found -> close_1530 NULL again
  C2 close_1530_ts is the capture time, not the bar time
  C3 a non-CAS row stamped 16:20 (e.g. a 16:00 / 16:20 idx snapshot) is taken as the close
  C4 with no CAS row, an in-window 15:29 row is no longer used (the fallback lost)
  C5 the CAS row of the NEXT day is taken (window not bounded to the session date)
Mutants M1-M3 each remove one part.
"""
from __future__ import annotations

import os
import sys
import types
from datetime import date, datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WRITER = REPO / "build_market_spot_session_markers.py"
D = date(2026, 10, 27)


def iso(s):  # IST wall clock on D or D+1 -> aware UTC ISO
    return datetime.fromisoformat(s).astimezone(timezone.utc).isoformat()


def fake_select(store):
    def _sel(table, columns, *, filters_eq=None, gte=None, lte=None, gt=None, lt=None,
             order_by=None, desc=False, limit=None):
        out = []
        for r in store:
            ok = True
            for k, v in (filters_eq or {}).items():
                if k == "raw->>cas_settled":
                    ok &= str((r.get("raw") or {}).get("cas_settled")).lower() == str(v).lower()
                else:
                    ok &= r.get(k) == v
            if gte: ok &= r["ts"] >= gte[1]
            if lte: ok &= r["ts"] <= lte[1]
            if ok: out.append(r)
        out.sort(key=lambda r: r["ts"], reverse=desc)
        return out[:limit] if limit else out
    return _sel


CAS = {"symbol": "NIFTY", "ts": iso("2026-10-27T16:20:05+05:30"), "spot": 22749.75, "source_table": "dhan_charts_intraday",
       "raw": {"cas_settled": True, "bar_ts_ist": "2026-10-27T15:29:00+05:30"}}
IDX = {"symbol": "NIFTY", "ts": iso("2026-10-27T16:20:30+05:30"), "spot": 22750.10, "source_table": "dhan_idx_i", "raw": {}}
WIN = {"symbol": "NIFTY", "ts": iso("2026-10-27T15:29:30+05:30"), "spot": 22748.00, "source_table": "dhan_charts_historical", "raw": {}}
NEXT = {"symbol": "NIFTY", "ts": iso("2026-10-28T16:20:05+05:30"), "spot": 22600.00, "source_table": "dhan_charts_intraday",
        "raw": {"cas_settled": True, "bar_ts_ist": "2026-10-28T15:29:00+05:30"}}


def load(src, name):
    sup = types.ModuleType("supabase"); sup.Client = object; sup.create_client = lambda *_a: object()
    dot = types.ModuleType("dotenv"); dot.load_dotenv = lambda *_a, **_k: None
    sys.modules.update({"supabase": sup, "dotenv": dot})
    os.environ.setdefault("SUPABASE_URL", "https://offline.invalid")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "offline-dummy-not-a-credential")
    mod = types.ModuleType(name); mod.__file__ = str(WRITER); mod.__name__ = name; sys.modules[name] = mod
    exec(compile(src, str(WRITER), "exec"), mod.__dict__)
    return mod


def cells(src, tag):
    out = []
    chk = lambda n, ok, f: out.append((n, bool(ok), f))
    try:
        mod = load(src, f"mk_{tag}")
        def close(store):
            mod.select_rows = fake_select(store)
            return mod.get_close_1530("NIFTY", D)
        r = close([CAS, IDX, NEXT])
        chk("C1 CAS-settled row found", r is not None and r.get("spot") == 22749.75, "close_1530 NULL")
        chk("C2 close ts = bar time 15:29", r is not None and str(r.get("ts")).startswith("2026-10-27T15:29"), "capture time used")
        r = close([IDX])
        chk("C3 a non-CAS 16:20 row is not taken", r is None, "a post-close snapshot read as the close")
        r = close([WIN])
        chk("C4 no CAS row -> the in-window 15:29 row is used", r is not None and r.get("spot") == 22748.00, "fallback lost")
        r = close([NEXT])
        chk("C5 the next day's CAS row is not taken", r is None, "window not bounded to the session")
    except Exception as e:
        for n in ("C1 CAS-settled row found", "C2 close ts = bar time 15:29", "C3 a non-CAS 16:20 row is not taken",
                  "C4 no CAS row -> the in-window 15:29 row is used", "C5 the next day's CAS row is not taken"):
            if n not in {x[0] for x in out}:
                chk(n, False, f"crashed: {e}")
    return out


MUTANTS = {
    "M1 CAS filter dropped": ('        filters_eq={"symbol": symbol, "raw->>cas_settled": "true"},\n',
                              '        filters_eq={"symbol": symbol},\n',
                              {"C3 a non-CAS 16:20 row is not taken"}),
    "M2 capture time kept": ('        if bar_ts:\n            row["ts"] = bar_ts\n', "",
                             {"C2 close ts = bar time 15:29"}),
    "M3 day bound dropped": ('        lte=("ts", utc_iso(ist_dt(trade_date, 23, 59, 59))),\n        order_by="ts",\n        desc=True,\n        limit=1,\n    )\n    if rows:',
                             '        order_by="ts",\n        desc=True,\n        limit=1,\n    )\n    if rows:',
                             {"C5 the next day's CAS row is not taken"}),
}


def main() -> int:
    src = WRITER.read_text(encoding="utf-8-sig")
    if "S102_CLOSE_CAS" not in src:
        print("MARKER CLOSE CAS FAIL: writer lacks S102_CLOSE_CAS"); return 1
    res = cells(src, "base")
    fails = [n for n, ok, _ in res if not ok]
    names = {n for n, _, _ in res}
    survivors, not_applied, unknown = [], [], []
    for i, (mname, (old, new, must_fail)) in enumerate(MUTANTS.items()):
        unknown += [f"{mname}: {n}" for n in must_fail if n not in names]
        if src.count(old) != 1:
            not_applied.append(mname); continue
        mres = {n: ok for n, ok, _ in cells(src.replace(old, new, 1), f"m{i}")}
        survivors += [f"{mname}: {n}" for n in must_fail if mres.get(n, True)]
    for n, ok, f in res:
        print(f"  {'PASS' if ok else 'FAIL'}  {n}" + ("" if ok else f"   (fails if: {f})"))
    print(f"  cells {len(res)}, failing {len(fails)}; mutants {len(MUTANTS)}, not applied {len(not_applied)}, "
          f"surviving {len(survivors)} (must be 0)")
    for s in not_applied: print(f"  MUTANT NOT APPLIED: {s}")
    for s in unknown: print(f"  MUTANT NAMES NO CELL: {s}")
    for s in survivors: print(f"  MUTANT SURVIVED: {s}")
    if fails or survivors or not_applied or unknown:
        print("MARKER CLOSE CAS FAIL"); return 1
    print("MARKER CLOSE CAS ALL PASS"); return 0


if __name__ == "__main__":
    sys.exit(main())
