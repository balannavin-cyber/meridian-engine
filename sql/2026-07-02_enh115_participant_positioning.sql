-- ENH-115 P1 — participant positioning + cash flow (source-only; display-not-gate).
-- Applied via Supabase SQL editor (house convention). NSE + BSE both.

-- Raw participant-wise OI, one row per (exchange, trade_date, participant).
-- Columns mirror the NSE fao_participant_oi CSV verbatim; BSE maps to the same shape.
create table if not exists public.participant_oi_daily (
    id                 bigint generated always as identity primary key,
    exchange           text        not null,   -- 'NSE' | 'BSE'
    trade_date         date        not null,
    participant        text        not null,   -- 'Client' | 'DII' | 'FII' | 'Pro' | 'TOTAL'
    fut_idx_long       bigint,
    fut_idx_short      bigint,
    fut_stk_long       bigint,
    fut_stk_short      bigint,
    opt_idx_call_long  bigint,
    opt_idx_put_long   bigint,
    opt_idx_call_short bigint,
    opt_idx_put_short  bigint,
    opt_stk_call_long  bigint,
    opt_stk_put_long   bigint,
    opt_stk_call_short bigint,
    opt_stk_put_short  bigint,
    total_long         bigint,
    total_short        bigint,
    source             text,
    created_at         timestamptz not null default now(),
    constraint participant_oi_daily_uq unique (exchange, trade_date, participant),
    constraint participant_oi_daily_participant_ck
        check (participant in ('Client','DII','FII','Pro','TOTAL')),
    constraint participant_oi_daily_exchange_ck
        check (exchange in ('NSE','BSE'))
);
create index if not exists ix_participant_oi_daily_date
    on public.participant_oi_daily (trade_date, exchange);

-- Cash-market FII/DII net (₹Cr). The NSE report is consolidated NSE+BSE+MSEI,
-- so one row per trade_date at scope='NSE_BSE_MSEI'. buy/sell kept when present.
create table if not exists public.fii_dii_cash_daily (
    id           bigint generated always as identity primary key,
    trade_date   date        not null,
    scope        text        not null default 'NSE_BSE_MSEI',
    fii_buy_cr   numeric,
    fii_sell_cr  numeric,
    fii_net_cr   numeric,
    dii_buy_cr   numeric,
    dii_sell_cr  numeric,
    dii_net_cr   numeric,
    source       text,
    created_at   timestamptz not null default now(),
    constraint fii_dii_cash_daily_uq unique (trade_date, scope)
);
create index if not exists ix_fii_dii_cash_daily_date
    on public.fii_dii_cash_daily (trade_date);

-- Freshness read for the ADR-018 recency guard: newest participant row per exchange.
-- Consumers (ENH-116 Lens 3) compare trade_date to the trading calendar and flag,
-- never silently tilt on a stale board.
create or replace view public.v_participant_oi_latest as
select distinct on (exchange) exchange, trade_date, created_at
from   public.participant_oi_daily
order  by exchange, trade_date desc;
