# ADR-009 Pre-Registration — Do price paths respect the ENH-81 PIN and ACCEL zones as shipped?

| Field | Value |
|---|---|
| **Status** | **Pre-registered. Not run.** No measurement has been taken against this design. Every commitment below is binding before the first query. |
| **Date** | 2026-09-07 (Session 74) |
| **Discipline** | ADR-009 Phase 1, **N ≥ 60 tier** (67% calibration / 33% holdout). Tolerance column does not transfer — see §5, Pre-commitment 5. |
| **Question** | Does the index price path respect the pin and accel zones produced by `v_gex_strike_pin_zone` / `v_gex_strike_accel_zone` as those views exist after 2026-09-05? |
| **Prior** | **OPEN.** Not "probably no". See §2. |
| **Decision attached** | ADR-023 D1 **Decision B** — the floor value and, behind it, whether PIN/ACCEL warrant a scheduled overlay at all. Decision A (the `52 10 * * 1-5` invoker) was taken S72; B was deferred here. |
| **Primary N** | **67 sessions**, NIFTY. Not 72, not 250+. Derivation in §4. |
| **Related** | ADR-009 (this discipline), ADR-021 + Amendment 1 (the views' scoping and the τ defect), ADR-023 + Amendment 1 (recency floors, consumer cadence), ADR-015 (`gex_strike_snapshots` schema), ADR-022 (CAS close timing), ADR-016 (`merdian_parameters`, τ storage), ADR-001 (stable lies), `docs/research/s72_gex_view_fix.sql` (the shipped walk). |

---

## 1. What this document is

A pre-registration, not a result. It fixes the cohort, the unit of observation, the statistic, the null model, the split, and the verdict rule **before** any of them can be chosen in the light of an answer.

It exists because this study is unusually easy to win by accident. Pin zones are built by walking outward from the maximum-positive-GEX strike, and that strike sits near spot. A naive "price stayed near the zone" statistic would therefore be substantially true by construction, in a way that has nothing to do with dealer positioning. The null model in Pre-commitment 4 is the whole defence, and it has to be fixed in advance or it becomes a dial.

---

## 2. Context — why the prior is OPEN and not "no"

The operator's standing observation is that price does not visibly respect the accel zone on the chart. **That observation cannot count as evidence either way, in either direction**, for two independent reasons, both of which are documented and both of which resolve on the same date.

**(a) τ was decorative until 2026-09-05.** ADR-021 Amendment 1 §A1.6: the recursive walk in both views tested a hardcoded `0.3` while the output column `tau_used` separately resolved `get_parameter_num('pin.tau.'||symbol)`. The knob was wired to the label, not to the computation. The live proof is in `s72_gex_view_fix.sql` §5: `pin.tau.NIFTY` was set to 0.25 on 2026-05-27 and reverted roughly thirty seconds later by an operator who saw nothing move — because nothing did. Every zone rendered before 2026-09-05 came from a walk whose threshold was fixed regardless of what the parameter table or the chart label said.

**(b) PIN was intermittently absent from the artefact.** ADR-021 Amendment 1 §A1.2: `57014` statement timeouts on `v_gex_strike_pin_zone` on 2026-08-28 and 2026-08-31, both first-call-of-the-morning cold-cache runs. ADR-023 Amendment 1 §A1.3: each failure produced a Pine overlay carrying ACCEL, **no PIN**, and an as-of stamp inherited from the surviving side. "No pin zone today" was a legitimate reading of those files. An observer looking at overlays in that window was, some of the time, looking at an artefact that asserted complete positioning while half was missing.

Both were corrected on 2026-09-05 (ADR-021 A1.4 and A1.6, equivalence-gated at zero rows).

**Therefore: no assessment of zone utility formed before 2026-09-05 measured the shipped implementation.** Impressions from that period are impressions of a different object. They are not disqualified as observations; they are disqualified as evidence about the thing under test. The prior is open.

A third, weaker point in the same direction: `generate_pine_overlay.py` had **no scheduled invoker** between the S70 migration and S72 (TD-S71-NEW-7), so overlay generation in that window was manual and irregular. Exposure to the artefact was itself intermittent.

---

## 3. Study bounds

**Ceiling is a timestamp, never a row count.** `gex_strike_snapshots` was measured at 1,412,989 rows and again at 1,417,090 rows within hours on 2026-09-05. A bound stated as a row count has an invisible expiry date — the ADR-021 A1.2 lesson, in the same table.

```
Study ceiling:  ts <  TIMESTAMPTZ '2026-09-05 00:00:00+00'
Study floor:    ts >= TIMESTAMPTZ '2026-05-25 00:00:00+00'
```

The floor is the ENH-80 writer's first day (ADR-015, Session 37). The ceiling is midnight before the S72 view correction landed, so the cohort is entirely pre-correction *data* — which is correct and intended: `gex_strike_snapshots` is the raw substrate and was never affected by the τ or scoping defects. Only the **views over it** were. The reconstruction in §7 applies the corrected walk to the whole substrate.

---

## 4. Eligibility — stated as a rule, with the arithmetic shown

**Rule.** A session is eligible iff it is an open day in `trading_calendar` within the study bounds, **and** carries at least one `gex_strike_snapshots` run for the symbol, **and** carries a usable in-window price path in `market_spot_snapshots`.

Applied:

| Step | Sessions |
|---|---:|
| `trading_calendar` open days, 2026-05-25 → 2026-09-04 | 72 |
| − 2026-06-03, 2026-06-04, 2026-06-08 (no GEX rows) | −3 |
| − 2026-06-11 (3 spot rows; no usable price path) | −1 |
| − 2026-06-26 (closed holiday; see §10) | −1 |
| **Eligible** | **67** |

**This supersedes the 72 in the tasking**, which came from `count(distinct ts::date)` on `gex_strike_snapshots` alone. The joint requirement — GEX geometry *and* a price path to test it against — is what reduces it. Both figures refute the "250+ sessions" that appeared in the session brief; that number is the age of the *table's index*, not of this cohort.

The eligibility rule is executable and must be re-run at study time rather than trusting this table. If the counts differ, the rule wins and the discrepancy is recorded.

---

## 5. Pre-commitments

Binding. Any departure is a new pre-registration, not an amendment to this one.

### 1 — The unit of observation is the session, not the cycle-row

There are ~83 GEX runs per symbol per session. 67 × 83 × 2 ≈ 11,100 cycle-rows. Treating those as independent observations is a multiple-comparisons machine: consecutive runs five minutes apart share nearly all their strikes, nearly all their OI, and the same spot to within a few points. **Each session collapses to one scalar per arm.** N = 67, and it does not become 11,100 by looking at it differently.

### 2 — Symbol is a stratum, not an N multiplier

NIFTY and SENSEX on the same date are near-collinear: same macro, same session, overlapping constituents. **Primary N = 67, NIFTY.** SENSEX is a quasi-replication check, reported alongside and never pooled to claim N = 134. If SENSEX contradicts NIFTY that is a finding to state, not a tie to break by averaging.

### 3 — Chronological split, 45 calibration / 22 holdout

Boundary **2026-08-05 / 2026-08-06**: sessions on or before 08-05 are calibration, from 08-06 are holdout. Random splitting leaks regime — a random 33% holdout drawn from a period containing one volatility regime shift is not out-of-sample in the only sense that matters.

45/67 = 67.2%, 22/67 = 32.8%. This independently lands on ADR-009's **N ≥ 60 tier (67/33)**; the split was derived from the calendar and then found to match, not chosen to match.

### 4 — The primary metric is real-minus-null, against a session-shuffled, spot-matched null

**Non-negotiable, and the reason this document exists.** Pin zones are anchored to the maximum-positive-GEX strike, which sits near spot; accel zones to the most-negative, likewise. Any statistic of the form "price stayed near the zone" is therefore partly tautological. Without breaking the zone↔spot link, the study measures its own construction and returns a confident yes.

**Null construction.** For each recipient session *r*, donor zones are drawn from other sessions *d* of the same symbol subject to all of:

- **spot match** — `abs(d.ref_spot − r.open_spot) <= 0.005 * r.open_spot` (±0.5%), where `d.ref_spot` is the `spot` recorded on the donor's GEX run and `r.open_spot` is the first in-window price of the recipient session. This holds "zone is near a plausible spot level" constant and varies only "zone is *this* session's structure";
- **temporal separation** — donor and recipient at least 4 sessions apart in the eligible sequence, to avoid autocorrelated structure;
- **not itself** — `d ≠ r`.

The null statistic for *r* is the **mean over all qualifying donors**, not a single random draw. This makes the null deterministic and exactly reproducible with no RNG seed, and it reduces null variance without any tuning.

If a recipient session has **zero qualifying donors** (plausible in a strong trend, where no other session opened within ±0.5%), that session is **dropped from the primary analysis and the count is reported**. It is not rescued by widening the band after the fact.

### 5 — The verdict rule, and why ADR-009's tolerance column does not transfer

**Verdict is "no" if either:**
- the holdout paired effect's 95% CI **includes zero**; or
- the holdout point estimate is **less than half** the calibration point estimate.

**ADR-009's Phase 1 tolerance column ("holdout WR within 10pp of calibration WR") does not apply here and is explicitly replaced.** That column presumes a win-rate on both sides of the split, so that a holdout WR can sit within 10pp of a calibration WR. This study has no win rate. Its estimand is a paired difference between a real statistic and a null statistic, in units of session-time-fraction (PIN) and of a dimensionless velocity ratio (ACCEL). There is no calibration WR for a holdout WR to be near. The two-part rule above is the substitute: the first clause tests that the effect exists out of sample, the second that it has not collapsed. The split ratio, cohort tiering and the ship/no-ship consequence are taken from ADR-009 unchanged.

**CI construction, fixed in advance:** nonparametric bootstrap over sessions (the unit of Pre-commitment 1), 10,000 resamples, percentile interval, **seed 20260907**. Reported to three significant figures.

**Exactly two primary tests:** PIN-NIFTY and ACCEL-NIFTY. Everything else in this document — SENSEX, DTE strata, τ sweeps, the contemporaneous alignment — is descriptive and cannot produce a verdict.

### 6 — τ = 0.3 only

0.3 is what shipped, both as the hardcoded literal before 2026-09-05 and as the live `pin.tau.*` / `accel.tau.*` values after. **Any τ sweep is exploratory, reported in a clearly separated section, and never the headline.** A sweep that finds a better τ has found a parameter to pre-register a *new* study around, under ADR-016 and ADR-009 — not a result.

### 7 — Vol-regime conditioning is excluded by data defect, and this is recorded so that its absence is not read as a negative test

`vix_percentile` is scored against a reference distribution frozen since **2026-03-11**: `india_vix_history` has had no writer since that date (TD-S70-NEW-4), and the S71 source-selection instrumentation returned `age_days=164` on the surviving window. Every regime label over this entire cohort is computed against a five-month-old distribution. Conditioning on it would produce a stratification that is confidently wrong rather than absent.

**Recorded explicitly: vol-regime is untested, not tested-and-null.** If the writer is restored, this is the first extension to pre-register.

**DTE is a stratum, not a conditioning variable.** Results are reported by DTE bucket for description; the verdict is computed on the pooled cohort. Choosing a DTE bucket after seeing the strata is the failure this rule prevents.

### 8 — Price path: `market_spot_snapshots`, 03:45–09:45 UTC, half-open

**Window: `[03:45, 09:45) UTC` = `[09:15, 15:15) IST`** — the market open to the ADR-022 continuous-trading close for Category-I instruments.

**Excluding the 15:15–16:00 plateau is mandatory, not cosmetic.** Per ADR-022 D2 and the S70 finding: NIFTY and SENSEX are *computed* from constituents, so while those constituents are in the closing auction the index has no continuous input and simply repeats its 15:14 value — carrying that bar's volume forward, which is why `is_filler_bar()` never fires on it. Those minutes are not price discovery. Including them injects roughly twenty artificially flat minutes into **every** session, and flat price near a zone reads as "contained" — a bias pointing directly at the hypothesis under test, in the direction that would confirm it. The plateau is excluded on the ground that it is not evidence about respect, whichever way it would have pointed.

**Dedupe by minute, with the winner pre-committed.** `market_spot_snapshots` receives from two writers: `capture_spot_1m_v2.py` (`source_table = 'dhan_charts_intraday'`, a real 1-minute OHLC bar) and `capture_market_spot_snapshot_local.py` (`source_table = 'dhan_idx_i'`, an LTP tick at capture time). Where both cover the same `date_trunc('minute', ts)`:

> **`dhan_charts_intraday` wins. `dhan_idx_i` fills only minutes the bar feed does not cover.**

Rationale: the bar close is tied to the minute boundary deterministically, whereas the LTP tick lands wherever the cron happened to fire within the minute; and the bar feed is the same source ADR-022's settled-close work is anchored on. Ties within a source resolve to the later `ts`. Rows with `spot IS NULL` are dropped and counted.

Per the `merdian_reference.json` critical rule for this table: **it has no `trade_date` column**; session date is `(ts AT TIME ZONE 'Asia/Kolkata')::date` throughout.

### 9 — Zone width: every zone is buffered by half the strike step

A zone is a *set of strikes*, and a strike is a point sample of a price continuum whose resolution is the grid step. A single-strike zone is therefore **one strike wide, not zero-width** — the S72 §5 observation recorded a NIFTY pin at `n_strikes = 5`, and the SENSEX pin on the same day was `n_strikes = 1` with `pin_lower = pin_upper = 77000`.

**The buffer is `step / 2` on each side, applied uniformly to every zone**, degenerate or not. It is the grid resolution, not a patch for degeneracy, and applying it only to single-strike zones would make zone width discontinuous in `n_strikes`.

`step` is computed per run by the same `strike_step` CTE the live views use (minimum positive lag-difference in `strike`), **not hardcoded**. An assertion fails the run loudly if `step ∉ {50}` for NIFTY or `step ∉ {100}` for SENSEX on any study run. Under that grid the buffer is 25 and 50 points respectively.

**Front-expiry contingency.** The views group by `expiry_date`, so a run carrying two expiries yields two zones. 83 of 83 runs carried exactly one expiry — but that was **measured on a single session**, so it is a weak prior and not a licence. Pre-committed rule: where a run carries more than one `expiry_date`, take the **nearest `expiry_date >= ` the run's IST session date** (the front). The number of affected runs is reported whether it is zero or not.

### 10 — *Added here, not in the tasking:* the primary alignment is prior-session zones on current-session path

This pre-commitment is **an addition made while writing this document**, flagged as such so the operator can strike it. It is included because leaving it open would let the analyst choose the alignment after seeing the data, which is precisely what a pre-registration exists to prevent.

`generate_pine_overlay.py` runs at `52 10 * * 1-5` (16:22 IST, ADR-023 D1 Decision A). The zones an operator can act on during session *d* are therefore those computed from the **last GEX run of session *d−1***. Measuring session *d*'s own zones against session *d*'s own path tests a zone the operator never had — a look-ahead of up to a full session.

> **Primary: lag-1. The zone geometry from the last eligible-session run before *d*, applied to *d*'s path.** The null of Pre-commitment 4 shuffles the same lag-1 pairing.
>
> **Secondary, exploratory, never the headline: contemporaneous** (session *d*'s zones on *d*'s path).

This is ADR-023 Amendment 1 §A1.2's finding applied one level along: the floor is calibrated against the consumer's cadence, not the writer's — and so is the alignment. The tasking's null construction ("session *d*'s zones applied to session *d+k*'s path") is alignment-agnostic and works unchanged under either.

---

## 6. The statistics

Two arms, two mechanisms, two statistics. They are **not combined into a composite** and each carries its own verdict.

**PIN — containment.** For a session, the fraction of in-window minutes with

```
spot BETWEEN pin_lower - step/2 AND pin_upper + step/2
```

Hypothesis: real > null. A session with zero minutes inside is a legitimate `0.0`, not undefined.

**ACCEL — velocity.** For a session, the ratio

```
mean(|Δspot per minute| while inside the buffered accel band)
--------------------------------------------------------------
mean(|Δspot per minute| while outside it)
```

Dimensionless, so it is comparable across symbols and across price levels without normalisation. Hypothesis: real ratio > null ratio — price traverses the accel band faster than it moves elsewhere in the same session.

**Guard:** a session with zero in-window minutes inside the accel band, or zero outside it, yields an undefined ratio, is **excluded from the ACCEL arm**, and the exclusion count is reported. It is not imputed.

---

## 7. Preconditions — numbered, all must pass before any statistic is computed

**P1 — Equivalence gate. Zero rows, or nothing downstream counts.**

The reconstruction in §8 must be shown to be *the shipped walk* before it is trusted on historical runs. Instantiate `study_runs` in **gate mode** (the two latest runs, mirroring the live lateral) and take the symmetric difference against each live view:

```sql
-- Expect ZERO rows. Pin.
(SELECT 'new_not_in_old' AS side, * FROM recon_pin
 EXCEPT ALL SELECT 'new_not_in_old', * FROM public.v_gex_strike_pin_zone)
UNION ALL
(SELECT 'old_not_in_new', * FROM public.v_gex_strike_pin_zone
 EXCEPT ALL SELECT 'old_not_in_new', * FROM recon_pin);

-- Expect ZERO rows. Accel.
(SELECT 'new_not_in_old' AS side, * FROM recon_accel
 EXCEPT ALL SELECT 'new_not_in_old', * FROM public.v_gex_strike_accel_zone)
UNION ALL
(SELECT 'old_not_in_new', * FROM public.v_gex_strike_accel_zone
 EXCEPT ALL SELECT 'old_not_in_new', * FROM recon_accel);
```

Any non-empty result means the reconstruction is not the shipped walk. **Stop.** Do not reason about which side is right — that is the S72 instruction and it holds here.

**P2 — τ liveness precondition for P1.** The reconstruction hardcodes `0.3` (Pre-commitment 6) while the live views resolve `COALESCE(get_parameter_num(...), 0.3)`. **P1 is only valid while all four `pin.tau.NIFTY`, `pin.tau.SENSEX`, `accel.tau.NIFTY`, `accel.tau.SENSEX` active rows hold `value_num = 0.30`.** Verify first:

```sql
SELECT key, value_num FROM public.merdian_parameters
 WHERE key IN ('pin.tau.NIFTY','pin.tau.SENSEX','accel.tau.NIFTY','accel.tau.SENSEX')
   AND valid_to IS NULL
 ORDER BY key;
```

Four rows, all `0.30`, or P1 is meaningless and the reconstruction must resolve the parameter instead of hardcoding it.

**P3 — Gate runs while the GEX writer is idle.** Outside 03:00–10:10 UTC, or the reconstruction and the live view read different runs and the diff is noise. Same constraint as `s72_gex_view_fix.sql`.

**P4 — Grid assertion.** `step ∈ {50}` for NIFTY, `{100}` for SENSEX on every study run (Pre-commitment 9). Fail loudly.

**P5 — Eligibility re-derivation.** Re-run the §4 rule. If N ≠ 67, the rule wins and the discrepancy is recorded before proceeding.

**P6 — Multi-expiry count.** Report the number of study runs carrying more than one `expiry_date`, including when it is zero (Pre-commitment 9).

**P7 — One spot per run. Fail loudly.**

```sql
-- Expect ZERO rows.
SELECT run_id, symbol, count(DISTINCT spot) AS n_spot
  FROM gex_strike_snapshots
 WHERE ts >= TIMESTAMPTZ '2026-05-25 00:00:00+00'
   AND ts <  TIMESTAMPTZ '2026-09-05 00:00:00+00'
 GROUP BY run_id, symbol
HAVING count(DISTINCT spot) <> 1;
```

`zone_ref` reads `ref_spot` via `SELECT DISTINCT g.spot … LIMIT 1` **with no `ORDER BY`**, so if any run ever carries more than one `spot` the planner picks one arbitrarily and the choice is not stable across executions. `ref_spot` is the quantity the **entire null model matches on** (Pre-commitment 4, ±0.5%), so an arbitrary pick there silently reshuffles which donors qualify for every recipient session — a nondeterministic null wearing a deterministic construction's authority.

Same shape as P4: a uniformity the writer almost certainly guarantees, asserted rather than assumed, because the failure is silent and the quantity is load-bearing. If P7 fails, the `LIMIT 1` must be replaced with an explicit rule (pre-committed before inspection) rather than left to the planner.

---

## 8. Reconstruction SQL

The **only** difference between gate mode and study mode is the body of the leading `study_runs` CTE. Everything below it is byte-identical between the two, which is what makes P1 informative: if the gate passes, the study query differs from the shipped view by exactly one CTE.

Column names follow `docs/research/s72_gex_view_fix.sql` and the live schema
`gex_strike_snapshots (id, run_id, symbol, ts, expiry_date, dte, strike, spot, oi_call, oi_put, gex_cr, created_at, gamma_call, gamma_put)`.[^schema]

### 8.1 — `study_runs`, gate mode

```sql
-- GATE MODE. Mirrors the live views' lateral exactly (ADR-021 A1.4).
WITH RECURSIVE study_runs AS (
    SELECT s.symbol, lr.run_id, lr.ts
      FROM (VALUES ('NIFTY'), ('SENSEX')) AS s(symbol)
      CROSS JOIN LATERAL (
           SELECT g.run_id, g.ts
             FROM gex_strike_snapshots g
            WHERE g.symbol = s.symbol
            ORDER BY g.ts DESC
            LIMIT 1
      ) lr
)
```

### 8.2 — `study_runs`, study mode

```sql
-- STUDY MODE. One run per symbol per session: the LAST run of the session,
-- which is the geometry the 16:22 IST overlay carries into the next morning
-- (Pre-commitment 10). Ceiling is a timestamp, never a row count (ADR-021 A1.2).
WITH RECURSIVE study_runs AS (
    SELECT DISTINCT ON (g.symbol, (g.ts AT TIME ZONE 'Asia/Kolkata')::date)
           g.symbol,
           g.run_id,
           g.ts,
           (g.ts AT TIME ZONE 'Asia/Kolkata')::date AS zone_date
      FROM gex_strike_snapshots g
     WHERE g.ts >= TIMESTAMPTZ '2026-05-25 00:00:00+00'
       AND g.ts <  TIMESTAMPTZ '2026-09-05 00:00:00+00'
     ORDER BY g.symbol,
              (g.ts AT TIME ZONE 'Asia/Kolkata')::date,
              g.ts DESC
)
```

### 8.3 — the walk (identical in both modes)

```sql
, scoped AS (
    SELECT g.id, g.run_id, g.symbol, g.ts, g.expiry_date, g.dte,
           g.strike, g.spot, g.oi_call, g.oi_put, g.gex_cr,
           g.created_at, g.gamma_call, g.gamma_put
      FROM gex_strike_snapshots g
      JOIN study_runs sr ON g.symbol = sr.symbol AND g.run_id = sr.run_id
), strike_step AS (
    SELECT x.run_id, x.symbol, x.expiry_date, min(x.diff) AS step
      FROM ( SELECT scoped.run_id, scoped.symbol, scoped.expiry_date,
                    scoped.strike - lag(scoped.strike) OVER (
                        PARTITION BY scoped.run_id, scoped.symbol, scoped.expiry_date
                        ORDER BY scoped.strike) AS diff
               FROM scoped ) x
     WHERE x.diff > 0::numeric
     GROUP BY x.run_id, x.symbol, x.expiry_date
), peak AS (
    SELECT DISTINCT ON (scoped.run_id, scoped.symbol, scoped.expiry_date)
           scoped.run_id, scoped.symbol, scoped.expiry_date, scoped.ts, scoped.spot,
           scoped.strike AS peak_strike,
           scoped.gex_cr AS peak_gex_cr,
           0.3::numeric  AS tau           -- Pre-commitment 6; see P2
      FROM scoped
     WHERE scoped.gex_cr > 0::numeric
     ORDER BY scoped.run_id, scoped.symbol, scoped.expiry_date,
              scoped.gex_cr DESC, (abs(scoped.strike - scoped.spot))
), walk AS (
    SELECT p.run_id, p.symbol, p.expiry_date, p.ts,
           p.peak_strike AS strike, p.peak_gex_cr AS gex_cr,
           p.peak_gex_cr, p.tau, s.step, 0 AS direction
      FROM peak p
      JOIN strike_step s USING (run_id, symbol, expiry_date)
    UNION ALL
    SELECT g.run_id, g.symbol, g.expiry_date, g.ts,
           g.strike, g.gex_cr, w_1.peak_gex_cr, w_1.tau, w_1.step,
           CASE WHEN g.strike < w_1.strike THEN '-1'::integer ELSE 1 END
      FROM walk w_1
      JOIN scoped g
        ON g.run_id = w_1.run_id AND g.symbol = w_1.symbol
       AND g.expiry_date = w_1.expiry_date
       AND ( (w_1.direction = ANY (ARRAY[0, '-1'::integer]))
             AND abs(g.strike - (w_1.strike - w_1.step)) < 0.0001
          OR (w_1.direction = ANY (ARRAY[0, 1]))
             AND abs(g.strike - (w_1.strike + w_1.step)) < 0.0001 )
     WHERE g.gex_cr > 0::numeric
       AND g.gex_cr >= (w_1.tau * w_1.peak_gex_cr)
)
SELECT run_id, symbol, expiry_date,
       max(ts)                                     AS ts,
       min(strike)                                 AS pin_lower,
       max(strike)                                 AS pin_upper,
       count(*)                                    AS n_strikes,
       sum(gex_cr)                                 AS total_pin_gex_cr,
       max(peak_gex_cr)                            AS peak_pin_gex_cr,
       (array_agg(strike ORDER BY gex_cr DESC))[1] AS peak_pin_strike,
       max(tau)                                    AS tau_used
  FROM walk w
 GROUP BY run_id, symbol, expiry_date;
```

The ACCEL reconstruction is the same body with `peak` → `trough` (`DISTINCT ON … WHERE gex_cr < 0 ORDER BY … gex_cr ASC`), the recursive predicate `abs(g.gex_cr) >= w_1.tau * abs(w_1.trough_gex_cr)`, and the S72 output column names `accel_lower`, `accel_upper`, `total_accel_gex_cr`, `trough_gex_cr`, `trough_strike`, `tau_used`.

Materialise four temp tables in study mode, so §9 can join against them without re-walking: `recon_pin`, `recon_accel`, `study_runs_materialised` (the `study_runs` CTE body, carrying `zone_date`), and `strike_step_materialised` (the `strike_step` CTE body, carrying `step` for the Pre-commitment 9 buffer). In gate mode only `recon_pin` / `recon_accel` are needed.

---

## 9. Null-model SQL

```sql
-- ---------------------------------------------------------------------------
-- Price path. Half-open [09:15, 15:15) IST (Pre-commitment 8). The 15:15-16:00
-- CAS plateau is excluded: the index is frozen at its 15:14 value through the
-- auction (ADR-022), so those minutes are not price discovery, and including
-- them would add ~20 flat minutes per session to a time-in-zone statistic.
-- market_spot_snapshots has NO trade_date column (merdian_reference.json).
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE path AS
SELECT symbol, session_date, minute_utc, spot
  FROM (
    SELECT m.symbol,
           (m.ts AT TIME ZONE 'Asia/Kolkata')::date AS session_date,
           date_trunc('minute', m.ts)               AS minute_utc,
           m.spot,
           row_number() OVER (
             PARTITION BY m.symbol, date_trunc('minute', m.ts)
             ORDER BY CASE m.source_table
                        WHEN 'dhan_charts_intraday' THEN 0   -- bar close wins
                        WHEN 'dhan_idx_i'           THEN 1   -- LTP tick fills
                        ELSE 2 END,
                      m.ts DESC
           ) AS rk
      FROM market_spot_snapshots m
     WHERE m.ts >= TIMESTAMPTZ '2026-05-25 00:00:00+00'
       AND m.ts <  TIMESTAMPTZ '2026-09-05 00:00:00+00'
       AND m.spot IS NOT NULL
       AND (m.ts AT TIME ZONE 'Asia/Kolkata')::time >= TIME '09:15'
       AND (m.ts AT TIME ZONE 'Asia/Kolkata')::time <  TIME '15:15'
  ) x
 WHERE rk = 1;

-- ---------------------------------------------------------------------------
-- Eligible sessions, indexed in chronological order (§4, P5).
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE eligible AS
SELECT p.symbol,
       p.session_date,
       row_number() OVER (PARTITION BY p.symbol ORDER BY p.session_date) AS sess_ix,
       (array_agg(p.spot ORDER BY p.minute_utc))[1] AS open_spot,
       count(*) AS n_minutes
  FROM path p
 GROUP BY p.symbol, p.session_date;

-- ---------------------------------------------------------------------------
-- Zone reference. One row per (symbol, zone_date): the session's closing zone
-- geometry, plus the spot recorded on that run, which is the quantity the null
-- matches on. `step` is carried from strike_step for the Pre-commitment 9
-- buffer. Front expiry already resolved per P6.
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE zone_ref AS
SELECT sr.symbol,
       sr.zone_date,
       sr.run_id,
       sc.spot        AS ref_spot,     -- spot on the zone's own run
       rp.pin_lower,  rp.pin_upper,
       ra.accel_lower, ra.accel_upper,
       ss.step
  FROM study_runs_materialised sr
  JOIN LATERAL (SELECT DISTINCT g.spot FROM gex_strike_snapshots g
                 WHERE g.run_id = sr.run_id AND g.symbol = sr.symbol
                 LIMIT 1) sc ON TRUE
  JOIN strike_step_materialised ss ON ss.run_id = sr.run_id AND ss.symbol = sr.symbol
  LEFT JOIN recon_pin   rp ON rp.run_id = sr.run_id AND rp.symbol = sr.symbol
  LEFT JOIN recon_accel ra ON ra.run_id = sr.run_id AND ra.symbol = sr.symbol;

-- A run may legitimately produce no pin zone (no positive gex_cr) or no accel
-- zone (no negative). Those are NULL here, and the session is excluded from
-- that arm only — never from both, and never imputed. Counts reported.

-- ---------------------------------------------------------------------------
-- REAL pairing. Lag-1: the zone from the last eligible session BEFORE the path
-- session, which is what the 16:22 IST overlay carries (Pre-commitment 10).
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE real_pair AS
SELECT e.symbol, e.session_date AS path_date, z.zone_date
  FROM eligible e
  JOIN eligible zp ON zp.symbol = e.symbol AND zp.sess_ix = e.sess_ix - 1
  JOIN zone_ref  z ON z.symbol  = e.symbol AND z.zone_date = zp.session_date;

-- ---------------------------------------------------------------------------
-- NULL pairing. Donor zones from spot-matched, temporally separated sessions.
-- Deterministic: every qualifying donor is used and averaged, so there is no
-- RNG and no seed to record for this step (Pre-commitment 4).
-- ---------------------------------------------------------------------------
CREATE TEMP TABLE null_pair AS
SELECT r.symbol,
       r.session_date AS path_date,
       d.zone_date    AS donor_zone_date
  FROM eligible r
  JOIN zone_ref d
    ON d.symbol = r.symbol
   AND d.zone_date <> r.session_date
   AND abs(d.ref_spot - r.open_spot) <= 0.005 * r.open_spot      -- ±0.5% spot match
  JOIN eligible de
    ON de.symbol = r.symbol AND de.session_date = d.zone_date
 WHERE abs(de.sess_ix - r.sess_ix) > 3;                          -- ≥4 sessions apart

-- Sessions with zero qualifying donors are dropped from the primary analysis
-- and COUNTED. The ±0.5% band is not widened after inspection.
SELECT e.symbol, count(*) AS sessions_without_donor
  FROM eligible e
  LEFT JOIN null_pair n
    ON n.symbol = e.symbol AND n.path_date = e.session_date
 WHERE n.path_date IS NULL
 GROUP BY e.symbol;

-- ---------------------------------------------------------------------------
-- PIN statistic, applied identically to real_pair and null_pair.
-- ---------------------------------------------------------------------------
-- pin_time_frac(pairing) =
--   avg over the session's minutes of
--     (spot BETWEEN pin_lower - step/2 AND pin_upper + step/2)::int
--   joining path -> pairing -> zone_ref on (symbol, zone_date)
--
-- Session-level paired effect:
--   delta_pin(s) = pin_time_frac_real(s) - mean_over_donors(pin_time_frac_null(s))

-- ---------------------------------------------------------------------------
-- ACCEL statistic, applied identically to real_pair and null_pair.
-- ---------------------------------------------------------------------------
WITH stepped AS (
  SELECT p.*,
         abs(p.spot - lag(p.spot) OVER (
             PARTITION BY p.symbol, p.session_date ORDER BY p.minute_utc)) AS dmove
    FROM path p
)
-- accel_velocity_ratio =
--   avg(dmove) FILTER (WHERE inside_accel_band)
--   / NULLIF(avg(dmove) FILTER (WHERE NOT inside_accel_band), 0)
-- NULL ratio (no minutes inside, or none outside) => session EXCLUDED from the
-- ACCEL arm and counted (§6). Never imputed.
SELECT 1;
```

**Effect and CI.** For each arm: the paired per-session differences (real − null) over the **holdout** 22 sessions, NIFTY. Point estimate = mean. Interval = percentile bootstrap over sessions, 10,000 resamples, **seed 20260907**. Calibration 45 reported alongside for the second clause of the verdict rule.

---

## 10. Separate finding, recorded and not investigated

**2026-06-26 is a closed holiday in `trading_calendar` and carries 4,380 `gex_strike_snapshots` rows against zero `market_spot_snapshots` rows.** The GEX writer ran a full session's worth of cycles on a closed market while the spot capture correctly did not. That is the Rule 18 holiday-gate shape — a writer with no gate, or a gate that fail-opened — and it is adjacent to TD-S72-NEW-10.

It is out of scope here and is **not** investigated in this document. Its only bearing on the study is that the session is excluded by §4, which it would be regardless, on the price-path requirement alone.

---

## 11. What a "yes" would and would not authorise

A holdout effect surviving §5 Pre-commitment 5 supports **ADR-023 D1 Decision B**: that PIN/ACCEL carry enough information to justify the scheduled overlay, the recency floor, and the maintenance cost of the views.

It does **not** authorise wiring GEX into `build_trade_signal_local.py`. That remains settled by the S37 GEX-as-context-not-gate decision — the operator is the integration layer, and any gate would additionally require its own N ≥ 30 live-runtime-cohort validation under the ADR-009 cohort-prior-gate-hazard sub-rule. This study measures a display surface's informativeness, not a gate's edge.

A "no" is equally useful and equally publishable: it would make the case for retiring the overlay boxes rather than continuing to floor, schedule, and maintain them.

---

## 12. Caveats fixed in advance

- **The null controls for spot level, not for regime.** A donor matched at ±0.5% of the recipient's open may come from a different volatility regime. Vol-regime conditioning is unavailable (Pre-commitment 7), so this residual is stated rather than removed.
- **Lag-1 is the consumer's alignment, but the operator may also read the intraday Marketview surface**, which is contemporaneous. The secondary contemporaneous arm exists for that reason and is descriptive only.
- **`step/2` assumes a uniform grid within a run.** P4 asserts it; a run with a non-uniform grid fails loudly rather than being silently buffered wrong.
- **Minute-level path resolution understates intrabar excursion.** A wick through a zone boundary and back within one minute is invisible. This biases *against* detecting accel-band traversal and *toward* pin containment — i.e. it is not neutral, and its direction is opposite between the two arms. Recorded, not corrected.
- **The reconstruction is validated against the views only at the latest run (P1).** Passing there is strong evidence it is the shipped walk, but it is not a proof over all historical runs; no such comparison is possible, because the views only ever expose the latest run.
- **Ceilings are timestamps.** Any figure in a result document derived from this pre-registration that is stated as a row count is a defect in that document.

[^schema]: `merdian_reference.json` records the ADR-015 as-designed schema for this table as `(… oi_total_calls integer, oi_total_puts integer …, source_table text)`, without `id`, `dte` or `created_at`. The live column names used by `s72_gex_view_fix.sql` are `oi_call` / `oi_put`. A documentation discrepancy observed by reading the two files side by side; noted here so the next reader does not resolve it by guessing, and not investigated in this document.

---

*Pre-registered 2026-09-07, Session 74, under ADR-009 Phase 1. Nothing in this document has been measured. Pre-commitment 10 was added during drafting and is flagged as such. The value of a pre-registration is entirely in its being written before the answer is known — an amendment made after the first result is a new study, not a revision of this one.*
