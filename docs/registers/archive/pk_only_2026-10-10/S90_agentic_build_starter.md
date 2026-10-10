# S90 starter — begin the agentic-layer build (Stage 0)

You are working on MERDIAN, the operator's live, solo-built analytics engine for Indian index options (NIFTY, SENSEX). This session starts building the roadmap in `claude/agentic_layer_roadmap_S90.md` (v2.3, PROPOSAL). MERDIAN is **live during market hours**; nothing in this session may put capture at risk.

## Read first, in this order (project knowledge, before asking the operator anything)

1. `CLAUDE.md`, `CURRENT.md`, `MERDIAN_ClaudeCode_Guardrails.md`, `data-access.md`
2. `claude/agentic_layer_roadmap_S90.md` — all of §1–§4 and §11 (risk classes and controls). §5–§9 as needed
3. `ADR-030-per-cycle-layer-history.md` and `claude/ENH-133_schema_proposal_S89.md` (R0.4)
4. `ADR-016-parameter-calibration-pattern.md`, `ADR-029-model-routing-and-token-efficiency.md`, `ADR-023-read-path-recency-floors.md`, `ADR-020-calendar-absence-is-not-a-verdict.md`, `ADR-008-replay-architecture.md`
5. `tech_debt.md` entries: TD-081, TD-S82-NEW-3, TD-S69-NEW-2, TD-S89-NEW-1, TD-S54-NEW-1, TD-NEW-7, TD-NEW-L, and the ENH-83 / `merdian_parameters` write-path gap
6. `claude/ref_2026-10-01_SENSEX_0DTE.md` — the first golden day's expected readings

## Standing rules (unchanged from S89)

- Never name the parity target's product in docs, prompts, commits or file names; say "the parity target".
- Never read or print `.env` or any credential.
- Database access read-only via `bin/roq.sh` (`merdian_ro`). Bounded probes in market hours (09:00–15:45 IST); heavier reads after the close.
- Production changes only by push and `git pull --ff-only` after 16:00 IST, from the operator's terminal. Never write under `~/meridian-engine`.
- At a permission prompt the operator gives ONE thing (a bare option number). Ask for one action at a time.
- Read the record before reasoning about MERDIAN's history (Assumption Register D.28.8).
- Session close is when the operator says so. Do not remind.

## Go/no-go for this session (roadmap §2, §11.3)

- **May start now:** RO and OFF items.
- **Prepare, do not execute:** SC and LIVE items wait for rulings **A-5** (Stages 0–2 into parity scope) and **A-8** (spine ADR). Exception: **R0.4 ENH-133**, already ruled, applied by the operator after 16:00 IST today.

## Scope, in order

### 1. R0.1 — Spine inventory (RO). Deliverable: `claude/R0.1_spine_inventory_S90.md`

For each core product — `option_chain_snapshots`, `market_spot_snapshots`, `market_ticks`, `gex_strike_snapshots`, `gamma_metrics`, `volatility_snapshots`, `gex_cycle_history` (after apply):
- grain and key; rows per day per symbol (last 5 sessions);
- does it carry `run_id`, a source column, a code version, a config version?
- retention (pg_cron jobid 19 or none);
- RLS: `merdian_ro` policy present? anon revoked?
- writer (script, cron line, host) and main readers.

Also establish:
- `script_execution_log`: schema, what writes to it, coverage per job;
- ENH-71 `record_write`: what it records and where;
- ADR-029 ledger: location and schema;
- `merdian_parameters`: rows, keys, the read path, the missing write path;
- existing health outputs (`eod_health_check` and any status tables);
- compute paths that use wall-clock time or latest-only views (read-only grep of the repo; list file:line);
- `trading_calendar` state for the next 30 days;
- capacity snapshot: disk free, RAM free, database size per table, rows/day growth.

**End with a gap list mapped to R0.3, R0.5, R0.6, R0.7, R0.8 and R1.9**, stating for each what exists, what is missing, and the smallest additive change that would close it.

### 2. R0.4 — ENH-133 apply and acceptance (LIVE, already ruled)

Before 16:00: prepare the acceptance queries from `ENH-133_schema_proposal_S89.md` §9:
- per-symbol distinct-`ts` coverage;
- source-column introspection;
- the stored 10-02 rows landing `is_trading_session=false`;
- `held_for_cycles` behaviour on the 28–29 Sep NIFTY episode.

After the operator applies: run them, record evidence, update the tracker.

### 3. R2.1 — Golden day #1 frozen (OFF)

Design and, after the close, produce the frozen fixture for 2026-10-01 SENSEX:
- the input rows;
- the expected outputs (match against `ref_2026-10-01_SENSEX_0DTE.md` §7 and the replay SQL, sha256 `c7c1d4b7…`);
- where the fixture lives, and how the diff is run.

Do not wire it into the deploy path yet (that is SC).

### 4. R0.2 — Spine ADR draft (RO). Deliverable: an ADR draft in the repo's ADR format

Informed by the R0.1 gap list. Covers:
- the contract registry;
- the status vocabulary (OK / DEGRADED / STALE / MISSING / CLOSED, plus UNKNOWN when no fresh status exists);
- provenance columns;
- ledger consolidation (extend, don't add a fifth log);
- effective-dating via `merdian_parameters`;
- instrument calendars.

Present it for ruling A-8. Do not apply anything.

## Tracker discipline

- When an item moves, update `claude/agentic_layer_roadmap_S90.md`: §3 Status and Session columns, and §4 Current column, **with evidence linked** (doc path, query output, commit). No DONE without evidence.
- New findings that are defects go to `tech_debt.md` in its format; new assumptions to `MERDIAN_Assumption_Register.md`.

## Rulings to put to the operator when the work reaches them

A-5, A-8, A-13 first (they unlock Stage 0–1 SC/LIVE work). The rest of A-1…A-12 as they become relevant.

## Out of scope this session

- Any SC or LIVE change other than R0.4.
- Kite redundancy.
- Global context sources.
- Agents.
- MCP.
- Historic-data purchase. If raised, see roadmap §5.4.
