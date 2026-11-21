# STREAMS.md — MERIDIAN development lanes (hub register)

**Status: v0.2, ruled 2026-11-21 (operator, "as recommended"; Doc Protocol v5.1 Rules 12–16).** Git home: `docs/registers/STREAMS.md` (engine repo). Owner: the engine lane. Every lane reads this at session open; the engine updates it at every engine doc-close (v5.1 Rule 13) and the same day when a blocking dependency changes.

**What this file is for:** the one place that says which lanes exist, where each keeps its records, which engine-owned objects each touches, and what each is waiting on from another. Pointers and dependencies only; never a lane's results.

---

## 1. Lanes

| Lane | Series / open session | Status | Project folder | Git home | ID prefix (v5.1 Rule 14) | Latest close |
|---|---|---|---|---|---|---|
| **Engine (hub)** | S / **S106** open (covers 2026-11-05→11-21: `tape_w`, 2b and one-login answers, parity-target synthesis, pin basis and greeks notes, E1/E3/E10 build and deploy) | live | `claude/` root; `claude/intake/` | `meridian-engine`: registers `docs/registers/`, decisions `docs/decisions/`, research `docs/research/s<N>/` | `TD-S<N>-NEW-k`; mints ADR, ENH, AR §D, CASE for all lanes | **S105 git close `eba1193` (2026-11-05), merged `7c64e7d`**; S106 close in progress (`docs/s105-close` worktree) |
| **Order flow (tape)** | MR-OFL / **OFL9** in session | live; first 2b day earliest Mon 2026-11-23 | `claude/` root (`MR_OFL*`, `rulings_mr_ofl*`, `tape_*`, `2b_*`, `Q1_*`) → `claude/ofl/` at OFL's own close | code: `meridian-engine` branch `tape/live-l2` @ `56bf055` (+ `meridian-tape-staging`); 2b tree uncommitted on Local (9 modified, 7 untracked), held by the x5 gate; docs `docs/tape/` (10 tracked); records: **PK only** → `docs/research/tape/` at OFL's close | `TD-OFL<n>-NEW-k`; rulings `R<n>-X` | OFL8 (2026-11-16) |
| **Retail** | MR-S / **S13** in session | live (web, gateways, drop, adopter) | `claude/retail/` | `retail-platform` (`docs/STATE.md`, phase docs), `retail-gateway` | `TD-MR-n` in `tech_debt_retail.md` (own repo; next free 119) | S12 (2026-11-18); S13 progress 11-18 |
| **Futures OI** | MR-FOI / **FOI3** next (not in session) | research; live ingest Stage 0 next | `claude/futoi/` | `meridian-engine` `docs/research/futoi/` (5 tracked; result folders untracked on the box in `~/meridian-cc`, being committed via the S106 close); `C:\fyers_test` has **no git home** | `TD-FOI<n>-NEW-k` | FOI2 (2026-11-19) |
| **Board pin** | MR-PIN / **PIN2** in session | research (pin behaviour study v5 frozen 11-21) | `claude/pin/` | `meridian-engine` `docs/research/pin_proof/` (0 tracked; sealed folder on the box in `~/meridian-cc`, committed after the PIN2 seal) | `TD-PIN<n>-NEW-k` | PIN1 (2026-11-20) |
| Parity (reference) | none | build closed 2026-10-09 (ADR-025); vendor watch only | `claude/parity_eval/` | `docs/research/parity_eval/` (from S106) and `docs/registers/archive/pk_only_2026-10-31*/` | engine IDs | — |

## 2. Engine-owned objects each lane touches

A lane may read these. It changes none of them itself: it files the change in its close inputs "Engine intake" section and the engine applies it (grants and DDL: engine authors, operator applies).

| Lane | Tables / views | Roles | Hosts / units / crons | Code |
|---|---|---|---|---|
| OFL | `tape_live_cycle/events/wall/label`; reads `v_gex_strike_rank`, `gex_cycle_history.pin_leader_strike` | `tape_w` (10 policies applied; login owed), `merdian_ro` (R-2 applied) | production box `tape-live.service/.timer`, user `tapelive`, `/etc/tape-live/`; retail box `tape-runner.timer` 08:50; S3 bucket | `services/tape_live/`, `merdian_compute/tape/` |
| Retail | engine reference DDL (O4), Γ `_1pct` wrappers (ADR-032) | none on engine Supabase (own project) | engine → retail drop (ssh `retaildrop`, E1/E3/E10 live, E9 cron 08:20 daily); MALPHA Kite push to the engine `.env` (cron `45 0 * * 1-5`) | `merdian_compute` packaging |
| FOI | `fyers_futures_bars_1m`, `fyers_chain_bars_3m/_1m`, `historical_index_futures_1m`, `index_futures_snapshots` | `fyers_loader` | (live ingest: production box, not yet built) | Board futures-OI tile (design draft) |
| PIN | `v_gex_strike_rank`, `gex_cycle_history`, `hist_option_greeks_1m`, `fyers_futures_bars_1m` (grant to `merdian_ro`, 2026-11-20; undo at PIN2 close) | `merdian_ro` | — | `compute_gamma_metrics_local.py` (blank-leg-as-zero), Board pin |

## 3. Cross-lane dependencies (open)

| # | From → to | What | Owner of the next step | State |
|---|---|---|---|---|
| X1 | PIN → OFL | `/tape` PIN anchor (R-E) **is** the Board pin. PIN Stage 1 shows that pin is not the dominant-gamma strike on most runs. Any Board pin change moves the `/tape` anchor. | Engine: no Board pin change ships without an OFL note first | open; nothing authorised for the Board |
| X2 | PIN ↔ FOI | Greeks / forward question: **ruled one engine-lane study** (2026-11-21), fed by FOI3 item 1 and PIN's gamma-rate sensitivity (rate alone does not close the NIFTY gap: 5 → 5 of 12). | Engine | ruled; study not started |
| X3 | Engine → OFL | `tape_w` password step, V2/V3/V5, login proof; cleanup SQL; E-1/2/4/6; `''` confirmation. Blocks the first live 2b day. Policies and R-2 are applied (read 2026-11-21). | Engine | open |
| X4 | Engine → Retail | One-login E1/E3/E10/E9 | Engine | **done 2026-11-21** (first live drop, `feed_adopted`); Sunday 11-22 second data point owed |
| X5 | Retail → Engine | MALPHA Kite push to the retail drop (cold storage brief), Kite load timer | Retail + MALPHA | held |
| X6 | FOI → PIN | `fyers_futures_bars_1m` grant to `merdian_ro` on a table FOI loaded | Operator | keep until PIN2 closes, then undo |
| X7 | FOI → Engine (Board) | Futures-OI tile; Board background-tab staleness fix | Engine (Lovable) | design draft; fix sent? unknown |
| X8 | OFL ↔ Retail | Retail box shared: recorder 08:50–15:45, gateway blackout 08:45–15:45, heavy jobs outside | both | standing |
| X9 | OFL, FOI, PIN ↔ Engine | Production box shared: one CC session per tree, no box analysis 08:30–15:40 Mon–Fri, `ulimit -v`; `~/meridian-cc` is the PIN lane's working tree (engine closes use their own worktree) | all | standing |

## 4. Rollout of this protocol (tracked to completion)

| # | Item | Evidence that closes it | State |
|---|---|---|---|
| R1 | Operator rules STREAMS.md and Doc Protocol v5.1 | ruling 2026-11-21 ~09:52 IST, recorded in v5.1 | **done** |
| R2 | S106 engine doc-close + intake I-001 applied | doc-close commit sha, three-way sha, PK re-upload | in progress (Phase 1, 1b done; archive commit next) |
| R3 | Each lane's next close_inputs carries the "Engine intake" section | OFL9, MR-S13, FOI3, PIN2 close inputs | open (paste-in text given to the operator) |
| R4 | FOI result folders committed; PIN after its seal | commit sha; `git status` clean for those paths | FOI in the S106 close; PIN open |
| R5 | OFL records (PK-only) committed to `docs/research/tape/`; 2b code per its own gate | commit sha | open (OFL close) |
| R6 | OFL docs moved to `claude/ofl/` in PK | project listing | open (OFL close) |
| R7 | Reference-product name removed from file names (I-001 E2) | `git mv` sha; PK listing | in progress (two PK docs renamed in the S106 archive; the git spec file renamed in Phase 2) |
