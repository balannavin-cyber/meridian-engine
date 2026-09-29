# ADR-027 — Doc-close drafting agent, mechanical verifier, and operator diff gate

> **STATUS: DRAFT — NOT FILED.** Lives in `docs/research/s85_rag/`,
> deliberately outside `docs/decisions/`. **No row in the Decision Index's own
> Index table** — that table takes accepted ADRs only; its ID is **RESERVED**
> in that document's Pending-ADRs table (S85). Authorises nothing. Filing
> requires an operator decision plus the §9 rulings.
>
> **ID provenance:** `ADR-027` confirmed free S85 by the reserved-row method —
> no `ADR-027` file at HEAD `59c9349`, no mention anywhere in `docs/` or
> `CLAUDE.md`, and the Decision Index reserved row `ADR-026+ | Next-free | — |
> Available` is a catch-all covering 026 and upward. Cited by row content, not
> line number, per the S84 line-citation rule. Re-confirm at filing time.
>
> ## DEPENDS ON ADR-026
>
> **This ADR cannot be filed, accepted, or built before ADR-026 is accepted and
> its A1 criterion passes.** It consumes ADR-026's retrieval layer and
> **inherits ADR-026 §6's write boundary verbatim** (reproduced as §6 below).
> ADR-026 §6 is the canonical text; if the two ever diverge, **ADR-026 governs.**
> The dependency is stated this prominently for one reason: §6 is what makes a
> drafting agent safe, and **this ADR must never ship against a weaker
> boundary.** ADR-026 stands alone and is useful alone. This one does not.

---

## 1. Status

PROPOSED, and **blocked on ADR-026**. Drafted S85 (2026-09-29) from the
measure-only inventory in `inventory.md`, against corpus HEAD `59c9349`.

---

## 2. Context

Each doc-close propagates one session's findings into an **8-file invariant
core** plus a conditional tail (measured S82–S84, `inventory.md` §5c). The same
finding is written eight times in eight registers' voices. CLAUDE.md records the
cost directly: TD-S73-NEW-8 stays OPEN because CLAUDE.md alone is 327 KB against
a 150 KB ceiling, and its stated cause is *"the eight-fold duplication of each
session's findings across this file and seven registers."*

The failure modes are also on record, and they are why this ADR is about
**verification** at least as much as automation:

- **S80** — *"All three files clean"* printed as a string literal rather than
  computed from per-file results, immediately after all three printed *Skipping*.
- **S81** — an expected `comment_len` of 4637 published against a file literal of
  **5632**; the artefact was correct the whole time and the number came from
  nowhere. Same session: a "0 remaining contradictions" claim written into a
  commit message *before* the check ran, which the check then contradicted.
- **S83** — five figures in one COMMENT draft wrong because they were read off
  rendered tables rather than from files.
- **S84** — filing one entry shifted three line citations by **+16 inside its own
  entry**, and a fourth came to resolve to `TD-S81-NEW-11`'s heading — a
  different entry that reads perfectly plausibly.

Every one is a drafting error a mechanical check catches, and **none were caught
by review.** That asymmetry — cheap mechanical checks catching what careful
reading does not — is the case for this pipeline. It is equally the case for the
pipeline never writing unsupervised, which is what §6 enforces.

Rule 0 governs: a check that cannot fail for the reason it names is not a check.

---

## 3. Decision

**D4 — Drafting agent emits a patch, never a write.**

Consumes a session transcript (per the §5 input contract) plus ADR-026 retrieval
context, and emits **a proposed splice set** — never a file write, never a
commit. Output is a byte-level splice script per Doc Protocol v4 Rule 7 (splices
with fail-loud assertions, not full-file rewrites), because every target register
is newest-first and prepend-only, and because on a 662 KB file through an agent a
full rewrite *is* the truncation risk TD-S73-NEW-8 records.

Rules inherited verbatim from existing canon:

- Every file-entry gets **its own** idempotency gate, and the closing summary is
  **computed from per-file results, never a literal** (S80).
- Anchors are built from a `repr()` dump of on-disk bytes, never from rendered,
  relayed or console output (S71).
- **No EOL normalisation** on document edits; match each insert to its local
  region — mixed-EOL files exist and normalising is a silent rewrite.
- Read bytes with `decode('utf-8-sig')`; write with `write_bytes()`.
- Generated cross-references cite **entry ID + row name**, never line numbers,
  for any newest-first register (S84 §D.40.6).
- Every generated figure carries a machine-runnable provenance handle (see V2).

**D5 — Mechanical verifier that must be able to fail.**

Runs before the operator sees anything. Checks enumerated in §6.1, each with its
failure condition stated. A verifier that cannot fail is documentation, not
verification. The verifier runs **after** the splice is composed and **against
the written file**, not at compose time — the S84 line-citation defect is correct
at compose time and wrong only after the write, so a dry run cannot catch that
class.

**D6 — Operator diff approval is the only write gate.**

Nothing reaches a register, a commit, or project knowledge without the operator
approving a rendered diff. The pipeline has no autonomous write path to `docs/`
at any stage, in any mode, including a "trusted" one. **There is no `--yes`
flag.** Note that MERDIAN's own convention runs the other way — a script exposing
only `--dry-run` is opt-*out* and writes by default, and roughly 60 scripts at
repo root do exactly that (S72). This pipeline is opt-**in** and inverts that
local convention deliberately.

**D7 — The pipeline never allocates identifiers.**

TD / ADR / ENH / CASE / §D IDs are **operator-allocated**. The draft either uses
an ID the operator supplied, or marks the slot `PROPOSED-ID` for allocation.
Monotonic-no-reuse (Doc Protocol Rule 5) is exactly the invariant an agent would
plausibly violate, and S74 found a next-free marker naming an already-consumed
ID even under human maintenance. Enforced as V5.

---

## 4. Scope

**In scope:** the 8-file invariant core plus conditional tail as drafting
targets; the verifier; the operator gate; S82/S83/S84 as replay ground truth.

**Explicitly out of scope:**

| Excluded | Reason |
|---|---|
| `sql/` files | Build output, not doc-close prose. **64.2%** of S83's insertions (1,049 of 1,635) — scoring them measures SQL generation (`inventory.md` §5b) |
| Production `.py` at repo root | Not documentation; a doc-close pipeline must not touch code |
| 27 `.docx` | Generated artifacts |
| S81 and earlier as replay targets | S81's doc-close is **~12 commits**, not one (`inventory.md` §5a) — unusable without reassembly |
| ID allocation | D7 |
| Commit / push / PK upload | Operator actions; the pipeline stops at an approved diff |
| Schema / extension / grant / DDL creation | Operator actions — §6 |
| Retrieval, chunking, the `rag` index | **ADR-026** |

**Not authorised by this ADR:** no change to any register's format; no change to
Doc Protocol v4; no widening of D6 — trusting D4 beyond diff-approval requires a
new decision, not an amendment to this one.

---

## 5. Input contract — transcript → session attribution

**Attribution is by entry `timestamp`, bounded by doc-close commit times. It is
never by marker count.** This is a hard input contract, not a heuristic
preference, and both halves are measured in `inventory.md` §1.

**Why marker counting is refused.** CLAUDE.md is injected into every session's
context and names every prior session, so an S80 transcript legitimately carries
`S79:1669` — quoted history, not session identity. Marker argmax is
*suggestive only*. Selecting a session's transcript content by marker frequency
would be the S83 defect in a new place: reading a figure off a rendered surface
instead of measuring the thing.

**Why file boundaries are refused.** There is no 1:1 session↔file map in either
direction. `0131f83d` (10.3 MB) spans S81 + S82 + S83; S84 spans three files;
`c972d318` spans four calendar days (2026-09-25 → 09-29). Any "one transcript,
one doc-close" assumption is false at the input.

**The contract.** For target session *N*:

1. Bound the window by commit times: lower = the doc-close commit of session
   *N−1*; upper = the doc-close commit of session *N* (or `now()` for a live
   session).
2. Select `user` / `assistant` entries whose `timestamp` falls in that window,
   **across all `~/.claude/projects/*/` slugs** — a session's work may be split
   across launch-cwd slugs, and it is (S82 spans `4b3bff6f` and `0131f83d`).
3. Ignore harness entry types: `mode`, `permission-mode`, `bridge-session`,
   `last-prompt`, `cost-state`, `file-history-snapshot`, `file-history-delta`,
   `atis-latch`, `ai-title`, `queue-operation`.
4. Report the entry count and byte span actually selected. **If the window
   selects zero entries, abort rather than widen it** — a silently widened window
   attributes another session's findings to this one, and the output would read
   plausibly.

Enforced as V0 in §6.1.

---

## 6. Write boundary — INHERITED VERBATIM FROM ADR-026 §6

> **ADR-026 §6 is the canonical text. It is reproduced below unchanged and may
> not be weakened here. If the two texts ever diverge, ADR-026 governs.** This
> ADR's entire safety argument rests on it.

**The only mutable surface is rows in pre-existing `rag` tables.**

| Surface | Access |
|---|---|
| **Rows** in pre-existing `rag.*` tables | Pipeline: SELECT + INSERT / UPDATE / DELETE **of rows only** |
| `rag` **schema, extension, tables, indexes, constraints, grants — all DDL** | **Operator action. The pipeline never issues DDL.** |
| Every other DB relation | Pipeline: READ ONLY, via `merdian_ro` / `bin/roq.sh` |
| `docs/`, `CLAUDE.md`, `sql/` | **NO WRITE.** ADR-027's drafting stage emits a proposed diff only |
| `~/meridian-engine` (production tree) | **NO ACCESS of any kind** |
| git commit / push | Operator only |
| Project knowledge upload | Operator only (CLAUDE.md Rule 12) |

**Consequences of the rows-only rule.** `CREATE EXTENSION vector`, `CREATE
SCHEMA rag`, every `CREATE TABLE`, every index, and every `REVOKE`/`ALTER
DEFAULT PRIVILEGES` in ADR-026 §5.1 are executed by the operator from the Supabase
editor, from a committed file under `sql/`. The pipeline finds the tables
already present and fails loudly if they are not — **it never self-provisions**,
because a pipeline that can create its own tables can also create them with
default grants, which is precisely the S39 mechanism ADR-026 §5.1 exists to close.

The pipeline therefore needs a **row-writable role distinct from `merdian_ro`**
(e.g. `merdian_rag_rw`) holding INSERT/SELECT/UPDATE/DELETE on `rag.*` tables
only, with no DDL, no rights outside `rag`, and no membership in any role that
has them. Creating that role and its grants is an operator action, like all
other DDL.

**On the production tree.** CLAUDE.md records the S80 cost of ambiguity here:
two patch scripts ran against `~/meridian-engine` before an operator instruction
corrected it, and the deploy-direction inversion recorded at `capture_s74.md`
§7.2 has stood unratified for eight consecutive sessions. This pipeline hardcodes `~/meridian-cc` as its repo
root and treats `~/meridian-engine` as non-existent. It does not resolve the
inversion — that is an ADR-006 amendment and out of scope — it declines to
depend on it.

### 6.0 One table added by this ADR

`rag.replay_run` — created by **operator DDL** like every other table, and
written rows-only by the pipeline:

```
rag.replay_run
  run_id         uuid primary key
  target_session text not null               -- 'S82' | 'S83' | 'S84'
  target_commit  text not null
  snapshot_id    uuid not null references rag.corpus_snapshot(snapshot_id)
  metric_version text not null               -- frozen before first scoring
  scored_at      timestamptz not null default now()
  result         jsonb not null
```

### 6.1 Verifier checks — each with its failure condition

Rule 0 compliance: for each check, what makes it fail, and would a real defect
produce exactly that?

| # | Check | Fails when | Run by |
|---|---|---|---|
| **V0** | Transcript window per §5 selects ≥ 1 entry; entry count and byte span reported; window never widened on empty | A misattributed or silently widened window — the output would read plausibly | pipeline |
| **V1** | Every cited entry ID resolves to an existing heading in the target file **at HEAD** | A fabricated or mistyped ID — the S84 defect, where a stale citation landed on a *different plausible* entry and nothing signalled it | pipeline |
| **V2** | Every numeric figure in generated prose is reproduced by re-running its stated provenance handle | A figure recalled rather than computed: S81's 4637-vs-5632, S83's five table-read figures | pipeline |
| **V3** | Splice anchors match on-disk bytes exactly, count **== 1** per anchor | Anchor drift, or an already-applied splice — distinguishes "correct document" from "failed edit", which S80 could not | pipeline |
| **V4** | Byte-delta assertion: post-splice size **==** pre + inserted, per file | A silent full-file rewrite or EOL normalisation | pipeline |
| **V5** | **Every ID in the draft is operator-supplied, or marked `PROPOSED-ID` for operator allocation; zero collisions with existing IDs** | The agent inventing `TD-S85-NEW-3`, or a `PROPOSED-ID` slot colliding with an ID already on disk. **Enforces D7 — the pipeline allocates nothing** | pipeline |
| **V6** | Emitted file set ⊆ {invariant core ∪ conditional tail}, and each tail file's inclusion is justified by a stated trigger | Touching `Deployment_Topology` with no topology change — the "NOT updated" claim S80 had to correct | pipeline |
| **V7** | Counts in summary prose (`TDs_NEW=N`) are **derived from the headings**, never passed in or incremented by hand | The CLAUDE.md footer convention; S81 explicitly derives | pipeline |
| **V8** | `anon` has zero privileges on `rag.*`, tested via the anon path in a **single-execution** role-scoped query selecting `current_user` beside the counts | S39's regression shape, live for 42 sessions while the register read "remediated" | **OPERATOR — not the pipeline** |
| **V9** | **PRECONDITION — snapshot is 0 doc-commits behind HEAD.** `git rev-list --count HEAD ^<snapshot.git_sha> -- docs CLAUDE.md` **must be 0**, or drafting **refuses to run** (ADR-026 D3 drafting floor) | The snapshot is even **one** doc-commit behind, so the draft would be composed against a register that has already moved — the stale-context failure, and the S84 shape where content correct at compose time is wrong after the write | pipeline |

**V9 runs FIRST, before V0–V8, despite being numbered last.** Ordering is not
numbering. It is appended rather than inserted as a new V0 because ADR-026 §5.1
cites **V8 by number**, and renumbering would silently redirect that citation —
the same citation-decay class as the S84 defect this verifier exists to catch.
Numbers are allocated monotonically here for exactly the reason Doc Protocol
Rule 5 allocates IDs that way. V9 is a **precondition**: it gates whether
drafting happens at all, so it cannot be satisfied by anything V0–V8 check, and
they cannot compensate for its failure.

**V8 is an operator check and is labelled as one.** It cannot be a pipeline
check: `merdian_ro` cannot `SET ROLE anon` (`permission denied to set role
"anon"`), so it runs as postgres in the Supabase editor, and `bin/roq.sh` is not
a substitute. The check itself and its single-execution form are specified in
**ADR-026 §5.1**; it appears here only so the verifier's coverage is complete and
the split in responsibility is explicit rather than assumed.

**V2 is the highest-yield and highest-cost check.** It requires D4 to emit a
machine-runnable provenance handle for every number. **If a figure has no
provenance handle, the verifier rejects the draft rather than passing the figure
through** — an unverifiable number is a failure, not an exemption.

---

## 7. Pre-registered acceptance criteria

Pre-registered per ADR-009 discipline and Rule 0's third clause: *an expected
value obtained by running the thing is not an assertion.* Thresholds and metric
definitions must be set by the operator **before** the first measurement.
Adjusting either until it passes replaces the belief with the observation, and
the criterion then asserts nothing.

### A2 — Doc-close replay agreement

**Instrument:** replay S82 (`bb374ae`, 12 files, +1481/−1202), S83 (`18c2fb8`,
16 files, +1635/−38) and S84 (`e554a56`, 8 files, +251/−95) from their
transcripts at each parent commit, and compare generated splices to actual.
One `rag.replay_run` row per scoring, with `metric_version` frozen first.

**Scored surface — fixed before measuring:**

- **`sql/` excluded.** 1,049 of S83's 1,635 insertions (64.2%) are the three
  `sql/` files; scoring them measures SQL authoring, not doc-close prose.
  Leaves ~586 prose insertions for S83.
- **File-set agreement is reported but NOT scoring.** The 8-file invariant core
  is emitted unconditionally and would score ~100% for free — and that core is
  *exactly* S84's complete file list. Gaming-resistance is the reason.
- **Scoring is on content, per target file:** did the generated entry capture the
  same finding, with the same ID, the same status, and figures matching the
  actual commit's figures?

**Metric definition: TBD — operator ruling (§9), and the definition is as much a
ruling as the number.** Candidate shape: a per-file three-way label
(AGREES / DIVERGES / MISSES) adjudicated against the real commit, with a stated
minimum on the invariant core specifically. **A single scalar over all files is
not acceptable** — it lets a strong one-line `session_log.md` entry mask a wrong
`tech_debt.md` entry, and those are not equally consequential.

**Threshold: TBD — operator ruling (§9).**

**Failure condition:** below threshold → **D4 is not accepted for autonomous
drafting.** The pipeline is retained as retrieval-only under ADR-026, which is
independently useful and carries none of the drafting risk.

### A3 — Verifier efficacy (mandatory, threshold NOT negotiable)

**Instrument:** inject the six known historical defects from §2 as synthetic
drafts — S80's literal summary, S81's unmeasured 4637, S83's five misread
figures, S84's +16 citation shift, plus an ID collision (V5) and an anon grant
(V8, operator-run).

**Threshold: 6 of 6 caught. Not TBD, and not for operator ruling.** A verifier
that misses a defect this project has already made twice is not a verifier. If
V0–V8 cannot catch all six, the missing check is authored before anything ships.

**Failure condition:** any miss → that check is **recorded as mis-specified and
never loosened.** S83's four mis-specified gates all stand failed, with the
builds they gated shipped on separately pre-registered replacements. Same
discipline.

### Ordering

A1 (ADR-026) must pass before A2 is attempted. **A3 must pass before A2 is
scored** — scoring replay agreement with a verifier of unknown efficacy measures
the draft and the verifier together and can distinguish neither.

---

## 8. Consequences

**If accepted and A2 + A3 pass:** doc-close drafting cost falls, and every
generated figure carries machine-checked provenance — stronger than the current
human-review baseline, which demonstrably missed all six §2 defects.

**If A3 passes and A2 fails:** the retrieval layer ships alone under ADR-026 and
this ADR does not. **This is a legitimate outcome, not a failure** — ADR-025 D1's
shape, where a recorded disposition counts as progress and stopping early is a
*result*. Stated plainly so a later reader cannot mistake the hold for the lapse
it would otherwise resemble.

**Costs and risks accepted:**

- **A verified draft is still a draft.** V1–V7 check form, provenance and
  arithmetic. They cannot check whether the finding is the *right* finding, or
  whether a session's real lesson was captured. D6 is not a formality and must
  not decay into one.
- **Automation bias is the live risk.** A pipeline that passes its verifier nine
  times trains the operator to approve the tenth. No check here mitigates that;
  it is a property of the workflow and is recorded rather than solved.
- This ADR makes the eight-fold duplication **cheaper to execute**, which is
  **not the same as fixing TD-S73-NEW-8** and must not be recorded as if it
  were. Cheaper duplication may make the underlying problem *less* likely to get
  fixed.
- Transcripts are 107 MiB across 52 files and contain operator instructions,
  infrastructure detail and incident narrative. Whatever consumes them inherits
  that exposure; no secrets are present but the surface is not trivial.

**What this ADR does not decide:** the A2 metric definition or threshold; whether
D4 is ever trusted beyond diff-approval (it is not, under this ADR); the
deploy-direction inversion at `capture_s74.md` §7.2; TD-S73-NEW-8's underlying
duplication.

---

## 9. Open items requiring operator ruling before filing

1. **A2 metric definition** — the per-file label scheme, how AGREES /
   DIVERGES / MISSES is adjudicated, and how the invariant core is weighted
   separately from the conditional tail. **The definition is the harder half of
   this ruling**, and it must be frozen as `metric_version` before the first
   scoring.
2. **A2 threshold** — the minimum, stated against that definition, including any
   separate minimum on the invariant core.
3. **Confirm the ID-allocation bar** — that D7 / V5 is the intended posture, i.e.
   the pipeline marks `PROPOSED-ID` and never allocates a TD / ADR / ENH / CASE /
   §D identifier itself.
4. **Confirm `ADR-027` still free** at filing time by the reserved-row method,
   and that ADR-026 is filed first — this ADR is meaningless without it.

**Deliberately NOT listed here:** nothing from **ADR-026 §9**. Duplicating an
item would create two places to rule one question, and as of S85 that list holds
only a filing-time hygiene check — every substantive ADR-026 decision is ruled.

**Three ADR-026 rulings have landed and are open nowhere:**

- **A1 thresholds** — ADR-026 §7: ID-bearing recall@5 = 100%, prose-only
  recall@20 ≥ 60% / recall@5 ≥ 40%, ≥ 20 questions per class.
- **Staleness floors** — ADR-026 D3: interactive absent when
  `age_doc_commits > 3` OR `age_days >= 2`; **drafting absent when
  `age_doc_commits > 0`**, enforced here as **V9**.
- **Embedding model** — ADR-026 D1: `bge-small-en-v1.5`, 384-dim, ONNX, local on
  MERDIAN EC2, execution bounded by the ADR-026 §8.1 guardrails G1–G8 and gated
  on tests T1–T4.

All three still gate this ADR. They are settled, not waived.
