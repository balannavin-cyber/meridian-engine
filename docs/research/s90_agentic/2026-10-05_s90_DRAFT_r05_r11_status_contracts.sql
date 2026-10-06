-- =====================================================================
-- DRAFT — NOT FOR APPLY. S90 R0.5 (status enum + lineage) and R1.1
-- (data_contracts registry) + the cycle_health sink R1.2 will write.
-- Governing draft: claude/ADR-031-DRAFT-spine-contracts-status-provenance-ledger.md
-- Apply only after ruling A-8 (spine ADR) and A-5 (scope). Risk class SC:
-- new tables only, live path untouched, nothing reads them until shadow ends.
-- Seed numbers are PROPOSALS for ruling A-11, taken from P4 (2026-10-05).
-- Access per ADR-031 D6: RLS ON + merdian_ro read policy, anon/authenticated
-- revoked, written by service_role only. Post-apply access check required.
-- =====================================================================
BEGIN;

-- ---------- R0.5: one status vocabulary (ADR-031 D2) ----------
CREATE TYPE public.merdian_status AS ENUM
  ('OK', 'DEGRADED', 'STALE', 'MISSING', 'CLOSED', 'NOT_COMPUTED', 'UNKNOWN');
COMMENT ON TYPE public.merdian_status IS
  'ADR-031 D2. Propagation = worst of own and required inputs, CLOSED excluded. Order MISSING > NOT_COMPUTED > STALE > UNKNOWN > DEGRADED > OK. UNKNOWN = no fresh status; never rendered as OK.';

-- ---------- R1.1: contract registry (ADR-031 D1) ----------
CREATE TABLE public.data_contracts (
  product              text PRIMARY KEY,             -- '<relation>:<scope>'
  relation_name        text NOT NULL,
  scope_symbol         text,                         -- NULL = not per-symbol
  scope_col            text,                         -- column holding the symbol ('symbol', 'index_symbol'); NULL with scope_symbol NULL
  time_col             text NOT NULL DEFAULT 'ts',   -- 'ts', or 'trade_date' for daily products
  grain                text[] NOT NULL,
  cadence_min          integer NOT NULL CHECK (cadence_min > 0),
  freshness_sla_min    integer NOT NULL CHECK (freshness_sla_min > 0),  -- consumer cadence (ADR-023 A1.2)
  expected_per_cycle   jsonb NOT NULL DEFAULT '{}'::jsonb,              -- e.g. {"rows":[700,1100],"expiries":[2,2]}
  movement_cols        text[] NOT NULL DEFAULT '{}',                    -- must change within movement_window_cycles
  movement_window_cycles integer NOT NULL DEFAULT 3 CHECK (movement_window_cycles >= 1),
  calendar             text NOT NULL DEFAULT 'NSE_FO',
  tier                 smallint NOT NULL CHECK (tier IN (1, 2, 3)),     -- core / context / research
  writer               text,
  owner                text NOT NULL DEFAULT 'operator',
  access_rls           text NOT NULL CHECK (access_rls IN ('ENABLED_WITH_RO_POLICY', 'DISABLED_BY_DESIGN', 'UNVERIFIED')),
  valid_from           timestamptz NOT NULL DEFAULT now(),
  valid_to             timestamptz,
  change_reason        text NOT NULL CHECK (length(change_reason) > 0)
);
COMMENT ON TABLE public.data_contracts IS
  'ADR-031 D1. One row per data product. Checks are generated from these rows by one runner; no hand-written per-table checks. Freshness = worst of own ts and required inputs (product_lineage), plus movement_cols. Thresholds are proposals until ruling A-11.';

CREATE TABLE public.product_lineage (
  product   text NOT NULL REFERENCES public.data_contracts(product),
  requires  text NOT NULL REFERENCES public.data_contracts(product),
  PRIMARY KEY (product, requires),
  CHECK (product <> requires)
);
COMMENT ON TABLE public.product_lineage IS 'ADR-031 D1/D2. Required inputs per product; status propagates along these edges.';

-- ---------- R1.2 sink: one status per product per cycle (write-and-flag) ----------
CREATE TABLE public.cycle_health (
  product          text NOT NULL REFERENCES public.data_contracts(product),
  cycle_ts         timestamptz NOT NULL,
  status           public.merdian_status NOT NULL,
  reason           text,                          -- required when status <> 'OK'
  checks           jsonb NOT NULL DEFAULT '{}'::jsonb,  -- per-check results
  run_id           uuid,
  checker_version  text NOT NULL,                 -- code_sha of the runner (ADR-031 D3)
  created_at       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (product, cycle_ts),
  CHECK (status = 'OK' OR reason IS NOT NULL)
);
CREATE INDEX ix_cycle_health_ts ON public.cycle_health (cycle_ts DESC);
COMMENT ON TABLE public.cycle_health IS
  'ADR-031 D2. Written by the R1.2 runner every cycle in shadow, including CLOSED and MISSING rows (write-and-flag, ADR-030). Nothing reads it until the shadow period ends.';

-- ---------- Access (ADR-031 D6) ----------
ALTER TABLE public.data_contracts  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.product_lineage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cycle_health    ENABLE ROW LEVEL SECURITY;
CREATE POLICY data_contracts_ro  ON public.data_contracts  FOR SELECT TO merdian_ro USING (true);
CREATE POLICY product_lineage_ro ON public.product_lineage FOR SELECT TO merdian_ro USING (true);
CREATE POLICY cycle_health_ro    ON public.cycle_health    FOR SELECT TO merdian_ro USING (true);
REVOKE ALL ON public.data_contracts, public.product_lineage, public.cycle_health FROM anon, authenticated;
GRANT SELECT ON public.data_contracts, public.product_lineage, public.cycle_health TO merdian_ro;

-- ---------- Seed: core products (proposals, from P4 2026-10-05) ----------
INSERT INTO public.data_contracts
  (product, relation_name, scope_symbol, scope_col, time_col, grain, cadence_min, freshness_sla_min, expected_per_cycle, movement_cols, calendar, tier, writer, access_rls, change_reason)
VALUES
  ('option_chain_snapshots:NIFTY',  'option_chain_snapshots', 'NIFTY', 'symbol', 'ts',  '{run_id,strike,option_type}', 5, 10, '{"rows":[800,1100],"expiries":[2,2]}', '{spot}', 'NSE_FO', 1, 'ingest_option_chain_local.py', 'UNVERIFIED', 'S90 seed from P4: 79-88k rows/day, 83-87 ts'),
  ('option_chain_snapshots:SENSEX', 'option_chain_snapshots', 'SENSEX', 'symbol', 'ts', '{run_id,strike,option_type}', 5, 10, '{"rows":[650,900],"expiries":[2,2]}',  '{spot}', 'BSE_FO', 1, 'ingest_option_chain_local.py', 'UNVERIFIED', 'S90 seed from P4: 62-67k rows/day'),
  ('market_spot_snapshots:NIFTY',   'market_spot_snapshots',  'NIFTY', 'symbol', 'ts',  '{symbol,ts,source_table}', 1, 5, '{"rows":[1,1]}', '{spot}', 'NSE_FO', 1, 'capture_spot_1m_v2.py', 'UNVERIFIED', 'S90 seed from P4: 360 rows/day 09:16-15:15'),
  ('market_spot_snapshots:SENSEX',  'market_spot_snapshots',  'SENSEX', 'symbol', 'ts', '{symbol,ts,source_table}', 1, 5, '{"rows":[1,1]}', '{spot}', 'BSE_FO', 1, 'capture_spot_1m_v2.py', 'UNVERIFIED', 'S90 seed from P4'),
  ('gex_strike_snapshots:NIFTY',    'gex_strike_snapshots',   'NIFTY', 'symbol', 'ts',  '{run_id,strike,expiry_date}', 5, 10, '{"rows":[90,160],"expiries":[1,1]}', '{gex_cr}', 'NSE_FO', 1, 'compute_gamma_metrics_local.py', 'UNVERIFIED', 'S90 seed from P4: 8.7-11.9k rows/day, 80-84 runs'),
  ('gex_strike_snapshots:SENSEX',   'gex_strike_snapshots',   'SENSEX', 'symbol', 'ts', '{run_id,strike,expiry_date}', 5, 10, '{"rows":[110,170],"expiries":[1,1]}', '{gex_cr}', 'BSE_FO', 1, 'compute_gamma_metrics_local.py', 'UNVERIFIED', 'S90 seed from P4'),
  ('gamma_metrics:NIFTY',           'gamma_metrics',          'NIFTY', 'symbol', 'ts',  '{symbol,ts}', 5, 10, '{"rows":[1,1],"expiries":[1,1]}', '{net_gex,spot}', 'NSE_FO', 1, 'compute_gamma_metrics_local.py', 'UNVERIFIED', 'S90 seed: UNIQUE (symbol, ts), W1 only (S90-B)'),
  ('gamma_metrics:SENSEX',          'gamma_metrics',          'SENSEX', 'symbol', 'ts', '{symbol,ts}', 5, 10, '{"rows":[1,1],"expiries":[1,1]}', '{net_gex,spot}', 'BSE_FO', 1, 'compute_gamma_metrics_local.py', 'UNVERIFIED', 'S90 seed'),
  ('equity_intraday_last:ALL',      'equity_intraday_last',   NULL, NULL, 'ts',     '{ticker}', 1440, 1440, '{"rows":[1200,1400]}', '{}', 'NSE_FO', 2, 'refresh_equity_intraday_last.py', 'UNVERIFIED', 'S90 seed: once daily 09:05 IST, holds PRIOR CLOSE (R01-F9)'),
  ('breadth_indicators_daily:ALL',  'breadth_indicators_daily', NULL, NULL, 'trade_date',   '{ticker,trade_date}', 1440, 2880, '{"rows":[1200,1400]}', '{}', 'NSE_FO', 2, 'run_equity_eod_until_done.py', 'UNVERIFIED', 'S90 seed: frontier stalled at 2026-09-29 (R01-F9) - would read MISSING today (4 trading days behind, SLA 2)'),
  ('weighted_constituent_breadth_snapshots:NIFTY',  'weighted_constituent_breadth_snapshots', 'NIFTY', 'index_symbol', 'ts',  '{index_symbol,ts}', 5, 10, '{"rows":[1,1]}', '{wcb_score,weighted_advances_pct}', 'NSE_FO', 2, 'build_wcb_snapshot_local.py', 'UNVERIFIED', 'S90 seed: values frozen since 2026-10-01 15:40 (MV-9) - would read STALE today (own movement + input)'),
  ('weighted_constituent_breadth_snapshots:SENSEX', 'weighted_constituent_breadth_snapshots', 'SENSEX', 'index_symbol', 'ts', '{index_symbol,ts}', 5, 10, '{"rows":[1,1]}', '{wcb_score,weighted_advances_pct}', 'BSE_FO', 2, 'build_wcb_snapshot_local.py', 'UNVERIFIED', 'S90 seed'),
  ('gex_cycle_history:NIFTY',       'gex_cycle_history',      'NIFTY', 'symbol', 'ts',  '{symbol,expiry_date,ts}', 5, 10, '{"rows":[1,1]}', '{}', 'NSE_FO', 1, 'write_gex_cycle_history_local.py (not wired, S90-A)', 'DISABLED_BY_DESIGN', 'S90 seed: applied 2026-10-05, writer not wired - would read MISSING until it is'),
  ('gex_cycle_history:SENSEX',      'gex_cycle_history',      'SENSEX', 'symbol', 'ts', '{symbol,expiry_date,ts}', 5, 10, '{"rows":[1,1]}', '{}', 'BSE_FO', 1, 'write_gex_cycle_history_local.py (not wired, S90-A)', 'DISABLED_BY_DESIGN', 'S90 seed');

INSERT INTO public.product_lineage (product, requires) VALUES
  ('gex_strike_snapshots:NIFTY',  'option_chain_snapshots:NIFTY'),
  ('gex_strike_snapshots:SENSEX', 'option_chain_snapshots:SENSEX'),
  ('gamma_metrics:NIFTY',         'option_chain_snapshots:NIFTY'),
  ('gamma_metrics:SENSEX',        'option_chain_snapshots:SENSEX'),
  ('weighted_constituent_breadth_snapshots:NIFTY',  'equity_intraday_last:ALL'),
  ('weighted_constituent_breadth_snapshots:NIFTY',  'breadth_indicators_daily:ALL'),
  ('weighted_constituent_breadth_snapshots:SENSEX', 'equity_intraday_last:ALL'),
  ('weighted_constituent_breadth_snapshots:SENSEX', 'breadth_indicators_daily:ALL'),
  ('gex_cycle_history:NIFTY',  'gamma_metrics:NIFTY'),
  ('gex_cycle_history:NIFTY',  'gex_strike_snapshots:NIFTY'),
  ('gex_cycle_history:SENSEX', 'gamma_metrics:SENSEX'),
  ('gex_cycle_history:SENSEX', 'gex_strike_snapshots:SENSEX');

COMMIT;

-- Post-apply access check (ADR-031 D6), run as postgres in the same session:
SELECT c.relname, c.relrowsecurity AS rls_on,
       (SELECT count(*) FROM pg_policy p WHERE p.polrelid = c.oid) AS n_policies,
       c.relacl::text AS acl
FROM pg_class c
WHERE c.oid IN ('public.data_contracts'::regclass, 'public.product_lineage'::regclass, 'public.cycle_health'::regclass)
ORDER BY 1;
