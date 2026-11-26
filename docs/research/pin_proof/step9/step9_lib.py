"""Step 9: pure functions for the old-against-new comparison.

Design: PREREG.md (sha256 eef1981...a73f0) as amended by PREREG_A1.md
(sha256 792b1fb...57cb). No I/O, no database, no clock. Every figure of
section 4 and every control of section 6 / A1.3 is computed here so that the
self-test can exercise it without a database.

Units: every exposure is crore per 100 % move, the stored unit (ADR-032).
Shares and HHI have no unit.

ONE IMPLEMENTATION OF THE ARITHMETIC
------------------------------------
Condition 4 of the task requires aggregation inside the query and at most 100
rows back, so the pull never holds a run's strike rows. Every figure of section 4
is an aggregate, so the pull sends SQL that produces the aggregate record below
and hands it to `figures_from_agg`.

The self-test holds hand-worked STRIKE ROWS instead. It turns them into the same
aggregate record with `aggregate_all`, which is built out of the strike-level
definitions (`v1_net`, `v1_peak`, `v1_top_share`, `v1_hhi`, `_union`, ...), and
then calls the same `figures_from_agg`. So the figures have one implementation,
exercised by hand-worked numbers, and the SQL's only job is to reproduce the
aggregate fields -- which the controls C1a, C1b, C3, C4 and C7 test against four
independently stored or independently produced sources.

A run record (the self-test's form; `aggregate_all` consumes it):

    run_id, symbol, expiry_date (str), ts (datetime, naive IST), spot (float)
    v1_strikes : [{strike, gex_cr, gamma_call, gamma_put}]  from gex_strike_snapshots
    v1_dte     : int                                         from gex_strike_snapshots
    v2_run     : {net_cr, net_top_share, dte, spot, ts, symbol, expiry_date,
                  rule_version}                              from gex_run_v2
    v2_strikes : [{strike, net_cr, in_map}]                  from gex_strike_v2
    gch        : {net_gex, pin_leader_strike, conc_top1_share, conc_hhi} or None
    gm         : {net_gex} or None
    v1_chain_status : 'OK' | 'NOT_COMPUTED'

The aggregate record's field names are the column names the pull's SQL returns;
`step9_pull.py` builds it straight from one JSON row per run.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Optional, Sequence

# ---------------------------------------------------------------- constants

GUARD_GAMMA = 5e-5          # F7: a leg counts as carrying gamma above this
GUARD_BAND = 0.05           # F7: "more than 5 % from spot"
TOL_CR = 0.01               # C1a, C1b, C3: +/- 0.01 Cr
TOL_SHARE = 1e-6            # C7: equal means abs difference <= 1e-6
STRIKE_STEP = {"NIFTY": 50.0, "SENSEX": 100.0}
RULE_STAMP = "v2-1.2-gss"

# Section 3 boundaries, as minutes from midnight IST.
MAIN_OPEN = 9 * 60 + 15     # 09:15 inclusive
MAIN_CLOSE = 15 * 60 + 30   # 15:30 inclusive
MAIN_WINDOWS = (
    ("w1_0915_1059", 9 * 60 + 15, 10 * 60 + 59),
    ("w2_1100_1359", 11 * 60 + 0, 13 * 60 + 59),
    ("w3_1400_1530", 14 * 60 + 0, 15 * 60 + 30),
)

# Section 5 fixed bins for the F1 relative change and for W.
REL_BINS = (("under_1pct", 0.01), ("1_to_10pct", 0.10),
            ("10_to_50pct", 0.50), ("50pct_or_more", None))
# F2 fixed bins for r.
R_BINS = (("under_1pct", 0.01), ("1_to_5pct", 0.05), ("5pct_or_more", None))


# ---------------------------------------------------------------- sets, §3

def minute_of_day(ts) -> int:
    """Clock time truncated to the minute, as minutes from midnight IST."""
    return ts.hour * 60 + ts.minute


def classify_set(ts) -> str:
    """'pre_open' | 'main' | 'post_close'. 09:15 and 15:30 are both MAIN."""
    m = minute_of_day(ts)
    if m < MAIN_OPEN:
        return "pre_open"
    if m > MAIN_CLOSE:
        return "post_close"
    return "main"


def main_window(ts) -> Optional[str]:
    """The §3 time-of-day window, or None when the run is not in the main set."""
    if classify_set(ts) != "main":
        return None
    m = minute_of_day(ts)
    for name, lo, hi in MAIN_WINDOWS:
        if lo <= m <= hi:
            return name
    return None


def is_0915(ts) -> bool:
    """The 09:15 run, printed on its own line as well as kept in the main set."""
    return minute_of_day(ts) == MAIN_OPEN


def dte_bucket(dte) -> str:
    if dte is None:
        return "unknown"
    d = int(dte)
    if d <= 0:
        return "0"
    if d <= 2:
        return "1_to_2"
    return "3_or_more"


def schedule_period(d) -> str:
    """§5: before 26 Oct 2026, from 26 Oct 2026. `d` is a date."""
    return "from_2026_10_26" if (d.month, d.day) >= (10, 26) and d.year >= 2026 \
        else "before_2026_10_26"


def bin_value(x: Optional[float], bins) -> Optional[str]:
    """Lower-closed, upper-open fixed bins: a value exactly on a boundary
    belongs to the HIGHER bin. r = 0.01 is '1_to_5pct', never 'under_1pct'
    (self-test mutant M9)."""
    if x is None:
        return None
    for name, upper in bins:
        if upper is None or x < upper:
            return name
    return bins[-1][0]


def bin_rel(x: Optional[float]) -> Optional[str]:
    return bin_value(x, REL_BINS)


def bin_r(x: Optional[float]) -> Optional[str]:
    return bin_value(x, R_BINS)


# ---------------------------------------------------------------- helpers

def _f(x) -> Optional[float]:
    return None if x is None else float(x)


def sgn(x: Optional[float]) -> Optional[int]:
    if x is None:
        return None
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def sign_label(x: Optional[float]) -> str:
    s = sgn(x)
    return {None: "none", 1: "positive", 0: "zero", -1: "negative"}[s]


def strike_net_from_legs(gamma_call, oi_call, gamma_put, oi_put, spot) -> float:
    """The sign convention of the stored V1 column: the CALL side positive and
    the PUT side NEGATED, scaled by S^2 / 1e7.

    The pull never recomputes a stored value -- A1.2 reads gex_cr as stored --
    so this exists only to build and check the self-test's invented runs, and
    it is the one place in this file where a put side is negated (self-test
    mutant M2 targets it).
    """
    return (float(gamma_call) * float(oi_call)
            - float(gamma_put) * float(oi_put)) * float(spot) ** 2 / 1e7


def quantile(xs: Sequence[float], q: float) -> Optional[float]:
    """Linear-interpolation quantile on the sorted sample. q in [0, 1]."""
    vals = sorted(float(v) for v in xs if v is not None)
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = q * (len(vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)


def spread(xs: Sequence[float]) -> dict:
    """§5: median, 90th, 99th, maximum, and n."""
    vals = [float(v) for v in xs if v is not None]
    return {
        "n": len(vals),
        "median": quantile(vals, 0.50),
        "p90": quantile(vals, 0.90),
        "p99": quantile(vals, 0.99),
        "max": max(vals) if vals else None,
    }


def k_of_n(k: int, n: int) -> str:
    return "%d of %d" % (k, n)


def _ratio(num, den) -> Optional[float]:
    """None when the denominator is 0 or missing -- A1.2's "none when the sum
    is 0", and never a silent zero."""
    if num is None or den is None or float(den) == 0.0:
        return None
    return float(num) / float(den)


# -------------------------------------------- V1 strike-level definitions, A1.2
# These are the DEFINITIONS. The pull reproduces them in SQL; the self-test
# reaches them through aggregate_v1 with hand-worked strike rows.

def v1_abs_sum(strikes) -> float:
    return sum(abs(_f(s["gex_cr"])) for s in strikes)


def v1_net(strikes) -> float:
    """F1, F2: V1 net = the sum of the stored gex_cr (A1.2)."""
    return sum(_f(s["gex_cr"]) for s in strikes)


def _peak(strikes, key, spot, positive_only=False):
    """Largest `key` over the rows; ties go to the strike nearer spot, then the
    lower strike. Returns (strike, value, n_tied) or (None, None, 0)."""
    rows = [s for s in strikes if s.get(key) is not None]
    if positive_only:
        rows = [s for s in rows if _f(s[key]) > 0]
    if not rows:
        return None, None, 0
    best = max(_f(s[key]) for s in rows)
    tied = [s for s in rows if _f(s[key]) == best]
    tied.sort(key=lambda s: (abs(_f(s["strike"]) - float(spot)), _f(s["strike"])))
    return _f(tied[0]["strike"]), best, len(tied)


def v1_peak(strikes, spot):
    """F3 V1: the strike with the largest ABS gex_cr (mutant M3 drops the abs)."""
    rows = [{"strike": s["strike"], "k": abs(_f(s["gex_cr"]))} for s in strikes]
    return _peak(rows, "k", spot)


def v1_largest_positive(strikes, spot):
    """F3b V1: the largest gex_cr that is > 0 -- NOT an abs (mutant M4)."""
    rows = [{"strike": s["strike"], "k": _f(s["gex_cr"])} for s in strikes]
    return _peak(rows, "k", spot, positive_only=True)


def v1_top_share(strikes) -> Optional[float]:
    """F4 V1: max abs gex_cr / sum of abs gex_cr. None when the sum is 0."""
    if not strikes:
        return None
    return _ratio(max(abs(_f(s["gex_cr"])) for s in strikes), v1_abs_sum(strikes))


def v1_hhi(strikes) -> Optional[float]:
    """F5 V1: the sum of (abs gex_cr / sum of abs gex_cr) squared.

    Equal to sum(gex_cr^2) / sum(abs gex_cr)^2, which is the form the pull's SQL
    returns -- so `aggregate_v1` carries the two sums and `f5` divides them.
    """
    d = v1_abs_sum(strikes)
    if d == 0:
        return None
    return sum((abs(_f(s["gex_cr"])) / d) ** 2 for s in strikes)


# -------------------------------------------- V2 strike-level definitions

def v2_map(strikes):
    """The map: the rows of gex_strike_v2 with in_map true."""
    return [s for s in strikes if s.get("in_map")]


def v2_abs_sum(strikes) -> float:
    return sum(abs(_f(s["net_cr"])) for s in strikes)


def v2_strike_sum(strikes) -> float:
    return sum(_f(s["net_cr"]) for s in strikes)


def v2_peak(strikes, spot):
    """F3 V2: the strike with the largest abs net_cr(K) over the map."""
    rows = [{"strike": s["strike"], "k": abs(_f(s["net_cr"]))} for s in strikes]
    return _peak(rows, "k", spot)


def v2_largest_positive(strikes, spot):
    rows = [{"strike": s["strike"], "k": _f(s["net_cr"])} for s in strikes]
    return _peak(rows, "k", spot, positive_only=True)


def _union(run, within_5pct=False):
    """F6: the union of strikes, a missing row counting as 0."""
    spot = float(run["spot"])

    def keep(k):
        return (not within_5pct) or abs(k - spot) <= GUARD_BAND * spot

    a = {_f(s["strike"]): _f(s["gex_cr"]) for s in run["v1_strikes"]}
    b = {_f(s["strike"]): _f(s["net_cr"]) for s in v2_map(run["v2_strikes"])}
    keys = sorted(k for k in set(a) | set(b) if keep(k))   # mutant M5 drops V2-only
    return a, b, keys


# ---------------------------------------------------------------- aggregates
# The field names below are the column names the pull's SQL returns.

def aggregate_v1(strikes, spot) -> dict:
    """The per-run V1 aggregate, from gex_strike_snapshots rows."""
    pk, _, pk_ties = v1_peak(strikes, spot)
    ps, _, ps_ties = v1_largest_positive(strikes, spot)
    in5 = [s for s in strikes
           if abs(_f(s["strike"]) - float(spot)) <= GUARD_BAND * float(spot)]
    legs_with_gamma = legs_removed = 0
    abs_at_removed = 0.0
    for s in strikes:
        far = abs(_f(s["strike"]) - float(spot)) > GUARD_BAND * float(spot)
        hit = False
        for side in ("gamma_call", "gamma_put"):
            g = _f(s.get(side))
            if g is None:
                continue
            legs_with_gamma += 1
            if g > GUARD_GAMMA and far:
                legs_removed += 1
                hit = True
        if hit:
            abs_at_removed += abs(_f(s["gex_cr"]))
    return {
        "v1_n": len(strikes),
        "v1_net": v1_net(strikes),
        "v1_abs": v1_abs_sum(strikes),
        "v1_sq": sum(_f(s["gex_cr"]) ** 2 for s in strikes),
        "v1_maxabs": max((abs(_f(s["gex_cr"])) for s in strikes), default=None),
        "v1_peak_strike": pk, "v1_peak_ties": pk_ties,
        "v1_pos_strike": ps, "v1_pos_ties": ps_ties,
        "v1_net_in5": sum(_f(s["gex_cr"]) for s in in5),
        "v1_abs_in5": sum(abs(_f(s["gex_cr"])) for s in in5),
        "legs_with_gamma": legs_with_gamma,
        "legs_removed": legs_removed,
        "v1_abs_at_removed": abs_at_removed,
    }


def aggregate_v2(strikes, spot) -> dict:
    """The per-run V2 aggregate, over the MAP rows of gex_strike_v2."""
    mp = v2_map(strikes)
    pk, _, pk_ties = v2_peak(mp, spot)
    ps, _, ps_ties = v2_largest_positive(mp, spot)
    in5 = [s for s in mp
           if abs(_f(s["strike"]) - float(spot)) <= GUARD_BAND * float(spot)]
    return {
        "v2_n_map": len(mp),
        "v2_strike_sum": v2_strike_sum(mp),
        "v2_abs": v2_abs_sum(mp),
        "v2_sq": sum(_f(s["net_cr"]) ** 2 for s in mp),
        "v2_maxabs": max((abs(_f(s["net_cr"])) for s in mp), default=None),
        "v2_peak_strike": pk, "v2_peak_ties": pk_ties,
        "v2_pos_strike": ps, "v2_pos_ties": ps_ties,
        "v2_net_in5": sum(_f(s["net_cr"]) for s in in5),
    }


def aggregate_cross(run) -> dict:
    """The per-run F6 cross aggregate, over the union of strikes, and the same
    over the strikes within 5 % of spot (F7's restricted W)."""
    out = {}
    for tag, within in (("x", False), ("x5", True)):
        a, b, keys = _union(run, within)
        n_both = n_v1 = n_v2 = n_sign = n_sign_nz = n_v1z = n_v2z = 0
        w_num = w_den = 0.0
        for k in keys:
            x, y = a.get(k), b.get(k)
            xv, yv = (0.0 if x is None else x), (0.0 if y is None else y)
            if x is not None and y is not None:
                n_both += 1
            elif y is None:
                n_v1 += 1
            else:
                n_v2 += 1
            if sgn(xv) != sgn(yv):
                n_sign += 1
                if xv != 0 and yv != 0:
                    n_sign_nz += 1
            if xv == 0 and yv != 0:
                n_v1z += 1
            if xv != 0 and yv == 0:
                n_v2z += 1
            w_num += abs(yv - xv)
            w_den += abs(xv)
        out.update({
            tag + "_n_union": len(keys), tag + "_n_both": n_both,
            tag + "_n_v1_only": n_v1, tag + "_n_v2_only": n_v2,
            tag + "_n_sign": n_sign, tag + "_n_sign_nz": n_sign_nz,
            tag + "_n_v1z_v2nz": n_v1z, tag + "_n_v1nz_v2z": n_v2z,
            tag + "_w_num": w_num, tag + "_w_den": w_den,
        })
    return out


def aggregate_all(run) -> dict:
    """Assemble the flat aggregate record from a strike-level run record.

    This is the self-test's path into `figures_from_agg`; the pull assembles the
    same record from one JSON row per run.
    """
    spot = float(run["spot"])
    v2r = run["v2_run"]
    a = {
        "run_id": run["run_id"], "symbol": run["symbol"],
        "ts": run["ts"], "expiry_date": str(run["expiry_date"]), "spot": spot,
        "r_net_cr": _f(v2r["net_cr"]),
        "r_net_top_share": _f(v2r.get("net_top_share")),
        "r_dte": v2r.get("dte"),
        "r_symbol": v2r.get("symbol"), "r_expiry_date": str(v2r.get("expiry_date")),
        "r_ts": v2r.get("ts"), "r_rule_version": v2r.get("rule_version"),
        # V1 identity, as the SQL returns it: one distinct value per run or a count > 1
        "v1_dte": run.get("v1_dte"), "v1_dte_n": run.get("v1_dte_n", 1),
        "v1_symbol": run["symbol"], "v1_symbol_n": 1,
        "v1_expiry_date": str(run["expiry_date"]), "v1_expiry_n": 1,
        "v1_ts": run["ts"], "v1_ts_n": 1,
        # V2 strike-row identity
        "v2_symbol": run["symbol"], "v2_symbol_n": 1,
        "v2_expiry_date": str(run["expiry_date"]), "v2_expiry_n": 1,
        "v2_ts": run["ts"], "v2_ts_n": 1,
        "v1_chain_status": run.get("v1_chain_status"),
        "gch": run.get("gch"), "gm": run.get("gm"),
    }
    a.update(aggregate_v1(run["v1_strikes"], spot))
    a.update(aggregate_v2(run["v2_strikes"], spot))
    a.update(aggregate_cross(run))
    return a


# ---------------------------------------------------------------- F1 to F7
# Every figure reads the aggregate record. One implementation.

def f1(a) -> dict:
    """Net exposure: V2 - V1 in Cr, and the relative change when V1 != 0."""
    v1, v2 = float(a["v1_net"]), float(a["r_net_cr"])
    d = v2 - v1
    rel = None if v1 == 0 else abs(d) / abs(v1)
    return {"v1": v1, "v2": v2, "diff": d, "rel": rel,
            "v1_is_zero": v1 == 0, "rel_bin": bin_rel(rel)}


def f2(a) -> dict:
    r1 = _ratio(abs(float(a["v1_net"])), a["v1_abs"])
    r2 = _ratio(abs(float(a["r_net_cr"])), a["v2_abs"])
    return {"v1_sign": sign_label(float(a["v1_net"])),
            "v2_sign": sign_label(float(a["r_net_cr"])),
            "v1_r": r1, "v2_r": r2, "v1_r_bin": bin_r(r1), "v2_r_bin": bin_r(r2)}


def _steps(x, y, symbol) -> Optional[float]:
    if x is None or y is None:
        return None
    return abs(x - y) / STRIKE_STEP.get(symbol, 50.0)


def f3(a) -> dict:
    k1, k2 = _f(a["v1_peak_strike"]), _f(a["v2_peak_strike"])
    return {"v1_strike": k1, "v2_strike": k2,
            "same": (k1 is not None and k1 == k2),
            "steps": _steps(k1, k2, a["symbol"]),
            "v1_ties": a["v1_peak_ties"], "v2_ties": a["v2_peak_ties"]}


def f3b(a) -> dict:
    k1, k2 = _f(a["v1_pos_strike"]), _f(a["v2_pos_strike"])
    return {"v1_strike": k1, "v2_strike": k2,
            "same": (k1 is not None and k1 == k2),
            "steps": _steps(k1, k2, a["symbol"]),
            "v1_none": k1 is None, "v2_none": k2 is None,
            "one_side_none": (k1 is None) != (k2 is None),
            "v1_ties": a["v1_pos_ties"], "v2_ties": a["v2_pos_ties"]}


def f4(a) -> dict:
    v1 = _ratio(a["v1_maxabs"], a["v1_abs"])
    v2 = _f(a.get("r_net_top_share"))
    return {"v1": v1, "v2": v2,
            "diff_pp": None if (v1 is None or v2 is None) else (v2 - v1) * 100.0}


def f5(a) -> dict:
    v1 = _ratio(a["v1_sq"], float(a["v1_abs"]) ** 2) if a["v1_abs"] else None
    v2 = _ratio(a["v2_sq"], float(a["v2_abs"]) ** 2) if a["v2_abs"] else None
    return {"v1": v1, "v2": v2,
            "diff": None if (v1 is None or v2 is None) else v2 - v1}


def f6(a) -> dict:
    W = _ratio(a["x_w_num"], a["x_w_den"])
    return {"n_union": a["x_n_union"], "n_both": a["x_n_both"],
            "n_v1_only": a["x_n_v1_only"], "n_v2_only": a["x_n_v2_only"],
            "n_sign_change": a["x_n_sign"],
            "n_sign_change_both_nonzero": a["x_n_sign_nz"],
            "n_v1_zero_v2_nonzero": a["x_n_v1z_v2nz"],
            "n_v1_nonzero_v2_zero": a["x_n_v1nz_v2z"],
            "w_num": float(a["x_w_num"]), "w_den": float(a["x_w_den"]),
            "W": W, "W_bin": bin_rel(W)}


def f7(a) -> dict:
    """The guard beyond 5 %: legs with stored gamma > 5e-5 at a strike more than
    5 % from spot, and F1 and W recomputed over strikes within 5 % only."""
    v1_in5, v2_in5 = float(a["v1_net_in5"]), float(a["v2_net_in5"])
    return {"legs_with_gamma": a["legs_with_gamma"],
            "legs_removed": a["legs_removed"],
            "share_abs_at_removed": _ratio(a["v1_abs_at_removed"], a["v1_abs"]),
            "f1_v1_in5": v1_in5, "f1_v2_in5": v2_in5,
            "f1_diff_in5": v2_in5 - v1_in5,
            "f1_rel_in5": None if v1_in5 == 0 else abs(v2_in5 - v1_in5) / abs(v1_in5),
            "W_in5": _ratio(a["x5_w_num"], a["x5_w_den"])}


# ---------------------------------------------------------------- controls

def c1a(a) -> Optional[bool]:
    """V1 net of A1.2 against gex_cycle_history.net_gex, +/- 0.01 Cr."""
    g = a.get("gch")
    if not g or g.get("net_gex") is None:
        return None
    return abs(float(a["v1_net"]) - float(g["net_gex"])) <= TOL_CR


def c1b(a) -> Optional[bool]:
    """V1 net of A1.2 against gamma_metrics.net_gex, +/- 0.01 Cr."""
    g = a.get("gm")
    if not g or g.get("net_gex") is None:
        return None
    return abs(float(a["v1_net"]) - float(g["net_gex"])) <= TOL_CR


def c2(a) -> Optional[bool]:
    """V1 net peak of A1.2 against gex_cycle_history.pin_leader_strike."""
    g = a.get("gch")
    if not g or g.get("pin_leader_strike") is None:
        return None
    k = _f(a["v1_peak_strike"])
    return k is not None and k == _f(g["pin_leader_strike"])


def c3(a) -> bool:
    """STOP: run net_cr against the sum of net_cr(K), +/- 0.01 Cr."""
    return abs(float(a["r_net_cr"]) - float(a["v2_strike_sum"])) <= TOL_CR


def _eq_ts(x, y) -> bool:
    if x is None or y is None:
        return False
    return str(x) == str(y)


def c6(a) -> dict:
    """STOP: run identity -- the symbol, expiry and timestamp of the V2 rows
    equal those of the V1 rows with the same run_id -- and (A1.2) dte one value
    per run and equal to gex_run_v2.dte."""
    single = (a.get("v1_symbol_n") == 1 and a.get("v1_expiry_n") == 1
              and a.get("v1_ts_n") == 1 and a.get("v2_symbol_n") == 1
              and a.get("v2_expiry_n") == 1 and a.get("v2_ts_n") == 1)
    ok_sym = a.get("v1_symbol") == a.get("v2_symbol") == a.get("r_symbol")
    ok_exp = (str(a.get("v1_expiry_date")) == str(a.get("v2_expiry_date"))
              == str(a.get("r_expiry_date")))
    ok_ts = (_eq_ts(a.get("v1_ts"), a.get("v2_ts"))
             and _eq_ts(a.get("v1_ts"), a.get("r_ts")))
    dte_one = a.get("v1_dte_n") == 1
    ok_dte = (a.get("v1_dte") is not None and a.get("r_dte") is not None
              and int(a["v1_dte"]) == int(a["r_dte"]))
    ok_stamp = a.get("r_rule_version") == RULE_STAMP
    return {"single_valued": single, "symbol": ok_sym, "expiry": ok_exp,
            "ts": ok_ts, "dte_single_value": dte_one, "dte_equal": ok_dte,
            "rule_version": ok_stamp,
            "ok": all([single, ok_sym, ok_exp, ok_ts, dte_one, ok_dte, ok_stamp])}


def c7(a) -> dict:
    """V1 top share and HHI of A1.2 against the stored conc_ columns."""
    out = {"top_share_equal": None, "top_share_diff": None,
           "hhi_equal": None, "hhi_diff": None}
    g = a.get("gch")
    if not g:
        return out
    v1t = _ratio(a["v1_maxabs"], a["v1_abs"])
    v1h = _ratio(a["v1_sq"], float(a["v1_abs"]) ** 2) if a["v1_abs"] else None
    if g.get("conc_top1_share") is not None and v1t is not None:
        d = v1t - float(g["conc_top1_share"])
        out["top_share_diff"] = d
        out["top_share_equal"] = abs(d) <= TOL_SHARE
    if g.get("conc_hhi") is not None and v1h is not None:
        d = v1h - float(g["conc_hhi"])
        out["hhi_diff"] = d
        out["hhi_equal"] = abs(d) <= TOL_SHARE
    return out


# ---------------------------------------------------------------- strata, §5

def chain_stratum(status) -> str:
    """§5: the V1 chain-check status, faithfully. A NOT_COMPUTED run is never
    put in the OK stratum (mutant M8)."""
    if status is None:
        return "NOT_COMPUTED"
    s = str(status).upper()
    return "OK" if s == "OK" else "NOT_COMPUTED"


def strata(a) -> dict:
    ts = a["ts"]
    return {
        "symbol": a["symbol"],
        "set": classify_set(ts),
        "window": main_window(ts),
        "dte": dte_bucket(a.get("v1_dte")),
        "chain": chain_stratum(a.get("v1_chain_status")),
        "schedule": schedule_period(ts.date()),
        "provenance": "period_1",      # PROVENANCE.md: one writer period
        "day": ts.date().isoformat(),
    }


def figures_from_agg(a) -> dict:
    """Every per-run figure and control, from the aggregate record."""
    return {
        "run_id": a["run_id"], "symbol": a["symbol"],
        "ts": a["ts"].isoformat(), "spot": float(a["spot"]),
        "expiry_date": str(a["expiry_date"]),
        "is_0915": is_0915(a["ts"]),
        "strata": strata(a),
        "F1": f1(a), "F2": f2(a), "F3": f3(a), "F3b": f3b(a),
        "F4": f4(a), "F5": f5(a), "F6": f6(a), "F7": f7(a),
        "C1a": c1a(a), "C1b": c1b(a), "C2": c2(a),
        "C3": c3(a), "C6": c6(a), "C7": c7(a),
    }


def figures(run) -> dict:
    """The self-test's entry point: strike rows in, the same figures out."""
    return figures_from_agg(aggregate_all(run))


# ---------------------------------------------------------------- summaries

def summarise(records: Iterable[dict], key) -> dict:
    """Group per-run records by `key(rec)` and build the §5 cells."""
    groups: dict[Any, list] = {}
    for rec in records:
        groups.setdefault(key(rec), []).append(rec)
    out = {}
    for g, rows in sorted(groups.items(), key=lambda kv: str(kv[0])):
        out[g] = cell(rows)
    return out


def cell(rows) -> dict:
    """§5: n runs and days; spreads of the signed and absolute differences for
    F1, F4, F5 and W; fixed bins; k of n for the count figures."""
    n = len(rows)
    days = sorted({r["strata"]["day"] for r in rows})
    f1d = [r["F1"]["diff"] for r in rows]
    f4d = [r["F4"]["diff_pp"] for r in rows if r["F4"]["diff_pp"] is not None]
    f5d = [r["F5"]["diff"] for r in rows if r["F5"]["diff"] is not None]
    wd = [r["F6"]["W"] for r in rows if r["F6"]["W"] is not None]
    rel = [r["F1"]["rel"] for r in rows if r["F1"]["rel"] is not None]

    def bins(vals, binner):
        b = {name: 0 for name, _ in (REL_BINS if binner is bin_rel else R_BINS)}
        for v in vals:
            nm = binner(v)
            if nm is not None:
                b[nm] += 1
        return {k: k_of_n(v, len(vals)) for k, v in b.items()}

    return {
        "n_runs": n, "n_days": len(days),
        "F1_signed": spread(f1d), "F1_abs": spread([abs(v) for v in f1d]),
        "F1_rel_bins": bins(rel, bin_rel),
        "F1_v1_zero": k_of_n(sum(1 for r in rows if r["F1"]["v1_is_zero"]), n),
        "F4_signed": spread(f4d), "F4_abs": spread([abs(v) for v in f4d]),
        "F5_signed": spread(f5d), "F5_abs": spread([abs(v) for v in f5d]),
        "W": spread(wd), "W_bins": bins(wd, bin_rel),
        "F2_table": sign_table(rows),
        "F3_same": k_of_n(sum(1 for r in rows if r["F3"]["same"]), n),
        "F3b_same": k_of_n(sum(1 for r in rows if r["F3b"]["same"]), n),
        "F3b_one_side_none": k_of_n(
            sum(1 for r in rows if r["F3b"]["one_side_none"]), n),
        "F6_sign_change_runs": k_of_n(
            sum(1 for r in rows if r["F6"]["n_sign_change"] > 0), n),
        "F6_v2_only_runs": k_of_n(
            sum(1 for r in rows if r["F6"]["n_v2_only"] > 0), n),
        "F7_runs_with_removal": k_of_n(
            sum(1 for r in rows if r["F7"]["legs_removed"] > 0), n),
        "F7_legs_removed": sum(r["F7"]["legs_removed"] for r in rows),
        "F7_legs_with_gamma": sum(r["F7"]["legs_with_gamma"] for r in rows),
    }


def sign_table(rows) -> dict:
    """F2's 3 x 3 table, V1 sign against V2 sign."""
    names = ("negative", "zero", "positive")
    t = {a: {b: 0 for b in names} for a in names}
    for r in rows:
        a, b = r["F2"]["v1_sign"], r["F2"]["v2_sign"]
        if a in t and b in t[a]:
            t[a][b] += 1
    return t


def day_level(rows) -> dict:
    """§5 day level: the day's median F1 relative change, then the median and
    maximum over days; over all days and over days with >= 37 main-set runs."""
    per_day: dict[tuple, list] = {}
    for r in rows:
        if r["strata"]["set"] != "main":
            continue
        per_day.setdefault((r["strata"]["day"], r["symbol"]), []).append(r)
    all_days, long_days, short = {}, {}, []
    for k, rs in per_day.items():
        med = quantile([x["F1"]["rel"] for x in rs if x["F1"]["rel"] is not None], 0.5)
        all_days[k] = {"n_main": len(rs), "median_F1_rel": med}
        if len(rs) >= 37:
            long_days[k] = all_days[k]
        else:
            short.append({"day": k[0], "symbol": k[1], "n_main": len(rs)})

    def over(d):
        vals = [v["median_F1_rel"] for v in d.values() if v["median_F1_rel"] is not None]
        return {"n_days": len(d), "median_over_days": quantile(vals, 0.5),
                "max_over_days": max(vals) if vals else None}

    top10 = sorted(
        ({"day": k[0], "symbol": k[1], **v} for k, v in all_days.items()
         if v["median_F1_rel"] is not None),
        key=lambda v: v["median_F1_rel"], reverse=True)[:10]
    return {"all_days": over(all_days), "days_ge_37_main": over(long_days),
            "short_days": sorted(short, key=lambda v: (v["day"], v["symbol"])),
            "top10_days_by_median_F1_rel": top10,
            "per_day": {"%s|%s" % k: v for k, v in sorted(all_days.items())}}


# ---------------------------------------------------------------- population, A1.1

def population_split(v2_runs, v1_runs) -> dict:
    """A1.1: the population is the runs in `gex_run_v2` (stamp v2-1.2-gss) that
    have rows in `gex_strike_snapshots` under the same run_id.

    Both arguments are iterables of {run_id, symbol, day}. Runs present in one
    table and not the other are counted and listed by date, as A1.1 requires.
    """
    v2 = {r["run_id"]: r for r in v2_runs}
    v1 = {r["run_id"]: r for r in v1_runs}
    both = sorted(set(v2) & set(v1))
    only2 = sorted(set(v2) - set(v1))
    only1 = sorted(set(v1) - set(v2))

    def by_date(ids, src):
        out: dict[str, dict[str, int]] = {}
        for rid in ids:
            r = src[rid]
            out.setdefault(r["day"], {}).setdefault(r["symbol"], 0)
            out[r["day"]][r["symbol"]] += 1
        return out

    return {
        "n_v2_runs": len(v2), "n_v1_runs": len(v1),
        "n_both": len(both),
        "n_v2_only": len(only2), "n_v1_only": len(only1),
        "population": both,
        "v2_only_by_date": by_date(only2, v2),
        "v1_only_by_date": by_date(only1, v1),
    }


# ---------------------------------------------------------------- C4, the known day

# The B2 limits, read from the frozen b2_compare.py on origin/main
# (docs/research/pin_proof/v2_check_v12/b2_compare.py:19-21, :51-59) and not
# invented here: counts and open-interest sums EXACT, the sums within
# 1e-9 relative + 1e-9 absolute, the shares and HHI within 1e-9 absolute only,
# and the rule stamp on every row.
B2_EXACT = ("n", "n_map", "n_band", "n_both", "n_call", "n_put",
            "s_oic", "s_oip", "r_n_map", "r_n_zero")
B2_SUMS = (("s_net", 1e-9, 1e-9), ("s_gross", 1e-9, 1e-9),
           ("s_gamma", 1e-9, 1e-9), ("sk_net", 1e-9, 1e-9),
           ("sk_gross", 1e-9, 1e-9), ("r_net_cr", 1e-9, 1e-9),
           ("r_gross_band_cr", 1e-9, 1e-9), ("r_net_top_share", 0.0, 1e-9),
           ("r_gross_top_share", 0.0, 1e-9), ("r_gross_hhi", 0.0, 1e-9))
B2_STAMPS = ("rv_strike", "rv_run")


def b2_close(a, b, rel, ab) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= ab + rel * abs(float(b))


def c4_compare(expected: dict, got: dict) -> dict:
    """STOP: on 2026-08-27 the V2 values this run read must equal the fixture
    within the B2 limits. `expected` and `got` are both {run_id: {field: value}}.

    A fixture run missing from `got` is a failure. A run in `got` that the
    fixture does not hold is listed, not compared -- b2_compare.py's rule.

    For every compared field the fixture holds, a field ABSENT from the database
    row, or present as None, is a failure recorded as "field missing" -- never a
    skip. A check that passes because it read nothing is not a check.
    """
    fails, missing = [], []
    for rid, e in sorted(expected.items()):
        g = got.get(rid)
        if g is None:
            missing.append(rid)
            fails.append((e.get("symbol"), rid, "missing in database", None, None))
            continue
        if g.get("symbol") != e.get("symbol"):
            fails.append((e.get("symbol"), rid, "symbol", g.get("symbol"), e.get("symbol")))
        for k in B2_EXACT:
            if k not in e:
                continue
            if k not in g or g[k] is None:
                fails.append((e.get("symbol"), rid, k, "field missing", e[k]))
            elif float(g[k]) != float(e[k]):
                fails.append((e.get("symbol"), rid, k, g[k], e[k]))
        for k, rel, ab in B2_SUMS:
            if k not in e:
                continue
            if k not in g or g[k] is None:
                fails.append((e.get("symbol"), rid, k, "field missing", e[k]))
            elif not b2_close(g[k], e[k], rel, ab):
                fails.append((e.get("symbol"), rid, k, g[k], e[k]))
        for k in B2_STAMPS:
            # Required on every database row (b2_compare.py :59-61), whether or
            # not the fixture carries it: the fixture does not hold rv_strike or
            # rv_run, and a row that cannot show its stamp is not a match.
            if k not in g or g[k] is None:
                fails.append((e.get("symbol"), rid, k, "field missing", RULE_STAMP))
            elif g[k] != RULE_STAMP:
                fails.append((e.get("symbol"), rid, k, g[k], RULE_STAMP))
    return {
        "n_expected": len(expected),
        "n_compared": len(expected) - len(missing),
        "n_missing": len(missing), "missing": missing,
        "n_fail_runs": len({f[1] for f in fails}),
        "n_fails": len(fails), "fails": fails[:200],
        "extra_in_db": sorted(set(got) - set(expected)),
        "ok": not fails,
    }
