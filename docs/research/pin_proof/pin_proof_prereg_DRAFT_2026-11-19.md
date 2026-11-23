# Pin proof: is the Board pin wrong, and what would be right? Pre-registration (DRAFT, 2026-11-19)

**Lane:** engine (Board pin). **Status:** DRAFT for operator approval. Written before any query in it is run. After approval the file is frozen by its sha256; any later change is a new version with its own hash, and a result produced under an older version stays tied to that version.
**Source of the question:** `claude/board_accuracy_discrepancies_2026-11-19.md` (K2, N5, N8, N9, K3), `claude/engine_note_pin_basis_and_vendor_greeks_2026-11-18.md`.
**Order of work (operator, 2026-11-19):** first prove that something is wrong with the pin beyond the observations, then find a fix.
**Authorises nothing in production.** The pin is display-only (ADR-024 §1, S37 GEX-as-context-not-gate).

---

## 1. What the pin claims, and the outside reference

**The Board's own claims.**
- Manual §3.2: PIN (γ-conc) is "the strike with the largest share of gross |γ|".
- The pin card carries the word "dampening" or "amplifying", the strike's own net sign.
- PIN STATE (NO PIN, SHIFTING, STABLE, LOCKED) says how settled the centre is.

**What the code does.** `v_gex_strike_rank` (ENH-125) ranks on `abs(gex_cr)`, where `gex_cr` = call γ·OI minus put γ·OI at the strike, times S²/1e7 (ADR-024 Amendment A §A1). `write_gex_cycle_history_local.py` copies rank 1 into `gex_cycle_history.pin_leader_strike`.

**Outside reference: the absolute gamma strike.** The published industry pin is the strike with the largest total gamma, with call and put gamma added rather than netted (SpotGamma "Absolute Gamma"; Option Alpha "Absolute Gamma"). Industry's netted per-side figures define the walls, not the pin.
- Avellaneda and Lipkin (2003): pinning needs unusually large OI at the strike and hedgers long options in aggregate, and it appears only at the end of the option's life.
- Ni, Pearson and Poteshman (2005): clustering on expiration dates.
- Golez and Jackwerth (2012): futures pulled to the at-the-money strike on expiry days.
- A 2026 SSRN study finds no pinning in S&P 500 expirations from 2016 to 2025. "No pinning" is a live answer.

**Definitions used below** (per `(symbol, run_id)`, front expiry, from `gex_strike_snapshots`):
- **N, the netted pin:** argmax over strikes of `abs(gex_cr)`. Tie-break as in the live `v_gex_strike_rank` definition (read from `sql/` and matched by md5 to `pg_get_viewdef`, Rule 25). Must reproduce `pin_leader_strike` (precondition C1).
- **A, the absolute gamma strike:** argmax of `(gamma_call·oi_call + gamma_put·oi_put)·spot²/1e7`, raw columns. Tie-break: nearer to spot, then lower strike. Known difference from N: the raw columns bypass the deep-in-the-money guard that `gex_cr` carries (TD-NEW-2 Part A). The guard's effect on concentration was measured at most 0.0021 at S79; P-A reports how many runs it touches.
- **L, the net-long strike:** argmax of `gex_cr` over `gex_cr > 0`, i.e. `gamma_metrics.max_gamma_strike` (ADR-024 §A1).
- **M, max pain:** as stored on the run (`gex_cycle_history.max_pain_strike` where present; otherwise recomputed from `gex_strike_snapshots` OI, the recomputation matched to the stored value where both exist).
- **B0, the ATM strike now:** spot at the run rounded to the strike grid.
- **B1, the mirror of N:** 2·B0 − N. Same distance from spot as N, on the other side. It controls for direction luck (a call-wall pin above spot "wins" on any up day).
- **Strike step:** the smallest positive difference between distinct strikes in the run.
- **σ (for distances):** spot × ATM IV/100 × √(max(dte, 1)/252), as in ADR-024 §A4. Distances are reported in strike steps and in σ, never in percent alone.
- **DTE buckets:** 0, 1–2, 3+ (ADR-024 §A4, ADR-011).

## 2. Preconditions (all pass before any statistic)

- **C0. Contamination (Rule 13).** Read `public.data_contamination_ranges` for `gex_strike_snapshots`, `gex_cycle_history`, the spot source and `option_chain_snapshots`. Any overlapping range is excluded and its run count reported.
- **C1. Reconstruction.** On every run where `gex_cycle_history` exists (from 2026-10-06), recomputed N equals `pin_leader_strike`. Must hold on at least 99% of runs per symbol. If not, stop: we would be testing a lookalike. This uses no outcome.
- **C2. Uniform strike grid** within each run. A non-uniform run is reported and excluded.
- **C3. One expiry per run** (`runs_with_multiple_expiries = 0`, ADR-024 §A9).
- **C4. Spot source clock** (P-D only). The spot path for outcomes must agree with the run's own `spot` at the run minute: median absolute difference under one strike step, per symbol. If `hist_spot_bars_1m` is used, it stores IST clock time labelled UTC (CLAUDE.md Rule 16, learnings); `gex_strike_snapshots.ts` is a true timestamp and lags `created_at` by one cycle (TD-S78-NEW-8). The check is what proves the join, not the reasoning.
- **C5. No unresolved read counts as a zero** (Data Inventory method rule 3). A timeout is reported as unmeasured.

## 3. Stage 1: is the construction wrong? (no outcomes read)

Cohort: every front-expiry run with `ts` from 2026-05-25 (first `gex_strike_snapshots` day) to the run date, both symbols, symbol a stratum, never pooled. Each test states what makes it say the pin is fine.

### P-A. Does the pin meet its own and the industry definition?

- **Measure:** share of runs where N = A; distribution of |N − A| in steps and in σ; distance from spot of N and of A (in σ); by DTE bucket. Also: what the denominator "gross" is in the Board's share (read from `v_gex_concentration` source).
- **The pin is fine if** N = A on at least 95% of runs in every DTE bucket for both symbols. *Derivation:* a construction that meets the definition it is described by agrees with it always; the 5% allows for exact ties, the deep-ITM guard and 3-significant-figure gamma storage (03_findings F7). The same 5% is ADR-024 T2's "anchor-neutral" bar.
- **What it cannot see:** whether A is useful. That is P-D.

### P-B. Can the pin be an amplifying strike?

- **Measure:** share of runs where `gex_cr` at N is below zero (the card reads "amplifying"); by DTE bucket; also the share where N and the runner-up have opposite signs (N5).
- **The pin is fine if** N is net short on under 5% of runs. *Derivation:* the pin is named after a mechanism (hedgers long gamma at the strike, Avellaneda and Lipkin) that a net-short strike contradicts; 5% as in P-A.
- **What it cannot see:** whether the dealer sign convention (calls +, puts −) is right for the day. The P2 finding (S94) says it holds only in some regimes. P-B tests the construction against its own convention.

### P-C. Does a known data error move the pin?

- **P-C1, vendor greeks.** Theory: a call and a put at the same strike and expiry share one gamma (engine note §5). Recompute N with one gamma per strike: where both `gamma_call` and `gamma_put` are above zero, both legs use their mean; where one is zero, the run is left as stored (so this test changes one thing, not two). Measure: share of runs where N changes; signed change; by DTE bucket and by day.
- **The pin is fine if** N changes on under 5% of runs. *Derivation:* if the vendor's two gammas agreed, N would change on 0% of runs; the 5% allows for ties and rounding.
- **P-C2, frozen OI (descriptive).** Flag a SENSEX or NIFTY run as frozen when its total call OI and total put OI both equal the session's first post-09:15 run to the share, while spot differs by more than one step (the D6 signature: 392.0L / 296.7L on 19 Nov). Report: number of frozen runs per day, and on frozen runs the share where N differs from the nearest live run's N. No pass/fail; it sizes D6's effect on the pin.
- **What it cannot see:** whether the mean gamma is the right gamma. The engine's own-solve (G1) is the exact version; P-C1 is a solver-free bound.

### Stage 1 reading

Stage 1 says the pin is wrong if any of P-A, P-B or P-C1 fails for either symbol. It names which part is wrong (definition, sign, input), which is what the fix has to address. A pass on all three means the observations were the exception, and Stage 2 still runs as the usefulness check.

## 4. Stage 2: which candidate, if any, does what a pin claims? (outcomes; design period only)

**Design period:** 2026-05-25 to 2026-09-30. **Holdout:** 2026-10-01 to 2026-11-19, sealed. The holdout is read once, after the design result is recorded and the operator rules which candidates go forward. Holdout output goes to the box, never through chat.

**Candidates:** N, A, L, M; and A with one gamma per strike (A-sym) if P-C1 fails. **Baselines:** B0 (ATM strike now) and B1 (mirror of N; for A, L and M the mirror is taken of that candidate).

**Outcomes** (spot path from the C4-checked source):
- **O1, settle (expiry sessions only).** |closing spot on expiry day − K(t)| in strike steps, for runs at 09:30, 11:00, 13:00, 14:30 and 15:00 IST on expiry day, and 15:20 IST on the session before expiry. For each candidate K and each comparator X, the paired difference D = d(K) − d(X), one value per session per time slot.
- **O2, attraction (all sessions).** Over horizons of 30 and 60 minutes from each run: change in distance from spot to K, |S(t+h) − K| − |S(t) − K|, in σ for that horizon. Compared with the same quantity for the candidate's own mirror. Averaged per session first (runs inside a session are not independent; S74 counted sessions).
- **O3, stickiness (expiry sessions, descriptive).** Share of minutes from 14:30 to 15:30 with spot within ±1 step of K, against B0 at 14:30.

**Statistic:** per comparison, the mean of the per-session paired differences, with a 95% session-level bootstrap interval (10,000 resamples, seed fixed in the script and printed) and a sign count. The unit of n is the session.

**Reading, fixed now:**
- A candidate **attracts** on O2 if the upper bound of its interval against its mirror is below zero, in a given DTE bucket and symbol.
- A candidate **beats spot** on O1 at a time slot if the upper bound of its interval against B0 is below zero.
- Anything else is **not shown**. No candidate is called better than another unless its interval against that other excludes zero.
- n is reported on every cell. There is no minimum-n cutoff (operator rule for this lane, 2026-11-17), and any cell under 30 sessions carries ADR-009's "too small to split" label rather than a verdict.

**Strata (reported, never used to select):** DTE bucket; expiry-day hour (09:15–12:00, 12:00–14:30, 14:30–15:30); day type by the ratio of |open-to-close move| to the opening ATM straddle (under 0.5 range, over 1.0 trend, between mixed). Day type uses the outcome day's own move, so it is a reading aid only, never a filter.

**Expected, written now so it can be wrong:** P-A, P-B and P-C1 fail on NIFTY at 3+ DTE. On O1 nothing beats B0 before 14:30 on expiry day. If any construct attracts, it is A in the 14:30–15:30 slot. Direction luck shows as N beating B1 on trend-up days and losing on trend-down days.

## 5. What a result authorises

- Stage 1 failing authorises **writing the fix options up against the failure** (R1/R2 basis, G1/G2 greeks, T2 hysteresis and tie state, a sign-aware pin), not building one.
- Stage 2 decides which candidate is taken to the holdout. The holdout result is the evidence a basis change (R2) or a relabel needs; an ADR-024 amendment and restated pre-registrations (engine note §7: H-C, P1d) follow from it.
- Nothing here changes a view, a table, a writer or a Board label.

## 6. Who runs what

- Claude Code on the engine box, rooted in `~/meridian-cc`, read-only through `bin/roq.sh` as `merdian_ro`, under `ulimit -v 700000`, outside 08:30–15:40 IST on trading days.
- Stage 1 first. Stage 2 only after the operator approves this file and reads Stage 1.
- Output goes to `~/meridian-cc/docs/research/pin_proof/`, uncommitted until the operator says so.
- Any read `merdian_ro` cannot make is reported by relation name; the operator is given SQL to run instead.
