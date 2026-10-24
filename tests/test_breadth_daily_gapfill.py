#!/usr/bin/env python3
"""S100 R19 (TD-S97-NEW-11): build_breadth_indicators_daily_local.py fills a complete EOD date that a later date
overtook before it was built -- offline, with mutants.

The builder is loaded from source; its two HTTP helpers (get_json, post_json) are replaced by an in-memory
Supabase over a 3-ticker universe and 3 EOD dates. No network, no database, no credential.

Rule 0 -- what each cell would catch:
  G1 the overtaken date is still skipped (the defect: 10-08, 10-15)
  G2 a date that already has rows is rebuilt by the gap pass (needless writes, and it would mask G1's control)
  G3 an incomplete date (< 95 % coverage) is "filled" with a partial universe
  G4 the gap date's row reads data from after its own date (look-ahead)
  G5 with no gap, the run writes exactly what it wrote before S100 (the latest date only)
Mutants M1-M3 each remove one part; a mutant whose named cells all pass means those cells assert nothing.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BUILDER = REPO / "build_breadth_indicators_daily_local.py"
TICKERS = ["AAA", "BBB", "CCC"]


def fake_db(eod, breadth_dates):
    """eod: {date: {ticker: close}}; breadth_dates: dates that already have breadth rows."""
    posted = []

    def get_json(url, params=None):
        p = params or {}
        if url.endswith("/dhan_scrip_map"):
            return [{"ticker": t} for t in TICKERS] if p.get("offset", "0") == "0" else []
        if url.endswith("/equity_eod"):
            if p.get("limit") == "1" and p.get("order") == "trade_date.desc":
                return [{"trade_date": max(eod)}]
            if p.get("offset", "0") != "0":
                return []
            return [{"ticker": t, "trade_date": d, "close": c} for d, row in sorted(eod.items()) for t, c in row.items()]
        if url.endswith("/breadth_indicators_daily"):
            d = p.get("trade_date", "")[3:]
            return [{"trade_date": d}] if d in breadth_dates else []
        raise AssertionError(f"unexpected GET {url}")

    def post_json(url, rows, params=None):
        assert url.endswith("/breadth_indicators_daily")
        posted.extend(rows)
    return get_json, post_json, posted


def load(src: str, name: str):
    req = types.ModuleType("requests"); req.Response = object
    dot = types.ModuleType("dotenv"); dot.load_dotenv = lambda *a, **k: None
    sys.modules.update({"requests": req, "dotenv": dot})
    os.environ.setdefault("SUPABASE_URL", "https://offline.invalid")
    os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "offline-dummy-not-a-credential")
    mod = types.ModuleType(name); mod.__file__ = str(BUILDER); sys.modules[name] = mod
    exec(compile(src, str(BUILDER), "exec"), mod.__dict__)
    return mod


def run(src, tag, eod, breadth_dates):
    mod = load(src, f"bbd_{tag}")
    g, p, posted = fake_db(eod, breadth_dates)
    mod.get_json, mod.post_json = g, p
    with contextlib.redirect_stdout(io.StringIO()) as out:
        mod.main()
    return posted, out.getvalue()


FULL = {"2026-10-07": {"AAA": 100.0, "BBB": 50.0, "CCC": 10.0},
        "2026-10-08": {"AAA": 105.0, "BBB": 49.0, "CCC": 10.5},
        "2026-10-09": {"AAA": 106.0, "BBB": 48.0, "CCC": 11.0}}


def cells(src: str, tag: str) -> list[tuple[str, bool, str]]:
    out = []
    chk = lambda n, ok, f: out.append((n, bool(ok), f))
    posted, log = run(src, tag + "a", FULL, {"2026-10-07"})
    by_date = {}
    for r in posted:
        by_date.setdefault(r["trade_date"], []).append(r)
    chk("G1 overtaken 10-08 is built after the latest 10-09 (3 rows each)",
        len(by_date.get("2026-10-09", [])) == 3 and len(by_date.get("2026-10-08", [])) == 3, "the gap date is skipped")
    chk("G2 10-07 already has rows -> not rebuilt", "2026-10-07" not in by_date, "existing dates rewritten")
    a08 = next((r for r in by_date.get("2026-10-08", []) if r["ticker"] == "AAA"), {})
    chk("G4 the 10-08 row uses 10-08's close and 10-07's as prev (no look-ahead)",
        a08.get("close") == 105.0 and a08.get("prev_close") == 100.0, "a later date leaked into the gap row")
    part = dict(FULL); part["2026-10-08"] = {"AAA": 105.0}          # 1 of 3 tickers = 33 %
    posted, _ = run(src, tag + "b", part, {"2026-10-07"})
    chk("G3 an incomplete date (33 %) is not filled", not any(r["trade_date"] == "2026-10-08" for r in posted),
        "a partial universe written as a complete day")
    posted, _ = run(src, tag + "c", FULL, {"2026-10-07", "2026-10-08"})
    chk("G5 no gap -> only the latest date written (3 rows)",
        len(posted) == 3 and {r["trade_date"] for r in posted} == {"2026-10-09"}, "behaviour changed with no gap")
    return out


MUTANTS = {
    "M1 gap pass removed": ("    for gap in gap_dates(coverage_map, len(universe_tickers), rebuild_trade_date):\n",
                            "    for gap in []:\n",
                            {"G1 overtaken 10-08 is built after the latest 10-09 (3 rows each)",
                             "G4 the 10-08 row uses 10-08's close and 10-07's as prev (no look-ahead)"}),
    "M2 existence check ignored": ("    return [d for d in complete if not breadth_date_exists(d)]\n",
                                   "    return list(complete)\n",
                                   {"G2 10-07 already has rows -> not rebuilt",
                                    "G5 no gap -> only the latest date written (3 rows)"}),
    "M3 completeness check removed": ("if d != skip and universe_count and (n / universe_count) * 100.0 >= COMPLETE_EOD_THRESHOLD_PCT)",
                                      "if d != skip)",
                                      {"G3 an incomplete date (33 %) is not filled"}),
}


def main() -> int:
    src = BUILDER.read_text(encoding="utf-8-sig")
    if "S100_BREADTH_GAPFILL" not in src:
        print("BREADTH DAILY GAPFILL FAIL: builder lacks S100_BREADTH_GAPFILL"); return 1
    res = cells(src, "base")
    fails = [n for n, ok, _ in res if not ok]
    names = {n for n, _, _ in res}
    survivors, not_applied, unknown = [], [], []
    for i, (mname, (old, new, must_fail)) in enumerate(MUTANTS.items()):
        unknown += [f"{mname}: {n}" for n in must_fail if n not in names]
        if src.count(old) != 1:
            not_applied.append(mname); continue
        try:
            mres = {n: ok for n, ok, _ in cells(src.replace(old, new, 1), f"m{i}")}
        except Exception as e:
            mres = {n: False for n in must_fail}; print(f"  ({mname} raised {type(e).__name__}: {e})")
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
        print("BREADTH DAILY GAPFILL FAIL"); return 1
    print("BREADTH DAILY GAPFILL ALL PASS"); return 0


if __name__ == "__main__":
    sys.exit(main())
