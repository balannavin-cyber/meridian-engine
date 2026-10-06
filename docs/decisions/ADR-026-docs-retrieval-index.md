# ADR-026 — Docs retrieval index: chunking, pgvector store, hybrid retrieval

> **STATUS: ACCEPTED — Session 85, 2026-09-29.** Filed to `docs/decisions/`
> by operator decision, with the §7 A1 thresholds, the D3 staleness floors and
> the D1 embedding model all RULED at S85, and **G3c RULED S85 — Option 1,
> no IAM grant** (§8.1). **Three obligations remain owed BEFORE the first real
> embedding run**, listed at §9: **T1–T4 must pass**, **`completed_at` must be
> added to `rag.corpus_snapshot`**, and **the instance's burst mode must be
> established**.
>
> **ID provenance:** `ADR-026` taken from the Decision Index reserved row
> `ADR-026+ | Next-free | — | Available` (advanced from `ADR-025+` at the S80
> doc-close). Cited by row content, not line number, per the S84 line-citation
> rule. Confirm still free at filing time — S74 found a next-free marker naming
> a consumed ID.
>
> **Companion:** ADR-027 (drafting agent + verifier + operator diff gate)
> **depends on this ADR** and inherits its §6 write boundary verbatim. This ADR
> stands alone and is useful alone; ADR-027 is not.

---

## 1. Status

PROPOSED. Drafted S85 (2026-09-29) from the measure-only inventory in
`inventory.md`, against corpus HEAD `59c9349`.

---

## 2. Context

Doc-close and register lookup both require answering "what does the record
already say about X?" across 138 text files and 7,432,679 bytes, of which nine
files hold 65%. The corpus is densely identifier-anchored — ~6,300
heading-anchored entry IDs (`TD-*` 2,965 · `ENH-N` 1,583 · `ADR-NNN` 1,574 ·
`§D.N.N` 174 · `CASE-*` 21).

CLAUDE.md records the cost of *not* having retrieval, repeatedly and by name.
S70's most expensive failure was reasoning about MERIDIAN's history without
reading it: TD-NEW-7 was diagnosed at S28 with the fix fully designed, carried
~40 sessions, produced a third outage, and was then re-derived from scratch
while `project_knowledge_search` was never called. S66 walked six wrong theories
that one read of the record would have collapsed. S74 found the session brief's
own premise measured one-of-six live.

This ADR covers **retrieval only**. It builds an index and a query path. It
writes nothing to `docs/`, drafts nothing, and decides nothing about whether an
agent may ever propose a register edit — that is ADR-027's question, and keeping
them separate is deliberate so that the useful, low-risk half can ship without
carrying the risky half's acceptance burden.

Rule 0 governs: a check that cannot fail for the reason it names is not a check.

---

## 3. Decision

**D1 — Ingest & index (read-only over git).**

Chunk the docs corpus at a pinned `git_sha` and embed into a new `rag` schema in
the existing Supabase instance using pgvector 0.8.2 (measured available,
`installed_version` empty — not installed). The index is **derived and
disposable**: droppable and rebuildable from any commit, holding no authority.
Where the index and the repo disagree, the repo is truth — the same relation
`tech_debt.md` has to a query result under CLAUDE.md Rule 3.

**Chunking design — ID-anchored and byte-budgeted.** Boundaries are placed at
heading-anchored entry IDs (markdown headings and bolded register rows), and
each chunk carries a byte budget so an oversized entry is split rather than
truncated. Three sub-rules, each earned from a measurement in `inventory.md` §2:

- **Chunks split *within* lines for the six paragraph-per-line files**, where one
  line is one whole entry and exceeds any sane chunk: `session_log.md` (2,665
  B/line, 21 lines), `CLAUDE_history.md` (2,516 B/line, 57 lines),
  `MERDIAN_Decision_Index.md` (736), `session_log_history.md` (523),
  `MERDIAN_Assumption_Register.md` (326), `CLAUDE.md` (280). A line-window
  chunker applied to this corpus emits chunks varying by two orders of
  magnitude. **Line count is not a chunkability proxy anywhere here.**
- **`merdian_reference.json` is chunked by key path**, not by markdown structure
  — 610,151 bytes, 2,194 inline IDs, zero headings. Its chunk identity is the
  JSON key path (e.g. `tables.gex_strike_snapshots`), and that path is stored in
  `heading_path`.
- Every chunk records exact `byte_start`/`byte_end` into the blob at `git_sha`,
  so any chunk is re-derivable from the commit and no chunk is authoritative on
  its own content.

**On the 512-token figure:** the ~4,270-chunk and 6.6 MB-index numbers in
`inventory.md` §4 are an **estimate of corpus size only** — computed at an
assumed 4.0 chars/token because `tiktoken` is absent from this host. They size
the store and the embedding bill. They are **not the chunking design** and must
not be read as fixing a chunk length; the design is the ID-anchored, byte-budgeted
rule above.

**Embedding model — RULED S85: `bge-small-en-v1.5`, 384-dim, ONNX, run locally
on MERIDIAN EC2.** No document text leaves the host. This fixes `embed_dim = 384`
and confirms the `vector(384)` column in §5 as a ruling rather than a
placeholder; `embed_model` records the exact model id and revision so a snapshot
built under a different model is distinguishable, and `corpus_snapshot`'s unique
key already treats a model change as a new snapshot rather than a silent
re-embed. **ONNX, not torch** — the distinction is the whole reason local is
viable: torch's peak brushes this box's 1,125 MB ceiling with no swap, while
onnxruntime does not (`inventory.md` §4). Execution is bounded by the §8.1
guardrails, which are a condition of this ruling and not advice.

**D2 — Retrieval (hybrid, ID-first).**

Lexical entry-ID match UNIONed with vector similarity, ID match ranked first.
Non-negotiable given the ~6,300 anchored IDs: a question about `TD-S82-NEW-4`
must retrieve *that* entry by exact ID, never by embedding proximity to
neighbouring entries. The S84 defect is the argument — a stale citation that
resolved to `TD-S81-NEW-11`'s heading read perfectly plausibly, and **a wrong
retrieval that lands on other valid content is worse than one that lands on
nothing**, because nothing signals the error.

**D3 — Staleness fails to absent, never to stale. Two floors, RULED S85.**

Every retrieval response carries its snapshot's `git_sha` and its age in
**doc-commits** and days. Past the floor for its consumer, the retrieval path
**returns absent with a stated reason rather than stale content**.

**Staleness is measured in doc-commits, not commits.** A doc-commit is a commit
touching `docs/` or `CLAUDE.md`. **Code-only commits do not make the doc index
stale** — the index is of documents, and a `compute_gamma_metrics_local.py` patch
changes nothing it holds. Exact measurement, so the count is reproducible rather
than described:

```
git -C <repo> rev-list --count HEAD ^<snapshot.git_sha> -- docs CLAUDE.md
```

`sql/` is deliberately not in that pathspec, consistent with §4 excluding it from
the corpus: a file the index never read cannot make the index stale.

**Two consumers, two floors** — because ADR-023 D1's lesson is that a floor is
calibrated against the **consumer's** cadence, never the writer's, and these two
consumers have nothing in common:

| Consumer | Absent when | Behaviour |
|---|---|---|
| **Interactive retrieval** (a session asking the record a question) | `age_doc_commits > 3` **OR** `age_days >= 2` | Return absent with a stated reason |
| **ADR-027 drafting** | `age_doc_commits > 0` — snapshot `git_sha` must equal HEAD for `docs/` + `CLAUDE.md` | **Refuse to run** |

**The comparison operators are part of the ruling and are stated here so the
text and the tests cannot disagree.** Read them literally:

- **3 doc-commits behind still answers; 4 is absent.** The floor is *past* 3, so
  the predicate is `>`, not `>=`.
- **Just under 2 days still answers; exactly 2 days is absent.** That limb is
  `>=`, not `>`.
- **The two limbs are OR'd**, evaluated independently — whichever trips first.
- **The limbs use different operators, deliberately.** `>` on commits and `>=` on
  days is asymmetric and will look like a typo to a later reader; it is not, and
  is recorded as intentional so it does not get "corrected" into symmetry. A1-secondary
  tests both boundaries from both sides, so a silent change to either would fail.

**Why drafting is zero and interactive is three.** An interactive answer is read
by a session that can see the stated age and go read the file; being three
doc-commits behind degrades an answer. Drafting *writes into* those same files,
so a single missed doc-commit means composing an entry against a register that
has already moved — which is **the stale-context failure this floor exists to
prevent**, and it is also precisely the S84 shape, where content correct at
compose time was wrong after the write. A near-miss there is not a degraded
answer; it is a splice authored against the wrong base. Enforced as ADR-027 V9.

**Re-index is event-triggered, never on a timer.** It runs after every doc-close
commit, and on demand. A timer would re-index on a cadence unrelated to when
documents actually change — burning embedding calls on code-only days while
still being able to lag a doc-close by the length of its own interval. The
trigger is the event that invalidates the snapshot, not the clock.

This is ADR-023's rule applied to a new read path, and the failure mode it
prevents is ADR-001's family: retrieval against a three-session-old snapshot
returns plausible, well-formed, wrong context. S71 is the precedent for why
warn-only is insufficient — a warn-only recency floor printed `STALE:` to stderr
and **returned the stale data anyway**. A staleness signal that reaches only a
log is not a floor.

---

## 4. Scope

**In scope:** the 138 text files of the docs corpus (`docs/` + `CLAUDE.md`) as
retrieval substrate; the `rag` schema; the query path.

**Explicitly out of scope:**

| Excluded | Reason |
|---|---|
| 27 `.docx` under `masters/` + `appendices/` (1,094,035 B) | Generated artifacts; CLAUDE.md forbids loading them as working documents |
| `sql/` and production `.py` at repo root | Not documentation |
| `.env`, any credential | Rule 19. Absent from corpus (gitignored); must remain absent from the index |
| Any write to `docs/` | Not this ADR, and not ADR-027 either — see §6 |
| Drafting, verification, filing | ADR-027 |
| Schema/extension/grant creation | Operator action — see §6 |

**Not authorised by this ADR:** no change to any register's format; no change to
Doc Protocol v4; no agent-proposed register edit of any kind.

---

## 5. Schema

New schema `rag`. Additive: **no existing table, view, function or grant is
altered.** All DDL below is an **operator action** (§6).

```
rag.corpus_snapshot
  snapshot_id     uuid primary key
  git_sha         text not null              -- the commit indexed, pinned
  taken_at        timestamptz not null default now()
  n_files         int  not null
  n_chunks        int  not null
  embed_model     text not null              -- provider + exact model id
  embed_dim       int  not null
  chunker_version text not null              -- bump invalidates the snapshot
  unique (git_sha, embed_model, chunker_version)

rag.doc_chunk
  chunk_id     bigserial primary key
  snapshot_id  uuid not null references rag.corpus_snapshot(snapshot_id) on delete cascade
  path         text not null                 -- repo-relative
  chunk_index  int  not null
  byte_start   int  not null                 -- exact offsets into the blob at git_sha,
  byte_end     int  not null                 --   so any chunk is re-derivable
  heading_path text                          -- markdown heading path, or JSON key path
  entry_ids    text[] not null default '{}'  -- anchored IDs: the lexical key for D2
  token_est    int
  content      text not null
  embedding    vector(384)                   -- dim pinned to embed_model
  unique (snapshot_id, path, chunk_index)

rag.retrieval_eval          -- §7 A1: frozen question set, authored before measuring
  query_id     text primary key
  question     text not null
  expect_ids   text[] not null               -- ground-truth entry IDs
  expect_paths text[] not null
  id_bearing   boolean not null              -- A1 reports the two classes separately
  authored_at  timestamptz not null
  frozen       boolean not null default false
```

**Indexes:** HNSW on `doc_chunk.embedding` (`vector_cosine_ops`); GIN on
`entry_ids`; btree on `(snapshot_id, path)`.

`rag.replay_run` is defined in **ADR-027**, which owns replay scoring.

**Sizing is a non-issue.** At the §4 estimate a float32 index is 6.6 MB at
384-dim / 13.1 MB at 768-dim, over ~4,270 rows. No infrastructure beyond the
existing instance is implied. ADR-021's lesson applies to any view built over
these tables: scope to the snapshot the consumer reads, or the cost curve
returns at larger N.

### 5.1 Security posture — explicit, because this is where S81 bled

`anon` gets **nothing**. Not SELECT.

Per `CASE-2026-09-22-anon-privilege-exposure`, **`REVOKE` alone reproduces S39**:
S39 revoked on thirteen surfaces, left Supabase's DEFAULT PRIVILEGES untouched,
and every object created afterwards came up with ALL again — `v_max_pain_by_strike`
(S40) measured at all seven privileges at S81, while D.21.1 read "remediated" for
42 sessions. The remediation that holds is at the mechanism:

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA rag REVOKE ALL ON TABLES FROM anon, authenticated;
REVOKE ALL ON ALL TABLES IN SCHEMA rag FROM anon, authenticated;
REVOKE USAGE ON SCHEMA rag FROM anon, authenticated;
```

The `rag` schema is **not** added to PostgREST's exposed schemas. And the second
half of that CASE applies: D.21.2's *"the boundary is the RLS policy + GRANT
pair"* was **false for ~100 tables with RLS off**, where the GRANT alone is the
boundary. So `rag` tables get RLS enabled **and** no grant — belt and braces,
with the absent grant as the real guarantee.

The corollary is stated because it is the tempting wrong fix: when an ingest
script later fails on a missing key, **supply the key — never restore the grant.**

**`COMMENT ON` and `GRANT` ship as live statements** in the `sql/` file, never as
commentary. TD-S81-NEW-5: three S79 views had COMMENTs present in `sql/` and
absent live, and GRANTs commented out in `sql/` while present live — a rebuild
from that file would have produced three panels at HTTP 200 with **zero rows**.

**Verification is by the anon path, not by object existence** — TD-S81-NEW-5
records ENH-126 shipping live and anon-unreadable, and only an anon-path test
could tell the two apart. The canonical form is a **single-execution**
role-scoped query selecting `current_user` beside the counts (S84 §D.40.1),
because the Supabase editor opens a new session per run and a `SET ROLE` in one
run does not survive into the next:

```sql
BEGIN; SET LOCAL ROLE anon;
SELECT current_user AS role_now, count(*) FROM rag.doc_chunk;  -- must ERROR
COMMIT;
```

**This is an OPERATOR check, not a pipeline check.** `merdian_ro` cannot run it
at all — `permission denied to set role "anon"` — so it belongs to the editor
under the postgres role, and `bin/roq.sh` is not a substitute. Recorded as V8 in
ADR-027 §6.1 and labelled there as operator-run.

---

## 6. Write boundary

> **This section is the canonical write boundary for both ADRs.** ADR-027 §6
> reproduces it verbatim and may not weaken it. If the two texts ever diverge,
> **this text governs.**

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

---

## 7. Pre-registered acceptance criterion

Pre-registered per ADR-009 discipline and Rule 0's third clause: *an expected
value obtained by running the thing is not an assertion.* **A1's thresholds were
RULED by the operator at S85 (2026-09-29), before any index exists** — not after
a first measurement, so there is no observation available to have fitted them to.
That ordering is the whole point: adjusting a threshold until it passes replaces
the belief with the observation, and the criterion then asserts nothing.

### A1 — Retrieval hit rate · THRESHOLDS RULED S85

**Instrument:** **≥ 20 questions per class** — ≥ 20 with `id_bearing = true` and
≥ 20 prose-only, ≥ 40 total — authored into `rag.retrieval_eval` and marked
`frozen = true` **before any index is built**, drawn from real doc-close
questions ("what is TD-S82-NEW-4's status?", "which ADR governs read-path
recency floors?", "what did S80 measure BUILT at?"). The per-class minimum is
itself part of the ruling: a pooled set of 40 could satisfy the total while
leaving one class at N=3, where neither threshold below would mean anything.

**Metric:** recall@k of ground-truth `expect_ids` at k = 5 and k = 20, **reported
separately** for the two classes. **Pooling them is not an acceptable
substitute** — the lexical half would mask vector-side failure.

**Thresholds — RULED (operator, S85):**

| Class | recall@5 | recall@20 |
|---|---|---|
| **ID-bearing** (`id_bearing = true`) | **= 100%** | 100% (implied) |
| **Prose-only** | **≥ 40%** | **≥ 60%** |

**Why ID-bearing is 100% and not "near-100%".** Lexical exact match is
**deterministic**. An entry ID either appears in a chunk's `entry_ids` or it does
not; there is no ranking noise to tolerate and no distribution to be unlucky
against. A miss is therefore not a shortfall to be scored — it is **positive
evidence of a chunker defect**, and it is **fixed, not tolerated**. Because the
bar is 100% at k = 5, recall@20 is necessarily 100% as well; it is reported for
completeness but is not a second, weaker bar that a k=5 failure could hide behind.

**Failure condition:** below threshold on **either** class → the retrieval layer
is not accepted, and ADR-027 does not proceed (it depends on this one). On an
ID-bearing miss the remedy is specifically the chunker, not the ranking and not
the threshold.

**What would make this check fail, stated per Rule 0:** a chunker that splits an
entry away from its ID heading — the ID in one chunk, its Status row in another —
drops that entry to zero recall on an ID-bearing query. That is a real, specific
defect and it produces exactly this failure, which is what makes 100% a testable
assertion rather than an aspiration. Two limits stated plainly: the prose-only
bars (40% / 60%) are **not** deterministic in this way and are a judgement about
useful-enough retrieval, not a proof of correctness; and A2-style content quality
is **not** tested here at all, so passing A1 says nothing about drafting.

### A1-secondary — both staleness floors fire (mandatory, no threshold)

**Both D3 floors are tested, separately, and each boundary is tested from both
sides.** Testing one floor and inferring the other is not acceptable: they are
different predicates on different consumers, and the drafting floor is the one
whose failure writes to disk. Testing only the far side of a boundary is equally
not acceptable — an implementation that returned absent *always* would pass every
absent-side arm.

**Test harness — no real repository is ever written to.** Every arm below runs
against a **throwaway git repo created under `scratch/` or a temp dir**, seeded
with synthetic `docs/*.md`, a synthetic `CLAUDE.md`, and synthetic `*.py` files.
**No arm creates a commit in `~/meridian-cc`, `~/meridian-engine`, or any real
repository** — §6 already bars the production tree, and this bars the working
clone too, because a test that commits to the repo it is measuring has changed
the thing it measures. **The clock is injected as a parameter**, never waited
out: `age_days` is supplied to the floor evaluator, so S-2a/S-2b run in
milliseconds and are deterministic rather than depending on when they are run.

| # | Arm | Setup (throwaway repo) | Assert |
|---|---|---|---|
| **S-1a** | Commit limb, near side | Snapshot, then land **3 doc-commits** | Retrieval **still answers** |
| **S-1b** | Commit limb, far side | Snapshot, then land **4 doc-commits** | Retrieval returns **absent with a stated reason** |
| **S-2a** | Day limb, near side | Snapshot, inject `age_days = 1.99`, **0 doc-commits** | Retrieval **still answers** |
| **S-2b** | Day limb, far side | Snapshot, inject `age_days = 2.0`, **0 doc-commits** | Retrieval returns **absent** — and proves the limbs are OR'd, not AND'ed |
| **S-3a** | Drafting, at zero | Snapshot, land **0 doc-commits** | Drafting **runs** |
| **S-3b** | Drafting, one behind | Snapshot, land **exactly 1 doc-commit** | Drafting **refuses to run** |
| **S-4** | Code-only control | Snapshot, land **4 commits touching only `*.py`** | Retrieval **still answers** |

**Three of these seven arms exist to stop the others being vacuous**, which is
the CAN-FIRE / CANNOT-FIRE discipline applied to this test set:

- **S-1a and S-2a** are the near sides. Without them, a floor that always
  returned absent would pass S-1b and S-2b and look correct.
- **S-3a** is the near side for drafting. Without it, a drafting stage that
  refused unconditionally would pass S-3b.
- **S-4** tests the ruling's central claim — that code-only commits do not make
  the doc index stale. It uses **4** commits, one past the commit floor, so a
  floor counting *all* commits fails here while passing S-1a, S-1b, S-2a, S-2b,
  S-3a and S-3b identically. Without S-4 the pathspec is untested.

**Failure = the floor is warn-only, measures the wrong commits, ANDs the limbs,
or has either boundary off by one.** Warn-only is the S71 defect verbatim and is
not accepted. **S-3b failing is the most consequential**: it means drafting can
run against a register that has already moved, the one failure in this ADR whose
consequence reaches `docs/`.

---

## 8. Consequences

**If accepted and A1 passes:** the record becomes queryable, and the S70-class
failure — re-deriving from scratch what the register already held — becomes
cheap to avoid rather than dependent on remembering to search.

**If A1 fails:** the chunker or the hybrid ranking is wrong and is fixed;
**the threshold is not loosened.** S83's four mis-specified gates all stand
failed, with the builds they gated shipped on separately pre-registered
replacements. Same discipline here.

**Costs and risks accepted:**
- A new schema, a new extension, and ~4,270 embedded chunks to maintain.
  Staleness against a moving HEAD is real; `corpus_snapshot` pins `git_sha` and
  D3 makes staleness fail to absent.
- The index is a **second copy of the record**, and CLAUDE.md's standing
  complaint (TD-S73-NEW-8) is that eight-fold duplication is already the
  problem. Mitigated only by the index being derived, disposable, and
  non-authoritative — it is explicitly **not** a ninth register, and must never
  be cited as a source. Citations resolve to the repo at a commit.
- **Embedding adds a compute consumer to the box that runs production cron** —
  1,125 MB available RAM, 2 vCPU, no swap. This is the principal risk this ADR
  takes on, and it is accepted only under the §8.1 guardrails. An OOM here does
  not merely fail the embedding job: the kernel may reap a capture or compute
  writer instead.
- **No document text leaves the host** (ONNX-local ruling, D1). The text-egress
  risk is closed; the RAM/CPU risk is the price.

**What this ADR does not decide:** anything about drafting or verification
(ADR-027); the deploy-direction inversion at `capture_s74.md` §7.2;
TD-S73-NEW-8's underlying duplication problem.

### 8.1 EC2 execution guardrails — conditions of the ONNX-local ruling

These are **conditions**, not recommendations. The ONNX-local ruling (D1) is
accepted *because* of them. Each carries its failure condition, per Rule 0: a
guardrail whose breach produces no observable failure is documentation.

**G1 — Dedicated virtualenv at `~/rag-venv`. Never system python.**
All packages (`onnxruntime`, tokenizers, client libs) install into that venv
only. **The system interpreter's package set must be byte-identical before and
after every install** — captured as `sha256` of `pip freeze` from the *system*
python, compared across the install.
*Fails when:* the system hash changes. That means a package landed outside the
venv, on the interpreter production writers run under, and the install is rolled
back before anything else proceeds. This is the guardrail that protects the
pipeline's own blast radius: `numpy 2.2.6` and `supabase 2.28.3` are load-bearing
for production, and a transitive upgrade of either is a production change
disguised as a tooling install.

**G2 — Run inside `systemd-run --scope -p MemoryMax=600M -p MemorySwapMax=0`,
with `OOMScoreAdjust=1000`.**
The cap is enforced by the kernel, not by the script's good intentions.
`MemorySwapMax=0` is explicit even though the box has no swap, so the guarantee
does not silently depend on that remaining true. `OOMScoreAdjust=1000` makes the
embedding process the **preferred** OOM victim.
*Fails when:* the process exceeds 600 MB — and the correct outcome is that **it**
dies, not a production writer. Absent `OOMScoreAdjust`, the kernel is free to
choose by RSS, and the largest process on this box at 09:20 IST may well be a
compute writer. Tested as T1.

**G3 — `CPUQuota=50%`, `nice 19`, `ionice -c3`.**
Embedding yields to everything. `nice 19` and idle-class I/O mean a capture
cycle preempts it rather than queueing behind it.
*Fails when:* a production cycle's duration degrades during an embedding run —
which is why G8 measures rather than assumes.
**The t3 CPU-credit risk is explicit and is the reason `CPUQuota` is capped at
50% rather than higher.** `t3.small` is a burstable instance: it accrues CPU
credits at a fixed hourly rate and has a baseline utilisation well below full
use of its 2 vCPUs. Sustained work above baseline **draws down
`CPUCreditBalance`**, and the consequence lands on production, not on the
embedding job: in *standard* mode, credit exhaustion throttles the **whole
instance** to baseline, slowing every capture and compute writer for as long as
the deficit lasts; in *unlimited* mode it does not throttle but **bills** for the
surplus. Either way the embedding job is not the thing that suffers.
**FINDING S85 — G3's start-of-run credit check is UNIMPLEMENTABLE as written,
and the burst mode is undeterminable from this host.** Measured, not assumed:

| Probe | Result |
|---|---|
| `aws` CLI on box | **present** — `/usr/bin/aws`, aws-cli/1.22.34, botocore/1.23.34 |
| IAM instance role | **present** — the instance role (acct [redacted: account id]) |
| `ec2:DescribeInstanceCreditSpecifications` | **`UnauthorizedOperation`** — no identity-based policy allows it |
| `cloudwatch:GetMetricStatistics` (CPUCreditBalance) | **`AccessDenied`** |
| `cloudwatch:ListMetrics` — *control* | **`AccessDenied`** |
| IMDS credit-spec path | **does not exist** — IMDS exposes `instance-type` and `instance-life-cycle`, never credit specification |

**The `ListMetrics` control is what makes this a finding rather than a guess:**
the denial is blanket, not metric-specific, so **this box cannot read
`CPUCreditBalance` at all.** A guardrail conditioned on a value the host cannot
obtain is not a guardrail — it is Rule 0's first clause, a check that cannot fire
for the reason it names. It is recorded here rather than dropped.

**A second, worse problem with G3 as written, found while doing the arithmetic:
`CPUQuota=50%` does not bound credit draw.** `t3.small` accrues **24 credits/hr**
at a baseline of **20% per vCPU** — 0.4 vCPU sustained, which *is* 24 vCPU-min/hr.
A run pinned at `CPUQuota=50%` consumes **0.5 vCPU = 30 vCPU-min/hr = 30
credits/hr**, i.e. **above the whole instance's accrual rate before production's
own usage is counted.** So the quota does not make the run credit-neutral; only
its **duration** does — a 20-minute run costs ~10 credits against ~8 accrued, a
rounding error against a 576-credit ceiling, while an unbounded run at the same
quota drains steadily. **The binding quantity is `CPUQuota × timeout`, not
`CPUQuota`**, and G3 originally reasoned about the easy quantity rather than the
one that binds — the same substitution CLAUDE.md records for
`OB_MIN_MOVE_PCT`, Guard 3 and ADR-023 D1.
*(These credit figures are from AWS's burstable-instance table, stated from
knowledge and **not measured here** — they require operator confirmation, since
the arithmetic below depends on them.)*

**PROPOSED ALTERNATIVE — three parts, replacing the unimplementable check:**

- **G3a — structural CPU budget. RULED S85.** `CPUQuota=50%` × a **hard
  timeout of 20 minutes** per run, so one run consumes **≤ 10 CPU credits**
  (0.5 vCPU × 20 min = 10 vCPU-min = 10 credits) against a ~576-credit ceiling,
  with **`flock` enforcing single-instance** (G4) so two runs cannot sum past
  it, and off-hours-only execution. **The product `CPUQuota × timeout` and the
  resulting credit figure are written into every run's G7 record** — not merely
  reasoned about once here.
  *Fails when:* a run exceeds the 20-minute hard timeout and is killed by it,
  or a G7 record lands without the credit figure — **an unlogged budget is not a
  budget**. **This is the part that replaces the unreadable check**, because the
  binding quantity is `CPUQuota × timeout` and this ruling fixes both factors.
- **G3b — local contention proxy. RULED S85.** `CPUCreditBalance` is
  unreadable, but **`%steal` is** — `/proc/stat` field 8, measured at
  1,184,275 / 121,021,694 jiffies = **0.979 % cumulative** over 7 days of
  uptime. **At run start, sample `/proc/stat` twice, 10 seconds apart, compute
  the INTERVAL steal, and abort if interval `%steal` > 5 %.** The abort is a
  **requeue to the next allowed window, not a failure**. Requires no installs
  (`mpstat` is absent and is not needed).
  *Fails when:* interval steal exceeds 5 % at start, which requeues the run.
  **Three stated limits:** steal is a proxy for *contention or throttling*, not
  a credit balance; **cumulative-since-boot is useless as a gate**, which is
  why the sample is a 10-second interval and not the boot total; and it can read
  near-zero on an instance whose credits are healthy but about to be spent — so
  G3b detects a bad *present*, never a bad *future*. That is why G3a, not G3b,
  is the load-bearing part.
- **G3c — the grant question. RULED S85 (operator): Option 1 — NO IAM
  grant.** G3a + G3b are accepted as the replacement, the instance role is
  **left scoped to SSM**, and the operator reviews `CPUCreditBalance` **in the
  AWS console periodically**. Neither `cloudwatch:GetMetricStatistics` nor
  `ec2:DescribeInstanceCreditSpecifications` is added to the role.
  *What this ruling accepts, stated so it is not mistaken for coverage:* there
  is **no automated credit-balance gate, by decision**. G3a bounds the draw by
  construction and G3b catches a contended present; **neither can see the
  balance itself**, and no check in this ADR can. The residual is carried by a
  human review cadence — a deliberate trade of automation for a role that stays
  narrow.

**Burst mode remains UNMEASURED.** It cannot be read from this host. The
operator-side command is in §9.

**G4 — No run between 03:00 and 10:30 UTC.**
That window covers pre-open through close for the production chain. Outside it,
four further conditions:
- **A doc-close commit landing inside the window queues the re-index for the next
  allowed window.** It does not trigger an immediate run, and it does not
  silently skip. While queued, the system is *correctly* stale and both floors
  fail safe: interactive retrieval goes absent past `> 3` doc-commits or
  `>= 2` days (D3), and **ADR-027 V9 refuses drafting at `> 0` behind**. The
  queue is therefore a delay in capability, never a window in which stale
  context is served as current.
- **Pre-check that no capture or compute process is mid-cycle**, by process and
  by the latest `script_execution_log` row — not by the clock alone, since a
  cycle can overrun its slot.
- **`flock` single-instance.** Two concurrent embedding runs would each be inside
  a 600 MB scope and together exceed the box.
- **Hard timeout**, so a wedged run cannot sit through the next market open
  holding the lock.
*Fails when:* a run starts inside the window, starts alongside a live cycle,
starts twice, or outlives its timeout. T2 tests the window refusal.

**G5 — Abort if free disk < 5 GB. Model lives in a fixed directory.**
Not a hypothetical: on 2026-09-22 this volume reached 100% and removed **both**
documented access paths at once, because the SSM agent is a snap on the failed
volume and Instance Connect must write a key to it. The volume is now 30 GB with
23 GB free, and ~1.76 GB of the prior growth remains unattributed (TD-S80-NEW-15).
*Fails when:* free space is below the floor at start — the run refuses rather
than contributing to that condition.

**G6 — Model downloaded once, `sha256` pinned, `HF_HUB_OFFLINE=1` at runtime.**
The one-time download is an explicit, separate, operator-run step. Every
subsequent run is offline and verifies the pinned digest first.
*Fails when:* the digest mismatches, or the runtime attempts network egress.
A silently re-downloaded or substituted model would change every embedding
without changing `embed_model`, making a snapshot's vectors incomparable to its
own recorded provenance — undetectable at query time and fatal to A1's meaning.

**G7 — Log peak RSS, wall duration, chunk count, CPU credit balance and exit
status to a file covered by logrotate. Telegram alert on abort.**
`logrotate_meridian.conf` exists in the repo as of S80 and the new log is added
to it **in the same change** that creates the log — an uncovered log is how this
box filled up.
*Fails when:* a run completes with no record of peak RSS, or aborts with no
alert. An unlogged run cannot be reasoned about afterwards, and the guardrails
above are only as good as the evidence that they held.

**G8 — Post-run health check: production heartbeat and latest cycle status are
healthy.**
Assert on the **row counts and cycle status** in `script_execution_log` and the
capture tables — never on a status string, and never on `systemctl is-active`,
whose healthy and broken paths share a terminal state for `merdian-wsfeed`.
*Fails when:* a writer's latest cycle is missing or errored after an embedding
run. **This is the guardrail that can detect what G1–G7 missed**, and it is the
reason they are not merely asserted: G2 prevents production being reaped, G8 is
how we would learn that it was anyway.

#### Pre-registered guardrail tests — all pass before the first real run

Pre-registered per Rule 0's third clause. **None has been run**; this session is
measure-only and performs no installs, downloads or executions.

| # | Test | Pass condition |
|---|---|---|
| **T1** | Deliberately allocate past 600 MB inside the scope | The **allocating process is killed**, and every production PID is **unchanged** across the test — enumerated before and after, not inferred |
| **T2** | Attempt a run inside 03:00–10:30 UTC | Refuses, with the reason logged. Verified by injecting the clock, not by waiting for the window |
| **T3** | Install the full dependency set into `~/rag-venv` | **System `pip freeze` sha256 identical** before and after |
| **T4** | Embed a 50-chunk sample under the scope | **Peak RSS < 450 MB** |

**T4's predicted value, stated before measuring:** **~330 MB peak RSS.**
Derivation, so this is a belief rather than a number fitted later —
`bge-small-en-v1.5` is ~33 M parameters at fp32 ≈ **133 MB** of weights;
onnxruntime's CPU runtime and arena ≈ **80–120 MB**; the Python interpreter plus
`numpy` ≈ **60–80 MB**; tokenizer and 50 chunks of activations at 512 tokens ≈
**20–30 MB**. That totals **~300–360 MB**, leaving ~120 MB of headroom under the
450 MB bar and ~270 MB under G2's 600 MB kernel cap.
**If measured peak exceeds 450 MB the bar is not moved** — the run is
investigated, because the gap would mean the model, the runtime arena or the
batch size is not what this derivation assumed. **If it comes in far below
~300 MB, that is also a finding**, most likely that the sample never exercised a
full batch, in which case T4 has not tested what it claims.

**T1 is the load-bearing test.** T2–T4 check that the guardrails are configured;
T1 checks that the kernel actually enforces the one whose failure mode reaches
production. Its production-PID clause is what distinguishes "the cap works" from
"something died and it happened to be the right thing".

### 8.2 Guardrail execution order

Two independent lanes. **Lane A** is the re-index run, gated by G1–G8. **Lane B**
is ADR-027 drafting, gated by V0–V9.

**Step ids are hyphenated (`A-1`, `B-0a`) to distinguish them from the acceptance
criteria `A1` / `A2` / `A3`**, which are different objects in these same two
documents. An unhyphenated `A1` would resolve to both the retrieval-hit-rate
criterion in §7 and the window gate below — the wrong-citation class this ADR
pair exists to catch, so it is not left in place.

#### Lane A — re-index run

| Step | Action | Gate | Abort lands |
|---|---|---|---|
| **A-0** | Trigger: doc-close commit, or on demand. **Never a timer** (D3) | G4 | — |
| **A-1** | Is now inside 03:00–10:30 UTC? | **G4** | **Queue** for next allowed window; nothing runs. Interactive floor + V9 fail safe meanwhile |
| **A-2** | Acquire `flock` | **G4** | Exit quietly — another run holds it |
| **A-3** | Free disk ≥ 5 GB? | **G5** | Refuse + alert (G7). Does not contribute to a disk-full condition |
| **A-4** | Interval `%steal` below floor? | **G3b** | Requeue for next window |
| **A-5** | No capture/compute cycle mid-flight (process **and** latest `script_execution_log` row) | **G4** | Requeue — a cycle can overrun its slot, so the clock alone is insufficient |
| **A-6** | System `pip freeze` sha256 unchanged; venv intact | **G1** | Refuse; roll back the install that moved it |
| **A-7** | Model digest matches pin; `HF_HUB_OFFLINE=1` | **G6** | Refuse + alert — a substituted model silently invalidates every vector |
| **A-8** | Launch under `systemd-run --scope` (MemoryMax 600M, MemorySwapMax 0, OOMScoreAdjust 1000, CPUQuota 50%, nice 19, ionice -c3) | **G2, G3, G3a** | Kernel kills **the job** at 600 MB — not a production writer (T1) |
| **A-9** | Embed; write chunk rows into pre-existing `rag` tables (**rows only**, §6) | **G4** timeout | Timeout kill; lock released; partial snapshot must not become visible — see below |
| **A-10** | Mark snapshot complete | — | An incomplete snapshot stays invisible to retrieval |
| **A-11** | Log peak RSS, duration, chunk count, credit/steal readings, exit | **G7** | A run with no record cannot be reasoned about afterwards |
| **A-12** | Post-run: production heartbeat + latest cycle status healthy | **G8** | Alert; **block further runs until cleared** — G8 is how we would learn that G2 failed anyway |

**Atomicity gap found while sequencing this — recorded, not patched silently.**
`doc_chunk` has an FK to `corpus_snapshot`, so the snapshot row must be inserted
**first**, before its chunks. Retrieval keyed on "snapshot exists" would therefore
be able to read a **half-built index** mid-run, or a permanently partial one if
A-9 is killed at A-8's memory cap or A-9's timeout. That failure returns fewer
chunks than the corpus holds, with no error — and it would degrade A1 recall
while looking like a retrieval-quality problem rather than a truncated ingest.
**Proposed fix, owed before the first run:** add `completed_at timestamptz` to
`rag.corpus_snapshot` (NULL until A-10), and have every retrieval select only
snapshots with `completed_at IS NOT NULL`. §5's schema does not yet carry that
column; adding it is operator DDL like all the rest (§6).

#### Lane B — ADR-027 drafting

| Step | Action | Gate | Abort lands |
|---|---|---|---|
| **B-0a** | **Snapshot 0 doc-commits behind HEAD?** | **V9** (precondition; runs before V0–V8) | **Refuse to draft.** Never proceeds against a moved register |
| **B-0b** | **Is the Lane A `flock` free?** Lane B takes the same lock, or checks it | **V9** | **Refuse while a re-index holds it** — see the overlap note below |
| **B-1** | Transcript window per ADR-027 §5 selects ≥ 1 entry | **V0** | Abort — never widen the window |
| **B-2** | Compose splice set | — | — |
| **B-3** | Apply the splice to a **scratch copy** of each target file (under `scratch/`, **never `docs/`**) and run V1–V7 against that copy | **V1–V7** | Reject the draft. `docs/` is never touched, so this is consistent with D6 |
| **B-4** | Operator reviews the rendered diff | **D6** | No approval → nothing is written. There is no `--yes` |
| **B-5** | **Re-assert V9**, then apply the approved splice to the real files under `docs/`; **re-run V3 and V4 against the written file** | **V9, V3, V4** | Revert the write — the base moved between approval and write, or the anchor no longer matches once |
| **B-6** | Operator commits, pushes, re-uploads to project knowledge | operator | — |
| — | `anon` has zero privileges on `rag.*` | **V8** — **operator**, in the Supabase editor | Out-of-band; `merdian_ro` cannot `SET ROLE anon` |

**Why V1–V7 run twice, against two different files.** Before approval there is
nothing written to check, so they run against a scratch copy with the splice
applied — which tests the composed result rather than the composition. After
approval, V3 and V4 re-run **against the real file**, because the target may have
moved during review and an anchor that matched the scratch copy can fail on
disk. That is the S84 shape: content correct at compose time and wrong after the
write. The B-5 V9 re-assert covers the same window — a doc-commit landing while
the operator reads the diff invalidates the base the splice was authored against.

**Overlap between the lanes is prevented by the LOCK, not by the clock.** An
earlier draft of this section claimed the two lanes could never overlap by
construction; **that was false and is corrected here.** Lane B has **no
time-of-day gate**, and an on-demand Lane A re-index that introduces no new
doc-commits leaves B-0a passing — so the clock and the freshness check together
do not exclude concurrency. Two runs inside separate 600 MB scopes would together
exceed the box, which is G4's reason for `flock` in the first place. Hence B-0b:
**Lane B takes or checks the same `flock` and refuses while Lane A holds it.**

---

## 9. Open items requiring operator ruling before filing

1. **Confirm `ADR-026` still free** at filing time by the reserved-row method
   (S74 precedent: a next-free marker naming a consumed ID).

**No substantive decision remains open.** All three original items were ruled at
S85, and they left this list by ruling rather than by omission — recorded
because a shrinking open-items list is otherwise indistinguishable from an
abandoned one:

- **A1 thresholds** — RULED S85, recorded in §7.
- **Staleness floor values and the re-index trigger** — RULED S85, recorded in
  **D3**, tested by **§7 A1-secondary** (seven arms, both boundaries from both
  sides). The drafting half is enforced as **ADR-027 V9**.
- **Embedding provider and model** — RULED S85: `bge-small-en-v1.5`, 384-dim,
  ONNX, local on MERIDIAN EC2. Recorded in **D1**, with execution bounded by the
  **§8.1** guardrails G1–G8 and gated on tests T1–T4.

The sole remaining item is a filing-time hygiene check, so **this ADR is
ready to file** once it is done. Three things are nonetheless **owed before
the first real embedding run** — obligations, not open questions:

1. **T1–T4 must pass.**
2. **`completed_at` must be added to `rag.corpus_snapshot`** and honoured by
   every retrieval, per the §8.2 atomicity gap.
3. **Burst mode must be established.** It **cannot be read from this host** —
   measured S85: `ec2:DescribeInstanceCreditSpecifications` returns
   `UnauthorizedOperation` and CloudWatch is denied blanket (§8.1 G3 finding).
   **Run this read-only command from your own machine:**

   ```
   aws ec2 describe-instance-credit-specifications \
       --instance-ids i-0878c118835386ec2 --region eu-north-1
   ```

   `CpuCredits: standard` → credit exhaustion **throttles the whole instance** to
   baseline, degrading every production writer. `unlimited` → no throttle, but
   the surplus is **billed**. The two outcomes justify different `CPUQuota`
   values, so this is worth settling before T1–T4 rather than alongside them.
