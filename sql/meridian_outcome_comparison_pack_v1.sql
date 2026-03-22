/* ============================================================
MERDIAN
Outcome Comparison Pack V1

Purpose
-------
Read-only comparison between:
1. baseline outcomes
2. shadow outcomes

Compares:
- row counts
- confidence
- outcome labels
- EOD moves
- latest rows by stream

No live logic changes.
============================================================ */


/* ------------------------------------------------------------
OC1. Row counts by stream
------------------------------------------------------------ */
select
  'BASELINE' as stream,
  count(*) as row_count
from public.signal_outcomes

union all

select
  'SHADOW' as stream,
  count(*) as row_count
from public.shadow_signal_outcomes

order by stream;


/* ------------------------------------------------------------
OC2. Average confidence by stream
------------------------------------------------------------ */
select
  'BASELINE' as stream,
  count(*) as row_count,
  round(avg(confidence_score)::numeric, 2) as avg_confidence
from public.signal_outcomes

union all

select
  'SHADOW' as stream,
  count(*) as row_count,
  round(avg(shadow_confidence_score)::numeric, 2) as avg_confidence
from public.shadow_signal_outcomes

order by stream;


/* ------------------------------------------------------------
OC3. Outcome labels by stream
------------------------------------------------------------ */
select
  'BASELINE' as stream,
  outcome_label_eod,
  count(*) as row_count
from public.signal_outcomes
group by outcome_label_eod

union all

select
  'SHADOW' as stream,
  outcome_label_eod,
  count(*) as row_count
from public.shadow_signal_outcomes
group by outcome_label_eod

order by stream, row_count desc, outcome_label_eod;


/* ------------------------------------------------------------
OC4. Average EOD move by stream
------------------------------------------------------------ */
select
  'BASELINE' as stream,
  count(*) as row_count,
  round(avg(move_eod_points)::numeric, 4) as avg_move_eod_points,
  round(avg(move_eod_pct)::numeric, 6) as avg_move_eod_pct
from public.signal_outcomes

union all

select
  'SHADOW' as stream,
  count(*) as row_count,
  round(avg(move_eod_points)::numeric, 4) as avg_move_eod_points,
  round(avg(move_eod_pct)::numeric, 6) as avg_move_eod_pct
from public.shadow_signal_outcomes

order by stream;


/* ------------------------------------------------------------
OC5. Symbol-level comparison by stream
------------------------------------------------------------ */
select
  'BASELINE' as stream,
  symbol,
  count(*) as row_count,
  round(avg(confidence_score)::numeric, 2) as avg_confidence,
  round(avg(move_eod_points)::numeric, 4) as avg_move_eod_points,
  round(avg(move_eod_pct)::numeric, 6) as avg_move_eod_pct
from public.signal_outcomes
group by symbol

union all

select
  'SHADOW' as stream,
  symbol,
  count(*) as row_count,
  round(avg(shadow_confidence_score)::numeric, 2) as avg_confidence,
  round(avg(move_eod_points)::numeric, 4) as avg_move_eod_points,
  round(avg(move_eod_pct)::numeric, 6) as avg_move_eod_pct
from public.shadow_signal_outcomes
group by symbol

order by stream, symbol;


/* ------------------------------------------------------------
OC6. Shadow policy breakdown inside shadow stream
------------------------------------------------------------ */
select
  shadow_policy_version,
  count(*) as row_count,
  round(avg(baseline_confidence_score)::numeric, 2) as avg_baseline_confidence,
  round(avg(shadow_confidence_score)::numeric, 2) as avg_shadow_confidence,
  round(avg(shadow_delta_confidence)::numeric, 2) as avg_shadow_delta,
  round(avg(move_eod_points)::numeric, 4) as avg_move_eod_points,
  round(avg(move_eod_pct)::numeric, 6) as avg_move_eod_pct
from public.shadow_signal_outcomes
group by shadow_policy_version
order by shadow_policy_version;


/* ------------------------------------------------------------
OC7. Latest rows by stream
------------------------------------------------------------ */
select
  'BASELINE' as stream,
  created_at,
  symbol,
  signal_id as row_id,
  action,
  trade_allowed,
  direction_bias,
  confidence_score,
  entry_spot,
  outcome_eod_spot,
  move_eod_points,
  move_eod_pct,
  outcome_label_eod,
  outcome_policy_version as policy_version
from public.signal_outcomes

union all

select
  'SHADOW' as stream,
  created_at,
  symbol,
  shadow_signal_id as row_id,
  shadow_action as action,
  shadow_trade_allowed as trade_allowed,
  shadow_direction_bias as direction_bias,
  shadow_confidence_score as confidence_score,
  entry_spot,
  outcome_eod_spot,
  move_eod_points,
  move_eod_pct,
  outcome_label_eod,
  shadow_policy_version as policy_version
from public.shadow_signal_outcomes

order by created_at desc
limit 20;


/* ------------------------------------------------------------
OC8. Most recent row per symbol by stream
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


/* ------------------------------------------------------------
OC9. Baseline vs shadow joined by symbol and latest row
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
      partition by sso.symbol
      order by sso.created_at desc, sso.id desc
    ) as rn
  from public.shadow_signal_outcomes sso
)
select
  br.symbol,
  br.created_at as baseline_created_at,
  sr.created_at as shadow_created_at,
  br.signal_id as baseline_signal_id,
  sr.shadow_signal_id as shadow_signal_id,
  br.action as baseline_action,
  sr.shadow_action,
  br.confidence_score as baseline_confidence,
  sr.shadow_confidence_score,
  sr.shadow_delta_confidence,
  br.move_eod_points as baseline_move_eod_points,
  sr.move_eod_points as shadow_move_eod_points,
  br.move_eod_pct as baseline_move_eod_pct,
  sr.move_eod_pct as shadow_move_eod_pct,
  br.outcome_label_eod as baseline_outcome_label,
  sr.outcome_label_eod as shadow_outcome_label,
  sr.shadow_policy_version
from baseline_ranked br
join shadow_ranked sr
  on br.symbol = sr.symbol
where br.rn = 1
  and sr.rn = 1
order by br.symbol;


/* ------------------------------------------------------------
OC10. Rows where shadow decision changed and outcome exists
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
  move_eod_points,
  move_eod_pct,
  outcome_label_eod
from public.shadow_signal_outcomes
where shadow_decision_changed = true
order by created_at desc;