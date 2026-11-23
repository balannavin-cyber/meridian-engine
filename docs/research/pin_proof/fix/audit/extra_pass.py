#!/usr/bin/env python3
"""POST-HOC extra pass -- the two per-run quantities item 4 needs that runs.csv does
not carry: the top strike's share of total gross_R, and leg-level OI-weighted rates
for missing / zero / sub-0.00010 vendor gamma. One symbol-day in memory at a time."""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "replay"))
sys.path.insert(0, str(HERE.parent.parent / "lookback_v5"))
from score_replay import _g            # noqa: E402
from analyze_v5 import compute_run     # noqa: E402

CHAIN = HERE.parent / "replay_v2" / "chain"
OUT = HERE / "extra.csv"
COLS = ["sym", "day", "run_id", "ts_ist", "top_gR_share",
        "oi_tot", "oi_missing", "oi_zero", "oi_sub1e4",
        "n_legs", "n_missing", "n_zero", "n_sub1e4"]

with OUT.open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=COLS)
    w.writeheader()
    for fp in sorted(CHAIN.glob("out_*.txt")):
        sym, day = fp.name[4:-4].split("_", 1)
        r0, legs = {}, defaultdict(dict)
        for line in fp.read_text(encoding="utf-8").splitlines():
            if not line or "|" not in line:
                continue
            tag, pay = line.split("|", 1)
            j = json.loads(pay)
            if tag == "R0" and "09:15" <= j["ts_ist"][11:16] <= "15:29":
                r0[j["run_id"]] = j
            elif tag == "R1":
                e = legs[j["run_id"]].setdefault(
                    float(j["strike"]),
                    {"c_gamma": None, "p_gamma": None, "c_oi": 0.0, "p_oi": 0.0,
                     "c_px": 0.0, "p_px": 0.0, "c_raw": None, "p_raw": None})
                oi = float(j["oi"]) if j.get("oi") not in (None, "") else 0.0
                px = float(j["ltp"]) if j.get("ltp") not in (None, "") else 0.0
                raw = j["gamma"] if "gamma" in j else None
                if j["ot"] == "CE":
                    e["c_gamma"], e["c_oi"], e["c_px"], e["c_raw"] = raw, oi, px, raw
                else:
                    e["p_gamma"], e["p_oi"], e["p_px"], e["p_raw"] = raw, oi, px, raw
        for rid, meta in r0.items():
            S = float(meta["spot_min"]) if meta.get("spot_min") else 0.0
            rows = {k: v for k, v in legs.get(rid, {}).items()
                    if v["c_oi"] > 0 or v["p_oi"] > 0}
            if S <= 0 or not rows:
                continue
            o = {c: "" for c in COLS}
            o.update(sym=sym, day=day, run_id=rid, ts_ist=meta["ts_ist"])
            # leg-level rates over legs with OI > 0
            ot = om = oz = os_ = 0.0
            nt = nm = nz = ns = 0
            for e in rows.values():
                for raw, oi in ((e["c_raw"], e["c_oi"]), (e["p_raw"], e["p_oi"])):
                    if oi <= 0:
                        continue
                    nt += 1
                    ot += oi
                    if raw in (None, ""):
                        nm += 1
                        om += oi
                        continue
                    g = float(raw)
                    if g == 0:
                        nz += 1
                        oz += oi
                    if g < 0.00010:          # includes the zeros, by design
                        ns += 1
                        os_ += oi
            o.update(oi_tot=ot, oi_missing=om, oi_zero=oz, oi_sub1e4=os_,
                     n_legs=nt, n_missing=nm, n_zero=nz, n_sub1e4=ns)
            cr = compute_run(sym, meta["ts_ist"][:10], meta["ts_ist"][11:16], S,
                             meta["expiry"], rows, [])
            if cr.get("valid"):
                gK = cr["g"]
                gr = {K: gK.get(K, 0.0) * (rows[K]["c_oi"] + rows[K]["p_oi"])
                      for K in rows}
                tot = sum(gr.values())
                o["top_gR_share"] = (max(gr.values()) / tot) if tot > 0 else ""
            for k in ("_rows", "g", "g_flat", "sigma_k"):
                cr.pop(k, None)
            w.writerow(o)
        r0.clear(); legs.clear()
        print(f"{fp.name} done", flush=True)
(HERE / "DONE_EXTRA").write_text("ok\n", encoding="utf-8")
print("DONE_EXTRA")
