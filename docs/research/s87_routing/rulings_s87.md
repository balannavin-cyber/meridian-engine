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

ADR-029 rulings 2026-10-01 09:03 IST, operator 'OK' to all proposals:
#1 A D14 risk-override review is **mechanical checks plus an operator read of a summary of ≤ 15 lines**, required before any canonical commit.
#4 **DEFERRED to S88** — the permission-prompt logging mechanism is a hook build plus test, and is not started here.
#5 **DEFERRED to S88 with #4** — context-limit logging ships with the same hook.
#6 **Operator owns the ledger schema.** The schema is the `ledger_append.py` fields **as built**; location was already ruled 2026-09-30 14:22 IST.
#7 A **ledger summary line in `session_log.md` at every doc-close**; the doc-close performs it.
#9 **DEFERRED until a class passes shadow** — no gear-up sampling rate is set before there is a class to sample.
#10 **TC1 = the frozen `tc1_v1` suite (10 tasks); TC2 = a 20-task suite still to be built; TC3 never gears down.**
#11 **Cost per PASSED task at the pre-registered bar**, graded by a **fresh blind subagent**.
#13 **DEFERRED to Sat 2026-10-03, outside market hours** — sandbox install and network-allowlist work does not run on a trading day.
#14 **DEFERRED with #13** — the Bash deny-bypass gap is addressed in the same out-of-hours window.
#16 **Automatic updates stay disabled**; revisit together with #15 at the end of shadow v1.
#17 The four bars are fixed: **AC29-1 zero individual regressions · AC29-2 every TC1/TC2 check proven to fail on a seeded defect · AC29-3 routed cost per passed task ≤ unrouted, per class · AC29-4 100 % ledger completeness.**
#18 **TC1 work must use deterministic tools** (`wc`, `grep -c`, …); a task for which no such tool exists **is TC2**.
