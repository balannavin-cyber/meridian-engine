# L12 pressure-ranking leg — DECLINED-ON-EVIDENCE (S89, 2026-10-03)

> **DECLINED-ON-EVIDENCE under ADR-025 D4.** The parity target's pressure formula is
> undisclosed (#558). Two candidate proxies were built and measured read-only; neither
> reproduces the property that defines the leg. **No pressure-rank ordering ships.**
>
> This file is the in-tree evidence record cited by **D-5a** (`rulings_s89.md`), the
> **ENH-125** register row, and the dated note at the head of `tech_debt.md`. The
> `claude/` namespace is project knowledge, not this git tree, so the citation resolves
> here.
>
> **Read-only throughout:** `bin/roq.sh` as `merdian_ro`. No view, table or production
> file was modified. Market closed (Saturday 2026-10-03), post-session.

---

## 1. What was tested, and what "working" would have meant

Two keys, both over the full strike ladder of a single γ-clock run:

| Key | Definition |
|---|---|
| **C1 — OI magnet** | `P1_k = (oi_call_k + oi_put_k) · exp(−((K_k − S)/(c·σ_T))²)`, `c ∈ {0.5, 0.75, 1.0, 1.5, 2.0}` |
| **C0 — proximity-weighted gamma** | `P0_k = abs(netΓ_k) · exp(−((K_k − S)/(c·σ_T))²)`, same sweep, `netΓ_k := gex_strike_snapshots.gex_cr` |
| **C2 — pain well** | `pain(k) = Σ_j [oi_call_j·max(K_k−K_j,0) + oi_put_j·max(K_j−K_k,0)]`; `P2_k = max_j pain(j) − pain(k)` |

**The pre-stated property.** The leg is only worth building if its ranking says something
the gamma ladder does not — i.e. the top-5 pressure order should **invert** the top-5
`abs(netΓ)` order (Spearman ρ negative), while the leader stays near spot. A key that
merely re-ranks `abs(netΓ)` monotonically adds a column and no information.

**ρ is read one way only, and it has to be said.** The two keys' top-5 *sets* differ, so
"correlate the two top-5 orders" is undefined across different sets. ρ_top5 is therefore
computed by taking **the key's own top-5 set** and re-ranking it by `abs(netΓ)` within
itself. ρ_all is over the whole ladder.

---

## 2. σ_T — measured per run, not assumed

`σ_T = spot · (atm_iv/100) · sqrt(dte/365)`, carried in **price points**.

**Source: `volatility_snapshots.atm_iv_avg` at the exact same `ts` as the γ run.**
Exact-ts alignment hit **15 of 15** runs. On 2026-10-01 its value is
`11.70527899673892` — **byte-identical** to `v_gex_strike_walls.atm_iv_used` on the same
run — so this is the shipped layer's own IV, not a substitute. No constant IV was needed
anywhere.

**A dimensional trap, recorded because the spec invites it.** `(K − S)/(c·σ_T)` divides a
point difference, so σ_T must be in points. On 10-01 the fractional σ_T is **0.01370** and
the points σ_T is **307.51**. Using the fraction would put `(K−S)/σ_T` at ~3,942 at one
strike step, the Gaussian would underflow to zero at every strike, and the key would
silently degenerate to `abs(netΓ)` ranked by nothing. `T_years = dte/365` is a stated
convention, not a measurement.

---

## 3. The 15-run window: 12 testable, 3 NO-TEST

Last 15 NIFTY trading days on the γ clock (**2026-09-10 → 2026-10-01**), one run per day
(that day's last run), each at its nearest expiry `>= run date`. Grid step **measured at
50.0 on all 15 runs**, not assumed.

| Day (IST) | dte | spot | atm_iv % | σ_T pts | Status |
|---|---|---|---|---|---|
| 2026-09-10 | 5 | 23477.80 | 9.0684 | 249.19 | usable |
| 2026-09-11 | 4 | 23398.10 | 10.1057 | 247.53 | usable |
| **2026-09-15** | **0** | 23118.60 | 0.7998 | **0.00** | **NO-TEST** |
| 2026-09-16 | 6 | 23217.60 | 12.6248 | 375.81 | usable |
| 2026-09-17 | 5 | 23270.60 | 10.5999 | 288.70 | usable |
| 2026-09-18 | 4 | 23346.40 | 8.5658 | 209.35 | usable |
| 2026-09-21 | 1 | 23414.30 | 12.1503 | 148.91 | usable |
| **2026-09-22** | **0** | 23329.00 | 2.3680 | **0.00** | **NO-TEST** |
| 2026-09-23 | 6 | 23446.80 | 8.4387 | 253.68 | usable |
| 2026-09-24 | 5 | 23063.10 | 11.6535 | 314.57 | usable |
| 2026-09-25 | 4 | 23140.50 | 9.8407 | 238.39 | usable |
| 2026-09-28 | 1 | 22780.25 | 14.5241 | 173.18 | usable |
| **2026-09-29** | **0** | 22716.20 | 0.7288 | **0.00** | **NO-TEST** |
| 2026-09-30 | 6 | 22620.45 | 11.6470 | 337.79 | usable |
| 2026-10-01 | 5 | 22446.00 | 11.7053 | 307.51 | usable |

**The dte-0 failure is structural, not a gap in the window.** At `dte = 0`,
`sqrt(T) = 0`, so `σ_T = 0` and the Gaussian divides by zero. **C1 is undefined on every
expiry day.** A T floor would not rescue it: ATM IV on those three days has itself
collapsed to **0.73 / 2.37 / 0.73 %**, so any small-T convention yields a σ_T of a few
points and the key degenerates to "the strike nearest spot". **The key is undefined
exactly on the days pinning matters most** — the same dte-0 wall already documented for
L3 and L10 (`MERDIAN_System_Map.md:1963-1976`; S62 rule at `.claude/rules/sql-views.md:20`).

**Every fraction below has 12 as its denominator, never 15.**

---

## 4. The defining property is not reproducible

ρ_top5 per run, both c (C1):

| Day | ρ_top5 c=0.75 | ρ_top5 c=1.0 | C1 leader | leader steps from nearest strike | within 1 step | `abs(netΓ)` leader | leader differs |
|---|---|---|---|---|---|---|---|
| 09-10 | +0.10 | +0.30 | 23500 | 0.00 | yes | 23500 | no |
| 09-11 | +0.80 | +0.80 | 23400 | 0.00 | yes | 23300 | yes |
| 09-16 | −0.30 | +0.30 | 23200 | 0.00 | yes | 23000 | yes |
| 09-17 | +0.30 | −0.40 | 23300 | +1.00 | yes | 23200 | yes |
| 09-18 | −0.20 | −0.50 | 23300 | −1.00 | yes | 23500 | yes |
| 09-21 | **−1.4 × 10⁻¹⁷** | +0.10 | 23400 | 0.00 | yes | 23400 | no |
| 09-23 | −0.50 | −0.30 | 23400 | −1.00 | yes | 23600 | yes |
| 09-24 | +0.40 | +0.30 | 23000 | −1.00 | yes | 23000 | no |
| 09-25 | +0.10 | +0.20 | 23100 | −1.00 | yes | 23000 | yes |
| 09-28 | −0.50 | −0.60 | 22800 | 0.00 | yes | 23000 | yes |
| 09-30 | +0.30 | −0.50 | 22700 | +2.00 | **no** | 22900 | yes |
| 10-01 | −0.60 | −0.70 | 22500 | +1.00 | yes | 22700 | yes |

| Statistic | c = 0.75 | c = 1.0 |
|---|---|---|
| mean ρ_top5 | **−0.0083** | **−0.0833** |
| range | −0.60 … +0.80 | −0.70 … +0.80 |
| strictly negative | **5 of 12** (+1 at float zero) | **6 of 12** |
| ρ_all (whole ladder) | **+0.84 → +0.90** across the c sweep | — |

**Verdict: the inversion is at chance.** 6 of 12 (c = 1.0) is exactly what a coin gives —
`P(≥6 of 12 | p = 0.5) = 0.61`. The mean is ~0 at both c. These data do not demonstrate
that C1 inverts the gamma order; they are consistent with no relationship.

**A count that fired for a reason other than the one it names.** The first summary read
"6 of 12 negative" at **c = 0.75** as well. One of those six is **2026-09-21, whose ρ is
−1.38777878078145 × 10⁻¹⁷** — a floating-point zero that satisfies `rho < 0`. Re-measured
with an explicit sign/epsilon split: **5 strictly negative, 0 exactly zero, 1 within 1e−9
of zero, 6 strictly positive.** The honest figure at c = 0.75 is **5/12**, which is
*further* from the claimed property, not closer. Recorded because the same filter shape
will recur in any future ρ sweep.

**The inversion, where it exists at all, is top-5-only.** ρ_all runs **+0.84 to +0.90**
and *rises* monotonically with c. Over the full ladder both keys agree with the gamma
order. If L12 is meant to disagree with the gamma ladder globally, neither candidate does.

**The single run that motivated this was the favourable tail.** 2026-10-01 reads
−0.60 / −0.70 — the most negative cell in the window. A one-run read of it was not
evidence, and the 12-run distribution is what retired the leg.

---

## 5. C2 is degenerate as a rendering key

C2's valley is real; the **key** has no dynamic range. `P2 = max(pain) − pain(k)` is
dominated by the constant `max(pain)`:

| C2 rank | strike | K − S | normalised by max | normalised min-max | total pain |
|---|---|---|---|---|---|
| 1 | 22500 | +54.0 | 1.000000 | 1.0000 | 13,110,899,750 |
| 2 | 22550 | +104.0 | 0.999835 | 0.9998 | 13,190,739,250 |
| 3 | 22600 | +154.0 | 0.998985 | 0.9990 | 13,602,342,000 |
| 4 | 22450 | +4.0 | 0.998853 | 0.9989 | 13,666,666,000 |
| 5 | 22400 | −46.0 | 0.997265 | 0.9973 | 14,435,892,250 |

Runner-up margin **0.000165** (max-normalised) and **0.0002** (min-max-normalised).
**Min-max normalisation does not rescue it**, because `min(pain)` is itself ~96 % of
`max(pain)`. A board drawing these as bars draws five identical bars. Any usable form
must normalise against **valley depth within a near-spot window**, not against the global
max — and that is a different key, not a rescaling of this one.

---

## 6. What survived the test and still does not ship

These are real properties of C1. They are recorded so the decline is not mistaken for
"the key measured nothing".

- **Leader adjacency holds, and is stable: 11 of 12** runs put the C1 leader within one
  strike step of the nearest-to-spot strike, **identically at both c**. The single failure
  is 09-30 at 2 steps.
- **C1's leader differs from the `abs(netΓ)` leader in 9 of 12 runs.** So C1 does say
  something different about *where* — just not in a reliably inverted *order*.
- **`c` is not a leader knob.** c = 0.75 and c = 1.0 select the **same leader on all 12
  runs**; only ρ_top5 moves. Choosing between them is a top-5-ordering decision.
- **But pin location is already served.** The γ-clock max-pain view (**E-D2**) gives the
  pin strike on the same run as the walls, so the one property C1 delivers is not a gap
  C1 is needed to fill.
- **And it is undefined at dte = 0**, where a pin read is most wanted (§3).

**What ships instead:** the ladder keeps the **net-Γ LONG/SHORT sign tag** (D-2, A.5) and
nothing else from this leg.

---

## 7. A threshold note (S83 family)

The first single-run flag used "**leader within 1 strike of spot**" implemented as
`|K − S| ≤ 50`. All six keys put the leader at **54.0 pts** from spot and failed by
**4 points** — because spot 22446 sits 4 pts below 22450, so on a 50-pt grid the strike
one step *above* spot is always 54 away. A 50-pt threshold is only satisfiable when spot
lands almost exactly on a strike: it scores the grid offset, not the quantity.

Measured under three readings on the same run:

| Reading | flags (of 6 keys) |
|---|---|
| `\|K − S\| ≤ 50` (literal) | **0** |
| leader is one of the two strikes bracketing spot | **0** |
| leader within one step of the **nearest** strike to spot | **3** (C1 at c = 0.50 / 0.75 / 1.00) |

**The cross-run work therefore uses the grid-relative form** — distance in **strike
steps** from the nearest-to-spot strike, with the step measured per run. A mis-specified
threshold is recorded as mis-specified and never loosened to make a build pass; the
replacement was stated before the 12-run sweep ran.

---

## 8. Guardrail

**Do not re-propose a proximity-weighted-gamma or OI-magnet pressure key.** Re-opening
requires one of:

1. **A newly disclosed formula** from the parity target — the measured decline is of
   *proxies*, and a disclosed definition is a different object; or
2. **ENH-133 history** (D-3) enabling a **materially different** key — one that does not
   reduce to `abs(netΓ)` × a spot-distance kernel, and whose property is **pre-registered
   with a threshold derived from the quantity's scale before any measurement**.

Neither condition is met by re-running this sweep on more days. A longer window moves the
chance estimate; it does not make a key defined at `dte = 0`, and it does not give C2
dynamic range.

---

## 9. Provenance

| Field | Value |
|---|---|
| Measured | 2026-10-03 (Saturday, out of hours), Session 89 |
| Path | `bin/roq.sh` only, role `merdian_ro`, `default_transaction_read_only = on` |
| Source relations | `gex_strike_snapshots` (unpurged; ladder, OI, `gex_cr`) · `volatility_snapshots` (`atm_iv_avg`) · `v_gex_strike_walls` (IV cross-check) |
| Window | 15 NIFTY γ-clock trading days, 2026-09-10 → 2026-10-01; 12 testable |
| Ladder width | varies **91 → 144** strikes across runs, so ρ_all is **not** comparable across days without bounding the ladder |
| Writes | none — no view, table, production file or engine change |
| Ruling | **D-5a**, `docs/research/s89_rulings/rulings_s89.md` |

*Evidence record, Session 89, 2026-10-03. Nothing here authorises a build. The decline is
of two measured proxies, not of the parity target's undisclosed formula — §8 states what
would re-open it.*
