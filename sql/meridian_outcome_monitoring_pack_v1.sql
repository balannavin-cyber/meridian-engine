/* ============================================================
MERDIAN
Outcome Monitoring Pack V1

Purpose
-------
Read-only monitoring queries for:
1. baseline signal outcomes
2. shadow signal outcomes

No live logic changes.
============================================================ */


/* ------------------------------------------------------------
OM1. Baseline outcome row count
------------------------------------------------------------ */
select
  count(*) as baseline_outcome_rows
from public.signal_outcomes;


/* ------------------------------------------------------------
OM2. Shadow outcome row count by policy
------------------------------------------------------------ */
select
  shadow_policy_version,
  count(*) as shadow_outcome_rows
from public.shadow_signal_outcomes
group by shadow_policy_version
order by shadow_policy_version;


/* ------------------------------------------------------------
OM3. Baseline outcome labels
------------------------------------------------------------ */
select
  outcome_label_eod,
  count(*) as row_count
from public.signal_outcomes
group by outcome_label_eod
order by row_count desc, outcome_label_eod;


/* ------------------------------------------------------------
OM4. Shadow outcome labels by policy
------------------------------------------------------------ */
select
  shadow_policy_version,
  outcome_label_eod,
  count(*) as row_count
from public.shadow_signal_outcomes
group by shadow_policy_version, outcome_label_eod
order by shadow_policy_version, row_count desc, outcome_label_eod;


/* ------------------------------------------------------------
OM5. Baseline average EOD move
------------------------------------------------------------ */
select
  count(*) as row_count,
  round(avg(move_eod_points)::numeric, 4) as avg_move_eod_points,
  round(avg(move_eod_pct)::numeric, 6) as avg_move_eod_pct
from public.signal_outcomes;


/* ------------------------------------------------------------
OM6. Shadow average EOD move by policy
------------------------------------------------------------ */
select
  shadow_policy_version,
  count(*) as row_count,
  round(avg(move_eod_points)::numeric, 4) as avg_move_eod_points,
  round(avg(move_eod_pct)::numeric, 6) as avg_move_eod_pct
from public.shadow_signal_outcomes
group by shadow_policy_version
order by shadow_policy_version;


/* ------------------------------------------------------------
OM7. Shadow confidence uplift by policy
------------------------------------------------------------ */
select
  shadow_policy_version,
  count(*) as row_count,
  round(avg(baseline_confidence_score)::numeric, 2) as avg_baseline_confidence,
  round(avg(shadow_confidence_score)::numeric, 2) as avg_shadow_confidence,
  round(avg(shadow_delta_confidence)::numeric, 2) as avg_shadow_delta
from public.shadow_signal_outcomes
group by shadow_policy_version
order by shadow_policy_version;


/* ------------------------------------------------------------
OM8. Baseline vs shadow latest rows
------------------------------------------------------------ */
select
  'BASELINE' as stream,
  so.created_at,
  so.symbol,
  so.signal_id as row_id,
  so.action,
  so.trade_allowed,
  so.direction_bias,
  so.confidence_score,
  so.entry_spot,
  so.outcome_eod_spot,
  so.move_eod_points,
  so.move_eod_pct,
  so.outcome_label_eod,
  so.outcome_policy_version as policy_version
from public.signal_outcomes so

union all

select
  'SHADOW' as stream,
  sso.created_at,
  sso.symbol,
  sso.shadow_signal_id as row_id,
  sso.shadow_action as action,
  sso.shadow_trade_allowed as trade_allowed,
  sso.shadow_direction_bias as direction_bias,
  sso.shadow_confidence_score as confidence_score,
  sso.entry_spot,
  sso.outcome_eod_spot,
  sso.move_eod_points,
  sso.move_eod_pct,
  sso.outcome_label_eod,
  sso.shadow_policy_version as policy_version
from public.shadow_signal_outcomes sso

order by created_at desc
limit 20;


/* ------------------------------------------------------------
OM9. Shadow rows with decision changes
------------------------------------------------------------ */
select
  created_at,
  symbol,
  shadow_signal_id,
  shadow_policy_version,
  baseline_action,
  shadow_action,
  baseline_confidence_score,
  shadow_confidence_score,
  shadow_delta_confidence,
  shadow_decision_changed,
  breadth_wcb_relationship,
  outcome_eod_spot,
  move_eod_points,
  move_eod_pct,
  outcome_label_eod
from public.shadow_signal_outcomes
where shadow_decision_changed = true
order by created_at desc;


/* ------------------------------------------------------------
OM10. Most recent outcome row per symbol
------------------------------------------------------------ */
with baseline_ranked as (
  select
    so.*,
    row_number() over (
      partition by so.symbol
      order by so.created_at desc, so.id desc
    ) as rn
  from public.signal_outcomes so
),
shadow_ranked as (
  select
    sso.*,
    row_number() over (
      partition by sso.symbol, sso.shadow_policy_version
      order by sso.created_at desc, sso.id desc
    ) as rn
  from public.shadow_signal_outcomes sso
)
select
  'BASELINE' as stream,
  br.symbol,
  br.created_at,
  br.signal_id as row_id,
  br.action,
  br.confidence_score,
  br.move_eod_points,
  br.move_eod_pct,
  br.outcome_label_eod,
  br.outcome_policy_version as policy_version
from baseline_ranked br
where br.rn = 1

union all

select
  'SHADOW' as stream,
  sr.symbol,
  sr.created_at,
  sr.shadow_signal_id as row_id,
  sr.shadow_action as action,
  sr.shadow_confidence_score as confidence_score,
  sr.move_eod_points,
  sr.move_eod_pct,
  sr.outcome_label_eod,
  sr.shadow_policy_version as policy_version
from shadow_ranked sr
where sr.rn = 1

order by stream, symbol, policy_version;