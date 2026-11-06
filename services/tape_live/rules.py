"""Tape live flow-vs-book rules v1 (docs/tape/tape_live_flow_vs_book_spec_v0.1.md s4; docs/tape/L0_plan.md section 4).

PURE: stdlib only, no clock, no randomness, no I/O. Two functions, and the page implements the same two separately; both
must pass services/tape_live/tapeLabels.vectors.json.

Inputs are cycle-table rows and event rows exactly as the offline CSVs render them (dicts of strings, cycle column ``T`` is the
bin stamp, events column ``ts_ist``), plus the wall row for the grid point. Nothing else: no minute-level data (operator ruling
on O-5, 2026-11-06), so the page, which reads the same tables, computes the same flags.

Derivation per wall at grid point T (K = the wall strike, leg CE for the call wall and PE for the put wall):
  wall_known      a wall row exists for T and names a strike for this wall
  in_window       (K, leg) on the wall row's expiry has a cycle row stamped T
  conc_evaluable  that strike-leg has >= 12 cycle rows stamped before T (the history the CONC test at T uses)
  thin_evaluable  sum of minutes_present_5 over its rows stamped T-25 .. T (six bins = the 30 minutes before T) is >= 20
  C               a CONC event at (K, leg) with T - 15 min < ts_ist <= T
  N               a THIN event with side ask at (K, leg) in the same window (ask on both legs, ruling R-3)
  untraded        no trades at (K, leg) in rows stamped <= T, and T >= 10:00 (the vendor OI artefact, TD-S95-NEW-1)
Display inputs carried in the flags: trades_cum, n_prior_bins, minutes_present_30, oi_build_15 (sum of oi_delta_5 over the rows in
the window; NULL when every one is NULL, never 0).

Label, first match wins: no wall -> NO_READ; not in window -> NO_READ; untraded -> NO_READ; both evaluable -> the 2x2 of C and N
(HIT, ABSORBED, THINNING, QUIET); only thin evaluable -> THINNING partial on N, else NO_READ; otherwise NO_READ. A gap is never
QUIET.
"""

RULE_VERSION = "v1"
LOOKBACK_MIN = 15
CONC_MIN_PRIOR = 12
THIN_MIN_PRESENT = 20
THIN_SPAN_MIN = 25
UNTRADED_FROM_MIN = 600
LABELS = ("HIT", "ABSORBED", "THINNING", "QUIET", "NO_READ")
LEG = {"call": "CE", "put": "PE"}
WALL_COL = {"call": "call_wall", "put": "put_wall"}


def _min(ts):
    """'YYYY-MM-DDTHH:MM:SS+05:30' -> minutes since midnight, IST."""
    return int(ts[11:13]) * 60 + int(ts[14:16])


def _int(s):
    return None if s is None or s == "" else int(s)


def _same_strike(a, k):
    return a not in (None, "") and float(a) == k


def derive_flags(cycle_rows, events, wall_row, T, wall):
    """cycle_rows / events: dicts of strings as the CSVs render them; wall_row: dict or None; T: grid stamp; wall: call | put."""
    tm = _min(T)
    leg = LEG[wall]
    f = {"wall_known": False, "in_window": False, "untraded": False, "conc_evaluable": False, "thin_evaluable": False,
         "C": False, "N": False, "trades_cum": None, "n_prior_bins": None, "minutes_present_30": None, "oi_build_15": None}
    k_s = None if wall_row is None else wall_row.get(WALL_COL[wall])
    if k_s in (None, ""):
        return f
    f["wall_known"] = True
    k = float(k_s)
    sym, exp = wall_row["symbol"], wall_row["expiry"]
    lo = tm - LOOKBACK_MIN
    own = [r for r in cycle_rows if r["symbol"] == sym and r["expiry"] == exp and r["leg"] == leg
           and _same_strike(r["strike"], k) and _min(r["T"]) <= tm]
    f["in_window"] = any(_min(r["T"]) == tm for r in own)
    f["n_prior_bins"] = sum(1 for r in own if _min(r["T"]) < tm)
    f["conc_evaluable"] = f["n_prior_bins"] >= CONC_MIN_PRIOR
    f["minutes_present_30"] = sum(_int(r["minutes_present_5"]) or 0 for r in own if _min(r["T"]) >= tm - THIN_SPAN_MIN)
    f["thin_evaluable"] = f["minutes_present_30"] >= THIN_MIN_PRESENT
    f["trades_cum"] = sum(_int(r["trades_5"]) or 0 for r in own)
    f["untraded"] = f["trades_cum"] == 0 and tm >= UNTRADED_FROM_MIN
    ob = [_int(r["oi_delta_5"]) for r in own if lo < _min(r["T"])]
    ob = [x for x in ob if x is not None]
    f["oi_build_15"] = sum(ob) if ob else None
    for e in events:
        if e["symbol"] != sym or e["expiry"] != exp or e["leg"] != leg or not _same_strike(e["strike"], k):
            continue
        if lo < _min(e["ts_ist"]) <= tm:
            if e["kind"] == "CONC":
                f["C"] = True
            elif e["kind"] == "THIN" and e["side"] == "ask":
                f["N"] = True
    return f


def label_wall(f):
    """flags -> (label, partial, reason). First match wins (spec s4)."""
    if not f["wall_known"]:
        return ("NO_READ", False, "no chain run")
    if not f["in_window"]:
        return ("NO_READ", False, "wall outside subscribed window")
    if f["untraded"]:
        return ("NO_READ", False, "untraded wall (vendor OI)")
    if f["conc_evaluable"] and f["thin_evaluable"]:
        if f["C"] and f["N"]:
            return ("HIT", False, "")
        if f["C"]:
            return ("ABSORBED", False, "")
        if f["N"]:
            return ("THINNING", False, "")
        return ("QUIET", False, "")
    if f["thin_evaluable"]:
        if f["N"]:
            return ("THINNING", True, "flow n/a")
        return ("NO_READ", False, "flow not yet evaluable")
    return ("NO_READ", False, "insufficient history")
