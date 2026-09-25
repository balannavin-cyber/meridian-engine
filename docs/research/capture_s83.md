# capture_s83.md — Session 83 doc-close source

Session 83 · 2026-09-24 → 2026-09-25 (Thu–Fri). **Three parity layers built, validated and
deployed: L9, L3, L10.** Every doc-close splice takes its content from this file. Every number
below must be re-verified against the named file or database object before it is spliced;
a mismatch is reported, never silently corrected.

**Naming rule (operator, S83, standing):** the reference product is never named in any MERDIAN
artefact. Say "the parity target" or "the ADR-025 L<n> target". Every file written in this
doc-close must grep 0 for the product name. Existing occurrences in older registers are NOT
scrubbed in this close (operator decision owed, §7).

---

## 0. Shape

Build session. Rule followed throughout: measure, propose, stop for OK, build. **Nothing
computed was adopted on a gate that failed.** Four gates were mis-specified by me and are
recorded as mis-specified, **never loosened** (§3). Production Python unchanged. Three views
added to the live database by the operator in the Supabase SQL editor. One stale logrotate
config moved out of `/etc/logrotate.d/`.

## 1. Deployed objects

| ENH | layer | view | sql file | cols | COMMENT len / md5 | EXPLAIN |
|---|---|---|---|---|---|---|
| ENH-130 | L9 IV term structure | `v_iv_term_structure` | `sql/2026-09-24_s83_v_iv_term_structure.sql` | 17 | 4922 / `a8fa5b05a873b7ea697e4eba27ae8864` | [verify from scratch/s83_l9] |
| ENH-131 | L3 repriced flip | `v_gex_repriced_flip` | `sql/2026-09-25_s83_v_gex_repriced_flip.sql` | 18 | 6997 / `d12ef107140ca423c83e0275ced58b7a` | 122.9 ms, no Seq Scan |
| ENH-132 | L10 IV surface | `v_iv_surface` | `sql/2026-09-25_s83_v_iv_surface.sql` | 21 | 4709 / `adff5d5a7ab68f79c74ec36b052ea93d` | 28.1 ms, no Seq Scan (2,715 ms before MATERIALIZED) |

All three: skip-scan + CROSS JOIN LATERAL latest-ts per symbol (ADR-021), never `created_at`;
COMMENT, REVOKE and GRANT shipped as **live statements** (TD-S81-NEW-5) so `sql/` matches the
database; grants anon SELECT + merdian_ro SELECT; **anon path verified by `SET ROLE anon`**,
not by object existence. L9 anon: NIFTY 2 / SENSEX 2. L10 anon: NIFTY 498 / SENSEX 378. L3 at
deploy: NIFTY `OK` flip 23024.67, SENSEX `SKIPPED_EXPIRY` (dte 0).

**ADR-025 D2:** clauses 1, 2, 4 MET on all three. **Clause 3 PENDING BY DECISION** under
Amendment B1 — a deliberate hold, not a lapse. BUILT count stays 2 of 14. L3 builds the
**repriced** zero-gamma level and neither reads nor changes `gamma_metrics.flip_level`
(Amendment B7 ruling 4).

Supabase defaults also gave `authenticated` MAINTAIN+SELECT and `service_role` full on each new
view. Flagged, not acted on (§7).

## 2. Findings, by layer

### L9 — ENH-130 (full evidence in the view COMMENT)
- Term structure **inverted on 93.5 % of NIFTY and 97.6 % of SENSEX stage-1 cycles**, in every
  dte bucket — the normal state of this window, not an event. Two sessions, one regime: not a
  finding about the market, and deliberately **not** filed as a TD.
- `parity_gap` (CE−PE at ATM) is negative on all four symbol-leg pairs, median −0.589 to
  −2.502 vol points; it is the quality column — a slope smaller than it is noise.
- 3 of 341 stage-1 cycles carried one expiry (incl. 2026-09-24 08:45) → one row, `term_slope`
  NULL, **no fallback to an earlier ts**. Forward variance negative in 0 of 336 paired cycles.
- **ADR-025 D3 deviation, PENDING OPERATOR DECISION:** the L9 target's back leg is the
  *furthest listed* expiry; stage-1 capture holds W1+W2 only, so `term_slope` is a short-end
  slope not comparable to the target figure.

### L3 — ENH-131 (full gate record in the view COMMENT)
- Black-Scholes repricing, sticky-strike, leg set frozen at observed spot; r = **session-median
  futures carry** over 09:20 IST..ts (≥6 rows, else UNMEASURABLE_R); T exact seconds / 365 d;
  dte 0 → SKIPPED_EXPIRY (S62).
- **Gate record:** G1 PASS (gex_cr rebuilt to 1.1e-10 Cr). **G2 FAIL, MIS-SPECIFIED** (net vs
  net at 1 % — net/gross 0.0095–0.341 amplified a 2–4 % gross error to 19 %). **G3 FAIL 1 of 3,
  clause (ii) MIS-SPECIFIED** (±5 % window blind to a 2→1 full-grid crossing change). **G4 FAIL
  1 of 4, r band UNDER-SPECIFIED** (~19× narrower than measured single-cycle carry dispersion).
  **G5 PASS 5 of 5**, pre-registered, incl. three out-of-sample arms (NIFTY 09-23 12:00, SENSEX
  09-22 12:00, NIFTY 09-18 12:00): crossing held within 0.25 of a 1-day σ across the p10–p90 r
  band and three T conventions; single-cycle carry 0.0203–0.2087 vs session-median 0.0368–0.0584
  (8.7× less dispersion).
- Caveats kept: gross fidelity 3.4 / 10.9 / 4.7 %, failing 5 % on SENSEX 1-dte — **a stable
  crossing is not a reproduced curve**; one far-tail crossing at 9.4 % of spot (~17σ) appeared
  and vanished with the T convention (`n_cross_full_grid` publishes it).
- Repriced flip sits 0.1–0.8σ from spot across arms.

### L10 — ENH-132 (full evidence in the view COMMENT; measurements in `scratch/s83_l10/*.out`)
- **iv = 0 means absent; iv IS NULL never occurs** (0 of 1,752 rows); zeros run 20–134 per side
  per leg. L9's "a single zero per leg" was true at ATM only and does not generalise.
- **OTM convention adopted on measurement:** inside ±2 % CE−PE medians −0.064..−0.079 (NIFTY
  front); outside, averaging is ruined by the ITM side (SENSEX front −5..−2 %: average 369.99 vs
  OTM 40.30). 789 of 876 strikes quote their OTM side = exactly those quoting any side.
- **All 20 worst outliers (iv/ATM) sit on the ITM side**, so the OTM convention excludes every
  one; 14 of 20 carry oi = 0; the high-OI exception is SENSEX back leg 72100–72400 CE, 1.6–2.0 %
  ITM, iv 110–117 vs ATM 13.1, 48.7 M OI.
- Wings 33–89 % absent; near-money clean on two of four legs (both NIFTY).
- **Skew** `leg_skew_98` = OTM put at the listed strike nearest 0.98 × ATM strike − ATM IV, no
  search, per leg. Deployed values: NIFTY 2.1411 / 1.9690, SENSEX back 0.8069, SENSEX front NULL
  (SKIPPED_EXPIRY). **Not comparable across expiries.**
- **dte 0:** ATM IV averages 17.07 across dte-0 session cycles but collapses to 0.89 at the
  post-expiry 15:40 cycle — S62 rule kept whole-day; narrowing it would change house canon.
- **V6 failed at 2,715 ms** (single-reference CTEs inlined; the k98 window CTE evaluated once per
  output row, loops=876, hdr re-scanned 767,376 times). Fixed with `AS MATERIALIZED` on px, hdr,
  k98r, legmeta → **28.1 ms**, k98r loops=1, **V1–V5 byte-identical before/after**.
- Parity-target check (conversation-only): skew definition matches the target's stated
  "2 % below ATM − ATM"; target surface panel is marked illustrative and discloses no method.
  Real distance to target is expiry depth (target term panel spans ~7–84 d; we hold W1+W2).

## 3. Self-corrections — file as Assumption Register §D.39 (one row each, belief vs evidence)

1. **Four mis-specified gates**, one shape — a threshold set without deriving the quantity's
   scale: L3 G2 (net/gross cancellation), L3 G3(ii) (window), L3 G4 (r band), **L10 pre-check**
   (one skew level across tenors; a fixed −2 % sits ~3 daily σ out at dte 1, ~1σ at dte 5–7).
   Measured: SENSEX front skew median dte 1 5.87, dte 0 9.93; N2 anchor within 0.013 %, 0 of 170
   cycles >0.25 % off. Recorded as mis-specified, not loosened.
2. **Five factual errors in the L10 COMMENT draft**, caught before apply: 16→14 of 20 oi=0;
   36→33 % wing floor; three→two of four clean legs; "per expiry leg"→"per side per leg"; an
   unexplained 3.49 cited as evidence. Cause: counts taken from rendered summary tables, and
   M1–M3b had never been saved to `.out`. Recounted from files.
3. A recalled expected value ("3 untracked") that measured differently (rotated logs +
   status.json + research/srs).
4. An unprivileged `journalctl` read reported "No entries" — a no-test; the sudo read showed
   logrotate failing 09-23 and 09-24.
5. "Vendor-side error" wording, corrected by the operator: exchange data is real; the Greeks/IV
   are the vendor's model conventions.
6. OI column names guessed from ADR-015 text (`oi_total_calls/puts`); live columns are
   `oi_call`/`oi_put`.
7. A COMMENT copied out of a wrapped terminal lost 37 characters; reconstructed from source and
   verified by md5 before apply.

## 4. Ops

- **logrotate:** `/etc/logrotate.d/meridian.PRE_20260922` (a stale second config) made
  logrotate fail on 2026-09-23 and 09-24. Moved to `/root/logrotate.meridian.PRE_20260922`,
  sha256 unchanged; `/etc/logrotate.d/meridian` untouched. First clean run expected 2026-09-25
  00:00 UTC — **verify `Finished Rotate log files.` in `sudo journalctl -u logrotate.service`**.
- **eod_health_check first scheduled run:** 2026-09-25 00:45 UTC. Verify it fired
  (`logs/eod_health_check.log`); `[ -- ] NOT AUDITABLE` on `equity_intraday_last` is by design.
- **Errata (uncommitted in ~/meridian-cc):** CLAUDE.md:992, session_log.md:3,
  merdian_reference.json now read "74148 bytes at bb374ae (71751 kept + 2397 pointer/S82
  entry)"; 73791 labelled a stale dry-run projection.

**STEP 0 OBSERVED (S83 doc-close, read-only, 2026-09-25):**
- (a) `eod_health_check` FIRED at 2026-09-25 00:45 UTC. `--date prev` resolved 2026-09-24 from
  2026-09-25 IST via rule-engine. **VERDICT `[ OK ] clean session`** — capture + compute
  complete and symmetric; every line OK. **MISMATCH against the expectation written above:**
  this file predicted `[ -- ] NOT AUDITABLE` on `equity_intraday_last` "by design", but the run
  printed `[ OK ] equity_intraday_last refreshed 2026-09-24 03:35 UTC, 1313 rows on 2026-09-24`.
  The check audited it successfully. The prediction was wrong; the run is not.
- (b) logrotate RAN CLEAN: `Finished Rotate log files.` at 2026-09-25 00:00:03, service
  `Deactivated successfully`, 1.223s CPU. The two-night failure is ended, so TD (a) below is
  filed CLOSED, not OPEN.

## 5. Tech debt to file (TD-S83-NEW-n — number from the headings at write time, never by hand)

- (a) S3 — stale logrotate config in `/etc/logrotate.d/` silently failed rotation two nights;
  remediated same session, **close only after the 00:00 UTC run is observed**.
- (b) S2 — `compute_volatility_metrics_local.py` has no zero guard on iv and derives dte from
  wall clock at :690.
- (c) S3 — depth-2 capture occasionally lands one expiry (3 of 341 stage-1 cycles, incl.
  2026-09-24 08:45).
- (d) S3 — far-wing OTM IV below ATM, unexplained (NIFTY back leg < −5 %: OTM median 3.49 vs ATM
  11.79). Published as-is by L10, not filtered.
- (e) S3 — vendor IV on high-OI ITM strikes reads 110–117 (SENSEX back 72100–72400 CE).
  Excluded by the OTM convention; recorded because OI there is real.
- (f) S3 — `.gitignore` lacks `*.log.[0-9]*` and `status.json`; the new logrotate scope rotates
  repo-root logs into untracked files. Correction to TD-S79-NEW-6: `status.json` is a live cron
  output, not scratch.
- (g) S3 — L10 `leg_atm_iv` requires both sides quoted; equivalence to L9 `atm_iv` (V3, |d|=0)
  was proven only on a cycle where both sides quote. Read L9's expression and confirm identical
  semantics on a one-sided ATM; if they differ, the L10 file comment "EXACTLY as L9" is wrong.
  **STEP 0 OBSERVED: SAME — do not file (g).** Read at source, not recalled. L9
  `sql/2026-09-24_s83_v_iv_term_structure.sql:160-162` is
  `CASE WHEN q.ce_iv > 0 AND q.pe_iv > 0 THEN (q.ce_iv + q.pe_iv) / 2.0 END`, over
  `NULLIF(max(...), 0)` at `:131`/`:133`. L10 `sql/2026-09-25_s83_v_iv_surface.sql:149-151` is
  the same expression on `p.`, over `NULLIF(max(...), 0)` at `:121`/`:122`. BOTH require both
  sides quoted above zero, so a one-sided ATM yields NULL in each. The L10 file comment
  "EXACTLY as v_iv_term_structure" is CORRECT and (g) is resolved at step 0.
- (h) Errata: ADR-015 names `oi_total_calls/puts`; live columns are `oi_call/oi_put`.
  CURRENT.md "before S79" → "before S81".

## 6. CLAUDE.md — two settled bullets (Rule 0 grade)

- **Derive a gate's threshold from the quantity's scaling before measuring, and write the
  derivation beside it.** Four S83 gates failed because a level was chosen without it (net/gross
  cancellation, window width, carry dispersion, skew across tenors). A mis-specified gate is
  recorded as mis-specified and never loosened.
- **A view CTE referenced once is inlined (PG ≥12).** A window or ranking CTE joined against
  mis-estimated CTEs can then run once per output row. Mark computed-once CTEs
  `AS MATERIALIZED` and verify `loops=1` in EXPLAIN; prove the change inert by byte-identical
  before/after outputs (L10: 2,715 → 28.1 ms).

## 7. Decisions owed to the operator

1. Capture depth — SENSEX furthest listed expiry, NIFTY 5th leg, or record the D3 deviation.
   Recommendation on record: add current + next **monthly** expiries (4 legs) as its own
   measured ENH; blocks L9 comparability and L10 depth, not their builds.
2. Scrub the product name from existing registers (parity spec filename, ADR-025, older notes).
3. `authenticated` / `service_role` default grants on new views.
4. Send the Dhan support question on the Greeks/IV methodology (drafted, not sent).

## 8. Carry to S84

- 2026-09-29 — NIFTY L9 stage-1 max-pain arm (TD-S80-NEW-1).
- ENH-98 re-run with SENSEX at dte 1–2; the multi-DTE offset test.
- Parity build order continues: **L7/L8 (ENH-98)** next.
- Everything under CURRENT.md S82 "Decisions owed" that S83 did not touch carries unchanged.
