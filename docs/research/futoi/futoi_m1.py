"""M1: hedge ratio at weekly expiry (pre-registration section 3).

Outcome-computing. Runs only with --score, and only if the self-test passes and
all four controls pass -- both are re-checked here, not assumed.

Section 3, verbatim in structure:
  Event     an option expiry_date E in the window on which no NIFTY futures
            contract expires, with chain rows and a solved iv at the close of
            the prior session E-1. An event without them is ineligible, counted.
  F(d)      total futures OI, series 1+2+3, at the close of session d.
  G(E)      sum over strikes of |delta| * OI for the series expiring on E, calls
            and puts, at the close of E-1.  N(E) = |sum delta * OI| beside it.
  d(E)      [ln F(E) - ln F(E-1)] - median of the same one-day change over the
            other eligible sessions in the same calendar week.
  Test 1    Wilcoxon signed-rank on d(E), one-sided, H: median < 0, alpha 0.05.
  Test 2    Spearman rho between -[dF(E) - week median dF] -- the abnormal fall
            in QUANTITY, not in logs -- and G(E), one-sided, H: rho > 0, 0.05.
  Test 3    ESTIMATE, NO VERDICT. h-hat = median of abnormal fall / G(E), with a
            bootstrap 95% interval over events (10,000 resamples, seed
            20261117). Also against N(E).
  Verdict   both tests met -> HEDGE FOOTPRINT PRESENT
            Test 1 only    -> EXPIRY EFFECT, NOT DOSE-SCALED
            otherwise      -> NOT DETECTED
            fewer than 20 eligible events -> UNDERPOWERED beside the verdict.

Method notes, none of them a change to section 3:
  * calendar week = ISO week (Monday-Sunday).
  * eligible session, for the week median = an in-window session that is not
    excluded by section 2, is not an option expiry day, and has both F(d) and
    F(previous session). Stated because section 3 says "other eligible sessions"
    without restating the eligibility.
  * delta from the stored iv, spot, strike, r_used, T = exact time to 15:30 IST
    on the expiry date / 365. Vendor delta is not used -- measured 0 of 433
    populated for this era, so it does not exist (Part 0 step 2).
  * only strikes with a solved gamma/iv enter G(E) and N(E); the solved share is
    reported per event.
  * interval method: percentile bootstrap. Resampling is over EVENTS.
"""
import argparse
import csv
import datetime as dt
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import futoi_lib as L
import futoi_stats as S
from futoi_controls import load_session_chain, _years_to_expiry

ALPHA = 0.05
HERE = os.path.dirname(os.path.abspath(__file__))


def iso_week(d):
    y, w, _ = dt.date.fromisoformat(d).isocalendar()
    return "%04d-W%02d" % (y, w)


def build(fut, spot, A, B, sessions):
    idx = {d: i for i, d in enumerate(sessions)}
    fut_expiries, _ = L.futures_expiry_dates(fut, sessions)
    excluded = L.excluded_by_s2(fut_expiries, sessions)
    opt_expiry_days = {d for (d, _), a in A.items() if a["exp_on_or_after"] == d}

    F = {}
    missing_series = {}
    for d in sessions:
        f, per, missing = L.futures_total_oi(fut, d)
        F[d] = {"F": f, "per": per, "missing": missing}
        if missing:
            missing_series[d] = missing

    # one-day changes, log and quantity
    chg = {}
    for i, d in enumerate(sessions):
        if i == 0:
            continue
        p = sessions[i - 1]
        if F[d]["F"] and F[p]["F"]:
            chg[d] = {"prev": p,
                      "dlog": math.log(F[d]["F"]) - math.log(F[p]["F"]),
                      "dqty": F[d]["F"] - F[p]["F"]}

    def eligible_for_week_median(d):
        return (d in chg and d not in excluded and d not in opt_expiry_days)

    by_week = {}
    for d in sessions:
        if eligible_for_week_median(d):
            by_week.setdefault(iso_week(d), []).append(d)

    events, ineligible = [], []
    for E in sorted(opt_expiry_days):
        why = []
        if E in excluded:
            why.append(excluded[E])
        if E not in chg:
            why.append("no one-day futures change at E (missing F(E) or F(E-1))")
        i = idx[E]
        Em1 = sessions[i - 1] if i > 0 else None
        if Em1 is None:
            why.append("no prior session in the window")
        rows = [r for r in B.get(Em1, []) if r["expiry"] == E] if Em1 else []
        if Em1 is not None and not rows:
            why.append("no chain rows for the expiring series at the close of E-1")
        solved = [r for r in rows if r["iv"] and r["oi"] and r["strike"]]
        if rows and not solved:
            why.append("no solved iv at the close of E-1")
        s_em1 = spot.get(Em1, {}).get(L.SESSION_CLOSE) if Em1 else None
        if Em1 is not None and s_em1 is None:
            why.append("no spot close at E-1")
        if why:
            ineligible.append({"expiry": E, "prior": Em1, "reasons": "; ".join(why),
                               "chain_legs": len(rows), "solved_legs": len(solved)})
            continue

        G = Nsum = 0.0
        used = 0
        for r in solved:
            T = _years_to_expiry(Em1, r["hhmmss"], E)
            dl = S.bs_delta(s_em1, r["strike"], T, r["r_used"], r["iv"], r["option_type"])
            if dl is None:
                continue
            G += abs(dl) * r["oi"]
            Nsum += dl * r["oi"]
            used += 1
        if used == 0 or G <= 0:
            ineligible.append({"expiry": E, "prior": Em1,
                               "reasons": "no leg produced a finite delta",
                               "chain_legs": len(rows), "solved_legs": len(solved)})
            continue

        wk = iso_week(E)
        others = [d for d in by_week.get(wk, []) if d != E]
        if not others:
            ineligible.append({"expiry": E, "prior": Em1,
                               "reasons": "no other eligible session in the same ISO week",
                               "chain_legs": len(rows), "solved_legs": len(solved)})
            continue
        med_dlog = S.median([chg[d]["dlog"] for d in others])
        med_dqty = S.median([chg[d]["dqty"] for d in others])
        abn_fall = -(chg[E]["dqty"] - med_dqty)

        events.append({
            "expiry": E, "prior": Em1, "iso_week": wk,
            "F_Em1": F[Em1]["F"], "F_E": F[E]["F"],
            "dlog_E": chg[E]["dlog"], "week_median_dlog": med_dlog,
            "d_E": chg[E]["dlog"] - med_dlog,
            "dqty_E": chg[E]["dqty"], "week_median_dqty": med_dqty,
            "abnormal_fall_qty": abn_fall,
            "G_E": G, "N_E": abs(Nsum),
            "legs_total": len(rows), "legs_solved": len(solved), "legs_used": used,
            "week_others_n": len(others),
            "h_vs_G": abn_fall / G, "h_vs_N": (abn_fall / abs(Nsum)) if Nsum else None,
        })
    return events, ineligible, {"F": F, "chg": chg, "by_week": by_week,
                                "excluded": excluded, "fut_expiries": fut_expiries,
                                "opt_expiry_days": opt_expiry_days, "idx": idx,
                                "missing_series": missing_series,
                                "week_median_pool": sum(len(v) for v in by_week.values())}


def placebo(ctx, sessions):
    """Descriptive, no verdict. NIFTY's weekly expiry moved from Thursday to
    Tuesday in September 2025. The same statistic -- the one-day log change less
    the week median -- on non-expiry Tuesdays BEFORE the move and non-expiry
    Thursdays AFTER it.

    The move date is taken from the data, not recalled: it is the first month in
    which the detected futures expiry falls on a Tuesday (Part 0 step 3 shows
    Thursdays to 2025-08 and Tuesdays from 2025-09)."""
    fe = ctx["fut_expiries"]
    first_tue = next((d for d in fe if dt.date.fromisoformat(d).weekday() == 1), None)
    chg, by_week, excl, oed = ctx["chg"], ctx["by_week"], ctx["excluded"], ctx["opt_expiry_days"]
    out = {}
    for label, wd, cond in (("non-expiry Tuesdays BEFORE the move", 1, lambda d: d < first_tue),
                            ("non-expiry Thursdays AFTER the move", 3, lambda d: d >= first_tue)):
        vals = []
        for d in sessions:
            if (dt.date.fromisoformat(d).weekday() == wd and cond(d)
                    and d in chg and d not in excl and d not in oed):
                others = [x for x in by_week.get(iso_week(d), []) if x != d]
                if others:
                    vals.append(chg[d]["dlog"] - S.median([chg[x]["dlog"] for x in others]))
        w = S.wilcoxon_less(vals) if vals else None
        out[label] = {"n": len(vals), "median": S.median(vals) if vals else float("nan"),
                      "p_one_sided": w["p"] if w else float("nan"),
                      "method": w["method"] if w else "-"}
    out["_move_anchor"] = first_tue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", action="store_true",
                    help="compute section 3 outcomes; refused unless the "
                         "self-test and all four controls pass")
    args = ap.parse_args()

    fut = L.load_futures()
    spot = L.load_spot()
    A, B = load_session_chain()
    sessions = sorted(fut.keys())

    if not args.score:
        print("M1: --score not given. Nothing in section 3 computed.")
        print("Eligibility and inputs would be built over %d sessions." % len(sessions))
        return 0

    # gates, re-checked here rather than assumed
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

    events, ineligible, ctx = build(fut, spot, A, B, sessions)

    print("=" * 96)
    print("M1 -- hedge ratio at weekly expiry (section 3)")
    print("=" * 96)
    print("\nF(d) requires ALL THREE series at the close; a partial sum is not F(d).")
    print("sessions with a missing series at the close:  %d of %d  %s"
          % (len(ctx["missing_series"]), len(sessions),
             sorted(ctx["missing_series"].items()) if ctx["missing_series"] else "(none)"))
    print("sessions with a one-day change available:     %d of %d" % (len(ctx["chg"]), len(sessions)))
    print("sessions in the week-median pool (eligible):  %d" % ctx["week_median_pool"])
    print("\noption expiry dates in the window:            %d" % len(ctx["opt_expiry_days"]))
    print("futures expiry days (section 2):              %d" % len(ctx["fut_expiries"]))
    print("sessions excluded by section 2:               %d" % len(ctx["excluded"]))
    print("ELIGIBLE EVENTS:                              %d" % len(events))
    print("ineligible, with reason:                      %d" % len(ineligible))
    for r in ineligible:
        print("   %s  (prior %s)  legs %d solved %d  -- %s"
              % (r["expiry"], r["prior"], r["chain_legs"], r["solved_legs"], r["reasons"]))

    if not events:
        print("\nNO ELIGIBLE EVENTS -- M1 verdict: NOT DETECTED (no sample).")
        return 0

    print("\n%-12s %-12s %-9s %13s %13s %10s %10s %14s %14s %7s"
          % ("expiry", "E-1", "ISO week", "F(E-1)", "F(E)", "d(E)", "wkmed", "G(E)", "N(E)", "solved"))
    for e in events:
        print("%-12s %-12s %-9s %13.0f %13.0f %+10.5f %+10.5f %14.3e %14.3e %4d/%-3d"
              % (e["expiry"], e["prior"], e["iso_week"], e["F_Em1"], e["F_E"],
                 e["d_E"], e["week_median_dlog"], e["G_E"], e["N_E"],
                 e["legs_used"], e["legs_total"]))

    # ---- Test 1
    dvals = [e["d_E"] for e in events]
    t1 = S.wilcoxon_less(dvals)
    met1 = t1["p"] < ALPHA
    print("\n--- Test 1: Wilcoxon signed-rank on d(E), one-sided, H: median < 0, alpha 0.05")
    print("    n events          %d" % len(dvals))
    print("    median d(E)       %+.6f  (log points of futures OI)" % S.median(dvals))
    print("    W+                %.1f" % t1["w_plus"])
    print("    zeros dropped     %d" % t1["zeros_dropped"])
    print("    p (%s)         %.6g" % (t1["method"], t1["p"]))
    print("    met at 0.05       %s" % met1)

    # ---- Test 2
    xs = [e["G_E"] for e in events]
    ys = [e["abnormal_fall_qty"] for e in events]
    t2 = S.spearman_greater(xs, ys)
    met2 = t2["p"] < ALPHA
    print("\n--- Test 2: Spearman rho, abnormal fall in QUANTITY vs G(E), one-sided, H: rho > 0")
    print("    n events          %d" % t2["n"])
    print("    rho               %+.6f" % t2["rho"])
    print("    p (%s)    %.6g" % (t2["method"], t2["p"]))
    print("    p (asymptotic t)  %.6g   <- cross-check, not the test" % t2["p_asymptotic_t"])
    print("    met at 0.05       %s" % met2)

    # ---- Test 3 (estimate, no verdict)
    print("\n--- Test 3: h-hat -- ESTIMATE, NO VERDICT")
    print("    interval method: percentile bootstrap, %d resamples, seed %d, over EVENTS"
          % (S.B_RESAMPLES, S.SEED))
    for nm, key in (("h-hat vs G(E)", "h_vs_G"), ("h-hat vs N(E)", "h_vs_N")):
        vals = [e[key] for e in events if e[key] is not None]
        bs = S.boot_percentile(vals, S.median)
        print("    %-14s  median %+.6f   95%% CI [%+.6f, %+.6f]   n=%d"
              % (nm, bs["point"], bs["lo"], bs["hi"], bs["n"]))
    print("    unit: dimensionless -- index units of futures OI per index unit of")
    print("          gross delta (C2 established both are index-unit quantities).")

    # ---- verdict, in the pre-registration's words
    if met1 and met2:
        verdict = "HEDGE FOOTPRINT PRESENT"
    elif met1:
        verdict = "EXPIRY EFFECT, NOT DOSE-SCALED"
    else:
        verdict = "NOT DETECTED"
    under = len(events) < 20
    print("\n" + "=" * 96)
    print("M1 VERDICT: %s%s" % (verdict, "   UNDERPOWERED" if under else ""))
    if under:
        print("  (section 6: fewer than 20 eligible events carries UNDERPOWERED)")
    print("=" * 96)

    # ---- placebo, descriptive
    pl = placebo(ctx, sessions)
    print("\n--- Placebo, DESCRIPTIVE, NO VERDICT (section 3)")
    print("    move anchor taken from the data: first Tuesday futures expiry = %s"
          % pl.pop("_move_anchor"))
    for k, v in pl.items():
        print("    %-38s n=%-4d median %+.6f   one-sided p %.4g (%s)"
              % (k, v["n"], v["median"], v["p_one_sided"], v["method"]))

    # ---- artefacts
    with open(os.path.join(L.DATA, "m1_events.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(events[0].keys()))
        w.writeheader()
        for e in events:
            w.writerow(e)
    with open(os.path.join(L.DATA, "m1_ineligible.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["expiry", "prior", "chain_legs",
                                           "solved_legs", "reasons"])
        w.writeheader()
        for r in ineligible:
            w.writerow(r)
    with open(os.path.join(L.DATA, "m1_summary.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["key", "value"])
        w.writerow(["n_events", len(events)])
        w.writerow(["n_ineligible", len(ineligible)])
        w.writerow(["median_d_E", S.median(dvals)])
        w.writerow(["test1_p", t1["p"]])
        w.writerow(["test1_method", t1["method"]])
        w.writerow(["test1_met", met1])
        w.writerow(["test2_rho", t2["rho"]])
        w.writerow(["test2_p", t2["p"]])
        w.writerow(["test2_p_asymptotic_t", t2["p_asymptotic_t"]])
        w.writerow(["test2_method", t2["method"]])
        w.writerow(["test2_met", met2])
        w.writerow(["verdict", verdict])
        w.writerow(["underpowered", under])
        for nm, key in (("h_vs_G", "h_vs_G"), ("h_vs_N", "h_vs_N")):
            vals = [e[key] for e in events if e[key] is not None]
            bs = S.boot_percentile(vals, S.median)
            w.writerow([nm + "_median", bs["point"]])
            w.writerow([nm + "_ci_lo", bs["lo"]])
            w.writerow([nm + "_ci_hi", bs["hi"]])
        for k, v in pl.items():
            w.writerow(["placebo::" + k, "n=%d median=%.8f p=%.6g"
                        % (v["n"], v["median"], v["p_one_sided"])])
    print("\nwrote data/m1_events.csv, data/m1_ineligible.csv, data/m1_summary.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
