"""C1 result document: section 4 (the one test) and section 7 (separate reads).
Imported by c1_score.py and run only behind --score. READ-ONLY, no database.
"""
import csv
import datetime as dt
import math
import os

import numpy as np

import c1_score as S

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "futoi_C1_result_2026-11-19.md")
LINES = []


def f(s=""):
    LINES.append(s)


def fmt(e):
    if e is None:
        return "— | — | — | — | —"
    return ("%d | %d | %d | %+.2f | [%+.2f, %+.2f]"
            % (e["n_pos"], e["n_neg"], e["weeks"], e["E"], e["p5"], e["p95"]))


def report(dv, kept, excl, ctx, vm, rm):
    main = S.effect(kept)
    verdict = ("SIGN CONFIRMED" if main and main["p95"] < 0
               else "NOT CONFIRMED (underpowered against -20 bp)")
    pts = float(np.mean([r["r_pts"] for r in kept if r["dF"] > 0])) \
        - float(np.mean([r["r_pts"] for r in kept if r["dF"] < 0]))

    f("# C1 result — %s" % verdict)
    f()
    f("One look, run once. The pre-registration "
      "`futoi_C1_oi_sign_prereg_2026-11-19.md` is binding; where it and the run "
      "prompt differ, the pre-registration governs. No database was accessed: "
      "every figure comes from the two hashed export files and the closed run's "
      "design-period CSVs.")
    f()
    f("## Design-period values, computed before the test file was read\n")
    f("| quantity | value |")
    f("|---|---|")
    f("| mean absolute daily return, series-1 close | **%.4f bp** |" % dv["mad_bp"])
    f("| design sessions / daily returns | %d / %d |"
      % (dv["n_sessions"], dv["n_returns"]))
    f("| sessions with a trailing value / day-row subset | %d / %d |"
      % (dv["n_trailing"], dv["n_dayrows"]))
    f()
    f("### Tercile cut points — two versions, and which was used\n")
    f("| quantity | recomputed here | **used (atlas_readout2.py day-row)** | difference |")
    f("|---|---|---|---|")
    for lbl, k, i in (("trailing vol, lower", "vol", 0), ("trailing vol, upper", "vol", 1),
                      ("trailing return, lower", "ret", 0), ("trailing return, upper", "ret", 1)):
        f("| %s cut | %.6f | **%.6f** | %.2e |"
          % (lbl, dv["recomputed"][k][i], dv["cuts"][k][i],
             abs(dv["recomputed"][k][i] - dv["cuts"][k][i])))
    f()
    f("**Which was used, and why.** The **day-row cut points as "
      "`atlas_readout2.py` computed them** are used for section 7's bucketing, "
      "by operator ruling 2026-11-19: the run prompt says \"exactly as "
      "atlas_readout2.py defines them\", and section 7 of the pre-registration "
      "says the cut points are **fixed from the design period**, which is where "
      "the atlas fixed them. They are constants in the code (`ATLAS_CUTS`), not "
      "recomputed at scoring time.")
    f()
    f("**They do NOT match the recomputation exactly, and the difference is "
      "stated rather than reconciled by adjustment.** Both use the same "
      "definition — the slice `sessions[max(0,i-20):i]`, ending at the prior "
      "close, cut over the day-row subset (`build_days` drops the first and "
      "last session) — on the same design period 2025-04-01..2026-03-30. The "
      "residual comes from two extractions of the same series: "
      "`atlas/data/fut_bars_hl.csv` carries a 15:29:59 series-1 close on **247** "
      "sessions, `data/futures_bars.csv` on **246**, so the trailing sets are "
      "236 and 235 and the day-row subsets 235 and 234. One session's close is "
      "in one extraction and not the other. Vol cuts agree to 1.9e−06; return "
      "cuts differ by up to 6.5e−04.")
    f()
    f("A first pass cut the terciles over **all** sessions with a trailing value "
      "rather than the day-row subset, and used a \"last bar at or before "
      "15:29:59\" scan rather than the exact bar; it matched neither. **All of "
      "this was settled on design-period data, before `--score` ran and before "
      "any test-period outcome existed.**")
    f()
    f("## Recorded about K4, before the verdict\n")
    f("**(1) K4's planted half cannot fail for a data reason.** Adding −20 bp to "
      "every `dF > 0` row shifts `mean(pos)` by exactly −20 and leaves "
      "`mean(neg)` untouched, so E shifts by exactly −20 as an **arithmetic "
      "identity, for any data**. The measured recovery was exactly −20.000 bp "
      "and the tolerance is 0.01. It checks that the grouping and the "
      "aggregation are wired to the same rows — a real wiring check — but it "
      "tests nothing about the data. **Planting on the week-shuffled copy would "
      "have been the stronger check**, showing a known effect recovered against "
      "a null background. It was **not changed**, by operator ruling, because "
      "the outcome had already been seen: changing a control after seeing the "
      "result it gates is the defect the one-look rule exists to prevent. K4 "
      "stands exactly as pre-registered.")
    f()
    f("**(2) The Part 0 K4 line printed the observed E before `--score` ran.** "
      "K4's output includes the line `observed: E = −7.192 bp`, so the main "
      "test's point estimate was visible to the operator and to the drafting "
      "assistant at Part 0, before the scoring step. **Nothing was changed after "
      "it** — no definition, window, exclusion, control or threshold. Recorded "
      "so a reader can weigh it, in the same spirit as the pre-registration's "
      "own exposure note.")
    f()
    f("## 1. The one test (section 4)\n")
    f("| quantity | value |")
    f("|---|---|")
    f("| sessions with dF > 0 | **%d** of %d used |" % (main["n_pos"], len(kept)))
    f("| sessions with dF < 0 | **%d** of %d used |" % (main["n_neg"], len(kept)))
    f("| mean r, dF > 0 | %+.3f bp |"
      % float(np.mean([r["r_bp"] for r in kept if r["dF"] > 0])))
    f("| mean r, dF < 0 | %+.3f bp |"
      % float(np.mean([r["r_bp"] for r in kept if r["dF"] < 0])))
    f("| **E** | **%+.3f bp** |" % main["E"])
    f("| E in NIFTY points | **%+.3f points** |" % pts)
    f("| bootstrap 5th percentile | %+.3f bp |" % main["p5"])
    f("| bootstrap 95th percentile | **%+.3f bp** |" % main["p95"])
    f("| ISO weeks resampled | %d |" % main["weeks"])
    f("| resamples / seed | 10,000 / 20261119 |")
    f("| H1 (E < 0), one-sided α 0.05 | 95th percentile below 0: **%s** |"
      % (main["p95"] < 0))
    f("| **VERDICT** | **%s** |" % verdict)
    f("| E ÷ design mean absolute daily return | **%+.4f** |"
      % (main["E"] / dv["mad_bp"]))
    f()
    f("Window: first session %s, last session %s, last d+1 %s. "
      "Sessions used **%d**; excluded **%d**:"
      % (min(r["d"] for r in kept), max(r["d"] for r in kept),
         max(r["next"] for r in kept), len(kept), sum(excl.values())))
    f()
    f("| excluded, reason | n |")
    f("|---|---|")
    for k, v in sorted(excl.items(), key=lambda kv: -kv[1]):
        f("| %s | %d |" % (k, v))
    f()
    f("**Exposure note, repeated from the pre-registration.** A trial export "
      "pasted into the drafting chat contained raw daily closes and OI for 11 "
      "test sessions, **2026-04-01..2026-04-20**. The drafting assistant saw "
      "them. No statistic was computed from them, and nothing in the "
      "pre-registration was changed because of them — the claim, test, window "
      "and controls were fixed in v2 before the file was seen. Recorded so a "
      "reader can weigh it.")
    f()
    f("**Size, no threshold (section 4).** A SIGN CONFIRMED verdict does not say "
      "the effect is worth trading; cost is assessed separately, later, before "
      "any use.")
    f()
    f("## 2. Section 7 reads — no verdict\n")
    f("Each is its own table and is never pooled into the main number.\n")

    # --- read 1: F1 alone, File A + B, to 2026-10-29
    f("### 7.1 Near contract (F1) alone, 2026-04-01..2026-10-29\n")
    allrows = ctx["rowsA"] + ctx["rowsB"]
    bys = S.sessionise(allrows)
    P, _F, F1, _TS, NC = S.series(bys)
    sess = sorted(bys)
    exp_all = set(S.expiry_sessions(allrows))
    after = set()
    for i, d in enumerate(sess):
        if d in exp_all and i + 1 < len(sess):
            after.add(sess[i + 1])
    rows1, ex1 = [], {}
    for i, d in enumerate(sess):
        if d < S.TEST_FROM:
            continue
        nxt = sess[i + 1] if i + 1 < len(sess) else None
        prev = sess[i - 1] if i > 0 else None
        if nxt is None or nxt > S.F1_TO:
            ex1["d+1 missing or after %s" % S.F1_TO] = \
                ex1.get("d+1 missing or after %s" % S.F1_TO, 0) + 1
            continue
        if d in exp_all or d in after:
            ex1["expiry session or the session after"] = \
                ex1.get("expiry session or the session after", 0) + 1
            continue
        if d not in F1 or prev not in F1 or d not in P or nxt not in P:
            ex1["F1 or P missing"] = ex1.get("F1 or P missing", 0) + 1
            continue
        dF = F1[d] - F1[prev]
        if dF == 0:
            ex1["dF1 = 0"] = ex1.get("dF1 = 0", 0) + 1
            continue
        rows1.append({"d": d, "dF": dF,
                      "r_bp": 1e4 * (math.log(P[nxt]) - math.log(P[d]))})
    e1 = S.effect(rows1)
    f("| n dF1>0 | n dF1<0 | weeks | E (bp) | 5th–95th |")
    f("|---|---|---|---|---|")
    f("| %s |" % fmt(e1))
    f("\nSessions used %d; excluded: %s.\n"
      % (len(rows1), ", ".join("%s %d" % (k, v) for k, v in sorted(ex1.items()))))

    # --- read 2: regime terciles, cuts fixed from the design period
    f("### 7.2 Regime — terciles of trailing 20-session vol and return\n")
    f("Cut points are **fixed from the design period** (section 7): "
      "vol %.6f / %.6f, return %.6f / %.6f. Trailing values use data up to the "
      "prior close only.\n"
      % (dv["cuts"]["vol"][0], dv["cuts"]["vol"][1],
         dv["cuts"]["ret"][0], dv["cuts"]["ret"][1]))
    tr = S.trailing_from(ctx["PA"], ctx["sessA"])
    for nm, key in (("trailing realised volatility", "vol20"),
                    ("trailing return", "ret20")):
        f("\n**Terciles of %s**\n" % nm)
        f("| tercile | n dF>0 | n dF<0 | weeks | E (bp) | 5th–95th |")
        f("|---|---|---|---|---|---|")
        for t in range(3):
            sel = [r for r in kept if r["d"] in tr
                   and S.bucket(tr[r["d"]][key], dv["cuts"][key[:3]]) == t]
            e = S.effect(sel)
            f("| T%d | %s |" % (t + 1, fmt(e)))
        miss = sum(1 for r in kept if r["d"] not in tr)
        f("\nSessions without a trailing value (fewer than 10 prior returns): "
          "%d of %d.\n" % (miss, len(kept)))

    # --- read 3: per calendar month
    f("### 7.3 Per calendar month\n")
    f("| month | n dF>0 | n dF<0 | weeks | E (bp) | 5th–95th |")
    f("|---|---|---|---|---|---|")
    for m in sorted({r["month"] for r in kept}):
        e = S.effect([r for r in kept if r["month"] == m])
        f("| %s | %s |" % (m, fmt(e)))

    # --- side by side
    f("\n### Side by side — for reading only, no verdict\n")
    f("| read | n dF>0 | n dF<0 | weeks | E (bp) | 5th–95th |")
    f("|---|---|---|---|---|---|")
    f("| **main test (section 4)** | %s |" % fmt(main))
    f("| 7.1 near contract F1 to 2026-10-29 | %s |" % fmt(e1))
    for nm, key in (("vol", "vol20"), ("ret", "ret20")):
        for t in range(3):
            sel = [r for r in kept if r["d"] in tr
                   and S.bucket(tr[r["d"]][key], dv["cuts"][nm]) == t]
            f("| 7.2 %s tercile T%d | %s |" % (nm, t + 1, fmt(S.effect(sel))))
    for m in sorted({r["month"] for r in kept}):
        f("| 7.3 %s | %s |" % (m, fmt(S.effect([r for r in kept if r["month"] == m]))))

    f("\n## 3. What was not tested\n")
    f("- **No cost threshold.** The verdict is about the sign only; size is "
      "reported against the typical daily move and nothing else.")
    f("- **No session after 2026-08-25** enters the main test. The near-contract "
      "read reaches 2026-10-29 and carries no verdict.")
    f("- **No price-direction conditioning.** Section 3 fixes the sign of dF as "
      "the only conditioning variable in the main test.")
    f("- **No live path.** The engine has no futures OI capture after "
      "2026-10-29 (section 8); live use would need one.")
    f("- **No re-run.** One look. A defect found after scoring is reported, not "
      "rescored, without an operator ruling.")
    f("- **Not a holdout for anything else.** This spends 2026-04..2026-08 "
      "(and, for F1, to 2026-10) of the futures holdout for this claim alone.")
    f()
    f("*Read-only. No database access, no commit, no branch, no push. "
      "Produced %s UTC.*"
      % dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))

    with open(OUT, "w") as fh:
        fh.write("\n".join(LINES) + "\n")
    with open(os.path.join(HERE, "c1_sessions.csv"), "w", newline="") as fh:
        keys = ["d", "prev", "next", "F", "F_prev", "dF", "P", "P_next",
                "r_bp", "r_pts", "week", "month", "n_contracts"]
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for r in sorted(kept, key=lambda x: x["d"]):
            w.writerow(r)
    print("\nVERDICT: %s" % verdict)
    print("E = %+.3f bp (%+.3f points), 95th pct %+.3f bp, weeks %d, n %d/%d"
          % (main["E"], pts, main["p95"], main["weeks"], main["n_pos"], main["n_neg"]))
    print("wrote %s (%d lines)" % (OUT, len(LINES)))
    return 0
