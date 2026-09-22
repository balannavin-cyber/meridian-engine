-- ============================================================================
-- backfill_pin_maxpain_runs()  --  chunked populator for gex_pin_maxpain_history
-- Session 80 (2026-09-22) · ADR-025
-- ============================================================================
--
-- WHAT
--   Reproduces v_gex_strike_pin_zone's recursive tau walk for up to p_limit
--   unprocessed runs in a ts window, joins the ENH-123 max-pain argmin, and
--   inserts one row per (symbol, run_id, expiry_date).
--
-- WHY CHUNKED
--   PostgREST enforces an 8 s statement ceiling. A whole symbol-day (~83 runs)
--   measured 8.45 s over RPC and timed out; 20 runs measured 1.17 s (~59 ms
--   per run, 7x under the ceiling). p_limit defaults to 20 for that margin.
--   Raising it would still fit but buys nothing -- the full 11,795-run
--   backfill is ~12 minutes either way.
--
-- WHY THE ts WINDOW, NOT A DATE
--   (ts AT TIME ZONE 'Asia/Kolkata')::date is not sargable: measured 465 ms
--   and 332,528 rows removed by filter, because it falls back to idx_gss_run_id.
--   A ts range uses ix_gex_strike_snap_sym_ts -- 19.6 ms, clean index scan.
--   Callers pass (date-1) 18:30Z -> date 18:30Z for an IST calendar day.
--
-- RESUMABILITY
--   The NOT EXISTS pre-filter skips completed runs before any walk executes,
--   so a finished day returns 0 in milliseconds. ON CONFLICT DO NOTHING is the
--   second line of defence. Verified S80: re-running a completed day inserts 0.
--
-- FIDELITY
--   The peak/walk/pin CTEs mirror v_gex_strike_pin_zone exactly -- gex_cr > 0,
--   the abs(strike - spot) tie-break, get_parameter_num('pin.tau.'||symbol)
--   with the 0.3 fallback, and peak_pin_strike as the argmax WITHIN the walk
--   rows (not the run-wide argmax; those differ when the surface is ragged).
--   Gate: reproduced the live view on 2026-09-18 for both symbols, all four of
--   peak_pin_strike / pin_lower / pin_upper / n_strikes identical.
--
-- DEPENDS ON
--   public.gex_strike_snapshots, public.gex_pin_maxpain_history,
--   get_parameter_num(text)
--
-- SUPERSEDES
--   backfill_pin_maxpain(text, date) -- whole-day unit, dropped S80. It
--   computed every run before ON CONFLICT could discard it, so even a
--   completed day paid full price and exceeded the ceiling. Do not reinstate.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.backfill_pin_maxpain_runs(
  p_symbol text,
  p_ts_from timestamp with time zone,
  p_ts_to timestamp with time zone,
  p_limit integer DEFAULT 20
)
RETURNS integer
LANGUAGE plpgsql
AS $function$
DECLARE n integer; v_runs uuid[];
BEGIN
  SELECT array_agg(run_id) INTO v_runs FROM (
    SELECT DISTINCT g.run_id
    FROM public.gex_strike_snapshots g
    WHERE g.symbol = p_symbol AND g.ts >= p_ts_from AND g.ts < p_ts_to
      AND NOT EXISTS (SELECT 1 FROM public.gex_pin_maxpain_history h
                      WHERE h.symbol = g.symbol AND h.run_id = g.run_id)
    LIMIT p_limit) x;
  IF v_runs IS NULL THEN RETURN 0; END IF;

  WITH RECURSIVE scoped AS (
    SELECT g.run_id, g.symbol, g.ts, g.expiry_date, g.dte, g.strike,
           g.spot, g.oi_call, g.oi_put, g.gex_cr
    FROM public.gex_strike_snapshots g
    WHERE g.symbol = p_symbol AND g.ts >= p_ts_from AND g.ts < p_ts_to
      AND g.run_id = ANY(v_runs)
  ),
  strike_step AS (
    SELECT x.run_id, x.symbol, x.expiry_date, min(x.diff) AS step
    FROM (SELECT run_id, symbol, expiry_date,
                 strike - lag(strike) OVER (PARTITION BY run_id, symbol, expiry_date ORDER BY strike) AS diff
          FROM scoped) x
    WHERE x.diff > 0::numeric
    GROUP BY x.run_id, x.symbol, x.expiry_date
  ),
  peak AS (
    SELECT DISTINCT ON (run_id, symbol, expiry_date)
           run_id, symbol, expiry_date, ts, spot,
           strike AS peak_strike, gex_cr AS peak_gex_cr,
           COALESCE(get_parameter_num('pin.tau.'::text || symbol), 0.3) AS tau
    FROM scoped WHERE gex_cr > 0::numeric
    ORDER BY run_id, symbol, expiry_date, gex_cr DESC, (abs(strike - spot))
  ),
  walk AS (
    SELECT p.run_id, p.symbol, p.expiry_date, p.ts, p.peak_strike AS strike,
           p.peak_gex_cr AS gex_cr, p.peak_gex_cr, p.tau, s.step, 0 AS direction
    FROM peak p JOIN strike_step s USING (run_id, symbol, expiry_date)
    UNION ALL
    SELECT g.run_id, g.symbol, g.expiry_date, g.ts, g.strike, g.gex_cr,
           w.peak_gex_cr, w.tau, w.step,
           CASE WHEN g.strike < w.strike THEN -1 ELSE 1 END
    FROM walk w
    JOIN scoped g
      ON g.run_id = w.run_id AND g.symbol = w.symbol AND g.expiry_date = w.expiry_date
     AND ((w.direction = ANY (ARRAY[0,-1])) AND abs(g.strike - (w.strike - w.step)) < 0.0001
       OR (w.direction = ANY (ARRAY[0, 1])) AND abs(g.strike - (w.strike + w.step)) < 0.0001)
    WHERE g.gex_cr > 0::numeric AND g.gex_cr >= (w.tau * w.peak_gex_cr)
  ),
  pin AS (
    SELECT run_id, symbol, expiry_date, max(ts) AS ts,
           min(strike) AS pin_lower, max(strike) AS pin_upper,
           count(*) AS pin_n_strikes, max(peak_gex_cr) AS peak_pin_gex_cr,
           (array_agg(strike ORDER BY gex_cr DESC))[1] AS peak_pin_strike,
           max(tau) AS tau_used
    FROM walk GROUP BY run_id, symbol, expiry_date
  ),
  pain AS (
    SELECT k.run_id, k.symbol, k.expiry_date, k.strike AS cand,
           SUM(GREATEST(k.strike - c.strike, 0) * COALESCE(c.oi_call,0))
         + SUM(GREATEST(c.strike - k.strike, 0) * COALESCE(c.oi_put,0)) AS tp
    FROM scoped k JOIN scoped c
      ON c.run_id = k.run_id AND c.symbol = k.symbol AND c.expiry_date = k.expiry_date
    GROUP BY k.run_id, k.symbol, k.expiry_date, k.strike
  ),
  mp AS (
    SELECT DISTINCT ON (run_id, symbol, expiry_date)
           run_id, symbol, expiry_date, cand AS max_pain_strike
    FROM pain ORDER BY run_id, symbol, expiry_date, tp ASC, cand ASC
  ),
  meta AS (
    SELECT run_id, symbol, expiry_date, max(ts) AS ts, max(dte) AS dte,
           max(spot) AS spot, count(*) AS chain_n_strikes
    FROM scoped GROUP BY run_id, symbol, expiry_date
  )
  INSERT INTO public.gex_pin_maxpain_history
    (symbol, run_id, ts, expiry_date, dte, spot, peak_pin_strike, pin_lower, pin_upper,
     pin_n_strikes, peak_pin_gex_cr, tau_used, max_pain_strike, chain_n_strikes)
  SELECT m.symbol, m.run_id, m.ts, m.expiry_date, m.dte, m.spot,
         p.peak_pin_strike, p.pin_lower, p.pin_upper, p.pin_n_strikes,
         p.peak_pin_gex_cr, p.tau_used, mp.max_pain_strike, m.chain_n_strikes
  FROM meta m
  JOIN pin p USING (run_id, symbol, expiry_date)
  JOIN mp    USING (run_id, symbol, expiry_date)
  ON CONFLICT (symbol, run_id, expiry_date) DO NOTHING;

  GET DIAGNOSTICS n = ROW_COUNT;
  RETURN n;
END $function$;

GRANT EXECUTE ON FUNCTION
  public.backfill_pin_maxpain_runs(text, timestamptz, timestamptz, integer)
  TO service_role;

-- Driver: scripts/backfill_pin_maxpain.py -- loops calls-until-zero per
-- symbol-day, newest first, 30-call cap, retries with the HTTP response body
-- logged. Full run S80: 11,795 / 11,795 runs, zero failures.
