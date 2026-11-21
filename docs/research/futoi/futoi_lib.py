"""Shared loading and session logic for the MR-FOI M1/M2 run (2026-11-17).

Clock: all tables carry the vendor clock (IST written as UTC, seconds :59).
No conversion is made between them -- prereg section 2, independently codified
at .claude/rules/data-access.md (S61 / TD-S61-NEW-2, zero shift).

Close: the last bar at or before 15:29:59. The 15:30 bar is never used.
"""
import csv
import os

NIFTY = "9992f600-51b3-4009-b487-f878692a0bc5"
SENSEX = "73a1390a-30c9-46d6-9d3f-5f03c3f5ad71"
WINDOW_LO, WINDOW_HI = "2025-04-01", "2026-03-30"

SESSION_FIRST = "09:15:59"
SESSION_CLOSE = "15:29:59"
SESSION_MINUTES = 375                 # 09:15:59..15:29:59 inclusive, measured

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def _f(x):
    return None if x is None or x == "" else float(x)


def load_futures(path=None):
    """-> {trade_date: {series: [(hhmmss, close, oi, volume), ...]}} time-ordered."""
    path = path or os.path.join(DATA, "futures_bars.csv")
    out = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r["trade_date"], {}).setdefault(int(r["contract_series"]), []).append(
                (r["hhmmss"], _f(r["close"]), _f(r["oi"]), _f(r["volume"])))
    return out


def load_spot(path=None):
    """-> {trade_date: {hhmmss: close}}"""
    path = path or os.path.join(DATA, "spot_bars.csv")
    out = {}
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            out.setdefault(r["trade_date"], {})[r["hhmmss"]] = _f(r["close"])
    return out


def series_close(bars_for_series):
    """Section 2's close: the last bar at or before 15:29:59, per series.
    contract_series 3 is absent at exactly 15:29:59 on some sessions, so this
    is a <= scan, not an equality match."""
    best = None
    for hhmmss, close, oi, vol in bars_for_series:
        if hhmmss <= SESSION_CLOSE and (best is None or hhmmss > best[0]):
            best = (hhmmss, close, oi, vol)
    return best


def futures_total_oi(fut, d):
    """F(d): total futures OI, series 1+2+3, at the close of session d.
    Roll-invariant (prereg section 3). Returns (F, {series: oi}, missing_series).

    F is None unless ALL THREE series are present at the close. A partial sum is
    not F(d): it is a different quantity that loses exactly the roll-invariance
    section 3 depends on, and it would fall across a roll for a reason that has
    nothing to do with option expiry -- the effect M1 is trying to measure.

    IMPLEMENTATION CORRECTION, made before any outcome was computed. The first
    version returned sum(present) and the caller ignored `missing`. MEASURED
    EFFECT: 0 of 247 sessions, so no number in this run changes. The defect was
    latent because section 2's close rule -- the last bar at or before 15:29:59,
    applied per series -- already recovers series 3 on the sessions where it is
    absent at exactly 15:29:59 (e.g. 2025-10-15). `missing` is still returned so
    a caller can count and report, and detect_futures_expiries, which uses only
    the per-series dict and never the sum, is unaffected."""
    per = {}
    missing = []
    for s in (1, 2, 3):
        b = series_close(fut.get(d, {}).get(s, []))
        if b is None or b[2] is None:
            missing.append(s)
        else:
            per[s] = b[2]
    F = sum(per.values()) if not missing else None
    return F, per, missing


def detect_futures_expiries(fut, sessions):
    """Futures expiry days, inferred because hist_future_bars_1m.expiry_date is
    NULL on all 260,126 NIFTY rows (measured, Part 0 step 2).

    Operator-confirmed threshold-free ladder rule, applied as the CONJUNCTION it
    was stated to be: session d is a futures expiry iff (a) among
    {OI_s1(d), OI_s2(d), OI_s3(d)} at the close, the value nearest OI_s1(d+1) is
    OI_s2(d) -- the contract ladder shifted by one -- AND (b) OI_s2(d+1) is
    nearest OI_s3(d), the same shift one rung down.

    CHANGE OF RECORD: this was first coded as clause (a) ALONE. It was changed to
    (a) AND (b) after the Part 0 measurement below and BEFORE any outcome in
    sections 3, 4 or 7 was computed. The measurement that forced the change:
    clause (a) alone fires on 21 of 246 session pairs and its margin does NOT
    separate -- weakest firing 1.05x against strongest non-firing 1.03x, i.e. a
    coin toss at the boundary. (a) AND (b) fires on 11, every one at margin
    >= 9.82x against a best (a)-only margin of 4.94x. No tolerance is tuned; the
    separation is reported, not imposed. `ladder_only` is kept on every row so
    clause (a)'s behaviour stays auditable.

    LAST SESSION: the rule cannot decide the final session in the data, because
    there is no d+1. See OPERATOR_SUPPLIED_FUT_EXPIRY.

    Returns a list of dicts, one per session, each carrying the decision and the
    margin that produced it, so every call is auditable. No tolerance is tuned.
    """
    rows = []
    for i, d in enumerate(sessions[:-1]):
        nxt = sessions[i + 1]
        _, per_d, _ = futures_total_oi(fut, d)
        _, per_n, _ = futures_total_oi(fut, nxt)
        if 1 not in per_n or 1 not in per_d or 2 not in per_d:
            rows.append({"date": d, "next": nxt, "decidable": False, "rolled": False,
                         "ladder_only": False,
                         "reason": "missing series at close", "argmin": None,
                         "margin_ratio": None, "corroborated": None})
            continue
        cands = {s: per_d[s] for s in (1, 2, 3) if s in per_d}
        target = per_n[1]
        dist = {s: abs(v - target) for s, v in cands.items()}
        argmin = min(dist, key=dist.get)
        ordered = sorted(dist.values())
        margin = (ordered[1] / ordered[0]) if len(ordered) > 1 and ordered[0] > 0 else None
        corrob = None
        if 2 in per_n and 3 in per_d and 2 in per_d:
            d2 = {s: abs(per_d[s] - per_n[2]) for s in cands}
            corrob = (min(d2, key=d2.get) == 3)
        rows.append({"date": d, "next": nxt, "decidable": True,
                     "rolled": (argmin == 2) and bool(corrob),
                     "ladder_only": argmin == 2,
                     "reason": "", "argmin": argmin, "margin_ratio": margin,
                     "corroborated": corrob,
                     "oi_s1_d": per_d.get(1), "oi_s2_d": per_d.get(2), "oi_s3_d": per_d.get(3),
                     "oi_s1_next": per_n.get(1), "oi_s2_next": per_n.get(2)})
    return rows


# The ladder rule needs a d+1 and so cannot decide the LAST session in the data.
# 2026-03-30 is a NIFTY futures expiry: the Fyers expired-contracts API lists the
# NIFTY futures and the month-end option expiry on that date (operator-supplied
# 2026-11-17). It is OPERATOR-SUPPLIED, NOT INFERRED from the OI ladder, and is
# listed as such in NOT_VERIFIED.md -- this run did not verify it against Fyers.
OPERATOR_SUPPLIED_FUT_EXPIRY = {
    "2026-03-30": "operator-supplied, not inferred (Fyers expired-contracts API, 2026-11-17)",
}


def futures_expiry_dates(fut, sessions):
    """The section 2 futures expiry list: inferred by the ladder rule, plus any
    operator-supplied date that falls inside the sessions actually held.
    Returns (sorted dates, {date: provenance})."""
    rows = detect_futures_expiries(fut, sessions)
    prov = {r["date"]: "inferred (OI ladder, clauses a AND b)" for r in rows if r["rolled"]}
    for d, why in OPERATOR_SUPPLIED_FUT_EXPIRY.items():
        if d in sessions:
            prov[d] = why
    return sorted(prov), prov


def excluded_by_s2(fut_expiries, sessions):
    """Section 2: futures expiry days AND the session after are excluded from
    every set in M1 and M2. Returns {date: reason}."""
    out = {}
    idx = {d: i for i, d in enumerate(sessions)}
    for e in fut_expiries:
        out[e] = "futures expiry day (s2)"
        i = idx.get(e)
        if i is not None and i + 1 < len(sessions):
            nxt = sessions[i + 1]
            out.setdefault(nxt, "session after a futures expiry (s2)")
    return out


def window_boundaries():
    """69 boundaries at 09:20:59, 09:25:59, ... 15:00:59 -> 68 non-overlapping
    5-minute windows (prereg section 4; count checked against section 6's 68).

    Operator-confirmed convention: for window k, dS and db are
    close(boundary k+1) - close(boundary k), and the dose g is read at
    boundary k. g is therefore fixed BEFORE the move it scales (Rule 0a)."""
    out = []
    t = 9 * 60 + 20
    while t <= 15 * 60:
        out.append("%02d:%02d:59" % (t // 60, t % 60))
        t += 5
    return out


def session_minutes():
    """The 375 minutes 09:15:59..15:29:59 -- the denominator for the 95% test."""
    out = []
    t = 9 * 60 + 15
    while t <= 15 * 60 + 29:
        out.append("%02d:%02d:59" % (t // 60, t % 60))
        t += 1
    return out
