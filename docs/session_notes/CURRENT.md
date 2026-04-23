# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."

---

## Last session

| Field | Value |
|---|---|
| **Date** | 2026-04-22 (IST evening) |
| **Concern** | Triage ~50 untracked files in the repo working tree into track / gitignore / archive categories and commit the result |
| **Type** | Documentation / hygiene |
| **Outcome** | DONE — 51 untracked files categorized; 6 TRACKed (protocol docs + master + appendices + misplaced session note); 45 GITIGNOREd via 15 at-root-anchored patterns; zero files deleted or archived per user rule "keep on disk, keep out of git"; final `git status` clean |
| **Git start → end** | `f7b9366` → `48fbf24` → `f8a3888` |
| **Local + AWS hash match** | NO — AWS still FAILED since 2026-04-15 per `merdian_reference.json.git.aws_status`; Local advanced 2 commits ahead of origin, unpushed |
| **Files changed (code)** | none |
| **Files added (tracked)** | `docs/operational/MERDIAN_Documentation_Protocol_v3.md`, `docs/operational/MERDIAN_Testing_Protocol_v1.md`, `docs/masters/MERDIAN_Master_V19.docx`, `docs/appendices/MERDIAN_AppendixV18G.docx`, `docs/appendices/MERDIAN_AppendixV18H_v2.docx`, `docs/session_notes/session_log_entry_20260417_18.md` |
| **Files modified (docs)** | `.gitignore` (+18 lines of at-root anchored patterns) |
| **Tables changed** | none |
| **`docs_updated`** | YES |

### What this session did, in 6 bullets

- Tracked 5 critical docs that were sitting untracked despite being referenced in CLAUDE.md lookup tables and CURRENT.md success criteria (`MERDIAN_Documentation_Protocol_v3.md`, `MERDIAN_Testing_Protocol_v1.md`, Master V19, AppendixV18G, AppendixV18H_v2). One misplaced session note also tracked at its existing location pending future rename to `YYYYMMDD_<topic>.md` convention.
- Applied user rule "don't delete anything, keep on disk out of git" to the 45-file debris pool: zero file moves, zero archive directory created, pure `.gitignore` pattern-match sweep. Reversible via `git add -f` if any turn out to be live.
- `.gitignore` patterns added with leading-slash anchoring to repo root only — protects against sweeping up legit `check_*.py` / `fix_*.py` that might live inside module directories.
- Verification: final `git status --porcelain` empty. All 45 previously-untracked at-root files now ignored; the `M .gitignore` was the only change between gitignore-edit and commit.
- Mid-market-day pause (09:07 IST) — session was held open through market hours without drift; close-out resumed post-market.
- One in-session finding promoted for next-session investigation: Pine Script regenerated 2026-04-21 17:34 IST omits 1H zones despite OI-27 fix (closed same day) writing them to `ict_htf_zones`. Flagged as candidate TD-011 for later intake; not acted on this session.

### What this session intentionally did NOT do

- Did NOT investigate AWS shadow runner FAILED status — still deferred, now 7 days old. Candidate for Session 8.
- Did NOT push commits to origin. Local is 2 ahead (`48fbf24`, `f8a3888`). Push deferred until next live-gate check.
- Did NOT verify whether `enhancement_register_entries_20260420.md` content was merged into main register before gitignoring. `Select-String "^###\s+ENH"` returned zero matches — either clean or regex miss. File preserved on disk; auditable via filesystem forever.
- Did NOT archive or delete any files. Explicit user preference overrode the original 3-wave plan (TRACK / GITIGNORE / ARCHIVE) into 2-wave (TRACK / GITIGNORE only).
- Did NOT draft V19B appendix for Sessions 3+4 (the biggest documentation gap in the series). Carry-forward for a dedicated session.
- Did NOT open TD-011 formally — noted in Session 6 bullet above, promoted to next-session intake.
- Did NOT rename the misplaced session note `session_log_entry_20260417_18.md` to Doc Protocol v3 convention — cosmetic, deferred.

---

## This session

| Field | Value |
|---|---|
| **Goal (one sentence, no comma)** | Investigate the 2026-04-22 10:55 IST NIFTY BULL_FVG blocked-signal to determine whether the CONF 32 block was correct behaviour or an artifact of suspected zero breadth coverage |
| **Type** | Code debug |
| **Success criterion** | One of: (a) confirmed the block was legitimate based on `execution_penalty_debug` breakdown plus independent verification of at least one low-confidence input → no code change log as learning; OR (b) confirmed breadth was at zero coverage at 10:55 IST and that suppressed confidence artificially → open new TD or C-N as appropriate plus workaround if blocking; in both cases `tech_debt.md` has a decisive entry for the finding |
| **Relevant files** | `build_trade_signal_local.py`, `ingest_breadth_from_ticks.py`, `compute_market_breadth_intraday.py`, `merdian_live_dashboard.py` (signal panel rendering) |
| **Relevant tables** | `signal_snapshots` (raw JSONB `execution_penalty_debug`, `conviction_score_debug`, `block_reasons`), `market_breadth_intraday`, `latest_market_breadth_intraday`, `market_ticks` |
| **Relevant ENH / TD / C items** | None open yet; may produce a new TD or promote C-08 reopen if breadth is broken. ENH-60 (UnboundLocalError in flow-modifier block) is thematically adjacent — check if it fired in today's cycles. |
| **Time budget** | ~40 exchanges. Apply Session Management Rule 1 checkpoint at 20 exchanges. |

### DO_NOT_REOPEN

- Capital ceiling values (₹50L / ₹25L / ₹2L)
- Strategy choice (Half Kelly C for live start)
- T+30m exit timing
- 5m vs 1m for ICT — 5m is the rule
- OI-* namespace — permanently closed
- ENH-72 scope — permanently closed
- V19A/V19B/V19C as per-session canonical outputs — under v3, routine sessions don't produce appendices. V19B for Sessions 3+4 remains the single legitimate appendix backlog item, deferred to its own session.
- Em-dashes in git commit subjects — ASCII-only
- PS 5.1 `Get-Content` display corruption — known (TD-010)

### Proposed approach

1. Pull the four signal_snapshots rows bracketing 10:55 IST (one cycle before, the cycle itself, one after) for both symbols. Compare `conviction_score_debug` vs `execution_penalty_debug` vs `block_reasons`.
2. Independently pull breadth state at 10:55 IST from `latest_market_breadth_intraday` — was `adv`/`dec`/`coverage_pct` genuinely zero or was the dashboard displaying stale state?
3. If breadth at zero: trace upstream — was `ingest_breadth_from_ticks.py` running? `script_execution_log` should have a row per 5-min cycle. If no row, task was dead. If row present with contract_met=false, the ingest broke mid-cycle.
4. If breadth was healthy: block was correctly based on other factors (momentum, MTF alignment, DTE modifier). Document the contributing factors, accept the block.
5. Either way, write the finding to `tech_debt.md` (new TD if broken) or close the thread with an ADR-style decision note if block was correct.

### Watch-outs for this session

- **Don't add ENH-72-style observability work mid-investigation.** If `execution_penalty_debug` is incomplete, that's a finding, not an invitation to refactor the debug layer.
- **Check COV 0% against the raw dashboard screenshot AND the underlying query.** Dashboard can display stale; the DB row is truth (Rule 3).
- **Respect Session Management Rule 1** — one concern. Do not branch into AWS shadow diagnosis from here even if it turns out the breadth issue is the same root cause as the AWS failure.

---

## Live state snapshot (at session start)

| Component | State |
|---|---|
| **Live trading** | Phase 4A — manual execution. No automated trades. First live NIFTY signal (BULL_FVG blocked at CONF 32) captured 2026-04-22 10:55 IST. |
| **Shadow gate** | All 10 sessions PASSED (closed 2026-04-15) |
| **Local env** | Windows Task Scheduler, 13 MERDIAN tasks. PS 5.1 profile with UTF-8 output. `Get-Content` read-side cp1252 (TD-010). |
| **AWS env** | t3.small at `i-0878c118835386ec2` (eu-north-1). Shadow runner FAILED since 2026-04-15. Still blocking Local↔AWS hash match. Candidate for Session 8. |
| **Local git HEAD** | `f8a3888` (clean, 2 ahead of origin, unpushed) |
| **Last canary tag** | none this session — hygiene work only |
| **Open C-N (critical)** | none open |
| **Open TD S1** | none |
| **Open TD S2** | TD-002 (breadth_regime backfill Apr–Jul 2025) |
| **Open TD S3** | TD-001, TD-004, TD-005, TD-006, TD-007 |
| **Open TD S4** | TD-009, TD-010 |
| **Closed this session** | none |
| **Open from Session 6 intake (not yet in tech_debt)** | Pine generator omits 1H zones (candidate TD-011); `enhancement_register_entries_20260420.md` merge-status unverified |
| **Active ENH in flight** | none this session |
| **Live signals today (2026-04-22)** | NIFTY 10:55 BULL_FVG BLOCKED CONF 32 · SENSEX 10:55 BULL_FVG BLOCKED CONF 20 · both with MIN SIZE tag + MTF LOW + breadth display showing COV 0% (authenticity pending Session 7 verification) |

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
```

---

*CURRENT.md — overwrite each session. Never branch this file. Never archive (the session_log is the archive).*
