-- S90 MV-9 — why are WCB values frozen since 01 Oct 15:40 IST? Read-only, after the close.
-- Writer: build_wcb_snapshot_local.py. pct_change = equity_intraday_last.last_price
--         / breadth_indicators_daily.prev_close (newest trade_date per ticker), :251-280.
-- Hypothesis H1 (from code, NOT yet measured): refresh_equity_intraday_last.py
--   (cron 35 3 * * 1-5 = 09:05 IST, once a day) writes last_price = Kite ohlc().close,
--   i.e. the PRIOR session's close (:125-140). Nothing refreshes it intraday, so WCB's
--   "advances" is the prior session's day change, constant all session.
-- Run: bin/roq.sh scratch/s90/p5_wcb_inputs_s90.sql > scratch/s90/p5_wcb_inputs_s90.out 2>&1
\pset pager off
\pset null '(null)'
SELECT current_user AS role_now, now() AS probed_at;

-- 1. equity_intraday_last: how fresh, how many, written when (IST).
SELECT count(*) AS n_rows, count(DISTINCT ts) AS n_distinct_ts,
       min(ts AT TIME ZONE 'Asia/Kolkata') AS oldest_ist,
       max(ts AT TIME ZONE 'Asia/Kolkata') AS newest_ist
FROM public.equity_intraday_last;
SELECT (ts AT TIME ZONE 'Asia/Kolkata')::date AS d_ist,
       to_char(ts AT TIME ZONE 'Asia/Kolkata','HH24:MI') AS hhmm_ist, count(*) AS n
FROM public.equity_intraday_last GROUP BY 1,2 ORDER BY 1 DESC, 2 DESC LIMIT 10;

-- 2. Who wrote it, per script_execution_log, last 8 days.
SELECT script_name, trade_date, to_char(started_at AT TIME ZONE 'Asia/Kolkata','MM-DD HH24:MI') AS start_ist,
       exit_code, exit_reason, contract_met, actual_writes, left(coalesce(error_message,''),120) AS err
FROM public.script_execution_log
WHERE script_name IN ('refresh_equity_intraday_last.py','ingest_breadth_intraday_local.py')
  AND started_at >= '2026-09-27 18:30+00'
ORDER BY started_at DESC LIMIT 20;

-- 3. breadth_indicators_daily frontier (prev_close + DMA source).
SELECT trade_date, count(*) AS n_tickers
FROM public.breadth_indicators_daily
WHERE trade_date >= '2026-09-24'
GROUP BY 1 ORDER BY 1 DESC;

-- 4. One heavy constituent end to end: does last_price equal a settled close?
--    (to_jsonb so an unknown column name cannot fail the probe)
SELECT 'equity_intraday_last' AS src, to_jsonb(e) AS row
FROM public.equity_intraday_last e WHERE e.ticker LIKE '%:RELIANCE' OR e.ticker LIKE '%:HDFCBANK' OR e.ticker IN ('RELIANCE','HDFCBANK')
UNION ALL
SELECT 'breadth_indicators_daily', to_jsonb(b)
FROM public.breadth_indicators_daily b
WHERE b.trade_date >= '2026-09-29'
  AND (b.ticker LIKE '%RELIANCE' OR b.ticker LIKE '%HDFCBANK');

-- 5. The change point: WCB rows around 01 Oct 15:25-15:50 IST and the first rows of 05 Oct.
SELECT index_symbol, to_char(ts AT TIME ZONE 'Asia/Kolkata','MM-DD HH24:MI') AS ts_ist,
       wcb_score, weighted_advances_pct AS adv, active_weight_pct AS coverage
FROM public.weighted_constituent_breadth_snapshots
WHERE (ts >= '2026-10-01 09:55+00' AND ts < '2026-10-01 10:20+00')
   OR (ts >= '2026-10-05 03:40+00' AND ts < '2026-10-05 04:00+00')
ORDER BY index_symbol, ts;

-- 6. Active weights per index (coverage denominator).
SELECT index_symbol, count(*) AS n_active, round(sum(weight_pct)::numeric,2) AS sum_weight
FROM public.index_constituent_weights WHERE is_active GROUP BY 1 ORDER BY 1;

-- 7. Role timeouts (carried from the morning list).
SELECT rolname, rolconfig FROM pg_roles WHERE rolname IN ('anon','authenticated','merdian_ro');
