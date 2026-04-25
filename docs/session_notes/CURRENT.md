# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."

---

## Last session

| Field | Value |
|---|---|
| **Date** | 2026-04-23 (Session 7 — diagnosis + close) and 2026-04-24 (Friday post-market — verification + research backlog) |
| **Concern** | Session 7 closed yesterday (breadth cascade root cause). Today's work was Friday-equivalent verification (first trading day after Session 7 closed) plus translating today's market observation into a research backlog. |
| **Type** | Production verification + research backlog formation. No code change. |
| **Outcome** | DONE — Session 7's fix proven in production. 7 experiments queued. 3 new TDs surfaced for Session 8. |
| **Git start → end** | `31970d1` → `6ea2829` → `ce89ca4` |
| **Local + AWS hash match** | Local at `ce89ca4`. AWS still at `2c130bb` (no AWS-side commits today). Drift is intentional — AWS doesn't need today's research/docs commits. |
| **Files changed (code)** | None |
| **Files modified (docs)** | `MERDIAN_Experiment_Compendium_v1.md` (+197 lines, Exp 17-23 backlog section) |
| **Files added (tracked)** | None |
| **Files added (untracked, gitignored)** | `preflight_20260424.py` (one-off scratch; proper preflight system already exists at `run_preflight.py` — see TD-NNN below) |
| **Tables changed** | None |
| **Cron added/changed** | None |
| **`docs_updated`** | YES |

### What today did, in 6 bullets

- **Production verification: Session 7 fix works end-to-end.** First post-open cycle 09:31 IST showed `291 ADV / 983 DEC / BEARISH (-52)` — directionally correct against the actual market tape (NIFTY -106 pts at 09:31 → -275 pts EOD at 23,898). The 27-day "1,270 ADV / 50 DEC / BULLISH 92" pattern is gone. `equity_intraday_last` populated fresh at 09:05 IST cron; `ws_feed_zerodha.py` connected at 09:14 IST; `ingest_breadth_from_ticks.py` computed against fresh reference. Every layer of the fix observed working.
- **Pre-market token chaos resolved.** Kite token: AUTH FAILED on both boxes despite identical token strings; fresh `refresh_kite_token.py` returned the SAME token but server-side state re-activated it. Dhan token: scheduled 08:15 IST task fired and produced `Invalid TOTP`; manual `refresh_dhan_token.py` at 09:03 IST succeeded. AWS Dhan pulled via `pull_token_from_supabase.py`. Both tokens validated before market open.
- **ICT HTF zones rebuilt for 2026-04-24.** `python build_ict_htf_zones.py --timeframe D` produced 4 NIFTY (1 D + 3 W) and 5 SENSEX (2 D + 3 W) active zones. `--timeframe H` returned 0 zones for both — investigation showed this is structurally correct (1H builder requires ≥ 2 completed hours of today's session; pre-market run is a no-op).
- **TradingView Pine script regenerated.** `MERDIAN_ICT_HTF_Zones_v20260424.pine` (98 lines) replaces v20260421. Down from 22 NIFTY zones / 18 SENSEX zones to 4/5 — historical 2025-era BEAR_OBs expired via breach filter. Captures NIFTY's price-INSIDE-W-BULL_FVG-24,074-24,241 positioning that proved critical post-open.
- **Today's market observation captured as research backlog.** NIFTY opened inside W BULL_FVG, broke below the lower edge, cascaded through unprotected territory to -275 pts EOD. `MERDIAN_Experiment_Compendium_v1.md` extended with 7 proposed experiments (Exp 17-23) covering: BULL zone break-below cascade, BEAR zone break-above confirmation, liquidity sweeps, open range breaks, gap behavior, zone confluence, and (most importantly per ADR-001) local-vs-net gamma divergence. Commit `6ea2829`.
- **Three new TDs surfaced, not yet filed.** (1) Existing `run_preflight.py` 4-stage system was unknown to today's chat — wasted effort writing `preflight_20260424.py` from scratch. (2) Dhan TOTP root cause unknown — task fired and failed; manual succeeded with same seed. Worth diagnosing before it recurs. (3) 1H ICT zone builder needs a post-market cron sibling (currently only `--timeframe D` is in cron; H must be run manually post-15:30).

---

## This session

> Session 8. Pick ONE primary path from below at session start.

### Candidate A (recommended) — Phase 4A posture ADR + verify Monday 09:15 IST cascade still works

| Field | Value |
|---|---|
| **Goal** | (1) Verify Monday 2026-04-27 09:15 IST cron + breadth pipeline still produce correct output (was Friday a one-off?). (2) Write `ADR-002-phase-4a-breadth-corruption-acknowledgement.md` formalizing: "27-day breadth corruption did not reach trading P&L because of LONG_GAMMA gating; continuing Phase 4A with override monitoring." |
| **Type** | Live verification + governance documentation. |
| **Success criterion** | Three queries from this CURRENT.md verification block PASS, then ADR-002 committed. |
| **Time budget** | ~20 exchanges. |

### Candidate B — Experiment 17 backfill (BULL zone break-below cascade)

| Field | Value |
|---|---|
| **Goal** | Build `experiment_17_bull_zone_break_cascade.py` per spec in Compendium §Experiment 17. Direct test of yesterday's NIFTY observation: does breaking below an active W BULL_FVG/BULL_OB produce statistically more bearish T+30/60/EOD returns? |
| **Type** | Backtest research script. Pure read against `ict_htf_zones` (incl. EXPIRED) joined with `hist_spot_bars_5m`. |
| **Success criterion** | Sample size ≥ 30 events; result table written; verdict block added to Compendium Exp 17 entry; if PASS criteria met, ENH candidate proposed. |
| **Time budget** | ~30-40 exchanges. |

### Candidate C — Kite token propagation automation (C-10)

| Field | Value |
|---|---|
| **Goal** | Implement either (a) Local Windows post-hook that propagates new token to MERDIAN AWS via SSH+sed after `refresh_kite_token.py`, or (b) pre-flight `kite.profile()` check on MERDIAN AWS at 09:10 IST with Telegram alert on failure. Closes C-10. |
| **Type** | Code change (operational automation). |
| **Success criterion** | Chosen path lands with a test run, runbook updated, C-10 marked CLOSED in `merdian_reference.json` (v10 → v11). |
| **Time budget** | ~30 exchanges. |

### Candidate D — TD-NNN-B source_ts freshness check across 6 JSONB blocks

| Field | Value |
|---|---|
| **Goal** | Add staleness gating to `build_market_state_snapshot_local.py` so every JSONB block (breadth, gamma, volatility, momentum, WCB, futures) validates `source_ts` against `now()` and rejects/downgrades if > N minutes old. Generalizes Session 7's lesson. |
| **Type** | Architectural code change — touches signal pipeline heart. |
| **Success criterion** | `validate_feature_freshness(block, max_age_secs)` helper exists, applied to all 6 blocks, configurable thresholds. Canary run shows expected behaviour. |
| **Time budget** | ~40-50 exchanges. Touches live signal generation; careful testing required. |

### DO_NOT_REOPEN

- Capital ceiling values (₹50L / ₹25L / ₹2L)
- Strategy choice (Half Kelly C for live start)
- T+30m exit timing
- 5m vs 1m for ICT — 5m is the rule
- OI-* namespace — permanently closed
- ENH-72 scope — permanently closed
- V19A/V19B/V19C as per-session canonical outputs — under v3, routine sessions don't produce appendices
- Em-dashes in git commit subjects — ASCII-only
- PS 5.1 `Get-Content` display corruption — known (TD-010)
- `python -c` for multi-line string replacement in PowerShell — always write a `fix_*.py` script instead
- Breadth cascade root cause (C-09 CLOSED) — fix proven in production 2026-04-24 09:31 IST. Do not re-diagnose.
- Contamination registry approach (Path D) — chosen over per-table flags / recomputation.
- **NEW: 1H ICT zone builder pre-market silence** — investigated 2026-04-24. Code is correct; pre-market `--timeframe H` is structurally a no-op (needs ≥ 2 completed session hours). Not a bug. Filed as TD for post-market cron sibling.
- **NEW: Kite "AUTH FAILED then AUTH OK with identical token"** — known Zerodha behaviour. Do fresh `refresh_kite_token.py` even if returned token is identical; the act of running re-activates server-side session state. Captured in runbook failure-modes (Session 8 to add row).

### Watch-outs for Candidate A

- Don't expand scope. If Monday's verification PASSES, write the ADR. If it FAILS, that's a new C-NN (investigate), NOT a Session 8 redirect.
- ADR-002 is a decision document, not an apology. Frame in terms of evidence: 27-day wrong-breadth did not reach P&L because LONG_GAMMA gating was orthogonal. State the posture and move on.

### Watch-outs for Candidate B

- The script `build_ict_htf_zones.py` reads `hist_spot_bars_1m` (NOT `hist_spot_bars_5m` for daily zones). Today's check confirmed `bar_ts` is the timestamp column. Use the same conventions in Exp 17 script — don't fight the codebase.
- Status filter is `status = 'ACTIVE'`. Pattern column is `pattern_type`. Confirmed 2026-04-24.
- **Sample for "active at break time":** zone may have `status = 'EXPIRED'` now but was `'ACTIVE'` when the break occurred. Need to query `ict_htf_zones` history including EXPIRED rows, then filter by `valid_from <= bar_ts AND valid_to >= bar_ts AND (broken_at_date IS NULL OR broken_at_date >= bar_ts)`. The exact lifecycle column logic needs verification by inspecting one EXPIRED row carefully.

### Watch-outs for Candidate C

- MeridianAlpha is NOT out-of-scope from MERDIAN — cross-system diagnosis is fine. But code changes belong in whichever repo owns the file.
- Pre-flight check (Option b) must not fail-open. Test all four branches: token valid, token stale, Kite API down, network failure.

### Watch-outs for Candidate D

- Each JSONB block has its own `source_ts` field name. No universal schema. Helper must accept a per-block lookup function.
- Don't block signals on first-5-minute staleness. ICT needs 3 bars minimum; threshold per block, not global.
- Strongly recommend doing Candidate A's verification step (5 min, just three SQL queries) before this; otherwise we're blind to whether Session 7's fix still works.

---

## New TDs to file at Session 8 start

These surfaced today but were not formally entered into `tech_debt.md`. First 2 minutes of Session 8 should add them:

| ID (proposed) | Severity | Description | Origin |
|---|---|---|---|
| TD-015 | S3 | Existing `run_preflight.py` 4-stage system (env / auth / db / runner_drystart) is undocumented; not in any runbook; today's session re-invented it as `preflight_20260424.py` (now untracked). Action: write runbook explaining stages and triggers; retire the one-off. | 2026-04-24 morning preflight |
| TD-016 | S3 | Dhan TOTP root cause unknown. 08:15 IST scheduled task fired and returned `Invalid TOTP`; manual `refresh_dhan_token.py` at 09:03 IST succeeded with same seed. Possible causes: clock drift not surfaced by `w32tm`, seed cache, Dhan-side rate-limit. Action: 30-min diagnosis next time it recurs; capture exact error context. | 2026-04-24 08:15 IST task |
| TD-017 | S3 | `build_ict_htf_zones.py --timeframe H` has no scheduled invocation. Daily `--timeframe D` runs at 09:00 IST cron; H requires post-market data and currently only runs manually. Action: add post-market cron at 16:15 IST (after EOD ingest) for `--timeframe H`. Possibly closes OI-11. | 2026-04-24 pre-market H run returned 0 |
| TD-018 (minor) | S4 | `build_ict_htf_zones.py:468` uses deprecated `datetime.utcnow()`. Migrate to `datetime.now(datetime.UTC)`. | 2026-04-24 D build deprecation warning |

### Re-upload to project knowledge (CLAUDE.md Rule 12)

Files changed across Session 7 close + 2026-04-24 work that should be re-uploaded to project knowledge for future `project_knowledge_search`:

- `CLAUDE.md` (v1.3) — Session 7 added Rule 13
- `docs/session_notes/CURRENT.md` (THIS file) — Session 7 close + Friday post-market
- `docs/session_notes/session_log.md` — Session 7 one-liner
- `docs/registers/merdian_reference.json` (v10)
- `docs/registers/MERDIAN_Experiment_Compendium_v1.md` (v1 with Proposed section)
- `docs/runbooks/runbook_update_kite_flow.md` (filled)
- `docs/decisions/ADR-001-stable-lies-defeat-duration-gates.md` (new)

Total 7 files. Bundle re-upload as one operation.

---

## Live state snapshot (at Session 8 start)

| Component | State |
|---|---|
| **Live trading** | Phase 4A — manual execution. 2026-04-24 trading day produced BULL_FVG TIER2 signals on both NIFTY and SENSEX intraday, all BLOCKED by LONG_GAMMA gate. No manual trades reported. |
| **Shadow gate** | All 10 sessions PASSED (closed 2026-04-15) — caveat: ran on corrupted breadth. ADR-002 (Candidate A) formalizes posture. |
| **Breadth pipeline** | FIXED and verified in production 2026-04-24 09:31 IST. `refresh_equity_intraday_last.py` cron 09:05 IST daily. |
| **Local env** | Windows Task Scheduler. PS 5.1 with UTF-8 profile. Git CRLF auto-conversion (cosmetic). |
| **AWS env** | MERDIAN AWS `i-0878c118835386ec2` (eu-north-1). 11 cron jobs total. Shadow runner FAILED since 2026-04-15 (pre-existing). |
| **MeridianAlpha AWS** | `13.51.242.119`. `refresh_kite_token.py` ~06:00 IST manual browser login. Token propagation to MERDIAN AWS still manual SSH+sed (C-10 OPEN). |
| **Local git HEAD** | `ce89ca4` (in sync with origin/main) |
| **Last canary tag** | none — Friday was research/observation only |
| **Open C-N (critical)** | C-10 HIGH OPEN (Kite token propagation manual) |
| **Open TD S1** | none |
| **Open TD S2** | TD-002 (breadth_regime backfill) — scope reduced by C-09 fix; reassess in Session 8 |
| **Open TD S3** | TD-001, TD-004, TD-005, TD-006, TD-007 (existing) + TD-015, TD-016, TD-017 (new from 2026-04-24, not yet filed) |
| **Open TD S4** | TD-009, TD-010 (existing) + TD-018 (new minor, datetime.utcnow deprecation) |
| **Closed in Session 7** | C-09, TD-014 |
| **Open from Session 7** | ADR-002 phase-4a-posture (Candidate A this session) |
| **Active research backlog** | Exp 17-23 in Compendium (NEW). Exp 17 = Candidate B this session. |
| **Active ENH in flight** | none |
| **Data contamination** | `BREADTH-STALE-REF-2026-03-27` registered. 27-day window 2026-03-27 → 2026-04-23. Guard with `WHERE NOT public.is_breadth_contaminated(ts)`. |

---

## Mid-session checkpoints

> Per Session Management Rule 1: every ~20 exchanges, write 5 bullets here. Do not wait until session end.

### Checkpoint 1 (~20 exchanges)
- Fixed:
- Confirmed:
- Open:
- Changed:
- Next:

### Checkpoint 2 (~40 exchanges)
- Fixed:
- Confirmed:
- Open:
- Changed:
- Next:

### Checkpoint 3 (~60 exchanges)
- Fixed:
- Confirmed:
- Open:
- Changed:
- Next:

### Checkpoint 4 (~80 exchanges)
- Fixed:
- Confirmed:
- Open:
- Changed:
- Next:

---

## Session-end checklist (before commit)

```
[ ] CURRENT.md updated — "Last session" reflects THIS session, "This session" reset for next
[ ] session_log.md appended (one line)
[ ] merdian_reference.json updated for any file/table/item status change
[ ] tech_debt.md updated if any TD added, mitigated, or closed (TD-015 through TD-018 from 2026-04-24 still need filing)
[ ] Enhancement Register updated if architectural thinking happened
[ ] Local + AWS hash match confirmed if code changed
[ ] All commits prefixed: MERDIAN: [ENV|DATA|SIGNAL|OPS|RESEARCH] <scope> — <intent>
[ ] Re-upload to project knowledge any of CURRENT.md / session_log.md / merdian_reference.json / tech_debt.md / Enhancement_Register / CLAUDE.md / docs/operational/* that changed (Rule 12)
[ ] Phase boundary check: any Master/Appendix .docx generation triggered? (rare)
[ ] Runbook review: any operation explained for 2nd time? Create runbook from RUNBOOK_TEMPLATE.md
[ ] data_contamination_ranges review: new contamination this session? INSERT row (Rule 13)
```

---

## Monday 2026-04-27 09:15 IST verification queries (Candidate A first step)

```sql
-- 1. Confirm 09:05 cron fired and wrote fresh reference for Monday
SELECT
    (MAX(ts) AT TIME ZONE 'Asia/Kolkata')::timestamp AS latest_ref_ist,
    COUNT(DISTINCT ticker) AS distinct_tickers
FROM public.equity_intraday_last;
-- Expected: ~09:05 IST Monday, ~1,330+ tickers

-- 2. First breadth cycle Monday post-09:15 reads realistic
SELECT
    (ts AT TIME ZONE 'Asia/Kolkata')::timestamp AS ts_ist,
    advances, declines, universe_count, breadth_score, breadth_regime
FROM public.market_breadth_intraday
WHERE ts >= '2026-04-27 09:15:00+05:30'
ORDER BY ts
LIMIT 3;
-- Expected: realistic adv/dec, NOT 1,270/50

-- 3. Instrumentation firing SUCCESS rows
SELECT
    (started_at AT TIME ZONE 'Asia/Kolkata')::timestamp AS started_ist,
    exit_code, exit_reason, contract_met, actual_writes
FROM public.script_execution_log
WHERE script_name = 'ingest_breadth_from_ticks.py'
  AND started_at >= '2026-04-27 09:00:00+05:30'
ORDER BY started_at
LIMIT 5;
-- Expected: exit_reason='SUCCESS', contract_met=true
```

These queries are identical to the 2026-04-24 verification (just date-shifted). The 2026-04-24 results are recorded in this CURRENT.md "What today did" block — first cycle 09:31 IST returned 291/983 BEARISH, fully clean.

---

*CURRENT.md — overwrite each session. Never branch this file. Never archive (the session_log is the archive).*
*Last updated 2026-04-24 16:30 IST (Friday post-market — Session 7 close + research backlog formation).*
