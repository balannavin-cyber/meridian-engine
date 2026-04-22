# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."

---

## Last session

| Field | Value |
|---|---|
| **Date** | 2026-04-22 (IST evening; some commits cross UTC midnight so git dates read 2026-04-21) |
| **Concern** | Close 6 open OI items carried from Session 3+4 resume prompt, then reconcile registers under v3 rules |
| **Type** | Code debug + Documentation (split within a single extended sitting) |
| **Outcome** | DONE — all 6 OIs closed (OI-18/19/20/21/22/23); `merdian_reference.json` v7→v8; `session_log.md` updated; CLAUDE.md v1.1 adopted mid-session; `tech_debt.md` TD-007/008/009 captured; ENH-72 register status drift identified and fix-script shipped (TD-008) |
| **Git start → end** | `7bfa6f3` → `90b8c2d` |
| **Local + AWS hash match** | PARTIAL — Local at `90b8c2d`; AWS shadow runner remains FAILED since 2026-04-15 per `merdian_reference.json` `git.aws_status` — not resynced this session |
| **Files changed (code)** | `run_option_snapshot_intraday_runner.py` (OI-22), `build_trade_signal_local.py` (OI-23 docstring only), `merdian_live_dashboard.py` (OI-18), `refresh_dhan_token.py` (OI-21) |
| **Files added (patch scripts)** | `fix_oi18_dashboard_preopen.py`, `fix_oi21_token_refresh_hardening.py`, `fix_oi22_transient_vs_auth.py`, `fix_oi23_signal_v4_docstring.py`, `fix_td008_enh72_register_flip.py` |
| **Files added (docs)** | `docs/session_notes/20260422_oi19_out_of_scope.md`, `docs/session_notes/20260422_oi20_encoding_disposition.md` |
| **Tables changed** | none |
| **`docs_updated`** | YES |

### What this session did, in 5 bullets

- Closed all 6 OIs (OI-18 dashboard preopen query fix; OI-19 out-of-scope disposition; OI-20 PS 5.1 UTF-8 BOM fix-forward; OI-21 refresh_dhan_token idempotency + retry sleep fix; OI-22 transient vs auth alert split; OI-23 MERDIAN_SIGNAL_V4 docstring alignment).
- Established PowerShell 5.1 UTF-8 encoding baseline: `$PROFILE` forces UTF-8 without BOM on console + output + input; `git config --global i18n.commitEncoding=utf-8` + `i18n.logOutputEncoding=utf-8`. Commits from this session forward are BOM-free.
- Bumped `merdian_reference.json` v7→v8 with three structural changes: sources appended (+2 sessions), `session_log` appended (+2 entries with new `session_local_oi_closed` field for audit), `open_items.ENH-72` status flipped PROPOSED→CLOSED with closure metadata. `git.current_hash` updated.
- Adopted CLAUDE.md v1.1 mid-session: read order, Rule 11 (no path/procedure asks without JSON/runbook check first), runbook layer (`docs/runbooks/`), ADR convention, `tech_debt.md` as middle-tier register.
- Surfaced three real tech debts: TD-007 (`is_pre_market` vestigial column), TD-008 (Enhancement Register ENH-72 drift — fix-script shipped this session), TD-009 (6 `.bak` files in `docs/registers/` totaling ~235 KB).

### What this session intentionally did NOT do

- Did NOT build the remaining 8 runbooks declared in `docs/runbooks/README.md` index. Per README rule "add a runbook the second time an operation is done by hand" — the operations this session touched (git session-boundary inventory, row-count SQL, Task Scheduler enumeration, file-overwrite recovery) were each first-time. No runbook capture warranted yet.
- Did NOT draft V19B or V19C appendices. V19A.md (62 KB, 13-block) was drafted under v2 protocol assumptions before v1.1 rules were adopted mid-session. Under v3 Rule 1, routine per-session appendices are no longer the default output; V19A is parked as pre-render draft awaiting phase-boundary trigger.
- Did NOT fix TD-002 (breadth_regime backfill) — still S2, not blocking, carry-forward.
- Did NOT investigate AWS shadow runner FAILED status (since 2026-04-15) — explicitly out of scope for OI-closure session. Still OPEN for a future session.
- Did NOT run the ENH-72 register fix script (`fix_td008_enh72_register_flip.py`). Ship-ready with 5-location string-match + closure-block append; waiting on Navin to execute, inspect diff, commit.

---

## This session

| Field | Value |
|---|---|
| **Goal (one sentence, no comma)** | Apply the TD-008 register fix-script, verify registers reconcile, then begin Session 6 priority work |
| **Type** | Documentation (short) → then open |
| **Success criterion** | `MERDIAN_Enhancement_Register.md` shows ENH-72 as CLOSED in all 5 locations + has closure block; `session_log.md` reflects 2026-04-23 one-liner; next concern decided and recorded |
| **Relevant files** | `fix_td008_enh72_register_flip.py`, `docs/registers/MERDIAN_Enhancement_Register.md`, `docs/session_notes/CURRENT.md`, `docs/session_notes/session_log.md` |
| **Relevant tables** | none (documentation hygiene) |
| **Relevant ENH / TD / C items** | TD-008 (closing), TD-007 (decision on (a) vs (b) pending), TD-009 (low priority carry) |
| **Time budget** | Short (~10 exchanges for TD-008 closure + register reconciliation); then open-budget for next concern |

### DO_NOT_REOPEN

- Capital ceiling values (₹50L / ₹25L / ₹2L) — final
- Strategy choice (Half Kelly C for live start) — decided in V18F
- T+30m exit timing — confirmed final
- 5m vs 1m for ICT — 5m is the rule
- OI-* namespace — permanently closed per Rule 5; the 6 closed-this-session labels are the last OI disposition. No new OI ids going forward.
- ENH-72 scope — 9 scripts are instrumented; any additional script instrumentation goes under a new ENH id, not an extension of ENH-72.
- V19A/V19B/V19C as per-session canonical outputs — under v3 protocol, routine sessions don't produce appendices. V19A markdown exists as pre-render draft only.
- MeridianAlpha system concerns — out of scope for MERDIAN register (OI-19 disposition). MeridianAlpha is a separate system; its maintenance is not tracked here.
- Em-dashes and other non-ASCII in git commit subjects — PS 5.1 argv serialization cannot pass them cleanly. ASCII-only discipline in commit messages (use `-F message.txt` for any required non-ASCII).

---

## Live state snapshot (at session start)

| Component | State |
|---|---|
| **Live trading** | Phase 4A — manual execution. No automated trades. |
| **Shadow gate** | All 10 sessions PASSED (closed 2026-04-15) |
| **Local env** | Windows Task Scheduler, 13 MERDIAN tasks enumerated last session; 11 Ready, 2 Disabled (`MERDIAN_Intraday_Session_Start` legacy, `MERDIAN_Market_Tape_1M` per TD-006). PS 5.1 profile active at `C:\Users\balan\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` — UTF-8 without BOM. |
| **AWS env** | t3.small at `i-0878c118835386ec2` (eu-north-1). Shadow runner FAILED since 2026-04-15 per `merdian_reference.json.git.aws_status`. Not blocking Local production; needs a dedicated session to diagnose. |
| **Last canary tag** | no canary tag this session — documentation + bug-fix work only |
| **Open C-N (critical)** | none open |
| **Open TD S1** | none |
| **Open TD S2** | TD-002 (breadth_regime backfill Apr–Jul 2025) |
| **Open TD S3** | TD-001, TD-004, TD-005, TD-006, TD-007 (new), TD-008 (closing-imminent), TD-009 (new) |
| **Active ENH in flight** | none — Session 6 concern not yet scoped |
| **DB row counts at last snapshot (2026-04-21 16:30 IST)** | `script_execution_log`: 1,891 · `hist_spot_bars_1m`: 213,227 · `ict_htf_zones`: 294 (includes first-ever H-timeframe zones post-OI-27 fix) · `market_spot_snapshots`: 7,207 · `signal_snapshots`: 2,987 · `option_chain_snapshots`: 1,018,302 |

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
☐ CURRENT.md updated — "Last session" block reflects THIS session, "This session" block reset for next
☐ session_log.md appended (one line: date · git hash · concern · outcome · docs_updated:yes/no)
☐ merdian_reference.json updated for any file/table/item status change
☐ tech_debt.md updated if any TD added, mitigated, or closed
☐ Enhancement Register updated if architectural thinking happened
☐ Local + AWS hash match confirmed if code changed
☐ All commits prefixed correctly: MERDIAN: [ENV|DATA|SIGNAL|OPS] <scope> — <intent>
☐ Phase boundary check: do we trigger a Master/Appendix .docx generation? (rare — see Doc Protocol v3 Rule 6)
☐ Runbook review: any operation explained to Claude for the SECOND time? If yes, create runbook from RUNBOOK_TEMPLATE.md
```

---

*CURRENT.md — overwrite each session. Never branch this file. Never archive (the session_log is the archive).*
