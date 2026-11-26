<!-- pk: lane=engine; git=meridian-engine:docs/research/s107/S108_session_prompt.md -->
# Engine session S108 — session prompt (written at the S107 close, Thu 2026-11-26)

You are the engine lane (the hub). Read, in order: `CLAUDE.md`, `docs/session_notes/CURRENT.md`,
`docs/registers/STREAMS.md`, `docs/research/s107/S107_close_inputs.md`, `docs/research/s107/rulings_s107.md`,
then `claude/pin/to_engine_LATEST.md` (the pin lane's standing note) before anything else.

## Where things stand

- **Live:** Board `d7642c2`; the Pin tile is the gross pin (`v_gex_pin_gross`, ENH-149).
- **Built, not switched on:** gamma V2 (ADR-033 PROPOSED, ENH-150). Tables hold the stored history to
  2026-11-25. Nothing writes them live.
- **Not approved:** the V2 writer hook, the `p3b2` job, the `v_gex2_*` views, any Board tile on V2.
- **Waiting on the pin lane:** its step 9 (V1 against V2 on history), then the operator's decision.

## First things

1. If the operator has pasted the `script_execution_log` read (statement in
   `docs/research/s107/engine_to_pin_LATEST.md` §1.4): check each `git_sha` against the repository (any commit at
   or after `a776d8a` ran the unchanged row-building code), write the result into `claude/engine_to_pin_LATEST.md`
   and close or update TD-S107-NEW-6.
2. Ask for the result of the market-hours look at the live Board (four checks against `v_gex_pin_gross`) if it is
   not in the pin lane's note.
3. Record the merge sha of `engine/s107-close` in CURRENT.
4. Do not start the eight-check gate or the `v_gex2_*` views until the operator says so.

## Standing rules (unchanged; the full set is in CLAUDE.md)

- Session close is when the operator says so. Never suggest ending, pausing or resting.
- Read the project documents before asking the operator to check anything.
- The operator runs all SQL against production; one statement per code block. Never name the reference product.
- No secrets in chat or git; never `cat`, `grep` or trace an env file.
- No box analysis 08:30–15:40 IST Mon–Fri; every box job under `ulimit -v 700000`; capture-path changes only
  16:30–07:45 IST on weekdays or at weekends.
- An expected value given to someone to check against is computed or read, never recalled; say where it comes from.
- Before any commit in the operator's worktree, have him print the branch.
- Every Board build sets `VITE_SUPABASE_URL=https://marketview.meridianalpha.in VITE_SUPABASE_ANON_KEY=proxy`; look
  at staging before any promote; never `nginx restart`; never Publish in Lovable.
- The operator wants exact commands, in order, in one message; keep relays between lanes to one line.

PK (binding, claude/MERDIAN_PK_Protocol_v1.md): lane=engine; PK folder claude/ root and claude/intake/;
git mirror meridian-engine:docs/research/s<N>/ on main. Write only in your folder; new files carry the
P2.2 header; executed prompts leave PK at the close; no reference-product name.
At close: P6 (with P4 steps 1–7 for the engine folder) and the "PK delta" section. Open: P5.
