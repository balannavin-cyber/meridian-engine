# ADR-029 (DRAFT) — Model routing and token efficiency

> **STATUS: DRAFT. NOT FILED.** No Decision Index row is added by this file, no
> register is edited, and nothing here is committed. The draft lives under
> `docs/research/s87_routing/` precisely so that it is not mistaken for an
> accepted decision sitting in `docs/decisions/`.
>
> **ID provenance.** The Decision Index already carries a reserved row reading
> *"ADR-029 | Model routing and token efficiency | … RESERVED S86 2026-09-30 —
> NOT DRAFTED. ID reserved so the topic cannot be collided with. Nothing is
> decided and no measurement is claimed."* This draft is that reservation being
> discharged. Cited by row content, not by line number. **The reserved row is
> re-confirmed at filing time, not at drafting time**, and the next-free marker
> is advanced in the same pass that consumes the ID.
>
> **Decision labels start at D13.** ADR-026 owns D1–D3, ADR-027 owns D4–D7, and
> ADR-028 owns D8–D12. A bare label that resolves against whichever document the
> reader happens to be in is the wrong-citation class this project has already
> paid for; the numbering is disjoint so that it cannot recur.
>
> **Task classes are named TC1, TC2 and TC3.** The bare `T`-prefixed labels are
> already taken in this corpus — by an enhancement-register test and by
> ADR-026's harness tests — so the `TC` prefix exists to keep them apart. The
> acceptance criteria are labelled `AC29-n` for the same reason: the bare `A`-
> and `C`-prefixed label spaces are occupied.
>
> **No measured figure appears in this document, in digits or in words.** Where a
> count would be the natural thing to write, the citation appears instead —
> `WS3.1_baseline.md §n` for measurements, `ADR-028 §n` for the harness — and the
> number stays in the record where it can be regenerated. **No model name, model
> identifier or price appears here either.** Those live in the mapping file,
> which is data and is versioned as data.

---

## 0. Status, context, and what this ADR does not decide

### 0.1 Status

**DRAFT.** Nothing below is in force. Every threshold is an open slot.

### 0.2 Context

What makes this decidable now rather than earlier:

**There is a measurement.** `WS3.1_baseline.md` measured what the Claude Code
transcripts for this project can and cannot tell us. Its findings bound
everything in this ADR. Token accounting is only meaningful when responses are
deduplicated by their message identifier, because a streamed response occupies
more than one transcript line (`WS3.1_baseline.md §3`). And approved permission
prompts are **byte-invisible**: an approval and a call that never prompted are
indistinguishable in the record, so the denial count has no denominator, and no
prompt rate, approval rate or approval-to-denial ratio can ever be computed
retrospectively (`WS3.1_baseline.md §5a`). Anything this ADR wants to know about
prompting has to be logged forward from the moment the decision is taken.

**There is a harness.** ADR-028 ran a behavioural comparison across both arms of
a change, graded blind, resolved by a 2-of-3 majority per prompt, with the CLI
pinned across arms and a launch-time version assertion that would have aborted a
mismatched run (ADR-028 §4, ADR-028 §7). That is a reusable pattern for answering
*"did this change make the system worse?"*, and it is the pattern §5 adopts for
model routing.

**The cost figures are the tool's own.** `WS3.1_baseline.md §4` cross-checks
independently emitted cost fields against each other. No price table is applied
anywhere in that instrument, and none is applied anywhere in this ADR. That
property is deliberate and §3 preserves it: a routing decision justified by a
price the project typed in is a routing decision justified by a number nobody
measured.

**What is not yet true.** There is no routing policy. Every task in this project
— a byte count, a register splice, an architectural ruling — runs on whatever
model the session happens to be using, and the only lever ever exercised is the
operator starting a new session. That is not obviously wrong. It is undecided,
and undecided is what this ADR proposes to change.

### 0.3 What this ADR does **not** decide

Named explicitly, because the absence of a decision should read as a decision and
not as an omission.

- **It does not pick a model for any class.** The class-to-model assignment is
  data, lives in the mapping file, and is an operator ruling (§2).
- **It does not set a single threshold.** Every number in this design is an open
  slot. A draft arriving with thresholds already chosen would be asserting a
  calibration nobody performed — the shape Rule 0 and ADR-009 both exist to
  refuse.
- **It does not claim a saving.** No efficiency figure is stated, predicted or
  implied. §9 pre-registers how a saving would be established; establishing one
  is later work.
- **It does not authorise a change of behaviour on any production path.**
  Routing governs which model does the work. It does not relax any gate, any
  permission, any review, or any write discipline.
- **It does not settle the absolute-path question.** `WS3.1_baseline.md §6` has
  now run and its finding is recorded at §6.1 below. The finding is a measurement;
  what to do about the convention is a ruling, and that ruling was made by the
  operator rather than by this document — it is recorded in `rulings_s87.md`.

---

## 1. Task classes

**D13 — Work is classified into the classes TC1, TC2 and TC3, and the class is a
property of the task, not of the person or model performing it.**

| class | name | what it covers | what makes it this class |
|---|---|---|---|
| **TC1** | mechanical | greps and inventories; file, hash and byte checks; extraction of a value from a known location; polling a state; applying a splice that has already been APPROVED | The correct output is determined by the input. Independent competent performers produce the same answer, and a checker can confirm it without judgement. |
| **TC2** | routine judgement | drafting a register entry from measured findings; writing code that has tests; grading against a written rubric | Judgement is required, but it is bounded by an artefact — a measurement, a test suite, a rubric — that exists before the work starts. |
| **TC3** | design and adjudication | ADRs; operator rulings and their supporting analysis; classifying an audit finding; diagnosing an incident | The artefact that would bound the judgement is the thing being produced. There is nothing to check the answer against except the reasoning. |

The boundary that matters is **TC1 against TC2**, and it is drawn at
*determinacy*, not at *difficulty*. Applying an approved splice is TC1 however
large the splice, because the diff was approved and the only question left is
whether the bytes landed. Deciding **whether** a splice should be approved is
never TC1.

The boundary between TC2 and TC3 is drawn at **whether the standard pre-exists**.
Grading a frozen prompt set against a frozen rubric is TC2. Writing the rubric,
and ruling on the cases it fails to cover, is TC3 — and this project has a
recorded instance of exactly that distinction going wrong, where a grading rule
was narrowed after both arms had been measured and had to be labelled post-hoc
because it was (ADR-028 §7.1).

**D14 — Risk override: any task whose output is written to a canonical document,
to production code, or to the database carries a TC3 review regardless of the
class the work itself falls in.**

The override is on the **destination**, not on the effort. A one-line splice into
`tech_debt.md` is mechanical to perform and canonical in its effect, and the
second property is the one that decides. This is not a statement that mechanical
work is unreliable; it is a statement that a cheap review on a canonical write is
cheap insurance.

**What the override does not mean:** it does not require that the review be
performed by a different model, or by the operator personally. Whether a TC3
review is a same-class re-read, a higher-class re-read, or an operator read is
open.

> **OPERATOR RULING OWED — what form a D14 review takes:** a re-read by the same
> performer, a re-read by a higher class, an operator read, or a mechanical
> verifier standing in for it where one exists. ADR-027 (DRAFT, not accepted) D5
> proposes such a verifier for the doc-close path; it is a proposal, not an
> available component.

> **OPEN QUESTION — not a decision, and no part of D13 or D14 rests on it. A TC1
> performer without deterministic tools counts by reading.** The TC1 v1 shadow run
> has been executed. Its full tally is at
> `/home/ssm-user/merdian_ledger/tc1_v1_tally.md` — outside the repository, with
> the ledger, per §3 — and **the shadow performer failed the pre-registered
> agreement bar**. The failure was not scattered: it was a **systematic miss on
> the line-count tasks**, in a single direction, while the tasks that resolve by
> listing files came back clean. No figure is restated here; the tally holds them,
> and it is also where they can be recomputed from the suite and the ledger.
>
> **The question this raises is about the class, not about the performer.** §1
> draws TC1 at determinacy — the correct output is determined by the input — and
> counting the lines in a file is as determinate as a task gets. What the shadow
> run exposed is that a determinate *answer* does not imply a deterministic
> *method*: a performer that reads a file and counts is estimating, and nothing in
> the class definition says it must not. **Should TC1 work be required to run a
> deterministic tool rather than to read?** If it should, then consequences follow
> that this draft does not currently state: D21's mechanical check becomes a
> constraint on how the output is produced and not only on the output, and the TC1
> boundary at §1 needs a method clause it does not have.
>
> Recorded as an open question because the evidence is one suite on one class, and
> because the alternative reading is live: that the class is fine and the shadow
> performer simply is not adequate for it, which is what the gear-down gate at §4
> exists to establish and did.

> **OPERATOR RULING OWED — whether TC1 work must use deterministic tools rather
> than model reading, and if so whether a TC1 task for which no such tool exists
> stops being TC1.**

---

## 2. Routing as data

**D15 — The class-to-model mapping lives in exactly one file, it is data rather
than prose, and no decision document restates its contents.**

The reason is not tidiness. A mapping restated in more than one place drifts, and
the drifted copy reads exactly as plausibly as the current one — the failure
shape recorded across this project's registers as a stale claim outliving the
thing it described. **One file, and every other document points at it.** This
document deliberately contains no model name, so that it cannot become one of the
drifted copies.

> **OPERATOR RULING OWED — where the mapping file lives, and in what format.**

> **OPERATOR RULING OWED — the initial mapping itself: which model each of TC1,
> TC2 and TC3 is assigned to at adoption.** No assignment is suggested here.

**D16 — Per-class subagents are declared through `.claude/agents/*.md`
frontmatter, so that the routing is exercised by configuration rather than by the
operator remembering to state it.**

A routing policy that depends on a human typing the right thing each time is a
policy followed on the sessions where it is remembered and silently abandoned on
the rest — and because approvals leave no transcript record
(`WS3.1_baseline.md §5a`), the abandoned sessions would not be distinguishable
from the observed ones. The frontmatter is the enforcement point.

**D17 — Everyday work names a model by alias; any run whose results will be
compared against another run pins an exact identifier.**

These are different requirements and conflating them costs a comparison. An alias
is what makes the mapping maintainable: it survives a version bump without an
edit. A pinned identifier is what makes an experiment interpretable: ADR-028
§7.3 records a toolchain version moving underneath an experiment mid-flight, and
the response was not to note the version but to **assert** it at launch and abort
on mismatch. The same discipline applies one level up, to the model. **An arm
that silently ran on a different model is indistinguishable from one that did
not**, which is the Rule 0 shape.

---

## 3. The measurement loop

A routing policy that is never measured is a preference. §3 is what makes it a
decision that can be wrong.

**D18 — Every routed unit of work writes one row to a cost ledger.**

| field | content | note |
|---|---|---|
| class | TC1, TC2 or TC3 | as assigned before the work ran, not after |
| model | the identifier actually used | read from the run, not from the mapping — a mapping is an intention |
| tokens | deduplicated by message identifier | mandatory per `WS3.1_baseline.md §7` R3; a per-line sum inflates every field |
| cost | from the tool's own emitted fields only | no price table is applied, per `WS3.1_baseline.md §4` |
| turns | carried | **informational only.** Harness turns are not a unit of work and are not comparable across arms — `WS3.1_baseline.md §4` says so explicitly, and this ledger inherits the caveat rather than quietly dropping it |
| verifier outcome | pass, fail, or not-applicable | the field that makes the cost column mean something |

The **verifier outcome** is the load-bearing column and the reason the ledger is
not merely an expense report. Cost without an outcome ranks a model that answers
cheaply and wrongly above one that answers dearly and correctly. §5 states the
consequence: the comparison is **cost per passed task**, never cost per task.

**D19 — The forward-logging requirements from the baseline are adopted as ledger
inputs.**

`WS3.1_baseline.md §7` R1 requires that **permission prompts be logged at the
point the prompt is raised and resolved**, because §5a establishes that no
retrospective analysis can ever recover them. R2 requires that **context-limit
events be logged with the context size at the moment of failure**, because both
corpora together yielded almost nothing to work from, and what they did yield was
identified by a margin so thin that a slightly different reading would have
classified it as something else (`WS3.1_baseline.md §5b`).

Both are adopted. **The mechanism for each is named as an open item and is not
chosen here** — a hook, a wrapper, an operator note, or something else. Choosing
a mechanism in a decision document without having tried one is how a design
acquires a component that does not exist.

> **OPERATOR RULING OWED — the mechanism by which permission prompts are logged
> (R1).**

> **OPERATOR RULING OWED — the mechanism by which context-limit events are logged
> (R2).**

> **OPERATOR RULING OWED — where the ledger lives, who owns its schema, and
> whether it is a repository file or a register.**

**D20 — The ledger is reviewed on a fixed recurring cadence, and the review is a
scheduled obligation rather than an occasion.**

The distinction is the point. An artefact reviewed "when someone looks" records a
regression for as long as nobody looks. **TD-S80-NEW-18** (`tech_debt.md`,
RESOLVED S81) is this project's instance of that class: a condition visible in the
system and invisible to the operator until it took the box down, closed by
building the watcher that would have surfaced it. The review must be on a
calendar.

> **OPERATOR RULING OWED — the review cadence, and who performs it.**

---

## 4. Gearing with guardrails

Routing cheaper work to a cheaper performer is only safe if the system can tell
when it has gone too far. §4 is the brake.

**D21 — Every TC1 and TC2 output is subject to a mechanical check.**

Not a review, a **check**: something that can fail for the reason it names. This
is Rule 0 applied to routing. A hash comparison, a byte-count assertion, a test
suite, a re-derivation from source — the specific instrument varies by task, and
what does not vary is that the check must have a failure mode a real defect
produces. A check that passes on every input is documentation.

TC3 output is not mechanically checkable by construction — if it were, it would
be TC2 — which is why D14's review sits on the destination instead.

**D22 — Gearing DOWN is gated on agreement; gearing UP is automatic.**

The asymmetry is deliberate and is the whole of the guardrail.

**Down** — moving a class to a cheaper performer — happens only after shadow
runs, in which both performers do the same work and only the incumbent's output
is used, agree at a **pre-registered** threshold. Pre-registered means fixed
before the shadow runs start. An agreement bar chosen after the results are in is
the shape ADR-028 §7.1 had to label post-hoc, and the only reason it could be
labelled at all is that the pass bar it departed from had been written down
first.

**Up** — reverting a class to a more capable performer — is automatic and
immediate on either of these triggers: **any mechanical checker failure**, or
**any disagreement found in sampled review**. No deliberation, no batching, no
waiting for the cadence in D20. Reverting cheaply and often is the property that
makes it safe to try gearing down at all.

**D23 — Results are never averaged.**

A regression is investigated, not absorbed into a mean. A favourable total that
contains a regression is a regression plus some gains, and the regression is the
thing that needs explaining. This is ADR-028's pass bar generalised, where *"any
regression is investigated, never averaged away"* was written before either arm
ran (ADR-028 §4).

> **OPERATOR RULING OWED — the shadow-run agreement threshold for gearing down:
> how many runs, and what agreement rate.**

> **OPERATOR RULING OWED — the sampling rate for the review that can trigger an
> automatic gear-up.**

---

## 5. Re-benchmark on model change

**D24 — The mapping is re-derived from a frozen evaluation suite whenever a model
in it changes, and the deciding statistic is cost per PASSED task.**

A mapping is a claim about which performer is adequate for which class. A model
change invalidates the claim without invalidating the mapping file, which is the
dangerous combination: the file still reads correctly and is no longer supported
by anything.

The suite is built on the pattern ADR-028 established and validated, adopted here
as a whole rather than reinvented:

| property | requirement | why, in one line |
|---|---|---|
| frozen prompts | fixed and sha-pinned before the first arm runs | a prompt edited between arms makes the comparison meaningless, and nothing in the output would show it |
| per class | prompts drawn for each of TC1, TC2 and TC3 | a suite that exercises only one class cannot rank performers for the others |
| blind grading | graders hold the rubric and not the arm identity | ADR-028 §7.1 graded both arms on one grader line and reports what that cost in consistency, which is the argument for doing it |
| 2-of-3 majority | an arm's result on a prompt is the majority of its runs, per ADR-028 §4 | a single run confuses a model difference with run-to-run variance |
| negative controls | at least one check that proves the suite CAN fail | Rule 0: a suite that has never failed has not been shown to be able to |
| ambiguity escalation | borderline grades go to the operator | no self-grading of the cases where the grade is the finding |

**Cost per passed task, not cost per task.** A performer that fails part of a
class is not a cheaper way of doing that class; it is a different and worse
outcome at a lower price. Nothing in the ledger ranks performers until the
verifier outcome column is joined to the cost column.

> **OPERATOR RULING OWED — the size and per-class composition of the evaluation
> suite, and the pass bar that decides adequacy for a class.**

> **OPERATOR RULING OWED — whether cost per passed task is compared at a fixed
> budget or at parity of outcome, and who grades.**

---

## 6. Session hygiene

**D25 — Context is managed by explicit practice rather than by hoping a session
stays small.**

| practice | what it does |
|---|---|
| a fresh context per workstream | prevents an unrelated earlier workstream from riding along in every subsequent prompt |
| multiplexed terminal sessions | lets workstreams stay separated without discarding one to start another |
| a fresh session for any heavy task | a task that will consume a large context starts from a small one |
| subagents for bulk reads | a subagent returns the conclusion; the file dumps that produced it do not enter the parent context |
| intermediate results written to files | a result on disk is re-readable at the size of a path; a result held in context is re-read at the size of itself |

The baseline is consistent with this being worth doing — `WS3.1_baseline.md §3`
reports context peaks and the count of sessions reaching high peaks for both
corpora — but the baseline **measures context, it does not measure the remedy**,
and no claim is made here that these practices have been shown to help. They are
adopted as discipline, and D18's ledger is what would eventually turn that into a
measurement.

**D26 — Any live corpus is measured from a sha-manifested snapshot, verified
before and after the run.**

Adopted verbatim from `WS3.1_baseline.md §7` R4, which was not a precaution but a
response to a measured failure: the first run against the live corpus failed its
own cross-check because the corpus grew mid-measurement, and the cross-check is
the only thing that noticed (`WS3.1_baseline.md §1`). Every subsequent figure
would have silently inherited the disagreement.

### 6.1 The absolute-path rule — TESTED, RULED

This project currently prefers absolute paths over directory-changing compound
commands. **That preference is now measured, and the operator has ruled on it; see
`rulings_s87.md`.**

`WS3.1_baseline.md §3` reports per-form denial rates across both corpora, and
`WS3.1_baseline.md §6` states why they cannot settle the question: these are
observational rates over unequal populations, not an experiment, and — the
decisive point — an approved prompt leaves no record, so a low denial rate is
**equally consistent with "never prompted" and with "prompted and approved every
time"**. The transcripts cannot distinguish the cases.

`WS3.1_baseline.md §6` is the operator-run experiment that can, and **it has now
run**. It asked one narrow question: does a directory-prefix argument break the
built-in read-only no-prompt match?

**It does.** Per `WS3.1_baseline.md §6`, the directory-prefixed read-only
invocations prompted and the bare ones did not — including the prefixed form that
named the very directory the session was already working in, which changes nothing
about what the command reads. **The evidence therefore supports the claim this
section was written so that it could be falsified: for `git`, the absolute-path
convention buys permission prompts.** The convention adopted to reduce prompting
increases it on this path.

**What the evidence is, stated with its scope.** n=1 per command, every command
run in a single session, operator-observed, on `git` alone. That is an **existence
result**: it
establishes that the prefixed form *can* fall outside the built-in match, on the
forms tried. It is not a prompt rate, it says nothing about other read-only verbs,
and `WS3.1_baseline.md §5a` is precisely why a rate cannot be recovered from the
transcripts instead — which is what made an operator-run experiment necessary in
the first place.

**The ruling stays owed, and the scope is why.** A measurement is not a decision.
The finding is on one verb at n=1 per command, and what follows from it — drop the
convention for `git`, drop it for every read-only verb, or retain it and accept the
prompts — is the operator's call. Nothing else in this ADR depends on the
convention either way.

**The allow-rule test ran, and it passed.** A set of read-only `git -C` allow
rules was added and then exercised in a fresh session against a bar written down
beforehand: the read-only invocations were to run with no prompt, and a
`push --dry-run` on the same path was to prompt. Both halves held, and the ruling
that followed is recorded in `rulings_s87.md` with its date and the operator's
words. **It is not restated here** — neither the ruling nor the residual limit
recorded beside it, which §7 carries as its own row. The finding above is
unchanged by the ruling: the convention buys prompts on the built-in match, and
the allow rules are what pays for them.

> **OPERATOR RULING #12 — RULED 2026-09-30 19:06 IST. See `rulings_s87.md`.**
> The scope limit above survives the ruling: one verb, n=1 per command. Other
> read-only verbs remain untested.

---

## 7. Permissions and safety baseline

**Recorded facts with their sources, not decisions.** §7 exists so that the
routing design is built on a stated baseline rather than an assumed one. Nothing
in this section is changed by this ADR. **Where a row could not be sourced to a
repository file by this pass, it says so in its own source cell** rather than
being promoted to a measured fact.

| # | fact | source |
|---|---|---|
| a | A built-in read-only command set exists and is **not configurable**. Listing those verbs in an allow rule adds nothing and implies a permission that is not ours to grant — for the forms the built-in set matches. Forms it does not match, such as `git -C <path>` (§6.1), do need allow rules; ruling #12 added them. | `docs/registers/session_log_history.md`, the Session 73 entry dated 2026-09-06 (commits `2c26cfe` + `057e890` + `3b22278`), item (2) — the block recording that `allow` was left deliberately empty for this reason. |
| b | User-level permission counts: **the allow / ask / deny counts in `~/.claude/settings.json` — changed at S87 by ruling #12, see `rulings_s87.md`**. | The live settings file. The `CURRENT.md` S86 block holds the pre-S87 values and is superseded by the S87 change — the restated-copy drift D15 names, observed here rather than argued. |
| c | `ask` rules survive automatic-approval mode — the mode does not silently convert an ask into an allow. | **S87 starter prompt (project knowledge, not in repo); not verified by this pass.** |
| d | A `Read` or `Edit` deny is a boundary **for the `Read` and `Edit` tools only, and not for other readers of the same file**. A `Read` deny does block the file commands the permission layer recognises; it does not reach readers it does not recognise, at least one of which is auto-approved read-only, nor code that opens the file itself. | `tech_debt.md`, the **Gap 2** row (*"`Read` deny does not cover every reader"*). |
| e | A `Bash` deny is **bypassable by absolute path** — a deny written against a bare verb is not matched by the same verb invoked at its full path. **Measured on one form only.** The deny list is a speed bump, not a boundary. | `CURRENT.md` S86 block, verbatim, including its own scope limit: only the absolute-path form was tested, no other spelling was. |
| f | **Sandbox is available and is NOT enabled.** Recorded as state, not as a remediation. Enabling it carries an installation cost and a network-allowlist cost. | State: `CURRENT.md` S86 block. Costs: **S87 starter prompt (project knowledge, not in repo); not verified by this pass.** |
| g | **`.env` is never read from an agent session**, in any form. | Rule 19. Not a preference, and not subject to routing. |
| h | The read-only `git diff` and `git log` allow rules added by ruling #12 **permit a file write**: both verbs accept an `--output=<file>` argument, so a rule matched on the verb alone is not a read-only boundary. **Recorded, not fixed.** | `rulings_s87.md`, the ruling #12 block. |

Row (d) and row (e) are why §7 is a table rather than a paragraph. Each records a
limit **with its own scope attached** — (d) names the tools the boundary holds
for and the readers it does not reach; (e) names the single form on which the
bypass was measured — which is what keeps either from being read as a general
claim about deny rules.

**None of this is relaxed by routing.** Class TC1 does not get a wider permission
surface because its work is mechanical. If anything the implication runs the
other way, and it is stated as an open item rather than assumed.

> **OPERATOR RULING OWED — whether sandbox is enabled, and if so who pays its
> installation and network-allowlist cost.**

> **OPERATOR RULING OWED — whether row (e)'s deny-bypass gap is closed, how, and
> whether the untested spellings are enumerated before or after.**

---

## 8. Toolchain

**D27 — Any run whose results will be compared against another run asserts its
toolchain and model identity at launch and aborts on mismatch.**

ADR-028 §4 and ADR-028 §7.3 record the case that produced this. An automatic
update landed between the arms of a running experiment. The response established
the full procedure, and this ADR adopts it rather than restating its numbers:

| element | what it is | why it is not optional |
|---|---|---|
| pin the CLI | install a specific version through the documented installer form | an arm on a different toolchain is a confound, not a data point |
| disable automatic updates | the documented environment key, confirmed through the tool's own diagnostic | a pin that can be overwritten by a background update is not a pin |
| the channel side effect | installing a pin **changes the update channel**, inert while updates are disabled and live the moment they are re-enabled | a dormant change is the kind that surfaces later with nothing pointing at it |
| launch-time version assertion | the runner **asserts** the version and **aborts** on mismatch | recording a version does not protect a comparison; only aborting does |
| model-identity parity check | the same assertion applied to the model identifier, across arms | D17's requirement, enforced here rather than trusted |

The fourth element carries the argument, and ADR-028 §4 states it plainly: a
version check that only *records* the version does not protect the comparison,
because an arm that silently ran on a different toolchain is indistinguishable
from one that did not.

**The current pin decision is not made here.** Whether the CLI stays at its
present pinned version, advances, or moves to a channel is a WS1.2 question.

> **OPERATOR RULING OWED — the current CLI pin: hold, advance, or unpin, and on
> what trigger. (WS1.2.)**

> **OPERATOR RULING OWED — whether automatic updates stay disabled, and if they
> are re-enabled, which channel the box follows given the recorded side effect.**

---

## 9. Pre-registered acceptance for ADR-029 itself

Per ADR-009 discipline and Rule 0. **The criteria are named here; every number in
them is owed, and all of them are fixed before any shadow run begins.** A
threshold set after the first results are in measures the results, not the
system.

### 9.1 The criteria, named

| # | criterion | what it asserts | what would falsify it |
|---|---|---|---|
| **AC29-1** | **No quality regression.** On the frozen evaluation suite, at the 2-of-3 majority reading per ADR-028 §4, the routed configuration passes at least as many tasks per class as the unrouted baseline, with zero individual regressions. | Routing did not make the system worse. | Any single prompt passing before and failing after. This criterion is **not** satisfied by a favourable total. |
| **AC29-2** | **Checker coverage.** Every TC1 and TC2 task in the measured window carries a mechanical check with a demonstrated failure mode. | D21 is real rather than declared. | Any class of routed output with no check, or a check that has never been shown to fail on a seeded defect. |
| **AC29-3** | **Cost per passed task.** The routed configuration's cost per passed task is compared against the unrouted baseline's, per class, from ledger fields only. | The policy is doing the thing it exists to do. | A cost-per-passed-task figure that does not improve, or that improves only in a pooled total while a class worsens. |
| **AC29-4** | **Ledger completeness.** Every routed unit of work in the window produced a ledger row, and the forward-logging inputs from D19 are present. | The instrument that would detect a problem was running. | Any gap in the ledger. A window with missing rows is not a favourable result; it is an unmeasured window. |

**AC29-1 is the merge gate, and it is a veto.** AC29-3 and AC29-4 can be
satisfactory while AC29-1 fails, and AC29-1 failing fails the adoption
regardless. This is ADR-028's own structure, where the behavioural test governed
and the size result — including a failed clause recorded as failed — did not
relax it.

### 9.2 Deliberate asymmetries, so they are not read as oversights

- **No efficiency target is stated.** AC29-3 is directional and says *improve*,
  not *improve by n*. A target chosen before any routed run has happened is a
  guess, and a guess in an acceptance criterion becomes a number the project
  later defends.
- **AC29-1 takes no credit for gains.** Should the routed configuration pass more
  tasks, that is recorded and is **not** claimed as an effect of routing.
  ADR-028 §7.5 declined exactly that claim on exactly these grounds: small n, and
  nothing in the design isolating the change from run-to-run variance. The same
  refusal applies here in advance.
- **AC29-4 can only fail.** A complete ledger is a precondition, not an
  achievement, and it is listed so that an incomplete one cannot be reported as a
  neutral outcome.

---

## Appendix — OPERATOR RULINGS OWED

Every open slot in this draft, one line each, in the order the body raises them.
**ADR-029 is not filed until each has a ruling or an explicit deferral with a
date.**

Rulings are recorded as they land in `rulings_s87.md`, alongside this draft. The
marks below **point at that file and do not restate its contents** — a ruling
transcribed into a second place is a ruling that can drift out of agreement with
itself, which is the same argument D15 makes about the mapping. The final row was
added after the first pass and sits at the end rather than in body order, so that
the numbering the body and this table already share does not move.

| # | ruling owed | § |
|---|---|---|
| 1 | What form a D14 risk-override review takes: same-class re-read, higher-class re-read, operator read, or a mechanical verifier where one exists. | 1 |
| 2 | Where the class-to-model mapping file lives, and in what format. **RULED 2026-09-30 14:22 IST — see `rulings_s87.md`.** | 2 |
| 3 | The initial mapping itself — which model each of TC1, TC2 and TC3 is assigned to at adoption. **RULED 2026-09-30 14:22 IST — see `rulings_s87.md`.** | 2 |
| 4 | The mechanism by which permission prompts are logged going forward (R1). | 3 |
| 5 | The mechanism by which context-limit events are logged going forward (R2). | 3 |
| 6 | Where the cost ledger lives, who owns its schema, and whether it is a repository file or a register. **PARTLY RULED 2026-09-30 14:22 IST — location only, see `rulings_s87.md`; schema owner still owed.** | 3 |
| 7 | The ledger review cadence, and who performs it. | 3 |
| 8 | The shadow-run agreement threshold for gearing down: how many runs, and what agreement rate. **RULED 2026-09-30 14:22 IST — see `rulings_s87.md`.** | 4 |
| 9 | The sampling rate for the review that can trigger an automatic gear-up. | 4 |
| 10 | The size and per-class composition of the evaluation suite, and the pass bar that decides adequacy for a class. | 5 |
| 11 | Whether cost per passed task is compared at a fixed budget or at parity of outcome, and who grades. | 5 |
| 12 | Whether the absolute-path convention is adopted, retained provisionally, or dropped, now that the `WS3.1_baseline.md` §6 experiment has run. **RULED 2026-09-30 19:06 IST — see `rulings_s87.md`.** | 6 |
| 13 | Whether sandbox is enabled, and if so who pays its installation and network-allowlist cost. | 7 |
| 14 | Whether the Bash deny-bypass gap is closed, how, and whether the untested spellings are enumerated first. | 7 |
| 15 | The current CLI pin: hold, advance, or unpin, and on what trigger (WS1.2). **RULED 2026-09-30 17:41 IST — hold.** See `rulings_s87.md`. | 8 |
| 16 | Whether automatic updates stay disabled, and which channel is followed if they are re-enabled. | 8 |
| 17 | The numeric bar for each acceptance criterion in §9.1, fixed and dated before any shadow run. | 9 |
| 18 | Whether TC1 work must use deterministic tools rather than model reading, and whether a TC1 task for which no such tool exists stops being TC1. | 1 |

---

*DRAFT. Not filed, not committed, no Decision Index row. Sources:
`WS3.1_baseline.md` for every measurement cited; ADR-028 for the harness and
toolchain pattern; ADR-026 and ADR-027 (DRAFT, not accepted) for the label
namespaces; `CURRENT.md` S86 block, `docs/registers/session_log_history.md` and
`tech_debt.md` for §7's recorded facts.*
