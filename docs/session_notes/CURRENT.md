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
| **Outcome** | DONE — all 6 OIs closed (OI-18/19/20/21/22/23); `merdian_reference.json` v7→v8; `session_log.md` updated with v3 one-liner prepend + 2026-04-22 block; CLAUDE.md v1.1 adopted mid-session; `tech_debt.md` created with TD-007/009/010 active + TD-008 added and closed same session; ENH-72 register status drift fixed (5 PROPOSED → CLOSED flips + closure block appended, commit `c521b2f`) |
| **Git start → end** | `7bfa6f3` → `c521b2f` (via intermediate `90b8c2d` for JSON v8 commit) |
| **Local + AWS hash match** | PARTIAL — Local at `c521b2f`; AWS shadow runner remains FAILED since 2026-04-15 per `merdian_reference.json` `git.aws_status` — not resynced this session |
| **Files changed (code)** | `run_option_snapshot_intraday_runner.py` (OI-22), `build_trade_signal_local.py` (OI-23 docstring only), `merdian_live_dashboard.py` (OI-18), `refresh_dhan_token.py` (OI-21) |
| **Files added (patch scripts)** | `fix_oi18_dashboard_preopen.py`, `fix_oi21_token_refresh_hardening.py`, `fix_oi22_transient_vs_auth.py`, `fix_oi23_signal_v4_docstring.py`, `fix_td008_enh72_register_flip.py` |
| **Files added (docs)** | `docs/session_notes/20260422_oi19_out_of_scope.md`, `docs/session_notes/20260422_oi20_encoding_disposition.md`, `docs/session_notes/CURRENT.md` (new — replaces prior placeholder), `docs/registers/tech_debt.md` (new) |
| **Files modified (docs)** | `docs/registers/merdian_reference.json` (v7→v8), `docs/registers/MERDIAN_Enhancement_Register.md` (ENH-72 flip), `docs/session_notes/session_log.md` (v3 one-liner prepend + 2026-04-22 block) |
| **Tables changed** | none |
| **`docs_updated`** | YES |

### What this session did, in 6 bullets

- Closed all 6 OIs (OI-18 dashboard preopen query fix; OI-19 out-of-scope disposition; OI-20 PS 5.1 UTF-8 BOM fix-forward; OI-21 refresh_dhan_token idempotency + retry sleep fix; OI-22 transient vs auth alert split; OI-23 MERDIAN_SIGNAL_V4 docstring alignment).
- Established PowerShell 5.1 UTF-8 encoding baseline: `$PROFILE` forces UTF-8 without BOM on console + output + input; `git config --global i18n.commitEncoding=utf-8` + `i18n.logOutputEncoding=utf-8`. Commits from this session forward are BOM-free. Residual: TD-010 read-side `Get-Content` cp1252 default still pending.
- Bumped `merdian_reference.json` v7→v8 with three structural changes: sources appended (+2 sessions), `session_log` appended (+2 entries with new `session_local_oi_closed` field for audit), `open_items.ENH-72` status flipped PROPOSED→CLOSED with closure metadata. `git.current_hash` updated.
- Adopted CLAUDE.md v1.1 mid-session: read order, Rule 11 (no path/procedure asks without JSON/runbook check first), runbook layer (`docs/runbooks/`), ADR convention, `tech_debt.md` as middle-tier register.
- Surfaced four real tech debts: TD-007 (`is_pre_market` vestigial column), TD-008 (ENH-72 register drift — fix-script written and applied this session), TD-009 (6 `.bak` files in `docs/registers/` totaling ~235 KB), TD-010 (PS 5.1 `Get-Content` cp1252 read-side default — sibling of OI-20).
- Applied TD-008 fix end-to-end: 5 PROPOSED markers in `MERDIAN_Enhancement_Register.md` flipped to CLOSED; closure block appended with commit chain and live-validation numbers; `merdian_reference.json` v8 and the markdown register now agree; TD-008 moved to Resolved section in `tech_debt.md`.

### What this session intentionally did NOT do

- Did NOT build the remaining 8 runbooks declared in `docs/runbooks/README.md` index. Per README rule "add a runbook the second time an operation is done by hand" — the operations this session touched (git session-boundary inventory, row-count SQL, Task Scheduler enumeration, file-overwrite recovery) were each first-time. No runbook capture warranted yet. Exception candidate: `runbook_recover_overwritten_file.md` is a second-time pattern across projects — noted for capture if it recurs in MERDIAN specifically.
- Did NOT draft V19B or V19C appendices. V19A.md (62 KB, 13-block) was drafted under v2 protocol assumptions before v1.1 rules were adopted mid-session. Under v3 Rule 1, routine per-session appendices are no longer the default output; V19A is parked as pre-render draft awaiting phase-boundary trigger.
- Did NOT fix TD-002 (breadth_regime backfill) — still S2, not blocking, carry-forward.
- Did NOT investigate AWS shadow runner FAILED status (since 2026-04-15) — explicitly out of scope for this session. Still OPEN for a future session.
- Did NOT triage the ~50 untracked files in the repo working tree. This was flagged twice during Session 5 but deferred each time. **Now the named goal for Session 6 — see "This session" block below.**
- Did NOT commit the `.bak` backup from TD-008 patch (`MERDIAN_Enhancement_Register.md.pre_td008.bak`). Correctly rejected by `.gitignore` per TD-009 anti-pattern. Backup lives on local disk only, as intended.

---

## This session

| Field | Value |
|---|---|
| **Goal (one sentence, no comma)** | Triage ~50 untracked files in the repo working tree into track / gitignore / archive categories and commit the result |
| **Type** | Documentation / hygiene |
| **Success criterion** | `git status` returns clean except for intentionally-gitignored working files; `docs/operational/MERDIAN_Documentation_Protocol_v3.md` and `docs/operational/MERDIAN_Testing_Protocol_v1.md` are tracked in git; Master V19 and recent appendices (V18G, V18H_v2) are either tracked or explicitly archived; ~40 `fix_*.py` / `check_*.py` / `experiment_*.py` / `append_*.py` / `debug_*.py` scripts and related artifacts are each categorized |
| **Relevant files** | `.gitignore`, `docs/operational/*`, `docs/masters/*`, `docs/appendices/*`, root-level `fix_*.py`/`check_*.py`/`experiment_*.py`/`append_*.py`/`debug_*.py`/`patch_*.py`/`*.ps1`/`*.xml` files |
| **Relevant tables** | none (documentation / hygiene only) |
| **Relevant ENH / TD / C items** | None currently indexed for this work — triage may surface a new TD item if patterns emerge worth tracking |
| **Time budget** | ~40 exchanges. Apply Session Management Rule 1 checkpoint at 20 exchanges. |

### DO_NOT_REOPEN

- Capital ceiling values (₹50L / ₹25L / ₹2L) — final
- Strategy choice (Half Kelly C for live start) — decided in V18F
- T+30m exit timing — confirmed final
- 5m vs 1m for ICT — 5m is the rule
- OI-* namespace — permanently closed per Rule 5
- ENH-72 scope — 9 scripts instrumented, ID permanently closed
- V19A/V19B/V19C as per-session canonical outputs — under v3, routine sessions don't produce appendices. V19A.md exists as pre-render draft only.
- MeridianAlpha system concerns — out of scope for MERDIAN register
- Em-dashes in git commit subjects — PS 5.1 argv cannot pass them cleanly; ASCII-only discipline in commit messages
- PS 5.1 `Get-Content` display corruption — known (TD-010); use `-Encoding UTF8` or wait for TD-010's `$PSDefaultParameterValues` fix

### Triage framework for this session

Categorize each untracked file into exactly one bucket:

**TRACK** (add to git) — protocol documents, master/appendix docx files that should be in version control, legitimate scripts that are part of the live system, runbooks, ADRs. Examples from `git status` 2026-04-22:
- `docs/operational/MERDIAN_Documentation_Protocol_v3.md` — **CRITICAL**, this is the rule doc we operated under all Session 5
- `docs/operational/MERDIAN_Testing_Protocol_v1.md` — referenced in CLAUDE.md lookup table
- `docs/masters/MERDIAN_Master_V19.docx` — current master
- `docs/appendices/MERDIAN_AppendixV18G.docx`, `MERDIAN_AppendixV18H_v2.docx` — recent appendices

**GITIGNORE** (pattern-match in `.gitignore`) — patch-script debris, edit-intermediate artifacts, anything that gets regenerated or is session-local scratchpad. Examples:
- `fix_*.py` patch scripts that have already served their purpose (but note: `fix_td008_enh72_register_flip.py` IS tracked per Session 5 commit — keep precedent; decide if legacy `fix_enh*.py` should be archived or truly ignored)
- `check_*.py` one-off diagnostic scripts
- `debug_*.py` one-off debug scripts

**ARCHIVE** (move to `archive/` subdirectory, then commit the archive) — historical artifacts worth preserving but cluttering the root. Examples:
- `experiment_17_*.py`, `experiment_18_*.py` — research artifacts from Sessions 4-5
- `append_enh*.py` — register manipulation scripts
- `session_log_entry_20260417_18.md` — misplaced session note that belongs in `docs/session_notes/`

### Proposed approach

1. Run `git status --porcelain` and dump the full list to a scratch file for categorization
2. Categorize each file — one pass, one bucket per file
3. Apply in three waves: TRACK commits first (safest — no file moves), GITIGNORE patterns second, ARCHIVE moves last
4. Each wave gets its own commit for clean git history
5. Verify `git status` clean at the end

### Watch-outs for this session

- **Do not `git add .` blindly.** That's how unreviewed artifacts get committed and then have to be force-rewritten. One file at a time or one small glob at a time, reviewed before staging.
- **Watch the `.bak` pattern.** Current `.gitignore` handles `*.bak` and `*.bak_*` per commit `bca369d`. If new patch scripts created `.pre_*.bak` variants those may need a new pattern.
- **`docs/session_notes/session_log_entry_20260417_18.md`** — this is a misplaced session note; per Doc Protocol v3 Rule 2 session notes belong in `docs/session_notes/`. Move, don't track at root.
- **`.docx` files are binary in git.** They track fine but diffs are not readable. Per Doc Protocol v3 these are generated artifacts — accept that committing them is lossy-for-review but valuable-for-distribution.

---

## Live state snapshot (at session start)

| Component | State |
|---|---|
| **Live trading** | Phase 4A — manual execution. No automated trades. |
| **Shadow gate** | All 10 sessions PASSED (closed 2026-04-15) |
| **Local env** | Windows Task Scheduler, 13 MERDIAN tasks enumerated 2026-04-22; 11 Ready, 2 Disabled (`MERDIAN_Intraday_Session_Start` legacy, `MERDIAN_Market_Tape_1M` per TD-006). PS 5.1 profile active at `C:\Users\balan\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1` — UTF-8 without BOM on output/input paths. `Get-Content` read-side still defaults cp1252 (TD-010). |
| **AWS env** | t3.small at `i-0878c118835386ec2` (eu-north-1). Shadow runner FAILED since 2026-04-15 per `merdian_reference.json.git.aws_status`. Not blocking Local production; needs a dedicated session to diagnose. |
| **Local git HEAD** | `c521b2f` (clean) |
| **Last canary tag** | no canary this session — documentation + bug-fix work only |
| **Open C-N (critical)** | none open |
| **Open TD S1** | none |
| **Open TD S2** | TD-002 (breadth_regime backfill Apr–Jul 2025) |
| **Open TD S3** | TD-001, TD-004, TD-005, TD-006, TD-007 |
| **Open TD S4** | TD-009, TD-010 |
| **Closed this session** | TD-008 (ENH-72 register drift — fixed commit `c521b2f`) |
| **Active ENH in flight** | none this session — Session 6 is hygiene work |
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
