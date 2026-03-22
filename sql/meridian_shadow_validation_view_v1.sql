/* ============================================================
MERDIAN
Shadow Validation View V1

Purpose
-------
Create a read-only view for comparing:
- baseline signal
- shadow signal

This view is for Phase 3 shadow monitoring only.
No live logic changes are introduced here.
============================================================ */

drop view if exists public.shadow_signal_validation_v1;

create view public.shadow_signal_validation_v1 as
select
    sss.id,
    sss.created_at,
    sss.ts,
    sss.market_state_ts,
    sss.symbol,

    sss.expiry_date,
    sss.expiry_type,
    sss.dte,
    sss.spot,

    sss.baseline_signal_id,
    sss.baseline_action,
    sss.baseline_trade_allowed,
    sss.baseline_entry_quality,
    sss.baseline_direction_bias,
    sss.baseline_confidence_score,

    sss.shadow_action,
    sss.shadow_trade_allowed,
    sss.shadow_entry_quality,
    sss.shadow_direction_bias,
    sss.shadow_confidence_score,

    sss.shadow_delta_confidence,
    sss.shadow_decision_changed,

    sss.gamma_regime,
    sss.breadth_regime,
    sss.breadth_score,
    sss.volatility_regime,

    sss.wcb_regime,
    sss.wcb_score,
    sss.wcb_alignment,
    sss.wcb_weight_coverage_pct,
    sss.breadth_wcb_relationship,

    case
        when sss.shadow_delta_confidence > 0 then 'UP'
        when sss.shadow_delta_confidence < 0 then 'DOWN'
        else 'FLAT'
    end as shadow_confidence_direction,

    case
        when sss.baseline_action = sss.shadow_action
         and sss.baseline_trade_allowed = sss.shadow_trade_allowed
         and sss.baseline_direction_bias = sss.shadow_direction_bias
        then 'UNCHANGED'
        else 'CHANGED'
    end as shadow_change_state,

    sss.shadow_policy_version,
    sss.reasons,
    sss.cautions,
    sss.raw

from public.shadow_signal_snapshots sss;