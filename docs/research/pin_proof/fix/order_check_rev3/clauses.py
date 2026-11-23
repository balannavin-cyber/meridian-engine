#!/usr/bin/env python3
"""The PREREG pass rule, clauses 1-4, as one shared evaluator.

self_test.py and the live comparison both call compare(). The self-test
therefore exercises the clause arithmetic itself, not merely indep.measure():
a clause that could not report FAIL would show up as a mutant that passes.

Scope, from the PREREG pass rule preamble: "Per symbol and expiry, over the rows
the view returns."
"""
from __future__ import annotations

LEAD_REL_TOL = 1e-9          # clause 3, fixed by PREREG
TOP_N = 10                   # clause 1: strike_rank 1..10, or all ranked if fewer


def _rel(a, b) -> float:
    """Relative difference, with 0 vs 0 == 0 and x vs 0 == inf."""
    if a is None or b is None:
        return float("inf") if a is not b else 0.0
    if a == b:
        return 0.0
    d = max(abs(a), abs(b))
    return float("inf") if d == 0 else abs(a - b) / d


def compare(view: dict, indep: dict) -> dict:
    """view, indep: {(symbol, expiry): record}.

    record keys: sequence (rank order), n_ranked, n_in_set, n_oi_no_gamma,
    legs_map {strike: tag}, lead_rel.

    Returns {"clause1".."clause4": bool, "overall": bool, "per_pair": {...},
             "notes": [...]}. Every clause is computed; none short-circuits the
    others, so a report shows which clause broke rather than only the first.
    """
    vp, ip = set(view), set(indep)
    out = {"per_pair": {}, "notes": []}

    # ---- clause 4: the pair sets ----
    out["clause4"] = (vp == ip)
    if vp - ip:
        out["notes"].append(f"pairs on VIEW side only: {sorted(vp - ip)}")
    if ip - vp:
        out["notes"].append(f"pairs on INDEP side only: {sorted(ip - vp)}")

    c1 = c2 = c3 = True
    for pair in sorted(vp & ip):
        v, i = view[pair], indep[pair]
        row = {}

        # ---- clause 1: the ranked strike sequence, rank 1..TOP_N ----
        # PREREG clause 1 is the SEQUENCE only. A difference in how many strikes
        # are ranked in total is n_ranked, which is clause 2 -- so the lengths
        # are not asserted here. rows_compared is the number of positions this
        # equality actually looked at: max, not min, so a length difference
        # inside the top 10 is visible in the denominator instead of hidden.
        vs, isq = list(v["sequence"])[:TOP_N], list(i["sequence"])[:TOP_N]
        row["rows_compared"] = max(len(vs), len(isq))
        row["seq_view"], row["seq_indep"] = vs, isq
        row["clause1"] = (vs == isq)
        if not row["clause1"]:
            c1 = False

        # ---- clause 2: the three counts, and gamma_legs on every compared row ----
        cnt = {}
        for k in ("n_ranked", "n_in_set", "n_oi_no_gamma"):
            cnt[k] = (v.get(k), i.get(k), v.get(k) == i.get(k))
        shared = [K for K in v.get("legs_map", {}) if K in i.get("legs_map", {})]
        legs_bad = [K for K in shared
                    if v["legs_map"][K] != i["legs_map"][K]]
        row["counts"] = cnt
        row["legs_rows_compared"] = len(shared)
        row["legs_mismatched"] = legs_bad
        row["clause2"] = all(t[2] for t in cnt.values()) and not legs_bad
        if not row["clause2"]:
            c2 = False

        # ---- clause 3: lead_rel ----
        r = _rel(v.get("lead_rel"), i.get("lead_rel"))
        row["lead_rel_view"], row["lead_rel_indep"] = v.get("lead_rel"), i.get("lead_rel")
        row["lead_rel_reldiff"] = r
        row["clause3"] = (r <= LEAD_REL_TOL)
        if not row["clause3"]:
            c3 = False

        # ---- reported, NOT judged: max relative gross_cr difference ----
        gv, gi = v.get("gross") or {}, i.get("gross") or {}
        both = [K for K in gv if K in gi]
        row["gross_rows_compared"] = len(both)
        row["max_rel_gross_diff"] = max((_rel(gv[K], gi[K]) for K in both),
                                        default=None)

        out["per_pair"][pair] = row

    out["clause1"], out["clause2"], out["clause3"] = c1, c2, c3
    out["overall"] = all((c1, c2, c3, out["clause4"]))
    return out
