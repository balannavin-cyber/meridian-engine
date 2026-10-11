-- mp7_status.sql -- M-P7, per-session status. Pre-registered with
-- docs/research/s96_priority/p7/MP7_flow_badge_prereg_2026-10-11.md (section 3).
-- Reads NO outcome: no flow, no book, no sign. One row per symbol for the date :'d'.
-- Session rule = v_dex_standing_book (ENH-140) clauses 1 and 2; front expiry = book leg_n 1;
-- anchor = v_oi_since_preopen (ENH-142, S95-B): first front-expiry row of the date, refused at/after 09:15 IST.
-- Run (mp7_run.sh): { printf "\\set d '%s'\n" 2026-09-01; cat mp7_status.sql; } | bin/roq.sh
\set QUIET on
\pset format csv
WITH RECURSIVE syms AS (
        SELECT (SELECT min(c.symbol) FROM public.option_chain_snapshots c) AS symbol
        UNION ALL
        SELECT (SELECT min(c.symbol) FROM public.option_chain_snapshots c WHERE c.symbol > s.symbol)
          FROM syms s WHERE s.symbol IS NOT NULL
     ), base AS MATERIALIZED (
        SELECT s.symbol, (:'d')::date AS session_date,
               EXISTS (SELECT 1 FROM public.trading_calendar tc
                        WHERE tc.trade_date = (:'d')::date AND tc.is_open = false) AS cal_closed,
               (SELECT count(DISTINCT m.spot)
                  FROM public.market_spot_snapshots m
                 WHERE m.symbol = s.symbol
                   AND m.ts >= ((:'d')::date::timestamp AT TIME ZONE 'Asia/Kolkata')
                   AND m.ts <= (((:'d')::date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata')) AS n_distinct_spot
          FROM syms s WHERE s.symbol IS NOT NULL
     ), fr AS MATERIALIZED (
        SELECT b.*,
               -- A1 (2026-10-11): min over a DISTINCT of the SAME predicates. The bare min()
               -- let the planner walk idx_ocs_symbol_expiry_strike_type with ts as a filter
               -- (EXPLAIN 2026-08-24: cost 294,617, 30 s timeout). DISTINCT needs every matching
               -- row, so the ts range on idx_ocs_ts_symbol_expiry is the cheap path -- the
               -- v_dex_standing_book legs CTE shape (measured 61 ms). Same value by definition.
               (SELECT min(e.expiry_date)
                  FROM (SELECT DISTINCT c.expiry_date FROM public.option_chain_snapshots c
                         WHERE c.symbol = b.symbol
                           AND c.ts >= (b.session_date::timestamp AT TIME ZONE 'Asia/Kolkata')
                           AND c.ts <= ((b.session_date + TIME '15:15') AT TIME ZONE 'Asia/Kolkata')
                           AND c.expiry_date >= b.session_date) e) AS expiry_date
          FROM base b
     ), an AS MATERIALIZED (
        SELECT f.*,
               (SELECT min(c.ts) FROM public.option_chain_snapshots c
                 WHERE c.symbol = f.symbol AND c.expiry_date = f.expiry_date
                   AND c.ts >= (f.session_date::timestamp AT TIME ZONE 'Asia/Kolkata')
                   AND c.ts <  ((f.session_date + 1)::timestamp AT TIME ZONE 'Asia/Kolkata')) AS first_ts
          FROM fr f
     )
SELECT a.symbol,
       a.session_date,
       a.cal_closed,
       a.n_distinct_spot,
       a.expiry_date,
       to_char(a.first_ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS first_ist,
       CASE WHEN a.cal_closed OR a.n_distinct_spot <= 1 THEN 'NOT_SESSION'
            WHEN a.expiry_date IS NULL                   THEN 'NO_FRONT'
            WHEN a.first_ts IS NULL
              OR a.first_ts >= ((a.session_date + TIME '09:15') AT TIME ZONE 'Asia/Kolkata')
                                                          THEN 'NO_PREOPEN'
            ELSE 'ANCHORED'
       END AS status
  FROM an a
 ORDER BY a.symbol;
