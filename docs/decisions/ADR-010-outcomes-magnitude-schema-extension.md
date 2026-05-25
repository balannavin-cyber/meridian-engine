# ADR-010 — `ict_primitive_outcomes` schema extension: magnitude profiling + ATM PnL + DTE (13 additive columns)

| Field | Value |
|---|---|
| **Status** | Proposed (Session 32 P0_PRIMARY — accepted at build-time before code lands per Doc Protocol v4 Rule 10) |
| **Date** | 2026-05-22 (Session 32; drafted to gate ENH-100 build) |
| **Decision-makers** | Navin (operator), Claude (architect) |
| **Supersedes** | None — additive extension of S31-A Task 3 DDL (commit pending S31-A close `447634c..S31-A-close-TBD`) |
| **Related** | ENH-100 (this ADR is its schema artifact; Enhancement Register Part 4 detail block), ENH-101 (consumer — `mae_pct` is the column it gates on), ENH-102 (consumer — ATM PnL + MFE for live-routing sizing/stop calibration), ADR-004 §5.1/§5.2/§6.1/§7.1/§7.2 (Wave 1 primitive canon — 5 primitive types whose outcomes get magnitude-extended), ADR-009 §Phase 1 (holdout discipline — magnitude columns extend Phase-1 into magnitude-stratified analysis), Assumption Register §D.14 (S31-B holdout findings — magnitude data needed to operationalize), Doc Protocol v4 Rule 10 (schema-affecting changes require ADR before code), CLAUDE.md v1.22 settled-decisions (ADR-004 Wave 1 IMPLEMENTED, H FVG retest VALIDATED holdout). |

---

## Context

S31-B (2026-05-21) shipped ADR-004 Wave 1 IMPLEMENTED end-to-end: 19,399 ICT primitives + 19,399 outcomes rows over a 414-day window (2025-04-01 → 2026-05-19) in 156.3s combined runtime (NIFTY 53.7s + SENSEX 102.6s). ADR-009 Phase-1 holdout split on the resulting cohort surfaced the headline finding — H FVG retest validates across all four buckets (NIFTY/SENSEX × BEAR/BULL, holdout WR 80.8–92.0%, N=27–30 per cell, deltas vs train +10.2 to +25.7pp in favorable direction).

The `ict_primitive_outcomes` table as currently built carries a **single outcome column**: `forward_30m_pct`. This was sufficient to produce direction-of-edge verdicts (HOLD/STRENGTHEN/REFUTE on holdout) but insufficient for everything downstream:

1. **Magnitude profiling is impossible.** A 60% WR signal at +0.5% mean move and a 60% WR signal at +1.5% mean move are operationally different signals. The current schema collapses both into the same `forward_30m_pct > 0` flag.

2. **Operator's six S31-B Q2 follow-up questions all gate on this.** "How far did the move go" / "ATM PnL + DTE" / "sweep reversal magnitude" / "optimum stop loss" / "optimum entry technique" / "D/H FVG retest distance" — none answerable with `forward_30m_pct` alone.

3. **ENH-101 stop-loss optimization is structurally blocked.** Its method (90th-pct of `mae_pct` among winning trades per cell with N≥30) requires an MAE column that does not exist.

4. **ENH-102 H-FVG-retest live routing is calibration-blocked.** The holdout-validated edge cannot be turned into a live rule without sizing posture (entry tolerance band, stop placement, exit horizon) that requires magnitude data.

5. **Wave 1's six-month live deployment data is invisible to the option layer.** Outcomes are spot-only. ATM option PnL is the actual P&L surface the trading system operates on. The disconnect between spot-WR research and option-PnL execution is a chronic MERDIAN risk (Exp 41 SENSEX MAE finding: 400pt stop on SENSEX ATM PE means option down 50–70% before recovery — spot WR alone misleads).

The next-level question — turn the validated H-FVG-retest edge into a live trading rule — is gated on magnitude characterization. Step 1 of the S32 ENH-100 build is to **codify the schema extension formally** before ALTER TABLE lands, per Doc Protocol v4 Rule 10.

---

## Decision

**Extend `public.ict_primitive_outcomes` with 13 additive columns** organized into four logical groups. No column drops, no column type changes, no FK changes, no UNIQUE/INDEX changes. The S31-A canonical 1:1 FK CASCADE relationship with `ict_primitives` is preserved exactly. The existing `forward_30m_pct` column stays where it is and continues to carry the canonical 30-minute spot return.

### Group 1 — Forward spot returns at fixed horizons (5 columns)

| Column | Type | Semantic |
|---|---|---|
| `forward_5m_pct` | numeric | Spot return at primitive `valid_from + 5 min`, as `(spot_t5 - spot_t0) / spot_t0` |
| `forward_15m_pct` | numeric | Spot return at +15 min |
| `forward_60m_pct` | numeric | Spot return at +60 min |
| `forward_120m_pct` | numeric | Spot return at +120 min |
| `forward_eod_pct` | numeric | Spot return at session close (15:30 IST on `valid_from`'s session date; NULL if primitive formed after 15:30) |

**Source.** `market_spot_snapshots` first tick at-or-after the horizon timestamp, same convention as S31-A Task 2 writer for `forward_30m_pct`. Per-symbol session-date filtering avoids cross-session leakage (the EOD column never crosses to next day's open).

**Rationale.** Five horizons span the operator's intraday + EOD interest. `forward_5m` is the fastest spot-feedback signal; `forward_120m` covers Sessions 11 P0–P3 transitions; `forward_eod` captures full-session edge realization (relevant for D/W-TF primitives that should sustain rather than fade).

### Group 2 — Excursion magnitudes (3 columns)

| Column | Type | Semantic |
|---|---|---|
| `mfe_pct` | numeric | Max Favorable Excursion: signed peak distance from entry in the direction of the primitive between `valid_from` and `valid_from + 30 min` (BULL primitives: max spot − entry over window, divided by entry; BEAR primitives: entry − min spot over window, divided by entry; always reported as positive when primitive moved in expected direction, negative if peak was opposite-side) |
| `mae_pct` | numeric | Max Adverse Excursion: signed worst drawdown from entry against the direction of the primitive in the same window (BULL primitives: entry − min spot over window, divided by entry, reported as negative; BEAR primitives: max spot − entry over window, divided by entry, reported as negative). **Negative-valued by construction**: a more-negative number is a worse drawdown |
| `time_to_mfe_min` | integer | Minutes from `valid_from` to the bar that produced `mfe_pct`. NULL if MFE is at-or-below 0 (no favorable movement in window) |

**Source.** Iterate `market_spot_snapshots` between `valid_from` and `valid_from + 30 min` (or session close, whichever earlier — same horizon as canonical `forward_30m_pct`). Track running max-favorable and min-favorable; emit signed peak and trough at end-of-window. `time_to_mfe_min` records the offset of the max-favorable bar.

**Rationale.** `mae_pct` is the column that gates ENH-101. `mfe_pct` is the symmetric peak-of-winners measurement that lets us reason about take-profit placement separately from stop placement. `time_to_mfe_min` answers "how quickly does the move materialize" — the operator's "optimum entry technique" follow-up question reduces to a distribution over this column.

**Window choice.** The 30-minute window mirrors the canonical exit horizon. ENH-101 extensibility for H-FVG-retest signals (which may use forward_60m as their canonical exit) is handled at the consumer layer, not at the schema layer. If consumer evolution demands per-cell-horizon MFE/MAE, those become Wave 1.5 columns (`mfe_60m_pct`, `mae_60m_pct`, etc.); not in this ADR.

### Group 3 — ATM option PnL at four horizons (4 columns)

| Column | Type | Semantic |
|---|---|---|
| `atm_pnl_5m_pct` | numeric | ATM option return at `valid_from + 5 min`: for BULL primitives, ATM CE premium at +5min vs ATM CE premium at +0; for BEAR primitives, ATM PE. Reported as `(premium_t5 - premium_t0) / premium_t0` |
| `atm_pnl_15m_pct` | numeric | At +15 min (same rule) |
| `atm_pnl_30m_pct` | numeric | At +30 min — parallel to spot `forward_30m_pct` |
| `atm_pnl_60m_pct` | numeric | At +60 min |

**Source.** Join `option_chain_snapshots` (or `hist_atm_option_bars_5m` / `hist_atm_option_bars_1m` per availability) at `valid_from` timestamp to identify the ATM strike (closest to spot, both symbols), then read that strike's CE (BULL) or PE (BEAR) premium at +0 / +5 / +15 / +30 / +60. Same-strike tracking: once identified at +0, the strike does NOT re-pick at later horizons (we follow that strike's premium evolution, not whatever became ATM later).

**ATM definition.** Closest strike to spot at `valid_from` rounded to standard strike interval (NIFTY 50pt, SENSEX 100pt). Tie-break: lower strike for ties.

**Rationale.** Spot WR and ATM PnL diverge meaningfully on tight-stop / fast-decay cohorts (see Exp 41 SENSEX MAE 400pt = option down 50–70%). Operator's "ATM PnL + DTE — what does an ATM option actually return?" follow-up question is the direct prompt for this group. Four horizons mirror the spot return horizons (omitting +120 / +EOD since theta dominates at those windows and the answer would degenerate into "near-zero or worthless").

**Nullability.** If `option_chain_snapshots` is missing for the relevant timestamp window (Dhan outage, pre-session, post-market), all four columns NULL for that primitive — same-row partial fill not permitted (avoid inconsistent CE/PE pairing).

### Group 4 — DTE at formation (1 column)

| Column | Type | Semantic |
|---|---|---|
| `dte_at_formation` | integer | Days-to-expiry on the weekly expiry calendar at primitive `valid_from`. NIFTY expiry = nearest Tuesday on-or-after `valid_from` per NSE 2025+ change. SENSEX expiry = nearest Thursday on-or-after `valid_from` per BSE. Same-day primitive on expiry day = DTE 0. Computed in IST market calendar (skip non-trading days for the count if applicable — but per established convention DTE is simple calendar-day diff, no holiday compression) |

**Source.** Deterministic from `valid_from` date + symbol expiry rule. No external lookup required. Computed at writer time.

**Rationale.** ATM PnL is dominated by theta on the day of expiry and far less so 4 days out. Bucketing the 4 ATM PnL columns by DTE separates the two regimes. Without `dte_at_formation`, ATM PnL distributions mix DTE-0 (high gamma, fast decay) with DTE-3+ (lower gamma, slower decay) and the resulting averages mislead.

**Symbol-specific expiry calendars.** NIFTY = Tuesday weekly per NSE 2025+ change; SENSEX = Thursday weekly per BSE. Hardcoded in writer; encoded as a pair of constants `EXPIRY_DOW_NIFTY = 1` (Tuesday is weekday 1 in Python's `datetime.weekday()`) and `EXPIRY_DOW_SENSEX = 3` (Thursday).

---

## Migration

```sql
ALTER TABLE public.ict_primitive_outcomes
  ADD COLUMN forward_5m_pct numeric,
  ADD COLUMN forward_15m_pct numeric,
  ADD COLUMN forward_60m_pct numeric,
  ADD COLUMN forward_120m_pct numeric,
  ADD COLUMN forward_eod_pct numeric,
  ADD COLUMN mfe_pct numeric,
  ADD COLUMN mae_pct numeric,
  ADD COLUMN time_to_mfe_min integer,
  ADD COLUMN atm_pnl_5m_pct numeric,
  ADD COLUMN atm_pnl_15m_pct numeric,
  ADD COLUMN atm_pnl_30m_pct numeric,
  ADD COLUMN atm_pnl_60m_pct numeric,
  ADD COLUMN dte_at_formation integer;

NOTIFY pgrst, 'reload schema';
```

All columns nullable by design — backfill populates incrementally per writer run, and missing source-data (option chain gaps, EOD timestamps for late-session primitives) is recorded as NULL rather than zero or sentinel.

**No index changes.** None of the new columns will carry queries that require index support at this phase; ENH-101 / ENH-102 consumer queries aggregate-group-by patterns that scan the table linearly per the existing `(symbol, timeframe, primitive_type, mode)` access pattern. If a consumer query at scale benefits from a magnitude-column index, that gets filed as a separate optimization decision, not bundled here.

**No CHECK constraints.** Magnitude columns can carry valid negative values (`mae_pct` is negative by construction); a CHECK that forbids negative would be wrong. Range CHECKs (e.g., `forward_5m_pct BETWEEN -0.20 AND 0.20`) get rejected because spot 20%-move events have happened (March 2020 etc.); the table is research-tier and outlier observations should be preserved not rejected.

---

## Alternatives considered

1. **Separate sister table `ict_primitive_outcomes_magnitude` keyed 1:1 by FK.** Rejected. Existing table is research-tier, lightly indexed, FK-CASCADE-d cleanly to `ict_primitives`. Splitting incurs a join on every consumer query for no gain. The 1:1 magnitude:outcomes ratio is structural — there is never a case where one primitive has multiple magnitude characterizations.

2. **JSONB blob column `magnitude_metrics jsonb` carrying the 13 fields.** Rejected. Loses type safety, loses index-ability, loses NULL-vs-missing distinction (Postgres JSONB makes `{}` and `{"x": null}` distinguishable but consumer code rarely handles this correctly), and consumer SQL becomes `(magnitude_metrics->>'mae_pct')::numeric` everywhere. The 13 columns are stable and known; JSONB is for unknown / variable schemas.

3. **Compute on-demand via SQL views over `market_spot_snapshots` joins.** Rejected. View recomputation cost at scale is prohibitive — the holdout split SQL on the 19,399-row outcomes table runs in seconds; the same query against a view recomputing forward returns from `market_spot_snapshots` would be minutes. ENH-101 percentile aggregations across (symbol, TF, primitive_type, direction, mode) cells require precomputed values.

4. **Wait until Wave 2 (ten remaining ADR-004 primitives) lands and do schema extension once.** Rejected on operational ground. Wave 2 is open-ended; H-FVG-retest live deployment is gate-blocked NOW on this schema; carrying the gate through Wave 2 delays the headline S31-B finding indefinitely. The extension is additive, so Wave 2 columns (whatever they are) can be added later without conflict.

5. **Add only `mae_pct` (the strict ENH-101 prerequisite) and defer the other 12.** Rejected. Operator's six follow-up questions are interconnected — sizing decisions (ENH-101) calibrate against both stop (`mae_pct`) AND take-profit (`mfe_pct`) AND ATM PnL (`atm_pnl_*` group) AND DTE (`dte_at_formation`). Shipping `mae_pct` alone unlocks ENH-101 mechanically but leaves ENH-102 live deployment still blocked on the remaining questions. Single-trip extension is operationally cleaner.

---

## Falsification commitment

ENH-100 is infrastructure not a hypothesis. Its failure mode is implementation defect, not invalidated edge. The schema decision in this ADR carries one operational falsification criterion at build time:

**Post-build 100-sample audit:**
- Spot return columns (`forward_5m_pct`, `forward_15m_pct`, `forward_60m_pct`, `forward_120m_pct`, `forward_eod_pct`) must agree with locally-computed forward returns from `market_spot_snapshots` to within **1bp absolute** on 100 randomly-selected primitives.
- ATM PnL columns (`atm_pnl_5m_pct`, `atm_pnl_15m_pct`, `atm_pnl_30m_pct`, `atm_pnl_60m_pct`) must agree with `hist_option_bars_1m` premium-percent change to within **5% relative** on the same 100-sample audit.
- `mae_pct` and `mfe_pct` must agree with locally-computed peak/trough scans to within **1bp absolute**.
- `dte_at_formation` must agree with manually-computed expiry-date diff on the same 100-sample audit (exact match, no tolerance).

Any discrepancy beyond these thresholds indicates a writer bug. Fix-and-rebackfill before declaring ENH-100 complete. Audit script gets filed in `/scripts/audits/` and re-runs on every backfill iteration.

**No edge-validity falsification at the ADR level.** Whether the magnitude data reveals an exploitable pattern is a separate research question downstream (ENH-101 / ENH-102 consumers). The ADR commits only that the schema is faithful to the underlying data.

---

## Consequences

**Positive.**

1. Unblocks ENH-101 (`mae_pct` becomes available).
2. Unblocks ENH-102 live-deployment calibration (sizing posture + entry tolerance band + stop placement derivable from magnitude data).
3. Answers all six operator S31-B Q2 follow-up questions in a single migration.
4. Establishes the schema home for future magnitude-stratified ADR-009 Phase-1 holdout iterations (rather than ad-hoc per-experiment column additions).
5. Closes the spot-WR-vs-option-PnL gap that has bitten prior research (Exp 41 SENSEX MAE finding).
6. Re-compute cost ~30s/symbol per S31-B Task 4 baseline (~1 minute combined) — operationally cheap.

**Negative.**

1. `ict_primitive_outcomes` row width grows by 13 columns (~104 bytes per row at numeric+integer mix, ~2MB additional storage on current 19,399-row table — negligible).
2. Writer complexity grows: option-chain join is the most expensive new dependency. Cache strategy at the writer level (per-session ATM strike lookup cache) recommended to keep re-compute cost in line with the 30s/symbol baseline.
3. Future Wave 2 primitives (10 of 15) will inherit the same 13 columns — generally fine since the magnitude profile is universal across primitive types, but Wave 2 detector implementations need to populate these (writer extension covers, no special-casing needed).
4. The `forward_30m_pct` column becomes one-of-six forward-return columns rather than the single canonical one. Consumer queries currently filtering on `forward_30m_pct > 0` (the holdout split SQL) continue to work unchanged; the column does not move and does not change semantics.

**Reversibility.**

Fully reversible: `ALTER TABLE … DROP COLUMN` on each of the 13 columns rolls back without disturbing the underlying outcome and primitive rows. Doc Protocol v4 Rule 10 trigger fires on the drop direction too (re-ADR if rolled back). No expected need; included for completeness.

---

## Open follow-ups

1. **ATM PnL writer cache strategy.** Per-session ATM-strike lookup cache should be implemented in `build_ict_primitives.py` to keep re-compute cost at 30s/symbol. Cache key: `(symbol, valid_from_session_date)`. Resolved at build time.
2. **`hist_option_bars_1m` vs `option_chain_snapshots` source preference.** Both can supply premium history; preference order should be: `hist_option_bars_1m` (canonical bar source) → `option_chain_snapshots` (5m-resolution fallback). If `hist_option_bars_1m` has gaps within the 60-minute horizon, fall back to snapshot interpolation. Filed as writer implementation choice, not ADR scope.
3. **Wave 2 inheritance.** When ADR-004 Wave 2 (10 remaining primitives) is built, the new primitives' detectors must produce outcomes through the same writer block. No schema change should be required at that time.
4. **`time_to_mfe_min` granularity.** Stored as integer minutes from `valid_from`. If sub-minute granularity becomes useful (high-frequency primitive timing analysis), upgrade to seconds-since via separate column rather than re-typing this one.

---

## Cross-references and lineage

- ENH-100 Enhancement Register Part 4 detail block — this ADR's source.
- S31-B CURRENT.md "Last session" block — finding context.
- S31-B session_log.md entry — ENH-100/101/102 filing.
- ADR-009 §Phase 1 — calibration discipline that consumes magnitude data.
- ADR-004 §5.1 (OB), §5.2 (FVG), §6.1 (PDH/PDL), §7.1 (Sweep), §7.2 (Displacement) — Wave 1 primitives feeding outcomes.
- merdian_reference.json `tables.ict_primitive_outcomes.contamination_notes` — describes current 1-column state, to be updated post-build.
- Assumption Register §D.14 (5 rows D.14.1–D.14.5) — holdout findings consuming this schema downstream.
- Doc Protocol v4 Rule 10 — schema-affecting changes require ADR before code.

---

*ADR-010 drafted Session 32. Acceptance gates ENH-100 build steps 2–5 (ALTER TABLE → writer extension → backfill → 100-sample falsification audit). Mechanical follow-throughs per Doc Protocol v4 Rule 11 land at S32 close: Decision Index row prepended, Pending ADRs table updated, CLAUDE.md settled-decisions appended, Assumption Register §D.14 cross-ref updated, tech_debt.md no change, Enhancement Register ENH-100 status updated PROPOSED → ACCEPTED-PENDING-BUILD.*
