-- =====================================================================
-- 2026-09-22_s81_v_max_pain_by_strike_CAPTURED_BASELINE.sql
-- S81 -- CAPTURED BASELINE of public.v_max_pain_by_strike, as it stood
--        before the TD-S80-NEW-10 expiry fix. DO NOT EDIT.
-- =====================================================================
--
-- THIS FILE IS A RECONSTRUCTION, NOT AN ORIGINAL.
--   The body below was produced by pg_get_viewdef('public.v_max_pain_by_strike', true)
--   on 2026-09-22 and is reproduced VERBATIM. It is committed because NO
--   DDL FOR THIS OBJECT HAS EVER EXISTED IN THE REPOSITORY.
--
--   The Enhancement Register footer for S40 records "1 new SQL file
--   (sql/v_max_pain_by_strike.sql)". THAT CLAIM IS FALSE. Measured at S81:
--   the path is absent from disk, `git log --all -- sql/v_max_pain_by_strike.sql`
--   is EMPTY, and the only max-pain DDL in the repo is ENH-123's
--   2026-09-22_s80_v_gex_max_pain.sql. TD-S80-NEW-10's own Component row
--   cites the same non-existent path.
--
--   The view has therefore existed since S40 in the live database only,
--   which is the exact condition ADR-025 D2 clause 4 names: a view living
--   only in the live database is one DROP from unrecoverable. This file
--   ends that, for the PRE-CHANGE state. The fix lands as a separate file
--   on top, so the diff between them is reviewable in git.
--
-- FIDELITY
--   pg_get_viewdef normalises: it qualifies column names, expands BETWEEN,
--   makes implicit casts and ELSE NULL explicit, and may rename aliases.
--   What is preserved exactly is SEMANTICS, not the original keystrokes,
--   which no longer exist anywhere.
--
-- KNOWN DEFECTS PRESENT IN THIS BASELINE -- all deliberate, all recorded:
--   1. `chain` groups by (symbol, strike) with NO expiry filter, so a
--      snapshot carrying two expiries collapses into a per-strike max()
--      mixture. Not firing (one expiry per cycle across 2,923 cycles) but
--      armed the moment TD-S80-NEW-1 raises ingest depth. TD-S80-NEW-10.
--   2. No `ts` in the output and `latest_ts` is an unbounded max(ts) with
--      no recency floor, so an ingest stall serves a plausible stale strike
--      with nothing downstream able to tell. Observed 2026-09-19 11:40 IST
--      serving a 2026-09-17 15:40 IST strike. TD-S80-NEW-10, ADR-023.
--   3. `max_pain` ties break NON-DETERMINISTICALLY: row_number() OVER
--      (PARTITION BY symbol ORDER BY total_pain) has no tie-break column,
--      so equal total_pain yields an arbitrary winner. ENH-123 orders by
--      (total_pain, candidate_strike). NOT corrected in the S81 fix either
--      -- it is out of the scope that was approved, and is reported for a
--      TD rather than changed silently.
--   4. `strikes` is a no-op: `chain` is already grouped by (symbol, strike)
--      and is therefore already distinct on it.
--   5. `latest_ts` is max(ts) GROUP BY symbol over the whole of
--      option_chain_snapshots -- the S72 FIX 2 cost shape. Carried
--      unchanged into the fix by instruction; EXPLAIN is reported there.
--
-- ANON PRIVILEGES AT CAPTURE TIME: ALL SEVEN (SELECT, INSERT, UPDATE,
--   DELETE, TRUNCATE, REFERENCES, TRIGGER). has_comment false. Corrected
--   in the fix file, not here -- this file records the state as found.
--
-- REPLAYING THIS FILE RESTORES THE PRE-FIX BEHAVIOUR, INCLUDING ALL FIVE
-- DEFECTS ABOVE. It exists for provenance and rollback, not for use.
-- =====================================================================

CREATE OR REPLACE VIEW public.v_max_pain_by_strike AS
WITH latest_ts AS (
         SELECT option_chain_snapshots.symbol,
            max(option_chain_snapshots.ts) AS max_ts
           FROM option_chain_snapshots
          GROUP BY option_chain_snapshots.symbol
        ), chain AS (
         SELECT ocs.symbol,
            ocs.strike,
            max(
                CASE
                    WHEN ocs.option_type = 'CE'::text THEN ocs.oi
                    ELSE NULL::numeric
                END) AS ce_oi,
            max(
                CASE
                    WHEN ocs.option_type = 'PE'::text THEN ocs.oi
                    ELSE NULL::numeric
                END) AS pe_oi
           FROM option_chain_snapshots ocs
             JOIN latest_ts lt ON lt.symbol = ocs.symbol AND lt.max_ts = ocs.ts
          GROUP BY ocs.symbol, ocs.strike
        ), strikes AS (
         SELECT DISTINCT chain.symbol,
            chain.strike
           FROM chain
        ), pain AS (
         SELECT s.symbol,
            s.strike AS candidate_strike,
            COALESCE(sum(GREATEST(s.strike - c.strike, 0::numeric) * c.ce_oi), 0::numeric) + COALESCE(sum(GREATEST(c.strike - s.strike, 0::numeric) * c.pe_oi), 0::numeric) AS total_pain
           FROM strikes s
             LEFT JOIN chain c ON c.symbol = s.symbol
          GROUP BY s.symbol, s.strike
        ), max_pain AS (
         SELECT ranked.symbol,
            ranked.candidate_strike AS max_pain_strike
           FROM ( SELECT pain.symbol,
                    pain.candidate_strike,
                    row_number() OVER (PARTITION BY pain.symbol ORDER BY pain.total_pain) AS rn
                   FROM pain) ranked
          WHERE ranked.rn = 1
        )
 SELECT p.symbol,
    p.candidate_strike,
    p.total_pain,
    mp.max_pain_strike,
        CASE
            WHEN p.candidate_strike < mp.max_pain_strike THEN 'PE_SIDE'::text
            WHEN p.candidate_strike > mp.max_pain_strike THEN 'CE_SIDE'::text
            ELSE 'MAX_PAIN'::text
        END AS side
   FROM pain p
     JOIN max_pain mp ON mp.symbol = p.symbol;
