-- mp7_control_live.sql -- M-P7 Part 0b: what the LIVE views say about their current session.
-- The replay (mp7_cycles.sql) for the same date must reproduce these figures at the settled
-- cycle before Part 1 is scored (prereg section 5). Reads the book's own totals and P5's anchor;
-- reads no flow and computes no sign. MUST run while both views still show the replay date,
-- i.e. before the next session's pre-open rows land (~08:30 IST on the next trading day).
\set QUIET on
\pset format csv
SELECT 'book' AS src, b.symbol, b.session_date, b.expiry_date,
       to_char(b.settled_ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS t_ist,
       max(b.leg_call_dex_cr)  AS a1,
       max(b.leg_put_dex_cr)   AS a2,
       max(b.leg_oi_qty)       AS a3,
       max(b.leg_gap_oi_qty)   AS a4
  FROM public.v_dex_standing_book b
 WHERE b.leg_n = 1
 GROUP BY b.symbol, b.session_date, b.expiry_date, b.settled_ts
UNION ALL
SELECT 'p5', p.symbol, (p.anchor_ts AT TIME ZONE 'Asia/Kolkata')::date, p.expiry_date,
       to_char(p.anchor_ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS'),
       sum(COALESCE(p.ce_oi_anchor_qty, 0) + COALESCE(p.pe_oi_anchor_qty, 0)),
       count(*) FILTER (WHERE p.ce_oi_anchor_qty IS NOT NULL OR p.pe_oi_anchor_qty IS NOT NULL),
       NULL, NULL
  FROM public.v_oi_since_preopen p
 GROUP BY p.symbol, p.anchor_ts, p.expiry_date
 ORDER BY 1, 2;
