# S86 — footer-only audit of `CLAUDE.md`

> **Measure-only.** No edit was made to `CLAUDE.md` or to anything under `docs/`.
> Produced for **ADR-028 §4 AC2-note**, which owed *"a sweep for what else is
> footer-only"* before D3 moves history out.

## Method

**Scope.** The 6 `*CLAUDE.md vX.XX` footer lines + the `*Version footer history`
pointer + the 23 `## Session NN engineering discoveries` blocks — exactly what
ADR-028 D3 moves. Extracted mechanically; the complement is the rest of the file.

| region | bytes | share |
|---|---:|---:|
| in scope (moves under D3) | 185,517 | 56.6 % |
| complement (stays loaded) | 142,431 | 43.4 % |

**Extraction.** 84 `Codified as:` statements were pulled programmatically, plus 18
further claims adjudicated by hand (the six numbered Rules 18–23, named canonical
patterns, and the footer-specific facts). Working files: `in_scope.txt`,
`complement.txt`, `codified.txt`, `codified_scan.json`, `final.json`.

**Duplication test — two passes, deliberately.**

1. *Verbatim*: a 44-char sliding window of each normalised statement against the
   complement and 135 files under `docs/` (6.7 M normalised chars), with
   `CLAUDE_history.md` tracked separately since it is where this content would go.
2. *Fact-level*: short keys (`pythonw`, `OI-18`, `BSESEN`, …) to **locate candidate
   files**, then the surrounding sentence read and quoted.

**The bar for DUPLICATE is a quote.** A short-key hit means *topic present* and
proves nothing. An item counts as DUPLICATE only where a sentence in another file
states the **same instruction**, and that sentence is printed beside it below. Where
no such sentence could be quoted, the item defaults to RULE-LIKE — falsely calling a
rule duplicated is the failure that makes the split lose it.

**Known limitation.** Pass 1 cannot see a rule restated in different words; pass 2
only covers items pass 1 flagged plus those found by reading. A rule paraphrased
somewhere unindexed would read here as RULE-LIKE. That biases toward over-preserving,
which is the correct direction for this decision.

## Counts

### Adjudicated facts (102)

| class | count |
|---|---:|
| **RULE-LIKE** — an instruction an agent must follow | **59** |
| **DUPLICATE** — same instruction quotably stated elsewhere | 40 |
| **RECORD** — history/result, or an extraction fragment | 3 |

Split by how each was found:

| | codified (84) | hand-adjudicated (18) |
|---|---:|---:|
| RULE-LIKE | 48 | 11 |
| DUPLICATE | 33 | 7 |
| RECORD | 3 | 0 |

### Bytes

| | bytes | share of in-scope |
|---|---:|---:|
| **RULE-LIKE set (rule text only)** | **8,799** | **4.74 %** |
| all adjudicated claim text | 12,613 | 6.8 % |
| RECORD residual — narrative, measurements, session ledgers | 172,904 | 93.2 % |

So **8,799 bytes** of the 185,517 in scope is binding instruction. The other
**93 %** is record. Against ADR-028 D1's proposed 40 KB core that is
affordable — the RULE-LIKE set is ~21 % of the core budget — but it is **not currently
anywhere else**, so D3 cannot be executed as written without relocating it first.

---

## RULE-LIKE — the set that must survive D3

### A. Numbered rules defined ONLY inside discovery blocks

The load-bearing finding. `CLAUDE.md`'s Non-negotiable section defines Rules 0–19.
**Rules 18–23 in the discovery blocks are a separate series**, and live registers cite
them by number as authority.

**R-a · Rule 18 (B6) - patch scripts MUST be line-ending agnostic: count crlf vs bare_lf, match anchors in LF-space, restore predominant EOL via write_bytes**
  · source: Session 14
  · NUMBER COLLISION with Non-negotiable Rule 18 (trading_calendar trust-anchor). `write_eol` occurs in 0 files outside the block.

**R-b · Rule 19 (B7) - grep module-level imports before referencing sys.executable / os.path in endpoint or top-level scope**
  · source: Session 14
  · NUMBER COLLISION with Non-negotiable Rule 19 (never bash -x on .env).

**R-c · Rule 20 (B8) - bar_ts handling is ERA-CONDITIONAL at 2026-04-07; canonical `in_session_filter` era-aware helper**
  · source: Session 15
  · The COMPLEMENT's anti-pattern list points AT it - 'See Rule 20 (Session 15) for era-aware helper' - so that pointer DANGLES after the split. `in_session_filter` occurs in 0 files.

**R-d · Rule 21 - always pipe >5min scripts through Tee-Object; prefix PYTHONIOENCODING=utf-8 for box-drawing output**
  · source: Session 16
  · Cited as AUTHORITY by tech_debt.md ('the Tee-Object log per CLAUDE.md Rule 21, which mandates exactly this artefact') and docs/research/experiment_forensics_2026-09-11.md. Citations, not restatements.

**R-e · Rule 22 - a direction-asymmetric defect in one component obliges auditing its parallel component (same author, same era, same blind spot)**
  · source: Session 17
  · Cited as AUTHORITY by tech_debt.md TD-S76 row, docs/audits/coupling_audit_2026-09-07.md and System Map. Citations, not restatements.

**R-f · Rule 23 - mirror Active/Resolved block pattern for every TD/ENH lifecycle in the registers**
  · source: Session 20
  · No definition anywhere outside the block.

Two consequences, both measured:

- **Rule 18 and Rule 19 each name two different rules.** Non-negotiable 18 is the
  `trading_calendar` trust-anchor; discovery 18 is EOL-agnostic patch scripts.
  Non-negotiable 19 is *never `bash -x` on `.env`*; discovery 19 is the module-import
  grep. After D3 each number silently resolves to one meaning only.
- **Register citations become dangling references into an unloaded file.**
  `tech_debt.md` cites *"the `Tee-Object` log per CLAUDE.md **Rule 21**, which
  mandates exactly this artefact"*; a TD-S76 row cites *"**CLAUDE.md Rule 22**: a
  direction-asymmetric defect in one component means auditing its pair"*;
  `coupling_audit_2026-09-07.md`, `MERDIAN_System_Map.md` and
  `experiment_forensics_2026-09-11.md` do the same. These **cite** the rule rather
  than restate it, so they are dependencies, not duplicates. This is §D.40.6
  citation-decay one level up: not a line number that moved, a **rule** that moved.
- The complement itself points inward: *"See Rule 20 (Session 15) for era-aware
  helper."* That pointer survives D3; its target does not.

### B. Footer-only facts

**R-j · `bin/roq.sh` + the `merdian_ro` role are the session's own read-only SQL path**
  · source: footer v1.53
  · WORST CASE. The COMPLEMENT's only surviving mention is NEGATIVE - '`bin/roq.sh` is not a substitute', '`merdian_ro` cannot run it at all'. Deployment Topology S81.4 documents existence and scope ('a session tool, not a production component') but never says to use it. After the split, loaded context states only what the tool CANNOT do.

**R-k · `merdian_ro` reads 0 rows SILENTLY from 57 RLS-enabled relations - a 0-row result through roq.sh is not evidence of absence**
  · source: footer v1.53
  · Only in CURRENT_history.md / merdian_reference.json. This is the safety caveat that makes R-j usable; without it a 0-row read is trusted.

**This corrects ADR-028 §4 AC2-note.** It predicts B4 (`roq.sh`/`merdian_ro`) is
footer-only and will regress on the NO-FILE arm. Measured, it is worse and more
specific than that: the *artefact* is documented (Deployment Topology §S81.4), the
*instruction to use it* is footer-only, and **the complement's one surviving mention
is negative**. After D3, loaded context says `bin/roq.sh` is not a substitute and
`merdian_ro` cannot run the check — and says nothing about what either is for. An
agent reading only loaded context would conclude the tool is unusable. Absence would
be safer than that.

### C. Other canonical patterns with no quotable home

**R-g · Every market-hours Task Scheduler task MUST have DisallowStartIfOnBatteries=$false AND StopIfGoingOnBatteries=$false at creation time**
  · source: Session 21
  · Deployment Topology records 'battery flags' as a property of individual tasks, never as the creation-time obligation.

**R-h · 5-step audit pattern for 'type-X missing across detector' defects; step S5 (manual canonical shape scan in raw bars) is the load-bearing one**
  · source: Session 15
  · tech_debt.md names 'The 5-step audit S5 (canonical shape scan)' but never enumerates S1-S5.

**R-i · Pine v6 PDH/PDL canonical fetch idiom: `[high[1], low[1]]` + `lookahead=barmerge.lookahead_on`**
  · source: Session 31-B
  · Only in CURRENT_history.md / session_log_history.md. The 5 sibling walls ARE in the Enhancement Register; this 6th idiom is not.

### D. `Codified as:` rules with no quotable home (48)

Verbatim-absent from the complement and from all 135 `docs/` files. Ordered as
extracted; `[hist]` marks the few that survive in `CLAUDE_history.md` only — which is
itself unloaded, so they do not survive D3 in loaded context either.

1. after 2 hotfix rounds on the same feature, default to revert + re-attempt with full-spec design rather than incremental patching

2. every new Task Scheduler task MUST use `pythonw.exe` not `python.exe`, and existing tasks need migration

3. shared library functions should not encode caller-specific assumptions about input shape; either expose the assumption as a parameter or push the responsibility to the caller via well-formed input

4. for any cycle-level bug that involves runner ↔ detector interaction, build a full-day cycle simulator that exercises the actual production invocation pattern, not unit tests against the detector alone.

5. for any production component whose normal behavior is "produces N signals per day on average", build a watchdog that fires when N=0 for >2 consecutive days

7. at task creation time, every NEW Task Scheduler task that runs during market hours MUST have battery flags disabled

8. NEVER use cmd-style `copy` in PowerShell context. Always `Copy-Item -Force` for file copy in PS.

10. session_log line and Git commit must happen TOGETHER at session end, no exceptions

11. after 3 refuted hypotheses on the same incident, STOP investigating and design a controlled reproducer test instead.

12. NEVER apply `.replace(tzinfo=ZoneInfo("UTC"))` to a Kite `historical_data` row's `date` field

13. when one Dhan/Zerodha/Kite endpoint fails intermittently, do NOT assume the vendor is "down" — test the parallel endpoint

14. NIFTY weekly = Tuesday. SENSEX weekly = Thursday. Don't assume same expiry calendar across symbols.

15. for any AWS/SSH diagnostic Python that needs env vars, write a file via `cat >` then invoke

16. for any Dhan outage of >30 min duration, immediate recovery action = MALPHA Kite backfill of affected day

18. whenever an anti-pattern bug is fixed in one production code path, immediately `grep -rn` for the same shape across the codebase and treat all matches as the same defect

20. for any code change that modifies a data-source anchor, table column, or upstream dependency that production code reads, validate via ADR-008 replay over historical days BEFORE production change

21. when a TD's investigation surface is broad (multi-component, multi-vendor), re-examine the original incident's cross-script timeline before drafting hypotheses

23. for any production parameter whose hypothesis is falsified by retrospective evidence, the disablement vector is an env flag with default OFF, not code removal

25. OI-18 (unbounded order_by + limit returning oldest rows) is the canonical Supabase query bug class

26. for any gate guarded by a `not None` check on a writer-produced value, ship with a parallel diagnostic that asserts the writer is populating the value at expected cadence (post-cycle: ` SELECT COUNT(*) FILTER (WHERE col IS NULL) / COUNT(*) FROM table_X WHERE date = today` should approach 0)

27. ENH ship triggers can be data-availability-gated (e.g., "deploy after first cycle confirms data flowing") and that gate can be discharged out-of-band, including on Sunday non-trading days when smoke tests are sufficient

31. after any `ALTER TABLE` on a Supabase-served table, issue `NOTIFY pgrst, 'reload schema'` before smoke testing

32. when creating a shadow / replica table via `CREATE TABLE LIKE`, always use `INCLUDING ALL` (columns + constraints + indexes + defaults + comments)

33. for any backfill or batch operation that may have a non-zero per-row failure rate, log each row's identifying key + status code

40. `[hist]` when capturing command-line arguments to pass to a different shell context, explicitly whitelist syntactically-meaningful argument shapes

45. `[hist]` the live writer's source table is not the backfill writer's source table.

46. PostgREST 8s timeout is the binding constraint for ad-hoc queries against multi-million-row tables; if a query times out under default settings, the access pattern needs an index, not retry logic.

47. when comparing live vs backfill data sources, mismatches in magnitude (not direction) indicate unit-convention drift; investigate before threshold-tuning.

50. for major data-layer builds, design the holdout validation pipeline in the same plan as the build pipeline; execute the holdout split immediately after backfill completes; the validation verdict is the build's primary success criterion not a follow-up task.

53. reserved ENH IDs preserve their reservation across session-close updates; the reservation is communicated by explicit skip-and-document at next-ENH-filing time, not by retroactive consumption of the slot.

55. when a major methodology investment (Phase 0b, Phase 0c, similar) reaches a verdict, before propagating that verdict to production action, explicitly ask: "is this verdict on the same cohort that the production gate operates on at runtime?" If not, re-validate on the runtime cohort before acting

56. when measuring per-pattern edge on `signal_snapshots`, verify that pattern attachment is working at the expected rate against the zone-touch denominator BEFORE drawing conclusions about per-pattern WR

57. a gate's regime-classification edge direction must be verified on the live cohort the gate operates on, not inferred from theoretical mechanism (e.g., "LONG_GAMMA dealers damp moves" is a mechanism hypothesis; the live cohort's WR per regime is the test)

58. for any production gate whose empirical justification is challenged by new cohort evidence, the disablement vector is an env flag with default OFF + explicit `=0` documentation in `.env` (not absence-of-line)

60. any commit that adds new env flag dependencies must include `.env` change instructions in the commit message body or in CURRENT.md; AWS-side .env reconciliation is the operator's manual step post-pull

61. when a vendor table appears "sparse" for a use case, FIRST verify the table is the canonical source for that use case

62. a mathematical correctness check applied to the wrong source table can produce a more wrong answer than no check on the right source

63. when the operator's domain knowledge contradicts the framing of a diagnostic, the diagnostic is wrong

64. for chain-table reads at scale, prefetch per (strike, expiry, option_type) tuple over a timestamp range, not per (primitive, horizon) point

65. when vendor data carries the calendar, READ the calendar — do not derive it

68. DTE is not a single-direction lever. DTE=0 needs aggressive exit (gamma-driven, theta accelerates after favorable move plateaus)

74. when operator pushes back on diagnostic framing with verified domain knowledge, the framing is the bug, not the data

76. supabase-py REST has no DISTINCT primitive; any "find unique values for a key prefix" query over >100k rows MUST be a DB function via RPC, not a client-side paginated walk

77. PostgREST writes/reads share an 8s ceiling that does not bind direct DB sessions; long-running DDL or `EXPLAIN ANALYZE` always goes through Supabase SQL editor or psql, never the JS/Python SDK.

79. backfill writers must mirror the schema invariants of the live writer they're substituting for; "I'll insert raw rows and let the schema reject what doesn't fit" is a category error when the schema invariant is `NOT NULL` rather than `CHECK`

80. for any new vendor integration involving Indian indices, do a multi-variant identifier probe in the first 5 minutes — don't accept "0 rows returned" as definitive without probing canonical alternatives

81. adding columns to `ict_primitive_outcomes` is an O(N) cohort regeneration not an O(1) ALTER — budget recompute cost (S35 precedent: ~35 min for full 19,571 rebuild) when scoping schema-extension ENHs.

82. for ad-hoc code transfer to a single SSM-only host, multi-line nano paste is the canonical method; here-docs and base64 streaming are anti-patterns

---

## DUPLICATE (40) — with the quote that justifies it

### From the 84 codified statements (33)

**6.** for any pipeline that detects + upserts + recheck-conditions + expires, the only correct order is detect → upsert → recheck → expire
  · **tech_debt.md (TD-071)** — "the order detect -> upsert -> recheck -> expire is the only correct one because: (a) detect produces new candidates; (b) upsert writes ACTIVE for new + leaves existing untouched; (c) recheck flips status based on price action; (d) expire flips date-"

**9.** for `.bat` file edits in PS, use `(Get-Content path) -replace 'exit /b 0', "newcontent`r`nexit /b 0" | Set-Content path`
  · **tech_debt.md** — "the -replace command form appears verbatim"

**17.** any architectural decision that affects pipeline structure or data model MUST be drafted as `docs/decisions/ADR-NNN-<topic>.md` BEFORE the corresponding code change
  · **Doc Protocol v4 Rule 10** — "**mandatory** before code for signal-architecture changes, deployment-topology changes, schema-affecting changes, and any reversal of a"

**19.** `ict_htf_zones.source_bar_date` is timeframe-aware: W = week-start Monday, D = calendar date, 1H = hour bucket date
  · **MERDIAN_System_Map.md** — "`source_bar_date` semantics differ by timeframe (codified Session 25 from TD-078 closure): W = week-start Monday date; D = bar's calendar date; 1H = hour bucket date. When debugging "missing zone row" claims on this table, check the timeframe-aware convention before concluding the row is absent."

**22.** methodology decisions at thin data scales require graduated commitment, not uniform commitment
  · **ADR-009 (title line)** — "Calibration discipline: graduated-strictness holdout (Phase 1) -> rolling walk-forward (Phase 2 at Y2 close)"

**24.** before assigning priority to a "same anti-pattern in N scripts" claim, verify with URL-spy or equivalent runtime trace, not grep alone
  · **tech_debt.md** — "verbatim sentence match"

**28.** any Python module that parses ISO timestamps from Supabase MUST run cross-version-compatible code paths
  · **MERDIAN_Assumption_Register.md + tech_debt.md** — "verbatim sentence match"

**29.** Phase 0 closure exercises (data backfills, schema reconciliations, replay validations) are defect-discovery surfaces
  · **session_log_history.md** — "verbatim sentence match [history register]"

**30.** for any architectural separation that depends on flag/parameter wiring (shadow vs production, dry-run vs live, test vs prod), verify the wiring is exercised end-to-end at deployment time
  · **session_log_history.md + tech_debt.md** — "verbatim sentence match"

**34.** when an unexpected production process is discovered, file as "unaudited" first (S1-S2), investigate, then close as filed-in-error if intentional
  · **tech_debt.md** — "verbatim sentence match"

**36.** `.env` changes require consumer restart, full stop. Filing rule for any new `.env`-mutation runbook: include a "Step Nd — Restart consumers" mandatory clause.
  · **CASE-2026-05-14-breadth-cascade-token-and-bloat.md** — "verbatim sentence match"

**37.** for any table whose retention horizon is shorter than its read-window-floor, TRUNCATE is the canonical recovery; DELETE is structurally unsafe.
  · **CASE-2026-05-14-breadth-cascade-token-and-bloat.md** — "TRUNCATE is the canonical recovery; DELETE is structurally unsafe"

**38.** any pg_cron job introduced to production must be accompanied by either (a) a polling check that surfaces failures within 24 hours (Telegram alert or dashboard widget), or (b) an explicit entry in the operator session-start checklist.
  · **CASE-2026-05-14 + MERDIAN_Deployment_Topology.md** — "verbatim sentence match"

**39.** build expected-time series in UTC at actual UTC times** (e.g., `'2026-05-14 03:45:00+00'::timestamptz` for 09:15 IST trading-start) **and let the join handle TZ conversion in output formatting only.
  · **CASE-2026-05-14-spot-gap-backfill.md** — "verbatim sentence match"

**41.** when a tried fix produces no observable change after one verified attempt, falsify the hypothesis before retrying.
  · **CASE-2026-05-14-breadth-cascade-token-and-bloat.md** — "verbatim sentence match"

**42.** Doc Protocol v4 candidate Rule N (Task Scheduler audit cadence)
  · **MERDIAN_Deployment_Topology.md** — "verbatim sentence match"

**43.** when retiring code or renaming a literal, deliberately preserve grep-discoverability of the old name in adjacent documentation
  · **tech_debt.md** — "verbatim sentence match"

**44.** when a TD claims a data limitation, verify against current table state before designing around the limitation.
  · **MERDIAN_Assumption_Register.md + tech_debt.md** — "verbatim sentence match"

**48.** a definitive FAIL verdict on a Phase 0b dimension means abandoning that dimension as a gate, not retrying with different parameters.
  · **CURRENT_history.md + session_log_history.md** — "verbatim sentence match [history registers only]"

**51.** holdout-validation on the build cohort is necessary but not sufficient — the cohort-translation pre-flight on the live runtime cohort is the final transferability check
  · **MERDIAN_Assumption_Register.md + MERDIAN_Enhancement_Register.md** — "'cohort-translation pre-flight' present as the named discipline"

**52.** any change that adds/removes/restructures table columns triggers Rule 10 ADR mandatory — even if "just columns" on a research-tier table
  · **Doc Protocol v4 Rule 10** — "mandatory before code for ... schema-affecting changes ..."

**54.** any signal-time gate whose go/no-go decision was derived from a cohort other than the live signal-snapshots cohort requires live-cohort re-validation before production deployment
  · **CURRENT_history.md + MERDIAN_Assumption_Register.md** — "verbatim sentence match"

**59.** for any file deployment to AWS that is not already on disk, the canonical path is git commit Local → push → pull AWS
  · **CLAUDE.md Non-negotiable Rule 1 (COMPLEMENT)** — "Edit only in Local. AWS receives code via `git pull` - never direct edits except BREAK_GLASS"

**66.** median PnL universally negative on a cell that has 80%+ spot WR is a source-table smell, not an edge property
  · **merdian_reference.json + session_log_history.md** — "verbatim sentence match"

**67.** trade M5 OBs at formation, not at retest. The retest paradox was real, not a sampling artifact.
  · **ADR-011** — "OB retest paradox documented at D.14.3 confirmed at option-PnL level - trade M5 OBs at formation, not retest"

**69.** capture and selection are distinct problems with distinct solutions
  · **CLAUDE.md settled section (COMPLEMENT) + merdian_reference.json** — "capture and selection are distinct problems with distinct solutions"

**70.** for ICT retest entries the SL anchor measures thesis failure (close-through zone invalidation on 5m), not microstructure noise
  · **MERDIAN_Decision_Index.md** — "verbatim sentence match"

**71.** ADR-012: **SL must anchor to spot zone-invalidation on 5m-close-through
  · **ADR-012 + CLAUDE.md settled (COMPLEMENT)** — "the stop-loss is anchored to spot zone-invalidation on 5m-close-through - NOT to option premium decay"

**72.** when a backfill cohort's coverage suddenly stops at a calendar boundary, the first diagnostic is "what tier of data lives on each side of the boundary?" — not "what failed?" The transition may be architectural (storage path mismatch) not operational (ingest failure).
  · **merdian_reference.json** — "verbatim sentence match"

**73.** a cohort definition that produces a smaller-than-expected N is not evidence prior research is wrong; it may be evidence the prior research measured a different (correctly-defined) cohort, and the current cohort definition is more restrictive
  · **merdian_reference.json** — "verbatim sentence match"

**75.** when a data-tier transition is identified, audit ALL surfaces that depend on the source table, not just the headline column
  · **MERDIAN_Assumption_Register.md D.17.1** — "Chain-data tier transition at 2026-04-01 UTC boundary is a three-surface architectural concern (chain prices, expiry calendar, ATM strike picking), not one - ... each must be routed separately by the writer"

**78.** the historical chain source-of-truth pivots from vendor (`hist_option_bars_1m`) to MERDIAN-ingest (`historical_option_chain_snapshots`) at 2026-04-01 UTC
  · **MERDIAN_Assumption_Register.md D.17.1** — "(same D.17.1 row - it names the 2026-04-01 UTC boundary explicitly)"

**83.** Breeze qualifies as architectural fallback for any future single-day chain outage; long-term graduation to canonical historical backfill source proposed as ADR-013 + ENH-109 pending broader validation cycles
  · **MERDIAN_Deployment_Topology.md + merdian_reference.json** — "verbatim sentence match"

### Hand-adjudicated (7)

**D-a · Pine v6 ergonomic catalog, 5 of 6 walls**
  · **MERDIAN_Enhancement_Register.md** — "descending for-loop `by -1` requirement, if/else type-compat CE10235, `var int` global mutation CE10088 wrapping in array.from(0), `close[1] + lookahead_off` double-shift bug on per-TF close fetches, `max_boxes_count=500` hard cap GC silently swallowing 1428 of 1928 zones"

**D-b · patched-copy deploy pattern**
  · **merdian_reference.json** — "patched-copy pattern with _PATCHED.py -> dry-run -> live -> verify -> rename + _PRE_S30.py backup"

**D-c · Doc Protocol v4 Rule 7 amendment - byte-level splices, not full-file rewrites**
  · **MERDIAN_Decision_Index.md (S74 row)** — "DECIDED - register updates are applied as byte-level splices with fail-loud assertions, not full-file rewrites."

**D-d · KillSignal=SIGINT on merdian-wsfeed.service**
  · **MERDIAN_Decision_Index.md + CURRENT_history.md** — "present in 7 files"

**D-e · get_premarket_ref window re-anchored to [09:00:00, 09:14:59]**
  · **MERDIAN_System_Map.md + coupling_audit_2026-09-07.md** — "present in 5-7 files"

**D-f · ADR-025 parity count BUILT = 2 of 14**
  · **ADR-025 + CLAUDE.md settled (COMPLEMENT)** — "present"

**D-g · v3 patch canon - read_bytes()+decode('utf-8-sig'), write_bytes(text.encode())**
  · **CLAUDE.md Anti-patterns (COMPLEMENT) + merdian_reference.json** — "present in complement"

---

## RECORD

Three of the 84 extracted statements are not facts an agent follows:

- **35.** a session-mandate of "verify yesterday's patches in live cycle" routinely produces a P0 closure in <20 minutes of sessio — advisory session-budgeting observation, not an instruction
- **49.** D.14.1 + D.14.2 + D.14.3 + D.14.4 + D.14.5** in Assumption Register; **ENH-100/101/102 — extraction fragment (a cross-reference list), not a fact
- **84.** Rule 19; rotation is operator-owned and outstanding as TD-S71-NEW-11 — extraction fragment (tail of Rule 19 prose)

The RECORD *bulk* is not itemised: it is the 172,904 B (93 %) of
narrative residual — incident reconstructions, measurement tables, session ledgers,
withdrawn-claim registers. All of it is history by construction, and D3 moving it is
the uncontroversial part of the proposal.

---

## Findings beyond the classification

**F1 — a standing rule amendment never reached its owning protocol.** Footer v1.51
announces *"Doc Protocol v4 Rule 7: register updates are applied as byte-level
splices with fail-loud assertions, not full-file rewrites."* The amendment's content
**is** recorded in `MERDIAN_Decision_Index.md` (S74 row), so it classifies DUPLICATE.
But `docs/operational/MERDIAN_Documentation_Protocol_v4.md` Rule 7 still reads
*"`CURRENT.md` is the live session resume"*, and the string `splice` occurs **0
times anywhere in `docs/operational/`**. An agent following `CLAUDE.md`'s
source-of-truth map to the Doc Protocol gets the **unamended** rule under that
number. Two documents define Rule 7 differently — the ADR-020 contract-collision
shape, where each file is coherent alone. Independent of the split; owed regardless.

**F2 — a scope boundary D3 does not cover.** `## v1.31 (Session 41, 2026-06-01)`
(lines 976–998) is a version footer in substance but matches neither the
`*CLAUDE.md vX.XX` pattern nor `Session NN engineering discoveries`, so **D3 as
written leaves it in place** — 22.8 KB across `### S41 settled-decisions` and `### S41
operational findings`. Either fold it into D3 explicitly or state that it stays.

**F3 — a mapping artefact in `section_map.out`.** Lines 1012–1051 hold the S58–S67
settled-decision bullets, which sit *after* the footer block and outside any heading
of their own, so `map_claude.py` attributes them to `### S41 operational findings`
(reported at 18,695 B / 54 lines — the largest class-(e) section). They are class (c)
settled decisions. They are **not** in D3's scope and stay loaded; the section map's
class totals are skewed by roughly their size.

**F4 — the complement is still 2.5× the binding limit.** At
142,431 B / 505 lines it is over the documented
200-line target by ~2.5×, so D3 alone does not satisfy AC1. ADR-028 D4 already says
this (*"necessary and not sufficient"*); this is the measured confirmation.

## Owed before D3 executes

1. Relocate the 8,799 B RULE-LIKE set into loaded context — the core file,
   a path-scoped rule, or a skill — **before** the history move, not after.
2. Resolve the **Rule 18 / Rule 19 number collisions**; two rules cannot share a
   number once one of them is in an unloaded file.
3. Re-point the register citations of Rules 20–23 (`tech_debt.md`,
   `coupling_audit_2026-09-07.md`, `MERDIAN_System_Map.md`,
   `experiment_forensics_2026-09-11.md`) at wherever those rules land.
4. Fix the `roq.sh` negative-only residue (R-j/R-k), or loaded context will
   actively mislead rather than merely omit.
5. Rule the F2 scope boundary on `## v1.31`.
6. File F1 — the Rule 7 amendment that never reached Doc Protocol v4.
