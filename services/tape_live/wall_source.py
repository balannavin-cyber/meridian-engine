"""Tape live: the ONE place that learns the two wall strikes (docs/tape/L0_plan.md section 4; spec s3).

Chain-side access in services/tape_live/ happens here and nowhere else (asserted by tests/test_tape_live.py). It reads only what a wall
needs: per run, the front expiry, the call wall (largest oi_call), the put wall (largest oi_put) and those two OI values.
The definitions are merdian_compute.tape.chain_events.build_runs, the same code that made the offline chain runs, so the live
wall and the scored wall cannot be defined twice.

  L0  runs_from_snapshot_csv: the gex_strike_snapshots export CSVs (run_id, symbol, ts, expiry_date, strike, oi_call, oi_put,
      gex_cr), as the T1b chain step reads them.
      runs_from_chain_runs_csv: the final chain_runs.csv of the offline chain step (walls only; verify_day uses it).
  L2  one SELECT on gex_strike_snapshots, front expiry, behind the same function shape (not built).

Timestamp width (docs/tape/L0_ts_width_plan.md). Postgres drops trailing zeros from a timestamptz, so a snapshot ts arrives with a
fraction of 0 to 6 digits; Python 3.10 fromisoformat accepts only 0, 3 or 6 (3.11+ accept all). chain_events.parse_ts is shared with
the scoring chain and is not edited here: every snapshot row goes through norm_snapshot_ts first, via the one build_runs below,
which is the ONLY call of chain_events.build_runs in services/tape_live/ (asserted by guard live-ts-width). A later live reader
(L2) builds its rows and calls this build_runs, so it inherits the normaliser.

Grid rule (the scorer's reconciliation): the run used for grid point T is the latest run whose timestamp, floored to the
5-minute grid, is <= T.
"""
import csv
import re

from merdian_compute.tape import chain_events

# The only shape seen in 130,954 exported values (2026-11-02..06): T separator, UTC offset written +00:00, fraction optional.
# Anything else (Z, +00, a space separator, surrounding whitespace) is refused: it would crash Python 3.10 or hide a new wire.
SNAP_TS_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?([+-]\d{2}:\d{2})$")


def _k(v):
    return "" if v is None else chain_events._k(v)


def norm_snapshot_ts(s):
    """One gex_strike_snapshots ts -> the same instant with a fraction of 0 or 6 digits.

    Pads the fraction on the right with zeros (.4396 -> .439600); never truncates, never rounds. Pure string work, so the
    result does not depend on the interpreter. Raises ValueError on a fraction wider than 6 digits and on any other shape.
    """
    m = SNAP_TS_RE.match(s)
    if m is None:
        raise ValueError("snapshot ts %r: not YYYY-MM-DDTHH:MM:SS[.f]+HH:MM" % (s,))
    frac = m.group(2)
    if frac is None:
        return s
    if len(frac) > 6:
        raise ValueError("snapshot ts %r: fraction wider than 6 digits (never rounded)" % (s,))
    return "%s.%s%s" % (m.group(1), frac.ljust(6, "0"), m.group(3))


def build_runs(rows, day):
    """The ONLY call of chain_events.build_runs in services/tape_live/: normalises every row's ts first. -> (by symbol, counters)."""
    return chain_events.build_runs([dict(r, ts=norm_snapshot_ts(r["ts"])) for r in rows], day)


def runs_from_snapshot_csv(paths, day):
    """-> {symbol: [run dicts of strings, in time order]}."""
    rows = []
    for p in paths:
        with open(p, encoding="utf-8", newline="") as fh:
            rows += list(csv.DictReader(fh))
    by_sym, _cnt = build_runs(rows, day)
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
