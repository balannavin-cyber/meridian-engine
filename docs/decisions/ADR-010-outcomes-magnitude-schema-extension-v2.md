# ADR-010 v2 — `ict_primitive_outcomes` schema extension: magnitude profiling + ATM PnL + DTE (9 net-new columns)

| Field | Value |
|---|---|
| **Status** | Proposed v2 (Session 32 P0_PRIMARY — supersedes ADR-010 v1 draft after migration deployment finding revealed pre-S32 schema was richer than v1 represented; v2 accepted at build-time before code lands per Doc Protocol v4 Rule 10) |
| **Date** | 2026-05-22 (Session 32; v1 drafted + deployed; v2 corrected post-deploy after column-collision finding) |
| **Decision-makers** | Navin (operator), Claude (architect) |
| **Supersedes** | ADR-010 v1 (drafted same session; superseded after migration deployment surfaced 3 pre-existing column collisions + 1 redundancy not represented in v1 Context) |
| **Related** | ENH-100 (this ADR is its schema artifact), ENH-101 (consumer — `mae_pct` is the column it gates on), ENH-102 (consumer — ATM PnL + MFE for live-routing sizing/stop calibration), ADR-004 §5.1/§5.2/§6.1/§7.1/§7.2 (Wave 1 primitive canon), ADR-009 §Phase 1 (holdout discipline), Assumption Register §D.14, Doc Protocol v4 Rule 10, CLAUDE.md v1.22 settled-decisions. |

---

## Context (v2 — corrected)

S31-B (2026-05-21) shipped ADR-004 Wave 1 IMPLEMENTED end-to-end: 19,399 ICT primitives + 19,399 outcomes rows over a 414-day window (2025-04-01 → 2026-05-19) in 156.3s combined runtime. ADR-009 Phase-1 holdout split on the resulting cohort surfaced the headline finding — H FVG retest validates across all four buckets (NIFTY/SENSEX × BEAR/BULL, holdout WR 80.8–92.0%, N=27–30 per cell).

**Pre-S32 schema reality (corrected from v1).** The `ict_primitive_outcomes` table as built by S31-A Task 3 DDL carried 19 columns organized into five logical groups, not the single-column simplification stated in v1's Context, CURRENT.md, and `merdian_reference.json.tables.ict_primitive_outcomes.contamination_notes`:

| Group | Columns | Populated? |
|---|---|---|
| FK + audit | `primitive_id` (FK CASCADE), `computed_at` | always |
| Forward spot returns | `forward_5m_pct`, `forward_15m_pct`, `forward_30m_pct`, `forward_1h_pct`, `forward_eod_pct` | yes (verified N=17,823 non-null on `forward_1h_pct`) |
| Retest tracking | `retest_status`, `first_retest_ts`, `retest_depth_pct` | yes |
| Retest forward returns | `retest_fwd_5m_pct`, `retest_fwd_15m_pct`, `retest_fwd_30m_pct`, `retest_fwd_1h_pct`, `retest_fwd_eod_pct` | conditionally (only when retest occurred) |
| Zone tracking | `respected`, `mitigated_at`, `breach_at` | yes |
| Option PnL placeholders | `option_pnl_30m`, `option_pnl_eod` | **100% NULL** — reserved-but-unused schema slots from S31-A |

The forward-return horizon coverage was therefore already 4 of the 5 horizons proposed in v1 (5m / 15m / 1h / eod — the 1h column having the same semantic as the proposed `forward_60m_pct`; correlation with `forward_30m_pct` = 0.864, mean = 0.0178 across N=17,823 — exact pattern for a decimal-fraction 60-minute spot return).

**What was actually missing pre-S32 and warrants the ADR:**

1. **No excursion magnitude data** — `mfe_pct`, `mae_pct`, `time_to_mfe_min`. ENH-101 stop-loss optimization is gated on `mae_pct`. ENH-102 H-FVG-retest take-profit posture is gated on `mfe_pct`.
2. **No ATM option PnL columns** — `option_pnl_30m` and `option_pnl_eod` are present-but-empty schema slots, semantically unspecified (points vs percent vs ATM-vs-strike-specific). ENH-100 introduces explicit `atm_pnl_*_pct` columns at four horizons with canonical _pct semantics + ATM-explicit prefix.
3. **No DTE tagging** — `dte_at_formation`. ATM PnL is theta-dominated on DTE-0; DTE bucketing separates regimes.
4. **No 120-minute horizon** — `forward_120m_pct`. Sessions 11 P0–P3 transitions span this window.

**Operator's six S31-B Q2 follow-up questions** (magnitude profiling / "how far did the move go" / ATM PnL + DTE / sweep reversal magnitude / optimum stop loss / optimum entry technique / D/H FVG retest distance) gate on the four items above, not on additional forward-return horizons that were already present.

**Doc drift acknowledged.** ADR-010 v1's Context statement that the table "carries a single outcome column: `forward_30m_pct`" was incorrect. Same statement appears in v1 ADR + CURRENT.md S31-B Last-session block + `merdian_reference.json.tables.ict_primitive_outcomes.contamination_notes`. All three need correction at S32 doc-close. Source of the drift: ADR-010 v1 was drafted from the Enhancement Register ENH-100 detail block + the S31-B CURRENT.md "Last session" block, neither of which surveyed the live schema. Migration deployment surfaced the drift in one query.

---

## Decision (v2)

**Extend `public.ict_primitive_outcomes` with 9 net-new additive columns** organized into three logical groups. No column drops to pre-existing columns; one drop of v1's redundant addition (`forward_60m_pct` → use pre-existing `forward_1h_pct`); two pre-existing columns deprecated-in-place via `COMMENT ON COLUMN` (`option_pnl_30m`, `option_pnl_eod`).

### Group 1 — Forward spot returns (1 net-new column)

| Column | Type | Semantic | Pre-existing? |
|---|---|---|---|
| `forward_5m_pct` | numeric | Spot return at +5 min | YES (no-op in v1 migration via IF NOT EXISTS) |
| `forward_15m_pct` | numeric | Spot return at +15 min | YES (no-op) |
| `forward_30m_pct` | numeric | Spot return at +30 min | YES (canonical; unchanged) |
| `forward_1h_pct` | numeric | Spot return at +60 min | YES (canonical 60-min — supersedes v1's `forward_60m_pct`) |
| **`forward_120m_pct`** | numeric | Spot return at +120 min | **NO — net-new in v2** |
| `forward_eod_pct` | numeric | Spot return at session close | YES (no-op) |

**v2 disposition.** `forward_60m_pct` (added by v1 migration as an empty column) is DROPPED via corrective SQL; `forward_1h_pct` is the canonical 60-min column. Writer extension references `forward_1h_pct` consistently.

### Group 2 — Excursion magnitudes (3 net-new columns)

| Column | Type | Semantic |
|---|---|---|
| `mfe_pct` | numeric | Max Favorable Excursion over +0..+30min window, signed in direction of primitive |
| `mae_pct` | numeric | Max Adverse Excursion over +0..+30min window, negative-valued by construction (gates ENH-101) |
| `time_to_mfe_min` | integer | Minutes from `valid_from` to MFE-producing bar; NULL if MFE ≤ 0 |

Window = 30 min to mirror canonical `forward_30m_pct`. Per-cell horizon-specific MFE/MAE (e.g., `mfe_60m_pct` for H-FVG-retest signals using +60min canonical exit) deferred to Wave 1.5; out of this ADR's scope.

### Group 3 — ATM option PnL (4 net-new columns)

| Column | Type | Semantic |
|---|---|---|
| `atm_pnl_5m_pct` | numeric | ATM CE (BULL) or PE (BEAR) return at +5 min from `valid_from` |
| `atm_pnl_15m_pct` | numeric | At +15 min |
| `atm_pnl_30m_pct` | numeric | At +30 min |
| `atm_pnl_60m_pct` | numeric | At +60 min |

Same-strike tracking: ATM identified at +0 (closest strike, lower-on-tie), tracked through +5/+15/+30/+60 without re-pick. NIFTY 50pt strike interval; SENSEX 100pt. No EOD column — theta dominates beyond +60min; measurement degenerates.

**Deprecates** `option_pnl_30m` + `option_pnl_eod` (100% NULL, reserved-but-unused since S31-A; semantically unspecified). `atm_pnl_30m_pct` is the canonical 30-min option PnL column going forward. Deprecation via `COMMENT ON COLUMN`; no drop (preserves legacy reference safety; future cleanup via separate ADR).

### Group 4 — DTE at formation (1 net-new column)

| Column | Type | Semantic |
|---|---|---|
| `dte_at_formation` | integer | Days-to-expiry on weekly calendar at `valid_from`. NIFTY Tue (per NSE 2025+); SENSEX Thu (per BSE). Same-day on expiry = DTE 0 |

---

## Migration (v2 — applied in two passes)

### Pass 1: Original migration (executed 2026-05-22)

```sql
ALTER TABLE public.ict_primitive_outcomes
  ADD COLUMN IF NOT EXISTS forward_5m_pct      numeric,    -- no-op (existed)
  ADD COLUMN IF NOT EXISTS forward_15m_pct     numeric,    -- no-op (existed)
  ADD COLUMN IF NOT EXISTS forward_60m_pct     numeric,    -- added (redundant; dropped in Pass 2)
  ADD COLUMN IF NOT EXISTS forward_120m_pct    numeric,    -- added (net-new)
  ADD COLUMN IF NOT EXISTS forward_eod_pct     numeric,    -- no-op (existed)
  ADD COLUMN IF NOT EXISTS mfe_pct             numeric,    -- added (net-new)
  ADD COLUMN IF NOT EXISTS mae_pct             numeric,    -- added (net-new)
  ADD COLUMN IF NOT EXISTS time_to_mfe_min     integer,    -- added (net-new)
  ADD COLUMN IF NOT EXISTS atm_pnl_5m_pct      numeric,    -- added (net-new)
  ADD COLUMN IF NOT EXISTS atm_pnl_15m_pct     numeric,    -- added (net-new)
  ADD COLUMN IF NOT EXISTS atm_pnl_30m_pct     numeric,    -- added (net-new)
  ADD COLUMN IF NOT EXISTS atm_pnl_60m_pct     numeric,    -- added (net-new)
  ADD COLUMN IF NOT EXISTS dte_at_formation    integer;    -- added (net-new)
NOTIFY pgrst, 'reload schema';
```

10 added, 3 no-op via IF NOT EXISTS guard.

### Pass 2: Corrective migration (file: `migrate_s32_enh100_corrective.sql`)

```sql
ALTER TABLE public.ict_primitive_outcomes
  DROP COLUMN IF EXISTS forward_60m_pct;      -- redundant; forward_1h_pct supersedes

COMMENT ON COLUMN public.ict_primitive_outcomes.option_pnl_30m IS
  'DEPRECATED 2026-05-22 ... superseded by atm_pnl_30m_pct ...';
COMMENT ON COLUMN public.ict_primitive_outcomes.option_pnl_eod IS
  'DEPRECATED 2026-05-22 ... ENH-100 does not add an atm_pnl_eod_pct equivalent ...';

NOTIFY pgrst, 'reload schema';
```

**Net schema delta post-S32:** 9 truly-new columns added; 2 pre-existing columns deprecated-in-place; 0 destructive changes to populated columns.

---

## Falsification commitment (unchanged from v1)

Post-build 100-sample audit:
- Spot return columns (`forward_5m_pct`, `forward_15m_pct`, `forward_30m_pct`, `forward_1h_pct`, `forward_120m_pct`, `forward_eod_pct`) — pre-existing columns continue to be writer-controlled; new `forward_120m_pct` must agree with locally-computed forward returns from `market_spot_snapshots` to within **1bp absolute**.
- ATM PnL columns (`atm_pnl_5/15/30/60m_pct`) must agree with `hist_option_bars_1m` premium-percent change to within **5% relative**.
- `mae_pct` and `mfe_pct` must agree with locally-computed peak/trough scans to within **1bp absolute**.
- `dte_at_formation` must agree with manually-computed expiry-date diff (exact match, no tolerance).

Audit script in `/scripts/audits/`; re-runs on every backfill iteration.

---

## Consequences (v2 deltas)

**Schema row-width growth.** ~72 bytes per row at numeric+integer mix (9 columns instead of 13 in v1) — ~1.4MB additional storage on current 19,399-row table.

**Writer complexity.** Writer extension (Step 3) populates 9 new columns (forward_120m + 3 excursion + 4 ATM PnL + DTE). Existing 5 forward-return columns + 5 retest-forward + retest tracking + zone tracking remain untouched (already populated by S31-A writer). Option-chain join is the most expensive new dependency; per-session ATM-strike cache recommended.

**Doc drift cleanup at S32 close.**
- ADR-010 v1 → v2 supersession recorded in Decision Index Pending ADRs table.
- CURRENT.md S31-B Last-session block "Currently only `forward_30m_pct` column for outcomes" — needs strikethrough + note pointing to S32 actual-schema audit.
- `merdian_reference.json.tables.ict_primitive_outcomes.contamination_notes` — needs rewrite reflecting actual pre-S32 19-column schema + post-S32 28-column schema (19 pre + 9 new = 28).
- Enhancement Register ENH-100 detail block "13 additive columns" → "9 net-new additive columns (3 collided via IF-NOT-EXISTS no-op; 1 dropped as redundant)"; falsification audit count updates from 13-column verification to 9-column verification + collision audit.
- Assumption Register §D.14 cross-references updated.

---

## Migration deployment finding (NEW section in v2)

The Pass 1 migration `migrate_s32_enh100_outcomes_magnitude.sql` deployed cleanly with `ADD COLUMN IF NOT EXISTS` guard catching three pre-existing columns and adding ten new (including one redundant). The pre-flight `column_name IN (...)` collision check returned `already_present = 3` — surfacing the drift between ADR-010 v1's Context and the live schema. Operator query against `forward_1h_pct` confirmed semantic identity with the v1-proposed `forward_60m_pct` (correlation 0.864 with `forward_30m_pct`, mean 0.0178, N=17,823 populated). NULL-only state of `option_pnl_30m` + `option_pnl_eod` confirmed via same query — reserved-but-unused schema slots, safe to deprecate-in-place.

**Lesson — methodology.** Schema-extension ADRs must verify live schema state before drafting, not infer from documentation. ADR-010 v1 inferred from CURRENT.md + Enhancement Register, both of which carried a months-old simplification. The `IF NOT EXISTS` idempotency guard was the only thing that prevented a deploy-time error or a duplicate-column-name catch (had the migration been written without the guard, the first ADD COLUMN on `forward_5m_pct` would have failed and the entire transactional block would have rolled back). **Generalize as governance rule: schema-affecting ADRs require a `SELECT column_name FROM information_schema.columns WHERE table_name = ...` pre-flight in their Context section before column-additions are listed.** File as a Doc Protocol v4 Rule 10 amendment candidate at S32 close.

**Lesson — diagnostic.** A single correlation-and-mean query (`CORR + AVG + N` on two columns) resolves semantic identity at decimal-fraction scale faster than reading writer code. Useful pattern for any future "are these two columns the same thing?" question.

---

## Open follow-ups (v2)

1. ATM PnL writer cache strategy (per-session ATM-strike lookup cache; cache key `(symbol, valid_from_session_date)`) — Step 3 implementation.
2. Source preference `hist_option_bars_1m` (canonical) → `option_chain_snapshots` (5m fallback) — Step 3 implementation.
3. Wave 2 detector inheritance — 10 remaining ADR-004 primitives will populate the same 9 new columns via the extended writer; no schema change expected.
4. `time_to_mfe_min` granularity — integer minutes; if sub-minute granularity becomes useful, add `time_to_mfe_sec` column rather than re-typing.
5. **NEW v2:** `option_pnl_30m` + `option_pnl_eod` permanent removal — deprecated-in-place by v2; file separate cleanup ADR if future audit confirms no consumer references; defer to dedicated session.
6. **NEW v2:** Doc Protocol v4 Rule 10 amendment proposal — require `information_schema.columns` pre-flight in schema-affecting ADR Context sections. File at S32 close for operator decision.
7. **NEW v2:** `merdian_reference.json` table inventory audit — sweep all `contamination_notes` for similar "only X column" simplifications that may have drifted from live schema; queue as TD if multiple findings.

---

*ADR-010 v2 supersedes v1 same-session per Doc Protocol v4 Rule 11.4 supersession discipline. Acceptance gates ENH-100 build steps 3–5 (writer extension → backfill → 100-sample falsification audit). v1 → v2 supersession + mechanical follow-throughs land at S32 close: Decision Index Pending ADRs table updated with v2 supersession note; CLAUDE.md settled-decisions reflects v2 net-9-columns + deployment-finding lesson; Assumption Register §D.14 cross-ref updated; merdian_reference.json `ict_primitive_outcomes.contamination_notes` rewritten; Enhancement Register ENH-100 detail block updated 13→9 net-new + collision audit.*
