/* ============================================================
MERDIAN
WCB Validation Summary Pack V1

Purpose
-------
Create summary / audit queries for the WCB validation phase.

This pack is read-only and intended for:
- validation
- audit
- evidence gathering
- periodic review

No live logic changes.
No confidence changes.
No trade gating.
============================================================ */


/* ------------------------------------------------------------
S1. High-level WCB adoption summary
------------------------------------------------------------ */
select
  count(*) as total_signal_rows,
  sum(case when has_wcb then 1 else 0 end) as wcb_enabled_rows,
  sum(case when not has_wcb then 1 else 0 end) as pre_wcb_rows,
  round(
    100.0 * sum(case when has_wcb then 1 else 0 end)::numeric / nullif(count(*), 0),
    2
  ) as pct_wcb_enabled
from public.wcb_signal_validation_v2;


/* ------------------------------------------------------------
S2. WCB relationship summary
------------------------------------------------------------ */
select
  breadth_wcb_relationship,
  count(*) as row_count,
  round(100.0 * count(*)::numeric / nullif(sum(count(*)) over (), 0), 2) as pct_of_total
from public.wcb_signal_validation_v2
group by breadth_wcb_relationship
order by row_count desc, breadth_wcb_relationship;


/* ------------------------------------------------------------
S3. WCB alignment summary
------------------------------------------------------------ */
select
  coalesce(wcb_alignment, 'NULL') as wcb_alignment,
  count(*) as row_count,
  round(100.0 * count(*)::numeric / nullif(sum(count(*)) over (), 0), 2) as pct_of_total
from public.wcb_signal_validation_v2
group by coalesce(wcb_alignment, 'NULL')
order by row_count desc, wcb_alignment;


/* ------------------------------------------------------------
S4. Coverage-quality summary
------------------------------------------------------------ */
select
  wcb_coverage_bucket,
  count(*) as row_count,
  round(100.0 * count(*)::numeric / nullif(sum(count(*)) over (), 0), 2) as pct_of_total
from public.wcb_signal_validation_v2
group by wcb_coverage_bucket
order by row_count desc, wcb_coverage_bucket;


/* ------------------------------------------------------------
S5. Confidence summary by breadth/WCB relationship
------------------------------------------------------------ */
select
  breadth_wcb_relationship,
  count(*) as row_count,
  round(avg(confidence_score)::numeric, 2) as avg_confidence,
  round(min(confidence_score)::numeric, 2) as min_confidence,
  round(max(confidence_score)::numeric, 2) as max_confidence
from public.wcb_signal_validation_v2
group by breadth_wcb_relationship
order by avg_confidence desc nulls last, breadth_wcb_relationship;


/* ------------------------------------------------------------
S6. WCB-enabled summary by symbol
------------------------------------------------------------ */
select
  symbol,
  count(*) as row_count,
  round(avg(confidence_score)::numeric, 2) as avg_confidence,
  round(avg(wcb_score)::numeric, 2) as avg_wcb_score,
  round(avg(wcb_weight_coverage_pct)::numeric, 2) as avg_wcb_coverage_pct
from public.wcb_signal_validation_v2
where has_wcb = true
group by symbol
order by symbol;


/* ------------------------------------------------------------
S7. Directional-action summary for WCB-enabled rows
------------------------------------------------------------ */
select
  symbol,
  action,
  direction_bias,
  count(*) as row_count
from public.wcb_signal_validation_v2
where has_wcb = true
group by symbol, action, direction_bias
order by symbol, action, direction_bias;


/* ------------------------------------------------------------
S8. Confirm-bearish audit rows
------------------------------------------------------------ */
select
  id,
  created_at,
  ts,
  symbol,
  spot,
  action,
  trade_allowed,
  direction_bias,
  confidence_score,
  breadth_regime,
  wcb_regime,
  wcb_score,
  wcb_alignment,
  wcb_weight_coverage_pct,
  breadth_wcb_relationship
from public.wcb_signal_validation_v2
where breadth_wcb_relationship = 'CONFIRM_BEARISH'
order by created_at desc;


/* ------------------------------------------------------------
S9. Confirm-bullish audit rows
------------------------------------------------------------ */
select
  id,
  created_at,
  ts,
  symbol,
  spot,
  action,
  trade_allowed,
  direction_bias,
  confidence_score,
  breadth_regime,
  wcb_regime,
  wcb_score,
  wcb_alignment,
  wcb_weight_coverage_pct,
  breadth_wcb_relationship
from public.wcb_signal_validation_v2
where breadth_wcb_relationship = 'CONFIRM_BULLISH'
order by created_at desc;


/* ------------------------------------------------------------
S10. Divergence audit rows
------------------------------------------------------------ */
select
  id,
  created_at,
  ts,
  symbol,
  spot,
  action,
  trade_allowed,
  direction_bias,
  confidence_score,
  breadth_regime,
  wcb_regime,
  wcb_score,
  wcb_alignment,
  wcb_weight_coverage_pct,
  breadth_wcb_relationship
from public.wcb_signal_validation_v2
where breadth_wcb_relationship in (
  'DIVERGENT_BREADTH_BULL_WCB_BEAR',
  'DIVERGENT_BREADTH_BEAR_WCB_BULL'
)
order by created_at desc;


/* ------------------------------------------------------------
S11. Most recent WCB-enabled row per symbol
------------------------------------------------------------ */
with ranked as (
  select
    v.*,
    row_number() over (
      partition by v.symbol
      order by v.created_at desc, v.id desc
    ) as rn
  from public.wcb_signal_validation_v2 v
  where v.has_wcb = true
)
select
  id,
  created_at,
  ts,
  symbol,
  spot,
  action,
  trade_allowed,
  direction_bias,
  confidence_score,
  breadth_regime,
  wcb_regime,
  wcb_score,
  wcb_alignment,
  wcb_weight_coverage_pct,
  breadth_wcb_relationship
from ranked
where rn = 1
order by symbol;


/* ------------------------------------------------------------
S12. Latest WCB-enabled rows with reasons and cautions
------------------------------------------------------------ */
select
  id,
  created_at,
  ts,
  symbol,
  action,
  trade_allowed,
  direction_bias,
  confidence_score,
  breadth_regime,
  wcb_regime,
  wcb_alignment,
  reasons,
  cautions
from public.wcb_signal_validation_v2
where has_wcb = true
order by created_at desc
limit 20;