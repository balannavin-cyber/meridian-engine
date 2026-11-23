#!/usr/bin/env python3
"""POST-HOC item 0 -- how the vendor gamma field is represented, counted from the
chain files. One symbol-day in memory at a time. No database."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHAIN = HERE.parent / "replay_v2" / "chain"


def acc():
    return {"n": 0, "oi": 0.0}


tot = defaultdict(lambda: defaultdict(lambda: defaultdict(acc)))   # sym->cls->side
raw_forms = defaultdict(int)

for fp in sorted(CHAIN.glob("out_*.txt")):
    sym, _ = fp.name[4:-4].split("_", 1)
    r0, legs = {}, defaultdict(dict)
    for line in fp.read_text(encoding="utf-8").splitlines():
        if not line or "|" not in line:
            continue
        tag, pay = line.split("|", 1)
        j = json.loads(pay)
        if tag == "R0" and "09:15" <= j["ts_ist"][11:16] <= "15:29":
            r0[j["run_id"]] = j
        elif tag == "R1":
            legs[j["run_id"]].setdefault(float(j["strike"]), {})[j["ot"]] = j
    for rid, meta in r0.items():
        S = float(meta["spot_min"]) if meta.get("spot_min") else 0.0
        if S <= 0:
            continue
        for K, pair in legs.get(rid, {}).items():
            # strike set: OI > 0 on at least one leg
            oi_any = any(float(v.get("oi") or 0) > 0 for v in pair.values())
            if not oi_any:
                continue
            for ot, j in pair.items():
                oi = float(j.get("oi") or 0)
                if oi <= 0:
                    continue
                has = "gamma" in j
                g = j.get("gamma")
                if not has or g is None or g == "":
                    cls = "missing"
                else:
                    raw_forms[str(g)[:12] if float(g) == 0 else "nonzero"] += 1
                    cls = "zero" if float(g) == 0 else "positive"
                side = ("ITM" if K < S else "OTM") if ot == "CE" else \
                       ("ITM" if K > S else "OTM")
                for sd in (side, "ALL"):
                    a = tot[sym][cls][sd]
                    a["n"] += 1
                    a["oi"] += oi
    r0.clear(); legs.clear()

print("POST-HOC item 0 -- vendor gamma field representation, legs with OI > 0 in the")
print("strike set, market runs 09:15-15:29 IST")
print()
print("raw renderings seen for a zero gamma:",
      {k: v for k, v in raw_forms.items() if k != "nonzero"})
print()
for sym in ("NIFTY", "SENSEX"):
    print("=" * 76)
    print(sym)
    for sd in ("ALL", "ITM", "OTM"):
        N = sum(tot[sym][c][sd]["n"] for c in ("missing", "zero", "positive"))
        O = sum(tot[sym][c][sd]["oi"] for c in ("missing", "zero", "positive"))
        print(f"  {sd:<4} legs {N}   OI {O:.0f}")
        for c in ("missing", "zero", "positive"):
            a = tot[sym][c][sd]
            pc = 100.0 * a["n"] / N if N else float("nan")
            po = 100.0 * a["oi"] / O if O else float("nan")
            print(f"       {c:<9} count {a['n']:>8} = {pc:6.3f}%   "
                  f"OI-weighted {po:6.3f}%")
