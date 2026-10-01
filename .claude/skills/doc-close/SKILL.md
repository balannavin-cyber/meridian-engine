---
name: doc-close
description: Gives the register-by-register order for MERDIAN's end-of-session documentation close. The session-end checklist in core CLAUDE.md under "What Claude must do at session end" governs WHAT must happen; this skill adds only the ORDER the registers are updated in. Use when the operator says close, or asks to close out, file TDs, or update the registers.
---

# Session-end documentation close

The session-end checklist is in core CLAUDE.md under 'What Claude must do at session end' and governs; this skill adds only the register order.

## Register order

Run these in order. Each step is finished before the next begins; the order is
load-bearing because later steps cite the IDs the earlier ones mint.

1. **ADR + Decision Index** — file or amend the ADR first, then index it. Nothing
   downstream can cite a decision that has no ID yet.
2. **`tech_debt.md`** — file new TDs at the top. New entries shift every line below
   them, so cite this file by entry ID plus row name, never by line.
3. **`MERDIAN_Assumption_Register.md`** — add the §D rows.
4. **`MERDIAN_Enhancement_Register.md`** — add or update the ENH blocks.
5. **`CURRENT.md` roll** — move the outgoing *Previous* session block into
   `docs/registers/CURRENT_history.md` **verbatim**, and assert **byte equality**
   between what left and what arrived. Then write this session's block.
6. **`session_log.md`** — append the one-line entry (date · git hash · concern ·
   outcome), then roll the file to the newest 10 entries.
7. **`merdian_reference.json`** — update any file, table or item whose status changed.
8. **`CLAUDE.md` footer** — bump the version line and record what this session closed.
9. **Commit, push, three-way sha check** — stage **by explicit path**, never
   `git add -A`; commit with the `MERDIAN: [OPS]` prefix; push; then verify the sha
   three ways (worktree, local HEAD, remote).
10. **Project-knowledge upload** — Rule 12. Git and project knowledge are two
    destinations and both are required: `CURRENT.md`, `session_log.md`,
    `merdian_reference.json`, `tech_debt.md`, the Assumption Register, the
    Enhancement Register, the Decision Index, any new ADR, and `CLAUDE.md`.
