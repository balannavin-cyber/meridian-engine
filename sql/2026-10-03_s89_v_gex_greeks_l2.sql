-- =====================================================================
-- 2026-10-03_s89_v_gex_greeks_l2.sql
-- S89 / ENH-98 -- ADR-025 parity L7 (vanna) and L8 (charm)
--   public.v_gex_greeks_l2_strike   grain (symbol, expiry_date, strike)
--   public.v_gex_greeks_l2_net      grain (symbol, expiry_date)
-- =====================================================================
--
-- S92 STATUS (2026-10-08) -- READ THIS FIRST
--   T1 PASSED 2026-10-07 (A5 arm; ENH-98 S91 block). The S89 block below
--   is kept as written and marked [SUPERSEDED S92] where it no longer holds.
--   Both COMMENT literals are restamped (rulings S92-C badge, S92-E D-4 as a
--   D3 deviation); V4's expected lengths are recomputed from this file.
--   View bodies, privileges and V1-V3, V5-V7 are UNCHANGED from S89.
--   STILL AUTHORED, NOT APPLIED: S90-A scoped the 2026-10-05 apply to
--   ENH-133 only, so these views have never existed. Read-only views,
--   S90-J "anything else" class -- apply any time.
--
-- AUTHORED, NOT APPLIED. S89, 2026-10-03 (Saturday, out of hours).
-- Application lands Monday 2026-10-05 >= 16:00 IST together with ENH-133.
--   [SUPERSEDED S92: it did not -- S90-A scoped that apply to ENH-133.]
-- Nothing in this file has been run against the database.
--
-- PROVISIONAL -- T1 PENDING 2026-10-07
--   [SUPERSEDED S92: T1 PASSED 2026-10-07; the kill below did not fire.
--    Badge is now "PROVISIONAL -- flow-vs-book (D-4) not built" (S92-C).]
--   ENH-98's own go/no-go, T1, is UNDECIDED (S86). The pair verdict needs
--   the SENSEX dte-1 re-run at Wed 2026-10-07 10:15:59 IST under the
--   TD-S86-NEW-9 ruling of 2026-10-03 (precondition gates offset/r_eff
--   only; gamma counts on ATM rows >= 10). THESE VIEWS ARE DISPLAY-ONLY
--   AND BADGED "PROVISIONAL -- T1 pending 10-07" ON EVERY SURFACE.
--   PRE-COMMITTED KILL: if 10-07 refuses T1 (exact/365 median
--   gamma_relerr > 0.10 at BOTH ATM and NEAR), both views are DROPped and
--   L7/L8 return to their prior disposition. The kill is agreed before the
--   measurement, so a refusal cannot be renegotiated into a caveat.
--
-- WHAT THIS IS
--   The second-order greek layer ADR-002 v2 P8 specifies and ADR-025
--   lists as L7 and L8. Four per-strike constructs, per OPERATOR RULING
--   L78-1 (compute BOTH the textbook delta-derivatives AND the parity
--   target's gamma-derivatives; each under a distinct name; NEITHER
--   labelled plain "vanna" or "charm"):
--
--     delta_drift_iv_cr_per_volpt    d(delta)/d(sigma)  -- textbook vanna
--     delta_drift_time_cr_per_day    d(delta)/d(t)      -- textbook charm
--     gex_drift_iv_cr_per_volpt      d(gamma)/d(sigma)  -- the dGamma construct
--     gex_drift_time_cr_per_day      d(gamma)/d(t)      -- the dGamma construct
--
-- METHOD IS ANALYTIC BLACK-SCHOLES, NOT A FINITE DIFFERENCE
--   Stated because the obvious alternative is wrong here. ENH-131
--   (v_gex_repriced_flip) already sweeps TotalGEX over a 201-point spot
--   grid, so it is tempting to difference that grid. These views do NOT.
--   The ENH-131 grid sweeps SPOT at fixed sigma and fixed T -- it carries
--   no sigma axis and no t axis, so neither d/d(sigma) nor d/d(t) can be
--   read off it at all. Differencing it would answer a different question.
--   Every quantity below is the CLOSED-FORM derivative, evaluated once at
--   the observed spot.
--
-- IT SHARES ENH-131'S INPUTS EXACTLY, AND THAT IS DELIBERATE
--   Same leg set, same r, same T, same Crore convention, same deep-ITM
--   guard, same latest-ts run scoping. L3 and L7/L8 are then reconcilable
--   by construction: a disagreement between them is a disagreement about
--   the derivative, never about which chain was priced.
--
-- FORMULAE (q = 0; recorded because the code must be checkable against
-- the docstring -- CLAUDE.md Rule 0a control 2)
--   d1    = (ln(S/K) + (r + sigma^2/2) T) / (sigma sqrt(T))
--   d2    = d1 - sigma sqrt(T)
--   n(d1) = exp(-d1^2/2) / sqrt(2 pi)
--   Gamma = n(d1) / (S sigma sqrt(T))
--   dd1/dT = (r + sigma^2/2)/(sigma sqrt(T)) - d1/(2T)
--
--   d(delta)/d(sigma) = -n(d1) d2 / sigma                 [per 1.00 sigma]
--   d(delta)/dt       = -n(d1) * dd1/dT                   [per year]
--   d(gamma)/d(sigma) = Gamma (d1 d2 - 1) / sigma         [per 1.00 sigma]
--   d(gamma)/dt       = Gamma (d1 * dd1/dT + 1/(2T))      [per year]
--
--   q = 0 MEANS CALL AND PUT CARRY THE SAME SECOND-ORDER GREEK at a
--   strike. The CE/PE distinction enters ONLY through the dealer sign
--   and through oi. That is why the sign convention below is load-bearing
--   and is stated rather than inherited.
--
-- UNITS, STATED EXPLICITLY BECAUSE AN IMPLICIT UNIT IS THE DEFECT
-- (TD-NEW-3 cost this system a 100x error; Rule 14 cost it another)
--   _cr_per_volpt  = <per-contract derivative> / 100 * oi * S   / 1e7
--                    "rupees crore of DEALER DELTA-NOTIONAL (or of GEX,
--                     for the dGamma pair) gained per +1 IMPLIED-VOL
--                     POINT", i.e. per +0.01 of sigma, NOT per 1.00.
--   _cr_per_day    = <per-contract derivative> / 365 * oi * S   / 1e7
--                    "... per ONE CALENDAR DAY of time passing".
--                    365, not 252: calendar decay including weekends,
--                    per OPERATOR RULING L78-3, and consistent with the
--                    exact/365 T convention used throughout.
--   The DELTA pair scales by oi * S / 1e7 (delta-notional crore, per
--   L78-1). The GAMMA pair scales by oi * S^2 / 1e7 -- one power of S
--   higher, which is signed_gamma_exposure()'s own Crore convention, so
--   the dGamma pair is in the same unit as gex_cr per unit of sigma / time.
--
-- SIGN CONVENTION, STATED AND TESTABLE
--   PE legs are NEGATED, exactly as signed_gamma_exposure() negates them.
--   This carries the standard dealer assumption (long calls, short puts)
--   into the second-order layer unchanged. It is NOT a sign flip applied
--   to an already-signed delta: with q = 0 the second-order greeks are
--   IDENTICAL for call and put, so the negation is the whole of the
--   dealer-side assumption and nothing else. Verification V6 asserts the
--   call/put equality the claim rests on.
--
-- DTE 0 IS SKIPPED, NEVER FLOORED -- MEASURED, NOT INHERITED
--   S62 settled that expiry-day gamma is numerically unreconstructible
--   and ENH-131 skips dte 0 on that authority. L7/L8 skip it on their own
--   evidence as well, because the time-derivatives are worse than gamma:
--   both carry 1/(2T) and both diverge as T -> 0. MEASURED at the 10:15
--   cycle (S89, four sessions):
--     net d(delta)/dt   SENSEX dte 2  -1,820 Cr/day
--                              dte 1 -23,744 Cr/day   (13x)
--                              dte 0 -156,855 Cr/day  (86x dte 2)
--     net d(gamma)/dt   SENSEX dte 0  -4,951,550 Cr/day
--   A "per calendar day" rate published with 0.222 days left to run is
--   not a small number badly estimated; it is an instantaneous derivative
--   extrapolated over a horizon that does not exist. The d1 control
--   agrees independently: median |BS delta - vendor delta| inside the
--   [0.05, 0.95] band reads 0.0031-0.0185 at dte 1-12 and 0.0643 at
--   dte 0 -- a 7-20x degradation at the one dte that is skipped.
--   On dte 0 the four value columns are NULL and status is
--   SKIPPED_EXPIRY. Per L78-3 the W1 expiry-day leg would be COMPUTED
--   AND RECORDED BUT NOT DISPLAYED -- and E1 (S85) and E2 (S87) BOTH
--   REFUSED, so that leg stays UNRECORDED and is not built here.
--
-- THE SESSION GATE IS CUTOFF-AWARE AND MATERIALIZED, AND BOTH WORDS WERE
-- EARNED BY AN EXPLAIN (ADR-021)
--   is_trading_session = (count(DISTINCT spot) > 1) over the rows of THIS
--   symbol from 00:00 IST on the ts date THROUGH ts INCLUSIVE -- the
--   ENH-133 D-3 clause 3 gate, cut off at ts so it carries no look-ahead.
--   Write-and-flag: the row is published either way and the consumer
--   filters. 2026-10-02 (Gandhi Jayanti) is why: 83 distinct ts and
--   79,680 NIFTY rows -- it passes a row count and a distinct-ts count
--   (TD-S89-NEW-1) and fails only on distinct_spot = 1.
--   THE CTE IS `AS MATERIALIZED` AND JOINED ON (symbol, ts). Three gate
--   shapes were measured against each other on a TWO-CONSTRUCT PRECURSOR
--   of this body -- same scoping, same legs, same data, two of the four
--   value columns. The comparison is between the three shapes; it is NOT
--   a timing of the view below, and is recorded as the precursor's:
--     gate as a plain CTE grouped off a day window   11,040 ms  (seq scan)
--     gate as a correlated subquery, un-materialized 26,424 ms  (490 loops)
--     gate AS MATERIALIZED, joined on (symbol, ts)      164 ms
--   The first two are over the PostgREST 8 s ceiling -- the exact ADR-021
--   failure, reproduced inside this file's own first draft. The keyword is
--   load-bearing, not stylistic; removing it reverts a sub-second view to
--   a 26 s one that returns HTTP 500 and reads as "no data".
--   THE BODY BELOW, measured on its own 2026-10-03 pre-apply, as an inline
--   query (no object was created), TWICE, because one timing on a shared
--   instance is a sample and not a figure: strike 210.280 then 186.476 ms,
--   net 157.714 then 191.610 ms, 4 net rows both times. The spread is
--   run-to-run variance; every reading is ~40x under the 8 s ceiling, so
--   the verdict does not turn on which one is quoted.
--   The `.claude/rules/sql-views.md` obligation is DISCHARGED, not assumed:
--   `CTE Scan on gate g` reports `loops=1` in both plans, so the
--   MATERIALIZED hint demonstrably took. Plans: scratch/s89_l78/explain_plans.txt.
--
-- R AND T COME FROM ENH-131 VERBATIM, AND R BARELY MATTERS HERE
--   r = session-median futures carry from 09:20 IST to ts inclusive, no
--   look-ahead, n >= 6 or UNMEASURABLE_R. T = exact seconds to 15:30 IST
--   on the expiry over a 365-day year.
--   MEASURED, and it is the opposite of the L3 result: sweeping r across
--   {0, 0.037, 0.065, 0.10, 0.12} -- wider than any dispersion this system
--   has measured -- moves SENSEX dte 1 net d(delta)/dt by 0.22 % and net
--   d(delta)/d(sigma) by 0.50 %; NIFTY dte 5 by 7.6 % and 2.0 %. The r
--   convention that failed Gates 3 and 4 for L3 is NOT the sensitive axis
--   for L7/L8.
--   T IS. Across exact/365, dte/365 and dte/252 on the same rows:
--     SENSEX dte 2 net d(delta)/dt  -1,150 / -1,760 / -2,746 Cr/day (2.4x)
--     SENSEX dte 1 net d(delta)/dt -25,688 / -23,718 / -22,046 Cr/day
--     NIFTY  dte 5 net d(delta)/dIV  4,806 /   4,917 /   5,737 Cr/volpt
--   exact/365 is chosen because it is the convention T1 is written on and
--   the one ENH-98 has measured lowest-error at every dte except dte 1,
--   where S86 observation (b) found dte/252 better by ~10x on gamma and
--   recorded it WITHOUT changing T1. That observation is NOT acted on
--   here: changing the convention after seeing which arm it favours is
--   the fitting the pre-registration exists to prevent. If the 10-07 arm
--   re-opens the convention, these views change with T1 and not before.
--
-- NET VS GROSS -- THE TWO PAIRS BEHAVE DIFFERENTLY AND BOTH ARE PUBLISHED
--   Gate 2 of ENH-131 FAILED because it scored a cancellation. Measured
--   here, |net| / gross-of-per-strike-nets over eight arms, per construct:
--     d(delta)/d(sigma)  0.844 to 1.000   (min: SENSEX dte 2)
--     d(delta)/dt        0.957 to 1.000 on 7 of 8; SENSEX dte 2 is 0.181
--     d(gamma)/d(sigma)  0.008 to 0.384
--     d(gamma)/dt        0.092 to 0.376
--   So the DELTA pair's net is meaningfully signed and is very nearly the
--   gross -- structurally, because d2 changes sign at the money and
--   (oi_call - oi_put) changes sign with it, so the two sign flips cancel
--   and every strike contributes the same way. The GAMMA pair's net is a
--   small residue of large opposing terms and MUST NOT be read alone.
--   Both views publish gross beside net for all four constructs, and the
--   net view publishes net_over_gross so the reader can see which case
--   they are in without computing it.
--
-- DISPLAY ONLY. Routes nothing, gates nothing, predicts nothing. The S37
-- GEX-as-context-not-gate ruling and TD-S79-NEW-15 apply unchanged.
--
-- APPLY ORDER: Section 1 -> 2 -> 3 -> 4 -> 5, verify with Section 6.
-- RUN ONE STATEMENT AT A TIME (S72 Section 5).
-- SECTIONS 3 AND 4 ARE LIVE STATEMENTS so sql/ matches the database
-- (TD-S81-NEW-5: a body-only file is not a rebuild source; a part-run
-- apply that skips the GRANT leaves the view anon-unreadable at HTTP 200
-- with zero rows, which is indistinguishable from no data).
-- =====================================================================


-- =====================================================================
-- SECTION 1 of 6 -- the per-strike view (L7/L8 grain)
-- =====================================================================

CREATE OR REPLACE VIEW public.v_gex_greeks_l2_strike AS
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
        -- idx_ocs_ts_symbol_expiry. NOT max(ts) GROUP BY symbol.
        -- NEVER created_at (S81, 89bc83e -- it hands back W2).
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
     ), scoped AS (
        -- BOTH expiry legs, unlike ENH-131 which keeps the front only.
        -- L78-3 requires W2 to compute as normal on expiry day. Capture
        -- stage 1 holds exactly W1 and W2; the MONTHLIES L78-3 also names
        -- ARE NOT CAPTURED (measured: n_expiry = 2 on every session
        -- 09-28..10-02, both symbols) and therefore cannot appear here.
        SELECT l.symbol, l.latest_ts AS ts,
               o.expiry_date, o.strike, o.option_type,
               o.iv, o.oi, o.gamma, o.spot
          FROM latest l
          JOIN option_chain_snapshots o
            ON o.symbol = l.symbol AND o.ts = l.latest_ts
     ), hdr AS (
        -- T is EXACT SECONDS to 15:30 IST on the expiry over a 365-day
        -- year -- ENH-131's convention, Gate 5 convention (b).
        SELECT s.symbol, s.ts, s.expiry_date,
               max(s.spot) AS spot,
               (s.expiry_date
                - (s.ts AT TIME ZONE 'Asia/Kolkata')::date) AS dte,
               (EXTRACT(epoch FROM
                  (((s.expiry_date + time '15:30') AT TIME ZONE 'Asia/Kolkata')
                   - s.ts)) / (365.0 * 86400.0))::double precision AS t_years
          FROM scoped s
         GROUP BY s.symbol, s.ts, s.expiry_date
     ), gate AS MATERIALIZED (
        -- ENH-133 D-3 clause 3, cut off at ts so there is no look-ahead.
        -- AS MATERIALIZED is load-bearing: see the header, 164 ms vs
        -- 26,424 ms on the two-construct precursor. Join is on
        -- (symbol, ts). This body measures 210.280 / 186.476 ms pre-apply,
        -- with `CTE Scan on gate g` at loops=1 in both plans.
        SELECT h.symbol, h.ts,
               (SELECT count(DISTINCT o2.spot) > 1
                  FROM option_chain_snapshots o2
                 WHERE o2.symbol = h.symbol
                   AND o2.ts >= ((((h.ts AT TIME ZONE 'Asia/Kolkata')::date)
                                  ::timestamp) AT TIME ZONE 'Asia/Kolkata')
                   AND o2.ts <= h.ts) AS is_trading_session
          FROM (SELECT DISTINCT symbol, ts FROM hdr) h
     ), futwin AS (
        -- NO LOOK-AHEAD. 09:20 IST on the ts date through ts INCLUSIVE.
        SELECT DISTINCT h.symbol, h.ts, i.ts AS fut_ts, i.expiry_date,
               i.futures_price, i.spot_price
          FROM (SELECT DISTINCT symbol, ts FROM hdr) h
          JOIN index_futures_snapshots i
            ON i.symbol = h.symbol
           AND i.ts >= (((h.ts AT TIME ZONE 'Asia/Kolkata')::date
                         + time '09:20') AT TIME ZONE 'Asia/Kolkata')
           AND i.ts <= h.ts
         WHERE i.futures_price > 0 AND i.spot_price > 0
     ), futfront AS (
        -- Front-month FUTURE, which is not always the option front.
        SELECT symbol, ts, min(expiry_date) AS fut_expiry
          FROM futwin
         WHERE expiry_date >= (ts AT TIME ZONE 'Asia/Kolkata')::date
         GROUP BY symbol, ts
     ), rrows AS (
        -- Per-cycle carry, T_f from THAT ROW's own ts. F and S are from
        -- the same row, so they are contemporaneous by construction.
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
        -- Fewer than 6 rows is UNMEASURABLE, never a substituted default
        -- (ADR-023 D1: fail to absent, never to stale).
        SELECT symbol, ts,
               count(*)::integer AS n_r_rows,
               percentile_cont(0.50) WITHIN GROUP (ORDER BY r_fut) AS r_sess
          FROM rrows
         GROUP BY symbol, ts
     ), legs AS (
        -- ENH-131's leg set, byte-for-byte in its predicates: oi above
        -- zero, vendor gamma non-zero, iv above zero, and the TD-NEW-2
        -- deep-ITM guard. The guard rejects spurious VENDOR gamma; it is
        -- kept so L3 and L7/L8 price the SAME legs and remain reconcilable.
        SELECT s.symbol, s.ts, s.expiry_date,
               h.spot, h.dte, h.t_years,
               r.r_sess, COALESCE(r.n_r_rows, 0) AS n_r_rows,
               s.strike::double precision       AS k,
               (CASE WHEN s.option_type = 'PE' THEN -1.0 ELSE 1.0 END)
                                                AS sgn,
               (s.iv / 100.0)::double precision AS sigma,
               s.oi::double precision           AS oi
          FROM scoped s
          JOIN hdr h
            ON h.symbol = s.symbol AND h.ts = s.ts
           AND h.expiry_date = s.expiry_date
          LEFT JOIN rstats r ON r.symbol = s.symbol AND r.ts = s.ts
         WHERE s.oi > 0
           AND s.gamma IS NOT NULL AND s.gamma <> 0
           AND s.iv > 0
           AND NOT (abs(s.strike - h.spot) / h.spot > 0.05
                    AND abs(s.gamma) > 5e-5)
     ), evalleg AS (
        -- Only legs that can carry a number reach the arithmetic. dte 0
        -- and a thin r window drop out here and are labelled in status.
        SELECT l.*
          FROM legs l
         WHERE l.dte > 0 AND l.t_years > 0
           AND l.n_r_rows >= 6 AND l.r_sess IS NOT NULL
     ), bs AS (
        SELECT e.*,
               ( ln(e.spot / e.k)
                 + (e.r_sess + 0.5 * power(e.sigma, 2)) * e.t_years )
               / (e.sigma * sqrt(e.t_years))                   AS d1
          FROM evalleg e
     ), bs2 AS (
        SELECT b.*,
               b.d1 - b.sigma * sqrt(b.t_years)                AS d2,
               exp(-0.5 * power(b.d1, 2)) / sqrt(2.0 * pi())   AS nd1,
               (b.r_sess + 0.5 * power(b.sigma, 2))
                 / (b.sigma * sqrt(b.t_years))
                 - b.d1 / (2.0 * b.t_years)                    AS dd1_dt
          FROM bs b
     ), bs3 AS (
        SELECT b.*,
               b.nd1 / (b.spot * b.sigma * sqrt(b.t_years))    AS bs_gamma
          FROM bs2 b
     ), perleg AS (
        -- The four constructs, scaled to their stated units. /100 is the
        -- per-IV-POINT step; /365 is the per-CALENDAR-DAY step; /1e7 is
        -- the Crore convention (TD-NEW-3). The delta pair carries one
        -- power of spot, the gamma pair two -- matching gex_cr.
        SELECT b.symbol, b.ts, b.expiry_date, b.dte, b.spot, b.k,
               b.sgn * ((-b.nd1 * b.d2 / b.sigma) / 100.0)
                     * b.oi * b.spot / 1e7            AS leg_delta_drift_iv,
               b.sgn * ((-b.nd1 * b.dd1_dt) / 365.0)
                     * b.oi * b.spot / 1e7            AS leg_delta_drift_time,
               b.sgn * ((b.bs_gamma * (b.d1 * b.d2 - 1.0) / b.sigma) / 100.0)
                     * b.oi * power(b.spot, 2) / 1e7  AS leg_gex_drift_iv,
               b.sgn * ((b.bs_gamma * (b.d1 * b.dd1_dt
                                       + 1.0 / (2.0 * b.t_years))) / 365.0)
                     * b.oi * power(b.spot, 2) / 1e7  AS leg_gex_drift_time
          FROM bs3 b
     ), agg AS (
        SELECT symbol, ts, expiry_date, dte, spot, k,
               count(*)::integer           AS n_legs,
               sum(leg_delta_drift_iv)     AS delta_drift_iv_cr_per_volpt,
               sum(leg_delta_drift_time)   AS delta_drift_time_cr_per_day,
               sum(leg_gex_drift_iv)       AS gex_drift_iv_cr_per_volpt,
               sum(leg_gex_drift_time)     AS gex_drift_time_cr_per_day,
               sum(abs(leg_delta_drift_iv))   AS gross_delta_drift_iv,
               sum(abs(leg_delta_drift_time)) AS gross_delta_drift_time,
               sum(abs(leg_gex_drift_iv))     AS gross_gex_drift_iv,
               sum(abs(leg_gex_drift_time))   AS gross_gex_drift_time
          FROM perleg
         GROUP BY symbol, ts, expiry_date, dte, spot, k
     )
SELECT
    h.symbol,
    h.ts,
    h.expiry_date,
    h.dte,
    h.spot,
    a.k                                          AS strike,
    g.is_trading_session,
    (h.t_years * 365.0)                          AS t_days,
    rr.r_sess,
    COALESCE(rr.n_r_rows, 0)                     AS n_r_rows,
    a.n_legs,
    a.delta_drift_iv_cr_per_volpt,
    a.delta_drift_time_cr_per_day,
    a.gex_drift_iv_cr_per_volpt,
    a.gex_drift_time_cr_per_day,
    a.gross_delta_drift_iv,
    a.gross_delta_drift_time,
    a.gross_gex_drift_iv,
    a.gross_gex_drift_time,
    -- Precedence is deliberate and matches ENH-131: an expiry-day cycle
    -- is skipped whatever else is true of it.
    CASE WHEN h.dte = 0                       THEN 'SKIPPED_EXPIRY'
         WHEN COALESCE(rr.n_r_rows, 0) < 6    THEN 'UNMEASURABLE_R'
         WHEN a.k IS NULL                     THEN 'NO_LEGS'
         ELSE 'OK'
    END                                          AS status
  FROM hdr h
  LEFT JOIN rstats rr ON rr.symbol = h.symbol AND rr.ts = h.ts
  LEFT JOIN gate   g  ON g.symbol  = h.symbol AND g.ts  = h.ts
  LEFT JOIN agg    a  ON a.symbol  = h.symbol AND a.ts  = h.ts
                     AND a.expiry_date = h.expiry_date;


-- =====================================================================
-- SECTION 2 of 6 -- the net view (one row per symbol and expiry leg)
-- =====================================================================

CREATE OR REPLACE VIEW public.v_gex_greeks_l2_net AS
SELECT
    s.symbol,
    s.ts,
    s.expiry_date,
    max(s.dte)                                   AS dte,
    max(s.spot)                                  AS spot,
    bool_and(s.is_trading_session)               AS is_trading_session,
    max(s.t_days)                                AS t_days,
    max(s.r_sess)                                AS r_sess,
    max(s.n_r_rows)                              AS n_r_rows,
    count(s.strike)::integer                     AS n_strikes,
    COALESCE(sum(s.n_legs), 0)::integer          AS n_legs,
    sum(s.delta_drift_iv_cr_per_volpt)           AS net_delta_drift_iv_cr_per_volpt,
    sum(s.delta_drift_time_cr_per_day)           AS net_delta_drift_time_cr_per_day,
    sum(s.gex_drift_iv_cr_per_volpt)             AS net_gex_drift_iv_cr_per_volpt,
    sum(s.gex_drift_time_cr_per_day)             AS net_gex_drift_time_cr_per_day,
    -- GROSS at the PER-STRIKE denominator: the sum of absolute per-strike
    -- nets, so CE/PE cancellation inside a strike has already happened.
    -- This is the denominator the net_over_gross ratios below use, and it
    -- is NOT the per-LEG gross carried on the strike view. Two different
    -- denominators, both published, neither implied.
    sum(abs(s.delta_drift_iv_cr_per_volpt))      AS gross_strike_delta_drift_iv,
    sum(abs(s.delta_drift_time_cr_per_day))      AS gross_strike_delta_drift_time,
    sum(abs(s.gex_drift_iv_cr_per_volpt))        AS gross_strike_gex_drift_iv,
    sum(abs(s.gex_drift_time_cr_per_day))        AS gross_strike_gex_drift_time,
    -- Published so no consumer has to decide whether a net is a signal or
    -- a cancellation residue. ENH-131 Gate 2 failed for want of this.
    sum(s.delta_drift_iv_cr_per_volpt)
      / NULLIF(sum(abs(s.delta_drift_iv_cr_per_volpt)), 0)
                                                 AS net_over_gross_delta_drift_iv,
    sum(s.delta_drift_time_cr_per_day)
      / NULLIF(sum(abs(s.delta_drift_time_cr_per_day)), 0)
                                                 AS net_over_gross_delta_drift_time,
    sum(s.gex_drift_iv_cr_per_volpt)
      / NULLIF(sum(abs(s.gex_drift_iv_cr_per_volpt)), 0)
                                                 AS net_over_gross_gex_drift_iv,
    sum(s.gex_drift_time_cr_per_day)
      / NULLIF(sum(abs(s.gex_drift_time_cr_per_day)), 0)
                                                 AS net_over_gross_gex_drift_time,
    max(s.status)                                AS status
  FROM public.v_gex_greeks_l2_strike s
 GROUP BY s.symbol, s.ts, s.expiry_date;


-- =====================================================================
-- SECTION 3 of 6 -- comments (LIVE, not commented out -- TD-S81-NEW-5)
-- =====================================================================

COMMENT ON VIEW public.v_gex_greeks_l2_strike IS
  'S89 / ENH-98 -- ADR-025 parity L7 (vanna) and L8 (charm), per-strike. Grain (symbol, expiry_date, strike) at the LATEST option_chain_snapshots ts, BOTH captured expiry legs. Consumers MUST ORDER BY -- a view body carries no ordering guarantee. PROVISIONAL -- flow-vs-book (D-4) not built. T1 PASSED 2026-10-07 on the A5 arm (SENSEX dte 1, cycle 10:15:59 IST; exact/365 median gamma_relerr ATM 0.0716, NEAR 0.0369; ATM rows 28 >= 10), against a pre-registration hashed before the read; the S89 pre-committed DROP therefore did not fire. The flow-vs-book classification ruled into L7/L8 scope (D-4) needs a previous-close OI baseline (PPC-1) and is recorded as an ADR-025 D3 deviation, deferred post-parity (ruling S92-E). Every surface rendering this view MUST carry the badge "PROVISIONAL -- flow-vs-book (D-4) not built" (ruling S92-C). DISPLAY ONLY per the S37 GEX-as-context-not-gate ruling and TD-S79-NEW-15: it routes nothing, gates nothing, and makes NO PREDICTIVE CLAIM. FOUR CONSTRUCTS, per OPERATOR RULING L78-1, which requires BOTH the textbook delta-derivatives AND the parity target dGamma constructs, each under a distinct name, and NEITHER labelled plain vanna or charm. delta_drift_iv_cr_per_volpt is d(delta)/d(sigma); delta_drift_time_cr_per_day is d(delta)/dt; gex_drift_iv_cr_per_volpt is d(gamma)/d(sigma); gex_drift_time_cr_per_day is d(gamma)/dt. METHOD IS ANALYTIC BLACK-SCHOLES, NOT A FINITE DIFFERENCE OFF THE ENH-131 GRID. Stated because that is the tempting wrong answer: ENH-131 sweeps SPOT at fixed sigma and fixed T, so it carries neither a sigma axis nor a t axis and NEITHER derivative can be read off it. Every quantity here is the closed form evaluated once at the observed spot. With q = 0: d1 = (ln(S/K) + (r + sigma squared / 2) T) / (sigma sqrt T), d2 = d1 - sigma sqrt T, n(d1) = exp(-d1 squared / 2) / sqrt(2 pi), Gamma = n(d1) / (S sigma sqrt T), and dd1/dT = (r + sigma squared / 2)/(sigma sqrt T) - d1/(2T). Then d(delta)/d(sigma) = -n(d1) d2 / sigma, d(delta)/dt = -n(d1) times dd1/dT, d(gamma)/d(sigma) = Gamma (d1 d2 - 1) / sigma, and d(gamma)/dt = Gamma (d1 times dd1/dT + 1/(2T)). q = 0 MEANS CALL AND PUT CARRY THE SAME SECOND-ORDER GREEK at a strike, so the CE/PE distinction enters ONLY through the dealer sign and through oi. UNITS, STATED BECAUSE AN IMPLICIT UNIT IS THE DEFECT -- TD-NEW-3 cost this system a 100x error and Rule 14 cost it another. A _cr_per_volpt column is the per-contract derivative divided by 100 then multiplied by oi and spot and divided by 1e7: rupees crore gained per +1 IMPLIED-VOL POINT, that is per +0.01 of sigma, NOT per 1.00. A _cr_per_day column is the per-contract derivative divided by 365 then scaled the same way: per ONE CALENDAR DAY of time passing, 365 and not 252, calendar decay including weekends per OPERATOR RULING L78-3 and consistent with the exact/365 T convention. The DELTA pair scales by oi times spot over 1e7, which is delta-notional crore per L78-1. The GAMMA pair scales by oi times spot squared over 1e7, one power of spot higher, which is signed_gamma_exposure() own Crore convention, so the dGamma pair sits in the same unit as gex_cr per unit of sigma or time. SIGN CONVENTION: PE legs are NEGATED exactly as signed_gamma_exposure() negates them, carrying the standard dealer assumption of long calls and short puts into the second-order layer. This is NOT a flip applied to an already-signed delta -- with q = 0 the second-order greeks are IDENTICAL for call and put, so the negation is the whole of the dealer-side assumption and nothing else. INPUTS ARE ENH-131 VERBATIM so L3 and L7/L8 remain reconcilable: same leg set including the TD-NEW-2 deep-ITM guard, same session-median futures carry r with no look-ahead and UNMEASURABLE_R below six rows, same exact-seconds T over a 365-day year, same latest-ts run scoping, same Crore convention. R BARELY MATTERS HERE AND T DOES, WHICH IS THE OPPOSITE OF L3. Sweeping r over 0 to 0.12, wider than any dispersion this system has measured, moves SENSEX dte 1 net d(delta)/dt by 0.22 pct and net d(delta)/d(sigma) by 0.50 pct, and NIFTY dte 5 by 7.6 pct and 2.0 pct. Across exact/365, dte/365 and dte/252 on the same rows, SENSEX dte 2 net d(delta)/dt reads -1150, -1760 and -2746 crore per day, a factor of 2.4. exact/365 is used because it is the convention T1 is written on; S86 observation (b) found dte/252 roughly 10x better on gamma at dte 1 and recorded it WITHOUT changing T1, and that observation is deliberately NOT acted on here, because changing a convention after seeing which arm it favours is the fitting a pre-registration exists to prevent. DTE 0 IS SKIPPED, NEVER FLOORED, and on this layer that is measured rather than inherited: net d(delta)/dt reads -1820 crore per day at SENSEX dte 2, -23744 at dte 1 and -156855 at dte 0, and net d(gamma)/dt reads -4951550 at dte 0. A per-calendar-day rate published with 0.222 days left to run is an instantaneous derivative extrapolated over a horizon that does not exist. The independent d1 control agrees: median absolute Black-Scholes minus vendor delta inside the 0.05 to 0.95 band reads 0.0031 to 0.0185 at dte 1 to 12 and 0.0643 at dte 0. On dte 0 the four value columns are NULL and status is SKIPPED_EXPIRY. Per L78-3 the W1 expiry-day leg would be computed and recorded but NOT displayed, and E1 (S85) and E2 (S87) BOTH REFUSED, so that leg stays UNRECORDED and is not built here. CAPTURE DEPTH LIMITS THE EXPIRY SCOPE: L78-3 names W2 and the monthlies, but capture stage 1 holds exactly W1 and W2 -- measured as n_expiry = 2 on every session 2026-09-28 through 2026-10-02 on both symbols -- so the monthly legs cannot appear in this view and their absence is a capture limit, not a filter. VENDOR INPUT QUALITY, MEASURED AT THE 10:15 CYCLE: iv is null or zero on 27 to 50 pct of chain rows and iv_max reaches 2062.81 on the SENSEX W2 leg. The iv above zero predicate and the deep-ITM guard remove those BY RULE and never by eye, and n_legs publishes how many survived at each strike. is_trading_session is count(DISTINCT spot) above 1 over this symbol rows from 00:00 IST on the ts date THROUGH ts INCLUSIVE, so it carries no look-ahead; it is the ENH-133 D-3 clause 3 gate and it is WRITE-AND-FLAG, meaning the row is published either way and the consumer filters. 2026-10-02, Gandhi Jayanti, is why it exists: 83 distinct ts and 79680 NIFTY rows, so it passes a row count and a distinct-ts count per TD-S89-NEW-1 and fails only on distinct spot. THE GATE CTE IS AS MATERIALIZED AND THAT KEYWORD IS LOAD-BEARING, NOT STYLISTIC. The three gate shapes were measured against each other on a TWO-CONSTRUCT PRECURSOR of this body -- same scoping, same legs, same data, two of the four value columns -- so the comparison is between the shapes and is not a timing of this view: the gate as a plain CTE grouped off a day window runs 11040 ms on a sequential scan, the gate as an un-materialized correlated subquery runs 26424 ms over 490 loops, and the gate AS MATERIALIZED joined on (symbol, ts) runs 164 ms. The first two breach the PostgREST 8 s ceiling, which is the exact ADR-021 failure reproduced inside this file own first draft; removing the keyword reverts a sub-second view to a 26 s one that returns HTTP 500 and reads to a consumer as no data. THIS BODY, measured on its own pre-apply on 2026-10-03 as an inline query with no object created, and measured TWICE because one timing on a shared instance is a sample rather than a figure, runs 210.280 then 186.476 ms, with v_gex_greeks_l2_net at 157.714 then 191.610 ms returning 4 rows both times; every reading is roughly 40x under the 8 s ceiling, and CTE Scan on gate reports loops = 1 in both plans, so the MATERIALIZED hint demonstrably took rather than being assumed. NET VERSUS GROSS, AND THE TWO PAIRS DIFFER. Absolute net over gross-of-per-strike-nets, measured over eight arms, per construct: d(delta)/d(sigma) runs 0.844 to 1.000 with the minimum at SENSEX dte 2; d(delta)/dt runs 0.957 to 1.000 on seven of eight arms with SENSEX dte 2 the exception at 0.181; d(gamma)/d(sigma) runs 0.008 to 0.384; d(gamma)/dt runs 0.092 to 0.376. The delta pair net is therefore meaningfully signed and very nearly equals its gross, structurally because d2 changes sign at the money while (oi_call - oi_put) changes sign with it so the two flips cancel; the gamma pair net is a small residue of large opposing terms and MUST NOT be read alone. Gross is published beside net for all four constructs here, and v_gex_greeks_l2_net publishes the ratios. STATUS values are OK, SKIPPED_EXPIRY, UNMEASURABLE_R and NO_LEGS; the four value columns are NULL on all but OK.';

COMMENT ON VIEW public.v_gex_greeks_l2_net IS
  'S89 / ENH-98 -- ADR-025 parity L7 and L8, net roll-up. Grain (symbol, expiry_date) at the LATEST option_chain_snapshots ts. Selects from v_gex_greeks_l2_strike and adds nothing to the method -- read that view COMMENT for the full specification, the units, the sign convention, the dte-0 skip and the PROVISIONAL stamp. PROVISIONAL -- flow-vs-book (D-4) not built; T1 PASSED 2026-10-07 (detail and badge in the strike view COMMENT). DISPLAY ONLY. THE ONE THING THIS VIEW ADDS IS THE DENOMINATOR, AND IT IS A DIFFERENT DENOMINATOR FROM THE STRIKE VIEW. The gross_strike_* columns are sums of ABSOLUTE PER-STRIKE NETS, so CE and PE cancellation inside a strike has already happened before the absolute value is taken. The gross_* columns on v_gex_greeks_l2_strike are per-LEG. The two are not interchangeable and neither is implied by the other. net_over_gross_* is published for all four constructs so no consumer has to decide for itself whether a net is a signal or a cancellation residue -- ENH-131 Gate 2 FAILED precisely for want of that distinction, scoring a cancellation rather than a model because net over gross ran 0.0095 to 0.341 while the gate compared nets at 1 pct. Measured over eight arms at the 10:15 cycle: the DELTA pair reads 0.976 to 1.000 on seven of eight arms and 0.181 on SENSEX dte 2, so its net is meaningfully signed; the GAMMA pair reads 0.008 to 0.384 on all eight, so its net is a residue and must be read with its gross. status is the per-strike status propagated by max(), which is safe only because every strike inside one (symbol, expiry_date) group shares one dte, one r window and one ts, so the group cannot be mixed -- verification V5 asserts that rather than assuming it.';


-- =====================================================================
-- SECTION 4 of 6 -- privileges (LIVE -- TD-S81-NEW-5, CASE-2026-09-22)
-- REVOKE FIRST, then GRANT. S39 revoked instances and left Supabase
-- DEFAULT PRIVILEGES untouched, so every object created afterwards came
-- up with ALL again. Order matters.
--
-- MEASURED 2026-10-03 on the sibling board views: v_iv_surface,
-- v_iv_term_structure, v_gex_repriced_flip, v_gex_concentration,
-- v_gex_strike_rank, v_gex_strike_walls, v_gex_abs_exposure,
-- v_gex_net_gamma_river, v_oi_rotation_since_open and
-- v_max_pain_by_strike all read `anon=r/postgres` -- SELECT alone.
-- v_gex_max_pain and v_gex_pin_maxpain read `anon=rm/postgres`, carrying
-- MAINTAIN as well: the CASE-2026-09-22 default-privileges shape, filed,
-- NOT repaired by this file, and NOT copied by it. All twelve are plain
-- views, not matviews, and none has RLS enabled -- so for these objects
-- the GRANT alone is the boundary (TD-S81-NEW-2).
-- =====================================================================

REVOKE ALL ON public.v_gex_greeks_l2_strike FROM anon;

GRANT SELECT ON public.v_gex_greeks_l2_strike TO anon;

REVOKE ALL ON public.v_gex_greeks_l2_net FROM anon;

GRANT SELECT ON public.v_gex_greeks_l2_net TO anon;


-- =====================================================================
-- SECTION 5 of 6 -- read-only role (matches every sibling: merdian_ro=r)
-- =====================================================================

GRANT SELECT ON public.v_gex_greeks_l2_strike TO merdian_ro;

GRANT SELECT ON public.v_gex_greeks_l2_net TO merdian_ro;


-- =====================================================================
-- SECTION 6 of 6 -- verification (run after 1-5; each is a real check)
--
-- Rule 0: each check below states what would make it FAIL, and a real
-- defect produces exactly that. A check that cannot fail for the reason
-- it names is documentation, not verification.
-- =====================================================================

-- V1  Grain and status. FAILS IF: the latest-ts seek returned more than
--     one ts per symbol (duplicate ts values appear), an expiry leg
--     vanished (fewer than 2 per symbol), or a dte-0 leg carries a
--     non-NULL value column.
--     EXPECTED: 2 symbols x 2 expiry legs = 4 rows, one ts per symbol,
--     and value columns NULL on exactly the rows whose status is not OK.
-- SELECT symbol, ts, expiry_date, dte, status, is_trading_session,
--        n_strikes, n_legs,
--        round(net_delta_drift_iv_cr_per_volpt::numeric,2)   AS d_delta_div,
--        round(net_delta_drift_time_cr_per_day::numeric,2)   AS d_delta_dt,
--        round(net_gex_drift_iv_cr_per_volpt::numeric,2)     AS d_gex_div,
--        round(net_gex_drift_time_cr_per_day::numeric,2)     AS d_gex_dt,
--        round(net_over_gross_delta_drift_time::numeric,3)   AS ng_delta_dt,
--        round(net_over_gross_gex_drift_time::numeric,3)     AS ng_gex_dt
--   FROM public.v_gex_greeks_l2_net ORDER BY symbol, expiry_date;

-- V2  THE d1 CONTROL. This is the check that can actually fail, and it is
--     the one that matters: every construct in this file is a function of
--     d1, so a wrong r, a wrong T unit, a wrong log argument or a wrong
--     sigma scale all land here.
--     Reconstruct Black-Scholes delta from this view's own d1 inputs and
--     compare with the VENDOR delta on the same row, inside the
--     [0.05, 0.95] band that ENH-98 established removes the junk wings.
--     FAILS IF: median absolute error exceeds 0.03 on any dte >= 1 leg.
--     EXPECTED, measured at the 10:15 cycle on four sessions: 0.0031 to
--     0.0185 across dte 1-12. Stated as a belief BEFORE the run, not read
--     off it -- the figures above come from the S89 probe, and this bar
--     is set roughly 1.6x above the worst of them, not fitted to them.
--     (Query: the probe at scratch/s89_l78/p8_ctl.sql, re-pinned to the
--     apply-day cycle. Committed with this file.)

-- V3  ANON PATH, not object existence. TD-S81-NEW-5: a GRANT skipped at
--     apply time leaves the view live and anon-unreadable, which returns
--     HTTP 200 with zero rows and is indistinguishable from no data.
--     ONE EXECUTION, with current_user beside the counts -- the Supabase
--     SQL editor opens a new session per run, so a SET ROLE in one run
--     does not survive into the next (S84 §D.40.1).
--     FAILS IF: role_now is not anon, or either count is 0.
--     EXPECTED: role_now = anon, n_strike > 0, n_net = 4.
-- BEGIN;
--   SET LOCAL ROLE anon;
--   SELECT current_user AS role_now,
--          (SELECT count(*) FROM public.v_gex_greeks_l2_strike) AS n_strike,
--          (SELECT count(*) FROM public.v_gex_greeks_l2_net)    AS n_net;
-- COMMIT;

-- V4  COMMENTS actually landed. A part-run apply that skips Section 3 is
--     the S79 failure; it leaves the views correct in body and silently
--     undocumented. FAILS IF: either length is NULL or differs from the
--     file literal.
--     EXPECTED, COMPUTED FROM THIS FILE'S OWN LITERALS (S89 2026-10-03; S92 2026-10-08),
--     before any apply and never read back off the database -- S81
--     published a comment_len of 4637 against a file literal of 5632
--     because a figure was stated with no measurement behind it:
--       v_gex_greeks_l2_strike  comment_len = 8642   comment_md5 = 3d96fcaf21b19318a8305a1b12f2d262
--       v_gex_greeks_l2_net     comment_len = 1710   comment_md5 = 5cd561cc8fdc6b26c43249dc37339b73
--     [S92: recomputed from the restamped literals; S89 read 8569 / 1688.]
--     If either literal is edited before the apply, RECOMPUTE these two
--     numbers from the file; do NOT adjust them to match the database.
-- SELECT c.relname,
--        length(obj_description(c.oid,'pg_class')) AS comment_len,
--        md5(obj_description(c.oid,'pg_class'))    AS comment_md5
--   FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
--  WHERE n.nspname = 'public'
--    AND c.relname IN ('v_gex_greeks_l2_strike','v_gex_greeks_l2_net')
--  ORDER BY c.relname;

-- V5  The net view's max(status) is only safe if no (symbol, expiry_date)
--     group mixes statuses. FAILS IF: any group carries more than one
--     distinct status, dte, ts or r_sess -- which is exactly what would
--     happen if the latest-ts seek or the expiry join ever widened.
--     EXPECTED: 0 rows.
-- SELECT symbol, expiry_date,
--        count(DISTINCT status) AS n_status, count(DISTINCT dte) AS n_dte,
--        count(DISTINCT ts) AS n_ts, count(DISTINCT r_sess) AS n_r
--   FROM public.v_gex_greeks_l2_strike
--  GROUP BY symbol, expiry_date
-- HAVING count(DISTINCT status) > 1 OR count(DISTINCT dte) > 1
--     OR count(DISTINCT ts) > 1 OR count(DISTINCT r_sess) > 1;

-- V6  THE q = 0 CALL/PUT EQUALITY the sign convention rests on. The header
--     claims the PE negation IS the dealer assumption and nothing else,
--     which is true only if the unsigned second-order greek is identical
--     for CE and PE at a strike. FAILS IF: at any strike carrying both a
--     CE and a PE leg with equal oi, the two legs' magnitudes differ.
--     This is a PARITY CLAIM BETWEEN TWO BRANCHES and CLAUDE.md Rule 0
--     clause 4 requires it be asserted by a test, not by this comment.
--     EXPECTED: 0 rows. (Run against the per-leg CTE via the committed
--     probe; it is not reachable from the published view, which already
--     aggregates CE and PE together.)

-- V7  Latency. ADR-021: the whole point of run scoping, and the reason
--     the gate CTE is MATERIALIZED. FAILS IF: either plan exceeds the
--     PostgREST 8 s ceiling. EXPECTED: both views well under 1 s.
--     MEASURED PRE-APPLY 2026-10-03, this exact body run inline as a
--     query with no object created, twice: strike 210.280 / 186.476 ms,
--     net 157.714 / 191.610 ms, gate CTE at loops=1 in both plans.
--     The two rejected gate shapes, measured on the two-construct
--     precursor, ran 11,040 ms and 26,424 ms -- both over the ceiling,
--     so this check has demonstrably fired before, on this same gate.
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_greeks_l2_strike;
-- EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM public.v_gex_greeks_l2_net;
