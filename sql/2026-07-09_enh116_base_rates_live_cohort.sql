-- 2026-07-09_enh116_base_rates_live_cohort.sql
-- ENH-116 Phase-B — segregate the base-rate surface to the LIVE four-lens cohort.
--
-- WHY: the 65-row seed (source='expiry_memory_s62') was labeled gamma-only — reconcile()
-- ran with div hardcoded 'NEUTRAL' ([M4] in backfill_expiry_outcomes.py), so every seed row
-- is RANGE/ALIGNED and can only ever be RANGE. A live verdict is a FOUR-lens read; pooling
-- the two in one cell blends a v1 gamma-only prior with a v2 four-lens prior (soft B29). The
-- only cell where the seed can contaminate a live note is RANGE/ALIGNED (the seed's cells).
--
-- FIX: the note surface reads live-cohort only. Seed rows stay in expiry_outcomes untouched
-- (do-not-re-run-the-seed respected) — just off the base-rate surface. The note/console panel
-- go honestly thin for four-lens regimes until forward accrual fills them; correct, not a
-- regression. CREATE OR REPLACE preserves the existing anon SELECT grant on the view.
--
-- This is the DEPLOYED view body (from pg_get_viewdef) with ONE predicate added:
--   WHERE resolved IS NOT NULL  ->  WHERE resolved IS NOT NULL AND source = 'expiry_memory_live'
-- Aggregation math is byte-identical to what was deployed; nothing else changed.

CREATE OR REPLACE VIEW public.v_expiry_base_rates AS
 SELECT ambient_regime,
    lens_alignment,
    expiry_type,
    count(*) AS n,
    round(avg((resolved = 'PINNED'::text)::integer) * 100::numeric, 1) AS pinned_pct,
    round(avg((resolved = 'BROKE_UP'::text)::integer) * 100::numeric, 1) AS broke_up_pct,
    round(avg((resolved = 'BROKE_DOWN'::text)::integer) * 100::numeric, 1) AS broke_down_pct,
        CASE
            WHEN sum((resolved = 'BROKE_UP'::text)::integer) > sum((resolved = 'BROKE_DOWN'::text)::integer) THEN 'UP'::text
            WHEN sum((resolved = 'BROKE_DOWN'::text)::integer) > sum((resolved = 'BROKE_UP'::text)::integer) THEN 'DOWN'::text
            ELSE 'MIXED'::text
        END AS dominant_break,
    round(avg(abs(settlement_vs_open_pin_pct)), 3) AS avg_abs_settle_pct,
    round(avg(intraday_range_pct), 3) AS avg_range_pct
   FROM expiry_outcomes
  WHERE resolved IS NOT NULL AND source = 'expiry_memory_live'
  GROUP BY ambient_regime, lens_alignment, expiry_type;
