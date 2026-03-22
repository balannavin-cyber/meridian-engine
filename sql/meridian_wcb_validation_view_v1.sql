/* ============================================================
MERDIAN
WCB Validation View V1

Purpose
-------
Create a clean validation view combining:
- signal snapshot
- observed WCB fields
- key signal metadata

This is for analysis only.
No live logic changes are introduced here.
============================================================ */

drop view if exists public.wcb_signal_validation_v1;

create view public.wcb_signal_validation_v1 as
select
    ss.id,
    ss.created_at,
    ss.ts,
    ss.market_state_ts,
    ss.symbol,
    ss.expiry_date,
    ss.expiry_type,
    ss.dte,

    ss.action,
    ss.trade_allowed,
    ss.entry_quality,
    ss.direction_bias,
    ss.confidence_score,

    ss.gamma_regime,
    ss.breadth_regime,
    ss.breadth_score,
    ss.volatility_regime,

    ss.india_vix,
    ss.vix_change,
    ss.vix_regime,

    ss.net_gex,
    ss.gamma_concentration,
    ss.flip_level,
    ss.flip_distance,
    ss.straddle_atm,
    ss.straddle_slope,

    ss.wcb_regime,
    ss.wcb_score,
    ss.wcb_alignment,
    ss.wcb_weight_coverage_pct,

    case
        when ss.wcb_regime is null then false
        else true
    end as has_wcb,

    case
        when ss.wcb_weight_coverage_pct is null then 'UNKNOWN'
        when ss.wcb_weight_coverage_pct >= 95 then 'GOOD'
        when ss.wcb_weight_coverage_pct >= 85 then 'PARTIAL'
        else 'WEAK'
    end as wcb_coverage_bucket,

    case
        when ss.direction_bias in ('BULLISH', 'BEARISH')
             and ss.wcb_alignment = 'ALIGNED'
        then true
        else false
    end as wcb_confirms_direction,

    case
        when ss.direction_bias in ('BULLISH', 'BEARISH')
             and ss.wcb_alignment = 'DIVERGENT'
        then true
        else false
    end as wcb_diverges_from_direction,

    ss.signal_source,
    ss.breadth_source_table,
    ss.source_run_id,
    ss.reasons,
    ss.cautions,
    ss.raw

from public.signal_snapshots ss;