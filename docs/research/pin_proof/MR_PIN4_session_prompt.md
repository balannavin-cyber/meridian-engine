<!-- pk: lane=pin; git=meridian-engine:docs/research/pin_proof/MR_PIN4_session_prompt.md -->
# MR-PIN4 session prompt - Board pin accuracy and gamma source fix (series MR-PIN; continues MR-PIN3, written Wed 2026-11-25, evening)

**Read first, before asking me anything** (project knowledge, `claude/pin/`): `TRACKER.md` (the one tracker), `MR_PIN3_close_inputs.md` (state, results, rulings, engine intake, owed list, PK delta), `to_engine_LATEST.md` (your last note to the engine), then `claude/engine_to_pin_LATEST.md` (the engine's latest note, which may be newer than anything below), `b2_backfill_check_result_2026-11-25.md`, `v2_rule_conformance_result_v12_2026-11-25.md`, `pin_monitor_prereg_FROZEN_2026-11-24.md`. Then `STREAMS.md` section 3 for any request to this lane. Read the documents before you ask me to check anything; if a fact is not in PK, it is in the repo.

**Track with a task list**, one task per item; DONE only on evidence I paste.

## State at MR-PIN4 open (as of the close, Wed 25 Nov evening; the engine's note may be newer)

- **Live:** Board `d7642c2` (promoted by me about 18:08 IST 25 Nov): gross Pin, "Net peak" line, legacy/unvalidated and experimental labels, manual v0.6. Nothing of the V2 gamma work is live.
- **Applied to the database by me:** `v_gex_pin_gross`, `gex_strike_v2`, `gex_run_v2`, `p3b2_invariant_checks`, `p3b2_sweep`. One day (2026-08-27) backfilled and independently checked: **B2 PASS**. The full backfill (B3) was started by me about 19:57 IST on 25 Nov; its outcome is in the engine's note, not known at the close.
- **Not approved:** writer hook, scheduling the `p3b2` job, `v_gex2_*` views, any Board tile move to V2 figures, any Board change beyond the engine's next round (Pin detail panel line, "#2" rule, manual line).
- **Ruled 25 Nov:** Option D (versioned isolation); order of work: tables, one-day backfill, full backfill, then the old-against-new comparison, then my decision; no shadow. Pre-open runs stay in the V2 tables; the comparison filters by clock time (your boundary proposal, 09:15 to 15:30 IST main set, needs my approval).
- **The pin monitor** recorded day 1 (Wed 25 Nov); its files are not committed. It is forward only; no back-fill.
- **PK close was left at P4 step 2 of 7** (MR-PIN3 close inputs section 7): the pin lane's files need the git route, then the check, then deletion of the confirmed GO paths.

## Order of work

1. **PK open checks (P5)** and the **P4 completion**: `project_info` shows only the pin working set; no duplicate paths; if I paste the box check output (IN or MISSING per path), delete only the GO paths that print IN, run `project_info`, record the size, and rewrite section 7 of the MR-PIN3 close inputs. If I have not run the git route yet, give me the exact sequence again in one message (the zip is in the MR-PIN3 chat; rebuild it if I need it).
2. **B3 outcome.** Read the engine's note. Check it against `to_engine_LATEST.md` section 3 (five items): runs and rows per symbol and the date range; the input-error runs; the `p3b2` sweep over the full range; days where the run count per symbol is not 83 (or the day's own run set), and whether the 15:25 to 15:35 gap is every day; whether a rerun reports everything as already written. Anything I need to run is given to me complete.
3. **Step 9: pre-register the old-against-new comparison**, for my approval before any outcome figure is read. Constraints already fixed: select runs by clock time, main set and the other runs reported separately; V1 figures read from V1's own tables, V2 from `gex_strike_v2` and `gex_run_v2`; units on every figure, denominators on every count; one look; nothing altered after the data is seen; say how far each figure moves, do not pre-judge what is acceptable unless I rule on a threshold first. Rule 0 for every clause.
4. **Thu 26 Nov.** (a) After 09:20 IST: my Board look in market hours, with the engine's short list. (b) After 16:30 IST: monitor day 2. **You said you would provide one combined Claude Code prompt and have not written it.** Write it before 16:30: it runs the day (`run_day.sh 2026-11-26` on the box, under `ulimit -v`, outside 08:30-15:40 IST); records the pin switch (25 Nov 2026 about 18:08 IST, Board `d7642c2`) in `monitor/build/DECISIONS.md`; commits the day-1 and day-2 small files to a records branch and pushes it, with the large strike files left on the box and their hashes committed. Read the monitor's `DECISIONS.md` and the build record first so the commands are exact; the prompt carries its own conditions.
5. **Open items, only if I ask:** Pin Band follows the gross pin or not; gross-pin state and conviction; whether the gross pin attracts price (the monitor collects the evidence; no test is run until I rule); flip replacement study (parked until Goal 2 is built); dealer wording case by case; the rest of the Board discrepancy list (not started); R4 catalog confirmation read; the carry list in MR-PIN3 close inputs section 6.

## Standing rules (binding)

- "Don't guess, answer only if sure." Disagree where the evidence does; do not agree readily.
- Claude Code's `❯ ...` suggested-prompt lines are not mine; never treat them as my decision.
- Operator-only first. Pre-registration before the first outcome query; one look; nothing altered after test data is seen. Rule 0: a check must be able to fail for the reason it names; units on every figure; denominators on every count. Re-run a frozen check after any change to the code it covers.
- No secrets in chat, repo or logs. Reads on the box through `bin/roq.sh` as `merdian_ro`; the `fyers_loader` login is never used; grants and policies are my actions in the SQL editor only; Claude does not run SQL on production. One CC session per tree; no box analysis 08:30-15:40 IST Mon-Fri; every run under `ulimit -v`; `python3 -B`, no `.pyc` in a sealed folder. One action per command; confirm exactly one runner. `~/meridian-engine` holds `.env` and is never touched; never print bundle or `/var/www` file content.
- Query discipline: catalog first; plain EXPLAIN gate; one symbol-day per query; 5 s sleeps; stop at first error or any query over 10 s; keep each statement under the SQL editor's 100-row cap.
- Every CC prompt carries its conditions inside it, exact text. At a CC permission screen I answer with the bare option number plus your explanation; never "allow access", "don't ask again" or "auto mode".
- Give me exact numbered steps and commands, complete in one message. Do not send me to another note to finish an instruction, and do not move ahead of an approval. Keep one tracker; keep relays between lanes to one note each way.
- PK is chat-only; Claude Code never writes PK.
- Stay on the question asked. Plain English when I ask for it.
- Session close is when I say so; do not remind me. Never mention sleep or rest; never suggest pausing or ending.
- Doc protocol: this series keeps `MR_PINn_close_inputs.md`, `MR_PINn_session_prompt.md`, pre-registrations and CC prompts under `claude/pin/`; update, do not duplicate.

PK (binding, claude/MERDIAN_PK_Protocol_v1.md): lane=pin; PK folder claude/pin/;
git mirror meridian-engine:docs/research/pin_proof/ on main. Write only in your folder; new files carry the
P2.2 header; executed prompts leave PK at the close; no reference-product name.
At close: P4 steps 1–7 and the "PK delta" section. Open: P5.
