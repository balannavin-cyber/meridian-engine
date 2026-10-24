# S100 close inputs — Saturday 2026-10-24 (B-part builds after 3ad5c81, rulings S100-A … S100-O)

Every figure here was computed from a pasted box output in the S100 session. Rulings: `claude/rulings_s100.md`.

## Commits (meridian-engine, box route)
| sha | what | TDs |
|---|---|---|
| 3ad5c81 | S98+S99 doc-close; tech_debt split (S100-A) | — |
| 3070682 | R3 monitor hung-run probe, step 16 | TD-S97-NEW-3 FIXED |
| b29f320 | R42 window = union of runner lines, step 17 | R42 |
| 9e24792 / 4769565 / d91295b | R4 pre-open probe 09:09, wsfeed retry timer + deduped alert, crontab (Dhan refresh 08:20), wsfeed unit sync | TD-S80-NEW-17 FIXED; R43/R44 OBSOLETE |
| f213d22 | R40 breadth-from-ticks gate / no-input / ledger; chain Dhan 5xx retry; steps 20–21 | TD-S81-NEW-11 FIXED; R40 |
| 9c5f50c | R19 daily breadth gap-fill + S100-H / R22 SQL records; step 22 | TD-S97-NEW-11 FIXED (10-08 1,377 / 10-15 1,373 rows backfilled, Oct short 0 on all 13 dates) |
| 418a75b | S100-M (b) SUBSCRIPTION_LAPSED (chain, spot 1m, CAS close, probe, core 11→12, daemon) + CHECK DDL record + S100-J/K SQL records; step 23 | TD-S97-NEW-21 (b) FIXED |

## Marketview (meridian-connect)
- `1072593` (S100-M (a)) live 12:32 IST, bundle `index-BHDegYdK.js`: Health untracks `build_ict_htf_zones.py` (14 tracked).
- `142c3e6` (S100-N) live ~12:59 IST, bundle `index-BeRqvGjW.js`: legacy pages' previous close / SPOT tile from Board's hooks.
- `2ee83e1` (S100-P, R35 / manual F-5) live 16:47 IST, bundle `index-CoRd4ixq.js`: Context IV-skew tile = view `leg_skew_98` front leg (operator-approved wording); client PE/CE recompute dropped.
- `3366bf1` (S100-Q / Q.1, R17 step 1) live 17:17 IST, bundle `index-Bu6mi2fq.js`: read sentence names the pocket word "(local γ)" and states "Net gamma is long|short, x of gross". R17 step 2 = R12 (neutral band on net/gross, pre-registered).
- `1aeb000` (S100-R) live 18:19 IST, bundle `index-BdbC9K5_.js`: Spot label `held since 15:15` / `close`; dealer wording D1–D5 live; D6/D7 corrected in source but the two components are unimported dead code. R33 closed by S100-R C (Γ = aggregate exposure, γ = per-option; CLAUDE.md standing rule reworded at close). R14 closed. R5: label part done; close print rides on S98-B's 15:40 cycle — Part C Monday.
- `f964e40` (S100-S, final report A2 / A4 / A5) live 18:48 IST, bundle `index-BFOk56iL.js`: session-state strip (pre-open / closing session / closed, dated), stale-strip window to 15:45, FUT·BASIS sub-line `vs spot X @ hh:mm`.
- Round records: `lovable_prompt_s100_health_untrack_ict.md`, `lovable_prompt_s100_legacy_prev_close.md` (→ docs/lovable_prompts/s100/).
- Backups after S100-L: `.bak-1aeb000`, `.bak-3366bf1`, `.bak-2ee83e1` + 3 `PRE_*`.

## Operator SQL applied (records in sql/)
S100-H cron deactivate (12 / 0 / 3) · R22 calendar (15 / 15 / 0 / 12) · S100-J `data_contamination_ranges.symbols` (4 rows,
1 scoped; merdian_ro 4 / 1 / 3 / 4) · S100-K `merdian_ro_select` on 51 RLS tables (56 policies; probes 0 → 1000) · S100-M
CHECK + SUBSCRIPTION_LAPSED (true / true).

## TD footers owed (status paragraphs, v5 Rule 3)
- TD-S97-NEW-3 FIXED 3070682 · R42 FIXED b29f320 · R43/R44 OBSOLETE · TD-S80-NEW-17 FIXED 9e24792/4769565 · TD-S81-NEW-11 FIXED f213d22 · R40 FIXED f213d22 (overlap deferred, S100-I)
- TD-S90-NEW-14 FIXED by S100-H (12 Edge Function cron jobs inactive; functions + x-cron-secret deletion = later ruling; the 15-char secret prefix that leaked into chat must be treated as disclosed)
- R22: TD-S97-NEW-14, TD-S81-NEW-7, TD-S41-NEW-1 CLOSED (11-08 per S100-O: stays closed)
- TD-S97-NEW-11 FIXED 9c5f50c · TD-S97-NEW-12 CLOSED (10-21 filled)
- TD-S81-NEW-12 CLOSED (basis context exits 0 since S92-B) · TD-S81-NEW-1 (a) unanswerable (7-day log window) — old token treated as disclosed
- TD-S97-NEW-15 CLOSED (S100-J) · TD-S94-NEW-1 CLOSED (S100-K; guard for future tables not built — note)
- TD-S97-NEW-16 CLOSED (S100-L; rule into the promote step of `docs/lovable_prompts` README)
- TD-S97-NEW-21: (a) live 1072593, (b) 418a75b, (c) ruled display-only → CLOSED; 10-21 counts were 360 / 174 / 1 (TD said 286 / 126 for a 24 h window); note: `backfill_cas_close_from_daily.py` logs DH-902 as DATA_ERROR
- TD-S82-NEW-4 CLOSED as decided (S100-O; ADR-020 amendment + docstrings owed in this close)
- TD-S80-NEW-19 CLOSED superseded by v5 Rule 3 (legacy instance TD-S70-NEW-5)
- TD-S76-NEW-17 CLOSED with ADR-004 Amendment C erratum (outcomes 19,571 measured 2026-09-10)
- TD-S90-NEW-12 CLOSED (capture SUCCESS every trading day 10-07→10-23 except holiday 10-20 and lapse 10-21; reconciliation corrected=0 on every counted day; 10-21 filled 10-22 per S98-D)
- New TD candidates: the R34 legacy-page defect is fixed (S100-N) → file + close in one; the 15:40 snapshot is not EOD OI on expiry eve (R7 note); Health error panels show "no errors" while loading, and the legacy strip shows `0 (0.00%)` / `iv not populated` while loading (loading states rendered as values); docs cite a dead bare-IP board URL; `NarrativeModal` / `AmbientTrajectory` are unimported dead code; **`index_futures_snapshots.spot_price` lags the chain's spot in the closing window** (10-23: 22,516.4 held on the 15:30–15:40 futures rows while the chain had the 22,600.0 close → stored basis +63.7…+72.6 vs true ≈ −20…−11) — fix: futures writer takes the chain's spot.

## Findings (B3 reads) — `docs/research/s100/B3_reads_2026-10-24.md`
R7 ours right (F7 compared 15:20 with 15:40); R8 last-trade bounce 2–4 bp both indices, no capture defect; R10 by construction;
R18 three figures reproduced, legacy-page defect → S100-N; R35 Context "IV skew" was a same-strike put/call gap → S100-P; 10-12 no `dhan_idx_i` pre-open row 09:00–09:15.

## §D.54 corrections (this session's own errors)
Helper regex on the TD template · PK extractor block cut-off (→ S100-A) · roq.sh given SQL as an argument (§D.53.6 repeat) ·
R3 bound recalled 170.7 s, measured 184.4 s · marker count recalled 9, real 7 · R4 mutant M2 mis-listed · wsfeed test stamp
guard · chain anchor matched 3 sites · tick query read 0 (pruning, not timezone) · log-query redaction missed x-cron-secret ·
"S100-J" label used before the ruling existed · 08:25 probe time (pre-open lands 09:08–09:12) · S100-K split stated 9 / 42
uncomputed (7 / 44) · `merdian_ro_select` total predicted 53 (56) · guard path assumed in `bin/` (docs/lovable_prompts/s92) ·
board URL assumed from docs (bare IP dead; hostname behind oauth2) · R7 first query timed out (DISTINCT ts scan) · R8
"SENSEX thinner" expectation falsified (15 vs 27 stale rows; equal in bp) · TD-S94-NEW-4 "misfiled" alarm (closed by S99) · S100-P diff size estimated +16 / −10 (computed +13 / −9).

## Part C additions — `partC_additions.md`

## Still open for the operator
BS-1: Dhan TOTP re-enrolment + PIN change (Dhan web), then the hidden-prompt `.env` update, then `refresh_dhan_token.py` +
`preopen_probe.py --check`. Later rotations: Telegram, Breeze, AWS key (TD-S99-NEW-1), Supabase service-role plan, Edge
Function + x-cron-secret deletion.
