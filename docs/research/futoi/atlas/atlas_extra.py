"""Four follow-up tables. READ-ONLY, no database access. Exploratory.

1. A1 LB vs SC on retnext, steps 60 and 30, F, no-expiry, at strength strong
   and all: each side's mean same-session return to close and mean |dP|; then
   the LB-minus-SC contrast WITHIN terciles of same-session return to close, so
   the two sides are matched on move size.
2. The mirror: SB vs LU on retnext over the same 24-cell grid
   (step x OI series x subset x strength).
3. A3 day level: LB vs SC and SB vs LU on next-session return, both subsets,
   with n days.
4. Study B: Spearman of dev against calendar date at each clock; and the Q1 /
   Q4 / Q5 rng_next contrasts split by half-year with n sessions.
"""
import csv
import datetime as dt
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_lib as L
import atlas_build as B
import atlas_studies as ST

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "futoi_atlas_extra_2026-11-18.md")
LINES = []
H1 = ST.H1
H2 = ST.H2


def f(s=""):
    LINES.append(s)


def mean(rows, key):
    v = [r[key] for r in rows if r.get(key) is not None]
    return float(np.mean(v)) if v else float("nan")


def build():
    D = L.load_all()
    W = {}
    for step in (15, 30, 60):
        for oi in ("F", "F1"):
            W[(step, oi)] = ST.add_hits(B.build_windows(D, step, oi))
    DAYS = {oi: B.build_days(D, oi) for oi in ("F", "F1")}
    BASIS = B.build_basis(D)
    ST.CTX.update({"D": D, "W": W, "DAYS": DAYS, "BASIS": BASIS})
    return D


# ------------------------------------------------------------------ item 1
def item1():
    f("\n## 1. A1 `LB vs SC` on `retnext`, matched on move size   [exploratory]\n")
    f("Steps 60 and 30, OI = F, subset = no-expiry. First each side's own mean "
      "same-session return to close (`retclose`, bp) and mean |dP| (index "
      "points), so the two sides' move sizes are visible. Then the LB-minus-SC "
      "contrast computed **within terciles of `retclose`**, the terciles cut on "
      "the pooled LB∪SC rows of that cell.\n")
    f("### Side profiles\n")
    f("| step | strength | side | n | sessions | mean retclose (bp) | "
      "mean \\|dP\\| (pts) |")
    f("|---|---|---|---|---|---|---|")
    for step in (60, 30):
        for strength in ("strong", "all"):
            rows, comp = ST.a1_pair(step, "F", "no-expiry", "all", strength,
                                    ("LB", "SC"), "all day")
            for nm, rs in (("LB", rows), ("SC", comp)):
                rs2 = [r for r in rs if r.get("retnext") is not None]
                f("| %d | %s | %s | %d | %d | %+.3f | %.2f |"
                  % (step, strength, nm, len(rs2),
                     len({r["trade_date"] for r in rs2}),
                     mean(rs2, "retclose"),
                     float(np.mean([abs(r["dP"]) for r in rs2 if r["dP"] is not None]))
                     if rs2 else float("nan")))
    f("\n### LB minus SC within terciles of same-session return to close\n")
    f("| step | strength | tercile of retclose | retclose range (bp) | n LB | "
      "n SC | sessions | effect (bp) | 95% CI | excl zero |")
    f("|---|---|---|---|---|---|---|---|---|---|")
    for step in (60, 30):
        for strength in ("strong", "all"):
            rows, comp = ST.a1_pair(step, "F", "no-expiry", "all", strength,
                                    ("LB", "SC"), "all day")
            pool = [r for r in rows + comp
                    if r.get("retclose") is not None and r.get("retnext") is not None]
            cuts = L.quantile_cuts([r["retclose"] for r in pool], 3)
            for t in range(3):
                lb = [r for r in rows if r.get("retclose") is not None
                      and L.bucket(r["retclose"], cuts) == t]
                sc = [r for r in comp if r.get("retclose") is not None
                      and L.bucket(r["retclose"], cuts) == t]
                lo = "-inf" if t == 0 else "%+.1f" % cuts[t - 1]
                hi = "+inf" if t == 2 else "%+.1f" % cuts[t]
                if not lb or not sc:
                    f("| %d | %s | T%d | %s .. %s | %d | %d | — | — | — | — |"
                      % (step, strength, t + 1, lo, hi, len(lb), len(sc)))
                    continue
                b = L.boot_diff(lb, sc, "retnext")
                ez = ((b["lo"] > 0 and b["hi"] > 0) or (b["lo"] < 0 and b["hi"] < 0))
                f("| %d | %s | T%d | %s .. %s | %d | %d | %d | %+.3f | "
                  "[%+.3f, %+.3f] | %s |"
                  % (step, strength, t + 1, lo, hi, b["n"], b["n_b"],
                     b["n_sessions"], b["mean"], b["lo"], b["hi"],
                     "yes" if ez else "no"))


# ------------------------------------------------------------------ item 2
def item2():
    f("\n## 2. The mirror: `SB vs LU` on `retnext`, full grid   [exploratory]\n")
    f("Same 24-cell grid as the `LB vs SC` neighbourhood: step × OI series × "
      "subset × strength. Effects are SB minus LU in bp.\n")
    f("| step | OI | subset | strength | n SB | sess SB | n LU | sess LU | "
      "effect (bp) | 95% CI | excl zero |")
    f("|---|---|---|---|---|---|---|---|---|---|---|")
    for step in (15, 30, 60):
        for oi in ("F", "F1"):
            for subset in ("all", "no-expiry"):
                for strength in ("strong", "all"):
                    rows, comp = ST.a1_pair(step, oi, subset, "all", strength,
                                            ("SB", "LU"), "all day")
                    b = L.boot_diff(rows, comp, "retnext")
                    nsb = sum(1 for r in rows if r.get("retnext") is not None)
                    nlu = sum(1 for r in comp if r.get("retnext") is not None)
                    ssb = len({r["trade_date"] for r in rows
                               if r.get("retnext") is not None})
                    slu = len({r["trade_date"] for r in comp
                               if r.get("retnext") is not None})
                    ez = ((b["lo"] > 0 and b["hi"] > 0)
                          or (b["lo"] < 0 and b["hi"] < 0))
                    f("| %d | %s | %s | %s | %d | %d | %d | %d | %+.3f | "
                      "[%+.3f, %+.3f] | %s |"
                      % (step, oi, subset, strength, nsb, ssb, nlu, slu,
                         b["mean"], b["lo"], b["hi"], "yes" if ez else "no"))


# ------------------------------------------------------------------ item 3
def item3():
    f("\n## 3. A3 day level — both pairs on next-session return   [exploratory]\n")
    f("Class from close-to-close dP and dOI; the outcome is the next session's "
      "return in bp. Effects are the first class minus the second.\n")
    f("| OI | subset | contrast | n days | n comp days | sessions | "
      "effect (bp) | 95% CI | excl zero |")
    f("|---|---|---|---|---|---|---|---|---|")
    for oi in ("F", "F1"):
        for subset in ("all", "no-expiry"):
            rows = ST.sub(ST.CTX["DAYS"][oi], subset)
            for pair in (("LB", "SC"), ("SB", "LU")):
                a = [r for r in rows if r["cls"] == pair[0]]
                c = [r for r in rows if r["cls"] == pair[1]]
                b = L.boot_diff(a, c, "retnext")
                ez = ((b["lo"] > 0 and b["hi"] > 0)
                      or (b["lo"] < 0 and b["hi"] < 0))
                f("| %s | %s | %s vs %s | %d | %d | %d | %+.3f | "
                  "[%+.3f, %+.3f] | %s |"
                  % (oi, subset, pair[0], pair[1], b["n"], b["n_b"],
                     b["n_sessions"], b["mean"], b["lo"], b["hi"],
                     "yes" if ez else "no"))


# ------------------------------------------------------------------ item 4
def item4():
    f("\n## 4. Study B — dev against calendar date, and half-year splits   [exploratory]\n")
    f("### Spearman of `dev` against calendar date, per clock\n")
    f("Date as its ordinal. Descriptive rank association; no p-value.\n")
    f("| clock | subset | n | Spearman ρ (dev vs date) |")
    f("|---|---|---|---|")
    basis = ST.CTX["BASIS"]
    for subset in ("all", "no-expiry"):
        rows = ST.sub(basis, subset)
        for m in B.CLOCKS:
            rs = [r for r in rows if r["clock_min"] == m and r["dev"] is not None]
            x = [dt.date.fromisoformat(r["trade_date"]).toordinal() for r in rs]
            y = [r["dev"] for r in rs]
            f("| %s | %s | %d | %+.4f |" % (L.lbl(m), subset, len(rs),
                                            L.spearman(x, y)))
    f("\n### Q1 / Q4 / Q5 `rng_next` contrasts by half-year\n")
    f("Quintiles of `dev` are cut **within each half-year**, so a quintile is "
      "relative to its own period. Effect is that quintile minus the other four "
      "in the same half-year, in bp.\n")
    f("| half-year | clock | subset | quintile | n | sessions | effect (bp) | "
      "95% CI | excl zero |")
    f("|---|---|---|---|---|---|---|---|---|")
    for hname, half in (("Apr–Sep 2025", "H1"), ("Oct 2025–Mar 2026", "H2")):
        for subset in ("all", "no-expiry"):
            rows = ST.sub(basis, subset, half)
            for m in B.CLOCKS:
                rs = [r for r in rows if r["clock_min"] == m and r["dev"] is not None]
                if len(rs) < 10:
                    continue
                cuts = L.quantile_cuts([r["dev"] for r in rs], 5)
                for q in (0, 3, 4):
                    qq = [r for r in rs if L.bucket(r["dev"], cuts) == q]
                    comp = [r for r in rs if L.bucket(r["dev"], cuts) != q]
                    if not qq or not comp:
                        continue
                    b = L.boot_diff(qq, comp, "rng_next")
                    ez = ((b["lo"] > 0 and b["hi"] > 0)
                          or (b["lo"] < 0 and b["hi"] < 0))
                    f("| %s | %s | %s | Q%d | %d | %d | %+.3f | "
                      "[%+.3f, %+.3f] | %s |"
                      % (hname, L.lbl(m), subset, q + 1, b["n"],
                         b["n_sessions"], b["mean"], b["lo"], b["hi"],
                         "yes" if ez else "no"))


def main():
    build()
    f("# Atlas follow-ups — 2026-11-18")
    f()
    f("Exploration. No verdict. Nothing here is a finding until confirmed once "
      "on unseen data.")
    f()
    f("Read-only; no database access. Same row builders and the same "
      "session-clustered percentile bootstrap (%d resamples, seed %d) as the "
      "main document. Intervals are descriptive." % (L.B_RESAMPLES, L.SEED))
    f()
    f("---")
    item1()
    item2()
    item3()
    item4()
    f()
    f("---")
    f()
    f("*Exploration. No verdict. Read-only; no database write, no commit.*")
    with open(OUT, "w") as fh:
        fh.write("\n".join(LINES) + "\n")
    print("wrote %s (%d lines)" % (OUT, len(LINES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
