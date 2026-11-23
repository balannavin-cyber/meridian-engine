#!/usr/bin/env python3
"""POST-HOC decomposition report -> fix/audit/decomp.md.

Reads runs_decomp.csv and extra.csv only (plus fix/replay_v2/runs.csv for the frozen
flag). Does not touch results.md, runs.csv or any existing measure.
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2 = HERE.parent / "replay_v2"
SYMS = ("NIFTY", "SENSEX")
CONS = ("P", "B1", "B2", "N")
L: list[str] = []
SCREEN: list[str] = []


def em(s=""):
    L.append(s)


def both(s=""):
    L.append(s)
    SCREEN.append(s)


def f(v):
    return None if v in (None, "", "None") else float(v)


def mean(v):
    return statistics.mean(v) if v else None


def med(v):
    return statistics.median(v) if v else None


def g(x, nd=6):
    return "n/a" if x is None else f"{x:.{nd}g}"


def main() -> int:
    rows = [r for r in csv.DictReader((HERE / "runs_decomp.csv").open(encoding="utf-8"))
            if r["valid"] == "1"]
    extra = {r["run_id"]: r for r in
             csv.DictReader((HERE / "extra.csv").open(encoding="utf-8"))}
    rv2 = {r["run_id"]: r for r in
           csv.DictReader((V2 / "runs.csv").open(encoding="utf-8"))}
    frozen_col = "frozen" if (rv2 and "frozen" in next(iter(rv2.values()))) else None

    both("<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/audit/decomp.md -->")
    both("")
    both("# POST-HOC decomposition — B1 / B2 between P and N")
    both("")
    both("**POST-HOC. Not part of the frozen rule.** E_raw, E_shape, T error, the N5 "
         "peaks and the lead ≥ 5 % classification are used exactly as defined; no new "
         "normalisation and no exclusion. Source `runs_decomp.csv` (8,595 rows) and "
         "`extra.csv`; `results.md` and `runs.csv` are unchanged.")
    both("")
    both("## Item 0 — how the vendor gamma field is represented")
    both("")
    both("Counted from the chain files over legs with OI > 0 in the strike set, market "
         "runs. **The field is never missing.** The only zero rendering is the JSON "
         "string `\"0.0\"`; there is no `null` and no absent key anywhere.")
    both("")
    both("| symbol | side | legs | missing | present and exactly 0 | present and > 0 |")
    both("|---|---|---|---|---|---|")
    both("| NIFTY | ALL | 399422 | 0 = 0.000% (OI 0.000%) | 61452 = 15.385% (OI 1.951%) | 337970 = 84.615% (OI 98.049%) |")
    both("| NIFTY | ITM | 196804 | 0 = 0.000% (OI 0.000%) | 61439 = 31.218% (OI 12.354%) | 135365 = 68.782% (OI 87.646%) |")
    both("| NIFTY | OTM | 202618 | 0 = 0.000% (OI 0.000%) | 13 = 0.006% (OI 0.001%) | 202605 = 99.994% (OI 99.999%) |")
    both("| SENSEX | ALL | 581573 | 0 = 0.000% (OI 0.000%) | 87104 = 14.977% (OI 1.504%) | 494469 = 85.023% (OI 98.496%) |")
    both("| SENSEX | ITM | 256600 | 0 = 0.000% (OI 0.000%) | 82716 = 32.235% (OI 3.511%) | 173884 = 67.765% (OI 96.489%) |")
    both("| SENSEX | OTM | 324973 | 0 = 0.000% (OI 0.000%) | 4388 = 1.350% (OI 0.905%) | 320585 = 98.650% (OI 99.095%) |")
    both("")
    both("**Consequence, stated before the numbers below: B1 (missing filled only) "
         "must equal P exactly on every real run, and (P−B1)/(P−N) must be 0.** B1 is "
         "exercised only by the planted self-test, where the missing fields are real.")
    both("")

    for sym in SYMS:
        rs = [r for r in rows if r["sym"] == sym]
        both(f"## {sym} — {len(rs)} valid market runs, "
             f"{len({r['day'] for r in rs})} days")
        both("")
        both("### Error means and medians")
        both("")
        both("| error | P mean | P median | B1 mean | B1 median | B2 mean | B2 median | N mean | N median |")
        both("|---|---|---|---|---|---|---|---|---|")
        M = {}
        for lab, key in (("E_raw", "ALL_E_raw_"), ("E_shape", "ALL_E_shape_"),
                         ("T error", "ALL_T_err_")):
            cells, mm = [], {}
            for c in CONS:
                v = [f(r[key + c]) for r in rs if f(r[key + c]) is not None]
                mm[c] = (mean(v), med(v))
                cells += [g(mm[c][0]), g(mm[c][1])]
            M[lab] = mm
            both(f"| {lab} | " + " | ".join(cells) + " |")
        both("")
        both("### Attribution on the means (no clipping)")
        both("")
        both("| error | P − B1 | P − B2 | P − N | (P−B1)/(P−N) | (P−B2)/(P−N) |")
        both("|---|---|---|---|---|---|")
        for lab in ("E_raw", "E_shape", "T error"):
            mm = M[lab]
            d1 = mm["P"][0] - mm["B1"][0]
            d2 = mm["P"][0] - mm["B2"][0]
            dn = mm["P"][0] - mm["N"][0]
            s1 = "NA" if dn == 0 else f"{100.0*d1/dn:.2f}%"
            s2 = "NA" if dn == 0 else f"{100.0*d2/dn:.2f}%"
            both(f"| {lab} | {g(d1)} | {g(d2)} | {g(dn)} | {s1} | {s2} |")
        both("")
        both("### N5 agreement with R, clear-lead runs (R lead ≥ 5 %)")
        both("")
        both("| peak | runs | P | B1 | B2 | N |")
        both("|---|---|---|---|---|---|")
        for mode in ("pos", "abs"):
            sub = [r for r in rs if f(r[f"N5_lead_R_{mode}"]) is not None
                   and f(r[f"N5_lead_R_{mode}"]) >= 0.05]
            cells = []
            for c in CONS:
                k = f"N5_same_{c}_{mode}"
                a = sum(1 for r in sub if r.get(k) == "True")
                cells.append(f"{100.0*a/len(sub):.2f}% ({a}/{len(sub)})"
                             if sub else "n/a(0)")
            both(f"| {mode} | {len(sub)} | " + " | ".join(cells) + " |")
        both("")
        both("### Error means, expiry day vs other days")
        both("")
        both("| scope | runs | E_raw P | E_raw B2 | E_raw N | E_shape P | E_shape B2 | E_shape N | T err P | T err B2 | T err N |")
        both("|---|---|---|---|---|---|---|---|---|---|---|")
        for lab, sel in (("expiry day", lambda r: r["expiry_day"] == "True"),
                         ("other days", lambda r: r["expiry_day"] != "True")):
            sub = [r for r in rs if sel(r)]
            cells = []
            for key in ("ALL_E_raw_", "ALL_E_shape_", "ALL_T_err_"):
                for c in ("P", "B2", "N"):
                    v = [f(r[key + c]) for r in sub if f(r[key + c]) is not None]
                    cells.append(g(mean(v)))
            both(f"| {lab} | {len(sub)} | " + " | ".join(cells) + " |")
        both("")
        both("### By day: days on which N's mean is LOWER than P's")
        both("")
        days = sorted({r["day"] for r in rs})
        line = []
        for lab, key in (("E_raw", "ALL_E_raw_"), ("E_shape", "ALL_E_shape_"),
                         ("T error", "ALL_T_err_")):
            n = 0
            for d in days:
                sub = [r for r in rs if r["day"] == d]
                p = mean([f(r[key + "P"]) for r in sub if f(r[key + "P"]) is not None])
                nn = mean([f(r[key + "N"]) for r in sub if f(r[key + "N"]) is not None])
                if p is not None and nn is not None and nn < p:
                    n += 1
            line.append(f"{lab} {n}/{len(days)}")
        both("N lower than P on: " + " | ".join(line) + ".")
        both("")

    # ---------------- item 4 ----------------
    WORSE = {"NIFTY": ["2026-10-09"],
             "SENSEX": ["2026-10-27", "2026-10-28", "2026-10-29",
                        "2026-11-11", "2026-11-17", "2026-11-19"]}
    both("## Item 4 — the days where N's mean E_shape exceeds P's")
    both("")
    both(f"Frozen flag in `fix/replay_v2/runs.csv`: "
         f"{'column `frozen`' if frozen_col else 'NONE — no such column'}.")
    both("")
    hdr = ("| symbol | day | runs | dte | E_sh P | E_sh B1 | E_sh B2 | E_sh N | "
           "mean abs(T_R) | mean fwd gap | zero rate OI-wt | missing rate OI-wt | "
           "fallback share GR | mean sigma_atm | gamma<1e-4 OI-wt | top strike "
           "share gross_R | frozen runs |")
    both(hdr)
    both("|" + "---|" * 17)

    def line_for(sym, label, sub):
        n = len(sub)
        def mn(k):
            v = [f(r[k]) for r in sub if f(r[k]) is not None]
            return mean(v)
        es = [g(mn("ALL_E_shape_" + c), 5) for c in CONS]
        tr = mean([abs(f(r["ALL_T_R"])) for r in sub if f(r["ALL_T_R"]) is not None])
        fb = mn("FB")
        sg = mn("sigma_atm")
        k1 = mn("K1_share_GR")
        dte = mn("dte_cal")
        ot = om = oz = os_ = 0.0
        tg = []
        for r in sub:
            e = extra.get(r["run_id"])
            if not e:
                continue
            ot += f(e["oi_tot"]) or 0
            om += f(e["oi_missing"]) or 0
            oz += f(e["oi_zero"]) or 0
            os_ += f(e["oi_sub1e4"]) or 0
            if f(e["top_gR_share"]) is not None:
                tg.append(f(e["top_gR_share"]))
        fr = (sum(1 for r in sub if rv2.get(r["run_id"], {}).get(frozen_col) == "True")
              if frozen_col else None)
        return (f"| {sym} | {label} | {n} | {g(dte,3)} | " + " | ".join(es) +
                f" | {g(tr,4)} | {g(fb,3)} | "
                f"{100*oz/ot:.3f}% | {100*om/ot:.3f}% | {g(k1,3)} | {g(sg,4)} | "
                f"{100*os_/ot:.3f}% | {g(mean(tg),4)} | "
                f"{fr if fr is not None else 'n/a'} |")

    for sym in SYMS:
        rs = [r for r in rows if r["sym"] == sym]
        for d in WORSE[sym]:
            both(line_for(sym, d, [r for r in rs if r["day"] == d]))
        both(line_for(sym, "ALL OTHER DAYS",
                      [r for r in rs if r["day"] not in WORSE[sym]]))
    both("")

    (HERE / "decomp.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(SCREEN))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
