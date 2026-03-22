/* ============================================================
MERDIAN
Shadow Signal Snapshots V1

Purpose
-------
Store a parallel shadow-signal output without changing
the live signal engine.

This table is for Phase 3 Shadow testing only.
No live action logic is changed by this table.
============================================================ */

create table if not exists public.shadow_signal_snapshots (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    ts timestamptz not null,
    market_state_ts timestamptz,
    symbol text not null,

    expiry_date date,
    expiry_type text,
    dte integer,
    spot numeric,

    baseline_signal_id bigint,
    baseline_action text,
    baseline_trade_allowed boolean,
    baseline_entry_quality text,
    baseline_direction_bias text,
    baseline_confidence_score numeric,

    shadow_action text,
    shadow_trade_allowed boolean,
    shadow_entry_quality text,
    shadow_direction_bias text,
    shadow_confidence_score numeric,

    shadow_delta_confidence numeric,
    shadow_decision_changed boolean,

    gamma_regime text,
    breadth_regime text,
    breadth_score numeric,
    volatility_regime text,

    wcb_regime text,
    wcb_score numeric,
    wcb_alignment text,
    wcb_weight_coverage_pct numeric,
    breadth_wcb_relationship text,

    shadow_policy_version text,
    reasons jsonb,
    cautions jsonb,
    raw jsonb
);

create index if not exists idx_shadow_signal_snapshots_symbol_created_at
on public.shadow_signal_snapshots (symbol, created_at desc);

create index if not exists idx_shadow_signal_snapshots_market_state_ts
on public.shadow_signal_snapshots (market_state_ts);

create index if not exists idx_shadow_signal_snapshots_shadow_policy_version
on public.shadow_signal_snapshots (shadow_policy_version);

comment on table public.shadow_signal_snapshots is
'Parallel shadow-signal outputs for MERDIAN Phase 3 shadow testing.';

comment on column public.shadow_signal_snapshots.shadow_policy_version is
'Version label for the shadow policy used to compute the shadow signal.';

comment on column public.shadow_signal_snapshots.shadow_decision_changed is
'True when shadow action or trade_allowed differs from baseline signal.';