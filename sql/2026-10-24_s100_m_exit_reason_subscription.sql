-- S100-M (b) (2026-10-24, operator, Supabase SQL editor): add SUBSCRIPTION_LAPSED to chk_exit_reason_valid -- a Dhan
-- 806 / DH-902 data-plan lapse, logged as TOKEN_EXPIRED before (10-21: capture_spot_1m_v2.py 360, ingest_option_chain_local.py
-- 174, capture_cas_close.py 1). Widening only: every existing row still satisfies the new CHECK. Applied BEFORE the code
-- (an unknown reason is coerced to CRASH by core.execution_log, and a row the CHECK refuses is lost).
-- The array below must equal core/execution_log.py VALID_EXIT_REASONS (tests/test_subscription_lapsed.py C7).
BEGIN;
ALTER TABLE public.script_execution_log DROP CONSTRAINT chk_exit_reason_valid;
ALTER TABLE public.script_execution_log ADD CONSTRAINT chk_exit_reason_valid CHECK (exit_reason = ANY (ARRAY[
  'SUCCESS','HOLIDAY_GATE','OFF_HOURS','TOKEN_EXPIRED','SUBSCRIPTION_LAPSED','DATA_ERROR','SKIPPED_NO_INPUT',
  'DEPENDENCY_MISSING','CRASH','TIMEOUT','RUNNING','DRY_RUN']::text[]));
COMMIT;
SELECT pg_get_constraintdef(oid) LIKE '%SUBSCRIPTION_LAPSED%' AS has_new_reason,
       pg_get_constraintdef(oid) LIKE '%TOKEN_EXPIRED%' AS kept_token_expired
  FROM pg_constraint WHERE conrelid = 'public.script_execution_log'::regclass AND conname = 'chk_exit_reason_valid';
