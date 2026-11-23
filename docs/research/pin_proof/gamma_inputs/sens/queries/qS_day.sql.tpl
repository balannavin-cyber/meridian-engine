\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- MR-PIN2 step 3 (rate sensitivity) per-day slice.
-- __IID__ instrument_id, __SYM__ symbol, __D__ trade_date. Literals substituted by
-- run_sens.sh; psql -v does not work through bin/roq.sh.
--
-- bar_ts is IST clock labelled +00:00 (TD-029 family): literals are written +00 and
-- never converted. Targets 10:00 / 12:30 / 15:00 at second :59.
--
-- The sel / fexp / spt CTEs are REPRODUCED FROM queries/qB_day.sql.tpl:14-43 unchanged,
-- so the minute each day resolves to, and the front expiry, are the ones Part B B1
-- picked -- not a re-derivation. B1 recorded offset 0 on all 72 minutes; the +/-120 s
-- LATERAL is kept anyway so that a day which did NOT resolve at offset 0 would resolve
-- here the same way it did there instead of silently returning nothing.
--
-- ONE statement. No temp table, no write. Reads only the +/-120 s neighbourhood of each
-- target minute, via a LATERAL probe on (instrument_id, trade_date, bar_ts).
WITH tgt(tname, tts) AS (
  VALUES ('10:00', timestamptz '__D__ 10:00:59+00'),
         ('12:30', timestamptz '__D__ 12:30:59+00'),
         ('15:00', timestamptz '__D__ 15:00:59+00')
), sel AS (
  SELECT t.tname, p.bar_ts,
         extract(epoch FROM (p.bar_ts - t.tts)) AS off_sec
    FROM tgt t
    CROSS JOIN LATERAL (
      SELECT ob.bar_ts
        FROM hist_option_bars_1m ob
       WHERE ob.instrument_id = '__IID__'
         AND ob.trade_date = date '__D__'
         AND ob.bar_ts >= t.tts - interval '120 seconds'
         AND ob.bar_ts <= t.tts + interval '120 seconds'
       ORDER BY abs(extract(epoch FROM (ob.bar_ts - t.tts))), ob.bar_ts
       LIMIT 1
    ) p
), fexp AS (
  SELECT s.tname, min(g.expiry_date) AS expiry
    FROM sel s
    JOIN hist_option_greeks_1m g
      ON g.instrument_id = '__IID__' AND g.bar_ts = s.bar_ts
     AND g.expiry_date >= date '__D__'
   GROUP BY 1
), spt AS (
  SELECT s.tname, hs.close::float8 AS spot
    FROM sel s
    JOIN hist_spot_bars_1m hs
      ON hs.instrument_id = '__IID__' AND hs.bar_ts = s.bar_ts
)
SELECT tag, payload FROM (
  -- S0: how each sampled minute resolved. One row per target minute.
  SELECT 'S0' AS tag, row_to_json(t)::text AS payload FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d, s.tname,
           to_char(s.bar_ts AT TIME ZONE 'UTC', 'HH24:MI:SS') AS bar_clock,
           s.off_sec, sp.spot, fe.expiry::text AS expiry,
           (fe.expiry - date '__D__') AS dte_opt
      FROM sel s LEFT JOIN spt sp ON sp.tname = s.tname
                 LEFT JOIN fexp fe ON fe.tname = s.tname
  ) t
  UNION ALL
  -- S1: every front-expiry leg within 3 % of spot, with the stored solve.
  -- iv and gamma are emitted as TEXT: both are unconstrained numeric (0c), and text
  -- preserves the stored decimal exactly, where ::float8 would assert a conversion.
  SELECT 'S1', row_to_json(t)::text FROM (
    SELECT '__SYM__' AS sym, '__D__' AS d, s.tname,
           sp.spot, ob.strike::float8 AS strike, ob.option_type AS ot,
           ob.expiry_date::text AS expiry,
           (ob.expiry_date - date '__D__') AS dte_opt,
           ob.close::float8 AS px, ob.oi::float8 AS oi,
           (g.id IS NOT NULL) AS has_g,
           g.iv::text AS iv_txt, g.gamma::text AS gamma_txt
      FROM sel s
      JOIN spt sp  ON sp.tname = s.tname
      JOIN fexp fe ON fe.tname = s.tname
      JOIN hist_option_bars_1m ob
        ON ob.instrument_id = '__IID__' AND ob.trade_date = date '__D__'
       AND ob.bar_ts = s.bar_ts AND ob.expiry_date = fe.expiry
      LEFT JOIN hist_option_greeks_1m g
        ON g.instrument_id = '__IID__' AND g.bar_ts = s.bar_ts
       AND g.strike = ob.strike AND g.option_type = ob.option_type
       AND g.expiry_date = ob.expiry_date
     WHERE abs(ob.strike::float8 / sp.spot - 1.0) <= 0.03
  ) t
) u ORDER BY tag, payload;
