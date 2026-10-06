-- =====================================================================
-- 2026-10-05_s90_v_dealer_flow_sim_sign_fix.sql
-- S90 MV-1 — v_dealer_flow_sim reports dealer hedge flow with the WRONG SIGN.
--
-- AUTHORED, NOT APPLIED. Apply in the SQL editor after 16:00 IST.
--
-- WHY. The view's header cites ADR-014 §2.3, which states:
--   positive gex_cr = dealer LONG gamma  -> dealer SELLS rallies / BUYS dips
--   negative gex_cr = dealer SHORT gamma -> dealer BUYS rallies / SELLS dips
-- The shipped body computes flow_cr = net_gex * pct and labels flow_cr > 0 BUY,
-- so a LONG-gamma book on +1 % reads BUY — the opposite of §2.3. Observed live
-- 2026-10-05 on Marketview Home, 3 of 3 readings (NIFTY +84,719 Cr -> "-1 %: SELL";
-- NIFTY -10.3L Cr -> "-1 %: BUY"; SENSEX -1.1L Cr -> "-1 %: BUY").
-- Hedge flow is the change in the dealer's futures position needed to stay
-- delta-neutral: d(hedge) = -Gamma * dS. Hence flow_cr = -net_gex * pct.
--
-- WHY THE ENH-81 FALSIFICATION GATE PASSED. Gate 3 in
-- sql/2026-05-25_enh81_falsification.sql asserts the SAME rule the view
-- implements (net_gex*pct > 0 => BUY), so it compared the view with itself and
-- could not fail for the reason it names (CLAUDE.md Rule 0, clause 4). The gate
-- below is written from ADR-014 §2.3's words, not from the view.
--
-- SCOPE: sign only. Column names, types and order are unchanged, so
-- CREATE OR REPLACE keeps the existing grants. The ADR-021 latest-run scoping
-- this view still lacks (TD-S81-NEW-4) is a separate change and is NOT made here.
-- Consumers: Marketview Home FLOWS card (src/lib/board.ts useFlowSim) and
-- src/lib/queries.ts useDealerFlow. No Python consumer.
-- =====================================================================

BEGIN;

CREATE OR REPLACE VIEW public.v_dealer_flow_sim AS
WITH scenarios AS (
  SELECT * FROM (VALUES
    (-0.02::numeric,  '-2.0%'::text),
    (-0.01,           '-1.0%'),
    (-0.005,          '-0.5%'),
    ( 0.005,          '+0.5%'),
    ( 0.01,           '+1.0%'),
    ( 0.02,           '+2.0%')
  ) AS s(pct, label)
),
latest_per_symbol AS (
  SELECT DISTINCT ON (symbol)
    run_id, symbol, expiry_date, ts, spot
  FROM gex_strike_snapshots
  ORDER BY symbol, ts DESC
),
ctx AS (
  SELECT
    l.symbol, l.run_id, l.expiry_date, l.ts, l.spot,
    gm.net_gex, gm.flip_level
  FROM latest_per_symbol l
  JOIN gamma_metrics gm
    ON gm.run_id = l.run_id AND gm.symbol = l.symbol
)
SELECT
  c.run_id, c.symbol, c.expiry_date, c.ts,
  s.label                                         AS scenario,
  s.pct                                           AS spot_pct,
  ROUND((c.spot * (1 + s.pct))::numeric, 2)       AS perturbed_spot,
  c.net_gex,
  ROUND((-c.net_gex * s.pct)::numeric, 2)         AS flow_cr,      -- S90: hedge flow = -Gamma * dS
  CASE WHEN (-c.net_gex * s.pct) < 0 THEN 'SELL' ELSE 'BUY' END AS direction,
  CASE
    WHEN c.flip_level IS NULL THEN false
    WHEN s.pct < 0 AND c.spot > c.flip_level
         AND c.spot * (1 + s.pct) <= c.flip_level THEN true
    WHEN s.pct > 0 AND c.spot < c.flip_level
         AND c.spot * (1 + s.pct) >= c.flip_level THEN true
    ELSE false
  END                                             AS crosses_flip
FROM ctx c
CROSS JOIN scenarios s
ORDER BY c.symbol, s.pct;

COMMENT ON VIEW public.v_dealer_flow_sim IS
  'ENH-81 v0 — dealer hedge-flow projection at ±0.5 %, ±1 %, ±2 % for the latest run per symbol. flow_cr = -net_gex × Δspot (first order): per ADR-014 §2.3 a long-gamma book (net_gex > 0) SELLS rallies and BUYS dips. SIGN CORRECTED S90 2026-10-05 (MV-1): the v0 body had flow_cr = +net_gex × Δspot, which inverted every direction. Not ADR-021 scoped (TD-S81-NEW-4): read it filtered by symbol or run_id.';

-- ---------------------------------------------------------------------
-- Gate, from ADR-014 §2.3's words. It RAISES, so a violation aborts the whole
-- transaction and the old view stays — the SQL editor runs every statement in
-- one go, so a SELECT-only gate could not stop the COMMIT.
-- Long gamma (net_gex > 0): rally (+) => SELL, dip (-) => BUY.
-- Short gamma (net_gex < 0): rally (+) => BUY, dip (-) => SELL.
-- It also refuses to pass vacuously: it needs 12 rows (2 symbols x 6 scenarios).
-- ---------------------------------------------------------------------
DO $gate$
DECLARE n_bad int; n_rows int;
BEGIN
  SELECT count(*) FILTER (WHERE
            (net_gex > 0 AND spot_pct > 0 AND direction <> 'SELL')
         OR (net_gex > 0 AND spot_pct < 0 AND direction <> 'BUY')
         OR (net_gex < 0 AND spot_pct > 0 AND direction <> 'BUY')
         OR (net_gex < 0 AND spot_pct < 0 AND direction <> 'SELL')),
         count(*)
    INTO n_bad, n_rows
  FROM public.v_dealer_flow_sim
  WHERE symbol IN ('NIFTY','SENSEX');      -- symbol filter keeps it off the 57014 path (TD-S81-NEW-4)
  IF n_rows <> 12 THEN
    RAISE EXCEPTION 'S90 gate: expected 12 rows, got % — not applied', n_rows;
  END IF;
  IF n_bad > 0 THEN
    RAISE EXCEPTION 'S90 gate: % rows violate ADR-014 §2.3 — not applied', n_bad;
  END IF;
END
$gate$;

COMMIT;

-- Evidence (runs after COMMIT; read-only): one line per symbol.
SELECT current_user AS role_now, symbol, count(*) AS n_rows, min(net_gex) AS net_gex,
       string_agg(scenario || ' ' || direction, ' · ' ORDER BY spot_pct) AS directions
FROM public.v_dealer_flow_sim
WHERE symbol IN ('NIFTY','SENSEX')
GROUP BY symbol ORDER BY symbol;
