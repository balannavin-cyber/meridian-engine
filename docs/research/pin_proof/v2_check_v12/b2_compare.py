"""B2: backfilled rows for 2026-08-27 against the pin lane's own output.

Usage: python3 -B -I b2_compare.py <pasted SQL editor output as JSON>
Pass criteria (fixed 25 Nov 19:55 IST, before the database output was seen):
  - every fixture run (78 per symbol) is present in the database output;
  - counts exact: rows, in_map, in_band, both, call_only, put_only, n_map, n_zero;
  - open-interest sums exact;
  - sums (net, gross, gamma, strike-weighted net and gross) and run net / band total
    within 1e-9 relative + 1e-9 absolute; shares and HHI within 1e-9;
  - rule_version 'v2-1.2-gss' on every row.
Runs in the database but not in the fixture are listed, not compared.
"""
import json
import sys

exp = json.load(open("/home/claude/v2_check_v12/b2_expected_2026-08-27.json"))
got = json.load(open(sys.argv[1]))
by = {r["run_id"]: r for r in got}
fails = []
EXACT = ("n", "n_map", "n_band", "n_both", "n_call", "n_put", "s_oic", "s_oip")
SUMS = ("s_net", "s_gross", "s_gamma", "sk_net", "sk_gross")


def num(x):
    return None if x is None else float(x)


def close(a, b, rel=1e-9, ab=1e-9):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= ab + rel * abs(b)


worst = 0.0
for rid, e in exp.items():
    g = by.get(rid)
    if g is None:
        fails.append((e["symbol"], rid, "missing in database", None, None))
        continue
    if g["symbol"] != e["symbol"]:
        fails.append((e["symbol"], rid, "symbol", g["symbol"], e["symbol"]))
    for k in EXACT:
        if num(g[k]) != float(e[k]):
            fails.append((e["symbol"], rid, k, g[k], e[k]))
    for k in SUMS:
        a, b = num(g[k]), float(e[k])
        if not close(a, b):
            fails.append((e["symbol"], rid, k, a, b))
        elif b:
            worst = max(worst, abs(a - b) / abs(b))
    for k, rel, ab in (("r_net_cr", 1e-9, 1e-9), ("r_gross_band_cr", 1e-9, 1e-9), ("r_net_top_share", 0, 1e-9),
                       ("r_gross_top_share", 0, 1e-9), ("r_gross_hhi", 0, 1e-9)):
        if not close(num(g[k]), e[k], rel, ab):
            fails.append((e["symbol"], rid, k, g[k], e[k]))
    for k in ("r_n_map", "r_n_zero"):
        if num(g[k]) != float(e[k]):
            fails.append((e["symbol"], rid, k, g[k], e[k]))
    for k in ("rv_strike", "rv_run"):
        if g[k] != "v2-1.2-gss":
            fails.append((e["symbol"], rid, k, g[k], "v2-1.2-gss"))

extra = sorted((r["symbol"], r["ist"], r["run_id"]) for r in got if r["run_id"] not in exp)
print(f"database rows returned: {len(got)}; fixture runs: {len(exp)}; compared: {len(exp) - sum(1 for f in fails if f[2] == 'missing in database')}")
print(f"largest relative difference in any sum: {worst:.3e}")
print(f"runs in the database and not in the fixture: {len(extra)}")
for s, t, r in extra:
    print(f"  {s} {t} {r}")
for f in fails[:30]:
    print("MISMATCH", f)
print("B2:", "PASS" if not fails else f"FAIL ({len(fails)} mismatches)")
