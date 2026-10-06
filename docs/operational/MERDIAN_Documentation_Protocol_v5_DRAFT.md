# MERDIAN Documentation Protocol v5 — DRAFT (not in force)

| Field | Value |
|---|---|
| Status | **DRAFT — for operator ruling.** Doc Protocol **v4 remains in force** until this is ruled. |
| Drafted | 2026-10-06, Session 90 / AM-1 (Agentic Meridian Session 1), at the operator's hybrid-close ruling (05:21 IST) |
| Changes from v4 | Rule 3 (session-end checklist) and Rule 7 (`CURRENT.md`) only. Rules 0–2, 4–6, 8–11 unchanged. |
| Trial | The S90 / AM-1 close was done this way, so the trial has already run once (commit carrying this file) |

---

## Why

Each session's findings are written **eight times** — `CLAUDE.md`, `CURRENT.md`, `session_log.md`, `tech_debt.md`, System Map, Deployment Topology, Assumption Register and Decision Index. `CLAUDE_history.md` and `CURRENT_history.md` already record the cost (TD-S73-NEW-8: the duplication, not the length, is the root cause). The copies drift. S90 found three: a TD whose premise was false from the day it was filed (§D.46.3), a "structural" ceiling that was a sync defect (§D.46.9), and an archive missing a footer number (§D.46.13).

From S90, the agentic layer has **its own progress record**, a tracker with a status and linked evidence per item, and a ledger in the database (ADR-031 D7). Session-end duplication of that progress adds drift, not information.

## The rule, in one line

**Each fact has one home. Other documents point to it. They don't restate it.**

## Rule 3 (v5) — at session end

```
☐ Progress: update the tracker that owns the work (e.g. the agentic roadmap §3 Status/Session
  columns), each change with linked evidence (commit, query output, doc path). No evidence, no DONE.
☐ Rulings: the session's rulings file (single source; others point).
☐ Findings: the session's working docs, committed under docs/research/<session>/.
☐ Registers, POINTER ENTRIES ONLY, each naming the home it points to:
    ☐ CURRENT.md — Last session (≤ ~40 lines), NEXT (dated items first; undated = "the tracker"),
      rulings pointer table, one predecessor; the older block moves to CURRENT_history.md verbatim
    ☐ session_log.md — one paragraph
    ☐ tech_debt.md — new TDs in full (they are their own home); changes to existing TDs as ONE
      status-footer paragraph, not body edits
    ☐ Assumption Register — the section of refuted/validated rows (its own home)
    ☐ Decision Index — the row for any new ADR (mechanical, v4 Rule 11 unchanged)
    ☐ System Map / Deployment Topology — a §S<N> section ONLY if a component, schedule, host
      or boundary changed; a table of what changed, no narrative
    ☐ Enhancement Register — only if an ENH id moved; roadmap-local IDs are not mirrored
    ☐ merdian_reference.json — one change_log entry; file/table inventory only for objects the
      roadmap or System Map does not already list
    ☐ CLAUDE.md — footer, plus a settled/anti-pattern line only for a rebuild-grade lesson (Rule 0)
☐ Commit (one doc-close commit), push, ff-pull on the box from the operator's terminal
☐ Project knowledge: re-upload the changed pointer files and the working docs
```

## Rule 7 (v5) — `CURRENT.md`

Unchanged in purpose. It also states **where progress lives** (the tracker path), so the next session reads the tracker rather than a copy of it.

## What v5 does not change

- Full-file discipline for the edits it does make: count==1 anchors, line and byte deltas checked against the baseline, `json.loads` on the reference file, EOL preserved.
- ADRs before code (Rule 10), Decision Index mechanics (Rule 11), numbering (Rule 5).
- The operator declares session close.

## Open questions for the ruling

1. Does the tracker live in `docs/research/<session>/` (as now) or move to `docs/registers/` once it spans sessions?
2. Should the `cycle_health` / ledger health report (roadmap R1.5) replace the "what ran" part of `session_log.md` once it has two weeks of history?
3. Retire the eight-file wording in `CLAUDE.md` / the `doc-close` skill now, or after two more sessions on v5?
