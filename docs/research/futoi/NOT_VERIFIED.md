# NOT VERIFIED — MR-FOI M1 / M2 run, 2026-11-17/18

Things taken from the pre-registration or from the operator's instructions that
this run could **not** check against the database, plus claims it checked and
found not to reproduce. Each entry says what was taken on trust, what would
settle it, and whether anything in the result depends on it.

---

## 1. `2026-03-30` as a NIFTY futures expiry — operator-supplied, not inferred

**Taken on trust.** The OI-ladder rule needs a session d+1 and therefore cannot
decide the last session in the data. The operator supplied 2026-03-30 as a NIFTY
futures expiry, citing the Fyers expired-contracts API (2026-11-17). **This run
did not query Fyers and did not verify it.**

*What depends on it:* 2026-03-30 is excluded from M1 and M2 by §2, and the
2026-03-30 option expiry is ineligible for M1 as a result. With it the futures
expiry list is 12, exactly one per calendar month — a structural check that
passed. Without it the list would be 11, with March 2026 absent.

*What would settle it:* the Fyers expired-contracts listing for NIFTY futures,
or a `hist_future_bars_1m` row carrying a non-NULL `expiry_date`.

---

## 2. §2's "OI at 15:29 identical on 247/247 (series 1), 246/247, 242/247"

**Not checked.** §2 records a verification made on 2026-11-17 against a Fyers
pull. This run has no access to that pull and did not reproduce the comparison.
The vendor table was used as given.

*What depends on it:* the claim that `contract_series` is expiry rank. The
OI-ladder detection in entry 1 of the result doc's change-of-record is
consistent with it — the ladder shifts by exactly one rung at each detected
expiry, 11 times — but that is corroboration, not the stated check.

---

## 3. §2's "join measured 100 %, Data Inventory §6.1" — reproduces only in scope

**Checked, and it does not hold chain-wide.** Measured at the 2025-10-15 close
bar: the `hist_option_bars_1m` → `hist_option_greeks_1m` join on the five-column
key matched **117 of 433** rows chain-wide (27.0 %). Per expiry it is **117/117
= 100.0 %** on the front expiry and **0 %** on each of the other nine.

*What depends on it:* nothing is harmed — both M1 (the series expiring on E, at
the E−1 close, which is the front expiry there) and M2 (front expiry) sit
entirely inside the covered scope. But §2's sentence is true of the scope used
and false of the chain, and a later reader should not generalise it.

---

## 4. §6's "193 of 247 sessions solved" — does not reproduce, and is unsourced

**Checked, and it does not reproduce.** Measured over the window:

| Quantity | Measured |
|---|---|
| Sessions in `hist_option_bars_1m` | 247 |
| Sessions with any row in `hist_option_greeks_1m` | 194 |
| Sessions with at least one solved `iv` | 194 |
| Sessions with a solved `iv` at the 15:29:59 close bar | 188 |

The figure 193 appears only in the pre-registration; it is not carried by any
register, inventory or data-contract row in the repo. Neither 194 nor 188 equals
it.

*What depends on it:* nothing — §6 offers it as an expectation, not a gate. M1's
eligibility counted its own exclusions (3 events lost to an unsolved `iv`).

---

## 5. The 207 off-lot option OI legs — cause not established

**Measured, not explained.** 207 option OI values on 13 of 247 sessions are not
whole multiples of the era lot (75 before the 2025-12-30 change, 65 after), so
the per-session GCD recovers 25 or 5 instead of the lot. Rows in
`data/c2_offlot_legs.csv`. Clusters: 2025-06-19…25, 2025-12-23…29, and
2026-03-24…27.

*Correction 2026-11-18: the 13 here is the GCD-inequality count, not off-lot sessions; see entry 13.*

*What depends on it:* nothing in the verdicts. C2's two stated conditions hold on
every session (every GCD > 1; gcd(futures, options) > 1 on 247 of 247), so both
series are index-unit quantities in a compatible unit and ĥ is dimensionless. No
leg was excluded on this ground.

*What would settle it:* the vendor's own OI unit documentation for those dates,
or an NSE corporate-action / lot-revision record covering them.

---

## 6. Whether the SENSEX front expiry specifically carries a solved `iv`

**Not measured.** The SENSEX sidecar probe counted rows across **all** expiries
at the close bar on 12 sampled sessions. Coverage there was all-or-nothing per
session: 8 of 12 sampled sessions carried 49k–77k sidecar rows with `iv` solved
on 98.6–99.9 % of them; 4 carried none. The front-expiry share — the scope item
7.1 actually needs — was measured for NIFTY (100 %) but **not** for SENSEX.

*What depends on it:* item 7.1 is descriptive and counts its own exclusions by
reason, so a gap would surface as a counted ineligible event rather than a silent
one. It reported 49 eligible SENSEX events and 3 ineligible, one of them for an
unsolved SENSEX `iv`.

---

## 7. Why four SENSEX sessions carry no sidecar rows at all

**Not explained.** The four empty sessions among the 12 probed are 2025-04-01,
2025-07-01, 2025-10-01 and 2026-01-01 — each the first session of a quarter. The
same all-or-nothing pattern exists on the NIFTY side (194 of 247 sessions carry
sidecar rows), so it is a property of the backfill rather than of SENSEX.

**No mechanism is claimed.** n = 4 with no mechanism is n = 4 with no mechanism;
the pattern is recorded as a pattern and nothing is inferred from it.

---

## 8. `futoi_m1.py` reads the NIFTY spot close by exact key; §7 uses §2's rule

**A difference in the code, recorded rather than reconciled.** `futoi_m1.py`
takes the NIFTY spot close as `spot[d]['15:29:59']` — an exact key match — while
`futoi_s7.py` takes the SENSEX spot close as the last bar at or before 15:29:59,
which is §2's stated rule. The two agree whenever the 15:29:59 bar exists and
differ only when it does not, in which case M1 declares the event ineligible
rather than stepping back to an earlier bar.

*What depends on it:* M1 reported no event lost for a missing spot close, and
every NIFTY session measured 375 of 375 bars in Part 0, so the two rules cannot
have diverged on this data. `futoi_m1.py` was not edited; the difference is
recorded so a reader knows which rule produced which number.

---

## 9. The window's data contamination status

**Checked against the registry, and clean — but the registry is the only source
consulted.** `public.data_contamination_ranges` holds four ranges. None names
`hist_future_bars_1m`, `hist_option_bars_1m`, `hist_option_greeks_1m`,
`hist_spot_bars_1m` or `hist_gamma_metrics`, and none overlaps the window for a
field this run reads. Rule 13 is satisfied as written. Whether an unregistered
incident touched these tables is, by construction, not knowable from the
registry.

---

## 10. The unit of `hist_future_bars_1m.volume`

**Assumed, never tested.** §7's volume item reports a coefficient of **+3,761.11
index-unit quantity per index point** and a median window volume of **51,012
index-unit quantity**. Both read `volume` as an **index-unit quantity**, by
analogy with `oi` in the same table — and that analogy is the whole of the
evidence for it.

C2 tested the unit of **OI**, on both sides, by measuring the per-session GCD and
showing it recovers the NSE lot (75, then 65). **No equivalent test was run on
`volume`.** If `volume` were a contract count rather than an index-unit quantity,
every figure in §7.2 would be out by the lot factor — about 75× for most of the
window, 65× after 2025-12-30. The two regression coefficients would scale with
it; nothing in M1 or M2 would change, because neither reads `volume`.

*What depends on it:* §7.2 only, which is descriptive and carries no verdict. The
note under that table points here.

*What would settle it:* the same GCD measurement C2 applies to OI, run on
`volume` — if its per-session GCD recovers 75 then 65, `volume` is an index-unit
quantity on the same convention; a GCD of 1 would mean a contract count.

---

*No entry here was resolved by assumption. Where a claim was checked and failed
to reproduce (entries 3 and 4), the measured value is given and the
pre-registration's figure is not used anywhere in the result.*
