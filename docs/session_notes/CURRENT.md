# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S83 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, S82 at the S84 doc-close and **S83 at the S85 doc-close**, each moved verbatim rather than retyped. This file carries the current session and one predecessor, and nothing else.

---

## Last session

**Session 85 — 2026-09-29 (Tue).** Two halves: the ENH-98 **A3 + E1** arms run against
the pre-registration, then a **feasibility inventory and ADR-026 filed ACCEPTED**. **No
production change, no DDL, no database write.** Three commits, all documentation:
`3a78769` → `f925939` → `881b03b`.

| Field | Value |
|---|---|
| **A3 (SENSEX dte 2) — the first T1 arm** | Gate passed before the run: both symbols at **10:15:06 IST**, **0.00 %** row deviation against their own 09:15 reference (NIFTY 1020, SENSEX 768). Precondition **PASS at 3.79×** (19.1 against 3 × 5.051). **T1 PASS on this arm** — `exact/365` ATM **0.0425**, NEAR **0.0439**, the refusal needing *both* above 0.10. Interpretation clause **NOT TRIGGERED**. **T1 itself is not decided** — §2.6 evaluates it across the dte 1–2 pair, so the verdict follows A4. |
| **E1 (NIFTY dte 0) — the refusal fired** | Precondition PASS (17 ATM rows ≥ 10). `exact/365` ATM **0.2657** / NEAR **0.4949**, both over the 0.10 bar → **refusal**. Per §2.8 outcome use, **W1's expiry-day charm stays UNRECORDED until re-tested**; E2 is unaffected. Offset/`r_eff` **NO-TEST at 0.49×** — the pre-registered expected outcome at dte 0, and **not read as a finding**. `dte/365` and `dte/252` returned **0 rows at dte 0**, as pre-registered. |
| **ADR-026 FILED ACCEPTED** | `docs/decisions/ADR-026-docs-retrieval-index.md`. Docs retrieval index over the **138-file / 7.43 MB** text corpus: `rag` schema on the existing Supabase (**pgvector 0.8.2, available and NOT installed**), **ID-anchored byte-budgeted** chunking that splits *within* lines for the six paragraph-per-line files and by key path for `merdian_reference.json`, **hybrid ID-first** retrieval over ~6,300 heading-anchored entry IDs. Decision Index row added; reserved marker advanced. |
| **ADR-027 DRAFTED, not filed** | `docs/research/s85_rag/ADR-027-DRAFT-…md`. Drafting agent + verifier + operator diff gate. **Depends on ADR-026** and **inherits its §6 write boundary verbatim** — asserted byte-identical by `check_s6_verbatim.py`, not claimed in prose. Its **ID is RESERVED** in the Decision Index Pending table so the draft cannot be collided with. |
| **Rulings, all operator, all S85** | **A1** — ID-bearing recall@5 **= 100 %** (lexical match is deterministic, so a miss is a chunker defect and is fixed, not tolerated); prose-only recall@20 **≥ 60 %** / recall@5 **≥ 40 %**; **≥ 20 questions per class**, frozen before any index exists. **Staleness floors** — interactive absent when `age_doc_commits > 3` **OR** `age_days >= 2`; **drafting absent at `> 0`**; measured in **doc-commits** so code-only commits do not stale the index; re-index is **event-triggered, never on a timer**. **Embedding** — `bge-small-en-v1.5`, 384-dim, **ONNX local on EC2**; no document text leaves the host. **G1–G8** guardrails with **T1–T4** pre-registered; **G3a** `CPUQuota=50%` × **20-min hard timeout** = ≤ 10 credits/run logged in G7; **G3b** abort/requeue if interval `%steal` > **5 %** over a **10-second** `/proc/stat` sample; **G3c** Option 1 — **no IAM grant**, console review. |
| **The burst mode cannot be read from this host** | Measured: `ec2:DescribeInstanceCreditSpecifications` → **`UnauthorizedOperation`**; `cloudwatch:GetMetricStatistics` → **`AccessDenied`**; and the **`ListMetrics` control also denied**, which is what makes it a blanket denial rather than a metric-specific one. **G3's original start-of-run credit check was therefore unimplementable** — a check conditioned on a value the host cannot obtain. Recorded, not dropped; replaced by G3a+G3b. |
| **`CPUQuota` does not bound credit draw — the timeout does** | Found while doing the arithmetic, not by review. `t3.small` accrues ~24 credits/hr at a 20 %-per-vCPU baseline; a run pinned at `CPUQuota=50%` consumes **0.5 vCPU = 30 credits/hr**, i.e. **above the whole instance's accrual** before production's own use. **The binding quantity is `CPUQuota × timeout`**, which is why G3a fixes both factors. The same substitution shape as `OB_MIN_MOVE_PCT` and Guard 3. *(Credit figures stated from knowledge, **not measured** — operator confirmation owed.)* |
| **`§7.2` belongs to `capture_s74.md`, not the Deployment Topology** | I was one step from qualifying a bare `§7.2` as "Deployment Topology §7.2" and stopped to measure. The only heading matching deploy-direction is **`capture_s74.md:182` — `### 7.2 Deploy-direction inversion — still UNRATIFIED`**. Deployment Topology **§7.2 is "Windows Task Scheduler"** — a different section entirely. And the §7.3 / §7.6 "Guardrails doc" premise **does not resolve at HEAD**: 0 such headings, 0 `bare-call` matches, no Guardrails file tracked. **TD-S85-NEW-2.** |
| **Windows surfaces — 0 `docs/` references, with positive controls** | **OPERATOR-MEASURED** on the Local Windows box, S85 ~11:48–11:49 IST, PowerShell at `C:\GammaEnginePython`: `Get-ScheduledTask` actions filtered on `docs\|\.md\|research` → **0**; positive control on `Gamma\|merdian\|meridian` → **19 tasks**. `Select-String` over top-level `*.bat` / `*.ps1` for `docs[\\/]\|\.md\b\|research` → **0**; positive control `python` → **199 matches**. **19 is "tasks matching the name/path filter", NOT a total inventory** — it does not contradict Deployment Topology's 20 or S76's 23. **EC2-measured, by this tool:** 31 tracked `.bat`/`.ps1`/`.cmd`, **0** `docs/` refs, control 28 files / 88 `.py` matches. Different scope (tracked, all dirs) and a different control pattern, which is why 199 and 88 differ. |
| **Two of my own instruments were wrong, both caught by measurement** | A residual-`DRAFT` grep on the filed ADR-026 **errored** (ugrep complexity limit) and the `\|\| echo` then printed *"(none — clean)"* — a **false clean**, and the CLAUDE.md anti-pattern verbatim; the fixed-string re-run returned the real 0/0/0/1. And `check_xrefs.py` reported a **false EXTERNAL** (`S85 -> G3`) because a bare session marker was treated as a document qualifier, silently skipping a local check; the qualifier was removed with the reason in a code comment. |
| **The D3 label collision** | `D3` was declared in **both** drafts — ADR-026's staleness floor and ADR-027's drafting agent. Renumbered ADR-027 to **D4–D7** through `@@`-placeholders so `D4→D5` could not re-hit a label `D3→D4` had produced, with **four foreign references masked and restored** (ADR-027 cites ADR-026 D3 twice; ADR-026 cites ADR-027's D5 twice). Now **mechanically prevented**: `check_xrefs.py` treats a token declared in both as a COLLISION and a bare use as AMBIGUOUS, with a selftest arm. |
| **Ledger** | TDs_NEW=**3** (TD-S85-NEW-1..3), TDs_CLOSED=**0**. **ADRs_NEW=1 — ADR-026 ACCEPTED**; ADRs_AMENDED=0; **Decision Index row ADDED** (first since ADR-025 at S80) and next-free advanced `ADR-026+` → **`ADR-028+`** with **ADR-027 reserved**. Enhancement Register TRIGGERED (ENH-98, A3/E1). Three commits, all pushed, HEAD == `origin/main` == `ls-remote` at **`881b03b`**. |

**The half that produced findings was the half that was supposed to be routine.** The
arms ran to their pre-registration and the refusal on E1 is a clean, pre-registered
outcome. Everything in the middle column above — an unimplementable guardrail, a quota
that bounds nothing, a citation pointing at the wrong document, a label declared twice, a
grep that reported clean because it had failed — came out of composing the ADR, and every
one was caught by a measurement rather than by reading it again.

## NEXT SESSION PICKS UP

**Time-boxed**

1. **A4 — Wed 2026-09-30, 10:15:59 IST.** Second T1 arm, SENSEX dte 1. **T1's verdict
   follows this arm**; the rule and thresholds are pre-registered at capture §2.6 —
   **do not re-derive them after seeing the arm.**
2. **E2 — Thu 2026-10-01, 10:15:59 IST.** SENSEX dte 0 gamma fidelity. Unaffected by
   E1's refusal.
3. **Pull `~/meridian-engine` after 16:00 IST** → `git pull --ff-only origin main` to
   **`881b03b`**. Three commits behind, **0 non-`docs/` files**. Note the old
   "`.py` count must be 0" gate **no longer applies**: the gap carries 7 `.py`, all the
   `docs/research/s85_rag/` checker toolchain, **none scheduled** — verified, the
   intersection with the 26 cron/unit-invoked scripts is empty.
4. **The NIFTY L9 stage-1 max-pain arm owed from S82** (TD-S80-NEW-1) — **still
   outstanding.** It rode on the A3 date and was not run; the A3 Decision-Index-adjacent
   row says so explicitly rather than reading as done.

**Owed measurements and decisions — none are mine**

5. **Burst mode — operator, from Windows.** `aws ec2 describe-instance-credit-specifications --instance-ids i-0878c118835386ec2 --region eu-north-1`.
   `standard` → credit exhaustion **throttles the whole instance**, degrading every
   production writer; `unlimited` → **billed** instead. The two justify different
   `CPUQuota` values, so settle it **before** T1–T4.
6. **T1–T4 must pass before the first real embedding run.** T4 carries a
   **pre-registered prediction of ~330 MB peak RSS** with its derivation; if measured
   peak exceeds 450 MB **the bar is not moved** — the run is investigated.
7. **`completed_at` DDL** — TD-S85-NEW-1. `rag.corpus_snapshot` needs the column and
   every retrieval must filter on it, or a half-built index is readable with no error.
8. **NEW — does the first full index build fit G3a's 20-minute hard timeout at
   `CPUQuota=50%`?** ~4,270 chunks on 2 vCPU, **unmeasured**. If it does not, **the build
   must be resumable across runs**, which ADR-026 does not currently provide. **Recorded
   as owed, not ruled** — TD-S85-NEW-3.
9. **ADR-027's two open items** — the **A2 metric definition and threshold** (the
   definition is the harder half, and must be frozen as `metric_version` before the
   first scoring), and **where the drafting LLM runs**, which ADR-027 does not decide.
10. **Everything under the S84 block's owed list that S85 did not touch carries
    unchanged** — capture depth / SENSEX monthly quote quality, the stage-2 gate
    redefinition (TD-S81-NEW-14), P5's canonical max pain, the scratch-evidence
    decision, the product-name scrub, and the vendor methodology question.

## OPERATOR RULINGS, S85

These exist only in chat and are recorded here, in ADR-026 and in the ENH-98 block.
**None authorises a build.**

- **A1 thresholds** — ID-bearing recall@5 **= 100 %**, prose-only recall@20 **≥ 60 %** and
  recall@5 **≥ 40 %**, **≥ 20 questions per class** frozen before any index is built.
- **Staleness floors** — interactive `age_doc_commits > 3` OR `age_days >= 2`; drafting
  `> 0`; doc-commits only; re-index event-triggered, never on a timer.
- **Embedding** — ONNX-local on MERDIAN EC2, `bge-small-en-v1.5`, 384-dim. No text egress.
- **G3c — Option 1.** Accept G3a + G3b; **no IAM grant**; operator reviews
  `CPUCreditBalance` in the AWS console periodically. **Accepted with its gap stated:
  there is no automated credit-balance gate, by decision.**
- **ADR-026 filed; ADR-027 stays a draft with its ID reserved.**
- **ADR-026 is MOVED, never copied, when filed** — two copies of an accepted ADR diverge,
  and once the index exists retrieval would return both.

## Previous session S84

**Session 84 — 2026-09-25 → 2026-09-28 (Fri–Mon).** Measure-only. **No production
change, no DDL, no write of any kind to the database.** Six commits, all documentation.

| Field | Value |
|---|---|
| **Item 0 — the three S83 views** | Three-way hash: authoring and `origin/main` both `18c2fb8`, EC2 `bb374ae` — ancestor, 1 commit, 16 files, **0 `.py`**; operator pulled 16:51 IST. `COMMENT` len/md5 **3/3 MATCH** against expected values **computed from the `sql/` file literal**, not recalled. `anon` holds **SELECT and nothing else** on all three. **`Seq Scan` = 0** on all three plans. L3 SENSEX reads **`NO_CROSSING`** — the designed third clause, reachable and fired, not a dead arm. |
| **ENH-98 — the instrument was recovered, not rebuilt** | The S81 go/no-go query **was never saved as a file**; it existed only in a markdown fence (`s81_docclose_notes.md:696-773`, 78 lines). Extracted verbatim, sha256 **`d5930ee5…`**, matching variant **LF + trailing newline**. **A0 reproduces the S82 record 12/12 with no MISS.** A1 is a new point. `r_eff` is **INFORMATIONAL (T3)**: 3.64 %–3.81 % across three points against the instrument's hardcoded 0.065 — consistent with a **rate-convention** difference, not a spot effect, and filed with its n stated. |
| **Pre-registered, before any run** | **T1** as the sole go/no-go at §2.6 (refuse if `exact/365 gamma_relerr` median > 0.10 in BOTH ATM and NEAR, at SENSEX dte 1–2), with the **corrected** precondition — **across-strike** SE of the median, ≥ 3×, not the across-cycle band. **E1/E2** at §2.8, expiry-day arms at **10:15:59 IST**, with the dte-0 offset pre-registered as an **expected NO-TEST** so its failure cannot be read later as news. |
| **Ledger** | TDs_NEW=**7** (TD-S84-NEW-1..7), TDs_CLOSED=0. ADRs_NEW=**0**, ADRs_AMENDED=**0**, **no Decision Index row — stated as a decision.** Enhancement Register TRIGGERED (ENH-98). Six commits: `35c3fea` → `f1b6778` → `6c0730c` → `caffcf7` → `2ce8f95` → `3805922`. |
| **`parity_render_contract.md`** | New, 1,637 lines — the 18-object read contract, the front-end consumer map, the gap list. **39 citation offsets corrected at source**: `acl.out` and `comments.out` both carry a two-line header, so `ord N` sits at file line `N+2`; the document cited `ord+3` for one and the bare `ord` for the other. Post-fix re-audit: **0 mis-resolved.** |
| **P1–P7 → six TDs, one declined** | P1→NEW-2, P2→NEW-3, P3→NEW-4, P4→NEW-5, P5→NEW-6, P7→NEW-7. **P6 was NOT filed** — `TD-S81-NEW-8` already held the same two `meridian-connect` clones, the same stale `14b63f3` and the same S72 flat-namespace root cause; its one new measurement (live HEAD `7b60d01` → `a408fb4`) went in as an **S84 update row** instead. Filing a second entry on one root cause was declined. |
| **A prior finding overturned on 2 strikes / 1 session** | `TD-S83-NEW-5` recorded an ~8× ATM `iv` **and** 48.7M OI as two properties of the feed. They are **one row**: `ltp` frozen 5464.15 from 03:05–04:10 UTC (08:35–09:40 IST); at 04:15 `ltp` corrects and `iv` drops **121.04 → 14.89 in the same row**; only at 04:20 does `oi` fall **48,768,100 → 40**. The **correction order** is the evidence. A correction row was appended to that entry; its existing text untouched. |
| **Four of my own claims withdrawn on measurement** | §D.40.8. A `head -8` read as newest-first produced a confident "S80/S81 lost from the archive" — **the file appends at the end and is complete through S81**, and its own Contents field said so. A `grep -c` on the product name returned **0** because it was case-sensitive; `-ci` returns **32 across six files**. And the contract's own `.out` line citations were propagated once before being measured. |

**The session's shape was recovery and pre-registration, not construction.** Nothing was
built. The two durable artefacts are an instrument that now exists as a file with a hash,
and two pre-registrations written before the runs they govern — which is what stops a
later session fitting a threshold to an observation it already has.

## NEXT SESSION PICKS UP

**Time-boxed — these expire or get harder if missed**

1. **A2 — Mon 2026-09-28, 10:15:59 IST.** Gradient point, NIFTY dte 1 / SENSEX dte 3;
   **not** a T1 arm. The pinned instrument targets *latest `ts` ≤ target*, so A2 remains
   runnable after the fact — it does not expire at 10:16.
2. **A3 + E1 — Tue 2026-09-29, 10:15:59 IST, the same cycle.** A3 is the first T1 arm
   (SENSEX dte 2); E1 is NIFTY dte 0 gamma fidelity (§2.8). Also carries **the NIFTY L9
   stage-1 max-pain arm owed from S82** (TD-S80-NEW-1).
3. **A4 — Wed 2026-09-30, 10:15:59 IST.** Second T1 arm, SENSEX dte 1.
4. **E2 — Thu 2026-10-01, 10:15:59 IST.** SENSEX dte 0 gamma fidelity.
5. **T1 verdict — after A3 + A4.** Not reachable on the current n. Rule and thresholds are
   pre-registered at capture §2.6; **do not re-derive them after seeing the arms.**

**Owed decisions — none are mine to make**

6. **Capture depth — REOPENED by operator ruling.** The operator wants SENSEX the same as
   NIFTY (W1, W2, current monthly, next monthly). This reopens the **ADR-025 S80 ruling**
   that stood on SENSEX monthly OI at **0.089 %**. **Owed measurement: SENSEX monthly quote
   quality — share of strikes live-quoted.** Both symbols' depth 4 stay behind the stage-2
   gate.
7. **Stage-2 gate redefinition — owed operator decision.** Per **TD-S81-NEW-14** the gate
   must count **fail-fasts by class and dropped captures**, not retries: a retry-shaped
   counter reads zero whatever happens, so the current gate cannot fail for the reason it
   names.
8. **P5 — which max pain is canonical** (`v_gex_max_pain` GEX-run vs `v_max_pain_by_strike`
   raw chain). They agree on strike and disagree on strike count, total and `ts`. A renderer
   must pick one and name it; **TD-S84-NEW-6** records that the agreement is not
   corroboration.
9. **The scratch-evidence decision.** `scratch/` and `research/` are untracked **and not
   git-ignored** — the third state. Every `path:line` in `capture_s84.md` and
   `parity_render_contract.md` points at evidence one `git clean -fd` from gone. Commit it,
   ignore it, or accept it as session-scoped; **all three are defensible, none is chosen.**
10. **Original owed decisions 2–5 carry unchanged** from the S83 block: the product-name
    scrub (**32 occurrences, six files** — measured this session, case-insensitively), the
    `authenticated` / `service_role` default grants on new views, and the vendor methodology
    question on Greeks/IV.

**Carried, not started**

11. **`parity_board_design.md` A–C** — brief is in project knowledge; nothing in A–C is
    startable from the repo alone.
12. **EC2 pull `18c2fb8` → HEAD, then `git -C ~/meridian-engine rev-parse HEAD`** — six
    commits behind, **all docs-only, measured** (`git diff --name-only`: 0 `.py`, 0
    non-`docs/`). §1.1 stays open until this tool reads the post-pull hash itself.
13. **The `merdian_parameters` editor sample** — still owed.
14. **Commit the ENH-98 instrument to `sql/research/enh98/`** — it exists only at
    `scratch/s84_l78/s81_gonogo_query.sql`, untracked, and it is the artefact A0's 12/12
    reproduction depends on.
15. **L78-1/-2/-3 are ruled, not built.** The rulings are recorded below and in the ENH-98
    block. No build is authorised by them.
16. **The doc-close checklist omits five files it governs** — `CLAUDE.md:129-136` names
    neither the Assumption Register, the Decision Index, the System Map, the Deployment
    Topology, nor `CURRENT_history.md`, all of which recent closes update. **Recorded as
    owed; the checklist was not edited this close.**

## OPERATOR RULINGS, S84

These exist only in chat and are recorded here and in the ENH-98 block. **None authorises a
build.**

- **L78-1 — definition: compute BOTH.** Textbook `∂delta/∂sigma` and `∂delta/∂t` in
  **δ-notional ₹ Cr**, *and* the parity target's `∂gamma` constructs. Each displays under a
  **distinct name with a one-line narration**; **neither is labelled plain "vanna"/"charm".**
- **L78-2 — scope: show BOTH.** Full standing book is **primary**; today's new positions are
  secondary and labelled *"since open; assumes the standard dealer side"*, and are **hidden
  when the L13 outlier guard trips** (TD-S84-NEW-4). A previous-close baseline and side
  classification come later.
- **L78-3 — cadence and horizon.** **One daily reading at the 10:15 IST cycle**, after the
  initial balance. Charm horizon is **the same time next trading session**, decaying in
  **calendar** time (weekends included). **No post-close reads.** On expiry day W2 and the
  monthlies compute as normal; **W1's "charm to 15:30" is COMPUTED AND RECORDED under its own
  label but NOT DISPLAYED** until E1/E2-type evidence accumulates across several expiries.
  **S62 is amended for that leg only, and only with evidence.** A per-expiry closure record
  (forecast vs observed) is to be designed as an extension of `expiry_outcomes` (ENH-116),
  **schema measured first.**
- **Capture depth — SENSEX to match NIFTY.** Recorded as an **open decision** that reopens
  ADR-025's S80 ruling, with the owed measurement named at item 6 above.
