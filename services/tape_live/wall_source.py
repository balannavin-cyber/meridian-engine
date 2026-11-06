"""Tape live: the ONE place that learns the two wall strikes (docs/tape/L0_plan.md section 4; spec s3).

Chain-side access in services/tape_live/ happens here and nowhere else (asserted by tests/test_tape_live.py). It reads only what a wall
needs: per run, the front expiry, the call wall (largest oi_call), the put wall (largest oi_put) and those two OI values.
The definitions are merdian_compute.tape.chain_events.build_runs, the same code that made the offline chain runs, so the live
wall and the scored wall cannot be defined twice.

  L0  runs_from_snapshot_csv: the gex_strike_snapshots export CSVs (run_id, symbol, ts, expiry_date, strike, oi_call, oi_put,
      gex_cr), as the T1b chain step reads them.
      runs_from_chain_runs_csv: the final chain_runs.csv of the offline chain step (walls only; verify_day uses it).
  L2  one SELECT on gex_strike_snapshots, front expiry, behind the same function shape (not built).

Grid rule (the scorer's reconciliation): the run used for grid point T is the latest run whose timestamp, floored to the
5-minute grid, is <= T.
"""
import csv

from merdian_compute.tape import chain_events


def _k(v):
    return "" if v is None else chain_events._k(v)


def runs_from_snapshot_csv(paths, day):
    """-> {symbol: [run dicts of strings, in time order]}."""
    rows = []
    for p in paths:
        with open(p, encoding="utf-8", newline="") as fh:
            rows += list(csv.DictReader(fh))
    by_sym, _cnt = chain_events.build_runs(rows, day)
    out = {}
    for sym in sorted(by_sym):
        lst = []
        for r in by_sym[sym]:
            cw, pw = r["call_wall"], r["put_wall"]
            lst.append({"symbol": sym, "expiry": r["expiry"], "ts_ist": r["ts_ist"], "run_id": r["run_id"],
                        "call_wall": _k(cw), "put_wall": _k(pw),
                        "call_wall_oi_call": "" if cw is None else str(r["strikes"][cw][0]),
                        "put_wall_oi_put": "" if pw is None else str(r["strikes"][pw][1])})
        out[sym] = lst
    return out


def runs_from_chain_runs_csv(path):
    """The final chain runs (walls, no OI) -> {symbol: [run dicts]} in file order (time order per symbol)."""
    out = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r["symbol"], []).append({
                "symbol": r["symbol"], "expiry": r["expiry"], "ts_ist": r["ts_ist"], "run_id": r["run_id"],
                "call_wall": r["call_wall"], "put_wall": r["put_wall"], "call_wall_oi_call": "", "put_wall_oi_put": ""})
    return out


def _floor5(ts):
    m = int(ts[11:13]) * 60 + int(ts[14:16])
    return m - m % 5


def wall_row(runs, day, hhmm):
    """runs: one symbol's runs in time order. -> the tape_live_wall row for grid point hhmm ('HH:MM'), or None."""
    tm = int(hhmm[:2]) * 60 + int(hhmm[3:5])
    best = None
    for r in runs:
        if _floor5(r["ts_ist"]) <= tm:
            best = r
        else:
            break
    if best is None:
        return None
    return {"symbol": best["symbol"], "trading_day": day, "expiry": best["expiry"], "ts_ist": "%sT%s:00+05:30" % (day, hhmm),
            "chain_run_id": best["run_id"], "chain_run_ts": best["ts_ist"], "call_wall": best["call_wall"],
            "put_wall": best["put_wall"], "call_wall_oi_call": best["call_wall_oi_call"],
            "put_wall_oi_put": best["put_wall_oi_put"]}
