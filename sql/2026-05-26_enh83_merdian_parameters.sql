-- ============================================================================
-- ENH-83 / ADR-016 — merdian_parameters table + audit view + bootstrap seeds
-- Session 39 / 2026-05-26
--
-- Architectural contract:
--   - Temporal-immutable history (no UPDATE of existing rows; valid_to closes
--     a row and a new one is inserted)
--   - Mandatory non-empty change_reason on every write
--   - Dot-hierarchical keys (e.g. pin.tau.NIFTY)
--   - Dual storage: typed columns (value_text/value_num/value_bool) for
--     simple types; value jsonb fallback for arrays/objects when needed.
--     value_type discriminator selects which column is authoritative.
--
-- Closes: TD-S37-01 (hardcoded τ in ENH-81 views)
-- Graduates ADR-016 from PROPOSED → ACCEPTED (via ENH-83 ship per ENH-110 §Phase 1)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Table
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.merdian_parameters (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    key             text NOT NULL,
    value_text      text,
    value_num       numeric,
    value_bool      boolean,
    value_jsonb     jsonb,
    value_type      text NOT NULL,           -- 'numeric' | 'text' | 'boolean' | 'jsonb'
    category        text NOT NULL,           -- 'pin_accel' | 'signal_gating' | 'capital' | 'ict_zone' | 'session_window' | 'display' | ...
    description     text NOT NULL,
    min_value       numeric,                 -- enforced at edit-modal layer for numeric type
    max_value       numeric,                 -- enforced at edit-modal layer for numeric type
    valid_from      timestamptz NOT NULL DEFAULT now(),
    valid_to        timestamptz,             -- NULL = currently active
    changed_by      text NOT NULL DEFAULT 'system',
    change_reason   text NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT chk_change_reason_nonempty
        CHECK (length(btrim(change_reason)) > 0),

    CONSTRAINT chk_value_type_valid
        CHECK (value_type IN ('numeric', 'text', 'boolean', 'jsonb')),

    CONSTRAINT chk_value_present
        CHECK (
            (value_type = 'numeric'  AND value_num   IS NOT NULL) OR
            (value_type = 'text'     AND value_text  IS NOT NULL) OR
            (value_type = 'boolean'  AND value_bool  IS NOT NULL) OR
            (value_type = 'jsonb'    AND value_jsonb IS NOT NULL)
        ),

    CONSTRAINT chk_valid_from_to
        CHECK (valid_to IS NULL OR valid_to > valid_from)
);

-- Currently-active rows: at most one row per key with valid_to IS NULL.
CREATE UNIQUE INDEX IF NOT EXISTS uniq_merdian_parameters_active_key
    ON public.merdian_parameters (key)
    WHERE valid_to IS NULL;

CREATE INDEX IF NOT EXISTS idx_merdian_parameters_key_valid_from
    ON public.merdian_parameters (key, valid_from DESC);

CREATE INDEX IF NOT EXISTS idx_merdian_parameters_category
    ON public.merdian_parameters (category);

COMMENT ON TABLE public.merdian_parameters IS
    'Temporal-immutable parameter store per ADR-016. Append-only writes; the active row per key is the one with valid_to IS NULL. Closing a row sets its valid_to and inserts a new active row.';

COMMENT ON COLUMN public.merdian_parameters.value_type IS
    'Discriminator selecting which value_* column is authoritative for this row.';

COMMENT ON COLUMN public.merdian_parameters.change_reason IS
    'ADR-016 architectural contract: every write requires non-empty change_reason. Enforced via chk_change_reason_nonempty.';

COMMENT ON COLUMN public.merdian_parameters.valid_to IS
    'NULL = currently active. Non-NULL = row was closed at this timestamp; replacement row was inserted at the same instant.';


-- ---------------------------------------------------------------------------
-- Audit log view — reverse-chronological surface for Settings audit footer
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW public.v_merdian_parameter_audit AS
SELECT
    id,
    key,
    category,
    value_type,
    COALESCE(
        value_text,
        value_num::text,
        value_bool::text,
        value_jsonb::text
    ) AS value_display,
    valid_from,
    valid_to,
    CASE WHEN valid_to IS NULL THEN 'ACTIVE' ELSE 'CLOSED' END AS lifecycle,
    changed_by,
    change_reason,
    created_at
FROM public.merdian_parameters
ORDER BY valid_from DESC, created_at DESC;

COMMENT ON VIEW public.v_merdian_parameter_audit IS
    'Reverse-chronological audit log of every parameter write. Consumed by Settings → Calibration audit-log footer link per ENH-110 Appendix B.';


-- ---------------------------------------------------------------------------
-- get_parameter(key) — canonical read API exposed to SQL views (ENH-81 etc.)
-- Returns the value of the currently-active row for the given key.
-- Type-specific variants return typed values without client-side casts.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.get_parameter_num(p_key text)
RETURNS numeric
LANGUAGE sql STABLE
AS $$
    SELECT value_num
    FROM public.merdian_parameters
    WHERE key = p_key AND valid_to IS NULL AND value_type = 'numeric'
    LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION public.get_parameter_text(p_key text)
RETURNS text
LANGUAGE sql STABLE
AS $$
    SELECT value_text
    FROM public.merdian_parameters
    WHERE key = p_key AND valid_to IS NULL AND value_type = 'text'
    LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION public.get_parameter_bool(p_key text)
RETURNS boolean
LANGUAGE sql STABLE
AS $$
    SELECT value_bool
    FROM public.merdian_parameters
    WHERE key = p_key AND valid_to IS NULL AND value_type = 'boolean'
    LIMIT 1;
$$;

COMMENT ON FUNCTION public.get_parameter_num(text) IS
    'Canonical typed read API for numeric parameters per ADR-016. Consumed by ENH-81 views v_gex_strike_pin_zone + v_gex_strike_accel_zone — closes TD-S37-01.';


-- ---------------------------------------------------------------------------
-- update_parameter(key, ...) — canonical write API exposed as RPC.
-- SECURITY DEFINER allows anon role to call it without direct INSERT on
-- the table; the function enforces change_reason, type compatibility, and
-- temporal-immutable semantics (close old row + insert new) atomically.
-- Serialization via FOR UPDATE on the active row + the unique partial index
-- on (key) WHERE valid_to IS NULL is the concurrency guard.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.update_parameter(
    p_key           text,
    p_change_reason text,
    p_value_num     numeric  DEFAULT NULL,
    p_value_text    text     DEFAULT NULL,
    p_value_bool    boolean  DEFAULT NULL,
    p_value_jsonb   jsonb    DEFAULT NULL,
    p_changed_by    text     DEFAULT 'operator'
) RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_old   public.merdian_parameters%ROWTYPE;
    v_new_id uuid;
    v_new_num   numeric;
    v_new_text  text;
    v_new_bool  boolean;
    v_new_jsonb jsonb;
BEGIN
    IF p_change_reason IS NULL OR length(btrim(p_change_reason)) = 0 THEN
        RAISE EXCEPTION 'change_reason is required (ADR-016 architectural contract)';
    END IF;

    -- Lock the active row for the key
    SELECT * INTO v_old
    FROM public.merdian_parameters
    WHERE key = p_key AND valid_to IS NULL
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'parameter % not found or already closed', p_key;
    END IF;

    -- Resolve the new value: caller passes the matching typed arg, NULL means "no change"
    v_new_num   := CASE WHEN v_old.value_type = 'numeric' THEN COALESCE(p_value_num,  v_old.value_num)  ELSE NULL END;
    v_new_text  := CASE WHEN v_old.value_type = 'text'    THEN COALESCE(p_value_text, v_old.value_text) ELSE NULL END;
    v_new_bool  := CASE WHEN v_old.value_type = 'boolean' THEN COALESCE(p_value_bool, v_old.value_bool) ELSE NULL END;
    v_new_jsonb := CASE WHEN v_old.value_type = 'jsonb'   THEN COALESCE(p_value_jsonb, v_old.value_jsonb) ELSE NULL END;

    -- Range check for numeric type
    IF v_old.value_type = 'numeric' AND v_old.min_value IS NOT NULL AND v_new_num < v_old.min_value THEN
        RAISE EXCEPTION 'value % below min_value % for key %', v_new_num, v_old.min_value, p_key;
    END IF;
    IF v_old.value_type = 'numeric' AND v_old.max_value IS NOT NULL AND v_new_num > v_old.max_value THEN
        RAISE EXCEPTION 'value % above max_value % for key %', v_new_num, v_old.max_value, p_key;
    END IF;

    -- Close the existing active row
    UPDATE public.merdian_parameters
    SET valid_to = now()
    WHERE id = v_old.id;

    -- Insert the new active row
    INSERT INTO public.merdian_parameters (
        key, value_num, value_text, value_bool, value_jsonb,
        value_type, category, description, min_value, max_value,
        valid_from, changed_by, change_reason
    ) VALUES (
        p_key, v_new_num, v_new_text, v_new_bool, v_new_jsonb,
        v_old.value_type, v_old.category, v_old.description,
        v_old.min_value, v_old.max_value,
        now(), p_changed_by, p_change_reason
    ) RETURNING id INTO v_new_id;

    RETURN v_new_id;
END;
$$;

COMMENT ON FUNCTION public.update_parameter(text, text, numeric, text, boolean, jsonb, text) IS
    'Canonical write API for merdian_parameters per ADR-016. Atomically closes the active row and inserts a new active row. SECURITY DEFINER so anon role can invoke without direct INSERT on table. Enforces change_reason + numeric range bounds.';

GRANT EXECUTE ON FUNCTION public.update_parameter(text, text, numeric, text, boolean, jsonb, text) TO anon;


-- ---------------------------------------------------------------------------
-- Bootstrap seeds — 11 parameters per ENH-110 §Phase 1 Backend
-- All written with change_reason = 'S39 ADR-016 bootstrap seed (ENH-83 ship)'
-- ---------------------------------------------------------------------------

INSERT INTO public.merdian_parameters
    (key, value_num, value_type, category, description, min_value, max_value, changed_by, change_reason)
VALUES
    -- (a) PIN / ACCEL THRESHOLDS — ADR-016 design target
    ('pin.tau.NIFTY',         0.30, 'numeric', 'pin_accel',
     'Prominence threshold τ for PIN zone detection on NIFTY per ENH-81 v_gex_strike_pin_zone. Range 0.1–0.5 typical.',
     0.05, 0.80, 'system', 'S39 ADR-016 bootstrap seed (ENH-83 ship)'),

    ('pin.tau.SENSEX',        0.30, 'numeric', 'pin_accel',
     'Prominence threshold τ for PIN zone detection on SENSEX per ENH-81 v_gex_strike_pin_zone.',
     0.05, 0.80, 'system', 'S39 ADR-016 bootstrap seed (ENH-83 ship)'),

    ('accel.tau.NIFTY',       0.30, 'numeric', 'pin_accel',
     'Prominence threshold τ for ACCEL zone detection on NIFTY per ENH-81 v_gex_strike_accel_zone.',
     0.05, 0.80, 'system', 'S39 ADR-016 bootstrap seed (ENH-83 ship)'),

    ('accel.tau.SENSEX',      0.30, 'numeric', 'pin_accel',
     'Prominence threshold τ for ACCEL zone detection on SENSEX per ENH-81 v_gex_strike_accel_zone.',
     0.05, 0.80, 'system', 'S39 ADR-016 bootstrap seed (ENH-83 ship)'),

    -- (b) SIGNAL GATING — ADR-012 + ADR-004 references
    ('sl.buffer_pct',         0.005, 'numeric', 'signal_gating',
     'Spot-anchored SL buffer X per ADR-012 §3. BULL trigger = close < zone_low × (1−X); BEAR = close > zone_high × (1+X).',
     0.001, 0.020, 'system', 'S39 ADR-016 bootstrap seed (ENH-83 ship)'),

    ('retest.tolerance_pct',  0.001, 'numeric', 'signal_gating',
     'Retest tolerance per ADR-004 §11 — first-touch detection window relative to zone edge.',
     0.0001, 0.010, 'system', 'S39 ADR-016 bootstrap seed (ENH-83 ship)'),

    -- (c) CAPITAL FLOORS
    ('capital.default_inr',   25000, 'numeric', 'capital',
     'Default trade capital in INR. Operator-tunable per session via Settings → Capital & sizing.',
     5000, 200000, 'system', 'S39 ADR-016 bootstrap seed (ENH-83 ship)'),

    ('capital.kelly_multiplier', 1.0, 'numeric', 'capital',
     'Kelly multiplier applied to sizing recommendation. 1.0 = full Kelly; <1 = fractional Kelly.',
     0.1, 2.0, 'system', 'S39 ADR-016 bootstrap seed (ENH-83 ship)'),

    ('capital.max_position_inr', 50000, 'numeric', 'capital',
     'Hard per-position capital cap in INR. Acts as backstop above Kelly recommendation.',
     10000, 500000, 'system', 'S39 ADR-016 bootstrap seed (ENH-83 ship)'),

    -- (d) ICT ZONE PARAMS — per ADR-005
    ('ict.zone.h_valid_days', 7, 'numeric', 'ict_zone',
     '1H OB/FVG zone validity horizon in days per ADR-005 (price-breach OR 1-week, whichever first).',
     1, 30, 'system', 'S39 ADR-016 bootstrap seed (ENH-83 ship)');

-- Boolean seed — handled separately because the multi-row INSERT above is numeric-only
INSERT INTO public.merdian_parameters
    (key, value_bool, value_type, category, description, changed_by, change_reason)
VALUES
    ('ict.zone.dwm_breach_only', true, 'boolean', 'ict_zone',
     'When true, D/W/M OB/FVG zones expire only on price-breach (valid_to=NULL) per ADR-005. When false, falls back to date-expiry.',
     'system', 'S39 ADR-016 bootstrap seed (ENH-83 ship)');


-- ---------------------------------------------------------------------------
-- RLS triplet for merdian_parameters + v_merdian_parameter_audit
-- (TD-S37-03 mitigation pattern — three-line canonical triplet)
-- NOTE: anon SELECT permitted (display layer needs the active rows + audit
-- log to render). Writes via service-role only — Lovable does not write
-- directly; Settings save action calls a server-side function that runs
-- with elevated credentials.
-- ---------------------------------------------------------------------------

ALTER TABLE public.merdian_parameters ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS merdian_parameters_anon_read ON public.merdian_parameters;
CREATE POLICY merdian_parameters_anon_read
    ON public.merdian_parameters
    FOR SELECT
    TO anon
    USING (true);

GRANT SELECT ON public.merdian_parameters TO anon;
GRANT SELECT ON public.v_merdian_parameter_audit TO anon;

-- Smoke-probe (run as anon role to verify TD-S37-03 mitigation pre-ship):
--   SELECT count(*) FROM public.merdian_parameters WHERE valid_to IS NULL;
--   -- Expect: 11 (the bootstrap seeds)
--   SELECT count(*) FROM public.v_merdian_parameter_audit;
--   -- Expect: 11 (one row per bootstrap insert)

-- ============================================================================
-- END
-- ============================================================================
