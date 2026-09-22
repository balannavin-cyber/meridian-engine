-- ============================================================================
-- ENH-124 · v_gex_pin_maxpain
-- Session 80 (2026-09-22) · ADR-025
-- ============================================================================
--
-- WHAT
--   Joins max pain (ENH-123), the pin zone (ENH-81) and the walls (ENH-120)
--   on the same run, and emits the DISTANCE between max pain and peak gamma --
--   in points, in strike steps, and in sigma -- plus band and corridor tests.
--
-- IT EMITS A DISTANCE, NOT A VERDICT -- DELIBERATELY
--   The brief that motivated this asked for "max pain and the pin on the same
--   strike" as a signal. That needs a tolerance, and TD-S79-NEW-21's ruling
--   applies: measure first, then parameterise, because parameterising an
--   unmeasured constant relocates it rather than calibrating it. No tolerance
--   constant appears in this view and none should be added until the history
--   supports one.
--
-- WHAT THE HISTORY SAYS (S80, gex_pin_maxpain_history, 11,795 runs)
--   The gap is a stable -0.4 sigma. Medians run -0.32 to -0.66 across BOTH
--   symbols, EVERY DTE and EVERY session hour; it never changes sign. Max pain
--   sits systematically below peak gamma -- close to a constant of this market,
--   not a varying relationship.
--
--   Exact coincidence is rare: 1.2-5.4% everywhere EXCEPT NIFTY at 0 DTE,
--   which runs 13.9% (164/1182) -- roughly 3x the next cell and 13x a random
--   landing. SENSEX at 0 DTE is NOT elevated (3.4%), so this is NIFTY expiry
--   day, not expiry day generically. Part of the symbol difference is grid
--   granularity: NIFTY 50 on ~23,500 (0.21% per strike) vs SENSEX 100 on
--   ~75,000 (0.13%). That does not explain 13.9% against NIFTY's own 2.8-5.4%
--   at other DTEs, since the grid does not change with DTE.
--
--   max_pain_in_pin_band is NOT a weaker form of coincidence and is close to
--   useless as a signal: NIFTY 6-DTE has the highest band rate in the sample
--   (42.1%) on a 2.9% exact rate. It fires on two runs in five regardless.
--
-- WHETHER COINCIDENCE PREDICTS ANYTHING IS UNANSWERED
--   That is a conjunction question, governed by Hedgewall_Parity_Spec section
--   5 and ADR-009: pre-registration, target and success criterion written
--   before the first query. ENH-97 is the standing warning -- chi-sq 1.56,
--   p ~= 0.30 on 1,968 signals.
--
-- SIGMA, NOT POINTS
--   Points are not a distance (ADR-024 A4). First light: NIFTY -4 strikes /
--   -0.587 sigma, SENSEX -1 strike / -0.128 sigma. Nearly equal in strikes,
--   4.6x apart in sigma. Any eventual rule reads gap_sigma.
--
--   sigma_overstated_expiry_day carries TD-S79-NEW-1 in the row rather than in
--   a footnote: GREATEST(dte,1) substitutes a full day for the remainder of an
--   expiry session. S80 measured the overstatement as TIME-VARYING, not a
--   constant scale error -- ~2% at the open, ~5x by 15:00 -- and it HIDES an
--   intraday effect: under day-sigma the 0-DTE gap looks flat through the
--   session (-0.398 -> -0.224), under correct remaining-time sigma it more
--   than doubles (-0.382 -> -0.939).
--
-- PARITY STATUS
--   NOT a parity layer. ADR-025 D5 files it as L19 alongside ENH-123. Parked:
--   applied, unrendered, not counted.
--
-- DEPENDS ON, IN ORDER -- a rebuild from sql/ MUST apply these first:
--   1. public.gex_strike_snapshots            (ENH-80, ADR-015)
--   2. public.v_gex_strike_pin_zone           (ENH-81, re-scoped by ADR-021)
--   3. public.v_gex_strike_walls              (ENH-120, S79)
--   4. public.v_gex_max_pain                  (ENH-123, this session)
--   Applying this file against a database missing any of them fails with a
--   bare dependency error and no explanation. TD-S79-NEW-3 is the precedent:
--   sql/ that cannot rebuild what is running is worse than no sql/ at all.
--
-- BODY  pg_get_viewdef(..., true) as deployed -- Postgres-normalised.
-- ============================================================================

CREATE OR REPLACE VIEW public.v_gex_pin_maxpain AS
 WITH latest_run AS (
         SELECT DISTINCT ON (gex_strike_snapshots.symbol) gex_strike_snapshots.symbol,
            gex_strike_snapshots.ts,
            gex_strike_snapshots.run_id
           FROM gex_strike_snapshots
          ORDER BY gex_strike_snapshots.symbol, gex_strike_snapshots.ts DESC
        ), scoped AS (
         SELECT g.symbol,
            g.run_id,
            g.expiry_date,
            g.strike
           FROM gex_strike_snapshots g
             JOIN latest_run l ON l.symbol = g.symbol AND l.ts = g.ts AND l.run_id = g.run_id
        ), steps AS (
         SELECT x.symbol,
            x.run_id,
            x.expiry_date,
            min(x.d) AS strike_step
           FROM ( SELECT scoped.symbol,
                    scoped.run_id,
                    scoped.expiry_date,
                    scoped.strike - lag(scoped.strike) OVER (PARTITION BY scoped.symbol, scoped.run_id, scoped.expiry_date ORDER BY scoped.strike) AS d
                   FROM scoped) x
          WHERE x.d > 0::numeric
          GROUP BY x.symbol, x.run_id, x.expiry_date
        )
 SELECT mp.symbol,
    mp.run_id,
    mp.ts,
    mp.expiry_date,
    mp.dte,
    w.spot,
    w.sigma,
    w.atm_iv_used,
    mp.max_pain_strike,
    pz.peak_pin_strike,
    pz.pin_lower,
    pz.pin_upper,
    st.strike_step,
    mp.max_pain_strike - pz.peak_pin_strike AS gap_points,
    (mp.max_pain_strike - pz.peak_pin_strike) / st.strike_step AS gap_strikes,
    (mp.max_pain_strike - pz.peak_pin_strike) / w.sigma AS gap_sigma,
    (mp.max_pain_strike - w.spot) / w.sigma AS max_pain_spot_sigma,
    (pz.peak_pin_strike - w.spot) / w.sigma AS peak_pin_spot_sigma,
    mp.max_pain_strike >= pz.pin_lower AND mp.max_pain_strike <= pz.pin_upper AS max_pain_in_pin_band,
    mp.max_pain_strike >= w.put_wall AND mp.max_pain_strike <= w.call_wall AS max_pain_in_corridor,
    w.corridor_state,
    w.corridor_width_sigma,
    pz.n_strikes AS pin_n_strikes,
    pz.tau_used,
    mp.n_strikes AS chain_n_strikes,
    mp.call_oi_coverage_pct,
    mp.put_oi_coverage_pct,
    mp.dte = 0 AS sigma_overstated_expiry_day,
    mp.snapshot_age_min,
    mp.is_fresh
   FROM v_gex_max_pain mp
     JOIN v_gex_strike_pin_zone pz ON pz.symbol = mp.symbol AND pz.run_id = mp.run_id AND pz.expiry_date = mp.expiry_date AND pz.ts = mp.ts
     JOIN v_gex_strike_walls w ON w.symbol = mp.symbol AND w.run_id = mp.run_id AND w.expiry_date = mp.expiry_date AND w.ts = mp.ts
     JOIN steps st ON st.symbol = mp.symbol AND st.run_id = mp.run_id AND st.expiry_date = mp.expiry_date
  WHERE mp.side = 'MAX_PAIN'::text;

GRANT SELECT ON public.v_gex_pin_maxpain TO anon;

COMMENT ON VIEW public.v_gex_pin_maxpain IS
  'ENH-124 (S80). Distance between max pain (ENH-123) and peak gamma '
  '(ENH-81), in points, strikes and sigma, with band/corridor tests. Emits a '
  'distance, never a verdict -- no tolerance constant, per TD-S79-NEW-21. '
  'History: the gap is a stable -0.4 sigma across both symbols, all DTE and '
  'all session hours. Extension (L19), not a parity layer -- ADR-025 D5.';
