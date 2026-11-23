\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- replay_v2 -- atm_iv_avg per run, ONE SYMBOL-DAY per query, one statement, read-only.
-- Literals __SYM__ __D__ (IST date) __D1__ (next IST date).
--
-- THE RULE IS v_gex_strike_rank's, transcribed from
-- sql/2026-09-22_s81_v_gex_strike_rank.sql:188-196: the newest volatility_snapshots
-- row at or before the run's ts, same symbol, atm_iv_avg NOT NULL, taken through a
-- LEFT JOIN LATERAL ... ORDER BY vs.ts DESC LIMIT 1. LEFT, not CROSS: a run with no
-- resolvable ATM IV must still appear, with atm_iv_avg NULL -- that run is counted as
-- having no FV pin, never given a zero.
-- NO age bound, exactly as the live view has none; the age is RETURNED instead
-- (age_min) so staleness is surfaced rather than enforced.
--
-- Indexed columns only: gamma_metrics on (symbol, ts) -- the leading pair of
-- uix_gamma_metrics_symbol_ts / idx_gm_ts_symbol_expiry; volatility_snapshots on
-- (symbol, ts) -- idx_volatility_snapshots_symbol_ts (symbol, ts DESC), which is also
-- what makes the DESC-ordered LIMIT 1 a single index tuple.
WITH r AS (
  SELECT g.run_id, g.ts
    FROM gamma_metrics g
   WHERE g.symbol = '__SYM__'
     AND g.ts >= timestamptz '__D__ 00:00:00+05:30'
     AND g.ts <  timestamptz '__D1__ 00:00:00+05:30'
     AND g.run_id IS NOT NULL
)
SELECT 'V0' AS tag, row_to_json(t)::text AS payload FROM (
  SELECT '__SYM__' AS sym,
         '__D__' AS d,
         r.run_id::text AS run_id,
         v.atm_iv_avg::text AS atm_iv_avg,
         round(v.age_min, 2)::text AS iva_min,
         to_char(v.vts AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') AS iv_ts_ist
    FROM r
    LEFT JOIN LATERAL (
      SELECT vs.atm_iv_avg,
             vs.ts AS vts,
             EXTRACT(epoch FROM (r.ts - vs.ts)) / 60.0 AS age_min
        FROM volatility_snapshots vs
       WHERE vs.symbol = '__SYM__'
         AND vs.ts <= r.ts
         AND vs.atm_iv_avg IS NOT NULL
       ORDER BY vs.ts DESC
       LIMIT 1
    ) v ON true
) t;
