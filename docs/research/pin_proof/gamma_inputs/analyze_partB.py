#!/usr/bin/env python3
"""Aggregate the Part B raw payloads into the tables that go in partB_results.md.

Input  : _partB_raw.txt  -- lines "SYM|DAY|tag|<json payload>"
Output : stdout, pipe-delimited blocks. No database access, no writes to tracked files.

Thresholds are the ones fixed in the prompt BEFORE any number was seen:
  B  usable as stored            : median call/put gamma ratio within 1% of spot in
                                   [0.95, 1.05] on >= 10 of 12 days
                                   AND median fillable OI share >= 95%
                                   AND worst minute >= 90%
  B  usable with one gamma/strike: fillable test passes, ratio test does not
  B  not usable, re-solve needed : otherwise
"""
import json
import sys
from collections import defaultdict

RAW = sys.argv[1] if len(sys.argv) > 1 else "_partB_raw.txt"

rows = defaultdict(list)
with open(RAW) as fh:
    for line in fh:
        line = line.rstrip("\n")
        if not line:
            continue
        sym, day, tag, payload = line.split("|", 3)
        rows[tag].append(json.loads(payload))


def q(vals, p):
    """Linear-interpolated percentile, p in [0,1]. Returns None on empty."""
    if not vals:
        return None
    s = sorted(vals)
    if len(s) == 1:
        return s[0]
    i = p * (len(s) - 1)
    lo, hi = int(i), min(int(i) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def f(v, nd=4):
    return "n/a" if v is None else f"{v:.{nd}f}"


# ---------------------------------------------------------------- R0 resolution
print("### B1 sample resolution (24 symbol-days x 3 minutes)")
print("sym|day|minute|bar_clock|off_sec|spot|expiry|dte")
off_nonzero = 0
days = defaultdict(set)
for d in rows["R0"]:
    days[d["sym"]].add(d["d"])
    if d["off_sec"] not in (0, 0.0, "0", None):
        off_nonzero += 1
    print(f"{d['sym']}|{d['d']}|{d['tname']}|{d['bar_clock']}|{d['off_sec']}|"
          f"{d['spot']}|{d['expiry']}|{d['dte']}")
print(f"# minutes resolved: {len(rows['R0'])}; with a non-zero offset from :59 -> {off_nonzero}")
for s in sorted(days):
    print(f"# {s}: {len(days[s])} sampled days")

# ---------------------------------------------------------------- B2 coverage
print()
print("### B2 coverage by option_type x ITM bucket (all sampled minutes pooled)")
print("sym|ot|bkt|legs_oi|g_pos|g_null|g_zero|g_norow|pct_legs_g_pos|oi_sum|oi_g_pos|pct_oi_g_pos")
agg = defaultdict(lambda: defaultdict(int))
for d in rows["R1"]:
    k = (d["sym"], d["ot"], d["bkt"])
    for c in ("legs_oi", "g_pos", "g_null", "g_zero", "g_norow",
              "oi_sum", "oi_g_pos", "oi_g_null", "oi_g_zero", "oi_g_norow", "px_pos"):
        v = d.get(c)
        agg[k][c] += int(v) if v is not None else 0
for k in sorted(agg):
    v = agg[k]
    pl = 100.0 * v["g_pos"] / v["legs_oi"] if v["legs_oi"] else None
    po = 100.0 * v["oi_g_pos"] / v["oi_sum"] if v["oi_sum"] else None
    print("|".join(list(k) + [str(v[c]) for c in
          ["legs_oi", "g_pos", "g_null", "g_zero", "g_norow"]] +
          [f(pl, 2), str(v["oi_sum"]), str(v["oi_g_pos"]), f(po, 2)]))

print()
print("### B2 rolled up per symbol")
print("sym|legs_oi|g_pos|g_null|g_zero|g_norow|pct_legs_g_pos|oi_sum|oi_g_pos|pct_oi_g_pos")
for sym in ("NIFTY", "SENSEX"):
    t = defaultdict(int)
    for k, v in agg.items():
        if k[0] == sym:
            for c, n in v.items():
                t[c] += n
    if not t:
        continue
    print(f"{sym}|{t['legs_oi']}|{t['g_pos']}|{t['g_null']}|{t['g_zero']}|{t['g_norow']}|"
          f"{f(100.0*t['g_pos']/t['legs_oi'],2)}|{t['oi_sum']}|{t['oi_g_pos']}|"
          f"{f(100.0*t['oi_g_pos']/t['oi_sum'],2)}")

# ---------------------------------------------------------------- B3 ratios
print()
print("### B3 call/put gamma and iv ratio at one strike")
by_sym_band = defaultdict(list)
by_sym_band_iv = defaultdict(list)
by_day = defaultdict(list)
for d in rows["R2"]:
    band = d["band"]
    gr = d.get("g_ratio")
    ivr = d.get("iv_ratio")
    if gr is not None:
        by_sym_band[(d["sym"], band)].append(float(gr))
        by_day[(d["sym"], band, d["d"])].append(float(gr))
    if ivr is not None:
        by_sym_band_iv[(d["sym"], band)].append(float(ivr))

print("sym|band|n_strikes|gamma_p10|gamma_median|gamma_p90")
for k in sorted(by_sym_band):
    v = by_sym_band[k]
    print(f"{k[0]}|{k[1]}|{len(v)}|{f(q(v,0.10))}|{f(q(v,0.50))}|{f(q(v,0.90))}")
print("sym|band|n_strikes|iv_p10|iv_median|iv_p90")
for k in sorted(by_sym_band_iv):
    v = by_sym_band_iv[k]
    print(f"{k[0]}|{k[1]}|{len(v)}|{f(q(v,0.10))}|{f(q(v,0.50))}|{f(q(v,0.90))}")

print()
print("### B3 per-day median gamma ratio, band W1 (within 1% of spot) -- the gate input")
print("sym|day|n_strikes|median_gamma_ratio|in_0.95_1.05")
gate_ratio = {}
for sym in ("NIFTY", "SENSEX"):
    ok = tot = 0
    for (s, band, day) in sorted(k for k in by_day if k[0] == sym and k[1] == "W1"):
        v = by_day[(s, band, day)]
        m = q(v, 0.50)
        inb = m is not None and 0.95 <= m <= 1.05
        ok += 1 if inb else 0
        tot += 1
        print(f"{sym}|{day}|{len(v)}|{f(m)}|{'YES' if inb else 'NO'}")
    gate_ratio[sym] = (ok, tot)
    print(f"# {sym}: {ok} of {tot} sampled days with median in [0.95, 1.05] (need >= 10 of 12)")

# ---------------------------------------------------------------- B4 fillable
print()
print("### B4 fillable share of open interest, per sampled minute")
print("sym|day|minute|oi_tot|pct_fillable|pct_both|pct_neither|strikes|strikes_fillable|strikes_both")
fill = defaultdict(list)
for d in rows["R3"]:
    tot = float(d["oi_tot"]) if d["oi_tot"] else 0.0
    if tot <= 0:
        continue
    pf = 100.0 * float(d["oi_fillable"]) / tot
    pb = 100.0 * float(d["oi_both"]) / tot
    pn = 100.0 * float(d["oi_neither"]) / tot
    fill[d["sym"]].append((pf, d["d"], d["tname"]))
    print(f"{d['sym']}|{d['d']}|{d['tname']}|{d['oi_tot']}|{f(pf,2)}|{f(pb,2)}|{f(pn,2)}|"
          f"{d['strikes']}|{d['strikes_fillable']}|{d['strikes_both']}")

print()
print("### B4 summary -- the gate input")
print("sym|minutes|median_pct_fillable|worst_pct_fillable|worst_minute")
gate_fill = {}
for sym in ("NIFTY", "SENSEX"):
    v = fill.get(sym, [])
    if not v:
        continue
    med = q([x[0] for x in v], 0.50)
    worst = min(v, key=lambda x: x[0])
    gate_fill[sym] = (med, worst[0])
    print(f"{sym}|{len(v)}|{f(med,2)}|{f(worst[0],2)}|{worst[1]} {worst[2]}")

# ---------------------------------------------------------------- verdict
print()
print("### B VERDICTS (thresholds fixed before any number was seen)")
for sym in ("NIFTY", "SENSEX"):
    if sym not in gate_fill or sym not in gate_ratio:
        print(f"{sym}|UNMEASURED -- no data aggregated")
        continue
    ok, tot = gate_ratio[sym]
    med, worst = gate_fill[sym]
    ratio_pass = ok >= 10
    fill_pass = (med is not None and med >= 95.0) and (worst is not None and worst >= 90.0)
    if fill_pass and ratio_pass:
        v = "B: history usable as stored"
    elif fill_pass and not ratio_pass:
        v = "B: history usable with one gamma per strike"
    else:
        bits = []
        if not fill_pass:
            bits.append(f"median fillable {f(med,2)}% (need >=95), worst minute {f(worst,2)}% (need >=90)")
        if not ratio_pass:
            bits.append(f"ratio in band on {ok}/{tot} days (need >=10)")
        v = "B: history not usable, re-solve needed -- " + "; ".join(bits)
    print(f"{sym}|{v}")
    print(f"       ratio_test: {ok}/{tot} days in [0.95,1.05] -> {'PASS' if ratio_pass else 'FAIL'}")
    print(f"       fill_test : median {f(med,2)}%, worst {f(worst,2)}% -> {'PASS' if fill_pass else 'FAIL'}")
