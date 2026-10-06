-- S90 R0.4 — ENH-133 post-apply acceptance, roq.sh form (merdian_ro, read-only).
-- RUN ONLY AFTER the operator has applied sql/2026-10-03_s89_gex_cycle_history.sql.
-- Run:  bin/roq.sh scratch/s90/p2_enh133_acceptance_s90.sql > scratch/s90/p2_enh133_acceptance_s90.out 2>&1
-- Each block states, in its header, what would make it FAIL.
\pset pager off
\pset null '(null)'
SELECT current_user AS role_now, now() AS probed_at;

-- ===== X1. Table exists. FAILS if the apply did not land. ================
SELECT to_regclass('public.gex_cycle_history') IS NOT NULL AS table_exists;

-- ===== X2. Column set equals the DDL (40 columns, names + types; S90 corrected from 35 — the 35 is the bound-source count). =========
-- FAILS if a column is missing, renamed or retyped. Expected count is from the
-- DDL file literal (40, counted by pglast from sql/2026-10-03_s89_gex_cycle_history.sql), not from running this query.
SELECT count(*) AS n_columns,
       count(*) = 40 AS matches_ddl_40
FROM information_schema.columns
WHERE table_schema='public' AND table_name='gex_cycle_history';
SELECT ordinal_position, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema='public' AND table_name='gex_cycle_history'
ORDER BY ordinal_position;

-- ===== X3. Key, checks, indexes. FAILS if PK is not (symbol,expiry_date,ts) =
SELECT conname, pg_get_constraintdef(oid) AS def
FROM pg_constraint WHERE conrelid = to_regclass('public.gex_cycle_history')
ORDER BY conname;
SELECT indexrelid::regclass AS index_name, pg_get_indexdef(indexrelid) AS def
FROM pg_index WHERE indrelid = to_regclass('public.gex_cycle_history');

-- ===== X4. Access boundary (roadmap §11.1 risk 3). =======================
-- FAILS if merdian_ro cannot read, or anon holds ANY privilege (the S39->S81
-- default-privileges shape), or RLS is on with zero policies (silent empty).
SELECT c.relacl::text AS relacl,
       has_table_privilege('merdian_ro', c.oid, 'SELECT') AS ro_select,
       has_table_privilege('anon', c.oid, 'SELECT')  AS anon_select,
       has_table_privilege('anon', c.oid, 'INSERT')  AS anon_insert,
       has_table_privilege('anon', c.oid, 'UPDATE')  AS anon_update,
       has_table_privilege('anon', c.oid, 'DELETE')  AS anon_delete,
       c.relrowsecurity AS rls_on,
       (SELECT count(*) FROM pg_policy p WHERE p.polrelid = c.oid) AS n_policies
FROM pg_class c WHERE c.oid = to_regclass('public.gex_cycle_history');

-- ===== X5. COMMENTs applied live (S81 rule; TD-S84-NEW-3 shape). =========
-- FAILS if the table COMMENT or any of the 16 column COMMENTs is absent.
SELECT obj_description(to_regclass('public.gex_cycle_history'), 'pg_class') IS NOT NULL AS table_comment_present,
       length(obj_description(to_regclass('public.gex_cycle_history'), 'pg_class')) AS table_comment_len;
SELECT a.attname, col_description(a.attrelid, a.attnum) IS NOT NULL AS has_comment
FROM pg_attribute a
WHERE a.attrelid = to_regclass('public.gex_cycle_history')
  AND a.attname IN ('dte','conc_top1_share','conc_top1_share_call','conc_top1_share_put',
       'conc_hhi','repriced_flip_level','repriced_flip_ts','session_gate_state',
       'session_gate_ticks','held_for_cycles','pin_state','conviction','reconciled_at',
       'reconciler_version','conviction_reason','is_fresh')
ORDER BY a.attname;

-- ===== A(a). Every bound source (relation, column) exists BY NAME. =======
-- FAILS on any row with exists = false. 35 pairs, copied from
-- acceptance_enh133_local.py BOUND_SOURCES; information_schema covers views.
WITH b(rel, col) AS (VALUES
 ('gamma_metrics','symbol'),('gamma_metrics','expiry_date'),('gamma_metrics','ts'),
 ('gamma_metrics','run_id'),('gamma_metrics','dte'),('gamma_metrics','spot'),
 ('gamma_metrics','net_gex'),('gamma_metrics','regime'),('gamma_metrics','flip_level'),
 ('option_chain_snapshots','run_id'),('option_chain_snapshots','ts'),
 ('volatility_snapshots','source_run_id'),('volatility_snapshots','atm_iv_avg'),
 ('v_gex_strike_rank','strike_rank'),('v_gex_strike_rank','strike'),
 ('v_gex_strike_rank','gex_cr'),('v_gex_strike_rank','share_of_abs'),
 ('v_gex_strike_rank','cum_share_of_abs'),('v_gex_strike_rank','n_ranked'),
 ('v_gex_concentration','hhi_net'),('v_gex_concentration','hhi_call'),
 ('v_gex_concentration','hhi_put'),
 ('v_gex_max_pain','max_pain_strike'),('v_gex_max_pain','is_fresh'),
 ('v_gex_max_pain','snapshot_age_min'),
 ('v_gex_pin_maxpain','is_fresh'),('v_gex_pin_maxpain','snapshot_age_min'),
 ('v_gex_strike_walls','call_wall'),('v_gex_strike_walls','put_wall'),
 ('v_gex_repriced_flip','ts'),('v_gex_repriced_flip','front_expiry'),
 ('v_gex_repriced_flip','flip'),
 ('market_spot_snapshots','symbol'),('market_spot_snapshots','ts'),
 ('market_spot_snapshots','spot'))
SELECT b.rel, b.col,
       EXISTS (SELECT 1 FROM information_schema.columns c
               WHERE c.table_schema='public' AND c.table_name=b.rel AND c.column_name=b.col) AS exists
FROM b ORDER BY exists, b.rel, b.col;
-- 35 pairs, equal to acceptance_enh133_local.py BOUND_SOURCES (counted).

-- ===== G2-forward. Per-symbol coverage, FORWARD ONLY. ====================
-- The script's G2 compares against EVERY gamma_metrics ts ever, which a
-- forward-only table fails by construction. This form starts at the table's
-- first row. FAILS if any gamma ts at/after that point is missing a row.
-- With the writer NOT wired, expect first_hist_ts = (null): reported, not passed.
WITH f AS (SELECT min(ts) AS first_ts FROM public.gex_cycle_history),
     want AS (SELECT DISTINCT g.symbol, g.ts FROM public.gamma_metrics g, f
              WHERE f.first_ts IS NOT NULL AND g.ts >= f.first_ts),
     have AS (SELECT DISTINCT symbol, ts FROM public.gex_cycle_history)
SELECT (SELECT first_ts FROM f) AS first_hist_ts,
       w.symbol, count(*) AS gamma_ts, count(h.ts) AS hist_ts,
       count(*) - count(h.ts) AS missing
FROM want w LEFT JOIN have h USING (symbol, ts)
GROUP BY w.symbol ORDER BY w.symbol;
SELECT count(*) AS hist_rows_total, count(DISTINCT symbol) AS symbols,
       count(DISTINCT expiry_date) AS expiries, min(ts) AS first_ts, max(ts) AS last_ts
FROM public.gex_cycle_history;

-- ===== Legs per (symbol, ts) in gamma_metrics — tests the "both legs" premise.
-- If max_legs = 1 everywhere, gex_cycle_history can only ever hold the front
-- leg, against ADR-030 D1. Bounded to the last 3 trading days.
SELECT symbol, max(legs) AS max_legs, min(legs) AS min_legs, count(*) AS cycles
FROM (SELECT symbol, ts, count(DISTINCT expiry_date) AS legs
      FROM public.gamma_metrics
      WHERE ts >= now() - interval '4 days'
      GROUP BY symbol, ts) x
GROUP BY symbol ORDER BY symbol;
