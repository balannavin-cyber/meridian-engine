# Part A results — where the blank gamma comes from

Read-only. Every read through `bin/roq.sh` as `merdian_ro`, every run under
`( ulimit -v 700000; … )`. No write, no vendor call, no outcome computed. Queries in
`queries/`, raw payloads in `_partA_raw.txt`, `_q03.txt`, `_q04.txt`, `_q05_raw.txt`,
`_q06.txt`. Run timings in `_partA_run.log`, `_q05_run.log`.

Days 2026-11-16, 11-17, 11-18, 11-19; NIFTY and SENSEX separately. Front-expiry runs
taken from `gamma_metrics` (one row per front-expiry `run_id`; the S80 extra-expiry legs
carry their own `run_id` and have no `gamma_metrics` row, so the join **is** the
front-expiry filter), joined to `option_chain_snapshots` on `run_id` **and**
`expiry_date`.

Ran during market hours after the plan cost was shown: every scan is an index scan,
largest planner estimate 2,325 rows, no sequential scan on any relation (EXPLAIN in
`queries/`). 8 queries, 2.99–4.20 s each.

| symbol | day | runs | expiry | chain legs | gss strikes |
|---|---|---|---|---|---|
| NIFTY | 11-16 | 87 | 2026-11-17 | 46,110 | 12,354 |
| NIFTY | 11-17 | 78 | 2026-11-17 | 41,340 | 11,076 |
| NIFTY | 11-18 | 87 | 2026-11-23 | 47,676 | 13,746 |
| NIFTY | 11-19 | 87 | 2026-11-23 | 47,676 | 13,746 |
| SENSEX | 11-16 | 87 | 2026-11-19 | 42,456 | 17,741 |
| SENSEX | 11-17 | 78 | 2026-11-19 | 38,376 | 16,500 |
| SENSEX | 11-18 | 87 | 2026-11-19 | 43,500 | 18,313 |
| SENSEX | 11-19 | 87 | 2026-11-19 | 43,500 | 18,534 |

`expiries = 1` on all eight, consistent with Stage 1 C3.

---

## The premise was wrong in one specific way

> Stage 1: "`gamma_call` is NULL on strikes below spot and `gamma_put` NULL above spot
> … **never 0**."

That holds for `gex_strike_snapshots` and is confirmed. But the chain table underneath
it is the mirror image:

**`option_chain_snapshots.gamma` is NULL on 0 of 94,942 NIFTY and 0 of 108,086 SENSEX
legs with `oi > 0`. Every blank is a stored `0`.** `iv` likewise: 0 NULLs.

So the two tables encode the same absence in opposite ways, and A1(c) is the converter:
`build_gss_rows` writes `NULL` unless `gamma_raw != 0.0`. Nothing is lost or added — the
cross-tab below is exact — but **no query can tell a vendor `0` from a vendor `NULL` by
looking at `gex_strike_snapshots`**, and no query can tell them apart in the chain table
either, because the vendor never sends `NULL`.

---

## A2 — chain rows, by option_type × ITM depth (4 days pooled)

Depth `m`: calls `(spot − strike)/spot`, puts `(strike − spot)/spot`. Counts over legs
with `oi > 0`. Full table in `_partA_agg.txt`.

| sym | ot | bucket | legs oi>0 | γ NULL | γ = 0 | γ > 0 | iv = 0 | γ blank % legs |
|---|---|---|---|---|---|---|---|---|
| NIFTY | CE | OTM | 17,742 | 0 | 891 | 16,851 | 788 | 5.02 |
| NIFTY | CE | ITM 0–1 % | 1,721 | 0 | 36 | 1,685 | 36 | 2.09 |
| NIFTY | CE | ITM 1–2 % | 1,716 | 0 | 235 | 1,481 | 235 | 13.69 |
| NIFTY | CE | ITM 2–5 % | 5,143 | 0 | 2,738 | 2,405 | 2,731 | 53.24 |
| NIFTY | CE | ITM > 5 % | 21,445 | 0 | 15,322 | 6,123 | 15,223 | 71.45 |
| NIFTY | PE | OTM | 33,180 | 0 | 11,237 | 21,943 | 6,302 | 33.87 |
| NIFTY | PE | ITM 0–1 % | 1,715 | 0 | 88 | 1,627 | 88 | 5.13 |
| NIFTY | PE | ITM 1–2 % | 1,715 | 0 | 261 | 1,454 | 261 | 15.22 |
| NIFTY | PE | ITM 2–5 % | 5,045 | 0 | 1,191 | 3,854 | 1,191 | 23.61 |
| NIFTY | PE | ITM > 5 % | 5,520 | 0 | 3,090 | 2,430 | 3,090 | 55.98 |
| SENSEX | CE | OTM | 20,423 | 0 | 3,029 | 17,394 | 0 | 14.83 |
| SENSEX | CE | ITM 0–1 % | 2,794 | 0 | 52 | 2,742 | 52 | 1.86 |
| SENSEX | CE | ITM 1–2 % | 2,800 | 0 | 672 | 2,128 | 670 | 24.00 |
| SENSEX | CE | ITM 2–5 % | 8,103 | 0 | 5,407 | 2,696 | 5,381 | 66.73 |
| SENSEX | CE | ITM > 5 % | 15,156 | 0 | 14,287 | 869 | 14,171 | 94.27 |
| SENSEX | PE | OTM | 49,984 | 0 | 30,591 | 19,393 | 13,664 | 61.20 |
| SENSEX | PE | ITM 0–1 % | 2,786 | 0 | 98 | 2,688 | 98 | 3.52 |
| SENSEX | PE | ITM 1–2 % | 2,644 | 0 | 318 | 2,326 | 317 | 12.03 |
| SENSEX | PE | ITM 2–5 % | 2,934 | 0 | 657 | 2,277 | 655 | 22.39 |
| SENSEX | PE | ITM > 5 % | 462 | 0 | 77 | 385 | 77 | 16.67 |

**The blank is U-shaped in moneyness, not ITM-only.** It rises monotonically with ITM
depth (NIFTY CE 2.09 % → 13.69 % → 53.24 % → 71.45 %) *and* it is large in the OTM
bucket (SENSEX PE 61.20 %). That is the shape of γ itself, which falls towards zero on
both wings — see A4.

**Near ATM, where a pin lives, the blank is small but not zero: 1.86 %–5.13 % of legs
within 1 % of spot.** Those are not wing strikes and they are not explained by γ being
small; A4 classifies them.

### The A2 key cell — legs with `oi > 0` AND `ltp > 0` AND γ blank

| symbol | scope | legs | blank γ | % legs | OI | OI blank | % of OI |
|---|---|---|---|---|---|---|---|
| NIFTY | ITM only | 44,020 | 22,961 | **52.16** | 22,673,119,885 | 4,839,087,825 | **21.34** |
| NIFTY | all buckets | 94,942 | 35,089 | 36.96 | 153,174,924,175 | 8,759,844,210 | 5.72 |
| SENSEX | ITM only | 37,679 | 21,568 | **57.24** | 2,173,374,630 | 172,567,660 | **7.94** |
| SENSEX | all buckets | 108,086 | 55,188 | 51.06 | 22,430,165,850 | 1,504,687,700 | 6.71 |

`legs_oi_px` equals `legs_oi` in **every** cell: **every leg with open interest also has
`ltp > 0`**. Price is never the discriminator — the blank cannot be explained by an
untraded leg.

**Unreconciled against the engine note.** The 2026-11-18 note says "about 13 % of NIFTY
legs and 28 % of SENSEX legs carry open interest and no vendor gamma". Measured here:
**36.96 % and 51.06 %** of legs, or **5.72 % and 6.71 %** of open interest. No
denominator computed in this session reproduces 13 % / 28 % — not legs, not OI, not
ITM-only (21.34 % / 7.94 %), not strikes (43.9 % of NIFTY strikes have a blank call leg).
I am not going to invent a reading that fits; the note's own query would settle it. Both
numbers cannot be right about the same quantity.

## A3 — chain against the strike table

Cross-tab over all strikes of all front-expiry runs on the four days. Every strike falls
in exactly **two** cells:

| symbol | leg | chain state | gss state | strikes |
|---|---|---|---|---|
| NIFTY | CE | POS | POS | 28,545 |
| NIFTY | CE | ZERO | NULL | 22,377 |
| NIFTY | PE | POS | POS | 31,985 |
| NIFTY | PE | ZERO | NULL | 18,937 |
| SENSEX | CE | POS | POS | 25,832 |
| SENSEX | CE | ZERO | NULL | 45,256 |
| SENSEX | PE | POS | POS | 36,834 |
| SENSEX | PE | ZERO | NULL | 34,254 |

**No `NOROW` cell, no chain `NULL` cell, no gss `ZERO` cell.** Every chain leg the
strike table needed was present; the mapping is exactly rule A1(c) and nothing else.

**Legs where the chain has γ > 0 and the strike table has NULL: 0**, on all four days,
both symbols, both legs (R5 returned no rows). *What would have made this fire:* the
deep-ITM guard nulling a stored gamma, or the `is None and` first-write-wins clause
dropping a second leg at one strike. Neither happens — consistent with A1(b)'s reading
that the guard touches only the return value, and with one leg per
`(strike, option_type)` per run.

### Strikes with both stored gammas > 0 and `gex_cr = 0`

| symbol | gss strikes | both γ > 0 | …and `gex_cr` = 0 | …and > 5 % from spot | all `gex_cr` = 0 | …both γ NULL |
|---|---|---|---|---|---|---|
| NIFTY | 50,922 | 20,467 | **224** | **224** | 11,462 | 10,859 |
| SENSEX | 71,088 | 23,862 | **5** | **5** | 33,526 | 32,284 |

All 229 are more than 5 % from spot — **the deep-ITM guard's signature, isolated**
(A1(b)/(d): the guard zeroes the contribution after `gamma_raw` is already captured).
These strikes assert, to any reader of `gex_strike_snapshots` alone, "two live gammas and
no exposure", which is arithmetically impossible from the stored columns.

The bulk of `gex_cr = 0` is the ordinary case: 10,859 of NIFTY's 11,462 and 32,284 of
SENSEX's 33,526 have both gammas NULL. A residue of 379 NIFTY and 1,237 SENSEX strikes
is left over by arithmetic (11,462 − 10,859 − 224; 33,526 − 32,284 − 5). **What makes
those strikes carry `gex_cr = 0` was not measured.** The obvious candidate — one stored
gamma and no open interest on that side — is a guess, not a count, and no query in this
session separates it from the alternatives.

## A4 — the stored vendor payload

`option_chain_snapshots.raw` holds the vendor's whole per-leg object
(`ingest_option_chain_local.py:311`), so this is measured, not UNMEASURED.

Three blank legs per symbol, highest OI first, last front-expiry run of 2026-11-19
(`_q03.txt`). Representative:

```
NIFTY  21000 PE  spot 25514.30  oi 2,243,670  ltp 0.90  chain gamma 0.0  iv 63.10
   raw.greeks = {"vega": 0.15532, "delta": -0.00176, "gamma": 0, "theta": -1.14621}
SENSEX 83000 CE  spot 83021.75  oi 3,392,800  ltp 21.70  chain gamma 0.0  iv 0.0
   raw.greeks = {"vega": 0, "delta": 0, "gamma": 0, "theta": 0}
```

**The vendor itself sends a literal `0`.** Across every blank leg measured
(`_q04.txt`): `raw` is missing the `greeks` key on **0** legs, missing the `gamma` key on
**0** legs, and carries `gamma` as a literal zero on **all** of them. The blank is not
created by ingest, and nothing is lost in transit.

Two distinct vendor populations, separated by whether the other greeks are also zero.
Last 10 runs of 2026-11-19:

`_q04.txt` filters on chain `gamma = 0` and so says nothing about a leg whose chain
gamma is NULL. **That filter excludes nothing here:** A2 measured chain `gamma IS NULL`
on **0** of 94,942 NIFTY and **0** of 108,086 SENSEX legs with `oi > 0`, so `gamma = 0`
covers every blank leg in the window. Were that count ever non-zero, the population
split below would be silent about those legs and would have to say so.

| sym | bucket | blank legs | vendor sent nothing | γ-only zero | remainder | OI blank | OI "nothing" |
|---|---|---|---|---|---|---|---|
| NIFTY | OTM | 321 | 11 | 310 | **0** | 61,737,650 | 3,074,630 |
| NIFTY | ITM 1–2 % | 2 | 2 | 0 | **0** | 3,165,305 | 3,165,305 |
| NIFTY | ITM 2–5 % | 134 | 134 | 0 | **0** | 45,193,980 | 45,193,980 |
| NIFTY | ITM > 5 % | 758 | 745 | 13 | **0** | 142,764,895 | 142,173,460 |
| SENSEX | OTM | 1,719 | 1,069 | 650 | **0** | 351,424,800 | 24,967,660 |
| SENSEX | ITM 0–1 % | 61 | 61 | 0 | **0** | 41,213,940 | 41,213,940 |
| SENSEX | ITM 1–2 % | 79 | 78 | 1 | **0** | 5,699,280 | 5,683,480 |
| SENSEX | ITM 2–5 % | 137 | 134 | 3 | **0** | 858,800 | 835,460 |
| SENSEX | ITM > 5 % | 459 | 459 | 0 | **0** | 346,740 | 346,740 |

"vendor sent nothing" = `delta`, `vega` and `theta` in `raw.greeks` are **all** zero.
`remainder = blank − nothing − γ-only` is **0 on every row**, so no leg fell between the
two columns through a NULL in `delta`/`vega`/`theta` — the risk that those two `FILTER`
clauses both evaluate NULL does not materialise here, and `raw_no_greeks_key = 0`
corroborates it independently.

**ITM blanks are a vendor blackout; OTM blanks are mostly arithmetic.** Every ITM bucket
is ≥ 97 % "vendor sent nothing". NIFTY's OTM blanks are 97 % γ-only (the vendor supplied
delta, vega, theta and iv, and only γ came through as 0). SENSEX's OTM blanks are 62 %
blackout.

**The 61 SENSEX legs within 1 % of spot are a per-leg blackout** — iv 0,
all four greeks 0, with a live price and millions of contracts of OI (the 83000 CE above
is 0.026 % from spot).

### Correction: the near-ATM blackout is one-sided on all 61 legs measured

An earlier draft of this file asserted that these 61 legs are the population a look-back
cannot work around, "because both legs at that strike are blacked out". **That was wrong,
and it was never measured** — it was inferred from a single A4 sample row. The
measurement (`queries/q07_sibling_leg.sql`, same scope and same blackout definition as
`_q04.txt`):

| quantity | value |
|---|---|
| blackout legs | 61 |
| sibling leg absent | **0** |
| sibling `gamma > 0` | **61 (all)** |
| sibling also blacked out | **0** |
| sibling `iv > 0` | 61 |
| blackout open interest | 41,213,940 |

16 distinct strikes across 10 runs, spanning 82,200–83,700, `iv = 0` on all 61, live
prices from 21.65 to 822.25.

**Scope of the claim.** Among the 61 ITM-bucket (0–1 %) blackout legs, the sibling is
intact on all 61. The blackout leg is the ITM one **by construction of the bucket** — 36
CE and 25 PE. Blackouts of **OTM** legs near spot were not examined, because the OTM
depth bucket is a single bucket; nothing here says whether they occur or how their
siblings fare.

**A usable gamma exists on all 61 siblings** (`gamma > 0`, range 1 × 10⁻⁵ to
5.09 × 10⁻³). Whether borrowing it is accurate enough is **not measured here.** Two
reasons for caution: the engine note of 2026-11-18 records that vendor call and put gamma
disagree at one strike because of the inferred forward; and a sibling at 1 × 10⁻⁵ sits on
the quantisation floor, so in relative terms it can be off by up to 50 %. B3 measures
call/put gamma ratios on the **own-solved history**, not on the vendor chain, so it does
not settle this either.

**The exposure is not recovered, only the gamma.** `build_gss_rows` keeps the surviving
leg's value in `gamma_call` / `gamma_put`, so the strike does retain a gamma. But
`gex_cr` is a netted sum in which the blacked-out leg contributes exactly `0` (A1(d)).
So the **41,213,940 of open interest sitting on the blacked-out leg is still counted as
zero** in `gex_cr`, and therefore in the Board's pin. The gamma survives in storage; the
exposure does not.

What remains unrecoverable even in storage is narrower than the earlier claim: a strike
where **both** legs are blank. A3 counts those directly — 10,859 NIFTY and 32,284 SENSEX
strikes with both gammas NULL and `gex_cr = 0` — presumably wing strikes rather than the
near-ATM pin band, but no measurement here establishes how many of them sit near spot.

### Why the γ-only zeros are a rounding floor, not missing data

Every vendor greek is transmitted **rounded to 5 decimal places**. Tested over all
front-expiry runs of the four days, per symbol-day (8 queries, 2.99–3.67 s):

| symbol | legs γ > 0 | not a multiple of 1e-5 (exact) | (1e-6 tolerance) | multiple of 1e-6 not 1e-5 | at the floor 0.00001 |
|---|---|---|---|---|---|
| NIFTY | 60,530 | **0** | **0** | 0 | 13,024 (21.5 %) |
| SENSEX | 63,837 | **0** | **0** | 0 | 12,919 (20.2 %) |

`delta`, `vega` and `theta` also return **0** failures. Pooled distinct γ values —
NIFTY 461, SENSEX 198 — are all on the 1e-5 lattice, re-tested independently in Python
`Decimal`, and the smallest six are exactly `0.00001 … 0.00006`.

`option_chain_snapshots.gamma` is `numeric` (`information_schema`, `_q00.txt`), so the
exact test carries no binary-rounding artefact; the 1e-6 tolerance form agrees, which is
the control on that specific risk.

**The control that makes this discriminating rather than vacuous:** `iv` on the *same*
runs is **100.00 % not** a multiple of 1e-5 — 106,153 / 106,153 NIFTY and 89,034 /
89,034 SENSEX — and 100 % not a multiple of 1e-2, so it is not a 2-dp field either. From
`raw`, vendor `implied_volatility` carries **12 to 16** decimal places (`_q06.txt`).
The test separates a quantised field from a full-precision one on real data.

So **`gamma = 0` from the vendor means the true γ fell below the vendor's reporting
floor.** The lattice test fixes the lattice spacing at 1 × 10⁻⁵ but **cannot tell
rounding-to-nearest from truncation**: under rounding the floor is 5 × 10⁻⁶, under
truncation it is 1 × 10⁻⁵, and both produce exactly the observed lattice. Either way,
against the **lowest** measured ATM γ of 1.2 × 10⁻³ the floor is **0.4 % to 0.8 %** of
ATM γ, **so nothing concluded here depends on which of the two it is.**

The 21 % pile-up at exactly `0.00001` is the **rounding-or-truncation signature** — a
continuous distribution pushed onto a lattice whose bottom rung is the last value before
zero. It establishes that a floor exists; it does not discriminate between the two.

A caution for anyone re-running `_q06.txt`: 7 NIFTY and 1 SENSEX legs show γ with **4**
decimal places. That is JSON trailing-zero suppression (`0.00120` → `0.0012`), still on
the 1e-5 lattice, not a counter-example.

---

## Verdicts

**NIFTY — A: blank is in the chain rows as stored (vendor; A4).**
**SENSEX — A: blank is in the chain rows as stored (vendor; A4).**

Not "mixed", and the split the mixed verdict would carry is **0 legs / 0 % of open
interest**: R5 found no leg whose blank the writer created out of a non-blank chain
value, and the cross-tab has no cell other than POS→POS and ZERO→NULL.

Two riders, both load-bearing for the look-back:

1. The **NULL encoding** in `gex_strike_snapshots` *is* created after the chain rows, by
   rule A1(c) — the chain stores `0`, never NULL. The absence is the vendor's; the NULL
   is MERIDIAN's. Three upstream states (vendor 0, vendor NULL, no leg) collapse into it,
   and only the first occurs in practice.
2. The vendor's `0` is **two different facts wearing one value**: an underflow below the
   vendor's reporting floor (5 × 10⁻⁶ if rounded, 1 × 10⁻⁵ if truncated; see the
   quantisation section), seen in most OTM blanks where delta/vega/theta/iv are all
   present; and a total blackout (nearly all ITM blanks, and 61 near-ATM legs, where
   the whole greeks block and iv are zero). A look-back that treats `gamma = 0` as
   "negligible γ" is right for the first and wrong for the second. On the 61 near-ATM
   blackouts the sibling leg carries a usable γ, but `gex_cr` still nets that leg's open
   interest at zero — see the Correction above.

## What these tests could not see

- **Four days, one expiry each.** No expiry-cycle, no regime, no vendor-version
  variation. The 2026-11-17 runs are a NIFTY expiry day (78 runs vs 87) and are pooled
  with the rest, not analysed separately.
- **The OTM bucket is one bucket.** Depth is resolved on the ITM side only, so the
  blank's gradient *within* OTM — which A4 shows is where the underflow population lives
  — is invisible here. SENSEX PE OTM at 61.20 % blank is an average over near-ATM and
  far-wing strikes that almost certainly differ by an order of magnitude.
- **A4's population split is 10 runs of one day**, not the four-day window. The
  blackout/underflow ratio is measured on 3,670 blank legs out of 90,277 in the full
  window.
- **Nothing here measures whether a blank γ matters.** No strike is related to later
  price anywhere in Part A, by instruction. "21.34 % of ITM open interest has no γ" is a
  statement about inputs, not about pin accuracy.
- **Why the vendor blacks out a leg is not measured** and is not visible in storage.
  `raw` records what arrived, not the vendor's reason. The near-ATM blackouts in
  particular have no explanation here beyond "the vendor sent zeros".
- **Vendor-vs-ingest is settled only for the states that occurred.** Ingest's NULL path
  (`:175-176`, `:282`) is never exercised by this data, so it is read from code, not
  measured.
- **The `signed_gamma_exposure` / `signed_gex_vec` equivalence is read, not tested**
  (Rule 0 clause 4) — it matters for Part B, which uses the vectorised one.
