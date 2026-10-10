-- P1c predictor extract. Pre-registered with docs/research/s94_priority/P1c_regime_range_prereg_2026-10-10.md.
-- Reads PREDICTORS only (net gamma, true HHI at each session's t0 run); no outcome is read here.
-- t0 = first gex_strike_snapshots run with ts in [09:15, 10:15) IST on the IST session date (P1 §3, p1_part2_extract.sql:26-34).
-- Front expiry = nearest expiry_date >= session date (P1 p1_part2_extract.sql:48-50).
-- Run: bin/roq.sh < p1c_regime_extract.sql > p1c_regime_2026-10-10.csv
\set QUIET on
\pset format csv
WITH runs AS (
    SELECT symbol, (ts AT TIME ZONE 'Asia/Kolkata')::date AS session_date, min(ts) AS t0
      FROM public.gex_strike_snapshots
     WHERE ts >= TIMESTAMPTZ '2026-05-25 00:00+05:30'
       AND ts <  TIMESTAMPTZ '2026-10-10 00:00+05:30'
       AND (ts AT TIME ZONE 'Asia/Kolkata')::time >= TIME '09:15'
       AND (ts AT TIME ZONE 'Asia/Kolkata')::time <  TIME '10:15'
     GROUP BY 1, 2
), rws AS (
    SELECT r.symbol, r.session_date, r.t0, g.expiry_date, g.gex_cr
      FROM runs r
      JOIN public.gex_strike_snapshots g ON g.symbol = r.symbol AND g.ts = r.t0
), fexp AS (
    SELECT symbol, session_date, min(expiry_date) AS fe
      FROM rws WHERE expiry_date >= session_date GROUP BY 1, 2
), agg AS (
    SELECT w.symbol, w.session_date, w.t0, f.fe, w.gex_cr,
           sum(abs(w.gex_cr)) OVER (PARTITION BY w.symbol, w.session_date) AS sa
      FROM rws w JOIN fexp f USING (symbol, session_date)
     WHERE w.expiry_date = f.fe
)
SELECT symbol, session_date,
       to_char(t0 AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI:SS') AS t0_ist,
       fe AS front_expiry,
       count(*) AS n_strikes,
       sum(gex_cr) AS net_gex_cr,
       max(sa) AS gross_abs_gex_cr,
       sum((abs(gex_cr) / NULLIF(sa, 0)) ^ 2) AS hhi
  FROM agg
 GROUP BY symbol, session_date, t0, fe
 ORDER BY symbol, session_date;
