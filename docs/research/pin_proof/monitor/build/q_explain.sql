-- Pin monitor build: plain EXPLAIN gate for every query template the daily
-- runner uses. EXPLAIN only -- no rows of any trading day are read.
-- EXPLAIN date literal: 2026-11-23 (condition 3).
-- GATE: no Seq Scan on gex_strike_snapshots, option_chain_snapshots or
--       hist_spot_bars_1m in any plan below.

\echo == T0 instrument resolution (NIFTY) ==
EXPLAIN
SELECT id, symbol, strike_step, timezone
  FROM public.instruments
 WHERE symbol = 'NIFTY';

\echo == T1 strike rows, one symbol-day (NIFTY) ==
EXPLAIN
SELECT run_id, ts, expiry_date, dte, strike, spot,
       oi_call, oi_put, gamma_call, gamma_put, gex_cr
  FROM public.gex_strike_snapshots
 WHERE symbol = 'NIFTY'
   AND ts >= timestamptz '2026-11-23 00:00:00+05:30'
   AND ts <  timestamptz '2026-11-24 00:00:00+05:30'
 ORDER BY ts, expiry_date, strike;

\echo == T1 strike rows, one symbol-day (SENSEX) ==
EXPLAIN
SELECT run_id, ts, expiry_date, dte, strike, spot,
       oi_call, oi_put, gamma_call, gamma_put, gex_cr
  FROM public.gex_strike_snapshots
 WHERE symbol = 'SENSEX'
   AND ts >= timestamptz '2026-11-23 00:00:00+05:30'
   AND ts <  timestamptz '2026-11-24 00:00:00+05:30'
 ORDER BY ts, expiry_date, strike;

\echo == T2 Board rows, one symbol-day (NIFTY) ==
EXPLAIN
SELECT run_id, ts, expiry_date, dte, spot, pin_leader_strike, session_gate_state
  FROM public.gex_cycle_history
 WHERE symbol = 'NIFTY'
   AND ts >= timestamptz '2026-11-23 00:00:00+05:30'
   AND ts <  timestamptz '2026-11-24 00:00:00+05:30'
 ORDER BY ts, expiry_date;

\echo == T2 Board rows, one symbol-day (SENSEX) ==
EXPLAIN
SELECT run_id, ts, expiry_date, dte, spot, pin_leader_strike, session_gate_state
  FROM public.gex_cycle_history
 WHERE symbol = 'SENSEX'
   AND ts >= timestamptz '2026-11-23 00:00:00+05:30'
   AND ts <  timestamptz '2026-11-24 00:00:00+05:30'
 ORDER BY ts, expiry_date;

\echo == T3 the 15:29 IST one-minute close bar (NIFTY) ==
-- bar_ts is TRUE UTC for rows from 2026-04 (operator ruling 2026-11-24, R2;
-- MERDIAN_Data_Inventory.md section 12), so the 15:29 IST minute-start bar
-- carries bar_ts = '<date> 09:59:00+00'. It is the CAS settled close written
-- by capture_cas_close.py at 16:20 IST (ADR-022).
EXPLAIN
SELECT bar_ts, close
  FROM public.hist_spot_bars_1m
 WHERE instrument_id = (SELECT id FROM public.instruments WHERE symbol = 'NIFTY')
   AND bar_ts = timestamptz '2026-11-23 09:59:00+00';

\echo == T3 the 15:29 IST one-minute close bar (SENSEX) ==
EXPLAIN
SELECT bar_ts, close
  FROM public.hist_spot_bars_1m
 WHERE instrument_id = (SELECT id FROM public.instruments WHERE symbol = 'SENSEX')
   AND bar_ts = timestamptz '2026-11-23 09:59:00+00';

\echo == T4 bar-label convention guard, one symbol-day (NIFTY) ==
-- The runner asserts last_bar = '<date> 09:59:00+00' and STOPS otherwise: a
-- last label of 15:29+00 would mean the legacy IST-as-UTC era, and a last
-- label short of 09:59 means the CAS close has not landed yet.
EXPLAIN
SELECT min(bar_ts) AS first_bar, max(bar_ts) AS last_bar, count(*) AS n_bars
  FROM public.hist_spot_bars_1m
 WHERE instrument_id = (SELECT id FROM public.instruments WHERE symbol = 'NIFTY')
   AND bar_ts >= timestamptz '2026-11-23 00:00:00+00'
   AND bar_ts <  timestamptz '2026-11-24 00:00:00+00';

\echo == T4 bar-label convention guard, one symbol-day (SENSEX) ==
EXPLAIN
SELECT min(bar_ts) AS first_bar, max(bar_ts) AS last_bar, count(*) AS n_bars
  FROM public.hist_spot_bars_1m
 WHERE instrument_id = (SELECT id FROM public.instruments WHERE symbol = 'SENSEX')
   AND bar_ts >= timestamptz '2026-11-23 00:00:00+00'
   AND bar_ts <  timestamptz '2026-11-24 00:00:00+00';

\echo == T5 tau, exactly as v_gex_strike_pin_zone resolves it ==
EXPLAIN
SELECT COALESCE(public.get_parameter_num('pin.tau.' || s.symbol), 0.3) AS tau
  FROM (VALUES ('NIFTY'::text), ('SENSEX'::text)) s(symbol);
