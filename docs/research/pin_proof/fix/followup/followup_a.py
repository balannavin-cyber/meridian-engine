#!/usr/bin/env python3
"""VS follow-up, part A. POST-HOC diagnostics -- not frozen measures.

Disk only. Reads fix/replay_v2/runs.csv and, for A2's rank question, the chain pulls
under fix/replay_v2/chain/ ONE SYMBOL-DAY AT A TIME with every per-strike map dropped
as soon as the run is used (box: 1,910 MB, no swap).

No pass marks anywhere; every figure carries its n.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2DIR = HERE.parent / "replay_v2"
sys.path.insert(0, str(V2DIR))
sys.path.insert(0, str(HERE.parent / "replay"))
sys.path.insert(0, str(HERE.parent.parent / "lookback_v5"))

from constructions_v2 import vs_scores          # noqa: E402
from analyze_v5 import compute_run              # noqa: E402

SYMS = ("NIFTY", "SENSEX")
STEP = {"NIFTY": 50.0, "SENSEX": 100.0}
SEEN = {"2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"}
L: list[str] = []


def em(s=""):
    L.append(s)


def f(x, nd=2):
    return "-" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"


def pct(n, d):
    return float("nan") if not d else 100.0 * n / d


def sh(n, d, nd=1):
    return "n/a(0)" if not d else f"{pct(n,d):.{nd}f}% ({n}/{d})"


def num(v):
    return None if v in (None, "", "None") else float(v)


def load():
    out = []
    with (V2DIR / "runs.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            for k in ("S", "B", "V2", "VS", "FV", "F", "K", "K_lead", "R", "BL", "FB",
                      "call_wall", "put_wall", "atm"):
                r[k] = num(r[k])
            r["dte_cal"] = int(r["dte_cal"]) if r["dte_cal"] else None
            r["valid"] = r["valid"] == "True"
            r["frozen"] = r["frozen"] == "True"
            out.append(r)
    return out


def main() -> int:
    runs = load()
    mkt = [r for r in runs if r["segment"] == "market" and r["valid"]]

    em("<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/followup/followup.md -->")
    em("")
    em("# VS follow-up — POST-HOC diagnostics")
    em("")
    em("**POST-HOC. Not frozen measures, no pass marks.** Source: "
       "`fix/replay_v2/runs.csv` (9,719 runs) and the chain pulls under "
       "`fix/replay_v2/chain/`. Market runs are 09:15–15:29 IST unless stated. "
       "Steps: NIFTY 50, SENSEX 100.")
    em("")

    # ---------------- A1 ----------------
    em("## A1 — expiry days (dte_cal = 0) — POST-HOC")
    em("")
    em("| symbol | date | SEEN | mkt runs | clear-lead | VS=K clear | V2=K clear | "
       "VS=K all valid | med abs(VS−S) | med abs(B−S) | B present |")
    em("|---|---|---|---|---|---|---|---|---|---|---|")
    for sym in SYMS:
        step = STEP[sym]
        days = sorted({r["day"] for r in mkt if r["sym"] == sym and r["dte_cal"] == 0})
        pool = []
        for d in days:
            rs = [r for r in mkt if r["sym"] == sym and r["day"] == d
                  and r["dte_cal"] == 0]
            pool += rs
            hi = [r for r in rs if r["K_lead"] is not None and r["K_lead"] >= 0.05]
            bs = [r for r in rs if r["B"] is not None]
            em(f"| {sym} | {d} | {'SEEN' if d in SEEN else 'UNSEEN'} | {len(rs)} | "
               f"{len(hi)} | "
               f"{sh(sum(1 for r in hi if r['VS']==r['K']),len(hi))} | "
               f"{sh(sum(1 for r in hi if r['V2']==r['K']),len(hi))} | "
               f"{sh(sum(1 for r in rs if r['VS']==r['K']),len(rs))} | "
               f"{f(statistics.median([abs(r['VS']-r['S'])/step for r in rs]))} | "
               f"{f(statistics.median([abs(r['B']-r['S'])/step for r in bs])) if bs else '-'} | "
               f"{len(bs)}/{len(rs)} |")
        hi = [r for r in pool if r["K_lead"] is not None and r["K_lead"] >= 0.05]
        bs = [r for r in pool if r["B"] is not None]
        em(f"| **{sym}** | **pooled** | — | **{len(pool)}** | **{len(hi)}** | "
           f"**{sh(sum(1 for r in hi if r['VS']==r['K']),len(hi))}** | "
           f"**{sh(sum(1 for r in hi if r['V2']==r['K']),len(hi))}** | "
           f"**{sh(sum(1 for r in pool if r['VS']==r['K']),len(pool))}** | "
           f"**{f(statistics.median([abs(r['VS']-r['S'])/step for r in pool]))}** | "
           f"**{f(statistics.median([abs(r['B']-r['S'])/step for r in bs])) if bs else '-'}** | "
           f"**{len(bs)}/{len(pool)}** |")
    em("")

    # ---------------- A2 ----------------
    em("## A2 — near-ties (K lead < 5 %), all 58 days — POST-HOC")
    em("")
    nt = {}
    for sym in SYMS:
        nt[sym] = [r for r in mkt if r["sym"] == sym
                   and r["K_lead"] is not None and r["K_lead"] < 0.05]
    em("| symbol | runs | VS = K | abs(VS−K) ≤1 step | ≤2 steps | median | max |")
    em("|---|---|---|---|---|---|---|")
    for sym in SYMS:
        step = STEP[sym]
        rs = nt[sym]
        dif = [abs(r["VS"] - r["K"]) / step for r in rs
               if r["VS"] is not None and r["K"] is not None]
        em(f"| {sym} | {len(rs)} | "
           f"{sh(sum(1 for r in rs if r['VS']==r['K']),len(rs))} | "
           f"{sh(sum(1 for d in dif if d<=1),len(dif))} | "
           f"{sh(sum(1 for d in dif if d<=2),len(dif))} | "
           f"{f(statistics.median(dif)) if dif else '-'} | "
           f"{f(max(dif)) if dif else '-'} |")
    em("")

    # --- rank of VS's strike under K's own score, re-running compute_run ---
    want = defaultdict(set)
    for sym in SYMS:
        for r in nt[sym]:
            want[(sym, r["day"])].add(r["run_id"])
    rank = {s: {"r1": 0, "r2": 0, "other": 0, "miss": 0} for s in SYMS}
    for (sym, day), ids in sorted(want.items()):
        fp = V2DIR / "chain" / f"out_{sym}_{day}.txt"
        r0, legs = {}, {}
        for raw in fp.read_text(encoding="utf-8").splitlines():
            if not raw or "|" not in raw:
                continue
            tag, pay = raw.split("|", 1)
            j = json.loads(pay)
            if j["run_id"] not in ids:
                continue
            if tag == "R0":
                r0[j["run_id"]] = j
            elif tag == "R1":
                e = legs.setdefault(j["run_id"], {}).setdefault(
                    float(j["strike"]),
                    {"c_gamma": None, "p_gamma": None, "c_oi": 0.0, "p_oi": 0.0,
                     "c_px": 0.0, "p_px": 0.0})
                oi = float(j["oi"]) if j.get("oi") not in (None, "") else 0.0
                px = float(j["ltp"]) if j.get("ltp") not in (None, "") else 0.0
                if j["ot"] == "CE":
                    e["c_gamma"], e["c_oi"], e["c_px"] = j.get("gamma"), oi, px
                else:
                    e["p_gamma"], e["p_oi"], e["p_px"] = j.get("gamma"), oi, px
        for rid, meta in r0.items():
            rows = {k: v for k, v in legs.get(rid, {}).items()
                    if v["c_oi"] > 0 or v["p_oi"] > 0}
            S = float(meta["spot_min"])
            cr = compute_run(sym, meta["ts_ist"][:10], meta["ts_ist"][11:16], S,
                             meta["expiry"], rows, [])
            if not cr.get("valid"):
                rank[sym]["miss"] += 1
                cr.clear()
                continue
            ks = {k: cr["g"][k] * (rows[k]["c_oi"] + rows[k]["p_oi"]) for k in cr["g"]}
            order = [k for k, _ in sorted(ks.items(),
                     key=lambda kv: (kv[1], -abs(kv[0] - S), -kv[0]), reverse=True)]
            vp, _, _ = __import__("analyze_v5").pick(vs_scores(rows), S)
            if vp is None:
                rank[sym]["miss"] += 1
            elif order and vp == order[0]:
                rank[sym]["r1"] += 1
            elif len(order) > 1 and vp == order[1]:
                rank[sym]["r2"] += 1
            else:
                rank[sym]["other"] += 1
            for k in ("_rows", "g", "g_flat", "sigma_k"):
                cr.pop(k, None)
            cr.clear()
            rows.clear()
        r0.clear(); legs.clear()
    em("VS's strike ranked by **K's own score**, on the same near-tie runs "
       "(compute_run re-run from the chain pulls, one symbol-day at a time):")
    em("")
    em("| symbol | near-tie runs | VS is K's 1st | K's 2nd | 1st or 2nd | lower | not scored |")
    em("|---|---|---|---|---|---|---|")
    for sym in SYMS:
        c = rank[sym]
        tot = c["r1"] + c["r2"] + c["other"] + c["miss"]
        em(f"| {sym} | {tot} | {sh(c['r1'],tot)} | {sh(c['r2'],tot)} | "
           f"{sh(c['r1']+c['r2'],tot)} | {sh(c['other'],tot)} | {c['miss']} |")
    em("")

    # ---------------- A4 ----------------
    em("## A4 — symbol-days where VS misses either day mark — POST-HOC")
    em("")
    em("Marks: 95 % of clear-lead runs, 85 % of all valid market runs.")
    em("")
    em("| symbol | date | SEEN | dte@open | mkt | clear-lead | VS clear | VS all | "
       "V2 clear | F clear | med R | med BL | med FB | frozen | med abs(VS−K) where differ |")
    em("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    nmiss = {s: 0 for s in SYMS}
    for sym in SYMS:
        step = STEP[sym]
        for d in sorted({r["day"] for r in mkt if r["sym"] == sym}):
            rs = [r for r in mkt if r["sym"] == sym and r["day"] == d]
            hi = [r for r in rs if r["K_lead"] is not None and r["K_lead"] >= 0.05]
            a = pct(sum(1 for r in hi if r["VS"] == r["K"]), len(hi))
            b = pct(sum(1 for r in rs if r["VS"] == r["K"]), len(rs))
            if a >= 95.0 and b >= 85.0:
                continue
            nmiss[sym] += 1
            dif = [abs(r["VS"] - r["K"]) / step for r in rs
                   if r["VS"] is not None and r["K"] is not None and r["VS"] != r["K"]]
            md_ = lambda key: statistics.median([r[key] for r in rs if r[key] is not None]) \
                if any(r[key] is not None for r in rs) else None
            em(f"| {sym} | {d} | {'SEEN' if d in SEEN else 'UNSEEN'} | "
               f"{rs[0]['dte_cal']} | {len(rs)} | {len(hi)} | {f(a,1)}% | {f(b,1)}% | "
               f"{f(pct(sum(1 for r in hi if r['V2']==r['K']),len(hi)),1)}% | "
               f"{f(pct(sum(1 for r in hi if r['F']==r['K']),len(hi)),1)}% | "
               f"{f(md_('R'),4)} | {f(md_('BL'),4)} | {f(md_('FB'))} | "
               f"{sum(1 for r in rs if r['frozen'])} | "
               f"{f(statistics.median(dif),1) if dif else '-'} |")
    em("")
    em("Symbol-days missing at least one VS mark: "
       + ", ".join(f"{s} {nmiss[s]} of 58" for s in SYMS) + ".")
    em("")
    (HERE / "_partA.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    sys.stdout.write("\n".join(L) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
