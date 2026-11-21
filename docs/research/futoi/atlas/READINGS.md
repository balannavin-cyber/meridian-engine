# READINGS — atlas exploration, 2026-11-18

Exploration. No verdict. Nothing here is a finding until confirmed once on
unseen data.

Where the brief left a choice open, the simplest reading was taken and recorded
here rather than asked about. Nothing in this list is a threshold, a gate or a
test. Readings were fixed before the tables they govern were computed.

---

## Study D — the three rules ruled by the operator, 2026-11-18

**D-a. The 11 call-edge and 13 put-edge sessions are FLAGGED, and every Study D
table is reported with and without them.**
A wall is the strike with the largest OI on its side. On 11 of 247 sessions the
call wall is the **highest** strike the vendor lists, and on 13 the put wall is
the **lowest** — so the true maximum may lie beyond the listed range and the
arg-max is censored. The flag is `edge_call` / `edge_put`
(`atlas_build.py:226`), carried onto every approach row (`:259`, `:279`). The
call-edge sessions are all April–May 2025 with `kmax` repeating at 25400 /
25500 / 26100 / 26800; the put-edge sessions run April 2025 – March 2026 with
`kmin` repeating at 20400 / 22800 / 23100 / 22750. Full date lists in
`NOT_VERIFIED.md` §1.

**D-b. 2025-10-21 is EXCLUDED from Study D walls, and counted.**
Its tag-B bar is **14:45:59**, not 15:29:59 — it is the one session of 247 whose
last chain bar at or before 15:29:59 is not the close. Walls are defined from a
prior session's close, so the exclusion falls on **2025-10-23**, the session
whose walls would have been fixed from 2025-10-21. Implemented at
`atlas_build.py:196` and the `bars != {"15:29:59"}` branch; it fired once and
the wall count is **245**, not 246. The exclusion is printed by name whenever
Study D runs.

**D-c. Sessions producing NO approach are counted at each band, split by wall
distance (≤2 %, 2–4 %, >4 %).**
A session with a distant wall cannot produce an approach, so the no-approach
count is a property of where the wall sat, not of what price did. Reporting it
by distance bucket keeps that visible instead of letting the approach set look
like a random sample of sessions. Bands 0.10 %, 0.15 % and 0.25 %; buckets from
`wall_distance_bucket()`. Measured context: the call wall sits beyond +4 % of
spot on **78 of 247** sessions and the put wall beyond −4 % on **59 of 247**.

---

## Class contrasts — operator ruling, 2026-11-18

**R0. A class effect is a difference against the PAIRED class at the same price
sign, and each pair is reported once.**

- **LB vs SC** — both have dP > 0 and differ only in the sign of dOI.
- **SB vs LU** — both have dP < 0 and differ only in the sign of dOI.
- SC vs LB and LU vs SB are the same contrasts with the sign flipped, so they
  are **not** reported separately.

The rule applies to **A1** (window classes), **A3** (day classes) and **C3**
(classes within large windows). It does not apply to A3's run-length table,
which compares run lengths within one class and so shares a price sign already.

*Why.* Differencing a class against a complement that mixes dP signs measures an
up-window/down-window asymmetry, not anything about OI: LB's complement would
contain SB and LU, both of which have the opposite price sign. Holding dP's sign
fixed leaves the sign of dOI as the only thing that varies, which is the
dimension these studies are about. This is the same correction applied to A2,
where the complement holds the current class fixed and varies only the previous
one.

**Ledger consequence.** A1's cells are the same windows re-cut across strengths,
subsets, time-of-day buckets and outcomes, so one structure appears as many
correlated cells. The ledger therefore also counts A1 by
**(contrast, step, OI series) family** — how many families carry any interval
excluding zero — beside the raw cell count.

---

## Series and units

**R1. P, S, F, F1.** P = series-1 futures close; S = spot close; F = futures OI
summed over series 1+2+3 and **None whenever any of the three is missing at that
minute**; F1 = series-1 OI alone. Every OI-based cut runs on F (primary) and F1
(secondary).

**R2. Ranges are measured from bar highs and lows**, pulled by this run into
`data/fut_bars_hl.csv` and `data/spot_bars_hl.csv`, not approximated from
closes. The closed M1/M2 run's CSVs carry closes only.

**R3. Ranges and returns are measured on P**, the series-1 futures close — not
on spot — because the outcomes are defined on P. Day-level "intraday range" is
likewise P's high-minus-low.

**R4. Returns are in basis points of the reference price**; OI changes are in
index units (C2 of the closed run measured both OI series as index-unit
quantities). Every figure carries its unit in the table.

---

## Windows and classes

**R5. Full grid windows only.** Non-overlapping windows of 15 / 30 / 60 minutes
from 09:15. Boundaries at 09:15 + k·L while ≤ 15:29. The ragged tail between the
last grid boundary and 15:29 is **not** a window and is not counted as one:
24 windows at 15 min, 12 at 30, 6 at 60.

**R6. Boundary convention.** For a window [a, b]: dP = P(b) − P(a),
dOI = OI(b) − OI(a). The outcome starts **at b**, so the first forward increment
is b → b+1 and no conditioning minute lies inside any outcome. `cond_ts` and
`out_ts` are carried on every row and `build_windows()` asserts
`cond_ts <= out_ts`.

**R7. FLAT and MISSING are different and never merged.** FLAT is a measured
change of exactly zero in dP or dOI; MISSING is a value that could not be
computed — a bar absent, or F null because a series is missing that minute.
Merging them would let a missing F be counted as a measured class. Both are
reported in every class table; `REAL_CLASSES` is the four directional ones.

**R8. "Strong" = |dP| and |dOI| both above that time slot's median**, the median
taken across sessions within the slot, separately for each window length and
each OI series.

**R9. Time-of-day bucket is taken from the window's END minute** — the minute the
outcome starts from — not its start.

**R10. Continuation = sign(dP) × forward return, in bp.** A FLAT or MISSING
window has no sign and therefore no continuation.

---

## Statistics

**R11. Intervals are session-clustered percentile bootstraps of a MEAN**, 2,000
resamples, seed 20261118, computed on per-session (sum, count) so a resample is
O(n_sessions). **Medians are reported as point estimates without an interval** —
the sum/count shortcut does not extend to them. The "effect" in every cell is the
mean; the median sits beside it unbounded.

**R12. Intervals are descriptive.** An interval excluding zero is not a test
result and is not called significant anywhere in this run.

**R13. Spearman ρ is reported without a p-value**, as a descriptive rank
association. Rank-biserial is 2·AUC − 1 from the Mann-Whitney U, ties at half
credit: +1 means one group always above the other, 0 no separation.

---

## Sample

**R14. Futures expiry days and the session after are FLAGGED, not dropped.**
Every table is reported with and without them. The 12 expiry dates are inherited
from the closed M1/M2 run (11 inferred from the OI ladder, 1 operator-supplied —
see `NOT_VERIFIED.md` §6).

**R15. Window 2025-04-01 … 2026-03-30, NIFTY only.** A date guard refuses any
input file carrying a `trade_date` after the window end, so nothing after
2026-03-30 is read and the Stage 1 holdout stays sealed. The vendor clock is used
as-is (:59 stamps), with no conversion between tables. The 15:30 bar is never
used.

**R16. Study B's days-to-expiry counts trading sessions** from the session to the
next futures expiry at or after it. The norm is the median b at the same
(days-to-expiry, clock time) **leaving out the session's own expiry cycle**, so a
session never contributes to the norm it is measured against.

---

*Exploration. No verdict. Nothing here is a finding until confirmed once on
unseen data.*
