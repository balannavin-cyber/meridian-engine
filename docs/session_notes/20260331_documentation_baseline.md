# Session Note — 2026-03-31 — Documentation Baseline Sprint

**Type:** Session Note (no code committed — documentation and planning only)

---

## What This Session Did

This was a holiday session (NSE closed). No live market. Used entirely for establishing the documentation and governance foundation that was missing from MERDIAN's operational infrastructure.

---

## Documentation Baseline Sprint — Phases Completed

| Phase | Deliverable | Status | Location |
|---|---|---|---|
| 1 | MERDIAN_Appendix_V18A_v4.docx | ✅ COMPLETE | docs/appendices/ |
| 2 | MERDIAN_OpenItems_Register_v3.docx | ✅ COMPLETE | docs/registers/ |
| 3 | merdian_reference.json | ✅ COMPLETE | docs/registers/ |
| 4 | MERDIAN_Enhancement_Register_v1.md | ✅ COMPLETE | docs/registers/ |
| 5a | MERDIAN_Change_Protocol_v1.md | ✅ COMPLETE | docs/operational/ |
| 5b | MERDIAN_Documentation_Protocol_v1.md | ✅ COMPLETE | docs/operational/ |
| 5c | MERDIAN_Session_Management_v1.md | ✅ COMPLETE | docs/operational/ |
| 6 | session_log.md | ✅ COMPLETE | docs/session_notes/ |
| 7 | Git directory structure + commit | ⏳ PENDING | User executes on Local + AWS |
| 8 | Code baseline reconciliation | ⏳ PENDING | Separate session with terminal access |

---

## Key Decisions Made This Session

### Documentation Architecture
- Dev protocol (Change Protocol) and Documentation Protocol are **separate documents** — different audiences, different update cadences, different use contexts
- docx for rebuild-grade records (masters, appendices). md for living documents (registers, protocols, session log). json for machine-queryable operational state.
- merdian_reference.json is the operational lookup layer. docx masters are authoritative for architecture and decisions. These serve different purposes and are intentionally maintained separately.

### Governance Rules Established
- **Documentation triggers:** session note (investigation, no code) / appendix (any code/schema/discovery) / minor master (3+ appendices or breaking change) / major master (phase boundary)
- **Session management:** 20-exchange checkpoints, 9-field resume block, one-concern-per-session, targeted context injection from merdian_reference.json
- **Change protocol:** 3-track system (A code / B config / C docs), 4-tag commit format (ENV/DATA/SIGNAL/OPS), DEGRADED failure mode added, rollback procedure defined, 08:15 token refresh before preflight
- **No state outside Git** — release states and canary outcomes live in Git tags only

### Strategic Direction Captured
All strategic architectural thinking from this session is captured in MERDIAN_Enhancement_Register_v1.md:
- Heston calibration enables complete strategy proposal engine (ENH-09 through ENH-21)
- Bloomberg BVOL equivalent as standalone data product (ENH-22)
- API commercial path in three stages (ENH-23 through ENH-25)
- Amazon Braket correctly sequenced after classical Monte Carlo proven (ENH-26/27)
- Pre-trade cost filter actionable now without Heston (ENH-06)

---

## What Is Not Done — Next Steps

### Phase 7 — Git Directory Structure (User Executes)

Create the directory structure on Local and commit all documents:

```powershell
# On Local (PowerShell)
cd C:\GammaEnginePython

# Create directory structure
mkdir docs\masters
mkdir docs\appendices
mkdir docs\registers
mkdir docs\operational
mkdir docs\session_notes
mkdir docs\preflight\fixtures

# Copy all existing master documents
copy <path>\GammaEngine_Master_V15_1.docx docs\masters\
copy <path>\MERDIAN_Master_V16_Fixed.docx docs\masters\
copy <path>\MERDIAN_Master_V17.docx docs\masters\
copy <path>\MERDIAN_Master_V18_v2.docx docs\masters\

# Copy all existing appendices
copy <path>\MERDIAN_Appendix_V16*.docx docs\appendices\
copy <path>\MERDIAN_Appendix_V17*.docx docs\appendices\
copy <path>\MERDIAN_Appendix_V18A_v4.docx docs\appendices\

# Copy registers
copy <path>\MERDIAN_OpenItems_Register_v3.docx docs\registers\
copy <path>\MERDIAN_Enhancement_Register_v1.md docs\registers\
copy <path>\merdian_reference.json docs\registers\

# Copy operational protocols
copy <path>\MERDIAN_Change_Protocol_v1.md docs\operational\
copy <path>\MERDIAN_Documentation_Protocol_v1.md docs\operational\
copy <path>\MERDIAN_Session_Management_v1.md docs\operational\

# Copy session notes
copy <path>\session_log.md docs\session_notes\
copy <path>\20260331_documentation_baseline.md docs\session_notes\

# Commit everything
git add docs\
git commit -m "MERDIAN: [OPS] Documentation baseline sprint — all masters, appendices, registers, operational protocols committed"
git push

# Tag the documentation baseline
git tag docs-v18-baseline
git push --tags
```

```bash
# On AWS — after Local push
cd /home/ssm-user/meridian-engine
git pull
git log --oneline -1
# Must match Local commit hash
```

### Phase 8 — Code Baseline Reconciliation (Separate Session)

Requires terminal access to Local and AWS. Steps:

1. Run file inventory on Local: `git status` + `Get-ChildItem *.py -Recurse`
2. Run file inventory on AWS: `git status` + `git diff HEAD` + `find . -name "*.py"`
3. Classify each file: SYNCED / LOCAL_ONLY / GIT_STALE / AWS_DRIFT / DEPRECATED / MISSING
4. Resolve AWS_DRIFT first (direct AWS edits that were not committed)
5. Resolve LOCAL_ONLY (files on Local but not in Git)
6. Resolve GIT_STALE (Local has newer uncommitted versions)
7. Commit baseline: `git commit -m "MERDIAN: [OPS] Code baseline reconciliation — v0-baseline"`
8. Tag: `git tag v0-baseline && git push --tags`
9. Run Preflight Sprint 1 (Stages 0-3) against the baseline

---

## State of Open Items at Session End

| Priority | Item | Status |
|---|---|---|
| CRITICAL | C-01 market_state UPSERT | OPEN |
| HIGH | V18A-01 Windows token unattended | OPEN |
| HIGH | V18A-02 Runner circuit-breaker | OPEN |
| HIGH | V18A-03 Calendar row maintenance | OPEN |
| HIGH | A-01 AWS 4 guards | OPEN |
| HIGH | C-02 EOD re-ingest 2026-03-24 | OPEN |
| CLOSED | E-01 Signal regret log | CLOSED V18A — 614 rows |
| CLOSED | D-06 flip_distance units | SUBSTANTIALLY CLOSED V18A |
| SHADOW LIVE | E-02 Three-zone gamma | SHADOW LIVE V18A |
| PARTIAL | A-03 TOTP automation | PARTIAL — manual proven, unattended pending |

---

*Session Note — 2026-03-31 — Documentation Baseline Sprint — MERDIAN*
