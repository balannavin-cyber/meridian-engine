/* ============================================================
MERDIAN
WCB Monitoring Pack V1

Purpose
-------
Operational monitoring queries for the WCB validation phase.

These queries are read-only and intended for:
- validation
- monitoring
- research
- tracking new WCB-enabled rows over time

This pack does NOT change live signal logic.
No confidence changes.
No trade gating.
No action changes.
============================================================ */


/* ------------------------------------------------------------
M1. Latest 20 rows from WCB validation view V2
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
  has_wcb,
  wcb_coverage_bucket,
  breadth_wcb_relationship
from public.wcb_signal_validation_v2
order by created_at desc
limit 20;


/* ------------------------------------------------------------
M2. Latest WCB-enabled rows only
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
where has_wcb = true
order by created_at desc
limit 20;


/* ------------------------------------------------------------
M3. Count rows by has_wcb
------------------------------------------------------------ */
select
  has_wcb,
  count(*) as row_count
from public.wcb_signal_validation_v2
group by has_wcb
order by has_wcb desc;


/* ------------------------------------------------------------
M4. Count rows by WCB coverage bucket
------------------------------------------------------------ */
select
  wcb_coverage_bucket,
  count(*) as row_count
from public.wcb_signal_validation_v2
group by wcb_coverage_bucket
order by row_count desc, wcb_coverage_bucket;


/* ------------------------------------------------------------
M5. Count rows by breadth vs WCB relationship
------------------------------------------------------------ */
select
  breadth_wcb_relationship,
  count(*) as row_count
from public.wcb_signal_validation_v2
group by breadth_wcb_relationship
order by row_count desc, breadth_wcb_relationship;


/* ------------------------------------------------------------
M6. Count rows by WCB alignment
------------------------------------------------------------ */
select
  coalesce(wcb_alignment, 'NULL') as wcb_alignment,
  count(*) as row_count
from public.wcb_signal_validation_v2
group by coalesce(wcb_alignment, 'NULL')
order by row_count desc, wcb_alignment;


/* ------------------------------------------------------------
M7. Average confidence by breadth vs WCB relationship
------------------------------------------------------------ */
select
  breadth_wcb_relationship,
  count(*) as row_count,
  round(avg(confidence_score)::numeric, 2) as avg_confidence
from public.wcb_signal_validation_v2
group by breadth_wcb_relationship
order by avg_confidence desc nulls last, breadth_wcb_relationship;


/* ------------------------------------------------------------
M8. Average confidence by WCB alignment
------------------------------------------------------------ */
select
  coalesce(wcb_alignment, 'NULL') as wcb_alignment,
  count(*) as row_count,
  round(avg(confidence_score)::numeric, 2) as avg_confidence
from public.wcb_signal_validation_v2
group by coalesce(wcb_alignment, 'NULL')
order by avg_confidence desc nulls last, wcb_alignment;


/* ------------------------------------------------------------
M9. Latest confirm-bearish rows
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
  wcb_weight_coverage_pct
from public.wcb_signal_validation_v2
where breadth_wcb_relationship = 'CONFIRM_BEARISH'
order by created_at desc
limit 20;


/* ------------------------------------------------------------
M10. Latest confirm-bullish rows
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
  wcb_weight_coverage_pct
from public.wcb_signal_validation_v2
where breadth_wcb_relationship = 'CONFIRM_BULLISH'
order by created_at desc
limit 20;


/* ------------------------------------------------------------
M11. Latest divergence rows
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
order by created_at desc
limit 20;


/* ------------------------------------------------------------
M12. Latest directional rows with WCB enabled
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
where has_wcb = true
  and action in ('BUY_CE', 'BUY_PE')
order by created_at desc
limit 20;


/* ------------------------------------------------------------
M13. WCB-enabled rows by symbol
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
M14. Most recent row per symbol
------------------------------------------------------------ */
with ranked as (
  select
    v.*,
    row_number() over (
      partition by v.symbol
      order by v.created_at desc, v.id desc
    ) as rn
  from public.wcb_signal_validation_v2 v
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
M15. Latest WCB-enabled rows with reasons and cautions
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