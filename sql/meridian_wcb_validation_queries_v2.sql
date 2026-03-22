/* ============================================================
MERDIAN
WCB Validation Queries V2

Purpose
-------
Validation-only query pack for:
- WCB telemetry
- breadth vs WCB relationship
- confidence comparisons
- monitoring latest rows

No live logic changes.
No confidence changes.
No trade gating.
============================================================ */


/* ------------------------------------------------------------
Q1. Latest WCB-enabled rows
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
Q2. Count rows by breadth vs WCB relationship
------------------------------------------------------------ */
select
  breadth_wcb_relationship,
  count(*) as row_count
from public.wcb_signal_validation_v2
group by breadth_wcb_relationship
order by row_count desc, breadth_wcb_relationship;


/* ------------------------------------------------------------
Q3. Average confidence by breadth vs WCB relationship
------------------------------------------------------------ */
select
  breadth_wcb_relationship,
  count(*) as row_count,
  round(avg(confidence_score)::numeric, 2) as avg_confidence
from public.wcb_signal_validation_v2
group by breadth_wcb_relationship
order by avg_confidence desc nulls last, breadth_wcb_relationship;


/* ------------------------------------------------------------
Q4. Rows where breadth and WCB confirm bearishness
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
order by created_at desc;


/* ------------------------------------------------------------
Q5. Rows where breadth and WCB confirm bullishness
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
order by created_at desc;


/* ------------------------------------------------------------
Q6. Rows where breadth and WCB diverge
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
Q7. WCB-enabled rows only: confidence by symbol
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
Q8. Directional rows only: how WCB relates to them
------------------------------------------------------------ */
select
  symbol,
  direction_bias,
  wcb_alignment,
  breadth_wcb_relationship,
  count(*) as row_count
from public.wcb_signal_validation_v2
where has_directional_action = true
group by symbol, direction_bias, wcb_alignment, breadth_wcb_relationship
order by symbol, direction_bias, wcb_alignment, breadth_wcb_relationship;