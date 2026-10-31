# S102 session prompt — S101 doc-close (Doc Protocol v5), carried live reads, then tracker §2.2

**Read first, before asking me anything:** `claude/S101_close_inputs.md` (state, evidence, findings, §D.55 1–25),
`claude/rulings_s101.md`, `claude/CURRENT.md` (S100 block — still the repo's CURRENT until this close), and the repo at
HEAD (clone `https://github.com/balannavin-cyber/meridian-engine.git`; read there). State at S101 close (2026-10-28 09:58
IST): **`origin/main` = `~/meridian-engine` = `~/meridian-cc` = Local = `4a1d8e1`**, no later commits; deployed 10-26
17:08 and live-verified 10-27 (0 non-zero exits); rollback not needed. Retail (MR-S2) pins `merdian_compute` at `4a1d8e1`.

**Track with a task list**, one task per item, each done only on its PASS evidence pasted by me.

## Part A — S101 doc-close (Doc Protocol v5; docs only — deploys any time, S90-J)

Model the commit on `7b91d1a` (S100 doc-close): read its diff first and match its file set and conventions. One commit,
box route (S99-A), message via `git commit -F`, four-way blob check after the push.

1. **CURRENT.md** — S101 block (state, what was established, filed, corrections, NEXT SESSION PICKS UP); S100 becomes the
   predecessor; the S99 block moves to `CURRENT_history.md` **verbatim**, asserted byte-identical (bytes + sha256 both sides).
   Binary-mode edit (mixed CRLF/LF).
2. **session_log.md** — S101 entry; the oldest entry moves to `session_log_history.md` verbatim.
3. **tech_debt.md** — close and move verbatim to `tech_debt_history.md`: TD-S97-NEW-4, TD-S82-NEW-1, TD-S82-NEW-2
   (S101-F), TD-S97-NEW-5, TD-S80-NEW-17; status paragraph names them. **File TD-S101-NEW-1…n** from `S101_close_inputs.md`
   §5, one block each, numbered in §5 order (the ENH-133 `57014` timeout first, per S101-F). TD-S100-NEW-1 stays open with
   a dated 10-27 re-measure note (NIFTY Δ 11.05, SENSEX Δ 42.37 at 15:40). Count blocks before and after by script.
4. **Assumption Register** — §D.55 = `S101_close_inputs.md` §6 items 1–25, verbatim in substance, one row each.
5. **System Map + Deployment Topology §S101** — `merdian_compute/` (gamma, cycle, volatility, pin; stdlib only;
   `pyproject.toml`), writers import from it; offline suite 23 → **25 steps** (24 import purity, 25 contract);
   `docs/interfaces/retail_compute_contract.md` v2.1; C6 / C7 register the live pin and accel zone views.
6. **CLAUDE.md** — version bump; standing rule from §D.55 item 14: a live view is identified by full `pg_get_viewdef` md5
   against a file that reproduces it, never by markers. History line in `CLAUDE_history.md`.
7. **Tracker** `agentic_layer_roadmap_S90.md` — v2.18: S101 rows done; §2.2 gains the §5 board questions as rows for ruling.
8. **merdian_reference.json** — one targeted insertion at the head of `change_log` (v79); never re-serialize; `json.loads`
   gate.
9. **Working docs** — `docs/research/s101/S101_close_inputs.md`; `docs/research/s92_parity/rulings_s101.md` (from
   `claude/rulings_s101.md`).

Every edit: anchored `str.replace` with count == 1 asserts, line / byte delta against the baseline shown, dry-run then
apply on the box. After commit: project-knowledge re-upload list.

## Part B — carried live reads (from S101)

1. **Pin path across the NIFTY expiry roll, part 2** (10-28 rows from 09:20 IST): same query as S101 (gex_cycle_history,
   NIFTY, 10-27 last 3 rows + 10-28 02:55–04:00 UTC). PASS: first OPEN row `held_for_cycles = 1` (leader 23000 ≠ 10-27
   last OPEN leader 22750), counts up while the leader holds, resets on change; `conviction` non-NULL on every OPEN row;
   SHIFTING at low held. `dte` is calendar days (6 on 10-28).
2. **R19 re-read** (first EOD run on or after 10-28 16:10 IST): `eod.log` mtime (box UTC) after the run; last `Date window`
   ends T−1; `Failures 0`; `selected_rebuild_trade_date` = T−1; `gap dates filled` names any complete date that had no
   breadth row (10-26 if Dhan has published it). SQL: expected vs actual rows for 10-26 and 10-27 (universe =
   `dhan_scrip_map` NSE active with security id; expected = distinct universe tickers with an `equity_eod` close that
   date; actual = `breadth_indicators_daily`, `universe_id = 'excel_v1'`); PASS = equal, `eod_pct ≥ 95`.

## Part C — then tracker §2.2 in its order (CURRENT.md S100 item 3)

B1 (R48 / R49, the ledger row, the R40 overlap) → BS-1 → B2 (R5 close print, R20; **TD-S100-NEW-1 first**) → B3 (R16 + R36)
→ B4 → B5 (R15, R11 + R39) → B6 (R12 with S100-Q step 2, R13); BR and the rest of BS before any retail build.
**Rulings I owe** (S101 §5, raise them with a recommendation each before building): Health OVERALL token threshold;
NIFTY board after the expiry-day close; Context IV skew on a 0-DTE front leg; WCB from pre-open ticks; `held_for_cycles`
across an expiry roll on the same strike.

## Standing rules (binding) — as S101

- Every command and SQL block in full, one step at a time, with the exact output that means PASS; each SQL query in its
  own code block. Rule 0: a check must be able to fail for the reason it names; expected values computed from the code or
  data, never recalled — read the writer before stating any expected value (§D.55 items 22, 24, 25).
- No fixture suite 08:30–15:40 IST on a trading day (Sunday exempt); always under `ulimit -v`.
- One CC session per tree, rooted in `~/meridian-cc`, never `~/meridian-engine`. No `.env` reads (rule 19).
- DDL and data writes are operator actions in the SQL editor; every batch ends with its own verification SELECT.
- Commits by the box route (S99-A); messages via `git commit -F`. Rollback commands only inside a refusing block.
- Alert / journal reads with `sudo journalctl`. Board reads in the operator's signed-in Chrome.
- At a CC permission prompt, give the option number only. Never name the parity target's product in artefacts.
- Retail scope line: this session changes `meridian-engine` only through the box route; it never touches the retail
  sandbox, and the retail sandbox never touches production.
- Session close is when the operator says so. Never mention sleep or rest, and never suggest ending the session.
