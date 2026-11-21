"""Atlas supplement: collapsed shortlist, the A1 neighbourhood, and Study B's
intervals excluding zero. READ-ONLY, no database access.

Rebuilds the same row sets and re-runs the same studies in process, so every
figure here is produced by the identical code path as the main document. The
main document's own SHORTLIST is left exactly as it was written; this file adds
a SECOND table beside it.
"""
import csv
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_lib as L
import atlas_build as B
import atlas_studies as ST

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "futoi_atlas_supplement_2026-11-18.md")
LINES = []


def f(s=""):
    LINES.append(s)


def sink(s=""):
    pass


def build():
    D = L.load_all()
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
    for fn in (ST.study_a1, ST.study_a2, ST.study_a3, ST.study_b,
               ST.study_c, ST.study_d):
        fn(sink)
    return D


def collapsed_shortlist():
    """Mirrored pairs collapsed. A C1 cell with set=rest is the exact negation
    of the same cell with set=large -- the same comparison read backwards -- so
    only set=large is kept. Nothing else in the ledger is mirrored: A1/A3/C3
    pairs are already reported once each (LB vs SC, SB vs LU), and A2 holds cur
    fixed."""
    elig, dropped = [], 0
    for c in ST.CELLS:
        if not (c["excl_zero"] and c["n_sessions"] >= 20):
            continue
        if math.isnan(c["effect"]) or math.isnan(c["lo"]) or math.isnan(c["hi"]):
            continue
        hw = (c["hi"] - c["lo"]) / 2.0
        if hw <= 0:
            continue
        if c["defn"].get("set") == "rest":
            dropped += 1
            continue
        c["rank_stat"] = abs(c["effect"]) / hw
        elig.append(c)
    elig.sort(key=lambda c: -c["rank_stat"])
    f("\n## Shortlist, mirrored pairs collapsed — top 15   [exploratory]\n")
    f("The main document's SHORTLIST is unchanged. Here a C1 `set=rest` cell is "
      "dropped as the exact negation of its `set=large` twin: **%d** such "
      "mirror rows removed. Eligible cells after collapsing: **%d**.\n"
      % (dropped, len(elig)))
    f("Ranking is unchanged: |effect| ÷ half-width of its own 95 %% interval. "
      "**A shortlist drawn from many cuts is biased upward** — these are the "
      "extreme tail of %d cells and nothing here is a finding.\n" % len(ST.CELLS))
    f("| # | study | definition | outcome | n windows | n (complement) | "
      "n sessions | effect | 95% CI | |eff|/hw | F vs F1 | both halves | "
      "expiry removed |")
    f("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(elig[:15], 1):
        rob = ST.robustness(c)
        f("| %d | %s | %s | %s | %d | %d | %d | %+.3f %s | [%+.3f, %+.3f] | "
          "%.2f | %s | %s | %s |"
          % (i, c["study"], ST.fmt_defn(c["defn"]), c["outcome"], c["n"],
             c["n_comp"], c["n_sessions"], c["effect"], c["unit"],
             c["lo"], c["hi"], c["rank_stat"], rob["oi"], rob["halves"],
             rob["noexp"]))
    return elig


def a1_neighbourhood():
    """The shortlisted A1 contrast, and the same contrast across every step,
    OI series and subset, so the extreme cell is seen in context."""
    f("\n## The A1 neighbourhood of `LB vs SC`, outcome `retnext`   [exploratory]\n")
    f("The main shortlist's A1 entries are all step=60, OI=F, no-expiry, strong, "
      "LB vs SC, all day. Below: that cell's two sides counted separately, then "
      "the SAME contrast at every step, both OI series and both subsets, at "
      "strength `strong` and `all`. Effects are LB minus SC in bp.\n")
    f("| step | OI | subset | strength | n LB | sess LB | n SC | sess SC | "
      "effect (bp) | 95% CI | excl zero |")
    f("|---|---|---|---|---|---|---|---|---|---|---|")
    for step in (15, 30, 60):
        for oi in ("F", "F1"):
            for subset in ("all", "no-expiry"):
                for strength in ("strong", "all"):
                    rows, comp = ST.a1_pair(step, oi, subset, "all", strength,
                                            ("LB", "SC"), "all day")
                    r = L.boot_diff(rows, comp, "retnext")
                    nlb = sum(1 for x in rows if x.get("retnext") is not None)
                    nsc = sum(1 for x in comp if x.get("retnext") is not None)
                    slb = len({x["trade_date"] for x in rows
                               if x.get("retnext") is not None})
                    ssc = len({x["trade_date"] for x in comp
                               if x.get("retnext") is not None})
                    ez = ((r["lo"] > 0 and r["hi"] > 0)
                          or (r["lo"] < 0 and r["hi"] < 0))
                    f("| %d | %s | %s | %s | %d | %d | %d | %d | %+.3f | "
                      "[%+.3f, %+.3f] | %s |"
                      % (step, oi, subset, strength, nlb, slb, nsc, ssc,
                         r["mean"], r["lo"], r["hi"], "yes" if ez else "no"))


def study_b_exclusions():
    f("\n## Study B — every cell whose interval excludes zero   [exploratory]\n")
    rows = [c for c in ST.CELLS if c["study"] == "B" and c["excl_zero"]]
    f("%d of %d Study B cells.\n"
      % (len(rows), sum(1 for c in ST.CELLS if c["study"] == "B")))
    if not rows:
        f("*None.*")
        return
    f("| clock | subset | quintile contrast | outcome | n | sessions | "
      "effect (bp) | 95% CI |")
    f("|---|---|---|---|---|---|---|---|")
    for c in sorted(rows, key=lambda c: (c["defn"]["clock"], c["defn"]["quintile"],
                                         c["outcome"])):
        d = c["defn"]
        f("| %s | %s | Q%s vs the other four | %s | %d | %d | %+.3f | "
          "[%+.3f, %+.3f] |"
          % (d["clock"], d["subset"], d["quintile"], c["outcome"], c["n"],
             c["n_sessions"], c["effect"], c["lo"], c["hi"]))


def main():
    build()
    f("# Atlas supplement — 2026-11-18")
    f()
    f("Exploration. No verdict. Nothing here is a finding until confirmed once "
      "on unseen data.")
    f()
    f("Produced by re-running the same row builders and the same study code in "
      "process, so every figure matches the main document's code path. The main "
      "document is unchanged. Read-only; no database access.")
    f()
    f("---")
    collapsed_shortlist()
    a1_neighbourhood()
    study_b_exclusions()
    f()
    f("---")
    f()
    f("*Exploration. No verdict. Read-only run; no database write, no commit.*")
    with open(OUT, "w") as fh:
        fh.write("\n".join(LINES) + "\n")
    print("cells rebuilt: %d" % len(ST.CELLS))
    print("recompute failures: %s"
          % (", ".join("%s=%d" % (s, ST.RECOMPUTE_ERRORS[s])
                       for s in sorted(ST.RECOMPUTE_ERRORS)) or "none"))
    print("wrote %s (%d lines)" % (OUT, len(LINES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
