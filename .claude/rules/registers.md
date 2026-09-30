---
paths:
  - "docs/registers/**/*.md"
  - "docs/decisions/**/*.md"
  - "docs/**/*.json"
---

# Registers, documents and repository layout

Relocated verbatim from `CLAUDE.md` at Session 86 (ADR-028). Rule text is
unchanged; only its location moved.

- ❌ Applying predominant-EOL detect-and-restore to a document file without checking whether it is mixed-EOL. (Session 71.) **The counts in this note are stale — corrected S75 2026-09-09:** `CURRENT.md` was 317 CRLF / 2,596 LF when this was written and measures **0 CRLF / 3,038 bare LF** now; it has been normalised since. The rule stands and is why the S75 splices normalised nothing — but check the file, not this number. §D.34.3.
## Project file layout

```
C:\GammaEnginePython\                 (Windows local, PRIMARY LIVE)
/home/ssm-user/meridian-engine\        (AWS, SHADOW — git pull only)

  CLAUDE.md                           <- THIS FILE — root entry point
  *.py                                <- engine code
  .env                                <- secrets, never commit

  docs/
    operational/
      MERDIAN_Change_Protocol_v1.md
      MERDIAN_Documentation_Protocol_v3.md   <- supersedes v2
      MERDIAN_Session_Management_v1.md
      MERDIAN_Testing_Protocol_v1.md         <- consolidated preflight/canary/replay

    registers/
      merdian_reference.json          <- machine-queryable inventory (authoritative on op state)
      MERDIAN_Enhancement_Register_v<n>.md
      tech_debt.md                    <- persistent middle-tier issues

    runbooks/                         <- step-by-step procedures for recurring ops
      README.md                       <- index of all runbooks
      RUNBOOK_TEMPLATE.md             <- template for new runbooks
      runbook_update_dhan_token.md
      runbook_update_kite_flow.md
      runbook_*.md                    <- grows as recurring ops surface

    session_notes/
      CURRENT.md                      <- live session resume -- updated EVERY session
      session_log.md                  <- append-only one-line per session
      YYYYMMDD_<topic>.md             <- per-session detail when warranted

    decisions/                        <- optional ADRs (one per major decision)
      ADR-001-stable-lies-defeat-duration-gates.md
      ADR-002-market-structure-philosophy.md
      ...

    research/
      MERDIAN_Experiment_Compendium_v<n>.md
      merdian_all_experiment_results.md

    masters/                          <- .docx PUBLISHED ARTIFACTS (generated on demand)
      MERDIAN_Master_V<n>.docx

    appendices/                       <- .docx PUBLISHED ARTIFACTS (generated on demand)
      MERDIAN_Appendix_V<n>.docx
```

---

**Rule 23 — Mirror v1 pattern for stage-N patches.** Session 20 introduced Active/Resolved register pattern in `tech_debt.md` for clarity; ENH register adopted mirror pattern same session. Pattern: each TD/ENH lifecycle is recorded as TWO blocks — Active when filed, Resolved when closed. Both blocks stamped with session number. Audit trail visible at a glance.
