# ADR-028 split — phase 1: placement proposal

> **PROPOSAL ONLY. No file in the repository has been created, moved or edited.**
> Lives outside the tree at `~/s86_test/s86_split/`. The docs corpus stays frozen at
> `6bba0ce` until the after-arm completes, apart from the split itself.
>
> Inputs: `footer_only_audit.md` (59 RULE-LIKE), `section_map.out`, the ADR-028 draft.
> Mechanism facts verified against `code.claude.com/docs/en/memory.md` this session,
> not recalled — see §0.

## 0. Mechanism constraints, quoted

Everything below depends on these, so they are quoted rather than paraphrased:

- **`paths` frontmatter is the whole interface.** *"`paths` is the only field Claude
  Code reads from a rule; any other field is ignored without an error."* Accepts a
  YAML list or a comma-separated string. Frontmatter is stripped before loading.
- **Unscoped rules do not help.** *"Rules without `paths` frontmatter are loaded at
  launch with the same priority as `.claude/CLAUDE.md`."*
- **Scoped rules fire on reads, not topics.** *"Path-scoped rules trigger when Claude
  reads files matching the pattern, not on every tool use."*
- **Skills are the only load-on-demand-by-topic mechanism.** *"For task-specific
  instructions that don't need to be in context all the time, use skills instead,
  which only load when you invoke them or when Claude determines they're relevant."*
- **The binding size target is lines.** *"target under 200 lines per CLAUDE.md file"*;
  hard skip at 4 MiB. **And there is a combined budget**: *"You also see a warning
  when files that are each within that length add up past a combined limit at session
  start. Each CLAUDE.md, rules file, and `@path` import counts as a separate file."*
  So the rule files below are **not** free — §2 keeps each one small for that reason.
- **`@path` imports are useless for size.** *"imported files load at launch."*

*(Unavailable to us: `/doctor prompt-audit` requires v2.1.283+ and we are pinned at
2.1.277 per AC2-note-2. The audit it would perform is done by hand in §5.)*

---

## 1. Core `CLAUDE.md` outline with line budget

| # | Section | lines | bytes | Source / note |
|--:|---|--:|--:|---|
| 1 | Title + What this project is | 7 | 800 | verbatim from current lines 1-15, trimmed |
| 2 | Read order at session start | 11 | 700 | verbatim; add rules/ + skills/ + CLAUDE_history.md |
| 3 | The single source of truth map | 15 | 1,500 | verbatim table + 2 new rows |
| 4 | Common operations -> runbooks | 8 | 900 | pointer + 3 highest-frequency rows; full table -> skill |
| 5 | **Non-negotiable Rules 0-19 (VERBATIM)** | 43 | 9,976 | measured: current section is 43 lines / 9,976 B |
| 6 | Session-invariant rules (from the audit) | 26 | 5,200 | the RULE-LIKE items that bind regardless of open files |
| 7 | Settled bullets classed CORE in §5 | 21 | 14,250 | **measured, not estimated** — 21 bullets, the Rule-0-family epistemics |
| 8 | Anti-patterns - universal subset | 13 | 3,200 | 13 of 33; the file-scoped 20 -> path-scoped rules |
| 9 | Rule 13 gate (contamination registry) | 4 | 500 | 3-line gate + pointer; detail -> rules/research.md |
| 10 | Session contract | 10 | 700 | verbatim table |
| 11 | Session-end checklist | 14 | 850 | verbatim; the procedure -> skills/doc-close |
| 12 | Quick environment reference | 12 | 520 | verbatim |
| 13 | Pointers block | 10 | 1,200 | rules/, skills/, CLAUDE_history.md topic index, registers |
| 14 | Version footer (1 line) | 2 | 400 | current session only; predecessors -> CLAUDE_history.md |
| | **TOTAL** | **196** | **40,696** | |
| | *AC1 bound* | *200* | *40,960* | |
| | *headroom* | *4* | *264* | |

**AC1: PASS on both bounds, but only just** — 196 lines (4 spare, 98 % of the line bound) and 40,696 B (264 spare, 99 % of the byte bound).

The two largest items are both measured rather than estimated, and together they are
59 % of the byte budget:

- **Non-negotiable Rules 0-19 — 43 lines / 9,976 B**, from `section_map.out`.
- **The 21 CORE-class settled bullets — 14,250 B**, from the §5 classification.

**This headroom is thin enough to be a finding, not a comfort.** Two sections that are
fixed by their own nature (a non-negotiable rule list, and the epistemic rules that
cost the most to learn) consume most of the budget, and the estimate for the remaining
eleven sections is exactly that — an estimate. **If any of them overruns, the
overrun lands on decision (b):** the settled block has to be *trimmed*, not merely
relocated. A plan that reported comfortable headroom here would be the easy-to-compute
number standing in for the one that binds.

### 1a. What §6 of the core carries — the session-invariant RULE-LIKE items

These are the audit's RULE-LIKE items that bind **regardless of which files are open**,
so a path-scoped rule cannot carry them: nothing would trigger it.

| Audit ID | Rule, as it will read in core | Why core and not scoped |
|---|---|---|
| **R-j + R-k** | `bin/roq.sh` + the `merdian_ro` role are how this session runs its own read-only SQL — **and `merdian_ro` reads 0 rows silently from 57 RLS-enabled relations, so a 0-row result is not evidence of absence.** | A session tool. No file read triggers it, and the audit's worst case: the only surviving mention in loaded context today is *negative*. |
| R-d (Rule 21) | Pipe any run over ~5 min through `Tee-Object`; prefix `PYTHONIOENCODING=utf-8`. | Applies to an invocation, not a file. |
| R-e (Rule 22) | A direction-asymmetric defect in one component obliges auditing its parallel component. | A reasoning obligation; the parallel file is not open yet — that is the point. |
| #11 | After 3 refuted hypotheses on one incident, stop and build a controlled reproducer. | Debugging discipline, file-agnostic. |
| #1 | After 2 hotfix rounds on one feature, revert and re-attempt with a full-spec design. | Same. |
| #63 + #74 | When the operator's domain knowledge contradicts the framing of a diagnostic, **the framing is the bug** — re-investigate it before defending it. | Fires on a conversational turn, not a file. |
| #18 | After fixing an anti-pattern in one path, `grep -rn` the shape repo-wide and treat every match as the same defect. | The sibling files are by definition not open. |
| #21 | When a TD's surface is broad, re-examine the incident's cross-script timeline before drafting hypotheses. | Debugging discipline at hypothesis time. |
| #23 | A parameter whose hypothesis is falsified is disabled by an env flag with default OFF, never by code removal. | A disposition decision, not a file edit. |
| #55 | Before propagating a verdict to production action, ask whether it was measured on the cohort the gate runs on. | Methodology gate at a decision point. |
| #61 + #62 | Verify a table is the canonical source for a use case before calling it sparse; a correct check on the wrong table is more wrong than no check. | Fires before any file is opened. |
| #65 | When the vendor data carries the calendar, read it — never derive it. | A design instruction, pre-file. |
| #10 | The `session_log` line and the git commit happen together at session end; a session that ends uncommitted is the next session's first action. | Session lifecycle. |
| #20 | A change to a data-source anchor, column or upstream dependency is validated via ADR-008 replay **before** production change. | Pre-change. |
| #53 | Reserved ENH IDs keep their reservation; communicate by explicit skip-and-document. | ID hygiene at filing time. |
| #27 | A ship gate may be data-availability-gated and discharged out-of-band. | Release discipline. |
| #5 | For any component whose normal output is N-per-day, a watchdog fires when N=0 for >2 days. **Silent zero is an alarm condition.** | Applies to the system, not a file. |

That is **20 of the 59 RULE-LIKE items**, presented as 18 rows because R-j/R-k and #63/#74 each read as one rule. The remaining **39** are file-scoped and go to §2.

---

## 2. Path-scoped rule files

Each carries `paths:` frontmatter in the verified syntax. Kept deliberately small
because of the combined-limit warning quoted in §0.

### `.claude/rules/python-writers.md`

```yaml
---
paths:
  - "**/*.py"
  - "patch_*.py"
  - "scripts/**/*.py"
---
```

**RULE-LIKE items carried:**
- **R-a — Rule 18 (B6)**, patch scripts are line-ending agnostic — **MOVED VERBATIM**, text unchanged including the defective `encode("utf-8")` (per constraint: TD-S86-NEW-4 is **not** fixed in the split, because prompt B2 measures it)
- **R-b — Rule 19 (B7)**, grep module-level imports before referencing them
- **R-c — Rule 20 (B8)**, era-conditional `bar_ts` + the `in_session_filter` helper
- **R-h** — the 5-step audit pattern (S1-S5, with S5 the load-bearing step)
- #3 shared libraries do not encode caller-specific input assumptions
- #4 cycle-level runner/detector bugs need a full-day cycle simulator
- #26 a `not None` gate ships with a writer-population diagnostic
- #40 whitelist argument shapes when re-emitting into another shell
- #79 backfill writers mirror the live writer's schema invariants
- #33 log each row's key + status in any batch/backfill with a non-zero failure rate

**Settled bullets carried:** the `ast.parse`-alone-insufficient bullet; fail-open/fail-soft visibility; the recency-floor-ships-with-the-latency-fix bullet.

**Note:** The largest rule file. `**/*.py` is broad, but the alternative is core.

### `.claude/rules/sql-views.md`

```yaml
---
paths:
  - "sql/**/*.sql"
  - "**/*.sql"
---
```

**RULE-LIKE items carried:**
- #25 OI-18 is the canonical unbounded-`order_by`+`limit` bug class
- #31 `NOTIFY pgrst, 'reload schema'` after any `ALTER TABLE`
- #32 `CREATE TABLE LIKE ... INCLUDING ALL`
- #46 a PostgREST timeout needs an index, not retries
- #76 no DISTINCT in supabase-py — use a DB function via RPC
- #77 the 8 s ceiling does not bind direct DB sessions
- #81 column adds on `ict_primitive_outcomes` are O(N) recompute

**Settled bullets carried:** `COMMENT`/`GRANT` ship as live statements in `sql/`; ALTER DEFAULT PRIVILEGES is the remediation that holds; a latest-run-scoped count is only comparable at equal `ts`; a CTE referenced once is inlined — verify `loops=1`.

**Note:** ADR-021 and ADR-025 D2 both bind here.

### `.claude/rules/registers.md`

```yaml
---
paths:
  - "docs/registers/**/*.md"
  - "docs/decisions/**/*.md"
  - "docs/**/*.json"
---
```

**RULE-LIKE items carried:**
- **R-f — Rule 23**, mirror Active/Resolved blocks per TD/ENH lifecycle
- #60 an env-flag commit carries its `.env` instructions

**Settled bullets carried:** byte-level splices not full-file rewrites (Rule 7 amendment); newest-first registers are cited by entry ID not line; cross-document §N carries its document.

**Note:** Fires on opening any register — which is most sessions, but not all.

### `.claude/rules/schedulers.md`

```yaml
---
paths:
  - "**/*.bat"
  - "**/*.ps1"
  - "**/crontab*"
  - "deploy/systemd/**"
  - "docs/registers/aws_crontab*.txt"
---
```

**RULE-LIKE items carried:**
- **R-g** — market-hours tasks need both battery flags disabled at creation
- #2 new Task Scheduler tasks use `pythonw.exe`
- #7 battery flags at creation time (the codified form of R-g)
- #8 `Copy-Item -Force`, never cmd `copy`, in PowerShell
- (note: the `.bat`-edit rule #9 is DUPLICATE per the audit — tech_debt.md carries it verbatim — so it is cited here, not restated)

**Settled bullets carried:** `SHELL=/bin/bash` as crontab line 1; monitors must not share the failure chain; `crontab - < file`; a service whose normal shutdown is `failed`.

**Note:** Note: the Windows scheduler is all-Disabled per Topology §S76.A, so #2/#7/R-g may be **expired rules**. Flagged, not dropped — see §6(d) note.

### `.claude/rules/data-access.md`

```yaml
---
paths:
  - "**/*.py"
  - "docs/registers/MERDIAN_Data_Inventory.md"
---
```

**RULE-LIKE items carried:**
- #12 never `.replace(tzinfo=UTC)` on a Kite `historical_data` date
- #13 test the parallel endpoint before concluding the vendor is down
- #14 NIFTY weekly = Tuesday, SENSEX = Thursday
- #45 the live writer's source table is not the backfill writer's
- #47 a magnitude-only mismatch is unit drift
- #80 multi-variant vendor identifier probe in the first 5 minutes
- #64 per-tuple range prefetch for chain reads

**Settled bullets carried:** both hist bar tables are IST-clock-as-UTC, zero shift; time-range fetchers bind BOTH ends; `ltp` is the last trade, not a price; NULL is a gap, never a zero.

**Note:** Overlaps `python-writers.md` on `**/*.py` deliberately: both load, and the docs state rules are concatenated, not overridden.

### `.claude/rules/research.md`

```yaml
---
paths:
  - "docs/research/**/*.md"
  - "experiment_*.py"
  - "docs/registers/MERDIAN_Experiment_Compendium*.md"
---
```

**RULE-LIKE items carried:**
- #50 design the holdout with the build, not after
- #56 verify pattern attachment against the zone-touch denominator first
- #57 verify regime edge on the live cohort, never from mechanism
- #58 a challenged gate is disabled by env flag with an explicit `=0`
- #68 DTE is not a single-direction lever
- **Rule 13** contamination-registry detail (the gate stays in core)

**Settled bullets carried:** a win rate above ~70 % is a defect report; ADR-009 graduated strictness; detectors must be provable to read only bars at or before entry.

**Note:** ADR-009 is the governing document; this file is the working checklist.

### `.claude/rules/pine.md`

```yaml
---
paths:
  - "**/*.pine"
  - "generate_pine_overlay*.py"
---
```

**RULE-LIKE items carried:**
- **R-i** — PDH/PDL fetch idiom `[high[1], low[1]]` + `lookahead_on`
- the 5 sibling Pine v6 walls (DUPLICATE in the Enhancement Register, restated here because the register is not loaded when a `.pine` file is open)

**Settled bullets carried:** Pine offsets are time-anchored, never `bar_index`-anchored; `max_boxes_count=500` and GC'd-box mutation is a silent no-op.

**Note:** Smallest file. Justified because Pine's failure modes are silent-render.

### `.claude/rules/ops-shell.md`

```yaml
---
paths:
  - "**/*.sh"
  - "bin/**"
---
```

**RULE-LIKE items carried:**
- #15 write a file via `cat >` for SSH diagnostics, never a heredoc
- #82 multi-line nano paste for SSM code transfer; here-docs and base64 are anti-patterns

**Settled bullets carried:** never trace a script that sources `.env`; the Rule 19 safe forms.

**Note:** Rule 19 itself stays in core — it is a hard rule, and the hazard precedes opening any `.sh` file.

**Coverage check — computed, and it aborts this document if it fails.** **20** RULE-LIKE items in core (§1a) + **39** across the eight rule files and the runbooks skill = **59**, against the audit's **59**. The emitting script asserts set-equality with the audit's own `final.json` classification, that no item is placed twice, and that nothing placed here is absent from the RULE-LIKE set.

That check earned its keep on the first run: the hand-written version of this section
claimed *"21 + 38 = 59"* while actually placing **10 items the audit had classed
DUPLICATE** and leaving **#23 and #33 unplaced**. The count was asserted, not computed,
and it was wrong in both directions at once.

---

## 3. Skills

Two. Skills are the only mechanism that loads **by topic** rather than by file read,
so they take the multi-step procedures — which is exactly what the docs say to do:
*"If an entry is a multi-step procedure ... move it to a skill."*

### `.claude/skills/doc-close/SKILL.md`

**Trigger description:** *"Run MERDIAN's end-of-session documentation close: update
CURRENT.md, session_log.md, tech_debt.md, merdian_reference.json, the Enhancement
Register and the Decision Index, then commit with the `MERDIAN: [OPS]` prefix. Use
when the user says the session is ending, asks to close out, or asks to file TDs or
update the registers."*

**Contents:** the session-end checklist expanded into steps; Doc Protocol v4 Rule 3
(full-file no-crunch) and the Rule 7 splice discipline with a worked
assertion-gated example; Rule 5 numbering and next-free-ID resolution by reserved-row
method; Rule 12 project-knowledge re-upload as a second destination; the per-register
update triggers. Core keeps only the 14-line checklist as the index.

### `.claude/skills/merdian-runbooks/SKILL.md`

**Trigger description:** *"Find and follow the MERDIAN runbook for a recurring
operation — token rotation, runner restart, backfill, hash mismatch, DhanError 401,
calendar rows, emergency stop, disk-full lockout. Use when the user asks how to
perform an operational procedure, or when a runner, token or feed needs recovery."*

**Contents:** the full 10-row runbook index table currently in core; the rule that a
`⚠ NAVIN: FILL` marker is discharged in the same session it is needed; the rule that
a missing runbook is created from `RUNBOOK_TEMPLATE.md` before proceeding; **#16**
(a >30 min Dhan outage recovers via MALPHA Kite backfill). Core keeps a 3-row table
of the highest-frequency operations plus the pointer.

**Not proposed as skills:** anything in §1a. A skill that must fire on every session
regardless of prompt is a core rule wearing a skill's clothes, and its trigger
description would have to be *"always"*.

---

## 4. What moves verbatim to `CLAUDE_history.md`

Append-only, in existing document order, no content edits:

| Item | Count | Bytes | Note |
|---|--:|--:|---|
| `## Session NN engineering discoveries` blocks | 23 | 163,492 | D3 as written |
| `*CLAUDE.md vX.XX` footer lines | 6 | 20,912 | D3 as written |
| `*Version footer history` pointer line | 1 | 1,084 | superseded by the new pointer |
| **`## v1.31 (Session 41, …)` + its two `###` subsections** | 1 | **22,819** | **D3 MISSES THIS** — see below |
| Settled bullets classed `register:` in §5 | see §5 | see §5 | only after their register is confirmed to carry them |

**The `v1.31` gap.** `## v1.31 (Session 41, 2026-06-01)` at current lines 976-998 is a
version footer in substance but matches **neither** D3 pattern — not `*CLAUDE.md vX.XX`
and not `Session NN engineering discoveries`. Under D3 as written it **stays in core**,
at 22,819 B across `### S41 settled-decisions` (4,124 B) and `### S41 operational
findings` (18,695 B). It must be named explicitly in D3 or it silently survives.

**A mapping caveat carried from the audit (F3).** The `### S41 operational findings`
figure of 18,695 B in `section_map.out` is **overstated**: current lines 1012-1051 hold
the **S58-S67 settled-decision bullets**, which sit after the footer block outside any
heading of their own and are therefore attributed to that section by `map_claude.py`.
Those bullets are class (c) and are dispositioned in §5, **not** moved here. Anyone
executing this plan must split lines 976-1011 from 1012-1051 by hand.

---

## 5. The settled-decisions block, per bullet

**133 top-level bullets, 91,195 B** (the block) / 90,819 B (the bullets themselves).
**83 cite a register ID; 50 cite none** — the latter matter most, because a
bullet with no register ID has no other home by construction.

| disposition | bullets | bytes |
|---|--:|--:|
| **CORE** | 21 | 14,250 |
| **rule** | 55 | 28,063 |
| **register** | 57 | 48,506 |
| **total** | 133 | 90,819 |

Per rule file:

- `data-access.md` — 19 bullets
- `research.md` — 15 bullets
- `sql-views.md` — 13 bullets
- `schedulers.md` — 6 bullets
- `python-writers.md` — 2 bullets

**Method and its limits, stated because the counts depend on it.** Disposition is
assigned by keyword precedence — universal-epistemic first (a Rule-0-family bullet is
CORE wherever else it might fit), then file-class, then register-of-record. It is a
**first pass, not an adjudication**: a bullet spanning two classes lands in the higher
one, and the `register:` class takes the *first* ID in the bullet, which is usually but
not always the authority. Every row is reviewable below. **Rows marked `⚠` have no
register ID and are not CORE** — they are the ones most likely mis-placed, and the ones
where a wrong call loses content.

| # | disposition | IDs cited | bullet (first 150 chars) |
|--:|---|---|---|
| 1 | register:ADR-004 | ADR-004, ADR-004, ADR-004 | ✅ **ADR-004 Amendment C (S76, 2026-09-10) — `valid_from` is the confirming bar's CLOSE.** The §4 field list's *"typically `source_bar_ts` + 1 TF"* (`A |
| 2 | rule:schedulers.md | TD-NEW-7, TD-S69-NEW-1, ADR-023 | ✅ **A register entry written from inference decays differently from one written from measurement.** Session 71 audited five carried items and **four** |
| 3 | CORE | ADR-006 | ✅ **A verification method can only find what it enumerates.** The S70 ADR-006 audit counted *scheduled tasks* and concluded migration was complete; a  |
| 4 ⚠ | rule:python-writers.md | — | ✅ **A green run against the wrong artefact proves nothing, and looks identical to success.** Session 71 produced five: box tests against unpushed code |
| 5 | CORE | — | ✅ **The accepted set and the storage key are different decisions.** Widening `capture_cas_close.py`'s bar-slot assertion to `{15:29, 15:34}` was right |
| 6 | rule:python-writers.md | ADR-023 | ✅ **A recency floor is calibrated against the CONSUMER's cadence, never the writer's.** ADR-023 D1's 15-minute default was derived from the GEX writer |
| 7 | CORE | ENH-81 | ✅ **Fail-soft must be visible in the artefact it degrades.** A `57014` timeout on `v_gex_strike_pin_zone` made `generate_pine_overlay.py` emit a Pine  |
| 8 ⚠ | rule:data-access.md | — | ✅ **`ltp` is the last trade, not a price.** On expiry morning, far-ITM SENSEX puts printed ~40 points **below intrinsic** — not an executable quote, j |
| 9 ⚠ | register:— | — | ✅ **Anchors are built from bytes, never from rendered output.** Patch anchors taken from a PowerShell console dump failed `count==0`: the console had  |
| 10 ⚠ | rule:sql-views.md | — | ✅ **Mixed-EOL files exist and normalising them is a silent rewrite.** A predominant-EOL detect-and-restore — correct for single-convention files — wou |
| 11 ⚠ | rule:data-access.md | — | ✅ **A service whose normal shutdown is `failed` cannot be health-checked by its state.** `merdian-wsfeed` catches SIGTERM, so every trading day ends i |
| 12 | CORE | — | ✅ **One upstream cause can present as N independent failures.** The 08-25 health check reported 3 FAIL + 1 WARN across `market_ticks`, `market_breadth |
| 13 ⚠ | rule:data-access.md | — | ✅ **Alerting that fires and is not read is a delivery problem, not an instrumentation gap.** The 08-18 outage was recorded three times in `ws_feed_zer |
| 14 ⚠ | rule:data-access.md | — | ✅ **Never propose removing infrastructure before enumerating what depends on it.** `snapd` was 1.3 G and looked like dead weight on a headless box. `a |
| 15 | CORE | ADR-020 | ✅ **Absence is not a verdict** — a shared gate must resolve a missing `trading_calendar` row through the V18E rule engine (`trading_calendar.get_sessi |
| 16 ⚠ | rule:sql-views.md | — | ✅ **Time-range fetchers must bind BOTH ends.** A `gte`-only PostgREST filter is an open-ended forward window: harmless on a `today` run (the newest ro |
| 17 | rule:sql-views.md | ENH-116 | ✅ **Store the raw anchor, not the derived scalar.** `front_expiry` (a date) beats a computed `dte` (an int): the view derives DTE *and* cycle-progress |
| 18 | CORE | ADR-018, ENH-116 | ✅ **NULL is a gap, never a zero.** When a recency guard makes a lens *abstain* (ADR-018 D2), rendering the NULL as 0 states a fact that was never meas |
| 19 ⚠ | rule:data-access.md | — | ✅ **`git status` clean ≠ file tracked.** A `.gitignore` pattern (`*.txt` at line 44) silently swallowed a committed-by-intent manifest with **no untra |
| 20 ⚠ | register:— | — | ✅ **EC2 git auth is an SSH deploy key, not a PAT.** PATs expire and 0-byte `~/.git-credentials`, silently breaking the box's push/pull (twice: S67, S6 |
| 21 ⚠ | rule:research.md | — | ✅ Options-only framework (Experiment 2b, 2026-04-12) |
| 22 ⚠ | register:— | — | ✅ Capital ceiling ₹50L / ₹25L / ₹2L (Appendix V18F v2) |
| 23 ⚠ | rule:research.md | — | ✅ T+30m exit timing (Experiment 8/14b/15, multiple confirmations) |
| 24 | register:ENH-37 | ENH-37 | ✅ 1H zones in MEDIUM context (ENH-37, validated) |
| 25 ⚠ | rule:research.md | — | ✅ BEAR_OB AFTERNOON → HARD SKIP (Signal Rule Book v1.1, 17% WR) |
| 26 ⚠ | register:— | — | ✅ ICT pattern detection on 5m bars (Research Sessions 4-5, 2026-04-17) |
| 27 | register:ENH-42 | ENH-42 | ✅ ENH-42 WebSocket — DEFERRED post-Phase 4, do not build now |
| 28 ⚠ | rule:data-access.md | — | ✅ OpenItems Register closed (2026-04-15) |
| 29 ⚠ | register:— | — | ✅ D-06 signal-consumer concerns (resolved earlier; do not rebuild regret log) |
| 30 ⚠ | rule:sql-views.md | — | ✅ **Compendium replicates** (Exp 15 re-run 2026-04-27, Session 10) — BEAR_OB ~92% WR, BULL_OB ~84%, MEDIUM context ~77%, combined +193.4% return. The  |
| 31 ⚠ | rule:data-access.md | — | ✅ **F1 (ICT zone time_zone classification) SHIPPED** (2026-04-27, Session 10) — `fix_ict_time_zone_utc.py` converted UTC→IST before time-bucket assign |
| 32 ⚠ | rule:sql-views.md | — | ✅ **F2 (1H OB threshold tuning) REJECTED** (Exp 29 v2, 2026-04-26, Session 10) — full-year sweep over {0.15, 0.20, 0.25, 0.30, 0.40}% confirmed curren |
| 33 ⚠ | rule:sql-views.md | — | ✅ **Path A retracted** (Session 10) — the framing "stop pretending ICT is the edge" was wrong. Compendium replicates. Do not re-introduce Path A under |
| 34 ⚠ | rule:research.md | — | ✅ **Naked intraday PDH/PDL sweeps have no edge** (Exp 34, Session 11) — WR=11.1% (PDH), 1.8% (PDL) at T+60m. ~0.73 events/session — normal mean revers |
| 35 ⚠ | rule:research.md | — | ✅ **PDL DTE<3 next-week CE = SKIP** (Exp 35D, Session 11) — T+1D WR=42.9%. EOD bounce is mechanical expiry pinning, not institutional. Fades next day. |
| 36 ⚠ | rule:research.md | — | ✅ **BEAR_OB AFTERNOON + PO3_BEARISH = 33.3% WR** (Exp 40, Session 11) — the distribution move is already done by AFTERNOON on bearish-bias sessions. H |
| 37 ⚠ | rule:research.md | — | ✅ **BULL_OB MIDDAY + PO3_BULLISH = 30.3% WR** (Exp 40, Session 11) — premature. Bullish accumulation doesn't resolve until AFTERNOON London open. Hard |
| 38 ⚠ | rule:research.md | — | ✅ **NIFTY BULL_OB AFTERNOON + PO3_BULLISH = 50% WR** (Exp 40, Session 11) — no edge on NIFTY for this signal. SENSEX only (73.7%). Do not route NIFTY  |
| 39 ⚠ | rule:research.md | — | ✅ **Current-week PE beats next-week PE for PDH DTE<3** (Exp 41, Session 11) — NIFTY mean +46% vs +20%, SENSEX mean +125% vs +68%. Current-week capture |
| 40 ⚠ | rule:research.md | — | ✅ **Entry at T+0 (rejection bar close) always beats waiting** (Exp 41, Session 11) — waiting 1 bar hurts across all edges and both symbols. Never wait |
| 41 | register:TD-017 | TD-017, ENH-71 | ✅ **TD-017 CLOSED** (Session 11 extension, 2026-04-28) — `build_ict_htf_zones.py` now scheduled daily 08:45 IST via `MERDIAN_ICT_HTF_Zones_0845` Task  |
| 42 | register:TD-030 | TD-030 | ✅ **TD-030 CLOSED** (Session 11 extension, 2026-04-28) — `recheck_breached_zones()` added; runs AFTER all upserts (ordering bug fixed Session 13). 72  |
| 43 | register:TD-031 | TD-031 | ✅ **TD-031 CLOSED** (Session 11 extension, 2026-04-28) — OB/FVG patterns written unconditionally; breach filter retained for PDH/PDL proximity only. D |
| 44 | CORE | TD-032, ENH-35 | ✅ **TD-032 dashboard opt_type wrong framing SETTLED** — root cause is NOT 'dashboard hardcodes direction off pattern_type'. Root cause IS `build()` re |
| 45 | register:ENH-75 | ENH-75 | ✅ **ENH-75 SHIPPED** (Session 13, 2026-04-29) — PO3 session bias detection live. `detect_po3_session_bias.py` running Mon-Fri 10:05 IST. `po3_session_ |
| 46 | register:ENH-76 | ENH-76 | ✅ **ENH-76 SHIPPED** (Session 13, 2026-04-29) — BEAR_OB MIDDAY 11:30-13:30 IST gated on PO3_BEARISH. 88.2% WR (Exp 40). Wired in `build_trade_signal_l |
| 47 | register:ENH-77 | ENH-77 | ✅ **ENH-77 SHIPPED** (Session 13, 2026-04-29) — BULL_OB AFTERNOON SENSEX 13:30-15:00 IST gated on PO3_BULLISH. 73.7% WR (Exp 40). NIFTY hard skip (50% |
| 48 ⚠ | rule:research.md | — | ✅ **Exp 42 DONE** (Session 13, 2026-04-29) — BEAR_OB MIDDAY occurs in 72.5% of all sessions. Unfiltered WR=48%, EV negative. PO3_BEARISH is the rare g |
| 49 | register:ENH-85 | ENH-85, ENH-85 | ✅ **ENH-85 direction lock REVERTED** (Session 13) — PO3 session lock patch built and reverted. Needs Exp 43 (Signal Direction Stability) before re-imp |
| 50 | register:ENH-78 | ENH-78 | ✅ **ENH-78 SHIPPED** (Session 14, 2026-04-30) — DTE<3 PDH sweep current-week PE rule live in `build_trade_signal_local.py`. Guarded by `po3_session_bi |
| 51 | register:ENH-84 | ENH-84 | ✅ **ENH-84 SHIPPED** (Session 14, 2026-04-30) — Dashboard 🔄 REFRESH ZONES button + `/refresh_and_download_pine` endpoint. With hotfix for `sys.executa |
| 52 | register:ENH-86 | ENH-86 | ✅ **ENH-86 v1 SHIPPED** (Session 14, 2026-04-30) — WIN RATE legend extended to 7 columns with EV + N. Live rows for E4/E5 added at top. v2 (BLOCKED/AL |
| 53 | register:TD-044 | TD-044, ENH-76, ENH-76 | ✅ **TD-044 CLOSED** (Session 14, 2026-04-30) — ENH-76/77 local var / `out` dict drift fixed. Three-site sync in `build_trade_signal_local.py`. Side ef |
| 54 | CORE | TD-038 | ✅ **TD-038 EXIT AT IST PATCH SHIPPED** (Session 14, 2026-04-30) — `merdian_signal_dashboard.py` `card()` now converts UTC→IST for the static EXIT AT l |
| 55 ⚠ | register:— | — | ✅ **Breach detection ordering FIXED** (Session 13) — `recheck_breached_zones()` now runs after all `upsert_zones()` calls. Upsert no longer overwrites |
| 56 | register:ADR-008 | ADR-008, ENH-93, ADR-008 | ✅ **ADR-008 Accepted** (Session 24, 2026-05-09) — Replay is a parallel-pipeline sandbox for what-if signal experiments — comparison of two replay runs |
| 57 | register:ADR-005 | ADR-005, ADR-006 | ✅ **Phase α Q1 ANSWERED** (Session 25, 2026-05-10) — Zone validity model = (a) pure price-based canonical with timeframe-tiered fallback intraday-only |
| 58 | register:ADR-006 | ADR-006 | ✅ **Phase α Q2 ANSWERED** (Session 25, 2026-05-10) — AWS migration scope = (a) capture/derived split with four-stage decomposition. Capture stage (`ma |
| 59 | register:ADR-006 | ADR-006, TD-080, ADR-006 | ✅ **Phase α Q3 ANSWERED** (Session 25, 2026-05-10) — Sequencing: token reliability FIRST, then ADR-006 actions. Investigate `refresh_dhan_token.py` fa |
| 60 | register:ADR-009 | ADR-009 | ✅ **Phase α Q4 ANSWERED** (Session 25, 2026-05-10) — Calibration discipline = graduated-strictness holdout (operator deferred to architect recommendat |
| 61 | register:TD-097 | TD-097, ENH-96, ENH-96 | ✅ **TD-097 RESOLVED + ENH-96 SHIPPED same-session** (Session 25, 2026-05-10) — Dashboard pre-open status URL-encoding bug producing 0% accuracy widget |
| 62 | register:TD-080 | TD-080, ADR-006 | ✅ **TD-080 REFRAMED** (Session 25, 2026-05-10) — Original framing "Dhan option chain endpoint reliability" narrowed to "AWS Dhan token refresh failure |
| 63 | register:TD-078 | TD-078, TD-070, TD-070 | ✅ **TD-078 RESOLVED** (Session 25, 2026-05-10) — TD-070 v2 multi-week BULL_OB lookback verified via SQL. The apparent missing Apr-13 row was a schema- |
| 64 | CORE | ADR-008 | ✅ **`MERDIAN_PreOpen` (Local 09:05 IST) DISABLED** (Session 25, 2026-05-10) — Auction-window writer disposed via PowerShell `Disable-ScheduledTask`, d |
| 65 | register:ADR-006 | ADR-006, TD-080 | ✅ **Topology §9 Q1 + Q2 CLOSED** (Session 25, 2026-05-10) — §9 Q1: post-market 16:00 dual-write empirically confirmed across 2026-05-04 → 2026-05-08 ( |
| 66 | register:ADR-002 | ADR-002, ENH-80, ENH-84 | ✅ **ADR-002 v2 ACCEPTED** (Session 27, 2026-05-11) — Market structure philosophy v2 supersedes v1. Six v1 principles preserved (P1 zones, P2 force, P3 |
| 67 | register:TD-NEW-2 | TD-NEW-2, TD-097, TD-101 | ✅ **TD-NEW-2 RESOLVED** (Session 27, 2026-05-11) — `flip_level` regression starting 2026-05-08 across both NIFTY and SENSEX (3+ days of stuck values ~ |
| 68 | register:TD-NEW-3 | TD-NEW-3 | ✅ **TD-NEW-3 RESOLVED** (Session 27, 2026-05-11) — `net_gex` stored ~10³ too large vs operational Crore convention; gamma engine had been writing raw  |
| 69 | rule:sql-views.md | ADR-002, ENH-80 | ✅ **Phase 0a §3 sign-convention audit PASS** (Session 27, 2026-05-11) — MERDIAN `gamma_metrics.net_gex` sign matches external source-material across 2 |
| 70 | CORE | TD-NEW-2, TD-NEW-3, TD-NEW-12 | ✅ **TD-NEW-2 + TD-NEW-3 P0 verification PASS — live cycle** (Session 28, 2026-05-12 09:25 IST) — S28 P0 mandate closed in ~10 minutes after market ope |
| 71 | register:TD-NEW-12 | TD-NEW-12 | ✅ **TD-NEW-12 RESOLVED** (Session 28, 2026-05-13) — Shadow architecture not implemented for `gamma_metrics_shadow`. AWS `compute_gamma_metrics_local.p |
| 72 | register:TD-NEW-4 | TD-NEW-4, TD-NEW-12, TD-NEW-12 | ✅ **TD-NEW-4 RESOLVED** (Session 28, 2026-05-13) — `dte` payload field in `compute_gamma_metrics_local.py::upsert_gamma_metrics()` was computed as `(d |
| 73 | register:TD-NEW-13 | TD-NEW-13, TD-NEW-4 | ✅ **TD-NEW-13 RESOLVED** (Session 28, 2026-05-13) — Python stdlib `datetime.fromisoformat()` not portable across runtime versions for variable-microse |
| 74 | register:TD-NEW-5 | TD-NEW-5, TD-NEW-6, TD-NEW-8 | ✅ **TD-NEW-5 + TD-NEW-6 + TD-NEW-8 RESOLVED** (Session 28, 2026-05-13) — Three S28 config / scheduler fixes: (5) `run_ict_htf_zones_daily.bat` patched |
| 75 | register:TD-NEW-13 | TD-NEW-13, ENH-84 | ✅ **P1 broken-window `gamma_metrics` backfill CLOSED** (Session 28, 2026-05-13) — 587/587 rows across 2026-05-08 + 2026-05-11 (NIFTY 149+144=293 rows  |
| 76 | register:ENH-84 | ENH-84, ENH-85, ENH-84 | ✅ **P2 Enhancement Register formal filing: ENH-84 + ENH-85 PROPOSED** (Session 28, 2026-05-13) — Deferred from S27 by operator consent. `MERDIAN_Enhan |
| 77 | rule:sql-views.md | TD-NEW-7 | ✅ **MALPHA catalogued as third environment in Deployment Topology** (Session 28, 2026-05-13) — Topology §1 expanded to three-environment side-by-side  |
| 78 | register:TD-NEW-10 | TD-NEW-10, TD-NEW-11 | ✅ **`merdian_order_placer.py` catalogued as MERDIAN-AWS-only service** (Session 28, 2026-05-13) — Phase 4B Order Placer (HTTP server port 8767, Dhan-I |
| 79 | register:ADR-012 | ADR-012, ENH-107, TD-S34-NEW-4 | ✅ **ADR-012 ACCEPTED** (Session 34, 2026-05-24) — Spot-anchored stop-loss doctrine for ICT retest entries; supersedes informal Compendium-era 30%+ pre |
| 80 ⚠ | rule:research.md | — | ✅ **Universal big-move-day capture rate 99.2% (118/119)** (Session 34, 2026-05-24) — MERDIAN's ICT primitive layer sees every ≥1% intraday move struct |
| 81 | rule:research.md | ENH-108 | ✅ **Selection problem articulated** (Session 34, 2026-05-24) — Selection (which active zone of 50+ fires today) is the unsolved problem; capture (does |
| 82 | register:ENH-108 | ENH-108, ADR-004, TD-S34-NEW-4 | ✅ **ENH-108 PROPOSED** (Session 34, 2026-05-24) — Second-touch / N-touch retest detection on ICT primitives. ADR-004 §10 records only `first_retest_ts |
| 83 | register:TD-S34-NEW-4 | TD-S34-NEW-4, TD-080-adjacent | ✅ **TD-S34-NEW-4 FILED — `hist_option_bars_1m` post-2026-04-01 coverage gap (vendor → MERDIAN-ingest tier transition)** (Session 34, 2026-05-24). Two- |
| 84 | register:ADR-015 | ADR-015, ADR-014, ENH-80 | ✅ **ADR-015 ACCEPTED** (Session 37, 2026-05-25) — Per-strike GEX schema v2: 12-column minimum-sufficient-statistic on `gex_strike_snapshots` `(run_id, |
| 85 | register:ADR-014 | ADR-014, ADR-015 | ✅ **ADR-014 SUPERSEDED same session by ADR-015** (Session 37, 2026-05-25) — Original 16-column `gex_strike_snapshots` schema with `gamma` (single) + ` |
| 86 | register:ADR-016 | ADR-016, ENH-83, ENH-81 | ✅ **ADR-016 PROPOSED, build deferred** (Session 37, 2026-05-25) — Parameter calibration pattern: temporal-immutable `merdian_parameters` table `(id, k |
| 87 | rule:research.md | ADR-001, ENH-55, ADR-009 | ✅ **GEX-as-context-not-gate** (Session 37, 2026-05-25) — Operator framing: *"Meridian doesn't need anymore gates. It's already gating everything."* ME |
| 88 | register:ENH-80 | ENH-80, ENH-80, ADR-015 | ✅ **ENH-80 per-strike GEX writer SHIPPED** (Session 37, 2026-05-25) — `compute_gamma_metrics_local.py` extended via `patch_s37_enh80_writer_v2.py` (ma |
| 89 | register:ENH-81 | ENH-81, ENH-83, ADR-016 | ✅ **ENH-81 Positioning Landscape SHIPPED** (Session 37, 2026-05-25) — Three SQL views materializing PIN zone + ACCEL zone + dealer flow sim from `gex_ |
| 90 | register:ENH-110 | ENH-110 | ✅ **ENH-110 Phase 1 SHIPPED** (Session 39, 2026-05-27) — Consolidated Marketview Build Phase 1 live at `http://13.63.27.85/marketview` via Lovable → G |
| 91 | register:ENH-83 | ENH-83, ADR-016, ADR-016 | ✅ **ENH-83 SHIPPED** (Session 39, 2026-05-27) — Calibration console + temporal-immutable `merdian_parameters` table live. Lovable auto-scaffolded the  |
| 92 | register:TD-S39-NEW-1 | TD-S39-NEW-1 | ✅ **Lovable auto-grant safety REFUTED — RLS triplets require pre-deploy anon-grants audit** (Session 39, 2026-05-27) — D.21.1 REFUTED + TD-S39-NEW-1 S |
| 93 | register:TD-S39-NEW-1 | TD-S39-NEW-1, TD-S39-NEW-3 | ✅ **Anon-key-in-public-repo trust model VALIDATED** (Session 39, 2026-05-27) — D.21.2 VALIDATED. Lovable auto-committed `.env` containing live Supabas |
| 94 | CORE | TD-S39-NEW-4 | ✅ **IMDSv2 attached-SG check mandatory before AWS SG edits — REFUTED operator-console-name memory** (Session 39, 2026-05-27) — D.21.3 REFUTED. AWS net |
| 95 ⚠ | rule:schedulers.md | — | **Orchestrator crontab syntax:** `cd /path && source .env && flock -n /lock timeout 90 python3 script.py` (cd and source BEFORE flock, relative paths  |
| 96 | register:ADR-006 | ADR-006 | **Volatility table canonical:** `volatility_snapshots` per ADR-006 Derived layer; write target for both LOCAL (production) and AWS (non-shadow after S |
| 97 ⚠ | rule:schedulers.md | — | **Cron graceful degradation:** Script exit_code=0 on known failures OK (404 table missing), but log the condition even on success for operational visi |
| 98 ⚠ | rule:schedulers.md | — | **Cron `SHELL=/bin/bash` is mandatory as crontab line 1 on AWS (S53):** cron defaults to `/bin/sh` (dash), which lacks the `source` builtin — every `c |
| 99 ⚠ | rule:data-access.md | — | **Monitors must not share the failure chain of what they watch (S53):** all four S52 monitors used the same `source .env` prefix as the capture layer  |
| 100 ⚠ | rule:schedulers.md | — | **Live ingest cron form is UNQUOTED `bash run_ingest.sh NIFTY FULL` (S53):** `run_ingest.sh` self-sources `.env`; do NOT reintroduce S49's single-quot |
| 101 | rule:data-access.md | TD-S54-NEW-1 | **Upserts can mask per-symbol write loss (S54):** the volatility insert→upsert(on_conflict=symbol,ts) correctly stopped 409 crashes but converted SENS |
| 102 | register:ADR-018 | ADR-018, TD-S57-NEW-1, ENH-30 | ✅ **ADR-018 ACCEPTED** (Session 57, 2026-06-19) — Breadth-feed supervision model + signal-subsystem disposition. (D1) `ws_feed_zerodha.py` runs under  |
| 103 | register:ENH-07 | ENH-07, TD-S58-NEW-1, ENH-07 | ✅ **ENH-07 A CLOSED — no-op, flat r** (Session 62, 2026-07-01) — The basis-implied risk-free rate is a no-op on two grounds and stays closed. (1) *Emp |
| 104 | rule:sql-views.md | ADR-001 | ✅ **Expiry-day 0-DTE flat-vol net_gex is numerically UNRECONSTRUCTIBLE intraday → live-sourced, not reconstructed** (Session 62, 2026-07-01) — As T→0  |
| 105 | rule:data-access.md | ENH-116 | ✅ **Pre-existing-table discovery discipline; `hist_gamma_metrics` is the canonical historical gamma series** (Session 62, 2026-07-01) — Always check f |
| 106 ⚠ | rule:data-access.md | — | ✅ **iv is the master key — lean sidecar schema is correct** (Session 62, 2026-07-01) — In the historical per-strike Greeks sidecar (`hist_option_greek |
| 107 ⚠ | rule:data-access.md | — | ✅ **"Correct-and-slower beats fast-and-subtly-wrong" — abandon divergent optimizations, never loosen the gate** (Session 62, 2026-07-01) — A `--fast`  |
| 108 | rule:data-access.md | TD-S62-NEW | ✅ **Cross-engine (StockMojo) parity isolates bugs** (Session 62, 2026-07-01) — Where two independent GEX engines agree, the structure is real; where t |
| 109 | register:ENH-116 | ENH-116, ADR-018, ENH-115 | ✅ **ENH-116 Ambient Environment Intelligence BUILT + DEPLOYED end-to-end (backend) — the nightly “what kind of day is it” verdict now writes, accrues, |
| 110 ⚠ | rule:data-access.md | — | ✅ **`ast.parse` alone does not prove a Python edit is safe — a `str_replace` insertion can silently eat a `def` header and leave an orphaned body that |
| 111 ⚠ | rule:data-access.md | — | ✅ **Marketview graduated from an internal `http://13.63.27.85/marketview` IP page to a public, TLS-terminated, Google-auth-gated app at `https://marke |
| 112 | rule:sql-views.md | ADR-017, ENH-116 | ✅ **Marketview v5 is a multi-page terminal, not a single scroll — pages split by the question each answers (Session 64).** Six content pages behind a  |
| 113 | rule:sql-views.md | ADR-001 | ✅ **Dhan EOD historical publish-lag is expected, not a stall — `compute_date_window()` (T−1, 220-day) is correct; don't patch the window to force a mi |
| 114 | rule:data-access.md | TD-S65-NEW-1 | ✅ **The EOD coverage guard's denominator is the active-universe / latest-EOD-date ticker count (~1,159), not the nominal ~1,385 universe; staleness is |
| 115 | rule:data-access.md | ENH-117 | ✅ **OAuth credential rotation via a *new* Google client changes BOTH `client_id` and `client_secret` — and the exposure closes only when the OLD clien |
| 116 | rule:schedulers.md | ADR-006 | **A month-long "frozen table" whose writer was declared "unidentified/decoupled" is almost always a scheduler/orchestration gap after an environment m |
| 117 ⚠ | rule:data-access.md | — | **A builder gated on a coverage threshold inside a cursored-ingest loop must treat the gate-miss as non-fatal, not a loop-stop (S67, `f5b9afd`).** `ru |
| 118 ⚠ | rule:data-access.md | — | **The active equity universe is 1,385 (dhan_scrip_map is_active + dhan_security_id not null); the true EOD coverage ceiling is 97.83%, not 100% or ~1, |
| 119 | rule:sql-views.md | TD-S66-NEW-5 | **Dhan EOD candle publish lag (1–3 trading days) means the day's frontier fills gradually — a "stuck at T-1" frontier is expected, not a bug, and self |
| 120 | CORE | — | ✅ **A relation that cannot produce a REAL EMPTY LIST is excluded from a measurement as UNMEASURABLE BY THIS METHOD — by measurement, never by name and |
| 121 | register:ADR-024 | ADR-024 | ✅ **GEX zone anchors are net-sign selections: PIN is the max net-long-gamma strike, ACCEL its mirror the max net-short; their offsets — above spot for |
| 122 | register:ADR-025 | ADR-025, ADR-021, TD-S79-NEW-3 | ✅ **Parity is a set of dispositions, not a count of builds — a layer counts as BUILT only when it RENDERS, and a layer outside the fourteen does not c |
| 123 | CORE | TD-S37-03, ENH-126, ADR-025 | ✅ **A `sql/` file that carries only the view body is not a rebuild source, and a rebuild from it fails SILENTLY.** Measured S81 across all three S79 G |
| 124 | CORE | CASE-2026-09-22-, TD-S81-NEW-1 | ✅ **Fixing every instance does not fix the mechanism, and a fix with no watcher has a half-life.** S39 revoked `anon` privileges on thirteen surfaces  |
| 125 | rule:research.md | TD-S79-NEW-12, ADR-025, ADR-025 | ✅ **A "latest snapshot" selector must never order by `created_at`.** `ingest_option_chain_local.py` computes `snapshot_ts` ONCE and reuses it, so ever |
| 126 | CORE | — | ✅ **On a latest-run-scoped view, a count taken at one moment cannot be compared with a count taken at another.** The S81 anon/editor pairing read NIFT |
| 127 | CORE | — | ✅ **An expected value handed to a verifier must be COMPUTED, and computed from the artefact — never recalled.** S81 published an expected `comment_len |
| 128 | CORE | — | ✅ **Derive a gate's threshold from the quantity's scale BEFORE measuring, and write the derivation beside the number.** Four S83 gates failed on this  |
| 129 ⚠ | rule:sql-views.md | — | ✅ **A view CTE referenced once is INLINED (PostgreSQL ≥ 12), and a ranking or window CTE joined against mis-estimated CTEs can then run once per outpu |
| 130 | CORE | — | ✅ **A role-scoped check runs in ONE execution, and selects `current_user` beside the counts.** The Supabase SQL editor opens a **new session per run** |
| 131 | CORE | TD-S84-NEW-1, TD-S81-NEW-11 | ✅ **A line citation is stable only into a file that will NOT be edited above the cited line — so newest-first registers are cited by entry ID plus row |
| 132 | CORE | TD-S85-NEW-2 | ✅ Cross-document section refs carry their owning document (`capture_s74.md` §7.2, not bare §7.2); a bare §N resolves to whichever file the reader is i |
| 133 | CORE | ADR-026 | ✅ A guardrail must be conditioned on a value the host can read, proven with a control; and a CPU quota bounds rate, not draw — the budget is CPUQuota  |

---

## 6. Three decisions for the operator

### (a) The second Rule 18-23 series collides with Non-negotiable 18/19

**The measurement that decides this.** Across all 135 `docs/` files (excluding
`CLAUDE_history.md`), every citation of `Rule 18` and `Rule 19` was classified by the
keywords in its surrounding 700 characters:

| | non-negotiable meaning | second-series meaning | ambiguous |
|---|--:|--:|--:|
| `Rule 18` | **32** (trading_calendar) | **0** (patch-script EOL) | 4 |
| `Rule 19` | **12** (`.env` tracing) | **0** (module imports) | 1 |

**Nothing in the corpus cites B6-as-Rule-18 or B7-as-Rule-19.** Renumbering that pair
costs zero citation churn. Rules **20-23 do not collide** and keep their numbers.

The separate, real citation cost is that Rules 20-23 move **out of `CLAUDE.md`**:
**10 occurrences explicitly say `CLAUDE.md Rule 20/21/22`** (`tech_debt.md`,
`MERDIAN_System_Map.md`, `MERDIAN_Assumption_Register.md`,
`coupling_audit_2026-09-07.md`, `experiment_forensics_2026-09-11.md`,
`ict_structure_audit_2026-09-09.md`). Those go stale under every option below.

> **S87 correction (2026-09-30):** this six-file list is wrong in composition. The live Rule 20/21/22 citations were 11, not 10: it omits merdian_reference.json and MERDIAN_Experiment_Compendium_v1.md, and two of its files carry the bare form. Only the 3 Rule-20 citations needed re-pointing, because 21/22 stayed in core. Done at b282a05.

| Option | What it does | Cost |
|---|---|---|
| **1. Renumber B6/B7 to Rules 24/25** | One monotonic series; Rules 20-23 unchanged | **0 citations** to re-point. Needs no new ID prefix, so no Rule 9 / Rule 10 ADR |
| 2. Re-label the series `P-18…P-23` | Visually preserves the numbers | Invents an ID prefix -> **Rule 10 requires updating the numbering convention** in the Doc Protocol, and Rule 9 bars new prefixes without an ADR. Also re-points all 10 `CLAUDE.md Rule 2x` citations *and* renames 4 rules that were not broken |
| 3. Leave as-is | No work now | After the split each number silently resolves to one meaning. The failure is invisible — the R-j shape |

**Recommendation: option 1.** Renumber **B6 -> Rule 24** and **B7 -> Rule 25**, leave
Rules 20-23 alone. It is the only option with measured-zero citation cost, it avoids
the ADR overhead a new prefix triggers, and it changes exactly the two rules that are
actually broken.
> **S87 correction (2026-09-30):** superseded. 24/25 were not free (a retired S40 Rule 24 survives in CLAUDE_history.md), and the cost was not 0: 2 citations existed, 1 needed re-pointing (`tech_debt.md:119`; `s81_docclose_notes.md:1943` cites the bare B6 label and was left alone). B6/B7 became Rules 26/27 at b282a05.


**Sequencing, because the constraint bites here.** You have required Rule 18 (B6) move
**verbatim**, and TD-S86-NEW-4 must not be fixed in the split because prompt B2
measures it. So: **phase 1 relocates B6/B7 verbatim, numbers and defect intact.** The
renumber is a **phase 3 action, after the after-arm is graded.** In the interim core
carries a 2-line disambiguator:

> *Rules 18 and 19 each name two rules. The hard rules here are the
> `trading_calendar` trust-anchor (18) and the `.env`-tracing ban (19). A second,
> older pair — patch-script EOL handling and the module-import grep — lives in
> `.claude/rules/python-writers.md` and is scheduled for renumbering to 24/25.*

**For the 10 stale `CLAUDE.md Rule 2x` citations:** re-point them in the same phase-3
pass, not now. A citation that resolves to a real rule in a new location is a
find-and-replace; one that resolves to *different plausible content* is the
§D.40.6 failure, and that is what option 3 would create.

### (b) The settled block: trim to rules, or relocate wholesale

| Option | What it does | Cost |
|---|---|---|
| 1. Relocate all 133 wholesale | Simplest; recovers the full 91,195 B | Strands the CORE-class bullets in an unloaded file. Those are the Rule-0-family epistemics — *a check that cannot fail is not a check*, *an expected value must be computed not recalled*, *a role-scoped check runs in ONE execution*. **This is the R-j failure shape at scale** |
| **2. Trim to rules only** | 21 bullets -> core, 55 -> path-scoped rules, 57 -> their register | The 57 relocations each need their register confirmed to actually carry the bullet — the audit showed 40 of 102 claims were duplicated and 59 were not, so **this cannot be assumed per bullet** |
| 3. Keep as-is | No work | 91,195 B and ~159 lines. **AC1 fails on both bounds** |

**Recommendation: option 2.** Measured basis: 83 of 133 bullets cite a register ID and are
records whose authority is the cited ADR/TD; only **21 are universal rules**, totalling
**14,250 B**, which fits the §1 budget. Option 1 is cheaper to execute and
loses exactly the content that cost the most to learn.

**One condition on option 2, and it is not optional.** Each `register:` relocation is
gated on confirming the register carries the bullet's substance — the same
quote-or-it-stays test the audit used. **50 bullets cite no register ID at all**; those
cannot be relocated to a register by definition and must go to core, a rule file, or a
newly-created register row. They are the `⚠` rows in §5.

### (c) The pointer text core carries to `CLAUDE_history.md`

| Option | Shape | Cost |
|---|---|---|
| 1. One-line pointer | *"Session history and version footers: `docs/registers/CLAUDE_history.md` (not loaded)."* | 1 line. **This is what the S74 split already did**, and TD-S73-NEW-8 records the result: the pointer went unread and the file kept growing. A pointer with no topic index is not addressable |
| **2. Pointer + topic index** | 1 line + an 8-row table mapping topic -> which session block answers it | ~10 lines. Makes the unloaded content addressable without loading it |
| 3. Pointer + rely on ADR-026 retrieval | 2 lines, delegating discovery to the docs index | ADR-026 is ACCEPTED but **its first full build is unmeasured (TD-S85-NEW-3)** and it has no resumability if the build overruns. Cannot be the only path yet |

**Recommendation: option 2**, with option 3 added later as a second path once ADR-026
has a measured build. Proposed text:

> **Session history is not loaded.** The 23 `Session NN engineering discoveries`
> blocks and all version footers live in `docs/registers/CLAUDE_history.md`. Open it
> when you need one of these, and cite by session number, never by line:
>
> | If you need… | Session block |
> |---|---|
> | patch-script encoding / EOL / BOM history | S11 ext, S14 |
> | timezone and bar-era handling | S11, S15, S22 |
> | Supabase / PostgREST limits and schema drift | S28, S29, S35 |
> | cohort, holdout and gate-transfer reasoning | S26, S30, S31-B, S33 |
> | chain-data tier transition and held-strike PnL | S33, S34, S35 |
> | Pine v6 ergonomics | S31-B, S41 |
> | read-path scoping, recency floors, CAS timing | S69, S70 |
> | fail-open corollary and cross-tier identity | S71, S72 |

**Why a topic index rather than a chronology:** an agent does not know it needs S31-B;
it knows it is about to write Pine. The index is keyed on the question, which is the
same reason the source-of-truth map in core is keyed that way.

---

## 7. What this plan does NOT do

- **No repo file is created, moved or edited.** Phase 1 is a proposal.
- **No content is edited beyond relocation and the new pointers.** Rule 18 (B6) moves
  verbatim with its `encode("utf-8")` defect intact; TD-S86-NEW-4 is **not** fixed,
  because prompt B2 measures it and fixing it would confound the after-arm.
- **The Rule 18/19 renumber is not executed** — it is decision (a), for phase 3.
- **AC1 is satisfied by the core file alone** ({0} lines / {1:,} B). The rule files and
  skills are additional context when they load; §0's combined-limit warning is the
  reason there are eight small rule files and not three large ones.
- **Not addressed:** whether the eight rule files trip the combined-limit warning in
  practice. That is measurable only after the split, via `/context` and `/status`, and
  it belongs in the after-arm's observations rather than in this proposal.
