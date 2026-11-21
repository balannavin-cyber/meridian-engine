# NOT VERIFIED — atlas exploration, 2026-11-18

Exploration. No verdict. Nothing here is a finding until confirmed once on
unseen data.

Things this run takes on trust, measured but could not explain, or inherited
from the closed M1/M2 run without re-checking. Each entry says what is unsettled,
what depends on it, and what would settle it.

---

## 1. The vendor's strike listing may be truncated on 24 sessions (Study D rule a)

**Measured, not explained.** A wall is the strike with the largest OI on its
side. On **11 of 247** sessions the call wall is the **highest** strike the
vendor lists, and on **13 of 247** the put wall is the **lowest**. When the
arg-max sits on the boundary of the listed range, a larger OI outside that range
is indistinguishable from a genuine peak at the edge.

Call-edge sessions (wall, listed `kmax`, % from prior spot):

| date | wall | kmax | % |
|---|---|---|---|
| 2025-04-01 | 25400 | 25400 | +9.58 |
| 2025-04-03 | 25400 | 25400 | +9.28 |
| 2025-04-04 | 25400 | 25400 | +10.84 |
| 2025-04-07 | 25400 | 25400 | +14.22 |
| 2025-04-09 | 25400 | 25400 | +13.29 |
| 2025-04-11 | 25400 | 25400 | +11.19 |
| 2025-04-15 | 25400 | 25400 | +8.81 |
| 2025-04-17 | 25500 | 25500 | +6.97 |
| 2025-04-30 | 26100 | 26100 | +7.66 |
| 2025-05-29 | 26800 | 26800 | +7.71 |
| 2025-05-30 | 26800 | 26800 | +8.34 |

Put-edge sessions: 2025-04-07 (20650, −7.14 %), 2025-04-09 (20400, −9.01 %),
2025-04-11 (20400, −10.69 %), 2025-06-13 (22800, −7.83 %), 2025-06-16 (22800,
−8.58 %), 2025-06-30 (22800, −10.61 %), 2025-08-08 (22800, −6.36 %), 2025-08-14
(22600, −8.16 %), 2026-01-29 (23300, −8.35 %), 2026-02-25 (23100, −9.34 %),
2026-03-04 (23100, −5.61 %), 2026-03-05 (22750, −8.03 %), 2026-03-06 (22750,
−7.03 %).

**This is not an extraction defect.** The tag-B query applies **no strike
filter** — `extract_session_chain.sql:66-67` restricts instrument, trade_date
and front expiry only, and the one strike reference at `:65` is inside a LEFT
JOIN to the Greeks sidecar, which cannot remove a bar row. Verified against the
database on edge session 2025-04-01: the full front-expiry chain holds **102
strikes, 20350–25400**, identical to tag B. A re-extraction returns the same
rows.

*What depends on it:* Study D's wall location on those 24 sessions. Every Study D
table is reported with and without them (reading D-a).

*What would settle it:* a chain source with a wider strike listing for those
cycles. Nothing in this database can distinguish a truncated listing from a
genuine far-OTM peak, because the truncation, if any, is upstream of the stored
table.

---

## 2. Why 2025-10-21's chain stops at 14:45:59 (Study D rule b)

**Measured, not explained.** Of 247 sessions, exactly one — **2025-10-21** — has
its last `hist_option_bars_1m` bar at or before 15:29:59 land at **14:45:59**
rather than 15:29:59. The cause is not established: a vendor gap, a truncated
session and a capture failure are not distinguishable from the stored rows.

*What depends on it:* the walls for **2025-10-23**, the session that would have
taken them from 2025-10-21's close. That session is excluded from Study D walls
and counted; the wall count is 245, not 246 (reading D-b).

*What would settle it:* an NSE session record for 2025-10-21, or the vendor's own
coverage log. Neither is in this repo.

---

## 3. Why some sessions produce no wall approach (Study D rule c)

**Will be counted, not explained.** A session produces no approach when price
never comes within the band of either wall from the inside. That can be because
the wall was far away or because price did not travel; the two are not separable
from the approach set alone, which is why the no-approach count is reported by
wall-distance bucket (≤2 %, 2–4 %, >4 %) at every band (reading D-c).

Context already measured: the call wall sits beyond **+4 %** of spot on **78 of
247** sessions, the put wall beyond **−4 %** on **59 of 247**. A wall that far
out can only be approached by a very large move.

*What depends on it:* whether the approach set is representative of sessions at
all. If approaches concentrate in the ≤2 % bucket, Study D describes near walls
and says nothing about distant ones.

*What would settle it:* nothing further — the counts themselves are the answer,
and they are reported rather than inferred.

---

## 3a. D2 (OI at the wall strike) was not computed in this run; Study D is D1 only

**Specified, not built.** The brief specified D2 as the change in OI **at the
wall strike itself** over the 30 minutes before the approach, giving a 2×2
against futures OI. **No such extraction was made and no such table exists.**

Verified in the code: zero occurrences of `D2`, `wall_oi` or `strike_oi` in any
pipeline module; the approach rows carry 18 fields of which the only OI columns
are `dF_30` and `dF1_30`, both **futures**; and all 516 Study D cells are
`table=D-break` with exactly two outcomes, `break_rate` and
`max_excursion_pct`.

The chain data this run holds cannot substitute. `../data/session_chain.csv`
tag B carries per-strike OI only at each session's **close** — one bar per
session — so it cannot give an intraday 30-minute change at a strike. D2 needs a
per-approach-session read of `hist_option_bars_1m` for the wall strikes across
the 30 minutes before the approach minute.

*What depends on it:* the whole of the brief's D2. Every Study D conditioning
variable in this document is futures OI; **no statement about option OI at the
wall is made or supportable from it.**

*What would settle it:* that extraction, and a rerun of Study D with it.

---

## 4. The Stage 1 figure of −0.35 bp

**Taken as supplied, never reproduced.** K2 prints this run's 15-minute LB − SB
30-minute mean (**+0.0983 bp**) beside the Stage 1 NIFTY figure
(**−0.3500 bp**), a difference of **+0.4483 bp**. The Stage 1 figure is quoted
from the brief; **no Stage 1 code, definition or output exists in this repo** —
the earlier search for its artefacts found nothing anywhere. So the comparison is
against a number whose construction cannot be inspected.

K2 lists five definitional differences that could account for any gap (window
length, OI series, outcome horizon, sample exclusions, price series). **No
parameter was adjusted to close it**, and no conclusion is drawn from the
difference.

**Stage 1's definition, operator-supplied 2026-11-18** from the project doc
`MR_FOI1_close_inputs.md`:

- near contract;
- 15-minute dP × dOI classes;
- eligibility at **0.5 × the trailing 20-session slot median**;
- the **last 6 sessions before a futures expiry excluded**;
- 30-minute outcome;
- day-clustered bootstrap;
- code `stage1_design.py`, run on local CSVs.

**Neither file is in this repo.** `MR_FOI1_close_inputs.md` and
`stage1_design.py` were both searched for and are absent, so the definition
above is recorded as supplied and **was not read from source by this run**.

Set against K2's five candidates, that definition closes three and leaves two
open — stated as a mapping, not as an explanation of the gap:

| K2 candidate | Status against the supplied definition |
|---|---|
| window length | **Closed** — both are 15-minute classification windows |
| outcome horizon | **Closed** — both are 30-minute |
| OI series | **Open** — "near contract" is a single contract, closest to this run's **F1**, not to F (series 1+2+3). This run's K2 figure is on F |
| sample exclusions | **Open, and different** — Stage 1 drops the last 6 sessions before each futures expiry; this run **flags** expiry days and the session after, and drops nothing |
| price series | **Open** — this run's P is the series-1 futures close; the supplied definition does not state its price series |

One difference the supplied definition adds that K2 did not list: **an
eligibility filter at 0.5 × the trailing 20-session slot median**. This run has
no such filter — its "strong" cut is a different construction (above the slot
median, not above half of a trailing median) and is reported separately rather
than applied as eligibility.

**K2 was not rerun and nothing was adjusted.** The mapping is recorded so a
later reader knows which parts of the +0.4483 bp difference are already
accounted for by definition and which are not.

*What would settle it:* `stage1_design.py` and the CSVs it ran on.

---

## 5. `g` covers only part of the window

**Inherited, measured.** Study C reads the dose `g` from the closed run's
`m2_windows.csv`, which exists only for the **182 sessions M2 kept** — not the
full 247. The 65 sessions M2 dropped (53 option expiry days, 11 sessions after a
futures expiry, 1 on bar presence) carry no `g`.

*What depends on it:* the `g` column of Study C's BEFORE panel, and nothing else.
Its denominator is stated separately wherever it appears.

---

## 6. The futures expiry list is inherited, and one date is operator-supplied

**Inherited from the closed M1/M2 run without re-derivation.** The 12 dates are
11 inferred from the OI ladder (clauses a AND b) plus **2026-03-30**, which is
operator-supplied from the Fyers expired-contracts API and was never verified
against Fyers by that run or this one.

*What depends on it:* the expiry flags on every table (reading R14), and Study
B's days-to-expiry and cycle assignment.

---

## 7. OI and volume units are inherited

**Inherited.** That both OI series are index-unit quantities rests on the closed
run's C2 (per-session GCD recovering the NSE lot, 75 then 65). This run did not
re-measure it. The unit of `hist_future_bars_1m.volume` was never tested at all —
it is read as an index-unit quantity by analogy with `oi`, which is the whole of
the evidence for it (closed run `NOT_VERIFIED.md` §10).

*What depends on it:* any figure carrying an "index units" label; volume appears
in this run only if a volume cut is reported.

---

## 8. 207 off-lot option OI legs

**Inherited, unexplained.** 207 option OI values across 12 sessions are not whole
multiples of the era lot (closed run `NOT_VERIFIED.md` §5, as corrected). Those
sessions are not excluded here. They affect the chain OI that Study D's walls are
built from, on sessions in late June 2025, late December 2025 and 2026-03-24…27.

---

*Exploration. No verdict. Nothing here is a finding until confirmed once on
unseen data. No entry was resolved by assumption.*
