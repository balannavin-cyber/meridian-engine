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
