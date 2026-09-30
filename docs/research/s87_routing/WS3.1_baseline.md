# WS3.1 — routing baseline: what Claude Code transcripts can and cannot measure

Measurement record for WS3.1. Every figure below is parsed from the frozen snapshot artefacts by the generator in `scripts/phase_c.py`; no number was typed. The generator exits non-zero naming any field it cannot parse rather than printing a default, and a closing assertion fails on any run of three or more digits in this document that the generator did not emit.

**Status: measurement only.** Nothing here is a decision. Section 7 states requirements this baseline implies for ADR-029; they are labelled derived requirements and they authorise nothing.

## 1. Provenance

| item | value |
|---|---|
| snapshot | `/home/ssm-user/s87_measure/snap_20260930T074849Z` |
| snapshot taken (UTC) | `20260930T074849Z` |
| `MANIFEST.sha256` sha256 | `526d74e02634c2eba2700811bd30b3d159fd26e2489a614103be86abef145f79` |
| manifest entries | 66 |
| `.jsonl` files under manifest | 66 |
| `schema_inventory.py` sha256 | `b2760806711f0b36617c4d8a903fd1336b58d254d9351e44c027b02103c9e0e3` |
| `baseline_b.py` sha256 | `e9eafdb73c9b7a27c55910ec412aa2c3cbebcb8ec6cd2aff42832255cfce6bac` |

**Metrics come from a frozen copy, not from the live directories, and the reason is a measured failure.** The first phase B run measured the live corpus. Its cross-check against phase A **failed on `-home-ssm-user-meridian-engine`**: phase B counted 2352 deduped responses against phase A's 2347, a delta of **+5**, verdict **MISMATCH**. This session writes to that directory, so it grew between the two runs. The cross-check is what caught it — nothing else in the instrument would have noticed, and every token total would have inherited the disagreement. After freezing, the same check reads delta +0 / MATCH on `-home-ssm-user-meridian-engine` and +0 / MATCH on `-home-ssm-user-meridian-cc`. The manifest verified `OK` before the runs and again after them.

## 2. Instrument and controls

All eight controls run on synthetic fixtures the instrument writes itself, before any metric is computed. A failure suppresses the metrics rather than annotating them.

| control | verdict | what it proves |
|---|---|---|
| C1 dedup | **PASS** | Lines sharing a `message.id` collapse to one response: the deduped input sum is 100 where a per-line sum would report 300. |
| C2 streaming | **PASS** | Streaming lines carry growing `output_tokens`; the last-line-in-file-order rule reports the final value, not the per-line sum of 85. |
| C3 cd regex | **PASS** | The Bash-form classifier keys on the leading token: a quoted `cd` inside an `echo` is not a `cd` form, and `git -C` is not one either. |
| C4 conservation (fixture only) | **PASS** | Per-session token sums add up to the project total, field by field. Fixture only — see the note below. |
| C5 negative control (cross-check can fail) | **PASS** | The phase-A cross-check *can* fail: dropping one id from a fixture makes it report MISMATCH. |
| C6 phase A reference parsed | **PASS** | The phase-A reference was parsed from phase A's own report, not typed into the instrument. |
| C7 schema subtree skipped | **PASS** | A key buried in a JSON-schema subtree does not reach the observability test: 1 schema-key occurrence(s) skipped in the fixture. |
| C8 real approval key survives | **PASS** | The schema skip does not blind the test: a real top-level `approvalGranted` key on a user line still becomes a candidate. |

**C4 is a fixture control only.** On real data the project total and the per-session sums are computed in the same loop, so the identity cannot fail and asserting it would prove nothing. The real-data check is the phase-A cross-check instead, and C5 exists to show that one can fail.

**C5's reported blind spot, stated because the control reports it itself:** the cross-check cannot detect a lost duplicate line, only a lost id. Two runs disagreeing only in how many lines a response was split across still agree on the id count and read MATCH.

## 3. Baseline

| measure | `-home-ssm-user-meridian-engine` | `-home-ssm-user-meridian-cc` |
|---|---|---|
| `.jsonl` files | 18 | 48 |
| bytes | 54485131 | 82884391 |
| non-blank lines | 15827 | 21485 |
| JSON parse failures | 0 | 0 |
| window, first to last timestamp | 2026-09-19T04:15:34.599Z → 2026-09-30T07:47:03.729Z | 2026-09-05T13:18:30.560Z → 2026-09-30T06:22:43.865Z |
| distinct `sessionId` values | 14 | 42 |
| sessions carrying at least one response | 14 | 40 |
| assistant lines | 5163 | 6398 |
| deduped API responses | 2358 | 3240 |
| lines per response (computed) | 2.190 | 1.975 |
| responses lacking a `message.id` | 0 | 0 |
| input tokens | 4698 | 6466 |
| cache_creation input tokens | 15316981 | 15486763 |
| cache_read input tokens | 1078699563 | 1014885570 |
| output tokens | 3257419 | 4096084 |
| all four, primary rule | 1097278661 | 1034474883 |
| all four, sensitivity rule (per-field max) | 1097278661 | 1034474883 |
| primary-vs-sensitivity gap | +0.0000% | +0.0000% |
| pooled re-read share — **PROXY** | 0.9860 | 0.9850 |
| pooled cache-creation share | 0.0140 | 0.0150 |
| prompt-token denominator | 1094021242 | 1030378799 |
| max context peak | 964286 | 873566 |
| sessions with peak > 200,000 | 11 | 37 |
| sessions with peak > 200,000 | 11 | 37 |
| `compact_boundary` lines | 2 | 0 |

The **primary-vs-sensitivity gap is +0.0000% on `-home-ssm-user-meridian-engine` and +0.0000% on `-home-ssm-user-meridian-cc`** — the per-field maximum across lines sharing an id and the last line in file order agree on every field in both corpora. The choice of dedup *rule* is therefore not load-bearing here; the choice to dedup **at all** is. At 2.190 and 1.975 lines per response, a per-line sum would inflate every token figure.

**Re-read share is labelled a PROXY and must stay labelled.** It is `cache_read / (input + cache_creation + cache_read)` — the share of prompt tokens served from cache. It cannot distinguish a cache hit on material the model used from a hit on material it ignored, and a TTL expiry is indistinguishable from genuinely new context. It is not a measure of how much context was re-read.

### Bash calls by leading form

| form | `-home-ssm-user-meridian-engine` calls / denials / rate | `-home-ssm-user-meridian-cc` calls / denials / rate |
|---|---|---|
| `cd-compound` | 949 / 37 / 3.9% | 479 / 41 / 8.6% |
| `cd-semicolon` | 182 / 5 / 2.7% | 169 / 10 / 5.9% |
| `git -C` | 41 / 2 / 4.9% | 87 / 2 / 2.3% |
| `bare git` | 8 / 2 / 25.0% | 112 / 10 / 8.9% |
| `python3/heredoc` | 186 / 22 / 11.8% | 408 / 34 / 8.3% |
| `other` | 505 / 39 / 7.7% | 1022 / 58 / 5.7% |
| **total** | **1871 / 107 / 5.7%** | **2277 / 155 / 6.8%** |

A denial is a joined `tool_result` with `is_error=true` whose text opens with a permission-refusal prefix. Denial rates differ by form — `git -C` reads 4.9% on `-home-ssm-user-meridian-engine` and 2.3% on `-home-ssm-user-meridian-cc`, against `cd-compound`'s 3.9% and 8.6% — but these are observational rates over unequal populations, not an experiment, and by 5a a denial rate is not a prompt rate. Section 6 is the experiment.

## 4. S86 harness results

| arm | results | `is_error` | sum `total_cost_usd` |
|---|---|---|---|
| `after_v1` | 45 | 4 | 14.732055 |
| `before_v3` | 45 | 0 | 33.184044 |
| `d5_probe` | 2 | 1 | 2.651006 |
| **total** | **92** | | **50.567106** |

Cross-check: sum of `total_cost_usd` = 50.567106, sum of `modelUsage.costUSD` = 50.567106, **difference 0.000000**, all on model `claude-opus-5[1m]`. **Costs are read from the tool's own fields; no price is applied anywhere in this instrument.** `num_turns` is carried as informational only — it counts harness turns, which is not a unit of work and is not comparable across arms.

## 5. Observability findings

### 5a. Approved permission prompts are NOT observable

Computed verdict, verbatim from the instrument:

> **APPROVED prompts not observable.** No key found by either test records a per-call approval: no matching key name is shaped like one, and no key appears on not-denied `tool_result` lines that is absent from denied ones.

Evidence, in the order it was obtained:

- **The lexical test alone was not enough.** A first run flagged `allowedPrompts` as a candidate. Inspection disposed of it: both occurrences sit on `attachment` lines at `$.attachment.entries[0].input_schema.properties.allowedPrompts`, are a tool's *parameter schema* rather than a record of any event, and the schema's own description reads "Deprecated: no longer used."
- **The fix is structural, not a name exclusion.** Key collection skips any path running through a JSON-schema subtree — a dict reached via `properties` whose parent carries `type`, or anything under `input_schema`. **28455 key occurrences were skipped** (`-home-ssm-user-meridian-engine` 9966, `-home-ssm-user-meridian-cc` 18489). No key name is special-cased, and C7 and C8 show the rule removes the schema key while keeping a real one.
- **A non-lexical test agrees.** Comparing the key sets of lines carrying a denied `tool_result` against lines carrying a non-denied one: on `-home-ssm-user-meridian-engine` the denied-only keys are _none_ and the not-denied-only keys are _none_; on `-home-ssm-user-meridian-cc` they are `toolDenialKind` and _none_. Nothing appears on the allowed side and nowhere else.
- **Denials are the only prompt signal, so the denial count has no denominator.** Across both corpora 318 denied and 5175 non-denied `tool_result`s were joined (`-home-ssm-user-meridian-engine`: 140 / 2220; `-home-ssm-user-meridian-cc`: 178 / 2955). An approved prompt and a call that never prompted are byte-indistinguishable, so no approval rate, prompt rate or approval-to-denial ratio can be computed from these transcripts at all.
- 8 key names matching `permission` / `approv` / `prompt` survive the schema skip across both projects, and none is a per-call permission outcome.

### 5b. Context-limit hits

Pre-registered reading, fixed before the markers were read: an event is a context-limit hit only if the context of its nearest preceding deduped response is **>= 900,000**, or its `error` type/code names *context* or *length*. A **line** counts as a hit when any of its markers meets that reading. Everything else is an other API event.

| corpus | marker events (hit / other / total) | distinct marker lines (hit / other / total) |
|---|---|---|
| `-home-ssm-user-meridian-engine` | 2 / 6 / 8 | 1 / 3 / 4 |
| `-home-ssm-user-meridian-cc` | 0 / 0 / 0 | 0 / 0 / 0 |

**`-home-ssm-user-meridian-engine`: 1 hit line.** `c972d318-699b-4e0a-af5f-c2f3ed7118a7.jsonl:1755`, markers isApiErrorMessage, error, preceding context 903266 — a margin of **+3266 tokens, +0.3629%** over the bar. The hit fired on the **size arm only**: the error code names neither context nor length, so had the bar been set 3267 tokens higher this line would read as an other API event. One line, one arm, a +0.3629% margin.

**`-home-ssm-user-meridian-cc`: not observable.** The instrument's own line: *context-limit hits without compaction are NOT observable by this metric*

**Corroboration, recorded outside the rule.** The same session carries a `compact_boundary` after the error. That is consistent with a context-limit event and is **not** part of the pre-registered reading, so it adds no hit; the field-level marker summary reads `compact_boundary (1), isApiErrorMessage (3), truncatedAfterOutput (1), error-key (3)`. It is written down here so a later reader can see what was available and what was counted.

**This is not linked to the S86 event on record.** The hit line is a context-limit-shaped event found in the snapshot by the stated rule. No attempt was made to match it to the S86 incident, and none should be read into it.

## 6. RUN — Block 4, the `git -C` prompt experiment

**RUN. Operator-observed, 2026-09-30 ~14:18 IST, operator.** The question is narrow: **does `-C` break the built-in read-only no-prompt match?** A bare read-only `git` invocation is matched as read-only and does not prompt; whether the same command with a `-C <path>` prefix is still matched was unknown, and 5a establishes that the transcripts cannot answer it — approvals leave no record, so a low denial rate is equally consistent with "never prompted" and with "prompted and approved every time". This is **not** a `git -C` versus `cd` comparison.

Session and cadence, as observed: **one fresh session (after /clear), commands run one at a time, once each, as Block 4 specified**. Working directory `/home/ssm-user/meridian-engine`; **n=1 per command**.

| # | command | prompted? |
|---|---|---|
| 1 | `git rev-parse --short HEAD` — bare control | no prompt |
| 2 | `git -C /home/ssm-user/meridian-engine rev-parse --short HEAD` | PROMPTED |
| 3 | `git -C /home/ssm-user/meridian-cc rev-parse --short HEAD` | PROMPTED |
| 4 | `git status --porcelain` — bare control | no prompt |

**The `-C` form broke the built-in no-prompt match — even when `-C` named the working directory the session was already in** (row 2, `/home/ssm-user/meridian-engine`, which changes nothing about which directory git reads and still prompted, while the bare forms did not): the prefix itself is what falls outside the match, not the directory it points at. **n=1 per command** in a single session, so this is an existence result and not a rate.

Every cell above is read from `gitC_result.json`, the operator's own record. The generator **aborts** if that file is absent, so an unrun experiment cannot render as a run one with an empty column.

## 7. Derived requirements for ADR-029

**Derived requirements, not decisions.** Each follows from a measurement above. None is adopted here; ADR-029 decides.

| # | requirement | the measurement it follows from |
|---|---|---|
| R1 | Permission prompts must be logged going forward, at the point the prompt is raised and resolved. | 5a: approvals are byte-invisible, so no retrospective analysis of prompting can ever be run on transcripts. |
| R2 | Context-limit events must be logged going forward, with the context size at the moment of the failure. | 5b: both corpora together yield 1 hit line, identified by a margin of +3266 tokens on a single arm. |
| R3 | Any token figure must be deduplicated by `message.id`. | Section 3: 2.190 and 1.975 assistant lines per response; a per-line sum inflates every field. |
| R4 | Any live corpus is measured from a sha-manifested snapshot, verified before and after the run. | Section 1: the live run failed its cross-check by +5 responses because the corpus grew mid-measurement. |

## 8. Instrument defects caught during WS3.1

For the Assumption Register at doc-close. Every row is a defect in the *instrument*, not in the system it measures.

| # | defect | how it was caught | fix |
|---|---|---|---|
| D1 | The B5 verdict was written in advance — a fixed paragraph naming keys before the script had read any data. | Review, before the first run. | Verdict computed from the keys actually found, plus a non-lexical key-set differential; the interpretive sentence kept but demoted and labelled "author's reading". |
| D2 | The conservation check could not fail on real data: the total and the per-session sums came from the same loop. | Review. | Kept as fixture control C4; the real-data check replaced by the phase-A cross-check, with C5 proving that one can fail. |
| D3 | The context-limit string scan read conversation text, in a project that discusses context windows constantly. | Review. | Paths under `$.message.content` excluded structurally, their match count reported as one number, and the remaining text-bearing paths named as still in scope. |
| D4 | The corpus was live and grew during measurement. | **Instrument** — the phase-A cross-check, on its first real run. | Frozen sha-manifested snapshot, verified before and after the runs. |
| D5 | A lexical name test produced a false candidate, `allowedPrompts`, from a deprecated JSON-schema property. | **Instrument** — the verdict refused to conclude and named the candidate for inspection. | Structural schema-subtree skip, with C7 and C8 proving it removes the schema key and keeps a real one. |
| D6 | Marker *events* were reported as marker *lines*, so one line carrying three markers counted three times. | **Instrument** — the table showed three rows at one timestamp. | Both units reported, keyed by (file, line number); a line is a hit when any of its markers meets the reading. |
| D7 | The nearest-preceding-response carry crossed file boundaries, so a marker on a file's first lines could inherit another session's context and be pushed over the bar. | Review of the patch, before it ran. | Carry reset at every file boundary, plus a session guard at render; no row in the final table was affected. |

Of 7 defects, **4 were caught by review** (D1, D2, D3, D7) and **3 by running an instrument** (D4, D5, D6).

Two patterns are worth separating, because they need different remedies. **D2, D3 and D7 are checks that could not fail for the reason they named** — D2 could not fail at all, D3 measured the wrong text, and D7 would have measured the wrong session. Those are fixed by changing what the check reads. **D1 is not that.** Its check ran correctly; the conclusion had simply been written before any measurement existed to support it, so the output would have been the same whatever the data said. That is fixed by computing the verdict, which is what turned D5 from a silent pass into a named candidate for inspection.

---

*Generated by `scripts/phase_c.py` from `snap_20260930T074849Z`. Instruments copied to `scripts/`; no transcript, snapshot or report file is committed.*
