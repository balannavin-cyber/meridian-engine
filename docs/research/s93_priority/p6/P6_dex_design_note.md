# P6 — DEX standing book: design note

| Field | Value |
|---|---|
| Session | S93, 2026-10-09 |
| Roadmap item | **P6** (S92-I post-parity priority track), `docs/research/s90_agentic/agentic_layer_roadmap_S90.md` §2.1 |
| Ruling basis | **S92-I** (P6 is item 6 of the eight-item track) · **S92-G / S92-J** (one rule, one implementation, in the database) |
| Status | **AUTHOR ONLY.** Nothing in this note has been applied to the database. The view is authored in `sql/2026-10-09_s93_v_dex_standing_book.sql` and not applied. |
| Register entry | **ENH-140**, status PROPOSED (`docs/registers/MERDIAN_Enhancement_Register.md`) |
| Not a parity layer | ADR-025 is closed (Amendment D). P6 adds no layer and amends no disposition. Display-only per S37 (GEX-as-context-not-gate). |

γ is written lower case throughout. Second-order terms are never labelled vanna or charm (L78-1).

---

## 1. What this is

Per strike, the **delta exposure** standing in the open interest: `call_dex`, `put_dex`,
`net_dex`, from `option_chain_snapshots` as `delta × oi × spot`, divided by `1e7` so the
number is in **₹ crore on the same convention as `gex_cr`** (§3).

**Grain.** `(symbol, expiry_date, strike)` — the **latest settled run per `(symbol,
expiry_date)`**, both legs, with a `leg_n` column. Consumers filter `leg_n = 1` for the
front leg.

**Settled run** = the last run at or before **15:15 IST** of the session, the ENH-126 /
`v_gex_net_gamma_river` rule reused verbatim: after 15:15 the index is frozen through the
closing auction (ADR-022), so a later run would thread an auction-frozen spot into the
book. Mid-session the settled run *is* the latest run, so the board is live; after 15:15 it
holds at the 15:10 cycle.

**Session** — the view decides this itself. It does **not** publish a date and leave the
closed-day question to the consumer: that would be two implementations of one rule
(S92-G / S92-J), and it reproduces **TD-S92-NEW-5** exactly — 2026-10-02 carried 77 frozen
chain cycles and has **no `trading_calendar` row at all**, so a consumer-side calendar gate
would have shown a holiday's frozen book as the standing book.

A date counts as a session only if **both** hold, stepping back from the symbol's newest
chain run (up to 5 dates):

1. **No explicit closure.** `trading_calendar` holds no `is_open = false` row for it. A
   *missing* row is still not a verdict (ADR-020) and does not drop a date on its own —
   which is precisely why clause 2 is needed and not redundant.
2. **The tape moved** — the house liveness rule, ADR-030 / ENH-133 §3.6:
   `count(DISTINCT spot) > 1` over `market_spot_snapshots` for that symbol and date up to
   15:15 IST. This is the one clause that catches 2026-10-02, and it subsumes ENH-133's
   `PRE_TICK` state too (0 or 1 tick cannot produce 2 distinct values).

Measured control — the check fails for the reason it names:

| date | symbol | ticks | `distinct_spot` | spot range | verdict |
|---|---|---|---|---|---|
| 2026-10-02 | NIFTY | 1 | **1** | 22,421.95 – 22,421.95 | **not a session** |
| 2026-10-02 | SENSEX | 1 | **1** | 71,909.70 – 71,909.70 | **not a session** |
| 2026-10-08 | NIFTY | 360 | 349 | 22,186.30 – 22,599.05 | session |
| 2026-10-08 | SENSEX | 360 | 359 | 71,359.97 – 72,668.00 | session |

**One deviation from the brief, with the measurement behind it.** The brief said to test
`count(DISTINCT spot) > 1` on *the chain's own* runs. The chain's `spot` is not in any index
(`idx_ocs_ts_symbol_expiry` carries `ts, symbol, expiry_date`), so that form is a heap scan:
measured **899 ms for one symbol-day** (59,100 rows, 5,554 buffer reads) against **0.578 ms**
on `market_spot_snapshots` — **1,555× cheaper**, and up to five candidate dates × two symbols
would have put the hot path over anon's binding 3 s ceiling (MV-6) on its own. The two are
the same event: the chain copies its `spot` from that feed at capture time, and on 2026-10-02
both are frozen at the identical value (NIFTY 22,421.95, SENSEX 71,909.70 — the chain reads
the same two numbers). The house rule's own binding is `market_spot_snapshots.spot` (ENH-133
§3.6), so this is also the *less* invented of the two. **The chain-side test is kept as
Section 4 check 4f** — not in the hot path, but asserted, so the claim that the two agree is
a test and not a comment (Rule 0).

`session_date` is still published, because a consumer that wants to label the board
"2026-10-08" needs it. What it no longer carries is the *decision*.

---

## 2. Measurements

Every number below was measured through `bin/roq.sh` (read-only, `merdian_ro`), bounded to
one symbol and one ts window per probe. Probe SQL is reproduced inline.

### 2(a) — Is `oi` in contracts or in quantity?

**Answer: QUANTITY — contracts × lot size. The lot is already inside `oi`, so no lot
multiplier appears anywhere in DEX or GEX.**

The test is divisibility. If `oi` were a quantity it is an exact multiple of the lot on
every strike; if it were a contract count there is no such structure. Measured on the
**2026-10-08 15:10:07 IST settled runs**, front leg, positive-OI rows only:

| symbol | n | min positive `oi` | ÷20 | ÷25 | ÷40 | ÷50 | ÷60 | ÷65 | ÷75 |
|---|---|---|---|---|---|---|---|---|---|
| SENSEX (exp 2026-10-08) | 234 | **20** | **234** | 32 | 103 | 32 | 84 | 15 | 11 |
| NIFTY (exp 2026-10-13) | 190 | **65** | 48 | 34 | 26 | 14 | 20 | **190** | 12 |

**100 % divisibility at exactly one candidate per symbol, and the minimum positive `oi`
equals that candidate.** The smallest non-zero open interest on the chain is one lot.
Lot = **20 (SENSEX)**, **65 (NIFTY)**.

*What would make this fail:* a contract count would show no 100 % divisor and a minimum of
1 or some other small integer. 234 of 234 SENSEX rows landing on multiples of 20 by chance
is ~20⁻²³⁴. The check can fail and did not.

**Independent corroboration — the `gex_cr` reconstruction.** `gex_cr` was rebuilt from the
chain with `signed_gamma_exposure()`'s formula verbatim (`compute_gamma_metrics_local.py:132`),
`gamma × oi × spot² / 1e7`, CE positive / PE negated, including the TD-NEW-2 deep-ITM guard,
and compared per strike against the stored column for the same run:

```
strikes_joined 159 | max_abs_diff 1.17e-9 Cr | n_mismatch 0
sum_gex_cr_live -8693690.6007015058714484 | recon -8693690.6007015091258540
```

So the ₹ crore convention `gex_cr` is in uses **`oi` exactly as stored, with no lot
multiplier**. DEX mirrors that convention with one power of spot instead of two.

**Second independent corroboration — `public.instruments`:**

```
symbol | exchange | lot_size | strike_step | is_active
NIFTY  | NSE      |       65 |          50 | t
SENSEX | BSE      |       20 |         100 | t
```

**65 and 20 — the divisibility measurement and the stored lot agree exactly**, by two routes
that share no input. (A first probe of this table failed on a non-existent `name` column and
briefly supported the opposite claim; the table does carry `symbol` and `lot_size`.)

**This is not a new finding, and saying so is the point.** ADR-014 §2.3 carries an
**S75 correction** that already establishes all of it: that the shipped
`signed_gamma_exposure` has **no multiplier term**, that the constants ADR-014 told readers
to "defer to" do not exist, that `public.instruments` records **NIFTY 65 / SENSEX 20** (not
the ADR's original "NIFTY 75"), and that **"Dhan reports `oi` already lot-multiplied, so
applying one would inflate every figure by the lot size"** — measured there on 2026-09-04
peak-OI strikes. P6 reproduces that conclusion independently on 2026-10-08 and inherits it;
it does not discover it. The reason to re-measure rather than cite was that getting this
wrong scales every ₹ figure in the product by 20× or 65×, and the assertion survives into
the offline test (§7, A2) so a future vendor change to contract counts fails loudly.

### 2(b) — Put delta sign as stored, and the delta null rate

**Answer: PE delta is stored NEGATIVE. `delta` is never NULL in the data — but it is
ZERO on 9–24 % of positive-OI rows, and that zero is a GAP, not a measurement.**

Sign, SENSEX settled run, front leg:

| side | rows | `delta IS NULL` | `delta < 0` | `delta > 0` | min | max |
|---|---|---|---|---|---|---|
| CE | 199 | 0 | 0 | 72 | 0.0 | 0.94685 |
| PE | 199 | 0 | 56 | 0 | **−0.99341** | 0.0 |

Read off single near-ATM rows so the sign is unambiguous (spot 71,359.97):

| strike | CE delta | PE delta |
|---|---|---|
| 71,300 | +0.58586 | −0.34158 |
| 71,400 | +0.44953 | −0.58418 |

**The null rate is zero; the gap rate is not.** Over the **whole 2026-10-08 session**, both
symbols, all legs, 55,228 positive-OI rows:

| symbol | positive-OI rows | `delta IS NULL` | `delta = 0` | of those, `gamma = 0` **and** `iv = 0` | `delta = 0` **and** `iv > 0` | `delta ≠ 0` **and** `iv = 0` | `delta = 0` **and** ITM |
|---|---|---|---|---|---|---|---|
| NIFTY | 25,389 | **0** | 2,321 (9.1 %) | **2,321 / 2,321** | **0** | **0** | 2,321 (100 %) |
| SENSEX | 29,839 | **0** | 7,053 (23.6 %) | **7,053 / 7,053** | **0** | **0** | 3,960 (56 %) |

Every zero delta arrives with a zero gamma and a zero iv, and no row carries a zero delta
beside a live iv. **The vendor drops the whole greeks block together.** So
`delta = 0 AND iv = 0` is a sound gap marker, and it degrades safely: if the vendor ever
emits a genuine zero delta with a live iv, that row is read as a true zero, which is
correct.

The gap is **ITM-concentrated and put-asymmetric.** At the SENSEX settled run the ITM
subset is 3 CE rows carrying 4,100 units against **51 PE rows carrying 7,722,860 units**.
An ITM option cannot have zero delta, so these are absent greeks, not small ones.

By OI quantity at the settled runs: SENSEX W1 **10,097,960 of 163,188,220 (6.19 %)**,
NIFTY W1 **10,223,460 of 366,687,945 (2.79 %)**.

`delta` **is** nullable in the schema (`information_schema.columns`: `is_nullable = YES`),
so the view handles NULL and the zero-gap marker together. The measured rate of the NULL
branch is zero; it is handled because the column permits it, not because it was observed.

### 2(c) — One run's row count vs `gex_strike_snapshots` for the same `run_id`

| symbol | run_id | expiry | chain rows | chain strikes | strikes with `oi > 0` | `gex_strike_snapshots` rows |
|---|---|---|---|---|---|---|
| SENSEX | `543bbd01…` | 2026-10-08 | 398 | 199 | **159** | **159** |
| NIFTY | `e7345951…` | 2026-10-13 | 472 | 236 | **108** | **108** |

The chain is symmetric (one CE and one PE row per strike), and `gex_strike_snapshots` holds
**exactly the strikes carrying OI on either side** — the writer's zero-noise drop
(`compute_gamma_metrics_local.py:1185`: drop when `oi_call = 0 AND oi_put = 0 AND gex_cr = 0`).
A DEX view at strike grain therefore carries **more** strikes than its GEX sibling unless it
applies the same drop. **It does not apply it**: a strike with no OI has `net_dex_cr = 0`,
which is a true zero, not a gap, and keeping it preserves one common strike axis with the
chain. The row-count consequence is in §6.

**Also measured, and it fixes the grain:** `run_id` is per **`(symbol, ts, expiry_date)`**,
not per cycle. At one ts the chain carries a different `run_id` for each leg —

```
SENSEX 2026-10-08 09:40:07.142356+00  exp 2026-10-08 -> 543bbd01…   exp 2026-10-15 -> e7c6f394…
NIFTY  2026-10-08 09:40:07.246037+00  exp 2026-10-13 -> e7345951…   exp 2026-10-19 -> 932afb93…
```

— and `gex_strike_snapshots` holds the **W1 leg only**. So "latest settled run per
`(symbol, expiry_date)`" is the right grain, a single `run_id` can never span legs, and
W2's run is not discoverable from the GEX table at all. This is the same shape as the
`created_at` hazard in `.claude/rules/research.md`: each `run_id` is single-expiry.

---

## 3. Sign convention, and the one place DEX must **not** copy GEX

`gex_cr` carries an **explicit** `PE → negative` flip because vendor gamma is positive on
both sides and the sign has to come from somewhere (`signed_gamma_exposure()`:
`return -base if option_type == "PE" else base`).

**Delta already carries its own sign** — measured in §2(b): PE delta is stored negative.
So:

```
call_dex_cr = delta_call × oi_call × spot / 1e7      -- delta_call > 0, so  ≥ 0
put_dex_cr  = delta_put  × oi_put  × spot / 1e7      -- delta_put  < 0, so  ≤ 0
net_dex_cr  = call_dex_cr + put_dex_cr
```

**There is no second flip.** Copying GEX's `CASE WHEN option_type = 'PE' THEN -1.0 END`
would double the negation, turn `put_dex` positive, and destroy the netting — and the
result would still look plausible, because both sides would simply be positive. This is the
single most likely transcription defect in the whole build, which is why it is written here,
stated in the view COMMENT, and **asserted** — in the Python by §7's A3, in the SQL by view
check 4c, and between the two by view check 4i, which was exercised against a deliberately
double-flipped view and caught it (§7). A comment alone would not have been a check.

### 3.1 FINDING — ADR-015's sign-convention wording is inverted against its own convention

The brief asked for "dealer-short, as GEX". That instruction cannot be followed as written,
because **GEX's convention is not dealer-short**, and the reason the confusion exists is a
defect in ADR-015's own prose.

**What the convention actually is.** ADR-015 §"Sign convention" says it is "unchanged from
ADR-014 §2.3". ADR-014 §2.3 reads:

> **Positive `gex_cr` = dampening (dealer long gamma at this strike; dealer sells rallies /
> buys dips).** … The `oi_call × gamma_call − oi_put × gamma_put` term yields positive
> (**dealer-long**) when **call writers dominate** at the strike, negative
> (**dealer-short**) when **put writers dominate**.

Calls enter with `+` and that is read as **dealer-LONG**; puts enter with `−` and that is
read as **dealer-SHORT**. So the convention is **calls dealer-long, puts dealer-short.**

**What ADR-015 says instead.** That the convention "coincide[s] under the standard
**'dealers short calls and long puts'** stylized fact."

That is the **exact inverse** on both legs. ADR-015's sentence contradicts the ADR-014 text
it claims to carry unchanged. **The convention in the code is not in doubt** —
`signed_gamma_exposure` negates PE and nothing else, and §2(a)'s reconstruction matched the
stored column to 1.17e-9 Cr — it is the *English gloss* in ADR-015 that is inverted.

Recorded as a finding, not fixed here: amending an ACCEPTED ADR is its own change, and
nothing in P6 depends on the gloss being repaired. Filed to the operator (§8 carry 7).

### 3.2 Consequence for P6: no dealer column, and no dealer claim

The two readings do not differ by a label. They differ in **size always, and in sign
conditionally**:

| reading | dealer delta |
|---|---|
| the GEX convention (calls dealer-long, puts dealer-short) | **`call_dex_cr − put_dex_cr`** — both legs long-delta, so the two *add* |
| "dealers short everything" | **`−net_dex_cr`** = `−(call_dex_cr + put_dex_cr)` — the two *cancel* |

On the 2026-10-08 NIFTY W1 settled run those are `58,697.30 − (−70,575.31) = +129,272.61`
and `−(−11,878.01) = +11,878.01` Cr — **the same sign on this leg but an order of magnitude
apart**. They differ in **sign** whenever `net_dex_cr > 0`, which **was not observed on the
four legs measured** (all four had `net_dex_cr < 0`, so both readings came out positive).
Four legs of one run says nothing about how often that holds. Picking between the two
readings is not a presentation choice; it is **P2's question** (S92-I item 2, dealer-side
check).

So, concretely:

- The view publishes **`call_dex_cr`, `put_dex_cr`, `net_dex_cr` only** — each signed by the
  option's own delta, i.e. the **open interest's** delta.
- **There is no dealer column.** No `dealer_dex_cr`, no negation, no derived "dealer" field.
- **Nothing in the view, the COMMENT, this note or the board asserts that any dealer number
  is `−net_dex_cr`** — or `call − put`, or anything else. The dealer side is **unruled**.
- A consumer that wants a dealer number must wait for P2. The columns are sufficient to
  compute either reading once it is ruled, which is the whole reason both are published
  separately rather than pre-netted.

**The board text is fixed, not advisory:** every surface rendering these columns reads

> **open-interest delta — dealer side unruled (P2)**

This replaces the earlier draft wording *"assumes dealers short — P2 pending"*, which was
withdrawn for asserting the very thing §3.1 shows is not established.

---

## 4. What the numbers can and cannot support

Two measurements bound how far this product may be read. Both are recorded as limits, and
**neither is loosened into a passing gate** (the S83 settled rule: a mis-specified gate is
recorded as mis-specified and never loosened).

### 4.1 Put–call delta parity fails in the vendor data — so a parity gate is REJECTED

For a European option on a non-dividend index, `Δ_C − Δ_P = 1` under spot moneyness
(`e^{−rT} ≈ 0.9988–1.0` over ≤ 7 days under forward moneyness). Measured over strikes with
both sides live, 2026-10-08 settled runs:

| symbol | expiry | strikes | min | max | mean | outside [0.998, 1.002] |
|---|---|---|---|---|---|---|
| NIFTY | 2026-10-13 | 71 | 0.64777 | 1.15260 | 0.874415 | **71 / 71** |
| NIFTY | 2026-10-19 | 76 | 0.70236 | 1.06345 | 0.882304 | 75 / 76 |
| SENSEX | 2026-10-08 | 32 | 0.57697 | 1.28089 | 0.816183 | **32 / 32** |
| SENSEX | 2026-10-15 | 78 | 0.62782 | 1.14607 | 0.848379 | 77 / 78 |

The vendor's CE and PE deltas at one strike are **not drawn from a consistent model/iv
pair**. A parity assertion would therefore fail on essentially every strike. It is
**recorded as mis-specified for this data and dropped**, not widened until it passes — a
band wide enough to admit 0.577 would measure the band.

### 4.2 `net_dex` magnitude is not determined to better than a factor ~3

`net_dex` is a difference of two large, nearly-cancelling terms. Measured `|net| ÷ gross`
on the 2026-10-08 settled runs: **9.2 %** (NIFTY W1), 18.0 % (NIFTY W2), **21.4 %**
(SENSEX W1), 23.7 % (SENSEX W2).

Substituting the parity-implied put delta `Δ_P' = Δ_C − 1` — an equally defensible delta set
on the same run — moves the answer:

| symbol | expiry | call_dex | put_dex (vendor) | put_dex (parity) | **net (vendor)** | **net (parity)** | ratio |
|---|---|---|---|---|---|---|---|
| NIFTY | 2026-10-13 | 58,697.30 | −70,575.31 | −93,462.59 | **−11,878.01** | **−34,765.29** | 2.93× |
| NIFTY | 2026-10-19 | 6,788.90 | −9,769.58 | −12,206.83 | −2,980.68 | −5,417.93 | 1.82× |
| SENSEX | 2026-10-08 | 53,694.19 | −82,883.29 | −127,507.14 | **−29,189.10** | **−73,812.95** | 2.53× |
| SENSEX | 2026-10-15 | 5,825.35 | −9,454.00 | −11,491.63 | −3,628.64 | −5,666.28 | 1.56× |

(₹ crore.) **The sign held on all four legs; the magnitude moved by 1.6–2.9×.**

Consequences, stated so no consumer has to infer them:

- **The magnitude is indicative, not measured.** No threshold, band or gate is built on
  `net_dex_cr`. This is the S83 cancellation shape: a gate on a net-of-nearly-cancelling
  quantity scores the cancellation, not the model.
- **The sign is not established either.** Four legs of one run is not a measurement of sign
  stability. Whether the sign is stable is P2's question.
- **The per-strike profile and the level where it balances are the robust products**, which
  is why §7's S\* is specified as a *level* and the view's content is the *shape*.

---

## 5. The Zero-Δ strike

### 5.1 The two candidates in the original P6 brief were measured and are **withdrawn**

Recorded here because both were tested, both are degenerate on real data, and the
measurement is the reason the specification changed. (Withdrawn at operator instruction,
2026-10-09, after these numbers were produced — reviewer error in the brief, not a build
failure.)

**Candidate 1 as briefed — cumulative `net_dex` sign change, interpolated: 0 crossings on
all four legs**, under both the vendor delta set *and* the parity-implied set
(`n_cross_vendor = n_cross_parity = 0`, 4 of 4 legs).

The curve, read directly (NIFTY exp 2026-10-13, spot 22,187.9, ₹ crore):

| strike | `oi_call` | `oi_put` | `delta_call` | `delta_put` | `call_dex` | `put_dex` | `net_dex` | **`cum_net_dex`** |
|---|---|---|---|---|---|---|---|---|
| 17,150 | 0 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **0.0** |
| 19,650 | 0 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **0.0** |
| 21,150 | 0 | 392,535 | 0.62828 | −0.02159 | 0.0 | −18.8 | −18.8 | **−642.9** |
| 22,000 | 1,029,210 | 11,137,165 | 0.69455 | −0.26098 | 1,586.1 | −6,449.1 | −4,863.0 | **−14,972.1** |
| 22,300 | 7,539,805 | 6,360,770 | 0.42002 | −0.60351 | 7,026.6 | −8,517.5 | −1,490.8 | **−24,812.8** |
| 22,500 | 14,459,965 | 3,380,520 | 0.22714 | −0.86610 | 7,287.5 | −6,496.3 | +791.1 | **−20,760.5** |
| 23,150 | 2,495,090 | 34,515 | 0.02131 | 0.0 *(gap)* | 118.0 | 0.0 | +118.0 | **−13,069.8** |
| 28,650 | 0 | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | **−11,878.0** |

The cumulative starts at 0, runs **monotonically negative** through the body to a minimum of
**−24,813 Cr** near 22,300, recovers as calls take over above spot, and ends at the leg
total **−11,878 Cr**. It never returns to zero, so there is no interior crossing to
interpolate.

**The cause is in the table.** Below spot there is effectively **no ITM-call open
interest** — `oi_call = 0` at every strike from 17,150 to 21,150 — while OTM puts carry
0.4–11 M units at delta −0.02 to −0.26. The cumulative is driven negative before any call
contribution exists, and nothing later brings it back. This is a property of a put-heavy
index book, not a defect.

**Candidate 2 as briefed — nearest strike to zero `net_dex`: lands on the lowest strike of
the chain**, 17,150 (NIFTY) and 64,900 (SENSEX), identically under both delta sets. There
`net_dex` is exactly 0 because there is **no OI at all**. The definition finds the emptiest
strike, not a balance point. Restricting it to strikes with OI and a live delta on both
sides moves the answer to the ATM region, but it then selects on a per-strike residual of
~10²–10³ Cr against per-strike grosses of ~10⁴ Cr — the §4.2 cancellation problem at
strike resolution.

Both are withdrawn. Neither is implemented.

### 5.2 Replacement: S\*, the **re-priced** zero-Δ level — ONE candidate, pending operator ruling

**Definition.** `S*` is the spot level at which the re-priced book's delta exposure is zero:

> `Σ_i Δ_i(S*) × OI_i = 0`

where `Δ_i(S)` is the **Black-Scholes** delta of leg `i` evaluated at spot `S`, holding each
leg's own implied volatility fixed. This is the γ flip of ENH-131 / `v_gex_repriced_flip`
with gamma replaced by delta, and it is specified to **reuse that code path**, not to
re-derive one.

**Why this survives where 5.1's candidates did not.** S\* reads delta from a *repricing*
rather than from the vendor's per-strike delta column, so (i) it is immune to the delta gap
that flattened the ITM region in 5.1 — the greeks are computed from `iv`, and the legs with
no `iv` are dropped *and counted* rather than silently zeroed; and (ii) it is a **level**,
not a magnitude, and §4.2 showed the level-like products are the robust ones.

**The L3 code path to reuse**, `sql/2026-09-25_s83_v_gex_repriced_flip.sql`, CTE by CTE —
every one of these is taken unchanged:

| CTE | What it fixes | Reuse |
|---|---|---|
| `symbols` | S72 skip scan; symbols derived, never a literal list | unchanged |
| `latest` | ADR-021 per-symbol latest-ts index seek; **never `created_at`** | unchanged |
| `front` | front expiry = `min(expiry_date)` in that snapshot (W1 only) | unchanged |
| `hdr` | `T` = exact seconds from `ts` to **15:30 IST on the front expiry**, over a 365-day year (Gate 5 convention (b)); `dte = front_expiry − (ts AT TIME ZONE 'Asia/Kolkata')::date` | unchanged |
| `legs` | **R1 frozen leg set at the observed spot**: `oi > 0`, vendor `gamma` non-null and `≠ 0`, `iv > 0`, and the TD-NEW-2 deep-ITM guard — **not re-applied per sweep point** | unchanged (§5.3) |
| `futwin`/`futfront`/`rrows`/`rstats` | `r_sess` = **session-median futures carry**, no look-ahead (09:20 IST → `ts` inclusive), front-month *future*, `p10`/`p90` published; **< 6 rows is `UNMEASURABLE_R`, never a default** | unchanged |
| `atm`/`atmiv` | house ATM grid (step 50 NIFTY / 100 SENSEX), `NULLIF(iv, 0)` so a zero abstains; `sigma_1d = spot × atm_iv/100 × sqrt(1/365)` | unchanged |
| `evalset` | `dte > 0 AND t_years > 0 AND n_r_rows ≥ 6` — **dte 0 is refused, never floored** (S62) | unchanged |
| `grid` | **201 points, ±10 % of spot, 0.1 % steps** — the same strike window | unchanged |
| `adj`/`crossings` | linear interpolation between adjacent grid points | unchanged |
| `counted`/`nearest` | crossing **nearest spot**; `n_cross_full_grid` and `n_cross_within_2sigma` published so far-tail instability stays visible | unchanged |
| `status` | precedence `SKIPPED_EXPIRY` → `UNMEASURABLE_R` → `NO_CROSSING` → `OK`; the level is NULL on all but `OK` | unchanged |

**Exactly two changes**, and no others:

1. **The greek.** `Δ_call = Φ(d1)`, `Δ_put = Φ(d1) − 1`, with `d1` **identical** to L3's:
   `d1 = (ln(S/K) + (r + σ²/2)·T) / (σ·√T)`.
   Φ is available exactly — `erf`/`erfc` are present on this server (**PostgreSQL 17.6**,
   verified in `pg_proc`), so

   ```
   Phi(x) = 0.5 * erfc(-x / sqrt(2.0))
   ```

   checked against textbook values before use: `Φ(0) = 0.5`, `Φ(1) = 0.841344746068543`,
   `Φ(1.96) = 0.97500210485178`, `Φ(−3) = 0.0013498980316301` — all exact to 15 digits.
   L3 needed only the normal **PDF**, which is elementary; S\* needs the **CDF**, and this
   is where it comes from. No rational approximation is used and none is needed.

2. **The exponent on S, and no sign flip.** Each leg contributes
   `Δ_i(S) × oi_i × S / 1e7` — **one** power of S, against GEX's two — and carries
   **no `PE → −1` factor**, because `Φ(d1) − 1` is already negative (§3). L3's
   `CASE WHEN l.option_type = 'PE' THEN -1.0 ELSE 1.0 END` is **deleted, not copied.**

**`S*` is NOT implemented in the view in this session.** It is specified here and marked
**pending operator ruling**. What the ruling decides: whether S\* ships as its own view
(`v_dex_repriced_zero`, the L3 shape, grain `(symbol)`) or as columns on the standing book;
and whether L3's five-gate record has to be re-run for the delta curve or is inherited.
Until then the standing book publishes the per-strike and per-leg content only, and carries
no zero-Δ column at all — an absent column rather than a provisional one.

### 5.3 One L3 inheritance that was checked rather than assumed

L3's `legs` filter drops a leg when vendor `gamma` is null or zero. On a *delta* curve that
test is not obviously right — it exists to reject spurious vendor gamma, and a leg can have
a sound `iv` and a well-defined BS delta while its vendor gamma rounds to zero. Measured,
2026-10-08 settled runs:

| symbol | expiry | positive-OI legs | dropped: no `iv` | dropped: no `gamma` | **`iv` live but `gamma = 0`** | their OI | their OI share | their \|delta\| |
|---|---|---|---|---|---|---|---|---|
| NIFTY | 2026-10-13 | 190 | 34 | 34 | **0** | — | 0.00 % | — |
| NIFTY | 2026-10-19 | 163 | 11 | 11 | **0** | — | 0.00 % | — |
| SENSEX | 2026-10-08 | 234 | 117 | 160 | **43** | 17,226,860 | 10.56 % | 0.00028 – 0.00134 |
| SENSEX | 2026-10-15 | 189 | 31 | 40 | **9** | 50,440 | 0.56 % | 0.00025 – 0.00458 |

The affected legs are **deep-OTM, not deep-ITM**: 10.56 % of SENSEX W1's open interest, at
`|delta| ≤ 0.00134`. Their total DEX contribution is of order
`0.00134 × 17.2 M × 71,360 / 1e7 ≈ 164 Cr` against a gross of ~136,600 Cr — **≲ 0.12 %**.
So **L3's leg set is inherited unchanged**, and the hypothesis that it would cost real
delta exposure is recorded as *tested and wrong*.

One observation owed to the operator, not a finding against L3: L3's COMMENT records *"iv
of zero removed none on any arm"* for its five gate arms (2026-09-18 … 09-24). On
**2026-10-08** the `iv ≤ 0` exclusion removes **117 of 234** SENSEX W1 positive-OI legs
(6.19 % of OI) and 34 of 190 NIFTY W1. The L3 statement is **era-specific, not wrong** —
nothing here re-opens ENH-131 — but a zero-iv exclusion that was immaterial on the gate
arms is material now, and S\* must publish the dropped-leg count and dropped OI beside the
level rather than inherit the assumption that it is zero.

---

## 6. The view

`sql/2026-10-09_s93_v_dex_standing_book.sql` — **one view, authored, not applied.**

**No client recompute is possible, by construction** (S92-G / S92-J). Every quantity the
board draws is a column: per-strike `call_dex_cr` / `put_dex_cr` / `net_dex_cr`, the per-leg
totals `leg_call_dex_cr` / `leg_put_dex_cr` / `leg_net_dex_cr`, and the gap columns beside
them. The client filters and draws; it never multiplies, divides or sums.

**There is no `cum_net_dex_cr`.** An earlier draft published a running sum. Its only
consumer was the cumulative zero-Δ candidate, which §5.1 measured degenerate and which is
withdrawn — and as written the column walked past gap strikes as if they were zero while
carrying no flag that it had done so, which is the thing §6's gap handling exists to
prevent. It is **removed**, not kept "in case". If S\* or a successor needs a cumulative, it
is added then, with its own gap disclosure.

**Gap handling — NULL is a gap, never a zero.** A side whose delta is absent while it
carries OI publishes **NULL**, not 0; a side with no OI publishes 0, which is a true zero.
`net_dex_cr` is NULL when either side is NULL. The un-deltaed OI rides along in
`oi_call_no_delta` / `oi_put_no_delta`, so the defect travels inside the artefact it
degrades.

**One consequence that had to be designed around.** Because `net_dex_cr` is NULL on
one-sided-gap strikes, `sum(net_dex_cr)` ≠ `sum(call_dex_cr) + sum(put_dex_cr)` — measured
on the 2026-10-09 13:20 IST run, NIFTY W1: `103,096.29 − 107,932.77 = −4,836.48` against a
`sum(net_dex_cr)` of `−3,446.47`, a **1,390.01 Cr** discrepancy that is exactly the good
half of the one-sided-gap strikes. A consumer adding up the per-strike column would silently
drop it. **That is why the leg totals are columns**: they are window sums over each side's
measured contribution, so the client is never in a position to compute the wrong one.

**But the leg totals are the MEASURED PART of the leg, not a complete total**, and the note
says so in the same breath because the earlier draft called them "additive and complete" —
which they are not. They cover only the strikes where a delta existed. `leg_gap_oi_qty` is
the OI they do **not** cover (and `leg_oi_qty` the leg's total OI), so the pair is read
together or not at all. On the SENSEX W1 settled run that uncovered OI is 6.19 % of the
leg's open interest, concentrated in ITM puts — the exposure most likely to matter.

**Row count.** Measured live on the 2026-10-09 13:20 IST settled runs: NIFTY 239 + 235,
SENSEX 198 + 190 = **862 rows** across both symbols and both legs — under PostgREST's
1,000-row cap (rule 15) but not by much, and SENSEX chains lengthen. Consumers filter
`leg_n = 1` (437 rows) and page with `.range()` otherwise. Stated so a truncation is never
discovered as missing strikes.

**Cost.** The final body was costed through `roq.sh` verbatim, `EXPLAIN (ANALYZE, BUFFERS)`,
862 rows out:

| | measured | against |
|---|---|---|
| **cold** (first run after a re-plan; `market_spot_snapshots` and the back-steps read from disk) | **1,322.7 / 1,445.0 / 1,934.3 ms** (three cold runs) | anon's 3 s `statement_timeout` (MV-6) |
| **warm** (nine runs) | **81.6 – 103.4 ms** | — |

**Both are stated because both are real.** The warm figure is what a 5-minute-cadence board
read normally sees; the cold figure is what the first read after a cache eviction sees, and
it is the cold one that has to clear the ceiling. **It clears it by 1.55× at the worst cold
run measured, not the ~2× an earlier draft of this note claimed** — and the cold figure is
the variable one, 1.3 s to 1.9 s across three runs, so that margin is the thing to watch as
the chain grows, never the warm number. Quoting 81 ms alone would have been the more
impressive and the less true number. If a cold run is ever seen above ~2.4 s, the liveness
clause is the first thing to move off the hot path — it is the only part that touches a
second relation.

Node detail (warm): the liveness CTE is **4.8 ms** across 10 candidate dates (0.44 ms each),
the 10 backward date seeks total 0.26 ms, the legs lateral runs at `loops = 2`, and the
per-leg strike seek at `loops = 4`, 431 rows each.

**The first draft of the leg-discovery CTE was a plain join and ran 8,095 ms**: the planner
hashed the session CTE and scanned 3.2 M index entries, removing 3,113,638 rows by join
filter. Rewriting it as a `CROSS JOIN LATERAL` made the ts window a parameterised index
range and took it to 61 ms. **This is the ADR-021 shape and it was found by measuring, not
by reading** — the plain-join form would have shipped, worked at today's table size, and
crossed the ceiling silently later.

**No dealer column** (§3.2), **no zero-Δ column** (§5.2), no history, no second-order terms.
Each omission is listed in the file's closing block with its reason, so an absence is never
read as an oversight.

**ACL.** `security_invoker = false`, `anon = r` through the view, `authenticated` revoked
(TD-S92-NEW-4), `merdian_ro = r` — ADR-031 D6, with the REVOKE first because Supabase
default privileges hand new objects ALL (CASE-2026-09-22). Noted and **not** relied on:
`option_chain_snapshots` itself already carries `anon = rm` (measured: `relacl` =
`{postgres=arwdDxtm,anon=rm,authenticated=rm,service_role=arwdDxtm,merdian_ro=r}`, RLS off).
That is R01-F8 / TD-S81-NEW-2's business, not this file's; this view neither widens it nor
depends on it, and the "one implementation" property here is a *design* guarantee, not an
access-control one.

---

## 7. Offline test

`tests/test_dex_recompute.py` — recomputes DEX in Python from the frozen golden day
`tests/golden/2026-10-01_SENSEX`, **independently of the SQL**, and asserts against values
that do not come from running the view.

**Written now; NOT RUN.** Authored at 2026-10-09 ~13:00 IST, inside the rule-23 window
(08:30–15:40 IST). It runs only after **15:40 IST**, under
`( ulimit -v 700000; … )`. The fixture is 31,914 chain rows over 81 cycles (`counts.csv`),
which is exactly the memory profile rule 23 exists for.

**What it tests, and what it cannot.** It tests **this Python recompute**. It cannot test
the view — there is no database offline — and the distinction is load-bearing, because an
assertion that passes offline is not evidence about the SQL:

- the SQL's scale and sign are tested by **view check 4c** (an independent in-SQL recompute
  with different algebra);
- the SQL's agreement with this recompute, strike by strike, is **view check 4i** — and
  *that* is where a doubled PE flip in the SQL would be caught;
- the SQL's session-liveness clause is tested **live, by Section 4 against 2026-10-02**.

**Where the expected values come from.** Not from the view, and not from the recompute
itself:

| # | Assertion | Expected value's source | What makes it fail |
|---|---|---|---|
| **A1** | `gex_cr` rebuilt in Python from the fixture's chain equals the fixture's stored `gex_cr` per strike, **joined by `run_id`**, max abs diff < 1e-6 Cr | `inputs/gex_strike.csv.gz` — written by **production**, not by this test | the harness's units, the `/1e7` scaling, the CE/PE flip or the deep-ITM guard being wrong. **This is the load-bearing check**: DEX shares every one of those with GEX, so a scale or sign error shows here first. Joined by `run_id` because that is the key §2(c) measured the two relations share — equal `ts` between them is not an established fact |
| **A2** | every positive `oi` is an exact multiple of 20 (SENSEX) | §2(a): `public.instruments.lot_size`, and ADR-014 §2.3's S75 correction — **not** from the fixture | a vendor switch from quantity to contracts — which would silently rescale every ₹ figure by 20× |
| **A3** *(recompute only)* | `put_dex_cr ≤ 0` and `call_dex_cr ≥ 0` on every strike where the side has OI and a live delta, **and the negative case is non-vacuous** | §2(b), measured sign | the §3 double-flip **in the Python**. A copied `PE → −1` makes `put_dex` positive and this fails on the first put strike. The **view's** sign is 4c / 4i |
| **A4** *(recompute only)* | a side with OI and no delta is `None`, never `0.0`; and `oi_*_no_delta` accounts for exactly that OI, cross-checked against an **independent row-level count** over the same run | the gap definition | a `COALESCE(…, 0)` creeping into **the Python**, which would assert a measurement never made. The **view's** is 4d (`n_zero_where_gap_c/_p`) |
| **A6** | `delta` is read as a gap only when `iv = 0`; no fixture row has `delta = 0 AND iv > 0 AND oi > 0` | §2(b), measured across 55,228 rows | the vendor emitting a true zero delta with a live iv, which would mean the marker needs revisiting — a **real** finding, not a test bug |
| **A7** | the settled-run selector picks the last cycle at or before 15:15 IST, and that cycle's ts is a cycle the fixture holds | ENH-126 rule + `queries/ocs.sql` window | an off-by-one in the ceiling, or a `created_at` ordering slipping in |
| **A8** | **the session selector's liveness clause, run over the fixture's own `market_spot_snapshots` rows — the same relation the view reads.** The live fixture day is **accepted**; a synthetic copy with one frozen spot is **rejected**; row and cycle counts in the window are identical across the two | §1's liveness rule (ADR-030 / ENH-133 §3.6) and the measured 2026-10-02 control | the liveness clause being dropped, inverted, or written as a row/cycle count — all three of which 2026-10-02 passes. **The synthetic frozen copy is what makes this a test**: the live fixture alone would pass a selector with no liveness clause at all. **Clause 1 (explicit calendar closure) is NOT tested here** — the fixture carries no `trading_calendar` rows, so clause 1 is live-only (Section 4) |
| **A9** | the fixture's own `dte`, and whether it exercises S\*'s dte-0 refusal | the fixture + the S62 refusal rule | — (reports which path the fixture does and does not reach) |

**A5 was written and then deleted, which is worth recording.** It asserted that
`sum(net_dex_cr) + the one-sided-gap residue == leg_call_dex_cr + leg_put_dex_cr`. That is
an **algebraic identity of the lines immediately above it** — both sides are sums over the
same two `COALESCE`d quantities — so it could not fail for the reason it named (Rule 0,
clauses 1 and 3). No external expected value for the leg totals exists offline: the fixture
carries *gamma*, not delta, so there is nothing production-written to anchor a delta total
against. The leg-total property is therefore asserted by **view check 4i** alone (the view
against this CSV, two independent implementations), and the numbers are **printed here as
observations, never asserted** — the test prints them on an `obs` line so they are visible
without pretending to be checks.

**An earlier draft of this paragraph also cited view check 4d "(additivity, in SQL)" — the
same error, one layer down.** 4d's `leg_total_mismatch` compares
`sum(COALESCE(call,0) + COALESCE(put,0))` against
`sum(COALESCE(call,0)) + sum(COALESCE(put,0))`: equal by linearity of `SUM` for *any*
definition of the dex arms, so it is the same window sum split in two. Its
`gap_oi_unaccounted` is a window sum compared with the sum of its own rows. Both were
relabelled **"ARITHMETIC SANITY ONLY — cannot fail for a modelling defect"** and removed
from 4d's `FAILS IF` and `EXPECTED`; `n_zero_where_gap_c/_p` remains the real check there,
because it reads the `oi_*_no_delta` CASE against the `*_dex_cr` CASE and a `COALESCE(…, 0)`
in the dex arms makes it fire. **Rule 0 caught the same shape twice in one session, once in
the Python and once in the SQL** — which is the argument for stating what would make a check
fail *before* writing it, not after.

**Output goes outside the frozen fixture.** `tests/golden/2026-10-01_SENSEX/` is frozen
(R2.1, `MANIFEST.sha256`) and the test **never writes into it** — it verifies that manifest
on the way in. The expected table is written to
`docs/research/s93_priority/p6/expected/dex_standing_book_1001_SENSEX.csv`, and view check
4i points there.

**What this test does not do.** It cannot run the SQL, so it does not compare Python against
the view. **Check 4i does, and it is built, not owed** — `--compare --view <csv> --chain
<csv>` recomputes from an exported chain read and diffs the view strike by strike. **The
expected values are computed by the recompute and never read back off the view** (the S81
rule: an expected value handed to a verifier is computed from the artefact, never recalled).

4i was **exercised on synthetic inputs** so that it is known to fail for each reason it
names, rather than assumed to:

| arm | result |
|---|---|
| agreeing view and recompute | **PASS** — 2 strikes, max abs diff 0.000e+00 Cr |
| a **doubled PE sign flip** in the view | **CAUGHT** — `put_dex_cr` off by 1.440e+03 Cr, and `net_dex_cr` with it |
| a **gap published as 0** instead of NULL | **CAUGHT** — NULL-ness differs on `put_dex_cr` and `net_dex_cr` |
| the two exports covering **different `run_id`s** | **CAUGHT** — reported as the S81 false-alarm shape (re-export together), not as a defect |

The `run_id` column is in both exports for that last reason: a latest-run-scoped view
compared against a chain read taken at another moment is exactly the S81 pairing error, and
nothing but the run key detects it.

The fixture carries **W1 only** (`expiry_date` is `2026-10-01` on every row) at **dte 0**, so
it exercises one leg and cannot exercise multi-leg ranking. It *can* and does assert that a
dte-0 run would be refused by S\*'s `evalset` — the negative case.

**Not wired into `tests/run_offline.sh` yet.** Adding an unrun test to the single-command
suite would put a test nobody has seen green in front of the next person who runs it.
Wiring is owed after the first post-15:40 run passes.

---

## 8. Carries

| # | Owed | To whom |
|---|---|---|
| 1 | **Operator ruling on S\*** (§5.2): own view vs columns; L3 gate record inherited or re-run for the delta curve | operator |
| 2 | Run the offline test after 15:40 IST under `( ulimit -v 700000; … )`, then wire it into `run_offline.sh` | next session |
| 3 | Apply the view (Section 1→2→3) and run Section 4; it has not touched the database | next session |
| 4 | **P2 settles the dealer side** (§3.2) and §4.2's sign question. Until it returns there is no dealer column and the board carries *"open-interest delta — dealer side unruled (P2)"* | P2, S92-I item 2 |
| 5 | Observation for the operator: L3's *"iv of zero removed none on any arm"* is era-specific (§5.3). Not a defect; not re-opened here | operator |
| 6 | The §4.1 parity failure is a property of the vendor's greeks, measured on one day. Whether it holds across the window is unmeasured | P4 (Greeks evidence) |
| 7 | **ADR-015's sign-convention gloss is inverted against ADR-014 §2.3, which it claims to carry unchanged** (§3.1). The code and the stored column are not in doubt. Amending an ACCEPTED ADR is its own change and is not done here | operator |
| 8 | **OPEN RULING — vendor delta or an in-house Black-Scholes delta?** The book as authored reads the vendor's `delta` column. §4.1 measured put–call parity on it at a mean of **0.816–0.882** against a theoretical ≈1, so an in-house BS delta from each leg's own `iv` (the §5.2 repricer's `Φ(d1)` / `Φ(d1) − 1`, which the S\* spec needs anyway) is a live alternative for the **book** as well as the level. The two differ by the §4.2 factor of 1.6–2.9× on `net_dex`. **Not changed in this session** — the view ships on the vendor column pending the ruling, and switching it **reuses the S\* repricer inputs (T, `r_sess`, the dte-0 refusal) and is not a one-line change** | operator |

---

## 9. Measurement provenance

Every figure above came from `bin/roq.sh` (read-only `merdian_ro`, 30 s `statement_timeout`),
bounded per probe to one symbol and a 60-second or one-day ts window. Probe files are in the
session scratchpad and are not committed; each probe's SQL is reproduced in the section that
uses it, so the numbers are reproducible without them.

**Two runs carry most of the numbers**, and they are different runs — labelled at every use:

- **2026-10-08 15:10:07 IST settled runs** (`543bbd01…` SENSEX exp 10-08, `e7345951…` NIFTY
  exp 10-13) — §2, §4, §5.1, §5.3.
- **2026-10-09 13:20:06 IST live settled runs** — §6's row counts, the leg roll-up and the
  78.7 ms cost.

Nothing in this note was applied to the database. No `.env` was read. No fixture suite was
run.
