#!/usr/bin/env python3
"""Load the view reads and the leg reads, run indep.measure() and clauses.compare(),
emit the comparison table and the verdict. Disk only -- no database.

The view side is parsed from out_view_<SYM>.txt; the independent side is rebuilt
from out_legs_<SYM>.txt via indep.measure(). Neither side is derived from the
other.
"""
from __future__ import annotations

import json
from pathlib import Path

from clauses import LEAD_REL_TOL, TOP_N, compare
from indep import measure

HERE = Path(__file__).resolve().parent
SYMS = ("NIFTY", "SENSEX")
FROZEN = {"NIFTY":  "85ba488d-7bd2-4333-af0c-03591f902694",
          "SENSEX": "d875b416-7b1d-4e34-bfc4-0ba077ac1af2"}
VIEWDEF_LEN = 5281
VIEWDEF_MD5 = "aa4946064341c1d1ae835819d8cba858"
L: list[str] = []


def em(s=""):
    L.append(s)
    print(s)


def f(x):
    return None if x in (None, "", "None") else float(x)


# ----------------------------------------------------------------- view side --
def load_view(sym: str) -> dict:
    """out_view_<SYM>.txt -> {(symbol, expiry): record}. Field order is the
    SELECT list of q_view.sql.tpl; see that file."""
    rows = {}
    meta = {}
    for line in (HERE / f"out_view_{sym}.txt").read_text().splitlines():
        if not line.startswith("V|"):
            continue
        p = line.split("|")
        (_, run_id, symbol, expiry, ts_ist, dte, spot, rank, strike,
         oi_c, oi_p, g_c, g_p, g_s, gross, lead, n_ranked, legs,
         n_in_set, n_oi_ng, side) = p[:21]
        key = (symbol, expiry)
        d = rows.setdefault(key, {"sequence": [], "legs_map": {}, "gross": {}})
        K = float(strike)
        d["sequence"].append((int(rank), K))
        d["legs_map"][K] = legs
        d["gross"][K] = f(gross)
        d["n_ranked"] = int(n_ranked)
        d["n_in_set"] = int(n_in_set)
        d["n_oi_no_gamma"] = int(n_oi_ng)
        d["lead_rel"] = f(lead)
        m = meta.setdefault(key, {"run_id": run_id, "ts_ist": ts_ist,
                                  "dte": int(dte), "spot": f(spot),
                                  "legs_tally": {}})
        m["legs_tally"][legs] = m["legs_tally"].get(legs, 0) + 1
        if m["run_id"] != run_id:
            raise SystemExit(f"STOP: {key} spans two run_ids in the view read")
    for key, d in rows.items():
        d["sequence"] = [K for _, K in sorted(d["sequence"])]
    return rows, meta


# ----------------------------------------------------------- independent side --
def load_legs(sym: str):
    """out_legs_<SYM>.txt -> (run header, {strike: leg dict}). The 5 % band is
    NOT applied here; indep.measure() makes the single cut (see q_legs.sql.tpl)."""
    hdr, legs = None, {}
    for line in (HERE / f"out_legs_{sym}.txt").read_text().splitlines():
        if line.startswith("R0|"):
            hdr = json.loads(line[3:])
        elif line.startswith("R1|"):
            j = json.loads(line[3:])
            K = float(j["strike"])
            e = legs.setdefault(K, {"c_gamma": None, "p_gamma": None,
                                    "c_oi": 0.0, "p_oi": 0.0})
            g, oi = f(j.get("gamma")), (f(j.get("oi")) or 0.0)
            if j["ot"] == "CE":
                e["c_gamma"], e["c_oi"] = g, oi
            else:
                e["p_gamma"], e["p_oi"] = g, oi
    return hdr, legs


def main() -> int:
    em("<!-- pk: lane=pin; "
       "git=meridian-engine:docs/research/pin_proof/fix/order_check_rev3/results.md -->")
    em()
    em("# Order check on revision 3 of v_gex_strike_rank_gross - RESULT")
    em()
    em("Design frozen in `PREREG.md` "
       "sha256 `da7440d119945e236136296b2db2a3f0ca86149ecefdfcaf01a668363a1fced7`. "
       "Self-test 38/38 with all three named mutants making a clause FAIL, run "
       "before any live read. One look; no clause added, relaxed or reordered "
       "after the data was seen.")
    em()
    em("## Pre-data clarification and stated limits")
    em()
    em("**Ranking condition `gross_cr > 0`.** Operator ruling 2026-11-23 20:00 "
       "IST, made AFTER the NIFTY view EXPLAIN gate and BEFORE any data read. "
       "Basis: the pin lane's own revision-2 draft "
       "`2026-11-21_pin_v_gex_strike_rank_gross_DRAFT.sql` (`WHERE gross_cr > "
       "0`), which is where `n_ranked` was defined. PREREG left the zero-gross "
       "case unstated, so this is a clarification and not a relaxation: an "
       "in-set strike carrying a gamma but zero total OI has `gross_cr = 0` and "
       "is NOT ranked. Only the ranking condition in `indep.measure()` changed. "
       "One in-set fixture strike with gamma > 0 and zero OI on both legs was "
       "added to exercise that condition, the hand expectations were recomputed, "
       "and the full self-test was re-run: **38/38**, with all three named "
       "mutants still each making at least one clause FAIL.")
    em()
    em("**Stated limits.**")
    em()
    em("1. The fixture tests the independent Python and the clause evaluator. It "
       "does NOT test the view.")
    em(f"2. The live view is identified by `pg_get_viewdef` length "
       f"**{VIEWDEF_LEN}** and md5 **{VIEWDEF_MD5}**. File-to-live identity "
       f"against `sql/2026-11-23_s107_v_gex_strike_rank_gross.sql` was NOT "
       f"established -- the engine tree was out of scope for this task -- so "
       f"CLAUDE.md Rule 25 is unsatisfied and nothing here claims the object "
       f"checked is that file.")
    em()

    view_all, indep_all, meta_all, hdr_all = {}, {}, {}, {}
    for sym in SYMS:
        v, m = load_view(sym)
        hdr, legs = load_legs(sym)
        if hdr["run_id"] != FROZEN[sym]:
            raise SystemExit(f"STOP: {sym} leg read is not the frozen run_id")
        spot = f(hdr["spot_min"])
        rec = measure(legs, spot)
        key = (sym, hdr["expiry"])
        view_all.update(v)
        meta_all.update(m)
        indep_all[key] = rec
        hdr_all[key] = hdr

    r = compare(view_all, indep_all)

    # ------------------------------------------------------------ run header --
    em("## The frozen runs")
    em()
    em("| symbol | expiry | run_id | ts IST | dte | view spot | chain spot_min | "
       "spot_max | distinct spot | chain legs |")
    em("|---|---|---|---|---|---|---|---|---|---|")
    for key in sorted(hdr_all):
        h, m = hdr_all[key], meta_all[key]
        em(f"| {key[0]} | {key[1]} | `{h['run_id']}` | {h['ts_ist']} | "
           f"{h['dte']} | {m['spot']} | {h['spot_min']} | {h['spot_max']} | "
           f"{h['n_distinct_spot']} | {h['n_legs_chain']} |")
    em()
    # Task condition 1, computed from out_refreeze_<SYM>.txt -- NOT a literal, so
    # this line cannot read PASS if the files say otherwise. A mismatch or a
    # multi-row result raises before any clause is evaluated.
    rf = []
    for sym in SYMS:
        lines = [x for x in (HERE / f"out_refreeze_{sym}.txt")
                 .read_text().splitlines() if x.startswith("REFREEZE|")]
        got = lines[0].split("|")[2] if len(lines) == 1 else None
        ok = (len(lines) == 1 and got == FROZEN[sym])
        rf.append(f"{sym} ROWS={len(lines)} returned=`{got}` "
                  f"frozen=`{FROZEN[sym]}` -> {'PASS' if ok else 'STOP'}")
        if not ok:
            raise SystemExit(f"STOP: condition 1 failed for {sym}: {rf[-1]}")
    em(f"**Condition 1, run_id re-read after the independent read:** "
       f"{' · '.join(rf)}. Neither symbol's latest run_id moved between the "
       f"view read and the leg read, so no run was discarded and no redo was "
       f"needed.")
    em()

    # ------------------------------------------------- per-clause comparison --
    em("## Per symbol and expiry")
    em()
    em("| symbol | expiry | rows compared | legs rows | gross rows | "
       "clause 1 | clause 2 | clause 3 | max rel gross diff |")
    em("|---|---|---|---|---|---|---|---|---|")
    for key in sorted(r["per_pair"]):
        d = r["per_pair"][key]
        mg = d["max_rel_gross_diff"]
        em(f"| {key[0]} | {key[1]} | {d['rows_compared']} | "
           f"{d['legs_rows_compared']} | {d['gross_rows_compared']} | "
           f"{'PASS' if d['clause1'] else 'FAIL'} | "
           f"{'PASS' if d['clause2'] else 'FAIL'} | "
           f"{'PASS' if d['clause3'] else 'FAIL'} | "
           f"{'n/a' if mg is None else f'{mg:.6g}'} |")
    em()
    em(f"Clause 4 (same set of (symbol, expiry) pairs): "
       f"**{'PASS' if r['clause4'] else 'FAIL'}** - "
       f"view {sorted(set(view_all))}, independent {sorted(set(indep_all))}.")
    for n in r["notes"]:
        em(f"  - {n}")
    em()

    # ------------------------------------------------------------- the counts --
    em("## The three counts, view vs independent")
    em()
    em("| symbol | expiry | n_ranked V | n_ranked I | n_in_set V | n_in_set I | "
       "n_oi_no_gamma V | n_oi_no_gamma I | equal |")
    em("|---|---|---|---|---|---|---|---|---|")
    for key in sorted(r["per_pair"]):
        c = r["per_pair"][key]["counts"]
        ok = all(t[2] for t in c.values())
        em(f"| {key[0]} | {key[1]} | {c['n_ranked'][0]} | {c['n_ranked'][1]} | "
           f"{c['n_in_set'][0]} | {c['n_in_set'][1]} | "
           f"{c['n_oi_no_gamma'][0]} | {c['n_oi_no_gamma'][1]} | "
           f"{'yes' if ok else 'NO'} |")
    em()

    # ------------------------------------------------------------- lead_rel ---
    em("## lead_rel")
    em()
    em(f"Tolerance {LEAD_REL_TOL:g} relative, fixed by PREREG.")
    em()
    em("| symbol | expiry | lead_rel view | lead_rel independent | rel diff | clause 3 |")
    em("|---|---|---|---|---|---|")
    for key in sorted(r["per_pair"]):
        d = r["per_pair"][key]
        em(f"| {key[0]} | {key[1]} | {d['lead_rel_view']!r} | "
           f"{d['lead_rel_indep']!r} | {d['lead_rel_reldiff']:.6g} | "
           f"{'PASS' if d['clause3'] else 'FAIL'} |")
    em()

    # ------------------------------------------------- the ranked sequences ---
    em(f"## Ranked sequence, rank 1..{TOP_N}")
    em()
    for key in sorted(r["per_pair"]):
        d = r["per_pair"][key]
        em(f"**{key[0]} {key[1]}** - clause 1 "
           f"{'PASS' if d['clause1'] else 'FAIL'}")
        em()
        em("```")
        em(f"view        {[int(x) for x in d['seq_view']]}")
        em(f"independent {[int(x) for x in d['seq_indep']]}")
        em("```")
        if d["legs_mismatched"]:
            em(f"gamma_legs mismatched at: {d['legs_mismatched']}")
        em()

    # ------------------------------- new columns: exercised by live data? ----
    em("## Were the new columns exercised by live data?")
    em()
    em("| symbol | expiry | call_only | put_only | n_oi_no_gamma | "
       "n_gamma_zero_oi (indep) |")
    em("|---|---|---|---|---|---|")
    co_tot = po_tot = 0
    ng_any = 0
    for key in sorted(indep_all):
        i, m = indep_all[key], meta_all[key]
        t = m["legs_tally"]
        co, po = t.get("call_only", 0), t.get("put_only", 0)
        co_tot += co
        po_tot += po
        ng_any = max(ng_any, i["n_oi_no_gamma"])
        em(f"| {key[0]} | {key[1]} | {co} | {po} | {i['n_oi_no_gamma']} | "
           f"{i['n_gamma_zero_oi']} |")
    em()
    if co_tot == 0 and po_tot == 0 and ng_any == 0:
        em("**new columns not exercised by live data** - clause 2 is NOT claimed "
           "for `call_only`, `put_only` or `n_oi_no_gamma`.")
    else:
        em("Per column:")
        em()
        if co_tot + po_tot > 0:
            em(f"- `gamma_legs`: **exercised** - `call_only + put_only = "
               f"{co_tot + po_tot}` across the two symbols ({co_tot} call_only, "
               f"{po_tot} put_only). Clause 2 is claimed for it.")
        else:
            em("- `gamma_legs`: **not exercised by live data; clause 2 not "
               "claimed for it** - `call_only + put_only = 0` across both symbols.")
        if ng_any > 0:
            em(f"- `n_oi_no_gamma`: **exercised** - greater than zero on at "
               f"least one symbol (maximum {ng_any}). Clause 2 is claimed for it.")
        else:
            em("- `n_oi_no_gamma`: **not exercised by live data; clause 2 not "
               "claimed for it** - zero on both symbols.")
    em()

    # ---------------------------------------------------------------- verdict --
    em("## Verdict")
    em()
    for c in ("clause1", "clause2", "clause3", "clause4"):
        em(f"- {c}: **{'PASS' if r[c] else 'FAIL'}**")
    em()
    em(f"**OVERALL: {'PASS' if r['overall'] else 'FAIL'}**")
    em()
    (HERE / "results.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return 0 if r["overall"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
