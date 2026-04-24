# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."

---

## Last session

| Field | Value |
|---|---|
| **Date** | 2026-04-23 (IST, full day — investigation pre-market through post-market writeup) |
| **Concern** | Investigate the 2026-04-22 10:55 IST NIFTY BULL_FVG blocked-signal to determine whether the CONF 32 block was correct behaviour or an artifact of suspected zero breadth coverage. |
| **Type** | Diagnosis → code fix → instrumentation → governance. Single concern held end-to-end: "breadth cascade." |
| **Outcome** | DONE — root cause identified and fixed for good (C-09 CLOSED). Expanded scope uncovered 27 trading days of fabricated breadth data spanning 29 downstream tables; documented via contamination registry rather than backfill. New open item C-10 (Kite token propagation manual/fragile) flagged for Session 9. Five commits landed; Local ↔ origin synced. |
| **Git start → end** | `f8a3888` → `2c130bb` → `1630726` → `befe721` → `04d91a0` → `48d1b6e` |
| **Local + AWS hash match** | Local at `48d1b6e`. AWS at `2c130bb` (writer-side commit — AWS disk is the ground truth for `refresh_equity_intraday_last.py`, doesn't need later commits since subsequent changes were to Local-side files only). No drift concern. |
| **Files changed (code)** | `refresh_equity_intraday_last.py` (NEW — created on MERDIAN AWS), `ingest_breadth_from_ticks.py` (instrumented with `_write_exec_log()` helper) |
| **Files added (tracked)** | `docs/runbooks/runbook_update_kite_flow.md` (FILLED from stub — 134 new lines), plus new AWS-side script above |
| **Files modified (docs)** | `CLAUDE.md` (v1.2 → v1.3 + Rule 13), `docs/registers/merdian_reference.json` (v9 → v10) |
| **Tables changed** | NEW `public.data_contamination_ranges` (Supabase), NEW function `public.is_breadth_contaminated(timestamptz)`, one row inserted: `BREADTH-STALE-REF-2026-03-27` |
| **Cron added** | MERDIAN AWS: `35 3 * * 1-5` (09:05 IST Mon-Fri) — runs `refresh_equity_intraday_last.py` |
| **`docs_updated`** | YES |

### What this session did, in 8 bullets

- **Root cause identified and closed (C-09 CLOSED).** `equity_intraday_last` (the breadth writer's reference-price table) had not been updated since 2026-03-27 15:30 IST. The C-08 fix on 2026-04-16 retired `ingest_breadth_intraday_local.py` (the Dhan-REST writer) and replaced it with `ingest_breadth_from_ticks.py`, but the retired writer had TWO responsibilities — compute breadth AND maintain the reference — and only the first was replaced. Every live breadth compute for 27 trading days compared today's LTPs against a frozen month-old reference, producing fabricated "BULLISH 92.x" values on objectively bearish days.
- **Fix-for-good deployed.** New script `refresh_equity_intraday_last.py` on MERDIAN AWS fetches prev-session close via Kite REST `ohlc()` for ~1,330 NSE breadth-universe symbols and UPSERTs to `equity_intraday_last`. Scheduled daily 09:05 IST via cron. Manual test 2026-04-23 18:02 IST wrote 1,330 rows in 4.5s. Simulated compute against late-day ticks with fresh reference matched NSE NIFTY 500 authoritative 32/68 adv/dec ratio (MERDIAN 429/875 on 1,330-universe = 32/68; NSE 158/342 on 500-universe = 32/68). Zero drift between MERDIAN and authoritative source.
- **Write-contract instrumentation added (TD-014 CLOSED).** `ingest_breadth_from_ticks.py` now writes one row to `script_execution_log` per invocation (host=`local`, contract_met=True iff coverage_pct ≥ 50% AND market_breadth_intraday write succeeded). Exit reasons use the `chk_exit_reason_valid` enum (SUCCESS / SKIPPED_NO_INPUT / DATA_ERROR). This is what would have caught the 27-day silent failure.
- **Kite token propagation flagged as architectural gap (C-10 OPEN).** Root cause of 2026-04-22's full-day WebSocket outage was skipping Step 2 of the morning token-refresh sequence (manual SSH + `sed` patch on MERDIAN AWS `.env`). Mechanism is documented in AppendixV18H_v2 §7.1 and Master V19 §5.1; no automation exists; no pre-flight verification catches a skipped step. Captured as C-10 for Session 9 — proposed fixes are either automated SSH+sed post-hook or pre-flight `kite.profile()` check with Telegram alert.
- **Runbook filled (`runbook_update_kite_flow.md`).** Stub → 179-line rebuild-grade runbook with explicit 3-step procedure, mandatory `profile()` verification as Step 3, failure-mode table, downstream consumer list, and the 2026-04-22 skipped-Step-2 failure mode captured as the runbook's first real entry. Honours CLAUDE.md Rule 11.
- **Data contamination registry created.** New Supabase table `public.data_contamination_ranges` centralizes known data-integrity incidents, replacing per-table flag columns (which don't scale — 29 downstream tables carry tainted breadth fields). Helper function `is_breadth_contaminated(ts)` lets any research query guard against it. CLAUDE.md v1.3 Rule 13 directs future researchers to check this registry before breadth queries.
- **Governance lesson captured (ADR pending).** Session surfaced a structural governance hole: 10-session shadow gate (PASSED 2026-04-15) cannot detect a stable lie. Breadth was systematically wrong across all 10 gate sessions in a consistent direction, but stability-based gates measure whether values are *steady*, not whether they're *correct*. Fix-for-good requires cross-reference validation (external source or internal consistency check) every cycle — not just duration-based stability testing. Draft ADR is Tier 3 Item 3 of this session's close; will land in `docs/decisions/` before session close.
- **Live-trading posture.** Through the full day of wrong breadth (today and preceding 27 days), live signals were protected by the ENH-35 LONG_GAMMA hard gate — every BULL_FVG that fired with fabricated BULLISH breadth was blocked by LONG_GAMMA anyway. No money was lost to this class of failure. However, Navin took several of the BLOCKED TIER2 BULL_FVG signals manually and realized ~30% on capital (options leverage on directionally correct pattern calls) — suggesting the LONG_GAMMA blanket block may be over-scoped per Experiments 11+12 findings (OB/FVG regime-independent edge). Noted for Session 9+ research.

---

## This session

> Session 8. Pick ONE from the candidates below at session start. DO NOT combine — each is independent work with its own watch-outs.

### Candidate A (recommended) — Verify Monday morning cascade + Phase 4A posture statement

| Field | Value |
|---|---|
| **Goal** | Confirm 2026-04-24 09:05 IST cron fired, breadth reads realistic, then write a formal Phase 4A posture statement acknowledging the 27-day corruption window and its non-impact on live trading (LONG_GAMMA gate protected us). |
| **Type** | Live verification + documentation. No code change. |
| **Success criterion** | (1) `equity_intraday_last.latest_ref_ts` ~2026-04-24 09:05 IST with ~1,330 tickers. (2) First 09:20 IST `market_breadth_intraday` row shows realistic adv/dec ratios — NOT the 1,270/50 pattern. (3) Posture statement committed to `docs/decisions/ADR-00X-phase-4a-breadth-corruption-acknowledgement.md` covering scope, blast radius, mitigation, and conclusion "continue Phase 4A with override monitoring." |
| **Relevant files** | `docs/decisions/` (NEW ADR), `merdian_reference.json` (cross-ref the ADR from C-09 entry) |
| **Relevant tables** | `equity_intraday_last`, `market_breadth_intraday`, `script_execution_log`, `data_contamination_ranges` |
| **Time budget** | ~20 exchanges. |

### Candidate B — Kite token propagation automation (C-10)

| Field | Value |
|---|---|
| **Goal** | Implement one of two options: (a) Local Windows post-hook that SSH+seds the new token to MERDIAN AWS after `refresh_kite_token.py` completes on MeridianAlpha, OR (b) pre-flight `kite.profile()` check on MERDIAN AWS at 09:10 IST with Telegram alert on failure. Option (b) is lower-effort and catches more failure modes; Option (a) solves the specific forgotten-step failure. |
| **Type** | Code change (automation). |
| **Success criterion** | The chosen path lands with a test run, runbook updated to reflect automation, C-10 CLOSED in merdian_reference.json. |
| **Relevant files** | Depends on path — `refresh_kite_token.py` (MeridianAlpha) + new push script for (a), OR new `preflight_kite_auth.py` on MERDIAN AWS for (b). |
| **Time budget** | ~30 exchanges. |

### Candidate C — TD-NNN-B source_ts freshness check across all 6 JSONB feature blocks

| Field | Value |
|---|---|
| **Goal** | Add staleness gating to `build_market_state_snapshot_local.py` so every JSONB block (breadth, gamma, volatility, momentum, WCB, futures) validates `source_ts` against `now()` and rejects/downgrades if > N minutes old. Generalizes the Session 7 lesson to all feature blocks. |
| **Type** | Architectural code change — touches the signal pipeline heart. |
| **Success criterion** | Helper `validate_feature_freshness(block, max_age_secs)` exists, applied to all 6 blocks, with configurable thresholds. `build_trade_signal_local.py` handles `UNKNOWN`/`STALE` regime values gracefully (skips breadth-dependent scoring, doesn't block on breadth alone). Canary run produces expected behaviour. |
| **Time budget** | ~40-50 exchanges. Risk: touches live signal generation; requires careful testing. |

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
- `python -c` for multi-line string replacement in PowerShell — always write a `fix_*.py` script instead (Session 7 reinforced this multiple times)
- **NEW: Breadth cascade root cause** — `equity_intraday_last` staleness diagnosed and fixed (C-09). Do not re-diagnose. Any future breadth anomaly is either (a) a new issue, (b) a cron that didn't fire, or (c) a newly-stale reference from a different mechanism — investigate from that framing, not C-09's.
- **NEW: Contamination registry approach (Path D)** — chosen over per-table flags (Path A) and recomputation (Path B) because 29+ tables carry tainted breadth fields. Registry + SQL helper is the agreed approach; do not re-debate.

### Watch-outs for Candidate A

- **Do not expand scope.** Verification is a 5-query job; posture ADR is a 30-minute write. If the cron failed or breadth is still wrong, that's a new C-NN (investigate), NOT "Session 8 redirects to re-fix." Candidate A presumes the cron fired correctly; branch to Candidate B-equivalent only on actual failure.
- **Posture statement is a decision, not an apology.** Claude should frame the ADR in terms of what the evidence actually shows — 27-day wrong-breadth did not reach trading P&L because of LONG_GAMMA gating — not paper over it. Honest record.

### Watch-outs for Candidate B

- **Don't touch any Python on MeridianAlpha box without confirming the scope.** It's a separate repo from MERDIAN. Per Session 7 correction, MeridianAlpha is NOT out-of-scope from MERDIAN register (that was a misreading) — cross-system diagnosis is fine — but code changes belong in whichever repo owns the file.
- **Pre-flight check (Option b) must not fail-open.** If the `profile()` test hangs or returns ambiguous errors, the alert must still fire. Testing should cover: token valid (no alert), token stale (alert), Kite API down (alert), network failure (alert). Four branches.

### Watch-outs for Candidate C

- **Every feature block has its own `source_ts` field layout.** Breadth uses `raw_ref_ts`; gamma may use `computed_at` or nothing; volatility uses VIX tick timestamp; momentum uses spot tick timestamp; WCB uses per-symbol basket timestamps. No universal schema — helper must accept a lookup function per block.
- **Don't block signals on first-5-minute staleness.** At 09:15 IST, some blocks naturally lag (ICT needs 3 bars minimum = 09:30 IST earliest). Threshold per block, not global.
- **This work, if done without Candidate A first, leaves us blind to whether the Session 7 fix itself works.** Strongly recommend A before C. Alternatively, do the Monday-morning verification query first as a 5-minute precursor to Candidate C.

---

## Live state snapshot (at session start)

| Component | State |
|---|---|
| **Live trading** | Phase 4A — manual execution. First live NIFTY/SENSEX signals this week (all BLOCKED by LONG_GAMMA gate). Navin took multiple BLOCKED signals manually; realized ~30% on capital via options leverage. Detection layer validated; blocking layer possibly over-scoped (ENH-35 question). |
| **Shadow gate** | All 10 sessions PASSED (closed 2026-04-15) — **but with known caveat: gate ran on corrupted breadth data throughout.** See ADR-pending for posture. |
| **Breadth pipeline** | FIXED as of 2026-04-23. `refresh_equity_intraday_last.py` scheduled 09:05 IST daily. Next verification: 2026-04-24 09:15 IST. |
| **Local env** | Windows Task Scheduler, 13 MERDIAN tasks incl. `MERDIAN_Intraday_Supervisor_Start` running `run_option_snapshot_intraday_runner.py` which invokes `ingest_breadth_from_ticks.py` every 5 min. PS 5.1 profile with UTF-8 output. |
| **AWS env** | MERDIAN AWS `i-0878c118835386ec2` (eu-north-1). Runs `ws_feed_zerodha.py` (09:14 IST cron) + `refresh_equity_intraday_last.py` (09:05 IST cron). Shadow runner FAILED since 2026-04-15 (pre-existing, not this session). |
| **MeridianAlpha AWS** | `13.51.242.119`. Runs `refresh_kite_token.py` (manual browser login, ~06:00 IST target). Token propagation to MERDIAN AWS is manual SSH+sed (C-10). |
| **Local git HEAD** | `48d1b6e` (in sync with origin/main) |
| **Last canary tag** | none this session — diagnosis + fix work |
| **Open C-N (critical)** | **C-10 HIGH OPEN** (Kite token propagation manual) — C-09 CLOSED this session |
| **Open TD S1** | none |
| **Open TD S2** | TD-002 (breadth_regime backfill Apr–Jul 2025) — scope changed by this session's C-09 fix; reassess in Session 8 |
| **Open TD S3** | TD-001, TD-004, TD-005, TD-006, TD-007 |
| **Open TD S4** | TD-009, TD-010 |
| **Closed this session** | C-09, TD-014 |
| **Open from Session 7 intake (not yet resolved)** | TD-NNN-B (source_ts freshness across 6 JSONB blocks — Candidate C), ADR for "stable lies defeat duration gates" (Tier 3 this session), ENH-35 LONG_GAMMA blanket-block scoping question |
| **Active ENH in flight** | none this session |
| **Data contamination** | `BREADTH-STALE-REF-2026-03-27` registered. Affects 29 tables × breadth-derived fields × [2026-03-27 → 2026-04-23] window. Guard queries with `WHERE NOT public.is_breadth_contaminated(ts)`. |

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
[ ] CURRENT.md updated — "Last session" block reflects THIS session, "This session" block reset for next
[ ] session_log.md appended (one line: date · git hash · concern · outcome · docs_updated:yes/no)
[ ] merdian_reference.json updated for any file/table/item status change
[ ] tech_debt.md updated if any TD added, mitigated, or closed
[ ] Enhancement Register updated if architectural thinking happened
[ ] Local + AWS hash match confirmed if code changed
[ ] All commits prefixed correctly: MERDIAN: [ENV|DATA|SIGNAL|OPS] <scope> — <intent>
[ ] Re-upload to project knowledge any of CURRENT.md / session_log.md / merdian_reference.json / tech_debt.md / Enhancement_Register / CLAUDE.md / docs/operational/* that changed this session (per CLAUDE.md Rule 12)
[ ] Phase boundary check: do we trigger a Master/Appendix .docx generation? (rare — see Doc Protocol v3 Rule 6)
[ ] Runbook review: any operation explained to Claude for the SECOND time? If yes, create runbook from RUNBOOK_TEMPLATE.md
[ ] data_contamination_ranges review: did this session surface new contamination? If yes, INSERT row (Rule 13)
```

---

## Monday 2026-04-24 09:15 IST verification queries (copy-paste ready)

```sql
-- 1. Confirm 09:05 cron fired and wrote fresh reference
SELECT
    (MAX(ts) AT TIME ZONE 'Asia/Kolkata')::timestamp AS latest_ref_ist,
    COUNT(DISTINCT ticker) AS distinct_tickers
FROM public.equity_intraday_last;
-- Expected: latest_ref_ist ~09:05 IST today, ~1,330 tickers

-- 2. Confirm first breadth cycle post-fix reads realistic (NOT 1270/50 pattern)
SELECT
    (ts AT TIME ZONE 'Asia/Kolkata')::timestamp AS ts_ist,
    advances, declines, universe_count, breadth_score, breadth_regime
FROM public.market_breadth_intraday
WHERE ts >= '2026-04-24 09:15:00+05:30'
ORDER BY ts
LIMIT 3;

-- 3. Confirm instrumentation writing SUCCESS rows for ingest_breadth_from_ticks
SELECT
    (started_at AT TIME ZONE 'Asia/Kolkata')::timestamp AS started_ist,
    exit_code, exit_reason, contract_met, actual_writes
FROM public.script_execution_log
WHERE script_name = 'ingest_breadth_from_ticks.py'
  AND started_at >= '2026-04-24 09:00:00+05:30'
ORDER BY started_at
LIMIT 5;
-- Expected: first post-open rows exit_reason=SUCCESS, contract_met=true
```

---

*CURRENT.md — overwrite each session. Never branch this file. Never archive (the session_log is the archive).*
*Last updated 2026-04-23 (Session 7 close).*
