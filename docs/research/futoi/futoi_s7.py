"""Section 7: reported DESCRIPTIVELY.

Four items, in the pre-registration's words:

  SENSEX -> NIFTY     For SENSEX option expiries: the M1 statistic computed on
                      NIFTY futures F(d) against SENSEX G(E). This previews the
                      claim that SENSEX gamma is hedged in NIFTY futures.
                      SENSEX's own futures are not used (vendor series unusable;
                      OI a few thousand).
  Volume              Regression of series-1 futures volume per window on |dS|
                      and |dS| x gross gamma, with time-of-day slot effects.
  Synthetic forward   M2 repeated with b measured against the put-call-parity
                      forward (median over the three strikes nearest spot with
                      both legs in that minute, front expiry) in place of spot.
  Expiry-afternoon    F at 15-minute steps on event days against the week's
  path                other days.

NOTHING HERE CARRIES A VERDICT. No item is compared with a threshold, no item
is labelled met or unmet, and no significance claim is made. In this module's
OUTPUT the word "verdict" appears in exactly one place: inside the
"[descriptive, no verdict]" section header printed by h(). Every other printed
line is free of it.

Self-checks that STOP the module rather than report a number:
  * date guard -- every PER-SESSION CSV is checked for a trade_date after
    2026-03-30 (section 8: the Stage 1 holdout stays sealed). Each section
    header prints its file's max trade_date. m2_summary.csv is a key/value
    summary with no per-session dates and is read without the guard (X3).
    `--guard-test` exercises the guard's three outcomes on temp files.
  * M2 reproduction -- M2's own rows from m2_windows.csv are pushed back through
    the same fit() and boot_cluster() calls and must reproduce a, b0, b1 and the
    interval in m2_summary.csv to 1e-8. This tests that section 7 holds M2's
    model and clustering identically before it varies one input (C5).
  * pool check -- the week-median pool built here must give every M1 event the
    same other-day count that m1_events.csv recorded (C6).
  * PCP shape -- rk must lie in 1..3 with at most three rows per minute (C3).

-----------------------------------------------------------------------------
PLACES WHERE SECTION 7 IS AMBIGUOUS, AND THE READING TAKEN
(for the change-of-record list; nothing here adds, drops or tunes a threshold)

S1  "the M1 statistic". M1 has three: d(E) and its Wilcoxon (Test 1), the
    abnormal fall in quantity against G(E) and its Spearman (Test 2), and h-hat
    (Test 3). "computed on NIFTY futures F(d) AGAINST SENSEX G(E)" names a dose
    relation, so Test 2's shape is the primary item. READING: all three are
    printed, because omitting a computed number is worse than printing it. No p
    is compared with alpha and no result is labelled.

S2  SENSEX event eligibility. Section 7 does not restate it. READING: M1's
    eligibility, with the chain side moved to SENSEX and the futures side left
    on NIFTY -- a SENSEX option expiry E on which no NIFTY futures contract
    expires, E not excluded by section 2 (those exclusions are properties of the
    NIFTY futures series, which is still the outcome), with SENSEX chain rows
    and a solved iv at the SENSEX close of E-1, and an F(E), F(E-1) pair.

S3  Volume: "with time-of-day slot effects". READING: slot = the window's start
    boundary (68 slots). Slot effects are applied by WITHIN-SLOT DEMEANING of
    the dependent variable and both regressors, which is algebraically identical
    to 68 slot dummies and avoids building a 12,376 x 70 design. The intercept
    is then zero by construction and is reported as such. "volume per window" is
    read as the SUM of series-1 volume over the five bars (t0, t1]; a window
    with any missing volume bar is dropped and counted, never partially summed.

S4  Synthetic forward: "b measured against the put-call-parity forward ... in
    place of spot". READING: only b changes -- b_syn = series-1 futures close
    minus the PCP forward. dS stays the SPOT change, so the regressor is
    identical to M2's and the two fits are comparable. The PCP forward per
    strike is K + (C - P) * exp(r * T), r = r_used, T = time to 15:30 IST on the
    expiry / 365; the forward for the minute is the MEDIAN over the three
    nearest strikes, as section 7 states. Minutes with fewer than three usable
    strikes are counted and dropped. M2's own spec is refitted on exactly the
    same window subset and printed beside it, so the comparison is like for
    like rather than synthetic-on-a-subset against M2-on-everything (C4).

S5  Expiry-afternoon path: "F at 15-minute steps" does not say when the
    afternoon starts, and F is a level that differs across days. READING: steps
    every 15 minutes from 12:00:59 to 15:15:59, plus the close at 15:29:59 --
    which is 14 minutes after the previous step, not 15, because the 15:30 bar
    is never used (C7). Each day is expressed as ln F(t) - ln F(12:00:59) so
    days of different size are comparable. "event days" = M1's eligible events;
    "the week's other days" = the other sessions of the same ISO week that are
    in the week-median pool.

S6  F(t) intraday. M1's F(d) is defined at the close. READING: at an intraday
    step, F(t) is the same 1+2+3 total taken at the last bar at or before t, per
    series -- the same rule section 2 states for the close -- and is None unless
    all three series are present, exactly as F(d).

-----------------------------------------------------------------------------
CHANGE OF RECORD, made before section 7 was scored

X1  The week-median pool. A first draft of item_sensex built its own pool that
    omitted M1's third condition -- it excluded the section 2 sessions but NOT
    the NIFTY option-expiry days -- so the SENSEX week medians would have been
    taken over a wider set than M1's. There is no shared helper to reuse: M1
    builds the pool inline through a local `eligible_for_week_median` closure
    (d in chg, d not in excluded, d not in opt_expiry_days). The pool is now
    built ONCE in main() with all three conditions and PASSED IN, and the
    duplicate is deleted. C6 then checks it against the week_others_n column
    m1_events.csv recorded, so the agreement is tested, not asserted.

X3  The date guard misfired on a SUMMARY file. It was applied to
    m2_summary.csv with datecol="key", so it took max() over that file's KEY
    column, got the string 'verdict', and reported 'verdict' > '2026-03-30' as a
    breach of the section 8 holdout. The file holds no dates at all. Nothing
    past 2026-03-30 was ever involved, and no section 7 number had been produced
    when this was found. Corrected before any was: a value is compared with the
    window end only if it matches YYYY-MM-DD; a non-date value in a per-session
    file's date column is its own Stop with its own message; and m2_summary.csv
    is read by load_plain(), without the guard. This is Rule 0 in its usual
    form -- the check could fail for a reason other than the one it names, so
    `--guard-test` now shows it failing for each named reason and passing
    otherwise.

X2  SENSEX spot close at E-1 uses "the last bar at or before 15:29:59", section
    2's own rule. NOTE, for the record: futoi_m1.py reads the NIFTY spot close
    by EXACT key (spot[d][SESSION_CLOSE]), not by that rule. The two are
    identical whenever the 15:29:59 bar exists and differ only when it does not,
    in which case M1 declares the event ineligible rather than stepping back to
    an earlier bar. futoi_m1.py is not edited here; the difference is recorded
    so the result doc can state which rule produced which number.
-----------------------------------------------------------------------------
"""
import argparse
import csv
import math
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import futoi_lib as L
import futoi_stats as S
from futoi_controls import load_session_chain, _years_to_expiry
from futoi_m1 import iso_week
from futoi_m2 import fit, beta1_of

HERE = os.path.dirname(os.path.abspath(__file__))
AFTERNOON_FROM = "12:00:59"
REPRO_TOL = 1e-8


class Stop(Exception):
    """Raised for a condition that must halt section 7, not be reported."""


def h(title, maxdate=None):
    print("\n" + "-" * 96)
    print("%s   [descriptive, no verdict]" % title)
    if maxdate:
        print("max trade_date in this item's inputs: %s" % maxdate)
    print("-" * 96)


# ------------------------------------------------------------ loaders
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_plain(name):
    """Load a CSV with NO date guard.

    For m2_summary.csv only. That file is a key/value SUMMARY: it holds no
    per-session trade_date at all, so the window-end guard has nothing to act on
    and is not applicable to it. See X3 -- applying it there is what made the
    guard fire on the string 'verdict'."""
    path = os.path.join(L.DATA, name)
    if not os.path.exists(path):
        return None
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def load_csv(name, datecol="trade_date", base=None):
    """Load a per-session CSV and GUARD ITS DATES. Returns (rows, max_date).

    The guard can fail for exactly two reasons, each with its own message:
      * a value in `datecol` is not a date at all -> the file is not the
        per-session file this call believes it is;
      * the largest date is after the window end -> section 8's sealed holdout.
    A value is compared with the window end ONLY if it matches YYYY-MM-DD, so a
    lexical comparison against a non-date string can no longer masquerade as a
    holdout breach (X3)."""
    path = os.path.join(base or L.DATA, name)
    if not os.path.exists(path):
        return None, None
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return [], None
    if datecol not in rows[0]:
        raise Stop("%s has no '%s' column -- cannot apply the date guard." % (name, datecol))
    vals = [(r[datecol] or "") for r in rows]
    bad = sorted({v for v in vals if not DATE_RE.match(v)})
    if bad:
        raise Stop("%s: non-date value in trade_date column '%s': %r. This file is "
                   "not the per-session file this call expects; the window-end "
                   "guard is not applicable to it."
                   % (name, datecol, bad[:3]))
    mx = max(vals)
    if mx > L.WINDOW_HI:
        raise Stop("%s contains trade_date %s, after the window end %s. Section 8 "
                   "seals the Stage 1 holdout; refusing to use this file."
                   % (name, mx, L.WINDOW_HI))
    return rows, mx


def load_spot_named(name):
    rows, mx = load_csv(name)
    if rows is None:
        return None, None
    out = {}
    for r in rows:
        out.setdefault(r["trade_date"], {})[r["hhmmss"]] = L._f(r["close"])
    return out, mx


def spot_close_at_or_before(spotmap, d, t=L.SESSION_CLOSE):
    """Section 2's close rule, applied to a spot series: the last bar at or
    before t. See X2 -- futoi_m1.py uses an exact key for NIFTY spot."""
    day = spotmap.get(d) or {}
    best = None
    for hh, c in day.items():
        if hh <= t and c is not None and (best is None or hh > best[0]):
            best = (hh, c)
    return best[1] if best else None


def series1_volume(fut, d):
    return {hh: v for hh, _c, _oi, v in fut.get(d, {}).get(1, [])}


def futures_total_at(fut, d, t):
    """S6: F at an intraday step -- series 1+2+3 at the last bar at or before t,
    per series; None unless all three are present."""
    per = {}
    for s in (1, 2, 3):
        best = None
        for hh, _c, oi, _v in fut.get(d, {}).get(s, []):
            if hh <= t and oi is not None and (best is None or hh > best[0]):
                best = (hh, oi)
        if best is None:
            return None
        per[s] = best[1]
    return sum(per.values())


# ------------------------------------------------------------ self-checks
def repro_check(m2rows):
    """C5: push M2's own rows back through the same fit() and boot_cluster()
    calls and require a, b0, b1 and the interval to reproduce m2_summary.csv.

    This is the parity claim made by a test that compares the two things, not by
    a comment: section 7 varies ONE input (b), so it must first be shown to hold
    M2's model, its clustering and its seed identically."""
    print("\n--- C5: M2 reproduction check (model, clustering and seed held fixed)")
    print("    m2_summary.csv: summary file, no per-session dates, guard not applicable")
    summ = load_plain("m2_summary.csv")
    if summ is None:
        raise Stop("data/m2_summary.csv absent -- cannot verify the reproduction.")
    want = {r["key"]: r["value"] for r in summ}
    rows, per_session = [], {}
    for r in m2rows:
        t = (float(r["dS"]), float(r["gxdS"]), float(r["db"]))
        rows.append(t)
        per_session.setdefault(r["trade_date"], []).append(t)
    got = fit(rows)
    bs = S.boot_cluster(per_session, beta1_of)
    checks = [("a", got[0]), ("b0", got[1]), ("b1", got[2]),
              ("b1_ci_lo", bs["lo"]), ("b1_ci_hi", bs["hi"])]
    print("    windows %d   clusters %d   resamples %d"
          % (len(rows), bs["clusters"], bs["resamples"]))
    print("    %-12s %22s %22s %12s" % ("key", "recomputed", "m2_summary.csv", "abs diff"))
    bad = []
    for k, v in checks:
        ref = float(want[k])
        d = abs(v - ref)
        print("    %-12s %22.12f %22.12f %12.2e%s"
              % (k, v, ref, d, "" if d <= REPRO_TOL else "   MISMATCH"))
        if d > REPRO_TOL:
            bad.append(k)
    if int(want["b1_resamples"]) != bs["resamples"]:
        bad.append("b1_resamples")
        print("    resamples %d vs %s   MISMATCH" % (bs["resamples"], want["b1_resamples"]))
    if bad:
        raise Stop("M2 reproduction failed on %s (tolerance %g). Section 7 would "
                   "not be varying one input of M2's model; it would be running a "
                   "different model." % (", ".join(bad), REPRO_TOL))
    print("    reproduced within %g on every key." % REPRO_TOL)


def pool_check(pool, m1events):
    """C6: the pool built here must give each M1 event the same other-day count
    that m1_events.csv recorded."""
    print("\n--- C6: week-median pool check against m1_events.csv")
    if not m1events:
        raise Stop("data/m1_events.csv absent -- cannot verify the pool.")
    if "week_others_n" not in m1events[0]:
        print("    m1_events.csv has no week_others_n column; the check cannot be")
        print("    made and nothing is asserted about the pool.")
        return
    bad = []
    for e in m1events:
        wk = iso_week(e["expiry"])
        mine = len([d for d in pool.get(wk, []) if d != e["expiry"]])
        theirs = int(e["week_others_n"])
        if mine != theirs:
            bad.append((e["expiry"], mine, theirs))
    print("    events checked: %d   mismatches: %d" % (len(m1events), len(bad)))
    for x in bad[:20]:
        print("       %s  pool here %d  m1_events.csv %d" % x)
    if bad:
        raise Stop("the week-median pool here differs from M1's on %d event(s). "
                   "SENSEX week medians would be taken over a different set than "
                   "M1's." % len(bad))
    print("    the pool reproduces M1's other-day count on every event.")


def pcp_shape_check(legs):
    """C3 (revised): rk must lie in 1..3, with at most three rows per minute."""
    per_min = {}
    for r in legs:
        rk = int(r["rk"])
        if rk < 1 or rk > 3:
            raise Stop("pcp_legs.csv carries rk=%d on %s %s; the extraction is "
                       "specified to return rk <= 3 only."
                       % (rk, r["trade_date"], r["hhmmss"]))
        per_min.setdefault((r["trade_date"], r["hhmmss"]), []).append(r)
    over = {k: len(v) for k, v in per_min.items() if len(v) > 3}
    if over:
        k = sorted(over)[0]
        raise Stop("pcp_legs.csv has %d rows for %s %s; at most three are "
                   "specified." % (over[k], k[0], k[1]))
    dup = {k: v for k, v in per_min.items() if len({int(r["rk"]) for r in v}) != len(v)}
    if dup:
        k = sorted(dup)[0]
        raise Stop("pcp_legs.csv repeats an rk within %s %s." % (k[0], k[1]))
    return per_min


# ------------------------------------------------------------ item 1
def item_sensex(fut, spot_sx, sx_max, sessions, pool):
    rows, mx = load_csv("sensex_chain.csv")
    h("7.1  SENSEX -> NIFTY: the M1 statistic on NIFTY F(d) against SENSEX G(E)",
      "sensex_chain %s, spot_bars_sensex %s" % (mx, sx_max))
    if not rows:
        print("SENSEX chain not extracted (data/sensex_chain.csv absent or empty).")
        print("n events = 0. Item not computed; nothing is inferred from its absence.")
        return None
    if spot_sx is None:
        print("SENSEX spot not extracted (data/spot_bars_sensex.csv absent).")
        print("n events = 0. Item not computed.")
        return None

    B, onafter = {}, {}
    for r in rows:
        B.setdefault(r["trade_date"], []).append({
            "hhmmss": r["hhmmss"], "expiry": r["expiry"], "strike": L._f(r["strike"]),
            "option_type": r["option_type"], "oi": L._f(r["oi"]),
            "iv": L._f(r["iv"]), "r_used": L._f(r["r_used"])})
        onafter[r["trade_date"]] = r["exp_on_or_after"]

    sx_sessions = sorted(B)
    sx_expiry_days = {d for d in sx_sessions if onafter.get(d) == d}
    no_sx = [d for d in sessions if d not in B]
    print("NIFTY sessions in the window:                 %d" % len(sessions))
    print("SENSEX sessions with chain rows:              %d" % len(sx_sessions))
    print("NIFTY sessions with NO SENSEX chain rows:     %d" % len(no_sx))
    if no_sx:
        for i in range(0, len(no_sx), 8):
            print("   " + "  ".join(no_sx[i:i + 8]))
    print("SENSEX option expiry days:                    %d" % len(sx_expiry_days))

    fut_expiries, _ = L.futures_expiry_dates(fut, sessions)
    excluded = L.excluded_by_s2(fut_expiries, sessions)      # B8: a dict
    A, _ = load_session_chain()
    nifty_opt_days = {d for (d, _), a in A.items() if a["exp_on_or_after"] == d}
    idx = {d: i for i, d in enumerate(sessions)}

    F = {d: L.futures_total_oi(fut, d)[0] for d in sessions}
    chg = {}
    for i, d in enumerate(sessions):
        if i and F.get(d) and F.get(sessions[i - 1]):
            p = sessions[i - 1]
            chg[d] = {"dlog": math.log(F[d]) - math.log(F[p]), "dqty": F[d] - F[p]}

    ev, inel = [], {}
    for E in sorted(sx_expiry_days):
        why = []
        if E not in idx:
            why.append("E is not a NIFTY futures session")
        if E in excluded:
            why.append(excluded[E])
        if E in idx and E not in chg:
            why.append("no NIFTY one-day change at E")
        Em1 = sessions[idx[E] - 1] if E in idx and idx[E] > 0 else None
        legs = [r for r in B.get(Em1, []) if r["expiry"] == E] if Em1 else []
        solved = [r for r in legs if r["iv"] and r["oi"] and r["strike"]]
        if Em1 is None:
            why.append("no prior NIFTY session")
        elif not legs:
            why.append("no SENSEX chain rows for the expiring series at E-1 close")
        elif not solved:
            why.append("no solved SENSEX iv at E-1 close")
        s_em1 = spot_close_at_or_before(spot_sx, Em1) if Em1 else None   # B4 / X2
        if Em1 is not None and s_em1 is None:
            why.append("no SENSEX spot close at or before 15:29:59 on E-1")
        if why:
            k = "; ".join(why)
            inel[k] = inel.get(k, 0) + 1
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
            inel["no SENSEX leg produced a finite delta"] = \
                inel.get("no SENSEX leg produced a finite delta", 0) + 1
            continue
        ev.append({"expiry": E, "prior": Em1, "iso_week": iso_week(E),
                   "on_nifty_opt_expiry": E in nifty_opt_days,
                   "F_Em1": F[Em1], "F_E": F[E], "dlog_E": chg[E]["dlog"],
                   "dqty_E": chg[E]["dqty"], "G_E_sensex": G, "N_E_sensex": abs(Nsum),
                   "legs_total": len(legs), "legs_used": used})
    print("SENSEX events eligible:                       %d" % len(ev))
    print("SENSEX events ineligible, by reason:          %d" % sum(inel.values()))
    for k in sorted(inel, key=lambda x: -inel[x]):
        print("   %4d  %s" % (inel[k], k))
    if not ev:
        print("n = 0; no statistic computed.")
        return None

    # C1: the pool is built once in main() with M1's three conditions and
    # passed in; item_sensex no longer builds one of its own.
    kept = []
    for e in ev:
        others = [d for d in pool.get(e["iso_week"], []) if d != e["expiry"]]
        if not others:
            continue
        e["week_median_dlog"] = S.median([chg[d]["dlog"] for d in others])
        e["week_median_dqty"] = S.median([chg[d]["dqty"] for d in others])
        e["d_E"] = e["dlog_E"] - e["week_median_dlog"]
        e["abnormal_fall_qty"] = -(e["dqty_E"] - e["week_median_dqty"])
        e["h_vs_G_sensex"] = e["abnormal_fall_qty"] / e["G_E_sensex"]
        e["week_others_n"] = len(others)
        kept.append(e)
    print("SENSEX events with a week median available:   %d" % len(kept))
    if not kept:
        return None

    on_nifty = [e for e in kept if e["on_nifty_opt_expiry"]]
    print("of those, falling on a NIFTY option-expiry day: %d" % len(on_nifty))
    print("  (a SENSEX expiry that shares its date with a NIFTY expiry carries")
    print("   both chains' unwind in the same F(d), so the two lines below")
    print("   separate the overlap from the rest.)")

    def line(label, rows_):
        dv = [e["d_E"] for e in rows_]
        w = S.wilcoxon_less(dv)
        sp = S.spearman_greater([e["G_E_sensex"] for e in rows_],
                                [e["abnormal_fall_qty"] for e in rows_])
        bs = S.boot_percentile([e["h_vs_G_sensex"] for e in rows_], S.median)
        print("\n%s" % label)
        print("  n events                                    %d" % len(rows_))
        print("  median d(E)                                 %+.6f log points of NIFTY futures OI"
              % S.median(dv))
        print("  Wilcoxon one-sided p (median < 0)           %.6g   (%s)" % (w["p"], w["method"]))
        print("  Spearman rho, abnormal fall vs SENSEX G(E)  %+.6f" % sp["rho"])
        print("  Spearman one-sided p (rho > 0)              %.6g   (%s)" % (sp["p"], sp["method"]))
        print("  h-hat vs SENSEX G(E), median                %+.8f" % bs["point"])
        print("  percentile bootstrap 95%% interval           [%+.8f, %+.8f]  (%d resamples, seed %d)"
              % (bs["lo"], bs["hi"], S.B_RESAMPLES, S.SEED))
        return {"n": len(rows_), "median_d": S.median(dv), "wilcoxon_p": w["p"],
                "rho": sp["rho"], "spearman_p": sp["p"], "h_median": bs["point"],
                "h_lo": bs["lo"], "h_hi": bs["hi"]}

    r_all = line("line 1, all eligible SENSEX events:", kept)
    rest = [e for e in kept if not e["on_nifty_opt_expiry"]]
    r_rest = line("line 2, the same with NIFTY option-expiry dates removed:", rest) \
        if rest else None
    if not rest:
        print("\nline 2: every eligible SENSEX event falls on a NIFTY option-expiry")
        print("        day, so the second line has n = 0 and is not computed.")
    print("\nunit of h-hat here: index units of NIFTY futures OI per index unit of")
    print("  SENSEX gross delta. The numerator and denominator belong to DIFFERENT")
    print("  underlyings, so this number is NOT comparable with M1's h-hat and is")
    print("  not a hedge ratio; it is a scale between two indices.")

    with open(os.path.join(L.DATA, "s7_sensex_events.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(kept[0].keys()))
        wr.writeheader()
        for e in kept:
            wr.writerow(e)
    out = {"all::" + k: v for k, v in r_all.items()}
    if r_rest:
        out.update({"ex_nifty_expiry::" + k: v for k, v in r_rest.items()})
    out["n_on_nifty_opt_expiry"] = len(on_nifty)
    out["n_nifty_sessions_without_sensex_chain"] = len(no_sx)
    return out


# ------------------------------------------------------------ item 2
def item_volume(fut, A, m2rows, m2_max):
    h("7.2  Volume: series-1 futures volume per window on |dS| and |dS| x gross gamma",
      "m2_windows %s" % m2_max)
    if not m2rows:
        print("M2 windows not available (data/m2_windows.csv absent). n = 0.")
        return None
    rows, dropped = [], {}

    def drop(reason):
        dropped[reason] = dropped.get(reason, 0) + 1

    for r in m2rows:
        d, t0, t1 = r["trade_date"], r["win_start"], r["win_end"]
        a = A.get((d, t0))
        if a is None or a["gross"] in (None, 0.0):
            drop("no gross gamma at the window's first minute")
            continue
        vol = series1_volume(fut, d)
        mins = [m for m in sorted(vol) if t0 < m <= t1]      # S3: the five bars (t0, t1]
        if len(mins) != 5:
            drop("window does not carry exactly 5 series-1 volume bars")
            continue
        if any(vol[m] is None for m in mins):               # B3: no partial sums
            drop("a series-1 volume bar in the window is null")
            continue
        v = sum(vol[m] for m in mins)
        adS = abs(float(r["dS"]))
        rows.append({"trade_date": d, "slot": t0, "volume": v, "abs_dS": adS,
                     "gross_gamma": a["gross"], "abs_dS_x_gross": adS * a["gross"]})
    print("windows offered by M2:                        %d" % len(m2rows))
    print("windows used:                                 %d" % len(rows))
    print("windows dropped, by reason:                   %d" % sum(dropped.values()))
    for k in sorted(dropped, key=lambda x: -dropped[x]):
        print("   %6d  %s" % (dropped[k], k))
    if len(rows) < 10:
        print("n too small; no fit reported.")
        return None
    slots = sorted({r["slot"] for r in rows})
    print("time-of-day slots:                            %d" % len(slots))
    print("slot effects by within-slot demeaning (S3), algebraically identical to")
    print("  %d slot dummies; the intercept is then 0 by construction." % len(slots))
    means = {}
    for s in slots:
        sub = [r for r in rows if r["slot"] == s]
        means[s] = (sum(r["volume"] for r in sub) / len(sub),
                    sum(r["abs_dS"] for r in sub) / len(sub),
                    sum(r["abs_dS_x_gross"] for r in sub) / len(sub))
    X, y = [], []
    for r in rows:
        mv, mx1, mx2 = means[r["slot"]]
        X.append([r["abs_dS"] - mx1, r["abs_dS_x_gross"] - mx2])
        y.append(r["volume"] - mv)
    b = S.ols(np.array(X), np.array(y))
    print("\nn windows                                     %d" % len(rows))
    print("intercept (demeaned, 0 by construction)       %+.6g" % b[0])
    print("coefficient on |dS|                           %+.6g  index-unit quantity per index point"
          % b[1])
    print("coefficient on |dS| x gross gamma             %+.6g  per (index point x index-unit gamma*OI)"
          % b[2])
    print("median volume per window                      %.0f  index-unit quantity"
          % S.median([r["volume"] for r in rows]))
    print("median |dS|                                   %.4f index points"
          % S.median([r["abs_dS"] for r in rows]))
    print("median gross gamma*OI                         %.6g index units"
          % S.median([r["gross_gamma"] for r in rows]))
    with open(os.path.join(L.DATA, "s7_volume_windows.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        for r in rows:
            wr.writerow(r)
    return {"n": len(rows), "b_absdS": b[1], "b_absdS_x_gross": b[2]}


# ------------------------------------------------------------ item 3
def item_synthetic(m2rows, m2_max):
    legs, pc_max = load_csv("pcp_legs.csv")
    h("7.3  Synthetic forward: M2 with b against the put-call-parity forward",
      "pcp_legs %s, m2_windows %s" % (pc_max, m2_max))
    if not legs:
        print("PCP legs not extracted (data/pcp_legs.csv absent or empty). n = 0.")
        return None
    per_min = pcp_shape_check(legs)                           # C3: stops on bad shape
    not_three = sum(1 for v in per_min.values() if len(v) != 3)
    print("minutes with PCP rows:                        %d" % len(per_min))
    print("minutes whose row count is not 3:             %d" % not_three)

    fwd, fexp, drop_minute = {}, {}, {}

    def dropm(reason):
        drop_minute[reason] = drop_minute.get(reason, 0) + 1

    for key, rs in per_min.items():
        if len(rs) != 3:
            dropm("fewer than three strikes with both legs")
            continue
        vals = []
        for r in rs:
            K, c, p, ru = (L._f(r["strike"]), L._f(r["c"]), L._f(r["p"]), L._f(r["r_used"]))
            if None in (K, c, p) or ru is None:
                continue
            T = _years_to_expiry(r["trade_date"], r["hhmmss"], r["expiry"])
            vals.append(K + (c - p) * math.exp(ru * T))
        if len(vals) != 3:
            dropm("a leg lacked a price or r_used")
            continue
        fwd[key] = S.median(vals)
        fexp[key] = rs[0]["expiry"]
    print("minutes with a PCP forward:                   %d" % len(fwd))
    print("minutes dropped, by reason:                   %d" % sum(drop_minute.values()))
    for k in sorted(drop_minute, key=lambda x: -drop_minute[x]):
        print("   %6d  %s" % (drop_minute[k], k))

    syn, m2same, dropped = [], [], {}
    syn_cl, m2_cl = {}, {}

    def drop(reason):
        dropped[reason] = dropped.get(reason, 0) + 1

    for r in m2rows or []:
        d, t0, t1 = r["trade_date"], r["win_start"], r["win_end"]
        k0, k1 = (d, t0), (d, t1)
        if k0 not in fwd or k1 not in fwd:
            drop("no PCP forward at a boundary")
            continue
        if fexp[k0] != r["expiry"] or fexp[k1] != r["expiry"]:   # C8
            drop("front expiry differs from M2's")
            continue
        dS, g = float(r["dS"]), float(r["g"])
        b_syn0 = float(r["fut_0"]) - fwd[k0]
        b_syn1 = float(r["fut_1"]) - fwd[k1]
        rs = (dS, g * dS, b_syn1 - b_syn0)
        rm = (dS, g * dS, float(r["db"]))                        # C4: M2's own db
        syn.append(rs)
        m2same.append(rm)
        syn_cl.setdefault(d, []).append(rs)
        m2_cl.setdefault(d, []).append(rm)
    print("windows offered by M2:                        %d" % len(m2rows or []))
    print("windows used:                                 %d" % len(syn))
    print("windows dropped, by reason:                   %d" % sum(dropped.values()))
    for k in sorted(dropped, key=lambda x: -dropped[x]):
        print("   %6d  %s" % (dropped[k], k))
    if len(syn) < 4:
        print("n too small; no fit reported.")
        return None

    fs, fm = fit(syn), fit(m2same)
    bsS = S.boot_cluster(syn_cl, beta1_of)
    bsM = S.boot_cluster(m2_cl, beta1_of)
    print("\nn windows %d   n sessions (bootstrap clusters) %d" % (len(syn), bsS["clusters"]))
    print("both fits below use EXACTLY the same window subset (C4), so the only")
    print("difference between them is what b is measured against.")
    print("\n%-34s %16s %16s" % ("", "b vs PCP forward", "b vs spot (M2)"))
    print("%-34s %+16.8f %+16.8f" % ("a (intercept, index points)", fs[0], fm[0]))
    print("%-34s %+16.8f %+16.8f" % ("b0", fs[1], fm[1]))
    print("%-34s %+16.8f %+16.8f" % ("b1", fs[2], fm[2]))
    print("%-34s %+16.8f %+16.8f" % ("b1 interval low", bsS["lo"], bsM["lo"]))
    print("%-34s %+16.8f %+16.8f" % ("b1 interval high", bsS["hi"], bsM["hi"]))
    print("intervals: %s, %d resamples, seed %d"
          % (bsS["method"], S.B_RESAMPLES, S.SEED))
    return {"n": len(syn), "a_syn": fs[0], "b0_syn": fs[1], "b1_syn": fs[2],
            "b1_syn_lo": bsS["lo"], "b1_syn_hi": bsS["hi"],
            "a_m2_same_subset": fm[0], "b0_m2_same_subset": fm[1],
            "b1_m2_same_subset": fm[2], "b1_m2_same_subset_lo": bsM["lo"],
            "b1_m2_same_subset_hi": bsM["hi"],
            "minutes_row_count_not_three": not_three}


# ------------------------------------------------------------ item 4
def item_afternoon(fut, m1events, pool):
    h("7.4  Expiry-afternoon path: F at 15-minute steps, event days vs the week's other days")
    if not m1events:
        print("M1 events not available (data/m1_events.csv absent). n = 0.")
        return None
    steps = []
    t = 12 * 60
    while t <= 15 * 60 + 29:
        steps.append("%02d:%02d:59" % (t // 60, t % 60))
        t += 15
    steps = [s for s in steps if s <= L.SESSION_CLOSE]
    if steps[-1] != L.SESSION_CLOSE:
        steps.append(L.SESSION_CLOSE)
    print("steps: %s to %s, every 15 minutes, then the close %s --" % (steps[0], steps[-2], steps[-1]))
    print("  the final gap is 14 minutes, not 15, because the 15:30 bar is never used (C7).")
    print("number of steps:                              %d" % len(steps))
    print("S5: each day is ln F(t) - ln F(%s), so levels are comparable." % AFTERNOON_FROM)

    ev_days = [e["expiry"] for e in m1events]
    other_days = []
    for e in m1events:
        wk = iso_week(e["expiry"])                            # C2: computed, not read
        for d in pool.get(wk, []):
            if d != e["expiry"]:
                other_days.append(d)
    other_days = sorted(set(other_days))
    print("event days:                                   %d" % len(ev_days))
    print("the weeks' other days:                        %d" % len(other_days))

    def paths(days):
        out, drop = {s: [] for s in steps}, 0
        for d in days:
            base = futures_total_at(fut, d, AFTERNOON_FROM)
            if not base:
                drop += 1
                continue
            for s in steps:
                v = futures_total_at(fut, d, s)
                if v:
                    out[s].append(math.log(v) - math.log(base))
        return out, drop

    pe, de = paths(ev_days)
    po, do = paths(other_days)
    print("event days dropped (no F at %s):        %d" % (AFTERNOON_FROM, de))
    print("other days dropped (no F at %s):        %d" % (AFTERNOON_FROM, do))
    print("\n%-10s %12s %8s %12s %8s %12s"
          % ("step", "event med", "n", "other med", "n", "difference"))
    out = []
    for s in steps:
        me = S.median(pe[s]) if pe[s] else float("nan")
        mo = S.median(po[s]) if po[s] else float("nan")
        print("%-10s %+12.6f %8d %+12.6f %8d %+12.6f"
              % (s, me, len(pe[s]), mo, len(po[s]), me - mo))
        out.append({"step": s, "event_median_lnF": me, "event_n": len(pe[s]),
                    "other_median_lnF": mo, "other_n": len(po[s]),
                    "difference": me - mo})
    print("unit: log points of total futures OI (series 1+2+3), relative to %s"
          % AFTERNOON_FROM)
    with open(os.path.join(L.DATA, "s7_afternoon_path.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        wr.writeheader()
        for r in out:
            wr.writerow(r)
    return {"steps": len(steps), "event_days_used": len(ev_days) - de,
            "other_days_used": len(other_days) - do}


# ------------------------------------------------------------ main
def run():
    fut = L.load_futures()
    spot_sx, sx_max = load_spot_named("spot_bars_sensex.csv")
    A, _B = load_session_chain()
    sessions = sorted(d for d in fut.keys() if L.WINDOW_LO <= d <= L.WINDOW_HI)
    m2rows, m2_max = load_csv("m2_windows.csv")
    m1events, _ = load_csv("m1_events.csv", datecol="expiry")

    print("=" * 96)
    print("Section 7 -- reported DESCRIPTIVELY")
    print("=" * 96)
    print("sessions in the window: %d   M2 windows on file: %s   M1 events on file: %s"
          % (len(sessions), len(m2rows) if m2rows else 0, len(m1events) if m1events else 0))
    print("date guard: every loaded CSV is checked against the window end %s."
          % L.WINDOW_HI)
    print("max trade_date -- m2_windows %s, spot_bars_sensex %s" % (m2_max, sx_max))

    # C1: the pool, built ONCE with M1's three conditions (X1)
    fut_expiries, _ = L.futures_expiry_dates(fut, sessions)
    excluded = L.excluded_by_s2(fut_expiries, sessions)
    opt_days = {d for (d, _), a in A.items() if a["exp_on_or_after"] == d}
    F = {d: L.futures_total_oi(fut, d)[0] for d in sessions}
    pool = {}
    for i, d in enumerate(sessions):
        if i and F.get(d) and F.get(sessions[i - 1]) \
                and d not in excluded and d not in opt_days:
            pool.setdefault(iso_week(d), []).append(d)
    print("week-median pool: %d weeks, %d sessions (M1's three conditions)"
          % (len(pool), sum(len(v) for v in pool.values())))

    if not m2rows:
        raise Stop("data/m2_windows.csv absent -- M2 must be scored before section 7.")
    repro_check(m2rows)        # C5
    pool_check(pool, m1events)  # C6

    res = {}
    res["sensex"] = item_sensex(fut, spot_sx, sx_max, sessions, pool)
    res["volume"] = item_volume(fut, A, m2rows, m2_max)
    res["synthetic"] = item_synthetic(m2rows, m2_max)
    res["afternoon"] = item_afternoon(fut, m1events, pool)

    with open(os.path.join(L.DATA, "s7_summary.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["item", "key", "value"])
        for item, d in res.items():
            if d is None:
                w.writerow([item, "computed", "no"])
                continue
            for k, v in d.items():
                w.writerow([item, k, v])
    print("\n" + "=" * 96)
    print("Section 7 complete. Every item above is DESCRIPTIVE: no threshold")
    print("comparison and no significance claim is made anywhere in it.")
    print("=" * 96)
    return 0


def guard_test():
    """Exercise the date guard's three outcomes on temp files. Not part of
    --score; it touches nothing in data/ and computes no section 7 number.

    Each case states what MUST happen, so the guard is shown failing for each
    reason it names and passing otherwise (X3)."""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="futoi_guard_")
    cases = [
        ("a", "guardtest_future.csv",
         "trade_date,x\n2025-06-02,1\n2026-03-31,2\n",
         "after the window end",
         "a date past 2026-03-30 must trip the section 8 holdout guard"),
        ("b", "guardtest_nondate.csv",
         "trade_date,x\nverdict,1\n2025-06-02,2\n",
         "non-date value in trade_date",
         "a non-date value must give the NON-DATE message, never the "
         "window-end message"),
        ("c", "guardtest_ok.csv",
         "trade_date,x\n2025-04-01,1\n2026-03-30,2\n",
         None,
         "in-window dates only must pass"),
    ]
    print("=" * 96)
    print("--guard-test: the date guard's three outcomes (no data/ file is read)")
    print("=" * 96)
    ok = True
    try:
        for tag, fname, body, expect, must in cases:
            with open(os.path.join(tmp, fname), "w") as fh:
                fh.write(body)
            print("\n(%s) %s" % (tag, fname))
            print("    must: %s" % must)
            try:
                rows, mx = load_csv(fname, base=tmp)
                got = "PASSED, max trade_date %s, %d rows" % (mx, len(rows))
                good = expect is None
            except Stop as e:
                got = "Stop: %s" % e
                good = expect is not None and expect in str(e)
                if expect is None:
                    good = False
                elif "after the window end" in str(e) and expect != "after the window end":
                    good = False
            print("    got:  %s" % got)
            print("    ->    %s" % ("as required" if good else "NOT AS REQUIRED"))
            ok = ok and good
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("\n" + "=" * 96)
    print("guard-test: %s" % ("all three outcomes as required" if ok else "FAILED"))
    print("=" * 96)
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", action="store_true",
                    help="compute the section 7 descriptives; refused unless "
                         "the self-test and all four controls pass")
    ap.add_argument("--guard-test", action="store_true",
                    help="exercise the date guard on temp files; reads nothing "
                         "in data/ and computes no section 7 number")
    args = ap.parse_args()

    if args.guard_test:
        return guard_test()

    if os.path.exists(os.path.join(HERE, "STOPPED.md")):
        print("REFUSING: STOPPED.md is present -- a control failed.")
        return 2
    if not args.score:
        print("S7: --score not given. Nothing in section 7 computed.")
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
    try:
        return run()
    except Stop as e:
        print("\n" + "!" * 96)
        print("SECTION 7 STOPPED: %s" % e)
        print("!" * 96)
        return 7


if __name__ == "__main__":
    sys.exit(main())
