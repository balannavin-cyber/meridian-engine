#!/usr/bin/env python3
"""Aggregate the Part A raw payloads into the tables that go in partA_results.md.

Input  : _partA_raw.txt  -- lines "SYM|DAY|tag|<json payload>"
Output : stdout, pipe-delimited blocks. No database access, no writes to tracked files.
"""
import json
import sys
from collections import defaultdict

RAW = sys.argv[1] if len(sys.argv) > 1 else "_partA_raw.txt"

rows = defaultdict(list)
with open(RAW) as fh:
    for line in fh:
        line = line.rstrip("\n")
        if not line:
            continue
        sym, day, tag, payload = line.split("|", 3)
        rows[tag].append(json.loads(payload))


def ag(tag, keys, sums):
    """Sum `sums` grouped by `keys` over every day."""
    out = defaultdict(lambda: defaultdict(int))
    for d in rows[tag]:
        k = tuple(d[x] for x in keys)
        for s in sums:
            v = d.get(s)
            out[k][s] += int(v) if v is not None else 0
    return out


def pct(a, b):
    return f"{100.0 * a / b:.2f}" if b else "n/a"


print("### R1 A2 coverage by option_type x ITM bucket (4 days pooled)")
print("sym|ot|bkt|legs_all|legs_oi|g_null|g_zero|g_pos|iv_null|iv_zero|iv_pos|ltp_pos|quoted|oi_sum|g_null_pct_of_oi_legs")
a = ag("R1", ["sym", "ot", "bkt"],
       ["legs_all", "legs_oi", "g_null", "g_zero", "g_pos", "iv_null", "iv_zero",
        "iv_pos", "ltp_pos", "quoted", "oi_sum"])
for k in sorted(a):
    v = a[k]
    print("|".join(list(k) + [str(v[c]) for c in
          ["legs_all", "legs_oi", "g_null", "g_zero", "g_pos", "iv_null", "iv_zero",
           "iv_pos", "ltp_pos", "quoted", "oi_sum"]] + [pct(v["g_null"], v["legs_oi"])]))

print()
print("### R2 A2 KEY CELL: legs with oi>0 AND ltp>0 AND gamma blank (4 days pooled)")
print("sym|ot|bkt|legs_oi_px|key_blank_g|key_g_null|key_g_zero|key_blank_both|key_blank_g_iv_pos|oi_sum_oi_px|oi_key_blank|blank_pct_legs|blank_pct_oi")
b = ag("R2", ["sym", "ot", "bkt"],
       ["legs_oi_px", "key_blank_g", "key_g_null", "key_g_zero", "key_blank_both",
        "key_blank_g_iv_pos", "oi_sum_oi_px", "oi_key_blank"])
for k in sorted(b):
    v = b[k]
    print("|".join(list(k) + [str(v[c]) for c in
          ["legs_oi_px", "key_blank_g", "key_g_null", "key_g_zero", "key_blank_both",
           "key_blank_g_iv_pos", "oi_sum_oi_px", "oi_key_blank"]] +
          [pct(v["key_blank_g"], v["legs_oi_px"]), pct(v["oi_key_blank"], v["oi_sum_oi_px"])]))

print()
print("### R2 KEY CELL rolled up to ITM-only (bkt != 1_OTM) and to all buckets")
print("sym|scope|legs_oi_px|key_blank_g|blank_pct_legs|oi_sum_oi_px|oi_key_blank|blank_pct_oi")
for sym in ("NIFTY", "SENSEX"):
    for scope, keep in (("ITM_only", lambda x: x != "1_OTM"), ("all_buckets", lambda x: True)):
        L = BG = OS = OB = 0
        for k, v in b.items():
            if k[0] == sym and keep(k[2]):
                L += v["legs_oi_px"]; BG += v["key_blank_g"]
                OS += v["oi_sum_oi_px"]; OB += v["oi_key_blank"]
        print(f"{sym}|{scope}|{L}|{BG}|{pct(BG,L)}|{OS}|{OB}|{pct(OB,OS)}")

print()
print("### R3/R4 A3 cross-tab: chain gamma state vs gex_strike_snapshots state (4 days pooled)")
print("sym|leg|chain_state|gss_state|strikes")
for tag in ("R3", "R4"):
    c = ag(tag, ["sym", "leg", "chain_state", "gss_state"], ["strikes"])
    for k in sorted(c):
        print("|".join(list(k) + [str(c[k]["strikes"])]))

print()
print("### R5 A3 chain gamma>0 but strike table NULL, by ITM bucket")
print("sym|leg|bkt|strikes")
e = ag("R5", ["sym", "leg", "bkt"], ["strikes"])
if not e:
    print("(no rows -- zero such legs on all 4 days, both symbols)")
for k in sorted(e):
    print("|".join(list(k) + [str(e[k]["strikes"])]))

print()
print("### R6 A3 gex_cr = 0 decomposition")
print("sym|gss_strikes|strikes_both_pos|both_pos_gex_zero|both_pos_gex_zero_deep|all_gex_zero|gex_zero_both_null")
f = ag("R6", ["sym"], ["gss_strikes", "strikes_both_pos", "both_pos_gex_zero",
                       "both_pos_gex_zero_deep", "all_gex_zero", "gex_zero_both_null"])
for k in sorted(f):
    v = f[k]
    print("|".join(list(k) + [str(v[c]) for c in
          ["gss_strikes", "strikes_both_pos", "both_pos_gex_zero",
           "both_pos_gex_zero_deep", "all_gex_zero", "gex_zero_both_null"]]))
