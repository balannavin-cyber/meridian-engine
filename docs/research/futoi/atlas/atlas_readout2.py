"""Readout 2: pooled OI-sign contrast and robustness slices.
READ-ONLY, no database access. Exploratory, no verdict.

The pooled contrast is (LB + SB) vs (SC + LU) -- i.e. dOI > 0 against dOI < 0,
with the price sign no longer held fixed because both groups contain both price
signs. Only rows carrying a real class are used, so FLAT and MISSING never
enter.

Two cluster definitions are reported side by side:
  session     resample whole trading sessions (as everywhere else in the atlas)
  week-block  resample whole ISO calendar weeks

Trailing quantities are computed from data up to the PRIOR close only:
  trailing 20-session realised volatility  sd of the 20 close-to-close log
                                           returns ending at d-1
  trailing 20-session return               ln P(d-1) / P(d-21)
Neither reads the session being classified.
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
OUT = os.path.join(HERE, "atlas_readout2_2026-11-19.md")
CUT_FROM, CUT_TO = "2026-02-01", "2026-03-30"
LINES = []


def f(s=""):
    LINES.append(s)


def iso_week(d):
    y, w, _ = dt.date.fromisoformat(d).isocalendar()
    return "%04d-W%02d" % (y, w)


def boot_diff_by(rows_a, rows_b, key, cluster, n=L.B_RESAMPLES, seed=L.SEED,
                 alpha=0.05):
    """Percentile bootstrap of mean(a) - mean(b), resampling whole CLUSTERS.
    `cluster` maps a row to its cluster id, so the same routine gives the
    session-clustered and the week-block interval."""
    per = {}
    for rows, i in ((rows_a, 0), (rows_b, 2)):
        for r in rows:
            v = r.get(key)
            if v is None:
                continue
            e = per.setdefault(cluster(r), [0.0, 0, 0.0, 0])
            e[i] += v
            e[i + 1] += 1
    nan = float("nan")
    keys = list(per)
    if not keys:
        return {"n": 0, "n_b": 0, "clusters": 0, "mean": nan, "lo": nan, "hi": nan}
    A = np.array([per[k] for k in keys], dtype=float)
    sa, ca, sb, cb = A[:, 0].sum(), A[:, 1].sum(), A[:, 2].sum(), A[:, 3].sum()
    if ca == 0 or cb == 0:
        return {"n": int(ca), "n_b": int(cb), "clusters": len(keys),
                "mean": nan, "lo": nan, "hi": nan}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(keys), size=(n, len(keys)))
    qa, na = A[:, 0][idx].sum(axis=1), A[:, 1][idx].sum(axis=1)
    qb, nb = A[:, 2][idx].sum(axis=1), A[:, 3][idx].sum(axis=1)
    ok = (na > 0) & (nb > 0)
    reps = np.full(n, np.nan)
    reps[ok] = qa[ok] / na[ok] - qb[ok] / nb[ok]
    reps = reps[~np.isnan(reps)]
    reps.sort()
    return {"n": int(ca), "n_b": int(cb), "clusters": len(keys),
            "mean": float(sa / ca - sb / cb),
            "lo": float(np.percentile(reps, 100 * alpha / 2)) if len(reps) else nan,
            "hi": float(np.percentile(reps, 100 * (1 - alpha / 2))) if len(reps) else nan}


BY_SESSION = lambda r: r["trade_date"]
BY_WEEK = lambda r: iso_week(r["trade_date"])


def split(rows):
    """(dOI>0, dOI<0) among rows carrying a real class."""
    real = [r for r in rows if r["cls"] in L.REAL_CLASSES]
    return ([r for r in real if r["dOI"] > 0], [r for r in real if r["dOI"] < 0])


def both(a, b, key):
    s = boot_diff_by(a, b, key, BY_SESSION)
    w = boot_diff_by(a, b, key, BY_WEEK)
    return s, w


def row(label, a, b, key="retnext"):
    s, w = both(a, b, key)
    return ("| %s | %d | %d | %d | %d | %+.3f | [%+.3f, %+.3f] | [%+.3f, %+.3f] |"
            % (label, s["n"], s["n_b"], s["clusters"], w["clusters"],
               s["mean"], s["lo"], s["hi"], w["lo"], w["hi"]))


HDR = ("| slice | n dOI>0 | n dOI<0 | sessions | weeks | effect (bp) | "
       "session CI | week-block CI |")
SEP = "|---|---|---|---|---|---|---|---|"


def build():
    D = L.load_all()
    W = {}
    for step in (15, 30, 60):
        for oi in ("F", "F1"):
            W[(step, oi)] = ST.add_hits(B.build_windows(D, step, oi))
    DAYS = {oi: B.build_days(D, oi) for oi in ("F", "F1")}
    BASIS = B.build_basis(D)
    ST.CTX.update({"D": D, "W": W, "DAYS": DAYS, "BASIS": BASIS})
    return D, W, DAYS, BASIS


def trailing(D):
    """Trailing 20-session realised vol and return, from the PRIOR close only."""
    P = D["P"]
    sessions = D["sessions"]
    closes = [(d, L.series_at(P, d, L.CLOSE_MIN)) for d in sessions]
    rets = {}
    for i in range(1, len(closes)):
        a, b = closes[i - 1][1], closes[i][1]
        if a and b:
            rets[closes[i][0]] = math.log(b / a)
    out = {}
    for i, d in enumerate(sessions):
        prior = sessions[max(0, i - 20):i]          # up to d-1 inclusive
        rr = [rets[x] for x in prior if x in rets]
        if len(rr) >= 10:
            m = sum(rr) / len(rr)
            sd = math.sqrt(sum((v - m) ** 2 for v in rr) / (len(rr) - 1))
            out[d] = {"vol20": sd, "ret20": sum(rr)}
    return out


def srcline(pattern):
    """Line number of the first line of THIS file containing `pattern`, so the
    citations below are read from the code rather than recalled."""
    with open(os.path.abspath(__file__)) as fh:
        for i, line in enumerate(fh, 1):
            if pattern in line:
                return i
    return -1


def provenance(D, DAYS):
    tr = trailing(D)
    sessions = D["sessions"]
    weeks = sorted({iso_week(d) for d in sessions})
    f("\n## Provenance — read from the code   [exploratory]\n")
    f("### (a) How a calendar week is keyed for the block bootstrap\n")
    f("| item | value |")
    f("|---|---|")
    f("| key function | `iso_week()` — `atlas_readout2.py:%d` |" % srcline("def iso_week(d):"))
    f("| key expression | ``\"%%04d-W%%02d\" %% (y, w)`` from "
      "`dt.date.fromisoformat(d).isocalendar()` — `atlas_readout2.py:%d` |"
      % srcline('return "%04d-W%02d"'))
    f("| cluster selector | `BY_WEEK` — `atlas_readout2.py:%d` |" % srcline("BY_WEEK = lambda r"))
    f("| resampler | `boot_diff_by(..., cluster)` — `atlas_readout2.py:%d` |"
      % srcline("def boot_diff_by("))
    f("| sessions in the window | %d |" % len(sessions))
    f("| **distinct ISO weeks** | **%d** |" % len(weeks))
    f("| first / last week | %s / %s |" % (weeks[0], weeks[-1]))
    f("| sessions per week | min %d, median %d, max %d |"
      % (min(sum(1 for d in sessions if iso_week(d) == w) for w in weeks),
         int(np.median([sum(1 for d in sessions if iso_week(d) == w) for w in weeks])),
         max(sum(1 for d in sessions if iso_week(d) == w) for w in weeks)))
    f("\n### (b) The trailing-20-session window\n")
    f("| item | value |")
    f("|---|---|")
    f("| slice | `prior = sessions[max(0, i - 20):i]` — "
      "`atlas_readout2.py:%d` |" % srcline("prior = sessions[max(0, i - 20):i]"))
    f("| end of window | the slice upper bound is `i`, **exclusive**, so the "
      "window's last session is `sessions[i-1]` — the PRIOR session. The "
      "session being classified, `sessions[i]`, is never in its own window. |")
    f("| returns used | `rets[x]` = close-to-close log return INTO session `x`, "
      "i.e. ln P(x)/P(x−1) — `atlas_readout2.py:%d` |"
      % srcline("rets[closes[i][0]] = math.log(b / a)"))
    f("| realised vol | sample sd of those returns — `atlas_readout2.py:%d` |"
      % srcline("sd = math.sqrt(sum((v - m) ** 2 for v in rr) / (len(rr) - 1))"))
    f("| trailing return | `sum(rr)`, the sum of the log returns in the window, "
      "= ln P(d−1)/P(d−21) — `atlas_readout2.py:%d` |" % srcline('"ret20": sum(rr)'))
    f("| minimum returns required | 10 — `atlas_readout2.py:%d` |"
      % srcline("if len(rr) >= 10:"))
    f("| sessions with a trailing value | %d of %d |" % (len(tr), len(sessions)))
    f("\n### (c) One worked example row for item 3\n")
    rows = [r for r in DAYS["F"] if r["trade_date"] in tr]
    vals = [tr[r["trade_date"]]["vol20"] for r in rows]
    cuts = L.quantile_cuts(vals, 3)
    ex = next(r for r in rows if r["cls"] in L.REAL_CLASSES
              and r.get("retnext") is not None
              and tr[r["trade_date"]]["vol20"] > cuts[1])
    d = ex["trade_date"]
    i = sessions.index(d)
    prior = sessions[max(0, i - 20):i]
    t = L.bucket(tr[d]["vol20"], cuts)
    f("| field | value |")
    f("|---|---|")
    f("| session classified | %s |" % d)
    f("| its trailing window, first session | %s |" % prior[0])
    f("| its trailing window, last session | %s |" % prior[-1])
    f("| sessions in the window | %d |" % len(prior))
    f("| the classified session is inside its own window | **no** — %s > %s |"
      % (d, prior[-1]))
    f("| trailing 20-session realised vol | %.6f |" % tr[d]["vol20"])
    f("| tercile cut points | %.6f, %.6f |" % (cuts[0], cuts[1]))
    f("| tercile assigned | **T%d** |" % (t + 1))
    f("| trailing 20-session return | %+.6f |" % tr[d]["ret20"])
    f("| its own class / dOI sign | %s / %s |"
      % (ex["cls"], "dOI>0" if ex["dOI"] > 0 else "dOI<0"))
    f("| its own next-session return | %+.3f bp |" % ex["retnext"])
    f("| ISO week used for the block bootstrap | %s |" % iso_week(d))


def item1(W, DAYS):
    f("\n## 1. Pooled OI-sign contrast — (LB+SB) vs (SC+LU) on `retnext`   [exploratory]\n")
    f("Price sign is NOT held fixed here: both groups contain both price signs, "
      "so the contrast is the sign of dOI alone. Rows must carry a real class, "
      "so FLAT and MISSING are excluded. Session CI resamples sessions; "
      "week-block CI resamples whole ISO calendar weeks. %d resamples, seed %d.\n"
      % (L.B_RESAMPLES, L.SEED))
    f(HDR)
    f(SEP)
    for oi in ("F", "F1"):
        for subset in ("all", "no-expiry"):
            for step in (15, 30, 60):
                a, b = split(ST.sub(W[(step, oi)], subset))
                f(row("step %d · %s · %s" % (step, oi, subset), a, b))
            a, b = split(ST.sub(DAYS[oi], subset))
            f(row("day · %s · %s" % (oi, subset), a, b))
    f("\n**Strong windows only, steps 30 and 60**\n")
    f(HDR)
    f(SEP)
    for oi in ("F", "F1"):
        for subset in ("all", "no-expiry"):
            for step in (30, 60):
                rows = [r for r in ST.sub(W[(step, oi)], subset) if r.get("strong")]
                a, b = split(rows)
                f(row("step %d strong · %s · %s" % (step, oi, subset), a, b))


def item2(DAYS):
    f("\n## 2. Day level, F — by calendar month, and with 2026-02-01..2026-03-30 removed   [exploratory]\n")
    rows = DAYS["F"]
    f(HDR.replace("| slice |", "| month |"))
    f(SEP)
    months = sorted({r["trade_date"][:7] for r in rows})
    for m in months:
        a, b = split([r for r in rows if r["trade_date"][:7] == m])
        if not a or not b:
            f("| %s | %d | %d | — | — | — | — | — |" % (m, len(a), len(b)))
            continue
        f(row(m, a, b))
    f("")
    f(HDR)
    f(SEP)
    a, b = split(rows)
    f(row("day · F · all months", a, b))
    kept = [r for r in rows if not (CUT_FROM <= r["trade_date"] <= CUT_TO)]
    a, b = split(kept)
    f(row("day · F · %s..%s REMOVED" % (CUT_FROM, CUT_TO), a, b))


def item3(D, DAYS):
    f("\n## 3. Day level, F — within trailing-20-session terciles   [exploratory]\n")
    f("Both trailing quantities use data up to the **prior close only**: "
      "realised volatility is the sd of the 20 close-to-close log returns "
      "ending at d−1, and the trailing return is ln P(d−1)/P(d−21). Neither "
      "reads the session being classified.\n")
    tr = trailing(D)
    rows = [r for r in DAYS["F"] if r["trade_date"] in tr]
    for name, key in (("trailing 20-session realised volatility", "vol20"),
                      ("trailing 20-session return", "ret20")):
        vals = [tr[r["trade_date"]][key] for r in rows]
        cuts = L.quantile_cuts(vals, 3)
        f("\n**Terciles of %s** — cut points %.6f and %.6f\n"
          % (name, cuts[0], cuts[1]))
        f(HDR.replace("| slice |", "| tercile |"))
        f(SEP)
        for t in range(3):
            sel = [r for r in rows
                   if L.bucket(tr[r["trade_date"]][key], cuts) == t]
            a, b = split(sel)
            if not a or not b:
                f("| T%d | %d | %d | — | — | — | — | — |" % (t + 1, len(a), len(b)))
                continue
            f(row("T%d" % (t + 1), a, b))


def item4(D, BASIS):
    f("\n## 4. Study B `rng_next`, Q1 and Q5 vs the other four   [exploratory]\n")
    f("Clocks 12:00:59 and 14:00:59. Quintiles of `dev` are cut within each "
      "slice. Session and week-block intervals side by side.\n")
    tr = trailing(D)
    f("\n**With 2026-02-01..2026-03-30 removed**\n")
    f("| clock | subset | quintile | n | n comp | sessions | weeks | "
      "effect (bp) | session CI | week-block CI |")
    f("|---|---|---|---|---|---|---|---|---|---|")
    for subset in ("all", "no-expiry"):
        for m in (12 * 60, 14 * 60):
            rs = [r for r in ST.sub(BASIS, subset)
                  if r["clock_min"] == m and r["dev"] is not None
                  and not (CUT_FROM <= r["trade_date"] <= CUT_TO)]
            if len(rs) < 10:
                continue
            cuts = L.quantile_cuts([r["dev"] for r in rs], 5)
            for q in (0, 4):
                qq = [r for r in rs if L.bucket(r["dev"], cuts) == q]
                comp = [r for r in rs if L.bucket(r["dev"], cuts) != q]
                s = boot_diff_by(qq, comp, "rng_next", BY_SESSION)
                w = boot_diff_by(qq, comp, "rng_next", BY_WEEK)
                f("| %s | %s | Q%d | %d | %d | %d | %d | %+.3f | "
                  "[%+.3f, %+.3f] | [%+.3f, %+.3f] |"
                  % (L.lbl(m), subset, q + 1, s["n"], s["n_b"], s["clusters"],
                     w["clusters"], s["mean"], s["lo"], s["hi"], w["lo"], w["hi"]))
    f("\n**Within terciles of trailing 20-session realised volatility (prior close only)**\n")
    f("| clock | subset | vol tercile | quintile | n | n comp | sessions | "
      "weeks | effect (bp) | session CI | week-block CI |")
    f("|---|---|---|---|---|---|---|---|---|---|---|")
    for subset in ("all", "no-expiry"):
        for m in (12 * 60, 14 * 60):
            base = [r for r in ST.sub(BASIS, subset)
                    if r["clock_min"] == m and r["dev"] is not None
                    and r["trade_date"] in tr]
            if len(base) < 30:
                continue
            vcuts = L.quantile_cuts([tr[r["trade_date"]]["vol20"] for r in base], 3)
            for t in range(3):
                rs = [r for r in base
                      if L.bucket(tr[r["trade_date"]]["vol20"], vcuts) == t]
                if len(rs) < 10:
                    continue
                cuts = L.quantile_cuts([r["dev"] for r in rs], 5)
                for q in (0, 4):
                    qq = [r for r in rs if L.bucket(r["dev"], cuts) == q]
                    comp = [r for r in rs if L.bucket(r["dev"], cuts) != q]
                    if not qq or not comp:
                        continue
                    s = boot_diff_by(qq, comp, "rng_next", BY_SESSION)
                    w = boot_diff_by(qq, comp, "rng_next", BY_WEEK)
                    f("| %s | %s | T%d | Q%d | %d | %d | %d | %d | %+.3f | "
                      "[%+.3f, %+.3f] | [%+.3f, %+.3f] |"
                      % (L.lbl(m), subset, t + 1, q + 1, s["n"], s["n_b"],
                         s["clusters"], w["clusters"], s["mean"], s["lo"],
                         s["hi"], w["lo"], w["hi"]))


def main():
    D, W, DAYS, BASIS = build()
    f("# Atlas readout 2 — 2026-11-19")
    f()
    f("Exploration. No verdict. Nothing here is a finding until confirmed once "
      "on unseen data.")
    f()
    f("Read-only; no database access. Tables only.")
    f()
    f("---")
    provenance(D, DAYS)
    f("\n---")
    item1(W, DAYS)
    item2(DAYS)
    item3(D, DAYS)
    item4(D, BASIS)
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
