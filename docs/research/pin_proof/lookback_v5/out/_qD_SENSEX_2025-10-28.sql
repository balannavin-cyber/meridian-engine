\pset format unaligned
\pset fieldsep '|'
\pset tuples_only on
-- lookback_v5 PART 3 -- per-(symbol, day) data pull. ONE symbol-day per query, ONE
-- statement, read-only, no temp table, no write.
-- Literals 73a1390a-30c9-46d6-9d3f-5f03c3f5ad71 SENSEX 2025-10-28 substituted by run_pull.sh (psql -v does not work
-- through bin/roq.sh).
--
-- bar_ts is IST clock labelled +00:00 (TD-029 family): every literal is written +00
-- and NEVER converted.
--
-- TARGETS: the 24 minutes 09:30, 09:45, ... 15:15 at second :59, EXACT bar only.
-- There is deliberately NO nearest-bar fallback: a minute with no bar at exactly
-- HH:MM:59 yields no R0 row, and the absence is the measurement. A +/-120 s probe
-- would turn "this minute is missing" into "this minute resolved 97 s away" and the
-- two would be indistinguishable downstream.
-- The targets are generated as TIMESTAMPTZ, not as time: generate_series has no
-- variant for the time type, so a time-based generator would not parse at all.
--
-- GRAIN. R0 one row per target minute THAT HAS A SPOT BAR; R1 one row per
-- front-expiry leg within +/-5 % of that minute's spot; R2 exactly one row for the
-- day. R0 is gated on the SPOT bar because spot is what the +/-5 % band is measured
-- from -- a minute with option bars but no spot bar has no band and is correctly
-- absent rather than banded against a spot borrowed from another minute.
--
-- front_expiry is a ONE-ROW ordered lookup on hist_option_bars_unique
-- (instrument_id, bar_ts, expiry_date, strike, option_type) -- the form ruled for
-- lookback_v4/sql/qB_opt_month.sql.tpl. With instrument_id and bar_ts fixed the index
-- already yields expiry_date in order, so ORDER BY ... LIMIT 1 reads one index tuple
-- and no aggregate is computed.
--
-- n_legs in R0 and the R1 rows are computed from the SAME predicate (the `legs` CTE),
-- so n_legs cannot drift from the number of R1 rows emitted. run_pull.sh gates every
-- day on sum(n_legs) = count(R1); that check is only meaningful because both sides
-- come from one definition rather than two.
--
-- INDEXED COLUMNS ONLY: filters are on instrument_id, bar_ts, expiry_date and strike.
-- trade_date is NOT used -- hist_option_bars_unique does not carry it, and bar_ts
-- pins the day exactly.
--
-- strike, px and oi are emitted as TEXT so that nothing is rounded by a float8 cast:
-- strike and oi are exact in the source (numeric / bigint) and close is numeric(10,2).
--
-- No outer ORDER BY (it would add a Sort for no gain); ordering is done by the reader.
WITH tgt AS (
  SELECT to_char(g.tts AT TIME ZONE 'UTC', 'HH24:MI') AS tname, g.tts
    FROM generate_series(timestamptz '2025-10-28 09:30:59+00',
                         timestamptz '2025-10-28 15:15:59+00',
                         interval '15 minutes') AS g(tts)
), spt AS (
  SELECT t.tname, t.tts, hs.close AS spot
    FROM tgt t
    JOIN hist_spot_bars_1m hs
      ON hs.instrument_id = '73a1390a-30c9-46d6-9d3f-5f03c3f5ad71'
     AND hs.bar_ts = t.tts
), fe AS (
  SELECT s.tname, s.tts, s.spot, f.front_expiry
    FROM spt s
    LEFT JOIN LATERAL (
      SELECT ob.expiry_date AS front_expiry
        FROM hist_option_bars_1m ob
       WHERE ob.instrument_id = '73a1390a-30c9-46d6-9d3f-5f03c3f5ad71'
         AND ob.bar_ts = s.tts
         AND ob.expiry_date >= date '2025-10-28'
       ORDER BY ob.expiry_date
       LIMIT 1
    ) f ON true
), legs AS (
  SELECT e.tname, ob.strike, ob.option_type, ob.close AS px, ob.oi
    FROM fe e
    JOIN hist_option_bars_1m ob
      ON ob.instrument_id = '73a1390a-30c9-46d6-9d3f-5f03c3f5ad71'
     AND ob.bar_ts = e.tts
     AND ob.expiry_date = e.front_expiry
     AND ob.strike >= e.spot * 0.95
     AND ob.strike <= e.spot * 1.05
   WHERE e.front_expiry IS NOT NULL
)
SELECT tag, payload FROM (
  SELECT 'R0' AS tag, row_to_json(t)::text AS payload FROM (
    SELECT 'SENSEX' AS sym, '2025-10-28' AS d, e.tname,
           e.spot::text AS spot,
           e.front_expiry::text AS front_expiry,
           (SELECT count(*) FROM legs l WHERE l.tname = e.tname) AS n_legs
      FROM fe e
  ) t
  UNION ALL
  SELECT 'R1', row_to_json(t)::text FROM (
    SELECT 'SENSEX' AS sym, '2025-10-28' AS d, l.tname,
           l.strike::text AS strike, l.option_type AS ot,
           l.px::text AS px, l.oi::text AS oi
      FROM legs l
  ) t
  UNION ALL
  -- R2: first and last spot bar of the session window, one row for the day.
  -- Two one-row LATERAL probes on idx_hist_spot_ts (instrument_id, bar_ts DESC);
  -- the window is 09:15:00 <= bar_ts < 15:31:00 so the 15:30:59-labelled bar is
  -- inside it, matching lookback_v4/sql/qA_spot_month.sql.tpl.
  SELECT 'R2', row_to_json(t)::text FROM (
    SELECT 'SENSEX' AS sym, '2025-10-28' AS d,
           to_char(a.bar_ts AT TIME ZONE 'UTC', 'HH24:MI:SS') AS first_clock,
           a.close::text AS first_close,
           to_char(z.bar_ts AT TIME ZONE 'UTC', 'HH24:MI:SS') AS last_clock,
           z.close::text AS last_close
      FROM (SELECT 1) one
      LEFT JOIN LATERAL (
        SELECT hs.bar_ts, hs.close
          FROM hist_spot_bars_1m hs
         WHERE hs.instrument_id = '73a1390a-30c9-46d6-9d3f-5f03c3f5ad71'
           AND hs.bar_ts >= timestamptz '2025-10-28 09:15:00+00'
           AND hs.bar_ts <  timestamptz '2025-10-28 15:31:00+00'
         ORDER BY hs.bar_ts
         LIMIT 1
      ) a ON true
      LEFT JOIN LATERAL (
        SELECT hs.bar_ts, hs.close
          FROM hist_spot_bars_1m hs
         WHERE hs.instrument_id = '73a1390a-30c9-46d6-9d3f-5f03c3f5ad71'
           AND hs.bar_ts >= timestamptz '2025-10-28 09:15:00+00'
           AND hs.bar_ts <  timestamptz '2025-10-28 15:31:00+00'
         ORDER BY hs.bar_ts DESC
         LIMIT 1
      ) z ON true
  ) t
) u;
