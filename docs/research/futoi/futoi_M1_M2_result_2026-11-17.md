# MR-FOI M1 / M2 — result

**The result is null. M1 is NOT DETECTED and M2 is NOT OBSERVED.** Neither
measurement found the hedge footprint the pre-registration set out to look for,
on the window and by the tests fixed before any outcome was computed.

| Field | Value |
|---|---|
| Pre-registration | `futoi_M1_M2_prereg_2026-11-17.md`, `git hash-object` **7006391b52cbbaab451800428fc2205d5f97f6e1** |
| Hash recorded | 2026-11-17T14:53:14Z, before the first outcome query (`PREREG_HASH.txt`) |
| Repo HEAD at recording | `8fde9df` |
| Window | 2025-04-01 → 2026-03-30, NIFTY for both verdicts |
| Risk class | RO. Every query through `bin/roq.sh` as `merdian_ro`. No DB write, no commit, no branch, no push |
| Interval method | **Percentile bootstrap, 10,000 resamples, seed 20261117.** M1 resamples events; M2 resamples whole sessions |
| scipy | Not installed, and not installed by this run. Wilcoxon imported unmodified from `services/tape_scoring/wilcoxon.py`; Spearman, OLS and the bootstraps written here and brute-force validated |

---

## 1. Verdicts

### M1 — **NOT DETECTED**

In the pre-registration's words: *both tests met → HEDGE FOOTPRINT PRESENT; Test 1
only → EXPIRY EFFECT, NOT DOSE-SCALED; otherwise → NOT DETECTED.* Neither test
was met. **38 eligible events, so the UNDERPOWERED label of §6 does not apply**
(it attaches below 20).

### M2 — **NOT OBSERVED**

In the pre-registration's words: *significant and both stability conditions met →
MECHANISM OBSERVED (indicative), with the sign; significant but unstable →
UNSTABLE; not significant → NOT OBSERVED.* β1's 95 % session-clustered interval
contains zero, so the verdict is NOT OBSERVED and **no sign reading is made.**
The §4 degeneracy gate did **not** trip (largest one-sided share of `g` is
72.3 %, against the 90 % gate), so the dose was not one-signed — the verdict
rests on the test, not on a degenerate regressor.

### §7 — descriptive, no verdict

Four items reported below. None carries a verdict, a threshold comparison or a
significance claim.

---

## 2. M1 — hedge ratio at weekly expiry (§3)

### Sample, with every denominator

| Quantity | Count |
|---|---|
| Option expiry dates in the window | 53 |
| Futures expiry days (§2) | 12 |
| Sessions excluded by §2 (expiry day + the session after) | 23 of 247 |
| Sessions with a one-day futures change available | 246 of 247 |
| Sessions in the week-median pool | 182 |
| **Eligible events** | **38** |
| Ineligible, with reason | 15 |

Ineligible, each with its reason (no cell suppressed):

| Reason | Count |
|---|---|
| Futures expiry day (§2) | 12 |
| No solved `iv` at the close of E−1 | 3 (2026-03-10, 2026-03-17, 2026-03-24) |

The three March exclusions had 186, 191 and 194 chain legs respectively and
**0** solved legs — the Greeks sidecar, not the chain, is what is missing.

### Test 1 — Wilcoxon signed-rank on d(E), one-sided, H: median < 0, α = 0.05

| | |
|---|---|
| n events | 38 |
| median d(E) | **+0.006191 log points of futures OI** |
| W+ | 491.0 |
| W− | 250.0 |
| zeros dropped | 0 |
| p (exact permutation) | **0.960398** |
| Met at 0.05 | **No** |

> Code prints the W− value under the label W+; see entry 7. Measured on the 38
> events: W+ = 491, W− = 250, W+ + W− = 741 = 38·39/2, so the two are consistent
> and only the label was wrong. The p-value is unaffected — `signed_rank_less`
> negates the differences before ranking, so the statistic it tests is the right
> one and 0.960398 stands.

d(E) is positive at the median: on expiry days futures OI rose slightly relative
to the week, in the direction opposite to the hypothesis.

### Test 2 — Spearman ρ, abnormal fall in quantity vs G(E), one-sided, H: ρ > 0

| | |
|---|---|
| n events | 38 |
| ρ | **+0.205821** |
| p (Monte-Carlo permutation, 200,000 draws, seed 20261117) | **0.108524** |
| p (asymptotic t) — cross-check, not the test | 0.107542 |
| Met at 0.05 | **No** |

The two p-values are reported together because a parity claim is made by a test
that compares the two numbers, never by a comment. They agree to 0.001.

### Test 3 — ĥ (estimate, no verdict)

| Estimate | Median | 95 % percentile bootstrap CI | n |
|---|---|---|---|
| ĥ vs G(E) | −0.002696 | [−0.008421, +0.000164] | 38 |
| ĥ vs N(E) | −0.029068 | [−0.106095, +0.001125] | 38 |

Unit: **dimensionless** — index units of futures OI per index unit of gross
delta. C2 established that both sides are index-unit quantities, so no
conversion is stated.

### Placebo — descriptive, no verdict

The Thursday→Tuesday move anchor is taken from the data, not recalled: the first
Tuesday futures expiry is **2025-09-30**.

| Set | n | median | one-sided p |
|---|---|---|---|
| Non-expiry Tuesdays before the move | 21 | +0.002679 | 0.5136 (exact) |
| Non-expiry Thursdays after the move | 22 | +0.002042 | 0.5 (exact) |

---

## 3. M2 — basis response to γ (§4)

### Sessions and windows, with every denominator

| Quantity | Count |
|---|---|
| Sessions in the window | 247 |
| Bar-presence threshold | 357 of 375 minutes (95 % of 09:15:59–15:29:59) |
| **Sessions kept** | **182** |
| Sessions dropped | 65 |
| Windows possible (182 × 68) | 12,376 |
| **Windows used** | **12,376** |
| Windows with no usable row | **0** |

Dropped sessions, each with its reason:

| Reason | Count |
|---|---|
| Option expiry day (§4 — the sidecar skips dte 0) | 41 |
| Option expiry day **and** futures expiry day (§2) | 12 |
| Session after a futures expiry (§2) | 11 |
| Bar presence below 95 % (spot 113/375, series-1 61/375) | 1 |

### Distribution of the dose g (unitless, −1…+1)

n = 12,376 windows. Positive 8,945 (**72.3 %**), negative 3,431 (27.7 %), zero 0.

| p0 | p10 | p20 | p30 | p40 | p50 | p60 | p70 | p80 | p90 | p100 |
|---|---|---|---|---|---|---|---|---|---|---|
| −0.3448 | −0.0894 | −0.0328 | +0.0084 | +0.0410 | +0.0708 | +0.1000 | +0.1283 | +0.1597 | +0.2019 | +0.3836 |

**Degeneracy gate: not tripped** (72.3 % against the 90 % gate).

### Model — Δb = a + β0·ΔS + β1·(g × ΔS) + ε, OLS

Units: ΔS and Δb in NIFTY index points, g unitless, so β0 and β1 are index
points of basis change per index point of spot change.

| Coefficient | Value |
|---|---|
| a (intercept) | −0.01415705 index points |
| β0 | −0.01577826 |
| **β1** | **−0.06010872** |
| β1 95 % CI, session-clustered percentile bootstrap, 182 clusters, 10,000 resamples | **[−0.17659213, +0.10071598]** |

### Test — β1 ≠ 0, two-sided, α = 0.05

Deciding statistic: the 95 % session-clustered bootstrap interval excludes zero.
**It does not.** → **NOT OBSERVED.**

### Stability (reported in full, though the test was not met)

| Condition (a): half-years | Sessions | Windows | β1 |
|---|---|---|---|
| Apr–Sep 2025 | 93 | 6,324 | **+0.03565411** |
| Oct 2025–Mar 2026 | 89 | 6,052 | **−0.15964216** |

Signs agree between the half-years: **No.**

Condition (b): terciles of session realised volatility (sample SD of the 68
five-minute **log** spot returns). Cut points **p33.3 = 0.00047604**,
**p66.7 = 0.00062178** (log-return SD).

| Tercile | Sessions | Windows | β1 |
|---|---|---|---|
| T1 low vol | 61 | 4,148 | +0.11404720 |
| T2 mid vol | 60 | 4,080 | −0.12148855 |
| T3 high vol | 61 | 4,148 | −0.12533449 |

Terciles matching the pooled sign: **2 of 3 → met.** With condition (a) unmet
and the test unmet, the verdict is NOT OBSERVED regardless.

---

## 4. Controls (§5) — all four passed before any outcome was computed

Each control states what would make it fail, in the same breath as its verdict.

| Control | Fails when | Measured | Result |
|---|---|---|---|
| **C1** clock | a one-minute label offset would put the maximum at lag ±1 | lag −1 **+0.013201**, lag 0 **+0.864710**, lag +1 **+0.046609** (n = 7,480 pairs, 20 sessions, seed 20261117) | **PASS** |
| **C2** units | a contract-count series has GCD 1; two incompatible units make ĥ meaningless | median futures OI 14,956,275; median front-expiry option OI per strike near spot 3,373,425; sessions with GCD ≤ 1 **0 of 247**; sessions with gcd(fut, opt) ≤ 1 **0 of 247**; min gcd 5 | **PASS** |
| **C3** γ parity | sign disagreement above 15 % would mean g is not the board's net gamma | **489 / 500 = 97.8 %** agreement with `hist_gamma_metrics.net_gex`, drawn from 12,253 eligible window starts at seed 20261117 | **PASS** |
| **C4** delta sanity | a wrong T, a percent-vs-decimal `iv`, or a sign error would push ATM call Δ outside 0.35–0.65 | five sampled E−1 closes: Δ = 0.5052, 0.5382, 0.4845, 0.4995, 0.5504; T = 0.002740 yr | **PASS** |

**Lot size, measured per session** (the pooled GCD over the window is 5, which is
gcd(75, 65) — a lot NSE never listed, so pooling is not the measurement):

| Series | Contiguous runs |
|---|---|
| Futures s1 | 2025-04-01 … 2025-12-30 → **75**; 2025-12-31 … 2026-03-30 → **65** |
| Options | 75 → 25 → 75 → 25 → 65 → 5 → 65 (see §6 entry 3) |

---

## 5. §7 — descriptive, no verdict

Two self-checks ran before any §7 number, and both are tests that compare rather
than claims that assert:

- **M2 reproduction (C5).** M2's own rows pushed back through the same `fit()`
  and `boot_cluster()` calls reproduced `a`, `β0`, `β1`, `b1_ci_lo` and
  `b1_ci_hi` at **abs diff 0.00e+00** on every key, 12,376 windows, 182
  clusters, 10,000 resamples. §7 therefore holds M2's model, clustering and seed
  identically before it varies one input.
- **Week-median pool (C6).** 38 events checked, **0 mismatches** against the
  `week_others_n` column M1 recorded.

### 7.1 SENSEX → NIFTY

| | |
|---|---|
| NIFTY sessions in the window | 247 |
| SENSEX sessions with chain rows | 246 (missing: 2025-06-05) |
| SENSEX option expiry days | 52 |
| **Eligible SENSEX events** | **49** |
| Ineligible | 3 (one no prior NIFTY session; one no solved SENSEX `iv` / no SENSEX spot close at E−1; one session after a futures expiry) |

| Statistic | Value |
|---|---|
| median d(E) | +0.002679 log points of NIFTY futures OI |
| Wilcoxon one-sided p | 0.449019 (exact) |
| Spearman ρ vs SENSEX G(E) | +0.060000 |
| Spearman one-sided p | 0.340528 (Monte-Carlo) |
| ĥ vs SENSEX G(E), median | −0.00798249 |
| 95 % percentile bootstrap CI | [−0.01874709, +0.04052015] |

**Zero of the 49 events fall on a NIFTY option-expiry day**, so the
NIFTY-expiry-removed line is identical to the full line (n = 49 both). ĥ here
has NIFTY futures OI in the numerator and SENSEX gross delta in the denominator
— **different underlyings, so it is not comparable with M1's ĥ and is not a
hedge ratio**; it is a scale between two indices.

### 7.2 Volume

n = 12,376 windows, 0 dropped, 68 time-of-day slots, slot effects by within-slot
demeaning (identical to 68 dummies; the intercept is 0 by construction and
measured at +1.3e−12).

| Term | Coefficient |
|---|---|
| \|ΔS\| | +3,761.11 index-unit quantity per index point |
| \|ΔS\| × gross γ | −0.00515653 per (index point × index-unit γ·OI) |

*Unit as assumed in the extraction; not verified, see `NOT_VERIFIED.md`.*

Medians: volume 51,012 index-unit quantity; \|ΔS\| 8.0000 index points; gross
γ·OI 198,894 index units.

### 7.3 Synthetic forward

12,558 minutes carried PCP rows; **0** had a row count other than 3; 12,558
forwards built; **0** windows dropped. Both fits use exactly the same 12,376
windows, so the only difference is what b is measured against.

| | b vs PCP forward | b vs spot (M2) |
|---|---|---|
| a (index points) | −0.00056283 | −0.01415705 |
| β0 | +0.00237328 | −0.01577826 |
| β1 | −0.06320640 | −0.06010872 |
| β1 interval low | −0.11692325 | −0.17659213 |
| β1 interval high | −0.00928673 | +0.10071598 |

*Descriptive. M2's registered verdict (spot-based b, NOT OBSERVED) stands. This interval was not registered as a test.*

### 7.4 Expiry-afternoon path

15 steps, 12:00:59 → 15:15:59 every 15 minutes plus the close at 15:29:59 (a
14-minute final gap, because the 15:30 bar is never used). Each day is
ln F(t) − ln F(12:00:59). 38 event days (0 dropped), 139 other days (1 dropped).

| Step | Event median | n | Other median | n | Difference |
|---|---|---|---|---|---|
| 12:00:59 | +0.000000 | 38 | +0.000000 | 139 | +0.000000 |
| 13:00:59 | +0.001871 | 38 | +0.001933 | 139 | −0.000062 |
| 14:00:59 | +0.004412 | 38 | +0.003157 | 139 | +0.001255 |
| 15:00:59 | +0.010033 | 38 | +0.004963 | 139 | +0.005070 |
| 15:29:59 | +0.013798 | 38 | +0.010399 | 139 | +0.003398 |

Full 15-step table in `data/s7_afternoon_path.csv`. Unit: log points of total
futures OI (series 1+2+3) relative to 12:00:59.

---

## 6. Change of record

Every item was settled **before** the outcome it could have touched was
computed. Nothing in the pre-registration's thresholds, windows, exclusions or
tests was added, dropped or tuned.

**1 — Futures expiry rule: clause (a) alone → (a) AND (b).**
`hist_future_bars_1m.expiry_date` is NULL on **all 260,126** NIFTY rows
(measured), so futures expiry days are inferred from the OI ladder. Coded first
as clause (a) alone — "OI_s2(d) is the nearest of {s1,s2,s3}(d) to OI_s1(d+1)" —
it fired on **21** of 246 session pairs with no margin separation: weakest firing
**1.05×** against a strongest non-firing margin that overlaps it. Changed to the
conjunction (a) AND (b), as the rule was stated, after the Part 0 measurement and
before any outcome: **11** firings, every one at margin **≥ 9.82×** against a
best (a)-only margin of **4.94×**. The 11 dates are the last Thursday of each
month to 2025-08 and the last Tuesday from 2025-09 — the Thursday→Tuesday move
the pre-registration itself records in §3.

**2 — 2026-03-30 is operator-supplied, not inferred.** The ladder rule needs a
d+1 and cannot decide the last session in the data. 2026-03-30 is a NIFTY futures
expiry per the Fyers expired-contracts API (operator-supplied 2026-11-17). With
it the list is **12 expiries, exactly one per calendar month 2025-04 … 2026-03**
— a check that was required to hold before Part 1 and did. Listed in
`NOT_VERIFIED.md`: this run did not verify it against Fyers.

**3 — C2 re-specified to §5's words.** C2 was first implemented with a third
condition — "the per-session GCDs are equal on every session" — that §5 does not
state. It failed on 13 of 247 sessions where 207 option legs are not whole
multiples of the era lot, so the GCD recovers a divisor (25, or 5) rather than
the lot. That is **not** the failure C2 names: the medians are plausible only as
index units (as contract counts the futures leg would be 1.12 billion index
units), and both series step 75 → 65 at the same NSE lot change. The stop was
recorded, diagnosed in `diagnose_c2.py`, and the re-specification ruled by the
operator before Part 1. The first stop record is preserved verbatim as
**`STOPPED_C2_first_fail_20261117.md`**. The 207 off-lot legs are carried into
Limits below and into `NOT_VERIFIED.md`; they are not suppressed.

*Correction 2026-11-18: the 13 here is the GCD-inequality count, not off-lot sessions; see entry 13.*

**4 — F(d) is None unless all three series are present.** `futures_total_oi`
first returned `sum(present)` and the caller ignored `missing`, so a partial sum
could have stood in for F(d) and lost the roll-invariance §3 depends on.
Corrected before any outcome. **Measured effect: 0 of 247 sessions** — the defect
was latent because §2's close rule (last bar at or before 15:29:59, applied per
series) already recovers series 3 on the sessions where it is absent at exactly
15:29:59. No number in this run changes.

**5 — §7's date guard misfired on a summary file.** The guard was applied to
`m2_summary.csv` with `datecol="key"`, took `max()` over that file's **key**
column, got the string `'verdict'`, and reported `'verdict' > '2026-03-30'` as a
breach of the §8 holdout. That file holds no dates at all; **nothing past
2026-03-30 was ever involved**, and no §7 number had been produced. Corrected
before any was: a value is compared with the window end only if it matches
`YYYY-MM-DD`; a non-date value in a per-session date column is its own stop with
its own message; `m2_summary.csv` is read without the guard. `--guard-test` now
shows the guard tripping on 2026-03-31 (the first day past the window end),
giving the non-date message on `'verdict'`, and passing on in-window dates.

**6 — SENSEX / NIFTY expiry overlap, and the SENSEX no-`iv` sessions.**
*Observation only; no interpretation is offered.*
Checked locally on `data/s7_sensex_events.csv` against `data/m1_events.csv` +
`data/m1_ineligible.csv`:

- NIFTY expiry dates found: **53** (38 from `m1_events.csv`, 15 from
  `m1_ineligible.csv`).
- SENSEX events: **49**.
- Overlap: **none**. Independently corroborated by the scorer's own
  `on_nifty_opt_expiry` flag, which is True on **0** of 49 rows.
- The median SENSEX event is **2025-07-22 (Tue)**, d(E) **+0.0026788134**.
  *This figure also appears in the M1 placebo row for non-expiry Tuesdays before
  the move. No interpretation of that match is offered here.*

Membership comparison, measured: `data/sensex_chain.csv` holds **246** SENSEX
sessions, of which **53** have no solved `iv` at the close. That count equals the
**53** NIFTY expiry dates. **The two sets are not identical** (`set == set` →
False). Nothing beyond those printed counts is asserted; the size of the
intersection was not produced.

**7 — M1 Test 1 printed W− under the label W+.** `futoi_m1.py` prints
`signed_rank_less`'s returned `w_plus` under the label "W+". `signed_rank_less`
negates the differences before ranking, so the value it returns is the
positive-rank sum **of the negated series** — that is, **W− of d(E)**, 250.0.
Measured on the 38 events: **W+ of d(E) = 491.0, W− = 250.0, total 741 =
38·39/2**. The **tested statistic and the p-value (0.960398) are unaffected** —
the negation is how the one-sided "median < 0" alternative is formed, so the
test is the right one and only the print label was wrong.
`services/tape_scoring/wilcoxon.py` is **unmodified** and its own docstring
defines `w_plus` correctly for the series it ranks; **the defect is the print
label in `futoi_m1.py`, nothing else.** The Test 1 table above carries both
values.

**8 — The two spot-close rules were reconciled by measurement, not by argument.**
`futoi_m1.py` takes the NIFTY spot close by **exact key** (`spot[d]['15:29:59']`)
while §2 states the close as **the last bar at or before 15:29:59**, which is the
rule `futoi_s7.py` applies to SENSEX spot. The two differ only when the exact bar
is absent, in which case M1 declares the event ineligible rather than stepping
back. `NOT_VERIFIED.md` entry 8 argued from full bar coverage that they *cannot*
have diverged. **Measured instead, over `data/spot_bars.csv`: 247 NIFTY sessions,
0 with no exact 15:29:59 bar, and 0 sessions where the two rules give a different
close.** The argument is replaced by a count; no M1 number depends on which rule
was used. `futoi_m1.py` was **not** edited.

**9 — M2 kept 182 sessions, above §6's expected 150–180.** §6 states *"about
150–180 M2 sessions at 68 windows each"*. Measured: **182 sessions, 12,376
windows**. The excess is two sessions above the top of the stated range, and the
window count is exactly 182 × 68 with **0** windows unusable. The figure is
reported as measured throughout; §6's range is an expectation, not a gate, and
nothing was adjusted to meet it. Recorded here for the same reason §6's "193 of
247 sessions solved" is in Limits: **a pre-registered expectation that does not
reproduce is stated, never quietly absorbed.**

**10 — `futoi_m2.py:338` prints a literal `%%`, recorded AS-RUN and not
corrected.** That line is a bare `print()` with no `%` operand but a `%%` escape
in its literal, so it emitted `the 95%% session-clustered bootstrap CI excludes
0` — see `logs/m2_20261118_0335.log:114`. It is a **display string carrying no
computed value**; the deciding statistic, the interval and the verdict are
unaffected. Lines 273 and 304 use `%%` correctly, inside real format strings.
**Deliberately left uncorrected:** `futoi_m2.py` as hashed in `SHA256SUMS` is the
file that produced the archived M2 log, and editing it would break that
correspondence for a cosmetic defect. A later run that fixes it should expect the
log text to change and nothing else.

**11 — C2's replacement check is an operationalisation of §5 chosen AFTER the
fail.** Stated plainly, because entry 3 does not say it: the original C2 was
written before any measurement, it failed, and the check that replaced it was
devised **with the failing measurement already in view**. §5 gives C2 in prose —
*"both must be quantities (index units), not contracts"* — and prose admits more
than one operationalisation. The one now in force (every session's GCD > 1, and
gcd(futures, options) > 1 on every session) was selected knowing which sessions
had broken the first one. The operator accepted it before Part 1 was computed,
the original stop record is preserved verbatim as
`STOPPED_C2_first_fail_20261117.md`, and the replacement is threshold-free — but
**none of that makes it a pre-registered check.** It is a post-fail choice, and a
reader should weigh C2 accordingly.

**12 — The 2025-12-30 lot change lands one session apart in the two series.**
Measured per-session GCD: futures hold **75** through 2025-12-30 and switch to
**65** on 2025-12-31; options switch to **65** a session earlier, on
**2025-12-30**. So on 2025-12-30 alone the two series disagree — futures 75,
options 65 — and that session is the thirteenth of the GCD-inequality sessions in
entry 13. It carries **no** off-lot legs under the controls' own boundary.
**A sensitivity run dropping the mismatch session was NOT RUN**, and no file or
log in this folder contains one. Nothing in M1 or M2 was recomputed for it.

**13 — "13 sessions" and "207 legs" are two different counts, and earlier text
paired them.** They are not the same set, and the sentence at entry 3 and in
`NOT_VERIFIED.md` §5 reads as though they were. Measured:

- **13 of 247** sessions have futures GCD ≠ options GCD. This is what C2's added
  clause actually failed on.
- **12** sessions carry at least one off-lot option leg, totalling **207** legs,
  under the boundary `futoi_controls.py` uses.
- The thirteenth GCD-unequal session is **2025-12-30** — entry 12's mismatch —
  which has 0 off-lot legs. `13 = 12 + 1`, and the off-lot set is a strict subset
  of the GCD-unequal set.

**306 vs 207 is a one-line difference in the era boundary.** The two source
lines, quoted:

```
diagnose_c2.py:64:    era_lot[d] = 75 if d <= "2025-12-30" else 65
futoi_controls.py:209:                 if r["oi"] and int(round(r["oi"])) % (75 if d <= "2025-12-29" else 65) != 0)
```

`diagnose_c2.py` scores 2025-12-30 against lot **75**; the options series had
already moved to **65** that session, so all 99 of its legs read as off-lot,
giving 13 sessions / 306 legs. `futoi_controls.py` uses `<= 2025-12-29` and
scores that session against 65, giving 12 sessions / 207 legs. **207 over 12
sessions is the figure that matches the options series' own switch date.** The
306-row `data/c2_offlot_legs.csv` was written by `diagnose_c2.py` and therefore
carries the 99 extra rows.

**The 12 off-lot sessions, classified** by joining `data/m1_events.csv` (the
`prior` column — E−1 of an eligible M1 event) and `data/m2_sessions.csv`
(M2-kept), read-only. No statistic is computed:

| Session | Off-lot legs | E−1 of an eligible M1 event | M2-kept | Class |
|---|---|---|---|---|
| 2025-06-19 | 14 | – | no | neither |
| 2025-06-20 | 14 | – | yes | M2-kept only |
| 2025-06-23 | 13 | – | yes | M2-kept only |
| 2025-06-24 | 12 | – | yes | M2-kept only |
| 2025-06-25 | 14 | – | yes | M2-kept only |
| 2025-12-23 | 16 | – | no | neither |
| 2025-12-24 | 19 | – | yes | M2-kept only |
| 2025-12-26 | 17 | – | yes | M2-kept only |
| 2025-12-29 | 17 | – | yes | M2-kept only |
| 2026-03-24 | 23 | – | no | neither |
| 2026-03-25 | 24 | – | yes | M2-kept only |
| 2026-03-27 | 24 | – | yes | M2-kept only |

**None of the 12 is the E−1 of an eligible M1 event**, so no M1 event's G(E) or
N(E) was built from an off-lot session. Nine are M2-kept; three are neither.

**14 — SENSEX spot is missing one session, and it is 2025-04-28.** Measured as a
set difference of `data/spot_bars_sensex.csv` against `data/sessions.txt`:
**246 of 247** NIFTY sessions carry SENSEX spot rows; the one absent is
**2025-04-28**, which is itself a NIFTY session. The earlier note naming that
date **is reproduced by this run.** It is a distinct gap from the SENSEX *chain*
gap already reported in §5 of this document: the chain is missing **2025-06-05**.
Both series are 246/247, on **different** sessions.

**15 — §7's readings S1–S6 and X1–X3, which live only in `futoi_s7.py`.**
Reproduced verbatim with their line numbers, because the result doc otherwise
carries no record of them:

```
futoi_s7.py:42   S1  "the M1 statistic". M1 has three: d(E) and its Wilcoxon (Test 1), the
     43              abnormal fall in quantity against G(E) and its Spearman (Test 2), and h-hat
     44              (Test 3). "computed on NIFTY futures F(d) AGAINST SENSEX G(E)" names a dose
     45              relation, so Test 2's shape is the primary item. READING: all three are
     46              printed, because omitting a computed number is worse than printing it. No p
     47              is compared with alpha and no result is labelled.
     49   S2  SENSEX event eligibility. Section 7 does not restate it. READING: M1's
     50              eligibility, with the chain side moved to SENSEX and the futures side left
     51              on NIFTY -- a SENSEX option expiry E on which no NIFTY futures contract
     52              expires, E not excluded by section 2 (those exclusions are properties of the
     53              NIFTY futures series, which is still the outcome), with SENSEX chain rows
     54              and a solved iv at the SENSEX close of E-1, and an F(E), F(E-1) pair.
     56   S3  Volume: "with time-of-day slot effects". READING: slot = the window's start
     57              boundary (68 slots). Slot effects are applied by WITHIN-SLOT DEMEANING of
     58              the dependent variable and both regressors, which is algebraically identical
     59              to 68 slot dummies and avoids building a 12,376 x 70 design. The intercept
     60              is then zero by construction and is reported as such. "volume per window" is
     61              read as the SUM of series-1 volume over the five bars (t0, t1]; a window
     62              with any missing volume bar is dropped and counted, never partially summed.
     64   S4  Synthetic forward: "b measured against the put-call-parity forward ... in
     65              place of spot". READING: only b changes -- b_syn = series-1 futures close
     66              minus the PCP forward. dS stays the SPOT change, so the regressor is
     67              identical to M2's and the two fits are comparable. The PCP forward per
     68              strike is K + (C - P) * exp(r * T), r = r_used, T = time to 15:30 IST on the
     69              expiry / 365; the forward for the minute is the MEDIAN over the three
     70              nearest strikes, as section 7 states. Minutes with fewer than three usable
     71              strikes are counted and dropped. M2's own spec is refitted on exactly the
     72              same window subset and printed beside it, so the comparison is like for
     73              like rather than synthetic-on-a-subset against M2-on-everything (C4).
     75   S5  Expiry-afternoon path: "F at 15-minute steps" does not say when the
     76              afternoon starts, and F is a level that differs across days. READING: steps
     77              every 15 minutes from 12:00:59 to 15:15:59, plus the close at 15:29:59 --
     78              which is 14 minutes after the previous step, not 15, because the 15:30 bar
     79              is never used (C7). Each day is expressed as ln F(t) - ln F(12:00:59) so
     80              days of different size are comparable. "event days" = M1's eligible events;
     81              "the week's other days" = the other sessions of the same ISO week that are
     82              in the week-median pool.
     84   S6  F(t) intraday. M1's F(d) is defined at the close. READING: at an intraday
     85              step, F(t) is the same 1+2+3 total taken at the last bar at or before t, per
     86              series -- the same rule section 2 states for the close -- and is None unless
     87              all three series are present, exactly as F(d).

     92   X1  The week-median pool. A first draft of item_sensex built its own pool that
     93              omitted M1's third condition -- it excluded the section 2 sessions but NOT
     94              the NIFTY option-expiry days -- so the SENSEX week medians would have been
     95              taken over a wider set than M1's. There is no shared helper to reuse: M1
     96              builds the pool inline through a local `eligible_for_week_median` closure
     97              (d in chg, d not in excluded, d not in opt_expiry_days). The pool is now
     98              built ONCE in main() with all three conditions and PASSED IN, and the
     99              duplicate is deleted. C6 then checks it against the week_others_n column
    100              m1_events.csv recorded, so the agreement is tested, not asserted.
    102   X3  The date guard misfired on a SUMMARY file. It was applied to
    103              m2_summary.csv with datecol="key", so it took max() over that file's KEY
    104              column, got the string 'verdict', and reported 'verdict' > '2026-03-30' as a
    105              breach of the section 8 holdout. The file holds no dates at all. Nothing
    106              past 2026-03-30 was ever involved, and no section 7 number had been produced
    107              when this was found. Corrected before any was: a value is compared with the
    108              window end only if it matches YYYY-MM-DD; a non-date value in a per-session
    109              file's date column is its own Stop with its own message; and m2_summary.csv
    110              is read by load_plain(), without the guard. This is Rule 0 in its usual
    111              form -- the check could fail for a reason other than the one it names, so
    112              `--guard-test` now shows it failing for each named reason and passing
    113              otherwise.
    115   X2  SENSEX spot close at E-1 uses "the last bar at or before 15:29:59", section
    116              2's own rule. NOTE, for the record: futoi_m1.py reads the NIFTY spot close
    117              by EXACT key (spot[d][SESSION_CLOSE]), not by that rule. The two are
    118              identical whenever the 15:29:59 bar exists and differ only when it does not,
    119              in which case M1 declares the event ineligible rather than stepping back to
    120              an earlier bar. futoi_m1.py is not edited here; the difference is recorded
    121              so the result doc can state which rule produced which number.
```

X3 precedes X2 in the file, as shown.

---

## 7. Limits — carried forward, not suppressed

- **207 off-lot option legs on 13 of 247 sessions** (`data/c2_offlot_legs.csv`),
  where OI is not a whole multiple of the era lot. Clustered in late June 2025,
  late December 2025 and 2026-03-24…27. Cause not established. They do not change
  the unit (C2 (a) and (b) hold on every session) and were not excluded from any
  measurement.
  *Correction 2026-11-18: 12 sessions carry the 207 off-lot legs; 13 is the GCD-inequality count; see entry 13.*
- **The pre-registration's "193 of 247 sessions solved" does not reproduce.**
  Measured: **194** sessions with any solved `iv`, **188** with a solved `iv` at
  the 15:29:59 close bar. The figure is unsourced anywhere in the repo.
- **The bars → greeks join is 100 % on the front expiry and 0 % elsewhere**
  (117/117 and 0/316 at the sampled minute). §2's "join measured 100 %" is true
  for the scope M1 and M2 use and false chain-wide.
- **Vendor `iv`, `delta` and `gamma` on `hist_option_bars_1m` are empty for this
  era** (0 of 433 at the sampled minute), so §2's "vendor delta is not used" is
  moot — it does not exist.
- §8's own limits stand unchanged: one year, one index, no like-for-like
  holdout; OI is a stock so ĥ is a lower bound; the basis is a proxy for signed
  flow; arbitrage and cash-carry positions add noise; positioning sign, not a
  dealer sign.

## 8. What was NOT tested

- **No forward confirmation.** Nothing after 2026-03-30 was read. The Stage 1
  holdout stays sealed (§8).
- **No SENSEX futures.** §7 uses NIFTY futures against SENSEX G(E) only.
- **M2's β1 sign is not read**, because the test was not met. The §4 sign mapping
  (β1 < 0 reads as dampening where net γ is positive) is therefore not applied.
- **No causal claim.** M2 tests whether a number scales a response, not who holds
  what (§8).
- **The 15:30 bar is never used**, so nothing here speaks to the closing auction.
- **Section 7 items carry no verdict** and were not compared with any threshold.
- **The C2 off-lot legs were not traced to a cause.**
- **No session-close documentation was written.** This run makes no commit, so
  `CURRENT.md`, `session_log.md`, `merdian_reference.json` and `tech_debt.md` are
  **not** updated and the futoi lane remains unreflected in `CURRENT.md`. The
  pre-registration mints no ADR/TD/ENH ID.

---

## 9. Proposed amendments — **NOT APPLIED**

Listed for a future pre-registration. None of these was used in this run.

1. **Fix the futures-expiry source.** Populating `hist_future_bars_1m.expiry_date`
   would remove the inference in entry 1 entirely. Until then, a pre-registration
   that depends on futures expiry days should state the detection rule itself
   rather than assume the column.
2. **State the bar-presence denominator.** §4's "95 % of spot and series-1 bars"
   needs the 375-minute denominator written down; this run measured it.
3. **Name the deciding statistic for a bootstrap test.** §4 fixes a two-sided
   test and a bootstrap interval but not which decides. State "the 95 % interval
   excludes zero" or "the bootstrap two-sided p", not both.
4. **Fix the boundary convention for windowed measures.** §4 gives the 5-minute
   grid but not which bar supplies a boundary price; the choice determines
   whether the dose is known before the move it scales.
5. **Define "the M1 statistic"** where §7 reuses it — M1 has three.
6. **Consider ĥ against N(E) as the primary estimate.** §3 makes it secondary,
   but net delta is the quantity a hedger actually carries; gross delta counts
   offsetting legs that need no hedge.
   *Post-hoc: raised after both estimates were seen; the argument is economic,
   not statistical, and it counts as a look. Any forward pre-registration must
   fix the primary estimate before data, and must not choose it by which
   interval is nearer zero.*
7. **Record the Greeks sidecar's session coverage as a first-class input.** 53 of
   246 SENSEX sessions and 53 of 247 NIFTY sessions carry no usable `iv`; a
   pre-registration that expects ~193 should cite where that number comes from.

---

## 10. Null register

| Test | Status | What would reopen it |
|---|---|---|
| **M1** | **Closed** — NOT DETECTED, 38 events | A window with materially more events, or a futures OI series in which a hedge that changes hands is distinguishable from one that is closed (§8: OI is a stock, so ĥ is a lower bound) |
| **M2** | **Closed** — NOT OBSERVED, β1 CI contains zero | A signed-flow series for futures, in place of the basis proxy (§8: no aggressor side exists for futures in this window) |
| **7.3 synthetic forward** | **Open** — descriptive only; forward data only, under its own pre-registration | Nothing in this run. It requires forward data and a pre-registration of its own before any verdict attaches to it |
| **Stage 1** | **Unknown** — weak design | Its own re-specification. This run neither tested it nor read its holdout (§8: nothing after 2026-03-30) |

---

*Produced 2026-11-18. Read-only run; no database write, no commit, no branch, no
push, no edit under `~/meridian-engine`. Every query through `bin/roq.sh` as
`merdian_ro` at the pinned 30 s statement timeout, never raised. Every Python
process under `ulimit -v 700000`.*
