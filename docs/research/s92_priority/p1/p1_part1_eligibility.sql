-- P1 level test — Part 1: preconditions and eligibility. READ-ONLY. Reveals no outcome
-- (no high, no low, no price beyond a minute COUNT).
-- Pre-registration: docs/research/s92_priority/P1_level_test_prereg_2026-10-09.md
--                   git hash-object 7a708a64c4bb73f0712a6d6e78f92a5d411a8ece
-- Run 1a and 1b SEPARATELY (the editor shows only the last statement's result).

-- ---------------------------------------------------------------- 1a  Rule 13 (§6.1)
SELECT contamination_id, field_scope, contamination_start, contamination_end,
       affected_tables::text AS affected_tables,
       (affected_tables::text ~* '(gex_strike_snapshots|market_spot_snapshots|volatility_snapshots|trading_calendar)')
         AS hits_study_tables
  FROM public.data_contamination_ranges
 WHERE contamination_start < TIMESTAMPTZ '2026-10-09 00:00:00+05:30'
   AND COALESCE(contamination_end, 'infinity'::timestamptz) >= TIMESTAMPTZ '2026-05-25 00:00:00+05:30'
 ORDER BY contamination_start;

-- ---------------------------------------------------------------- 1b  Eligibility (§4) + §6.2–6.5
WITH cal AS (
    SELECT tc.trade_date AS session_date
      FROM trading_calendar tc
     WHERE tc.trade_date BETWEEN DATE '2026-05-25' AND DATE '2026-10-08'
       AND tc.is_open
), grid AS (
    SELECT s.symbol, c.session_date
      FROM (VALUES ('NIFTY'), ('SENSEX')) s(symbol) CROSS JOIN cal c
), t0 AS (                       -- first run with ts in [09:15, 10:15) IST  (§3, §4.2)
    SELECT g.symbol, g.session_date, r.run_id, r.ts AS t0
      FROM grid g
      LEFT JOIN LATERAL (
           SELECT x.run_id, x.ts
             FROM gex_strike_snapshots x
            WHERE x.symbol = g.symbol
              AND x.ts >= (g.session_date + TIME '09:15') AT TIME ZONE 'Asia/Kolkata'
              AND x.ts <  (g.session_date + TIME '10:15') AT TIME ZONE 'Asia/Kolkata'
            ORDER BY x.ts
            LIMIT 1) r ON true
), runrows AS (
    SELECT t.symbol, t.session_date, x.expiry_date, x.strike, x.spot
      FROM t0 t
      JOIN gex_strike_snapshots x
        ON x.symbol = t.symbol AND x.run_id = t.run_id
       AND x.ts >= t.t0 AND x.ts < t.t0 + interval '5 minutes'
), hdr AS (
    SELECT symbol, session_date,
           count(DISTINCT spot)        AS n_spot,      -- §6.4
           count(DISTINCT expiry_date) AS n_expiry     -- §6.5
      FROM runrows GROUP BY 1, 2
), stp AS (                      -- §6.3 grid step, front expiry
    SELECT symbol, session_date, min(d) AS step
      FROM (SELECT r.symbol, r.session_date,
                   r.strike - lag(r.strike) OVER (PARTITION BY r.symbol, r.session_date ORDER BY r.strike) AS d
              FROM runrows r
             WHERE r.expiry_date = (SELECT min(r2.expiry_date) FROM runrows r2
                                     WHERE r2.symbol = r.symbol AND r2.session_date = r.session_date
                                       AND r2.expiry_date >= r.session_date)) q
     WHERE d > 0 GROUP BY 1, 2
), iv AS (                       -- §4.3 latest atm_iv_avg <= t0
    SELECT t.symbol, t.session_date, v.ts AS iv_ts
      FROM t0 t
      LEFT JOIN LATERAL (
           SELECT vs.ts FROM volatility_snapshots vs
            WHERE vs.symbol = t.symbol AND vs.ts <= t.t0 AND vs.atm_iv_avg IS NOT NULL
            ORDER BY vs.ts DESC LIMIT 1) v ON true
), mins AS (                     -- §4.4 minute COUNT only, (t0, 15:15) IST
    SELECT t.symbol, t.session_date, count(DISTINCT date_trunc('minute', m.ts)) AS n_minutes
      FROM t0 t
      JOIN market_spot_snapshots m
        ON m.symbol = t.symbol AND m.spot IS NOT NULL
       AND m.ts > t.t0
       AND m.ts < (t.session_date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata'
     GROUP BY 1, 2
), cls AS (
    SELECT t.symbol, t.session_date, t.t0, h.n_spot, h.n_expiry, s.step,
           round((EXTRACT(epoch FROM (t.t0 - i.iv_ts)) / 60.0)::numeric, 1) AS iv_age_min,
           COALESCE(mn.n_minutes, 0) AS n_minutes,
           CASE WHEN t.run_id IS NULL THEN 'no_t0_run'
                WHEN i.iv_ts IS NULL
                  OR (i.iv_ts AT TIME ZONE 'Asia/Kolkata')::date <> t.session_date THEN 'no_same_day_iv'
                WHEN COALESCE(mn.n_minutes, 0) < 300 THEN 'lt_300_min'
           END AS drop_reason
      FROM t0 t
      LEFT JOIN hdr  h  USING (symbol, session_date)
      LEFT JOIN stp  s  USING (symbol, session_date)
      LEFT JOIN iv   i  USING (symbol, session_date)
      LEFT JOIN mins mn USING (symbol, session_date)
), el AS (
    SELECT c.*,
           CASE WHEN c.drop_reason IS NULL THEN
                row_number() OVER (PARTITION BY c.symbol, (c.drop_reason IS NULL) ORDER BY c.session_date) END AS sess_ix,
           floor(0.67 * count(*) FILTER (WHERE c.drop_reason IS NULL) OVER (PARTITION BY c.symbol))::int AS n_cal
      FROM cls c
)
SELECT symbol,
       count(*)                                               AS n_open_days,
       count(*) FILTER (WHERE drop_reason IS NULL)            AS n_eligible,
       max(n_cal)                                             AS n_calibration,
       max(session_date) FILTER (WHERE sess_ix = n_cal)       AS last_calibration_date,
       min(session_date) FILTER (WHERE sess_ix = n_cal + 1)   AS first_holdout_date,
       string_agg(session_date || ' ' || drop_reason, ', ' ORDER BY session_date)
         FILTER (WHERE drop_reason IS NOT NULL)               AS dropped,
       string_agg(session_date || ' step=' || COALESCE(step::text, 'NULL'), ', ' ORDER BY session_date)
         FILTER (WHERE drop_reason IS NULL
                   AND step IS DISTINCT FROM CASE symbol WHEN 'NIFTY' THEN 50 ELSE 100 END) AS grid_failures,
       count(*) FILTER (WHERE drop_reason IS NULL AND n_spot   <> 1) AS multi_spot_runs,
       count(*) FILTER (WHERE drop_reason IS NULL AND n_expiry >  1) AS multi_expiry_runs,
       min((t0 AT TIME ZONE 'Asia/Kolkata')::time) FILTER (WHERE drop_reason IS NULL) AS t0_earliest,
       max((t0 AT TIME ZONE 'Asia/Kolkata')::time) FILTER (WHERE drop_reason IS NULL) AS t0_latest,
       percentile_cont(0.5) WITHIN GROUP (ORDER BY iv_age_min) FILTER (WHERE drop_reason IS NULL) AS iv_age_min_median,
       max(iv_age_min) FILTER (WHERE drop_reason IS NULL)    AS iv_age_min_max
  FROM el
 GROUP BY symbol
 ORDER BY symbol;
