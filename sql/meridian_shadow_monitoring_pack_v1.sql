/* ============================================================
MERDIAN
Shadow Monitoring Pack V1

Purpose
-------
Monitoring queries for the shadow signal layer.

This pack is read-only and intended for:
- shadow comparison
- monitoring
- validation
- evidence gathering

No live logic changes.
============================================================ */


/* ------------------------------------------------------------
SM1. Latest shadow rows
------------------------------------------------------------ */
select
  id,
  created_at,
  ts,
  symbol,
  spot,
  baseline_action,
  baseline_trade_allowed,
  baseline_direction_bias,
  baseline_confidence_score,
  shadow_action,
  shadow_trade_allowed,
  shadow_direction_bias,
  shadow_confidence_score,
  shadow_delta_confidence,
  shadow_decision_changed,
  breadth_regime,
  wcb_regime,
  wcb_alignment,
  breadth_wcb_relationship,
  shadow_policy_version
from public.shadow_signal_validation_v1
order by created_at desc
limit 20;


/* ------------------------------------------------------------
SM2. Count rows by shadow change state
------------------------------------------------------------ */
select
  shadow_change_state,
  count(*) as row_count
from public.shadow_signal_validation_v1
group by shadow_change_state
order by row_count desc, shadow_change_state;


/* ------------------------------------------------------------
SM3. Count rows by shadow decision changed flag
------------------------------------------------------------ */
select
  shadow_decision_changed,
  count(*) as row_count
from public.shadow_signal_validation_v1
group by shadow_decision_changed
order by shadow_decision_changed desc;


/* ------------------------------------------------------------
SM4. Average baseline vs shadow confidence by symbol
------------------------------------------------------------ */
select
  symbol,
  count(*) as row_count,
  round(avg(baseline_confidence_score)::numeric, 2) as avg_baseline_confidence,
  round(avg(shadow_confidence_score)::numeric, 2) as avg_shadow_confidence,
  round(avg(shadow_delta_confidence)::numeric, 2) as avg_shadow_delta_confidence
from public.shadow_signal_validation_v1
group by symbol
order by symbol;


/* ------------------------------------------------------------
SM5. Average baseline vs shadow confidence by breadth/WCB relationship
------------------------------------------------------------ */
select
  breadth_wcb_relationship,
  count(*) as row_count,
  round(avg(baseline_confidence_score)::numeric, 2) as avg_baseline_confidence,
  round(avg(shadow_confidence_score)::numeric, 2) as avg_shadow_confidence,
  round(avg(shadow_delta_confidence)::numeric, 2) as avg_shadow_delta_confidence
from public.shadow_signal_validation_v1
group by breadth_wcb_relationship
order by avg_shadow_delta_confidence desc nulls last, breadth_wcb_relationship;


/* ------------------------------------------------------------
SM6. Rows where shadow decision changed
------------------------------------------------------------ */
select
  id,
  created_at,
  ts,
  symbol,
  spot,
  baseline_action,
  baseline_trade_allowed,
  baseline_direction_bias,
  baseline_confidence_score,
  shadow_action,
  shadow_trade_allowed,
  shadow_direction_bias,
  shadow_confidence_score,
  shadow_delta_confidence,
  shadow_decision_changed,
  breadth_regime,
  wcb_regime,
  wcb_alignment,
  breadth_wcb_relationship,
  reasons,
  cautions
from public.shadow_signal_validation_v1
where shadow_decision_changed = true
order by created_at desc
limit 20;


/* ------------------------------------------------------------
SM7. Rows where shadow confidence increased
------------------------------------------------------------ */
select
  id,
  created_at,
  ts,
  symbol,
  spot,
  baseline_confidence_score,
  shadow_confidence_score,
  shadow_delta_confidence,
  baseline_action,
  shadow_action,
  breadth_regime,
  wcb_regime,
  breadth_wcb_relationship
from public.shadow_signal_validation_v1
where shadow_delta_confidence > 0
order by created_at desc
limit 20;


/* ------------------------------------------------------------
SM8. Most recent shadow row per symbol
------------------------------------------------------------ */
with ranked as (
  select
    v.*,
    row_number() over (
      partition by v.symbol
      order by v.created_at desc, v.id desc
    ) as rn
  from public.shadow_signal_validation_v1 v
)
select
  id,
  created_at,
  ts,
  symbol,
  spot,
  baseline_action,
  baseline_trade_allowed,
  baseline_direction_bias,
  baseline_confidence_score,
  shadow_action,
  shadow_trade_allowed,
  shadow_direction_bias,
  shadow_confidence_score,
  shadow_delta_confidence,
  shadow_decision_changed,
  breadth_regime,
  wcb_regime,
  wcb_alignment,
  breadth_wcb_relationship,
  shadow_policy_version
from ranked
where rn = 1
order by symbol;


/* ------------------------------------------------------------
SM9. Latest shadow rows with reasons and cautions
------------------------------------------------------------ */
select
  id,
  created_at,
  ts,
  symbol,
  baseline_action,
  baseline_confidence_score,
  shadow_action,
  shadow_confidence_score,
  shadow_delta_confidence,
  shadow_decision_changed,
  breadth_wcb_relationship,
  reasons,
  cautions
from public.shadow_signal_validation_v1
order by created_at desc
limit 20;