#!/usr/bin/env python3
"""VS follow-up, part A3 + B. POST-HOC diagnostics -- not frozen measures. Disk only."""
from __future__ import annotations

import csv
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
V2DIR = HERE.parent / "replay_v2"
STEP = {"NIFTY": 50.0, "SENSEX": 100.0}
L: list[str] = []


def em(s=""):
    L.append(s)


def num(v):
    return None if v in (None, "", "None") else float(v)


def sh(n, d, nd=1):
    return "n/a(0)" if not d else f"{100.0*n/d:.{nd}f}% ({n}/{d})"


def f(x, nd=0):
    return "-" if x is None else f"{x:.{nd}f}"


rows = []
with (V2DIR / "runs.csv").open(encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        if r["sym"] != "SENSEX" or r["day"] != "2026-11-19":
            continue
        for k in ("S", "B", "V2", "VS", "FV", "F", "K", "K_lead",
                  "call_wall", "put_wall"):
            r[k] = num(r[k])
        r["frozen"] = r["frozen"] == "True"
        r["valid"] = r["valid"] == "True"
        rows.append(r)
rows.sort(key=lambda r: r["ts_ist"])
mkt = [r for r in rows if r["segment"] == "market" and r["valid"]]

# band rows for that symbol-day, if any were pulled
band = {}
bp = HERE / "band_SENSEX_2026-11-19.txt"
if bp.exists():
    for line in bp.read_text(encoding="utf-8").splitlines():
        if line.startswith("P0|"):
            j = json.loads(line.split("|", 1)[1])
            band[j["run_id"]] = j

em("## A3 — SENSEX 2026-11-19, every third market run — POST-HOC")
em("")
em(f"Market runs that day: {len(mkt)}. Stored pin-band rows matched by run_id: "
   f"**{len(band)}** (see B3). The band_lo / band_hi columns are therefore shown as "
   "`-` on every row; they are NOT reconstructed.")
em("")
em("`X` marks a pin outside the stored corridor [put wall, call wall].")
em("")
em("| ts IST | S | B | X | V2 | VS | X | K | K lead | put wall | call wall | band_lo | band_hi | frozen |")
em("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")


def out(p, r):
    if p is None or r["put_wall"] is None or r["call_wall"] is None:
        return " "
    return "X" if not (r["put_wall"] <= p <= r["call_wall"]) else " "


for r in mkt[::3]:
    b = band.get(r["run_id"], {})
    em(f"| {r['ts_ist'][11:16]} | {f(r['S'],2)} | {f(r['B'])} | {out(r['B'],r)} | "
       f"{f(r['V2'])} | {f(r['VS'])} | {out(r['VS'],r)} | {f(r['K'])} | "
       f"{f(r['K_lead'],4)} | {f(r['put_wall'])} | {f(r['call_wall'])} | "
       f"{b.get('pin_lower','-')} | {b.get('pin_upper','-')} | "
       f"{'Y' if r['frozen'] else 'N'} |")
em("")
em("Counts over ALL market runs of SENSEX 2026-11-19:")
em("")
em("| quantity | value |")
em("|---|---|")
wd = [r for r in mkt if r["put_wall"] is not None and r["call_wall"] is not None]
for c in ("B", "VS", "K"):
    have = [r for r in wd if r[c] is not None]
    em(f"| {c} outside [put wall, call wall] | "
       f"{sh(sum(1 for r in have if not (r['put_wall']<=r[c]<=r['call_wall'])), len(have))} |")
em(f"| frozen runs | {sh(sum(1 for r in mkt if r['frozen']), len(mkt))} |")
for c in ("B", "VS", "K"):
    seq = [r[c] for r in mkt if r[c] is not None]
    em(f"| pin changes, {c} | {sum(1 for i in range(len(seq)-1) if seq[i]!=seq[i+1])} "
       f"(over {len(seq)} runs) |")
em("")

em("## B — the pin band — POST-HOC")
em("")
em("**B1. Definition.** `public.v_gex_strike_pin_zone`, defined in "
   "`~/meridian-engine/sql/2026-10-26_s101_v_gex_strike_pin_zone_live_captured.sql:30` "
   "(`CREATE OR REPLACE VIEW`, file is 125 lines). The band-deciding lines are the "
   "`peak` CTE (`:74-82`), the recursive `walk` CTE (`:83-112`) and the final "
   "aggregate (`:113-124`):")
em("")
em("```sql")
em(" 77:            scoped.strike AS peak_strike,")
em(" 78:            scoped.gex_cr AS peak_gex_cr,")
em(" 79:            COALESCE(get_parameter_num('pin.tau.'::text || scoped.symbol), 0.3) AS tau")
em(" 80:           FROM scoped")
em(" 81:          WHERE scoped.gex_cr > 0::numeric")
em(" 82:          ORDER BY scoped.run_id, scoped.symbol, scoped.expiry_date, scoped.gex_cr DESC, (abs(scoped.strike - scoped.spot))")
em(" 83:        ), walk AS (")
em(" 88:            p.peak_strike AS strike,")
em(" 96:         SELECT g.run_id,")
em("105:                CASE")
em("106:                    WHEN g.strike < w_1.strike THEN '-1'::integer")
em("107:                    ELSE 1")
em("108:                END AS direction")
em("109:           FROM walk w_1")
em("110:             JOIN scoped g ON ... AND ((w_1.direction = ANY (ARRAY[0, -1])) AND abs(g.strike - (w_1.strike - w_1.step)) < 0.0001")
em("110:                                   OR (w_1.direction = ANY (ARRAY[0, 1]))  AND abs(g.strike - (w_1.strike + w_1.step)) < 0.0001)")
em("112:          WHERE g.gex_cr > 0::numeric AND g.gex_cr >= (w_1.tau * w_1.peak_gex_cr)")
em("118:    min(strike) AS pin_lower,")
em("119:    max(strike) AS pin_upper,")
em("120:    count(*) AS n_strikes,")
em("123:    (array_agg(strike ORDER BY gex_cr DESC))[1] AS peak_pin_strike,")
em("124:    max(tau) AS tau_used")
em("```")
em("")
em("It walks on **`gex_cr` SIGN-FILTERED to positive only** — `WHERE scoped.gex_cr > "
   "0` both at the peak (`:81`) and at every walk step (`:112`), so a negative-`gex_cr` "
   "strike stops the walk and can never be inside the band.")
em("")
em("**tau** is the walk's stopping fraction of the peak: a neighbouring strike joins "
   "the band only while `gex_cr >= tau * peak_gex_cr` (`:112`), with "
   "`tau = COALESCE(get_parameter_num('pin.tau.'||symbol), 0.3)` (`:79`) — i.e. 0.3 by "
   "default, per-symbol overridable, and reported back as `tau_used`.")
em("")
em("**B2. Stored per run_id — YES, but not in `gex_cycle_history`.**")
em("")
em("| table | columns matching band/zone/pin/lo/hi/low/high/peak |")
em("|---|---|")
em("| `gex_cycle_history` | `pin_leader_strike` (17), `gamma_at_pin` (18), "
   "`conc_hhi` (25), `pin_state` (27), `pin_state_reason` (28) — **no band low/high** |")
em("| `gex_pin_maxpain_history` | `peak_pin_strike` (8), **`pin_lower` (9)**, "
   "**`pin_upper` (10)**, `pin_n_strikes` (11), `peak_pin_gex_cr` (12) |")
em("")
em("Band low and high per run_id ARE stored, in **`public.gex_pin_maxpain_history`**, "
   "columns **`pin_lower`** and **`pin_upper`**, keyed "
   "`UNIQUE (symbol, run_id, expiry_date)` "
   "(`gex_pin_maxpain_history_symbol_run_id_expiry_date_key`).")
em("")
em("**B3. Pulled, and the result is zero rows.**")
em("")
em("| symbol-day | band rows returned |")
em("|---|---|")
tot = 0
for sym in ("NIFTY", "SENSEX"):
    for d in ("2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"):
        p = HERE / f"band_{sym}_{d}.txt"
        n = sum(1 for x in p.read_text(encoding="utf-8").splitlines()
                if x.startswith("P0|")) if p.exists() else 0
        tot += n
        em(f"| {sym} {d} | {n} |")
em(f"| **all ten** | **{tot}** |")
em("")
em("All ten symbol-days returned **0 rows**, each query gated (Index Scan using "
   "`gex_pin_maxpain_history_symbol_run_id_expiry_date_key`, estimate 1 row, no Seq "
   "Scan), rc 0, empty stderr, 2.51–2.77 s. So the per-run-id join, the outside-band "
   "counts and the median band width asked for in B3 are **NOT COMPUTABLE** on these "
   "days, and the `band_lo` / `band_hi` columns in A3 are empty.")
em("")
em("**The table is not empty overall, but its extent is UNMEASURED.** The only plan "
   "available for a whole-table `min(ts)/max(ts)` probe is a **Seq Scan on "
   "`gex_pin_maxpain_history`**, which the gate forbids, so that query was not run. "
   "The rejected plan's own row estimate was 11,808, which is a planner estimate and "
   "not a count; nothing here establishes which dates the table does cover.")
em("")

(HERE / "_partB.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
