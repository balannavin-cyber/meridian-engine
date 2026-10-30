#!/usr/bin/env python3
"""S102_TDS100_NEW1 -- capture_index_futures_snapshot_local.py prices the index in the SAME Dhan
marketfeed/ltp request as the future and computes basis against it.

The writer is loaded from source with `requests` and `dotenv` replaced by stubs, and any Supabase read
made to raise; no database, network or credential. Only build_dhan_payload / build_output_rows run.

Rule 0 -- what each cell would catch:
  F1 the request does not ask Dhan for the index (IDX_I 13 / 51), once each
  F2 the stored spot is not the index LTP from that response, or basis is not futures - spot
  F3 the closing-window case: a stale table spot is used instead of the response's close
  F4 a missing index LTP falls back to anything (must write no row for that symbol only)
  F5 any Supabase read happens while building rows (the old market_spot_snapshots read)
  F6 (S102_FUT_ARGV) a cron line's symbol argument is ignored (both symbols captured = duplicate rows)
Mutants M1-M4 each remove one part.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WRITER = REPO / "capture_index_futures_snapshot_local.py"

CONTRACTS = [
    {"symbol": "NIFTY", "security_id": 111, "marketfeed_segment": "NSE_FNO", "display_name": "NIFTY NOV FUT",
     "expiry_date": "2026-11-24"},
    {"symbol": "SENSEX", "security_id": 222, "marketfeed_segment": "BSE_FNO", "display_name": "SENSEX NOV FUT",
     "expiry_date": "2026-11-26"},
]


def response(nifty_idx=22749.75, sensex_idx=73598.67):
    idx = {}
    if nifty_idx is not None:
        idx["13"] = {"last_price": nifty_idx}
    if sensex_idx is not None:
        idx["51"] = {"last_price": sensex_idx}
    return {"data": {"NSE_FNO": {"111": {"last_price": 22800.0}}, "BSE_FNO": {"222": {"last_price": 73700.0}},
                     "IDX_I": idx}, "status": "success"}


def load(src, name):
    req = types.ModuleType("requests")
    def _boom(*_a, **_k): raise AssertionError("network call in an offline test")
    req.get = req.post = _boom
    dot = types.ModuleType("dotenv"); dot.load_dotenv = lambda *_a, **_k: None
    sys.modules.update({"requests": req, "dotenv": dot})
    mod = types.ModuleType(name); mod.__file__ = str(WRITER); mod.__name__ = name; sys.modules[name] = mod
    exec(compile(src, str(WRITER), "exec"), mod.__dict__)
    reads = []
    def _sb_get(table, params):
        reads.append(table); raise RuntimeError(f"supabase read of {table} during row build")
    mod.supabase_get = _sb_get
    return mod, reads


def cells(src, tag):
    out = []
    chk = lambda n, ok, f: out.append((n, bool(ok), f))
    try:
        mod, reads = load(src, f"fut_{tag}")
        payload = mod.build_dhan_payload([dict(c) for c in CONTRACTS])
        chk("F1 request asks for IDX_I 13 and 51, once each",
            sorted(payload.get("IDX_I", [])) == [13, 51] and payload.get("NSE_FNO") == [111]
            and payload.get("BSE_FNO") == [222], "the index is not in the request")
        with contextlib.redirect_stdout(io.StringIO()):
            rows = mod.build_output_rows(response(), [dict(c) for c in CONTRACTS])
        by = {r["symbol"]: r for r in rows}
        chk("F2 spot = index LTP from the same response; basis = futures - spot",
            len(rows) == 2 and by["NIFTY"]["spot_price"] == 22749.75 and by["SENSEX"]["spot_price"] == 73598.67
            and abs(by["NIFTY"]["basis"] - (22800.0 - 22749.75)) < 1e-9
            and by["NIFTY"]["raw"].get("spot_source") == "dhan_ltp_idx_i_same_request", "spot not from the response")
        chk("F3 closing window: the response's close is used (10-27: 22,749.75, not 22,760.8)",
            by.get("NIFTY", {}).get("spot_price") != 22760.8 and by.get("NIFTY", {}).get("spot_price") == 22749.75,
            "a stale spot is used")
        with contextlib.redirect_stdout(io.StringIO()):
            rows2 = mod.build_output_rows(response(nifty_idx=None), [dict(c) for c in CONTRACTS])
        chk("F4 index LTP missing for NIFTY -> no NIFTY row, SENSEX row kept",
            [r["symbol"] for r in rows2] == ["SENSEX"], "a missing index LTP falls back")
        chk("F5 no Supabase read while building rows", reads == [], "the market_spot_snapshots read is back")
        try:
            mod.symbols_from_argv(["x", "BANKNIFTY"]); bad_raises = False
        except mod.ConfigError:
            bad_raises = True
        chk("F6 argv NIFTY -> [NIFTY]; sensex -> [SENSEX]; none -> both; unknown -> error",
            mod.symbols_from_argv(["x", "NIFTY"]) == ["NIFTY"] and mod.symbols_from_argv(["x", "sensex"]) == ["SENSEX"]
            and mod.symbols_from_argv(["x"]) == ["NIFTY", "SENSEX"] and bad_raises, "the argument is ignored")
    except Exception as e:  # a crash is a failed cell
        for n in ("F1 request asks for IDX_I 13 and 51, once each",
                  "F2 spot = index LTP from the same response; basis = futures - spot",
                  "F3 closing window: the response's close is used (10-27: 22,749.75, not 22,760.8)",
                  "F4 index LTP missing for NIFTY -> no NIFTY row, SENSEX row kept",
                  "F5 no Supabase read while building rows",
                  "F6 argv NIFTY -> [NIFTY]; sensex -> [SENSEX]; none -> both; unknown -> error"):
            if n not in {x[0] for x in out}:
                chk(n, False, f"crashed: {e}")
    return out


MUTANTS = {
    "M1 index not requested": ('        index_id = INDEX_SECURITY_IDS[contract["symbol"]]\n        if index_id not in payload.setdefault(INDEX_SEGMENT, []):\n            payload[INDEX_SEGMENT].append(index_id)\n',
                               "",
                               {"F1 request asks for IDX_I 13 and 51, once each"}),
    "M2 table spot back": ('        spot = extract_last_price_or_none(payload, INDEX_SEGMENT, INDEX_SECURITY_IDS[symbol])\n',
                           '        spot = supabase_get("market_spot_snapshots", {}) if False else 22760.8\n',
                           {"F2 spot = index LTP from the same response; basis = futures - spot",
                            "F3 closing window: the response's close is used (10-27: 22,749.75, not 22,760.8)"}),
    "M3 missing index falls back": ('        if spot is None or spot <= 0:\n',
                                    '        if spot is None:\n            spot = 1.0\n        if spot <= 0:\n',
                                    {"F4 index LTP missing for NIFTY -> no NIFTY row, SENSEX row kept"}),
    "M4 argument ignored again": ("    sym = argv[1].strip().upper()\n", "    return list(FUTURES_SYMBOLS)\n    sym = argv[1].strip().upper()\n",
                                  {"F6 argv NIFTY -> [NIFTY]; sensex -> [SENSEX]; none -> both; unknown -> error"}),
}


def main() -> int:
    src = WRITER.read_text(encoding="utf-8-sig")
    if "S102_TDS100_NEW1" not in src:
        print("FUTURES SPOT FAIL: writer lacks S102_TDS100_NEW1"); return 1
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
        print("FUTURES SPOT FAIL"); return 1
    print("FUTURES SPOT ALL PASS"); return 0


if __name__ == "__main__":
    sys.exit(main())
