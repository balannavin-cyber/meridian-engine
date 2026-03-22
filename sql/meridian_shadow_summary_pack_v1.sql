/* ============================================================
MERDIAN
Shadow Summary Pack V1

Purpose
-------
High level audit of the shadow signal engine.

Provides evidence for:
• confidence changes
• decision flips
• WCB impact
• breadth/WCB interaction

Used during Phase-3 Shadow evaluation.
============================================================ */


/* ------------------------------------------------------------
SS1 — Total shadow rows
------------------------------------------------------------ */
select
    count(*) as total_shadow_rows
from public.shadow_signal_validation_v1;


/* ------------------------------------------------------------
SS2 — Baseline vs shadow decision counts
------------------------------------------------------------ */
select
    baseline_action,
    shadow_action,
    count(*) as row_count
from public.shadow_signal_validation_v1
group by baseline_action, shadow_action
order by row_count desc;


/* ------------------------------------------------------------
SS3 — Shadow decision change rate
------------------------------------------------------------ */
select
    count(*) as total_rows,
    sum(case when shadow_decision_changed then 1 else 0 end) as changed_rows,
    round(
        100.0 * sum(case when shadow_decision_changed then 1 else 0 end)
        / nullif(count(*),0),2
    ) as pct_changed
from public.shadow_signal_validation_v1;


/* ------------------------------------------------------------
SS4 — Average confidence comparison
------------------------------------------------------------ */
select
    round(avg(baseline_confidence_score)::numeric,2) as avg_baseline_confidence,
    round(avg(shadow_confidence_score)::numeric,2) as avg_shadow_confidence,
    round(avg(shadow_delta_confidence)::numeric,2) as avg_shadow_delta
from public.shadow_signal_validation_v1;


/* ------------------------------------------------------------
SS5 — Confidence uplift distribution
------------------------------------------------------------ */
select
    shadow_confidence_direction,
    count(*) as row_count
from public.shadow_signal_validation_v1
group by shadow_confidence_direction
order by row_count desc;


/* ------------------------------------------------------------
SS6 — Impact by breadth/WCB relationship
------------------------------------------------------------ */
select
    breadth_wcb_relationship,
    count(*) as row_count,
    round(avg(shadow_delta_confidence)::numeric,2) as avg_shadow_delta
from public.shadow_signal_validation_v1
group by breadth_wcb_relationship
order by avg_shadow_delta desc;


/* ------------------------------------------------------------
SS7 — Symbol level summary
------------------------------------------------------------ */
select
    symbol,
    count(*) as row_count,
    round(avg(baseline_confidence_score)::numeric,2) as avg_baseline_confidence,
    round(avg(shadow_confidence_score)::numeric,2) as avg_shadow_confidence,
    round(avg(shadow_delta_confidence)::numeric,2) as avg_shadow_delta
from public.shadow_signal_validation_v1
group by symbol
order by symbol;


/* ------------------------------------------------------------
SS8 — Most recent shadow rows
------------------------------------------------------------ */
select
    id,
    created_at,
    symbol,
    baseline_action,
    shadow_action,
    baseline_confidence_score,
    shadow_confidence_score,
    shadow_delta_confidence,
    shadow_decision_changed,
    breadth_regime,
    wcb_regime,
    breadth_wcb_relationship
from public.shadow_signal_validation_v1
order by created_at desc
limit 20;


/* ------------------------------------------------------------
SS9 — Rows where shadow decision differs
------------------------------------------------------------ */
select
    id,
    created_at,
    symbol,
    baseline_action,
    shadow_action,
    baseline_trade_allowed,
    shadow_trade_allowed,
    baseline_direction_bias,
    shadow_direction_bias,
    baseline_confidence_score,
    shadow_confidence_score,
    shadow_delta_confidence,
    breadth_wcb_relationship
from public.shadow_signal_validation_v1
where shadow_decision_changed = true
order by created_at desc;


/* ------------------------------------------------------------
SS10 — Reasons audit
------------------------------------------------------------ */
select
    symbol,
    breadth_wcb_relationship,
    reasons
from public.shadow_signal_validation_v1
order by created_at desc
limit 10;