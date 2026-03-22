/* ============================================================
MERDIAN
WCB Validation Queries V1

Purpose
-------
Exploratory validation queries for WCB measurement phase.

These queries do NOT change any live logic.
They are for analysis only.
============================================================ */


/* ------------------------------------------------------------
Q1. Latest WCB-enabled signals
------------------------------------------------------------ */
select
  id,
  created_at,
  symbol,
  action,
  trade_allowed,
  direction_bias,
  confidence_score,
  wcb_regime,
  wcb_score,
  wcb_alignment,
  wcb_weight_coverage_pct,
  has_wcb,
  wcb_coverage_bucket
from public.wcb_signal_validation_v1
order by created_at desc
limit 20;


/* ------------------------------------------------------------
Q2. Count rows with and without WCB
------------------------------------------------------------ */
select
  has_wcb,
  count(*) as row_count
from public.wcb_signal_validation_v1
group by has_wcb
order by has_wcb desc;


/* ------------------------------------------------------------
Q3. WCB alignment distribution
------------------------------------------------------------ */
select
  coalesce(wcb_alignment, 'NULL') as wcb_alignment,
  count(*) as row_count
from public.wcb_signal_validation_v1
group by coalesce(wcb_alignment, 'NULL')
order by row_count desc, wcb_alignment;


/* ------------------------------------------------------------
Q4. Coverage bucket distribution
------------------------------------------------------------ */
select
  wcb_coverage_bucket,
  count(*) as row_count
from public.wcb_signal_validation_v1
group by wcb_coverage_bucket
order by row_count desc, wcb_coverage_bucket;


/* ------------------------------------------------------------
Q5. Average confidence by WCB alignment
------------------------------------------------------------ */
select
  coalesce(wcb_alignment, 'NULL') as wcb_alignment,
  count(*) as row_count,
  round(avg(confidence_score)::numeric, 2) as avg_confidence
from public.wcb_signal_validation_v1
group by coalesce(wcb_alignment, 'NULL')
order by avg_confidence desc nulls last;


/* ------------------------------------------------------------
Q6. Average confidence by symbol and WCB alignment
------------------------------------------------------------ */
select
  symbol,
  coalesce(wcb_alignment, 'NULL') as wcb_alignment,
  count(*) as row_count,
  round(avg(confidence_score)::numeric, 2) as avg_confidence
from public.wcb_signal_validation_v1
group by symbol, coalesce(wcb_alignment, 'NULL')
order by symbol, avg_confidence desc nulls last;


/* ------------------------------------------------------------
Q7. WCB regime distribution
------------------------------------------------------------ */
select
  coalesce(wcb_regime, 'NULL') as wcb_regime,
  count(*) as row_count
from public.wcb_signal_validation_v1
group by coalesce(wcb_regime, 'NULL')
order by row_count desc, wcb_regime;


/* ------------------------------------------------------------
Q8. Rows where direction is non-neutral and WCB confirms
------------------------------------------------------------ */
select
  id,
  created_at,
  symbol,
  action,
  trade_allowed,
  direction_bias,
  confidence_score,
  wcb_regime,
  wcb_alignment,
  wcb_weight_coverage_pct
from public.wcb_signal_validation_v1
where direction_bias in ('BULLISH', 'BEARISH')
  and wcb_confirms_direction = true
order by created_at desc;


/* ------------------------------------------------------------
Q9. Rows where direction is non-neutral and WCB diverges
------------------------------------------------------------ */
select
  id,
  created_at,
  symbol,
  action,
  trade_allowed,
  direction_bias,
  confidence_score,
  wcb_regime,
  wcb_alignment,
  wcb_weight_coverage_pct
from public.wcb_signal_validation_v1
where direction_bias in ('BULLISH', 'BEARISH')
  and wcb_diverges_from_direction = true
order by created_at desc;


/* ------------------------------------------------------------
Q10. Latest rows with reasons and cautions
------------------------------------------------------------ */
select
  id,
  created_at,
  symbol,
  action,
  trade_allowed,
  direction_bias,
  confidence_score,
  wcb_regime,
  wcb_alignment,
  reasons,
  cautions
from public.wcb_signal_validation_v1
order by created_at desc
limit 10;