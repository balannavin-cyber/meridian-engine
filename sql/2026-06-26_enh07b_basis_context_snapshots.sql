-- ENH-07 (B): basis-velocity context — Measure-stage table.
-- Display-not-gate per S37/S57. Forward-cohort accrual; one row per
-- (symbol, ts). Run once in the Supabase SQL editor.

create table if not exists public.basis_context_snapshots (
    id                bigint generated always as identity primary key,
    ts                timestamptz not null,
    symbol            text        not null,
    basis             numeric,            -- futures - spot (points), at `now`
    basis_pct_now     numeric,            -- basis as % of spot, at `now`
    basis_pct_prev    numeric,            -- basis %, ~window_min earlier
    basis_velocity_pp numeric,            -- basis_pct_now - basis_pct_prev (pp)
    window_min        integer,            -- actual minutes between now and prev
    spot_now          numeric,
    spot_delta        numeric,            -- spot_now - spot_prev (points)
    context_label     text,              -- NULL when velocity not computable
    created_at        timestamptz not null default now(),
    constraint uq_basis_context_symbol_ts unique (symbol, ts),
    constraint chk_basis_context_label_valid
        check (context_label is null or context_label in
            ('LONG_BUILD', 'WEAK_LONG', 'SHORT_BUILD', 'WEAK_SHORT', 'NEUTRAL'))
);

create index if not exists idx_basis_context_symbol_ts
    on public.basis_context_snapshots (symbol, ts desc);

-- NOTE: RLS SELECT-to-anon triplet (ENH-110 pattern) is intentionally NOT
-- applied here. It is added as part of the Marketview tile follow-on, so the
-- table is not exposed to the public anon role before a consumer needs it
-- (avoids the S39 over-grant footgun re-opening).
