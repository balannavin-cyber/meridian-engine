# ADR-028 — Splitting `CLAUDE.md` into a loaded core and on-demand modules

> **STATUS: ACCEPTED, S86 (2026-09-30).** Filed with a Decision Index row. The
> split is built and merged; the outcome is §7.
>
> **While this was a draft it lived at `~/s86_test/s86_split/`**, because the
> ADR-028 behavioural test gave one arm `Read`/`Glob`/`Grep` over `~/meridian-cc`
> and a draft inside the tree would have been greppable answer material. Both
> arms are graded, so that reason has expired and the file is filed in place.
>
> **ID provenance:** `ADR-028` was next-free — the Decision Index reserved row
> read `| ADR-028+ | Next-free | — | Available |`, advanced from `ADR-027+` at
> the S85 close, with ADR-027 itself reserved for its own draft. Cited by row
> content, not line number (§D.40.6). **Re-confirmed at filing time**, and the
> marker is advanced in the same pass that consumes the ID.
>
> **Provenance note, recorded because it is the kind of thing this project
> files:** an earlier S86 message stated this draft already existed at
> `scratch/s86_split/ADR-028-DRAFT-claude-md-split.md`. **It did not** — that
> directory held only `map_claude.py` and `section_map.out`. A claim was made
> without the artefact behind it, the same shape as S81's unmeasured
> `comment_len`. This file is that claim being discharged, a turn late.

---

## 1. Status

**ACCEPTED, S86 (2026-09-30).** Proposed 2026-09-29 as a measure-only session;
the split was built and merged at `76ad9a3`. The decisions below are in force.

---

## 2. Context

### 2.1 The ceiling this project has been tracking does not exist

`TD-S73-NEW-8` and five other documents record `CLAUDE.md` as over a **"150k
ceiling"**. Traced to source: **`capture_s74.md` §8**, which reads *"421,684
bytes — 2.8× the 150k ceiling"*. **It carries no citation, and no external
source for it exists anywhere in the repository.** The figure then propagated
verbatim into `CLAUDE_history.md`, `session_log_history.md`,
`merdian_reference.json` and `CURRENT_history.md`.

**It is also in the wrong unit.** It is called a *"150k **context** ceiling"*
and then divided into **bytes**.

The documented guidance, from `https://code.claude.com/docs/en/memory`:

> **"Size**: target under **200 lines** per CLAUDE.md file. Longer files consume
> more context and reduce adherence."

> *"Claude Code loads a CLAUDE.md file of up to **4 MiB** in full and **skips a
> larger file**."*

Measured against the real numbers, `CLAUDE.md` at **327,949 bytes / 1,173 lines** *(the draft read 1,174; measured on `6bba0ce:CLAUDE.md`, which ends with a trailing newline, the count is 1,173 — §D.42.12)*
is:

| against | value | verdict |
|---|---|---|
| 4 MiB hard skip | 0.078× | **nowhere near being skipped** |
| 200-line target | **5.9×** | **far over — and this is the binding constraint** |
| the invented "150k" | 2.2× | meaningless |

**The tracked number was wrong in magnitude and in unit, and it understated the
problem.** The constraint is **lines**, not bytes. **TD-S73-NEW-8's figure needs
correcting at the next doc-close** — owed, not done here.

*(The 25 KB / 200-line limit that does exist applies to auto-memory's
`MEMORY.md` index, not to `CLAUDE.md`. Conflating the two is the likeliest
origin of the 150k figure, but that is a guess and is recorded as one.)*

### 2.2 What the file actually contains

Measured by `map_claude.py` over 39 sections:

| class | bytes | % | lines |
|---|---:|---:|---:|
| (a) hard rule / non-negotiable | 19,884 | 6.1 % | 113 |
| (b) operational procedure | 3,783 | 1.2 % | 64 |
| (c) settled decision | 91,195 | 27.8 % | 159 |
| (d) session footer / history | 185,494 | 56.6 % | 669 |
| (e) reference data | 27,554 | 8.4 % | 169 |

**(a) + (b) — everything binding — is 23,667 B, 7.3 %, 177 lines.** Duplication
against the registers measures **95–100 %** for every ID-bearing section; the 23
`Session NN engineering discoveries` blocks measure **100 %**.

### 2.3 Which mechanisms actually reduce startup context

From the same source, and this rules out the two obvious moves:

- **`@path` imports do NOT help.** *"Splitting into `@path` imports helps
  organization but doesn't reduce context, since imported files load at
  launch."* Max depth four hops.
- **Un-scoped `.claude/rules/` do NOT help.** *"Rules without `paths`
  frontmatter are loaded at launch with the same priority as
  `.claude/CLAUDE.md`."*
- **Path-scoped rules DO.** *"These conditional rules only apply when Claude is
  working with files matching the specified patterns."*
- **Skills DO.** *"skills … only load when you invoke them or when Claude
  determines they're relevant to your prompt."*
- **Subdirectory `CLAUDE.md` DO.** *"Instead of loading them at launch, they are
  included when Claude reads files in those subdirectories."*
- **Not loading a file at all** — history moved to `CLAUDE_history.md`.

---

## 3. Decision

**D8 — A core `CLAUDE.md` of ≤ 40 KB and ≤ 200 lines**, always loaded, carrying
all of class (a), class (b)'s entry points, the read order, the source-of-truth
map, and pointers.

**D9 — Procedures move to path-scoped rules and skills**, the only in-repo
mechanisms that defer loading: `.claude/rules/registers.md`, `sql-views.md`,
`python-writers.md` (each with `paths:` frontmatter), and
`.claude/skills/doc-close/`, `merdian-runbooks/`.

**D10 — All 23 discovery blocks and all 6 version footers move verbatim to
`CLAUDE_history.md`**, which is not loaded, leaving a one-line pointer.

**D11 — The settled-decisions block stays in the registers it already cites.**
At 91 KB and 95 % duplication it is the second-largest item, and moving history
alone leaves ~142 KB — **necessary and not sufficient**, exactly as the S74
split was.

**D12 — `@path` imports are NOT used for size.** They would look like a split and
save nothing.

---

## 4. Pre-registered acceptance criteria

Per ADR-009 discipline and Rule 0: a value obtained by running the thing is not
an assertion. Both criteria were **set before the before-arm ran**.

### AC1 — core size bound
Core `CLAUDE.md` **≤ 40,960 bytes AND ≤ 200 lines**. Both, not either: the byte
bound is this project's own target, the line bound is the documented one, and
the line bound is the one that binds.

### AC1 amendment, S86, made after measurement

**AC1-lines (≤ 200) FAILED.** Measured on the **shipped** core at `76ad9a3`:
**258 lines — 172 content, 66 blank, 20 structural**, over by **58**. Recorded as
**failed**, not reinterpreted. *(This paragraph first carried **281 lines — 172 content, 89
blank, 20 structural** from a pre-final build attempt, and predicted that collapsing every
run of blank lines would give **259**. The authorised tidy below was applied and the
shipped file measures **258** — the prediction was 1 line over, and both numbers are kept so the estimate
stays legible beside the measurement.)* The protected floor alone (Rules 0–19 at
43 lines, core §6 at 31, plus the 39 lines of scaffolding that rulings (a) and (c)
require) is 113 before anything optional, and ruling (d)'s nominated valve — the
universal anti-patterns subset — is 9 lines.

**The binding bound going forward is bytes: ≤ 40,960.** Measured on the shipped core:
**39,786 — PASS**, with **1,174 B** of headroom (97.1 % used). Rationale: the documented
reason for the line target is *context consumption*, and bytes measure that directly.
This file's density is **231 B per content line**, so the line count is a poor proxy for the thing the target
exists to control — it binds roughly 2.4× harder than the byte bound on this file and
would force relocations that serve the metric rather than the reader.

**This reverses AC1's own closing sentence**, which reads *"the line bound is the one
that binds."* That sentence is **left in place above and annotated here rather than
deleted**, in the shape ADR-025 Amendment B used: a reversed ruling stays legible as a
reversal. AC1's byte figure of 40,960 is unchanged and was pre-registered.

**AC2 is unchanged and remains the merge gate.** The line result does not relax it; a
behavioural regression still fails the split regardless of any size number.

**Growth rule for core, from now on:** any addition to core is offset by an equal or
larger relocation **in the same commit**, so core stays ≤ 40,960 B. Version footers stay
**one line, current session only**; predecessors go to `CLAUDE_history.md`.

**Allowed tidy, authorised with this amendment:** collapse runs of two or more blank
lines in core to one. Whitespace only. Conservation is unaffected because blank lines are
already excluded from the gate-1 comparison as non-identity-bearing. **No other change**
— the session contract and the session-end checklist stay in core, because behavioural
prompt B3 covers them.

### AC2 — behavioural test, 15 prompts, before and after
Set frozen by sha256 at `~/s86_test/behav_test_prompts.md` before the first run;
5 hard-rule, 5 procedure, 5 settled/history; **4 run with `--tools ""`** to
measure what deferred loading costs.

**Grading:** pass = correct answer **AND** correct rule/entry ID cited. Ambiguous
grades go to the **operator**; no self-grading of borderline cases.

**Pass bar (operator, S86, recorded before any run):**
- **Hard-rule: 5/5 before AND 5/5 after.** Any hard-rule miss after the split
  **fails the split.**
- **After ≥ before overall, with zero individual regressions.**
- Any regression is **investigated, never averaged away.**

### AC2-note — two prompts have footer-only answers
**B4** (`roq.sh` / `merdian_ro`) and **C3** (the PIN verdict) exist in
`CLAUDE.md` **only inside version footers** — v1.53 and v1.51. D10 moves those
out. B4 is on the NO-FILE arm and is therefore expected to regress; **C3 is on
the file arm and can still reach `capture_s74.md`, so no regression is predicted
for it** and none may be read into its grade. The pair converts *"moving history
is safe"* from an assumption into a measurement.

**Owed before D10 is executed: a sweep for what else is footer-only.** Two were
found by accident while writing fifteen prompts; the population is unmeasured.

### AC2-note-2 — the CLI moved mid-experiment and is pinned for the after-arm

Recorded because a toolchain change between arms is a confound, and the
alternative is discovering it while reading a regression.

- **The before-arm (`before_v3`) ran on CLI `2.1.277`.**
- **An auto-update to `2.1.280` landed on 2026-09-29, mid-experiment**, between the
  before-arm and this session. `claude doctor` reports it as
  `Last update attempt: success -> 2.1.280 (2026-09-29)`.
- **Auto-updates are now disabled** — `DISABLE_AUTOUPDATER: "1"` in the `env` key of
  `~/.claude/settings.json`, the form documented at
  `code.claude.com/docs/en/setup.md` §"Disable auto-updates", confirmed by
  `claude doctor` reading `Auto-updates: disabled (set by env: DISABLE_AUTOUPDATER)`.
- **The CLI is pinned back to `2.1.277`** via the documented native installer form
  (`curl -fsSL https://claude.ai/install.sh | bash -s 2.1.277`), so the after-arm runs
  on the same CLI as the before-arm. Verified: `claude --version` -> `2.1.277`;
  launcher -> `~/.local/share/claude/versions/2.1.277`; `~/.claude/settings.json` md5
  unchanged across the install (`f5bceafb47c57079d50ae50ca8c9ed9b`); ADR-027 D5-style smoke
  probe `claude -p "Reply with exactly: ok" --tools "" --max-turns 1
  --output-format json` returned `subtype: "success"`, `is_error: false`,
  `result: "ok"`, `num_turns: 1`.
- **Side effect of the pin, recorded rather than passed over:** the install changed
  `Auto-update channel` from `latest` to `stable` — the docs state *"The channel you
  choose at install time becomes your default for auto-updates."* Inert while
  `DISABLE_AUTOUPDATER` is set; it matters only if that key is later removed, at which
  point the box would follow `stable` rather than `latest`.

**Mandatory on the after-arm runner:** it **asserts `claude --version` == `2.1.277` at
launch and aborts otherwise.** A version check that only records the version does not
protect the comparison — an arm that silently ran on a different CLI is
indistinguishable from one that did not, which is the Rule 0 shape.

**Unpinning happens only after the after-arm is graded**, not before, and not as part of
any intervening session.

*(Unrelated observation from the same directory listing, recorded because it is
surprising and cheap to state: `~/.local/share/claude/versions/` holds `2.1.281` with an
mtime of Sep 24, earlier than `2.1.280`'s Sep 29. Not acted on.)*

---

## 5. Consequences

**Accepted:** a path-scoped rule fires on **file reads, not on topic** — asking
about register conventions without opening a register will not load the rule.
That is a real behavioural change and is what AC2 exists to detect.

**Not decided here:** the exact section-to-module assignment beyond the table in
§3; whether the settled block is trimmed or only relocated; and whether
`AGENTS.md` should carry any of this.

---

## 6. Open items requiring operator ruling before filing — **all four disposed**

1. **AC1's byte bound** — 40 KB is proposed, not ruled. The 200-line bound is
   documented and not negotiable.
   **RULED S86:** the byte bound is ratified at 40,960 and becomes the binding
   bound; the line bound **failed** and is recorded as failed (§4 AC1 amendment).
2. **The settled-decisions block (D11)** — relocate wholesale, or trim to the
   subset that is a *rule* rather than a *record*?
   **RULED S86 (ruling (b)):** trimmed to rules; a bullet drops to a register only
   with a recorded quote; the 50 bullets carrying no register ID go to core, a rule
   file, or history — **never a new register row**, and no register file was edited.
3. **TD-S73-NEW-8's figure** — correct the "150k ceiling" to 200 lines / 4 MiB
   at the next doc-close, and decide whether the five documents that copied it
   are corrected in place or annotated.
   **TD-S73-NEW-8 corrected in the S86 doc-close `tech_debt.md` pass** (status
   **SUPERSEDED BY ADR-028**); **the five documents carrying the copied figure
   remain OWED** as an operator decision: correct in place, or annotate.

   **Disposed S87 (2026-10-01) — annotated by erratum, operator ruling 06:44 IST.**
   The five documents are **left byte-identical**; the correction lives here, in the
   ADR that found the error, rather than in ten edits across four registers and a
   session note. The reading to apply at every location below:

   > **"150k" is the Claude Code CLI's 150.0k-CHARACTER warning for `CLAUDE.md`, not
   > a token ceiling and not a byte ceiling.** Measured S87: the warning is *shown* on
   > pre-split `6bba0ce` and *absent* on post-split `35588a2`
   > (`docs/research/s87_routing/ws2_6_context_measure.md`). ADR-028 §2.1 is correct that
   > the figure was uncited and in the wrong unit; it is now also **identified** — it
   > is a real tool limit, in characters, that the project recorded in bytes.

   **Ten occurrences, located S87** (`file:line`, newest measurement):

   - `docs/session_notes/capture_s74.md:192` — **the source**: *"421,684 bytes — 2.8×
     the 150k ceiling."* §2.1 cites this as `capture_s74.md` §8 without a path; the
     file is under `docs/session_notes/`, **not** `docs/research/`.
   - `docs/registers/CLAUDE_history.md:9` · `:602` · `:604` — three copies
     (*"~2.8x the 150k context ceiling"* twice, *"still ~1.9x the 150k ceiling"* once).
   - `docs/registers/session_log_history.md:7` · `:9`.
   - `docs/registers/merdian_reference.json:4924` · `:5049`.
   - `docs/registers/CURRENT_history.md:135` · `:156`.

   **Two of the ten are not copies of the error, and are recorded as such rather than
   counted in.** `merdian_reference.json:4924` is **already a correction** — it reads
   *"TD-S73-NEW-8 SUPERSEDED BY ADR-028: its '150k ceiling' was unsourced, in the wrong
   unit…"* — so it mentions the figure in the act of retracting it. And
   `session_log_history.md:9` / `CURRENT_history.md:156` read *"407.3k against 150k,
   **warned on every launch**"*: those two were describing the **tool's warning**, which
   is the one thing in this family that was true. So the tally is **1 source + 7 copies
   of the claim + 1 prior correction + 2 descriptions of the real warning**, not ten
   identical errors.

   **Why annotate rather than correct in place.** `CLAUDE_history.md`,
   `session_log_history.md` and `CURRENT_history.md` are **history files**: ADR-028 D10
   moved their content *verbatim* so conservation could be asserted, and editing them
   now would break the property the split was verified on. A history that is corrected
   in place stops being a record of what was believed at the time.
4. **Confirm `ADR-028` still free** at filing time by the reserved-row method.
   **DONE at filing:** the reserved row read `| ADR-028+ | Next-free | — | Available |`
   and is advanced in the same pass that consumes the ID, with ADR-029 reserved.

---

## 7. Outcome — measured, S86 (2026-09-30)

The split was built on `s86/claude-split`, merged, and both behavioural arms are
graded. **AC2 is met.**

### 7.1 AC2 — the merge gate

Graded **blind** by graders holding the rulings but not the arm identity; three
runs per prompt, arm result = 2-of-3.

| | before | after |
|---|---|---|
| **blind pass count** | **10** / 15 | **12** / 15 |

The pass bar's three clauses, as the tally reports them:

| clause | test | verdict |
|---|---|---|
| (a) | all five class-A (hard-rule) prompts PASS at 2-of-3 | **PASS** |
| (b) | no PASS → FAIL regression | **PASS** |
| (c) | after pass count ≥ before | **PASS** (12 vs 10) |

Two gains, **B2** and **C1**, both FAIL → PASS. No regressions. Source:
`~/s86_test/blind_key/_unblinded_result.txt`.

**The label these clauses carry in the harness is `D3(a)`–`D3(c)`**, from
**Amendment 2 in `~/s86_test/FROZEN.txt`** — a namespace distinct from this ADR's
decisions and from ADR-026's D1–D3. They are written as (a)–(c) here so no bare
`D3` in this document resolves against ADR-026.

**One discrepancy, recorded rather than reconciled away.** The blind before-arm
scored **10 / 5**; the locked before-arm baseline was **11 / 4**. The single
disagreement is **B3**, blind FAIL against locked PASS: the blind grader failed it
under `FROZEN.txt` D6(4), **required-element omission** — the run did not give the
`MERDIAN: [OPS]` commit prefix. The comparison used is **blind-vs-blind** — the
same grader line on both arms — which is why the gate reads 12 vs 10 and not
12 vs 11. Grading both arms by one line matters more than which line it is.

**RULING 3 was made AFTER blind grading of both arms**, unlike the pass bar and
RULINGS 1–2, which predate their arms. It narrows what counts as a carve-out:
naming the revision route the canon itself sanctions — a new ADR, an
architectural session — is not one. It is **post-hoc and labelled post-hoc**. Two
controls bound it: it was applied to a **fresh blind re-grade of C1 and C2 only**,
and the before-arm run that RULING 1 locked as FAIL was re-checked under it and
**still FAILs**, so it does not disturb the locked case. It moved ten individual
run grades, six after and four before — visible in the tally, not folded in.

**Four fabrication findings on B4**, three after and one before: runs emitting
tool-call blocks as text with invented command output, and no answer. B4 is on the
NO-FILE arm, which had **no tools** — `CLAUDE.md` was loaded in both arms, and the
`roq.sh` fact sat in the v1.53 footer before the split and in core §6 after, so the
material was in context either way. The failure mode was **emitting invented tool
calls instead of answering from loaded context**, which is a property of the test
harness rather than of the split.

### 7.2 AC1 — failed on lines, amended to bytes

**AC1-lines FAILED: 258 lines against a bound of 200**, over by 58. Recorded as a
failure, not reinterpreted. **AC1-bytes PASSED: 39,786 ≤ 40,960**, with 1,174 B of
headroom (97.1 % used). The amendment and its reasoning are at §4; the reversed
sentence is annotated in place rather than deleted.

### 7.3 Toolchain — pinned across both arms

CLI **`2.1.277`** on the before-arm and the after-arm. An auto-update to `2.1.280`
landed mid-experiment and was rolled back; auto-updates are disabled; the
after-arm runner **asserted the version at launch and would have aborted**
otherwise. §4 AC2-note-2 carries the detail.

### 7.4 What the split actually changed at launch — operator-measured

`/context` run post-merge at `76ad9a3`: **only `CLAUDE.md` is loaded at launch,
at 14.1k tokens. No rules file is loaded, and no file-size warning appears.**
Recorded as **OPERATOR-MEASURED** — a `/context` reading cannot be produced from
inside a session, so it carries the operator's word and is labelled as such.

This is the mechanism working as D9 predicted: the eight path-scoped rule files
and two skills are present in the tree and absent from the launch context.

### 7.5 Summary — stated at the strength the evidence supports

> **No measured harm, launch load in bytes down 88 % (327,949 → 39,786 B), and the
> gains are not attributable to the split.**

The three clauses are deliberately unequal in strength. *No measured harm* is what
AC2 establishes: no regression across 15 prompts, 90 runs. *The byte reduction* is
arithmetic on `CLAUDE.md` at `6bba0ce` against `76ad9a3`, the least contestable
claim here — and it is stated **in bytes**, because the pre-split launch load was
never measured in tokens and a token figure would be an inference dressed as a
measurement. **The two gains, B2 and C1, are NOT claimed as effects of the split**
— n=2, one of them the prompt RULING 3's post-hoc re-grade moved, and nothing in
the design isolates the split from run-to-run variance. A split that removes
88 % of the launch load without breaking anything is the result; a split that
makes the model better at its own canon is a claim this experiment cannot support
and does not make.

### 7.6 S87 amendment (2026-10-01) — the launch load measured in TOKENS, and the warning as a state change

§7.4 and §7.5 above are **unchanged**. They recorded the launch load **in bytes**,
deliberately, because *"the pre-split launch load was never measured in tokens and a
token figure would be an inference dressed as a measurement."* It has since been
measured. Source: `docs/research/s87_routing/ws2_6_context_measure.md`,
operator-read `/context`, working directory / CLI / model held constant across both
readings.

| reading | commit | state | `CLAUDE.md` | over-limit warning |
|---|---|---|---|---|
| before | `6bba0ce` | pre-split | **128.9k tokens** | **shown** — over the 150.0k-char limit (318.5k chars) |
| after | `35588a2` | post-pull | **14.3k tokens** | **absent** |

**Token reduction 88.91%**, computed from the two readings. Corroborated from a
different instrument — the blobs git holds — at **327949 → 40073 bytes,
87.78%**: same order, independent of the tool.

**The warning is the part that is not a matter of degree.** Before the split the file
was over the character limit and the tool said so; after it, the warning is absent.
That is a **state change**, not a smaller number, and it is what identifies the "150k"
of ADR-028 §2.1 and ADR-028 §6 item 3 as a **character** limit.

**The S86 figure, and the growth since.** §7.4 recorded **14.1k tokens at
`76ad9a3`**, the split commit. The reading above is 14.3k at `35588a2`, the S86
**doc-close** commit — so the file **grew at the doc-close**, by 1.42%, when the
v1.58 footer and the S86 settled-decision rows were written into it. Measured against
the S86 figure the reduction would read 89.06 %; **88.91% is the honest one**,
because that is the file a session loads today. The gap between the two is the
doc-close cost of one session, and it is the quantity to watch: **a split that is
re-filled at every doc-close returns to the limit on its own.**

**Not claimed.** The char figure in the warning (318.5k) does **not** reconcile
with the file's own char count at `6bba0ce`, and no attempt is made to make it — the
tool's char accounting is its own. Both readings are **n=1**, one observer, one box;
nothing here establishes run-to-run stability of the `/context` figure itself. And this
is a **size** reading only: it says nothing about behaviour, which is AC2's job.
