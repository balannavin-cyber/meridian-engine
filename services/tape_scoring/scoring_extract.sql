-- scoring_extract.sql -- tape scoring inputs (docs/tape/scoring_plan.md section 1.4). HASHED with score.py.
-- Pure SELECTs: one per relation, fixed filters only (symbol, one IST trading day). No join, no aggregate, no window
-- function, no arithmetic, no clock or front-expiry filter (those live in score.py, where the guards can reach them).
-- Variables come from psql meta-commands that run_extract.sh prepends: :'d' (trading day), :'t0' / :'t1' (IST day bounds),
-- :'d0' / :'d1' (range, days_list only). This file is never executed by the scoring session; the operator runs it through
-- bin/roq.sh (merdian_ro) via run_extract.sh. CSV output comes from "\pset format csv".

-- @name days_list
SELECT trading_day, symbol FROM public.tape_daily_report WHERE trading_day >= :'d0' AND trading_day <= :'d1';

-- @name tape_strike_cycle
SELECT symbol, trading_day, expiry, strike, leg, ts_ist, buy_cum, sell_cum, uncl_cum, gap_cum, first_seen_ts_ist, run_id
FROM public.tape_strike_cycle
WHERE trading_day = :'d' AND symbol IN ('NIFTY', 'SENSEX');

-- @name tape_events
SELECT symbol, trading_day, expiry, strike, leg, kind, ts_ist, side, magnitude, run_id
FROM public.tape_events
WHERE trading_day = :'d' AND symbol IN ('NIFTY', 'SENSEX');

-- @name tape_chain_events
SELECT symbol, trading_day, expiry, kind, ts_ist, strike, merged_n, run_id
FROM public.tape_chain_events
WHERE trading_day = :'d' AND symbol IN ('NIFTY', 'SENSEX');

-- @name tape_chain_runs
SELECT symbol, trading_day, expiry, ts_ist, chain_run_id, leader_strike, call_wall, put_wall, net_sign, in_window, run_id
FROM public.tape_chain_runs
WHERE trading_day = :'d' AND symbol IN ('NIFTY', 'SENSEX');

-- @name tape_daily_report
SELECT symbol, trading_day, classified_share_late, report, g3, run_id
FROM public.tape_daily_report
WHERE trading_day = :'d' AND symbol IN ('NIFTY', 'SENSEX');

-- @name tape_minute
SELECT symbol, trading_day, minute_ist, run_id
FROM public.tape_minute
WHERE trading_day = :'d' AND symbol IN ('NIFTY', 'SENSEX');

-- @name gex_strike_snapshots
SELECT run_id, symbol, ts, expiry_date, strike, gamma_call, gamma_put, oi_call, oi_put, gex_cr
FROM public.gex_strike_snapshots
WHERE ts >= :'t0' AND ts < :'t1' AND symbol IN ('NIFTY', 'SENSEX');

-- @name gamma_metrics
SELECT run_id, symbol, ts, expiry_date, straddle_atm
FROM public.gamma_metrics
WHERE ts >= :'t0' AND ts < :'t1' AND symbol IN ('NIFTY', 'SENSEX');

-- @name hist_spot_bars_1m
SELECT instrument_id, trade_date, bar_ts, open, high, low, close
FROM public.hist_spot_bars_1m
WHERE bar_ts >= :'t0' AND bar_ts < :'t1' AND instrument_id IN ('9992f600-51b3-4009-b487-f878692a0bc5', '73a1390a-30c9-46d6-9d3f-5f03c3f5ad71');
