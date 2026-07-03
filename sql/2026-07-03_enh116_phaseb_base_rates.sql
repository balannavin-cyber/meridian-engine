-- ============================================================================
-- ENH-116 Phase B — expiry-memory base rates  ·  v_expiry_base_rates
-- ----------------------------------------------------------------------------
-- Session   : S64 (2026-07-03)
-- Spec       : docs/decisions/ENH-116-ambient-environment-intelligence.md (build seq step 8)
-- Governance : display-not-gate; the labeled event-store (expiry_outcomes) queried
--              for conditional base rates. Stores, does not predict. N-gated at read.
--
-- Conditioning key: (ambient_regime, lens_alignment, expiry_type) — the same key the
-- Tier-1 verdict carries ("DISTRIBUTION · lenses ALIGNED · pin-hold 61% N=23").
--
-- NOTE on the current seed: the S64 backfill labeled historical ambient state with
-- breadth NULL, so every seeded row is ambient_regime=RANGE / lens_alignment=ALIGNED.
-- Therefore TODAY the only discriminating dimension is expiry_type (weekly vs monthly);
-- the ambient_regime / lens_alignment cells richen only as FORWARD expiries accrue under
-- the live v2 reconcile (which needs the forward-accrual labeler — the companion piece).
-- N is exposed raw; consumers apply their own N-floor and read "insufficient N" below it.
-- ============================================================================

create or replace view public.v_expiry_base_rates as
select
    ambient_regime,
    lens_alignment,
    expiry_type,
    count(*)                                                 as n,
    round(avg((resolved = 'PINNED')::int)     * 100, 1)      as pinned_pct,
    round(avg((resolved = 'BROKE_UP')::int)   * 100, 1)      as broke_up_pct,
    round(avg((resolved = 'BROKE_DOWN')::int) * 100, 1)      as broke_down_pct,
    case
        when sum((resolved = 'BROKE_UP')::int) > sum((resolved = 'BROKE_DOWN')::int) then 'UP'
        when sum((resolved = 'BROKE_DOWN')::int) > sum((resolved = 'BROKE_UP')::int) then 'DOWN'
        else 'MIXED'
    end                                                      as dominant_break,
    round(avg(abs(settlement_vs_open_pin_pct))::numeric, 3)  as avg_abs_settle_pct,
    round(avg(intraday_range_pct)::numeric, 3)               as avg_range_pct
from public.expiry_outcomes
where resolved is not null
group by ambient_regime, lens_alignment, expiry_type;

-- anon read for the future Marketview Tier-3 panel (S39 RLS/grant discipline);
-- the compiler reads via service role and needs no grant.
grant select on public.v_expiry_base_rates to anon;
