# ADR-024: GEX zone anchor — what the PIN and ACCEL construction walks outward from

## Status

**PROPOSED — 2026-09-15 (Session 79). Decision RESERVED pending §4.**

Reserved at S75 (`297ae68`) and undrafted since. This draft files the question, enumerates
the blast radius, and pre-registers the measurement that must precede any ruling. **It does
not choose an anchor.** The decision lands as Amendment A once §4 returns.

**Why the decision is reserved rather than taken here.** CLAUDE.md Rule 10 requires an ADR
before its code. It does not require a ruling before its evidence. The anchor question has
a measurable component and a design component, and the design component is unanswerable
until the measurable one is settled — §3 sets out why. Taking the ruling now would be
D.32's shape: a structural prediction substituted for a measurement.

---

## Context

### The premise that was never tested

`adr009_prereg_gex_zone_utility_2026-09-07.md` asserts at §1 and §3, verbatim, that **the
maximum-positive-GEX strike sits near spot**, and names it as the reason the study exists.

Measured at S75 over every `gamma_metrics` row carrying `max_gamma_strike` — n = 9,820,
paged, client-side comparison against each row's own `spot`:

| symbol | above spot | below spot | equal |
|---|---:|---:|---:|
| NIFTY | **4,883 / 4,928 — 99.1 %** | 0.9 % | **0** |
| SENSEX | **4,861 / 4,892 — 99.4 %** | 0.6 % | **0** |

Source: Assumption Register **§D.33.8**.

**The premise is false in the direction that matters**, and every zone built by walking
outward from that strike inherits the offset. The pre-registration's own justification does
not hold.

### Why this is not yet a defect

**A systematic offset is not automatically an error.** There is a mechanical hypothesis that
would make the anchor *correct and merely misnamed* — §3.1. Until that hypothesis is tested,
"the anchor is wrong" and "the anchor's documentation is wrong" are indistinguishable, and
they have opposite remedies.

This is the whole reason §4 precedes any decision.

### What has already been answered, and what has not

Three measurements bear on this and none of them settles it:

| | finding | bearing |
|---|---|---|
| **S74** | **PIN answered NO** — NIFTY holdout mean −0.1996, 95 % CI [−0.2998, −0.0801], 19 of 21 sessions negative, SENSEX reproducing the sign. All seven preconditions passed; equivalence gate at zero rows on both arms, so the reconstruction was the shipped walk | A verdict on the construction **as anchored today** |
| **S75 §D.33.4** | That verdict **does not transfer to the shipped zones.** The null matches donors to ±0.5 % of the recipient's open while the real zone's own reference spot is unconstrained — **26.1 % of NIFTY sessions fall outside that band** | The NO stands as *"PIN adds nothing over spot-matched donors"*, not as *"shipped pin zones are useless"* |
| **S74** | **ACCEL not answered.** N = 11 after exclusions against ADR-009's own N<30 *"meaningless to split"* tier; CI lower bound +0.013 carried by one of eleven points; SENSEX contradicting; a ~50 % exclusion that is **outcome-dependent** — a design defect present in the pre-registration **before** measurement, recorded as such rather than reframed after | Unanswered, and its instrument needs repair before re-running |

**Nothing shipped on either.** The state is: zone utility is genuinely open, both attempts
broke on their own instruments rather than on the market, and the anchor both attempts
assumed has now been measured and is not what either assumed.

**Data is not the constraint.** §D.33.5 refuted that directly — per-strike GEX is
COMPUTABLE NOW on **299 of 356 NIFTY and 299 of 355 SENSEX** trading days.

---

## 1. Blast radius — the consumers bound by this decision

Enumerated before the question is argued, per the standing discipline that a finding whose
consumers were never enumerated is a hypothesis rather than a finding.

| consumer | what it does with the anchor | what changes if the anchor changes |
|---|---|---|
| **`compute_max_gamma_strike`** — `compute_gamma_metrics_local.py:758` | Produces the anchor. Positive-only argmax, hardened at **S41 P0.a FIX-1** | It *is* the decision's implementation |
| **`v_gex_strike_pin_zone`** | Walks outward from the argmax; τ-weighted concentration band, `tau_pin` from `merdian_parameters` (`pin.tau.{symbol}`) per ADR-016 | Every PIN band's position and width |
| **`compute_pin_risk_score`** — `compute_gamma_metrics_local.py:835` | Takes spot-proximity **to that strike** as an input | A scalar that moves with the anchor by construction |
| **`v_gex_strike_accel_zone`** | Sibling view, same walk shape, same τ pattern | Recorded as in-scope; its coupling to the argmax is **owed verification from source** (§5) |
| **Marketview + Pine overlay** | Render PIN and ACCEL as bands/boxes; display-only per the S37 *GEX-is-context-not-gate* ruling and `flip_audit` §PART C | Presentation only. **No signal or gate reads `gex_cr`** — the blast radius stops at display, which is why this ADR is safe to take slowly |

**A fifth consumer worth naming because it is not code:** the ADR-009 study template. Both
arms of the S74 study are anchored here. Re-running PIN or ACCEL before this ADR closes
would re-measure the same unvalidated construction.

---

## 2. What the anchor currently is, as shipped

`signed_gamma_exposure` (`compute_gamma_metrics_local.py:114–133`) computes
`base = gamma * oi * (spot ** 2) / 1e7`, **CE positive, PE negated** — ADR-015's sign
convention, where positive `gex_cr` means dampening. Two guards sit in front of it:

- **The deep-ITM guard** (TD-NEW-2 Part A, S27):
  `if strike > 0 and abs(strike - spot) / spot > 0.05: if abs(gamma) > 5e-5: return 0.0`.
  **Both constants are bare literals and the function takes no `symbol` argument**
  (TD-S75-NEW-2). The moneyness leg is scale-free; the gamma leg is not, because gamma
  scales inversely with the underlying's level. Spot ~24,300 against ~77,000 is a ratio of
  ~3.2, and the source comment justifies `5e-5` as *"~5× typical ATM gamma"* — a calibration
  that can hold for at most one of the two symbols.
- **The zero-gamma branch** — `gamma_raw == 0.0` returns 0 by a separate path.

The argmax is then taken **positive-only** (S41 P0.a FIX-1).

**And the filter is not applied uniformly across the row.** TD-S75-NEW-1: `build_gss_rows`
iterates `option_rows_raw` — pre-filter, deliberately — so `oi_call`/`oi_put` and
`gamma_call`/`gamma_put` carry full-chain values while `gex_cr` carries filtered ones. **The
three columns disagree about which rows count.** Guard-firing signature, `count=exact` on
`gex_strike_snapshots`:

| month | NIFTY | SENSEX |
|---|---:|---:|
| June 2026 | 1,394 | **15,720** |
| July 2026 | 3,082 | **18,688** |
| August 2026 | 906 | **11,529** |
| 2026-09-01..08 | 230 | **787** |

Roughly an order of magnitude more on SENSEX in every month — TD-S75-NEW-2's asymmetry,
measured.

**ADR-014 §2.5's falsification rule cannot see any of this.** It checks `sum(gex_cr)` across
per-strike rows against `net_gex` in `gamma_metrics`; both sides come from
`signed_gamma_exposure` and carry the filter identically, so it passes by construction. **It
is a self-consistency test, not an independent one** — Rule 0 clause 1 in a new place.

---

## 3. The question, split into its measurable and design halves

### 3.1 The mechanical hypothesis — and it would make the anchor correct

**H1: the offset is produced by the positive-only selection, not by a defect.**

`gex_cr` is positive for calls and negative for puts. A positive-only argmax therefore
selects **the largest call-gamma concentration**, and on Indian index weeklies call OI stacks
above spot. If H1 holds, the anchor is not offset — **it is the max call-gamma strike,
correctly computed and wrongly described**, and the remedy is a rename plus an amendment to
the pre-registration template, not a change to three consumers.

**H2: the deep-ITM guard moves the argmax, asymmetrically by symbol.** The guard zeroes
strikes beyond 5 % moneyness carrying `|γ| > 5e-5`, which removes candidates *far* from spot
and should pull the argmax *toward* it. That is the opposite direction to the observed
offset — so H2 cannot be the primary cause, but it can shape the distribution and it fires
~10× more often on SENSEX. **Any cross-symbol reading of the anchor inherits that
asymmetry**, which is precisely the axis ADR-009's replication design is supposed to hold
fixed.

**H3: the offset is not stable.** ADR-017 Principle 6's own worked example has NIFTY max γ
at **+0.15 %** from spot at 0h DTE and SENSEX at **+0.6 %** at 24h DTE on the same day. If
the offset varies systematically with DTE, spot level or regime, then the zone width — which
walks outward from the anchor under a fixed τ — is measuring something different on
different days while presenting identically.

### 3.2 The design half, which cannot be settled before §4

Four candidate anchors, recorded so §4's protocol is not written toward one of them:

| candidate | argument | disqualifier, if any |
|---|---|---|
| **Max positive `gex_cr`** (current) | Dampening concentration is the mechanism PIN claims | Answers a call-side question while presenting as a spot-relative one, if H1 holds |
| **Max `abs(gex_cr)`** | Sign-agnostic; picks up put walls below spot that the current anchor cannot see | Mixes two mechanisms with opposite hedging behaviour into one point |
| **Zero-gamma flip** | The theoretically motivated boundary, and Hedgewall's own construction | **Unsound as shipped** — `flip_audit_2026-09-08.md`: the value gates nothing, the two branches return levels on opposite sides of spot on the same chain, median 5-min step 10 pts NIFTY / 41 SENSEX against maxima 1,330 / 7,300. Unavailable until the L3 rebuild lands |
| **Spot** | Makes the zone a spot-relative band, which is how it is read | Discards the positioning information entirely; the zone becomes a volatility band |

---

## 4. Measurement — pre-registered under ADR-009 Phase 1

**Written before any query is run.** Per the pre-registration doctrine: the value is
entirely in its being written before the answer is known, and an amendment made after the
first result is a new study, not a revision of this one.

### 4.1 Cohort and bounds

**Ceiling is a timestamp, never a row count** — `gex_strike_snapshots` was measured at
1,412,989 and again at 1,417,090 rows within hours on 2026-09-05, so a row-count bound has
an invisible expiry date.

```
Floor:   ts >= TIMESTAMPTZ '2026-05-25 00:00:00+00'   -- ENH-80 writer's first day
Ceiling: ts  <  the run date, stated in the result document
```

Symbol is a **stratum, not an N multiplier** — per S74 Pre-commitment 2, and with added
force here because TD-S75-NEW-2 means the two arms are filtered at different effective
strictness.

**`gex_strike_snapshots.ts` lags `created_at` by exactly one 5-minute cycle** (TD-S78-NEW-8).
**Provenance reads `ts`; freshness reads `created_at`.** This study is a provenance question
and uses `ts`. Stated because the same confusion produced three wrong readings in one
session.

### 4.2 The three tests, with success criteria fixed in advance

**T1 — does positive-only selection explain the offset? (tests H1)**

Recompute, per `(symbol, run_id)`, three argmaxes from the stored per-strike rows: over
positive `gex_cr` (reproducing the shipped anchor), over `abs(gex_cr)`, and over the
negative leg alone. Report each one's signed distance from that row's own `spot` as a
distribution, not a maximum — **§D.33.7: a maximum over a heterogeneous window is not a
central tendency.**

> **Criterion, fixed now:** H1 is **supported** if the negative-leg argmax sits *below* spot
> at a rate comparable to the positive-leg argmax sitting above it — i.e. the offset is a
> property of the sign selected, not of the chain. H1 is **refuted** if both legs sit above
> spot.

**T2 — does the deep-ITM guard move the anchor? (tests H2)**

Recompute the positive-only argmax with and without the guard, on identical rows, per symbol.
Report the fraction of runs where the anchor strike changes, and the signed distance of the
change.

> **Criterion:** the guard is **anchor-neutral** if it changes the strike on < 5 % of runs in
> both symbols. If it exceeds that in either, **TD-S75-NEW-2 is promoted from S2 and must be
> fixed before any ruling in §3.2**, because the two arms are then not comparable.

**T3 — is the offset stable? (tests H3)**

The offset in strike steps, conditioned on DTE (0 / 1–2 / ≥3, the S33 ADR-011 structure) and
on spot decile.

> **Criterion:** the offset is **stable** if the interquartile range within each DTE bucket
> is ≤ 1 strike step. If it is not, the fixed-τ walk is measuring different widths on
> different days and **that is a finding about the zone construction independent of the
> anchor ruling.**

### 4.3 Preconditions — all must pass before any statistic is computed

1. **Uniform strike grid within a run.** Assert it; a non-uniform run fails loudly rather
   than being silently mis-stepped. (S74 P4's rule, same table.)
2. **Reconstruction equivalence.** The recomputed positive-only argmax must reproduce
   `gamma_metrics.max_gamma_strike` exactly on the latest run, both symbols. **This is the
   gate that makes T1–T3 statements about the shipped construction rather than about a
   lookalike.** It is not a proof over all historical runs — the views only ever expose the
   latest run — and that limit is stated rather than assumed away.
3. **No unresolved probe counts as a negative.** Every absence must be a real empty list
   (Data Inventory method rule 3), never a `57014` or a planner floor — §D.33.9 and §D.33.10
   are both instances of exactly this in this table family.
4. **`count=exact` is unavailable on the largest relations.** Where it times out, offset
   bisection gives an exact integer in ~18 cheap requests.

### 4.4 What a result does and does not authorise

A finding here authorises **the §3.2 ruling and nothing else.** It does not authorise wiring
GEX into `build_trade_signal_local.py` — that remains settled by the S37
GEX-as-context-not-gate decision, and any gate would additionally require its own N ≥ 30
live-runtime-cohort validation under the ADR-009 cohort-prior-gate-hazard sub-rule.

**This ADR measures a construction's correctness, not a signal's edge.** The edge question
is the re-run of PIN and ACCEL, and it is downstream of this and of the ADR-009 template
amendment that §D.33.4 requires.

---

## 5. Owed verification — claims in this draft that came from registers, not source

Stated explicitly so the next reader does not resolve them by guessing, and so this ADR does
not become an instance of the class it exists to correct.

| claim | source of the claim | how to settle it |
|---|---|---|
| `compute_max_gamma_strike` at `:758` is a positive-only argmax | Decision Index ADR-024 reserved row | Read the function |
| `compute_pin_risk_score` at `:835` takes spot-proximity to that strike | same | Read the function |
| `v_gex_strike_pin_zone` walks outward from the argmax | ADR-015 / ENH-81 register entries | Read `sql/` and `s72_gex_view_fix.sql` |
| `v_gex_strike_accel_zone` shares the walk shape | inferred from sibling naming | **Read it. Inferring a coupling from a filename is the failure this project keeps filing** |
| Line numbers throughout | registers, and they drift | `git grep -n` at the run commit; cite the commit |

---

## 6. Consequences

**Operational.** No production behaviour changes on this ADR. Every consumer is display-only
(`flip_audit` §PART C), so the construction can be measured and re-ruled without a live
exposure window.

**Architectural.** The anchor becomes a named, evidenced decision with an enumerated blast
radius rather than an implementation detail that three consumers inherited. ADR-015's
minimum-sufficient-statistic doctrine argues that the anchor is a read-layer derivation, not
a stored column — **in scope for Amendment A, out of scope for this draft.**

**On the ADR-009 template.** §D.33.4's defect — a null matched on the recipient's open while
the real zone's reference spot is unconstrained — is a defect **in the pre-registration
template, not only in the S74 study.** It must be amended before PIN or ACCEL is re-run.
Recorded here because this ADR is the reason that re-run is waiting.

**Costs.** §4 is a read-only recomputation over `gex_strike_snapshots` — no writer, no
migration, no backfill. Bounded by the request budget, not by compute.

**Risks.** The measurement returns "the anchor is fine, the documentation was wrong" (H1
supported), and the effort reads retrospectively as overhead. **That outcome is the cheapest
one available and it closes a premise that two studies have now assumed.** A null is
publishable here for the same reason the S74 null was.

---

## 7. Cross-references

`MERDIAN_Assumption_Register.md` **§D.33.8** (the measurement that forces this ADR), §D.33.4
(the null-template defect), §D.33.2 (the asymmetry hypothesis this one must not repeat),
§D.33.5 (power is not the constraint), §D.33.7 (maxima are not central tendencies) ·
**TD-S75-NEW-1** (filter applied non-uniformly across the row), **TD-S75-NEW-2** (symbol-blind
threshold), TD-S75-NEW-3 (`net_gex` normalisation, scalar, non-binding here), **TD-S78-NEW-8**
(`ts` versus `created_at`) · **ADR-015** §F2 and the sign convention · **ADR-014** §2.5 (the
falsification rule that cannot see §2) · **ADR-016** (the `merdian_parameters` pattern any
symbol-relative threshold would use) · **ADR-017** Principle 6 (the DTE-dependent salience
example that motivates T3) · **ADR-009** Phase 1 (the reserved Decision-Index row carrying
the holdout policy; **there is no ADR-009 file** — the reserved row and
`adr009_prereg_gex_zone_utility_2026-09-07.md` are the governing artefacts) · **ADR-021**
Amendment 1 §A1.6 (τ was decorative until 2026-09-05) · `flip_audit_2026-09-08.md` (why the
flip is unavailable as a candidate anchor) · **S41 P0.a FIX-1** (the prior hardening of the
argmax, which is why Rule 10 applies).

---

*Drafted 2026-09-15, Session 79. **Nothing in §4 has been measured.** The decision is
reserved and lands as Amendment A. Per §D.36.1, every figure above is cited to the register
that measured it; §5 lists the claims that are not yet measured at all.*
# ADR-024 — Amendment A (v3): the anchor offset is arithmetic, and most of §4 was answered by asking a different question

**Date:** 2026-09-15 (Session 79) · **Status:** ACCEPTED
**Supersedes:** Amendment A v1 (withdrawn — its central ruling was refuted from source) and
Amendment A v2 (drafted, never committed — three of its findings were overtaken within the
same session).
**Appended as a new section** per the ADR-004 §15 precedent.

Resolves the parent's *"Decision RESERVED pending §4."*

---

## A0. What changed between v2 and v3, and why v2 is not the record

v2 was drafted, presented, and superseded before it reached the repo. Three of its positions
did not survive measurements taken later the same session. **They are listed first so no
reader reconstructs v2's version from a partial quote:**

| v2 said | v3 says | what changed it |
|---|---|---|
| H4 (OI-imbalance) is a **hypothesis, untested** | **H4 is measured and supported** at full window | §A2 |
| T3's DTE-offset finding **survives as measurement** | **Withdrawn.** It was a unit error | §A4 |
| The deep-ITM guard zeroes ~35 % of SENSEX rows | **~5.2 %.** The other ~30 % is a different finding entirely | §A3 |

v2 also lacked the independent falsification check (§A6), which is the one result in this
amendment that ADR-014 §2.5 structurally cannot produce.

**C1 is resolved.** `pg_get_viewdef` was run. The live `v_gex_strike_pin_zone` and
`v_gex_strike_accel_zone` are the S72 parameterised definition — `get_parameter_num` in the
peak CTE, the bounded `CROSS JOIN LATERAL`, not S69's hardcoded `0.3` or unbounded
`DISTINCT ON`. Everything below is therefore about the running system, not about a file.

---

## A1. The anchor ruling: correct, and carrying less information than its name implies

**`WHERE gex_cr > 0` does not select call strikes.** Refuted from source at `434a7fb`:
`:1153` keys `per_strike` on **strike alone**; `:1161` does `bucket["gex_cr"] += gex_contrib`,
accumulating CE and PE rows at the same strike into one bucket; `:132-133` negates PE. A
stored `gex_cr` is **CE_contrib − PE_contrib at that strike** — a per-strike **net**.

So the argmax selects the strike of greatest **net long dealer gamma**.

**Ruling: the construction is correct. The name and the documentation are wrong, and
§D.33.8 is a tautology rather than a defect.** See §A2 for why.

**Remedy, and it is the whole remedy:**

1. Describe it as the **max net-long-gamma strike**. Never *"near spot"* — the
   pre-registration's §1/§3 premise.
2. **No column rename.** Five registers and a live frontend bundle reference
   `max_gamma_strike`; the cost exceeds the benefit of a better label.
3. Record in ADR-015 that the positive-only argmax is a **net-sign** selection, and that
   `v_gex_strike_accel_zone`'s trough is its mirror.
4. **No consumer changes.**

---

## A2. T1 and H4 — the 99 % is arithmetic

### T1, as pre-registered

Both legs recomputed per `(symbol, run_id)`, `ts >= 2026-05-25`:

| leg | symbol | n_runs | above spot | p10 | median | p90 |
|---|---|---:|---:|---:|---:|---:|
| peak (+) | NIFTY | 5,591 | **99.2 %** | 0.178 | **+0.549** | 1.103 |
| trough (−) | NIFTY | 5,591 | 1.3 % | −1.186 | **−0.412** | −0.133 |
| peak (+) | SENSEX | 5,540 | **99.1 %** | 0.196 | **+0.543** | 1.226 |
| trough (−) | SENSEX | 5,540 | 2.2 % | −1.045 | **−0.483** | −0.110 |

`n_runs` identical between legs on both symbols — every run holds both a positive and a
negative strike, so neither leg carries survivorship. **Criterion met: the offset is a
property of the sign selected.**

### H4, measured — and this is the finding

**H4:** at a given strike call and put gamma are equal under put-call parity, so
`gex_cr ≈ γ_c·OI_c − γ_p·OI_p` and the sign is driven by **OI imbalance**. OTM options carry
the open interest, and which side is OTM flips at spot.

Cross-tabulated over the full window, 1,515,008 rows:

| | at/below spot | above spot |
|---|---|---|
| **NIFTY call-OI-heavy** | 1,053 / 306,015 = **0.34 %** | 286,770 / 288,341 = **99.5 %** |
| **SENSEX call-OI-heavy** | 1,917 / 491,558 = **0.39 %** | 425,302 / 429,094 = **99.1 %** |
| NIFTY `gex_cr > 0` | 0.78 % | 90.3 % |
| SENSEX `gex_cr > 0` | 1.6 % | 66.5 % |

**H4 supported.** Call-OI-heaviness is separated by spot at 0.3–0.4 % versus 99 %+, on both
symbols, across 1.5 M rows.

**Consequence: a positive-only argmax cannot select a strike below spot, because almost no
strike below spot has positive `gex_cr`.** *"The max positive-GEX strike sits above spot"* is
not a finding about positioning. It is a restatement of *"OTM calls are above spot."*

**§D.33.8 is reclassified: a tautology.** Measured, real, and empty of positioning content.

### The residual, which is where any information actually lives

**H4 is directional, not absolute.** Below spot, where positive `gex_cr` is rare, it is
**mostly** produced by gamma overcoming OI imbalance:

| | positive `gex_cr` | of which put-OI-heavy |
|---|---:|---:|
| NIFTY, below spot | 2,383 | **1,501 = 63 %** |
| SENSEX, below spot | 7,644 | **5,919 = 77 %** |
| NIFTY, above spot | 260,435 | 326 = 0.13 % |
| SENSEX, above spot | 285,334 | 467 = 0.16 % |

Above spot, OI imbalance determines the sign outright. Below it, it does not — and those
**~8,300 strikes** are IV skew doing real work, which is exactly what ADR-015's separate
`gamma_call` / `gamma_put` columns were preserved to capture (S37 measured them differing
43 % at ATM). **They are invisible to a positive-only argmax because they never win the
max.** Recorded as the one place the current construct discards information a sign-agnostic
one would keep.

---

## A3. T2 — H2 dead, and a larger finding underneath it

**H2 is dead by §A2's table.** If the symbol-blind `5e-5` guard shaped the anchor, two
symbols at spot levels ~3.2× apart could not land on medians of **+0.543 and +0.549**.

**And the guard is far smaller than v2 claimed.** `gex_cr = 0` has **two** paths — the
deep-ITM guard (which requires `|gamma| > 5e-5`, i.e. gamma present and large) and a
zero-gamma branch. Splitting them on the zeroed rows:

| | zeroed | **guard (gamma present)** | **no gamma at all** |
|---|---:|---:|---:|
| NIFTY | 64,183 = 10.8 % | ≤ 8,940 → **1.5 %** | ≥ 55,243 → **9.3 %** |
| SENSEX | 323,550 = 35.1 % | ≤ 47,878 → **5.2 %** | ≥ 275,672 → **29.9 %** |

The guard bounds match TD-S75-NEW-1's monthly counts almost exactly — SENSEX Jun–Sep sums to
46,724 against a bound of 47,878. **S75's counts were right; v2's 35 % conflated two zero
paths and inflated the guard ~7×.**

**The real finding is underneath: SENSEX has no gamma at all on ~30 % of its strikes.** That
is a coverage fact, not a filtering one, and it is recorded nowhere. **File separately.**

**TD-S75-NEW-2 stays S2** — a cross-symbol replication defect, not an anchor question.

---

## A4. T3 — WITHDRAWN. It was a unit error.

v2 reported the anchor's distance from spot varying ~2.8× across DTE and called five of six
cells a criterion failure. **That finding does not survive the correct unit.**

Hedgewall's reading order, step 3, verbatim: *"Pin, flip and the two walls, each read as a
distance from spot divided by sigma. Points on their own are not a distance."*

Recomputed with `σ = spot × atm_iv/100 × sqrt(GREATEST(dte,1)/252)`:

| symbol | DTE | median % | **median σ** | IQR σ |
|---|---|---:|---:|---:|
| NIFTY | 0 | 0.265 | **0.359** | 0.222 |
| NIFTY | 1–2 | 0.464 | **0.587** | 0.380 |
| NIFTY | 3+ | 0.748 | **0.500** | 0.374 |
| SENSEX | 0 | 0.260 | **0.342** | 0.197 |
| SENSEX | 1–2 | 0.566 | **0.586** | 0.383 |
| SENSEX | 3+ | 0.676 | **0.410** | 0.412 |

In percent the spread is 2.8×, monotone. **In sigma it is 1.6× and non-monotone**, and the
two symbols agree to three decimals at 1–2 DTE (0.587 / 0.586) and two at 0 DTE
(0.359 / 0.342) — at spot levels 3.2× apart. The IQRs are 0.20–0.41σ, comfortably inside
half an expected move.

**The dispersion v2 called a defect was percent-scale noise.** The anchor sits around half an
expected move above spot, fairly stably.

**Consequences:**

- **T3's finding is withdrawn**, and with it the τ-per-DTE-bucket remedy — now withdrawn for
  a third and sufficient reason. (It was already refuted twice: band width grows with DTE
  because τ is a *relative* threshold behaving correctly, and containment does not improve
  with wider bands.)
- **ADR-017 Principle 6 is right about the bug and wrong about the cause.** Its worked
  example (NIFTY +0.15 % vs SENSEX +0.6 % *"on the same day"*) reads as a symbol difference.
  It is a **DTE** difference measured on a day when the two symbols were at different DTEs.
  **P6 amendment owed**; the salience function should key on DTE and distance-in-sigma, not
  on symbol.
- **The 3+ bucket dipping below 1–2 on both symbols** is real and consistent, but small
  (1.2–1.4×) and plausibly the √t assumption rather than the anchor. Not chased.

**Method note worth keeping:** a board read in percent will keep manufacturing findings of
this shape. S75 said this before the sigma work confirmed it.

---

## A5. Containment — S74's finding, rediscovered at a different granularity

**This was not new.** `capture_s74.md:103`, also in `CURRENT.md`, `CURRENT_history.md` and
`CLAUDE.md:980`:

> Spot is inside the pin zone at the moment the zone is computed on only **15/67 NIFTY
> (22 %)** and **13/67 SENSEX**; mean distance **0.70 % / 0.79 %**.

And `:105` — in **16 of 21** NIFTY holdout sessions price never entered the buffered zone at
all, *"bimodal, not shifted."* And `:107`, the conclusion: *"The containment statistic is
measuring whether the zone **landed on** spot more than whether spot was **held**."*

**The S79 recomputation (4.6 / 4.2 / 11.5 % by DTE) disagrees 2–5× and is NOT reconciled.**
Two candidates, neither verified: **denominator** (S74 counts sessions, S79 counts ~75 runs
per session) and **buffer** (S74 uses ±step/2 per prereg line 174; S79 did not buffer).
**Until settled, neither figure may be quoted as "the containment rate."**

**What is new:** the DTE stratification, which exists nowhere on disk. **No result artefact
for the S74 study exists at all** — `docs/research/` holds only the pre-registration, and
every S74 figure lives in session notes, which is why A5's reconciliation cannot be done
without re-running.

### And the whole framing was wrong

Hedgewall's own guide, sample readout: spot 56,748, **PIN 57,500 — +1.32 % from spot**.
Their pin sits **further out than MERDIAN's**. A pin above spot is what the reference
implementation ships.

**What contains spot is the corridor — floor to ceiling, put wall to call wall.** Their
readout: *"Price sits between the put wall and the call wall."* MERDIAN's pin and accel zones
**are** their call wall and put wall; the missing object was the corridor, which is now built
as ENH-120 `v_gex_strike_walls`.

---

## A6. The independent falsification check — passes, and ADR-014 §2.5 cannot do it

`net_gex` recomputed from the **unfiltered** stored columns —
`(γ_c·OI_c − γ_p·OI_p) × spot² / 1e7` — against the shipped `sum(gex_cr)`:

| symbol | unfiltered | filtered | guard contribution |
|---|---:|---:|---:|
| NIFTY | 6,068,140.58 | 6,069,054.98 | **−914.41 (0.015 %)** |
| SENSEX | 482,929.82 | 482,929.82 | **0.00** |

**This is a genuinely independent check** — it does not pass through
`signed_gamma_exposure`, so it could have failed. It did not. The writer's arithmetic is
sound, and on this run the guard removes essentially nothing.

**ADR-014 §2.5 remains structurally blind.** It compares `sum(gex_cr)` to `net_gex`; both
sides come from `signed_gamma_exposure` and carry the filter identically, so it passes by
construction — Rule 0 clause 1. **Independently rediscovered three times** (TD-S75-NEW-1,
this ADR's §2, the S79 source audit). Standing note, not a fourth cross-reference. The
recomputation above is the check §2.5 should have been.

---

## A7. `pin_risk_score`'s proximity component is ABSENT, not depressed

`compute_gamma_metrics_local.py:835-912`:
`spot_proximity_factor = max(0.0, 1.0 − (|spot − max_gamma_strike| / strike_step) / 3.0)` —
linear decay to **zero at 3 strike-steps**, weight 0.30 at `:902`, renormalised over
*available* components at `:899-911`.

| offset | NIFTY (step 50, spot ≈ 24,000) | SENSEX (step 100, spot ≈ 81,000) |
|---|---|---|
| 0.25 % | 1.2 steps → 0.60 | 2.0 steps → 0.32 |
| 0.50 % | 2.4 steps → 0.20 | 4.1 steps → **0.00** |
| 0.75 % | 3.6 steps → **0.00** | 6.1 steps → **0.00** |

**At S74's measured mean distances (0.70 % / 0.79 %) the factor is 0 on both symbols.** The
component drops at `:901` and the score **renormalises over the remaining 0.70 weight** — so
`pin_risk_score` silently changes basis between cycles depending on where the anchor happens
to sit. Given §A2, that is most cycles.

**First consequence in this ADR touching a scalar consumers read**, rather than a band they
draw. File as a TD.

---

## A8. What this amendment rules

**Accepts:** the anchor ruling (§A1) — correct construction, wrong name, no consumer change;
H4 as measured (§A2); the independent falsification result (§A6).

**Withdraws:** v1's call-side ruling and rename; v2's τ-per-DTE remedy; v2's T3 finding
(§A4); v2's 35 % guard figure (§A3).

**Opens, as separate filings:** SENSEX's ~30 % no-gamma coverage gap (§A3); the A5
containment reconciliation; `pin_risk_score`'s basis shift (§A7); ADR-017 P6's amendment
(§A4).

**Authorises nothing in production.** Every consumer is display-only. This measures a
construction, not an edge — unchanged from the parent §4.4, and any gate would additionally
require N ≥ 30 live-runtime-cohort validation.

---

## A9. Self-corrections, S79

Filed rather than absorbed, and four are one reflex.

1. **The call-side ruling** (§A1) — a sign convention asserted without reading the
   accumulation two lines away.
2. **The containment rediscovery** (§A5) — `capture_s74.md` was in project knowledge all
   session and was not read.
3. **The 35 % guard figure** (§A3) — two zero-paths conflated, inflating it ~7×.
4. **A single-run symbol asymmetry** — NIFTY +0.70 % / SENSEX +1.45 % read as a symbol
   difference; over 5,540+ runs the medians are +0.549 / +0.543. §D.33.7, and the same
   reflex as §D.33.2.
5. **An instrument cap read as a result** — `limit: 4000` returns 1,000 (Rule 15); *"runs
   sampled: 2"* was the cap. Settled by a scalar aggregate: `runs_with_multiple_expiries = 0`.
6. **Measurements requested that S75 had already taken** — live column lists, recorded as
   `columns_live_s75` in `merdian_reference.json` v52.
7. **"Verbatim from the view"** said of a change script read from project knowledge. Rule 3:
   the DB is truth.
8. **A check called "the single most valuable"** that could not fail — given C3 and a
   matching peak, walk ⊆ recomputation is deductive.

**1, 2, 6 and 7 are one pattern: reasoning from the archive when the source was available.**

---

## A10. Owed

1. **§A5's reconciliation** — re-run S79's containment per *session* and *with* the ±step/2
   buffer, against S74's 15/67.
2. **File §A3's coverage gap, §A7, and ADR-017 P6's amendment** as TDs.
3. **`infer_expiry_date:245-247`** returns `expiries[0]` from an unordered PostgREST result
   rather than `min()`. Wrong by construction; correct today only because
   `runs_with_multiple_expiries = 0`. S3.
4. **ADR-015 note** per §A1 item 3.

---

*Amended 2026-09-15, Session 79. v1 withdrawn, v2 superseded before commit. Every figure is
cited to the measurement that produced it; §A9 lists what this session got wrong before §A8
lists what it decided.*
