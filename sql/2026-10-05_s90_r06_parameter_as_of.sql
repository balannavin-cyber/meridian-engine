-- S90 R0.6 — effective-dated read of merdian_parameters (ADR-031 D4.1). Additive.
-- SQL editor, postgres, ONE execution. Adds a 2-argument overload; the existing
-- 1-argument get_parameter_num(text) is untouched (no default on p_as_of => no ambiguity).
-- Gate: the overload must agree with the 1-argument function for every active numeric key
-- at now(), and must return the PRE-change value for a key read before its valid_from.
BEGIN;

CREATE OR REPLACE FUNCTION public.get_parameter_num(p_key text, p_as_of timestamptz)
RETURNS numeric
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public
AS $fn$
  SELECT p.value_num
  FROM public.merdian_parameters p
  WHERE p.key = p_key
    AND p.value_type = 'numeric'
    AND p.valid_from <= p_as_of
    AND (p.valid_to IS NULL OR p.valid_to > p_as_of)
  ORDER BY p.valid_from DESC
  LIMIT 1
$fn$;

COMMENT ON FUNCTION public.get_parameter_num(text, timestamptz) IS
  'S90 R0.6 (ADR-031 D4.1). The numeric parameter value in force at p_as_of (valid_from <= as_of < valid_to). Replays read rules as they were. NULL when no row was in force: absence is not a default (ADR-020).';

DO $gate$
DECLARE n_keys int; n_disagree int;
BEGIN
  SELECT count(*),
         count(*) FILTER (WHERE public.get_parameter_num(k.key) IS DISTINCT FROM public.get_parameter_num(k.key, now()))
    INTO n_keys, n_disagree
  FROM (SELECT DISTINCT key FROM public.merdian_parameters WHERE valid_to IS NULL AND value_type = 'numeric') k;
  IF n_keys = 0 THEN RAISE EXCEPTION 'S90 R0.6 gate: no active numeric keys'; END IF;
  IF n_disagree > 0 THEN RAISE EXCEPTION 'S90 R0.6 gate: % of % keys disagree with get_parameter_num(text) at now()', n_disagree, n_keys; END IF;
END
$gate$;

COMMIT;

-- Evidence (last result shown): the S40 pin.tau.NIFTY history (0.30 -> 0.25 -> 0.30 within 30 s)
-- read at each row's valid_from, and every key now vs as-of the day before it was created.
SELECT p.key, to_char(p.valid_from AT TIME ZONE 'Asia/Kolkata','YYYY-MM-DD HH24:MI:SS') AS valid_from_ist,
       p.value_num AS row_value,
       public.get_parameter_num(p.key, p.valid_from) AS read_at_valid_from,
       public.get_parameter_num(p.key, p.valid_from - interval '1 second') AS read_1s_before,
       public.get_parameter_num(p.key) AS read_now
FROM public.merdian_parameters p
WHERE p.value_type = 'numeric'
ORDER BY p.key, p.valid_from;
