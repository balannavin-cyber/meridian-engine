-- ENH-07 (B) historical backfill — basis-velocity cohort from 1m bars.
-- Separate from live basis_context_snapshots (different source tables /
-- cadence / a known IST bar_ts mislabel on futures — see TD-S61-NEW-2).
-- Run once in the Supabase SQL editor before backfill_basis_context.py.

create table if not exists public.hist_basis_context (
    id                bigint generated always as identity primary key,
    ts                timestamptz not null,   -- IST-clock-as-UTC (matches hist_*_bars_1m
    --                                            source convention; -5h30m for true UTC.
    --                                            See TD-S61-NEW-2)
    symbol            text        not null,
    contract_series   smallint,               -- front series used (NIFTY=1, SENSEX=0)
    expiry_date       date,                   -- populated for SENSEX; NULL for NIFTY
    basis             numeric,
    basis_pct_now     numeric,                -- percent, = basis/spot*100 (matches live)
    basis_pct_prev    numeric,
    basis_velocity_pp numeric,
    window_min        integer,
    spot_now          numeric,
    spot_delta        numeric,
    context_label     text,
    source            text        not null default 'hist_backfill',
    created_at        timestamptz not null default now(),
    constraint uq_hist_basis_context_symbol_ts unique (symbol, ts),
    constraint chk_hist_basis_context_label_valid
        check (context_label is null or context_label in
            ('LONG_BUILD', 'WEAK_LONG', 'SHORT_BUILD', 'WEAK_SHORT', 'NEUTRAL'))
);

create index if not exists idx_hist_basis_context_symbol_ts
    on public.hist_basis_context (symbol, ts desc);
