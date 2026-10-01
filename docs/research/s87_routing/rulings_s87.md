# S87 routing — operator rulings

Operator rulings, 2026-09-30 14:22 IST (operator 'OK' in chat, pre-registered before any shadow run):
 #2 mapping file = .claude/routing.json in meridian-cc
 #3 shadow candidates: TC1 = haiku, TC2 = sonnet; incumbent = opus for all classes
 #6 ledger = /home/ssm-user/merdian_ledger/ledger.jsonl (outside repo)
 #8 gear-down bar: TC1 10/10 agreement, TC2 18/20 agreement.

WS1.2 / ADR-029 ruling #15 — 2026-09-30 17:41 IST, operator 'hold': CLI stays pinned at 2.1.277; DISABLE_AUTOUPDATER stays set; revisit at the end of shadow v1.

#12 test, pre-registered 2026-09-30 18:47 IST: 8 allow rules added (read-only git -C: rev-parse, status, log, diff × meridian-engine, meridian-cc).
PASS = in a fresh session, the 4 read-only git -C test commands run with NO prompt AND `git -C /home/ssm-user/meridian-cc push --dry-run origin main` DOES prompt.
If a read-only command prompts: the rules did not take effect, so investigate. If the push does not prompt: the rules are too broad, so revert immediately from the .bak.

#12 test result, operator-observed 2026-09-30 ~19:03–19:05 IST, fresh session: commands 1–4 (read-only git -C) ran with no prompt; command 5 (push --dry-run) prompted and was declined. PASS as pre-registered at 18:47.
#12 RULED 2026-09-30 19:06 IST, operator 'OK': keep the absolute-path convention together with the 8 git -C allow rules. Other verbs untested.
Known limit: `git diff` and `git log` accept --output=<file>, so the diff/log allow rules technically permit a file write. Recorded, not fixed.

WS2.3 — option A (checklist moved into the skill) attempted and VOID (s87_measure/ws23/result.md, sha256 14d77ff5…): B3's rubric is inverted for this change (the control passed 3/3). C-close discriminated on the register order (3/3 vs 0/3 vs 0/3). Per prereg §7, fall back to option B; RULED 2026-10-01 07:22 IST. Owed if A is revisited: a v2 pre-registration (B3 rubric scored on checklist CONTENT, baseline floor ≥ 1, C-close without its unfalsifiable criterion 1).
