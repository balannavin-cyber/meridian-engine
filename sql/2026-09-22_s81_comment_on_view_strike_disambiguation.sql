-- =====================================================================
-- 2026-09-22_s81_comment_on_view_strike_disambiguation.sql
-- S81 / TD-S79-NEW-13 -- name the three strike scalars apart
-- =====================================================================
--
-- WHY
--   Three live-facing objects each emit a "notable strike" on a different
--   basis, and no comment distinguishes them:
--
--     v_gex_strike_walls.call_wall / put_wall  RAW-OI argmax in +/-band*sigma
--     v_gex_concentration.top_strike_net       GAMMA-WEIGHTED argmax |gex_cr|
--     gamma_metrics.max_gamma_strike           argmax of POSITIVE gex_cr
--                                              (ADR-024 Amendment A)
--
--   TD-S79-NEW-13 names the first two. The third was found at S81 while
--   reading the Marketview source: state.ts computes it client-side and
--   renders it under THREE different labels (MAX gamma, Max gamma Strike,
--   strongest dampen). The fix is naming, not renaming -- both view column
--   names are correct for their own view and renaming would break consumers
--   to close a documentation gap.
--
-- MEASURED 2026-09-22 08:15 UTC, and it is why this matters now:
--   NIFTY  call_wall 23400 == top_strike_net 23400   (spot 23334.85, dte 0)
--   SENSEX call_wall 75000 == top_strike_net 75000   (spot 74585.33, dte 2)
--   Both coincided on the same run. TD-S79-NEW-13's own first-light evidence
--   had NIFTY's top_strike_net at ATM instead, so this varies run to run.
--
--   The coincidence is NOT evidence of anything and must not be read as two
--   independent measures agreeing. gex_cr is gamma*OI*S^2, so BOTH argmaxes
--   are OI-weighted and coincidence is partly arithmetic. Whether any such
--   coincidence predicts anything is a pre-registered ADR-009 question and is
--   left UNANSWERED by design -- the same ruling S80 applied to the
--   pin<->max-pain gap, with ENH-97 as the warning.
--
-- SCOPE: comments only. No view body changes, no renames, no grants, and
--   therefore no re-verification of either view.
--
-- COMMENT ON VIEW REPLACES, IT DOES NOT APPEND. Each statement below carries
--   its view's COMPLETE existing comment text, extracted from the S79 source
--   files byte-for-byte, with the new sentence added at the end. Running only
--   the new sentence would DESTROY the existing documentation.
--
-- RUN ONE STATEMENT AT A TIME. The Supabase SQL editor wraps a pasted script
--   in one transaction, so the weakest statement in a bundle gates the
--   strongest (S72 Section 5 took Sections 2 and 3 down with it).
-- =====================================================================


-- =====================================================================
-- STATEMENT 1 of 2 -- v_gex_strike_walls
-- =====================================================================

COMMENT ON VIEW public.v_gex_strike_walls IS
  'S79 / ENH-120 -- OI walls: put/call wall as raw-OI argmax within a +/-band*sigma moneyness window, scoped to the latest run per symbol (ADR-021, S72 FIX 2 lateral form). Band via get_parameter_num(''wall.band.<symbol>''), default 1.5. Gamma-weighted argmax was tested and rejected (collapses to ATM). Sigma columns are the distance measure; raw strikes exist for labelling only. corridor_state is four-valued: ~30% of runs sit outside the corridor, and a NULL wall is UNDEFINED, not BELOW_FLOOR. atm_iv is sourced from volatility_snapshots, which is single-expiry and silently switches expiry class -- staleness is surfaced (atm_iv_age_min / iv_fresh) but NOT enforced to absent; see ADR-023 deviation noted in sql/2026-09-15_s79_v_gex_strike_walls.sql. NOT the same strike as v_gex_concentration.top_strike_net: these walls are a RAW-OI argmax (gamma weighting was tested for this layer and rejected because it collapses to ATM), top_strike_net is a GAMMA-WEIGHTED argmax over abs(gex_cr) and is the strike its Herfindahl is measured on, and neither is gamma_metrics.max_gamma_strike, which is the argmax of POSITIVE gex_cr -- the max net-long-gamma strike, ADR-024 Amendment A. Three bases, three questions; they may land on the same strike on any run and did on 2026-09-22 (NIFTY call_wall = top_strike_net = 23400). That is coincidence, not identity. Both bases are OI-weighted, so coincidence is partly arithmetic and is not evidence of anything.';


-- =====================================================================
-- STATEMENT 2 of 2 -- v_gex_concentration
-- =====================================================================

COMMENT ON VIEW public.v_gex_concentration IS
  'S79 / ENH-122 -- L12 gamma concentration. Herfindahl max/sum on the gamma book, three legs: hhi_net over abs(gex_cr), hhi_call over abs(gamma_call*oi_call), hhi_put over abs(gamma_put*oi_put). Latest-run scoped (ADR-021, S72 FIX 2 lateral form), grain (run_id, symbol, expiry_date). THE SPLIT IS LOAD-BEARING: call and put concentration correlate 0.71-0.87 at 0 DTE but -0.00 to 0.15 away from it, so a single combined number averages two independent signals on most days. CONCENTRATION FALLS ~2x ACROSS DTE, so dte_bucket is stored and any percentile MUST be computed within bucket and per symbol -- NIFTY runs ~35 pct more concentrated than SENSEX at every quantile, and live p90 exceeds historical p90 by 36-42 pct while p10 barely moves. hhi_net IS gamma_metrics.gamma_concentration recomputed by the identical formula from the same signed_gamma_exposure() output -- comparing them passes BY CONSTRUCTION and verifies nothing (ADR-014 s2.5, Rule 0 clause 1). The split legs bypass the TD-NEW-2 deep-ITM guard because signed netting destroys the per-side view; measured effect at p90 is at most 0.0021 (1.2 pct of that cell) against a 0.01 criterion fixed before the query, so filtered legs were considered and DELIBERATELY NOT BUILT. hhi_call 0.32 vs hhi_net 0.22 at 0 DTE is entirely sign netting, not the guard. Percentile, d1D and d-vs-mean are a separate historical object, not this one. top_strike_net is a GAMMA-WEIGHTED argmax over abs(gex_cr) -- the strike hhi_net is measured on -- and is NOT v_gex_strike_walls.call_wall/put_wall, which are RAW-OI argmaxes inside a +/-band*sigma window (gamma weighting was tested and rejected for that layer because it collapses to ATM), nor gamma_metrics.max_gamma_strike, which is the argmax of POSITIVE gex_cr (ADR-024 Amendment A). Coincidence across runs is expected: it is coincidence, not identity. Both bases are OI-weighted, so coincidence is partly arithmetic and is not evidence of anything.';


-- =====================================================================
-- VERIFY (run separately, after both statements)
-- Expect 2 rows; each description must contain BOTH the original opening
-- ('S79 / ENH-120' / 'S79 / ENH-122') and the new closing sentence.
-- =====================================================================

-- SELECT c.relname AS view_name,
--        left(obj_description(c.oid, 'pg_class'), 40)  AS starts_with,
--        right(obj_description(c.oid, 'pg_class'), 60) AS ends_with,
--        length(obj_description(c.oid, 'pg_class'))    AS comment_len
--   FROM pg_class c
--  WHERE c.relnamespace = 'public'::regnamespace
--    AND c.relname IN ('v_gex_strike_walls','v_gex_concentration')
--  ORDER BY 1;
