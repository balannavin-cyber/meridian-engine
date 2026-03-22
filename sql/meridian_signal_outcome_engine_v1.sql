/* ============================================================
MERDIAN
Signal Outcome Engine V1

Purpose
-------
Create the first outcome-tracking tables for:
1. baseline signals
2. shadow signals

These tables let MERDIAN measure what happened AFTER a signal.

This is read/write infrastructure only.
It does NOT change live signal logic.
============================================================ */


/* ============================================================
A. Baseline signal outcomes
============================================================ */

create table if not exists public.signal_outcomes (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    signal_id bigint not null,
    signal_ts timestamptz not null,
    symbol text not null,

    action text not null,
    trade_allowed boolean not null,
    direction_bias text,
    entry_quality text,
    confidence_score numeric,

    entry_spot numeric,
    entry_reference_price numeric,

    outcome_15m_spot numeric,
    outcome_30m_spot numeric,
    outcome_60m_spot numeric,
    outcome_eod_spot numeric,

    move_15m_points numeric,
    move_30m_points numeric,
    move_60m_points numeric,
    move_eod_points numeric,

    move_15m_pct numeric,
    move_30m_pct numeric,
    move_60m_pct numeric,
    move_eod_pct numeric,

    outcome_label_15m text,
    outcome_label_30m text,
    outcome_label_60m text,
    outcome_label_eod text,

    mfe_points_60m numeric,
    mae_points_60m numeric,

    outcome_policy_version text not null default 'BASELINE_SIGNAL_V1',
    raw jsonb
);

create index if not exists idx_signal_outcomes_signal_id
on public.signal_outcomes (signal_id);

create index if not exists idx_signal_outcomes_symbol_signal_ts
on public.signal_outcomes (symbol, signal_ts desc);

create index if not exists idx_signal_outcomes_outcome_policy_version
on public.signal_outcomes (outcome_policy_version);


/* ============================================================
B. Shadow signal outcomes
============================================================ */

create table if not exists public.shadow_signal_outcomes (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    shadow_signal_id bigint not null,
    shadow_policy_version text not null,
    signal_ts timestamptz not null,
    symbol text not null,

    baseline_action text,
    baseline_trade_allowed boolean,
    baseline_direction_bias text,
    baseline_entry_quality text,
    baseline_confidence_score numeric,

    shadow_action text not null,
    shadow_trade_allowed boolean not null,
    shadow_direction_bias text,
    shadow_entry_quality text,
    shadow_confidence_score numeric,
    shadow_delta_confidence numeric,
    shadow_decision_changed boolean,

    breadth_wcb_relationship text,
    wcb_regime text,
    wcb_score numeric,
    wcb_alignment text,
    wcb_weight_coverage_pct numeric,

    entry_spot numeric,
    entry_reference_price numeric,

    outcome_15m_spot numeric,
    outcome_30m_spot numeric,
    outcome_60m_spot numeric,
    outcome_eod_spot numeric,

    move_15m_points numeric,
    move_30m_points numeric,
    move_60m_points numeric,
    move_eod_points numeric,

    move_15m_pct numeric,
    move_30m_pct numeric,
    move_60m_pct numeric,
    move_eod_pct numeric,

    outcome_label_15m text,
    outcome_label_30m text,
    outcome_label_60m text,
    outcome_label_eod text,

    mfe_points_60m numeric,
    mae_points_60m numeric,

    raw jsonb
);

create index if not exists idx_shadow_signal_outcomes_shadow_signal_id
on public.shadow_signal_outcomes (shadow_signal_id);

create index if not exists idx_shadow_signal_outcomes_symbol_signal_ts
on public.shadow_signal_outcomes (symbol, signal_ts desc);

create index if not exists idx_shadow_signal_outcomes_policy
on public.shadow_signal_outcomes (shadow_policy_version);


/* ============================================================
C. Helpful comments
============================================================ */

comment on table public.signal_outcomes is
'Stores realized post-signal outcome measurements for baseline MERDIAN signals.';

comment on table public.shadow_signal_outcomes is
'Stores realized post-signal outcome measurements for MERDIAN shadow signals, split by shadow policy version.';

comment on column public.signal_outcomes.entry_reference_price is
'Optional future-use field for option premium or other tradable entry reference. For now this may match entry_spot or remain null.';

comment on column public.shadow_signal_outcomes.entry_reference_price is
'Optional future-use field for option premium or other tradable entry reference. For now this may match entry_spot or remain null.';