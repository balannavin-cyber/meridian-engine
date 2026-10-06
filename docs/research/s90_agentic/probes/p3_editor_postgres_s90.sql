-- S90 R0.4 — two checks merdian_ro CANNOT run. Supabase SQL editor, postgres
-- role, ONE execution, SELECT only. current_user rides in the same result set.
-- (ADR-030 D2 tripwire; seed visibility — merdian_ro is RLS-blind here.)
SELECT current_user AS role_now,
       (SELECT active FROM cron.job WHERE jobid = 19)            AS jobid19_active,       -- must be false
       (SELECT jobname FROM cron.job WHERE jobid = 19)           AS jobid19_name,
       (SELECT position('gex_cycle_history' in command) > 0
          FROM cron.job WHERE jobid = 19)                        AS jobid19_names_table,  -- must be false
       (SELECT count(*) FROM public.merdian_parameters
          WHERE key LIKE 'pin_state.%' AND valid_to IS NULL)     AS pin_state_keys_active, -- 8 after seed
       (SELECT string_agg(DISTINCT value_type, ',') FROM public.merdian_parameters
          WHERE key LIKE 'pin_state.%')                          AS pin_state_value_types, -- must be 'numeric'
       (SELECT count(*) FROM public.merdian_parameters
          WHERE valid_to IS NULL)                                AS all_active_params,
       public.get_parameter_num('pin_state.locked_held_for.NIFTY') AS read_back_locked_nifty; -- 12, not NULL
