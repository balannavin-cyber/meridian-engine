"""M2: does the futures basis respond to spot the way gamma predicts?
(pre-registration section 4)

Outcome-computing. Runs only with --score, and only if the self-test passes and
all four controls pass -- both re-checked here, not assumed.

Section 4, in the pre-registration's words:
  Sessions   window sessions that are not an option expiry day (the Greeks
             sidecar skips dte 0), not excluded by section 2, with at least 95%
             of spot and series-1 bars present. Others are counted.
  Windows    non-overlapping 5-minute windows starting 09:20, the last ending
             15:00.  -> 69 boundaries, 68 windows per session.
  dS         change in spot close over the window.
  db         change in b = series-1 futures close - spot close over the same
             window.
  Dose g     net / gross gamma at the window's first minute, front expiry
             (nearest expiry_date after the session date):
             g = sum(sign * gamma * OI) / sum(gamma * OI), CE positive, PE
             negative. Unitless, range -1 to +1. The board's own net-over-gross.
  Model      db = a + b0*dS + b1*(g*dS) + e, ordinary least squares.
             Intervals by session-clustered bootstrap, 10,000 resamples, seed
             20261117.
  Test       b1 != 0, TWO-sided, alpha 0.05. Two-sided because P2 left the side
             REGIME-DEPENDENT. The sign found is a mapping FOUND, NOT PREDICTED:
             b1 < 0 reads as dampening where net gamma is positive.
  Stability  the sign of b1 is the same (a) in both half-years (Apr-Sep 2025,
             Oct 2025-Mar 2026) and (b) in at least two of three terciles of
             session realised volatility (from 5-minute spot returns).
  Verdict    significant and both stability conditions met
                 -> MECHANISM OBSERVED (indicative), with the sign
             significant but unstable -> UNSTABLE
             not significant          -> NOT OBSERVED
  Degeneracy if g has one sign on >= 90% of windows, the result carries the
             label "dose nearly one-signed" and the sign reading is not made.

-----------------------------------------------------------------------------
PLACES WHERE SECTION 4 IS AMBIGUOUS, AND THE READING TAKEN
(for the change-of-record list; none of these adds, drops or tunes a threshold)

R1  Window boundaries. "non-overlapping 5-minute windows starting 09:20, the
    last ending 15:00" fixes the grid but not which bar supplies a boundary
    price. Bars are labelled HH:MM:59. READING, operator-confirmed before Part 0:
    boundaries are the bars 09:20:59, 09:25:59, ... 15:00:59; for window k,
    dS and db are close(boundary k+1) - close(boundary k), and g is read at
    boundary k. g is therefore fixed BEFORE the move it scales (Rule 0a).

R2  Significance of b1. Section 4 fixes a two-sided test at alpha 0.05 and
    fixes the interval as a session-clustered bootstrap, but does not say which
    statistic decides the test. READING: significance is the 95% session-
    clustered bootstrap interval EXCLUDING ZERO. A bootstrap two-sided p-value
    (twice the smaller tail mass about zero) is reported BESIDE it as a
    cross-check, never as the deciding number.

R3  "the sign of b1 is the same ... in both half-years". Same as each other, or
    same as the pooled sign? READING: condition (a) is sign(b1_H1) ==
    sign(b1_H2). Condition (b) is "at least two of three terciles" matching the
    POOLED sign, since the pre-registration counts terciles against one sign.
    All five b1 values (pooled, two half-years, three terciles) are printed, so
    either reading can be checked against the output.

R4  Session realised volatility, for the terciles. "from 5-minute spot returns"
    does not fix the estimator. READING: the sample standard deviation of the
    68 five-minute LOG returns of spot close across the session's boundaries.
    The three tercile cut points are printed.

R5  Series-1 price at a window boundary. The operator's instruction named
    series_close(fut[d][1]); that accessor returns ONE value per session --
    section 2's close -- and cannot supply 69 boundary prices. READING: the same
    series-1 bar list fut[d][1], indexed by minute label. Series 1 only;
    futures_total_oi (the 1+2+3 total that M1 uses) is not called here.

R6  The 95% bar-presence denominator. Section 4 says "at least 95% of spot and
    series-1 bars present" without stating the denominator. READING: the 375
    minutes 09:15:59..15:29:59, measured in Part 0, so the threshold is
    ceil(0.95 * 375) = 357 bars in each series.
-----------------------------------------------------------------------------

Nothing here reads futures data after 2026-03-30 (section 8: the Stage 1 holdout
stays sealed). No clock conversion is made between tables: all four carry the
vendor clock (IST written as UTC, :59 seconds).
"""
import argparse
import csv
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import futoi_lib as L
import futoi_stats as S
from futoi_controls import load_session_chain, dose_g

ALPHA = 0.05
PRESENCE = 0.95
HALF1 = ("2025-04-01", "2025-09-30")
HALF2 = ("2025-10-01", "2026-03-30")
DEGENERACY = 0.90


# ----------------------------------------------------------------- model
def beta1_of(rows):
    """b1 from db = a + b0*dS + b1*(g*dS) + e on `rows` of (dS, g*dS, db)."""
    if len(rows) < 4:
        return None
    X = np.array([[r[0], r[1]] for r in rows], dtype=float)
    y = np.array([r[2] for r in rows], dtype=float)
    if np.allclose(X[:, 1], X[0, 1]) or np.allclose(X[:, 0], X[0, 0]):
        return None
    try:
        return float(S.ols(X, y)[2])
    except np.linalg.LinAlgError:
        return None


def fit(rows):
    """-> (a, b0, b1) or None."""
    if len(rows) < 4:
        return None
    X = np.array([[r[0], r[1]] for r in rows], dtype=float)
    y = np.array([r[2] for r in rows], dtype=float)
    try:
        b = S.ols(X, y)
    except np.linalg.LinAlgError:
        return None
    return float(b[0]), float(b[1]), float(b[2])


# ----------------------------------------------------------------- build
def build(fut, spot, A, sessions):
    bounds = L.window_boundaries()                    # 69
    minutes = L.session_minutes()                     # 375
    need = math.ceil(PRESENCE * len(minutes))         # 357

    fut_expiries, _ = L.futures_expiry_dates(fut, sessions)
    excluded = L.excluded_by_s2(fut_expiries, sessions)
    opt_expiry_days = {d for (d, _), a in A.items() if a["exp_on_or_after"] == d}

    kept, dropped = [], []
    for d in sessions:
        why = []
        if not (L.WINDOW_LO <= d <= L.WINDOW_HI):
            why.append("outside the window")
        if d in opt_expiry_days:
            why.append("option expiry day (section 4; the sidecar skips dte 0)")
        if d in excluded:
            why.append(excluded[d])
        sp = spot.get(d, {})
        f1 = {h: c for h, c, _, _ in fut.get(d, {}).get(1, [])}
        n_sp = sum(1 for m in minutes if m in sp and sp[m])
        n_f1 = sum(1 for m in minutes if m in f1 and f1[m])
        if n_sp < need:
            why.append("spot bars %d/%d < 95%% (%d needed)" % (n_sp, len(minutes), need))
        if n_f1 < need:
            why.append("series-1 bars %d/%d < 95%% (%d needed)" % (n_f1, len(minutes), need))
        if why:
            dropped.append({"trade_date": d, "spot_bars": n_sp, "fut_s1_bars": n_f1,
                            "reasons": "; ".join(why)})
        else:
            kept.append(d)

    rows, skipped = [], {}

    def skip(reason):
        skipped[reason] = skipped.get(reason, 0) + 1

    per_session = {}
    for d in kept:
        sp = spot[d]
        f1 = {h: c for h, c, _, _ in fut[d][1]}       # R5: series 1 only, by minute
        srows = []
        for k in range(len(bounds) - 1):
            t0, t1 = bounds[k], bounds[k + 1]
            s0, s1 = sp.get(t0), sp.get(t1)
            p0, p1 = f1.get(t0), f1.get(t1)
            if s0 is None or s1 is None:
                skip("missing spot close at a boundary")
                continue
            if p0 is None or p1 is None:
                skip("missing series-1 futures close at a boundary")
                continue
            a = A.get((d, t0))
            if a is None:
                skip("no chain row at the window's first minute")
                continue
            if a["legs_solved"] == 0:
                skip("no leg with a solved gamma at the window's first minute")
                continue
            if a["gross"] in (None, 0.0):
                skip("gross gamma*OI is zero or null at the window's first minute")
                continue
            g = dose_g(a)
            if g is None:
                skip("dose g not computable")
                continue
            dS = s1 - s0
            db = (p1 - s1) - (p0 - s0)
            srows.append({"trade_date": d, "win_start": t0, "win_end": t1,
                          "expiry": a["expiry"], "spot_0": s0, "spot_1": s1,
                          "fut_0": p0, "fut_1": p1, "b_0": p0 - s0, "b_1": p1 - s1,
                          "dS": dS, "db": db, "g": g, "gxdS": g * dS,
                          "legs": a["legs"], "legs_solved": a["legs_solved"]})
        if srows:
            per_session[d] = srows
            rows.extend(srows)

    # R4: session realised volatility from 5-minute log spot returns
    rv = {}
    for d, srows in per_session.items():
        r = [math.log(x["spot_1"] / x["spot_0"]) for x in srows
             if x["spot_0"] and x["spot_1"] and x["spot_0"] > 0 and x["spot_1"] > 0]
        if len(r) >= 2:
            m = sum(r) / len(r)
            rv[d] = math.sqrt(sum((v - m) ** 2 for v in r) / (len(r) - 1))
    return {"bounds": bounds, "minutes": minutes, "need": need, "kept": kept,
            "dropped": dropped, "rows": rows, "skipped": skipped,
            "per_session": per_session, "rv": rv,
            "fut_expiries": fut_expiries, "excluded": excluded,
            "opt_expiry_days": opt_expiry_days}


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", action="store_true",
                    help="compute section 4 outcomes; refused unless the "
                         "self-test and all four controls pass")
    args = ap.parse_args()

    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "STOPPED.md")):
        print("REFUSING: STOPPED.md is present -- a control failed.")
        return 2

    fut = L.load_futures()
    spot = L.load_spot()
    A, _B = load_session_chain()
    sessions = sorted(d for d in fut.keys() if L.WINDOW_LO <= d <= L.WINDOW_HI)

    if not args.score:
        print("M2: --score not given. Nothing in section 4 computed.")
        print("Sessions available in the window: %d" % len(sessions))
        return 0

    import futoi_selftest
    if futoi_selftest.main() != 0:
        print("REFUSING to score: self-test failed.")
        return 4
    cpath = os.path.join(L.DATA, "controls.csv")
    if not os.path.exists(cpath):
        print("REFUSING to score: controls have not been run.")
        return 5
    with open(cpath, newline="") as fh:
        ctrl = list(csv.DictReader(fh))
    bad = [r["id"] for r in ctrl if r["passed"] != "True"]
    if bad or len(ctrl) != 4:
        print("REFUSING to score: controls not all passing (%d rows, failing %s)."
              % (len(ctrl), bad))
        return 6

    ctx = build(fut, spot, A, sessions)
    rows = ctx["rows"]

    print("=" * 96)
    print("M2 -- does the futures basis respond to spot the way gamma predicts? (section 4)")
    print("=" * 96)
    print("\n--- sessions")
    print("sessions in the window:                       %d" % len(sessions))
    print("option expiry days:                           %d" % len(ctx["opt_expiry_days"]))
    print("futures expiry days (section 2):              %d" % len(ctx["fut_expiries"]))
    print("sessions excluded by section 2:               %d" % len(ctx["excluded"]))
    print("bar-presence threshold:                       %d of %d minutes (95%%)"
          % (ctx["need"], len(ctx["minutes"])))
    print("SESSIONS KEPT:                                %d" % len(ctx["kept"]))
    print("sessions dropped, with reason:                %d" % len(ctx["dropped"]))
    byreason = {}
    for r in ctx["dropped"]:
        byreason[r["reasons"]] = byreason.get(r["reasons"], 0) + 1
    for k in sorted(byreason, key=lambda x: -byreason[x]):
        print("   %4d  %s" % (byreason[k], k))
    print("sessions that produced at least one window:   %d" % len(ctx["per_session"]))

    print("\n--- windows")
    print("windows per session by construction:          %d" % (len(ctx["bounds"]) - 1))
    print("windows possible over kept sessions:          %d"
          % (len(ctx["kept"]) * (len(ctx["bounds"]) - 1)))
    print("WINDOWS USED:                                 %d" % len(rows))
    tot_skip = sum(ctx["skipped"].values())
    print("windows with no usable row:                   %d" % tot_skip)
    for k in sorted(ctx["skipped"], key=lambda x: -ctx["skipped"][x]):
        print("   %6d  %s" % (ctx["skipped"][k], k))

    if len(rows) < 4:
        print("\nTOO FEW WINDOWS -- M2 verdict: NOT OBSERVED (no sample).")
        return 0

    # --- distribution of g
    gs = sorted(r["g"] for r in rows)
    pos = sum(1 for g in gs if g > 0)
    neg = sum(1 for g in gs if g < 0)
    zer = sum(1 for g in gs if g == 0)
    print("\n--- distribution of the dose g (unitless, -1..+1)")
    print("n windows: %d   positive %d (%.1f%%)   negative %d (%.1f%%)   zero %d"
          % (len(gs), pos, 100.0 * pos / len(gs), neg, 100.0 * neg / len(gs), zer))
    print("deciles:")
    for q in range(0, 101, 10):
        print("   p%-3d  %+.6f" % (q, S._pct(gs, q)))
    one_signed = max(pos, neg) / len(gs)
    degenerate = one_signed >= DEGENERACY
    print("largest one-sided share:                      %.1f%%  (gate >= %.0f%%)"
          % (100.0 * one_signed, 100.0 * DEGENERACY))
    print("degeneracy gate:                              %s"
          % ("TRIPPED -- dose nearly one-signed" if degenerate else "not tripped"))

    # --- pooled fit
    flat = [(r["dS"], r["gxdS"], r["db"]) for r in rows]
    pooled = fit(flat)
    print("\n--- model: db = a + b0*dS + b1*(g*dS) + e   (OLS)")
    print("units: dS and db in NIFTY index points; g unitless, so b0 and b1 are")
    print("       index points of basis change per index point of spot change.")
    print("a   (intercept) %+.8f  index points" % pooled[0])
    print("b0              %+.8f  (per index point of dS)" % pooled[1])
    print("b1              %+.8f  (per index point of g*dS)" % pooled[2])

    clusters = {d: [(r["dS"], r["gxdS"], r["db"]) for r in ctx["per_session"][d]]
                for d in ctx["per_session"]}
    bs = S.boot_cluster(clusters, beta1_of)
    print("\n--- interval for b1")
    print("method: %s, %d resamples, seed %d, clusters = SESSIONS"
          % (bs["method"], S.B_RESAMPLES, S.SEED))
    print("clusters: %d    usable resamples: %d" % (bs["clusters"], bs["resamples"]))
    print("b1 point %+.8f   95%% CI [%+.8f, %+.8f]" % (bs["point"], bs["lo"], bs["hi"]))

    # R2: the test is the 95% CI excluding zero; a bootstrap p is a cross-check
    excl0 = (bs["lo"] > 0 and bs["hi"] > 0) or (bs["lo"] < 0 and bs["hi"] < 0)
    print("\n--- Test: b1 != 0, TWO-sided, alpha 0.05")
    print("deciding statistic: the 95%% session-clustered bootstrap CI excludes 0")
    print("CI excludes zero:                             %s" % excl0)
    significant = excl0

    # --- stability
    print("\n--- stability condition (a): both half-years")
    halves = {}
    for nm, (lo, hi) in (("Apr-Sep 2025", HALF1), ("Oct 2025-Mar 2026", HALF2)):
        sub = [(r["dS"], r["gxdS"], r["db"]) for r in rows if lo <= r["trade_date"] <= hi]
        nsess = len({r["trade_date"] for r in rows if lo <= r["trade_date"] <= hi})
        f = fit(sub)
        halves[nm] = f[2] if f else None
        print("   %-20s %s..%s  sessions %3d  windows %6d  b1 %s"
              % (nm, lo, hi, nsess, len(sub),
                 ("%+.8f" % f[2]) if f else "not estimable"))
    hv = [v for v in halves.values() if v is not None]
    cond_a = len(hv) == 2 and (hv[0] > 0) == (hv[1] > 0)
    print("   signs agree between the two half-years:    %s" % cond_a)

    print("\n--- stability condition (b): terciles of session realised volatility")
    rv = ctx["rv"]
    vals = sorted(rv.values())
    c1, c2 = S._pct(vals, 100.0 / 3), S._pct(vals, 200.0 / 3)
    print("   estimator: sample sd of the 68 five-minute LOG spot returns (R4)")
    print("   tercile cut points: p33.3 = %.8f   p66.7 = %.8f  (log return sd)"
          % (c1, c2))
    terc = {}
    for nm, pred in (("T1 low vol", lambda v: v <= c1),
                     ("T2 mid vol", lambda v: c1 < v <= c2),
                     ("T3 high vol", lambda v: v > c2)):
        ds = {d for d in rv if pred(rv[d])}
        sub = [(r["dS"], r["gxdS"], r["db"]) for r in rows if r["trade_date"] in ds]
        f = fit(sub)
        terc[nm] = f[2] if f else None
        print("   %-12s sessions %3d  windows %6d  b1 %s"
              % (nm, len(ds), len(sub), ("%+.8f" % f[2]) if f else "not estimable"))
    pooled_sign = pooled[2] > 0
    matching = sum(1 for v in terc.values() if v is not None and (v > 0) == pooled_sign)
    cond_b = matching >= 2
    print("   terciles whose b1 sign matches the pooled sign: %d of 3" % matching)
    print("   at least two of three:                     %s" % cond_b)

    # --- verdict, in the pre-registration's words
    if significant and cond_a and cond_b:
        verdict = "MECHANISM OBSERVED (indicative)"
    elif significant:
        verdict = "UNSTABLE"
    else:
        verdict = "NOT OBSERVED"
    print("\n" + "=" * 96)
    if degenerate:
        print("M2 VERDICT: %s   [dose nearly one-signed]" % verdict)
        print("  the sign reading is NOT made (section 4 degeneracy gate).")
    else:
        sign_txt = ""
        if verdict == "MECHANISM OBSERVED (indicative)":
            sign_txt = ("   sign: b1 %s 0 -- %s where net gamma is positive"
                        % ("<" if pooled[2] < 0 else ">",
                           "dampening" if pooled[2] < 0 else "amplifying"))
            print("  the sign is a mapping FOUND, NOT PREDICTED (section 4).")
        print("M2 VERDICT: %s%s" % (verdict, sign_txt))
    print("=" * 96)

    # --- artefacts
    with open(os.path.join(L.DATA, "m2_windows.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open(os.path.join(L.DATA, "m2_sessions.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["trade_date", "windows", "realised_vol_5m_logret_sd",
                    "mean_g", "mean_dS", "mean_db", "b1_session_only"])
        for d in sorted(ctx["per_session"]):
            sr = ctx["per_session"][d]
            f = fit([(r["dS"], r["gxdS"], r["db"]) for r in sr])
            w.writerow([d, len(sr), rv.get(d, ""),
                        S.median([r["g"] for r in sr]),
                        S.median([r["dS"] for r in sr]),
                        S.median([r["db"] for r in sr]),
                        f[2] if f else ""])
    with open(os.path.join(L.DATA, "m2_excluded_sessions.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["trade_date", "spot_bars", "fut_s1_bars", "reasons"])
        w.writeheader()
        for r in ctx["dropped"]:
            w.writerow(r)
    with open(os.path.join(L.DATA, "m2_summary.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["key", "value"])
        w.writerow(["n_sessions_window", len(sessions)])
        w.writerow(["n_sessions_kept", len(ctx["kept"])])
        w.writerow(["n_sessions_dropped", len(ctx["dropped"])])
        w.writerow(["n_windows_used", len(rows)])
        w.writerow(["n_windows_skipped", tot_skip])
        for k, v in sorted(ctx["skipped"].items()):
            w.writerow(["skipped::" + k, v])
        w.writerow(["g_share_positive", pos / len(gs)])
        w.writerow(["g_share_negative", neg / len(gs)])
        w.writerow(["g_largest_one_sided_share", one_signed])
        w.writerow(["degeneracy_tripped", degenerate])
        w.writerow(["a", pooled[0]])
        w.writerow(["b0", pooled[1]])
        w.writerow(["b1", pooled[2]])
        w.writerow(["b1_ci_lo", bs["lo"]])
        w.writerow(["b1_ci_hi", bs["hi"]])
        w.writerow(["b1_ci_method", bs["method"]])
        w.writerow(["b1_resamples", bs["resamples"]])
        w.writerow(["significant_ci_excludes_zero", significant])
        for nm, v in halves.items():
            w.writerow(["b1_half::" + nm, v])
        w.writerow(["stability_a_halfyear_signs_agree", cond_a])
        w.writerow(["tercile_cut_p33", c1])
        w.writerow(["tercile_cut_p67", c2])
        for nm, v in terc.items():
            w.writerow(["b1_tercile::" + nm, v])
        w.writerow(["stability_b_terciles_matching", matching])
        w.writerow(["stability_b_met", cond_b])
        w.writerow(["verdict", verdict])
    print("\nwrote data/m2_windows.csv, data/m2_sessions.csv,")
    print("      data/m2_excluded_sessions.csv, data/m2_summary.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
