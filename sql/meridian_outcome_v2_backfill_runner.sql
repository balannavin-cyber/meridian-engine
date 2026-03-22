/* ============================================================
MERDIAN
Outcome V2 Backfill Runner

Purpose
-------
Upgrade existing stored outcome rows from V1-style storage
to V2-style storage by recomputing horizon fields from
gamma_metrics and updating rows in place.

Updates:
1. public.signal_outcomes
2. public.shadow_signal_outcomes

Notes
-----
- This is an in-place backfill.
- It preserves existing row ids.
- It does NOT create duplicate rows.
- Intraday horizons may remain null if gamma history is sparse.
============================================================ */


/* ============================================================
A. Backfill baseline outcomes -> BASELINE_SIGNAL_V2
============================================================ */
with baseline_computed as (
    select
        so.id,

        g15.spot as outcome_15m_spot,
        g30.spot as outcome_30m_spot,
        g60.spot as outcome_60m_spot,
        geod.spot as outcome_eod_spot,

        g15.ts as ts_15m,
        g30.ts as ts_30m,
        g60.ts as ts_60m,
        geod.ts as ts_eod

    from public.signal_outcomes so

    left join lateral (
        select gm.ts, gm.spot
        from public.gamma_metrics gm
        where gm.symbol = so.symbol
          and gm.ts >= so.signal_ts + interval '15 minutes'
        order by gm.ts asc
        limit 1
    ) g15 on true

    left join lateral (
        select gm.ts, gm.spot
        from public.gamma_metrics gm
        where gm.symbol = so.symbol
          and gm.ts >= so.signal_ts + interval '30 minutes'
        order by gm.ts asc
        limit 1
    ) g30 on true

    left join lateral (
        select gm.ts, gm.spot
        from public.gamma_metrics gm
        where gm.symbol = so.symbol
          and gm.ts >= so.signal_ts + interval '60 minutes'
        order by gm.ts asc
        limit 1
    ) g60 on true

    left join lateral (
        select gm.ts, gm.spot
        from public.gamma_metrics gm
        where gm.symbol = so.symbol
          and gm.ts >= date_trunc('day', so.signal_ts)
          and gm.ts <  date_trunc('day', so.signal_ts) + interval '1 day'
        order by gm.ts desc
        limit 1
    ) geod on true
)
update public.signal_outcomes so
set
    outcome_15m_spot = bc.outcome_15m_spot,
    outcome_30m_spot = bc.outcome_30m_spot,
    outcome_60m_spot = bc.outcome_60m_spot,
    outcome_eod_spot = bc.outcome_eod_spot,

    move_15m_points = case
        when so.entry_spot is null or bc.outcome_15m_spot is null then null
        else round((bc.outcome_15m_spot - so.entry_spot)::numeric, 4)
    end,
    move_30m_points = case
        when so.entry_spot is null or bc.outcome_30m_spot is null then null
        else round((bc.outcome_30m_spot - so.entry_spot)::numeric, 4)
    end,
    move_60m_points = case
        when so.entry_spot is null or bc.outcome_60m_spot is null then null
        else round((bc.outcome_60m_spot - so.entry_spot)::numeric, 4)
    end,
    move_eod_points = case
        when so.entry_spot is null or bc.outcome_eod_spot is null then null
        else round((bc.outcome_eod_spot - so.entry_spot)::numeric, 4)
    end,

    move_15m_pct = case
        when so.entry_spot is null or so.entry_spot = 0 or bc.outcome_15m_spot is null then null
        else round((((bc.outcome_15m_spot - so.entry_spot) / so.entry_spot) * 100.0)::numeric, 6)
    end,
    move_30m_pct = case
        when so.entry_spot is null or so.entry_spot = 0 or bc.outcome_30m_spot is null then null
        else round((((bc.outcome_30m_spot - so.entry_spot) / so.entry_spot) * 100.0)::numeric, 6)
    end,
    move_60m_pct = case
        when so.entry_spot is null or so.entry_spot = 0 or bc.outcome_60m_spot is null then null
        else round((((bc.outcome_60m_spot - so.entry_spot) / so.entry_spot) * 100.0)::numeric, 6)
    end,
    move_eod_pct = case
        when so.entry_spot is null or so.entry_spot = 0 or bc.outcome_eod_spot is null then null
        else round((((bc.outcome_eod_spot - so.entry_spot) / so.entry_spot) * 100.0)::numeric, 6)
    end,

    outcome_label_15m = case
        when so.action = 'DO_NOTHING' then 'NO_TRADE'
        when bc.outcome_15m_spot is null or so.entry_spot is null then null
        when so.action = 'BUY_CE' and bc.outcome_15m_spot > so.entry_spot then 'FAVORABLE'
        when so.action = 'BUY_CE' and bc.outcome_15m_spot < so.entry_spot then 'UNFAVORABLE'
        when so.action = 'BUY_PE' and bc.outcome_15m_spot < so.entry_spot then 'FAVORABLE'
        when so.action = 'BUY_PE' and bc.outcome_15m_spot > so.entry_spot then 'UNFAVORABLE'
        else 'FLAT'
    end,
    outcome_label_30m = case
        when so.action = 'DO_NOTHING' then 'NO_TRADE'
        when bc.outcome_30m_spot is null or so.entry_spot is null then null
        when so.action = 'BUY_CE' and bc.outcome_30m_spot > so.entry_spot then 'FAVORABLE'
        when so.action = 'BUY_CE' and bc.outcome_30m_spot < so.entry_spot then 'UNFAVORABLE'
        when so.action = 'BUY_PE' and bc.outcome_30m_spot < so.entry_spot then 'FAVORABLE'
        when so.action = 'BUY_PE' and bc.outcome_30m_spot > so.entry_spot then 'UNFAVORABLE'
        else 'FLAT'
    end,
    outcome_label_60m = case
        when so.action = 'DO_NOTHING' then 'NO_TRADE'
        when bc.outcome_60m_spot is null or so.entry_spot is null then null
        when so.action = 'BUY_CE' and bc.outcome_60m_spot > so.entry_spot then 'FAVORABLE'
        when so.action = 'BUY_CE' and bc.outcome_60m_spot < so.entry_spot then 'UNFAVORABLE'
        when so.action = 'BUY_PE' and bc.outcome_60m_spot < so.entry_spot then 'FAVORABLE'
        when so.action = 'BUY_PE' and bc.outcome_60m_spot > so.entry_spot then 'UNFAVORABLE'
        else 'FLAT'
    end,
    outcome_label_eod = case
        when so.action = 'DO_NOTHING' then 'NO_TRADE'
        when bc.outcome_eod_spot is null or so.entry_spot is null then null
        when so.action = 'BUY_CE' and bc.outcome_eod_spot > so.entry_spot then 'FAVORABLE'
        when so.action = 'BUY_CE' and bc.outcome_eod_spot < so.entry_spot then 'UNFAVORABLE'
        when so.action = 'BUY_PE' and bc.outcome_eod_spot < so.entry_spot then 'FAVORABLE'
        when so.action = 'BUY_PE' and bc.outcome_eod_spot > so.entry_spot then 'UNFAVORABLE'
        else 'FLAT'
    end,

    mfe_points_60m = case
        when so.action = 'DO_NOTHING' then null
        when so.entry_spot is null then null
        when bc.outcome_15m_spot is null and bc.outcome_30m_spot is null and bc.outcome_60m_spot is null then null
        when so.action = 'BUY_PE' then round(greatest(
            coalesce(so.entry_spot - bc.outcome_15m_spot, -1e15),
            coalesce(so.entry_spot - bc.outcome_30m_spot, -1e15),
            coalesce(so.entry_spot - bc.outcome_60m_spot, -1e15)
        )::numeric, 4)
        else round(greatest(
            coalesce(bc.outcome_15m_spot - so.entry_spot, -1e15),
            coalesce(bc.outcome_30m_spot - so.entry_spot, -1e15),
            coalesce(bc.outcome_60m_spot - so.entry_spot, -1e15)
        )::numeric, 4)
    end,

    mae_points_60m = case
        when so.action = 'DO_NOTHING' then null
        when so.entry_spot is null then null
        when bc.outcome_15m_spot is null and bc.outcome_30m_spot is null and bc.outcome_60m_spot is null then null
        when so.action = 'BUY_PE' then round(least(
            coalesce(so.entry_spot - bc.outcome_15m_spot, 1e15),
            coalesce(so.entry_spot - bc.outcome_30m_spot, 1e15),
            coalesce(so.entry_spot - bc.outcome_60m_spot, 1e15)
        )::numeric, 4)
        else round(least(
            coalesce(bc.outcome_15m_spot - so.entry_spot, 1e15),
            coalesce(bc.outcome_30m_spot - so.entry_spot, 1e15),
            coalesce(bc.outcome_60m_spot - so.entry_spot, 1e15)
        )::numeric, 4)
    end,

    outcome_policy_version = 'BASELINE_SIGNAL_V2',

    raw = coalesce(so.raw, '{}'::jsonb) || jsonb_build_object(
        'source', 'meridian_outcome_v2_backfill_runner.sql',
        'spot_source_table', 'gamma_metrics',
        'horizon_row_ts', jsonb_build_object(
            '15m', bc.ts_15m,
            '30m', bc.ts_30m,
            '60m', bc.ts_60m,
            'eod', bc.ts_eod
        ),
        'note', 'V2 backfill applied from gamma_metrics'
    )
from baseline_computed bc
where so.id = bc.id;


/* ============================================================
B. Backfill shadow outcomes
============================================================ */
with shadow_computed as (
    select
        sso.id,

        g15.spot as outcome_15m_spot,
        g30.spot as outcome_30m_spot,
        g60.spot as outcome_60m_spot,
        geod.spot as outcome_eod_spot,

        g15.ts as ts_15m,
        g30.ts as ts_30m,
        g60.ts as ts_60m,
        geod.ts as ts_eod

    from public.shadow_signal_outcomes sso

    left join lateral (
        select gm.ts, gm.spot
        from public.gamma_metrics gm
        where gm.symbol = sso.symbol
          and gm.ts >= sso.signal_ts + interval '15 minutes'
        order by gm.ts asc
        limit 1
    ) g15 on true

    left join lateral (
        select gm.ts, gm.spot
        from public.gamma_metrics gm
        where gm.symbol = sso.symbol
          and gm.ts >= sso.signal_ts + interval '30 minutes'
        order by gm.ts asc
        limit 1
    ) g30 on true

    left join lateral (
        select gm.ts, gm.spot
        from public.gamma_metrics gm
        where gm.symbol = sso.symbol
          and gm.ts >= sso.signal_ts + interval '60 minutes'
        order by gm.ts asc
        limit 1
    ) g60 on true

    left join lateral (
        select gm.ts, gm.spot
        from public.gamma_metrics gm
        where gm.symbol = sso.symbol
          and gm.ts >= date_trunc('day', sso.signal_ts)
          and gm.ts <  date_trunc('day', sso.signal_ts) + interval '1 day'
        order by gm.ts desc
        limit 1
    ) geod on true
)
update public.shadow_signal_outcomes sso
set
    outcome_15m_spot = sc.outcome_15m_spot,
    outcome_30m_spot = sc.outcome_30m_spot,
    outcome_60m_spot = sc.outcome_60m_spot,
    outcome_eod_spot = sc.outcome_eod_spot,

    move_15m_points = case
        when sso.entry_spot is null or sc.outcome_15m_spot is null then null
        else round((sc.outcome_15m_spot - sso.entry_spot)::numeric, 4)
    end,
    move_30m_points = case
        when sso.entry_spot is null or sc.outcome_30m_spot is null then null
        else round((sc.outcome_30m_spot - sso.entry_spot)::numeric, 4)
    end,
    move_60m_points = case
        when sso.entry_spot is null or sc.outcome_60m_spot is null then null
        else round((sc.outcome_60m_spot - sso.entry_spot)::numeric, 4)
    end,
    move_eod_points = case
        when sso.entry_spot is null or sc.outcome_eod_spot is null then null
        else round((sc.outcome_eod_spot - sso.entry_spot)::numeric, 4)
    end,

    move_15m_pct = case
        when sso.entry_spot is null or sso.entry_spot = 0 or sc.outcome_15m_spot is null then null
        else round((((sc.outcome_15m_spot - sso.entry_spot) / sso.entry_spot) * 100.0)::numeric, 6)
    end,
    move_30m_pct = case
        when sso.entry_spot is null or sso.entry_spot = 0 or sc.outcome_30m_spot is null then null
        else round((((sc.outcome_30m_spot - sso.entry_spot) / sso.entry_spot) * 100.0)::numeric, 6)
    end,
    move_60m_pct = case
        when sso.entry_spot is null or sso.entry_spot = 0 or sc.outcome_60m_spot is null then null
        else round((((sc.outcome_60m_spot - sso.entry_spot) / sso.entry_spot) * 100.0)::numeric, 6)
    end,
    move_eod_pct = case
        when sso.entry_spot is null or sso.entry_spot = 0 or sc.outcome_eod_spot is null then null
        else round((((sc.outcome_eod_spot - sso.entry_spot) / sso.entry_spot) * 100.0)::numeric, 6)
    end,

    outcome_label_15m = case
        when sso.shadow_action = 'DO_NOTHING' then 'NO_TRADE'
        when sc.outcome_15m_spot is null or sso.entry_spot is null then null
        when sso.shadow_action = 'BUY_CE' and sc.outcome_15m_spot > sso.entry_spot then 'FAVORABLE'
        when sso.shadow_action = 'BUY_CE' and sc.outcome_15m_spot < sso.entry_spot then 'UNFAVORABLE'
        when sso.shadow_action = 'BUY_PE' and sc.outcome_15m_spot < sso.entry_spot then 'FAVORABLE'
        when sso.shadow_action = 'BUY_PE' and sc.outcome_15m_spot > sso.entry_spot then 'UNFAVORABLE'
        else 'FLAT'
    end,
    outcome_label_30m = case
        when sso.shadow_action = 'DO_NOTHING' then 'NO_TRADE'
        when sc.outcome_30m_spot is null or sso.entry_spot is null then null
        when sso.shadow_action = 'BUY_CE' and sc.outcome_30m_spot > sso.entry_spot then 'FAVORABLE'
        when sso.shadow_action = 'BUY_CE' and sc.outcome_30m_spot < sso.entry_spot then 'UNFAVORABLE'
        when sso.shadow_action = 'BUY_PE' and sc.outcome_30m_spot < sso.entry_spot then 'FAVORABLE'
        when sso.shadow_action = 'BUY_PE' and sc.outcome_30m_spot > sso.entry_spot then 'UNFAVORABLE'
        else 'FLAT'
    end,
    outcome_label_60m = case
        when sso.shadow_action = 'DO_NOTHING' then 'NO_TRADE'
        when sc.outcome_60m_spot is null or sso.entry_spot is null then null
        when sso.shadow_action = 'BUY_CE' and sc.outcome_60m_spot > sso.entry_spot then 'FAVORABLE'
        when sso.shadow_action = 'BUY_CE' and sc.outcome_60m_spot < sso.entry_spot then 'UNFAVORABLE'
        when sso.shadow_action = 'BUY_PE' and sc.outcome_60m_spot < sso.entry_spot then 'FAVORABLE'
        when sso.shadow_action = 'BUY_PE' and sc.outcome_60m_spot > sso.entry_spot then 'UNFAVORABLE'
        else 'FLAT'
    end,
    outcome_label_eod = case
        when sso.shadow_action = 'DO_NOTHING' then 'NO_TRADE'
        when sc.outcome_eod_spot is null or sso.entry_spot is null then null
        when sso.shadow_action = 'BUY_CE' and sc.outcome_eod_spot > sso.entry_spot then 'FAVORABLE'
        when sso.shadow_action = 'BUY_CE' and sc.outcome_eod_spot < sso.entry_spot then 'UNFAVORABLE'
        when sso.shadow_action = 'BUY_PE' and sc.outcome_eod_spot < sso.entry_spot then 'FAVORABLE'
        when sso.shadow_action = 'BUY_PE' and sc.outcome_eod_spot > sso.entry_spot then 'UNFAVORABLE'
        else 'FLAT'
    end,

    mfe_points_60m = case
        when sso.shadow_action = 'DO_NOTHING' then null
        when sso.entry_spot is null then null
        when sc.outcome_15m_spot is null and sc.outcome_30m_spot is null and sc.outcome_60m_spot is null then null
        when sso.shadow_action = 'BUY_PE' then round(greatest(
            coalesce(sso.entry_spot - sc.outcome_15m_spot, -1e15),
            coalesce(sso.entry_spot - sc.outcome_30m_spot, -1e15),
            coalesce(sso.entry_spot - sc.outcome_60m_spot, -1e15)
        )::numeric, 4)
        else round(greatest(
            coalesce(sc.outcome_15m_spot - sso.entry_spot, -1e15),
            coalesce(sc.outcome_30m_spot - sso.entry_spot, -1e15),
            coalesce(sc.outcome_60m_spot - sso.entry_spot, -1e15)
        )::numeric, 4)
    end,

    mae_points_60m = case
        when sso.shadow_action = 'DO_NOTHING' then null
        when sso.entry_spot is null then null
        when sc.outcome_15m_spot is null and sc.outcome_30m_spot is null and sc.outcome_60m_spot is null then null
        when sso.shadow_action = 'BUY_PE' then round(least(
            coalesce(sso.entry_spot - sc.outcome_15m_spot, 1e15),
            coalesce(sso.entry_spot - sc.outcome_30m_spot, 1e15),
            coalesce(sso.entry_spot - sc.outcome_60m_spot, 1e15)
        )::numeric, 4)
        else round(least(
            coalesce(sc.outcome_15m_spot - sso.entry_spot, 1e15),
            coalesce(sc.outcome_30m_spot - sso.entry_spot, 1e15),
            coalesce(sc.outcome_60m_spot - sso.entry_spot, 1e15)
        )::numeric, 4)
    end,

    raw = coalesce(sso.raw, '{}'::jsonb) || jsonb_build_object(
        'source', 'meridian_outcome_v2_backfill_runner.sql',
        'spot_source_table', 'gamma_metrics',
        'horizon_row_ts', jsonb_build_object(
            '15m', sc.ts_15m,
            '30m', sc.ts_30m,
            '60m', sc.ts_60m,
            'eod', sc.ts_eod
        ),
        'note', 'V2 backfill applied from gamma_metrics'
    )
from shadow_computed sc
where sso.id = sc.id;