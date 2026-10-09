-- r24_score_rerun3.sql — S92 R2.4, three corrected anchors (F26, F37, F41): READ-ONLY. MERIDIAN values AS OF each parity-fixture's screenshot time.
-- Run in the Supabase SQL editor as one statement; export the result as JSON and paste/attach it.
-- Replays MERIDIAN's own rules as-of the anchor (the views are latest-only; ENH-134 as-of functions are not built):
--   gamma_metrics: latest run <= anchor, same IST date            -> spot, net_gex (Cr), regime, legacy flip_level, dte
--   gex_strike_snapshots: latest run <= anchor, same IST date,     -> leader / runner-up by |gex_cr| (v_gex_strike_rank rule),
--     front expiry of that run                                        top-5 by |gex_cr| with share_of_abs, HHI = sum(share^2)
--                                                                     (gex_cycle_history.conc_hhi rule), +/- peaks
--   walls: v_gex_strike_walls rule (OI argmax within band*sigma, sigma from the latest atm_iv <= run ts), CURRENT band params
WITH fx(fid, symbol, anchor) AS (VALUES
  ('F26', 'NIFTY', timestamptz '2026-07-17 15:30:59+05:30'),
  ('F37', 'NIFTY', timestamptz '2026-08-11 12:56:59+05:30'),
  ('F41', 'NIFTY', timestamptz '2026-08-27 12:16:59+05:30')
), gm AS (
  SELECT fx.fid, g.ts AS gm_ts, g.run_id AS gm_run_id, g.spot, g.net_gex, g.regime, g.flip_level, g.dte AS gm_dte
    FROM fx LEFT JOIN LATERAL (
      SELECT * FROM gamma_metrics g
       WHERE g.symbol = fx.symbol AND g.ts <= fx.anchor
         AND g.ts >= ((fx.anchor AT TIME ZONE 'Asia/Kolkata')::date::timestamp AT TIME ZONE 'Asia/Kolkata')
       ORDER BY g.ts DESC LIMIT 1) g ON true
), run AS (
  SELECT fx.fid, fx.symbol, r.run_id, r.ts
    FROM fx LEFT JOIN LATERAL (
      SELECT s.run_id, s.ts FROM gex_strike_snapshots s
       WHERE s.symbol = fx.symbol AND s.ts <= fx.anchor
         AND s.ts >= ((fx.anchor AT TIME ZONE 'Asia/Kolkata')::date::timestamp AT TIME ZONE 'Asia/Kolkata')
       ORDER BY s.ts DESC LIMIT 1) r ON true
), rows AS (
  SELECT run.fid, s.* FROM run
    JOIN gex_strike_snapshots s ON s.run_id = run.run_id AND s.symbol = run.symbol
), front AS (
  SELECT fid, min(expiry_date) AS expiry_date FROM rows GROUP BY fid
), fr AS (
  SELECT r.* FROM rows r JOIN front f ON f.fid = r.fid AND f.expiry_date = r.expiry_date
), tot AS (
  SELECT fid, sum(abs(gex_cr)) AS gross, sum(gex_cr) AS net_strike_sum, max(spot) AS spot, max(dte) AS dte,
         max(expiry_date) AS expiry_date, max(ts) AS ts
    FROM fr WHERE gex_cr IS NOT NULL GROUP BY fid
), ranked AS (
  SELECT fr.fid, fr.strike, fr.gex_cr, abs(fr.gex_cr) / NULLIF(t.gross, 0) AS share,
         row_number() OVER (PARTITION BY fr.fid ORDER BY abs(fr.gex_cr) DESC, fr.strike) AS rk
    FROM fr JOIN tot t ON t.fid = fr.fid WHERE fr.gex_cr IS NOT NULL
), agg AS (
  SELECT fid,
         max(strike) FILTER (WHERE rk = 1) AS leader,
         max(strike) FILTER (WHERE rk = 2) AS runner_up,
         round(sum(share) FILTER (WHERE rk <= 5) * 100, 1) AS top5_share_pct,
         round(sum(share * share), 4) AS hhi,
         round(max(share) * 100, 1) AS top1_share_pct,
         json_agg(json_build_object('strike', strike, 'share_pct', round(share * 100, 1), 'gex_cr', round(gex_cr, 0))
                  ORDER BY rk) FILTER (WHERE rk <= 5) AS top5
    FROM ranked GROUP BY fid
), peaks AS (
  SELECT fid,
         (array_agg(strike ORDER BY gex_cr DESC))[1] AS pos_peak,
         (array_agg(strike ORDER BY gex_cr ASC))[1]  AS neg_peak
    FROM fr WHERE gex_cr IS NOT NULL GROUP BY fid
), sig AS (
  SELECT t.fid, t.spot,
         COALESCE(get_parameter_num('wall.band.' || fx.symbol), 1.5) AS band,
         (t.spot * v.atm_iv_avg::numeric / 100.0 * sqrt(GREATEST(t.dte, 1)::numeric / 252.0)) AS sigma
    FROM tot t JOIN fx ON fx.fid = t.fid
    LEFT JOIN LATERAL (SELECT vs.atm_iv_avg FROM volatility_snapshots vs
                        WHERE vs.symbol = fx.symbol AND vs.ts <= t.ts AND vs.atm_iv_avg IS NOT NULL
                        ORDER BY vs.ts DESC LIMIT 1) v ON true
), walls AS (
  SELECT fr.fid,
         (array_agg(fr.strike ORDER BY fr.oi_call DESC) FILTER (WHERE fr.oi_call > 0))[1] AS call_wall,
         (array_agg(fr.strike ORDER BY fr.oi_put  DESC) FILTER (WHERE fr.oi_put  > 0))[1] AS put_wall
    FROM fr JOIN sig ON sig.fid = fr.fid
   WHERE sig.sigma > 0 AND abs(fr.strike - sig.spot) <= sig.band * sig.sigma
   GROUP BY fr.fid
)
SELECT fx.fid, fx.symbol, to_char(fx.anchor AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD HH24:MI') AS anchor_ist,
       to_char(gm.gm_ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS gm_ts_ist, gm.spot AS gm_spot,
       round(gm.net_gex, 0) AS net_gex_cr, gm.regime, gm.flip_level AS legacy_flip, gm.gm_dte,
       to_char(t.ts AT TIME ZONE 'Asia/Kolkata', 'HH24:MI:SS') AS gss_ts_ist, t.expiry_date, t.dte AS gss_dte, t.spot AS gss_spot,
       a.leader, a.runner_up, a.top1_share_pct, a.top5_share_pct, a.hhi, a.top5, p.pos_peak, p.neg_peak,
       w.call_wall, w.put_wall, round(sig.sigma, 1) AS wall_sigma
  FROM fx
  LEFT JOIN gm    ON gm.fid = fx.fid
  LEFT JOIN tot t ON t.fid = fx.fid
  LEFT JOIN agg a ON a.fid = fx.fid
  LEFT JOIN peaks p ON p.fid = fx.fid
  LEFT JOIN sig   ON sig.fid = fx.fid
  LEFT JOIN walls w ON w.fid = fx.fid
 ORDER BY fx.fid;
