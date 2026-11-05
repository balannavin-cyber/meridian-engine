# Tape scoring hash ledger (pre-registration v0.2)

Pre-registration v0.2 sha256: `71950f92eb1313f2e58a40772c8671a2beefce220d5222213d39e8a80dfa4800`
Date: 2026-11-03
Head sha of the commit that carries the four hashed files (branch `tape/scoring`): `93c0196b8b6b139ec7e5e001383c7a99de22dac6`

| file | sha256 (raw LF bytes) |
|---|---|
| services/tape_scoring/scoring_extract.sql | 0baf9e9fda2042c8ac32229cb21ef4bed837c12355f1b7be53b6166030379d22 |
| services/tape_scoring/run_extract.sh | e586dfb72725fcce7cb1e7febecaa7984d720797f17dc0a725ebf6f96a0f93da |
| services/tape_scoring/score.py | 7a1267d6d250f47bb381624558c2cb36eb8f3aa5306923f167827b0f257c9f57 |
| services/tape_scoring/wilcoxon.py | e4dbace545f067c9c1ccc33184fd64bc18ee0f70c55c165c8084f0e72d5e1e84 |

**No tape-vs-outcome query has run before this hash.** The scorer ran only on planted fixtures
(`tests/tape_scoring/gen_fixture.py`); the extract SQL was never executed against the database; no join of tape rows
with chain events, spot outcomes or `gex_strike_snapshots` has been computed on real data.

First definitions that are inside the hash (the pre-registration named them without defining them): quarantine
completeness = distinct `minute_ist` in 09:15-15:30 with a `tape_minute` row / 375 (DEF-2); an unverifiable
data-quality rule quarantines the day (DEF-3); a token restart = `restarts[].prev_state == "TOKEN_FAIL"` with
`process_start_ist` in session (DEF-4); T3 passive side = ask on both legs (operator ruling R-3). See
`docs/tape/scoring_plan.md` section 1.3 and section 5.

`score.py` recomputes these four values on every non-fixture run and refuses on any difference. The operator copies
this file beside `tape_preregistration_v0.2.md` on `meridian-tape-staging` `main`.

## Entry 2026-11-05 — pre-registration v0.4

Pre-registration v0.4 sha256: `b45477d36eba6930ab41171a3405c10cf6ecb0bd1fbb04b52d09a5c2129acd57`
Date: 2026-11-05
Head sha of the commit that carries the four hashed files (branch `tape/scoring-v04`): `6b8bdf913c55fa320452594cf151d295a8d330db`

| file | sha256 (raw LF bytes) | change from the v0.2 entry |
|---|---|---|
| services/tape_scoring/scoring_extract.sql | 8f3db643d0a0e667cbe5800dc937626fcaf474bbaf9b2bfb1fbf7b164bcf7bea | changed: `tape_strike_cycle` SELECT + `buy_5, sell_5, uncl_5, gap_5`; new OPTIONAL pure SELECT `tape_minute_oi` (last) |
| services/tape_scoring/run_extract.sh | 01bff8743d0cea2f792c815e69acb2c66c718b8b50dab27efffb42a5fb07854d | changed: `tape_minute_oi` last in `RELS`, on an OPTIONAL SKIP path that never aborts |
| services/tape_scoring/score.py | 9011aba09e64d91467842e0f9e17fbd822849ae5bfe54e79bbdac809cf31ff9c | changed: v0.4 S, R window, descriptive block, last-entry ledger check |
| services/tape_scoring/wilcoxon.py | e4dbace545f067c9c1ccc33184fd64bc18ee0f70c55c165c8084f0e72d5e1e84 | unchanged |

**Scoring-code defect (recorded under §0.3; fixed with this version, before any run).** `services/tape_scoring/score.py`,
`spot_range`, lines 285–290 at the hashed version: `m0 = hm(t_dt) + 1`, so R(T) was computed over bars labelled
T+1 … T+30. The scoring plan (§1.3) had pinned "minute label m in (T, T+30]" before the exploration established that
`hist_spot_bars_1m` labels are minute-start; on that clock the pinned labels are one bar late relative to the intended
window [T, T+30). Effect: every R(T) would have omitted the bar beginning at T and included the bar beginning at T+30.
No scoring run had used the code, so no result is affected. Fix: `m0 = hm(t_dt)`; the `r_horizon_min` (30) and
`r_min_bars` (25) parameters are unchanged. The fix ships with the S-window change (§1), the reporting additions
(§§1–3), a guard for each (`ha-r-window`: planted bars where the T and T+30 bars carry the extreme values, so the
one-bar-late mutant fails; `ha-s-window`: S equals the planted trailing-30 sign and differs from the planted cumulative
sign; `hb-per-label`; `hb-t4-separate`: T4 never enters the H-B match set), and the three files are re-hashed.

No tape-vs-outcome query has run on a confirmatory day before this hash. The scorer ran only on planted fixtures
(`tests/tape_scoring/gen_fixture.py`); the extract was not executed against the database.

From this entry on, `score.py` verifies against the **last** `## Entry` block of this file, which must name the v0.4
sha256 above, and refuses on the v0.2 entry (guard `sc-hash-check`, mutant `M-SC-HASH-FIRST-ENTRY`). The operator copies
this file beside `tape_preregistration_v0.4.md` on `meridian-tape-staging` `main`.
