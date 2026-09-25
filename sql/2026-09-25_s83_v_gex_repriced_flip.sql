-- =====================================================================
-- 2026-09-25_s83_v_gex_repriced_flip.sql
-- S83 / ENH-131 -- L3 repriced zero-gamma level (v_gex_repriced_flip)
-- =====================================================================
--
-- WHAT THIS IS
--   Parity spec L3 per ADR-025 B7: the REPRICED zero-gamma level. One
--   row per symbol at the LATEST option_chain_snapshots ts. The front
--   expiry chain is repriced with Black-Scholes gamma from each strike
--   own implied volatility, swept across spot, and the sign change of
--   TotalGEX nearest spot is published as flip.
--   18 columns, grain (symbol).
--
-- IT DOES NOT READ OR WRITE gamma_metrics.flip_level
--   ADR-025 B7. The existing scalar is computed by a cumulative walk
--   over VENDOR gamma in compute_gamma_metrics_local.py. This view
--   shares no code, no column and no input with it. The two numbers
--   are independent measurements of the same idea and may disagree;
--   nothing here reconciles them and nothing here overwrites them.
--
-- THE GATE RECORD, IN FULL, BECAUSE THREE OF FIVE FAILED
--   Gate 1  PASSED. It did NOT compare against gamma_metrics. It
--           REBUILT each strike stored gex_cr from gamma_call,
--           gamma_put, oi_call, oi_put and spot using
--           signed_gamma_exposure() verbatim, and matched to a max
--           per-strike abs diff of 1.1e-10 Cr and a relative diff of
--           at most 6.5e-15, on both symbols.
--   Gate 2  FAILED, and was MIS-SPECIFIED. It compared the repriced net
--           against the stored net at 1 pct and missed by 19.3 / 19.7
--           pct. Measured cause: net divided by gross is 0.0095 to
--           0.341 across arms, so a 2 to 4 pct GROSS error is amplified
--           into a 19 pct net error by cancellation. It scored the
--           cancellation, not the model. It stays FAILED.
--   Gate 3  FAILED, 1 of 3 arms. It required the nearest-spot crossing
--           to move less than 0.25 of a 1-day sigma across r in
--           {0, 0.065, 0.10} and T in three conventions. The spread was
--           r-driven on every arm: at fixed T the r spread was 31.6,
--           20.6 and 38.6 points against T spreads of 10.9, 12.2 and
--           1.0. Its clause (ii) was also MIS-SPECIFIED -- a plus or
--           minus 5 pct window could not see one arm full-grid count
--           change from 2 to 1.
--   Gate 4  FAILED, 1 of 4 arms. It replaced the arbitrary r set with a
--           single-cycle futures carry. Its clause (ii) was
--           UNDER-SPECIFIED: a plus or minus 0.01 band is about 19
--           times narrower than the measured cross-arm dispersion of
--           single-cycle carry, 0.020 to 0.209, so passing it measured
--           the band width rather than a pinned r.
--   Gate 5  PASSED 5 of 5, and is the basis for this view. Arms:
--           NIFTY 2026-09-24 15:20, SENSEX 2026-09-23 15:40,
--           NIFTY 2026-09-23 12:00, SENSEX 2026-09-22 12:00,
--           NIFTY 2026-09-18 12:00. r came from the SESSION MEDIAN of
--           per-cycle futures carry, which cut cross-arm dispersion
--           8.7-fold, from 0.188 to 0.0216. Every arm held its crossing
--           inside 0.25 sigma across the measured p10-to-p90 r band and
--           across three T conventions, every crossing was neg to pos,
--           and every arm had exactly one crossing within 2 sigma.
--
-- MEASURED S83, and each number shaped the design
--   * r_sess across the five arms: 0.0368 to 0.0584. Single-cycle carry
--     across the same arms: 0.0203 to 0.2087. The median is the whole
--     difference; the underlying futures price is a last trade, not a
--     quote, and a single cycle carries its noise.
--   * The per-session r band is wide where the horizon is short: p10 to
--     p90 spanned 0.335 on the 1-dte arm against 0.019 on the 4-dte
--     arm. Gate 5 clause (i) swept the full measured band and still
--     held inside 0.25 sigma, which is why the band is published.
--   * Repriced flip sat 0.15 to 0.76 sigma from spot across the arms.
--   * One arm carried its futures expiry on a different date from its
--     option front expiry. The r rule keys on the front-month FUTURE,
--     not on the option front, and that arm passed unchanged.
--   * The deep-ITM filter removed 31, 0, 32, 0 and 20 legs on the five
--     arms; iv of zero removed none on any arm.
--
-- TWO DELIBERATE CHOICES, each recorded rather than absorbed
--   1. STICKY-STRIKE. iv is held FIXED per strike across the whole
--      sweep. A real 10 pct spot move would move the smile. This
--      prices a parallel-shift world and says so.
--   2. THE R1 LEG SET IS FROZEN AT THE OBSERVED SPOT. The deep-ITM
--      filter guards against spurious VENDOR gamma; repricing uses BS
--      gamma, so re-applying the filter per sweep point would inject
--      artefact steps into the curve.
--
-- APPLY ORDER: Section 1 -> 2 -> 3 -> verify with Section 4.
-- RUN ONE STATEMENT AT A TIME (S72 Section 5).
-- SECTIONS 2 AND 3 ARE LIVE STATEMENTS so sql/ matches the database
-- (TD-S81-NEW-5: a body-only file is not a rebuild source).
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 4 -- the view
-- =====================================================================

CREATE OR REPLACE VIEW public.v_gex_repriced_flip AS
WITH RECURSIVE symbols AS (
        -- S72 FIX 2 skip scan. Symbols derived, never a literal list.
        SELECT (SELECT min(o.symbol) FROM option_chain_snapshots o) AS symbol
        UNION ALL
        SELECT (SELECT min(o.symbol)
                  FROM option_chain_snapshots o
                 WHERE o.symbol > s.symbol)
          FROM symbols s
         WHERE s.symbol IS NOT NULL
     ), latest AS (
        -- ADR-021 run scoping: one index seek per symbol through
        -- idx_ocs_ts_symbol_expiry (ts DESC, symbol, expiry_date).
        -- NOT max(ts) GROUP BY symbol. NEVER created_at: ingest reuses
        -- one snapshot_ts per cycle but created_at is a DB-side default
        -- and is later for the extra expiry pass, so ordering by it
        -- hands back W2 (S81, 89bc83e).
        SELECT s.symbol, lt.ts AS latest_ts
          FROM symbols s
          CROSS JOIN LATERAL (
               SELECT o.ts
                 FROM option_chain_snapshots o
                WHERE o.symbol = s.symbol
                ORDER BY o.ts DESC
                LIMIT 1
          ) lt
         WHERE s.symbol IS NOT NULL
     ), front AS (
        -- Front expiry = the nearest listed expiry IN THAT SNAPSHOT.
        -- Capture stage 1 holds W1 and W2; only W1 is repriced, so the
        -- comparison is like-for-like against a front-expiry net.
        SELECT l.symbol, l.latest_ts AS ts,
               min(o.expiry_date) AS front_expiry
          FROM latest l
          JOIN option_chain_snapshots o
            ON o.symbol = l.symbol AND o.ts = l.latest_ts
         GROUP BY l.symbol, l.latest_ts
     ), scoped AS (
        SELECT f.symbol, f.ts, f.front_expiry,
               o.strike, o.option_type, o.iv, o.oi, o.gamma, o.spot
          FROM front f
          JOIN option_chain_snapshots o
            ON o.symbol = f.symbol AND o.ts = f.ts
           AND o.expiry_date = f.front_expiry
     ), hdr AS (
        -- T is EXACT SECONDS to 15:30 IST on the front expiry, over a
        -- 365-day year. This is Gate 5 convention (b). dte 0 is NOT
        -- floored: S62 settled that expiry-day 0-DTE gamma exposure is
        -- numerically unreconstructible, so it is marked and skipped.
        SELECT s.symbol, s.ts, s.front_expiry,
               max(s.spot) AS spot,
               (s.front_expiry
                - (s.ts AT TIME ZONE 'Asia/Kolkata')::date) AS dte,
               (EXTRACT(epoch FROM
                  (((s.front_expiry + time '15:30') AT TIME ZONE 'Asia/Kolkata')
                   - s.ts)) / (365.0 * 86400.0))::double precision AS t_years
          FROM scoped s
         GROUP BY s.symbol, s.ts, s.front_expiry
     ), legs AS (
        -- R1 FROZEN LEG SET, evaluated once at the OBSERVED spot.
        -- iv > 0 is required because sigma is a divisor; it removed no
        -- leg on any of the five gate arms.
        SELECT s.symbol, s.ts,
               s.strike::double precision       AS k,
               s.option_type,
               (s.iv / 100.0)::double precision AS sigma,
               s.oi::double precision           AS oi
          FROM scoped s
          JOIN hdr h ON h.symbol = s.symbol AND h.ts = s.ts
         WHERE s.oi > 0
           AND s.gamma IS NOT NULL AND s.gamma <> 0
           AND s.iv > 0
           AND NOT (abs(s.strike - h.spot) / h.spot > 0.05
                    AND abs(s.gamma) > 5e-5)
     ), futwin AS (
        -- NO LOOK-AHEAD. Futures rows for this symbol from 09:20 IST on
        -- the ts date through ts INCLUSIVE. One index range scan per
        -- symbol through idx_index_futures_snapshots_symbol_ts.
        SELECT h.symbol, h.ts, i.ts AS fut_ts, i.expiry_date,
               i.futures_price, i.spot_price
          FROM hdr h
          JOIN index_futures_snapshots i
            ON i.symbol = h.symbol
           AND i.ts >= (((h.ts AT TIME ZONE 'Asia/Kolkata')::date
                         + time '09:20') AT TIME ZONE 'Asia/Kolkata')
           AND i.ts <= h.ts
         WHERE i.futures_price > 0 AND i.spot_price > 0
     ), futfront AS (
        -- Front-month FUTURE at ts, which is not always the option
        -- front expiry: min expiry on or after the IST date of ts.
        SELECT symbol, ts, min(expiry_date) AS fut_expiry
          FROM futwin
         WHERE expiry_date >= (ts AT TIME ZONE 'Asia/Kolkata')::date
         GROUP BY symbol, ts
     ), rrows AS (
        -- Per-cycle carry r_fut(t) = ln(F/S) / T_f, with T_f taken from
        -- THAT ROW OWN ts, not from the snapshot ts. F and S come from
        -- the same row, so the two are contemporaneous by construction.
        SELECT w.symbol, w.ts,
               ( ln(w.futures_price / w.spot_price)
                 / (EXTRACT(epoch FROM
                      (((w.expiry_date + time '15:30') AT TIME ZONE 'Asia/Kolkata')
                       - w.fut_ts)) / (365.0 * 86400.0))
               )::double precision AS r_fut
          FROM futwin w
          JOIN futfront f
            ON f.symbol = w.symbol AND f.ts = w.ts
           AND f.fut_expiry = w.expiry_date
         WHERE w.fut_ts < ((w.expiry_date + time '15:30')
                           AT TIME ZONE 'Asia/Kolkata')
     ), rstats AS (
        -- r_sess is the MEDIAN, and the p10-p90 band is published beside
        -- it because Gate 5 clause (i) is a sweep over that band, not a
        -- point estimate. Fewer than 6 rows is UNMEASURABLE, never
        -- substituted with a default.
        SELECT symbol, ts,
               count(*)::integer AS n_r_rows,
               percentile_cont(0.50) WITHIN GROUP (ORDER BY r_fut) AS r_sess,
               percentile_cont(0.10) WITHIN GROUP (ORDER BY r_fut) AS r_p10,
               percentile_cont(0.90) WITHIN GROUP (ORDER BY r_fut) AS r_p90
          FROM rrows
         GROUP BY symbol, ts
     ), atm AS (
        -- House ATM grid: round(spot / step) * step, step 50 for NIFTY
        -- and 100 for SENSEX, matching
        -- compute_volatility_metrics_local.py:86-88 and :624. This is a
        -- GRID strike and may not be listed; when it is not, atm_iv is
        -- NULL and sigma_1d is NULL rather than sliding to a neighbour.
        SELECT h.symbol, h.ts,
               round(h.spot
                     / (CASE WHEN h.symbol = 'NIFTY' THEN 50 ELSE 100 END))
                 * (CASE WHEN h.symbol = 'NIFTY' THEN 50 ELSE 100 END)
                 AS atm_strike
          FROM hdr h
     ), atmiv AS (
        -- NULLIF(iv, 0): a zero iv abstains. Same deviation recorded in
        -- the L9 view, for the same reason.
        SELECT q.symbol, q.ts, q.atm_strike,
               CASE WHEN q.ce_iv > 0 AND q.pe_iv > 0
                    THEN (q.ce_iv + q.pe_iv) / 2.0
               END AS atm_iv
          FROM (
            SELECT a.symbol, a.ts, a.atm_strike,
                   NULLIF(max(CASE WHEN s.option_type = 'CE' THEN s.iv END), 0)
                     AS ce_iv,
                   NULLIF(max(CASE WHEN s.option_type = 'PE' THEN s.iv END), 0)
                     AS pe_iv
              FROM atm a
              LEFT JOIN scoped s
                ON s.symbol = a.symbol AND s.ts = a.ts
               AND s.strike = a.atm_strike
             GROUP BY a.symbol, a.ts, a.atm_strike
          ) q
     ), base AS (
        SELECT h.symbol, h.ts, h.front_expiry, h.spot, h.dte, h.t_years,
               r.n_r_rows, r.r_sess, r.r_p10, r.r_p90,
               v.atm_iv,
               (h.spot * v.atm_iv / 100.0 * sqrt(1.0 / 365.0))::double precision
                 AS sigma_1d
          FROM hdr h
          LEFT JOIN rstats r ON r.symbol = h.symbol AND r.ts = h.ts
          LEFT JOIN atmiv  v ON v.symbol = h.symbol AND v.ts = h.ts
     ), evalset AS (
        -- Only rows that can carry a number reach the sweep. dte 0 and a
        -- thin r window drop out here and are labelled in status.
        SELECT b.symbol, b.ts, b.spot::double precision AS spot,
               b.t_years, b.r_sess
          FROM base b
         WHERE b.dte > 0 AND b.t_years > 0
           AND b.n_r_rows >= 6 AND b.r_sess IS NOT NULL
     ), grid AS (
        -- 201 points, 0.1 pct steps, plus or minus 10 pct of spot.
        SELECT e.symbol, e.ts, g.i,
               e.spot * (1.0 + (g.i - 100) * 0.001) AS s_grid
          FROM evalset e
          CROSS JOIN generate_series(0, 200) AS g(i)
     ), gexcurve AS (
        -- TotalGEX(S). gamma = n(d1) / (S sigma sqrt(T)),
        -- d1 = (ln(S/K) + (r + sigma^2 / 2) T) / (sigma sqrt(T)).
        -- Per leg: gamma * oi * S^2 / 1e7, PE negated, matching
        -- signed_gamma_exposure() exactly except that gamma is BS
        -- rather than vendor. Division by 1e7 is the Crore convention
        -- (TD-NEW-3).
        SELECT gr.symbol, gr.ts, gr.i, gr.s_grid,
               sum(
                 (CASE WHEN l.option_type = 'PE' THEN -1.0 ELSE 1.0 END)
                 * ( exp(-0.5 * power(
                       ( ln(gr.s_grid / l.k)
                         + (e.r_sess + 0.5 * power(l.sigma, 2)) * e.t_years )
                       / (l.sigma * sqrt(e.t_years)), 2))
                     / sqrt(2.0 * pi()) )
                   / (gr.s_grid * l.sigma * sqrt(e.t_years))
                 * l.oi * power(gr.s_grid, 2) / 1e7
               ) AS total_gex
          FROM grid gr
          JOIN evalset e ON e.symbol = gr.symbol AND e.ts = gr.ts
          JOIN legs   l  ON l.symbol = gr.symbol AND l.ts = gr.ts
         GROUP BY gr.symbol, gr.ts, gr.i, gr.s_grid
     ), adj AS (
        SELECT c.symbol, c.ts, c.s_grid, c.total_gex,
               lag(c.s_grid)    OVER (PARTITION BY c.symbol, c.ts
                                      ORDER BY c.i) AS prev_s,
               lag(c.total_gex) OVER (PARTITION BY c.symbol, c.ts
                                      ORDER BY c.i) AS prev_g
          FROM gexcurve c
     ), crossings AS (
        -- Linear interpolation between adjacent grid points, exactly as
        -- the gate script computed it.
        SELECT a.symbol, a.ts,
               a.prev_s + (a.s_grid - a.prev_s)
                        * (0.0 - a.prev_g) / (a.total_gex - a.prev_g)
                 AS s_star,
               CASE WHEN a.prev_g < 0 THEN 'neg->pos' ELSE 'pos->neg' END
                 AS flip_direction
          FROM adj a
         WHERE a.prev_g IS NOT NULL
           AND ((a.prev_g < 0) <> (a.total_gex < 0))
           AND a.total_gex <> a.prev_g
     ), counted AS (
        SELECT b.symbol, b.ts,
               count(x.s_star)::integer AS n_cross_full_grid,
               CASE WHEN b.sigma_1d IS NULL THEN NULL
                    ELSE count(x.s_star) FILTER (
                           WHERE abs(x.s_star - b.spot) <= 2.0 * b.sigma_1d
                         )::integer
               END AS n_cross_within_2sigma
          FROM base b
          LEFT JOIN crossings x ON x.symbol = b.symbol AND x.ts = b.ts
         GROUP BY b.symbol, b.ts, b.sigma_1d
     ), nearest AS (
        SELECT DISTINCT ON (x.symbol, x.ts)
               x.symbol, x.ts, x.s_star, x.flip_direction
          FROM crossings x
          JOIN base b ON b.symbol = x.symbol AND b.ts = x.ts
         ORDER BY x.symbol, x.ts, abs(x.s_star - b.spot)
     )
SELECT
    b.symbol,
    b.ts,
    b.spot,
    b.front_expiry,
    (b.t_years * 365.0)                          AS t_days,
    b.r_sess,
    b.r_p10,
    b.r_p90,
    COALESCE(b.n_r_rows, 0)                      AS n_r_rows,
    b.atm_iv,
    b.sigma_1d,
    n.s_star                                     AS flip,
    n.flip_direction,
    (n.s_star - b.spot)                          AS flip_minus_spot,
    CASE WHEN b.sigma_1d IS NULL OR b.sigma_1d = 0 THEN NULL
         ELSE (n.s_star - b.spot) / b.sigma_1d
    END                                          AS flip_sigma,
    c.n_cross_within_2sigma,
    c.n_cross_full_grid,
    -- Precedence is deliberate. S62 first: an expiry-day cycle is
    -- skipped whatever else is true of it.
    CASE WHEN b.dte = 0                 THEN 'SKIPPED_EXPIRY'
         WHEN COALESCE(b.n_r_rows, 0) < 6 THEN 'UNMEASURABLE_R'
         WHEN n.s_star IS NULL          THEN 'NO_CROSSING'
         ELSE 'OK'
    END                                          AS status
  FROM base b
  LEFT JOIN nearest n ON n.symbol = b.symbol AND n.ts = b.ts
  LEFT JOIN counted c ON c.symbol = b.symbol AND c.ts = b.ts;

-- =====================================================================
-- SECTION 2 of 4 -- comment (LIVE, not commented out -- TD-S81-NEW-5)
-- =====================================================================

COMMENT ON VIEW public.v_gex_repriced_flip IS
  'S83 / ENH-131 -- ADR-025 parity spec L3, the REPRICED zero-gamma level, per ADR-025 Amendment B clause B7. One row per symbol at the LATEST option_chain_snapshots ts. Grain (symbol). Consumers MUST ORDER BY symbol -- a view body carries no ordering guarantee. DISPLAY ONLY per the S37 GEX-as-context-not-gate ruling and TD-S79-NEW-15: it routes nothing, gates nothing, and makes NO PREDICTIVE CLAIM. Whether price is attracted to, repelled by, or indifferent to this level is UNMEASURED; the S74 holdout answered that question NO for the pin zone and left the acceleration zone unanswered, and nothing here revisits either. INDEPENDENT OF gamma_metrics.flip_level: this view neither reads nor writes that column. The existing scalar comes from a cumulative walk over VENDOR gamma inside compute_gamma_metrics_local.py; this level comes from a Black-Scholes repricing of the front chain. They share no code, no column and no input, they are two independent measurements of one idea, and they may disagree. Nothing here reconciles them and nothing here overwrites them. TD-S79-NEW-16 CONTEXT: the stored flip_level was measured sitting about three times closer to spot than the 0.54 sigma reference figure, while the repriced level measured 0.1 to 0.8 sigma from spot across the five gate arms. That is context for the disagreement, NOT a verdict that either is right. METHOD. The front expiry chain at that ts is repriced strike by strike with Black-Scholes gamma, d1 = (ln(S/K) + (r + sigma squared / 2) T) / (sigma sqrt T) and gamma = n(d1) / (S sigma sqrt T), each leg contributing gamma * oi * S squared / 1e7 with PE negated -- identical to signed_gamma_exposure() except that gamma is Black-Scholes rather than vendor. TotalGEX is swept over 201 points spanning plus or minus 10 pct of spot in 0.1 pct steps, sign changes are linearly interpolated between adjacent points, and flip is the crossing NEAREST SPOT. STICKY-STRIKE IS AN ASSUMPTION, NOT A NEUTRAL CHOICE: iv is held FIXED per strike across the entire sweep, so this prices a parallel-shift world, and a real 10 pct spot move would move the smile. THE LEG SET IS FROZEN at the observed spot -- oi above zero, vendor gamma non-zero, iv above zero, and the TD-NEW-2 deep-ITM guard (drop when distance from spot exceeds 5 pct AND absolute gamma exceeds 5e-5). That guard is NOT re-applied per sweep point: it exists to reject spurious VENDOR gamma, and re-applying it against Black-Scholes gamma would inject artefact steps into the curve. r IS THE SESSION-MEDIAN FUTURES CARRY, WITH NO LOOK-AHEAD. For each index_futures_snapshots row of the same symbol carrying the front-month FUTURE expiry -- the earliest futures expiry on or after the IST date of ts, which is NOT always the option front expiry -- carry is ln(futures_price / spot_price) divided by the exact time from THAT ROW OWN ts to 15:30 IST on the futures expiry over a 365-day year. The window runs from 09:20 IST on the ts date through ts INCLUSIVE, so no row after the snapshot is used. r_sess is the median over that window and r_p10 and r_p90 are its tenth and ninetieth percentiles. FEWER THAN SIX ROWS IS UNMEASURABLE_R with a NULL flip, never a substituted default (ADR-023 D1: fail to absent, never to stale). futures_price IS A LAST TRADE, NOT A QUOTE: index_futures_snapshots carries no bid or ask, its source tag names a last-traded-price feed, and the CLAUDE.md warning that a last trade is not an executable price applies. The median over a session is what makes it usable -- single-cycle carry measured 0.0203 to 0.2087 across the five gate arms while the session median measured 0.0368 to 0.0584, an 8.7-fold reduction in dispersion. T IS EXACT SECONDS from ts to 15:30 IST on the front expiry over a 365-day year, which is Gate 5 convention (b). DTE 0 IS SKIPPED, NEVER FLOORED: S62 settled that expiry-day 0-DTE gamma exposure is numerically unreconstructible, so such a cycle returns status SKIPPED_EXPIRY with a NULL flip rather than a number produced by a floored T. THE GATE RECORD, BECAUSE THREE OF FIVE FAILED AND THE FAILURES ARE PART OF WHAT THIS COLUMN MEANS. Gate 1 PASSED: it rebuilt each strike stored gex_cr from gamma_call, gamma_put, oi_call, oi_put and spot using signed_gamma_exposure() verbatim and matched to a max per-strike absolute difference of 1.1e-10 Cr and a relative difference of at most 6.5e-15, on both symbols. Gate 2 FAILED and was MIS-SPECIFIED: it compared the repriced NET against the stored net at 1 pct and missed by 19.3 and 19.7 pct, but net divided by gross measured 0.0095 to 0.341 across arms, so it amplified a 2 to 4 pct gross error into a 19 pct net error and scored the cancellation rather than the model. Gate 3 FAILED on 1 of 3 arms, its spread was r-driven on every arm with the fixed-T r spread at 31.6, 20.6 and 38.6 points against T spreads of 10.9, 12.2 and 1.0, and its second clause was mis-specified because a plus or minus 5 pct window could not see one arm full-grid crossing count change from 2 to 1. Gate 4 FAILED on 1 of 4 arms and its r band was UNDER-SPECIFIED, about 19 times narrower than the measured cross-arm dispersion of single-cycle carry, so passing it measured the band width rather than a pinned r. Gate 5 PASSED 5 of 5 on NIFTY 2026-09-24 15:20, SENSEX 2026-09-23 15:40, NIFTY 2026-09-23 12:00, SENSEX 2026-09-22 12:00 and NIFTY 2026-09-18 12:00 -- every arm held its nearest-spot crossing inside 0.25 of a 1-day sigma across the full measured p10-to-p90 r band and across three T conventions, every crossing ran negative to positive, and every arm carried exactly one crossing within 2 sigma. CAVEATS, EACH MEASURED. Gate 3b gross fidelity, the sum of absolute per-leg Black-Scholes minus vendor contribution over the sum of absolute vendor contribution, measured 3.4 pct, 10.9 pct and 4.7 pct, and it FAILED its 5 pct threshold on the SENSEX 1-dte arm at up to about 11 pct. A STABLE CROSSING IS NOT A REPRODUCED CURVE, and near expiry on SENSEX the curve is the least faithful. FAR-TAIL CROSSINGS BEYOND 2 SIGMA CAN BE UNSTABLE: one arm carried a second crossing at 9.4 pct of spot, roughly 17 sigma away, which appeared and disappeared with the T convention. n_cross_full_grid publishes that count so the instability stays visible; flip itself is always the crossing nearest spot, and n_cross_within_2sigma was 1 on every gate arm. sigma_1d = spot * atm_iv / 100 * sqrt(1 / 365), a calendar-day convention consistent with T. atm_iv USES THE HOUSE ATM GRID, round(spot / step) * step with step 50 for NIFTY and 100 for SENSEX, matching compute_volatility_metrics_local.py:86-88 and :624, averaging call and put iv with NULLIF(iv, 0) so a zero abstains -- the same deliberate deviation recorded in v_iv_term_structure. When that grid strike is not listed, atm_iv and sigma_1d are NULL and flip_sigma and n_cross_within_2sigma abstain rather than sliding to a neighbouring strike. STATUS values are OK, SKIPPED_EXPIRY, UNMEASURABLE_R and NO_CROSSING; flip is NULL on all but OK.';


-- =====================================================================
-- SECTION 3 of 4 -- privileges (LIVE -- TD-S81-NEW-5, CASE-2026-09-22)
-- REVOKE FIRST, then GRANT. S39 revoked instances and left Supabase
-- DEFAULT PRIVILEGES untouched, so every object created afterwards came
-- up with ALL again. Order matters.
-- =====================================================================

REVOKE ALL ON public.v_gex_repriced_flip FROM anon;

GRANT SELECT ON public.v_gex_repriced_flip TO anon;


-- =====================================================================
-- SECTION 4 of 4 -- verification (run after 1-3; each is a real check)
-- =====================================================================

-- V1  One row per symbol, and the status of each.
--     Would fail if: the latest-ts seek returned more than one ts per
--     symbol, or a symbol vanished from the skip scan.
-- SELECT symbol, ts, spot, front_expiry, round(t_days::numeric,4) AS t_days,
--        round(r_sess::numeric,6) AS r_sess, n_r_rows,
--        round(flip::numeric,2) AS flip, flip_direction,
--        round(flip_sigma::numeric,3) AS flip_sigma,
--        n_cross_within_2sigma, n_cross_full_grid, status
--   FROM public.v_gex_repriced_flip ORDER BY symbol;

-- V2  The view never touches gamma_metrics.flip_level (ADR-025 B7).
--     Expected: 0 rows. Fails if any dependency on that relation exists.
-- SELECT d.refobjid::regclass AS depends_on
--   FROM pg_depend d
--   JOIN pg_rewrite r ON r.oid = d.objid
--  WHERE r.ev_class = 'public.v_gex_repriced_flip'::regclass
--    AND d.refobjid::regclass::text = 'gamma_metrics'
--  GROUP BY 1;

-- V3  ANON PATH, not object existence. TD-S81-NEW-5: a GRANT skipped at
--     apply time leaves the view live and anon-unreadable, which returns
--     HTTP 200 with zero rows and is indistinguishable from no data.
--     Run AS anon. Expected: 2 rows (one per symbol).
-- SET ROLE anon; SELECT count(*) FROM public.v_gex_repriced_flip; RESET ROLE;

-- V4  COMMENT actually landed (a part-run apply is the S79 failure).
--     Expected: comment_len below matches the file.
-- SELECT length(obj_description('public.v_gex_repriced_flip'::regclass, 'pg_class'))
--          AS comment_len,
--        md5(obj_description('public.v_gex_repriced_flip'::regclass, 'pg_class'))
--          AS comment_md5;

-- V5  Latency. ADR-021: the whole point of run scoping. Expected well
--     under the PostgREST 8 s ceiling.
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_repriced_flip;
