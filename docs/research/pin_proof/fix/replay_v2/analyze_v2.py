#!/usr/bin/env python3
"""Pin live replay v2 -- measures M1..M8 and the decision rule.

Disk only. Reads replay_v2/scored/*.jsonl -- the PER-RUN scored records only, never a
per-strike map, never load_runs/measures/main of analyze_v5.py. Writes results.md,
runs.csv and nothing else outside replay_v2/.

PRECONDITION, asserted in code: _pull_v2.log's last line is exactly 'ALL 128 DONE'
(128 = 64 weekdays x 2 symbols) and it carries no STOP line. Otherwise exit 2.

Decision rule, applied verbatim and not reinterpreted: on MARKET runs of UNSEEN days,
per symbol, a construction is enough if BOTH
  (1) pooled over those days it is on K's strike on >= 95 % of runs with K lead >= 5 %;
  (2) on >= 90 % of those days it meets both day marks (95 % of clear-lead runs AND
      85 % of all valid runs).
It must hold on both symbols.
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYMS = ("NIFTY", "SENSEX")
STEP = {"NIFTY": 50.0, "SENSEX": 100.0}
CONS = ("V2", "VS", "FV", "F")
ALLPINS = ("B", "V2", "VS", "FV", "F", "K")
SEEN = {"2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"}
MIN_RUNS = 60

L: list[str] = []


def em(s: str = "") -> None:
    L.append(s)


def pct(n, d):
    return float("nan") if not d else 100.0 * n / d


def sh(n, d, nd=1):
    return "n/a(0)" if not d else f"{pct(n,d):.{nd}f}% ({n}/{d})"


def q_at(v, p):
    if not v:
        return float("nan")
    s = sorted(v)
    return s[min(len(s) - 1, max(0, int(round(p * (len(s) - 1)))))]


def md(v, nd=2):
    return "n/a(0)" if not v else f"{statistics.median(v):.{nd}f} (n={len(v)})"


def precondition():
    lg = HERE / "_pull_v2.log"
    if not lg.exists():
        return False, "_pull_v2.log missing"
    lines = [x for x in lg.read_text(encoding="utf-8").splitlines() if x.strip()]
    d, b, n = date(2026, 8, 25), date(2026, 11, 20), 0
    while d <= b:
        if d.weekday() < 5:
            n += 1
        d += timedelta(days=1)
    want = f"ALL {n*2} DONE"
    stops = [x for x in lines if x.startswith("STOP")]
    if stops:
        return False, f"{len(stops)} STOP line(s); first: {stops[0]}"
    if lines[-1] != want:
        return False, f"last line {lines[-1]!r}, expected {want!r}"
    return True, f"{want}; no STOP line; {n} weekdays"


def load():
    runs = []
    for fp in sorted((HERE / "scored").glob("*.jsonl")):
        for line in fp.read_text(encoding="utf-8").splitlines():
            if line.strip():
                runs.append(json.loads(line))
    runs.sort(key=lambda r: (r["sym"], r["day"], r["ts_ist"]))
    return runs


def main() -> int:
    ok, why = precondition()
    if not ok:
        print(f"exit 2: precondition failed -- {why}")
        return 2
    print(f"precondition OK: {why}")

    runs = load()
    # frozen: a run AFTER the day's first run at or after 09:15 IST whose whole-chain
    # call OI and put OI both equal that run's.
    bysd = defaultdict(list)
    for r in runs:
        bysd[(r["sym"], r["day"])].append(r)
    for k in bysd:
        rs = sorted(bysd[k], key=lambda r: r["ts_ist"])
        ref = next((r for r in rs if r["ts_ist"][11:16] >= "09:15"), None)
        seen_ref = False
        for r in rs:
            if ref is not None and r["run_id"] == ref["run_id"]:
                seen_ref = True
                r["frozen"] = False
                continue
            r["frozen"] = bool(ref) and seen_ref \
                and r["tot_oi_call"] == ref["tot_oi_call"] \
                and r["tot_oi_put"] == ref["tot_oi_put"]
    for r in runs:
        r.setdefault("frozen", False)
        r["unseen"] = r["day"] not in SEEN

    mkt = [r for r in runs if r["segment"] == "market" and r.get("valid")]
    # short symbol-days: fewer than 60 valid market runs -> reported, left out of counts
    nmkt = Counter((r["sym"], r["day"]) for r in mkt)
    short = sorted(k for k, v in nmkt.items() if v < MIN_RUNS)
    shortset = set(short)
    counted = {k for k in nmkt if k not in shortset}

    em("<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/fix/replay_v2/results.md -->")
    em("")
    em("# Pin live replay v2 — results")
    em("")
    em("Frozen design sha256 "
       "`d2d87a85d2854dc19feb762344e266277d27d7dfde2b7fb6a88484e6e4b19a14`. Read-only. "
       "Weekdays 2026-08-25..2026-11-20, NIFTY and SENSEX never pooled. "
       "`analyze_v5.py` sha256 "
       "`4958435201740e86acb9791781abe764a4df42d09eefab987e7bcbd805086979`, "
       "self_tests 18/18; VS/FV self-tests 16/16. Wall source: stored "
       "`gex_cycle_history.call_wall_strike` / `put_wall_strike`.")
    em("")
    em(f"SEEN days (2026-11-16..20) are marked; all others UNSEEN. "
       f"A symbol-day with fewer than {MIN_RUNS} valid market runs is reported and "
       f"left out of the day counts: **{len(short)}** such symbol-day(s)"
       + (" — " + ", ".join(f"{s} {d} ({nmkt[(s,d)]} runs)" for s, d in short)
          if short else "") + ".")
    em("")

    # ------------- per symbol-day shares -------------
    daily = {}
    for (sym, day) in sorted(nmkt):
        rs = [r for r in mkt if r["sym"] == sym and r["day"] == day]
        hi = [r for r in rs if r.get("K_lead") is not None and r["K_lead"] >= 0.05]
        row = {"n_mkt": len(rs), "n_hi": len(hi), "unseen": day not in SEEN}
        for c in CONS:
            row[f"{c}_hi"] = pct(sum(1 for r in hi
                                     if r.get(c) is not None and r[c] == r["K"]), len(hi))
            row[f"{c}_all"] = pct(sum(1 for r in rs
                                      if r.get(c) is not None and r[c] == r["K"]), len(rs))
            row[f"{c}_mark"] = (row[f"{c}_hi"] >= 95.0 and row[f"{c}_all"] >= 85.0)
        for d2, lab in ((("R",), "R"), (("BL",), "BL"), (("FB",), "FB")):
            vals = [r[d2[0]] for r in rs if r.get(d2[0]) is not None]
            row[f"med_{lab}"] = statistics.median(vals) if vals else None
        row["dte_open"] = rs[0]["dte_cal"] if rs else None
        daily[(sym, day)] = row

    # ------------- DECISION -------------
    em("## Decision rule")
    em("")
    em("Market runs of UNSEEN days. (1) pooled ≥ 95 % on K-lead ≥ 5 % runs; "
       "(2) ≥ 90 % of those days meet both day marks (95 % clear-lead, 85 % all valid). "
       "Both symbols must hold.")
    em("")
    em("| symbol | construction | pooled on K-lead≥5% | need ≥95% | days meeting both marks | need ≥90% | verdict |")
    em("|---|---|---|---|---|---|---|")
    dec = {}
    for sym in SYMS:
        us = [r for r in mkt if r["sym"] == sym and r["unseen"]
              and (r["sym"], r["day"]) in counted]
        hi = [r for r in us if r.get("K_lead") is not None and r["K_lead"] >= 0.05]
        udays = sorted(d for (s, d) in counted if s == sym and d not in SEEN)
        for c in CONS:
            a = sum(1 for r in hi if r.get(c) is not None and r[c] == r["K"])
            p1 = pct(a, len(hi))
            nm = sum(1 for d in udays if daily[(sym, d)][f"{c}_mark"])
            p2 = pct(nm, len(udays))
            v = (p1 >= 95.0) and (p2 >= 90.0)
            dec[(sym, c)] = (p1, a, len(hi), p2, nm, len(udays), v)
            em(f"| {sym} | {c} | {p1:.2f}% ({a}/{len(hi)}) | "
               f"{'PASS' if p1>=95 else 'FAIL'} | {nm}/{len(udays)} = {p2:.1f}% | "
               f"{'PASS' if p2>=90 else 'FAIL'} | **{'PASS' if v else 'FAIL'}** |")
    em("")
    em("| construction | NIFTY | SENSEX | overall (both symbols) |")
    em("|---|---|---|---|")
    for c in CONS:
        n_ok = dec[("NIFTY", c)][6]
        s_ok = dec[("SENSEX", c)][6]
        em(f"| {c} | {'PASS' if n_ok else 'FAIL'} | {'PASS' if s_ok else 'FAIL'} | "
           f"**{'ENOUGH' if (n_ok and s_ok) else 'NOT ENOUGH'}** |")
    em("")

    # ------------- M1 -------------
    em("## M1 — per-day shares, summarised across days")
    em("")
    em("| symbol | scope | construction | days | median clear-lead | p10 | min | "
       "median all-valid | p10 | min | days meeting both marks |")
    em("|---|---|---|---|---|---|---|---|---|---|---|")
    for sym in SYMS:
        for scope in ("UNSEEN", "ALL"):
            ds = sorted(d for (s, d) in counted if s == sym
                        and (scope == "ALL" or d not in SEEN))
            for c in CONS:
                hiv = [daily[(sym, d)][f"{c}_hi"] for d in ds
                       if not math.isnan(daily[(sym, d)][f"{c}_hi"])]
                alv = [daily[(sym, d)][f"{c}_all"] for d in ds]
                nm = sum(1 for d in ds if daily[(sym, d)][f"{c}_mark"])
                em(f"| {sym} | {scope} | {c} | {len(ds)} | "
                   f"{statistics.median(hiv):.1f}% | {q_at(hiv,.10):.1f}% | "
                   f"{min(hiv):.1f}% | {statistics.median(alv):.1f}% | "
                   f"{q_at(alv,.10):.1f}% | {min(alv):.1f}% | "
                   f"{nm}/{len(ds)} = {pct(nm,len(ds)):.1f}% |")
    em("")

    # ------------- M2 -------------
    em("## M2 — pooled over UNSEEN days, by clock segment")
    em("")
    em("| symbol | segment | construction | runs | = K (all) | runs K-lead≥5% | = K (clear lead) |")
    em("|---|---|---|---|---|---|---|")
    for sym in SYMS:
        for segname in ("market", "pre", "post"):
            base = [r for r in runs if r["sym"] == sym and r["unseen"]
                    and r["segment"] == segname and r.get("valid")
                    and (r["sym"], r["day"]) in counted]
            hi = [r for r in base if r.get("K_lead") is not None and r["K_lead"] >= 0.05]
            for c in CONS:
                em(f"| {sym} | {segname} | {c} | {len(base)} | "
                   f"{sh(sum(1 for r in base if r.get(c) is not None and r[c]==r['K']), len(base))} | "
                   f"{len(hi)} | "
                   f"{sh(sum(1 for r in hi if r.get(c) is not None and r[c]==r['K']), len(hi))} |")
    em("")

    # ------------- M3 -------------
    em("## M3 — where each pin sits (market runs)")
    em("")
    for sym in SYMS:
        em(f"### {sym}")
        em("")
        em("| pin | runs | median abs(pin−S) steps | pin = ATM | outside stored corridor | median pin changes/day |")
        em("|---|---|---|---|---|---|")
        step = STEP[sym]
        rs = [r for r in mkt if r["sym"] == sym and (r["sym"], r["day"]) in counted]
        for c in ALLPINS:
            have = [r for r in rs if r.get(c) is not None]
            d = [abs(r[c] - r["S"]) / step for r in have]
            atm = sum(1 for r in have if r[c] == r["atm"])
            wd = [r for r in have if r.get("put_wall") is not None
                  and r.get("call_wall") is not None]
            outw = sum(1 for r in wd if not (r["put_wall"] <= r[c] <= r["call_wall"]))
            chg = []
            for day in sorted({r["day"] for r in rs}):
                dr = sorted([r for r in rs if r["day"] == day and r.get(c) is not None],
                            key=lambda r: r["ts_ist"])
                seq = [r[c] for r in dr]
                if seq:
                    chg.append(sum(1 for i in range(len(seq)-1) if seq[i] != seq[i+1]))
            em(f"| {c} | {len(have)} | {md(d)} | {sh(atm,len(have))} | "
               f"{sh(outw,len(wd))} | {md(chg,1)} |")
        em("")

    # ------------- M5 -------------
    def bin_lnR(r):
        if r.get("R") is None or r["R"] <= 0:
            return None
        a = abs(math.log(r["R"]))
        return "[0,0.1)" if a < 0.1 else ("[0.1,0.3)" if a < 0.3 else "[0.3,inf)")

    def bin_BL(r):
        if r.get("BL") is None:
            return None
        b = r["BL"]
        return "[0,2%)" if b < 0.02 else ("[2%,5%)" if b < 0.05 else "[5%,inf)")

    def bin_FB(r):
        if r.get("FB") is None:
            return None
        a = abs(r["FB"])
        return "[0,0.5)" if a < 0.5 else ("[0.5,1)" if a < 1 else "[1,inf)")

    def bin_IVA(r):
        if r.get("IVA") is None:
            return None
        a = r["IVA"]
        return "[0,10)" if a < 10 else ("[10,60)" if a < 60 else "[60,inf)")

    em("## M5 — agreement with K, split by diagnostic (market, K lead ≥ 5 %)")
    em("")
    em("| symbol | split | bin | runs | V2 = K | VS = K | FV = K | F = K |")
    em("|---|---|---|---|---|---|---|---|")
    for sym in SYMS:
        hi = [r for r in mkt if r["sym"] == sym and (r["sym"], r["day"]) in counted
              and r.get("K_lead") is not None and r["K_lead"] >= 0.05]
        for lab, fn, order in (("abs(ln R)", bin_lnR, ("[0,0.1)", "[0.1,0.3)", "[0.3,inf)")),
                               ("BL", bin_BL, ("[0,2%)", "[2%,5%)", "[5%,inf)")),
                               ("abs(FB)", bin_FB, ("[0,0.5)", "[0.5,1)", "[1,inf)")),
                               ("DTE", lambda r: r.get("DTE"), ("0", "1", "2", "3+"))):
            for b in order:
                sub = [r for r in hi if fn(r) == b]
                em(f"| {sym} | {lab} | {b} | {len(sub)} | "
                   + " | ".join(sh(sum(1 for r in sub if r.get(c) is not None
                                       and r[c] == r["K"]), len(sub)) for c in CONS)
                   + " |")
            nb = [r for r in hi if fn(r) is None]
            if nb:
                em(f"| {sym} | {lab} | (no value) | {len(nb)} | "
                   + " | ".join(sh(sum(1 for r in nb if r.get(c) is not None
                                       and r[c] == r["K"]), len(nb)) for c in CONS)
                   + " |")
        for b in ("[0,10)", "[10,60)", "[60,inf)"):
            sub = [r for r in hi if bin_IVA(r) == b]
            em(f"| {sym} | IVA (FV only) | {b} | {len(sub)} | — | — | "
               f"{sh(sum(1 for r in sub if r.get('FV') is not None and r['FV']==r['K']), len(sub))} | — |")
    em("")

    # ------------- M6 -------------
    em("## M6 — the ten symbol-days with the lowest V2 agreement")
    em("")
    em("Market runs, K lead ≥ 5 %. 2026-11-20 is shown for both symbols whatever its rank.")
    em("")
    em("| rank | symbol | day | SEEN | mkt runs | K-lead≥5% | V2 = K | DTE at open | median R | median BL | median FB | VS = K | FV = K | F = K |")
    em("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    cand = [(daily[k][f"V2_hi"], k) for k in counted
            if not math.isnan(daily[k]["V2_hi"])]
    cand.sort()
    pickset = [k for _, k in cand[:10]]
    for sym in SYMS:
        if (sym, "2026-11-20") in counted and (sym, "2026-11-20") not in pickset:
            pickset.append((sym, "2026-11-20"))
    for i, k in enumerate(pickset, 1):
        sym, day = k
        row = daily[k]
        rank = next((j for j, (_, kk) in enumerate(cand, 1) if kk == k), None)
        em(f"| {rank} | {sym} | {day} | {'SEEN' if day in SEEN else 'UNSEEN'} | "
           f"{row['n_mkt']} | {row['n_hi']} | {row['V2_hi']:.1f}% | {row['dte_open']} | "
           f"{row['med_R']:.4f} | {row['med_BL']:.4f} | {row['med_FB']:.2f} | "
           f"{row['VS_hi']:.1f}% | {row['FV_hi']:.1f}% | {row['F_hi']:.1f}% |")
    em("")

    # ------------- M7 -------------
    em("## M7 — frozen runs")
    em("")
    em("| symbol | days with any frozen | market runs frozen | K pin changes with a frozen run before or after |")
    em("|---|---|---|---|")
    for sym in SYMS:
        rs = [r for r in mkt if r["sym"] == sym and (r["sym"], r["day"]) in counted]
        days = sorted({r["day"] for r in rs})
        dany = sum(1 for d in days if any(r["frozen"] for r in rs if r["day"] == d))
        nf = sum(1 for r in rs if r["frozen"])
        tot = adj = 0
        for d in days:
            dr = sorted([r for r in rs if r["day"] == d and r.get("K") is not None],
                        key=lambda r: r["ts_ist"])
            for i in range(len(dr) - 1):
                if dr[i]["K"] != dr[i+1]["K"]:
                    tot += 1
                    if dr[i]["frozen"] or dr[i+1]["frozen"]:
                        adj += 1
        em(f"| {sym} | {dany}/{len(days)} | {sh(nf,len(rs))} | {sh(adj,tot)} |")
    em("")

    # ------------- M8 -------------
    em("## M8 — data quality")
    em("")
    lg = (HERE / "_pull_v2.log").read_text(encoding="utf-8").splitlines()
    empties = [x.split() for x in lg if x.startswith("OK_EMPTY")]
    em(f"Empty weekdays: **{len(empties)} symbol-days** "
       f"({len(empties)//2} weekdays, both symbols) — "
       + ", ".join(sorted({f'{e[2]}' for e in empties})) + ". "
       "2026-08-25 is the only one where the volatility pull returned rows "
       "(v0=83 both symbols) while the chain join returned none; the other four "
       "returned v0=0, i.e. no gamma_metrics runs at all.")
    em("")
    em("| symbol | runs | valid | market | no Board row | no atm_iv_avg | "
       "invalid by reason | fallback strikes | legs oi>0 & ltp≤0 | ambiguous spot |")
    em("|---|---|---|---|---|---|---|---|---|---|")
    for sym in SYMS:
        rs = [r for r in runs if r["sym"] == sym]
        inv = Counter(r.get("reason") for r in rs if not r.get("valid"))
        em(f"| {sym} | {len(rs)} | {sum(1 for r in rs if r.get('valid'))} | "
           f"{sum(1 for r in rs if r['segment']=='market')} | "
           f"{sum(1 for r in rs if not r['has_board_row'])} | "
           f"{sum(1 for r in rs if r.get('atm_iv_avg') is None)} | "
           f"{dict(inv) if inv else 'none'} | "
           f"{sum(r.get('n_fallback',0) or 0 for r in rs)} | "
           f"{sum(r['legs_oi_pos_ltp_nonpos'] for r in rs)} | "
           f"{sum(1 for r in rs if r['spot_ambiguous'])} |")
    em("")
    em(f"Short symbol-days (fewer than {MIN_RUNS} valid market runs), reported and left "
       f"out of the day counts: {len(short)}"
       + ("" if not short else " — " + ", ".join(f"{s} {d} ({nmkt[(s,d)]})"
                                                 for s, d in short)) + ".")
    em("")
    em("FV status counts: "
       + str(dict(Counter(r.get("FV_status") for r in runs))) + ".")
    em("")

    (HERE / "results.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    cols = ["sym", "day", "unseen", "run_id", "ts_ist", "tname", "segment", "expiry",
            "dte_gm", "dte_cal", "DTE", "t_min", "S", "atm", "spot_ambiguous",
            "n_strikes", "n_legs_band", "n_legs_chain", "n_fallback", "sigma_atm",
            "F_fwd", "FB", "R", "R_n", "BL", "atm_iv_avg", "IVA", "FV_status",
            "tot_oi_call", "tot_oi_put", "frozen", "has_board_row", "call_wall",
            "put_wall", "valid", "reason", "B", "V2", "VS", "FV", "F", "K",
            "V2_lead", "VS_lead", "FV_lead", "F_lead", "K_lead", "K_share",
            "legs_oi_pos_ltp_nonpos"]
    with (HERE / "runs.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in runs:
            w.writerow(["" if r.get(c) is None else r.get(c, "") for c in cols])
    print(f"results.md ({len(L)} lines), runs.csv ({len(runs)} rows) written")
    for c in CONS:
        n_ok, s_ok = dec[("NIFTY", c)], dec[("SENSEX", c)]
        print(f"{c}: NIFTY {n_ok[0]:.2f}% ({n_ok[1]}/{n_ok[2]}) days {n_ok[4]}/{n_ok[5]} "
              f"{'PASS' if n_ok[6] else 'FAIL'} | SENSEX {s_ok[0]:.2f}% "
              f"({s_ok[1]}/{s_ok[2]}) days {s_ok[4]}/{s_ok[5]} "
              f"{'PASS' if s_ok[6] else 'FAIL'} | "
              f"{'ENOUGH' if (n_ok[6] and s_ok[6]) else 'NOT ENOUGH'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
