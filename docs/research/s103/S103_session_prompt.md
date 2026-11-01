# S103 session prompt — S102 doc-close (Doc Protocol v5), the six queued engine bundles, carried reads, then tracker §2.2

**Read first, before asking me anything:** `claude/S102_close_inputs.md` (state, evidence, findings, §D.56 1–16, and its
stated record limit for 10-28), `claude/rulings_s102.md`, `claude/ADR-032-DRAFT-gex-stored-unit.md`,
`claude/gex_unit_inventory_S102.md`, both S102 Lovable prompts, and the repo at HEAD (clone
`https://github.com/balannavin-cyber/meridian-engine.git`; read there).

State at S102 close (2026-10-30 11:05 IST): **meridian-engine `origin/main` = `3abb83f`** (no S102 engine commit pushed);
**meridian-connect `main` = live = staging = `30998f2`** (`index-EtZmieBR.js`), ADR-032 D1 live and read PASS; rollback
target `/var/www/marketview.bak-27c0e17`.

**Track with a task list**, one task per item, each done only on its PASS evidence pasted by me.

## Part A — S102 doc-close (Doc Protocol v5; docs only — any time, S90-J)

Model on `3abb83f` (the S101 doc-close): read its diff first and match its file set and conventions. One commit, box route
(S99-A), message via `git commit -F`, four-way blob check + Local after the push.

1. **CURRENT.md** — S102 block; S101 becomes the predecessor; the S100 block moves to `CURRENT_history.md` verbatim,
   asserted byte-identical (bytes + sha256). Binary-mode edit.
2. **session_log.md** — S102 entry; oldest entry to `session_log_history.md` verbatim.
3. **tech_debt.md** — file TD-S102-NEW-1…n from `S102_close_inputs.md` §5 in order (re-read `pg_indexes` for the
   `market_ticks` duplicate-index entry before filing it). Count blocks before / after by script.
4. **Assumption Register** — §D.56 = close inputs §6 items 1–16, one row each.
5. **ADR-032** → `docs/decisions/ADR-032-gex-stored-unit.md` (status: D1 RULED + LIVE; D2–D5 PROPOSED) + Decision Index row.
   **CLAUDE.md** — settled line (ADR-032 governance language), version bump, history line.
6. **Artefacts in the repo**: `sql/2026-10-30_s102_gex_per_1pct_views.sql`; `docs/research/s102/` (inventory, close inputs,
   `rulings_s102.md` → `docs/research/s92_parity/rulings_s102.md`); `docs/lovable_prompts/s102/` (two prompts, two
   guards, round records, `s102_manual_v05.sh`); ACL baseline (close inputs §1) in `docs/lovable_prompts/s92/README.md`
   with the one-writer-per-change rule and the promote rule "live ≡ named backup by `diff -rq`, rollback only in a refusing
   block".
7. **Engine manual source to v0.5**: apply the 18 edits of `s102_manual_v05.sh`'s `edits_man.py` to
   `docs/marketview_manual/marketview_user_manual.md` (`0f103a58…` → `e4872ab6…`, asserted), and set
   `build_help_pack.py` `BOARD = "index-EtZmieBR.js"`; rebuilding the pack is a separate content round.
8. **System Map + Topology §S102** (the `_1pct` views; Marketview reads per-1 % Γ), **tracker** v2.19, **reference.json**
   v80 (targeted `change_log` insertion, `json.loads` gate).

Every edit: anchored replace with count == 1 asserts, byte delta against the baseline shown, dry-run then apply.
After commit: project-knowledge re-upload list.

## Part B — the six 10-28 engine bundles (code; apply after 15:40 IST, push after 16:30 IST)

Order fixed by their baselines: **`s102r48` → `s102r40` → `s102td8` → `s102fut` → `s102argv` → `s102mk`** (close inputs
§2.2). Per bundle: baseline sha check on the box, dry-run, apply, `ast.parse`, its offline step; then the full offline suite
(29 steps) once, out of hours, under `ulimit -v`; one commit per bundle; push; four-way + Local. `s102mk` carries the live
crontab edit (markers `40 10` → `0 11` UTC) in the same change, read back with `crontab -l`. Next-session live checks:
END line with rc on a failing ingest; breadth-from-ticks run time; 09:05 refresh ledger row; futures rows one per symbol per
minute with `raw.spot_source = dhan_ltp_idx_i_same_request` through 15:40; markers `close_1530` from CAS.

## Part C — carried reads, then tracker §2.2

1. **R19 re-read**: `breadth_indicators_daily` for 10-26 onward (expected = universe tickers with an `equity_eod` close
   that date; PASS = equal, `eod_pct ≥ 95`).
2. Then tracker §2.2 in its order from where S102 stopped. **Rulings I owe** (close inputs §4) — raise each with a
   recommendation, read from the code first.

## Standing rules (binding)

- Every command and SQL block in full, one step at a time, with the exact output that means PASS; each SQL query in its own
  code block. Commands run on the box or in the SQL editor — no web-UI steps unless I ask. Rule 0: expected values computed
  from the code or data, never recalled; read what is live before naming a rollback target.
- **Rollback commands only inside a refusing block, and never in the same paste-ready message as the forward step.**
- One writer per change (Lovable or the box, never both).
- No fixture suite 08:30–15:40 IST on a trading day; always under `ulimit -v`. One CC session per tree, rooted in
  `~/meridian-cc`. No `.env` reads (rule 19). DDL and data writes are operator actions with a verification SELECT. Commits
  by the box route; messages via `git commit -F`. `sudo journalctl`. Board reads in my signed-in Chrome. Never name the
  parity target's product in artefacts. Retail scope line as S102.
- Session close is when I say so. Never mention sleep or rest, never suggest ending the session.
