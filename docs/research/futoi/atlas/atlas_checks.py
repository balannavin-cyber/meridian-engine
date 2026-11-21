"""K1-K3, run BEFORE any atlas table. READ-ONLY.

K1 planted signal  -- each half must be able to fail:
    K1a outcomes shuffled ACROSS sessions -> every class's continuation should
        collapse toward zero. It fails if a shuffled table still shows a class
        effect, which would mean the class tables are reading something other
        than the pairing of class with outcome.
    K1b +5 bp added to LB rows only -> A1 must recover about +5 bp on LB and
        about nothing elsewhere. It fails if the planted size does not come
        back on LB, or if it leaks into SC/SB/LU, which would mean the class
        assignment and the aggregation disagree.
K2 Stage 1 cross-check -- print, do not tune.
K3 Lookahead -- one fully worked row per study, every timestamp shown.

If K1 fails the run stops and atlas/STOPPED.md is written.
"""
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_lib as L
import atlas_build as B

STAGE1_NIFTY_BP = -0.35      # the Stage 1 figure, quoted for comparison only
FAILED = []


def _mean(rows, key):
    v = [r[key] for r in rows if r.get(key) is not None]
    return float(np.mean(v)) if v else float("nan")


def k1(D, windows):
    print("=" * 96)
    print("K1  planted signal")
    print("=" * 96)
    base = [r for r in windows if r["cls"] in L.REAL_CLASSES and r["cont30"] is not None]
    print("\nrows with a real class and a 30-min continuation: %d over %d sessions"
          % (len(base), len({r['trade_date'] for r in base})))

    print("\n--- K1a  outcomes shuffled ACROSS sessions ---")
    print("    must: every class collapses toward zero. Fails if a class keeps an effect.")
    rng = random.Random(L.SEED)
    vals = [r["cont30"] for r in base]
    shuf = vals[:]
    rng.shuffle(shuf)
    sh = [dict(r, cont30=v) for r, v in zip(base, shuf)]
    print("    %-8s %8s %12s %12s" % ("class", "n", "observed bp", "shuffled bp"))
    worst = 0.0
    for c in L.REAL_CLASSES:
        o = _mean([r for r in base if r["cls"] == c], "cont30")
        s = _mean([r for r in sh if r["cls"] == c], "cont30")
        n = sum(1 for r in base if r["cls"] == c)
        print("    %-8s %8d %12.3f %12.3f" % (c, n, o, s))
        worst = max(worst, abs(s))
    grand = _mean(base, "cont30")
    print("    grand mean of the pool (the shuffle preserves it): %.3f bp" % grand)
    print("    largest |shuffled class mean - grand mean|: %.3f bp"
          % max(abs(_mean([r for r in sh if r["cls"] == c], "cont30") - grand)
                for c in L.REAL_CLASSES))
    ok_a = max(abs(_mean([r for r in sh if r["cls"] == c], "cont30") - grand)
               for c in L.REAL_CLASSES) < 1.0
    print("    -> %s" % ("collapsed as required" if ok_a else "DID NOT COLLAPSE"))
    if not ok_a:
        FAILED.append("K1a")

    print("\n--- K1b  +5 bp planted on LB rows only ---")
    print("    must: LB recovers about +5 bp above its own baseline, others move ~0.")
    planted = [dict(r, cont30=(r["cont30"] + 5.0 if r["cls"] == "LB" else r["cont30"]))
               for r in base]
    print("    %-8s %8s %12s %12s %10s" % ("class", "n", "before bp", "after bp", "delta bp"))
    ok_b = True
    for c in L.REAL_CLASSES:
        o = _mean([r for r in base if r["cls"] == c], "cont30")
        p = _mean([r for r in planted if r["cls"] == c], "cont30")
        n = sum(1 for r in base if r["cls"] == c)
        print("    %-8s %8d %12.3f %12.3f %10.3f" % (c, n, o, p, p - o))
        if c == "LB" and abs((p - o) - 5.0) > 0.01:
            ok_b = False
        if c != "LB" and abs(p - o) > 0.01:
            ok_b = False
    print("    -> %s" % ("recovered on LB only, as required" if ok_b else "NOT RECOVERED"))
    if not ok_b:
        FAILED.append("K1b")
    return ok_a and ok_b


def k2(D, w15):
    print("\n" + "=" * 96)
    print("K2  Stage 1 cross-check -- printed beside, NOT tuned to match")
    print("=" * 96)
    rows = [r for r in w15 if r["cont30"] is not None]
    lb = [r for r in rows if r["cls"] == "LB"]
    sb = [r for r in rows if r["cls"] == "SB"]
    # the raw 30-min forward return, not the continuation, so the sign is price
    mlb = _mean(lb, "ret30")
    msb = _mean(sb, "ret30")
    print("\n15-minute windows, 30-minute forward return on P:")
    print("    LB mean        %+8.4f bp   (n=%d, %d sessions)"
          % (mlb, len(lb), len({r['trade_date'] for r in lb})))
    print("    SB mean        %+8.4f bp   (n=%d, %d sessions)"
          % (msb, len(sb), len({r['trade_date'] for r in sb})))
    print("    LB minus SB    %+8.4f bp" % (mlb - msb))
    print("    Stage 1 figure %+8.4f bp   (NIFTY, as supplied)" % STAGE1_NIFTY_BP)
    print("    difference     %+8.4f bp" % ((mlb - msb) - STAGE1_NIFTY_BP))
    print("""
    Definitional differences that could account for any gap, stated before the
    numbers were read and NOT adjusted to close it:
      * window length. This is a 15-minute classification window; Stage 1's
        class window length is not restated in this run's inputs.
      * OI series. Here dOI is F = series 1+2+3. A series-1-only class (F1) is
        a different partition; both are run and both are reported.
      * outcome horizon. Here 30 minutes forward from the window END. A horizon
        measured from the window start, or over the window itself, differs.
      * sample. This is 247 sessions with futures expiry days FLAGGED, not
        dropped; Stage 1's exclusions are not restated here.
      * price series. P is the series-1 futures close, not spot.
    No parameter was changed to move this number.""")


def k3(D, w15, days, basis, walls, appr):
    print("\n" + "=" * 96)
    print("K3  lookahead -- one fully worked row per study, every timestamp")
    print("=" * 96)
    print("\nInvariant: cond_ts <= out_ts, and the first forward increment runs")
    print("from out_ts to the next minute, so no conditioning minute lies inside")
    print("any outcome. build_windows() asserts this on every row.")

    r = next(r for r in w15 if r["cls"] in L.REAL_CLASSES and r["ret30"] is not None
             and r["dOI"] is not None)
    print("\n--- STUDY A1 (15-minute window) ---")
    print("    session                 %s" % r["trade_date"])
    print("    window start bar        %s   P=%.2f" % (r["win_start"], r["P_start"]))
    print("    window end bar          %s   P=%.2f" % (r["win_end"], r["P_end"]))
    print("    dP  = P(end)-P(start)   %+.2f index points" % r["dP"])
    print("    dOI = F(end)-F(start)   %+.0f index units  [F = series 1+2+3]" % r["dOI"])
    print("    class                   %s" % r["cls"])
    print("    cond_ts (last input)    %s %s" % (r["trade_date"], r["cond_ts"]))
    print("    out_ts  (outcome from)  %s %s" % (r["trade_date"], r["out_ts"]))
    print("    ret30 reads P at        %s  -> %+.3f bp"
          % (L.lbl(r["end_min"] + 30), r["ret30"]))
    print("    continuation = sign(dP) x ret30 = %+.3f bp" % r["cont30"])
    print("    FIRST outcome minute is %s, strictly after cond_ts %s"
          % (L.lbl(r["end_min"] + 1), r["cond_ts"]))

    dr = next(x for x in days if x["cls"] in L.REAL_CLASSES and x["retnext"] is not None)
    print("\n--- STUDY A3 (day level) ---")
    print("    session d               %s   prior %s   next %s"
          % (dr["trade_date"], dr["prev"], dr["next"]))
    print("    dP  close(d)-close(prior)  %+.2f index points" % dr["dP"])
    print("    dOI close(d)-close(prior)  %+.0f index units" % dr["dOI"])
    print("    class                   %s   run length %s" % (dr["cls"], dr["run_bucket"]))
    print("    cond_ts                 %s" % dr["cond_ts"])
    print("    out_ts                  %s" % dr["out_ts"])
    print("    outcome reads close at  %s 15:29:59 -> %+.3f bp"
          % (dr["next"], dr["retnext"]))

    br = next(x for x in basis if x["dev"] is not None and x["ret_to_close"] is not None)
    print("\n--- STUDY B (basis deviation) ---")
    print("    session                 %s  clock %s" % (br["trade_date"], br["clock"]))
    print("    b = (P-S)/S             %+.3f bp" % br["b"])
    print("    days to series-1 expiry %s   cycle %s" % (br["dte"], br["cycle"]))
    print("    norm = median b at same (dte, clock), OWN CYCLE LEFT OUT")
    print("                            %+.3f bp over %d other-cycle observations"
          % (br["norm"], br["norm_n"]))
    print("    dev = b - norm          %+.3f bp" % br["dev"])
    print("    cond_ts                 %s" % br["cond_ts"])
    print("    out_ts                  %s" % br["out_ts"])
    print("    ret to close reads      %s 15:29:59 -> %+.3f bp"
          % (br["trade_date"], br["ret_to_close"]))

    ar = next((x for x in appr if x.get("approached") and x.get("outcome")), None)
    print("\n--- STUDY D (wall approach) ---")
    if ar is None:
        print("    no approach row available at this band")
    else:
        w = walls[ar["trade_date"]]
        print("    session                 %s" % ar["trade_date"])
        print("    walls fixed from        %s 15:29:59 (PRIOR session close)" % w["prior"])
        print("    front expiry            %s   prior spot close %.2f"
              % (w["expiry"], w["prior_spot"]))
        print("    %s wall                %.0f   (%.2f%% from prior spot, edge=%s)"
              % (ar["side"], ar["wall"], ar["wall_dist_pct"], ar["edge"]))
        print("    approach minute         %s  (first minute S within %.2f%% from inside)"
              % (ar["approach_ts"], ar["band_pct"]))
        print("    cond_ts                 %s" % ar["cond_ts"])
        print("    dF  over the 30 min BEFORE the approach  %s"
              % ("%+.0f" % ar["dF_30"] if ar.get("dF_30") is not None else "n/a"))
        print("    dF1 over the 30 min BEFORE the approach  %s"
              % ("%+.0f" % ar["dF1_30"] if ar.get("dF1_30") is not None else "n/a"))
        print("    out_ts                  %s" % ar["out_ts"])
        print("    outcome read at         %s 15:29:59 -> %s (%.3f%% beyond)"
              % (ar["trade_date"], ar["outcome"], ar["final_beyond_pct"]))
        print("    the conditioning window ENDS at the approach minute; the")
        print("    outcome runs from that same minute forward.")


def write_stopped():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "STOPPED.md"), "w") as fh:
        fh.write("# Atlas STOPPED at K1\n\n")
        fh.write("K1 (planted signal) failed: %s\n\n" % ", ".join(FAILED))
        fh.write("No atlas table was computed.\n")


def main():
    D = L.load_all()
    chain = L.load_chain_close()
    spot_close = {d: L.series_at(D["S"], d, L.CLOSE_MIN) for d in D["sessions"]}
    w15 = B.build_windows(D, 15, "F")
    days = B.build_days(D, "F")
    basis = B.build_basis(D)
    walls, wexc = B.build_walls(D, chain, spot_close)
    appr = B.build_approaches(D, walls, 0.15)

    print("inputs: %d sessions, %d 15-min windows, %d day rows, %d basis rows, "
          "%d walls (%d sessions excluded from walls)"
          % (len(D["sessions"]), len(w15), len(days), len(basis), len(walls), len(wexc)))
    for d, p, why in wexc:
        print("   wall excluded: d=%s prior=%s -- %s" % (d, p, why))

    ok = k1(D, w15)
    k2(D, w15)
    k3(D, w15, days, basis, walls, appr)
    print("\n" + "=" * 96)
    if not ok:
        write_stopped()
        print("K1 FAILED -- atlas/STOPPED.md written, no table computed.")
        return 3
    print("K1 PASSED. K2 and K3 printed. No atlas table has been computed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
