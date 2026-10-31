# S100 session prompt — finish the S98 + S99 doc-close, keep building the single list over the weekend, Monday live reads

**Read first, before asking me anything:** `claude/S99_close_inputs.md` (state, commits, owed footers, delivery route);
`claude/rulings_s99.md` (S99-A … S99-I); the tracker §2.2 single list (repo `docs/registers/agentic_layer_roadmap_S90.md`
v2.15 — clone the public repo `https://github.com/balannavin-cyber/meridian-engine.git` and read it there).
State at S99 EOS (2026-10-24 ~07:25 IST): HEAD `3706435` on all four trees. It is Saturday: maximise build work on
non-market days and hours (operator, 2026-10-24).

**Track with a task list**, one task per item, each done only on its PASS evidence pasted by me.

## Part A — Doc-close for S98 + S99 (first; one commit, Doc Protocol v5)

Check first whether it already landed (`git log --oneline -3` on the clone). If not, from `S99_close_inputs.md` §2–§5 and
`claude/S98_close_inputs.md`: CURRENT.md rewrite (S99 block + S98 as predecessor; S97 moved verbatim to
`docs/registers/CURRENT_history.md`, byte-identical assertion); session_log entries S98, S99; `tech_debt.md` footers +
TD-S99-NEW-1 + S98's R38–R49 TDs; Assumption Register §D.52 and §D.53; tracker change-history row; commit the S98 working
docs and the newer `rulings_s99.md`. Deliver by the §6 route. **Project knowledge model (operator, 2026-10-24):** large registers live in PK as *latest* extracts, history in the repo
only — the CLAUDE.md / CLAUDE_history split applied to every big file. In PK now, all at `3706435`: `claude/CURRENT.md`,
`claude/agentic_layer_roadmap_S90.md`, `claude/session_log.md`, `claude/CLAUDE_history.md` (full); `claude/tech_debt_LATEST.md`
(preamble + S95–S99 status paragraphs + the 154 open entries in full), `claude/MERDIAN_Enhancement_Register_LATEST.md`
(Parts 1–3), `claude/merdian_reference_LATEST.json` (minus `_meta`, `change_log`, `session_log`, `_sNN_addendum` keys).
At this doc-close: **regenerate all seven from the new HEAD** with `claude/pk_extract_s99.py` (run on the clone) and
re-upload. **Ruling owed:** physically split `tech_debt.md` in the repo into `tech_debt.md` (open) + `tech_debt_history.md`
(closed / duplicate / obsolete / parked / resolved), as CLAUDE.md was — recommended; then the extract becomes a plain copy.

## Part B — Weekend build, in §2.2 order (each: read code on the clone → design → offline test with controls and mutants → bundle → box dry-run/apply → suite → commit → four-way)

1. **R3** — monitor flags a hung orchestrator run (`finished_at` NULL and `started_at` older than 6 min → CRITICAL).
   `monitor_orchestrator_health.py` was read at S99 EOS: rows are fetched with a 5-min `LOOKBACK_MIN` on `created_at`,
   and `finished` filters out in-progress rows, so a hang ages out unseen (comment at the S97-J block). Monitor-only.
2. **R42–R44** — window parser takes the first matching line silently (union or raise on > 1); `SKIPPED_NO_INPUT` treated
   as benign where the alert daemon alerts on it (`merdian_pipeline_alert_daemon.py`:64–71) — note S99-H now emits it
   with exit 0 every pre-open cycle; daily audit calls every non-zero exit a "crash".
3. **R4** — one 08:25 IST pre-open probe: Dhan option chain / intraday / LTP and Kite token validity, through a delivering
   sender; plus the wsfeed preflight's give-up-after-23 s gap (TD-S80-NEW-17). Deploy before Monday 07:45 IST.
4. **B1 rest** — TD-S81-NEW-11 (Dhan 500 drops a cycle), TD-S81-NEW-12 (basis cron hour), TD-S90-NEW-14 (off-box EOD
   cursor writer), R40 (breadth writer overlap, NULL status; also writes on holidays — the 10-20 09:20 breadth row).
5. **BS-1** — operator steps for TD-S81-NEW-1 (Dhan token review / rotation) and TD-S71-NEW-11 (`.env` rotation).
6. **B3 reads on past data** (R7, R8, R10, R18) and **B4** (R22 calendar repair SQL from the 2026-10-24 read, R19, R23,
   R24, R9).

## Part C — Monday 2026-10-26, read after 15:45 IST

| Check | PASS |
|---|---|
| `gamma_metrics` `created_at − ts`, median per symbol | < 60 s (was 307 / 315 s) |
| Rows with IST `created_at` date > IST `ts` date, from 10-26 | 0 |
| γ rows at 15:30 / 15:35 / 15:40 IST, created 10-26 | 3 per symbol |
| 08:30 ledger row | `run_ids` are 10-26 runs |
| Runner `exit_code ≠ 0` | 0 on a healthy day; any `SKIPPED_NO_INPUT` read against the ingest ledger first |
| `[CYCLE WAIT]` lines in the orchestrator log | one per cycle, `missing=[]` on healthy cycles |
| WCB at 08:31 IST | no row on Friday's 15:24 ts; ledger `SKIPPED_NO_INPUT`, exit 0 |
| WCB at 15:40 IST | a real row (`constituent_count` > 0), untouched by Tuesday 08:31 |

PASS closes TD-S97-NEW-4, TD-S82-NEW-1, TD-S82-NEW-2 (S99 paragraph) and confirms TD-S97-NEW-8/-9/-10.

## Standing rules (binding)

- Every command and SQL block in full, one step at a time, with the exact output that means PASS; repeat a command in
  full. Each SQL query in its own code block.
- Rule 0: a check must be able to fail for the reason it names; expected values computed (run on the clone), never
  recalled. State a count only after computing it.
- No fixture suite 08:30–15:40 IST on a trading day (weekends exempt); always under `ulimit -v`.
- One CC session per tree, never rooted in `~/meridian-engine`. No `.env` reads (rule 19).
- DDL and data writes are operator actions in the SQL editor; every batch ends with its own verification SELECT.
- Board wording needs the operator's explicit yes. Never "vanna" / "charm"; γ lower case.
- Every multiple-choice question carries a recommended option and states any conflict with an earlier ruling.
- At a CC permission prompt, give the option number only. Use Chrome for browser work. Never name the parity target's
  product in artefacts.
- Rollback commands only inside a refusing block. Commits by the box route (S99-A); commit messages via `git commit -F`
  on the box, `[IO.File]::WriteAllText` on Local.
- Signal / ICT stream ranks after agentic (S99-G); agentic Stages 3–6 on hold (S99-D).
- Session close is when the operator says so. Never mention sleep or rest, and never suggest ending the session.
