# CURRENT.md — MERDIAN Live Session State

> **Living file.** Overwritten at the end of every session to reflect what just happened and what the next session is for.
> Claude reads this immediately after `CLAUDE.md` at session start. It replaces the practice of manually pasting a "session resume block."
> **History.** Every session block before S82 lives in [`docs/registers/CURRENT_history.md`](../registers/CURRENT_history.md) — committed to git, **not** uploaded to project knowledge. Split at the S78 doc-close per **TD-S73-NEW-8**; S78 demoted to history at the S80 doc-close and **S81 at the S83 doc-close**, each moved verbatim rather than retyped. This file carries the current session and one predecessor, and nothing else.

---

## Last session

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

## Previous session S83

**Session 83 — 2026-09-24 → 2026-09-25 (Thu–Fri).** Build. Three ADR-025 parity
layers authored, validated and deployed; **production Python unchanged**.

| Field | Value |
|---|---|
| **Shipped** | **ENH-130** `v_iv_term_structure` (L9, 17 cols) · **ENH-131** `v_gex_repriced_flip` (L3, 18 cols) · **ENH-132** `v_iv_surface` (L10, 21 cols). Applied by the operator in the Supabase editor. Anon path verified by `SET ROLE anon`, not by object existence. |
| **Parity count** | **BUILT STAYS 2 of 14.** ADR-025 D2 clauses 1/2/4 MET on all three; **clause 3 PENDING BY DECISION** under Amendment B1. Three ships that deliberately do not move the count — B1 working as written, not a lapse. |
| **The gate record** | **Three of ENH-131's five gates FAILED** and the full record lives in the view's own COMMENT. Gate 2 compared a heavily-cancelled net against 1 % where net/gross runs **0.0095–0.341**; Gate 3(ii) used a ±5 % window blind to a 2→1 crossing-count change; Gate 4's ±0.01 r band was **~19× narrower** than the dispersion it bounded. Gate 5 passed 5/5 on three out-of-sample arms. |
| **Four mis-specified gates, none loosened** | One shape: a threshold set before the quantity's scale was derived. Now a CLAUDE.md settled bullet. The builds shipped on separately pre-registered replacements, not on relaxed thresholds. |
| **Host change** | One `mv`: `/etc/logrotate.d/meridian.PRE_20260922` → `/root/`. **TD-S83-NEW-1 filed and CLOSED** on an **observed** clean run (`Finished Rotate log files.` 2026-09-25 00:00:03), not on the fix. |
| **Ledger** | TDs_NEW=7 (TD-S83-NEW-1..7), TDs_CLOSED=1. ADRs_NEW=0, ADRs_AMENDED=0, **no Decision Index row — stated as a decision**. Enhancement Register TRIGGERED, fifth consecutive session. |

**Three things this session got wrong and recorded rather than absorbed.** Five
figures in one COMMENT draft were wrong because they were read off rendered tables
instead of files, and the queries had never been saved to `.out`. A `journalctl`
read returning `No entries` was a **no-test**, not a clean result — the `sudo` read
returned two nights of logrotate failures. And **the capture file written to drive
this doc-close was itself wrong twice**: it predicted `[ -- ] NOT AUDITABLE` on a
check that printed `[ OK ]`, and it blamed ADR-015 for a column naming the ADR does
not use. All filed — §D.39, TD-S83-NEW-7.

**`equity_intraday_last` is auditable on the schedule, and the S82 claim that it
reads `[ -- ] NOT AUDITABLE` every night by design was wrong.** The mechanism is in
§D.39.4, read from `scripts/eod_health_check.py:367-419`: NOT AUDITABLE requires the
one-generation table to have moved **past** the audited date, and the 00:45 UTC slot
runs **before** that day's successor refresh. Do not repeat the "every night" claim.

## NEXT SESSION PICKS UP

1. **Capture depth — the one decision that blocks two layers.** SENSEX furthest
   listed expiry, NIFTY 5th leg, or formally record the ADR-025 **D3 deviation**.
   Recommendation on record: add current + next **monthly** expiries (4 legs) as its
   own measured ENH. Blocks L9 comparability and L10 depth; blocks neither build.
2. **Scrub the reference product name from existing registers** (the parity spec
   filename, ADR-025, older notes). New S83 lines already carry none.
3. **`authenticated` / `service_role` default grants on new views** — Supabase
   defaults gave both privileges on all three; flagged at deploy, not acted on.
4. **Send the vendor methodology question on Greeks/IV** (drafted, not sent) — one
   route to closing TD-S83-NEW-4 and TD-S83-NEW-5.
5. **2026-09-29 — NIFTY L9 stage-1 max-pain arm** (TD-S80-NEW-1).
6. **ENH-98 re-run with SENSEX at dte 1–2**; the multi-DTE offset test.
7. **Parity build order continues: L7/L8 (ENH-98) next.**
8. Everything under the S82 block's "Decisions owed" that S83 did not touch carries
   unchanged.

