"""Part 0 step 6: controls C1-C4 from section 5 of the pre-registration.

"Any control failing stops the run. The cause is diagnosed before anything in
section 3 or section 4 is computed."  This module therefore writes STOPPED.md
and exits 3 on any failure. It computes NOTHING from sections 3, 4 or 7.

Each control states, before its number, what would make it fail -- Rule 0: a
check that cannot fail for the reason it names is not a check.
"""
import csv
import datetime as dt
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import futoi_lib as L
import futoi_stats as S

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = S.SEED
RESULTS = []


def record(cid, title, what_would_fail, measured, passed, detail=""):
    RESULTS.append({"id": cid, "title": title, "fails_when": what_would_fail,
                    "measured": measured, "passed": passed, "detail": detail})
    print("\n%s  %s" % (cid, title))
    print("   fails when: %s" % what_would_fail)
    for line in str(measured).splitlines():
        print("   %s" % line)
    if detail:
        for line in detail.splitlines():
            print("   %s" % line)
    print("   -> %s" % ("PASS" if passed else "FAIL"))
    return passed


# ---------------------------------------------------------------- loaders
def load_session_chain():
    """-> (A rows by (date,hhmmss), B rows by date)"""
    A, B = {}, {}
    path = os.path.join(L.DATA, "session_chain.csv")
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            if r["tag"] == "A":
                A[(r["trade_date"], r["hhmmss"])] = {
                    "expiry": r["expiry"], "exp_on_or_after": r["exp_on_or_after"],
                    "legs": int(r["legs"]), "legs_solved": int(r["legs_solved"]),
                    "net": L._f(r["net_gamma_oi"]), "gross": L._f(r["gross_gamma_oi"])}
            else:
                B.setdefault(r["trade_date"], []).append({
                    "hhmmss": r["hhmmss"], "expiry": r["expiry"],
                    "exp_on_or_after": r["exp_on_or_after"],
                    "strike": L._f(r["strike"]), "option_type": r["option_type"],
                    "oi": L._f(r["oi"]), "iv": L._f(r["iv"]), "r_used": L._f(r["r_used"])})
    return A, B


def load_gamma_metrics():
    out = {}
    path = os.path.join(L.DATA, "gamma_metrics.csv")
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            out[(r["trade_date"], r["hhmmss"])] = L._f(r["net_gex"])
    return out


def dose_g(a):
    """Section 4's dose: g = sum(sign * gamma * OI) / sum(gamma * OI),
    CE positive, PE negative. Unitless, -1..+1. Computed over the strikes with
    a solved gamma only; a NULL gamma enters neither sum."""
    if a is None or a["gross"] in (None, 0.0) or a["net"] is None:
        return None
    return a["net"] / a["gross"]


# ---------------------------------------------------------------- C1
def c1_clock(fut, spot, sessions):
    """C1: correlation of 1-minute series-1 futures returns with spot returns at
    lags -1, 0, +1 over 20 sessions; lag 0 must be the largest.

    FAILS IF the vendor clocks are offset between the two tables: a one-minute
    label shift would put the maximum at lag -1 or +1. That is exactly the defect
    this control exists to catch, and it is the defect S105 found in R(T)."""
    rnd = random.Random(SEED)
    pool = [d for d in sessions if d in spot and 1 in fut.get(d, {})]
    pick = sorted(rnd.sample(pool, 20))
    minutes = L.session_minutes()
    pairs = {-1: ([], []), 0: ([], []), 1: ([], [])}
    for d in pick:
        fs = {h: c for h, c, _, _ in fut[d][1]}
        sp = spot[d]
        fr, sr = {}, {}
        for i in range(1, len(minutes)):
            t0, t1 = minutes[i - 1], minutes[i]
            if t0 in fs and t1 in fs and fs[t0]:
                fr[t1] = math.log(fs[t1] / fs[t0])
            if t0 in sp and t1 in sp and sp[t0]:
                sr[t1] = math.log(sp[t1] / sp[t0])
        idx = {t: i for i, t in enumerate(minutes)}
        for lag in (-1, 0, 1):
            for t, v in fr.items():
                j = idx[t] + lag
                if 0 <= j < len(minutes):
                    u = sr.get(minutes[j])
                    if u is not None:
                        pairs[lag][0].append(v)
                        pairs[lag][1].append(u)
    cors = {lag: S._pearson(x, y) for lag, (x, y) in pairs.items()}
    best = max(cors, key=lambda k: cors[k])
    txt = ("sessions sampled: 20 of %d (seed %d)\n" % (len(pool), SEED)
           + "\n".join("corr(fut_ret[t], spot_ret[t%+d]) = %+.6f   (n=%d pairs)"
                       % (lag, cors[lag], len(pairs[lag][0])) for lag in (-1, 0, 1))
           + "\nlargest at lag %+d" % best)
    return record("C1", "clock alignment, futures vs spot 1-minute returns",
                  "a one-minute label offset between the tables would put the "
                  "maximum at lag -1 or +1", txt, best == 0), cors


# ---------------------------------------------------------------- C2
def _gcd_list(vals):
    g = 0
    for v in vals:
        if v is None:
            continue
        g = math.gcd(g, int(round(v)))
    return g


def c2_units(fut, B, sessions, spot):
    """C2: median series-1 futures OI at close, and median front-expiry option OI
    per strike near spot, both printed with their magnitudes. Both must be
    quantities (index units), not contracts.

    Quantity-vs-contracts is decided by MEASUREMENT, not by inspection of the
    magnitude: an OI expressed in index units is a whole multiple of the lot
    size, so the per-session GCD over many values recovers the lot, while a
    contract count has GCD 1.

    TWO conditions, both of them section 5's own and neither added:
      (a) every session's GCD > 1 in BOTH series
          -> both are index-unit quantities, not contract counts.
      (b) every session's gcd(fut_gcd, opt_gcd) > 1
          -> the two are expressed in a COMPATIBLE unit, so no conversion is
             needed and h-hat is dimensionless. Threshold-free: if option OI
             were a contract count its GCD would be 1 and gcd(75, 1) = 1 fails.

    CHANGE OF SPECIFICATION, recorded before any outcome was scored.
    This control was first implemented with a third condition -- "the per-session
    GCDs are EQUAL on every session" -- which section 5 does not state. It FAILED
    on 13 of 247 sessions where 306 option legs are not whole multiples of the
    era lot, so the GCD recovers a divisor (25, or 5) rather than the lot. That
    is a property of those OI values, not of the unit: the medians are plausible
    only as index units (as contract counts the futures leg would be 1.12 billion
    index units), and both series step 75 -> 65 at the same NSE lot change. The
    failure was therefore NOT the one C2 names. Diagnosed in diagnose_c2.py, the
    stop recorded in STOPPED.md, and the re-specification ruled by the operator
    on 2026-11-17 before Part 1 was computed. The 306 off-lot legs are reported
    here, and carried into the result doc's Limits and NOT_VERIFIED.md -- they
    are not suppressed.

    The GCD is taken PER SESSION, never pooled: the pooled GCD over the window
    is 5, which is gcd(75, 65) and a lot NSE never listed. A first pass asserted
    "5, the NIFTY lot size" -- an interpretation stated without measuring it."""
    fut_oi, fut_g, opt_g = [], {}, {}
    for d in sessions:
        vals = [b[2] for b in fut.get(d, {}).get(1, []) if b[2]]
        b = L.series_close(fut.get(d, {}).get(1, []))
        if b and b[2]:
            fut_oi.append(b[2])
        if vals:
            fut_g[d] = _gcd_list(vals)
    near = []
    for d, rows in B.items():
        s = spot.get(d, {}).get(L.SESSION_CLOSE)
        if s is None or not rows:
            continue
        ks = sorted({r["strike"] for r in rows if r["strike"] is not None},
                    key=lambda k: abs(k - s))[:5]
        sess_oi = [r["oi"] for r in rows if r["oi"]]
        for r in rows:
            if r["strike"] in ks and r["oi"]:
                near.append(r["oi"])
        if sess_oi:
            opt_g[d] = _gcd_list(sess_oi)
    med_fut, med_opt = S.median(fut_oi), S.median(near)
    pooled_fut, pooled_opt = _gcd_list(fut_oi), _gcd_list(near)

    def eras(gmap):
        out, cur = [], None
        for d in sorted(gmap):
            if cur is None or gmap[d] != cur[2]:
                cur = [d, d, gmap[d]]
                out.append(cur)
            else:
                cur[1] = d
        return out

    ef, eo = eras(fut_g), eras(opt_g)
    shared = sorted(set(fut_g) & set(opt_g))
    cond_a_bad = [d for d in shared if fut_g[d] <= 1 or opt_g[d] <= 1]
    cond_b = {d: math.gcd(fut_g[d], opt_g[d]) for d in shared}
    cond_b_bad = [d for d in shared if cond_b[d] <= 1]
    equal_anyway = sum(1 for d in shared if fut_g[d] == opt_g[d])
    offlot = sum(1 for d in opt_g
                 for r in B[d]
                 if r["oi"] and int(round(r["oi"])) % (75 if d <= "2025-12-29" else 65) != 0)
    ok = not cond_a_bad and not cond_b_bad
    txt = ("median series-1 futures OI at close:        %15.0f  (n=%d sessions)\n"
           "   read as index units  -> %.0f contracts at the era lot\n"
           "   read as CONTRACTS    -> %.2f billion index units (implausible)\n"
           "median front-expiry option OI per strike\n"
           "  over the 5 strikes nearest spot:          %15.0f  (n=%d legs)\n"
           "   read as index units  -> %.0f contracts at the era lot\n"
           "pooled GCD over the whole window, futures:  %15d\n"
           "pooled GCD over the whole window, options:  %15d\n"
           "   (pooling collapses eras: 5 = gcd(75,65), a lot NSE never listed;\n"
           "    the per-session GCD is the measurement)\n"
           "per-session GCD, futures -- contiguous runs:\n%s\n"
           "per-session GCD, options -- contiguous runs:\n%s\n"
           "(a) sessions with GCD <= 1 in either series: %d of %d\n"
           "(b) sessions with gcd(fut,opt) <= 1:         %d of %d\n"
           "    minimum gcd(fut,opt) over the window:   %d\n"
           "reported, not gating: sessions where the two GCDs happen to be\n"
           "    exactly equal:                          %d of %d\n"
           "reported, not gating: option legs that are not whole multiples of\n"
           "    the era lot:                            %d"
           % (med_fut, len(fut_oi), med_fut / 75.0, med_fut * 75 / 1e9,
              med_opt, len(near), med_opt / 75.0,
              pooled_fut, pooled_opt,
              "\n".join("     %s .. %s   GCD %d" % (a, b, g) for a, b, g in ef),
              "\n".join("     %s .. %s   GCD %d" % (a, b, g) for a, b, g in eo),
              len(cond_a_bad), len(shared), len(cond_b_bad), len(shared),
              min(cond_b.values()) if cond_b else 0,
              equal_anyway, len(shared), offlot))
    det = ("(a) and (b) both hold on every session, so both series are index-unit\n"
           "QUANTITIES in a compatible unit. h-hat = (index units of futures OI) /\n"
           "(index units of gross delta) is dimensionless; NO conversion is stated.\n"
           "The %d off-lot option legs do not change the unit -- they are carried\n"
           "into the result doc's Limits and into NOT_VERIFIED.md." % offlot
           if ok else
           "units are NOT compatible -- h-hat is withheld until a conversion is\n"
           "stated (section 5).")
    return record("C2", "units of futures OI and option OI",
                  "a contract-count series has GCD 1, and two incompatible units "
                  "would make h-hat dimensionally meaningless",
                  txt, ok, det), {"med_fut": med_fut, "med_opt": med_opt,
                                  "fut_gcd_eras": ef, "opt_gcd_eras": eo,
                                  "offlot_legs": offlot}


# ---------------------------------------------------------------- C3
def c3_gamma_parity(A, gm, excluded, opt_expiry_days):
    """C3: sign(g) agrees with sign(hist_gamma_metrics.net_gex) at the same minute
    on >= 85% of 500 sampled window starts.

    FAILS IF the chain's net-over-gross and the board's net_gex disagree in sign
    more than 15% of the time -- which would mean g is not the quantity the board
    calls net gamma, whatever its scale. The two use different expiry scopes, so
    exact agreement is not expected; the measured rate is reported."""
    starts = L.window_boundaries()[:-1]
    cand = []
    for (d, h), a in A.items():
        if h not in starts or d in excluded or d in opt_expiry_days:
            continue
        g = dose_g(a)
        ng = gm.get((d, h))
        if g is None or ng is None or g == 0 or ng == 0:
            continue
        cand.append((d, h, g, ng))
    cand.sort()
    rnd = random.Random(SEED)
    n = min(500, len(cand))
    pick = rnd.sample(cand, n) if len(cand) >= n else cand
    agree = sum(1 for _, _, g, ng in pick if (g > 0) == (ng > 0))
    rate = agree / len(pick) if pick else float("nan")
    with open(os.path.join(L.DATA, "c3_sample.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["trade_date", "hhmmss", "g", "net_gex", "sign_g", "sign_net_gex", "agree"])
        for d, h, g, ng in sorted(pick):
            w.writerow([d, h, "%.10g" % g, "%.10g" % ng,
                        1 if g > 0 else -1, 1 if ng > 0 else -1, (g > 0) == (ng > 0)])
    txt = ("eligible window starts with both values non-zero: %d\n"
           "sampled (seed %d):                                %d\n"
           "sign agreement:                                   %d/%d = %.1f%%\n"
           "threshold:                                        >= 85.0%%"
           % (len(cand), SEED, len(pick), agree, len(pick), 100 * rate))
    return record("C3", "gamma parity, sign(g) vs sign(net_gex)",
                  "sign disagreement above 15% would mean g is not the board's "
                  "net gamma", txt, rate >= 0.85), rate


# ---------------------------------------------------------------- C4
def c4_delta(B, spot, e_minus_1):
    """C4: at the close of five sampled E-1 sessions, the strike nearest spot has
    call delta within 0.35-0.65.

    FAILS IF the delta construction is wrong -- a mis-set T (days instead of
    years), a decimal-vs-percent iv, or a sign error would push the at-the-money
    call delta far outside that band. This is the control that would have caught
    F-68's anchor error class on the Greeks side."""
    rnd = random.Random(SEED)
    pool = sorted(d for d in e_minus_1 if d in B and d in spot)
    pick = sorted(rnd.sample(pool, 5)) if len(pool) >= 5 else pool
    lines, oks = [], []
    for d in pick:
        s = spot[d].get(L.SESSION_CLOSE)
        rows = [r for r in B[d] if r["iv"] and r["strike"] and r["option_type"] == "CE"]
        if s is None or not rows:
            lines.append("%s  no ATM call with a solved iv at the close" % d)
            oks.append(False)
            continue
        r = min(rows, key=lambda r: abs(r["strike"] - s))
        E = r["expiry"]
        T = _years_to_expiry(d, r["hhmmss"], E)
        dl = S.bs_delta(s, r["strike"], T, r["r_used"], r["iv"], "CE")
        ok = dl is not None and 0.35 <= dl <= 0.65
        oks.append(ok)
        lines.append("%s  spot %9.2f  K %9.2f  iv %.4f  r %.4f  T %.6f yr  "
                     "call delta %.4f  %s"
                     % (d, s, r["strike"], r["iv"], r["r_used"], T, dl,
                        "in band" if ok else "OUT OF BAND"))
    txt = ("E-1 sessions available: %d, sampled 5 (seed %d)\n" % (len(pool), SEED)
           + "\n".join(lines) + "\nband: 0.35 <= call delta <= 0.65")
    return record("C4", "delta sanity at the money",
                  "a wrong T, a percent-vs-decimal iv, or a sign error would put "
                  "the ATM call delta outside 0.35-0.65",
                  txt, all(oks) and len(oks) == 5), None


def _years_to_expiry(d, hhmmss, expiry):
    """T = exact time to 15:30 IST on the expiry date / 365 (section 2).
    Both timestamps are read on the vendor clock; no conversion is applied."""
    t0 = dt.datetime.fromisoformat("%sT%s" % (d, hhmmss))
    t1 = dt.datetime.fromisoformat("%sT15:30:00" % expiry)
    return (t1 - t0).total_seconds() / (365.0 * 24 * 3600)


# ---------------------------------------------------------------- main
def main():
    fut = L.load_futures()
    spot = L.load_spot()
    sessions = sorted(fut.keys())
    A, B = load_session_chain()
    gm = load_gamma_metrics()

    chain_sessions = sorted({d for d, _ in A.keys()} | set(B.keys()))
    if len(chain_sessions) < len(sessions):
        print("EXTRACTION INCOMPLETE: chain has %d of %d sessions -- controls not run."
              % (len(chain_sessions), len(sessions)))
        return 2

    fut_expiries, _ = L.futures_expiry_dates(fut, sessions)
    excluded = L.excluded_by_s2(fut_expiries, sessions)

    # option expiry days, by TWO independent derivations, compared (not asserted)
    by_front = {a["expiry"] for a in A.values() if a["expiry"]} & set(sessions)
    by_onafter = {d for (d, _), a in A.items() if a["exp_on_or_after"] == d}
    print("=" * 96)
    print("Part 0 step 6 -- controls C1-C4 (section 5). No outcome is computed here.")
    print("=" * 96)
    print("\noption expiry days, two independent derivations:")
    print("   front_after values that are themselves sessions: %d" % len(by_front))
    print("   sessions where exp_on_or_after == trade_date:    %d" % len(by_onafter))
    print("   symmetric difference:                            %d  %s"
          % (len(by_front ^ by_onafter), sorted(by_front ^ by_onafter)[:8]))
    opt_expiry_days = by_onafter
    idx = {d: i for i, d in enumerate(sessions)}
    e_minus_1 = {sessions[idx[e] - 1] for e in opt_expiry_days if idx.get(e, 0) > 0}
    print("   option expiry days used:                         %d" % len(opt_expiry_days))
    print("   E-1 sessions:                                    %d" % len(e_minus_1))
    print("\nfutures expiry days (section 2): %d; sessions excluded by section 2: %d"
          % (len(fut_expiries), len(excluded)))

    ok1, _ = c1_clock(fut, spot, sessions)
    ok2, _ = c2_units(fut, B, sessions, spot)
    ok3, _ = c3_gamma_parity(A, gm, excluded, opt_expiry_days)
    ok4, _ = c4_delta(B, spot, e_minus_1)

    print("\n" + "=" * 96)
    allok = ok1 and ok2 and ok3 and ok4
    for r in RESULTS:
        print("  %s  %-52s %s" % (r["id"], r["title"], "PASS" if r["passed"] else "FAIL"))
    with open(os.path.join(L.DATA, "controls.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "title", "fails_when", "passed", "measured"])
        for r in RESULTS:
            w.writerow([r["id"], r["title"], r["fails_when"], r["passed"],
                        str(r["measured"]).replace("\n", " | ")])
    if not allok:
        write_stopped()
        print("\nSTOPPED. A control failed; nothing in section 3, 4 or 7 was computed.")
        return 3
    print("\nALL CONTROLS PASS -- Part 1 may proceed.")
    return 0


def write_stopped():
    bad = [r for r in RESULTS if not r["passed"]]
    with open(os.path.join(HERE, "STOPPED.md"), "w") as fh:
        fh.write("# MR-FOI M1/M2 run STOPPED at Part 0 step 6\n\n")
        fh.write("Date (UTC): %s\n\n" % dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
        fh.write("Pre-registration section 5: \"Any control failing stops the run. "
                 "The cause is diagnosed before anything in section 3 or section 4 "
                 "is computed.\"\n\n")
        fh.write("**Nothing in section 3, 4 or 7 was computed.**\n\n")
        for r in bad:
            fh.write("## %s FAILED -- %s\n\n" % (r["id"], r["title"]))
            fh.write("**The control fails when:** %s\n\n" % r["fails_when"])
            fh.write("**Measured:**\n\n```\n%s\n```\n\n" % r["measured"])
            if r["detail"]:
                fh.write("%s\n\n" % r["detail"])
        fh.write("## Controls that passed\n\n")
        for r in RESULTS:
            if r["passed"]:
                fh.write("- %s %s\n" % (r["id"], r["title"]))


if __name__ == "__main__":
    sys.exit(main())
