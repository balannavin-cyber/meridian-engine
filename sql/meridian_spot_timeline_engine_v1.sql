/* ============================================================
MERDIAN
Spot Timeline Engine V1

Purpose
-------
Create a dedicated spot timeline table for index spot history,
bootstrapped initially from gamma_metrics.spot.

This table will become the canonical source for:
- +15m
- +30m
- +60m
- EOD
outcome lookups.

No live signal logic changes in this step.
============================================================ */


/* ============================================================
A. Core table
============================================================ */
create table if not exists public.market_spot_snapshots (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    ts timestamptz not null,
    symbol text not null,
    spot numeric not null,
    source_table text not null,
    source_id text,
    raw jsonb
);


/* ============================================================
B. Indexes
============================================================ */
create index if not exists idx_market_spot_snapshots_symbol_ts
on public.market_spot_snapshots (symbol, ts desc);

create index if not exists idx_market_spot_snapshots_ts
on public.market_spot_snapshots (ts desc);

create unique index if not exists uq_market_spot_snapshots_symbol_ts_source
on public.market_spot_snapshots (symbol, ts, source_table);


/* ============================================================
C. Comments
============================================================ */
comment on table public.market_spot_snapshots is
'Canonical spot timeline table for MERDIAN horizon lookups and outcome evaluation.';

comment on column public.market_spot_snapshots.source_table is
'Origin table for the spot reading, e.g. gamma_metrics.';

comment on column public.market_spot_snapshots.source_id is
'Optional originating row id from the source table, stored as text to support uuid or bigint ids.';


/* ============================================================
D. Initial backfill from gamma_metrics
============================================================ */
insert into public.market_spot_snapshots (
    ts,
    symbol,
    spot,
    source_table,
    source_id,
    raw
)
select
    gm.ts,
    gm.symbol,
    gm.spot,
    'gamma_metrics' as source_table,
    gm.id::text as source_id,
    jsonb_build_object(
        'backfill_source', 'meridian_spot_timeline_engine_v1.sql',
        'gamma_run_id', gm.run_id
    ) as raw
from public.gamma_metrics gm
where gm.symbol in ('NIFTY', 'SENSEX')
  and gm.spot is not null
on conflict (symbol, ts, source_table) do nothing;