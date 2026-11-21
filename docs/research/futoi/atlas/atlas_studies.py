"""Studies A-D. READ-ONLY. EXPLORATION, not a test.

No verdict, no threshold passed or failed, nothing called significant.

EFFECT DEFINITION (operator ruling 2026-11-18, revised the same day).
  * **Every** cell effect is the DIFFERENCE between the condition and its
    COMPLEMENT in the same table, with a session-clustered bootstrap of the
    difference -- signed forward returns and continuations included.
  * The first version of this rule applied differencing only to unsigned
    outcomes and read signed returns as levels against zero. The 20-session
    smoke test then showed **1,340 of 5,546 intervals excluding zero (24 %
    against 5 %)**, because a level-vs-zero interval on a forward return is
    dominated by the sample's own market drift, which every class inherits
    equally. The count was measuring the drift, not the partition. Differencing
    cancels the common term.
  * Raw levels are still printed for every cell, beside the difference and
    marked "level, not an effect". They are never tested against zero.
  * `excl_zero`, the ledger's testable count and the shortlist use ONLY
    differences. A cell with no complement is a level and enters none of them.

Complements used, each the natural "everything else" within the same table:
  A1  the paired class at the SAME price sign: LB vs SC (both dP>0), SB vs LU
      (both dP<0), same step/OI/subset/strength/time-of-day. Each pair once.
  A2  the other transitions INTO THE SAME cur: same current class, a
      different previous class, real classes only (cur held fixed)
  A3  class: the paired class at the same price sign (LB vs SC, SB vs LU);
      runs: the same class's other run lengths
  B   the other dev quintiles at the same clock
  C1  large set vs rest (the complement is the comparison itself)
  C2  large set vs rest
  C3  the paired class at the same price sign, within the large-window set
  D   the complementary condition: F rising vs F falling, a tercile vs the other
      two. The unconditional "all" row has no complement and is printed as a
      level only.
"""
import csv
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import atlas_lib as L
import atlas_build as B

HERE = os.path.dirname(os.path.abspath(__file__))
H1 = ("2025-04-01", "2025-09-30")
H2 = ("2025-10-01", "2026-03-30")
BANDS = [0.10, 0.15, 0.25]
FWD = ["ret30", "ret60", "retclose", "retnext", "rng60", "rngclose"]
CONT = ["cont30", "cont60", "contclose", "contnext"]
HIT = ["hit30", "hit60", "hitclose", "hitnext"]

# Class contrasts hold the PRICE SIGN FIXED (operator ruling 2026-11-18).
# LB and SC both have dP>0 and differ only in the sign of dOI; SB and LU both
# have dP<0. Differencing a class against a complement that mixes dP signs
# measures an up-window/down-window asymmetry instead of anything about OI.
# SC vs LB and LU vs SB are the same contrasts with the sign flipped, so each
# pair is reported ONCE.
PAIRS = [("LB", "SC"), ("SB", "LU")]

CELLS = []
CTX = {}
RECOMPUTE_ERRORS = {}        # study -> failure COUNT (ints only; printed with %d)
RECOMPUTE_LAST = {}          # study -> last exception repr (strings; log only)


def unit_of(o):
    if o.startswith("hit") or o == "break_rate":
        return "rate"
    if o == "max_excursion_pct":
        return "%"
    return "bp"


def cell(study, table, defn, rows, outcome, comp=None, note=""):
    """One cell.

    EFFECT = THE DIFFERENCE AGAINST THE COMPLEMENT, FOR EVERY OUTCOME
    (operator ruling 2026-11-18, revised). Signed forward returns are included.
    A level-vs-zero interval on a forward return is dominated by the sample's
    own market drift, which EVERY class inherits, so levels exclude zero
    together and the count of exclusions measures the drift rather than the
    partition. Differencing against the complement cancels the common term.

    `comp` is required. Without it the cell is recorded as a LEVEL ONLY: it is
    printed, marked "level, not an effect", and excluded from `excl_zero`, from
    the ledger's testable count and from the shortlist.

    The raw level is always carried beside the difference, as a level."""
    if comp is not None:
        r = L.boot_diff(rows, comp, outcome)
        c = {"effect": r["mean"], "median": float("nan"), "lo": r["lo"], "hi": r["hi"],
             "n": r["n"], "n_comp": r["n_b"], "n_sessions": r["n_sessions"],
             "level": r["level_a"], "level_comp": r["level_b"],
             "kind": "difference vs complement"}
    else:
        r = L.boot_mean(rows, outcome)
        c = {"effect": r["mean"], "median": r["median"], "lo": float("nan"),
             "hi": float("nan"), "n": r["n"], "n_comp": 0,
             "n_sessions": r["n_sessions"],
             "level": r["mean"], "level_comp": float("nan"),
             "kind": "level, not an effect"}
    c.update({"study": study, "table": table, "outcome": outcome,
              "unit": unit_of(outcome), "note": note,
              "excl_zero": (L.excludes_zero(c) and c["kind"] != "level, not an effect"),
              "shortlistable": c["kind"] != "level, not an effect"})
    c.update({"d_" + k: v for k, v in defn.items()})
    c["defn"] = defn
    CELLS.append(c)
    return c


def add_hits(rows):
    for r in rows:
        for h, cn in zip(HIT, CONT):
            v = r.get(cn)
            r[h] = None if v is None else (1.0 if v > 0 else 0.0)
    return rows


def sub(rows, subset="all", half="all"):
    out = rows
    if subset == "no-expiry":
        out = [r for r in out if not r.get("expiry_flag")]
    if half == "H1":
        out = [r for r in out if H1[0] <= r["trade_date"] <= H1[1]]
    elif half == "H2":
        out = [r for r in out if H2[0] <= r["trade_date"] <= H2[1]]
    return out


def show(c):
    """One table row for a cell: effect (a difference), its interval, then the
    two raw levels, which are levels and not effects."""
    if c["kind"] == "difference vs complement":
        return ("%+.3f %s | [%+.3f, %+.3f] | %.3f vs %.3f | difference"
                % (c["effect"], c["unit"], c["lo"], c["hi"], c["level"], c["level_comp"]))
    return "%+.3f %s | — | — | level, not an effect" % (c["effect"], c["unit"])


HDR = ("| n | sessions | outcome | effect (diff vs complement) | 95% CI | "
       "levels: cell vs comp (not effects) | kind |")
SEP = "|---|---|---|---|---|---|---|"


# =============================================================== STUDY A
def a1_rows(step, oi, subset, half, strength, cls, tod):
    rows = sub(CTX["W"][(step, oi)], subset, half)
    if strength == "strong":
        rows = [r for r in rows if r.get("strong")]
    if tod != "all day":
        rows = [r for r in rows if r["tod"] == tod]
    if cls != "all":
        rows = [r for r in rows if r["cls"] == cls]
    return rows


def a1_pair(step, oi, subset, half, strength, pair, tod):
    """(rows, comp) for one price-sign-matched pair, e.g. LB vs SC."""
    a, b = pair
    return (a1_rows(step, oi, subset, half, strength, a, tod),
            a1_rows(step, oi, subset, half, strength, b, tod))


def study_a1(f):
    f("\n## A1 — class anatomy over non-overlapping windows   [exploratory]\n")
    f("Windows of 15 / 30 / 60 minutes from 09:15, full grid windows only "
      "(24 / 12 / 6 per session; the ragged 15:15–15:29 tail is not a window). "
      "dP and dOI are measured start→end; the outcome starts at the window end. "
      "FLAT (a measured zero) and MISSING (uncomputable) are counted separately "
      "and never merged into a class.\n")
    f("Contrasts hold the **price sign fixed**: **LB vs SC** (both dP>0) and "
      "**SB vs LU** (both dP<0), so the difference isolates the sign of dOI "
      "rather than an up-window/down-window asymmetry. SC vs LB and LU vs SB "
      "are the same contrasts with the sign flipped and are not repeated.\n")
    f("### A1.0 Composition — every class counted, including FLAT and MISSING\n")
    f("| step | OI | subset | " + " | ".join(L.CLASSES) + " | total |")
    f("|---|---|---|" + "---|" * (len(L.CLASSES) + 1))
    for step in (15, 30, 60):
        for oi in ("F", "F1"):
            for subset in ("all", "no-expiry"):
                rows = sub(CTX["W"][(step, oi)], subset)
                counts = [sum(1 for r in rows if r["cls"] == c) for c in L.CLASSES]
                f("| %d | %s | %s | %s | %d |"
                  % (step, oi, subset, " | ".join(str(x) for x in counts), len(rows)))
    f("")
    for step in (15, 30, 60):
        for oi in ("F", "F1"):
            for strength in ("all", "strong"):
                for subset in ("all", "no-expiry"):
                    f("\n### A1 step=%d min · OI=%s · %s windows · %s   [exploratory]\n"
                      % (step, oi, strength, subset))
                    f("| contrast | time of day " + HDR[1:])
                    f("|---|---" + SEP[1:])
                    for pair in PAIRS:
                        nm = "%s vs %s" % pair
                        for tod in L.TOD:
                            rows, comp = a1_pair(step, oi, subset, "all",
                                                 strength, pair, tod)
                            d = {"step": step, "oi": oi, "subset": subset,
                                 "strength": strength, "pair": nm, "tod": tod}
                            for o in FWD + CONT + HIT:
                                c = cell("A1", "A1", d, rows, o, comp=comp)
                                if o in ("cont30", "rng60", "hit30") and c["n"]:
                                    f("| %s | %s | %d | %d | %s | %s |"
                                      % (nm, tod, c["n"], c["n_sessions"], o, show(c)))
                    f("\n*Each row is the first class of the pair MINUS the second, "
                      "both at the same price sign. Printed: cont30, rng60, hit30; "
                      "all %d outcomes per cell are computed and in "
                      "`data/cells.csv`.*" % len(FWD + CONT + HIT))


def study_a2(f):
    f("\n## A2 — transitions between consecutive windows   [exploratory]\n")
    f("The previous window's class against the current one, and the **next** "
      "window's 30-minute continuation in bp (signed, so the effect is the "
      "level). SC → LB and LU → SB are called out below each table.\n")
    for step in (15, 30, 60):
        for oi in ("F", "F1"):
            for subset in ("all", "no-expiry"):
                pairs = a2_pairs(step, oi, subset, "all")
                f("\n### A2 step=%d min · OI=%s · %s   [exploratory]\n" % (step, oi, subset))
                f("Effect is the pair's next-window cont30 **minus the other "
                  "transitions into the same `cur`** — current class held fixed, "
                  "previous class varied — so the contrast isolates what the "
                  "previous class adds, and the sample's drift cancels.\n")
                f("| prev → cur " + HDR[1:])
                f("|---" + SEP[1:])
                for p in L.REAL_CLASSES:
                    for q in L.REAL_CLASSES:
                        rs = [x for x in pairs if x["prev"] == p and x["cur"] == q]
                        comp = a2_comp(pairs, p, q)
                        c = cell("A2", "A2", {"step": step, "oi": oi, "subset": subset,
                                              "prev": p, "cur": q}, rs, "nxt_cont30",
                                 comp=comp)
                        if c["n"]:
                            f("| %s → %s | %d | %d | %s | %s |"
                              % (p, q, c["n"], c["n_sessions"], "nxt_cont30", show(c)))
                for p, q in (("SC", "LB"), ("LU", "SB")):
                    rs = [x for x in pairs if x["prev"] == p and x["cur"] == q]
                    r = L.boot_diff(rs, a2_comp(pairs, p, q), "nxt_cont30")
                    f("\n**%s → %s**: n=%d over %d sessions. Next-window cont30 "
                      "**%+.3f bp against other transitions into %s**, 95%% CI "
                      "[%+.3f, %+.3f]. Raw levels %.3f vs %.3f bp (levels, not "
                      "effects)."
                      % (p, q, r["n"], r["n_sessions"], r["mean"], q,
                         r["lo"], r["hi"], r["level_a"], r["level_b"]))


def a2_comp(pairs, p, q):
    """Complement for a transition cell: the other transitions INTO THE SAME
    `cur` -- same current class, a different previous class, real classes only.

    `cur` is held FIXED (operator ruling 2026-11-18). The first version let cur
    vary too, which mixed the current class's own effect into a contrast meant
    to isolate what the PREVIOUS class adds. Holding cur fixed makes the cell
    answer one question: given the window is now `cur`, does it matter what it
    was before?"""
    return [x for x in pairs
            if x["cur"] == q and x["prev"] in L.REAL_CLASSES and x["prev"] != p]


def a2_pairs(step, oi, subset, half):
    rows = sub(CTX["W"][(step, oi)], subset, half)
    bys = {}
    for r in rows:
        bys.setdefault(r["trade_date"], []).append(r)
    out = []
    for d, rs in bys.items():
        rs = sorted(rs, key=lambda x: x["end_min"])
        for i in range(1, len(rs) - 1):
            out.append({"trade_date": d, "prev": rs[i - 1]["cls"], "cur": rs[i]["cls"],
                        "nxt_cont30": rs[i + 1].get("cont30"),
                        "expiry_flag": rs[i]["expiry_flag"]})
    return out


def study_a3(f):
    f("\n## A3 — day level   [exploratory]\n")
    f("Class from close-to-close dP and dOI; the outcome is the **next** "
      "session. Every effect is a difference against the PAIRED class at the "
      "same price sign (LB vs SC, SB vs LU).\n")
    for oi in ("F", "F1"):
        for subset in ("all", "no-expiry"):
            rows = sub(CTX["DAYS"][oi], subset)
            f("\n### A3 OI=%s · %s   [exploratory]\n" % (oi, subset))
            f("Composition (counts only): %s\n"
              % " · ".join("%s %d" % (c, sum(1 for r in rows if r["cls"] == c))
                           for c in L.CLASSES))
            f("Contrasts hold the price sign fixed: LB vs SC, SB vs LU.\n")
            f("| contrast " + HDR[1:])
            f("|---" + SEP[1:])
            for pair in PAIRS:
                nm = "%s vs %s" % pair
                rs = [r for r in rows if r["cls"] == pair[0]]
                comp = [r for r in rows if r["cls"] == pair[1]]
                for o in ("retnext", "contnext", "rngnext"):
                    c = cell("A3", "A3-class", {"oi": oi, "subset": subset, "pair": nm},
                             rs, o, comp=comp)
                    if c["n"]:
                        f("| %s | %d | %d | %s | %s |"
                          % (nm, c["n"], c["n_sessions"], o, show(c)))
            f("\n**Runs of the same day class** — contnext against the same "
              "class's other run lengths\n")
            f("| class | run length " + HDR[1:])
            f("|---|---" + SEP[1:])
            for cls in L.REAL_CLASSES:
                for rb in ("1", "2", "3+"):
                    rs = [r for r in rows if r["cls"] == cls and r["run_bucket"] == rb]
                    comp = [r for r in rows if r["cls"] == cls and r["run_bucket"] != rb]
                    c = cell("A3", "A3-runs", {"oi": oi, "subset": subset,
                                               "cls": cls, "run": rb},
                             rs, "contnext", comp=comp)
                    if c["n"]:
                        f("| %s | %s | %d | %d | %s | %s |"
                          % (cls, rb, c["n"], c["n_sessions"], "contnext", show(c)))


# =============================================================== STUDY B
def study_b(f):
    f("\n## B — basis against its usual level   [exploratory]\n")
    f("b = (P − S)/S in **bp of S** at 10:00:59, 12:00:59, 14:00:59 and "
      "15:29:59. The norm is the median b at the same trading days to series-1 "
      "expiry and the same clock time, **leaving out the session's own expiry "
      "cycle**. dev = b − norm, in bp. Quintiles are of dev within each clock. "
      "rng_next is unsigned and given as a difference against the other "
      "quintiles.\n")
    for subset in ("all", "no-expiry"):
        rows = sub(CTX["BASIS"], subset)
        f("\n### B · %s   [exploratory]\n" % subset)
        f("| clock | quintile " + HDR[1:])
        f("|---|---" + SEP[1:])
        for m in B.CLOCKS:
            rs = [r for r in rows if r["clock_min"] == m and r["dev"] is not None]
            cuts = L.quantile_cuts([r["dev"] for r in rs], 5)
            for q in range(5):
                qq = [r for r in rs if L.bucket(r["dev"], cuts) == q]
                comp = [r for r in rs if L.bucket(r["dev"], cuts) != q]
                for o in ("ret_to_close", "ret_next", "rng_next"):
                    c = cell("B", "B-quintile", {"subset": subset, "clock": L.lbl(m),
                                                 "quintile": q + 1}, qq, o, comp=comp)
                    if c["n"]:
                        f("| %s | Q%d | %d | %d | %s | %s |"
                          % (L.lbl(m), q + 1, c["n"], c["n_sessions"], o, show(c)))
        f("\n**Spearman ρ of dev against each outcome** (descriptive, no p-value)\n")
        f("| clock | outcome | n | ρ |")
        f("|---|---|---|---|")
        for m in B.CLOCKS:
            rs = [r for r in rows if r["clock_min"] == m and r["dev"] is not None]
            for o in ("ret_to_close", "ret_next", "rng_next"):
                pr = [(r["dev"], r[o]) for r in rs if r.get(o) is not None]
                f("| %s | %s | %d | %+.4f |"
                  % (L.lbl(m), o, len(pr),
                     L.spearman([p[0] for p in pr], [p[1] for p in pr])))


# =============================================================== STUDY C
def c_prepare():
    days = CTX["DAYS"]["F"]
    devmap = {r["trade_date"]: r["dev"] for r in CTX["BASIS"]
              if r["clock_min"] == L.CLOSE_MIN and r["dev"] is not None}
    g = CTX["G"]
    P, PH, PL = CTX["D"]["P"], CTX["D"]["PH"], CTX["D"]["PL"]
    sessions = CTX["D"]["sessions"]
    prev = {d: sessions[i - 1] for i, d in enumerate(sessions) if i}
    for r in days:
        d = r["trade_date"]
        hs = [v for m, v in PH.get(d, {}).items() if v is not None]
        ls = [v for m, v in PL.get(d, {}).items() if v is not None]
        base = L.series_at(P, prev.get(d), L.CLOSE_MIN)
        r["abs_ret"] = abs(r["dP"]) if r["dP"] is not None else None
        r["intraday_range"] = 1e4 * (max(hs) - min(ls)) / base if hs and ls and base else None
        r["basis_dev"] = devmap.get(d)
        gg = list((g.get(d) or {}).values())
        r["g_mean"] = float(np.mean(gg)) if gg else None
        for key in ("F", "F1"):
            a = L.series_at(CTX["D"][key], d, L.CLOSE_MIN - 60)
            b = L.series_at(CTX["D"][key], d, L.CLOSE_MIN)
            r["d%s_60" % key] = None if (a is None or b is None) else b - a
            pa = L.series_at(CTX["D"][key], prev.get(d), L.CLOSE_MIN)
            r["d%s_prev" % key] = None if (pa is None or b is None) else b - pa
    return days


def c2_split(oi, half="all"):
    w = add_hits(sub(CTX["W"][(30, oi)], "all", half))
    vals = [abs(r["dP"]) for r in w if r["dP"] is not None]
    if not vals:
        return [], [], None
    cut = float(np.percentile(vals, 95))
    big = [r for r in w if r["dP"] is not None and abs(r["dP"]) >= cut]
    rest = [r for r in w if r["dP"] is not None and abs(r["dP"]) < cut]
    return big, rest, cut


def study_c(f):
    f("\n## C — large moves on any day   [exploratory]\n")
    f("C1: the top decile of |close-to-close return| and, separately, of "
      "intraday range (both on P). C2: the top 5 % of |30-minute return|. Each "
      "set is set beside all other days or windows, which is the complement for "
      "every unsigned outcome here.\n")
    days = c_prepare()
    for setname, key in (("top decile |close-to-close return|", "abs_ret"),
                         ("top decile intraday range", "intraday_range")):
        vals = [r[key] for r in days if r.get(key) is not None]
        if not vals:
            continue
        cut = float(np.percentile(vals, 90))
        big = [r for r in days if r.get(key) is not None and r[key] >= cut]
        rest = [r for r in days if r.get(key) is not None and r[key] < cut]
        f("\n### C1 %s   [exploratory]\n" % setname)
        f("Cut at the 90th percentile = %.4f. Large n=%d days over %d sessions; "
          "rest n=%d.\n" % (cut, len(big), len({r['trade_date'] for r in big}), len(rest)))
        f("**BEFORE — rank-biserial separation** (+1 large always above rest, 0 none)\n")
        f("| variable | n large | n rest | rank-biserial |")
        f("|---|---|---|---|")
        for v in ("dF_60", "dF1_60", "dF_prev", "dF1_prev", "basis_dev", "g_mean"):
            a = [r.get(v) for r in big if r.get(v) is not None]
            b2 = [r.get(v) for r in rest if r.get(v) is not None]
            f("| %s | %d | %d | %+.4f |" % (v, len(a), len(b2), L.rank_biserial(a, b2)))
        f("\n*`g_mean` exists only for the 182 sessions M2 kept — see "
          "NOT_VERIFIED §5; its denominator is the `n` column above.*\n")
        f("**DURING — class composition**\n")
        f("| set | " + " | ".join(L.CLASSES) + " |")
        f("|---|" + "---|" * len(L.CLASSES))
        for nm, s in (("large", big), ("rest", rest)):
            f("| %s | %s |" % (nm, " | ".join(str(sum(1 for r in s if r["cls"] == c))
                                              for c in L.CLASSES)))
        f("\n**AFTER — next-session outcome**\n")
        f("| set " + HDR[1:])
        f("|---" + SEP[1:])
        for nm, s, comp in (("large", big, rest), ("rest", rest, big)):
            for o in ("retnext", "contnext", "rngnext"):
                c = cell("C1", "C1-" + key, {"set": nm, "metric": key}, s, o, comp=comp)
                if c["n"]:
                    f("| %s | %d | %d | %s | %s |" % (nm, c["n"], c["n_sessions"], o, show(c)))
    for oi in ("F", "F1"):
        big, rest, cut = c2_split(oi)
        f("\n### C2 top 5 %% of |30-minute return| · OI=%s   [exploratory]\n" % oi)
        f("Cut at |dP| ≥ %.2f index points. Large n=%d windows over %d sessions; "
          "rest n=%d.\n" % (cut, len(big), len({r['trade_date'] for r in big}), len(rest)))
        f("| set " + HDR[1:])
        f("|---" + SEP[1:])
        for nm, s, comp in (("large", big, rest), ("rest", rest, big)):
            for o in CONT + HIT:
                c = cell("C2", "C2", {"oi": oi, "set": nm}, s, o, comp=comp)
                if c["n"]:
                    f("| %s | %d | %d | %s | %s |" % (nm, c["n"], c["n_sessions"], o, show(c)))
        f("\n### C3 large windows by class · OI=%s   [exploratory]\n" % oi)
        f("Contrasts hold the price sign fixed: LB vs SC, SB vs LU.\n")
        f("| contrast " + HDR[1:])
        f("|---" + SEP[1:])
        for pair in PAIRS:
            nm = "%s vs %s" % pair
            rs = [r for r in big if r["cls"] == pair[0]]
            comp = [r for r in big if r["cls"] == pair[1]]
            for o in CONT + HIT:
                c = cell("C3", "C3", {"oi": oi, "pair": nm}, rs, o, comp=comp)
                if c["n"]:
                    f("| %s | %d | %d | %s | %s |" % (nm, c["n"], c["n_sessions"], o, show(c)))


# =============================================================== STUDY D
def d_conds(sr, oi):
    """Conditions and their complements for one side at one band."""
    out = [("all", sr, None)]
    k = "d%s_30" % oi
    rise = [r for r in sr if r.get(k) is not None and r[k] > 0]
    fall = [r for r in sr if r.get(k) is not None and r[k] < 0]
    out.append(("%s rising" % oi, rise, fall))
    out.append(("%s falling" % oi, fall, rise))
    vals = [r[k] for r in sr if r.get(k) is not None]
    if len(vals) >= 6:
        cuts = L.quantile_cuts(vals, 3)
        for t in range(3):
            ins = [r for r in sr if r.get(k) is not None and L.bucket(r[k], cuts) == t]
            oth = [r for r in sr if r.get(k) is not None and L.bucket(r[k], cuts) != t]
            out.append(("%s T%d" % (oi, t + 1), ins, oth))
    return out


def d_rows(band, edgemode, subset, half="all"):
    rows = [r for r in CTX["APPR"][band] if r["approached"] and r.get("outcome")]
    if edgemode == "without edge":
        rows = [r for r in rows if not r["edge"]]
    rows = sub(rows, subset, half)
    for r in rows:
        r["break_rate"] = 1.0 if r["outcome"] == "BREAK" else 0.0
    return rows


def study_d(f):
    f("\n## D — walls from the chain, read with futures OI   [exploratory]\n")
    f("Walls are fixed from the **prior** session's close, front expiry: the "
      "call wall is the strike with the largest CE OI at or above the prior spot "
      "close, the put wall the largest PE OI at or below. An approach is the "
      "first minute S comes within the band of a wall **from the inside**. "
      "BREAK if S at 15:29:59 is beyond the wall by ≥ 0.10 %, else HOLD.\n")
    f("Break rate and maximum excursion are unsigned, so each conditioned row "
      "is a **difference against the complementary condition** (F rising minus "
      "F falling; a tercile minus the other two). The unconditional `all` row "
      "has no complement and is printed as a level only.\n")
    f("**2025-10-21 is excluded from walls** (its tag-B bar is 14:45:59, not the "
      "close), removing the walls for **2025-10-23**. Walls are built for "
      "**%d** sessions, not 246.\n" % len(CTX["WALLS"]))
    f("**Edge sessions are flagged**: on 11 sessions the call wall is the highest "
      "strike the vendor lists and on 13 the put wall is the lowest. Every table "
      "is given with and without them.\n")
    f("> **D2 (OI at the wall strike) was not computed in this run; Study D is "
      "D1 only.** D2 requires the change in OI at the wall strike itself over "
      "the 30 minutes before the approach, which needs a per-approach-session "
      "read of `hist_option_bars_1m`. No such extraction was made, and the "
      "chain data this run holds (`session_chain.csv` tag B) carries per-strike "
      "OI only at each session's CLOSE \u2014 one bar per session \u2014 so it "
      "cannot supply an intraday 30-minute change. The conditioning below is on "
      "**futures** OI alone. There is no 2x2 of option-strike OI against "
      "futures OI anywhere in this document.\n")
    for band in BANDS:
        appr = CTX["APPR"][band]
        f("\n### D band = %.2f %%   [exploratory]\n" % band)
        f("**Sessions producing NO approach, by wall distance**\n")
        f("| side | wall distance | no approach | sessions in bucket | share |")
        f("|---|---|---|---|---|")
        for side in ("call", "put"):
            for bk in ("<=2%", "2-4%", ">4%"):
                inb = [r for r in appr if r["side"] == side
                       and B.wall_distance_bucket(r["wall_dist_pct"]) == bk]
                no = [r for r in inb if not r["approached"]]
                if inb:
                    f("| %s | %s | %d | %d | %.1f%% |"
                      % (side, bk, len(no), len(inb), 100.0 * len(no) / len(inb)))
        for edgemode in ("with edge", "without edge"):
            for subset in ("all", "no-expiry"):
                rows = d_rows(band, edgemode, subset)
                f("\n**Break rate and excursion · %s · %s**\n" % (edgemode, subset))
                f("| side | condition " + HDR[1:])
                f("|---|---" + SEP[1:])
                for side in ("call", "put"):
                    sr = [r for r in rows if r["side"] == side]
                    for oi in ("F", "F1"):
                        for nm, rs, comp in d_conds(sr, oi):
                            if nm == "all" and oi == "F1":
                                continue
                            d = {"band": band, "edge": edgemode, "subset": subset,
                                 "side": side, "cond": nm, "oi": oi}
                            for o in ("break_rate", "max_excursion_pct"):
                                c = cell("D", "D-break", d, rs, o, comp=comp)
                                if c["n"]:
                                    f("| %s | %s | %d | %d | %s | %s |"
                                      % (side, nm, c["n"], c["n_sessions"], o, show(c)))


# =============================================================== ledger
def ledger(f):
    f("\n## CUTS LEDGER   [exploratory]\n")
    f("Every cell computed, printed or not. A cell is one "
      "(subset × definition × outcome) with its own interval. **Every effect is "
      "a difference against the cell's complement**, for signed and unsigned "
      "outcomes alike, so the sample's common drift cancels. A cell with no "
      "complement is recorded as a **level** and cannot exclude zero by "
      "construction.\n")
    f("| study | cells | levels only | testable | intervals excluding zero |")
    f("|---|---|---|---|---|")
    bys = {}
    for c in CELLS:
        s = c["study"]
        a, lv, te, ez = bys.get(s, (0, 0, 0, 0))
        bys[s] = (a + 1, lv + (0 if c["shortlistable"] else 1),
                  te + (1 if c["shortlistable"] and c["n"] > 0 else 0),
                  ez + (1 if c["excl_zero"] else 0))
    T = [0, 0, 0, 0]
    for s in sorted(bys):
        v = bys[s]
        T = [T[i] + v[i] for i in range(4)]
        f("| %s | %d | %d | %d | %d |" % (s, v[0], v[1], v[2], v[3]))
    f("| **total** | **%d** | **%d** | **%d** | **%d** |" % tuple(T))
    f("\nTestable cells (a real effect, n > 0): **%d**. Expected to exclude zero "
      "by chance alone at 5 %%: **%.1f**. Observed: **%d**.\n"
      % (T[2], 0.05 * T[2], T[3]))
    fam = set()
    fam_ez = set()
    for c in CELLS:
        if c["study"] != "A1" or not c["shortlistable"] or c["n"] == 0:
            continue
        k = (c["defn"]["pair"], c["defn"]["step"], c["defn"]["oi"])
        fam.add(k)
        if c["excl_zero"]:
            fam_ez.add(k)
    f("**A1 by family.** A1's cells are the same windows re-cut across "
      "strengths, subsets, time-of-day buckets and outcomes, so one structure "
      "appears as many correlated cells. Counting instead by "
      "**(contrast, step, OI series) family**: **%d** families carry at least "
      "one testable cell, and **%d** of them carry at least one interval "
      "excluding zero, against **%d** A1 cells excluding zero.\n"
      % (len(fam), len(fam_ez),
         sum(1 for c in CELLS if c["study"] == "A1" and c["excl_zero"])))
    for k in sorted(fam):
        f("- %s · step %s · OI %s — %s"
          % (k[0], k[1], k[2], "has an interval excluding zero"
             if k in fam_ez else "none excluding zero"))
    f("")
    f("These cells are **not independent** — they share rows across window "
      "lengths, OI series, subsets, time-of-day buckets and outcomes — so the "
      "chance expectation is a reference point for sizing the search, not a null "
      "distribution, and the comparison is not a test.\n")
    if RECOMPUTE_ERRORS:
        f("**Robustness recomputation failures**, by study: %s. A failure is "
          "reported as `error` in the shortlist, never as `n/a`.\n"
          % ", ".join("%s=%d" % (s, RECOMPUTE_ERRORS[s])
                      for s in sorted(RECOMPUTE_ERRORS)))
        for s in sorted(RECOMPUTE_LAST):
            f("- last failure in %s: `%s`" % (s, RECOMPUTE_LAST[s]))
        f("")
    else:
        f("**Robustness recomputation failures: none.**\n")
    return T


def shortlist(f):
    f("\n## SHORTLIST   [exploratory]\n")
    f("**A shortlist drawn from many cuts is biased upward.** These ten were "
      "selected *because* they are the most extreme among %d cells; selecting on "
      "the statistic guarantees the estimates here overstate whatever is real. "
      "Nothing in this list is a finding.\n" % len(CELLS))
    f("Every effect here is a **difference against the cell's complement**, "
      "not a level, so the sample's market drift is cancelled rather than "
      "counted.\n")
    f("**Ranking: |effect| ÷ half-width of its own 95 % interval.** This is "
      "unit-free, so bp, rate and %% cells compete on one scale and no per-unit "
      "quota is needed. Level-only cells are excluded by construction.\n")
    elig = []
    for c in CELLS:
        if not (c["excl_zero"] and c["n_sessions"] >= 20):
            continue
        if math.isnan(c["effect"]) or math.isnan(c["lo"]) or math.isnan(c["hi"]):
            continue
        hw = (c["hi"] - c["lo"]) / 2.0
        if hw <= 0:
            continue
        c["rank_stat"] = abs(c["effect"]) / hw
        elig.append(c)
    elig.sort(key=lambda c: -c["rank_stat"])
    top = elig[:10]
    f("| # | study | definition | outcome | n | sessions | effect | 95% CI | "
      "|eff|/half-width | F vs F1 | both halves | expiry removed |")
    f("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(top, 1):
        rob = robustness(c)
        f("| %d | %s | %s | %s | %d | %d | %+.3f %s | [%+.3f, %+.3f] | %.2f | %s | %s | %s |"
          % (i, c["study"], fmt_defn(c["defn"]), c["outcome"], c["n"], c["n_sessions"],
             c["effect"], c["unit"], c["lo"], c["hi"], c["rank_stat"],
             rob["oi"], rob["halves"], rob["noexp"]))
    f("\nEligibility: interval excludes zero, n sessions ≥ 20, and the cell is a "
      "real effect (signed level, or unsigned difference against a complement). "
      "Eligible cells: **%d**; the ten above are the extreme tail of that set.\n"
      % len(elig))
    return top


def fmt_defn(d):
    return ", ".join("%s=%s" % (k, v) for k, v in d.items())


def robustness(c):
    out = {"oi": "n/a", "halves": "n/a", "noexp": "n/a"}
    d = dict(c["defn"])
    if c["study"] not in ("A1", "A2", "A3", "C2", "C3", "D"):
        return out
    other = {"F": "F1", "F1": "F"}.get(d.get("oi"))
    if other:
        out["oi"] = sign_word(c["effect"], recompute(c, dict(d, oi=other)))
    r1 = recompute(c, d, half="H1")
    r2 = recompute(c, d, half="H2")
    if isinstance(r1, float) and isinstance(r2, float) \
            and not math.isnan(r1) and not math.isnan(r2):
        out["halves"] = "yes" if (r1 > 0) == (r2 > 0) == (c["effect"] > 0) else "no"
    elif r1 == "error" or r2 == "error":
        out["halves"] = "error"
    if d.get("subset") in ("all", "no-expiry"):
        out["noexp"] = sign_word(c["effect"], recompute(c, dict(d, subset="no-expiry")))
    return out


def sign_word(base, v):
    if v == "error":
        return "error"
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "n/a"
    return "yes" if (v > 0) == (base > 0) else "no"


def recompute(c, d, half="all"):
    """Recompute a cell's effect under a variant definition.

    Exceptions are NOT swallowed: the study is counted in RECOMPUTE_ERRORS and
    the string 'error' is returned, so a failure shows as `error` in the
    shortlist and never as `n/a`."""
    study, outcome = c["study"], c["outcome"]
    try:
        comp = None
        if study == "A1":
            pair = tuple(d["pair"].split(" vs "))
            rows, comp = a1_pair(d["step"], d["oi"], d["subset"], half,
                                 d["strength"], pair, d["tod"])
        elif study == "A2":
            pairs = a2_pairs(d["step"], d["oi"], d["subset"], half)
            rows = [x for x in pairs if x["prev"] == d["prev"] and x["cur"] == d["cur"]]
            comp = a2_comp(pairs, d["prev"], d["cur"])
        elif study == "A3":
            base = sub(CTX["DAYS"][d["oi"]], d["subset"], half)
            if "run" in d:
                rows = [r for r in base if r["cls"] == d["cls"] and r["run_bucket"] == d["run"]]
                comp = [r for r in base if r["cls"] == d["cls"] and r["run_bucket"] != d["run"]]
            else:
                pair = tuple(d["pair"].split(" vs "))
                rows = [r for r in base if r["cls"] == pair[0]]
                comp = [r for r in base if r["cls"] == pair[1]]
        elif study in ("C2", "C3"):
            big, rest, _ = c2_split(d["oi"], half)
            if study == "C2":
                rows = big if d["set"] == "large" else rest
                comp = rest if d["set"] == "large" else big
            else:
                pair = tuple(d["pair"].split(" vs "))
                rows = [r for r in big if r["cls"] == pair[0]]
                comp = [r for r in big if r["cls"] == pair[1]]
        elif study == "D":
            rows_all = d_rows(d["band"], d["edge"], d["subset"], half)
            sr = [r for r in rows_all if r["side"] == d["side"]]
            found = [(nm, rs, cm) for nm, rs, cm in d_conds(sr, d["oi"]) if nm == d["cond"]]
            if not found:
                return float("nan")
            _, rows, comp = found[0]
        else:
            return float("nan")
        if comp is None:
            return float("nan")      # level-only cells are not shortlistable
        return L.boot_diff(rows, comp, outcome)["mean"]
    except Exception as e:
        RECOMPUTE_ERRORS[study] = RECOMPUTE_ERRORS.get(study, 0) + 1
        RECOMPUTE_LAST[study] = repr(e)[:160]
        return "error"
