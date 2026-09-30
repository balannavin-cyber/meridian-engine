# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S83 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** and **S85 at the S87 doc-close**, each moved verbatim rather than retyped. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**Session 87 — 2026-09-30 (Wed).** One concern in three workstreams: **what this project's
own Claude Code usage costs, and how the work should be routed**. A transcript baseline was
measured, **ADR-029 was drafted and NOT filed**, and a **shadow routing v1** was built and
run once on TC1. **No production change, no DDL, no database write.** Three commits, all
documentation: `c4566b3` → `9c5190f` → `e638059`.

| Field | Value |
|---|---|
| **WS1 — the engine tree was pulled, and is behind again** | The S86-owed pull landed: `~/meridian-engine` reads **`35588a2`** by `git -C … rev-parse`, the S86 doc-close commit. **It is now three commits behind again** — `c4566b3`, `9c5190f`, `e638059`, all written after the pull, all `docs/` — **so a second pull is owed at this close.** CLI pin **`2.1.277` HOLD** with `DISABLE_AUTOUPDATER` still set, **ruled 17:41 IST**, revisit at the end of shadow v1. |
| **WS2.6 — the split measured on the instrument, and the warning is the finding** | `ws2_6_context_measure.md`, operator-read `/context`, working directory / CLI / model held constant across both readings: **before `6bba0ce`, 128.9k tokens with the over-limit warning SHOWN; after `35588a2`, 14.3k tokens, warning ABSENT — reduction 88.91 %.** **The warning's absence is a state change, not a smaller number.** Corroborated from the git blobs rather than from the tool: **327,949 → 40,073 B, 87.78 %** — same order, different instrument. And **the file grew at the S86 doc-close**: S86 read 14.1k at `76ad9a3`, this reads 14.3k at `35588a2`, **+1.42 % in a single close** — a split re-filled at every doc-close returns to the limit on its own, and that delta is the quantity to watch. **The ADR-028 §7 amendment is OWED**, and it should cite the token readings and the warning state change, **not** the char figure, which does not reconcile with the warning and was left unreconciled rather than adjusted to fit. |
| **WS2.5 — the "150k" figure has an origin, and it is a CHARACTER limit** | Read off the same `/context` capture at `6bba0ce`: the warning states *over the 150.0k-char limit (318.5k chars)*. So the number carried by five documents is **the CLI's own 150.0k-CHARACTER warning** — not a token ceiling and not a byte ceiling, which is how it came to be compared against byte counts. **The origin is now known; the disposition is not.** ADR-028 §6 item 3's **correct-in-place-or-annotate ruling is still OWED.** |
| **WS3.1 — the baseline, and the measurement that says what cannot be measured** | `WS3.1_baseline.md`. Measured from a **sha-manifested frozen snapshot**, because the first run against the live corpus **failed its own phase-A cross-check by +5 responses** when this session's writes grew the directory mid-measurement — **the cross-check is the only thing that noticed**, and every token total would have inherited the disagreement (§1). Eight instrument controls PASS **before** any metric, and a failure suppresses the metrics rather than annotating them (§2). **§5a — approved permission prompts are BYTE-INVISIBLE.** No key records a per-call approval, by a lexical test **and** a non-lexical denied-vs-not-denied key-set differential; **the denial count therefore has no denominator, and no prompt rate, approval rate or approval-to-denial ratio can ever be recovered from these transcripts.** Anything ADR-029 wants to know about prompting must be logged **forward**. **§5b — context-limit hits: one line across both corpora**, on `-meridian-engine` only, firing on the size arm at a margin of **+3266 tokens / +0.3629 %** over the pre-registered bar — **had the bar been set 3267 tokens higher it would read as an ordinary API event**; `-meridian-cc` is **not observable by this metric**. **§6 — the `git -C` existence result: the `-C` prefix breaks the built-in read-only no-prompt match, even when it names the directory the session is already working in.** n=1 per command, one session, `git` alone — an existence result, not a rate. **§4 — costs are read from the tool's own emitted fields, cross-checked to a difference of 0.000000, and no price table is applied anywhere.** **§8 records 7 instrument defects — 4 caught by review, 3 by running an instrument** — and is the source for the owed Assumption Register **§D.43**. |
| **WS3.2 — ADR-029 DRAFTED, NOT FILED** | `docs/research/s87_routing/ADR-029-DRAFT-model-routing-and-token-efficiency.md`, deliberately under `docs/research/` so it cannot be mistaken for an accepted decision sitting in `docs/decisions/`. Decisions are labelled **D13–D27** (ADR-026 owns D1–D3, ADR-027 D4–D7, ADR-028 D8–D12); classes are **TC1 / TC2 / TC3** and criteria **AC29-1..4**, both prefixed because the bare `T`, `A` and `C` label spaces are already occupied in this corpus. **No model name, model identifier, price or measured figure appears in the draft, in digits or in words** — a scanner asserts it, with negative controls that prove it can fire. The reserved Decision Index row is **re-confirmed at filing time, not at drafting time.** **Rulings live in `rulings_s87.md` and are never restated in the draft** — the same argument D15 makes about the mapping. The appendix carries **18 rows: 5 RULED, 1 PARTLY RULED, 13 still owed**, and **ADR-029 is not filed until each has a ruling or an explicit dated deferral.** |
| **WS3.4 — shadow v1 built, TC1 run once, and the shadow FAILED its pre-registered bar** | Built to the 14:22 rulings: `.claude/routing.json` (mode `shadow`; TC3 shadow `null`), two shadow subagents declared in `.claude/agents/*.md` (`tc1-measurer`, `tc2-drafter`), and the ledger **outside the repository** at `/home/ssm-user/merdian_ledger/`. **TC1 v1** — suite sha256 **recorded == recomputed**, 10 tasks × 2 roles. Incumbent **10/10**, shadow **6/10**, **agreement 6/10 against a bar of 10/10 fixed before the run → FAIL, so TC1 stays on the incumbent and nothing gears down.** **The failure is systematic, not scattered: 0/3 on the line-count tasks, every one off by exactly +1**, while the tasks that resolve by listing files are **3/3** — so a determinate *answer* does not imply a deterministic *method*, and **whether TC1 work must run a tool rather than read is now an open question in the draft, not a settled clause.** Shadow cost **0.2535× (3.94× cheaper)** on **28.20× the output tokens** — **and cost ranks nothing until the verifier column is joined to it**, which is the whole of D18. **All 10 truths re-verified from the files on disk, 10/10 MATCH**, so each shadow FAIL is a genuinely wrong answer and not a bad truth; the independent re-derivation of the verifier disagrees with the ledger on **0**. **TC2 NOT RUN.** |
| **Permissions — ruling #12, and it moved the environment** | The §6 finding was acted on rather than noted: **8 read-only `git -C` allow rules** (rev-parse, status, log, diff × both trees), with the **PASS bar pre-registered at 18:47, before the test** — the four read-only commands to run with **no** prompt **and** `push --dry-run` to **prompt**, with the revert condition written down for each failure direction. Tested in a fresh session ~19:03–19:05 IST: **both halves held**, and ruling #12 followed at **19:06 IST — keep the absolute-path convention together with the allow rules.** User-level permissions now read **allow 10 / ask 15 / deny 22** from `~/.claude/settings.json`, so **the S86 block's `allow 2` below is SUPERSEDED** — the restated-copy drift D15 names, arriving in the register that names it. **Recorded and NOT fixed: `git diff` and `git log` both accept `--output=<file>`, so two of the eight read-only rules technically permit a file write** (ADR-029 §7 row h). **Other read-only verbs remain untested.** |
| **Ledger** | **TDs_NEW=0, TDs_CLOSED=0, ADRs_NEW=0, ADRs_AMENDED=0, no Decision Index row** — ADR-029 holds a **reserved** ID and filing it is what would add the row; drafting it does not. **The registers were not touched this session and are owed**: `tech_debt.md` (the `--output` limit and the ADR-028 §7 amendment both want entries), Assumption Register **§D.43** from `WS3.1_baseline.md` §8, Decision Index, Enhancement Register. Three commits, all pushed; **HEAD == `origin/main` == `ls-remote` at `e638059`.** |

**The session's two load-bearing results both say the same thing about instruments.** §5a is a
measurement whose entire content is that a quantity cannot be measured — approvals leave no
bytes, so every prompting question has to be answered forward or not at all. And the TC1
shadow run failed on the one task type where the class definition is most obviously
satisfied: counting lines is as determinate as work gets, and the shadow was wrong on all
three by exactly +1. **Neither was found by reasoning about the design.** The first came out
of a key-set differential run because a lexical test had already produced a false candidate;
the second came out of running the suite against a bar written down first. The draft records
both as open questions rather than resolving them, which is the only honest disposition for
one suite on one class.

## NEXT SESSION PICKS UP

**Time-boxed, in order**

1. **E2 — Thu 2026-10-01, 10:15:59 IST.** SENSEX dte 0 gamma fidelity, unaffected by E1's
   refusal. Derive `e2.sql` from `a4.sql` by the same pin-only edit and stamp the
   pre-registration **before** the arm.
2. **TD-S86-NEW-9 — the T1 precondition-scope ruling. OWED BEFORE 2026-10-07.** Does
   ≥ 3×SE gate the gamma reading or only the offset/`r_eff` reading? Pre-register and date
   the ruling **before** the arm runs, amend `capture_s84.md` §2.6 in place with the
   reversal left legible, and confirm or restate §2.11's verdict citing the ruling — **do
   not silently recompute it.**
3. **A4 re-run — Wed 2026-10-07, 10:15:59 IST**, the next SENSEX dte 1. Gated on item 2.
   S86 recorded, before the arm, that the monotone precondition gradient makes another
   NO-TEST more likely than not.
4. **The NIFTY L9 stage-1 max-pain arm (TD-S80-NEW-1) — STILL OUTSTANDING.** Owed from S82,
   not run at S85, S86 or S87. Named rather than carried silently for a fourth session.

**Owed work and decisions**

5. **Pull `~/meridian-engine` → `e638059`.** Three commits behind, **all `docs/`**. Verify by
   `git -C … rev-parse` equality, not by byte size.
6. **WS2.1–2.5 — not started.** Only WS2.6 ran, and WS2.5's *origin* was traced without its
   disposition being ruled. The five items, stated here so they live in the repo rather
   than in a brief:
   - **2.1 — renumber B6/B7 → Rules 24/25** in `.claude/rules/python-writers.md`, re-point
     the **10** `CLAUDE.md Rule 20 / 21 / 22` citations, and **remove core's two-line
     disambiguator** once they resolve. Run `check_xrefs` after, not before.
   - **2.2 — TD-S86-NEW-4.** Make the BOM snippet **round-trip the BOM**, demonstrated on a
     fixture that shows both arms — **before: BOM lost; after: BOM kept** — and run the
     `git log` forensics on the **27** BOM-carrying files.
   - **2.3 — TD-S86-NEW-8.** Populate the `doc-close` skill, with an **operator ruling owed
     on whether the session-end checklist stays in core or moves into the skill** (the
     growth rule applies), and **extend gate 2 to assert a non-trivial body** — with a
     **negative control on the present empty shell**, or the gate proves nothing.
   - **2.4 — the same check on `.claude/skills/merdian-runbooks/`.** Not measured at S86;
     named rather than assumed clean.
   - **2.5 — the five copied "150k" figures.** Origin found at S87: **the CLI's own 150.0k-
     CHARACTER warning**, not a token or byte ceiling. **Operator ruling owed — correct in
     place, or annotate** (ADR-028 §6 item 3).
7. **The ADR-028 §7 amendment — OWED**, from `ws2_6_context_measure.md`. Cite the token
   readings and the warning state change; **do not cite the char figure.**
8. **The remaining ADR-029 rulings — 13 of 18**, listed one per line in the draft's
   appendix and tracked in `rulings_s87.md`. **The draft cannot be filed until each has a
   ruling or a dated deferral**, and the numeric bars in §9.1 must be fixed **before** any
   further shadow run, not after.
9. **The TC2 shadow run — NOT RUN.** Bar pre-registered at 18/20. TC1's result does not
   transfer: it was a failure of *method* on one task type, and TC2's tasks are drafting
   tasks with no line-counting in them.
10. **Registers owed, none written this session** — Decision Index (no row yet, by
    decision), `tech_debt.md`, Assumption Register **§D.43** sourced from
    `WS3.1_baseline.md` §8, Enhancement Register.
11. **Project-knowledge re-upload — Rule 12.** `CURRENT.md` and `session_log.md` at minimum,
    plus `tech_debt.md`, `MERDIAN_Assumption_Register.md`, `MERDIAN_Decision_Index.md` and
    `MERDIAN_Enhancement_Register.md` once item 10 is done. **Git commit and
    project-knowledge upload are two destinations and both are required for session close.**

## OPERATOR RULINGS, S87

Recorded in `docs/research/s87_routing/rulings_s87.md`, which is the only place their text
lives. **Numbers and times only here** — a ruling transcribed into a second place is a ruling
that can drift out of agreement with itself. **None authorises a build.**

- **2026-09-30 14:22 IST** — ADR-029 appendix **#2**, **#3**, **#6** (partly — location only)
  and **#8**, pre-registered before any shadow run.
- **2026-09-30 17:41 IST** — ADR-029 appendix **#15**.
- **2026-09-30 18:47 IST** — not a ruling: the **#12 test and its PASS bar, pre-registered
  before the test ran**, with the revert condition stated for each failure direction.
- **2026-09-30 19:06 IST** — ADR-029 appendix **#12**, after the test returned PASS.

## Previous session S86

**Session 86 — 2026-09-29 → 2026-09-30 (Tue–Wed).** Two halves: the **ADR-028 `CLAUDE.md`
split** built, behaviourally tested and merged, then the **ENH-98 A4 arm** run to its
pre-registration and a ten-entry doc-close. **No production change, no DDL, no database
write** — the only database contact was three read-only `roq.sh` queries for A4.

| Field | Value |
|---|---|
| **ADR-028 SHIPPED and FILED ACCEPTED** | The split is merged at **`76ad9a3`**. Core `CLAUDE.md` is **39,786 B / 258 lines** (172 content, 66 blank, 20 structural); launch load **327,949 → 39,786 B, −87.9 %**. Eight `.claude/rules/*.md` files carry `paths:` frontmatter, two skills exist, and all 23 discovery blocks + 6 version footers moved **verbatim** to the unloaded `docs/registers/CLAUDE_history.md`. `/context` post-merge: **only `CLAUDE.md` loads at launch, 14.1k tokens, no rules file, no size warning** — **OPERATOR-MEASURED**. Decisions renumbered **D8–D12** (ADR-026 owns D1–D3, ADR-027 D4–D7); Decision Index row added; next-free **`ADR-028+` → `ADR-030+`** with **ADR-029 reserved** for *model routing and token efficiency*. |
| **AC2 met; AC1 failed on lines and was amended to bytes** | Blind graded, three runs per prompt, 2-of-3: **before 10 / after 12** of 15, pass-bar clauses **(a) (b) (c) all PASS**, two gains (B2, C1), **no regressions**. **AC1-lines FAILED at 258 against 200** and is recorded as failed; **AC1-bytes PASSED at 39,786 ≤ 40,960**. CLI pinned **`2.1.277`** across both arms. **The summary is deliberately weak where the evidence is weak:** no measured harm, launch load down 87.9 % in bytes, and **the two gains are NOT claimed as effects of the split** — n=2, one moved by a post-hoc re-grade, nothing isolates the split from run-to-run variance. |
| **RULING 3 is post-hoc and labelled post-hoc** | Made **after** blind grading of both arms, unlike the pass bar and RULINGS 1–2. Bounded by two controls: applied to a **fresh blind re-grade of C1 and C2 only**, and the before-arm run RULING 1 locked as FAIL **still FAILs** under it. It moved ten individual run grades, six after and four before — visible in the tally, not folded in. |
| **A4 (SENSEX dte 1) — T1 is UNDECIDED, not decided** | Gate passed before the run: both symbols **10:15:06 IST**, **0.00 %** row deviation against their own 09:15 reference (NIFTY 936, SENSEX 780). dte MATCH both symbols (SENSEX 1, NIFTY 6). Precondition **FAIL at 1.18×** (10.0 against 3 × 8.453 = 25.359) → **NO-TEST**. T1's refusal condition does not fire on this arm's numbers (`exact/365` ATM 0.0675, NEAR 0.0760) **but the arm does not count**. Per the operator-ratified clause (b), **T1 = UNDECIDED**; re-run **Wed 2026-10-07 10:15:59 IST**; **no L7/L8 proposed**. An UNDECIDED T1 is **not** a refusal and must not be recorded as one. |
| **The precondition is now binding, and the gradient is three points** | **6.41×** (dte 3) → **3.79×** (dte 2) → **1.18×** (dte 1), monotone. The mechanism is dispersion: ATM offset **19.1 → 10.0** while SE(median) grew **5.051 → 8.453**, `sd` **35.691** at ~3.6× the median. **Stated before the re-run: on this gradient 2026-10-07 is more likely than not to be a NO-TEST too**, which would mean T1 is scoped to a dte range its own precondition may not admit. |
| **A pre-registration ambiguity that flips T1 — TD-S86-NEW-9, ruling OWED** | §2.6's *"an arm counts only if…"* gives UNDECIDED; §2.8 + §2.10's precedent (E1's gamma refusal fired while its offset was a NO-TEST at 0.49×) gives **PASS on both arms**. **Same data, two verdicts.** Noticed *after* A4 was measured, so it cannot settle it — the ratified clause (b) governs. **An operator ruling is owed, pre-registered and dated, before 2026-10-07.** |
| **Ledger** | TDs_NEW=**10** (TD-S86-NEW-1..10), TDs_CLOSED=**2** (NEW-5, NEW-10), **TD-S73-NEW-8 → SUPERSEDED BY ADR-028**. **ADRs_NEW=1 — ADR-028 ACCEPTED**; ADRs_AMENDED=0; Decision Index row added, marker advanced, ADR-029 reserved. Assumption Register **§D.42 added — 13 rows, 12 REFUTED / 1 WITHDRAWN, twelve of them defects in this session's own instruments or drafts**. Enhancement Register TRIGGERED (ENH-98, A4). |
| **The `doc-close` skill is an empty shell** | Invoked at the start of this close and returned a heading and one sentence. 448 bytes, frontmatter promising the whole session-end procedure, **no procedure relocated into it**. The split's gate 2 checked skills for a `name:` key, which an empty body passes. **TD-S86-NEW-8** — populate or remove, and extend gate 2 to assert a non-trivial body. |
| **Environment state** | CLI pinned **`2.1.277`**; **`DISABLE_AUTOUPDATER: "1"`** in the `env` key of `~/.claude/settings.json`. User-level permissions: **allow 2 / ask 15 / deny 22**. **Known gap, measured on one form only: a Bash deny is bypassable by absolute path** — `/bin/cat` does not match a deny written against `cat` — so the deny list is a speed bump and not a boundary. Only the absolute-path form was tested; no other spelling was. **Sandbox is NOT enabled.** Recorded as state, not as a remediation. |
| **What the session's own instruments caught that reading did not** | `check_xrefs.py`, once fixed to see two-digit labels, found a bare **`A1`** in ADR-028 §7.1 resolving silently to **ADR-026's acceptance criterion A1** — a wrong citation inside the document being filed, written while re-pointing other documents' citations. The A4 apply step's parse-and-branch rewrite caught two defects in its own first draft. **§D.42.10 records that four of the five ADR draft defects were found by reading and only one by an instrument** — the instrument earned its place by finding the one that resolved to plausible wrong content. |

**The split's gates were relocation gates, and that is the session's standing lesson.**
Conservation proved every line moved intact and unaltered — and passed *because* two
fictitious ADR filenames, present since before S86, were preserved faithfully
(TD-S86-NEW-5). Gate 2 proved each skill file had a `name:` key and could not see that
`doc-close` had no body (TD-S86-NEW-8). Neither gate was wrong; neither was a correctness
gate, and nothing in the split claimed to be one.

## NEXT SESSION PICKS UP

**Time-boxed, in order**

1. **TD-S86-NEW-9 — the T1 precondition-scope ruling. OWED BEFORE 2026-10-07.** Does
   ≥ 3×SE gate the gamma reading or only the offset/`r_eff` reading? Pre-register and date
   the ruling **before** the arm runs, amend `capture_s84.md` §2.6 in place with the
   reversal left legible, and confirm or restate §2.11's verdict citing the ruling — **do
   not silently recompute it.**
2. **E2 — Thu 2026-10-01, 10:15:59 IST.** SENSEX dte 0 gamma fidelity. Unaffected by E1's
   refusal. Derive `e2.sql` from `a4.sql` by the same pin-only edit and stamp the
   pre-registration before the arm.
3. **Pull `~/meridian-engine` after 16:00 IST today** → `git pull --ff-only origin main`.
   Verify `git rev-parse` equality, not byte size. Check the `.py` intersection with the
   26 cron/unit-invoked scripts is empty before pulling.
4. **A4 re-run — Wed 2026-10-07, 10:15:59 IST**, next SENSEX dte 1. Gated on item 1.
5. **The NIFTY L9 stage-1 max-pain arm (TD-S80-NEW-1) — STILL OUTSTANDING.** Owed from
   S82, rode on the A3 date, not run at S85 and not run here. Named rather than carried
   silently for a third session.

**Owed decisions and follow-ups — none of them mine**

6. **The CLI unpin is a deliberate decision, not a default.** `2.1.277` was pinned for the
   ADR-028 comparison and both arms are graded, so the reason has expired. Unpinning also
   re-exposes the `stable`-channel side effect the pin introduced. Decide explicitly;
   `DISABLE_AUTOUPDATER` stays set until then.
7. **ADR-029 — model routing and token efficiency.** ID reserved this session, **not
   drafted**. Nothing is decided and no measurement is claimed.
8. **The five documents carrying the copied "150k" figure** — ADR-028 §6 item 3's owed
   decision: correct in place, or annotate. `TD-S73-NEW-8` is SUPERSEDED; the copies are not.
9. **`merdian-runbooks` skill sibling check.** Not measured this session. TD-S86-NEW-8
   names it rather than assuming it clean.
10. **The `doc-close` skill fix — TD-S86-NEW-8.** Populate it with the session-end
    procedure or remove it and its pointer; then extend gate 2 to assert a non-trivial
    body for every emitted skill.
11. **Project-knowledge re-upload — Rule 12.** `CURRENT.md`, `session_log.md`,
    `merdian_reference.json`, `tech_debt.md`, `MERDIAN_Assumption_Register.md`,
    `MERDIAN_Enhancement_Register.md`, `MERDIAN_Decision_Index.md`,
    `docs/decisions/ADR-028-claude-md-split.md`, `docs/research/capture_s84.md` (§2.11 is
    new), `CLAUDE.md` and the eight `.claude/rules/*.md` files. **Git commit and
    project-knowledge upload are two destinations and both are required for session close.**

## OPERATOR RULINGS, S86

These exist only in chat and are recorded here, in ADR-028 and in the ENH-98 block.
**None authorises a build.**

- **T1 pair rule, clause (b).** If A4 is a NO-TEST on its own precondition, **T1 is
  UNDECIDED** — not "rests on A3 alone" — because §2.6 scopes T1 to SENSEX dte 1–2 and one
  dte-2 arm does not cover that scope. Re-run at the next SENSEX dte 1 cycle. Ratified
  **2026-09-30 10:07:42 IST**, before the arm.
- **Gate2 stays at the coded ≤ 5 %.** The 0.00 % of A2b and A3 is an observed value, not
  the bar. A pre-registered gate is not tightened to what its predecessors returned.
- **AC1's byte bound ratified at 40,960**, and the line bound recorded as **failed** rather
  than reinterpreted.
- **ADR-028's decisions renumber to D8–D12**, and every internal reference with them.
- **The next-free marker advances to `ADR-030+`, not `ADR-029+`** — a marker naming a
  reserved ID is the S74 defect (d) this table exists to prevent.
- **`CURRENT.md` rolls the outgoing `## Previous session` block (S84), not the S85 one** —
  rolling S85 would have left a gap at S84 in `CURRENT_history.md` and left S86 without its
  immediate predecessor.
- **ADR-028 §6 item 3 records the five copied figures as OWED**, not disposed, because the
  `tech_debt.md` entry written in the same pass says they are owed.

