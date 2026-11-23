#!/usr/bin/env python3
"""Summarise the futures coverage probe for the Part B sampled minutes.

Input  : _partF_raw.txt -- "SYM|DAY|tag|<json payload>"
Output : stdout. No database access, no writes to tracked files.

Reports, per symbol: whether a futures bar exists at each sampled minute, which
contract_series are present, the near-contract time to expiry (which is the DENOMINATOR
basis_implied_r needs -- NOT the option's), and any minute where an EXACT miss coincides
with a NEAREST hit, which would mean the two stores disagree on the bar_ts convention.
"""
import json
import sys
from collections import defaultdict

RAW = sys.argv[1] if len(sys.argv) > 1 else "_partF_raw.txt"

F1 = []
F2 = []
with open(RAW) as fh:
    for line in fh:
        line = line.rstrip("\n")
        if not line:
            continue
        sym, day, tag, payload = line.split("|", 3)
        d = json.loads(payload)
        (F1 if tag == "F1" else F2).append(d)

print("### F2 coverage: does a futures bar exist at each sampled minute?")
print("sym|minutes|exact_hit|exact_miss|miss_with_nearest_hit|nearest_off_sec_nonzero")
for sym in ("NIFTY", "SENSEX"):
    v = [r for r in F2 if r["sym"] == sym]
    hit = sum(1 for r in v if r["exact_hit"])
    miss = len(v) - hit
    miss_near = sum(1 for r in v if not r["exact_hit"] and r.get("nearest_off_sec") is not None)
    offnz = sum(1 for r in v if r.get("nearest_off_sec") not in (None, 0, 0.0))
    print(f"{sym}|{len(v)}|{hit}|{miss}|{miss_near}|{offnz}")

miss_rows = [r for r in F2 if not r["exact_hit"]]
if miss_rows:
    print()
    print("# EXACT misses, listed individually (a zero here is NOT absence unless")
    print("# nearest_off_sec is also null -- see the query header):")
    print("sym|day|minute|nearest_off_sec|nearest_series|nearest_close")
    for r in miss_rows:
        print(f"{r['sym']}|{r['d']}|{r['tname']}|{r.get('nearest_off_sec')}|"
              f"{r.get('nearest_series')}|{r.get('nearest_close')}")

print()
print("### F1 contracts present at the exact sampled bar_ts")
print("sym|contract_series|rows|distinct_expiries|min_fut_dte|max_fut_dte")
agg = defaultdict(lambda: {"n": 0, "exp": set(), "dte": []})
for r in F1:
    k = (r["sym"], r["contract_series"])
    agg[k]["n"] += 1
    agg[k]["exp"].add(r["expiry_date"])
    if r["fut_dte"] is not None:
        agg[k]["dte"].append(int(r["fut_dte"]))
for k in sorted(agg, key=lambda x: (x[0], x[1] is None, x[1] if x[1] is not None else 0)):
    a = agg[k]
    print(f"{k[0]}|{k[1]}|{a['n']}|{len(a['exp'])}|"
          f"{min(a['dte']) if a['dte'] else 'n/a'}|{max(a['dte']) if a['dte'] else 'n/a'}")

print()
print("### near contract per sampled minute: fut_dte and the basis it implies")
print("# fut_dte is the T that ln(F/S)/T must be divided by. A SMALL fut_dte makes r")
print("# explode, so these are the minutes a sensitivity run must flag, not average over.")
print("sym|day|minute|near_series|fut_dte|fut_close")
near = {}
for r in F1:
    k = (r["sym"], r["d"], r["tname"])
    dte = r.get("fut_dte")
    if dte is None or int(dte) < 0:
        continue  # an already-expired contract cannot carry the forward
    # NEAR = smallest fut_dte >= 0, MEASURED. Picking the smallest contract_series
    # instead would assume series 1 is the nearest expiry, which is an assumption.
    if k not in near or int(dte) < int(near[k]["fut_dte"]):
        near[k] = r
small = 0
for k in sorted(near):
    r = near[k]
    dte = r["fut_dte"]
    if dte is not None and int(dte) < 3:
        small += 1
    print(f"{k[0]}|{k[1]}|{k[2]}|{r['contract_series']}|{dte}|{r['fut_close']}")
print(f"# sampled minutes whose NEAR futures contract has fut_dte < 3 days: {small}")
dtes = [int(r["fut_dte"]) for r in near.values() if r["fut_dte"] is not None]
if dtes:
    dtes.sort()
    print(f"# near-contract fut_dte across all sampled minutes: min {dtes[0]}, "
          f"median {dtes[len(dtes)//2]}, max {dtes[-1]}")
