-- S103 / ruling S103-F (2026-10-30 18:32 IST) -- TD-S90-NEW-5 / TD-S101-NEW-1: v_gex_max_pain and v_gex_pin_maxpain
-- time out at authenticator's statement_timeout = 8s because their latest_run CTE is
--     SELECT DISTINCT ON (symbol) symbol, ts, run_id FROM gex_strike_snapshots ORDER BY symbol, ts DESC
-- which the planner runs as a Unique over a FULL walk of ix_gex_strike_snap_sym_ts (EXPLAIN ANALYZE 2026-10-30 17:55 IST:
-- 2,207,583 rows, 50,045 buffers read, 17,562 ms of a 17,891 ms read; the max-pain self-join itself ~60 ms).
-- Fix: latest_run takes the S79 / S72 FIX 2 shape already live in v_gex_abs_exposure -- a recursive skip scan over symbols
-- plus CROSS JOIN LATERAL ... ORDER BY ts DESC LIMIT 1 -- O(distinct symbols) index seeks. NOTHING ELSE CHANGES: output
-- columns, grain (symbol, run_id, expiry_date), every other CTE, the grants (CREATE OR REPLACE keeps them). Registered
-- definitions before this change (rule 25, read live 2026-10-30 17:30 IST = contract section 8):
--     v_gex_max_pain     3088 / 3d067c67ef36f9841af9eea81a4c0575  (sql/2026-09-22_s80_v_gex_max_pain.sql)
--     v_gex_pin_maxpain  2577 / 0d7d5258d6a1169ffe97a94aa82474e5  (sql/2026-09-22_s80_v_gex_pin_maxpain.sql)
-- Dependents: v_gex_pin_maxpain reads v_gex_max_pain (CREATE OR REPLACE, column list unchanged, so no drop needed). Neither
-- view is a source of an ADR-032 _1pct wrapper. Deploys any time (S90-J: views).
--
-- Operator action, SQL editor, in this order: T0 (plan of the new body, nothing changed) -> T1a / T1b (equality, nothing
-- changed) -> BLOCK 1 (one execution) -> T2 (plan of the live view as the writer reads it) -> T3 (register lengths / md5s).
-- Rollback: BLOCK R re-creates the S80 bodies verbatim from the two files named above (not printed here).

-- =====================================================================  T0 -- the new latest_run shape, standalone
-- PASS: the plan shows Index Only Scan / Index Scan using ix_gex_strike_snap_sym_ts with Limit under a Nested Loop, and
-- Execution Time well under 1,000 ms (the old shape measured 17,562 ms for this CTE alone).
EXPLAIN (ANALYZE, BUFFERS, SUMMARY)
WITH RECURSIVE symbols AS (
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g) AS symbol
        UNION ALL
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g WHERE g.symbol > s.symbol)
          FROM symbols s WHERE s.symbol IS NOT NULL
     ), latest_run AS (
        SELECT s.symbol, lr.ts, lr.run_id
          FROM symbols s
          CROSS JOIN LATERAL (SELECT g.ts, g.run_id FROM gex_strike_snapshots g
                               WHERE g.symbol = s.symbol ORDER BY g.ts DESC LIMIT 1) lr
         WHERE s.symbol IS NOT NULL
     )
SELECT * FROM latest_run;

-- =====================================================================  T1a -- equality: new body vs the live v_gex_max_pain
-- Both sides evaluated in ONE statement (one now(), one latest run). snapshot_age_min / is_fresh / stale_floor_min_used are
-- now()-dependent and identical by construction; the comparison is on every other column.
-- PASS: one row, only_in_new = 0, only_in_old = 0, n_new = n_old > 0.
WITH RECURSIVE symbols AS (
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g) AS symbol
        UNION ALL
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g WHERE g.symbol > s.symbol)
          FROM symbols s WHERE s.symbol IS NOT NULL
     ), latest_run AS (
        SELECT s.symbol, lr.ts, lr.run_id
          FROM symbols s
          CROSS JOIN LATERAL (SELECT g.ts, g.run_id FROM gex_strike_snapshots g
                               WHERE g.symbol = s.symbol ORDER BY g.ts DESC LIMIT 1) lr
         WHERE s.symbol IS NOT NULL
     ), scoped AS (
         SELECT g.symbol, g.run_id, g.ts, g.expiry_date, g.strike,
                COALESCE(g.oi_call, 0::bigint) AS oi_call, COALESCE(g.oi_put, 0::bigint) AS oi_put
           FROM gex_strike_snapshots g
             JOIN latest_run l ON l.symbol = g.symbol AND l.ts = g.ts AND l.run_id = g.run_id
     ), cohort AS (
         SELECT scoped.symbol, scoped.run_id, scoped.expiry_date, count(*) AS n_strikes,
                count(*) FILTER (WHERE scoped.oi_call > 0) AS n_call_oi,
                count(*) FILTER (WHERE scoped.oi_put > 0) AS n_put_oi
           FROM scoped GROUP BY scoped.symbol, scoped.run_id, scoped.expiry_date
     ), pain AS (
         SELECT k.symbol, k.run_id, k.ts, k.expiry_date, k.strike AS candidate_strike,
                sum(GREATEST(k.strike - c_1.strike, 0::numeric) * c_1.oi_call::numeric)
              + sum(GREATEST(c_1.strike - k.strike, 0::numeric) * c_1.oi_put::numeric) AS total_pain
           FROM scoped k
             JOIN scoped c_1 ON c_1.symbol = k.symbol AND c_1.run_id = k.run_id AND c_1.expiry_date = k.expiry_date
          GROUP BY k.symbol, k.run_id, k.ts, k.expiry_date, k.strike
     ), argmin AS (
         SELECT DISTINCT ON (pain.symbol, pain.run_id, pain.expiry_date) pain.symbol, pain.run_id, pain.expiry_date,
                pain.candidate_strike AS max_pain_strike, pain.total_pain AS max_pain_value
           FROM pain
          ORDER BY pain.symbol, pain.run_id, pain.expiry_date, pain.total_pain, pain.candidate_strike
     ), new_body AS (
         SELECT p.symbol, p.run_id, p.ts, p.expiry_date,
                p.expiry_date - (p.ts AT TIME ZONE 'Asia/Kolkata'::text)::date AS dte,
                p.candidate_strike, p.total_pain, a.max_pain_strike, a.max_pain_value,
                CASE WHEN p.candidate_strike < a.max_pain_strike THEN 'PE_SIDE'::text
                     WHEN p.candidate_strike > a.max_pain_strike THEN 'CE_SIDE'::text
                     ELSE 'MAX_PAIN'::text END AS side,
                c.n_strikes,
                round(100.0 * c.n_call_oi::numeric / NULLIF(c.n_strikes, 0)::numeric, 1) AS call_oi_coverage_pct,
                round(100.0 * c.n_put_oi::numeric / NULLIF(c.n_strikes, 0)::numeric, 1) AS put_oi_coverage_pct
           FROM pain p
             JOIN argmin a USING (symbol, run_id, expiry_date)
             JOIN cohort c USING (symbol, run_id, expiry_date)
     ), old_body AS (
         SELECT symbol, run_id, ts, expiry_date, dte, candidate_strike, total_pain, max_pain_strike, max_pain_value, side,
                n_strikes, call_oi_coverage_pct, put_oi_coverage_pct
           FROM v_gex_max_pain
     )
SELECT (SELECT count(*) FROM (SELECT * FROM new_body EXCEPT SELECT * FROM old_body) x) AS only_in_new,
       (SELECT count(*) FROM (SELECT * FROM old_body EXCEPT SELECT * FROM new_body) y) AS only_in_old,
       (SELECT count(*) FROM new_body) AS n_new,
       (SELECT count(*) FROM old_body) AS n_old;

-- =====================================================================  T1b -- equality: new strike_step CTE vs the live v_gex_pin_maxpain
-- The only change in v_gex_pin_maxpain is its own latest_run (feeding steps.strike_step); the rest joins views unchanged here.
-- PASS: one row, only_in_new = 0, only_in_old = 0, n > 0.
WITH RECURSIVE symbols AS (
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g) AS symbol
        UNION ALL
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g WHERE g.symbol > s.symbol)
          FROM symbols s WHERE s.symbol IS NOT NULL
     ), latest_run AS (
        SELECT s.symbol, lr.ts, lr.run_id
          FROM symbols s
          CROSS JOIN LATERAL (SELECT g.ts, g.run_id FROM gex_strike_snapshots g
                               WHERE g.symbol = s.symbol ORDER BY g.ts DESC LIMIT 1) lr
         WHERE s.symbol IS NOT NULL
     ), scoped AS (
         SELECT g.symbol, g.run_id, g.expiry_date, g.strike
           FROM gex_strike_snapshots g
             JOIN latest_run l ON l.symbol = g.symbol AND l.ts = g.ts AND l.run_id = g.run_id
     ), new_steps AS (
         SELECT x.symbol, x.run_id, x.expiry_date, min(x.d) AS strike_step
           FROM (SELECT scoped.symbol, scoped.run_id, scoped.expiry_date,
                        scoped.strike - lag(scoped.strike) OVER (PARTITION BY scoped.symbol, scoped.run_id, scoped.expiry_date ORDER BY scoped.strike) AS d
                   FROM scoped) x
          WHERE x.d > 0::numeric
          GROUP BY x.symbol, x.run_id, x.expiry_date
     ), old_steps AS (
         SELECT symbol, run_id, expiry_date, strike_step FROM v_gex_pin_maxpain
     )
SELECT (SELECT count(*) FROM (SELECT * FROM new_steps EXCEPT SELECT * FROM old_steps) x) AS only_in_new,
       (SELECT count(*) FROM (SELECT * FROM old_steps EXCEPT SELECT * FROM new_steps) y) AS only_in_old,
       (SELECT count(*) FROM new_steps) AS n;

-- =====================================================================  BLOCK 1 -- one execution
CREATE OR REPLACE VIEW public.v_gex_max_pain AS
 WITH RECURSIVE symbols AS (
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g) AS symbol
        UNION ALL
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g WHERE g.symbol > s.symbol)
          FROM symbols s WHERE s.symbol IS NOT NULL
     ), latest_run AS (
        SELECT s.symbol, lr.ts, lr.run_id
          FROM symbols s
          CROSS JOIN LATERAL (SELECT g.ts, g.run_id FROM gex_strike_snapshots g
                               WHERE g.symbol = s.symbol ORDER BY g.ts DESC LIMIT 1) lr
         WHERE s.symbol IS NOT NULL
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

CREATE OR REPLACE VIEW public.v_gex_pin_maxpain AS
 WITH RECURSIVE symbols AS (
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g) AS symbol
        UNION ALL
        SELECT (SELECT min(g.symbol) FROM gex_strike_snapshots g WHERE g.symbol > s.symbol)
          FROM symbols s WHERE s.symbol IS NOT NULL
     ), latest_run AS (
        SELECT s.symbol, lr.ts, lr.run_id
          FROM symbols s
          CROSS JOIN LATERAL (SELECT g.ts, g.run_id FROM gex_strike_snapshots g
                               WHERE g.symbol = s.symbol ORDER BY g.ts DESC LIMIT 1) lr
         WHERE s.symbol IS NOT NULL
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

COMMENT ON VIEW public.v_gex_max_pain IS
  'ENH-123 (S80). Max pain over gex_strike_snapshots, scoped per '
  '(symbol, run_id, expiry_date), emitting ts/dte/coverage/freshness. '
  'Distinct from v_max_pain_by_strike (S40), which is chain-based, has no '
  'expiry filter and emits no timestamp. Both are live. Extension (L19), '
  'not a parity layer -- ADR-025 D5. S103 (ruling S103-F, 2026-10-30): latest_run is the S79 '
  'skip-scan + LATERAL shape (O(symbols) index seeks), replacing DISTINCT ON over the full '
  'index that timed out at 8 s (TD-S90-NEW-5, TD-S101-NEW-1). Output unchanged.';

COMMENT ON VIEW public.v_gex_pin_maxpain IS
  'ENH-124 (S80). Distance between max pain (ENH-123) and peak gamma '
  '(ENH-81), in points, strikes and sigma, with band/corridor tests. Emits a '
  'distance, never a verdict -- no tolerance constant, per TD-S79-NEW-21. '
  'History: the gap is a stable -0.4 sigma across both symbols, all DTE and '
  'all session hours. Extension (L19), not a parity layer -- ADR-025 D5. S103 (ruling S103-F, '
  '2026-10-30): latest_run is the S79 skip-scan + LATERAL shape; output unchanged.';

-- =====================================================================  T2 -- the live view, read as the writer reads it
-- PASS: Execution Time under 1,000 ms (was 17,891 ms at 17:55 IST), and the plan contains no Unique over a full index scan.
EXPLAIN (ANALYZE, BUFFERS, SUMMARY)
SELECT max_pain_strike, snapshot_age_min, is_fresh
FROM v_gex_max_pain
WHERE symbol = 'NIFTY'
ORDER BY ts DESC
LIMIT 1;

-- =====================================================================  T3 -- register the live definitions (rule 25; contract section 8)
-- PASS: two rows; both lengths and md5s differ from the S80 values quoted in the header; paste them into the contract.
SELECT v, length(d) AS len, md5(d),
       has_table_privilege('anon', ('public.' || v)::regclass, 'SELECT') AS anon_sel,
       has_table_privilege('merdian_ro', ('public.' || v)::regclass, 'SELECT') AS ro_sel
FROM (SELECT v, pg_get_viewdef(('public.' || v)::regclass, true) AS d
      FROM unnest(ARRAY['v_gex_max_pain','v_gex_pin_maxpain']) AS v) s;
