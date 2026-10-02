# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S83 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close, **S83 at the S85 doc-close**, **S84 at the S86 doc-close** **S85 at the S87 doc-close** and **S86 at the S88 doc-close**, each moved verbatim rather than retyped. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**S88 — 2026-10-01 (Thursday, SENSEX expiry day), closed 2026-10-02.** One pre-registered test
passed three times; everything else measured was negative, a correction, or a refusal by design.
Full detail: `docs/research/capture_s88.md` §1–§6, with §5.7 correcting §5.3.

**What was established**

1. **L9 stage-1 max-pain, SENSEX arm: PASS ×3** (§1). Pre-registered before any OI or expiry data
   was read; instrument hash verified before each run. PASS at **12:45:07, 14:55:06, 15:30:06 IST**
   — arm A 0/0 both ways, arm B 197/197, no tie at minimum `total_pain` in any body. Mechanism:
   W2-only strikes 0 and all three `max_pain_strike` agreeing, so **all 197 differing rows differ
   in `total_pain` alone — the expiry mixture moved the magnitude and never the published level**,
   while shared strikes where W2 OI > W1 grew 6 → 12 → 16. **TD-S80-NEW-1 is NOT closed: the NIFTY
   arm is owed, next NIFTY expiry 2026-10-06 (measured).**
2. **The S82 instrument did not exist in the tree and was rebuilt** (§1.2), stated as rebuilt
   rather than implied continuous.
3. **Marketview header reads a close two sessions old during every session** (§3, **TD-S88-NEW-1**).
   Writer at **16:10 IST** (crontab line 24) + a newest-row reader with no date filter. NIFTY
   2026-10-01: **−1.2953 %** shown against a settled **−0.8775 %** — overstated **0.4178 pp, 48 %
   too large**; SENSEX only 0.0667 pp, and that is luck, not safety — the error is the gap between
   two consecutive closes and is **unbounded**. **Fix belongs in the read layer**; moving the cron
   cannot work, because no settled close exists before 16:00.
4. **`open_0915_spot` is the 09:16 bar's CLOSE**, not the 09:15 open (§3.3, D.44.5) — proven by
   comparison, 4/4, with `ohlc_open ≠ ohlc_close` on all 4 so the test was not vacuous.
5. **The all-layers reconstruction returned a NEGATIVE result** (§5). 90/90 spine cells and
   **540/540 layer cells** admitted on exact `ts` equality. **On the built layers, 2026-10-01 was
   not distinguishable from the other five SENSEX expiry days before 12:15** — below chance on
   SET A (34 vs 36), 5 above on SET B (38 vs 33). **08-27 scored highest in both** and its range is
   **rank 5 of 17, 44 % of 10-01's**.
6. **Eleven of twelve parity views carry no history** (D.44.3); L3 refuses wholesale on dte 0, L10
   **partially** (keeps `ce_iv`/`pe_iv`), L9 publishes throughout and was limited by chain depth —
   **and all of that was already documented at `MERDIAN_System_Map.md:1963-1976`** (§5.7).

**Corrections I made to my own work inside the session** — recorded because they are the session's
most transferable output: a **UTC/IST cast** that would have pinned every bucket to the same run
and looked plausible (D.44.4); a **register-contradiction claim** that was an omission, not a
conflict (§2.5 ii → §3.2, D.44.7); **"L10 is empty"**, too strong (§5.7, D.44.10); and a
**NIFTY/SENSEX number mix** in a TD row, rebuilt with the arithmetic asserted against the artefact.

**Registers touched:** `tech_debt.md` (TD-S88-NEW-1; update rows on TD-S81-NEW-16 and
TD-S80-NEW-1), `MERDIAN_Assumption_Register.md` (**§D.44, 10 rows, all REFUTED**),
`MERDIAN_Enhancement_Register.md` (**ENH-133…138, all PROPOSED**; Part 1 count recomputed
**116 → 122**, having drifted 4 since S81 despite the "derive, don't carry" rule),
`merdian_reference.json`, System Map §S88, `CLAUDE.md` footer. **No new ADR.**

## NEXT SESSION PICKS UP

**Dated, in order:**

1. **Sat 2026-10-03, out of market hours** — ADR-029 **#13/#14**: sandbox enable plus install and
   network-allowlist cost, and the Bash deny-bypass gap with the untested spellings enumerated first.
2. **TD-S86-NEW-9 — the owed operator ruling, BEFORE 2026-10-07.** §2.6's ≥ 3×SE precondition does
   not say whether it gates the gamma reading or only the offset reading, and on A4's data the two
   give **different T1 verdicts**. Must be ruled, pre-registered and dated before the next arm runs.
3. **Tue 2026-10-06 — the NIFTY L9 stage-1 arm** (TD-S80-NEW-1, owed since S82, carried through
   S85/S86/S87/S88). Front expiry **measured** as 2026-10-06. **Pre-register that morning, before
   any read**, by the §1.3 verdict order; the instrument is `scratch/s88_l9/l9_rebuilt_source.sql`
   with the scope CTE set to NIFTY and that day's W1.
4. **Optional, before 2026-10-06** — a pre-registered threshold for the fixed-strike OI tilt and/or
   `ratio_pct`, if either is to be tested rather than described. **Unstamped means not a test.**
5. **Wed 2026-10-07, 10:15:59 IST — A4 re-run**, SENSEX dte 1, gated on item 2.

**PARITY BUILD QUEUE — S88's stated priority, and it comes before the ENH queue.**

- **(a) TD-S88-NEW-1 repair.** A Lovable read-layer prompt was **drafted in chat 2026-10-01** and is
  not in the tree. **Precondition before it ships:** a **single-run anon check in the SQL editor**
  — one execution carrying `current_user` beside its rows — against `trading_calendar` and
  `market_spot_snapshots` (the **16:00–16:10 IST `dhan_idx_i`** rows). `merdian_ro` cannot run it
  (`permission denied to set role "anon"`), so it belongs to the editor under postgres.
- **(b) §H phased Lovable prompts for the board.** Design doc **§A–G APPROVED 2026-10-01 13:04 IST
  with four additions R1–R4**; the **§B.1a bindings are measured** (§2.2–§2.4). Note for whoever
  writes them: `basis_pct` is a **futures-calendar artefact** across days (§5.4) and `open_0915_spot`
  is the **09:16 close** (D.44.5) — both bindings must carry those qualifications.
- **(c) Snapshot export into the board canvas.**

**Build queue — nothing started, all operator-gated:** ENH-133…138 (Part 4 S88 footer).
**ENH-133 and ENH-134 are alternatives, not a sequence.** **ENH-135 revisits a deliberate S62
decision and is not a defect report.** **ENH-137 is shadow-only under ADR-029.**

**Rulings owed:**

- The **six ENH dispositions** (ENH-133…138).
- The **five candidate rule lines** in `docs/research/s88_rule_lines_PROPOSED.md` — **proposed, not
  applied, and deliberately NOT in `.claude/rules/`**.
- Whether **`open_0915_spot` taking the 09:16 close is intended**, and whether `gap_open_pct`
  should be recomputed off `raw->>'ohlc_open'`.
- **L11 — decline or pending.** The design doc now says **PENDING**; the disposition is unresolved.
- **E-D1 … E-D8:** `gex_cr` unit · canonical max pain · theme · legacy pin · NET-LONG γ source ·
  signal row · ACCEL retirement · prototype corrections.
- **TD-S87-NEW-1** (parked, S3) · the **CLI unpin** · the **five documents carrying the copied
  "150k" figure**.

**Owed probe:** `scratch/s88_design/markers_check` — the anon-path read in one execution carrying
`current_user`, and `created_at` sampling on marker rows.

## OPERATOR RULINGS, S88

Recorded because each changed what was measured or what was written.

- **Parity board design doc §A–G APPROVED** 2026-10-01 13:04 IST, **with four additions R1–R4** —
  change marks on spot/VIX and the other levels; futures with basis and its change vs the previous
  session; the pre-open print; the gap up/down.
- **The tie clause gates BOTH arms, and all three bodies are counted**, evaluated before either
  arm is read — a tie can fake arm A *and* arm B. **P3 accepted** (independently derived leg 1).
  Both ruled **before** any OI or expiry data was read (§1.3).
- **Engine pull is operator-terminal only.** Nothing under `~/meridian-engine` runs from Claude
  Code, `git fetch` included. **Standing rule.**
- **Claude Code runs in a plain SSM shell, not tmux.** Resume with
  `cd /home/ssm-user/meridian-cc && claude --continue`.
- **§4.5's wording kept as written** (the quartile result stated with its caveats inline).
- **Price levels dropped from scoring; `d_oi_tilt` dropped from SET B** — both confounds named by
  the operator, both recorded in the output rather than silently applied.
- **Rule lines go to `docs/research/`, not `.claude/rules/`** — they are operator rules.

## Previous session S87

**Session 87 — 2026-09-30 (Wed).** One concern in three workstreams: **what this project's
own Claude Code usage costs, and how the work should be routed**. A transcript baseline was
measured, **ADR-029 was drafted and NOT filed**, and a **shadow routing v1** was built and
run once on TC1. **No production change, no DDL, no database write.** Three commits, all
documentation: `c4566b3` → `9c5190f` → `e638059`.

| Field | Value |
|---|---|
| **WS1 — the engine tree was pulled, and is behind again** | The S86-owed pull landed: `~/meridian-engine` reads **`35588a2`** by `git -C … rev-parse`, the S86 doc-close commit. **It is now three commits behind again** — `c4566b3`, `9c5190f`, `e638059`, all written after the pull, all `docs/` — **so a second pull is owed at this close.** CLI pin **`2.1.277` HOLD** with `DISABLE_AUTOUPDATER` still set, **ruled 17:41 IST**, revisit at the end of shadow v1. |
| **WS2.6 — the split measured on the instrument, and the warning is the finding** | `ws2_6_context_measure.md`, operator-read `/context`, working directory / CLI / model held constant across both readings: **before `6bba0ce`, 128.9k tokens with the over-limit warning SHOWN; after `35588a2`, 14.3k tokens, warning ABSENT — reduction 88.91 %.** **The warning's absence is a state change, not a smaller number.** Corroborated from the git blobs rather than from the tool: **327,949 → 40,073 B, 87.78 %** — same order, different instrument. And **the file grew at the S86 doc-close**: S86 read 14.1k at `76ad9a3`, this reads 14.3k at `35588a2`, **+1.42 % in a single close** — a split re-filled at every doc-close returns to the limit on its own, and that delta is the quantity to watch. **The ADR-028 §7 amendment is OWED**, and it should cite the token readings and the warning state change, **not** the char figure, which does not reconcile with the warning and was left unreconciled rather than adjusted to fit. |
| **WS2.5 — the "150k" figure has an origin, and it is a CHARACTER limit** | Read off the same `/context` capture at `6bba0ce`: the warning states *over the 150.0k-char limit (318.5k chars)*. So the number carried by five documents is **the CLI's own 150.0k-CHARACTER warning** — not a token ceiling and not a byte ceiling, which is how it came to be compared against byte counts. **The origin is now known; the disposition is not.** ADR-028 §6 item 3's **correct-in-place-or-annotate ruling is still OWED.** |
| **WS3.1 — the baseline, and the measurement that says what cannot be measured** | `WS3.1_baseline.md`. Measured from a **sha-manifested frozen snapshot**, because the first run against the live corpus **failed its own phase-A cross-check by +5 responses** when this session's writes grew the directory mid-measurement — **the cross-check is the only thing that noticed**, and every token total would have inherited the disagreement (§1). Eight instrument controls PASS **before** any metric, and a failure suppresses the metrics rather than annotating them (§2). **§5a — approved permission prompts are BYTE-INVISIBLE.** No key records a per-call approval, by a lexical test **and** a non-lexical denied-vs-not-denied key-set differential; **the denial count therefore has no denominator, and no prompt rate, approval rate or approval-to-denial ratio can ever be recovered from these transcripts.** Anything ADR-029 wants to know about prompting must be logged **forward**. **§5b — context-limit hits: one line across both corpora**, on `-meridian-engine` only, firing on the size arm at a margin of **+3266 tokens / +0.3629 %** over the pre-registered bar — **had the bar been set 3267 tokens higher it would read as an ordinary API event**; `-meridian-cc` is **not observable by this metric**. **§6 — the `git -C` existence result: the `-C` prefix breaks the built-in read-only no-prompt match, even when it names the directory the session is already working in.** n=1 per command, one session, `git` alone — an existence result, not a rate. **§4 — costs are read from the tool's own emitted fields, cross-checked to a difference of 0.000000, and no price table is applied anywhere.** **§8 records 7 instrument defects — 4 caught by review, 3 by running an instrument** — and is the source for the owed Assumption Register **§D.43**. |
| **WS3.2 — ADR-029 FILED ACCEPTED (S87, 2026-10-01)** | `docs/decisions/ADR-029-model-routing-and-token-efficiency.md`, deliberately under `docs/research/` so it cannot be mistaken for an accepted decision sitting in `docs/decisions/`. Decisions are labelled **D13–D27** (ADR-026 owns D1–D3, ADR-027 D4–D7, ADR-028 D8–D12); classes are **TC1 / TC2 / TC3** and criteria **AC29-1..4**, both prefixed because the bare `T`, `A` and `C` label spaces are already occupied in this corpus. **No model name, model identifier, price or measured figure appears in the draft, in digits or in words** — a scanner asserts it, with negative controls that prove it can fire. The reserved Decision Index row is **re-confirmed at filing time, not at drafting time.** **Rulings live in `rulings_s87.md` and are never restated in the draft** — the same argument D15 makes about the mapping. The appendix carries **18 rows: 5 RULED, 1 PARTLY RULED, 13 still owed**, and **ADR-029 is not filed until each has a ruling or an explicit dated deferral.** |
| **WS3.4 — shadow v1 built, TC1 run once, and the shadow FAILED its pre-registered bar** | Built to the 14:22 rulings: `.claude/routing.json` (mode `shadow`; TC3 shadow `null`), two shadow subagents declared in `.claude/agents/*.md` (`tc1-measurer`, `tc2-drafter`), and the ledger **outside the repository** at `/home/ssm-user/merdian_ledger/`. **TC1 v1** — suite sha256 **recorded == recomputed**, 10 tasks × 2 roles. Incumbent **10/10**, shadow **6/10**, **agreement 6/10 against a bar of 10/10 fixed before the run → FAIL, so TC1 stays on the incumbent and nothing gears down.** **The failure is systematic, not scattered: 0/3 on the line-count tasks, every one off by exactly +1**, while the tasks that resolve by listing files are **3/3** — so a determinate *answer* does not imply a deterministic *method*, and **whether TC1 work must run a tool rather than read is now an open question in the draft, not a settled clause.** Shadow cost **0.2535× (3.94× cheaper)** on **28.20× the output tokens** — **and cost ranks nothing until the verifier column is joined to it**, which is the whole of D18. **All 10 truths re-verified from the files on disk, 10/10 MATCH**, so each shadow FAIL is a genuinely wrong answer and not a bad truth; the independent re-derivation of the verifier disagrees with the ledger on **0**. **TC2 NOT RUN.** |
| **Permissions — ruling #12, and it moved the environment** | The §6 finding was acted on rather than noted: **8 read-only `git -C` allow rules** (rev-parse, status, log, diff × both trees), with the **PASS bar pre-registered at 18:47, before the test** — the four read-only commands to run with **no** prompt **and** `push --dry-run` to **prompt**, with the revert condition written down for each failure direction. Tested in a fresh session ~19:03–19:05 IST: **both halves held**, and ruling #12 followed at **19:06 IST — keep the absolute-path convention together with the allow rules.** User-level permissions now read **allow 10 / ask 15 / deny 22** from `~/.claude/settings.json`, so **the S86 block's `allow 2` below is SUPERSEDED** — the restated-copy drift D15 names, arriving in the register that names it. **Recorded and NOT fixed: `git diff` and `git log` both accept `--output=<file>`, so two of the eight read-only rules technically permit a file write** (ADR-029 §7 row h). **Other read-only verbs remain untested.** |
| **Ledger** | **TDs_NEW=0, TDs_CLOSED=0, ADRs_NEW=0, ADRs_AMENDED=0, no Decision Index row** — ADR-029 holds a **reserved** ID and filing it is what would add the row; drafting it does not. **The registers were not touched this session and are owed**: `tech_debt.md` (the `--output` limit and the ADR-028 §7 amendment both want entries), Assumption Register **§D.43** from `WS3.1_baseline.md` §8, Decision Index, Enhancement Register. Three commits, all pushed; **HEAD == `origin/main` == `ls-remote` at `e638059`.** |

**The session's two load-bearing results both say the same thing about instruments.** §5a is a
measurement whose entire content is that a quantity cannot be measured — approvals leave no
bytes, so every prompting question has to be answered forward or not at all. And the TC1
shadow run failed on the one task type where the class definition is most obviously
satisfied: counting lines is as determinate as work gets, and the shadow was wrong on all
three by exactly +1. **Neither was found by reasoning about the design.** The first came out
of a key-set differential run because a lexical test had already produced a false candidate;
the second came out of running the suite against a bar written down first. The draft records
both as open questions rather than resolving them, which is the only honest disposition for
one suite on one class.


**Since `707276a` — the registers were written and five more workstreams landed.** The
S87 block above records the session as it stood at the first three commits; this is what
followed, in commit order.

| Workstream | Outcome |
|---|---|
| **WS2.1 — rule renumber** (`b282a05`) | B6/B7 → **Rules 26/27** (free repo-wide); **24 is NOT free** — the retired S40 Rule 24 survives in `CLAUDE_history.md`. **11** Rule-20/21/22 citations found, **3** re-pointed; **2** B6/B7 citations, **1** re-pointed. The core disambiguator note removed. Every figure in the pre-S87 estimate was wrong in the direction that made the renumber look safe (§D.43.11). |
| **WS2.2 — BOM round-trip** (`dfeb261`) | The Rule 26 snippet now round-trips the BOM (`has_bom` → `enc`), demonstrated on a fixture showing both arms; the `:15` bullet reconciled so one rule has one statement, proved by grep. **TD-S86-NEW-4 RESOLVED.** Blast radius re-measured at **36** files (27 `.py` + 3 `.ps1` + 4 `.md` + 2 backups), not the 27 the entry recorded — and the `.ps1` files are the scheduled ones (§D.43.12). |
| **WS2.3/2.4 — the `doc-close` skill** (`be9c3d4`) | **Option A was built, measured and came out VOID.** Three arms × two prompts × three runs, 0 aborts, one model, blind-graded by a fresh agent: **B3 baseline 0/3, change 0/3, control 3/3** — the control, with the content removed from *both* core and the skill, **passed**, because the empty core heading becomes conspicuous and the model names it, satisfying the *"Must cite"* clause that reciting the content does not. **B3's rubric is inverted for a relocation.** The purpose-built `C-close` discriminated correctly (change 3/3 · baseline 0/3 · control 0/3) on the register order, but the pre-registered VOID governed and was **not** overridden on C-close's strength. Operator ruled **option B** at 07:22 IST: core keeps the checklist, the skill gains the register order. **TD-S86-NEW-8 RESOLVED**; gate 2 extended to a **body ≥ 500 B** check that FAILS on the old 95 B shell. **WS2.4 found an S1**: `merdian-runbooks` passes the byte gate at 1026 B while **7 of its 9 runbook targets do not exist**, including *Emergency stop* — pre-existing, not a split regression (**TD-S87-NEW-1**). |
| **WS2.5/2.6 — the `"150k"` figure, identified** (`0e52360`) | Disposed **by erratum in ADR-028**: the five documents stay **byte-identical** and the correction lives in the ADR that found the error. **`"150k"` is the CLI's 150.0k-CHARACTER warning**, not a token or byte ceiling — *shown* on `6bba0ce`, *absent* on `35588a2`. Ten occurrences located by `file:line`, and the tally recorded honestly: 1 source + 7 copies + 1 prior correction + 2 that describe the real warning. **ADR-028 §7.6 added**: launch load **128.9k → 14.3k tokens, 88.91 %**, corroborated 327,949 → 40,073 B (87.78 %); the file **grew 1.42 % at the S86 doc-close**, which is the quantity to watch. |
| **WS3.2 — ADR-029 FILED ACCEPTED** (`af34e58`, `e8d9306`) | `git mv` into `docs/decisions/`; all **18** appendix rulings closed — ruled, or deferred with a date (**#4/#5 → S88**, **#13/#14 → Sat 2026-10-03**, **#9 until a class passes shadow**). Decision Index row added in ADR-028's format, the S86 reservation discharged, next-free **already** `ADR-030+` so it was asserted rather than advanced. Each of the 15 body `OPERATOR RULING OWED` blocks now carries a dated `→` mark beneath it, the heading itself byte-unchanged. |
| **EOS part 1** (`6b32fb5`) | **TD-S87-NEW-2..5** filed; **Assumption Register §D.43** added (**17 rows, all REFUTED** — 7 carried from `WS3.1_baseline.md` §8, 10 new, of which 3 are this session's own instruments caught by review). `CLAUDE.md` **v1.58 → v1.59 at 39,592 → 39,592 B, exactly flat**: the first footer draft was 663 B against the old 510 and the growth-rule assertion stopped the write, so the footer was rewritten to fit rather than spend headroom. |
| **ENH-98 E2 — the refusal FIRES** | Ratified pre-registration (`e2_02_prereg.out`, `41b4426b…`, ratified **05:59:47 IST**), gate passed first (both symbols 10:15:06 IST, 0.00 %), then the arm. SENSEX dte 0: precondition PASS (ATM rows **28 ≥ 10**), `exact/365` ATM **0.2620** / NEAR **0.5140** — both over 0.10 → **REFUSE**. **E1 and E2 have now both refused, so W1's "charm to 15:30" stays UNRECORDED and L78-3's expiry leg is NOT amended.** E2 is **not** a T1 arm: **T1 remains UNDECIDED.** The stamp **corrected §2.8's NIFTY dte from 2 to 5** before the arm (2 was a trading-day count); observed 5 — had the error been carried, a correct arm would have read as a MISS. `capture_s84.md` **§2.12**. |

**Ledger, since `707276a`.** TDs_NEW **5** (TD-S87-NEW-1 **S1**, NEW-2..5), TDs_RESOLVED
**2** (TD-S86-NEW-4, TD-S86-NEW-8), ADRs_NEW **1** (ADR-029 ACCEPTED), ADRs_AMENDED **1**
(ADR-028 — erratum + §7.6), Decision Index rows **+1**, Assumption Register **§D.43 (17
rows)**. Eight commits, all pushed, three-way sha verified on each. **No production code,
no DDL. The only database contact all session was the E2 arm, read-only as `merdian_ro`.**

## NEXT SESSION PICKS UP

**The Parity build is the priority. Items 2–4 are dated and must not slip.**

1. **THE PARITY BUILD — the session's main work.** Operator-prioritised 2026-10-01 over the
   runbook repair, which is parked (TD-S87-NEW-1). Everything below is either dated or
   background; this is the item that gets the session's attention.
2. **TD-S86-NEW-9 — the owed operator ruling, BEFORE 2026-10-07.** §2.6's ≥ 3×SE
   precondition does not say whether it gates the gamma reading or only the offset reading,
   and on A4's data the two readings give **different T1 verdicts** (UNDECIDED vs PASS). It
   must be ruled, **pre-registered and dated**, before the next arm runs, or that arm is
   measured under two live readings at once.
3. **A4 re-run — Wed 2026-10-07, 10:15:59 IST, SENSEX dte 1.** The arm T1 needs. Stated
   before the run: on the three-point precondition gradient (6.41× → 3.79× → 1.18×) this arm
   is **more likely than not to be another NO-TEST**; if it is, T1 as written is scoped to a
   dte range its own precondition may not admit — a decision owed to the operator, not a
   result.
4. **Sat 2026-10-03, out of market hours** (ADR-029 **#13/#14**, DEFERRED). Sandbox enable
   plus its install and network-allowlist cost, and the Bash deny-bypass gap with the
   untested spellings **enumerated first**.
5. **The NIFTY L9 stage-1 max-pain arm — STILL OUTSTANDING** (TD-S80-NEW-1, owed from S82).
   It rode on the A3 date, was not run, and has now been carried through S85, S86 and S87.

**BACKGROUND / PARKED — not this session's work unless the Parity build frees time.**

- **TD-S87-NEW-1 — PARKED, re-rated S1 → S3** (operator, 2026-10-01). **MERDIAN has never
  placed an order** and the placer was never matured for use, so the seven dead runbook
  routes have no live incident behind them. The phase-1 measurement is kept at
  `s87_measure/runbooks/phase1.md` so the work is not repeated. Two measured facts survive
  for whenever it is unparked: `docs/runbooks/README.md` carries the **same** eight dead
  rows and names a **ninth** absent runbook the skill omits, and
  `MERDIAN_Deployment_Topology.md:43,183` is **stale** on the order placer.
- **S88 — the logging hooks** (ADR-029 **#4/#5**, DEFERRED to S88): **background.**
  Permission prompts and context-limit events must be logged **forward** — §5a established
  that approvals are byte-invisible, so nothing retrospective can answer these.
- **The TC2 suite** (ADR-029 **#10**): **background.** 20 tasks, to be built. TC1 v1 is
  frozen at 10 tasks and its shadow **FAILED 6/10 against a 10/10 bar**, so nothing gears
  down; per **#18** TC1 work must use deterministic tools and a task without one **is TC2**.

**Also owed, undated:** TD-S87-NEW-2 (`check_xrefs` blind to `AC29-n` and letter-suffixed
sections; the copy actually run is unversioned), TD-S87-NEW-3 (`.gitignore` rotated logs —
fix in `meridian-cc`, then pull), TD-S87-NEW-5's actual fix (a length check on
`session_log.md`, not just the skill's ordering), the **second engine pull** (the tree is
behind by this session's commits; the pull waits until **16:00**), and the BOM `git log`
forensics, which `git log -S` **cannot** answer (§D.43.13).

## OPERATOR RULINGS, S87

**All rulings are recorded in `docs/research/s87_routing/rulings_s87.md`**, which is the
single source. This table points at it and does not restate the text — a ruling
transcribed into a second place is a ruling that can drift out of agreement with itself.

| # | Topic | Ruled at |
|---|---|---|
| **#2** | Where the class-to-model mapping file lives, and in what format | 2026-09-30 14:22 IST |
| **#3** | The initial TC1/TC2/TC3 mapping | 2026-09-30 14:22 IST |
| **#6** | Ledger location (schema owner followed at #6b) | 2026-09-30 14:22 IST |
| **#8** | The shadow-agreement threshold for gearing down | 2026-09-30 14:22 IST |
| **#15** | The CLI pin — **HOLD** | 2026-09-30 17:41 IST |
| **#12** | The absolute-path convention, kept with the eight read-only `git -C` allow rules | 2026-09-30 19:06 IST |
| **#1 · #4 · #5 · #6b · #7 · #9 · #10 · #11 · #13 · #14 · #16 · #17 · #18** | The thirteen remaining ADR-029 appendix slots, ruled or deferred-with-a-date in one pass | 2026-10-01 09:03 IST |
| **ADR-028 `"150k"` disposition** | Annotate by erratum; the five documents stay byte-identical | 2026-10-01 06:44 IST |
| **WS2.3 option B** | Option A is VOID on its own control; core keeps the checklist and the skill gains the register order | 2026-10-01 07:22 IST |
| **E2 pre-registration** | Ratified as written, including the NIFTY dte 5 correction and the SENSEX-only scope of the 0-rows expectation | 2026-10-01 05:59:47 IST |
| **`--max-turns` deviation** | Accepted: all arms share the config and every bar is within-WS2.3, so the runs continued | 2026-10-01 06:42:15 IST |
