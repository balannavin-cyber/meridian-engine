"""Atlas driver. Builds every row set, runs K1-K3, then studies A-D, then the
cuts ledger and the shortlist, and writes futoi_atlas_2026-11-18.md.

READ-ONLY. Exploration, not a test. Stops before any table if K1 fails.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_lib as L
import atlas_build as B
import atlas_checks as K
import atlas_studies as ST

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, "futoi_atlas_2026-11-18.md")

LINES = []


def f(s=""):
    LINES.append(s)


def limit_sessions(D, n):
    """Smoke-test mode: keep only the first n sessions, in every per-session
    dict, so the whole pipeline runs end to end on a small sample. The doc it
    writes is NOT a result -- the driver names it as a smoke test."""
    keep = set(D["sessions"][:n])
    for k in ("P", "PH", "PL", "S", "SH", "SL", "F", "F1"):
        D[k] = {d: v for d, v in D[k].items() if d in keep}
    D["sessions"] = sorted(keep)
    D["expiry_flag"] = {d: v for d, v in D["expiry_flag"].items() if d in keep}
    return D


def main():
    limit = None
    skip_k1 = "--skip-k1" in sys.argv
    for i, a in enumerate(sys.argv):
        if a == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
    # --skip-k1 is valid ONLY with --limit. A full run can never skip K1: K1 is
    # the gate that decides whether any table may be computed at all, and its
    # tolerance is sized for the full sample (it passed there at 0.543 bp and
    # fails on 20 sessions for sample size, not for the reason it names).
    if skip_k1 and not limit:
        print("REFUSING: --skip-k1 is only valid with --limit (smoke test). "
              "A full run must pass K1.")
        return 2
    D = L.load_all()
    if limit:
        D = limit_sessions(D, limit)
        print("SMOKE TEST: limited to the first %d sessions" % len(D["sessions"]))
    chain = L.load_chain_close()
    spot_close = {d: L.series_at(D["S"], d, L.CLOSE_MIN) for d in D["sessions"]}

    W = {}
    for step in (15, 30, 60):
        for oi in ("F", "F1"):
            W[(step, oi)] = ST.add_hits(B.build_windows(D, step, oi))
    DAYS = {oi: B.build_days(D, oi) for oi in ("F", "F1")}
    BASIS = B.build_basis(D)
    walls, wexc = B.build_walls(D, chain, spot_close)
    APPR = {b: B.build_approaches(D, walls, b) for b in ST.BANDS}

    ST.CTX.update({"D": D, "W": W, "DAYS": DAYS, "BASIS": BASIS,
                   "WALLS": walls, "APPR": APPR, "G": L.load_g()})

    # ---------------- K1 gate
    if skip_k1:
        print("K1 skipped (smoke test)")
    else:
        ok = K.k1(D, W[(15, "F")])
        if not ok:
            K.write_stopped()
            print("K1 FAILED -- STOPPED.md written, no table computed.")
            return 3

    # ---------------- document
    f("# Futures OI atlas — NIFTY, 2025-04-01 … 2026-03-30")
    f()
    f("Exploration. No verdict. Nothing here is a finding until confirmed once "
      "on unseen data.")
    f()
    if limit:
        f("> **SMOKE TEST — NOT A RESULT.** This document was produced on the "
          "first **%d** sessions only, to exercise the pipeline end to end. "
          "Every number in it is from that truncated sample." % len(D["sessions"]))
        f(">")
        f("> **K1 skipped (smoke test).** K1a's tolerance is sized for the full "
          "sample, where it passed at 0.543 bp; on %d sessions it fails on "
          "sample size rather than for the reason it names. No full run may skip "
          "it — `--skip-k1` is refused without `--limit`." % len(D["sessions"]))
        f()
    f("| Field | Value |")
    f("|---|---|")
    f("| Window | 2025-04-01 … 2026-03-30, **NIFTY only**. Nothing after "
      "2026-03-30 is read; the Stage 1 holdout stays sealed |")
    f("| Clock | vendor clock as-is (:59 stamps), no conversion between tables. "
      "The 15:30 bar is never used |")
    f("| Series | P = series-1 futures close · S = spot close · F = OI series "
      "1+2+3 (None if any missing) · F1 = series-1 OI |")
    f("| Expiry days | futures expiry days and the session after are **flagged, "
      "not dropped**; every table is given with and without them |")
    f("| Intervals | session-clustered percentile bootstrap of a mean, 2,000 "
      "resamples, seed 20261118. **Descriptive** — an interval excluding zero is "
      "not a test result |")
    f("| Medians | point estimates **without** an interval (READINGS R11) |")
    f("| Sessions | %d · 15-min windows %d · 30-min %d · 60-min %d · day rows "
      "%d · basis rows %d · walls %d |"
      % (len(D["sessions"]), len(W[(15, "F")]), len(W[(30, "F")]),
         len(W[(60, "F")]), len(DAYS["F"]), len(BASIS), len(walls)))
    f()
    f("Readings that resolve every open choice are in `READINGS.md`; what this "
      "run takes on trust is in `NOT_VERIFIED.md`.")
    if limit:
        f()
        f("K1 was NOT run for this document (see the banner above), so no K1 "
          "result is quoted here.")
    else:
        f()
        f("K1 ran as the gate for this document; its output is in "
          "`logs/checks_*.log` and in this run's own log.")
    f()
    f("Sessions excluded from Study D walls: %d." % len(wexc))
    for d, p, why in wexc:
        f("- %s (walls would come from %s) — %s" % (d, p, why))
    f()
    f("---")

    ST.study_a1(f)
    ST.study_a2(f)
    ST.study_a3(f)
    ST.study_b(f)
    ST.study_c(f)
    ST.study_d(f)
    f("\n---")
    # ledger() returns four totals: cells, levels-only, testable, excluding-zero
    n_cells, n_levels, n_testable, n_exczero = ST.ledger(f)
    top = ST.shortlist(f)
    f("\n---")
    f("\n*Exploration. No verdict. Nothing here is a finding until confirmed "
      "once on unseen data. Read-only run: no database write, no commit, no "
      "branch, no push. Every query through `bin/roq.sh` as `merdian_ro`; every "
      "Python process under `ulimit -v 700000`.*")

    with open(DOC, "w") as fh:
        fh.write("\n".join(LINES) + "\n")

    # ---------------- CSVs
    with open(os.path.join(HERE, "data", "cells.csv"), "w", newline="") as fh:
        keys = sorted({k for c in ST.CELLS for k in c if k != "defn"})
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for c in ST.CELLS:
            w.writerow(c)
    for name, rows in (("windows_15_F", W[(15, "F")]), ("windows_30_F", W[(30, "F")]),
                       ("windows_60_F", W[(60, "F")]), ("days_F", DAYS["F"]),
                       ("basis", BASIS)):
        if not rows:
            continue
        keys = sorted({k for r in rows for k in r})
        with open(os.path.join(HERE, "data", name + ".csv"), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
    with open(os.path.join(HERE, "data", "walls.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["trade_date", "prior", "expiry", "prior_spot", "call_wall",
                    "call_oi", "put_wall", "put_oi", "edge_call", "edge_put",
                    "call_dist_pct", "put_dist_pct"])
        for d, v in sorted(walls.items()):
            w.writerow([d] + [v[k] for k in ("prior", "expiry", "prior_spot",
                                             "call_wall", "call_oi", "put_wall",
                                             "put_oi", "edge_call", "edge_put",
                                             "call_dist_pct", "put_dist_pct")])
    for b, rows in APPR.items():
        keys = sorted({k for r in rows for k in r})
        with open(os.path.join(HERE, "data", "approaches_%.2f.csv" % b), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)

    print("cells computed: %d ; levels only: %d ; testable: %d ; "
          "intervals excluding zero: %d"
          % (n_cells, n_levels, n_testable, n_exczero))
    print("recompute failures: %s"
          % (", ".join("%s=%d" % (s, ST.RECOMPUTE_ERRORS[s])
                       for s in sorted(ST.RECOMPUTE_ERRORS)) or "none"))
    print("shortlist: %d rows" % len(top))
    print("doc: %s (%d lines)" % (DOC, len(LINES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
