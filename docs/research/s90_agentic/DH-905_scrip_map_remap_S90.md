# DH-905 — dhan_scrip_map stale security IDs (S90 / AM-1, 2026-10-05/06)

## Finding
Active NSE rows in `dhan_scrip_map` carried Dhan security IDs that no longer exist anywhere in `dhan_scripmaster` (any exchange, any segment). 32 rows in total:
- 2026-10-05 (11 that failed in EOD ingest): 10 remapped (MTARTECH→2715, RAMASTEEL→10304, SPECTRUM→30457, STALLION→29205, STLTECH→9313, SYSTMTXC→759358, TAC→23441, TBZ→27041, TIL→9802, WAAREEINDO→19955), SANGHIIND deactivated.
- 2026-10-06 05:05 (21 found by the full sweep): 18 remapped, 3 deactivated.

| symbol | old | new | master series |
|---|---|---|---|
| ABINFRA | 27020 | 27016 | BE |
| AIMTRON | 23987 | 23984 | SM |
| ANURAS | 23687 | 2829 | EQ |
| BESTAGRO | 2311 | 2306 | EQ |
| BFUTILITIE | 25879 | 14567 | EQ |
| BGRENERGY | 15189 | 15193 | BE |
| BLISSGVS | 19265 | 19269 | BE |
| CHOLAFIN | 19257 | 685 | EQ |
| DIACABS | 18543 | 18545 | BE |
| E2E | 8937 | 8940 | BE |
| EMBDL | 14453 | 14450 | EQ |
| ESAFSFB | 19878 | 19884 | BE |
| HFCL | 21951 | 21954 | BE |
| LOTUSDEV | 758145 | 758147 | BE |
| MICEL | 7169 | 7165 | BE |
| RAJOOENG | 757049 | 757052 | BE |
| RMDRIP | 757834 | 757836 | BE |
| RNBDENIMS | 758981 | 758984 | BE |

Deactivated (no master row, and no renamed NSE equity row found by display name): GSPL 13197, JBCHEPHARM 1726, CIGNITITEC 5142.

## Root cause
Dhan issues a new security ID when NSE moves a stock between series (EQ ↔ BE/T trade-to-trade, SME). The new ID is usually within a few of the old one. `dhan_scrip_map` is never re-synced against the master after the 1st/15th reload, so it goes stale every time the exchange reclassifies a stock — which happens weekly. The "~28 DH-905 dead IDs / 97.83 % coverage ceiling" recorded at S67 was this, not a structural ceiling.

## Evidence
- Comparison read (merdian_ro, 2026-10-06 05:01): `to_jsonb` match of each mapped id against every master row (by id: none; by symbol: the rows above).
- Post-fix check (merdian_ro, 2026-10-06 05:16): active NSE map rows whose id is not an NSE segment-E master row = **0**.
- SQL record: `sql/2026-10-06_s90_dh905_scrip_map_remap.sql`.
- **The first editor run** (temp table + `BEGIN`/`COMMIT` as separate statements) applied the 18 remaps but errored `42P01` on its final check; the values were verified row by row afterwards. Lesson (§D.46.8): in the Supabase SQL editor, put gated multi-step writes inside a single `DO` block.

## Follow-up
Roadmap **R1.10** (TD-S90-NEW-1): sync step after each `swap_dhan_scripmaster()` — match each active NSE map row to the master by symbol, segment E, any series; remap on a single unambiguous match; write a `gap` ledger row (ADR-031 D7) for zero or multiple matches; never keep a dead ID silently. Plus a daily contract check: active map IDs absent from the master = 0.
