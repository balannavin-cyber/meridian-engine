# S85 — Feasibility inventory: automated doc-close pipeline

**Session:** S85 · **Date:** 2026-09-29 · **Mode:** MEASURE-ONLY
**Corpus HEAD:** `59c934936305d1b73f6a621ec880cb53f5d54617`
**HEAD == origin/main:** YES — verified by `git ls-remote origin refs/heads/main`
(read-only; no local ref written).

**Write boundary honoured this session.** Everything created lives under
`~/meridian-cc/scratch/s85_rag/`. `~/meridian-engine` — the production tree cron
executes from — was confirmed untouched: `scratch/` does not exist there (not even
the parent), and `git status --short` is 11 untracked / **0** modified, identical
to the session-open snapshot. No DDL, no database writes. Every DB read went
through `bin/roq.sh` as `merdian_ro` (SELECT-only role).

> **Note on a premise.** The brief stated `~/meridian-engine` "sits several
> commits behind". Measured, it does not: `rev-parse HEAD` returns the same SHA
> `59c9349` in both trees, with the same `origin`. Since the corpus is read from
> a commit, both trees yield byte-identical inventories. All git calls below use
> `-C /home/ssm-user/meridian-cc` as instructed regardless.

---

## 1. Claude Code session transcripts

**Path:** `~/.claude/projects/<slug>/*.jsonl`, one directory per launch cwd.

| Slug | Files | First entry | Last entry |
|---|---:|---|---|
| `-home-ssm-user-meridian-cc` | 40 | 2026-09-05T13:18 | 2026-09-22T06:21 |
| `-home-ssm-user-meridian-engine` | 10 | 2026-09-19T04:15 | 2026-09-29T03:46 |
| `-home-ssm-user-srs-work` | 1 | 2026-09-21T05:13 | 2026-09-21T05:42 |
| `-var-snap-amazon-ssm-agent-13349` | 1 | 2026-09-23T11:01 | 2026-09-24T15:38 |
| **TOTAL** | **52** | **2026-09-05** | **2026-09-29** |

**Volume:** 112,017,867 bytes (107 MiB) · 30,827 JSONL lines.

**Format:** newline-delimited JSON, one typed envelope per line. Entry `type`
values observed across the 52 files: `user`, `assistant`, `system`, `attachment`,
`mode`, `permission-mode`, `bridge-session`, `last-prompt`, `cost-state`,
`file-history-snapshot`, `file-history-delta`, `atis-latch`, `ai-title`,
`queue-operation`. Only `user` / `assistant` (and the tool blocks nested inside
assistant entries) carry session substance; the rest is harness state.

### S82 / S83 / S84 presence — PRESENT, but not as discrete files

| Session | Highest-marker file(s) | Marker count | File time span |
|---|---|---:|---|
| S82 | `0131f83d` | 1,644 | 2026-09-23T14:15 → 2026-09-25T03:30 |
| | `4b3bff6f` | 283 | 2026-09-23T13:45 → 2026-09-23T14:16 |
| S83 | `0131f83d` | 856 | (same file as S82) |
| | `c972d318` | 784 | 2026-09-25T07:01 → 2026-09-29T03:31 |
| S84 | `c972d318` | 1,323 | (same file as S83) |
| | `13285548` | 63 | 2026-09-25T11:47 → 2026-09-25T12:36 |

**Two findings that constrain the pipeline design.**

**(a) There is no 1:1 session↔file map, in either direction.** `0131f83d`
(10.3 MB) spans S81 / S82 / S83. S84 appears across three files. A single
transcript spans up to four calendar days (`c972d318`: 09-25 → 09-29). Any
"ingest one transcript, emit one doc-close" assumption is false at the input.

**(b) Marker counting is contaminated and cannot be the attribution method.**
CLAUDE.md is injected into every session's context and names every prior session,
so an S80 transcript legitimately carries `S79:1669`. Marker argmax is
*suggestive only*. Reliable attribution must come from entry `timestamp` ranges
bounded by the doc-close commit times (§5), not from content frequency.

**Correction to my own prediction.** I predicted S84's transcript was missing,
because no file has an mtime on 09-26/27/28. Wrong: mtime is last-write, and
these sessions run for days. Nothing is missing. Recorded here because the same
reasoning error would have produced a fabricated gap in the register.

---

## 2. Docs corpus at HEAD

**Scope:** every tracked file under `docs/` plus `CLAUDE.md`.
Full per-file table: `docs_inventory.out`.

| | Files | Bytes |
|---|---:|---:|
| Text (RAG-eligible) | 138 | 7,432,679 |
| Binary `.docx` (excluded) | 27 | 1,094,035 |
| **TOTAL** | **165** | **8,526,714** |

Text lines: 68,060. `CLAUDE.md` = 327,171 B / 1,169 L (working tree matches HEAD).

### Entry-ID density

| Pattern | Heading-anchored | All mentions |
|---|---:|---:|
| `TD-*` | 2,965 | 7,254 |
| `ADR-NNN` | 1,574 | 4,223 |
| `ENH-N` | 1,583 | 6,018 |
| `§D.N.N` | 174 | 493 |
| `CASE-*` | 21 | 55 |

"Heading-anchored" = the ID appears on a markdown heading (`#`–`######`) or a
bolded register row (`- **TD-…**`), i.e. lines that are candidate chunk
boundaries. The corpus is **densely ID-anchored** — ~6,300 anchored IDs across
138 files. This is the single most favourable fact for retrieval: entry IDs are a
natural, high-precision retrieval key, so hybrid (lexical ID match + vector)
should strongly outperform pure vector.

### Ten largest text files — the chunk-count drivers

| Bytes | File |
|---:|---|
| 1,075,558 | `docs/registers/tech_debt.md` |
| 790,734 | `docs/registers/CURRENT_history.md` |
| 615,172 | `docs/registers/session_log_history.md` |
| 610,151 | `docs/registers/merdian_reference.json` |
| 459,686 | `docs/registers/MERDIAN_Enhancement_Register.md` |
| 327,171 | `CLAUDE.md` |
| 320,123 | `docs/registers/MERDIAN_Assumption_Register.md` |
| 236,438 | `docs/registers/MERDIAN_System_Map.md` |
| 230,541 | `docs/registers/MERDIAN_Deployment_Topology.md` |
| 143,384 | `docs/registers/CLAUDE_history.md` |

Nine files hold 4.8 MB of the 7.4 MB text corpus (65%).

### Files with no entry-ID structure — 51 flagged

Full list in `docs_inventory.out`. **The flag needs interpreting, not just
reporting.** Three distinct causes:

1. **Genuinely unstructured, correctly flagged** — runbooks
   (`runbook_update_dhan_token.md`, `RUNBOOK_TEMPLATE.md`), Documentation
   Protocol v1–v3, `MERDIAN_Session_Management_v1.md`, lovable prompts,
   `MERDIAN_Data_Inventory.md`, `MERDIAN_Hedgewall_Parity_Spec.md`. These are
   procedural/spec prose. They need heading-path chunking, not ID chunking.
2. **Not markdown at all** — `merdian_reference.json` (610 KB, **2,194** inline
   IDs, zero headings), `s72_gex_view_fix.sql`, `parameters_jsonb.py`,
   `gamma_metrics_tail_probe.py`, `logrotate_meridian.conf`, `aws_crontab.txt`.
   JSON needs structural (key-path) chunking; the flag is an artifact of applying
   a markdown test.
3. **Paragraph-per-line files** — dense with IDs but with no heading anchors:

| B/line | Bytes / lines | File |
|---:|---|---|
| 2,665 | 55,974 / **21** | `docs/session_notes/session_log.md` |
| 2,516 | 143,384 / **57** | `docs/registers/CLAUDE_history.md` |
| 736 | 111,098 / **151** | `docs/decisions/MERDIAN_Decision_Index.md` |
| 523 | 615,172 / 1,176 | `docs/registers/session_log_history.md` |
| 326 | 320,123 / 981 | `docs/registers/MERDIAN_Assumption_Register.md` |
| 280 | 327,171 / 1,169 | `CLAUDE.md` |

**This is the load-bearing chunking finding.** `session_log.md` averages 2,665
bytes per line; `CLAUDE_history.md` 2,516. One line is one whole session entry —
larger than a 512-token chunk. **Line count is not a proxy for chunkability
anywhere in this corpus**, and a line-window chunker would emit chunks varying by
two orders of magnitude. Chunking must be byte/token-budgeted with ID-anchored
boundaries, and must split *within* a line for these six files.

---

## 3. pgvector

Query run via `bin/roq.sh` (as `merdian_ro`):

```
  name  | default_version | installed_version
--------+-----------------+-------------------
 vector | 0.8.2           |
(1 row)
```

**AVAILABLE at 0.8.2 · NOT INSTALLED** (`installed_version` empty).

`CREATE EXTENSION vector` is a write and is refused by `merdian_ro` both at the
client verb guard and at the role. **This is an operator action**, and under
Doc Protocol Rule 10 a new schema + tables is an ADR-gated change — hence the
draft alongside this file.

**Index sizing is a non-issue.** At the estimate in §4 (~4,270 chunks) a
float32 index is **6.6 MB at 384-dim** or **13.1 MB at 768-dim**. There is no
scaling argument for infrastructure beyond the existing Supabase instance; an
HNSW index over ~4k rows is trivial. Note ADR-021's lesson applies to any view
built over these tables: scope to the snapshot the consumer reads, or the cost
curve returns at larger N.

---

## 4. Host capacity — local vs hosted embeddings

| Field | Measured |
|---|---|
| Instance | `i-0878c118835386ec2`, **t3.small**, eu-north-1 |
| vCPU | 2 |
| RAM | 1,910 MB total · 585 used · **1,125 MB available** |
| **Swap** | **none** |
| Disk | 29 G total · 6.2 G used · **23 G available** (22%) |
| Python | 3.10.12 |

Installed: `numpy` 2.2.6, `supabase` 2.28.3.
**Absent: `torch`, `onnxruntime`, `transformers`, `sentence-transformers`,
`tiktoken`, `psycopg2`/`psycopg`.**

### Workload estimate — labelled ESTIMATE, not measurement

`tiktoken` is absent, so tokens are estimated at **4.0 chars/token** (a stated
assumption). 7,432,679 text bytes → **~1.86 M tokens** → **~4,270 chunks** at
512 tokens with 15% overlap.

### The binding constraint is RAM, not disk or index size

Disk at 23 G free is ample. The constraint is **1,125 MB available with no
swap, on the box that runs production cron** — the orchestrator, capture and
compute writers. An embedding job that peaks into OOM does not merely fail; the
kernel may reap a production writer. This is the same box whose root volume
filling at S80 removed *both* documented access paths simultaneously.

| Option | Peak RAM | Disk | Verdict |
|---|---|---|---|
| `torch` + sentence-transformers (MiniLM) | ~0.8–1.2 GB | ~2.0 GB | **Not advised** — peak brushes the 1.1 GB ceiling with no swap, against live writers |
| `onnxruntime` + MiniLM-L6 ONNX (384-dim) | ~0.3–0.4 GB | ~0.3 GB | **Feasible** — comfortable margin; needs `nice`/`systemd-run` memory cap and an off-hours window |
| Hosted embedding API | ~0 | ~0 | **Recommended** — one-off cost for ~4,270 chunks is negligible; zero production risk |

**Recommendation:** hosted embeddings for the initial build, with ONNX-local as
the documented fallback if egress of document text to a third party is
unacceptable. That is a real consideration and an operator call: the corpus
contains infrastructure topology and incident detail, though **no secrets** —
`.env` is gitignored and absent from the corpus. It is *not* a reason to prefer
torch-local; ONNX-local is the privacy-preserving option, not torch.

If local is chosen: run under `systemd-run --scope -p MemoryMax=600M`, outside
03:00–10:30 UTC, and only after confirming no capture/compute cron is mid-cycle.

---

## 5. Doc-close replay ground truth

| Session | Commit | Date | Files | +ins | −del |
|---|---|---|---:|---:|---:|
| S82 | `bb374ae` | 2026-09-24 | 12 | 1,481 | 1,202 |
| S83 | `18c2fb8` | 2026-09-25 | 16 | 1,635 | 38 |
| S84 | `e554a56` | 2026-09-28 | 8 | 251 | 95 |

S82 and S83 match the file counts asserted in their own commit messages (12, 16).
S84's message states no count; it is 8.

### Three properties that must shape the replay metric

**(a) Doc-close granularity changed at S82.** S81's doc-close was **split across
~12 commits** (`doc-close 1/10` … `10/10`, plus `1b`, `3b`, `6b`). S82/S83/S84
are each a **single** commit. So S82–S84 are clean replay targets and **S81 is
not usable as one without reassembly** — worth knowing before anyone proposes
widening the ground-truth set backwards.

**(b) The S83 diff is 64.2% SQL authoring, not doc-close prose.** Measured:
1,049 of 1,635 insertions are the three `sql/` files (`v_iv_term_structure`,
`v_gex_repriced_flip`, `v_iv_surface`). Those are the session's *build* output,
which a doc-close pipeline is not being asked to generate. **Replay agreement
scored on the raw S83 diff would mostly measure SQL generation.** `sql/` must be
excluded from the scored surface, leaving ~586 prose insertions.

**(c) There is an 8-file invariant core.** Recurrence across the three:

| Appears in | Files |
|---|---|
| **3 of 3** | `CLAUDE.md`, `docs/session_notes/CURRENT.md`, `docs/session_notes/session_log.md`, `docs/registers/CURRENT_history.md`, `docs/registers/session_log_history.md`, `docs/registers/merdian_reference.json`, `docs/registers/MERDIAN_Assumption_Register.md`, `docs/registers/MERDIAN_Enhancement_Register.md` |
| 2 of 3 | `tech_debt.md`, `MERDIAN_System_Map.md`, `MERDIAN_Deployment_Topology.md` |
| 1 of 3 | `MERDIAN_Decision_Index.md`, `aws_crontab.txt`, `capture_s83.md`, 3× `sql/` |

**The 3-of-3 set is exactly S84's complete file list.** That is a genuine
structural regularity: an invariant core always touched, plus a conditional tail
gated on whether the session produced tech debt, topology change, or an ADR. It
gives the pipeline a defensible target decomposition — and it also means a naive
"did we touch the right files?" metric scores ~100% by always emitting the core,
which is why file-set agreement alone must not be an acceptance criterion.

---

## 6. Feasibility assessment

**Favourable:**
- Corpus is small (7.4 MB text, ~4.3k chunks) — index size and query latency are
  non-problems; pgvector 0.8.2 is available on the existing instance.
- ~6,300 heading-anchored entry IDs give a high-precision lexical retrieval key;
  hybrid retrieval should beat pure vector substantially.
- Three single-commit doc-closes exist as ground truth, with a measured
  invariant-core structure.
- `roq.sh` already provides a safe read-only DB path for a verifier.

**Unfavourable / needs design:**
- Transcript→session attribution is not a file mapping and marker counts are
  contaminated (§1). Needs timestamp bounding against commit times.
- Six high-value files are paragraph-per-line at up to 2,665 B/line (§2);
  chunking must split within lines.
- `merdian_reference.json` (610 KB) needs structural, not markdown, chunking.
- 1,125 MB RAM / no swap on a production-cron box constrains local embedding
  (§4).
- Ground-truth surface needs `sql/` exclusion and a metric that cannot be gamed
  by emitting the invariant core (§5).
- Registers are **newest-first and prepend-only**, so any generated edit must be
  a byte-level splice with fail-loud assertions per Doc Protocol v4 Rule 7 — not
  a full-file rewrite. Line citations into these files decay on the next filing
  (S84 rule), so generated cross-references must use entry ID + row name.

**Verdict:** feasible, with the retrieval layer the low-risk half and the
*drafting + verification* half carrying essentially all the risk. Nothing
measured here blocks a build. Thresholds are deliberately left for operator
ruling in the draft ADR — per Rule 0, an expected value obtained by running the
thing is not an assertion, so the numbers must be set before the first replay.

---

## 7. Artifacts

| File | Contents |
|---|---|
| `inventory.md` | this document |
| `map_transcripts.py` / `transcript_map.out` | §1 — per-file timestamps, markers, entry types |
| `docs_inventory.py` / `docs_inventory.out` | §2 — per-file bytes/lines/ID counts, flags |
| `corpus_size.py` / `corpus_size.out` | §4 — text/binary split, chunk + index estimate |
| `ADR-026-DRAFT-doc-close-rag-pipeline.md` | draft ADR — **NOT FILED** |

All three scripts were `py_compile`-gated before execution.
