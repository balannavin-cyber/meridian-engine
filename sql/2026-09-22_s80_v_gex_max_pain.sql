-- ============================================================================
-- ENH-123 · v_gex_max_pain
-- Session 80 (2026-09-22) · ADR-025
-- ============================================================================
--
-- WHAT
--   Max pain per (symbol, run_id, expiry_date) over gex_strike_snapshots:
--   total writer pain at each candidate strike, argmin, and a side label.
--
-- WHY A SECOND MAX-PAIN VIEW EXISTS
--   v_max_pain_by_strike (S40, 2026-05-29) already ships and renders on the
--   Marketview Max Pain page. It is NOT replaced -- both are live. This one
--   differs in four ways that matter:
--     1. Base is gex_strike_snapshots (1.58M rows, no retention policy) rather
--        than option_chain_snapshots, measured at only 18 days of history
--        (2026-08-24 -> 2026-09-17), NOT the ~11 days previously on record.
--     2. Scoped on (symbol, run_id, expiry_date). The S40 view groups by
--        (symbol, strike) with no expiry filter, so multiple expiries in one
--        snapshot would collapse into a per-strike mixture. Latent, not firing
--        -- measured 1 expiry per OCS cycle across all 2,923 cycles.
--     3. Emits ts / run_id / expiry_date / dte and a freshness flag. The S40
--        view emits no timestamp at all, so a consumer cannot tell a current
--        row from a three-week-old one, and its unbounded max(ts) will serve a
--        complete, plausible, stale strike if chain ingest stops.
--     4. Deterministic tie-break on the argmin. The S40 view's bare
--        row_number() leaves ties to plan order.
--
-- EQUIVALENCE GATE
--   Agreed with v_max_pain_by_strike on both symbols at first light --
--   NIFTY 23,300 and SENSEX 74,400 -- from a different base table, a different
--   pivot and snapshots 20 minutes apart. Not a tautology; a real cross-check.
--
-- FRESHNESS FLOOR
--   maxpain.stale_floor_min via get_parameter_num, COALESCE default 30. Probed
--   CAN FIRE under BEGIN/ROLLBACK: stale_floor_min_used tracked 30 -> 20 ->
--   99999 and is_fresh flipped false -> true at an unchanged age, so the
--   parameter drives the comparison and the floor is not decorative. That
--   closes the TD-S79-NEW-2 ambiguity (seeded value == COALESCE fallback makes
--   a successful read and a NULL read indistinguishable) for this view.
--   The parameter is deliberately NOT seeded -- the default 30 differs from any
--   value we would seed, keeping the two cases distinguishable.
--
-- PARITY STATUS
--   NOT a parity layer. Max pain appears nowhere in the fourteen layers or the
--   build order of MERDIAN_Hedgewall_Parity_Spec.md. ADR-025 D5 files it as
--   L19, an extension under section 2.5. Parked: applied, unrendered, not
--   counted toward parity.
--
-- DEPENDS ON  public.gex_strike_snapshots · get_parameter_num(text)
-- BODY        pg_get_viewdef(..., true) as deployed -- Postgres-normalised, so
--             this is what is running, not what was typed.
-- ============================================================================

CREATE OR REPLACE VIEW public.v_gex_max_pain AS
 WITH latest_run AS (
         SELECT DISTINCT ON (gex_strike_snapshots.symbol) gex_strike_snapshots.symbol,
            gex_strike_snapshots.ts,
            gex_strike_snapshots.run_id
           FROM gex_strike_snapshots
          ORDER BY gex_strike_snapshots.symbol, gex_strike_snapshots.ts DESC
        ), scoped AS (
         SELECT g.symbol,
            g.run_id,
            g.ts,
            g.expiry_date,
            g.strike,
            COALESCE(g.oi_call, 0::bigint) AS oi_call,
            COALESCE(g.oi_put, 0::bigint) AS oi_put
           FROM gex_strike_snapshots g
             JOIN latest_run l ON l.symbol = g.symbol AND l.ts = g.ts AND l.run_id = g.run_id
        ), cohort AS (
         SELECT scoped.symbol,
            scoped.run_id,
            scoped.expiry_date,
            count(*) AS n_strikes,
            count(*) FILTER (WHERE scoped.oi_call > 0) AS n_call_oi,
            count(*) FILTER (WHERE scoped.oi_put > 0) AS n_put_oi
           FROM scoped
          GROUP BY scoped.symbol, scoped.run_id, scoped.expiry_date
        ), pain AS (
         SELECT k.symbol,
            k.run_id,
            k.ts,
            k.expiry_date,
            k.strike AS candidate_strike,
            sum(GREATEST(k.strike - c_1.strike, 0::numeric) * c_1.oi_call::numeric) + sum(GREATEST(c_1.strike - k.strike, 0::numeric) * c_1.oi_put::numeric) AS total_pain
           FROM scoped k
             JOIN scoped c_1 ON c_1.symbol = k.symbol AND c_1.run_id = k.run_id AND c_1.expiry_date = k.expiry_date
          GROUP BY k.symbol, k.run_id, k.ts, k.expiry_date, k.strike
        ), argmin AS (
         SELECT DISTINCT ON (pain.symbol, pain.run_id, pain.expiry_date) pain.symbol,
            pain.run_id,
            pain.expiry_date,
            pain.candidate_strike AS max_pain_strike,
            pain.total_pain AS max_pain_value
           FROM pain
          ORDER BY pain.symbol, pain.run_id, pain.expiry_date, pain.total_pain, pain.candidate_strike
        )
 SELECT p.symbol,
    p.run_id,
    p.ts,
    p.expiry_date,
    p.expiry_date - (p.ts AT TIME ZONE 'Asia/Kolkata'::text)::date AS dte,
    p.candidate_strike,
    p.total_pain,
    a.max_pain_strike,
    a.max_pain_value,
        CASE
            WHEN p.candidate_strike < a.max_pain_strike THEN 'PE_SIDE'::text
            WHEN p.candidate_strike > a.max_pain_strike THEN 'CE_SIDE'::text
            ELSE 'MAX_PAIN'::text
        END AS side,
    c.n_strikes,
    round(100.0 * c.n_call_oi::numeric / NULLIF(c.n_strikes, 0)::numeric, 1) AS call_oi_coverage_pct,
    round(100.0 * c.n_put_oi::numeric / NULLIF(c.n_strikes, 0)::numeric, 1) AS put_oi_coverage_pct,
    round(EXTRACT(epoch FROM now() - p.ts) / 60.0, 1) AS snapshot_age_min,
    COALESCE(get_parameter_num('maxpain.stale_floor_min'::text), 30::numeric) AS stale_floor_min_used,
    (EXTRACT(epoch FROM now() - p.ts) / 60.0) <= COALESCE(get_parameter_num('maxpain.stale_floor_min'::text), 30::numeric) AS is_fresh
   FROM pain p
     JOIN argmin a USING (symbol, run_id, expiry_date)
     JOIN cohort c USING (symbol, run_id, expiry_date);

GRANT SELECT ON public.v_gex_max_pain TO anon;

COMMENT ON VIEW public.v_gex_max_pain IS
  'ENH-123 (S80). Max pain over gex_strike_snapshots, scoped per '
  '(symbol, run_id, expiry_date), emitting ts/dte/coverage/freshness. '
  'Distinct from v_max_pain_by_strike (S40), which is chain-based, has no '
  'expiry filter and emits no timestamp. Both are live. Extension (L19), '
  'not a parity layer -- ADR-025 D5.';
