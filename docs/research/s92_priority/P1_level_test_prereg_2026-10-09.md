# P1 pre-registration — Do the session's high and low land at MERIDIAN's levels more often than chance?

| Field | Value |
|---|---|
| **Status** | **Pre-registered. Not run.** Accepted by the operator 2026-10-09 09:16 IST, with the drafting choices in the footer confirmed as written. Nothing has been queried against this design; every commitment below is binding before the first outcome query. |
| **Date** | 2026-10-09 (Session 92) |
| **Track** | Post-parity priority track **P1** (ruling **S92-I**, `agentic_layer_roadmap_S90.md` §2.1) |
| **Discipline** | ADR-009 Phase 1, **N ≥ 60 tier** (chronological 67 / 33). Verdict rule replaces the win-rate tolerance column, as S74 did (§6). |
| **Question** | When the market opens, MERIDIAN's board shows a call wall, a put wall and a leading |γ| strike set. Do the session's high and low then land closer to those levels than to levels placed the same way on a different day? |
| **Prior** | **OPEN.** Two earlier zone studies broke on their own instruments, not on the market (§2). |
| **Primary N** | Every eligible NIFTY session from 2026-05-25 to 2026-10-08 under the §4 rule. Estimated ≈ 90–95; **not measured** — the rule is executed at run time and wins. |
| **Related** | ADR-009 · `adr009_prereg_gex_zone_utility_2026-09-07.md` (S74, the template and the precedent) · ADR-024 Amendment A (H4, A5) · ADR-025 C8 (L4/L5, L12 BUILT) · ENH-120 `v_gex_strike_walls` · `v_gex_strike_rank` · ADR-016 / R0.6 `get_parameter_num(key, as_of)` · R2.4 (`docs/research/s92_parity/r24/`, the as-of replay method) · CLAUDE.md Rule 13 |
| **Pre-registration hash** | `git hash-object` of this file as committed — recorded in the commit message and repeated in the result document (a file cannot carry its own hash) |

---

## 1. What this is

A pre-registration, not a result. It fixes the levels, the time they are read, the outcome, the
statistic, the null, the split, the exclusions and the verdict rule **before** any outcome is seen.
The SQL that implements it is written next, committed, and must implement these definitions
verbatim; any difference between the SQL and this document is resolved in favour of this document,
and any change made after the first outcome query is **a new pre-registration, not an amendment**.

## 2. Why the prior is open, and what this design repairs

| Earlier attempt | What it found | What broke | Repaired here by |
|---|---|---|---|
| **S74** PIN containment | **NO** — PIN adds nothing over spot-matched donors (NIFTY holdout −0.1996, CI [−0.2998, −0.0801]) | Null matched donors to ±0.5 % of the recipient's open while the real zone's own reference spot was unconstrained: **26.1 %** of NIFTY sessions fell outside the band (§D.33.4) | **Offset-preserving null** (§5.5): every donor contributes; no spot band, no drop for want of donors |
| **S74** ACCEL | Not answered | ~50 % of sessions excluded by an **outcome-dependent** rule (zero minutes inside / outside the band) | **No outcome-dependent exclusion anywhere** (§5.7): every exclusion is decided at the level-read time |
| **S79** (ADR-024 H4) | A positive-only γ argmax sits above spot on 99 %+ of rows **by construction** (OTM calls) | A level whose side of spot is fixed by arithmetic makes "the high landed near it" partly tautological | **Signed-offset null** preserves each level's side and distance from spot, so the tautology is in both real and null and cancels |

The S74 PIN *NO* stands and is **not** retested: the pin zone (L2) is not an arm here.

## 3. The levels — what the board shows, read at the open

Read from the **first `gex_strike_snapshots` run with `ts` at or after 09:15 IST** of the session,
front expiry (nearest `expiry_date` ≥ session date). That run's timestamp is **t0**.

| Arm | Level set | Rule (replayed as of t0, as R2.4 did) | Board layer |
|---|---|---|---|
| **A — Corridor** | call wall **CW**, put wall **PW** | `v_gex_strike_walls`: raw-OI argmax per side within ± band·σ_w of spot; band = `COALESCE(get_parameter_num('wall.band.'‖symbol, t0), 1.5)`; σ_w = spot · `atm_iv_avg`/100 · √(max(dte,1)/252), `atm_iv_avg` the latest `volatility_snapshots` row ≤ t0 | L4 / L5 |
| **B — Leader set** | the top 3 strikes by \|`gex_cr`\| | `v_gex_strike_rank` ordering on that run (ties broken by smaller \|strike − spot\|, then lower strike) | L12 |

The band parameter is read **as of t0** (R0.6), not today's value — a change from R2.4, which used
current parameters.

## 4. Eligibility — a rule, executed at run time

A session is eligible for a symbol iff, **all decided before the outcome**:

1. `trading_calendar.is_open` for that date, between 2026-05-25 and 2026-10-08 inclusive;
2. a `gex_strike_snapshots` run exists with `ts` in [09:15, 10:15) IST (so t0 is a morning read);
3. a `volatility_snapshots.atm_iv_avg` row exists at or before t0 on the same IST date;
4. `market_spot_snapshots` holds at least **300** deduplicated minutes in [t0, 15:15) IST.

The count, and every date dropped with its reason, is reported. Condition 4 is a data-coverage test
on minute counts, not on prices, so it cannot select on the outcome.

## 5. Pre-commitments (binding)

### 5.1 Unit and strata
**The session is the unit** — one value per session per arm. **NIFTY is primary.** SENSEX is
reported alongside as a replication and **never pooled** (same macro day, near-collinear). DTE is a
reporting stratum, never a selection.

### 5.2 Outcome
**H** and **L** = the highest and lowest deduplicated minute `spot` in **(t0, 15:15) IST**. The
15:15–16:00 closing-auction plateau is excluded (ADR-022; S74 Pre-commitment 8). Anything before t0
is excluded — it happened before the levels were on the screen.

Path source and dedupe exactly as S74 Pre-commitment 8: `market_spot_snapshots`, session date =
`(ts AT TIME ZONE 'Asia/Kolkata')::date`, one row per minute, `dhan_charts_intraday` winning over
`dhan_idx_i`, later `ts` winning within a source, `spot IS NULL` dropped and counted.

### 5.3 Scale
σ_d = S0 · IV0 / 100 / √252 — one trading day of expected movement, where S0 is the run's `spot` at
t0 and IV0 the `atm_iv_avg` used in §3. (Distinct from σ_w, which the wall rule scales by DTE.)

### 5.4 Statistics
- **Arm A:** `dA = ( |H − CW| + |L − PW| ) / (2 σ_d)` — the ceiling against the high, the floor
  against the low.
- **Arm B:** `dB = ( min_l |H − l| + min_l |L − l| ) / (2 σ_d)` over the three leader strikes.

Smaller is closer. Continuous, so there is no hit threshold to choose.

### 5.5 The null — offset-preserving, deterministic
For recipient session *r* and every **donor** session *d* of the same symbol with
`|sess_ix(d) − sess_ix(r)| ≥ 4` (eligible-sequence index):

1. express each of *d*'s levels as a signed offset in *d*'s own σ: `k = (level_d − S0_d) / σ_d,d`;
2. place it on *r*: `level* = S0_r + k · σ_d,r`;
3. snap to *r*'s strike grid (nearest multiple of the run's step; ties round away from spot).

Compute dA / dB for *r*'s own H and L against the placed levels. The null value for *r* is the
**mean over all donors** — no sampling, no seed, exactly reproducible. Each level's side of spot and
its distance in σ are preserved; only "these are today's strikes" is broken.

**Effect per session:** `e = d_null − d_real` (positive = MERIDIAN's levels sit closer to the
extremes than levels placed the same way on other days).

### 5.6 Split
Chronological. The first **⌊0.67 · N⌋** eligible NIFTY sessions are calibration, the rest holdout;
the boundary date is fixed from the eligibility list **before** any statistic is computed, and
reported. Donors may come from either half (they carry geometry, not outcome labels of *r*).

### 5.7 Exclusions — none may depend on the outcome
- Arm A: a session whose CW or PW is NULL at t0 (no OI inside the band — "a NULL wall is UNDEFINED",
  ENH-120) is excluded **from arm A only**, decided at t0, counted.
- Arm B: no exclusion beyond §4 (a run always has three strikes).
- A donor missing a level is skipped **for that level's arm**; it is never imputed.
- Nothing is excluded for where H or L fell.

### 5.8 Verdict — exactly two primary tests: A-NIFTY and B-NIFTY
For each, **NO** if either:
- the holdout mean of *e* has a **97.5 %** bootstrap interval that includes zero (two tests,
  Bonferroni); or
- the holdout mean is less than **half** the calibration mean.

Otherwise **YES**. Bootstrap: over sessions, 10,000 resamples, percentile, **seed 20261009**, three
significant figures.

### 5.9 Descriptive only — cannot produce a verdict
- SENSEX, both arms.
- Hit rates: H within *X* of CW and L within *X* of PW, *X* = half the strike step (NIFTY 25,
  SENSEX 50) and *X* = 0.10 σ_d — real vs null.
- By DTE bucket (0, 1, 2–3, 4+).
- Levels read at the **10:15** run instead of t0 (the L78-3 cadence).
- Arm A split into its high (CW) and low (PW) halves.
- How often H or L **broke through** the wall (beyond it by more than *X*), real vs null.

## 6. Preconditions — all pass before any statistic

1. **Rule 13:** no overlap between the study window and `data_contamination_ranges` for the fields
   read; any overlap is reported and its dates excluded **before** the run.
2. **Eligibility** (§4) executed; N and drops recorded.
3. **Grid:** step ∈ {50} NIFTY, {100} SENSEX on every t0 run — fail loudly otherwise.
4. **One spot per run** on every t0 run (S74 P7).
5. **Front expiry:** count of t0 runs carrying more than one `expiry_date`, reported even when zero.
6. **Replay check:** on the latest run, the §3 replay equals `v_gex_strike_walls` and
   `v_gex_strike_rank` live (zero-row symmetric difference) — run outside 08:30–15:40 IST, when the
   writer is idle.

## 7. What a result does and does not authorise

**YES on A** supports the corridor as an informative display: the walls mark where the session tends
to stop, beyond what their position relative to spot alone explains. **YES on B**, likewise for the
leader set. Either bears on the operator's S/R premium-selling idea, whose premise is that such
levels hold.

**Neither authorises a gate or a trade rule.** Display-only, as ADR-025 states; any gate needs its
own N ≥ 30 live-runtime cohort under ADR-009.

**NO on both** is the S92-I decision point: the operator re-plans P2–P8 before more is built on the
levels.

## 8. Caveats fixed in advance

- **The null controls for placement, not for regime.** σ scaling absorbs IV level; it does not make a
  trend day like a range day. Vol-regime conditioning remains unavailable (S74 Pre-commitment 7).
- **`atm_iv_avg` is single-expiry and silently switches expiry class** (ENH-120 COMMENT). σ inherits
  that; staleness is reported (age of the IV row at t0), not enforced.
- **SENSEX has no gamma on ~30 % of strikes** (ADR-024 §A3). Arm B on SENSEX is weaker for it; this is
  one reason SENSEX is descriptive.
- **Minute resolution** misses intrabar extremes; it biases distances slightly upward in real and null
  alike.
- **The t0 levels use the previous session's OI** (OI is end-of-day); that is what the board shows at
  the open, so it is the right object, but it is not intraday positioning.
- **The replay is validated only at the latest run** (§6.6), as in S74 and R2.4; no historical run of
  a latest-only view exists to compare against.
- **N ≈ 90 is enough for a direction, not for a small effect.** A NO with a wide interval is reported
  as *not shown*, not as *shown absent*.

---

*Drafted 2026-10-09, Session 92, under ADR-009 Phase 1 and ruling S92-I; accepted by the operator
09:16 IST. Not run. Choices made while drafting, **confirmed by the operator as written**: t0 = first run ≥ 09:15 IST (§3); top-3 for the
leader set (§3); one-day σ for the distance scale (§5.3); Bonferroni 97.5 % (§5.8); the ≥ 300-minute
coverage floor (§4).*
