-- l13_measure.sql — S92 L13 bind: READ-ONLY measurement of v_oi_rotation_since_open before the Lovable prompt.
-- Run each block ON ITS OWN in the Supabase SQL editor and paste each result.

-- ── M1 · does anon read it inside its 3 s statement_timeout? (paste the last 3 lines: Planning / Execution Time)
SET LOCAL ROLE anon;   -- lasts only for this run; the editor wraps a run in one transaction
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_oi_rotation_since_open;

-- ── M2 · what it says right now, per symbol (this is the acceptance baseline for the L13 render)
WITH v AS (SELECT * FROM public.v_oi_rotation_since_open)
SELECT symbol, expiry_date, dte,
       to_char(anchor_ts AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI') AS anchor_ist,
       to_char(latest_ts AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI') AS latest_ist,
       count(*)                                                        AS n_strikes,
       count(*) FILTER (WHERE ce_presence = 'BOTH')                    AS ce_both,
       count(*) FILTER (WHERE pe_presence = 'BOTH')                    AS pe_both,
       count(*) FILTER (WHERE ce_presence IN ('ANCHOR_ONLY','LATEST_ONLY')
                           OR pe_presence IN ('ANCHOR_ONLY','LATEST_ONLY')) AS churned,
       sum(ce_oi_delta_qty)                                            AS ce_net_delta_qty,
       sum(pe_oi_delta_qty)                                            AS pe_net_delta_qty,
       max(abs(ce_oi_delta_qty))                                       AS ce_max_abs_delta,
       max(abs(pe_oi_delta_qty))                                       AS pe_max_abs_delta,
       count(*) FILTER (WHERE abs(ce_oi_delta_qty) > 1000000
                           OR abs(pe_oi_delta_qty) > 1000000)          AS n_abs_over_1m,
       max(snapshot_age_min)                                           AS age_min,
       bool_and(is_fresh)                                              AS is_fresh
  FROM v
 GROUP BY symbol, expiry_date, dte, anchor_ts, latest_ts
 ORDER BY symbol;

-- ── M3 · top 5 strikes by |Δ| per symbol and side (shows whether the TD-S84-NEW-4 stale-anchor artefact is present today)
WITH legs AS (
  SELECT symbol, 'CE' AS side, strike, ce_oi_anchor_qty AS anchor_qty, ce_oi_latest_qty AS latest_qty,
         ce_oi_delta_qty AS delta_qty, ce_presence AS presence FROM public.v_oi_rotation_since_open
  UNION ALL
  SELECT symbol, 'PE', strike, pe_oi_anchor_qty, pe_oi_latest_qty, pe_oi_delta_qty, pe_presence
    FROM public.v_oi_rotation_since_open
), r AS (
  SELECT legs.*, row_number() OVER (PARTITION BY symbol, side ORDER BY abs(delta_qty) DESC NULLS LAST) AS rn FROM legs
)
SELECT symbol, side, rn, strike, anchor_qty, latest_qty, delta_qty, presence
  FROM r WHERE rn <= 5 ORDER BY symbol, side, rn;
