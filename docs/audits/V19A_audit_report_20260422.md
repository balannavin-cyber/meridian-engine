# Audit Report — MERDIAN Appendix V19A

**Auditor:** Independent review, operating from the 13-block Development Session Documentation Checklist (Appendices H/I origin, re-uploaded 2026-04-22).
**Document under audit:** `MERDIAN_AppendixV19A.md` (62,340 bytes, 753 lines, draft pending docx render).
**Audit date:** 2026-04-22 (IST).
**Audit scope:** Rebuild-grade completeness per checklist. Can a developer with no prior context reconstruct the 2026-04-20 session state from V19A alone?

---

## 1. Executive Summary

**Verdict:** **PASS with three MINOR findings and one MODERATE finding.** V19A is rebuild-grade for its declared scope (the 2026-04-20 session — programme Sessions 1+2).

A cold-start developer could reconstruct the 2026-04-20 work end-to-end from V19A alone without asking a question. All file paths are absolute, all DDL is inline, both incidents are timeline-reconstructed, rejected alternatives are documented, and the resume prompt is paste-ready. This is the checklist outcome.

The four findings below are real — not cosmetic — but none defeat the rebuild-grade property. They should be resolved in V19A v2 if a docx render is commissioned; they do not warrant blocking the current markdown draft from being the authoritative session record.

### Findings Summary

| # | Severity | Block | Finding | Blocks rebuild-grade? |
|---|---|---|---|---|
| F-1 | MODERATE | Block 6 | API contracts are under-populated with observed values — "specific values not logged because outage prevented capture" | No, but weakens claim partially; self-audit acknowledges this honestly |
| F-2 | MINOR | Block 3 | The 7-script ENH-66 propagation list contains one double-count and an internal inconsistency between §1.2 and §2.3 | No — the 7 scripts can be enumerated unambiguously from git |
| F-3 | MINOR | Block 4 | Row counts are dated 2026-04-21 16:30 IST, not 2026-04-20 session close | No, but a rebuild-grade audit should call out this timing offset explicitly |
| F-4 | MINOR | Block 5 | Full DDL provided, but the SCHEMA of `trading_calendar` (which was central to Incident #1) is described in prose only, not with a `\d trading_calendar` output | No, but the checklist Block 5 specifically says "copy from `\d tablename`, not from memory" |

---

## 2. Block-by-Block Audit

### Block 1 — Session Identity ✅ PASS

| Checklist item | V19A evidence | Status |
|---|---|---|
| One-sentence primary objective | §1.1 lines 23-25 — single sentence naming ENH-66 + ENH-68 + ENH-71 explicitly | ✅ |
| Secondary items list | §1.2 — 8 numbered items (register unification, archive migration, ICT zone reference, ENH-63/65 status flips, `.gitignore` modernization, AWS-local merge, 6 new ENH IDs reserved) | ✅ |
| Parent documents | §1.3 — V19 master (`07b2494`), V18H_v2 appendix (`4675745`), V18H_v2_RENUMBERING_NOTE.md | ✅ |
| Versioning | §1.4 — explicitly says "V19A is a session appendix, not a master increment" with V19A_v2 naming convention | ✅ |

**Auditor note:** §1.2 item 1 lists "ENH-66 propagation across **7 calendar-gated scripts**" and names them. This list enables F-2 below. The count is stated as 7 but the enumeration names 7 files with parenthetical caveat "(`capture_spot_1m.py` and `merdian_start.py` are also in this set but listed elsewhere.)" — see F-2 for detail.

### Block 2 — Before / After Boundary ✅ PASS

This is the block the checklist explicitly flags as "the most commonly missed." V19A takes this seriously.

| Checklist sub-item | V19A evidence | Status |
|---|---|---|
| What existed before | §2.1 — code baseline (`cdcdbbd`), database baseline, register fragmentation state, 14 active ENH IDs, 6 legacy OI IDs all named | ✅ |
| What was discovered (the under-documented item) | §2.2 — **6 explicit numbered discoveries**, each naming the thing and why it wasn't known going in | ✅ EXCELLENT |
| What changed (not aspirational) | §2.3 — 5 sub-categories (schema additions, files created, files modified, files removed/untracked, files moved, JSON deltas) | ✅ |

**Auditor note:** §2.2 discovery #3 is notable — the stale-token cascade is framed as "a different bug from #1 — it surfaced because the holiday-gate fix made the pipeline run again, exposing the stale-env defect that had been hidden behind the silent-exit." This causal-chain framing is exactly what the checklist Block 2 is asking for and it would commonly be missed. Credit.

### Block 3 — File Inventory ⚠️ MINOR FINDING (F-2)

| Checklist sub-item | V19A evidence | Status |
|---|---|---|
| Full path for every file | §3.1, §3.2, §3.3 — all paths absolute `C:\GammaEnginePython\...` | ✅ |
| Reads from / Writes to | §3.1 table has Reads/Writes columns populated per file | ✅ |
| Status (✅/⚠️/❌/🔄) | §3.1 column uses the exact checklist legend | ✅ |
| Notes (with root cause if known wrong thing) | §3.1 Notes column has substantive content per row, including caveats | ✅ |
| Rejected/superseded files documented anyway | §3.4 "Files NOT touched but worth noting (rejected scope)" names 2 | ✅ |

**Finding F-2 (MINOR):** Internal inconsistency in the ENH-66 propagation file count.

- §1.2 bullet 1 says "**7 calendar-gated scripts** beyond the architectural fix in `merdian_start.py`" — and then names 7 files, **one of which IS `merdian_start.py`**. Reading carefully: the list enumerates `build_market_spot_session_markers.py, capture_market_spot_snapshot_local.py, capture_spot_1m.py, compute_iv_context_local.py, ingest_breadth_intraday_local.py, merdian_start.py, run_equity_eod_until_done.py`. That is 7 files total, but one of them (`merdian_start.py`) is the architectural fix itself, not "beyond" it.
- §2.3 "Files modified" then lists **6 scripts** as "6 additional calendar-gated scripts patched for ENH-66 propagation" — parenthetically admitting "(`capture_spot_1m.py` and `merdian_start.py` are also in this set but listed elsewhere.)"
- §3.1 table lists **9 code files total** including `merdian_start.py`, `capture_spot_1m.py`, and the 6 others + `run_option_snapshot_intraday_runner.py` + `core/execution_log.py` + `.gitignore`.

**Impact:** A cold-start developer counting "was this 6, 7, 8, or 9 scripts?" has to cross-reference three sections and accept the §2.3 parenthetical as the tie-breaker. The git commit itself (`ef477e6`, "V18G orphan work") is authoritative and the V19B draft will likely enumerate it exactly — but V19A standing alone is ambiguous.

**Recommended fix:** One canonical list. State "ENH-66 landed across N files in commit ef477e6: merdian_start.py (architectural fix at commit 8f83859) + N-1 consumer propagation files in commit ef477e6." Enumerate once; cross-reference by exact count everywhere else.

### Block 4 — Table Inventory ⚠️ MINOR FINDING (F-3)

| Checklist sub-item | V19A evidence | Status |
|---|---|---|
| Exact table name with schema prefix | `public.script_execution_log`, `public.v_script_execution_health_30m`, `public.trading_calendar`, etc. | ✅ |
| Written by / Read by | Columns populated | ✅ |
| Row count at end of session | §4 table | ⚠️ see F-3 |
| Column-level gotchas | `trading_calendar` row on `open_time`/`close_time` nullability called out explicitly; `is_pre_market` vestigial column flagged; `contract_met` NULLable-while-in-flight called out | ✅ |

**Finding F-3 (MINOR):** The row counts in §4 are dated "2026-04-21 16:30 IST" — ONE DAY after the V19A session (2026-04-20).

- The `script_execution_log` count is stated as "~120 rows by session end (capture_spot_1m running 1/min during the post-fix window)" — this IS a session-end value, correctly scoped.
- But `market_spot_snapshots: 7,207`, `hist_spot_bars_1m: 213,227`, `option_chain_snapshots: 1,018,302`, etc. — all tagged "per Block 4 row-count query 2026-04-21 16:30 IST" — are from the NEXT session's evidence gathering, not from the 2026-04-20 session close.

**Why this matters:** A rebuild-grade document's Block 4 exists so a cold-start developer can confirm "the table has roughly this many rows and it's this many rows because of what this session did." Using next-day counts imports unrelated downstream-session changes into the V19A numbers. For `market_spot_snapshots`, this is not a huge distortion (delta is ~1 trading day of 5-min captures). For `hist_spot_bars_1m`, the V19B session did a deliberate 2,250-row Kite backfill for 04-16/17/20 — so the 213,227 figure includes work that V19A did NOT do.

**Severity is MINOR because:** V19A discloses the 2026-04-21 16:30 IST timestamp openly, not covertly. A careful reader can reconcile it. But a cold-start developer reading fast will assume these are session-close numbers.

**Recommended fix:** Either (a) add a parallel 2026-04-20 session-close row-count column to §4, or (b) add one sentence flagging "row counts sourced from 2026-04-21 16:30 IST evidence query; intervening 04-21 morning work added ~X rows to market_spot_snapshots and ~2,250 rows to hist_spot_bars_1m (Kite backfill, not V19A scope)."

### Block 5 — Exact Schemas ⚠️ MINOR FINDING (F-4)

| Checklist sub-item | V19A evidence | Status |
|---|---|---|
| Full DDL for new tables | §5.1 — 133 lines of DDL verbatim from `sql/20260420_script_execution_log.sql`, including all 4 indexes + check constraint + 5 column comments + rollup view | ✅ EXCELLENT |
| Full confirmed column list for tables verified this session | §5.1 covers `script_execution_log`; `trading_calendar` is discussed in §5.3 in PROSE only | ⚠️ F-4 |
| Indexes / unique constraints / generated columns noted | All 4 indexes + unique(invocation_id) + check constraint all present in §5.1 | ✅ |
| Schema differences vs prior documents | §5.2 — "None. script_execution_log is a new table" — explicit, checklist-compliant | ✅ |

**Finding F-4 (MINOR):** `trading_calendar` schema is central to Incident #1 but is NOT provided as a `\d trading_calendar` output.

- §5.3 describes the nullability of `open_time` / `close_time` in prose ("the trading_calendar table schema is unchanged from prior masters. What changed is the *invariant*...").
- The checklist Block 5 requires: "Full confirmed column list for every table whose schema was verified in this session — copy from `\d tablename` or equivalent, not from memory."
- V19A does not include the `\d trading_calendar` output. A cold-start developer investigating Incident #1 would want to see the exact column names, types, and nullability of `trading_calendar` — and would have to either trust the prose in §5.3 or pull the schema themselves.

**Severity is MINOR because:** The prose description is correct. The column names `open_time`, `close_time`, `is_open`, `trade_date` are all referenced consistently across the document. But the checklist specifically calls out "from memory" as an anti-pattern, and §5.3 reads like a from-memory description.

**Recommended fix:** Add the 4-to-6-line `\d trading_calendar` output under §5.3 showing exact column types and `not null` constraints (or absence thereof).

### Block 6 — API and Capture Contracts ⚠️ MODERATE FINDING (F-1)

| Checklist sub-item | V19A evidence | Status |
|---|---|---|
| API endpoint URL exact | §6.1 — `https://api.dhan.co/marketfeed/ltp` (idx_i), `https://auth.dhan.co/app/generateAccessToken`; §6.2 — `${SUPABASE_URL}/rest/v1/system_config?config_key=eq.dhan_api_token` | ✅ |
| Authentication method | `DHAN_API_TOKEN` header, TOTP-derived auth, apikey + service_role bearer | ✅ |
| Key parameters | `securities = {idx_i: [13, 51]}`, TOTP code 30s window, client_id, pin | ✅ |
| Rate-limiting observed + workaround | "1 token / 2 minutes (observed indirectly via runner crash diagnosis 11:26-12:26 — see §9 incident #2)" | ✅ |
| **Validated response values — actual numbers observed, not expected values** | §6.1 — "Specific values not logged because outage prevented capture; first post-fix capture at 12:30 IST recorded NIFTY 24,228 / SENSEX 78,612." | ⚠️ F-1 |

**Finding F-1 (MODERATE):** Block 6 API contract validation relies on one post-fix observation (12:30 IST) to represent a whole trading day's worth of API interaction. The pre-fix window has NO observed values because the bug prevented their capture.

- This is the **worst-case kind of Block 6 gap** the checklist is trying to prevent. Checklist language: "NOT 'it worked' but the specific values, labels, or counts that proved it worked."
- V19A has exactly ONE tuple of observed values: NIFTY 24,228 / SENSEX 78,612 at 12:30 IST.
- The self-audit (line 743) acknowledges this honestly: "Outage prevented full capture of values DURING the window; first post-fix capture values are recorded... The pre-outage state has no captured numbers because no captures occurred."

**Why MODERATE rather than MAJOR:** The honesty of disclosure is the mitigating factor. A rebuild-grade document that says "we tried to capture validated values, this is what we got, here is why we didn't get more" is very different from one that fabricates or omits. V19A does the right thing. But F-1 nevertheless reflects a real gap in the rebuild-grade claim — a cold-start developer investigating "how did the Dhan API behave on 2026-04-20?" gets one data point, not a characterization.

**Why this is not fixable retrospectively:** You cannot go back and capture values that were never captured. The mitigating data would be: aggregate row counts from `market_spot_snapshots` over the next 10 trading days showing the pipeline running normally (evidence of sustained post-fix capture working). This could be added as a forward-looking validation ledger that V19B/C can reference back to V19A.

**Recommended fix:** Add a §6.4 "Post-fix validation ledger" that cites cumulative row counts in `market_spot_snapshots` / `option_chain_snapshots` for 2026-04-20, 04-21, 04-22 trading windows as a check that the pipeline really resumed normal operation and didn't regress. This converts F-1 from "one post-fix data point" to "one data point + multi-day continuity evidence."

### Block 7 — Execution Chain / Pipeline Diagram ✅ PASS

| Checklist sub-item | V19A evidence | Status |
|---|---|---|
| Full ordered sequence for modified runners | §7.1 (pre-ENH-66 defective), §7.2 (post-ENH-66 fixed), §7.3 (ENH-68 env reload) — all three as ASCII flow diagrams | ✅ |
| What each step reads / writes | Inline in the diagrams | ✅ |
| Cadence | §7.3 "every 5 minutes (the runner cycle period)" stated explicitly | ✅ |
| Scheduler ownership — UNAMBIGUOUS | §7.4 — Windows Task Scheduler `MERDIAN_Intraday_Supervisor_Start` (08:55 IST) for merdian_start.py; ENH-66 propagation scripts via "their respective Task Scheduler tasks (see V19 §3.4 for mapping) or as supervisor children" | ⚠️ minor |
| Exact schtasks command if Task Scheduler | Not provided | ⚠️ minor |

**Auditor note on §7.4:** Scheduler ownership is "unambiguous" for `merdian_start.py` (named task, named time). For the 7-script propagation set, §7.4 defers to "V19 §3.4 for mapping" rather than duplicating the mapping inline. This is arguably acceptable (V19A is an appendix to V19, so referencing V19 is within the document family) — but strictly per checklist "scheduler ownership is unambiguous" reading, V19A itself doesn't contain the full mapping. The exact `schtasks` commands are likewise absent. A rebuild-grade document would inline the 7 task-to-script mappings rather than reference a parent.

**Not elevated to a finding because:** the checklist permits reference to parent documents (Block 1 "parent documents listed" implies parents are legitimate references). V19A is coherent in deferring scheduler detail to V19 §3.4.

**Optional improvement:** Inline the 7 task-to-script mappings in §7.4 to make V19A fully standalone.

### Block 8 — Validation Results ✅ PASS

| Checklist sub-item | V19A evidence | Status |
|---|---|---|
| One row per thing validated | §8.1 (3), §8.2 (2), §8.3 (4), §8.4 (1), §8.5 (3) — 13 validation checks across 5 sub-blocks | ✅ |
| PASSED / FAILED outcome | Column present with ✅ / ⏳ / ⚠️ markers | ✅ |
| Actual output observed — specific values | "NIFTY 24,228, SENSEX 78,612" (§8.1), "5 SUCCESS rows" (§8.3), "capture_spot_1m.py \| invocations=~30 \| success_pct=100.0 \| last_exit_reason=SUCCESS" (§8.3) | ✅ |
| For FAILED — root cause and fix | §8.2 has one ⏳ "NOT YET VALIDATED IN PRODUCTION" with reasoning why deferred | ✅ |
| For caveated — caveat stated | §8.2 row 2 is explicitly "cannot reproduce on 2026-04-20 without forcing a token expiry" | ✅ |
| §8.5 known gap | `.bak` files in registers/ flagged as known incomplete | ✅ |

**Auditor note:** §8.2 row 2 (ENH-68 token rotation caught within one cycle) is correctly marked ⏳ rather than ✅. A less disciplined document would have claimed "PASSED" based on logic review alone. V19A distinguishes code-review evidence from production-observation evidence explicitly. Credit.

### Block 9 — Known Failure Modes and Fixes ✅ PASS

| Checklist sub-item | V19A evidence | Status |
|---|---|---|
| Symptom | §9.1, §9.2, §9.3 all have "Symptom" rows with specific observable behavior | ✅ |
| Root cause | Each incident has explicit root-cause section | ✅ |
| Fix applied — exact fix, not description | §9.1 names commits `8f83859` + `ef477e6`; §9.2 names commit `b195499`; §9.3 names commit `bca369d` | ✅ |
| §9.4 Investigation-that-produced-no-fix | Included — ENH-67 latest_market_breadth_intraday dashboard staleness catalogued for later | ✅ |
| §9.5 Common-pattern reminder per checklist | Explicitly walks the checklist's common-missed list | ✅ |

**Auditor note:** §9 structure — three incidents + one dead-end investigation + checklist-reminder confirmation — is textbook. The checklist's "every error encountered, however trivial" rule is observed: incident #3 (tracked `.bak` files) is arguably cosmetic but is documented with the same Symptom/Root-cause/Fix structure as the two outages. This is the correct scope.

### Block 10 — Decision Log ✅ PASS

| Checklist sub-item | V19A evidence | Status |
|---|---|---|
| What was considered | §10.1 through §10.5 — 5 decisions, each with "Considered" row | ✅ |
| What was decided | Each decision has "Decided" row | ✅ |
| Why the alternative was rejected | Each decision has "Why alternative rejected" row, each one a full sentence | ✅ |
| Superseded models documented both old + new | §10.1 covers ENH-68 (tactical, shipped) vs ENH-74 (strategic, deferred). Both are on record. | ✅ |

**Auditor note on §10:** The checklist Block 10 is described as "the block that prevented rework in Appendix I." V19A's §10 meets that bar. §10.1 in particular is a strong example — a cold-start developer who encounters ENH-68 as `load_dotenv(override=True)` scattered in cycle loops could reasonably wonder "why is this tactical? why is it scattered?" — and §10.1 + §13.2 together answer that exactly.

### Block 11 — Stable vs Incomplete ✅ PASS

| Checklist sub-item | V19A evidence | Status |
|---|---|---|
| Two explicit lists, not mixed | §11.1 Stable / §11.2 Incomplete are structurally separate | ✅ |
| Stable items named | 7 items in §11.1, each one-line with specific commit hash or validation reference | ✅ |
| Incomplete with priority | §11.2 table has Priority column (HIGH / LOW / MEDIUM) | ✅ |
| Blocking? column | §11.2 has "Blocking?" column populated per row | ✅ |
| Architectural debt section | §11.3 "NOT addressed this session" — names AWS shadow runner + ExecutionLog test coverage | ✅ |

### Block 12 — Resume Checkpoint ✅ PASS

| Checklist sub-item | V19A evidence | Status |
|---|---|---|
| Settled facts (what not to re-open) | §12.1 — 8 settled facts, each a specific claim | ✅ |
| Next immediate task — one sentence | §12.2 — single sentence, names ENH-72 + reference impl pattern | ✅ |
| Resume prompt (paste-verbatim) | §12.3 — code block, includes last clean state (hash), preflight status, last session summary, this session goal, 9-script list, DO_NOT_REOPEN, relevant files/tables, governance | ✅ |

**Auditor note on §12.3:** The resume prompt is operationally complete. It includes the hash (`e95002b`), the 9-script next-session target enumerated, a DO_NOT_REOPEN list that prevents rework, and governance rules (`ast.parse()` validation, subprocess encoding). This is the highest-quality Block 12 possible given the checklist standard. The resume prompt was in fact used to bootstrap the V19B session (this is an authentic validation of Block 12).

### Block 13 — Functional Narration ✅ PASS

| Checklist sub-item | V19A evidence | Status |
|---|---|---|
| What it does — one sentence | §13.1 ENH-66, §13.2 ENH-68, §13.3 ENH-71, §13.4 Register unification — each has opening one-sentence statement | ✅ |
| Why it matters architecturally | Each has this section with concrete reasoning | ✅ |
| What it enables downstream | Each has "What it enables downstream" section naming the dependent future work | ✅ |

**Auditor note:** §13.3 ENH-71 is particularly strong — it names the specific class of bug the write-contract layer makes queryable ("silent-exit bugs that existing observability stack couldn't see") with an example SQL query showing exactly how to query for them. This is the narration that prevents "why did we build this?" rework.

### Quick Self-Audit — ✅ PASS with honest caveat

V19A's own self-audit (lines 740-747) anticipates my F-1 finding. Quoting V19A line 743: "Partially. Outage prevented full capture of values DURING the window; first post-fix capture values are recorded (NIFTY 24,228 / SENSEX 78,612 at 12:30 IST). The pre-outage state has no captured numbers because no captures occurred."

An auditor finding a gap that the document itself already flagged is less severe than an auditor finding a gap the document missed. V19A's self-audit is internally consistent.

---

## 3. Checklist-vs-Block Coverage Matrix

| Checklist Block | V19A § | Completeness | Gap |
|---|---|---|---|
| 1 Session Identity | §1.1–1.4 | 100% | none |
| 2 Before/After | §2.1–2.3 | 100% | none |
| 3 File Inventory | §3.1–3.4 | 95% | F-2 (count inconsistency in ENH-66 propagation list) |
| 4 Table Inventory | §4 | 90% | F-3 (row counts dated 2026-04-21 not 2026-04-20) |
| 5 Exact Schemas | §5.1–5.3 | 90% | F-4 (`trading_calendar` in prose, not `\d` output) |
| 6 API Contracts | §6.1–6.3 | 80% | F-1 (pre-fix observed values absent — unrecoverable) |
| 7 Pipeline Diagram | §7.1–7.4 | 95% | minor — scheduler mapping defers to V19 §3.4; exact schtasks absent |
| 8 Validation Results | §8.1–8.5 | 100% | none |
| 9 Failure Modes | §9.1–9.5 | 100% | none |
| 10 Decision Log | §10.1–10.5 | 100% | none |
| 11 Stable/Incomplete | §11.1–11.3 | 100% | none |
| 12 Resume Checkpoint | §12.1–12.3 | 100% | none |
| 13 Functional Narration | §13.1–13.4 | 100% | none |
| Self-audit | end of doc | 100% | self-acknowledges F-1 |

**Weighted overall:** ~96% rebuild-grade. Three MINOR gaps are clean to fix. One MODERATE gap (F-1) is unrecoverable but honestly disclosed.

---

## 4. Rebuild-Grade Reconstruction Test

The checklist's Quick Self-Audit asks: "Could a developer cold-start from this document without asking a single question?" I tested this by tracing four scenarios a rebuild-grade reader might attempt:

**Scenario A — Reconstruct what the outage was.** Can do from §1.1 + §2.2 #1 + §9.1. Timeline, symptom, root cause, fix all present. **PASS.**

**Scenario B — Rebuild `script_execution_log` from scratch.** §5.1 has verbatim DDL including indexes, check constraint, comments, view. A DBA could copy-paste this into psql and reproduce the table exactly. **PASS.**

**Scenario C — Understand why ENH-68 is "tactical" and what replaces it.** §10.1 + §13.2 + §11.2 row for ENH-74. Complete. **PASS.**

**Scenario D — Determine the exact file list affected by ENH-66 propagation.** This is where F-2 bites. §1.2 says 7, §2.3 says 6 "additional" + 2 "listed elsewhere" with no exact count reconciliation, §3.1 lists 9 code files total including non-ENH-66 work. Resolvable but requires cross-reference. **PASS with effort.** If this were F-2's severity elevated to MODERATE I'd fail Scenario D outright; at MINOR it's recoverable.

---

## 5. Specific Corrections Recommended for V19A v2

If a docx render is commissioned, the following edits would resolve all four findings:

| # | Change | Effort |
|---|---|---|
| F-1 | Add §6.4 "Post-fix validation ledger" with cumulative row counts across 04-20, 04-21, 04-22 for `market_spot_snapshots` / `option_chain_snapshots` as evidence of sustained capture. Cannot recover pre-fix values but can corroborate post-fix normalcy. | 20 min |
| F-2 | One canonical list of ENH-66-touched files with a single count. Reconcile §1.2, §2.3, §3.1 to agree on the count and the membership. | 15 min |
| F-3 | Either (a) add a parallel 2026-04-20 session-close row-count column to §4, or (b) add one-sentence caveat noting "row counts from 2026-04-21 16:30 IST; intervening morning added ~2,250 rows to hist_spot_bars_1m via Kite backfill (not V19A scope)." | 15 min |
| F-4 | Add `\d trading_calendar` verbatim output to §5.3 (4-6 lines). Pulls the `trading_calendar` schema from "prose description" to "copied from psql." | 10 min |

**Total effort to remediate:** ~60 minutes. All four findings are reasonably resolved before V19A→docx generation if a phase boundary triggers it.

---

## 6. Auditor's Overall Assessment

V19A is a rebuild-grade document in substance. A developer with no prior context can reconstruct the 2026-04-20 session end-to-end from V19A alone, with the single exception of Dhan API pre-fix observed values (F-1, unrecoverable).

**What V19A does unusually well:**

1. **Block 2 discovery documentation.** The 6 numbered discoveries in §2.2 are explicit, causally-linked, and include the non-obvious "this bug was hidden behind a different bug" framing that the checklist specifically flags as commonly missed. Better than average for this block.

2. **Full DDL inline (§5.1).** 133 lines of verbatim SQL including indexes, check constraint, column comments, and the rollup view definition. This is what rebuild-grade looks like for schema.

3. **Decision log rejection rationale (§10).** Every rejected alternative gets a full sentence of why, not a dismissive one-word "too slow" or "not needed." §10.1's ship-both-tactical-and-strategic rationale is the kind of entry that prevents future re-litigation.

4. **Resume prompt operationally validated (§12.3).** This prompt was used to bootstrap V19B. That is the highest possible proof that Block 12 works as the checklist intends.

5. **Self-audit honesty.** Line 743 acknowledges the pre-fix observed-values gap without hedging. An auditor catching F-1 is not catching V19A by surprise; V19A beat me to it.

**What V19A could do better:**

1. **Count consistency (F-2).** Cheap to fix, embarrassingly visible to a careful reader.

2. **Row-count temporal scope (F-3).** Using 2026-04-21 16:30 IST data is forgivable — the session was written 2026-04-22, well after the fact — but should be disclosed explicitly rather than as a footer note.

3. **`\d trading_calendar` verbatim (F-4).** The checklist is specific about "copy from `\d tablename`, not from memory." V19A mostly complies; the exception is the one table where non-compliance matters most (Incident #1's central data structure).

**Is V19A safe to promote to docx when a trigger fires?** Yes, with the 4 fixes from §5 applied first. The 60-minute remediation is proportionate to the stakes.

**Is V19A safe to leave as-is if no docx trigger fires?** Yes. The 4 findings are real but survivable. The rebuild-grade claim stands. No urgent rework required. This can wait for the next phase boundary.

---

## 7. Audit Trail

- **Document hashed at audit time:** /home/claude/v19_appendices/MERDIAN_AppendixV19A.md
- **Size:** 62,340 bytes, 753 lines
- **Read in full:** Yes (lines 1-150, 150-450, 450-753, 260-336, 528-675 in separate views)
- **Checklist applied:** MERDIAN Development Session Documentation Checklist (uploaded 2026-04-22) — 13 blocks + Quick Self-Audit
- **Cross-referenced:** merdian_reference.json v8 (commit 90b8c2d) for JSON deltas, CLAUDE.md v1.1 for governance rules, Documentation Protocol v3 for "rebuild-grade" definition (line 362-373)
- **Auditor bias disclosure:** I (Claude) also authored V19A earlier in this session. An auditor cannot be fully independent of a document they wrote; this audit is adversarial self-review rather than external review. A human independent audit by Navin remains advisable before any high-stakes use of V19A (external review, regulatory submission).

---

*Audit Report — MERDIAN Appendix V19A — 2026-04-22 — PASS with F-1 MODERATE + F-2/F-3/F-4 MINOR.*
