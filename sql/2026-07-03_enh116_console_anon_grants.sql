-- ============================================================================
-- ENH-116 step 5 prereq — anon read access for the Marketview ambient console
-- ----------------------------------------------------------------------------
-- Session : S64 (2026-07-03)
-- Pattern : S39 security-first quadruplet (D.21.1) — REVOKE ALL → ENABLE RLS →
--           CREATE POLICY FOR SELECT → GRANT SELECT. Lovable auto-grants anon ALL
--           privileges; the REVOKE ALL is the load-bearing step, not the grant.
--           Service-role writers (compiler / seed / labeler / ingest) bypass RLS,
--           so this restricts ONLY the public anon key to read-only.
-- Idempotent: drop-policy-if-exists before create; safe to re-run.
-- ============================================================================

-- ── market_environment_snapshots (verdict + four lenses) ───────────────────
revoke all on public.market_environment_snapshots from anon;
alter table public.market_environment_snapshots enable row level security;
drop policy if exists anon_select_mes on public.market_environment_snapshots;
create policy anon_select_mes
    on public.market_environment_snapshots for select to anon using (true);
grant select on public.market_environment_snapshots to anon;

-- ── expiry_outcomes (underlying table of v_expiry_base_rates) ──────────────
revoke all on public.expiry_outcomes from anon;
alter table public.expiry_outcomes enable row level security;
drop policy if exists anon_select_expiry_outcomes on public.expiry_outcomes;
create policy anon_select_expiry_outcomes
    on public.expiry_outcomes for select to anon using (true);
grant select on public.expiry_outcomes to anon;

-- ── v_expiry_base_rates ────────────────────────────────────────────────────
-- REVOKE ALL first: the view carried a full anon grant (INSERT/UPDATE/DELETE/
-- TRUNCATE/REFERENCES/TRIGGER) surfaced by the S39 audit; a bare add-grant can't
-- remove them. (Writes error anyway on this GROUP BY view, but the drift shouldn't stand.)
revoke all on public.v_expiry_base_rates from anon;
grant select on public.v_expiry_base_rates to anon;

-- ── post-deploy audit: anon must be SELECT-only on all three surfaces ──────
-- Expect exactly one 'SELECT' row per surface, nothing else.
--   select table_name, privilege_type
--   from information_schema.role_table_grants
--   where grantee = 'anon'
--     and table_name in ('market_environment_snapshots','expiry_outcomes','v_expiry_base_rates')
--   order by table_name, privilege_type;
