# ENH-98 / L7 + L8 — design spec, S89 (2026-10-03)

> **Bound spec for the ADR-025 parity layers L7 (vanna) and L8 (charm).**
> Authored, **not applied**. The DDL is `sql/2026-10-03_s89_v_gex_greeks_l2.sql`; application
> lands **Monday 2026-10-05 ≥ 16:00 IST with ENH-133**. Shape follows
> `ENH-133_schema_spec_S89.md` — this file is the input to the apply, not a record of one.
>
> **PROVISIONAL — T1 pending 2026-10-07.** Nothing here authorises a build decision; it
> specifies what gets applied *if* the operator applies it, and what kills it if T1 refuses.
>
> Every figure below was measured this session against the live database as `merdian_ro`,
> read-only. Probes: `scratch/s89_l78/p{1..8}*.sql`; plans: `scratch/s89_l78/explain_plans.txt`.

---

## §0 The stamp, and the pre-committed kill

ENH-98's own go/no-go, **T1**, is **UNDECIDED** — not passed, not refused (S86 pair verdict;
A3 counted and did not refuse, A4 was a NO-TEST at 1.18×). The deciding arm is the **SENSEX
dte-1 cycle, Wed 2026-10-07 10:15:59 IST**, run under the **TD-S86-NEW-9 ruling of
2026-10-03** (the ≥ 3×SE precondition gates offset/`r_eff` only; the gamma reading counts on
ATM rows ≥ 10; prospective from 10-07; A4's UNDECIDED stands).

Consequently:

- Both views are **DISPLAY ONLY** and every surface rendering them carries the badge
  **"PROVISIONAL — T1 pending 10-07"**.
- **Pre-committed kill, agreed before the measurement so a refusal cannot be renegotiated
  into a caveat:** if 10-07 refuses T1 — `exact/365` median `gamma_relerr` **> 0.10 at BOTH
  ATM and NEAR** — `v_gex_greeks_l2_strike` and `v_gex_greeks_l2_net` are **DROPped** and
  L7/L8 return to their prior disposition.
- An **UNDECIDED** T1 on 10-07 (the arm fails its own gamma precondition, ATM rows < 10) is
  **not** a refusal and **not** a pass. It extends the stamp; it does not fire the kill and
  does not clear it. Stated now so the third possible outcome is not adjudicated after the
  fact.

---

## §1 Grain

Two views, one grain each — the house convention, so neither view's rows mean two things.

| View | Grain | Rows at a live cycle |
|---|---|---|
| `v_gex_greeks_l2_strike` | `(symbol, expiry_date, strike)` at the latest `option_chain_snapshots` `ts` | 59–109 strikes per leg, measured |
| `v_gex_greeks_l2_net` | `(symbol, expiry_date)` | **4** — 2 symbols × 2 expiry legs |

**Both captured expiry legs, not the front only.** ENH-131 keeps W1 because it publishes one
level per symbol; L78-3 requires W2 to compute as normal on expiry day, so L7/L8 carry both.

**The monthlies L78-3 also names cannot appear, and that is a capture limit, not a filter.**
Measured: `n_expiry = 2` on every session 2026-09-28 → 10-02, both symbols. Capture stage 1
holds exactly W1 and W2. The ENH-98 S84 block already records "capture depth — REOPENED" as
an **open operator decision** gated behind the stage-2 redefinition (TD-S81-NEW-14); until
that lands, L78-3's monthly leg is **BLOCKED-ON-DATA** and these views say nothing about it.

**Run scoping is ENH-131's verbatim:** recursive skip-scan over symbols, then one index seek
per symbol through `idx_ocs_ts_symbol_expiry` — never `max(ts) GROUP BY symbol`, never
`created_at` (S81 `89bc83e`: `created_at` hands back W2).

---

## §2 Methodology — ANALYTIC Black-Scholes, explicitly **not** finite-differenced

**This is the first thing to state because the obvious alternative is wrong.** ENH-131 already
sweeps TotalGEX over a 201-point grid, so differencing that grid looks like the cheap route.
It is not available: **the ENH-131 grid sweeps SPOT at fixed σ and fixed T.** It carries no σ
axis and no t axis, so **neither ∂/∂σ nor ∂/∂t can be read off it at all** — a difference taken
along it answers a different question. Every quantity here is the **closed form, evaluated once
at the observed spot**.

With q = 0:

```
d1     = (ln(S/K) + (r + σ²/2)·T) / (σ√T)
d2     = d1 − σ√T
n(d1)  = exp(−d1²/2) / √(2π)
Γ      = n(d1) / (S·σ·√T)
dd1/dT = (r + σ²/2)/(σ√T) − d1/(2T)

∂Δ/∂σ = −n(d1)·d2 / σ                     [per 1.00 σ]
∂Δ/∂t = −n(d1) · dd1/dT                   [per year]
∂Γ/∂σ = Γ·(d1·d2 − 1) / σ                 [per 1.00 σ]
∂Γ/∂t = Γ·(d1·dd1/dT + 1/(2T))            [per year]
```

**Four constructs, because L78-1 ruled BOTH.** The textbook delta-derivatives *and* the parity
target's ∂gamma constructs, each under a distinct name, **neither labelled plain "vanna" or
"charm"**:

| Column | Is | L78-1 family |
|---|---|---|
| `delta_drift_iv_cr_per_volpt` | ∂Δ/∂σ | textbook |
| `delta_drift_time_cr_per_day` | ∂Δ/∂t | textbook |
| `gex_drift_iv_cr_per_volpt` | ∂Γ/∂σ | the ∂gamma construct |
| `gex_drift_time_cr_per_day` | ∂Γ/∂t | the ∂gamma construct |

**`q = 0` means call and put carry the SAME second-order greek at a strike.** The CE/PE
distinction enters **only** through the dealer sign and through `oi`. That is why the sign
convention below is load-bearing rather than inherited, and why V6 tests it.

### Source columns

All from `option_chain_snapshots` at the scoped `ts`: `strike`, `option_type`, `iv`, `oi`,
`gamma`, `spot`, `expiry_date`. Plus `index_futures_snapshots.{ts, expiry_date,
futures_price, spot_price}` for `r`. **No new input is required** — the ENH-131 repricer
publishes only `(symbol)`-grain scalars (18 columns, one row per symbol: `flip`,
`flip_sigma`, `r_sess`, `atm_iv`, …) and **exposes no per-strike repriced greek**, so L7/L8
cannot select from it and re-implement its leg machinery instead.

### Inputs are ENH-131's, deliberately

Same leg set — `oi > 0`, vendor `gamma` non-zero, `iv > 0`, and the **TD-NEW-2 deep-ITM
guard** (drop when distance from spot > 5 % **and** |vendor gamma| > 5e-5). Same `r`. Same `T`.
Same Crore convention. Same latest-`ts` scoping. **L3 and L7/L8 are then reconcilable by
construction:** a disagreement between them is a disagreement about the derivative, never
about which chain was priced.

### The sign convention, stated

**PE legs are NEGATED**, exactly as `signed_gamma_exposure()` negates them, carrying the
standard dealer assumption (long calls, short puts) into the second-order layer. This is **not**
a flip applied to an already-signed delta: with q = 0 the second-order greeks are identical for
call and put, so **the negation is the whole of the dealer-side assumption and nothing else**.
V6 asserts the call/put equality the claim rests on — CLAUDE.md Rule 0 clause 4: a parity claim
between two branches is asserted by a test, never by a comment.

---

## §3 Units — stated explicitly, because an implicit unit is the defect

TD-NEW-3 cost this system a 100× error; Rule 14 cost it another. So:

```
_cr_per_volpt = <per-contract derivative> / 100 · oi · S   / 1e7
_cr_per_day   = <per-contract derivative> / 365 · oi · S   / 1e7     (delta pair)
_cr_per_day   = <per-contract derivative> / 365 · oi · S²  / 1e7     (gamma pair)
```

- **`/100`** — per **+1 implied-vol POINT**, i.e. per +0.01 of σ, **not** per 1.00.
- **`/365`** — per **one CALENDAR day** of time passing. 365 and not 252: calendar decay
  including weekends, per **operator ruling L78-3**, and consistent with the `exact/365` T
  convention used throughout.
- **`/1e7`** — the Crore convention (TD-NEW-3).
- **The delta pair scales by `oi·S`** → δ-notional ₹ Cr, which is what **L78-1** asked for.
  **The gamma pair scales by `oi·S²`** — one power of S higher, which is
  `signed_gamma_exposure()`'s own convention, so the ∂gamma pair sits in the same unit as
  `gex_cr` per unit of σ / time.

So in words, for the board: *"₹ Cr of dealer delta-notional gained per +1 implied-vol point"*
and *"₹ Cr of dealer delta-notional gained per calendar day"*; the ∂gamma pair reads the same
sentence with "GEX" in place of "delta-notional".

### Why `exact/365`, and it is the load-bearing choice — unlike `r`

**Measured, and it is the opposite of the L3 result.**

**`r` barely matters.** Sweeping r over `{0, 0.037, 0.065, 0.10, 0.12}` — wider than any
dispersion this system has measured, and spanning both the ENH-98 `r_eff` band (3.57–3.81 %)
and the live SENSEX session-median carry (~10 %):

| arm | net ∂Δ/∂σ spread | net ∂Δ/∂t spread |
|---|---|---|
| SENSEX dte 1 | 3314 → 3298, **0.50 %** | −23 703 → −23 755, **0.22 %** |
| SENSEX dte 2 | 1119 → 1149, 2.7 % | −1683 → −1833, 8.9 % |
| NIFTY dte 5 | 4854 → 4951, **2.0 %** | −6047 → −6508, **7.6 %** |

The r convention that failed ENH-131's Gates 3 and 4 is **not** the sensitive axis here.
(Separately measured and worth recording: `r_sess` is **stable** between the 10:15 cycle and
the full session — NIFTY 0.0609 (n=18) vs 0.0598 (n=140); SENSEX 0.1063 vs 0.1016 — so
L78-3's 10:15 cadence does not degrade `r`. The ~10 % **SENSEX level** against ENH-98's
3.57–3.81 % `r_eff` is a real disagreement and is **recorded, not reconciled** — filed as
**TD-S89-NEW-3**; on the sensitivity above it does not move these numbers.)

**`T` does matter.** Same rows, three conventions:

| arm | `exact/365` | `dte/365` | `dte/252` | spread |
|---|---|---|---|---|
| SENSEX dte 2, net ∂Δ/∂t | −1760 | −1150 | −2746 | **2.4×** |
| SENSEX dte 1, net ∂Δ/∂t | −23 718 | −25 688 | −22 046 | 17 % |
| NIFTY dte 5, net ∂Δ/∂σ | 4917 | 4806 | 5737 | 19 % |

`exact/365` is chosen because **it is the convention T1 is written on**. S86 observation (b)
found `dte/252` roughly 10× better on gamma at dte 1 and **recorded it without changing T1**;
that observation is deliberately **not acted on here**, because changing a convention after
seeing which arm it favours is the fitting a pre-registration exists to prevent. **If 10-07
re-opens the convention, these views change with T1 and not before.**

---

## §4 Gate semantics — the cutoff-aware materialized distinct-spot flag

`is_trading_session = (count(DISTINCT spot) > 1)` over this symbol's rows **from 00:00 IST on
the `ts` date through `ts` INCLUSIVE**. Three properties, each deliberate:

1. **Cutoff-aware.** The window ends at `ts`, not at end-of-day, so the flag carries **no
   look-ahead** — the same discipline as the `futwin` window.
2. **Write-and-flag**, per ENH-133 D-3 clause 3. The row is **published either way** and the
   consumer filters; the flag is not a suppression.
3. **`AS MATERIALIZED`, joined on `(symbol, ts)`** — and the keyword is load-bearing, not
   stylistic.

**Why this gate and not a row count.** 2026-10-02 (Gandhi Jayanti) is the case: **83 distinct
`ts` and 79 680 NIFTY rows**, so it passes a row count *and* a distinct-`ts` count
(TD-S89-NEW-1) and fails only on `distinct_spot = 1`. Measured at the live latest `ts`, the
net view returns four rows with `is_trading_session = f` — i.e. **the default read of these
views today is a frozen holiday**, correctly flagged rather than silently published.

**The gate shape was earned by an EXPLAIN, and the first two drafts breached ADR-021.**
Measured on a two-construct precursor of this body — same scoping, same legs, same data:

| gate shape | execution |
|---|---|
| plain CTE grouped off a day window | **11 040 ms** (Seq Scan, 2 519 992 rows) |
| correlated subquery, un-materialized | **26 424 ms** (490 loops) |
| `AS MATERIALIZED`, joined on `(symbol, ts)` | **164 ms** |

The first two are over the PostgREST 8 s ceiling — **the exact ADR-021 failure, reproduced
inside this file's own first draft.** Removing the keyword reverts a sub-second view to a 26 s
one that returns HTTP 500 and reads to a consumer as *no data*.

---

## §5 dte-0 handling — SKIPPED, never floored, and on this layer that is measured

ENH-131 skips dte 0 on S62's authority (expiry-day gamma numerically unreconstructible).
**L7/L8 skip it on their own evidence as well**, because the time-derivatives are *worse* than
gamma: both ∂Δ/∂t and ∂Γ/∂t carry `1/(2T)` and both diverge as T → 0.

Measured at the 10:15 cycle across four sessions:

| arm | net ∂Δ/∂t (₹ Cr/day) | vs dte 2 |
|---|---|---|
| SENSEX dte 2 | −1 820 | — |
| SENSEX dte 1 | −23 744 | **13×** |
| SENSEX dte 0 | **−156 855** | **86×** |
| SENSEX dte 0, net ∂Γ/∂t | **−4 951 550** | — |

A *"per calendar day"* rate published with **0.222 days** left to run is not a small number
badly estimated; it is an **instantaneous derivative extrapolated over a horizon that does not
exist**.

**An independent control agrees.** Reconstructing BS delta from this view's own `d1` and
comparing with the **vendor** delta inside the `[0.05, 0.95]` band:

| dte | 12 | 9 | 8 | 7 | 5 | 2 | 1 | **0** |
|---|---|---|---|---|---|---|---|---|
| median \|BS − vendor\| | 0.0164 | 0.0038 | 0.0031 | 0.0038 | 0.0103 | 0.0088 | 0.0185 | **0.0643** |

A **7–20× degradation at the one dte that is skipped** — reached from a different direction
than the blow-up above, which is what makes it a control rather than a restatement.

**Behaviour:** `status = 'SKIPPED_EXPIRY'`, all four value columns **NULL**. Precedence matches
ENH-131 — expiry-day first, whatever else is true of the cycle.

**L78-3's W1 expiry-day leg is NOT built here.** The ruling says it would be *computed and
recorded under its own label but not displayed, until E1/E2-type evidence accumulates*. **E1
(S85) and E2 (S87) BOTH REFUSED**, so that leg stays **UNRECORDED** and L78-3's expiry leg is
not amended.

---

## §6 Net vs gross — the two pairs behave differently, and both are published

ENH-131's **Gate 2 FAILED because it scored a cancellation**: net/gross ran 0.0095–0.341 while
the gate compared nets at 1 %, so a 2–4 % gross error read as 19 %. That lesson is the reason
this section exists.

Measured over **eight arms** (four sessions × two expiry legs), net ÷ gross-of-per-strike-nets:

| construct | range | reading |
|---|---|---|
| ∂Δ/∂σ | 0.844 – 1.000 | |
| ∂Δ/∂t | −0.181, then −0.957 … −1.000 on 7 of 8 | **net is meaningfully signed** |
| ∂Γ/∂σ | −0.135 … 0.384 | |
| ∂Γ/∂t | 0.092 … −0.376 | **net is a cancellation residue** |

**So the answer differs by pair, and the spec states it rather than leaving the reader to
infer it:**

- **The DELTA pair's net IS meaningfully signed, and very nearly equals its gross** (|ratio|
  ≥ 0.957 on 7 of 8 arms; the exception is SENSEX dte 2 at 0.181 on ∂Δ/∂t). This is
  structural, not luck: `d2` changes sign at the money and `(oi_call − oi_put)` changes sign
  with it, so **the two sign flips cancel and every strike contributes the same way**. It is
  reported as net, with gross beside it.
- **The GAMMA pair's net is a small residue of large opposing terms** (|ratio| as low as
  0.008) and **must not be read alone**. It is reported as net **with gross mandatory
  alongside**, and the board renders the pair, never the net on its own.

Both views publish gross; `v_gex_greeks_l2_net` additionally publishes `net_over_gross_*` for
all four, **so no consumer has to decide for itself which case it is in** — which is precisely
what Gate 2's author had to do, and got wrong.

**Two different denominators exist and neither is implied by the other**, so both are named:
`v_gex_greeks_l2_strike.gross_*` is **per-leg** (CE and PE counted separately);
`v_gex_greeks_l2_net.gross_strike_*` is the sum of **absolute per-strike nets** (CE/PE
cancellation already taken). The ratios use the second.

---

## §7 Reliability at SENSEX dte 1–2 — the regime T1 covers

**Asked directly: is repricer precision the concern there? Yes, and it is the sharpest concern
in this spec — but it is not the only one, and the others are measurable now.**

1. **Gross fidelity is worst exactly there.** ENH-131's Gate 3b — Σ|BS − vendor per-leg
   contribution| ÷ Σ|vendor| — measured 3.4 %, **10.9 %**, 4.7 % across arms and **FAILED its
   5 % threshold on the SENSEX 1-dte arm at ~11 %**. A stable crossing is not a reproduced
   curve, and L7/L8 read the *curve*, not a crossing. Whatever makes the repriced gamma curve
   ~11 % unfaithful at SENSEX dte 1 propagates into ∂Γ/∂σ and ∂Γ/∂t, which are built from Γ.
2. **The d1 control degrades there too, and independently.** 0.0031–0.0038 at dte 7–9 →
   **0.0185 at dte 1** → 0.0643 at dte 0. dte 1 is ~5× the dte-8 error while still an order
   below dte 0.
3. **T-convention sensitivity is largest there.** SENSEX **dte 2** net ∂Δ/∂t spans a **factor
   of 2.4** across the three conventions. And **S86 observation (b)** found the convention
   *ordering reverses at dte 1* — `dte/252` ~10× better than `exact/365` on gamma — a reversal
   that tracks dte 1 rather than the symbol. **T1 picks `exact/365`; at dte 1 that may be the
   worse convention, and this spec follows T1 rather than the observation.**
4. **Vendor input quality is worst there.** Measured at the 10:15 cycle: `iv` null-or-zero on
   **34 % (dte 2) / 36 % (dte 1) / 50 % (dte 0)** of SENSEX W1 rows, `iv_max` 196–422 on W1 and
   **2062.81** on W2. The `iv > 0` predicate and the deep-ITM guard remove those **by rule,
   never by eye**, and `n_legs` publishes how many survived at each strike.
5. **ENH-98's precondition gradient is itself binding there.** 6.41× (dte 3) → 3.79× (dte 2) →
   **1.18× (dte 1)**, monotone over three consecutive SENSEX arms, driven by *dispersion* not
   the centre (ATM offset halved 19.1 → 10.0 while SE(median) grew 5.051 → 8.453). S86 stated
   **before** the re-run that 10-07 is more likely than not to be another NO-TEST. Under the
   2026-10-03 ruling that precondition no longer gates the gamma reading — which is what makes
   10-07 decidable at all — but the underlying dispersion has not improved, and the PROVISIONAL
   stamp exists because of it.

**What 10-07 tests, and what it does not.** It tests gamma relative error at SENSEX dte 1 under
`exact/365`. It does **not** test ∂Δ/∂t, ∂Γ/∂σ or ∂Γ/∂t directly, and no arm has. **The
inference from "gamma reproduces" to "its derivatives reproduce" is an assumption, stated here
as one**, and it is the weakest joint in the layer: the derivatives carry `1/(2T)` and `1/σ`
factors that gamma does not, so they amplify exactly the inputs that are worst at short dte.
A derivative-level arm is **owed** and is not proposed here, because specifying it after seeing
these numbers would be the same fitting §3 refuses.

---

## §8 D2 four-clause status at apply time

ADR-025 D2: a layer is **BUILT** only when all four hold.

| clause | at apply (Mon 2026-10-05 ≥ 16:00) | note |
|---|---|---|
| **1 — computes against the live DB and its output has been read** | **MET** | Already satisfied pre-apply: both bodies run inline and were read — 4 net rows, 59–109 strikes per leg, `is_trading_session = f` on the 10-02 frozen cycle. Re-read after apply as V1. |
| **2 — run-scoped and EXPLAIN-verified per ADR-021** | **MET** | ENH-131's latest-`ts` seek verbatim. Plans captured: strike **210.280 / 186.476 ms**, net **157.714 / 191.610 ms**, both ~40× under the 8 s ceiling; `CTE Scan on gate` at **loops = 1** in both, so the MATERIALIZED hint is verified rather than assumed (`.claude/rules/sql-views.md`). Two rejected gate shapes measured 11 040 ms and 26 424 ms, so the clause has demonstrably fired on this very object. |
| **3 — visible on at least one operator surface** | **NOT MET AT APPLY — and that is Amendment B, not a lapse** | ADR-025 **Amendment B (S81)** suspends clause 3: rendering is deferred until every layer carries a disposition. Clause 3 is therefore **PENDING BY DECISION**, the same status the three S81 views carry. When it is lifted, the surface is the Flows tab, and it renders **badged PROVISIONAL**. |
| **4 — ENH register entry + DDL committed under `sql/`** | **MET at apply** | DDL: `sql/2026-10-03_s89_v_gex_greeks_l2.sql`, committed with this spec, **with `COMMENT` and `GRANT` as LIVE statements** per TD-S81-NEW-5 — a body-only file is not a rebuild source, and a part-run apply that skips the GRANT leaves the view live and anon-unreadable at HTTP 200 with zero rows. Register entry: the ENH-98 S89 block spliced from this file. |

**Therefore L7 and L8 at apply: clauses 1, 2, 4 MET; clause 3 PENDING BY DECISION under
Amendment B. Disposition stays PENDING, not BUILT** — and that is a deliberate hold, not a
gap. **It would remain PENDING even if T1 passed on 10-07**, because clause 3 is suspended for
every layer; T1 governs whether the views survive, not whether they are BUILT.

---

## §9 Anon grant and naming, matched to the siblings — measured, not assumed

Measured 2026-10-03 from `pg_class.relacl` (`information_schema.role_table_grants` is useless
here — as `merdian_ro` it cannot see `anon`'s grants at all, and returns a clean-looking list
that omits them):

| object | kind | RLS | `anon` |
|---|---|---|---|
| `v_iv_surface`, `v_iv_term_structure`, `v_gex_repriced_flip`, `v_gex_concentration`, `v_gex_strike_rank`, `v_gex_strike_walls`, `v_gex_abs_exposure`, `v_gex_net_gamma_river`, `v_oi_rotation_since_open`, `v_max_pain_by_strike` | view | off | `anon=r` — SELECT alone |
| `v_gex_max_pain`, `v_gex_pin_maxpain` | view | off | **`anon=rm`** — carries MAINTAIN |

**All twelve are plain views, never matviews, and none has RLS enabled** — so for this family
the **GRANT alone is the boundary** (TD-S81-NEW-2: D.21.2's *"the boundary is the RLS policy +
GRANT pair"* is false where RLS is off).

The two `rm` rows are the **CASE-2026-09-22 default-privileges shape**. This file **follows the
`anon=r` majority, does not copy the `rm` anomaly, and does not repair it either** — repairing
it is `ALTER DEFAULT PRIVILEGES` work with its own blast radius, not a side-effect of a new
view. Section 4 is `REVOKE ALL … FROM anon;` then `GRANT SELECT … TO anon;`, in that order,
because `REVOKE` alone reproduces S39. `merdian_ro` gets SELECT, matching all twelve siblings.

**Naming** follows the `v_gex_*` family. `_l2_` is ENH-98's own word for this layer — its
register entry already proposes a `greeks_l2_analytics` table — so the views are
`v_gex_greeks_l2_strike` and `v_gex_greeks_l2_net`, and no column is named bare `vanna` or
`charm` (L78-1).

---

## §10 Verification — what each check can fail for

Section 6 of the DDL. Summarised here with the Rule 0 sentence attached to each.

| # | fails if | expected |
|---|---|---|
| **V1** | the latest-`ts` seek returned >1 `ts` per symbol, an expiry leg vanished, or a dte-0 row carries a non-NULL value | 4 rows; values NULL on exactly the non-`OK` rows |
| **V2** | **the d1 control**: median \|BS − vendor delta\| in the `[0.05, 0.95]` band exceeds **0.03** on any dte ≥ 1 leg. Every construct is a function of `d1`, so a wrong `r`, a wrong T unit, a wrong log argument or a wrong σ scale all land here | 0.0031–0.0185, measured. **The bar is set ~1.6× above the worst observed, stated as a belief, not fitted to the observation** |
| **V3** | `role_now ≠ anon`, or either count is 0 — the **anon path**, not object existence (a skipped GRANT is HTTP 200 + zero rows). **One execution**, `current_user` in the same result set (S84 §D.40.1) | `anon`, `n_strike > 0`, `n_net = 4` |
| **V4** | either comment length is NULL or differs from the file literal — the S79 part-run-apply failure | computed from the file **before** the run, never recalled (S81's wrong `comment_len`) |
| **V5** | any `(symbol, expiry_date)` group carries >1 distinct `status`, `dte`, `ts` or `r_sess` — which is what `max(status)` in the net view would silently absorb | 0 rows |
| **V6** | the q = 0 call/put equality fails at any strike carrying both legs. **The sign convention's whole justification rests on it**, and Rule 0 clause 4 forbids asserting it in a comment | 0 rows |
| **V7** | either plan exceeds the 8 s ceiling | 210.280 / 186.476 ms and 157.714 / 191.610 ms pre-apply; two rejected shapes at 11 040 / 26 424 ms |

---

## §11 What is NOT in this spec, recorded so the omissions are visible

- **The L78-2 "today's new positions" secondary leg.** L78-2 wants it labelled *"since open;
  assumes the standard dealer side"* and hidden when the L13 outlier guard trips. These views
  carry the **standing book only** — L78-2's primary. The secondary leg is an addition over
  the same arithmetic with a ΔOI weight in place of `oi`.
- **D-4's flow-vs-book ΔOI classification.** Ruled 2026-10-03 as a **parity prerequisite** for
  L7/L8 (the target reprices today's classified OI only). It is **not built here** and L7/L8
  are therefore **not yet complete against D-4**. Its baseline is *previous close*, while the
  shipped L13 `v_oi_rotation_since_open` anchors at **09:15 same-session open**, front expiry
  only — so D-4 needs a baseline L13 does not currently carry. **Parked by the operator**,
  filed as a post-parity candidate (**"L13 refinement: prev-close-anchored ΔOI"**), not built.
- **A derivative-level validation arm** (§7). Owed; deliberately not specified after seeing
  the numbers.
- **The monthly expiry legs** (§1). Blocked on capture depth, itself behind the TD-S81-NEW-14
  stage-2 redefinition.
- **Any reconciliation of SENSEX `r_sess` ≈ 0.10 against ENH-98's `r_eff` 3.57–3.81 %** (§3).
  Recorded as a live disagreement; shown not to move these numbers; **not resolved**. Filed as
  **TD-S89-NEW-3** — likely definitional (implied carry including dividend/borrow/basis vs a
  risk-free rate), and the confirmation-or-reconciliation is owed there, not here.

---

*ENH-98 L7/L8 design spec, S89, 2026-10-03. Authored, not applied. Nothing here authorises a
build; the 10-07 T1 arm does, and the kill in §0 governs if it refuses.*
