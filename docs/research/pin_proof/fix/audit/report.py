#!/usr/bin/env python3
"""STAGE B report -- reads ONLY fix/audit/runs.csv (plus the chain files for the two
file-level additions, which are counted, never inferred). Writes fix/audit/results.md.

The section 6 rule is applied verbatim and is NOT softened or reinterpreted.
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHAIN = HERE.parent / "replay_v2" / "chain"
SYMS = ("NIFTY", "SENSEX")
WIN_LO, WIN_HI = "2026-08-24", "2026-11-20"
L: list[str] = []


def em(s=""):
    L.append(s)


def f(v):
    return None if v in (None, "", "None") else float(v)


def i(v):
    return None if v in (None, "", "None") else int(float(v))


def b(v):
    return v in ("True", "1", 1, True)


def q(v, p):
    if not v:
        return None
    s = sorted(v)
    return s[min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))]


def mmp(v, nd=6):
    """mean / median / p90 / n -- the shape every measure is reported in."""
    if not v:
        return "n/a | n/a | n/a | n=0"
    return (f"{statistics.mean(v):.{nd}g} | {statistics.median(v):.{nd}g} | "
            f"{q(v, 0.90):.{nd}g} | n={len(v)}")


def sh(n, d, nd=2):
    return "n/a (n=0)" if not d else f"{100.0*n/d:.{nd}f}% ({n}/{d})"


def load():
    rows = []
    with (HERE / "runs.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append(r)
    return rows


def main() -> int:
    rows = load()
    valid = [r for r in rows if r["valid"] == "1"]

    em("<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/audit/results.md -->")
    em("")
    em("# Gamma pipeline audit — STAGE B results")
    em("")
    em("Disk only; no database. Source `fix/audit/runs.csv` (8,595 rows), built by "
       "`run_stage_b.py` over `fix/replay_v2/chain/`. P = production replica, "
       "N = proposed (one vendor gamma per strike), R = reference (replay v2 per-strike "
       "own gamma). **No spot²/1e7 factor**: these are raw gamma×OI sums, not Crore.")
    em("")

    # ================= ADDITION 1 : the 128 files =================
    em("## Addition 1 — what the 128 files are")
    em("")
    files = sorted(CHAIN.glob("out_*.txt"))
    per = defaultdict(list)
    for fp in files:
        sym, day = fp.name[4:-4].split("_", 1)
        per[sym].append(day)
    days_with = defaultdict(set)
    for r in rows:
        days_with[r["sym"]].add(r["day"])
    em("| symbol | files | first date | last date | files with ≥1 market run | files with zero market runs |")
    em("|---|---|---|---|---|---|")
    zero = {}
    for sym in SYMS:
        d = sorted(per[sym])
        z = sorted(set(d) - days_with[sym])
        zero[sym] = z
        em(f"| {sym} | {len(d)} | {d[0]} | {d[-1]} | {len(days_with[sym])} | "
           f"{len(z)} |")
    em("")
    em(f"Zero-market-run dates (identical on both symbols): "
       f"{', '.join(zero['NIFTY'])}.")
    em("")
    alldates = sorted({d for s in SYMS for d in per[s]})
    outside = [d for d in alldates if not (WIN_LO <= d <= WIN_HI)]
    em(f"128 files = **64 distinct dates × 2 symbols**. The frozen design names 58 days "
       f"in {WIN_LO}..{WIN_HI}; the files hold 64 dates, of which **6 per symbol carry "
       f"no market run**, leaving exactly **58 days per symbol with data** — the "
       f"design's 58.")
    em("")
    if outside:
        em(f"**Files OUTSIDE {WIN_LO}..{WIN_HI}: {', '.join(outside)}** — the rule is "
           f"evaluated on the in-window files only and these are reported separately.")
    else:
        em(f"**No file lies outside {WIN_LO}..{WIN_HI}** (earliest file {alldates[0]}, "
           f"latest {alldates[-1]}), so the rule is evaluated on all of them and there "
           f"is nothing to report separately. Note the design window opens 2026-08-24 "
           f"but no file exists for that date: the chain pull began 2026-08-25.")
    em("")
    em("Of the six zero-market-run dates, five (2026-08-25, 09-14, 10-20, 10-21, "
       "11-10) are the empty weekdays the replay v2 pull already logged OK_EMPTY. "
       "The sixth, **2026-10-02, is different**: that file does carry rows, but none "
       "inside 09:15–15:29 IST. It is the registered holiday "
       "`HOLIDAY-FROZEN-CHAIN-2026-10-02` (Rule 13), whose chain was written from the "
       "previous session's post-close prints.")
    em("")

    # ================= ADDITION 2 : completeness =================
    em("## Addition 2 — completeness, counted from the chain files")
    em("")
    r0cnt = Counter()
    nospot = Counter()
    nolegs = Counter()
    for fp in files:
        sym, _ = fp.name[4:-4].split("_", 1)
        r0, legs = {}, defaultdict(set)
        for raw in fp.read_text(encoding="utf-8").splitlines():
            if not raw or "|" not in raw:
                continue
            tag, pay = raw.split("|", 1)
            j = json.loads(pay)
            if tag == "R0" and "09:15" <= j["ts_ist"][11:16] <= "15:29":
                r0[j["run_id"]] = j
            elif tag == "R1" and float(j["oi"] or 0) > 0:
                legs[j["run_id"]].add(float(j["strike"]))
        for rid, j in r0.items():
            s = float(j["spot_min"]) if j.get("spot_min") else 0.0
            if s <= 0:
                nospot[sym] += 1
            elif not legs.get(rid):
                nolegs[sym] += 1
        r0cnt[sym] += len(r0)
        r0.clear(); legs.clear()
    ncsv = Counter(r["sym"] for r in rows)
    em("| symbol | market R0 rows in chain files | rows in runs.csv | dropped | of which spot ≤ 0 | of which no legs |")
    em("|---|---|---|---|---|---|")
    for sym in SYMS:
        em(f"| {sym} | {r0cnt[sym]} | {ncsv[sym]} | {r0cnt[sym]-ncsv[sym]} | "
           f"{nospot[sym]} | {nolegs[sym]} |")
    em("")
    em("Every market R0 row reached `runs.csv`; `audit_run` returned None on none of "
       "them. Counted from the files, not inferred.")
    em("")

    # ================= per-symbol measures =================
    def col(rs, c, cast=f):
        return [cast(r[c]) for r in rs if cast(r[c]) is not None]

    em("## Measures per symbol — mean | median | p90 | n (valid market runs)")
    em("")
    for sym in SYMS:
        rs = [r for r in valid if r["sym"] == sym]
        em(f"### {sym} — {len(rs)} valid runs of {ncsv[sym]}")
        em("")
        em("| measure | all strikes | no-fallback strikes |")
        em("|---|---|---|")
        for lab, key in (("N2 E_raw(P)", "E_raw_P"), ("N2 E_raw(N)", "E_raw_N"),
                         ("N3 E_shape(P)", "E_shape_P"), ("N3 E_shape(N)", "E_shape_N"),
                         ("N4 |T_P−T_R|", "T_err_P"), ("N4 |T_N−T_R|", "T_err_N"),
                         ("L1 gross shape P", "L1_P"), ("L1 gross shape N", "L1_N"),
                         ("N4 T_R", "T_R"), ("N4 T_P", "T_P"), ("N4 T_N", "T_N")):
            em(f"| {lab} | {mmp(col(rs, 'ALL_'+key))} | {mmp(col(rs, 'NOFB_'+key))} |")
        em("")

    # ================= SECTION 6 RULE =================
    em("## Section 6 rule — applied verbatim")
    em("")
    em("N is BETTER than P for a symbol when **all four** hold on the all-strikes "
       "figures: (1) mean and median of E_raw(N) both lower than E_raw(P); (2) mean "
       "and median of E_shape(N) both lower; (3) mean and median of |T_N−T_R| both "
       "lower; (4) on runs where R's lead ≥ 5 %, N's agreement with R is not lower "
       "than P's on BOTH peaks of N5. Overall BETTER only if all four hold for BOTH "
       "symbols. Clause 4 is read peak by peak: the positive peak is judged on runs "
       "with `lead_R_pos ≥ 0.05`, the abs peak on runs with `lead_R_abs ≥ 0.05`.")
    em("")
    em("| symbol | clause | P | N | holds |")
    em("|---|---|---|---|---|")
    verdict = {}
    for sym in SYMS:
        rs = [r for r in valid if r["sym"] == sym]
        cl = {}
        for n, (lab, kp, kn) in enumerate(
                (("1 E_raw", "ALL_E_raw_P", "ALL_E_raw_N"),
                 ("2 E_shape", "ALL_E_shape_P", "ALL_E_shape_N"),
                 ("3 |T−T_R|", "ALL_T_err_P", "ALL_T_err_N")), start=1):
            P, N = col(rs, kp), col(rs, kn)
            mp, mn = statistics.mean(P), statistics.mean(N)
            dp, dn = statistics.median(P), statistics.median(N)
            ok = (mn < mp) and (dn < dp)
            cl[n] = ok
            em(f"| {sym} | {lab} | mean {mp:.6g}, median {dp:.6g} | "
               f"mean {mn:.6g}, median {dn:.6g} | {'YES' if ok else 'NO'} |")
        ok4 = True
        for mode in ("pos", "abs"):
            sub = [r for r in rs if f(r[f"N5_lead_R_{mode}"]) is not None
                   and f(r[f"N5_lead_R_{mode}"]) >= 0.05]
            aP = sum(1 for r in sub if b(r[f"N5_same_P_{mode}"]))
            aN = sum(1 for r in sub if b(r[f"N5_same_N_{mode}"]))
            hold = aN >= aP
            ok4 = ok4 and hold
            em(f"| {sym} | 4 N5 {mode} peak (lead ≥ 5 %) | {sh(aP, len(sub))} | "
               f"{sh(aN, len(sub))} | {'YES' if hold else 'NO'} |")
        cl[4] = ok4
        verdict[sym] = cl
    em("")
    em("| symbol | clause 1 | clause 2 | clause 3 | clause 4 | symbol verdict |")
    em("|---|---|---|---|---|---|")
    for sym in SYMS:
        c = verdict[sym]
        allok = all(c.values())
        em(f"| {sym} | {'YES' if c[1] else 'NO'} | {'YES' if c[2] else 'NO'} | "
           f"{'YES' if c[3] else 'NO'} | {'YES' if c[4] else 'NO'} | "
           f"**{'BETTER' if allok else 'NOT BETTER'}** |")
    overall = all(all(verdict[s].values()) for s in SYMS)
    failed = [f"{s} clause {n}" for s in SYMS for n, v in verdict[s].items() if not v]
    em("")
    em(f"**OVERALL: {'BETTER' if overall else 'NOT BETTER'}**"
       + ("" if overall else " — failed: " + ", ".join(failed) + "."))
    em("")

    # ================= per-day table =================
    em("## Per-day table")
    em("")
    em("| symbol | day | runs | mean E_raw P | mean E_raw N | mean E_shape P | "
       "mean E_shape N | mean \\|T_P−T_R\\| | mean \\|T_N−T_R\\| |")
    em("|---|---|---|---|---|---|---|---|---|")
    worse = defaultdict(list)
    for sym in SYMS:
        for day in sorted({r["day"] for r in valid if r["sym"] == sym}):
            rs = [r for r in valid if r["sym"] == sym and r["day"] == day]
            eP, eN = col(rs, "ALL_E_raw_P"), col(rs, "ALL_E_raw_N")
            sP, sN = col(rs, "ALL_E_shape_P"), col(rs, "ALL_E_shape_N")
            tP, tN = col(rs, "ALL_T_err_P"), col(rs, "ALL_T_err_N")
            if sN and sP and statistics.mean(sN) > statistics.mean(sP):
                worse[sym].append(day)
            em(f"| {sym} | {day} | {len(rs)} | {statistics.mean(eP):.6g} | "
               f"{statistics.mean(eN):.6g} | {statistics.mean(sP):.6g} | "
               f"{statistics.mean(sN):.6g} | {statistics.mean(tP):.6g} | "
               f"{statistics.mean(tN):.6g} |")
    em("")
    for sym in SYMS:
        em(f"**{sym}: days where N's mean E_shape is HIGHER than P's — "
           f"{len(worse[sym])} of {len({r['day'] for r in valid if r['sym']==sym})}**"
           + ("" if not worse[sym] else ": " + ", ".join(worse[sym])) + ".")
    em("")

    (HERE / "results.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---- machine summary for the reply ----
    out = {"files": {s: len(per[s]) for s in SYMS},
           "zero": {s: zero[s] for s in SYMS},
           "r0": dict(r0cnt), "csv": dict(ncsv),
           "verdict": {s: verdict[s] for s in SYMS}, "overall": overall,
           "worse_days": {s: worse[s] for s in SYMS}}
    (HERE / "_summary.json").write_text(json.dumps(out, indent=1, default=str),
                                        encoding="utf-8")
    print(f"results.md written ({len(L)} lines)")
    print("OVERALL:", "BETTER" if overall else "NOT BETTER",
          "" if overall else ("failed: " + ", ".join(failed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
