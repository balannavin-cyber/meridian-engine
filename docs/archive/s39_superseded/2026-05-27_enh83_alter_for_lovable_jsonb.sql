-- ============================================================================
-- ENH-83 / ADR-016 — ALTER existing merdian_parameters (Lovable's jsonb schema)
-- Session 39 / 2026-05-27
--
-- Lovable auto-provisioned merdian_parameters with single `value jsonb` column
-- after seeing ADR-016 referenced in our build prompt. The 11 bootstrap rows
-- are already present. This script:
--   1. Adds the CHECK constraints ADR-016 requires (change_reason non-empty,
--      value_type whitelist, valid_to > valid_from).
--   2. Adds the unique partial index ("at most one active row per key").
--   3. Creates the typed read RPCs (get_parameter_num/text/bool) — parse
--      jsonb at query time via #>> '{}' then cast.
--   4. Creates the write RPC update_parameter taking jsonb input — atomic
--      close-old + insert-new, SECURITY DEFINER so anon can invoke without
--      direct INSERT/UPDATE grants.
--   5. Creates the v_merdian_parameter_audit reverse-chronological view.
--   6. Applies RLS triplet for anon SELECT.
--
-- All idempotent. Safe to re-run. Preserves existing data.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. CHECK constraints (ADR-016 contract enforcement at DB layer)
-- ---------------------------------------------------------------------------

DO $$
BEGIN
    -- change_reason non-empty
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_change_reason_nonempty'
          AND conrelid = 'public.merdian_parameters'::regclass
    ) THEN
        ALTER TABLE public.merdian_parameters
            ADD CONSTRAINT chk_change_reason_nonempty
            CHECK (length(btrim(change_reason)) > 0);
    END IF;

    -- value_type whitelist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_value_type_valid'
          AND conrelid = 'public.merdian_parameters'::regclass
    ) THEN
        ALTER TABLE public.merdian_parameters
            ADD CONSTRAINT chk_value_type_valid
            CHECK (value_type IN ('numeric', 'text', 'boolean', 'jsonb'));
    END IF;

    -- valid_to > valid_from
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_valid_from_to'
          AND conrelid = 'public.merdian_parameters'::regclass
    ) THEN
        ALTER TABLE public.merdian_parameters
            ADD CONSTRAINT chk_valid_from_to
            CHECK (valid_to IS NULL OR valid_to > valid_from);
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- 2. Indexes
-- ---------------------------------------------------------------------------

CREATE UNIQUE INDEX IF NOT EXISTS uniq_merdian_parameters_active_key
    ON public.merdian_parameters (key)
    WHERE valid_to IS NULL;

CREATE INDEX IF NOT EXISTS idx_merdian_parameters_key_valid_from
    ON public.merdian_parameters (key, valid_from DESC);

CREATE INDEX IF NOT EXISTS idx_merdian_parameters_category
    ON public.merdian_parameters (category);

-- ---------------------------------------------------------------------------
-- 3. Typed read RPCs — parse value jsonb at query time
--    `#>> '{}'` extracts the scalar as text (strips JSON quoting for strings).
-- ---------------------------------------------------------------------------

DROP FUNCTION IF EXISTS public.get_parameter_num(text)  CASCADE;
DROP FUNCTION IF EXISTS public.get_parameter_text(text) CASCADE;
DROP FUNCTION IF EXISTS public.get_parameter_bool(text) CASCADE;

CREATE OR REPLACE FUNCTION public.get_parameter_num(p_key text)
RETURNS numeric
LANGUAGE sql STABLE
AS $$
    SELECT (value #>> '{}')::numeric
    FROM public.merdian_parameters
    WHERE key = p_key AND valid_to IS NULL AND value_type = 'numeric'
    LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION public.get_parameter_text(p_key text)
RETURNS text
LANGUAGE sql STABLE
AS $$
    SELECT (value #>> '{}')
    FROM public.merdian_parameters
    WHERE key = p_key AND valid_to IS NULL AND value_type = 'text'
    LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION public.get_parameter_bool(p_key text)
RETURNS boolean
LANGUAGE sql STABLE
AS $$
    SELECT (value #>> '{}')::boolean
    FROM public.merdian_parameters
    WHERE key = p_key AND valid_to IS NULL AND value_type = 'boolean'
    LIMIT 1;
$$;

COMMENT ON FUNCTION public.get_parameter_num(text) IS
    'Canonical typed read API for numeric parameters per ADR-016. Consumed by ENH-81 views v_gex_strike_pin_zone + v_gex_strike_accel_zone — closes TD-S37-01.';

-- ---------------------------------------------------------------------------
-- 4. update_parameter RPC — atomic close-old + insert-new, jsonb value input
--    SECURITY DEFINER allows anon role to invoke without direct INSERT grant.
--    Serialization via FOR UPDATE lock on the active row.
-- ---------------------------------------------------------------------------

DROP FUNCTION IF EXISTS public.update_parameter(text, jsonb, text, text) CASCADE;

CREATE OR REPLACE FUNCTION public.update_parameter(
    p_key           text,
    p_value         jsonb,
    p_change_reason text,
    p_changed_by    text DEFAULT 'operator'
) RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_old    public.merdian_parameters%ROWTYPE;
    v_new_id uuid;
    v_num    numeric;
BEGIN
    -- ADR-016 contract: change_reason mandatory
    IF p_change_reason IS NULL OR length(btrim(p_change_reason)) = 0 THEN
        RAISE EXCEPTION 'change_reason is required (ADR-016 architectural contract)';
    END IF;

    -- Lock the currently-active row for this key
    SELECT * INTO v_old
    FROM public.merdian_parameters
    WHERE key = p_key AND valid_to IS NULL
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'parameter % not found or already closed', p_key;
    END IF;

    -- Range check for numeric type
    IF v_old.value_type = 'numeric' THEN
        v_num := (p_value #>> '{}')::numeric;
        IF v_old.min_value IS NOT NULL AND v_num < v_old.min_value THEN
            RAISE EXCEPTION 'value % below min_value % for key %', v_num, v_old.min_value, p_key;
        END IF;
        IF v_old.max_value IS NOT NULL AND v_num > v_old.max_value THEN
            RAISE EXCEPTION 'value % above max_value % for key %', v_num, v_old.max_value, p_key;
        END IF;
    END IF;

    -- Close the existing active row
    UPDATE public.merdian_parameters
    SET valid_to = now()
    WHERE id = v_old.id;

    -- Insert new active row carrying forward all metadata except the value + audit fields
    INSERT INTO public.merdian_parameters (
        key, value, value_type, category, description,
        min_value, max_value, valid_from, changed_by, change_reason
    ) VALUES (
        p_key, p_value, v_old.value_type, v_old.category, v_old.description,
        v_old.min_value, v_old.max_value, now(), p_changed_by, p_change_reason
    ) RETURNING id INTO v_new_id;

    RETURN v_new_id;
END;
$$;

COMMENT ON FUNCTION public.update_parameter(text, jsonb, text, text) IS
    'Canonical write API for merdian_parameters per ADR-016. Atomically closes the active row and inserts a new active row. SECURITY DEFINER so anon role can invoke without direct INSERT grant. Enforces change_reason + numeric range bounds.';

GRANT EXECUTE ON FUNCTION public.update_parameter(text, jsonb, text, text) TO anon;

-- ---------------------------------------------------------------------------
-- 5. Audit log view — reverse-chronological surface for Settings footer link
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW public.v_merdian_parameter_audit AS
SELECT
    id,
    key,
    category,
    value_type,
    (value #>> '{}')                                                       AS value_display,
    valid_from,
    valid_to,
    CASE WHEN valid_to IS NULL THEN 'ACTIVE' ELSE 'CLOSED' END              AS lifecycle,
    changed_by,
    change_reason,
    created_at
FROM public.merdian_parameters
ORDER BY valid_from DESC, created_at DESC;

COMMENT ON VIEW public.v_merdian_parameter_audit IS
    'Reverse-chronological audit log of every parameter write. Consumed by Settings → Calibration audit-log footer link per ENH-110 Appendix B.';

-- ---------------------------------------------------------------------------
-- 6. RLS triplet (TD-S37-03 mitigation pattern)
-- ---------------------------------------------------------------------------

ALTER TABLE public.merdian_parameters ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS merdian_parameters_anon_read ON public.merdian_parameters;
CREATE POLICY merdian_parameters_anon_read
    ON public.merdian_parameters
    FOR SELECT
    TO anon
    USING (true);

GRANT SELECT ON public.merdian_parameters       TO anon;
GRANT SELECT ON public.v_merdian_parameter_audit TO anon;

-- ---------------------------------------------------------------------------
-- 7. Smoke verification — run these after the migration to confirm everything
-- ---------------------------------------------------------------------------

-- Expected: 11 active rows
SELECT count(*) AS active_param_count
FROM public.merdian_parameters
WHERE valid_to IS NULL;

-- Expected: 0.3 (or whatever the current PIN tau is for NIFTY)
SELECT public.get_parameter_num('pin.tau.NIFTY') AS pin_tau_nifty;

-- Expected: true
SELECT public.get_parameter_bool('ict.zone.dwm_breach_only') AS dwm_breach_only;

-- Audit log peek
SELECT key, value_display, lifecycle, changed_by, change_reason
FROM public.v_merdian_parameter_audit
LIMIT 15;

-- Confirm RLS is enabled and policy exists
SELECT relname, relrowsecurity AS rls_enabled,
       (SELECT count(*) FROM pg_policies p WHERE p.tablename = 'merdian_parameters') AS policy_count
FROM pg_class
WHERE relname = 'merdian_parameters' AND relnamespace = 'public'::regnamespace;

-- ============================================================================
-- END
-- ============================================================================
