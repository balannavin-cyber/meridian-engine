# tech_debt.md — S90 / AM-1 additions (project-knowledge copy)

The full `tech_debt.md` is too large to re-upload to project knowledge (write refused at the size cap, 2026-10-06). The repo file is canonical; this doc carries only what S90 added: the eleven new items (prepended above TD-S89-NEW-5 in the repo) and the S90 status footer (appended at the end).

### TD-S90-NEW-1 (S2 priority) — `dhan_scrip_map` is never re-synced against the scrip master, so every NSE series change leaves a dead security ID behind

| Field | Value |
|---|---|
| **Priority** | **S2.** Each dead ID is a ticker silently missing from EOD and breadth; S67 read the tail as a structural 97.83 % ceiling. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Component** | `dhan_scrip_map` · `dhan_scripmaster` (reloaded 1st/15th by `reload_dhan_scripmaster.py` → `swap_dhan_scripmaster()`) · `ingest_equity_eod_local.py` |
| **Evidence** | 32 active NSE rows pointed at IDs absent from the master on every exchange and segment; 28 had a replacement ID for the same company (mostly series moves into BE/T), 4 had none. Cured by hand 2026-10-05/06: 0 unmapped. `docs/research/s90_agentic/DH-905_scrip_map_remap_S90.md`, `sql/2026-10-06_s90_dh905_scrip_map_remap.sql`, §D.46.9. |
| **Proper fix** | Roadmap **R1.10**: after each reload, match each active NSE map row to the master by symbol (segment E, any series); remap on one unambiguous match; write a `gap` ledger row (ADR-031 D7) on zero or several; contract check "active map IDs absent from master = 0". |
| **Status** | **OPEN — mitigated by hand; recurs with the next series change.** |

### TD-S90-NEW-2 (S2 priority) — the deployed Marketview bundle is built from commits that exist only on the box

| Field | Value |
|---|---|
| **Priority** | **S2.** A rebuild from GitHub would silently revert MV-2/3/4/5/9 and the WCB staleness line. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Component** | `~/meridian-connect` (`3cb474a`, `6cdc0a1`, `265ceb0` on `main`) · `/var/www/marketview` |
| **Evidence** | `git push` from the box fails 403 (HTTPS PAT); the S90 fixes were built and rsynced from the local commits (`marketview_live_check_S90.md` fix log). |
| **Proper fix** | A deploy key for `meridian-connect` on the box (commands given in-session), push, and verify `origin/main` = the deployed build's commit. |
| **Status** | **OPEN.** |

### TD-S90-NEW-3 (S3 priority) — about 26 calendar gates are still inline copies, not `core/trading_calendar_gate.py`

| Field | Value |
|---|---|
| **Priority** | **S3.** The two capture-path gates that read "no row" as open are routed (`ca79717`) and closed days are now rows, so the dated risk (2026-10-20) is covered. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Component** | inline gates across the scheduled scripts (S68 counted ~28; 2 routed in S90) |
| **Proper fix** | ADR-031 D5.3 / roadmap R0.8: route each onto the shared gate, one per change, with the absent-row and gate-failure cases tested as in `docs/research/s90_agentic/patches/patch_r08_gates.py`. |
| **Status** | **OPEN.** |

### TD-S90-NEW-4 (S3 priority) — `market_ticks` is purged after every close by a job nobody has traced

| Field | Value |
|---|---|
| **Priority** | **S3.** No data loss that anything reads, but nothing tick-based can be validated or replayed after the close, and capacity planning must not assume tick history. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Evidence** | 33,365 EQ rows at 16:57 IST, 0 at 19:00 IST on 2026-10-05; the 8-day window held only the current day (R0.1 P4, §D.46.12). |
| **Proper fix** | Find the purge (pg_cron as postgres, crontab, a writer's own cleanup), record it in Topology, and decide retention under R1.9. |
| **Status** | **OPEN.** |

### TD-S90-NEW-5 (S3 priority) — `v_gex_max_pain` fails intermittently at about anon's 3-second statement timeout

| Field | Value |
|---|---|
| **Priority** | **S3.** One failed read per occurrence; the board shows "no max pain" for that cycle. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Evidence** | One HTTP 500 after 3,282 ms (retry 200 at 1,283 ms); `anon` `statement_timeout = 3s` (MV-6, R0.1 P4). Not reproduced at 15:10 (888 ms). Cause **probable, not proven** — the PostgREST error body was not captured. |
| **Proper fix** | Capture the error body; then index, simplify, or cache per run. |
| **Status** | **OPEN.** |

### TD-S90-NEW-6 (S3 priority) — the wall corridor can degenerate: put wall = call wall, put wall above spot

| Field | Value |
|---|---|
| **Priority** | **S3.** One SENSEX cycle on 2026-10-05 (10:20 run); next cycle normal. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Evidence** | `v_gex_strike_walls`: put = call = 72,500, `put_wall_sigma +0.093`, `BELOW_FLOOR`, rendered "72,500–72,500 · 0.00 % wide" (MV-8). Walls are argmax within the band with no side constraint. |
| **Proper fix** | Decide whether a put wall must lie at or below spot (and a call wall at or above); if so, constrain in the view and mark the cycle when no wall qualifies. |
| **Status** | **OPEN — needs a definition ruling first.** |

### TD-S90-NEW-7 (S3 priority) — one screen shows two runs: the signal stream and the board disagree on regime, and two ATM definitions coexist

| Field | Value |
|---|---|
| **Priority** | **S3.** Not a wrong number, but an operator reading both sees contradictory states with nothing saying which is current. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Evidence** | 15:05 signal row `SHORT_GAMMA`, net −1,38,305 vs board 15:00 net +2,53,636 LONG (MV-10); Context IV-skew ATM 22,550 vs Board W1 ATM 22,500 at spot 22,535 (MV-11). |
| **Proper fix** | Each panel labels its run time (ADR-031 D2 status with "since"), and one ATM rule is used across the read layer. |
| **Status** | **OPEN.** |

### TD-S90-NEW-8 (S2 priority) — Marketview Settings is read-only since S90-E; the authenticated write route, `changed_by` and `config_version` are owed

| Field | Value |
|---|---|
| **Priority** | **S2.** Parameters now change only through the SQL editor; `core/pin_state.py` reads eight keys seeded on 2026-10-05. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Component** | `update_parameter()` (EXECUTE revoked from PUBLIC/anon/authenticated, `sql/2026-10-05_s90_apply_S90E_r05_r11.sql`) · `meridian-connect` `src/pages/Settings.tsx` |
| **Proper fix** | ADR-031 D4.3/D4.4 and D3: a write route behind the sign-in that passes the signed-in identity as `p_changed_by`, re-granted only to it; `config_version` stamped on computed rows (roadmap R0.6). |
| **Status** | **OPEN.** Supersedes the write-path half of TD-S89-NEW-2. |

### TD-S90-NEW-9 (S3 priority) — every `roq.sh` connection warns of a collation version mismatch

| Field | Value |
|---|---|
| **Priority** | **S3.** Warning only. A mismatch can mean text indexes sort differently from the OS library. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Evidence** | Database created with collation 153.120, OS provides 153.121 (every `bin/roq.sh` run, S90). |
| **Proper fix** | Supabase-side: reindex check, then `ALTER DATABASE postgres REFRESH COLLATION VERSION` as postgres. Not runnable from `merdian_ro`. |
| **Status** | **OPEN.** |

### TD-S90-NEW-10 (S3 priority) — unused Breeze credentials remain in `.env`

| Field | Value |
|---|---|
| **Priority** | **S3.** No code path uses Breeze (operator, 2026-10-05); the keys are credential surface only, and Rule 19 records both Breeze keys among those exposed in S71. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Proper fix** | Operator removes the Breeze lines from `.env` on the box and revokes the keys at the broker. Note: `.env` line 21 contains `$4`, so `set -u` breaks sourcing — use `set +u` around it. |
| **Status** | **OPEN — operator action.** |

### TD-S90-NEW-11 (S3 priority) — two S90-H backup tables to drop after a clean week

| Field | Value |
|---|---|
| **Priority** | **S3.** Storage only; both revoked from anon/authenticated. |
| **Filed** | 2026-10-06 (Session 90 / AM-1) |
| **Component** | `equity_eod_bak_s90_20261005`, `breadth_indicators_daily_bak_s90_20261005` (`sql/2026-10-05_s90H_eod_date_shift_migration.sql`) |
| **Proper fix** | After a week of clean EOD runs on IST dates (from ~2026-10-13), `DROP TABLE` both as postgres. |
| **Status** | **OPEN — dated.** |


---

**S90 / AM-1 (2026-10-05 → 06) — 11 new items filed (TD-S90-NEW-1..11), 0 closed; status changes on six existing items.** Ledger: **`TDs_NEW=11 (0×S1, 3×S2, 8×S3)` · `TDs_CLOSED=0`**. Hybrid close: each item points at its evidence in `docs/research/s90_agentic/`; progress on the agentic layer is tracked in the roadmap, not here. **Existing items, updated without editing their bodies** (anchors would not be unique, and the body is the record of what was believed): **TD-S89-NEW-1 → MITIGATED** — proper fix (2) deployed: closed days written as rows (`82619f8`, belt rows 10-20 / 11-10) and the chain ingest + spot capture on `core/trading_calendar_gate.py` (`ca79717`); the contract runner calls 10-02 CLOSED; **close after 2026-10-20 passes with no chain rows.** **TD-S89-NEW-2 → premise REFUTED** (§D.46.3): the table holds 16 rows and the write path exists as an anon-executable RPC; closed to anon by S90-E; the remaining half is **TD-S90-NEW-8** — recommend closing TD-S89-NEW-2 as superseded. **TD-S89-NEW-5 → evidence added**: R01-F8 measures `anon=rm` (MAINTAIN) on six base tables (`option_chain_snapshots`, `market_spot_snapshots`, `market_ticks`, `volatility_snapshots`, `script_execution_log`, `trading_calendar`), not only the two views. **TD-S81-NEW-16 → partly remediated further**: `merdian_ro` read policies added on `script_execution_log`, `merdian_parameters`, `dhan_scripmaster` (S90); new S90 tables carry RLS + a `merdian_ro` policy in their own DDL (ADR-031 D6). **TD-S82-NEW-4 → interacts**: the seeder now writes Muhurat 2026-11-08 CLOSED as the engine says; it self-heals through the merge when the engine is fixed. **TD-S88-NEW-1 → not reproduced** on 2026-10-05 10:27 (previous close resolved across the 10-02 holiday); one observation, not a closure.
