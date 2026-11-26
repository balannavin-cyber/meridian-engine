# STREAMS.md — MERIDIAN development lanes (hub register)

**Status: v0.3 (rows updated at the S107 engine close, 2026-11-26); v0.2 ruled 2026-11-21 (operator, "as recommended"; Doc Protocol v5.1 Rules 12–16).** Git home: `docs/registers/STREAMS.md` (engine repo). Owner: the engine lane. Every lane reads this at session open; the engine updates it at every engine doc-close (v5.1 Rule 13) and the same day when a blocking dependency changes.

**What this file is for:** the one place that says which lanes exist, where each keeps its records, which engine-owned objects each touches, and what each is waiting on from another. Pointers and dependencies only; never a lane's results.

**Project knowledge, all lanes:** `docs/operational/MERDIAN_PK_Protocol_v1.md` (PK copy `claude/MERDIAN_PK_Protocol_v1.md`). Read P5 at every session open; run P4 at every close. Lane PK folders and git mirrors are in its P2.1 table.

---

## 1. Lanes

| Lane | Series / open session | Status | Project folder | Git home | ID prefix (v5.1 Rule 14) | Latest close |
|---|---|---|---|---|---|---|
| **Engine (hub)** | S / **S108** next (S107 closed 2026-11-26: `tape_w` login, gross pin view and Board Pin switch, gamma V2 tables and backfill, intakes I-002 and I-003) | live | `claude/` root; `claude/intake/` | `meridian-engine`: registers `docs/registers/`, decisions `docs/decisions/`, research `docs/research/s<N>/` | `TD-S<N>-NEW-k`; mints ADR, ENH, AR §D, CASE for all lanes | **S107 (2026-11-26)**, branch `engine/s107-close` cut from `6a69dbe`, for the operator to merge; S106 `7c6e18c` |
| **Order flow (tape)** | MR-OFL / **OFL10** next | live; `tape_w` login proved 2026-11-24; first live 2b day earliest Mon 2026-11-30 | `claude/ofl/` (from OFL9; older OFL files still at `claude/` root until their git copies exist) | code: `meridian-engine` branch `tape/live-l2` @ `d1f9ba2` (+ `meridian-tape-staging`), not on `main`; docs `docs/tape/`; records: PK only → `docs/research/tape/` at OFL10 (PK delta step 2 of 7 at the OFL9 close) | `TD-OFL<n>-NEW-k`; rulings `R<n>-X` | OFL9 (2026-11-24) |
| **Retail** | MR-S / **S14** next | live (web `363d2b8`, gateways `1474e8a`; Upstox code-only, flag off) | `claude/retail/` | `retail-platform` (`docs/STATE.md`, phase docs; records → `docs/research/retail/`), `retail-gateway` | `TD-MR-n` in `tech_debt_retail.md` (own repo; next free 127) | S13 (2026-11-23) |
| **Futures OI** | MR-FOI / **FOI3** next (not in session) | research; live ingest Stage 0 next | `claude/futoi/` | `meridian-engine` `docs/research/futoi/` (5 tracked; result folders untracked on the box in `~/meridian-cc`, being committed via the S106 close); `C:\fyers_test` has **no git home** | `TD-FOI<n>-NEW-k` | FOI2 (2026-11-19) |
| **Board pin** | MR-PIN / **PIN4** in session | Board Pin is the gross pin (live 2026-11-25); V2 conformance and one-day backfill check PASS; full backfill accepted 2026-11-26; **step 9** (V1 against V2 on history) pre-registration frozen 2026-11-26, run pending; daily pin monitor from 2026-11-25 | `claude/pin/` | `meridian-engine` `docs/research/pin_proof/` (records on `main`: PR #2 `7eb3ba5`, PR #4 `5a96195`, PR #5 `934fe44`, PR #6 `6a69dbe`); check code on branch `pin/v2-check` | `TD-PIN<n>-NEW-k` | PIN3 (2026-11-25) |
| Parity (reference) | none | build closed 2026-10-09 (ADR-025); vendor watch only | `claude/parity_eval/` | `docs/research/parity_eval/` (from S106) and `docs/registers/archive/pk_only_2026-10-31*/` | engine IDs | — |

## 2. Engine-owned objects each lane touches

A lane may read these. It changes none of them itself: it files the change in its close inputs "Engine intake" section and the engine applies it (grants and DDL: engine authors, operator applies).

| Lane | Tables / views | Roles | Hosts / units / crons | Code |
|---|---|---|---|---|
| OFL | `tape_live_cycle/events/wall/label`; reads `v_gex_strike_rank`, `gex_cycle_history.pin_leader_strike` (the **net** quantity; shown on the Board as "Net peak" from 2026-11-25, not as "Pin") | `tape_w` (10 policies applied; **login proved 2026-11-24**), `merdian_ro` (R-2 applied) | production box `tape-live.service/.timer`, user `tapelive`, `/etc/tape-live/` (`tape-live.env`, `tape-w.env`); retail box `tape-runner.timer` 08:50; S3 bucket | `services/tape_live/`, `merdian_compute/tape/` |
| Retail | engine reference DDL (O4), Γ `_1pct` wrappers (ADR-032) | none on engine Supabase (own project) | engine → retail drop (ssh `retaildrop`, E1/E3/E10 live, E9 cron 08:20 daily); MALPHA Kite push to the engine `.env` (cron `45 0 * * 1-5`) | `merdian_compute` packaging |
| FOI | `fyers_futures_bars_1m`, `fyers_chain_bars_3m/_1m`, `historical_index_futures_1m`, `index_futures_snapshots` | `fyers_loader` | (live ingest: production box, not yet built) | Board futures-OI tile (design draft) |
| PIN | `v_gex_strike_rank`, `gex_cycle_history`, `hist_option_greeks_1m`; `v_gex_strike_rank_gross` and `v_gex_pin_gross` (live); `gex_strike_v2`, `gex_run_v2`, `p3b2_invariant_checks` (read as `merdian_ro`); `fyers_futures_bars_1m` grant undone 2026-11-23 | `merdian_ro` | production box trees `~/meridian-cc`, `~/meridian-v2-check`; the daily pin monitor (by hand, not scheduled) | `merdian_compute/gamma_v2.py` (independent check), Board pin |

## 3. Cross-lane dependencies (open)

| # | From → to | What | Owner of the next step | State |
|---|---|---|---|---|
| X1 | PIN → OFL | The Board Pin switched to the gross pin on 2026-11-25 about 18:08 IST. `/tape`'s PIN anchor still reads `gex_cycle_history.pin_leader_strike`, which was **not** redefined and is the Board's "Net peak". So `/tape` did not move, and it no longer anchors on what the Board calls "Pin". **The note required before the switch was not written before it** (AR §D.62.4); it is `docs/research/s107/engine_note_board_pin_switch_for_ofl_2026-11-26.md`. | OFL: decide at OFL10 whether `/tape` keeps the net anchor, moves to `v_gex_pin_gross`, or shows both; engine applies any grant | **open, with OFL** |
| X2 | PIN ↔ FOI | Greeks / forward question: **ruled one engine-lane study** (2026-11-21), fed by FOI3 item 1 and PIN's gamma-rate sensitivity (rate alone does not close the NIFTY gap: 5 → 5 of 12). | Engine | ruled; study not started |
| X3 | Engine → OFL | `tape_w` password step, V1–V5, login proof, E-1 probe, E-6 comments. | Engine: **E-4 contract INSERTs on the writer-start day**; the `''` confirmation for `tape_live_label.reason` and `tape_live_events.side` on the offline path | **done 2026-11-24 except the two items in the next-step cell** (`claude/ofl/MR_OFL9_close_inputs.md` §1) |
| X4 | Engine → Retail | One-login E1/E3/E10/E9 | Engine | **done 2026-11-21** (first live drop, `feed_adopted`); Sunday 11-22 second data point owed |
| X5 | Retail → Engine | MALPHA Kite push to the retail drop (cold storage brief), Kite load timer | Retail + MALPHA | held |
| X6 | FOI → PIN | `fyers_futures_bars_1m` grant to `merdian_ro` on a table FOI loaded | Operator | **done 2026-11-23**: undo run ~05:05 IST (`DROP POLICY ro_select_merdian`, `REVOKE SELECT ... FROM merdian_ro`); catalog read the same day: policies `loader_rw` only, no `merdian_ro` in the table ACL, `has_table_privilege` false |
| X7 | FOI → Engine (Board) | Futures-OI tile; Board background-tab staleness fix | Engine (Lovable) | design draft; fix sent? unknown |
| X8 | OFL ↔ Retail | Retail box shared: recorder 08:50–15:45, gateway blackout 08:45–15:45, heavy jobs outside | both | standing |
| X9 | OFL, FOI, PIN ↔ Engine | Production box shared: one CC session per tree, no box analysis 08:30–15:40 Mon–Fri, `ulimit -v`; `~/meridian-cc` is the PIN lane's working tree (engine closes use their own worktree) | all | standing |
| X10 | PIN → Engine | Gross-pin view revision 3. | — | **done**: applied 2026-11-23, rule-25 values in I-002 §3a, order check PASS; the ten-day shadow was dropped by the operator 2026-11-23; `data_contracts` row owed (TD-S107-NEW-2) |
| X11 | Engine ↔ PIN | Gamma V2 (ADR-033): tables applied and the stored history backfilled (19,050 runs). Standing notes: `claude/pin/to_engine_LATEST.md`, `claude/engine_to_pin_LATEST.md`. | PIN: step 9, the pre-registered comparison of V1 against V2. Engine: the `script_execution_log` read for writer provenance (TD-S107-NEW-6); then, only on the operator's decision, the eight-check gate for the writer hook and the `v_gex2_*` views as one family | open; **writer hook, `p3b2` job, views and Board tiles not approved** |
| X12 | OFL, PIN, Engine | Production box memory: 1,910 MB, no swap; tape 2b unit `MemoryMax=900M`; every lane's box job under `ulimit -v 700000`; a stray interactive process held 460 MB on 2026-11-24. | Operator: budget, swap or resize (TD-PIN2-NEW-12) | open |

## 4. Rollout of this protocol (tracked to completion)

| # | Item | Evidence that closes it | State |
|---|---|---|---|
| R1 | Operator rules STREAMS.md and Doc Protocol v5.1 | ruling 2026-11-21 ~09:52 IST, recorded in v5.1 | **done** |
| R2 | S106 engine doc-close + intake I-001 applied | doc-close commit sha, three-way sha, PK re-upload | **done** (`7c6e18c`; PK re-upload 2026-11-21) |
| R3 | Each lane's next close_inputs carries the "Engine intake" section | OFL9, MR-S13, FOI3, PIN2 close inputs | **done for OFL9, MR-S13, PIN2, PIN3** (taken in I-002 and I-003); FOI3 has not closed |
| R4 | FOI result folders committed; PIN after its seal | commit sha; `git status` clean for those paths | FOI in the S106 close; **PIN done** (records on `main`, PR #2, `7eb3ba5`) |
| R5 | OFL records (PK-only) committed to `docs/research/tape/`; 2b code per its own gate | commit sha | open (OFL close) |
| R6 | OFL docs moved to `claude/ofl/` in PK | project listing | open (OFL close) |
| R7 | Reference-product name removed from file names (I-001 E2) | `git mv` sha; PK listing | **done** (git `7c6e18c`; PK copies deleted 2026-11-21) |
| R8 | PK Protocol v1 in force (2026-11-21); pointers in project instructions, CLAUDE.md, STREAMS, v5.1, CURRENT | this commit sha; project-instructions line | **done** (`a71f232`, `3bc81fa`, `0b9aa10`) |
| R9 | First engine P6 run (PK Protocol): Tier A refresh, engine Tier C through P4, whole-PK audit, transition items T3 and T4 | PK delta in `docs/research/s107/S107_close_inputs.md` | in progress at the S107 close |
