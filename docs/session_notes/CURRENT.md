# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S83 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close** and **S84 at the S86 doc-close**, each moved verbatim rather than retyped. This file carries the current session and one predecessor, and nothing else.

---

## Last session

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

## Previous session S85

**Session 85 — 2026-09-29 (Tue).** Two halves: the ENH-98 **A3 + E1** arms run against
the pre-registration, then a **feasibility inventory and ADR-026 filed ACCEPTED**. **No
production change, no DDL, no database write.** Three commits, all documentation:
`3a78769` → `f925939` → `881b03b`.

| Field | Value |
|---|---|
| **A3 (SENSEX dte 2) — the first T1 arm** | Gate passed before the run: both symbols at **10:15:06 IST**, **0.00 %** row deviation against their own 09:15 reference (NIFTY 1020, SENSEX 768). Precondition **PASS at 3.79×** (19.1 against 3 × 5.051). **T1 PASS on this arm** — `exact/365` ATM **0.0425**, NEAR **0.0439**, the refusal needing *both* above 0.10. Interpretation clause **NOT TRIGGERED**. **T1 itself is not decided** — §2.6 evaluates it across the dte 1–2 pair, so the verdict follows A4. |
| **E1 (NIFTY dte 0) — the refusal fired** | Precondition PASS (17 ATM rows ≥ 10). `exact/365` ATM **0.2657** / NEAR **0.4949**, both over the 0.10 bar → **refusal**. Per §2.8 outcome use, **W1's expiry-day charm stays UNRECORDED until re-tested**; E2 is unaffected. Offset/`r_eff` **NO-TEST at 0.49×** — the pre-registered expected outcome at dte 0, and **not read as a finding**. `dte/365` and `dte/252` returned **0 rows at dte 0**, as pre-registered. |
| **ADR-026 FILED ACCEPTED** | `docs/decisions/ADR-026-docs-retrieval-index.md`. Docs retrieval index over the **138-file / 7.43 MB** text corpus: `rag` schema on the existing Supabase (**pgvector 0.8.2, available and NOT installed**), **ID-anchored byte-budgeted** chunking that splits *within* lines for the six paragraph-per-line files and by key path for `merdian_reference.json`, **hybrid ID-first** retrieval over ~6,300 heading-anchored entry IDs. Decision Index row added; reserved marker advanced. |
| **ADR-027 DRAFTED, not filed** | `docs/research/s85_rag/ADR-027-DRAFT-…md`. Drafting agent + verifier + operator diff gate. **Depends on ADR-026** and **inherits its §6 write boundary verbatim** — asserted byte-identical by `check_s6_verbatim.py`, not claimed in prose. Its **ID is RESERVED** in the Decision Index Pending table so the draft cannot be collided with. |
| **Rulings, all operator, all S85** | **A1** — ID-bearing recall@5 **= 100 %** (lexical match is deterministic, so a miss is a chunker defect and is fixed, not tolerated); prose-only recall@20 **≥ 60 %** / recall@5 **≥ 40 %**; **≥ 20 questions per class**, frozen before any index exists. **Staleness floors** — interactive absent when `age_doc_commits > 3` **OR** `age_days >= 2`; **drafting absent at `> 0`**; measured in **doc-commits** so code-only commits do not stale the index; re-index is **event-triggered, never on a timer**. **Embedding** — `bge-small-en-v1.5`, 384-dim, **ONNX local on EC2**; no document text leaves the host. **G1–G8** guardrails with **T1–T4** pre-registered; **G3a** `CPUQuota=50%` × **20-min hard timeout** = ≤ 10 credits/run logged in G7; **G3b** abort/requeue if interval `%steal` > **5 %** over a **10-second** `/proc/stat` sample; **G3c** Option 1 — **no IAM grant**, console review. |
| **The burst mode cannot be read from this host** | Measured: `ec2:DescribeInstanceCreditSpecifications` → **`UnauthorizedOperation`**; `cloudwatch:GetMetricStatistics` → **`AccessDenied`**; and the **`ListMetrics` control also denied**, which is what makes it a blanket denial rather than a metric-specific one. **G3's original start-of-run credit check was therefore unimplementable** — a check conditioned on a value the host cannot obtain. Recorded, not dropped; replaced by G3a+G3b. |
| **`CPUQuota` does not bound credit draw — the timeout does** | Found while doing the arithmetic, not by review. `t3.small` accrues ~24 credits/hr at a 20 %-per-vCPU baseline; a run pinned at `CPUQuota=50%` consumes **0.5 vCPU = 30 credits/hr**, i.e. **above the whole instance's accrual** before production's own use. **The binding quantity is `CPUQuota × timeout`**, which is why G3a fixes both factors. The same substitution shape as `OB_MIN_MOVE_PCT` and Guard 3. *(Credit figures stated from knowledge, **not measured** — operator confirmation owed.)* |
| **`§7.2` belongs to `capture_s74.md`, not the Deployment Topology** | I was one step from qualifying a bare `§7.2` as "Deployment Topology §7.2" and stopped to measure. The only heading matching deploy-direction is **`capture_s74.md:182` — `### 7.2 Deploy-direction inversion — still UNRATIFIED`**. Deployment Topology **§7.2 is "Windows Task Scheduler"** — a different section entirely. And the §7.3 / §7.6 "Guardrails doc" premise **does not resolve at HEAD**: 0 such headings, 0 `bare-call` matches, no Guardrails file tracked. **TD-S85-NEW-2.** |
| **Windows surfaces — 0 `docs/` references, with positive controls** | **OPERATOR-MEASURED** on the Local Windows box, S85 ~11:48–11:49 IST, PowerShell at `C:\GammaEnginePython`: `Get-ScheduledTask` actions filtered on `docs\|\.md\|research` → **0**; positive control on `Gamma\|merdian\|meridian` → **19 tasks**. `Select-String` over top-level `*.bat` / `*.ps1` for `docs[\\/]\|\.md\b\|research` → **0**; positive control `python` → **199 matches**. **19 is "tasks matching the name/path filter", NOT a total inventory** — it does not contradict Deployment Topology's 20 or S76's 23. **EC2-measured, by this tool:** 31 tracked `.bat`/`.ps1`/`.cmd`, **0** `docs/` refs, control 28 files / 88 `.py` matches. Different scope (tracked, all dirs) and a different control pattern, which is why 199 and 88 differ. |
| **Two of my own instruments were wrong, both caught by measurement** | A residual-`DRAFT` grep on the filed ADR-026 **errored** (ugrep complexity limit) and the `\|\| echo` then printed *"(none — clean)"* — a **false clean**, and the CLAUDE.md anti-pattern verbatim; the fixed-string re-run returned the real 0/0/0/1. And `check_xrefs.py` reported a **false EXTERNAL** (`S85 -> G3`) because a bare session marker was treated as a document qualifier, silently skipping a local check; the qualifier was removed with the reason in a code comment. |
| **The D3 label collision** | `D3` was declared in **both** drafts — ADR-026's staleness floor and ADR-027's drafting agent. Renumbered ADR-027 to **D4–D7** through `@@`-placeholders so `D4→D5` could not re-hit a label `D3→D4` had produced, with **four foreign references masked and restored** (ADR-027 cites ADR-026 D3 twice; ADR-026 cites ADR-027's D5 twice). Now **mechanically prevented**: `check_xrefs.py` treats a token declared in both as a COLLISION and a bare use as AMBIGUOUS, with a selftest arm. |
| **Ledger** | TDs_NEW=**3** (TD-S85-NEW-1..3), TDs_CLOSED=**0**. **ADRs_NEW=1 — ADR-026 ACCEPTED**; ADRs_AMENDED=0; **Decision Index row ADDED** (first since ADR-025 at S80) and next-free advanced `ADR-026+` → **`ADR-028+`** with **ADR-027 reserved**. Enhancement Register TRIGGERED (ENH-98, A3/E1). Three commits, all pushed, HEAD == `origin/main` == `ls-remote` at **`881b03b`**. |

**The half that produced findings was the half that was supposed to be routine.** The
arms ran to their pre-registration and the refusal on E1 is a clean, pre-registered
outcome. Everything in the middle column above — an unimplementable guardrail, a quota
that bounds nothing, a citation pointing at the wrong document, a label declared twice, a
grep that reported clean because it had failed — came out of composing the ADR, and every
one was caught by a measurement rather than by reading it again.

## NEXT SESSION PICKS UP

**Time-boxed**

1. **A4 — Wed 2026-09-30, 10:15:59 IST.** Second T1 arm, SENSEX dte 1. **T1's verdict
   follows this arm**; the rule and thresholds are pre-registered at capture §2.6 —
   **do not re-derive them after seeing the arm.**
2. **E2 — Thu 2026-10-01, 10:15:59 IST.** SENSEX dte 0 gamma fidelity. Unaffected by
   E1's refusal.
3. **Pull `~/meridian-engine` after 16:00 IST** → `git pull --ff-only origin main` to
   **`881b03b`**. Three commits behind, **0 non-`docs/` files**. Note the old
   "`.py` count must be 0" gate **no longer applies**: the gap carries 7 `.py`, all the
   `docs/research/s85_rag/` checker toolchain, **none scheduled** — verified, the
   intersection with the 26 cron/unit-invoked scripts is empty.
4. **The NIFTY L9 stage-1 max-pain arm owed from S82** (TD-S80-NEW-1) — **still
   outstanding.** It rode on the A3 date and was not run; the A3 Decision-Index-adjacent
   row says so explicitly rather than reading as done.

**Owed measurements and decisions — none are mine**

5. **Burst mode — operator, from Windows.** `aws ec2 describe-instance-credit-specifications --instance-ids i-0878c118835386ec2 --region eu-north-1`.
   `standard` → credit exhaustion **throttles the whole instance**, degrading every
   production writer; `unlimited` → **billed** instead. The two justify different
   `CPUQuota` values, so settle it **before** T1–T4.
6. **T1–T4 must pass before the first real embedding run.** T4 carries a
   **pre-registered prediction of ~330 MB peak RSS** with its derivation; if measured
   peak exceeds 450 MB **the bar is not moved** — the run is investigated.
7. **`completed_at` DDL** — TD-S85-NEW-1. `rag.corpus_snapshot` needs the column and
   every retrieval must filter on it, or a half-built index is readable with no error.
8. **NEW — does the first full index build fit G3a's 20-minute hard timeout at
   `CPUQuota=50%`?** ~4,270 chunks on 2 vCPU, **unmeasured**. If it does not, **the build
   must be resumable across runs**, which ADR-026 does not currently provide. **Recorded
   as owed, not ruled** — TD-S85-NEW-3.
9. **ADR-027's two open items** — the **A2 metric definition and threshold** (the
   definition is the harder half, and must be frozen as `metric_version` before the
   first scoring), and **where the drafting LLM runs**, which ADR-027 does not decide.
10. **Everything under the S84 block's owed list that S85 did not touch carries
    unchanged** — capture depth / SENSEX monthly quote quality, the stage-2 gate
    redefinition (TD-S81-NEW-14), P5's canonical max pain, the scratch-evidence
    decision, the product-name scrub, and the vendor methodology question.

## OPERATOR RULINGS, S85

These exist only in chat and are recorded here, in ADR-026 and in the ENH-98 block.
**None authorises a build.**

- **A1 thresholds** — ID-bearing recall@5 **= 100 %**, prose-only recall@20 **≥ 60 %** and
  recall@5 **≥ 40 %**, **≥ 20 questions per class** frozen before any index is built.
- **Staleness floors** — interactive `age_doc_commits > 3` OR `age_days >= 2`; drafting
  `> 0`; doc-commits only; re-index event-triggered, never on a timer.
- **Embedding** — ONNX-local on MERDIAN EC2, `bge-small-en-v1.5`, 384-dim. No text egress.
- **G3c — Option 1.** Accept G3a + G3b; **no IAM grant**; operator reviews
  `CPUCreditBalance` in the AWS console periodically. **Accepted with its gap stated:
  there is no automated credit-balance gate, by decision.**
- **ADR-026 filed; ADR-027 stays a draft with its ID reserved.**
- **ADR-026 is MOVED, never copied, when filed** — two copies of an accepted ADR diverge,
  and once the index exists retrieval would return both.
