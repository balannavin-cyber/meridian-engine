# Operator rulings — Session 100

Single source for the S100 rulings. Other documents point here and do not restate them. Sits beside `rulings_s92.md` …
`rulings_s99.md` in `docs/research/s92_parity/`. S100 opened 2026-10-24 07:39 IST.

| # | Ruled | Topic | Ruling | Basis |
|---|---|---|---|---|
| **S100-A** | 2026-10-24 ~08:00 IST | `tech_debt.md` physical split (owed by the S100 prompt, Part A) | **Split now, in the S98 + S99 doc-close commit.** `tech_debt.md` keeps the open entries (the tracker §2.2 set, the three that close on the Monday S98-B read, TD-S99-NEW-1) and the status paragraphs; every closed, resolved, duplicate, obsolete and parked block, and the `## Resolved (audit trail)` section, moves verbatim to `tech_debt_history.md` (byte-identical assertion). The project-knowledge extract becomes a plain copy. | The CLAUDE.md / CLAUDE_history.md model (S86). Measured at the build: the S99 extractor's block cut-off ran each entry to the next `## ` heading, so TD-S97-NEW-21's block swallowed the S99 and S97 status paragraphs. Operator: "Split now, same commit". |
| **S100-B** | 2026-10-24 ~08:00 IST | S98's rows R38–R49 — TDs or tracker rows | **Tracker §2.2 is their home; no TDs.** R38–R44 are §2.2 rows already; R48 and R49 are added to §2.2 B1; R45 closed in `2edd25f`, R46 recorded, R47 verified — status-paragraph lines only. | Conflict stated at ruling: supersedes `S98_close_inputs.md` §2 ("register as TDs at doc-close") under S99-C (pass 1 + pass 2 = the single list) and v5's one-home rule. Operator: "§2.2 is the home". |
