# S99 close inputs (doc-close material; Doc Protocol v5)

S99 ran 2026-10-23 evening → 2026-10-24 ~07:25 IST. Rulings: `claude/rulings_s99.md` (S99-A … S99-I, single source; repo
copy `docs/research/s92_parity/rulings_s99.md` at `3706435` lacks the final "Applied after ruling" lines — the PK copy is
newer and is the one to commit at the doc-close).

## 1. Commits (all four trees verified identical by blob each time: Local, GitHub, `~/meridian-engine`, `~/meridian-cc`)

| Commit | What |
|---|---|
| `2edd25f` | S98-B: shadow runner waits for its own cycle's chain run (TD-S97-NEW-4); `tests/test_runner_cycle_wait.py` repointed at the live runner; `run_offline.sh` step 14/14 |
| `7d8f7d1` | S99 one stream: tracker v2.15 §2.2 single list + §2.3 retail; Stages 3–6 ON HOLD; `tech_debt.md` S99 status paragraph (46 closed); OpenItems v7 SUPERSEDED; CURRENT.md NEXT pointer; `docs/research/s99/reconciliation_pass2.md`; `rulings_s99.md` |
| `3706435` | R2/R21: WCB no-input guard (exit 0 `SKIPPED_NO_INPUT`); `tests/test_wcb_no_input.py` step 15/15 (OFFLINE PASS on the box 2026-10-24 07:13 IST, 1m32.5s); crontab line 11 (no-symbol WCB) removed; `docs/registers/aws_crontab.txt` refreshed from `crontab -l` |

Crontab: S98-B line appended 2026-10-23 (backup `~/crontab.bak-S98B-2026-10-23`, 69 → 70 lines); S99 R21 removed the WCB
line 2026-10-24 (backup `~/crontab.bak-S99R21-2026-10-24`, 70 → 69). Runner lines now 13 (`*/5 03-09`) and 69
(`0,5,10 10`). `parse_orchestrator_window` = (180, 595, 5, {1..5}) after both changes (S99-B baseline).

Operator data writes: S99-I — 12 zero WCB rows deleted (verification `zero_rows_left 0`, `rows_since_1012 912`).

## 2. Status footers owed at the doc-close (v5 Rule 3, one paragraph, no body edits)

- **TD-S97-NEW-4** — R1a evidence: 39 rows per symbol since 08-24 stamped 15:40 IST and written at the next session's
  08:30/08:40 (39 of 41 days); S98-B deployed `2edd25f`; closes on the Monday PASS (with TD-S82-NEW-1, -2 — already
  listed in the S99 paragraph).
- **TD-S97-NEW-9, -10, -8** — CLOSED by `3706435` + S99-I (mechanism measured 2026-10-24: first-cycle upsert onto the
  previous session's last breadth ts; 10-20 rows were written 10-21 08:31). Residual for the Monday read: no WCB row on
  Friday 15:24 ts at 08:31; a real 15:40 row from the closing cycle.
- **TD-S97-NEW-6 / TD-S80-NEW-17** — evidence: wsfeed preflight on 10-15 and 10-19 tried three times in ~23 s
  (03:40:03–03:40:26 UTC) then never again that session.
- **`tech_debt.md`:989's γ statement** ("gamma_metrics has no rows at all for 10-02") — superseded by R1a (S98).

## 3. New TD to file

- **TD-S99-NEW-1 (S3, security)** — the AWS access key ID of the operator's IAM user is committed in the PUBLIC repo
  (`docs/runbooks/runbook_aws_cli_file_operations.md` ×2, `docs/registers/session_log_history.md` ×1). No secret key, no
  `.env`, no JWT found in history (scan 2026-10-24). Fix: redact going forward; history rewrite or key rotation is the
  operator's call. Home: tracker §2.2 BS.
- R42–R44 are already pass-1 rows in §2.2 B1 (no TD needed until built). The calendar findings of 2026-10-24 are in R22.

## 4. Assumption Register §D.53 (corrections to my own work, S99)

1. A0's expected `git status` listed two untracked files; the tree held many older scratch files — an expected value
   recalled, not computed.
2. A4 expected `??` for `_PRE_S99A4` backups; `.gitignore:108 *_PRE_S*` ignores them.
3. S98-E.1's window "03:10–10:00 UTC" was wrong; the parser returns 03:00–09:55 (S99-B).
4. Pass-2 first count "247 open of 296" parsed only entries with a Status row; the true figure is 364 open of 441.
5. Cloning failed on a wrong owner name (`balannavin-cyber1`); the repo is public at `balannavin-cyber/meridian-engine`.
6. One read command was sent without its `| bin/roq.sh` pipe (TD-S89-NEW-1 read).
7. The WCB test's mutant M3 first expected T2 to fail; T2 is caught by the second layer (0 constituents) — the cell set was
   corrected to T3/T6/T8 after measuring.

## 5. Owed from S98 (Part C never ran)

Commit `claude/rulings_s98.md`, `claude/s98_reconciliation_table.md` (= pass 1), `claude/S98-B_cycle_wait_design_2026-10-23.md`
(with amendment notes: §5 step 1 superseded by the box route S99-A; S98-E.1 window figure corrected by S99-B; R47 footer
verified 2026-10-23 18:05 IST) and `claude/S98_close_inputs.md` to `docs/research/s92_parity/` (rulings) and
`docs/research/s98/` (the rest); S98's own items in `S98_close_inputs.md` §1–§2 (footers, R38–R49 TDs) and §D.52.

## 6. Delivery route that worked (no GitHub connector)

The repo is public: Claude clones `https://github.com/balannavin-cyber/meridian-engine.git` read-only. Changes go as a
tested bundle: Claude builds a patcher (pre-blob checks, dry-run default, `--apply`, `_PRE_` backups, sha256 re-read) and
runs it on its clone to compute expected hashes → `SendUserFile` → operator `aws s3 cp` Local → `s3://meridian-engine-deploy/s99/`
→ box `aws s3 cp` into `~/meridian-cc/scratch/` → dry-run → apply → commit by explicit paths → push → pull in
`~/meridian-engine` and Local → four-way blob check.

## 7. Project knowledge

S99 EOS (operator, 2026-10-24): stale 10-09 register copies deleted, then — at the operator's direction — current versions
restored on the CLAUDE.md / CLAUDE_history model: small registers in full, big ones as LATEST extracts (history repo-only).
Files and the generator: see `claude/S100_session_prompt.md` Part A and `claude/pk_extract_s99.py`. The S97–S99 session
prompts and S97 close inputs stay deleted (superseded).
