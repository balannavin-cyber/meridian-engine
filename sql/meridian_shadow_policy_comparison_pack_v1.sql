/* ============================================================
MERDIAN
Shadow Policy Comparison Pack V1

Purpose
-------
Compare shadow policy versions side by side.

Read-only analysis for:
- row counts
- average confidence uplift
- changed decision counts
- relationship-level behavior
- latest rows by policy

No live logic changes.
============================================================ */


/* ------------------------------------------------------------
PC1. High-level comparison by policy
------------------------------------------------------------ */
select
  shadow_policy_version,
  count(*) as row_count,
  round(avg(baseline_confidence_score)::numeric, 2) as avg_baseline_confidence,
  round(avg(shadow_confidence_score)::numeric, 2) as avg_shadow_confidence,
  round(avg(shadow_delta_confidence)::numeric, 2) as avg_shadow_delta,
  sum(case when shadow_decision_changed then 1 else 0 end) as changed_rows
from public.shadow_signal_validation_v1
group by shadow_policy_version
order by shadow_policy_version;


/* ------------------------------------------------------------
PC2. Comparison by policy and symbol
------------------------------------------------------------ */
select
  shadow_policy_version,
  symbol,
  count(*) as row_count,
  round(avg(baseline_confidence_score)::numeric, 2) as avg_baseline_confidence,
  round(avg(shadow_confidence_score)::numeric, 2) as avg_shadow_confidence,
  round(avg(shadow_delta_confidence)::numeric, 2) as avg_shadow_delta,
  sum(case when shadow_decision_changed then 1 else 0 end) as changed_rows
from public.shadow_signal_validation_v1
group by shadow_policy_version, symbol
order by shadow_policy_version, symbol;


/* ------------------------------------------------------------
PC3. Comparison by policy and breadth/WCB relationship
------------------------------------------------------------ */
select
  breadth_wcb_relationship,
  shadow_policy_version,
  count(*) as row_count,
  round(avg(baseline_confidence_score)::numeric, 2) as avg_baseline_confidence,
  round(avg(shadow_confidence_score)::numeric, 2) as avg_shadow_confidence,
  round(avg(shadow_delta_confidence)::numeric, 2) as avg_shadow_delta,
  sum(case when shadow_decision_changed then 1 else 0 end) as changed_rows
from public.shadow_signal_validation_v1
group by breadth_wcb_relationship, shadow_policy_version
order by breadth_wcb_relationship, shadow_policy_version;


/* ------------------------------------------------------------
PC4. Decision-change rate by policy
------------------------------------------------------------ */
select
  shadow_policy_version,
  count(*) as total_rows,
  sum(case when shadow_decision_changed then 1 else 0 end) as changed_rows,
  round(
    100.0 * sum(case when shadow_decision_changed then 1 else 0 end)::numeric
    / nullif(count(*), 0),
    2
  ) as pct_changed
from public.shadow_signal_validation_v1
group by shadow_policy_version
order by shadow_policy_version;


/* ------------------------------------------------------------
PC5. Confidence-direction distribution by policy
------------------------------------------------------------ */
select
  shadow_policy_version,
  shadow_confidence_direction,
  count(*) as row_count
from public.shadow_signal_validation_v1
group by shadow_policy_version, shadow_confidence_direction
order by shadow_policy_version, shadow_confidence_direction;


/* ------------------------------------------------------------
PC6. Latest rows by policy
------------------------------------------------------------ */
select
  id,
  created_at,
  symbol,
  shadow_policy_version,
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
  breadth_wcb_relationship
from public.shadow_signal_validation_v1
order by created_at desc
limit 30;


/* ------------------------------------------------------------
PC7. Most recent row per symbol per policy
------------------------------------------------------------ */
with ranked as (
  select
    v.*,
    row_number() over (
      partition by v.shadow_policy_version, v.symbol
      order by v.created_at desc, v.id desc
    ) as rn
  from public.shadow_signal_validation_v1 v
)
select
  id,
  created_at,
  symbol,
  shadow_policy_version,
  baseline_action,
  baseline_confidence_score,
  shadow_action,
  shadow_confidence_score,
  shadow_delta_confidence,
  shadow_decision_changed,
  breadth_wcb_relationship
from ranked
where rn = 1
order by shadow_policy_version, symbol;


/* ------------------------------------------------------------
PC8. Rows where any policy changed the decision
------------------------------------------------------------ */
select
  id,
  created_at,
  symbol,
  shadow_policy_version,
  baseline_action,
  baseline_trade_allowed,
  baseline_direction_bias,
  baseline_entry_quality,
  baseline_confidence_score,
  shadow_action,
  shadow_trade_allowed,
  shadow_direction_bias,
  shadow_entry_quality,
  shadow_confidence_score,
  shadow_delta_confidence,
  shadow_decision_changed,
  breadth_wcb_relationship,
  reasons,
  cautions
from public.shadow_signal_validation_v1
where shadow_decision_changed = true
order by created_at desc;


/* ------------------------------------------------------------
PC9. Policy comparison pivot
------------------------------------------------------------ */
select
  shadow_policy_version,
  count(*) as row_count,
  round(avg(case when breadth_wcb_relationship = 'CONFIRM_BEARISH' then shadow_delta_confidence end)::numeric, 2) as avg_delta_confirm_bearish,
  round(avg(case when breadth_wcb_relationship = 'CONFIRM_BULLISH' then shadow_delta_confidence end)::numeric, 2) as avg_delta_confirm_bullish,
  round(avg(case when breadth_wcb_relationship like 'DIVERGENT%' then shadow_delta_confidence end)::numeric, 2) as avg_delta_divergent,
  sum(case when breadth_wcb_relationship like 'DIVERGENT%' and shadow_decision_changed then 1 else 0 end) as changed_divergent_rows
from public.shadow_signal_validation_v1
group by shadow_policy_version
order by shadow_policy_version;


/* ------------------------------------------------------------
PC10. Raw reasons audit by policy
------------------------------------------------------------ */
select
  created_at,
  symbol,
  shadow_policy_version,
  breadth_wcb_relationship,
  reasons,
  cautions
from public.shadow_signal_validation_v1
order by created_at desc
limit 20;