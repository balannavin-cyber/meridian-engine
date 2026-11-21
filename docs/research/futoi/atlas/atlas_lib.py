"""Atlas exploration library (2026-11-18). READ-ONLY.

EXPLORATION, not a test. Nothing here produces a verdict, and no number is
compared with a threshold to decide anything.

Window 2025-04-01 .. 2026-03-30, NIFTY only. Vendor clock as-is (:59 stamps),
no conversion between tables. The 15:30 bar is never used.

Series:
  P   series-1 futures close          PH / PL  its high / low
  S   spot close                      SH / SL  its high / low
  F   futures OI, series 1+2+3, None if any series is missing at that minute
  F1  series-1 OI alone

Reads, all read-only:
  ../data/futures_bars.csv   (closed run) all three series, close/oi/volume
  ../data/spot_bars.csv      (closed run) spot closes
  ../data/futures_expiry_list.csv (closed run) the 12 futures expiry dates
  ../data/session_chain.csv  (closed run) per-strike OI at each session close
  ../data/m2_windows.csv     (closed run) g per 5-minute window
  data/fut_bars_hl.csv, data/spot_bars_hl.csv   this run's high/low pull
"""
import csv
import math
import os
import random

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CLOSED = os.path.join(os.path.dirname(HERE), "data")   # the closed run's data/
DATA = os.path.join(HERE, "data")

WINDOW_LO, WINDOW_HI = "2025-04-01", "2026-03-30"
OPEN_MIN = 9 * 60 + 15          # 09:15
CLOSE_MIN = 15 * 60 + 29        # 15:29  (the 15:30 bar is never used)
SEED = 20261118
B_RESAMPLES = 2000


def lbl(m):
    """minute-of-day -> vendor bar label HH:MM:59"""
    return "%02d:%02d:59" % (m // 60, m % 60)


def _f(x):
    return None if x in (None, "") else float(x)


def guard(rows, col, name):
    """Date guard: nothing after the window end (Stage 1 holdout sealed)."""
    bad = [r[col] for r in rows if r[col] > WINDOW_HI]
    if bad:
        raise SystemExit("%s contains %s, after the window end %s" % (name, max(bad), WINDOW_HI))
    return max(r[col] for r in rows) if rows else None


# ----------------------------------------------------------------- loaders
def load_all():
    d = {}
    # --- high/low bars pulled by this run
    for which, key in (("fut", "P"), ("spot", "S")):
        path = os.path.join(DATA, "%s_bars_hl.csv" % which)
        with open(path, newline="") as fh:
            rows = list(csv.DictReader(fh))
        guard(rows, "trade_date", path)
        close, high, low = {}, {}, {}
        for r in rows:
            t = r["trade_date"]
            m = int(r["hhmmss"][:2]) * 60 + int(r["hhmmss"][3:5])
            close.setdefault(t, {})[m] = _f(r["close"])
            high.setdefault(t, {})[m] = _f(r["high"])
            low.setdefault(t, {})[m] = _f(r["low"])
        d[key] = close
        d[key + "H"] = high
        d[key + "L"] = low
    # --- all three futures series, for F
    path = os.path.join(CLOSED, "futures_bars.csv")
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    guard(rows, "trade_date", path)
    per = {}
    for r in rows:
        t = r["trade_date"]
        m = int(r["hhmmss"][:2]) * 60 + int(r["hhmmss"][3:5])
        per.setdefault(t, {}).setdefault(m, {})[int(r["contract_series"])] = _f(r["oi"])
    F, F1 = {}, {}
    for t, bymin in per.items():
        for m, s in bymin.items():
            if 1 in s and s[1] is not None:
                F1.setdefault(t, {})[m] = s[1]
            if all(k in s and s[k] is not None for k in (1, 2, 3)):
                F.setdefault(t, {})[m] = s[1] + s[2] + s[3]
    d["F"], d["F1"] = F, F1
    d["sessions"] = sorted(d["P"].keys())
    # --- futures expiry dates (the 12 of the M1/M2 run)
    with open(os.path.join(CLOSED, "futures_expiry_list.csv"), newline="") as fh:
        d["fut_expiries"] = [r["date"] for r in csv.DictReader(fh)]
    # --- sessions excluded by the M1/M2 run's section 2 (FLAGGED here, not dropped)
    idx = {s: i for i, s in enumerate(d["sessions"])}
    flag = {}
    for e in d["fut_expiries"]:
        if e in idx:
            flag[e] = "futures expiry"
            if idx[e] + 1 < len(d["sessions"]):
                flag.setdefault(d["sessions"][idx[e] + 1], "session after a futures expiry")
    d["expiry_flag"] = flag
    return d


def load_g():
    """g per 5-minute window start, from the closed run's m2_windows.csv."""
    g = {}
    path = os.path.join(CLOSED, "m2_windows.csv")
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            m = int(r["win_start"][:2]) * 60 + int(r["win_start"][3:5])
            g.setdefault(r["trade_date"], {})[m] = float(r["g"])
    return g


def load_chain_close():
    """Per-strike OI at each session close, front expiry, from session_chain.csv
    tag B. For session d the walls use the PRIOR session's close and the expiry
    nearest to d; tag B's expiry is min(expiry > d-1), which for dates is the
    same set as min(expiry >= d)."""
    out = {}
    with open(os.path.join(CLOSED, "session_chain.csv"), newline="") as fh:
        for r in csv.DictReader(fh):
            if r["tag"] != "B":
                continue
            out.setdefault(r["trade_date"], []).append(
                {"expiry": r["expiry"], "strike": _f(r["strike"]),
                 "option_type": r["option_type"], "oi": _f(r["oi"]),
                 "hhmmss": r["hhmmss"]})
    return out


# ----------------------------------------------------------------- windows
def boundaries(step):
    """Non-overlapping windows of `step` minutes from 09:15. Only FULL windows
    on the grid are used; the ragged 15:15->15:29 tail is left out and counted.
    Returns the boundary minutes."""
    out = []
    m = OPEN_MIN
    while m <= CLOSE_MIN:
        out.append(m)
        m += step
    return out


def series_at(series, d, m):
    return series.get(d, {}).get(m)


def ret_bp(a, b):
    """(b - a) / a in basis points."""
    if a in (None, 0) or b is None:
        return None
    return 1e4 * (b - a) / a


def fwd_range_bp(H, L, d, m0, m1, ref):
    """(max high - min low) / ref in bp over minutes (m0, m1]."""
    hs = [v for m, v in H.get(d, {}).items() if m0 < m <= m1 and v is not None]
    ls = [v for m, v in L.get(d, {}).items() if m0 < m <= m1 and v is not None]
    if not hs or not ls or not ref:
        return None
    return 1e4 * (max(hs) - min(ls)) / ref


def classify(dP, dOI):
    """LB (+,+) long build-up; SC (+,-) short covering; SB (-,+) short build-up;
    LU (-,-) long unwinding.

    FLAT and MISSING are DIFFERENT and are never merged:
      FLAT     a measured change of exactly zero in dP or dOI
      MISSING  dP or dOI could not be computed (a bar or an OI leg is absent;
               F is None whenever any of series 1/2/3 is missing at that minute)
    Merging them would let a missing F be counted as a measured class. Both are
    reported in every class table (READINGS R10)."""
    if dP is None or dOI is None:
        return "MISSING"
    if dP == 0 or dOI == 0:
        return "FLAT"
    if dP > 0:
        return "LB" if dOI > 0 else "SC"
    return "SB" if dOI > 0 else "LU"


CLASSES = ["LB", "SC", "SB", "LU", "FLAT", "MISSING"]
REAL_CLASSES = ["LB", "SC", "SB", "LU"]


def tod(m):
    """Time-of-day bucket from the window's END minute."""
    if m <= 11 * 60 + 30:
        return "to 11:30"
    if m <= 13 * 60 + 30:
        return "11:30-13:30"
    return "after 13:30"


TOD = ["to 11:30", "11:30-13:30", "after 13:30", "all day"]


# ----------------------------------------------------------------- bootstrap
def boot_mean(rows, key, n=B_RESAMPLES, seed=SEED, alpha=0.05):
    """Session-clustered percentile bootstrap of a MEAN.

    Whole sessions are resampled with replacement. Implemented on per-session
    (sum, count) so a resample is an O(n_sessions) operation; the result is the
    same as resampling the rows of the selected sessions. Intervals are
    DESCRIPTIVE.

    Medians are reported as point estimates WITHOUT an interval -- the
    sum/count shortcut does not apply to them (READINGS R9)."""
    per = {}
    for r in rows:
        v = r.get(key)
        if v is None:
            continue
        s, c = per.get(r["trade_date"], (0.0, 0))
        per[r["trade_date"]] = (s + v, c + 1)
    if not per:
        return {"n": 0, "n_sessions": 0, "mean": float("nan"), "median": float("nan"),
                "lo": float("nan"), "hi": float("nan")}
    keys = list(per)
    sums = np.array([per[k][0] for k in keys], dtype=float)
    cnts = np.array([per[k][1] for k in keys], dtype=float)
    vals = [r[key] for r in rows if r.get(key) is not None]
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(keys), size=(n, len(keys)))
    num = sums[idx].sum(axis=1)
    den = cnts[idx].sum(axis=1)
    reps = np.divide(num, den, out=np.full(n, np.nan), where=den > 0)
    reps = reps[~np.isnan(reps)]
    reps.sort()
    return {"n": int(cnts.sum()), "n_sessions": len(keys),
            "mean": float(sums.sum() / cnts.sum()),
            "median": float(np.median(vals)),
            "lo": float(np.percentile(reps, 100 * alpha / 2)) if len(reps) else float("nan"),
            "hi": float(np.percentile(reps, 100 * (1 - alpha / 2))) if len(reps) else float("nan")}


def boot_diff(rows_a, rows_b, key, n=B_RESAMPLES, seed=SEED, alpha=0.05):
    """Session-clustered percentile bootstrap of the DIFFERENCE of two means,
    mean(a) - mean(b).

    For an outcome with no meaningful zero -- a forward range, a hit rate, a
    break rate, a maximum excursion -- a raw level's interval cannot exclude
    zero in any informative way, because the quantity is bounded away from zero
    by construction. Only a contrast against the complement condition is an
    effect. Sessions are the clusters and are resampled ONCE per replicate, so
    the two groups move together and a session contributing to both is handled
    correctly."""
    per = {}
    for rows, i in ((rows_a, 0), (rows_b, 2)):
        for r in rows:
            v = r.get(key)
            if v is None:
                continue
            e = per.setdefault(r["trade_date"], [0.0, 0, 0.0, 0])
            e[i] += v
            e[i + 1] += 1
    nan = float("nan")
    keys = list(per)
    if not keys:
        return {"n": 0, "n_b": 0, "n_sessions": 0, "mean": nan, "median": nan,
                "lo": nan, "hi": nan, "level_a": nan, "level_b": nan}
    A = np.array([per[k] for k in keys], dtype=float)
    sa, ca, sb, cb = A[:, 0].sum(), A[:, 1].sum(), A[:, 2].sum(), A[:, 3].sum()
    if ca == 0 or cb == 0:
        return {"n": int(ca), "n_b": int(cb),
                "n_sessions": int((A[:, 1] > 0).sum()), "mean": nan, "median": nan,
                "lo": nan, "hi": nan,
                "level_a": (sa / ca) if ca else nan, "level_b": (sb / cb) if cb else nan}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(keys), size=(n, len(keys)))
    qa, na = A[:, 0][idx].sum(axis=1), A[:, 1][idx].sum(axis=1)
    qb, nb = A[:, 2][idx].sum(axis=1), A[:, 3][idx].sum(axis=1)
    ok = (na > 0) & (nb > 0)
    reps = np.full(n, np.nan)
    reps[ok] = qa[ok] / na[ok] - qb[ok] / nb[ok]
    reps = reps[~np.isnan(reps)]
    reps.sort()
    return {"n": int(ca), "n_b": int(cb), "n_sessions": int((A[:, 1] > 0).sum()),
            "mean": float(sa / ca - sb / cb), "median": nan,
            "lo": float(np.percentile(reps, 100 * alpha / 2)) if len(reps) else nan,
            "hi": float(np.percentile(reps, 100 * (1 - alpha / 2))) if len(reps) else nan,
            "level_a": float(sa / ca), "level_b": float(sb / cb)}


# Outcomes with no meaningful zero: only a contrast against the complement is an
# effect. A raw level for one of these is printed as "level, not an effect", is
# never tested against zero, and never enters the shortlist.
UNSIGNED = {"rng60", "rngclose", "rngnext", "break_rate", "max_excursion_pct",
            "hit30", "hit60", "hitclose", "hitnext"}


def is_unsigned(outcome):
    return outcome in UNSIGNED


def excludes_zero(c):
    return (not math.isnan(c["lo"]) and not math.isnan(c["hi"])
            and ((c["lo"] > 0 and c["hi"] > 0) or (c["lo"] < 0 and c["hi"] < 0)))


def rank_biserial(a, b):
    """Rank-biserial effect size for 'does this separate group a from group b':
    2*AUC - 1, computed from the Mann-Whitney U. +1 = a always above b, -1 = the
    reverse, 0 = no separation. Ties get half credit."""
    a = [x for x in a if x is not None and not (isinstance(x, float) and math.isnan(x))]
    b = [x for x in b if x is not None and not (isinstance(x, float) and math.isnan(x))]
    if not a or not b:
        return float("nan")
    allv = np.array(a + b, dtype=float)
    order = allv.argsort()
    ranks = np.empty(len(allv), dtype=float)
    ranks[order] = np.arange(1, len(allv) + 1)
    # midranks for ties
    sv = allv[order]
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + j + 2) / 2.0
        i = j + 1
    na, nb = len(a), len(b)
    ra = ranks[:na].sum()
    u = ra - na * (na + 1) / 2.0
    return 2.0 * (u / (na * nb)) - 1.0


def spearman(x, y):
    """Spearman rho via midranks. Descriptive; no p-value is reported."""
    pairs = [(a, b) for a, b in zip(x, y)
             if a is not None and b is not None
             and not (isinstance(a, float) and math.isnan(a))
             and not (isinstance(b, float) and math.isnan(b))]
    if len(pairs) < 3:
        return float("nan")

    def rk(v):
        v = np.asarray(v, dtype=float)
        order = v.argsort()
        r = np.empty(len(v), dtype=float)
        r[order] = np.arange(1, len(v) + 1)
        sv = v[order]
        i = 0
        while i < len(sv):
            j = i
            while j + 1 < len(sv) and sv[j + 1] == sv[i]:
                j += 1
            if j > i:
                r[order[i:j + 1]] = (i + j + 2) / 2.0
            i = j + 1
        return r
    rx, ry = rk([p[0] for p in pairs]), rk([p[1] for p in pairs])
    rx = rx - rx.mean()
    ry = ry - ry.mean()
    den = math.sqrt(float((rx * rx).sum()) * float((ry * ry).sum()))
    return float((rx * ry).sum()) / den if den else float("nan")


def quantile_cuts(vals, k):
    v = sorted(x for x in vals if x is not None and not (isinstance(x, float) and math.isnan(x)))
    return [np.percentile(v, 100.0 * i / k) for i in range(1, k)] if v else []


def bucket(v, cuts):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    for i, c in enumerate(cuts):
        if v <= c:
            return i
    return len(cuts)
