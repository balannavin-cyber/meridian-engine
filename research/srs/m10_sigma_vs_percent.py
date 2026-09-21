#!/usr/bin/env python3
"""M10 stage 1 -- constant sigma versus constant percent. ZERO requests.

THE QUESTION. The pre-registration picks strikes at 1% from spot. At the
measured IV terciles the same 1% is a very different sigma-distance in a calm
week than a wild one. If outcomes depend on sigma-distance rather than on
percent, the strike rule is wrong.

WHAT WOULD FALSIFY A POSITIVE RESULT, stated before the numbers. A real
sigma-distance effect means the >=50/60/70/80 shares vary MONOTONICALLY across
sigma-distance terciles. Non-monotone buckets, or a spread inside sampling
noise at these N, is no effect. The brief's own gate is a spread wider than 10
percentage points at DTE 1 before stage 2 is worth running.

THE COUPLING THAT MAKES THIS NEARLY A RESTATEMENT, and which is measured here
rather than assumed. For a strike at 1% of spot:

    sigma_distance = 0.01*S / (S * IV/100 / sqrt(252)) = sqrt(252) / IV

so sigma-distance is a deterministic function of ATM IV alone -- 1.59 sigma at
IV 10, 1.19 at IV 13.3, 0.79 at IV 20 -- and the ONLY independent variation
comes from rounding the strike to the exchange grid. That rounding is not
negligible and differs by symbol: NIFTY rounds 1% of ~24,000 (240 pts) to a
50-pt grid, SENSEX rounds 1% of ~80,000 (800 pts) to a 100-pt grid. The
realised correlation between sigma-distance and 1/IV is reported below; if it
is ~1.0 then this measurement is the M1 IV-regime split under another name and
must be read as such, not as independent corroboration.

CAVEATS INHERITED FROM THE CACHE. This reads `.m1_era1_cycles.json` as written
by the run of 08:02, which predates three fixes: per-leg staleness rejection
(so a stamp lost to one stale leg lost all legs), Muhurat removal from the
index (so DTE is inflated by one for any cycle containing 2025-10-21), and the
HELD_ATM rename. M10 uses only the OTM legs and the threshold shares, so the
rename is irrelevant; the other two are stated per table.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".m1_era1_cycles.json"
RESULTS = HERE / "srs_exploration_2026-09-21_m10_stage1.md"

THRESHOLDS = (50, 60, 70, 80)
OTM_LEGS = ("OTM_PE", "OTM_CE")
DTE_ORDER = ["DTE5", "DTE4", "DTE3", "DTE2", "DTE1", "DTE0", "EXP1300"]


def _deser(d):
    return dt.date.fromisoformat(d["__date__"]) if "__date__" in d else d


def leg_decay(stamp, leg):
    """Works on both cache shapes: pre-fix whole-stamp and post-fix per-leg."""
    if "legs" in stamp:
        l = stamp["legs"].get(leg)
        return None if (not l or l.get("rejected")) else l["decay"]
    if stamp.get("rejected"):
        return None
    return stamp.get("decay", {}).get(leg)


def stamp_dte(rec, stamp):
    if stamp["label"] == "EXP1300":
        return "EXP1300"
    return f"DTE{rec['n_days'] - int(stamp['label'][1:])}"


def terciles(xs):
    s = sorted(xs)
    return (s[len(s) // 3], s[2 * len(s) // 3]) if len(s) >= 3 else None


def bucket(v, cuts):
    if cuts is None:
        return "all"
    return "near" if v <= cuts[0] else ("far" if v > cuts[1] else "mid")


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    if sx == 0 or sy == 0:
        return float("nan")
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def main():
    payload = json.loads(CACHE.read_text(), object_hook=_deser)
    cycles = payload["measured"]

    # sigma-distance per cycle per OTM leg
    for c in cycles:
        c["sdist"] = {
            "OTM_PE": (c["spot_ref"] - c["k_pe"]) / c["sigma_d"],
            "OTM_CE": (c["k_ce"] - c["spot_ref"]) / c["sigma_d"],
        }

    by = defaultdict(list)
    for c in cycles:
        for lg in OTM_LEGS:
            by[(c["symbol"], lg)].append(c)
    cuts = {k: terciles([c["sdist"][k[1]] for c in cs]) for k, cs in by.items()}

    # threshold shares by (symbol, leg, sigma-bucket, DTE), pooled state
    dec = defaultdict(list)
    for c in cycles:
        for lg in OTM_LEGS:
            b = bucket(c["sdist"][lg], cuts[(c["symbol"], lg)])
            for s in c["stamps"]:
                d = leg_decay(s, lg)
                if d is None:
                    continue
                t = stamp_dte(c, s)
                for bb in (b, "all"):
                    dec[(c["symbol"], lg, bb, t)].append(d)

    def share(xs, thr):
        return 100.0 * sum(1 for x in xs if x >= thr) / len(xs)

    w = []
    a = w.append
    a("# M10 stage 1 -- constant sigma versus constant percent")
    a("")
    a(f"Generated {dt.date.today().isoformat()}. **Zero database requests** -- "
      f"computed entirely from `.m1_era1_cycles.json` ({len(cycles)} measured "
      f"era-1 cycles).")
    a("")
    a("## What would falsify a positive result")
    a("")
    a("A real sigma-distance effect means the threshold shares vary "
      "**monotonically** across sigma-distance terciles. Non-monotone buckets, "
      "or a spread inside sampling noise at these N, is no effect. The brief's "
      "gate for stage 2 is a spread wider than **10 percentage points at "
      "DTE 1**.")
    a("")
    a("## The coupling: this is largely the IV split under another name")
    a("")
    a("For a strike at 1% of spot, "
      "`sigma_distance = 0.01*S / (S * IV/100 / sqrt(252)) = sqrt(252)/IV` -- "
      "a deterministic function of ATM IV alone. The only independent variation "
      "is grid rounding, which differs by symbol: NIFTY rounds 240 points to a "
      "50-point grid, SENSEX rounds 800 points to a 100-point grid.")
    a("")
    a("| symbol | leg | corr(sigma_dist, 1/IV) | sigma-dist terciles | min | max |")
    a("|---|---|---:|---|---:|---:|")
    for k in sorted(by):
        cs = by[k]
        xs = [c["sdist"][k[1]] for c in cs]
        ys = [1.0 / c["atm_iv"] for c in cs]
        cu = cuts[k]
        a(f"| {k[0]} | {k[1]} | {pearson(xs, ys):.3f} | "
          f"{cu[0]:.2f} / {cu[1]:.2f} | {min(xs):.2f} | {max(xs):.2f} |")
    a("")
    a("A correlation at or near 1.000 means this table is the M1 IV-regime "
      "split relabelled, and is **not** independent corroboration of it.")
    a("")

    a("## M10.A  The question: spread between FAR and NEAR tercile at DTE 1")
    a("")
    a("`far` = largest sigma-distance (lowest IV). Spread = far minus near, in "
      "percentage points.")
    a("")
    a("| symbol | leg | thr | near | mid | far | spread (far-near) | monotone? |")
    a("|---|---|---|---:|---:|---:|---:|---|")
    verdict_rows = []
    for sym in ("NIFTY", "SENSEX"):
        for lg in OTM_LEGS:
            for thr in THRESHOLDS:
                vals = {}
                for b in ("near", "mid", "far"):
                    xs = dec.get((sym, lg, b, "DTE1"), [])
                    vals[b] = share(xs, thr) if xs else None
                if any(v is None for v in vals.values()):
                    continue
                sp = vals["far"] - vals["near"]
                mono = ((vals["near"] <= vals["mid"] <= vals["far"]) or
                        (vals["near"] >= vals["mid"] >= vals["far"]))
                verdict_rows.append((sym, lg, thr, sp, mono))
                a(f"| {sym} | {lg} | >={thr}% | {vals['near']:.0f}% | "
                  f"{vals['mid']:.0f}% | {vals['far']:.0f}% | {sp:+.0f} pp | "
                  f"{'yes' if mono else 'NO'} |")
    a("")
    wide = [r for r in verdict_rows if abs(r[3]) > 10]
    mono_n = sum(1 for r in verdict_rows if r[4])
    a(f"**{len(wide)} of {len(verdict_rows)}** DTE-1 cells show a spread wider "
      f"than the 10 pp stage-2 gate. **{mono_n} of {len(verdict_rows)}** are "
      f"monotone across the three buckets.")
    a("")

    a("## M10.B  Full threshold shares by sigma-distance bucket and DTE")
    a("")
    a("Pooled state (tested and untested together) -- the ex-ante view. "
      "`N*` marks N < 20.")
    a("")
    a("| symbol | leg | bucket | DTE | N | >=50% | >=60% | >=70% | >=80% |")
    a("|---|---|---|---|---:|---:|---:|---:|---:|")
    for k in sorted(dec, key=lambda x: (x[0], x[1],
                                        {"all": 0, "near": 1, "mid": 2,
                                         "far": 3}.get(x[2], 9),
                                        DTE_ORDER.index(x[3])
                                        if x[3] in DTE_ORDER else 99)):
        xs = dec[k]
        n = f"{len(xs)}" + ("*" if len(xs) < 20 else "")
        a(f"| {k[0]} | {k[1]} | {k[2]} | {k[3]} | {n} | "
          + " | ".join(f"{share(xs, t):.0f}%" for t in THRESHOLDS) + " |")
    a("")
    a("## Inherited caveats")
    a("")
    a("This reads the cache written at 08:02, which predates three fixes:")
    a("")
    a("- **whole-stamp rejection** -- a stamp lost to one stale leg lost all "
      "legs, so OTM N here is lower than it will be after per-leg rejection;")
    a("- **Muhurat still counted as a trading day** -- DTE is inflated by one "
      "for any cycle containing 2025-10-21;")
    a("- the HELD_ATM rename, which is irrelevant here since M10 uses only the "
      "OTM legs.")
    a("")
    a("None of the three plausibly reverses a monotonic spread, but all three "
      "shift N and DTE labels slightly. Re-run after the era-1 re-sweep lands.")
    a("")

    with RESULTS.open("w", encoding="utf-8") as fh:
        fh.write("\n".join(w) + "\n")

    print(f"cycles={len(cycles)}  DTE1 cells={len(verdict_rows)}  "
          f"spread>10pp={len(wide)}  monotone={mono_n}")
    for sym, lg, thr, sp, mono in verdict_rows:
        if thr == 50:
            print(f"  {sym} {lg} >=50%: spread {sp:+.0f} pp  "
                  f"monotone={'yes' if mono else 'NO'}")
    for k in sorted(by):
        xs = [c["sdist"][k[1]] for c in by[k]]
        ys = [1.0 / c["atm_iv"] for c in by[k]]
        print(f"  corr(sigma_dist, 1/IV) {k[0]} {k[1]}: {pearson(xs, ys):.3f}")
    print(f"wrote {RESULTS.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
