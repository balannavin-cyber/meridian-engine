-- =====================================================================
-- 2026-05-25_v_oi_prev_close_snapshots.sql
-- ADR-015 §F1 — prior-day EOD OI view for OI-Change GEX derivation
-- =====================================================================
--
-- Returns the most recent option_chain_snapshots row per
-- (symbol, expiry_date, strike, option_type) tuple where the row's IST
-- date is strictly before today's IST date.
--
-- "Most recent prior trading day" handled implicitly — weekends/holidays
-- have no rows, so DISTINCT ON automatically picks Friday's EOD when
-- queried on Monday.
--
-- Consumer pattern (OI-Change GEX, to be implemented in ENH-81):
--
--   SELECT
--     ocs.symbol, ocs.expiry_date, ocs.strike, ocs.option_type,
--     ocs.oi                                       AS curr_oi,
--     v.prev_close_oi                              AS prev_oi,
--     (ocs.oi - COALESCE(v.prev_close_oi, 0))      AS oi_change,
--     ocs.gamma, ocs.spot,
--     ((ocs.oi - COALESCE(v.prev_close_oi, 0))
--       * ocs.gamma * POWER(ocs.spot, 2) / 1e7)    AS oi_change_gex_cr
--   FROM option_chain_snapshots ocs
--   LEFT JOIN v_oi_prev_close_snapshots v USING (symbol, expiry_date, strike, option_type)
--   WHERE ocs.run_id = :latest_run_id;
--
-- LEFT JOIN handles new strikes that didn't exist yesterday (prev_oi → 0).
-- COALESCE → treat absent prior as zero baseline (full OI is "new").
--
-- Performance note: option_chain_snapshots is large. If this view becomes
-- slow, materialize as a per-day snapshot table written by a daily cron
-- job at session start. Defer materialization until measured pain.
-- =====================================================================

CREATE OR REPLACE VIEW v_oi_prev_close_snapshots AS
SELECT DISTINCT ON (symbol, expiry_date, strike, option_type)
  symbol,
  expiry_date,
  strike,
  option_type,
  oi  AS prev_close_oi,
  ts  AS prev_close_ts
FROM option_chain_snapshots
WHERE (ts AT TIME ZONE 'Asia/Kolkata')::date
      < (now() AT TIME ZONE 'Asia/Kolkata')::date
ORDER BY symbol, expiry_date, strike, option_type, ts DESC;

COMMENT ON VIEW v_oi_prev_close_snapshots IS
  'ADR-015 §F1 — most recent prior-trading-day EOD OI per (symbol, expiry, strike, option_type). Source: option_chain_snapshots. Weekend/holiday safe via DISTINCT ON + DESC sort.';
