# ADR-014 — Per-strike GEX schema, sign convention, and writer placement (ENH-80)

| Field | Value |
|---|---|
| Status | Proposed (S37 2026-05-25 — to be moved to Accepted on first clean live-fire cycle with falsification pass) |
| Date decided | 2026-05-25 |
| Date documented | 2026-05-25 |
| Session | Session 37 |
| Supersedes | ADR-002 v2 §148 *schema only* (table name preserved as `gex_strike_snapshots`; column set deviates — see §3) — philosophical principles P1–P6 of ADR-002 v2 are unaffected |
| Related ENH | ENH-80 (this ADR is the build doctrine for ENH-80); ENH-81 Positioning Landscape (downstream consumer of `gex_strike_snapshots` rows aggregated to scalars); ENH-82 Pin Risk Score continuous (downstream consumer; populates `is_pin_candidate_bool` once threshold calibrated); ENH-98 vanna/charm (additional per-strike columns may land later under separate ADR); ENH-109 Breeze graduation (full-chain historical backfill source for ENH-80 history if Breeze graduates canonical) |
| Related TD | TD-094 RECLASSIFIED-STALE S29 (vendor data populated `hist_option_bars_1m.oi` 99.9% — provides historical OI substrate for backfill); TD-S35-NEW-1 (HOCS strike-coverage structural limit — bounds backfill coverage post-2026-04-01); TD-S36-NEW-1 (gamma_metrics Apr-early-May row gap — overlaps the backfill window for ENH-80 history) |
| Related commits | (S37 close commit TBD — DDL + writer patch + this ADR + Decision Index row) |

---

## 1. Context

ADR-002 v2 §148 (S27 2026-05-11) proposed a per-strike GEX time-series table `gex_strike_snapshots` as the substrate for Phase 3 capability (Principles P2–P5 — force, trapped positioning, regime velocity, local-vs-net divergence). The proposed schema had a single `oi bigint` column and two structural pin markers (`is_local_max`, `is_flip_zone`).

S29 unblocked the build:
- TD-094 RECLASSIFIED-STALE (vendor data populated `hist_option_bars_1m.oi` 99.9% across 12 months) provided the historical OI substrate for backfill.
- ENH-97 PIVOTED to logging-only — the previously-assumed P7 4-way regime gate dependency dissolved (logging-only doesn't gate ENH-80).

S36 closed the Layer 1 (capture-layer) resilience build via ENH-99. Per operator's S37 sequencing directive (capture/integrity → compute → display → execution), ENH-80 is the first Layer 2 (compute) build.

S37 sequencing requires concrete schema, sign convention, and writer-placement decisions before code lands. Three deviations from ADR-002 v2 §148 surfaced during scope confirmation:

1. **OI split.** Single `oi` discards call-writer vs put-writer attribution. Dealers writing calls dampen above spot; dealers writing puts dampen below spot. The Positioning Landscape (ENH-81) Dealer Flow Simulator needs the asymmetry to reason about asymmetric scenarios (e.g. +0.5% move drags through call-writer cluster; −0.5% move drags through put-writer cluster). Aggregating to a single `oi` column loses this at the storage layer.
2. **Pin marker semantics.** ADR-002 v2 §148's `is_local_max` + `is_flip_zone` are mechanical (no threshold-fitting required) and can be populated S37. The compound `is_pin_candidate_bool` (= `is_local_max AND |gex_cr| > τ` for some calibrated τ) is a Pin Risk Score concept (ENH-82) and depends on calibration that doesn't exist yet. Forward-compatible answer: store `is_pin_candidate_bool` NULLable in the schema now so ENH-82 can populate without a DDL migration, but ENH-80 writer leaves it NULL.
3. **Storage shape.** A JSONB column on `gamma_metrics` was considered. Rejected — see §3.

A sign convention codification is overdue. ADR-002 v2 P3 ("trapped seller positioning — acceleration zone") implies a directional reading of GEX signs but never codifies "positive = dampening vs negative = amplifying". The per-strike layer needs the convention codified explicitly because the falsification rule (per-strike sum == net_gex) is sign-sensitive.

---

## 2. Decision

### 2.1 Storage shape

**New normalized table `gex_strike_snapshots`.** Not a JSONB column on `gamma_metrics`.

Rationale: the dominant access patterns are (a) keyed reads at a fixed `(symbol, ts)` to fetch the full strike row group, (b) range queries on strike for Positioning Landscape window aggregation (±100Δ from spot), (c) GROUP BY joins to `gamma_metrics.net_gex` for the falsification check. All three want a normalized indexed table. JSONB enforces application-side filtering and breaks the falsification join.

### 2.2 Final schema

```sql
CREATE TABLE IF NOT EXISTS public.gex_strike_snapshots (
    id                       uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id                   uuid NOT NULL,
    symbol                   text NOT NULL,
    ts                       timestamptz NOT NULL,
    expiry_date              date NOT NULL,
    dte                      integer NOT NULL,
    strike                   numeric NOT NULL,
    spot                     numeric NOT NULL,
    gamma                    numeric,
    oi_call                  bigint,
    oi_put                   bigint,
    gex_cr                   numeric NOT NULL,
    is_local_max             boolean NOT NULL DEFAULT false,
    is_flip_zone             boolean NOT NULL DEFAULT false,
    is_pin_candidate_bool    boolean,
    created_at               timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_gss_run_strike_expiry UNIQUE (run_id, strike, expiry_date)
);
CREATE INDEX IF NOT EXISTS idx_gss_symbol_ts        ON public.gex_strike_snapshots (symbol, ts DESC);
CREATE INDEX IF NOT EXISTS idx_gss_symbol_exp_ts    ON public.gex_strike_snapshots (symbol, expiry_date, ts DESC);
CREATE INDEX IF NOT EXISTS idx_gss_run_id           ON public.gex_strike_snapshots (run_id);
CREATE INDEX IF NOT EXISTS idx_gss_symbol_ts_strike ON public.gex_strike_snapshots (symbol, ts DESC, strike);
```

Deviations from ADR-002 v2 §148:
- `oi bigint` → `oi_call bigint` + `oi_put bigint` (split per §1 rationale)
- `is_pin_candidate_bool boolean` NULLable added (forward-compatible landing for ENH-82)
- `gex_cr` is `NOT NULL` (was unmarked); `spot` is `NOT NULL` (was unmarked); pin markers default `false` (was unmarked)
- `UNIQUE (run_id, strike, expiry_date)` added — dedup safety on writer retry
- `idx_gss_symbol_ts_strike` added — supports range queries on strike within `(symbol, ts)`

### 2.3 Sign convention

**Positive `gex_cr` = dampening (dealer long gamma at this strike; dealer sells rallies / buys dips).**
**Negative `gex_cr` = amplifying (dealer short gamma at this strike; dealer buys rallies / sells dips).**

This matches the existing `gamma_metrics.net_gex` sign convention as established by `compute_gamma_metrics_local.py` at S27 commit `241f943` (validated S36 D.18.1 writer-state read — `/1e7` Cr conversion intact, sign-preserving). The falsification rule in §2.5 auto-verifies this match.

Per-strike `gex_cr` formula:
```
gex_cr = (oi_call × gamma_call - oi_put × gamma_put) × spot² × multiplier / 1e7
```
where `multiplier` is the index lot/contract multiplier (NIFTY 75, SENSEX 20 — defer to existing `compute_gamma_metrics_local.py` constants). The `oi_call × gamma_call − oi_put × gamma_put` term yields positive (dealer-long) when call writers dominate at the strike, negative (dealer-short) when put writers dominate, matching the convention above.

Codified to Assumption Register §D.18.5 at S37 close.

### 2.4 Writer placement

**Extension of `compute_gamma_metrics_local.py` — not a new module.**

Rationale: that script already pulls the chain cache once per 5-min cycle, generates the `run_id`, knows `spot`, and computes per-strike `gamma × OI × spot²` as the input to the existing `net_gex` aggregation. A new module duplicates the chain pull, forks the `run_id` lineage (breaking the falsification join), and doubles the Dhan/Kite API budget on the live path.

The writer extension is a single additional compute pass inside the same 5-min cycle: build the per-strike row list during the existing aggregation, then bulk-insert into `gex_strike_snapshots` immediately after the `gamma_metrics` row insert, both keyed on the same `run_id`.

Pin marker population:
- `is_local_max`: neighbor-comparison `|gex_cr[i]| > |gex_cr[i±1]|` per (symbol, ts, expiry) row group — multiple Trues per group expected (pin cluster + acceleration cluster both light up). Endpoints (first/last strike in group) get `is_local_max = false` regardless. This matches the practitioner gamma-dashboard pattern of multiple highlighted strikes per snapshot.
- `is_flip_zone`: True at strike `i` if `sign(gex_cr[i]) != sign(gex_cr[i-1])` within the row group.
- `is_pin_candidate_bool`: left NULL by ENH-80 writer. ENH-82 populates once Pin Risk Score threshold calibrated.

### 2.5 Falsification rule

Per `run_id`, the sum of `gex_cr` over all strikes and expiries must equal `gamma_metrics.net_gex` for the same `run_id` within ±0.01 Cr tolerance:

```sql
SELECT
    g.symbol,
    g.run_id,
    g.net_gex                            AS net_gex_metrics_cr,
    COALESCE(SUM(s.gex_cr), 0)           AS net_gex_from_strikes_cr,
    g.net_gex - COALESCE(SUM(s.gex_cr), 0) AS diff_cr
FROM gamma_metrics g
LEFT JOIN gex_strike_snapshots s ON s.run_id = g.run_id
WHERE g.ts >= now() - interval '1 day'
GROUP BY g.symbol, g.run_id, g.net_gex
HAVING ABS(g.net_gex - COALESCE(SUM(s.gex_cr), 0)) > 0.01
ORDER BY g.run_id DESC;
```

Pass criterion: zero rows returned across at least one full live cycle (NIFTY + SENSEX, both expiries each). Pass → ADR-014 moves to Accepted at S37 close. Fail → halt writer deployment, surface the diff, investigate sign/units before re-deploying.

---

## 3. Alternatives considered

**JSONB column on `gamma_metrics` (e.g. `strike_gex_jsonb jsonb`).** Rejected. Defeats keyed reads at strike level; range queries on strike require application-side parsing; falsification join becomes a `jsonb_each → SUM` over the column which loses index acceleration; ENH-81 Positioning Landscape windowing (±100Δ from spot) becomes O(N) parse per row. Storage savings are marginal — at 78 cycles/day × 2 symbols × ~100 strikes/cycle × ~3 expiries = ~46,800 rows/day, table size grows ~10 MB/month uncompressed, negligible against the existing `option_chain_snapshots` footprint.

**Single `oi` column matching ADR-002 v2 §148 verbatim.** Rejected per §1 rationale. The call-writer vs put-writer attribution is load-bearing for Layer 2.

**New module `compute_gex_strikes_local.py` separate from `compute_gamma_metrics_local.py`.** Rejected per §2.4 rationale. Duplicated chain pull, forked `run_id`, doubled API budget on the live path.

**Compute `is_pin_candidate_bool` heuristically S37 (e.g. top-3 by |gex_cr| per group).** Considered but rejected. Heuristic without empirical calibration would have to be re-populated when ENH-82 calibrates the actual threshold — a TRUNCATE+recompute over historical data. Leaving NULL until ENH-82 lands avoids the recompute and preserves the column for forward-compatible writes.

**Defer falsification to S38.** Rejected. Per §D.18.1 (S36 lesson — writer-state-vs-data-state diagnosis ordering), shipping a writer without an immediate downstream falsification check is the same failure mode that cost 7 sessions on TD-S30-CANDIDATE-1. The falsification SQL is ~10 lines; running it on the first clean cycle is non-negotiable.

---

## 4. Consequences

**Positive:**
- ENH-81 Positioning Landscape unblocked — five scalars (NET Γ IN WINDOW, Σ DAMPEN, Σ AMPLIFY, STRONGEST DAMPEN, STRONGEST AMPLIFY, Σ TO EXPIRY) and four-scenario Dealer Flow Simulator have a row-level substrate.
- ENH-82 Pin Risk Score continuous unblocked — `is_pin_candidate_bool` lands forward-compatibly.
- Sign convention codified — Layer 2 consumers (buyer-tier Phase 1, writer-tier Phase 2/3) read a single consistent convention.
- Falsification rule provides immediate Layer 2 ↔ Layer 1 integrity check on every cycle. Builds in the §D.18.1 discipline by construction.

**Negative:**
- ~46,800 rows/day write load on Supabase (NIFTY + SENSEX × ~100 strikes × ~3 expiries × 78 cycles). Manageable but flagged for monitoring against Supabase write budget — particularly during weekly-expiry days when chain depth peaks.
- Schema deviates from ADR-002 v2 §148. Anyone reading the ADR-002 v2 schema block expecting the literal table to match will hit a delta. Cross-reference markers added to ADR-002 v2 §148 (or via this ADR's Supersedes field — schema only, principles unaffected).
- Backfill of `gex_strike_snapshots` from `hist_option_bars_1m` is gated on per-row `gamma` availability and strike-coverage limits. Backfill scope and cohort scoping are explicitly out of scope for ADR-014 — to be addressed in a follow-up ADR or in ENH-80 backfill spec.

---

## 5. What this ADR does NOT decide

- **Backfill strategy.** Whether to backfill ENH-80 from `hist_option_bars_1m` (S29 unblocked), from Breeze (ENH-109 graduation pending ADR-013), or both. ADR-014 ships the forward writer only. Backfill is a separate decision.
- **`is_pin_candidate_bool` threshold τ.** Calibration is ENH-82's responsibility.
- **`gex_per_oi` derived column.** Operator's S37 prompt mentioned this as a candidate column; rejected for storage in §2.2 as it's cheaply derivable at query time as `gex_cr / NULLIF(oi_call + oi_put, 0)`. If query-time derivation proves painful in practice (e.g. PostgREST overhead), a generated column or materialized view can be added later — no ADR required for either.
- **Per-strike vanna/charm columns (ENH-98).** Out of scope. ENH-98 will land via its own ADR if and when Phase 2 deployment plan commits.
- **AWS migration of the writer.** Out of scope. Per CLAUDE.md / ADR-006 (PROPOSED), writer canonical placement for the derived stage is Local with AWS shadow; ENH-80 follows that pattern without re-litigating.

---

## 6. Cross-references

- **ADR-002 v2 §148** — original ENH-80 schema proposal; this ADR supersedes the schema block only, principles P1–P6 are unaffected.
- **Assumption Register §D.18.1** — writer-state-vs-data-state diagnosis ordering; falsification rule §2.5 is the application of this lesson at build time.
- **Assumption Register §D.18.5** (new at S37 close) — sign convention codification.
- **`tech_debt.md` TD-094 RECLASSIFIED-STALE S29** — vendor OI populated 99.9% (substrate for backfill).
- **`tech_debt.md` TD-S35-NEW-1** — HOCS strike-coverage structural limit (bounds backfill post-2026-04-01).
- **`tech_debt.md` TD-S36-NEW-1** — gamma_metrics Apr-early-May row gap (overlaps backfill window).
- **`MERDIAN_Enhancement_Register.md` ENH-80** — full spec to be expanded with SHIPPED detail block at S37 close once writer lands.
- **`MERDIAN_System_Map.md`** — §A and §B sections to add `gex_strike_snapshots` writer + table entry at S37 close.

---

## 7. Status transitions

- **2026-05-25 (S37):** PROPOSED. Awaiting first clean live-fire cycle with falsification pass.
- **Move to ACCEPTED:** when one full live cycle (NIFTY + SENSEX, both expiries each) produces zero rows from the §2.5 falsification SQL.
- **Move to IMPLEMENTED:** when the writer has run continuously for 5 trading sessions without falsification regression.

*End ADR-014.*
