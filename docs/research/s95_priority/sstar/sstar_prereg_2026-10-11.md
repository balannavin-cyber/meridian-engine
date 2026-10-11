# S\* — the re-priced zero-Δ level: pre-registration (S95, 2026-10-11)

**Status: PRE-REGISTERED, NOT RUN.** Committed with its `git hash-object` recorded **before** the first
export of real arm data. Ruling basis: **S94-H** (S\* ships as its own view `v_dex_repriced_zero`, after
the book; *"L3's five-gate record is re-run for the delta curve, not inherited"*). Spec: P6 design note
§5.2 (definition, the two changes) and §5.3 (dropped legs published). Roadmap §2.1 **P6**. Not a parity
layer; display-only (S37).

Artefacts committed together with this file, in this directory:

| file | what |
|---|---|
| `sstar_view_body.sql` | Section 1 of the future `sql/` file — the view body. Its bytes are fixed by this commit. |
| `sstar_gates.py` | The gate harness: an **independent** Python implementation written from §5.2's formula, not translated from the SQL. Reads CSV exports only. |
| `arms.csv` | The 11 arms. |

## 1. The object

`v_dex_repriced_zero`, grain `(symbol)`, latest chain cycle. **Every CTE of ENH-131
(`sql/2026-09-25_s83_v_gex_repriced_flip.sql`) is taken unchanged** — symbols, latest (ADR-021, never
`created_at`), front, scoped, hdr (T = exact seconds to 15:30 IST / 365 d), legs (R1 frozen set, inherited
per §5.3), futwin / futfront / rrows / rstats (session-median futures carry, ≥ 6 rows else
`UNMEASURABLE_R`), atm / atmiv, evalset (dte 0 refused, S62), grid (201 pts, ±10 %), adj / crossings /
counted / nearest, status precedence. **Exactly two changes** (§5.2):

1. the greek — `Φ(d1)` for a call, `Φ(d1) − 1` for a put, `Φ(x) = 0.5·erfc(−x/√2)`, `d1` identical to L3;
2. one power of S (`Δ·oi·S/1e7`) and **no PE → −1 factor** (L3's is deleted, not copied).

**Added, per §5.3:** `n_legs_used`, `n_legs_oi`, `n_dropped_no_iv`, `oi_dropped_no_iv`,
`n_dropped_other`, `oi_dropped_other`, `oi_total`; and `net_dex_at_spot_cr` / `gross_dex_at_spot_cr`
(grid point i = 100, s = spot exactly). Output level `zero_delta`, with `cross_direction`,
`zero_minus_spot`, `zero_sigma`, `n_cross_within_2sigma`, `n_cross_full_grid`, `status`.

**The as-of form** used to evaluate historical arms differs from the body by **one predicate** — the
inert comment `-- @ASOF@` in `latest` is replaced by `AND o.ts <= <arm ts>` (the ENH-134 / S88 pattern).
Nothing else is altered; `sstar_gates.py --emit-sql` asserts the marker occurs exactly once.

## 2. A structural fact the gates use

Every Black–Scholes delta, call or put, is **strictly increasing in S** for σ > 0, T > 0. So
`D(S) = Σ Δᵢ(S)·OIᵢ` is strictly increasing and **S\* is unique when it exists, and always a neg→pos
crossing.** The published curve is `D(S)·S/1e7`, which has the same sign. A crossing outside ±10 % of
spot is `NO_CROSSING` — a statement about the book, not a failure.

## 3. Arms (fixed now; `arms.csv`)

Chosen from the S95 availability probe (`sstar_A1`, 2026-10-11 12:39 IST — existence and leg counts only,
no repricing, no level, no outcome). Chain retention measured there: oldest row **2026-08-24 15:30 IST**
on both symbols.

| arm | role | dte (probe) |
|---|---|---|
| L3-A NIFTY 09-24 15:20 · L3-C SENSEX 09-23 15:40 · L3-D NIFTY 09-23 12:00 · L3-E SENSEX 09-22 12:00 · L3-F NIFTY 09-18 12:00 | **L3's five gate arms**, re-run | 5 · 1 · 6 · 2 · 4 |
| OOS NIFTY 10-07 · OOS SENSEX 10-07 · OOS NIFTY 10-08 · OOS NIFTY 10-09 · OOS SENSEX 10-09, all 12:00 | **out of sample** — every post-S83 candidate probed, except the one at dte 0 | 6 · 1 · 5 · 4 · 6 |
| CTRL SENSEX 10-08 12:00 | **negative control** — dte 0, must be refused (`SKIPPED_EXPIRY`) | 0 |

**Arm ts** = the first chain snapshot in `[label, label + 5 min)` IST — the cycle the label names. (The
probe read *at or before* the label and so landed one cycle early, e.g. 11:55 for 12:00; that is why the
rule is stated.) An arm with no snapshot in its window is reported unavailable, never substituted.

## 4. Gates — each states what makes it fail; thresholds derived before any measurement

`σ₁d = spot × atm_iv/100 × √(1/365)` (L3's). An arm is **scorable** for G4/G5 if its status is `OK`,
σ₁d exists and T(c) is computable; for G3 if its status is `OK` or `NO_CROSSING` and T(c) is computable.

**T conventions (L3's three, read from its gate scripts H4/I8/J5):** (a) `dte_cal/365`; (b) exact
seconds to 15:30 IST on expiry `/(365·86400)` — the view's; (c) `sessions/252`, sessions = dates in
`(ts date, expiry]` with `trading_calendar.is_open = true`. **A date in that range with no
`trading_calendar` row makes T(c) unmeasurable** for that arm (ADR-020: absence is not a verdict); the arm
is then unscorable, never filled in.

| gate | asserts | fails when | threshold and its derivation |
|---|---|---|---|
| **G1** implementation | the view body (as-of) and the independent Python give the same row, on **all 11 arms** incl. the control | status differs; `n_legs_used`, dropped counts, `n_cross_full_grid` differ; S\* or net-at-spot differ beyond tolerance; the control is not `SKIPPED_EXPIRY` | \|ΔS\*\| ≤ 1e-6 × spot; \|Δnet\| ≤ 1e-6 × gross + 1e-9 Cr. Both sides are IEEE double on the same grid and interpolation, so a correct pair differs by summation order, ~1e-12 relative; the bound is 10⁶× that and still ~10⁻⁴ of a 1-day σ. |
| **G2** descriptive | **never gates** | — | Reports, per scorable arm: repriced net and gross at spot vs the **vendor-delta** net on the same legs; S\* in points and σ; dropped legs and OI. L3's G2 (net vs net) was mis-specified, and §4.1/§4.2 already measured vendor vs parity delta 1.6–2.9× apart: a gate here would score the vendor's parity failure, not the model. |
| **G3** structure | on every G3-scorable arm × every (r, T) of the G5 sweep: `D(S)` strictly increasing over all 201 points; ≤ 1 crossing, and it is neg→pos | any non-increase, any second crossing, any pos→neg | None to choose: §2 is exact. A sign error or wrong `d1` breaks it. **It cannot catch a copied PE flip on a call-heavy book** (the flipped sum stays positive and can stay increasing) — measured on the S95 local test, so that mutant is assigned to G1. |
| **G4** r sensitivity | S\* across `r ∈ {r_p10, r_sess, r_p90}` at T(b) moves ≤ 0.25 σ₁d | spread > 0.25 σ₁d, or any variant has no level | **0.25 σ₁d, L3 Gate 5 clause (i)'s.** Scale: with near-equal legs, ∂S\*/∂r ≈ S·T, so the widest measured L3 band (p10–p90 0.335 at 1 dte) moves S\* ≈ S × 0.335/365 ≈ 0.0009 S ≈ 0.13 σ₁d at NIFTY's ~12 % IV. r entered as a percent (×100) moves it ~13 σ₁d — the defect this can see. |
| **G5** L3 Gate 5, re-run | S\* across the full sweep, `{r_p10, r_sess, r_p90} × {T(a), T(b), T(c)}`, moves ≤ 0.25 σ₁d | spread > 0.25 σ₁d, or any of the 9 variants has no level | **0.25 σ₁d, inherited unchanged from L3 Gate 5, not loosened.** Recorded honestly: T(c)/T(b) is ~1.4× on a 1-dte arm, and the delta curve's response to T was never measured — this gate is where that is learned. |

**L3's Gate 4 (single-cycle carry, ±0.01 band) is NOT re-run in its own form:** S83 recorded it as
under-specified (~19× narrower than measured dispersion) and replaced it by the session median that G4/G5
use. Re-running a gate known to be mis-specified would assert nothing.

**Mutants** (in the harness; each must make its named gate fail on ≥ 1 arm, or the run is void):
M1 L3's PE flip copied → G1 · M2 two powers of S → G1 · M3 r ×100 → G1 and G4 · M4 dte 0 not refused →
G1 · M5 d1 negated → G3. A mutant that leaves its gate passing means that gate cannot fail for its reason.

## 5. Decision rule (fixed now)

`v_dex_repriced_zero` is applied **only if**: G1 passes on all 11 arms; G3, G4 and G5 pass on every
scorable arm; at least **6 of the 10** scoring arms are G4/G5-scorable; and every mutant is caught
(`sstar_gates.py --score` exit 0, `-> APPLY`). Otherwise **DO NOT APPLY**: every failed gate is recorded
as failed — **never loosened, never re-run with a changed threshold** — and S\* waits for an operator
ruling. A gate later judged mis-specified is recorded as mis-specified (S83) and replaced only by a **new**
pre-registration.

If applied: Sections 2–4 of `sql/<date>_s95_v_dex_repriced_zero.sql` are written then — the COMMENT
carrying this gate record verbatim, `REVOKE`/`GRANT` (anon, merdian_ro), and verification SELECTs — with
Section 1 **byte-identical** to `sstar_view_body.sql` (asserted by hash). Board use is a separate operator
decision.

## 6. Procedure

1. Commit this directory; record `git hash-object` of this file. **Nothing below runs before that.**
2. `python3 -I sstar_gates.py --emit-sql <dir>`; run each file through `bin/roq.sh` (merdian_ro,
   read-only, 30 s timeout) into `<data>/`: `arms_resolved.csv`, `chain.csv`, `futures.csv`,
   `calendar.csv`, `view_asof_NN.csv`. Exports stay local (`.gitignore:43`); their sha256 are recorded.
3. `python3 -I sstar_gates.py --score <data>` — output saved whole; the verdict line is the result.

**Validated before commit** (machinery only, says nothing about the market): on local PostgreSQL 16 with
three golden days and **synthetic** futures, the body ran, G1 matched SQL to Python on 8 arms incl. two
dte-0 controls, and all five mutants were caught. The first local run found M1 uncaught by G3 — it is
recorded in §4 and the mutant was reassigned **before** this commit, not after any real-data result.
