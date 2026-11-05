# Operator rulings — Session 105 (tape stream, 2026-11-04 evening → 2026-11-05)

Single source for S105. Recorded at the S105 doc-close (2026-11-05). Branches: `tape/exploration` `bc14f18` (exploration) · `9cf1fcb` (S-window counts); `tape/scoring-v04` `6b8bdf9` (code) · `ea27c17` (ledger entry) · `0ef8f71` (ledger note + `.gitattributes`) (all on `meridian-tape-staging`,
never `origin`). The operator's own staging-`main` commits in the window: `f481d9c` (pre-registration v0.4) and `07a8a53`
(ledger v0.4 entry beside it).

| # | Ruling (operator's words condensed) | Where it landed |
|---|---|---|
| **S105-A** | Exploration plan approved with four answers: use the full 1-minute local tape (T1a/T1b outputs) after a TAPE_LOCAL row-for-row check; accept the 0.25-straddle grace band and the as-of straddle as recorded added parameters; absorption on real resting depth; results in the directory plus a pointer file naming the v0.3 hash | `docs/tape/exploration_2026-11-02_04/` (`bc14f18`) |
| **S105-B** | S-window follow-up: group counts only for 15/30/60/90, no outcome, assert no spot column read | `tables/E3_candidate_S_window_counts.csv` (`9cf1fcb`); window 30 ruled 2026-11-05 08:14 IST and written into v0.4 §1 |
| **S105-C** | v0.4 scoring plan: F-1 approved (5-minute columns in the extract); F-2 approved on condition that `tape_minute.oi` is an OPTIONAL input (absent → `NOT COMPUTED`, verdicts byte-identical, guard + mutant); F-3 approved (edit `tests/test_tape_scoring.py`, `tests/tape_scoring_mutants.py`); F-4 approved (`e2_oi_move_pct = 5`, unit check against `chain_events.OI_PCT` in the test only, no import in `score.py`); last-entry hash check approved with `M-SC-HASH-FIRST-ENTRY` and a both-entries cell | `docs/tape/scoring_plan_v04.md` §8; `6b8bdf9` |
| **S105-D** | Follow-up, no code change, no re-hash: ledger note (four hashed files, not three) and `services/tape_scoring/.gitattributes` | `0ef8f71` |
| **S105-E** | The close lands in a new worktree off `main`, branch pushed to `origin` for the operator to merge | this close |
| **S105-F** | The close must carry eight named items (R(T) defect; three vs four files; CRLF exposure; `run_offline.sh` not run and the Windows Rule-23 gap; `tape_minute_oi` timeout and real `roq.sh` unverified; build on Opus, not Sonnet; recorder `n_subscribed` 186 vs 148; the weekday timer's blank NEXT) | TD-S105-NEW-1…7, AR §D.59, CURRENT |
