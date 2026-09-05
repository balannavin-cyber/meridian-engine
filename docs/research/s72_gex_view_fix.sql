-- ============================================================================
-- S72 — v_gex_strike_pin_zone / v_gex_strike_accel_zone corrections
--
-- Two defects, both present in both views, both found by reading the view
-- definitions on 2026-08-31 (not from any register entry):
--
--   FIX 1 (tau wiring) — the walk threshold was hardcoded 0.3 while the
--   output column tau_used separately resolved get_parameter_num('pin.tau.'||symbol).
--   The knob was wired to the label, not to the computation. Evidenced live:
--   pin.tau.NIFTY was set to 0.25 on 2026-05-27 for ~30s and reverted; the walk
--   ran at 0.3 throughout while the view would have displayed T0.25.
--   Fix resolves tau ONCE in the peak/trough CTE, carries it through the walk,
--   and selects the carried column — so label and computation are structurally
--   the same value and cannot drift again.
--   COALESCE default added: get_parameter_num returns NULL on a missing key
--   (no default in its body), which would otherwise NULL the whole predicate.
--
--   FIX 2 (bounded latest_run) — DISTINCT ON (symbol) ... ORDER BY symbol, ts DESC
--   with no symbol predicate is a full ordered scan of all rows (1.32M as of
--   2026-08-31, growing ~28k/day) to return two rows, on every call. Postgres
--   has no loose index scan. This is the residual cost ADR-021 did not remove
--   and the reason the view sits on the statement_timeout boundary
--   (observed 57014 on 2026-08-28 and 2026-08-31, both intermittent).
--   Replaced with a lateral: one index lookup per symbol against the existing
--   idx_gss_symbol_ts (symbol, ts DESC). O(2) regardless of table size.
--
-- HAZARD introduced by FIX 2: the symbol list is now a literal. A third symbol
-- added later would be silently absent from both views. This is the same
-- silent-omission shape as the dropped .bat line (TD-S71-NEW-7). Guard with a
-- health-check assertion that (select count(distinct symbol) from
-- gex_strike_snapshots) equals the literal list length. File before shipping.
--
-- Output column names, order and types are unchanged in both views, so
-- CREATE OR REPLACE VIEW is legal and no dependent object needs dropping.
--
-- APPLY ORDER: Section 1 (snapshot) -> Section 2 (pin) -> Section 4 (verify pin)
--              -> Section 3 (accel) -> Section 4 (verify accel) -> Section 5.
-- Run while the GEX writer is idle (outside 03:00-10:10 UTC) or the snapshot
-- and the comparison read different runs and the diff is meaningless.
-- ============================================================================


-- ============================================================================
-- SECTION 1 — Snapshot current output BEFORE any change
-- ============================================================================

DROP TABLE IF EXISTS public._s72_pin_before;
DROP TABLE IF EXISTS public._s72_accel_before;

CREATE TABLE public._s72_pin_before   AS SELECT * FROM public.v_gex_strike_pin_zone;
CREATE TABLE public._s72_accel_before AS SELECT * FROM public.v_gex_strike_accel_zone;

SELECT 'pin' AS view, count(*) FROM public._s72_pin_before
UNION ALL
SELECT 'accel', count(*) FROM public._s72_accel_before;

-- Baseline plan cost, for the before/after comparison in Section 4.
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_strike_pin_zone;


-- ============================================================================
-- SECTION 2 — v_gex_strike_pin_zone
-- ============================================================================

CREATE OR REPLACE VIEW public.v_gex_strike_pin_zone AS
WITH RECURSIVE latest_run AS (
        SELECT s.symbol,
               lr.run_id,
               lr.ts
          FROM (VALUES ('NIFTY'), ('SENSEX')) AS s(symbol)
          CROSS JOIN LATERAL (
               SELECT g.run_id, g.ts
                 FROM gex_strike_snapshots g
                WHERE g.symbol = s.symbol
                ORDER BY g.ts DESC
                LIMIT 1
          ) lr
     ), scoped AS (
        SELECT g.id,
               g.run_id,
               g.symbol,
               g.ts,
               g.expiry_date,
               g.dte,
               g.strike,
               g.spot,
               g.oi_call,
               g.oi_put,
               g.gex_cr,
               g.created_at,
               g.gamma_call,
               g.gamma_put
          FROM gex_strike_snapshots g
          JOIN latest_run lr ON g.symbol = lr.symbol AND g.run_id = lr.run_id
     ), strike_step AS (
        SELECT x.run_id,
               x.symbol,
               x.expiry_date,
               min(x.diff) AS step
          FROM ( SELECT scoped.run_id,
                        scoped.symbol,
                        scoped.expiry_date,
                        scoped.strike - lag(scoped.strike) OVER (PARTITION BY scoped.run_id, scoped.symbol, scoped.expiry_date ORDER BY scoped.strike) AS diff
                   FROM scoped) x
         WHERE x.diff > 0::numeric
         GROUP BY x.run_id, x.symbol, x.expiry_date
     ), peak AS (
        SELECT DISTINCT ON (scoped.run_id, scoped.symbol, scoped.expiry_date)
               scoped.run_id,
               scoped.symbol,
               scoped.expiry_date,
               scoped.ts,
               scoped.spot,
               scoped.strike  AS peak_strike,
               scoped.gex_cr  AS peak_gex_cr,
               COALESCE(get_parameter_num('pin.tau.'::text || scoped.symbol), 0.3) AS tau
          FROM scoped
         WHERE scoped.gex_cr > 0::numeric
         ORDER BY scoped.run_id, scoped.symbol, scoped.expiry_date, scoped.gex_cr DESC, (abs(scoped.strike - scoped.spot))
     ), walk AS (
        SELECT p.run_id,
               p.symbol,
               p.expiry_date,
               p.ts,
               p.peak_strike  AS strike,
               p.peak_gex_cr  AS gex_cr,
               p.peak_gex_cr,
               p.tau,
               s.step,
               0 AS direction
          FROM peak p
          JOIN strike_step s USING (run_id, symbol, expiry_date)
        UNION ALL
        SELECT g.run_id,
               g.symbol,
               g.expiry_date,
               g.ts,
               g.strike,
               g.gex_cr,
               w_1.peak_gex_cr,
               w_1.tau,
               w_1.step,
               CASE
                   WHEN g.strike < w_1.strike THEN '-1'::integer
                   ELSE 1
               END AS direction
          FROM walk w_1
          JOIN scoped g ON g.run_id = w_1.run_id AND g.symbol = w_1.symbol AND g.expiry_date = w_1.expiry_date
                       AND ((w_1.direction = ANY (ARRAY[0, '-1'::integer])) AND abs(g.strike - (w_1.strike - w_1.step)) < 0.0001
                         OR (w_1.direction = ANY (ARRAY[0, 1]))            AND abs(g.strike - (w_1.strike + w_1.step)) < 0.0001)
         WHERE g.gex_cr > 0::numeric
           AND g.gex_cr >= (w_1.tau * w_1.peak_gex_cr)
     )
SELECT run_id,
       symbol,
       expiry_date,
       max(ts)                                       AS ts,
       min(strike)                                   AS pin_lower,
       max(strike)                                   AS pin_upper,
       count(*)                                      AS n_strikes,
       sum(gex_cr)                                   AS total_pin_gex_cr,
       max(peak_gex_cr)                              AS peak_pin_gex_cr,
       (array_agg(strike ORDER BY gex_cr DESC))[1]   AS peak_pin_strike,
       max(tau)                                      AS tau_used
  FROM walk w
 GROUP BY run_id, symbol, expiry_date;


-- ============================================================================
-- SECTION 3 — v_gex_strike_accel_zone
--
-- Note: the original recursive term aliased its CASE expression "AS int4"
-- where the pin view used "AS direction". That is cosmetic only — a recursive
-- UNION ALL takes column names from the non-recursive term and matches the
-- recursive term positionally, so the column was always "direction". Renamed
-- here for symmetry. No behaviour change.
-- ============================================================================

CREATE OR REPLACE VIEW public.v_gex_strike_accel_zone AS
WITH RECURSIVE latest_run AS (
        SELECT s.symbol,
               lr.run_id,
               lr.ts
          FROM (VALUES ('NIFTY'), ('SENSEX')) AS s(symbol)
          CROSS JOIN LATERAL (
               SELECT g.run_id, g.ts
                 FROM gex_strike_snapshots g
                WHERE g.symbol = s.symbol
                ORDER BY g.ts DESC
                LIMIT 1
          ) lr
     ), scoped AS (
        SELECT g.id,
               g.run_id,
               g.symbol,
               g.ts,
               g.expiry_date,
               g.dte,
               g.strike,
               g.spot,
               g.oi_call,
               g.oi_put,
               g.gex_cr,
               g.created_at,
               g.gamma_call,
               g.gamma_put
          FROM gex_strike_snapshots g
          JOIN latest_run lr ON g.symbol = lr.symbol AND g.run_id = lr.run_id
     ), strike_step AS (
        SELECT x.run_id,
               x.symbol,
               x.expiry_date,
               min(x.diff) AS step
          FROM ( SELECT scoped.run_id,
                        scoped.symbol,
                        scoped.expiry_date,
                        scoped.strike - lag(scoped.strike) OVER (PARTITION BY scoped.run_id, scoped.symbol, scoped.expiry_date ORDER BY scoped.strike) AS diff
                   FROM scoped) x
         WHERE x.diff > 0::numeric
         GROUP BY x.run_id, x.symbol, x.expiry_date
     ), trough AS (
        SELECT DISTINCT ON (scoped.run_id, scoped.symbol, scoped.expiry_date)
               scoped.run_id,
               scoped.symbol,
               scoped.expiry_date,
               scoped.ts,
               scoped.spot,
               scoped.strike  AS trough_strike,
               scoped.gex_cr  AS trough_gex_cr,
               COALESCE(get_parameter_num('accel.tau.'::text || scoped.symbol), 0.3) AS tau
          FROM scoped
         WHERE scoped.gex_cr < 0::numeric
         ORDER BY scoped.run_id, scoped.symbol, scoped.expiry_date, scoped.gex_cr, (abs(scoped.strike - scoped.spot))
     ), walk AS (
        SELECT t.run_id,
               t.symbol,
               t.expiry_date,
               t.ts,
               t.trough_strike  AS strike,
               t.trough_gex_cr  AS gex_cr,
               t.trough_gex_cr,
               t.tau,
               s.step,
               0 AS direction
          FROM trough t
          JOIN strike_step s USING (run_id, symbol, expiry_date)
        UNION ALL
        SELECT g.run_id,
               g.symbol,
               g.expiry_date,
               g.ts,
               g.strike,
               g.gex_cr,
               w_1.trough_gex_cr,
               w_1.tau,
               w_1.step,
               CASE
                   WHEN g.strike < w_1.strike THEN '-1'::integer
                   ELSE 1
               END AS direction
          FROM walk w_1
          JOIN scoped g ON g.run_id = w_1.run_id AND g.symbol = w_1.symbol AND g.expiry_date = w_1.expiry_date
                       AND ((w_1.direction = ANY (ARRAY[0, '-1'::integer])) AND abs(g.strike - (w_1.strike - w_1.step)) < 0.0001
                         OR (w_1.direction = ANY (ARRAY[0, 1]))            AND abs(g.strike - (w_1.strike + w_1.step)) < 0.0001)
         WHERE g.gex_cr < 0::numeric
           AND abs(g.gex_cr) >= (w_1.tau * abs(w_1.trough_gex_cr))
     )
SELECT run_id,
       symbol,
       expiry_date,
       max(ts)                                  AS ts,
       min(strike)                              AS accel_lower,
       max(strike)                              AS accel_upper,
       count(*)                                 AS n_strikes,
       sum(gex_cr)                              AS total_accel_gex_cr,
       min(trough_gex_cr)                       AS trough_gex_cr,
       (array_agg(strike ORDER BY gex_cr))[1]   AS trough_strike,
       max(tau)                                 AS tau_used
  FROM walk w
 GROUP BY run_id, symbol, expiry_date;


-- ============================================================================
-- SECTION 4 — Equivalence gate
--
-- All four pin.tau.* / accel.tau.* live values are 0.30 as of 2026-08-31, and
-- the old predicate was a hardcoded 0.3. The rewrite must therefore produce
-- IDENTICAL output. Any non-empty result below means the rewrite changed
-- something it should not have — roll back with the original definitions
-- rather than reasoning about which side is right.
-- ============================================================================

-- Symmetric difference, pin. Expect ZERO rows.
(SELECT 'new_not_in_old' AS side, * FROM public.v_gex_strike_pin_zone
 EXCEPT ALL SELECT 'new_not_in_old', * FROM public._s72_pin_before)
UNION ALL
(SELECT 'old_not_in_new', * FROM public._s72_pin_before
 EXCEPT ALL SELECT 'old_not_in_new', * FROM public.v_gex_strike_pin_zone);

-- Symmetric difference, accel. Expect ZERO rows.
(SELECT 'new_not_in_old' AS side, * FROM public.v_gex_strike_accel_zone
 EXCEPT ALL SELECT 'new_not_in_old', * FROM public._s72_accel_before)
UNION ALL
(SELECT 'old_not_in_new', * FROM public._s72_accel_before
 EXCEPT ALL SELECT 'old_not_in_new', * FROM public.v_gex_strike_accel_zone);

-- Plan after. Compare against the Section 1 baseline: the ~1.3M-row ordered
-- scan feeding the Unique node should be replaced by two index lookups.
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_strike_pin_zone;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_strike_accel_zone;


-- ============================================================================
-- SECTION 5 — Prove tau is now live (the whole point of FIX 1)
--
-- CORRECTED 2026-09-05, AFTER THE FACT. The version originally committed here
-- COULD NOT RUN and was never successfully applied. It read:
--
--     INSERT INTO public.merdian_parameters
--            (key, value_num, value_type, valid_from, valid_to)
--     VALUES ('pin.tau.NIFTY', 0.50, 'numeric', now(), NULL);
--
-- merdian_parameters has THREE NOT NULL columns with no default that this list
-- omits: category, description, change_reason. It failed with
--   ERROR: 23502 null value in column "category" ... violates not-null constraint
-- and, because the Supabase SQL editor wraps a pasted script in one transaction,
-- it took SECTIONS 2 AND 3 DOWN WITH IT. Both views rolled back; production was
-- untouched; the whole file had to be re-run section by section.
--
-- Two lessons, both worth more than the fix:
--
--   1. The column list was written without reading the schema. Every other
--      statement in this file was built from measured output; this one was
--      constructed from memory. It is the only one that failed.
--
--   2. A verified DDL change and an unverified data probe do not belong in the
--      same script. Section 5 is a DEMONSTRATION; Sections 2-4 are the FIX.
--      Bundling them meant the weakest statement in the file gated the
--      strongest. RUN SECTIONS SEPARATELY.
--
-- The corrected form below CLONES the row that is already valid and changes only
-- value_num and change_reason, so the three NOT NULL columns are inherited rather
-- than invented. It is wrapped BEGIN/ROLLBACK: the probe reads the changed value
-- inside the transaction and discards it, so nothing needs restoring afterwards.
--
-- Note also uniq_merdian_parameters_active_key, a partial unique index on
-- (key) WHERE valid_to IS NULL. The table structurally cannot hold two active
-- rows for one key, so an expire-then-insert cannot half-complete into a
-- duplicate — but it CAN half-complete into ZERO active rows, which the partial
-- index permits. That is the failure mode the explicit transaction guards.
--
-- OBSERVED RESULT when this was finally run (2026-09-05):
--     tau 0.30 -> pin_lower 24300, pin_upper 24500, n_strikes 5
--     tau 0.50 -> pin_lower 24300, pin_upper 24400, n_strikes 3   <- zone moved
--     restored -> pin_lower 24300, pin_upper 24500, n_strikes 5
-- Under the OLD view the boundaries would NOT have moved and only tau_used
-- would have changed. That is the entire proof.
-- ============================================================================

BEGIN;

SELECT symbol, pin_lower, pin_upper, n_strikes, tau_used
  FROM public.v_gex_strike_pin_zone WHERE symbol = 'NIFTY';

UPDATE public.merdian_parameters SET valid_to = now()
 WHERE key = 'pin.tau.NIFTY' AND valid_to IS NULL;

INSERT INTO public.merdian_parameters
       (key, value_text, value_num, value_bool, value_jsonb, value_type,
        category, description, min_value, max_value,
        valid_from, valid_to, changed_by, change_reason)
SELECT  key, value_text, 0.50,      value_bool, value_jsonb, value_type,
        category, description, min_value, max_value,
        now(), NULL, 'system', 'S72 tau liveness probe'
FROM public.merdian_parameters
WHERE key = 'pin.tau.NIFTY'
ORDER BY valid_from DESC
LIMIT 1;

-- Expect a NARROWER zone and tau_used = 0.50.
SELECT symbol, pin_lower, pin_upper, n_strikes, tau_used
  FROM public.v_gex_strike_pin_zone WHERE symbol = 'NIFTY';

ROLLBACK;

-- Confirm the rollback: expect ONE row, value_num 0.30, valid_to NULL.
SELECT key, value_num, category, valid_from, valid_to
  FROM public.merdian_parameters
 WHERE key = 'pin.tau.NIFTY'
 ORDER BY valid_from DESC;


-- ============================================================================
-- SECTION 6 — Cleanup (only after Section 4 returned zero rows)
-- ============================================================================

-- DROP TABLE IF EXISTS public._s72_pin_before;
-- DROP TABLE IF EXISTS public._s72_accel_before;
